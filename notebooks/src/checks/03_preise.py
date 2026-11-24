# Prüf-Funktionen für Block 3: Preisfalle und Umsatzkurve
# Grundfunktionen ok, hint, has_columns kommen aus checks/00_base.py.
import numpy as np
import pandas as pd


def _is_number(value):
    """True für int/float (auch numpy), aber nicht für bool."""
    return pd.api.types.is_number(value) and not isinstance(value, (bool, np.bool_))


def check_daily(daily, daily_rates):
    """Aufgabe 3.1: daily hat je Kategorie und Anreisetag genau eine Zeile, auch ohne Verkauf."""
    try:
        if not isinstance(daily, pd.DataFrame):
            hint("daily sollte ein DataFrame sein.")
            return
        if not has_columns(daily, ["bookings", "r"], "daily"):
            return
        if len(daily) < len(daily_rates):
            hint(f"daily hat {len(daily):,} Zeilen, daily_rates aber {len(daily_rates):,}. "
                 "Es fehlen Tage ohne Verkauf. Welches how behält alle Zeilen der linken Tabelle?")
            return
        if len(daily) > len(daily_rates):
            hint(f"daily hat mehr Zeilen ({len(daily):,}) als daily_rates ({len(daily_rates):,}). "
                 "Habt ihr die Zelle mehrfach ausgeführt? Startet ab dem ersten Merge neu.")
            return
        if daily["bookings"].isna().any():
            hint("In bookings gibt es noch leere Werte (NaN). Ersetzt sie mit fillna.")
            return
        if not (daily["bookings"] == 0).any():
            hint("Es gibt keinen Tag mit 0 Buchungen. Welche Zahl gehört zu einem Tag ohne Verkauf?")
            return
        if daily["r"].isna().any() or not daily["r"].between(0.1, 5).all():
            hint("Einige Werte von r sehen seltsam aus. r ist offered_rate geteilt durch base_price.")
            return
        ok(f"daily ist fertig: {len(daily):,} Tage, davon {(daily['bookings'] == 0).mean():.0%} ohne Verkauf.")
    except Exception as error:
        hint(f"Die Prüfung konnte nicht laufen: {error}")


def check_day_type(regular):
    """Aufgabe 3.3: Tagesart Event > Sommer > Alltag, passend zu is_event und Monat."""
    try:
        if not isinstance(regular, pd.DataFrame):
            hint("regular sollte ein DataFrame sein.")
            return
        if not has_columns(regular, ["arrival_date", "is_event", "day_type"], "regular"):
            return
        if regular["is_event"].dtype != bool:
            hint("is_event sollte nur True/False enthalten. Habt ihr .notna() ausgeführt?")
            return
        allowed = {"Event", "Sommer", "Alltag"}
        found = set(regular["day_type"].dropna().unique())
        if found - allowed:
            hint(f"Unerwartete Werte in day_type: {sorted(found - allowed)}. "
                 "Erlaubt sind genau 'Event', 'Sommer' und 'Alltag'.")
            return
        missing = allowed - found
        if missing:
            hint(f"Diese Tagesarten kommen gar nicht vor: {sorted(missing)}. Prüft eure Bedingungen.")
            return
        day_type = regular["day_type"]
        month = regular["arrival_date"].dt.month
        summer_month = month.isin([6, 7, 8])
        if (regular["is_event"] & (day_type != "Event")).any():
            hint("Einige Event-Tage sind nicht als 'Event' markiert. "
                 "Die Event-Bedingung gehört ins äußere np.where.")
            return
        if ((day_type == "Event") & ~regular["is_event"]).any():
            hint("Einige Tage ohne Event sind als 'Event' markiert. Prüft die äußere Bedingung.")
            return
        if ((day_type == "Sommer") & ~summer_month).any():
            hint("Einige 'Sommer'-Tage liegen nicht im Sommer. Sommer sind die Monate Juni bis August.")
            return
        if ((day_type == "Alltag") & summer_month).any():
            hint("Einige Sommertage sind als 'Alltag' markiert. Prüft die Monatsliste und die innere Bedingung.")
            return
        ok("Jeder Tag hat die richtige Tagesart: Event, Sommer oder Alltag.")
    except Exception as error:
        hint(f"Die Prüfung konnte nicht laufen: {error}")


def check_closed_share(share_closed):
    """Aufgabe 3.4: Anteil der geschlossenen Tage als Zahl zwischen 0 und 1."""
    try:
        if not _is_number(share_closed):
            hint("share_closed sollte eine einzelne Zahl sein, kein DataFrame und keine Series.")
            return
        if share_closed > 1:
            hint("Der Wert ist größer als 1. Das ist eine Anzahl, kein Anteil. "
                 "Welche Funktion liefert bei True/False den Anteil?")
            return
        if share_closed <= 0:
            hint("Der Anteil ist 0 oder kleiner. Habt ihr die Spalte closed_to_arrival von daily benutzt?")
            return
        ok(f"An {share_closed:.1%} der Tage war keine Anreise mehr möglich.")
    except Exception as error:
        hint(f"Die Prüfung konnte nicht laufen: {error}")


def check_test_days(test):
    """Aufgabe 3.5: test enthält nur Tage mit zufälligem Preistest."""
    try:
        if not isinstance(test, pd.DataFrame):
            hint("test sollte ein DataFrame sein.")
            return
        if not has_columns(test, ["price_source", "r", "bookings"], "test"):
            return
        if len(test) == 0:
            hint("test ist leer. Steht der Wert im query-Text in einfachen Anführungszeichen "
                 "und genau so geschrieben wie in price_source?")
            return
        sources = set(test["price_source"].unique())
        if sources != {"test"}:
            hint(f"In test stecken noch diese Preisquellen: {sorted(sources)}. "
                 "Behaltet nur die Tage mit zufälligem Preistest.")
            return
        ok(f"test enthält nur Preistest-Tage ({len(test):,} Zeilen).")
    except Exception as error:
        hint(f"Die Prüfung konnte nicht laufen: {error}")


def check_revenue_peak(best_r):
    """Aufgabe 3.6: Gipfel des Umsatzbergs liegt in einem plausiblen Bereich."""
    try:
        if not _is_number(best_r):
            hint("best_r sollte eine einzelne Zahl sein, nämlich eine Preisstufe r.")
            return
        if 0.75 <= best_r <= 1.0:
            ok(f"Der Umsatzberg hat seinen Gipfel bei r = {best_r:.2f}.")
            return
        hint(f"best_r = {best_r} passt noch nicht. Habt ihr die Stelle des Maximums (idxmax) "
             "genommen und nicht das Maximum selbst (max)? Und rechnet ihr nur mit den Testtagen?")
    except Exception as error:
        hint(f"Die Prüfung konnte nicht laufen: {error}")


def check_segment_peaks(peaks):
    """Aufgabe 3.7: Leisure hat den Umsatzgipfel bei niedrigerem r als Business."""
    try:
        if not isinstance(peaks, pd.Series):
            hint("peaks sollte eine Series sein: je Gästegruppe eine Preisstufe r.")
            return
        missing = [name for name in ["business", "leisure"] if name not in peaks.index]
        if missing:
            hint(f"In peaks fehlen die Gruppen {missing}. Gehört segment in columns der pivot_table?")
            return
        business = peaks["business"]
        leisure = peaks["leisure"]
        if not (_is_number(business) and _is_number(leisure)):
            hint("Die Werte in peaks sollten Preisstufen r sein. Nehmt idxmax, nicht max.")
            return
        if not (0.5 <= leisure <= 1.6 and 0.5 <= business <= 1.6):
            hint("Die Werte in peaks sehen nicht wie Preisstufen r aus. Nehmt idxmax, nicht max.")
            return
        if leisure < business:
            ok(f"Zwei Gipfel: leisure bei r = {leisure:.2f}, business bei r = {business:.2f}.")
            return
        hint("Bei euch liegen beide Gipfel gleich oder leisure höher als business. "
             "Prüft eure Segmentregel aus Block 1 und ob ihr mit dem Preis r multipliziert habt.")
    except Exception as error:
        hint(f"Die Prüfung konnte nicht laufen: {error}")


def check_net(test_stays):
    """Aufgabe 3.8: gross und net passen zu Preis, Nächten und Provision."""
    try:
        if not isinstance(test_stays, pd.DataFrame):
            hint("test_stays sollte ein DataFrame sein.")
            return
        needed = ["rate_per_night", "nights", "commission_pct", "gross", "net"]
        if not has_columns(test_stays, needed, "test_stays"):
            return
        data = test_stays[needed].dropna()
        data = data[data["gross"] > 0]
        if len(data) == 0:
            hint("In test_stays gibt es keine Zeilen mit Bruttoumsatz.")
            return
        if not np.allclose(data["gross"], data["rate_per_night"] * data["nights"]):
            hint("gross passt nicht zu Preis je Nacht und Zahl der Nächte.")
            return
        kept = data["net"] / data["gross"]
        lost = 1 - kept
        rate = data["commission_pct"] / 100
        if np.allclose(lost, rate, atol=1e-6):
            ok("net stimmt: Dem Hotel bleibt der Bruttoumsatz abzüglich Provision.")
            return
        if (data["net"] > data["gross"] + 1e-6).any():
            hint("net ist teilweise größer als gross. Die Provision wird abgezogen, nicht addiert.")
            return
        if np.allclose(lost, data["commission_pct"], atol=1e-6):
            hint("Die Provision ist in Prozent angegeben. Teilt ihr durch 100?")
            return
        if np.allclose(kept, rate, atol=1e-6):
            hint("net ist gerade die Provision selbst. Gesucht ist, was dem Hotel übrig bleibt.")
            return
        hint("net passt noch nicht. Bei 0 % Provision muss net gleich gross sein, "
             "bei 20 % Provision bleiben 80 % von gross.")
    except Exception as error:
        hint(f"Die Prüfung konnte nicht laufen: {error}")
