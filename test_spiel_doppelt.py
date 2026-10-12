#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests fuer B-G-26 (Gruppe 5.5, 0.62.5): Derselbe Spielstand wird auf zwei
Geraeten offline weitergespielt und dann abgeglichen. Feierabend und
geloeste Tickets duerfen danach nicht doppelt zaehlen.

Konservative Regel (Nicos Auflage P-14): Uebersprungen wird nur, was
eindeutig doppelt ist - gleiche Ereignisart und gleiche Tagesangabe (beim
Ticket zusaetzlich dieselbe Aufgabe). Feierabende oder Tickets OHNE
Tagesangabe werden nicht geraten und zaehlen wie bisher.

Erwartung (rot/gruen):
  ROT auf v0.62.3, gruen nach der Aenderung (Klasse DoppeltTest):
    test_d5_block            Fall D5: 2 Tage, Geld 300, 2 Tickets (rot: 3, 450, 3)
    test_d5_verzahnt         D5 mit verzahnter Reihenfolge der Ereignisse
    test_ticket_falsch_doppelt   Strafe und Reputation einmal (rot: zweimal)
    test_ticket_richtig_doppelt  Belohnung, Lieferung, Lagerteile einmal
    test_feierabend_doppelt_miete  Gehalt minus Miete einmal, 1 Kontostand
    test_feierabend_doppelt_firma  Firmen-Feierabend (Umsatz, Kundenticket) einmal
    test_echte_api_zwei_geraete    echte Spiel-API, zwei Datenbanken, Abgleich
                                   der Zeilen: Stand wie Geraet A allein
  SCHUTZ, auf v0.62.3 ebenfalls gruen (Klasse SchutzTest):
    test_feierabende_ohne_tag_zaehlen        zwei Feierabende ohne Tag: 2 Tage
    test_ohne_tag_dann_mit_tag_zaehlen       ohne Tag, danach Tag 2: 2 Tage
    test_ungueltige_tagesangaben_zaehlen     "1", 0, true, 1.0: nicht geraten
    test_ticket_ohne_tag_doppelt_zaehlt      Ticket ohne Tag zweimal: zweimal
    test_gleiches_ticket_anderer_tag         gleiche Aufgabe an Tag 1 und 2: zweimal
    test_zwei_tickets_selber_tag             zwei Aufgaben an einem Tag: zweimal
    test_verschoben_doppelt_unveraendert     ticket_verschoben ist nicht Teil der
                                             Aenderung (zaehlt wie bisher doppelt)
    test_dreissig_tage_ein_geraet            30-Tage-Lauf, ein Geraet, echte API:
                                             Tage, Tickets, Geld unabhaengig nachgerechnet

Code-Ordner waehlbar (wie ABGLEICH_CODE in test_abgleich.py):
    SPIEL_CODE=<ordner mit dem Code> python test_spiel_doppelt.py
Ohne Angabe: der Ordner dieser Datei. Nur Wegwerf-Datenbanken (eigener
Temp-Ordner, eigenes HOME und FISI_DB_PATH).
Start:  python test_spiel_doppelt.py
"""

import os
import shutil
import sqlite3
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
CODE = os.path.abspath(os.environ.get("SPIEL_CODE") or HERE)
_HOME = tempfile.mkdtemp(prefix="fisi_spiel_doppelt_")
os.environ["HOME"] = _HOME
os.environ["FISI_DB_PATH"] = os.path.join(_HOME, "nie_benutzt.db")
sys.path.insert(0, CODE)

import fisi_core as core  # noqa: E402
import fisi_game as fg  # noqa: E402

assert os.path.dirname(os.path.abspath(fg.__file__)) == CODE, fg.__file__


def _ts(n):
    """Zeitstempel in fester Reihenfolge (eine Sekunde je Ereignis)."""
    return "2026-10-01 %02d:%02d:%02d" % (8 + n // 3600, (n // 60) % 60, n % 60)


def _events(*items):
    return [(_ts(index), kind, data) for index, (kind, data) in enumerate(items)]


def _solved(task, day, money=50, right=True, **extra):
    data = {"aufgabe": task, "geld": money, "richtig": right, "tag": day}
    data.update(extra)
    return (fg.EV_SOLVED, data)


def _day_end(day, salary=100, rent=0, **extra):
    data = {"tag": day, "gehalt": salary, "miete": rent}
    data.update(extra)
    return (fg.EV_DAY_END, data)


def _d5_start():
    """Wie g4_geraet.py spieltag:l2:1 (Teil 4, Szenario D5)."""
    return [_solved("g4-ticket-1", 1), _day_end(1)]


def _d5_day2():
    return [_solved("g4-ticket-2", 2), _day_end(2)]


class TempDB:
    def __init__(self):
        self.folder = tempfile.mkdtemp(dir=_HOME)
        self.path = os.path.join(self.folder, "spiel.db")

    def open(self):
        return core.DBManager(self.path)


def _play_day(game, rng_right=True):
    """Alle offenen Tickets bearbeiten (richtig, wenn eine Loesung bekannt
    ist, sonst leere Antwort), dann Feierabend. Liefert die Zahl der
    verschobenen Tickets (sollte 0 sein)."""
    deferred = 0
    for _ in range(60):
        todo = game.state.open_tickets()
        if not todo:
            break
        task = todo[0]
        answer = {}
        if rng_right:
            prepared = game.state.prepared_task(task)
            found = fg.find_solution(prepared, game.state.available_parts(prepared))
            if found is not None:
                answer = found
        try:
            game.solve(task["id"], answer, False)
        except ValueError:
            try:
                game.solve(task["id"], {}, False)
            except ValueError:
                game.defer(task["id"])
                deferred += 1
    game.end_day()
    return deferred


def _merge_rows(source_path, target_path):
    """Abgleich nachgestellt: Spielereignisse aus source, deren uid in target
    fehlt, mit ihrem Zeitstempel in target uebernehmen (so legt auch
    fisi_sync fremde Zeilen ab). Liefert die Zahl der uebernommenen Zeilen."""
    src = sqlite3.connect(source_path)
    dst = sqlite3.connect(target_path)
    try:
        cols = [row[1] for row in src.execute("PRAGMA table_info(spiel_ereignisse)")
                if row[1] != "id"]
        have = {row[0] for row in dst.execute("SELECT uid FROM spiel_ereignisse")}
        rows = [row for row in src.execute(
            "SELECT %s FROM spiel_ereignisse ORDER BY id" % ", ".join(cols))
            if row[cols.index("uid")] not in have]
        dst.executemany("INSERT INTO spiel_ereignisse (%s) VALUES (%s)" % (
            ", ".join(cols), ", ".join("?" * len(cols))), rows)
        dst.commit()
        return len(rows)
    finally:
        src.close()
        dst.close()


def _core_values(state):
    return {"tage": state.days_done, "tag": state.day, "geld": state.money,
            "tickets": state.tickets_done,
            "reputation": dict(state.reputation),
            "geloest": sorted(str(item) for item in state.solved),
            "kontostaende": list(state.balances)}


class DoppeltTest(unittest.TestCase):
    """ROT auf v0.62.3, gruen nach der Aenderung."""

    def test_d5_block(self):
        """Fall D5 (Teil 4): PC und Handy spielen Tag 2 offline, dann Abgleich.
        Reihenfolge nach dem Abgleich: erst alle Ereignisse des PCs, dann die des
        Handys. Soll: 2 Tage, Geld 300, 2 Tickets (v0.62.3: 3 Tage, 450, 3)."""
        state = fg.GameState(_events(*(_d5_start() + _d5_day2() + _d5_day2())))
        self.assertEqual((state.days_done, state.money, state.tickets_done), (2, 300, 2))
        self.assertEqual(state.day, 3)
        self.assertEqual([day for day, _money in state.balances], [1, 2])

    def test_d5_verzahnt(self):
        """D5, aber die Uhren der Geraete verzahnen die Ereignisse:
        Ticket PC, Ticket Handy, Feierabend PC, Feierabend Handy."""
        ticket, end = _d5_day2()
        state = fg.GameState(_events(*(_d5_start() + [ticket, ticket, end, end])))
        self.assertEqual((state.days_done, state.money, state.tickets_done), (2, 300, 2))

    def test_ticket_falsch_doppelt(self):
        """Dasselbe Ticket am selben Tag auf zwei Geraeten falsch geloest
        (wie g403b): Strafe und Reputationsverlust einmal."""
        wrong = _solved("hw-01", 1, money=-15, right=False,
                        reputation={"kompetenz": -4})
        single = fg.GameState(_events(wrong))
        double = fg.GameState(_events(wrong, wrong))
        self.assertEqual(double.money, single.money)
        self.assertEqual(double.money, -15)
        self.assertEqual(double.tickets_done, 1)
        self.assertEqual(double.reputation, single.reputation)
        self.assertEqual(double.book, single.book)

    def test_ticket_richtig_doppelt(self):
        """Richtig geloestes Ticket mit Lieferung und Teil aus dem Lager
        doppelt: Belohnung, Lieferung und verbautes Teil einmal."""
        stock = fg.GAME["hardware"].get("grundbestand", {})
        part_id = sorted(stock)[0] if stock else "teil-x"
        right = _solved("hw-02", 1, money=80, lieferung=[
            {"teil": "ram_ddr5_16", "menge": 1, "ankunft": 2, "haendler": "x"}],
            aus_lager=[part_id])
        single = fg.GameState(_events(right))
        double = fg.GameState(_events(right, right))
        self.assertEqual(double.money, 80)
        self.assertEqual(double.tickets_done, 1)
        self.assertEqual(double.deliveries, single.deliveries)
        self.assertEqual(double.used, single.used)

    def test_feierabend_doppelt_miete(self):
        """Zwei Feierabende mit Tag 1 (Gehalt 120, Miete 30): einmal."""
        state = fg.GameState(_events(_day_end(1, salary=120, rent=30),
                                     _day_end(1, salary=120, rent=30)))
        self.assertEqual((state.days_done, state.money), (1, 90))
        self.assertEqual(len(state.balances), 1)
        self.assertEqual(len(state.day_log), 1)

    def test_feierabend_doppelt_firma(self):
        """Firmen-Feierabend doppelt (Umsatz, Gehaelter, Kundenticket):
        die ganze Firmenrechnung des Tages zaehlt einmal."""
        founded = (fg.EV_FOUNDED, {"name": "Testfirma", "tag": 1, "geld": 1000})
        firm = {"umsatz": 400, "gehaelter": 150, "nebenkosten": 50,
                "tickets": [{"ticket": "kt-1", "geld": 70, "erfolg": False}]}
        once = fg.GameState(_events(founded, _day_end(1, salary=0, firma=firm)))
        twice = fg.GameState(_events(founded, _day_end(1, salary=0, firma=firm),
                                     _day_end(1, salary=0, firma=dict(firm))))
        self.assertEqual(twice.days_done, 1)
        self.assertEqual(twice.money, once.money)
        self.assertEqual(twice.book, once.book)

    def test_echte_api_zwei_geraete(self):
        """Echte Spiel-API: Geraet A spielt Tag 1, die Datenbank wird auf
        Geraet B kopiert, beide spielen Tag 2 offline zu Ende, dann werden die
        Zeilen von B bei A uebernommen (Abgleich). Soll: derselbe Stand wie
        Geraet A allein (v0.62.3: 3 Tage, Tickets und Geld doppelt)."""
        a, b = TempDB(), TempDB()
        game_a = fg.Game(a.open(), device="PC")
        game_a.set_profile("Ada", {})
        self.assertEqual(_play_day(game_a), 0)
        shutil.copy(a.path, b.path)
        game_b = fg.Game(b.open(), device="Handy")
        self.assertEqual(game_b.run, game_a.run)
        self.assertEqual(_play_day(game_a), 0)
        self.assertEqual(_play_day(game_b), 0)
        alone = _core_values(game_a.reload())
        self.assertEqual(alone["tage"], 2)
        self.assertEqual(_core_values(game_b.reload()), alone)
        self.assertGreater(_merge_rows(b.path, a.path), 0)
        game_a.invalidate()
        merged = fg.GameState(a.open().game_events(game_a.run))
        self.assertEqual(_core_values(merged), alone)
        self.assertEqual(_core_values(game_a.reload()), alone)


class SchutzTest(unittest.TestCase):
    """SCHUTZ: auf v0.62.3 und nach der Aenderung gruen."""

    def test_feierabende_ohne_tag_zaehlen(self):
        """Aeltere Feierabende ohne Tagesangabe werden nicht geraten: zwei
        direkt hintereinander zaehlen zweimal (wie bisher)."""
        state = fg.GameState(_events((fg.EV_DAY_END, {"gehalt": 100}),
                                     (fg.EV_DAY_END, {"gehalt": 100})))
        self.assertEqual((state.days_done, state.money), (2, 200))

    def test_ohne_tag_dann_mit_tag_zaehlen(self):
        """Feierabend ohne Tag, danach einer mit Tag 2 und einer mit Tag 1:
        nichts ist eindeutig doppelt, alle drei zaehlen."""
        state = fg.GameState(_events((fg.EV_DAY_END, {"gehalt": 10}),
                                     _day_end(2, salary=10), _day_end(1, salary=10)))
        self.assertEqual((state.days_done, state.money), (3, 30))

    def test_ungueltige_tagesangaben_zaehlen(self):
        """Tagesangaben, die keine ganze Zahl > 0 sind ("1", 0, true, 1.0),
        gelten als 'ohne Tagesangabe' und werden nicht uebersprungen."""
        for bad in ("1", 0, True, 1.0, None, -1):
            events = _events(_day_end(1, salary=10),
                             (fg.EV_DAY_END, {"tag": bad, "gehalt": 10}))
            state = fg.GameState(events)
            self.assertEqual(state.days_done, 2, bad)
            self.assertEqual(state.money, 20, bad)

    def test_ticket_ohne_tag_doppelt_zaehlt(self):
        """Ticket ohne Tagesangabe zweimal: nicht geraten, zaehlt zweimal."""
        data = {"aufgabe": "hw-03", "geld": 20, "richtig": True}
        state = fg.GameState(_events((fg.EV_SOLVED, data), (fg.EV_SOLVED, dict(data))))
        self.assertEqual((state.tickets_done, state.money), (2, 40))

    def test_gleiches_ticket_anderer_tag(self):
        """Dieselbe Aufgabe an Tag 1 und Tag 2 (z.B. Falsche Ware kommt
        wieder): zwei verschiedene Arbeitstage, zaehlt zweimal."""
        state = fg.GameState(_events(_solved("hw-04", 1, money=-10, right=False),
                                     _day_end(1, salary=0),
                                     _solved("hw-04", 2, money=-10, right=False)))
        self.assertEqual((state.tickets_done, state.money), (2, -20))

    def test_zwei_tickets_selber_tag(self):
        state = fg.GameState(_events(_solved("hw-05", 1), _solved("hw-06", 1)))
        self.assertEqual((state.tickets_done, state.money), (2, 100))

    def test_verschoben_doppelt_unveraendert(self):
        """Abgrenzung: 'ticket_verschoben' ist nicht Teil von B-G-26 (Plan
        0.62.4, 5.5 nennt nur ticket_erledigt und tag_beendet) und zaehlt wie
        bisher bei jedem Ereignis."""
        data = {"aufgabe": "hw-07", "tag": 1, "reputation": {"zuverlaessigkeit": -2}}
        single = fg.GameState(_events((fg.EV_DEFERRED, data)))
        double = fg.GameState(_events((fg.EV_DEFERRED, data), (fg.EV_DEFERRED, dict(data))))
        start = fg.GameState([]).reputation["zuverlaessigkeit"]
        self.assertEqual(single.reputation["zuverlaessigkeit"], start - 2)
        self.assertEqual(double.reputation["zuverlaessigkeit"], start - 4)

    def test_dreissig_tage_ein_geraet(self):
        """30-Tage-Lauf mit einem Geraet (echte Spiel-API, keine Doppel):
        Tage, Tickets und Geld stimmen mit einer unabhaengigen Nachrechnung
        aus dem Ereignisprotokoll ueberein, Neuaufbau == laufender Stand."""
        tmp = TempDB()
        db = tmp.open()
        game = fg.Game(db, device="PC")
        game.set_profile("Ada", {})
        for _ in range(30):
            self.assertEqual(_play_day(game), 0)
        state = game.reload()
        events = db.game_events(game.run)
        kinds = [kind for _ts_, kind, _data in events]
        self.assertEqual(state.days_done, 30)
        self.assertEqual(kinds.count(fg.EV_DAY_END), 30)
        self.assertEqual(state.tickets_done, kinds.count(fg.EV_SOLVED))
        self.assertIsNone(state.firm)
        money = 0
        for _stamp, kind, data in events:
            if kind in (fg.EV_SOLVED, fg.EV_DEFERRED, fg.EV_SPARE_ORDER, fg.EV_MOVE,
                        fg.EV_BUY, fg.EV_SELL):
                money += int(data.get("geld", 0))
            elif kind == fg.EV_DAY_END:
                money += int(data.get("gehalt", 0)) - int(data.get("miete", 0))
        self.assertEqual(state.money, money)
        fresh = fg.GameState(events)
        self.assertEqual(_core_values(fresh), _core_values(state))
        # Tagesangaben im Protokoll: 1..30, jede genau einmal
        days = [data.get("tag") for _stamp, kind, data in events if kind == fg.EV_DAY_END]
        self.assertEqual(days, list(range(1, 31)))


def tearDownModule():
    shutil.rmtree(_HOME, ignore_errors=True)


if __name__ == "__main__":
    print("Code-Ordner: %s" % CODE)
    unittest.main(verbosity=2)
