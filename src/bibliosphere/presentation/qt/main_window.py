from PySide6.QtWidgets import QMainWindow, QStackedWidget, QTabWidget, QWidget

from bibliosphere.application.container import UseCases
from bibliosphere.domain.entities import Member, Role
from bibliosphere.presentation.qt.catalog_view import CatalogView
from bibliosphere.presentation.qt.checkout_view import CheckoutView
from bibliosphere.presentation.qt.login_view import LoginView
from bibliosphere.presentation.qt.member_view import MemberView
from bibliosphere.presentation.qt.my_loans_view import MyLoansView


class MainWindow(QMainWindow):
    def __init__(self, use_cases: UseCases):
        super().__init__()
        self.setWindowTitle("Bibliosphere")
        self.resize(900, 600)
        self._use_cases = use_cases
        self._dashboard: QWidget | None = None

        self._stack = QStackedWidget()
        self.setCentralWidget(self._stack)

        self._login_view = LoginView(use_cases.authenticate_user)
        self._login_view.login_succeeded.connect(self._on_login)
        self._stack.addWidget(self._login_view)

    def _on_login(self, member: Member) -> None:
        if self._dashboard is not None:
            self._stack.removeWidget(self._dashboard)
            self._dashboard.deleteLater()

        self._dashboard = self._build_dashboard(member)
        self._stack.addWidget(self._dashboard)
        self._stack.setCurrentWidget(self._dashboard)
        self.statusBar().showMessage(f"Logged in as {member.name} ({member.role.value})")

    def _build_dashboard(self, member: Member) -> QWidget:
        tabs = QTabWidget()
        uc = self._use_cases

        if member.role is Role.LIBRARIAN:
            catalog = CatalogView(
                uc.search_catalog,
                add_bibliography=uc.add_bibliography,
                edit_bibliography=uc.edit_bibliography,
                add_item=uc.add_item,
                remove_item=uc.remove_item,
            )
            tabs.addTab(catalog, "Catalog")

            members = MemberView(uc.list_members, uc.create_member, uc.edit_member)
            tabs.addTab(members, "Members")

            checkout = CheckoutView(
                uc.search_catalog, uc.list_members, uc.checkout_item, uc.list_open_loans, uc.return_item
            )
            tabs.addTab(checkout, "Checkout / Return")
        else:
            catalog = CatalogView(uc.search_catalog)
            tabs.addTab(catalog, "Catalog")

            my_loans = MyLoansView(uc.list_member_loans, member.id)
            tabs.addTab(my_loans, "My Loans")

        # Each tab's own view already refreshes itself on construction; this catches it
        # back up on every subsequent switch, since actions in one tab (e.g. adding a
        # bibliography in Catalog) don't otherwise reach the other tabs' cached state
        # (e.g. Checkout's bibliography dropdown).
        tabs.currentChanged.connect(lambda index: tabs.widget(index).refresh())

        return tabs
