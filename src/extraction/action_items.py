"""Extract action items with transcript evidence (scaffold)."""

from __future__ import annotations

from typing import Any


def extract_action_items(segments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return grounded action-item candidates.

    Owners and deadlines are only filled when explicitly present in the text.
    This scaffold returns an empty list until the extraction model is wired in.
    """
    if not segments:
        return []
    return []
