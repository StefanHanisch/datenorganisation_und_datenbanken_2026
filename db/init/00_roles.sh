#!/bin/sh
set -eu
# The default role 'hotel_owner' is created by POSTGRES_USER.
# Passwords are injected, never committed with real values.
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
  -v app_password="$HOTEL_APP_PASSWORD" \
  -v student_password="$HOTEL_STUDENT_PASSWORD" <<'SQL'
SELECT format('CREATE ROLE hotel_app LOGIN PASSWORD %L', :'app_password') \gexec
SELECT format('CREATE ROLE hotel_student LOGIN PASSWORD %L', :'student_password') \gexec
GRANT CONNECT ON DATABASE hoteldb TO hotel_app, hotel_student;
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO hotel_app, hotel_student;
SQL
