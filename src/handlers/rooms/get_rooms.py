import os
import json
from boto3 import resource
from src.common.repository.room_repo import RoomRepository
from src.common.services.room_service import RoomService
from src.common.models.rooms import Category
from src.common.utils.custom_exceptions import NoAvailableRooms
from src.common.utils.custom_response import send_custom_response

TABLE_NAME = os.environ.get("table_name")

dynamodb = resource("dynamodb", region_name="ap-south-1")
table = dynamodb.Table(TABLE_NAME)

room_repo = RoomRepository(table)
room_service = RoomService(room_repo=room_repo)


def get_rooms(event, context):
    try:
        params = event.get("queryStringParameters") or {}

        category_raw = params.get("category")
        checkin = params.get("checkin")
        checkout = params.get("checkout")

        if not category_raw or not checkin or not checkout:
            return send_custom_response(
                400,
                 "category, checkin and checkout are required"
            )

        try:
            category = Category(category_raw)
        except ValueError:
            return send_custom_response(
                400,
                f"Invalid category. Allowed: {[c.value for c in Category]}"
            )

        rooms = room_service.get_available_rooms(
            category=category,
            checkin=checkin,
            checkout=checkout
        )

        return send_custom_response(
            200,
            "successfully retrieved",
            {
                "category": category.value,
                "checkin": checkin,
                "checkout": checkout,
                "available_rooms": rooms,
                "count": len(rooms)
            }
        )

    except NoAvailableRooms as err:
        return send_custom_response(
            404,
            str(err)
        )
        
