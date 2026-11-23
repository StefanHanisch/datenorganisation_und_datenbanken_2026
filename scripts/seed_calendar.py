"""Real German events and public holidays for the pattern seed.

Fair and festival dates are the real dates published by the organizers.
Easter, carnival and the movable public holidays are computed.
"""
from dataclasses import dataclass
from datetime import date, timedelta

from seed_model import END_DAY, START_DAY

YEARS = [2023, 2024, 2025, 2026]
EURO_2024_HOST_CITIES = ['Berlin', 'Hamburg', 'München', 'Köln', 'Frankfurt am Main', 'Leipzig']
DECOY_FAIRS = ['Hannover Messe', 'Frankfurter Buchmesse', 'gamescom', 'ITB Berlin', 'Leipziger Buchmesse']


@dataclass(frozen=True)
class Event:
    name: str
    event_type: str  # 'trade_fair', 'festival', 'carnival', 'tournament' or 'holiday'
    city: str
    start: date
    end: date  # inclusive


def easter_sunday(year: int) -> date:
    """Easter Sunday in the Gregorian calendar (Meeus/Jones/Butcher algorithm)."""
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = (h + l - 7 * m + 114) % 31 + 1
    return date(year, month, day)


def national_holidays(year: int) -> list[tuple[date, str]]:
    """The nine public holidays that apply in every German state."""
    easter = easter_sunday(year)
    return [
        (date(year, 1, 1), 'Neujahr'),
        (easter - timedelta(days=2), 'Karfreitag'),
        (easter + timedelta(days=1), 'Ostermontag'),
        (date(year, 5, 1), 'Tag der Arbeit'),
        (easter + timedelta(days=39), 'Christi Himmelfahrt'),
        (easter + timedelta(days=50), 'Pfingstmontag'),
        (date(year, 10, 3), 'Tag der Deutschen Einheit'),
        (date(year, 12, 25), '1. Weihnachtstag'),
        (date(year, 12, 26), '2. Weihnachtstag'),
    ]


def _carnival(year: int) -> Event:
    """Cologne carnival: Weiberfastnacht (Thursday) to Rosenmontag."""
    easter = easter_sunday(year)
    return Event('Karneval', 'carnival', 'Köln',
                 easter - timedelta(days=52), easter - timedelta(days=48))


EVENTS: list[Event] = [
    Event('Oktoberfest', 'festival', 'München', date(2023, 9, 16), date(2023, 10, 3)),
    Event('Oktoberfest', 'festival', 'München', date(2024, 9, 21), date(2024, 10, 6)),
    Event('Oktoberfest', 'festival', 'München', date(2025, 9, 20), date(2025, 10, 5)),
    Event('Oktoberfest', 'festival', 'München', date(2026, 9, 19), date(2026, 10, 4)),

    Event('Hannover Messe', 'trade_fair', 'Hannover', date(2023, 4, 17), date(2023, 4, 21)),
    Event('Hannover Messe', 'trade_fair', 'Hannover', date(2024, 4, 22), date(2024, 4, 26)),
    Event('Hannover Messe', 'trade_fair', 'Hannover', date(2025, 3, 31), date(2025, 4, 4)),
    Event('Hannover Messe', 'trade_fair', 'Hannover', date(2026, 4, 20), date(2026, 4, 24)),

    Event('Frankfurter Buchmesse', 'trade_fair', 'Frankfurt am Main', date(2023, 10, 18), date(2023, 10, 22)),
    Event('Frankfurter Buchmesse', 'trade_fair', 'Frankfurt am Main', date(2024, 10, 16), date(2024, 10, 20)),
    Event('Frankfurter Buchmesse', 'trade_fair', 'Frankfurt am Main', date(2025, 10, 15), date(2025, 10, 19)),
    Event('Frankfurter Buchmesse', 'trade_fair', 'Frankfurt am Main', date(2026, 10, 7), date(2026, 10, 11)),

    Event('gamescom', 'trade_fair', 'Köln', date(2023, 8, 23), date(2023, 8, 27)),
    Event('gamescom', 'trade_fair', 'Köln', date(2024, 8, 21), date(2024, 8, 25)),
    Event('gamescom', 'trade_fair', 'Köln', date(2025, 8, 20), date(2025, 8, 24)),
    Event('gamescom', 'trade_fair', 'Köln', date(2026, 8, 26), date(2026, 8, 30)),

    Event('ITB Berlin', 'trade_fair', 'Berlin', date(2023, 3, 7), date(2023, 3, 9)),
    Event('ITB Berlin', 'trade_fair', 'Berlin', date(2024, 3, 5), date(2024, 3, 7)),
    Event('ITB Berlin', 'trade_fair', 'Berlin', date(2025, 3, 4), date(2025, 3, 6)),
    Event('ITB Berlin', 'trade_fair', 'Berlin', date(2026, 3, 3), date(2026, 3, 5)),

    Event('Leipziger Buchmesse', 'trade_fair', 'Leipzig', date(2023, 4, 27), date(2023, 4, 30)),
    Event('Leipziger Buchmesse', 'trade_fair', 'Leipzig', date(2024, 3, 21), date(2024, 3, 24)),
    Event('Leipziger Buchmesse', 'trade_fair', 'Leipzig', date(2025, 3, 27), date(2025, 3, 30)),
    Event('Leipziger Buchmesse', 'trade_fair', 'Leipzig', date(2026, 3, 19), date(2026, 3, 22)),
]
EVENTS += [_carnival(year) for year in YEARS]
EVENTS += [
    Event('Euro 2024', 'tournament', city, date(2024, 6, 14), date(2024, 7, 14))
    for city in EURO_2024_HOST_CITIES
]


def _days_of(event: Event) -> list[date]:
    """All days of an event that lie inside the seed period."""
    first = max(event.start, START_DAY)
    last = min(event.end, END_DAY)
    return [first + timedelta(days=n) for n in range((last - first).days + 1)]


# Lookup table (city, day) -> events, built once so events_on is fast.
_EVENTS_BY_CITY_AND_DAY: dict[tuple[str, date], list[Event]] = {}
for _event in EVENTS:
    for _day in _days_of(_event):
        _EVENTS_BY_CITY_AND_DAY.setdefault((_event.city, _day), []).append(_event)


def events_on(city: str, day: date) -> list[Event]:
    """Events in this city on this day. Public holidays are not included."""
    return _EVENTS_BY_CITY_AND_DAY.get((city, day), [])


def calendar_rows(city_ids: dict[str, int]) -> list[tuple[date, int | None, str, str]]:
    """Rows (event_date, city_id, event_type, name) for calendar_events.

    One row per event day. Public holidays have city_id None (nationwide).
    """
    rows: list[tuple[date, int | None, str, str]] = []
    for event in EVENTS:
        for day in _days_of(event):
            rows.append((day, city_ids[event.city], event.event_type, event.name))
    for year in YEARS:
        for day, name in national_holidays(year):
            if START_DAY <= day <= END_DAY:
                rows.append((day, None, 'holiday', name))
    rows.sort(key=lambda row: (row[0], row[1] is None, row[1] or 0, row[3]))
    return rows
