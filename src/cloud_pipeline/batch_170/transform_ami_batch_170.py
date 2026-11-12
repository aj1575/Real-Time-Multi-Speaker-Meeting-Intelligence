
"""Transform all 170 AMI meetings using ground-truth annotations.

The script:
- Reads the 170-meeting manifest from GCS.
- Reads WAV metadata without downloading full recordings.
- Parses speaker-segment XML files.
- Handles empty speaker annotation files.
- Excludes invalid or entirely out-of-bounds segments.
- Clips segments that partially exceed audio duration.
- Saves detailed validation reports.
- Uploads processed outputs to a separate GCS location.

Original audio and annotations are never modified.
This script does not perform ASR or diarization inference.
"""

import argparse
import csv
import io
import json
import logging
import math
import re
import wave
import zipfile

from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
import xml.etree.ElementTree as ET

from google.cloud import storage


LOG = logging.getLogger("ami_batch_170")

SEGMENT_PATTERN = re.compile(
    r"(?P<meeting>[A-Za-z0-9]+)\."
    r"(?P<speaker>[A-Z])\.segments\.xml"
)

SEGMENT_COLUMNS = (
    "meeting_id",
    "speaker",
    "start",
    "end",
    "duration",
)

ISSUE_COLUMNS = (
    "meeting_id",
    "filename",
    "speaker",
    "segment_index",
    "issue_type",
    "original_start",
    "original_end",
    "corrected_start",
    "corrected_end",
    "reason",
)

METADATA_COLUMNS = (
    "meeting_id",
    "num_annotation_files",
    "num_active_speakers",
    "audio_duration_sec",
    "sample_rate_hz",
    "channels",
    "segment_count",
    "audio_size_bytes",
)

STATS_COLUMNS = (
    "meeting_id",
    "speaker",
    "n_segments",
    "speech_sec",
    "speech_min",
)


def write_csv(path, rows, columns):
    with path.open(
        "w", encoding="utf-8", newline=""
    ) as file:
        writer = csv.DictWriter(
            file, fieldnames=columns
        )
        writer.writeheader()
        writer.writerows(rows)


def record_issue(
    issues,
    meeting_id,
    filename,
    speaker,
    segment_index,
    issue_type,
    original_start=None,
    original_end=None,
    corrected_start=None,
    corrected_end=None,
    reason="",
):
    issues.append({
        "meeting_id": meeting_id,
        "filename": filename,
        "speaker": speaker,
        "segment_index": segment_index,
        "issue_type": issue_type,
        "original_start": original_start,
        "original_end": original_end,
        "corrected_start": corrected_start,
        "corrected_end": corrected_end,
        "reason": reason,
    })


def parse_segments(
    xml_bytes,
    filename,
    meeting_id,
    validation_issues,
):
    """Parse timed segments and record invalid timestamps."""

    match = SEGMENT_PATTERN.fullmatch(filename)

    if not match:
        raise ValueError(
            f"Invalid annotation filename: {filename}"
        )

    if match.group("meeting") != meeting_id:
        raise ValueError(
            f"Annotation belongs to another meeting: {filename}"
        )

    speaker = match.group("speaker")

    root = ET.fromstring(xml_bytes)

    rows = []

    segment_elements = [
        element
        for element in root.iter()
        if element.tag.split("}")[-1] == "segment"
    ]

    # Some AMI annotation files are completely empty.
    if not segment_elements:
        record_issue(
            validation_issues,
            meeting_id,
            filename,
            speaker,
            None,
            "empty_annotation_file",
            reason="Annotation contains zero segments",
        )

        LOG.warning(
            "Empty speaker annotation: %s",
            filename,
        )

        return rows

    for segment_index, element in enumerate(
        segment_elements
    ):
        start_raw = element.get("transcriber_start")
        end_raw = element.get("transcriber_end")

        # Preserve the original pipeline's behavior:
        # untimed elements are not converted to speech segments.
        if start_raw is None or end_raw is None:
            continue

        try:
            start = float(start_raw)
            end = float(end_raw)
        except (TypeError, ValueError):
            start = None
            end = None

        if (
            start is None
            or end is None
            or not math.isfinite(start)
            or not math.isfinite(end)
            or start < 0
            or end <= start
        ):
            record_issue(
                validation_issues,
                meeting_id,
                filename,
                speaker,
                segment_index,
                "invalid_timing",
                original_start=start_raw,
                original_end=end_raw,
                reason="Invalid or reversed timestamps",
            )

            LOG.warning(
                "Skipping invalid segment: %s | %s to %s",
                filename,
                start_raw,
                end_raw,
            )

            continue

        rows.append({
            "meeting_id": meeting_id,
            "speaker": speaker,
            "start": round(start, 6),
            "end": round(end, 6),
            "duration": round(end - start, 6),
            "_filename": filename,
            "_segment_index": segment_index,
        })

    return rows


def correct_segments(
    rows,
    meeting_id,
    audio_duration,
    validation_issues,
):
    """Correct segments that exceed the recording duration."""

    corrected_rows = []
    audio_end = round(audio_duration, 6)

    for row in rows:
        start = row["start"]
        end = row["end"]

        filename = row["_filename"]
        segment_index = row["_segment_index"]

        # Segment is completely outside the recording.
        if start >= audio_end:
            record_issue(
                validation_issues,
                meeting_id,
                filename,
                row["speaker"],
                segment_index,
                "outside_audio",
                original_start=start,
                original_end=end,
                reason="Segment starts at or after audio end",
            )

            LOG.warning(
                "Skipping out-of-bounds segment: "
                "%s | speaker=%s | start=%s | end=%s",
                meeting_id,
                row["speaker"],
                start,
                end,
            )

            continue

        # Segment partially extends beyond the recording.
        if end > audio_end:
            record_issue(
                validation_issues,
                meeting_id,
                filename,
                row["speaker"],
                segment_index,
                "clipped_segment",
                original_start=start,
                original_end=end,
                corrected_start=start,
                corrected_end=audio_end,
                reason="Segment end exceeds audio duration",
            )

            LOG.warning(
                "Clipping segment: %s | speaker=%s | "
                "old_end=%s | new_end=%s",
                meeting_id,
                row["speaker"],
                end,
                audio_end,
            )

            end = audio_end

        if end <= start:
            raise ValueError(
                f"Invalid corrected segment: {meeting_id}"
            )

        corrected_rows.append({
            "meeting_id": meeting_id,
            "speaker": row["speaker"],
            "start": start,
            "end": end,
            "duration": round(end - start, 6),
        })

    return corrected_rows


def run(
    bucket_name,
    manifest_blob,
    output_prefix,
    output_dir,
):
    client = storage.Client()
    bucket = client.bucket(bucket_name)

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    LOG.info("Downloading the full-dataset manifest")

    manifest = json.loads(
        bucket.blob(manifest_blob).download_as_text()
    )

    meetings = manifest["meetings"]

    if len(meetings) != 170:
        raise ValueError(
            f"Expected 170 meetings, found {len(meetings)}"
        )

    LOG.info("Downloading the AMI annotation archive")

    archive_bytes = bucket.blob(
        "raw/ami_public_manual_1.6.2.zip"
    ).download_as_bytes()

    all_segments = []
    meeting_rows = []
    validation_issues = []
    seen_meetings = set()

    with zipfile.ZipFile(
        io.BytesIO(archive_bytes)
    ) as archive:

        bad_member = archive.testzip()

        if bad_member:
            raise ValueError(
                f"Corrupt ZIP entry: {bad_member}"
            )

        annotation_lookup = {}

        for member in archive.namelist():
            filename = Path(member).name

            if SEGMENT_PATTERN.fullmatch(filename):
                if filename in annotation_lookup:
                    raise ValueError(
                        f"Duplicate annotation: {filename}"
                    )

                annotation_lookup[filename] = member

        for index, meeting in enumerate(
            meetings, start=1
        ):
            meeting_id = meeting["meeting_id"]

            if meeting_id in seen_meetings:
                raise ValueError(
                    f"Duplicate meeting ID: {meeting_id}"
                )

            seen_meetings.add(meeting_id)

            audio_blob = meeting["audio_blob"]

            expected_audio_blob = (
                "raw/ami_full_170/audio/"
                f"{meeting_id}.Mix-Headset.wav"
            )

            if audio_blob != expected_audio_blob:
                raise ValueError(
                    f"Incorrect audio path: {meeting_id}"
                )

            blob = bucket.get_blob(audio_blob)

            if blob is None or not blob.size:
                raise ValueError(
                    f"Missing or empty audio: {meeting_id}"
                )

            # Only read WAV metadata.
            with blob.open("rb") as audio_stream:
                with wave.open(
                    audio_stream, "rb"
                ) as wav:

                    sample_rate = wav.getframerate()
                    channels = wav.getnchannels()
                    frames = wav.getnframes()

                    if sample_rate <= 0 or channels <= 0:
                        raise ValueError(
                            f"Invalid WAV format: {meeting_id}"
                        )

                    audio_duration = (
                        frames / sample_rate
                    )

            if audio_duration <= 0:
                raise ValueError(
                    f"Invalid duration: {meeting_id}"
                )

            reference_files = meeting["reference_segments"]
            expected_annotation_count = meeting["num_speakers"]

            if (
                not reference_files
                or len(reference_files) != expected_annotation_count
                or len(set(reference_files)) != len(reference_files)
            ):
                raise ValueError(
                    f"Invalid annotation references: {meeting_id}"
                )

            rows = []

            for filename in reference_files:
                match = SEGMENT_PATTERN.fullmatch(filename)

                if (
                    match is None
                    or match.group("meeting") != meeting_id
                ):
                    raise ValueError(
                        f"Unexpected annotation: {filename}"
                    )

                member = annotation_lookup.get(filename)

                if member is None:
                    raise ValueError(
                        f"Missing annotation: {filename}"
                    )

                rows.extend(
                    parse_segments(
                        archive.read(member),
                        filename,
                        meeting_id,
                        validation_issues,
                    )
                )

            # Apply timestamp corrections.
            rows = correct_segments(
                rows,
                meeting_id,
                audio_duration,
                validation_issues,
            )

            if not rows:
                raise ValueError(
                    f"No valid segments remaining: {meeting_id}"
                )

            active_speakers = {
                row["speaker"]
                for row in rows
            }

            expected_speaker_labels = {
                SEGMENT_PATTERN.fullmatch(
                    filename
                ).group("speaker")
                for filename in reference_files
            }

            # Every active speaker must have a corresponding
            # annotation file. Empty annotation files are allowed.
            if not active_speakers.issubset(
                expected_speaker_labels
            ):
                raise ValueError(
                    f"Unexpected active speaker: {meeting_id}"
                )

            if len(active_speakers) > expected_annotation_count:
                raise ValueError(
                    f"Too many active speakers: {meeting_id}"
                )

            # Validate the final processed segments.
            if any(
                row["start"] < 0
                or row["end"] <= row["start"]
                or row["end"] > round(
                    audio_duration, 6
                )
                for row in rows
            ):
                raise ValueError(
                    f"Invalid corrected segments: {meeting_id}"
                )

            all_segments.extend(rows)

            meeting_rows.append({
                "meeting_id": meeting_id,
                "num_annotation_files": len(reference_files),
                "num_active_speakers": len(active_speakers),
                "audio_duration_sec": round(
                    audio_duration, 3
                ),
                "sample_rate_hz": sample_rate,
                "channels": channels,
                "segment_count": len(rows),
                "audio_size_bytes": blob.size,
            })

            LOG.info(
                "[%d/170] %s | %d segments | "
                "%d active speakers | %d annotation files",
                index,
                meeting_id,
                len(rows),
                len(active_speakers),
                len(reference_files),
            )

    all_segments.sort(
        key=lambda row: (
            row["meeting_id"],
            row["start"],
            row["speaker"],
            row["end"],
        )
    )

    speaker_stats = defaultdict(
        lambda: {
            "n_segments": 0,
            "speech_sec": 0.0,
        }
    )

    for row in all_segments:
        key = (
            row["meeting_id"],
            row["speaker"],
        )

        speaker_stats[key]["n_segments"] += 1
        speaker_stats[key]["speech_sec"] += row["duration"]

    speaker_rows = []

    for (meeting_id, speaker), stats in sorted(
        speaker_stats.items()
    ):
        speaker_rows.append({
            "meeting_id": meeting_id,
            "speaker": speaker,
            "n_segments": stats["n_segments"],
            "speech_sec": round(
                stats["speech_sec"], 3
            ),
            "speech_min": round(
                stats["speech_sec"] / 60, 3
            ),
        })

    # Count each type of validation issue.
    issue_counts = defaultdict(int)

    for issue in validation_issues:
        issue_counts[issue["issue_type"]] += 1

    excluded_count = (
        issue_counts["invalid_timing"]
        + issue_counts["outside_audio"]
    )

    clipped_count = issue_counts["clipped_segment"]
    empty_file_count = issue_counts["empty_annotation_file"]

    affected_meetings = sorted({
        issue["meeting_id"]
        for issue in validation_issues
    })

    total_annotation_files = sum(
        row["num_annotation_files"]
        for row in meeting_rows
    )

    summary = {
        "dataset": manifest.get(
            "dataset", "AMI Meeting Corpus"
        ),
        "sample_id": "ami_full_170",
        "generated_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "meetings": len(meeting_rows),
        "annotation_files": total_annotation_files,
        "segments": len(all_segments),
        "active_speaker_meeting_pairs": len(speaker_rows),
        "validation_issues": len(validation_issues),
        "invalid_timing_segments": issue_counts["invalid_timing"],
        "outside_audio_segments": issue_counts["outside_audio"],
        "excluded_segments": excluded_count,
        "clipped_segments": clipped_count,
        "empty_annotation_files": empty_file_count,
        "affected_meetings": affected_meetings,
        "input_manifest": (
            f"gs://{bucket_name}/{manifest_blob}"
        ),
        "annotation_archive": (
            f"gs://{bucket_name}/"
            "raw/ami_public_manual_1.6.2.zip"
        ),
        "note": (
            "Ground-truth speaker annotations, "
            "not model predictions. Original AMI "
            "audio and annotations were not modified."
        ),
    }

    # Save processed CSV files.
    write_csv(
        output_dir / "speaker_segments.csv",
        all_segments,
        SEGMENT_COLUMNS,
    )

    write_csv(
        output_dir / "speaker_stats.csv",
        speaker_rows,
        STATS_COLUMNS,
    )

    write_csv(
        output_dir / "meeting_metadata.csv",
        meeting_rows,
        METADATA_COLUMNS,
    )

    write_csv(
        output_dir / "validation_issues.csv",
        validation_issues,
        ISSUE_COLUMNS,
    )

    # Save processed JSON files.
    (output_dir / "speaker_segments.json").write_text(
        json.dumps(all_segments, indent=2),
        encoding="utf-8",
    )

    (output_dir / "validation_issues.json").write_text(
        json.dumps(validation_issues, indent=2),
        encoding="utf-8",
    )

    (output_dir / "transformation_summary.json").write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )

    # Upload only the expected output files.
    filenames = [
        "speaker_segments.csv",
        "speaker_segments.json",
        "speaker_stats.csv",
        "meeting_metadata.csv",
        "validation_issues.csv",
        "validation_issues.json",
        "transformation_summary.json",
    ]

    for filename in filenames:
        local_path = output_dir / filename
        remote_path = (
            f"{output_prefix.strip('/')}/{filename}"
        )

        bucket.blob(
            remote_path
        ).upload_from_filename(
            str(local_path)
        )

        if not bucket.blob(remote_path).exists():
            raise RuntimeError(
                f"Upload verification failed: {remote_path}"
            )

        LOG.info(
            "Uploaded gs://%s/%s",
            bucket_name,
            remote_path,
        )

    LOG.info(
        "TRANSFORMATION COMPLETE: %s",
        json.dumps(summary),
    )

    return summary


def main():
    parser = argparse.ArgumentParser(
        description="Transform all 170 AMI meetings"
    )

    parser.add_argument(
        "--bucket",
        default="meeting-intelligence-data-514219",
    )

    parser.add_argument(
        "--manifest-blob",
        default=(
            "raw/ami_full_170/"
            "ami_full_170_manifest.json"
        ),
    )

    parser.add_argument(
        "--output-prefix",
        default="processed/ami_full_170_v1",
    )

    parser.add_argument(
        "--output-dir",
        default="data/processed/ami_full_170",
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    run(
        args.bucket,
        args.manifest_blob,
        args.output_prefix,
        args.output_dir,
    )


if __name__ == "__main__":
    main()
