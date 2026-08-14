from datetime import date, timedelta

import pytest

from bibliosphere.domain.entities import Author, Bibliography, Loan, Member, Role
from bibliosphere.infrastructure.sqlite.author_repository import SqliteAuthorRepository
from bibliosphere.infrastructure.sqlite.bibliography_repository import SqliteBibliographyRepository
from bibliosphere.infrastructure.sqlite.connection import connect, init_schema
from bibliosphere.infrastructure.sqlite.loan_repository import SqliteLoanRepository
from bibliosphere.infrastructure.sqlite.member_repository import SqliteMemberRepository


@pytest.fixture
def conn():
    connection = connect(":memory:")
    init_schema(connection)
    yield connection
    connection.close()


def test_bibliography_repository_round_trip(conn):
    repo = SqliteBibliographyRepository(conn)
    authors = SqliteAuthorRepository(conn)
    added = repo.add(Bibliography(id=None, title="Dune", isbn_issn="123"))

    assert repo.get_by_id(added.id) == added
    assert repo.get_by_isbn("123") == added
    assert repo.search("Dune") == [added]

    herbert = authors.add(Author(id=None, name="Herbert"))
    repo.set_authors(added.id, [herbert.id])
    assert repo.list_authors(added.id) == [herbert]
    assert repo.search("Herbert") == [added]

    item = repo.add_item(added.id)
    assert repo.list_items(added.id) == [item]
    repo.remove_item(item.id)
    assert repo.get_item(item.id) is None


def test_member_repository_round_trip(conn):
    repo = SqliteMemberRepository(conn)
    added = repo.add(
        Member(id=None, username="alice", name="Alice", role=Role.PATRON, password_hash="h", password_salt="s")
    )

    assert repo.get_by_id(added.id) == added
    assert repo.get_by_username("alice") == added


def test_loan_repository_open_loan_tracking(conn):
    bibliographies = SqliteBibliographyRepository(conn)
    members = SqliteMemberRepository(conn)
    loans = SqliteLoanRepository(conn)

    bibliography = bibliographies.add(Bibliography(id=None, title="Dune", isbn_issn="123"))
    item = bibliographies.add_item(bibliography.id)
    member = members.add(
        Member(id=None, username="alice", name="Alice", role=Role.PATRON, password_hash="h", password_salt="s")
    )

    today = date.today()
    loan = loans.add(
        Loan(id=None, item_id=item.id, member_id=member.id, checkout_date=today, due_date=today + timedelta(days=14))
    )

    assert loans.get_open_loan_for_item(item.id) == loan
    assert loans.count_open_loans_for_member(member.id) == 1

    loan.return_date = today
    loans.update(loan)

    assert loans.get_open_loan_for_item(item.id) is None
    assert loans.count_open_loans_for_member(member.id) == 0
