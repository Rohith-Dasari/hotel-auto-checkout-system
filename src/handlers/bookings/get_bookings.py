import os
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

        try:
            role = UserRole(role_raw.upper()) if role_raw else None
        except ValueError:
            role = None

        path_params = event.get("pathParameters") or {}
        requested_user_id = path_params.get("user_id") or user_id

        if role == UserRole.CUSTOMER and requested_user_id != user_id:
            return send_custom_response(403, "Forbidden")

        target_user_id = (
            requested_user_id
            if role in {UserRole.MANAGER, UserRole.ADMIN}
            else user_id
        )

        bookings = booking_service.get_user_bookings(target_user_id)

        result = []
        for b in bookings:
            result.append({
                "booking_id": b.booking_id,
                "room_id": b.room_id,
                "category": b.category.value,
                "status": b.status.value,
                "checkin": b.checkin.isoformat(),
                "checkout": b.checkout.isoformat(),
                "price_per_night": str(b.price_per_night),
                "booked_at": b.booked_at.isoformat()
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

    except Exception:
        return send_custom_response(500, "Internal server error")
