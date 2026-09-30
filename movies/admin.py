from django.contrib import admin
from .models import Genre, Language, Cast, Movie, MovieCast, MoviePoster, Review


class MovieCastInline(admin.TabularInline):
    model = MovieCast
    extra = 1


class MoviePosterInline(admin.TabularInline):
    model = MoviePoster
    extra = 1


@admin.register(Movie)
class MovieAdmin(admin.ModelAdmin):
    list_display = ['title', 'status', 'certification', 'release_date', 'average_rating', 'total_ratings', 'is_trending']
    list_filter = ['status', 'certification', 'is_trending', 'genres', 'languages']
    search_fields = ['title', 'description']
    prepopulated_fields = {'slug': ('title',)}
    filter_horizontal = ['genres', 'languages']
    inlines = [MovieCastInline, MoviePosterInline]
    readonly_fields = ['average_rating', 'total_ratings']


@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Language)
class LanguageAdmin(admin.ModelAdmin):
    list_display = ['name', 'code']


@admin.register(Cast)
class CastAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['movie', 'user', 'rating', 'is_verified', 'is_approved', 'is_reported', 'created_at']
    list_filter = ['is_verified', 'is_approved', 'is_reported', 'rating']
    search_fields = ['movie__title', 'user__username', 'content']
    actions = ['approve_reviews', 'reject_reviews']

    def approve_reviews(self, request, queryset):
        queryset.update(is_approved=True)
    approve_reviews.short_description = 'Approve selected reviews'

    def reject_reviews(self, request, queryset):
        queryset.update(is_approved=False)
    reject_reviews.short_description = 'Reject selected reviews'
