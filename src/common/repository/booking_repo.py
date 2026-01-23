from botocore.exceptions import ClientError
import logging
from types_boto3_dynamodb.service_resource import Table
from types_boto3_dynamodb import DynamoDBClient
from typing import Optional, List
from boto3.dynamodb.conditions import Key
from src.common.models.bookings import Booking, BookingStatus
from src.common.models.rooms import Category, RoomStatus


logger = logging.getLogger(__name__)


class BookingRepository:
    def __init__(self, table: Table, client: DynamoDBClient = None):
        self.table = table
        self.client = client if client else table.meta.client

    def add_booking(self, booking: Booking):
        booking_item = {
            "pk": f"BOOKING#{booking.booking_id}",
            "sk": "DETAILS",
            "user_id": booking.user_id,
            "check_in": booking.checkin,
            "check_out": booking.checkout,
            "category": booking.category.value,
            "booking_status": booking.status.value,
            "room_id": booking.room_id,
            "price_per_night": booking.price_per_night,
            "booked_at": booking.booked_at,
            "scheduler_id": booking.scheduler_id,
        }
        user_booking = {
            "pk": f"USER#{booking.user_id}",
            "sk": f"BOOKING#{booking.booking_id}",
        }
        room_booking = {
            "pk": f"ROOM#{booking.room_id}",
            "sk": f"CHECKIN#{booking.checkin}",
            "booking_id": booking.booking_id,
            "checkout_date": booking.checkout,
            "checkin_date": booking.checkin,
        }
        try:
            self.client.transact_write_items(
                TransactItems=[
                    {
                        "Put": {
                            "TableName": self.table.name,
                            "Item": booking_item,
                        },
                    },
                    {
                        "Put": {
                            "TableName": self.table.name,
                            "Item": user_booking,
                        }
                    },
                    {
                        "Put": {
                            "TableName": self.table.name,
                            "Item": room_booking,
                        }
                    },
                ]
            )
        except ClientError as err:
            logger.error(f"error in updating booking {booking.booking_id}: {err}")
            raise

    def get_user_bookings(self, user_id):
        pass

    def get_booking_by_id(self, booking_id) -> Optional[Booking]:
        try:
            response = self.table.get_item(
                Key={"pk": f"BOOKING#{booking_id}", "sk": "DETAILS"}
            )
        except ClientError as err:
            logger.error(f"Error retrieving booking bby id {booking_id}:{err}")
            raise

        item = response.get("Item")
        if not item:
            return None
        if not item:
            return None
        return Booking(
            booking_id=booking_id,
            user_id=item["booking_id"],
            room_id=item["room_id"],
            category=Category(item["category"]),
            # to do: complete it
        )

    def update_booking_status(self, booking_id: str, room_id, status: BookingStatus):
        if status == BookingStatus.CHECKED_OUT:
            try:
                self.client.transact_write_items(
                    TransactItems=[
                        {
                            "Update": {
                                "Key": {"pk": f"ROOM#{room_id}", "sk": f"DETAILS"},
                                "TableName": self.table.name,
                                "UpdateExpression": "SET #room_status=:new_value",
                                "ExpressionAttributeNames": {
                                    "#room_status": "room_status",
                                },
                                "ExpressionAttributeValues": {
                                    ":new_value": RoomStatus.HOUSEKEEPING,
                                },
                                "ConditionExpression": "attribute_exists(pk)",
                            },
                        },
                        {
                            "Update": {
                                "Key": {
                                    "pk": f"BOOKING#{booking_id}",
                                    "sk": f"DETAILS",
                                },
                                "TableName": self.table.name,
                                "UpdateExpression": "SET #booking_status=:new_value",
                                "ExpressionAttributeNames": {
                                    "#booking_status": "booking_status",
                                },
                                "ExpressionAttributeValues": {
                                    ":new_value": BookingStatus.CHECKED_OUT,
                                },
                                "ConditionExpression": "attribute_exists(pk)",
                            },
                        },
                    ]
                )
            except ClientError as err:
                logger.error(f"Error updating room {booking_id} status: {err}")
                raise

        else:
            try:
                self.table.update_item(
                    {"pk": f"BOOKING#{booking_id}", "sk": "DETAILS"},
                    UpdateExpression="SET #attribute=:value",
                    ExpressionAttributeNames={"#attribute": "booking_status"},
                    ExpressionAttributeValues={
                        ":value": status.value,
                    },
                    ConditionExpression="attribute_exists(pk)",
                )
            except ClientError as err:
                logger.error(f"Error updating booking {booking_id} status: {err}")
                raise
