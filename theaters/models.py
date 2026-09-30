from django.db import models
from django.utils.text import slugify


class City(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=110, unique=True, blank=True)
    state = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = 'Cities'
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Theater(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    city = models.ForeignKey(City, on_delete=models.CASCADE, related_name='theaters')
    address = models.TextField()
    pincode = models.CharField(max_length=10, blank=True)
    phone = models.CharField(max_length=15, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['city', 'is_active']),
            models.Index(fields=['slug']),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(f'{self.name}-{self.city.name}')
            slug = base
            counter = 1
            while Theater.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f'{base}-{counter}'
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.name}, {self.city.name}'


class Screen(models.Model):
    theater = models.ForeignKey(Theater, on_delete=models.CASCADE, related_name='screens')
    name = models.CharField(max_length=50)  # Screen 1, Audi 2
    total_rows = models.PositiveIntegerField(default=10)
    seats_per_row = models.PositiveIntegerField(default=12)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('theater', 'name')
        ordering = ['theater', 'name']

    def __str__(self):
        return f'{self.theater.name} - {self.name}'

    @property
    def total_seats(self):
        return self.total_rows * self.seats_per_row


class Seat(models.Model):
    SEAT_TYPE_CHOICES = [
        ('regular', 'Regular'),
        ('premium', 'Premium'),
        ('recliner', 'Recliner'),
        ('vip', 'VIP'),
    ]
    screen = models.ForeignKey(Screen, on_delete=models.CASCADE, related_name='seats')
    row = models.CharField(max_length=5)  # A, B, C...
    number = models.PositiveIntegerField()
    seat_type = models.CharField(max_length=20, choices=SEAT_TYPE_CHOICES, default='regular')
    price_multiplier = models.DecimalField(max_digits=3, decimal_places=2, default=1.00)

    class Meta:
        unique_together = ('screen', 'row', 'number')
        ordering = ['row', 'number']
        indexes = [
            models.Index(fields=['screen', 'row', 'number']),
        ]

    def __str__(self):
        return f'{self.row}{self.number}'

    @property
    def seat_label(self):
        return f'{self.row}{self.number}'


class Show(models.Model):
    movie = models.ForeignKey('movies.Movie', on_delete=models.CASCADE, related_name='shows')
    screen = models.ForeignKey(Screen, on_delete=models.CASCADE, related_name='shows')
    language = models.ForeignKey('movies.Language', on_delete=models.SET_NULL, null=True)
    show_date = models.DateField()
    show_time = models.TimeField()
    base_price = models.DecimalField(max_digits=8, decimal_places=2)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['show_date', 'show_time']
        indexes = [
            models.Index(fields=['movie', 'show_date', 'is_active']),
            models.Index(fields=['screen', 'show_date', 'show_time']),
            models.Index(fields=['show_date', 'show_time']),
        ]
        unique_together = ('screen', 'show_date', 'show_time')

    def __str__(self):
        return f'{self.movie.title} @ {self.screen} - {self.show_date} {self.show_time}'

    @property
    def datetime_display(self):
        return f'{self.show_date.strftime("%d %b %Y")} | {self.show_time.strftime("%I:%M %p")}'
