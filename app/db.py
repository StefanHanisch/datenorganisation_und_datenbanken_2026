"""No globally shared database cursors: each request owns one connection/transaction."""
from contextlib import contextmanager
from typing import Iterator
import psycopg
from psycopg import Connection
from psycopg.rows import dict_row
from app.config import get_settings


@contextmanager
def db_connection(role: str = 'app') -> Iterator[Connection]:
    settings = get_settings()
    if role not in ('app', 'student'):
        raise ValueError('Invalid application role')
    url = settings.student_database_url if role == 'student' else settings.database_url
    # HTTPS to Azure does not automatically imply encrypted DB traffic.
    # Use sslmode=require/verify-full in production connection strings.
    with psycopg.connect(url, row_factory=dict_row, connect_timeout=8) as conn:
        yield conn
