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

from bibliosphere.application.use_cases.create_member import CreateMember
from bibliosphere.application.use_cases.edit_member import EditMember
from bibliosphere.application.use_cases.generate_member_id import GenerateMemberId
from bibliosphere.application.use_cases.list_members import ListMembers
from bibliosphere.domain.entities import Member
from bibliosphere.domain.exceptions import BibliosphereError
from bibliosphere.presentation.qt.add_member_dialog import AddMemberDialog
from bibliosphere.presentation.qt.edit_member_dialog import EditMemberDialog

_COLUMN_LABELS = [
    "ID",
    "Username",
    "Name",
    "Role",
    "Birthdate",
    "Email",
    "Phone",
    "Join Date",
    "Expiry Date",
    "Address",
]


class MemberView(QWidget):
    """Librarian-only: create and edit patron/librarian accounts."""

    def __init__(
        self,
        list_members: ListMembers,
        create_member: CreateMember,
        edit_member: EditMember,
        generate_member_id: GenerateMemberId,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._list_members = list_members
        self._create_member = create_member
        self._edit_member = edit_member
        self._generate_member_id = generate_member_id
        self._members: list[Member] = []
        # The subset of self._members actually shown after filtering — _selected_member
        # indexes into this, not self._members, since a filtered table's row order
        # diverges from the unfiltered list.
        self._displayed_members: list[Member] = []

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

        add_button = QPushButton("Add Member...")
        add_button.clicked.connect(self._on_add_member)
        edit_button = QPushButton("Edit Selected...")
        edit_button.clicked.connect(self._on_edit_member)

        button_row = QHBoxLayout()
        button_row.addWidget(add_button)
        button_row.addWidget(edit_button)

        layout = QVBoxLayout(self)
        layout.addLayout(filter_row)
        layout.addWidget(self._table)
        layout.addLayout(button_row)

        self.refresh()

    def refresh(self) -> None:
        self._members = self._list_members.execute()
        self._apply_filters()

    def _apply_filters(self) -> None:
        filters = [box.text().strip().lower() for box in self._column_filters]
        self._displayed_members = [m for m in self._members if self._matches_filters(m, filters)]
        self._table.setRowCount(len(self._displayed_members))
        for row, member in enumerate(self._displayed_members):
            for column, value in enumerate(self._row_values(member)):
                self._table.setItem(row, column, QTableWidgetItem(value))

    @staticmethod
    def _matches_filters(member: Member, filters: list[str]) -> bool:
        values = MemberView._row_values(member)
        return all(needle in value.lower() for needle, value in zip(filters, values) if needle)

    @staticmethod
    def _row_values(member: Member) -> list[str]:
        return [
            member.id,
            member.username,
            member.name,
            member.role.value,
            member.birthdate.isoformat() if member.birthdate else "",
            member.email or "",
            member.phone or "",
            member.join_date.isoformat() if member.join_date else "",
            member.expiry_date.isoformat() if member.expiry_date else "",
            member.address or "",
        ]

    def _selected_member(self) -> Member | None:
        row = self._table.currentRow()
        if row < 0 or row >= len(self._displayed_members):
            return None
        return self._displayed_members[row]

    def _on_add_member(self) -> None:
        suggested_id = self._generate_member_id.execute()
        dialog = AddMemberDialog(suggested_id, self._create_member, self)
        if not dialog.exec():
            return
        self.refresh()

    def _on_edit_member(self) -> None:
        member = self._selected_member()
        if member is None:
            QMessageBox.information(self, "No selection", "Select a member first.")
            return
        dialog = EditMemberDialog(member, self)
        if not dialog.exec():
            return
        try:
            username, name, password, role, birthdate, email, phone, expiry_date, address = dialog.values()
            self._edit_member.execute(
                member.id, username, name, role, password, birthdate, email, phone, expiry_date, address
            )
        except ValueError as error:
            QMessageBox.warning(self, "Could not edit member", f"Invalid date: {error}")
            return
        except BibliosphereError as error:
            QMessageBox.warning(self, "Could not edit member", str(error))
            return
        self.refresh()
