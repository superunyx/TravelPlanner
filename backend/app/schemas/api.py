import datetime as dt
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

PacingType = Literal["relaxed", "moderate", "packed"]
TripStatusType = Literal["draft", "generated"]
RoleType = Literal["editor", "viewer"]


class CreateTripRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=120, examples=["Golden Triangle Highlights"])
    destination: str = Field(..., min_length=2, max_length=120, examples=["Jaipur, India"])
    start_date: dt.date = Field(..., examples=["2026-11-10"])
    end_date: dt.date = Field(..., examples=["2026-11-14"])
    budget: float = Field(..., gt=0, examples=[50000.0])
    currency: str = Field(default="INR", min_length=3, max_length=5, examples=["INR"])
    travel_style: str | None = Field(default="balanced", examples=["cultural"])
    pacing: PacingType = Field(default="moderate", examples=["moderate"])
    group_size: int = Field(default=2, ge=1, le=20, examples=[2])
    interests: list[str] = Field(default_factory=list, examples=[["architecture", "food", "history"]])
    preferences: dict[str, Any] = Field(default_factory=dict, examples=[{"diet": "vegetarian"}])
    stay: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_dates(self) -> "CreateTripRequest":
        if self.end_date < self.start_date:
            raise ValueError("end_date must be greater than or equal to start_date")
        days_count = (self.end_date - self.start_date).days + 1
        if days_count > 14:
            raise ValueError(f"Trip duration cannot exceed 14 days (requested {days_count} days)")
        return self


class UpdateTripRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=120)
    destination: str | None = Field(default=None, min_length=2, max_length=120)
    start_date: dt.date | None = None
    end_date: dt.date | None = None
    budget: float | None = Field(default=None, gt=0)
    currency: str | None = Field(default=None, min_length=3, max_length=5)
    travel_style: str | None = None
    pacing: PacingType | None = None
    group_size: int | None = Field(default=None, ge=1, le=20)
    interests: list[str] | None = None
    preferences: dict[str, Any] | None = None
    stay: dict[str, Any] | None = None

    @model_validator(mode="after")
    def validate_dates(self) -> "UpdateTripRequest":
        if self.start_date and self.end_date:
            if self.end_date < self.start_date:
                raise ValueError("end_date must be greater than or equal to start_date")
            days_count = (self.end_date - self.start_date).days + 1
            if days_count > 14:
                raise ValueError(f"Trip duration cannot exceed 14 days (requested {days_count} days)")
        return self


class RegenerateDayRequest(BaseModel):
    instruction: str | None = Field(
        default=None,
        max_length=500,
        examples=["Focus on traditional craft markets and street food."],
    )


class UpdateDayRequest(BaseModel):
    summary: str | None = None
    items: list[dict[str, Any]] | None = None
    est_cost: float | None = Field(default=None, ge=0)


class AddMemberRequest(BaseModel):
    email: str = Field(
        ...,
        pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
        examples=["partner@example.com"],
    )
    role: RoleType = Field(default="editor", examples=["editor"])


class MemberResponse(BaseModel):
    trip_id: UUID
    user_id: UUID
    email: str | None = None
    role: str


class CategoryCostBreakdown(BaseModel):
    category: str
    total_cost: float
    percentage: float


class TripSummaryResponse(BaseModel):
    trip_id: UUID
    currency: str
    budget: float | None
    total_estimated_cost: float
    accommodation_cost: float
    activities_cost: float
    budget_status: str
    difference: float
    categories: list[CategoryCostBreakdown]
