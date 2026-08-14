from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from bibliosphere.application.use_cases.create_member import CreateMember
from bibliosphere.domain.entities import Role
from bibliosphere.domain.exceptions import BibliosphereError
from bibliosphere.presentation.qt.dates import parse_optional_date


class AddMemberDialog(QDialog):
    """OK never closes this dialog on invalid input — the use case is called (and can
    be retried) from within the dialog itself, showing the error inline instead of
    closing and leaving the caller to report the failure after the fields are gone.
    """

    def __init__(self, suggested_member_id: str, create_member: CreateMember, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("Add Member")
        self.resize(480, 360)
        self._create_member = create_member

        self._member_id = QLineEdit(suggested_member_id)
        self._username = QLineEdit()
        self._name = QLineEdit()
        self._password = QLineEdit()
        self._password.setEchoMode(QLineEdit.EchoMode.Password)
        self._role = QComboBox()
        self._role.addItem("Patron", Role.PATRON)
        self._role.addItem("Librarian", Role.LIBRARIAN)
        self._role.currentIndexChanged.connect(self._update_credential_hints)
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

        self._status_label = QLabel()
        self._status_label.setWordWrap(True)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._on_ok_clicked)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(self._status_label)
        layout.addWidget(buttons)

        self._update_credential_hints()

    def _update_credential_hints(self) -> None:
        # Only librarians must be able to log in; a patron with neither is fine.
        hint = "Optional for patrons" if self._role.currentData() is Role.PATRON else ""
        self._username.setPlaceholderText(hint)
        self._password.setPlaceholderText(hint)

    def _set_status(self, message: str, *, is_error: bool) -> None:
        self._status_label.setStyleSheet(f"color: {'#c0392b' if is_error else '#1e8449'};")
        self._status_label.setText(message)

    def _on_ok_clicked(self) -> None:
        try:
            birthdate = parse_optional_date(self._birthdate.text())
            expiry_date = parse_optional_date(self._expiry_date.text())
        except ValueError as error:
            self._set_status(f"Invalid date: {error}", is_error=True)
            return
        try:
            self._create_member.execute(
                self._member_id.text().strip(),
                self._username.text().strip(),
                self._name.text().strip(),
                self._password.text(),
                self._role.currentData(),
                birthdate,
                self._email.text().strip() or None,
                self._phone.text().strip() or None,
                expiry_date,
                self._address.text().strip() or None,
            )
        except BibliosphereError as error:
            self._set_status(str(error), is_error=True)
            return
        self.accept()
