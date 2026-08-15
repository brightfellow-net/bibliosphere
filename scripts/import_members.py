"""One-off: bulk-imports patrons from a legacy `member` CSV export.

Run from the project root: python scripts/import_members.py <csv_path>

All 465 rows in the known 2026-08-15 export have member_type_id=1 (the only value
present), so every row is imported as a Role.PATRON with no username/password — a
patron with neither simply has no self-service login, which is fine for v1. This
bypasses CreateMember (which always sets join_date=date.today()) since a bulk
historical import needs to preserve each member's real join_date (member_since_date
in the export) instead. Legacy member_id is preserved as members.id, matching the
"preserve legacy id" rationale used by the other import scripts, so a future loan
history import can join on member_id directly.

Columns with no counterpart in the members table (gender, member_type_id,
member_mail_address, postal_code, inst_name, is_new, member_image, pin, member_fax,
member_notes, is_pending, mpasswd, last_login, last_login_ip, input_date,
last_update) are dropped. register_date is also dropped: it's identical to
member_since_date in every row of the known export.
"""

import csv
import sys
from datetime import date
from pathlib import Path

from bibliosphere.infrastructure.sqlite.connection import connect, init_schema

DB_PATH = Path(__file__).parent.parent / "data" / "bibliosphere.db"

# Ids belonging to pre-import smoke-test/seed members, safe to leave in place.
KNOWN_SEED_IDS = {"admin"}

COLUMNS = ("id", "name", "role", "birthdate", "email", "phone", "join_date", "expiry_date", "address")


def _date_or_none(value: str) -> str | None:
    value = value.strip()
    return date.fromisoformat(value).isoformat() if value else None


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python scripts/import_members.py <csv_path>")
        return 1
    csv_path = Path(sys.argv[1])

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = connect(DB_PATH)
    init_schema(connection)

    existing_ids = {row[0] for row in connection.execute("SELECT id FROM members")}
    if not existing_ids <= KNOWN_SEED_IDS:
        print("Error: members table has unexpected existing data; refusing to import.")
        return 1

    rows_read = 0
    skipped: list[str] = []
    to_insert: list[tuple[object, ...]] = []

    with csv_path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            rows_read += 1
            member_id = row["member_id"].strip()
            name = row["member_name"].strip()
            if not member_id or not name:
                skipped.append(f"row {rows_read}: blank member_id or member_name")
                continue
            if member_id in existing_ids:
                skipped.append(f"member_id {member_id!r}: already exists")
                continue
            values = {
                "id": member_id,
                "name": name,
                "role": "patron",
                "birthdate": _date_or_none(row["birth_date"]),
                "email": row["member_email"].strip() or None,
                "phone": row["member_phone"].strip() or None,
                "join_date": _date_or_none(row["member_since_date"]),
                "expiry_date": _date_or_none(row["expire_date"]),
                "address": row["member_address"].strip() or None,
            }
            to_insert.append(tuple(values[col] for col in COLUMNS))

    placeholders = ", ".join("?" for _ in COLUMNS)
    with connection:
        connection.executemany(
            f"INSERT INTO members ({', '.join(COLUMNS)}) VALUES ({placeholders})",
            to_insert,
        )

    print(f"Read {rows_read} row(s) from {csv_path}.")
    print(f"Imported {len(to_insert)} patron(s).")
    if skipped:
        print(f"Skipped {len(skipped)} row(s):")
        for reason in skipped:
            print(f"  - {reason}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
