from django.contrib import admin
from .models import City, Theater, Screen, Seat, Show


class ScreenInline(admin.TabularInline):
    model = Screen
    extra = 1


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ['name', 'state', 'is_active']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Theater)
class TheaterAdmin(admin.ModelAdmin):
    list_display = ['name', 'city', 'is_active']
    list_filter = ['city', 'is_active']
    search_fields = ['name', 'address']
    prepopulated_fields = {'slug': ('name',)}
    inlines = [ScreenInline]


@admin.register(Screen)
class ScreenAdmin(admin.ModelAdmin):
    list_display = ['name', 'theater', 'total_rows', 'seats_per_row', 'is_active']
    list_filter = ['theater__city', 'is_active']


@admin.register(Seat)
class SeatAdmin(admin.ModelAdmin):
    list_display = ['seat_label', 'screen', 'seat_type', 'price_multiplier']
    list_filter = ['screen__theater', 'seat_type']
    search_fields = ['row', 'number']


@admin.register(Show)
class ShowAdmin(admin.ModelAdmin):
    list_display = ['movie', 'screen', 'show_date', 'show_time', 'base_price', 'language', 'is_active']
    list_filter = ['show_date', 'is_active', 'movie', 'screen__theater']
    search_fields = ['movie__title', 'screen__theater__name']
    date_hierarchy = 'show_date'
