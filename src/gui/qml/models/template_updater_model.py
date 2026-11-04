"""
* Template Updater Model

Exposes every known template to QML, checks Google Drive for new versions and
performs the downloads triggered from the updater window.
"""
from __future__ import annotations
from asyncio import ensure_future, gather, to_thread
from functools import cached_property
from threading import Lock

from pydantic import BaseModel
from PySide6.QtCore import Property, QObject, Signal, Slot

from src._loader import AppTemplate, PluginLibrary, TemplateLibrary
from src._state import AppEnvironment
from src.enums.mtg import LayoutCategory
from src.gui.qml.models.pydantic_q_list_model import PydanticQListModel
from src.utils.asynchronic import run_in_thread
from src.utils.data_structures import find_index, find_item, get_item
from src.utils.hexapi import check_api_keys


class DownloadableTemplateDetails(BaseModel):
    """One row of the template updater list.

    The ``handler`` is attached after construction and points at the
    ``AppTemplate`` responsible for checking and installing the update.
    """

    file_name: str
    google_drive_id: str | None
    img: str
    plugin: str
    plugin_id: str
    template_names: list[str]
    template_classes: list[str]
    layout_categories: list[LayoutCategory]
    installed_version: str
    available_version: str
    download_size: int
    """bytes"""
    downloading: bool = False

    @cached_property
    def handler(self) -> AppTemplate:
        """The ``AppTemplate`` backing this row, injected by the model."""
        raise ValueError("Download handler is not specified")


_data_fetch_lock = Lock()


class TemplateUpdaterModel(PydanticQListModel[DownloadableTemplateDetails]):
    """QML list model that drives the template updater window."""

    item_model = DownloadableTemplateDetails

    def __init__(
        self,
        app_env: AppEnvironment,
        plugin_library: PluginLibrary,
        parent: QObject | None = None,
        items: list[DownloadableTemplateDetails] | None = None,
        selected_index: int = -1,
    ) -> None:
        self._app_env = app_env
        self._plugin_library = plugin_library
        self._template_library = plugin_library.template_library

        self._fetching_data = False

        plugin_library.template_library_changed.add_listener(
            self._on_template_library_changed
        )

        super().__init__(parent, items, selected_index)

    _fetching_data_changed = Signal(name="fetchingDataChanged")

    @Property(bool, notify=_fetching_data_changed)
    def fetching_data(self) -> bool:  # pyright: ignore[reportRedeclaration]
        """Whether a metadata refresh is currently running."""
        return self._fetching_data

    @fetching_data.setter
    def fetching_data(self, value: bool) -> None:
        """Set update the refresh flag and notify QML when it changes."""
        if value != self._fetching_data:
            self._fetching_data = value
            self._fetching_data_changed.emit()

    @Slot()
    def fetch_data(self) -> None:
        """Start a metadata refresh without blocking the UI thread."""
        ensure_future(self.handle_fetch_data())

    _update_available = Signal(name="updateAvailable")

    async def handle_fetch_data(self) -> bool:
        """Check every template for updates and rebuild the item list.

        Returns:
            True when at least one installed template has a newer version.
        """
        if not _data_fetch_lock.acquire(False):
            return False

        try:
            self.fetching_data = True  # pyright: ignore[reportAttributeAccessIssue]

            await check_api_keys(self._app_env)

            await gather(
                *[
                    to_thread(template.check_for_update)
                    for template in self._template_library.templates
                ]
            )

            self.beginResetModel()
            self.items = [
                DownloadableTemplateDetails(
                    file_name=template.file_name,
                    google_drive_id=template.google_drive_id,
                    img=str(
                        template.get_path_preview(
                            class_name=(
                                first_item := next(
                                    iter(template.all_classes_and_layouts.items())
                                )
                            )[0],
                            class_type=first_item[1][0],
                        ).as_uri()
                    ),
                    plugin=template.plugin.name if template.plugin else "",
                    plugin_id=template.plugin.id if template.plugin else "",
                    template_names=template.all_names,
                    template_classes=template.all_classes,
                    layout_categories=template.supported_layout_categories,
                    installed_version=template.version or "",
                    available_version=template.update_version or "",
                    download_size=template.update_size or 0,
                )
                for template in self._template_library.templates
            ]
            for item, template in zip(self.items, self._template_library.templates):
                item.handler = template
            self.selected_index = 0  # pyright: ignore[reportAttributeAccessIssue]
            self.endResetModel()

            self.fetching_data = False  # pyright: ignore[reportAttributeAccessIssue]

            if update_available := bool(
                find_item(
                    self.items,
                    lambda item: bool(
                        item.installed_version
                        and item.available_version
                        and item.installed_version != item.available_version
                    ),
                )
            ):
                self._update_available.emit()
            return update_available
        finally:
            _data_fetch_lock.release()

    @Slot(int)
    def download_template(self, index: int) -> None:
        """Download the template shown at ``index`` in the model."""
        if index < 0 or index >= self.rowCount():
            return

        ensure_future(self._handle_template_download(index))

    async def _handle_template_download(self, index: int) -> None:
        item = self.items[index]
        q_index = self.createIndex(index, 0)

        item.downloading = True
        changed_fields: list[int] = [self.get_role("downloading")]
        self.dataChanged.emit(q_index, q_index, changed_fields)
        if await to_thread(item.handler.update_template):
            item.installed_version = item.handler.version or ""
            changed_fields.append(self.get_role("installed_version"))
        item.downloading = False
        self.dataChanged.emit(q_index, q_index, changed_fields)

    @Slot()
    def save_versions(self) -> None:
        """Persist the installed template versions to disk."""
        self._template_library.save_template_versions()

    _template_library_change_lock = Lock()

    async def _handle_template_library_change(
        self, template_library: TemplateLibrary
    ) -> None:
        with self._template_library_change_lock:
            self._template_library.save_template_versions()
            self._template_library = template_library
            if current_template := get_item(self.items, self._selected_index):
                await self.handle_fetch_data()
                new_idx = find_index(
                    self.items,
                    lambda item: (
                        item.file_name == current_template.file_name
                        and item.plugin_id == current_template.plugin_id
                    ),
                )
                if new_idx > -1:
                    self.selected_index = new_idx  # pyright: ignore[reportAttributeAccessIssue]
            else:
                self.beginResetModel()
                self.items = []
                self.selected_index = 0  # pyright: ignore[reportAttributeAccessIssue]
                self.endResetModel()

    def _on_template_library_changed(self, template_library: TemplateLibrary) -> None:
        run_in_thread(self._handle_template_library_change(template_library))
