from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

# Allowed biological ranks — extend this list as needed
ALLOWED_RANKS = {
    "domain", "kingdom", "phylum", "class", "order",
    "family", "genus", "species", "subspecies", "strain",
}


# ──────────────────────────────────────────────
# CREATE  (POST /taxa)
# ──────────────────────────────────────────────

class TaxonCreate(BaseModel):
    tax_id:        int         = Field(..., gt=0, description="NCBI Taxonomy ID")
    name:          str         = Field(..., min_length=1, max_length=300)
    rank:          str         = Field(..., description=f"One of: {sorted(ALLOWED_RANKS)}")
    parent_tax_id: int | None  = Field(None, gt=0)

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("name must not be blank")
        return v.strip()

    @field_validator("rank")
    @classmethod
    def rank_allowed(cls, v: str) -> str:
        v = v.strip().lower()
        if v not in ALLOWED_RANKS:
            raise ValueError(f"rank '{v}' is not allowed. Choose from: {sorted(ALLOWED_RANKS)}")
        return v


# ──────────────────────────────────────────────
# UPDATE  (PUT /taxa/{tax_id})
# ──────────────────────────────────────────────

class TaxonUpdate(BaseModel):
    """All fields are optional — only sent fields are updated."""

    name:          str | None  = Field(None, min_length=1, max_length=300)
    rank:          str | None  = None
    parent_tax_id: int | None  = Field(None, gt=0)

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, v: str | None) -> str | None:
        if v is not None and not v.strip():
            raise ValueError("name must not be blank")
        return v.strip() if v else v

    @field_validator("rank")
    @classmethod
    def rank_allowed(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip().lower()
        if v not in ALLOWED_RANKS:
            raise ValueError(f"rank '{v}' is not allowed. Choose from: {sorted(ALLOWED_RANKS)}")
        return v


# ──────────────────────────────────────────────
# READ  (response body)
# ──────────────────────────────────────────────

class TaxonRead(BaseModel):
    tax_id:        int
    name:          str
    rank:          str
    parent_tax_id: int | None

    model_config = {"from_attributes": True}
