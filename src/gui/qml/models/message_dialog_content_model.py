from __future__ import annotations
from asyncio import Future, get_running_loop
from collections.abc import Callable
from contextlib import suppress
from typing import Any

from PySide6.QtCore import Property, QObject, QRect, Signal, Slot
from PySide6.QtGui import QGuiApplication, QWindow

from src.utils.asynchronic import try_threadsafe_set_result


class MessageDialogContentModel(QObject):
    def __init__(
        self,
        /,
        title: str = "",
        text: str = "",
        informative_text: str = "",
        detailed_text: str = "",
        ok_callback: Callable[[], Any] | None = None,
        cancel_callback: Callable[[], Any] | None = None,
        parent: QObject | None = None,
        *,
        objectName: str | None = None,
    ) -> None:
        super().__init__(parent, objectName=objectName)
        self._title = title
        self._text = text
        self._informative_text = informative_text
        self._detailed_text = detailed_text
        self.ok_callback = ok_callback
        self.cancel_callback = cancel_callback

        self._manual_edit_overlay_visible = False
        self._manual_edit_overlay_title = ""
        self._manual_edit_overlay_text = ""
        self._manual_edit_overlay_x = 0
        self._manual_edit_overlay_y = 0
        self._manual_edit_overlay_width = 640
        self._manual_edit_overlay_height = 112
        self._manual_edit_overlay_handle: int | None = None
        self._manual_edit_overlay_window: QWindow | None = None
        self._manual_edit_overlay_shown.connect(self._apply_manual_edit_overlay)
        self._manual_edit_overlay_hidden.connect(self._clear_manual_edit_overlay)

    _title_changed = Signal()

    @Property(str, notify=_title_changed)
    def title(self) -> str:  # pyright: ignore[reportRedeclaration]
        return self._title

    @title.setter
    def title(self, value: str) -> None:
        if value != self._title:
            self._title = value
            self._title_changed.emit()

    _text_changed = Signal()

    @Property(str, notify=_text_changed)
    def text(self) -> str:  # pyright: ignore[reportRedeclaration]
        return self._text

    @text.setter
    def text(self, value: str) -> None:
        if value != self._text:
            self._text = value
            self._text_changed.emit()

    _informative_text_changed = Signal()

    @Property(str, notify=_informative_text_changed)
    def informative_text(self) -> str:  # pyright: ignore[reportRedeclaration]
        return self._informative_text

    @informative_text.setter
    def informative_text(self, value: str) -> None:
        if value != self._informative_text:
            self._informative_text = value
            self._informative_text_changed.emit()

    _detailed_text_changed = Signal()

    @Property(str, notify=_detailed_text_changed)
    def detailed_text(self) -> str:  # pyright: ignore[reportRedeclaration]
        return self._detailed_text

    @detailed_text.setter
    def detailed_text(self, value: str) -> None:
        if value != self._detailed_text:
            self._detailed_text = value
            self._detailed_text_changed.emit()

    @Slot()
    def ok(self) -> None:
        if self.ok_callback:
            self.ok_callback()

    @Slot()
    def cancel(self) -> None:
        if self.cancel_callback:
            self.cancel_callback()

    _dismissed = Signal(name="dismissed")

    def dismiss(self) -> None:
        self._dismissed.emit()

    dialog_requested = Signal(name="dialogRequested")

    """
    * Manual Editing Overlay
    """

    _manual_edit_overlay_shown = Signal(int, str, str)
    _manual_edit_overlay_hidden = Signal()
    _manual_edit_overlay_changed = Signal()

    def show_manual_edit_overlay(
        self, window_handle: int | None, title: str, text: str
    ) -> None:
        """Ask QML to show the overlay above the PhotoCraft window."""
        self._manual_edit_overlay_shown.emit(int(window_handle or 0), title, text)

    @Slot()
    def hide_manual_edit_overlay(self) -> None:
        """Hide the overlay shown for a manual editing session."""
        self._manual_edit_overlay_hidden.emit()

    @Slot(int, str, str)
    def _apply_manual_edit_overlay(
        self, window_handle: int, title: str, text: str
    ) -> None:
        if window_handle != self._manual_edit_overlay_handle:
            self._manual_edit_overlay_window = None
        self._manual_edit_overlay_handle = window_handle or None
        self._manual_edit_overlay_title = title
        self._manual_edit_overlay_text = text
        self._refresh_manual_edit_overlay_geometry()
        self._manual_edit_overlay_visible = True
        self._manual_edit_overlay_changed.emit()

    @Slot()
    def _clear_manual_edit_overlay(self) -> None:
        self._manual_edit_overlay_visible = False
        self._manual_edit_overlay_handle = None
        self._manual_edit_overlay_window = None
        self._manual_edit_overlay_changed.emit()

    @Slot()
    def refresh_manual_edit_overlay(self) -> None:
        if not self._manual_edit_overlay_visible:
            return
        self._refresh_manual_edit_overlay_geometry()
        self._manual_edit_overlay_changed.emit()

    def _refresh_manual_edit_overlay_geometry(self) -> None:
        rect: QRect | None = None
        if self._manual_edit_overlay_handle:
            if self._manual_edit_overlay_window is None:
                with suppress(Exception):
                    self._manual_edit_overlay_window = QWindow.fromWinId(
                        self._manual_edit_overlay_handle
                    )
            if self._manual_edit_overlay_window is not None:
                with suppress(Exception):
                    geometry = self._manual_edit_overlay_window.geometry()
                    if geometry.isValid():
                        rect = geometry
        if rect is None:
            screen = QGuiApplication.primaryScreen()
            if screen is not None:
                rect = screen.availableGeometry()
        if rect is None:
            return

        width = min(760, max(360, int(rect.width() * 0.72)))
        self._manual_edit_overlay_width = width
        self._manual_edit_overlay_height = 132
        self._manual_edit_overlay_x = rect.x() + (rect.width() - width) // 2
        self._manual_edit_overlay_y = rect.y() + 48

    @Property(bool, notify=_manual_edit_overlay_changed)
    def manual_edit_overlay_visible(self) -> bool:
        return self._manual_edit_overlay_visible

    @Property(str, notify=_manual_edit_overlay_changed)
    def manual_edit_overlay_title(self) -> str:
        return self._manual_edit_overlay_title

    @Property(str, notify=_manual_edit_overlay_changed)
    def manual_edit_overlay_text(self) -> str:
        return self._manual_edit_overlay_text

    @Property(int, notify=_manual_edit_overlay_changed)
    def manual_edit_overlay_x(self) -> int:
        return self._manual_edit_overlay_x

    @Property(int, notify=_manual_edit_overlay_changed)
    def manual_edit_overlay_y(self) -> int:
        return self._manual_edit_overlay_y

    @Property(int, notify=_manual_edit_overlay_changed)
    def manual_edit_overlay_width(self) -> int:
        return self._manual_edit_overlay_width

    @Property(int, notify=_manual_edit_overlay_changed)
    def manual_edit_overlay_height(self) -> int:
        return self._manual_edit_overlay_height

    def open_message_dialog(
        self,
        title: str = "",
        text: str = "",
        informative_text: str = "",
        detailed_text: str = "",
        ok_callback: Callable[[], Any] | None = None,
        cancel_callback: Callable[[], Any] | None = None,
    ) -> None:
        self.title = title  # pyright: ignore[reportAttributeAccessIssue]
        self.text = text  # pyright: ignore[reportAttributeAccessIssue]
        self.informative_text = informative_text  # pyright: ignore[reportAttributeAccessIssue]
        self.detailed_text = detailed_text  # pyright: ignore[reportAttributeAccessIssue]
        self.ok_callback = ok_callback
        self.cancel_callback = cancel_callback
        self.dialog_requested.emit()

    async def open_message_dialog_async(
        self,
        title: str = "",
        text: str = "",
        informative_text: str = "",
        detailed_text: str = "",
    ) -> bool:
        future: Future[bool] = get_running_loop().create_future()
        self.open_message_dialog(
            title=title,
            text=text,
            informative_text=informative_text,
            detailed_text=detailed_text,
            ok_callback=lambda: try_threadsafe_set_result(future, True),
            cancel_callback=lambda: try_threadsafe_set_result(future, False),
        )
        return await future
