from datetime import date, timedelta
from itertools import count

import pytest

from bibliosphere.application.config import LOAN_PERIOD_DAYS, MAX_LOANS_PER_MEMBER
from bibliosphere.application.use_cases.add_bibliography import AddBibliography
from bibliosphere.application.use_cases.add_item import AddItem
from bibliosphere.application.use_cases.checkout_item import CheckoutItem
from bibliosphere.application.use_cases.create_member import CreateMember
from bibliosphere.application.use_cases.list_member_loans import ListMemberLoans
from bibliosphere.application.use_cases.return_item import ReturnItem
from bibliosphere.domain.entities import Role
from bibliosphere.domain.exceptions import ItemNotAvailable, LoanAlreadyReturned, LoanLimitExceeded


_isbn_counter = count(1)


def _make_bibliography_with_items(bibliography_repo, author_repo, unit_of_work, n_items=1):
    isbn = f"isbn-{next(_isbn_counter)}"
    bibliography = AddBibliography(bibliography_repo, author_repo, unit_of_work).execute(
        isbn_issn=isbn, title="Dune", authors=["Herbert"]
    )
    for _ in range(n_items):
        AddItem(bibliography_repo).execute(bibliography.id)
    return bibliography


def test_checkout_item_success(bibliography_repo, author_repo, unit_of_work, member_repo, loan_repo):
    bibliography = _make_bibliography_with_items(bibliography_repo, author_repo, unit_of_work)
    member = CreateMember(member_repo).execute("alice", "Alice", "pw", Role.PATRON)

    loan = CheckoutItem(bibliography_repo, member_repo, loan_repo).execute(bibliography.id, member.id)

    assert loan.due_date == date.today() + timedelta(days=LOAN_PERIOD_DAYS)
    assert loan.is_open


def test_checkout_item_raises_when_none_available(bibliography_repo, author_repo, unit_of_work, member_repo, loan_repo):
    bibliography = _make_bibliography_with_items(bibliography_repo, author_repo, unit_of_work, n_items=1)
    member = CreateMember(member_repo).execute("alice", "Alice", "pw", Role.PATRON)
    other = CreateMember(member_repo).execute("bob", "Bob", "pw", Role.PATRON)

    CheckoutItem(bibliography_repo, member_repo, loan_repo).execute(bibliography.id, member.id)

    with pytest.raises(ItemNotAvailable):
        CheckoutItem(bibliography_repo, member_repo, loan_repo).execute(bibliography.id, other.id)


def test_checkout_item_enforces_loan_limit(bibliography_repo, author_repo, unit_of_work, member_repo, loan_repo):
    member = CreateMember(member_repo).execute("alice", "Alice", "pw", Role.PATRON)
    checkout = CheckoutItem(bibliography_repo, member_repo, loan_repo)

    for _ in range(MAX_LOANS_PER_MEMBER):
        bibliography = _make_bibliography_with_items(bibliography_repo, author_repo, unit_of_work)
        checkout.execute(bibliography.id, member.id)

    bibliography = _make_bibliography_with_items(bibliography_repo, author_repo, unit_of_work)
    with pytest.raises(LoanLimitExceeded):
        checkout.execute(bibliography.id, member.id)


def test_return_item_frees_it_for_checkout(bibliography_repo, author_repo, unit_of_work, member_repo, loan_repo):
    bibliography = _make_bibliography_with_items(bibliography_repo, author_repo, unit_of_work, n_items=1)
    member = CreateMember(member_repo).execute("alice", "Alice", "pw", Role.PATRON)
    other = CreateMember(member_repo).execute("bob", "Bob", "pw", Role.PATRON)

    checkout = CheckoutItem(bibliography_repo, member_repo, loan_repo)
    loan = checkout.execute(bibliography.id, member.id)

    ReturnItem(loan_repo).execute(loan.id)

    second_loan = checkout.execute(bibliography.id, other.id)
    assert second_loan.item_id == loan.item_id


def test_return_item_rejects_already_returned_loan(bibliography_repo, author_repo, unit_of_work, member_repo, loan_repo):
    bibliography = _make_bibliography_with_items(bibliography_repo, author_repo, unit_of_work, n_items=1)
    member = CreateMember(member_repo).execute("alice", "Alice", "pw", Role.PATRON)

    checkout = CheckoutItem(bibliography_repo, member_repo, loan_repo)
    loan = checkout.execute(bibliography.id, member.id)

    first_return = ReturnItem(loan_repo).execute(loan.id)
    with pytest.raises(LoanAlreadyReturned):
        ReturnItem(loan_repo).execute(loan.id)

    # The original return_date must survive the rejected second call, not get overwritten.
    assert loan_repo.get_by_id(loan.id).return_date == first_return.return_date


def test_list_member_loans_only_open(bibliography_repo, author_repo, unit_of_work, member_repo, loan_repo):
    bibliography = _make_bibliography_with_items(bibliography_repo, author_repo, unit_of_work, n_items=2)
    member = CreateMember(member_repo).execute("alice", "Alice", "pw", Role.PATRON)
    checkout = CheckoutItem(bibliography_repo, member_repo, loan_repo)

    first_loan = checkout.execute(bibliography.id, member.id)
    checkout.execute(bibliography.id, member.id)
    ReturnItem(loan_repo).execute(first_loan.id)

    open_loans = ListMemberLoans(member_repo, loan_repo, bibliography_repo).execute(member.id)
    assert len(open_loans) == 1
    assert open_loans[0].loan.id != first_loan.id
    assert open_loans[0].bibliography_title == bibliography.title
    assert open_loans[0].member_name == "Alice"
