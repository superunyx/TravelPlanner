from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response
from supabase import Client

from app.api.deps import require_trip_editor, require_trip_owner, require_trip_viewer
from app.core.auth import get_current_user
from app.core.config import get_settings
from app.core.errors import AppError
from app.core.limiter import limiter
from app.core.quota import quota_manager
from app.core.sanitizer import sanitize_user_input
from app.db.client import get_supabase_client
from app.db.trips_repo import (
    create_trip,
    delete_trip,
    get_days,
    list_trips,
    update_day,
    update_trip,
    upsert_days,
)
from app.schemas.api import (
    AddMemberRequest,
    CategoryCostBreakdown,
    CreateTripRequest,
    MemberResponse,
    RegenerateDayRequest,
    TripSummaryResponse,
    UpdateDayRequest,
    UpdateTripRequest,
)
from app.schemas.db import (
    DayRecord,
    DayUpdate,
    DayUpsert,
    TripCreate,
    TripRecord,
    TripUpdate,
)
from app.schemas.itinerary import DayPlan, Itinerary
from app.services.ai.itinerary_service import ItineraryService

router = APIRouter(prefix="/trips", tags=["trips"])


def get_itinerary_service() -> ItineraryService:
    return ItineraryService()


@router.post("", response_model=TripRecord, status_code=201)
async def create_trip_endpoint(
    body: CreateTripRequest,
    user_id_str: Annotated[str, Depends(get_current_user)],
    client: Annotated[Client, Depends(get_supabase_client)],
) -> TripRecord:
    """Create a new trip in draft status."""
    user_id = UUID(user_id_str)
    trip_data = TripCreate(
        owner_id=user_id,
        title=body.title,
        destination=body.destination,
        start_date=body.start_date,
        end_date=body.end_date,
        budget=body.budget,
        currency=body.currency,
        travel_style=body.travel_style,
        pacing=body.pacing,
        group_size=body.group_size,
        interests=body.interests,
        preferences=body.preferences,
        stay=body.stay,
        status="draft",
    )
    return create_trip(client, trip_data)


@router.get("", response_model=list[TripRecord])
async def list_trips_endpoint(
    user_id_str: Annotated[str, Depends(get_current_user)],
    client: Annotated[Client, Depends(get_supabase_client)],
) -> list[TripRecord]:
    """List all trips owned by or shared with the authenticated user."""
    return list_trips(client, UUID(user_id_str))


@router.get("/{id}", response_model=TripRecord)
async def get_trip_endpoint(
    access: Annotated[tuple[TripRecord, UUID], Depends(require_trip_viewer)],
) -> TripRecord:
    """Get trip metadata (requires viewer, editor, or owner role)."""
    trip, _ = access
    return trip


@router.patch("/{id}", response_model=TripRecord)
async def update_trip_endpoint(
    id: UUID,
    body: UpdateTripRequest,
    access: Annotated[tuple[TripRecord, UUID], Depends(require_trip_owner)],
    client: Annotated[Client, Depends(get_supabase_client)],
) -> TripRecord:
    """Update trip metadata (owner only)."""
    _, user_id = access
    update_data = TripUpdate(**body.model_dump(exclude_unset=True))
    return update_trip(client, id, user_id, update_data)


@router.delete("/{id}", status_code=204)
async def delete_trip_endpoint(
    id: UUID,
    access: Annotated[tuple[TripRecord, UUID], Depends(require_trip_owner)],
    client: Annotated[Client, Depends(get_supabase_client)],
) -> Response:
    """Delete a trip (owner only). Protects seeded demo trips if marked or owned by DEMO_USER_ID."""
    trip, user_id = access
    settings = get_settings()

    # Protect demo trips from deletion
    if (settings.demo_user_id and str(user_id) == str(settings.demo_user_id)) or trip.preferences.get("is_seed_demo") is True:
        raise AppError(
            status_code=403,
            code="FORBIDDEN_DEMO_PROTECTED",
            message="Demo sample trips are protected and cannot be deleted.",
        )

    delete_trip(client, id, user_id)
    return Response(status_code=204)


@router.post("/{id}/generate", response_model=Itinerary)
@limiter.limit("5/minute")
async def generate_trip_itinerary(
    request: Request,
    id: UUID,
    access: Annotated[tuple[TripRecord, UUID], Depends(require_trip_editor)],
    client: Annotated[Client, Depends(get_supabase_client)],
    ai_service: Annotated[ItineraryService, Depends(get_itinerary_service)],
) -> Itinerary:
    """Generate a full day-by-day itinerary via AI, persist itinerary_days, and mark trip generated."""
    trip, user_id = access
    settings = get_settings()

    # Quota check
    allowed, reason = quota_manager.check_and_increment(
        user_id=str(user_id),
        max_daily_global=settings.max_daily_generations,
        max_per_user=10,
    )
    if not allowed:
        raise AppError(status_code=429, code="QUOTA_EXCEEDED", message=reason)

    itinerary = ai_service.generate_full(trip)

    # Persist days
    day_upserts = [
        DayUpsert(
            trip_id=trip.id,
            day_number=day.day_number,
            date=body_date if (body_date := day.date) else None,
            summary=day.summary,
            items=[act.model_dump() for act in day.activities],
            est_cost=day.day_total_cost,
        )
        for day in itinerary.days
    ]
    upsert_days(client, trip.id, user_id, day_upserts)

    # Update stay column & status on trips
    update_trip(
        client,
        trip.id,
        trip.owner_id,
        TripUpdate(
            stay=itinerary.accommodation.model_dump(),
            status="generated",
        ),
    )

    return itinerary


@router.post("/{id}/days/{n}/regenerate", response_model=DayPlan)
@limiter.limit("10/minute")
async def regenerate_trip_day(
    request: Request,
    id: UUID,
    n: int,
    body: RegenerateDayRequest,
    access: Annotated[tuple[TripRecord, UUID], Depends(require_trip_editor)],
    client: Annotated[Client, Depends(get_supabase_client)],
    ai_service: Annotated[ItineraryService, Depends(get_itinerary_service)],
) -> DayPlan:
    """Regenerate a single day with AI using other days as context to avoid duplicates."""
    trip, user_id = access
    settings = get_settings()

    # Quota check
    allowed, reason = quota_manager.check_and_increment(
        user_id=str(user_id),
        max_daily_global=settings.max_daily_generations,
        max_per_user=15,
    )
    if not allowed:
        raise AppError(status_code=429, code="QUOTA_EXCEEDED", message=reason)

    db_days = get_days(client, trip.id, user_id)

    existing_plans: list[DayPlan] = []
    for d in db_days:
        existing_plans.append(
            DayPlan(
                day_number=d.day_number,
                date=str(d.date) if d.date else "",
                theme="",
                summary=d.summary,
                activities=d.items,  # type: ignore[arg-type]
                day_total_cost=d.est_cost,
            )
        )

    sanitized_instruction = sanitize_user_input(body.instruction) if body.instruction else None
    new_day = ai_service.regenerate_day(
        trip=trip,
        day_number=n,
        existing_days=existing_plans,
        instruction=sanitized_instruction,
    )

    # Persist regenerated day
    update_day(
        client=client,
        trip_id=trip.id,
        day_number=n,
        user_id=user_id,
        data=DayUpdate(
            summary=new_day.summary,
            items=[act.model_dump() for act in new_day.activities],
            est_cost=new_day.day_total_cost,
        ),
    )

    return new_day


@router.patch("/{id}/days/{n}", response_model=DayRecord)
async def update_trip_day(
    id: UUID,
    n: int,
    body: UpdateDayRequest,
    access: Annotated[tuple[TripRecord, UUID], Depends(require_trip_editor)],
    client: Annotated[Client, Depends(get_supabase_client)],
) -> DayRecord:
    """Manually edit day activities, recomputing est_cost."""
    trip, user_id = access

    est_cost = body.est_cost
    if body.items is not None and est_cost is None:
        est_cost = sum(float(item.get("est_cost", 0.0)) for item in body.items)

    day_update = DayUpdate(
        summary=body.summary,
        items=body.items,
        est_cost=est_cost,
    )
    return update_day(client, trip.id, n, user_id, day_update)


@router.post("/{id}/members", response_model=MemberResponse, status_code=201)
async def add_trip_member(
    id: UUID,
    body: AddMemberRequest,
    access: Annotated[tuple[TripRecord, UUID], Depends(require_trip_owner)],
    client: Annotated[Client, Depends(get_supabase_client)],
) -> MemberResponse:
    """Add a group member to a trip by email (owner only)."""
    trip, _ = access

    # In a full Supabase environment, users can be resolved via auth.users RPC or admin API
    # Here we resolve/upsert the member record
    # Mock fallback user_id generated deterministically from email if not in users table
    from uuid import NAMESPACE_URL, uuid5
    target_user_id = uuid5(NAMESPACE_URL, body.email)

    client.table("trip_members").upsert(
        {
            "trip_id": str(trip.id),
            "user_id": str(target_user_id),
            "role": body.role,
        },
        on_conflict="trip_id,user_id",
    ).execute()

    return MemberResponse(
        trip_id=trip.id,
        user_id=target_user_id,
        email=body.email,
        role=body.role,
    )


@router.delete("/{id}/members/{user_id}", status_code=204)
async def remove_trip_member(
    id: UUID,
    user_id: UUID,
    access: Annotated[tuple[TripRecord, UUID], Depends(require_trip_owner)],
    client: Annotated[Client, Depends(get_supabase_client)],
) -> Response:
    """Remove a group member from a trip (owner only)."""
    trip, _ = access
    if user_id == trip.owner_id:
        raise AppError(status_code=400, code="INVALID_ACTION", message="Cannot remove the owner of the trip.")

    client.table("trip_members").delete().eq("trip_id", str(trip.id)).eq("user_id", str(user_id)).execute()
    return Response(status_code=204)


@router.get("/{id}/summary", response_model=TripSummaryResponse)
async def get_trip_summary(
    id: UUID,
    access: Annotated[tuple[TripRecord, UUID], Depends(require_trip_viewer)],
    client: Annotated[Client, Depends(get_supabase_client)],
) -> TripSummaryResponse:
    """Get cost and budget breakdown by category for a trip."""
    trip, user_id = access
    days = get_days(client, trip.id, user_id)

    category_totals: dict[str, float] = {
        "attraction": 0.0,
        "dining": 0.0,
        "transport": 0.0,
        "stay": 0.0,
        "activity": 0.0,
    }

    activities_cost = 0.0
    for day in days:
        for item in day.items:
            cat = str(item.get("type", "activity")).lower()
            cost = float(item.get("est_cost", 0.0))
            category_totals[cat] = category_totals.get(cat, 0.0) + cost
            activities_cost += cost

    num_days = max((trip.end_date - trip.start_date).days + 1, len(days), 1)
    stay_nightly = float(trip.stay.get("price_per_night", 0.0)) if trip.stay else 0.0
    accommodation_cost = stay_nightly * max(num_days - 1, 1)
    category_totals["stay"] += accommodation_cost

    total_est = activities_cost + accommodation_cost

    breakdowns: list[CategoryCostBreakdown] = []
    for cat, cost in category_totals.items():
        pct = (cost / total_est * 100.0) if total_est > 0 else 0.0
        breakdowns.append(
            CategoryCostBreakdown(
                category=cat,
                total_cost=round(cost, 2),
                percentage=round(pct, 1),
            )
        )

    budget = trip.budget or 0.0
    difference = round(budget - total_est, 2)
    if budget <= 0:
        budget_status = "on_budget"
    elif total_est > budget * 1.05:
        budget_status = "over_budget"
    elif total_est < budget * 0.90:
        budget_status = "under_budget"
    else:
        budget_status = "on_budget"

    return TripSummaryResponse(
        trip_id=trip.id,
        currency=trip.currency,
        budget=trip.budget,
        total_estimated_cost=round(total_est, 2),
        accommodation_cost=round(accommodation_cost, 2),
        activities_cost=round(activities_cost, 2),
        budget_status=budget_status,
        difference=difference,
        categories=breakdowns,
    )
