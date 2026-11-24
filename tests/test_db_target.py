import pytest

from app.config import Settings
from app.db_target import describe_target, resolve_db_url

URLS = {
    'DATABASE_URL': 'postgresql://hotel_app:legacy@localhost/hoteldb',
    'LOCAL_DATABASE_URL': 'postgresql://hotel_app:l@localhost:5433/hoteldb',
    'AZURE_DATABASE_URL': 'postgresql://hotel_app:a@azure.example.test:5432/hoteldb?sslmode=require',
    'AZURE_SEED_DATABASE_URL': 'postgresql://hotel_owner:<OWNER_PASSWORD>@azure.example.test/hoteldb',
}


def test_without_target_the_plain_variable_is_used():
    assert resolve_db_url(URLS, 'DATABASE_URL') == URLS['DATABASE_URL']
    assert resolve_db_url({}, 'DATABASE_URL') == ''


def test_empty_target_counts_as_not_set():
    assert resolve_db_url({**URLS, 'DB_TARGET': '  '}, 'DATABASE_URL') == URLS['DATABASE_URL']


@pytest.mark.parametrize('target, key', [('local', 'LOCAL_DATABASE_URL'),
                                         ('azure', 'AZURE_DATABASE_URL'),
                                         ('AZURE', 'AZURE_DATABASE_URL')])
def test_target_selects_its_own_url_set(target, key):
    assert resolve_db_url({**URLS, 'DB_TARGET': target}, 'DATABASE_URL') == URLS[key]


def test_unknown_target_is_rejected():
    with pytest.raises(RuntimeError, match="'local' or 'azure'"):
        resolve_db_url({**URLS, 'DB_TARGET': 'prod'}, 'DATABASE_URL')


def test_missing_url_of_selected_target_does_not_fall_back_to_the_other_one():
    with pytest.raises(RuntimeError, match='LOCAL_STUDENT_DATABASE_URL is empty'):
        resolve_db_url({**URLS, 'DB_TARGET': 'local'}, 'STUDENT_DATABASE_URL')


def test_placeholder_in_url_is_rejected():
    with pytest.raises(RuntimeError, match='placeholder'):
        resolve_db_url({**URLS, 'DB_TARGET': 'azure'}, 'SEED_DATABASE_URL')


def test_describe_target_hides_user_and_password():
    text = describe_target(URLS['AZURE_DATABASE_URL'])
    assert text == 'azure.example.test:5432/hoteldb'
    assert 'hotel_app' not in text and ':a@' not in text


def test_settings_follow_db_target(monkeypatch):
    for name, value in URLS.items():
        monkeypatch.setenv(name, value)
    monkeypatch.setenv('LOCAL_STUDENT_DATABASE_URL', 'postgresql://hotel_student:s@localhost/hoteldb')
    monkeypatch.setenv('AZURE_STUDENT_DATABASE_URL', 'postgresql://hotel_student:z@azure.example.test/hoteldb')
    monkeypatch.setenv('DB_TARGET', 'azure')
    settings = Settings(_env_file=None)
    assert settings.database_url == URLS['AZURE_DATABASE_URL']
    assert 'azure.example.test' in settings.student_database_url
    monkeypatch.setenv('DB_TARGET', 'local')
    settings = Settings(_env_file=None)
    assert settings.database_url == URLS['LOCAL_DATABASE_URL']
    assert 'localhost' in settings.student_database_url


def test_settings_without_target_keep_legacy_behaviour(monkeypatch):
    monkeypatch.delenv('DB_TARGET', raising=False)
    monkeypatch.setenv('DATABASE_URL', URLS['DATABASE_URL'])
    monkeypatch.setenv('STUDENT_DATABASE_URL', 'postgresql://hotel_student:x@localhost/hoteldb')
    settings = Settings(_env_file=None)
    assert settings.database_url == URLS['DATABASE_URL']
    assert settings.student_database_url.startswith('postgresql://hotel_student')
