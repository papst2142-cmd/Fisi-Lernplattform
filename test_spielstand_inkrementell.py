#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests fuer B-F-02 (0.63.2, Bauauftrag N4, FG-43): Nach einer Spielaktion wird
nur das neue Ereignis auf den vorhandenen Spielstand angewendet, statt alle
Ereignisse neu zu rechnen. Am Feierabend sichert ein Vergleich mit dem
vollstaendigen Neuaufbau ab (bei Abweichung gilt der Neuaufbau, Zeile in
fehler.log).

Erwartung (rot/gruen):
  ROT gegen 14b3bd4, gruen nach der Aenderung:
    test_aktion_rechnet_nicht_neu         eine Spielaktion baut den Spielstand
                                          nicht mehr ganz neu auf
    test_feierabend_heilt_und_meldet      verfaelschter Spielstand: Feierabend
                                          heilt (Neuaufbau gilt) und meldet in
                                          fehler.log, genau eine Zeile
  SCHUTZ (auch gegen 14b3bd4 gruen, Mutationen machen sie rot):
    test_bot_schritt_fuer_schritt         Bot-Laeufe: nach JEDER Aktion ist der
                                          Spielstand feldweise gleich dem
                                          Neuaufbau aus der Datenbank
    test_ereignisse_wie_mit_neuaufbau     derselbe Bot-Lauf mit Neuaufbau nach
                                          jedem _log (Verhalten bis 0.63.1)
                                          schreibt dieselben Ereignisse (Art,
                                          Daten, Zeitstempel, Reihenfolge) und
                                          dieselbe Bestenliste
    test_uhr_zurueck                      neues Ereignis sortiert vor aeltere
                                          (Uhr zurueckgestellt): gleich dem
                                          Neuaufbau
    test_abgleich_eingang                 fremde Zeilen (Abgleich) dazwischen:
                                          gleich dem Neuaufbau
    test_abgleich_waehrend_schreiben      fremde Zeile zwischen Stempel und
                                          eigenem Schreiben: Neuaufbau
    test_doppel_nach_abgleich             E-5-Doppel (fremdes Ticket, dann
                                          dasselbe lokal): zaehlt einmal, auch
                                          schrittweise (Merker ohne Feld im
                                          Spielstand, E-5 R6)
    test_alter_stand_bleibt               ein vorher gemerktes game.state bleibt
                                          unveraendert (neues Objekt wie bisher)
    test_oeffnen_schreibt_nichts          Oeffnen eines Spielstands aendert die
                                          Datenbank nicht und schreibt kein
                                          fehler.log

Code-Ordner waehlbar: SPIEL_CODE=<ordner> python test_spielstand_inkrementell.py
Nur Wegwerf-Datenbanken (eigener Temp-Ordner, eigenes HOME und FISI_DB_PATH).
Start:  python test_spielstand_inkrementell.py
"""

import datetime
import hashlib
import json
import os
import random
import shutil
import sys
import tempfile
import unittest
import uuid as _uuid

HERE = os.path.dirname(os.path.abspath(__file__))
CODE = os.path.abspath(os.environ.get("SPIEL_CODE") or HERE)
_HOME = tempfile.mkdtemp(prefix="fisi_spielstand_inkr_")
os.environ["HOME"] = _HOME
os.environ["FISI_DB_PATH"] = os.path.join(_HOME, "nie_benutzt.db")
sys.path.insert(0, CODE)

import fisi_core as core  # noqa: E402
import fisi_game as fg  # noqa: E402

assert os.path.dirname(os.path.abspath(fg.__file__)) == CODE, fg.__file__

_REAL_NOW = core.device_now
_REAL_UUID = fg.uuid.uuid4


# -- Vergleich (unabhaengig vom Code unter Test) ------------------------------

def _same(left, right):
    """Gleich samt Typ und Reihenfolge."""
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return list(left) == list(right) and all(_same(v, right[k]) for k, v in left.items())
    if isinstance(left, (list, tuple)):
        return len(left) == len(right) and all(map(_same, left, right))
    return left == right


def field_differences(state, rebuilt):
    """Felder, in denen sich zwei Spielstaende unterscheiden. Ausgenommen:
    Inhalte und der Zwischenspeicher _pressure; _topic_base nur gemeinsame
    Eintraege (Zwischenspeicher, der beim Abfragen gefuellt wird)."""
    a, b = vars(state), vars(rebuilt)
    out = [key for key in sorted(set(a) | set(b))
           if key not in ("content", "_pressure", "_topic_base") and
           (key not in a or key not in b or not _same(a[key], b[key]))]
    ta, tb = a.get("_topic_base", {}), b.get("_topic_base", {})
    if any(not _same(ta[k], tb[k]) for k in set(ta) & set(tb)):
        out.append("_topic_base")
    return out


def _read(path, mode="r"):
    with open(path, mode, **({} if "b" in mode else {"encoding": "utf-8"})) as handle:
        return handle.read()


def rebuilt_state(game):
    return fg.GameState(game.db.game_events(game.run), game.content)


# -- Kunstuhr und Bot ----------------------------------------------------------

class FakeClock:
    """Datenbank-Uhr: "sekunde" +1 s je Aufruf, "gleich" meist dieselbe
    Sekunde, "rueck" gelegentlich 30 s zurueck."""

    def __init__(self, mode, seed):
        self.mode = mode
        self.rng = random.Random("uhr|%s|%s" % (mode, seed))
        self.now = datetime.datetime(2026, 3, 2, 8, 0, 0,
                                     tzinfo=datetime.timezone(datetime.timedelta(hours=2)))
        self.calls = 0

    def __call__(self):
        self.calls += 1
        if self.mode == "gleich":
            if self.calls % 7 == 0:
                self.now += datetime.timedelta(seconds=1)
        elif self.mode == "rueck" and self.rng.random() < 0.03:
            self.now -= datetime.timedelta(seconds=30)
        else:
            self.now += datetime.timedelta(seconds=1)
        return self.now


def install(seed, clock):
    core.device_now = FakeClock(clock, seed)
    ids = random.Random("uuid|%s" % seed)
    fg.uuid.uuid4 = lambda: _uuid.UUID(int=ids.getrandbits(128))


def uninstall():
    core.device_now = _REAL_NOW
    fg.uuid.uuid4 = _REAL_UUID


def _try(fn, *args):
    try:
        fn(*args)
        return True
    except ValueError:
        return False


def play(game, seed, days, step, fast_firm=True):
    """Zufaelliger, aber fester Spielverlauf ueber die oeffentliche Spiel-API.
    step(label) nach jeder Aktion."""
    rng = random.Random("bot|%s" % seed)
    content = game.content
    game.set_profile("Bot%s" % seed, {"haut": "hell"},
                     rng.choice([fg.DIFF_EASY, fg.DIFF_NORMAL]))
    step("profil")
    if fast_firm:
        tasks = content["aufgaben"]
        rep = {k: 1 for k in fg.AXIS_KEYS}
        for i, task in enumerate(tasks):
            game._log(fg.EV_SOLVED, {"aufgabe": task["id"], "tag": 1 + i // 3,
                                     "richtig": True, "geld": 60, "reputation": rep})
            if i % 3 == 2 or i == len(tasks) - 1:
                game._log(fg.EV_DAY_END, {"tag": 1 + i // 3, "gehalt": 140})
            if i % 25 == 0:
                step("schnell")
        game._log(fg.EV_SOLVED, {"aufgabe": "bot-erspartes", "tag": game.state.day,
                                 "richtig": False, "geld": 400000})
        step("erspartes")
    for _day in range(days):
        for task in list(game.state.open_tickets()):
            state = game.state
            if not state.is_open(task["id"]):
                continue
            prepared = state.prepared_task(task)
            answer = fg.find_solution(prepared, state.available_parts(prepared))
            if task.get("austausch") and answer and \
                    answer.get("teil") not in state.available_parts(prepared):
                if _try(game.order_spare, task["id"], answer["teil"]):
                    step("ersatzteil")
                continue
            roll = rng.random()
            if roll < 0.05 and _try(game.defer, task["id"]):
                step("verschoben")
                continue
            if roll < 0.15 and task["typ"] == "auswahl":
                answer = [o for o in task["optionen"] if o != task["antwort"]][0]
            if _try(game.solve, task["id"], answer, rng.random() < 0.2):
                step("ticket")
        if rng.random() < 0.1:
            items = [i for i in fg.shop_items(content) if i.get("laden", True)]
            if _try(game.buy_furniture, rng.choice(items)["id"]):
                step("moebel")
        state = game.state
        if not state.firm and not state.founding_missing() and _try(game.found_firm, "Bot"):
            step("gruendung")
            for _ in range(2):
                if _try(game.expand):
                    step("ausbau")
        if game.state.firm:
            _firm_day(game, rng, step)
        state = game.state
        for decision in state.open_decisions():
            options = [o for o in decision["optionen"] if not o.get("problem")]
            if options and _try(game.decide, decision["id"], rng.choice(options)["id"]):
                step("entscheidung")
        if _try(game.end_day):
            step("feierabend")


def _firm_day(game, rng, step):
    content = game.content
    for item in fg.applicants(game.state, content):
        if len(game.state.staff) < game.state.capacity and rng.random() < 0.4 and \
                _try(game.hire, item["id"]):
            step("einstellung")
    state = game.state
    if state.staff and rng.random() < 0.05 and _try(game.fire, sorted(state.staff)[0]):
        step("entlassung")
    state = game.state
    if state.staff and rng.random() < 0.1 and \
            _try(game.train, rng.choice(sorted(state.staff)), rng.choice(fg.CAT_ORDER)):
        step("weiterbildung")
    for inquiry in game.state.inquiries():
        if inquiry.get("ergebnis"):
            continue
        markup = rng.choice(fg.offer_rules(content)["zuschlaege"])
        answer = fg.find_solution(fg.inquiry_task(inquiry, markup, content))
        if _try(game.send_offer, inquiry["id"], markup, answer):
            step("angebot")
    for ticket in game.state.customer_tickets():
        if ticket.get("an"):
            continue
        options = [o for o in fg.ticket_candidates(game.state, ticket, game.firm_levels(),
                                                   content) if not o["problem"]]
        if options and _try(game.delegate, ticket["id"],
                            max(options, key=lambda o: o["chance"])["an"]):
            step("verteilt")
    if rng.random() < 0.08 and _try(game.take_loan, 10000, 100, fg.FREE_LOAN):
        step("kredit")
    if rng.random() < 0.05:
        rooms = [r for r in fg.room_status(game.state, content) if not r["problem"]]
        if rooms and _try(game.build_room, rooms[0]["id"]):
            step("raum")


# -- Tests ----------------------------------------------------------------------

class _Base(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.mkdtemp(prefix="inkr_", dir=_HOME)
        self.db = core.DBManager(os.path.join(self.folder, "spiel.db"))

    def tearDown(self):
        uninstall()
        shutil.rmtree(self.folder, ignore_errors=True)

    def assert_like_rebuild(self, game, label=""):
        diff = field_differences(game.state, rebuilt_state(game))
        self.assertEqual(diff, [], "Unterschied zum Neuaufbau nach %s" % label)


class SchrittweiseTest(_Base):
    def test_bot_schritt_fuer_schritt(self):
        """Nach JEDER Aktion: Spielstand feldweise = Neuaufbau (drei Startwerte,
        drei Uhr-Arten, Gruendung, Personal, Angebote, Kundentickets, Kredite)."""
        for seed, clock, days in (("a", "sekunde", 12), ("b", "gleich", 12),
                                  ("c", "rueck", 12)):
            with self.subTest(seed=seed, clock=clock):
                install(seed, clock)
                db = core.DBManager(os.path.join(self.folder, "bot_%s.db" % seed))
                game = fg.Game(db, "PC")
                steps = []

                def step(label):
                    steps.append(label)
                    self.assert_like_rebuild(game, "Schritt %d (%s)" % (len(steps), label))
                play(game, seed, days, step)
                self.assertTrue(game.state.firm)
                self.assertGreater(len(steps), 60)
                uninstall()

    def test_ereignisse_wie_mit_neuaufbau(self):
        """Gleicher Lauf, einmal wie bis 0.63.1 (nach jedem _log voll neu
        gerechnet): dieselben Ereignisse und dieselbe Bestenliste."""
        def old_log(game, kind, data):
            game._ensure_run()
            game.db.log_game_event(kind, json.dumps(data, ensure_ascii=False), game.device,
                                   game.run)
            game.reload()
            if kind != fg.EV_ACHIEVEMENT:
                game.check_achievements(day_end=kind == fg.EV_DAY_END)

        results = []
        for mode in ("neu", "alt"):
            install("e", "gleich")
            db = core.DBManager(os.path.join(self.folder, "ev_%s.db" % mode))
            game = fg.Game(db, "PC")
            if mode == "alt":
                game._log = lambda kind, data, game=game: old_log(game, kind, data)
            play(game, "e", 10, lambda label: None)
            rows = db._execute("SELECT timestamp, utc_offset, typ, daten, geraet, lauf"
                               " FROM spiel_ereignisse ORDER BY id", fetch="all")
            records = [row[2:] for row in db.records()]
            results.append((rows, records, game.state.money, game.state.day))
            uninstall()
        self.assertGreater(len(results[0][0]), 600)
        self.assertEqual(results[0][0], results[1][0])
        self.assertEqual(results[0][1], results[1][1])
        self.assertEqual(results[0][2:], results[1][2:])

    def test_uhr_zurueck(self):
        install("u", "sekunde")
        game = fg.Game(self.db, "PC")
        game.set_profile("Uhr", {})
        game._log(fg.EV_DAY_END, {"tag": 1, "gehalt": 5000})
        clock = core.device_now
        clock.now -= datetime.timedelta(minutes=5)
        task = game.state.open_tickets()[0]
        game.solve(task["id"], fg.find_solution(game.state.prepared_task(task)), False)
        self.assert_like_rebuild(game, "Ticket mit frueherem Zeitstempel")
        stamps = [ts for ts, _k, _d in game.state.history]
        self.assertEqual(stamps, sorted(stamps))
        self.assertNotEqual(game.state.history[-1][1], fg.EV_SOLVED)

    def test_abgleich_eingang(self):
        install("g", "sekunde")
        game = fg.Game(self.db, "PC")
        game.set_profile("Abgleich", {})
        game._log(fg.EV_DAY_END, {"tag": 1, "gehalt": 5000})
        task = game.state.open_tickets()[0]
        # Zeile eines anderen Geraets (wie nach dem Abgleich), ohne reload
        self.db.log_game_event(fg.EV_DAY_END, json.dumps({"tag": 2, "gehalt": 7}), "Handy",
                               game.run)
        # Abzeichen-Pruefung aus: sie rechnet bei neuen Abzeichen ohnehin neu
        # und wuerde einen Fehler im schrittweisen Weg verdecken
        game.check_achievements = lambda *args, **kwargs: []
        game.solve(task["id"], fg.find_solution(game.state.prepared_task(task)), False)
        self.assert_like_rebuild(game, "Ticket nach fremder Zeile")
        self.assertEqual(game.state.days_done, 2)
        game._log(fg.EV_LAYOUT, {"wohnung": game.state.home_id, "moebel": {}, "boeden": {}})
        self.assert_like_rebuild(game, "Einrichtung danach")

    def test_abgleich_waehrend_schreiben(self):
        """Fremde Zeile genau zwischen Stempel und eigenem Schreiben (Abgleich
        im Hintergrund): voller Neuaufbau, nichts geht verloren."""
        install("w", "sekunde")
        game = fg.Game(self.db, "PC")
        game.set_profile("Wettlauf", {})
        game._log(fg.EV_DAY_END, {"tag": 1, "gehalt": 5000})
        game.check_achievements = lambda *args, **kwargs: []
        original = self.db.log_game_event

        def with_foreign(kind, data, device="", run=None):
            original(fg.EV_DAY_END, json.dumps({"tag": 2, "gehalt": 7}), "Handy", game.run)
            return original(kind, data, device, run)
        self.db.log_game_event = with_foreign
        try:
            game._log(fg.EV_LAYOUT, {"wohnung": game.state.home_id, "moebel": {},
                                     "boeden": {}})
        finally:
            self.db.log_game_event = original
        self.assert_like_rebuild(game, "Einrichtung mit fremder Zeile dazwischen")
        self.assertEqual(game.state.days_done, 2)

    def test_doppel_nach_abgleich(self):
        """E-5 auch schrittweise: Kommt dasselbe Ticket (gleiche Aufgabe, gleicher
        Tag) erst vom anderen Geraet und dann lokal, zaehlt es einmal."""
        install("d", "sekunde")
        game = fg.Game(self.db, "PC")
        game.set_profile("Doppel", {})
        task = game.state.open_tickets()[0]
        answer = fg.find_solution(game.state.prepared_task(task))
        payload = fg.evaluate(game.state.prepared_task(task), answer, False,
                              game.firm_levels(), game.state.day, game.content["balancing"],
                              game.state.available_parts(task), None, game.state.stock())
        self.db.log_game_event(fg.EV_SOLVED, json.dumps(payload, ensure_ascii=False), "Handy",
                               game.run)
        game.reload()
        money = game.state.money
        game._log(fg.EV_SOLVED, payload)
        self.assert_like_rebuild(game, "lokales Doppel")
        self.assertEqual(game.state.money, money)
        self.assertEqual(game.state.tickets_done, 1)

    def test_oeffnen_schreibt_nichts(self):
        install("o", "sekunde")
        game = fg.Game(self.db, "PC")
        play(game, "o", 3, lambda label: None)
        uninstall()
        path = self.db.db_path
        self.db = None
        game = None
        before = hashlib.sha256(_read(path, "rb")).hexdigest()
        db = core.DBManager(path)
        game = fg.Game(db, "PC")
        game.reload()
        self.assertTrue(game.state.firm)
        after = hashlib.sha256(_read(path, "rb")).hexdigest()
        self.assertEqual(before, after)
        self.assertFalse(os.path.exists(os.path.join(self.folder, core.ERROR_LOG_NAME)))


class LeistungUndAbsicherungTest(_Base):
    def test_aktion_rechnet_nicht_neu(self):
        """Eine Spielaktion (Ticket, Moebel) baut den Spielstand nicht mehr
        ganz neu auf (rot bis 0.63.1: jedes _log rechnete alle Ereignisse)."""
        install("l", "sekunde")
        game = fg.Game(self.db, "PC")
        game.set_profile("Leistung", {})
        game._log(fg.EV_DAY_END, {"tag": 1, "gehalt": 5000})
        items = [i for i in fg.shop_items(game.content) if i.get("laden", True)]
        # Vorlauf: erstes Ticket und erstes Moebel (dabei freigeschaltete
        # Abzeichen rechnet check_achievements wie bisher neu, ausserhalb B-F-02)
        task = game.state.open_tickets()[0]
        game.solve(task["id"], fg.find_solution(game.state.prepared_task(task)), False)
        game.buy_furniture(items[0]["id"])
        builds = []
        original = fg.GameState.__init__

        def counting(state, events, content=None):
            builds.append(len(events))
            original(state, events, content)
        fg.GameState.__init__ = counting
        try:
            task = game.state.open_tickets()[0]
            game.solve(task["id"], fg.find_solution(game.state.prepared_task(task)), False)
            game.buy_furniture(items[0]["id"])
        finally:
            fg.GameState.__init__ = original
        self.assertEqual(builds, [])
        self.assert_like_rebuild(game, "Ticket und Moebel")

    def test_alter_stand_bleibt(self):
        """Wie bis 0.63.1: Nach einer Aktion ist game.state ein neues Objekt;
        wer den Stand vorher gemerkt hat, sieht ihn unveraendert."""
        install("k", "sekunde")
        game = fg.Game(self.db, "PC")
        game.set_profile("Kopie", {})
        game._log(fg.EV_DAY_END, {"tag": 1, "gehalt": 5000})
        before = game.state
        snapshot = json.dumps(sorted((k, repr(v)) for k, v in vars(before).items()
                                     if k != "content"))
        task = game.state.open_tickets()[0]
        game.solve(task["id"], fg.find_solution(game.state.prepared_task(task)), False)
        self.assertIsNot(game.state, before)
        self.assertEqual(json.dumps(sorted((k, repr(v)) for k, v in vars(before).items()
                                           if k != "content")), snapshot)
        self.assertNotEqual(game.state.handled, before.handled)
        self.assert_like_rebuild(game, "Ticket")

    def test_feierabend_heilt_und_meldet(self):
        """Absicherung im Betrieb: Weicht der schrittweise Spielstand ab, gilt
        am Feierabend der Neuaufbau, und genau eine Zeile geht nach fehler.log
        (neben der Datenbank)."""
        install("h", "sekunde")
        game = fg.Game(self.db, "PC")
        game.set_profile("Heilen", {})
        game._log(fg.EV_DAY_END, {"tag": 1, "gehalt": 5000})
        task = game.state.open_tickets()[0]
        game.solve(task["id"], fg.find_solution(game.state.prepared_task(task)), False)
        game.state.money += 777        # kuenstlich verfaelscht (kein Ereignis)
        for task in game.state.open_tickets():
            game.defer(task["id"])
        game.end_day()
        self.assert_like_rebuild(game, "Feierabend")
        self.assertEqual(game.state.money, rebuilt_state(game).money)
        log = os.path.join(self.folder, core.ERROR_LOG_NAME)
        self.assertTrue(os.path.exists(log))
        text = _read(log)
        self.assertEqual(text.count("Spiel: Der schrittweise berechnete Spielstand"), 1, text)
        self.assertIn("money", text)
        # Ohne Abweichung kein weiterer Eintrag
        for task in game.state.open_tickets():
            game.defer(task["id"])
        game.end_day()
        self.assertEqual(_read(log), text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
