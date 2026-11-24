# %% [markdown]
# ## Block 4: SpiegelMining im Hotel (Vertiefung)
#
# David Kriesel hat in seinem Vortrag „SpiegelMining“ aus öffentlich zugänglichen Artikeldaten erstaunlich viel
# herausgelesen: Wer schreibt mit wem, wer ist wann im Urlaub, wer verschwindet plötzlich aus der Redaktion?
# Geht so etwas auch mit Buchungsdaten?
#
# Eure Leitfrage für diesen Block: **Fällt euch in den Aufenthalten etwas auf, das kein Zufall sein kann?**
#
# Die Idee ist einfach: Wenn zwei Gäste auffällig oft **am selben Tag im selben Hotel** anreisen, kennen sie sich
# vermutlich. Wir gehen in kleinen Schritten vor:
#
# 1. Gäste mit genug Aufenthalten auswählen
# 2. Alle Paare bilden, die am selben Tag im selben Hotel anreisen
# 3. Paare zählen
# 4. und 5. Harmlose Erklärungen aussortieren
# 6. Namen dazuholen
# 7. Die Definition von „zusammen“ verändern
#
# Ihr braucht dafür nur `stays`, `guests` und `events` aus Block 1.

# %% [markdown]
# ### Aufgabe 4.1: Stammgäste auswählen · ⏱ ca. 10 Min.
#
# Wer nur ein- oder zweimal im Hotel war, kann kaum ein auffälliges Muster zeigen. Außerdem wird der Merge im
# nächsten Schritt sehr groß, wenn wir alle Gäste mitnehmen. Deshalb behalten wir nur Gäste mit **mindestens
# 4 Aufenthalten**.
#
# Dafür brauchen wir für **jede Zeile** die Anzahl der Aufenthalte ihres Gastes. Genau das macht
# `groupby(...).transform("size")`:
#
# - `agg("size")` fasst zusammen: **eine Zeile pro Gruppe**.
# - `transform("size")` rechnet dasselbe, schreibt das Ergebnis aber **in jede Zeile der Gruppe zurück**. Das
#   Ergebnis ist genauso lang wie die Tabelle und passt deshalb direkt als Filter.

# %%
# Mini-Beispiel: Gast 1 war dreimal da, Gast 2 einmal
toy_stays = pd.DataFrame({
    "guest_id": [1, 1, 1, 2],
    "checkin": pd.to_datetime(["2024-01-08", "2024-02-12", "2024-03-04", "2024-01-08"]),
})
print("agg: eine Zeile pro Gast")
print(toy_stays.groupby("guest_id")["checkin"].agg("size"))
print()
print("transform: eine Zeile pro Aufenthalt")
print(toy_stays.groupby("guest_id")["checkin"].transform("size"))

# %%
# TODO: Behaltet nur Gäste mit mindestens 4 Aufenthalten.
guest_stays = stays[["guest_id", "hotel_id", "city_id", "checkin"]]
stay_count = guest_stays.groupby("guest_id")["checkin"].transform("size")
### LÖSUNG
guest_stays = guest_stays[stay_count >= 4]
### LÜCKE
guest_stays = guest_stays[stay_count >= ___]
### ENDE
print(f"{len(guest_stays):,} Aufenthalte von {guest_stays['guest_id'].nunique():,} Gästen")

# %%
check_guest_stays(guest_stays)

# %% [markdown]
# ### Aufgabe 4.2: Wer reist am selben Tag an? · ⏱ ca. 20 Min.
#
# Jetzt suchen wir alle Paare von Gästen, die **im selben Hotel am selben Tag** anreisen. Der Trick:
# Wir mergen die Tabelle **mit sich selbst**. Damit wir die beiden Seiten auseinanderhalten können, benennen wir
# `guest_id` links in `a` und rechts in `b` um.
#
# Dabei entsteht zu viel:
#
# - **Selbstpaare:** Jeder Gast passt zu sich selbst, z. B. (1, 1).
# - **Doppelte Paare:** Das Paar (1, 2) taucht auch als (2, 1) auf.
#
# Beides entfernt `query("a < b")` in einem Schritt: (1, 1) fällt raus, weil 1 nicht kleiner als 1 ist, und von
# (1, 2) und (2, 1) bleibt nur (1, 2). Schaut es euch im Mini-Beispiel an.

# %%
# Mini-Beispiel: Gäste 1, 2 und 3 reisen am selben Tag in Hotel 10 an, Gast 4 in Hotel 20
toy_stays = pd.DataFrame({
    "guest_id": [1, 2, 3, 4],
    "hotel_id": [10, 10, 10, 20],
    "checkin": pd.to_datetime(["2024-05-06"] * 4),
})
toy_left = toy_stays.rename(columns={"guest_id": "a"})
toy_right = toy_stays.rename(columns={"guest_id": "b"})
toy_merged = toy_left.merge(toy_right, on=["hotel_id", "checkin"])
print(f"Nach dem Merge: {len(toy_merged)} Zeilen (mit Selbstpaaren und doppelten Paaren)")
print(toy_merged)
print()
print("Nach query('a < b'): jedes Paar genau einmal")
print(toy_merged.query("a < b"))

# %% [markdown]
# Jetzt mit den echten Daten. Die linke Seite behält `city_id`, die brauchen wir später noch.

# %%
# TODO: Merged auf die beiden Spalten, die "selbes Hotel, selber Tag" beschreiben.
left = guest_stays.rename(columns={"guest_id": "a"})
right = guest_stays.rename(columns={"guest_id": "b"})[["b", "hotel_id", "checkin"]]
### LÖSUNG
pairs = left.merge(right, on=["hotel_id", "checkin"]).query("a < b")
### LÜCKE
pairs = left.merge(right, on=[___, ___]).query("a < b")
### ENDE
print(f"{len(pairs):,} gemeinsame Anreisen")
pairs.head()

# %%
check_pairs(pairs)

# %% [markdown]
# ### Aufgabe 4.3: Paare zählen · ⏱ ca. 10 Min.
#
# Jede Zeile in `pairs` ist **eine** gemeinsame Anreise. Wie oft hat sich jedes Paar getroffen? Dafür gruppieren
# wir nach `a` und `b`, zählen mit `size()` und sortieren mit `sort_values(ascending=False)` absteigend.

# %%
# Mini-Beispiel: Paar (1, 2) trifft sich zweimal, Paar (3, 4) einmal
toy_pairs = pd.DataFrame({"a": [1, 1, 3], "b": [2, 2, 4], "hotel_id": [10, 20, 10]})
toy_pairs.groupby(["a", "b"]).size().sort_values(ascending=False)

# %%
# TODO: Sortiert so, dass die häufigsten Paare oben stehen.
### LÖSUNG
top_pairs = pairs.groupby(["a", "b"]).size().sort_values(ascending=False).head(10)
### LÜCKE
top_pairs = pairs.groupby(["a", "b"]).size().sort_values(ascending=___).head(10)
### ENDE
top_pairs

# %%
check_top_pairs(top_pairs)

# %% [markdown]
# Schaut euch das Spitzenpaar genauer an: In welchen Hotels treffen sich die beiden?

# %%
top_a, top_b = top_pairs.index[0]
top_meetings = pairs[(pairs["a"] == top_a) & (pairs["b"] == top_b)]
print(f"Paar {top_a} und {top_b}: {len(top_meetings)} gemeinsame Anreisen")
top_meetings["hotel_id"].value_counts()

# %% [markdown]
# 🤔 Ist das Spitzenpaar wirklich verdächtig? Welche harmlose Erklärung fällt euch ein, wenn sich zwei Menschen
# sehr oft, aber immer im selben Hotel treffen?

# %% [markdown] [loesung]
# **Erkenntnis:** Falsche Fährte! Ganz oben stehen Berater, die jede Woche im selben Haus arbeiten. Sie reisen
# oft am selben Tag an, weil sie für denselben Kunden arbeiten, nicht weil sie sich heimlich treffen. Eine hohe
# Anzahl allein sagt also noch nichts. Wir brauchen eine Kennzahl, die diese Fälle aussortiert.

# %% [markdown]
# ### Aufgabe 4.4: Filter 1 – nur Paare, die herumkommen · ⏱ ca. 15 Min.
#
# Berater treffen sich immer im selben Hotel. Ein Paar, das sich in **vielen verschiedenen Hotels** trifft, ist
# viel interessanter. Wir berechnen deshalb pro Paar zwei Kennzahlen auf einmal:
#
# - `meetings`: Anzahl gemeinsamer Anreisen (`"size"`)
# - `hotels`: Anzahl **verschiedener** Hotels (`"nunique"`)
#
# Das geht mit **benannter Aggregation**: `agg(neuer_name=("spalte", "funktion"), ...)`.

# %%
# Mini-Beispiel: Paar (1, 2) trifft sich dreimal in zwei Hotels, Paar (3, 4) zweimal im selben Hotel
toy_pairs = pd.DataFrame({
    "a": [1, 1, 1, 3, 3],
    "b": [2, 2, 2, 4, 4],
    "hotel_id": [10, 10, 20, 30, 30],
})
toy_pairs.groupby(["a", "b"]).agg(meetings=("hotel_id", "size"), hotels=("hotel_id", "nunique"))

# %%
# TODO: Zählt die verschiedenen Hotels pro Paar und behaltet Paare mit mindestens 4 Hotels.
### LÖSUNG
pair_stats = pairs.groupby(["a", "b"]).agg(meetings=("hotel_id", "size"), hotels=("hotel_id", "nunique"))
candidates = pair_stats[pair_stats["hotels"] >= 4].reset_index()[["a", "b"]]
### LÜCKE
pair_stats = pairs.groupby(["a", "b"]).agg(meetings=("hotel_id", "size"), hotels=("hotel_id", ___))
candidates = pair_stats[pair_stats["hotels"] >= ___].reset_index()[["a", "b"]]
### ENDE
print(f"{len(candidates):,} Paare treffen sich in mindestens 4 Hotels")
candidates.head()

# %%
check_candidates(candidates, pairs)

# %% [markdown]
# ### Aufgabe 4.5: Filter 2 – Messetage herausnehmen · ⏱ ca. 20 Min.
#
# Noch eine harmlose Erklärung: Auf einer **Messe** reisen tausende Menschen am selben Tag in dieselbe Stadt.
# Zwei Messebesucher treffen sich also zufällig, auch in vielen verschiedenen Hotels. Deshalb werfen wir alle
# gemeinsamen Anreisen an Messetagen raus.
#
# Wir wollen also die Zeilen behalten, die **keinen** Partner in der Messetabelle haben. Das nennt man
# **Anti-Join**. In pandas geht er in zwei Schritten:
#
# 1. `merge(..., how="left", indicator=True)` behält alle linken Zeilen und schreibt in die neue Spalte `_merge`,
#    ob es einen Partner gab (`both`) oder nicht (`left_only`).
# 2. `query("_merge == 'left_only'")` behält nur die Zeilen ohne Partner.

# %%
# Mini-Beispiel: In Stadt 1 ist am 6. Mai Messe
toy_meetings = pd.DataFrame({
    "city_id": [1, 1, 2],
    "checkin": pd.to_datetime(["2024-05-06", "2024-05-13", "2024-05-06"]),
})
toy_fairs = pd.DataFrame({"city_id": [1], "checkin": pd.to_datetime(["2024-05-06"])})
toy_marked = toy_meetings.merge(toy_fairs, how="left", on=["city_id", "checkin"], indicator=True)
print(toy_marked)
print()
print("Anti-Join: nur Zeilen ohne Messe")
print(toy_marked.query("_merge == 'left_only'"))

# %% [markdown]
# Zuerst bauen wir die Messetabelle. Sie ist vorgegeben: In `events` heißt die Datumsspalte `event_date`, wir
# benennen sie in `checkin` um, damit der Merge passt. Bundesweite Termine haben keine `city_id`; die werfen wir
# mit `dropna()` raus und machen `city_id` dann zu einer normalen Ganzzahl-Spalte.

# %%
fairs = events.query("event_type == 'trade_fair'")[["city_id", "event_date"]]
fairs = fairs.dropna().drop_duplicates()
fairs = fairs.rename(columns={"event_date": "checkin"}).astype({"city_id": "int64"})
print(f"{len(fairs):,} Messetage")
fairs.head()

# %% [markdown]
# Jetzt der Anti-Join. Wir nehmen nur die Treffen der Kandidaten aus Aufgabe 4.4 und werfen die Messetage raus.

# %%
# TODO: Ergänzt den Merge so, dass alle Treffen bleiben und die Spalte _merge entsteht.
meetings = pairs.merge(candidates, on=["a", "b"])
### LÖSUNG
marked = meetings.merge(fairs, how="left", on=["city_id", "checkin"], indicator=True)
### LÜCKE
marked = meetings.merge(fairs, how=___, on=["city_id", "checkin"], indicator=___)
### ENDE
outside_fairs = marked.query("_merge == 'left_only'")
print(f"{len(meetings):,} Treffen, davon {len(outside_fairs):,} außerhalb von Messen")

# %% [markdown]
# Zum Schluss zählen wir wie in Aufgabe 4.4 noch einmal, wenden Filter 1 erneut an und sortieren. Dieser Code ist
# vorgegeben.

# %%
result = outside_fairs.groupby(["a", "b"]).agg(meetings=("hotel_id", "size"), hotels=("hotel_id", "nunique"))
result = result[result["hotels"] >= 4].sort_values("meetings", ascending=False).reset_index()
result.head(15)

# %%
check_result(result)

# %% [markdown]
# ### Aufgabe 4.6: Wer steckt dahinter? · ⏱ ca. 10 Min.
#
# Bisher sehen wir nur Nummern. Holen wir Namen und Firmen dazu. Weil jedes Paar **zwei** Gäste hat, verbinden
# wir `guests` zweimal: einmal über `a`, einmal über `b`.
#
# - `join(andere_tabelle, on="spalte")` sucht den Wert aus `spalte` im **Index** der anderen Tabelle.
# - `add_suffix("_a")` hängt an alle Spaltennamen `_a` an, damit sich die Spalten der beiden Gäste nicht in die
#   Quere kommen.

# %%
# Mini-Beispiel
toy_result = pd.DataFrame({"a": [1, 2], "b": [3, 3], "meetings": [5, 2]})
toy_names = pd.DataFrame({"id": [1, 2, 3], "first_name": ["Ada", "Bo", "Cem"]}).set_index("id")
toy_result.join(toy_names.add_suffix("_a"), on="a").join(toy_names.add_suffix("_b"), on="b")

# %%
# TODO: Holt die Namen für den zweiten Gast dazu.
names_by_id = guests.set_index("id")[["first_name", "last_name", "company"]]
### LÖSUNG
named = result.join(names_by_id.add_suffix("_a"), on="a").join(names_by_id.add_suffix("_b"), on="b")
### LÜCKE
named = result.join(names_by_id.add_suffix("_a"), on="a").join(names_by_id.add_suffix("_b"), on=___)
### ENDE
named.head(15)

# %% [markdown]
# 🤔 Tauchen Personen mehrfach auf? Aus welchen Firmen kommen sie? Und welches Paar trifft sich auffällig oft?

# %% [markdown] [loesung]
# **Erkenntnis:** Zwei Geschichten stechen heraus.
#
# - **Das Kartell:** Vier Personen aus vier Konkurrenzfirmen treffen sich immer wieder in wechselnden Hotels.
#   Vier Personen ergeben 4 · 3 / 2 = **6 Paare**, deshalb tauchen dieselben Namen mehrfach auf.
# - **Das diskrete Duo:** Ein Paar mit **18 gemeinsamen Aufenthalten** in verschiedenen Städten, obwohl beide
#   immer getrennt buchen.
#
# Beides ist kein Beweis für etwas Verbotenes, aber kein Zufall. Genau so arbeitet SpiegelMining.
#
# Und die letzte Zeile mit nur 4 Treffen in 4 Hotels? Zwei ganz gewöhnliche Gäste ohne Firma, die zufällig gleich oft unterwegs waren. Genau solche Zufallstreffer werden in Block 5 zum Problem: Wer sehr viele Paare prüft, findet immer auch harmlose Leute.

# %% [markdown]
# ### Aufgabe 4.7: Andere Blickwinkel · ⏱ ca. 20 Min.
#
# Bisher hieß „zusammen“: selber Tag, selbes Hotel. Was, wenn jemand **nicht am selben Tag**, sondern immer
# **einen Tag später** anreist? Das finden wir, indem wir ein Datum verschieben, bevor wir mergen.
#
# `pd.Timedelta(days=1)` ist eine Zeitspanne von einem Tag. Man kann sie von Datumswerten abziehen oder dazuzählen.

# %%
# Mini-Beispiel
toy_dates = pd.Series(pd.to_datetime(["2024-03-01", "2024-03-04"]))
pd.DataFrame({"original": toy_dates, "minus_1_tag": toy_dates - pd.Timedelta(days=1)})

# %% [markdown]
# Die Idee: Wir nennen die eine Seite `leader` (reist zuerst an) und die andere `follower`. Beim `follower`
# ziehen wir einen Tag vom Anreisedatum ab. Reist der `follower` am 7. März an, steht dort danach der 6. März und
# passt im Merge genau zum `leader`, der am 6. März angereist ist.
#
# Hier gibt es kein `a < b`, denn die Reihenfolge ist jetzt wichtig: „B folgt A“ ist etwas anderes als „A folgt B“.
# Wir entfernen nur Selbstpaare mit `leader != follower`.

# %%
# TODO: Verschiebt die Anreise des follower um einen Tag nach vorne.
followers = guest_stays.rename(columns={"guest_id": "follower"})[["follower", "hotel_id", "checkin"]].copy()
### LÖSUNG
followers["checkin"] = followers["checkin"] - pd.Timedelta(days=1)
### LÜCKE
followers["checkin"] = followers["checkin"] - pd.Timedelta(days=___)
### ENDE
leaders = guest_stays.rename(columns={"guest_id": "leader"})
lagged = leaders.merge(followers, on=["hotel_id", "checkin"]).query("leader != follower")
print(f"{len(lagged):,} Anreisen genau einen Tag nach einem anderen Gast")

# %% [markdown]
# Die Auswertung kennt ihr schon aus den Aufgaben 4.4 und 4.6. Sie ist vorgegeben.

# %%
lag_stats = lagged.groupby(["leader", "follower"]).agg(trips=("hotel_id", "size"), hotels=("hotel_id", "nunique"))
lag_stats = lag_stats[lag_stats["hotels"] >= 4].sort_values("trips", ascending=False).reset_index()
lag_named = lag_stats.join(names_by_id.add_suffix("_leader"), on="leader")
lag_named = lag_named.join(names_by_id.add_suffix("_follower"), on="follower")
lag_named.head(5)

# %%
check_lag_stats(lag_stats)

# %% [markdown]
# 🤔 Was fällt euch beim obersten Paar auf? Welche Erklärungen gäbe es, harmlose und weniger harmlose?

# %% [markdown] [loesung]
# **Erkenntnis:** **Der Schatten.** Eine Person B reist **15-mal genau einen Tag nach** Person A an, immer im
# selben Hotel wie A, in wechselnden Städten. Mit der alten Definition „selber Tag“ war dieses Paar unsichtbar.
# Wie man „zusammen“ definiert, entscheidet also darüber, was man findet.

# %% [markdown]
# **Zum Weiterprobieren (freiwillig):** Verändert die Definition noch einmal. Ideen:
#
# - selbe **Stadt** statt selbes Hotel (`city_id` statt `hotel_id`)
# - zwei Tage statt einem Tag Abstand
# - mehr oder weniger als 4 verschiedene Hotels als Filter

# %%
# Platz für eure Experimente

