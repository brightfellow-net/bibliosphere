from PySide6.QtCore import Qt, QStringListModel
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QCompleter,
    QFormLayout,
    QGroupBox,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from bibliosphere.application.dto import CatalogEntry, LoanView
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
        # Keyed by "<call number> — <title>" (call numbers are unique and mandatory),
        # so the input box's exact text always resolves unambiguously to one entry.
        self._entry_by_display_text: dict[str, CatalogEntry] = {}

        layout = QVBoxLayout(self)
        layout.addWidget(self._build_checkout_box())
        layout.addWidget(self._build_returns_box())

        self.refresh()

    def _build_checkout_box(self) -> QGroupBox:
        box = QGroupBox("Check Out")

        self._bibliography_input = QLineEdit()
        self._bibliography_input.setPlaceholderText("Call number...")
        self._bibliography_completer_model = QStringListModel()
        completer = QCompleter(self._bibliography_completer_model, self)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self._bibliography_input.setCompleter(completer)
        self._bibliography_input.textChanged.connect(self._update_selected_book_label)

        self._selected_book_label = QLabel()
        self._update_selected_book_label()

        self._member_combo = QComboBox()
        checkout_button = QPushButton("Check Out")
        checkout_button.clicked.connect(self._on_checkout)

        form = QFormLayout()
        form.addRow("Call Number:", self._bibliography_input)
        form.addRow(self._selected_book_label)
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
        # Rebuilding a combo box resets its selection to index 0, which would otherwise
        # silently swap the selected member for a different one on every refresh (e.g.
        # right after a checkout) without the librarian noticing — risking the next
        # checkout going to the wrong person. Restore the previous selection by id so
        # it only changes when the librarian deliberately picks something else. (The
        # call number QLineEdit doesn't have this problem: its text is untouched by
        # refresh(), so a typed/selected value simply persists on its own.)
        previous_member_id = self._member_combo.currentData()

        self._entry_by_display_text = {}
        for entry in self._search_catalog.execute(""):
            display = f"{entry.bibliography.call_number} — {entry.bibliography.title}"
            self._entry_by_display_text[display] = entry
        self._bibliography_completer_model.setStringList(sorted(self._entry_by_display_text))
        self._update_selected_book_label()

        self._member_combo.clear()
        for member in self._list_members.execute():
            self._member_combo.addItem(f"{member.name} ({member.username})", member.id)
        self._restore_combo_selection(self._member_combo, previous_member_id)

        self._loan_views = self._list_open_loans.execute()
        self._loans_table.setRowCount(len(self._loan_views))
        for row, view in enumerate(self._loan_views):
            self._loans_table.setItem(row, 0, QTableWidgetItem(view.bibliography_title))
            self._loans_table.setItem(row, 1, QTableWidgetItem(view.member_name))
            self._loans_table.setItem(row, 2, QTableWidgetItem(view.loan.due_date.isoformat()))

    def _update_selected_book_label(self) -> None:
        # Lets the librarian visually confirm the title/availability before checking
        # out, rather than trusting the call number alone.
        entry = self._entry_by_display_text.get(self._bibliography_input.text().strip())
        if entry is None:
            self._selected_book_label.setText("No matching book selected.")
            self._selected_book_label.setStyleSheet("color: gray;")
        else:
            self._selected_book_label.setText(
                f"{entry.bibliography.title} — {entry.available_items}/{entry.total_items} available"
            )
            self._selected_book_label.setStyleSheet("")

    @staticmethod
    def _restore_combo_selection(combo: QComboBox, data_id: object) -> None:
        if data_id is None:
            return
        index = combo.findData(data_id)
        if index >= 0:
            combo.setCurrentIndex(index)

    def _on_checkout(self) -> None:
        entry = self._entry_by_display_text.get(self._bibliography_input.text().strip())
        member_id = self._member_combo.currentData()
        if entry is None or member_id is None:
            QMessageBox.information(
                self, "Nothing to check out", "Select a book by call number and a member first."
            )
            return
        try:
            loan = self._checkout_item.execute(entry.bibliography.id, member_id)
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
