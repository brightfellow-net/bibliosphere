from bibliosphere.domain.exceptions import BibliographyHasItems, BibliographyNotFound
from bibliosphere.domain.ports import BibliographyRepository


class DeleteBibliography:
    def __init__(self, bibliography_repository: BibliographyRepository):
        self._bibliographies = bibliography_repository

    def execute(self, bibliography_id: int) -> None:
        if self._bibliographies.get_by_id(bibliography_id) is None:
            raise BibliographyNotFound(f"No bibliography with id {bibliography_id}")
        if self._bibliographies.list_items(bibliography_id):
            raise BibliographyHasItems("Cannot delete a bibliography that still has items; remove them first")
        self._bibliographies.remove(bibliography_id)
