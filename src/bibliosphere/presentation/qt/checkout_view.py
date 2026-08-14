from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHeaderView,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from bibliosphere.application.dto import LoanView
from bibliosphere.application.use_cases.checkout_item import CheckoutItem
from bibliosphere.application.use_cases.list_members import ListMembers
from bibliosphere.application.use_cases.list_open_loans import ListOpenLoans
from bibliosphere.application.use_cases.return_item import ReturnItem
from bibliosphere.application.use_cases.search_catalog import SearchCatalog
from bibliosphere.domain.exceptions import BibliosphereError


class CheckoutView(QWidget):
    """Librarian-only: check items out to members and process returns."""

    def __init__(
        self,
        search_catalog: SearchCatalog,
        list_members: ListMembers,
        checkout_item: CheckoutItem,
        list_open_loans: ListOpenLoans,
        return_item: ReturnItem,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._search_catalog = search_catalog
        self._list_members = list_members
        self._checkout_item = checkout_item
        self._list_open_loans = list_open_loans
        self._return_item = return_item
        self._loan_views: list[LoanView] = []

        layout = QVBoxLayout(self)
        layout.addWidget(self._build_checkout_box())
        layout.addWidget(self._build_returns_box())

        self.refresh()

    def _build_checkout_box(self) -> QGroupBox:
        box = QGroupBox("Check Out")
        self._bibliography_combo = QComboBox()
        self._member_combo = QComboBox()
        checkout_button = QPushButton("Check Out")
        checkout_button.clicked.connect(self._on_checkout)

        form = QFormLayout()
        form.addRow("Bibliography:", self._bibliography_combo)
        form.addRow("Member:", self._member_combo)
        form.addRow(checkout_button)
        box.setLayout(form)
        return box

    def _build_returns_box(self) -> QGroupBox:
        box = QGroupBox("Return")
        self._loans_table = QTableWidget(0, 3)
        self._loans_table.setHorizontalHeaderLabels(["Title", "Member", "Due Date"])
        self._loans_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._loans_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._loans_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._loans_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        return_button = QPushButton("Return Selected")
        return_button.clicked.connect(self._on_return)

        layout = QVBoxLayout()
        layout.addWidget(self._loans_table)
        layout.addWidget(return_button)
        box.setLayout(layout)
        return box

    def refresh(self) -> None:
        self._bibliography_combo.clear()
        for entry in self._search_catalog.execute(""):
            label = f"{entry.bibliography.title} ({entry.available_items}/{entry.total_items} available)"
            self._bibliography_combo.addItem(label, entry.bibliography.id)

        self._member_combo.clear()
        for member in self._list_members.execute():
            self._member_combo.addItem(f"{member.name} ({member.username})", member.id)

        self._loan_views = self._list_open_loans.execute()
        self._loans_table.setRowCount(len(self._loan_views))
        for row, view in enumerate(self._loan_views):
            self._loans_table.setItem(row, 0, QTableWidgetItem(view.bibliography_title))
            self._loans_table.setItem(row, 1, QTableWidgetItem(view.member_name))
            self._loans_table.setItem(row, 2, QTableWidgetItem(view.loan.due_date.isoformat()))

    def _on_checkout(self) -> None:
        bibliography_id = self._bibliography_combo.currentData()
        member_id = self._member_combo.currentData()
        if bibliography_id is None or member_id is None:
            QMessageBox.information(self, "Nothing to check out", "Add a bibliography and a member first.")
            return
        try:
            loan = self._checkout_item.execute(bibliography_id, member_id)
        except BibliosphereError as error:
            QMessageBox.warning(self, "Could not check out", str(error))
            return
        QMessageBox.information(self, "Checked out", f"Due back {loan.due_date.isoformat()}.")
        self.refresh()

    def _on_return(self) -> None:
        row = self._loans_table.currentRow()
        if row < 0 or row >= len(self._loan_views):
            QMessageBox.information(self, "No selection", "Select a loan to return first.")
            return
        loan_id = self._loan_views[row].loan.id
        try:
            self._return_item.execute(loan_id)
        except BibliosphereError as error:
            QMessageBox.warning(self, "Could not return item", str(error))
            return
        self.refresh()
