from datetime import date

from bibliosphere.domain.ports import MemberRepository


class GenerateMemberId:
    """Suggests the next member id for today: <YYYYMMDD><3-digit sequence>,
    e.g. 20260814001. Purely a starting suggestion for the Add Member form —
    the librarian can accept it as-is or type a different id entirely; nothing
    reserves it until CreateMember actually persists a member with it.
    """

    def __init__(self, member_repository: MemberRepository):
        self._members = member_repository

    def execute(self) -> str:
        prefix = date.today().strftime("%Y%m%d")
        todays_sequences = [
            int(member.id[len(prefix) :])
            for member in self._members.list_all()
            if member.id.startswith(prefix) and member.id[len(prefix) :].isdigit()
        ]
        next_sequence = max(todays_sequences, default=0) + 1
        return f"{prefix}{next_sequence:03d}"
