"""Hidden stories and decoys for the pattern seed.

All people and firms in this file are invented. There are three stories:

- Kartell: four people from rival firms meet in changing hotels.
- Schatten: a follower arrives exactly one day after a leader.
- Duo: two merger negotiators stay in the same hotels on the same days.

And two decoys, which look like stories when pairs are only counted:

- Berater: six consultants who work in one single hotel every week.
- Messe: six exhibitors who visit the same trade fairs every year.
"""
import hashlib
from collections import Counter
from datetime import date, datetime, time, timedelta

from seed_calendar import DECOY_FAIRS, EVENTS, events_on, national_holidays
from seed_model import (
    BUSINESS,
    COMMISSION_PCT,
    END_DAY,
    START_DAY,
    Booking,
    CoreCategory,
    StoryGuest,
)

# (first_name, last_name, company, home_state). The order defines the roles.
ROSTER = [
    # Kartell
    ('Konstantin', 'Fiktivius', 'Zement Fiktiv Nord AG', 'Hamburg'),
    ('Philippa', 'Erfundenreich', 'Beton Beispiel Süd GmbH', 'Bayern'),
    ('Quirin', 'Platzhalter', 'Mörtel Märchen West KG', 'Nordrhein-Westfalen'),
    ('Theodora', 'Ausgedacht', 'Kies Kulisse Ost SE', 'Berlin'),
    # Schatten: leader, then follower
    ('Balduin', 'Beispielmann', 'Revision Fiktiv GmbH', 'Baden-Württemberg'),
    ('Ottilie', 'Testhausen', 'Archiv Fantasia Fiktiv UG', 'Niedersachsen'),
    # Duo: merger negotiators of two different firms
    ('Leopold', 'Musterfeld', 'Reederei Fiktiv Hanse AG', 'Hamburg'),
    ('Ludwig', 'Beispielberg', 'Logistik Beispiel Rhein AG', 'Nordrhein-Westfalen'),
    # Berater
    ('Adalbert', 'Probemann', 'Strategie Fiktiv Partner GmbH', 'Bayern'),
    ('Beatrix', 'Probefeld', 'Strategie Fiktiv Partner GmbH', 'Baden-Württemberg'),
    ('Cornelius', 'Musterhain', 'Strategie Fiktiv Partner GmbH', 'Nordrhein-Westfalen'),
    ('Dorothea', 'Testfeld', 'Strategie Fiktiv Partner GmbH', 'Berlin'),
    ('Emil', 'Beispielhof', 'Strategie Fiktiv Partner GmbH', 'Niedersachsen'),
    ('Friederike', 'Erdachtmann', 'Strategie Fiktiv Partner GmbH', 'Hamburg'),
    # Messe
    ('Gustav', 'Scheinwerth', 'Stand und Schau Fiktiv GmbH', 'Nordrhein-Westfalen'),
    ('Hedwig', 'Scheinfeld', 'Stand und Schau Fiktiv GmbH', 'Bayern'),
    ('Ignaz', 'Fabelmann', 'Stand und Schau Fiktiv GmbH', 'Baden-Württemberg'),
    ('Josefine', 'Fabelhain', 'Stand und Schau Fiktiv GmbH', 'Berlin'),
    ('Kasimir', 'Traumfeld', 'Stand und Schau Fiktiv GmbH', 'Niedersachsen'),
    ('Lieselotte', 'Traumhausen', 'Stand und Schau Fiktiv GmbH', 'Hamburg'),
]

# Positions of each role in ROSTER.
KARTELL = slice(0, 4)
LEADER = 4
FOLLOWER = 5
DUO = slice(6, 8)
BERATER = slice(8, 14)
MESSE = slice(14, 20)

MONDAY, TUESDAY, WEDNESDAY, THURSDAY = 0, 1, 2, 3

KARTELL_CITIES = ['Berlin', 'Hamburg', 'München', 'Köln', 'Leipzig', 'Hannover']
KARTELL_MEETINGS = 14
KARTELL_ABSENCES_PER_GUEST = 2  # 12 of 14 meetings, about 85% attendance

SCHATTEN_CITIES = ['Berlin', 'Hamburg', 'München', 'Köln', 'Frankfurt am Main', 'Leipzig', 'Hannover']
SCHATTEN_TRIPS = 25
SCHATTEN_NIGHTS = 3
SCHATTEN_FOLLOWED_TRIPS = 15
SCHATTEN_SOLO_TRIPS = 2

DUO_CITIES = ['Berlin', 'Hamburg', 'München', 'Köln', 'Frankfurt am Main', 'Leipzig']
DUO_STAYS = 18
DUO_NIGHTS = 2

BERATER_CITY = 'Frankfurt am Main'
BERATER_NIGHTS = 3
BERATER_ATTENDANCE = 0.5

MESSE_NIGHTS = 2

HOLIDAYS = {
    day
    for year in range(START_DAY.year, END_DAY.year + 1)
    for day, _name in national_holidays(year)
}


def build_story_guests(first_guest_id: int) -> list[StoryGuest]:
    """Create the invented guests with consecutive ids."""
    guests = []
    for offset, (first_name, last_name, company, home_state) in enumerate(ROSTER):
        guest_id = first_guest_id + offset
        guests.append(StoryGuest(
            guest_id=guest_id,
            first_name=first_name,
            last_name=last_name,
            email=f'gast{guest_id}@example.test',
            home_state=home_state,
            company=company,
        ))
    return guests


def stories_ground_truth(story_guests: list[StoryGuest]) -> dict:
    """Tell the teacher which guest ids belong to which story."""
    ids = [guest.guest_id for guest in story_guests]
    return {
        'kartell': ids[KARTELL],
        'schatten': {'leader': ids[LEADER], 'follower': ids[FOLLOWER]},
        'duo': ids[DUO],
        'berater': ids[BERATER],
        'messe': ids[MESSE],
    }


class StoryPlan:
    """Collects the bookings and remembers what is already taken."""

    def __init__(self, rooms: dict[str, CoreCategory], rates: dict, rng):
        self.rooms = rooms
        self.rates = rates
        self.rng = rng
        self.bookings: list[Booking] = []
        self.guest_nights: set[tuple[int, date]] = set()
        self.room_nights: Counter = Counter()
        self.blocked_arrivals: set[tuple[int, date]] = set()

    def can_book(self, guest_ids: list[int], category: CoreCategory, checkin: date, nights: int) -> bool:
        """Check the date range, the guests' calendars and the free rooms."""
        if checkin < START_DAY or checkin + timedelta(days=nights) > END_DAY:
            return False
        for night in stay_nights(checkin, nights):
            if any((guest_id, night) in self.guest_nights for guest_id in guest_ids):
                return False
            if self.room_nights[(category.category_id, night)] + len(guest_ids) > category.capacity:
                return False
        return True

    def book(self, guest_id: int, category: CoreCategory, checkin: date, nights: int, channel: str) -> None:
        """Add one separate booking for one guest."""
        if not self.can_book([guest_id], category, checkin, nights):
            raise ValueError(f'Story booking does not fit: guest {guest_id} on {checkin}')
        for night in stay_nights(checkin, nights):
            self.guest_nights.add((guest_id, night))
            self.room_nights[(category.category_id, night)] += 1
        lead_days = int(self.rng.integers(3, 15))
        booked_time = time(int(self.rng.integers(7, 22)), int(self.rng.integers(0, 60)))
        self.bookings.append(Booking(
            reservation_id=0,
            guest_id=guest_id,
            category_id=category.category_id,
            checkin=checkin,
            checkout=checkin + timedelta(days=nights),
            status='confirmed',
            created_at=datetime.combine(checkin - timedelta(days=lead_days), booked_time),
            cancelled_at=None,
            rate_per_night=self.rates[(category.category_id, checkin)].offered_rate,
            adults=1,
            children=0,
            channel=channel,
            commission_pct=COMMISSION_PCT[channel],
            card_token=card_token_for_guest(guest_id),
            segment=BUSINESS,
        ))

    def block_arrival(self, category: CoreCategory, day: date) -> None:
        """Keep other trips one day away, so that no accidental pairs appear."""
        for offset in (-1, 0, 1):
            self.blocked_arrivals.add((category.hotel_id, day + timedelta(days=offset)))

    def pick_arrival(self, guest_ids, category, first_day, last_day, weekdays, nights) -> date:
        """Pick a random quiet arrival day between first_day and last_day."""
        candidates = []
        day = first_day
        while day <= last_day:
            if (
                day.weekday() in weekdays
                and (category.hotel_id, day) not in self.blocked_arrivals
                and is_quiet(category.city, day, nights)
                and self.can_book(guest_ids, category, day, nights)
            ):
                candidates.append(day)
            day += timedelta(days=1)
        if not candidates:
            raise ValueError(f'No free day in {category.city} from {first_day} to {last_day}')
        return candidates[int(self.rng.integers(len(candidates)))]


def stay_nights(checkin: date, nights: int) -> list[date]:
    return [checkin + timedelta(days=offset) for offset in range(nights)]


def is_quiet(city: str, checkin: date, nights: int) -> bool:
    """True if no event or holiday touches the stay, including the checkout day."""
    for offset in range(nights + 1):
        day = checkin + timedelta(days=offset)
        if day in HOLIDAYS or events_on(city, day):
            return False
    return True


def card_token_for_guest(guest_id: int) -> str:
    """A random-looking token that stays the same for one guest."""
    return 'tok_' + hashlib.sha256(f'story-card-{guest_id}'.encode()).hexdigest()[:16]


def standard_rooms_by_city(categories: list[CoreCategory]) -> dict[str, CoreCategory]:
    """Find the Standard category of the first hotel in every city."""
    first_hotel: dict[str, int] = {}
    for category in categories:
        first_hotel.setdefault(category.city, category.hotel_id)
    return {
        category.city: category
        for category in categories
        if category.name == 'Standard' and category.hotel_id == first_hotel[category.city]
    }


def time_windows(count: int, nights: int) -> list[tuple[date, date]]:
    """Split the whole period into equal windows, so trips spread over the years."""
    arrival_days = (END_DAY - START_DAY).days + 1 - nights
    windows = []
    for index in range(count):
        first = START_DAY + timedelta(days=index * arrival_days // count)
        last = START_DAY + timedelta(days=(index + 1) * arrival_days // count - 1)
        windows.append((first, last))
    return windows


def city_rotation(cities: list[str], count: int, rng) -> list[str]:
    """Visit the cities in a random order, again and again."""
    order = [cities[int(index)] for index in rng.permutation(len(cities))]
    return [order[index % len(order)] for index in range(count)]


def add_berater(plan: StoryPlan, guest_ids: list[int]) -> None:
    """Decoy: every week the same hotel, so raw pair counts are very high."""
    room = plan.rooms[BERATER_CITY]
    monday = START_DAY + timedelta(days=(MONDAY - START_DAY.weekday()) % 7)
    while monday + timedelta(days=BERATER_NIGHTS) <= END_DAY:
        for guest_id in guest_ids:
            if plan.rng.random() < BERATER_ATTENDANCE:
                plan.book(guest_id, room, monday, BERATER_NIGHTS, 'corporate')
        plan.block_arrival(room, monday)
        monday += timedelta(days=7)


def add_messe(plan: StoryPlan, guest_ids: list[int]) -> None:
    """Decoy: all guests arrive on the first day of every trade fair edition."""
    fairs = [event for event in EVENTS if event.name in DECOY_FAIRS]
    for fair in sorted(fairs, key=lambda event: event.start):
        room = plan.rooms[fair.city]
        if plan.can_book(guest_ids, room, fair.start, MESSE_NIGHTS):
            for guest_id in guest_ids:
                plan.book(guest_id, room, fair.start, MESSE_NIGHTS, 'corporate')
            plan.block_arrival(room, fair.start)


def add_kartell(plan: StoryPlan, guest_ids: list[int]) -> None:
    """Story: secret meetings on quiet Tuesdays, one night, changing hotels."""
    # Never more than one person is missing, and everybody misses equally
    # often. So every pair meets 10 times in at least 4 different hotels.
    absent_slots = [guest_id for guest_id in guest_ids for _ in range(KARTELL_ABSENCES_PER_GUEST)]
    absent_meetings = plan.rng.choice(KARTELL_MEETINGS, size=len(absent_slots), replace=False)
    absent_at = {int(meeting): guest_id for meeting, guest_id in zip(absent_meetings, absent_slots)}

    cities = city_rotation(KARTELL_CITIES, KARTELL_MEETINGS, plan.rng)
    windows = time_windows(KARTELL_MEETINGS, 1)
    for meeting, (city, (first, last)) in enumerate(zip(cities, windows)):
        room = plan.rooms[city]
        arrival = plan.pick_arrival(guest_ids, room, first, last, (TUESDAY,), 1)
        for guest_id in guest_ids:
            if absent_at.get(meeting) != guest_id:
                plan.book(guest_id, room, arrival, 1, 'direct')
        plan.block_arrival(room, arrival)


def add_solo_trips(plan: StoryPlan, guest_id: int, count: int, cities: list[str], nights: int) -> None:
    """Some ordinary trips alone, in quiet weeks."""
    for city, (first, last) in zip(city_rotation(cities, count, plan.rng), time_windows(count, nights)):
        room = plan.rooms[city]
        arrival = plan.pick_arrival([guest_id], room, first, last, (TUESDAY, WEDNESDAY, THURSDAY), nights)
        plan.book(guest_id, room, arrival, nights, 'direct')
        plan.block_arrival(room, arrival)


def add_duo(plan: StoryPlan, guest_ids: list[int]) -> None:
    """Story: same arrival, same hotel, but always two separate bookings."""
    cities = city_rotation(DUO_CITIES, DUO_STAYS, plan.rng)
    for city, (first, last) in zip(cities, time_windows(DUO_STAYS, DUO_NIGHTS)):
        room = plan.rooms[city]
        arrival = plan.pick_arrival(guest_ids, room, first, last, (WEDNESDAY, THURSDAY), DUO_NIGHTS)
        for guest_id in guest_ids:
            plan.book(guest_id, room, arrival, DUO_NIGHTS, 'direct')
        plan.block_arrival(room, arrival)
    for guest_id in guest_ids:
        add_solo_trips(plan, guest_id, int(plan.rng.integers(3, 7)), DUO_CITIES, DUO_NIGHTS)


def add_schatten(plan: StoryPlan, leader: int, follower: int) -> None:
    """Story: on many trips of the leader the follower arrives one day later."""
    followed = {
        int(trip)
        for trip in plan.rng.choice(SCHATTEN_TRIPS, size=SCHATTEN_FOLLOWED_TRIPS, replace=False)
    }
    cities = city_rotation(SCHATTEN_CITIES, SCHATTEN_TRIPS, plan.rng)
    windows = time_windows(SCHATTEN_TRIPS, SCHATTEN_NIGHTS + 1)
    weekdays = (MONDAY, TUESDAY, WEDNESDAY, THURSDAY)
    for trip, (city, (first, last)) in enumerate(zip(cities, windows)):
        room = plan.rooms[city]
        travellers = [leader, follower] if trip in followed else [leader]
        arrival = plan.pick_arrival(travellers, room, first, last, weekdays, SCHATTEN_NIGHTS + 1)
        plan.book(leader, room, arrival, SCHATTEN_NIGHTS, 'corporate')
        plan.block_arrival(room, arrival)
        if trip in followed:
            next_day = arrival + timedelta(days=1)
            plan.book(follower, room, next_day, SCHATTEN_NIGHTS, 'direct')
            plan.block_arrival(room, next_day)
    add_solo_trips(plan, follower, SCHATTEN_SOLO_TRIPS, SCHATTEN_CITIES, SCHATTEN_NIGHTS)


def build_story_bookings(story_guests: list[StoryGuest], categories: list[CoreCategory], rates: dict, rng) -> list[Booking]:
    """Create all story and decoy bookings. Decoys first: their dates are fixed."""
    ids = [guest.guest_id for guest in story_guests]
    plan = StoryPlan(standard_rooms_by_city(categories), rates, rng)
    add_berater(plan, ids[BERATER])
    add_messe(plan, ids[MESSE])
    add_kartell(plan, ids[KARTELL])
    add_duo(plan, ids[DUO])
    add_schatten(plan, ids[LEADER], ids[FOLLOWER])
    return plan.bookings
