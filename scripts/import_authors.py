"""One-off: bulk-imports authors from a legacy `mst_author` CSV export.

Run from the project root: python scripts/import_authors.py <csv_path>

Legacy author_id is preserved as authors.id (rather than letting SQLite assign fresh
autoincrement ids) so that a future import of the sibling `biblio_author` export can
join on author_id directly, without an id-remapping step. Only author_id and
author_name are carried over: authority_type/auth_list/author_year are empty in every
row of the source export, and input_date/last_update have no corresponding columns in
the authors table (see schema.sql).
"""

import csv
import sys
from pathlib import Path

from bibliosphere.infrastructure.sqlite.connection import connect, init_schema

DB_PATH = Path(__file__).parent.parent / "data" / "bibliosphere.db"


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python scripts/import_authors.py <csv_path>")
        return 1
    csv_path = Path(sys.argv[1])

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = connect(DB_PATH)
    init_schema(connection)

    existing = connection.execute("SELECT COUNT(*) FROM authors").fetchone()[0]
    if existing:
        print(f"Error: authors table already has {existing} row(s); refusing to import.")
        return 1

    rows_read = 0
    rows_imported = 0
    skipped: list[str] = []
    to_insert: list[tuple[int, str]] = []

    with csv_path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            rows_read += 1
            author_id = int(row["author_id"])
            name = row["author_name"].strip()
            if not name:
                skipped.append(f"author_id {author_id}: blank author_name")
                continue
            to_insert.append((author_id, name))

    with connection:
        connection.executemany("INSERT INTO authors (id, name) VALUES (?, ?)", to_insert)
    rows_imported = len(to_insert)

    print(f"Read {rows_read} row(s) from {csv_path}.")
    print(f"Imported {rows_imported} author(s).")
    if skipped:
        print(f"Skipped {len(skipped)} row(s):")
        for reason in skipped:
            print(f"  - {reason}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
