-- Keyword tags ranked by adoption across the catalog plus aggregate TMDB sentiment signals.
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
