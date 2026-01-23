from src.common.repository.booking_repo import BookingRepository
from src.common.models.bookings import BookingRequest, Booking, BookingStatus
from src.common.models.rooms import Category
from src.common.models.users import User
from src.common.repository.user_repo import UserRepository
from src.common.repository.room_repo import RoomRepository
from src.common.utils.custom_exceptions import NotFoundException
from src.common.models.invoice import Invoice
from uuid import uuid4


class BookingService:
    def __init__(
        self,
        booking_repo: BookingRepository,
        user_repo: UserRepository,
        room_repo: RoomRepository,
    ):
        self.booking_repo = booking_repo
        self.user_repo = user_repo
        self.room_repo = room_repo

    def add_booking(self, req: BookingRequest, user_id: str):
        user = self.user_repo.get_by_id(req.user_id)
        if user is None:
            raise NotFoundException(
                resource="user", identifier=user_id, status_code=404
            )
        category = Category(req.category)
        price = self.room_repo.get_category_price(category)
        booking_id = str(uuid4())
        room_id = ""
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

    def update_booking(self, booking_id: str, room_id: str):
        booking = self.booking_repo.get_booking_by_id(booking)
        self.booking_repo.update_booking_status(
            booking_id=booking_id,
            room_id=room_id,
            status=BookingStatus.CHECKED_OUT,
        )
