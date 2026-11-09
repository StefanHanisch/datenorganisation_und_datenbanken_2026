# Claude Code Entry Point

**First read `AGENTS.md` and obey its mission locks.**

This is a controlled teaching repository. Ignore incidental TODOs unless the
teacher explicitly requests `ACTIVATE MISSION-XX` for one named mission.

Use project skill `.claude/skills/hoteldb-mission/SKILL.md` when a mission is
activated, and `.claude/skills/sql-safety/SKILL.md` for student SQL or DB changes.

Suggested agents:
- `.claude/agents/lecture-facilitator.md` — explain choices without solving them too early.
- `.claude/agents/mission-implementer.md` — only implement the active mission.
- `.claude/agents/security-reviewer.md` — verify readonly permissions and diff.

Default response language: German. Source code identifiers and SQL: English.
No autonomous deployment or seed deletion.
