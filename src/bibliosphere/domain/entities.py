from dataclasses import dataclass
from datetime import date
from enum import Enum


class Role(Enum):
    LIBRARIAN = "librarian"
    PATRON = "patron"


@dataclass
class Member:
    """`id` is a librarian-assigned membership number (e.g. "20260814001" —
    date + daily sequence), not a database-autoincremented integer: it's
    supplied by the caller before the member is persisted, with GenerateMemberId
    only providing a starting suggestion for the Add Member form.

    `username`/`password_hash`/`password_salt` are required for Role.LIBRARIAN
    (librarians must log in to use the app) but optional for Role.PATRON — a patron
    with no username simply has no self-service login, which is fine since v1 doesn't
    require one. See CreateMember/EditMember for the role-conditional validation.
    """

    id: str | None
    username: str | None
    name: str
    role: Role
    password_hash: str | None
    password_salt: str | None
    birthdate: date | None = None
    email: str | None = None
    phone: str | None = None
    join_date: date | None = None
    expiry_date: date | None = None
    address: str | None = None


@dataclass
class Author:
    id: int | None
    name: str


@dataclass
class BibliographyAuthor:
    """An Author credited on a Bibliography, with their author-order level

    (1 = main author, higher = additional/co-author) — see biblio_author.level
    in data/migration/v2__author.sql.
    """

    author: Author
    level: int = 1


@dataclass
class Bibliography:
    id: int | None
    title: str
    isbn_issn: str | None = None
    sor: str | None = None
    edition: str | None = None
    publish_year: str | None = None
    collation: str | None = None
    series_title: str | None = None
    call_number: str | None = None
    classification: str | None = None
    notes: str | None = None
    language_id: str = "en"
    gmd_id: int | None = None
    publisher_id: int | None = None
    publish_place_id: int | None = None
    content_type_id: int | None = None
    media_type_id: int | None = None
    carrier_type_id: int | None = None


@dataclass
class Item:
    id: int | None
    bibliography_id: int


@dataclass
class Loan:
    id: int | None
    item_id: int
    member_id: str
    checkout_date: date
    due_date: date
    return_date: date | None = None

    @property
    def is_open(self) -> bool:
        return self.return_date is None
