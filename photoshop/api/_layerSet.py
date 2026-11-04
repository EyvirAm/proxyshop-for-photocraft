"""
* Photocraft LayerSet and LayerSets compatibility (photoshop.api._layerSet)
"""
from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from photoshop.api._artlayer import ArtLayer, ArtLayers
from photoshop.api._layer import Layer
from photoshop.api.enumerations import BlendMode, ElementPlacement, LayerKind


class LayerSet(Layer):
    """Represents a layer group/folder in Photocraft."""

    def __init__(
        self,
        parent: Any = None,
        name: str = "Group 1",
        layer_id: int | None = None,
        bounds: tuple[float, float, float, float] = (0.0, 0.0, 100.0, 100.0),
        visible: bool = True,
        opacity: float = 100.0,
        blend_mode: BlendMode = BlendMode.PassThrough,
    ) -> None:
        super().__init__(
            parent=parent,
            name=name,
            layer_id=layer_id,
            bounds=bounds,
            visible=visible,
            opacity=opacity,
            blend_mode=blend_mode,
            kind=LayerKind.NormalLayer,
        )
        self.artLayers = ArtLayers(parent=self)
        self.layerSets = LayerSets(parent=self)

    @property
    def layers(self) -> list[ArtLayer | LayerSet]:
        """Layers and nested groups inside this set."""
        return [*self.artLayers._items, *self.layerSets._items]

    def _remove_child(self, child: Layer) -> None:
        if child in self.artLayers._items:
            self.artLayers._items.remove(child)  # type: ignore[arg-type]
        elif child in self.layerSets._items:
            self.layerSets._items.remove(child)  # type: ignore[arg-type]

    @property
    def bounds(self) -> tuple[float, float, float, float]:
        """Combined bounds of the visible children."""
        vis_bounds: list[tuple[float, float, float, float]] = []
        all_bounds: list[tuple[float, float, float, float]] = []
        for art in self.artLayers._items:
            b = art.bounds
            if b[2] > b[0] and b[3] > b[1]:
                all_bounds.append(b)
                if art.visible:
                    vis_bounds.append(b)
        for grp in self.layerSets._items:
            b = grp.bounds
            if b[2] > b[0] and b[3] > b[1]:
                all_bounds.append(b)
                if grp.visible:
                    vis_bounds.append(b)
        chosen = vis_bounds or all_bounds
        if chosen:
            return (
                min(b[0] for b in chosen),
                min(b[1] for b in chosen),
                max(b[2] for b in chosen),
                max(b[3] for b in chosen),
            )
        return self._bounds

    @bounds.setter
    def bounds(self, value: tuple[float, float, float, float]) -> None:
        """Update the cached group bounds."""
        self._bounds = value

    def _shift_children_bounds(self, dx: int, dy: int) -> None:
        for art in self.artLayers._items:
            l, t, r, b = art._bounds
            art._bounds = (l + dx, t + dy, r + dx, b + dy)
        for grp in self.layerSets._items:
            l, t, r, b = grp._bounds
            grp._bounds = (l + dx, t + dy, r + dx, b + dy)
            grp._shift_children_bounds(dx, dy)

    def translate(self, delta_x: float = 0.0, delta_y: float = 0.0) -> None:
        """Move the group and all of its children."""
        dx = int(round(delta_x))
        dy = int(round(delta_y))
        if dx == 0 and dy == 0:
            return
        super().translate(dx, dy)
        self._shift_children_bounds(dx, dy)

    def _clone_tree(self, target_parent: Any, new_id: int | None = None) -> LayerSet:
        dup = LayerSet(
            parent=target_parent,
            name=f"{self._name} copy",
            layer_id=new_id,
            bounds=self._bounds,
            visible=self._visible,
            opacity=self._opacity,
            blend_mode=self._blend_mode,
        )
        dup._doc = self._doc
        if self._doc is not None and hasattr(self._doc, "_layer_by_id") and new_id is not None:
            self._doc._layer_by_id[int(new_id)] = dup
        for art in list(self.artLayers._items):
            art_dup = ArtLayer(
                parent=dup,
                name=art._name,
                layer_id=None,
                bounds=art._bounds,
                visible=art._visible,
                opacity=art._opacity,
                blend_mode=art._blend_mode,
                kind=art._kind,
            )
            art_dup._doc = self._doc
            art_dup._transform = list(art._transform)
            art_dup._box = dict(art._box) if art._box else None
            art_dup._runs = [dict(r) for r in art._runs]
            art_dup._type_lines = [dict(ln) for ln in getattr(art, "_type_lines", [])]
            if art._text_item is not None:
                art_dup.textItem._contents = art._text_item._contents
                art_dup.textItem._font = art._text_item._font
                art_dup.textItem._size = art._text_item._size
                art_dup.textItem._color = art._text_item._color
                art_dup.textItem.leading = art._text_item.leading
            dup.artLayers._items.append(art_dup)
        for grp in list(self.layerSets._items):
            dup.layerSets._items.append(grp._clone_tree(dup, None))
        return dup

    def duplicate(
        self,
        relativeObject: Any = None,
        insertionLocation: ElementPlacement | None = None,
    ) -> LayerSet:
        """Duplicate the group, optionally relative to another layer."""
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
        dup = (
            self._clone_from_backend(target_parent, int(new_id))
            if new_id is not None
            else self._clone_tree(target_parent, new_id)
        )
        if target_parent is not None and hasattr(target_parent, "layerSets"):
            target_parent.layerSets._items.append(dup)
        return dup

    def _clone_from_backend(self, target_parent: Any, new_id: int) -> LayerSet:
        """Build a duplicate group wired to the backend's real layer ids and texts."""
        doc = self._doc
        node: dict[str, Any] | None = None

        def find(items: list[dict[str, Any]]) -> dict[str, Any] | None:
            """Find."""
            for item in items:
                if int(item.get("id", -1)) == new_id:
                    return item
                found = find(item.get("children") or [])
                if found is not None:
                    return found
            return None

        if doc is not None and hasattr(doc, "inspect_layers_raw"):
            node = find(doc.inspect_layers_raw())
        if node is None:
            return self._clone_tree(target_parent, new_id)
        b = node.get("bounds")
        bounds = (
            (float(b[0]), float(b[1]), float(b[0] + b[2]), float(b[1] + b[3]))
            if isinstance(b, list) and len(b) == 4
            else self._bounds
        )
        dup = LayerSet(
            parent=target_parent,
            name=str(node.get("name", f"{self._name} copy")),
            layer_id=new_id,
            bounds=bounds,
            visible=bool(node.get("visible", True)),
            opacity=self._opacity,
            blend_mode=self._blend_mode,
        )
        dup._doc = doc
        if doc is not None and hasattr(doc, "_layer_by_id"):
            doc._layer_by_id[new_id] = dup
        children = node.get("children")
        if isinstance(children, list) and hasattr(doc, "_populate_layers_from_photocraft_json"):
            doc._populate_layers_from_photocraft_json(children, dup)
        elif isinstance(children, list):
            self._clone_tree(target_parent, new_id)
        return dup

    def merge(self) -> ArtLayer:
        """Merge the group into a single art layer."""
        self._exec_photocraft("layer.mergeGroup", {"layer": self._id})
        art = ArtLayer(
            parent=self.parent,
            name=self._name,
            layer_id=self._id,
            bounds=self._bounds,
            visible=self._visible,
            opacity=self._opacity,
        )
        if self.parent is not None and hasattr(self.parent, "artLayers"):
            self.parent.artLayers._items.append(art)
        if self.parent is not None and hasattr(self.parent, "_remove_child"):
            self.parent._remove_child(self)
        return art


class LayerSets:
    """Collection of LayerSet objects inside a Document or LayerSet."""

    def __init__(self, parent: Any = None, items: list[LayerSet] | None = None) -> None:
        self.parent = parent
        self._items: list[LayerSet] = list(items) if items else []

    @property
    def app(self) -> LayerSets:
        """The collection itself, mirroring the Photoshop API."""
        return self

    @property
    def length(self) -> int:
        """Number of layer groups in the collection."""
        return len(self._items)

    def __len__(self) -> int:
        return len(self._items)

    def __iter__(self) -> Iterator[LayerSet]:
        return iter(self._items)

    def __getitem__(self, key: int | str) -> LayerSet:
        if isinstance(key, int):
            return self._items[key]
        return self.getByName(key)

    def getByName(self, name: str) -> LayerSet:
        """Return a group by name, falling back to a case-insensitive match."""
        for item in self._items:
            if item.name == name:
                return item
        for item in self._items:
            if item.name.lower() == name.lower():
                return item
        raise KeyError(f"LayerSet '{name}' not found")

    def add(self) -> LayerSet:
        """Create a new, empty layer group at the top of the collection."""
        grp = LayerSet(parent=self.parent, name=f"Group {len(self._items) + 1}")
        self._items.insert(0, grp)
        return grp

    def removeAll(self) -> None:
        """Remove every group from the collection."""
        self._items.clear()
