from datetime import date

from PySide6.QtWidgets import QComboBox, QDialog, QDialogButtonBox, QFormLayout, QLabel, QLineEdit, QVBoxLayout, QWidget

from bibliosphere.domain.entities import Member, Role
from bibliosphere.presentation.qt.dates import parse_optional_date


class EditMemberDialog(QDialog):
    def __init__(self, member: Member, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("Edit Member")

        self._username = QLineEdit(member.username)
        self._name = QLineEdit(member.name)
        self._password = QLineEdit()
        self._password.setEchoMode(QLineEdit.EchoMode.Password)
        self._password.setPlaceholderText("Leave blank to keep current password")
        self._role = QComboBox()
        self._role.addItem("Patron", Role.PATRON)
        self._role.addItem("Librarian", Role.LIBRARIAN)
        self._role.setCurrentIndex(self._role.findData(member.role))
        self._birthdate = QLineEdit(member.birthdate.isoformat() if member.birthdate else "")
        self._birthdate.setPlaceholderText("YYYY-MM-DD")
        self._email = QLineEdit(member.email or "")
        self._phone = QLineEdit(member.phone or "")
        self._expiry_date = QLineEdit(member.expiry_date.isoformat() if member.expiry_date else "")
        self._expiry_date.setPlaceholderText("YYYY-MM-DD")
        self._address = QLineEdit(member.address or "")

        form = QFormLayout()
        form.addRow("Username:", self._username)
        form.addRow("Name:", self._name)
        form.addRow("New Password:", self._password)
        form.addRow("Role:", self._role)
        form.addRow("Birthdate:", self._birthdate)
        form.addRow("Email:", self._email)
        form.addRow("Phone:", self._phone)
        form.addRow("Join date:", QLabel(member.join_date.isoformat() if member.join_date else "—"))
        form.addRow("Membership expiry:", self._expiry_date)
        form.addRow("Address:", self._address)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def values(self) -> tuple[str, str, str, Role, date | None, str | None, str | None, date | None, str | None]:
        return (
            self._username.text().strip(),
            self._name.text().strip(),
            self._password.text(),
            self._role.currentData(),
            parse_optional_date(self._birthdate.text()),
            self._email.text().strip() or None,
            self._phone.text().strip() or None,
            parse_optional_date(self._expiry_date.text()),
            self._address.text().strip() or None,
        )
