from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from bibliosphere.application.use_cases.list_member_loans import ListMemberLoans


class MyLoansView(QWidget):
    """Patron-only: view their own current loans and due dates."""

    def __init__(self, list_member_loans: ListMemberLoans, member_id: int, parent: QWidget | None = None):
        super().__init__(parent)
        self._list_member_loans = list_member_loans
        self._member_id = member_id

        self._table = QTableWidget(0, 2)
        self._table.setHorizontalHeaderLabels(["Title", "Due Date"])
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        refresh_button = QPushButton("Refresh")
        refresh_button.clicked.connect(self.refresh)

        layout = QVBoxLayout(self)
        layout.addWidget(self._table)
        layout.addWidget(refresh_button)

        self.refresh()

    def refresh(self) -> None:
        loan_views = self._list_member_loans.execute(self._member_id)
        self._table.setRowCount(len(loan_views))
        for row, view in enumerate(loan_views):
            self._table.setItem(row, 0, QTableWidgetItem(view.bibliography_title))
            self._table.setItem(row, 1, QTableWidgetItem(view.loan.due_date.isoformat()))
