# HotelDB — Mandatory Instructions for ALL Coding Agents

This project is a **90-minute live teaching simulation**, not a product backlog.
The intentional gaps are the teaching material. Do not "clean up" the gaps.

## Mission-lock rules (CRITICAL)

1. NEVER implement any `TODO(MISSION-XX)` unless the teacher explicitly says **ACTIVATE MISSION-XX**.
2. Touch **only** code owned by the activated mission and directly dependent tests.
3. Never implement future missions, even when you can predict their solutions.
4. Do not preemptively optimize SQL, add indexes, introduce caches, or replace the Trie with SQL features.
5. Do not remove the initial unindexed `guests.email` state before Mission 01.
6. No automatic SQL migrations against Azure, no seed reset, no destructive operations without teacher confirmation.
7. After coding: run the relevant tests, inspect the Git diff, summarize changes; STOP before commit/push/deployment unless the teacher explicitly approves.

## How to work in the lecture

- Think of the students as architects. Ask for their jointly reached algorithm/decision before implementing an activated mission.
- State which exact files you plan to touch; prefer a change small enough to explain in ~3 minutes.
- Use the existing FastAPI endpoint and function contracts. Do not rebuild the website or the data model.
- Keep code readable for SQL and OOP beginners: simple classes/functions, explicit names, no clever abstractions.
- Report actual measurements, never invented execution times or index wins.
- Do not change the 4-second student query timeout or student read-only DB credentials.

## Current mission locations

- `MISSION-01` — `db/missions/mission01_email_index.sql`, `app/main.py` (`bookings`), `scripts/benchmark_email.py`. Task: **only** investigate and (after decision) add `guests.email` index.
- `MISSION-02` — `app/mission02_autocomplete.py`, `tests/missions/test_mission02_future.py`. Task: implement the **student-designed Trie**; preserve `suggest_cities(prefix, available)`.
- `MISSION-03` — `app/mission03_change.py`, `app/services.py`, reservation PATCH endpoint. Task: edit dates transactionally with existing category capacity checks.

## Security guardrails

- Student SQL runs through `hotel_student`, never `hotel_app` or `hotel_owner`.
- Student SQL must stay read-only; continue to enforce SELECT validation, a read-only transaction, limited result rows and server-side timeout.
- Admin POST endpoints require the teacher session; ordinary booking is available to students.
- All demo emails use `@example.test`; never import real hotel customer data.
- Don't expose access codes, Azure credentials, connection strings, or `.env` in commits/logs.

## Commands

```sh
python -m pytest -q
python -m compileall -q app scripts
# After activating mission 02:
RUN_MISSION_02=1 python -m pytest tests/missions/test_mission02_future.py -q
```

## Before suggesting any deployment

1. Show `git diff --stat` and relevant diff.
2. Explain precisely which mission changed.
3. Verify unrelated mission TODOs are unchanged.
4. Verify tests pass.
5. Ask teacher to explicitly approve commit/push/deploy.
