# %% [markdown]
# ## Block 3: Preisfalle und Umsatzkurve
#
# Die Hotelleitung stellt eine einfache Frage: **Welcher Preis bringt uns den höchsten Umsatz?**
#
# Klingt nach einer Zeile Code. In diesem Block seht ihr, warum die naheliegende Antwort
# falsch ist und wie man mit den richtigen Daten trotzdem eine faire Antwort findet.
# Wir gehen in kleinen Schritten vor:
#
# 1. Eine Tabelle bauen: ein Angebotspreis und die Zahl der Buchungen je Kategorie und Anreisetag.
# 2. Einen ersten Blick auf Preis und Verkäufe werfen.
# 3. Verstehen, woher die überraschende Kurve kommt.
# 4. Eine faire Preiskurve und den „Umsatzberg“ finden.
# 5. Prüfen, ob das für alle Gäste und alle Vertriebskanäle gilt.
#
# Ihr braucht dafür `stays`, `places`, `daily_rates` und `events` aus Block 1.
#
# **Wichtige Kennzahl `r`:** Jede Zimmerkategorie hat einen Listenpreis (`base_price`).
# Das Hotel bietet an jedem Tag einen Preis an (`offered_rate`). Wir rechnen
# `r = offered_rate / base_price`. `r = 1.0` heißt Listenpreis, `r = 0.8` heißt 20 % günstiger,
# `r = 1.2` heißt 20 % teurer. So lassen sich Kategorien mit verschiedenen Listenpreisen vergleichen.

# %% [markdown]
# ### Aufgabe 3.1: Eine Tabelle je Kategorie und Anreisetag · ⏱ ca. 15 Min.
#
# In `daily_rates` steht für jede Kategorie und jeden Anreisetag der angebotene Preis.
# In `stays` stehen die tatsächlichen Buchungen. Wir wollen beides in **einer** Tabelle `daily`.
#
# Zuerst zählen wir die Buchungen je Kategorie und Anreisetag. Dieser Code ist vorgegeben.

# %%
# Buchungen je Kategorie und Anreisetag zählen
sales = stays.groupby(["category_id", "checkin"]).size()  # size() zählt die Zeilen je Gruppe
sales = sales.rename("bookings").reset_index()            # Series -> DataFrame mit Spalte bookings
sales = sales.rename(columns={"checkin": "arrival_date"}) # gleicher Spaltenname wie in daily_rates
sales.head()

# %% [markdown]
# **Das Problem:** In `sales` fehlen alle Tage, an denen **niemand** gebucht hat.
# Gerade diese Tage sind für die Preisfrage wichtig: Vielleicht war der Preis dort zu hoch.
#
# **Mini-Beispiel `merge` mit `how`:** Beim Verbinden zweier Tabellen entscheidet `how`,
# welche Zeilen übrig bleiben.
#
# - `how="inner"`: nur Zeilen, die es in **beiden** Tabellen gibt.
# - `how="left"`: **alle** Zeilen der linken Tabelle. Fehlt rechts ein Partner, steht dort `NaN` (leer).

# %%
demo_days = pd.DataFrame({"day": ["Mo", "Di", "Mi"], "price": [80, 90, 100]})
demo_sales = pd.DataFrame({"day": ["Mo", "Mi"], "bookings": [3, 1]})

print("how='inner':")
print(demo_days.merge(demo_sales, how="inner", on="day"))
print()
print("how='left':")
print(demo_days.merge(demo_sales, how="left", on="day"))

# %% [markdown]
# Beim `inner`-Merge ist der Dienstag verschwunden. Beim `left`-Merge bleibt er, aber mit `NaN`.
# Mit `fillna(wert)` ersetzt ihr leere Werte. Ein Tag ohne Buchung hat 0 Buchungen.
#
# **Mini-Beispiel `fillna`:**

# %%
demo_left = demo_days.merge(demo_sales, how="left", on="day")
demo_left["bookings"] = demo_left["bookings"].fillna(0)
demo_left

# %% [markdown]
# Jetzt ihr. `daily` soll **jeden** Tag aus `daily_rates` behalten, auch Tage ohne Verkauf.

# %%
# Schritt 1: Preise mit den Kategorie-Infos (Listenpreis, Stadt, ...) verbinden
daily = daily_rates.merge(places, on="category_id")

# TODO: Verbindet daily mit sales so, dass alle Tage erhalten bleiben,
#       und tragt für Tage ohne Verkauf die richtige Zahl ein.
### LÖSUNG
daily = daily.merge(sales, how="left", on=["category_id", "arrival_date"])
daily["bookings"] = daily["bookings"].fillna(0)
### LÜCKE
daily = daily.merge(sales, how=___, on=["category_id", "arrival_date"])
daily["bookings"] = daily["bookings"].fillna(___)
### ENDE

# Preis im Verhältnis zum Listenpreis, auf 2 Nachkommastellen gerundet
daily["r"] = (daily["offered_rate"] / daily["base_price"]).round(2)
daily[["category", "arrival_date", "offered_rate", "base_price", "r", "bookings"]].head()

# %%
check_daily(daily, daily_rates)

# %% [markdown]
# ### Aufgabe 3.2: Der erste Blick · ⏱ ca. 10 Min.
#
# Im normalen Betrieb setzt das Hotel seine Preise selbst (`price_source == 'dynamic'`).
# So sieht die Hotelleitung ihre Zahlen jeden Tag. Wir zeichnen für jeden Wert von `r`,
# wie viele Buchungen ein Tag im Durchschnitt hatte. Der Code ist vorgegeben.

# %%
regular_days = daily.query("price_source == 'dynamic'")

regular_days.groupby("r")["bookings"].mean().plot(
    marker="o",
    title="Regelbetrieb: Preis gegen Verkäufe",
    xlabel="r (Angebotspreis / Listenpreis)",
    ylabel="Buchungen je Tag",
)
plt.show()

# %% [markdown]
# 🤔 Was seht ihr? Was würdet ihr der Hotelleitung raten, wenn ihr nur dieses Bild hättet?

# %% [markdown] [loesung]
# **Erkenntnis:** Je teurer, desto mehr Buchungen. Wer nur dieses Bild kennt, würde raten:
# „Preise rauf, dann kommen mehr Gäste.“ Das widerspricht jeder Erfahrung.
# Die nächste Aufgabe zeigt, warum das Bild in die Irre führt.

# %% [markdown]
# ### Aufgabe 3.3: Woher kommt diese Kurve? · ⏱ ca. 20 Min.
#
# Glaubt ihr wirklich, dass höhere Preise mehr Gäste anlocken? Sucht eine andere Erklärung.
# Ein Verdacht: An manchen Tagen wollen ohnehin viele Menschen in die Stadt, zum Beispiel
# bei einer Messe, einem Festival oder im Sommer. Wir markieren deshalb jeden Tag mit einer **Tagesart**.
#
# **Schritt 1: Event-Tage markieren.** In `events` stehen Termine je Stadt.
# Bundesweite Termine (`city_id` leer) lassen wir hier weg.
#
# **Mini-Beispiel „Markierung per Merge“:** Wir geben der Event-Tabelle eine Spalte `is_event = True`
# und verbinden mit `how="left"`. Wo es kein Event gibt, steht danach `NaN`.
# `.notna()` macht daraus `True`/`False`.

# %%
demo_days = pd.DataFrame({"day": ["Mo", "Di", "Mi"], "price": [80, 120, 90]})
demo_events = pd.DataFrame({"day": ["Di"]}).assign(is_event=True)

demo_marked = demo_days.merge(demo_events, how="left", on="day")
print(demo_marked)
print()
demo_marked["is_event"] = demo_marked["is_event"].notna()
print(demo_marked)

# %% [markdown]
# Jetzt für unsere Daten. Achtung, Datentypen: In `events` ist `city_id` vom Typ `Int64`
# (erlaubt leere Werte), in `daily` vom Typ `int64`. Nach `dropna` wandeln wir mit `astype("int64")` um,
# damit der Merge sauber passt.

# %%
# Nur Events mit Stadt, eine Zeile je Stadt und Tag
city_events = events.dropna(subset=["city_id"])[["city_id", "event_date"]].drop_duplicates()
city_events["city_id"] = city_events["city_id"].astype("int64")
city_events = city_events.rename(columns={"event_date": "arrival_date"}).assign(is_event=True)

# TODO: Verbindet so, dass alle Tage aus regular_days erhalten bleiben.
### LÖSUNG
regular = regular_days.merge(city_events, how="left", on=["city_id", "arrival_date"])
### LÜCKE
regular = regular_days.merge(city_events, how=___, on=["city_id", "arrival_date"])
### ENDE
regular["is_event"] = regular["is_event"].notna()
regular["is_event"].value_counts()

# %% [markdown]
# **Schritt 2: Tagesart festlegen.** Jeder Tag bekommt genau eine von drei Tagesarten:
#
# 1. `"Event"`, wenn ein Event stattfindet,
# 2. sonst `"Sommer"`, wenn der Tag im Juni, Juli oder August liegt,
# 3. sonst `"Alltag"`.
#
# **Mini-Beispiel verschachteltes `np.where`:** `np.where(bedingung, wert_wenn_ja, wert_wenn_nein)`.
# Für drei Fälle setzt ihr ein zweites `np.where` in den Nein-Teil. Mit `.isin([...])` prüft ihr,
# ob ein Wert in einer Liste vorkommt.

# %%
demo = pd.DataFrame({
    "day": ["10.03.", "15.07.", "20.07.", "05.11."],
    "month": [3, 7, 7, 11],
    "is_event": [False, False, True, True],
})
demo_summer = demo["month"].isin([6, 7, 8])
demo["day_type"] = np.where(demo["is_event"], "Event", np.where(demo_summer, "Sommer", "Alltag"))
demo

# %% [markdown]
# Beachtet die Reihenfolge: Der 20.07. ist Sommer **und** Event, er wird zu `"Event"`,
# weil die Event-Bedingung zuerst geprüft wird.

# %%
# TODO: Legt fest, welche Monate Sommer sind, und setzt die Sommer-Bedingung ins innere np.where.
### LÖSUNG
is_summer = regular["arrival_date"].dt.month.isin([6, 7, 8])
regular["day_type"] = np.where(regular["is_event"], "Event", np.where(is_summer, "Sommer", "Alltag"))
### LÜCKE
is_summer = regular["arrival_date"].dt.month.isin(___)
regular["day_type"] = np.where(regular["is_event"], "Event", np.where(___, "Sommer", "Alltag"))
### ENDE
regular["day_type"].value_counts()

# %%
check_day_type(regular)

# %% [markdown]
# **Schritt 3: Vergleichen.** Wie hoch sind Preis `r` und Buchungen im Durchschnitt je Tagesart?
# Der Code ist vorgegeben, lest das Ergebnis genau.

# %%
regular.groupby("day_type")[["r", "bookings"]].mean().round(2)

# %% [markdown]
# **Schritt 4: Die Kurve getrennt nach Tagesart.**
#
# **Mini-Beispiel `pivot_table`:** `pivot_table` macht aus einer langen Tabelle eine Kreuztabelle.
# `index` wird zu den Zeilen, `columns` zu den Spalten, und in den Zellen steht
# `aggfunc` (hier der Mittelwert) über `values`.

# %%
demo = pd.DataFrame({
    "r": [0.9, 0.9, 1.1, 1.1, 1.1],
    "day_type": ["Alltag", "Event", "Alltag", "Event", "Event"],
    "bookings": [2, 5, 1, 6, 4],
})
demo.pivot_table(index="r", columns="day_type", values="bookings", aggfunc="mean")

# %% [markdown]
# Jetzt für unsere Daten. Jede Tagesart bekommt eine eigene Farbe. Der Code ist vorgegeben.

# %%
points = regular.pivot_table(index="r", columns="day_type", values="bookings", aggfunc="mean")
points.plot(
    style="o",
    alpha=0.6,
    title="Regelbetrieb: Preis gegen Verkäufe nach Tagesart",
    xlabel="r (Angebotspreis / Listenpreis)",
    ylabel="Buchungen je Tag",
)
plt.show()

# %% [markdown]
# 🤔 Wo liegen die Event-Tage, wo die Alltagstage? Was ist hier Ursache, was ist Wirkung?

# %% [markdown] [loesung]
# **Erkenntnis:** Vor allem Eventtage haben hohe Preise **und** viele Buchungen (im Schnitt etwa
# 6 statt 4,6 pro Tag), Sommertage liegen leicht darüber, Alltagstage am niedrigsten. Innerhalb einer Tagesart steigen die Verkäufe
# nicht mit dem Preis. Das Hotel erhöht die Preise, **wenn die Nachfrage ohnehin hoch ist**.
# Ursache und Wirkung sind vertauscht: Nicht der Preis lockt Gäste an, sondern die hohe Nachfrage
# führt zum hohen Preis. Das nennt man **Scheinkorrelation**; die Tagesart ist die versteckte
# dritte Größe, die beides beeinflusst.

# %% [markdown]
# ### Aufgabe 3.4: Verkäufe sind nicht Nachfrage · ⏱ ca. 10 Min.
#
# Es gibt ein zweites Problem. An manchen Tagen ist eine Kategorie ausgebucht und das Hotel
# nimmt keine neuen Anreisen mehr an. Das steht in der Spalte `closed_to_arrival` (`True`/`False`).
#
# **Mini-Beispiel: Anteil mit `mean`.** Bei `True`/`False` zählt pandas `True` als 1 und `False` als 0.
# Der Mittelwert ist deshalb der **Anteil** der `True`-Werte.

# %%
demo_closed = pd.Series([True, False, False, True])
print("Anzahl True:", demo_closed.sum())
print("Anteil True:", demo_closed.mean())

# %%
# TODO: Berechnet den Anteil der Tage, an denen keine Anreise mehr möglich war.
### LÖSUNG
share_closed = daily["closed_to_arrival"].mean()
### LÜCKE
share_closed = daily["closed_to_arrival"].___()
### ENDE
print(f"Anteil geschlossener Tage: {share_closed:.1%}")

# %%
check_closed_share(share_closed)

# %% [markdown]
# Wie viele Buchungen gibt es an geschlossenen und offenen Tagen, je Zimmerkategorie?
# Nutzt wieder `pivot_table`: Zeilen sind die Kategorien, Spalten sind offen/geschlossen.

# %%
# TODO: Setzt die Spalte ein, nach der ihr offene und geschlossene Tage trennen wollt.
### LÖSUNG
closed_table = daily.pivot_table(index="category", columns="closed_to_arrival", values="bookings", aggfunc="mean")
### LÜCKE
closed_table = daily.pivot_table(index="category", columns=___, values="bookings", aggfunc="mean")
### ENDE
closed_table.round(1)

# %% [markdown]
# 🤔 Sagt die Zahl der Buchungen an geschlossenen Tagen, wie viele Gäste gern gekommen wären?

# %% [markdown] [loesung]
# **Erkenntnis:** Nein. An geschlossenen Tagen sind die Verkäufe **gedeckelt**: Mehr Zimmer gab es nicht.
# Wie viele Gäste zusätzlich gebucht hätten, bleibt unsichtbar. Verkäufe sind also nicht dasselbe
# wie Nachfrage. Gerade an Tagen mit hoher Nachfrage (und hohen Preisen) unterschätzen wir sie.

# %% [markdown]
# ### Aufgabe 3.5: Eine faire Preiskurve · ⏱ ca. 15 Min.
#
# Für eine faire Aussage brauchen wir Tage, an denen der Preis **nicht** von der Nachfrage abhängt.
# Schaut euch dazu noch einmal die Spalten von `daily` und die Werte von `price_source` an.

# %%
print(daily.columns.tolist())
daily["price_source"].value_counts()

# %% [markdown]
# Neben `'dynamic'` gibt es `'test'`. An diesen Tagen hat das Hotel den Preis **zufällig** gewählt,
# zum Beispiel per Losverfahren, ganz egal ob Messe, Sommer oder Alltag. Das ist ein **Experiment**,
# wie ein A/B-Test bei einem Online-Shop: Weil der Zufall entscheidet, sind teure und günstige Testtage
# im Mittel gleich „gute“ Tage. Unterschiede bei den Verkäufen kommen dann vom Preis selbst.
#
# **Mini-Beispiel `query`:** Die Bedingung steht als Text in Anführungszeichen. Ein Textwert
# darin bekommt **einfache** Anführungszeichen.

# %%
demo = pd.DataFrame({"fruit": ["Apfel", "Birne", "Apfel"], "price": [1.0, 1.5, 1.2]})
demo.query("fruit == 'Apfel'")

# %%
# TODO: Behaltet nur die Tage mit zufälligem Preistest.
#       Der Wert gehört in einfache Anführungszeichen innerhalb des Textes.
### LÖSUNG
test = daily.query("price_source == 'test'")
### LÜCKE
test = daily.query("price_source == ___")
### ENDE
len(test)

# %%
check_test_days(test)

# %% [markdown]
# Jetzt die Kurve: mittlere Buchungen je Testtag für jeden Wert von `r`.
#
# **Mini-Beispiel `agg` mit Namen:** `agg(neuer_name=("spalte", "funktion"))` rechnet je Gruppe
# eine Kennzahl und gibt der Ergebnisspalte gleich einen sprechenden Namen.

# %%
demo = pd.DataFrame({"r": [0.8, 0.8, 1.0, 1.0], "bookings": [4, 6, 2, 3]})
demo.groupby("r").agg(rooms=("bookings", "mean"))

# %%
# TODO: Berechnet je Preisstufe r die mittlere Zahl der Buchungen.
### LÖSUNG
curve = test.groupby("r").agg(rooms=("bookings", "mean"))
### LÜCKE
curve = test.groupby("r").agg(rooms=("bookings", ___))
### ENDE
curve.head()

# %%
curve["rooms"].plot(
    marker="o",
    title="Preistest: Preis gegen Verkäufe",
    xlabel="r (Angebotspreis / Listenpreis)",
    ylabel="Buchungen je Testtag",
)
plt.show()

# %% [markdown]
# 🤔 Vergleicht mit dem Bild aus Aufgabe 3.2. Was ist anders?

# %% [markdown] [loesung]
# **Erkenntnis:** Auf den Testtagen fällt die Kurve: Je teurer, desto weniger Buchungen.
# Nur hier hängt der Preis nicht von der Nachfrage ab, deshalb zeigt nur diese Kurve,
# wie Gäste wirklich auf den Preis reagieren.

# %% [markdown]
# ### Aufgabe 3.6: Der Umsatzberg · ⏱ ca. 10 Min.
#
# Ein niedriger Preis bringt viele Buchungen, aber wenig Geld je Zimmer. Ein hoher Preis bringt viel
# Geld je Zimmer, aber wenige Buchungen. Umsatz ist **Preis mal Menge**.
# Wir rechnen in Vielfachen des Listenpreises: Umsatz je Testtag = `r` × `rooms`.
# Die Preisstufe `r` steht im Index von `curve` (`curve.index`).
#
# **Mini-Beispiel `max` und `idxmax`:** `max()` liefert den größten **Wert**,
# `idxmax()` liefert die **Stelle** (den Index), an der er steht.

# %%
demo = pd.Series([3.0, 7.0, 5.0], index=[0.8, 0.9, 1.0])
print("größter Wert:   ", demo.max())
print("an der Stelle r:", demo.idxmax())

# %%
# TODO: Umsatz = Preis mal Menge. Der Preis steckt im Index.
### LÖSUNG
curve["revenue"] = curve.index * curve["rooms"]
### LÜCKE
curve["revenue"] = ___ * curve["rooms"]
### ENDE
curve["revenue"].plot(
    marker="o",
    title="Preistest: Umsatz je Preisstufe",
    xlabel="r (Angebotspreis / Listenpreis)",
    ylabel="Umsatz je Testtag (in Listenpreisen)",
)
plt.show()

# %%
# TODO: Bei welchem r liegt der Gipfel des Umsatzbergs?
### LÖSUNG
best_r = curve["revenue"].idxmax()
### LÜCKE
best_r = curve["revenue"].___()
### ENDE
best_r

# %%
check_revenue_peak(best_r)

# %% [markdown]
# 🤔 Liegt der beste Preis über oder unter dem Listenpreis? Was hätte die Hotelleitung
# mit dem Bild aus Aufgabe 3.2 entschieden?

# %% [markdown] [loesung]
# **Erkenntnis:** Der Umsatz hat einen Berg. Der Gipfel liegt etwa bei `r` = 0,85 bis 0,9,
# also etwas **unter** dem Listenpreis. Teurer verliert zu viele Gäste, billiger verschenkt Geld.
# Mit dem Bild aus dem Regelbetrieb hätte die Hotelleitung die Preise erhöht und Umsatz verloren.

# %% [markdown]
# ### Aufgabe 3.7: Gilt das für alle Gäste? · ⏱ ca. 20 Min.
#
# In Block 1 habt ihr die Gäste in `business` und `leisure` eingeteilt. Reagieren beide Gruppen
# gleich auf den Preis? Dafür brauchen wir die einzelnen Aufenthalte auf Testtagen.
#
# Der erste Schritt ist vorgegeben: Wir verbinden jeden Aufenthalt aus `stays` mit seinem Testtag
# (gleiche Kategorie, Anreise = Testtag) und holen uns so das `r`. Ein normaler (`inner`) Merge
# genügt, denn Aufenthalte an Nicht-Testtagen wollen wir hier gar nicht.

# %%
if "segment" not in stays.columns:
    print("💡 In stays fehlt noch die Spalte segment. Löst zuerst die Segment-Aufgabe in Block 1,")
    print("   führt die Zelle dort aus und kommt dann hierher zurück.")
else:
    columns_needed = ["category_id", "arrival_date", "r"]
    test_stays = stays.merge(
        test[columns_needed],
        left_on=["category_id", "checkin"],
        right_on=["category_id", "arrival_date"],
    )
    # Wie viele Testtage gab es je Preisstufe? Damit rechnen wir gleich "je Testtag".
    days_per_r = test.groupby("r").size()
    print("Aufenthalte auf Testtagen:", len(test_stays))
    print(test_stays["segment"].value_counts())

# %% [markdown]
# Für manche Preisstufen gibt es mehr Testtage als für andere. Damit der Vergleich fair ist,
# teilen wir die Zahl der Aufenthalte durch die Zahl der Testtage je `r`.
#
# **Mini-Beispiel `pivot_table` mit `count` und `div(..., axis=0)`:** `aggfunc="count"` zählt Zeilen.
# `div(series, axis=0)` teilt jede **Zeile** der Tabelle durch den passenden Wert der Series
# (gleicher Index).

# %%
demo = pd.DataFrame({
    "id": [1, 2, 3, 4, 5, 6],
    "r": [0.8, 0.8, 0.8, 1.2, 1.2, 1.2],
    "segment": ["leisure", "leisure", "business", "business", "business", "leisure"],
})
demo_days_per_r = pd.Series([2, 1], index=[0.8, 1.2])

demo_counts = demo.pivot_table(index="r", columns="segment", values="id", aggfunc="count")
print(demo_counts)
print()
print(demo_counts.div(demo_days_per_r, axis=0))

# %%
# TODO: Zählt die Aufenthalte je Preisstufe r, getrennt nach Gästegruppe.
### LÖSUNG
rooms_by_segment = test_stays.pivot_table(index="r", columns="segment", values="id", aggfunc="count")
### LÜCKE
rooms_by_segment = test_stays.pivot_table(index="r", columns=___, values="id", aggfunc="count")
### ENDE
rooms_by_segment = rooms_by_segment.div(days_per_r, axis=0)  # Aufenthalte je Testtag
rooms_by_segment.round(2).head()

# %% [markdown]
# Jetzt wieder Preis mal Menge, diesmal für beide Gruppen gleichzeitig.
# `mul(series, axis=0)` multipliziert jede Zeile mit dem passenden Wert, genau wie `div` oben teilt.

# %%
# TODO: Multipliziert jede Zeile mit ihrer Preisstufe r (steht im Index).
### LÖSUNG
revenue_by_segment = rooms_by_segment.mul(rooms_by_segment.index, axis=0)
### LÜCKE
revenue_by_segment = rooms_by_segment.mul(___, axis=0)
### ENDE
revenue_by_segment.plot(
    marker="o",
    title="Preistest: Umsatz je Gästegruppe",
    xlabel="r (Angebotspreis / Listenpreis)",
    ylabel="Umsatz je Testtag (in Listenpreisen)",
)
plt.show()

# %%
# TODO: Bei welchem r liegt der Gipfel für jede Gruppe? (idxmax arbeitet auf jeder Spalte einzeln)
### LÖSUNG
peaks = revenue_by_segment.idxmax()
### LÜCKE
peaks = revenue_by_segment.___()
### ENDE
peaks

# %%
check_segment_peaks(peaks)

# %% [markdown]
# 🤔 Warum reagieren die beiden Gruppen so unterschiedlich auf den Preis?
# Was bedeutet das für die Preisgestaltung des Hotels?

# %% [markdown] [loesung]
# **Erkenntnis:** Zwei Berge mit zwei Gipfeln. Leisure-Gäste haben ihr Optimum etwa bei `r` ≈ 0,9,
# also unter dem Listenpreis, Business-Gäste deutlich darüber, etwa bei `r` ≈ 1,3. Urlaubsgäste zahlen selbst und vergleichen Preise.
# Geschäftsreisende buchen kurzfristig, die Firma zahlt, der Termin steht fest. Ein einziger Preis
# für alle verschenkt Umsatz. Weil Business kurzfristig bucht, kann das Hotel über den Vorlauf
# unterschiedliche Preise anbieten (früh günstig, spät teurer).

# %% [markdown]
# ### Aufgabe 3.8: Brutto oder netto? · ⏱ ca. 15 Min.
#
# Bisher haben wir den Umsatz gezählt, den Gäste bezahlen (**brutto**). Buchungsportale verlangen aber
# eine Provision. Dem Hotel bleibt nur der **Nettobetrag**. In `test_stays` stehen dafür
# `rate_per_night` (Preis je Nacht), `nights` (Zahl der Nächte), `channel` (Vertriebskanal) und
# `commission_pct` (Provision in Prozent).
#
# **Mini-Beispiel brutto und netto:** Bei 20 % Provision bleiben 80 %, also `1 - 20 / 100 = 0.8`.

# %%
demo = pd.DataFrame({
    "rate_per_night": [100.0, 100.0, 120.0],
    "nights": [2, 2, 1],
    "commission_pct": [0.0, 20.0, 10.0],
})
demo["gross"] = demo["rate_per_night"] * demo["nights"]
demo["net"] = demo["gross"] * (1 - demo["commission_pct"] / 100)
demo

# %%
test_stays["gross"] = test_stays["rate_per_night"] * test_stays["nights"]

# TODO: Zieht die Provision ab. commission_pct ist in Prozent angegeben.
### LÖSUNG
test_stays["net"] = test_stays["gross"] * (1 - test_stays["commission_pct"] / 100)
### LÜCKE
test_stays["net"] = test_stays["gross"] * (1 - ___ / 100)
### ENDE
test_stays[["channel", "commission_pct", "gross", "net"]].head()

# %%
check_net(test_stays)

# %% [markdown]
# Jetzt die Umsatzkurve in Euro je Testtag, brutto und netto. Der Code ist vorgegeben.

# %%
money = test_stays.groupby("r")[["gross", "net"]].sum().div(days_per_r, axis=0)
money.plot(
    marker="o",
    title="Preistest: Umsatz je Testtag, brutto und netto",
    xlabel="r (Angebotspreis / Listenpreis)",
    ylabel="Euro je Testtag",
)
plt.show()

# %% [markdown]
# Und je Vertriebskanal: Wie viel vom Bruttoumsatz bleibt dem Hotel? Der Code ist vorgegeben.

# %%
channel_money = test_stays.groupby("channel")[["gross", "net"]].sum()
channel_money["kept_pct"] = 100 * channel_money["net"] / channel_money["gross"]
channel_money.round(1)

# %% [markdown]
# 🤔 Welcher Kanal kostet das Hotel am meisten? Warum lohnt es sich für ein Hotel,
# Gäste zur Direktbuchung zu bewegen?

# %% [markdown] [loesung]
# **Erkenntnis:** Die Provision unterscheidet sich stark: `direct` 0 %, `corporate` 5 %, `ota` 18 %.
# Bei einer Buchung über ein Portal bleiben nur 82 % beim Hotel. Gleicher Bruttoumsatz ist also nicht
# gleich viel wert. Für Preisentscheidungen zählt, was **nach** der Provision übrig bleibt.
