import sqlite3


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
    filter_tax_id: int | None = None,
    filter_pmid: int | None = None,
) -> list[sqlite3.Row]:
    """
    Return rows from Taxon_article.

    Parameters
    ----------
    filter_tax_id : restrict to a specific taxon
    filter_pmid   : restrict to a specific article
    """
    sql = "SELECT * FROM Taxon_article"
    params: list = []
    conditions: list[str] = []

    if filter_tax_id is not None:
        conditions.append("tax_id = ?")
        params.append(filter_tax_id)

    if filter_pmid is not None:
        conditions.append("pmid = ?")
        params.append(filter_pmid)

    if conditions:
        sql += " WHERE " + " AND ".join(conditions)

    with _connect() as conn:
        return conn.execute(sql, params).fetchall()


# ──────────────────────────────────────────────
# JOIN  —  enriched view of the junction
# ──────────────────────────────────────────────

def get_full_links(
    filter_taxon_name: str | None = None,
    filter_title: str | None = None,
    sort_fetched_at: str | None = None,   # "asc" | "desc"
    columns_article: list[str] | None = None,
    columns_taxon: list[str] | None = None,
) -> list[sqlite3.Row]:
    """
    Join Taxon_article with both Taxon and Article and return enriched rows.

    Parameters
    ----------
    filter_taxon_name  : substring match on Taxon.name
    filter_title       : substring match on Article.title
    sort_fetched_at    : "asc" or "desc" — sort by Article.fetched_at
    columns_article    : whitelist of Article columns to include
    columns_taxon      : whitelist of Taxon columns to include
    """
    allowed_article = {"pmid", "pmc_id", "doi", "title", "pub_year", "authors", "fetched_at"}
    allowed_taxon   = {"tax_id", "name", "rank", "parent_tax_id"}

    art_cols = columns_article or list(allowed_article)
    tax_cols = columns_taxon   or list(allowed_taxon)

    invalid_a = set(art_cols) - allowed_article
    invalid_t = set(tax_cols) - allowed_taxon
    if invalid_a:
        raise ValueError(f"Unknown Article column(s): {invalid_a}")
    if invalid_t:
        raise ValueError(f"Unknown Taxon column(s): {invalid_t}")

    a_select = ", ".join(f"a.{c}"  for c in art_cols)
    t_select = ", ".join(f"t.{c}"  for c in tax_cols)
    col_sql  = f"ta.id, {t_select}, {a_select}"

    sql = f"""
        SELECT {col_sql}
        FROM   Taxon_article ta
        JOIN   Taxon         t  ON t.tax_id = ta.tax_id
        JOIN   Article       a  ON a.pmid   = ta.pmid
    """
    params: list = []
    conditions: list[str] = []

    if filter_taxon_name is not None:
        conditions.append("t.name LIKE ?")
        params.append(f"%{filter_taxon_name}%")

    if filter_title is not None:
        conditions.append("a.title LIKE ?")
        params.append(f"%{filter_title}%")

    if conditions:
        sql += " WHERE " + " AND ".join(conditions)

    if sort_fetched_at is not None:
        direction = sort_fetched_at.strip().lower()
        if direction not in ("asc", "desc"):
            raise ValueError("sort_fetched_at must be 'asc' or 'desc'")
        sql += f" ORDER BY a.fetched_at {direction.upper()}"

    with _connect() as conn:
        return conn.execute(sql, params).fetchall()


# ──────────────────────────────────────────────
# INSERT
# ──────────────────────────────────────────────

def add_link(tax_id: int, pmid: int) -> None:
    """
    Link a Taxon to an Article.
    All values are bound as parameters — safe against SQL injection.
    """
    sql = "INSERT INTO Taxon_article (tax_id, pmid) VALUES (?, ?)"
    with _connect() as conn:
        conn.execute(sql, (tax_id, pmid))
        conn.commit()


# ──────────────────────────────────────────────
# DELETE
# ──────────────────────────────────────────────

def delete_link(link_id: int) -> int:
    """
    Delete a Taxon_article row by its surrogate primary key `id`.
    Returns number of rows deleted.
    """
    with _connect() as conn:
        cur = conn.execute("DELETE FROM Taxon_article WHERE id = ?", (link_id,))
        conn.commit()
        return cur.rowcount


def delete_link_by_pair(tax_id: int, pmid: int) -> int:
    """
    Delete a Taxon_article row by the (tax_id, pmid) pair.
    Returns number of rows deleted.
    """
    with _connect() as conn:
        cur = conn.execute(
            "DELETE FROM Taxon_article WHERE tax_id = ? AND pmid = ?",
            (tax_id, pmid),
        )
        conn.commit()
        return cur.rowcount
