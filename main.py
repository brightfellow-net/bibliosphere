"""Composition root: wires SQLite repositories into use cases and starts the GUI."""

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from bibliosphere.application.container import UseCases
from bibliosphere.application.use_cases.add_bibliography import AddBibliography
from bibliosphere.application.use_cases.add_item import AddItem
from bibliosphere.application.use_cases.authenticate_user import AuthenticateUser
from bibliosphere.application.use_cases.checkout_item import CheckoutItem
from bibliosphere.application.use_cases.create_member import CreateMember
from bibliosphere.application.use_cases.delete_bibliography import DeleteBibliography
from bibliosphere.application.use_cases.edit_bibliography import EditBibliography
from bibliosphere.application.use_cases.edit_member import EditMember
from bibliosphere.application.use_cases.generate_member_id import GenerateMemberId
from bibliosphere.application.use_cases.list_authors import ListAuthors
from bibliosphere.application.use_cases.list_loan_history import ListLoanHistory
from bibliosphere.application.use_cases.list_member_loans import ListMemberLoans
from bibliosphere.application.use_cases.list_members import ListMembers
from bibliosphere.application.use_cases.list_open_loans import ListOpenLoans
from bibliosphere.application.use_cases.remove_item import RemoveItem
from bibliosphere.application.use_cases.return_item import ReturnItem
from bibliosphere.application.use_cases.search_catalog import SearchCatalog
from bibliosphere.application.use_cases.set_bibliography_authors import SetBibliographyAuthors
from bibliosphere.infrastructure.sqlite.author_repository import SqliteAuthorRepository
from bibliosphere.infrastructure.sqlite.bibliography_repository import SqliteBibliographyRepository
from bibliosphere.infrastructure.sqlite.connection import connect, init_schema
from bibliosphere.infrastructure.sqlite.loan_repository import SqliteLoanRepository
from bibliosphere.infrastructure.sqlite.member_repository import SqliteMemberRepository
from bibliosphere.infrastructure.sqlite.unit_of_work import SqliteUnitOfWork
from bibliosphere.presentation.qt.main_window import MainWindow

DB_PATH = Path(__file__).parent / "data" / "bibliosphere.db"


def build_use_cases(db_path: Path) -> UseCases:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = connect(db_path)
    init_schema(connection)

    bibliographies = SqliteBibliographyRepository(connection)
    authors = SqliteAuthorRepository(connection)
    members = SqliteMemberRepository(connection)
    loans = SqliteLoanRepository(connection)
    bibliography_uow = SqliteUnitOfWork(connection)

    return UseCases(
        authenticate_user=AuthenticateUser(members),
        search_catalog=SearchCatalog(bibliographies, loans),
        add_bibliography=AddBibliography(bibliographies, authors, bibliography_uow),
        edit_bibliography=EditBibliography(bibliographies, authors, bibliography_uow),
        delete_bibliography=DeleteBibliography(bibliographies),
        set_bibliography_authors=SetBibliographyAuthors(bibliographies, authors, bibliography_uow),
        list_authors=ListAuthors(authors),
        add_item=AddItem(bibliographies),
        remove_item=RemoveItem(bibliographies, loans),
        list_members=ListMembers(members),
        generate_member_id=GenerateMemberId(members),
        create_member=CreateMember(members),
        edit_member=EditMember(members),
        checkout_item=CheckoutItem(bibliographies, members, loans),
        return_item=ReturnItem(loans),
        list_member_loans=ListMemberLoans(members, loans, bibliographies),
        list_open_loans=ListOpenLoans(loans, bibliographies, members),
        list_loan_history=ListLoanHistory(loans, bibliographies, members),
    )


def main() -> int:
    app = QApplication(sys.argv)
    use_cases = build_use_cases(DB_PATH)
    window = MainWindow(use_cases)
    window.showMaximized()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
