-- Activation and D7/D30 retention from the project's own events (module-add analytics, product level).
-- Postgres. Run with `npm run metrics`, or paste into the database console.
--
-- Definitions, stated so the numbers mean the same thing everywhere — and in the PRD's targets:
--   signup      = the user's `signed_up` event, recorded when the account is created (a user who signs up and
--                 does nothing else is still counted: that is the false positive the PRD watches).
--   cohort      = the ISO week of the signup.
--   activated   = the user has an :activation event (the PRD's activation event) within 7 days of the signup.
--                 Activating months later is a different story than "got the value"; change 7 here and in the
--                 PRD's Measurement line together if the product's first-value moment is slower.
--   retained Dn = an activated user with any event in [signup + n days, signup + n + 1 days) — back on day n.
--   eligible Dn = an activated user whose day-n window has already ended. Only eligible users are in the Dn
--                 denominator, so this week's cohort does not read as 0 % before its day 7 has come.
-- :activation is a bind parameter: the event name from the PRD's ## Measurement.

-- 1. Activation rate per weekly signup cohort.
WITH signup AS (
  SELECT user_id, min(created_at) AS at FROM analytics_events WHERE name = 'signed_up' GROUP BY user_id
)
SELECT date_trunc('week', s.at)::date AS cohort,
       count(*)                       AS signups,
       count(*) FILTER (WHERE EXISTS (SELECT 1 FROM analytics_events e
                                      WHERE e.user_id = s.user_id AND e.name = :activation
                                      AND e.created_at < s.at + interval '7 days')) AS activated
FROM signup s
GROUP BY 1
ORDER BY 1;

-- 2. D7 and D30 retention of activated users per weekly signup cohort; rate = retained / eligible.
WITH signup AS (
  SELECT user_id, min(created_at) AS at FROM analytics_events WHERE name = 'signed_up' GROUP BY user_id
), activated AS (
  SELECT s.* FROM signup s
  WHERE EXISTS (SELECT 1 FROM analytics_events e WHERE e.user_id = s.user_id AND e.name = :activation
                AND e.created_at < s.at + interval '7 days')
)
SELECT date_trunc('week', a.at)::date AS cohort,
       count(*)                       AS activated,
       count(*) FILTER (WHERE a.at + interval '8 days' <= now())  AS eligible_d7,
       count(*) FILTER (WHERE a.at + interval '8 days' <= now() AND EXISTS (
                          SELECT 1 FROM analytics_events e WHERE e.user_id = a.user_id
                          AND e.created_at >= a.at + interval '7 days'
                          AND e.created_at <  a.at + interval '8 days'))  AS retained_d7,
       count(*) FILTER (WHERE a.at + interval '31 days' <= now()) AS eligible_d30,
       count(*) FILTER (WHERE a.at + interval '31 days' <= now() AND EXISTS (
                          SELECT 1 FROM analytics_events e WHERE e.user_id = a.user_id
                          AND e.created_at >= a.at + interval '30 days'
                          AND e.created_at <  a.at + interval '31 days')) AS retained_d30
FROM activated a
GROUP BY 1
ORDER BY 1;
