import os
import json
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://api.themoviedb.org/3"
RAW_DIR = Path("data/raw/movies")
RAW_DIR.mkdir(parents=True, exist_ok=True)


def headers():
    token = os.getenv("TMDB_ACCESS_TOKEN")
    if not token:
        raise ValueError("Missing TMDB_ACCESS_TOKEN in .env")

    return {
        "Authorization": f"Bearer {token}",
        "accept": "application/json"
    }


def discover_movies(page_range):
    all_movies = []

    for page in page_range:
        print(f"Fetching discover page {page}...")

        res = requests.get(
            f"{BASE_URL}/discover/movie",
            headers=headers(),
            params={
                "sort_by": "popularity.desc",
                "page": page,
                "include_adult": False
            }
        )

        res.raise_for_status()
        data = res.json()

        all_movies.extend(data["results"])
        time.sleep(0.25)

    return all_movies

def fetch_movie_details(movie_id):
    res = requests.get(
        f"{BASE_URL}/movie/{movie_id}",
        headers=headers(),
        params={
            "append_to_response": "credits,keywords"
        }
    )

    res.raise_for_status()
    return res.json()


def main():
    page_range = range(1, 51)
    movies = discover_movies(page_range)

    print(f"Found {len(movies)} movies")

    for i, m in enumerate(movies, start=1):
        movie_id = m["id"]

        try:
            print(f"[{i}] Fetching movie {movie_id}")
            data = fetch_movie_details(movie_id)

            filepath = RAW_DIR / f"{movie_id}.json"

            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

            time.sleep(0.25)

        except Exception as e:
            print(f"Failed for {movie_id}: {e}")

    print("Done.")


if __name__ == "__main__":
    main()