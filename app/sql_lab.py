"""Student SQL workbench. DB role is security boundary; parsing is just extra defense."""
from typing import Any
import sqlparse
from sqlparse import tokens as T
from psycopg import DatabaseError
from app.config import get_settings
from app.db import db_connection


class SqlRejected(ValueError):
    pass


FORBIDDEN = {
    'INSERT', 'UPDATE', 'DELETE', 'MERGE', 'DROP', 'ALTER', 'CREATE', 'TRUNCATE',
    'GRANT', 'REVOKE', 'COPY', 'CALL', 'DO', 'INTO', 'VACUUM', 'ANALYZE',
    'LOCK', 'SET', 'RESET', 'EXECUTE',
}


def validate_student_query(sql: str) -> str:
    sql = sql.strip()
    if not sql or len(sql) > 8000:
        raise SqlRejected('Please enter one SELECT query (max 8,000 characters).')
    parts = sqlparse.parse(sql)
    if len(parts) != 1 or parts[0].get_type() != 'SELECT':
        raise SqlRejected('Only one SELECT statement (optionally WITH) is allowed.')
    for token in parts[0].flatten():
        if token.ttype in T.Comment or token.ttype in T.Literal.String:
            continue
        if token.ttype in T.Keyword or token.ttype in T.DML or token.ttype in T.DDL:
            if token.value.upper() in FORBIDDEN:
                raise SqlRejected(f'{token.value.upper()} is not permitted in the SQL lab.')
    return sql


def run_student_query(sql: str, explain: bool = False) -> dict[str, Any]:
    statement = validate_student_query(sql)
    s = get_settings()
    try:
        with db_connection('student') as conn:
            # Explicit read-only transaction, in addition to separate read-only DB user.
            conn.execute('SET TRANSACTION READ ONLY')
            conn.execute("SELECT set_config('statement_timeout', %s, true)",
                         (str(s.sql_statement_timeout_ms),))
            if explain:
                # ANALYZE makes the database ACTUALLY run the query. Still read-only and timed.
                plan_sql = 'EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) ' + statement.rstrip(';')
                plan = conn.execute(plan_sql).fetchone()['QUERY PLAN']
                return {'plan': plan, 'type': 'explain'}
            # Server-side cursor avoids materializing millions of rows in FastAPI memory.
            with conn.cursor(name='student_result') as cursor:
                cursor.execute(statement)
                columns = [x.name for x in cursor.description or []]
                rows = cursor.fetchmany(s.sql_max_rows + 1)
                has_more = len(rows) > s.sql_max_rows
                return {
                    'type': 'result', 'columns': columns,
                    'rows': rows[:s.sql_max_rows], 'truncated': has_more,
                    'row_limit': s.sql_max_rows,
                }
    except DatabaseError as exc:
        # Don't expose connection strings; PostgreSQL errors are helpful for SQL teaching.
        message = str(exc).split('\n')[0][:250]
        return {'type': 'error', 'message': message}
