#!/usr/bin/env python3
"""Teacher-only example: open an airport hotel via prepared POST endpoints.

Usage: python scripts/admin_scenario.py --url http://localhost:8000 --teacher-code <code>
Use only fabricated data; it creates real records in your demo database.
"""
import argparse
import getpass
import httpx


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default='http://localhost:8000')
    parser.add_argument('--teacher-code', default='')
    parser.add_argument('--city-id', type=int, default=5)
    args = parser.parse_args()
    code = args.teacher_code or getpass.getpass('Teacher code: ')
    with httpx.Client(base_url=args.url, follow_redirects=False, timeout=20.0) as client:
        r = client.post('/login', data={'code': code})
        if r.status_code != 303:
            raise SystemExit(f'Login failed (HTTP {r.status_code})')

        def create(path, payload):
            res = client.post('/api/admin/' + path, json=payload)
            res.raise_for_status()
            print(f'POST /api/admin/{path} -> {res.json()}')
            return res.json()['id']

        hotel = create('hotels', {'city_id': args.city_id,
            'name': 'GlobalStay Hamburg Airport – Campus Opening',
            'address': 'Flughafenstraße 1', 'stars': 4})
        for name, price, amount, code in [
            ('Standard', 109, 12, 'STD'), ('Deluxe', 159, 6, 'DLX'),
            ('Suite', 259, 2, 'STE'),
        ]:
            cat = create('room-categories', {'hotel_id': hotel, 'name': name,
                'base_price': price, 'max_guests': 2})
            for number in range(1, amount + 1):
                create('rooms', {'category_id': cat, 'room_number': f'{code}-{number:03}'})
        print('Done. Ask students to verify the new hotel with a JOIN in SQL lab.')


if __name__ == '__main__':
    main()
