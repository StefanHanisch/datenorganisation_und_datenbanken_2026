"""Resource API (CRUD) for the hotel inventory: cities, hotels, room categories, rooms.

- Read: every logged-in session, through the read-only student role (4 s statement timeout).
- Write: teacher session only, through hotel_app.
- Lists are ALWAYS limited and paged by id ("keyset pagination"):
      GET /api/v1/hotels?limit=50              -> first page
      GET /api/v1/hotels?limit=50&after_id=812 -> next page (812 = next_after_id of the previous page)
  Unlike OFFSET, `WHERE id > after_id ORDER BY id` stays fast on page 10 000 because the primary key
  index jumps straight to the start of the page.
- Guests and reservations are intentionally NOT part of this API (personal data, MISSION-01/03).
"""
from contextlib import contextmanager
from datetime import datetime
from typing import Generic, TypeVar

from fastapi import APIRouter, HTTPException, Query, Request, Response
from psycopg.errors import ForeignKeyViolation, UniqueViolation
from pydantic import BaseModel, Field

from app.access import require_access
from app.db import db_connection

DEFAULT_LIMIT = 50
MAX_LIMIT = 500

router = APIRouter(prefix='/api/v1')


# ---------- Input models (also used by the /api/admin/* forms) ----------

class CityCreate(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    country: str = Field(min_length=2, max_length=80)


class HotelCreate(BaseModel):
    city_id: int = Field(gt=0)
    name: str = Field(min_length=2, max_length=140)
    address: str = Field(min_length=2, max_length=200)
    stars: int = Field(default=3, ge=1, le=5)


class CategoryCreate(BaseModel):
    hotel_id: int = Field(gt=0)
    name: str = Field(min_length=2, max_length=60)
    base_price: float = Field(gt=0, le=10000)
    max_guests: int = Field(default=2, ge=1, le=8)


class RoomCreate(BaseModel):
    category_id: int = Field(gt=0)
    room_number: str = Field(min_length=1, max_length=40)


class RoomUpdate(RoomCreate):
    is_active: bool = True


# ---------- Output models (what the API returns) ----------

class City(BaseModel):
    id: int
    name: str
    country: str


class Hotel(BaseModel):
    id: int
    city_id: int
    name: str
    address: str
    stars: int
    created_at: datetime
    city_type: str | None
    bundesland: str | None


class RoomCategory(BaseModel):
    id: int
    hotel_id: int
    name: str
    base_price: float
    max_guests: int


class Room(BaseModel):
    id: int
    category_id: int
    room_number: str
    is_active: bool


Item = TypeVar('Item')


class Page(BaseModel, Generic[Item]):
    items: list[Item]
    limit: int
    next_after_id: int | None = Field(
        description='Als ?after_id= einsetzen, um die nächste Seite zu laden. null = letzte Seite.')


# ---------- Shared SQL helpers ----------
# Table and column names below only ever come from constants in this file or from the
# field names of the Pydantic models above, never from the request. Values are always %s parameters.

def limit_param():
    return Query(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT, description=f'Zeilen pro Seite (max. {MAX_LIMIT}).')


def after_id_param():
    return Query(0, ge=0, description='Nur Zeilen mit id > after_id (Wert next_after_id der Vorseite).')


def list_rows(table: str, limit: int, after_id: int, filter_column: str | None = None,
              filter_value: int | None = None) -> dict:
    conditions = ['id > %s']
    values: list = [after_id]
    if filter_value is not None:
        conditions.append(f'{filter_column} = %s')
        values.append(filter_value)
    sql = f'SELECT * FROM {table} WHERE {" AND ".join(conditions)} ORDER BY id LIMIT %s'
    with db_connection('student') as conn:
        # Ask for one extra row: if it exists, there is a next page.
        rows = conn.execute(sql, (*values, limit + 1)).fetchall()
    has_more = len(rows) > limit
    items = rows[:limit]
    return {'items': items, 'limit': limit, 'next_after_id': items[-1]['id'] if has_more else None}


def get_row(table: str, row_id: int) -> dict:
    with db_connection('student') as conn:
        row = conn.execute(f'SELECT * FROM {table} WHERE id = %s', (row_id,)).fetchone()
    if row is None:
        raise HTTPException(404, 'Nicht gefunden.')
    return row


@contextmanager
def write_transaction(request: Request):
    require_access(request, teacher=True)
    try:
        with db_connection('app') as conn:
            yield conn
    except UniqueViolation as exc:
        raise HTTPException(409, 'Ein Datensatz mit diesen Werten existiert bereits.') from exc
    except ForeignKeyViolation as exc:
        raise HTTPException(409, 'Verweis ungültig oder Datensatz wird noch verwendet.') from exc


def insert_row(request: Request, table: str, payload: BaseModel) -> dict:
    data = payload.model_dump()
    columns = ', '.join(data)
    placeholders = ', '.join(['%s'] * len(data))
    with write_transaction(request) as conn:
        return conn.execute(f'INSERT INTO {table} ({columns}) VALUES ({placeholders}) RETURNING *',
                            tuple(data.values())).fetchone()


def update_row(request: Request, table: str, row_id: int, payload: BaseModel) -> dict:
    data = payload.model_dump()
    assignments = ', '.join(f'{column} = %s' for column in data)
    with write_transaction(request) as conn:
        row = conn.execute(f'UPDATE {table} SET {assignments} WHERE id = %s RETURNING *',
                           (*data.values(), row_id)).fetchone()
    if row is None:
        raise HTTPException(404, 'Nicht gefunden.')
    return row


def delete_row(request: Request, table: str, row_id: int, children: list[tuple[str, str]]) -> Response:
    """Delete one row, but refuse while dependent rows exist (no silent ON DELETE CASCADE of seed data)."""
    with write_transaction(request) as conn:
        for child_table, child_column in children:
            in_use = conn.execute(f'SELECT EXISTS (SELECT 1 FROM {child_table} WHERE {child_column} = %s)',
                                  (row_id,)).fetchone()['exists']
            if in_use:
                raise HTTPException(409, f'Noch Einträge in {child_table} vorhanden. Erst diese löschen.')
        deleted = conn.execute(f'DELETE FROM {table} WHERE id = %s RETURNING id', (row_id,)).fetchone()
    if deleted is None:
        raise HTTPException(404, 'Nicht gefunden.')
    return Response(status_code=204)


# ---------- Cities ----------

@router.get('/cities', tags=['cities'], response_model=Page[City])
def list_cities(request: Request, limit: int = limit_param(), after_id: int = after_id_param()):
    require_access(request)
    return list_rows('cities', limit, after_id)


@router.get('/cities/{city_id}', tags=['cities'], response_model=City)
def read_city(request: Request, city_id: int):
    require_access(request)
    return get_row('cities', city_id)


@router.post('/cities', tags=['cities'], response_model=City, status_code=201)
def create_city(request: Request, payload: CityCreate):
    return insert_row(request, 'cities', payload)


@router.put('/cities/{city_id}', tags=['cities'], response_model=City)
def update_city(request: Request, city_id: int, payload: CityCreate):
    return update_row(request, 'cities', city_id, payload)


@router.delete('/cities/{city_id}', tags=['cities'], status_code=204)
def delete_city(request: Request, city_id: int):
    return delete_row(request, 'cities', city_id, [('hotels', 'city_id'), ('calendar_events', 'city_id')])


# ---------- Hotels ----------

@router.get('/hotels', tags=['hotels'], response_model=Page[Hotel])
def list_hotels(request: Request, limit: int = limit_param(), after_id: int = after_id_param(),
                city_id: int | None = Query(None, description='Nur Hotels dieser Stadt.')):
    require_access(request)
    return list_rows('hotels', limit, after_id, 'city_id', city_id)


@router.get('/hotels/{hotel_id}', tags=['hotels'], response_model=Hotel)
def read_hotel(request: Request, hotel_id: int):
    require_access(request)
    return get_row('hotels', hotel_id)


@router.post('/hotels', tags=['hotels'], response_model=Hotel, status_code=201)
def create_hotel(request: Request, payload: HotelCreate):
    return insert_row(request, 'hotels', payload)


@router.put('/hotels/{hotel_id}', tags=['hotels'], response_model=Hotel)
def update_hotel(request: Request, hotel_id: int, payload: HotelCreate):
    return update_row(request, 'hotels', hotel_id, payload)


@router.delete('/hotels/{hotel_id}', tags=['hotels'], status_code=204)
def delete_hotel(request: Request, hotel_id: int):
    return delete_row(request, 'hotels', hotel_id, [('room_categories', 'hotel_id')])


# ---------- Room categories ----------

@router.get('/room-categories', tags=['room-categories'], response_model=Page[RoomCategory])
def list_room_categories(request: Request, limit: int = limit_param(), after_id: int = after_id_param(),
                         hotel_id: int | None = Query(None, description='Nur Kategorien dieses Hotels.')):
    require_access(request)
    return list_rows('room_categories', limit, after_id, 'hotel_id', hotel_id)


@router.get('/room-categories/{category_id}', tags=['room-categories'], response_model=RoomCategory)
def read_room_category(request: Request, category_id: int):
    require_access(request)
    return get_row('room_categories', category_id)


@router.post('/room-categories', tags=['room-categories'], response_model=RoomCategory, status_code=201)
def create_room_category(request: Request, payload: CategoryCreate):
    return insert_row(request, 'room_categories', payload)


@router.put('/room-categories/{category_id}', tags=['room-categories'], response_model=RoomCategory)
def update_room_category(request: Request, category_id: int, payload: CategoryCreate):
    return update_row(request, 'room_categories', category_id, payload)


@router.delete('/room-categories/{category_id}', tags=['room-categories'], status_code=204)
def delete_room_category(request: Request, category_id: int):
    # Reservations are protected by their foreign key (-> 409), rooms and daily rates by this check.
    return delete_row(request, 'room_categories', category_id,
                      [('rooms', 'category_id'), ('daily_rates', 'category_id')])


# ---------- Rooms ----------

@router.get('/rooms', tags=['rooms'], response_model=Page[Room])
def list_rooms(request: Request, limit: int = limit_param(), after_id: int = after_id_param(),
               category_id: int | None = Query(None, description='Nur Zimmer dieser Kategorie.')):
    require_access(request)
    return list_rows('rooms', limit, after_id, 'category_id', category_id)


@router.get('/rooms/{room_id}', tags=['rooms'], response_model=Room)
def read_room(request: Request, room_id: int):
    require_access(request)
    return get_row('rooms', room_id)


@router.post('/rooms', tags=['rooms'], response_model=Room, status_code=201)
def create_room(request: Request, payload: RoomCreate):
    return insert_row(request, 'rooms', payload)


@router.put('/rooms/{room_id}', tags=['rooms'], response_model=Room)
def update_room(request: Request, room_id: int, payload: RoomUpdate):
    return update_row(request, 'rooms', room_id, payload)


@router.delete('/rooms/{room_id}', tags=['rooms'], status_code=204)
def delete_room(request: Request, room_id: int):
    return delete_row(request, 'rooms', room_id, [])
