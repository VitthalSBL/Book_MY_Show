from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.contrib.auth.models import User
from .models import Profile
from bookings.models import Booking
from payments.models import Payment, TransactionHistory


def register(request):
    if request.user.is_authenticated:
        return redirect('movies:home')
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            email = request.POST.get('email', '')
            if email:
                user.email = email
                user.save(update_fields=['email'])
            login(request, user)
            messages.success(request, 'Account created successfully!')
            return redirect('movies:home')
    else:
        form = UserCreationForm()
    return render(request, 'accounts/register.html', {'form': form})


@login_required
def profile(request):
    profile_obj, _ = Profile.objects.get_or_create(user=request.user)
    return render(request, 'accounts/profile.html', {'profile': profile_obj})


@login_required
def edit_profile(request):
    profile_obj, _ = Profile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        request.user.first_name = request.POST.get('first_name', '')[:30]
        request.user.last_name = request.POST.get('last_name', '')[:30]
        request.user.email = request.POST.get('email', '')[:100]
        request.user.save()
        profile_obj.phone = request.POST.get('phone', '')[:15]
        profile_obj.save()
        messages.success(request, 'Profile updated.')
        return redirect('accounts:profile')
    return render(request, 'accounts/edit_profile.html', {'profile': profile_obj})


@login_required
def my_bookings(request):
    bookings = Booking.objects.filter(user=request.user).select_related(
        'show__movie', 'show__screen__theater', 'show__language'
    ).prefetch_related('seat_reservations__seat').order_by('-booked_at')
    status_filter = request.GET.get('status')
    if status_filter:
        bookings = bookings.filter(status=status_filter)
    return render(request, 'accounts/my_bookings.html', {'bookings': bookings})


@login_required
def transaction_history(request):
    payments = Payment.objects.filter(user=request.user).select_related(
        'booking__show__movie'
    ).order_by('-created_at')
    return render(request, 'accounts/transactions.html', {'payments': payments})
