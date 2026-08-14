from datetime import date


def parse_optional_date(text: str) -> date | None:
    """Parses a YYYY-MM-DD form field; blank means "not set", not an error.

    Raises ValueError on a non-blank but malformed date, which callers surface to the
    user the same way they surface other invalid-input errors.
    """
    text = text.strip()
    return date.fromisoformat(text) if text else None
