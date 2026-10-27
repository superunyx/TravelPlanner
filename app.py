"""Personalized Travel Itinerary Planner API Entry Point.

Full-stack AI web app generating structured, day-by-day travel itineraries.
Usage:
  Direct run:   python app.py
  Uvicorn CLI:  uvicorn app:app --host 0.0.0.0 --port 8000 --reload
"""

import importlib.util
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock

# Stub transient sub-dependencies if not yet present
for mod in ["multidict", "propcache", "propcache.api"]:
    if mod not in sys.modules:
        m = MagicMock()
        m.istr = str
        m.under_cached_property = property
        sys.modules[mod] = m

CURRENT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = CURRENT_DIR / "backend"

# Ensure backend directory is in sys.path
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Ensure backend/app is importable as backend_app
backend_app_path = BACKEND_DIR / "app"
backend_init_path = backend_app_path / "__init__.py"
pkg_spec = importlib.util.spec_from_file_location(
    "backend_app",
    backend_init_path,
    submodule_search_locations=[str(backend_app_path)],
)
if pkg_spec and pkg_spec.loader:
    app_pkg = importlib.util.module_from_spec(pkg_spec)
    sys.modules["app"] = app_pkg
    sys.modules["backend_app"] = app_pkg
    pkg_spec.loader.exec_module(app_pkg)

# Import the FastAPI application instance
from app.main import app as fastapi_app

# Export 'app' attribute on sys.modules['app'] so uvicorn app:app finds it
sys.modules["app"].app = fastapi_app  # type: ignore[attr-defined]
app = fastapi_app

__all__ = ["app"]

if __name__ == "__main__":
    import uvicorn

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))

    uvicorn.run(
        app,
        host=host,
        port=port,
    )
