import re

DISALLOWED_PROMPT_PATTERNS = [
    r"ignore previous instructions",
    r"system override",
    r"you are now",
    r"jailbreak",
    r"reveal prompt",
    r"<\|im_start\|>",
    r"<\|im_end\|>",
]


def sanitize_user_input(text: str, max_length: int = 500) -> str:
    """Sanitize free-text user prompts against prompt injection and control instructions."""
    if not text:
        return ""

    sanitized = text.strip()[:max_length]
    for pattern in DISALLOWED_PROMPT_PATTERNS:
        sanitized = re.sub(pattern, "[sanitized]", sanitized, flags=re.IGNORECASE)

    # Strip dangerous shell/template chars
    sanitized = sanitized.replace("{", "(").replace("}", ")")
    return sanitized
