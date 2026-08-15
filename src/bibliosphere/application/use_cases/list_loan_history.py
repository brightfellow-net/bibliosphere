from bibliosphere.application.dto import LoanHistoryPage, LoanView
from bibliosphere.domain.ports import BibliographyRepository, LoanHistoryFilters, LoanRepository, MemberRepository


class ListLoanHistory:
    """One page of loan history (open and returned) across all members, filtered
    per-column — librarian-facing audit view. Paginated at the repository since loan
    history is unbounded over the library's lifetime (docs/requirements.md §6.1).
    """

    def __init__(
        self,
        loan_repository: LoanRepository,
        bibliography_repository: BibliographyRepository,
        member_repository: MemberRepository,
    ):
        self._loans = loan_repository
        self._bibliographies = bibliography_repository
        self._members = member_repository

    def execute(self, filters: LoanHistoryFilters, *, page: int, page_size: int) -> LoanHistoryPage:
        total_count = self._loans.count_history(filters)
        views = []
        for loan in self._loans.list_history_page(filters, page=page, page_size=page_size):
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
        return LoanHistoryPage(views=views, total_count=total_count, page=page, page_size=page_size)
