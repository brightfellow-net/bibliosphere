from datetime import date, timedelta
from itertools import count

from bibliosphere.application.use_cases.add_bibliography import AddBibliography
from bibliosphere.application.use_cases.add_item import AddItem
from bibliosphere.application.use_cases.checkout_item import CheckoutItem
from bibliosphere.application.use_cases.create_member import CreateMember
from bibliosphere.application.use_cases.list_members import ListMembers
from bibliosphere.application.use_cases.list_open_loans import ListOpenLoans
from bibliosphere.domain.entities import Role

_isbn_counter = count(100)


def _make_bibliography_with_items(bibliography_repo, author_repo, n_items=1):
    isbn = f"isbn-{next(_isbn_counter)}"
    bibliography = AddBibliography(bibliography_repo, author_repo).execute(
        isbn_issn=isbn, title="Dune", authors=["Herbert"]
    )
    for _ in range(n_items):
        AddItem(bibliography_repo).execute(bibliography.id)
    return bibliography


def test_list_members(member_repo):
    CreateMember(member_repo).execute("alice", "Alice", "pw", Role.PATRON)
    CreateMember(member_repo).execute("bob", "Bob", "pw", Role.LIBRARIAN)

    members = ListMembers(member_repo).execute()
    assert {m.username for m in members} == {"alice", "bob"}


def test_list_open_loans_across_all_members(bibliography_repo, author_repo, member_repo, loan_repo):
    bibliography = _make_bibliography_with_items(bibliography_repo, author_repo, n_items=2)
    alice = CreateMember(member_repo).execute("alice", "Alice", "pw", Role.PATRON)
    bob = CreateMember(member_repo).execute("bob", "Bob", "pw", Role.PATRON)
    checkout = CheckoutItem(bibliography_repo, member_repo, loan_repo)

    checkout.execute(bibliography.id, alice.id)
    checkout.execute(bibliography.id, bob.id)

    views = ListOpenLoans(loan_repo, bibliography_repo, member_repo).execute()
    assert {view.member_name for view in views} == {"Alice", "Bob"}
    assert all(view.bibliography_title == "Dune" for view in views)
