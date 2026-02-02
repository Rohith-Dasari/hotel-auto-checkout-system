import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone, timedelta

from common.services.booking_service import BookingService
from common.models.bookings import BookingStatus
from common.models.rooms import Category
from common.schemas.bookings import BookingRequest
from common.utils.custom_exceptions import NotFoundException, NoAvailableRooms


class TestBookingService(unittest.TestCase):

    def setUp(self):
        self.booking_repo = MagicMock()
        self.user_repo = MagicMock()
        self.room_repo = MagicMock()
        self.scheduler = MagicMock()

        self.service = BookingService(
            booking_repo=self.booking_repo,
            user_repo=self.user_repo,
            room_repo=self.room_repo,
            schedule_service=self.scheduler
        )

        self.user = MagicMock()
        self.user.email = "test@example.com"

        now = datetime.now(timezone.utc)

        self.req = BookingRequest(
            category="deluxe",
            checkin=now + timedelta(days=1),
            checkout=now + timedelta(days=2),
        )

    @patch("common.services.booking_service.random.choice", return_value="room42")
    def test_add_booking_success(self, _):
        self.user_repo.get_by_id.return_value = self.user
        self.room_repo.get_category_price.return_value = "1500"
        self.room_repo.get_available_rooms.return_value = ["room42"]

        self.service.add_booking(self.req, "user-1")

        self.booking_repo.add_booking.assert_called_once()
        self.scheduler.schedule_checkout.assert_called_once_with(
            booking_id=unittest.mock.ANY,
            user_id="user-1",
            room_id="room42",
            checkout_time=self.req.checkout,
        )

    def test_add_booking_user_not_found(self):
        self.user_repo.get_by_id.return_value = None

        with self.assertRaises(NotFoundException):
            self.service.add_booking(self.req, "missing-user")

    def test_add_booking_category_price_not_found(self):
        self.user_repo.get_by_id.return_value = self.user
        self.room_repo.get_category_price.return_value = None

        with self.assertRaises(NotFoundException):
            self.service.add_booking(self.req, "user-1")

    def test_add_booking_no_available_rooms(self):
        self.user_repo.get_by_id.return_value = self.user
        self.room_repo.get_category_price.return_value = "1500"
        self.room_repo.get_available_rooms.return_value = []

        with self.assertRaises(NoAvailableRooms):
            self.service.add_booking(self.req, "user-1")

    def test_add_booking_without_scheduler(self):
        service = BookingService(
            booking_repo=self.booking_repo,
            user_repo=self.user_repo,
            room_repo=self.room_repo,
            schedule_service=None
        )

        self.user_repo.get_by_id.return_value = self.user
        self.room_repo.get_category_price.return_value = "1500"
        self.room_repo.get_available_rooms.return_value = ["room1"]

        service.add_booking(self.req, "user-1")

        self.booking_repo.add_booking.assert_called_once()
        self.scheduler.schedule_checkout.assert_not_called()

    def test_update_booking_calls_repo(self):
        self.service.update_booking(
            booking_id="b1",
            user_id="u1",
            room_id="r1"
        )

        self.booking_repo.update_booking_status.assert_called_once_with(
            booking_id="b1",
            user_id="u1",
            room_id="r1",
            status=BookingStatus.CHECKED_OUT
        )

    def test_get_user_bookings_success(self):
        self.user_repo.get_by_id.return_value = self.user
        self.booking_repo.get_user_bookings.return_value = ["b1", "b2"]

        result = self.service.get_user_bookings("user-1")

        self.booking_repo.get_user_bookings.assert_called_once_with("user-1")
        self.assertEqual(result, ["b1", "b2"])

    def test_get_user_bookings_user_not_found(self):
        self.user_repo.get_by_id.return_value = None

        with self.assertRaises(NotFoundException):
            self.service.get_user_bookings("missing-user")

    @patch("common.services.booking_service.random.choice", return_value="room99")
    def test_allocate_room_picks_room(self, _):
        self.room_repo.get_available_rooms.return_value = ["room1", "room99"]

        room = self.service._allocate_room(Category.DELUXE, self.req)

        self.assertEqual(room, "room99")
        self.room_repo.get_available_rooms.assert_called_once()

    def test_allocate_room_no_rooms(self):
        self.room_repo.get_available_rooms.return_value = []

        with self.assertRaises(NoAvailableRooms):
            self.service._allocate_room(Category.DELUXE, self.req)


if __name__ == "__main__":
    unittest.main()
