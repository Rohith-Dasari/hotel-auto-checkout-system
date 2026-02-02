import importlib
import json
import os
import unittest
from unittest.mock import MagicMock, patch
from common.models.users import UserRole
from common.utils.custom_exceptions import NotFoundException

class GetUserBookingsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.env = patch.dict(os.environ, {"TABLE_NAME": "test-table"}, clear=False)
        cls.env.start()
        cls.resource = patch("handlers.bookings.get_bookings.resource")
        mock_res = cls.resource.start()
        mock_res.return_value.Table.return_value = MagicMock()
        import handlers.bookings.get_bookings as mod
        cls.mod = importlib.reload(mod)

    @classmethod
    def tearDownClass(cls):
        cls.resource.stop(); cls.env.stop()

    def setUp(self):
        self.p_send = patch(
            "handlers.bookings.get_bookings.send_custom_response",
            side_effect=lambda status_code, message=None, data=None: {
                "statusCode": status_code,
                "body": json.dumps({"message": message, "data": data})
            },
        )
        self.p_get = patch.object(self.mod.booking_service, "get_user_bookings")
        self.mock_send = self.p_send.start()
        self.mock_get = self.p_get.start()

    def tearDown(self):
        self.p_send.stop(); self.p_get.stop()

    def _event(self, user_id="u1", role=UserRole.CUSTOMER.value, path_user_id=None):
        event = {
            "requestContext": {"authorizer": {"user_id": user_id, "role": role}},
            "pathParameters": {"user_id": path_user_id} if path_user_id else {},
        }
        return event

    def test_missing_authorizer_returns_401(self):
        resp = self.mod.get_user_bookings({"requestContext": {}}, None)
        self.assertEqual(401, resp["statusCode"])

    def test_invalid_role_value_treated_as_none(self):
        self.mock_get.return_value = []
        resp = self.mod.get_user_bookings(self._event(role="bad"), None)
        self.assertEqual(200, resp["statusCode"])

    def test_customer_forbidden_on_other_user(self):
        resp = self.mod.get_user_bookings(self._event(user_id="u1", role=UserRole.CUSTOMER.value, path_user_id="u2"), None)
        self.assertEqual(403, resp["statusCode"])

    def test_manager_can_access_other_user(self):
        self.mock_get.return_value = []
        resp = self.mod.get_user_bookings(self._event(user_id="u1", role=UserRole.MANAGER.value, path_user_id="u2"), None)
        self.assertEqual(200, resp["statusCode"])
        self.mock_get.assert_called_with("u2")

    def test_admin_can_access_other_user(self):
        self.mock_get.return_value = []
        resp = self.mod.get_user_bookings(self._event(user_id="u1", role=UserRole.ADMIN.value, path_user_id="u2"), None)
        self.assertEqual(200, resp["statusCode"])
        self.mock_get.assert_called_with("u2")

    def test_customer_gets_own_bookings(self):
        self.mock_get.return_value = []
        resp = self.mod.get_user_bookings(self._event(user_id="u1", role=UserRole.CUSTOMER.value, path_user_id="u1"), None)
        self.assertEqual(200, resp["statusCode"])
        self.mock_get.assert_called_with("u1")

    def test_success_returns_bookings(self):
        from datetime import datetime, timezone
        b = MagicMock()
        b.booking_id = "b1"
        b.room_id = "r1"
        b.category.value = "DELUXE"
        b.status.value = "UPCOMING"
        b.checkin = datetime(2026, 1, 1, tzinfo=timezone.utc)
        b.checkout = datetime(2026, 1, 2, tzinfo=timezone.utc)
        b.price_per_night = 1500.0
        b.booked_at = datetime(2025, 12, 31, tzinfo=timezone.utc)
        self.mock_get.return_value = [b]
        resp = self.mod.get_user_bookings(self._event(), None)
        self.assertEqual(200, resp["statusCode"])
        body = json.loads(resp["body"])
        self.assertEqual(1, body["data"]["count"])
        self.assertEqual("b1", body["data"]["bookings"][0]["booking_id"])

    def test_not_found_exception_returns_status(self):
        self.mock_get.side_effect = NotFoundException("user", "u1", 404)
        resp = self.mod.get_user_bookings(self._event(), None)
        self.assertEqual(404, resp["statusCode"])

    def test_generic_error_returns_500(self):
        self.mock_get.side_effect = RuntimeError("boom")
        resp = self.mod.get_user_bookings(self._event(), None)
        self.assertEqual(500, resp["statusCode"])

if __name__ == "__main__":
    unittest.main()
