from PySide6.QtWidgets import QComboBox, QDialog, QDialogButtonBox, QFormLayout, QLineEdit, QVBoxLayout, QWidget

from bibliosphere.domain.entities import Role


class AddMemberDialog(QDialog):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("Add Member")

        self._username = QLineEdit()
        self._name = QLineEdit()
        self._password = QLineEdit()
        self._password.setEchoMode(QLineEdit.EchoMode.Password)
        self._role = QComboBox()
        self._role.addItem("Patron", Role.PATRON)
        self._role.addItem("Librarian", Role.LIBRARIAN)

        form = QFormLayout()
        form.addRow("Username:", self._username)
        form.addRow("Name:", self._name)
        form.addRow("Password:", self._password)
        form.addRow("Role:", self._role)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def values(self) -> tuple[str, str, str, Role]:
        return (
            self._username.text().strip(),
            self._name.text().strip(),
            self._password.text(),
            self._role.currentData(),
        )
