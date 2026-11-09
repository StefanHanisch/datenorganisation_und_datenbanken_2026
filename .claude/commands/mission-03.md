ACTIVATE MISSION-03 ONLY. Read `AGENTS.md` and `docs/missions/03-reservation-change.md`.

The class's approach is:
$ARGUMENTS

Implement date changes in `app/mission03_change.py`, reusing
`services.category_has_capacity`, including a row lock on `room_categories`.
Never use the simple total-overlap count for category capacity; inspect each night.
Write useful integration tests in an isolated DB. Do not alter unrelated missions.
Run test suite, show diff, STOP before deployment unless teacher approves.
