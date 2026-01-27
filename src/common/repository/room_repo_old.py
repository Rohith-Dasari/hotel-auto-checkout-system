from botocore.exceptions import ClientError
import logging
from typing import Optional, List
from boto3.dynamodb.conditions import Key
from src.common.models.rooms import Room, Category, RoomStatus
from datetime import datetime, timezone
from src.common.utils.custom_exceptions import NotFoundException


from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from types_boto3_dynamodb.service_resource import Table
    from types_boto3_dynamodb import DynamoDBClient
else:
    Table = object
    DynamoDBClient = object


logger = logging.getLogger(__name__)


class RoomRepository:
    def __init__(self, table: Table, client: DynamoDBClient = None):
        self.table = table
        self.client = client if client else table.meta.client

    def get_room_by_id(self, room_id: str) -> Optional[Room]:
        try:
            response = self.table.get_item(
                Key={"pk": f"ROOM#{room_id}", "sk": "DETAILS"}
            )
        except ClientError as err:
            logger.error(f"Error retrieving room by id {room_id}: {err}")
            raise

        item = response.get("Item")
        if not item:
            return None
        return Room(
            room_id,
            category=Category(item["category"]),
            status=RoomStatus(item["room_status"]),
        )

    def get_rooms_ids_by_category(self, category: Category) -> List[str]:
        try:
            response = self.table.query(
                KeyConditionExpression=(
                    Key("pk").eq(f"CATEGORY#{category.value}")
                    & Key("sk").begins_with("ROOM#")
                )
            )
        except ClientError as err:
            logger.error(f"Error retrieving {category.value} rooms: {err}")
            raise
        items = response.get("Items", [])
        if not items:
            return []
        room_ids = []
        for item in items:
            id = item["sk"].split("ROOM#", 1)[1]
            room_ids.append(id)
        return room_ids

    def get_category_price(self, category: Category) -> Optional[float]:
        try:
            response = self.table.get_item(
                Key={"pk": f"CATEGORY#{category.value}", "sk": "DETAILS"}
            )
        except ClientError as err:
            logger.error(f"Error retrieving category {category.value} details: {err}")
            raise
        item = response.get("Item")
        if not item:
            return None
        return float(item["price"])

    def update_room_status(self, room_id: str, status: RoomStatus):
        try:
            self.table.update_item(
                Key={"pk": f"ROOM#{room_id}", "sk": "DETAILS"},
                UpdateExpression="SET #attribute=:value",
                ExpressionAttributeNames={"#attribute": "room_status"},
                ExpressionAttributeValues={
                    ":value": status.value,
                },
                ConditionExpression="attribute_exists(pk)",
            )
        except ClientError as err:
            if (
                err.response.get("Error", {}).get("Code")
                == "ConditionalCheckFailedException"
            ):
                raise NotFoundException("room", room_id, 404)
            logger.error(f"Error updating room {room_id} status: {err}")
            raise

    def _to_utc(self, dt: datetime) -> datetime:
        if dt.tzinfo is None:
            raise ValueError("Datetime must be timezone-aware")
        return dt.astimezone(timezone.utc)

    def _to_iso(self, dt: datetime) -> str:
        return self._to_utc(dt).isoformat()

    def _from_iso(self, value: str) -> datetime:
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            raise ValueError("Stored datetime must be timezone-aware")
        return dt.astimezone(timezone.utc)

    def get_available_rooms(
        self, category: Category, checkin: datetime, checkout: datetime
    ) -> list[str]:

        requested_checkin = self._to_utc(checkin)
        requested_checkout = self._to_utc(checkout)

        room_ids = self.get_rooms_ids_by_category(category)
        if not room_ids:
            return []

        available_rooms = []

        sk_upper_bound = f"CHECKIN#{self._to_iso(requested_checkout)}"

        for room_id in room_ids:
            try:
                response = self.table.query(
                    KeyConditionExpression=Key("pk").eq(f"ROOM#{room_id}")
                    & Key("sk").lte(sk_upper_bound),
                    ScanIndexForward=True,
                )
            except ClientError as err:
                logger.error(f"Error querying bookings for room {room_id}: {err}")
                continue

            bookings = response.get("Items", [])
            is_available = True

            for booking in bookings:
                existing_checkin = self._from_iso(booking["checkin_date"])
                existing_checkout = self._from_iso(booking["checkout_date"])
                if (
                    requested_checkin < existing_checkout
                    and existing_checkin < requested_checkout
                ):
                    is_available = False
                    break

            if is_available:
                available_rooms.append(room_id)

        return available_rooms
