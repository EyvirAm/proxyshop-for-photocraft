"""
* GUI: File Path Model

QML model exposing well-known filesystem paths.
"""
from __future__ import annotations
from PySide6.QtCore import Property, QObject, QUrl, Signal, Slot

from src._state import PATH


class FilePathModel(QObject):
    """QML model exposing well-known filesystem paths."""
    @Property(QUrl)
    def app_root(self) -> QUrl:
        """App root."""
        return QUrl.fromLocalFile(PATH.CWD)

    @Property(QUrl)
    def out_directory(self) -> QUrl:
        """Out directory."""
        return QUrl.fromLocalFile(PATH.OUT)

    @Property(QUrl)
    def templates_directory(self) -> QUrl:
        """Templates directory."""
        return QUrl.fromLocalFile(PATH.TEMPLATES)

    _plugins_directory_signal = Signal()

    @Property(QUrl, notify=_plugins_directory_signal)
    def plugins_directory(self) -> QUrl:
        """Plugins directory."""
        return QUrl.fromLocalFile(PATH.PLUGINS)

    _preview_img_fallback_signal = Signal()

    @Property(str, notify=_preview_img_fallback_signal)
    def preview_img_fallback(self) -> str:
        """Preview img fallback."""
        return PATH.SRC_IMG_NOTFOUND.as_uri()

    @Slot(str, result=str)
    def get_preferences_path(self, file_name: str) -> str:
        """Return the preferences path."""
        return (PATH.SRC_DATA_PREFERENCES / file_name).as_uri()
