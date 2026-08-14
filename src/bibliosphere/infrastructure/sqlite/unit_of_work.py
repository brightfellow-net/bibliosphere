import sqlite3


class SqliteUnitOfWork:
    def __init__(self, connection: sqlite3.Connection):
        self._conn = connection

    def __enter__(self) -> "SqliteUnitOfWork":
        return self

    def __exit__(self, exc_type: type[BaseException] | None, exc: BaseException | None, tb: object) -> None:
        if exc_type is None:
            self._conn.commit()
        else:
            self._conn.rollback()
