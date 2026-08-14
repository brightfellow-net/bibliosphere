from PySide6.QtWidgets import QDialog, QDialogButtonBox, QFormLayout, QLineEdit, QVBoxLayout, QWidget

from bibliosphere.application.dto import CatalogEntry


class EditBibliographyDialog(QDialog):
    def __init__(self, entry: CatalogEntry, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("Edit Bibliography")
        self.resize(480, 200)

        self._isbn = QLineEdit(entry.bibliography.isbn_issn or "")
        self._title = QLineEdit(entry.bibliography.title)
        self._series_title = QLineEdit(entry.bibliography.series_title or "")
        self._edition = QLineEdit(entry.bibliography.edition or "")
        self._publish_year = QLineEdit(entry.bibliography.publish_year or "")
        self._call_number = QLineEdit(entry.bibliography.call_number or "")

        form = QFormLayout()
        form.addRow("ISBN/ISSN:", self._isbn)
        form.addRow("Title:", self._title)
        form.addRow("Series Title:", self._series_title)
        form.addRow("Edition:", self._edition)
        form.addRow("Publish Year:", self._publish_year)
        form.addRow("Call Number:", self._call_number)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def values(self) -> tuple[str, str, str, str, str, str]:
        return (
            self._isbn.text().strip(),
            self._title.text().strip(),
            self._series_title.text().strip(),
            self._edition.text().strip(),
            self._publish_year.text().strip(),
            self._call_number.text().strip(),
        )
