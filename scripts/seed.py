#!/usr/bin/env python3
"""Generate deterministic synthetic teaching data inside PostgreSQL.

The lecture profile is HUGE and can take a while on a burstable Azure database.
Never run in CI. Requires a privileged SEED_DATABASE_URL and --reset to drop data.
"""
import argparse
import csv
import json
import os
import random
import time
from dataclasses import dataclass
from pathlib import Path
import psycopg
from psycopg import sql
from dotenv import load_dotenv
from faker import Faker

from app.db_target import describe_target, resolve_db_url
from seed_calendar import calendar_rows
from seed_holidays import STATE_SLOTS
from seed_model import CORE_CAPACITY, CORE_CITIES, CoreCategory
from seed_patterns import generate_core

RANDOM_SEED = 42
CORE_GUEST_POOL = 60_000  # keeps the analysis data small and guests returning
PRIVATE_DIR = Path(__file__).resolve().parent.parent / 'private'


@dataclass(frozen=True)
class Profile:
    hotels: int
    cities: int
    std: int
    deluxe: int
    suites: int
    guests: int
    reservations: int
    core_hotels: int  # extra hotels on top of `hotels`, these carry the patterns


PROFILES = {
    'demo': Profile(1_500, 1_000, 12, 6, 2, 2_000, 4_000, 0),
    # Small profile to check the patterns quickly
    'patterns': Profile(30, 30, 12, 6, 2, 60_000, 240_000, 10),
    # 1,000 hotels x 1,000 rooms = 1,000,000 rooms, plus the core hotels
    'large': Profile(1_000, 1_000, 600, 300, 100, 1_000_000, 3_000_000, 10),
    'lecture': Profile(5_000, 2_500, 120, 60, 20, 3_000_000, 5_000_000, 10),
}
MIN_CITIES_WITH_CORE = 28  # 20 classic cities plus the 8 missing core cities
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
# Both list lengths are prime (97 and 127). The guest SQL picks names with g modulo
# the length, so every combination occurs and names do not follow home_state.
FIRST_NAMES = [
    'Anna', 'Max', 'Mia', 'Jonas', 'Lina', 'Alexander', 'Emma', 'Paul', 'Sophie', 'Leon',
    'Marie', 'Felix', 'Laura', 'Lukas', 'Julia', 'Tim', 'Sarah', 'Jan', 'Lea', 'Niklas',
    'Hannah', 'Elias', 'Clara', 'David', 'Lena', 'Simon', 'Nina', 'Fabian', 'Katharina', 'Moritz',
    'Johanna', 'Philipp', 'Charlotte', 'Daniel', 'Amelie', 'Tobias', 'Franziska', 'Sebastian',
    'Theresa', 'Matthias', 'Helena', 'Christian', 'Isabel', 'Florian', 'Emilia', 'Thomas',
    'Greta', 'Michael', 'Ida', 'Andreas', 'Luisa', 'Stefan', 'Frieda', 'Martin', 'Nora', 'Markus',
    'Eva', 'Peter', 'Monika', 'Klaus', 'Sabine', 'Wolfgang', 'Petra', 'Jürgen', 'Claudia', 'Uwe',
    'Birgit', 'Bernd', 'Karin', 'Dieter', 'Ursula', 'Ralf', 'Heike', 'Holger', 'Silke', 'Oliver',
    'Anja', 'Carsten', 'Susanne', 'Jens', 'Nicole', 'Dirk', 'Melanie', 'Patrick', 'Yasemin',
    'Mehmet', 'Aylin', 'Emre', 'Zeynep', 'Ali', 'Olga', 'Piotr', 'Agnieszka', 'Marco', 'Giulia',
    'Ivan', 'Elena',
]
LAST_NAMES = [
    'Müller', 'Schmidt', 'Schneider', 'Fischer', 'Weber', 'Meyer', 'Wagner', 'Becker', 'Schulz',
    'Hoffmann', 'Schäfer', 'Koch', 'Bauer', 'Richter', 'Klein', 'Wolf', 'Schröder', 'Neumann',
    'Schwarz', 'Zimmermann', 'Braun', 'Krüger', 'Hofmann', 'Hartmann', 'Lange', 'Schmitt',
    'Werner', 'Schmitz', 'Krause', 'Meier', 'Lehmann', 'Schmid', 'Schulze', 'Maier', 'Köhler',
    'Herrmann', 'König', 'Walter', 'Mayer', 'Huber', 'Kaiser', 'Fuchs', 'Peters', 'Lang',
    'Scholz', 'Möller', 'Weiß', 'Jung', 'Hahn', 'Schubert', 'Vogel', 'Friedrich', 'Keller',
    'Günther', 'Frank', 'Berger', 'Winkler', 'Roth', 'Beck', 'Lorenz', 'Baumann', 'Franke',
    'Albrecht', 'Schuster', 'Simon', 'Ludwig', 'Böhm', 'Winter', 'Kraus', 'Martin', 'Schumacher',
    'Krämer', 'Vogt', 'Stein', 'Jäger', 'Otto', 'Sommer', 'Groß', 'Seidel', 'Heinrich', 'Brandt',
    'Haas', 'Schreiber', 'Graf', 'Schulte', 'Dietrich', 'Ziegler', 'Kuhn', 'Kühn', 'Pohl',
    'Engel', 'Horn', 'Busch', 'Bergmann', 'Thomas', 'Voigt', 'Sauer', 'Arnold', 'Wolff', 'Pfeiffer',
    'Yılmaz', 'Kaya', 'Demir', 'Şahin', 'Çelik', 'Nowak', 'Kowalski', 'Wójcik', 'Rossi', 'Russo',
    'Petrov', 'Ivanova', 'Popescu', 'Nguyen', 'Tran', 'Haddad', 'Khan', 'Garcia', 'Santos',
    'Novak', 'Horvat', 'Jansen', 'de Vries', 'Andersen', 'Lindqvist', 'Virtanen', 'Papadopoulos',
]
# Invented firm names for the guests.company column
COMPANIES = [
    'Nordlicht Logistik GmbH', 'Brückner & Falk Beratung', 'Rheintal Maschinenbau AG',
    'Solvana Energie GmbH', 'Weserkraft Technik GmbH', 'Alpenblick Software GmbH',
    'Hanseatic Datenwerk GmbH', 'Elbmark Consulting', 'Tannhof Pharma AG',
    'Lindengrund Immobilien GmbH', 'Mainbogen Finanz AG', 'Ostwind Telekom GmbH',
    'Kupferhain Metall GmbH', 'Sonnfeld Medien GmbH', 'Isarquell Versicherung AG',
    'Grauwacke Bau GmbH', 'Birkenau Handel KG', 'Neckarwerk Automation GmbH',
    'Moosbach Chemie AG', 'Havelport Spedition GmbH', 'Fernbruch Systems GmbH',
    'Dünenrand Touristik GmbH', 'Silberau Textil KG',
]


def build_cities(count, rng, with_core_cities):
    """First the classic cities (plus missing core cities), then Faker cities and prefix families."""
    cities = list(CITIES)
    if with_core_cities:
        cities += [(c.name, c.country) for c in CORE_CITIES if (c.name, c.country) not in CITIES]
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


def build_core_hotels(core_count, core_city_ids, rng):
    """Core hotels go round-robin across CORE_CITIES and carry city_type and bundesland."""
    fake = Faker('de_DE')
    fake.seed_instance(RANDOM_SEED + 1)
    rows = []
    for i in range(core_count):
        city = CORE_CITIES[i % len(CORE_CITIES)]
        stars = rng.choices([3, 4, 5], weights=[40, 45, 15])[0]
        rows.append((core_city_ids[city.name], hotel_name(city.name, rng, fake),
                     fake.street_address(), stars, city.city_type, city.bundesland))
    return rows


def load_core_categories(cur):
    """Read the core categories back from the database for the pattern generator."""
    rows = cur.execute('''
        SELECT c.id, c.hotel_id, ci.name, h.city_type, c.name, c.base_price
        FROM room_categories c
        JOIN hotels h ON h.id = c.hotel_id
        JOIN cities ci ON ci.id = h.city_id
        WHERE h.city_type IS NOT NULL
        ORDER BY c.id
    ''').fetchall()
    return [CoreCategory(category_id, hotel_id, city, city_type, name,
                         float(base_price), CORE_CAPACITY[name])
            for category_id, hotel_id, city, city_type, name, base_price in rows]


def sync_id_sequence(cur, table):
    """After inserts with explicit ids, the next generated id must follow the highest one."""
    cur.execute(f"SELECT setval(pg_get_serial_sequence('{table}','id'), (SELECT max(id) FROM {table}))")


def insert_story_guests(cur, story_guests):
    cur.executemany('''
        INSERT INTO guests(id,first_name,last_name,email,home_state,company)
        VALUES(%s,%s,%s,%s,%s,%s)
    ''', [(s.guest_id, s.first_name, s.last_name, s.email, s.home_state, s.company)
          for s in story_guests])
    sync_id_sequence(cur, 'guests')


def copy_reservations(cur, bookings):
    with cur.copy('''
        COPY reservations(id,guest_id,category_id,checkin,checkout,status,created_at,cancelled_at,
                          rate_per_night,adults,children,channel,commission_pct,card_token)
        FROM STDIN
    ''') as copy:
        for b in bookings:
            copy.write_row((int(b.reservation_id), int(b.guest_id), int(b.category_id),
                            b.checkin, b.checkout, b.status, b.created_at, b.cancelled_at,
                            float(b.rate_per_night), int(b.adults), int(b.children), b.channel,
                            float(b.commission_pct), b.card_token))
    sync_id_sequence(cur, 'reservations')


def copy_daily_rates(cur, rates, closed):
    with cur.copy('''
        COPY daily_rates(category_id,arrival_date,offered_rate,price_source,closed_to_arrival)
        FROM STDIN
    ''') as copy:
        for key, rate in rates.items():
            copy.write_row((int(rate.category_id), rate.arrival_date, float(rate.offered_rate),
                            rate.price_source, key in closed))


def copy_calendar_events(cur, core_city_ids):
    with cur.copy('COPY calendar_events(event_date,city_id,event_type,name) FROM STDIN') as copy:
        for row in calendar_rows(core_city_ids):
            copy.write_row(row)


def write_private_files(result):
    """The solution stays outside the database, in the git-ignored private/ directory."""
    PRIVATE_DIR.mkdir(parents=True, exist_ok=True)
    with open(PRIVATE_DIR / 'ground_truth.csv', 'w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(['reservation_id', 'segment'])
        writer.writerows((b.reservation_id, b.segment) for b in result.bookings)
    with open(PRIVATE_DIR / 'stories.json', 'w', encoding='utf-8') as file:
        json.dump(result.stories, file, indent=2, ensure_ascii=False)


def progress(msg):
    print(f'[{time.strftime("%H:%M:%S")}] {msg}', flush=True)


def refresh_analytics(conn):
    """Refresh the analytics materialized views, if the schema exists (scripts/setup_analytics.py)."""
    if conn.execute("SELECT 1 FROM pg_namespace WHERE nspname = 'analytics'").fetchone() is None:
        return
    # Creation order (oid), so views that read other views are refreshed after them
    views = [row[0] for row in conn.execute(
        "SELECT matviewname FROM pg_matviews WHERE schemaname = 'analytics' "
        "ORDER BY format('%I.%I', schemaname, matviewname)::regclass::oid")]
    progress(f'Refreshing {len(views)} materialized views in schema analytics')
    for view in views:
        conn.execute(sql.SQL('REFRESH MATERIALIZED VIEW {}.{}').format(
            sql.Identifier('analytics'), sql.Identifier(view)))
    conn.commit()


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
    try:
        url = resolve_db_url(os.environ, 'SEED_DATABASE_URL')
    except RuntimeError as error:
        parser.error(str(error))
    if not url:
        parser.error('SEED_DATABASE_URL missing (set it from .env)')
    progress(f"target={os.environ.get('DB_TARGET') or 'default'} -> {describe_target(url)}")
    p = PROFILES[args.profile]
    if p.hotels < p.cities:
        parser.error('profile needs hotels >= cities so every city has a hotel')
    if p.core_hotels > 0 and p.cities < MIN_CITIES_WITH_CORE:
        parser.error(f'profile with core hotels needs cities >= {MIN_CITIES_WITH_CORE}')
    rooms = p.hotels * (p.std + p.deluxe + p.suites) + p.core_hotels * sum(CORE_CAPACITY.values())
    progress(f'profile={args.profile}: cities={p.cities}, hotels={p.hotels}, core_hotels={p.core_hotels}, '
             f'rooms={rooms:,}, guests={p.guests:,}, reservations={p.reservations:,}')
    with psycopg.connect(url, connect_timeout=10) as conn:
        if conn.execute("SELECT to_regclass('daily_rates')").fetchone()[0] is None:
            parser.error('Tabelle daily_rates fehlt: Die Datenbank hat noch das alte Schema. '
                         'Bitte die Datenbank mit db/init/01_schema.sql neu anlegen und den Seed erneut starten.')
        if args.reset:
            progress('RESET: deleting all synthetic rows and resetting identities')
            conn.execute('TRUNCATE reservations, guests, rooms, room_categories, hotels, cities, '
                         'daily_rates, calendar_events RESTART IDENTITY CASCADE')
            conn.commit()
        if conn.execute('SELECT EXISTS(SELECT 1 FROM hotels)').fetchone()[0]:
            parser.error('Database already contains hotels. Re-run with --reset --i-understand-data-loss.')
        with conn.cursor() as cur:
            rng = random.Random(RANDOM_SEED)
            cities = build_cities(p.cities, rng, p.core_hotels > 0)
            cur.executemany('INSERT INTO cities(name,country) VALUES(%s,%s)', cities)
            city_rows = cur.execute('SELECT id, name, country FROM cities ORDER BY id').fetchall()
            hotels = build_hotels(p.hotels, [r[0] for r in city_rows],
                                  [r[1] for r in city_rows], rng)
            cur.executemany('INSERT INTO hotels(city_id,name,address,stars) VALUES(%s,%s,%s,%s)',
                            hotels)
            # Name and country together: Faker may invent the same name in another country.
            city_id_by_key = {(name, country): city_id for city_id, name, country in city_rows}
            core_city_ids = {}
            if p.core_hotels > 0:
                core_city_ids = {c.name: city_id_by_key[(c.name, c.country)] for c in CORE_CITIES}
                core_hotels = build_core_hotels(p.core_hotels, core_city_ids, rng)
                cur.executemany('''
                    INSERT INTO hotels(city_id,name,address,stars,city_type,bundesland)
                    VALUES(%s,%s,%s,%s,%s,%s)
                ''', core_hotels)
            # ORDER BY h.id: normal hotels come first, so their categories get the lowest ids.
            cur.execute('''
                INSERT INTO room_categories(hotel_id,name,base_price,max_guests)
                SELECT h.id, c.name, c.price, c.max_guests
                FROM hotels h CROSS JOIN (VALUES
                   ('Standard',99.00,2),('Deluxe',149.00,3),('Suite',249.00,4)
                ) AS c(name,price,max_guests)
                ORDER BY h.id, c.price
            ''')
            cur.execute('''
                INSERT INTO rooms(category_id,room_number)
                SELECT c.id,
                   CASE c.name WHEN 'Standard' THEN 'STD-'
                               WHEN 'Deluxe' THEN 'DLX-' ELSE 'STE-' END
                   || lpad(n::text,3,'0')
                FROM room_categories c
                JOIN hotels h ON h.id = c.hotel_id
                CROSS JOIN LATERAL generate_series(1,
                  CASE WHEN h.city_type IS NULL THEN
                    CASE c.name WHEN 'Standard' THEN %s::int
                                WHEN 'Deluxe' THEN %s::int ELSE %s::int END
                  ELSE
                    CASE c.name WHEN 'Standard' THEN %s::int
                                WHEN 'Deluxe' THEN %s::int ELSE %s::int END
                  END
                ) AS n
            ''', (p.std, p.deluxe, p.suites, CORE_CAPACITY['Standard'],
                  CORE_CAPACITY['Deluxe'], CORE_CAPACITY['Suite']))
            first_category, normal_categories = cur.execute('''
                SELECT min(c.id), count(*)
                FROM room_categories c
                JOIN hotels h ON h.id = c.hotel_id
                WHERE h.city_type IS NULL
            ''').fetchone()
        conn.commit()
        progress('Cities, hotels, categories and rooms ready')
        for start in range(1, p.guests + 1, args.batch):
            end = min(start + args.batch - 1, p.guests)
            # The company draw uses modulo 101, so it is independent of the
            # business rule, which only depends on g modulo 100.
            conn.execute('''
                INSERT INTO guests(first_name,last_name,email,home_state,company)
                SELECT (%(first_names)s::text[])[1 + (g %% %(first_count)s)],
                       (%(last_names)s::text[])[1 + (g %% %(last_count)s)],
                       'gast' || g::text || '@example.test',
                       (%(states)s::text[])[1 + ((g*31) %% 20)],
                       CASE WHEN (g*48271) %% 101 <
                                 CASE WHEN (g*2654435761) %% 100 < 35 THEN 60 ELSE 15 END
                            THEN (%(companies)s::text[])[1 + (g %% %(company_count)s)]
                       END
                FROM generate_series(%(start)s::bigint,%(end)s::bigint) AS g
            ''', {'first_names': FIRST_NAMES, 'first_count': len(FIRST_NAMES),
                  'last_names': LAST_NAMES, 'last_count': len(LAST_NAMES),
                  'states': STATE_SLOTS, 'companies': COMPANIES,
                  'company_count': len(COMPANIES), 'start': start, 'end': end})
            conn.commit()
            if end == p.guests or end % (args.batch * 5) == 0:
                progress(f'Guests: {end:,} / {p.guests:,}')
        core_count = 0
        if p.core_hotels > 0:
            with conn.cursor() as cur:
                progress('Generating core bookings, prices and stories')
                result = generate_core(load_core_categories(cur), min(p.guests, CORE_GUEST_POOL), p.guests + 1, RANDOM_SEED)
                core_count = len(result.bookings)
                progress(f'Loading {core_count:,} core reservations and {len(result.rates):,} daily rates')
                insert_story_guests(cur, result.story_guests)
                copy_reservations(cur, result.bookings)
                copy_daily_rates(cur, result.rates, result.closed)
                copy_calendar_events(cur, core_city_ids)
            conn.commit()
            write_private_files(result)
            progress(f'Ground truth written to {PRIVATE_DIR}')
        background = max(0, p.reservations - core_count)
        for start in range(1, background + 1, args.batch):
            end = min(start + args.batch - 1, background)
            conn.execute('''
                INSERT INTO reservations(guest_id,category_id,checkin,checkout,status,created_at)
                SELECT 1 + ((g-1) %% %s),
                       %s + (((g-1)*37) %% %s),
                       s.checkin,
                       s.checkin + (1 + (g %% 4))::int,
                       'confirmed',
                       s.checkin - (g %% 60)::int
                FROM (
                    SELECT g, date '2023-01-01' + ((g*7) %% 1900)::int AS checkin
                    FROM generate_series(%s::bigint,%s::bigint) AS g
                ) AS s
            ''', (p.guests, first_category, normal_categories, start, end))
            conn.commit()
            if end == background or end % (args.batch * 5) == 0:
                progress(f'Background reservations: {end:,} / {background:,}')
        progress('ANALYZE (required for meaningful query plans and dashboard stats)')
        for table in ('cities', 'hotels', 'room_categories', 'rooms', 'guests', 'reservations',
                      'daily_rates', 'calendar_events'):
            conn.execute('ANALYZE ' + table)
        conn.commit()
        refresh_analytics(conn)
        progress('DONE. Sample lookup: gast1@example.test')
        progress('MISSION-01: guests.email has intentionally NO INDEX.')


if __name__ == '__main__':
    main()
