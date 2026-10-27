from typing import Annotated, Literal
from uuid import UUID

from fastapi import Depends
from supabase import Client

from app.core.auth import get_current_user
from app.core.errors import AppError
from app.db.client import get_supabase_client
from app.db.trips_repo import get_trip
from app.schemas.db import TripRecord

PermissionRole = Literal["owner", "editor", "viewer"]


class TripAccessChecker:
    """Dependency checker verifying the authenticated user has sufficient trip permissions."""

    def __init__(self, allowed_roles: set[PermissionRole]) -> None:
        self.allowed_roles = allowed_roles

    def __call__(
        self,
        id: UUID,
        user_id_str: Annotated[str, Depends(get_current_user)],
        client: Annotated[Client, Depends(get_supabase_client)],
    ) -> tuple[TripRecord, UUID]:
        try:
            user_id = UUID(user_id_str)
        except ValueError as exc:
            raise AppError(status_code=401, code="INVALID_USER_ID", message="Invalid user id.") from exc

        trip = get_trip(client, id, user_id)
        if trip is None:
            raise AppError(status_code=404, code="TRIP_NOT_FOUND", message="Trip not found.")

        if trip.owner_id == user_id:
            return trip, user_id

        # Check membership role
        resp = (
            client.table("trip_members")
            .select("role")
            .eq("trip_id", str(id))
            .eq("user_id", str(user_id))
            .limit(1)
            .execute()
        )
        rows = resp.data or []
        if not rows:
            raise AppError(status_code=403, code="FORBIDDEN", message="You do not have access to this trip.")

        member_role = str(rows[0].get("role", "viewer"))
        if member_role not in self.allowed_roles:
            raise AppError(
                status_code=403,
                code="FORBIDDEN",
                message=f"Insufficient permissions. Required role: {sorted(self.allowed_roles)}, but user is '{member_role}'.",
            )

        return trip, user_id


require_trip_viewer = TripAccessChecker(allowed_roles={"owner", "editor", "viewer"})
require_trip_editor = TripAccessChecker(allowed_roles={"owner", "editor"})
require_trip_owner = TripAccessChecker(allowed_roles={"owner"})
