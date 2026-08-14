from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QInputDialog,
    QListWidget,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from bibliosphere.application.dto import CatalogEntry


class ManageAuthorsDialog(QDialog):
    """Add/remove/reorder a single bibliography's authors, independent of its other
    fields — list order becomes the stored author level (1 = main author).
    """

    def __init__(self, entry: CatalogEntry, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle(f"Manage Authors — {entry.bibliography.title}")
        self.resize(420, 320)

        self._list = QListWidget()
        for credit in entry.authors:
            self._list.addItem(credit.author.name)

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
        name, ok = QInputDialog.getText(self, "Add Author", "Author name:")
        name = name.strip()
        if not ok or not name:
            return
        existing_names = {self._list.item(i).text() for i in range(self._list.count())}
        if name in existing_names:
            return
        self._list.addItem(name)

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
