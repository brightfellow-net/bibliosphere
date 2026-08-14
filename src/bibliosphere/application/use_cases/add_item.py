from bibliosphere.domain.entities import Item
from bibliosphere.domain.exceptions import BibliographyNotFound
from bibliosphere.domain.ports import BibliographyRepository


class AddItem:
    def __init__(self, bibliography_repository: BibliographyRepository):
        self._bibliographies = bibliography_repository

    def execute(self, bibliography_id: int) -> Item:
        if self._bibliographies.get_by_id(bibliography_id) is None:
            raise BibliographyNotFound(f"No bibliography with id {bibliography_id}")
        return self._bibliographies.add_item(bibliography_id)
