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
├── compose.yaml                   # Docker: postgres:16 + pgAdmin 4 + optional CSV loader
├── requirements.txt               # Python dependencies
├── .env.example                   # Copy to .env and fill in secrets
├── plan.md                        # Full schema design document (HW2)
├── Relational Schema_Course Project_Group 10.pdf   # ER / relational schema diagram
│
├── queries/                       # Example analytical queries (run in pgAdmin or psql)
│   ├── most_frequent_cast_members.sql
│   ├── popular_directors.sql
│   ├── top_companies.sql
│   ├── top_genres.sql
│   └── top_keywords.sql
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

Starts **PostgreSQL** and **pgAdmin** only. The CSV loader service is **opt‑in** so a normal startup does not truncate and reload the database.

Alternatively, specify services explicitly:

```bash
docker compose up -d db pgadmin
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

**Adult-content filter.** Movies with TMDB `adult: true`, or titles / overviews that match configurable blocked-keyword phrases for adult-oriented content in `fetch_tmdb_1000_random_to_csv.py`, are skipped and do **not** count toward the target of 1 000 valid movies.

### 5. Load all CSVs into PostgreSQL

**Option A — on the host** (recommended while developing):

```bash
python scripts/load_csv_to_postgres.py
```

**Option B — inside Docker** (one-shot container; requires the `loader` profile):

```bash
docker compose --profile loader up load_csv
```

The `load_csv` service is **not** started by plain `docker compose up`, so your database is not wiped on every restart. Use the profile when you want the container to run `load_csv_to_postgres.py` against `db`.

The loader container installs `psycopg2-binary` and `python-dotenv`, then runs `scripts/load_csv_to_postgres.py` against the `db` service on port 5432.

What the loader does:

- Truncates all tables first (safe to re-run).
- Loads all 17 CSV files in FK-dependency order using fast `COPY`.
- Falls back to `INSERT ON CONFLICT DO NOTHING` if `COPY` fails for any table.

---

## Sample analytical queries

The [`queries/`](queries/) folder contains example SQL you can paste into **pgAdmin** (Query Tool) or `psql`. They cover cast frequency, directors, companies, genres, and keywords. Open each `.sql` file for the full statement and comments.

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

Approximate counts for the bundled dataset in [`data/csv/`](data/csv/) after a crawl (figures change each run):

| Table | Rows (approx.) | Description |
|---|---|---|
| `movie` | 1 000 | Core movie metadata |
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
