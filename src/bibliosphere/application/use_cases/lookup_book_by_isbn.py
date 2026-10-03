from bibliosphere.domain.exceptions import IsbnNotFound
from bibliosphere.domain.ports import BookMetadata, BookMetadataProvider


class LookupBookByIsbn:
    def __init__(self, provider: BookMetadataProvider):
        self._provider = provider

    def execute(self, isbn: str) -> BookMetadata:
        normalized = isbn.replace("-", "").replace(" ", "")
        if not normalized:
            raise IsbnNotFound("Enter an ISBN first.")
        metadata = self._provider.fetch_by_isbn(normalized)
        if metadata is None:
            raise IsbnNotFound(f"No book found for ISBN {isbn.strip()}.")
        return metadata
