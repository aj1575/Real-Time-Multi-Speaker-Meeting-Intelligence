"""ASR transcription for diarized AMI segments."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.pipeline.diarize import DiarizationSegment


class TranscriptionError(RuntimeError):
    """Raised when ASR cannot run."""


@dataclass
class TranscriptSegment:
    speaker: str
    start: float
    end: float
    text: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "speaker": self.speaker,
            "start": round(float(self.start), 3),
            "end": round(float(self.end), 3),
            "text": self.text,
        }


def _load_audio_window(audio_path: Path, start: float, end: float) -> tuple[Any, int]:
    try:
        import soundfile as sf
    except ImportError as exc:
        raise TranscriptionError(
            "Missing dependency: soundfile is required to crop diarized segments for ASR."
        ) from exc

    with sf.SoundFile(str(audio_path)) as handle:
        sample_rate = handle.samplerate
        start_frame = max(0, int(start * sample_rate))
        end_frame = min(len(handle), int(end * sample_rate))
        if end_frame <= start_frame:
            raise TranscriptionError(f"Invalid segment window: {start}-{end}")
        handle.seek(start_frame)
        audio = handle.read(frames=end_frame - start_frame, dtype="float32", always_2d=False)
    return audio, sample_rate


def _load_asr_pipeline(model_name: str, device: str):
    try:
        import torch
        from transformers import pipeline as hf_pipeline
    except ImportError as exc:
        raise TranscriptionError(
            "Missing model access: transformers/torch are not installed for ASR."
        ) from exc

    torch_dtype = torch.float16 if device == "cuda" else torch.float32
    try:
        return hf_pipeline(
            "automatic-speech-recognition",
            model=model_name,
            device=0 if device == "cuda" else -1,
            torch_dtype=torch_dtype,
        )
    except Exception as exc:  # noqa: BLE001
        raise TranscriptionError(f"Failed to load ASR model '{model_name}': {exc}") from exc


def transcribe_segments(
    audio_path: Path,
    diarization_segments: list[DiarizationSegment],
    *,
    model_name: str,
    language: str,
    device: str,
) -> list[TranscriptSegment]:
    if not audio_path.exists():
        raise TranscriptionError(f"Missing audio: {audio_path}")
    if not diarization_segments:
        raise TranscriptionError("Empty diarization output: nothing to transcribe.")

    asr = _load_asr_pipeline(model_name=model_name, device=device)
    results: list[TranscriptSegment] = []

    for segment in diarization_segments:
        audio, sample_rate = _load_audio_window(audio_path, segment.start, segment.end)
        try:
            output = asr(
                {"array": audio, "sampling_rate": sample_rate},
                generate_kwargs={"language": language},
            )
        except TypeError:
            output = asr({"array": audio, "sampling_rate": sample_rate})
        except Exception as exc:  # noqa: BLE001
            raise TranscriptionError(
                f"ASR failed for {segment.speaker} [{segment.start}-{segment.end}]: {exc}"
            ) from exc

        text = str(output.get("text", "")).strip() if isinstance(output, dict) else str(output).strip()
        results.append(
            TranscriptSegment(
                speaker=segment.speaker,
                start=segment.start,
                end=segment.end,
                text=text or "[inaudible]",
            )
        )

    return results
