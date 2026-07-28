"""Dependency-free helpers for clip loading."""

from __future__ import annotations

from typing import Any

DEPTH_VALUES = {
    "8 bit": 0,
    "16 bit": 1,
    "Half": 2,
    "Float": 3,
}
OUTPUT_DEPTH_VALUES = {
    "Follow process depth": -1,
    **DEPTH_VALUES,
}


def entity_fps(context: dict[str, Any]) -> float:
    """Resolve FPS from the AYON task, then folder, then version."""
    for entity_name in ("task", "folder", "version"):
        entity = context.get(entity_name) or {}
        value = (entity.get("attrib") or {}).get("fps")
        if value not in (None, ""):
            fps = float(value)
            if fps > 0:
                return fps
    raise RuntimeError(
        "The AYON task/folder does not define a valid FPS value."
    )
