from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count, Avg, Prefetch
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from .models import Movie, Genre, Language, Review
from bookings.models import Booking


def home(request):
    now_showing = Movie.objects.filter(status='now_showing').prefetch_related(
        'genres', 'languages'
    ).order_by('-is_trending', '-average_rating')[:12]
    upcoming = Movie.objects.filter(status='upcoming').prefetch_related(
        'genres', 'languages'
    ).order_by('release_date')[:8]
    trending = Movie.objects.filter(is_trending=True, status='now_showing').prefetch_related(
        'genres'
    )[:6]
    top_rated = Movie.objects.filter(status='now_showing', total_ratings__gte=1).order_by(
        '-average_rating'
    )[:6]
    return render(request, 'movies/home.html', {
        'now_showing': now_showing,
        'upcoming': upcoming,
        'trending': trending,
        'top_rated': top_rated,
    })


def movie_list(request):
    qs = Movie.objects.filter(status__in=['now_showing', 'upcoming']).prefetch_related(
        'genres', 'languages'
    ).select_related()

    genre = request.GET.get('genre')
    language = request.GET.get('language')
    status = request.GET.get('status')
    rating_min = request.GET.get('rating')
    sort = request.GET.get('sort', '-release_date')
    q = request.GET.get('q', '').strip()

    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(description__icontains=q) | Q(cast__name__icontains=q)).distinct()
    if genre:
        qs = qs.filter(genres__slug=genre)
    if language:
        qs = qs.filter(languages__code=language)
    if status:
        qs = qs.filter(status=status)
    if rating_min:
        try:
            qs = qs.filter(average_rating__gte=float(rating_min))
        except ValueError:
            pass

    allowed_sorts = ['-release_date', 'release_date', '-average_rating', 'title', '-title']
    if sort in allowed_sorts:
        qs = qs.order_by(sort)

    paginator = Paginator(qs, 12)
    page = request.GET.get('page', 1)
    movies = paginator.get_page(page)

    return render(request, 'movies/list.html', {
        'movies': movies,
        'genres': Genre.objects.all(),
        'languages': Language.objects.all(),
        'current_filters': request.GET,
    })


def movie_detail(request, slug):
    movie = get_object_or_404(
        Movie.objects.prefetch_related(
            'genres', 'languages', 'posters', 'moviecast_set__cast',
            Prefetch('reviews', queryset=Review.objects.filter(is_approved=True).select_related('user').order_by('-is_verified', '-created_at')),
        ),
        slug=slug
    )
    # Similar movies by genre
    similar = Movie.objects.filter(
        genres__in=movie.genres.all(), status='now_showing'
    ).exclude(pk=movie.pk).distinct().prefetch_related('genres')[:6]

    user_review = None
    has_booked = False
    if request.user.is_authenticated:
        user_review = Review.objects.filter(movie=movie, user=request.user).first()
        has_booked = Booking.objects.filter(
            user=request.user, show__movie=movie, status='confirmed'
        ).exists()

    # Shows for this movie (next 7 days)
    from django.utils import timezone
    from datetime import timedelta
    today = timezone.now().date()
    shows = movie.shows.filter(
        show_date__gte=today,
        show_date__lte=today + timedelta(days=7),
        is_active=True
    ).select_related('screen__theater__city', 'language').order_by('show_date', 'show_time')

    # Group shows by city/theater
    shows_by_city = {}
    for show in shows:
        city = show.screen.theater.city
        theater = show.screen.theater
        if city not in shows_by_city:
            shows_by_city[city] = {}
        if theater not in shows_by_city[city]:
            shows_by_city[city][theater] = []
        shows_by_city[city][theater].append(show)

    return render(request, 'movies/detail.html', {
        'movie': movie,
        'similar': similar,
        'user_review': user_review,
        'has_booked': has_booked,
        'shows_by_city': shows_by_city,
    })


@login_required
def add_review(request, slug):
    movie = get_object_or_404(Movie, slug=slug)
    if Review.objects.filter(movie=movie, user=request.user).exists():
        messages.warning(request, 'You already reviewed this movie.')
        return redirect('movies:detail', slug=slug)

    has_booked = Booking.objects.filter(
        user=request.user, show__movie=movie, status='confirmed'
    ).exists()

    if request.method == 'POST':
        rating = int(request.POST.get('rating', 0))
        title = request.POST.get('title', '')[:200]
        content = request.POST.get('content', '').strip()
        if 1 <= rating <= 5 and content:
            Review.objects.create(
                movie=movie,
                user=request.user,
                rating=rating,
                title=title,
                content=content,
                is_verified=has_booked,
            )
            messages.success(request, 'Review submitted successfully!')
            return redirect('movies:detail', slug=slug)
        messages.error(request, 'Please provide valid rating and content.')
    return render(request, 'movies/add_review.html', {
        'movie': movie,
        'has_booked': has_booked,
    })


@login_required
def edit_review(request, pk):
    review = get_object_or_404(Review, pk=pk, user=request.user)
    if request.method == 'POST':
        rating = int(request.POST.get('rating', 0))
        title = request.POST.get('title', '')[:200]
        content = request.POST.get('content', '').strip()
        if 1 <= rating <= 5 and content:
            review.rating = rating
            review.title = title
            review.content = content
            review.save()
            messages.success(request, 'Review updated.')
            return redirect('movies:detail', slug=review.movie.slug)
    return render(request, 'movies/add_review.html', {
        'movie': review.movie,
        'review': review,
        'has_booked': review.is_verified,
    })


@login_required
def report_review(request, pk):
    review = get_object_or_404(Review, pk=pk)
    if request.method == 'POST':
        review.report_count += 1
        if review.report_count >= 3:
            review.is_reported = True
            review.is_approved = False
        review.save(update_fields=['report_count', 'is_reported', 'is_approved'])
        messages.info(request, 'Review reported. Thank you.')
    return redirect('movies:detail', slug=review.movie.slug)


def search(request):
    return movie_list(request)


@require_GET
def search_count_api(request):
    """Live result count for filters"""
    qs = Movie.objects.filter(status__in=['now_showing', 'upcoming'])
    genre = request.GET.get('genre')
    language = request.GET.get('language')
    q = request.GET.get('q', '').strip()
    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(description__icontains=q))
    if genre:
        qs = qs.filter(genres__slug=genre)
    if language:
        qs = qs.filter(languages__code=language)
    return JsonResponse({'count': qs.distinct().count()})
