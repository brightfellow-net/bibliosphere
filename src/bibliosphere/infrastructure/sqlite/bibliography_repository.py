import sqlite3

from bibliosphere.domain.entities import Author, Bibliography, BibliographyAuthor, Item
from bibliosphere.domain.ports import CatalogFilters

# Direct bibliography columns filterable/sortable via CatalogFilters/list_page's
# sort_column — a whitelist so sort_column (though UI-driven, not user-typed) is never
# string-interpolated straight into SQL. "author" isn't here: it isn't a plain column,
# it's an EXISTS subquery (see _catalog_query_sql), and isn't offered as a sort key.
_FILTERABLE_COLUMNS = ("call_number", "title", "series_title", "isbn_issn", "edition", "publish_year")


def _like_prefix_param(text: str) -> str:
    # Escape LIKE wildcards so a literal '%' or '_' in a search (e.g. "100% Wolf") is
    # matched literally, then anchor the pattern to a prefix match (no leading '%') so
    # it can use a plain B-tree index — unlike a substring '%text%' match.
    escaped = text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"{escaped}%"


def _catalog_query_sql(filters: CatalogFilters) -> tuple[str, list[str]]:
    """Returns (where_sql, params) for BibliographyRepository.count/list_page.

    No dynamic FROM/JOIN is needed here (contrast loan_repository._history_query_sql):
    the author filter is a self-contained EXISTS subquery rather than a join, so it
    can't produce duplicate rows and doesn't need a DISTINCT.
    """
    conditions = []
    params = []
    for column in _FILTERABLE_COLUMNS:
        value: str = getattr(filters, column)
        if value:
            conditions.append(f"bibliographies.{column} LIKE ? ESCAPE '\\'")
            params.append(_like_prefix_param(value))
    if filters.author:
        conditions.append(
            "EXISTS (SELECT 1 FROM bibliography_authors ba JOIN authors a ON a.id = ba.author_id "
            "WHERE ba.bibliography_id = bibliographies.id AND a.name LIKE ? ESCAPE '\\')"
        )
        params.append(_like_prefix_param(filters.author))
    where_sql = " AND ".join(conditions) if conditions else "1 = 1"
    return where_sql, params


_UPDATABLE_COLUMNS = (
    "title",
    "isbn_issn",
    "sor",
    "edition",
    "publish_year",
    "collation",
    "series_title",
    "call_number",
    "classification",
    "notes",
    "language_id",
    "gmd_id",
    "publisher_id",
    "publish_place_id",
    "content_type_id",
    "media_type_id",
    "carrier_type_id",
)


class SqliteBibliographyRepository:
    def __init__(self, connection: sqlite3.Connection):
        self._conn = connection

    def add(self, bibliography: Bibliography) -> Bibliography:
        # No commit here: this is called from use cases (AddBibliography) that also
        # link authors in the same logical operation, and control the transaction
        # boundary themselves via UnitOfWork.
        columns = ", ".join(_UPDATABLE_COLUMNS)
        placeholders = ", ".join("?" for _ in _UPDATABLE_COLUMNS)
        values = tuple(getattr(bibliography, column) for column in _UPDATABLE_COLUMNS)
        cursor = self._conn.execute(
            f"INSERT INTO bibliographies ({columns}) VALUES ({placeholders})", values
        )
        new_id = cursor.lastrowid
        assert new_id is not None
        created = self.get_by_id(new_id)
        assert created is not None
        return created

    def update(self, bibliography: Bibliography) -> None:
        # No commit here — see add()'s note; EditBibliography controls the transaction.
        assignments = ", ".join(f"{column} = ?" for column in _UPDATABLE_COLUMNS)
        values = tuple(getattr(bibliography, column) for column in _UPDATABLE_COLUMNS)
        self._conn.execute(
            f"UPDATE bibliographies SET {assignments} WHERE id = ?", (*values, bibliography.id)
        )

    def remove(self, bibliography_id: int) -> None:
        # No FK cascade defined in schema.sql, so the author links have to be cleared
        # explicitly first — items aren't handled here since DeleteBibliography only
        # calls this once list_items() is already empty.
        self._conn.execute("DELETE FROM bibliography_authors WHERE bibliography_id = ?", (bibliography_id,))
        self._conn.execute("DELETE FROM bibliographies WHERE id = ?", (bibliography_id,))
        self._conn.commit()

    def get_by_id(self, bibliography_id: int) -> Bibliography | None:
        row = self._conn.execute("SELECT * FROM bibliographies WHERE id = ?", (bibliography_id,)).fetchone()
        return self._row_to_bibliography(row) if row else None

    def get_by_isbn(self, isbn: str) -> Bibliography | None:
        row = self._conn.execute("SELECT * FROM bibliographies WHERE isbn_issn = ?", (isbn,)).fetchone()
        return self._row_to_bibliography(row) if row else None

    def get_by_call_number(self, call_number: str) -> Bibliography | None:
        row = self._conn.execute("SELECT * FROM bibliographies WHERE call_number = ?", (call_number,)).fetchone()
        return self._row_to_bibliography(row) if row else None

    def count(self, filters: CatalogFilters) -> int:
        where_sql, params = _catalog_query_sql(filters)
        row = self._conn.execute(
            f"SELECT COUNT(*) AS n FROM bibliographies WHERE {where_sql}", params
        ).fetchone()
        return int(row["n"])

    def list_page(
        self, filters: CatalogFilters, *, sort_column: str, sort_descending: bool, page: int, page_size: int
    ) -> list[Bibliography]:
        if sort_column not in _FILTERABLE_COLUMNS:
            raise ValueError(f"Unsortable column: {sort_column!r}")
        where_sql, params = _catalog_query_sql(filters)
        direction = "DESC" if sort_descending else "ASC"
        offset = (page - 1) * page_size
        rows = self._conn.execute(
            f"SELECT bibliographies.* FROM bibliographies WHERE {where_sql} "
            f"ORDER BY bibliographies.{sort_column} {direction}, bibliographies.id ASC LIMIT ? OFFSET ?",
            (*params, page_size, offset),
        ).fetchall()
        return [self._row_to_bibliography(row) for row in rows]

    def add_item(self, bibliography_id: int) -> Item:
        cursor = self._conn.execute("INSERT INTO items (bibliography_id) VALUES (?)", (bibliography_id,))
        self._conn.commit()
        return Item(id=cursor.lastrowid, bibliography_id=bibliography_id)

    def remove_item(self, item_id: int) -> None:
        self._conn.execute("DELETE FROM items WHERE id = ?", (item_id,))
        self._conn.commit()

    def get_item(self, item_id: int) -> Item | None:
        row = self._conn.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
        return Item(id=row["id"], bibliography_id=row["bibliography_id"]) if row else None

    def list_items(self, bibliography_id: int) -> list[Item]:
        rows = self._conn.execute("SELECT * FROM items WHERE bibliography_id = ?", (bibliography_id,)).fetchall()
        return [Item(id=row["id"], bibliography_id=row["bibliography_id"]) for row in rows]

    def set_authors(self, bibliography_id: int, author_ids: list[int]) -> None:
        # No commit here — see add()'s note; the calling use case controls the transaction.
        unique_ids = list(dict.fromkeys(author_ids))
        self._conn.execute("DELETE FROM bibliography_authors WHERE bibliography_id = ?", (bibliography_id,))
        self._conn.executemany(
            "INSERT INTO bibliography_authors (bibliography_id, author_id, level) VALUES (?, ?, ?)",
            [(bibliography_id, author_id, level) for level, author_id in enumerate(unique_ids, start=1)],
        )

    def list_authors(self, bibliography_id: int) -> list[BibliographyAuthor]:
        rows = self._conn.execute(
            """
            SELECT a.id, a.name, ba.level FROM authors a
            JOIN bibliography_authors ba ON ba.author_id = a.id
            WHERE ba.bibliography_id = ?
            ORDER BY ba.level, a.name
            """,
            (bibliography_id,),
        ).fetchall()
        return [
            BibliographyAuthor(author=Author(id=row["id"], name=row["name"]), level=row["level"]) for row in rows
        ]

    @staticmethod
    def _row_to_bibliography(row: sqlite3.Row) -> Bibliography:
        return Bibliography(
            id=row["id"],
            title=row["title"],
            isbn_issn=row["isbn_issn"],
            sor=row["sor"],
            edition=row["edition"],
            publish_year=row["publish_year"],
            collation=row["collation"],
            series_title=row["series_title"],
            call_number=row["call_number"],
            classification=row["classification"],
            notes=row["notes"],
            language_id=row["language_id"],
            gmd_id=row["gmd_id"],
            publisher_id=row["publisher_id"],
            publish_place_id=row["publish_place_id"],
            content_type_id=row["content_type_id"],
            media_type_id=row["media_type_id"],
            carrier_type_id=row["carrier_type_id"],
        )
