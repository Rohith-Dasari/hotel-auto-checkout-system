from src.common.repository.room_repo import RoomRepository
from src.common.models.rooms import RoomStatus, Category
from typing import List, Optional
from src.common.utils.custom_exceptions import NoAvailableRooms


class RoomService:
    def __init__(self, room_repo: RoomRepository):
        self.room_repo = room_repo

    def update_room_status(
        self, room_id: str, status: Optional[str] = RoomStatus.HOUSEKEEPING
    ):
        self.room_repo.update_room_status(room_id, status)
        
    def get_available_rooms(self,category:Category,checkin,checkout):
        rooms= self.room_repo.get_available_rooms(category,checkin,checkout)
        if not rooms:
            raise NoAvailableRooms(f"no {category} for {checkin} to {checkout}")
        return rooms 
             
