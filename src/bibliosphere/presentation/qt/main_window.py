from typing import Protocol

from PySide6.QtWidgets import QMainWindow, QStackedWidget, QTabWidget, QWidget

from bibliosphere.application.container import UseCases
from bibliosphere.domain.entities import Member, Role
from bibliosphere.presentation.qt.catalog_view import CatalogView
from bibliosphere.presentation.qt.checkout_view import CheckoutView
from bibliosphere.presentation.qt.login_view import LoginView
from bibliosphere.presentation.qt.member_view import MemberView
from bibliosphere.presentation.qt.my_loans_view import MyLoansView


class _RefreshableTab(Protocol):
    def refresh(self) -> None: ...


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
        views: list[_RefreshableTab] = []

        if member.role is Role.LIBRARIAN:
            catalog = CatalogView(
                uc.search_catalog,
                add_bibliography=uc.add_bibliography,
                edit_bibliography=uc.edit_bibliography,
                set_bibliography_authors=uc.set_bibliography_authors,
                list_authors=uc.list_authors,
                add_item=uc.add_item,
                remove_item=uc.remove_item,
                delete_bibliography=uc.delete_bibliography,
            )
            tabs.addTab(catalog, "Catalog")
            views.append(catalog)

            members = MemberView(uc.list_members, uc.create_member, uc.edit_member, uc.generate_member_id)
            tabs.addTab(members, "Members")
            views.append(members)

            checkout = CheckoutView(
                uc.search_catalog, uc.list_members, uc.checkout_item, uc.list_open_loans, uc.return_item
            )
            tabs.addTab(checkout, "Checkout / Return")
            views.append(checkout)
        else:
            catalog = CatalogView(uc.search_catalog)
            tabs.addTab(catalog, "Catalog")
            views.append(catalog)

            my_loans = MyLoansView(uc.list_member_loans, member.id)
            tabs.addTab(my_loans, "My Loans")
            views.append(my_loans)

        # Each tab's own view already refreshes itself on construction; this catches it
        # back up on every subsequent switch, since actions in one tab (e.g. adding a
        # bibliography in Catalog) don't otherwise reach the other tabs' cached state
        # (e.g. Checkout's bibliography dropdown). Dispatched via `views` (built in the
        # same order as the tabs above) rather than tabs.widget(index), since QTabWidget
        # only knows its children as plain QWidget and has no notion of "refreshable".
        tabs.currentChanged.connect(lambda index: views[index].refresh())

        return tabs
