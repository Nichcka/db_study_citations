"""
Model for the Article table.
All user input is passed via query parameters (?) — never interpolated into SQL strings.
"""

import sqlite3
from typing import Optional


DB_PATH = "data/citations.db"


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row          # rows accessible as dicts
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# ──────────────────────────────────────────────
# SELECT
# ──────────────────────────────────────────────

def get_all(
    columns: list[str] | None = None,
    filter_title: str | None = None,
    sort_fetched_at: str | None = None,   # "asc" | "desc"
) -> list[sqlite3.Row]:
    """
    Return rows from Article.

    Parameters
    ----------
    columns       : list of column names to return, e.g. ["pmid", "title"]
                    Pass None to return all columns.
    filter_title  : substring to match inside `title` (case-insensitive)
    sort_fetched_at : "asc" or "desc" — sort by fetched_at
    """
    allowed_columns = {"pmid", "pmc_id", "doi", "title", "pub_year", "authors", "fetched_at"}

    if columns:
        # Validate every requested column against the whitelist
        invalid = set(columns) - allowed_columns
        if invalid:
            raise ValueError(f"Unknown column(s): {invalid}")
        col_sql = ", ".join(columns)
    else:
        col_sql = "*"

    sql = f"SELECT {col_sql} FROM Article"
    params: list = []

    if filter_title is not None:
        sql += " WHERE title LIKE ?"
        params.append(f"%{filter_title}%")

    if sort_fetched_at is not None:
        direction = sort_fetched_at.strip().lower()
        if direction not in ("asc", "desc"):
            raise ValueError("sort_fetched_at must be 'asc' or 'desc'")
        sql += f" ORDER BY fetched_at {direction.upper()}"

    with _connect() as conn:
        return conn.execute(sql, params).fetchall()


def get_by_pmid(pmid: int) -> sqlite3.Row | None:
    """Return a single Article row by primary key."""
    with _connect() as conn:
        return conn.execute(
            "SELECT * FROM Article WHERE pmid = ?", (pmid,)
        ).fetchone()


# ──────────────────────────────────────────────
# JOIN
# ──────────────────────────────────────────────

def get_articles_by_taxon(tax_id: int) -> list[sqlite3.Row]:
    """
    Return all Articles linked to a given Taxon via Taxon_article.
    Demonstrates a JOIN across all three tables.
    """
    sql = """
        SELECT a.*
        FROM   Article a
        JOIN   Taxon_article ta ON ta.pmid   = a.pmid
        JOIN   Taxon         t  ON t.tax_id  = ta.tax_id
        WHERE  t.tax_id = ?
        ORDER  BY a.pub_year DESC
    """
    with _connect() as conn:
        return conn.execute(sql, (tax_id,)).fetchall()


# ──────────────────────────────────────────────
# INSERT
# ──────────────────────────────────────────────

def add_article(
    pmid: int,
    title: str,
    pmc_id: str | None = None,
    doi: str | None = None,
    pub_year: int | None = None,
    authors: str | None = None,
    fetched_at: str | None = None,
) -> None:
    """
    Insert a new Article row.
    All values are bound as parameters — safe against SQL injection.
    """
    sql = """
        INSERT INTO Article (pmid, pmc_id, doi, title, pub_year, authors, fetched_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """
    with _connect() as conn:
        conn.execute(sql, (pmid, pmc_id, doi, title, pub_year, authors, fetched_at))
        conn.commit()


# ──────────────────────────────────────────────
# DELETE
# ──────────────────────────────────────────────

def delete_article(pmid: int) -> int:
    """
    Delete an Article by pmid.
    Returns the number of rows deleted (0 if the pmid did not exist).
    """
    with _connect() as conn:
        cur = conn.execute("DELETE FROM Article WHERE pmid = ?", (pmid,))
        conn.commit()
        return cur.rowcount