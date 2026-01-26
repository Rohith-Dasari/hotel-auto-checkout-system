import json
import os
from boto3 import resource
from src.common.repository.room_repo import RoomRepository
from src.common.services.room_service import RoomService
from src.common.models.rooms import RoomStatus
from src.common.utils.custom_response import send_custom_response
from src.common.utils.custom_exceptions import NotFoundException
from botocore.exceptions import ClientError

TABLE_NAME = os.environ.get("TABLE_NAME")

dynamodb = resource("dynamodb", region_name="ap-south-1")
table = dynamodb.Table(TABLE_NAME)

room_repo = RoomRepository(table)
room_service = RoomService(room_repo=room_repo)


def update_room(event, context):
    try:
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

        room_id = body.get("room_id")
        status_raw = body.get("status")

        if not room_id or not status_raw:
            return send_custom_response(
                400,
                "room_id and status are required"
            )

        try:
            status = RoomStatus(status_raw)
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
