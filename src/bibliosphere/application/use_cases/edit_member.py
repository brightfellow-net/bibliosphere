from datetime import date

from bibliosphere.application.security import hash_password
from bibliosphere.domain.entities import Member, Role
from bibliosphere.domain.exceptions import DuplicateUsername, InvalidMemberDetails, MemberNotFound
from bibliosphere.domain.ports import MemberRepository


class EditMember:
    def __init__(self, member_repository: MemberRepository):
        self._members = member_repository

    def execute(
        self,
        member_id: str,
        username: str,
        name: str,
        role: Role,
        password: str = "",
        birthdate: date | None = None,
        email: str | None = None,
        phone: str | None = None,
        expiry_date: date | None = None,
        address: str | None = None,
    ) -> Member:
        """`password` is optional: leave blank to keep the member's current password.
        `join_date` is not a parameter: it is set once at creation and not editable.
        `username`/password are only required for Role.LIBRARIAN — a patron with
        neither simply has no self-service login.
        """
        if not name.strip():
            raise InvalidMemberDetails("Name must not be blank")
        if role is Role.LIBRARIAN and not username.strip():
            raise InvalidMemberDetails("Librarian accounts require a username")

        existing = self._members.get_by_id(member_id)
        if existing is None:
            raise MemberNotFound(f"No member with id {member_id}")
        if role is Role.LIBRARIAN and not password and existing.password_hash is None:
            raise InvalidMemberDetails("Librarian accounts require a password")

        username = username.strip() or None
        if username is not None:
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
            role=role,
            password_hash=password_hash,
            password_salt=password_salt,
            birthdate=birthdate,
            email=email,
            phone=phone,
            join_date=existing.join_date,
            expiry_date=expiry_date,
            address=address,
        )
        self._members.update(updated)
        return updated
