"""One-off: bulk-imports bibliographies from a legacy `biblio` CSV export.

Run from the project root: python scripts/import_bibliographies.py <csv_path>

Legacy biblio_id is preserved as bibliographies.id (same rationale as
scripts/import_authors.py) so that a future import of the sibling `biblio_author`
export can join on biblio_id directly. Only rows with a non-blank call_number are
imported: call_number is NOT NULL in schema.sql and is already enforced as
required+unique by AddBibliography/EditBibliography, and 4208 of 4222 rows in the
known 2026-08-15 export have no call_number. Columns with no counterpart in the
bibliographies table (source, image, file_att, opac_hide, promoted, labels,
frequency_id, spec_detail_info, input_date, last_update, uid) are dropped, matching
the "out of v1 scope" list already documented on the bibliographies table in
schema.sql.
"""

import csv
import sys
from pathlib import Path

from bibliosphere.infrastructure.sqlite.connection import connect, init_schema

DB_PATH = Path(__file__).parent.parent / "data" / "bibliosphere.db"

# Ids belonging to pre-import smoke-test bibliographies, safe to remove before import.
KNOWN_TEST_IDS = {1, 2}

INT_COLUMNS = (
    "gmd_id",
    "publisher_id",
    "publish_place_id",
    "content_type_id",
    "media_type_id",
    "carrier_type_id",
)
TEXT_COLUMNS = (
    "title",
    "sor",
    "edition",
    "isbn_issn",
    "publish_year",
    "collation",
    "series_title",
    "call_number",
    "language_id",
    "classification",
    "notes",
)
COLUMNS = ("id", *TEXT_COLUMNS, *INT_COLUMNS)


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python scripts/import_bibliographies.py <csv_path>")
        return 1
    csv_path = Path(sys.argv[1])

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = connect(DB_PATH)
    init_schema(connection)

    existing_ids = {row[0] for row in connection.execute("SELECT id FROM bibliographies")}
    if not existing_ids <= KNOWN_TEST_IDS:
        print("Error: bibliographies table has unexpected existing data; refusing to import.")
        return 1
    removed_ids = sorted(existing_ids)

    rows_read = 0
    rows_skipped = 0
    to_insert: list[tuple[object, ...]] = []

    with csv_path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            rows_read += 1
            call_number = row["call_number"].strip()
            if not call_number:
                rows_skipped += 1
                continue
            values: dict[str, object] = {"id": int(row["biblio_id"])}
            for col in TEXT_COLUMNS:
                values[col] = row[col].strip()
            for col in INT_COLUMNS:
                raw = row[col].strip()
                values[col] = int(raw) if raw else None
            to_insert.append(tuple(values[col] for col in COLUMNS))

    placeholders = ", ".join("?" for _ in COLUMNS)
    with connection:
        if removed_ids:
            connection.execute(
                f"DELETE FROM loans WHERE item_id IN "
                f"(SELECT id FROM items WHERE bibliography_id IN ({','.join('?' * len(removed_ids))}))",
                removed_ids,
            )
            connection.execute(
                f"DELETE FROM items WHERE bibliography_id IN ({','.join('?' * len(removed_ids))})",
                removed_ids,
            )
            connection.execute(
                f"DELETE FROM bibliographies WHERE id IN ({','.join('?' * len(removed_ids))})",
                removed_ids,
            )
        connection.executemany(
            f"INSERT INTO bibliographies ({', '.join(COLUMNS)}) VALUES ({placeholders})",
            to_insert,
        )

    print(f"Read {rows_read} row(s) from {csv_path}.")
    if removed_ids:
        print(f"Removed {len(removed_ids)} pre-import test bibliography row(s): {removed_ids}")
    print(f"Imported {len(to_insert)} bibliography(ies).")
    print(f"Skipped {rows_skipped} row(s) with no call_number.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
