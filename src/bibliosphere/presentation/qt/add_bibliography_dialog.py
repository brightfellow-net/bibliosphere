from PySide6.QtCore import Signal
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

from bibliosphere.application.use_cases.add_bibliography import AddBibliography
from bibliosphere.domain.exceptions import BibliosphereError
from bibliosphere.presentation.qt.manage_authors_dialog import ManageAuthorsDialog


class AddBibliographyDialog(QDialog):
    """OK never closes this dialog on its own — the use case is called (and can be
    retried) from within the dialog itself:

    - Invalid input: shows the error and stays open with the fields as entered.
    - Valid input: adds the bibliography, emits `bibliography_added` so the caller can
      refresh immediately, then clears the fields and stays open so a librarian can
      keep entering books back-to-back without reopening the dialog.

    Only Cancel (or closing the window) ends the dialog.
    """

    bibliography_added = Signal()

    def __init__(
        self, add_bibliography: AddBibliography, all_author_names: list[str] = (), parent: QWidget | None = None
    ):
        super().__init__(parent)
        self.setWindowTitle("Add Bibliography")
        self.resize(480, 240)
        self._add_bibliography = add_bibliography
        self._all_author_names = list(all_author_names)
        self._authors: list[str] = []

        self._call_number = QLineEdit()
        self._title = QLineEdit()
        self._isbn = QLineEdit()
        self._series_title = QLineEdit()
        self._edition = QLineEdit()
        self._publish_year = QLineEdit()

        form = QFormLayout()
        form.addRow("Call Number:", self._call_number)
        form.addRow("Title:", self._title)
        form.addRow("ISBN/ISSN:", self._isbn)
        form.addRow("Series Title:", self._series_title)
        form.addRow("Edition:", self._edition)
        form.addRow("Publish Year:", self._publish_year)

        self._authors_label = QLabel()
        self._authors_label.setWordWrap(True)
        self._update_authors_label()
        manage_authors_button = QPushButton("Manage Authors...")
        manage_authors_button.clicked.connect(self._on_manage_authors)

        authors_row = QHBoxLayout()
        authors_row.addWidget(self._authors_label, stretch=1)
        authors_row.addWidget(manage_authors_button)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._on_ok_clicked)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addLayout(authors_row)
        layout.addWidget(buttons)

    def _update_authors_label(self) -> None:
        self._authors_label.setText(f"Authors: {', '.join(self._authors)}" if self._authors else "Authors: (none)")

    def _on_manage_authors(self) -> None:
        # No bibliography id exists yet, so this can't persist immediately (unlike
        # EditBibliographyDialog's) — it only stages the list until the whole dialog
        # is accepted, at which point AddBibliography.execute() creates the record and
        # links these authors in one atomic step.
        dialog = ManageAuthorsDialog(self._title.text().strip(), self._authors, self._all_author_names, self)
        if not dialog.exec():
            return
        self._authors = dialog.values()
        self._update_authors_label()

    def _on_ok_clicked(self) -> None:
        try:
            self._add_bibliography.execute(
                title=self._title.text().strip(),
                authors=self._authors,
                call_number=self._call_number.text().strip(),
                isbn_issn=self._isbn.text().strip() or None,
                series_title=self._series_title.text().strip() or None,
                edition=self._edition.text().strip() or None,
                publish_year=self._publish_year.text().strip() or None,
            )
        except BibliosphereError as error:
            QMessageBox.warning(self, "Could not add bibliography", str(error))
            return
        self.bibliography_added.emit()
        self._reset_fields()

    def _reset_fields(self) -> None:
        for field in (
            self._call_number,
            self._title,
            self._isbn,
            self._series_title,
            self._edition,
            self._publish_year,
        ):
            field.clear()
        self._authors = []
        self._update_authors_label()
        self._call_number.setFocus()
