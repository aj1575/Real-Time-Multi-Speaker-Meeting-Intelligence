"""Smoke tests for repository scaffolding."""

from pathlib import Path

from src.extraction.action_items import extract_action_items
from src.pipeline.validate_manifest import validate_manifest


ROOT = Path(__file__).resolve().parents[1]


def test_ami_sample_manifest_validates() -> None:
    errors = validate_manifest(ROOT / "data" / "manifests" / "ami_sample.json")
    assert errors == []


def test_action_item_scaffold_returns_empty_for_placeholder() -> None:
    items = extract_action_items(
        [{"speaker": "SPEAKER_00", "text": "Placeholder transcript segment."}]
    )
    assert items == []


def test_required_scaffold_files_exist() -> None:
    required = [
        ROOT / "configs" / "ami_sample.yaml",
        ROOT / ".env.example",
        ROOT / "requirements.txt",
        ROOT / "README.md",
    ]
    missing = [str(path) for path in required if not path.exists()]
    assert missing == []
