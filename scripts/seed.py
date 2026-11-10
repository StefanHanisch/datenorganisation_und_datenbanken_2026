#!/usr/bin/env python3
"""Generate deterministic synthetic teaching data inside PostgreSQL.

The lecture profile is HUGE and can take a while on a burstable Azure database.
Never run in CI. Requires a privileged SEED_DATABASE_URL and --reset to drop data.
"""
import argparse
import os
import random
import time
from dataclasses import dataclass
import psycopg
from dotenv import load_dotenv
from faker import Faker

RANDOM_SEED = 42


@dataclass(frozen=True)
class Profile:
    hotels: int
    cities: int
    std: int
    deluxe: int
    suites: int
    guests: int
    reservations: int


PROFILES = {
    'demo': Profile(1_500, 1_000, 12, 6, 2, 2_000, 4_000),
    # 1,000 hotels x 1,000 rooms = 1,000,000 rooms
    'large': Profile(1_000, 1_000, 600, 300, 100, 1_000_000, 3_000_000),
    'lecture': Profile(5_000, 2_500, 120, 60, 20, 3_000_000, 5_000_000),
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
# Faker locale -> country name used in the cities table
CITY_LOCALES = {
    'de_DE': 'Deutschland', 'de_AT': 'Österreich', 'de_CH': 'Schweiz',
    'fr_FR': 'Frankreich', 'it_IT': 'Italien', 'es_ES': 'Spanien',
    'nl_NL': 'Niederlande', 'pl_PL': 'Polen', 'sv_SE': 'Schweden',
    'en_GB': 'Vereinigtes Königreich', 'en_US': 'USA', 'pt_PT': 'Portugal',
    'da_DK': 'Dänemark', 'fi_FI': 'Finnland', 'cs_CZ': 'Tschechien',
}
# Many cities share a prefix, so autocomplete / Trie has something to chew on.
PREFIX_FAMILIES = ['Neu', 'Ober', 'Unter', 'Bad', 'Sankt', 'Klein', 'Groß', 'Alt']
ANIMALS = ['Adler', 'Hirsch', 'Löwen', 'Bären', 'Schwan', 'Raben', 'Fuchs', 'Pelikan', 'Krone']
COLORS = ['Blue', 'Golden', 'Silver', 'Green', 'Red', 'White', 'Crimson', 'Amber']
NOUNS = ['Harbor', 'Lantern', 'Orchard', 'Anchor', 'Meadow', 'Compass', 'Willow', 'Summit',
         'Lighthouse', 'Garden', 'Bridge', 'Falcon', 'Cedar', 'Horizon']
SUFFIXES = ['Inn', 'Lodge', 'House', 'Retreat', 'Suites', 'Residence']


def build_cities(count, rng):
    """First the 20 classic cities, then Faker cities from many locales plus prefix families."""
    cities = list(CITIES)
    seen = set(cities)
    fakers = {loc: Faker(loc) for loc in CITY_LOCALES}
    for i, f in enumerate(fakers.values()):
        f.seed_instance(RANDOM_SEED + i)
    locales = list(CITY_LOCALES)
    attempts = 0
    while len(cities) < count and attempts < count * 50:
        attempts += 1
        locale = rng.choice(locales)
        name = fakers[locale].city()
        if locale in ('de_DE', 'de_AT') and rng.random() < 0.12:
            name = rng.choice(PREFIX_FAMILIES) + (' ' if rng.random() < 0.5 else '') + name
        entry = (name, CITY_LOCALES[locale])
        if entry not in seen:
            seen.add(entry)
            cities.append(entry)
    if len(cities) < count:
        raise SystemExit(f'Faker produced only {len(cities)} unique cities, wanted {count}')
    return cities


def hotel_name(city, rng, fake):
    """Pick one of many name patterns so hotel names do not look alike."""
    last, first = fake.last_name(), fake.first_name()
    patterns = [
        lambda: f'Hotel zum {rng.choice(ANIMALS)}',
        lambda: f'Gasthof {last}',
        lambda: f'Villa {first}',
        lambda: f'Seeblick {city}',
        lambda: f'The {rng.choice(COLORS)} {rng.choice(NOUNS)} {rng.choice(SUFFIXES)}',
        lambda: f'Grand Hotel {city}',
        lambda: f'Pension {first}',
        lambda: f'{fake.street_name()}-Residenz',
        lambda: f'Landhaus {last}',
        lambda: f'Boutique {rng.choice(NOUNS)} & {rng.choice(NOUNS)}',
        lambda: 'Alte Post',
        lambda: f'Casa {first}',
        lambda: f'{city} Central Suites',
        lambda: f'Hôtel de la {rng.choice(NOUNS)}',
        lambda: f'{last} {rng.choice(SUFFIXES)}',
        lambda: f'{first}s {rng.choice(NOUNS)}',
    ]
    return rng.choice(patterns)()


def build_hotels(hotel_count, city_ids, city_names, rng):
    """Every city gets one hotel; the rest is spread randomly (some cities get many)."""
    fake = Faker('de_DE')
    fake.seed_instance(RANDOM_SEED)
    rows = []
    for i in range(hotel_count):
        idx = i if i < len(city_ids) else int(len(city_ids) * rng.random() ** 2)
        stars = rng.choices([1, 2, 3, 4, 5], weights=[3, 10, 35, 35, 17])[0]
        rows.append((city_ids[idx], hotel_name(city_names[idx], rng, fake),
                     fake.street_address(), stars))
    return rows


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
    if p.hotels < p.cities:
        parser.error('profile needs hotels >= cities so every city has a hotel')
    progress(f'profile={args.profile}: cities={p.cities}, hotels={p.hotels}, rooms={p.hotels*(p.std+p.deluxe+p.suites):,}, '
             f'guests={p.guests:,}, reservations={p.reservations:,}')
    with psycopg.connect(url, connect_timeout=10) as conn:
        if args.reset:
            progress('RESET: deleting all synthetic rows and resetting identities')
            conn.execute('TRUNCATE reservations, guests, rooms, room_categories, hotels, cities RESTART IDENTITY CASCADE')
            conn.commit()
        if conn.execute('SELECT EXISTS(SELECT 1 FROM hotels)').fetchone()[0]:
            parser.error('Database already contains hotels. Re-run with --reset --i-understand-data-loss.')
        with conn.cursor() as cur:
            rng = random.Random(RANDOM_SEED)
            cities = build_cities(p.cities, rng)
            cur.executemany('INSERT INTO cities(name,country) VALUES(%s,%s)', cities)
            city_rows = cur.execute('SELECT id, name FROM cities ORDER BY id').fetchall()
            hotels = build_hotels(p.hotels, [r[0] for r in city_rows],
                                  [r[1] for r in city_rows], rng)
            cur.executemany('INSERT INTO hotels(city_id,name,address,stars) VALUES(%s,%s,%s,%s)',
                            hotels)
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
                SELECT (ARRAY['Anna','Max','Mia','Jonas','Lina','Alex'])[1 + (g %% 6)],
                       'Gast' || g::text, 'gast' || g::text || '@example.test'
                FROM generate_series(%s::bigint,%s::bigint) AS g
            ''', (start, end))
            conn.commit()
            if end == p.guests or end % (args.batch * 5) == 0:
                progress(f'Guests: {end:,} / {p.guests:,}')
        categories = p.hotels * 3
        for start in range(1, p.reservations + 1, args.batch):
            end = min(start + args.batch - 1, p.reservations)
            conn.execute('''
                INSERT INTO reservations(guest_id,category_id,checkin,checkout,status)
                SELECT 1 + ((g-1) %% %s),
                       1 + (((g-1)*37) %% %s),
                       date '2026-11-01' + ((g*7) %% 520)::int,
                       date '2026-11-01' + ((g*7) %% 520)::int + (1 + (g %% 4))::int,
                       'confirmed'
                FROM generate_series(%s::bigint,%s::bigint) AS g
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
