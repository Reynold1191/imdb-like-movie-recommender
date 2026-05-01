# TMDB SQL Functions Reference

All **32** SQL queries used by the application, with page location, general template, and specific examples.

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

**Goal:** Show up to eight top-rated movies per genre using a correlated `COUNT(*)` subquery (equivalent to per-genre `ROW_NUMBER`, without window functions).
**Page:** User site → Home page (`/`) — genre rows section

<details>
<summary>Show SQL Code</summary>

```sql
SELECT g.genre_name, m.movie_id, m.title, m.release_date,
    m.vote_average, m.poster_path
FROM movie m
JOIN movie_genre mg ON m.movie_id = mg.movie_id
JOIN genre g ON mg.genre_id = g.genre_id
WHERE m.vote_count >= 100
  AND (
      SELECT COUNT(*)
      FROM movie m2
      JOIN movie_genre mg2 ON m2.movie_id = mg2.movie_id
      WHERE mg2.genre_id = g.genre_id
        AND m2.vote_count >= 100
        AND (
            m2.vote_average > m.vote_average
            OR (m2.vote_average = m.vote_average AND m2.popularity > m.popularity)
            OR (
                m2.vote_average = m.vote_average
                AND m2.popularity = m.popularity
                AND m2.movie_id < m.movie_id
            )
        )
  ) < 8
ORDER BY genre_name, m.vote_average DESC, m.popularity DESC, m.movie_id;
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

**Specific example — account_id = 1 (user: JPV852):**

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

**Specific example — account_id = 1 (user: JPV852):**

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

**Goal:** Build a genre pool from ratings (strong genres if any have average ≥7.5, otherwise the top eight genres by the user’s average), then recommend unwatched titles; **cold start** users with no ratings get popular unseen movies.
**Page:** User site → Home page (`/`) — "Recommended for You" section

<details>
<summary>Show SQL Code</summary>

**General template:**

```sql
WITH genre_avg AS (
    SELECT mg.genre_id, AVG(ur.rating_value) AS avg_user_rating
    FROM user_rating ur
    JOIN movie_genre mg ON ur.movie_id = mg.movie_id
    WHERE ur.account_id = :account_id
    GROUP BY mg.genre_id
),
fav_genres AS (
    SELECT genre_id FROM genre_avg WHERE avg_user_rating >= 7.5
    UNION
    SELECT ga.genre_id
    FROM genre_avg ga
    WHERE NOT EXISTS (SELECT 1 FROM genre_avg WHERE avg_user_rating >= 7.5)
      AND ga.genre_id IN (
          SELECT ga2.genre_id FROM genre_avg ga2
          ORDER BY ga2.avg_user_rating DESC
          LIMIT 8
      )
)
SELECT * FROM (
    SELECT DISTINCT
        m.movie_id, m.title, m.release_date,
        m.vote_average, m.popularity, m.poster_path
    FROM movie m
    JOIN movie_genre mg ON m.movie_id = mg.movie_id
    JOIN fav_genres fg ON mg.genre_id = fg.genre_id
    WHERE m.movie_id NOT IN (
        SELECT movie_id FROM user_rating WHERE account_id = :account_id
    )
      AND EXISTS (SELECT 1 FROM genre_avg)
    UNION ALL
    SELECT m.movie_id, m.title, m.release_date,
           m.vote_average, m.popularity, m.poster_path
    FROM movie m
    WHERE m.movie_id NOT IN (
        SELECT movie_id FROM user_rating WHERE account_id = :account_id
    )
      AND NOT EXISTS (SELECT 1 FROM genre_avg)
      AND m.vote_count >= 100
) rec
ORDER BY rec.vote_average DESC NULLS LAST, rec.popularity DESC NULLS LAST
LIMIT 20;
```

**Specific example — account_id = 1 (user: JPV852):**

```sql
WITH genre_avg AS (
    SELECT mg.genre_id, AVG(ur.rating_value) AS avg_user_rating
    FROM user_rating ur
    JOIN movie_genre mg ON ur.movie_id = mg.movie_id
    WHERE ur.account_id = 1
    GROUP BY mg.genre_id
),
fav_genres AS (
    SELECT genre_id FROM genre_avg WHERE avg_user_rating >= 7.5
    UNION
    SELECT ga.genre_id
    FROM genre_avg ga
    WHERE NOT EXISTS (SELECT 1 FROM genre_avg WHERE avg_user_rating >= 7.5)
      AND ga.genre_id IN (
          SELECT ga2.genre_id FROM genre_avg ga2
          ORDER BY ga2.avg_user_rating DESC
          LIMIT 8
      )
)
SELECT * FROM (
    SELECT DISTINCT
        m.movie_id, m.title, m.release_date,
        m.vote_average, m.popularity, m.poster_path
    FROM movie m
    JOIN movie_genre mg ON m.movie_id = mg.movie_id
    JOIN fav_genres fg ON mg.genre_id = fg.genre_id
    WHERE m.movie_id NOT IN (
        SELECT movie_id FROM user_rating WHERE account_id = 1
    )
      AND EXISTS (SELECT 1 FROM genre_avg)
    UNION ALL
    SELECT m.movie_id, m.title, m.release_date,
           m.vote_average, m.popularity, m.poster_path
    FROM movie m
    WHERE m.movie_id NOT IN (
        SELECT movie_id FROM user_rating WHERE account_id = 1
    )
      AND NOT EXISTS (SELECT 1 FROM genre_avg)
      AND m.vote_count >= 100
) rec
ORDER BY rec.vote_average DESC NULLS LAST, rec.popularity DESC NULLS LAST
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

**Goal:** Rank users by activity and average rating using scalar subqueries (`1 + COUNT(*)`) instead of `RANK() OVER`, matching standard `RANK` behavior for ties. Also computes `STDDEV` (rating consistency) and bias vs. TMDB average per user.
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
SELECT
    us.*,
    (
        1 + (
            SELECT COUNT(*)
            FROM user_stats u2
            WHERE u2.total_ratings IS NOT NULL
              AND (
                  us.total_ratings IS NULL
                  OR u2.total_ratings > us.total_ratings
              )
        )
    ) AS activity_rank,
    (
        1 + (
            SELECT COUNT(*)
            FROM user_stats u2
            WHERE u2.avg_rating IS NOT NULL
              AND (
                  us.avg_rating IS NULL
                  OR u2.avg_rating > us.avg_rating
              )
        )
    ) AS avg_rating_rank
FROM user_stats us
ORDER BY us.total_ratings DESC NULLS LAST;
```

</details>

---

## Function 25: Rating Distribution Histogram

**Goal:** Bucket all user ratings into tiers using `CASE`, then express each tier’s share as `count * 100 / (SELECT COUNT(*) FROM user_rating)` — no window aggregate.
**Page:** Admin site → Ratings Analytics (`/admin/ratings`)

<details>
<summary>Show SQL Code</summary>

```sql
SELECT
    b.rating_bucket,
    b.rating_count,
    ROUND(
        b.rating_count * 100.0 / (SELECT COUNT(*)::numeric FROM user_rating),
        1
    ) AS percentage
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
) b
ORDER BY b.sort_key;
```

</details>

---

## Function 26: Genre Performance Deep Analysis

**Goal:** Multi-metric genre rollup with three rank columns, each `1 + COUNT(*)` over the same CTE (strictly greater metric values), replacing `RANK() OVER`.
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
SELECT
    gm.*,
    (
        1 + (
            SELECT COUNT(*) FROM genre_metrics x
            WHERE x.avg_tmdb_rating > gm.avg_tmdb_rating
        )
    ) AS tmdb_rating_rank,
    (
        1 + (
            SELECT COUNT(*) FROM genre_metrics x
            WHERE x.total_user_ratings > gm.total_user_ratings
        )
    ) AS popularity_rank,
    (
        1 + (
            SELECT COUNT(*) FROM genre_metrics x
            WHERE x.total_movies > gm.total_movies
        )
    ) AS volume_rank
FROM genre_metrics gm
ORDER BY gm.total_user_ratings DESC;
```

</details>

---

## Function 27: Company Portfolio Analysis

**Goal:** Evaluate production companies with `quality_pct` (% distinct movies with TMDB rating ≥7), `genre_diversity_score` (distinct genres ÷ total movies), and an average-rating rank via `1 + COUNT(*)` (no `RANK()` window). Movie-level counts and averages are computed **without** joining `movie_genre`, so quality counts are not multiplied by the number of genres per film. Requires ≥3 movies per company.
**Page:** Admin site → Company Analytics (`/admin/companies`)

<details>
<summary>Show SQL Code</summary>

```sql
WITH company_portfolio AS (
    SELECT
        c.company_id,
        c.company_name,
        s.total_movies,
        COALESCE(gb.distinct_genres, 0)         AS distinct_genres,
        s.avg_rating,
        s.avg_popularity,
        s.best_movie_rating,
        s.quality_movies
    FROM company c
    JOIN (
        SELECT
            mc.company_id,
            COUNT(DISTINCT m.movie_id) AS total_movies,
            ROUND(AVG(m.vote_average), 2) AS avg_rating,
            ROUND(AVG(m.popularity), 2) AS avg_popularity,
            MAX(m.vote_average) AS best_movie_rating,
            COUNT(DISTINCT CASE WHEN m.vote_average >= 7 THEN m.movie_id END) AS quality_movies
        FROM movie_company mc
        JOIN movie m ON mc.movie_id = m.movie_id
        GROUP BY mc.company_id
        HAVING COUNT(DISTINCT m.movie_id) >= 3
    ) s ON c.company_id = s.company_id
    LEFT JOIN (
        SELECT
            mc.company_id,
            COUNT(DISTINCT g.genre_id) AS distinct_genres
        FROM movie_company mc
        JOIN movie_genre mg ON mc.movie_id = mg.movie_id
        JOIN genre g ON mg.genre_id = g.genre_id
        GROUP BY mc.company_id
    ) gb ON s.company_id = gb.company_id
)
SELECT
    cp.*,
    ROUND(cp.quality_movies * 100.0 / NULLIF(cp.total_movies, 0), 1) AS quality_pct,
    ROUND(cp.distinct_genres * 1.0  / NULLIF(cp.total_movies, 0), 2) AS genre_diversity_score,
    (
        1 + (
            SELECT COUNT(*) FROM company_portfolio x
            WHERE x.avg_rating > cp.avg_rating
        )
    ) AS rating_rank
FROM company_portfolio cp
ORDER BY cp.avg_rating DESC
LIMIT 20;
```

</details>

---

## Function 28: Catalog Analytics — Most Frequent Cast Members

**Goal:** Rank actors by how many credited movies appear in this dataset; use correlated `NOT EXISTS` subqueries with tie-break logic to derive each actor's single strongest film and dominant genre (`queries/most_frequent_cast_members.sql`).
**Page:** Admin site → Catalog Analytics (`/admin/catalog-analytics`)

<details>
<summary>Show SQL Code</summary>

```sql
SELECT
    p.name AS cast_member,
    COUNT(DISTINCT m.movie_id) AS movie_count,
    ROUND(AVG(m.vote_average), 3) AS avg_movie_rating,
    ROUND(AVG(m.popularity), 3) AS avg_popularity,
    best.title AS best_rated_movie,
    best.vote_average AS best_movie_rating,
    top_g.genre_name AS top_genre
FROM person p
JOIN movie_cast mc ON p.person_id = mc.person_id
JOIN movie m ON mc.movie_id = m.movie_id
JOIN movie best ON best.movie_id = (
    SELECT m2.movie_id
    FROM movie_cast mc2
    JOIN movie m2 ON mc2.movie_id = m2.movie_id
    WHERE mc2.person_id = p.person_id
      AND NOT EXISTS (
          SELECT 1
          FROM movie_cast mc3
          JOIN movie m3 ON mc3.movie_id = m3.movie_id
          WHERE mc3.person_id = p.person_id
            AND (
                m3.vote_average > m2.vote_average
                OR (
                    m3.vote_average = m2.vote_average
                    AND m3.popularity > m2.popularity
                )
                OR (
                    m3.vote_average = m2.vote_average
                    AND m3.popularity = m2.popularity
                    AND m3.movie_id < m2.movie_id
                )
            )
      )
    LIMIT 1
)
LEFT JOIN genre top_g ON top_g.genre_id = (
    SELECT g2.genre_id
    FROM movie_cast mcg
    JOIN movie_genre mg2 ON mcg.movie_id = mg2.movie_id
    JOIN genre g2 ON mg2.genre_id = g2.genre_id
    WHERE mcg.person_id = p.person_id
    GROUP BY g2.genre_id, g2.genre_name
    ORDER BY COUNT(DISTINCT mcg.movie_id) DESC, g2.genre_id
    LIMIT 1
)
GROUP BY
    p.person_id,
    p.name,
    best.title,
    best.vote_average,
    top_g.genre_name
HAVING COUNT(DISTINCT m.movie_id) >= 3
ORDER BY movie_count DESC, avg_movie_rating DESC, avg_popularity DESC
LIMIT 35;
```

</details>

---

## Function 29: Catalog Analytics — Popular Directors

**Goal:** Aggregate each director's filmography breadth and TMDB aggregates; correlate in the "best-directed" title via `NOT EXISTS` (`queries/popular_directors.sql`).
**Page:** Admin site → Catalog Analytics (`/admin/catalog-analytics`)

<details>
<summary>Show SQL Code</summary>

```sql
SELECT
    d.name AS director_name,
    COUNT(DISTINCT m.movie_id) AS directed_movie_count,
    ROUND(AVG(m.vote_average), 3) AS avg_rating,
    ROUND(AVG(m.popularity), 3) AS avg_popularity,
    best.title AS best_rated_movie,
    best.vote_average AS best_movie_rating
FROM person d
JOIN movie_crew mc ON d.person_id = mc.person_id
JOIN movie m ON mc.movie_id = m.movie_id
JOIN movie best ON best.movie_id = (
    SELECT m2.movie_id
    FROM movie_crew mc2
    JOIN movie m2 ON mc2.movie_id = m2.movie_id
    WHERE mc2.person_id = d.person_id
      AND mc2.job_title = 'Director'
      AND NOT EXISTS (
          SELECT 1
          FROM movie_crew mc3
          JOIN movie m3 ON mc3.movie_id = m3.movie_id
          WHERE mc3.person_id = d.person_id
            AND mc3.job_title = 'Director'
            AND (
                m3.vote_average > m2.vote_average
                OR (
                    m3.vote_average = m2.vote_average
                    AND m3.popularity > m2.popularity
                )
                OR (
                    m3.vote_average = m2.vote_average
                    AND m3.popularity = m2.popularity
                    AND m3.movie_id < m2.movie_id
                )
            )
      )
    LIMIT 1
)
WHERE mc.job_title = 'Director'
GROUP BY d.person_id, d.name, best.title, best.vote_average
HAVING COUNT(DISTINCT m.movie_id) >= 2
ORDER BY avg_rating DESC, directed_movie_count DESC
LIMIT 35;
```

</details>

---

## Function 30: Catalog Analytics — Top Companies (Financial Depth)

**Goal:** Restrict to movies with strictly positive reported budget **and** revenue, then summarize company-level averages and totals (`queries/top_companies.sql`).
**Page:** Admin site → Catalog Analytics (`/admin/catalog-analytics`)

<details>
<summary>Show SQL Code</summary>

```sql
SELECT
    c.company_id,
    c.company_name,
    COUNT(DISTINCT m.movie_id) AS movie_count,
    ROUND(AVG(m.revenue - m.budget), 3) AS avg_profit,
    SUM(m.revenue - m.budget) AS total_profit,
    ROUND(AVG(m.vote_average), 3) AS avg_rating,
    ROUND(AVG(m.popularity), 3) AS avg_popularity
FROM company c
JOIN movie_company mc ON c.company_id = mc.company_id
JOIN movie m ON mc.movie_id = m.movie_id
WHERE m.budget > 0
  AND m.revenue > 0
GROUP BY c.company_id, c.company_name
ORDER BY avg_popularity DESC, avg_rating DESC
LIMIT 25;
```

</details>

---

## Function 31: Catalog Analytics — Top Genres on Profitable Films

**Goal:** Genre-level rollup limited to monetized titles so averages are comparable across revenue-backed catalog slices (`queries/top_genres.sql`).
**Page:** Admin site → Catalog Analytics (`/admin/catalog-analytics`)

<details>
<summary>Show SQL Code</summary>

```sql
SELECT
    g.genre_name,
    COUNT(DISTINCT m.movie_id) AS movie_count,
    ROUND(AVG(m.vote_average), 3) AS avg_rating,
    ROUND(AVG(m.popularity), 3) AS avg_popularity,
    ROUND(AVG(m.vote_count), 3) AS avg_vote_count,
    ROUND(AVG(m.runtime), 3) AS avg_runtime,
    SUM(m.revenue) AS total_revenue,
    SUM(m.budget) AS total_budget,
    SUM(m.revenue - m.budget) AS total_profit,
    ROUND(AVG(m.revenue - m.budget), 3) AS avg_profit
FROM genre g
JOIN movie_genre mg ON g.genre_id = mg.genre_id
JOIN movie m ON mg.movie_id = m.movie_id
WHERE m.budget > 0
  AND m.revenue > 0
GROUP BY g.genre_id, g.genre_name
ORDER BY movie_count DESC, avg_profit DESC, avg_rating DESC
LIMIT 10;
```

</details>

---

## Function 32: Catalog Analytics — Top Keywords

**Goal:** Surface the most frequently assigned keyword tags with aggregate popularity and rating signals (`queries/top_keywords.sql`).
**Page:** Admin site → Catalog Analytics (`/admin/catalog-analytics`)

<details>
<summary>Show SQL Code</summary>

```sql
SELECT
    k.keyword_name AS keyword,
    COUNT(DISTINCT m.movie_id) AS movie_count,
    ROUND(AVG(m.popularity), 3) AS avg_popularity,
    ROUND(AVG(m.vote_average), 3) AS avg_rating
FROM keyword k
JOIN movie_keyword mk ON k.keyword_id = mk.keyword_id
JOIN movie m ON mk.movie_id = m.movie_id
GROUP BY k.keyword_id, k.keyword_name
ORDER BY movie_count DESC, avg_rating DESC, avg_popularity DESC
LIMIT 25;
```

</details>

---

*For project overview, architecture, user/admin site flow, and how to run → see [`README.md`](README.md)*
