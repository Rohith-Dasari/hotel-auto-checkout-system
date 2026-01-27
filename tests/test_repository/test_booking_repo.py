import unittest
from unittest.mock import MagicMock
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from botocore.exceptions import ClientError

from src.common.repository.booking_repo import BookingRepository
from src.common.models.bookings import Booking, BookingStatus
from src.common.models.rooms import Category, RoomStatus


class TestBookingRepository(unittest.TestCase):

    def setUp(self):
        self.table = MagicMock()
        self.client = MagicMock()

        self.table.meta.client = self.client
        self.repo = BookingRepository(self.table, self.client)

        now = datetime.now(timezone.utc)

        self.booking = Booking(
            booking_id="b1",
            user_id="u1",
            room_id="r1",
            category=Category.DELUXE,
            status=BookingStatus.UPCOMING,
            checkin=now + timedelta(days=1),
            checkout=now + timedelta(days=2),
            price_per_night=1500.0,
            booked_at=now,
            user_email="test@example.com"
        )

    def test_iso_success(self):
        iso = self.repo._iso(self.booking.checkin)

        self.assertTrue(iso.endswith("Z") or "+" in iso)

    def test_iso_naive_fails(self):
        naive = datetime.now()

        with self.assertRaises(ValueError):
            self.repo._iso(naive)

    def test_iso_string_input(self):
        dt = self.booking.checkin.isoformat()

        iso = self.repo._iso(dt)

        self.assertTrue("T" in iso)


    def test_add_booking_success(self):
        self.client.transact_write_items.return_value = {}

        self.repo.add_booking(self.booking)

        self.client.transact_write_items.assert_called_once()
        _, kwargs = self.client.transact_write_items.call_args

        items = kwargs["TransactItems"]
        self.assertEqual(len(items), 4)

        booking_put = items[0]["Put"]["Item"]
        user_put = items[1]["Put"]["Item"]
        room_put = items[2]["Put"]["Item"]
        avail_put = items[3]["Put"]["Item"]

        self.assertEqual(booking_put["pk"], "BOOKING#b1")
        self.assertEqual(booking_put["sk"], "DETAILS")
        self.assertEqual(booking_put["user_id"], "u1")
        self.assertEqual(booking_put["room_id"], "r1")
        self.assertEqual(booking_put["category"], "DELUXE")
        self.assertEqual(
            booking_put["price_per_night"],
            Decimal("1500.0")
        )

        self.assertEqual(user_put["pk"], "USER#u1")
        self.assertEqual(user_put["sk"], "BOOKING#b1")

        self.assertEqual(room_put["pk"], "ROOM#r1")
        self.assertTrue(room_put["sk"].startswith("CHECKIN#"))

        self.assertEqual(avail_put["pk"], f"CATEGORY#{self.booking.category.value}")
        self.assertTrue(avail_put["sk"].startswith(f"CHECKIN#"))
        self.assertEqual(avail_put["room_id"], self.booking.room_id)
        self.assertEqual(avail_put["booking_id"], self.booking.booking_id)

    def test_add_booking_client_error(self):
        self.client.transact_write_items.side_effect = ClientError(
            error_response={"Error": {"Message": "Write failed"}},
            operation_name="TransactWriteItems"
        )

        with self.assertRaises(ClientError):
            self.repo.add_booking(self.booking)

    def test_get_user_bookings_success(self):
        now = datetime.now(timezone.utc)

        self.table.query.return_value = {
            "Items": [
                {
                    "pk": "USER#u1",
                    "sk": "BOOKING#b1",
                    "room_id": "r1",
                    "category": "DELUXE",
                    "booking_status": "UPCOMING",
                    "check_in": now.isoformat(),
                    "check_out": (now + timedelta(days=1)).isoformat(),
                    "price_per_night": Decimal("1500.0"),
                    "booked_at": now.isoformat(),
                    "user_email": "test@example.com"
                }
            ]
        }

        bookings = self.repo.get_user_bookings("u1")

        self.table.query.assert_called_once()
        self.assertEqual(len(bookings), 1)

        booking = bookings[0]
        self.assertEqual(booking.booking_id, "b1")
        self.assertEqual(booking.room_id, "r1")
        self.assertEqual(booking.category, Category.DELUXE)
        self.assertEqual(booking.status, BookingStatus.UPCOMING)
        self.assertEqual(booking.price_per_night, 1500.0)

    def test_get_user_bookings_empty(self):
        self.table.query.return_value = {"Items": []}

        bookings = self.repo.get_user_bookings("u1")

        self.assertEqual(bookings, [])

    def test_get_user_bookings_client_error(self):
        self.table.query.side_effect = ClientError(
            error_response={"Error": {"Message": "Query failed"}},
            operation_name="Query"
        )

        with self.assertRaises(ClientError):
            self.repo.get_user_bookings("u1")

    def test_get_booking_by_id_success(self):
        now = datetime.now(timezone.utc)

        self.table.get_item.return_value = {
            "Item": {
                "pk": "BOOKING#b1",
                "sk": "DETAILS",
                "user_id": "u1",
                "room_id": "r1",
                "category": "DELUXE",
                "booking_status": "UPCOMING",
                "check_in": now.isoformat(),
                "check_out": (now + timedelta(days=1)).isoformat(),
                "price_per_night": Decimal("1500.0"),
                "booked_at": now.isoformat(),
                "user_email": "test@example.com"
            }
        }

        booking = self.repo.get_booking_by_id("b1")

        self.table.get_item.assert_called_once()
        self.assertEqual(booking.booking_id, "b1")
        self.assertEqual(booking.user_id, "u1")
        self.assertEqual(booking.room_id, "r1")
        self.assertEqual(booking.category, Category.DELUXE)
        self.assertEqual(booking.status, BookingStatus.UPCOMING)

    def test_get_booking_by_id_not_found(self):
        self.table.get_item.return_value = {}

        result = self.repo.get_booking_by_id("missing")

        self.assertIsNone(result)

    def test_get_booking_by_id_client_error(self):
        self.table.get_item.side_effect = ClientError(
            error_response={"Error": {"Message": "Get failed"}},
            operation_name="GetItem"
        )

        with self.assertRaises(ClientError):
            self.repo.get_booking_by_id("b1")

    # -------------------------
    # UPDATE BOOKING STATUS
    # -------------------------
    def test_update_booking_status_checked_out_sets_housekeeping(self):
        self.client.transact_write_items.return_value = {}

        self.repo.update_booking_status(
            booking_id="b1",
            user_id="u1",
            room_id="r1",
            status=BookingStatus.CHECKED_OUT
        )

        self.client.transact_write_items.assert_called_once()
        _, kwargs = self.client.transact_write_items.call_args

        updates = kwargs["TransactItems"]

        room_update = updates[0]["Update"]
        self.assertEqual(
            room_update["ExpressionAttributeValues"][":new_value"],
            RoomStatus.HOUSEKEEPING.value
        )

    def test_update_booking_status_other_sets_occupied(self):
        self.client.transact_write_items.return_value = {}

        self.repo.update_booking_status(
            booking_id="b1",
            user_id="u1",
            room_id="r1",
            status=BookingStatus.CHECKED_IN
        )

        _, kwargs = self.client.transact_write_items.call_args
        updates = kwargs["TransactItems"]

        room_update = updates[0]["Update"]
        self.assertEqual(
            room_update["ExpressionAttributeValues"][":new_value"],
            RoomStatus.OCCUPIED.value
        )

    def test_update_booking_status_client_error(self):
        self.client.transact_write_items.side_effect = ClientError(
            error_response={"Error": {"Message": "Update failed"}},
            operation_name="TransactWriteItems"
        )

        with self.assertRaises(ClientError):
            self.repo.update_booking_status(
                booking_id="b1",
                user_id="u1",
                room_id="r1",
                status=BookingStatus.CHECKED_OUT
            )


if __name__ == "__main__":
    unittest.main()
