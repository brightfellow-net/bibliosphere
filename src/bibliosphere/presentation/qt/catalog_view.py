from PySide6.QtCore import QSize
from PySide6.QtGui import QResizeEvent, QShowEvent
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from bibliosphere.application.dto import CatalogEntry
from bibliosphere.application.use_cases.add_bibliography import AddBibliography
from bibliosphere.application.use_cases.add_item import AddItem
from bibliosphere.application.use_cases.delete_bibliography import DeleteBibliography
from bibliosphere.application.use_cases.edit_bibliography import EditBibliography
from bibliosphere.application.use_cases.list_authors import ListAuthors
from bibliosphere.application.use_cases.remove_item import RemoveItem
from bibliosphere.application.use_cases.search_catalog import SearchCatalog
from bibliosphere.application.use_cases.set_bibliography_authors import SetBibliographyAuthors
from bibliosphere.domain.exceptions import BibliosphereError
from bibliosphere.presentation.qt.add_bibliography_dialog import AddBibliographyDialog
from bibliosphere.presentation.qt.edit_bibliography_dialog import EditBibliographyDialog

_COLUMN_LABELS = ["Call Number", "Title", "Series Title", "Authors", "ISBN", "Edition", "Publish Year", "Available"]
# Parallel to _COLUMN_LABELS: initial widths (px) users can then drag to resize. Series
# Title's entry is a placeholder — it's the designated "filler" column (see
# _rebalance_filler_column), so its actual width always fills whatever space the others
# don't use, ignoring this value. It's the filler rather than Title so Title itself
# stays draggable like every other column.
_DEFAULT_COLUMN_WIDTHS = [110, 260, 140, 160, 110, 90, 90, 80]
_FILLER_COLUMN = _COLUMN_LABELS.index("Series Title")
_MIN_FILLER_WIDTH = 60


class CatalogView(QWidget):
    """Catalog search, shared by librarian and patron dashboards.

    Management actions (add bibliography, edit/add item/remove item/delete
    bibliography) only appear when the corresponding use case is supplied — omitting
    them gives a read-only patron view without a separate widget class. Edit/Add
    Item/Remove Item/Delete are per-row buttons in the trailing "Action" column (rather
    than a global "...Selected" button) so they don't depend on a table selection; that
    column itself only appears when at least one of them is available.
    """

    def __init__(
        self,
        search_catalog: SearchCatalog,
        add_bibliography: AddBibliography | None = None,
        edit_bibliography: EditBibliography | None = None,
        set_bibliography_authors: SetBibliographyAuthors | None = None,
        list_authors: ListAuthors | None = None,
        add_item: AddItem | None = None,
        remove_item: RemoveItem | None = None,
        delete_bibliography: DeleteBibliography | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._search_catalog = search_catalog
        self._add_bibliography = add_bibliography
        self._edit_bibliography = edit_bibliography
        self._set_bibliography_authors = set_bibliography_authors
        self._list_authors = list_authors
        self._add_item = add_item
        self._remove_item = remove_item
        self._delete_bibliography = delete_bibliography
        self._entries: list[CatalogEntry] = []
        self._show_actions = (
            edit_bibliography is not None
            or add_item is not None
            or remove_item is not None
            or delete_bibliography is not None
        )
        column_labels = [*_COLUMN_LABELS, "Action"] if self._show_actions else list(_COLUMN_LABELS)

        self._column_filters: list[QLineEdit] = []
        filter_row = QHBoxLayout()
        filter_row.setSpacing(0)
        filter_row.setContentsMargins(0, 0, 0, 0)
        for label in column_labels:
            filter_box = QLineEdit()
            if label == "Action":
                filter_box.setEnabled(False)
            else:
                filter_box.setPlaceholderText(f"Filter {label}...")
                filter_box.textChanged.connect(self._apply_filters)
            self._column_filters.append(filter_box)
            filter_row.addWidget(filter_box)

        self._table = QTableWidget(0, len(column_labels))
        self._table.setHorizontalHeaderLabels(column_labels)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        # Otherwise its width is one more thing the filter row above would have to
        # account for, on top of each column's own width.
        self._table.verticalHeader().setVisible(False)
        # Interactive (not Stretch) so users can drag column borders to resize; initial
        # widths are set explicitly below since Interactive columns don't auto-size.
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        # Series Title is the one column not user-draggable — its width is instead
        # recomputed in _rebalance_filler_column() to absorb whatever space the other
        # (fixed-until-dragged) columns don't use, so the columns always fill the
        # table's width with no dead space or horizontal scrollbar. This is handled by
        # hand rather than via Qt's own Stretch resize mode: mixing Stretch with
        # Interactive columns relies on Qt to redistribute the Stretch section whenever
        # any other section resizes, which turned out not to happen reliably (e.g. a
        # window at a fixed size, so no resize event of its own reaches the header).
        self._table.horizontalHeader().setSectionResizeMode(_FILLER_COLUMN, QHeaderView.ResizeMode.Fixed)
        if self._show_actions:
            # Fixed to fit its buttons, unlike the data columns — leaving it Interactive
            # would let a user drag it down to unreadable fragments.
            self._table.horizontalHeader().setSectionResizeMode(
                len(column_labels) - 1, QHeaderView.ResizeMode.ResizeToContents
            )
        self._table.setSortingEnabled(True)
        # The filter row is a separate QHBoxLayout, not part of the table itself (a
        # table row can't be pinned above the sortable ones), so its boxes' widths are
        # kept in lockstep with the actual column widths here instead of relying on
        # both layouts happening to divide up space the same way. Connected before the
        # initial setColumnWidth() calls below so those are picked up too.
        self._table.horizontalHeader().sectionResized.connect(self._on_column_resized)
        for column, width in enumerate(_DEFAULT_COLUMN_WIDTHS):
            if column != _FILLER_COLUMN:
                self._table.setColumnWidth(column, width)

        layout = QVBoxLayout(self)
        layout.addLayout(filter_row)
        layout.addWidget(self._table)

        if add_bibliography is not None:
            bib_row = QHBoxLayout()
            add_bib_button = QPushButton("Add Bibliography...")
            add_bib_button.clicked.connect(self._on_add_bibliography)
            bib_row.addWidget(add_bib_button)
            layout.addLayout(bib_row)

        self.refresh()

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        # Otherwise resizing the window leaves Series Title at its old width instead of
        # absorbing/releasing the newly available space, the way the rest of the
        # columns filling the table depends on.
        self._rebalance_filler_column()

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        # The very first rebalance (during __init__, via refresh()) runs before this
        # widget has real on-screen geometry, and before the Action column's
        # ResizeToContents width has settled to fit its buttons — both only become
        # final once the widget is actually shown, so it needs to happen once more here.
        self._rebalance_filler_column()

    def minimumSizeHint(self) -> QSize:
        # Otherwise this propagates all the way up to the top-level window's minimum
        # size: _sync_filter_column_widths uses setFixedWidth() to keep a filter box
        # exactly as wide as its column, and setFixedWidth() pins that box's *minimum*
        # width too — so dragging a column wide enough would otherwise force the window
        # to grow past the screen size, unable to be maximized/restored afterward. A
        # QAbstractScrollArea like the table already overrides this the same way, which
        # is why only the filter row needed it here.
        return QSize(200, 150)

    def _on_column_resized(self, index: int, old_size: int, new_size: int) -> None:
        self._sync_filter_column_width(index, new_size)
        if index != _FILLER_COLUMN:
            self._rebalance_filler_column()

    def _sync_filter_column_width(self, index: int, new_size: int) -> None:
        if 0 <= index < len(self._column_filters):
            self._column_filters[index].setFixedWidth(new_size)

    def _rebalance_filler_column(self) -> None:
        fixed_total = sum(
            self._table.columnWidth(i) for i in range(self._table.columnCount()) if i != _FILLER_COLUMN
        )
        available = max(_MIN_FILLER_WIDTH, self._table.viewport().width() - fixed_total)
        if available != self._table.columnWidth(_FILLER_COLUMN):
            # sectionResized (and so _on_column_resized) fires from this in turn, but
            # only syncs that column's filter box — it's excluded from triggering
            # another rebalance above, so this can't recurse.
            self._table.setColumnWidth(_FILLER_COLUMN, available)

    def refresh(self) -> None:
        self._entries = self._search_catalog.execute("")
        self._apply_filters()

    def _apply_filters(self) -> None:
        filters = [box.text().strip().lower() for box in self._column_filters]
        matching = [entry for entry in self._entries if self._matches_filters(entry, filters)]

        # Disable sorting while bulk-repopulating rows — otherwise Qt re-sorts after
        # every single setItem() call, which is both slow and can scatter a row's
        # cells across the wrong positions mid-insert.
        self._table.setSortingEnabled(False)
        self._table.setRowCount(len(matching))
        for row, entry in enumerate(matching):
            self._set_row(row, entry)
        self._table.setSortingEnabled(True)
        # Action's ResizeToContents width can only be known once its cell widgets
        # exist, i.e. after the rows above are populated — so the filler needs to
        # re-settle afterward too, not just when a data column is dragged.
        self._rebalance_filler_column()

    @staticmethod
    def _matches_filters(entry: CatalogEntry, filters: list[str]) -> bool:
        values = CatalogView._row_values(entry)
        return all(needle in value.lower() for needle, value in zip(filters, values) if needle)

    @staticmethod
    def _row_values(entry: CatalogEntry) -> list[str]:
        return [
            entry.bibliography.call_number or "",
            entry.bibliography.title,
            entry.bibliography.series_title or "",
            entry.author_names,
            entry.bibliography.isbn_issn or "",
            entry.bibliography.edition or "",
            entry.bibliography.publish_year or "",
            f"{entry.available_items}/{entry.total_items}",
        ]

    def _set_row(self, row: int, entry: CatalogEntry) -> None:
        for column, value in enumerate(self._row_values(entry)):
            self._table.setItem(row, column, QTableWidgetItem(value))
        if self._show_actions:
            self._table.setCellWidget(row, len(_COLUMN_LABELS), self._make_action_widget(entry.bibliography.id))

    def _make_action_widget(self, bibliography_id: int) -> QWidget:
        widget = QWidget()
        row = QHBoxLayout(widget)
        row.setContentsMargins(2, 2, 2, 2)
        if self._edit_bibliography is not None:
            edit_button = QPushButton("Edit")
            edit_button.clicked.connect(lambda: self._on_edit_bibliography(bibliography_id))
            row.addWidget(edit_button)
        if self._add_item is not None:
            add_item_button = QPushButton("Add Item")
            add_item_button.clicked.connect(lambda: self._on_add_item(bibliography_id))
            row.addWidget(add_item_button)
        if self._remove_item is not None:
            remove_item_button = QPushButton("Remove Item")
            remove_item_button.clicked.connect(lambda: self._on_remove_item(bibliography_id))
            row.addWidget(remove_item_button)
        if self._delete_bibliography is not None:
            delete_button = QPushButton("Delete")
            delete_button.clicked.connect(lambda: self._on_delete_bibliography(bibliography_id))
            row.addWidget(delete_button)
        return widget

    def _entry_by_id(self, bibliography_id: int) -> CatalogEntry | None:
        # A row's action buttons close over the bibliography id rather than its
        # CatalogEntry snapshot, so a click always acts on the latest data even if
        # refresh() replaced self._entries (e.g. from another row's action) since the
        # button was created.
        return next((entry for entry in self._entries if entry.bibliography.id == bibliography_id), None)

    def _on_add_bibliography(self) -> None:
        all_author_names = [a.name for a in self._list_authors.execute()] if self._list_authors is not None else []
        dialog = AddBibliographyDialog(self._add_bibliography, all_author_names, self)
        dialog.bibliography_added.connect(self._on_bibliography_added)
        dialog.exec()

    def _on_bibliography_added(self) -> None:
        # Otherwise a leftover filter can hide the just-added bibliography with no
        # feedback that anything happened, inviting an accidental duplicate re-add.
        for box in self._column_filters:
            box.clear()
        self.refresh()

    def _on_edit_bibliography(self, bibliography_id: int) -> None:
        entry = self._entry_by_id(bibliography_id)
        if entry is None:
            return
        all_author_names = [a.name for a in self._list_authors.execute()] if self._list_authors is not None else []
        dialog = EditBibliographyDialog(
            entry, self._edit_bibliography, self._set_bibliography_authors, all_author_names, self
        )
        if not dialog.exec():
            return
        self.refresh()

    def _on_add_item(self, bibliography_id: int) -> None:
        entry = self._entry_by_id(bibliography_id)
        if entry is None:
            return
        try:
            self._add_item.execute(entry.bibliography.id)
        except BibliosphereError as error:
            QMessageBox.warning(self, "Could not add item", str(error))
            return
        self.refresh()

    def _on_remove_item(self, bibliography_id: int) -> None:
        entry = self._entry_by_id(bibliography_id)
        if entry is None:
            return
        removable = next((status.item for status in entry.items if status.available), None)
        if removable is None:
            QMessageBox.warning(self, "Cannot remove item", "No available (non-checked-out) item to remove.")
            return
        try:
            self._remove_item.execute(removable.id)
        except BibliosphereError as error:
            QMessageBox.warning(self, "Could not remove item", str(error))
            return
        self.refresh()

    def _on_delete_bibliography(self, bibliography_id: int) -> None:
        entry = self._entry_by_id(bibliography_id)
        if entry is None:
            return
        confirmed = QMessageBox.question(
            self,
            "Delete bibliography",
            f"Delete {entry.bibliography.title!r}? This cannot be undone.",
        )
        if confirmed != QMessageBox.StandardButton.Yes:
            return
        try:
            self._delete_bibliography.execute(bibliography_id)
        except BibliosphereError as error:
            QMessageBox.warning(self, "Could not delete bibliography", str(error))
            return
        self.refresh()
