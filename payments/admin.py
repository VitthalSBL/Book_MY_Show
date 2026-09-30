from django.contrib import admin
from .models import Payment, TransactionHistory


class TransactionHistoryInline(admin.TabularInline):
    model = TransactionHistory
    extra = 0
    readonly_fields = ['event', 'amount', 'details', 'created_at']


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['payment_id', 'user', 'amount', 'status', 'razorpay_order_id', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['payment_id', 'razorpay_order_id', 'razorpay_payment_id', 'user__username']
    readonly_fields = ['payment_id', 'idempotency_key', 'created_at']
    inlines = [TransactionHistoryInline]


@admin.register(TransactionHistory)
class TransactionHistoryAdmin(admin.ModelAdmin):
    list_display = ['payment', 'event', 'amount', 'created_at']
    list_filter = ['event']
