import sqlite3

from bibliosphere.domain.entities import Author


class SqliteAuthorRepository:
    def __init__(self, connection: sqlite3.Connection):
        self._conn = connection

    def add(self, author: Author) -> Author:
        cursor = self._conn.execute("INSERT INTO authors (name) VALUES (?)", (author.name,))
        self._conn.commit()
        return Author(id=cursor.lastrowid, name=author.name)

    def get_by_id(self, author_id: int) -> Author | None:
        row = self._conn.execute("SELECT * FROM authors WHERE id = ?", (author_id,)).fetchone()
        return Author(id=row["id"], name=row["name"]) if row else None

    def get_by_name(self, name: str) -> Author | None:
        row = self._conn.execute("SELECT * FROM authors WHERE name = ?", (name,)).fetchone()
        return Author(id=row["id"], name=row["name"]) if row else None

    def list_all(self) -> list[Author]:
        rows = self._conn.execute("SELECT * FROM authors ORDER BY name").fetchall()
        return [Author(id=row["id"], name=row["name"]) for row in rows]

    def find_or_create_by_name(self, name: str) -> Author:
        existing = self.get_by_name(name)
        if existing is not None:
            return existing
        return self.add(Author(id=None, name=name))
