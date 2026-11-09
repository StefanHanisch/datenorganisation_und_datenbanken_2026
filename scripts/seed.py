#!/usr/bin/env python3
"""Generate deterministic synthetic teaching data inside PostgreSQL.

The lecture profile is HUGE and can take a while on a burstable Azure database.
Never run in CI. Requires a privileged SEED_DATABASE_URL and --reset to drop data.
"""
import argparse
import os
import time
from dataclasses import dataclass
import psycopg
from dotenv import load_dotenv


@dataclass(frozen=True)
class Profile:
    hotels: int
    std: int
    deluxe: int
    suites: int
    guests: int
    reservations: int


PROFILES = {
    'demo': Profile(20, 12, 6, 2, 2_000, 4_000),
    'lecture': Profile(5_000, 120, 60, 20, 3_000_000, 5_000_000),
}
CITIES = [
    ('Berlin', 'Deutschland'), ('Bern', 'Schweiz'), ('Bergen', 'Norwegen'),
    ('Bonn', 'Deutschland'), ('Hamburg', 'Deutschland'),
    ('London', 'Vereinigtes Königreich'), ('Paris', 'Frankreich'),
    ('Madrid', 'Spanien'), ('Amsterdam', 'Niederlande'), ('Zürich', 'Schweiz'),
    ('Oslo', 'Norwegen'), ('Kopenhagen', 'Dänemark'), ('Stockholm', 'Schweden'),
    ('Toronto', 'Kanada'), ('Montreal', 'Kanada'), ('Singapur', 'Singapur'),
    ('Wien', 'Österreich'), ('Prag', 'Tschechien'), ('Lissabon', 'Portugal'),
    ('Helsinki', 'Finnland'),
]


def progress(msg):
    print(f'[{time.strftime("%H:%M:%S")}] {msg}', flush=True)


def main():
    load_dotenv()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', choices=PROFILES, default='demo')
    parser.add_argument('--reset', action='store_true', help='Required to wipe existing records')
    parser.add_argument('--i-understand-data-loss', action='store_true')
    parser.add_argument('--batch', type=int, default=100_000)
    args = parser.parse_args()
    if args.reset and not args.i_understand_data_loss:
        parser.error('--reset needs --i-understand-data-loss')
    if args.batch < 1_000 or args.batch > 500_000:
        parser.error('--batch must be between 1,000 and 500,000')
    url = os.getenv('SEED_DATABASE_URL')
    if not url:
        parser.error('SEED_DATABASE_URL missing (set it from .env)')
    p = PROFILES[args.profile]
    progress(f'profile={args.profile}: hotels={p.hotels}, rooms={p.hotels*(p.std+p.deluxe+p.suites):,}, '
             f'guests={p.guests:,}, reservations={p.reservations:,}')
    with psycopg.connect(url, connect_timeout=10) as conn:
        if args.reset:
            progress('RESET: deleting all synthetic rows and resetting identities')
            conn.execute('TRUNCATE reservations, guests, rooms, room_categories, hotels, cities RESTART IDENTITY CASCADE')
            conn.commit()
        if conn.execute('SELECT EXISTS(SELECT 1 FROM hotels)').fetchone()[0]:
            parser.error('Database already contains hotels. Re-run with --reset --i-understand-data-loss.')
        with conn.cursor() as cur:
            cur.executemany('INSERT INTO cities(name,country) VALUES(%s,%s)', CITIES)
            cur.execute('''
                WITH city_ids AS (SELECT array_agg(id ORDER BY id) AS ids FROM cities)
                INSERT INTO hotels(city_id,name,address,stars)
                SELECT ids[1 + ((g-1) % array_length(ids,1))],
                       'GlobalStay Hotel ' || lpad(g::text,5,'0'),
                       'Hotelstraße ' || g::text, (3+(g%3))::smallint
                FROM generate_series(1,%s) AS g, city_ids
            ''', (p.hotels,))
            cur.execute('''
                INSERT INTO room_categories(hotel_id,name,base_price,max_guests)
                SELECT h.id, c.name, c.price, c.max_guests
                FROM hotels h CROSS JOIN (VALUES
                   ('Standard',99.00,2),('Deluxe',149.00,3),('Suite',249.00,4)
                ) AS c(name,price,max_guests)
            ''')
            cur.execute('''
                INSERT INTO rooms(category_id,room_number)
                SELECT c.id,
                   CASE c.name WHEN 'Standard' THEN 'STD-'
                               WHEN 'Deluxe' THEN 'DLX-' ELSE 'STE-' END
                   || lpad(n::text,3,'0')
                FROM room_categories c
                CROSS JOIN LATERAL generate_series(1,
                  CASE c.name WHEN 'Standard' THEN %s
                              WHEN 'Deluxe' THEN %s ELSE %s END
                ) AS n
            ''', (p.std, p.deluxe, p.suites))
        conn.commit()
        progress('Cities, hotels, categories and rooms ready')
        for start in range(1, p.guests + 1, args.batch):
            end = min(start + args.batch - 1, p.guests)
            conn.execute('''
                INSERT INTO guests(first_name,last_name,email)
                SELECT (ARRAY['Anna','Max','Mia','Jonas','Lina','Alex'])[1 + (g % 6)],
                       'Gast' || g::text, 'gast' || g::text || '@example.test'
                FROM generate_series(%s,%s) AS g
            ''', (start, end))
            conn.commit()
            if end == p.guests or end % (args.batch * 5) == 0:
                progress(f'Guests: {end:,} / {p.guests:,}')
        categories = p.hotels * 3
        for start in range(1, p.reservations + 1, args.batch):
            end = min(start + args.batch - 1, p.reservations)
            conn.execute('''
                INSERT INTO reservations(guest_id,category_id,checkin,checkout,status)
                SELECT 1 + ((g-1) % %s),
                       1 + (((g-1)*37) % %s),
                       date '2026-11-01' + ((g*7) % 520),
                       date '2026-11-01' + ((g*7) % 520) + (1 + (g % 4)),
                       'confirmed'
                FROM generate_series(%s,%s) AS g
            ''', (p.guests, categories, start, end))
            conn.commit()
            if end == p.reservations or end % (args.batch * 5) == 0:
                progress(f'Reservations: {end:,} / {p.reservations:,}')
        progress('ANALYZE (required for meaningful query plans and dashboard stats)')
        for table in ('cities', 'hotels', 'room_categories', 'rooms', 'guests', 'reservations'):
            conn.execute('ANALYZE ' + table)
        conn.commit()
        progress('DONE. Sample lookup: gast1@example.test')
        progress('MISSION-01: guests.email has intentionally NO INDEX.')


if __name__ == '__main__':
    main()
