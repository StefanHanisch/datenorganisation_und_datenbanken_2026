"""Hidden demand model of the pattern seed: daily prices and booking requests.

Students never see this file. They only see its effects in the exported data:
prices follow demand on most days, and on a few random 'test' days the price
is independent of demand.
"""
from datetime import date, timedelta
from operator import attrgetter

import numpy as np

from seed_calendar import easter_sunday, events_on, national_holidays
from seed_model import (
    BUSINESS,
    END_DAY,
    LEISURE,
    START_DAY,
    CoreCategory,
    DailyRate,
    Request,
)

REQUESTS_PER_ROOM = 0.48
BUSINESS_SHARE = {'city': 0.40, 'resort': 0.08}

# Monday first. Both lists have a mean of 1.
WEEKDAY_FACTOR = {
    BUSINESS: [1.6, 1.6, 1.5, 0.7, 0.2, 0.1, 1.3],
    LEISURE: [0.5, 0.5, 0.6, 1.2, 2.0, 1.5, 0.7],
}

# January first.
CITY_SEASON = [0.85, 0.85, 0.95, 1.05, 1.1, 1.1, 1.1, 1.1, 1.1, 1.05, 0.9, 0.9]
COAST_SEASON = [0.4, 0.4, 0.4, 0.8, 1.1, 1.6, 1.6, 1.6, 1.6, 0.8, 0.4, 0.4]
ALPINE_SEASON = [1.3, 1.3, 1.3, 0.7, 0.7, 1.2, 1.2, 1.2, 1.2, 0.8, 0.7, 1.3]
LEISURE_SEASON = {
    'Sylt': COAST_SEASON,
    'Rügen': COAST_SEASON,
    'Garmisch-Partenkirchen': ALPINE_SEASON,
}

# event_type -> (business factor, leisure factor)
EVENT_FACTOR = {
    'trade_fair': (2.5, 0.7),
    'festival': (1.0, 1.9),
    'carnival': (0.3, 2.0),
    'tournament': (0.8, 1.9),  # Euro 2024
}

TEST_PROBABILITY = 0.35
TEST_RATIOS = [0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.3, 1.4, 1.5]

# segment -> (price ratio with 50 % acceptance, steepness of the curve)
WILLINGNESS_TO_PAY = {BUSINESS: (1.50, 0.28), LEISURE: (1.05, 0.13)}

DEMAND_NOISE_SIGMA = 0.15
NIGHT_PROBABILITIES = {
    BUSINESS: [0.70, 0.20, 0.10],  # 1-3 nights, mean 1.4
    LEISURE: [0.38, 0.30, 0.16, 0.08, 0.04, 0.03, 0.01],  # 1-7 nights, mean 2.23
}
LEAD_DAYS = {BUSINESS: (3, 14), LEISURE: (30, 120)}
SECONDS_PER_DAY = 86_400

ALL_DAYS = [
    START_DAY + timedelta(days=offset)
    for offset in range((END_DAY - START_DAY).days + 1)
]
ALL_DAYS_NUMPY = np.array(ALL_DAYS, dtype='datetime64[D]')

YEARS = range(START_DAY.year, END_DAY.year + 1)
EASTER = {year: easter_sunday(year) for year in YEARS}
NATIONAL_HOLIDAY_DAYS = {
    holiday for year in YEARS for holiday, _name in national_holidays(year)
}


def accepted_probability(r, segment: str) -> float:
    """Share of guests who accept the price ratio r (also works on numpy arrays)."""
    midpoint, steepness = WILLINGNESS_TO_PAY[segment]
    return 1 / (1 + np.exp((r - midpoint) / steepness))


def business_season(day: date) -> float:
    if (day.month == 12 and day.day >= 20) or (day.month == 1 and day.day <= 6):
        return 0.3
    if day.month == 8:
        return 0.6
    return 1.0


def business_holiday(day: date) -> float:
    """Applied once, because Good Friday can also be a national holiday."""
    easter = EASTER[day.year]
    is_easter_core = easter - timedelta(days=2) <= day <= easter + timedelta(days=1)
    return 0.3 if is_easter_core or day in NATIONAL_HOLIDAY_DAYS else 1.0


def leisure_easter(day: date) -> float:
    easter = EASTER[day.year]
    if easter - timedelta(days=2) <= day <= easter + timedelta(days=1):
        return 2.4
    if easter - timedelta(days=14) <= day <= easter + timedelta(days=7):
        return 2.0
    return 1.0


def demand_per_request_unit(city: str, city_type: str, day: date) -> tuple[float, float]:
    """Return (business, leisure) demand of one day, before scaling by capacity."""
    business_share = BUSINESS_SHARE[city_type]
    weekday = day.weekday()
    business = business_share * WEEKDAY_FACTOR[BUSINESS][weekday]
    business *= business_season(day) * business_holiday(day)

    leisure = (1 - business_share) * WEEKDAY_FACTOR[LEISURE][weekday]
    leisure *= LEISURE_SEASON.get(city, CITY_SEASON)[day.month - 1]
    leisure *= leisure_easter(day)

    for event in events_on(city, day):
        business_factor, leisure_factor = EVENT_FACTOR.get(event.event_type, (1.0, 1.0))
        business *= business_factor
        leisure *= leisure_factor
    return business, leisure


def city_demand(city: str, city_type: str) -> tuple[np.ndarray, np.ndarray]:
    """Return business and leisure demand arrays with one entry per day."""
    pairs = [demand_per_request_unit(city, city_type, day) for day in ALL_DAYS]
    demand = np.array(pairs)
    return demand[:, 0], demand[:, 1]


def build_daily_rates(
    categories: list[CoreCategory], rng: np.random.Generator
) -> dict[tuple[int, date], DailyRate]:
    """Set one price per category and arrival day."""
    demand_by_city = {}
    rates = {}
    for category in categories:
        city_key = (category.city, category.city_type)
        if city_key not in demand_by_city:
            demand_by_city[city_key] = city_demand(*city_key)
        business, leisure = demand_by_city[city_key]

        # D is 1 on an average day and independent of the room count.
        pressure = business + leisure
        is_test = (pressure <= 1.0) & (rng.random(len(ALL_DAYS)) < TEST_PROBABILITY)
        test_ratio = rng.choice(TEST_RATIOS, size=len(ALL_DAYS))
        dynamic_ratio = np.round(np.clip(1 + 0.1 * (pressure - 1), 0.90, 1.15), 2)
        ratios = np.where(is_test, test_ratio, dynamic_ratio)

        scale = REQUESTS_PER_ROOM * category.capacity
        for day, ratio, test, mu_business, mu_leisure in zip(
            ALL_DAYS,
            ratios.tolist(),
            is_test.tolist(),
            (business * scale).tolist(),
            (leisure * scale).tolist(),
        ):
            rates[(category.category_id, day)] = DailyRate(
                category_id=category.category_id,
                arrival_date=day,
                offered_rate=round(category.base_price * ratio, 2),
                r=ratio,
                price_source='test' if test else 'dynamic',
                mu_business=mu_business,
                mu_leisure=mu_leisure,
            )
    return rates


def draw_segment_requests(
    category: CoreCategory,
    segment: str,
    mu: np.ndarray,
    ratios: np.ndarray,
    rng: np.random.Generator,
) -> list[Request]:
    """Draw all accepted requests of one segment for one category."""
    # The mean of this log-normal noise is 1, so it does not change total demand.
    noise = rng.lognormal(
        mean=-DEMAND_NOISE_SIGMA**2 / 2, sigma=DEMAND_NOISE_SIGMA, size=len(mu)
    )
    asked = rng.poisson(mu * noise)
    accepted = rng.binomial(asked, accepted_probability(ratios, segment))

    # One array entry per accepted request.
    day_index = np.repeat(np.arange(len(mu)), accepted)
    count = len(day_index)
    night_probabilities = NIGHT_PROBABILITIES[segment]
    nights = rng.choice(
        np.arange(1, len(night_probabilities) + 1), size=count, p=night_probabilities
    )
    shortest_lead, longest_lead = LEAD_DAYS[segment]
    lead_days = rng.integers(shortest_lead, longest_lead + 1, size=count)
    second_of_day = rng.integers(0, SECONDS_PER_DAY, size=count)
    created_at = (
        ALL_DAYS_NUMPY[day_index]
        - lead_days.astype('timedelta64[D]')
        + second_of_day.astype('timedelta64[s]')
    )

    return [
        Request(category.category_id, ALL_DAYS[index], segment, night_count, created)
        for index, night_count, created in zip(
            day_index.tolist(), nights.tolist(), created_at.tolist()
        )
    ]


def draw_requests(
    categories: list[CoreCategory],
    rates: dict[tuple[int, date], DailyRate],
    rng: np.random.Generator,
) -> list[Request]:
    """Return every request that accepts its price, oldest first."""
    requests = []
    for category in categories:
        day_rates = [rates[(category.category_id, day)] for day in ALL_DAYS]
        ratios = np.array([rate.r for rate in day_rates])
        mu_business = np.array([rate.mu_business for rate in day_rates])
        mu_leisure = np.array([rate.mu_leisure for rate in day_rates])
        requests += draw_segment_requests(category, BUSINESS, mu_business, ratios, rng)
        requests += draw_segment_requests(category, LEISURE, mu_leisure, ratios, rng)
    requests.sort(key=attrgetter('created_at'))
    return requests
