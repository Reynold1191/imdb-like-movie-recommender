-- Query to find the top 10 companies by average popularity of their movies, along with other relevant metrics.
SELECT
    c.company_id,
    c.company_name,
    COUNT(DISTINCT m.movie_id) AS movie_count,
    ROUND(AVG(m.revenue - m.budget), 3) AS avg_profit,
    SUM(m.revenue - m.budget) AS total_profit,
    ROUND(AVG(m.vote_average), 3) AS avg_rating,
    ROUND(AVG(m.popularity), 3) AS avg_popularity
FROM company c
JOIN movie_company mc
    ON c.company_id = mc.company_id
JOIN movie m
    ON mc.movie_id = m.movie_id
WHERE m.budget > 0
  AND m.revenue > 0
GROUP BY
    c.company_id,
    c.company_name
ORDER BY
    avg_popularity DESC,
    avg_rating DESC;