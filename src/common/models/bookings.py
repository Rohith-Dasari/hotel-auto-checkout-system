from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


class BookingStatus(str, Enum):
    UPCOMING = "UPCOMING"
    CHECKED_IN = "CHECKED_IN"
    CHECKED_OUT = "CHECKED_OUT"


@dataclass
class Category:
    name: str
    price_per_night: float


@dataclass
class Booking:
    booking_id: str
    user_id: str
    user_email: str
    room_id: str
    category: str
    checkin: datetime
    checkout: datetime
    status: BookingStatus = BookingStatus.UPCOMING

    price_per_night: float = 0.0

    invoice_url: Optional[str] = None
    scheduler_id: Optional[str] = None

    created_at: datetime = field(default_factory=datetime.now(timezone.utc))
