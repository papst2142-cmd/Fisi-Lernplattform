#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests fuer die kleinen Werkzeuge ab 0.54 - ohne Oberflaeche:
  * Problem melden (fisi_diagnose.py): kein Token im Bericht, fehler.log
    fehlt/leer, 256-KB-Grenze
  * Schwaechen direkt ueben (fisi_lernen.topic_practice)
  * Suche im Notizblock (fisi_core.notebook_search)
  * Aufgaben pro Tag (fisi_lernen.daily_series)

Datenbank und einstellungen.json liegen in einem Temp-Ordner (FISI_DB_PATH).

Start:  python test_werkzeuge.py
"""

import datetime
import json
import os
import shutil
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import fisi_diagnose as fd  # noqa: E402
import fisi_lernen as fl  # noqa: E402
from fisi_core import (ERROR_LOG_MAX, FILTER_ALL, KARTEIKARTEN, LEVEL_RED, Q_PRACTICE,  # noqa: E402
                       QUIZ_QUESTIONS, SRC_AP2, SRC_CARD, SRC_QUIZ, TOPIC_NAME, DBManager,
                       StatusBook, error_log_path, notebook_entries, notebook_search)
from fisi_update import load_settings, save_settings  # noqa: E402

FAKE_TOKEN = "github_pat_11GEHEIM1234567890abcdefXYZ"
CLASSIC_TOKEN = "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"


class TempDataMixin:
    def setUp(self):
        self.folder = tempfile.mkdtemp(prefix="fisi_test_")
        self._old_env = os.environ.get("FISI_DB_PATH")
        os.environ["FISI_DB_PATH"] = os.path.join(self.folder, "fisi_lernplattform.db")
        self.db = DBManager()

    def tearDown(self):
        if self._old_env is None:
            os.environ.pop("FISI_DB_PATH", None)
        else:
            os.environ["FISI_DB_PATH"] = self._old_env
        shutil.rmtree(self.folder, ignore_errors=True)


# ============================================================================
#  PROBLEM MELDEN
# ============================================================================

class DiagnoseTest(TempDataMixin, unittest.TestCase):

    def _write_log(self, text):
        with open(error_log_path(), "w", encoding="utf-8") as handle:
            handle.write(text)

    def test_log_liegt_im_datenordner(self):
        self.assertEqual(os.path.dirname(error_log_path()), self.folder)

    def test_kopfdaten(self):
        text = fd.build_report(self.db, "0.54", "PC", settings={})
        self.assertIn("Programmversion: 0.54", text)
        self.assertIn("Gerät: PC · ", text)
        self.assertIn("Datenordner: %s" % self.folder, text)
        self.assertIn("Datenbankgröße: ", text)
        self.assertIn("Ereignisse: 0 Lern-Einträge, 0 Spielereignisse", text)
        self.assertIn("Abgleich eingerichtet: nein", text)

    def test_ereignisse_werden_gezaehlt(self):
        self.db.log_card("Netzwerk", "Frage", "lernen", True)
        self.db.log_quiz_answer("Netzwerk", "Quiz", False)
        self.db.log_game_event("start", "{}")
        text = fd.build_report(self.db, "0.54", "PC", settings={})
        self.assertIn("Ereignisse: 2 Lern-Einträge, 1 Spielereignis", text)

    def test_fehlende_log_datei_freundlich(self):
        self.assertFalse(os.path.exists(error_log_path()))
        text = fd.build_report(self.db, "0.54", "PC", settings={})
        self.assertIn(fd.NO_LOG, text)

    def test_leere_log_datei_freundlich(self):
        self._write_log("  \n")
        self.assertEqual(fd.read_log(), "")
        self.assertIn(fd.NO_LOG, fd.build_report(self.db, "0.54", "PC", settings={}))

    def test_log_inhalt(self):
        self._write_log("=== 2026-10-01 | Version 0.53 | linux ===\nZeroDivisionError\n")
        text = fd.build_report(self.db, "0.54", "PC", settings={})
        self.assertIn("ZeroDivisionError", text)
        self.assertNotIn(fd.NO_LOG, text)

    def test_grenze_256_kb(self):
        line = "x" * 99 + "\n"
        self._write_log("ANFANG\n" + line * (ERROR_LOG_MAX // len(line) + 500) + "ENDE\n")
        self.assertGreater(os.path.getsize(error_log_path()), ERROR_LOG_MAX)
        log = fd.read_log()
        self.assertNotIn("ANFANG", log)
        self.assertTrue(log.endswith("ENDE"))
        self.assertTrue(log.startswith(fd.LOG_CUT % (ERROR_LOG_MAX // 1024)))
        # nur ganze Zeilen nach dem Hinweis
        for row in log.splitlines()[1:-1]:
            self.assertEqual(row, "x" * 99)
        self.assertLessEqual(len(log.encode("utf-8")), ERROR_LOG_MAX + 200)

    def test_kleine_datei_ungekuerzt(self):
        self._write_log("ANFANG\nENDE\n")
        self.assertEqual(fd.read_log(), "ANFANG\nENDE")

    def test_token_aus_einstellungen_nie_im_bericht(self):
        settings = load_settings()
        settings.update({"sync_repo": "nico/fisi-lernstand", "sync_token": FAKE_TOKEN})
        save_settings(settings)
        # der Token steht auch im Fehlerprotokoll (z.B. in einer Fehlermeldung)
        self._write_log("Fehler beim Abgleich mit %s\nheaders={'Authorization': 'Bearer %s'}\n"
                        % (FAKE_TOKEN, FAKE_TOKEN))
        text = fd.build_report(self.db, "0.54", "PC")
        self.assertNotIn(FAKE_TOKEN, text)
        self.assertNotIn("GEHEIM", text)
        self.assertIn(fd.REDACTED, text)
        self.assertIn("Abgleich eingerichtet: ja", text)

    def test_unbekannte_token_im_log_werden_entfernt(self):
        """Auch Zugangsdaten, die nicht (mehr) in den Einstellungen stehen."""
        self._write_log("\n".join([
            "alter Token %s" % CLASSIC_TOKEN,
            "fein: github_pat_ZZZZZZZZZZZZZZZZZZZZZZZZ_yyyy",
            "Authorization: token abcdefghijklmnop",
            '{"sync_token": "irgendwasGeheimes"}',
            "password=hunter2geheim",
            "Passwort: meinGeheimesPasswort",
            "https://nutzer:kennwortGeheim@github.com/repo.git",
            "https://%s@github.com/repo.git" % "tokenGeheim123"]))
        text = fd.build_report(self.db, "0.54", "PC", settings={})
        for secret in (CLASSIC_TOKEN, "github_pat_ZZZZ", "abcdefghijklmnop",
                       "irgendwasGeheimes", "hunter2geheim", "meinGeheimesPasswort",
                       "kennwortGeheim", "tokenGeheim123"):
            self.assertNotIn(secret, text, secret)
        self.assertIn("github.com/repo.git", text)

    def test_einstellungen_mit_passwort(self):
        text = fd.build_report(self.db, "0.54", "PC",
                               settings={"proxy_passwort": "Sommer2026!x", "x": "harmlos"})
        self.assertNotIn("Sommer2026!x", text)

    def test_einstellungsdatei_kommt_nicht_in_den_bericht(self):
        settings = {"sync_repo": "nico/fisi-lernstand", "sync_token": FAKE_TOKEN,
                    "farbe": "violett"}
        text = fd.build_report(self.db, "0.54", "Handy", settings=settings)
        self.assertNotIn("nico/fisi-lernstand", text)
        self.assertNotIn(json.dumps(settings), text)

    def test_scrub_laesst_normalen_text(self):
        text = "Datenordner: /home/nico/.local/share\nTagesziel: 20 Aufgaben"
        self.assertEqual(fd.scrub(text), text)

    def test_dateiname(self):
        name = fd.default_name(datetime.datetime(2026, 10, 2, 14, 23))
        self.assertEqual(name, "FISI-Problembericht_2026-10-02_1423.txt")

    # -- ab 0.59.2: haenger.log und laeuft.info -----------------------------

    def test_ohne_haenger_dateien_keine_abschnitte(self):
        text = fd.build_report(self.db, "0.59.2", "PC", settings={})
        self.assertNotIn("--- haenger.log ---", text)
        self.assertNotIn("--- laeuft.info ---", text)

    def test_haenger_log_und_laeuft_info_angehaengt(self):
        home = os.path.expanduser("~")
        with open(os.path.join(self.folder, fd.HANG_LOG_NAME), "w", encoding="utf-8") as h:
            h.write("=== 2026-10-07 08:00:03 | Start | Version 0.59.2 ===\n"
                    'Thread 0x1 (most recent call first):\n'
                    '  File "%s/quelle/app_gui.py", line 7204 in _recolor\n'
                    "token=ghp_ABCDEFGHIJKLMNOPQRSTUV\n" % home)
        with open(os.path.join(self.folder, fd.INFO_NAME), "w", encoding="utf-8") as h:
            h.write("pid=4321\nstart=2026-10-07 08:00:03\nversion=0.59.2\n")
        text = fd.build_report(self.db, "0.59.2", "PC", settings={})
        self.assertIn("--- haenger.log ---", text)
        self.assertIn("line 7204 in _recolor", text)
        self.assertIn("--- laeuft.info ---", text)
        self.assertIn("pid=4321", text)
        # Benutzerpfad und Zugangsdaten entfernt wie bei fehler.log
        self.assertNotIn(home + "/quelle", text)
        self.assertNotIn("ghp_ABCDEFGHIJKLMNOPQRSTUV", text)
        # Reihenfolge: fehler.log, (update.log), haenger.log, laeuft.info
        self.assertLess(text.index("--- fehler.log ---"), text.index("--- haenger.log ---"))
        self.assertLess(text.index("--- haenger.log ---"), text.index("--- laeuft.info ---"))

    def test_haenger_log_gekuerzt(self):
        line = "y" * 99 + "\n"
        with open(os.path.join(self.folder, fd.HANG_LOG_NAME), "w", encoding="utf-8") as h:
            h.write("ANFANG\n" + line * 1000 + "ENDE\n")
        text = fd.build_report(self.db, "0.59.2", "PC", settings={})
        part = text.split("--- haenger.log ---", 1)[1]
        self.assertNotIn("ANFANG", part)
        self.assertIn("ENDE", part)
        self.assertIn(fd.LOG_CUT % (fd.HANG_LOG_MAX // 1024), part)
        self.assertLess(len(part.encode("utf-8")), fd.HANG_LOG_MAX + 500)

    def test_kaputte_datenbank(self):
        with open(self.db.db_path, "wb") as handle:
            handle.write(b"kein sqlite")
        self.db.error_handler = lambda _message: None
        text = fd.build_report(self.db, "0.54", "PC", settings={})
        self.assertIn("Programmversion: 0.54", text)


# ============================================================================
#  SCHWAECHEN DIREKT UEBEN
# ============================================================================

def _book(answers):
    """StatusBook aus {(quelle, frage): [True/False, ...]}."""
    results = {}
    for number, (key, values) in enumerate(answers.items()):
        results[key] = [("2026-10-01 10:%02d:%02d" % (number % 60, index), value)
                        for index, value in enumerate(values)]
    return StatusBook(results=results)


class TopicPracticeTest(unittest.TestCase):

    def test_alle_pruefungsthemen_zugeordnet(self):
        from fisi_core import AP1_SZENARIEN, SZENARIEN
        import fisi_pruefung as fp
        names = {s["theme"] for s in SZENARIEN} | {s["theme"] for s in AP1_SZENARIEN}
        names |= {"Recht & Verträge", "Arbeitswelt"}
        for exam in fp.EXAMS:
            if isinstance(exam.get("themen"), list):
                names |= {name for group in exam["themen"] for name in group}
            names |= set(exam.get("pool", []))
        for name in names:
            topics = fl.practice_topics(name)
            self.assertTrue(topics, name)
            for topic in topics:
                self.assertIn(topic, TOPIC_NAME)

    def test_themen_id_und_name(self):
        self.assertEqual(fl.practice_topics("ipv4"), ["ipv4"])
        self.assertEqual(fl.practice_topics(TOPIC_NAME["ipv4"]), ["ipv4"])
        self.assertEqual(fl.practice_topics("gibt es nicht"), [])

    def test_nur_fragen_des_themas(self):
        source, keys = fl.topic_practice(StatusBook(results={}), ["routing"])
        pool = {q["q"]: q for q in QUIZ_QUESTIONS} if source == SRC_QUIZ else \
            {c["q"]: c for c in KARTEIKARTEN}
        self.assertTrue(keys)
        for key in keys:
            self.assertEqual(pool[key].get("thema"), "routing")

    def test_laenge_wie_bisher(self):
        source, keys = fl.topic_practice(StatusBook(results={}), ["kalkulation"])
        self.assertEqual(len(keys), fl.PRACTICE_ROUND)
        self.assertEqual(fl.PRACTICE_ROUND, 10)
        _source, keys = fl.topic_practice(StatusBook(results={}), ["kalkulation"], size=3)
        self.assertEqual(len(keys), 3)

    def test_kleines_thema_ganze_liste(self):
        cards = [c["q"] for c in KARTEIKARTEN if c.get("thema") == "zahlen"]
        quiz = [q["q"] for q in QUIZ_QUESTIONS if q.get("thema") == "zahlen"]
        source, keys = fl.topic_practice(StatusBook(results={}), ["zahlen"], size=500)
        self.assertEqual(sorted(keys), sorted(quiz if source == SRC_QUIZ else cards))

    def test_rote_zuerst(self):
        quiz = [q["q"] for q in QUIZ_QUESTIONS if q.get("thema") == "routing"]
        done, yellow, red = quiz[0], quiz[1], quiz[-1]
        book = _book({(SRC_QUIZ, done): [True, True], (SRC_QUIZ, yellow): [False, True],
                      (SRC_QUIZ, red): [True, False]})
        self.assertEqual(book.status(SRC_QUIZ, red), (Q_PRACTICE, LEVEL_RED))
        source, keys = fl.topic_practice(book, ["routing"], size=len(quiz))
        self.assertEqual(source, SRC_QUIZ)
        self.assertEqual(keys[0], red)
        self.assertEqual(keys[1], yellow)
        self.assertEqual(keys[-1], done)          # Abgeschlossenes zuletzt
        _source, short = fl.topic_practice(book, ["routing"], size=2)
        self.assertEqual(short, [red, yellow])

    def test_gemischt_erst_quiz_dann_karten(self):
        cards = [c["q"] for c in KARTEIKARTEN if c.get("thema") == "routing"]
        book = _book({(SRC_CARD, cards[0]): [False], (SRC_CARD, cards[1]): [False]})
        parts = fl.topic_practice_parts(book, ["routing"])
        self.assertEqual([source for source, _keys in parts], [SRC_QUIZ, SRC_CARD])
        self.assertEqual(set(parts[1][1][:2]), {cards[0], cards[1]})   # Rotes zuerst
        for _source, keys in parts:
            self.assertEqual(len(keys), fl.PRACTICE_ROUND)
        self.assertEqual(fl.topic_practice(book, ["routing"]), parts[0])

    def test_gemischt_nur_vorhandene_bereiche(self):
        self.assertEqual(fl.topic_practice_parts(StatusBook(results={}), []), [])
        for topic in TOPIC_NAME:
            parts = fl.topic_practice_parts(StatusBook(results={}), [topic])
            sources = [source for source, _keys in parts]
            self.assertEqual(sources, [s for s in (SRC_QUIZ, SRC_CARD) if s in sources])
            self.assertTrue(all(keys for _source, keys in parts))

    def test_rueckfrage_zweiter_teil(self):
        self.assertEqual(fl.practice_next_text(SRC_CARD, 1),
                         "Zum selben Thema gibt es noch 1 Karteikarte. Jetzt weiterüben?")
        self.assertEqual(fl.practice_next_text(SRC_CARD, 10),
                         "Zum selben Thema gibt es noch 10 Karteikarten. Jetzt weiterüben?")

    def test_ohne_fragen(self):
        self.assertEqual(fl.topic_practice(StatusBook(results={}), []), (None, []))

    def test_mischen_aendert_nur_innerhalb_der_gruppen(self):
        import random
        quiz = [q["q"] for q in QUIZ_QUESTIONS if q.get("thema") == "ipv4"]
        book = _book({(SRC_QUIZ, quiz[5]): [False]})
        _source, keys = fl.topic_practice(book, ["ipv4"], rng=random.Random(3))
        self.assertEqual(keys[0], quiz[5])

    def test_letzte_pruefung_im_fortschritt(self):
        import fisi_pruefung as fp
        self.assertEqual(fp.latest_weak([]), (None, []))
        exams = [{"timestamp": "2026-10-02 10:00:00", "art": fp.NETZWERKE, "daten": {
                     "themen": {"IT-Sicherheit": [5, 25], "Netzwerkdesign": [20, 25],
                                "Subnetting & Routing": [10, 50]}}},
                 {"timestamp": "2026-09-01 10:00:00", "art": fp.AP1, "daten": {
                     "themen": {"Projektplanung": [0, 25]}}}]
        title, weak = fp.latest_weak(exams)
        self.assertEqual(weak, ["IT-Sicherheit", "Subnetting & Routing"])
        self.assertEqual(title, "Üben (letzte Prüfung: Netzwerke, 02.10.2026)")
        # nur die juengste Pruefung zaehlt
        exams[0]["daten"]["themen"] = {"IT-Sicherheit": [25, 25]}
        self.assertEqual(fp.latest_weak(exams), (None, []))
        self.assertEqual(fp.latest_weak([{"timestamp": "", "art": "x", "daten": {}}]),
                         (None, []))


# ============================================================================
#  SUCHE IM NOTIZBLOCK
# ============================================================================

class NotebookSearchTest(unittest.TestCase):

    def setUp(self):
        self.book = StatusBook(results={})
        self.entries = notebook_entries(self.book, status=FILTER_ALL)

    def test_leer_heisst_alle(self):
        self.assertEqual(len(notebook_search(self.entries, "")), len(self.entries))
        self.assertEqual(len(notebook_search(self.entries, "   ")), len(self.entries))

    def test_treffer_in_der_frage(self):
        card = KARTEIKARTEN[0]
        word = max(card["q"].split(), key=len)
        hits = notebook_search(self.entries, word)
        self.assertIn((SRC_CARD, card["q"]), {(e["source"], e["key"]) for e in hits})
        for entry in hits:
            self.assertIn(word.casefold(), fl_text(entry))

    def test_treffer_in_der_antwort(self):
        hits = notebook_search(self.entries, "Broadcast")
        self.assertTrue(any("broadcast" not in e["title"].casefold() for e in hits))

    def test_thema_ja_fachbereich_nein(self):
        by_topic = notebook_search(self.entries, TOPIC_NAME["routing"])
        self.assertTrue(by_topic)
        self.assertTrue(any(e["item"].get("thema") == "routing" for e in by_topic))
        # Der Fachbereichsname zaehlt nicht (ab 0.54): "raid" findet nur
        # Fragen, in denen RAID vorkommt, nicht den ganzen Bereich
        category = [e for e in self.entries if "RAID" in e["item"].get("cat", "")]
        hits = notebook_search(self.entries, "raid")
        self.assertTrue(hits)
        self.assertLess(len(hits), len(category))
        for entry in hits:
            self.assertIn("raid", fl_text(entry))

    def test_keine_treffer(self):
        self.assertEqual(notebook_search(self.entries, "xyzzy-gibt-es-nicht"), [])
        self.assertIn("%s", __import__("fisi_core").NOTEBOOK_NO_HITS)

    def test_gross_klein_und_leerzeichen(self):
        a = notebook_search(self.entries, "raid")
        b = notebook_search(self.entries, "  RAID ")
        self.assertTrue(a)
        self.assertEqual(a, b)

    def test_umlaute(self):
        lower = notebook_search(self.entries, "prüfsumme")
        upper = notebook_search(self.entries, "PRÜFSUMME")
        self.assertTrue(lower)
        self.assertEqual(lower, upper)
        # zerlegte Schreibweise (u + Trema) findet dasselbe
        self.assertEqual(notebook_search(self.entries, "prüfsumme"), lower)
        # ß wie ss (casefold)
        self.assertEqual(notebook_search(self.entries, "GRÖSSE"),
                         notebook_search(self.entries, "größe"))

    def test_kombination_mit_filtern(self):
        filtered = notebook_entries(self.book, status=FILTER_ALL, topic="storage",
                                    sources=[SRC_QUIZ])
        hits = notebook_search(filtered, "raid")
        self.assertTrue(hits)
        for entry in hits:
            self.assertEqual(entry["source"], SRC_QUIZ)
            self.assertEqual(entry["item"].get("thema"), "storage")
        self.assertLess(len(hits), len(notebook_search(self.entries, "raid")))

    def test_reihenfolge_bleibt(self):
        hits = notebook_search(self.entries, "netz")
        positions = [self.entries.index(entry) for entry in hits]
        self.assertEqual(positions, sorted(positions))

    def test_szenarien_durchsuchbar(self):
        hits = notebook_search(self.entries, "Subnetting")
        self.assertTrue(any(e["source"] == SRC_AP2 for e in hits))

    def test_schnell_genug(self):
        import time
        notebook_search(self.entries, "a")          # Suchtexte einmal bauen
        start = time.perf_counter()
        for word in ("netz", "raid", "dhcp", "vertrag", "ipv6"):
            notebook_search(self.entries, word)
        self.assertLess((time.perf_counter() - start) / 5, 0.25)


def fl_text(entry):
    from fisi_core import _entry_search_text
    return _entry_search_text(entry)


# ============================================================================
#  AUFGABEN PRO TAG
# ============================================================================

class DailySeriesTest(TempDataMixin, unittest.TestCase):

    def _insert(self, table, stamp, correct=1):
        conn = sqlite3.connect(self.db.db_path)
        try:
            if table == "card_events":
                conn.execute("INSERT INTO card_events (timestamp, category, question, mode,"
                             " correct, uid) VALUES (?, 'x', 'q', 'lernen', ?, ?)",
                             (stamp, correct, os.urandom(8).hex()))
            elif table == "quiz_answers":
                conn.execute("INSERT INTO quiz_answers (timestamp, category, question,"
                             " correct, uid) VALUES (?, 'x', 'q', ?, ?)",
                             (stamp, correct, os.urandom(8).hex()))
            conn.commit()
        finally:
            conn.close()

    def test_leere_tage_null(self):
        today = datetime.date(2026, 10, 2)
        series = fl.daily_series({}, 7, today)
        self.assertEqual(len(series), 7)
        self.assertEqual(series[0][0], datetime.date(2026, 9, 26))
        self.assertEqual(series[-1][0], today)
        self.assertEqual([count for _day, count in series], [0] * 7)
        self.assertEqual(len(fl.daily_series({}, 30, today)), 30)

    def test_werte_wie_tagesziel(self):
        """Gezaehlt wird genau wie beim Tagesziel (activity_days)."""
        today = datetime.date.today()
        yesterday = today - datetime.timedelta(days=1)
        self.db.log_card("Netzwerk", "Frage", "lernen", True)
        self.db.log_card("Netzwerk", "Frage", "lernen", None)   # nur angesehen
        self.db.log_quiz_answer("Netzwerk", "Quiz", False)
        self.db.log_trainer("ipv4", 1, True)
        self._insert("card_events", yesterday.strftime("%Y-%m-%d 12:00:00"))
        self._insert("quiz_answers", (today - datetime.timedelta(days=10)).isoformat()
                     + " 08:00:00")
        activity = self.db.activity_days()
        series = fl.daily_series(activity, 7)
        goal = fl.DailyGoal(activity, 20)
        self.assertEqual(series[-1][1], goal.done)
        self.assertEqual(series[-1][1], 3)
        self.assertEqual(series[-2][1], 1)
        self.assertEqual(sum(count for _d, count in series), 4)
        self.assertEqual(sum(count for _d, count in fl.daily_series(activity, 30)), 5)

    def test_mitternacht(self):
        self._insert("card_events", "2026-10-01 23:59:59")
        self._insert("card_events", "2026-10-02 00:00:00")
        self._insert("quiz_answers", "2026-10-02 00:00:01")
        series = fl.daily_series(self.db.activity_days(), 7, datetime.date(2026, 10, 2))
        self.assertEqual(series[-2], (datetime.date(2026, 10, 1), 1))
        self.assertEqual(series[-1], (datetime.date(2026, 10, 2), 2))

    def test_zukunft_zaehlt_nicht(self):
        series = fl.daily_series({"2026-10-03": 9}, 7, datetime.date(2026, 10, 2))
        self.assertEqual(sum(count for _d, count in series), 0)

    def test_beschriftung(self):
        week = fl.daily_series({}, 7, datetime.date(2026, 10, 4))   # Sonntag
        self.assertEqual(fl.day_labels(week), ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"])
        month = fl.daily_series({}, 30, datetime.date(2026, 10, 2))
        labels = fl.day_labels(month)
        self.assertEqual(labels[-1], "02.10")
        self.assertEqual(labels[0], "03.09")

    def test_zusammenfassung(self):
        series = fl.daily_series({"2026-10-02": 25, "2026-10-01": 5}, 7,
                                 datetime.date(2026, 10, 2))
        self.assertEqual(fl.daily_summary(series, 20),
                         "7 Tage: 30 Aufgaben · Tagesziel an 1 von 7 Tagen erreicht")
        one = fl.daily_series({"2026-10-02": 1}, 1, datetime.date(2026, 10, 2))
        self.assertEqual(fl.daily_summary(one), "1 Tag: 1 Aufgabe")


if __name__ == "__main__":
    unittest.main()
