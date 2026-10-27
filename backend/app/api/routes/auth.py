from datetime import datetime, timedelta, timezone
from typing import Annotated
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, Request
from supabase import Client

from app.core.config import Settings, get_settings
from app.core.errors import AppError
from app.core.limiter import limiter
from app.db.client import get_supabase_client
from app.db.trips_repo import create_trip, list_trips, update_trip, upsert_days
from app.schemas.api import DemoAuthResponse, SignupRequest, SignupResponse
from app.schemas.db import DayUpsert, TripCreate, TripUpdate

router = APIRouter(prefix="/auth", tags=["auth"])

DEMO_ACCOUNT_EMAIL = "demo@travelplanner.io"
DEMO_ACCOUNT_PASSWORD = "DemoPlanner123!"


def _seed_sample_trips_if_empty(client: Client, user_id: UUID) -> None:
    """Populate 2 rich sample itineraries for the demo account if none exist yet."""
    existing = list_trips(client, user_id)
    if existing:
        return

    today = datetime.now(timezone.utc).date()

    # Sample Trip 1: Weekend Solo Escape in Goa
    start_1 = today + timedelta(days=14)
    end_1 = start_1 + timedelta(days=1)
    trip_1 = create_trip(
        client,
        TripCreate(
            owner_id=user_id,
            title="Weekend Solo Escape in Goa",
            destination="Goa, India",
            start_date=start_1,
            end_date=end_1,
            budget=15000.0,
            currency="INR",
            travel_style="leisure",
            pacing="relaxed",
            group_size=1,
            interests=["Beaches", "Local Cuisine", "Photography"],
            preferences={"is_seed_demo": True, "vibe": "chill beachfront"},
            stay={
                "name": "Santana Beach Resort",
                "area": "Candolim Beach",
                "price_per_night": 4500.0,
                "why": "Peaceful tropical gardens right next to the beach, perfect for solo travelers.",
            },
            status="draft",
        ),
    )

    days_1 = [
        DayUpsert(
            trip_id=trip_1.id,
            day_number=1,
            date=start_1,
            summary="Arrival, beachside walk, and authentic Goan lunch at Candolim.",
            items=[
                {
                    "time_slot": "morning",
                    "start_time": "10:00",
                    "end_time": "12:00",
                    "title": "Candolim Beach Walk & Shack Relax",
                    "type": "activity",
                    "description": "Stroll along the calm sands and unwind under sun loungers.",
                    "location": "Candolim",
                    "est_cost": 300.0,
                    "travel_time_from_previous_min": 0,
                    "tips": "Carry sunglasses and beach towel.",
                },
                {
                    "time_slot": "afternoon",
                    "start_time": "12:30",
                    "end_time": "14:00",
                    "title": "Fresh Goan Seafood Curry",
                    "type": "dining",
                    "description": "Authentic Kingfish thali and sol kadhi.",
                    "location": "Candolim Beach Rd",
                    "est_cost": 850.0,
                    "travel_time_from_previous_min": 5,
                    "tips": "Try the kokum cooler.",
                },
                {
                    "time_slot": "evening",
                    "start_time": "16:30",
                    "end_time": "18:45",
                    "title": "Aguada Fort Sunset Viewpoint",
                    "type": "attraction",
                    "description": "Historic 17th-century bastion with 360-degree ocean views.",
                    "location": "Sinquerim",
                    "est_cost": 200.0,
                    "travel_time_from_previous_min": 15,
                    "tips": "Reach 45 mins before sunset for optimal lighting.",
                },
            ],
            est_cost=1350.0,
        ),
        DayUpsert(
            trip_id=trip_1.id,
            day_number=2,
            date=end_1,
            summary="Latin Quarter heritage architecture and artisan cafe brunch.",
            items=[
                {
                    "time_slot": "morning",
                    "start_time": "09:30",
                    "end_time": "12:00",
                    "title": "Fontainhas Latin Quarter Photo Walk",
                    "type": "attraction",
                    "description": "Vibrant colonial Portuguese villas, tiled frescoes, and heritage alleys.",
                    "location": "Panaji",
                    "est_cost": 0.0,
                    "travel_time_from_previous_min": 25,
                    "tips": "Respect local residents when taking street photographs.",
                },
                {
                    "time_slot": "afternoon",
                    "start_time": "12:30",
                    "end_time": "14:00",
                    "title": "Artisan Bakery & Coffee",
                    "type": "dining",
                    "description": "Traditional bebinca pastry and locally roasted South Indian coffee.",
                    "location": "Panaji",
                    "est_cost": 500.0,
                    "travel_time_from_previous_min": 5,
                    "tips": "Order the warm cinnamon bebinca slice.",
                },
            ],
            est_cost=500.0,
        ),
    ]
    upsert_days(client, trip_1.id, user_id, days_1)
    update_trip(client, trip_1.id, user_id, TripUpdate(status="generated"))

    # Sample Trip 2: 5-Day Royal Romance in Udaipur
    start_2 = today + timedelta(days=30)
    end_2 = start_2 + timedelta(days=4)
    trip_2 = create_trip(
        client,
        TripCreate(
            owner_id=user_id,
            title="Royal Romance in Udaipur & Mount Abu",
            destination="Udaipur, Rajasthan",
            start_date=start_2,
            end_date=end_2,
            budget=60000.0,
            currency="INR",
            travel_style="cultural",
            pacing="moderate",
            group_size=2,
            interests=["Historical Forts", "Local Cuisine", "Temples & Spirituality"],
            preferences={"is_seed_demo": True, "special": "anniversary celebration"},
            stay={
                "name": "Fateh Garh Heritage Sanctuary",
                "area": "Sisarma Hills, Lake Pichola",
                "price_per_night": 7500.0,
                "why": "Panoramic hilltop views over Lake Pichola and authentic Mewari architecture.",
            },
            status="draft",
        ),
    )

    themes = [
        ("Grand City Palace & Sunset Boat Ride", "Lake Pichola"),
        ("Monsoon Palace & Saheliyon Ki Bari", "Fateh Sagar"),
        ("Jagdish Temple & Old City Bazaars", "Old City"),
        ("Day Excursion to Kumbhalgarh Fort", "Kumbhalgarh"),
        ("Bagore Ki Haveli Folk Dance & Rooftop Dining", "Gangaur Ghat"),
    ]
    days_2: list[DayUpsert] = []
    for d_idx, (summary_text, loc) in enumerate(themes, start=1):
        d_date = start_2 + timedelta(days=d_idx - 1)
        days_2.append(
            DayUpsert(
                trip_id=trip_2.id,
                day_number=d_idx,
                date=d_date,
                summary=summary_text,
                items=[
                    {
                        "time_slot": "morning",
                        "start_time": "09:30",
                        "end_time": "12:00",
                        "title": f"Mewar Heritage Tour - {loc}",
                        "type": "attraction",
                        "description": "Intricate marble carvings, royal museum exhibits, and historic courtyards.",
                        "location": loc,
                        "est_cost": 600.0,
                        "travel_time_from_previous_min": 0,
                    },
                    {
                        "time_slot": "afternoon",
                        "start_time": "13:00",
                        "end_time": "14:30",
                        "title": "Royal Rajasthani Thali Lunch",
                        "type": "dining",
                        "description": "Traditional dal baati churma, gatte ki sabzi, and ker sangri.",
                        "location": "Old Town",
                        "est_cost": 1400.0,
                        "travel_time_from_previous_min": 10,
                    },
                    {
                        "time_slot": "evening",
                        "start_time": "17:00",
                        "end_time": "19:00",
                        "title": "Lake Pichola Golden Hour Cruise",
                        "type": "activity",
                        "description": "Scenic boat cruise gliding past Jag Mandir Island palace.",
                        "location": "Lake Pichola",
                        "est_cost": 1200.0,
                        "travel_time_from_previous_min": 15,
                    },
                ],
                est_cost=3200.0,
            )
        )
    upsert_days(client, trip_2.id, user_id, days_2)
    update_trip(client, trip_2.id, user_id, TripUpdate(status="generated"))


@router.post("/signup", response_model=SignupResponse, status_code=201)
@limiter.limit("10/minute")
async def signup_user_endpoint(
    request: Request,
    body: SignupRequest,
    client: Annotated[Client, Depends(get_supabase_client)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> SignupResponse:
    """Register a user with auto-confirmed email via Supabase Admin API (no SMTP server needed)."""
    normalized_email = body.email.strip().lower()
    admin_auth = getattr(client.auth, "admin", None)
    if admin_auth is None:
        raise AppError(status_code=500, code="AUTH_UNAVAILABLE", message="Auth admin service unavailable.")

    try:
        admin_auth.create_user(
            {
                "email": normalized_email,
                "password": body.password,
                "email_confirm": True,
            }
        )
        return SignupResponse(email=normalized_email, confirmed=True)
    except Exception as exc:
        # Check if this account was created earlier while email confirmation was pending,
        # and verify the caller knows the exact password before confirming it.
        api_key = (
            settings.supabase_anon_key
            if "placeholder" not in settings.supabase_anon_key
            else settings.supabase_service_role_key
        )
        token_url = f"{settings.supabase_url.rstrip('/')}/auth/v1/token?grant_type=password"
        try:
            resp = httpx.post(
                token_url,
                headers={"apikey": api_key, "Content-Type": "application/json"},
                json={"email": normalized_email, "password": body.password},
                timeout=10.0,
            )
            data = resp.json()
        except Exception:
            data = {}

        if data.get("error_code") == "email_not_confirmed":
            users = admin_auth.list_users(page=1, per_page=200)
            target = next((u for u in users if (u.email or "").lower() == normalized_email), None)
            if target is not None:
                admin_auth.update_user_by_id(str(target.id), {"email_confirm": True})
                return SignupResponse(email=normalized_email, confirmed=True)

        err_msg = str(exc)
        if "already" in err_msg.lower() or "registered" in err_msg.lower() or "exists" in err_msg.lower():
            raise AppError(
                status_code=409,
                code="USER_ALREADY_EXISTS",
                message="An account with this email already exists. Please sign in instead.",
            ) from exc

        raise AppError(
            status_code=400,
            code="SIGNUP_FAILED",
            message=f"Unable to create account: {err_msg}",
        ) from exc


@router.post("/demo", response_model=DemoAuthResponse)
@limiter.limit("15/minute")
async def prepare_demo_account_endpoint(
    request: Request,
    client: Annotated[Client, Depends(get_supabase_client)],
) -> DemoAuthResponse:
    """Ensure the shared demo account and sample itineraries exist and return public demo credentials."""
    admin_auth = getattr(client.auth, "admin", None)
    if admin_auth is None:
        raise AppError(status_code=500, code="AUTH_UNAVAILABLE", message="Auth admin service unavailable.")

    user_id_str: str | None = None
    try:
        res = admin_auth.create_user(
            {
                "email": DEMO_ACCOUNT_EMAIL,
                "password": DEMO_ACCOUNT_PASSWORD,
                "email_confirm": True,
            }
        )
        user_id_str = str(res.user.id)
    except Exception:
        users = admin_auth.list_users(page=1, per_page=200)
        target = next((u for u in users if (u.email or "").lower() == DEMO_ACCOUNT_EMAIL), None)
        if target is None:
            raise AppError(
                status_code=500,
                code="DEMO_PROVISION_FAILED",
                message="Could not provision demo account.",
            ) from None
        admin_auth.update_user_by_id(
            str(target.id),
            {"email_confirm": True, "password": DEMO_ACCOUNT_PASSWORD},
        )
        user_id_str = str(target.id)

    try:
        _seed_sample_trips_if_empty(client, UUID(user_id_str))
    except Exception:
        # Even if sample trip seeding encounters an issue, still allow demo sign-in
        pass

    return DemoAuthResponse(email=DEMO_ACCOUNT_EMAIL, password=DEMO_ACCOUNT_PASSWORD)
