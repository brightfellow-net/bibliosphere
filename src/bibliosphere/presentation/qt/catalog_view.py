from PySide6.QtCore import QSize, Qt
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
from bibliosphere.domain.ids import require_id
from bibliosphere.presentation.qt.add_bibliography_dialog import AddBibliographyDialog
from bibliosphere.presentation.qt.edit_bibliography_dialog import EditBibliographyDialog

_COLUMN_LABELS = ["Call Number", "Title", "Series Title", "Authors", "ISBN", "Edition", "Publish Year", "Available"]
# Parallel to _COLUMN_LABELS: initial widths (px), user-draggable from there.
_DEFAULT_COLUMN_WIDTHS = [110, 260, 140, 160, 110, 90, 90, 80]
# Call Number and Title stay on screen while the rest of the table scrolls
# horizontally underneath (see _frozen_table below) — this is how many leading
# columns that covers.
_FROZEN_COLUMN_COUNT = 2


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
        # Every column (Call Number/Title included) keeps this mode: with nothing
        # forcing columns to shrink to the viewport width, Qt's default
        # ScrollBarAsNeeded policy shows a horizontal scrollbar once the real column
        # widths exceed it, instead of squeezing everything to fit.
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        if self._show_actions:
            # Fixed to fit its buttons, unlike the data columns — leaving it Interactive
            # would let a user drag it down to unreadable fragments.
            self._table.horizontalHeader().setSectionResizeMode(
                len(column_labels) - 1, QHeaderView.ResizeMode.ResizeToContents
            )
        self._table.setSortingEnabled(True)
        # Default scroll mode is per-item (the horizontal scrollbar's value would be a
        # column index, not a pixel offset), which both makes for chunky horizontal
        # scrolling and breaks the pixel-for-pixel offset _on_table_hscroll relies on
        # to keep the non-frozen filter boxes lined up with their columns.
        self._table.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self._table.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        for column, width in enumerate(_DEFAULT_COLUMN_WIDTHS):
            self._table.setColumnWidth(column, width)

        # Second table overlaid on top of _table's own Call Number/Title columns
        # (which stay in place underneath, just visually covered) — QTableWidget has
        # no built-in frozen-column support, so this mirrors Qt's own "frozen column"
        # pattern by hand: a second view showing just the columns to freeze, scroll-
        # synced to the real one. See _update_frozen_table_geometry and the sync
        # methods wired up below for how the two are kept in lockstep.
        self._frozen_table = QTableWidget(0, _FROZEN_COLUMN_COUNT, self._table)
        self._frozen_table.setHorizontalHeaderLabels(column_labels[:_FROZEN_COLUMN_COUNT])
        self._frozen_table.verticalHeader().setVisible(False)
        self._frozen_table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self._frozen_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._frozen_table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._frozen_table.setFrameShape(QTableWidget.Shape.NoFrame)
        self._frozen_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._frozen_table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        # Must match _table's vertical scroll mode (both per-pixel) for the two
        # scrollbars' values to mean the same thing when synced 1:1 below.
        self._frozen_table.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self._frozen_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        for column in range(_FROZEN_COLUMN_COUNT):
            self._frozen_table.setColumnWidth(column, _DEFAULT_COLUMN_WIDTHS[column])
        # _frozen_table's header visually replaces _table's for these columns (it's
        # drawn on top), so it needs its own click-to-sort — but it must never sort
        # itself independently of _table (that would desync row order between the
        # two), so a click here just forwards to _table's real sort indicator instead.
        self._frozen_table.horizontalHeader().setSectionsClickable(True)

        self._column_filters: list[QLineEdit] = []
        # The filter row can't be a real table row pinned above the sortable ones, so
        # it's built separately here — but split to match the table above it: a fixed
        # panel for Call Number/Title's filters (over _frozen_table) and a clipped,
        # horizontally-scrolled panel for the rest (over _table), see
        # _update_filter_bar_geometry and _on_table_hscroll.
        self._filter_bar = QWidget()
        self._frozen_filter_container = QWidget(self._filter_bar)
        frozen_filter_layout = QHBoxLayout(self._frozen_filter_container)
        frozen_filter_layout.setSpacing(0)
        frozen_filter_layout.setContentsMargins(0, 0, 0, 0)
        self._scroll_filter_clip = QWidget(self._filter_bar)
        self._scroll_filter_inner = QWidget(self._scroll_filter_clip)
        scroll_filter_layout = QHBoxLayout(self._scroll_filter_inner)
        scroll_filter_layout.setSpacing(0)
        scroll_filter_layout.setContentsMargins(0, 0, 0, 0)
        for index, label in enumerate(column_labels):
            filter_box = QLineEdit()
            if label == "Action":
                filter_box.setEnabled(False)
            else:
                filter_box.setPlaceholderText(f"Filter {label}...")
                filter_box.textChanged.connect(self._apply_filters)
            self._column_filters.append(filter_box)
            if index < _FROZEN_COLUMN_COUNT:
                frozen_filter_layout.addWidget(filter_box)
            else:
                scroll_filter_layout.addWidget(filter_box)
            filter_box.setFixedWidth(self._table.columnWidth(index))
        self._filter_bar.setFixedHeight(self._column_filters[0].sizeHint().height())

        # Wired up only now that every widget these handlers touch (_column_filters,
        # _filter_bar and its children) actually exists — connecting any earlier risks
        # a handler firing off one of the setColumnWidth() calls above and crashing on
        # a not-yet-built attribute.
        self._table.horizontalHeader().sectionResized.connect(self._on_column_resized)
        self._table.horizontalScrollBar().valueChanged.connect(self._on_table_hscroll)
        self._frozen_table.horizontalHeader().sectionClicked.connect(self._on_frozen_header_clicked)
        # Dragging Call Number/Title now has to happen on the (visible) frozen
        # header — mirror the new width onto _table's hidden-underneath column so its
        # total content width (and therefore its horizontal scrollbar range) stays
        # correct, and re-settle both overlays' geometry.
        self._frozen_table.horizontalHeader().sectionResized.connect(self._on_frozen_column_resized)
        # A header click (native, for columns 2+, or forwarded from _frozen_table's
        # header for 0/1 via _on_frozen_header_clicked above) reorders _table's rows
        # in place without going through _apply_filters, so _frozen_table needs an
        # explicit resync afterward. Note this has to be the *model's* layoutChanged,
        # not the header's sortIndicatorChanged: the indicator signal fires before the
        # actual row reorder happens (confirmed empirically — connecting there copied
        # stale, pre-sort data into _frozen_table), whereas layoutChanged fires once
        # the reorder is actually done.
        self._table.model().layoutChanged.connect(self._on_table_sorted)
        self._table.verticalScrollBar().valueChanged.connect(self._frozen_table.verticalScrollBar().setValue)
        self._frozen_table.verticalScrollBar().valueChanged.connect(self._table.verticalScrollBar().setValue)

        layout = QVBoxLayout(self)
        layout.addWidget(self._filter_bar)
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
        self._update_frozen_table_geometry()
        self._update_filter_bar_geometry()

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        # The very first geometry pass (during __init__, via refresh()) runs before
        # this widget has real on-screen geometry, and before the Action column's
        # ResizeToContents width has settled to fit its buttons — both only become
        # final once the widget is actually shown, so it needs to happen once more here.
        self._update_frozen_table_geometry()
        self._update_filter_bar_geometry()

    def minimumSizeHint(self) -> QSize:
        # Otherwise this propagates all the way up to the top-level window's minimum
        # size: the filter boxes' setFixedWidth() calls pin their *minimum* width too
        # — so dragging a column wide enough would otherwise force the window to grow
        # past the screen size, unable to be maximized/restored afterward. A
        # QAbstractScrollArea like the table already overrides this the same way, which
        # is why only the filter row needed it here.
        return QSize(200, 150)

    def _update_frozen_table_geometry(self) -> None:
        frozen_width = sum(self._table.columnWidth(i) for i in range(_FROZEN_COLUMN_COUNT))
        self._frozen_table.setGeometry(
            self._table.frameWidth(),
            self._table.frameWidth(),
            frozen_width,
            self._table.viewport().height() + self._table.horizontalHeader().height(),
        )

    def _update_filter_bar_geometry(self) -> None:
        frozen_width = sum(self._table.columnWidth(i) for i in range(_FROZEN_COLUMN_COUNT))
        bar_height = self._filter_bar.height()
        self._frozen_filter_container.setGeometry(0, 0, frozen_width, bar_height)
        self._scroll_filter_clip.setGeometry(
            frozen_width, 0, max(0, self._filter_bar.width() - frozen_width), bar_height
        )
        self._scroll_filter_inner.resize(self._scroll_filter_inner.sizeHint().width(), bar_height)
        self._on_table_hscroll(self._table.horizontalScrollBar().value())

    def _on_table_hscroll(self, value: int) -> None:
        # Keeps the non-frozen filter boxes lined up with the columns they filter as
        # _table scrolls horizontally underneath them — same pixel units (column
        # widths) on both sides, so no offset math is needed beyond the raw value.
        self._scroll_filter_inner.move(-value, 0)

    def _on_frozen_header_clicked(self, column: int) -> None:
        header = self._table.horizontalHeader()
        already_ascending = (
            header.sortIndicatorSection() == column
            and header.sortIndicatorOrder() == Qt.SortOrder.AscendingOrder
        )
        order = Qt.SortOrder.DescendingOrder if already_ascending else Qt.SortOrder.AscendingOrder
        # _table has setSortingEnabled(True), which is what makes changing its sort
        # indicator (rather than calling sortItems() directly) actually perform the
        # sort — the same mechanism a real click on one of its own headers uses.
        header.setSortIndicator(column, order)

    def _on_frozen_column_resized(self, index: int, old_size: int, new_size: int) -> None:
        self._table.setColumnWidth(index, new_size)
        self._sync_filter_column_width(index, new_size)
        self._update_frozen_table_geometry()
        self._update_filter_bar_geometry()

    def _on_table_sorted(self) -> None:
        self._sync_frozen_rows()

    def _sync_frozen_rows(self) -> None:
        self._frozen_table.setRowCount(self._table.rowCount())
        for row in range(self._table.rowCount()):
            for column in range(_FROZEN_COLUMN_COUNT):
                item = self._table.item(row, column)
                text = item.text() if item is not None else ""
                self._frozen_table.setItem(row, column, QTableWidgetItem(text))

    def _on_column_resized(self, index: int, old_size: int, new_size: int) -> None:
        self._sync_filter_column_width(index, new_size)

    def _sync_filter_column_width(self, index: int, new_size: int) -> None:
        if 0 <= index < len(self._column_filters):
            self._column_filters[index].setFixedWidth(new_size)

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
        self._frozen_table.setRowCount(len(matching))
        for row, entry in enumerate(matching):
            self._set_row(row, entry)
        self._table.setSortingEnabled(True)
        # Re-enabling sorting can itself reorder rows immediately (if a sort indicator
        # was already active from an earlier click) without necessarily emitting
        # sortIndicatorChanged — so _sync_frozen_rows is called explicitly here rather
        # than relied on via that signal, which only covers a later interactive click.
        self._sync_frozen_rows()
        # Action's ResizeToContents width can only be known once its cell widgets
        # exist, i.e. after the rows above are populated — so the overlays need to
        # re-settle afterward too, not just when a column is dragged.
        self._update_frozen_table_geometry()
        self._update_filter_bar_geometry()

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
        values = self._row_values(entry)
        for column, value in enumerate(values):
            self._table.setItem(row, column, QTableWidgetItem(value))
        for column in range(_FROZEN_COLUMN_COUNT):
            self._frozen_table.setItem(row, column, QTableWidgetItem(values[column]))
        if self._show_actions:
            self._table.setCellWidget(
                row, len(_COLUMN_LABELS), self._make_action_widget(require_id(entry.bibliography.id))
            )

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
        assert self._add_bibliography is not None
        add_bibliography = self._add_bibliography
        all_author_names = [a.name for a in self._list_authors.execute()] if self._list_authors is not None else []
        dialog = AddBibliographyDialog(add_bibliography, all_author_names, self)
        dialog.bibliography_added.connect(self._on_bibliography_added)
        dialog.exec()

    def _on_bibliography_added(self) -> None:
        # Otherwise a leftover filter can hide the just-added bibliography with no
        # feedback that anything happened, inviting an accidental duplicate re-add.
        for box in self._column_filters:
            box.clear()
        self.refresh()

    def _on_edit_bibliography(self, bibliography_id: int) -> None:
        assert self._edit_bibliography is not None
        edit_bibliography = self._edit_bibliography
        entry = self._entry_by_id(bibliography_id)
        if entry is None:
            return
        all_author_names = [a.name for a in self._list_authors.execute()] if self._list_authors is not None else []
        dialog = EditBibliographyDialog(
            entry, edit_bibliography, self._set_bibliography_authors, all_author_names, self
        )
        if not dialog.exec():
            return
        self.refresh()

    def _on_add_item(self, bibliography_id: int) -> None:
        assert self._add_item is not None
        entry = self._entry_by_id(bibliography_id)
        if entry is None:
            return
        try:
            self._add_item.execute(require_id(entry.bibliography.id))
        except BibliosphereError as error:
            QMessageBox.warning(self, "Could not add item", str(error))
            return
        self.refresh()

    def _on_remove_item(self, bibliography_id: int) -> None:
        assert self._remove_item is not None
        entry = self._entry_by_id(bibliography_id)
        if entry is None:
            return
        removable = next((status.item for status in entry.items if status.available), None)
        if removable is None:
            QMessageBox.warning(self, "Cannot remove item", "No available (non-checked-out) item to remove.")
            return
        try:
            self._remove_item.execute(require_id(removable.id))
        except BibliosphereError as error:
            QMessageBox.warning(self, "Could not remove item", str(error))
            return
        self.refresh()

    def _on_delete_bibliography(self, bibliography_id: int) -> None:
        assert self._delete_bibliography is not None
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
