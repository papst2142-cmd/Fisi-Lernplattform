#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests fuer das Lernspiel (fisi_game.py) - ohne Oberflaeche.

Start:  python test_spiel.py
"""

import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import fisi_game as fg  # noqa: E402
import fisi_sync  # noqa: E402
from fisi_core import CAT_NET, CAT_SYS, DBManager, validate_content  # noqa: E402

BALANCING = fg.GAME["balancing"]


class TempDB:
    """Eine frische Datenbank in einem temporaeren Ordner."""

    def __enter__(self):
        self.folder = tempfile.mkdtemp()
        self.db = DBManager(os.path.join(self.folder, "test.db"))
        return self.db

    def __exit__(self, *_exc):
        shutil.rmtree(self.folder, ignore_errors=True)


def levels(value):
    return {key: value for key in fg.CAT_ORDER}


class InhalteTest(unittest.TestCase):
    def test_inhalte_fehlerfrei(self):
        self.assertEqual(fg.validate_game_content(), [])
        self.assertEqual(validate_content(), [])

    def test_fehler_werden_gefunden(self):
        content = json.loads(json.dumps(fg.GAME))
        content["aufgaben"][0]["raum"] = "keller"
        content["aufgaben"][1]["antwort"] = "gibt es nicht"
        problems = fg.validate_game_content(content)
        self.assertTrue(any("keller" in p for p in problems))
        self.assertTrue(any("nicht in den Optionen" in p for p in problems))

    def test_alle_fachbereiche_kommen_vor(self):
        cats = {task["cat"] for task in fg.GAME["aufgaben"]}
        self.assertEqual(cats, set(fg.CAT_ORDER))


class WissenTest(unittest.TestCase):
    def test_ohne_antworten_null(self):
        self.assertEqual(fg.knowledge_from_answers({}, {}), levels(0.0))

    def test_alles_richtig_volle_abdeckung(self):
        answers = {"netzwerk": [True] * 50}
        coverage = {"netzwerk": 60.0}
        self.assertEqual(fg.knowledge_from_answers(answers, coverage)["netzwerk"], 100.0)

    def test_wenige_antworten_werden_gedaempft(self):
        few = fg.knowledge_from_answers({"netzwerk": [True] * 5}, {"netzwerk": 60.0})
        many = fg.knowledge_from_answers({"netzwerk": [True] * 40}, {"netzwerk": 60.0})
        self.assertLess(few["netzwerk"], many["netzwerk"])

    def test_neuere_antworten_zaehlen_staerker(self):
        besser = fg.knowledge_from_answers({"netzwerk": [True] * 20 + [False] * 20},
                                           {"netzwerk": 60.0})
        schlechter = fg.knowledge_from_answers({"netzwerk": [False] * 20 + [True] * 20},
                                               {"netzwerk": 60.0})
        self.assertGreater(besser["netzwerk"], schlechter["netzwerk"])

    def test_abdeckung_wird_gedaempft_nicht_linear(self):
        # 12,5 % Abdeckung bei voller Wirkung ab 50 % -> Wurzel(0,25) = 50 %
        value = fg.knowledge_from_answers({"netzwerk": [True] * 40},
                                          {"netzwerk": 12.5})["netzwerk"]
        self.assertAlmostEqual(value, 50.0, places=1)

    def test_aus_der_datenbank(self):
        with TempDB() as db:
            for _ in range(30):
                db.log_quiz_answer(CAT_NET, "Frage netz %d" % _, True)
            db.log_card(CAT_SYS, "Karte", "mc", False)
            result = fg.knowledge(db)
            self.assertGreater(result["netzwerk"], 0)
            self.assertEqual(result["systeme"], 0)
            self.assertEqual(result["wirtschaft"], 0)


class AufgabenTest(unittest.TestCase):
    def setUp(self):
        self.choice = next(t for t in fg.GAME["aufgaben"] if t["typ"] == "auswahl")
        self.match = next(t for t in fg.GAME["aufgaben"] if t["typ"] == "zuordnung")

    def test_auswahl(self):
        self.assertEqual(fg.check_answer(self.choice, self.choice["antwort"]), (True, 0))
        wrong = [o for o in self.choice["optionen"] if o != self.choice["antwort"]][0]
        self.assertEqual(fg.check_answer(self.choice, wrong), (False, 1))

    def test_zuordnung(self):
        right = {left: r for left, r in self.match["paare"]}
        self.assertEqual(fg.check_answer(self.match, right), (True, 0))
        lefts = [left for left, _r in self.match["paare"]]
        swapped = dict(right)
        swapped[lefts[0]], swapped[lefts[1]] = right[lefts[1]], right[lefts[0]]
        self.assertEqual(fg.check_answer(self.match, swapped), (False, 2))
        self.assertEqual(fg.check_answer(self.match, {})[0], False)

    def test_bonus_ohne_hilfe(self):
        base = self.choice["belohnung"]
        with_help = fg.evaluate(self.choice, self.choice["antwort"], True, levels(100), 1)
        without = fg.evaluate(self.choice, self.choice["antwort"], False, levels(100), 1)
        self.assertGreater(without["geld"], with_help["geld"])
        self.assertGreaterEqual(with_help["geld"], base["geld"])
        self.assertGreater(without["reputation"]["fachkompetenz"],
                           with_help["reputation"]["fachkompetenz"])

    def test_weiche_sperre_doppelter_verlust(self):
        wrong = [o for o in self.choice["optionen"] if o != self.choice["antwort"]][0]
        normal = fg.evaluate(self.choice, wrong, False, levels(100), 1)
        below = fg.evaluate(self.choice, wrong, False, levels(0), 1)
        self.assertTrue(below["unter_niveau"])
        self.assertFalse(normal["unter_niveau"])
        self.assertEqual(below["reputation"]["fachkompetenz"],
                         2 * normal["reputation"]["fachkompetenz"])
        self.assertLess(normal["geld"], 0)

    def test_warnhinweis(self):
        gaps = fg.requirement_gaps(self.choice, levels(0))
        self.assertTrue(gaps)
        self.assertIn("fehlt dir noch Wissen", fg.gap_warning(gaps))
        self.assertEqual(fg.gap_warning(fg.requirement_gaps(self.choice, levels(100))), "")

    def test_verweise_ins_lernen(self):
        for task in fg.GAME["aufgaben"]:
            links = fg.learn_links(task)
            self.assertTrue(links, task["id"])
            self.assertTrue(all(hit[0] in ("Karteikarte", "Quizfrage") for hit in links))


class SpielstandTest(unittest.TestCase):
    def test_leerer_stand(self):
        state = fg.GameState([])
        self.assertIsNone(state.profile)
        self.assertEqual(state.day, 1)
        self.assertEqual(state.money, 0)
        self.assertEqual(state.rank, "Azubi-Niveau")
        self.assertEqual(len(state.todays_tickets()), BALANCING["tickets_pro_tag"])
        self.assertFalse(state.can_end_day())

    def test_juengstes_profil_gewinnt(self):
        state = fg.GameState([
            ("2026-09-28 10:00:00", fg.EV_PROFILE, {"name": "Alt", "aussehen": {}}),
            ("2026-09-28 11:00:00", fg.EV_PROFILE,
             {"name": "Neu", "aussehen": {"frisur": "locken", "haut": "unsinn"}}),
        ])
        self.assertEqual(state.profile["name"], "Neu")
        self.assertEqual(state.profile["aussehen"]["frisur"], "locken")
        self.assertEqual(state.profile["aussehen"]["haut"], "hell")

    def test_reputation_bleibt_zwischen_0_und_100(self):
        events = [("t%03d" % i, fg.EV_SOLVED,
                   {"aufgabe": "x", "tag": 1, "richtig": False, "geld": -1,
                    "reputation": {"fachkompetenz": -30}}) for i in range(5)]
        events += [("u%03d" % i, fg.EV_SOLVED,
                    {"aufgabe": "x", "tag": 1, "richtig": True, "geld": 1,
                     "reputation": {"fachkompetenz": 40}}) for i in range(5)]
        state = fg.GameState(events)
        self.assertEqual(state.reputation["fachkompetenz"], 100)
        self.assertEqual(state.money, 0)


class SpielMitDatenbankTest(unittest.TestCase):
    def test_arbeitstag_ablauf(self):
        with TempDB() as db:
            game = fg.Game(db, device="Test")
            game.set_profile("Nico", {"frisur": "kurz"})
            tickets = game.state.open_tickets()
            first, second, third = tickets
            payload = game.solve(first["id"], _right_answer(first), used_help=False)
            self.assertTrue(payload["richtig"])
            self.assertEqual(game.state.status_of(first["id"]), fg.ST_RIGHT)
            game.solve(second["id"], _wrong_answer(second), used_help=True)
            self.assertEqual(game.state.status_of(second["id"]), fg.ST_WRONG)
            self.assertFalse(game.state.can_end_day())
            game.defer(third["id"])
            # Keine neuen Tickets am selben Tag, Tag kann enden
            self.assertEqual(game.state.open_tickets(), [])
            self.assertTrue(game.state.can_end_day())
            money_before = game.state.money
            salary = game.state.salary
            game.end_day()
            self.assertEqual(game.state.day, 2)
            self.assertEqual(game.state.money, money_before + salary)
            # Falsch geloeste und verschobene Tickets kommen wieder
            open_ids = [task["id"] for task in game.state.open_tickets()]
            self.assertIn(second["id"], open_ids)
            self.assertIn(third["id"], open_ids)
            self.assertNotIn(first["id"], open_ids)
            with self.assertRaises(ValueError):
                game.solve(first["id"], _right_answer(first), False)

    def test_alle_aufgaben_loesbar(self):
        with TempDB() as db:
            game = fg.Game(db)
            game.set_profile("Test", {})
            for _day in range(30):
                for task in game.state.open_tickets():
                    game.solve(task["id"], _right_answer(task), used_help=False)
                if game.state.all_done():
                    break
                game.end_day()
            self.assertTrue(game.state.all_done())
            self.assertGreater(game.state.money, 0)
            self.assertNotEqual(game.state.rank, "Azubi-Niveau")

    def test_zuruecksetzen_getrennt(self):
        with TempDB() as db:
            game = fg.Game(db)
            game.set_profile("Nico", {})
            db.log_quiz_answer(CAT_NET, "Frage", True)
            # "Alle Lerndaten loeschen" laesst den Spielstand stehen
            db.reset_all()
            self.assertEqual(game.reload().profile["name"], "Nico")
            db.clear_history()
            self.assertEqual(game.reload().profile["name"], "Nico")
            # "Spielstand zuruecksetzen" laesst den Lernfortschritt stehen
            db.log_quiz_answer(CAT_NET, "Frage 2", True)
            game.reset()
            self.assertIsNone(game.state.profile)
            self.assertEqual(db.count_quiz_answers(), 1)
            self.assertTrue(db.get_meta("spiel_reset_at"))


class AbgleichTest(unittest.TestCase):
    def test_spielstand_wird_abgeglichen(self):
        with TempDB() as pc, TempDB() as handy:
            fg.Game(pc, "PC").set_profile("Nico", {"extra": "brille"})
            fisi_sync.merge_into_local(handy, fisi_sync.export_local(pc))
            state = fg.Game(handy, "Handy").state
            self.assertEqual(state.profile["name"], "Nico")
            # Doppelter Abgleich zaehlt nichts doppelt
            fisi_sync.merge_into_local(handy, fisi_sync.export_local(pc))
            self.assertEqual(len(handy.game_events()), 1)

    def test_zuruecksetzen_wird_abgeglichen(self):
        with TempDB() as pc, TempDB() as handy:
            game = fg.Game(pc, "PC")
            game.set_profile("Nico", {})
            fisi_sync.merge_into_local(handy, fisi_sync.export_local(pc))
            handy_game = fg.Game(handy, "Handy")
            # Zeitstempel sind sekundengenau - Reset eindeutig spaeter setzen
            handy._execute("UPDATE spiel_ereignisse SET timestamp = '2026-01-01 00:00:00'",
                           commit=True)
            pc._execute("UPDATE spiel_ereignisse SET timestamp = '2026-01-01 00:00:00'",
                        commit=True)
            handy_game.reset()
            fisi_sync.merge_into_local(pc, fisi_sync.export_local(handy))
            self.assertIsNone(fg.Game(pc).state.profile)

    def test_lern_reset_loescht_spiel_nicht_beim_abgleich(self):
        with TempDB() as pc, TempDB() as handy:
            fg.Game(pc, "PC").set_profile("Nico", {})
            pc._execute("UPDATE spiel_ereignisse SET timestamp = '2026-01-01 00:00:00'",
                        commit=True)
            handy.reset_all()
            fisi_sync.merge_into_local(pc, fisi_sync.export_local(handy))
            self.assertEqual(fg.Game(pc).state.profile["name"], "Nico")


class GrundrissUndAvatarTest(unittest.TestCase):
    def test_raum_treffer(self):
        for item in fg.GAME["gebaeude"]["raeume"]:
            hit = fg.room_at(item["x"] + item["w"] / 2.0, item["y"] + item["h"] / 2.0)
            self.assertEqual(hit["id"], item["id"])
        self.assertIsNone(fg.room_at(-1, -1))

    def test_raeume_ueberlappen_nicht(self):
        building = fg.GAME["gebaeude"]
        for x in range(building["breite"]):
            for y in range(building["hoehe"]):
                hits = [r for r in building["raeume"]
                        if r["x"] <= x < r["x"] + r["w"] and r["y"] <= y < r["y"] + r["h"]]
                self.assertLessEqual(len(hits), 1, (x, y))

    def test_gebaeude_zeichnung(self):
        state = fg.GameState([])
        shapes = fg.building_shapes(state.open_count_by_room(), "serverraum",
                                    ("Nico", fg.DEFAULT_APPEARANCE))
        kinds = {shape["k"] for shape in shapes}
        self.assertLessEqual(kinds, {"rect", "oval", "line", "arc", "text"})
        texts = [shape["text"] for shape in shapes if shape["k"] == "text"]
        for item in fg.GAME["gebaeude"]["raeume"]:
            self.assertIn(item["name"], texts)
        self.assertIn("Nico", texts)
        # Ohne Spielfigur keine Figur im Flur
        texts = [shape["text"] for shape in fg.building_shapes() if shape["k"] == "text"]
        self.assertNotIn("Nico", texts)

    def test_einrichtung_und_plaetze_in_den_raeumen(self):
        for item in fg.GAME["gebaeude"]["raeume"]:
            for deco in item.get("deko", []):
                self.assertIn(deco["typ"], fg.DECO_TYPES)
                self.assertTrue(fg._inside(deco, item), (item["id"], deco))
        for person in fg.GAME["kollegen"]:
            hit = fg.room_at(*person["platz"])
            self.assertEqual(hit["id"], person["raum"], person["id"])
        # Der Flur gehoert zu keinem Raum
        hall = fg.GAME["gebaeude"]["flur"]
        self.assertIsNone(fg.room_at(5, hall["y"] + hall["h"] / 2.0))

    def test_alle_kollegen_erreichbar(self):
        start = fg.start_position()
        self.assertTrue(fg.can_stand(*start))
        for person in fg.GAME["kollegen"]:
            route = fg.walk_path(start, person["platz"], reach=fg.REACH)
            self.assertTrue(route, person["id"])
            end = route[-1]
            self.assertLessEqual((end[0] - person["platz"][0]) ** 2 +
                                 (end[1] - person["platz"][1]) ** 2,
                                 fg.REACH ** 2 + 1e-9)
            self.assertEqual(fg.person_near(*end)["id"], person["id"])
            # jeder Wegpunkt ist begehbar
            for point in route:
                self.assertTrue(fg.can_stand(*point), (person["id"], point))

    def test_waende_nur_durch_tueren(self):
        # Von Raum zu Raum fuehrt der Weg immer durch den Flur
        hall = fg.GAME["gebaeude"]["flur"]
        route = fg.walk_path((3.5, 12.0), (3.5, 4.5))
        self.assertTrue(route)
        self.assertTrue(any(hall["y"] <= y <= hall["y"] + hall["h"] for _x, y in route))

    def test_drehung_hin_und_zurueck(self):
        for point in ((0, 0), (3.5, 12.25), (24, 16)):
            self.assertEqual(fg.from_view(*fg.to_view(*point, rotate=True), rotate=True),
                             point)
        self.assertEqual(fg.plan_size(True), (16, 24))
        shapes = fg.building_shapes(rotate=True)
        width, height = fg.plan_size(True)
        for shape in shapes:
            if shape["k"] == "text":
                self.assertTrue(-1 <= shape["x"] <= width + 1 and -1 <= shape["y"] <= height + 1)

    def test_auftraege_je_person(self):
        state = fg.GameState([])
        quests = state.quests()
        self.assertEqual(sum(len(tasks) for tasks in quests.values()),
                         len(state.open_tickets()))
        person_id = next(iter(quests))
        person = fg.colleague(person_id)
        title, _text = fg.office_message(person["platz"], person, quests)
        self.assertIn("Auftrag", title)
        texts = [s["text"] for s in fg.building_shapes(quests=set(quests)) if s["k"] == "text"]
        self.assertEqual(texts.count("!"), len(quests))

    def test_avatar_alle_varianten(self):
        for part, options in fg.APPEARANCE.items():
            for key, _name in options:
                shapes = fg.avatar_shapes({part: key})
                self.assertTrue(shapes)
                for kind, coords, color in shapes:
                    self.assertIn(kind, ("oval", "rect", "line"))
                    self.assertEqual(len(coords), 4)
                    self.assertTrue(color.startswith("#"))


def _right_answer(task):
    if task["typ"] == "auswahl":
        return task["antwort"]
    return {left: right for left, right in task["paare"]}


def _wrong_answer(task):
    if task["typ"] == "auswahl":
        return [o for o in task["optionen"] if o != task["antwort"]][0]
    return {}


if __name__ == "__main__":
    unittest.main(verbosity=1)
