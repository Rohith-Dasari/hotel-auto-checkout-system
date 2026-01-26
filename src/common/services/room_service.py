from src.common.repository.room_repo import RoomRepository
from src.common.models.rooms import RoomStatus, Category
from typing import List, Optional
from src.common.utils.custom_exceptions import NoAvailableRooms, InvalidDates
from datetime import datetime, timezone


class RoomService:
    def __init__(self, room_repo: RoomRepository):
        self.room_repo = room_repo

    def update_room_status(
        self, room_id: str, status: Optional[str] = RoomStatus.HOUSEKEEPING
    ):
        self.room_repo.update_room_status(room_id, status)
        
    def _ensure_datetime(self, value):
        if isinstance(value, datetime):
            dt = value
        else:
            dt = datetime.fromisoformat(value)

        if dt.tzinfo is None:
            raise InvalidDates("checkin/checkout must include timezone info")

        return dt.astimezone(timezone.utc)

    def get_available_rooms(self, category: Category, checkin, checkout):

        checkin_dt = self._ensure_datetime(checkin)
        checkout_dt = self._ensure_datetime(checkout)

        if checkout_dt <= checkin_dt:
            raise InvalidDates(
                "checkout must be after checkin"
            )

        rooms = self.room_repo.get_available_rooms(category, checkin_dt, checkout_dt)

        if not rooms:
            raise NoAvailableRooms(f"no {category} for {checkin_dt} to {checkout_dt}")
        return rooms 
             
