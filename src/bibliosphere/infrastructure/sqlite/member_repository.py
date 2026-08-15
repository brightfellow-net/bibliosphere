import sqlite3
from datetime import date

from bibliosphere.domain.entities import Member, Role


class SqliteMemberRepository:
    def __init__(self, connection: sqlite3.Connection):
        self._conn = connection

    def add(self, member: Member) -> Member:
        # member.id is caller-supplied (see Member's docstring), not DB-assigned.
        self._conn.execute(
            """
            INSERT INTO members (
                id, username, name, role, password_hash, password_salt,
                birthdate, email, phone, join_date, expiry_date, address
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                member.id,
                member.username,
                member.name,
                member.role.value,
                member.password_hash,
                member.password_salt,
                member.birthdate.isoformat() if member.birthdate else None,
                member.email,
                member.phone,
                member.join_date.isoformat() if member.join_date else None,
                member.expiry_date.isoformat() if member.expiry_date else None,
                member.address,
            ),
        )
        self._conn.commit()
        return member

    def update(self, member: Member) -> None:
        self._conn.execute(
            """
            UPDATE members SET
                username = ?, name = ?, role = ?, password_hash = ?, password_salt = ?,
                birthdate = ?, email = ?, phone = ?, join_date = ?, expiry_date = ?, address = ?
            WHERE id = ?
            """,
            (
                member.username,
                member.name,
                member.role.value,
                member.password_hash,
                member.password_salt,
                member.birthdate.isoformat() if member.birthdate else None,
                member.email,
                member.phone,
                member.join_date.isoformat() if member.join_date else None,
                member.expiry_date.isoformat() if member.expiry_date else None,
                member.address,
                member.id,
            ),
        )
        self._conn.commit()

    def remove(self, member_id: str) -> None:
        self._conn.execute("DELETE FROM members WHERE id = ?", (member_id,))
        self._conn.commit()

    def get_by_id(self, member_id: str) -> Member | None:
        row = self._conn.execute("SELECT * FROM members WHERE id = ?", (member_id,)).fetchone()
        return self._row_to_member(row) if row else None

    def get_by_username(self, username: str) -> Member | None:
        row = self._conn.execute("SELECT * FROM members WHERE username = ?", (username,)).fetchone()
        return self._row_to_member(row) if row else None

    def list_all(self) -> list[Member]:
        rows = self._conn.execute("SELECT * FROM members ORDER BY name").fetchall()
        return [self._row_to_member(row) for row in rows]

    @staticmethod
    def _row_to_member(row: sqlite3.Row) -> Member:
        return Member(
            id=row["id"],
            username=row["username"],
            name=row["name"],
            role=Role(row["role"]),
            password_hash=row["password_hash"],
            password_salt=row["password_salt"],
            birthdate=date.fromisoformat(row["birthdate"]) if row["birthdate"] else None,
            email=row["email"],
            phone=row["phone"],
            join_date=date.fromisoformat(row["join_date"]) if row["join_date"] else None,
            expiry_date=date.fromisoformat(row["expiry_date"]) if row["expiry_date"] else None,
            address=row["address"],
        )
