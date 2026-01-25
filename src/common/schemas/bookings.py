from datetime import datetime
from typing import Optional
from  src.common.models.bookings import BookingStatus
from pydantic import BaseModel


class BookingRequest(BaseModel):
    category: str
    checkin: datetime
    checkout: datetime

class BookingResponse(BaseModel):
    booking_id: str
    room_id: str
    status: BookingStatus
    checkin: datetime
    checkout: datetime
    invoice_url: Optional[str] = None
