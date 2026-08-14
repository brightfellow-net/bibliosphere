from bibliosphere.application.security import hash_password
from bibliosphere.domain.entities import Member
from bibliosphere.domain.exceptions import DuplicateUsername, InvalidMemberDetails, MemberNotFound
from bibliosphere.domain.ports import MemberRepository


class EditMember:
    def __init__(self, member_repository: MemberRepository):
        self._members = member_repository

    def execute(self, member_id: int, username: str, name: str, password: str = "") -> Member:
        """`password` is optional: leave blank to keep the member's current password."""
        if not username.strip() or not name.strip():
            raise InvalidMemberDetails("Username and name must not be blank")

        existing = self._members.get_by_id(member_id)
        if existing is None:
            raise MemberNotFound(f"No member with id {member_id}")

        other = self._members.get_by_username(username)
        if other is not None and other.id != member_id:
            raise DuplicateUsername(f"Username {username!r} is already taken")

        if password:
            password_hash, password_salt = hash_password(password)
        else:
            password_hash, password_salt = existing.password_hash, existing.password_salt

        updated = Member(
            id=member_id,
            username=username,
            name=name,
            role=existing.role,
            password_hash=password_hash,
            password_salt=password_salt,
        )
        self._members.update(updated)
        return updated
