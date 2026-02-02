from botocore.exceptions import ClientError
import logging
from typing import Optional, List
from boto3.dynamodb.conditions import Key
from common.models.bookings import Booking, BookingStatus
from common.models.rooms import Category, RoomStatus
from common.utils.datetime_normaliser import from_iso_string
from decimal import Decimal
from datetime import datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from types_boto3_dynamodb.service_resource import Table
    from types_boto3_dynamodb import DynamoDBClient
else:
    Table = object
    DynamoDBClient = object


logger = logging.getLogger(__name__)


class BookingRepository:
    def __init__(self, table: Table, client: DynamoDBClient = None):
        self.table = table
        self.client = client if client else table.meta.client

    @staticmethod
    def _iso(dt: datetime | str) -> str:
        if isinstance(dt, str):
            parsed = datetime.fromisoformat(dt)
        else:
            parsed = dt

        if parsed.tzinfo is None:
            raise ValueError("Datetime must be timezone-aware")

        return parsed.astimezone(timezone.utc).isoformat()

    def add_booking(self, booking: Booking):
        checkin_iso = self._iso(booking.checkin)
        checkout_iso = self._iso(booking.checkout)

        booking_item = {
            "pk": f"BOOKING#{booking.booking_id}",
            "sk": "DETAILS",
            "user_id": booking.user_id,
            "check_in": checkin_iso,
            "check_out": checkout_iso,
            "category": booking.category.value,
            "booking_status": booking.status.value,
            "room_id": booking.room_id,
            "price_per_night": Decimal(str(booking.price_per_night)),
            "booked_at": self._iso(booking.booked_at),
            "user_email": booking.user_email,
        }

        user_booking = {
            "pk": f"USER#{booking.user_id}",
            "sk": f"BOOKING#{booking.booking_id}",
            "check_in": checkin_iso,
            "check_out": checkout_iso,
            "category": booking.category.value,
            "booking_status": booking.status.value,
            "room_id": booking.room_id,
            "price_per_night": Decimal(str(booking.price_per_night)),
            "booked_at": self._iso(booking.booked_at),
            "user_email": booking.user_email,
        }

        room_booking = {
            "pk": f"ROOM#{booking.room_id}",
            "sk": f"CHECKIN#{checkin_iso}",
            "booking_id": booking.booking_id,
            "checkout_date": checkout_iso,
            "checkin_date": checkin_iso,
        }
        availability_item = {
            "pk": f"CATEGORY#{booking.category.value}",
            "sk": f"CHECKIN#{checkin_iso}#ROOM#{booking.room_id}",
            "room_id": booking.room_id,
            "checkout": checkout_iso,
            "booking_id": booking.booking_id,
            "ttl_attribute": int(booking.checkout.timestamp()),
        }

        try:
            self.client.transact_write_items(
                TransactItems=[
                    {
                        "Put": {
                            "TableName": self.table.name,
                            "Item": booking_item,
                            "ConditionExpression": "attribute_not_exists(pk)",
                        }
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
                    {
                        "Put": {
                            "TableName": self.table.name,
                            "Item": availability_item,
                            "ConditionExpression": "attribute_not_exists(sk)",
                        }
                    },
                ]
            )

        except ClientError as err:
            logger.error(f"Error creating booking {booking.booking_id}: {err}")
            raise

    def get_user_bookings(self, user_id: str) -> List[Booking]:
        try:
            response = self.table.query(
                KeyConditionExpression=Key("pk").eq(f"USER#{user_id}")
                & Key("sk").begins_with("BOOKING#")
            )
        except ClientError as err:
            logger.error(f"Error retrieving user {user_id} bookings: {err}")
            raise

        items = response.get("Items", [])
        if not items:
            return []

        bookings = []
        for item in items:
            checkin_dt = from_iso_string(item["check_in"])
            checkout_dt = from_iso_string(item["check_out"])
            booked_at_dt = datetime.fromisoformat(item["booked_at"])

            booking = Booking(
                booking_id=item["sk"].removeprefix("BOOKING#"),
                user_id=user_id,
                room_id=item["room_id"],
                category=Category(item["category"]),
                status=BookingStatus(item["booking_status"]),
                checkin=checkin_dt,
                checkout=checkout_dt,
                price_per_night=float(item["price_per_night"]),
                booked_at=booked_at_dt,
                user_email=item.get("user_email"),
            )
            bookings.append(booking)

        return bookings

    def get_booking_by_id(self, booking_id: str) -> Optional[Booking]:
        try:
            response = self.table.get_item(
                Key={"pk": f"BOOKING#{booking_id}", "sk": "DETAILS"}
            )
        except ClientError as err:
            logger.error(f"Error retrieving booking {booking_id}: {err}")
            raise

        item = response.get("Item")
        if not item:
            return None

        checkin_dt = from_iso_string(item["check_in"])
        checkout_dt = from_iso_string(item["check_out"])
        booked_at_dt = datetime.fromisoformat(item["booked_at"])

        return Booking(
            booking_id=booking_id,
            user_id=item["user_id"],
            room_id=item["room_id"],
            category=Category(item["category"]),
            status=BookingStatus(item["booking_status"]),
            checkin=checkin_dt,
            checkout=checkout_dt,
            price_per_night=float(item["price_per_night"]),
            booked_at=booked_at_dt,
            user_email=item.get("user_email"),
        )

    def update_booking_status(
        self, booking_id: str, user_id: str, room_id: str, status: BookingStatus
    ):
        room_status = (
            RoomStatus.HOUSEKEEPING
            if status == BookingStatus.CHECKED_OUT
            else RoomStatus.OCCUPIED
        )

        try:
            self.client.transact_write_items(
                TransactItems=[
                    {
                        "Update": {
                            "Key": {"pk": f"ROOM#{room_id}", "sk": "DETAILS"},
                            "TableName": self.table.name,
                            "UpdateExpression": "SET #room_status = :new_value",
                            "ExpressionAttributeNames": {
                                "#room_status": "room_status",
                            },
                            "ExpressionAttributeValues": {
                                ":new_value": room_status.value,
                            },
                            "ConditionExpression": "attribute_exists(pk)",
                        }
                    },
                    {
                        "Update": {
                            "Key": {
                                "pk": f"BOOKING#{booking_id}",
                                "sk": "DETAILS",
                            },
                            "TableName": self.table.name,
                            "UpdateExpression": "SET #booking_status = :new_value",
                            "ExpressionAttributeNames": {
                                "#booking_status": "booking_status",
                            },
                            "ExpressionAttributeValues": {
                                ":new_value": status.value,
                            },
                            "ConditionExpression": "attribute_exists(pk)",
                        }
                    },
                    {
                        "Update": {
                            "Key": {
                                "pk": f"USER#{user_id}",
                                "sk": f"BOOKING#{booking_id}",
                            },
                            "TableName": self.table.name,
                            "UpdateExpression": "SET #booking_status = :new_value",
                            "ExpressionAttributeNames": {
                                "#booking_status": "booking_status",
                            },
                            "ExpressionAttributeValues": {
                                ":new_value": status.value,
                            },
                            "ConditionExpression": "attribute_exists(pk)",
                        }
                    },
                ]
            )
        except ClientError as err:
            logger.error(f"Error updating booking {booking_id} status: {err}")
            raise
