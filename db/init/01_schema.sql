-- Run as hotel_owner. Lecture intent: guests.email must NOT be indexed.
CREATE TABLE IF NOT EXISTS cities (
  id BIGSERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  country TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS hotels (
  id BIGSERIAL PRIMARY KEY,
  city_id BIGINT NOT NULL REFERENCES cities(id),
  name TEXT NOT NULL,
  address TEXT NOT NULL,
  stars SMALLINT NOT NULL DEFAULT 3 CHECK (stars BETWEEN 1 AND 5),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_hotels_city ON hotels(city_id);
CREATE TABLE IF NOT EXISTS room_categories (
  id BIGSERIAL PRIMARY KEY,
  hotel_id BIGINT NOT NULL REFERENCES hotels(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  base_price NUMERIC(10,2) NOT NULL CHECK (base_price > 0),
  max_guests SMALLINT NOT NULL DEFAULT 2 CHECK (max_guests BETWEEN 1 AND 8),
  UNIQUE (hotel_id, name)
);
CREATE TABLE IF NOT EXISTS rooms (
  id BIGSERIAL PRIMARY KEY,
  category_id BIGINT NOT NULL REFERENCES room_categories(id) ON DELETE CASCADE,
  room_number TEXT NOT NULL,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  UNIQUE (category_id, room_number)
);
CREATE TABLE IF NOT EXISTS guests (
  id BIGSERIAL PRIMARY KEY,
  first_name TEXT NOT NULL,
  last_name TEXT NOT NULL,
  email TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
-- DO NOT CREATE AN INDEX ON guests(email). MISSION-01 must discover this.
CREATE TABLE IF NOT EXISTS reservations (
  id BIGSERIAL PRIMARY KEY,
  guest_id BIGINT NOT NULL REFERENCES guests(id),
  category_id BIGINT NOT NULL REFERENCES room_categories(id),
  checkin DATE NOT NULL,
  checkout DATE NOT NULL,
  status TEXT NOT NULL DEFAULT 'confirmed'
     CHECK (status IN ('confirmed', 'cancelled')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT valid_nights CHECK (checkout > checkin)
);
CREATE INDEX IF NOT EXISTS idx_reservations_guest ON reservations(guest_id);
CREATE INDEX IF NOT EXISTS idx_reservations_category_dates
  ON reservations(category_id, checkin, checkout)
  WHERE status = 'confirmed';
