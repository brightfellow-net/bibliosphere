from bibliosphere.domain.entities import Member
from bibliosphere.domain.ports import MemberRepository


class ListMembers:
    def __init__(self, member_repository: MemberRepository):
        self._members = member_repository

    def execute(self) -> list[Member]:
        return self._members.list_all()
