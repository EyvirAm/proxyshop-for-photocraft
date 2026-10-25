"""
* Utils: Photocraft Backend Adapter (formerly Adobe Photoshop)
"""
from __future__ import annotations

from _ctypes import ArgumentError, COMError
from collections.abc import Callable
from contextlib import suppress
from ctypes import c_uint32
from functools import cached_property, wraps
from typing import Self, TypedDict

from packaging.version import parse
from photoshop.api import (
    ActionDescriptor,
    ActionReference,
    Application,
    PhotoshopPythonAPIError,
)
from photoshop.api._artlayer import ArtLayer
from photoshop.api._core import Photoshop
from photoshop.api._document import Document
from photoshop.api._layer import Layer
from photoshop.api._layerSet import LayerSet
from photoshop.api.enumerations import DialogModes, ElementPlacement, TypeUnits, Units
from win32api import FormatMessage

from src._state import AppEnvironment
from src.utils.photocraft import PhotocraftHandler
from src.utils.windows import (
    WindowState,
    get_window_handle_by_process_file_path_suffix,
    set_window_state,
)

"""
* Types & Definitions
"""

# Common Layer Objects
LayerContainer = LayerSet, Document
LayerObject = LayerSet, ArtLayer

# Common Layer Types
LayerContainerTypes = LayerSet | Document
LayerObjectTypes = ArtLayer | LayerSet

# Common Photoshop/Photocraft Exceptions
PS_EXCEPTIONS = (
    PhotoshopPythonAPIError,
    ArgumentError,
    COMError,
    AttributeError,
    IndexError,
    KeyError,
    ValueError,
    TypeError,
    OSError,
)

_CHAR_ID_TO_TYPE_ID_CACHE: dict[tuple[object, ...], int] = {}
_TYPE_ID_TO_CHAR_ID_CACHE: dict[tuple[object, ...], str] = {}
_STRING_ID_TO_TYPE_ID_CACHE: dict[tuple[object, ...], int] = {}
_TYPE_ID_TO_STRING_ID_CACHE: dict[tuple[object, ...], str] = {}
_CHAR_ID_TO_STRING_ID_CACHE: dict[tuple[object, ...], str] = {}
_STRING_ID_TO_CHAR_ID_CACHE: dict[tuple[object, ...], str] = {}
_SCALE_BY_DPI_CACHE: dict[tuple[object, ...], int] = {}


def _cache_result[**P, T](
    result_cache: dict[tuple[object, ...], T],
    key_func: Callable[..., tuple[object, ...]] | None = None,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Cache a method result without retaining the method's instance."""

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            key = (
                key_func(*args, **kwargs)
                if key_func
                else (args[1:], *sorted(kwargs.items()))
            )
            if key not in result_cache:
                result_cache[key] = func(*args, **kwargs)
            return result_cache[key]

        return wrapper

    return decorator


def _scale_by_dpi_cache_key(handler: Application, value: float) -> tuple[object, ...]:
    return (handler.activeDocument.width, value)


PS_ERROR_CODES: dict[int, str] = {
    -2147417846: "Photocraft is currently busy, close any dialog boxes and stop any pending actions.",
    -2147023170: "Unable to make connection with Photocraft.",
    -2147352565: "Failed to load a PSD template or other file.",
    -2147352567: "Photocraft does not appear to be installed.",
    -2147220261: "Invalid data type passed to action descriptor function.",
    -2147213497: "Tried to transform, select, or translate an empty layer.",
    -2147212704: "Action descriptor or layer object key/property is missing.",
    -2147220262: "Photocraft tried to load a PSD template or file that doesn't exist.",
    -2147220279: "Wrong type of value passed to an object property.",
    -2147213327: "Tried to interact with a text layer that is rasterized or has an uninstalled font.",
    -2147213404: "Tried to delete a layer that doesn't exist.",
}


# Layer bounds: left, top, right, bottom
LayerBounds = tuple[float, float, float, float]


class LayerDimensions(TypedDict):
    """Calculated layer dimension info for a layer."""

    width: float
    height: float
    center_x: float
    center_y: float
    left: float
    right: float
    top: float
    bottom: float


"""
* Util Classes
"""


class ApplicationHandler(PhotocraftHandler):
    """Wrapper for the Photocraft Application class."""

    def __init__(self, env: AppEnvironment | None = None):
        version = env.PS_VERSION if env else None
        super().__init__(version=version)
        self._env = env

        with suppress(Exception):
            self.displayDialogs = (
                DialogModes.DisplayErrorDialogs
                if (env and env.PS_ERROR_DIALOG)
                else DialogModes.DisplayNoDialogs
            )

    @cached_property
    def _env(self) -> AppEnvironment | None:
        return None

    def is_error_dialog_enabled(self) -> bool:
        if self._env:
            return self._env.PS_ERROR_DIALOG
        return False


class PhotoshopHandler(ApplicationHandler):
    """Wrapper for a single global Photocraft-backed Application object."""

    _instance = None
    _window_handle: int | None = None

    @property
    def window_handle(self) -> int | None:
        if self._window_handle is None:
            self._window_handle = get_window_handle_by_process_file_path_suffix(
                "photocraft.exe"
            )
        return self._window_handle

    def __new__(cls, env: AppEnvironment | None = None) -> Self:
        if cls._instance is None:
            try:
                cls._instance = super().__new__(cls)
            except PS_EXCEPTIONS:
                cls._instance = super(Photoshop, cls).__new__(cls)
        return cls._instance

    def refresh_app(self) -> OSError | None:
        if not self.is_running():
            try:
                super().__init__(env=self._env)
                self.preferences.rulerUnits = Units.Pixels
                self.preferences.typeUnits = TypeUnits.TypePoints
            except Exception as e:  # noqa: BLE001
                return OSError(get_photoshop_error_message(e))
            self._window_handle = None
        return None

    def set_window_state(self, state: WindowState) -> None:
        if (handle := self.window_handle) is not None:
            set_window_state(handle, state)

    @classmethod
    def is_running(cls) -> bool:
        with suppress(Exception):
            if cls._instance and cls._instance.version:
                return True
        return False

    @_cache_result(_CHAR_ID_TO_TYPE_ID_CACHE)
    def charIDToTypeID(self, index: str) -> int:
        return super().charIDToTypeID(index)

    def cID(self, index: str) -> int:
        return self.charIDToTypeID(index)

    @_cache_result(_TYPE_ID_TO_CHAR_ID_CACHE)
    def typeIDToCharID(self, index: int) -> str:
        return super().typeIDToCharID(index)

    @_cache_result(_STRING_ID_TO_TYPE_ID_CACHE)
    def stringIDToTypeID(self, index: str) -> int:
        return super().stringIDToTypeID(index)

    def sID(self, index: str) -> int:
        return self.stringIDToTypeID(index)

    @_cache_result(_TYPE_ID_TO_STRING_ID_CACHE)
    def typeIDToStringID(self, index: int) -> str:
        return super().typeIDToStringID(index)

    @_cache_result(_CHAR_ID_TO_STRING_ID_CACHE)
    def charIDToStringID(self, index: str) -> str:
        return self.typeIDToStringID(self.charIDToTypeID(index))

    @_cache_result(_STRING_ID_TO_CHAR_ID_CACHE)
    def stringIDToCharID(self, index: str) -> str:
        return self.typeIDToCharID(self.stringIDToTypeID(index))

    def executeAction(
        self,
        event_id: int,
        descriptor: ActionDescriptor | None = None,
        display_dialogs: DialogModes = DialogModes.DisplayNoDialogs,
    ) -> ActionDescriptor:
        if self.is_error_dialog_enabled():
            return super().executeAction(
                event_id, descriptor, DialogModes.DisplayErrorDialogs
            )
        return super().executeAction(event_id, descriptor, display_dialogs)

    @cached_property
    def supports_target_text_replace(self) -> bool:
        return self.version_meets_requirement("22.0.0")

    @cached_property
    def supports_webp(self) -> bool:
        return self.version_meets_requirement("23.2.0")

    @cached_property
    def supports_generative_fill(self) -> bool:
        return self.version_meets_requirement("24.6.0")

    @cached_property
    def supports_uxp_scripts(self) -> bool:
        return self.version_meets_requirement("23.5.0")

    def version_meets_requirement(self, value: str) -> bool:
        return parse(self.version) >= parse(value)

    @_cache_result(_SCALE_BY_DPI_CACHE, _scale_by_dpi_cache_key)
    def scale_by_dpi(self, value: float) -> int:
        return int((self.activeDocument.width / 3264) * value)


class ReferenceLayer(ArtLayer):
    """A static ArtLayer whose properties such as width or height are not going to change."""

    def __init__(
        self, parent: Photoshop | None = None, app: PhotoshopHandler | None = None
    ):
        self._global_app = app if app else PhotoshopHandler()
        self._wrapped_layer = parent if isinstance(parent, ArtLayer) else None
        super().__init__(parent=parent)

    def duplicate(
        self,
        relativeObject: Layer | None = None,
        insertionLocation: ElementPlacement | None = None,
    ) -> ArtLayer:
        return ReferenceLayer(super().duplicate(relativeObject, insertionLocation))

    @cached_property
    def id(self) -> int:  # pyright: ignore[reportIncompatibleMethodOverride]
        return super().id

    @cached_property
    def action_getter(self) -> ActionDescriptor:
        ref = ActionReference()
        ref.putIdentifier(self._global_app.sID("layer"), self.id)
        return self._global_app.executeActionGet(ref)

    @property
    def bounds(self) -> LayerBounds:  # pyright: ignore[reportIncompatibleMethodOverride]
        if self._wrapped_layer is not None:
            return self._wrapped_layer.bounds
        return super().bounds

    @bounds.setter
    def bounds(self, value: LayerBounds) -> None:
        if self._wrapped_layer is not None:
            self._wrapped_layer._bounds = value
        self._bounds = value

    @property
    def bounds_no_effects(self) -> LayerBounds:
        return self.bounds

    @bounds_no_effects.setter
    def bounds_no_effects(self, value: LayerBounds) -> None:
        self.bounds = value

    @property
    def dims(self) -> LayerDimensions:
        if hasattr(self, "_custom_dims") and self._custom_dims is not None:
            return self._custom_dims
        return self.get_dimensions_from_bounds(self.bounds)

    @dims.setter
    def dims(self, value: LayerDimensions) -> None:
        self._custom_dims = value

    @property
    def dims_no_effects(self) -> LayerDimensions:
        return self.get_dimensions_from_bounds(self.bounds_no_effects)

    @dims_no_effects.setter
    def dims_no_effects(self, value: LayerDimensions) -> None:
        self._custom_dims = value

    @staticmethod
    def get_dimensions_from_bounds(
        bounds: tuple[float, float, float, float],
    ) -> LayerDimensions:
        width = int(bounds[2] - bounds[0])
        height = int(bounds[3] - bounds[1])
        return LayerDimensions(
            width=width,
            height=height,
            center_x=round((width / 2) + bounds[0]),
            center_y=round((height / 2) + bounds[1]),
            left=int(bounds[0]),
            right=int(bounds[2]),
            top=int(bounds[1]),
            bottom=int(bounds[3]),
        )


def try_photoshop[**P, T](func: Callable[P, T]) -> Callable[P, T | None]:
    """Decorator to handle trying to run a Photocraft/Photoshop action and allowing exceptions to fail silently."""

    def wrapper(*args: P.args, **kwargs: P.kwargs):
        try:
            return func(*args, **kwargs)
        except PS_EXCEPTIONS:
            return None

    return wrapper


def get_photoshop_error_message(err: Exception) -> str:
    return (
        "Photocraft is currently busy, close any dialogs and stop any actions.\n"
        if "busy" in str(err).lower()
        else f"Photocraft backend error: {err}\n"
    )


def get_com_error(signed_int: int) -> str:
    try:
        err = FormatMessage(signed_int)
    except Exception as e:  # noqa: BLE001
        try:
            unsigned_int = c_uint32(signed_int).value
            err = FormatMessage(unsigned_int) or e.args[2]
        except Exception as e:  # noqa: BLE001
            err = str(e)
    return err
