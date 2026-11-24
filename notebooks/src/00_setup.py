# %% [markdown]
# # Hotel-Analytics mit pandas
#
# {{COLAB_BADGE}}
#
# Unsere Hoteldatenbank ist voll: Städte, Hotels, Zimmerkategorien, Gäste, Reservierungen, Tagespreise und ein Kalender mit Feiertagen und Events. In diesem Notebook schaut ihr mit **pandas** hinein. Wenige Zeilen Code, viele Plots, keine Statistikformeln.
#
# **Wichtig:** Die Termine der Events und Feiertage sind echt. Ihre Effekte auf Preise und Buchungen sind dagegen synthetisch erzeugt. Alle Personen, Firmen und Buchungen sind frei erfunden.
#
# {{ZEITTABELLE}}
#
# Die Zeiten sind großzügig geschätzt. Lasst euch Zeit, lest in Ruhe und probiert aus. Block 4 ist eine Vertiefung für alle, die noch Lust haben.

# %% [markdown]
# ## So funktioniert dieses Notebook
#
# - Führt die Zellen **von oben nach unten** aus: Zelle anklicken und **Shift+Enter** drücken.
# - Vor jeder Aufgabe steht ein **Mini-Beispiel** mit einem winzigen DataFrame. Probiert es aus und verändert es ruhig. So seht ihr, was eine Funktion macht, bevor ihr sie auf die echten Daten loslasst.
# - In den Aufgaben-Zellen ersetzt ihr jedes `___` (drei Unterstriche) durch euren Code. Der Kommentar `# TODO:` sagt euch, was gesucht ist.
# - Danach folgt eine **Check-Zelle**. Sie meldet ✅, wenn alles passt, oder gibt euch mit 💡 einen Tipp.
# - `LueckeOffen: In dieser Zelle steht noch eine Lücke ___` heißt: Hier fehlt noch eure Lösung. Bei Lücken an manchen Stellen meldet pandas stattdessen einen eigenen Fehler, in dem `___` oder `OpenGap` vorkommt. Auch das heißt: Lücke noch offen.
# - `NameError: name '…' is not defined` in einer Check- oder Plot-Zelle heißt meist: Die Aufgabe darüber ist noch nicht gelöst.
# - Wenn alles durcheinander ist: Menü **Laufzeit/Kernel → Neu starten** und dann alle Zellen von oben ausführen. Die Daten kommen dann aus dem Cache, das geht schnell.

# %% [markdown]
# ## So startet ihr
#
# Ihr braucht die **Datenbank-URL** von eurer Lehrperson. Sie beginnt mit `postgresql://` und enthält ein Passwort. Schreibt sie nie in das Notebook und committet sie nie.
#
# ### Weg A: Google Colab (nichts installieren)
#
# 1. Klickt oben auf den Button **In Colab öffnen**.
# 2. Gebt die URL auf **einem** dieser Wege an:
#    - **Secrets:** Links auf das Schlüsselsymbol klicken, ein Secret mit dem Namen `AZURE_ANALYST_DATABASE_URL` anlegen, die URL als Wert eintragen und den Notebook-Zugriff erlauben.
#    - **.env-Datei:** Links auf das Ordnersymbol klicken und eine Datei `.env` hochladen, die die Zeile `AZURE_ANALYST_DATABASE_URL=postgresql://…` enthält.
#    - **Eingabe:** Einfach die Setup-Zelle ausführen. Wenn nichts gefunden wird, fragt sie nach der URL. Die Eingabe bleibt verdeckt.
# 3. Führt die Setup-Zelle unten aus.
#
# ### Weg B: lokal in VS Code
#
# 1. Python 3.11 oder neuer installieren.
# 2. Im Projektordner einmal ausführen: `pip install -e ".[analytics]"`
# 3. Im Projektordner eine Datei `.env` mit der Zeile `AZURE_ANALYST_DATABASE_URL=postgresql://…` anlegen. Die Datei ist von Git ausgeschlossen.
# 4. Das Notebook öffnen, oben rechts den Python-Kernel wählen und die Setup-Zelle ausführen.

# %% [markdown]
# ## Spickzettel
#
# | Befehl | wofür | Beispiel |
# |---|---|---|
# | `df.head()` | die ersten Zeilen ansehen | `reservations.head(3)` |
# | `df["spalte"]` | eine Spalte auswählen | `reservations["status"]` |
# | `df.query("x > 3")` | Zeilen filtern | `stays.query("nights > 3")` |
# | `df.merge(other, on=...)` | zwei Tabellen verbinden (Join) | `stays.merge(guests, left_on="guest_id", right_on="id")` |
# | `df.groupby("a")["b"].mean()` | Gruppen bilden und zusammenfassen | `stays.groupby("city")["nights"].mean()` |
# | `df.pivot_table(index=, columns=, values=, aggfunc=)` | Kreuztabelle | `stays.pivot_table(index="month", columns="year", values="id", aggfunc="count")` |
# | `np.where(bed, a, b)` | Wert je nach Bedingung | `np.where(stays["nights"] > 3, "lang", "kurz")` |
# | `pd.cut(werte, bins=..., labels=...)` | Zahlen in Klassen einteilen | `pd.cut(stays["nights"], bins=[0, 2, 7, 30])` |
# | `.dt.year`, `.dt.day_of_week` | Teile eines Datums (0 = Montag) | `stays["checkin"].dt.year` |
# | `.plot(...)`, `.plot.bar()`, `.plot.hist()` | Linie, Balken, Histogramm | `stays["nights"].plot.hist(title="Nächte")` |
# | `pd.read_sql(text(...), engine)` | SQL an die Datenbank schicken | `pd.read_sql(text("SELECT * FROM analytics.cities"), engine)` |
#
# ### SQL ↔ pandas
#
# | SQL | pandas |
# |---|---|
# | `SELECT name, stars FROM hotels` | `hotels[["name", "stars"]]` |
# | `WHERE stars >= 4` | `hotels.query("stars >= 4")` |
# | `JOIN cities ON hotels.city_id = cities.id` | `hotels.merge(cities, left_on="city_id", right_on="id")` |
# | `GROUP BY city_id` mit `AVG(stars)` | `hotels.groupby("city_id")["stars"].mean()` |
# | `ORDER BY stars DESC` | `hotels.sort_values("stars", ascending=False)` |

# %% [setup]
# @title Setup – einfach ausführen (lädt Pakete und verbindet mit der Datenbank)
import getpass
import os
import re
import subprocess
import sys
import time
import urllib.parse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError, ProgrammingError

try:
    import psycopg2  # noqa: F401  (Datenbank-Treiber für SQLAlchemy)
except ImportError:
    print("Installiere den Datenbank-Treiber psycopg2-binary …")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "psycopg2-binary"])
    import psycopg2  # noqa: F401

plt.rcParams["figure.figsize"] = (9, 4)
pd.set_option("display.max_columns", 30)

ENV_NAME = "AZURE_ANALYST_DATABASE_URL"


def find_project_root():
    """Sucht von hier aus nach oben den Ordner mit pyproject.toml (sonst None)."""
    for folder in [Path.cwd(), *Path.cwd().parents]:
        if (folder / "pyproject.toml").exists():
            return folder
    return None


def read_env_file(path):
    """Liest KEY=VALUE-Zeilen aus einer .env-Datei in ein dict."""
    values = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export "):].strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip()
        # Optionale Anführungszeichen entfernen: KEY="wert" oder KEY='wert'
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        values[key] = value
    return values


def env_file_candidates(project_root):
    """Mögliche .env-Dateien: aktueller Ordner, Eltern bis zum Projektordner, Colab."""
    folders = [Path.cwd()]
    if project_root is not None:
        for folder in Path.cwd().parents:
            if project_root == folder or project_root in folder.parents:
                folders.append(folder)
    folders.append(Path("/content"))  # Ordner für Uploads in Colab
    return [folder / ".env" for folder in folders]


def read_colab_secret():
    """Liest das Colab-Secret, falls wir in Colab sind und der Zugriff erlaubt ist."""
    try:
        from google.colab import userdata
    except ImportError:
        return None
    try:
        return userdata.get(ENV_NAME)
    except Exception:
        print(f"💡 Colab-Secret {ENV_NAME} nicht gefunden oder Notebook-Zugriff nicht erlaubt.")
        return None


def get_db_url():
    """Findet die Datenbank-URL und gibt sie zurück, ohne sie anzuzeigen."""
    url, source = os.environ.get(ENV_NAME), "Umgebungsvariable"
    if not url:
        for env_file in env_file_candidates(find_project_root()):
            if env_file.is_file():
                url = read_env_file(env_file).get(ENV_NAME)
                if url:
                    source = f".env-Datei ({env_file})"
                    break
    if not url:
        url, source = read_colab_secret(), "Colab-Secret"
    if not url:
        url = getpass.getpass("Datenbank-URL (von der Lehrperson): ")
        source = "Eingabe"

    url = (url or "").strip()
    if not url.startswith("postgresql://"):
        raise ValueError(
            f"Die Datenbank-URL aus der Quelle '{source}' beginnt nicht mit 'postgresql://'. "
            "Prüft, ob ihr die vollständige URL von der Lehrperson kopiert habt."
        )
    if re.search(r"<[^<>]+>", url):
        raise ValueError(
            f"Die Datenbank-URL aus der Quelle '{source}' enthält noch einen Platzhalter wie <PASSWORT>. "
            "Ersetzt ihn durch den echten Wert."
        )
    try:
        parts = urllib.parse.urlsplit(url)
        target = f"{parts.hostname} / {parts.path.lstrip('/')}"
    except ValueError:
        target = "(Adresse nicht lesbar)"
    print(f"Zugangsdaten aus: {source}")
    print(f"Ziel: {target}")
    return url


def connect(url):
    """Erstellt die Engine und testet die Verbindung mit SELECT current_user."""
    engine = create_engine(
        url.replace("postgresql://", "postgresql+psycopg2://", 1),
        pool_pre_ping=True,
        connect_args={"connect_timeout": 15},
    )
    try:
        with engine.connect() as connection:
            user = connection.execute(text("SELECT current_user")).scalar()
    except OperationalError as error:
        details = str(error.orig).strip().splitlines()[0] if error.orig else ""
        if "password" in details.lower():
            reason = "Benutzername oder Passwort stimmen nicht. Prüft die URL."
        else:
            reason = (
                "Die Datenbank ist nicht erreichbar. Prüft eure Internetverbindung. "
                "Manche WLANs sperren den Port 5432, dann hilft z. B. ein Handy-Hotspot."
            )
        raise ConnectionError(f"❌ Keine Verbindung zur Datenbank. {reason}\nDetails: {details}") from None
    print(f"✅ Verbunden als {user}")
    return engine


TABLES = ["cities", "hotels", "room_categories", "guests", "reservations", "daily_rates", "calendar_events"]
DATE_COLUMNS = ["checkin", "checkout", "arrival_date", "event_date", "created_at", "cancelled_at"]
FLOAT_COLUMNS = ["base_price", "rate_per_night", "commission_pct", "offered_rate"]

PROJECT_ROOT = find_project_root()
CACHE_DIR = (PROJECT_ROOT / "data" / "cache") if PROJECT_ROOT else Path("hotel_cache")


def tidy_types(name, df):
    """Einheitliche Typen: Datum ohne Zeitzone, Preise als float, city_id als Int64."""
    for column in DATE_COLUMNS:
        if column in df.columns:
            values = pd.to_datetime(df[column], utc=True).dt.tz_localize(None)
            df[column] = values.astype("datetime64[ns]")
    for column in FLOAT_COLUMNS:
        if column in df.columns:
            df[column] = pd.to_numeric(df[column]).astype(float)
    if name == "calendar_events":
        df["city_id"] = df["city_id"].astype("Int64")  # <NA> = bundesweit
    return df


def load_tables(refresh=False):
    """Lädt alle Tabellen aus dem Cache oder (beim ersten Mal) aus der Datenbank."""
    tables = {}
    start = time.time()
    for name in TABLES:
        table_start = time.time()
        cache_file = CACHE_DIR / f"{name}.parquet"
        if cache_file.exists() and not refresh:
            df = pd.read_parquet(cache_file)
            source = "Cache"
        else:
            try:
                df = pd.read_sql(text(f"SELECT * FROM analytics.{name}"), engine)
            except ProgrammingError:
                raise RuntimeError(
                    f"❌ Tabelle analytics.{name} nicht gefunden oder kein Leserecht. "
                    "Ist das Schema analytics eingerichtet? Fragt eure Lehrperson."
                ) from None
            df = tidy_types(name, df)
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            df.to_parquet(cache_file, index=False)
            source = "DB"
        tables[name] = tidy_types(name, df)
        rows = f"{len(df):,}".replace(",", ".")
        print(f"  {name:<16} {rows:>10} Zeilen  {time.time() - table_start:5.1f} s  ({source})")
    print(f"Fertig in {time.time() - start:.1f} s")
    return tables


class LueckeOffen(Exception):
    """Wird ausgelöst, sobald eine Zelle eine noch offene Lücke benutzt."""


class OpenGap:
    """Platzhalter für Lücken in den Aufgaben.

    Jupyter nutzt den Namen der Lücke sonst selbst (für die drittletzte Ausgabe).
    Dann würde eine offene Lücke still mit einem falschen Wert weiterrechnen.
    Dieser Platzhalter meldet stattdessen sofort, dass noch etwas fehlt.
    """

    MESSAGE = ("In dieser Zelle steht noch eine Lücke " + "_" * 3 + ". "
               "Ersetzt sie durch eure Lösung und führt die Zelle erneut aus.")

    def _stop(self, *args, **kwargs):
        raise LueckeOffen(self.MESSAGE)

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)
        self._stop()

    def __repr__(self):
        return "<Lücke: hier fehlt noch eure Lösung>"


for _name in ["__eq__", "__ne__", "__lt__", "__le__", "__gt__", "__ge__", "__hash__", "__bool__",
              "__len__", "__iter__", "__contains__", "__getitem__", "__call__", "__index__", "__int__",
              "__float__", "__add__", "__radd__", "__sub__", "__rsub__", "__mul__", "__rmul__",
              "__truediv__", "__rtruediv__", "__floordiv__", "__rfloordiv__", "__neg__", "__array__"]:
    setattr(OpenGap, _name, OpenGap._stop)

globals()["_" * 3] = OpenGap()  # die Lücke aus den Aufgaben

engine = connect(get_db_url())
print(f"Cache-Ordner: {CACHE_DIR}")
print("✅ Setup fertig")

# %% [checks]
