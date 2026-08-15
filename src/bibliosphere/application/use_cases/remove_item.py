from bibliosphere.domain.exceptions import ItemHasLoanHistory, ItemNotAvailable, ItemNotFound
from bibliosphere.domain.ports import BibliographyRepository, LoanRepository


class RemoveItem:
    def __init__(self, bibliography_repository: BibliographyRepository, loan_repository: LoanRepository):
        self._bibliographies = bibliography_repository
        self._loans = loan_repository

    def execute(self, item_id: int) -> None:
        item = self._bibliographies.get_item(item_id)
        if item is None:
            raise ItemNotFound(f"No item with id {item_id}")
        if self._loans.get_open_loan_for_item(item_id) is not None:
            raise ItemNotAvailable("Cannot remove an item that is currently checked out")
        # Not just the open-loan case above: the loans.item_id foreign key rejects
        # deleting an item that ANY loan references, including returned ones — check
        # explicitly so that's a clean error instead of an unhandled IntegrityError.
        if self._loans.has_any_loan_for_item(item_id):
            raise ItemHasLoanHistory(
                f"Cannot remove item {item_id}: it has loan history, which must be kept intact"
            )
        self._bibliographies.remove_item(item_id)
