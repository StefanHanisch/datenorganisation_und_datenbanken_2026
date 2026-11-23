#!/usr/bin/env python
"""Export the core HotelDB data to Parquet files for the pandas notebooks.

Run once by the teacher: python scripts/export_analytics.py [--out data/export]

Only reads from the database (read-only transaction, SEED_DATABASE_URL).
Rows are streamed in chunks through a server-side cursor, so memory use stays
small no matter how many reservations exist.
"""
import argparse
import os
from dataclasses import dataclass
from pathlib import Path

import psycopg
import pyarrow as pa
import pyarrow.parquet as pq
from dotenv import load_dotenv

CHUNK_ROWS = 50_000

# PostgreSQL TIMESTAMPTZ values are stored as UTC instants in the Parquet files.
TIMESTAMP = pa.timestamp("us", tz="UTC")


@dataclass(frozen=True)
class ExportTable:
    """One Parquet file: the query that fills it and its column types."""

    name: str
    sql: str
    schema: pa.Schema


# NUMERIC columns are cast to double precision so that Parquet stores floats.
EXPORT_TABLES = [
    ExportTable(
        name="cities",
        sql="""
            SELECT id, name, country
            FROM cities
            ORDER BY id
        """,
        schema=pa.schema([
            ("id", pa.int64()),
            ("name", pa.string()),
            ("country", pa.string()),
        ]),
    ),
    ExportTable(
        name="hotels",
        sql="""
            SELECT id, city_id, name, address, stars, created_at, city_type, bundesland
            FROM hotels
            WHERE city_type IS NOT NULL
            ORDER BY id
        """,
        schema=pa.schema([
            ("id", pa.int64()),
            ("city_id", pa.int64()),
            ("name", pa.string()),
            ("address", pa.string()),
            ("stars", pa.int16()),
            ("created_at", TIMESTAMP),
            ("city_type", pa.string()),
            ("bundesland", pa.string()),
        ]),
    ),
    ExportTable(
        name="room_categories",
        sql="""
            SELECT c.id, c.hotel_id, c.name,
                   c.base_price::double precision AS base_price,
                   c.max_guests
            FROM room_categories c
            JOIN hotels h ON h.id = c.hotel_id
            WHERE h.city_type IS NOT NULL
            ORDER BY c.id
        """,
        schema=pa.schema([
            ("id", pa.int64()),
            ("hotel_id", pa.int64()),
            ("name", pa.string()),
            ("base_price", pa.float64()),
            ("max_guests", pa.int16()),
        ]),
    ),
    # Guests with at least one core reservation. The email column is left out on purpose.
    ExportTable(
        name="guests",
        sql="""
            SELECT g.id, g.first_name, g.last_name, g.created_at, g.home_state, g.company
            FROM guests g
            WHERE g.id IN (
                SELECT r.guest_id
                FROM reservations r
                JOIN room_categories c ON c.id = r.category_id
                JOIN hotels h ON h.id = c.hotel_id
                WHERE h.city_type IS NOT NULL
            )
            ORDER BY g.id
        """,
        schema=pa.schema([
            ("id", pa.int64()),
            ("first_name", pa.string()),
            ("last_name", pa.string()),
            ("created_at", TIMESTAMP),
            ("home_state", pa.string()),
            ("company", pa.string()),
        ]),
    ),
    ExportTable(
        name="reservations",
        sql="""
            SELECT r.id, r.guest_id, r.category_id, r.checkin, r.checkout, r.status,
                   r.created_at,
                   r.rate_per_night::double precision AS rate_per_night,
                   r.adults, r.children, r.channel,
                   r.commission_pct::double precision AS commission_pct,
                   r.cancelled_at, r.card_token
            FROM reservations r
            JOIN room_categories c ON c.id = r.category_id
            JOIN hotels h ON h.id = c.hotel_id
            WHERE h.city_type IS NOT NULL
            ORDER BY r.id
        """,
        schema=pa.schema([
            ("id", pa.int64()),
            ("guest_id", pa.int64()),
            ("category_id", pa.int64()),
            ("checkin", pa.date32()),
            ("checkout", pa.date32()),
            ("status", pa.string()),
            ("created_at", TIMESTAMP),
            ("rate_per_night", pa.float64()),
            ("adults", pa.int16()),
            ("children", pa.int16()),
            ("channel", pa.string()),
            ("commission_pct", pa.float64()),
            ("cancelled_at", TIMESTAMP),
            ("card_token", pa.string()),
        ]),
    ),
    ExportTable(
        name="daily_rates",
        sql="""
            SELECT d.category_id, d.arrival_date,
                   d.offered_rate::double precision AS offered_rate,
                   d.price_source, d.closed_to_arrival
            FROM daily_rates d
            JOIN room_categories c ON c.id = d.category_id
            JOIN hotels h ON h.id = c.hotel_id
            WHERE h.city_type IS NOT NULL
            ORDER BY d.category_id, d.arrival_date
        """,
        schema=pa.schema([
            ("category_id", pa.int64()),
            ("arrival_date", pa.date32()),
            ("offered_rate", pa.float64()),
            ("price_source", pa.string()),
            ("closed_to_arrival", pa.bool_()),
        ]),
    ),
    ExportTable(
        name="calendar_events",
        sql="""
            SELECT event_date, city_id, event_type, name
            FROM calendar_events
            ORDER BY event_date, city_id, name
        """,
        schema=pa.schema([
            ("event_date", pa.date32()),
            ("city_id", pa.int64()),
            ("event_type", pa.string()),
            ("name", pa.string()),
        ]),
    ),
]


def rows_to_batch(rows, schema):
    """Turn a list of database rows into one Arrow batch with fixed column types."""
    columns = list(zip(*rows))
    arrays = [
        pa.array(column, type=field.type)
        for column, field in zip(columns, schema)
    ]
    return pa.RecordBatch.from_arrays(arrays, schema=schema)


def export_table(conn, table, out_dir):
    """Stream one query into one Parquet file and return its row count and path."""
    target = out_dir / f"{table.name}.parquet"
    # Write to a temporary name first, so a failed run leaves no half-written file.
    temporary = out_dir / f"{table.name}.parquet.tmp"
    row_count = 0
    try:
        with conn.cursor(name=f"export_{table.name}") as cursor:
            cursor.execute(table.sql)
            column_names = [column.name for column in cursor.description]
            if column_names != table.schema.names:
                raise RuntimeError(
                    f"{table.name}: Spalten {column_names} passen nicht "
                    f"zum Schema {table.schema.names}"
                )
            with pq.ParquetWriter(temporary, table.schema) as writer:
                while True:
                    rows = cursor.fetchmany(CHUNK_ROWS)
                    if not rows:
                        break
                    writer.write_batch(rows_to_batch(rows, table.schema))
                    row_count += len(rows)
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)
    return row_count, target


def main():
    load_dotenv()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default="data/export", help="Zielordner der Parquet-Dateien")
    args = parser.parse_args()

    url = os.getenv("SEED_DATABASE_URL")
    if not url:
        parser.error("SEED_DATABASE_URL fehlt (aus .env setzen)")

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    total_bytes = 0
    with psycopg.connect(url, connect_timeout=10) as conn:
        # One read-only snapshot: all files show the same state of the database.
        conn.read_only = True
        conn.isolation_level = psycopg.IsolationLevel.REPEATABLE_READ
        # Timestamps arrive in UTC, independent of the server's default time zone.
        conn.execute("SET LOCAL TIME ZONE 'UTC'")
        for table in EXPORT_TABLES:
            row_count, path = export_table(conn, table, out_dir)
            size = path.stat().st_size
            total_bytes += size
            size_mb = size / 1_000_000
            print(f"{table.name:<16} {row_count:>12,} Zeilen {size_mb:>10.1f} MB", flush=True)
    print(f"Export fertig: {out_dir} ({total_bytes / 1_000_000:.1f} MB)")


if __name__ == "__main__":
    main()
