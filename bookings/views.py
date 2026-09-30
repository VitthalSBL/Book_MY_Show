from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.http import JsonResponse, HttpResponse, FileResponse
from django.utils import timezone
from django.conf import settings
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
import json

from .models import Booking, SeatReservation
from theaters.models import Show, Seat


@login_required
@require_POST
def hold_seats(request):
    """
    Atomically hold seats for 2 minutes using select_for_update.
    Prevents double booking under concurrent load.
    """
    try:
        data = json.loads(request.body)
        show_id = data.get('show_id')
        seat_ids = data.get('seat_ids', [])
    except (json.JSONDecodeError, TypeError):
        return JsonResponse({'success': False, 'error': 'Invalid request'}, status=400)

    if not show_id or not seat_ids or len(seat_ids) > 10:
        return JsonResponse({'success': False, 'error': 'Invalid seats (max 10)'}, status=400)

    show = get_object_or_404(Show, pk=show_id, is_active=True)

    try:
        with transaction.atomic():
            # Lock the rows - critical for concurrency
            reservations = list(
                SeatReservation.objects.select_for_update()
                .filter(show=show, seat_id__in=seat_ids)
            )

            if len(reservations) != len(seat_ids):
                # Create missing reservations if seats exist
                existing_seat_ids = {r.seat_id for r in reservations}
                missing = set(seat_ids) - existing_seat_ids
                seats = Seat.objects.filter(pk__in=missing, screen=show.screen)
                for seat in seats:
                    price = show.base_price * seat.price_multiplier
                    r = SeatReservation.objects.create(
                        show=show, seat=seat, status='available', price=price
                    )
                    reservations.append(r)

            # Release any expired holds first
            now = timezone.now()
            for r in reservations:
                if r.status == 'held' and r.held_until and r.held_until < now:
                    r.status = 'available'
                    r.held_by = None
                    r.held_at = None
                    r.held_until = None
                    r.booking = None

            # Check availability
            # Booked seats are always unavailable.
            # Held seats are unavailable unless held by the same user (re-hold).
            unavailable = [
                r for r in reservations
                if r.status == 'booked'
                or (r.status == 'held' and r.held_by_id != request.user.id)
            ]
            if unavailable:
                labels = [str(r.seat) for r in unavailable]
                return JsonResponse({
                    'success': False,
                    'error': f'Seats already taken: {", ".join(labels)}'
                }, status=409)

            # Create booking
            total = sum(r.price for r in reservations)
            booking = Booking.objects.create(
                user=request.user,
                show=show,
                status='pending',
                total_amount=total,
                seats_count=len(reservations),
            )

            hold_until = now + timezone.timedelta(seconds=settings.SEAT_HOLD_TIMEOUT)
            for r in reservations:
                r.status = 'held'
                r.held_by = request.user
                r.held_at = now
                r.held_until = hold_until
                r.booking = booking
                r.save(update_fields=['status', 'held_by', 'held_at', 'held_until', 'booking'])

            return JsonResponse({
                'success': True,
                'booking_id': booking.booking_id,
                'expires_at': hold_until.isoformat(),
                'total_amount': str(total),
                'seats': [r.seat.seat_label for r in reservations],
                'redirect_url': f'/payments/create/{booking.booking_id}/',
            })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_POST
def release_seats(request):
    """Release held seats (user cancelled or navigated away)"""
    try:
        data = json.loads(request.body)
        booking_id = data.get('booking_id')
    except (json.JSONDecodeError, TypeError):
        return JsonResponse({'success': False}, status=400)

    booking = get_object_or_404(Booking, booking_id=booking_id, user=request.user)
    if booking.status != 'pending':
        return JsonResponse({'success': False, 'error': 'Cannot release'}, status=400)

    with transaction.atomic():
        SeatReservation.objects.filter(booking=booking, status='held').update(
            status='available', held_by=None, held_at=None, held_until=None, booking=None
        )
        booking.status = 'expired'
        booking.save(update_fields=['status'])

    return JsonResponse({'success': True})


@login_required
def booking_detail(request, booking_id):
    booking = get_object_or_404(
        Booking.objects.select_related(
            'show__movie', 'show__screen__theater__city', 'show__language', 'user'
        ).prefetch_related('seat_reservations__seat'),
        booking_id=booking_id,
        user=request.user
    )
    return render(request, 'bookings/detail.html', {'booking': booking})


@login_required
def cancel_booking(request, booking_id):
    booking = get_object_or_404(Booking, booking_id=booking_id, user=request.user)
    if booking.status == 'confirmed':
        # Only allow cancel before show time ideally - simplified
        booking.cancel()
        messages.success(request, 'Booking cancelled. Refund will be processed if applicable.')
    else:
        messages.warning(request, 'Only confirmed bookings can be cancelled.')
    return redirect('accounts:my_bookings')


@login_required
def download_ticket(request, booking_id):
    booking = get_object_or_404(Booking, booking_id=booking_id, user=request.user, status='confirmed')
    if booking.pdf_ticket:
        return FileResponse(booking.pdf_ticket.open('rb'), as_attachment=True, filename=f'ticket_{booking.booking_id}.pdf')
    # Generate on the fly if missing
    from .services import generate_ticket_pdf
    pdf_path = generate_ticket_pdf(booking)
    return FileResponse(open(pdf_path, 'rb'), as_attachment=True, filename=f'ticket_{booking.booking_id}.pdf')
