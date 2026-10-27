from datetime import date, datetime, timezone
from typing import Any
from uuid import uuid4

import pytest
from app.core.cache import generation_cache
from app.core.errors import AppError
from app.schemas.db import TripRecord
from app.schemas.itinerary import DayPlan, Itinerary
from app.services.ai.itinerary_service import ItineraryService
from app.services.ai.provider import LLMProvider


def make_sample_trip(budget: float = 20000.0) -> TripRecord:
    return TripRecord(
        id=uuid4(),
        owner_id=uuid4(),
        title="Jaipur Weekend",
        destination="Jaipur, Rajasthan",
        start_date=date(2026, 12, 1),
        end_date=date(2026, 12, 2),
        budget=budget,
        currency="INR",
        travel_style="cultural",
        pacing="relaxed",
        group_size=2,
        interests=["forts", "rajasthani thali"],
        preferences={},
        stay={},
        status="draft",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


VALID_ITINERARY_DICT: dict[str, Any] = {
    "destination": "Jaipur, Rajasthan",
    "accommodation": {
        "name": "Alsisar Haveli",
        "area": "MI Road",
        "price_per_night": 5000.0,
        "why": "Heritage stay with central connectivity.",
    },
    "days": [
        {
            "day_number": 1,
            "date": "2026-12-01",
            "theme": "Amer & Heritage",
            "summary": "Visit Amer Fort and enjoy lunch.",
            "activities": [
                {
                    "time_slot": "morning",
                    "start_time": "09:00",
                    "end_time": "12:00",
                    "title": "Amer Fort Guided Tour",
                    "type": "attraction",
                    "description": "Magnificent hilltop fort.",
                    "location": "Amer",
                    "est_cost": 500.0,
                    "travel_time_from_previous_min": 20,
                    "tips": "Take the shuttle or walk up.",
                },
                {
                    "time_slot": "afternoon",
                    "start_time": "13:00",
                    "end_time": "14:30",
                    "title": "Traditional Thali Lunch",
                    "type": "dining",
                    "description": "Dal Baati Churma meal.",
                    "location": "1135 AD, Amer",
                    "est_cost": 1200.0,
                    "travel_time_from_previous_min": 5,
                    "tips": "Reserve a table in advance.",
                },
            ],
            "day_total_cost": 0.0,  # post-processor should recalculate to 1700.0
        },
        {
            "day_number": 2,
            "date": "2026-12-02",
            "theme": "City Palace & Bazaars",
            "summary": "City landmarks and shopping.",
            "activities": [
                {
                    "time_slot": "morning",
                    "start_time": "10:00",
                    "end_time": "12:30",
                    "title": "City Palace Tour",
                    "type": "attraction",
                    "description": "Courtyards and museum.",
                    "location": "Old City",
                    "est_cost": 700.0,
                    "travel_time_from_previous_min": 15,
                    "tips": "Combine ticket with Jantar Mantar.",
                }
            ],
            "day_total_cost": 0.0,  # post-processor should recalculate to 700.0
        },
    ],
    "total_estimated_cost": 0.0,  # post-processor recalculates to 1700 + 700 + 5000 = 7400.0
    "budget_status": "on_budget",
    "packing_tips": ["Sun hat", "Walking shoes"],
}


class MockSuccessProvider(LLMProvider):
    def generate_json(self, system_prompt: str, user_prompt: str, json_schema=None):
        return VALID_ITINERARY_DICT


class MockRepairSuccessProvider(LLMProvider):
    def __init__(self) -> None:
        self.call_count = 0

    def generate_json(self, system_prompt: str, user_prompt: str, json_schema=None):
        self.call_count += 1
        if self.call_count == 1:
            # Missing required 'accommodation' key and invalid activity time_slot
            return {
                "destination": "Jaipur, Rajasthan",
                "days": [],
            }
        # Repaired output on retry
        return VALID_ITINERARY_DICT


class MockAlwaysFailsProvider(LLMProvider):
    def generate_json(self, system_prompt: str, user_prompt: str, json_schema=None):
        # Invalid schema on both attempts
        return {"destination": 12345, "invalid": True}


def test_generate_full_success_and_post_processing() -> None:
    trip = make_sample_trip(budget=10000.0)
    service = ItineraryService(provider=MockSuccessProvider())
    itinerary = service.generate_full(trip)

    assert isinstance(itinerary, Itinerary)
    assert itinerary.destination == "Jaipur, Rajasthan"
    assert len(itinerary.days) == 2
    # Verify post-processor recalculations
    assert itinerary.days[0].day_total_cost == 1700.0
    assert itinerary.days[1].day_total_cost == 700.0
    # Total = 1700 + 700 + (1 night * 5000) = 7400.0
    assert itinerary.total_estimated_cost == 7400.0
    assert itinerary.budget_status == "under_budget"


def test_generate_full_repair_retry_success() -> None:
    trip = make_sample_trip(budget=20000.0)
    provider = MockRepairSuccessProvider()
    service = ItineraryService(provider=provider)

    itinerary = service.generate_full(trip)
    assert provider.call_count == 2
    assert isinstance(itinerary, Itinerary)
    assert itinerary.total_estimated_cost == 7400.0


def test_generate_full_fails_after_repair_returns_502() -> None:
    generation_cache.clear()
    trip = make_sample_trip(budget=20000.0)
    service = ItineraryService(provider=MockAlwaysFailsProvider())

    with pytest.raises(AppError) as exc_info:
        service.generate_full(trip)

    assert exc_info.value.status_code == 502
    assert exc_info.value.code == "AI_SCHEMA_VALIDATION_FAILED"


def test_regenerate_day_success() -> None:
    trip = make_sample_trip(budget=20000.0)

    class MockDayProvider(LLMProvider):
        def generate_json(self, system_prompt: str, user_prompt: str, json_schema=None):
            return {
                "day_number": 1,
                "date": "2026-12-01",
                "theme": "Alternative Heritage Walk",
                "summary": "Alternative morning and afternoon plan.",
                "activities": [
                    {
                        "time_slot": "morning",
                        "start_time": "09:00",
                        "end_time": "11:30",
                        "title": "Nahargarh Fort Sunrise",
                        "type": "attraction",
                        "description": "Hilltop palace walls.",
                        "location": "Nahargarh",
                        "est_cost": 300.0,
                        "travel_time_from_previous_min": 15,
                        "tips": "Early morning is best.",
                    }
                ],
                "day_total_cost": 0.0,
            }

    service = ItineraryService(provider=MockDayProvider())
    existing_days = [
        DayPlan(
            day_number=1,
            date="2026-12-01",
            theme="Old Day 1",
            summary="Old plan",
            activities=[],
        ),
        DayPlan(
            day_number=2,
            date="2026-12-02",
            theme="Day 2",
            summary="Day 2 plan",
            activities=[],
        ),
    ]

    new_day = service.regenerate_day(
        trip=trip,
        day_number=1,
        existing_days=existing_days,
        instruction="Focus on Nahargarh instead of Amer",
    )

    assert isinstance(new_day, DayPlan)
    assert new_day.day_number == 1
    assert new_day.activities[0].title == "Nahargarh Fort Sunrise"
    assert new_day.day_total_cost == 300.0
