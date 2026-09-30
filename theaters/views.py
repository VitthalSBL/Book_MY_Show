from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Prefetch
from .models import City, Theater, Show, Seat, Screen
from bookings.models import SeatReservation


def theaters_by_city(request, city_slug):
    city = get_object_or_404(City, slug=city_slug, is_active=True)
    theaters = Theater.objects.filter(city=city, is_active=True).prefetch_related('screens')
    return render(request, 'theaters/by_city.html', {'city': city, 'theaters': theaters})


def theater_detail(request, slug):
    theater = get_object_or_404(Theater.objects.select_related('city'), slug=slug, is_active=True)
    today = timezone.now().date()
    shows = Show.objects.filter(
        screen__theater=theater, show_date__gte=today, is_active=True
    ).select_related('movie', 'language', 'screen').order_by('show_date', 'show_time')
    return render(request, 'theaters/detail.html', {'theater': theater, 'shows': shows})


def seat_selection(request, show_id):
    show = get_object_or_404(
        Show.objects.select_related(
            'movie', 'screen__theater__city', 'language'
        ),
        pk=show_id, is_active=True
    )
    # Ensure seat reservations exist for this show
    seats = Seat.objects.filter(screen=show.screen).order_by('row', 'number')
    existing = set(
        SeatReservation.objects.filter(show=show).values_list('seat_id', flat=True)
    )
    to_create = []
    for seat in seats:
        if seat.id not in existing:
            to_create.append(SeatReservation(
                show=show,
                seat=seat,
                status='available',
                price=show.base_price * seat.price_multiplier
            ))
    if to_create:
        SeatReservation.objects.bulk_create(to_create, ignore_conflicts=True)

    # Release expired holds
    now = timezone.now()
    SeatReservation.objects.filter(
        show=show, status='held', held_until__lt=now
    ).update(status='available', held_by=None, held_at=None, held_until=None, booking=None)

    reservations = SeatReservation.objects.filter(show=show).select_related('seat')
    seat_map = {}
    for r in reservations:
        row = r.seat.row
        if row not in seat_map:
            seat_map[row] = []
        seat_map[row].append({
            'id': r.seat.id,
            'label': r.seat.seat_label,
            'number': r.seat.number,
            'type': r.seat.seat_type,
            'status': r.status,
            'price': float(r.price),
            'held_by_me': r.held_by_id == request.user.id if request.user.is_authenticated else False,
        })
    # Sort seats in each row
    for row in seat_map:
        seat_map[row].sort(key=lambda x: x['number'])

    rows = sorted(seat_map.keys())
    return render(request, 'theaters/seat_selection.html', {
        'show': show,
        'seat_map': seat_map,
        'rows': rows,
    })


def seat_status_api(request, show_id):
    """Polling endpoint for live seat availability"""
    now = timezone.now()
    # Auto-release expired
    SeatReservation.objects.filter(
        show_id=show_id, status='held', held_until__lt=now
    ).update(status='available', held_by=None, held_at=None, held_until=None, booking=None)

    reservations = SeatReservation.objects.filter(show_id=show_id).values(
        'seat_id', 'status', 'held_by_id'
    )
    user_id = request.user.id if request.user.is_authenticated else None
    data = {}
    for r in reservations:
        status = r['status']
        if status == 'held' and r['held_by_id'] == user_id:
            status = 'held_by_me'
        data[r['seat_id']] = status
    return JsonResponse({'seats': data, 'timestamp': now.isoformat()})
