from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from bibliosphere.application.dto import CatalogEntry
from bibliosphere.application.use_cases.set_bibliography_authors import SetBibliographyAuthors
from bibliosphere.domain.exceptions import BibliosphereError
from bibliosphere.presentation.qt.manage_authors_dialog import ManageAuthorsDialog


class EditBibliographyDialog(QDialog):
    def __init__(
        self,
        entry: CatalogEntry,
        set_bibliography_authors: SetBibliographyAuthors | None = None,
        all_author_names: list[str] = (),
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Edit Bibliography")
        self.resize(480, 240)
        self._bibliography_id = entry.bibliography.id
        self._set_bibliography_authors = set_bibliography_authors
        self._all_author_names = list(all_author_names)
        self._current_authors = [credit.author.name for credit in entry.authors]

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

        self._authors_label = QLabel()
        self._authors_label.setWordWrap(True)
        self._update_authors_label()
        manage_authors_button = QPushButton("Manage Authors...")
        manage_authors_button.setEnabled(self._set_bibliography_authors is not None)
        manage_authors_button.clicked.connect(self._on_manage_authors)

        authors_row = QHBoxLayout()
        authors_row.addWidget(self._authors_label, stretch=1)
        authors_row.addWidget(manage_authors_button)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addLayout(authors_row)
        layout.addWidget(buttons)

    def _update_authors_label(self) -> None:
        self._authors_label.setText(
            f"Authors: {', '.join(self._current_authors)}" if self._current_authors else "Authors: (none)"
        )

    def _on_manage_authors(self) -> None:
        title = self._title.text().strip()
        dialog = ManageAuthorsDialog(title, self._current_authors, self._all_author_names, self)
        if not dialog.exec():
            return
        new_authors = dialog.values()
        try:
            # This bibliography already exists, so — unlike AddBibliographyDialog's
            # staged-until-OK approach — persist immediately: the author list is a
            # fully separate, independently-committed action from the rest of this
            # dialog's fields, taking effect even if the outer edit is then cancelled.
            self._set_bibliography_authors.execute(self._bibliography_id, new_authors)
        except BibliosphereError as error:
            QMessageBox.warning(self, "Could not update authors", str(error))
            return
        self._current_authors = new_authors
        self._update_authors_label()

    def values(self) -> tuple[str, str, str, str, str, str, list[str]]:
        return (
            self._isbn.text().strip(),
            self._title.text().strip(),
            self._series_title.text().strip(),
            self._edition.text().strip(),
            self._publish_year.text().strip(),
            self._call_number.text().strip(),
            self._current_authors,
        )
