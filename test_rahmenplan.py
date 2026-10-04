#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests fuer Version 0.55 (Lernqualitaet nach Ausbildungsrahmenplan) - ohne
Oberflaeche:
  * Rahmenplan als Daten (Teil 1): Punkte je Abschnitt, Summe C = 52 Wochen,
    A7 im 1.-18. Monat, jede Karte/Frage gehoert zu mindestens einem Punkt
  * Rahmenplan-Abdeckung (Teil 3): leere Datenbank, Nachrechnung, Schalter
    B/D/E, Filter, Lernfeld-Ansicht, "Jetzt ueben" je Punkt
  * Gewichtung neuer Inhalte (Teil 4): Verteilung, Mindestanteil, Schalter
    aus = 0.54, Wiederholungen unberuehrt, Naehe zum Pruefungstermin
  * Benutzerpfade im Problembericht und in fehler.log (Teil 6)
  * Umhaengen der 17 SQL-Inhalte: Reihenfolge und Fragetexte unveraendert,
    Antworten haengen am Inhalt, Abgleich-Format 2
  * Pruefungsthemen: neue Szenario-Themen und EXAM_THEME_TOPICS

Start:  python test_rahmenplan.py
"""

import collections
import datetime
import hashlib
import json
import os
import random
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import fisi_core as core  # noqa: E402
import fisi_diagnose as fd  # noqa: E402
import fisi_game as fg  # noqa: E402
import fisi_lernen as fl  # noqa: E402
import fisi_pruefung as fp  # noqa: E402
import fisi_rahmenplan as frp  # noqa: E402
import fisi_sync  # noqa: E402
from fisi_core import (KARTEIKARTEN, QUIZ_QUESTIONS, SRC_CARD, SRC_QUIZ,  # noqa: E402
                       DBManager, StatusBook)

BASE = os.path.dirname(os.path.abspath(__file__))


class TempDB:
    def setUp(self):
        self.folder = tempfile.mkdtemp(prefix="fisi_rp_")
        self._old = os.environ.get("FISI_DB_PATH")
        os.environ["FISI_DB_PATH"] = os.path.join(self.folder, "test.db")
        self.db = DBManager(os.environ["FISI_DB_PATH"])

    def tearDown(self):
        if self._old is None:
            os.environ.pop("FISI_DB_PATH", None)
        else:
            os.environ["FISI_DB_PATH"] = self._old
        shutil.rmtree(self.folder, ignore_errors=True)

    def answer(self, source, item, correct, timestamp, category=None):
        """Antwort mit festem Zeitpunkt (wie log_card/log_quiz_answer)."""
        category = category or item["cat"]
        if source == SRC_CARD:
            self.db._execute("INSERT INTO card_events (timestamp, category, question, mode,"
                             " correct, uid) VALUES (?, ?, ?, ?, ?, ?)",
                             (timestamp, category, item["q"], "lernen", int(correct),
                              self.db._uid()), commit=True)
        else:
            self.db._execute("INSERT INTO quiz_answers (timestamp, category, question,"
                             " correct, uid) VALUES (?, ?, ?, ?, ?)",
                             (timestamp, category, item["q"], int(correct),
                              self.db._uid()), commit=True)


# ============================================================================
#  TEIL 1: RAHMENPLAN ALS DATEN
# ============================================================================

class RahmenplanDatenTest(unittest.TestCase):

    def test_punkte_je_abschnitt(self):
        count = collections.Counter(point["abschnitt"] for point in frp.POINTS)
        self.assertEqual(dict(count), {"A": 51, "B": 13, "C": 19, "D": 19, "E": 20, "F": 22})
        self.assertEqual(len(frp.POINT_IDS), len(set(frp.POINT_IDS)))

    def test_summe_c_52_wochen(self):
        groups = {(p["nr"], p["gruppe"]): p["wochen_gruppe"] for p in frp.POINTS
                  if p["abschnitt"] == "C"}
        self.assertEqual(sum(groups.values()), 52)

    def test_a7_erste_18_monate(self):
        for point in frp.POINTS:
            if point["id"].startswith("A7"):
                self.assertEqual(point["zeitraum"], "1.–18.")
                self.assertTrue(point["ap1"])

    def test_ap1_nur_a1_bis_a7(self):
        for point in frp.POINTS:
            if point["ap1"]:
                self.assertEqual(point["abschnitt"], "A")
                self.assertLessEqual(point["nr"], 7)

    def test_optionale_abschnitte(self):
        self.assertEqual(frp.OPTIONAL_SECTIONS, ["B", "D", "E"])
        self.assertEqual(frp.enabled_sections(frp.rp_settings({})), ["A", "C", "F"])

    def test_inhalte_gueltig(self):
        self.assertEqual(frp.validate_rahmenplan(), [])
        self.assertEqual(core.validate_content(), [])

    def test_jeder_inhalt_hat_einen_punkt(self):
        mapping = frp.item_points()
        self.assertEqual(len(mapping), len(KARTEIKARTEN) + len(QUIZ_QUESTIONS))
        for key, points in mapping.items():
            self.assertTrue(points, key)
            for point_id in points:
                self.assertIn(point_id, frp.POINT)

    def test_eigenes_feld_rahmenplan_gilt(self):
        mapping = frp.item_points()
        own = [item for item in KARTEIKARTEN if item.get("rahmenplan")]
        for item in own[:50]:
            self.assertEqual(mapping[(SRC_CARD, item["q"])], item["rahmenplan"])

    def test_a2e_nur_englisch(self):
        """Nicos Rueckmeldung: A2e war mit Zufallstreffern zu gut bewertet."""
        rule = [r for r in frp.MATCH_RULES if r[0] == "A2e"][0]
        self.assertNotIn("handbuch", rule[2])
        self.assertNotIn("recherche", rule[2])


# ============================================================================
#  TEIL 3: ABDECKUNG
# ============================================================================

class AbdeckungTest(TempDB, unittest.TestCase):

    def test_leere_datenbank(self):
        coverage = frp.Coverage(StatusBook(self.db), frp.rp_settings({}))
        self.assertFalse(coverage.any_answers)
        for point_id in frp.POINT_IDS:
            value = coverage.point[point_id]
            self.assertIn(value, (0.0, None))
        for section in coverage.sections():
            self.assertEqual(section["wert"], 0.0)

    def test_nachrechnung_eines_punktes(self):
        keys = frp.point_items()["C3e"]
        by_q = {q["q"]: q for q in QUIZ_QUESTIONS}
        for number, question in enumerate(keys[SRC_QUIZ][:12]):
            self.answer(SRC_QUIZ, by_q[question], number % 3 != 0,
                        "2026-10-01 10:%02d:00" % number)
        book = StatusBook(self.db)
        coverage = frp.Coverage(book, frp.rp_settings({}))
        params = fg.topic_params()
        answers = [number % 3 != 0 for number in range(12)][::-1]
        total = len(keys[SRC_QUIZ]) + len(keys[SRC_CARD])
        expected = fg.knowledge_from_answers({"x": answers}, {"x": 12 * 100.0 / total},
                                             params, keys=["x"])["x"]
        self.assertAlmostEqual(coverage.point["C3e"], expected)
        self.assertTrue(coverage.any_answers)

    def test_thema_wie_wissensstand(self):
        """Ein Lernthema in der Lernfeld-Ansicht hat denselben Wert wie der
        Wissensstand je Thema (fisi_game.topic_knowledge)."""
        rng = random.Random(5)
        items = [q for q in QUIZ_QUESTIONS if q.get("thema") == "storage"][:30]
        cards = [c for c in KARTEIKARTEN if c.get("thema") == "storage"][:10]
        for number, item in enumerate(items):
            self.answer(SRC_QUIZ, item, rng.random() < 0.7, "2026-10-02 08:%02d:00" % number)
        for number, item in enumerate(cards):
            self.answer(SRC_CARD, item, rng.random() < 0.7, "2026-10-02 09:%02d:00" % number)
        coverage = frp.Coverage(StatusBook(self.db), frp.rp_settings({}))
        value = coverage.group_value(frp.topic_items("storage"))
        self.assertAlmostEqual(value, fg.topic_knowledge(self.db)["storage"], places=1)

    def test_schalter_bde(self):
        book = StatusBook(self.db)
        base = frp.Coverage(book, frp.rp_settings({}))
        self.assertEqual([s["id"] for s in base.sections()], ["A", "C", "F"])
        allon = frp.Coverage(book, frp.rp_settings({"rp_abschnitt_b": True,
                                                    "rp_abschnitt_d": True,
                                                    "rp_abschnitt_e": True}))
        self.assertEqual([s["id"] for s in allon.sections()], frp.SECTIONS)
        fields = [f["id"] for year in base.fields() for f in year["felder"]]
        self.assertNotIn("LF 10a", fields)
        fields = [f["id"] for year in allon.fields() for f in year["felder"]]
        self.assertIn("LF 10a", fields)

    def test_filter(self):
        coverage = frp.Coverage(StatusBook(self.db), frp.rp_settings({}))
        ap1 = coverage.sections("AP1")
        self.assertEqual([s["id"] for s in ap1], ["A"])
        for position in ap1[0]["positionen"]:
            for point in position["punkte"]:
                self.assertTrue(frp.POINT[point["id"]]["ap1"])
        wiso = coverage.sections("WiSo")
        self.assertEqual([s["id"] for s in wiso], ["F"])
        for area in ("Konzeption", "Netzwerke", "Projekt"):
            for section in coverage.sections(area):
                for position in section["positionen"]:
                    for point in position["punkte"]:
                        self.assertIn(area, frp.POINT[point["id"]]["ap2"])

    def test_aktuelles_lernfeld_oben(self):
        values = frp.rp_settings({"rp_lernfeld": "LF 4"})
        coverage = frp.Coverage(StatusBook(self.db), values)
        year = coverage.fields()[0]
        self.assertEqual(year["felder"][0]["id"], "LF 4")
        self.assertTrue(year["felder"][0]["aktuell"])
        lf7 = [f for y in coverage.fields() for f in y["felder"] if f["id"] == "LF 7"][0]
        self.assertEqual(lf7["themen"], [])
        self.assertIsNone(lf7["wert"])

    def test_ampel(self):
        self.assertEqual(frp.level(0), frp.LEVEL_LOW)
        self.assertEqual(frp.level(49.9), frp.LEVEL_LOW)
        self.assertEqual(frp.level(50), frp.LEVEL_MID)
        self.assertEqual(frp.level(79.9), frp.LEVEL_MID)
        self.assertEqual(frp.level(80), frp.LEVEL_HIGH)

    def test_ampel_kontrast_hell_und_dunkel(self):
        import fisi_theme as ft
        old = ft.current_mode
        try:
            for mode in (ft.MODE_DARK, ft.MODE_LIGHT):
                ft.apply_mode(mode)
                for key in frp.LEVEL_COLOR_KEY.values():
                    for surface in ("card", "card_alt"):
                        self.assertGreaterEqual(ft.contrast(ft.C[key], ft.C[surface]), 4.5,
                                                (mode, key, surface))
        finally:
            ft.apply_mode(old)

    def test_jetzt_ueben_je_punkt(self):
        parts = frp.point_practice_parts(StatusBook(self.db), "A3a", rng=random.Random(1))
        keys = frp.point_items()["A3a"]
        self.assertTrue(parts)
        for source, chosen in parts:
            self.assertLessEqual(len(chosen), fl.PRACTICE_ROUND)
            for key in chosen:
                self.assertIn(key, keys[source])
        self.assertEqual(parts[0][0], SRC_QUIZ)

    def test_einstellungen_je_geraet(self):
        values = frp.load_rp_settings()
        self.assertFalse(values["rp_abschnitt_b"])
        self.assertTrue(values["rp_gewichtung"])
        self.assertEqual(values["rp_termin_ap1"], "2027-09-29")
        self.assertEqual(values["rp_termin_ap2"], "2028-04-26")
        frp.save_rp_settings(rp_abschnitt_d=True, rp_termin_ap1="01.03.2027", fremd=1)
        values = frp.load_rp_settings()
        self.assertTrue(values["rp_abschnitt_d"])
        self.assertEqual(values["rp_termin_ap1"], "2027-03-01")
        self.assertEqual(frp.date_text(values["rp_termin_ap1"]), "01.03.2027")
        self.assertIsNone(frp.parse_date("31.02.2027"))
        self.assertNotIn("rp_abschnitt_d", fisi_sync.SYNC_TABLES if hasattr(
            fisi_sync, "SYNC_TABLES") else {})


# ============================================================================
#  TEIL 4: GEWICHTUNG
# ============================================================================

def preferred_order_054(book, source, keys, rng=None):
    """StatusBook.preferred_order wie in Version 0.54 (zum Vergleich)."""
    fresh, repeat = [], []
    for key in keys:
        if not book.touched(source, key):
            fresh.append(key)
        else:
            status, level = book.status(source, key)
            rank = {(core.Q_PRACTICE, core.LEVEL_RED): 0, (core.Q_PRACTICE, core.LEVEL_YELLOW): 1,
                    (core.Q_OPEN, ""): 2}.get((status, level), 3)
            repeat.append((rank, key))
    if rng is not None:
        rng.shuffle(fresh)
        rng.shuffle(repeat)
    repeat = [key for _rank, key in sorted(repeat, key=lambda item: item[0])]
    ordered = []
    while fresh or repeat:
        ordered += fresh[:core.NEW_PER_REPEAT]
        fresh = fresh[core.NEW_PER_REPEAT:]
        if repeat:
            ordered.append(repeat.pop(0))
        if not fresh:
            ordered += repeat
            repeat = []
    return ordered


class GewichtungTest(TempDB, unittest.TestCase):
    NO_DATES = {"rp_termin_ap1": "", "rp_termin_ap2": ""}

    def _book_with_answers(self):
        for number, item in enumerate(QUIZ_QUESTIONS[:40]):
            self.answer(SRC_QUIZ, item, number % 4 != 0, "2026-09-%02d 10:00:00"
                        % (1 + number % 28))
        for number, item in enumerate(KARTEIKARTEN[:40]):
            self.answer(SRC_CARD, item, number % 5 != 0, "2026-09-%02d 11:00:00"
                        % (1 + number % 28))
        return StatusBook(self.db)

    def test_schalter_aus_wie_054(self):
        book = self._book_with_answers()
        self.assertIsNone(frp.fresh_order(SRC_CARD, frp.rp_settings({"rp_gewichtung": False})))
        keys = [c["q"] for c in KARTEIKARTEN]
        self.assertEqual(book.preferred_order(SRC_CARD, keys, fresh_order=None),
                         preferred_order_054(book, SRC_CARD, keys))
        quiz = [q["q"] for q in QUIZ_QUESTIONS]
        self.assertEqual(book.preferred_order(SRC_QUIZ, quiz, rng=random.Random(3)),
                         preferred_order_054(book, SRC_QUIZ, quiz, rng=random.Random(3)))

    def test_nur_neue_inhalte_umsortiert(self):
        book = self._book_with_answers()
        keys = [c["q"] for c in KARTEIKARTEN]
        order = frp.fresh_order(SRC_CARD, frp.rp_settings({}), datetime.date(2026, 10, 4))
        new = book.preferred_order(SRC_CARD, keys, fresh_order=order)
        old = preferred_order_054(book, SRC_CARD, keys)
        self.assertEqual(sorted(new), sorted(old))
        # Wiederholungen stehen an denselben Stellen in derselben Reihenfolge
        self.assertEqual([k for k in new if book.touched(SRC_CARD, k)],
                         [k for k in old if book.touched(SRC_CARD, k)])
        self.assertEqual([i for i, k in enumerate(new) if book.touched(SRC_CARD, k)],
                         [i for i, k in enumerate(old) if book.touched(SRC_CARD, k)])

    def test_wiederholungsplan_unberuehrt(self):
        book = self._book_with_answers()
        today = datetime.date(2026, 10, 4)
        before = fl.ReviewPlan(book, today=today).due
        frp.save_rp_settings(rp_gewichtung=False)
        after = fl.ReviewPlan(StatusBook(self.db), today=today).due
        self.assertEqual(before, after)

    def test_gleicher_tag_gleiche_reihenfolge(self):
        keys = [q["q"] for q in QUIZ_QUESTIONS[:300]]
        values = frp.rp_settings(self.NO_DATES)
        day = datetime.date(2026, 10, 4)
        first = frp.weighted_order(SRC_QUIZ, keys, values, day)
        self.assertEqual(first, frp.weighted_order(SRC_QUIZ, list(reversed(keys)), values, day))
        self.assertNotEqual(first, frp.weighted_order(SRC_QUIZ, keys, values,
                                                      day + datetime.timedelta(days=1)))

    def test_gewichte_mild(self):
        values = frp.rp_settings(self.NO_DATES)
        weights = [frp.item_weight(SRC_QUIZ, q["q"], values) for q in QUIZ_QUESTIONS] + \
            [frp.item_weight(SRC_CARD, c["q"], values) for c in KARTEIKARTEN]
        self.assertGreaterEqual(min(weights), 1.0)
        self.assertLessEqual(max(weights), 3.0)
        # Mindestanteil: das kleinste Gewicht ist mindestens ein Drittel des groessten
        self.assertGreaterEqual(min(weights) / max(weights), 1 / 3.0)

    def test_verteilung_entspricht_gewichten(self):
        """Ueber 4000 Auswahlen (Tage) kommt jeder Fachbereich so oft zuerst
        dran, wie es seinem Anteil am Gesamtgewicht entspricht (Abweichung
        unter 2 Prozentpunkten), und jedes Thema kommt vor."""
        rng = random.Random(11)
        pool = rng.sample(QUIZ_QUESTIONS, 240)
        keys = [q["q"] for q in pool]
        cat = {q["q"]: q["cat"] for q in pool}
        topic = {q["q"]: q["thema"] for q in pool}
        values = frp.rp_settings(self.NO_DATES)
        weight = {key: frp.item_weight(SRC_QUIZ, key, values) for key in keys}
        total = sum(weight.values())
        expected = collections.Counter()
        for key in keys:
            expected[cat[key]] += weight[key] / total
        seen = collections.Counter()
        topics = set()
        start = datetime.date(2026, 1, 1)
        rounds = 4000
        for offset in range(rounds):
            day = start + datetime.timedelta(days=offset)
            scored = max(keys, key=lambda k: frp._day_random(SRC_QUIZ, k, day)
                         ** (1.0 / weight[k]))
            seen[cat[scored]] += 1
            topics.add(topic[scored])
        for name, share in expected.items():
            self.assertLess(abs(seen[name] / float(rounds) - share), 0.02, name)
        self.assertEqual(topics, set(topic.values()))

    def test_pruefungsnaehe(self):
        values = frp.rp_settings({})
        self.assertIsNone(frp.exam_phase(values, datetime.date(2027, 3, 28)))
        self.assertEqual(frp.exam_phase(values, datetime.date(2027, 3, 29)), "ap1")
        self.assertEqual(frp.exam_phase(values, datetime.date(2027, 9, 28)), "ap1")
        self.assertIsNone(frp.exam_phase(values, datetime.date(2027, 10, 1)))
        self.assertEqual(frp.exam_phase(values, datetime.date(2027, 10, 26)), "ap2")
        self.assertIsNone(frp.exam_phase(values, datetime.date(2028, 4, 26)))
        self.assertIsNone(frp.exam_phase(frp.rp_settings(self.NO_DATES),
                                         datetime.date(2027, 6, 1)))
        # AP1-relevanter Inhalt: Faktor 1,5 vor der AP1
        key = frp.point_items()["A7f"][SRC_QUIZ][0]
        normal = frp.item_weight(SRC_QUIZ, key, values, datetime.date(2026, 10, 4))
        near = frp.item_weight(SRC_QUIZ, key, values, datetime.date(2027, 6, 1))
        self.assertAlmostEqual(near, normal * frp.EXAM_FACTOR)


# ============================================================================
#  TEIL 6: BENUTZERPFADE
# ============================================================================

class BenutzerpfadTest(TempDB, unittest.TestCase):

    def test_windows(self):
        env = {"APPDATA": r"C:\Users\Nico Muster\AppData\Roaming",
               "LOCALAPPDATA": r"C:\Users\Nico Muster\AppData\Local"}
        text = (r"Datenordner: C:\Users\Nico Muster\AppData\Roaming\FISI-Lernplattform" "\n"
                r'File "C:\Users\Nico Muster\AppData\Local\Programs\FISI\app_gui.py"' "\n"
                r"C:\Users\Nico Muster\Desktop\x.txt" "\n"
                r"c:/users/nico muster/Documents" "\n"
                r"D:\Users\Anna\Daten")
        result = core.anonymize_paths(text, env=env, home=r"C:\Users\Nico Muster")
        self.assertIn(r"Datenordner: %APPDATA%\FISI-Lernplattform", result)
        self.assertIn(r"%LOCALAPPDATA%\Programs", result)
        self.assertIn(r"~\Desktop", result)
        self.assertNotIn("Nico", result)
        self.assertNotIn("Muster", result)
        self.assertNotIn("Anna", result)
        self.assertIn("…", result)

    def test_linux_und_mac(self):
        text = "/home/nico/.local/share/FISI\n/Users/nico/Library\n/home/anna/x"
        result = core.anonymize_paths(text, env={}, home="/home/nico")
        self.assertIn("~/.local/share/FISI", result)
        self.assertNotIn("nico", result)
        self.assertNotIn("anna", result)

    def test_bericht_und_fehlerlog(self):
        home = os.path.expanduser("~")
        core.write_error_log("Fehler in %s" % os.path.join(home, "geheim", "datei.py"))
        with open(core.error_log_path(), encoding="utf-8") as handle:
            log = handle.read()
        if home not in ("/", "~") and len(home) > 3:
            self.assertNotIn(home, log)
        report = fd.build_report(self.db, "0.55", geraet="PC", settings={})
        if len(home) > 3:
            self.assertNotIn(home + os.sep, report)
        self.assertIn("Datenordner:", report)

    def test_token_filter_bleibt(self):
        token = "github_pat_11GEHEIM1234567890abcdefXYZ"
        text = fd.build_report(self.db, "0.55", settings={"sync_token": token})
        self.assertNotIn(token, text)


# ============================================================================
#  SQL-INHALTE UMGEHAENGT (EINZIGE AUSNAHME VOM GRUNDSATZ)
# ============================================================================

# Fragetexte in Dateireihenfolge, Stand 0.54 (sha256 ueber die Fragen, mit
# Zeilenumbruch verbunden). Neue Inhalte werden nur angehaengt.
STAND_054 = {
    "karteikarten": (1400, "5d94402f4cd4eb4836d3b8e25fb536a474a9f6b8e98318d2974f515abf7ffa83"),
    "quizfragen": (1946, "6c6b5eda7575fde0ce14d05c2210ddad131d17ecd2bf73d4a4911aa68fae4296"),
    "szenarien_ap1": (250, "833fea3f1964c0feaf212c69e6f833bd06499d9342b4ac2923f03589153ec7ff"),
    "szenarien_ap2": (300, "05ad5c7df8a76814617a90a929eac75dc3127d778cfe8148a11466ee0f49d58b"),
    "projektarbeiten": (50, "d64254b71ce4a0d2f812d2e5afdb7da4d328ef7873f01f7226bd7e76553c6e58"),
}
MOVED_CARDS = {722: "modellierung", 723: "modellierung", 1208: "sql", 1209: "sql", 1210: "sql"}
MOVED_QUIZ = {1009: "modellierung", 1010: "sql", 1011: "sql", 1012: "db_betrieb",
              1622: "sql", 1623: "sql", 1624: "sql", 1625: "sql",
              1736: "sql", 1737: "sql", 1738: "sql", 1739: "sql"}


def _raw(name):
    with open(os.path.join(BASE, "inhalte", name + ".json"), encoding="utf-8") as handle:
        return json.load(handle)


class UmhaengenTest(TempDB, unittest.TestCase):

    def test_nur_angehaengt(self):
        for name, (count, digest) in STAND_054.items():
            items = _raw(name)
            field = "q" if "q" in items[0] else "title"
            self.assertGreaterEqual(len(items), count, name)
            text = "\n".join(item[field] for item in items[:count])
            self.assertEqual(hashlib.sha256(text.encode("utf-8")).hexdigest(), digest, name)

    def test_neue_themen(self):
        cards, quiz = _raw("karteikarten"), _raw("quizfragen")
        for index, topic in MOVED_CARDS.items():
            self.assertEqual(cards[index]["thema"], topic)
            self.assertEqual(cards[index]["cat"], "datenbanken")
        for index, topic in MOVED_QUIZ.items():
            self.assertEqual(quiz[index]["thema"], topic)
            self.assertEqual(quiz[index]["cat"], "datenbanken")

    def test_antworten_haengen_am_inhalt(self):
        """Eine alte Antwort (Fachbereich noch Systeme) zaehlt nach dem
        Umhaengen zum selben Inhalt und zu seinem neuen Thema."""
        card = KARTEIKARTEN[1208]
        self.answer(SRC_CARD, card, False, "2026-09-01 10:00:00", category=core.CAT_SYS)
        book = StatusBook(self.db)
        self.assertEqual(book.status(SRC_CARD, card["q"])[0], core.Q_PRACTICE)
        self.assertEqual(core.event_topic(1, card["q"]), "sql")
        self.assertEqual(self.db.topic_answers(50).get("sql"), [False])

    def test_abgleich_format_2(self):
        self.assertEqual(fisi_sync.FORMAT, 2)


# ============================================================================
#  PRUEFUNGSTHEMEN
# ============================================================================

AP1_NEW = "Arbeitsplatz einrichten: Bedarf, Beschaffung, Übergabe"


class PruefungsthemenTest(unittest.TestCase):

    def test_exam_theme_topics_gueltig(self):
        for name, topics in fl.EXAM_THEME_TOPICS.items():
            for topic in topics:
                self.assertIn(topic, core.TOPIC_NAME, name)
        for theme in {s["theme"] for s in core.SZENARIEN + core.AP1_SZENARIEN}:
            self.assertIn(theme, fl.EXAM_THEME_TOPICS)

    def test_ergaenzungen(self):
        self.assertIn("wan_vpn", fl.EXAM_THEME_TOPICS["Subnetting & Routing"])
        self.assertIn("recht", fl.EXAM_THEME_TOPICS["Wirtschaft & Beratung"])
        self.assertIn("kalkulation", fl.EXAM_THEME_TOPICS["Wirtschafts- und Sozialkunde"])
        self.assertEqual(fl.practice_topics(AP1_NEW)[0], "beschaffung")

    def test_neue_themen_im_dashboard_block(self):
        self.assertEqual(core.theme_block(AP1_NEW), "Projektplanung")
        self.assertEqual(core.theme_block("Systemadministration"), "Storage & RAID")
        self.assertEqual(core.theme_block("Automatisierung & Skripte"), "Storage & RAID")
        self.assertEqual(len(core.AP1_THEMES), 5)
        self.assertEqual(len(core.AP2_THEMES), 5)

    def test_simulation(self):
        ap1 = fp.EXAM[fp.AP1]
        self.assertEqual(len(ap1["themen"]), 4)
        self.assertEqual(ap1["minuten"], 90)
        self.assertEqual(ap1["themen"][3], ["Projektplanung", AP1_NEW])
        self.assertEqual(fp.WEIGHTS[fp.AP1], 20)
        pool = fp.EXAM[fp.KONZEPTION]["pool"]
        self.assertEqual(len(pool), 7)
        self.assertIn("Systemadministration", pool)
        self.assertIn("Automatisierung & Skripte", pool)
        for theme in pool:
            self.assertTrue(fp.usable_indices("ap2", theme), theme)
        self.assertTrue(fp.usable_indices("ap1", AP1_NEW))
        for seed in range(30):
            state = fp.new_exam(fp.KONZEPTION, seed=seed)
            self.assertEqual(len(state["aufgaben"]), 4)
            state = fp.new_exam(fp.AP1, seed=seed)
            self.assertEqual(len(state["aufgaben"]), 4)


if __name__ == "__main__":
    unittest.main(verbosity=1)
