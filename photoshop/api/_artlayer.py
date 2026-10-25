"""
* Photocraft ArtLayer and ArtLayers compatibility (photoshop.api._artlayer)
"""
from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from photoshop.api._layer import Layer
from photoshop.api.enumerations import BlendMode, ElementPlacement, LayerKind
from photoshop.api.text_item import TextItem


_PS_FONT_MAP: dict[str, dict[str, Any]] = {
    "PlantinMTPro-Regular": {"font": "Plantin MT Pro", "italic": False, "weight": 400},
    "PlantinMTPro-Italic": {"font": "Plantin MT Pro", "italic": True, "weight": 400},
    "PlantinMTPro-Bold": {"font": "Plantin MT Pro", "italic": False, "weight": 700},
    "PlantinMTPro-SemiboldIt": {"font": "Plantin MT Pro", "italic": True, "weight": 600},
    "BelerenProxy-Bold": {"font": "Beleren Proxy", "italic": False, "weight": 700},
    "BelerenSmallCaps-Bold": {"font": "Beleren Small Caps", "italic": False, "weight": 700},
    "Gotham-Medium": {"font": "Gotham", "italic": False, "weight": 500},
    "Matrix-Bold": {"font": "Matrix", "italic": False, "weight": 700},
    "Proxyglyph": {"font": "Proxyglyph", "italic": False, "fauxItalic": False, "weight": 400},
    "NDPMTG": {"font": "NDPMTG", "italic": False, "fauxItalic": False, "weight": 400},
    "Magic:theGathering": {"font": "Magic:the Gathering", "italic": False, "weight": 400},
    "Keyrune": {"font": "Keyrune", "italic": False, "weight": 400},
}
class ArtLayer(Layer):
    """Represents a leaf layer (pixel, text, adjustment, shape, smart object) in Photocraft."""

    def __init__(
        self,
        parent: Any = None,
        name: str = "Layer 1",
        layer_id: int | None = None,
        bounds: tuple[float, float, float, float] = (0.0, 0.0, 100.0, 100.0),
        visible: bool = True,
        opacity: float = 100.0,
        blend_mode: BlendMode = BlendMode.NormalBlend,
        kind: LayerKind = LayerKind.NormalLayer,
    ) -> None:
        super().__init__(
            parent=parent,
            name=name,
            layer_id=layer_id,
            bounds=bounds,
            visible=visible,
            opacity=opacity,
            blend_mode=blend_mode,
            kind=kind,
        )
        if isinstance(parent, ArtLayer):
            self._text_item: TextItem | None = parent._text_item
        else:
            self._text_item = None

    @property
    def textItem(self) -> TextItem:
        if self._text_item is None:
            self._text_item = TextItem(parent=self)
        return self._text_item

    @textItem.setter
    def textItem(self, value: TextItem) -> None:
        self._text_item = value
        self._text_item.parent = self

    def _update_bounds_from_type_result(self, res: Any) -> None:
        if isinstance(res, dict):
            if isinstance(res.get("bounds"), list) and len(res["bounds"]) == 4:
                b = res["bounds"]
                self._bounds = (float(b[0]), float(b[1]), float(b[2]), float(b[3]))
            if isinstance(res.get("runs"), list):
                self._runs = res["runs"]
            if isinstance(res.get("lines"), list):
                self._type_lines = res["lines"]
            if isinstance(res.get("transform"), list) and len(res["transform"]) == 6:
                self._transform = [float(x) for x in res["transform"]]

    def _sync_text_to_photocraft(self) -> None:
        if self._text_item is not None:
            res = self._exec_photocraft(
                "type.edit",
                {
                    "layer": self._id,
                    "text": self._text_item.contents.replace("\r", "\n"),
                },
            )
            self._update_bounds_from_type_result(res)

    def _sync_style_to_photocraft(self, **kwargs: Any) -> None:
        params: dict[str, Any] = {"layer": self._id}
        if "font" in kwargs and kwargs["font"]:
            fn = str(kwargs["font"])
            if fn in _PS_FONT_MAP:
                params.update(_PS_FONT_MAP[fn])
            else:
                params["font"] = fn
        if "size" in kwargs and kwargs["size"] is not None:
            params["size"] = max(0.1, float(kwargs["size"]))
        if "leading" in kwargs and kwargs["leading"] is not None:
            params["leading"] = (
                "auto"
                if kwargs["leading"] == "auto"
                else max(0.1, float(kwargs["leading"]))
            )
        if "color" in kwargs and kwargs["color"] is not None:
            col = kwargs["color"]
            if hasattr(col, "rgb"):
                params["color"] = f"#{int(round(col.rgb.red)):02x}{int(round(col.rgb.green)):02x}{int(round(col.rgb.blue)):02x}"
            elif isinstance(col, str):
                params["color"] = col
        if "align" in kwargs:
            params["align"] = kwargs["align"]
        if "hyphenate" in kwargs:
            params["hyphenate"] = bool(kwargs["hyphenate"])
        if "baselineShift" in kwargs:
            params["baselineShift"] = float(kwargs["baselineShift"])
        if "tracking" in kwargs and kwargs["tracking"] is not None:
            params["tracking"] = int(round(float(kwargs["tracking"])))
        if "spaceBefore" in kwargs and kwargs["spaceBefore"] is not None:
            params["spaceBefore"] = float(kwargs["spaceBefore"])
        if "spaceAfter" in kwargs and kwargs["spaceAfter"] is not None:
            params["spaceAfter"] = float(kwargs["spaceAfter"])
        if "firstLineIndent" in kwargs and kwargs["firstLineIndent"] is not None:
            params["firstLineIndent"] = float(kwargs["firstLineIndent"])
        if "startIndent" in kwargs and kwargs["startIndent"] is not None:
            params["startIndent"] = float(kwargs["startIndent"])
        if "endIndent" in kwargs and kwargs["endIndent"] is not None:
            params["endIndent"] = float(kwargs["endIndent"])
        if "range" in kwargs and kwargs["range"] is not None:
            params["range"] = list(kwargs["range"])
        if "metricsAsShown" in kwargs:
            params["metricsAsShown"] = bool(kwargs["metricsAsShown"])

        if len(params) > 1:
            res = self._exec_photocraft("type.setStyle", params)
            self._update_bounds_from_type_result(res)

    def duplicate(
        self,
        relativeObject: Any = None,
        insertionLocation: ElementPlacement | None = None,
    ) -> ArtLayer:
        target_parent = (
            relativeObject
            if insertionLocation == ElementPlacement.PlaceInside
            and relativeObject is not None
            else (
                getattr(relativeObject, "parent", self.parent)
                if relativeObject is not None
                else self.parent
            )
        )
        rel_id = getattr(relativeObject, "id", None) if relativeObject is not None else None
        if rel_id is not None:
            if insertionLocation == ElementPlacement.PlaceInside:
                pos = "into"
            elif insertionLocation in (ElementPlacement.PlaceAfter, ElementPlacement.PlaceAtEnd):
                pos = "below"
            else:
                pos = "above"
            res = self._exec_photocraft(
                "layer.moveTo",
                {"layer": self._id, "target": rel_id, "position": pos, "copy": True},
            )
        else:
            res = self._exec_photocraft("layer.duplicate", {"layer": self._id})
        new_id = res.get("layer") if isinstance(res, dict) else None
        dup = ArtLayer(
            parent=target_parent,
            name=f"{self._name} copy",
            layer_id=new_id,
            bounds=self._bounds,
            visible=self._visible,
            opacity=self._opacity,
            blend_mode=self._blend_mode,
            kind=self._kind,
        )
        dup._doc = self._doc
        if self._doc is not None and hasattr(self._doc, "_layer_by_id") and new_id is not None:
            self._doc._layer_by_id[int(new_id)] = dup
        dup._transform = list(self._transform)
        dup._box = dict(self._box) if self._box else None
        dup._runs = [dict(r) for r in self._runs]
        dup._type_lines = [dict(ln) for ln in getattr(self, "_type_lines", [])]
        if self._text_item is not None:
            dup.textItem._contents = self._text_item._contents
            dup.textItem._font = self._text_item._font
            dup.textItem._size = self._text_item._size
            dup.textItem._color = self._text_item._color
            dup.textItem.leading = self._text_item.leading
        if target_parent is not None and hasattr(target_parent, "artLayers"):
            target_parent.artLayers._items.append(dup)
        return dup

    def rasterize(self, target: Any = None) -> None:
        if self._kind == LayerKind.TextLayer:
            self._exec_photocraft("type.rasterize", {"layer": self._id})
        else:
            self._exec_photocraft("layer.rasterize.layer", {"layer": self._id})
        self._kind = LayerKind.NormalLayer

    def merge(self) -> ArtLayer:
        self._exec_photocraft("layer.mergeDown", {"layer": self._id})
        return self

    def clear(self) -> None:
        self._exec_photocraft("edit.clear", {})

    def copy(self, merge: bool = False) -> None:
        self._exec_photocraft("edit.copyMerged" if merge else "edit.copy", {})

    def cut(self) -> None:
        self._exec_photocraft("edit.cut", {})

    def invert(self) -> None:
        self._exec_photocraft("image.adjustments.invert", {})

    def applyGaussianBlur(self, radius: float = 1.0) -> None:
        self._exec_photocraft("filter.blur.gaussianBlur", {"radius": float(radius)})


class ArtLayers:
    """Collection of ArtLayer objects inside a Document or LayerSet."""

    def __init__(self, parent: Any = None, items: list[ArtLayer] | None = None) -> None:
        self.parent = parent
        self._items: list[ArtLayer] = list(items) if items else []

    @property
    def app(self) -> ArtLayers:
        return self

    @property
    def length(self) -> int:
        return len(self._items)

    def __len__(self) -> int:
        return len(self._items)

    def __iter__(self) -> Iterator[ArtLayer]:
        return iter(self._items)

    def __getitem__(self, key: int | str) -> ArtLayer:
        if isinstance(key, int):
            return self._items[key]
        return self.getByName(key)

    def getByName(self, name: str) -> ArtLayer:
        for item in self._items:
            if item.name == name:
                return item
        for item in self._items:
            if item.name.lower() == name.lower():
                return item
        raise KeyError(f"ArtLayer '{name}' not found")

    def add(self) -> ArtLayer:
        doc = getattr(self.parent, "_doc", self.parent)
        new_id = None
        if doc is not None and hasattr(doc, "_exec_photocraft"):
            res = doc._exec_photocraft(
                "layer.new.layer", {"name": f"Layer {len(self._items) + 1}"}
            )
            if isinstance(res, dict) and "layer" in res:
                new_id = int(res["layer"])
        layer = ArtLayer(
            parent=self.parent,
            name=f"Layer {len(self._items) + 1}",
            layer_id=new_id,
        )
        self._items.insert(0, layer)
        if doc is not None:
            doc._active_layer = layer
        return layer

    def removeAll(self) -> None:
        self._items.clear()
