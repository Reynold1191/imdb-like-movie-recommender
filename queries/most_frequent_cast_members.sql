-- Most frequent cast members: correlated subqueries for "best-rated" film and dominant genre per actor.
-- Requires ≥ 3 credited movies; excludes NOT EXISTS ties on vote/popularity/id.
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
