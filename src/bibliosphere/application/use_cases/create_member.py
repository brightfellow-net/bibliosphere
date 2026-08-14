from bibliosphere.application.security import hash_password
from bibliosphere.domain.entities import Member, Role
from bibliosphere.domain.exceptions import DuplicateUsername
from bibliosphere.domain.ports import MemberRepository


class CreateMember:
    """Creates a librarian or patron account.

    Enforcing that only a librarian may invoke this is a presentation/composition-root
    concern (role-gated routing), not a rule this use case checks itself — the seed
    script also calls this directly to create the first librarian account.
    """

    def __init__(self, member_repository: MemberRepository):
        self._members = member_repository

    def execute(self, username: str, name: str, password: str, role: Role) -> Member:
        if self._members.get_by_username(username) is not None:
            raise DuplicateUsername(f"Username {username!r} is already taken")

        password_hash, salt = hash_password(password)
        member = Member(
            id=None,
            username=username,
            name=name,
            role=role,
            password_hash=password_hash,
            password_salt=salt,
        )
        return self._members.add(member)
