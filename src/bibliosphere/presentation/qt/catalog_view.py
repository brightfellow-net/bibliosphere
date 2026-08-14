from PySide6.QtCore import Qt
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
from bibliosphere.application.use_cases.edit_bibliography import EditBibliography
from bibliosphere.application.use_cases.list_authors import ListAuthors
from bibliosphere.application.use_cases.remove_item import RemoveItem
from bibliosphere.application.use_cases.search_catalog import SearchCatalog
from bibliosphere.application.use_cases.set_bibliography_authors import SetBibliographyAuthors
from bibliosphere.domain.exceptions import BibliosphereError
from bibliosphere.presentation.qt.add_bibliography_dialog import AddBibliographyDialog
from bibliosphere.presentation.qt.edit_bibliography_dialog import EditBibliographyDialog

_COLUMN_LABELS = ["Call Number", "Title", "Series Title", "Authors", "ISBN", "Edition", "Publish Year", "Available"]


class CatalogView(QWidget):
    """Catalog search, shared by librarian and patron dashboards.

    Management actions (add bibliography/item, remove item) only appear when the
    corresponding use case is supplied — omitting them gives a read-only patron view
    without a separate widget class.
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
        self._entries: list[CatalogEntry] = []

        self._column_filters: list[QLineEdit] = []
        filter_row = QHBoxLayout()
        for label in _COLUMN_LABELS:
            filter_box = QLineEdit()
            filter_box.setPlaceholderText(f"Filter {label}...")
            filter_box.textChanged.connect(self._apply_filters)
            self._column_filters.append(filter_box)
            filter_row.addWidget(filter_box)

        self._table = QTableWidget(0, len(_COLUMN_LABELS))
        self._table.setHorizontalHeaderLabels(_COLUMN_LABELS)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._table.setSortingEnabled(True)

        layout = QVBoxLayout(self)
        layout.addLayout(filter_row)
        layout.addWidget(self._table)

        if add_bibliography is not None or edit_bibliography is not None:
            bib_row = QHBoxLayout()
            if add_bibliography is not None:
                add_bib_button = QPushButton("Add Bibliography...")
                add_bib_button.clicked.connect(self._on_add_bibliography)
                bib_row.addWidget(add_bib_button)
            if edit_bibliography is not None:
                edit_bib_button = QPushButton("Edit Selected...")
                edit_bib_button.clicked.connect(self._on_edit_bibliography)
                bib_row.addWidget(edit_bib_button)
            layout.addLayout(bib_row)

        if add_item is not None or remove_item is not None:
            item_row = QHBoxLayout()
            if add_item is not None:
                add_item_button = QPushButton("Add Item to Selected")
                add_item_button.clicked.connect(self._on_add_item)
                item_row.addWidget(add_item_button)
            if remove_item is not None:
                remove_item_button = QPushButton("Remove Item from Selected")
                remove_item_button.clicked.connect(self._on_remove_item)
                item_row.addWidget(remove_item_button)
            layout.addLayout(item_row)

        self.refresh()

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
            item = QTableWidgetItem(value)
            if column == 0:
                # Row order shifts under sorting/filtering, so selected_entry() looks
                # entries up by this id instead of assuming row index == self._entries
                # index.
                item.setData(Qt.ItemDataRole.UserRole, entry.bibliography.id)
            self._table.setItem(row, column, item)

    def selected_entry(self) -> CatalogEntry | None:
        row = self._table.currentRow()
        if row < 0:
            return None
        item = self._table.item(row, 0)
        if item is None:
            return None
        bibliography_id = item.data(Qt.ItemDataRole.UserRole)
        return next((entry for entry in self._entries if entry.bibliography.id == bibliography_id), None)

    def _on_add_bibliography(self) -> None:
        all_author_names = [a.name for a in self._list_authors.execute()] if self._list_authors is not None else []
        dialog = AddBibliographyDialog(all_author_names, self)
        if not dialog.exec():
            return
        isbn, title, series_title, edition, publish_year, call_number, authors = dialog.values()
        try:
            self._add_bibliography.execute(
                title=title,
                authors=authors,
                isbn_issn=isbn or None,
                series_title=series_title or None,
                edition=edition or None,
                publish_year=publish_year or None,
                call_number=call_number or None,
            )
        except BibliosphereError as error:
            QMessageBox.warning(self, "Could not add bibliography", str(error))
            return
        # Otherwise a leftover filter can hide the just-added bibliography with no
        # feedback that anything happened, inviting an accidental duplicate re-add.
        for box in self._column_filters:
            box.clear()
        self.refresh()

    def _on_edit_bibliography(self) -> None:
        entry = self.selected_entry()
        if entry is None:
            QMessageBox.information(self, "No selection", "Select a bibliography first.")
            return
        all_author_names = [a.name for a in self._list_authors.execute()] if self._list_authors is not None else []
        dialog = EditBibliographyDialog(entry, self._set_bibliography_authors, all_author_names, self)
        if not dialog.exec():
            return
        isbn, title, series_title, edition, publish_year, call_number, authors = dialog.values()
        existing = entry.bibliography
        try:
            # Forward the fields this dialog doesn't expose (sor, publisher_id, etc.)
            # unchanged, so editing here can't silently null them out. `authors` here
            # reflects whatever the dialog's "Manage Authors..." action already
            # persisted (or the original list if untouched) — this write is therefore
            # a harmless no-op for authors in the common case, not a second source of
            # truth for them.
            self._edit_bibliography.execute(
                existing.id,
                title=title,
                authors=authors,
                isbn_issn=isbn or None,
                sor=existing.sor,
                edition=edition or None,
                publish_year=publish_year or None,
                collation=existing.collation,
                series_title=series_title or None,
                call_number=call_number or None,
                classification=existing.classification,
                notes=existing.notes,
                language_id=existing.language_id,
                gmd_id=existing.gmd_id,
                publisher_id=existing.publisher_id,
                publish_place_id=existing.publish_place_id,
                content_type_id=existing.content_type_id,
                media_type_id=existing.media_type_id,
                carrier_type_id=existing.carrier_type_id,
            )
        except BibliosphereError as error:
            QMessageBox.warning(self, "Could not edit bibliography", str(error))
            return
        self.refresh()

    def _on_add_item(self) -> None:
        entry = self.selected_entry()
        if entry is None:
            QMessageBox.information(self, "No selection", "Select a bibliography first.")
            return
        try:
            self._add_item.execute(entry.bibliography.id)
        except BibliosphereError as error:
            QMessageBox.warning(self, "Could not add item", str(error))
            return
        self.refresh()

    def _on_remove_item(self) -> None:
        entry = self.selected_entry()
        if entry is None:
            QMessageBox.information(self, "No selection", "Select a bibliography first.")
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
