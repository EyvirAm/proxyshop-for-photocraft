"""
* Photocraft API Compatibility Module (photoshop.api)
"""
from __future__ import annotations

import copy
import zlib
from pathlib import Path
from typing import Any

from photoshop.api._artlayer import ArtLayer, ArtLayers
from photoshop.api._core import Photoshop
from photoshop.api._document import Document, Documents
from photoshop.api._layer import Layer
from photoshop.api._layerSet import LayerSet, LayerSets
from photoshop.api._selection import Selection
from photoshop.api.enumerations import (
    AnchorPosition,
    AutoKernType,
    BlendMode,
    ColorBlendMode,
    ColorModel,
    DescValueType,
    DialogModes,
    ElementPlacement,
    FormatOptionsType,
    Justification,
    Language,
    LayerKind,
    PointKind,
    PurgeTarget,
    RasterizeType,
    SaveOptions,
    TypeUnits,
    Units,
)
from photoshop.api.path_item import PathItem
from photoshop.api.text_item import TextItem


class PhotoshopPythonAPIError(Exception):
    """Compatibility exception class for Photocraft backend errors."""


class _DualColorModel:
    """Compares equal to both ColorModel enum values and color classes (RGBColor, CMYKColor, etc.)."""

    def __init__(self, enum_val: ColorModel, cls_ref: type) -> None:
        self.enum_val = enum_val
        self.cls_ref = cls_ref

    def __eq__(self, other: object) -> bool:
        if other is self.cls_ref or other == self.enum_val:
            return True
        if isinstance(other, _DualColorModel):
            return self.enum_val == other.enum_val
        return False

    def __hash__(self) -> int:
        return hash(self.enum_val)

    def __repr__(self) -> str:
        return f"ColorModel({self.cls_ref.__name__})"


class RGBColor:
    """RGB color representation."""

    def __init__(
        self, red: float = 0.0, green: float = 0.0, blue: float = 0.0
    ) -> None:
        self._red = float(red)
        self._green = float(green)
        self._blue = float(blue)
        self._owner: SolidColor | None = None

    @property
    def red(self) -> float:
        return self._red

    @red.setter
    def red(self, val: float) -> None:
        self._red = float(val)
        if self._owner is not None:
            self._owner._model = _DualColorModel(ColorModel.RGBModel, RGBColor)

    @property
    def green(self) -> float:
        return self._green

    @green.setter
    def green(self, val: float) -> None:
        self._green = float(val)
        if self._owner is not None:
            self._owner._model = _DualColorModel(ColorModel.RGBModel, RGBColor)

    @property
    def blue(self) -> float:
        return self._blue

    @blue.setter
    def blue(self, val: float) -> None:
        self._blue = float(val)
        if self._owner is not None:
            self._owner._model = _DualColorModel(ColorModel.RGBModel, RGBColor)

    @property
    def hexValue(self) -> str:
        return f"{int(round(self._red)):02X}{int(round(self._green)):02X}{int(round(self._blue)):02X}"

    @hexValue.setter
    def hexValue(self, value: str) -> None:
        h = str(value).lstrip("#")
        if len(h) == 3:
            h = "".join(c * 2 for c in h)
        if len(h) != 6:
            raise ValueError(f"Invalid hex color: {value}")
        self._red = float(int(h[0:2], 16))
        self._green = float(int(h[2:4], 16))
        self._blue = float(int(h[4:6], 16))
        if self._owner is not None:
            self._owner._model = _DualColorModel(ColorModel.RGBModel, RGBColor)


class CMYKColor:
    """CMYK color representation."""

    def __init__(
        self,
        cyan: float = 0.0,
        magenta: float = 0.0,
        yellow: float = 0.0,
        black: float = 0.0,
    ) -> None:
        self._cyan = float(cyan)
        self._magenta = float(magenta)
        self._yellow = float(yellow)
        self._black = float(black)
        self._owner: SolidColor | None = None

    @property
    def cyan(self) -> float:
        return self._cyan

    @cyan.setter
    def cyan(self, val: float) -> None:
        self._cyan = float(val)
        if self._owner is not None:
            self._owner._model = _DualColorModel(ColorModel.CMYKModel, CMYKColor)

    @property
    def magenta(self) -> float:
        return self._magenta

    @magenta.setter
    def magenta(self, val: float) -> None:
        self._magenta = float(val)
        if self._owner is not None:
            self._owner._model = _DualColorModel(ColorModel.CMYKModel, CMYKColor)

    @property
    def yellow(self) -> float:
        return self._yellow

    @yellow.setter
    def yellow(self, val: float) -> None:
        self._yellow = float(val)
        if self._owner is not None:
            self._owner._model = _DualColorModel(ColorModel.CMYKModel, CMYKColor)

    @property
    def black(self) -> float:
        return self._black

    @black.setter
    def black(self, val: float) -> None:
        self._black = float(val)
        if self._owner is not None:
            self._owner._model = _DualColorModel(ColorModel.CMYKModel, CMYKColor)


class HSBColor:
    """HSB color representation."""

    def __init__(
        self, hue: float = 0.0, saturation: float = 0.0, brightness: float = 0.0
    ) -> None:
        self._hue = float(hue)
        self._saturation = float(saturation)
        self._brightness = float(brightness)
        self._owner: SolidColor | None = None

    @property
    def hue(self) -> float:
        return self._hue

    @hue.setter
    def hue(self, val: float) -> None:
        self._hue = float(val)
        if self._owner is not None:
            self._owner._model = _DualColorModel(ColorModel.HSBModel, HSBColor)

    @property
    def saturation(self) -> float:
        return self._saturation

    @saturation.setter
    def saturation(self, val: float) -> None:
        self._saturation = float(val)
        if self._owner is not None:
            self._owner._model = _DualColorModel(ColorModel.HSBModel, HSBColor)

    @property
    def brightness(self) -> float:
        return self._brightness

    @brightness.setter
    def brightness(self, val: float) -> None:
        self._brightness = float(val)
        if self._owner is not None:
            self._owner._model = _DualColorModel(ColorModel.HSBModel, HSBColor)


class LabColor:
    """Lab color representation."""

    def __init__(self, L: float = 0.0, A: float = 0.0, B: float = 0.0) -> None:
        self._L = float(L)
        self._A = float(A)
        self._B = float(B)
        self._owner: SolidColor | None = None

    @property
    def L(self) -> float:
        return self._L

    @L.setter
    def L(self, val: float) -> None:
        self._L = float(val)
        if self._owner is not None:
            self._owner._model = _DualColorModel(ColorModel.LabModel, LabColor)

    @property
    def A(self) -> float:
        return self._A

    @A.setter
    def A(self, val: float) -> None:
        self._A = float(val)
        if self._owner is not None:
            self._owner._model = _DualColorModel(ColorModel.LabModel, LabColor)

    @property
    def B(self) -> float:
        return self._B

    @B.setter
    def B(self, val: float) -> None:
        self._B = float(val)
        if self._owner is not None:
            self._owner._model = _DualColorModel(ColorModel.LabModel, LabColor)


class SolidColor:
    """Unified SolidColor class compatible with Proxyshop's Pydantic schemas and helpers."""

    def __init__(self, model: ColorModel = ColorModel.RGBModel) -> None:
        self.rgb = RGBColor()
        self.rgb._owner = self
        self.cmyk = CMYKColor()
        self.cmyk._owner = self
        self.hsb = HSBColor()
        self.hsb._owner = self
        self.lab = LabColor()
        self.lab._owner = self
        if model == ColorModel.CMYKModel:
            self._model = _DualColorModel(ColorModel.CMYKModel, CMYKColor)
        elif model == ColorModel.HSBModel:
            self._model = _DualColorModel(ColorModel.HSBModel, HSBColor)
        elif model == ColorModel.LabModel:
            self._model = _DualColorModel(ColorModel.LabModel, LabColor)
        else:
            self._model = _DualColorModel(ColorModel.RGBModel, RGBColor)

    @property
    def model(self) -> Any:
        return self._model

    @model.setter
    def model(self, val: Any) -> None:
        if val in (ColorModel.CMYKModel, CMYKColor):
            self._model = _DualColorModel(ColorModel.CMYKModel, CMYKColor)
        elif val in (ColorModel.HSBModel, HSBColor):
            self._model = _DualColorModel(ColorModel.HSBModel, HSBColor)
        elif val in (ColorModel.LabModel, LabColor):
            self._model = _DualColorModel(ColorModel.LabModel, LabColor)
        else:
            self._model = _DualColorModel(ColorModel.RGBModel, RGBColor)


class ActionReference:
    """Stores target references for action descriptors."""

    def __init__(self) -> None:
        self.entries: list[tuple[str, Any]] = []

    def putIdentifier(self, key: int, value: int) -> None:
        self.entries.append(("identifier", (key, int(value))))

    def putIndex(self, key: int, value: int) -> None:
        self.entries.append(("index", (key, int(value))))

    def putName(self, key: int, value: str) -> None:
        self.entries.append(("name", (key, str(value))))

    def putEnumerated(self, key: int, enum_type: int, value: int) -> None:
        self.entries.append(("enumerated", (key, enum_type, value)))

    def putProperty(self, key: int, value: int) -> None:
        self.entries.append(("property", (key, value)))

    def putClass(self, value: int) -> None:
        self.entries.append(("class", value))

    def putOffset(self, key: int, value: int) -> None:
        self.entries.append(("offset", (key, int(value))))


class ActionList:
    """Stores an ordered list of values in an ActionDescriptor."""

    def __init__(self) -> None:
        self._items: list[tuple[DescValueType, Any]] = []

    @property
    def count(self) -> int:
        return len(self._items)

    def putInteger(self, value: int) -> None:
        self._items.append((DescValueType.IntegerType, int(value)))

    def putDouble(self, value: float) -> None:
        self._items.append((DescValueType.DoubleType, float(value)))

    def putUnitDouble(self, unit_id: int, value: float) -> None:
        self._items.append((DescValueType.UnitDouble, (unit_id, float(value))))

    def putString(self, value: str) -> None:
        self._items.append((DescValueType.StringType, str(value)))

    def putBoolean(self, value: bool) -> None:
        self._items.append((DescValueType.BooleanType, bool(value)))

    def putObject(self, class_id: int, value: ActionDescriptor) -> None:
        self._items.append((DescValueType.ObjectType, (class_id, copy.deepcopy(value))))

    def putReference(self, value: ActionReference) -> None:
        self._items.append((DescValueType.ReferenceType, copy.deepcopy(value)))

    def putList(self, value: ActionList) -> None:
        self._items.append((DescValueType.ListType, copy.deepcopy(value)))

    def putEnumerated(self, enum_type: int, value: int) -> None:
        self._items.append((DescValueType.EnumeratedType, (enum_type, value)))

    def getType(self, index: int) -> DescValueType:
        return self._items[index][0]

    def getInteger(self, index: int) -> int:
        return int(self._items[index][1])

    def getDouble(self, index: int) -> float:
        val = self._items[index][1]
        return float(val[1]) if isinstance(val, tuple) else float(val)

    def getUnitDoubleType(self, index: int) -> int:
        val = self._items[index][1]
        return int(val[0]) if isinstance(val, tuple) else 0

    def getUnitDoubleValue(self, index: int) -> float:
        val = self._items[index][1]
        return float(val[1]) if isinstance(val, tuple) else float(val)

    def getString(self, index: int) -> str:
        return str(self._items[index][1])

    def getBoolean(self, index: int) -> bool:
        return bool(self._items[index][1])

    def getObjectType(self, index: int) -> int:
        val = self._items[index][1]
        return int(val[0]) if isinstance(val, tuple) else 0

    def getObjectValue(self, index: int) -> ActionDescriptor:
        val = self._items[index][1]
        return val[1] if isinstance(val, tuple) else val

    def getList(self, index: int) -> ActionList:
        return self._items[index][1]

    def getEnumerationType(self, index: int) -> int:
        val = self._items[index][1]
        return int(val[0]) if isinstance(val, tuple) else 0

    def getEnumerationValue(self, index: int) -> int:
        val = self._items[index][1]
        return int(val[1]) if isinstance(val, tuple) else int(val)


class ActionDescriptor:
    """Stores key-value pairs for Photoshop/Photocraft actions."""

    def __init__(self) -> None:
        self._data: dict[int, tuple[DescValueType, Any]] = {}

    @property
    def count(self) -> int:
        return len(self._data)

    def hasKey(self, key: int) -> bool:
        return key in self._data

    def getKey(self, index: int) -> int:
        return list(self._data.keys())[index]

    def getType(self, key: int) -> DescValueType:
        return self._data.get(key, (DescValueType.IntegerType, 0))[0]

    def putInteger(self, key: int, value: int) -> None:
        self._data[key] = (DescValueType.IntegerType, int(value))

    def putLargeInteger(self, key: int, value: int) -> None:
        self._data[key] = (DescValueType.LargeIntegerType, int(value))

    def putDouble(self, key: int, value: float) -> None:
        self._data[key] = (DescValueType.DoubleType, float(value))

    def putUnitDouble(self, key: int, unit_id: int, value: float) -> None:
        self._data[key] = (DescValueType.UnitDouble, (unit_id, float(value)))

    def putString(self, key: int, value: str) -> None:
        self._data[key] = (DescValueType.StringType, str(value))

    def putBoolean(self, key: int, value: bool) -> None:
        self._data[key] = (DescValueType.BooleanType, bool(value))

    def putObject(self, key: int, class_id: int, value: ActionDescriptor) -> None:
        self._data[key] = (DescValueType.ObjectType, (class_id, copy.deepcopy(value)))

    def putReference(self, key: int, value: ActionReference) -> None:
        self._data[key] = (DescValueType.ReferenceType, copy.deepcopy(value))

    def putList(self, key: int, value: ActionList) -> None:
        self._data[key] = (DescValueType.ListType, copy.deepcopy(value))

    def putEnumerated(self, key: int, enum_type: int, value: int) -> None:
        self._data[key] = (DescValueType.EnumeratedType, (enum_type, value))

    def putClass(self, key: int, value: int) -> None:
        self._data[key] = (DescValueType.ClassType, int(value))

    def putPath(self, key: int, value: str | Path) -> None:
        self._data[key] = (DescValueType.AliasType, str(value))

    def putData(self, key: int, value: str | bytes) -> None:
        self._data[key] = (DescValueType.RawType, value)

    def getInteger(self, key: int) -> int:
        if key not in self._data:
            return 0
        val = self._data[key][1]
        return int(val[1]) if isinstance(val, tuple) else int(val)

    def getLargeInteger(self, key: int) -> int:
        return self.getInteger(key)

    def getDouble(self, key: int) -> float:
        if key not in self._data:
            return 0.0
        val = self._data[key][1]
        return float(val[1]) if isinstance(val, tuple) else float(val)

    def getUnitDoubleType(self, key: int) -> int:
        if key not in self._data:
            return 0
        val = self._data[key][1]
        return int(val[0]) if isinstance(val, tuple) else 0

    def getUnitDoubleValue(self, key: int) -> float:
        return self.getDouble(key)

    def getString(self, key: int) -> str:
        if key not in self._data:
            return ""
        return str(self._data[key][1])

    def getBoolean(self, key: int) -> bool:
        if key not in self._data:
            return False
        return bool(self._data[key][1])

    def getObjectType(self, key: int) -> int:
        if key not in self._data:
            return 0
        val = self._data[key][1]
        return int(val[0]) if isinstance(val, tuple) else 0

    def getObjectValue(self, key: int) -> ActionDescriptor:
        if key not in self._data:
            return ActionDescriptor()
        val = self._data[key][1]
        return val[1] if isinstance(val, tuple) else val

    def getList(self, key: int) -> ActionList:
        if key not in self._data:
            return ActionList()
        return self._data[key][1]

    def getReference(self, key: int) -> ActionReference:
        if key not in self._data:
            return ActionReference()
        return self._data[key][1]

    def getEnumerationType(self, key: int) -> int:
        if key not in self._data:
            return 0
        val = self._data[key][1]
        return int(val[0]) if isinstance(val, tuple) else 0

    def getEnumerationValue(self, key: int) -> int:
        if key not in self._data:
            return 0
        val = self._data[key][1]
        return int(val[1]) if isinstance(val, tuple) else int(val)

    def getClass(self, key: int) -> int:
        return self.getInteger(key)

    def getPath(self, key: int) -> str:
        return self.getString(key)

    def getData(self, key: int) -> str:
        return self.getString(key)


class JPEGSaveOptions:
    def __init__(self, quality: int = 12) -> None:
        self.quality = quality
        self.formatOptions = FormatOptionsType.StandardBaseline
        self.scans = 3
        self.matte = 1


class PNGSaveOptions:
    def __init__(self, compression: int = 3, interlaced: bool = False) -> None:
        self.compression = compression
        self.interlaced = interlaced


class PhotoshopSaveOptions:
    def __init__(self) -> None:
        self.alphaChannels = True
        self.annotations = True
        self.layers = True
        self.spotColors = True


class _Preferences:
    def __init__(self) -> None:
        self.rulerUnits = Units.Pixels
        self.typeUnits = TypeUnits.TypePoints


class _TextFont:
    def __init__(self, name: str, postScriptName: str | None = None, family: str | None = None) -> None:
        self.name = name
        self.postScriptName = postScriptName or name
        self.family = family or name
        self.style = "Regular"


class _TextFonts:
    def __init__(self) -> None:
        self._fonts: list[_TextFont] = [
            _TextFont("Beleren Bold", "BelerenProxy-Bold", "Beleren"),
            _TextFont("Beleren SmallCaps", "BelerenSmallCaps-Bold", "Beleren SmallCaps"),
            _TextFont("MPlantin", "PlantinMTPro-Regular", "Plantin MT Pro"),
            _TextFont("MPlantin-Italic", "PlantinMTPro-Italic", "Plantin MT Pro"),
            _TextFont("MPlantin-Bold", "PlantinMTPro-Bold", "Plantin MT Pro"),
            _TextFont("Relay-Medium", "Gotham-Medium", "Gotham"),
            _TextFont("NDPMTG", "NDPMTG", "NDPMTG"),
            _TextFont("Proxyglyph", "Proxyglyph", "Proxyglyph"),
        ]

    @property
    def app(self) -> _TextFonts:
        return self

    def __iter__(self):
        return iter(self._fonts)

    def __len__(self) -> int:
        return len(self._fonts)

    def getByName(self, name: str) -> _TextFont:
        for f in self._fonts:
            if f.name == name or f.postScriptName == name:
                return f
        return _TextFont(name, name)

    def __getitem__(self, key: int | str) -> _TextFont:
        if isinstance(key, int):
            return self._fonts[key]
        return self.getByName(key)


_ID_TO_STR: dict[int, str] = {}
_STR_TO_ID: dict[str, int] = {}


def _register_id(name: str) -> int:
    if name in _STR_TO_ID:
        return _STR_TO_ID[name]
    if len(name) == 4:
        val = (
            (ord(name[0]) << 24)
            | (ord(name[1]) << 16)
            | (ord(name[2]) << 8)
            | ord(name[3])
        )
    else:
        val = zlib.crc32(name.encode("utf-8")) & 0x7FFFFFFF
    _STR_TO_ID[name] = val
    _ID_TO_STR[val] = name
    return val


class Application(Photoshop):
    """Photocraft-backed Application class replacing Adobe Photoshop COM Application."""

    def __init__(self, version: str | None = None) -> None:
        super().__init__(parent=None)
        self.app = self
        self.version: str = version or "25.0.0"
        self.displayDialogs: DialogModes = DialogModes.DisplayNoDialogs
        self.preferences = _Preferences()
        self.documents = Documents(app=self)
        self._active_doc: Document | None = None
        self.fonts = _TextFonts()
        self.foregroundColor = SolidColor()
        self.backgroundColor = SolidColor()

    @property
    def activeDocument(self) -> Document:
        if self._active_doc is None:
            if self.documents._docs:
                self._active_doc = self.documents._docs[-1]
            else:
                self._active_doc = self.documents.add()
        return self._active_doc

    @activeDocument.setter
    def activeDocument(self, doc: Document) -> None:
        self._active_doc = doc

    def bringToFront(self) -> None:
        pass

    def load(self, file_path: str | Path) -> Document:
        doc = Document(parent=self, file_path=file_path)
        self.documents._docs = [
            d for d in self.documents._docs if d.name != doc.name
        ]
        self.documents._docs.append(doc)
        self._active_doc = doc
        return doc

    def open(self, file_path: str | Path) -> Document:
        return self.load(file_path)

    def purge(self, target: PurgeTarget = PurgeTarget.AllCaches) -> None:
        pass

    def refreshFonts(self) -> None:
        pass

    def doJavaScript(self, javascript: str, *args: Any, **kwargs: Any) -> str:
        return ""

    def charIDToTypeID(self, char_id: str) -> int:
        return _register_id(char_id)

    def typeIDToCharID(self, type_id: int) -> str:
        s = _ID_TO_STR.get(type_id)
        if s and len(s) == 4:
            return s
        return "    "

    def stringIDToTypeID(self, string_id: str) -> int:
        return _register_id(string_id)

    def typeIDToStringID(self, type_id: int) -> str:
        return _ID_TO_STR.get(type_id, str(type_id))

    def _resolve_target_layer(self, ref: ActionReference | None) -> ArtLayer | LayerSet | None:
        if self._active_doc is None:
            return None
        if ref is not None:
            for kind, val in reversed(ref.entries):
                if kind == "identifier" and isinstance(val, tuple):
                    lid = int(val[1])
                    found = self._active_doc.find_layer_by_id(lid)
                    if found is not None:
                        return found
                elif kind == "name" and isinstance(val, tuple):
                    name = str(val[1])
                    try:
                        return self._active_doc.artLayers.getByName(name)
                    except KeyError:
                        try:
                            return self._active_doc.layerSets.getByName(name)
                        except KeyError:
                            pass
        return self._active_doc._active_layer

    def _extract_hex_color(self, style_desc: ActionDescriptor) -> str | None:
        id_color = self.stringIDToTypeID("color")
        if not style_desc.hasKey(id_color):
            return None
        c_desc = style_desc.getObjectValue(id_color)
        id_r = self.stringIDToTypeID("red")
        id_g = self.stringIDToTypeID("green")
        id_b = self.stringIDToTypeID("blue")
        if c_desc.hasKey(id_r) or c_desc.hasKey(id_g) or c_desc.hasKey(id_b):
            r = max(0, min(255, int(round(c_desc.getDouble(id_r)))))
            g = max(0, min(255, int(round(c_desc.getDouble(id_g)))))
            b = max(0, min(255, int(round(c_desc.getDouble(id_b)))))
            return f"#{r:02x}{g:02x}{b:02x}"
        return None

    def executeAction(
        self,
        event_id: int,
        descriptor: ActionDescriptor | None = None,
        display_dialogs: DialogModes = DialogModes.DisplayNoDialogs,
    ) -> ActionDescriptor:
        event_name = self.typeIDToStringID(event_id)
        doc = self._active_doc
        if doc is None:
            return ActionDescriptor()

        id_target = self.stringIDToTypeID("target")
        id_null = self.stringIDToTypeID("null")
        id_to = self.stringIDToTypeID("to")
        id_T = self.charIDToTypeID("T   ")

        if event_name == "placeEvent" and descriptor is not None and descriptor.hasKey(id_target):
            placed_path = Path(descriptor.getPath(id_target))
            layer = ArtLayer(parent=doc, name=placed_path.stem)
            if hasattr(self, "photocraft_place"):
                res = self.photocraft_place(placed_path)
                if isinstance(res, dict):
                    if "layer" in res:
                        layer._id = int(res["layer"])
                    b = res.get("bounds")
                    if isinstance(b, list) and len(b) == 4:
                        layer._bounds = (
                            float(b[0]),
                            float(b[1]),
                            float(b[2]),
                            float(b[3]),
                        )
            if layer._bounds == (0.0, 0.0, 100.0, 100.0) and placed_path.exists():
                try:
                    from PIL import Image

                    img = Image.open(str(placed_path))
                    layer._pil_image = img.copy()
                    layer._bounds = (0.0, 0.0, float(img.width), float(img.height))
                except Exception:
                    pass
            doc.artLayers._items.insert(0, layer)
            doc._layer_by_id[layer.id] = layer
            doc._active_layer = layer
            return ActionDescriptor()

        if event_name == "select" and descriptor is not None:
            ref = descriptor.getReference(id_target) if descriptor.hasKey(id_target) else None
            target_layer = self._resolve_target_layer(ref)
            if target_layer is not None:
                doc._active_layer = target_layer
                doc._exec_photocraft(
                    "layer.select", {"layer": target_layer.id, "mode": "replace"}
                )
                id_make_vis = self.stringIDToTypeID("makeVisible")
                if descriptor.hasKey(id_make_vis) and descriptor.getBoolean(id_make_vis):
                    target_layer.visible = True
            return ActionDescriptor()

        if event_name in ("set", "setd") and descriptor is not None:
            ref = (
                descriptor.getReference(id_target)
                if descriptor.hasKey(id_target)
                else descriptor.getReference(id_null)
                if descriptor.hasKey(id_null)
                else None
            )
            target_layer = self._resolve_target_layer(ref)
            to_key = id_to if descriptor.hasKey(id_to) else id_T if descriptor.hasKey(id_T) else None

            if to_key is not None:
                val_type = descriptor.getType(to_key)
                if val_type == DescValueType.ReferenceType and target_layer is not None:
                    # e.g. select_layer_pixels setting selection to layer transparency
                    l, t, r, b = target_layer.bounds
                    doc.selection.bounds = (l, t, r, b)
                    doc.selection._inverted = False
                    w = max(1, int(round(r - l)))
                    h = max(1, int(round(b - t)))
                    doc._exec_photocraft(
                        "select.rect",
                        {
                            "x": int(round(l)),
                            "y": int(round(t)),
                            "width": w,
                            "height": h,
                            "mode": "replace",
                            "ellipse": False,
                        },
                    )
                    return ActionDescriptor()

                if val_type == DescValueType.ObjectType and target_layer is not None:
                    to_obj = descriptor.getObjectValue(to_key)
                    id_vec_m = self.stringIDToTypeID("vectorMaskEnabled")
                    id_usr_m = self.charIDToTypeID("UsrM")
                    # Group and layer mask toggling (works for LayerSet and ArtLayer alike)
                    if to_obj.hasKey(id_vec_m):
                        vis = to_obj.getBoolean(id_vec_m)
                        doc._exec_photocraft(
                            "layer.vectorMask.enabled",
                            {"layer": target_layer.id, "enabled": vis},
                        )
                        return ActionDescriptor()
                    if to_obj.hasKey(id_usr_m):
                        vis = to_obj.getBoolean(id_usr_m)
                        doc._exec_photocraft(
                            "layer.layerMask.enabled",
                            {"layer": target_layer.id, "enabled": vis},
                        )
                        return ActionDescriptor()

                if val_type == DescValueType.ObjectType and isinstance(target_layer, ArtLayer):
                    to_obj = descriptor.getObjectValue(to_key)
                    id_text_key = self.stringIDToTypeID("textKey")
                    id_style_range = self.stringIDToTypeID("textStyleRange")
                    id_size = self.stringIDToTypeID("size")
                    id_leading = self.stringIDToTypeID("leading")
                    id_tracking = self.stringIDToTypeID("tracking")
                    id_font_ps = self.stringIDToTypeID("fontPostScriptName")
                    id_from = self.stringIDToTypeID("from")
                    id_text_style = self.stringIDToTypeID("textStyle")
                    id_usr_m = self.charIDToTypeID("UsrM")

                    # 1. Full textKey update (from format_text / apply_text_key)
                    if to_obj.hasKey(id_text_key):
                        raw_text = to_obj.getString(id_text_key)
                        target_layer.textItem._contents = raw_text
                        res = doc._exec_photocraft(
                            "type.edit",
                            {
                                "layer": target_layer.id,
                                "text": raw_text.replace("\r", "\n"),
                            },
                        )
                        target_layer._update_bounds_from_type_result(res)

                        if to_obj.hasKey(id_style_range):
                            ranges_list = to_obj.getList(id_style_range)
                            seen_colors: list[str] = []
                            dup_counter = 0
                            for i in range(ranges_list.count):
                                r_desc = ranges_list.getObjectValue(i)
                                start = r_desc.getInteger(id_from)
                                end = r_desc.getInteger(id_to)
                                if end <= start:
                                    continue
                                st_desc = r_desc.getObjectValue(id_text_style)
                                style_kwargs: dict[str, Any] = {
                                    "range": [start, end],
                                    "metricsAsShown": True,
                                }
                                if st_desc.hasKey(id_font_ps):
                                    style_kwargs["font"] = st_desc.getString(id_font_ps)
                                if st_desc.hasKey(id_size):
                                    style_kwargs["size"] = st_desc.getDouble(id_size)
                                    if i == 0:
                                        tr = getattr(target_layer, "_transform", [1.0, 0.0, 0.0, 1.0, 0.0, 0.0])
                                        yy = ((float(tr[2]) ** 2 + float(tr[3]) ** 2) ** 0.5) or 1.0
                                        target_layer.textItem._size = float(style_kwargs["size"]) / yy
                                if st_desc.hasKey(id_leading):
                                    style_kwargs["leading"] = st_desc.getDouble(id_leading)
                                if st_desc.hasKey(id_tracking):
                                    style_kwargs["tracking"] = st_desc.getInteger(id_tracking)
                                hex_c = self._extract_hex_color(st_desc)
                                if hex_c:
                                    # Ensure sequential colour passes in PhotoCraft's text renderer
                                    # so background mana circles never paint over later foreground glyphs
                                    if hex_c in seen_colors and seen_colors[-1] != hex_c:
                                        dup_counter += 1
                                        r_v = int(hex_c[1:3], 16)
                                        g_v = int(hex_c[3:5], 16)
                                        b_v = int(hex_c[5:7], 16)
                                        b_v = (b_v + dup_counter) if b_v + dup_counter <= 255 else max(0, b_v - dup_counter)
                                        hex_c = f"#{r_v:02x}{g_v:02x}{b_v:02x}"
                                    seen_colors.append(hex_c)
                                    style_kwargs["color"] = hex_c
                                target_layer._sync_style_to_photocraft(**style_kwargs)

                        id_para_range = self.stringIDToTypeID("paragraphStyleRange")
                        id_para_style = self.stringIDToTypeID("paragraphStyle")
                        id_space_before = self.stringIDToTypeID("spaceBefore")
                        id_space_after = self.stringIDToTypeID("spaceAfter")
                        id_first_indent = self.stringIDToTypeID("firstLineIndent")
                        id_start_indent = self.stringIDToTypeID("startIndent")
                        id_end_indent = self.stringIDToTypeID("endIndent")
                        id_align = self.stringIDToTypeID("align")
                        if to_obj.hasKey(id_para_range):
                            p_list = to_obj.getList(id_para_range)
                            for i in range(p_list.count):
                                p_desc = p_list.getObjectValue(i)
                                p_start = p_desc.getInteger(id_from)
                                p_end = p_desc.getInteger(id_to)
                                if p_end <= p_start:
                                    continue
                                ps_desc = p_desc.getObjectValue(id_para_style)
                                p_kwargs: dict[str, Any] = {
                                    "range": [p_start, p_end],
                                }
                                if ps_desc.hasKey(id_space_before):
                                    p_kwargs["spaceBefore"] = ps_desc.getDouble(id_space_before)
                                if ps_desc.hasKey(id_space_after):
                                    p_kwargs["spaceAfter"] = ps_desc.getDouble(id_space_after)
                                if ps_desc.hasKey(id_first_indent):
                                    p_kwargs["firstLineIndent"] = ps_desc.getDouble(id_first_indent)
                                if ps_desc.hasKey(id_start_indent):
                                    p_kwargs["startIndent"] = ps_desc.getDouble(id_start_indent)
                                if ps_desc.hasKey(id_end_indent):
                                    p_kwargs["endIndent"] = ps_desc.getDouble(id_end_indent)
                                if ps_desc.hasKey(id_align):
                                    align_val = self.typeIDToStringID(ps_desc.getEnumerationValue(id_align))
                                    if align_val in ("left", "center", "right", "justify"):
                                        p_kwargs["align"] = align_val
                                if len(p_kwargs) > 1:
                                    target_layer._sync_style_to_photocraft(**p_kwargs)
                        return ActionDescriptor()

                    # 2. Direct textStyle update (from set_text_size / set_text_size_and_leading)
                    if to_obj.hasKey(id_size) or to_obj.hasKey(id_leading) or to_obj.hasKey(id_font_ps):
                        style_kwargs = {"metricsAsShown": True}
                        if to_obj.hasKey(id_size):
                            sz = to_obj.getDouble(id_size)
                            target_layer.textItem._size = sz
                            style_kwargs["size"] = sz
                        if to_obj.hasKey(id_leading):
                            ld = to_obj.getDouble(id_leading)
                            target_layer.textItem.leading = ld
                            style_kwargs["leading"] = ld
                        if to_obj.hasKey(id_font_ps):
                            fn = to_obj.getString(id_font_ps)
                            target_layer.textItem._font = fn
                            style_kwargs["font"] = fn
                        target_layer._sync_style_to_photocraft(**style_kwargs)
                        return ActionDescriptor()

        if event_name == "findReplace" and descriptor is not None:
            id_using = self.stringIDToTypeID("using")
            if descriptor.hasKey(id_using):
                u_desc = descriptor.getObjectValue(id_using)
                find_str = u_desc.getString(self.stringIDToTypeID("find"))
                rep_str = u_desc.getString(self.stringIDToTypeID("replace"))
                lyr = doc._active_layer
                if isinstance(lyr, ArtLayer) and find_str in lyr.textItem.contents:
                    lyr.textItem.contents = lyr.textItem.contents.replace(find_str, rep_str)
            return ActionDescriptor()

        if event_name == "interfaceIconFrameDimmed" and descriptor is not None:
            ref = descriptor.getReference(id_target) if descriptor.hasKey(id_target) else None
            target_layer = self._resolve_target_layer(ref)
            if target_layer is not None:
                rl, rt, rr, rb = doc.selection.bounds
                ll, lt, lr, lb = target_layer.bounds
                il, it, ir, ib = max(rl, ll), max(rt, lt), min(rr, lr), min(rb, lb)
                if ir <= il or ib <= it:
                    doc.selection.bounds = (0.0, 0.0, 0.0, 0.0)
                else:
                    type_lines = getattr(target_layer, "_type_lines", None)
                    if isinstance(type_lines, list) and type_lines:
                        tr = getattr(target_layer, "_transform", [1.0, 0.0, 0.0, 1.0, 0.0, 0.0])
                        xx = float(tr[0]) if float(tr[0]) > 0 else 1.0
                        yy = float(tr[3]) if float(tr[3]) > 0 else 1.0
                        b0 = float(type_lines[0].get("baseline", 0.0))
                        x0_first = float(type_lines[0].get("x0", 0.0))
                        origin_x = ll - x0_first * xx
                        max_bot = None
                        for ln in type_lines:
                            bk = float(ln.get("baseline", 0.0))
                            asc = float(ln.get("ascent", 0.0)) * yy
                            desc_v = float(ln.get("descent", 0.0)) * yy
                            ln_top = lt + (bk - b0) * yy
                            ln_bot = ln_top + asc + desc_v
                            ln_right = origin_x + float(ln.get("x1", 0.0)) * xx
                            if ln_bot > rt and ln_top < rb and ln_right > rl:
                                if max_bot is None or ln_bot > max_bot:
                                    max_bot = ln_bot
                        if max_bot is None:
                            doc.selection.bounds = (0.0, 0.0, 0.0, 0.0)
                        else:
                            doc.selection.bounds = (il, it, ir, min(rb, max_bot))
                    else:
                        doc.selection.bounds = (il, it, ir, ib)
            return ActionDescriptor()

        if event_name in ("make", "Mk  ") and descriptor is not None:
            id_using = self.stringIDToTypeID("using")
            id_usng = self.charIDToTypeID("Usng")
            u_key = id_using if descriptor.hasKey(id_using) else id_usng if descriptor.hasKey(id_usng) else None
            if u_key is not None and descriptor.getType(u_key) == DescValueType.ReferenceType:
                # e.g. copy_layer_mask: make channel mask at layer_to using channel mask of layer_from
                id_at = self.stringIDToTypeID("at")
                ref_from = descriptor.getReference(u_key)
                ref_to = descriptor.getReference(id_at) if descriptor.hasKey(id_at) else None
                lyr_from = self._resolve_target_layer(ref_from)
                lyr_to = self._resolve_target_layer(ref_to)
                if lyr_from is not None and lyr_to is not None:
                    doc._exec_photocraft("layer.select", {"layer": lyr_from.id, "mode": "replace"})
                    doc._exec_photocraft("channel.target.layerMask", {})
                    doc._exec_photocraft("select.all", {})
                    doc._exec_photocraft("edit.copy", {})
                    doc._exec_photocraft("select.deselect", {})
                    doc._exec_photocraft("layer.select", {"layer": lyr_to.id, "mode": "replace"})
                    doc._exec_photocraft("layer.layerMask.revealAll", {"layer": lyr_to.id})
                    doc._exec_photocraft("channel.target.layerMask", {})
                    doc._exec_photocraft("select.all", {})
                    doc._exec_photocraft("edit.paste", {})
                    doc._exec_photocraft("channel.target.composite", {})
                return ActionDescriptor()

            if u_key is not None and descriptor.getType(u_key) == DescValueType.ObjectType:
                u_obj = descriptor.getObjectValue(u_key)
                u_cls = self.typeIDToStringID(descriptor.getObjectType(u_key))
                if u_cls == "layerSection":
                    id_nm = self.charIDToTypeID("Nm  ")
                    grp_name = u_obj.getString(id_nm) if u_obj.hasKey(id_nm) else "Group"
                    res = doc._exec_photocraft("layer.new.groupFromLayers", {"name": grp_name})
                    lid = int(res["layer"]) if isinstance(res, dict) and "layer" in res else None
                    grp = LayerSet(parent=doc, name=grp_name, layer_id=lid)
                    doc.layerSets._items.insert(0, grp)
                    doc._layer_by_id[grp.id] = grp
                    doc._active_layer = grp
                    return ActionDescriptor()

                # Solid Color or Gradient adjustment layer (contentLayer)
                id_type = self.stringIDToTypeID("type")
                id_group = self.stringIDToTypeID("group")
                id_grad = self.stringIDToTypeID("gradient")
                id_colors = self.stringIDToTypeID("colors")
                id_loc = self.stringIDToTypeID("location")
                id_ang = self.stringIDToTypeID("angle")
                id_scl = self.stringIDToTypeID("scale")
                clipped = u_obj.getBoolean(id_group) if u_obj.hasKey(id_group) else False
                prev_active = doc._active_layer
                lid: int | None = None

                if u_obj.hasKey(id_type) and u_obj.getType(id_type) == DescValueType.ObjectType:
                    t_obj = u_obj.getObjectValue(id_type)
                    t_cls = self.typeIDToStringID(u_obj.getObjectType(id_type))
                    if t_cls == "gradientLayer" or t_obj.hasKey(id_grad):
                        stops: list[list[Any]] = []
                        if t_obj.hasKey(id_grad):
                            g_obj = t_obj.getObjectValue(id_grad)
                            if g_obj.hasKey(id_colors):
                                c_list = g_obj.getList(id_colors)
                                for idx in range(c_list.count):
                                    s_desc = c_list.getObjectValue(idx)
                                    loc_val = (
                                        max(0.0, min(1.0, s_desc.getInteger(id_loc) / 4096.0))
                                        if s_desc.hasKey(id_loc)
                                        else 0.0
                                    )
                                    col_hex = self._extract_hex_color(s_desc) or "#000000"
                                    stops.append([round(loc_val, 4), col_hex])
                        if not stops:
                            stops = [[0.0, "#000000"], [1.0, "#ffffff"]]
                        ang_val = t_obj.getDouble(id_ang) if t_obj.hasKey(id_ang) else 0.0
                        scl_val = t_obj.getDouble(id_scl) if t_obj.hasKey(id_scl) else 100.0
                        res = doc._exec_photocraft(
                            "gradient.fill.create",
                            {
                                "from": [0.0, float(doc.height) / 2.0],
                                "to": [float(doc.width), float(doc.height) / 2.0],
                                "style": "linear",
                                "stops": stops,
                            },
                        )
                        lid = int(res["layer"]) if isinstance(res, dict) and "layer" in res else None
                        if lid is not None:
                            doc._exec_photocraft(
                                "gradient.fill.set",
                                {
                                    "layer": lid,
                                    "angle": float(ang_val),
                                    "scale": float(scl_val),
                                    "stops": stops,
                                },
                            )
                    else:
                        hex_c = self._extract_hex_color(t_obj) or "#000000"
                        res = doc._exec_photocraft("layer.newFillLayer.solidColor", {"color": hex_c})
                        lid = int(res["layer"]) if isinstance(res, dict) and "layer" in res else None
                else:
                    res = doc._exec_photocraft("layer.newFillLayer.solidColor", {"color": "#000000"})
                    lid = int(res["layer"]) if isinstance(res, dict) and "layer" in res else None

                if lid is not None:
                    if isinstance(prev_active, LayerSet) and prev_active.id:
                        doc._exec_photocraft(
                            "layer.moveTo",
                            {"layer": lid, "target": prev_active.id, "position": "into"},
                        )
                    if clipped:
                        doc._exec_photocraft("layer.setProps", {"layer": lid, "clipped": True})

                parent_container: Any = prev_active if isinstance(prev_active, LayerSet) else doc
                fill_lyr = ArtLayer(
                    parent=parent_container,
                    name="Color Fill 1",
                    layer_id=lid,
                    bounds=(0.0, 0.0, float(doc.width), float(doc.height)),
                    kind=LayerKind.SolidFillLayer,
                )
                fill_lyr._doc = doc
                if hasattr(parent_container, "artLayers"):
                    parent_container.artLayers._items.insert(0, fill_lyr)
                doc._layer_by_id[fill_lyr.id] = fill_lyr
                doc._active_layer = fill_lyr
                return ActionDescriptor()
            return ActionDescriptor()

        if event_name == "newPlacedLayer":
            res = doc._exec_photocraft("layer.smartObjects.convertToSmartObject", {})
            lid = int(res["layer"]) if isinstance(res, dict) and "layer" in res else None
            if not isinstance(doc._active_layer, ArtLayer):
                sm_lyr = ArtLayer(
                    parent=doc,
                    name=doc._active_layer.name if doc._active_layer else "Smart Layer",
                    layer_id=lid,
                    bounds=(0.0, 0.0, float(doc.width), float(doc.height)),
                    kind=LayerKind.SmartObjectLayer,
                )
                doc.artLayers._items.insert(0, sm_lyr)
                doc._layer_by_id[sm_lyr.id] = sm_lyr
                doc._active_layer = sm_lyr
            elif lid is not None:
                doc._active_layer._id = lid
                doc._layer_by_id[lid] = doc._active_layer
            return ActionDescriptor()

        if event_name == "mergeLayersNew":
            old_layer = doc._active_layer
            res = doc._exec_photocraft("layer.mergeLayers", {})
            merged_id = (
                int(res["layer"])
                if isinstance(res, dict) and "layer" in res
                else None
            )
            if merged_id is not None:
                # Drop stale objects for the merged-away group/layers.
                if old_layer is not None:
                    doc._remove_child(old_layer)
                merged = doc.find_layer_by_id(merged_id)
                if not isinstance(merged, ArtLayer):
                    merged = ArtLayer(
                        parent=doc,
                        name=old_layer.name if old_layer else "Merged Layer",
                        layer_id=merged_id,
                    )
                    doc.artLayers._items.insert(0, merged)
                    doc._layer_by_id[merged_id] = merged
                doc.refresh_layer_bounds(merged_id)
                doc._active_layer = merged
            elif not isinstance(old_layer, ArtLayer):
                m_lyr = ArtLayer(
                    parent=doc,
                    name=old_layer.name if old_layer else "Merged Layer",
                    bounds=old_layer.bounds
                    if old_layer
                    else (0.0, 0.0, float(doc.width), float(doc.height)),
                )
                doc.artLayers._items.insert(0, m_lyr)
                doc._layer_by_id[m_lyr.id] = m_lyr
                doc._active_layer = m_lyr
            return ActionDescriptor()

        if event_name == "duplicate" and descriptor is not None:
            ref = (
                descriptor.getReference(id_target)
                if descriptor.hasKey(id_target)
                else descriptor.getReference(id_null)
                if descriptor.hasKey(id_null)
                else None
            )
            target_layer = self._resolve_target_layer(ref)
            if target_layer is not None:
                dup = target_layer.duplicate()
                id_name = self.stringIDToTypeID("name")
                if descriptor.hasKey(id_name):
                    dup.name = descriptor.getString(id_name)
                doc._active_layer = dup
            return ActionDescriptor()

        if event_name == "fill":
            if descriptor is not None:
                id_using = self.stringIDToTypeID("using")
                if descriptor.hasKey(id_using):
                    fill_mode = self.typeIDToStringID(
                        descriptor.getEnumerationValue(id_using)
                    )
                else:
                    fill_mode = "contentAware"
            else:
                fill_mode = "contentAware"
            if fill_mode == "foregroundColor":
                fg = self.foregroundColor
                hex_c = f"#{int(round(fg.rgb.red)):02x}{int(round(fg.rgb.green)):02x}{int(round(fg.rgb.blue)):02x}"
                doc._exec_photocraft("edit.fill", {"contents": "color", "color": hex_c})
            else:
                doc._exec_photocraft("edit.fill", {"contents": "contentAware"})
            return ActionDescriptor()
        if event_name == "trim":
            doc.trim()
        elif event_name == "rotateEventEnum" and descriptor is not None:
            angle_id = self.stringIDToTypeID("angle")
            angle = descriptor.getDouble(angle_id) if descriptor.hasKey(angle_id) else 0.0
            doc.rotateCanvas(angle)
        elif event_name == "save" and descriptor is not None:
            in_id = self.stringIDToTypeID("in")
            if descriptor.hasKey(in_id):
                doc.saveAs(descriptor.getPath(in_id))
        return ActionDescriptor()

    def executeActionGet(self, reference: ActionReference) -> ActionDescriptor:
        desc = ActionDescriptor()
        target_layer = self._resolve_target_layer(reference)
        l, t, r, b = (0, 0, 100, 100)
        if target_layer is not None:
            b_tuple = target_layer.bounds
            l, t, r, b = (
                int(round(b_tuple[0])),
                int(round(b_tuple[1])),
                int(round(b_tuple[2])),
                int(round(b_tuple[3])),
            )
        bounds = ActionDescriptor()
        bounds.putInteger(self.stringIDToTypeID("left"), l)
        bounds.putInteger(self.stringIDToTypeID("top"), t)
        bounds.putInteger(self.stringIDToTypeID("right"), r)
        bounds.putInteger(self.stringIDToTypeID("bottom"), b)
        bounds.putInteger(self.stringIDToTypeID("width"), max(1, r - l))
        bounds.putInteger(self.stringIDToTypeID("height"), max(1, b - t))
        bounds.putUnitDouble(self.stringIDToTypeID("left"), self.stringIDToTypeID("pixelsUnit"), float(l))
        bounds.putUnitDouble(self.stringIDToTypeID("top"), self.stringIDToTypeID("pixelsUnit"), float(t))
        bounds.putUnitDouble(self.stringIDToTypeID("right"), self.stringIDToTypeID("pixelsUnit"), float(r))
        bounds.putUnitDouble(self.stringIDToTypeID("bottom"), self.stringIDToTypeID("pixelsUnit"), float(b))
        bounds.putUnitDouble(self.stringIDToTypeID("width"), self.stringIDToTypeID("pixelsUnit"), float(max(1, r - l)))
        bounds.putUnitDouble(self.stringIDToTypeID("height"), self.stringIDToTypeID("pixelsUnit"), float(max(1, b - t)))
        desc.putObject(self.stringIDToTypeID("bounds"), self.stringIDToTypeID("rectangle"), bounds)
        desc.putObject(self.stringIDToTypeID("boundsNoEffects"), self.stringIDToTypeID("rectangle"), bounds)

        # Populate boundingBox for paragraph text layers
        bbox = ActionDescriptor()
        if target_layer is not None and getattr(target_layer, "_box", None):
            bx = target_layer._box
            bw = int(round(bx.get("width", max(1, r - l))))
            bh = int(round(bx.get("height", max(1, b - t))))
            bl = int(round(bx.get("x", l)))
            bt = int(round(bx.get("y", t)))
            bbox.putInteger(self.stringIDToTypeID("left"), bl)
            bbox.putInteger(self.stringIDToTypeID("top"), bt)
            bbox.putInteger(self.stringIDToTypeID("right"), bl + bw)
            bbox.putInteger(self.stringIDToTypeID("bottom"), bt + bh)
            bbox.putInteger(self.stringIDToTypeID("width"), bw)
            bbox.putInteger(self.stringIDToTypeID("height"), bh)
        else:
            bbox = bounds
        desc.putObject(self.stringIDToTypeID("boundingBox"), self.stringIDToTypeID("boundingBox"), bbox)

        # Populate textKey descriptor for TextLayers
        if isinstance(target_layer, ArtLayer):
            tk = ActionDescriptor()
            txt = target_layer.textItem.contents
            tk.putString(self.stringIDToTypeID("textKey"), txt)

            tr_desc = ActionDescriptor()
            tr = getattr(target_layer, "_transform", [1.0, 0.0, 0.0, 1.0, 0.0, 0.0])
            tr_desc.putUnitDouble(self.stringIDToTypeID("xx"), self.stringIDToTypeID("pixelsUnit"), float(tr[0]))
            tr_desc.putUnitDouble(self.stringIDToTypeID("xy"), self.stringIDToTypeID("pixelsUnit"), float(tr[1]))
            tr_desc.putUnitDouble(self.stringIDToTypeID("yx"), self.stringIDToTypeID("pixelsUnit"), float(tr[2]))
            tr_desc.putUnitDouble(self.stringIDToTypeID("yy"), self.stringIDToTypeID("pixelsUnit"), float(tr[3]))
            tr_desc.putUnitDouble(self.stringIDToTypeID("tx"), self.stringIDToTypeID("pixelsUnit"), float(tr[4]))
            tr_desc.putUnitDouble(self.stringIDToTypeID("ty"), self.stringIDToTypeID("pixelsUnit"), float(tr[5]))
            tk.putObject(self.stringIDToTypeID("transform"), self.stringIDToTypeID("transform"), tr_desc)

            click_pt = ActionDescriptor()
            click_pt.putUnitDouble(self.stringIDToTypeID("horizontal"), self.stringIDToTypeID("percentUnit"), 50.0)
            click_pt.putUnitDouble(self.stringIDToTypeID("vertical"), self.stringIDToTypeID("percentUnit"), 50.0)
            tk.putObject(self.stringIDToTypeID("textClickPoint"), self.stringIDToTypeID("point"), click_pt)

            style_list = ActionList()
            yy = ((float(tr[2]) ** 2 + float(tr[3]) ** 2) ** 0.5) or 1.0
            saved_runs = getattr(target_layer, "_runs", [])
            if saved_runs:
                for run in saved_runs:
                    r_desc = ActionDescriptor()
                    r_desc.putInteger(self.stringIDToTypeID("from"), int(run.get("start", 0)))
                    r_desc.putInteger(self.stringIDToTypeID("to"), int(run.get("end", len(txt))))
                    st = run.get("style", {})
                    st_desc = ActionDescriptor()
                    ps_name = st.get("postscript_name") or st.get("font_family") or target_layer.textItem.font
                    st_desc.putString(self.stringIDToTypeID("fontPostScriptName"), str(ps_name))
                    sz_pt = float(st.get("size_pt", target_layer.textItem.size)) * yy
                    st_desc.putUnitDouble(
                        self.stringIDToTypeID("size"),
                        self.stringIDToTypeID("pointsUnit"),
                        sz_pt,
                    )
                    ld_raw = st.get("leading_pt")
                    ld_pt = (float(ld_raw) * yy) if ld_raw is not None else sz_pt
                    st_desc.putUnitDouble(
                        self.stringIDToTypeID("leading"),
                        self.stringIDToTypeID("pointsUnit"),
                        ld_pt,
                    )
                    if "tracking" in st and st["tracking"] is not None:
                        st_desc.putInteger(
                            self.stringIDToTypeID("tracking"),
                            int(round(float(st["tracking"]))),
                        )
                    c_desc = ActionDescriptor()
                    col_dict = st.get("color")
                    if isinstance(col_dict, dict) and isinstance(col_dict.get("c"), list) and len(col_dict["c"]) >= 3:
                        c_arr = col_dict["c"]
                        c_desc.putDouble(self.stringIDToTypeID("red"), float(c_arr[0]) * 255.0)
                        c_desc.putDouble(self.stringIDToTypeID("green"), float(c_arr[1]) * 255.0)
                        c_desc.putDouble(self.stringIDToTypeID("blue"), float(c_arr[2]) * 255.0)
                    else:
                        col = target_layer.textItem.color
                        c_desc.putDouble(self.stringIDToTypeID("red"), float(col.rgb.red))
                        c_desc.putDouble(self.stringIDToTypeID("green"), float(col.rgb.green))
                        c_desc.putDouble(self.stringIDToTypeID("blue"), float(col.rgb.blue))
                    st_desc.putObject(self.stringIDToTypeID("color"), self.stringIDToTypeID("RGBColor"), c_desc)
                    r_desc.putObject(self.stringIDToTypeID("textStyle"), self.stringIDToTypeID("textStyle"), st_desc)
                    style_list.putObject(self.stringIDToTypeID("textStyleRange"), r_desc)
            else:
                r_desc = ActionDescriptor()
                r_desc.putInteger(self.stringIDToTypeID("from"), 0)
                r_desc.putInteger(self.stringIDToTypeID("to"), max(1, len(txt)))
                st_desc = ActionDescriptor()
                st_desc.putString(self.stringIDToTypeID("fontPostScriptName"), target_layer.textItem.font)
                st_desc.putUnitDouble(
                    self.stringIDToTypeID("size"),
                    self.stringIDToTypeID("pointsUnit"),
                    float(target_layer.textItem.size) * yy,
                )
                lead_val = (
                    float(target_layer.textItem.leading) * yy
                    if isinstance(target_layer.textItem.leading, (int, float))
                    else float(target_layer.textItem.size) * yy
                )
                st_desc.putUnitDouble(
                    self.stringIDToTypeID("leading"),
                    self.stringIDToTypeID("pointsUnit"),
                    lead_val,
                )
                c_desc = ActionDescriptor()
                col = target_layer.textItem.color
                c_desc.putDouble(self.stringIDToTypeID("red"), float(col.rgb.red))
                c_desc.putDouble(self.stringIDToTypeID("green"), float(col.rgb.green))
                c_desc.putDouble(self.stringIDToTypeID("blue"), float(col.rgb.blue))
                st_desc.putObject(self.stringIDToTypeID("color"), self.stringIDToTypeID("RGBColor"), c_desc)
                r_desc.putObject(self.stringIDToTypeID("textStyle"), self.stringIDToTypeID("textStyle"), st_desc)
                style_list.putObject(self.stringIDToTypeID("textStyleRange"), r_desc)
            tk.putList(self.stringIDToTypeID("textStyleRange"), style_list)

            para_list = ActionList()
            p_desc = ActionDescriptor()
            p_desc.putInteger(self.stringIDToTypeID("from"), 0)
            p_desc.putInteger(self.stringIDToTypeID("to"), max(1, len(txt)))
            ps_desc = ActionDescriptor()
            p_desc.putObject(self.stringIDToTypeID("paragraphStyle"), self.stringIDToTypeID("paragraphStyle"), ps_desc)
            para_list.putObject(self.stringIDToTypeID("paragraphStyleRange"), p_desc)
            tk.putList(self.stringIDToTypeID("paragraphStyleRange"), para_list)

            desc.putObject(self.stringIDToTypeID("textKey"), self.stringIDToTypeID("textKey"), tk)

        return desc


__all__ = [
    "ActionDescriptor",
    "ActionList",
    "ActionReference",
    "AnchorPosition",
    "Application",
    "ArtLayer",
    "ArtLayers",
    "AutoKernType",
    "BlendMode",
    "CMYKColor",
    "ColorBlendMode",
    "ColorModel",
    "DescValueType",
    "DialogModes",
    "Document",
    "Documents",
    "ElementPlacement",
    "FormatOptionsType",
    "HSBColor",
    "JPEGSaveOptions",
    "Justification",
    "LabColor",
    "Language",
    "Layer",
    "LayerKind",
    "LayerSet",
    "LayerSets",
    "PNGSaveOptions",
    "PathItem",
    "Photoshop",
    "PhotoshopPythonAPIError",
    "PhotoshopSaveOptions",
    "PointKind",
    "PurgeTarget",
    "RGBColor",
    "RasterizeType",
    "SaveOptions",
    "Selection",
    "SolidColor",
    "TextItem",
    "TypeUnits",
    "Units",
    "enumerations",
]
