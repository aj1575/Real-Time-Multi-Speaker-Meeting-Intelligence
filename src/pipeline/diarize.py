"""Speaker diarization for the AMI baseline."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class DiarizationSegment:
    speaker: str
    start: float
    end: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "speaker": self.speaker,
            "start": round(float(self.start), 3),
            "end": round(float(self.end), 3),
        }


class DiarizationError(RuntimeError):
    """Raised when diarization cannot run."""


def resolve_device(device: str) -> str:
    requested = (device or "auto").lower()
    if requested in {"cpu", "cuda"}:
        if requested == "cuda":
            try:
                import torch

                if not torch.cuda.is_available():
                    raise DiarizationError("GPU unavailable: CUDA was requested but is not available.")
            except ImportError as exc:
                raise DiarizationError("GPU unavailable: torch is not installed.") from exc
        return requested

    try:
        import torch

        return "cuda" if torch.cuda.is_available() else "cpu"
    except ImportError:
        return "cpu"


def run_diarization(
    audio_path: Path,
    *,
    model_name: str,
    device: str,
    hf_token: str | None,
) -> list[DiarizationSegment]:
    """Run pyannote diarization, or raise a clear error if unavailable."""
    if not audio_path.exists():
        raise DiarizationError(f"Missing audio: {audio_path}")

    if not hf_token:
        raise DiarizationError(
            "Missing model access: set HF_TOKEN in .env for gated pyannote models."
        )

    try:
        from pyannote.audio import Pipeline
    except ImportError as exc:
        raise DiarizationError(
            "Missing model access: pyannote.audio is not installed. "
            "Install the team-approved torch/pyannote versions first."
        ) from exc

    resolved_device = resolve_device(device)

    try:
        try:
            pipeline = Pipeline.from_pretrained(model_name, token=hf_token)
        except TypeError:
            pipeline = Pipeline.from_pretrained(model_name, use_auth_token=hf_token)
        if hasattr(pipeline, "to"):
            import torch

            pipeline.to(torch.device(resolved_device))
        annotation = pipeline(str(audio_path))
    except Exception as exc:  # noqa: BLE001 - surface provider/runtime failures clearly
        raise DiarizationError(f"Diarization failed: {exc}") from exc

    segments: list[DiarizationSegment] = []
    for turn, _, speaker in annotation.itertracks(yield_label=True):
        segments.append(
            DiarizationSegment(speaker=str(speaker), start=float(turn.start), end=float(turn.end))
        )

    if not segments:
        raise DiarizationError("Empty diarization output: no speaker turns were produced.")

    return segments
