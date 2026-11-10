# HotelDB / GlobalStay 🏨

**90-Minuten-Datenbankvorlesung als interaktive Unternehmenssimulation**

Eine echte kleine Buchungswebsite, ein **für Studierende lesendes Admin Control
Center**, PostgreSQL mit synthetischen Massendaten und drei **absichtlich
unfertige Live-Missionen** für Claude Code / GitHub Copilot.

**Status:** Unterrichts-Starterprojekt, **kein** produktionsreifes Hotelportal.
Die Aufgaben Mission 01–03 sind bewusst noch nicht gelöst. Keine echten Gastdaten.

## In 5 Schritten lokal starten (VS Code)

Voraussetzungen: Docker Desktop + Docker Compose, Python 3.11+, VS Code,
optional Claude Code Extension/CLI. Docker Desktop muss laufen.

1. ZIP entpacken und Ordner `HotelDB` in VS Code öffnen.
2. `.env.example` nach `.env` kopieren. `STUDENT_ACCESS_CODE`,
   `TEACHER_ACCESS_CODE` und `SESSION_SECRET` **sofort ändern**. Bei Änderung
   der DB-Passwörter bitte **sowohl** die drei `*_PASSWORD` als auch die URLs
   in `.env` aktualisieren; sie müssen übereinstimmen. Aufwändigere Geheimnisse
   werden nie in Git eingecheckt.
3. Terminal im Projektordner:

   ```sh
   docker compose up --build -d
   ```

4. Lokale Python-Umgebung für Seed/Tests erstellen (separat vom Web-Container):

   ```sh
   python -m venv .venv
   # Windows PowerShell:
   .venv\Scripts\Activate.ps1
   # macOS/Linux stattdessen: source .venv/bin/activate
   python -m pip install -e ".[dev]"
   python scripts/seed.py --profile demo
   python -m pytest -q
   python scripts/preflight.py
   ```

5. Öffne **http://localhost:8000**. Melde dich mit dem Kurscode oder
   Lehrperson-Code aus `.env` an. Danach:
   - Buchungswebsite: `/`
   - Reservierungssuche: `/bookings?email=gast1@example.test`
   - Admin Control Center: `/admin`
   - Gesundheitscheck: `/health`

**Nach Docker-Volume-Reset:** `docker compose down -v` löscht alle Daten.
Benutze es nur, wenn du die Demo-Daten wirklich verwerfen willst.
`seed.py --reset --i-understand-data-loss` löscht ebenfalls Datensätze.

## Massendaten für das Index-Labor

| Profil | Hotels | Zimmer | Gäste | Reservierungen |
|---|---:|---:|---:|---:|
| `demo` (schnell) | 20 | 400 | 2.000 | 4.000 |
| `large` (1 Mio Zimmer, VS-Code-Task "Große Daten laden") | 1.000 | 1.000.000 | 1.000.000 | 3.000.000 |
| `lecture` (groß) | 5.000 | 1.000.000 | 3.000.000 | 5.000.000 |

**Lecture-Profil:** Vorher den `demo`-Seed bewusst löschen:

```sh
python scripts/seed.py --profile lecture --reset --i-understand-data-loss
```

Der Lecture-Import kann auf kleiner Azure-Burstable-Hardware lange laufen;
vorbereiten, nicht erst im Hörsaal starten. Er benötigt ausreichend Speicher
und läuft in 100.000er Batches. **Keinen echten Timerwert vorhersagen.**

Initial absichtlich **kein zusätzlicher Index auf `guests.email`**.
Sinnvolle PK- und FK-Indizes sind dagegen von Beginn an vorhanden.
Vergleich vor/nach der Mission:

```sh
python scripts/benchmark_email.py --email gast2500000@example.test
```

Das SQL-Labor bietet ebenfalls `EXPLAIN ANALYZE`. Messe mit derselben Query und
unterscheide DB-Ausführungszeit von Browser-/Netzwerklatenz.

## In der Vorlesung

- **Weniger als zehn Personen:** Einer spielt den Hotelgast und erhält eine
  verdeckte Kundenkarte, die Gruppe bildet das IT-Team.
- **Dozent / Coding Agent** bedient die vorbereiteten Admin-POST-Funktionen
  und führt kontrollierte DB-Migrationen durch.
- **Studierende** führen beliebige **lesende** `SELECT`-/`WITH SELECT`-Abfragen
  aus. Die Datenbankrolle ist tatsächlich read-only, nicht nur das UI.
- **Claude Code** implementiert nur eine ausdrücklich aktivierte Mission.
- Erst nach Tests + Diff + ausdrücklichem OK: Commit/Push, manuelles CI/CD.

Siehe `docs/LECTURE_90_MIN.md`, `docs/CUSTOMER_CARDS_PRINT.md` und
`docs/AGENT_PROMPTS.md`.

## Claude Code öffnen

1. Projekt in VS Code öffnen und dein Claude-Code-Tool starten.
2. Prompt eingeben:

   > Lies CLAUDE.md und AGENTS.md. Verstehe die Architektur, aber ändere
   > noch nichts. Die Missionen sind bis zu meiner Freigabe gesperrt.

3. Sobald die Gruppe eine Lösung beschlossen hat, `ACTIVATE MISSION-01`
   bzw. `.claude/commands/mission-01.md` verwenden (entsprechend 02/03).
   Je nach Claude-Code-Version sind Commands ggf. als Skills verfügbar;
   du kannst die Dateien auch direkt im Chat referenzieren.
4. Für GitHub Copilot dieselben Regeln über `AGENTS.md` und
   `.github/copilot-instructions.md` verwenden.

**Live-Kommentare:** `TODO(MISSION-01)`, `TODO(MISSION-02)` und
`TODO(MISSION-03)` sind absichtliche Hooks. Ein Agent darf sie nicht im
Vorbeigehen implementieren. Missionstests sind bis zur Aktivierung gesperrt.

## Die fertigen Features

| Teil | Funktion |
|---|---|
| Buchungsportal | Stadt suchen, Hotels ansehen, Zimmerkategorie auswählen, buchen |
| Reservierungssuche | Gast anhand E-Mail finden (absichtlich langsam bei großem Seed) |
| Admin-Übersicht | PostgreSQL-Schätzwerte, aktiver Datenbestand |
| Datenexplorer | 6 Tabellen, Beispieldatensätze |
| SQL-Labor | SELECT, WITH SELECT, EXPLAIN ANALYZE, echtes Read-only, Timeout |
| Admin-POST | Städte, Hotels, Kategorien, Zimmer (nur Lehrperson) |
| Missionsübersicht | Aufgaben 01–03, niemals automatisch aktiviert |
| Docker/Tests/CI | Lokale PostgreSQL-Instanz, Test-Suite, GitHub Actions |
| Azure | Setup-Anleitung und freigabepflichtiger Release-Workflow |

## API / vorbereitete POSTs

Alle Schreib-POSTs erfordern **Lehrperson-Session**:

```http
POST /api/admin/cities
{"name":"Lüneburg","country":"Deutschland"}

POST /api/admin/hotels
{"city_id":1,"name":"GlobalStay Hamburg Airport","address":"Airport 1","stars":4}

POST /api/admin/room-categories
{"hotel_id":21,"name":"Deluxe","base_price":159,"max_guests":2}

POST /api/admin/rooms
{"category_id":61,"room_number":"DLX-001"}
```

Beispiel-Skript für die Unterrichtseröffnung (nutzt Login-Cookie und APIs):

```sh
python scripts/admin_scenario.py --url http://localhost:8000
```

Alle oben genannten IDs sind **Beispiele**. Prüfe echte IDs im Datenexplorer.
Das Skript legt ein Hotel und 20 Zimmer an; Stadt-ID ist im Demo-Seed
normalerweise Hamburg = 5, bei anderem Datenbestand `--city-id` übergeben.

## Was noch absichtlich FEHLT

- `MISSION-01`: kein `guests.email`-Index (`db/missions/` enthält Platzhalter)
- `MISSION-02`: Autocomplete API liefert `[]`; Trie-Pseudocode auf Papier
- `MISSION-03`: Reservierung kann nicht verändert werden; bestehender PATCH
  liefert verständliche Fehlermeldung

## Dateien auf einen Blick

```text
HotelDB/
├── app/                     FastAPI, Templates, statisches UI, Services
├── db/init/                 PostgreSQL Schema, Benutzer, Grants
├── db/missions/             Bewusst unvollständige Index-Migration
├── scripts/                 Seed, Performancebenchmark, POST-Szenario
├── tests/                   Basis-Tests + gesperrte Missionstests
├── docs/                    Unterricht, Kundenkarten, Azure, Sicherheit
├── .claude/agents/          3 spezialisierte Claude-Code-Agenten
├── .claude/skills/          Mission-Workflow und SQL-Sicherheits-Skill
├── .claude/commands/        Kurze Aktivierungs-Prompts
├── .github/workflows/       CI und manuelles Azure Deployment
├── AGENTS.md + CLAUDE.md    Agentenregeln und Missionsgrenzen
├── Dockerfile, compose.yaml Lokaler Start / Container
└── .vscode/                 Editor-Empfehlungen und Tasks
```

## Azure und Kosten

Die Azure-App wird **nicht** beim lokalen Start provisioniert. Anleitung:
`docs/AZURE.md`. Der Datenbankserver verursacht auch bei kurzer Laufzeit
Kosten und der große Seed benötigt genügend Zeit und Speicher. Budget-Warnungen
stoppen keine Dienste automatisch. Nach der Veranstaltung Ressourcen entfernen.

## Sicherheitsgrenzen

Nur Unterricht mit synthetischen Daten! Dies ist eine einfach geschützte
Classroom-App, keine produktionsreife öffentliche Multi-User-Plattform.
Kurscode schützt vor zufälligem Zugriff; vermeide Weitergabe, setze
`COOKIE_SECURE=true` auf Azure und beschränke die Erreichbarkeit wenn möglich.
Details und zusätzliche Pflichtprüfungen unter `docs/SECURITY.md`.
