#!/usr/bin/env python3
"""Set up HotelDB on the Azure PostgreSQL server: roles, database, schema, grants.

Does the same as db/init/*.sh|sql do for the local Docker database, but on Azure,
where the admin user (AZURE_PG_ADMIN_*) is not a superuser. The SQL files are reused,
not copied. Never drops or truncates anything; running it twice is safe.

  python scripts/setup_azure_db.py            # DRY RUN: checks login, shows the plan, changes nothing
  python scripts/setup_azure_db.py --apply    # really sets everything up (teacher approval needed)

Passwords for hotel_owner / hotel_app / hotel_student are taken from the AZURE_*_DATABASE_URL
values in .env. An existing hotel_* role gets that password again (.env is the source of truth).
"""
import argparse
import os
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

import psycopg
import sqlparse
from dotenv import load_dotenv
from psycopg import sql

from app.db_target import describe_target, resolve_db_url

INIT_DIR = Path(__file__).resolve().parent.parent / 'db' / 'init'
DB_NAME = 'hoteldb'
# role -> the .env variable (without AZURE_ prefix) whose URL holds its password
ROLES = {
    'hotel_owner': 'SEED_DATABASE_URL',
    'hotel_app': 'DATABASE_URL',
    'hotel_student': 'STUDENT_DATABASE_URL',
}


def role_passwords(env) -> dict[str, str]:
    """Read the three role passwords from the AZURE_* URLs and check they fit together."""
    azure_env = {**env, 'DB_TARGET': 'azure'}
    passwords = {}
    for role, name in ROLES.items():
        url = resolve_db_url(azure_env, name)  # raises on empty value or <placeholder>
        parts = urlsplit(url)
        if parts.username != role:
            raise RuntimeError(f'AZURE_{name} must use the user {role}, not {parts.username}')
        if parts.hostname != env.get('AZURE_PG_HOST'):
            raise RuntimeError(f'AZURE_{name} points to {parts.hostname}, not to AZURE_PG_HOST')
        if parts.path.lstrip('/') != DB_NAME:
            raise RuntimeError(f'AZURE_{name} must use the database {DB_NAME}')
        if not parts.password:
            raise RuntimeError(f'AZURE_{name} has no password')
        passwords[role] = unquote(parts.password)
    return passwords


def sql_statements(path: Path) -> list[str]:
    """Split a SQL file into single statements without comments."""
    cleaned = (sqlparse.format(s, strip_comments=True).strip() for s in sqlparse.split(path.read_text()))
    return [s for s in cleaned if s and s != ';']


def split_grants(statements: list[str]) -> tuple[list[str], list[str]]:
    """ALTER ROLE needs the admin user; everything else runs as hotel_owner (owner of the tables)."""
    admin = [s for s in statements if s.upper().startswith('ALTER ROLE')]
    owner = [s for s in statements if s not in admin]
    return admin, owner


def connect(env, dbname: str, user: str, password: str, autocommit: bool = False) -> psycopg.Connection:
    return psycopg.connect(host=env['AZURE_PG_HOST'], port=int(env.get('AZURE_PG_PORT') or 5432),
                           dbname=dbname, user=user, password=password,
                           sslmode=env.get('AZURE_PG_SSLMODE') or 'require',
                           connect_timeout=15, autocommit=autocommit)


def exists(conn, query: str, value: str) -> bool:
    return conn.execute(query, (value,)).fetchone() is not None


def dry_run(env, passwords):
    with connect(env, 'postgres', env['AZURE_PG_ADMIN_USER'], env['AZURE_PG_ADMIN_PASSWORD']) as conn:
        conn.read_only = True
        for role in ROLES:
            state = 'vorhanden (Passwort wird gesetzt)' if exists(
                conn, 'SELECT 1 FROM pg_roles WHERE rolname = %s', role) else 'wird angelegt'
            print(f'  Rolle {role:14} {state}')
        state = 'vorhanden' if exists(conn, 'SELECT 1 FROM pg_database WHERE datname = %s', DB_NAME) \
            else 'wird angelegt (Owner hotel_owner)'
        print(f'  Datenbank {DB_NAME:12} {state}')
    print('  Schema   db/init/01_schema.sql (CREATE ... IF NOT EXISTS, kein Index auf guests.email)')
    print('  Rechte   db/init/02_grants.sql (app: lesen/schreiben, student: nur lesen, 4 s Timeout)')
    print('\nVORSCHAU - es wurde nichts geändert. Zum Ausführen: --apply')


def apply(env, passwords):
    admin, admin_pw = env['AZURE_PG_ADMIN_USER'], env['AZURE_PG_ADMIN_PASSWORD']
    grants_admin, grants_owner = split_grants(sql_statements(INIT_DIR / '02_grants.sql'))

    print('1/4 Rollen und Datenbank anlegen (als Admin)')
    with connect(env, 'postgres', admin, admin_pw, autocommit=True) as conn:
        for role, password in passwords.items():
            known = exists(conn, 'SELECT 1 FROM pg_roles WHERE rolname = %s', role)
            verb = 'ALTER' if known else 'CREATE'
            conn.execute(sql.SQL(f'{verb} ROLE {{}} LOGIN PASSWORD {{}}').format(
                sql.Identifier(role), sql.Literal(password)))
            print(f'    {verb} ROLE {role}')
        # The admin must be allowed to SET ROLE hotel_owner to create its database.
        # PostgreSQL 16+ needs the explicit SET option; older versions do not know the syntax.
        with_set = ' WITH SET TRUE' if conn.info.server_version >= 160000 else ''
        conn.execute(sql.SQL('GRANT hotel_owner TO {}' + with_set).format(sql.Identifier(admin)))
        if exists(conn, 'SELECT 1 FROM pg_database WHERE datname = %s', DB_NAME):
            print(f'    Datenbank {DB_NAME} existiert schon')
        else:
            conn.execute(sql.SQL('CREATE DATABASE {} OWNER hotel_owner').format(sql.Identifier(DB_NAME)))
            print(f'    CREATE DATABASE {DB_NAME}')
    # On Azure the schema "public" belongs to azure_pg_admin (not to the database owner as locally),
    # so only the admin can hand out its rights. Locally this is done by db/init/00_roles.sh.
    with connect(env, DB_NAME, admin, admin_pw, autocommit=True) as conn:
        conn.execute(sql.SQL('GRANT CONNECT ON DATABASE {} TO hotel_app, hotel_student').format(
            sql.Identifier(DB_NAME)))
        conn.execute('REVOKE CREATE ON SCHEMA public FROM PUBLIC')
        conn.execute('GRANT USAGE, CREATE ON SCHEMA public TO hotel_owner')
        conn.execute('GRANT USAGE ON SCHEMA public TO hotel_app, hotel_student')
        print('    Schema public: hotel_owner darf anlegen, hotel_app/hotel_student nur nutzen')

    print('2/4 Schema und Tabellenrechte (als hotel_owner)')
    with connect(env, DB_NAME, 'hotel_owner', passwords['hotel_owner']) as conn:
        for statement in sql_statements(INIT_DIR / '01_schema.sql') + grants_owner:
            conn.execute(statement)
        print('    01_schema.sql und Tabellenrechte aus 02_grants.sql ausgeführt')

    print('3/4 Rollen-Einstellungen für hotel_student (als Admin)')
    with connect(env, 'postgres', admin, admin_pw, autocommit=True) as conn:
        for statement in grants_admin:
            conn.execute(statement)
            print(f'    {statement}')

    print('4/4 Selbsttest')
    verify(env, passwords)


def verify(env, passwords):
    with connect(env, DB_NAME, 'hotel_owner', passwords['hotel_owner']) as conn:
        tables = conn.execute("SELECT count(*) FROM pg_tables WHERE schemaname = 'public'").fetchone()[0]
        email_idx = conn.execute("SELECT count(*) FROM pg_indexes WHERE tablename = 'guests' "
                                 "AND indexdef ILIKE '%(email)%'").fetchone()[0]
        print(f'    hotel_owner : {tables} Tabellen, Indizes auf guests.email: {email_idx} (muss 0 sein)')
    with connect(env, DB_NAME, 'hotel_app', passwords['hotel_app']) as conn:
        conn.execute('SELECT count(*) FROM cities').fetchone()
        print('    hotel_app   : darf lesen')
    with connect(env, DB_NAME, 'hotel_student', passwords['hotel_student']) as conn:
        conn.execute('SELECT count(*) FROM cities').fetchone()
        timeout = conn.execute('SHOW statement_timeout').fetchone()[0]
        try:
            conn.execute("INSERT INTO cities(name, country) VALUES ('x', 'x')")
            raise RuntimeError('FEHLER: hotel_student darf schreiben!')
        except psycopg.errors.DatabaseError:
            conn.rollback()
        print(f'    hotel_student: darf lesen, Schreiben abgelehnt, statement_timeout={timeout}')


def main():
    load_dotenv()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--apply', action='store_true', help='make the changes (default: dry run)')
    args = parser.parse_args()
    env = dict(os.environ)
    for key in ('AZURE_PG_HOST', 'AZURE_PG_ADMIN_USER', 'AZURE_PG_ADMIN_PASSWORD'):
        if not env.get(key):
            parser.error(f'{key} is empty in .env')
    try:
        passwords = role_passwords(env)
        print(f"Ziel: {env['AZURE_PG_HOST']} (Admin: {env['AZURE_PG_ADMIN_USER']}), "
              f"App-URL -> {describe_target(resolve_db_url({**env, 'DB_TARGET': 'azure'}, 'DATABASE_URL'))}")
        (apply if args.apply else dry_run)(env, passwords)
    except (RuntimeError, psycopg.Error) as error:
        sys.exit(f'FEHLER: {str(error).strip().splitlines()[0]}')


if __name__ == '__main__':
    main()
