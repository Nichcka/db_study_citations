"""
Pydantic schemas for the Article table.

Three schemas follow the Create / Update / Read pattern:
  - ArticleCreate  — payload for POST   /articles
  - ArticleUpdate  — payload for PUT    /articles/{pmid}
  - ArticleRead    — response body (includes all DB fields + computed ones)
"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


# ──────────────────────────────────────────────
# CREATE  (POST /articles)
# ──────────────────────────────────────────────

class ArticleCreate(BaseModel):
    pmid:       int         = Field(..., gt=0, description="PubMed ID, must be positive")
    title:      str         = Field(..., min_length=1, max_length=2000)
    pmc_id:     str | None  = Field(None, max_length=20)
    doi:        str | None  = Field(None, max_length=200)
    pub_year:   int | None  = Field(None, ge=1000, le=2100)
    authors:    str | None  = Field(None, max_length=2000)
    fetched_at: str | None  = Field(
        None,
        pattern=r"^\d{4}-\d{2}-\d{2}$",
        description="ISO date: YYYY-MM-DD",
        examples=["2024-06-01"],
    )

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("title must not be blank")
        return v.strip()


# ──────────────────────────────────────────────
# UPDATE  (PUT /articles/{pmid})
# ──────────────────────────────────────────────

class ArticleUpdate(BaseModel):
    """All fields are optional — only sent fields are updated (PATCH-style PUT)."""

    title:      str | None  = Field(None, min_length=1, max_length=2000)
    pmc_id:     str | None  = Field(None, max_length=20)
    doi:        str | None  = Field(None, max_length=200)
    pub_year:   int | None  = Field(None, ge=1000, le=2100)
    authors:    str | None  = Field(None, max_length=2000)
    fetched_at: str | None  = Field(
        None,
        pattern=r"^\d{4}-\d{2}-\d{2}$",
        description="ISO date: YYYY-MM-DD",
    )

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, v: str | None) -> str | None:
        if v is not None and not v.strip():
            raise ValueError("title must not be blank")
        return v.strip() if v else v


# ──────────────────────────────────────────────
# READ  (response body)
# ──────────────────────────────────────────────

class ArticleRead(BaseModel):
    pmid:       int
    title:      str
    pmc_id:     str | None
    doi:        str | None
    pub_year:   int | None
    authors:    str | None
    fetched_at: str | None

    model_config = {"from_attributes": True}   # allows .model_validate(sqlite3.Row)