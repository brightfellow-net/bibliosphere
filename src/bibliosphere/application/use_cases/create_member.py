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
        created at the moment they join. `username`/`password` are only required for
        Role.LIBRARIAN — a patron with neither simply has no self-service login.
        """
        if not member_id.strip() or not name.strip():
            raise InvalidMemberDetails("Member id and name must not be blank")
        if role is Role.LIBRARIAN and (not username.strip() or not password):
            raise InvalidMemberDetails("Librarian accounts require a username and password")

        if self._members.get_by_id(member_id) is not None:
            raise DuplicateMemberId(f"Member id {member_id!r} is already in use")

        username = username.strip() or None
        if username is not None and self._members.get_by_username(username) is not None:
            raise DuplicateUsername(f"Username {username!r} is already taken")

        if password:
            password_hash, salt = hash_password(password)
        else:
            password_hash, salt = None, None
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
