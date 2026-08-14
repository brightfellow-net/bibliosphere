from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFormLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget

from bibliosphere.application.use_cases.authenticate_user import AuthenticateUser
from bibliosphere.domain.entities import Member
from bibliosphere.domain.exceptions import InvalidCredentials


class LoginView(QWidget):
    login_succeeded = Signal(Member)

    def __init__(self, authenticate_user: AuthenticateUser, parent: QWidget | None = None):
        super().__init__(parent)
        self._authenticate_user = authenticate_user

        self._username = QLineEdit()
        self._password = QLineEdit()
        self._password.setEchoMode(QLineEdit.EchoMode.Password)
        self._error_label = QLabel()
        self._error_label.setStyleSheet("color: red;")
        self._error_label.setVisible(False)

        login_button = QPushButton("Log In")
        login_button.setDefault(True)
        login_button.clicked.connect(self._on_login_clicked)
        self._password.returnPressed.connect(self._on_login_clicked)

        form = QFormLayout()
        form.addRow("Username:", self._username)
        form.addRow("Password:", self._password)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("<h2>Bibliosphere</h2>"))
        layout.addLayout(form)
        layout.addWidget(self._error_label)
        layout.addWidget(login_button)
        layout.addStretch()

    def _on_login_clicked(self) -> None:
        try:
            member = self._authenticate_user.execute(self._username.text(), self._password.text())
        except InvalidCredentials:
            self._error_label.setText("Invalid username or password.")
            self._error_label.setVisible(True)
            return

        self._error_label.setVisible(False)
        self._password.clear()
        self.login_succeeded.emit(member)
