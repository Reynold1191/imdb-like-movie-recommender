-- ============================================================================
-- CATALOG ANALYTICS — 12 QUERIES
-- Queries 1–5 mirror queries/*.sql; queries 6–12 are bundled analytics SQL.
-- Run in PostgreSQL (psql / DBeaver).
-- ============================================================================

-- ----------------------------------------------------------------------------
-- QUERY 1
-- Most frequent cast members — correlated NOT EXISTS tie-break best film
-- Source: queries/most_frequent_cast_members.sql
-- ----------------------------------------------------------------------------
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

-- ----------------------------------------------------------------------------
-- QUERY 2
-- Popular directors — breadth plus correlated best-directed title
-- Source: queries/popular_directors.sql
-- ----------------------------------------------------------------------------
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

-- ----------------------------------------------------------------------------
-- QUERY 3
-- Top companies by profit (positive budget and revenue)
-- Source: queries/top_companies.sql
-- ----------------------------------------------------------------------------
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

-- ----------------------------------------------------------------------------
-- QUERY 4
-- Top genres on profitable films
-- Source: queries/top_genres.sql
-- ----------------------------------------------------------------------------
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

-- ----------------------------------------------------------------------------
-- QUERY 5
-- Top keywords (adoption and TMDB aggregates)
-- Source: queries/top_keywords.sql
-- ----------------------------------------------------------------------------
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

-- ----------------------------------------------------------------------------
-- QUERY 6
-- Top 8 movies per genre (same logic as home Function 3) — correlated counts
-- ----------------------------------------------------------------------------
SELECT
    g.genre_name,
    m.movie_id,
    m.title,
    m.release_date,
    m.vote_average,
    m.vote_count,
    m.popularity
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
            OR (
                m2.vote_average = m.vote_average
                AND m2.popularity > m.popularity
            )
            OR (
                m2.vote_average = m.vote_average
                AND m2.popularity = m.popularity
                AND m2.movie_id < m.movie_id
            )
        )
  ) < 8
ORDER BY genre_name, m.vote_average DESC, m.popularity DESC, m.movie_id;

-- ----------------------------------------------------------------------------
-- QUERY 7
-- Browse-style search: “health”, release year ≥ 2010, vote_average ≥ 6
-- ----------------------------------------------------------------------------
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

-- ----------------------------------------------------------------------------
-- QUERY 8
-- Personalized recommendations — high-rated genres, else top genres by user avg; cold-start popular
-- ----------------------------------------------------------------------------
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
          SELECT ga2.genre_id
          FROM genre_avg ga2
          ORDER BY ga2.avg_user_rating DESC
          LIMIT 8
      )
)
SELECT * FROM (
    SELECT DISTINCT
        m.movie_id, m.title, m.release_date,
        m.vote_average, m.popularity
    FROM movie m
    JOIN movie_genre mg ON m.movie_id = mg.movie_id
    JOIN fav_genres fg ON mg.genre_id = fg.genre_id
    WHERE m.movie_id NOT IN (
        SELECT movie_id FROM user_rating WHERE account_id = 1
    )
      AND EXISTS (SELECT 1 FROM genre_avg)
    UNION ALL
    SELECT m.movie_id, m.title, m.release_date,
           m.vote_average, m.popularity
    FROM movie m
    WHERE m.movie_id NOT IN (
        SELECT movie_id FROM user_rating WHERE account_id = 1
    )
      AND NOT EXISTS (SELECT 1 FROM genre_avg)
      AND m.vote_count >= 100
) rec
ORDER BY rec.vote_average DESC NULLS LAST, rec.popularity DESC NULLS LAST
LIMIT 20;

-- ----------------------------------------------------------------------------
-- QUERY 9
-- User engagement: activity, STDDEV, bias vs TMDB — ranks via scalar subqueries
-- ----------------------------------------------------------------------------
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

-- ----------------------------------------------------------------------------
-- QUERY 10
-- User rating histogram with percentage per bucket (total from COUNT(*) on user_rating)
-- ----------------------------------------------------------------------------
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

-- ----------------------------------------------------------------------------
-- QUERY 11
-- Genre metrics with three rank columns via scalar subqueries
-- ----------------------------------------------------------------------------
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

-- ----------------------------------------------------------------------------
-- QUERY 12
-- Company portfolio: quality share, genre diversity, rating rank (scalar subquery)
-- Movie-level aggregates use movie_company+movie only; genres joined in a side
-- rollup so quality_movies / averages are not inflated by one row per genre.
-- ----------------------------------------------------------------------------
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
