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
                    game.solve(task["id"], _right_answer(task, game.state), used_help=False)
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
        for point in ((0, 0), (3.5, 12.25), (30, 16)):
            self.assertEqual(fg.from_view(*fg.to_view(*point, rotate=True), rotate=True),
                             point)
        self.assertEqual(fg.plan_size(True), (16, 30))
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

    def test_kreisfarbe_waehlbar(self):
        for key, _name in fg.APPEARANCE["kreis"]:
            shapes = fg.player_shapes(fg.start_position(), ("Nico", {"kreis": key}))
            self.assertEqual(shapes[0]["line"], fg.RING_COLORS[key])
            self.assertEqual(shapes[-1]["color"], fg.RING_COLORS[key])
        # alte Spielstaende ohne Kreis bekommen Pink
        self.assertEqual(fg.normalize_appearance({})["kreis"], "pink")

    def test_avatar_alle_varianten(self):
        for part, options in fg.APPEARANCE.items():
            for key, _name in options:
                shapes = fg.avatar_shapes({part: key})
                self.assertTrue(shapes)
                for kind, coords, color in shapes:
                    self.assertIn(kind, ("oval", "rect", "line"))
                    self.assertEqual(len(coords), 4)
                    self.assertTrue(color.startswith("#"))


def _right_answer(task, state=None):
    available = state.available_parts(task) if state is not None else None
    return fg.find_solution(task, available)


def _wrong_answer(task):
    if task["typ"] == "auswahl":
        return [o for o in task["optionen"] if o != task["antwort"]][0]
    return {}


def _task(task_id):
    return fg.task_by_id(task_id)


def _solved_event(stamp, task, answer, day, state=None):
    available = state.available_parts(task) if state is not None else None
    stock = state.stock() if state is not None else None
    payload = fg.evaluate(task, answer, False, levels(100), day, BALANCING, available,
                          None, stock)
    return (stamp, fg.EV_SOLVED, payload)


def _day_ends(count):
    return [("d%03d" % index, fg.EV_DAY_END, {"tag": index + 1, "gehalt": 0})
            for index in range(count)]


class BauteileTest(unittest.TestCase):
    def parts(self, *ids):
        return {fg.part(pid)["typ"]: fg.part(pid) for pid in ids}

    def test_kompatibilitaet(self):
        ok = self.parts("mb_a620_matx", "cpu_r5_7600", "ram_ddr5_2x8", "ssd_nvme_500",
                        "nt_300", "geh_matx")
        self.assertEqual(fg.compatibility_problems(ok), [])
        cases = [
            (("mb_a620_matx", "cpu_i5_13400"), "Sockel"),
            (("mb_b760_matx", "ram_ddr5_2x8"), "DDR5"),
            (("mb_a620_matx", "ram_ddr5_2x8"), None),
            (("mb_h610_itx", "ram_ddr4_4x8"), "Steckplätze"),
            (("mb_b650_atx", "geh_matx"), "Gehäuse"),
            (("mb_h610_itx", "ssd_nvme_500"), "M.2"),
            (("mb_h610_itx", "ssd_sata_500"), None),
            (("cpu_r7_7700x", "gpu_4070", "nt_450"), "zu schwach"),
            (("cpu_r7_7700x", "gpu_4070", "nt_650"), None),
        ]
        for ids, word in cases:
            problems = fg.compatibility_problems(self.parts(*ids))
            if word is None:
                self.assertEqual(problems, [], ids)
            else:
                self.assertEqual(len(problems), 1, ids)
                self.assertIn(word, problems[0], ids)

    def test_netzteil_formel(self):
        # (105 + 200 + 60) * 1,3 = 474,5 -> 475 W
        self.assertEqual(fg.psu_needed(fg.part("cpu_r7_7700x"), fg.part("gpu_4070")), 475)
        self.assertEqual(fg.psu_needed(fg.part("cpu_r5_7600")), 163)

    def test_pc_bauen(self):
        task = _task("pc-servicecenter")
        right = fg.find_solution(task)
        self.assertEqual(fg.check_answer(task, right), (True, 0))
        wrong = dict(right, cpu="cpu_i5_13400f", gehaeuse="geh_itx")
        problems = fg.build_problems(task, wrong)
        self.assertTrue(any("Sockel" in text for text in problems))
        self.assertTrue(any("Gehäuse" in text for text in problems))
        # Leerer Steckplatz und Teil, das nicht bereitliegt
        missing = dict(right)
        del missing["netzteil"]
        self.assertIn("Netzteil fehlt noch.", fg.build_problems(task, missing))
        foreign = dict(right, ram="ram_ddr5_2x16")
        self.assertIn("Arbeitsspeicher fehlt noch.", fg.build_problems(task, foreign))
        payload = fg.evaluate(task, wrong, False, levels(100), 4)
        self.assertFalse(payload["richtig"])
        self.assertEqual(payload["fehler"], len(payload["probleme"]))
        text = fg.result_text(task, payload)
        self.assertIn("Probleme", text)
        self.assertIn("Eine passende Zusammenstellung", text)

    def test_kein_bild_ohne_grafik(self):
        task = _task("pc-servicecenter")
        answer = {"mainboard": "mb_b760_matx", "cpu": "cpu_i5_13400f"}
        self.assertTrue(any("Kein Bild" in text for text in fg.build_problems(task, answer)))
        # Mit Grafikkarte ist die CPU ohne Grafik in Ordnung
        task = _task("grafik-arbeitsplatz")
        answer = fg.find_solution(task, task["teile"] + ["nt_650"])
        answer["cpu"] = "cpu_i5_13400f"
        problems = fg.build_problems(task, answer, task["teile"] + ["nt_650"])
        self.assertFalse(any("Kein Bild" in text for text in problems))

    def test_bestellung(self):
        task = _task("ram-leitstelle")
        self.assertEqual(fg.valid_carts(task), [{"a3": 2}])
        self.assertEqual(fg.check_answer(task, {"a3": 2}), (True, 0))
        checks = [
            ({}, "leer"),
            ({"a1": 2}, "DDR5"),
            ({"a4": 2}, "zu klein"),
            ({"a2": 2}, "Zu spät"),
            ({"a3": 1, "a5": 1}, "Budget"),
            ({"a3": 3}, "Zu viel"),
            ({"a3": 1}, "nicht gedeckt"),
        ]
        for cart, word in checks:
            problems = fg.order_problems(task, cart)
            self.assertTrue(any(word in text for text in problems), (cart, problems))
        self.assertEqual(fg.cart_total(task, {"a3": 2, "a1": 0}), (110, 2))

    def test_ersparnis_und_lieferung(self):
        task = _task("ssd-automaten")
        cheap = fg.evaluate(task, {"s2": 3}, True, levels(100), 6)
        dear = fg.evaluate(task, {"s2": 1, "s3": 2}, True, levels(100), 6)
        self.assertTrue(cheap["richtig"] and dear["richtig"])
        self.assertGreater(cheap["ersparnis_bonus"], dear.get("ersparnis_bonus", 0))
        self.assertEqual(cheap["geld"] - dear["geld"],
                         cheap["ersparnis_bonus"] - dear.get("ersparnis_bonus", 0))
        self.assertEqual(cheap["kosten"], 126)
        self.assertEqual(cheap["lieferung"], [{"teil": "ssd_sata_500", "menge": 3,
                                               "haendler": "kabelkoenig", "ankunft": 8}])
        self.assertEqual({item["ankunft"] for item in dear["lieferung"]}, {7, 8})
        self.assertIn("Arbeitstag 8", fg.result_text(task, cheap))
        wrong = fg.evaluate(task, {"s1": 3}, True, levels(100), 6)
        self.assertNotIn("lieferung", wrong)
        self.assertLess(wrong["geld"], 0)
        self.assertIn("So hätte es gepasst", fg.result_text(task, wrong))

    def test_unloesbare_inhalte_werden_gefunden(self):
        content = json.loads(json.dumps(fg.GAME))
        order = next(t for t in content["aufgaben"] if t["id"] == "ram-leitstelle")
        order["budget"] = 50
        build = next(t for t in content["aufgaben"] if t["id"] == "pc-servicecenter")
        build["teile"].remove("nt_300")
        problems = fg.validate_game_content(content)
        self.assertTrue(any("ram-leitstelle" in p and "keine gueltige" in p
                            for p in problems), problems)
        self.assertTrue(any("pc-servicecenter" in p and "nicht bauen" in p
                            for p in problems), problems)
        # Der Folgeauftrag haengt an der (jetzt unmoeglichen) Bestellung
        self.assertTrue(any("leitstelle-pc" in p for p in problems), problems)


class LagerTest(unittest.TestCase):
    def test_folgeauftrag_wartet_auf_lieferung(self):
        order = _task("ram-leitstelle")
        events = _day_ends(3)                              # Arbeitstag 4
        events.append(_solved_event("e1", order, {"a3": 2}, 4))
        state = fg.GameState(events)
        self.assertNotIn("leitstelle-pc", [t["id"] for t in state._pool()])
        self.assertEqual([t["id"] for t in state.waiting_for_delivery()], ["leitstelle-pc"])
        store = state.warehouse()
        self.assertEqual(store["unterwegs"][0]["teil"], "ram_ddr4_2x8")
        self.assertEqual(store["unterwegs"][0]["ankunft"], 6)
        self.assertEqual(state.stock(), {})
        self.assertIn("Arbeitstag 6", fg.warehouse_summary(state))

        events += [("f%d" % i, fg.EV_DAY_END, {"tag": 4 + i, "gehalt": 0}) for i in range(2)]
        state = fg.GameState(events)                       # Arbeitstag 6
        self.assertEqual(state.day, 6)
        self.assertTrue(state.arrived("ram-leitstelle"))
        self.assertEqual(state.stock(), {"ram_ddr4_2x8": 2})
        build = _task("leitstelle-pc")
        self.assertIn(build["id"], [t["id"] for t in state._pool()])
        self.assertIn("ram_ddr4_2x8", state.available_parts(build))
        # Der Grafik-Arbeitsplatz darf den RAM nicht aus dem Lager nehmen
        self.assertNotIn("ram_ddr4_2x8", state.available_parts(_task("grafik-arbeitsplatz")))

        answer = fg.find_solution(build, state.available_parts(build))
        events.append(_solved_event("g1", build, answer, 6, state))
        state = fg.GameState(events)
        self.assertEqual(state.stock(), {"ram_ddr4_2x8": 1})
        self.assertEqual(state.warehouse()["bestand"], [("ram_ddr4_2x8", 1)])

    def test_ware_mit_empfaenger_geht_nicht_ins_lager(self):
        task = _task("notebook-chefin")
        events = _day_ends(4) + [_solved_event("e1", task, {"b2": 1}, 5)]
        events += [("x1", fg.EV_DAY_END, {"tag": 5, "gehalt": 0})]
        state = fg.GameState(events)
        self.assertEqual(state.stock(), {})
        handed = state.warehouse()["ausgeliefert"]
        self.assertEqual(handed[0]["empfaenger"], "sabine")

    def test_tag_endet_auch_beim_warten(self):
        # Alles erledigt ausser den Auftraegen, die auf Ware warten
        events = []
        for index, task in enumerate(fg.GAME["aufgaben"]):
            if task.get("nach"):
                continue
            stamp, kind, payload = _solved_event("s%02d" % index, task,
                                                 fg.find_solution(task), 1)
            for item in payload.get("lieferung", []):
                item["ankunft"] = 9
            events.append((stamp, kind, payload))
        events += [("z%d" % i, fg.EV_DAY_END, {"tag": i + 1, "gehalt": 0}) for i in range(4)]
        state = fg.GameState(events)                       # Tag 5, Ware kommt Tag 9
        self.assertEqual(state.open_tickets(), [])
        self.assertFalse(state.handled)
        self.assertTrue(state.waiting_for_delivery())
        self.assertTrue(state.can_end_day())

    def test_lagerist_zeigt_bestand(self):
        rainer = fg.colleague("rainer")
        state = fg.GameState([])
        title, text = fg.office_message(rainer["platz"], rainer, {}, state=state)
        self.assertIn("Lagerist", title)
        self.assertIn("Lager ist leer", text)

    def test_lager_nur_durch_die_tuer(self):
        # Von der Verwaltung ins Lager fuehrt der Weg durch den Flur
        hall = fg.GAME["gebaeude"]["flur"]
        route = fg.walk_path((22.5, 3.0), (25.5, 5.3))
        self.assertTrue(route)
        self.assertTrue(any(hall["y"] <= y <= hall["y"] + hall["h"] for _x, y in route))
        self.assertEqual(fg.door_side(fg.room("lager")), "w")
        self.assertEqual(fg.door_side(fg.room("helpdesk")), "n")
        self.assertEqual(fg.door_side(fg.room("chefbuero")), "s")


class RackTest(unittest.TestCase):
    def setUp(self):
        self.task = fg.task_by_id("rack-leitstelle")
        # Plaetze: 0/1 Server 1 HE, 2 Altserver 4 HE, 3 Switch, 4 Patchpanel, 5 USV
        self.good = {"5": 1, "0": 3, "1": 4, "3": 5, "4": 6}

    def test_richtige_belegung(self):
        self.assertEqual(fg.rack_problems(self.task, self.good), [])
        self.assertEqual(fg.check_answer(self.task, self.good), (True, 0))

    def test_leer_und_ueberlappung(self):
        self.assertEqual(fg.rack_problems(self.task, {}), ["Der Schrank ist noch leer."])
        answer = dict(self.good, **{"1": 3})
        self.assertTrue(any("überlappen in HE 3" in p
                            for p in fg.rack_problems(self.task, answer)))

    def test_ragt_oben_heraus(self):
        answer = dict(self.good, **{"4": 13})
        self.assertTrue(any("passt ab HE 13 nicht" in p
                            for p in fg.rack_problems(self.task, answer)))

    def test_usv_nach_unten(self):
        answer = {"0": 1, "1": 2, "3": 3, "4": 4, "5": 5}
        problems = fg.rack_problems(self.task, answer)
        self.assertIn("Die USV gehört ganz nach unten, unter alle anderen Geräte.", problems)
        answer = {"5": 5, "0": 7, "1": 8, "3": 9, "4": 10}
        self.assertTrue(any("wiegt 24 kg" in p for p in fg.rack_problems(self.task, answer)))

    def test_patchpanel_neben_switch(self):
        answer = dict(self.good, **{"4": 8})
        problems = fg.rack_problems(self.task, answer)
        self.assertTrue(any(p.startswith("Patchpanel") for p in problems))
        self.assertTrue(any(p.startswith("Switch") for p in problems))

    def test_strom_und_kuehlung(self):
        answer = dict(self.good, **{"2": 7})           # Altserver 650 W dazu
        problems = fg.rack_problems(self.task, answer)
        self.assertTrue(any("USV schafft mit 20 % Reserve nur 800 W" in p
                            and "1255 W" in p for p in problems), problems)
        self.assertTrue(any("Kühlung" in p for p in problems))

    def test_vorgaben(self):
        answer = {"5": 1, "0": 3, "3": 4, "4": 5}          # nur ein Server
        self.assertTrue(any("2 × Server" in p for p in fg.rack_problems(self.task, answer)))
        task = json.loads(json.dumps(self.task))
        task["vorgaben"]["frei_min"] = 7                  # belegt sind 6 von 12 HE
        self.assertTrue(any("mindestens 7 HE" in p and "frei sind 6" in p
                            for p in fg.rack_problems(task, self.good)))

    def test_traglast_und_ports(self):
        task = fg.task_by_id("rack-servicecenter")
        # 6 = USV 3000 W (48 kg), 2 = PoE-Switch 48, 5 = Patchpanel 48
        problems = fg.rack_problems(task, {"6": 1, "2": 4, "5": 5})
        self.assertEqual(problems, ["Zu schwer: 57 kg bei 50 kg Traglast des Schranks."])
        problems = fg.rack_problems(task, {"7": 1, "0": 3, "3": 4})
        self.assertTrue(any("Zu wenige Ports (Switch): 24" in p for p in problems))
        # Zwei 24er-Paare sind ebenso richtig
        self.assertEqual(fg.rack_problems(task, {"7": 1, "3": 3, "0": 4, "1": 5, "4": 6}), [])

    def test_usv_im_raum(self):
        task = fg.task_by_id("rack-serverraum")
        # Storage + 2 Server + PoE-Switch = 1670 W: zu viel fuer Kuehlung und USV
        answer = {"0": 1, "1": 3, "2": 5, "4": 7, "6": 8}
        problems = fg.rack_problems(task, answer)
        self.assertTrue(any("nur 1600 W" in p for p in problems), problems)
        answer["5"] = answer.pop("4")
        self.assertEqual(fg.rack_problems(task, answer), [])

    def test_einbauen_verdraengt_und_rutscht(self):
        answer = fg.rack_place(self.task, {}, 5, 12)          # USV (2 HE) ganz oben
        self.assertEqual(answer, {"5": 11})
        answer = fg.rack_place(self.task, answer, 2, 9)        # Altserver HE 9-12
        self.assertEqual(answer, {"2": 9})                     # USV ist wieder frei
        answer = fg.rack_place(self.task, answer, 5, 1)
        self.assertEqual(fg.rack_occupant(self.task, answer, 2), 5)
        self.assertEqual(fg.rack_occupant(self.task, answer, 12), 2)
        self.assertIsNone(fg.rack_occupant(self.task, answer, 5))

    def test_anzeige_und_loesungstext(self):
        text, over = fg.rack_summary(self.task, self.good)
        self.assertIn("6 von 12 HE", text)
        self.assertIn("605 W von 800 W", text)
        self.assertFalse(over)
        payload = fg.evaluate(self.task, {"0": 1}, True, levels(100), 6)
        self.assertFalse(payload["richtig"])
        self.assertIn("Eine passende Belegung: HE 1–2: USV 1000 W",
                      fg.result_text(self.task, payload))

    def test_unloesbarer_schrank_wird_gefunden(self):
        content = json.loads(json.dumps(fg.GAME))
        task = next(t for t in content["aufgaben"] if t["id"] == "rack-leitstelle")
        task["schrank"]["traglast"] = 40
        problems = fg.validate_game_content(content)
        self.assertTrue(any("rack-leitstelle" in p and "nicht richtig bestuecken" in p
                            for p in problems), problems)


class FormularTest(unittest.TestCase):
    def test_eingaben_tolerant(self):
        self.assertEqual(fg.parse_number("1.234,50 €"), 1234.5)
        self.assertEqual(fg.parse_number("7351.34"), 7351.34)
        self.assertEqual(fg.parse_number("12.000"), 12000)
        self.assertEqual(fg.parse_number("16 TB"), 16)
        self.assertEqual(fg.parse_number("66,7 %"), 66.7)
        self.assertIsNone(fg.parse_number("viel"))
        self.assertEqual(fg.parse_prefix("/26"), 26)
        self.assertEqual(fg.parse_prefix("26"), 26)
        self.assertEqual(fg.parse_prefix("255.255.255.192"), 26)
        self.assertIsNone(fg.parse_prefix("255.0.255.0"))
        self.assertEqual(fg.parse_ip(" 10.20.0.128/26 "), "10.20.0.128")
        self.assertIsNone(fg.parse_ip("10.20.0.300"))

    def test_ip_plan_gleich_gross(self):
        task = fg.task_by_id("ipplan-talbahn")
        values = {f["id"]: f["anzeige"] for f in fg.form_fields(task)}
        self.assertEqual(values["praefix"], "/26")
        self.assertEqual(values["hosts"], "62")
        self.assertEqual(values["2.netz"], "192.168.40.128")
        self.assertEqual(values["3.broadcast"], "192.168.40.255")

    def test_ip_plan_vlsm(self):
        task = fg.task_by_id("vlsm-talbahn")
        values = {f["id"]: f["anzeige"] for f in fg.form_fields(task)}
        self.assertEqual([values["%d.praefix" % i] for i in range(4)],
                         ["/25", "/26", "/27", "/28"])
        self.assertEqual(values["3.netz"], "10.20.0.224")
        self.assertEqual(values["3.broadcast"], "10.20.0.239")
        # Reihenfolge in der Aufgabe egal: vergeben wird nach Groesse
        swapped = json.loads(json.dumps(task))
        swapped["daten"]["teilnetze"].reverse()
        plan = dict(fg.ip_plan(swapped))
        self.assertEqual(str(plan["WLAN"]), "10.20.0.0/25")
        self.assertEqual(str(plan["Technik"]), "10.20.0.224/28")

    def test_raid_wie_der_rechner(self):
        from fisi_core import raid_values
        task = fg.task_by_id("raid-dateiserver-neu")
        values = {f["id"]: f["soll"] for f in fg.form_fields(task)}
        self.assertEqual(values["netto"], raid_values("RAID 6", 6, 4)["netto"])
        self.assertEqual((values["brutto"], values["netto"], values["toleranz"]), (24, 16, 2))

    def test_angebot_und_leasing(self):
        task = fg.task_by_id("angebot-leitstelle")
        values = {f["id"]: f["soll"] for f in fg.form_fields(task)}
        self.assertEqual(values["netto"], 6177.6)
        self.assertEqual(values["ust"], 1173.74)
        self.assertEqual(values["brutto"], 7351.34)
        task = fg.task_by_id("leasing-server")
        values = {f["id"]: f["soll"] for f in fg.form_fields(task)}
        self.assertEqual((values["leasing"], values["kauf"], values["differenz"]),
                         (15940, 14400, 1540))
        self.assertEqual(values["guenstiger"], "Kauf")

    def test_pruefung_und_rueckmeldung(self):
        task = fg.task_by_id("angebot-leitstelle")
        answer = fg.find_solution(task)
        self.assertEqual(fg.check_answer(task, answer), (True, 0))
        answer["brutto"] = "7351,33"                     # ein Cent Rundung ist ok
        self.assertTrue(fg.check_answer(task, answer)[0])
        answer["gewinn"] = "617,76"                      # Gewinn auf den Netto gerechnet
        answer["ust"] = ""
        right, errors = fg.check_answer(task, answer)
        self.assertEqual((right, errors), (False, 2))
        payload = fg.evaluate(task, answer, False, levels(100), 7)
        text = fg.result_text(task, payload)
        self.assertIn("2 Felder stimmen nicht", text)
        self.assertIn("„617,76“ stimmt nicht, richtig ist 561,60 €", text)
        self.assertIn("Umsatzsteuer (19 %) fehlt", text)
        check = fg.form_check(task, answer)
        self.assertFalse(check["gewinn"])
        self.assertTrue(check["netto"])

    def test_kaputtes_formular_wird_gefunden(self):
        content = json.loads(json.dumps(fg.GAME))
        task = next(t for t in content["aufgaben"] if t["id"] == "raid-dateiserver-neu")
        task["daten"]["platten"] = 3
        problems = fg.validate_game_content(content)
        self.assertTrue(any("raid-dateiserver-neu" in p and "nicht berechnen" in p
                            for p in problems), problems)


if __name__ == "__main__":
    unittest.main(verbosity=1)
