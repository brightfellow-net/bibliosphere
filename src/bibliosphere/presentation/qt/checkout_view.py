from PySide6.QtCore import Qt, QStringListModel
from PySide6.QtWidgets import (
    QAbstractItemView,
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
from bibliosphere.domain.entities import Member
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
        # Subset of self._loan_views actually shown in the Return table (see
        # _populate_loans_table) — _on_return indexes into this, not self._loan_views,
        # since filtering makes the table's row order diverge from the unfiltered list.
        self._displayed_loans: list[LoanView] = []
        # Keyed by "<call number> — <title>" (call numbers are unique and mandatory),
        # so the input box's exact text always resolves unambiguously to one entry.
        self._entry_by_display_text: dict[str, CatalogEntry] = {}
        # Keyed by "<member id> — <name> (<username>)" (member ids are unique and
        # mandatory), same reasoning as above.
        self._member_by_display_text: dict[str, Member] = {}

        layout = QVBoxLayout(self)
        layout.addWidget(self._build_checkout_box())
        layout.addWidget(self._build_returns_box())

        self.refresh()

    def _build_checkout_box(self) -> QGroupBox:
        box = QGroupBox("Check Out")

        self._bibliography_input = QLineEdit()
        self._bibliography_input.setPlaceholderText("Call number...")
        self._bibliography_completer_model = QStringListModel()
        bibliography_completer = QCompleter(self._bibliography_completer_model, self)
        bibliography_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        bibliography_completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self._bibliography_input.setCompleter(bibliography_completer)
        self._bibliography_input.textChanged.connect(self._update_selected_book_label)

        self._selected_book_label = QLabel()
        self._update_selected_book_label()

        self._member_input = QLineEdit()
        self._member_input.setPlaceholderText("Member ID...")
        self._member_completer_model = QStringListModel()
        member_completer = QCompleter(self._member_completer_model, self)
        member_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        member_completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self._member_input.setCompleter(member_completer)
        self._member_input.textChanged.connect(self._update_selected_member_label)

        # Not initialized here the way _selected_book_label is above: this also
        # populates the Return table (see _update_selected_member_label), which needs
        # self._loans_table — built afterward, in _build_returns_box(). refresh(), at
        # the end of __init__, sets both the label and the table's initial contents.
        self._selected_member_label = QLabel()

        checkout_button = QPushButton("Check Out")
        checkout_button.clicked.connect(self._on_checkout)

        form = QFormLayout()
        form.addRow("Call Number:", self._bibliography_input)
        form.addRow(self._selected_book_label)
        form.addRow("Member ID:", self._member_input)
        form.addRow(self._selected_member_label)
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
        # Neither call-number nor member-id input box needs selection-restore logic:
        # rebuilding a QComboBox resets its index (which is why the member combo used
        # to need special handling), but a QLineEdit's typed/selected text is simply
        # untouched by refresh() and persists on its own.
        self._entry_by_display_text = {}
        for entry in self._search_catalog.execute(""):
            display = f"{entry.bibliography.call_number} — {entry.bibliography.title}"
            self._entry_by_display_text[display] = entry
        self._bibliography_completer_model.setStringList(sorted(self._entry_by_display_text))
        self._update_selected_book_label()

        self._member_by_display_text = {}
        for member in self._list_members.execute():
            display = f"{member.id} — {member.name}"
            if member.username:
                display += f" ({member.username})"
            self._member_by_display_text[display] = member
        self._member_completer_model.setStringList(sorted(self._member_by_display_text))

        self._loan_views = self._list_open_loans.execute()
        # Also (re)populates the Return table filtered to whatever member is currently
        # entered — must run after self._loan_views is fetched above.
        self._update_selected_member_label()

    def _populate_loans_table(self, member: Member | None) -> None:
        # Empty, i.e. no resolved member (whether the field is blank or just doesn't
        # match one yet), shows nothing — the table only ever lists one specific
        # member's outstanding loans, never everyone's at once.
        self._displayed_loans = (
            [] if member is None else [v for v in self._loan_views if v.loan.member_id == member.id]
        )
        self._loans_table.setRowCount(len(self._displayed_loans))
        for row, view in enumerate(self._displayed_loans):
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

    def _update_selected_member_label(self) -> None:
        # Same reasoning as _update_selected_book_label: confirm who's about to
        # receive the loan before checking out, rather than trusting the id alone.
        member = self._member_by_display_text.get(self._member_input.text().strip())
        if member is None:
            self._selected_member_label.setText("No matching member selected.")
            self._selected_member_label.setStyleSheet("color: gray;")
        else:
            username_part = f" ({member.username})" if member.username else ""
            self._selected_member_label.setText(f"{member.name}{username_part} — {member.role.value}")
            self._selected_member_label.setStyleSheet("")
        self._populate_loans_table(member)

    def _on_checkout(self) -> None:
        entry = self._entry_by_display_text.get(self._bibliography_input.text().strip())
        member = self._member_by_display_text.get(self._member_input.text().strip())
        if entry is None or member is None:
            QMessageBox.information(
                self, "Nothing to check out", "Select a book by call number and a member by member ID first."
            )
            return
        try:
            loan = self._checkout_item.execute(entry.bibliography.id, member.id)
        except BibliosphereError as error:
            QMessageBox.warning(self, "Could not check out", str(error))
            return
        QMessageBox.information(self, "Checked out", f"Due back {loan.due_date.isoformat()}.")
        # Otherwise the just-checked-out (now unavailable) book is left selected, and
        # its stale call number invites checking out the same title again by accident.
        self._bibliography_input.clear()
        self.refresh()

    def _on_return(self) -> None:
        row = self._loans_table.currentRow()
        if row < 0 or row >= len(self._displayed_loans):
            QMessageBox.information(self, "No selection", "Select a loan to return first.")
            return
        loan_id = self._displayed_loans[row].loan.id
        try:
            self._return_item.execute(loan_id)
        except BibliosphereError as error:
            QMessageBox.warning(self, "Could not return item", str(error))
            return
        self.refresh()
