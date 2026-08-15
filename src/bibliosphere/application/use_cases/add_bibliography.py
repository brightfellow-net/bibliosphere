from bibliosphere.domain.entities import Bibliography
from bibliosphere.domain.exceptions import DuplicateCallNumber, DuplicateIsbn, InvalidBibliographyDetails
from bibliosphere.domain.ids import require_id
from bibliosphere.domain.ports import AuthorRepository, BibliographyRepository, UnitOfWork


class AddBibliography:
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
        title: str,
        authors: list[str],
        *,
        call_number: str,
        isbn_issn: str | None = None,
        sor: str | None = None,
        edition: str | None = None,
        publish_year: str | None = None,
        collation: str | None = None,
        series_title: str | None = None,
        classification: str | None = None,
        notes: str | None = None,
        language_id: str = "en",
        gmd_id: int | None = None,
        publisher_id: int | None = None,
        publish_place_id: int | None = None,
        content_type_id: int | None = None,
        media_type_id: int | None = None,
        carrier_type_id: int | None = None,
        initial_copies: int = 0,
    ) -> Bibliography:
        if not call_number or not call_number.strip():
            raise InvalidBibliographyDetails("Call number must not be blank")
        if initial_copies < 0:
            raise InvalidBibliographyDetails("Initial copies must not be negative")
        if self._bibliographies.get_by_call_number(call_number) is not None:
            raise DuplicateCallNumber(f"A bibliography with call number {call_number!r} already exists")

        if isbn_issn and self._bibliographies.get_by_isbn(isbn_issn) is not None:
            raise DuplicateIsbn(f"A bibliography with ISBN/ISSN {isbn_issn!r} already exists")

        bibliography = Bibliography(
            id=None,
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
            created = self._bibliographies.add(bibliography)

            unique_authors = list(dict.fromkeys(authors))
            author_ids = [require_id(self._authors.find_or_create_by_name(name).id) for name in unique_authors]
            self._bibliographies.set_authors(require_id(created.id), author_ids)

            if initial_copies:
                self._bibliographies.add_items(require_id(created.id), initial_copies)

        return created
