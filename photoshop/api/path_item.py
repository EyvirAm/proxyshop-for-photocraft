"""
* Photocraft PathItem compatibility (photoshop.api.path_item)
"""
from __future__ import annotations

from typing import Any

from photoshop.api._core import Photoshop


class PathItem(Photoshop):
    """Represents a vector path item in a Photocraft document."""

    def __init__(self, parent: Any = None, name: str = "Path 1") -> None:
        super().__init__(parent=parent)
        self.name = name
        self.subPathItems: list[Any] = []

    def select(self) -> None:
        """No-op: path selection is not implemented."""
        pass

    def deselect(self) -> None:
        """No-op: path deselection is not implemented."""
        pass

    def remove(self) -> None:
        """No-op: path removal is not implemented."""
        pass

    def strokePath(self, *args: Any, **kwargs: Any) -> None:
        """No-op: stroking paths is not implemented."""
        pass

    def fillPath(self, *args: Any, **kwargs: Any) -> None:
        """No-op: filling paths is not implemented."""
        pass

    def makeSelection(self, *args: Any, **kwargs: Any) -> None:
        """No-op: converting paths to selections is not implemented."""
        pass
