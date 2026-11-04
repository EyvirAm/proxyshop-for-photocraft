"""
* GUI: Pydantic Qt Models

Generic Qt list/tree models backed by Pydantic models.
"""
from __future__ import annotations
from itertools import chain
from logging import getLogger
from typing import Any, override

from pydantic import BaseModel
from PySide6.QtCore import (
    Property,
    QAbstractItemModel,
    QAbstractListModel,
    QByteArray,
    QModelIndex,
    QObject,
    QPersistentModelIndex,
    Qt,
    Signal,
    Slot,
)

_logger = getLogger(__name__)


class TreeItem[T: BaseModel]:
    """Node in a tree of Pydantic items."""
    def __init__(self, data: T, parent: TreeItem[T] | None = None) -> None:
        self.children: list[TreeItem[T]] = []
        self.data = data
        self.parent: TreeItem[T] | None = None
        if parent:
            parent.append_child(self)

    def append_child(self, child: TreeItem[T]) -> None:
        """Append a child item and set its parent."""
        self.children.append(child)
        child.parent = self

    def child(self, row: int) -> TreeItem[T] | None:
        """Return the child at ``row``, if it exists."""
        return self.children[row] if -1 < row < self.child_count() else None

    def child_count(self) -> int:
        """Number of child items."""
        return len(self.children)

    def column_count(self) -> int:
        """Number of columns exposed to Qt."""
        return 1

    def row(self) -> int:
        """Return this item's row within its parent."""
        return self.parent.children.index(self) if self.parent else -1


class PydanticQItemModelBase[T: BaseModel]:
    """Shared role handling for Pydantic-backed Qt models."""
    item_model: type[T]
    _role_names: dict[int, QByteArray]
    _roles_reverse: dict[str, int]

    def roleNames(self) -> dict[int, QByteArray]:
        """Map role IDs to their QML names."""
        return self._role_names

    def get_role(self, property_name: str) -> int:
        """Return the role ID for a Pydantic field name."""
        return self._roles_reverse[property_name]


class PydanticQItemModel[T: BaseModel](PydanticQItemModelBase[T], QAbstractItemModel):
    """
    Item model that exposes Pydantic model's fields as roles to QML.

    Inheriting models have to set the Pydantic model's type to `item_model` field.
    """

    _root: TreeItem[T]

    def __init__(self, /, parent: QObject | None = None) -> None:
        self._roles: dict[int, str] = {
            Qt.ItemDataRole.UserRole + 1 + idx: field
            for idx, field in enumerate(self.item_model.model_fields)
        }
        self._roles_reverse: dict[str, int] = {
            field: idx for idx, field in self._roles.items()
        }
        self._role_names: dict[int, QByteArray] = {
            role: QByteArray(field.encode("utf-8"))
            for role, field in self._roles.items()
        }

        super().__init__(parent)

    @override
    def rowCount(
        self,
        parent: QModelIndex | QPersistentModelIndex = QModelIndex(),  # noqa: B008
    ) -> int:
        """Row count."""
        if parent.column() > 0:
            return 0

        parent_item: TreeItem[T] = (
            parent.internalPointer() if parent.isValid() else self._root
        )

        return parent_item.child_count()

    @override
    def columnCount(
        self,
        parent: QModelIndex | QPersistentModelIndex = QModelIndex(),  # noqa: B008
    ) -> int:
        """Number of columns exposed to Qt."""
        if parent.isValid():
            parent_item: TreeItem[T] = parent.internalPointer()
            return parent_item.column_count()
        return self._root.column_count()

    @override
    def data(
        self,
        index: QModelIndex | QPersistentModelIndex,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        """Return the data for the given index and role."""
        if not index.isValid() or role not in self._roles:
            return None
        tree_item: TreeItem[T] = index.internalPointer()
        return getattr(tree_item.data, self._roles[role])

    @override
    def index(
        self,
        row: int,
        column: int,
        parent: QModelIndex | QPersistentModelIndex = QModelIndex(),  # noqa: B008
    ) -> QModelIndex:
        """Return the model index for a row, column and parent."""
        if not self.hasIndex(row, column, parent=parent):
            return QModelIndex()

        parent_item: TreeItem[T] = (
            parent.internalPointer() if parent.isValid() else self._root
        )

        if child_item := parent_item.child(row):
            return self.createIndex(row, column, child_item)

        return QModelIndex()

    @override
    def parent(self, index: QModelIndex = QModelIndex()) -> QModelIndex:  # pyright: ignore[reportIncompatibleMethodOverride]  # noqa: B008
        """Return the parent model index of a child index."""
        if not index.isValid():
            return QModelIndex()

        child_item: TreeItem[T] = index.internalPointer()
        parent_item = child_item.parent

        if parent_item and parent_item != self._root:
            return self.createIndex(parent_item.row(), 0, parent_item)

        return QModelIndex()

    def index_of_item(self, item: TreeItem[T]) -> QModelIndex:
        """Index of item."""
        return self.createIndex(item.row(), 0, item)

    # region Properties

    selected_model_index_changed = Signal(QModelIndex, name="selectedModelIndexChanged")

    @Property(QModelIndex, notify=selected_model_index_changed)
    def selected_model_index(self) -> QModelIndex:  # pyright: ignore[reportRedeclaration]
        """Selected model index."""
        return self._selected_model_index

    def _set_selected_model_index(self, value: QModelIndex) -> None:
        item: TreeItem[T] | None = value.internalPointer()
        if not value.isValid() or not item:
            self._selected_model_index = value
            self.selected_model_index_changed.emit(value)
            return

        if value != self._selected_model_index:
            self._selected_model_index = value
            self.selected_model_index_changed.emit(value)

    @selected_model_index.setter
    def selected_model_index(self, value: QModelIndex) -> None:
        """Set the selected model index."""
        self._set_selected_model_index(value)

    # endregion Properties


class PydanticQListModel[T: BaseModel](PydanticQItemModelBase[T], QAbstractListModel):
    """
    List model that exposes Pydantic model's fields as roles to QML.

    Inheriting models have to set the Pydantic model's type to `item_model` field.
    """

    def __init__(
        self,
        parent: QObject | None = None,
        items: list[T] | None = None,
        selected_index: int = -1,
    ) -> None:
        self._roles: dict[int, str] = {
            Qt.ItemDataRole.UserRole + 1 + idx: field
            for idx, field in enumerate(
                chain(
                    self.item_model.model_fields, self.item_model.model_computed_fields
                )
            )
        }
        self._roles_reverse: dict[str, int] = {
            field: idx for idx, field in self._roles.items()
        }
        self._role_names: dict[int, QByteArray] = {
            role: QByteArray(field.encode("utf-8"))
            for role, field in self._roles.items()
        }

        self.all_items: list[T] = items if items is not None else []
        self.items: list[T] = self.all_items.copy()
        self._selected_index = selected_index

        super().__init__(parent)

    # region Signals

    _selected_index_changed = Signal(name="selectedIndexChanged")

    # endregion Signals

    # region Properties

    @Property(int, notify=_selected_index_changed, final=True)
    def selected_index(self) -> int:  # pyright: ignore[reportRedeclaration]
        """Selected index."""
        return self._selected_index

    @selected_index.setter
    def selected_index(self, value: int) -> None:
        """Set the selected index."""
        if value != self._selected_index:
            self._selected_index = value
            self._selected_index_changed.emit()

    # endregion Properties

    @Slot(int, str, result="QVariant")
    def get_data(self, index: int, role_name: str) -> Any:
        """Return the data."""
        if (
            index < -1
            or index >= len(self.items)
            or role_name not in self._roles_reverse
        ):
            _logger.warning(
                f"Tried to get data with invalid index '{index}' or role_name '{role_name}'"
            )
            return None
        item = self.items[index]
        return getattr(item, role_name)

    @override
    def data(
        self,
        index: QModelIndex | QPersistentModelIndex,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        """Return the data for the given index and role."""
        if not index.isValid() or role not in self._roles:
            return

        item = self.items[index.row()]
        return getattr(item, self._roles[role])

    @override
    def rowCount(
        self,
        parent: QModelIndex | QPersistentModelIndex = QModelIndex(),  # noqa: B008
    ) -> int:
        """Row count."""
        return len(self.items)
