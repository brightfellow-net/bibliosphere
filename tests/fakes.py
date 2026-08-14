"""In-memory fakes satisfying the domain repository Protocols — no SQLite required.

See docs/architecture.md "Testing implication".
"""

from dataclasses import replace
from itertools import count

from bibliosphere.domain.entities import Author, Bibliography, Item, Loan, Member


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

    def get_by_id(self, bibliography_id: int) -> Bibliography | None:
        return self._bibliographies.get(bibliography_id)

    def get_by_isbn(self, isbn: str) -> Bibliography | None:
        return next((b for b in self._bibliographies.values() if b.isbn_issn == isbn), None)

    def search(self, query: str) -> list[Bibliography]:
        query = query.lower()

        def matches(bibliography: Bibliography) -> bool:
            author_names = " ".join(author.name for author in self.list_authors(bibliography.id))
            haystack = f"{bibliography.title} {bibliography.isbn_issn or ''} {author_names}".lower()
            return query in haystack

        return [b for b in self._bibliographies.values() if matches(b)]

    def list_all(self) -> list[Bibliography]:
        return list(self._bibliographies.values())

    def add_item(self, bibliography_id: int) -> Item:
        new_id = next(self._item_ids)
        item = Item(id=new_id, bibliography_id=bibliography_id)
        self._items[new_id] = item
        return item

    def remove_item(self, item_id: int) -> None:
        self._items.pop(item_id, None)

    def get_item(self, item_id: int) -> Item | None:
        return self._items.get(item_id)

    def list_items(self, bibliography_id: int) -> list[Item]:
        return [item for item in self._items.values() if item.bibliography_id == bibliography_id]

    def set_authors(self, bibliography_id: int, author_ids: list[int]) -> None:
        self._author_ids[bibliography_id] = list(author_ids)

    def list_authors(self, bibliography_id: int) -> list[Author]:
        if self._authors_repo is None:
            return []
        ids = self._author_ids.get(bibliography_id, [])
        return [author for author in (self._authors_repo.get_by_id(i) for i in ids) if author is not None]


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


class FakeMemberRepository:
    def __init__(self):
        self._members: dict[int, Member] = {}
        self._ids = count(1)

    def add(self, member: Member) -> Member:
        new_id = next(self._ids)
        stored = Member(
            id=new_id,
            username=member.username,
            name=member.name,
            role=member.role,
            password_hash=member.password_hash,
            password_salt=member.password_salt,
        )
        self._members[new_id] = stored
        return stored

    def update(self, member: Member) -> None:
        self._members[member.id] = member

    def get_by_id(self, member_id: int) -> Member | None:
        return self._members.get(member_id)

    def get_by_username(self, username: str) -> Member | None:
        return next((m for m in self._members.values() if m.username == username), None)

    def list_all(self) -> list[Member]:
        return list(self._members.values())


class FakeLoanRepository:
    def __init__(self):
        self._loans: dict[int, Loan] = {}
        self._ids = count(1)

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

    def list_open_loans_for_member(self, member_id: int) -> list[Loan]:
        return [loan for loan in self._loans.values() if loan.member_id == member_id and loan.is_open]

    def list_all_open_loans(self) -> list[Loan]:
        return [loan for loan in self._loans.values() if loan.is_open]

    def count_open_loans_for_member(self, member_id: int) -> int:
        return len(self.list_open_loans_for_member(member_id))
