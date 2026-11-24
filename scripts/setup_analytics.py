#!/usr/bin/env python3
"""Set up the read-only analytics area: role hotel_analyst + schema analytics (materialized views).

The target follows DB_TARGET=local|azure in .env. The SQL lives in db/init/03_analytics.sql and is
reused, not copied. Never drops or truncates anything; running it twice is safe.

  python scripts/setup_analytics.py            # DRY RUN: checks logins read-only, shows the plan, changes nothing
  python scripts/setup_analytics.py --apply    # creates the role, runs 03_analytics.sql, self test (teacher approval needed)
  python scripts/setup_analytics.py --refresh  # only REFRESH MATERIALIZED VIEW analytics.* (as hotel_owner), self test

The password for hotel_analyst is taken from <TARGET>_ANALYST_DATABASE_URL in .env.
An existing hotel_analyst role gets that password again (.env is the source of truth).
Admin work runs as AZURE_PG_ADMIN_USER on Azure and as hotel_owner (superuser) locally.
"""
import argparse
import os
import sys
import time
from pathlib import Path
from urllib.parse import unquote, urlsplit

import psycopg
from dotenv import load_dotenv
from psycopg import sql

from app.db_target import TARGETS, describe_target, resolve_db_url
from setup_azure_db import connect, exists, split_grants, sql_statements

ANALYTICS_SQL = Path(__file__).resolve().parent.parent / 'db' / 'init' / '03_analytics.sql'
DB_NAME = 'hoteldb'
ROLE = 'hotel_analyst'
SCHEMA = 'analytics'
ANALYTICS_VIEWS = ('cities', 'hotels', 'room_categories', 'guests',
                   'reservations', 'daily_rates', 'calendar_events')
FORBIDDEN = ('DROP', 'TRUNCATE')  # this script never deletes anything


def analyst_password(env) -> str:
    """Read the hotel_analyst password from the ANALYST_DATABASE_URL of the selected target."""
    url = resolve_db_url(env, 'ANALYST_DATABASE_URL')  # raises on empty value or <placeholder>
    parts = urlsplit(url)
    if parts.username != ROLE:
        raise RuntimeError(f'ANALYST_DATABASE_URL must use the user {ROLE}, not {parts.username}')
    if parts.path.lstrip('/') != DB_NAME:
        raise RuntimeError(f'ANALYST_DATABASE_URL must use the database {DB_NAME}')
    if not parts.password:
        raise RuntimeError('ANALYST_DATABASE_URL has no password')
    return unquote(parts.password)


def analytics_statements() -> tuple[list[str], list[str]]:
    """Split 03_analytics.sql: ALTER ROLE needs the admin, everything else runs as hotel_owner."""
    if not ANALYTICS_SQL.exists():
        raise RuntimeError(f'{ANALYTICS_SQL.name} fehlt in db/init/')
    statements = sql_statements(ANALYTICS_SQL)
    check_no_destructive(statements)
    return split_grants(statements)


def check_no_destructive(statements: list[str]) -> None:
    for statement in statements:
        if statement.split(None, 1)[0].upper() in FORBIDDEN:
            raise RuntimeError(f'03_analytics.sql enthält DROP/TRUNCATE - wird nicht ausgeführt: {statement[:60]}')


def admin_connect(env, dbname: str, read_only: bool = False) -> psycopg.Connection:
    """Azure: the server admin. Local: hotel_owner, who is superuser in the Docker database."""
    if env['DB_TARGET'] == 'azure':
        conn = connect(env, dbname, env['AZURE_PG_ADMIN_USER'], env['AZURE_PG_ADMIN_PASSWORD'], autocommit=True)
    else:
        conn = psycopg.connect(resolve_db_url(env, 'SEED_DATABASE_URL'), connect_timeout=15, autocommit=True)
    if read_only:
        conn.read_only = True
    return conn


def owner_connect(env) -> psycopg.Connection:
    return psycopg.connect(resolve_db_url(env, 'SEED_DATABASE_URL'), connect_timeout=15)


def analyst_connect(env) -> psycopg.Connection:
    return psycopg.connect(resolve_db_url(env, 'ANALYST_DATABASE_URL'), connect_timeout=15)


def dry_run(env, password):
    grants_admin, grants_owner = analytics_statements()
    with admin_connect(env, 'postgres' if env['DB_TARGET'] == 'azure' else DB_NAME, read_only=True) as conn:
        state = 'vorhanden (Passwort wird gesetzt)' if exists(
            conn, 'SELECT 1 FROM pg_roles WHERE rolname = %s', ROLE) else 'wird angelegt'
        print(f'  Rolle  {ROLE:14} {state}')
    with owner_connect(env) as conn:
        conn.read_only = True
        if exists(conn, 'SELECT 1 FROM pg_namespace WHERE nspname = %s', SCHEMA):
            views = conn.execute('SELECT count(*) FROM pg_matviews WHERE schemaname = %s', (SCHEMA,)).fetchone()[0]
            print(f'  Schema {SCHEMA:14} vorhanden, {views} von {len(ANALYTICS_VIEWS)} Materialized Views')
        else:
            print(f'  Schema {SCHEMA:14} wird angelegt')
    print(f'  SQL    {ANALYTICS_SQL.name}: {len(grants_owner)} Statements als hotel_owner, '
          f'{len(grants_admin)} als Admin:')
    for statement in grants_admin:
        print(f'         {statement}')
    print('\nVORSCHAU - es wurde nichts geändert. Zum Ausführen: --apply')


def apply(env, password):
    grants_admin, grants_owner = analytics_statements()
    roles_db = 'postgres' if env['DB_TARGET'] == 'azure' else DB_NAME

    print(f'1/4 Rolle {ROLE} anlegen (als Admin)')
    with admin_connect(env, roles_db) as conn:
        known = exists(conn, 'SELECT 1 FROM pg_roles WHERE rolname = %s', ROLE)
        verb = 'ALTER' if known else 'CREATE'
        conn.execute(sql.SQL(f'{verb} ROLE {{}} LOGIN PASSWORD {{}}').format(
            sql.Identifier(ROLE), sql.Literal(password)))
        print(f'    {verb} ROLE {ROLE}')
    with admin_connect(env, DB_NAME) as conn:
        conn.execute(sql.SQL('GRANT CONNECT ON DATABASE {} TO {}').format(
            sql.Identifier(DB_NAME), sql.Identifier(ROLE)))
        print(f'    GRANT CONNECT ON DATABASE {DB_NAME} TO {ROLE}')

    print(f'2/4 {ANALYTICS_SQL.name} ausführen (als hotel_owner, eine Transaktion)')
    started = time.perf_counter()
    with owner_connect(env) as conn:
        for statement in grants_owner:
            conn.execute(statement)
    print(f'    {len(grants_owner)} Statements ausgeführt in {time.perf_counter() - started:.1f} s')

    print(f'3/4 Rollen-Einstellungen für {ROLE} (als Admin)')
    with admin_connect(env, roles_db) as conn:
        for statement in grants_admin:
            conn.execute(statement)
            print(f'    {statement}')

    print('4/4 Selbsttest')
    verify(env)


def refresh_views(conn):
    """Recompute all analytics materialized views (needs the owner, i.e. hotel_owner)."""
    for name in ANALYTICS_VIEWS:
        started = time.perf_counter()
        conn.execute(sql.SQL('REFRESH MATERIALIZED VIEW {}').format(sql.Identifier(SCHEMA, name)))
        print(f'    REFRESH {SCHEMA}.{name:16} {time.perf_counter() - started:6.1f} s')


def refresh(env, password):
    print('1/2 Materialized Views neu berechnen (als hotel_owner)')
    with owner_connect(env) as conn:
        refresh_views(conn)
    print('2/2 Selbsttest')
    verify(env)


def verify(env):
    with analyst_connect(env) as conn:
        timeout = conn.execute('SHOW statement_timeout').fetchone()[0]
        print(f'    {ROLE}: statement_timeout={timeout}')
        for name in ANALYTICS_VIEWS:
            rows = conn.execute(sql.SQL('SELECT count(*) FROM {}').format(sql.Identifier(SCHEMA, name))).fetchone()[0]
            print(f'    {SCHEMA}.{name:16} {rows:>12,} Zeilen')

        started = time.perf_counter()
        rows = conn.execute('SELECT * FROM analytics.reservations').fetchall()
        print(f'    SELECT * FROM analytics.reservations: {len(rows):,} Zeilen in '
              f'{time.perf_counter() - started:.2f} s')
        conn.rollback()

        # Writing must fail, in public and in analytics (a materialized view cannot take INSERTs,
        # so for analytics we try to create a table instead).
        write_probes = {
            'public': "INSERT INTO public.cities(name, country) VALUES ('x', 'x')",
            'analytics': 'CREATE TABLE analytics.analyst_probe (id int)',
        }
        for schema, statement in write_probes.items():
            try:
                conn.execute(statement)
                raise RuntimeError(f'FEHLER: {ROLE} darf in {schema} schreiben!')
            except psycopg.errors.DatabaseError:
                conn.rollback()
        print(f'    {ROLE}: Schreiben in public und {SCHEMA} abgelehnt')

        try:
            conn.execute('SELECT 1 FROM public.guests LIMIT 1')
            raise RuntimeError(f'FEHLER: {ROLE} darf public.guests lesen!')
        except psycopg.errors.InsufficientPrivilege:
            conn.rollback()
        print(f'    {ROLE}: Lesen von public.guests abgelehnt (nur {SCHEMA}.* erlaubt)')


def main():
    load_dotenv()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--apply', action='store_true', help='make the changes (default: dry run)')
    mode.add_argument('--refresh', action='store_true', help='only refresh the materialized views')
    args = parser.parse_args()
    env = dict(os.environ)
    env['DB_TARGET'] = (env.get('DB_TARGET') or '').strip().lower()
    if env['DB_TARGET'] not in TARGETS:
        parser.error("DB_TARGET must be 'local' or 'azure' in .env")
    if env['DB_TARGET'] == 'azure':
        for key in ('AZURE_PG_HOST', 'AZURE_PG_ADMIN_USER', 'AZURE_PG_ADMIN_PASSWORD'):
            if not env.get(key):
                parser.error(f'{key} is empty in .env')
    try:
        password = analyst_password(env)
        print(f"Ziel: DB_TARGET={env['DB_TARGET']}, "
              f"hotel_owner -> {describe_target(resolve_db_url(env, 'SEED_DATABASE_URL'))}, "
              f"{ROLE} -> {describe_target(resolve_db_url(env, 'ANALYST_DATABASE_URL'))}")
        action = apply if args.apply else refresh if args.refresh else dry_run
        action(env, password)
    except (RuntimeError, psycopg.Error) as error:
        message = str(error).strip().splitlines()[0]
        sys.exit(message if message.startswith('FEHLER') else f'FEHLER: {message}')


if __name__ == '__main__':
    main()
