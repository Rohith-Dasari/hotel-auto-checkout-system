import os
from src.common.services.booking_service import BookingService
from src.common.repository.booking_repo import BookingRepository
from src.common.repository.user_repo import UserRepository
from src.common.repository.room_repo import RoomRepository
from src.common.services.invoice_service import InvoiceService
from src.common.utils.custom_exceptions import NotFoundException
from boto3 import resource
from botocore.exceptions import ClientError

TABLE_NAME = os.environ.get("TABLE_NAME")
dynamodb = resource("dynamodb", region_name="ap-south-1")
table = dynamodb.Table(TABLE_NAME)

booking_repo = BookingRepository(table)
user_repo = UserRepository(table)
room_repo = RoomRepository(table)
booking_service = BookingService(
    booking_repo=booking_repo, user_repo=user_repo, room_repo=room_repo
)
invoice_service=InvoiceService(booking_repo)


def auto_checkout(event, context):
    booking_id = event.get("booking_id") 
    room_id = event.get("room_id") 
    user_id = event.get("user_id") 

    if not booking_id or not room_id or not user_id:
        raise KeyError("Missing booking_id, room_id, or user_id in event")

    try:
        booking_service.update_booking(booking_id=booking_id, room_id=room_id, user_id=user_id)
        invoice_service.send_invoice(booking_id)
    except NotFoundException as err:
        print(f"Auto-checkout failed: {err}")
    except ClientError as err:
        print(f"Auto-checkout failed: {err}")
    except Exception as err:
        print(f"Auto-checkout failed: {err}")
