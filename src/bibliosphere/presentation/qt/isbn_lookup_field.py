from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QHBoxLayout, QLineEdit, QPushButton, QWidget

from bibliosphere.application.use_cases.lookup_book_by_isbn import LookupBookByIsbn
from bibliosphere.domain.exceptions import BibliosphereError


class IsbnLookupField(QWidget):
    """An ISBN line edit with a "Load" button beside it that fetches book metadata.

    Emits `book_loaded(BookMetadata)` on success or `lookup_failed(str)` with a
    user-facing message; the owning dialog decides how to apply or display them.
    The lookup is a blocking network call (bounded by the provider's timeout), shown
    with a wait cursor.
    """

    book_loaded = Signal(object)
    lookup_failed = Signal(str)

    def __init__(self, lookup: LookupBookByIsbn | None, text: str = "", parent: QWidget | None = None):
        super().__init__(parent)
        self._lookup = lookup
        self.line_edit = QLineEdit(text)
        self._button = QPushButton("Load")
        self._button.setEnabled(lookup is not None)
        self._button.clicked.connect(self._on_load_clicked)
        self.line_edit.returnPressed.connect(self._on_load_clicked)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.line_edit, stretch=1)
        layout.addWidget(self._button)

    def _on_load_clicked(self) -> None:
        if self._lookup is None:
            return
        self._button.setEnabled(False)
        QGuiApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            metadata = self._lookup.execute(self.line_edit.text())
        except BibliosphereError as error:
            self.lookup_failed.emit(str(error))
            return
        finally:
            QGuiApplication.restoreOverrideCursor()
            self._button.setEnabled(True)
        self.book_loaded.emit(metadata)
