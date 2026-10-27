from typing import Any, cast
from uuid import UUID

from supabase import Client

from app.core.errors import AppError
from app.schemas.db import (
    DayRecord,
    DayUpdate,
    DayUpsert,
    TripCreate,
    TripRecord,
    TripUpdate,
)


def _user_can_view_trip(client: Client, trip_id: UUID, user_id: UUID) -> bool:
    """Check whether user_id is the trip owner or a member of trip_id."""
    trip_resp = (
        client.table("trips")
        .select("owner_id")
        .eq("id", str(trip_id))
        .limit(1)
        .execute()
    )
    rows = cast(list[dict[str, Any]], trip_resp.data or [])
    if not rows:
        return False
    if str(rows[0].get("owner_id")) == str(user_id):
        return True

    member_resp = (
        client.table("trip_members")
        .select("role")
        .eq("trip_id", str(trip_id))
        .eq("user_id", str(user_id))
        .limit(1)
        .execute()
    )
    member_rows = cast(list[dict[str, Any]], member_resp.data or [])
    return len(member_rows) > 0


def _user_can_edit_days(client: Client, trip_id: UUID, user_id: UUID) -> bool:
    """Check whether user_id is the trip owner or an owner/editor member."""
    trip_resp = (
        client.table("trips")
        .select("owner_id")
        .eq("id", str(trip_id))
        .limit(1)
        .execute()
    )
    rows = cast(list[dict[str, Any]], trip_resp.data or [])
    if not rows:
        return False
    if str(rows[0].get("owner_id")) == str(user_id):
        return True

    member_resp = (
        client.table("trip_members")
        .select("role")
        .eq("trip_id", str(trip_id))
        .eq("user_id", str(user_id))
        .limit(1)
        .execute()
    )
    member_rows = cast(list[dict[str, Any]], member_resp.data or [])
    if not member_rows:
        return False
    return str(member_rows[0].get("role")) in ("owner", "editor")


def create_trip(client: Client, data: TripCreate) -> TripRecord:
    """Insert a new trip and register the owner in trip_members."""
    payload = data.model_dump(mode="json")
    response = client.table("trips").insert(payload).execute()
    rows = cast(list[dict[str, Any]], response.data or [])
    if not rows:
        raise AppError(
            status_code=500,
            code="DB_INSERT_FAILED",
            message="Failed to create trip record.",
        )

    trip = TripRecord.model_validate(rows[0])

    # Ensure owner is also recorded in trip_members for uniform membership queries
    client.table("trip_members").upsert(
        {
            "trip_id": str(trip.id),
            "user_id": str(trip.owner_id),
            "role": "owner",
        },
        on_conflict="trip_id,user_id",
    ).execute()

    return trip


def get_trip(client: Client, trip_id: UUID, user_id: UUID) -> TripRecord | None:
    """Return a trip by ID if user_id is the owner or a trip member."""
    response = (
        client.table("trips")
        .select("*")
        .eq("id", str(trip_id))
        .limit(1)
        .execute()
    )
    rows = cast(list[dict[str, Any]], response.data or [])
    if not rows:
        return None

    trip = TripRecord.model_validate(rows[0])
    if trip.owner_id != user_id and not _user_can_view_trip(client, trip_id, user_id):
        raise AppError(
            status_code=403,
            code="FORBIDDEN",
            message="You do not have permission to view this trip.",
        )

    return trip


def list_trips(client: Client, user_id: UUID) -> list[TripRecord]:
    """List all trips owned by or shared with user_id, ordered by created_at desc."""
    owned_resp = (
        client.table("trips")
        .select("*")
        .eq("owner_id", str(user_id))
        .order("created_at", desc=True)
        .execute()
    )
    owned_rows = cast(list[dict[str, Any]], owned_resp.data or [])

    member_resp = (
        client.table("trip_members")
        .select("trip_id")
        .eq("user_id", str(user_id))
        .execute()
    )
    member_rows = cast(list[dict[str, Any]], member_resp.data or [])
    owned_ids = {str(r["id"]) for r in owned_rows}
    shared_ids = [
        str(r["trip_id"])
        for r in member_rows
        if str(r.get("trip_id")) not in owned_ids
    ]

    shared_rows: list[dict[str, Any]] = []
    if shared_ids:
        shared_resp = (
            client.table("trips")
            .select("*")
            .in_("id", shared_ids)
            .order("created_at", desc=True)
            .execute()
        )
        shared_rows = cast(list[dict[str, Any]], shared_resp.data or [])

    combined = [TripRecord.model_validate(r) for r in [*owned_rows, *shared_rows]]
    combined.sort(key=lambda t: t.created_at, reverse=True)
    return combined


def update_trip(
    client: Client, trip_id: UUID, user_id: UUID, data: TripUpdate
) -> TripRecord:
    """Update trip metadata (owner only)."""
    existing = get_trip(client, trip_id, user_id)
    if existing is None:
        raise AppError(
            status_code=404,
            code="TRIP_NOT_FOUND",
            message="Trip not found.",
        )
    if existing.owner_id != user_id:
        raise AppError(
            status_code=403,
            code="FORBIDDEN",
            message="Only the trip owner can update trip settings.",
        )

    update_payload = data.model_dump(exclude_unset=True, mode="json")
    if not update_payload:
        return existing

    response = (
        client.table("trips")
        .update(update_payload)
        .eq("id", str(trip_id))
        .eq("owner_id", str(user_id))
        .execute()
    )
    rows = cast(list[dict[str, Any]], response.data or [])
    if not rows:
        raise AppError(
            status_code=404,
            code="TRIP_NOT_FOUND",
            message="Trip not found or could not be updated.",
        )
    return TripRecord.model_validate(rows[0])


def delete_trip(client: Client, trip_id: UUID, user_id: UUID) -> bool:
    """Delete a trip (owner only)."""
    existing = get_trip(client, trip_id, user_id)
    if existing is None:
        raise AppError(
            status_code=404,
            code="TRIP_NOT_FOUND",
            message="Trip not found.",
        )
    if existing.owner_id != user_id:
        raise AppError(
            status_code=403,
            code="FORBIDDEN",
            message="Only the trip owner can delete this trip.",
        )

    response = (
        client.table("trips")
        .delete()
        .eq("id", str(trip_id))
        .eq("owner_id", str(user_id))
        .execute()
    )
    rows = cast(list[dict[str, Any]], response.data or [])
    return len(rows) > 0


def upsert_days(
    client: Client, trip_id: UUID, user_id: UUID, days: list[DayUpsert]
) -> list[DayRecord]:
    """Bulk upsert itinerary_days for a trip (owner or editor)."""
    if not _user_can_edit_days(client, trip_id, user_id):
        raise AppError(
            status_code=403,
            code="FORBIDDEN",
            message="You do not have permission to modify itinerary days for this trip.",
        )

    if not days:
        return []

    payloads = [
        {**day.model_dump(mode="json"), "trip_id": str(trip_id)} for day in days
    ]
    response = (
        client.table("itinerary_days")
        .upsert(payloads, on_conflict="trip_id,day_number")
        .execute()
    )
    rows = cast(list[dict[str, Any]], response.data or [])
    records = [DayRecord.model_validate(r) for r in rows]
    records.sort(key=lambda d: d.day_number)
    return records


def get_days(client: Client, trip_id: UUID, user_id: UUID) -> list[DayRecord]:
    """Fetch ordered itinerary_days for a trip (owner or member)."""
    if not _user_can_view_trip(client, trip_id, user_id):
        raise AppError(
            status_code=403,
            code="FORBIDDEN",
            message="You do not have permission to view itinerary days for this trip.",
        )

    response = (
        client.table("itinerary_days")
        .select("*")
        .eq("trip_id", str(trip_id))
        .order("day_number", desc=False)
        .execute()
    )
    rows = cast(list[dict[str, Any]], response.data or [])
    return [DayRecord.model_validate(r) for r in rows]


def update_day(
    client: Client,
    trip_id: UUID,
    day_number: int,
    user_id: UUID,
    data: DayUpdate,
) -> DayRecord:
    """Update a single itinerary day (owner or editor)."""
    if not _user_can_edit_days(client, trip_id, user_id):
        raise AppError(
            status_code=403,
            code="FORBIDDEN",
            message="You do not have permission to update this itinerary day.",
        )

    update_payload = data.model_dump(exclude_unset=True, mode="json")
    response = (
        client.table("itinerary_days")
        .update(update_payload)
        .eq("trip_id", str(trip_id))
        .eq("day_number", day_number)
        .execute()
    )
    rows = cast(list[dict[str, Any]], response.data or [])
    if not rows:
        raise AppError(
            status_code=404,
            code="DAY_NOT_FOUND",
            message=f"Day {day_number} not found for this trip.",
        )
    return DayRecord.model_validate(rows[0])
