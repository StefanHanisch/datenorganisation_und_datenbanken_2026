# Grundfunktionen für alle Prüf-Funktionen.
# Prüf-Funktionen werfen nie Exceptions: Sie geben genau eine ✅-Zeile
# oder konkrete 💡-Tipps aus.
import numpy as np  # noqa: F401
import pandas as pd


def ok(message):
    """Meldet, dass alles passt."""
    print(f"✅ {message}")


def hint(message):
    """Gibt einen Tipp aus."""
    print(f"💡 {message}")


def has_columns(df, names, df_name):
    """True, wenn df alle Spalten aus names hat, sonst Tipp und False."""
    if not isinstance(df, pd.DataFrame):
        hint(f"`{df_name}` ist kein DataFrame, sondern {type(df).__name__}.")
        return False
    missing = [name for name in names if name not in df.columns]
    if missing:
        hint(f"In `{df_name}` fehlen die Spalten: {', '.join(missing)}")
        return False
    return True


def check_tables(tables):
    """Prüft das Ergebnis von load_tables()."""
    expected = ["cities", "hotels", "room_categories", "guests",
                "reservations", "daily_rates", "calendar_events"]
    try:
        if not isinstance(tables, dict):
            hint("`tables` sollte ein dict sein. Nutzt `tables = load_tables()`.")
            return
        missing = [name for name in expected if name not in tables]
        if missing:
            hint(f"In `tables` fehlen: {', '.join(missing)}. Nutzt `tables = load_tables()`.")
            return
        empty = [name for name in expected
                 if not isinstance(tables[name], pd.DataFrame) or tables[name].empty]
        if empty:
            hint(f"Leer oder kein DataFrame: {', '.join(empty)}. "
                 "Versucht `tables = load_tables(refresh=True)`.")
            return
        reservations = tables["reservations"]
        if not has_columns(reservations, ["checkin"], "reservations"):
            return
        if not pd.api.types.is_datetime64_any_dtype(reservations["checkin"]):
            hint("`reservations['checkin']` ist kein Datum. "
                 "Versucht `tables = load_tables(refresh=True)`.")
            return
        rows = f"{len(reservations):,}".replace(",", ".")
        ok(f"Alle {len(expected)} Tabellen geladen, darunter {rows} Reservierungen.")
    except Exception as error:
        hint(f"Prüfung nicht möglich: {error}")
