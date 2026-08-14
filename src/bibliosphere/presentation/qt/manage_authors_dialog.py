from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCompleter,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

class ManageAuthorsDialog(QDialog):
    """Add/remove/reorder authors for a bibliography (existing or not-yet-created),
    independent of its other fields — list order becomes the stored author level
    (1 = main author). Takes a plain title + starting author names rather than a
    CatalogEntry so it can be opened from AddBibliographyDialog before a bibliography
    id exists, as well as from EditBibliographyDialog for an existing one.
    """

    def __init__(
        self,
        bibliography_title: str,
        initial_authors: list[str],
        all_author_names: list[str] = (),
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.setWindowTitle(f"Manage Authors — {bibliography_title}" if bibliography_title else "Manage Authors")
        self.resize(420, 320)
        self._all_author_names = list(all_author_names)

        self._list = QListWidget()
        for name in initial_authors:
            self._list.addItem(name)

        add_button = QPushButton("Add Author...")
        add_button.clicked.connect(self._on_add)
        remove_button = QPushButton("Remove")
        remove_button.clicked.connect(self._on_remove)
        up_button = QPushButton("Move Up")
        up_button.clicked.connect(self._on_move_up)
        down_button = QPushButton("Move Down")
        down_button.clicked.connect(self._on_move_down)

        button_row = QHBoxLayout()
        button_row.addWidget(add_button)
        button_row.addWidget(remove_button)
        button_row.addWidget(up_button)
        button_row.addWidget(down_button)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(self._list)
        layout.addLayout(button_row)
        layout.addWidget(buttons)

    def _on_add(self) -> None:
        name = self._prompt_for_author_name()
        if not name:
            return
        existing_names = {self._list.item(i).text() for i in range(self._list.count())}
        if name in existing_names:
            return
        self._list.addItem(name)

    def _prompt_for_author_name(self) -> str:
        dialog = QDialog(self)
        dialog.setWindowTitle("Add Author")

        line_edit = QLineEdit()
        completer = QCompleter(self._all_author_names, dialog)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        line_edit.setCompleter(completer)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)

        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel("Author name:"))
        layout.addWidget(line_edit)
        layout.addWidget(buttons)

        if not dialog.exec():
            return ""
        return line_edit.text().strip()

    def _on_remove(self) -> None:
        row = self._list.currentRow()
        if row >= 0:
            self._list.takeItem(row)

    def _on_move_up(self) -> None:
        row = self._list.currentRow()
        if row > 0:
            item = self._list.takeItem(row)
            self._list.insertItem(row - 1, item)
            self._list.setCurrentRow(row - 1)

    def _on_move_down(self) -> None:
        row = self._list.currentRow()
        if 0 <= row < self._list.count() - 1:
            item = self._list.takeItem(row)
            self._list.insertItem(row + 1, item)
            self._list.setCurrentRow(row + 1)

    def values(self) -> list[str]:
        return [self._list.item(i).text() for i in range(self._list.count())]
