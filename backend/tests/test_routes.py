from uuid import uuid4

from app.api.routes.trips import get_itinerary_service
from app.core.config import Settings, get_settings
from app.db.client import get_supabase_client
from app.main import app
from app.schemas.itinerary import Accommodation, Activity, DayPlan, Itinerary
from app.services.ai.itinerary_service import ItineraryService
from fastapi.testclient import TestClient

from tests.test_health_and_auth import TEST_JWT_SECRET, create_token
from tests.test_trips_repo import FakeSupabaseClient

fake_db = FakeSupabaseClient()


def override_supabase_client() -> FakeSupabaseClient:
    return fake_db


def override_settings() -> Settings:
    return Settings(
        supabase_jwt_secret=TEST_JWT_SECRET,
        cors_origin="http://localhost:5173",
    )


class StubAiService(ItineraryService):
    def __init__(self) -> None:
        pass

    def generate_full(self, trip):
        return Itinerary(
            destination=trip.destination,
            days=[
                DayPlan(
                    day_number=1,
                    date=str(trip.start_date),
                    theme="City Highlights",
                    summary="Sightseeing and dinner",
                    activities=[
                        Activity(
                            time_slot="morning",
                            start_time="09:00",
                            end_time="11:30",
                            title="Palace Visit",
                            type="attraction",
                            description="Touring the grand palace",
                            location="Center",
                            est_cost=500.0,
                            travel_time_from_previous_min=10,
                        ),
                        Activity(
                            time_slot="evening",
                            start_time="19:00",
                            end_time="21:00",
                            title="Local Dinner",
                            type="dining",
                            description="Traditional cuisine",
                            location="Old Town",
                            est_cost=1500.0,
                            travel_time_from_previous_min=15,
                        ),
                    ],
                    day_total_cost=2000.0,
                )
            ],
            accommodation=Accommodation(
                name="Grand Hotel",
                area="Downtown",
                price_per_night=4000.0,
                why="Strategic location",
            ),
            total_estimated_cost=6000.0,
            budget_status="on_budget",
            packing_tips=["Comfortable walking shoes"],
        )

    def regenerate_day(self, trip, day_number, existing_days, instruction=None):
        return DayPlan(
            day_number=day_number,
            date=str(trip.start_date),
            theme="Regenerated Day",
            summary="Refreshed activities",
            activities=[
                Activity(
                    time_slot="morning",
                    start_time="10:00",
                    end_time="12:00",
                    title="Museum Visit",
                    type="attraction",
                    description="Art exhibits",
                    location="Art District",
                    est_cost=300.0,
                    travel_time_from_previous_min=5,
                )
            ],
            day_total_cost=300.0,
        )


app.dependency_overrides[get_settings] = override_settings
app.dependency_overrides[get_supabase_client] = override_supabase_client
app.dependency_overrides[get_itinerary_service] = lambda: StubAiService()

client = TestClient(app)


def test_auth_failure_on_unauthenticated_request() -> None:
    res = client.get("/api/v1/trips")
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "UNAUTHORIZED"


def test_validation_failure_on_invalid_dates_and_duration() -> None:
    user_id = str(uuid4())
    token = create_token(sub=user_id)
    headers = {"Authorization": f"Bearer {token}"}

    # end_date before start_date
    res = client.post(
        "/api/v1/trips",
        headers=headers,
        json={
            "title": "Invalid Trip",
            "destination": "Goa",
            "start_date": "2026-11-10",
            "end_date": "2026-11-05",
            "budget": 10000,
        },
    )
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "VALIDATION_ERROR"

    # duration > 14 days
    res = client.post(
        "/api/v1/trips",
        headers=headers,
        json={
            "title": "Too Long Trip",
            "destination": "Goa",
            "start_date": "2026-11-01",
            "end_date": "2026-11-20",
            "budget": 10000,
        },
    )
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "VALIDATION_ERROR"


def test_happy_path_trip_lifecycle_and_permissions() -> None:
    owner_id = str(uuid4())
    owner_token = create_token(sub=owner_id)
    owner_headers = {"Authorization": f"Bearer {owner_token}"}

    outsider_id = str(uuid4())
    outsider_token = create_token(sub=outsider_id)
    outsider_headers = {"Authorization": f"Bearer {outsider_token}"}

    # 1. POST /api/v1/trips (draft)
    create_res = client.post(
        "/api/v1/trips",
        headers=owner_headers,
        json={
            "title": "Kerala Backwaters",
            "destination": "Kochi, India",
            "start_date": "2026-12-01",
            "end_date": "2026-12-03",
            "budget": 30000,
            "currency": "INR",
            "travel_style": "nature",
            "pacing": "relaxed",
            "group_size": 2,
            "interests": ["houseboats", "spices"],
        },
    )
    assert create_res.status_code == 201
    trip_data = create_res.json()
    trip_id = trip_data["id"]
    assert trip_data["status"] == "draft"

    # 2. GET /api/v1/trips/{id} (outsider forbidden 403)
    out_res = client.get(f"/api/v1/trips/{trip_id}", headers=outsider_headers)
    assert out_res.status_code == 403

    # 3. POST /api/v1/trips/{id}/members (add editor)
    member_res = client.post(
        f"/api/v1/trips/{trip_id}/members",
        headers=owner_headers,
        json={"email": "collaborator@travel.test", "role": "editor"},
    )
    assert member_res.status_code == 201
    collab_user_id = member_res.json()["user_id"]
    collab_token = create_token(sub=collab_user_id)
    collab_headers = {"Authorization": f"Bearer {collab_token}"}

    # 4. POST /api/v1/trips/{id}/generate (editor generates)
    gen_res = client.post(f"/api/v1/trips/{trip_id}/generate", headers=collab_headers)
    assert gen_res.status_code == 200
    gen_json = gen_res.json()
    assert len(gen_json["days"]) == 1
    assert gen_json["total_estimated_cost"] == 6000.0

    # Verify trip status updated to generated
    trip_check = client.get(f"/api/v1/trips/{trip_id}", headers=owner_headers).json()
    assert trip_check["status"] == "generated"

    # 5. POST /api/v1/trips/{id}/days/1/regenerate
    regen_res = client.post(
        f"/api/v1/trips/{trip_id}/days/1/regenerate",
        headers=collab_headers,
        json={"instruction": "Add more cultural arts"},
    )
    assert regen_res.status_code == 200
    assert regen_res.json()["activities"][0]["title"] == "Museum Visit"

    # 6. PATCH /api/v1/trips/{id}/days/1 (manual activity edit)
    patch_day_res = client.patch(
        f"/api/v1/trips/{trip_id}/days/1",
        headers=collab_headers,
        json={
            "summary": "Manual adjustment of day 1",
            "items": [
                {
                    "title": "Kathakali Performance",
                    "type": "activity",
                    "est_cost": 800.0,
                }
            ],
        },
    )
    assert patch_day_res.status_code == 200
    assert patch_day_res.json()["est_cost"] == 800.0

    # 7. GET /api/v1/trips/{id}/summary (budget breakdown)
    summary_res = client.get(f"/api/v1/trips/{trip_id}/summary", headers=collab_headers)
    assert summary_res.status_code == 200
    summary_data = summary_res.json()
    assert summary_data["trip_id"] == trip_id
    assert summary_data["activities_cost"] == 800.0
    assert "categories" in summary_data

    # 8. DELETE /api/v1/trips/{id}/members/{user_id}
    del_member_res = client.delete(
        f"/api/v1/trips/{trip_id}/members/{collab_user_id}",
        headers=owner_headers,
    )
    assert del_member_res.status_code == 204

    # 9. DELETE /api/v1/trips/{id}
    del_res = client.delete(f"/api/v1/trips/{trip_id}", headers=owner_headers)
    assert del_res.status_code == 204
