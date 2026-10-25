"""
* Photocraft Document and Documents compatibility (photoshop.api._document)
"""
from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

from PIL import Image
from photoshop.api._artlayer import ArtLayer, ArtLayers
from photoshop.api._core import Photoshop
from photoshop.api._layerSet import LayerSet, LayerSets
from photoshop.api._selection import Selection
from photoshop.api.enumerations import LayerKind, SaveOptions
from photoshop.api.path_item import PathItem


class Document(Photoshop):
    """Represents an open document backed by Photocraft and psd-tools/Pillow."""

    def __init__(
        self,
        parent: Any = None,
        file_path: str | Path | None = None,
        width: int = 3264,
        height: int = 4440,
        resolution: float = 1200.0,
        name: str = "Untitled-1",
    ) -> None:
        super().__init__(parent=parent)
        self._doc = self
        self._file_path = Path(file_path) if file_path else None
        self.name = self._file_path.name if self._file_path else name
        self.width = width
        self.height = height
        self.resolution = resolution
        self.saved = bool(self._file_path)
        self.bitsPerChannel = 8
        self.artLayers = ArtLayers(parent=self)
        self.layerSets = LayerSets(parent=self)
        self.selection = Selection(parent=self)
        self._active_layer: ArtLayer | LayerSet | None = None
        self._layer_by_id: dict[int, ArtLayer | LayerSet] = {}
        self.pathItems: list[PathItem] = []
        self.historyStates: list[Any] = []
        self.activeHistoryState: Any = None
        self._psd_image: Any = None
        self._pil_image: Image.Image | None = None

        if self._file_path and self._file_path.exists():
            self._load_from_disk(self._file_path)
        else:
            default_layer = ArtLayer(
                parent=self,
                name="Background",
                bounds=(0.0, 0.0, float(self.width), float(self.height)),
            )
            default_layer.isBackgroundLayer = True
            self.artLayers._items.append(default_layer)
            self._layer_by_id[default_layer.id] = default_layer
            self._active_layer = default_layer

    def find_layer_by_id(self, layer_id: int) -> ArtLayer | LayerSet | None:
        if layer_id in self._layer_by_id:
            return self._layer_by_id[layer_id]

        def _walk(container: Document | LayerSet) -> ArtLayer | LayerSet | None:
            for a in container.artLayers._items:
                self._layer_by_id[a.id] = a
                if a.id == layer_id:
                    return a
            for g in container.layerSets._items:
                self._layer_by_id[g.id] = g
                if g.id == layer_id:
                    return g
                found = _walk(g)
                if found is not None:
                    return found
            return None

        return _walk(self)

    @property
    def fullName(self) -> str:
        return str(self._file_path) if self._file_path else self.name

    @property
    def path(self) -> str:
        return str(self._file_path.parent) if self._file_path else "."

    @property
    def layers(self) -> list[ArtLayer | LayerSet]:
        return [*self.artLayers._items, *self.layerSets._items]

    @property
    def activeLayer(self) -> ArtLayer | LayerSet:
        if self._active_layer is None:
            if self.artLayers._items:
                self._active_layer = self.artLayers._items[0]
            elif self.layerSets._items:
                self._active_layer = self.layerSets._items[0]
            else:
                self._active_layer = self.artLayers.add()
        return self._active_layer

    @activeLayer.setter
    def activeLayer(self, layer: ArtLayer | LayerSet) -> None:
        self._active_layer = layer
        self._exec_photocraft("layer.select", {"layer": layer.id, "mode": "replace"})

    def _exec_photocraft(self, command: str, params: dict[str, Any]) -> Any:
        if self.app is not None and hasattr(self.app, "photocraft_execute"):
            return self.app.photocraft_execute(command, params)
        return None

    def _remove_child(self, child: Any) -> None:
        if child in self.artLayers._items:
            self.artLayers._items.remove(child)
        elif child in self.layerSets._items:
            self.layerSets._items.remove(child)
        self._layer_by_id.pop(getattr(child, "id", -1), None)

    def _load_from_disk(self, path: Path) -> None:
        # 1. Open in Photocraft backend first
        if self.app is not None and hasattr(self.app, "photocraft_open"):
            info = self.app.photocraft_open(path)
            if isinstance(info, dict):
                self.width = int(info.get("width", self.width))
                self.height = int(info.get("height", self.height))
                res = info.get("resolution") or info.get("dpi")
                if res:
                    self.resolution = float(res)
                if "layers" in info and isinstance(info["layers"], list):
                    self._populate_layers_from_photocraft_json(info["layers"], self)
                    return

        # 2. Fallback: Load via psd-tools for .psd/.psb or Pillow for raster images
        suffix = path.suffix.lower()
        if suffix in (".psd", ".psb"):
            try:
                from psd_tools import PSDImage

                psd = PSDImage.open(str(path))
                self._psd_image = psd
                self.width = psd.width
                self.height = psd.height
                self._populate_layers_from_psd(psd, self)
                return
            except Exception:
                pass

        try:
            img = Image.open(str(path))
            self._pil_image = img.copy()
            self.width, self.height = img.size
            dpi = img.info.get("dpi")
            if dpi and isinstance(dpi, tuple) and dpi[0] > 0:
                self.resolution = float(dpi[0])
            layer = ArtLayer(
                parent=self,
                name=path.stem,
                bounds=(0.0, 0.0, float(self.width), float(self.height)),
            )
            layer._pil_image = self._pil_image
            self.artLayers._items.append(layer)
            self._layer_by_id[layer.id] = layer
            self._active_layer = layer
        except Exception:
            layer = ArtLayer(
                parent=self,
                name="Layer 1",
                bounds=(0.0, 0.0, float(self.width), float(self.height)),
            )
            self.artLayers._items.append(layer)
            self._layer_by_id[layer.id] = layer
            self._active_layer = layer

    def _populate_layers_from_photocraft_json(
        self, layers_json: list[dict[str, Any]], container: Document | LayerSet
    ) -> None:
        from photoshop.api import SolidColor

        for item in layers_json:
            lid = item.get("id")
            name = item.get("name", "Layer")
            visible = bool(item.get("visible", True))
            raw_op = float(item.get("opacity", 1.0))
            opacity = raw_op * 100.0 if raw_op <= 1.0 else raw_op
            b = item.get("bounds")
            if isinstance(b, list) and len(b) == 4:
                bounds = (
                    float(b[0]),
                    float(b[1]),
                    float(b[0] + b[2]),
                    float(b[1] + b[3]),
                )
            else:
                bounds = (0.0, 0.0, float(self.width), float(self.height))
            kind_str = str(item.get("kind", "pixel")).lower()
            children = item.get("children")
            if children is not None or kind_str == "group":
                grp = LayerSet(
                    parent=container,
                    name=name,
                    layer_id=lid,
                    bounds=bounds,
                    visible=visible,
                    opacity=opacity,
                )
                grp._doc = self
                container.layerSets._items.append(grp)
                if lid is not None:
                    self._layer_by_id[int(lid)] = grp
                if isinstance(children, list):
                    self._populate_layers_from_photocraft_json(children, grp)
            else:
                if kind_str == "type":
                    kind = LayerKind.TextLayer
                elif kind_str == "shape":
                    kind = LayerKind.SolidFillLayer
                elif kind_str in ("smartobject", "smart"):
                    kind = LayerKind.SmartObjectLayer
                else:
                    kind = LayerKind.NormalLayer

                art = ArtLayer(
                    parent=container,
                    name=name,
                    layer_id=lid,
                    bounds=bounds,
                    visible=visible,
                    opacity=opacity,
                    kind=kind,
                )
                art._doc = self
                if kind == LayerKind.TextLayer and lid is not None:
                    ti = self._exec_photocraft("type.info", {"layer": int(lid)})
                    if isinstance(ti, dict):
                        txt = str(ti.get("text", "")).replace("\n", "\r")
                        art.textItem._contents = txt
                        tb = ti.get("bounds")
                        if isinstance(tb, list) and len(tb) == 4:
                            art._bounds = (
                                float(tb[0]),
                                float(tb[1]),
                                float(tb[2]),
                                float(tb[3]),
                            )
                        tr = ti.get("transform")
                        if isinstance(tr, list) and len(tr) == 6:
                            art._transform = [float(x) for x in tr]
                        shp = ti.get("shape")
                        if isinstance(shp, dict) and "Box" in shp and isinstance(shp["Box"], dict):
                            art._box = {
                                k: float(v) for k, v in shp["Box"].items() if isinstance(v, (int, float))
                            }
                            art.textItem.kind = 2
                        runs = ti.get("runs")
                        if isinstance(runs, list) and runs:
                            art._runs = runs
                            st = runs[0].get("style", {})
                            ps_name = st.get("postscript_name") or st.get("font_family")
                            if ps_name:
                                art.textItem._font = str(ps_name)
                            if "size_pt" in st and st["size_pt"] is not None:
                                art.textItem._size = float(st["size_pt"])
                            lead = st.get("leading_pt")
                            art.textItem.leading = (
                                float(lead) if lead is not None else art.textItem._size
                            )
                            col_dict = st.get("color")
                            if isinstance(col_dict, dict) and isinstance(col_dict.get("c"), list):
                                c_arr = col_dict["c"]
                                if len(c_arr) >= 3:
                                    sc = SolidColor()
                                    sc.rgb.red = float(c_arr[0]) * 255.0
                                    sc.rgb.green = float(c_arr[1]) * 255.0
                                    sc.rgb.blue = float(c_arr[2]) * 255.0
                                    art.textItem._color = sc
                container.artLayers._items.append(art)
                if lid is not None:
                    self._layer_by_id[int(lid)] = art
                if self._active_layer is None:
                    self._active_layer = art

    def _populate_layers_from_psd(self, psd_group: Any, container: Document | LayerSet) -> None:
        for layer in reversed(list(psd_group)):
            bbox = getattr(layer, "bbox", (0, 0, self.width, self.height))
            bounds = (float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3]))
            visible = bool(getattr(layer, "visible", True))
            opacity = round((getattr(layer, "opacity", 255) / 255.0) * 100.0, 2)
            layer_id = getattr(layer, "layer_id", None)
            if layer.is_group():
                grp = LayerSet(
                    parent=container,
                    name=layer.name,
                    layer_id=layer_id,
                    bounds=bounds,
                    visible=visible,
                    opacity=opacity,
                )
                grp._doc = self
                grp._psd_layer = layer
                container.layerSets._items.append(grp)
                self._layer_by_id[grp.id] = grp
                self._populate_layers_from_psd(layer, grp)
            else:
                kind = (
                    LayerKind.TextLayer
                    if getattr(layer, "kind", "") == "type"
                    else LayerKind.NormalLayer
                )
                art = ArtLayer(
                    parent=container,
                    name=layer.name,
                    layer_id=layer_id,
                    bounds=bounds,
                    visible=visible,
                    opacity=opacity,
                    kind=kind,
                )
                art._doc = self
                art._psd_layer = layer
                if kind == LayerKind.TextLayer and hasattr(layer, "text"):
                    art.textItem._contents = str(layer.text or "")
                container.artLayers._items.append(art)
                self._layer_by_id[art.id] = art
                if self._active_layer is None:
                    self._active_layer = art

    def save(self) -> None:
        if self._file_path:
            self.saveAs(str(self._file_path))

    def saveAs(
        self,
        file_path: str,
        options: Any = None,
        asCopy: bool = True,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        out_path = Path(file_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        # 1. Try Photocraft save/export first
        if self.app is not None and hasattr(self.app, "photocraft_save"):
            if self.app.photocraft_save(out_path, src_path=self._file_path):
                if not asCopy:
                    self._file_path = out_path
                return

        # 2. Fallback: composite with psd-tools / Pillow
        img: Image.Image | None = None
        if self._psd_image is not None:
            try:
                img = self._psd_image.composite()
            except Exception:
                img = None
        if img is None and self._pil_image is not None:
            img = self._pil_image.copy()
        if img is None:
            img = Image.new("RGBA", (max(1, int(self.width)), max(1, int(self.height))), (255, 255, 255, 255))

        ext = out_path.suffix.lower()
        if ext in (".jpg", ".jpeg"):
            if img.mode in ("RGBA", "LA", "P"):
                img = img.convert("RGB")
            img.save(str(out_path), format="JPEG", quality=95)
        elif ext == ".webp":
            img.save(str(out_path), format="WEBP", quality=95)
        elif ext in (".psd", ".psb") and self._psd_image is not None:
            self._psd_image.save(str(out_path))
        else:
            img.save(str(out_path), format="PNG")

        if not asCopy:
            self._file_path = out_path

    def close(self, saving: SaveOptions = SaveOptions.DoNotSaveChanges) -> None:
        if saving == SaveOptions.SaveChanges and self._file_path:
            self.save()
        if self.app is not None and hasattr(self.app, "photocraft_close"):
            self.app.photocraft_close(self)
        if self.app is not None and hasattr(self.app, "documents"):
            self.app.documents._remove_doc(self)

    def paste(self, *args: Any, **kwargs: Any) -> ArtLayer:
        self._exec_photocraft("edit.paste", {})
        if self._active_layer and isinstance(self._active_layer, ArtLayer):
            return self._active_layer
        return self.artLayers.add()

    def flatten(self) -> None:
        self._exec_photocraft("layer.flattenImage", {})

    def mergeVisibleLayers(self) -> None:
        self._exec_photocraft("layer.mergeVisible", {})

    def resizeImage(
        self,
        width: float | None = None,
        height: float | None = None,
        resolution: float | None = None,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        if width is not None:
            self.width = int(width)
        if height is not None:
            self.height = int(height)
        if resolution is not None:
            self.resolution = float(resolution)
        self._exec_photocraft(
            "image.imageSize",
            {"width": self.width, "height": self.height},
        )

    def resizeCanvas(
        self,
        width: float | None = None,
        height: float | None = None,
        anchor: Any = None,
    ) -> None:
        if width is not None:
            self.width = int(width)
        if height is not None:
            self.height = int(height)
        self._exec_photocraft(
            "image.canvasSize",
            {"width": self.width, "height": self.height},
        )

    def rotateCanvas(self, angle: float) -> None:
        ang = float(angle)
        self._exec_photocraft("layer.flattenImage", {})
        if ang in (-90.0, 270.0):
            self.width, self.height = self.height, self.width
            self._exec_photocraft("image.imageRotation.90ccw", {})
        elif ang in (90.0, -270.0):
            self.width, self.height = self.height, self.width
            self._exec_photocraft("image.imageRotation.90cw", {})
        elif abs(ang) == 180.0:
            self._exec_photocraft("image.imageRotation.180", {})
        else:
            self._exec_photocraft("image.rotation.arbitrary", {"angle": ang})

    def crop(self, bounds: tuple[float, float, float, float], *args: Any, **kwargs: Any) -> None:
        l, t, r, b = bounds
        self.width = max(1, int(r - l))
        self.height = max(1, int(b - t))
        self._exec_photocraft(
            "image.crop",
            {"x": int(l), "y": int(t), "width": self.width, "height": self.height},
        )

    def trim(self, *args: Any, **kwargs: Any) -> None:
        self._exec_photocraft("image.trim", {})

    def duplicate(self, name: str | None = None, *args: Any, **kwargs: Any) -> Document:
        dup = Document(
            parent=self.parent,
            file_path=self._file_path,
            width=self.width,
            height=self.height,
            resolution=self.resolution,
            name=name or f"{self.name} copy",
        )
        if self.app is not None and hasattr(self.app, "documents"):
            self.app.documents._docs.append(dup)
            self.app.activeDocument = dup
        return dup

    def suspendHistory(self, historyString: str, javaScriptString: str) -> None:
        pass


class Documents:
    """Collection of open Document instances in Application."""

    def __init__(self, app: Any = None) -> None:
        self.app = app
        self._docs: list[Document] = []

    @property
    def length(self) -> int:
        return len(self._docs)

    def __len__(self) -> int:
        return len(self._docs)

    def __iter__(self) -> Iterator[Document]:
        return iter(self._docs)

    def __getitem__(self, key: int | str) -> Document:
        if isinstance(key, int):
            return self._docs[key]
        return self.getByName(key)

    def getByName(self, name: str) -> Document:
        for doc in self._docs:
            if doc.name == name or Path(doc.name).stem == Path(name).stem:
                return doc
        raise KeyError(f"Document '{name}' not found")

    def add(
        self,
        width: int = 3264,
        height: int = 4440,
        resolution: float = 1200.0,
        name: str = "Untitled-1",
        *args: Any,
        **kwargs: Any,
    ) -> Document:
        doc = Document(
            parent=self.app,
            width=int(width),
            height=int(height),
            resolution=float(resolution),
            name=name,
        )
        self._docs.append(doc)
        if self.app is not None:
            self.app.activeDocument = doc
            if hasattr(self.app, "photocraft_new"):
                self.app.photocraft_new(int(width), int(height))
        return doc

    def _remove_doc(self, doc: Document) -> None:
        if doc in self._docs:
            self._docs.remove(doc)
        if self.app is not None and getattr(self.app, "_active_doc", None) is doc:
            self.app._active_doc = self._docs[-1] if self._docs else None
