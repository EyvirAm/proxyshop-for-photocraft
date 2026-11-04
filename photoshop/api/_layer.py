"""
* Photocraft Layer base class (photoshop.api._layer)
"""
from __future__ import annotations

import itertools
from typing import Any

from photoshop.api._core import Photoshop
from photoshop.api.enumerations import AnchorPosition, BlendMode, ElementPlacement, LayerKind

_LAYER_ID_COUNTER = itertools.count(10000)


class Layer(Photoshop):
    """Base layer class for Photocraft ArtLayer and LayerSet."""

    def __init__(
        self,
        parent: Any = None,
        name: str = "Layer",
        layer_id: int | None = None,
        bounds: tuple[float, float, float, float] = (0.0, 0.0, 100.0, 100.0),
        visible: bool = True,
        opacity: float = 100.0,
        blend_mode: BlendMode = BlendMode.NormalBlend,
        kind: LayerKind = LayerKind.NormalLayer,
    ) -> None:
        from photoshop.api._artlayer import ArtLayer as _ArtLayer

        if isinstance(parent, _ArtLayer):
            super().__init__(parent=parent.parent)
            self._id: int = parent._id
            self._name: str = parent._name
            self._bounds: tuple[float, float, float, float] = parent._bounds
            self._visible: bool = parent._visible
            self._opacity: float = parent._opacity
            self.fillOpacity: float = parent.fillOpacity
            self._blend_mode: BlendMode = parent._blend_mode
            self._kind: LayerKind = parent._kind
            self._doc: Any = parent._doc
            self.allLocked: bool = parent.allLocked
            self.pixelsLocked: bool = parent.pixelsLocked
            self.positionLocked: bool = parent.positionLocked
            self.transparentPixelsLocked: bool = parent.transparentPixelsLocked
            self.grouped: bool = parent.grouped
            self.isBackgroundLayer: bool = parent.isBackgroundLayer
            self._psd_layer: Any = getattr(parent, "_psd_layer", None)
            self._pil_image: Any = getattr(parent, "_pil_image", None)
            self._transform: list[float] = list(
                getattr(parent, "_transform", [1.0, 0.0, 0.0, 1.0, 0.0, 0.0])
            )
            self._box: dict[str, float] | None = getattr(parent, "_box", None)
            self._runs: list[dict[str, Any]] = list(getattr(parent, "_runs", []))
        else:
            super().__init__(parent=parent)
            self._id = layer_id if layer_id is not None else next(_LAYER_ID_COUNTER)
            self._name = name
            self._bounds = bounds
            self._visible = visible
            self._opacity = opacity
            self.fillOpacity = 100.0
            self._blend_mode = blend_mode
            self._kind = kind
            self._doc = getattr(parent, "_doc", parent)
            self.allLocked = False
            self.pixelsLocked = False
            self.positionLocked = False
            self.transparentPixelsLocked = False
            self.grouped = False
            self.isBackgroundLayer = False
            self._psd_layer = None
            self._pil_image = None
            self._transform = [1.0, 0.0, 0.0, 1.0, 0.0, 0.0]
            self._box = None
            self._runs = []

    def _exec_photocraft(self, command: str, params: dict[str, Any]) -> Any:
        if self._doc is not None and hasattr(self._doc, "_exec_photocraft"):
            return self._doc._exec_photocraft(command, params)
        return None

    @property
    def id(self) -> int:
        """Numeric layer identifier."""
        return self._id

    @property
    def name(self) -> str:
        """Layer name."""
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        """Rename the layer in PhotoCraft."""
        self._name = str(value)
        self._exec_photocraft(
            "layer.setProps", {"layer": self._id, "name": self._name}
        )

    @property
    def visible(self) -> bool:
        """Whether the layer is visible."""
        return self._visible

    @visible.setter
    def visible(self, value: bool) -> None:
        """Show or hide the layer in PhotoCraft."""
        self._visible = bool(value)
        self._exec_photocraft(
            "layer.setProps", {"layer": self._id, "visible": self._visible}
        )

    @property
    def opacity(self) -> float:
        """Layer opacity as a percentage (0-100)."""
        return self._opacity

    @opacity.setter
    def opacity(self, value: float) -> None:
        """Set the layer opacity, clamped to 0-100."""
        self._opacity = float(value)
        self._exec_photocraft(
            "layer.setProps",
            {"layer": self._id, "opacity": max(0.0, min(1.0, self._opacity / 100.0))},
        )

    @property
    def blendMode(self) -> BlendMode:
        """Blend mode used by the layer."""
        return self._blend_mode

    @blendMode.setter
    def blendMode(self, value: BlendMode) -> None:
        """Set the layer blend mode."""
        self._blend_mode = value

    @property
    def kind(self) -> LayerKind:
        """Layer kind (normal, text, adjustment, etc.)."""
        return self._kind

    @kind.setter
    def kind(self, value: LayerKind) -> None:
        """Set the layer kind."""
        self._kind = value

    @property
    def bounds(self) -> tuple[float, float, float, float]:
        """Layer bounds as ``(left, top, right, bottom)``."""
        return self._bounds

    @bounds.setter
    def bounds(self, value: tuple[float, float, float, float]) -> None:
        """Update the cached layer bounds."""
        self._bounds = value

    @property
    def boundsNoEffects(self) -> tuple[float, float, float, float]:
        """Layer bounds ignoring layer effects."""
        return self._bounds

    def translate(self, delta_x: float = 0.0, delta_y: float = 0.0) -> None:
        """Move the layer by the given delta, rounded to whole pixels."""
        dx = int(round(delta_x))
        dy = int(round(delta_y))
        if dx == 0 and dy == 0:
            return
        l, t, r, b = self._bounds
        self._bounds = (l + dx, t + dy, r + dx, b + dy)
        self._exec_photocraft(
            "layer.translate",
            {"layer": self._id, "dx": dx, "dy": dy},
        )

    def resize(
        self,
        horizontal: float = 100.0,
        vertical: float = 100.0,
        anchor: Any = None,
    ) -> None:
        """Scale the layer around its center by the given percentages."""
        l, t, r, b = self._bounds
        w = (r - l) * (horizontal / 100.0)
        h = (b - t) * (vertical / 100.0)
        cx = (l + r) / 2.0
        cy = (t + b) / 2.0
        nl, nt, nr, nb = (cx - w / 2.0, cy - h / 2.0, cx + w / 2.0, cy + h / 2.0)
        self._bounds = (nl, nt, nr, nb)
        self._exec_photocraft(
            "edit.transform",
            {
                "layer": self._id,
                "rect": [l, t, r, b],
                "quad": [[nl, nt], [nr, nt], [nr, nb], [nl, nb]],
            },
        )

    def rotate(self, angle: float, anchor: Any = None) -> None:
        """Rotate the layer by ``angle`` degrees."""
        self._exec_photocraft(
            "edit.transform",
            {"layer": self._id, "rotate": float(angle)},
        )

    def move(
        self, relativeObject: Any, insertionLocation: ElementPlacement
    ) -> None:
        """Move the layer relative to another layer or group."""
        target_id = getattr(relativeObject, "id", None)
        if target_id is None:
            return
        if insertionLocation in (
            ElementPlacement.PlaceBefore,
            ElementPlacement.PlaceAtBeginning,
        ):
            pos = "above"
        elif insertionLocation == ElementPlacement.PlaceInside:
            pos = "into"
        else:
            pos = "below"
        self._exec_photocraft(
            "layer.moveTo",
            {"layer": self._id, "target": target_id, "position": pos},
        )

    def remove(self) -> None:
        """Delete the layer from the document."""
        self._exec_photocraft("layer.delete", {"layer": self._id})
        if self.parent is not None and hasattr(self.parent, "_remove_child"):
            self.parent._remove_child(self)

    def delete(self) -> None:
        """Alias of :meth:`remove`."""
        self.remove()

    def unlink(self) -> None:
        """No-op: links are not supported by PhotoCraft."""
        pass

    def link(self, with_layer: Any) -> None:
        """No-op: links are not supported by PhotoCraft."""
        pass
