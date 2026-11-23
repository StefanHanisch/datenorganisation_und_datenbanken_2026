"""Home states of guests and their official summer holidays.

Source of all dates: KMK "Ferien im Schuljahr" lists for 2022/23, 2023/24,
2024/25 and 2025/26 (https://www.kmk.org/service/ferien.html).
Each tuple holds the first and the last holiday day, both inclusive.
"""
from datetime import date

HOME_STATES = [
    'Nordrhein-Westfalen',
    'Bayern',
    'Baden-Württemberg',
    'Niedersachsen',
    'Berlin',
    'Hamburg',
]

# 20 slots, shared out roughly by population.
STATE_SLOTS = (
    ['Nordrhein-Westfalen'] * 6
    + ['Bayern'] * 5
    + ['Baden-Württemberg'] * 4
    + ['Niedersachsen'] * 3
    + ['Berlin'] * 1
    + ['Hamburg'] * 1
)

SUMMER_HOLIDAYS = {
    'Nordrhein-Westfalen': {
        2023: (date(2023, 6, 22), date(2023, 8, 4)),
        2024: (date(2024, 7, 8), date(2024, 8, 20)),
        2025: (date(2025, 7, 14), date(2025, 8, 26)),
        2026: (date(2026, 7, 20), date(2026, 9, 1)),
    },
    'Bayern': {
        2023: (date(2023, 7, 31), date(2023, 9, 11)),
        2024: (date(2024, 7, 29), date(2024, 9, 9)),
        # The KMK list shows "01.08. 04.08. - 15.09."; the Bavarian ministry
        # names 1 August as the first holiday day.
        2025: (date(2025, 8, 1), date(2025, 9, 15)),
        2026: (date(2026, 8, 3), date(2026, 9, 14)),
    },
    'Baden-Württemberg': {
        2023: (date(2023, 7, 27), date(2023, 9, 9)),
        2024: (date(2024, 7, 25), date(2024, 9, 7)),
        2025: (date(2025, 7, 31), date(2025, 9, 13)),
        2026: (date(2026, 7, 30), date(2026, 9, 12)),
    },
    'Niedersachsen': {
        2023: (date(2023, 7, 6), date(2023, 8, 16)),
        2024: (date(2024, 6, 24), date(2024, 8, 2)),
        2025: (date(2025, 7, 3), date(2025, 8, 13)),
        2026: (date(2026, 7, 2), date(2026, 8, 12)),
    },
    'Berlin': {
        2023: (date(2023, 7, 13), date(2023, 8, 25)),
        2024: (date(2024, 7, 18), date(2024, 8, 30)),
        2025: (date(2025, 7, 24), date(2025, 9, 6)),
        2026: (date(2026, 7, 9), date(2026, 8, 22)),
    },
    'Hamburg': {
        2023: (date(2023, 7, 13), date(2023, 8, 23)),
        2024: (date(2024, 7, 18), date(2024, 8, 28)),
        2025: (date(2025, 7, 24), date(2025, 9, 3)),
        2026: (date(2026, 7, 9), date(2026, 8, 19)),
    },
}


def home_state_for_guest(guest_id):
    """Return the home state of a guest; same rule as the guests SQL in seed.py."""
    return STATE_SLOTS[(guest_id * 31) % 20]


def in_summer_holidays(state, day):
    """Return True if the day lies in the summer holidays of the state."""
    period = SUMMER_HOLIDAYS[state].get(day.year)
    if period is None:
        return False
    first_day, last_day = period
    return first_day <= day <= last_day


def in_summer_season(day):
    """Return True from 15 June to 15 September (both inclusive)."""
    return date(day.year, 6, 15) <= day <= date(day.year, 9, 15)
