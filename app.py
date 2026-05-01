import os
from functools import wraps

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv
from flask import (Flask, flash, redirect, render_template, request,
                   session, url_for)

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "tmdb-movie-recommender-secret-2024")

TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/w300"
TMDB_BACKDROP_BASE = "https://image.tmdb.org/t/p/w1280"


@app.template_filter("score_class")
def score_class_filter(val):
    """Return CSS class (high/mid/low) for a numeric score, handles None."""
    if val is None:
        return "low"
    try:
        v = float(val)
    except (TypeError, ValueError):
        return "low"
    return "high" if v >= 7 else ("mid" if v >= 5 else "low")


@app.template_filter("fmt_score")
def fmt_score_filter(val, decimals=1):
    if val is None:
        return "N/A"
    try:
        return f"{float(val):.{decimals}f}"
    except (TypeError, ValueError):
        return "N/A"

DB_CONFIG = {
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "port": int(os.getenv("POSTGRES_PORT", 5433)),
    "database": os.getenv("POSTGRES_DB", "movie_recommender"),
    "user": os.getenv("POSTGRES_USER", "postgres"),
    "password": os.getenv("POSTGRES_PASSWORD", "123456"),
}


def get_db():
    return psycopg2.connect(**DB_CONFIG)


def dict_cursor(conn):
    return conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)


# ── Decorators ──────────────────────────────────────────────────────────────

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user" not in session or not session["user"].get("is_admin"):
            flash("Admin access required.", "error")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


# ── Context processor ────────────────────────────────────────────────────────

@app.context_processor
def inject_globals():
    return {
        "tmdb_img": TMDB_IMAGE_BASE,
        "tmdb_backdrop": TMDB_BACKDROP_BASE,
    }


# ── Auth Routes ──────────────────────────────────────────────────────────────

@app.route("/login", methods=["GET", "POST"])
def login():
    if "user" in session:
        if session["user"].get("is_admin"):
            return redirect(url_for("admin_dashboard"))
        return redirect(url_for("home"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not username or not password:
            flash("Please enter username and password.", "error")
            return render_template("login.html")

        # Admin login
        if username == "admin" and password == "1":
            session["user"] = {
                "username": "admin",
                "display_name": "Administrator",
                "is_admin": True,
            }
            return redirect(url_for("admin_dashboard"))

        if password != "1":
            flash("Invalid username or password.", "error")
            return render_template("login.html")

        # Username format: {tmdb_username}_{account_id}  e.g. r96sk_1
        if "_" not in username:
            flash(
                "Invalid format. Use <strong>username_accountid</strong> "
                "(e.g. <strong>r96sk_1</strong>).",
                "error",
            )
            return render_template("login.html")

        parts = username.rsplit("_", 1)
        if len(parts) != 2 or not parts[1].isdigit():
            flash(
                "Invalid format. Use <strong>username_accountid</strong> "
                "(e.g. <strong>r96sk_1</strong>).",
                "error",
            )
            return render_template("login.html")

        tmdb_username = parts[0]
        account_id_int = int(parts[1])

        conn = get_db()
        cur = dict_cursor(conn)
        cur.execute(
            """
            SELECT account_id, username, display_name, avatar_path
            FROM tmdb_account
            WHERE username = %s AND account_id = %s
            """,
            (tmdb_username, account_id_int),
        )
        user = cur.fetchone()
        cur.close()
        conn.close()

        if user:
            session["user"] = {
                "account_id": user["account_id"],
                "username": user["username"],
                "display_name": user["display_name"] or user["username"],
                "avatar_path": user["avatar_path"],
                "is_admin": False,
            }
            return redirect(url_for("home"))

        flash("Invalid username or password.", "error")

    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if "user" in session:
        return redirect(url_for("home"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        display_name = request.form.get("display_name", "").strip()

        if not username:
            flash("Username is required.", "error")
            return render_template("register.html")

        if len(username) < 3:
            flash("Username must be at least 3 characters.", "error")
            return render_template("register.html")

        conn = get_db()
        cur = dict_cursor(conn)

        cur.execute(
            "SELECT account_id FROM tmdb_account WHERE username = %s", (username,)
        )
        if cur.fetchone():
            flash("Username already taken. Please choose another.", "error")
            cur.close()
            conn.close()
            return render_template("register.html")

        cur.execute(
            "SELECT COALESCE(MAX(account_id), 0) + 1 AS new_id FROM tmdb_account"
        )
        new_id = cur.fetchone()["new_id"]

        cur2 = conn.cursor()
        cur2.execute(
            """
            INSERT INTO tmdb_account (account_id, username, display_name, include_adult)
            VALUES (%s, %s, %s, %s)
            """,
            (new_id, username, display_name or username, False),
        )
        conn.commit()
        cur.close()
        cur2.close()
        conn.close()

        flash(
            f"Account created! You can now log in with username <strong>{username}</strong> and password <strong>1</strong>.",
            "success",
        )
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ── User Routes ──────────────────────────────────────────────────────────────

@app.route("/")
@login_required
def home():
    conn = get_db()
    cur = dict_cursor(conn)

    cur.execute(
        """
        SELECT movie_id, title, release_date, vote_average, vote_count, popularity, poster_path
        FROM movie
        WHERE vote_count >= 100
        ORDER BY vote_average DESC, popularity DESC
        LIMIT 10
        """
    )
    top_movies = cur.fetchall()

    cur.execute(
        """
        WITH ranked AS (
            SELECT g.genre_name, m.movie_id, m.title, m.release_date,
                   m.vote_average, m.poster_path,
                   ROW_NUMBER() OVER (
                       PARTITION BY g.genre_id
                       ORDER BY m.vote_average DESC, m.popularity DESC
                   ) AS rn
            FROM movie m
            JOIN movie_genre mg ON m.movie_id = mg.movie_id
            JOIN genre g ON mg.genre_id = g.genre_id
            WHERE m.vote_count >= 100
        )
        SELECT * FROM ranked
        WHERE rn <= 8
        ORDER BY genre_name, rn
        """
    )
    genre_rows = [dict(r) for r in cur.fetchall()]
    genre_movies: dict = {}
    for row in genre_rows:
        g = row["genre_name"]
        genre_movies.setdefault(g, []).append(row)

    recommendations = []
    user = session.get("user", {})
    if not user.get("is_admin") and user.get("account_id"):
        cur.execute(
            """
            WITH fav_genres AS (
                SELECT mg.genre_id
                FROM user_rating ur
                JOIN movie_genre mg ON ur.movie_id = mg.movie_id
                WHERE ur.account_id = %s
                GROUP BY mg.genre_id
                HAVING AVG(ur.rating_value) >= 7.5
            )
            SELECT DISTINCT m.movie_id, m.title, m.release_date, m.vote_average, m.poster_path
            FROM movie m
            JOIN movie_genre mg ON m.movie_id = mg.movie_id
            JOIN fav_genres fg ON mg.genre_id = fg.genre_id
            WHERE m.movie_id NOT IN (
                SELECT movie_id FROM user_rating WHERE account_id = %s
            )
            ORDER BY m.vote_average DESC
            LIMIT 10
            """,
            (user["account_id"], user["account_id"]),
        )
        recommendations = cur.fetchall()

    cur.close()
    conn.close()
    return render_template(
        "home.html",
        top_movies=top_movies,
        genre_movies=genre_movies,
        genre_rows=genre_rows,
        recommendations=recommendations,
    )


def _build_browse_specific_sql(q, genre_filter, year_from, year_to, min_rating):
    """Build a display-only SQL string with actual parameter values substituted."""
    base = (
        "SELECT DISTINCT\n"
        "    m.movie_id, m.title, m.release_date,\n"
        "    m.vote_average, m.popularity, m.poster_path\n"
        "FROM movie m\n"
        "LEFT JOIN movie_genre mg ON m.movie_id = mg.movie_id\n"
        "LEFT JOIN genre g ON mg.genre_id = g.genre_id\n"
        "LEFT JOIN movie_keyword mk ON m.movie_id = mk.movie_id\n"
        "LEFT JOIN keyword k ON mk.keyword_id = k.keyword_id\n"
        "LEFT JOIN movie_company mc ON m.movie_id = mc.movie_id\n"
        "LEFT JOIN company c ON mc.company_id = c.company_id"
    )
    conditions = []
    if q:
        like = f"%{q}%"
        conditions.append(
            f"(\n    LOWER(m.title) LIKE LOWER('{like}')\n"
            f"    OR LOWER(g.genre_name) LIKE LOWER('{like}')\n"
            f"    OR LOWER(k.keyword_name) LIKE LOWER('{like}')\n"
            f"    OR LOWER(c.company_name) LIKE LOWER('{like}')\n  )"
        )
    if genre_filter:
        safe_genre = genre_filter.replace("'", "''")
        conditions.append(f"g.genre_name = '{safe_genre}'")
    if year_from:
        conditions.append(f"EXTRACT(YEAR FROM m.release_date) >= {year_from}")
    if year_to:
        conditions.append(f"EXTRACT(YEAR FROM m.release_date) <= {year_to}")
    if min_rating:
        conditions.append(f"m.vote_average >= {min_rating}")
    if conditions:
        base += "\nWHERE " + "\n  AND ".join(conditions)
    base += "\nORDER BY m.popularity DESC\nLIMIT 60;"
    return base


@app.route("/browse")
@login_required
def browse():
    q = request.args.get("q", "").strip()
    genre_filter = request.args.get("genre", "").strip()
    year_from = request.args.get("year_from", "").strip()
    year_to = request.args.get("year_to", "").strip()
    min_rating = request.args.get("min_rating", "").strip()

    conn = get_db()
    cur = dict_cursor(conn)

    cur.execute("SELECT genre_name FROM genre ORDER BY genre_name")
    genres = [r["genre_name"] for r in cur.fetchall()]

    movies = []
    filters_active = any([q, genre_filter, year_from, year_to, min_rating])
    if filters_active:
        sql = """
            SELECT DISTINCT m.movie_id, m.title, m.release_date,
                   m.vote_average, m.popularity, m.poster_path
            FROM movie m
            LEFT JOIN movie_genre mg ON m.movie_id = mg.movie_id
            LEFT JOIN genre g ON mg.genre_id = g.genre_id
            LEFT JOIN movie_keyword mk ON m.movie_id = mk.movie_id
            LEFT JOIN keyword k ON mk.keyword_id = k.keyword_id
            LEFT JOIN movie_company mc ON m.movie_id = mc.movie_id
            LEFT JOIN company c ON mc.company_id = c.company_id
            WHERE 1=1
        """
        params = []
        if q:
            like = f"%{q}%"
            sql += """
                AND (
                    LOWER(m.title) LIKE LOWER(%s)
                    OR LOWER(g.genre_name) LIKE LOWER(%s)
                    OR LOWER(k.keyword_name) LIKE LOWER(%s)
                    OR LOWER(c.company_name) LIKE LOWER(%s)
                )
            """
            params.extend([like, like, like, like])
        if genre_filter:
            sql += " AND g.genre_name = %s"
            params.append(genre_filter)
        if year_from:
            sql += " AND EXTRACT(YEAR FROM m.release_date) >= %s"
            params.append(int(year_from))
        if year_to:
            sql += " AND EXTRACT(YEAR FROM m.release_date) <= %s"
            params.append(int(year_to))
        if min_rating:
            sql += " AND m.vote_average >= %s"
            params.append(float(min_rating))
        sql += " ORDER BY m.popularity DESC LIMIT 60"
        cur.execute(sql, params)
        movies = cur.fetchall()
    else:
        cur.execute(
            """
            SELECT movie_id, title, release_date, vote_average, popularity, poster_path
            FROM movie
            WHERE vote_count >= 50
            ORDER BY popularity DESC
            LIMIT 60
            """
        )
        movies = cur.fetchall()

    browse_sql_specific = (
        _build_browse_specific_sql(q, genre_filter, year_from, year_to, min_rating)
        if filters_active else None
    )

    cur.close()
    conn.close()
    return render_template(
        "browse.html",
        movies=movies,
        genres=genres,
        q=q,
        genre_filter=genre_filter,
        year_from=year_from,
        year_to=year_to,
        min_rating=min_rating,
        browse_sql_specific=browse_sql_specific,
        movies_rows=[dict(m) for m in movies],
    )


@app.route("/movie/<int:movie_id>")
@login_required
def movie_detail(movie_id):
    conn = get_db()
    cur = dict_cursor(conn)

    cur.execute(
        """
        SELECT m.movie_id, m.title, m.overview, m.release_date, m.runtime,
               m.vote_average, m.vote_count, m.popularity, m.poster_path,
               m.backdrop_path, m.tagline, m.budget, m.revenue,
               STRING_AGG(DISTINCT g.genre_name, ', ' ORDER BY g.genre_name) AS genres,
               STRING_AGG(DISTINCT c.company_name, ', ' ORDER BY c.company_name) AS companies,
               STRING_AGG(DISTINCT k.keyword_name, ', ' ORDER BY k.keyword_name) AS keywords
        FROM movie m
        LEFT JOIN movie_genre mg ON m.movie_id = mg.movie_id
        LEFT JOIN genre g ON mg.genre_id = g.genre_id
        LEFT JOIN movie_company mc ON m.movie_id = mc.movie_id
        LEFT JOIN company c ON mc.company_id = c.company_id
        LEFT JOIN movie_keyword mk ON m.movie_id = mk.movie_id
        LEFT JOIN keyword k ON mk.keyword_id = k.keyword_id
        WHERE m.movie_id = %s
        GROUP BY m.movie_id
        """,
        (movie_id,),
    )
    movie = cur.fetchone()

    if not movie:
        flash("Movie not found.", "error")
        cur.close()
        conn.close()
        return redirect(url_for("home"))

    cur.execute(
        """
        SELECT p.person_id, p.name, mc.character_name, mc.cast_order
        FROM movie_cast mc
        JOIN person p ON mc.person_id = p.person_id
        WHERE mc.movie_id = %s
        ORDER BY mc.cast_order ASC
        LIMIT 15
        """,
        (movie_id,),
    )
    cast = cur.fetchall()

    cur.execute(
        """
        SELECT p.person_id, p.name, mcr.department, mcr.job_title
        FROM movie_crew mcr
        JOIN person p ON mcr.person_id = p.person_id
        WHERE mcr.movie_id = %s
        ORDER BY mcr.department, mcr.job_title
        LIMIT 20
        """,
        (movie_id,),
    )
    crew = cur.fetchall()

    cur.execute(
        """
        SELECT review_id, author_name, author_username, author_rating, content, created_at
        FROM review
        WHERE movie_id = %s
        ORDER BY created_at DESC
        """,
        (movie_id,),
    )
    reviews = cur.fetchall()

    cur.execute(
        """
        SELECT m2.movie_id, m2.title, m2.vote_average, m2.poster_path,
               COUNT(*) AS shared_keyword_count
        FROM movie_keyword mk1
        JOIN movie_keyword mk2 ON mk1.keyword_id = mk2.keyword_id
        JOIN movie m2 ON mk2.movie_id = m2.movie_id
        WHERE mk1.movie_id = %s AND mk2.movie_id <> %s
        GROUP BY m2.movie_id, m2.title, m2.vote_average, m2.poster_path
        ORDER BY shared_keyword_count DESC, m2.vote_average DESC
        LIMIT 8
        """,
        (movie_id, movie_id),
    )
    similar = cur.fetchall()

    user_rating = None
    user = session.get("user", {})
    if not user.get("is_admin") and user.get("account_id"):
        cur.execute(
            "SELECT rating_value FROM user_rating WHERE account_id=%s AND movie_id=%s",
            (user["account_id"], movie_id),
        )
        row = cur.fetchone()
        if row:
            user_rating = row["rating_value"]

    cur.close()
    conn.close()
    return render_template(
        "movie_detail.html",
        movie=movie,
        cast=cast,
        crew=crew,
        reviews=reviews,
        similar=similar,
        user_rating=user_rating,
    )


@app.route("/movie/<int:movie_id>/rate", methods=["POST"])
@login_required
def rate_movie(movie_id):
    user = session.get("user", {})
    if user.get("is_admin"):
        return redirect(url_for("movie_detail", movie_id=movie_id))

    rating_val = request.form.get("rating", "0")
    try:
        rating_val = float(rating_val)
    except ValueError:
        flash("Invalid rating value.", "error")
        return redirect(url_for("movie_detail", movie_id=movie_id))

    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO user_rating (account_id, movie_id, rating_value, created_at)
        VALUES (%s, %s, %s, NOW())
        ON CONFLICT (account_id, movie_id)
        DO UPDATE SET rating_value = EXCLUDED.rating_value, created_at = NOW()
        """,
        (user["account_id"], movie_id, rating_val),
    )
    conn.commit()
    cur.close()
    conn.close()
    flash("Your rating has been saved!", "success")
    return redirect(url_for("movie_detail", movie_id=movie_id))


@app.route("/profile")
@login_required
def profile():
    user = session.get("user", {})
    if user.get("is_admin"):
        return redirect(url_for("admin_dashboard"))

    conn = get_db()
    cur = dict_cursor(conn)
    cur.execute(
        """
        SELECT a.account_id, a.username, a.display_name, a.avatar_path,
               COUNT(ur.movie_id) AS total_rated_movies,
               ROUND(AVG(ur.rating_value), 2) AS average_rating_given
        FROM tmdb_account a
        LEFT JOIN user_rating ur ON a.account_id = ur.account_id
        WHERE a.account_id = %s
        GROUP BY a.account_id
        """,
        (user["account_id"],),
    )
    user_profile = cur.fetchone()

    # Recent ratings
    cur.execute(
        """
        SELECT m.movie_id, m.title, ur.rating_value, ur.created_at, m.poster_path
        FROM user_rating ur
        JOIN movie m ON ur.movie_id = m.movie_id
        WHERE ur.account_id = %s
        ORDER BY ur.created_at DESC
        LIMIT 6
        """,
        (user["account_id"],),
    )
    recent_ratings = cur.fetchall()

    cur.close()
    conn.close()
    return render_template("profile.html", user_profile=user_profile, recent_ratings=recent_ratings)


@app.route("/my-ratings")
@login_required
def my_ratings():
    user = session.get("user", {})
    if user.get("is_admin"):
        return redirect(url_for("admin_dashboard"))

    conn = get_db()
    cur = dict_cursor(conn)
    cur.execute(
        """
        SELECT m.movie_id, m.title, m.release_date,
               m.vote_average AS tmdb_average,
               ur.rating_value AS my_rating,
               ur.created_at, m.poster_path
        FROM user_rating ur
        JOIN movie m ON ur.movie_id = m.movie_id
        WHERE ur.account_id = %s
        ORDER BY ur.created_at DESC
        """,
        (user["account_id"],),
    )
    ratings = cur.fetchall()
    cur.close()
    conn.close()
    return render_template("my_ratings.html", ratings=ratings)


# ── Admin Routes ─────────────────────────────────────────────────────────────

@app.route("/admin/")
@admin_required
def admin_dashboard():
    conn = get_db()
    cur = dict_cursor(conn)
    cur.execute(
        """
        SELECT
            (SELECT COUNT(*) FROM movie)        AS total_movies,
            (SELECT COUNT(*) FROM tmdb_account) AS total_accounts,
            (SELECT COUNT(*) FROM review)       AS total_reviews,
            (SELECT COUNT(*) FROM user_rating)  AS total_user_ratings,
            (SELECT COUNT(*) FROM person)       AS total_people,
            (SELECT COUNT(*) FROM keyword)      AS total_keywords,
            (SELECT COUNT(*) FROM company)      AS total_companies
        """
    )
    stats = cur.fetchone()

    # Top 10 movies
    cur.execute(
        """
        SELECT movie_id, title, vote_average, vote_count, popularity
        FROM movie
        WHERE vote_count >= 100
        ORDER BY vote_average DESC, popularity DESC
        LIMIT 10
        """
    )
    top_movies = cur.fetchall()

    # Function 23: Movie Release Trend by Year
    cur.execute(
        """
        SELECT
            EXTRACT(YEAR FROM release_date)::INT        AS release_year,
            COUNT(*)                                     AS movie_count,
            ROUND(AVG(vote_average), 2)                  AS avg_rating,
            ROUND(AVG(popularity), 2)                    AS avg_popularity,
            SUM(CASE WHEN vote_average >= 7 THEN 1 ELSE 0 END) AS highly_rated_count
        FROM movie
        WHERE release_date IS NOT NULL
          AND EXTRACT(YEAR FROM release_date) >= 1990
        GROUP BY release_year
        ORDER BY release_year DESC
        LIMIT 20
        """
    )
    release_trends = cur.fetchall()

    cur.close()
    conn.close()
    return render_template("admin/dashboard.html", stats=stats, top_movies=top_movies,
                           release_trends=release_trends)


@app.route("/admin/users")
@admin_required
def admin_users():
    conn = get_db()
    cur = dict_cursor(conn)
    cur.execute(
        """
        SELECT a.account_id, a.username, a.display_name,
               COUNT(ur.movie_id) AS rating_count,
               ROUND(AVG(ur.rating_value), 2) AS average_rating
        FROM tmdb_account a
        LEFT JOIN user_rating ur ON a.account_id = ur.account_id
        GROUP BY a.account_id
        ORDER BY rating_count DESC
        """
    )
    users = cur.fetchall()

    # Function 24: User Engagement Ranking with window functions
    cur.execute(
        """
        WITH user_stats AS (
            SELECT
                a.account_id,
                a.username,
                a.display_name,
                COUNT(ur.movie_id)                             AS total_ratings,
                ROUND(AVG(ur.rating_value), 2)                 AS avg_rating,
                ROUND(COALESCE(STDDEV(ur.rating_value), 0), 2) AS rating_stddev,
                ROUND(
                    COALESCE(AVG(ur.rating_value), 0) - COALESCE(AVG(m.vote_average), 0),
                    2
                )                                              AS bias_vs_tmdb
            FROM tmdb_account a
            LEFT JOIN user_rating ur ON a.account_id = ur.account_id
            LEFT JOIN movie m        ON ur.movie_id  = m.movie_id
            GROUP BY a.account_id, a.username, a.display_name
        )
        SELECT *,
            RANK() OVER (ORDER BY total_ratings DESC NULLS LAST) AS activity_rank,
            RANK() OVER (ORDER BY avg_rating     DESC NULLS LAST) AS avg_rating_rank
        FROM user_stats
        ORDER BY total_ratings DESC NULLS LAST
        """
    )
    user_engagement = cur.fetchall()

    cur.close()
    conn.close()
    return render_template("admin/users.html", users=users, user_engagement=user_engagement)


@app.route("/admin/movies")
@admin_required
def admin_movies():
    conn = get_db()
    cur = dict_cursor(conn)
    cur.execute(
        """
        SELECT m.movie_id, m.title, m.release_date, m.vote_average, m.vote_count,
               COUNT(DISTINCT mg.genre_id) AS genre_count,
               COUNT(DISTINCT mk.keyword_id) AS keyword_count,
               COUNT(DISTINCT mc.person_id) AS cast_count
        FROM movie m
        LEFT JOIN movie_genre mg ON m.movie_id = mg.movie_id
        LEFT JOIN movie_keyword mk ON m.movie_id = mk.movie_id
        LEFT JOIN movie_cast mc ON m.movie_id = mc.movie_id
        GROUP BY m.movie_id
        ORDER BY m.vote_average DESC, m.vote_count DESC
        LIMIT 100
        """
    )
    movies = cur.fetchall()
    cur.close()
    conn.close()
    return render_template("admin/movies.html", movies=movies)


@app.route("/admin/ratings")
@admin_required
def admin_ratings():
    conn = get_db()
    cur = dict_cursor(conn)

    cur.execute(
        """
        SELECT m.movie_id, m.title,
               COUNT(ur.account_id) AS user_rating_count,
               ROUND(AVG(ur.rating_value), 2) AS average_user_rating,
               m.vote_average AS tmdb_average
        FROM movie m
        JOIN user_rating ur ON m.movie_id = ur.movie_id
        GROUP BY m.movie_id
        ORDER BY user_rating_count DESC, average_user_rating DESC
        LIMIT 20
        """
    )
    most_rated = cur.fetchall()

    cur.execute(
        """
        SELECT m.movie_id, m.title,
               m.vote_average AS tmdb_average,
               ROUND(AVG(ur.rating_value), 2) AS local_average,
               ROUND(AVG(ur.rating_value) - m.vote_average, 2) AS rating_gap,
               COUNT(ur.account_id) AS local_rating_count
        FROM movie m
        JOIN user_rating ur ON m.movie_id = ur.movie_id
        GROUP BY m.movie_id
        HAVING COUNT(ur.account_id) >= 3
        ORDER BY ABS(AVG(ur.rating_value) - m.vote_average) DESC
        LIMIT 20
        """
    )
    rating_gaps = cur.fetchall()

    # Function 25: Rating Distribution Histogram
    cur.execute(
        """
        SELECT
            rating_bucket,
            sort_key,
            rating_count,
            ROUND(rating_count * 100.0 / SUM(rating_count) OVER (), 1) AS percentage
        FROM (
            SELECT
                CASE
                    WHEN rating_value BETWEEN 1 AND 2  THEN '1-2  (Very Low)'
                    WHEN rating_value BETWEEN 3 AND 4  THEN '3-4  (Below Average)'
                    WHEN rating_value BETWEEN 5 AND 6  THEN '5-6  (Average)'
                    WHEN rating_value BETWEEN 7 AND 8  THEN '7-8  (Good)'
                    ELSE                                    '9-10 (Excellent)'
                END                AS rating_bucket,
                MIN(rating_value)  AS sort_key,
                COUNT(*)           AS rating_count
            FROM user_rating
            GROUP BY 1
        ) buckets
        ORDER BY sort_key
        """
    )
    rating_distribution = cur.fetchall()

    cur.close()
    conn.close()
    return render_template(
        "admin/ratings.html", most_rated=most_rated, rating_gaps=rating_gaps,
        rating_distribution=rating_distribution
    )


@app.route("/admin/genres")
@admin_required
def admin_genres():
    conn = get_db()
    cur = dict_cursor(conn)
    cur.execute(
        """
        SELECT g.genre_name,
               COUNT(ur.movie_id) AS rating_count,
               ROUND(AVG(ur.rating_value), 2) AS average_user_rating
        FROM user_rating ur
        JOIN movie_genre mg ON ur.movie_id = mg.movie_id
        JOIN genre g ON mg.genre_id = g.genre_id
        GROUP BY g.genre_id, g.genre_name
        ORDER BY rating_count DESC
        """
    )
    genres = cur.fetchall()

    # Function 26: Genre Performance Deep Analysis with ranking
    cur.execute(
        """
        WITH genre_metrics AS (
            SELECT
                g.genre_name,
                COUNT(DISTINCT m.movie_id)              AS total_movies,
                COUNT(ur.movie_id)                      AS total_user_ratings,
                ROUND(AVG(m.vote_average), 2)           AS avg_tmdb_rating,
                ROUND(COALESCE(AVG(ur.rating_value), 0), 2) AS avg_user_rating,
                MAX(m.vote_average)                     AS best_tmdb_rating,
                ROUND(
                    COALESCE(AVG(ur.rating_value), 0) - AVG(m.vote_average),
                    2
                )                                       AS user_vs_tmdb_gap
            FROM genre g
            JOIN movie_genre mg ON g.genre_id = mg.genre_id
            JOIN movie m        ON mg.movie_id = m.movie_id
            LEFT JOIN user_rating ur ON m.movie_id = ur.movie_id
            GROUP BY g.genre_id, g.genre_name
        )
        SELECT *,
            RANK() OVER (ORDER BY avg_tmdb_rating    DESC) AS tmdb_rating_rank,
            RANK() OVER (ORDER BY total_user_ratings DESC) AS popularity_rank,
            RANK() OVER (ORDER BY total_movies       DESC) AS volume_rank
        FROM genre_metrics
        ORDER BY total_user_ratings DESC
        """
    )
    genre_deep = cur.fetchall()

    cur.close()
    conn.close()
    return render_template("admin/genres.html", genres=genres, genre_deep=genre_deep)


@app.route("/admin/keywords")
@admin_required
def admin_keywords():
    conn = get_db()
    cur = dict_cursor(conn)
    cur.execute(
        """
        SELECT k.keyword_name,
               COUNT(*) AS rating_count,
               ROUND(AVG(ur.rating_value), 2) AS average_user_rating
        FROM user_rating ur
        JOIN movie_keyword mk ON ur.movie_id = mk.movie_id
        JOIN keyword k ON mk.keyword_id = k.keyword_id
        GROUP BY k.keyword_id, k.keyword_name
        HAVING COUNT(*) >= 2
        ORDER BY average_user_rating DESC, rating_count DESC
        LIMIT 30
        """
    )
    keywords = cur.fetchall()
    cur.close()
    conn.close()
    return render_template("admin/keywords.html", keywords=keywords)


@app.route("/admin/companies")
@admin_required
def admin_companies():
    conn = get_db()
    cur = dict_cursor(conn)
    cur.execute(
        """
        SELECT c.company_name,
               COUNT(DISTINCT m.movie_id) AS movie_count,
               ROUND(AVG(m.vote_average), 2) AS average_tmdb_rating,
               ROUND(AVG(m.popularity), 2) AS average_popularity
        FROM company c
        JOIN movie_company mc ON c.company_id = mc.company_id
        JOIN movie m ON mc.movie_id = m.movie_id
        GROUP BY c.company_id, c.company_name
        HAVING COUNT(DISTINCT m.movie_id) >= 2
        ORDER BY average_tmdb_rating DESC, movie_count DESC
        LIMIT 30
        """
    )
    companies = cur.fetchall()

    # Function 27: Company Portfolio Analysis — diversity + quality score
    cur.execute(
        """
        WITH company_portfolio AS (
            SELECT
                c.company_id,
                c.company_name,
                COUNT(DISTINCT m.movie_id)              AS total_movies,
                COUNT(DISTINCT g.genre_id)              AS distinct_genres,
                ROUND(AVG(m.vote_average), 2)           AS avg_rating,
                ROUND(AVG(m.popularity), 2)             AS avg_popularity,
                MAX(m.vote_average)                     AS best_movie_rating,
                SUM(CASE WHEN m.vote_average >= 7 THEN 1 ELSE 0 END) AS quality_movies
            FROM company c
            JOIN movie_company mc ON c.company_id = mc.company_id
            JOIN movie m          ON mc.movie_id  = m.movie_id
            JOIN movie_genre mg   ON m.movie_id   = mg.movie_id
            JOIN genre g          ON mg.genre_id  = g.genre_id
            GROUP BY c.company_id, c.company_name
            HAVING COUNT(DISTINCT m.movie_id) >= 3
        )
        SELECT *,
            ROUND(quality_movies * 100.0 / NULLIF(total_movies, 0), 1) AS quality_pct,
            ROUND(distinct_genres * 1.0  / NULLIF(total_movies, 0), 2) AS genre_diversity_score,
            RANK() OVER (ORDER BY avg_rating DESC)                      AS rating_rank
        FROM company_portfolio
        ORDER BY avg_rating DESC
        LIMIT 20
        """
    )
    company_portfolio = cur.fetchall()

    cur.close()
    conn.close()
    return render_template("admin/companies.html", companies=companies,
                           company_portfolio=company_portfolio)


@app.route("/admin/reviews")
@admin_required
def admin_reviews():
    conn = get_db()
    cur = dict_cursor(conn)
    cur.execute(
        """
        SELECT m.movie_id, m.title,
               COUNT(r.review_id) AS review_count,
               ROUND(AVG(r.author_rating), 2) AS average_review_author_rating
        FROM movie m
        LEFT JOIN review r ON m.movie_id = r.movie_id
        GROUP BY m.movie_id
        ORDER BY review_count DESC
        LIMIT 20
        """
    )
    reviews = cur.fetchall()
    cur.close()
    conn.close()
    return render_template("admin/reviews.html", reviews=reviews)


@app.route("/admin/quality")
@admin_required
def admin_quality():
    conn = get_db()
    cur = dict_cursor(conn)

    cur.execute(
        """
        SELECT m.movie_id, m.title
        FROM movie m
        LEFT JOIN movie_keyword mk ON m.movie_id = mk.movie_id
        WHERE mk.keyword_id IS NULL
        ORDER BY m.movie_id
        LIMIT 50
        """
    )
    missing_keywords = cur.fetchall()

    # Pre-aggregate each table separately before joining to avoid row explosion
    cur.execute(
        """
        SELECT
            m.movie_id,
            m.title,
            COALESCE(g.cnt,  0) AS genre_count,
            COALESCE(k.cnt,  0) AS keyword_count,
            COALESCE(c.cnt,  0) AS cast_count,
            COALESCE(cr.cnt, 0) AS crew_count,
            COALESCE(co.cnt, 0) AS company_count,
            COALESCE(r.cnt,  0) AS review_count
        FROM movie m
        LEFT JOIN (SELECT movie_id, COUNT(*) AS cnt FROM movie_genre   GROUP BY movie_id) g  ON m.movie_id = g.movie_id
        LEFT JOIN (SELECT movie_id, COUNT(*) AS cnt FROM movie_keyword  GROUP BY movie_id) k  ON m.movie_id = k.movie_id
        LEFT JOIN (SELECT movie_id, COUNT(*) AS cnt FROM movie_cast     GROUP BY movie_id) c  ON m.movie_id = c.movie_id
        LEFT JOIN (SELECT movie_id, COUNT(*) AS cnt FROM movie_crew     GROUP BY movie_id) cr ON m.movie_id = cr.movie_id
        LEFT JOIN (SELECT movie_id, COUNT(*) AS cnt FROM movie_company  GROUP BY movie_id) co ON m.movie_id = co.movie_id
        LEFT JOIN (SELECT movie_id, COUNT(*) AS cnt FROM review         GROUP BY movie_id) r  ON m.movie_id = r.movie_id
        ORDER BY keyword_count ASC, cast_count ASC, review_count ASC
        LIMIT 50
        """
    )
    coverage = cur.fetchall()

    cur.close()
    conn.close()
    return render_template(
        "admin/data_quality.html",
        missing_keywords=missing_keywords,
        coverage=coverage,
    )


if __name__ == "__main__":
    app.run(debug=True, port=5000)
