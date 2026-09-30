from django.urls import path
from . import views

app_name = 'theaters'

urlpatterns = [
    path('city/<slug:city_slug>/', views.theaters_by_city, name='by_city'),
    path('<slug:slug>/', views.theater_detail, name='detail'),
    path('show/<int:show_id>/seats/', views.seat_selection, name='seat_selection'),
    path('api/seats/<int:show_id>/', views.seat_status_api, name='seat_status_api'),
]
