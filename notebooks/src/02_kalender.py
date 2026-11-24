# %% [markdown]
# ## Block 2: Kalender-Detektive
#
# Ein Hotel lebt vom Kalender: Feiertage, Messen, Feste und Turniere verschieben die Nachfrage. In diesem Block werdet ihr zu Detektiv*innen und prüft, ob hinter auffälligen Zahlen ein Termin steckt.
#
# **Wichtig:** Die Termine in `events` (Tabelle `calendar_events`) sind real. Ihre Effekte auf unsere Buchungen sind synthetisch erzeugt.
#
# Ihr arbeitet mit den DataFrames aus Block 1: `stays` (bestätigte Aufenthalte mit `month`, `year`, `checkin`, `city_id`, …), `events`, `reservations` und `guests`.

# %% [markdown]
# ### Aufgabe 2.1: Die Osterfalle · ⏱ ca. 20 Min.
#
# Das Management ist begeistert: Im März 2024 gab es deutlich mehr Anreisen als im März 2023. Ist das Hotel wirklich gewachsen? Oder steckt etwas anderes dahinter?
#
# Dafür brauchen wir eine Tabelle mit **einer Zeile je Monat** und **einer Spalte je Jahr**. In jeder Zelle steht die Zahl der Anreisen. So etwas baut `pivot_table`:
#
# - `index=` bestimmt die Zeilen,
# - `columns=` bestimmt die Spalten,
# - `values=` ist die Spalte, die ausgewertet wird,
# - `aggfunc=` sagt, wie: `"count"` zählt, `"sum"` summiert, `"mean"` bildet den Mittelwert.
#
# **Mini-Beispiel:** Ein Spielzeug-Hotel mit fünf Anreisen.

# %%
toy = pd.DataFrame({
    "id": [1, 2, 3, 4, 5],
    "month": [3, 3, 4, 3, 4],
    "year": [2023, 2024, 2023, 2024, 2024],
})
toy.pivot_table(index="month", columns="year", values="id", aggfunc="count")

# %% [markdown]
# Lest die Tabelle: Im März (Zeile 3) 2024 gab es zwei Anreisen, im April (Zeile 4) 2023 eine.
#
# Jetzt dasselbe mit den echten Daten. Die Zeilen sind die Monate, die Spalten die Jahre.

# %%
# TODO: Welche Spalte von stays gehört in die Spalten der Tabelle?
### LÖSUNG
monthly = stays.pivot_table(index="month", columns="year", values="id", aggfunc="count")
### LÜCKE
monthly = stays.pivot_table(index="month", columns=___, values="id", aggfunc="count")
### ENDE
monthly

# %%
check_monthly(monthly)

# %% [markdown]
# Wir zeichnen nur die vollständigen Jahre 2023 bis 2025. Die Liste `years` enthält nur Jahre, die es in `monthly` wirklich gibt.

# %%
years = [y for y in [2023, 2024, 2025] if y in monthly.columns]
monthly[years].plot(marker="o", title="Anreisen je Monat", xlabel="Monat", ylabel="Anreisen")

# %% [markdown]
# Seht ihr den Sprung im März 2024? Detektiv-Frage: Welcher Feiertag wandert jedes Jahr durch den Kalender? Ostern!
#
# Mit `query` filtert ihr Zeilen mit einer Bedingung in Anführungszeichen. Texte stehen darin in einfachen Anführungszeichen `'…'`. Mit `@` greift ihr auf eine Python-Variable zu.
#
# **Mini-Beispiel:**

# %%
toy_events = pd.DataFrame({
    "name": ["Neujahr", "Ostermontag", "Karneval", "Ostermontag"],
    "event_date": pd.to_datetime(["2023-01-01", "2023-04-10", "2023-02-16", "2024-04-01"]),
})
wanted = ["Neujahr", "Karneval"]
display(toy_events.query("name == 'Ostermontag'"))
toy_events.query("name in @wanted")

# %% [markdown]
# Jetzt schlagt ihr in `events` nach, auf welches Datum der Ostermontag in den einzelnen Jahren fiel.

# %%
# TODO: Ergänzt den Namen des Feiertags (in einfachen Anführungszeichen).
### LÖSUNG
easter = events.query("name == 'Ostermontag'")[["event_date", "name"]]
### LÜCKE
easter = events.query("name == ___")[["event_date", "name"]]
### ENDE
easter

# %% [markdown]
# Ostern 2024 lag sehr früh: Ostersonntag war der 31. März. Viele Osterurlaube fielen also in den März statt in den April. Vergleicht März und April einzeln:

# %%
monthly.loc[[3, 4], years]

# %% [markdown]
# Und jetzt März und April **zusammen**. `.sum()` addiert die beiden Zeilen je Jahr. Ein Ostereffekt kann so nicht mehr zwischen den Monaten hin- und herspringen.

# %%
monthly.loc[[3, 4], years].sum()

# %% [markdown]
# 🤔 Ist das Hotel im März 2024 wirklich gewachsen? Was würdet ihr dem Management sagen?

# %% [markdown] [loesung]
# **Erkenntnis:** Ostern 2024 lag im März (Ostermontag am 1.4.2024), in den Jahren 2023 und 2025 dagegen im April. Die Osterurlaube haben sich nur vom April in den März verschoben. März und April zusammen zeigen kein echtes Wachstum. Vergleicht deshalb bei wandernden Feiertagen immer passende Zeiträume, nicht einzelne Kalendermonate.

# %% [markdown]
# ### Aufgabe 2.2: Event-Study · ⏱ ca. 30 Min.
#
# Bringen Messen und Feste dem Hotel wirklich mehr Gäste? Ein einzelnes Jahr ist oft verrauscht. Deshalb machen wir eine **Event-Study**:
#
# 1. Wir legen alle Ausgaben eines Events übereinander, zum Beispiel das Oktoberfest 2023, 2024 und 2025.
# 2. **Tag 0** ist jeweils der erste Eventtag. Tag −3 heißt: drei Tage vorher, Tag 5: fünf Tage danach.
# 3. Für jeden Tag zählen wir die Anreisen in der Stadt des Events.
# 4. Zum Schluss teilen wir durch den Durchschnitt der **14 Tage davor**. Eine 1,0 heißt dann „normal“, eine 2,0 „doppelt so viele Anreisen wie sonst“.
#
# Wir gehen in kleinen Schritten vor. Zuerst wählen wir die Events aus.

# %%
names = ["Oktoberfest", "Hannover Messe", "Frankfurter Buchmesse", "gamescom", "Karneval"]
selected = events.query("name in @names").copy()
selected.head()

# %% [markdown]
# Ein Event steht in `events` mit **einer Zeile je Tag**. Uns interessiert aber nur der erste Tag jeder Ausgabe.
#
# Noch ein technisches Detail: `events["city_id"]` hat den Typ `Int64` (großes I). Dieser Typ erlaubt fehlende Werte `<NA>`, z. B. für bundesweite Feiertage. In `stays` ist `city_id` ein normales `int64`. Damit `merge` später passt, entfernen wir fehlende Werte mit `dropna` und wandeln den Typ mit `astype` um.

# %%
selected = selected.dropna(subset=["city_id"]).astype({"city_id": "int64"})
selected["year"] = selected["event_date"].dt.year
# Erster Tag je Event, Stadt und Jahr
starts = selected.groupby(["name", "city_id", "year"], as_index=False)["event_date"].min()
starts

# %% [markdown]
# Jetzt zählen wir die Anreisen je Stadt und Tag. `groupby(...).size()` zählt die Zeilen je Gruppe.

# %%
city_days = stays.groupby(["city_id", "checkin"]).size().rename("bookings").reset_index()
city_days.head()

# %% [markdown]
# Mit `merge` hängen wir an jeden Stadt-Tag die Starttermine der Events in dieser Stadt. Eine Zeile sagt dann z. B.: „In München kamen am 10.9.2024 so viele Gäste an, und das Oktoberfest 2024 begann am 21.9.2024.“

# %%
study = city_days.merge(starts, on="city_id")
study.head()

# %% [markdown]
# Der Kern der Event-Study ist der **Abstand in Tagen** zwischen Anreise und Eventstart. Zieht man zwei Datumswerte voneinander ab, entsteht eine Zeitdauer (`Timedelta`). `.dt.days` macht daraus eine ganze Zahl.
#
# **Mini-Beispiel:**

# %%
toy_days = pd.DataFrame({
    "checkin": pd.to_datetime(["2024-09-18", "2024-09-21", "2024-09-25"]),
    "event_date": pd.to_datetime(["2024-09-21", "2024-09-21", "2024-09-21"]),
})
toy_days["offset"] = (toy_days["checkin"] - toy_days["event_date"]).dt.days
toy_days

# %%
# TODO: Von welchem Datum zieht ihr ab? Tag 0 soll der erste Eventtag sein.
### LÖSUNG
study["offset"] = (study["checkin"] - study["event_date"]).dt.days
### LÜCKE
study["offset"] = (study["checkin"] - study[___]).dt.days
### ENDE
study[["checkin", "event_date", "offset"]].head()

# %% [markdown]
# Wir behalten nur das Fenster von 14 Tagen vor bis 21 Tage nach dem Eventstart.

# %%
study = study.query("-14 <= offset <= 21")
study["offset"].describe()

# %% [markdown]
# Jetzt legen wir die Jahre übereinander: Eine Zeile je `offset`, eine Spalte je Event, in der Zelle der Mittelwert der Anreisen über alle Jahre.

# %%
curve = study.pivot_table(index="offset", columns="name", values="bookings", aggfunc="mean")
curve.head()

# %% [markdown]
# Die Events finden in unterschiedlich großen Städten statt. Damit man sie vergleichen kann, teilen wir jede Spalte durch ihren eigenen Normalwert, den Durchschnitt der Tage −14 bis −1.
#
# `div` teilt jede Spalte durch die passende Zahl.
#
# **Mini-Beispiel:**

# %%
toy_curve = pd.DataFrame({"A": [10, 10, 30], "B": [2, 2, 3]}, index=[-2, -1, 0])
toy_base = toy_curve.loc[-2:-1].mean()
toy_curve.div(toy_base)

# %%
baseline = curve.loc[-14:-1].mean()
# TODO: Teilt die Kurve durch den Normalwert der 14 Tage davor.
### LÖSUNG
curve_rel = curve.div(baseline)
### LÜCKE
curve_rel = curve.div(___)
### ENDE
curve_rel.round(2).head()

# %%
check_event_curve(curve_rel)

# %%
ax = curve_rel.plot(title="Anreisen rund um Events (relativ zu den 14 Tagen davor)",
                    xlabel="Tage relativ zum Eventstart", ylabel="Anreisen (1 = normal)")
ax.axvline(0, color="grey", linestyle="--")

# %% [markdown]
# 🤔 Bei welchen Events steigen die Anreisen am stärksten? Fällt die Kurve nach dem Event wieder auf etwa 1 zurück?

# %% [markdown] [loesung]
# **Erkenntnis:** Rund um Messen und Feste steigen die Anreisen deutlich über das Niveau der 14 Tage davor, die Kurven liegen während der Eventtage klar über 1. Nach dem Event kehren sie etwa auf 1 zurück. Wie stark der Effekt ist, unterscheidet sich je Event. Für das Hotel heißt das: Eventtage sind planbar und gehören in die Preis- und Personalplanung.

# %% [markdown]
# ### Aufgabe 2.3: Euro 2024 · ⏱ ca. 20 Min.
#
# Vom 14. Juni bis 14. Juli 2024 fand die Fußball-Europameisterschaft in Deutschland statt. Haben die Hotels in den Austragungsorten davon profitiert?
#
# Ein einfacher Vergleich „Juni 2024 gegen Juni 2023“ reicht nicht, denn vielleicht lief 2024 überall besser. Deshalb vergleichen wir zwei Gruppen:
#
# - **Austragungsort**: Städte mit EM-Spielen,
# - **Vergleichsgruppe**: alle anderen Städte.
#
# Beide jeweils im Turnierzeitraum vom 14. Juni bis 14. Juli, relativ zu 2023. Warum nicht einfach die ganzen Monate Juni und Juli? Dann würden die Tage ohne Turnier den Effekt verwässern.
#
# Für die Einteilung braucht ihr zwei Werkzeuge:
#
# - `isin(liste)` prüft für jede Zeile, ob der Wert in der Liste vorkommt, und gibt `True`/`False` zurück.
# - `np.where(bedingung, wert_wenn_true, wert_wenn_false)` macht daraus Text.
#
# **Mini-Beispiel:**

# %%
toy_stays = pd.DataFrame({"city_id": [1, 2, 3, 2]})
toy_hosts = [2, 3]
toy_stays["is_host"] = toy_stays["city_id"].isin(toy_hosts)
toy_stays["group"] = np.where(toy_stays["is_host"], "Austragungsort", "Vergleichsgruppe")
toy_stays

# %% [markdown]
# Zuerst holen wir die Städte mit EM-Spielen aus `events`. Wieder entfernen wir fehlende Werte und wandeln in `int64` um.
#
# Für den Zeitraum nutzen wir einen kleinen Trick: `.dt.strftime("%m-%d")` macht aus jedem Datum Text wie `"06-14"` (Monat-Tag, ohne Jahr). Mit `.between("06-14", "07-14")` behalten wir dann in **jedem** Jahr genau den Turnierzeitraum.

# %%
hosts = events.query("name == 'Euro 2024'")["city_id"].dropna().astype("int64").unique()
in_window = stays["checkin"].dt.strftime("%m-%d").between("06-14", "07-14")
summer = stays[in_window].query("year in [2023, 2024, 2025]").copy()
hosts

# %%
# TODO: Welche Liste enthält die Austragungsorte?
### LÖSUNG
summer["group"] = np.where(summer["city_id"].isin(hosts), "Austragungsort", "Vergleichsgruppe")
### LÜCKE
summer["group"] = np.where(summer["city_id"].isin(___), "Austragungsort", "Vergleichsgruppe")
### ENDE
summer["group"].value_counts()

# %% [markdown]
# Jetzt zählen wir die Anreisen je Jahr und Gruppe und teilen durch das Jahr 2023. 2023 steht dann bei beiden Gruppen auf 1,0.

# %%
euro = summer.pivot_table(index="year", columns="group", values="id", aggfunc="count")
euro_rel = euro.div(euro.loc[2023])
euro_rel.round(2)

# %%
check_euro(euro_rel)

# %%
euro_rel.plot.bar(title="Anreisen 14.6.–14.7. relativ zu 2023", xlabel="Jahr", ylabel="Anreisen (2023 = 1)")

# %% [markdown]
# 🤔 Was passiert 2024 in den Austragungsorten im Vergleich zur Vergleichsgruppe? Und warum ist die Vergleichsgruppe wichtig?

# %% [markdown] [loesung]
# **Erkenntnis:** Während des Turniers 2024 liegen die Austragungsorte rund 7 % über 2023, die Vergleichsgruppe dagegen leicht darunter (etwa 0,99). 2025 fallen beide wieder auf ähnliche Werte. Hätten wir die ganzen Monate Juni und Juli genommen, wäre der Unterschied fast verschwunden: Ein zu grober Zeitraum verwässert einen Effekt. Die Vergleichsgruppe zeigt, was ohne EM passiert wäre: Nur der Unterschied zwischen den Gruppen geht auf das Turnier zurück, nicht ein allgemeiner Aufschwung.

# %% [markdown]
# ### Aufgabe 2.4: Vertiefung: Stornos und Familien · ⏱ ca. 15 Min.
#
# Diese Aufgabe ist freiwillig, falls ihr noch Zeit habt.
#
# **Wer storniert am häufigsten?** Dafür brauchen wir alle Reservierungen, auch die stornierten, also `reservations` statt `stays`.
#
# Ein Trick: Der Mittelwert einer `True`/`False`-Spalte ist der **Anteil** der `True`-Werte, denn `True` zählt als 1 und `False` als 0.
#
# **Mini-Beispiel:**

# %%
toy_res = pd.DataFrame({
    "channel": ["direct", "direct", "ota", "ota"],
    "status": ["confirmed", "cancelled", "cancelled", "cancelled"],
})
toy_cancelled = toy_res["status"] == "cancelled"
toy_cancelled.groupby(toy_res["channel"]).mean()

# %%
# TODO: Welcher Status steht für eine Stornierung?
### LÖSUNG
cancelled = reservations["status"] == "cancelled"
### LÜCKE
cancelled = reservations["status"] == ___
### ENDE
cancel_rate = cancelled.groupby(reservations["channel"]).mean()
cancel_rate.round(3)

# %%
check_cancel_rate(cancel_rate)

# %%
cancel_rate.plot.bar(title="Stornoquote je Buchungskanal", xlabel="Kanal", ylabel="Anteil storniert")

# %% [markdown]
# **Wann reisen Familien aus welchem Bundesland?** Wir nehmen Aufenthalte mit Kindern im Sommer 2025 und holen mit `merge` das Herkunfts-Bundesland `home_state` aus `guests`. `dt.isocalendar().week` liefert die Kalenderwoche. Hier gibt es nichts zu ergänzen, lest den Code und schaut euch den Plot an.

# %%
families = stays.query("children > 0 and year == 2025 and month in [6, 7, 8, 9]")
families = families.merge(guests[["id", "home_state"]], left_on="guest_id", right_on="id", suffixes=("", "_guest"))
families["week"] = families["checkin"].dt.isocalendar().week
family_weeks = families.pivot_table(index="week", columns="home_state", values="id", aggfunc="count")
family_weeks.plot(title="Anreisen von Familien je Kalenderwoche (Sommer 2025)",
                  xlabel="Kalenderwoche", ylabel="Anreisen")

# %% [markdown]
# 🤔 Warum haben die Bundesländer ihre Gipfel in unterschiedlichen Wochen? Was bedeutet das für ein Hotel, das Familien anspricht?

# %% [markdown] [loesung]
# **Erkenntnis:** Die Sommerferien beginnen je Bundesland zu unterschiedlichen Zeiten. Familien reisen vor allem in ihren Ferien, deshalb verschieben sich die Gipfel von Bundesland zu Bundesland. Ein Hotel kann Werbung und Familienangebote gezielt auf die Ferienzeiten der wichtigsten Herkunftsländer abstimmen. Bei den Stornos fällt der Kanal `ota` (Buchungsportale) mit der höchsten Quote auf. Das ist doppelt teuer, denn über Portale zahlt das Hotel auch die höchste Provision.
