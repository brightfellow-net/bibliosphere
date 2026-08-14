import sqlite3

from bibliosphere.domain.entities import Member, Role


class SqliteMemberRepository:
    def __init__(self, connection: sqlite3.Connection):
        self._conn = connection

    def add(self, member: Member) -> Member:
        cursor = self._conn.execute(
            "INSERT INTO members (username, name, role, password_hash, password_salt) VALUES (?, ?, ?, ?, ?)",
            (member.username, member.name, member.role.value, member.password_hash, member.password_salt),
        )
        self._conn.commit()
        return Member(
            id=cursor.lastrowid,
            username=member.username,
            name=member.name,
            role=member.role,
            password_hash=member.password_hash,
            password_salt=member.password_salt,
        )

    def update(self, member: Member) -> None:
        self._conn.execute(
            "UPDATE members SET username = ?, name = ?, role = ?, password_hash = ?, password_salt = ? WHERE id = ?",
            (member.username, member.name, member.role.value, member.password_hash, member.password_salt, member.id),
        )
        self._conn.commit()

    def get_by_id(self, member_id: int) -> Member | None:
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
        )
