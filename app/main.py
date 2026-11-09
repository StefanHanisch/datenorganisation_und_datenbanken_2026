"""GlobalStay: small operational booking portal + restricted teaching control center."""
from datetime import date, timedelta
from pathlib import Path
import secrets

from fastapi import FastAPI, HTTPException, Request, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from starlette.middleware.sessions import SessionMiddleware
from psycopg.errors import UniqueViolation, ForeignKeyViolation

from app.config import get_settings
from app.db import db_connection
from app.services import category_has_capacity, create_reservation, valid_stay
from app.mission02_autocomplete import suggest_cities
from app.mission03_change import change_reservation
from app.sql_lab import SqlRejected, run_student_query

BASE = Path(__file__).resolve().parent
settings = get_settings()
app = FastAPI(title='GlobalStay / HotelDB', docs_url=None, redoc_url=None)
app.add_middleware(SessionMiddleware, secret_key=settings.session_secret or 'LOCAL-UNCONFIGURED-DO-NOT-PUBLISH',
                   same_site='lax', https_only=settings.cookie_secure, max_age=60 * 60 * 4)
app.mount('/static', StaticFiles(directory=BASE / 'static'), name='static')
templates = Jinja2Templates(directory=BASE / 'templates')


@app.on_event('startup')
def verify_config():
    settings.check_runtime()


def role_of(request: Request) -> str | None:
    role = request.session.get('role')
    return role if role in ('student', 'teacher') else None


def require_access(request: Request, teacher: bool = False) -> str:
    role = role_of(request)
    if role is None:
        raise HTTPException(status_code=401, detail='Bitte zuerst anmelden.')
    if teacher and role != 'teacher':
        raise HTTPException(status_code=403, detail='Nur für die Lehrperson freigegeben.')
    return role


def page_context(request: Request, **kwargs):
    return {'request': request, 'role': role_of(request), 'is_teacher': role_of(request) == 'teacher', **kwargs}


def page_or_login(request: Request):
    if role_of(request) is None:
        return RedirectResponse('/login', status_code=303)
    return None


@app.get('/health')
def health():
    return {'status': 'ok'}


@app.get('/login', response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse(request=request, name='login.html',
                                      context=page_context(request, error=None))


@app.post('/login')
def login(request: Request, code: str = Form(...)):
    code = code.strip()
    if secrets.compare_digest(code, settings.teacher_access_code):
        request.session['role'] = 'teacher'
    elif secrets.compare_digest(code, settings.student_access_code):
        request.session['role'] = 'student'
    else:
        return templates.TemplateResponse(request=request, name='login.html',
            context=page_context(request, error='Zugangscode unbekannt.'), status_code=401)
    return RedirectResponse('/', status_code=303)


@app.post('/logout')
def logout(request: Request):
    request.session.clear()
    return RedirectResponse('/login', status_code=303)


@app.get('/', response_class=HTMLResponse)
def home(request: Request):
    if redirect := page_or_login(request):
        return redirect
    today = date.today() + timedelta(days=14)
    return templates.TemplateResponse(request=request, name='home.html', context=page_context(request,
        today=today.isoformat(), later=(today + timedelta(days=2)).isoformat()))


@app.get('/search', response_class=HTMLResponse)
def search(request: Request, city: str = '', checkin: date | None = None,
           checkout: date | None = None):
    if redirect := page_or_login(request):
        return redirect
    checkin = checkin or date.today() + timedelta(days=14)
    checkout = checkout or checkin + timedelta(days=2)
    try:
        valid_stay(checkin, checkout)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    with db_connection('student') as conn:
        results = conn.execute('''
            SELECT h.id, h.name, h.stars, h.address, c.name AS city, c.country,
                   MIN(rc.base_price) AS from_price
            FROM hotels h JOIN cities c ON c.id=h.city_id
            JOIN room_categories rc ON rc.hotel_id=h.id
            WHERE c.name ILIKE %s
            GROUP BY h.id, h.name, h.stars, h.address, c.name, c.country
            ORDER BY h.id LIMIT 24
        ''', (f'{city.strip()}%',)).fetchall()
    return templates.TemplateResponse(request=request, name='results.html', context=page_context(request,
        results=results, city=city, checkin=checkin.isoformat(), checkout=checkout.isoformat()))


@app.get('/hotels/{hotel_id}', response_class=HTMLResponse)
def hotel_detail(request: Request, hotel_id: int, checkin: date, checkout: date):
    if redirect := page_or_login(request):
        return redirect
    try:
        valid_stay(checkin, checkout)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    with db_connection('student') as conn:
        hotel = conn.execute('''
            SELECT h.*, c.name AS city, c.country FROM hotels h
            JOIN cities c ON c.id=h.city_id WHERE h.id=%s
        ''', (hotel_id,)).fetchone()
        if hotel is None:
            raise HTTPException(404, 'Hotel nicht gefunden.')
        categories = conn.execute('''
            SELECT rc.id, rc.name, rc.base_price, rc.max_guests,
                   COUNT(r.id) FILTER (WHERE r.is_active) AS capacity
            FROM room_categories rc LEFT JOIN rooms r ON r.category_id=rc.id
            WHERE rc.hotel_id=%s GROUP BY rc.id ORDER BY rc.base_price
        ''', (hotel_id,)).fetchall()
        for category in categories:
            category['available'] = category_has_capacity(conn, category['id'], checkin, checkout)
    return templates.TemplateResponse(request=request, name='hotel.html', context=page_context(request,
        hotel=hotel, categories=categories, checkin=checkin.isoformat(), checkout=checkout.isoformat()))


@app.post('/book', response_class=HTMLResponse)
def book(request: Request, category_id: int = Form(...), checkin: date = Form(...),
         checkout: date = Form(...), first_name: str = Form(...),
         last_name: str = Form(...), email: str = Form(...)):
    require_access(request)
    if not email or '@' not in email or not first_name.strip() or not last_name.strip():
        raise HTTPException(400, 'Bitte Name und gültige E-Mail-Adresse angeben.')
    if len(email) > 200 or len(first_name) > 100 or len(last_name) > 100:
        raise HTTPException(400, 'Eingaben zu lang.')
    try:
        with db_connection('app') as conn:
            number = create_reservation(conn, category_id=category_id, checkin=checkin,
                checkout=checkout, email=email, first_name=first_name, last_name=last_name)
        return templates.TemplateResponse(request=request, name='booked.html', context=page_context(request,
            number=number, email=email.strip().lower()))
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@app.get('/bookings', response_class=HTMLResponse)
def bookings(request: Request, email: str = ''):
    if redirect := page_or_login(request):
        return redirect
    bookings_result = []
    if email.strip():
        # MISSION-01: intentionally unindexed equality lookup on guests.email.
        # TODO(MISSION-01): Analyze with EXPLAIN ANALYZE, choose an index, re-benchmark.
        # ACTIVATION: ONLY if teacher explicitly instructs to implement Mission 01.
        with db_connection('student') as conn:
            bookings_result = conn.execute('''
                SELECT res.id, res.checkin, res.checkout, res.status,
                       rc.name AS category, h.name AS hotel, c.name AS city
                FROM guests g JOIN reservations res ON res.guest_id=g.id
                JOIN room_categories rc ON rc.id=res.category_id
                JOIN hotels h ON h.id=rc.hotel_id
                JOIN cities c ON c.id=h.city_id
                WHERE g.email=%s ORDER BY res.checkin DESC LIMIT 25
            ''', (email.strip().lower(),)).fetchall()
    return templates.TemplateResponse(request=request, name='bookings.html', context=page_context(request,
        bookings=bookings_result, email=email))


@app.get('/api/cities/suggest')
def city_suggest(request: Request, q: str = Query('', max_length=80)):
    require_access(request)
    with db_connection('student') as conn:
        cities = [r['name'] for r in conn.execute('SELECT DISTINCT name FROM cities ORDER BY name').fetchall()]
    return {'suggestions': suggest_cities(q, cities)}


class ChangeDates(BaseModel):
    checkin: date
    checkout: date


@app.patch('/api/reservations/{reservation_id}')
def update_booking(request: Request, reservation_id: int, payload: ChangeDates):
    require_access(request)
    # MISSION-03: route is prepared, domain logic intentionally absent.
    with db_connection('app') as conn:
        result = change_reservation(conn, reservation_id, payload.checkin, payload.checkout)
    return result


TABLES = {'cities', 'hotels', 'room_categories', 'rooms', 'guests', 'reservations'}


@app.get('/admin', response_class=HTMLResponse)
def admin(request: Request):
    if redirect := page_or_login(request):
        return redirect
    return templates.TemplateResponse(request=request, name='admin.html',
                                      context=page_context(request))


@app.get('/api/admin/stats')
def admin_stats(request: Request):
    require_access(request)
    with db_connection('student') as conn:
        data = conn.execute('''
            SELECT relname, n_live_tup::bigint AS approx_rows
            FROM pg_stat_user_tables WHERE schemaname='public'
        ''').fetchall()
    counts = {row['relname']: row['approx_rows'] for row in data if row['relname'] in TABLES}
    return {'counts': counts, 'note': 'Schätzwerte aus PostgreSQL-Statistiken (ANALYZE empfohlen).'}


@app.get('/api/admin/tables/{table_name}')
def admin_table(request: Request, table_name: str):
    require_access(request)
    if table_name not in TABLES:
        raise HTTPException(404, 'Unbekannte Tabelle')
    with db_connection('student') as conn:
        # Identifier comes from a fixed allowlist, never from arbitrary SQL.
        rows = conn.execute(f'SELECT * FROM {table_name} ORDER BY id LIMIT 15').fetchall()
    return {'table': table_name, 'rows': rows}


class QueryRequest(BaseModel):
    sql: str = Field(max_length=8000)
    explain: bool = False


@app.post('/api/admin/sql')
def sql_workbench(request: Request, payload: QueryRequest):
    require_access(request)
    try:
        return run_student_query(payload.sql, explain=payload.explain)
    except SqlRejected as exc:
        raise HTTPException(400, str(exc)) from exc


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


def write_record(request: Request, statement: str, values: tuple):
    require_access(request, teacher=True)
    try:
        with db_connection('app') as conn:
            item = conn.execute(statement, values).fetchone()
        return {'created': True, 'id': item['id']}
    except (UniqueViolation, ForeignKeyViolation) as exc:
        raise HTTPException(409, 'Duplikat oder Fremdschlüssel nicht vorhanden.') from exc


@app.post('/api/admin/cities')
def create_city(request: Request, payload: CityCreate):
    return write_record(request,
        'INSERT INTO cities(name,country) VALUES(%s,%s) RETURNING id',
        (payload.name, payload.country))


@app.post('/api/admin/hotels')
def create_hotel(request: Request, payload: HotelCreate):
    return write_record(request,
        'INSERT INTO hotels(city_id,name,address,stars) VALUES(%s,%s,%s,%s) RETURNING id',
        (payload.city_id, payload.name, payload.address, payload.stars))


@app.post('/api/admin/room-categories')
def create_category(request: Request, payload: CategoryCreate):
    return write_record(request,
        'INSERT INTO room_categories(hotel_id,name,base_price,max_guests) VALUES(%s,%s,%s,%s) RETURNING id',
        (payload.hotel_id, payload.name, payload.base_price, payload.max_guests))


@app.post('/api/admin/rooms')
def create_room(request: Request, payload: RoomCreate):
    return write_record(request,
        'INSERT INTO rooms(category_id,room_number) VALUES(%s,%s) RETURNING id',
        (payload.category_id, payload.room_number))
