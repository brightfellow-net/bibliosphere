from datetime import date

from bibliosphere.application.security import hash_password
from bibliosphere.domain.entities import Member, Role
from bibliosphere.domain.exceptions import DuplicateMemberId, DuplicateUsername, InvalidMemberDetails
from bibliosphere.domain.ports import MemberRepository


class CreateMember:
    """Creates a librarian or patron account.

    Enforcing that only a librarian may invoke this is a presentation/composition-root
    concern (role-gated routing), not a rule this use case checks itself — the seed
    script also calls this directly to create the first librarian account.
    """

    def __init__(self, member_repository: MemberRepository):
        self._members = member_repository

    def execute(
        self,
        member_id: str,
        username: str,
        name: str,
        password: str,
        role: Role,
        birthdate: date | None = None,
        email: str | None = None,
        phone: str | None = None,
        expiry_date: date | None = None,
        address: str | None = None,
    ) -> Member:
        """`join_date` is not a parameter: it is always set to today, since members are
        created at the moment they join.
        """
        if not member_id.strip() or not username.strip() or not name.strip() or not password:
            raise InvalidMemberDetails("Member id, username, name, and password must not be blank")

        if self._members.get_by_id(member_id) is not None:
            raise DuplicateMemberId(f"Member id {member_id!r} is already in use")
        if self._members.get_by_username(username) is not None:
            raise DuplicateUsername(f"Username {username!r} is already taken")

        password_hash, salt = hash_password(password)
        member = Member(
            id=member_id,
            username=username,
            name=name,
            role=role,
            password_hash=password_hash,
            password_salt=salt,
            birthdate=birthdate,
            email=email,
            phone=phone,
            join_date=date.today(),
            expiry_date=expiry_date,
            address=address,
        )
        return self._members.add(member)
