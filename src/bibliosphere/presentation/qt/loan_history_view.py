from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from bibliosphere.application.dto import LoanHistoryPage, LoanView
from bibliosphere.application.use_cases.list_loan_history import ListLoanHistory
from bibliosphere.domain.ports import LoanHistoryFilters

_COLUMN_LABELS = ["Member ID", "Member Name", "Title", "Checkout Date", "Due Date", "Return Date", "Status"]
_FILTER_FIELDS = ["member_id", "member_name", "title", "checkout_date", "due_date", "return_date", "status"]
# Loan history is unbounded (docs/requirements.md §6.1), so only one page is ever
# fetched/materialized at a time — see ListLoanHistory / SqliteLoanRepository.
_PAGE_SIZE = 200
# A member_name/title filter needs a substring scan across the whole (unbounded)
# history — debounce so typing doesn't fire one such query per keystroke.
_FILTER_DEBOUNCE_MS = 300


class LoanHistoryView(QWidget):
    """Librarian-only: every loan (open and returned) across all members, paginated
    and filtered at the repository so it stays responsive at very large data volumes.
    """

    def __init__(self, list_loan_history: ListLoanHistory, parent: QWidget | None = None):
        super().__init__(parent)
        self._list_loan_history = list_loan_history
        self._page = 1

        self._filter_debounce = QTimer(self)
        self._filter_debounce.setSingleShot(True)
        self._filter_debounce.setInterval(_FILTER_DEBOUNCE_MS)
        self._filter_debounce.timeout.connect(self._on_filters_changed)

        self._column_filters: dict[str, QLineEdit] = {}
        filter_row = QHBoxLayout()
        for field, label in zip(_FILTER_FIELDS, _COLUMN_LABELS):
            filter_box = QLineEdit()
            filter_box.setPlaceholderText(f"Filter {label}...")
            filter_box.textChanged.connect(lambda _text: self._filter_debounce.start())
            self._column_filters[field] = filter_box
            filter_row.addWidget(filter_box)

        self._table = QTableWidget(0, len(_COLUMN_LABELS))
        self._table.setHorizontalHeaderLabels(_COLUMN_LABELS)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        # No setSortingEnabled: only one page of the full history is ever loaded, so
        # letting the header re-sort it would silently sort just that page, not the
        # whole (unbounded) dataset — misleading rather than useful.

        self._previous_button = QPushButton("< Previous")
        self._previous_button.clicked.connect(self._on_previous)
        self._page_label = QLabel()
        self._next_button = QPushButton("Next >")
        self._next_button.clicked.connect(self._on_next)

        pagination_row = QHBoxLayout()
        pagination_row.addWidget(self._previous_button)
        pagination_row.addWidget(self._page_label)
        pagination_row.addWidget(self._next_button)
        pagination_row.addStretch()

        layout = QVBoxLayout(self)
        layout.addLayout(filter_row)
        layout.addWidget(self._table)
        layout.addLayout(pagination_row)

        self.refresh()

    def refresh(self) -> None:
        self._load_page()

    def _current_filters(self) -> LoanHistoryFilters:
        return LoanHistoryFilters(**{field: box.text().strip() for field, box in self._column_filters.items()})

    def _on_filters_changed(self) -> None:
        self._page = 1
        self._load_page()

    def _on_previous(self) -> None:
        if self._page > 1:
            self._page -= 1
            self._load_page()

    def _on_next(self) -> None:
        self._page += 1
        self._load_page()

    def _load_page(self) -> None:
        result = self._list_loan_history.execute(self._current_filters(), page=self._page, page_size=_PAGE_SIZE)
        # A stale Next click (or a filter change shrinking the result set) can request
        # a page past the new last page — clamp and reload once rather than show it empty.
        if not result.views and self._page > result.total_pages:
            self._page = result.total_pages
            result = self._list_loan_history.execute(self._current_filters(), page=self._page, page_size=_PAGE_SIZE)
        self._populate_table(result)

    def _populate_table(self, result: LoanHistoryPage) -> None:
        self._table.setRowCount(len(result.views))
        for row, view in enumerate(result.views):
            for column, value in enumerate(self._row_values(view)):
                self._table.setItem(row, column, QTableWidgetItem(value))

        self._page_label.setText(f"Page {result.page} of {result.total_pages} ({result.total_count} total)")
        self._previous_button.setEnabled(result.page > 1)
        self._next_button.setEnabled(result.page < result.total_pages)

    @staticmethod
    def _row_values(view: LoanView) -> list[str]:
        loan = view.loan
        return [
            loan.member_id,
            view.member_name,
            view.bibliography_title,
            loan.checkout_date.isoformat(),
            loan.due_date.isoformat(),
            loan.return_date.isoformat() if loan.return_date else "",
            "Checked Out" if loan.is_open else "Returned",
        ]
