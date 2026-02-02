from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from common.models.rooms import Category


class BookingStatus(str, Enum):
    UPCOMING = "UPCOMING"
    CHECKED_IN = "CHECKED_IN"
    CHECKED_OUT = "CHECKED_OUT"


@dataclass
class Booking:
    booking_id: str
    user_id: str
    user_email: str
    room_id: str
    category: Category
    checkin: datetime
    checkout: datetime
    status: BookingStatus = BookingStatus.UPCOMING

    price_per_night: float = 0.0

    invoice_url: Optional[str] = None

    booked_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


