from datetime import date, timedelta

import pytest

from bibliosphere.application.use_cases.add_bibliography import AddBibliography
from bibliosphere.application.use_cases.edit_bibliography import EditBibliography
from bibliosphere.domain.entities import Author, Bibliography, BibliographyAuthor, Loan, Member, Role
from bibliosphere.infrastructure.sqlite.author_repository import SqliteAuthorRepository
from bibliosphere.infrastructure.sqlite.bibliography_repository import SqliteBibliographyRepository
from bibliosphere.infrastructure.sqlite.connection import connect, init_schema
from bibliosphere.infrastructure.sqlite.loan_repository import SqliteLoanRepository
from bibliosphere.infrastructure.sqlite.member_repository import SqliteMemberRepository
from bibliosphere.infrastructure.sqlite.unit_of_work import SqliteUnitOfWork


class _FailingAuthorRepository:
    """Always fails author lookup, to force a mid-transaction error in tests."""

    def find_or_create_by_name(self, name: str) -> Author:
        raise RuntimeError("simulated author-lookup failure")


@pytest.fixture
def conn():
    connection = connect(":memory:")
    init_schema(connection)
    yield connection
    connection.close()


def test_bibliography_repository_round_trip(conn):
    repo = SqliteBibliographyRepository(conn)
    authors = SqliteAuthorRepository(conn)
    added = repo.add(Bibliography(id=None, title="Dune", isbn_issn="123", call_number="813.54 HER"))

    assert repo.get_by_id(added.id) == added
    assert repo.get_by_isbn("123") == added
    assert repo.get_by_call_number("813.54 HER") == added
    assert repo.search("Dune") == [added]

    herbert = authors.add(Author(id=None, name="Herbert"))
    anderson = authors.add(Author(id=None, name="Anderson"))
    repo.set_authors(added.id, [herbert.id, anderson.id])
    assert repo.list_authors(added.id) == [
        BibliographyAuthor(author=herbert, level=1),
        BibliographyAuthor(author=anderson, level=2),
    ]
    assert repo.search("Herbert") == [added]

    item = repo.add_item(added.id)
    assert repo.list_items(added.id) == [item]
    repo.remove_item(item.id)
    assert repo.get_item(item.id) is None


def test_search_escapes_like_wildcards_in_query(conn):
    repo = SqliteBibliographyRepository(conn)
    dune = repo.add(Bibliography(id=None, title="Dune", isbn_issn="123", call_number="CN-1"))
    wolf = repo.add(Bibliography(id=None, title="100% Wolf", isbn_issn="456", call_number="CN-2"))

    # A literal '_' shouldn't match every row via LIKE's single-character wildcard.
    assert repo.search("_") == []
    # A literal '%' should still match its literal occurrence, not act as a wildcard.
    assert repo.search("100%") == [wolf]
    assert repo.search("Dune") == [dune]


def test_uow_rolls_back_all_writes_on_failure(conn):
    repo = SqliteBibliographyRepository(conn)
    uow = SqliteUnitOfWork(conn)

    with pytest.raises(RuntimeError):
        with uow:
            repo.add(Bibliography(id=None, title="Ghost", call_number="CN-GHOST"))
            raise RuntimeError("simulated failure mid-transaction")

    assert repo.list_all() == []


def test_add_bibliography_rolls_back_on_author_failure(conn):
    bibliographies = SqliteBibliographyRepository(conn)
    uow = SqliteUnitOfWork(conn)
    use_case = AddBibliography(bibliographies, _FailingAuthorRepository(), uow)

    with pytest.raises(RuntimeError):
        use_case.execute(title="Ghost", authors=["Someone"], call_number="CN-GHOST")

    # The bibliography insert that happened before the failure must not have leaked.
    assert bibliographies.list_all() == []


def test_edit_bibliography_rolls_back_partial_update_on_failure(conn):
    bibliographies = SqliteBibliographyRepository(conn)
    authors = SqliteAuthorRepository(conn)
    uow = SqliteUnitOfWork(conn)

    added = AddBibliography(bibliographies, authors, uow).execute(
        title="Original", authors=["Real Author"], call_number="CN-ORIGINAL", isbn_issn="111"
    )

    edit_use_case = EditBibliography(bibliographies, _FailingAuthorRepository(), uow)
    with pytest.raises(RuntimeError):
        edit_use_case.execute(added.id, title="Edited Title", authors=["X"], call_number="CN-ORIGINAL", isbn_issn="111")

    # The title UPDATE that happened before the failure must not have leaked either.
    reloaded = bibliographies.get_by_id(added.id)
    assert reloaded.title == "Original"
    assert [c.author.name for c in bibliographies.list_authors(added.id)] == ["Real Author"]


def test_member_repository_round_trip(conn):
    repo = SqliteMemberRepository(conn)
    added = repo.add(
        Member(id="M0001", username="alice", name="Alice", role=Role.PATRON, password_hash="h", password_salt="s")
    )

    assert repo.get_by_id(added.id) == added
    assert repo.get_by_username("alice") == added


def test_member_repository_round_trip_with_optional_fields(conn):
    repo = SqliteMemberRepository(conn)
    added = repo.add(
        Member(
            id="M0002",
            username="bob",
            name="Bob",
            role=Role.PATRON,
            password_hash="h",
            password_salt="s",
            birthdate=date(1990, 1, 1),
            email="bob@example.com",
            phone="555-1234",
            join_date=date.today(),
            expiry_date=date(2027, 1, 1),
            address="123 Main St",
        )
    )

    assert repo.get_by_id(added.id) == added


def test_loan_repository_open_loan_tracking(conn):
    bibliographies = SqliteBibliographyRepository(conn)
    members = SqliteMemberRepository(conn)
    loans = SqliteLoanRepository(conn)

    bibliography = bibliographies.add(Bibliography(id=None, title="Dune", isbn_issn="123", call_number="813.54 HER"))
    item = bibliographies.add_item(bibliography.id)
    member = members.add(
        Member(id="M0001", username="alice", name="Alice", role=Role.PATRON, password_hash="h", password_salt="s")
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
