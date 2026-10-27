import json
import logging
from datetime import timedelta
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from app.core.cache import generation_cache
from app.core.errors import AppError
from app.schemas.db import TripRecord
from app.schemas.itinerary import DayPlan, Itinerary
from app.services.ai.gemini_provider import GeminiProvider
from app.services.ai.prompts import (
    SYSTEM_PROMPT,
    build_full_itinerary_prompt,
    build_regenerate_day_prompt,
)
from app.services.ai.provider import LLMProvider

logger = logging.getLogger("travel_planner.itinerary_service")
T = TypeVar("T", bound=BaseModel)

PACING_LIMITS: dict[str, int] = {
    "relaxed": 4,
    "moderate": 5,
    "packed": 6,
}


def optimize_day_geographic_order(day: DayPlan) -> DayPlan:
    """Sort activities logically by location/area and recompute realistic travel times."""
    if len(day.activities) <= 1:
        return day

    # Group activities by location area to minimize crisscrossing
    sorted_activities = sorted(
        day.activities,
        key=lambda act: (act.location.lower().strip(), act.start_time),
    )

    # Recompute travel time estimates based on location proximity
    previous_loc = None
    for idx, act in enumerate(sorted_activities):
        if idx == 0:
            act.travel_time_from_previous_min = 0
        elif previous_loc and previous_loc.lower() == act.location.lower():
            act.travel_time_from_previous_min = 5
        else:
            act.travel_time_from_previous_min = 20
        previous_loc = act.location

    day.activities = sorted_activities
    return day


def post_process_day(day: DayPlan, pacing: str = "moderate") -> DayPlan:
    """Reorder geographically, enforce pacing limits, and recompute costs."""
    day = optimize_day_geographic_order(day)

    # Recompute day cost directly from activities
    calculated_day_cost = sum(act.est_cost for act in day.activities)
    day.day_total_cost = round(calculated_day_cost, 2)

    # Flag days with more than pacing limit
    max_allowed = PACING_LIMITS.get(pacing, 5)
    if len(day.activities) > max_allowed:
        day.summary += f" [Note: Pacing alert - {len(day.activities)} activities exceed {pacing} target of {max_allowed}]"

    return day


def post_process_itinerary(itinerary: Itinerary, trip: TripRecord) -> Itinerary:
    """Recompute all day costs and total_estimated_cost from activities; evaluate budget status."""
    total_activities_cost = 0.0

    for day in itinerary.days:
        post_process_day(day, trip.pacing)
        total_activities_cost += day.day_total_cost

    num_days = max((trip.end_date - trip.start_date).days + 1, len(itinerary.days))
    stay_total = itinerary.accommodation.price_per_night * max(num_days - 1, 1)
    total_cost = total_activities_cost + stay_total
    itinerary.total_estimated_cost = round(total_cost, 2)

    if trip.budget and trip.budget > 0:
        if itinerary.total_estimated_cost > trip.budget * 1.05:
            itinerary.budget_status = "over_budget"
        elif itinerary.total_estimated_cost < trip.budget * 0.90:
            itinerary.budget_status = "under_budget"
        else:
            itinerary.budget_status = "on_budget"
    else:
        itinerary.budget_status = "on_budget"

    return itinerary


def validate_and_repair(
    provider: LLMProvider,
    raw_response: dict[str, Any],
    schema_cls: type[T],
    original_user_prompt: str,
) -> T:
    try:
        return schema_cls.model_validate(raw_response)
    except ValidationError as first_error:
        repair_user_prompt = (
            f"The following JSON failed schema validation:\n"
            f"```json\n{json.dumps(raw_response)}\n```\n"
            f"Validation errors:\n{first_error.errors()}\n\n"
            f"Original user request:\n{original_user_prompt}\n\n"
            f"Fix ALL errors and return strictly valid JSON matching the schema."
        )

        try:
            repaired_raw = provider.generate_json(
                system_prompt=SYSTEM_PROMPT,
                user_prompt=repair_user_prompt,
            )
            return schema_cls.model_validate(repaired_raw)
        except Exception as second_error:
            raise AppError(
                status_code=502,
                code="AI_SCHEMA_VALIDATION_FAILED",
                message=f"Failed to generate valid itinerary schema after repair retry: {second_error!s}",
            ) from second_error


class ItineraryService:
    def __init__(self, provider: LLMProvider | None = None) -> None:
        self.provider = provider or GeminiProvider()

    def generate_full(self, trip: TripRecord) -> Itinerary:
        cache_key = f"trip_full_{trip.destination}_{trip.start_date}_{trip.end_date}_{trip.budget}_{trip.pacing}_{trip.group_size}"
        cached = generation_cache.get(cache_key)
        if cached:
            return Itinerary.model_validate(cached)

        user_prompt = build_full_itinerary_prompt(trip)
        raw = self.provider.generate_json(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=user_prompt,
        )
        itinerary = validate_and_repair(self.provider, raw, Itinerary, user_prompt)
        processed = post_process_itinerary(itinerary, trip)

        generation_cache.set(cache_key, processed.model_dump())
        return processed

    def regenerate_day(
        self,
        trip: TripRecord,
        day_number: int,
        existing_days: list[DayPlan],
        instruction: str | None = None,
    ) -> DayPlan:
        other_days_summary = [
            {
                "day_number": d.day_number,
                "summary": d.summary,
                "activities": [a.title for a in d.activities],
            }
            for d in existing_days
            if d.day_number != day_number
        ]

        user_prompt = build_regenerate_day_prompt(
            trip, day_number, instruction, other_days_summary
        )
        raw = self.provider.generate_json(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=user_prompt,
        )
        day_plan = validate_and_repair(self.provider, raw, DayPlan, user_prompt)

        target_date = trip.start_date + timedelta(days=day_number - 1)
        day_plan.date = target_date.isoformat()
        day_plan.day_number = day_number

        return post_process_day(day_plan, trip.pacing)
