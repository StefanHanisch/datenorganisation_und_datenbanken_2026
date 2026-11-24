# %% [markdown]
# ## Block 1b: SQL und pandas – direkt in der Datenbank
#
# Bisher haben wir ganze Tabellen mit `load_tables()` geladen und dann in pandas gerechnet. Man kann die Datenbank aber auch **selbst rechnen lassen** und nur das fertige Ergebnis abholen. Bei großen Tabellen ist das oft schneller, weil nur wenige Zeilen über das Netz kommen.
#
# Dafür steht euch aus der Setup-Zelle die Verbindung **`engine`** zur Verfügung. Ein paar Spielregeln:
#
# - Eure Verbindung darf **nur lesen**. `INSERT`, `UPDATE`, `DELETE` oder `CREATE` werden abgelehnt.
# - Alle Tabellen liegen im Schema **`analytics`**. Schreibt deshalb immer `analytics.` vor den Tabellennamen, also `analytics.reservations`, `analytics.hotels` usw. Die Spalten sind dieselben wie in den DataFrames.
# - Jede Abfrage darf höchstens **60 Sekunden** laufen, danach bricht die Datenbank ab.
# - Bitte **keine riesigen Ergebnisse** abholen (also kein `SELECT * FROM analytics.reservations`). Lasst die Datenbank zählen, summieren und gruppieren.

# %% [markdown]
# ### Aufgabe 1b.1: Eine Abfrage aus Python · ⏱ ca. 10 Min.
#
# Mit **`pd.read_sql(text(sql), engine)`** schickt ihr eine SQL-Abfrage an die Datenbank und bekommt das Ergebnis als DataFrame zurück. `text(...)` markiert den String als SQL.
#
# **Mini-Beispiel:** Wie viele Hotels gibt es? (Die dreifachen Anführungszeichen `"""` erlauben SQL über mehrere Zeilen.)

# %%
pd.read_sql(text("""
    SELECT COUNT(*) AS n_hotels
    FROM analytics.hotels
"""), engine)

# %% [markdown]
# Oft soll ein Wert aus Python in die Abfrage, zum Beispiel eine Hotel-ID. Dafür schreibt ihr im SQL einen **Platzhalter** mit Doppelpunkt (`:min_stars`) und übergebt den Wert getrennt mit `params={...}`.
#
# Warum nicht einfach mit einem f-String (`f"... WHERE stars >= {x}"`) in den Text kleben? Weil dann jeder Text, der in `x` steht, als SQL ausgeführt wird. Kommt dieser Text von außen, etwa aus einem Suchfeld, kann jemand eigenen SQL-Code einschleusen: **SQL-Injection**. Mit Platzhaltern übergibt die Datenbank-Bibliothek den Wert sicher als reinen Wert.
#
# **Mini-Beispiel:**

# %%
pd.read_sql(
    text("""
        SELECT name, stars
        FROM analytics.hotels
        WHERE stars >= :min_stars
        ORDER BY stars DESC
    """),
    engine,
    params={"min_stars": 4},
)

# %% [markdown]
# Jetzt eine echte Frage: **Wie oft wurde jede Zimmerkategorie im ersten Hotel gebucht?** Wir verbinden `room_categories` und `reservations` mit `JOIN`, filtern auf ein Hotel und auf bestätigte Buchungen und zählen je Kategorie.
#
# `hotels["id"].iloc[0]` ist die ID in der ersten Zeile von `hotels`. `int(...)` macht daraus eine normale Python-Zahl, denn mit dem pandas-Zahlentyp kann die Datenbank-Bibliothek nichts anfangen. Diese Zelle ist vorgegeben.

# %%
selected_hotel = int(hotels["id"].iloc[0])

sql_df = pd.read_sql(
    text("""
        SELECT c.name AS category, COUNT(*) AS bookings
        FROM analytics.room_categories AS c
        JOIN analytics.reservations AS r ON r.category_id = c.id
        WHERE c.hotel_id = :hotel_id
          AND r.status = 'confirmed'
        GROUP BY c.name
        ORDER BY bookings DESC
    """),
    engine,
    params={"hotel_id": selected_hotel},
)
sql_df

# %% [markdown]
# ### Aufgabe 1b.2: Dieselbe Frage in pandas · ⏱ ca. 10 Min.
#
# Dieselbe Abfrage könnt ihr auch mit den geladenen DataFrames beantworten. Jede SQL-Zeile hat ein pandas-Gegenstück. Zwei Dinge sind neu:
#
# - In `query` greift ihr mit **`@`** auf eine Python-Variable zu: `query("hotel_id == @selected_hotel")`.
# - **`groupby(...).size()`** zählt die Zeilen je Gruppe (wie `COUNT(*)`). **`reset_index(name="bookings")`** macht daraus wieder einen normalen DataFrame mit der Zählspalte `bookings`.
#
# **Mini-Beispiel:**

# %%
toy_sql = pd.DataFrame({
    "hotel_id": [1, 1, 1, 2],
    "category": ["Standard", "Suite", "Standard", "Standard"],
})
wanted_hotel = 1
toy_sql.query("hotel_id == @wanted_hotel").groupby("category").size().reset_index(name="bookings")

# %%
# WHERE c.hotel_id = :hotel_id   (und Spalten umbenennen wie c.name AS category)
hotel_categories = categories.query("hotel_id == @selected_hotel").rename(
    columns={"id": "category_id", "name": "category"}
)
# WHERE r.status = 'confirmed'
confirmed = reservations.query("status == 'confirmed'")
# JOIN ... ON r.category_id = c.id
joined = confirmed.merge(hotel_categories, on="category_id")

# TODO: GROUP BY c.name: Nach welcher Spalte von joined wird gruppiert?
### LÖSUNG
pandas_df = joined.groupby("category").size().reset_index(name="bookings")
### LÜCKE
pandas_df = joined.groupby(___).size().reset_index(name="bookings")
### ENDE
# ORDER BY bookings DESC
pandas_df = pandas_df.sort_values("bookings", ascending=False)
pandas_df

# %%
check_same_total(sql_df, pandas_df)

# %% [markdown]
# ### Aufgabe 1b.3: Eure eigene SQL-Abfrage · ⏱ ca. 15 Min.
#
# Das Hotel verkauft Zimmer über drei **Vertriebskanäle** (`channel`): `direct` (eigene Website), `corporate` (Firmenverträge) und `ota` (Buchungsportale). Frage: **Welcher Kanal bringt im Jahr 2024 den höchsten Durchschnittspreis pro Nacht?**
#
# Die Abfrage ist fast fertig. Zwei Hinweise zum SQL:
#
# - `AVG(rate_per_night)::numeric` wandelt den Mittelwert in den PostgreSQL-Typ `numeric` um, weil `ROUND(..., 2)` nur damit auf zwei Nachkommastellen rundet.
# - Diesmal steht die Lücke **im SQL-Text**. Lasst ihr sie stehen, meldet PostgreSQL einen Fehler wie `column "___" does not exist`.
#
# Erinnerung: Jede Spalte im `SELECT`, die nicht in einer Aggregatfunktion (`AVG`, `COUNT`, …) steckt, muss im `GROUP BY` stehen.

# %%
# TODO: Ergänzt im SQL, wonach gruppiert wird.
### LÖSUNG
channel_sql = """
    SELECT channel,
           ROUND(AVG(rate_per_night)::numeric, 2) AS avg_rate,
           COUNT(*) AS bookings
    FROM analytics.reservations
    WHERE status = 'confirmed'
      AND checkin >= DATE '2024-01-01'
      AND checkin < DATE '2025-01-01'
    GROUP BY channel
    ORDER BY avg_rate DESC
"""
### LÜCKE
channel_sql = """
    SELECT channel,
           ROUND(AVG(rate_per_night)::numeric, 2) AS avg_rate,
           COUNT(*) AS bookings
    FROM analytics.reservations
    WHERE status = 'confirmed'
      AND checkin >= DATE '2024-01-01'
      AND checkin < DATE '2025-01-01'
    GROUP BY ___
    ORDER BY avg_rate DESC
"""
### ENDE
channel_rates = pd.read_sql(text(channel_sql), engine)
# numeric kommt in Python als Decimal an; für Rechnungen und Plots in float umwandeln
channel_rates["avg_rate"] = channel_rates["avg_rate"].astype(float)
channel_rates

# %%
check_channel_rates(channel_rates)

# %% [markdown]
# 🤔 Warum könnte ein Kanal teurer sein als ein anderer? Denkt daran, wer über `corporate` bucht und wann gebucht wird.

# %% [markdown] [loesung]
# **Erkenntnis:** Die Durchschnittspreise der drei Kanäle liegen fast gleichauf (rund 135 € pro Nacht). Hinter den Kanälen stecken trotzdem verschiedene Gäste: Über `corporate` buchen nur Geschäftsreisende (kurzfristig, allein, meist unter der Woche), über Buchungsportale vor allem Urlauber*innen. Der eigentliche Unterschied für das Hotel entsteht erst nach Abzug der Provision (`commission_pct`): direct 0 %, corporate 5 %, ota 18 %. Das schaut ihr euch in Block 3 genauer an.

# %% [markdown]
# ### Aufgabe 1b.4: SQL ↔ pandas · ⏱ ca. 5 Min.
#
# Zum Vergleich steht hier dieselbe Kanal-Auswertung in pandas (vorgegeben). Legt die beiden Lösungen nebeneinander: Jeder Teil der SQL-Abfrage findet sich in einer Zeile wieder.

# %%
pandas_rates = (
    reservations
    .query("status == 'confirmed' and checkin >= '2024-01-01' and checkin < '2025-01-01'")  # WHERE
    .groupby("channel")                                                                   # GROUP BY
    .agg(avg_rate=("rate_per_night", "mean"), bookings=("id", "count"))                   # SELECT AVG, COUNT
    .round(2)
    .sort_values("avg_rate", ascending=False)                                             # ORDER BY
    .reset_index()
)
pandas_rates

# %% [markdown]
# **Merke: SQL ↔ pandas**
#
# | SQL | pandas |
# |---|---|
# | `SELECT a, b` | `df[["a", "b"]]` |
# | `WHERE status = 'confirmed'` | `df.query("status == 'confirmed'")` |
# | `JOIN b ON a.key = b.key` | `a.merge(b, on="key")` |
# | `GROUP BY x` + `COUNT(*)` | `df.groupby("x").size()` |
# | `GROUP BY x` + `AVG(y) AS avg_y` | `df.groupby("x").agg(avg_y=("y", "mean"))` |
# | `ORDER BY y DESC` | `df.sort_values("y", ascending=False)` |
# | `CASE WHEN … THEN … ELSE … END` | `np.where(bedingung, wert_ja, wert_nein)` |
#
# 🤔 Wann lasst ihr lieber die Datenbank rechnen, wann rechnet ihr lieber in pandas?

# %% [markdown] [loesung]
# **Erkenntnis:** In der Datenbank rechnen lohnt sich, wenn die Tabellen groß sind und am Ende nur ein kleines Ergebnis gebraucht wird (Zählen, Summen, Filter): Dann wandern nur wenige Zeilen über das Netz, und die Daten sind immer aktuell. In pandas rechnen lohnt sich, wenn man dieselben Daten viele Male unterschiedlich auswerten, schnell ausprobieren und plotten will, oder für Schritte, die in SQL umständlich sind. In der Praxis kombiniert man beides: grob in SQL filtern und aggregieren, fein in pandas auswerten.
