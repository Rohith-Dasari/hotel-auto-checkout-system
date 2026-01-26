import unittest
from unittest.mock import MagicMock
from datetime import datetime, timezone

from src.common.services.room_service import RoomService
from src.common.models.rooms import Category, RoomStatus
from src.common.utils.custom_exceptions import NoAvailableRooms, InvalidDates


class TestRoomService(unittest.TestCase):

    def setUp(self):
        self.repo = MagicMock()
        self.service = RoomService(self.repo)

    def test_update_room_status_calls_repo(self):
        self.service.update_room_status("room-1", RoomStatus.HOUSEKEEPING)

        self.repo.update_room_status.assert_called_once_with(
            "room-1",
            RoomStatus.HOUSEKEEPING
        )

    def test_ensure_datetime_with_datetime(self):
        dt = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)

        result = self.service._ensure_datetime(dt)

        self.assertEqual(result, dt)

    def test_ensure_datetime_with_iso_string(self):
        dt_str = "2026-01-01T12:00:00+05:30"

        result = self.service._ensure_datetime(dt_str)

        self.assertEqual(result.tzinfo, timezone.utc)

    def test_ensure_datetime_missing_timezone(self):
        dt_str = "2026-01-01T12:00:00"

        with self.assertRaises(InvalidDates):
            self.service._ensure_datetime(dt_str)

    def test_get_available_rooms_success(self):
        checkin = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
        checkout = datetime(2026, 1, 2, 12, 0, tzinfo=timezone.utc)

        fake_rooms = ["room1", "room2"]
        self.repo.get_available_rooms.return_value = fake_rooms

        result = self.service.get_available_rooms(
            Category.DELUXE,
            checkin,
            checkout
        )

        self.repo.get_available_rooms.assert_called_once()
        self.assertEqual(result, fake_rooms)

    def test_get_available_rooms_checkout_before_checkin(self):
        checkin = datetime(2026, 1, 2, 12, 0, tzinfo=timezone.utc)
        checkout = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)

        with self.assertRaises(InvalidDates):
            self.service.get_available_rooms(
                Category.DELUXE,
                checkin,
                checkout
            )

    def test_get_available_rooms_no_rooms(self):
        checkin = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
        checkout = datetime(2026, 1, 2, 12, 0, tzinfo=timezone.utc)

        self.repo.get_available_rooms.return_value = []

        with self.assertRaises(NoAvailableRooms):
            self.service.get_available_rooms(
                Category.DELUXE,
                checkin,
                checkout
            )
