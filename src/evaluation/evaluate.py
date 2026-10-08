"""Evaluate generated predictions (scaffold)."""

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

    metrics_path = output_dir / "metrics.json"
    metrics = {
        "status": "pending",
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "metrics": {
            "der": None,
            "wer": None,
            "action_item_f1": None,
            "latency_p95_seconds": None,
        },
        "notes": (
            "No reproduced scores yet. Report results only after a fixed protocol "
            "run with saved evidence."
        ),
    }
    metrics_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(f"Wrote pending metrics: {metrics_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
