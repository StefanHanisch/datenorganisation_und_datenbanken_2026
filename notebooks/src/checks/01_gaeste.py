# Prüf-Funktionen für Block 1: Wer sind unsere Gäste?
# Nutzt ok, hint und has_columns aus checks/00_base.py (check_tables steht dort).


def _block1_number(value):
    """Ganze Zahl mit deutschem Tausenderpunkt, z. B. 12.345."""
    return f"{int(value):,}".replace(",", ".")


def check_counts(n_reservations, n_columns, reservations):
    """Aufgabe 1.1: Zeilen- und Spaltenzahl von reservations."""
    try:
        if not isinstance(reservations, pd.DataFrame):
            hint("`reservations` ist kein DataFrame. Führt die Zellen oben noch einmal aus.")
            return
        rows, cols = reservations.shape
        if not isinstance(n_reservations, (int, np.integer)):
            hint("`n_reservations` sollte eine ganze Zahl sein. `len(...)` liefert die Anzahl Zeilen eines DataFrames.")
            return
        if n_reservations != rows:
            if n_reservations == cols:
                hint("`n_reservations` ist die Zahl der Spalten. Gesucht ist die Zahl der Zeilen von `reservations`.")
            else:
                hint("`n_reservations` passt nicht zu `reservations`. Gebt `len(...)` die ganze Tabelle `reservations`.")
            return
        if not isinstance(n_columns, (int, np.integer)):
            hint("`n_columns` sollte eine ganze Zahl sein. `shape` ist ein Paar (Zeilen, Spalten), in eckigen Klammern wählt ihr eine Position.")
            return
        if n_columns != cols:
            if n_columns == rows:
                hint("`n_columns` ist die Zahl der Zeilen. Welche Position im Paar `shape` steht für die Spalten? Python zählt ab 0.")
            else:
                hint("`n_columns` passt nicht. Schaut euch das Mini-Beispiel zu `shape` noch einmal an.")
            return
        ok(f"{_block1_number(rows)} Reservierungen mit je {cols} Spalten.")
    except Exception as error:
        hint(f"Prüfung nicht möglich: {error}")


def check_hotel_cities(hotel_cities, hotels):
    """Aufgabe 1.2: hotels mit towns verbunden."""
    try:
        if not has_columns(hotel_cities, ["name", "city", "city_type"], "hotel_cities"):
            hint("Verbindet `hotels` mit `towns`, dann kommt die Spalte `city` dazu.")
            return
        if not isinstance(hotels, pd.DataFrame):
            hint("`hotels` ist kein DataFrame. Führt Aufgabe 1.1 noch einmal aus.")
            return
        if len(hotel_cities) != len(hotels):
            hint(f"`hotel_cities` hat {len(hotel_cities)} Zeilen, es gibt aber {len(hotels)} Hotels. "
                 "Jedes Hotel sollte genau einmal vorkommen. Stimmt die Schlüsselspalte?")
            return
        if hotel_cities["city"].isna().any():
            hint("Bei einigen Hotels fehlt die Stadt. Stimmt die Schlüsselspalte?")
            return
        ok(f"Alle {len(hotel_cities)} Hotels haben ihre Stadt.")
    except Exception as error:
        hint(f"Prüfung nicht möglich: {error}")


def check_stays(stays):
    """Aufgabe 1.3: Arbeitstabelle stays."""
    try:
        needed = ["category_id", "hotel_id", "category", "city", "city_type",
                  "nights", "persons", "lead_days", "weekday", "month", "year"]
        if not has_columns(stays, needed, "stays"):
            hint("Führt die Zellen in Aufgabe 1.2 und 1.3 noch einmal der Reihe nach aus.")
            return
        if len(stays) == 0:
            hint("`stays` ist leer. Führt Aufgabe 1.1 bis 1.3 noch einmal der Reihe nach aus.")
            return
        if "status" in stays.columns and (stays["status"] != "confirmed").any():
            hint("In `stays` stehen noch stornierte Reservierungen. Es sollen nur bestätigte drin sein.")
            return
        if (stays["nights"] < 1).any():
            hint("Es gibt Aufenthalte mit weniger als einer Nacht. Prüft die Rechnung für `nights`.")
            return
        if not stays["weekday"].between(0, 6).all():
            hint("`weekday` sollte zwischen 0 (Montag) und 6 (Sonntag) liegen.")
            return
        ok(f"`stays` enthält {_block1_number(len(stays))} bestätigte Aufenthalte mit allen neuen Spalten.")
    except Exception as error:
        hint(f"Prüfung nicht möglich: {error}")


def check_avg_nights(avg_nights, stays):
    """Aufgabe 1.3: durchschnittliche Nächte."""
    try:
        if not has_columns(stays, ["nights"], "stays"):
            return
        try:
            value = float(avg_nights)
        except (TypeError, ValueError):
            hint("`avg_nights` sollte eine einzelne Zahl sein. Ruft die Methode mit runden Klammern auf: `.methode()`.")
            return
        nights = stays["nights"]
        if abs(value - nights.mean()) < 0.01:
            shown = f"{value:.2f}".replace(".", ",")
            ok(f"Ein Aufenthalt dauert im Durchschnitt {shown} Nächte.")
            return
        if abs(value - nights.median()) < 0.01:
            hint("Das ist der Median (der mittlere Wert). Gesucht ist der Durchschnitt.")
        elif abs(value - nights.sum()) < 0.5:
            hint("Das ist die Summe aller Nächte. Gesucht ist der Durchschnitt.")
        elif abs(value - nights.max()) < 0.01 or abs(value - nights.min()) < 0.01:
            hint("Das ist ein Extremwert (Maximum oder Minimum). Gesucht ist der Durchschnitt.")
        else:
            hint("Der Wert passt nicht zum Durchschnitt von `stays['nights']`. Schaut ins Mini-Beispiel.")
    except Exception as error:
        hint(f"Prüfung nicht möglich: {error}")


def check_bucket_means(bucket_means):
    """Aufgabe 1.5: Mittelwerte von nights und persons je Vorlauf-Bucket."""
    try:
        if not has_columns(bucket_means, ["nights", "persons"], "bucket_means"):
            return
        if len(bucket_means) == 0 or len(bucket_means) > 5:
            hint("`bucket_means` sollte eine Zeile je Vorlauf-Bucket haben (höchstens 5).")
            return
        nights = pd.to_numeric(bucket_means["nights"], errors="coerce")
        persons = pd.to_numeric(bucket_means["persons"], errors="coerce")
        if nights.isna().any() or persons.isna().any():
            hint("In `bucket_means` stehen leere Werte. Habt ihr `observed=True` stehen lassen?")
            return
        if nights.max() > 30 or persons.max() > 10:
            hint("Die Werte sind viel zu groß für einen einzelnen Aufenthalt. "
                 "Habt ihr summiert oder gezählt statt den Mittelwert gebildet?")
            return
        if nights.min() < 1 or persons.min() < 1:
            hint("Die Werte sind zu klein. Jeder Aufenthalt hat mindestens eine Nacht und eine Person.")
            return
        ok("Mittelwerte je Vorlauf-Bucket berechnet. Vergleicht kurzen und langen Vorlauf!")
    except Exception as error:
        hint(f"Prüfung nicht möglich: {error}")


def check_segment(stays):
    """Aufgabe 1.6: Segmentregel in stays['segment']."""
    try:
        if not isinstance(stays, pd.DataFrame):
            hint("`stays` ist kein DataFrame. Führt Aufgabe 1.3 noch einmal aus.")
            return
        if "segment" not in stays.columns:
            hint("Die Spalte `segment` fehlt noch. Speichert eure Regel in `stays['segment']`.")
            return
        values = set(stays["segment"].dropna().unique())
        if stays["segment"].isna().any():
            hint("In `segment` gibt es leere Werte. Jeder Aufenthalt braucht ein Segment.")
            return
        if not values <= {"business", "leisure"}:
            extra = ", ".join(sorted(str(v) for v in values - {"business", "leisure"}))
            hint(f"`segment` darf nur 'business' und 'leisure' enthalten, gefunden: {extra}.")
            return
        if values != {"business", "leisure"}:
            hint("Es kommt nur ein Segment vor. Eure Grenze ist zu groß oder zu klein.")
            return
        share = (stays["segment"] == "business").mean()
        if share < 0.15:
            hint(f"Nur {share:.0%} business. Eure Grenze ist zu streng. "
                 "Schaut ins Histogramm: Wo liegt das Tal zwischen den Gipfeln?")
            return
        if share > 0.70:
            hint(f"{share:.0%} business ist zu viel. Eure Grenze ist zu großzügig. "
                 "Schaut ins Histogramm: Wo liegt das Tal zwischen den Gipfeln?")
            return
        if "lead_days" in stays.columns:
            lead = stays.groupby("segment")["lead_days"].mean()
            if lead["business"] >= lead["leisure"]:
                hint("Bei euch buchen business-Gäste im Schnitt früher als leisure-Gäste. "
                     "Geschäftsreisende buchen kurzfristig. Stimmt die Richtung eurer Bedingung?")
                return
        ok(f"Segmentregel passt: {share:.0%} business, {1 - share:.0%} leisure.")
    except Exception as error:
        hint(f"Prüfung nicht möglich: {error}")


def check_segment_profile(segment_profile):
    """Aufgabe 1.6: Steckbrief je Segment."""
    try:
        if not has_columns(segment_profile, ["stays", "nights", "persons"], "segment_profile"):
            return
        if not {"business", "leisure"} <= set(segment_profile.index):
            hint("`segment_profile` sollte je eine Zeile für business und leisure haben. Gruppiert nach `segment`.")
            return
        persons = pd.to_numeric(segment_profile["persons"], errors="coerce")
        if persons.isna().any():
            hint("In der Spalte `persons` stehen keine Zahlen. Die Rechenart ist ein Text wie im Mini-Beispiel.")
            return
        if persons.max() > 10:
            hint("`persons` ist viel zu groß für eine Reisegruppe. Habt ihr summiert oder gezählt statt den Mittelwert gebildet?")
            return
        if persons.min() < 1:
            hint("`persons` ist kleiner als 1. Jeder Aufenthalt hat mindestens eine Person.")
            return
        ok("Steckbrief fertig. Vergleicht Vorlauf, Nächte und Personen der beiden Segmente.")
    except Exception as error:
        hint(f"Prüfung nicht möglich: {error}")
