"""PDF ticket generation and email sending"""
import os
from io import BytesIO
from django.conf import settings
from django.core.mail import EmailMessage
from django.core.files.base import ContentFile
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor, black, white
import qrcode


def generate_ticket_pdf(booking):
    """Generate PDF ticket with QR code for a confirmed booking"""
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # Header
    c.setFillColor(HexColor('#E50914'))
    c.rect(0, height - 80, width, 80, fill=1, stroke=0)
    c.setFillColor(white)
    c.setFont('Helvetica-Bold', 24)
    c.drawString(30, height - 45, 'BookMyShow Clone')
    c.setFont('Helvetica', 12)
    c.drawString(30, height - 65, 'E-Ticket / Booking Confirmation')

    # Booking details
    y = height - 120
    c.setFillColor(black)
    c.setFont('Helvetica-Bold', 16)
    c.drawString(30, y, booking.show.movie.title)
    y -= 25
    c.setFont('Helvetica', 11)
    c.drawString(30, y, f'Booking ID: {booking.booking_id}')
    y -= 18
    c.drawString(30, y, f'Theater: {booking.show.screen.theater.name}')
    y -= 18
    c.drawString(30, y, f'Screen: {booking.show.screen.name}')
    y -= 18
    c.drawString(30, y, f'Date & Time: {booking.show.datetime_display}')
    y -= 18
    if booking.show.language:
        c.drawString(30, y, f'Language: {booking.show.language.name}')
        y -= 18

    seats = [r.seat.seat_label for r in booking.seat_reservations.all()]
    c.drawString(30, y, f'Seats: {", ".join(seats)}')
    y -= 18
    c.drawString(30, y, f'Total Amount: ₹{booking.total_amount}')
    y -= 18
    c.drawString(30, y, f'Booked by: {booking.user.get_full_name() or booking.user.username}')
    y -= 30

    # QR Code
    qr_data = f'BMS|{booking.booking_id}|{booking.show.movie.title}|{",".join(seats)}'
    qr = qrcode.QRCode(version=1, box_size=6, border=2)
    qr.add_data(qr_data)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color='black', back_color='white')
    qr_buffer = BytesIO()
    qr_img.save(qr_buffer, format='PNG')
    qr_buffer.seek(0)

    from reportlab.lib.utils import ImageReader
    c.drawImage(ImageReader(qr_buffer), width - 150, height - 280, 100, 100)

    c.setFont('Helvetica', 9)
    c.setFillColor(HexColor('#666666'))
    c.drawString(30, 80, 'Please show this ticket (QR code) at the theater entrance.')
    c.drawString(30, 65, 'This is a computer-generated ticket. No signature required.')
    c.drawString(30, 50, f'Generated at: {booking.confirmed_at or booking.booked_at}')

    c.showPage()
    c.save()
    buffer.seek(0)

    # Save to booking
    filename = f'ticket_{booking.booking_id}.pdf'
    booking.pdf_ticket.save(filename, ContentFile(buffer.read()), save=True)
    return booking.pdf_ticket.path


def send_ticket_email(booking):
    """Send booking confirmation email with PDF attachment"""
    if not booking.user.email:
        return False

    subject = f'Booking Confirmed - {booking.show.movie.title} | {booking.booking_id}'
    seats = ', '.join(r.seat.seat_label for r in booking.seat_reservations.all())
    body = f"""Hi {booking.user.get_full_name() or booking.user.username},

Your booking is confirmed!

Movie: {booking.show.movie.title}
Theater: {booking.show.screen.theater.name}
Screen: {booking.show.screen.name}
Date & Time: {booking.show.datetime_display}
Seats: {seats}
Amount Paid: ₹{booking.total_amount}
Booking ID: {booking.booking_id}

Please find your e-ticket attached. Show the QR code at the entrance.

Thank you for booking with BookMyShow Clone!
"""
    email = EmailMessage(
        subject=subject,
        body=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[booking.user.email],
    )
    if booking.pdf_ticket:
        email.attach_file(booking.pdf_ticket.path)
    else:
        path = generate_ticket_pdf(booking)
        email.attach_file(path)
    email.send(fail_silently=True)
    return True
