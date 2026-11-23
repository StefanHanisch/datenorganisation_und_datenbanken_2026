"""Shared constants and record types for the pattern seed."""
from dataclasses import dataclass
from datetime import date, datetime

START_DAY = date(2023, 1, 1)
END_DAY = date(2026, 10, 31)
BUSINESS = 'business'
LEISURE = 'leisure'
CORE_CAPACITY = {'Standard': 30, 'Deluxe': 16, 'Suite': 8}
COMMISSION_PCT = {'direct': 0.0, 'corporate': 5.0, 'ota': 18.0}


@dataclass(frozen=True)
class CoreCity:
    name: str
    country: str
    bundesland: str
    city_type: str  # 'city' or 'resort'


CORE_CITIES = [
    CoreCity('Berlin', 'Deutschland', 'Berlin', 'city'),
    CoreCity('Hamburg', 'Deutschland', 'Hamburg', 'city'),
    CoreCity('München', 'Deutschland', 'Bayern', 'city'),
    CoreCity('Köln', 'Deutschland', 'Nordrhein-Westfalen', 'city'),
    CoreCity('Frankfurt am Main', 'Deutschland', 'Hessen', 'city'),
    CoreCity('Leipzig', 'Deutschland', 'Sachsen', 'city'),
    CoreCity('Hannover', 'Deutschland', 'Niedersachsen', 'city'),
    CoreCity('Sylt', 'Deutschland', 'Schleswig-Holstein', 'resort'),
    CoreCity('Garmisch-Partenkirchen', 'Deutschland', 'Bayern', 'resort'),
    CoreCity('Rügen', 'Deutschland', 'Mecklenburg-Vorpommern', 'resort'),
]


@dataclass(frozen=True)
class CoreCategory:
    category_id: int
    hotel_id: int
    city: str
    city_type: str
    name: str  # 'Standard', 'Deluxe' or 'Suite'
    base_price: float
    capacity: int


@dataclass(frozen=True)
class DailyRate:
    category_id: int
    arrival_date: date
    offered_rate: float
    r: float  # offered_rate / base_price
    price_source: str  # 'dynamic' or 'test'
    mu_business: float
    mu_leisure: float


@dataclass(slots=True)
class Request:
    category_id: int
    arrival: date
    segment: str
    nights: int
    created_at: datetime


@dataclass(slots=True)
class Booking:
    reservation_id: int
    guest_id: int
    category_id: int
    checkin: date
    checkout: date
    status: str  # 'confirmed' or 'cancelled'
    created_at: datetime
    cancelled_at: datetime | None
    rate_per_night: float
    adults: int
    children: int
    channel: str
    commission_pct: float
    card_token: str | None
    segment: str  # ground truth only, never written to the database


@dataclass(frozen=True)
class StoryGuest:
    guest_id: int
    first_name: str
    last_name: str
    email: str
    home_state: str
    company: str | None


def is_business_guest(guest_id: int) -> bool:
    """Same rule as the SQL guest insert in seed.py."""
    return (guest_id * 2654435761) % 100 < 35
