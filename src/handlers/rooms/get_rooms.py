import os
from datetime import datetime
from boto3 import resource

from src.common.repository.room_repo import RoomRepository
from src.common.services.room_service import RoomService
from src.common.models.rooms import Category
from src.common.models.users import UserRole
from src.common.utils.custom_exceptions import NoAvailableRooms, InvalidDates
from src.common.utils.custom_response import send_custom_response


TABLE_NAME = os.environ.get("TABLE_NAME")

dynamodb = resource("dynamodb", region_name="ap-south-1")
table = dynamodb.Table(TABLE_NAME)

room_repo = RoomRepository(table)
room_service = RoomService(room_repo=room_repo)


def _validate_iso_date(date_str: str) -> bool:
    try:
        datetime.fromisoformat(date_str)
        return True
    except (ValueError, TypeError):
        return False


def get_rooms(event, context):
    try:
        params = event.get("queryStringParameters") or {}

        authorizer = event.get("requestContext", {}).get("authorizer", {})
        role_raw = authorizer.get("role")
        role = None
        if role_raw:
            try:
                role = UserRole(role_raw.upper())
            except ValueError:
                role = None

        category_raw = params.get("category")
        checkin = params.get("checkin")
        checkout = params.get("checkout")

        if not category_raw or not checkin or not checkout:
            return send_custom_response(
                400,
                "category, checkin and checkout are required"
            )

        if not _validate_iso_date(checkin) or not _validate_iso_date(checkout):
            return send_custom_response(
                400,
                "checkin and checkout must be in ISO format: YYYY-MM-DD"
            )

        try:
            category = Category(category_raw.upper())
        except ValueError:
            allowed = ", ".join(c.value for c in Category)
            return send_custom_response(
                400,
                f"Invalid category. Allowed: {allowed}"
            )

        rooms = room_service.get_available_rooms(
            category=category,
            checkin=checkin,
            checkout=checkout
        )

        response_data = {
            "category": category.value,
            "checkin": checkin,
            "checkout": checkout,
            "count": len(rooms)
        }

        if role != UserRole.CUSTOMER:
            response_data["available_rooms"] = rooms

        return send_custom_response(
            200,
            "successfully retrieved",
            response_data
        )

    except NoAvailableRooms as err:
        return send_custom_response(
            404,
            str(err)
        )

    except InvalidDates as err:
        return send_custom_response(
            400,
            str(err)
        )

    except Exception as err:
        print("Unhandled error:", err)
        return send_custom_response(
            500,
            "Internal server error"
        )
