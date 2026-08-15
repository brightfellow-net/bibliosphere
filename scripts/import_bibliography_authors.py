"""One-off: bulk-imports bibliography/author links from a legacy `biblio_author` CSV.

Run from the project root: python scripts/import_bibliography_authors.py <csv_path>

The CSV's biblio_id range (1-4223, from data/import/biblio_202608150951.csv) is wider
than what's actually in the bibliographies table: scripts/import_bibliographies.py only
imported the 14 rows that had a call_number. Rows here referencing a biblio_id that
was never imported (e.g. 4225-4239, which aren't even in the source biblio export) are
skipped rather than failing the whole import, since bibliography_id/author_id are
foreign keys into tables that only carry a subset of the legacy data.
"""

import csv
import sys
from pathlib import Path

from bibliosphere.infrastructure.sqlite.connection import connect, init_schema

DB_PATH = Path(__file__).parent.parent / "data" / "bibliosphere.db"


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python scripts/import_bibliography_authors.py <csv_path>")
        return 1
    csv_path = Path(sys.argv[1])

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = connect(DB_PATH)
    init_schema(connection)

    existing = connection.execute("SELECT COUNT(*) FROM bibliography_authors").fetchone()[0]
    if existing:
        print(f"Error: bibliography_authors table already has {existing} row(s); refusing to import.")
        return 1

    bibliography_ids = {row[0] for row in connection.execute("SELECT id FROM bibliographies")}
    author_ids = {row[0] for row in connection.execute("SELECT id FROM authors")}

    rows_read = 0
    skipped: list[str] = []
    to_insert: list[tuple[int, int, int]] = []

    with csv_path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if not row["biblio_id"]:
                continue
            rows_read += 1
            biblio_id = int(row["biblio_id"])
            author_id = int(row["author_id"])
            level = int(row["level"])
            if biblio_id not in bibliography_ids:
                skipped.append(f"biblio_id {biblio_id}, author_id {author_id}: no such bibliography")
                continue
            if author_id not in author_ids:
                skipped.append(f"biblio_id {biblio_id}, author_id {author_id}: no such author")
                continue
            to_insert.append((biblio_id, author_id, level))

    with connection:
        connection.executemany(
            "INSERT INTO bibliography_authors (bibliography_id, author_id, level) VALUES (?, ?, ?)",
            to_insert,
        )

    print(f"Read {rows_read} row(s) from {csv_path}.")
    print(f"Imported {len(to_insert)} bibliography-author link(s).")
    if skipped:
        print(f"Skipped {len(skipped)} row(s):")
        for reason in skipped:
            print(f"  - {reason}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
