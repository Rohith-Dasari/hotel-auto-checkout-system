from enum import Enum
from dataclasses import dataclass


class UserRole(Enum):
    ADMIN = "ADMIN"
    MANAGER = "MANAGER"
    CUSTOMER = "CUSTOMER"


@dataclass
class User:
    user_id: str
    email: str
    name: str
    role: UserRole
