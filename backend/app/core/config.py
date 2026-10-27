import sys
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    env: str = "development"
    port: int = 8000
    # Support both ALLOWED_ORIGINS and legacy CORS_ORIGIN
    allowed_origins: str | None = None
    cors_origin: str = "http://localhost:5173"

    supabase_url: str = "https://placeholder.supabase.co"
    supabase_anon_key: str = "placeholder-anon-key"
    supabase_service_role_key: str = "placeholder-service-role-key"
    supabase_jwt_secret: str = "super-secret-jwt-token-with-at-least-32-characters-long"

    ai_provider: str = "gemini"
    gemini_api_key: str = "placeholder-gemini-key"
    gemini_model: str = "gemini-2.5-flash"

    # Rate limiting & quota protection
    max_daily_generations: int = 50
    demo_user_id: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def cors_origins_list(self) -> list[str]:
        origins_str = self.allowed_origins or self.cors_origin
        return [origin.strip() for origin in origins_str.split(",") if origin.strip()]


def validate_startup_env(settings: Settings) -> None:
    """Validate required environment variables when running in production."""
    if settings.env.lower() in ("production", "prod"):
        missing: list[str] = []
        required_vars = [
            ("SUPABASE_URL", settings.supabase_url, "placeholder"),
            ("SUPABASE_SERVICE_ROLE_KEY", settings.supabase_service_role_key, "placeholder"),
            ("SUPABASE_JWT_SECRET", settings.supabase_jwt_secret, "super-secret"),
            ("GEMINI_API_KEY", settings.gemini_api_key, "placeholder"),
        ]
        for name, value, placeholder_substr in required_vars:
            if not value or placeholder_substr in value:
                missing.append(name)

        if missing:
            msg = (
                f"\n[FATAL] Missing required production environment variables: {', '.join(missing)}\n"
                f"Please define them in your environment or hosting dashboard.\n"
            )
            sys.stderr.write(msg)
            sys.stderr.flush()
            raise RuntimeError(f"Missing required production environment variables: {', '.join(missing)}")


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings instance."""
    s = Settings()
    validate_startup_env(s)
    return s
