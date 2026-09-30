from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Sum, Count, Avg, F, Q
from django.db.models.functions import TruncDate, TruncWeek, TruncMonth, TruncHour
from django.http import HttpResponse
from django.utils import timezone
from datetime import timedelta, datetime
import csv

from bookings.models import Booking, SeatReservation
from payments.models import Payment
from movies.models import Movie
from theaters.models import Theater, Show, City
from django.contrib.auth.models import User


@staff_member_required
def admin_dashboard(request):
    # Date filters
    period = request.GET.get('period', 'monthly')
    start_date = request.GET.get('start')
    end_date = request.GET.get('end')

    now = timezone.now()
    if start_date and end_date:
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d').date()
            end = datetime.strptime(end_date, '%Y-%m-%d').date()
        except ValueError:
            start = now.date() - timedelta(days=30)
            end = now.date()
    else:
        if period == 'daily':
            start = now.date()
            end = now.date()
        elif period == 'weekly':
            start = now.date() - timedelta(days=7)
            end = now.date()
        elif period == 'yearly':
            start = now.date() - timedelta(days=365)
            end = now.date()
        else:  # monthly
            start = now.date() - timedelta(days=30)
            end = now.date()

    confirmed = Booking.objects.filter(status='confirmed', booked_at__date__gte=start, booked_at__date__lte=end)

    # Revenue
    revenue_total = confirmed.aggregate(total=Sum('total_amount'))['total'] or 0
    revenue_by_day = (
        confirmed.annotate(day=TruncDate('booked_at'))
        .values('day')
        .annotate(revenue=Sum('total_amount'), bookings=Count('id'))
        .order_by('day')
    )

    # Occupancy
    total_seats_booked = SeatReservation.objects.filter(
        status='booked', booking__booked_at__date__gte=start, booking__booked_at__date__lte=end
    ).count()
    total_possible = Show.objects.filter(
        show_date__gte=start, show_date__lte=end
    ).aggregate(
        total=Sum(F('screen__total_rows') * F('screen__seats_per_row'))
    )['total'] or 1
    occupancy_pct = round((total_seats_booked / total_possible) * 100, 1) if total_possible else 0

    # Top movies
    top_movies = (
        confirmed.values('show__movie__title')
        .annotate(bookings=Count('id'), revenue=Sum('total_amount'))
        .order_by('-revenue')[:10]
    )

    # Top theaters
    top_theaters = (
        confirmed.values('show__screen__theater__name', 'show__screen__theater__city__name')
        .annotate(bookings=Count('id'), revenue=Sum('total_amount'))
        .order_by('-revenue')[:10]
    )

    # Peak hours
    peak_hours = (
        confirmed.annotate(hour=TruncHour('booked_at'))
        .values('hour')
        .annotate(count=Count('id'))
        .order_by('-count')[:10]
    )

    # Cancellations & refunds
    cancelled = Booking.objects.filter(
        status__in=['cancelled', 'refunded'], booked_at__date__gte=start, booked_at__date__lte=end
    ).count()
    refunded_amount = Payment.objects.filter(
        status='refunded', created_at__date__gte=start, created_at__date__lte=end
    ).aggregate(total=Sum('amount'))['total'] or 0

    # User growth
    new_users = User.objects.filter(date_joined__date__gte=start, date_joined__date__lte=end).count()
    total_users = User.objects.count()
    total_bookings = Booking.objects.filter(status='confirmed').count()
    total_revenue_all = Booking.objects.filter(status='confirmed').aggregate(
        t=Sum('total_amount')
    )['t'] or 0

    return render(request, 'dashboard/index.html', {
        'period': period,
        'start': start,
        'end': end,
        'revenue_total': revenue_total,
        'revenue_by_day': list(revenue_by_day),
        'occupancy_pct': occupancy_pct,
        'total_seats_booked': total_seats_booked,
        'top_movies': top_movies,
        'top_theaters': top_theaters,
        'peak_hours': peak_hours,
        'cancelled': cancelled,
        'refunded_amount': refunded_amount,
        'new_users': new_users,
        'total_users': total_users,
        'total_bookings': total_bookings,
        'total_revenue_all': total_revenue_all,
        'confirmed_count': confirmed.count(),
    })


@staff_member_required
def export_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="bookings_export.csv"'
    writer = csv.writer(response)
    writer.writerow([
        'Booking ID', 'User', 'Movie', 'Theater', 'Show Date', 'Show Time',
        'Seats', 'Amount', 'Status', 'Booked At'
    ])
    bookings = Booking.objects.select_related(
        'user', 'show__movie', 'show__screen__theater'
    ).prefetch_related('seat_reservations__seat').order_by('-booked_at')[:5000]
    for b in bookings:
        seats = ', '.join(r.seat.seat_label for r in b.seat_reservations.all())
        writer.writerow([
            b.booking_id, b.user.username, b.show.movie.title,
            b.show.screen.theater.name, b.show.show_date, b.show.show_time,
            seats, b.total_amount, b.status, b.booked_at.isoformat()
        ])
    return response
