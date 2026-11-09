---
name: hoteldb-mission
description: Follow the controlled live-coding workflow for an explicitly activated HotelDB lecture mission.
---

# HotelDB Mission Protocol

Only engage when the teacher says `ACTIVATE MISSION-01`, `ACTIVATE MISSION-02`, or `ACTIVATE MISSION-03`.

1. Read `AGENTS.md` and the corresponding file in `docs/missions/`.
2. Confirm the class's *decision* in a sentence; if missing, ask for the chosen solution rather than selecting one yourself.
3. State the **only files** you intend to edit. Never open a new mission by implication.
4. Keep the smallest working change that matches the joint solution.
5. Run mission-related tests and the normal suite. Only activate intentional-red tests for the current mission.
6. Show measurements or test results; do not invent timings.
7. Show Git diff; require approval before push or Azure deployment.

Mission 01: index selection and EXPLAIN ANALYZE; do not silently change queries.
Mission 02: student's paper Trie; don't replace with a database feature.
Mission 03: preserve category-based booking, lock the category and validate *each night*.
