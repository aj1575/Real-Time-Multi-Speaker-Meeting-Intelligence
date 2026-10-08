"""Validate a local dataset manifest against the expected schema."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml


REQUIRED_MEETING_KEYS = {
    "meeting_id",
    "audio_path",
    "reference_rttm",
    "reference_transcript",
    "num_speakers",
}


def load_config(config_path: Path) -> dict:
    with config_path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def validate_manifest(manifest_path: Path) -> list[str]:
    errors: list[str] = []

    if not manifest_path.exists():
        return [f"Manifest not found: {manifest_path}"]

    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"Manifest is not valid JSON: {exc}"]

    if "meetings" not in payload or not isinstance(payload["meetings"], list):
        errors.append("Manifest must include a 'meetings' list.")
        return errors

    if not payload["meetings"]:
        errors.append("Manifest 'meetings' list is empty.")

    for index, meeting in enumerate(payload["meetings"]):
        if not isinstance(meeting, dict):
            errors.append(f"meetings[{index}] must be an object.")
            continue
        missing = REQUIRED_MEETING_KEYS - set(meeting)
        if missing:
            errors.append(
                f"meetings[{index}] missing keys: {', '.join(sorted(missing))}"
            )
        speakers = meeting.get("num_speakers")
        if speakers is not None and (not isinstance(speakers, int) or speakers < 1):
            errors.append(f"meetings[{index}].num_speakers must be a positive integer.")

    return errors


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
    manifest_path = Path(config["data"]["manifest_path"])
    errors = validate_manifest(manifest_path)

    if errors:
        print("Manifest validation failed:")
        for error in errors:
            print(f"  - {error}")
        return 1

    print(f"Manifest OK: {manifest_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
