"""
* Photocraft TextItem compatibility (photoshop.api.text_item)
"""
from __future__ import annotations

from typing import Any

from photoshop.api._core import Photoshop
from photoshop.api.enumerations import AutoKernType, Justification, Language


class TextItem(Photoshop):
    """Represents editable text attributes of a Photocraft text layer."""

    def __init__(
        self,
        parent: Any = None,
        contents: str = "",
        font: str = "BelerenProxy-Bold",
        size: float = 12.0,
        color: Any = None,
    ) -> None:
        super().__init__(parent=parent)
        self._contents = contents
        self._font = font
        self._size = size
        self._color = color
        self.position: tuple[float, float] = (0.0, 0.0)
        self._justification: Justification = Justification.Left
        self.autoKerning: AutoKernType = AutoKernType.Metrics
        self.leading: float | str = 12.0
        self.useAutoLeading: bool = True
        self.tracking: float = 0.0
        self.horizontalScale: float = 100.0
        self.verticalScale: float = 100.0
        self._baseline_shift: float = 0.0
        self.fauxBold: bool = False
        self.fauxItalic: bool = False
        self._hyphenation: bool = False
        self.language: Language = Language.EnglishUSA
        self.spaceAfter: float = 0.0
        self.spaceBefore: float = 0.0
        self.width: float = 200.0
        self.height: float = 50.0
        self.kind: int = 1  # PointText = 1, ParagraphText = 2

    @property
    def contents(self) -> str:
        return self._contents

    @contents.setter
    def contents(self, value: str) -> None:
        self._contents = str(value)
        if self.parent is not None and hasattr(self.parent, "_sync_text_to_photocraft"):
            self.parent._sync_text_to_photocraft()

    @property
    def font(self) -> str:
        return self._font

    @font.setter
    def font(self, value: str) -> None:
        self._font = str(value)
        if self.parent is not None and hasattr(self.parent, "_sync_style_to_photocraft"):
            self.parent._sync_style_to_photocraft(font=self._font)

    @property
    def size(self) -> float:
        return self._size

    @size.setter
    def size(self, value: float) -> None:
        self._size = float(value)
        if self.parent is not None and hasattr(self.parent, "_sync_style_to_photocraft"):
            self.parent._sync_style_to_photocraft(size=self._size)

    @property
    def color(self) -> Any:
        if self._color is None:
            from photoshop.api import SolidColor

            self._color = SolidColor()
        return self._color

    @color.setter
    def color(self, value: Any) -> None:
        self._color = value
        if self.parent is not None and hasattr(self.parent, "_sync_style_to_photocraft"):
            self.parent._sync_style_to_photocraft(color=self._color)

    @property
    def justification(self) -> Justification:
        return self._justification

    @justification.setter
    def justification(self, value: Justification) -> None:
        self._justification = value
        align_map = {
            Justification.Left: "left",
            Justification.Center: "center",
            Justification.Right: "right",
            Justification.LeftJustified: "justify",
            Justification.CenterJustified: "justifyCenter",
            Justification.RightJustified: "justifyRight",
            Justification.FullyJustified: "justifyAll",
        }
        if self.parent is not None and hasattr(self.parent, "_sync_style_to_photocraft"):
            self.parent._sync_style_to_photocraft(
                align=align_map.get(value, "left")
            )

    @property
    def hyphenation(self) -> bool:
        return self._hyphenation

    @hyphenation.setter
    def hyphenation(self, value: bool) -> None:
        self._hyphenation = bool(value)
        if self.parent is not None and hasattr(self.parent, "_sync_style_to_photocraft"):
            self.parent._sync_style_to_photocraft(hyphenate=self._hyphenation)

    @property
    def baselineShift(self) -> float:
        return self._baseline_shift

    @baselineShift.setter
    def baselineShift(self, value: float) -> None:
        self._baseline_shift = float(value)
        if self.parent is not None and hasattr(self.parent, "_sync_style_to_photocraft"):
            self.parent._sync_style_to_photocraft(baselineShift=self._baseline_shift)
