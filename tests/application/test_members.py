from datetime import date, timedelta

import pytest

from bibliosphere.application.use_cases.add_bibliography import AddBibliography
from bibliosphere.application.use_cases.authenticate_user import AuthenticateUser
from bibliosphere.application.use_cases.checkout_item import CheckoutItem
from bibliosphere.application.use_cases.create_member import CreateMember
from bibliosphere.application.use_cases.delete_member import DeleteMember
from bibliosphere.application.use_cases.edit_member import EditMember
from bibliosphere.application.use_cases.generate_member_id import GenerateMemberId
from bibliosphere.application.use_cases.return_item import ReturnItem
from bibliosphere.domain.entities import Role
from bibliosphere.domain.exceptions import (
    CannotDeleteLastLibrarian,
    DuplicateMemberId,
    DuplicateUsername,
    InvalidCredentials,
    InvalidMemberDetails,
    MemberHasLoanHistory,
    MemberNotFound,
)


def test_create_member_hashes_password(member_repo):
    member = CreateMember(member_repo).execute("M0001", "alice", "Alice", "hunter2", Role.PATRON)
    assert member.password_hash != "hunter2"
    assert member.password_salt


def test_create_member_defaults_optional_fields_to_none(member_repo):
    member = CreateMember(member_repo).execute("M0001", "alice", "Alice", "hunter2", Role.PATRON)
    assert member.birthdate is None
    assert member.email is None
    assert member.phone is None
    assert member.expiry_date is None
    assert member.address is None


def test_create_member_sets_join_date_to_today(member_repo):
    member = CreateMember(member_repo).execute("M0001", "alice", "Alice", "hunter2", Role.PATRON)
    assert member.join_date == date.today()


def test_create_member_stores_optional_fields(member_repo):
    member = CreateMember(member_repo).execute(
        "M0001",
        "alice",
        "Alice",
        "hunter2",
        Role.PATRON,
        birthdate=date(1990, 1, 1),
        email="alice@example.com",
        phone="555-1234",
        expiry_date=date(2027, 1, 1),
        address="123 Main St",
    )
    assert member.birthdate == date(1990, 1, 1)
    assert member.email == "alice@example.com"
    assert member.phone == "555-1234"
    assert member.expiry_date == date(2027, 1, 1)
    assert member.address == "123 Main St"


def test_create_member_rejects_duplicate_username(member_repo):
    CreateMember(member_repo).execute("M0001", "alice", "Alice", "pw1", Role.PATRON)
    with pytest.raises(DuplicateUsername):
        CreateMember(member_repo).execute("M0002", "alice", "Alice 2", "pw2", Role.LIBRARIAN)


def test_create_member_rejects_duplicate_member_id(member_repo):
    CreateMember(member_repo).execute("M0001", "alice", "Alice", "pw1", Role.PATRON)
    with pytest.raises(DuplicateMemberId):
        CreateMember(member_repo).execute("M0001", "bob", "Bob", "pw2", Role.PATRON)


def test_create_member_rejects_blank_password_for_librarian(member_repo):
    with pytest.raises(InvalidMemberDetails):
        CreateMember(member_repo).execute("M0001", "alice", "Alice", "", Role.LIBRARIAN)


def test_create_member_rejects_blank_member_id(member_repo):
    with pytest.raises(InvalidMemberDetails):
        CreateMember(member_repo).execute("  ", "alice", "Alice", "pw", Role.PATRON)


def test_create_member_rejects_blank_name(member_repo):
    with pytest.raises(InvalidMemberDetails):
        CreateMember(member_repo).execute("M0001", "alice", "  ", "pw", Role.PATRON)


def test_create_member_rejects_blank_username_for_librarian(member_repo):
    with pytest.raises(InvalidMemberDetails):
        CreateMember(member_repo).execute("M0001", "  ", "Alice", "pw", Role.LIBRARIAN)


def test_create_member_allows_blank_username_and_password_for_patron(member_repo):
    member = CreateMember(member_repo).execute("M0001", "  ", "Alice", "", Role.PATRON)
    assert member.username is None
    assert member.password_hash is None
    assert member.password_salt is None


def test_create_member_allows_a_second_patron_with_no_username(member_repo):
    # A UNIQUE column would otherwise reject a second NULL/blank username.
    CreateMember(member_repo).execute("M0001", "", "Alice", "", Role.PATRON)
    member2 = CreateMember(member_repo).execute("M0002", "", "Bob", "", Role.PATRON)
    assert member2.username is None


def test_authenticate_user_success(member_repo):
    CreateMember(member_repo).execute("M0001", "alice", "Alice", "hunter2", Role.PATRON)
    member = AuthenticateUser(member_repo).execute("alice", "hunter2")
    assert member.username == "alice"


def test_authenticate_user_wrong_password(member_repo):
    CreateMember(member_repo).execute("M0001", "alice", "Alice", "hunter2", Role.PATRON)
    with pytest.raises(InvalidCredentials):
        AuthenticateUser(member_repo).execute("alice", "wrong")


def test_authenticate_unknown_user(member_repo):
    with pytest.raises(InvalidCredentials):
        AuthenticateUser(member_repo).execute("nobody", "pw")


def test_edit_member(member_repo):
    member = CreateMember(member_repo).execute("M0001", "alice", "Alice", "pw", Role.PATRON)
    updated = EditMember(member_repo).execute(member.id, username="alice2", name="Alice B.", role=Role.PATRON)
    assert updated.username == "alice2"
    assert updated.name == "Alice B."
    assert updated.password_hash == member.password_hash


def test_edit_member_changes_role(member_repo):
    member = CreateMember(member_repo).execute("M0001", "alice", "Alice", "pw", Role.PATRON)
    updated = EditMember(member_repo).execute(member.id, username="alice", name="Alice", role=Role.LIBRARIAN)
    assert updated.role == Role.LIBRARIAN


def test_edit_member_resets_password_when_provided(member_repo):
    member = CreateMember(member_repo).execute("M0001", "alice", "Alice", "old-pw", Role.PATRON)
    EditMember(member_repo).execute(member.id, username="alice", name="Alice", role=Role.PATRON, password="new-pw")

    with pytest.raises(InvalidCredentials):
        AuthenticateUser(member_repo).execute("alice", "old-pw")
    assert AuthenticateUser(member_repo).execute("alice", "new-pw").username == "alice"


def test_edit_member_missing_raises(member_repo):
    with pytest.raises(MemberNotFound):
        EditMember(member_repo).execute("nonexistent", username="x", name="y", role=Role.PATRON)


def test_edit_member_rejects_blank_name(member_repo):
    member = CreateMember(member_repo).execute("M0001", "alice", "Alice", "pw", Role.PATRON)
    with pytest.raises(InvalidMemberDetails):
        EditMember(member_repo).execute(member.id, username="alice", name="  ", role=Role.PATRON)


def test_edit_member_rejects_blank_username_for_librarian(member_repo):
    member = CreateMember(member_repo).execute("M0001", "alice", "Alice", "pw", Role.LIBRARIAN)
    with pytest.raises(InvalidMemberDetails):
        EditMember(member_repo).execute(member.id, username="  ", name="Alice", role=Role.LIBRARIAN)


def test_edit_member_allows_blank_username_for_patron(member_repo):
    member = CreateMember(member_repo).execute("M0001", "alice", "Alice", "pw", Role.PATRON)
    updated = EditMember(member_repo).execute(member.id, username="  ", name="Alice", role=Role.PATRON)
    assert updated.username is None


def test_edit_member_rejects_changing_to_librarian_without_ever_setting_a_password(member_repo):
    member = CreateMember(member_repo).execute("M0001", "", "Alice", "", Role.PATRON)
    with pytest.raises(InvalidMemberDetails):
        EditMember(member_repo).execute(member.id, username="alice", name="Alice", role=Role.LIBRARIAN)
    # Providing a password alongside the role change should succeed.
    updated = EditMember(member_repo).execute(
        member.id, username="alice", name="Alice", role=Role.LIBRARIAN, password="pw"
    )
    assert updated.role == Role.LIBRARIAN
    assert updated.password_hash is not None


def test_edit_member_updates_optional_fields(member_repo):
    member = CreateMember(member_repo).execute("M0001", "alice", "Alice", "pw", Role.PATRON)
    updated = EditMember(member_repo).execute(
        member.id,
        username="alice",
        name="Alice",
        role=Role.PATRON,
        birthdate=date(1990, 1, 1),
        email="alice@example.com",
        phone="555-1234",
        expiry_date=date(2027, 1, 1),
        address="123 Main St",
    )
    assert updated.birthdate == date(1990, 1, 1)
    assert updated.email == "alice@example.com"
    assert updated.phone == "555-1234"
    assert updated.expiry_date == date(2027, 1, 1)
    assert updated.address == "123 Main St"


def test_edit_member_does_not_change_join_date(member_repo):
    member = CreateMember(member_repo).execute("M0001", "alice", "Alice", "pw", Role.PATRON)
    updated = EditMember(member_repo).execute(member.id, username="alice", name="Alice", role=Role.PATRON)
    assert updated.join_date == member.join_date


def test_generate_member_id_starts_at_one_for_the_day(member_repo):
    suggested = GenerateMemberId(member_repo).execute()
    today_prefix = date.today().strftime("%Y%m%d")
    assert suggested == f"{today_prefix}001"


def test_generate_member_id_increments_past_existing_members_today(member_repo):
    today_prefix = date.today().strftime("%Y%m%d")
    CreateMember(member_repo).execute(f"{today_prefix}001", "alice", "Alice", "pw", Role.PATRON)
    CreateMember(member_repo).execute(f"{today_prefix}002", "bob", "Bob", "pw", Role.PATRON)

    suggested = GenerateMemberId(member_repo).execute()
    assert suggested == f"{today_prefix}003"


def test_generate_member_id_resets_to_one_on_a_new_day(member_repo):
    yesterday_prefix = (date.today() - timedelta(days=1)).strftime("%Y%m%d")
    today_prefix = date.today().strftime("%Y%m%d")
    CreateMember(member_repo).execute(f"{yesterday_prefix}001", "alice", "Alice", "pw", Role.PATRON)
    CreateMember(member_repo).execute(f"{yesterday_prefix}047", "bob", "Bob", "pw", Role.PATRON)

    # Even though yesterday reached 047, today's sequence must start over at 1,
    # not continue from yesterday's count.
    suggested = GenerateMemberId(member_repo).execute()
    assert suggested == f"{today_prefix}001"


def test_delete_member(member_repo, loan_repo):
    member = CreateMember(member_repo).execute("M0001", "alice", "Alice", "pw", Role.PATRON)
    DeleteMember(member_repo, loan_repo).execute(member.id)
    assert member_repo.get_by_id(member.id) is None


def test_delete_member_missing_raises(member_repo, loan_repo):
    with pytest.raises(MemberNotFound):
        DeleteMember(member_repo, loan_repo).execute("nonexistent")


def test_delete_member_with_loan_history_raises(
    member_repo, loan_repo, bibliography_repo, author_repo, unit_of_work
):
    member = CreateMember(member_repo).execute("M0001", "alice", "Alice", "pw", Role.PATRON)
    bibliography = AddBibliography(bibliography_repo, author_repo, unit_of_work).execute(
        title="Dune", authors=["Herbert"], call_number="CN-1"
    )
    bibliography_repo.add_item(bibliography.id)
    loan = CheckoutItem(bibliography_repo, member_repo, loan_repo).execute(bibliography.id, member.id)
    ReturnItem(loan_repo).execute(loan.id)

    # Even though the loan is closed (returned), it must still block deletion —
    # loans.member_id is a NOT NULL FK, mirroring ItemHasLoanHistory for items.
    with pytest.raises(MemberHasLoanHistory):
        DeleteMember(member_repo, loan_repo).execute(member.id)
    assert member_repo.get_by_id(member.id) is not None


def test_delete_last_librarian_raises(member_repo, loan_repo):
    librarian = CreateMember(member_repo).execute("M0001", "alice", "Alice", "pw", Role.LIBRARIAN)
    with pytest.raises(CannotDeleteLastLibrarian):
        DeleteMember(member_repo, loan_repo).execute(librarian.id)
    assert member_repo.get_by_id(librarian.id) is not None


def test_delete_one_of_two_librarians_succeeds(member_repo, loan_repo):
    librarian1 = CreateMember(member_repo).execute("M0001", "alice", "Alice", "pw", Role.LIBRARIAN)
    CreateMember(member_repo).execute("M0002", "bob", "Bob", "pw", Role.LIBRARIAN)

    DeleteMember(member_repo, loan_repo).execute(librarian1.id)
    assert member_repo.get_by_id(librarian1.id) is None
