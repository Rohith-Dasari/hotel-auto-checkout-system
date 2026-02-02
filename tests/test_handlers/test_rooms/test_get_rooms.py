import importlib, json, os, unittest
from unittest.mock import MagicMock, patch
from common.models.users import UserRole
from common.utils.custom_exceptions import NoAvailableRooms, InvalidDates

class GetRoomsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.env = patch.dict(os.environ, {"TABLE_NAME": "test-table"}, clear=False)
        cls.env.start()
        cls.resource = patch("handlers.rooms.get_rooms.resource")
        mock_res = cls.resource.start()
        mock_res.return_value.Table.return_value = MagicMock()
        import handlers.rooms.get_rooms as mod
        cls.mod = importlib.reload(mod)

    @classmethod
    def tearDownClass(cls):
        cls.resource.stop(); cls.env.stop()

    def setUp(self):
        self.p_send = patch(
            "handlers.rooms.get_rooms.send_custom_response",
            side_effect=lambda status_code, message=None, data=None: {
                "statusCode": status_code,
                "body": json.dumps({"message": message, "data": data})
            }
        )
        self.p_get = patch.object(self.mod.room_service, "get_available_rooms")
        self.p_parse = patch("handlers.rooms.get_rooms._parse_iso_datetime")
        self.mock_send = self.p_send.start()
        self.mock_get = self.p_get.start()
        self.mock_parse = self.p_parse.start()
        # default parse -> real datetime
        from datetime import datetime
        self.mock_parse.side_effect = lambda s: datetime.fromisoformat(s)

    def tearDown(self):
        self.p_send.stop(); self.p_get.stop(); self.p_parse.stop()

    def _event(self, category="deluxe", checkin="2026-01-01T00:00:00+00:00", checkout="2026-01-02T00:00:00+00:00", role=None):
        ctx = {"authorizer": {"role": role}} if role else {}
        return {"queryStringParameters": {"category": category, "checkin": checkin, "checkout": checkout},
                "requestContext": ctx}

    def test_missing_params(self):
        resp = self.mod.get_rooms({"queryStringParameters": {}}, None)
        self.assertEqual(400, resp["statusCode"])

    def test_invalid_category(self):
        resp = self.mod.get_rooms(self._event(category="unknown"), None)
        self.assertEqual(400, resp["statusCode"])

    def test_checkout_before_checkin(self):
        self.mock_parse.side_effect = ["2026-01-02", "2026-01-01"]
        resp = self.mod.get_rooms(self._event(), None)
        self.assertEqual(400, resp["statusCode"])

    def test_no_available_rooms(self):
        self.mock_get.side_effect = NoAvailableRooms("no rooms")
        resp = self.mod.get_rooms(self._event(), None)
        self.assertEqual(404, resp["statusCode"])

    def test_invalid_dates_exception(self):
        self.mock_get.side_effect = InvalidDates("bad dates")
        resp = self.mod.get_rooms(self._event(), None)
        self.assertEqual(400, resp["statusCode"])

    def test_parse_datetime_error(self):
        self.mock_parse.side_effect = ValueError("bad dt")
        resp = self.mod.get_rooms(self._event(), None)
        self.assertEqual(400, resp["statusCode"])

    def test_success_customer_hides_rooms(self):
        self.mock_get.return_value = ["r1", "r2"]
        resp = self.mod.get_rooms(self._event(role=UserRole.CUSTOMER.value), None)
        self.assertEqual(200, resp["statusCode"])
        body = json.loads(resp["body"])
        self.assertNotIn("available_rooms", body["data"])
        self.assertEqual(2, body["data"]["count"])

    def test_success_staff_shows_rooms(self):
        self.mock_get.return_value = ["r1", "r2"]
        resp = self.mod.get_rooms(self._event(role=UserRole.MANAGER.value), None)
        self.assertEqual(200, resp["statusCode"])
        body = json.loads(resp["body"])
        self.assertEqual(["r1", "r2"], body["data"]["available_rooms"])
        self.assertEqual(2, body["data"]["count"])

    def test_generic_error(self):
        self.mock_get.side_effect = RuntimeError("boom")
        resp = self.mod.get_rooms(self._event(), None)
        self.assertEqual(500, resp["statusCode"])

if __name__ == "__main__":
    unittest.main()