"""
* Photocraft Selection compatibility (photoshop.api._selection)
"""
from __future__ import annotations

from typing import Any

from photoshop.api._core import Photoshop


class Selection(Photoshop):
    """Represents a document selection routed to Photocraft."""

    def __init__(self, parent: Any = None) -> None:
        super().__init__(parent=parent)
        self._bounds: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
        self._inverted: bool = False
        self.solid: bool = True

    @property
    def bounds(self) -> tuple[float, float, float, float]:
        """Selection bounds as ``(left, top, right, bottom)``."""
        return self._bounds

    @bounds.setter
    def bounds(self, value: tuple[float, float, float, float]) -> None:
        """Update the cached selection bounds."""
        self._bounds = value

    def select(self, region: list[list[float]] | list[tuple[float, float]], *args: Any, **kwargs: Any) -> None:
        """Select the rectangular region enclosing the given points."""
        if region:
            xs = [pt[0] for pt in region]
            ys = [pt[1] for pt in region]
            self._bounds = (min(xs), min(ys), max(xs), max(ys))
            self._inverted = False
            if self.parent is not None and hasattr(self.parent, "_exec_photocraft"):
                w = max(1, int(self._bounds[2] - self._bounds[0]))
                h = max(1, int(self._bounds[3] - self._bounds[1]))
                self.parent._exec_photocraft(
                    "select.rect",
                    {
                        "x": int(self._bounds[0]),
                        "y": int(self._bounds[1]),
                        "width": w,
                        "height": h,
                        "mode": "replace",
                        "ellipse": False,
                    },
                )

    def selectAll(self) -> None:
        """Select the whole canvas."""
        if self.parent is not None:
            w = getattr(self.parent, "width", 3264)
            h = getattr(self.parent, "height", 4440)
            self._bounds = (0.0, 0.0, float(w), float(h))
            self._inverted = False
            if hasattr(self.parent, "_exec_photocraft"):
                self.parent._exec_photocraft("select.all", {})

    def deselect(self) -> None:
        """Clear the current selection."""
        self._bounds = (0.0, 0.0, 0.0, 0.0)
        self._inverted = False
        if self.parent is not None and hasattr(self.parent, "_exec_photocraft"):
            self.parent._exec_photocraft("select.deselect", {})

    def invert(self) -> None:
        """Invert the current selection."""
        self._inverted = not self._inverted
        if self.parent is not None and hasattr(self.parent, "_exec_photocraft"):
            self.parent._exec_photocraft("select.inverse", {})

    def copy(self, merge: bool = False) -> None:
        """Copy the selection, optionally merging visible layers."""
        if self.parent is not None and hasattr(self.parent, "_exec_photocraft"):
            cmd = "edit.copyMerged" if merge else "edit.copy"
            self.parent._exec_photocraft(cmd, {})

    def cut(self) -> None:
        """Cut the selection to the clipboard."""
        if self.parent is not None and hasattr(self.parent, "_exec_photocraft"):
            self.parent._exec_photocraft("edit.cut", {})

    def clear(self) -> None:
        """Clear the pixels inside the selection."""
        if self.parent is not None and hasattr(self.parent, "_exec_photocraft"):
            l, t, r, b = self._bounds
            if not self._inverted and b > t and r > l:
                doc_w = int(getattr(self.parent, "width", 3264))
                self.parent._exec_photocraft(
                    "select.rect",
                    {
                        "x": 0,
                        "y": max(0, int(round(t)) - 20),
                        "width": doc_w,
                        "height": int(round(b - max(0, int(round(t)) - 20))) + 10,
                        "mode": "replace",
                        "ellipse": False,
                    },
                )
            self.parent._exec_photocraft("edit.clear", {})
            active = getattr(self.parent, "_active_layer", None)
            if active is not None:
                type_lines = getattr(active, "_type_lines", None)
                if isinstance(type_lines, list) and len(type_lines) >= 2:
                    orig_l, orig_t, orig_r, orig_b = active._bounds
                    tr = getattr(active, "_transform", [1.0, 0.0, 0.0, 1.0, 0.0, 0.0])
                    yy = float(tr[3]) if float(tr[3]) > 0 else 1.0
                    b0 = float(type_lines[0].get("baseline", 0.0))
                    for ln in type_lines[1:]:
                        bk = float(ln.get("baseline", 0.0))
                        line_top = orig_t + (bk - b0) * yy
                        if line_top >= b - 30:
                            active._bounds = (orig_l, line_top, orig_r, orig_b)
                            return
                ll = self.parent._exec_photocraft("layer.list", {"flat": True})
                if isinstance(ll, dict) and isinstance(ll.get("layers"), list):
                    for lyr in ll["layers"]:
                        if lyr.get("id") == active.id and isinstance(lyr.get("bounds"), list):
                            b_arr = lyr["bounds"]
                            if len(b_arr) == 4:
                                active._bounds = (
                                    float(b_arr[0]),
                                    float(b_arr[1]),
                                    float(b_arr[0] + b_arr[2]),
                                    float(b_arr[1] + b_arr[3]),
                                )
                            break

    def fill(self, fill_type: Any, *args: Any, **kwargs: Any) -> None:
        """Fill the selection with the color carried by ``fill_type``."""
        if self.parent is not None and hasattr(self.parent, "_exec_photocraft"):
            color_hex = "#000000"
            if hasattr(fill_type, "rgb"):
                color_hex = f"#{int(fill_type.rgb.red):02x}{int(fill_type.rgb.green):02x}{int(fill_type.rgb.blue):02x}"
            self.parent._exec_photocraft(
                "edit.fill", {"contents": "color", "color": color_hex}
            )

    def stroke(self, color: Any, width: int = 1, *args: Any, **kwargs: Any) -> None:
        """No-op: stroking selections is not implemented."""
        pass

    def expand(self, by: float) -> None:
        """Expand the selection by ``by`` pixels on every side."""
        l, t, r, b = self._bounds
        self._bounds = (l - by, t - by, r + by, b + by)
        if self.parent is not None and hasattr(self.parent, "_exec_photocraft"):
            w = max(1, int(round(self._bounds[2] - self._bounds[0])))
            h = max(1, int(round(self._bounds[3] - self._bounds[1])))
            self.parent._exec_photocraft(
                "select.rect",
                {
                    "x": int(round(self._bounds[0])),
                    "y": int(round(self._bounds[1])),
                    "width": w,
                    "height": h,
                    "mode": "replace",
                    "ellipse": False,
                },
            )

    def contract(self, by: float) -> None:
        """Contract the selection by ``by`` pixels."""
        if self.parent is not None and hasattr(self.parent, "_exec_photocraft"):
            self.parent._exec_photocraft("select.modify.contract", {"by": int(by)})

    def feather(self, by: float) -> None:
        """Feather the selection edge by ``by`` pixels."""
        if self.parent is not None and hasattr(self.parent, "_exec_photocraft"):
            self.parent._exec_photocraft("select.modify.feather", {"radius": float(by)})

    def grow(self, tolerance: int, anti_alias: bool = True) -> None:
        """No-op: growing selections is not implemented."""
        pass

    def similar(self, tolerance: int, anti_alias: bool = True) -> None:
        """No-op: selecting similar pixels is not implemented."""
        pass

    def translate(self, delta_x: float = 0.0, delta_y: float = 0.0) -> None:
        """Move the selection bounds by the given delta."""
        l, t, r, b = self._bounds
        self._bounds = (l + delta_x, t + delta_y, r + delta_x, b + delta_y)

    def translateBoundary(self, delta_x: float = 0.0, delta_y: float = 0.0) -> None:
        """Alias of :meth:`translate` for boundary-only moves."""
        self.translate(delta_x, delta_y)

    def resize(self, horizontal: float = 100.0, vertical: float = 100.0, anchor: Any = None) -> None:
        """No-op: resizing selections is not implemented."""
        pass

    def resizeBoundary(self, horizontal: float = 100.0, vertical: float = 100.0, anchor: Any = None) -> None:
        """No-op: resizing selection boundaries is not implemented."""
        pass

    def rotate(self, angle: float, anchor: Any = None) -> None:
        """No-op: rotating selections is not implemented."""
        pass

    def rotateBoundary(self, angle: float, anchor: Any = None) -> None:
        """No-op: rotating selection boundaries is not implemented."""
        pass
