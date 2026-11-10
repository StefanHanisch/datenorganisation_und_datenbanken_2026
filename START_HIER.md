# START HIER — HotelDB in VS Code

**Das Projekt ist bereits vorbereitet. Nicht mit Claude Code die drei Missionen
beim Einrichten lösen lassen.**

## Lokal starten (Windows / VS Code)

1. Ordner `HotelDB` in VS Code öffnen.
2. `.env.example` zu `.env` kopieren, beide Zugangscodes und `SESSION_SECRET`
   austauschen. Database-URLs/Passwörter müssen zusammenpassen.
3. `docker compose up --build -d` (Docker Desktop läuft).
4. In der VS-Code-Python-Umgebung:

   ```powershell
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   python -m pip install -e ".[dev]"
   python scripts/seed.py --profile demo
   python scripts/preflight.py
   ```

5. Browser `http://localhost:8000`, mit Kurscode anmelden. `/admin` öffnen.

## Claude Code: erster Prompt

> Lies CLAUDE.md und AGENTS.md. Untersuche, ob Website, SQL-Labor und
> Datenbankschema vorbereitet sind. Implementiere **keine** TODO(MISSION-XX)
> und ändere noch keinen Code.

## Vor der Vorlesung

- Vorlesungsablauf klein → groß: erst `demo` messen, dann den VS-Code-Task
  „HotelDB: Große Daten laden (1 Mio Zimmer)“ (`--profile large`, ersetzt die
  Demo-Daten) ausführen und erneut messen.
- Auf großem Datensatz testen: `python scripts/seed.py --profile lecture --reset
  --i-understand-data-loss` (Dauer/Storage vorher beachten).
- Kundenkarten unter `docs/CUSTOMER_CARDS_PRINT.md` ausdrucken.
- Vorlesungsablauf `docs/LECTURE_90_MIN.md` öffnen.
- `docs/SECURITY.md` kontrollieren, insbesondere DB-Rollen.
- Azure: `docs/AZURE.md`. GH Actions deploy erst nach manueller Freigabe.

## Missionsfreigaben

| Freigabe | Darf live geändert werden? |
|---|---|
| `ACTIVATE MISSION-01` | Indexmigration auf guests.email |
| `ACTIVATE MISSION-02` | Python Trie-Autocomplete |
| `ACTIVATE MISSION-03` | Reservierungsänderung |

**Kein Agent bekommt pauschal den Auftrag, alle TODOs zu erledigen!**
