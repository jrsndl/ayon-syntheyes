"""Data structures shared by SynthEyes loaders and the host."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ayon_core.pipeline import AYON_CONTAINER_ID


@dataclass
class Container:
    """AYON representation loaded as a SynthEyes scene object."""

    name: Optional[str] = None
    id: str = AYON_CONTAINER_ID
    namespace: str = ""
    loader: Optional[str] = None
    representation: Optional[str] = None
    objectName: Optional[str] = None  # noqa: N815
    version: Optional[str] = None
    shot_id: Optional[str] = None
    colorspace: Optional[str] = None
