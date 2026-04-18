import sqlite3
from typing import Optional


DB_PATH = "data/citations.db"


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# ──────────────────────────────────────────────
# SELECT
# ──────────────────────────────────────────────

def get_all(
    columns: list[str] | None = None,
    filter_name: str | None = None,
    filter_rank: str | None = None,
) -> list[sqlite3.Row]:
    """
    Return rows from Taxon.

    Parameters
    ----------
    columns     : column whitelist, e.g. ["tax_id", "name"]
    filter_name : substring match on `name` (case-insensitive)
    filter_rank : exact match on `rank`, e.g. "genus", "species"
    """
    allowed_columns = {"tax_id", "name", "rank", "parent_tax_id"}

    if columns:
        invalid = set(columns) - allowed_columns
        if invalid:
            raise ValueError(f"Unknown column(s): {invalid}")
        col_sql = ", ".join(columns)
    else:
        col_sql = "*"

    sql = f"SELECT {col_sql} FROM Taxon"
    params: list = []
    conditions: list[str] = []

    if filter_name is not None:
        conditions.append("name LIKE ?")
        params.append(f"%{filter_name}%")

    if filter_rank is not None:
        conditions.append("rank = ?")
        params.append(filter_rank)

    if conditions:
        sql += " WHERE " + " AND ".join(conditions)

    with _connect() as conn:
        return conn.execute(sql, params).fetchall()


def get_by_tax_id(tax_id: int) -> sqlite3.Row | None:
    """Return a single Taxon row by primary key."""
    with _connect() as conn:
        return conn.execute(
            "SELECT * FROM Taxon WHERE tax_id = ?", (tax_id,)
        ).fetchone()


# ──────────────────────────────────────────────
# JOIN
# ──────────────────────────────────────────────

def get_taxa_by_article(pmid: int) -> list[sqlite3.Row]:
    """
    Return all Taxa linked to a given Article via Taxon_article.
    """
    sql = """
        SELECT t.*
        FROM   Taxon t
        JOIN   Taxon_article ta ON ta.tax_id = t.tax_id
        JOIN   Article       a  ON a.pmid    = ta.pmid
        WHERE  a.pmid = ?
        ORDER  BY t.name ASC
    """
    with _connect() as conn:
        return conn.execute(sql, (pmid,)).fetchall()


# ──────────────────────────────────────────────
# INSERT
# ──────────────────────────────────────────────

def add_taxon(
    tax_id: int,
    name: str,
    rank: str,
    parent_tax_id: int | None = None,
) -> None:
    """
    Insert a new Taxon row.
    All values are bound as parameters — safe against SQL injection.
    """
    sql = """
        INSERT INTO Taxon (tax_id, name, rank, parent_tax_id)
        VALUES (?, ?, ?, ?)
    """
    with _connect() as conn:
        conn.execute(sql, (tax_id, name, rank, parent_tax_id))
        conn.commit()


# ──────────────────────────────────────────────
# DELETE
# ──────────────────────────────────────────────

def delete_taxon(tax_id: int) -> int:
    """
    Delete a Taxon by tax_id.
    Returns the number of rows deleted (0 if not found).
    """
    with _connect() as conn:
        cur = conn.execute("DELETE FROM Taxon WHERE tax_id = ?", (tax_id,))
        conn.commit()
        return cur.rowcount
