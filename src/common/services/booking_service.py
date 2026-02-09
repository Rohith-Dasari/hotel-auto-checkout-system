from common.repository.booking_repo import BookingRepository
from common.models.bookings import Booking, BookingStatus
from common.schemas.bookings import BookingRequest
from common.models.rooms import Category
from typing import List,Optional
from common.repository.user_repo import UserRepository
from common.repository.room_repo import RoomRepository
from common.utils.custom_exceptions import NotFoundException,NoAvailableRooms
from common.services.schedule_service import SchedulerService
from uuid import uuid4
import random

class BookingService:
    def __init__(
        self,
        booking_repo: BookingRepository,
        user_repo: UserRepository,
        room_repo: RoomRepository,
        schedule_service:Optional[SchedulerService]=None
    ):
        self.booking_repo = booking_repo
        self.user_repo = user_repo
        self.room_repo = room_repo
        self.schedule_service=schedule_service

    def add_booking(self, req: BookingRequest, user_id: str):
        user = self.user_repo.get_by_id(user_id)
        if user is None:
            raise NotFoundException(
                resource="user", identifier=user_id, status_code=404
            )
        category = Category(req.category.upper())
        price = self.room_repo.get_category_price(category)
        if price is None:
            raise NotFoundException("category", category.value, 404)

        price = float(price)
        booking_id = str(uuid4())
        room_id = self._allocate_room(category,req)
        booking = Booking(
            booking_id=booking_id,
            user_id=user_id,
            room_id=room_id,
            category=category,
            checkin=req.checkin,
            checkout=req.checkout,
            price_per_night=price,
            user_email=user.email,
        )
        self.booking_repo.add_booking(booking)
        if self.schedule_service:
            self.schedule_service.schedule_checkout(
                booking_id=booking_id,
                user_id=user_id,
                room_id=room_id,
                checkout_time=booking.checkout,
            )

    def update_booking(self, booking_id: str, user_id:str,room_id:str):
        self.booking_repo.update_booking_status(
            booking_id=booking_id,
            user_id=user_id,
            room_id=room_id,
            status=BookingStatus.CHECKED_OUT,
        )                                          
                         
    def _allocate_room(self, category: Category, req: BookingRequest) -> str:
        rooms = self.room_repo.get_available_rooms(
            category,
            req.checkin,
            req.checkout
        )

        if not rooms:
            raise NoAvailableRooms("no available rooms for the category")

        return random.choice(rooms)

    
    def get_user_bookings(self,user_id)->List[Booking]:
        user=self.user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundException("user", user_id, 404)
        return self.booking_repo.get_user_bookings(user_id)

