"""
main.py — Citations DB.
Запуск: uvicorn main:app --reload
"""

from fastapi import FastAPI, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from starlette import status

import models.article       as article_model
import models.taxon         as taxon_model
import models.taxon_article as ta_model

from schemas.article       import ArticleCreate
from schemas.taxon         import TaxonCreate
from schemas.taxon_article import TaxonArticleCreate
from pydantic import ValidationError

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="change-me-in-production")
templates = Jinja2Templates(directory="templates")

PER_PAGE = 100

DEFAULT_COLS = {"tax_id", "name", "rank", "pmid", "title", "pub_year", "authors", "fetched_at"}
ALL_COLS     = {"tax_id", "name", "rank", "parent_tax_id",
                "pmid", "pmc_id", "doi", "title", "pub_year", "authors", "fetched_at"}

# Все фильтруемые колонки
FILTER_COLS = ["tax_id", "name", "rank", "parent_tax_id",
               "pmid", "pmc_id", "doi", "title", "pub_year", "authors", "fetched_at"]


# ── helpers ───────────────────────────────────────────────────────────────────

def flash(request: Request, message: str, category: str = "success"):
    request.session.setdefault("_flashes", []).append((category, message))

def get_flashed_messages(request: Request):
    return request.session.pop("_flashes", [])

def render(request: Request, context: dict):
    context["get_flashed_messages"] = lambda with_categories=False: (
        get_flashed_messages(request) if with_categories
        else [m for _, m in get_flashed_messages(request)]
    )
    macro_tpl = templates.env.get_template("macros.html")
    context["pagination"] = macro_tpl.module.pagination
    return templates.TemplateResponse(request=request, name="index.html", context=context)

def redirect_home():
    return RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)

def paginate(rows: list, page: int) -> tuple:
    total = len(rows)
    total_pages = max(1, (total + PER_PAGE - 1) // PER_PAGE)
    page = max(1, min(page, total_pages))
    return rows[(page - 1) * PER_PAGE: page * PER_PAGE], total, total_pages, page


# ── INDEX ─────────────────────────────────────────────────────────────────────

@app.get("/", name="index")
def index(
    request: Request,
    f_sort: str = "",
    f_has_pmc: str = "",
    page: int = 1,
    cols: list[str] = [],
    # per-column filters
    f_tax_id:        str = "",
    f_name:          str = "",
    f_rank:          str = "",
    f_parent_tax_id: str = "",
    f_pmid:          str = "",
    f_pmc_id:        str = "",
    f_doi:           str = "",
    f_title:         str = "",
    f_pub_year:      str = "",
    f_authors:       str = "",
    f_fetched_at:    str = "",
):
    # Видимые колонки
    if cols:
        visible = set(cols) & ALL_COLS
        request.session["visible_cols"] = list(visible)
    elif "visible_cols" in request.session:
        visible = set(request.session["visible_cols"]) & ALL_COLS
    else:
        visible = DEFAULT_COLS

    filters = {
        "tax_id":        f_tax_id,
        "name":          f_name,
        "rank":          f_rank,
        "parent_tax_id": f_parent_tax_id,
        "pmid":          f_pmid,
        "pmc_id":        f_pmc_id,
        "doi":           f_doi,
        "title":         f_title,
        "pub_year":      f_pub_year,
        "authors":       f_authors,
        "fetched_at":    f_fetched_at,
    }

    rows = ta_model.get_full_links(
        filter_taxon_name=f_name or None,
        filter_title=f_title or None,
        sort_fetched_at=f_sort or None,
    )

    # Доп. фильтры Python-side
    for col, val in filters.items():
        if not val or col in ("name", "title"):
            continue
        val_lower = val.lower()
        rows = [r for r in rows if r[col] is not None and val_lower in str(r[col]).lower()]

    if f_has_pmc:
        rows = [r for r in rows if r["pmc_id"]]

    page_rows, total, total_pages, page = paginate(rows, page)

    param_parts = [("f_sort", f_sort), ("f_has_pmc", f_has_pmc)] + [(f"f_{k}", v) for k, v in filters.items()]
    params = "&".join(f"{k}={v}" for k, v in param_parts if v)

    active_filters = any(filters.values()) or bool(f_has_pmc)

    return render(request, {
        "rows": page_rows,
        "page": page, "total": total, "total_pages": total_pages,
        "pagination_params": params,
        "visible_cols": visible,
        "f_sort": f_sort,
        "f_has_pmc": f_has_pmc,
        "filters": filters,
        "active_filters": active_filters,
    })


# ── ADD FULL ──────────────────────────────────────────────────────────────────

@app.post("/add-full")
async def add_full(
    request: Request,
    tax_id:        int        = Form(...),
    pmid:          int        = Form(...),
    name:          str        = Form(...),
    rank:          str        = Form(...),
    title:         str        = Form(...),
    parent_tax_id: int | None = Form(None),
    doi:           str | None = Form(None),
    pmc_id:        str | None = Form(None),
    pub_year:      int | None = Form(None),
    authors:       str | None = Form(None),
    fetched_at:    str | None = Form(None),
):
    try:
        # 1. Таксон
        taxon_data = TaxonCreate(tax_id=tax_id, name=name, rank=rank,
                                 parent_tax_id=parent_tax_id)
        taxon_model.add_taxon(**taxon_data.model_dump())

        # 2. Статья
        article_data = ArticleCreate(pmid=pmid, title=title, doi=doi or None,
                                     pmc_id=pmc_id or None, pub_year=pub_year,
                                     authors=authors or None, fetched_at=fetched_at or None)
        article_model.add_article(**article_data.model_dump())

        # 3. Связь — tax_id и pmid подтягиваются автоматически
        link = TaxonArticleCreate(tax_id=tax_id, pmid=pmid)
        ta_model.add_link(**link.model_dump())

        flash(request, f"Добавлено: таксон «{name}», статья PMID {pmid}, связь создана.", "success")
    except ValidationError as e:
        flash(request, f"Ошибка валидации: {e.errors()[0]['msg']}", "danger")
    except Exception as e:
        flash(request, f"Ошибка: {e}", "danger")
    return redirect_home()


# ── DELETE LINK ───────────────────────────────────────────────────────────────

@app.post("/taxon-articles/{link_id}/delete")
async def taxon_article_delete(request: Request, link_id: int):
    try:
        ta_model.delete_link(link_id)
        flash(request, f"Связь #{link_id} удалена.", "warning")
    except Exception as e:
        flash(request, f"Ошибка: {e}", "danger")
    return redirect_home()
