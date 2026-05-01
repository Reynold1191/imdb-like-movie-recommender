# TMDB — Toan & Mahin Database

> **Not The Movie Database, but Toan & Mahin Database**

A full-stack movie recommender web application built on top of a PostgreSQL database populated from the [TMDB API](https://developer.themoviedb.org/reference/getting-started).

**Group 10** · Thai Toan Tran `117739781` · Mahin Roddur `116778987`  
CSE 532 / Data Management — Stony Brook University, Spring 2026

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Project Structure](#project-structure)
4. [Database Schema](#database-schema)
5. [How to Run](#how-to-run)
6. [User Site](#user-site)
7. [Admin Site](#admin-site)
8. [Login Credentials](#login-credentials)
9. [SQL Functions Reference](#sql-functions-reference)
10. [Environment Variables](#environment-variables)

---

## Overview

TMDB is a relational database project that crawls ~1,000 movies from the TMDB API and exposes them through:

- A **user-facing website** — browse movies, view details, rate films, and receive personalized recommendations
- An **admin dashboard** — analytics, data quality reports, and user activity tracking

The project demonstrates practical use of SQL across joins, aggregations, CTEs, and window functions over a realistic multi-table schema.

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                    Browser (HTML/CSS/JS)             │
└──────────────────────┬──────────────────────────────┘
                       │ HTTP
┌──────────────────────▼──────────────────────────────┐
│           Flask Web App  (Python 3.11)               │
│           app.py · templates/ · static/              │
│           Jinja2 · psycopg2                          │
└──────────────────────┬──────────────────────────────┘
                       │ SQL (psycopg2)
┌──────────────────────▼──────────────────────────────┐
│           PostgreSQL 16  (Docker container)          │
│           port 5433 (host) → 5432 (container)        │
└─────────────────────────────────────────────────────┘
```

**Running modes:**

| Mode | Command | URLs |
|---|---|---|
| Local dev | `python app.py` (Postgres must be running — e.g. `docker compose up -d db`) | http://localhost:5000 |
| Full stack (build) | `docker compose up --build -d` | App http://localhost:5000 · pgAdmin http://localhost:5050 |
| Stack without rebuild | `docker compose up -d` | Same as above |

Use `docker compose --profile loader up load_csv` when you want the one-shot CSV import container (truncates + loads all tables).

## Project Structure

```
imdb-like-movie-recommender/
│
├── app.py                         # Flask application (routes, DB logic, Jinja2 filters)
├── Dockerfile.web                 # Container image for the Flask app
├── compose.yaml                   # postgres + pgAdmin + Flask web (optional `--profile loader` for CSV load container)
├── requirements.txt               # Python dependencies
├── .env.example                   # Copy to .env and fill secrets
│
├── templates/                     # Jinja2 HTML templates
│   ├── base.html                  # User site base layout (navbar, footer)
│   ├── _macros.html               # Reusable sql_box macro
│   ├── login.html
│   ├── register.html
│   ├── home.html
│   ├── browse.html
│   ├── movie_detail.html
│   ├── profile.html
│   ├── my_ratings.html
│   └── admin/
│       ├── base.html              # Admin site base layout (sidebar nav)
│       ├── dashboard.html
│       ├── users.html
│       ├── movies.html
│       ├── ratings.html
│       ├── genres.html
│       ├── keywords.html
│       ├── companies.html
│       ├── reviews.html
│       └── data_quality.html
│
├── static/
│   ├── css/style.css              # Dark TMDB-inspired theme
│   └── js/main.js                 # Dropdown, SQL copy, table pagination
│
├── plan.md                         # Formal schema design narrative (HW2)
├── Relational Schema_Course Project_Group 10.pdf   # ER / relational diagram PDF
├── queries/                        # Example analytical SQL (copy into pgAdmin)
│   ├── most_frequent_cast_members.sql
│   ├── popular_directors.sql
│   ├── top_companies.sql
│   ├── top_genres.sql
│   └── top_keywords.sql
├── scripts/
│   ├── fetch_tmdb_1000_random_to_csv.py   # Crawl TMDB API → 17 CSV files (includes adult-keyword filter)
│   └── load_csv_to_postgres.py            # Load CSVs into PostgreSQL
│
├── db/
│   ├── init/01_create_tables.sql  # Auto-runs on first docker compose up
│   └── pgadmin/
│       ├── servers.json           # Pre-configured pgAdmin servers
│       └── pgpass                 # Saved passwords (not committed)
│
├── data/csv/                      # 17 CSV files (one per table)
│
└── tmdb_sql_functions.md          # All SQL queries (Functions 1–27) with page locations
```

---

## Database Schema

17 tables organised around the `movie` entity:

```
MOVIE
 ├─< MOVIE_GENRE    >── GENRE
 ├─< MOVIE_CAST     >── PERSON
 ├─< MOVIE_CREW     >── PERSON
 ├─< MOVIE_KEYWORD  >── KEYWORD
 ├─< MOVIE_COMPANY  >── COMPANY
 ├─< MOVIE_COUNTRY  >── COUNTRY
 ├─< REVIEW
 ├─< USER_RATING    >── TMDB_ACCOUNT
 └─< GUEST_RATING   >── GUEST_SESSION
```

**Key design decisions:**

- `PERSON` is shared by `MOVIE_CAST` and `MOVIE_CREW` — no profile duplication
- `movie_cast` uses `(movie_id, person_id, credit_id)` as PK so an actor with multiple roles in one film gets one row per credit
- `REVIEW` stores author fields as a snapshot (TMDB does not expose a full public user model)
- `TMDB_ACCOUNT` is a lightweight external-user entity — no password column (demo uses fixed password `1`)
- `USER_RATING` and `GUEST_RATING` are split because their identifiers come from different domains

Approximate counts for bundled [`data/csv/`](data/csv/) files after a crawl (figures vary each run):

| Table | Rows (approx.) | Description |
|---|---|---|
| `movie` | ~1 000 | Core movie metadata |
| `genre` | ~19 | TMDB genre master list |
| `movie_genre` | ~2 000 | Movie ↔ genre bridge |
| `person` | ~34 000 | Actors and crew members |
| `movie_cast` | ~19 500 | Cast roles per movie |
| `movie_crew` | ~20 100 | Crew jobs per movie |
| `keyword` | ~2 400 | TMDB keyword tags |
| `movie_keyword` | ~3 800 | Movie ↔ keyword bridge |
| `company` | ~1 200 | Production companies |
| `movie_company` | ~1 600 | Movie ↔ company bridge |
| `country` | ~60 | Production countries |
| `movie_country` | ~1 050 | Movie ↔ country bridge |
| `review` | ~830 | User-written reviews |
| `tmdb_account` | ~79 | Reviewer accounts (derived) |
| `user_rating` | ~224 | Numeric ratings from reviewers |
| `guest_session` | 0 | Requires live TMDB guest-session auth |
| `guest_rating` | 0 | Requires live TMDB guest-session auth |

Additional reference: [`queries/`](queries/) (analytical examples for pgAdmin) and [`Relational Schema_Course Project_Group 10.pdf`](Relational Schema_Course Project_Group 10.pdf) (diagram).  
**Fetch** skips TMDB-adult-flagged titles and configurable adult keyword phrases in `fetch_tmdb_1000_random_to_csv.py`. **Load**: host `python scripts/load_csv_to_postgres.py`; Docker `docker compose --profile loader up load_csv`.

---

## How to Run

### Prerequisites

| Tool | Version |
|---|---|
| Python | 3.10+ |
| Docker Desktop | any recent |

### Option A — Local Python + Docker database

**1. Clone and configure**

```bash
git clone https://github.com/Reynold1191/imdb-like-movie-recommender.git
cd imdb-like-movie-recommender
cp .env.example .env
# Edit .env with your values
```

**2. Start the database**

```bash
docker compose up -d db
```

PostgreSQL starts on `localhost:5433`. The schema is created automatically on first boot via `db/init/01_create_tables.sql`.

**3. Install Python dependencies**

```bash
pip install -r requirements.txt
```

**4. Fetch movie data from TMDB**

```bash
python scripts/fetch_tmdb_1000_random_to_csv.py
```

Crawls ~1,000 random movies from TMDB API and writes 17 CSV files to `data/csv/`.  
Requires `TMDB_ACCESS_TOKEN` in `.env` (get one free at [themoviedb.org/settings/api](https://www.themoviedb.org/settings/api)).

**5. Load data into PostgreSQL**

```bash
python scripts/load_csv_to_postgres.py
```

Truncates all tables then loads all 17 CSVs in FK-dependency order using fast `COPY`.

**6. Start the web app**

```bash
python app.py
```

Open [http://localhost:5000](http://localhost:5000)

---

### Option B — Full Docker (all services)

```bash
docker compose up --build
```

Starts three containers:

| Container | URL |
|---|---|
| `movie-web` (Flask) | http://localhost:5000 |
| `movie-postgres` (PostgreSQL) | `localhost:5433` |
| `movie-pgadmin` (pgAdmin 4) | http://localhost:5050 |

The web service waits for the database health check before starting.

---

### Re-running / Reset

```bash
# Re-fetch fresh data (overwrites data/csv/)
python scripts/fetch_tmdb_1000_random_to_csv.py

# Reload (truncates DB then reloads — no docker restart needed)
python scripts/load_csv_to_postgres.py

# Full reset (wipes schema + data)
docker compose down -v
docker compose up -d
python scripts/load_csv_to_postgres.py
```

---

## User Site

Accessible at **http://localhost:5000** after login.

### Flow

```
Login / Register
    │
    ▼
Home
├── Top 10 rated movies
├── Top movies per genre (carousel rows)
└── Personalized recommendations (based on your highest-rated genres)
    │
    ▼
Browse  (/browse)
├── Search by title, genre, keyword, or company name
├── Filter: genre, release year range, min TMDB rating
└── Results grid with poster, score badge
    │
    ▼
Movie Detail  (/movie/<id>)
├── Full metadata (overview, runtime, budget, revenue, tagline)
├── TMDB score + vote count
├── Cast cards + Crew table
├── Reviews section
├── Rate this movie (1–10 star widget)
└── Similar Movies sidebar (by shared keywords)
    │
    ▼
Profile  (/profile)
└── Account summary: total ratings, average given
    │
    ▼
My Ratings  (/my-ratings)
└── All your rated movies — your score vs TMDB average
```

### Pages summary

| Page | Route | SQL Functions |
|---|---|---|
| Login | `/login` | F1 |
| Register | `/register` | — |
| Home | `/` | F2, F3, F10 |
| Browse | `/browse` | F4 |
| Movie Detail | `/movie/<id>` | F5, F6, F7, F11 |
| Profile | `/profile` | F8 |
| My Ratings | `/my-ratings` | F9 |

---

## Admin Site

Accessible at **http://localhost:5000/admin/** using `admin` / `1`.

### Flow

```
Admin Login
    │
    ▼
Dashboard  (/admin/)
├── System stats: total movies, accounts, ratings, reviews, people, keywords
└── Top 10 rated movies table
└── Movie Release Trend by Year (F23)
    │
    ▼
Users  (/admin/users)
├── All accounts with rating count + average
└── User Engagement Ranking — RANK(), STDDEV, bias vs TMDB (F24)
    │
    ▼
Movies  (/admin/movies)
└── Top 100 movies with metadata coverage (genre/keyword/cast counts)
    │
    ▼
Ratings Analytics  (/admin/ratings)
├── Most rated movies by user count (F15)
├── Biggest rating disagreements — user vs TMDB gap (F16)
└── Rating Distribution Histogram — CASE bucketing + window % (F25)
    │
    ▼
Genre Analytics  (/admin/genres)
├── Genres by user rating activity (F17)
└── Genre Performance Deep Analysis — 3× RANK() windows (F26)
    │
    ▼
Keyword Analytics  (/admin/keywords)
└── Top keywords by associated avg user rating (F18)
    │
    ▼
Company Analytics  (/admin/companies)
├── Companies by avg TMDB rating (F19)
└── Company Portfolio Analysis — quality%, diversity score, RANK() (F27)
    │
    ▼
Review Analytics  (/admin/reviews)
└── Movies ranked by review count + avg author rating (F20)
    │
    ▼
Data Quality  (/admin/quality)
├── Movies missing keyword data (F21)
└── Movie Coverage Report — completeness across 6 metadata tables (F22)
```

### Pages summary

| Page | Route | SQL Functions |
|---|---|---|
| Dashboard | `/admin/` | F13, F2, F23 |
| Users | `/admin/users` | F14, F24 |
| Movies | `/admin/movies` | F22 |
| Ratings Analytics | `/admin/ratings` | F15, F16, F25 |
| Genre Analytics | `/admin/genres` | F17, F26 |
| Keyword Analytics | `/admin/keywords` | F18 |
| Company Analytics | `/admin/companies` | F19, F27 |
| Review Analytics | `/admin/reviews` | F20 |
| Data Quality | `/admin/quality` | F21, F22 |

---

## Login Credentials

### Demo rule

```
User account:
  username  =  {tmdb_account.username}_{tmdb_account.account_id}
  password  =  1
  example   →  JPV852_1

Admin account:
  username  =  admin
  password  =  1
```

All user accounts can be seen on the **Admin → Users** page.  
Newly registered accounts also follow the same password rule (password is always `1` for this demo).

> **Note:** This is a demo/prototype authentication system only. In production, passwords must be hashed and stored in a dedicated auth table.

---

## SQL Functions Reference

All 27 SQL functions (with full query code, page locations, and specific examples) are documented in:

**[`tmdb_sql_functions.md`](tmdb_sql_functions.md)**

Quick summary:

| # | Function | Page |
|---|---|---|
| 1 | Login | Login |
| 2 | Top 10 Movies | Home |
| 3 | Top Movies per Genre | Home |
| 4 | Browse / Search (dynamic WHERE) | Browse |
| 5 | Movie Detail | Movie Detail |
| 6 | Cast & Crew | Movie Detail |
| 7 | Movie Reviews | Movie Detail |
| 8 | User Profile | Profile |
| 9 | My Ratings | My Ratings |
| 10 | Personalized Recommendations | Home |
| 11 | Similar Movies by Keywords | Movie Detail |
| 12 | Similar Movies by Cast | Movie Detail |
| 13 | Admin Dashboard Summary | Admin Dashboard |
| 14 | Admin Users Table | Admin Users |
| 15 | Most Rated Movies | Admin Ratings |
| 16 | Rating Gap vs TMDB | Admin Ratings |
| 17 | Genre Analytics | Admin Genres |
| 18 | Keyword Analytics | Admin Keywords |
| 19 | Company Analytics | Admin Companies |
| 20 | Review Analytics | Admin Reviews |
| 21 | Missing Keywords | Admin Data Quality |
| 22 | Coverage Report (optimized) | Admin Data Quality |
| 23 | Release Trend by Year | Admin Dashboard |
| 24 | User Engagement Ranking (RANK+STDDEV) | Admin Users |
| 25 | Rating Distribution Histogram (CASE+window) | Admin Ratings |
| 26 | Genre Deep Analysis (3× RANK) | Admin Genres |
| 27 | Company Portfolio (diversity+quality score) | Admin Companies |

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `TMDB_ACCESS_TOKEN` | — | TMDB v4 Read Access Token (for data fetch) |
| `SECRET_KEY` | `cinescope-secret-2024` | Flask session secret |
| `POSTGRES_HOST` | `localhost` | Postgres host |
| `POSTGRES_PORT` | `5433` | Host-side port |
| `POSTGRES_DB` | `movie_recommender` | Database name |
| `POSTGRES_USER` | `postgres` | Postgres user |
| `POSTGRES_PASSWORD` | — | Postgres password |
| `PGADMIN_DEFAULT_EMAIL` | `admin@movie.local` | pgAdmin login email |
| `PGADMIN_DEFAULT_PASSWORD` | `admin` | pgAdmin login password |

---

## References

- [TMDB API Documentation](https://developer.themoviedb.org/reference/getting-started)
- [Flask Documentation](https://flask.palletsprojects.com/)
- [psycopg2 Documentation](https://www.psycopg.org/docs/)
- [PostgreSQL 16 Documentation](https://www.postgresql.org/docs/16/)
