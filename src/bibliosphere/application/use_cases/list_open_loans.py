from bibliosphere.application.dto import LoanView
from bibliosphere.domain.ports import BibliographyRepository, LoanRepository, MemberRepository


class ListOpenLoans:
    """All open loans across all members — librarian-facing, for processing returns."""

    def __init__(
        self,
        loan_repository: LoanRepository,
        bibliography_repository: BibliographyRepository,
        member_repository: MemberRepository,
    ):
        self._loans = loan_repository
        self._bibliographies = bibliography_repository
        self._members = member_repository

    def execute(self) -> list[LoanView]:
        views = []
        for loan in self._loans.list_all_open_loans():
            item = self._bibliographies.get_item(loan.item_id)
            bibliography = self._bibliographies.get_by_id(item.bibliography_id) if item else None
            member = self._members.get_by_id(loan.member_id)
            views.append(
                LoanView(
                    loan=loan,
                    bibliography_title=bibliography.title if bibliography else "Unknown",
                    member_name=member.name if member else "Unknown",
                )
            )
        return views
