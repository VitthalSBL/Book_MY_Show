from django.db import models
from django.contrib.auth.models import User
import uuid


class Payment(models.Model):
    STATUS_CHOICES = [
        ('created', 'Created'),
        ('pending', 'Pending'),
        ('authorized', 'Authorized'),
        ('captured', 'Captured'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
        ('cancelled', 'Cancelled'),
    ]

    payment_id = models.CharField(max_length=40, unique=True, editable=False)
    booking = models.OneToOneField(
        'bookings.Booking', on_delete=models.CASCADE, related_name='payment'
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='INR')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='created')

    # Razorpay fields
    razorpay_order_id = models.CharField(max_length=100, blank=True, db_index=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True, db_index=True)
    razorpay_signature = models.CharField(max_length=200, blank=True)

    # Idempotency key to prevent duplicate processing from webhooks
    idempotency_key = models.CharField(max_length=100, unique=True, blank=True)

    failure_reason = models.TextField(blank=True)
    raw_response = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['razorpay_order_id']),
            models.Index(fields=['status', 'created_at']),
        ]

    def save(self, *args, **kwargs):
        if not self.payment_id:
            self.payment_id = f'PAY{uuid.uuid4().hex[:12].upper()}'
        if not self.idempotency_key:
            self.idempotency_key = str(uuid.uuid4())
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.payment_id} - {self.amount} - {self.status}'


class TransactionHistory(models.Model):
    """Immutable log of every payment event for audit & profile history"""
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name='history')
    event = models.CharField(max_length=50)  # created, authorized, captured, failed, refunded
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Transaction Histories'

    def __str__(self):
        return f'{self.payment.payment_id} - {self.event}'
