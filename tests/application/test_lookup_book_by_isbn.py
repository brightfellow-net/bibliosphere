import pytest

from bibliosphere.application.use_cases.lookup_book_by_isbn import LookupBookByIsbn
from bibliosphere.domain.exceptions import IsbnNotFound
from bibliosphere.domain.ports import BookMetadata


class FakeProvider:
    def __init__(self, books: dict[str, BookMetadata]):
        self._books = books
        self.requested: list[str] = []

    def fetch_by_isbn(self, isbn: str) -> BookMetadata | None:
        self.requested.append(isbn)
        return self._books.get(isbn)


def test_lookup_returns_metadata_and_normalizes_isbn():
    provider = FakeProvider({"9780140328721": BookMetadata(title="Fantastic Mr. Fox", authors=["Roald Dahl"])})

    metadata = LookupBookByIsbn(provider).execute(" 978-0-14-032872-1 ")

    assert metadata.title == "Fantastic Mr. Fox"
    assert provider.requested == ["9780140328721"]


def test_lookup_unknown_isbn_raises():
    with pytest.raises(IsbnNotFound):
        LookupBookByIsbn(FakeProvider({})).execute("123")


def test_lookup_blank_isbn_raises_without_calling_provider():
    provider = FakeProvider({})
    with pytest.raises(IsbnNotFound):
        LookupBookByIsbn(provider).execute("  ")
    assert provider.requested == []
