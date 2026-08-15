import sqlite3
from datetime import date

from bibliosphere.domain.entities import Loan
from bibliosphere.domain.ports import LoanHistoryFilters


def _like_param(text: str) -> str:
    escaped = text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def _history_query_sql(filters: LoanHistoryFilters) -> tuple[str, str, list[str]]:
    """Returns (from_sql, where_sql, params). Only joins the tables a given filter
    actually needs — at large data volumes, an unconditional join to resolve
    title/member name makes even an unfiltered COUNT(*) pay a real, avoidable cost.

    LEFT (not INNER) JOIN where used: a loan whose item or member was later deleted
    must still show up in history (as "Unknown", matching ListLoanHistory's
    fallback), not disappear.
    """
    from_sql = "FROM loans"
    if filters.title:
        from_sql += (
            " LEFT JOIN items ON items.id = loans.item_id"
            " LEFT JOIN bibliographies ON bibliographies.id = items.bibliography_id"
        )
    if filters.member_name:
        from_sql += " LEFT JOIN members ON members.id = loans.member_id"

    conditions = []
    params = []

    if filters.member_id:
        conditions.append("loans.member_id LIKE ? ESCAPE '\\'")
        params.append(_like_param(filters.member_id))
    if filters.member_name:
        conditions.append("COALESCE(members.name, 'Unknown') LIKE ? ESCAPE '\\'")
        params.append(_like_param(filters.member_name))
    if filters.title:
        conditions.append("COALESCE(bibliographies.title, 'Unknown') LIKE ? ESCAPE '\\'")
        params.append(_like_param(filters.title))
    if filters.checkout_date:
        conditions.append("loans.checkout_date LIKE ? ESCAPE '\\'")
        params.append(_like_param(filters.checkout_date))
    if filters.checkout_date_from is not None:
        conditions.append("loans.checkout_date >= ?")
        params.append(filters.checkout_date_from.isoformat())
    if filters.checkout_date_to is not None:
        conditions.append("loans.checkout_date <= ?")
        params.append(filters.checkout_date_to.isoformat())
    if filters.due_date:
        conditions.append("loans.due_date LIKE ? ESCAPE '\\'")
        params.append(_like_param(filters.due_date))
    if filters.return_date:
        # An open loan's return_date is NULL, i.e. displays as "" — a non-empty filter
        # here must never match an open loan, mirroring the substring-match UI.
        conditions.append("(loans.return_date IS NOT NULL AND loans.return_date LIKE ? ESCAPE '\\')")
        params.append(_like_param(filters.return_date))

    status_needle = filters.status.strip().lower()
    if status_needle:
        matches_checked_out = status_needle in "checked out"
        matches_returned = status_needle in "returned"
        if matches_checked_out and not matches_returned:
            conditions.append("loans.return_date IS NULL")
        elif matches_returned and not matches_checked_out:
            conditions.append("loans.return_date IS NOT NULL")
        elif not matches_checked_out and not matches_returned:
            conditions.append("0 = 1")
        # else (matches both, e.g. "e"): no constraint — every status contains it.

    where_sql = " AND ".join(conditions) if conditions else "1 = 1"
    return from_sql, where_sql, params


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

    def has_any_loan_for_item(self, item_id: int) -> bool:
        row = self._conn.execute("SELECT 1 FROM loans WHERE item_id = ? LIMIT 1", (item_id,)).fetchone()
        return row is not None

    def has_any_loan_for_member(self, member_id: str) -> bool:
        row = self._conn.execute("SELECT 1 FROM loans WHERE member_id = ? LIMIT 1", (member_id,)).fetchone()
        return row is not None

    def list_open_loans_for_member(self, member_id: str) -> list[Loan]:
        rows = self._conn.execute(
            "SELECT * FROM loans WHERE member_id = ? AND return_date IS NULL ORDER BY due_date", (member_id,)
        ).fetchall()
        return [self._row_to_loan(row) for row in rows]

    def list_all_open_loans(self) -> list[Loan]:
        rows = self._conn.execute("SELECT * FROM loans WHERE return_date IS NULL ORDER BY due_date").fetchall()
        return [self._row_to_loan(row) for row in rows]

    def count_history(self, filters: LoanHistoryFilters) -> int:
        from_sql, where_sql, params = _history_query_sql(filters)
        row = self._conn.execute(f"SELECT COUNT(*) AS n {from_sql} WHERE {where_sql}", params).fetchone()
        return int(row["n"])

    def list_history_page(self, filters: LoanHistoryFilters, *, page: int, page_size: int) -> list[Loan]:
        from_sql, where_sql, params = _history_query_sql(filters)
        offset = (page - 1) * page_size
        rows = self._conn.execute(
            f"SELECT loans.* {from_sql} WHERE {where_sql} "
            "ORDER BY loans.checkout_date DESC, loans.id DESC LIMIT ? OFFSET ?",
            (*params, page_size, offset),
        ).fetchall()
        return [self._row_to_loan(row) for row in rows]

    def count_open_loans_for_member(self, member_id: str) -> int:
        row = self._conn.execute(
            "SELECT COUNT(*) AS n FROM loans WHERE member_id = ? AND return_date IS NULL", (member_id,)
        ).fetchone()
        return int(row["n"])

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
