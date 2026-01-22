from enum import Enum
from typing import Optional
from dataclasses import dataclass


class RoomStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    OCCUPIED = "OCCUPIED"
    HOUSEKEEPING = "HOUSEKEEPING"
    MAINTENANCE = "MAINTENANCE"


@dataclass
class Room:
    room_id: str
    category: str
    status: RoomStatus = RoomStatus.AVAILABLE
    floor: Optional[int] = None
