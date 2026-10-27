from abc import ABC, abstractmethod
from typing import Any


class LLMProvider(ABC):
    """Abstract provider for structured LLM interactions."""

    @abstractmethod
    def generate_json(
        self,
        system_prompt: str,
        user_prompt: str,
        json_schema: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Generate structured JSON response adhering to optional json_schema."""
