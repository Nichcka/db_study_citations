"""
Pydantic schemas for the Taxon_article junction table.

  - TaxonArticleCreate  — payload for POST   /taxon-articles
  - TaxonArticleRead    — response body (flat link)
  - TaxonArticleFull    — enriched response with nested Taxon + Article data
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from .article import ArticleRead
from .taxon   import TaxonRead


# ──────────────────────────────────────────────
# CREATE  (POST /taxon-articles)
# ──────────────────────────────────────────────

class TaxonArticleCreate(BaseModel):
    tax_id: int = Field(..., gt=0, description="Must reference an existing Taxon.tax_id")
    pmid:   int = Field(..., gt=0, description="Must reference an existing Article.pmid")


# ──────────────────────────────────────────────
# READ  — flat link row (response body)
# ──────────────────────────────────────────────

class TaxonArticleRead(BaseModel):
    id:     int
    tax_id: int
    pmid:   int

    model_config = {"from_attributes": True}


# ──────────────────────────────────────────────
# FULL READ  — enriched JOIN response
# ──────────────────────────────────────────────

class TaxonArticleFull(BaseModel):
    """
    Returned when the client requests a JOIN view.
    Nests the full Taxon and Article representations.
    """
    id:      int
    taxon:   TaxonRead
    article: ArticleRead

    model_config = {"from_attributes": True}
