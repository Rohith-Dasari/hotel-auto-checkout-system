import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone, timedelta

from src.common.services.invoice_service import InvoiceService
from src.common.models.bookings import Booking
from src.common.models.rooms import Category
from src.common.utils.custom_exceptions import NotFoundException


class TestInvoiceService(unittest.TestCase):

    @patch("src.common.services.invoice_service.boto3.client")
    def setUp(self, mock_boto_client):
        self.mock_ses = MagicMock()
        mock_boto_client.return_value = self.mock_ses

        self.repo = MagicMock()
        self.service = InvoiceService(self.repo)

        now = datetime.now(timezone.utc)

        self.booking = Booking(
            booking_id="b1",
            user_id="u1",
            user_email="test@example.com",
            room_id="room42",
            category=Category.DELUXE,
            checkin=now - timedelta(days=2),
            checkout=now,
            price_per_night=1000.0
        )

    def test_generate_invoice_success(self):
        self.repo.get_booking_by_id.return_value = self.booking

        invoice = self.service.generate_invoice("b1")

        self.repo.get_booking_by_id.assert_called_once_with("b1")

        self.assertEqual(invoice.booking_id, "b1")
        self.assertEqual(invoice.user_email, "test@example.com")
        self.assertEqual(invoice.room_no, "room42")
        self.assertEqual(invoice.category, Category.DELUXE.value)
        self.assertEqual(invoice.nights, 2)
        self.assertEqual(invoice.price_per_night, 1000.0)
        self.assertEqual(invoice.total_amount, 2000.0)

    def test_generate_invoice_minimum_one_night(self):
        now = datetime.now(timezone.utc)
        self.booking.checkin = now
        self.booking.checkout = now

        self.repo.get_booking_by_id.return_value = self.booking

        invoice = self.service.generate_invoice("b1")

        self.assertEqual(invoice.nights, 1)
        self.assertEqual(invoice.total_amount, 1000.0)

    def test_generate_invoice_not_found(self):
        self.repo.get_booking_by_id.return_value = None

        with self.assertRaises(NotFoundException):
            self.service.generate_invoice("missing")

    def test_send_email_calls_ses(self):
        self.repo.get_booking_by_id.return_value = self.booking
        invoice = self.service.generate_invoice("b1")

        self.service.send_email(invoice)

        self.mock_ses.send_raw_email.assert_called_once()
        args, kwargs = self.mock_ses.send_raw_email.call_args

        self.assertIn("Source", kwargs)
        self.assertIn("Destinations", kwargs)
        self.assertIn("RawMessage", kwargs)

    @patch.object(InvoiceService, "send_email")
    @patch.object(InvoiceService, "store_invoice_in_s3")
    def test_send_invoice_flow(self, mock_store, mock_send):
        self.repo.get_booking_by_id.return_value = self.booking

        self.service.send_invoice("b1")

        mock_store.assert_called_once()
        mock_send.assert_called_once()


if __name__ == "__main__":
    unittest.main()
