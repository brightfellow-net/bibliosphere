from bibliosphere.domain.entities import Role
from bibliosphere.domain.exceptions import CannotDeleteLastLibrarian, MemberHasLoanHistory, MemberNotFound
from bibliosphere.domain.ports import LoanRepository, MemberRepository


class DeleteMember:
    def __init__(self, member_repository: MemberRepository, loan_repository: LoanRepository):
        self._members = member_repository
        self._loans = loan_repository

    def execute(self, member_id: str) -> None:
        member = self._members.get_by_id(member_id)
        if member is None:
            raise MemberNotFound(f"No member with id {member_id}")
        if self._loans.has_any_loan_for_member(member_id):
            raise MemberHasLoanHistory("Cannot delete a member that has ever had a loan; it has loan history")
        if member.role is Role.LIBRARIAN:
            librarians = [m for m in self._members.list_all() if m.role is Role.LIBRARIAN]
            if len(librarians) <= 1:
                raise CannotDeleteLastLibrarian("Cannot delete the last remaining librarian account")
        self._members.remove(member_id)
