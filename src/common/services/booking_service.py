from src.common.repository.booking_repo import BookingRepository
from src.common.models.bookings import BookingRequest, Booking, BookingStatus
from src.common.models.rooms import Category
from typing import List
from src.common.models.users import User
from src.common.repository.user_repo import UserRepository
from src.common.repository.room_repo import RoomRepository
from src.common.utils.custom_exceptions import NotFoundException
from src.common.models.invoice import Invoice
from src.common.services.schedule_service import SchedulerService
from uuid import uuid4
import random

class BookingService:
    def __init__(
        self,
        booking_repo: BookingRepository,
        user_repo: UserRepository,
        room_repo: RoomRepository,
        schedule_service:SchedulerService
    ):
        self.booking_repo = booking_repo
        self.user_repo = user_repo
        self.room_repo = room_repo
        self.schedule_service=schedule_service

    def add_booking(self, req: BookingRequest, user_id: str):
        user = self.user_repo.get_by_id(req.user_id)
        if user is None:
            raise NotFoundException(
                resource="user", identifier=user_id, status_code=404
            )
        category = Category(req.category)
        price = self.room_repo.get_category_price(category)
        booking_id = str(uuid4())
        room_id = self._allocate_room(category,req)
        if not room_id:
            raise Exception("No rooms available")
        booking = Booking(
            booking_id=booking_id,
            user_id=user_id,
            room_id=room_id,
            category=category,
            checkin=req.checkin,
            checkout=req.checkout,
            price_per_night=price,
        )
        self.booking_repo.add_booking(booking)
        self.schedule_service.schedule_checkout(booking_id=booking_id,room_id=room_id,checkout_time=booking.checkout)

    def update_booking(self, booking_id: str, room_id: str):
        booking = self.booking_repo.get_booking_by_id(booking_id)
        self.booking_repo.update_booking_status(
            booking_id=booking_id,
            user_id=booking.user_id,
            room_id=room_id,
            status=BookingStatus.CHECKED_OUT,
        )
    def _allocate_room(self,category:str,req:BookingRequest)->str:
        rooms=self.room_repo.get_available_rooms(category,req.checkin,req.checkout)
        if not rooms:
            raise NotFoundException("no available rooms for the category")
        room_id = random.choice(rooms)
        return room_id
    
    def get_user_bookings(self,user_id)->List[Booking]:
        user=self.user_repo.get_by_id(user_id)
        if not user:
            NotFoundException(f"user {user_id} not found")
        return self.booking_repo.get_user_bookings(user_id)
    
