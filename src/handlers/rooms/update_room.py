import json
import os
from boto3 import resource
from src.common.repository.room_repo import RoomRepository
from src.common.services.room_service import RoomService
from src.common.models.rooms import RoomStatus
from src.common.utils.custom_response import send_custom_response
from src.common.utils.custom_exceptions import NotFoundException
from botocore.exceptions import ClientError
from src.common.models.users import UserRole

TABLE_NAME = os.environ.get("TABLE_NAME")

dynamodb = resource("dynamodb", region_name="ap-south-1")
table = dynamodb.Table(TABLE_NAME)

room_repo = RoomRepository(table)
room_service = RoomService(room_repo=room_repo)


def update_room(event, context):
    try:
        try:
            role_raw = event["requestContext"]["authorizer"]["role"]
        except KeyError:
            return send_custom_response(401, "Unauthorized")

        try:
            role = UserRole(role_raw.upper())
        except ValueError:
            return send_custom_response(403, "Forbidden")

        if role != UserRole.MANAGER:
            return send_custom_response(403, "Only managers can update room status")

        path_params = event.get("pathParameters") or {}
        room_id = path_params.get("room_id")

        if not room_id:
            return send_custom_response(
                400,
                "room_id is required in the path"
            )

        if not event.get("body"):
            return send_custom_response(
                400,
                "Request body is required"
            )

        try:
            body = json.loads(event["body"])
        except json.JSONDecodeError:
            return send_custom_response(
                400,
                "Invalid JSON body"
            )

        status_raw = body.get("status")

        if not status_raw:
            return send_custom_response(
                400,
                "status is required"
            )

        try:
            status = RoomStatus(status_raw.upper())
        except ValueError:
            return send_custom_response(
                400,
                f"Invalid status. Allowed: {[s.value for s in RoomStatus]}"
            )

        room_service.update_room_status(
            room_id=room_id,
            status=status
        )

        return send_custom_response(
            200,
            "Room status updated successfully",
            {
                "room_id": room_id,
                "new_status": status.value
            }
        )

    except NotFoundException as err:
        return send_custom_response(404, str(err))
    except ClientError as err:
        print("AWS client error:", err)
        return send_custom_response(500, "Internal server error")
    except Exception as err:
        print("Unhandled error:", err)
        return send_custom_response(
            500,
            "Internal server error"
        )
