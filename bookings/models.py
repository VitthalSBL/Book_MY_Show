from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.conf import settings
import uuid


class Booking(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending Payment'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
        ('expired', 'Expired'),
        ('refunded', 'Refunded'),
    ]

    booking_id = models.CharField(max_length=20, unique=True, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookings')
    show = models.ForeignKey('theaters.Show', on_delete=models.CASCADE, related_name='bookings')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    seats_count = models.PositiveIntegerField(default=0)
    booked_at = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)  # for pending holds
    qr_code = models.ImageField(upload_to='qr_codes/', blank=True, null=True)
    pdf_ticket = models.FileField(upload_to='tickets/', blank=True, null=True)

    class Meta:
        ordering = ['-booked_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['show', 'status']),
            models.Index(fields=['booking_id']),
            models.Index(fields=['status', 'expires_at']),
            models.Index(fields=['booked_at']),
        ]

    def save(self, *args, **kwargs):
        if not self.booking_id:
            self.booking_id = self._generate_booking_id()
        if self.status == 'pending' and not self.expires_at:
            self.expires_at = timezone.now() + timezone.timedelta(seconds=settings.SEAT_HOLD_TIMEOUT)
        super().save(*args, **kwargs)

    def _generate_booking_id(self):
        return f'BMS{uuid.uuid4().hex[:10].upper()}'

    def __str__(self):
        return f'{self.booking_id} - {self.user.username} - {self.status}'

    @property
    def is_expired(self):
        if self.status == 'pending' and self.expires_at:
            return timezone.now() > self.expires_at
        return False

    def confirm(self):
        self.status = 'confirmed'
        self.confirmed_at = timezone.now()
        self.save(update_fields=['status', 'confirmed_at'])

    def cancel(self):
        self.status = 'cancelled'
        self.cancelled_at = timezone.now()
        self.save(update_fields=['status', 'cancelled_at'])
        # Release seats
        self.seat_reservations.filter(status__in=['held', 'booked']).update(status='available')


class SeatReservation(models.Model):
    """
    Critical model for concurrency control.
    status: available | held | booked
    Uses select_for_update() in views to prevent double booking.
    """
    STATUS_CHOICES = [
        ('available', 'Available'),
        ('held', 'Temporarily Held'),
        ('booked', 'Booked'),
    ]

    show = models.ForeignKey('theaters.Show', on_delete=models.CASCADE, related_name='seat_reservations')
    seat = models.ForeignKey('theaters.Seat', on_delete=models.CASCADE, related_name='reservations')
    booking = models.ForeignKey(
        Booking, on_delete=models.SET_NULL, null=True, blank=True, related_name='seat_reservations'
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available')
    held_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name='held_seats'
    )
    held_at = models.DateTimeField(null=True, blank=True)
    held_until = models.DateTimeField(null=True, blank=True)
    price = models.DecimalField(max_digits=8, decimal_places=2, default=0)

    class Meta:
        unique_together = ('show', 'seat')
        indexes = [
            models.Index(fields=['show', 'status']),
            models.Index(fields=['held_until']),
            models.Index(fields=['booking']),
            models.Index(fields=['show', 'seat', 'status']),
        ]

    def __str__(self):
        return f'{self.seat} @ {self.show} - {self.status}'

    @property
    def is_hold_expired(self):
        if self.status == 'held' and self.held_until:
            return timezone.now() > self.held_until
        return False
