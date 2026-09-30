from django.contrib import admin
from .models import Booking, SeatReservation


class SeatReservationInline(admin.TabularInline):
    model = SeatReservation
    extra = 0
    readonly_fields = ['seat', 'status', 'price', 'held_by', 'held_at', 'held_until']


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ['booking_id', 'user', 'show', 'status', 'total_amount', 'seats_count', 'booked_at']
    list_filter = ['status', 'booked_at']
    search_fields = ['booking_id', 'user__username', 'user__email']
    readonly_fields = ['booking_id', 'booked_at']
    inlines = [SeatReservationInline]
    date_hierarchy = 'booked_at'


@admin.register(SeatReservation)
class SeatReservationAdmin(admin.ModelAdmin):
    list_display = ['seat', 'show', 'status', 'booking', 'held_by', 'held_until', 'price']
    list_filter = ['status', 'show__show_date']
    search_fields = ['seat__row', 'booking__booking_id']
