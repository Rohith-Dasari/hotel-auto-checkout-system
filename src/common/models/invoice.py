from dataclasses import dataclass
from datetime import datetime


@dataclass
class Invoice:
    booking_id: str
    user_email: str
    room_id: str
    category: str
    checkin: datetime
    checkout: datetime
    nights: int
    price_per_night: float
    total_amount: float
