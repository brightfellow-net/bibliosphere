from datetime import date, timedelta
from itertools import count

from bibliosphere.application.use_cases.add_bibliography import AddBibliography
from bibliosphere.application.use_cases.add_item import AddItem
from bibliosphere.application.use_cases.checkout_item import CheckoutItem
from bibliosphere.application.use_cases.create_member import CreateMember
from bibliosphere.application.use_cases.list_loan_history import ListLoanHistory
from bibliosphere.application.use_cases.list_members import ListMembers
from bibliosphere.application.use_cases.list_open_loans import ListOpenLoans
from bibliosphere.application.use_cases.return_item import ReturnItem
from bibliosphere.domain.entities import Loan, Role
from bibliosphere.domain.ports import LoanHistoryFilters

_isbn_counter = count(100)
_member_id_counter = count(100)


def _create_member(member_repo, username, name, password, role):
    return CreateMember(member_repo).execute(f"M{next(_member_id_counter):04d}", username, name, password, role)


def _make_bibliography_with_items(bibliography_repo, author_repo, unit_of_work, n_items=1):
    n = next(_isbn_counter)
    bibliography = AddBibliography(bibliography_repo, author_repo, unit_of_work).execute(
        isbn_issn=f"isbn-{n}", title="Dune", authors=["Herbert"], call_number=f"cn-{n}"
    )
    for _ in range(n_items):
        AddItem(bibliography_repo).execute(bibliography.id)
    return bibliography


def test_list_members(member_repo):
    _create_member(member_repo, "alice", "Alice", "pw", Role.PATRON)
    _create_member(member_repo, "bob", "Bob", "pw", Role.LIBRARIAN)

    members = ListMembers(member_repo).execute()
    assert {m.username for m in members} == {"alice", "bob"}


def test_list_open_loans_across_all_members(bibliography_repo, author_repo, unit_of_work, member_repo, loan_repo):
    bibliography = _make_bibliography_with_items(bibliography_repo, author_repo, unit_of_work, n_items=2)
    alice = _create_member(member_repo, "alice", "Alice", "pw", Role.PATRON)
    bob = _create_member(member_repo, "bob", "Bob", "pw", Role.PATRON)
    checkout = CheckoutItem(bibliography_repo, member_repo, loan_repo)

    checkout.execute(bibliography.id, alice.id)
    checkout.execute(bibliography.id, bob.id)

    views = ListOpenLoans(loan_repo, bibliography_repo, member_repo).execute()
    assert {view.member_name for view in views} == {"Alice", "Bob"}
    assert all(view.bibliography_title == "Dune" for view in views)


def test_loan_history_includes_open_and_returned_loans_for_all_members(
    bibliography_repo, author_repo, unit_of_work, member_repo, loan_repo
):
    bibliography = _make_bibliography_with_items(bibliography_repo, author_repo, unit_of_work, n_items=2)
    alice = _create_member(member_repo, "alice", "Alice", "pw", Role.PATRON)
    bob = _create_member(member_repo, "bob", "Bob", "pw", Role.PATRON)
    checkout = CheckoutItem(bibliography_repo, member_repo, loan_repo)

    alice_loan = checkout.execute(bibliography.id, alice.id)
    checkout.execute(bibliography.id, bob.id)
    ReturnItem(loan_repo).execute(alice_loan.id)

    result = ListLoanHistory(loan_repo, bibliography_repo, member_repo).execute(
        LoanHistoryFilters(), page=1, page_size=200
    )

    assert result.total_count == 2
    assert {view.member_name for view in result.views} == {"Alice", "Bob"}
    statuses = {view.member_name: view.loan.is_open for view in result.views}
    assert statuses == {"Alice": False, "Bob": True}


def test_loan_history_paginates_and_filters(bibliography_repo, author_repo, unit_of_work, member_repo, loan_repo):
    bibliography = _make_bibliography_with_items(bibliography_repo, author_repo, unit_of_work, n_items=5)
    alice = _create_member(member_repo, "alice", "Alice", "pw", Role.PATRON)
    checkout = CheckoutItem(bibliography_repo, member_repo, loan_repo)
    for _ in range(5):
        checkout.execute(bibliography.id, alice.id)

    history = ListLoanHistory(loan_repo, bibliography_repo, member_repo)

    page1 = history.execute(LoanHistoryFilters(), page=1, page_size=2)
    assert page1.total_count == 5
    assert page1.total_pages == 3
    assert len(page1.views) == 2

    page3 = history.execute(LoanHistoryFilters(), page=3, page_size=2)
    assert len(page3.views) == 1

    filtered = history.execute(LoanHistoryFilters(member_name="ali"), page=1, page_size=200)
    assert filtered.total_count == 5

    no_match = history.execute(LoanHistoryFilters(member_name="bob"), page=1, page_size=200)
    assert no_match.total_count == 0
    assert no_match.views == []


def test_loan_history_filters_by_checkout_date_range(bibliography_repo, author_repo, unit_of_work, member_repo, loan_repo):
    bibliography = _make_bibliography_with_items(bibliography_repo, author_repo, unit_of_work, n_items=3)
    alice = _create_member(member_repo, "alice", "Alice", "pw", Role.PATRON)
    items = bibliography_repo.list_items(bibliography.id)

    for item, checkout_date in zip(items, [date(2026, 1, 1), date(2026, 1, 15), date(2026, 2, 1)]):
        loan_repo.add(
            Loan(id=None, item_id=item.id, member_id=alice.id, checkout_date=checkout_date, due_date=checkout_date)
        )

    history = ListLoanHistory(loan_repo, bibliography_repo, member_repo)

    result = history.execute(
        LoanHistoryFilters(checkout_date_from=date(2026, 1, 10), checkout_date_to=date(2026, 1, 20)),
        page=1,
        page_size=200,
    )
    assert result.total_count == 1
    assert result.views[0].loan.checkout_date == date(2026, 1, 15)
