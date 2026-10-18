-- Activation and D7/D30 retention from the project's own events (module-add analytics, product level).
-- Postgres. Run with `npm run metrics`, or paste into the database console.
--
-- Definitions, stated so the numbers mean the same thing everywhere:
--   signup      = a user's first event in analytics_events (no users table needed; a project whose users
--                 table has created_at can join it instead).
--   cohort      = the ISO week of the signup.
--   activated   = the user has at least one :activation event (the PRD's activation event).
--   retained Dn = an activated user with any event in [signup + n days, signup + n + 1 days).
-- :activation is a bind parameter: the event name from the PRD's ## Measurement.

-- 1. Activation rate per weekly signup cohort.
WITH signup AS (
  SELECT user_id, min(created_at) AS at FROM analytics_events GROUP BY user_id
)
SELECT date_trunc('week', s.at)::date AS cohort,
       count(*)                       AS signups,
       count(*) FILTER (WHERE EXISTS (SELECT 1 FROM analytics_events e
                                      WHERE e.user_id = s.user_id AND e.name = :activation)) AS activated
FROM signup s
GROUP BY 1
ORDER BY 1;

-- 2. D7 and D30 retention of activated users per weekly signup cohort.
WITH signup AS (
  SELECT user_id, min(created_at) AS at FROM analytics_events GROUP BY user_id
), activated AS (
  SELECT s.* FROM signup s
  WHERE EXISTS (SELECT 1 FROM analytics_events e WHERE e.user_id = s.user_id AND e.name = :activation)
)
SELECT date_trunc('week', a.at)::date AS cohort,
       count(*)                       AS activated,
       count(*) FILTER (WHERE EXISTS (SELECT 1 FROM analytics_events e WHERE e.user_id = a.user_id
                                      AND e.created_at >= a.at + interval '7 days'
                                      AND e.created_at <  a.at + interval '8 days'))  AS retained_d7,
       count(*) FILTER (WHERE EXISTS (SELECT 1 FROM analytics_events e WHERE e.user_id = a.user_id
                                      AND e.created_at >= a.at + interval '30 days'
                                      AND e.created_at <  a.at + interval '31 days')) AS retained_d30
FROM activated a
GROUP BY 1
ORDER BY 1;
