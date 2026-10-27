import datetime as dt
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

PacingType = Literal["relaxed", "moderate", "packed"]
TripStatusType = Literal["draft", "generated"]
MemberRoleType = Literal["owner", "editor", "viewer"]


class TripCreate(BaseModel):
    owner_id: UUID
    title: str
    destination: str
    start_date: dt.date
    end_date: dt.date
    budget: float | None = None
    currency: str = "INR"
    travel_style: str | None = None
    pacing: PacingType = "moderate"
    group_size: int = Field(default=1, ge=1)
    interests: list[str] = Field(default_factory=list)
    preferences: dict[str, Any] = Field(default_factory=dict)
    stay: dict[str, Any] = Field(default_factory=dict)
    status: TripStatusType = "draft"


class TripUpdate(BaseModel):
    title: str | None = None
    destination: str | None = None
    start_date: dt.date | None = None
    end_date: dt.date | None = None
    budget: float | None = None
    currency: str | None = None
    travel_style: str | None = None
    pacing: PacingType | None = None
    group_size: int | None = Field(default=None, ge=1)
    interests: list[str] | None = None
    preferences: dict[str, Any] | None = None
    stay: dict[str, Any] | None = None
    status: TripStatusType | None = None


class TripRecord(BaseModel):
    id: UUID
    owner_id: UUID
    title: str
    destination: str
    start_date: dt.date
    end_date: dt.date
    budget: float | None = None
    currency: str = "INR"
    travel_style: str | None = None
    pacing: PacingType = "moderate"
    group_size: int = 1
    interests: list[str] = Field(default_factory=list)
    preferences: dict[str, Any] = Field(default_factory=dict)
    stay: dict[str, Any] = Field(default_factory=dict)
    status: TripStatusType = "draft"
    created_at: dt.datetime
    updated_at: dt.datetime


class DayUpsert(BaseModel):
    trip_id: UUID
    day_number: int = Field(ge=1)
    date: dt.date | None = None
    summary: str = ""
    items: list[dict[str, Any]] = Field(default_factory=list)
    est_cost: float = 0.0


class DayUpdate(BaseModel):
    date: dt.date | None = None
    summary: str | None = None
    items: list[dict[str, Any]] | None = None
    est_cost: float | None = None


class DayRecord(BaseModel):
    id: UUID
    trip_id: UUID
    day_number: int
    date: dt.date | None = None
    summary: str = ""
    items: list[dict[str, Any]] = Field(default_factory=list)
    est_cost: float = 0.0
