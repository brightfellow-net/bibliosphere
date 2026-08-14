from datetime import date, timedelta

from bibliosphere.application.config import LOAN_PERIOD_DAYS, MAX_LOANS_PER_MEMBER
from bibliosphere.domain.entities import Loan
from bibliosphere.domain.exceptions import BibliographyNotFound, ItemNotAvailable, LoanLimitExceeded, MemberNotFound
from bibliosphere.domain.ports import BibliographyRepository, LoanRepository, MemberRepository


class CheckoutItem:
    def __init__(
        self,
        bibliography_repository: BibliographyRepository,
        member_repository: MemberRepository,
        loan_repository: LoanRepository,
    ):
        self._bibliographies = bibliography_repository
        self._members = member_repository
        self._loans = loan_repository

    def execute(self, bibliography_id: int, member_id: str) -> Loan:
        if self._bibliographies.get_by_id(bibliography_id) is None:
            raise BibliographyNotFound(f"No bibliography with id {bibliography_id}")
        if self._members.get_by_id(member_id) is None:
            raise MemberNotFound(f"No member with id {member_id}")

        if self._loans.count_open_loans_for_member(member_id) >= MAX_LOANS_PER_MEMBER:
            raise LoanLimitExceeded(f"Member already has {MAX_LOANS_PER_MEMBER} books checked out")

        available_item = next(
            (
                item
                for item in self._bibliographies.list_items(bibliography_id)
                if self._loans.get_open_loan_for_item(item.id) is None
            ),
            None,
        )
        if available_item is None:
            raise ItemNotAvailable("No available item for this bibliography")

        today = date.today()
        loan = Loan(
            id=None,
            item_id=available_item.id,
            member_id=member_id,
            checkout_date=today,
            due_date=today + timedelta(days=LOAN_PERIOD_DAYS),
        )
        return self._loans.add(loan)
