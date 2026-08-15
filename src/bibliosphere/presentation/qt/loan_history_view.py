from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QLineEdit,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from bibliosphere.application.dto import LoanView
from bibliosphere.application.use_cases.list_loan_history import ListLoanHistory

_COLUMN_LABELS = ["Member ID", "Member Name", "Title", "Checkout Date", "Due Date", "Return Date", "Status"]


class LoanHistoryView(QWidget):
    """Librarian-only: every loan (open and returned) across all members."""

    def __init__(self, list_loan_history: ListLoanHistory, parent: QWidget | None = None):
        super().__init__(parent)
        self._list_loan_history = list_loan_history
        self._loan_views: list[LoanView] = []
        # The subset of self._loan_views actually shown after filtering — matches the
        # same filtered-subset-vs-full-list split used in CatalogView/MemberView.
        self._displayed_loan_views: list[LoanView] = []

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

        self.refresh()

    def refresh(self) -> None:
        self._loan_views = self._list_loan_history.execute()
        self._apply_filters()

    def _apply_filters(self) -> None:
        filters = [box.text().strip().lower() for box in self._column_filters]
        self._displayed_loan_views = [v for v in self._loan_views if self._matches_filters(v, filters)]

        # See CatalogView._apply_filters: avoids Qt re-sorting after every single
        # setItem() call while bulk-repopulating rows.
        self._table.setSortingEnabled(False)
        self._table.setRowCount(len(self._displayed_loan_views))
        for row, view in enumerate(self._displayed_loan_views):
            for column, value in enumerate(self._row_values(view)):
                self._table.setItem(row, column, QTableWidgetItem(value))
        self._table.setSortingEnabled(True)

    @staticmethod
    def _matches_filters(view: LoanView, filters: list[str]) -> bool:
        values = LoanHistoryView._row_values(view)
        return all(needle in value.lower() for needle, value in zip(filters, values) if needle)

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
