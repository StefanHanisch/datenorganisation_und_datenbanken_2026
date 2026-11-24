# %% [markdown]
# ## Block 5: Darf man das?
#
# In Block 4 habt ihr aus ganz gewöhnlichen Buchungsdaten Beziehungen zwischen Menschen herausgelesen. Technisch
# war das nicht schwer: ein paar Merges, ein paar Filter. Die spannendere Frage lautet: **Darf man das überhaupt?**

# %% [markdown]
# ### Aufgabe 5.1: Datenschutz und Fehlverdacht · ⏱ ca. 15 Min.
#
# Alle Personen in diesen Daten sind frei erfunden. Bei echten Gästen sähe die Lage anders aus:
#
# - **Zweckbindung (Art. 5 Abs. 1 lit. b DSGVO):** Buchungsdaten werden erhoben, um eine Übernachtung abzuwickeln.
#   Dürfen wir daraus Beziehungen zwischen Gästen ableiten? Auch die **Datenminimierung** (Art. 5 Abs. 1 lit. c
#   DSGVO) gehört in diese Diskussion: Es dürfen nur so viele Daten verarbeitet werden, wie für den Zweck nötig sind.
# - **Sensible Rückschlüsse (Art. 9 DSGVO):** Aus harmlosen Daten können Hinweise auf Gesundheit, Religion,
#   politische Haltung, Gewerkschaftszugehörigkeit oder sexuelle Orientierung entstehen. Solche Daten sind
#   besonders geschützt.
# - **Pseudonymisierung ist keine Anonymisierung:** Unser Export enthält keine E-Mail-Adressen, und selbst eine
#   reine `guest_id` oder ein `card_token` verknüpft weiterhin alle Aufenthalte einer Person. Pseudonymisierte
#   Daten bleiben personenbezogene Daten (Art. 4 Nr. 5 und Erwägungsgrund 26 DSGVO).
# - **Fehlverdacht:** Wer sehr viele Paare prüft, findet auch dann Auffälligkeiten, wenn gar nichts dahintersteckt.
#
# Wie viele Paare sind das eigentlich? Bei `n` Gästen kann jeder Gast mit `n - 1` anderen ein Paar bilden. Dabei
# zählt man jedes Paar doppelt (A mit B und B mit A), also teilt man durch 2:
#
# $$\text{Paare} = \frac{n \cdot (n - 1)}{2}$$
#
# Ihr kennt das schon vom Kartell: 4 Personen ergeben 4 · 3 / 2 = 6 Paare.

# %%
# TODO: Ergänzt die Formel für die Anzahl möglicher Paare.
guest_count = guests["id"].nunique()
### LÖSUNG
possible_pairs = guest_count * (guest_count - 1) // 2
### LÜCKE
possible_pairs = guest_count * (guest_count - 1) // ___
### ENDE
print(f"{guest_count:,} Gäste ergeben {possible_pairs:,} mögliche Paare.")
print(f"Schon bei einem Treffer auf eine Million Paare wären das {possible_pairs // 1_000_000:,} Verdachtsfälle.")

# %% [markdown]
# ### Diskussion
#
# Besprecht in kleinen Gruppen und notiert eure Antworten:
#
# 1. Wer in einem Hotelkonzern dürfte eine solche Auswertung starten, und wer müsste sie genehmigen?
# 2. Was würde passieren, wenn ein Treffer falsch ist und die betroffene Person davon erfährt?
# 3. Welche Spalten würdet ihr vor einem Export entfernen oder vergröbern, und welche Auswertungen gingen dann
#    nicht mehr?
# 4. Wo verläuft für euch die Grenze zwischen Preisoptimierung und Überwachung?

# %% [markdown]
# ## Geschafft!
#
# Ihr habt ein ganzes Analyse-Projekt mit echten Fragen durchgespielt. Ein kurzer Rückblick:
#
# - **pandas-Werkzeuge:** Tabellen filtern, neue Spalten berechnen, mit `groupby` und `agg` zusammenfassen, mit
#   `transform` Gruppenwerte in jede Zeile schreiben, mit `merge` Tabellen verbinden (auch mit sich selbst und als
#   Anti-Join), mit `pd.Timedelta` Datumswerte verschieben und Ergebnisse als Plot zeigen.
# - **SQL und pandas:** Vieles geht in beiden Welten. SQL rechnet direkt in der Datenbank, pandas ist bequem zum
#   Ausprobieren und Visualisieren.
# - **Vorsicht bei Zusammenhängen:** Ein Muster ist noch keine Ursache. Die Osterfalle, die Preisfalle und die
#   Berater in Block 4 zeigen: Erst wenn ihr harmlose Erklärungen ausgeschlossen habt, wird ein Befund belastbar.
# - **Datenschutz:** Was technisch einfach geht, ist nicht automatisch erlaubt. Zweck, Datenminimierung und das
#   Risiko eines Fehlverdachts gehören zu jeder Analyse dazu.
