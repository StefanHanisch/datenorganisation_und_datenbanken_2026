# Prüf-Funktionen für Block 1b: SQL und pandas
# Nutzt ok, hint und has_columns aus checks/00_base.py.


def check_same_total(sql_df, pandas_df):
    """Aufgabe 1b.2: SQL- und pandas-Ergebnis zählen dieselben Buchungen."""
    try:
        if not has_columns(sql_df, ["category", "bookings"], "sql_df"):
            hint("Führt die SQL-Zelle aus Aufgabe 1b.1 noch einmal aus.")
            return
        if not has_columns(pandas_df, ["category", "bookings"], "pandas_df"):
            hint("Gruppiert nach der Spalte mit dem Kategorienamen, dann heißt die Spalte `category`.")
            return
        if len(pandas_df) != len(sql_df):
            hint(f"SQL liefert {len(sql_df)} Kategorien, pandas {len(pandas_df)}. "
                 "Gruppiert ihr nach derselben Spalte wie das GROUP BY im SQL?")
            return
        if set(pandas_df["category"]) != set(sql_df["category"]):
            hint("In `pandas_df` stehen andere Gruppen als in `sql_df`. "
                 "Gruppiert nach dem Namen der Zimmerkategorie.")
            return
        sql_total = int(pd.to_numeric(sql_df["bookings"]).sum())
        pandas_total = int(pd.to_numeric(pandas_df["bookings"]).sum())
        if sql_total != pandas_total:
            hint(f"SQL zählt {sql_total} Buchungen, pandas {pandas_total}. "
                 "Wurde die Datenbank seit dem Laden neu befüllt? Dann hilft `tables = load_tables(refresh=True)` "
                 "und Block 1 noch einmal ausführen.")
            return
        ok(f"SQL und pandas kommen auf dieselben {sql_total} Buchungen in {len(sql_df)} Kategorien.")
    except Exception as error:
        hint(f"Prüfung nicht möglich: {error}")


def check_channel_rates(channel_rates):
    """Aufgabe 1b.3: Durchschnittspreis je Vertriebskanal 2024."""
    try:
        if not has_columns(channel_rates, ["channel", "avg_rate", "bookings"], "channel_rates"):
            hint("Die Spaltennamen kommen aus dem SQL: `channel`, `... AS avg_rate`, `... AS bookings`.")
            return
        channels = set(channel_rates["channel"])
        if len(channel_rates) != 3 or channels != {"direct", "corporate", "ota"}:
            hint(f"Erwartet ist genau eine Zeile je Kanal (direct, corporate, ota), gefunden: {len(channel_rates)} Zeilen. "
                 "Wonach muss gruppiert werden, damit jeder Kanal einmal vorkommt?")
            return
        rates = pd.to_numeric(channel_rates["avg_rate"], errors="coerce")
        bookings = pd.to_numeric(channel_rates["bookings"], errors="coerce")
        if rates.isna().any() or (rates <= 0).any():
            hint("`avg_rate` sollte für jeden Kanal ein positiver Preis sein.")
            return
        if bookings.isna().any() or (bookings <= 0).any():
            hint("`bookings` sollte für jeden Kanal eine positive Anzahl sein.")
            return
        if not rates.is_monotonic_decreasing:
            hint("Die Kanäle sind nicht absteigend nach `avg_rate` sortiert. Lasst das ORDER BY stehen.")
            return
        top = channel_rates["channel"].iloc[0]
        ok(f"Drei Kanäle ausgewertet, den höchsten Durchschnittspreis 2024 hat '{top}'.")
    except Exception as error:
        hint(f"Prüfung nicht möglich: {error}")
