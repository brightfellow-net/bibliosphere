"""One-off: creates the first librarian account.

In-app account creation requires an existing librarian (docs/requirements.md §4.5), so
the very first one is created out-of-band by running this script once during setup.
Run from the project root: python scripts/seed_admin.py
"""

import getpass
import sys
from pathlib import Path

from bibliosphere.application.use_cases.create_member import CreateMember
from bibliosphere.application.use_cases.generate_member_id import GenerateMemberId
from bibliosphere.domain.entities import Role
from bibliosphere.domain.exceptions import BibliosphereError
from bibliosphere.infrastructure.sqlite.connection import connect, default_db_path, init_schema
from bibliosphere.infrastructure.sqlite.member_repository import SqliteMemberRepository

# Resolves to the exact same file main.py's frozen build would use — see
# default_db_path's docstring — so running this (also packaged as its own frozen
# executable, see bibliosphere.spec) actually seeds the database the app will open.
DB_PATH = default_db_path(Path(__file__).parent.parent / "data" / "bibliosphere.db")


def main() -> int:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = connect(DB_PATH)
    init_schema(connection)
    members = SqliteMemberRepository(connection)

    suggested_id = GenerateMemberId(members).execute()
    member_id = input(f"Member ID [{suggested_id}]: ").strip() or suggested_id
    username = input("Librarian username: ").strip()
    name = input("Librarian name: ").strip()
    password = getpass.getpass("Password: ")
    if not password or password != getpass.getpass("Confirm password: "):
        print("Passwords did not match.")
        return 1

    try:
        CreateMember(members).execute(member_id, username, name, password, Role.LIBRARIAN)
    except BibliosphereError as error:
        print(f"Error: {error}")
        return 1

    print(f"Librarian account {username!r} created (member id {member_id!r}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
