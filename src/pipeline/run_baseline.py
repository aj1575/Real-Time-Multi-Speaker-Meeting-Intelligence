"""Run the AMI diarization + ASR baseline."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import yaml
from dotenv import load_dotenv

from src.pipeline.diarize import DiarizationError, resolve_device, run_diarization
from src.pipeline.transcribe import TranscriptionError, transcribe_segments


class BaselineError(RuntimeError):
    """Raised for configuration or input problems."""


def load_config(config_path: Path) -> dict:
    if not config_path.exists():
        raise BaselineError(f"Config not found: {config_path}")
    with config_path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def resolve_audio_path(config: dict, repo_root: Path) -> tuple[str, Path]:
    meeting_id = str(config.get("data", {}).get("meeting_id") or "").strip()
    if not meeting_id:
        raise BaselineError("Invalid meeting ID: data.meeting_id is missing.")

    audio_value = config.get("data", {}).get("audio_path")
    if not audio_value:
        raise BaselineError("Missing audio: data.audio_path is not set in the config.")

    audio_path = Path(audio_value)
    if not audio_path.is_absolute():
        audio_path = repo_root / audio_path

    if not audio_path.exists():
        raise BaselineError(f"Missing audio: {audio_path}")

    return meeting_id, audio_path


def maybe_trim_audio(audio_path: Path, max_duration_seconds: float | None, work_dir: Path) -> Path:
    """Optionally trim long meetings for local CPU validation runs."""
    if max_duration_seconds is None:
        return audio_path
    try:
        max_seconds = float(max_duration_seconds)
    except (TypeError, ValueError) as exc:
        raise BaselineError("Invalid pipeline.max_duration_seconds") from exc
    if max_seconds <= 0:
        return audio_path

    try:
        import soundfile as sf
    except ImportError as exc:
        raise BaselineError("soundfile is required to trim audio") from exc

    work_dir.mkdir(parents=True, exist_ok=True)
    trimmed = work_dir / f"{audio_path.stem}_first_{int(max_seconds)}s.wav"
    with sf.SoundFile(str(audio_path)) as handle:
        frames = int(max_seconds * handle.samplerate)
        audio = handle.read(frames=min(frames, len(handle)), dtype="float32", always_2d=False)
        sf.write(str(trimmed), audio, handle.samplerate)
    return trimmed


def write_outputs(
    *,
    output_dir: Path,
    meeting_id: str,
    segments: list[dict],
    status: str,
    notes: str,
    runtime_seconds: float,
    device: str,
) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "meeting_id": meeting_id,
        "status": status,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "device": device,
        "runtime_seconds": round(runtime_seconds, 3),
        "segments": segments,
        "notes": notes,
    }

    json_path = output_dir / f"{meeting_id}_transcript.json"
    txt_path = output_dir / f"{meeting_id}_transcript.txt"

    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    lines = [
        f"Meeting: {meeting_id}",
        f"Status: {status}",
        f"Device: {device}",
        f"Runtime seconds: {payload['runtime_seconds']}",
        "",
    ]
    for segment in segments:
        lines.append(
            f"[{segment['start']:.2f}-{segment['end']:.2f}] {segment['speaker']}: {segment['text']}"
        )
    if notes:
        lines.extend(["", f"Notes: {notes}"])
    txt_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    # Keep demo default path in sync for local runs.
    (output_dir / "sample_transcript.json").write_text(
        json.dumps(payload, indent=2), encoding="utf-8"
    )
    return json_path, txt_path


def run_baseline(config_path: Path, repo_root: Path | None = None) -> int:
    repo_root = repo_root or Path.cwd()
    load_dotenv(repo_root / ".env")

    started = time.perf_counter()
    config = load_config(config_path)
    meeting_id, audio_path = resolve_audio_path(config, repo_root)
    output_dir = repo_root / Path(config.get("evaluation", {}).get("output_dir", "outputs"))
    device = resolve_device(str(config.get("pipeline", {}).get("device", "auto")))
    max_duration = config.get("pipeline", {}).get("max_duration_seconds")
    audio_path = maybe_trim_audio(
        audio_path,
        max_duration,
        repo_root / Path(config.get("data", {}).get("processed_root", "data/processed")),
    )

    diar_cfg = config.get("pipeline", {}).get("diarization", {})
    asr_cfg = config.get("pipeline", {}).get("asr", {})
    hf_token = os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_TOKEN")

    try:
        diar_segments = run_diarization(
            audio_path,
            model_name=str(diar_cfg.get("model", "pyannote/speaker-diarization-2.1")),
            device=device,
            hf_token=hf_token,
        )
        transcript_segments = transcribe_segments(
            audio_path,
            diar_segments,
            model_name=str(asr_cfg.get("model", "openai/whisper-tiny")),
            language=str(asr_cfg.get("language", "en")),
            device=device,
        )
        status = "ok"
        notes = (
            "Baseline pipeline implemented; metric reproduction pending. "
            "Do not claim published DER until evaluation evidence is saved."
        )
        segments = [segment.to_dict() for segment in transcript_segments]
    except (DiarizationError, TranscriptionError, BaselineError) as exc:
        runtime_seconds = time.perf_counter() - started
        status = "Baseline pipeline implemented; metric reproduction pending."
        notes = str(exc)
        segments = [
            {
                "speaker": "SPEAKER_00",
                "start": 0.0,
                "end": 0.0,
                "text": "[pipeline blocked before full model run]",
            }
        ]
        json_path, txt_path = write_outputs(
            output_dir=output_dir,
            meeting_id=meeting_id,
            segments=segments,
            status=status,
            notes=notes,
            runtime_seconds=runtime_seconds,
            device=device,
        )
        print(f"Baseline blocked: {exc}")
        print(f"Wrote pending outputs: {json_path}")
        print(f"Wrote pending text: {txt_path}")
        return 2

    runtime_seconds = time.perf_counter() - started
    json_path, txt_path = write_outputs(
        output_dir=output_dir,
        meeting_id=meeting_id,
        segments=segments,
        status=status,
        notes=notes,
        runtime_seconds=runtime_seconds,
        device=device,
    )
    print(f"Meeting: {meeting_id}")
    print(f"Device: {device}")
    print(f"Segments: {len(segments)}")
    print(f"Runtime seconds: {runtime_seconds:.3f}")
    print(f"Wrote JSON: {json_path}")
    print(f"Wrote TXT: {txt_path}")
    print(status if status != "ok" else notes)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        required=True,
        type=Path,
        help="Path to YAML config (e.g. configs/ami_sample.yaml)",
    )
    args = parser.parse_args(argv)

    try:
        return run_baseline(args.config, repo_root=Path.cwd())
    except BaselineError as exc:
        print(f"Baseline error: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
