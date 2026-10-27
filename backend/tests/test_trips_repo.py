from dataclasses import dataclass
from datetime import date
from typing import Any
from uuid import UUID, uuid4

import pytest
from app.core.errors import AppError
from app.db.trips_repo import (
    create_trip,
    delete_trip,
    get_days,
    get_trip,
    list_trips,
    update_day,
    update_trip,
    upsert_days,
)
from app.schemas.db import DayUpdate, DayUpsert, TripCreate, TripUpdate
from supabase import Client


@dataclass
class FakeResponse:
    data: list[dict[str, Any]]


class FakeTableQuery:
    """In-memory fluent query builder mimicking supabase-py PostgREST chains."""

    def __init__(self, store: dict[str, list[dict[str, Any]]], table_name: str) -> None:
        self._store = store
        self._table_name = table_name
        self._op: str = "select"
        self._payload: Any = None
        self._on_conflict: str | None = None
        self._filters: list[tuple[str, str, Any]] = []
        self._order_col: str | None = None
        self._order_desc: bool = False
        self._limit_val: int | None = None

    def select(self, _columns: str = "*") -> "FakeTableQuery":
        self._op = "select"
        return self

    def insert(self, payload: dict[str, Any] | list[dict[str, Any]]) -> "FakeTableQuery":
        self._op = "insert"
        self._payload = payload
        return self

    def update(self, payload: dict[str, Any]) -> "FakeTableQuery":
        self._op = "update"
        self._payload = payload
        return self

    def upsert(
        self,
        payload: dict[str, Any] | list[dict[str, Any]],
        on_conflict: str | None = None,
    ) -> "FakeTableQuery":
        self._op = "upsert"
        self._payload = payload
        self._on_conflict = on_conflict
        return self

    def delete(self) -> "FakeTableQuery":
        self._op = "delete"
        return self

    def eq(self, column: str, value: Any) -> "FakeTableQuery":
        self._filters.append(("eq", column, value))
        return self

    def in_(self, column: str, values: list[Any]) -> "FakeTableQuery":
        self._filters.append(("in", column, values))
        return self

    def order(self, column: str, desc: bool = False) -> "FakeTableQuery":
        self._order_col = column
        self._order_desc = desc
        return self

    def limit(self, count: int) -> "FakeTableQuery":
        self._limit_val = count
        return self

    def _matches(self, row: dict[str, Any]) -> bool:
        for kind, col, val in self._filters:
            if kind == "eq" and str(row.get(col)) != str(val):
                return False
            if kind == "in" and str(row.get(col)) not in {str(v) for v in val}:
                return False
        return True

    def execute(self) -> FakeResponse:
        rows = self._store.setdefault(self._table_name, [])

        if self._op == "insert":
            items = (
                self._payload if isinstance(self._payload, list) else [self._payload]
            )
            inserted: list[dict[str, Any]] = []
            for item in items:
                record = dict(item)
                record.setdefault("id", str(uuid4()))
                record.setdefault("created_at", "2026-10-24T10:00:00Z")
                record.setdefault("updated_at", "2026-10-24T10:00:00Z")
                rows.append(record)
                inserted.append(dict(record))
            return FakeResponse(data=inserted)

        if self._op == "upsert":
            items = (
                self._payload if isinstance(self._payload, list) else [self._payload]
            )
            conflict_cols = (
                [c.strip() for c in self._on_conflict.split(",")]
                if self._on_conflict
                else ["id"]
            )
            upserted: list[dict[str, Any]] = []
            for item in items:
                existing = next(
                    (
                        r
                        for r in rows
                        if all(str(r.get(c)) == str(item.get(c)) for c in conflict_cols)
                    ),
                    None,
                )
                if existing is not None:
                    existing.update(item)
                    upserted.append(dict(existing))
                else:
                    record = dict(item)
                    record.setdefault("id", str(uuid4()))
                    rows.append(record)
                    upserted.append(dict(record))
            return FakeResponse(data=upserted)

        if self._op == "update":
            updated: list[dict[str, Any]] = []
            for r in rows:
                if self._matches(r):
                    r.update(self._payload)
                    r["updated_at"] = "2026-10-24T12:00:00Z"
                    updated.append(dict(r))
            return FakeResponse(data=updated)

        if self._op == "delete":
            deleted: list[dict[str, Any]] = []
            remaining: list[dict[str, Any]] = []
            for r in rows:
                if self._matches(r):
                    deleted.append(dict(r))
                else:
                    remaining.append(r)
            self._store[self._table_name] = remaining
            return FakeResponse(data=deleted)

        # select
        matched = [dict(r) for r in rows if self._matches(r)]
        if self._order_col:
            matched.sort(
                key=lambda x: x.get(self._order_col, ""),
                reverse=self._order_desc,
            )
        if self._limit_val is not None:
            matched = matched[: self._limit_val]
        return FakeResponse(data=matched)


class FakeSupabaseClient:
    def __init__(self) -> None:
        self.store: dict[str, list[dict[str, Any]]] = {
            "trips": [],
            "itinerary_days": [],
            "trip_members": [],
        }

    def table(self, name: str) -> FakeTableQuery:
        return FakeTableQuery(self.store, name)


@pytest.fixture
def mock_client() -> Client:
    return FakeSupabaseClient()  # type: ignore[return-value]


@pytest.fixture
def owner_id() -> UUID:
    return uuid4()


@pytest.fixture
def editor_id() -> UUID:
    return uuid4()


@pytest.fixture
def viewer_id() -> UUID:
    return uuid4()


@pytest.fixture
def outsider_id() -> UUID:
    return uuid4()


def _sample_trip_create(owner: UUID) -> TripCreate:
    return TripCreate(
        owner_id=owner,
        title="Kyoto Autumn Escape",
        destination="Kyoto, Japan",
        start_date=date(2026, 11, 10),
        end_date=date(2026, 11, 14),
        budget=150000.0,
        currency="INR",
        travel_style="cultural",
        pacing="moderate",
        group_size=2,
        interests=["temples", "ramen", "gardens"],
        preferences={"dietary": "vegetarian-friendly"},
        stay={"hotel": "Ryokan Nishiyama", "area": "Gion"},
        status="draft",
    )


def test_create_and_get_trip(mock_client: Client, owner_id: UUID) -> None:
    created = create_trip(mock_client, _sample_trip_create(owner_id))
    assert created.title == "Kyoto Autumn Escape"
    assert created.owner_id == owner_id
    assert created.stay["hotel"] == "Ryokan Nishiyama"

    fetched = get_trip(mock_client, created.id, owner_id)
    assert fetched is not None
    assert fetched.id == created.id


def test_get_trip_permissions(
    mock_client: Client,
    owner_id: UUID,
    viewer_id: UUID,
    outsider_id: UUID,
) -> None:
    created = create_trip(mock_client, _sample_trip_create(owner_id))

    # Add viewer member
    mock_client.table("trip_members").insert(
        {"trip_id": str(created.id), "user_id": str(viewer_id), "role": "viewer"}
    ).execute()

    # Viewer can read
    viewer_trip = get_trip(mock_client, created.id, viewer_id)
    assert viewer_trip is not None
    assert viewer_trip.id == created.id

    # Outsider receives 403 FORBIDDEN
    with pytest.raises(AppError) as exc_info:
        get_trip(mock_client, created.id, outsider_id)
    assert exc_info.value.status_code == 403
    assert exc_info.value.code == "FORBIDDEN"


def test_list_trips_includes_owned_and_shared(
    mock_client: Client,
    owner_id: UUID,
    viewer_id: UUID,
) -> None:
    trip1 = create_trip(mock_client, _sample_trip_create(owner_id))
    trip2 = create_trip(mock_client, _sample_trip_create(viewer_id))

    # Share trip1 with viewer_id
    mock_client.table("trip_members").insert(
        {"trip_id": str(trip1.id), "user_id": str(viewer_id), "role": "viewer"}
    ).execute()

    viewer_trips = list_trips(mock_client, viewer_id)
    trip_ids = {t.id for t in viewer_trips}
    assert trip1.id in trip_ids
    assert trip2.id in trip_ids


def test_update_and_delete_trip_owner_only(
    mock_client: Client,
    owner_id: UUID,
    editor_id: UUID,
) -> None:
    created = create_trip(mock_client, _sample_trip_create(owner_id))
    mock_client.table("trip_members").insert(
        {"trip_id": str(created.id), "user_id": str(editor_id), "role": "editor"}
    ).execute()

    # Editor cannot update trip metadata
    with pytest.raises(AppError) as exc_info:
        update_trip(
            mock_client,
            created.id,
            editor_id,
            TripUpdate(title="Unauthorized Rename"),
        )
    assert exc_info.value.status_code == 403

    # Owner can update trip metadata
    updated = update_trip(
        mock_client,
        created.id,
        owner_id,
        TripUpdate(title="Kyoto & Nara Escape", status="generated"),
    )
    assert updated.title == "Kyoto & Nara Escape"
    assert updated.status == "generated"

    # Editor cannot delete trip
    with pytest.raises(AppError) as del_exc:
        delete_trip(mock_client, created.id, editor_id)
    assert del_exc.value.status_code == 403

    # Owner can delete trip
    assert delete_trip(mock_client, created.id, owner_id) is True
    assert get_trip(mock_client, created.id, owner_id) is None


def test_upsert_get_and_update_days_permissions(
    mock_client: Client,
    owner_id: UUID,
    editor_id: UUID,
    viewer_id: UUID,
) -> None:
    trip = create_trip(mock_client, _sample_trip_create(owner_id))
    mock_client.table("trip_members").insert(
        [
            {"trip_id": str(trip.id), "user_id": str(editor_id), "role": "editor"},
            {"trip_id": str(trip.id), "user_id": str(viewer_id), "role": "viewer"},
        ]
    ).execute()

    days_to_upsert = [
        DayUpsert(
            trip_id=trip.id,
            day_number=1,
            date=date(2026, 11, 10),
            summary="Arrival and Gion Walk",
            items=[{"title": "Fushimi Inari", "time": "09:00", "cost": 1500}],
            est_cost=4500.0,
        ),
        DayUpsert(
            trip_id=trip.id,
            day_number=2,
            date=date(2026, 11, 11),
            summary="Arashiyama Bamboo Grove",
            items=[{"title": "Bamboo Forest", "time": "08:00", "cost": 1000}],
            est_cost=5200.0,
        ),
    ]

    # Owner upserts days
    saved_days = upsert_days(mock_client, trip.id, owner_id, days_to_upsert)
    assert len(saved_days) == 2
    assert saved_days[0].day_number == 1

    # Viewer can read days
    fetched_days = get_days(mock_client, trip.id, viewer_id)
    assert len(fetched_days) == 2

    # Viewer cannot update a day
    with pytest.raises(AppError) as view_exc:
        update_day(
            mock_client,
            trip.id,
            1,
            viewer_id,
            DayUpdate(summary="Viewer Edit Attempt"),
        )
    assert view_exc.value.status_code == 403

    # Editor CAN update a day
    edited_day = update_day(
        mock_client,
        trip.id,
        1,
        editor_id,
        DayUpdate(summary="Updated Gion & Kiyomizu-dera Walk", est_cost=6000.0),
    )
    assert edited_day.summary == "Updated Gion & Kiyomizu-dera Walk"
    assert edited_day.est_cost == 6000.0
