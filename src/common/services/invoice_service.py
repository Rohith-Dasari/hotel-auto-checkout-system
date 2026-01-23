from src.common.models.invoice import Invoice
from src.common.models.bookings import Booking
from src.common.repository.booking_repo import BookingRepository


import boto3
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os


class InvoiceService:
    def __init__(self, booking_repo):
        self.booking_repo = booking_repo
        self.ses = boto3.client(
            "ses"
        )

    def send_email(self, invoice:Invoice):
        sender = "invoice@rohith-dasari.me"
        recipient = invoice.user_email

        subject = f"Invoice for Booking {invoice.booking_id}"

        body = f"""
            Hello,

            Here is your booking invoice:

            Booking ID: {invoice.booking_id}
            Room No: {invoice.room_no}
            Category: {invoice.category}

            Check-in: {invoice.checkin}
            Check-out: {invoice.checkout}
            Nights: {invoice.nights}

            Price per Night: ₹{invoice.price_per_night}
            Total Amount: ₹{invoice.total_amount}

            Thank you for staying with us.
            """

        msg = MIMEMultipart()
        msg["From"] = sender
        msg["To"] = recipient
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        self.ses.send_raw_email(
            Source=sender,
            Destinations=[recipient],
            RawMessage={"Data": msg.as_string()},
        )


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

    def store_invoice_in_s3(self,invoice: Invoice):
        pass


