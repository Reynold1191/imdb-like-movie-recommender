import os
import csv
import time
import random
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://api.themoviedb.org/3"

# Target: collect 1000 valid movies from random IDs 1..100000
TARGET_VALID_MOVIES = 1000
ID_MIN = 1
ID_MAX = 100000

# Safety limit so the script does not run forever if many IDs are invalid
MAX_RANDOM_ATTEMPTS = 20000

# Parallel crawling
MAX_WORKERS = 12

# API pacing. Increase if you hit 429.
REQUEST_SLEEP_SECONDS = 0.05
TIMEOUT_SECONDS = 20

# Reviews can be paginated. For a class project, 1 page is usually enough.
# Set to None if you want all review pages, but it will be slower.
MAX_REVIEW_PAGES = 1

OUT_DIR = Path("data/csv")
OUT_DIR.mkdir(parents=True, exist_ok=True)


def get_headers():
    token = os.getenv("TMDB_ACCESS_TOKEN")
    if not token:
        raise ValueError("Missing TMDB_ACCESS_TOKEN in .env")

    return {
        "Authorization": f"Bearer {token}",
        "accept": "application/json",
    }


HEADERS = get_headers()


def safe_get(url, params=None):
    try:
        time.sleep(REQUEST_SLEEP_SECONDS)
        res = requests.get(url, headers=HEADERS, params=params, timeout=TIMEOUT_SECONDS)

        if res.status_code == 429:
            retry_after = int(res.headers.get("Retry-After", "2"))
            time.sleep(retry_after)
            res = requests.get(url, headers=HEADERS, params=params, timeout=TIMEOUT_SECONDS)

        if res.status_code != 200:
            return res.status_code, None

        return res.status_code, res.json()

    except requests.RequestException:
        return None, None


def fetch_movie_details(movie_id):
    url = f"{BASE_URL}/movie/{movie_id}"
    params = {
        "append_to_response": "credits,keywords",
        "language": "en-US",
    }
    return safe_get(url, params=params)


def fetch_movie_reviews_page(movie_id, page=1):
    url = f"{BASE_URL}/movie/{movie_id}/reviews"
    params = {
        "language": "en-US",
        "page": page,
    }
    return safe_get(url, params=params)


def fetch_movie_reviews(movie_id):
    status, first_page = fetch_movie_reviews_page(movie_id, page=1)

    if status != 200 or not first_page:
        return []

    reviews = first_page.get("results", [])

    total_pages = first_page.get("total_pages", 1) or 1
    if MAX_REVIEW_PAGES is not None:
        total_pages = min(total_pages, MAX_REVIEW_PAGES)

    for page in range(2, total_pages + 1):
        status, data = fetch_movie_reviews_page(movie_id, page=page)
        if status == 200 and data:
            reviews.extend(data.get("results", []))

    return reviews


def parse_date(value):
    return value or ""


def clean_text(value):
    if value is None:
        return ""
    return str(value)

ADULT_KEYWORDS = {
    "pornography",
    "softcore",
    "hardcore",
    "erotic",
    "erotica",
    "sexploitation",
    "adult film",
    "nudity",
    "sexual content",
}


def has_blocked_adult_keyword(details):
    keyword_container = details.get("keywords") or {}
    keyword_list = keyword_container.get("keywords", [])

    movie_keywords = [
        clean_text(keyword.get("name")).strip().lower()
        for keyword in keyword_list
        if keyword.get("name")
    ]

    return any(
        blocked in keyword_name
        for keyword_name in movie_keywords
        for blocked in ADULT_KEYWORDS
    )



def build_rows_from_movie(details, reviews):
    movie_id = details["id"]

    rows = {
        "movies": [],
        "genres": [],
        "movie_genres": [],
        "persons": [],
        "movie_cast": [],
        "movie_crew": [],
        "keywords": [],
        "movie_keywords": [],
        "companies": [],
        "movie_companies": [],
        "countries": [],
        "movie_countries": [],
        "reviews": [],
    }

    collection = details.get("belongs_to_collection") or {}

    rows["movies"].append({
        "movie_id": movie_id,
        "title": clean_text(details.get("title")),
        "original_title": clean_text(details.get("original_title")),
        "overview": clean_text(details.get("overview")),
        "release_date": parse_date(details.get("release_date")),
        "runtime": details.get("runtime") or "",
        "original_language": clean_text(details.get("original_language")),
        "status": clean_text(details.get("status")),
        "imdb_id": clean_text(details.get("imdb_id")),
        "popularity": details.get("popularity") or "",
        "vote_average": details.get("vote_average") or "",
        "vote_count": details.get("vote_count") or "",
        "adult_flag": details.get("adult"),
        "video_flag": details.get("video"),
        "poster_path": clean_text(details.get("poster_path")),
        "backdrop_path": clean_text(details.get("backdrop_path")),
        "homepage": clean_text(details.get("homepage")),
        "tagline": clean_text(details.get("tagline")),
        "budget": details.get("budget") or 0,
        "revenue": details.get("revenue") or 0,
        "collection_id": collection.get("id", ""),
        "collection_name": clean_text(collection.get("name")),
    })

    for genre in details.get("genres", []):
        genre_id = genre.get("id")
        if genre_id is None:
            continue
        rows["genres"].append({"genre_id": genre_id, "genre_name": clean_text(genre.get("name"))})
        rows["movie_genres"].append({"movie_id": movie_id, "genre_id": genre_id})

    for company in details.get("production_companies", []):
        company_id = company.get("id")
        if company_id is None:
            continue
        rows["companies"].append({
            "company_id": company_id,
            "company_name": clean_text(company.get("name")),
            "logo_path": clean_text(company.get("logo_path")),
            "origin_country": clean_text(company.get("origin_country")),
        })
        rows["movie_companies"].append({"movie_id": movie_id, "company_id": company_id})

    for country in details.get("production_countries", []):
        country_code = country.get("iso_3166_1")
        if not country_code:
            continue
        rows["countries"].append({
            "country_code": country_code,
            "country_name": clean_text(country.get("name")),
        })
        rows["movie_countries"].append({"movie_id": movie_id, "country_code": country_code})

    keyword_container = details.get("keywords") or {}
    keyword_list = keyword_container.get("keywords", [])

    for keyword in keyword_list:
        keyword_id = keyword.get("id")
        if keyword_id is None:
            continue
        rows["keywords"].append({"keyword_id": keyword_id, "keyword_name": clean_text(keyword.get("name"))})
        rows["movie_keywords"].append({"movie_id": movie_id, "keyword_id": keyword_id})

    credits = details.get("credits") or {}

    for cast in credits.get("cast", []):
        person_id = cast.get("id")
        credit_id = cast.get("credit_id")
        if person_id is None or not credit_id:   # credit_id is now part of PK
            continue
        rows["persons"].append({
            "person_id": person_id,
            "name": clean_text(cast.get("name")),
            "original_name": clean_text(cast.get("original_name")),
            "gender": cast.get("gender") if cast.get("gender") is not None else "",
            "known_for_department": clean_text(cast.get("known_for_department")),
            "profile_path": clean_text(cast.get("profile_path")),
            "popularity": cast.get("popularity") or "",
        })
        rows["movie_cast"].append({
            "movie_id": movie_id,
            "person_id": person_id,
            "credit_id": clean_text(credit_id),
            "character_name": clean_text(cast.get("character")),
            "cast_order": cast.get("order") if cast.get("order") is not None else "",
            "cast_id": cast.get("cast_id") if cast.get("cast_id") is not None else "",
        })

    for crew in credits.get("crew", []):
        person_id = crew.get("id")
        credit_id = crew.get("credit_id")
        if person_id is None or not credit_id:
            continue
        rows["persons"].append({
            "person_id": person_id,
            "name": clean_text(crew.get("name")),
            "original_name": clean_text(crew.get("original_name")),
            "gender": crew.get("gender") if crew.get("gender") is not None else "",
            "known_for_department": clean_text(crew.get("known_for_department")),
            "profile_path": clean_text(crew.get("profile_path")),
            "popularity": crew.get("popularity") or "",
        })
        rows["movie_crew"].append({
            "movie_id": movie_id,
            "person_id": person_id,
            "credit_id": clean_text(credit_id),
            "department": clean_text(crew.get("department")),
            "job_title": clean_text(crew.get("job")),
        })

    for review in reviews:
        review_id = review.get("id")
        if not review_id:
            continue
        author_details = review.get("author_details") or {}
        rows["reviews"].append({
            "review_id": clean_text(review_id),
            "movie_id": movie_id,
            "author_name": clean_text(review.get("author")),
            "author_username": clean_text(author_details.get("username")),
            "author_display_name": clean_text(author_details.get("name")),
            "author_avatar_path": clean_text(author_details.get("avatar_path")),
            "author_rating": author_details.get("rating") if author_details.get("rating") is not None else "",
            "content": clean_text(review.get("content")),
            "created_at": clean_text(review.get("created_at")),
            "updated_at": clean_text(review.get("updated_at")),
            "review_url": clean_text(review.get("url")),
        })

    return rows


def crawl_one_movie(movie_id):
    status, details = fetch_movie_details(movie_id)

    if status != 200 or not details:
        return {"movie_id": movie_id, "status": status, "valid": False, "rows": None}
    
    # Skip adult movies
    if details.get("adult") is True:
        return {"movie_id": movie_id, "status": 200, "valid": False, "rows": None, "reason": "adult"}
    
    if has_blocked_adult_keyword(details):
        return {"movie_id": movie_id, "status": 200, "valid": False, "rows": None, "reason": "adult_keyword"}

    reviews = fetch_movie_reviews(movie_id)
    rows = build_rows_from_movie(details, reviews)

    return {"movie_id": movie_id, "status": 200, "valid": True, "rows": rows}


CSV_FIELDS = {
    # ── core movie data ──────────────────────────────────────────────────────
    "movies": [
        "movie_id", "title", "original_title", "overview", "release_date", "runtime",
        "original_language", "status", "imdb_id", "popularity", "vote_average",
        "vote_count", "adult_flag", "video_flag", "poster_path", "backdrop_path",
        "homepage", "tagline", "budget", "revenue", "collection_id", "collection_name",
    ],
    "genres": ["genre_id", "genre_name"],
    "movie_genres": ["movie_id", "genre_id"],
    "persons": [
        "person_id", "name", "original_name", "gender",
        "known_for_department", "profile_path", "popularity",
    ],
    "movie_cast": ["movie_id", "person_id", "credit_id", "character_name", "cast_order", "cast_id"],
    "movie_crew": ["movie_id", "person_id", "credit_id", "department", "job_title"],
    "keywords": ["keyword_id", "keyword_name"],
    "movie_keywords": ["movie_id", "keyword_id"],
    "companies": ["company_id", "company_name", "logo_path", "origin_country"],
    "movie_companies": ["movie_id", "company_id"],
    "countries": ["country_code", "country_name"],
    "movie_countries": ["movie_id", "country_code"],
    "reviews": [
        "review_id", "movie_id", "author_name", "author_username", "author_display_name",
        "author_avatar_path", "author_rating", "content", "created_at", "updated_at", "review_url",
    ],
    # ── derived from review authors (no real TMDB auth endpoint available) ──
    "tmdb_accounts": ["account_id", "username", "display_name", "avatar_path", "include_adult"],
    "user_ratings":  ["account_id", "movie_id", "rating_value", "created_at"],
    # ── empty stubs (require live TMDB guest-session flow to populate) ───────
    "guest_sessions": ["guest_session_id", "expires_at"],
    "guest_ratings":  ["guest_session_id", "movie_id", "rating_value", "created_at"],
}


def derive_accounts_and_ratings(all_rows):
    """
    Build tmdb_accounts and user_ratings rows from the collected reviews.
    Each unique author_username becomes one synthetic tmdb_account.
    Each review with a numeric author_rating becomes one user_rating row.
    guest_sessions and guest_ratings are left empty (require live TMDB auth).
    """
    accounts = {}   # username -> row dict
    for i, review in enumerate(all_rows.get("reviews", []), start=1):
        username = (review.get("author_username") or "").strip()
        if not username or username in accounts:
            continue
        accounts[username] = {
            "account_id":   i,
            "username":     username,
            "display_name": (review.get("author_display_name") or "").strip() or username,
            "avatar_path":  (review.get("author_avatar_path") or "").strip() or "",
            "include_adult": False,
        }

    rating_rows = []
    seen_pairs = set()
    for review in all_rows.get("reviews", []):
        username    = (review.get("author_username") or "").strip()
        raw_rating  = str(review.get("author_rating") or "").strip()
        movie_id_s  = str(review.get("movie_id") or "").strip()
        if not username or not raw_rating or not movie_id_s:
            continue
        try:
            rating_value = float(raw_rating)
            movie_id     = int(movie_id_s)
        except ValueError:
            continue
        account = accounts.get(username)
        if account is None:
            continue
        pair = (account["account_id"], movie_id)
        if pair in seen_pairs:
            continue
        seen_pairs.add(pair)
        rating_rows.append({
            "account_id":   account["account_id"],
            "movie_id":     movie_id,
            "rating_value": rating_value,
            "created_at":   (review.get("created_at") or "").strip(),
        })

    all_rows["tmdb_accounts"]  = list(accounts.values())
    all_rows["user_ratings"]   = rating_rows
    all_rows["guest_sessions"] = []   # populated only via live TMDB guest-session flow
    all_rows["guest_ratings"]  = []


def deduplicate_rows(rows_by_table):
    pk_fields = {
        "movies":         ["movie_id"],
        "genres":         ["genre_id"],
        "movie_genres":   ["movie_id", "genre_id"],
        "persons":        ["person_id"],
        "movie_cast":     ["movie_id", "person_id", "credit_id"],
        "movie_crew":     ["movie_id", "person_id", "credit_id"],
        "keywords":       ["keyword_id"],
        "movie_keywords": ["movie_id", "keyword_id"],
        "companies":      ["company_id"],
        "movie_companies":["movie_id", "company_id"],
        "countries":      ["country_code"],
        "movie_countries":["movie_id", "country_code"],
        "reviews":        ["review_id"],
        "tmdb_accounts":  ["account_id"],
        "user_ratings":   ["account_id", "movie_id"],
        "guest_sessions": ["guest_session_id"],
        "guest_ratings":  ["guest_session_id", "movie_id"],
    }

    result = {}

    for table, rows in rows_by_table.items():
        seen = set()
        unique_rows = []

        for row in rows:
            key = tuple(row.get(field) for field in pk_fields[table])
            if key in seen:
                continue
            seen.add(key)
            unique_rows.append(row)

        result[table] = unique_rows

    return result


def write_csv_files(rows_by_table):
    for table, fields in CSV_FIELDS.items():
        filepath = OUT_DIR / f"{table}.csv"
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows_by_table.get(table, []))

        print(f"Wrote {filepath} ({len(rows_by_table.get(table, []))} rows)")


def main():
    random_ids = random.sample(range(ID_MIN, ID_MAX + 1), MAX_RANDOM_ATTEMPTS)

    all_rows = {table: [] for table in CSV_FIELDS}
    valid_count = 0
    attempted_count = 0

    print(f"Trying random TMDB movie IDs from {ID_MIN} to {ID_MAX}")
    print(f"Target valid movies: {TARGET_VALID_MOVIES}")
    print(f"Max attempts: {MAX_RANDOM_ATTEMPTS}")
    print(f"Max workers: {MAX_WORKERS}")

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_id = {}

        id_iter = iter(random_ids)

        for _ in range(MAX_WORKERS):
            try:
                movie_id = next(id_iter)
            except StopIteration:
                break
            future_to_id[executor.submit(crawl_one_movie, movie_id)] = movie_id

        while future_to_id and valid_count < TARGET_VALID_MOVIES:
            for future in as_completed(list(future_to_id.keys())):
                movie_id = future_to_id.pop(future)
                attempted_count += 1

                try:
                    result = future.result()
                except Exception as e:
                    print(f"[ERROR] movie_id={movie_id}: {e}")
                    result = {"valid": False, "status": None}

                if result.get("valid"):
                    valid_count += 1
                    rows = result["rows"]

                    for table, table_rows in rows.items():
                        all_rows[table].extend(table_rows)

                    print(f"[VALID {valid_count}/{TARGET_VALID_MOVIES}] movie_id={movie_id}, reviews={len(rows['reviews'])}")
                else:
                    print(f"[SKIP] movie_id={movie_id}, status={result.get('status')}")

                if valid_count >= TARGET_VALID_MOVIES:
                    break

                try:
                    next_movie_id = next(id_iter)
                    future_to_id[executor.submit(crawl_one_movie, next_movie_id)] = next_movie_id
                except StopIteration:
                    pass

            if attempted_count >= MAX_RANDOM_ATTEMPTS:
                break

    print("\nCrawling finished.")
    print(f"Attempted IDs: {attempted_count}")
    print(f"Valid movies collected: {valid_count}")

    print("\nDeriving tmdb_accounts and user_ratings from review authors...")
    derive_accounts_and_ratings(all_rows)

    print("\nDeduplicating rows...")
    all_rows = deduplicate_rows(all_rows)

    print("\nWriting CSV files...")
    write_csv_files(all_rows)

    print("\nDone.")
    print(f"CSV output folder: {OUT_DIR.resolve()}")


if __name__ == "__main__":
    main()
