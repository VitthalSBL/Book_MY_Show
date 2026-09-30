from django.urls import path
from . import views

app_name = 'bookings'

urlpatterns = [
    path('hold/', views.hold_seats, name='hold_seats'),
    path('release/', views.release_seats, name='release_seats'),
    path('<str:booking_id>/', views.booking_detail, name='detail'),
    path('<str:booking_id>/cancel/', views.cancel_booking, name='cancel'),
    path('<str:booking_id>/ticket/', views.download_ticket, name='download_ticket'),
]
