"""Simple local demo for speaker-attributed transcripts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        required=True,
        type=Path,
        help="Path to transcript JSON (e.g. outputs/sample_transcript.json)",
    )
    args = parser.parse_args(argv)

    if not args.input.exists():
        print(f"Input not found: {args.input}")
        print("Run the baseline scaffold first:")
        print("  python -m src.pipeline.run_baseline --config configs/ami_sample.yaml")
        return 1

    payload = json.loads(args.input.read_text(encoding="utf-8"))
    print(f"Demo input: {args.input}")
    print(f"Status: {payload.get('status', 'unknown')}")
    print("---")
    for segment in payload.get("segments", []):
        speaker = segment.get("speaker", "?")
        start = segment.get("start", "?")
        end = segment.get("end", "?")
        text = segment.get("text", "")
        print(f"[{start}-{end}] {speaker}: {text}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
