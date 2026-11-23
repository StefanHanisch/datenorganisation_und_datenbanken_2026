-- MISSION-01: PERFORMANCE
-- Decision (class + teacher): B-tree index on guests.email for the equality lookup
-- `WHERE email = ...` used by /bookings.
-- Measured before the index: Parallel Seq Scan, ~1,000,020 rows read, ~13,400 buffers, ~51-60 ms (local Docker).
--
-- Run as hotel_owner. Do NOT wrap in BEGIN/COMMIT: CREATE INDEX CONCURRENTLY
-- cannot run inside a transaction block. Run it as a single statement.
-- Execute only after separate explicit teacher approval (never automatically against Azure).
--
-- Check first that no such index exists:
--   SELECT indexname FROM pg_indexes WHERE tablename = 'guests';
--
-- Afterwards re-run EXPLAIN (ANALYZE, BUFFERS) (scripts/benchmark_email.py) and compare.

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_guests_email ON guests (email);
