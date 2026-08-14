from PySide6.QtWidgets import QDialog, QDialogButtonBox, QFormLayout, QLineEdit, QVBoxLayout, QWidget


class AddBibliographyDialog(QDialog):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("Add Bibliography")
        self.resize(480, 200)

        self._isbn = QLineEdit()
        self._title = QLineEdit()
        self._authors = QLineEdit()
        self._edition = QLineEdit()
        self._publish_year = QLineEdit()
        self._call_number = QLineEdit()

        form = QFormLayout()
        form.addRow("ISBN/ISSN:", self._isbn)
        form.addRow("Title:", self._title)
        form.addRow("Authors (comma-separated):", self._authors)
        form.addRow("Edition:", self._edition)
        form.addRow("Publish Year:", self._publish_year)
        form.addRow("Call Number:", self._call_number)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def values(self) -> tuple[str, str, list[str], str, str, str]:
        authors = [name.strip() for name in self._authors.text().split(",") if name.strip()]
        return (
            self._isbn.text().strip(),
            self._title.text().strip(),
            authors,
            self._edition.text().strip(),
            self._publish_year.text().strip(),
            self._call_number.text().strip(),
        )
