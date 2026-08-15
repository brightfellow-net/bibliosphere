from bibliosphere.application.dto import CatalogEntry, CatalogPage, ItemStatus
from bibliosphere.domain.entities import Bibliography
from bibliosphere.domain.ids import require_id
from bibliosphere.domain.ports import BibliographyRepository, CatalogFilters, LoanRepository


class SearchCatalog:
    """The catalog is unbounded (thousands of bibliographies), so it's paginated and
    filtered at the repository — mirrors ListLoanHistory. Per-row items/loans/authors
    lookups in _to_entry stay bounded to one page's worth of bibliographies.
    """

    def __init__(self, bibliography_repository: BibliographyRepository, loan_repository: LoanRepository):
        self._bibliographies = bibliography_repository
        self._loans = loan_repository

    def execute(
        self, filters: CatalogFilters, *, sort_column: str, sort_descending: bool, page: int, page_size: int
    ) -> CatalogPage:
        total_count = self._bibliographies.count(filters)
        entries = [
            self._to_entry(bibliography)
            for bibliography in self._bibliographies.list_page(
                filters, sort_column=sort_column, sort_descending=sort_descending, page=page, page_size=page_size
            )
        ]
        return CatalogPage(entries=entries, total_count=total_count, page=page, page_size=page_size)

    def _to_entry(self, bibliography: Bibliography) -> CatalogEntry:
        bibliography_id = require_id(bibliography.id)
        items = self._bibliographies.list_items(bibliography_id)
        statuses = [
            ItemStatus(item=item, available=self._loans.get_open_loan_for_item(require_id(item.id)) is None)
            for item in items
        ]
        authors = self._bibliographies.list_authors(bibliography_id)
        return CatalogEntry(bibliography=bibliography, authors=authors, items=statuses)
