import sqlite3
from datetime import date

from bibliosphere.domain.entities import Loan


class SqliteLoanRepository:
    def __init__(self, connection: sqlite3.Connection):
        self._conn = connection

    def add(self, loan: Loan) -> Loan:
        cursor = self._conn.execute(
            "INSERT INTO loans (item_id, member_id, checkout_date, due_date, return_date) VALUES (?, ?, ?, ?, ?)",
            (loan.item_id, loan.member_id, loan.checkout_date.isoformat(), loan.due_date.isoformat(), None),
        )
        self._conn.commit()
        return Loan(
            id=cursor.lastrowid,
            item_id=loan.item_id,
            member_id=loan.member_id,
            checkout_date=loan.checkout_date,
            due_date=loan.due_date,
            return_date=None,
        )

    def update(self, loan: Loan) -> None:
        self._conn.execute(
            "UPDATE loans SET item_id = ?, member_id = ?, checkout_date = ?, due_date = ?, return_date = ? WHERE id = ?",
            (
                loan.item_id,
                loan.member_id,
                loan.checkout_date.isoformat(),
                loan.due_date.isoformat(),
                loan.return_date.isoformat() if loan.return_date else None,
                loan.id,
            ),
        )
        self._conn.commit()

    def get_by_id(self, loan_id: int) -> Loan | None:
        row = self._conn.execute("SELECT * FROM loans WHERE id = ?", (loan_id,)).fetchone()
        return self._row_to_loan(row) if row else None

    def get_open_loan_for_item(self, item_id: int) -> Loan | None:
        row = self._conn.execute(
            "SELECT * FROM loans WHERE item_id = ? AND return_date IS NULL", (item_id,)
        ).fetchone()
        return self._row_to_loan(row) if row else None

    def list_open_loans_for_member(self, member_id: int) -> list[Loan]:
        rows = self._conn.execute(
            "SELECT * FROM loans WHERE member_id = ? AND return_date IS NULL ORDER BY due_date", (member_id,)
        ).fetchall()
        return [self._row_to_loan(row) for row in rows]

    def list_all_open_loans(self) -> list[Loan]:
        rows = self._conn.execute("SELECT * FROM loans WHERE return_date IS NULL ORDER BY due_date").fetchall()
        return [self._row_to_loan(row) for row in rows]

    def count_open_loans_for_member(self, member_id: int) -> int:
        row = self._conn.execute(
            "SELECT COUNT(*) AS n FROM loans WHERE member_id = ? AND return_date IS NULL", (member_id,)
        ).fetchone()
        return row["n"]

    @staticmethod
    def _row_to_loan(row: sqlite3.Row) -> Loan:
        return Loan(
            id=row["id"],
            item_id=row["item_id"],
            member_id=row["member_id"],
            checkout_date=date.fromisoformat(row["checkout_date"]),
            due_date=date.fromisoformat(row["due_date"]),
            return_date=date.fromisoformat(row["return_date"]) if row["return_date"] else None,
        )
