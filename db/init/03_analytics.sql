-- Run as hotel_owner. Read-only analytics snapshot for the pandas notebook.
-- Only core hotels (hotels.city_type IS NOT NULL). No guest emails, no card tokens.
-- Materialized views are filled at creation time (empty on a fresh volume).
-- After every new seed run REFRESH MATERIALIZED VIEW for each view
-- (done by seed.py or scripts/setup_analytics.py --refresh).
CREATE SCHEMA IF NOT EXISTS analytics;

CREATE MATERIALIZED VIEW IF NOT EXISTS analytics.cities AS
SELECT ci.id, ci.name, ci.country
FROM public.cities ci
WHERE ci.id IN (
  SELECT h.city_id
  FROM public.hotels h
  WHERE h.city_type IS NOT NULL
)
ORDER BY ci.id;

CREATE MATERIALIZED VIEW IF NOT EXISTS analytics.hotels AS
SELECT h.id, h.city_id, h.name, h.address, h.stars, h.created_at, h.city_type, h.bundesland
FROM public.hotels h
WHERE h.city_type IS NOT NULL
ORDER BY h.id;

CREATE MATERIALIZED VIEW IF NOT EXISTS analytics.room_categories AS
SELECT c.id, c.hotel_id, c.name,
       c.base_price::double precision AS base_price,
       c.max_guests
FROM public.room_categories c
JOIN public.hotels h ON h.id = c.hotel_id
WHERE h.city_type IS NOT NULL
ORDER BY c.id;

-- Guests with at least one core reservation. The email column is left out on purpose.
CREATE MATERIALIZED VIEW IF NOT EXISTS analytics.guests AS
SELECT g.id, g.first_name, g.last_name, g.created_at, g.home_state, g.company
FROM public.guests g
WHERE g.id IN (
  SELECT r.guest_id
  FROM public.reservations r
  JOIN public.room_categories c ON c.id = r.category_id
  JOIN public.hotels h ON h.id = c.hotel_id
  WHERE h.city_type IS NOT NULL
)
ORDER BY g.id;

-- card_token is left out on purpose.
CREATE MATERIALIZED VIEW IF NOT EXISTS analytics.reservations AS
SELECT r.id, r.guest_id, r.category_id, r.checkin, r.checkout, r.status,
       r.created_at,
       r.rate_per_night::double precision AS rate_per_night,
       r.adults, r.children, r.channel,
       r.commission_pct::double precision AS commission_pct,
       r.cancelled_at
FROM public.reservations r
JOIN public.room_categories c ON c.id = r.category_id
JOIN public.hotels h ON h.id = c.hotel_id
WHERE h.city_type IS NOT NULL
ORDER BY r.id;

CREATE MATERIALIZED VIEW IF NOT EXISTS analytics.daily_rates AS
SELECT d.category_id, d.arrival_date,
       d.offered_rate::double precision AS offered_rate,
       d.price_source, d.closed_to_arrival
FROM public.daily_rates d
JOIN public.room_categories c ON c.id = d.category_id
JOIN public.hotels h ON h.id = c.hotel_id
WHERE h.city_type IS NOT NULL
ORDER BY d.category_id, d.arrival_date;

-- All rows (small table). city_id NULL = nationwide.
CREATE MATERIALIZED VIEW IF NOT EXISTS analytics.calendar_events AS
SELECT e.event_date, e.city_id, e.event_type, e.name
FROM public.calendar_events e
ORDER BY e.event_date, e.city_id, e.name;

-- The analyst role reads only the analytics schema, never the public tables.
-- Explicitly no CREATE, INSERT, UPDATE, DELETE or TRUNCATE for hotel_analyst.
-- The ALTER ROLE statements below carry no leading comment, so each split
-- statement starts with ALTER ROLE (setup scripts run those as admin).
GRANT USAGE ON SCHEMA analytics TO hotel_analyst;
GRANT SELECT ON ALL TABLES IN SCHEMA analytics TO hotel_analyst;
ALTER ROLE hotel_analyst SET default_transaction_read_only = on;
ALTER ROLE hotel_analyst SET statement_timeout = '60s';
ALTER ROLE hotel_analyst SET idle_in_transaction_session_timeout = '60s';
ALTER ROLE hotel_analyst CONNECTION LIMIT 100;
