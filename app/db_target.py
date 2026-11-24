"""Choose the database for DB_TARGET=local|azure (one switch in .env, no commenting out).

Without DB_TARGET the plain variables (DATABASE_URL, ...) are used as before.
With DB_TARGET=azure the variables AZURE_DATABASE_URL, ... are used instead.
There is no silent fallback: a wrong target never ends up on the other database.
"""
import re
from collections.abc import Mapping
from urllib.parse import urlsplit

TARGETS = ('local', 'azure')
PLACEHOLDER = re.compile(r'<[^<>]+>')  # e.g. <APP_PASSWORD> that was never replaced


def resolve_db_url(env: Mapping[str, str], name: str) -> str:
    """Return the URL for `name` (e.g. 'SEED_DATABASE_URL') of the selected target."""
    target = (env.get('DB_TARGET') or '').strip().lower()
    if not target:
        return env.get(name) or ''
    if target not in TARGETS:
        raise RuntimeError(f"DB_TARGET must be 'local' or 'azure', not '{target}'")
    key = f'{target.upper()}_{name}'
    url = (env.get(key) or '').strip()
    if not url:
        raise RuntimeError(f'DB_TARGET={target}, but {key} is empty in .env')
    if PLACEHOLDER.search(url):
        raise RuntimeError(f'{key} still contains a placeholder such as <APP_PASSWORD>')
    return url


def describe_target(url: str) -> str:
    """Return 'host:port/database' for log lines, never the user name or password."""
    parts = urlsplit(url)
    return f'{parts.hostname or "?"}:{parts.port or 5432}/{parts.path.lstrip("/")}'
