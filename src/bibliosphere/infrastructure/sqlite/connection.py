import sqlite3
from importlib import resources
from pathlib import Path


def connect(db_path: str | Path) -> sqlite3.Connection:
    connection = sqlite3.connect(db_path)
    connection.execute("PRAGMA foreign_keys = ON")
    connection.row_factory = sqlite3.Row
    return connection


def init_schema(connection: sqlite3.Connection) -> None:
    schema_sql = resources.files("bibliosphere.infrastructure.sqlite").joinpath("schema.sql").read_text()
    connection.executescript(schema_sql)
    connection.commit()
