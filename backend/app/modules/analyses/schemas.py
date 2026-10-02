from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AnalysisCreate(BaseModel):
    query: str = Field(min_length=3, max_length=120)
    country: Literal["MX", "CO", "AR"]
    category: str | None = Field(default=None, max_length=120)
    period_months: Literal[3, 6, 12]

    @field_validator("query", mode="before")
    @classmethod
    def normalize_query(cls, value: object) -> object:
        return " ".join(value.split()) if isinstance(value, str) else value

    @field_validator("category", mode="before")
    @classmethod
    def normalize_category(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        return " ".join(value.split()) or None


class AnalysisRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    query: str
    country: str
    category: str | None
    period_months: int
    status: str
    created_at: datetime


class AnalysisList(BaseModel):
    items: list[AnalysisRead]
    total: int
    limit: int
    offset: int
