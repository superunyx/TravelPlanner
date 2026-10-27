from typing import Annotated, Any

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import Settings, get_settings
from app.core.errors import AppError

security = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> str:
    """Verify the Supabase HS256 JWT token and return the user_id (sub claim)."""
    if credentials is None or not credentials.credentials:
        raise AppError(
            status_code=401,
            code="UNAUTHORIZED",
            message="Missing authentication token.",
        )

    token = credentials.credentials
    try:
        payload: dict[str, Any] = jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            options={"verify_aud": False},
        )
    except jwt.ExpiredSignatureError as exc:
        raise AppError(
            status_code=401,
            code="TOKEN_EXPIRED",
            message="Authentication token has expired.",
        ) from exc
    except jwt.InvalidTokenError as exc:
        raise AppError(
            status_code=401,
            code="INVALID_TOKEN",
            message="Invalid authentication token.",
        ) from exc

    user_id = payload.get("sub")
    if not isinstance(user_id, str) or not user_id.strip():
        raise AppError(
            status_code=401,
            code="INVALID_TOKEN",
            message="Token payload is missing a valid 'sub' user identifier.",
        )

    return user_id
