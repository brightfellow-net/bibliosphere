from bibliosphere.application.security import verify_password
from bibliosphere.domain.entities import Member
from bibliosphere.domain.exceptions import InvalidCredentials
from bibliosphere.domain.ports import MemberRepository


class AuthenticateUser:
    def __init__(self, member_repository: MemberRepository):
        self._members = member_repository

    def execute(self, username: str, password: str) -> Member:
        member = self._members.get_by_username(username)
        if member is None or not verify_password(password, member.password_hash, member.password_salt):
            raise InvalidCredentials("Invalid username or password")
        return member
