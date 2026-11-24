import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'scripts'))
import setup_azure_db as setup  # noqa: E402

HOST = 'azure.example.test'


def env(**overrides):
    base = {
        'AZURE_PG_HOST': HOST,
        'AZURE_SEED_DATABASE_URL': f'postgresql://hotel_owner:own%40er@{HOST}:5432/hoteldb?sslmode=require',
        'AZURE_DATABASE_URL': f'postgresql://hotel_app:app@{HOST}:5432/hoteldb?sslmode=require',
        'AZURE_STUDENT_DATABASE_URL': f'postgresql://hotel_student:stu@{HOST}:5432/hoteldb?sslmode=require',
    }
    return {**base, **overrides}


def test_passwords_come_from_the_urls_and_are_decoded():
    assert setup.role_passwords(env()) == {
        'hotel_owner': 'own@er', 'hotel_app': 'app', 'hotel_student': 'stu'}


def test_placeholder_password_is_rejected():
    with pytest.raises(RuntimeError, match='placeholder'):
        setup.role_passwords(env(AZURE_DATABASE_URL=f'postgresql://hotel_app:<APP_PASSWORD>@{HOST}/hoteldb'))


def test_wrong_user_host_or_database_is_rejected():
    with pytest.raises(RuntimeError, match='must use the user hotel_app'):
        setup.role_passwords(env(AZURE_DATABASE_URL=f'postgresql://other:x@{HOST}/hoteldb'))
    with pytest.raises(RuntimeError, match='AZURE_PG_HOST'):
        setup.role_passwords(env(AZURE_DATABASE_URL='postgresql://hotel_app:x@elsewhere.test/hoteldb'))
    with pytest.raises(RuntimeError, match='database hoteldb'):
        setup.role_passwords(env(AZURE_DATABASE_URL=f'postgresql://hotel_app:x@{HOST}/postgres'))


def test_grants_are_split_between_admin_and_owner():
    admin, owner = setup.split_grants(setup.sql_statements(setup.INIT_DIR / '02_grants.sql'))
    assert admin and all(s.upper().startswith('ALTER ROLE HOTEL_STUDENT') for s in admin)
    assert owner and all(s.upper().startswith('GRANT') for s in owner)
    assert any('default_transaction_read_only' in s for s in admin)


def test_schema_statements_keep_the_email_index_out():
    statements = setup.sql_statements(setup.INIT_DIR / '01_schema.sql')
    assert len(statements) > 5
    assert not any('INDEX' in s.upper() and 'EMAIL' in s.upper() for s in statements)
