import importlib
import json
import os
import unittest
from unittest.mock import MagicMock, patch

from common.models.rooms import Category
from common.utils.custom_exceptions import NotFoundException, NoAvailableRooms


class CreateBookingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.env = patch.dict(
            os.environ,
            {
                "TABLE_NAME": "test-table",
                "AUTO_CHECKOUT_LAMBDA_ARN": "arn:lambda",
                "SCHEDULER_ROLE_ARN": "arn:role",
            },
            clear=False,
        )
        cls.env.start()
        cls.resource = patch("handlers.bookings.create_booking.resource")
        mock_res = cls.resource.start()
        mock_res.return_value.Table.return_value = MagicMock()
        import handlers.bookings.create_booking as mod
        cls.mod = importlib.reload(mod)

    @classmethod
    def tearDownClass(cls):
        cls.resource.stop()
        cls.env.stop()

    def setUp(self):
        self.p_send = patch(
            "handlers.bookings.create_booking.send_custom_response",
            side_effect=lambda status_code, message=None, data=None: {
                "statusCode": status_code,
                "body": json.dumps({"message": message, "data": data}),
            },
        )
        self.p_add = patch.object(self.mod.booking_service, "add_booking")
        self.p_validate = patch("handlers.bookings.create_booking.BookingRequest.model_validate_json")
        self.mock_send = self.p_send.start()
        self.mock_add = self.p_add.start()
        self.mock_validate = self.p_validate.start()

    def tearDown(self):
        self.p_send.stop()
        self.p_add.stop()
        self.p_validate.stop()

    def _event(self, body=None, user_id="u1"):
        return {
            "body": body,
            "requestContext": {"authorizer": {"user_id": user_id} if user_id else {}},
        }

    def test_missing_body_returns_400(self):
        resp = self.mod.create_booking({}, None)
        self.assertEqual(400, resp["statusCode"])

    def test_validation_error_returns_400(self):
        from pydantic import ValidationError

        self.mock_validate.side_effect = ValidationError.from_exception_data("BookingRequest", [])
        resp = self.mod.create_booking(self._event(body="{}"), None)
        self.assertEqual(400, resp["statusCode"])

    def test_missing_user_in_authorizer_returns_401(self):
        self.mock_validate.return_value = MagicMock()
        resp = self.mod.create_booking(self._event(body="{}", user_id=None), None)
        self.assertEqual(401, resp["statusCode"])

    def test_value_error_invalid_category_returns_400(self):
        self.mock_validate.return_value = MagicMock()
        self.mock_add.side_effect = ValueError("bad category")
        resp = self.mod.create_booking(self._event(body="{}"), None)
        self.assertEqual(400, resp["statusCode"])
        body = json.loads(resp["body"])
        self.assertIn("Invalid category", body["message"])

    def test_not_found_returns_status_from_exception(self):
        self.mock_validate.return_value = MagicMock()
        self.mock_add.side_effect = NotFoundException("user", "u1", 404)
        resp = self.mod.create_booking(self._event(body="{}"), None)
        self.assertEqual(404, resp["statusCode"])

    def test_no_available_rooms_returns_404(self):
        self.mock_validate.return_value = MagicMock()
        self.mock_add.side_effect = NoAvailableRooms("none")
        resp = self.mod.create_booking(self._event(body="{}"), None)
        self.assertEqual(404, resp["statusCode"])

    def test_generic_error_returns_500(self):
        self.mock_validate.return_value = MagicMock()
        self.mock_add.side_effect = RuntimeError("boom")
        resp = self.mod.create_booking(self._event(body="{}"), None)
        self.assertEqual(500, resp["statusCode"])

    def test_success_returns_201(self):
        req = MagicMock()
        req.category = Category.DELUXE
        self.mock_validate.return_value = req
        resp = self.mod.create_booking(self._event(body="{}"), None)
        self.assertEqual(201, resp["statusCode"])
        self.mock_add.assert_called_once()


if __name__ == "__main__":
    unittest.main()
