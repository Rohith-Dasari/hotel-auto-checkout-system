from src.common.models.invoice import Invoice
from src.common.models.bookings import Booking
from src.common.repository.booking_repo import BookingRepository


class InvoiceService:
    def __init__(self, booking_repo: BookingRepository):
        self.booking_repo = booking_repo

    def send_invoice(self, booking_id: str):
        invoice = self.generate_invoice(booking_id)
        self.store_invoice_in_s3(invoice)
        self.send_email(invoice)

    def generate_invoice(self, booking_id: str) -> Invoice:
        booking = self.booking_repo.get_booking_by_id(booking_id)
        nights = (booking.checkout - booking.checkin).days
        total_price = nights * booking.price_per_night
        invoice = Invoice(
            booking_id=booking.booking_id,
            user_email=booking.user_email,
            room_no=booking.room_no,
            category=booking.category,
            checkin=booking.checkin,
            checkout=booking.checkout,
            nights=nights,
            price_per_night=booking.price_per_night,
            total_amount=total_price,
        )
        return invoice

    def store_invoice_in_s3(invoice: Invoice):
        pass

    def send_email(invoice: Invoice):
        pass
