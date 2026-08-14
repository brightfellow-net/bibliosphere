from dataclasses import replace
from datetime import date

from bibliosphere.domain.entities import Loan
from bibliosphere.domain.exceptions import LoanNotFound
from bibliosphere.domain.ports import LoanRepository


class ReturnItem:
    def __init__(self, loan_repository: LoanRepository):
        self._loans = loan_repository

    def execute(self, loan_id: int) -> Loan:
        loan = self._loans.get_by_id(loan_id)
        if loan is None:
            raise LoanNotFound(f"No loan with id {loan_id}")

        returned = replace(loan, return_date=date.today())
        self._loans.update(returned)
        return returned
