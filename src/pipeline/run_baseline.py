"""Run the diarization + ASR baseline (scaffold)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml


def load_config(config_path: Path) -> dict:
    with config_path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        required=True,
        type=Path,
        help="Path to YAML config (e.g. configs/ami_sample.yaml)",
    )
    args = parser.parse_args(argv)

    config = load_config(args.config)
    output_dir = Path(config["evaluation"]["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)

    sample_path = output_dir / "sample_transcript.json"
    payload = {
        "status": "pending_model_run",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "config": str(args.config),
        "segments": [
            {
                "start": 0.0,
                "end": 2.5,
                "speaker": "SPEAKER_00",
                "text": "Placeholder transcript segment.",
            }
        ],
        "notes": (
            "Baseline pipeline scaffold only. Replace with pyannote + ASR once "
            "model access and hardware are confirmed."
        ),
    }
    sample_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote scaffold transcript: {sample_path}")
    print("Baseline model execution is not enabled yet.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
