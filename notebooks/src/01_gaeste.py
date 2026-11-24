# %% [markdown]
# ## Block 1: Wer sind unsere Gäste?
#
# In unserer Hoteldatenbank stecken Privat- und Geschäftsreisende. Für das Hotel ist das ein großer Unterschied: Geschäftsreisende brauchen ein Zimmer am Montag in der Messestadt, Urlauber*innen ein Familienzimmer am Wochenende an der See. Leider gibt es **keine Spalte**, die verrät, wer wer ist.
#
# In diesem Block lernt ihr die wichtigsten pandas-Werkzeuge kennen und findet am Ende selbst eine Regel, die die beiden Gruppen trennt. Schritt für Schritt:
#
# 1. Daten laden und anschauen
# 2. Tabellen verbinden (wie `JOIN` in SQL)
# 3. Eine Arbeitstabelle `stays` bauen
# 4. Den Buchungsvorlauf anschauen
# 5. Gruppen bilden und vergleichen
# 6. Eure eigene Segmentregel

# %% [markdown]
# ### Aufgabe 1.1: Daten laden und anschauen · ⏱ ca. 10 Min.
#
# Die Setup-Zelle oben hat die Funktion `load_tables()` bereitgestellt. Sie holt alle Tabellen aus der Datenbank und gibt sie als **Dictionary** zurück: Zu jedem Tabellennamen gehört ein **DataFrame**.
#
# Ein DataFrame ist eine Tabelle in Python: Zeilen, Spalten mit Namen, und jede Spalte hat einen Datentyp (Zahl, Text, Datum, …). Im Grunde dasselbe wie eine Tabelle in der Datenbank, nur dass sie jetzt im Arbeitsspeicher liegt und wir mit Python darin rechnen.

# %%
tables = load_tables()
check_tables(tables)

# %% [markdown]
# Damit wir nicht immer `tables["reservations"]` schreiben müssen, geben wir jeder Tabelle einen kurzen Namen. Diese Namen benutzen wir im ganzen Notebook.

# %%
cities = tables["cities"]
hotels = tables["hotels"]
categories = tables["room_categories"]
guests = tables["guests"]
reservations = tables["reservations"]
daily_rates = tables["daily_rates"]
events = tables["calendar_events"]

# %% [markdown]
# Vier Werkzeuge, um einen DataFrame kennenzulernen:
#
# | Befehl | Was es zeigt |
# |---|---|
# | `df.head()` | die ersten 5 Zeilen (`df.head(10)`: die ersten 10) |
# | `df.shape` | (Anzahl Zeilen, Anzahl Spalten) |
# | `len(df)` | nur die Anzahl Zeilen |
# | `df.info()` | alle Spalten mit Datentyp und Anzahl gefüllter Werte |
#
# **Mini-Beispiel:** Ein Spielzeug-DataFrame mit drei Gästen.

# %%
toy = pd.DataFrame({
    "name": ["Ada", "Ben", "Cem"],
    "nights": [2, 5, 1],
})
print("shape:", toy.shape)        # (3, 2): 3 Zeilen, 2 Spalten
print("Zeilen:", toy.shape[0])    # Position 0 im Paar = Zeilen
print("Spalten:", toy.shape[1])   # Position 1 im Paar = Spalten
print("len:", len(toy))           # ebenfalls 3
toy.head()

# %% [markdown]
# Jetzt die echte Tabelle `reservations`. Die letzte Zeile einer Zelle wird automatisch angezeigt.

# %%
reservations.head()

# %%
reservations.info()

# %% [markdown]
# Achtet in der Ausgabe von `info()` auf die Spalte `Dtype`: `int64` sind ganze Zahlen, `float64` Kommazahlen, `object` meist Text und `datetime64[ns]` Datum mit Uhrzeit. Mit Datumsspalten kann pandas rechnen, das brauchen wir gleich.
#
# Jetzt seid ihr dran. Eine Lücke ist immer `___` (drei Unterstriche). Die Meldung `LueckeOffen: In dieser Zelle steht noch eine Lücke ___` heißt: Hier fehlt noch eure Lösung.

# %%
# TODO: Wie viele Reservierungen gibt es? Und wie viele Spalten hat die Tabelle?
### LÖSUNG
n_reservations = len(reservations)
n_columns = reservations.shape[1]
### LÜCKE
n_reservations = len(___)
n_columns = reservations.shape[___]
### ENDE
print(f"{n_reservations:,} Reservierungen mit je {n_columns} Spalten")

# %%
check_counts(n_reservations, n_columns, reservations)

# %% [markdown]
# ### Aufgabe 1.2: Tabellen verbinden · ⏱ ca. 15 Min.
#
# Eine Reservierung kennt nur ihre `category_id`. In welchem Hotel und in welcher Stadt das Zimmer liegt, steht in anderen Tabellen:
#
# `reservations.category_id` → `room_categories.id` → `room_categories.hotel_id` → `hotels.id` → `hotels.city_id` → `cities.id`
#
# In SQL würdet ihr dafür `JOIN … ON …` schreiben. In pandas heißt das **`merge`**:
#
# | SQL | pandas |
# |---|---|
# | `FROM a JOIN b ON a.key = b.key` | `a.merge(b, on="key")` |
#
# `on=` nennt die Spalte, die in **beiden** Tabellen gleich heißt. Wie beim SQL-`JOIN` (ein *inner join*) bleiben nur Zeilen, die in beiden Tabellen einen Partner finden.
#
# **Mini-Beispiel:** Zwei Spielzeug-Tabellen, verbunden über `city_id`.

# %%
toy_hotels = pd.DataFrame({
    "hotel": ["Seeblick", "Messehof", "Alpenruh"],
    "city_id": [1, 2, 3],
})
toy_cities = pd.DataFrame({
    "city_id": [1, 2, 3],
    "city": ["Sylt", "Hannover", "Garmisch-Partenkirchen"],
})
toy_hotels.merge(toy_cities, on="city_id")

# %% [markdown]
# Ein Problem: In unseren echten Tabellen heißt der Schlüssel oft einfach `id`, und auch `name` gibt es mehrfach (Kategorie-Name, Hotel-Name, Stadt-Name). Deshalb benennen wir Spalten vor dem `merge` um. Das macht **`rename`**, ähnlich wie `AS` in SQL.
#
# Mit doppelten eckigen Klammern `df[["a", "b"]]` wählt ihr Spalten aus, wie die Spaltenliste hinter `SELECT`.
#
# **Mini-Beispiel:**

# %%
toy_rooms = pd.DataFrame({"id": [7, 8], "name": ["Standard", "Suite"], "base_price": [90.0, 250.0]})
toy_rooms.rename(columns={"id": "category_id", "name": "category"})[["category_id", "category"]]

# %% [markdown]
# Jetzt bauen wir die Tabelle `places`: **eine Zeile je Zimmerkategorie** mit Hotel, Stadt, Stadttyp (`city` = Großstadt, `resort` = Urlaubsort) und Bundesland. Diese Zelle ist vollständig vorgegeben, weil alle späteren Blöcke `places` brauchen. Lest sie trotzdem Zeile für Zeile.

# %%
# Schritt 1: Spalten umbenennen, damit die Schlüssel zusammenpassen
rooms = categories.rename(columns={"id": "category_id", "name": "category"})
houses = hotels.rename(columns={"id": "hotel_id"})[["hotel_id", "city_id", "city_type", "bundesland"]]
towns = cities.rename(columns={"id": "city_id", "name": "city"})[["city_id", "city"]]

# Schritt 2: zwei JOINs hintereinander
places = rooms.merge(houses, on="hotel_id").merge(towns, on="city_id")
places.head()

# %% [markdown]
# **Kleine Übung:** Welches Hotel liegt in welcher Stadt? Verbindet `hotels` mit `towns`. Überlegt, über welche Spalte die beiden Tabellen zusammengehören. (Tipp: Sie steht in beiden Tabellen und heißt gleich.)

# %%
# TODO: Ergänzt die Schlüsselspalte für den merge (als Text in Anführungszeichen).
### LÖSUNG
hotel_cities = hotels.merge(towns, on="city_id")
### LÜCKE
hotel_cities = hotels.merge(towns, on=___)
### ENDE
hotel_cities[["name", "city", "city_type", "stars"]]

# %%
check_hotel_cities(hotel_cities, hotels)

# %% [markdown]
# Wie viele unserer Hotels liegen in Großstädten, wie viele an Urlaubsorten? **`value_counts()`** zählt, wie oft jeder Wert in einer Spalte vorkommt.
#
# **Mini-Beispiel:**

# %%
toy_types = pd.DataFrame({"city_type": ["city", "resort", "city", "city"]})
toy_types["city_type"].value_counts()

# %%
hotel_cities["city_type"].value_counts()

# %% [markdown]
# ### Aufgabe 1.3: Die Arbeitstabelle `stays` · ⏱ ca. 15 Min.
#
# Für unsere Auswertungen zählen nur **bestätigte** Aufenthalte, Stornierungen lassen wir weg. Zeilen filtern geht mit **`query`**: Ihr schreibt die Bedingung wie hinter `WHERE` in SQL, aber in Anführungszeichen. Texte stehen darin in einfachen Anführungszeichen `'…'`.
#
# **Mini-Beispiel:**

# %%
toy_bookings = pd.DataFrame({
    "id": [1, 2, 3, 4],
    "status": ["confirmed", "cancelled", "confirmed", "confirmed"],
    "adults": [1, 2, 2, 1],
})
toy_bookings.query("status == 'confirmed'")

# %% [markdown]
# Mit Datumsspalten kann pandas rechnen. Zieht man zwei Datumswerte voneinander ab, entsteht eine Zeitspanne. Über **`.dt`** kommt ihr an die Teile eines Datums oder einer Zeitspanne:
#
# | Befehl | Ergebnis |
# |---|---|
# | `(ende - anfang).dt.days` | Zeitspanne in ganzen Tagen |
# | `datum.dt.day_of_week` | Wochentag, 0 = Montag … 6 = Sonntag |
# | `datum.dt.month`, `datum.dt.year` | Monat, Jahr |
# | `datum.dt.normalize()` | Uhrzeit auf 00:00 setzen, nur der Tag zählt |
#
# **Mini-Beispiel:**

# %%
toy_dates = pd.DataFrame({
    "checkin": pd.to_datetime(["2024-03-04", "2024-03-08", "2024-12-24"]),
    "checkout": pd.to_datetime(["2024-03-06", "2024-03-10", "2024-12-27"]),
})
toy_dates["nights"] = (toy_dates["checkout"] - toy_dates["checkin"]).dt.days
toy_dates["weekday"] = toy_dates["checkin"].dt.day_of_week
toy_dates["month"] = toy_dates["checkin"].dt.month
toy_dates

# %% [markdown]
# Jetzt bauen wir `stays`. Auch diese Zelle ist vollständig vorgegeben, weil spätere Blöcke sie brauchen. Neu ist der **Vorlauf** `lead_days`: die Zahl der Tage zwischen Buchung (`created_at`) und Anreise (`checkin`).

# %%
# Nur bestätigte Reservierungen, dazu Hotel und Stadt aus places
stays = reservations.query("status == 'confirmed'").merge(places, on="category_id")

# Neue Spalten berechnen
stays["nights"] = (stays["checkout"] - stays["checkin"]).dt.days
stays["persons"] = stays["adults"] + stays["children"]
stays["lead_days"] = (stays["checkin"] - stays["created_at"].dt.normalize()).dt.days
stays["weekday"] = stays["checkin"].dt.day_of_week
stays["month"] = stays["checkin"].dt.month
stays["year"] = stays["checkin"].dt.year

stays[["checkin", "checkout", "nights", "persons", "lead_days", "weekday", "city"]].head()

# %%
check_stays(stays)

# %% [markdown]
# **Kleine Übung:** Wie viele Nächte bleibt ein Gast im Durchschnitt? Eine Spalte lässt sich mit einer Methode zu einer einzigen Zahl zusammenfassen.
#
# **Mini-Beispiel:**

# %%
toy_nights = pd.Series([2, 5, 1, 4])
print("Summe:     ", toy_nights.sum())
print("Mittelwert:", toy_nights.mean())
print("Median:    ", toy_nights.median())
print("Maximum:   ", toy_nights.max())

# %%
# TODO: Berechnet den Mittelwert der Spalte nights.
### LÖSUNG
avg_nights = stays["nights"].mean()
### LÜCKE
avg_nights = stays["nights"].___()
### ENDE
print(f"Im Durchschnitt {avg_nights:.2f} Nächte")

# %%
check_avg_nights(avg_nights, stays)

# %% [markdown]
# ### Aufgabe 1.4: Wie weit im Voraus wird gebucht? · ⏱ ca. 5 Min.
#
# Ein **Histogramm** zeigt, wie sich die Werte einer Spalte verteilen: Die x-Achse wird in schmale Bereiche geteilt, die Höhe eines Balkens ist die Anzahl der Werte darin.
#
# Ganz wenige Buchungen haben einen sehr langen Vorlauf. Damit die Achse lesbar bleibt, setzt `clip(upper=150)` alle Werte über 150 auf 150. Diese Zelle ist vorgegeben, ihr müsst nur hinschauen.

# %%
stays["lead_days"].clip(upper=150).plot.hist(bins=50, title="Vorlauf in Tagen (gekappt bei 150)")
plt.xlabel("Tage zwischen Buchung und Anreise")
plt.show()

# %% [markdown]
# 🤔 Wie viele Gipfel seht ihr? Was könnte hinter jedem Gipfel stecken? Wo liegt ungefähr das Tal dazwischen?

# %% [markdown] [loesung]
# **Erkenntnis:** Es gibt zwei Gipfel. Ein Gipfel liegt bei wenigen Tagen bis etwa zwei Wochen (kurzfristige Buchungen, typisch für Geschäftsreisen), ein zweiter, breiterer Gipfel bei etwa einem bis vier Monaten (langfristig geplante Urlaube). Dazwischen, zwischen etwa zwei und vier Wochen, liegt ein Tal: Dort bucht in unseren Daten fast niemand.

# %% [markdown]
# ### Aufgabe 1.5: Vorlauf in Gruppen · ⏱ ca. 15 Min.
#
# Mit vielen einzelnen Tageswerten lässt sich schlecht vergleichen. Wir teilen den Vorlauf deshalb in **Bereiche** („Buckets“) ein. Das macht **`pd.cut`**:
#
# - `bins=` sind die Grenzen. Ein Bereich enthält die rechte Grenze, aber nicht die linke: Zwischen −1 und 14 liegen also die Werte 0 bis 14.
# - `labels=` sind die Namen der Bereiche.
#
# **Mini-Beispiel:**

# %%
bins = [-1, 14, 29, 60, 120, 10_000]
labels = ["0-14", "15-29", "30-60", "61-120", "über 120"]
toy_lead = pd.DataFrame({"lead_days": [0, 14, 15, 45, 200]})
toy_lead["lead_bucket"] = pd.cut(toy_lead["lead_days"], bins=bins, labels=labels)
toy_lead

# %% [markdown]
# Jetzt für alle Aufenthalte (vorgegeben, spätere Blöcke brauchen `lead_bucket`):

# %%
stays["lead_bucket"] = pd.cut(stays["lead_days"], bins=bins, labels=labels)
stays["lead_bucket"].value_counts().sort_index()

# %% [markdown]
# **An welchen Wochentagen reisen die Gäste aus den einzelnen Buckets an?** Dafür brauchen wir eine Kreuztabelle: Zeilen = Wochentag, Spalten = Vorlauf-Bucket, in jeder Zelle die Anzahl Anreisen. Das macht **`pivot_table`**:
#
# - `index=` bestimmt die Zeilen, `columns=` die Spalten,
# - `values=` ist die Spalte, die ausgewertet wird,
# - `aggfunc=` sagt wie: `"count"` zählt, `"sum"` summiert, `"mean"` bildet den Mittelwert.
#
# `observed=True` heißt: nur Kombinationen zeigen, die wirklich vorkommen. Das braucht man bei Bucket-Spalten wie `lead_bucket`.
#
# **Mini-Beispiel:**

# %%
toy_arrivals = pd.DataFrame({
    "id": [1, 2, 3, 4, 5],
    "weekday": [0, 0, 4, 4, 4],
    "lead_bucket": ["0-14", "0-14", "0-14", "30-60", "30-60"],
})
toy_arrivals.pivot_table(index="weekday", columns="lead_bucket", values="id", aggfunc="count")

# %% [markdown]
# Lest die Tabelle: Am Montag (0) gab es zwei kurzfristige Anreisen, am Freitag (4) eine kurzfristige und zwei mit 30–60 Tagen Vorlauf. Fehlende Kombinationen erscheinen als `NaN` (kein Wert).
#
# Jetzt mit den echten Daten, als gestapeltes Balkendiagramm. Mit `rename` ersetzen wir die Zahlen 0–6 durch Wochentagsnamen.

# %%
weekday_names = {0: "Mo", 1: "Di", 2: "Mi", 3: "Do", 4: "Fr", 5: "Sa", 6: "So"}
table = stays.pivot_table(index="weekday", columns="lead_bucket", values="id", aggfunc="count", observed=True)
table = table.rename(index=weekday_names)
table.plot.bar(stacked=True, title="Anreisen je Wochentag und Vorlauf")
plt.xlabel("Wochentag der Anreise")
plt.ylabel("Anreisen")
plt.show()

# %% [markdown]
# Bleiben kurzfristige Gäste kürzer? Reisen sie mit weniger Personen? Dafür bilden wir **Gruppen** und berechnen je Gruppe einen Mittelwert. Das macht **`groupby`**, genau wie `GROUP BY` in SQL:
#
# `df.groupby("gruppenspalte")[["spalte_a", "spalte_b"]].mean()`
#
# **Mini-Beispiel:**

# %%
toy_groups = pd.DataFrame({
    "lead_bucket": ["0-14", "0-14", "30-60", "30-60", "30-60"],
    "nights": [1, 2, 5, 7, 6],
    "persons": [1, 1, 2, 4, 3],
})
toy_groups.groupby("lead_bucket")[["nights", "persons"]].mean()

# %%
# TODO: Berechnet je Vorlauf-Bucket den Mittelwert von nights und persons.
### LÖSUNG
bucket_means = stays.groupby("lead_bucket", observed=True)[["nights", "persons"]].mean().round(2)
### LÜCKE
bucket_means = stays.groupby("lead_bucket", observed=True)[["nights", "persons"]].___().round(2)
### ENDE
bucket_means

# %%
check_bucket_means(bucket_means)

# %% [markdown]
# 🤔 Vergleicht die kurzfristigen Buckets mit den langfristigen: Wochentag der Anreise, Nächte, Personen. Welche zwei Gästetypen erkennt ihr?

# %% [markdown] [loesung]
# **Erkenntnis:** Gäste mit kurzem Vorlauf (0–14 Tage) reisen vor allem Montag bis Mittwoch an, bleiben kurz und reisen mit wenigen Personen: typisch Geschäftsreise. Gäste mit langem Vorlauf reisen eher Donnerstag oder Freitag an, bleiben länger und kommen mit mehr Personen: typisch Urlaub. Die Buckets 15–29 und „über 120“ sind leer: Das ist das Tal aus dem Histogramm, und länger als vier Monate im Voraus bucht in unseren Daten niemand.

# %% [markdown]
# ### Aufgabe 1.6: Eure Segmentregel · ⏱ ca. 20 Min.
#
# Jetzt legt ihr fest, wer als Geschäftsreise (`"business"`) und wer als Urlaub (`"leisure"`) zählt. Die neue Spalte `stays["segment"]` brauchen spätere Blöcke, zum Beispiel für getrennte Preiskurven.
#
# Eine Wenn-dann-Regel für eine ganze Spalte schreibt man mit **`np.where`**:
#
# `np.where(bedingung, wert_wenn_wahr, wert_wenn_falsch)`
#
# Das entspricht `CASE WHEN bedingung THEN … ELSE … END` in SQL.
#
# **Mini-Beispiel:** Wer mehr als 3 Nächte bleibt, ist ein „Langbleiber“.

# %%
toy_rule = pd.DataFrame({"nights": [1, 4, 2, 7]})
toy_rule["stay_type"] = np.where(toy_rule["nights"] > 3, "long", "short")
toy_rule

# %% [markdown]
# Welche Spalte trennt die beiden Gruppen am deutlichsten? Schaut noch einmal auf das Histogramm aus Aufgabe 1.4: Wo liegt das Tal zwischen den beiden Gipfeln? Wählt dort eure Grenze in Tagen.

# %%
# TODO: Ergänzt die Grenze in Tagen. Kurzfristige Buchungen zählen als business.
### LÖSUNG
stays["segment"] = np.where(stays["lead_days"] <= 21, "business", "leisure")
### LÜCKE
stays["segment"] = np.where(stays["lead_days"] <= ___, "business", "leisure")
### ENDE
stays["segment"].value_counts(normalize=True).round(2)

# %%
check_segment(stays)

# %% [markdown]
# Prüfen wir die Regel: An welchen Wochentagen reisen die beiden Segmente an? Damit große und kleine Gruppen vergleichbar sind, teilen wir jede Spalte durch ihre Summe. So steht in jeder Zelle der **Anteil** der Anreisen (vorgegeben).

# %%
weekday_counts = stays.pivot_table(index="weekday", columns="segment", values="id", aggfunc="count")
weekday_share = (weekday_counts / weekday_counts.sum()).rename(index=weekday_names)
weekday_share.plot.bar(title="Anteil der Anreisen je Wochentag und Segment")
plt.xlabel("Wochentag der Anreise")
plt.ylabel("Anteil")
plt.show()

# %% [markdown]
# Zum Schluss ein Steckbrief je Segment. Mit **`agg`** berechnet ihr mehrere Kennzahlen auf einmal. Jede Kennzahl bekommt einen Namen und ein Paar aus Spalte und Rechenart:
#
# `name=("spalte", "rechenart")`, zum Beispiel `nights=("nights", "mean")`.
#
# **Mini-Beispiel:**

# %%
toy_profile = pd.DataFrame({
    "segment": ["business", "business", "leisure", "leisure", "leisure"],
    "nights": [1, 2, 5, 7, 6],
    "persons": [1, 1, 2, 4, 3],
})
toy_profile.groupby("segment").agg(
    stays=("nights", "count"),
    nights=("nights", "mean"),
    max_persons=("persons", "max"),
)

# %%
# TODO: Ergänzt die Rechenart für persons: Wie viele Personen reisen im Durchschnitt mit?
### LÖSUNG
segment_profile = stays.groupby("segment").agg(
    stays=("id", "count"),
    lead_days=("lead_days", "mean"),
    nights=("nights", "mean"),
    persons=("persons", "mean"),
).round(2)
### LÜCKE
segment_profile = stays.groupby("segment").agg(
    stays=("id", "count"),
    lead_days=("lead_days", "mean"),
    nights=("nights", "mean"),
    persons=("persons", ___),
).round(2)
### ENDE
segment_profile

# %%
check_segment_profile(segment_profile)

# %% [markdown]
# 🤔 Passt euer Steckbrief zu dem, was ihr von Geschäfts- und Urlaubsreisen erwartet? Wo könnte eure Regel danebenliegen, zum Beispiel bei einer Familie, die spontan ans Meer fährt?

# %% [markdown] [loesung]
# **Erkenntnis:** Der Vorlauf trennt die beiden Gruppen am saubersten, eine Grenze im Tal (etwa 21 Tage) funktioniert gut. Business reist überwiegend Montag bis Mittwoch an, bleibt kurz und reist mit wenigen Personen. Leisure reist vor allem Donnerstag oder Freitag an, bleibt länger und kommt mit mehr Personen. Die Regel ist eine Schätzung: Spontane Kurzurlaube landen fälschlich bei business, früh geplante Dienstreisen bei leisure.
