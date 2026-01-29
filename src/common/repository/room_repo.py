from botocore.exceptions import ClientError
import logging
from typing import Optional, List
from boto3.dynamodb.conditions import Key
from src.common.models.rooms import Room, Category, RoomStatus
from datetime import datetime, timezone, timedelta
from src.common.utils.custom_exceptions import NotFoundException
from src.common.utils.constants import MAX_STAY
from src.common.utils.datetime_normaliser import from_iso_string

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

    def add_room(self, room: Room):
        room_item = {
            "pk": f"ROOM#{room.room_id}",
            "sk": f"DETAILS",
            "category": room.category.value,
            "room_status": room.status.value,
        }
        category_item = {
            "pk": f"CATEGORY#{room.category.value}",
            "sk": f"ROOM#{room.room_id}",
        }
        try:
            self.client.transact_write_items(
                TransactItems=[
                    {
                        "Put": {
                            "TableName": self.table.name,
                            "Item": room_item,
                            "ConditionExpression": "attribute_not_exists(pk)",
                        }
                    },
                    {
                        "Put": {
                            "TableName": self.table.name,
                            "Item": category_item,
                        }
                    },
                ]
            )
        except ClientError as err:
            logger.error(f"Error creating booking {room.room_id}: {err}")
            raise

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

    def get_available_rooms(
        self, category: Category, checkin: datetime, checkout: datetime
    ) -> list[str]:
        requested_checkin = self._to_utc(checkin)
        requested_checkout = self._to_utc(checkout)
        max_stay_delta = timedelta(days=MAX_STAY)
        lower_iso = self._to_iso(requested_checkin - max_stay_delta)
        upper_iso = self._to_iso(requested_checkout)
        rooms = self.get_rooms_ids_by_category(category)
        all_room_ids: set[str] = set(rooms)
        if not all_room_ids:
            return []
        blocked_rooms: set[str] = set()
        try:
            resp = self.table.query(
                KeyConditionExpression=(
                    Key("pk").eq(f"CATEGORY#{category.value}")
                    & Key("sk").between(
                        f"CHECKIN#{lower_iso}",
                        f"CHECKIN#{upper_iso}",
                    )
                )
            )
            for item in resp.get("Items", []):
                existing_checkout = from_iso_string(item["checkout"])
                existing_checkin = from_iso_string(
                    item["sk"].split("CHECKIN#", 1)[1].split("#ROOM#", 1)[0]
                )
                if (
                    requested_checkin < existing_checkout
                    and existing_checkin < requested_checkout
                ):
                    blocked_rooms.add(item["room_id"])
            while "LastEvaluatedKey" in resp:
                resp = self.table.query(
                    KeyConditionExpression=(
                        Key("pk").eq(f"CATEGORY#{category.value}")
                        & Key("sk").between(
                            f"CHECKIN#{lower_iso}",
                            f"CHECKIN#{upper_iso}",
                        )
                    ),
                    ExclusiveStartKey=resp["LastEvaluatedKey"],
                )
                for item in resp.get("Items", []):
                    existing_checkout = from_iso_string(item["checkout"])
                    existing_checkin = from_iso_string(
                        item["sk"].split("CHECKIN#", 1)[1].split("#ROOM#", 1)[0]
                    )
                    if (
                        requested_checkin < existing_checkout
                        and existing_checkin < requested_checkout
                    ):
                        blocked_rooms.add(item["room_id"])
        except ClientError as err:
            logger.error(
                f"Error retrieving bookings for {category.value} between {lower_iso} and {upper_iso}: {err}"
            )
            raise
        return list(all_room_ids - blocked_rooms)
