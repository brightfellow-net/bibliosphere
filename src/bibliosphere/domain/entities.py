from dataclasses import dataclass
from datetime import date
from enum import Enum


class Role(Enum):
    LIBRARIAN = "librarian"
    PATRON = "patron"


@dataclass
class Member:
    id: int | None
    username: str
    name: str
    role: Role
    password_hash: str
    password_salt: str


@dataclass
class Author:
    id: int | None
    name: str


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
    member_id: int
    checkout_date: date
    due_date: date
    return_date: date | None = None

    @property
    def is_open(self) -> bool:
        return self.return_date is None
