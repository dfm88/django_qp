"""Benchmark test models — pydantic and msgspec equivalents."""

from __future__ import annotations

from datetime import date

import msgspec  # type: ignore[import]
from pydantic import BaseModel, field_validator, model_validator

# === Case 1: Simple (typical filter endpoint) ===


class PydanticSimple(BaseModel):
    """Pydantic model for a simple filter endpoint benchmark."""

    search: str
    page: int
    active: bool
    tags: list[str] | None = None
    category: str | None = None


class MsgspecSimple(msgspec.Struct):
    """Msgspec model for a simple filter endpoint benchmark."""

    search: str
    page: int
    active: bool
    tags: list[str] | None = None
    category: str | None = None


# === Case 2: Complex with custom validation ===


class PydanticComplex(BaseModel):
    """Pydantic model with custom validators for a complex endpoint benchmark."""

    date_from: date
    date_to: date
    min_price: int
    max_price: int
    sort_by: str
    order: str
    status: list[str] | None = None
    limit: int = 10

    @field_validator("limit")
    @classmethod
    def validate_limit(cls, v: int) -> int:
        """Ensure limit is between 1 and 100."""
        if not 1 <= v <= 100:
            raise ValueError("limit must be between 1 and 100")
        return v

    @model_validator(mode="after")
    def validate_ranges(self) -> PydanticComplex:
        """Ensure date_from < date_to and min_price < max_price."""
        if self.date_from >= self.date_to:
            raise ValueError("date_from must be before date_to")
        if self.min_price >= self.max_price:
            raise ValueError("min_price must be less than max_price")
        return self


class MsgspecComplex(msgspec.Struct):
    """Msgspec model with post-init validation for a complex endpoint benchmark."""

    date_from: date
    date_to: date
    min_price: int
    max_price: int
    sort_by: str
    order: str
    status: list[str] | None = None
    limit: int = 10

    def __post_init__(self) -> None:
        """Validate limit range, date ordering, and price ordering."""
        if not 1 <= self.limit <= 100:
            raise ValueError("limit must be between 1 and 100")
        if self.date_from >= self.date_to:
            raise ValueError("date_from must be before date_to")
        if self.min_price >= self.max_price:
            raise ValueError("min_price must be less than max_price")
