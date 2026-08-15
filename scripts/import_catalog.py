"""One-off: bulk-imports bibliographies and items from a legacy `biblio` + `item`
CSV export pair.

Run from the project root:
    python scripts/import_catalog.py <biblio_csv_path> <item_csv_path>

This supersedes the standalone scripts/import_bibliographies.py for the current
export batch: bibliographies.call_number is NOT NULL and enforced unique by
AddBibliography/EditBibliography, but only 157 of 4728 biblio rows carry a
call_number themselves. The legacy `item` export turns out to be the real source
of truth for most titles -- every one of its 4474 rows has a non-blank
call_number, and it agrees with the biblio-level value in 131/132 cases where
both exist. So call_number is resolved per biblio_id as:

  1. the biblio row's own call_number, if non-blank;
  2. otherwise the most common call_number among that biblio_id's items, if it
     has any (318/320 multi-item biblios agree on one value already; the rare
     disagreements are resolved to the most-common value and reported below for
     manual review, not silently dropped);
  3. otherwise the biblio_id is skipped as a stub (580 titles were never
     accessioned: no call_number and no items).

Resolving call_number this way surfaces 11 cases where two different biblio_ids
land on the same effective call_number -- apparent duplicate cataloging of one
physical title (one biblio_id holds the item(s), its sibling is a call-number-only
stub with zero items). Both sides of every such collision are skipped rather than
guessed at, and reported for manual cataloging cleanup.

Items are imported only for biblio_ids that survive the above; legacy item_id is
preserved as items.id (same rationale as authors/bibliographies imports: lets a
future loan-history import join on item_id directly). No other item column has a
home in the current schema -- items only has (id, bibliography_id), matching the
"no stored status" design in schema.sql.
"""

import csv
import sys
from collections import Counter, defaultdict
from pathlib import Path

from bibliosphere.infrastructure.sqlite.connection import connect, init_schema

DB_PATH = Path(__file__).parent.parent / "data" / "bibliosphere.db"

BIBLIO_TEXT_COLUMNS = (
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
BIBLIO_INT_COLUMNS = (
    "gmd_id",
    "publisher_id",
    "publish_place_id",
    "content_type_id",
    "media_type_id",
    "carrier_type_id",
)
BIBLIO_COLUMNS = ("id", *BIBLIO_TEXT_COLUMNS, *BIBLIO_INT_COLUMNS)


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: python scripts/import_catalog.py <biblio_csv_path> <item_csv_path>")
        return 1
    biblio_csv_path = Path(sys.argv[1])
    item_csv_path = Path(sys.argv[2])

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = connect(DB_PATH)
    init_schema(connection)

    existing_biblios = connection.execute("SELECT COUNT(*) FROM bibliographies").fetchone()[0]
    existing_items = connection.execute("SELECT COUNT(*) FROM items").fetchone()[0]
    if existing_biblios or existing_items:
        print(
            f"Error: bibliographies has {existing_biblios} row(s), items has "
            f"{existing_items} row(s); refusing to import into a non-empty catalog."
        )
        return 1

    with biblio_csv_path.open(newline="", encoding="utf-8") as f:
        biblio_rows = list(csv.DictReader(f))
    with item_csv_path.open(newline="", encoding="utf-8") as f:
        item_rows = list(csv.DictReader(f))

    item_calls_by_biblio: dict[int, list[str]] = defaultdict(list)
    for item_row in item_rows:
        item_calls_by_biblio[int(item_row["biblio_id"])].append(item_row["call_number"].strip())

    effective_call: dict[int, str | None] = {}
    call_source: dict[int, str] = {}
    ambiguous_multi_call: list[tuple[int, Counter[str]]] = []
    for biblio_row in biblio_rows:
        biblio_id = int(biblio_row["biblio_id"])
        own_call = biblio_row["call_number"].strip()
        item_calls = item_calls_by_biblio.get(biblio_id, [])
        if own_call:
            effective_call[biblio_id] = own_call
            call_source[biblio_id] = "biblio"
        elif item_calls:
            counts = Counter(item_calls)
            effective_call[biblio_id] = counts.most_common(1)[0][0]
            call_source[biblio_id] = "item"
            if len(counts) > 1:
                ambiguous_multi_call.append((biblio_id, counts))
        else:
            effective_call[biblio_id] = None
            call_source[biblio_id] = "none"

    biblio_ids_by_call: dict[str, list[int]] = defaultdict(list)
    for biblio_id, call in effective_call.items():
        if call is not None:
            biblio_ids_by_call[call].append(biblio_id)
    collision_biblio_ids: set[int] = set()
    collision_groups: list[list[int]] = []
    for call, biblio_ids in biblio_ids_by_call.items():
        if len(biblio_ids) > 1:
            collision_groups.append(biblio_ids)
            collision_biblio_ids.update(biblio_ids)

    stub_count = sum(1 for call in effective_call.values() if call is None)

    include_ids: set[int] = {
        biblio_id
        for biblio_id, call in effective_call.items()
        if call is not None and biblio_id not in collision_biblio_ids
    }

    to_insert_biblios: list[tuple[object, ...]] = []
    biblio_title = {int(r["biblio_id"]): r["title"].strip() for r in biblio_rows}
    for biblio_row in biblio_rows:
        biblio_id = int(biblio_row["biblio_id"])
        if biblio_id not in include_ids:
            continue
        values: dict[str, object] = {"id": biblio_id}
        for col in BIBLIO_TEXT_COLUMNS:
            values[col] = biblio_row[col].strip()
        values["call_number"] = effective_call[biblio_id]
        for col in BIBLIO_INT_COLUMNS:
            raw = biblio_row[col].strip()
            values[col] = int(raw) if raw else None
        to_insert_biblios.append(tuple(values[col] for col in BIBLIO_COLUMNS))

    to_insert_items: list[tuple[int, int]] = []
    items_skipped = 0
    for item_row in item_rows:
        biblio_id = int(item_row["biblio_id"])
        if biblio_id not in include_ids:
            items_skipped += 1
            continue
        to_insert_items.append((int(item_row["item_id"]), biblio_id))

    placeholders = ", ".join("?" for _ in BIBLIO_COLUMNS)
    with connection:
        connection.executemany(
            f"INSERT INTO bibliographies ({', '.join(BIBLIO_COLUMNS)}) VALUES ({placeholders})",
            to_insert_biblios,
        )
        connection.executemany(
            "INSERT INTO items (id, bibliography_id) VALUES (?, ?)",
            to_insert_items,
        )

    print(f"Read {len(biblio_rows)} biblio row(s) from {biblio_csv_path}.")
    print(f"Read {len(item_rows)} item row(s) from {item_csv_path}.")
    print()
    call_source_counts = Counter(call_source[biblio_id] for biblio_id in include_ids)
    print(f"Imported {len(to_insert_biblios)} bibliography(ies).")
    print(f"  - call_number from biblio row: {call_source_counts['biblio']}")
    print(f"  - call_number backfilled from item row(s): {call_source_counts['item']}")
    print(f"Imported {len(to_insert_items)} item(s).")
    print(f"Skipped {items_skipped} item(s) whose bibliography was excluded.")
    print()
    print(f"Skipped {stub_count} bibliography(ies): no call_number and no items (stub, never accessioned).")
    print(
        f"Skipped {len(collision_biblio_ids)} bibliography(ies) across "
        f"{len(collision_groups)} duplicate-call_number group(s) -- likely the same "
        "title cataloged twice. Manual review needed:"
    )
    for group in collision_groups:
        call = effective_call[group[0]]
        print(f"  call_number {call!r}:")
        for biblio_id in group:
            n_items = len(item_calls_by_biblio.get(biblio_id, []))
            print(f"    biblio_id {biblio_id} ({call_source[biblio_id]}, {n_items} item(s)): {biblio_title[biblio_id]!r}")

    if ambiguous_multi_call:
        print()
        print(
            f"{len(ambiguous_multi_call)} bibliography(ies) had items disagreeing on "
            "call_number; imported using the most common value. Manual review needed:"
        )
        for biblio_id, counts in ambiguous_multi_call:
            print(f"  biblio_id {biblio_id} ({biblio_title[biblio_id]!r}): {dict(counts)} -> used {effective_call[biblio_id]!r}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
