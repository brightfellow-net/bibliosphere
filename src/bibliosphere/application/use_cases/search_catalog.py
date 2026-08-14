from bibliosphere.application.dto import CatalogEntry, ItemStatus
from bibliosphere.domain.ports import BibliographyRepository, LoanRepository


class SearchCatalog:
    def __init__(self, bibliography_repository: BibliographyRepository, loan_repository: LoanRepository):
        self._bibliographies = bibliography_repository
        self._loans = loan_repository

    def execute(self, query: str) -> list[CatalogEntry]:
        results = self._bibliographies.search(query) if query else self._bibliographies.list_all()
        return [self._to_entry(bibliography) for bibliography in results]

    def _to_entry(self, bibliography) -> CatalogEntry:
        items = self._bibliographies.list_items(bibliography.id)
        statuses = [
            ItemStatus(item=item, available=self._loans.get_open_loan_for_item(item.id) is None) for item in items
        ]
        authors = self._bibliographies.list_authors(bibliography.id)
        return CatalogEntry(bibliography=bibliography, authors=authors, items=statuses)
