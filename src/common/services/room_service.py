from src.common.repository.room_repo import RoomRepository
from src.common.models.rooms import RoomStatus
from typing import List, Optional


class RoomService:
    def __init__(self, room_repo: RoomRepository):
        self.room_repo = room_repo

    def update_room_status(
        self, room_id: str, status: Optional[str] = RoomStatus.HOUSEKEEPING
    ):
        self.room_repo.update_room_status(room_id, status)
