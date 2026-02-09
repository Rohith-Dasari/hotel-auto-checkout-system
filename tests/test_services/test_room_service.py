import unittest
from unittest.mock import MagicMock
from datetime import datetime, timezone, timedelta

from common.services.room_service import RoomService
from common.models.rooms import Category, RoomStatus
from common.utils.custom_exceptions import NoAvailableRooms, InvalidDates


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

    def test_get_available_rooms_success(self):
        checkin = datetime.now(timezone.utc) + timedelta(days=1)
        checkout = checkin + timedelta(days=1)

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
        checkin = datetime.now(timezone.utc) + timedelta(days=2)
        checkout = checkin - timedelta(days=1)

        with self.assertRaises(InvalidDates):
            self.service.get_available_rooms(
                Category.DELUXE,
                checkin,
                checkout
            )

    def test_get_available_rooms_no_rooms(self):
        checkin = datetime.now(timezone.utc) + timedelta(days=1)
        checkout = checkin + timedelta(days=1)

        self.repo.get_available_rooms.return_value = []

        with self.assertRaises(NoAvailableRooms):
            self.service.get_available_rooms(
                Category.DELUXE,
                checkin,
                checkout
            )
    def test_add_room_calls_repo(self):
        from common.models.rooms import Room
        room_id = "room-123"
        category = Category.DELUXE

        self.service.add_room(room_id, category)

        self.repo.add_room.assert_called_once()
        called_room = self.repo.add_room.call_args[1]["room"]
        self.assertIsInstance(called_room, Room)
        self.assertEqual(called_room.room_id, room_id)
        self.assertEqual(called_room.category, category)
