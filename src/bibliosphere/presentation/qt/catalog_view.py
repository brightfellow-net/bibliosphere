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
from bibliosphere.presentation.qt.manage_authors_dialog import ManageAuthorsDialog


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

        self._search_box = QLineEdit()
        self._search_box.setPlaceholderText("Search by title, authors, or ISBN...")
        self._search_box.returnPressed.connect(self.refresh)

        search_button = QPushButton("Search")
        search_button.clicked.connect(self.refresh)

        self._table = QTableWidget(0, 8)
        self._table.setHorizontalHeaderLabels(
            ["Call Number", "Title", "Series Title", "Authors", "ISBN", "Edition", "Publish Year", "Available"]
        )
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        search_row = QHBoxLayout()
        search_row.addWidget(self._search_box)
        search_row.addWidget(search_button)

        layout = QVBoxLayout(self)
        layout.addLayout(search_row)
        layout.addWidget(self._table)

        if add_bibliography is not None or edit_bibliography is not None or set_bibliography_authors is not None:
            bib_row = QHBoxLayout()
            if add_bibliography is not None:
                add_bib_button = QPushButton("Add Bibliography...")
                add_bib_button.clicked.connect(self._on_add_bibliography)
                bib_row.addWidget(add_bib_button)
            if edit_bibliography is not None:
                edit_bib_button = QPushButton("Edit Selected...")
                edit_bib_button.clicked.connect(self._on_edit_bibliography)
                bib_row.addWidget(edit_bib_button)
            if set_bibliography_authors is not None:
                manage_authors_button = QPushButton("Manage Authors...")
                manage_authors_button.clicked.connect(self._on_manage_authors)
                bib_row.addWidget(manage_authors_button)
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
        self._entries = self._search_catalog.execute(self._search_box.text().strip())
        self._table.setRowCount(len(self._entries))
        for row, entry in enumerate(self._entries):
            self._table.setItem(row, 0, QTableWidgetItem(entry.bibliography.call_number or ""))
            self._table.setItem(row, 1, QTableWidgetItem(entry.bibliography.title))
            self._table.setItem(row, 2, QTableWidgetItem(entry.bibliography.series_title or ""))
            self._table.setItem(row, 3, QTableWidgetItem(entry.author_names))
            self._table.setItem(row, 4, QTableWidgetItem(entry.bibliography.isbn_issn or ""))
            self._table.setItem(row, 5, QTableWidgetItem(entry.bibliography.edition or ""))
            self._table.setItem(row, 6, QTableWidgetItem(entry.bibliography.publish_year or ""))
            self._table.setItem(row, 7, QTableWidgetItem(f"{entry.available_items}/{entry.total_items}"))

    def selected_entry(self) -> CatalogEntry | None:
        row = self._table.currentRow()
        if row < 0 or row >= len(self._entries):
            return None
        return self._entries[row]

    def _on_add_bibliography(self) -> None:
        dialog = AddBibliographyDialog(self)
        if not dialog.exec():
            return
        isbn, title, series_title, edition, publish_year, call_number = dialog.values()
        try:
            # New bibliographies start with no authors; add them afterward via
            # "Manage Authors...", which is a separate action from this dialog.
            self._add_bibliography.execute(
                title=title,
                authors=[],
                isbn_issn=isbn or None,
                series_title=series_title or None,
                edition=edition or None,
                publish_year=publish_year or None,
                call_number=call_number or None,
            )
        except BibliosphereError as error:
            QMessageBox.warning(self, "Could not add bibliography", str(error))
            return
        # Otherwise a leftover search filter can hide the just-added bibliography with
        # no feedback that anything happened, inviting an accidental duplicate re-add.
        self._search_box.clear()
        self.refresh()

    def _on_edit_bibliography(self) -> None:
        entry = self.selected_entry()
        if entry is None:
            QMessageBox.information(self, "No selection", "Select a bibliography first.")
            return
        dialog = EditBibliographyDialog(entry, self)
        if not dialog.exec():
            return
        isbn, title, series_title, edition, publish_year, call_number = dialog.values()
        existing = entry.bibliography
        try:
            # Forward the fields this dialog doesn't expose (sor, publisher_id, etc.)
            # unchanged, so editing here can't silently null them out. Authors are
            # managed separately via "Manage Authors...", so also forward those as-is.
            self._edit_bibliography.execute(
                existing.id,
                title=title,
                authors=[credit.author.name for credit in entry.authors],
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

    def _on_manage_authors(self) -> None:
        entry = self.selected_entry()
        if entry is None:
            QMessageBox.information(self, "No selection", "Select a bibliography first.")
            return
        all_author_names = [a.name for a in self._list_authors.execute()] if self._list_authors is not None else []
        dialog = ManageAuthorsDialog(entry, all_author_names, self)
        if not dialog.exec():
            return
        try:
            self._set_bibliography_authors.execute(entry.bibliography.id, dialog.values())
        except BibliosphereError as error:
            QMessageBox.warning(self, "Could not update authors", str(error))
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
