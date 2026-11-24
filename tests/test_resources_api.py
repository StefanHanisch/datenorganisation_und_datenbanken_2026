"""Resource API: access rules, mandatory limits and keyset paging (no database needed)."""
from contextlib import contextmanager

import pytest
from fastapi.testclient import TestClient

import app.resources_api as resources_api
from app.main import app, settings


class FakeResult:
    def __init__(self, rows):
        self.rows = rows

    def fetchall(self):
        return self.rows

    def fetchone(self):
        return self.rows[0] if self.rows else None


class FakeConnection:
    """Returns rooms with id > after_id, at most LIMIT rows, like the real SELECT."""

    def __init__(self, total_rows):
        self.total_rows = total_rows
        self.calls = []

    def execute(self, sql, values):
        self.calls.append((sql, values))
        after_id, limit = values[0], values[-1]
        rows = [{'id': i, 'category_id': 1, 'room_number': str(i), 'is_active': True}
                for i in range(after_id + 1, self.total_rows + 1)]
        return FakeResult(rows[:limit])


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(settings, 'student_access_code', 'student-test-code')
    monkeypatch.setattr(settings, 'teacher_access_code', 'teacher-test-code')
    return TestClient(app)


def login(client, code):
    client.post('/login', data={'code': code}, follow_redirects=False)


@pytest.fixture
def fake_db(monkeypatch):
    conn = FakeConnection(total_rows=5)

    @contextmanager
    def fake_connection(role='app'):
        assert role == 'student', 'reads must use the read-only student role'
        yield conn

    monkeypatch.setattr(resources_api, 'db_connection', fake_connection)
    return conn


def test_reads_require_login(client):
    assert client.get('/api/v1/hotels').status_code == 401


def test_writes_require_teacher(client):
    login(client, 'student-test-code')
    response = client.post('/api/v1/cities', json={'name': 'Testdorf', 'country': 'Deutschland'})
    assert response.status_code == 403


@pytest.mark.parametrize('limit', [0, resources_api.MAX_LIMIT + 1])
def test_limit_is_bounded(client, limit):
    login(client, 'student-test-code')
    assert client.get(f'/api/v1/rooms?limit={limit}').status_code == 422


def test_keyset_paging_walks_through_all_rows(client, fake_db):
    login(client, 'student-test-code')

    first = client.get('/api/v1/rooms?limit=2').json()
    assert [r['id'] for r in first['items']] == [1, 2]
    assert first['next_after_id'] == 2

    second = client.get(f'/api/v1/rooms?limit=2&after_id={first["next_after_id"]}').json()
    assert [r['id'] for r in second['items']] == [3, 4]

    last = client.get(f'/api/v1/rooms?limit=2&after_id={second["next_after_id"]}').json()
    assert [r['id'] for r in last['items']] == [5]
    assert last['next_after_id'] is None

    sql, values = fake_db.calls[0]
    assert 'ORDER BY id LIMIT %s' in sql
    assert values == (0, 3)  # limit + 1 to detect a next page


def test_filter_is_a_parameter_not_sql_text(client, fake_db):
    login(client, 'student-test-code')
    client.get('/api/v1/rooms?category_id=7&limit=10')
    sql, values = fake_db.calls[0]
    assert 'category_id = %s' in sql
    assert values == (0, 7, 11)


def test_swagger_lists_crud_for_every_resource(client):
    paths = client.get('/openapi.json').json()['paths']
    for resource in ('cities', 'hotels', 'room-categories', 'rooms'):
        assert set(paths[f'/api/v1/{resource}']) == {'get', 'post'}
        assert set(paths[f'/api/v1/{resource}/{{{resource_id(resource)}}}']) == {'get', 'put', 'delete'}
    assert not any('guests' in p or p.startswith('/api/v1/reservations') for p in paths)


def resource_id(resource):
    return {'cities': 'city_id', 'hotels': 'hotel_id', 'room-categories': 'category_id', 'rooms': 'room_id'}[resource]
