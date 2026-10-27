from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.auth import get_current_user

router = APIRouter(tags=["system"])


class HealthResponse(BaseModel):
    status: str


class MeResponse(BaseModel):
    user_id: str


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Public health check endpoint."""
    return HealthResponse(status="ok")


@router.get("/api/me", response_model=MeResponse)
async def get_me(user_id: Annotated[str, Depends(get_current_user)]) -> MeResponse:
    """Protected route returning the authenticated user's ID."""
    return MeResponse(user_id=user_id)
