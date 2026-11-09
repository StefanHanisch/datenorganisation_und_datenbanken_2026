import pytest

from app.sql_lab import SqlRejected, validate_student_query


def test_simple_select_is_accepted():
    assert validate_student_query("SELECT id, name FROM hotels LIMIT 3") == "SELECT id, name FROM hotels LIMIT 3"


def test_cte_select_is_accepted():
    assert validate_student_query("WITH c AS (SELECT id FROM cities) SELECT * FROM c").startswith("WITH")


@pytest.mark.parametrize("query", [
    "DELETE FROM guests", "DROP TABLE hotels", "UPDATE guests SET email='x'",
    "SELECT 1; DELETE FROM guests", "SELECT 1; SELECT 2", "",
    "WITH x AS (DELETE FROM guests RETURNING id) SELECT * FROM x",
    "EXPLAIN ANALYZE DELETE FROM guests",
])
def test_writes_or_multiple_statements_are_rejected(query):
    with pytest.raises(SqlRejected):
        validate_student_query(query)


def test_semicolon_in_string_is_safe():
    assert validate_student_query("SELECT 'a;b' AS value;") == "SELECT 'a;b' AS value;"
