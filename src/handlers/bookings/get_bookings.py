import os
import json
from boto3 import resource

from src.common.repository.booking_repo import BookingRepository
from src.common.repository.user_repo import UserRepository
from src.common.repository.room_repo import RoomRepository
from src.common.services.booking_service import BookingService
from src.common.models.users import UserRole
from src.common.utils.custom_response import send_custom_response
from src.common.utils.custom_exceptions import NotFoundException

TABLE_NAME = os.environ.get("TABLE_NAME")

dynamodb = resource("dynamodb", region_name="ap-south-1")
table = dynamodb.Table(TABLE_NAME)

booking_repo = BookingRepository(table)
user_repo = UserRepository(table)
room_repo = RoomRepository(table)

booking_service = BookingService(
    booking_repo=booking_repo,
    user_repo=user_repo,
    room_repo=room_repo,
)


def get_user_bookings(event, context):
    try:
        try:
            authorizer = event["requestContext"]["authorizer"]
            user_id = authorizer["user_id"]
            role_raw = authorizer.get("role")
        except KeyError:
            return send_custom_response(401, "Unauthorized")

        role = None
        if role_raw:
            try:
                role = UserRole(role_raw.upper())
            except ValueError:
                role = None

        requested_user_id = user_id
        if event.get("body"):
            try:
                body = json.loads(event["body"])
                requested_user_id = body.get("user_id", user_id)
            except json.JSONDecodeError:
                return send_custom_response(400, "Invalid JSON body")

        if role == UserRole.CUSTOMER and requested_user_id != user_id:
            return send_custom_response(401, "Unauthorized")

        target_user_id = requested_user_id if role in {UserRole.MANAGER, UserRole.ADMIN} else user_id

        bookings = booking_service.get_user_bookings(target_user_id)

        result = []
        for b in bookings:
            result.append({
                "booking_id": b.booking_id,
                "room_id": b.room_id,
                "category": b.category.value,
                "status": b.status.value,
                "checkin": b.checkin,
                "checkout": b.checkout,
                "price_per_night": b.price_per_night,
                "booked_at": b.booked_at
            })

        return send_custom_response(
            200,
            "Bookings retrieved successfully",
            {
                "count": len(result),
                "bookings": result
            }
        )

    except NotFoundException as err:
        return send_custom_response(err.status_code, str(err))

    except Exception as err:
        print("Unhandled error:", err)
        return send_custom_response(500, "Internal server error")
