"""Transform AMI sample annotations from private GCS into validated CSV/JSON.

Adapted from the parsing and aggregation logic in notebooks/01_dataset_eda.ipynb.
This is a standalone batch task suitable for orchestration by Apache Airflow.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import logging
import math
import re
import wave
import xml.etree.ElementTree as ET
import zipfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from google.cloud import storage

LOG = logging.getLogger("ami_cloud_transform")
SEGMENT_PATTERN = re.compile(r"^(?P<meeting>.+)\.(?P<speaker>[A-Z])\.segments\.xml$")
COLUMNS = ("meeting_id", "speaker", "start", "end", "duration")


def gcs_name(relative_path: str) -> str:
    """Map manifest repo paths to object names beneath the GCS raw prefix."""
    relative_path = relative_path.replace("\\", "/")
    if not relative_path.startswith("data/raw/"):
        raise ValueError(f"Manifest path must start with data/raw/: {relative_path}")
    return "raw/" + relative_path.removeprefix("data/raw/")


def get_bytes(bucket, name: str) -> bytes:
    blob = bucket.blob(name)
    if not blob.exists():
        raise FileNotFoundError(f"Missing GCS object: gs://{bucket.name}/{name}")
    content = blob.download_as_bytes()
    if not content:
        raise ValueError(f"Empty GCS object: {name}")
    LOG.info("Downloaded gs://%s/%s (%d bytes)", bucket.name, name, len(content))
    return content


def parse_segments(xml_bytes: bytes, filename: str, meeting_id: str) -> list[dict]:
    """Same transcriber_start/end extraction as the team's EDA notebook."""
    match = SEGMENT_PATTERN.fullmatch(filename)
    if not match or match.group("meeting") != meeting_id:
        raise ValueError(f"Unexpected segment filename: {filename}")
    root = ET.fromstring(xml_bytes)
    records = []
    for element in root.iter():
        if element.tag.split("}")[-1] != "segment":
            continue
        start_raw = element.get("transcriber_start")
        end_raw = element.get("transcriber_end")
        if start_raw is None or end_raw is None:
            continue  # Matches notebook behavior for un-timed segments.
        start, end = float(start_raw), float(end_raw)
        if not math.isfinite(start) or not math.isfinite(end) or start < 0 or end <= start:
            raise ValueError(f"Invalid time range in {filename}: {start_raw} to {end_raw}")
        records.append({
            "meeting_id": meeting_id,
            "speaker": match.group("speaker"),
            "start": round(start, 6),
            "end": round(end, 6),
            "duration": round(end - start, 6),
        })
    if not records:
        raise ValueError(f"No valid timed segments found in {filename}")
    return records


def zip_segments(archive: bytes, wanted: list[str]) -> dict[str, bytes]:
    """Read only the required segment XML members without extracting the whole ZIP."""
    found = {}
    with zipfile.ZipFile(io.BytesIO(archive)) as zf:
        bad_member = zf.testzip()
        if bad_member:
            raise ValueError(f"Corrupt ZIP member: {bad_member}")
        for member in zf.namelist():
            base = Path(member).name
            if base in wanted:
                if base in found:
                    raise ValueError(f"Duplicate annotation in ZIP: {base}")
                found[base] = zf.read(member)
    missing = sorted(set(wanted) - set(found))
    if missing:
        raise ValueError(f"Missing segment XML files in ZIP: {missing}")
    return found


def write_csv(path: Path, rows: list[dict], columns: tuple[str, ...]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def run(bucket_name: str, output_prefix: str, output_dir: Path, manifest_blob: str = 'raw/ami_sample.json') -> None:
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    output_prefix = output_prefix.strip("/")
    output_dir.mkdir(parents=True, exist_ok=True)

    manifest = json.loads(get_bytes(bucket, manifest_blob))
    meetings = manifest.get("meetings")
    if not isinstance(meetings, list) or not meetings:
        raise ValueError("Manifest must contain a nonempty meetings list")

    archive = get_bytes(bucket, "raw/ami_public_manual_1.6.2.zip")
    all_segments = []
    meeting_rows = []
    seen_meetings = set()

    for meeting in meetings:
        meeting_id = str(meeting.get("meeting_id", "")).strip()
        if not meeting_id or meeting_id in seen_meetings:
            raise ValueError(f"Missing or duplicate meeting ID: {meeting_id!r}")
        seen_meetings.add(meeting_id)
        if not isinstance(meeting.get("num_speakers"), int) or meeting["num_speakers"] <= 0:
            raise ValueError(f"Invalid num_speakers for {meeting_id}")
        audio_name = gcs_name(meeting["audio_path"])
        # Download and check the WAV header. No model inference or audio transformation.
        audio = get_bytes(bucket, audio_name)
        with wave.open(io.BytesIO(audio), "rb") as wf:
            audio_duration = wf.getnframes() / wf.getframerate()
            sample_rate = wf.getframerate()
            channels = wf.getnchannels()
        if audio_duration <= 0:
            raise ValueError(f"Empty audio duration: {meeting_id}")
        for headset_path in meeting.get("headset_paths", []):
            headset_name = gcs_name(headset_path)
            blob = bucket.get_blob(headset_name)
            if blob is None or not blob.size:
                raise FileNotFoundError(f"Missing or empty headset audio: {headset_name}")

        segment_paths = meeting.get("reference_segments") or []
        if not segment_paths:
            raise ValueError(f"No reference_segments for {meeting_id}")
        filenames = [Path(p).name for p in segment_paths]
        xml_map = zip_segments(archive, filenames)
        rows = []
        for filename in filenames:
            rows.extend(parse_segments(xml_map[filename], filename, meeting_id))
        speakers = {r["speaker"] for r in rows}
        if len(speakers) != meeting["num_speakers"]:
            raise ValueError(f"Speaker-count mismatch for {meeting_id}: expected {meeting['num_speakers']}, got {len(speakers)}")
        if any(r["end"] > audio_duration + 1 for r in rows):
            raise ValueError(f"Annotation extends beyond audio duration for {meeting_id}")
        all_segments.extend(rows)
        meeting_rows.append({
            "meeting_id": meeting_id,
            "split": meeting.get("split", ""),
            "num_speakers": len(speakers),
            "audio_duration_sec": round(audio_duration, 3),
            "sample_rate_hz": sample_rate,
            "channels": channels,
            "segment_count": len(rows),
            "audio_sha256": hashlib.sha256(audio).hexdigest(),
        })
        LOG.info("Validated %s: %d segments, %d speakers", meeting_id, len(rows), len(speakers))

    all_segments.sort(key=lambda r: (r["meeting_id"], r["start"], r["speaker"], r["end"]))
    speaker_stats = defaultdict(lambda: {"n_segments": 0, "speech_sec": 0.0})
    for row in all_segments:
        stats = speaker_stats[(row["meeting_id"], row["speaker"])]
        stats["n_segments"] += 1
        stats["speech_sec"] += row["duration"]
    speaker_rows = [
        {"meeting_id": m, "speaker": s, "n_segments": v["n_segments"],
         "speech_sec": round(v["speech_sec"], 3), "speech_min": round(v["speech_sec"] / 60, 3)}
        for (m, s), v in sorted(speaker_stats.items())
    ]
    summary = {
        "dataset": manifest.get("dataset"),
        "sample_id": manifest.get("sample_id"),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "meetings": len(meeting_rows),
        "segments": len(all_segments),
        "speakers": len(speaker_rows),
        "validation_issues": 0,
        "input_manifest": f"gs://{bucket_name}/{manifest_blob}",
        "annotation_archive": f"gs://{bucket_name}/raw/ami_public_manual_1.6.2.zip",
        "segment_schema": list(COLUMNS),
        "note": "Ground-truth AMI annotation segments, not model predictions.",
    }

    artifacts = {
        "speaker_segments.csv": lambda p: write_csv(p, all_segments, COLUMNS),
        "speaker_segments.json": lambda p: p.write_text(json.dumps(all_segments, indent=2), encoding="utf-8"),
        "speaker_stats.csv": lambda p: write_csv(p, speaker_rows, ("meeting_id", "speaker", "n_segments", "speech_sec", "speech_min")),
        "meeting_metadata.csv": lambda p: write_csv(p, meeting_rows, ("meeting_id", "split", "num_speakers", "audio_duration_sec", "sample_rate_hz", "channels", "segment_count", "audio_sha256")),
        "transformation_summary.json": lambda p: p.write_text(json.dumps(summary, indent=2), encoding="utf-8"),
    }
    for filename, save in artifacts.items():
        local_path = output_dir / filename
        save(local_path)
        remote_name = f"{output_prefix}/{filename}"
        bucket.blob(remote_name).upload_from_filename(str(local_path))
        if not bucket.blob(remote_name).exists():
            raise RuntimeError(f"Upload verification failed: {remote_name}")
        LOG.info("Uploaded gs://%s/%s (%d bytes)", bucket_name, remote_name, local_path.stat().st_size)
    LOG.info("SUCCESS: %s", json.dumps(summary))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bucket", default="meeting-intelligence-data-514219")
    parser.add_argument("--output-prefix", default="processed/ami_sample_v1")
    parser.add_argument("--output-dir", type=Path, default=Path("data/processed/ami_cloud"))
    parser.add_argument("--manifest-blob", default="raw/ami_sample.json")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    run(args.bucket, args.output_prefix, args.output_dir, args.manifest_blob)


if __name__ == "__main__":
    main()
