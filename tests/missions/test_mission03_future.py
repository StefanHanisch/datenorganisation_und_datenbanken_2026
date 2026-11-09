"""Explicitly run ONLY after teacher says ACTIVATE MISSION-03.

Requires an ISOLATED empty test database with schema and app CRUD permissions,
not the lecture database. Set RUN_MISSION_03=1 and TEST_DATABASE_URL.
"""
import os
from datetime import date
import pytest

pytestmark = pytest.mark.skipif(
    os.getenv('RUN_MISSION_03') != '1' or not os.getenv('TEST_DATABASE_URL'),
    reason='Mission 03 locked or TEST_DATABASE_URL absent',
)


def test_extend_reservation_updates_dates_without_changing_category():
    import psycopg
    from psycopg.rows import dict_row
    from app.mission03_change import change_reservation

    with psycopg.connect(os.environ['TEST_DATABASE_URL'], row_factory=dict_row) as conn:
        # Transaction rollback: no fixture persists. Never run against the lecture DB.
        city = conn.execute("INSERT INTO cities(name,country) VALUES ('Testville','Testland') RETURNING id").fetchone()['id']
        hotel = conn.execute("INSERT INTO hotels(city_id,name,address) VALUES (%s,'Testhotel','Testweg') RETURNING id", (city,)).fetchone()['id']
        cat = conn.execute("INSERT INTO room_categories(hotel_id,name,base_price) VALUES (%s,'Test',100) RETURNING id", (hotel,)).fetchone()['id']
        conn.execute("INSERT INTO rooms(category_id,room_number) VALUES (%s,'T-01')", (cat,))
        guest = conn.execute("INSERT INTO guests(first_name,last_name,email) VALUES ('Test','Person','test@example.test') RETURNING id").fetchone()['id']
        reservation = conn.execute("INSERT INTO reservations(guest_id,category_id,checkin,checkout) VALUES (%s,%s,'2027-01-01','2027-01-03') RETURNING id", (guest,cat)).fetchone()['id']
        result = change_reservation(conn, reservation, date(2027, 1, 1), date(2027, 1, 5))
        actual = conn.execute('SELECT checkout,category_id FROM reservations WHERE id=%s', (reservation,)).fetchone()
        assert result['success'] is True
        assert actual['checkout'] == date(2027, 1, 5)
        assert actual['category_id'] == cat
        conn.rollback()
