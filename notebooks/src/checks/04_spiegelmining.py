# Prüf-Funktionen für Block 4: SpiegelMining im Hotel
# Nutzt ok, hint und has_columns aus checks/00_base.py.


def check_guest_stays(guest_stays):
    if not hasattr(guest_stays, "columns"):
        hint("guest_stays sollte ein DataFrame sein.")
        return
    if not has_columns(guest_stays, ["guest_id", "hotel_id", "city_id", "checkin"], "guest_stays"):
        return
    if len(guest_stays) == 0:
        hint("guest_stays ist leer. Ist die Mindestzahl vielleicht zu hoch?")
        return
    smallest = guest_stays.groupby("guest_id").size().min()
    if smallest < 4:
        hint(f"Es gibt noch Gäste mit nur {smallest} Aufenthalten. Behaltet nur Gäste mit mindestens 4.")
        return
    if smallest > 4:
        hint("Der kleinste Gast hat mehr als 4 Aufenthalte. Habt ihr mit > statt >= oder mit einer zu großen Zahl gefiltert?")
        return
    ok(f"guest_stays enthält {guest_stays['guest_id'].nunique():,} Gäste mit mindestens 4 Aufenthalten.")


def check_pairs(pairs):
    if not hasattr(pairs, "columns"):
        hint("pairs sollte ein DataFrame sein.")
        return
    if not has_columns(pairs, ["a", "b", "hotel_id", "checkin"], "pairs"):
        return
    if len(pairs) == 0:
        hint("pairs ist leer. Merged ihr auf Hotel und Anreisetag?")
        return
    if (pairs["a"] == pairs["b"]).any():
        hint("pairs enthält noch Selbstpaare (a == b). Habt ihr query('a < b') angewendet?")
        return
    if not (pairs["a"] < pairs["b"]).all():
        hint("Es gibt Zeilen mit a > b. Damit zählt ihr jedes Paar doppelt.")
        return
    ok(f"pairs enthält {len(pairs):,} gemeinsame Anreisen, jedes Paar nur in einer Richtung.")


def check_top_pairs(top_pairs):
    if not hasattr(top_pairs, "is_monotonic_decreasing") or hasattr(top_pairs, "columns"):
        hint("top_pairs sollte eine Series sein: das Ergebnis von groupby(...).size().")
        return
    if len(top_pairs) == 0:
        hint("top_pairs ist leer.")
        return
    if len(top_pairs) > 10:
        hint("Zeigt nur die 10 häufigsten Paare (head(10)).")
        return
    if not top_pairs.is_monotonic_decreasing:
        hint("Die Paare sind nicht absteigend sortiert. Die häufigsten Paare gehören nach oben.")
        return
    ok(f"Die 10 häufigsten Paare stehen oben, Spitzenreiter mit {top_pairs.iloc[0]} gemeinsamen Anreisen.")


def check_candidates(candidates, pairs):
    if not hasattr(candidates, "columns"):
        hint("candidates sollte ein DataFrame sein.")
        return
    if not has_columns(candidates, ["a", "b"], "candidates"):
        return
    if len(candidates) == 0:
        hint("candidates ist leer. Ist der Filter zu streng?")
        return
    if candidates.duplicated(["a", "b"]).any():
        hint("Manche Paare kommen mehrfach vor. candidates sollte jedes Paar nur einmal enthalten.")
        return
    try:
        enough = pairs.groupby(["a", "b"])["hotel_id"].nunique()
    except Exception:
        ok(f"candidates enthält {len(candidates):,} Paare.")
        return
    expected = int((enough >= 4).sum())
    if len(candidates) > expected:
        hint("candidates enthält Paare mit weniger als 4 verschiedenen Hotels. Zählt ihr wirklich verschiedene Hotels?")
        return
    if len(candidates) < expected:
        hint("candidates enthält zu wenige Paare. Filtert auf mindestens 4 verschiedene Hotels (>=).")
        return
    ok(f"candidates enthält {len(candidates):,} Paare, die sich in mindestens 4 Hotels treffen.")


def check_result(result):
    if not hasattr(result, "columns"):
        hint("result sollte ein DataFrame sein.")
        return
    if not has_columns(result, ["a", "b", "meetings", "hotels"], "result"):
        return
    if len(result) == 0:
        hint("result ist leer. Prüft den Anti-Join: Bleiben die Zeilen mit _merge == 'left_only'?")
        return
    if (result["hotels"] < 4).any():
        hint("result enthält Paare mit weniger als 4 verschiedenen Hotels.")
        return
    if not result["meetings"].is_monotonic_decreasing:
        hint("result ist nicht absteigend nach meetings sortiert.")
        return
    if len(result) > 50:
        hint(f"result hat noch {len(result):,} Paare. Sind die Messetage wirklich herausgefiltert?")
        return
    ok(f"result enthält {len(result)} auffällige Paare. Schaut euch die obersten genau an.")


def check_lag_stats(lag_stats):
    if not hasattr(lag_stats, "columns"):
        hint("lag_stats sollte ein DataFrame sein.")
        return
    if not has_columns(lag_stats, ["leader", "follower", "trips", "hotels"], "lag_stats"):
        return
    if len(lag_stats) == 0:
        hint("lag_stats ist leer. Habt ihr das Datum um einen Tag verschoben?")
        return
    if (lag_stats["leader"] == lag_stats["follower"]).any():
        hint("lag_stats enthält Selbstpaare (leader == follower).")
        return
    if not lag_stats["trips"].is_monotonic_decreasing:
        hint("lag_stats ist nicht absteigend nach trips sortiert.")
        return
    ok(f"lag_stats enthält {len(lag_stats)} Paare mit versetzter Anreise in mindestens 4 Hotels.")
