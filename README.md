# BookMyShow Clone — Django Movie Ticket Booking Platform

Production-ready clone of BookMyShow with real-time seat booking, payments, admin analytics, and e-tickets.

## Features (6 Modules)

| # | Module | Highlights |
|---|--------|------------|
| 1 | **Movie Management** | Movies, Genres, Languages, Cast, Trailers, Multi-posters, Certification, Verified Reviews (only booked users), Similar & Trending |
| 2 | **Seat Reservation** | Multi-seat select, live availability (5s polling), 2-min temporary hold, auto-release, color status (Available/Held/Booked) |
| 3 | **Payment Workflow** | Razorpay (test + demo mode), Success/Failure/Cancel/Retry, Webhook + signature verification, Idempotency keys |
| 4 | **Admin Dashboard** | Revenue (daily/weekly/monthly/yearly), Occupancy, Top movies/theaters, Peak hours, Cancellations, User growth, CSV export |
| 5 | **Discovery** | Search + filters (genre, language, city, rating, status), sorting, pagination, live result count API |
| 6 | **PDF Ticket + Email** | ReportLab PDF with QR code, Celery async email, download from history |

## Tech Stack

- **Backend:** Django 5/6 + PostgreSQL (SQLite local)
- **Concurrency:** `transaction.atomic()` + `select_for_update()`
- **Payments:** Razorpay (India-friendly test mode)
- **Background:** Celery + Redis
- **PDF:** ReportLab + qrcode
- **Frontend:** Bootstrap 5 + vanilla JS (seat map)
- **Deploy:** Gunicorn + WhiteNoise → Render (free tier)

## Quick Start (Local)

```bash
git clone <your-repo>
cd bookmyshow-clone
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python seed_data.py
python manage.py runserver
```

Open http://127.0.0.1:8000

**Admin:** `admin` / `Admin@123`  
**Demo user:** `demo` / `Demo@123`

## Deploy on Render (Free)

1. Push this repo to GitHub
2. Create new **Web Service** on Render → connect repo
3. Runtime: Python · Build: `./build.sh` · Start: `gunicorn bookmyshow.wsgi:application`
4. Add **PostgreSQL** free database → set `DATABASE_URL`
5. Env vars: `SECRET_KEY`, `DEBUG=False`, `ALLOWED_HOSTS=.onrender.com`
6. Optional: Redis (for Celery), Razorpay test keys

Or use `render.yaml` for Blueprint deploy.

## Project Structure

```
bookmyshow/
  settings.py, urls.py, celery.py, wsgi.py
accounts/     # Auth, Profile
movies/       # Movie, Genre, Language, Cast, Review
theaters/     # City, Theater, Screen, Seat, Show
bookings/     # Booking, SeatReservation (concurrency)
payments/     # Payment, TransactionHistory, Razorpay
dashboard/    # Admin analytics
templates/    # Bootstrap UI
seed_data.py  # Sample data
```

## Concurrency Safety

Seat hold uses:

```python
with transaction.atomic():
    reservations = SeatReservation.objects.select_for_update().filter(...)
    # check availability → hold → create booking
```

Prevents double-booking under concurrent requests.

## Admin Credentials (for report)

- URL: `/admin/`
- Username: `admin`
- Password: `Admin@123`

## License

MIT — Internship / portfolio project.
