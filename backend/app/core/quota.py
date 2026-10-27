import threading
from datetime import date, datetime, timezone


class QuotaManager:
    """Thread-safe in-memory quota manager tracking daily generations."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._current_date: date = datetime.now(timezone.utc).date()
        self._global_count: int = 0
        self._user_counts: dict[str, int] = {}

    def _reset_if_new_day(self) -> None:
        today = datetime.now(timezone.utc).date()
        if today != self._current_date:
            self._current_date = today
            self._global_count = 0
            self._user_counts.clear()

    def check_and_increment(self, user_id: str, max_daily_global: int = 50, max_per_user: int = 10) -> tuple[bool, str]:
        with self._lock:
            self._reset_if_new_day()

            if self._global_count >= max_daily_global:
                return False, f"Daily generation quota ({max_daily_global}) for this demo server has been reached. Please try again tomorrow."

            user_count = self._user_counts.get(user_id, 0)
            if user_count >= max_per_user:
                return False, f"You have reached your limit of {max_per_user} itinerary generations for today."

            self._global_count += 1
            self._user_counts[user_id] = user_count + 1
            return True, ""


quota_manager = QuotaManager()
