"""Turn the drawn booking requests into the reservation history of the core hotels.

The simulation runs through time like a real booking system: every request
arrives at its created_at, sees the rooms that are sold at that moment and is
either booked or rejected. Cancelled bookings give their rooms back at
cancelled_at, so later requests can use them.
"""
import hashlib
import heapq
from array import array
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from operator import attrgetter

import numpy as np

from seed_demand import build_daily_rates, draw_requests
from seed_holidays import home_state_for_guest, in_summer_holidays, in_summer_season
from seed_model import (
    BUSINESS,
    COMMISSION_PCT,
    END_DAY,
    START_DAY,
    Booking,
    CoreCategory,
    Request,
    StoryGuest,
    is_business_guest,
)
from seed_stories import build_story_bookings, build_story_guests, stories_ground_truth

FREQUENT_GUEST_SHARE = 0.02
REGULAR_GUEST_SHARE = 0.18
FREQUENT_BOOKING_SHARE = 0.20
REGULAR_BOOKING_SHARE = 0.40
MAX_GUEST_TRIES = 5

MAX_GUESTS = {'Standard': 2, 'Deluxe': 3, 'Suite': 4}
FAMILY_SHARE = 0.55
FAMILY_DROP_OUTSIDE_HOLIDAYS = 0.7

LEISURE_OTA_SHARE = 0.60
BUSINESS_CORPORATE_SHARE = 0.50
BUSINESS_DIRECT_SHARE = 0.30
LEISURE_OTA_CANCEL = 0.25
OTHER_CANCEL = 0.10


@dataclass
class CoreResult:
    story_guests: list[StoryGuest]
    bookings: list[Booking]
    rates: dict
    closed: set[tuple[int, date]]
    stories: dict


class RandomStream:
    """Hands out uniform random numbers one by one, drawn from numpy in large blocks."""

    BLOCK_SIZE = 1_000_000

    def __init__(self, rng: np.random.Generator):
        self.rng = rng
        self.block: list[float] = []
        self.position = 0

    def next(self) -> float:
        if self.position == len(self.block):
            self.block = self.rng.random(self.BLOCK_SIZE).tolist()
            self.position = 0
        value = self.block[self.position]
        self.position += 1
        return value


class Occupancy:
    """Counts the sold rooms per category and night. Nights are day numbers from START_DAY."""

    def __init__(self, categories: list[CoreCategory], day_count: int):
        self.sold = {c.category_id: array('H', [0]) * day_count for c in categories}
        self.capacity = {c.category_id: c.capacity for c in categories}

    def has_room(self, category_id: int, first_night: int, end_night: int) -> bool:
        return max(self.sold[category_id][first_night:end_night]) < self.capacity[category_id]

    def book(self, category_id: int, first_night: int, end_night: int) -> None:
        sold = self.sold[category_id]
        for night in range(first_night, end_night):
            sold[night] += 1

    def release(self, category_id: int, first_night: int, end_night: int) -> None:
        sold = self.sold[category_id]
        for night in range(first_night, end_night):
            sold[night] -= 1


class GuestPool:
    """Picks guests by segment and tier and remembers the stays of each guest.

    A cancelled stay stays in the guest's calendar. This is a little stricter
    than necessary and keeps the rule simple: no two bookings of a guest overlap.
    """

    def __init__(self, guest_count: int, seed: int, rng: np.random.Generator, random: RandomStream):
        self.seed = seed
        self.random = random
        self.stays: dict[int, list[tuple[int, int]]] = {}
        self.card_tokens: dict[int, str] = {}
        shuffled = rng.permutation(np.arange(1, guest_count + 1)).tolist()
        business = [g for g in shuffled if is_business_guest(g)]
        leisure = [g for g in shuffled if not is_business_guest(g)]
        if not business or not leisure:
            raise ValueError('guest_count is too small to have business and leisure guests')
        self.tiers = {True: split_into_tiers(business), False: split_into_tiers(leisure)}

    def pick_free_guest(self, segment: str, first_night: int, end_night: int) -> int | None:
        """Return a guest who is free on these nights, or None after a few tries."""
        frequent, regular, occasional = self.tiers[segment == BUSINESS]
        for _ in range(MAX_GUEST_TRIES):
            tier_draw = self.random.next()
            if tier_draw < FREQUENT_BOOKING_SHARE:
                tier = frequent
            elif tier_draw < FREQUENT_BOOKING_SHARE + REGULAR_BOOKING_SHARE:
                tier = regular
            else:
                tier = occasional
            guest_id = tier[int(self.random.next() * len(tier))]
            if self.is_free(guest_id, first_night, end_night):
                return guest_id
        return None

    def is_free(self, guest_id: int, first_night: int, end_night: int) -> bool:
        for stay_first, stay_end in self.stays.get(guest_id, ()):
            if first_night < stay_end and stay_first < end_night:
                return False
        return True

    def add_stay(self, guest_id: int, first_night: int, end_night: int) -> None:
        self.stays.setdefault(guest_id, []).append((first_night, end_night))

    def card_token(self, guest_id: int) -> str:
        token = self.card_tokens.get(guest_id)
        if token is None:
            digest = hashlib.sha256(f'{self.seed}:{guest_id}'.encode()).hexdigest()
            token = f'tok_{digest[:24]}'
            self.card_tokens[guest_id] = token
        return token


def split_into_tiers(pool: list[int]) -> tuple[list[int], list[int], list[int]]:
    """Split a shuffled guest list into frequent, regular and occasional guests."""
    frequent_end = int(len(pool) * FREQUENT_GUEST_SHARE)
    regular_end = frequent_end + int(len(pool) * REGULAR_GUEST_SHARE)
    # A very small pool can leave a tier empty; then that tier uses the whole pool.
    return pool[:frequent_end] or pool, pool[frequent_end:regular_end] or pool, pool[regular_end:]


def draw_party(segment: str, category_name: str, random: RandomStream) -> tuple[int, int]:
    """Return (adults, children) for one booking."""
    if segment == BUSINESS:
        return 1, 0
    if category_name == 'Standard' or random.next() >= FAMILY_SHARE:
        return 2, 0
    most_children = MAX_GUESTS[category_name] - 2
    return 2, 1 + int(random.next() * most_children)


def draw_channel(segment: str, random: RandomStream) -> str:
    draw = random.next()
    if segment == BUSINESS:
        if draw < BUSINESS_CORPORATE_SHARE:
            return 'corporate'
        return 'direct' if draw < BUSINESS_CORPORATE_SHARE + BUSINESS_DIRECT_SHARE else 'ota'
    return 'ota' if draw < LEISURE_OTA_SHARE else 'direct'


def draw_cancelled_at(request: Request, channel: str, random: RandomStream) -> datetime | None:
    """Return the moment of cancellation, or None if the booking is kept."""
    is_leisure_ota = request.segment != BUSINESS and channel == 'ota'
    if random.next() >= (LEISURE_OTA_CANCEL if is_leisure_ota else OTHER_CANCEL):
        return None
    arrival = request.arrival
    checkin_start = datetime(arrival.year, arrival.month, arrival.day, tzinfo=request.created_at.tzinfo)
    return request.created_at + (checkin_start - request.created_at) * random.next()


def is_dropped_family(guest_id: int, arrival: date, random: RandomStream) -> bool:
    """Families mostly travel in summer only if their home state has school holidays."""
    if not in_summer_season(arrival):
        return False
    if in_summer_holidays(home_state_for_guest(guest_id), arrival):
        return False
    return random.next() < FAMILY_DROP_OUTSIDE_HOLIDAYS


def place_story_bookings(story_bookings: list[Booking], occupancy: Occupancy, guests: GuestPool) -> None:
    """Story bookings come first, they must never be pushed out by normal demand."""
    for booking in story_bookings:
        first_night = (booking.checkin - START_DAY).days
        end_night = (booking.checkout - START_DAY).days
        if first_night < 0 or not occupancy.has_room(booking.category_id, first_night, end_night):
            raise ValueError(f'story booking does not fit: {booking}')
        occupancy.book(booking.category_id, first_night, end_night)
        booking.card_token = guests.card_token(booking.guest_id)


def process_requests(
    requests: list[Request],
    categories: list[CoreCategory],
    rates: dict,
    calendar_days: list[date],
    occupancy: Occupancy,
    guests: GuestPool,
    random: RandomStream,
) -> tuple[list[Booking], set[tuple[int, date]]]:
    """Go through the requests in created_at order and book what still fits."""
    category_names = {c.category_id: c.name for c in categories}
    bookings: list[Booking] = []
    closed: set[tuple[int, date]] = set()
    cancellations: list[tuple] = []  # heap: earliest cancelled_at on top

    for request in requests:
        while cancellations and cancellations[0][0] <= request.created_at:
            _, _, category_id, first_night, end_night = heapq.heappop(cancellations)
            occupancy.release(category_id, first_night, end_night)

        category_id = request.category_id
        first_night = (request.arrival - START_DAY).days
        end_night = first_night + request.nights
        if not occupancy.has_room(category_id, first_night, end_night):
            closed.add((category_id, request.arrival))
            continue

        guest_id = guests.pick_free_guest(request.segment, first_night, end_night)
        if guest_id is None:
            continue
        adults, children = draw_party(request.segment, category_names[category_id], random)
        if children > 0 and is_dropped_family(guest_id, request.arrival, random):
            continue

        channel = draw_channel(request.segment, random)
        cancelled_at = draw_cancelled_at(request, channel, random)
        occupancy.book(category_id, first_night, end_night)
        guests.add_stay(guest_id, first_night, end_night)
        if cancelled_at is not None:
            # len(bookings) is unique, so the heap never has to compare further fields.
            heapq.heappush(cancellations, (cancelled_at, len(bookings), category_id, first_night, end_night))
        bookings.append(Booking(
            reservation_id=0,
            guest_id=guest_id,
            category_id=category_id,
            checkin=request.arrival,
            checkout=calendar_days[end_night],
            status='confirmed' if cancelled_at is None else 'cancelled',
            created_at=request.created_at,
            cancelled_at=cancelled_at,
            rate_per_night=rates[(category_id, request.arrival)].offered_rate,
            adults=adults,
            children=children,
            channel=channel,
            commission_pct=COMMISSION_PCT[channel],
            card_token=guests.card_token(guest_id),
            segment=request.segment,
        ))
    return bookings, closed


def generate_core(
    categories: list[CoreCategory],
    guest_count: int,
    first_story_guest_id: int,
    seed: int,
) -> CoreResult:
    """Build all core reservations. The same arguments always give the same result."""
    if first_story_guest_id <= guest_count:
        raise ValueError('story guests need ids above the normal guest pool')

    rng = np.random.default_rng(seed)
    rates = build_daily_rates(categories, rng)
    story_guests = build_story_guests(first_story_guest_id)
    story_bookings = build_story_bookings(story_guests, categories, rates, rng)
    requests = draw_requests(categories, rates, rng)
    random = RandomStream(rng)
    guests = GuestPool(guest_count, seed, rng, random)

    # The calendar must also reach the last checkout after END_DAY.
    longest_stay = max((r.nights for r in requests), default=1)
    last_story_day = max((b.checkout for b in story_bookings), default=START_DAY)
    last_day = max(END_DAY + timedelta(days=longest_stay), last_story_day)
    day_count = (last_day - START_DAY).days + 1
    calendar_days = [START_DAY + timedelta(days=i) for i in range(day_count)]

    occupancy = Occupancy(categories, day_count)
    place_story_bookings(story_bookings, occupancy, guests)
    bookings, closed = process_requests(requests, categories, rates, calendar_days, occupancy, guests, random)

    # Ids follow the booking time, so they do not give away the story bookings.
    bookings.extend(story_bookings)
    bookings.sort(key=attrgetter('created_at'))
    for reservation_id, booking in enumerate(bookings, start=1):
        booking.reservation_id = reservation_id

    return CoreResult(story_guests, bookings, rates, closed, stories_ground_truth(story_guests))
