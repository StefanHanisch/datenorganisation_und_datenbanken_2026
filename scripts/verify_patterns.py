"""Check that the exported pattern seed contains the planned patterns.

Usage: python scripts/verify_patterns.py [--export data/export] [--private private]

Reads only parquet and private files, never the database. Prints one PASS or
FAIL line per check and ends with exit code 1 if any check fails.
"""
import argparse
import itertools
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from seed_model import BUSINESS, CORE_CAPACITY, LEISURE

MIN_STAYS_FOR_PAIRS = 4  # keeps the pair merge small enough for memory
MIN_HOTELS_PER_PAIR = 4
SMALL_INVERSION = 0.05  # a rise of at most 5 percent counts as small
MAX_INVERSIONS = 1
MIN_RULE_ACCURACY = 0.75
BEST_REVENUE_STEPS = (0.8, 0.9)


def report(name, passed, detail):
    """Print one result line and return whether the check passed."""
    print(f"{'PASS' if passed else 'FAIL'}  {name}: {detail}")
    return bool(passed)


def format_curve(curve):
    return ', '.join(f'{step:.1f}={value:.2f}' for step, value in curve.items())


# --- Loading and preparing ---------------------------------------------------

def load_tables(export_dir):
    """Read the parquet files and normalize dates and numbers."""
    names = ['hotels', 'room_categories', 'reservations', 'daily_rates', 'calendar_events']
    tables = {name: pd.read_parquet(Path(export_dir) / f'{name}.parquet') for name in names}
    return normalize_tables(tables)


def normalize_tables(tables):
    """PostgreSQL DATE and NUMERIC can arrive as Python objects, so convert them."""
    reservations = tables['reservations'].copy()
    reservations['checkin'] = pd.to_datetime(reservations['checkin'])
    reservations['checkout'] = pd.to_datetime(reservations['checkout'])
    created_at = pd.to_datetime(reservations['created_at'], utc=True)
    reservations['created_day'] = created_at.dt.tz_localize(None).dt.normalize()
    reservations['rate_per_night'] = reservations['rate_per_night'].astype(float)

    rates = tables['daily_rates'].copy()
    rates['arrival_date'] = pd.to_datetime(rates['arrival_date'])
    rates['offered_rate'] = rates['offered_rate'].astype(float)
    rates['closed_to_arrival'] = rates['closed_to_arrival'].astype(bool)

    categories = tables['room_categories'].copy()
    categories['base_price'] = categories['base_price'].astype(float)

    events = tables['calendar_events'].copy()
    events['event_date'] = pd.to_datetime(events['event_date'])

    return {
        'hotels': tables['hotels'],
        'room_categories': categories,
        'reservations': reservations,
        'daily_rates': rates,
        'calendar_events': events,
    }


def build_daily_sales(confirmed, rates, categories):
    """One row per category and arrival day, including days without any sale."""
    sales = confirmed.groupby(['category_id', 'checkin']).size().rename('sales').reset_index()
    sales = sales.rename(columns={'checkin': 'arrival_date'})
    daily = rates.merge(sales, how='left', on=['category_id', 'arrival_date'])
    daily['sales'] = daily['sales'].fillna(0)
    prices = categories[['id', 'base_price']].rename(columns={'id': 'category_id'})
    daily = daily.merge(prices, on='category_id')
    daily['r'] = daily['offered_rate'] / daily['base_price']
    daily['r_step'] = daily['r'].round(1)
    daily['revenue'] = daily['sales'] * daily['offered_rate']
    return daily


def build_pair_stays(confirmed, categories, hotels, events):
    """Stays of guests with enough confirmed stays, marked on trade-fair days."""
    stays = confirmed[['guest_id', 'category_id', 'checkin']]
    stays = stays.merge(
        categories[['id', 'hotel_id']].rename(columns={'id': 'category_id'}), on='category_id'
    )
    stays = stays.merge(hotels[['id', 'city_id']].rename(columns={'id': 'hotel_id'}), on='hotel_id')

    stay_counts = stays['guest_id'].value_counts()
    active_guests = stay_counts[stay_counts >= MIN_STAYS_FOR_PAIRS].index
    stays = stays[stays['guest_id'].isin(active_guests)]

    fairs = events[events['event_type'] == 'trade_fair'][['event_date', 'city_id']].drop_duplicates()
    fairs = fairs.rename(columns={'event_date': 'checkin'})
    fairs['city_id'] = fairs['city_id'].astype('int64')
    fairs['is_trade_fair_day'] = True
    stays = stays.merge(fairs, how='left', on=['checkin', 'city_id'])
    stays['is_trade_fair_day'] = stays['is_trade_fair_day'].notna()
    return stays[['guest_id', 'hotel_id', 'checkin', 'is_trade_fair_day']]


def same_day_pairs(stays):
    """One row per two guests arriving in the same hotel on the same day."""
    left = stays[['guest_id', 'hotel_id', 'checkin']].rename(columns={'guest_id': 'guest_a'})
    right = stays[['guest_id', 'hotel_id', 'checkin']].rename(columns={'guest_id': 'guest_b'})
    pairs = left.merge(right, on=['hotel_id', 'checkin'])
    return pairs[pairs['guest_a'] < pairs['guest_b']]


# --- Checks on capacity, prices and demand -----------------------------------

def check_no_overbooking(confirmed, categories):
    """Occupancy = running sum of arrivals minus departures per category."""
    arrivals = confirmed.groupby(['category_id', 'checkin']).size()
    departures = confirmed.groupby(['category_id', 'checkout']).size()
    arrivals.index.names = ['category_id', 'day']
    departures.index.names = ['category_id', 'day']
    change = arrivals.sub(departures, fill_value=0).sort_index()
    occupancy = change.groupby(level='category_id').cumsum().rename('occupied').reset_index()

    capacity = categories[['id', 'name']].rename(columns={'id': 'category_id'})
    capacity['capacity'] = capacity['name'].map(CORE_CAPACITY)
    occupancy = occupancy.merge(capacity, how='left', on='category_id')
    # Written with ~ so that a category without known capacity counts as a problem.
    overbooked = occupancy[~(occupancy['occupied'] <= occupancy['capacity'])]
    return report(
        'Keine Überbelegung', overbooked.empty, f'{len(overbooked)} Nächte über der Kapazität'
    )


def check_rates_match(confirmed, rates, stories):
    story_guests = all_story_guests(stories)
    normal = confirmed[~confirmed['guest_id'].isin(story_guests)]
    merged = normal.merge(
        rates[['category_id', 'arrival_date', 'offered_rate']],
        how='left',
        left_on=['category_id', 'checkin'],
        right_on=['category_id', 'arrival_date'],
    )
    # Written with ~ so that a booking without an offered rate counts as a mismatch.
    matches = (merged['rate_per_night'] - merged['offered_rate']).abs() < 0.005
    mismatches = int((~matches).sum())
    return report(
        'rate_per_night passt zum Angebotspreis',
        len(merged) > 0 and mismatches == 0,
        f'{mismatches} von {len(merged)} Buchungen abweichend',
    )


def check_zero_sale_days(daily):
    zero_days = int((daily['sales'] == 0).sum())
    return report('Tage ohne Verkauf existieren', zero_days > 0, f'{zero_days} Kategorie-Tage')


def check_dynamic_curve_rises(daily):
    dynamic = daily[daily['price_source'] == 'dynamic']
    curve = dynamic.groupby('r_step')['sales'].mean().sort_index()
    passed = len(curve) >= 2 and curve.iloc[-1] > curve.iloc[0]
    return report('Naive Kurve (dynamic) steigt', passed, format_curve(curve))


def check_test_curve_falls(daily):
    test_days = daily[daily['price_source'] == 'test']
    curve = test_days.groupby('r_step')['sales'].mean().sort_index()

    inversions = 0
    large_inversion = False
    for previous, current in zip(curve.iloc[:-1], curve.iloc[1:]):
        if current >= previous:
            inversions += 1
            if current > previous * (1 + SMALL_INVERSION):
                large_inversion = True

    passed = len(curve) >= 3 and inversions <= MAX_INVERSIONS and not large_inversion
    return report(
        'Kurve auf Testtagen fällt', passed, f'{inversions} Umkehrungen; {format_curve(curve)}'
    )


def check_revenue_maximum(daily):
    test_days = daily[daily['price_source'] == 'test']
    curve = test_days.groupby('r_step')['revenue'].mean().sort_index()
    if curve.empty:
        return report('Umsatzmaximum bei r 0,8 oder 0,9', False, 'keine Testtage')
    best_step = round(float(curve.idxmax()), 1)
    return report(
        'Umsatzmaximum bei r 0,8 oder 0,9',
        best_step in BEST_REVENUE_STEPS,
        f'Maximum bei {best_step}; {format_curve(curve)}',
    )


def check_closed_share(rates):
    share = rates['closed_to_arrival'].mean()
    return report(
        'Einige, aber weniger als die Hälfte geschlossen', 0 < share < 0.5, f'Anteil {share:.1%}'
    )


# --- Checks on the hidden stories --------------------------------------------

def all_story_guests(stories):
    schatten = [stories['schatten']['leader'], stories['schatten']['follower']]
    return set(stories['kartell'] + schatten + stories['duo'] + stories['berater'] + stories['messe'])


def check_raw_pairs_show_berater(stays, stories):
    counts = same_day_pairs(stays).groupby(['guest_a', 'guest_b']).size()
    if counts.empty:
        return report('Rohes Zählen: Berater vorn', False, 'keine Paare')
    top_pairs = counts[counts == counts.max()].index
    berater = set(stories['berater'])
    passed = all(a in berater and b in berater for a, b in top_pairs)
    return report('Rohes Zählen: Berater vorn', passed, f'höchste Paarzahl {counts.max()}')


def check_filtered_pairs_show_stories(stays, stories):
    expected = set(itertools.combinations(sorted(stories['kartell']), 2))
    expected.add(tuple(sorted(stories['duo'])))

    normal_stays = stays[~stays['is_trade_fair_day']]
    summary = same_day_pairs(normal_stays).groupby(['guest_a', 'guest_b']).agg(
        meetings=('checkin', 'size'), hotels=('hotel_id', 'nunique')
    )
    kept = summary[summary['hotels'] >= MIN_HOTELS_PER_PAIR]
    kept = kept.sort_values('meetings', ascending=False)

    top_count = len(expected)
    top_pairs = set(kept.index[:top_count])
    # The next pair must be clearly behind, otherwise the top list is not exact.
    clear_gap = len(kept) == top_count or (
        len(kept) > top_count and kept['meetings'].iloc[top_count - 1] > kept['meetings'].iloc[top_count]
    )
    return report(
        'Nach Filtern: genau Kartell und Duo vorn',
        top_pairs == expected and clear_gap,
        f'{len(top_pairs & expected)} von {top_count} geplanten Paaren, {len(kept)} Paare nach Filtern',
    )


def check_schatten_lag(stays, stories):
    """Count how often one guest arrives exactly one day after another guest."""
    leaders = stays[['guest_id', 'hotel_id', 'checkin']].rename(columns={'guest_id': 'leader'})
    leaders['checkin'] = leaders['checkin'] + pd.Timedelta(days=1)
    followers = stays[['guest_id', 'hotel_id', 'checkin']].rename(columns={'guest_id': 'follower'})
    lagged = leaders.merge(followers, on=['hotel_id', 'checkin'])
    lagged = lagged[lagged['leader'] != lagged['follower']]
    counts = lagged.groupby(['leader', 'follower']).size()
    if counts.empty:
        return report('Schatten-Paar beim Versatz vorn', False, 'keine Paare')

    expected = (stories['schatten']['leader'], stories['schatten']['follower'])
    top_pairs = set(counts[counts == counts.max()].index)
    return report(
        'Schatten-Paar beim Versatz vorn',
        top_pairs == {expected},
        f'höchste Zahl {counts.max()}, Schatten-Paar {counts.get(expected, 0)}',
    )


def check_segment_rule(confirmed, ground_truth):
    merged = confirmed.merge(ground_truth, how='left', left_on='id', right_on='reservation_id')
    weekday = merged['checkin'].dt.day_of_week
    lead = (merged['checkin'] - merged['created_day']).dt.days
    predicted = np.where((weekday <= 2) & (lead <= 14) & (merged['adults'] == 1), BUSINESS, LEISURE)
    accuracy = (predicted == merged['segment']).mean()
    return report(
        'np.where-Regel trifft Ground Truth',
        accuracy >= MIN_RULE_ACCURACY,
        f'Trefferquote {accuracy:.1%}, Minimum {MIN_RULE_ACCURACY:.0%}',
    )


# --- Program -----------------------------------------------------------------

def run_checks(tables, stories, ground_truth):
    """Run every check and return True only if all of them passed."""
    reservations = tables['reservations']
    confirmed = reservations[reservations['status'] == 'confirmed']
    if confirmed.empty:
        return report('Bestätigte Buchungen vorhanden', False, '0 Zeilen')

    rates = tables['daily_rates']
    categories = tables['room_categories']
    daily = build_daily_sales(confirmed, rates, categories)
    stays = build_pair_stays(confirmed, categories, tables['hotels'], tables['calendar_events'])

    results = [
        check_no_overbooking(confirmed, categories),
        check_rates_match(confirmed, rates, stories),
        check_zero_sale_days(daily),
        check_dynamic_curve_rises(daily),
        check_test_curve_falls(daily),
        check_revenue_maximum(daily),
        check_closed_share(rates),
        check_raw_pairs_show_berater(stays, stories),
        check_filtered_pairs_show_stories(stays, stories),
        check_schatten_lag(stays, stories),
        check_segment_rule(confirmed, ground_truth),
    ]
    return all(results)


def main():
    parser = argparse.ArgumentParser(description='Prüft die Muster im exportierten Seed.')
    parser.add_argument('--export', default='data/export')
    parser.add_argument('--private', default='private')
    args = parser.parse_args()

    tables = load_tables(args.export)
    private_dir = Path(args.private)
    stories = json.loads((private_dir / 'stories.json').read_text(encoding='utf-8'))
    ground_truth = pd.read_csv(private_dir / 'ground_truth.csv')

    all_passed = run_checks(tables, stories, ground_truth)
    print('Alle Prüfungen bestanden.' if all_passed else 'Mindestens eine Prüfung ist fehlgeschlagen.')
    sys.exit(0 if all_passed else 1)


if __name__ == '__main__':
    main()
