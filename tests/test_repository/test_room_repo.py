import unittest
from unittest.mock import MagicMock
from datetime import datetime, timezone, timedelta
from botocore.exceptions import ClientError

from src.common.repository.room_repo import RoomRepository
from src.common.models.rooms import Category, RoomStatus, Room
from src.common.utils.custom_exceptions import NotFoundException


class TestRoomRepository(unittest.TestCase):
    def setUp(self):
        self.table = MagicMock()
        self.client = MagicMock()

        self.table.meta.client = self.client
        self.repo = RoomRepository(self.table, self.client)

        patcher = unittest.mock.patch("src.common.utils.datetime_normaliser.from_iso_string")
        self.addCleanup(patcher.stop)
        self.mock_from_iso = patcher.start()
        # Default: just use datetime.fromisoformat
        self.mock_from_iso.side_effect = lambda s: datetime.fromisoformat(s) if isinstance(s, str) else s

    def test_add_room_success(self):
        room = Room(room_id="r1", category=Category.DELUXE)
        self.client.transact_write_items.return_value = {}
        self.repo.add_room(room)
        self.client.transact_write_items.assert_called_once()
        args = self.client.transact_write_items.call_args[1]
        self.assertIn("TransactItems", args)
        self.assertEqual(args["TransactItems"][0]["Put"]["Item"]["pk"], "ROOM#r1")

    def test_add_room_duplicate(self):
        from botocore.exceptions import ClientError
        room = Room(room_id="r1", category=Category.DELUXE)
        error = ClientError({"Error": {"Code": "ConditionalCheckFailedException"}}, "TransactWriteItems")
        self.client.transact_write_items.side_effect = error
        with self.assertRaises(ClientError):
            self.repo.add_room(room)

    def test_add_room_other_client_error(self):
        from botocore.exceptions import ClientError
        room = Room(room_id="r1", category=Category.DELUXE)
        error = ClientError({"Error": {"Code": "InternalError"}}, "TransactWriteItems")
        self.client.transact_write_items.side_effect = error
        with self.assertRaises(ClientError):
            self.repo.add_room(room)

    def setUp(self):
        self.table = MagicMock()
        self.client = MagicMock()

        self.table.meta.client = self.client
        self.repo = RoomRepository(self.table, self.client)

    def test_get_room_by_id_success(self):
        self.table.get_item.return_value = {
            "Item": {
                "pk": "ROOM#r1",
                "sk": "DETAILS",
                "category": "DELUXE",
                "room_status": "AVAILABLE"
            }
        }

        room = self.repo.get_room_by_id("r1")

        self.table.get_item.assert_called_once_with(
            Key={"pk": "ROOM#r1", "sk": "DETAILS"}
        )

        self.assertIsInstance(room, Room)
        self.assertEqual(room.room_id, "r1")
        self.assertEqual(room.category, Category.DELUXE)
        self.assertEqual(room.status, RoomStatus.AVAILABLE)

    def test_get_room_by_id_not_found(self):
        self.table.get_item.return_value = {}

        result = self.repo.get_room_by_id("missing")

        self.assertIsNone(result)

    def test_get_room_by_id_client_error(self):
        self.table.get_item.side_effect = ClientError(
            error_response={"Error": {"Message": "Get failed"}},
            operation_name="GetItem"
        )

        with self.assertRaises(ClientError):
            self.repo.get_room_by_id("r1")

    def test_get_rooms_ids_by_category_success(self):
        self.table.query.return_value = {
            "Items": [
                {"pk": "CATEGORY#DELUXE", "sk": "ROOM#r1"},
                {"pk": "CATEGORY#DELUXE", "sk": "ROOM#r2"},
            ]
        }

        result = self.repo.get_rooms_ids_by_category(Category.DELUXE)

        self.table.query.assert_called_once()
        self.assertEqual(result, ["r1", "r2"])

    def test_get_rooms_ids_by_category_empty(self):
        self.table.query.return_value = {"Items": []}

        result = self.repo.get_rooms_ids_by_category(Category.DELUXE)

        self.assertEqual(result, [])

    def test_get_rooms_ids_by_category_client_error(self):
        self.table.query.side_effect = ClientError(
            error_response={"Error": {"Message": "Query failed"}},
            operation_name="Query"
        )

        with self.assertRaises(ClientError):
            self.repo.get_rooms_ids_by_category(Category.DELUXE)

    def test_get_category_price_success(self):
        self.table.get_item.return_value = {
            "Item": {
                "pk": "CATEGORY#DELUXE",
                "sk": "DETAILS",
                "price": "2000"
            }
        }

        price = self.repo.get_category_price(Category.DELUXE)

        self.assertEqual(price, 2000.0)

    def test_get_category_price_not_found(self):
        self.table.get_item.return_value = {}

        result = self.repo.get_category_price(Category.DELUXE)

        self.assertIsNone(result)

    def test_get_category_price_client_error(self):
        self.table.get_item.side_effect = ClientError(
            error_response={"Error": {"Message": "Get failed"}},
            operation_name="GetItem"
        )

        with self.assertRaises(ClientError):
            self.repo.get_category_price(Category.DELUXE)

    def test_update_room_status_success(self):
        self.table.update_item.return_value = {}

        self.repo.update_room_status("r1", RoomStatus.HOUSEKEEPING)

        self.table.update_item.assert_called_once()

    def test_update_room_status_not_found(self):
        error = ClientError(
            error_response={"Error": {"Code": "ConditionalCheckFailedException"}},
            operation_name="UpdateItem"
        )
        self.table.update_item.side_effect = error

        with self.assertRaises(NotFoundException):
            self.repo.update_room_status("r1", RoomStatus.HOUSEKEEPING)

    def test_update_room_status_other_error(self):
        error = ClientError(
            error_response={"Error": {"Code": "InternalError"}},
            operation_name="UpdateItem"
        )
        self.table.update_item.side_effect = error

        with self.assertRaises(ClientError):
            self.repo.update_room_status("r1", RoomStatus.HOUSEKEEPING)

    def test_to_utc_success(self):
        dt = datetime.now(timezone.utc)

        result = self.repo._to_utc(dt)

        self.assertEqual(result.tzinfo, timezone.utc)

    def test_to_utc_naive_fails(self):
        naive = datetime.now()

        with self.assertRaises(ValueError):
            self.repo._to_utc(naive)

    def test_to_iso_and_from_iso_roundtrip(self):
        dt = datetime.now(timezone.utc)
        iso = self.repo._to_iso(dt)
        from src.common.utils.datetime_normaliser import from_iso_string
        parsed = from_iso_string(iso)
        self.assertEqual(parsed, dt)


    def test_get_available_rooms_blocks_overlapping(self):
        now = datetime.now(timezone.utc)
        checkin = now + timedelta(days=1)
        checkout = now + timedelta(days=2)
        self.repo.get_rooms_ids_by_category = MagicMock(return_value=["r1", "r2"])
        def fake_from_iso(s):
            if "r1" in s:
                if "checkout" in s:
                    return checkin + timedelta(hours=1)
                else:
                    return checkin
            return datetime.fromisoformat(s)
        patcher = unittest.mock.patch("src.common.utils.datetime_normaliser.from_iso_string", side_effect=fake_from_iso)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.table.query.return_value = {
            "Items": [
                {
                    "room_id": "r1",
                    "checkout": (checkin + timedelta(hours=1)).isoformat(),
                    "sk": f"CHECKIN#{checkin.isoformat()}#ROOM#r1"
                }
            ]
        }
        available = self.repo.get_available_rooms(Category.DELUXE, checkin, checkout)
        self.assertEqual(set(available), {"r2"})

    def test_get_available_rooms_pagination(self):
        now = datetime.now(timezone.utc)
        checkin = now + timedelta(days=1)
        checkout = now + timedelta(days=2)
        self.repo.get_rooms_ids_by_category = MagicMock(return_value=["r1", "r2", "r3"])
        def fake_from_iso(s):
            if "r1" in s:
                if "checkout" in s:
                    return checkin + timedelta(hours=1)
                else:
                    return checkin
            if "r2" in s:
                if "checkout" in s:
                    return checkin + timedelta(hours=2)
                else:
                    return checkin
            return datetime.fromisoformat(s)
        patcher = unittest.mock.patch("src.common.utils.datetime_normaliser.from_iso_string", side_effect=fake_from_iso)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.table.query.side_effect = [
            {
                "Items": [
                    {
                        "room_id": "r1",
                        "checkout": (checkin + timedelta(hours=1)).isoformat(),
                        "sk": f"CHECKIN#{checkin.isoformat()}#ROOM#r1"
                    }
                ],
                "LastEvaluatedKey": True
            },
            {
                "Items": [
                    {
                        "room_id": "r2",
                        "checkout": (checkin + timedelta(hours=2)).isoformat(),
                        "sk": f"CHECKIN#{checkin.isoformat()}#ROOM#r2"
                    }
                ]
            }
        ]
        available = self.repo.get_available_rooms(Category.DELUXE, checkin, checkout)
        self.assertEqual(set(available), {"r3"})

    def test_get_available_rooms_no_rooms_in_category(self):
        self.repo.get_rooms_ids_by_category = MagicMock(return_value=[])
        now = datetime.now(timezone.utc)
        import sys
        sys.modules["src.common.utils.constants"].MAX_STAY = 30
        available = self.repo.get_available_rooms(
            Category.DELUXE,
            now + timedelta(days=1),
            now + timedelta(days=2)
        )
        self.assertEqual(available, [])

    def test_get_available_rooms_query_error(self):
        now = datetime.now(timezone.utc)
        checkin = now + timedelta(days=1)
        checkout = now + timedelta(days=2)
        self.repo.get_rooms_ids_by_category = MagicMock(return_value=["r1"])
        self.table.query.side_effect = ClientError(
            error_response={"Error": {"Message": "Query failed"}},
            operation_name="Query"
        )
        import sys
        sys.modules["src.common.utils.constants"].MAX_STAY = 30
        with self.assertRaises(ClientError):
            self.repo.get_available_rooms(Category.DELUXE, checkin, checkout)

    def test_get_available_rooms_no_rooms_in_category(self):
        self.repo.get_rooms_ids_by_category = MagicMock(
            return_value=[]
        )

        now = datetime.now(timezone.utc)

        available = self.repo.get_available_rooms(
            Category.DELUXE,
            now + timedelta(days=1),
            now + timedelta(days=2)
        )

        self.assertEqual(available, [])

    def test_get_available_rooms_query_error_raises(self):
        now = datetime.now(timezone.utc)
        checkin = now + timedelta(days=1)
        checkout = now + timedelta(days=2)
        self.repo.get_rooms_ids_by_category = MagicMock(return_value=["r1"])
        self.table.query.side_effect = ClientError(
            error_response={"Error": {"Message": "Query failed"}},
            operation_name="Query"
        )
        import sys
        sys.modules["src.common.utils.constants"].MAX_STAY = 30
        with self.assertRaises(ClientError):
            self.repo.get_available_rooms(Category.DELUXE, checkin, checkout)


if __name__ == "__main__":
    unittest.main()
