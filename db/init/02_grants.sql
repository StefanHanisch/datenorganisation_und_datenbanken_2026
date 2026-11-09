-- Application role can operate the booking product; it cannot alter the schema.
GRANT SELECT, INSERT, UPDATE, DELETE ON
  cities, hotels, room_categories, rooms, guests, reservations TO hotel_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO hotel_app;
-- Students can inspect data, but cannot mutate it, even if request validation fails.
GRANT SELECT ON cities, hotels, room_categories, rooms, guests, reservations TO hotel_student;
ALTER ROLE hotel_student SET default_transaction_read_only = on;
ALTER ROLE hotel_student SET statement_timeout = '4000ms';
ALTER ROLE hotel_student SET idle_in_transaction_session_timeout = '5000ms';
-- Explicitly no CREATE, INSERT, UPDATE, DELETE, TRUNCATE or EXECUTE on custom functions.
