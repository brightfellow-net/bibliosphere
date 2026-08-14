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
from bibliosphere.application.use_cases.remove_item import RemoveItem
from bibliosphere.application.use_cases.search_catalog import SearchCatalog
from bibliosphere.domain.exceptions import BibliosphereError
from bibliosphere.presentation.qt.add_bibliography_dialog import AddBibliographyDialog


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
        add_item: AddItem | None = None,
        remove_item: RemoveItem | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._search_catalog = search_catalog
        self._add_bibliography = add_bibliography
        self._add_item = add_item
        self._remove_item = remove_item
        self._entries: list[CatalogEntry] = []

        self._search_box = QLineEdit()
        self._search_box.setPlaceholderText("Search by title, author, or ISBN...")
        self._search_box.returnPressed.connect(self.refresh)

        search_button = QPushButton("Search")
        search_button.clicked.connect(self.refresh)

        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels(["Title", "Author", "ISBN", "Available"])
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

        if add_bibliography is not None:
            add_bib_button = QPushButton("Add Bibliography...")
            add_bib_button.clicked.connect(self._on_add_bibliography)
            layout.addWidget(add_bib_button)

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
            self._table.setItem(row, 0, QTableWidgetItem(entry.bibliography.title))
            self._table.setItem(row, 1, QTableWidgetItem(entry.author_names))
            self._table.setItem(row, 2, QTableWidgetItem(entry.bibliography.isbn_issn or ""))
            self._table.setItem(row, 3, QTableWidgetItem(f"{entry.available_items}/{entry.total_items}"))

    def selected_entry(self) -> CatalogEntry | None:
        row = self._table.currentRow()
        if row < 0 or row >= len(self._entries):
            return None
        return self._entries[row]

    def _on_add_bibliography(self) -> None:
        dialog = AddBibliographyDialog(self)
        if not dialog.exec():
            return
        isbn, title, authors = dialog.values()
        try:
            self._add_bibliography.execute(title=title, authors=authors, isbn_issn=isbn or None)
        except BibliosphereError as error:
            QMessageBox.warning(self, "Could not add bibliography", str(error))
            return
        self.refresh()

    def _on_add_item(self) -> None:
        entry = self.selected_entry()
        if entry is None:
            QMessageBox.information(self, "No selection", "Select a bibliography first.")
            return
        self._add_item.execute(entry.bibliography.id)
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
