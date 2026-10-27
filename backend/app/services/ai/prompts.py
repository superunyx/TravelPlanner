import json
from typing import Any

from app.schemas.db import TripRecord

SYSTEM_PROMPT = """You are an expert personalized travel itinerary planner.
Your goal is to build logical, practical, highly engaging travel plans adhering strictly to user constraints.

Rules:
1. Respect the user's budget and currency strictly.
2. Group nearby places and attractions on the same day to minimize travel time.
3. Activity pacing:
   - 'relaxed': 3 to 4 activities per day
   - 'moderate': 4 to 5 activities per day
   - 'packed': 5 to 6 activities per day
4. Include at least one authentic local dining or meal experience per day.
5. Provide realistic, sequential start_time and end_time (e.g. '09:00', '11:30') with realistic travel_time_from_previous_min.
6. Return ONLY valid JSON matching the requested schema. No conversational preamble or Markdown fences.
"""


def build_full_itinerary_prompt(trip: TripRecord) -> str:
    num_days = (trip.end_date - trip.start_date).days + 1
    interests_str = ", ".join(trip.interests) if trip.interests else "General sightseeing"
    budget_str = f"{trip.budget} {trip.currency}" if trip.budget else "Standard budget"

    return f"""Generate a detailed day-by-day itinerary for:
- Destination: {trip.destination}
- Dates: {trip.start_date.isoformat()} to {trip.end_date.isoformat()} ({num_days} days)
- Pacing: {trip.pacing}
- Budget: {budget_str}
- Currency: {trip.currency}
- Group Size: {trip.group_size}
- Travel Style: {trip.travel_style or 'balanced'}
- Interests: {interests_str}
- Additional Preferences: {json.dumps(trip.preferences)}
- Known Stay/Accommodation: {json.dumps(trip.stay)}

Ensure exactly {num_days} days in the days array, numbered 1 to {num_days}.
"""


def build_regenerate_day_prompt(
    trip: TripRecord,
    day_number: int,
    instruction: str | None,
    other_days_summary: list[dict[str, Any]],
) -> str:
    interests_str = ", ".join(trip.interests) if trip.interests else "General sightseeing"

    return f"""Regenerate ONLY day number {day_number} of the trip to {trip.destination}.
- Trip Dates: {trip.start_date.isoformat()} to {trip.end_date.isoformat()}
- Day Number: {day_number}
- Pacing: {trip.pacing}
- Currency: {trip.currency}
- Interests: {interests_str}
- Specific User Instruction: {instruction or 'Provide fresh, high-quality alternatives.'}

Other days context (DO NOT repeat attractions or venues already visited on these days):
{json.dumps(other_days_summary, indent=2)}

Output ONLY valid JSON for a DayPlan object matching the DayPlan schema with day_number={day_number}.
"""
