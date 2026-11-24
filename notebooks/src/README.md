# Quellen für das Hotel-Analytics-Notebook

Aus diesen Dateien erzeugt `python scripts/build_notebooks.py` zwei Notebooks:

- `notebooks/hotel_analytics.ipynb` – für Studierende, mit Lücken `___`
- `notebooks/hotel_analytics_loesung.ipynb` – Lösung

**Nie die `.ipynb` von Hand bearbeiten**, immer hier ändern und neu bauen.

## Dateien und Reihenfolge

Der Generator liest die Blockdateien in Namensreihenfolge:

| Datei | Inhalt |
|---|---|
| `00_setup.py` | Titel, Zeittabelle, So startest du, Spickzettel, Setup-Zelle |
| `01_gaeste.py` | Block 1: Wer sind unsere Gäste? (lädt Daten, baut `places`, `stays`) |
| `01b_sql.py` | Block 1b: SQL und pandas (direkt in der Datenbank) |
| `02_kalender.py` | Block 2: Kalender-Detektive |
| `03_preise.py` | Block 3: Preisfalle und Umsatzkurve |
| `04_spiegelmining.py` | Block 4: SpiegelMining im Hotel (Vertiefung) |
| `05_dsgvo.py` | Block 5: Darf man das? |
| `checks/NN_*.py` | Prüf-Funktionen. Der Generator fügt alle Dateien in Namensreihenfolge zu **einer** Code-Zelle zusammen. Diese Zelle steht an der Stelle von `# %% [checks]` in `00_setup.py`. |

## Zellformat (wie jupytext „percent“)

```python
# %% [markdown]
# ## Block 1: Wer sind unsere Gäste?
#
# Text in **Markdown**. Jede Zeile beginnt mit "# " oder ist genau "#".

# %%
code = "eine Code-Zelle"
```

- `# %% [markdown]` beginnt eine Markdown-Zelle. Der Generator entfernt pro Zeile das führende `# ` bzw. `#`.
- `# %%` beginnt eine Code-Zelle. Leere Zeilen am Anfang und Ende einer Zelle werden entfernt.
- `# %% [checks]` (nur in `00_setup.py`) ist der Platzhalter für die Prüf-Zelle.
- `# %% [setup]` wie `# %%`, aber die Zelle wird in Colab eingeklappt. Die erste Zeile muss `# @title …` sein.

## Lösung und Lücke in einer Code-Zelle

```python
# %%
# TODO: Legt die Regel fest. Geschäftsreisende buchen kurzfristig.
### LÖSUNG
stays["segment"] = np.where(stays["lead_days"] <= 21, "business", "leisure")
### LÜCKE
stays["segment"] = np.where(stays["lead_days"] <= ___, "business", "leisure")
### ENDE
stays["segment"].value_counts()
```

- Lösungs-Notebook: Zeilen zwischen `### LÖSUNG` und `### LÜCKE` bleiben, der Lücken-Teil fällt weg.
- Studierenden-Notebook: umgekehrt.
- Zeilen außerhalb der Marker erscheinen in beiden Notebooks. Die Marker-Zeilen selbst verschwinden.
- Eine Zelle darf mehrere LÖSUNG/LÜCKE/ENDE-Gruppen haben.
- Lücken heißen immer `___` (drei Unterstriche). Pro Zelle 1–2 Lücken, höchstens 3.
- Für Markdown-Zellen, die nur in der Lösung stehen sollen (z. B. „Erkenntnis“): erste Zeile `# %% [markdown] [loesung]`. Im Studierenden-Notebook fällt die Zelle weg.

## Didaktik-Regeln (für alle Blöcke)

1. Sprache Markdown: Deutsch, Anrede **„ihr“**. Code-Bezeichner: Englisch. Kommentare im Code: Deutsch.
2. Jede Aufgabe beginnt mit einer Überschrift im festen Format (der Generator summiert die Zeiten):
   `### Aufgabe 1.2: Titel · ⏱ ca. 10 Min.`
   Großzügig schätzen, für Einsteiger*innen, die pandas zum ersten Mal sehen: Lesen, Ausprobieren und Nachdenken zählen mit. Ein Block beginnt mit `## Block N: Titel` (`## Block 1b: …` erlaubt).
3. Aufbau jeder Aufgabe:
   1. Markdown: Was ist die Frage und warum interessiert sie das Hotel?
   2. **Mini-Beispiel**: Die neue pandas- oder SQL-Funktion an einem winzigen Spielzeug-DataFrame (3–5 Zeilen), als eigene ausführbare Code-Zelle ohne Lücke. So muss niemand im Internet suchen.
   3. Code-Zelle mit Gerüst, `# TODO:`-Kommentar und Lücke(n) `___`.
   4. Check-Zelle, z. B. `check_segment(stays)`.
   5. Optional: Frage zum Nachdenken (Markdown, beginnt mit „🤔“). In der Lösung folgt eine `[loesung]`-Markdown-Zelle mit der Erkenntnis.
4. Reine Plot- oder Lesezellen ohne Lücke sind erlaubt und erwünscht. Viel Code ist schon da, nur die Kernidee wird ergänzt.
5. Code, den spätere Blöcke brauchen, ist **immer vollständig vorgegeben** (keine Lücke). Einzige Ausnahme ist `stays["segment"]` (siehe unten).
6. Verboten in allen Texten: Bezüge auf KI-Assistenten, Prompts, Agenten, Online-Kursanbieter, „Mission“, Lehrkräfte-Interna. Keine Zugangsdaten, keine Hostnamen.
7. Keine weiteren Pakete als: `pandas`, `numpy`, `matplotlib`, `sqlalchemy`, `psycopg2`, `pyarrow` sowie die Standardbibliothek. Plots mit `DataFrame.plot` oder `plt`, jede Zelle mit höchstens einem Plot. Ein Plot bekommt immer einen Titel.

## Prüf-Funktionen (`checks/*.py`)

- Reiner Python-Code, eine Datei pro Block (`checks/01_gaeste.py` usw.). Grundfunktionen stehen in `checks/00_base.py`:
  - `ok(message)` gibt „✅ message“ aus.
  - `hint(message)` gibt „💡 message“ aus.
  - `has_columns(df, names, df_name)` gibt `True`/`False` zurück und meldet fehlende Spalten per `hint`.
- Prüf-Funktionen heißen `check_<thema>(…)`, nehmen die zu prüfenden Objekte als Parameter, **werfen keine Exceptions** und geben genau eine ✅-Zeile oder konkrete 💡-Tipps aus.
- Sie prüfen Eigenschaften mit Toleranz (Spalte vorhanden, Werte in erlaubter Menge, Anteil im Bereich, Maximum im Bereich). Sie verraten keine Lösungszeile.
- `___` ist in der Setup-Zelle ein Platzhalter-Objekt (`OpenGap`). Jede Benutzung wirft `LueckeOffen` mit deutscher Meldung. Grund: In Jupyter ist `___` sonst die drittletzte Ausgabe, und eine offene Lücke würde still weiterrechnen. Auf eine offene Lücke reagiert der Check gar nicht, weil die Zelle davor schon scheitert.

## Daten: was nach dem Setup und nach Block 1 existiert

### Setup-Zelle (`00_setup.py`) stellt bereit
- Importe: `pd`, `np`, `plt`, `Path`, `text` (aus sqlalchemy)
- `engine`: SQLAlchemy-Engine (psycopg2) auf die Rolle `hotel_analyst`. Lesen ist nur im Schema `analytics` erlaubt, Timeout 60 s.
- `load_tables(refresh=False) -> dict[str, pd.DataFrame]` mit den Schlüsseln `cities, hotels, room_categories, guests, reservations, daily_rates, calendar_events`.

### Tabellen im Schema `analytics` (gleiche Namen wie die DataFrames)
Spalten, nachdem `load_tables` sie umgewandelt hat:

| Tabelle | Spalten |
|---|---|
| `cities` | `id` int64, `name`, `country` |
| `hotels` | `id`, `city_id`, `name`, `address`, `stars`, `created_at`, `city_type`, `bundesland` |
| `room_categories` | `id`, `hotel_id`, `name`, `base_price` float, `max_guests` |
| `guests` | `id`, `first_name`, `last_name`, `created_at`, `home_state`, `company` (keine E-Mail) |
| `reservations` | `id`, `guest_id`, `category_id`, `checkin`, `checkout`, `status` ('confirmed'/'cancelled'), `created_at`, `rate_per_night` float, `adults`, `children`, `channel` ('direct'/'corporate'/'ota'), `commission_pct` float, `cancelled_at` |
| `daily_rates` | `category_id`, `arrival_date`, `offered_rate` float, `price_source` ('dynamic'/'test'), `closed_to_arrival` bool |
| `calendar_events` | `event_date`, `city_id` (pandas `Int64`, `<NA>` = bundesweit), `event_type` ('holiday','carnival','tournament','festival','trade_fair'), `name` |

Konventionen für die DataFrames:
- Alle Datums- und Zeitspalten sind `datetime64[ns]` **ohne** Zeitzone (UTC).
- Nur die 10 Hotels mit Mustern (`city_type` gesetzt).
- Zeitraum der Anreisen: 2023 bis 2028; vollständige Jahre 2023, 2024, 2025.
- Event-Namen u. a.: 'Ostermontag' (bundesweit), 'Oktoberfest', 'Hannover Messe', 'Frankfurter Buchmesse', 'gamescom', 'Karneval', 'Euro 2024'.

### Block 1 (`01_gaeste.py`) erzeugt – vollständig vorgegeben
- `cities, hotels, categories, guests, reservations, daily_rates, events`. Dabei ist `categories = tables["room_categories"]` und `events = tables["calendar_events"]`.
- `places`: eine Zeile je Kategorie mit `category_id, hotel_id, category, base_price, max_guests, city_id, city_type, bundesland, city`
- `stays`: bestätigte Reservierungen, gemergt mit `places`, plus `nights`, `persons`, `lead_days`, `weekday` (0 = Mo), `month`, `year`, `lead_bucket` (Kategorien "0-14","15-29","30-60","61-120","über 120")
- **Aufgabe mit Lücke:** `stays["segment"]` mit den Werten `"business"`/`"leisure"`. Lösung: Vorlauf ≤ 21 Tage → business.
  - Blöcke, die `segment` brauchen, prüfen zuerst mit `if "segment" not in stays.columns:` und geben dann einen Tipp aus, statt abzustürzen.

Alle anderen Blöcke legen eigene Variablen an und verändern `stays` **nicht**, außer durch neue Spalten. Sie benutzen keine Variablen aus anderen Blöcken außer den oben genannten.

## Bekannte Erkenntnisse (aus der bisherigen Lösung, für Check-Toleranzen)

- Vorlauf: zwei Gipfel. Business ist kurzfristig (Anreise Mo–Mi, kurz, wenige Personen), Leisure langfristig (Do/Fr, länger, mehr Personen).
- Osterfalle: Ostern 2024 lag im März (Ostermontag 1.4.2024). März plus April zusammen zeigen kein echtes Wachstum.
- Event-Study: Anreisen steigen rund um Messen und Feste deutlich.
- Euro 2024: Austragungsorte steigen im Juni/Juli 2024 relativ zu 2023 stärker als die Vergleichsgruppe.
- Preisfalle: Auf `price_source == 'dynamic'` steigen die Verkäufe mit dem Preis (Scheinkorrelation durch Events/Saison). An `closed_to_arrival`-Tagen sind die Verkäufe gedeckelt. Faire Kurve nur auf `price_source == 'test'`. Umsatz-Optimum `r` ≈ 0,9. Segmente: Leisure ≈ 0,9, Business ≈ 1,3 (gemessen 2026-11-24). Provision: direct 0 %, corporate 5 %, ota 18 %.
- SpiegelMining: Paare am selben Tag im selben Hotel. Oben stehen Berater (immer dasselbe Hotel), also Filter `hotels >= 4`. Danach Anti-Join gegen Messetage (`event_type == 'trade_fair'`). Dann bleiben ein „Kartell“ (4 Personen aus 4 Firmen, 6 Paare) und ein „diskretes Duo“ (18 gemeinsame Aufenthalte). Mit `pd.Timedelta(days=1)` findet man den „Schatten“ (B reist 15-mal einen Tag nach A an).
