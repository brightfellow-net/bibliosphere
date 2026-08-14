from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from bibliosphere.presentation.qt.manage_authors_dialog import ManageAuthorsDialog


class AddBibliographyDialog(QDialog):
    def __init__(self, all_author_names: list[str] = (), parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("Add Bibliography")
        self.resize(480, 240)
        self._all_author_names = list(all_author_names)
        self._authors: list[str] = []

        self._isbn = QLineEdit()
        self._title = QLineEdit()
        self._series_title = QLineEdit()
        self._edition = QLineEdit()
        self._publish_year = QLineEdit()
        self._call_number = QLineEdit()

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

    def values(self) -> tuple[str, str, str, str, str, str, list[str]]:
        return (
            self._isbn.text().strip(),
            self._title.text().strip(),
            self._series_title.text().strip(),
            self._edition.text().strip(),
            self._publish_year.text().strip(),
            self._call_number.text().strip(),
            self._authors,
        )
