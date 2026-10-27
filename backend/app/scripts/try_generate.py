import json
from datetime import date, datetime, timezone
from uuid import uuid4

from app.schemas.db import TripRecord
from app.services.ai.itinerary_service import ItineraryService
from app.services.ai.provider import LLMProvider


class MockDemoProvider(LLMProvider):
    def generate_json(self, system_prompt: str, user_prompt: str, json_schema=None):
        return {
            "destination": "Goa, India",
            "accommodation": {
                "name": "Taj Fort Aguada Resort",
                "area": "Sinquerim Beach, North Goa",
                "price_per_night": 12000.0,
                "why": "Beachfront heritage resort with easy access to coastal highlights and fine dining.",
            },
            "days": [
                {
                    "day_number": 1,
                    "date": "2026-11-15",
                    "theme": "Coastal Heritage & Sunsets",
                    "summary": "Explore Aguada Fort and relax at Sinquerim beach with beachside seafood.",
                    "activities": [
                        {
                            "time_slot": "morning",
                            "start_time": "09:30",
                            "end_time": "12:00",
                            "title": "Fort Aguada & Lighthouse Walk",
                            "type": "attraction",
                            "description": "Historic 17th-century Portuguese fortress with panoramic Arabian sea views.",
                            "location": "Candolim",
                            "est_cost": 200.0,
                            "travel_time_from_previous_min": 15,
                            "tips": "Wear comfortable shoes and carry sun protection.",
                        },
                        {
                            "time_slot": "afternoon",
                            "start_time": "13:00",
                            "end_time": "14:30",
                            "title": "Authentic Goan Seafood Lunch",
                            "type": "dining",
                            "description": "Taste local Goan fish curry, prawn balchao, and poi.",
                            "location": "Kokum Kitchen, Sinquerim",
                            "est_cost": 1500.0,
                            "travel_time_from_previous_min": 10,
                            "tips": "Try the sol kadhi cooler.",
                        },
                        {
                            "time_slot": "evening",
                            "start_time": "17:00",
                            "end_time": "19:00",
                            "title": "Sinquerim Beach Sunset",
                            "type": "activity",
                            "description": "Golden hour walk along the coast and calm beachside relaxation.",
                            "location": "Sinquerim Beach",
                            "est_cost": 0.0,
                            "travel_time_from_previous_min": 5,
                            "tips": "Best sunset views near the lower fort walls.",
                        },
                    ],
                    "day_total_cost": 0.0,
                }
            ],
            "total_estimated_cost": 0.0,
            "budget_status": "on_budget",
            "packing_tips": ["Sunscreen SPF 50+", "Comfortable sandals", "Breathable linen clothing"],
        }


def main() -> None:
    demo_trip = TripRecord(
        id=uuid4(),
        owner_id=uuid4(),
        title="Goa Quick Coastal Getaway",
        destination="Goa, India",
        start_date=date(2026, 11, 15),
        end_date=date(2026, 11, 15),
        budget=20000.0,
        currency="INR",
        travel_style="relaxed",
        pacing="relaxed",
        group_size=2,
        interests=["beaches", "seafood", "heritage"],
        preferences={"hotel_preference": "beachfront"},
        stay={},
        status="draft",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    print("=== Generating Itinerary via ItineraryService ===")
    service = ItineraryService(provider=MockDemoProvider())
    itinerary = service.generate_full(demo_trip)
    print(json.dumps(itinerary.model_dump(), indent=2))
    print("\nSuccessfully generated and post-processed itinerary!")


if __name__ == "__main__":
    main()
