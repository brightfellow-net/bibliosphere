from datetime import date, timedelta

import pytest

from bibliosphere.application.use_cases.add_bibliography import AddBibliography
from bibliosphere.application.use_cases.checkout_item import CheckoutItem
from bibliosphere.application.use_cases.create_member import CreateMember
from bibliosphere.application.use_cases.edit_bibliography import EditBibliography
from bibliosphere.application.use_cases.remove_item import RemoveItem
from bibliosphere.application.use_cases.return_item import ReturnItem
from bibliosphere.domain.entities import Author, Bibliography, BibliographyAuthor, Loan, Member, Role
from bibliosphere.domain.exceptions import ItemHasLoanHistory
from bibliosphere.domain.ports import CatalogFilters, LoanHistoryFilters
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


def _page(
    repo: SqliteBibliographyRepository,
    filters: CatalogFilters,
    *,
    sort_column: str = "title",
    sort_descending: bool = False,
    page: int = 1,
    page_size: int = 200,
) -> list[Bibliography]:
    return repo.list_page(
        filters, sort_column=sort_column, sort_descending=sort_descending, page=page, page_size=page_size
    )


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
    assert repo.count(CatalogFilters(title="Dune")) == 1
    assert _page(repo, CatalogFilters(title="Dune")) == [added]

    herbert = authors.add(Author(id=None, name="Herbert"))
    anderson = authors.add(Author(id=None, name="Anderson"))
    repo.set_authors(added.id, [herbert.id, anderson.id])
    assert repo.list_authors(added.id) == [
        BibliographyAuthor(author=herbert, level=1),
        BibliographyAuthor(author=anderson, level=2),
    ]
    assert _page(repo, CatalogFilters(author="Herbert")) == [added]

    item = repo.add_item(added.id)
    assert repo.list_items(added.id) == [item]
    repo.remove_item(item.id)
    assert repo.get_item(item.id) is None


def test_bibliography_repository_remove_clears_author_links(conn):
    repo = SqliteBibliographyRepository(conn)
    authors = SqliteAuthorRepository(conn)
    added = repo.add(Bibliography(id=None, title="Dune", isbn_issn="123", call_number="813.54 HER"))
    herbert = authors.add(Author(id=None, name="Herbert"))
    repo.set_authors(added.id, [herbert.id])

    repo.remove(added.id)

    assert repo.get_by_id(added.id) is None
    assert repo.list_authors(added.id) == []


def test_catalog_paginates_and_sorts(conn):
    repo = SqliteBibliographyRepository(conn)
    repo.add(Bibliography(id=None, title="Charlie", call_number="CN-3"))
    repo.add(Bibliography(id=None, title="Alpha", call_number="CN-1"))
    repo.add(Bibliography(id=None, title="Bravo", call_number="CN-2"))

    assert repo.count(CatalogFilters()) == 3
    page1 = _page(repo, CatalogFilters(), sort_column="title", page=1, page_size=2)
    page2 = _page(repo, CatalogFilters(), sort_column="title", page=2, page_size=2)
    assert [b.title for b in page1] == ["Alpha", "Bravo"]
    assert [b.title for b in page2] == ["Charlie"]

    descending = _page(repo, CatalogFilters(), sort_column="call_number", sort_descending=True, page=1, page_size=200)
    assert [b.call_number for b in descending] == ["CN-3", "CN-2", "CN-1"]


def test_catalog_filter_escapes_like_wildcards_and_is_prefix_only(conn):
    repo = SqliteBibliographyRepository(conn)
    dune = repo.add(Bibliography(id=None, title="Dune", isbn_issn="123", call_number="CN-1"))
    wolf = repo.add(Bibliography(id=None, title="100% Wolf", isbn_issn="456", call_number="CN-2"))

    # A literal '_' shouldn't match every row via LIKE's single-character wildcard.
    assert _page(repo, CatalogFilters(title="_")) == []
    # A literal '%' should still match its literal occurrence, not act as a wildcard.
    assert _page(repo, CatalogFilters(title="100%")) == [wolf]
    assert _page(repo, CatalogFilters(title="Dune")) == [dune]
    # Prefix-only: a mid-string needle must not match, unlike the old substring search.
    assert _page(repo, CatalogFilters(title="une")) == []


def test_catalog_list_page_rejects_unsortable_column(conn):
    repo = SqliteBibliographyRepository(conn)
    with pytest.raises(ValueError):
        _page(repo, CatalogFilters(), sort_column="author")


def test_uow_rolls_back_all_writes_on_failure(conn):
    repo = SqliteBibliographyRepository(conn)
    uow = SqliteUnitOfWork(conn)

    with pytest.raises(RuntimeError):
        with uow:
            repo.add(Bibliography(id=None, title="Ghost", call_number="CN-GHOST"))
            raise RuntimeError("simulated failure mid-transaction")

    assert repo.count(CatalogFilters()) == 0


def test_add_bibliography_rolls_back_on_author_failure(conn):
    bibliographies = SqliteBibliographyRepository(conn)
    uow = SqliteUnitOfWork(conn)
    use_case = AddBibliography(bibliographies, _FailingAuthorRepository(), uow)

    with pytest.raises(RuntimeError):
        use_case.execute(title="Ghost", authors=["Someone"], call_number="CN-GHOST")

    # The bibliography insert that happened before the failure must not have leaked.
    assert bibliographies.count(CatalogFilters()) == 0


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


def test_member_repository_allows_multiple_patrons_with_no_username(conn):
    # A UNIQUE column would otherwise reject a second NULL username.
    repo = SqliteMemberRepository(conn)
    m1 = repo.add(Member(id="M0003", username=None, name="Carol", role=Role.PATRON, password_hash=None, password_salt=None))
    m2 = repo.add(Member(id="M0004", username=None, name="Dave", role=Role.PATRON, password_hash=None, password_salt=None))

    assert repo.get_by_id(m1.id).username is None
    assert repo.get_by_id(m2.id).username is None
    assert repo.get_by_username("") is None


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


def test_loan_repository_history_includes_open_and_returned(conn):
    bibliographies = SqliteBibliographyRepository(conn)
    members = SqliteMemberRepository(conn)
    loans = SqliteLoanRepository(conn)

    bibliography = bibliographies.add(Bibliography(id=None, title="Dune", isbn_issn="123", call_number="813.54 HER"))
    item1 = bibliographies.add_item(bibliography.id)
    item2 = bibliographies.add_item(bibliography.id)
    member = members.add(
        Member(id="M0001", username="alice", name="Alice", role=Role.PATRON, password_hash="h", password_salt="s")
    )

    today = date.today()
    open_loan = loans.add(
        Loan(id=None, item_id=item1.id, member_id=member.id, checkout_date=today, due_date=today + timedelta(days=14))
    )
    returned_loan = loans.add(
        Loan(id=None, item_id=item2.id, member_id=member.id, checkout_date=today, due_date=today + timedelta(days=14))
    )
    returned_loan.return_date = today
    loans.update(returned_loan)

    filters = LoanHistoryFilters()
    assert loans.count_history(filters) == 2
    all_loans = loans.list_history_page(filters, page=1, page_size=200)

    assert {loan.id for loan in all_loans} == {open_loan.id, returned_loan.id}
    assert {loan.id: loan.is_open for loan in all_loans} == {open_loan.id: True, returned_loan.id: False}


def test_loan_repository_history_paginates_in_checkout_date_order(conn):
    bibliographies = SqliteBibliographyRepository(conn)
    members = SqliteMemberRepository(conn)
    loans = SqliteLoanRepository(conn)

    bibliography = bibliographies.add(Bibliography(id=None, title="Dune", isbn_issn="123", call_number="813.54 HER"))
    member = members.add(
        Member(id="M0001", username="alice", name="Alice", role=Role.PATRON, password_hash="h", password_salt="s")
    )

    today = date.today()
    created_ids = []
    for offset in range(5):
        item = bibliographies.add_item(bibliography.id)
        loan = loans.add(
            Loan(
                id=None,
                item_id=item.id,
                member_id=member.id,
                checkout_date=today - timedelta(days=offset),
                due_date=today + timedelta(days=14 - offset),
            )
        )
        created_ids.append(loan.id)

    filters = LoanHistoryFilters()
    assert loans.count_history(filters) == 5

    page1 = loans.list_history_page(filters, page=1, page_size=2)
    page2 = loans.list_history_page(filters, page=2, page_size=2)
    page3 = loans.list_history_page(filters, page=3, page_size=2)

    # Most recent checkout_date first — created_ids[0] has today's date, the rest older.
    assert [loan.id for loan in page1] == created_ids[0:2]
    assert [loan.id for loan in page2] == created_ids[2:4]
    assert [loan.id for loan in page3] == created_ids[4:5]


def test_loan_repository_history_filters_by_member_name_and_title(conn):
    bibliographies = SqliteBibliographyRepository(conn)
    members = SqliteMemberRepository(conn)
    loans = SqliteLoanRepository(conn)

    dune = bibliographies.add(Bibliography(id=None, title="Dune", isbn_issn="123", call_number="813.54 HER"))
    hobbit = bibliographies.add(Bibliography(id=None, title="The Hobbit", isbn_issn="456", call_number="823 TOL"))
    dune_item = bibliographies.add_item(dune.id)
    hobbit_item = bibliographies.add_item(hobbit.id)
    alice = members.add(
        Member(id="M0001", username="alice", name="Alice", role=Role.PATRON, password_hash="h", password_salt="s")
    )
    bob = members.add(
        Member(id="M0002", username="bob", name="Bob", role=Role.PATRON, password_hash="h", password_salt="s")
    )

    today = date.today()
    loans.add(Loan(id=None, item_id=dune_item.id, member_id=alice.id, checkout_date=today, due_date=today))
    loans.add(Loan(id=None, item_id=hobbit_item.id, member_id=bob.id, checkout_date=today, due_date=today))

    by_title = loans.list_history_page(LoanHistoryFilters(title="hobbit"), page=1, page_size=200)
    assert [loan.item_id for loan in by_title] == [hobbit_item.id]

    by_member = loans.list_history_page(LoanHistoryFilters(member_name="ali"), page=1, page_size=200)
    assert [loan.member_id for loan in by_member] == [alice.id]

    by_status_returned = loans.list_history_page(LoanHistoryFilters(status="returned"), page=1, page_size=200)
    assert by_status_returned == []

    by_status_open = loans.list_history_page(LoanHistoryFilters(status="checked"), page=1, page_size=200)
    assert len(by_status_open) == 2


def test_loan_repository_history_shows_unknown_for_deleted_item(conn):
    bibliographies = SqliteBibliographyRepository(conn)
    members = SqliteMemberRepository(conn)
    loans = SqliteLoanRepository(conn)

    bibliography = bibliographies.add(Bibliography(id=None, title="Dune", isbn_issn="123", call_number="813.54 HER"))
    item = bibliographies.add_item(bibliography.id)
    member = members.add(
        Member(id="M0001", username="alice", name="Alice", role=Role.PATRON, password_hash="h", password_salt="s")
    )
    today = date.today()
    loan = loans.add(Loan(id=None, item_id=item.id, member_id=member.id, checkout_date=today, due_date=today))
    loan.return_date = today
    loans.update(loan)

    # RemoveItem itself refuses to produce this state (see ItemHasLoanHistory /
    # test_remove_item_with_returned_loan_history_raises), but a legacy-data import
    # could plausibly leave orphaned references, so simulate one directly.
    conn.execute("PRAGMA foreign_keys = OFF")
    conn.execute("DELETE FROM items WHERE id = ?", (item.id,))
    conn.commit()

    # A loan whose item was later removed must still appear in history (LEFT JOIN),
    # matching ListLoanHistory's "Unknown" fallback rather than disappearing silently.
    filters = LoanHistoryFilters()
    assert loans.count_history(filters) == 1
    result = loans.list_history_page(filters, page=1, page_size=200)
    assert [loan_.id for loan_ in result] == [loan.id]

    by_title = loans.list_history_page(LoanHistoryFilters(title="unknown"), page=1, page_size=200)
    assert [loan_.id for loan_ in by_title] == [loan.id]


def test_remove_item_with_returned_loan_raises_cleanly_not_integrity_error(conn):
    """Regression test: loans.item_id is a NOT NULL, enforced FK (PRAGMA foreign_keys
    = ON in connect()), so deleting an item with any loan history — even returned —
    used to bubble up as an unhandled sqlite3.IntegrityError. RemoveItem must catch
    this itself and raise ItemHasLoanHistory before ever reaching the DELETE.
    """
    bibliographies = SqliteBibliographyRepository(conn)
    members = SqliteMemberRepository(conn)
    loans = SqliteLoanRepository(conn)

    bibliography = bibliographies.add(Bibliography(id=None, title="Dune", isbn_issn="123", call_number="813.54 HER"))
    item = bibliographies.add_item(bibliography.id)
    member = members.add(
        Member(id="M0001", username="alice", name="Alice", role=Role.PATRON, password_hash="h", password_salt="s")
    )
    loan = CheckoutItem(bibliographies, members, loans).execute(bibliography.id, member.id)
    ReturnItem(loans).execute(loan.id)

    with pytest.raises(ItemHasLoanHistory):
        RemoveItem(bibliographies, loans).execute(item.id)
    assert bibliographies.get_item(item.id) is not None


def test_loan_repository_history_filters_by_checkout_date_range(conn):
    bibliographies = SqliteBibliographyRepository(conn)
    members = SqliteMemberRepository(conn)
    loans = SqliteLoanRepository(conn)

    bibliography = bibliographies.add(Bibliography(id=None, title="Dune", isbn_issn="123", call_number="813.54 HER"))
    member = members.add(
        Member(id="M0001", username="alice", name="Alice", role=Role.PATRON, password_hash="h", password_salt="s")
    )

    dates = [date(2026, 1, 1), date(2026, 1, 10), date(2026, 1, 20), date(2026, 2, 1)]
    ids_by_date = {}
    for checkout_date in dates:
        item = bibliographies.add_item(bibliography.id)
        loan = loans.add(
            Loan(id=None, item_id=item.id, member_id=member.id, checkout_date=checkout_date, due_date=checkout_date)
        )
        ids_by_date[checkout_date] = loan.id

    # Inclusive on both ends.
    in_range = loans.list_history_page(
        LoanHistoryFilters(checkout_date_from=date(2026, 1, 5), checkout_date_to=date(2026, 1, 20)),
        page=1,
        page_size=200,
    )
    assert {loan.id for loan in in_range} == {ids_by_date[date(2026, 1, 10)], ids_by_date[date(2026, 1, 20)]}

    from_only = loans.list_history_page(
        LoanHistoryFilters(checkout_date_from=date(2026, 1, 20)), page=1, page_size=200
    )
    assert {loan.id for loan in from_only} == {ids_by_date[date(2026, 1, 20)], ids_by_date[date(2026, 2, 1)]}

    to_only = loans.list_history_page(LoanHistoryFilters(checkout_date_to=date(2026, 1, 1)), page=1, page_size=200)
    assert {loan.id for loan in to_only} == {ids_by_date[date(2026, 1, 1)]}
