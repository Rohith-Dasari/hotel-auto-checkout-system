import importlib
import os
import unittest
from unittest.mock import MagicMock, patch

from botocore.exceptions import ClientError
from src.common.utils.custom_exceptions import NotFoundException


class TestAutoCheckout(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.env = patch.dict(
            os.environ,
            {
                "TABLE_NAME": "test-table",
            },
            clear=False,
        )
        cls.env.start()

        cls.resource = patch("src.handlers.checkout.auto_checkout.resource")
        mock_res = cls.resource.start()
        mock_res.return_value.Table.return_value = MagicMock()

        import src.handlers.checkout.auto_checkout as mod
        cls.mod = importlib.reload(mod)

    @classmethod
    def tearDownClass(cls):
        cls.resource.stop()
        cls.env.stop()

    def setUp(self):
        self.p_booking = patch.object(self.mod, "booking_service")
        self.p_invoice = patch.object(self.mod, "invoice_service")

        self.mock_booking = self.p_booking.start()
        self.mock_invoice = self.p_invoice.start()

    def tearDown(self):
        self.p_booking.stop()
        self.p_invoice.stop()

    def _event(self, booking_id="b1", room_id="r1", user_id="u1"):
        return {
            "booking_id": booking_id,
            "room_id": room_id,
            "user_id": user_id,
        }

    def test_auto_checkout_success(self):
        resp = self.mod.auto_checkout(self._event(), None)

        self.mock_booking.update_booking.assert_called_once_with(
            booking_id="b1",
            room_id="r1",
            user_id="u1",
        )

        self.mock_invoice.send_invoice.assert_called_once_with("b1")

    def test_missing_booking_id(self):
        with self.assertRaises(KeyError):
            self.mod.auto_checkout(
                self._event(booking_id=None),
                None
            )

    def test_missing_room_id(self):
        with self.assertRaises(KeyError):
            self.mod.auto_checkout(
                self._event(room_id=None),
                None
            )

    def test_missing_user_id(self):
        with self.assertRaises(KeyError):
            self.mod.auto_checkout(
                self._event(user_id=None),
                None
            )

    def test_not_found_exception(self):
        self.mock_booking.update_booking.side_effect = NotFoundException(
            "booking", "b1", 404
        )

        self.mod.auto_checkout(self._event(), None)

        self.mock_booking.update_booking.assert_called_once()
        self.mock_invoice.send_invoice.assert_not_called()

    def test_client_error(self):
        self.mock_booking.update_booking.side_effect = ClientError(
            {"Error": {"Code": "InternalError"}},
            "UpdateItem"
        )

        self.mod.auto_checkout(self._event(), None)

        self.mock_booking.update_booking.assert_called_once()
        self.mock_invoice.send_invoice.assert_not_called()

    def test_generic_exception(self):
        self.mock_booking.update_booking.side_effect = RuntimeError("boom")

        self.mod.auto_checkout(self._event(), None)

        self.mock_booking.update_booking.assert_called_once()
        self.mock_invoice.send_invoice.assert_not_called()


if __name__ == "__main__":
    unittest.main()
