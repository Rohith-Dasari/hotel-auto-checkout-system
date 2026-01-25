from botocore.exceptions import ClientError
import logging
from typing import Optional, List
from boto3.dynamodb.conditions import Key
from src.common.models.rooms import Room, Category, RoomStatus
from datetime import datetime

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
            room_id,category= Category(item["category"]), status=RoomStatus(item["room_status"])
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
            logger.error(f"Error retrieving {category} rooms: {err}")
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
            logger.error(f"Error retrieving category {category} details: {err}")
            raise
        item = response.get("Item")
        if not item:
            return None
        return float(item["price"])

    def update_room_status(self, room_id: str, status: RoomStatus):
        try:
            self.table.update_item(
                {"pk": f"ROOM#{room_id}", "sk": "DETAILS"},
                UpdateExpression="SET #attribute=:value",
                ExpressionAttributeNames={"#attribute": "room_status"},
                ExpressionAttributeValues={
                    ":value": status.value,
                },
                ConditionExpression="attribute_exists(pk)",
            )
        except ClientError as err:
            logger.error(f"Error updating room {room_id} status: {err}")
            raise

    def get_available_rooms(
        self,
        category: Category,
        checkin_date: str,
        checkout_date: str
    ) -> List[str]:

        room_ids = self.get_rooms_ids_by_category(category)
        if not room_ids:
            return []

        requested_checkin = datetime.fromisoformat(checkin_date)
        requested_checkout = datetime.fromisoformat(checkout_date)

        available_rooms = []

        sk_upper_bound = f"CHECKIN#{checkout_date}"

        for room_id in room_ids:
            try:
                response = self.table.query(
                    KeyConditionExpression=
                        Key("pk").eq(f"ROOM#{room_id}") &
                        Key("sk").lte(sk_upper_bound),
                    ScanIndexForward=False,
                    Limit=1
                )

            except ClientError as err:
                logger.error(f"Error querying bookings for room {room_id}: {err}")
                continue

            bookings = response.get("Items", [])
            is_available = True

            for booking in bookings:
                existing_checkout = datetime.fromisoformat(
                    booking["checkout_date"]
                )

                if requested_checkin < existing_checkout:
                    is_available = False
                    break

            if is_available:
                available_rooms.append(room_id)

        return available_rooms
