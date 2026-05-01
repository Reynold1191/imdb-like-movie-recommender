-- This query identifies popular directors based on their average movie ratings and popularity. 
-- It retrieves the director's name, the count of movies they have directed, their average rating and popularity, and their best-rated movie along with its rating. The results are filtered to include only directors who have directed at least 2 movies and are ordered by average rating and movie count.
SELECT
    d.name AS director_name,
    COUNT(DISTINCT m.movie_id) AS directed_movie_count,
    ROUND(AVG(m.vote_average), 3) AS avg_rating,
    ROUND(AVG(m.popularity), 3) AS avg_popularity,
    best.title AS best_rated_movie,
    best.vote_average AS best_movie_rating
FROM person d
JOIN movie_crew mc
    ON d.person_id = mc.person_id
JOIN movie m
    ON mc.movie_id = m.movie_id
JOIN movie best
    ON best.movie_id = (
        SELECT m2.movie_id
        FROM movie_crew mc2
        JOIN movie m2
            ON mc2.movie_id = m2.movie_id
        WHERE mc2.person_id = d.person_id
          AND mc2.job_title = 'Director'
          AND NOT EXISTS (
              SELECT *
              FROM movie_crew mc3
              JOIN movie m3
                  ON mc3.movie_id = m3.movie_id
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
    )
WHERE mc.job_title = 'Director'
GROUP BY
    d.person_id,
    d.name,
    best.title,
    best.vote_average
HAVING COUNT(DISTINCT m.movie_id) >= 2 -- Only include directors who have directed at least 2 movies
ORDER BY
    avg_rating DESC,
    directed_movie_count DESC;