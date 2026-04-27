# TMDB Movie Recommender — Database Project

A relational PostgreSQL database populated from the [TMDB API](https://developer.themoviedb.org/reference/getting-started), designed as a movie-centered schema supporting metadata, cast/crew, keywords, reviews, and ratings.

Built for **CSE 532 / Data Management** — Stony Brook University, Spring 2026.

---

## Schema Overview

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

Key design decisions (full discussion in [`plan.md`](plan.md)):

- `PERSON` is shared by `MOVIE_CAST` and `MOVIE_CREW` to avoid profile duplication.
- `movie_cast` uses `(movie_id, person_id, credit_id)` as PK so an actor with multiple roles in one film gets a separate row per credit.
- `REVIEW` stores author fields as a snapshot (TMDB does not expose a full public user model).
- `TMDB_ACCOUNT` is a lightweight external-user entity — no password column (TMDB handles auth).
- `USER_RATING` and `GUEST_RATING` are intentionally split because their identifiers come from different domains (`account_id` vs `guest_session_id`).

---

## Project Structure

```
imdb-like-movie-recommender/
├── compose.yaml                   # Docker: postgres:16 + pgAdmin 4
├── requirements.txt               # Python dependencies
├── .env.example                   # Copy to .env and fill in secrets
├── plan.md                        # Full schema design document (HW2)
│
├── scripts/
│   ├── fetch_tmdb_1000_random_to_csv.py   # Step 1 – crawl TMDB → 17 CSV files
│   └── load_csv_to_postgres.py            # Step 2 – load CSVs into PostgreSQL
│
├── db/
│   ├── init/
│   │   └── 01_create_tables.sql   # Auto-runs on first `docker compose up`
│   └── pgadmin/
│       ├── servers.json           # Pre-configured servers for pgAdmin
│       └── pgpass                 # Saved passwords (not committed)
│
└── data/
    └── csv/                       # 17 CSV files (one per table)
        ├── movies.csv
        ├── genres.csv
        ├── movie_genres.csv
        ├── persons.csv
        ├── movie_cast.csv
        ├── movie_crew.csv
        ├── keywords.csv
        ├── movie_keywords.csv
        ├── companies.csv
        ├── movie_companies.csv
        ├── countries.csv
        ├── movie_countries.csv
        ├── reviews.csv
        ├── tmdb_accounts.csv
        ├── user_ratings.csv
        ├── guest_sessions.csv
        └── guest_ratings.csv
```

---

## Prerequisites

| Tool | Version |
|---|---|
| Python | 3.10+ |
| Docker Desktop | any recent |
| Git | any |

---

## Quick Start

### 1. Clone and configure

```bash
git clone https://github.com/Reynold1191/imdb-like-movie-recommender.git
cd imdb-like-movie-recommender
cp .env.example .env
```

Edit `.env` and set your values:

```env
TMDB_ACCESS_TOKEN=your_tmdb_read_access_token   # from themoviedb.org/settings/api
POSTGRES_DB=movie_recommender
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password
POSTGRES_PORT=5433                              # 5433 avoids clash with local Postgres on 5432
PGADMIN_DEFAULT_EMAIL=admin@movie.local
PGADMIN_DEFAULT_PASSWORD=admin
```

### 2. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 3. Start PostgreSQL + pgAdmin

```bash
docker compose up -d
```

- **PostgreSQL** → `localhost:5433`  (Docker container, schema created automatically)
- **pgAdmin 4** → [http://localhost:5050](http://localhost:5050)  (login: `admin@movie.local` / `admin`)

> pgAdmin comes pre-configured with two servers:
> - **Movie Recommender DB (Docker)** — the container Postgres
> - **Local PostgreSQL (Host :5432)** — your local Postgres installation

### 4. Fetch 1 000 random movies from TMDB

```bash
python scripts/fetch_tmdb_1000_random_to_csv.py
```

Crawls random movie IDs, fetches details + credits + keywords + reviews for each, and writes **17 CSV files** to `data/csv/`. `tmdb_accounts` and `user_ratings` are derived from review authors automatically.

### 5. Load all CSVs into PostgreSQL

```bash
python scripts/load_csv_to_postgres.py
```

- Truncates all tables first (safe to re-run).
- Loads all 17 CSV files in FK-dependency order using fast `COPY`.
- Falls back to `INSERT ON CONFLICT DO NOTHING` if `COPY` fails for any table.

---

## Re-running

To fetch fresh data and reload:

```bash
# Re-fetch (overwrites data/csv/)
python scripts/fetch_tmdb_1000_random_to_csv.py

# Reload (truncates DB then loads — no docker restart needed)
python scripts/load_csv_to_postgres.py
```

To reset the Docker volume (wipes schema + data):

```bash
docker compose down -v
docker compose up -d
python scripts/load_csv_to_postgres.py
```

---

## Table Summary

| Table | Rows (sample) | Description |
|---|---|---|
| `movie` | 1 000 | Core movie metadata |
| `genre` | ~19 | TMDB genre master list |
| `movie_genre` | ~1 900 | Movie ↔ genre bridge |
| `person` | ~33 000 | Actors and crew members |
| `movie_cast` | ~18 000 | Cast roles per movie |
| `movie_crew` | ~20 000 | Crew jobs per movie |
| `keyword` | ~2 400 | TMDB keyword tags |
| `movie_keyword` | ~3 800 | Movie ↔ keyword bridge |
| `company` | ~1 300 | Production companies |
| `movie_company` | ~1 600 | Movie ↔ company bridge |
| `country` | ~68 | Production countries |
| `movie_country` | ~1 100 | Movie ↔ country bridge |
| `review` | ~230 | User-written reviews |
| `tmdb_account` | ~66 | Reviewer accounts (derived) |
| `user_rating` | ~211 | Numeric ratings from reviewers |
| `guest_session` | 0 | Requires live TMDB guest-session auth |
| `guest_rating` | 0 | Requires live TMDB guest-session auth |

---

## Environment Variables Reference

| Variable | Default | Description |
|---|---|---|
| `TMDB_ACCESS_TOKEN` | — | TMDB v4 Read Access Token |
| `POSTGRES_HOST` | `localhost` | Postgres host for load script |
| `POSTGRES_PORT` | `5433` | Host-side port for Docker Postgres |
| `POSTGRES_DB` | `movie_recommender` | Database name |
| `POSTGRES_USER` | `postgres` | Postgres user |
| `POSTGRES_PASSWORD` | — | Postgres password |
| `PGADMIN_DEFAULT_EMAIL` | `admin@movie.local` | pgAdmin login email |
| `PGADMIN_DEFAULT_PASSWORD` | `admin` | pgAdmin login password |

---

## References

- [TMDB API Documentation](https://developer.themoviedb.org/reference/getting-started)
- [TMDB API Settings](https://www.themoviedb.org/settings/api)
