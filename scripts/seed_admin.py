"""One-off: creates the first librarian account.

In-app account creation requires an existing librarian (docs/requirements.md §4.5), so
the very first one is created out-of-band by running this script once during setup.
Run from the project root: python scripts/seed_admin.py
"""

import getpass
import sys
from pathlib import Path

from bibliosphere.application.use_cases.create_member import CreateMember
from bibliosphere.domain.entities import Role
from bibliosphere.domain.exceptions import DuplicateUsername
from bibliosphere.infrastructure.sqlite.connection import connect, init_schema
from bibliosphere.infrastructure.sqlite.member_repository import SqliteMemberRepository

DB_PATH = Path(__file__).parent.parent / "data" / "bibliosphere.db"


def main() -> int:
    username = input("Librarian username: ").strip()
    name = input("Librarian name: ").strip()
    password = getpass.getpass("Password: ")
    if not password or password != getpass.getpass("Confirm password: "):
        print("Passwords did not match.")
        return 1

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = connect(DB_PATH)
    init_schema(connection)
    members = SqliteMemberRepository(connection)

    try:
        CreateMember(members).execute(username, name, password, Role.LIBRARIAN)
    except DuplicateUsername as error:
        print(f"Error: {error}")
        return 1

    print(f"Librarian account {username!r} created.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
