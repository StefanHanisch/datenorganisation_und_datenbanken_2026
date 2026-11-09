#!/usr/bin/env python3
"""Run BEFORE and AFTER Mission 01; does not create an index."""
import argparse
import json
import os
import psycopg
from dotenv import load_dotenv


def main():
    load_dotenv()
    parser = argparse.ArgumentParser()
    parser.add_argument('--email', default='gast1@example.test')
    args = parser.parse_args()
    url = os.getenv('STUDENT_DATABASE_URL')
    if not url:
        parser.error('STUDENT_DATABASE_URL not set')
    with psycopg.connect(url) as conn:
        conn.execute('SET TRANSACTION READ ONLY')
        plan = conn.execute('''
            EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)
            SELECT * FROM guests WHERE email = %s
        ''', (args.email,)).fetchone()[0]
        print(json.dumps(plan, indent=2))


if __name__ == '__main__':
    main()
