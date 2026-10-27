#!/usr/bin/env python3
"""Seed demo account and pre-generated sample trips directly into Supabase.

Creates:
1. Demo user in auth.users (if not already existing) via Supabase Admin API
2. Weekend Solo Trip (Goa) - Draft -> Generated with 2 full days and stay
3. 5-Day Couple Trip (Udaipur & Mount Abu) - Generated with 5 full days and stay
"""

import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID, uuid4

# Ensure app imports resolve
CURRENT_DIR = Path(__file__).resolve().parent
REPO_ROOT = CURRENT_DIR.parent
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Stub optional modules if needed in environment
for mod in ["multidict", "propcache", "propcache.api"]:
    if mod not in sys.modules:
        from unittest.mock import MagicMock
        m = MagicMock()
        m.istr = str
        m.under_cached_property = property
        sys.modules[mod] = m

from app.core.config import get_settings
from app.db.client import get_supabase_client
from app.db.trips_repo import TripUpdate, create_trip, update_trip, upsert_days
from app.schemas.db import DayUpsert, TripCreate


def seed_demo_data() -> None:
    settings = get_settings()
    client = get_supabase_client()

    demo_email = os.getenv("DEMO_EMAIL", "demo@travelplanner.local")
    demo_password = os.getenv("DEMO_PASSWORD", "DemoPlanner123!")

    print(f"Connecting to Supabase at: {settings.supabase_url}")

    # 1. Resolve or create demo user
    user_id_str = os.getenv("DEMO_USER_ID", "")
    if not user_id_str:
        try:
            # Attempt to create or retrieve user using Supabase Auth Admin
            admin_auth = getattr(client.auth, "admin", None)
            if admin_auth and hasattr(admin_auth, "create_user"):
                res = admin_auth.create_user({
                    "email": demo_email,
                    "password": demo_password,
                    "email_confirm": True,
                })
                user_id_str = str(res.user.id)
                print(f"Created demo user: {demo_email} (ID: {user_id_str})")
            else:
                user_id_str = str(uuid4())
                print(f"Generated standalone UUID for seed user: {user_id_str}")
        except Exception as exc:
            print(f"User creation note: {exc}. Using deterministic fallback.")
            from uuid import NAMESPACE_URL, uuid5
            user_id_str = str(uuid5(NAMESPACE_URL, demo_email))

    user_id = UUID(user_id_str)

    # 2. Trip 1: Weekend Solo Trip to Goa (Relaxed)
    today = datetime.now(timezone.utc).date()
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
    print(f"Seeded Trip 1 (Solo Goa): ID {trip_1.id}")

    # 3. Trip 2: 5-Day Couple Trip to Udaipur (Moderate)
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

    days_2: list[DayUpsert] = []
    themes = [
        ("Grand City Palace & Sunset Boat Ride", "Lake Pichola"),
        ("Monsoon Palace & Saheliyon Ki Bari", "Fateh Sagar"),
        ("Jagdish Temple & Old City Bazaars", "Old City"),
        ("Day Excursion to Kumbhalgarh Fort", "Kumbhalgarh"),
        ("Bagore Ki Haveli Folk Dance & Rooftop Dining", "Gangaur Ghat"),
    ]

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
    print(f"Seeded Trip 2 (Couple Udaipur): ID {trip_2.id}")

    print("\n[SUCCESS] Seed demo script finished cleanly!")


if __name__ == "__main__":
    seed_demo_data()
