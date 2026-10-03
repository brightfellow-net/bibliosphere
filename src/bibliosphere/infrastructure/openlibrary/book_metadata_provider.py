import re

import requests

from bibliosphere.domain.exceptions import BookLookupFailed
from bibliosphere.domain.ports import BookMetadata

_BASE_URL = "https://openlibrary.org"
_TIMEOUT_SECONDS = 10
_YEAR = re.compile(r"\b(\d{4})\b")


class OpenLibraryBookMetadataProvider:
    """Adapter implementing BookMetadataProvider against the Open Library REST API."""

    def __init__(self, session: requests.Session | None = None):
        self._session = session or requests.Session()

    def _get_json(self, path: str) -> dict[str, object] | None:
        try:
            response = self._session.get(f"{_BASE_URL}{path}", timeout=_TIMEOUT_SECONDS)
        except requests.RequestException as error:
            raise BookLookupFailed(f"Could not reach Open Library: {error}") from error
        if response.status_code == 404:
            return None
        if response.status_code != 200:
            raise BookLookupFailed(f"Open Library returned HTTP {response.status_code}.")
        try:
            data = response.json()
        except ValueError as error:
            raise BookLookupFailed("Open Library returned an invalid response.") from error
        return data if isinstance(data, dict) else None

    def fetch_by_isbn(self, isbn: str) -> BookMetadata | None:
        edition = self._get_json(f"/isbn/{isbn}.json")
        if edition is None:
            return None

        title = edition.get("title")
        subtitle = edition.get("subtitle")
        if isinstance(title, str) and isinstance(subtitle, str) and subtitle:
            title = f"{title}: {subtitle}"

        series = edition.get("series")
        edition_name = edition.get("edition_name")
        publish_date = edition.get("publish_date")
        year = _YEAR.search(publish_date) if isinstance(publish_date, str) else None

        return BookMetadata(
            title=title if isinstance(title, str) else None,
            authors=self._author_names(edition.get("authors")),
            series_title=series[0] if isinstance(series, list) and series and isinstance(series[0], str) else None,
            edition=edition_name if isinstance(edition_name, str) else None,
            publish_year=year.group(1) if year else None,
        )

    def _author_names(self, refs: object) -> list[str]:
        names: list[str] = []
        if not isinstance(refs, list):
            return names
        for ref in refs:
            key = ref.get("key") if isinstance(ref, dict) else None
            if not isinstance(key, str):
                continue
            author = self._get_json(f"{key}.json")
            name = author.get("name") if author else None
            if isinstance(name, str) and name:
                names.append(name)
        return names
