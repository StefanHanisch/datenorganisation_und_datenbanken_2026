"""Booking domain functions. No assignments of concrete rooms, only categories."""
from datetime import date
from psycopg import Connection


def nights_overlap(start_a: date, end_a: date, start_b: date, end_b: date) -> bool:
    """Checkout is exclusive (same-day checkout/checkin is NOT a conflict)."""
    return start_a < end_b and start_b < end_a


def valid_stay(checkin: date, checkout: date) -> bool:
    length = (checkout - checkin).days
    if not 1 <= length <= 30:
        raise ValueError('Aufenthalt muss 1 bis 30 Nächte umfassen.')
    return True


def category_has_capacity(
    conn: Connection, category_id: int, checkin: date, checkout: date,
    exclude_reservation_id: int | None = None,
) -> bool:
    """Check MAX occupancy PER NIGHT; not just COUNT of all overlapping reservations.

    Caller MUST acquire SELECT ... FOR UPDATE lock on room_categories row before
    calling this and committing a reservation. Exclusion is for a future edit.
    """
    valid_stay(checkin, checkout)
    capacity = conn.execute(
        'SELECT COUNT(*) AS n FROM rooms WHERE category_id = %s AND is_active',
        (category_id,),
    ).fetchone()['n']
    if capacity < 1:
        return False
    row = conn.execute('''
        WITH nights AS (
            SELECT day::date AS night
            FROM generate_series(%s::date, (%s::date - 1), interval '1 day') AS day
        ), occupancy AS (
            SELECT n.night, COUNT(r.id) AS occupied
            FROM nights n LEFT JOIN reservations r
              ON r.category_id = %s AND r.status = 'confirmed'
              AND r.checkin <= n.night AND r.checkout > n.night
              AND (%s::bigint IS NULL OR r.id <> %s::bigint)
            GROUP BY n.night
        )
        SELECT EXISTS(SELECT 1 FROM occupancy WHERE occupied >= %s) AS is_full
    ''', (checkin, checkout, category_id, exclude_reservation_id,
          exclude_reservation_id, capacity)).fetchone()
    return not row['is_full']


def create_reservation(conn: Connection, *, category_id: int, checkin: date,
                       checkout: date, email: str, first_name: str,
                       last_name: str) -> int:
    valid_stay(checkin, checkout)
    # Serialize ALL bookings for the same category to prevent two simultaneous guests
    # from occupying the final slot. Avoid silently removing this lock in refactors.
    locked = conn.execute('SELECT id FROM room_categories WHERE id=%s FOR UPDATE',
                          (category_id,)).fetchone()
    if locked is None:
        raise ValueError('Zimmerkategorie existiert nicht.')
    if not category_has_capacity(conn, category_id, checkin, checkout):
        raise ValueError('Zimmerkategorie ist in diesem Zeitraum ausgebucht.')
    guest = conn.execute('SELECT id FROM guests WHERE email=%s LIMIT 1',
                         (email.strip().lower(),)).fetchone()
    if guest:
        guest_id = guest['id']
    else:
        guest_id = conn.execute('''
            INSERT INTO guests (first_name, last_name, email)
            VALUES (%s,%s,%s) RETURNING id
        ''', (first_name.strip(), last_name.strip(), email.strip().lower())).fetchone()['id']
    result = conn.execute('''
        INSERT INTO reservations (guest_id, category_id, checkin, checkout)
        VALUES (%s,%s,%s,%s) RETURNING id
    ''', (guest_id, category_id, checkin, checkout)).fetchone()
    return result['id']
