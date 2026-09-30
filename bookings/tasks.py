from celery import shared_task
from django.utils import timezone
from .models import Booking, SeatReservation


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_booking_confirmation(self, booking_id):
    """Async task: generate PDF + send email. Retries on failure."""
    try:
        booking = Booking.objects.select_related(
            'user', 'show__movie', 'show__screen__theater'
        ).prefetch_related('seat_reservations__seat').get(pk=booking_id)
        from .services import generate_ticket_pdf, send_ticket_email
        generate_ticket_pdf(booking)
        send_ticket_email(booking)
        return f'Email sent for {booking.booking_id}'
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task
def release_expired_holds():
    """Periodic task: release seats whose hold has expired"""
    now = timezone.now()
    expired = SeatReservation.objects.filter(status='held', held_until__lt=now)
    count = expired.count()
    booking_ids = list(expired.values_list('booking_id', flat=True).distinct())
    expired.update(status='available', held_by=None, held_at=None, held_until=None, booking=None)
    Booking.objects.filter(id__in=booking_ids, status='pending').update(status='expired')
    return f'Released {count} expired holds'
