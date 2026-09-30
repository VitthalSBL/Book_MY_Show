"""
Seed script for BookMyShow Clone
Usage: python seed_data.py
"""
import os
import django
import random
from datetime import date, time, timedelta
from decimal import Decimal
from io import BytesIO

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bookmyshow.settings')
django.setup()

from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from movies.models import Genre, Language, Cast, Movie, MovieCast, Review
from theaters.models import City, Theater, Screen, Seat, Show
from PIL import Image, ImageDraw, ImageFont

print('=== Seeding BookMyShow Clone ===')

# --- Genres ---
genres = {}
for g in ['Action', 'Comedy', 'Drama', 'Horror', 'Romance', 'Sci-Fi', 'Thriller', 'Adventure', 'Animation', 'Crime']:
    obj, _ = Genre.objects.get_or_create(name=g)
    genres[g] = obj

# --- Languages ---
languages = {}
for name, code in [('Hindi', 'hi'), ('English', 'en'), ('Tamil', 'ta'), ('Telugu', 'te'), ('Kannada', 'kn'), ('Malayalam', 'ml')]:
    obj, _ = Language.objects.get_or_create(name=name, defaults={'code': code})
    languages[name] = obj

# --- Cast ---
casts = {}
for name in ['Shah Rukh Khan', 'Deepika Padukone', 'Aamir Khan', 'Alia Bhatt', 'Ranbir Kapoor',
             'Priyanka Chopra', 'Hrithik Roshan', 'Katrina Kaif', 'Salman Khan', 'Anushka Sharma',
             'Rajinikanth', 'Vijay', 'Allu Arjun', 'Prabhas', 'Rashmika Mandanna']:
    obj, _ = Cast.objects.get_or_create(name=name)
    casts[name] = obj

# --- Cities ---
cities = {}
for name, state in [('Mumbai', 'Maharashtra'), ('Delhi', 'Delhi'), ('Bangalore', 'Karnataka'),
                    ('Hyderabad', 'Telangana'), ('Chennai', 'Tamil Nadu'), ('Pune', 'Maharashtra'),
                    ('Kolkata', 'West Bengal'), ('Ahmedabad', 'Gujarat')]:
    obj, _ = City.objects.get_or_create(name=name, defaults={'state': state})
    cities[name] = obj

# --- Theaters + Screens + Seats ---
theater_names = {
    'Mumbai': ['PVR Phoenix', 'INOX R City'],
    'Delhi': ['PVR Select Citywalk', 'INOX Nehru Place'],
    'Bangalore': ['PVR Orion', 'INOX Garuda'],
    'Hyderabad': ['PVR Inorbit', 'INOX GVK One'],
    'Chennai': ['PVR Grand Mall'],
    'Pune': ['PVR Pavilion'],
    'Kolkata': ['PVR Mani Square'],
    'Ahmedabad': ['PVR Acropolis'],
}
ROWS = list('ABCDEFGHIJ')
for city_name, tnames in theater_names.items():
    city = cities[city_name]
    for tname in tnames:
        theater, _ = Theater.objects.get_or_create(
            name=tname, city=city, defaults={'address': f'{tname}, {city_name}'}
        )
        for snum in range(1, 3):
            screen, _ = Screen.objects.get_or_create(
                theater=theater, name=f'Screen {snum}',
                defaults={'total_rows': 10, 'seats_per_row': 12}
            )
            if not screen.seats.exists():
                seats = []
                for ri, row in enumerate(ROWS):
                    stype = 'recliner' if ri >= 8 else ('premium' if ri >= 5 else 'regular')
                    mult = Decimal('1.5') if stype == 'recliner' else (Decimal('1.25') if stype == 'premium' else Decimal('1.0'))
                    for num in range(1, 13):
                        seats.append(Seat(screen=screen, row=row, number=num, seat_type=stype, price_multiplier=mult))
                Seat.objects.bulk_create(seats, ignore_conflicts=True)

print(f'Theaters: {Theater.objects.count()} | Seats: {Seat.objects.count()}')



# Real Wikipedia / Wikimedia fair-use film posters (educational use)
POSTER_FILES = {
    'Pathaan': 'Pathaan_film_poster.jpg',
    'Jawan': 'Jawan_film_poster.jpg',
    'Animal': 'Animal_(2023_film)_poster.jpg',
    'Salaar': 'Salaar_Part_1_–_Ceasefire.jpg',
    'Leo': 'Leo_(2023_Indian_film).jpg',
    '12th Fail': '12th_Fail_poster.jpeg',
    'Kalki 2898 AD': 'Kalki_2898_AD.jpg',
    'Stree 2': 'Stree_2.jpg',
    'Pushpa 2': 'Pushpa_2-_The_Rule.jpg',
    'Fighter': 'Fighter_film_poster.jpg',
}

def download_real_poster(title):
    """Download real movie poster from Wikipedia Special:FilePath."""
    import urllib.request
    import urllib.parse
    fname = POSTER_FILES.get(title)
    if not fname:
        return None
    url = 'https://en.wikipedia.org/wiki/Special:FilePath/' + urllib.parse.quote(fname)
    headers = {'User-Agent': 'BookMyShowClone/1.0 (Educational Django Project)'}
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = resp.read()
            if len(data) < 5000:
                return None
            # determine extension
            ext = '.jpg'
            if 'jpeg' in fname.lower() or fname.lower().endswith('.jpeg'):
                ext = '.jpeg'
            elif fname.lower().endswith('.png'):
                ext = '.png'
            safe = title.replace(' ', '_')[:40] + ext
            return ContentFile(data, name=safe)
    except Exception as e:
        print(f'  Download failed for {title}: {e}')
        return None


def make_poster_image(title, color_rgb, size=(400, 600)):
    """Generate a cinematic-looking poster with gradient and large title."""
    from PIL import ImageFilter
    w, h = size
    # Gradient background
    img = Image.new('RGB', size, color_rgb)
    draw = ImageDraw.Draw(img)
    r, g, b = color_rgb
    for y in range(h):
        factor = y / h
        nr = int(r * (1 - factor * 0.7))
        ng = int(g * (1 - factor * 0.7))
        nb = int(b * (1 - factor * 0.7))
        draw.line([(0, y), (w, y)], fill=(nr, ng, nb))
    # Top red bar (BMS style)
    draw.rectangle([0, 0, w, 12], fill=(248, 68, 100))
    # Decorative circle
    draw.ellipse([w//2 - 60, h//3 - 60, w//2 + 60, h//3 + 60], outline=(220, 220, 230), width=3)
    draw.ellipse([w//2 - 40, h//3 - 40, w//2 + 40, h//3 + 40], outline=(180, 180, 200), width=2)
    # Film icon approximation
    draw.rectangle([w//2 - 25, h//3 - 20, w//2 + 25, h//3 + 20], outline=(255, 255, 255), width=2)
    # Bottom dark panel
    draw.rectangle([0, h - 140, w, h], fill=(15, 15, 25))
    # Title - large
    words = title.upper().split()
    lines, line = [], ''
    for word in words:
        test = (line + ' ' + word).strip()
        if len(test) <= 14:
            line = test
        else:
            if line:
                lines.append(line)
            line = word
    if line:
        lines.append(line)
    y = h - 120
    for ln in lines[:3]:
        # Manual approximate centering
        char_w = 14
        tw = len(ln) * char_w
        x = max(16, (w - tw) // 2)
        # shadow
        draw.text((x + 2, y + 2), ln, fill=(0, 0, 0))
        draw.text((x, y), ln, fill=(255, 255, 255))
        y += 28
    # Accent line
    draw.rectangle([w//2 - 30, h - 20, w//2 + 30, h - 16], fill=(248, 68, 100))
    buf = BytesIO()
    img.save(buf, format='JPEG', quality=90)
    buf.seek(0)
    return ContentFile(buf.read(), name=f'{title.replace(" ", "_")[:30]}.jpg')

# Real YouTube trailer IDs (public official trailers)
# poster_url: reliable placeholder images from picsum with seed for consistency
MOVIES = [
    {
        'title': 'Pathaan', 'desc': 'An action thriller featuring a RAW agent on a mission to stop a deadly attack.',
        'dur': 146, 'cert': 'UA', 'status': 'now_showing', 'trending': True,
        'gens': ['Action', 'Thriller'], 'langs': ['Hindi'],
        'cast': ['Shah Rukh Khan', 'Deepika Padukone'],
        'trailer': 'https://www.youtube.com/watch?v=vqu4z34wENw',
        'color': (180, 40, 40),
        'poster_url': 'https://picsum.photos/seed/pathaanmovie/400/600',
    },
    {
        'title': 'Jawan', 'desc': 'A man is driven by a revenge mission carried out by him under the guise of his lookalike.',
        'dur': 169, 'cert': 'UA', 'status': 'now_showing', 'trending': True,
        'gens': ['Action', 'Thriller'], 'langs': ['Hindi'],
        'cast': ['Shah Rukh Khan'],
        'trailer': 'https://www.youtube.com/watch?v=COv52QyctAs',
        'color': (30, 80, 140),
        'poster_url': 'https://picsum.photos/seed/jawanmovie/400/600',
    },
    {
        'title': 'Animal', 'desc': 'A son\'s love for his father turns into obsession that leads to a path of violence.',
        'dur': 201, 'cert': 'A', 'status': 'now_showing', 'trending': True,
        'gens': ['Action', 'Drama'], 'langs': ['Hindi'],
        'cast': ['Ranbir Kapoor'],
        'trailer': 'https://www.youtube.com/watch?v=Dydmpfo58C8',
        'color': (60, 20, 20),
        'poster_url': 'https://picsum.photos/seed/animalmovie/400/600',
    },
    {
        'title': 'Salaar', 'desc': 'A gang leader makes enemies after freeing a village from a violent gang.',
        'dur': 175, 'cert': 'A', 'status': 'now_showing', 'trending': True,
        'gens': ['Action', 'Thriller'], 'langs': ['Telugu', 'Hindi'],
        'cast': ['Prabhas'],
        'trailer': 'https://www.youtube.com/watch?v=4GPvYMKtrtI',
        'color': (100, 30, 60),
        'poster_url': 'https://picsum.photos/seed/salaarmovie/400/600',
    },
    {
        'title': 'Leo', 'desc': 'A mild-mannered cafe owner becomes the target of a notorious drug cartel.',
        'dur': 164, 'cert': 'UA', 'status': 'now_showing', 'trending': True,
        'gens': ['Action', 'Thriller'], 'langs': ['Tamil', 'Hindi'],
        'cast': ['Vijay'],
        'trailer': 'https://www.youtube.com/watch?v=Po3jStA6734',
        'color': (20, 100, 60),
        'poster_url': 'https://picsum.photos/seed/leomovie/400/600',
    },
    {
        'title': '12th Fail', 'desc': 'The real-life story of IPS officer Manoj Kumar Sharma who overcame extreme poverty.',
        'dur': 147, 'cert': 'U', 'status': 'now_showing', 'trending': False,
        'gens': ['Drama'], 'langs': ['Hindi'],
        'cast': [],
        'trailer': 'https://www.youtube.com/watch?v=WeMFo70Vq-0',
        'color': (40, 60, 100),
        'poster_url': 'https://picsum.photos/seed/12thfailmovie/400/600',
    },
    {
        'title': 'Kalki 2898 AD', 'desc': 'A modern-day avatar of Vishnu, a Hindu god, is taken on an entity trying to control the future.',
        'dur': 180, 'cert': 'UA', 'status': 'now_showing', 'trending': True,
        'gens': ['Sci-Fi', 'Action'], 'langs': ['Telugu', 'Hindi'],
        'cast': ['Prabhas', 'Deepika Padukone'],
        'trailer': 'https://www.youtube.com/watch?v=kQDd1AhGIHk',
        'color': (80, 40, 120),
        'poster_url': 'https://picsum.photos/seed/kalkimovie/400/600',
    },
    {
        'title': 'Stree 2', 'desc': 'The town of Chanderi is being haunted again, and only the gang can solve the mystery.',
        'dur': 149, 'cert': 'UA', 'status': 'now_showing', 'trending': True,
        'gens': ['Horror', 'Comedy'], 'langs': ['Hindi'],
        'cast': [],
        'trailer': 'https://www.youtube.com/watch?v=KVnssAuORQ4',
        'color': (20, 20, 40),
        'poster_url': 'https://picsum.photos/seed/stree2movie/400/600',
    },
    {
        'title': 'Pushpa 2', 'desc': 'The rule of Pushpa Raj begins as he rises in the world of red sandalwood smuggling.',
        'dur': 200, 'cert': 'UA', 'status': 'upcoming', 'trending': True,
        'gens': ['Action', 'Drama'], 'langs': ['Telugu', 'Hindi'],
        'cast': ['Allu Arjun', 'Rashmika Mandanna'],
        'trailer': 'https://www.youtube.com/watch?v=1kVK0M9XAHc',
        'color': (140, 80, 20),
        'poster_url': 'https://picsum.photos/seed/pushpa2movie/400/600',
    },
    {
        'title': 'Fighter', 'desc': 'An Indian Air Force pilot and his colleagues face an international crisis.',
        'dur': 166, 'cert': 'UA', 'status': 'now_showing', 'trending': False,
        'gens': ['Action', 'Drama'], 'langs': ['Hindi'],
        'cast': ['Hrithik Roshan', 'Deepika Padukone'],
        'trailer': 'https://www.youtube.com/watch?v=6amg_w_Zb-E',
        'color': (20, 50, 90),
        'poster_url': 'https://picsum.photos/seed/fightermovie/400/600',
    },
]

today = date.today()
movies = []
for md in MOVIES:
    release = today - timedelta(days=random.randint(10, 90)) if md['status'] != 'upcoming' else today + timedelta(days=random.randint(10, 60))
    movie, created = Movie.objects.get_or_create(
        title=md['title'],
        defaults={
            'description': md['desc'],
            'duration_minutes': md['dur'],
            'release_date': release,
            'certification': md['cert'],
            'status': md['status'],
            'is_trending': md['trending'],
            'trailer_url': md['trailer'],
            'poster_url': md['poster_url'],
        }
    )
    # Always update trailer + poster_url
    movie.trailer_url = md['trailer']
    movie.poster_url = md['poster_url']
    movie.status = md['status']
    movie.is_trending = md['trending']
    movie.save()

    # Use pre-downloaded REAL Wikipedia posters from media/posters/
    try:
        from pathlib import Path as _P
        from django.core.files import File
        safe_map = {
            'Pathaan': 'Pathaan.jpg', 'Jawan': 'Jawan.jpg', 'Animal': 'Animal.jpg',
            'Salaar': 'Salaar.jpg', 'Leo': 'Leo.jpg', '12th Fail': '12th_Fail.jpg',
            'Kalki 2898 AD': 'Kalki_2898_AD.jpg', 'Stree 2': 'Stree_2.jpg',
            'Pushpa 2': 'Pushpa_2.jpg', 'Fighter': 'Fighter.jpg',
        }
        local = _P('media/posters') / safe_map.get(md['title'], '')
        if local.exists() and local.stat().st_size > 20000:
            with open(local, 'rb') as fh:
                if movie.poster:
                    movie.poster.delete(save=False)
                movie.poster.save(local.name, File(fh), save=True)
            print(f'  Real poster: {md["title"]}')
        else:
            real = download_real_poster(md['title'])
            if real:
                if movie.poster:
                    movie.poster.delete(save=False)
                movie.poster.save(real.name, real, save=True)
                print(f'  Downloaded: {md["title"]}')
            else:
                img_file = make_poster_image(md['title'], md['color'])
                if movie.poster:
                    movie.poster.delete(save=False)
                movie.poster.save(img_file.name, img_file, save=True)
                print(f'  Fallback: {md["title"]}')
    except Exception as e:
        print(f'  Poster failed for {md["title"]}: {e}')

    if created or movie.genres.count() == 0:
        movie.genres.set([genres[g] for g in md['gens'] if g in genres])
        movie.languages.set([languages[l] for l in md['langs'] if l in languages])
        for cname in md['cast']:
            if cname in casts:
                MovieCast.objects.get_or_create(movie=movie, cast=casts[cname], defaults={'role': 'actor'})
    movies.append(movie)
    print(f'  Movie: {movie.title} | trailer OK | poster={bool(movie.poster)} url={bool(movie.poster_url)}')

print(f'Movies: {len(movies)}')

# --- Shows ---
screens = list(Screen.objects.all())
show_times = [time(10, 0), time(13, 30), time(16, 45), time(19, 30), time(22, 15)]
sc = 0
for day_offset in range(5):
    show_date = today + timedelta(days=day_offset)
    for movie in movies:
        if movie.status == 'upcoming' and movie.release_date > show_date:
            continue
        for screen in random.sample(screens, min(3, len(screens))):
            for st in random.sample(show_times, 2):
                lang = movie.languages.first()
                price = Decimal(random.choice([150, 180, 200, 250, 300]))
                _, created = Show.objects.get_or_create(
                    screen=screen, show_date=show_date, show_time=st,
                    defaults={'movie': movie, 'language': lang, 'base_price': price, 'is_active': True}
                )
                if created:
                    sc += 1
print(f'Shows created: {sc} (total {Show.objects.count()})')

# --- Users ---
admin_user, created = User.objects.get_or_create(
    username='admin',
    defaults={'email': 'admin@bookmyshow.clone', 'is_staff': True, 'is_superuser': True}
)
if created:
    admin_user.set_password('Admin@123')
    admin_user.save()
else:
    admin_user.set_password('Admin@123')
    admin_user.is_staff = True
    admin_user.is_superuser = True
    admin_user.save()

demo_user, created = User.objects.get_or_create(
    username='demo',
    defaults={'email': 'demo@example.com', 'first_name': 'Demo'}
)
if created:
    demo_user.set_password('Demo@123')
    demo_user.save()
else:
    demo_user.set_password('Demo@123')
    demo_user.save()

for movie in movies[:5]:
    Review.objects.get_or_create(
        movie=movie, user=demo_user,
        defaults={
            'rating': random.randint(3, 5),
            'title': 'Must watch!',
            'content': f'Really enjoyed {movie.title}. Great performances and story.',
            'is_verified': True,
        }
    )

print('=== Seed complete ===')
print(f'Movies: {Movie.objects.count()} | Shows: {Show.objects.count()} | Seats: {Seat.objects.count()}')
print('Admin: admin / Admin@123')
print('Demo:  demo / Demo@123')
