from datetime import date

from PySide6.QtWidgets import QComboBox, QDialog, QDialogButtonBox, QFormLayout, QLineEdit, QVBoxLayout, QWidget

from bibliosphere.domain.entities import Role
from bibliosphere.presentation.qt.dates import parse_optional_date


class AddMemberDialog(QDialog):
    def __init__(self, suggested_member_id: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("Add Member")

        self._member_id = QLineEdit(suggested_member_id)
        self._username = QLineEdit()
        self._name = QLineEdit()
        self._password = QLineEdit()
        self._password.setEchoMode(QLineEdit.EchoMode.Password)
        self._role = QComboBox()
        self._role.addItem("Patron", Role.PATRON)
        self._role.addItem("Librarian", Role.LIBRARIAN)
        self._birthdate = QLineEdit()
        self._birthdate.setPlaceholderText("YYYY-MM-DD")
        self._email = QLineEdit()
        self._phone = QLineEdit()
        self._expiry_date = QLineEdit()
        self._expiry_date.setPlaceholderText("YYYY-MM-DD")
        self._address = QLineEdit()

        form = QFormLayout()
        form.addRow("Member ID:", self._member_id)
        form.addRow("Username:", self._username)
        form.addRow("Name:", self._name)
        form.addRow("Password:", self._password)
        form.addRow("Role:", self._role)
        form.addRow("Birthdate:", self._birthdate)
        form.addRow("Email:", self._email)
        form.addRow("Phone:", self._phone)
        form.addRow("Membership expiry:", self._expiry_date)
        form.addRow("Address:", self._address)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def values(self) -> tuple[str, str, str, str, Role, date | None, str | None, str | None, date | None, str | None]:
        return (
            self._member_id.text().strip(),
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
