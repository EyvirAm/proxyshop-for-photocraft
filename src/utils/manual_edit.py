"""
* Utils: Manual Editing Sessions
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from contextlib import suppress
from logging import getLogger
from pathlib import Path
from time import monotonic, sleep
from typing import TYPE_CHECKING

import win32gui

from src._state import PATH
from src.utils.photocraft import find_photocraft_cli
from src.utils.windows import (
    WindowState,
    get_window_handle_by_process_id,
    set_window_state,
)

if TYPE_CHECKING:
    from src.templates._core import BaseTemplate

_logger = getLogger(__name__)

DEFAULT_MANUAL_EDIT_TITLE = "Manual editing"
DEFAULT_MANUAL_EDIT_MESSAGE = (
    "Edit the card, then save the file with Ctrl+S.\n"
    "Return to the Proxyshop window and press OK to continue."
)


def find_photocraft_app() -> str | None:
    """Locate the PhotoCraft desktop executable used for manual editing."""
    env_app = os.getenv("PHOTOCRAFT_APP")
    if env_app and Path(env_app).is_file():
        return env_app

    cli_path = Path(find_photocraft_cli())
    for name in ("photocraft.exe", "photocraft"):
        if (candidate := cli_path.with_name(name)).is_file():
            return str(candidate)

    program_files = Path(os.getenv("ProgramFiles", r"C:\Program Files"))
    local_appdata = Path(
        os.getenv("LOCALAPPDATA", r"C:\Users\usuario\AppData\Local")
    )
    repo_root = Path(__file__).resolve().parents[3] / "photocraft-repo"
    candidates = [
        program_files / "PhotoCraft" / "photocraft.exe",
        local_appdata / "Programs" / "PhotoCraft" / "photocraft.exe",
        local_appdata / "PhotoCraft" / "photocraft.exe",
        repo_root / "target" / "release" / "photocraft.exe",
        repo_root / "target" / "debug" / "photocraft.exe",
        repo_root / "target" / "release" / "photocraft",
        repo_root / "target" / "debug" / "photocraft",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)

    return shutil.which("photocraft")


class ManualEditSession:
    """A temporary PSD opened in PhotoCraft for user edits."""

    def __init__(
        self,
        template: BaseTemplate,
        title: str,
        message: str,
    ) -> None:
        self.template = template
        self.title = title
        self.message = message
        self.temp_dir: Path | None = None
        self.psd_path: Path | None = None
        self.process: subprocess.Popen[bytes] | None = None
        self.window_handle: int | None = None
        self._initial_mtime_ns: int | None = None

    @classmethod
    def start(
        cls,
        template: BaseTemplate,
        title: str | None = None,
        message: str | None = None,
    ) -> ManualEditSession | None:
        """Save the current document and open it in the PhotoCraft desktop app."""
        app_path = find_photocraft_app()
        if not app_path:
            _logger.error(
                "Manual editing requires the PhotoCraft desktop application, "
                "but photocraft.exe could not be found."
            )
            return None

        session = cls(
            template,
            title=title or DEFAULT_MANUAL_EDIT_TITLE,
            message=message or DEFAULT_MANUAL_EDIT_MESSAGE,
        )
        if not session._write_snapshot():
            session.cleanup()
            return None
        if not session._open_editor(app_path):
            session.cleanup()
            return None
        try:
            session._show_overlay()
        except Exception:
            _logger.exception("Unable to show the manual editing message.")
        return session

    def _write_snapshot(self) -> bool:
        """Write the current render to a temporary PSD."""
        template_file = Path(self.template.layout.template_file)
        self.temp_dir = Path(
            tempfile.mkdtemp(prefix="manual_edit_", dir=PATH.TMP)
        )
        self.psd_path = self.temp_dir / template_file.name
        try:
            self.template.docref.saveAs(str(self.psd_path), asCopy=True)
        except Exception:
            _logger.exception("Unable to save the PSD for manual editing.")
            return False
        if not self.psd_path.is_file():
            _logger.error(
                "The PSD for manual editing was not written: %s", self.psd_path
            )
            return False
        self._initial_mtime_ns = self.psd_path.stat().st_mtime_ns
        return True

    def _open_editor(self, app_path: str) -> bool:
        """Open the snapshot in a dedicated PhotoCraft instance."""
        try:
            self.process = subprocess.Popen(
                [app_path, "--new-instance", str(self.psd_path)],
                cwd=str(PATH.CWD),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except OSError:
            _logger.exception("Unable to start PhotoCraft for manual editing.")
            return False

        deadline = monotonic() + 30
        while monotonic() < deadline:
            if (
                handle := get_window_handle_by_process_id(self.process.pid)
            ) is not None:
                self.window_handle = handle
                with suppress(Exception):
                    set_window_state(handle, WindowState.NORMAL)
                    win32gui.SetForegroundWindow(handle)
                return True
            if self.process.poll() is not None:
                _logger.error(
                    "PhotoCraft exited before its manual editing window opened."
                )
                return False
            sleep(0.25)

        _logger.warning(
            "PhotoCraft started, but its window could not be located. "
            "The manual editing message will be centered on the screen."
        )
        return True

    def _show_overlay(self) -> None:
        if self.template.message_dialog is not None:
            self.template.message_dialog.show_manual_edit_overlay(
                self.window_handle, self.title, self.message
            )

    def _hide_overlay(self) -> None:
        if self.template.message_dialog is not None:
            self.template.message_dialog.hide_manual_edit_overlay()

    def file_changed(self) -> bool:
        """Whether the user wrote the manual editing PSD."""
        if (
            self.psd_path is None
            or self._initial_mtime_ns is None
            or not self.psd_path.is_file()
        ):
            return False
        with suppress(OSError):
            return self.psd_path.stat().st_mtime_ns != self._initial_mtime_ns
        return False

    def stop(self) -> bool:
        """Close PhotoCraft and report whether the snapshot was saved."""
        changed = self.file_changed()
        self._hide_overlay()
        self._close_editor()
        return changed

    def _close_editor(self) -> None:
        process = self.process
        self.process = None
        if process is None or process.poll() is not None:
            return
        with suppress(Exception):
            process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            with suppress(Exception):
                process.kill()
                process.wait(timeout=5)

    def cleanup(self) -> None:
        """Remove the temporary PSD and its directory."""
        self._close_editor()
        if self.temp_dir is not None:
            shutil.rmtree(self.temp_dir, ignore_errors=True)
        self.temp_dir = None
        self.psd_path = None
