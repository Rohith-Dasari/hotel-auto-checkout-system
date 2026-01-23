from botocore.exceptions import ClientError
import logging
from types_boto3_dynamodb.service_resource import Table
from types_boto3_dynamodb import DynamoDBClient
from typing import Optional, List
from boto3.dynamodb.conditions import Key
from src.common.models.rooms import Room, Category, RoomStatus


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
            room_id, Category(category=item["category"]), status=item["room_status"]
        )

    def get_rooms_ids_by_category(self, category: Category) -> List[str]:
        try:
            response = self.table.query(
                KeyConditionExpression=(
                    Key("pk").eq(f"CATEGORY#{category}")
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

    def get_category_price(self, category: Category) -> Optional[str]:
        try:
            response = self.table.get_item(
                Key={"pk": f"CATEGORY#{category}", "sk": "DETAILS"}
            )
        except ClientError as err:
            logger.error(f"Error retrieving category {category} details: {err}")
            raise
        item = response.get("Item")
        if not item:
            return None
        return item["price"]

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

    def get_available_rooms(self, checkin_data: str):
        pass
