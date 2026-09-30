from django.urls import path
from . import views

app_name = 'payments'

urlpatterns = [
    path('create/<str:booking_id>/', views.create_payment, name='create'),
    path('callback/', views.payment_callback, name='callback'),
    path('webhook/', views.razorpay_webhook, name='webhook'),
    path('success/<str:payment_id>/', views.payment_success, name='success'),
    path('failure/<str:payment_id>/', views.payment_failure, name='failure'),
]
