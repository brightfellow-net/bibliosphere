"""In-memory fakes satisfying the domain repository Protocols — no SQLite required.

See docs/architecture.md "Testing implication".
"""

from dataclasses import replace
from itertools import count

from bibliosphere.domain.entities import Author, Bibliography, BibliographyAuthor, Item, Loan, Member
from bibliosphere.domain.ports import CatalogFilters, LoanHistoryFilters

# Columns matched by a plain prefix startswith() check, mirroring
# SqliteBibliographyRepository's _PREFIX_FILTER_COLUMNS. "title" is excluded — it
# matches by substring instead (see _matches_catalog_filters), "author" isn't a plain
# bibliography attribute at all.
_PREFIX_FILTER_COLUMNS = ("call_number", "series_title", "isbn_issn", "edition", "publish_year")

# Attribute getters for every sortable CatalogFilters column (title included — sorting
# is unaffected by title's prefix->substring matching change), mirroring
# SqliteBibliographyRepository's _SORTABLE_COLUMNS whitelist.
_CATALOG_SORT_KEYS = {
    "call_number": lambda b: b.call_number or "",
    "title": lambda b: b.title,
    "series_title": lambda b: b.series_title or "",
    "isbn_issn": lambda b: b.isbn_issn or "",
    "edition": lambda b: b.edition or "",
    "publish_year": lambda b: b.publish_year or "",
}


class FakeBibliographyRepository:
    """Resolves author ids to Author records via the given FakeAuthorRepository,
    mirroring how SqliteBibliographyRepository joins to the `authors` table.
    """

    def __init__(self, author_repository: "FakeAuthorRepository | None" = None):
        self._authors_repo = author_repository
        self._bibliographies: dict[int, Bibliography] = {}
        self._items: dict[int, Item] = {}
        self._author_ids: dict[int, list[int]] = {}
        self._bibliography_ids = count(1)
        self._item_ids = count(1)

    def add(self, bibliography: Bibliography) -> Bibliography:
        new_id = next(self._bibliography_ids)
        stored = replace(bibliography, id=new_id)
        self._bibliographies[new_id] = stored
        return stored

    def update(self, bibliography: Bibliography) -> None:
        self._bibliographies[bibliography.id] = bibliography

    def remove(self, bibliography_id: int) -> None:
        self._bibliographies.pop(bibliography_id, None)
        self._author_ids.pop(bibliography_id, None)

    def get_by_id(self, bibliography_id: int) -> Bibliography | None:
        return self._bibliographies.get(bibliography_id)

    def get_by_isbn(self, isbn: str) -> Bibliography | None:
        return next((b for b in self._bibliographies.values() if b.isbn_issn == isbn), None)

    def get_by_call_number(self, call_number: str) -> Bibliography | None:
        return next((b for b in self._bibliographies.values() if b.call_number == call_number), None)

    def _matches_catalog_filters(self, bibliography: Bibliography, filters: CatalogFilters) -> bool:
        def starts_with(value: str | None, needle: str) -> bool:
            return not needle or (value or "").lower().startswith(needle.lower())

        def contains(value: str | None, needle: str) -> bool:
            return not needle or needle.lower() in (value or "").lower()

        for column in _PREFIX_FILTER_COLUMNS:
            if not starts_with(getattr(bibliography, column), getattr(filters, column)):
                return False
        if not contains(bibliography.title, filters.title):
            return False
        if filters.author:
            names = [credit.author.name for credit in self.list_authors(bibliography.id)]
            if not any(filters.author.lower() in name.lower() for name in names):
                return False
        return True

    def _catalog_matches(
        self, filters: CatalogFilters, *, sort_column: str, sort_descending: bool
    ) -> list[Bibliography]:
        matches = [b for b in self._bibliographies.values() if self._matches_catalog_filters(b, filters)]
        key = _CATALOG_SORT_KEYS[sort_column]
        return sorted(matches, key=lambda b: (key(b), b.id), reverse=sort_descending)

    def count(self, filters: CatalogFilters) -> int:
        return len(self._catalog_matches(filters, sort_column="title", sort_descending=False))

    def list_page(
        self, filters: CatalogFilters, *, sort_column: str, sort_descending: bool, page: int, page_size: int
    ) -> list[Bibliography]:
        start = (page - 1) * page_size
        matches = self._catalog_matches(filters, sort_column=sort_column, sort_descending=sort_descending)
        return matches[start : start + page_size]

    def add_item(self, bibliography_id: int) -> Item:
        new_id = next(self._item_ids)
        item = Item(id=new_id, bibliography_id=bibliography_id)
        self._items[new_id] = item
        return item

    def add_items(self, bibliography_id: int, count: int) -> list[Item]:
        items = []
        for _ in range(count):
            new_id = next(self._item_ids)
            item = Item(id=new_id, bibliography_id=bibliography_id)
            self._items[new_id] = item
            items.append(item)
        return items

    def remove_item(self, item_id: int) -> None:
        self._items.pop(item_id, None)

    def get_item(self, item_id: int) -> Item | None:
        return self._items.get(item_id)

    def list_items(self, bibliography_id: int) -> list[Item]:
        return [item for item in self._items.values() if item.bibliography_id == bibliography_id]

    def set_authors(self, bibliography_id: int, author_ids: list[int]) -> None:
        self._author_ids[bibliography_id] = list(dict.fromkeys(author_ids))

    def list_authors(self, bibliography_id: int) -> list[BibliographyAuthor]:
        if self._authors_repo is None:
            return []
        ids = self._author_ids.get(bibliography_id, [])
        credits = []
        for level, author_id in enumerate(ids, start=1):
            author = self._authors_repo.get_by_id(author_id)
            if author is not None:
                credits.append(BibliographyAuthor(author=author, level=level))
        return credits


class FakeAuthorRepository:
    def __init__(self):
        self._authors: dict[int, Author] = {}
        self._ids = count(1)

    def add(self, author: Author) -> Author:
        new_id = next(self._ids)
        stored = Author(id=new_id, name=author.name)
        self._authors[new_id] = stored
        return stored

    def get_by_id(self, author_id: int) -> Author | None:
        return self._authors.get(author_id)

    def get_by_name(self, name: str) -> Author | None:
        return next((a for a in self._authors.values() if a.name == name), None)

    def list_all(self) -> list[Author]:
        return list(self._authors.values())

    def find_or_create_by_name(self, name: str) -> Author:
        existing = self.get_by_name(name)
        if existing is not None:
            return existing
        return self.add(Author(id=None, name=name))


class FakeUnitOfWork:
    """No-op: fakes mutate plain dicts, so each write is already atomic and there's
    no uncommitted/partial state to roll back — unlike SqliteUnitOfWork, which
    guards against a real multi-statement SQL transaction being left half-applied.
    """

    def __enter__(self) -> "FakeUnitOfWork":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        pass


class FakeMemberRepository:
    """member.id is caller-supplied (see Member's docstring), not autoincremented."""

    def __init__(self):
        self._members: dict[str, Member] = {}

    def add(self, member: Member) -> Member:
        self._members[member.id] = member
        return member

    def update(self, member: Member) -> None:
        self._members[member.id] = member

    def remove(self, member_id: str) -> None:
        self._members.pop(member_id, None)

    def get_by_id(self, member_id: str) -> Member | None:
        return self._members.get(member_id)

    def get_by_username(self, username: str) -> Member | None:
        return next((m for m in self._members.values() if m.username == username), None)

    def list_all(self) -> list[Member]:
        return list(self._members.values())


class FakeLoanRepository:
    """Resolves item/member ids to titles/names via the given fakes, mirroring how
    SqliteLoanRepository's history query LEFT JOINs to items/bibliographies/members.
    """

    def __init__(
        self,
        bibliography_repository: "FakeBibliographyRepository | None" = None,
        member_repository: "FakeMemberRepository | None" = None,
    ):
        self._loans: dict[int, Loan] = {}
        self._ids = count(1)
        self._bibliographies_repo = bibliography_repository
        self._members_repo = member_repository

    def add(self, loan: Loan) -> Loan:
        new_id = next(self._ids)
        stored = Loan(
            id=new_id,
            item_id=loan.item_id,
            member_id=loan.member_id,
            checkout_date=loan.checkout_date,
            due_date=loan.due_date,
            return_date=loan.return_date,
        )
        self._loans[new_id] = stored
        return stored

    def update(self, loan: Loan) -> None:
        self._loans[loan.id] = loan

    def get_by_id(self, loan_id: int) -> Loan | None:
        return self._loans.get(loan_id)

    def get_open_loan_for_item(self, item_id: int) -> Loan | None:
        return next((loan for loan in self._loans.values() if loan.item_id == item_id and loan.is_open), None)

    def has_any_loan_for_item(self, item_id: int) -> bool:
        return any(loan.item_id == item_id for loan in self._loans.values())

    def has_any_loan_for_member(self, member_id: str) -> bool:
        return any(loan.member_id == member_id for loan in self._loans.values())

    def list_open_loans_for_member(self, member_id: str) -> list[Loan]:
        return [loan for loan in self._loans.values() if loan.member_id == member_id and loan.is_open]

    def list_all_open_loans(self) -> list[Loan]:
        return [loan for loan in self._loans.values() if loan.is_open]

    def count_open_loans_for_member(self, member_id: str) -> int:
        return len(self.list_open_loans_for_member(member_id))

    def _title_for(self, loan: Loan) -> str:
        item = self._bibliographies_repo.get_item(loan.item_id) if self._bibliographies_repo else None
        bibliography = self._bibliographies_repo.get_by_id(item.bibliography_id) if item else None
        return bibliography.title if bibliography else "Unknown"

    def _member_name_for(self, loan: Loan) -> str:
        member = self._members_repo.get_by_id(loan.member_id) if self._members_repo else None
        return member.name if member else "Unknown"

    def _matches_history_filters(self, loan: Loan, filters: LoanHistoryFilters) -> bool:
        if filters.member_id and filters.member_id.lower() not in loan.member_id.lower():
            return False
        if filters.member_name and filters.member_name.lower() not in self._member_name_for(loan).lower():
            return False
        if filters.title and filters.title.lower() not in self._title_for(loan).lower():
            return False
        if filters.checkout_date and filters.checkout_date.lower() not in loan.checkout_date.isoformat():
            return False
        if filters.checkout_date_from is not None and loan.checkout_date < filters.checkout_date_from:
            return False
        if filters.checkout_date_to is not None and loan.checkout_date > filters.checkout_date_to:
            return False
        if filters.due_date and filters.due_date.lower() not in loan.due_date.isoformat():
            return False
        if filters.return_date:
            if loan.return_date is None or filters.return_date.lower() not in loan.return_date.isoformat():
                return False
        if filters.status:
            status_text = "checked out" if loan.is_open else "returned"
            if filters.status.strip().lower() not in status_text:
                return False
        return True

    def _history_matches(self, filters: LoanHistoryFilters) -> list[Loan]:
        matches = [loan for loan in self._loans.values() if self._matches_history_filters(loan, filters)]
        return sorted(matches, key=lambda loan: (loan.checkout_date, loan.id), reverse=True)

    def count_history(self, filters: LoanHistoryFilters) -> int:
        return len(self._history_matches(filters))

    def list_history_page(self, filters: LoanHistoryFilters, *, page: int, page_size: int) -> list[Loan]:
        start = (page - 1) * page_size
        return self._history_matches(filters)[start : start + page_size]
