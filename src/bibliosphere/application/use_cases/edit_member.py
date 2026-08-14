from bibliosphere.domain.entities import Member
from bibliosphere.domain.exceptions import DuplicateUsername, MemberNotFound
from bibliosphere.domain.ports import MemberRepository


class EditMember:
    def __init__(self, member_repository: MemberRepository):
        self._members = member_repository

    def execute(self, member_id: int, username: str, name: str) -> Member:
        existing = self._members.get_by_id(member_id)
        if existing is None:
            raise MemberNotFound(f"No member with id {member_id}")

        other = self._members.get_by_username(username)
        if other is not None and other.id != member_id:
            raise DuplicateUsername(f"Username {username!r} is already taken")

        updated = Member(
            id=member_id,
            username=username,
            name=name,
            role=existing.role,
            password_hash=existing.password_hash,
            password_salt=existing.password_salt,
        )
        self._members.update(updated)
        return updated
