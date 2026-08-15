from bibliosphere.domain.exceptions import BibliographyNotFound
from bibliosphere.domain.ids import require_id
from bibliosphere.domain.ports import AuthorRepository, BibliographyRepository, UnitOfWork


class SetBibliographyAuthors:
    """Replaces a bibliography's author list, independent of its other fields.

    Kept separate from AddBibliography/EditBibliography so a librarian can manage
    authors (add, remove, reorder) without re-submitting every other field.
    """

    def __init__(
        self,
        bibliography_repository: BibliographyRepository,
        author_repository: AuthorRepository,
        unit_of_work: UnitOfWork,
    ):
        self._bibliographies = bibliography_repository
        self._authors = author_repository
        self._uow = unit_of_work

    def execute(self, bibliography_id: int, authors: list[str]) -> None:
        """`authors` order is preserved as the stored author level (1-based)."""
        if self._bibliographies.get_by_id(bibliography_id) is None:
            raise BibliographyNotFound(f"No bibliography with id {bibliography_id}")

        unique_authors = list(dict.fromkeys(authors))
        with self._uow:
            author_ids = [require_id(self._authors.find_or_create_by_name(name).id) for name in unique_authors]
            self._bibliographies.set_authors(bibliography_id, author_ids)
