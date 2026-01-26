from datetime import datetime, timezone
from pydantic import BaseModel, model_validator
from typing import Optional

from src.common.models.bookings import BookingStatus


class BookingRequest(BaseModel):
    category: str
    checkin: datetime
    checkout: datetime

    @model_validator(mode="after")
    def validate_and_normalize(self):
        if self.checkin.tzinfo is None or self.checkout.tzinfo is None:
            raise ValueError("checkin and checkout must include timezone info")

        checkin_utc = self.checkin.astimezone(timezone.utc)
        checkout_utc = self.checkout.astimezone(timezone.utc)
        now_utc = datetime.now(timezone.utc)

        if checkin_utc <= now_utc:
            raise ValueError("checkin must be in the future")

        if checkout_utc <= checkin_utc:
            raise ValueError("checkout must be after checkin")

        self.checkin = checkin_utc
        self.checkout = checkout_utc

        return self
