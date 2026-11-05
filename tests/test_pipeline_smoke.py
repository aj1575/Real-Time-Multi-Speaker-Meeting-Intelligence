"""Smoke tests for the AMI baseline pipeline."""

from pathlib import Path

import yaml

from src.pipeline.run_baseline import resolve_audio_path, run_baseline


ROOT = Path(__file__).resolve().parents[1]


def test_config_points_at_es2002a() -> None:
    config = yaml.safe_load((ROOT / "configs" / "ami_sample.yaml").read_text(encoding="utf-8"))
    assert config["data"]["meeting_id"] == "ES2002a"
    meeting_id, audio_path = resolve_audio_path(config, ROOT)
    assert meeting_id == "ES2002a"
    assert audio_path.name == "ES2002a.Mix-Headset.wav"


def test_run_baseline_writes_schema_even_without_models(tmp_path: Path) -> None:
    """Pipeline must produce schema-compatible outputs when model access is missing."""
    config_path = ROOT / "configs" / "ami_sample.yaml"
    # Run from repo root so relative audio paths resolve.
    import os

    previous = Path.cwd()
    os.chdir(ROOT)
    try:
        code = run_baseline(config_path, repo_root=ROOT)
    finally:
        os.chdir(previous)

    # 0 = full model success, 2 = blocked on model/audio access but outputs written
    assert code in {0, 2}

    output = ROOT / "outputs" / "ES2002a_transcript.json"
    assert output.exists()
    payload = yaml.safe_load(output.read_text(encoding="utf-8"))  # json is yaml-compatible
    assert payload["meeting_id"] == "ES2002a"
    assert "segments" in payload
    assert isinstance(payload["segments"], list)
    assert payload["segments"]
    assert {"speaker", "start", "end", "text"} <= set(payload["segments"][0])
