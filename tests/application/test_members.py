import pytest

from bibliosphere.application.use_cases.authenticate_user import AuthenticateUser
from bibliosphere.application.use_cases.create_member import CreateMember
from bibliosphere.application.use_cases.edit_member import EditMember
from bibliosphere.domain.entities import Role
from bibliosphere.domain.exceptions import DuplicateUsername, InvalidCredentials, MemberNotFound


def test_create_member_hashes_password(member_repo):
    member = CreateMember(member_repo).execute("alice", "Alice", "hunter2", Role.PATRON)
    assert member.password_hash != "hunter2"
    assert member.password_salt


def test_create_member_rejects_duplicate_username(member_repo):
    CreateMember(member_repo).execute("alice", "Alice", "pw1", Role.PATRON)
    with pytest.raises(DuplicateUsername):
        CreateMember(member_repo).execute("alice", "Alice 2", "pw2", Role.LIBRARIAN)


def test_authenticate_user_success(member_repo):
    CreateMember(member_repo).execute("alice", "Alice", "hunter2", Role.PATRON)
    member = AuthenticateUser(member_repo).execute("alice", "hunter2")
    assert member.username == "alice"


def test_authenticate_user_wrong_password(member_repo):
    CreateMember(member_repo).execute("alice", "Alice", "hunter2", Role.PATRON)
    with pytest.raises(InvalidCredentials):
        AuthenticateUser(member_repo).execute("alice", "wrong")


def test_authenticate_unknown_user(member_repo):
    with pytest.raises(InvalidCredentials):
        AuthenticateUser(member_repo).execute("nobody", "pw")


def test_edit_member(member_repo):
    member = CreateMember(member_repo).execute("alice", "Alice", "pw", Role.PATRON)
    updated = EditMember(member_repo).execute(member.id, username="alice2", name="Alice B.")
    assert updated.username == "alice2"
    assert updated.name == "Alice B."
    assert updated.password_hash == member.password_hash


def test_edit_member_missing_raises(member_repo):
    with pytest.raises(MemberNotFound):
        EditMember(member_repo).execute(999, username="x", name="y")
