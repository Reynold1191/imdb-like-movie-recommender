# TMDB SQL Functions Reference

All 27 SQL queries used by the application, with page location, general template, and specific examples.

For project overview, architecture, and how to run → see [`README.md`](README.md)

---

## Function 1: Login with TMDB Account Username

**Goal:** Verify username + password to authenticate a user.
**Page:** User site → Login page (`/login`)

<details>
<summary>Show SQL Code</summary>

```sql
SELECT
    account_id,
    username,
    display_name,
    avatar_path
FROM tmdb_account
WHERE username = :username
  AND account_id = :account_id;
-- Password is always '1' in this demo — checked in application logic
```

</details>

---

## Function 2: Home Page — Top 10 Movies Overall

**Goal:** Show top 10 movies by TMDB rating and popularity.
**Page:** User site → Home page (`/`)

<details>
<summary>Show SQL Code</summary>

```sql
SELECT
    movie_id,
    title,
    release_date,
    vote_average,
    vote_count,
    popularity,
    poster_path
FROM movie
WHERE vote_count >= 100
ORDER BY vote_average DESC, popularity DESC
LIMIT 10;
```

</details>

---

## Function 3: Top Movies in Each Genre

**Goal:** Show top-rated movies grouped by genre using a window function.
**Page:** User site → Home page (`/`) — genre rows section

<details>
<summary>Show SQL Code</summary>

```sql
WITH ranked_movies AS (
    SELECT
        g.genre_name,
        m.movie_id,
        m.title,
        m.release_date,
        m.vote_average,
        m.vote_count,
        m.popularity,
        ROW_NUMBER() OVER (
            PARTITION BY g.genre_id
            ORDER BY m.vote_average DESC, m.popularity DESC
        ) AS genre_rank
    FROM movie m
    JOIN movie_genre mg ON m.movie_id = mg.movie_id
    JOIN genre g ON mg.genre_id = g.genre_id
    WHERE m.vote_count >= 100
)
SELECT *
FROM ranked_movies
WHERE genre_rank <= 8
ORDER BY genre_name, genre_rank;
```

</details>

---

## Function 4: Browse / Search Movies

**Goal:** Search movies by title, genre, keyword, or company. Supports optional filters for genre, release year range, and minimum rating.
**Page:** User site → Browse page (`/browse`)

<details>
<summary>Show SQL Code</summary>

**General template (all possible WHERE clauses):**

```sql
SELECT DISTINCT
    m.movie_id,
    m.title,
    m.release_date,
    m.vote_average,
    m.popularity,
    m.poster_path
FROM movie m
LEFT JOIN movie_genre mg ON m.movie_id = mg.movie_id
LEFT JOIN genre g ON mg.genre_id = g.genre_id
LEFT JOIN movie_keyword mk ON m.movie_id = mk.movie_id
LEFT JOIN keyword k ON mk.keyword_id = k.keyword_id
LEFT JOIN movie_company mc ON m.movie_id = mc.movie_id
LEFT JOIN company c ON mc.company_id = c.company_id
WHERE
    (
        LOWER(m.title) LIKE LOWER('%:q%')
        OR LOWER(g.genre_name) LIKE LOWER('%:q%')
        OR LOWER(k.keyword_name) LIKE LOWER('%:q%')
        OR LOWER(c.company_name) LIKE LOWER('%:q%')
    )
    -- [if genre filter active]:
    AND g.genre_name = ':genre'
    -- [if year_from active]:
    AND EXTRACT(YEAR FROM m.release_date) >= :year_from
    -- [if year_to active]:
    AND EXTRACT(YEAR FROM m.release_date) <= :year_to
    -- [if min_rating active]:
    AND m.vote_average >= :min_rating
ORDER BY m.popularity DESC
LIMIT 60;
```

**Specific example — keyword "health", year from 2010, min rating 6:**

```sql
SELECT DISTINCT
    m.movie_id, m.title, m.release_date,
    m.vote_average, m.popularity, m.poster_path
FROM movie m
LEFT JOIN movie_genre mg ON m.movie_id = mg.movie_id
LEFT JOIN genre g ON mg.genre_id = g.genre_id
LEFT JOIN movie_keyword mk ON m.movie_id = mk.movie_id
LEFT JOIN keyword k ON mk.keyword_id = k.keyword_id
LEFT JOIN movie_company mc ON m.movie_id = mc.movie_id
LEFT JOIN company c ON mc.company_id = c.company_id
WHERE
    (
        LOWER(m.title) LIKE LOWER('%health%')
        OR LOWER(g.genre_name) LIKE LOWER('%health%')
        OR LOWER(k.keyword_name) LIKE LOWER('%health%')
        OR LOWER(c.company_name) LIKE LOWER('%health%')
    )
    AND EXTRACT(YEAR FROM m.release_date) >= 2010
    AND m.vote_average >= 6
ORDER BY m.popularity DESC
LIMIT 60;
```

</details>

---

## Function 5: Movie Detail Page

**Goal:** Load full metadata for one movie including genres, companies, and keywords via STRING_AGG.
**Page:** User site → Movie Detail page (`/movie/<movie_id>`)

<details>
<summary>Show SQL Code</summary>

**General template:**

```sql
SELECT
    m.movie_id, m.title, m.overview, m.release_date, m.runtime,
    m.vote_average, m.vote_count, m.popularity,
    m.poster_path, m.backdrop_path, m.tagline, m.budget, m.revenue,
    STRING_AGG(DISTINCT g.genre_name, ', ' ORDER BY g.genre_name)    AS genres,
    STRING_AGG(DISTINCT c.company_name, ', ' ORDER BY c.company_name) AS companies,
    STRING_AGG(DISTINCT k.keyword_name, ', ' ORDER BY k.keyword_name) AS keywords
FROM movie m
LEFT JOIN movie_genre mg   ON m.movie_id = mg.movie_id
LEFT JOIN genre g          ON mg.genre_id = g.genre_id
LEFT JOIN movie_company mc ON m.movie_id = mc.movie_id
LEFT JOIN company c        ON mc.company_id = c.company_id
LEFT JOIN movie_keyword mk ON m.movie_id = mk.movie_id
LEFT JOIN keyword k        ON mk.keyword_id = k.keyword_id
WHERE m.movie_id = :movie_id
GROUP BY m.movie_id;
```

**Specific example — movie_id = 680 ("Pulp Fiction"):**

```sql
-- Executed with movie_id = 680 ("Pulp Fiction")
SELECT
    m.movie_id, m.title, m.overview, m.release_date, m.runtime,
    m.vote_average, m.vote_count, m.popularity,
    m.poster_path, m.backdrop_path, m.tagline, m.budget, m.revenue,
    STRING_AGG(DISTINCT g.genre_name, ', ' ORDER BY g.genre_name)    AS genres,
    STRING_AGG(DISTINCT c.company_name, ', ' ORDER BY c.company_name) AS companies,
    STRING_AGG(DISTINCT k.keyword_name, ', ' ORDER BY k.keyword_name) AS keywords
FROM movie m
LEFT JOIN movie_genre mg   ON m.movie_id = mg.movie_id
LEFT JOIN genre g          ON mg.genre_id = g.genre_id
LEFT JOIN movie_company mc ON m.movie_id = mc.movie_id
LEFT JOIN company c        ON mc.company_id = c.company_id
LEFT JOIN movie_keyword mk ON m.movie_id = mk.movie_id
LEFT JOIN keyword k        ON mk.keyword_id = k.keyword_id
WHERE m.movie_id = 680
GROUP BY m.movie_id;
```

</details>

---

## Function 6: Cast and Crew for a Movie

**Goal:** Show actors (with character names) and crew members (with department and job) for one movie.
**Page:** User site → Movie Detail page (`/movie/<movie_id>`) — cast & crew sections

<details>
<summary>Show SQL Code</summary>

**General template:**

```sql
-- Cast query
SELECT p.person_id, p.name, mc.character_name, mc.cast_order
FROM movie_cast mc
JOIN person p ON mc.person_id = p.person_id
WHERE mc.movie_id = :movie_id
ORDER BY mc.cast_order ASC
LIMIT 15;

-- Crew query
SELECT p.person_id, p.name, mcr.department, mcr.job_title
FROM movie_crew mcr
JOIN person p ON mcr.person_id = p.person_id
WHERE mcr.movie_id = :movie_id
ORDER BY mcr.department, mcr.job_title
LIMIT 20;
```

**Specific example — movie_id = 680 ("Pulp Fiction"):**

```sql
SELECT p.person_id, p.name, mc.character_name, mc.cast_order
FROM movie_cast mc
JOIN person p ON mc.person_id = p.person_id
WHERE mc.movie_id = 680
ORDER BY mc.cast_order ASC
LIMIT 15;

SELECT p.person_id, p.name, mcr.department, mcr.job_title
FROM movie_crew mcr
JOIN person p ON mcr.person_id = p.person_id
WHERE mcr.movie_id = 680
ORDER BY mcr.department, mcr.job_title
LIMIT 20;
```

</details>

---

## Function 7: Movie Reviews

**Goal:** Show all reviews for the selected movie ordered by date.
**Page:** User site → Movie Detail page (`/movie/<movie_id>`) — reviews section

<details>
<summary>Show SQL Code</summary>

**General template:**

```sql
SELECT
    review_id, author_name, author_username,
    author_rating, content, created_at, updated_at, review_url
FROM review
WHERE movie_id = :movie_id
ORDER BY created_at DESC;
```

**Specific example — movie_id = 680 ("Pulp Fiction"):**

```sql
SELECT
    review_id, author_name, author_username,
    author_rating, content, created_at, updated_at, review_url
FROM review
WHERE movie_id = 680
ORDER BY created_at DESC;
```

</details>

---

## Function 8: User Profile Summary

**Goal:** Show account profile with total ratings and average rating given.
**Page:** User site → Profile page (`/profile`)

<details>
<summary>Show SQL Code</summary>

**General template:**

```sql
SELECT
    a.account_id,
    a.username,
    a.display_name,
    a.avatar_path,
    COUNT(ur.movie_id)             AS total_rated_movies,
    ROUND(AVG(ur.rating_value), 2) AS average_rating_given
FROM tmdb_account a
LEFT JOIN user_rating ur ON a.account_id = ur.account_id
WHERE a.account_id = :account_id
GROUP BY a.account_id;
```

**Specific example — account_id = 1 (user: r96sk):**

```sql
SELECT
    a.account_id, a.username, a.display_name, a.avatar_path,
    COUNT(ur.movie_id)             AS total_rated_movies,
    ROUND(AVG(ur.rating_value), 2) AS average_rating_given
FROM tmdb_account a
LEFT JOIN user_rating ur ON a.account_id = ur.account_id
WHERE a.account_id = 1
GROUP BY a.account_id;
```

</details>

---

## Function 9: My Ratings

**Goal:** Show all movies rated by the logged-in account with comparison to TMDB average.
**Page:** User site → My Ratings page (`/my-ratings`)

<details>
<summary>Show SQL Code</summary>

**General template:**

```sql
SELECT
    m.movie_id, m.title, m.release_date,
    m.vote_average    AS tmdb_average,
    ur.rating_value   AS my_rating,
    ur.created_at
FROM user_rating ur
JOIN movie m ON ur.movie_id = m.movie_id
WHERE ur.account_id = :account_id
ORDER BY ur.created_at DESC;
```

**Specific example — account_id = 1 (user: r96sk):**

```sql
SELECT
    m.movie_id, m.title, m.release_date,
    m.vote_average    AS tmdb_average,
    ur.rating_value   AS my_rating,
    ur.created_at
FROM user_rating ur
JOIN movie m ON ur.movie_id = m.movie_id
WHERE ur.account_id = 1
ORDER BY ur.created_at DESC;
```

</details>

---

## Function 10: Personalized Recommendations

**Goal:** Find genres the user rates ≥7.5 on average (CTE), then recommend unwatched movies from those genres.
**Page:** User site → Home page (`/`) — "Recommended for You" section

<details>
<summary>Show SQL Code</summary>

**General template:**

```sql
WITH favorite_genres AS (
    SELECT mg.genre_id
    FROM user_rating ur
    JOIN movie_genre mg ON ur.movie_id = mg.movie_id
    WHERE ur.account_id = :account_id
    GROUP BY mg.genre_id
    HAVING AVG(ur.rating_value) >= 7.5
)
SELECT DISTINCT
    m.movie_id, m.title, m.release_date,
    m.vote_average, m.popularity
FROM movie m
JOIN movie_genre mg ON m.movie_id = mg.movie_id
JOIN favorite_genres fg ON mg.genre_id = fg.genre_id
WHERE m.movie_id NOT IN (
    SELECT movie_id FROM user_rating WHERE account_id = :account_id
)
ORDER BY m.vote_average DESC, m.popularity DESC
LIMIT 20;
```

**Specific example — account_id = 1 (user: r96sk):**

```sql
WITH favorite_genres AS (
    SELECT mg.genre_id
    FROM user_rating ur
    JOIN movie_genre mg ON ur.movie_id = mg.movie_id
    WHERE ur.account_id = 1
    GROUP BY mg.genre_id
    HAVING AVG(ur.rating_value) >= 7.5
)
SELECT DISTINCT
    m.movie_id, m.title, m.release_date,
    m.vote_average, m.popularity
FROM movie m
JOIN movie_genre mg ON m.movie_id = mg.movie_id
JOIN favorite_genres fg ON mg.genre_id = fg.genre_id
WHERE m.movie_id NOT IN (
    SELECT movie_id FROM user_rating WHERE account_id = 1
)
ORDER BY m.vote_average DESC, m.popularity DESC
LIMIT 20;
```

</details>

---

## Function 11: Similar Movies by Shared Keywords

**Goal:** Self-join `movie_keyword` to find movies sharing the most keywords with the current movie.
**Page:** User site → Movie Detail page (`/movie/<movie_id>`) — "Similar Movies" sidebar

<details>
<summary>Show SQL Code</summary>

**General template:**

```sql
SELECT
    m2.movie_id, m2.title,
    m2.vote_average,
    COUNT(*) AS shared_keyword_count
FROM movie_keyword mk1
JOIN movie_keyword mk2 ON mk1.keyword_id = mk2.keyword_id
JOIN movie m2 ON mk2.movie_id = m2.movie_id
WHERE mk1.movie_id = :movie_id
  AND mk2.movie_id <> :movie_id
GROUP BY m2.movie_id
ORDER BY shared_keyword_count DESC, m2.vote_average DESC
LIMIT 8;
```

**Specific example — movie_id = 680 ("Pulp Fiction"):**

```sql
SELECT
    m2.movie_id, m2.title,
    m2.vote_average,
    COUNT(*) AS shared_keyword_count
FROM movie_keyword mk1
JOIN movie_keyword mk2 ON mk1.keyword_id = mk2.keyword_id
JOIN movie m2 ON mk2.movie_id = m2.movie_id
WHERE mk1.movie_id = 680
  AND mk2.movie_id <> 680
GROUP BY m2.movie_id
ORDER BY shared_keyword_count DESC, m2.vote_average DESC
LIMIT 8;
```

</details>

---

## Function 12: Similar Movies by Same Cast

**Goal:** Self-join `movie_cast` to find movies that share the most actors with the current movie.
**Page:** User site → Movie Detail page (`/movie/<movie_id>`) — "More with similar cast" sidebar

<details>
<summary>Show SQL Code</summary>

```sql
SELECT
    m2.movie_id, m2.title,
    COUNT(*) AS shared_actor_count,
    m2.vote_average
FROM movie_cast mc1
JOIN movie_cast mc2 ON mc1.person_id = mc2.person_id
JOIN movie m2 ON mc2.movie_id = m2.movie_id
WHERE mc1.movie_id = :movie_id
  AND mc2.movie_id <> :movie_id
GROUP BY m2.movie_id
ORDER BY shared_actor_count DESC, m2.vote_average DESC
LIMIT 10;
```

</details>

---

## Function 13: Admin Dashboard Summary

**Goal:** Single-row system-wide stats using scalar subqueries.
**Page:** Admin site → Dashboard (`/admin/`)

<details>
<summary>Show SQL Code</summary>

```sql
SELECT
    (SELECT COUNT(*) FROM movie)        AS total_movies,
    (SELECT COUNT(*) FROM tmdb_account) AS total_accounts,
    (SELECT COUNT(*) FROM review)       AS total_reviews,
    (SELECT COUNT(*) FROM user_rating)  AS total_user_ratings,
    (SELECT COUNT(*) FROM person)       AS total_people,
    (SELECT COUNT(*) FROM keyword)      AS total_keywords,
    (SELECT COUNT(*) FROM company)      AS total_companies;
```

</details>

---

## Function 14: Admin Users Table

**Goal:** All TMDB accounts with their rating count and average.
**Page:** Admin site → Users (`/admin/users`)

<details>
<summary>Show SQL Code</summary>

```sql
SELECT
    a.account_id,
    a.username,
    a.display_name,
    COUNT(ur.movie_id)             AS rating_count,
    ROUND(AVG(ur.rating_value), 2) AS average_rating
FROM tmdb_account a
LEFT JOIN user_rating ur ON a.account_id = ur.account_id
GROUP BY a.account_id
ORDER BY rating_count DESC;
```

</details>

---

## Function 15: Most Rated Movies by Users

**Goal:** Movies ranked by how many user ratings they have received.
**Page:** Admin site → Ratings Analytics (`/admin/ratings`)

<details>
<summary>Show SQL Code</summary>

```sql
SELECT
    m.movie_id, m.title,
    COUNT(ur.account_id)           AS user_rating_count,
    ROUND(AVG(ur.rating_value), 2) AS average_user_rating,
    m.vote_average                 AS tmdb_average
FROM movie m
JOIN user_rating ur ON m.movie_id = ur.movie_id
GROUP BY m.movie_id
ORDER BY user_rating_count DESC, average_user_rating DESC
LIMIT 20;
```

</details>

---

## Function 16: Compare User Ratings vs TMDB Average

**Goal:** Find movies where local user ratings most differ from TMDB's public score. Uses `ABS()` on the gap for ordering.
**Page:** Admin site → Ratings Analytics (`/admin/ratings`) — "Biggest Rating Disagreements" section

<details>
<summary>Show SQL Code</summary>

```sql
SELECT
    m.movie_id, m.title,
    m.vote_average                            AS tmdb_average,
    ROUND(AVG(ur.rating_value), 2)            AS local_average,
    ROUND(AVG(ur.rating_value) - m.vote_average, 2) AS rating_gap,
    COUNT(ur.account_id)                      AS local_rating_count
FROM movie m
JOIN user_rating ur ON m.movie_id = ur.movie_id
GROUP BY m.movie_id
HAVING COUNT(ur.account_id) >= 3
ORDER BY ABS(AVG(ur.rating_value) - m.vote_average) DESC
LIMIT 20;
```

</details>

---

## Function 17: Genre Analytics

**Goal:** Genres ranked by total user rating activity and average rating given.
**Page:** Admin site → Genre Analytics (`/admin/genres`)

<details>
<summary>Show SQL Code</summary>

```sql
SELECT
    g.genre_name,
    COUNT(ur.movie_id)             AS rating_count,
    ROUND(AVG(ur.rating_value), 2) AS average_user_rating
FROM user_rating ur
JOIN movie_genre mg ON ur.movie_id = mg.movie_id
JOIN genre g ON mg.genre_id = g.genre_id
GROUP BY g.genre_id, g.genre_name
ORDER BY rating_count DESC;
```

</details>

---

## Function 18: Keyword Analytics

**Goal:** Keywords associated with highly-rated movies, filtered to those with sufficient data.
**Page:** Admin site → Keyword Analytics (`/admin/keywords`)

<details>
<summary>Show SQL Code</summary>

```sql
SELECT
    k.keyword_name,
    COUNT(*)                       AS rating_count,
    ROUND(AVG(ur.rating_value), 2) AS average_user_rating
FROM user_rating ur
JOIN movie_keyword mk ON ur.movie_id = mk.movie_id
JOIN keyword k ON mk.keyword_id = k.keyword_id
GROUP BY k.keyword_id, k.keyword_name
HAVING COUNT(*) >= 2
ORDER BY average_user_rating DESC, rating_count DESC
LIMIT 30;
```

</details>

---

## Function 19: Company Analytics

**Goal:** Production companies with the highest average TMDB ratings, filtered to those with ≥2 movies.
**Page:** Admin site → Company Analytics (`/admin/companies`)

<details>
<summary>Show SQL Code</summary>

```sql
SELECT
    c.company_name,
    COUNT(DISTINCT m.movie_id)     AS movie_count,
    ROUND(AVG(m.vote_average), 2)  AS average_tmdb_rating,
    ROUND(AVG(m.popularity), 2)    AS average_popularity
FROM company c
JOIN movie_company mc ON c.company_id = mc.company_id
JOIN movie m ON mc.movie_id = m.movie_id
GROUP BY c.company_id, c.company_name
HAVING COUNT(DISTINCT m.movie_id) >= 2
ORDER BY average_tmdb_rating DESC, movie_count DESC
LIMIT 30;
```

</details>

---

## Function 20: Review Analytics

**Goal:** Movies ranked by review count with average author rating.
**Page:** Admin site → Review Analytics (`/admin/reviews`)

<details>
<summary>Show SQL Code</summary>

```sql
SELECT
    m.movie_id, m.title,
    COUNT(r.review_id)              AS review_count,
    ROUND(AVG(r.author_rating), 2)  AS average_review_author_rating
FROM movie m
LEFT JOIN review r ON m.movie_id = r.movie_id
GROUP BY m.movie_id
ORDER BY review_count DESC
LIMIT 20;
```

</details>

---

## Function 21: Data Quality — Movies Missing Keywords

**Goal:** Find movies with no keyword data using a LEFT JOIN null check.
**Page:** Admin site → Data Quality (`/admin/quality`)

<details>
<summary>Show SQL Code</summary>

```sql
SELECT m.movie_id, m.title
FROM movie m
LEFT JOIN movie_keyword mk ON m.movie_id = mk.movie_id
WHERE mk.keyword_id IS NULL
ORDER BY m.movie_id;
```

</details>

---

## Function 22: Data Quality — Movie Coverage Report

**Goal:** Check how complete each movie record is across 6 metadata tables.

> **Performance note:** Naive approach joining all 6 tables simultaneously causes a Cartesian product explosion (cast × crew × keywords = millions of rows per movie). The correct approach pre-aggregates each table in a subquery before joining.

**Page:** Admin site → Data Quality (`/admin/quality`) — coverage report section

<details>
<summary>Show SQL Code</summary>

```sql
-- Each table is pre-aggregated before joining — avoids row-count explosion
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
LIMIT 50;
```

</details>

---

## Function 23: Movie Release Trend Analysis

**Goal:** Time-series view of catalog growth per year — movie count, average rating, and share of high-quality films. Uses `EXTRACT`, `CASE SUM`, and `GROUP BY`.
**Page:** Admin site → Dashboard (`/admin/`)

<details>
<summary>Show SQL Code</summary>

```sql
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
LIMIT 20;
```

</details>

---

## Function 24: User Engagement Ranking

**Goal:** Rank users by activity and average rating using `RANK() OVER`. Also computes `STDDEV` (rating consistency) and bias vs. TMDB average per user.
**Page:** Admin site → Users (`/admin/users`)

<details>
<summary>Show SQL Code</summary>

```sql
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
ORDER BY total_ratings DESC NULLS LAST;
```

</details>

---

## Function 25: Rating Distribution Histogram

**Goal:** Bucket all user ratings into tiers using `CASE`, then compute each tier's percentage share using `SUM() OVER ()`.
**Page:** Admin site → Ratings Analytics (`/admin/ratings`)

<details>
<summary>Show SQL Code</summary>

```sql
SELECT
    rating_bucket,
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
ORDER BY sort_key;
```

</details>

---

## Function 26: Genre Performance Deep Analysis

**Goal:** Multi-metric genre analysis using a CTE and three independent `RANK() OVER` windows — ranking each genre by TMDB quality, user popularity, and catalog volume separately.
**Page:** Admin site → Genre Analytics (`/admin/genres`)

<details>
<summary>Show SQL Code</summary>

```sql
WITH genre_metrics AS (
    SELECT
        g.genre_name,
        COUNT(DISTINCT m.movie_id)                  AS total_movies,
        COUNT(ur.movie_id)                          AS total_user_ratings,
        ROUND(AVG(m.vote_average), 2)               AS avg_tmdb_rating,
        ROUND(COALESCE(AVG(ur.rating_value), 0), 2) AS avg_user_rating,
        MAX(m.vote_average)                         AS best_tmdb_rating,
        ROUND(
            COALESCE(AVG(ur.rating_value), 0) - AVG(m.vote_average),
            2
        )                                           AS user_vs_tmdb_gap
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
ORDER BY total_user_ratings DESC;
```

</details>

---

## Function 27: Company Portfolio Analysis

**Goal:** Evaluate production companies with computed `quality_pct` (% movies ≥7), `genre_diversity_score` (distinct genres ÷ total movies), and `RANK() OVER` for quality ranking. Requires ≥3 movies per company.
**Page:** Admin site → Company Analytics (`/admin/companies`)

<details>
<summary>Show SQL Code</summary>

```sql
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
LIMIT 20;
```

</details>

---

*For project overview, architecture, user/admin site flow, and how to run → see [`README.md`](README.md)*
