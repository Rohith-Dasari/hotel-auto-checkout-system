from enum import Enum
from typing import Optional
from dataclasses import dataclass


class Category(str, Enum):
    DELUXE = "DELUXE"
    SUITE = "SUITE"
    STANDARD = "STANDARD"


@dataclass
class RoomType:
    name: Category
    price_per_night: float


class RoomStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    OCCUPIED = "OCCUPIED"
    HOUSEKEEPING = "HOUSEKEEPING"
    MAINTENANCE = "MAINTENANCE"


@dataclass
class Room:
    room_id: str
    category: Category
    status: RoomStatus = RoomStatus.AVAILABLE
    floor: Optional[int] = None
