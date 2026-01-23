from dataclasses import dataclass
from datetime import datetime
from src.common.models.rooms import Category


@dataclass
class Invoice:
    booking_id: str
    user_email: str
    room_no: str
    category: Category
    checkin: datetime
    checkout: datetime
    nights: int
    price_per_night: float
    total_amount: float
