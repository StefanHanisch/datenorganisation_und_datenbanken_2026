# Prüf-Funktionen für Block 2: Kalender-Detektive
import pandas as pd


def check_monthly(monthly):
    """Aufgabe 2.1: Monat x Jahr mit Anzahl der Anreisen."""
    try:
        if not isinstance(monthly, pd.DataFrame):
            hint("`monthly` sollte eine Tabelle (DataFrame) sein, so wie `pivot_table` sie liefert.")
            return
        if any(month not in monthly.index for month in range(1, 13)):
            hint("Die Zeilen von `monthly` sollten die Monate 1 bis 12 sein. Prüft `index=`.")
            return
        missing = [year for year in (2023, 2024, 2025) if year not in monthly.columns]
        if missing:
            hint(f"In den Spalten von `monthly` fehlen die Jahre {missing}. Die Spalten sollten Jahre sein.")
            return
        values = monthly.loc[list(range(1, 13)), [2023, 2024, 2025]]
        if values.isna().any().any() or (values <= 0).any().any():
            hint("Für 2023 bis 2025 sollte jeder Monat mehr als 0 Anreisen haben. Zählt ihr mit `aggfunc=\"count\"`?")
            return
        ok("`monthly` hat eine Zeile je Monat und eine Spalte je Jahr.")
    except Exception as error:
        hint(f"`monthly` ließ sich nicht prüfen ({type(error).__name__}). Führt die Zellen davor noch einmal aus.")


def check_event_curve(curve_rel):
    """Aufgabe 2.2: relative Anreisen je Tag rund um den Eventstart."""
    try:
        if not isinstance(curve_rel, pd.DataFrame):
            hint("`curve_rel` sollte eine Tabelle (DataFrame) mit einer Spalte je Event sein.")
            return
        if any(day not in curve_rel.index for day in range(-14, 22)):
            hint("Der Index von `curve_rel` sollte alle Tage von -14 bis 21 enthalten. Prüft die Spalte `offset` und den Filter.")
            return
        if curve_rel.shape[1] < 2:
            hint("`curve_rel` sollte mehrere Events als Spalten haben. Prüft `columns=\"name\"` in der `pivot_table`.")
            return
        before = curve_rel[curve_rel.index.isin(range(-14, 0))].mean().mean()
        if not 0.9 <= before <= 1.1:
            hint("Vor dem Event (Tage -14 bis -1) sollte die Kurve im Mittel bei etwa 1 liegen. "
                 "Habt ihr durch den Normalwert der 14 Tage davor geteilt?")
            return
        peak = curve_rel[curve_rel.index.isin(range(0, 11))].max().max()
        if not peak > 1.2:
            hint("Ab Tag 0 sollte die Kurve deutlich über 1 steigen. Prüft die Richtung von `offset`: "
                 "Anreise minus Eventstart, damit Tag 0 der erste Eventtag ist.")
            return
        ok(f"`curve_rel` deckt die Tage -14 bis 21 ab und enthält {curve_rel.shape[1]} Events.")
    except Exception as error:
        hint(f"`curve_rel` ließ sich nicht prüfen ({type(error).__name__}). Führt die Zellen davor noch einmal aus.")


def check_euro(euro_rel):
    """Aufgabe 2.3: Anreisen Juni/Juli je Gruppe, relativ zu 2023."""
    try:
        if not isinstance(euro_rel, pd.DataFrame):
            hint("`euro_rel` sollte eine Tabelle (DataFrame) mit einer Spalte je Gruppe sein.")
            return
        if not has_columns(euro_rel, ["Austragungsort", "Vergleichsgruppe"], "euro_rel"):
            hint("Beide Gruppen müssen vorkommen. Prüft, ob `isin` die Liste der Austragungsorte bekommt.")
            return
        if 2023 not in euro_rel.index or 2024 not in euro_rel.index:
            hint("Die Zeilen von `euro_rel` sollten die Jahre sein, mindestens 2023 und 2024.")
            return
        base = euro_rel.loc[2023, ["Austragungsort", "Vergleichsgruppe"]]
        if not ((base - 1).abs() < 0.01).all():
            hint("Im Jahr 2023 sollten beide Gruppen genau bei 1 liegen. Habt ihr durch die Zeile 2023 geteilt?")
            return
        ok("`euro_rel` vergleicht beide Gruppen relativ zu 2023.")
    except Exception as error:
        hint(f"`euro_rel` ließ sich nicht prüfen ({type(error).__name__}). Führt die Zellen davor noch einmal aus.")


def check_cancel_rate(cancel_rate):
    """Aufgabe 2.4: Anteil stornierter Reservierungen je Kanal."""
    try:
        if not isinstance(cancel_rate, pd.Series):
            hint("`cancel_rate` sollte eine Series mit einem Wert je Kanal sein.")
            return
        missing = [name for name in ("direct", "corporate", "ota") if name not in cancel_rate.index]
        if missing:
            hint(f"Im Index von `cancel_rate` fehlen die Kanäle {missing}. Gruppiert nach `channel`.")
            return
        if not cancel_rate.between(0, 1).all():
            hint("Eine Quote liegt zwischen 0 und 1. Bildet ihr den Mittelwert einer True/False-Spalte?")
            return
        if (cancel_rate == 0).all() or (cancel_rate == 1).all():
            hint("Alle Quoten sind 0 oder alle sind 1. Welche Werte gibt es in `reservations[\"status\"]`? "
                 "Probiert `reservations[\"status\"].unique()`.")
            return
        ok("`cancel_rate` enthält eine Stornoquote je Kanal.")
    except Exception as error:
        hint(f"`cancel_rate` ließ sich nicht prüfen ({type(error).__name__}). Führt die Zellen davor noch einmal aus.")
