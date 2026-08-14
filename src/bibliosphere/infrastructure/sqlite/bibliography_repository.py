import sqlite3

from bibliosphere.domain.entities import Author, Bibliography, Item

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
        columns = ", ".join(_UPDATABLE_COLUMNS)
        placeholders = ", ".join("?" for _ in _UPDATABLE_COLUMNS)
        values = tuple(getattr(bibliography, column) for column in _UPDATABLE_COLUMNS)
        cursor = self._conn.execute(
            f"INSERT INTO bibliographies ({columns}) VALUES ({placeholders})", values
        )
        self._conn.commit()
        return self.get_by_id(cursor.lastrowid)

    def update(self, bibliography: Bibliography) -> None:
        assignments = ", ".join(f"{column} = ?" for column in _UPDATABLE_COLUMNS)
        values = tuple(getattr(bibliography, column) for column in _UPDATABLE_COLUMNS)
        self._conn.execute(
            f"UPDATE bibliographies SET {assignments} WHERE id = ?", (*values, bibliography.id)
        )
        self._conn.commit()

    def get_by_id(self, bibliography_id: int) -> Bibliography | None:
        row = self._conn.execute("SELECT * FROM bibliographies WHERE id = ?", (bibliography_id,)).fetchone()
        return self._row_to_bibliography(row) if row else None

    def get_by_isbn(self, isbn: str) -> Bibliography | None:
        row = self._conn.execute("SELECT * FROM bibliographies WHERE isbn_issn = ?", (isbn,)).fetchone()
        return self._row_to_bibliography(row) if row else None

    def search(self, query: str) -> list[Bibliography]:
        like = f"%{query}%"
        rows = self._conn.execute(
            """
            SELECT DISTINCT b.* FROM bibliographies b
            LEFT JOIN bibliography_authors ba ON ba.bibliography_id = b.id
            LEFT JOIN authors a ON a.id = ba.author_id
            WHERE b.title LIKE ? OR b.isbn_issn LIKE ? OR a.name LIKE ?
            ORDER BY b.title
            """,
            (like, like, like),
        ).fetchall()
        return [self._row_to_bibliography(row) for row in rows]

    def list_all(self) -> list[Bibliography]:
        rows = self._conn.execute("SELECT * FROM bibliographies ORDER BY title").fetchall()
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
        self._conn.execute("DELETE FROM bibliography_authors WHERE bibliography_id = ?", (bibliography_id,))
        self._conn.executemany(
            "INSERT INTO bibliography_authors (bibliography_id, author_id) VALUES (?, ?)",
            [(bibliography_id, author_id) for author_id in author_ids],
        )
        self._conn.commit()

    def list_authors(self, bibliography_id: int) -> list[Author]:
        rows = self._conn.execute(
            """
            SELECT a.* FROM authors a
            JOIN bibliography_authors ba ON ba.author_id = a.id
            WHERE ba.bibliography_id = ?
            ORDER BY a.name
            """,
            (bibliography_id,),
        ).fetchall()
        return [Author(id=row["id"], name=row["name"]) for row in rows]

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
