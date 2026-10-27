from functools import lru_cache
from typing import Annotated, Any

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient

from app.core.config import Settings, get_settings
from app.core.errors import AppError

security = HTTPBearer(auto_error=False)


@lru_cache
def get_jwk_client(supabase_url: str) -> PyJWKClient:
    """Return a cached JWKS client for Supabase asymmetric JWT verification (ES256/RS256)."""
    jwks_url = f"{supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"
    return PyJWKClient(jwks_url, cache_keys=True)


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> str:
    """Verify the Supabase JWT token (HS256 or ES256/RS256 JWKS) and return user_id (sub claim)."""
    if credentials is None or not credentials.credentials:
        raise AppError(
            status_code=401,
            code="UNAUTHORIZED",
            message="Missing authentication token.",
        )

    token = credentials.credentials
    try:
        header = jwt.get_unverified_header(token)
        alg = header.get("alg", "HS256")

        if alg in ("ES256", "RS256"):
            jwk_client = get_jwk_client(settings.supabase_url)
            signing_key = jwk_client.get_signing_key_from_jwt(token)
            payload: dict[str, Any] = jwt.decode(
                token,
                signing_key.key,
                algorithms=["ES256", "RS256"],
                options={"verify_aud": False},
            )
        else:
            payload = jwt.decode(
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
    except (jwt.InvalidTokenError, jwt.PyJWKClientError) as exc:
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
