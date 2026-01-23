import os
from src.common.services.booking_service import BookingService
from src.common.repository.booking_repo import BookingRepository
from src.common.repository.user_repo import UserRepository
from src.common.repository.room_repo import RoomRepository
from src.common.services.room_service import RoomService
from boto3 import resource

TABLE_NAME = os.environ.get("checkout_system_db")
dynamodb = resource("dynamodb", region_name="ap-south-1")
table = dynamodb.Table(TABLE_NAME)

booking_repo = BookingRepository(table)
user_repo = UserRepository(table)
room_repo = RoomRepository(table)
booking_service = BookingService(
    booking_repo=booking_repo, user_repo=user_repo, room_repo=room_repo
)
room_service = RoomService(room_repo=room_repo)


def auto_checkout(event, context):
    booking_id = event["bookingId"]
    room_id = event["room_id"]
    booking_service.update_booking(booking_id=booking_id, room_id=room_id)
    booking_service.send_invoice(booking_id)
