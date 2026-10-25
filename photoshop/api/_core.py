"""
* Photocraft Core Base Object (photoshop.api._core)
"""
from __future__ import annotations

from typing import Any


class Photoshop:
    """Base wrapper class for Photocraft-backed objects."""

    def __init__(self, parent: Any = None) -> None:
        self.parent = parent
        self.app: Any = getattr(parent, "app", parent)
