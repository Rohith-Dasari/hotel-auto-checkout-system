from datetime import datetime, timezone

def from_iso_string(value: str) -> datetime:
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        raise ValueError("Stored datetime must be timezone-aware")
    return dt.astimezone(timezone.utc)