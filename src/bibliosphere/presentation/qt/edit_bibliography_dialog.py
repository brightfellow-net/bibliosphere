from PySide6.QtCore import QTimer
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
from bibliosphere.application.use_cases.edit_bibliography import EditBibliography
from bibliosphere.application.use_cases.set_bibliography_authors import SetBibliographyAuthors
from bibliosphere.domain.exceptions import BibliosphereError
from bibliosphere.domain.ids import require_id
from bibliosphere.presentation.qt.manage_authors_dialog import ManageAuthorsDialog

_CLOSE_DELAY_MS = 1000


class EditBibliographyDialog(QDialog):
    """Stays open and shows the error on invalid input, instead of closing on OK and
    leaving the caller to report the failure after the fields are already gone — the
    use case is called (and can be retried) from within this dialog. On success, it
    shows a confirmation and closes itself after a brief delay instead of vanishing
    immediately, so the confirmation is actually visible.
    """

    def __init__(
        self,
        entry: CatalogEntry,
        edit_bibliography: EditBibliography,
        set_bibliography_authors: SetBibliographyAuthors | None = None,
        all_author_names: list[str] | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Edit Bibliography")
        self.resize(480, 240)
        self._bibliography = entry.bibliography
        self._edit_bibliography = edit_bibliography
        self._set_bibliography_authors = set_bibliography_authors
        self._all_author_names = list(all_author_names or [])
        self._current_authors = [credit.author.name for credit in entry.authors]

        self._call_number = QLineEdit(entry.bibliography.call_number or "")
        self._title = QLineEdit(entry.bibliography.title)
        self._isbn = QLineEdit(entry.bibliography.isbn_issn or "")
        self._series_title = QLineEdit(entry.bibliography.series_title or "")
        self._edition = QLineEdit(entry.bibliography.edition or "")
        self._publish_year = QLineEdit(entry.bibliography.publish_year or "")

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
        manage_authors_button.setEnabled(self._set_bibliography_authors is not None)
        manage_authors_button.clicked.connect(self._on_manage_authors)

        authors_row = QHBoxLayout()
        authors_row.addWidget(self._authors_label, stretch=1)
        authors_row.addWidget(manage_authors_button)

        self._status_label = QLabel()
        self._status_label.setWordWrap(True)

        self._buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self._buttons.accepted.connect(self._on_ok_clicked)
        self._buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addLayout(authors_row)
        layout.addWidget(self._status_label)
        layout.addWidget(self._buttons)

    def _set_status(self, message: str, *, is_error: bool) -> None:
        self._status_label.setStyleSheet(f"color: {'#c0392b' if is_error else '#1e8449'};")
        self._status_label.setText(message)

    def _update_authors_label(self) -> None:
        self._authors_label.setText(
            f"Authors: {', '.join(self._current_authors)}" if self._current_authors else "Authors: (none)"
        )

    def _on_manage_authors(self) -> None:
        assert self._set_bibliography_authors is not None
        set_bibliography_authors = self._set_bibliography_authors
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
            set_bibliography_authors.execute(require_id(self._bibliography.id), new_authors)
        except BibliosphereError as error:
            QMessageBox.warning(self, "Could not update authors", str(error))
            return
        self._current_authors = new_authors
        self._update_authors_label()

    def _on_ok_clicked(self) -> None:
        existing = self._bibliography
        try:
            # Forward the fields this dialog doesn't expose (sor, publisher_id, etc.)
            # unchanged, so editing here can't silently null them out. `authors` here
            # reflects whatever "Manage Authors..." already persisted (or the original
            # list if untouched) — this write is therefore a harmless no-op for authors
            # in the common case, not a second source of truth for them.
            self._edit_bibliography.execute(
                require_id(existing.id),
                title=self._title.text().strip(),
                authors=self._current_authors,
                call_number=self._call_number.text().strip(),
                isbn_issn=self._isbn.text().strip() or None,
                sor=existing.sor,
                edition=self._edition.text().strip() or None,
                publish_year=self._publish_year.text().strip() or None,
                collation=existing.collation,
                series_title=self._series_title.text().strip() or None,
                classification=existing.classification,
                notes=existing.notes,
                language_id=existing.language_id,
                gmd_id=existing.gmd_id,
                publisher_id=existing.publisher_id,
                publish_place_id=existing.publish_place_id,
                content_type_id=existing.content_type_id,
                media_type_id=existing.media_type_id,
                carrier_type_id=existing.carrier_type_id,
            )
        except BibliosphereError as error:
            self._set_status(str(error), is_error=True)
            return
        self._set_status("Bibliography updated.", is_error=False)
        # Disable further edits/clicks while the confirmation is showing, then close on
        # its own — the user asked for the success message to actually be visible
        # instead of the dialog vanishing the instant OK is clicked.
        self._buttons.setEnabled(False)
        QTimer.singleShot(_CLOSE_DELAY_MS, self.accept)
