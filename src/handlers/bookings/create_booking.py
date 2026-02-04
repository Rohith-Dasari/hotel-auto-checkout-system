import json
import os
from boto3 import resource

from common.repository.booking_repo import BookingRepository
from common.repository.user_repo import UserRepository
from common.repository.room_repo import RoomRepository
from common.services.booking_service import BookingService
from common.models.rooms import Category
from common.services.schedule_service import SchedulerService
from common.schemas.bookings import BookingRequest
from common.utils.custom_response import send_custom_response
from common.utils.custom_exceptions import NotFoundException, NoAvailableRooms
from pydantic import ValidationError

TABLE_NAME = os.environ.get("TABLE_NAME")
AUTO_CHECKOUT_LAMBDA_ARN = os.environ.get("AUTO_CHECKOUT_LAMBDA_ARN")
SCHEDULER_ROLE_ARN = os.environ.get("SCHEDULER_ROLE_ARN")

dynamodb = resource("dynamodb", region_name="ap-south-1")
table = dynamodb.Table(TABLE_NAME)

booking_repo = BookingRepository(table)
user_repo = UserRepository(table)
room_repo = RoomRepository(table)
scheduler_service = SchedulerService(AUTO_CHECKOUT_LAMBDA_ARN, SCHEDULER_ROLE_ARN)

booking_service = BookingService(
    booking_repo=booking_repo,
    user_repo=user_repo,
    room_repo=room_repo,
    schedule_service=scheduler_service,
)


def create_booking(event, context):
    if not event.get("body"):
        return send_custom_response(400, "Request body is required")

    try:
        request_body = BookingRequest.model_validate_json(event["body"])
    except ValidationError as e:
        formatted = "; ".join(f"{err['msg']}" for err in e.errors())
        return send_custom_response(400, formatted)

    except ValueError as e:
        return send_custom_response(400, str(e))
    try:
        user_id = event["requestContext"]["authorizer"]["user_id"]
    except KeyError:
        return send_custom_response(401, "Unauthorized")

    try:
        booking_service.add_booking(request_body, user_id)

        return send_custom_response(201, "Booking created successfully")

    except ValueError:
        allowed = ", ".join(c.value for c in Category)
        return send_custom_response(400, f"Invalid category. Allowed: {allowed}")

    except NotFoundException as err:
        return send_custom_response(err.status_code, str(err))

    except NoAvailableRooms as err:
        return send_custom_response(404, str(err))

    except Exception as err:
        print("Unhandled error:", err)
        return send_custom_response(500, "Internal server error")
