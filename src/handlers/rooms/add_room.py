import os
from datetime import datetime
from boto3 import resource
from common.repository.room_repo import RoomRepository
from common.services.room_service import RoomService
from common.models.rooms import Category
from common.models.users import UserRole
from common.utils.custom_response import send_custom_response
import json
from botocore.exceptions import ClientError

TABLE_NAME = os.environ.get("TABLE_NAME")

dynamodb = resource("dynamodb", region_name="ap-south-1")
table = dynamodb.Table(TABLE_NAME)

room_repo = RoomRepository(table)
room_service = RoomService(room_repo=room_repo)

def add_room(event,context):
    try:
        role_raw = event["requestContext"]["authorizer"]["role"]
    except (KeyError, TypeError):
        return send_custom_response(401, "Unauthorized")

    try:
        role = UserRole(role_raw.upper())
    except ValueError:
        return send_custom_response(403, "Forbidden")

    if role not in (UserRole.MANAGER, UserRole.ADMIN):
        return send_custom_response(403, "Only managers or admins can add rooms")

    if not event.get("body"):
        return send_custom_response(400, "Request body is required")

    try:
        body = json.loads(event["body"])
    except json.JSONDecodeError:
        return send_custom_response(400, "Invalid JSON body")

    room_id = body.get("room_id")
    category_raw = body.get("category")

    if not room_id or not category_raw:
        return send_custom_response(400, "room_id and category are required")

    try:
        category = Category(category_raw.upper())
    except ValueError:
        allowed = ", ".join(c.value for c in Category)
        return send_custom_response(400, f"Invalid category. Allowed: {allowed}")

    try:
        room_service.add_room(room_id=room_id, category=category)
    except ClientError as err:
        error_code = err.response["Error"].get("Code", "")
        if error_code == "ConditionalCheckFailedException":
            return send_custom_response(400, f"Room with id {room_id} already exists")
        return send_custom_response(500, f"Internal server error: {str(err)}")
    except Exception as e:
        return send_custom_response(500, f"Internal server error: {str(e)}")

    return send_custom_response(201, f"Room {room_id} added successfully")

