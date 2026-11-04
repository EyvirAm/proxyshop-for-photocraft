"""
* GUI: PhotoCraft Setup Model

Asks for the PhotoCraft CLI path when it cannot be found automatically.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Property, QObject, QUrl, Signal, Slot

from src.utils.adobe import PhotoshopHandler
from src.utils.photocraft import (
    locate_photocraft_cli,
    resolve_photocraft_cli,
    save_photocraft_cli,
)
from src.utils.threading import ThreadInitializedInstance


class PhotocraftSetupModel(QObject):
    """QML model that requests the PhotoCraft CLI location on first launch."""

    def __init__(
        self,
        app_initializer: ThreadInitializedInstance[PhotoshopHandler],
        parent: QObject | None = None,
        *,
        objectName: str | None = None,
    ) -> None:
        super().__init__(parent, objectName=objectName)
        self._app_initializer = app_initializer
        self._required = locate_photocraft_cli() is None
        self._error = ""

    _required_changed = Signal(name="requiredChanged")

    @Property(bool, notify=_required_changed)
    def required(self) -> bool:  # pyright: ignore[reportRedeclaration]
        """Whether the GUI should ask the user for the PhotoCraft CLI path."""
        return self._required

    @required.setter
    def required(self, value: bool) -> None:
        """Update whether the GUI still needs to ask for the PhotoCraft path."""
        if value != self._required:
            self._required = value
            self._required_changed.emit()

    _error_changed = Signal(name="errorChanged")

    @Property(str, notify=_error_changed)
    def error(self) -> str:  # pyright: ignore[reportRedeclaration]
        """Validation error for the last selected path, if any."""
        return self._error

    @error.setter
    def error(self, value: str) -> None:
        """Update the validation error shown to the user."""
        if value != self._error:
            self._error = value
            self._error_changed.emit()

    @Slot(str)
    def set_path(self, value: str) -> None:
        """Validate and remember a user-selected PhotoCraft path."""
        local_path = QUrl(value).toLocalFile()
        candidate = resolve_photocraft_cli(Path(local_path)) if local_path else None
        if not candidate:
            self.error = "Select photocraft-cli.exe or a PhotoCraft installation folder."
            return

        save_photocraft_cli(candidate)
        self.error = ""
        self.required = False

        from src.startup import photoshop_checks

        self._app_initializer.add_listener(photoshop_checks)
        self._app_initializer.initialize()

    @Slot()
    def cancel(self) -> None:
        """Stop asking for the path for this session."""
        self.required = False
        self.error = "PhotoCraft is required to render cards."
