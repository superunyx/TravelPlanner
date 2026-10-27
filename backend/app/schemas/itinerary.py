from typing import Literal

from pydantic import BaseModel, Field

TimeSlotType = Literal["morning", "afternoon", "evening", "night"]
ActivityType = Literal["attraction", "dining", "transport", "stay", "activity"]
BudgetStatusType = Literal["under_budget", "on_budget", "over_budget"]


class Activity(BaseModel):
    time_slot: TimeSlotType
    start_time: str
    end_time: str
    title: str
    type: ActivityType
    description: str
    location: str
    est_cost: float = Field(default=0.0, ge=0.0)
    travel_time_from_previous_min: int = Field(default=0, ge=0)
    tips: str = ""


class DayPlan(BaseModel):
    day_number: int = Field(ge=1)
    date: str
    theme: str
    summary: str
    activities: list[Activity] = Field(default_factory=list)
    day_total_cost: float = Field(default=0.0, ge=0.0)


class Accommodation(BaseModel):
    name: str
    area: str
    price_per_night: float = Field(default=0.0, ge=0.0)
    why: str


class Itinerary(BaseModel):
    destination: str
    days: list[DayPlan] = Field(default_factory=list)
    accommodation: Accommodation
    total_estimated_cost: float = Field(default=0.0, ge=0.0)
    budget_status: BudgetStatusType = "on_budget"
    packing_tips: list[str] = Field(default_factory=list)
