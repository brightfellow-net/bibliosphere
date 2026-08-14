from PySide6.QtWidgets import QDialog, QDialogButtonBox, QFormLayout, QLineEdit, QVBoxLayout, QWidget

from bibliosphere.domain.entities import Member


class EditMemberDialog(QDialog):
    def __init__(self, member: Member, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("Edit Member")

        self._username = QLineEdit(member.username)
        self._name = QLineEdit(member.name)

        form = QFormLayout()
        form.addRow("Username:", self._username)
        form.addRow("Name:", self._name)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def values(self) -> tuple[str, str]:
        return self._username.text().strip(), self._name.text().strip()
