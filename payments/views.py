from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.db import transaction
from django.utils import timezone
from django.conf import settings
import razorpay
import json
import hmac
import hashlib

from .models import Payment, TransactionHistory
from bookings.models import Booking, SeatReservation


def get_razorpay_client():
    return razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))


@login_required
def create_payment(request, booking_id):
    booking = get_object_or_404(
        Booking.objects.select_related('show__movie', 'user'),
        booking_id=booking_id, user=request.user
    )
    if booking.status != 'pending':
        messages.warning(request, 'This booking is no longer pending payment.')
        return redirect('bookings:detail', booking_id=booking_id)

    if booking.is_expired:
        booking.status = 'expired'
        booking.save(update_fields=['status'])
        SeatReservation.objects.filter(booking=booking).update(
            status='available', held_by=None, held_at=None, held_until=None, booking=None
        )
        messages.error(request, 'Seat hold expired. Please select seats again.')
        return redirect('theaters:seat_selection', show_id=booking.show_id)

    # Create or get payment
    payment, created = Payment.objects.get_or_create(
        booking=booking,
        defaults={
            'user': request.user,
            'amount': booking.total_amount,
            'status': 'created',
        }
    )

    # Create Razorpay order if needed
    if not payment.razorpay_order_id or payment.status in ('failed', 'cancelled'):
        client = get_razorpay_client()
        amount_paise = int(booking.total_amount * 100)
        try:
            order = client.order.create({
                'amount': amount_paise,
                'currency': 'INR',
                'receipt': booking.booking_id,
                'notes': {'booking_id': booking.booking_id, 'user': request.user.username},
            })
            payment.razorpay_order_id = order['id']
            payment.status = 'pending'
            payment.save(update_fields=['razorpay_order_id', 'status'])
            TransactionHistory.objects.create(
                payment=payment, event='created', amount=payment.amount,
                details={'order_id': order['id']}
            )
        except Exception as e:
            # Fallback for missing/invalid keys - demo mode
            payment.razorpay_order_id = f'order_demo_{booking.booking_id}'
            payment.status = 'pending'
            payment.save(update_fields=['razorpay_order_id', 'status'])
            messages.info(request, 'Running in demo payment mode (Razorpay keys not configured).')

    return render(request, 'payments/checkout.html', {
        'booking': booking,
        'payment': payment,
        'razorpay_key_id': settings.RAZORPAY_KEY_ID,
        'amount_paise': int(booking.total_amount * 100),
    })


@login_required
@require_POST
def payment_callback(request):
    """Client-side callback after Razorpay checkout"""
    razorpay_order_id = request.POST.get('razorpay_order_id')
    razorpay_payment_id = request.POST.get('razorpay_payment_id')
    razorpay_signature = request.POST.get('razorpay_signature')
    booking_id = request.POST.get('booking_id')

    payment = get_object_or_404(Payment, razorpay_order_id=razorpay_order_id, user=request.user)
    booking = payment.booking

    # Demo mode bypass
    if razorpay_order_id.startswith('order_demo_'):
        return _confirm_payment(payment, booking, razorpay_payment_id or 'demo_pay', razorpay_signature or 'demo_sig')

    # Verify signature
    client = get_razorpay_client()
    try:
        client.utility.verify_payment_signature({
            'razorpay_order_id': razorpay_order_id,
            'razorpay_payment_id': razorpay_payment_id,
            'razorpay_signature': razorpay_signature,
        })
    except Exception:
        payment.status = 'failed'
        payment.failure_reason = 'Signature verification failed'
        payment.save()
        TransactionHistory.objects.create(
            payment=payment, event='failed', amount=payment.amount,
            details={'reason': 'signature_mismatch'}
        )
        messages.error(request, 'Payment verification failed.')
        return redirect('payments:failure', payment_id=payment.payment_id)

    return _confirm_payment(payment, booking, razorpay_payment_id, razorpay_signature)


def _confirm_payment(payment, booking, razorpay_payment_id, razorpay_signature):
    """Idempotent payment confirmation"""
    with transaction.atomic():
        payment = Payment.objects.select_for_update().get(pk=payment.pk)
        if payment.status == 'captured':
            # Already processed (idempotent)
            return redirect('payments:success', payment_id=payment.payment_id)

        payment.razorpay_payment_id = razorpay_payment_id
        payment.razorpay_signature = razorpay_signature
        payment.status = 'captured'
        payment.paid_at = timezone.now()
        payment.save()

        TransactionHistory.objects.create(
            payment=payment, event='captured', amount=payment.amount,
            details={'payment_id': razorpay_payment_id}
        )

        # Confirm booking & seats
        booking.status = 'confirmed'
        booking.confirmed_at = timezone.now()
        booking.save(update_fields=['status', 'confirmed_at'])

        SeatReservation.objects.filter(booking=booking).update(status='booked', held_by=None, held_at=None, held_until=None)

    # Async email + PDF (Celery or sync fallback)
    try:
        from bookings.tasks import send_booking_confirmation
        send_booking_confirmation.delay(booking.id)
    except Exception:
        from bookings.services import generate_ticket_pdf, send_ticket_email
        try:
            generate_ticket_pdf(booking)
            send_ticket_email(booking)
        except Exception:
            pass

    return redirect('payments:success', payment_id=payment.payment_id)


@csrf_exempt
@require_POST
def razorpay_webhook(request):
    """
    Server-side webhook with idempotency.
    Prevents duplicate booking confirmation from repeated webhooks.
    """
    webhook_secret = settings.RAZORPAY_WEBHOOK_SECRET
    signature = request.headers.get('X-Razorpay-Signature', '')
    body = request.body

    # Verify webhook signature (skip in demo)
    if webhook_secret and webhook_secret != 'webhook_secret':
        expected = hmac.new(
            webhook_secret.encode(), body, hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(expected, signature):
            return HttpResponse(status=400)

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return HttpResponse(status=400)

    event = payload.get('event', '')
    if event != 'payment.captured':
        return HttpResponse(status=200)

    entity = payload.get('payload', {}).get('payment', {}).get('entity', {})
    order_id = entity.get('order_id')
    payment_id = entity.get('id')

    if not order_id:
        return HttpResponse(status=200)

    try:
        with transaction.atomic():
            payment = Payment.objects.select_for_update().filter(
                razorpay_order_id=order_id
            ).first()
            if not payment:
                return HttpResponse(status=200)

            # Idempotency check
            if payment.status == 'captured':
                return HttpResponse(status=200)

            payment.razorpay_payment_id = payment_id
            payment.status = 'captured'
            payment.paid_at = timezone.now()
            payment.raw_response = entity
            payment.save()

            TransactionHistory.objects.create(
                payment=payment, event='captured_webhook', amount=payment.amount,
                details={'payment_id': payment_id, 'source': 'webhook'}
            )

            booking = payment.booking
            if booking.status == 'pending':
                booking.status = 'confirmed'
                booking.confirmed_at = timezone.now()
                booking.save(update_fields=['status', 'confirmed_at'])
                SeatReservation.objects.filter(booking=booking).update(status='booked', held_by=None, held_at=None, held_until=None)

                try:
                    from bookings.tasks import send_booking_confirmation
                    send_booking_confirmation.delay(booking.id)
                except Exception:
                    pass
    except Exception:
        return HttpResponse(status=500)

    return HttpResponse(status=200)


@login_required
def payment_success(request, payment_id):
    payment = get_object_or_404(
        Payment.objects.select_related('booking__show__movie', 'booking__show__screen__theater'),
        payment_id=payment_id, user=request.user
    )
    return render(request, 'payments/success.html', {'payment': payment, 'booking': payment.booking})


@login_required
def payment_failure(request, payment_id):
    payment = get_object_or_404(Payment, payment_id=payment_id, user=request.user)
    return render(request, 'payments/failure.html', {'payment': payment})
