from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
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

        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels(["ID", "Username", "Name", "Role"])
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
        layout.addWidget(self._table)
        layout.addLayout(button_row)

        self.refresh()

    def refresh(self) -> None:
        self._members = self._list_members.execute()
        self._table.setRowCount(len(self._members))
        for row, member in enumerate(self._members):
            self._table.setItem(row, 0, QTableWidgetItem(member.id))
            self._table.setItem(row, 1, QTableWidgetItem(member.username))
            self._table.setItem(row, 2, QTableWidgetItem(member.name))
            self._table.setItem(row, 3, QTableWidgetItem(member.role.value))

    def _selected_member(self) -> Member | None:
        row = self._table.currentRow()
        if row < 0 or row >= len(self._members):
            return None
        return self._members[row]

    def _on_add_member(self) -> None:
        suggested_id = self._generate_member_id.execute()
        dialog = AddMemberDialog(suggested_id, self)
        if not dialog.exec():
            return
        member_id, username, name, password, role = dialog.values()
        try:
            self._create_member.execute(member_id, username, name, password, role)
        except BibliosphereError as error:
            QMessageBox.warning(self, "Could not add member", str(error))
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
        username, name, password = dialog.values()
        try:
            self._edit_member.execute(member.id, username, name, password)
        except BibliosphereError as error:
            QMessageBox.warning(self, "Could not edit member", str(error))
            return
        self.refresh()
