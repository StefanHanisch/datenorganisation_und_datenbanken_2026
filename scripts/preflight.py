#!/usr/bin/env python3
"""Non-destructive HTTP preflight; start Docker and seed demo first.

Usage: python scripts/preflight.py [--url http://localhost:8000]
"""
import argparse
import getpass
import httpx


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--url', default='http://localhost:8000')
    a = p.parse_args()
    code = getpass.getpass('Student access code: ')
    with httpx.Client(base_url=a.url, timeout=20, follow_redirects=False) as client:
        resp = client.get('/health')
        assert resp.status_code == 200 and resp.json()['status'] == 'ok', 'Health check failed'
        resp = client.post('/login', data={'code':code})
        assert resp.status_code == 303, 'Student login failed'
        resp = client.get('/admin')
        assert resp.status_code == 200, 'Control center unavailable'
        read = client.post('/api/admin/sql', json={'sql':'SELECT id,name FROM cities LIMIT 2'})
        assert read.status_code == 200 and read.json()['type'] == 'result', read.text
        denied = client.post('/api/admin/sql', json={'sql':'DELETE FROM guests'})
        assert denied.status_code == 400, 'Danger: student SQL DELETE accepted by API'
        write = client.post('/api/admin/hotels', json={
            'city_id':1,'name':'SHOULD NEVER BE CREATED','address':'X','stars':3,
        })
        assert write.status_code == 403, 'Danger: student reached teacher POST'
        print('OK — health, student login, SQL SELECT, DELETE rejection, teacher-only POST')


if __name__ == '__main__':
    main()
