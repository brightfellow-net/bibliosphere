import os
import sqlite3
import sys
from importlib import resources
from pathlib import Path


def default_db_path(source_path: Path) -> Path:
    """Resolves to `source_path` unless running as a PyInstaller-frozen binary
    (`sys.frozen`, set by PyInstaller at startup), in which case it resolves to the
    OS's standard per-user data directory instead.

    A frozen bundle's own directory isn't a reliable place to keep a writable
    database: it may not be writable at all (e.g. installed under Program Files), and
    for a --onefile build it's a fresh extraction temp dir on every single launch. Both
    composition roots (main.py and scripts/seed_admin.py, packaged as two separate
    executables from the same bibliosphere.spec — see its comments) call this, each
    passing their own source-mode default, so a frozen build of either one always
    resolves to the exact same on-disk file.
    """
    if not getattr(sys, "frozen", False):
        return source_path
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home()))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share")
    return base / "Bibliosphere" / "bibliosphere.db"


def connect(db_path: str | Path) -> sqlite3.Connection:
    connection = sqlite3.connect(db_path)
    connection.execute("PRAGMA foreign_keys = ON")
    connection.row_factory = sqlite3.Row
    return connection


def init_schema(connection: sqlite3.Connection) -> None:
    schema_sql = resources.files("bibliosphere.infrastructure.sqlite").joinpath("schema.sql").read_text()
    connection.executescript(schema_sql)
    connection.commit()
