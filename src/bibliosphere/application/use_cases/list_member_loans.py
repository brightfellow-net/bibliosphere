from bibliosphere.application.dto import LoanView
from bibliosphere.domain.exceptions import MemberNotFound
from bibliosphere.domain.ports import BibliographyRepository, LoanRepository, MemberRepository


class ListMemberLoans:
    def __init__(
        self,
        member_repository: MemberRepository,
        loan_repository: LoanRepository,
        bibliography_repository: BibliographyRepository,
    ):
        self._members = member_repository
        self._loans = loan_repository
        self._bibliographies = bibliography_repository

    def execute(self, member_id: int) -> list[LoanView]:
        member = self._members.get_by_id(member_id)
        if member is None:
            raise MemberNotFound(f"No member with id {member_id}")

        views = []
        for loan in self._loans.list_open_loans_for_member(member_id):
            item = self._bibliographies.get_item(loan.item_id)
            bibliography = self._bibliographies.get_by_id(item.bibliography_id) if item else None
            views.append(
                LoanView(
                    loan=loan,
                    bibliography_title=bibliography.title if bibliography else "Unknown",
                    member_name=member.name,
                )
            )
        return views
