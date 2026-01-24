import os
from boto3 import resource

from src.common.repository.booking_repo import BookingRepository
from src.common.repository.user_repo import UserRepository
from src.common.repository.room_repo import RoomRepository
from src.common.services.booking_service import BookingService
from src.common.services.schedule_service import SchedulerService
from src.common.utils.custom_response import send_custom_response
from src.common.utils.custom_exceptions import NotFoundException

TABLE_NAME = os.environ.get("table_name")

dynamodb = resource("dynamodb", region_name="ap-south-1")
table = dynamodb.Table(TABLE_NAME)

booking_repo = BookingRepository(table)
user_repo = UserRepository(table)
room_repo = RoomRepository(table)
scheduler_service = SchedulerService()

booking_service = BookingService(
    booking_repo=booking_repo,
    user_repo=user_repo,
    room_repo=room_repo,
    schedule_service=scheduler_service
)


def get_user_bookings(event, context):
    try:
        try:
            user_id = event["requestContext"]["authorizer"]["user_id"]
        except KeyError:
            return send_custom_response(401, "Unauthorized")

        bookings = booking_service.get_user_bookings(user_id)

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
