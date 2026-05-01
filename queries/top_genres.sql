-- This query retrieves the top 10 genres based on the number of movies, average profit, and average rating.
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
JOIN movie_genre mg
    ON g.genre_id = mg.genre_id
JOIN movie m
    ON mg.movie_id = m.movie_id
WHERE m.budget > 0
  AND m.revenue > 0
GROUP BY
    g.genre_id,
    g.genre_name
ORDER BY
    movie_count DESC,
    avg_profit DESC,
    avg_rating DESC
LIMIT 10;