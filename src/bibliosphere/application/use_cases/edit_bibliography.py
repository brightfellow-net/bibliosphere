from bibliosphere.domain.entities import Bibliography
from bibliosphere.domain.exceptions import BibliographyNotFound, DuplicateIsbn
from bibliosphere.domain.ports import AuthorRepository, BibliographyRepository, UnitOfWork


class EditBibliography:
    def __init__(
        self,
        bibliography_repository: BibliographyRepository,
        author_repository: AuthorRepository,
        unit_of_work: UnitOfWork,
    ):
        self._bibliographies = bibliography_repository
        self._authors = author_repository
        self._uow = unit_of_work

    def execute(
        self,
        bibliography_id: int,
        title: str,
        authors: list[str],
        isbn_issn: str | None = None,
        sor: str | None = None,
        edition: str | None = None,
        publish_year: str | None = None,
        collation: str | None = None,
        series_title: str | None = None,
        call_number: str | None = None,
        classification: str | None = None,
        notes: str | None = None,
        language_id: str = "en",
        gmd_id: int | None = None,
        publisher_id: int | None = None,
        publish_place_id: int | None = None,
        content_type_id: int | None = None,
        media_type_id: int | None = None,
        carrier_type_id: int | None = None,
    ) -> Bibliography:
        existing = self._bibliographies.get_by_id(bibliography_id)
        if existing is None:
            raise BibliographyNotFound(f"No bibliography with id {bibliography_id}")

        if isbn_issn:
            other = self._bibliographies.get_by_isbn(isbn_issn)
            if other is not None and other.id != bibliography_id:
                raise DuplicateIsbn(f"A bibliography with ISBN/ISSN {isbn_issn!r} already exists")

        updated = Bibliography(
            id=bibliography_id,
            title=title,
            isbn_issn=isbn_issn,
            sor=sor,
            edition=edition,
            publish_year=publish_year,
            collation=collation,
            series_title=series_title,
            call_number=call_number,
            classification=classification,
            notes=notes,
            language_id=language_id,
            gmd_id=gmd_id,
            publisher_id=publisher_id,
            publish_place_id=publish_place_id,
            content_type_id=content_type_id,
            media_type_id=media_type_id,
            carrier_type_id=carrier_type_id,
        )
        with self._uow:
            self._bibliographies.update(updated)

            unique_authors = list(dict.fromkeys(authors))
            author_ids = [self._authors.find_or_create_by_name(name).id for name in unique_authors]
            self._bibliographies.set_authors(bibliography_id, author_ids)

        return updated
