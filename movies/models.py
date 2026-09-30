from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models import Avg, Count
from django.urls import reverse
from django.utils.text import slugify


class Genre(models.Model):
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=60, unique=True, blank=True)

    class Meta:
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Language(models.Model):
    name = models.CharField(max_length=50, unique=True)
    code = models.CharField(max_length=10, unique=True)  # hi, en, ta, te

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Cast(models.Model):
    name = models.CharField(max_length=100)
    photo = models.ImageField(upload_to='cast/', blank=True, null=True)
    bio = models.TextField(blank=True)

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'Cast'

    def __str__(self):
        return self.name


class Movie(models.Model):
    CERTIFICATION_CHOICES = [
        ('U', 'U - Universal'),
        ('UA', 'UA - Parental Guidance'),
        ('A', 'A - Adults Only'),
        ('S', 'S - Restricted'),
    ]
    STATUS_CHOICES = [
        ('upcoming', 'Upcoming'),
        ('now_showing', 'Now Showing'),
        ('archived', 'Archived'),
    ]

    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    description = models.TextField()
    duration_minutes = models.PositiveIntegerField(help_text='Duration in minutes')
    release_date = models.DateField()
    certification = models.CharField(max_length=5, choices=CERTIFICATION_CHOICES, default='UA')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='upcoming')
    trailer_url = models.URLField(blank=True, help_text='YouTube embed URL or watch URL')
    poster = models.ImageField(upload_to='posters/', blank=True, null=True)
    poster_url = models.URLField(blank=True, help_text='External poster image URL (used if no uploaded poster)')
    banner = models.ImageField(upload_to='banners/', blank=True, null=True)
    genres = models.ManyToManyField(Genre, related_name='movies')
    languages = models.ManyToManyField(Language, related_name='movies')
    cast = models.ManyToManyField(Cast, through='MovieCast', related_name='movies')
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)
    total_ratings = models.PositiveIntegerField(default=0)
    is_trending = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-release_date']
        indexes = [
            models.Index(fields=['status', 'release_date']),
            models.Index(fields=['is_trending']),
            models.Index(fields=['average_rating']),
            models.Index(fields=['slug']),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title)
            slug = base
            counter = 1
            while Movie.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f'{base}-{counter}'
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('movies:detail', kwargs={'slug': self.slug})

    def update_rating(self):
        result = self.reviews.filter(is_approved=True).aggregate(
            avg=Avg('rating'), count=Count('id')
        )
        self.average_rating = result['avg'] or 0
        self.total_ratings = result['count'] or 0
        self.save(update_fields=['average_rating', 'total_ratings'])

    @property
    def duration_display(self):
        hours = self.duration_minutes // 60
        mins = self.duration_minutes % 60
        return f'{hours}h {mins}m' if hours else f'{mins}m'

    @property
    def trailer_embed_url(self):
        if not self.trailer_url:
            return ''
        url = self.trailer_url
        if 'watch?v=' in url:
            video_id = url.split('watch?v=')[-1].split('&')[0]
            return f'https://www.youtube.com/embed/{video_id}'
        if 'youtu.be/' in url:
            video_id = url.split('youtu.be/')[-1].split('?')[0]
            return f'https://www.youtube.com/embed/{video_id}'
        return url


    @property
    def poster_display(self):
        """Local uploaded poster first (offline-safe), else external URL."""
        if self.poster:
            try:
                return self.poster.url
            except Exception:
                pass
        return self.poster_url or ''


class MovieCast(models.Model):
    ROLE_CHOICES = [
        ('actor', 'Actor'),
        ('actress', 'Actress'),
        ('director', 'Director'),
        ('producer', 'Producer'),
        ('writer', 'Writer'),
    ]
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE)
    cast = models.ForeignKey(Cast, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='actor')
    character_name = models.CharField(max_length=100, blank=True)

    class Meta:
        unique_together = ('movie', 'cast', 'role')

    def __str__(self):
        return f'{self.cast.name} as {self.character_name or self.role} in {self.movie.title}'


class MoviePoster(models.Model):
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name='posters')
    image = models.ImageField(upload_to='posters/gallery/')
    caption = models.CharField(max_length=200, blank=True)
    is_primary = models.BooleanField(default=False)

    def __str__(self):
        return f'Poster for {self.movie.title}'


class Review(models.Model):
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews')
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    title = models.CharField(max_length=200, blank=True)
    content = models.TextField()
    is_verified = models.BooleanField(default=False, help_text='User has booked this movie')
    is_approved = models.BooleanField(default=True)
    is_reported = models.BooleanField(default=False)
    report_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('movie', 'user')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['movie', 'is_approved']),
            models.Index(fields=['user']),
        ]

    def __str__(self):
        return f'{self.user.username} - {self.movie.title} ({self.rating}★)'

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.movie.update_rating()
