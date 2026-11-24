import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'scripts'))
import setup_analytics as setup  # noqa: E402

HOST = 'azure.example.test'


def env(**overrides):
    base = {
        'DB_TARGET': 'azure',
        'AZURE_ANALYST_DATABASE_URL': f'postgresql://hotel_analyst:an%40lyst%23@{HOST}:5432/hoteldb?sslmode=require',
        'LOCAL_ANALYST_DATABASE_URL': 'postgresql://hotel_analyst:local_pw@localhost:5433/hoteldb',
    }
    return {**base, **overrides}


def test_password_comes_from_the_url_of_the_target_and_is_decoded():
    assert setup.analyst_password(env()) == 'an@lyst#'
    assert setup.analyst_password(env(DB_TARGET='local')) == 'local_pw'


def test_placeholder_password_is_rejected():
    with pytest.raises(RuntimeError, match='placeholder'):
        setup.analyst_password(env(AZURE_ANALYST_DATABASE_URL=f'postgresql://hotel_analyst:<ANALYST_PASSWORD>@{HOST}/hoteldb'))


def test_wrong_user_database_or_missing_password_is_rejected():
    with pytest.raises(RuntimeError, match='must use the user hotel_analyst'):
        setup.analyst_password(env(AZURE_ANALYST_DATABASE_URL=f'postgresql://hotel_student:x@{HOST}/hoteldb'))
    with pytest.raises(RuntimeError, match='database hoteldb'):
        setup.analyst_password(env(AZURE_ANALYST_DATABASE_URL=f'postgresql://hotel_analyst:x@{HOST}/postgres'))
    with pytest.raises(RuntimeError, match='no password'):
        setup.analyst_password(env(AZURE_ANALYST_DATABASE_URL=f'postgresql://hotel_analyst@{HOST}/hoteldb'))


def test_analytics_views_are_the_seven_tables():
    assert set(setup.ANALYTICS_VIEWS) == {
        'cities', 'hotels', 'room_categories', 'guests', 'reservations', 'daily_rates', 'calendar_events'}
    assert len(setup.ANALYTICS_VIEWS) == 7


def test_drop_and_truncate_are_refused():
    with pytest.raises(RuntimeError, match='DROP/TRUNCATE'):
        setup.check_no_destructive(['CREATE SCHEMA IF NOT EXISTS analytics', 'DROP SCHEMA analytics CASCADE'])
    with pytest.raises(RuntimeError, match='DROP/TRUNCATE'):
        setup.check_no_destructive(['truncate public.guests'])
    setup.check_no_destructive(['CREATE MATERIALIZED VIEW IF NOT EXISTS analytics.cities AS SELECT 1'])


def test_analytics_sql_is_split_between_admin_and_owner():
    if not setup.ANALYTICS_SQL.exists():
        pytest.skip('db/init/03_analytics.sql does not exist yet')
    admin, owner = setup.analytics_statements()
    assert admin and all(s.upper().startswith('ALTER ROLE HOTEL_ANALYST') for s in admin)
    assert owner and not any(s.upper().startswith('ALTER ROLE') for s in owner)
    assert any(s.upper().startswith('CREATE SCHEMA') for s in owner)
    for name in setup.ANALYTICS_VIEWS:
        assert any('MATERIALIZED VIEW' in s.upper() and f'ANALYTICS.{name.upper()}' in s.upper() for s in owner), name
