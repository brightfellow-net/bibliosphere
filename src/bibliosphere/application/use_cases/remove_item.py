from bibliosphere.domain.exceptions import ItemNotAvailable, ItemNotFound
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
        self._bibliographies.remove_item(item_id)
