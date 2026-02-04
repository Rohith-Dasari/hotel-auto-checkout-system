import os
from datetime import datetime, timezone
from boto3 import resource

from common.repository.room_repo import RoomRepository
from common.services.room_service import RoomService
from common.models.rooms import Category
from common.models.users import UserRole
from common.utils.custom_exceptions import NoAvailableRooms, InvalidDates
from common.utils.custom_response import send_custom_response


TABLE_NAME = os.environ.get("TABLE_NAME")

dynamodb = resource("dynamodb", region_name="ap-south-1")
table = dynamodb.Table(TABLE_NAME)

room_repo = RoomRepository(table)
room_service = RoomService(room_repo=room_repo)


def _parse_iso_datetime(value: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError("Datetime must be a string")

    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        raise ValueError("Datetime must include timezone offset")
    return dt.astimezone(timezone.utc)


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
                400, "category, checkin and checkout are required"
            )

        try:
            checkin_dt = _parse_iso_datetime(checkin)
            checkout_dt = _parse_iso_datetime(checkout)
        except ValueError as e:
            return send_custom_response(400, str(e))

        try:
            category = Category(category_raw.upper())
        except ValueError:
            allowed = ", ".join(c.value for c in Category)
            return send_custom_response(400, f"Invalid category. Allowed: {allowed}")

        rooms = room_service.get_available_rooms(
            category=category, checkin=checkin_dt, checkout=checkout_dt
        )

        response_data = {
            "category": category.value,
            "checkin": checkin_dt.isoformat(),
            "checkout": checkout_dt.isoformat(),
            "count": len(rooms),
        }

        if role != UserRole.CUSTOMER:
            response_data["available_rooms"] = rooms

        return send_custom_response(200, "successfully retrieved", response_data)

    except NoAvailableRooms as err:
        return send_custom_response(404, str(err))

    except InvalidDates as err:
        return send_custom_response(400, str(err))
    except ValueError as err:
        return send_custom_response(400, str(err))

    except Exception as err:
        print("Unhandled error:", err)
        return send_custom_response(500, "Internal server error")
