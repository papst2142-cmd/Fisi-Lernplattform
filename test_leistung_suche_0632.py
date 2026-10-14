# -*- coding: utf-8 -*-
"""Tests 0.63.2, Bauauftrag N7 (Leistung PC II): B-I-02 und B-I-03 Weg 1.

Testplan: bau_0.63.2/testplaene/Testplan_N7.md (Pruefer vor Bauer).

  * B-I-02 Suche oben: Suchtext der Inhalte einmal je Programmlauf (K6),
    Treffer gleich fisi_core.search_content (K1, Weisung B2: Vorbereitung nur
    in app_gui.py, Gleichheitstest gegen die fisi_core-Funktionen), Anzeige
    gleich (K2), erste Zeilen sofort und Rest in Schritten (K3), neue Suche
    bricht die alte ab (K4), Bedienung per Klick und Tastatur (K5)
  * B-I-03 Dashboard: gebuendelt (K10), nur die betroffenen Abfragen neu
    (K11, Zuordnung DASH_QUERIES), Anzeige gleich einer Neuberechnung ohne
    Zwischenspeicher nach jedem Schritt einer Folge von Aenderungen (K12)
  * B-I-03 Notizblock: Treffer gleich fisi_core.notebook_search (K13),
    Tipp-Pause (K14), Suchtext einmal je refresh, nicht je Taste (K15)
  * B-I-03 Hinweis "Bitte warten" bei Sicherung erstellen / Alles ersetzen,
    PC und Handy, Wortlaut der Weisung zu Meldung 38/40 (N7-F7) (K25)

Aufruf:  xvfb-run -a python test_leistung_suche_0632.py
Optional N7_GROSS_DB=<pfad>: Dashboard-/Notizblock-Tests auf einer Kopie
dieses (grossen) Lernstands statt auf dem kleinen, im Test erzeugten.
"""
import datetime
import os
import random
import shutil
import sys
import tempfile
import time
import types
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.chdir(HERE)
_TMP = tempfile.mkdtemp(prefix="fisi_n7_")
os.environ["FISI_DB_PATH"] = os.path.join(_TMP, "n7.db")
os.environ.setdefault("FISI_SELFTEST", os.path.join(_TMP, "selbsttest.log"))
os.environ["HOME"] = _TMP
os.environ["APPDATA"] = _TMP
os.environ["FISI_VORLADEN"] = "0"     # Vorladen aus: Zaehlungen ohne Hintergrund

import fisi_core as fc  # noqa: E402
import fisi_hilfe as fh  # noqa: E402
import fisi_lernen as fl  # noqa: E402
import fisi_optionen as fo  # noqa: E402

MOBILE_SOURCE = open(os.path.join(HERE, "mobile", "src", "main.py"), encoding="utf-8").read()

# Feste Begriffsliste (Testplan 2.2; "Maß"/"groß" fuer K-N7-03, "ß")
TERMS = ["Subnetz", "RAID", "zz-nichts", "a", "IPv6", "ä", "Datenschutz", "Farbe",
         "Hilfe", "z. B.", "z.B.", "RAID ", " raid", "192.168", "%", "(", "Maß", "groß",
         "ss", "Port", "OSI", "e", "Firewall", "–"]

WAIT_BACKUP = b"Bitte warten \xe2\x80\x93 die Sicherung wird erstellt.".decode("utf-8")
WAIT_REPLACE = b"Bitte warten \xe2\x80\x93 die Daten werden ersetzt.".decode("utf-8")
# Weisung zu Meldung 38/40, N7-F7: keine Zusage, kein "Abgleich", kein "GitHub"
FORBIDDEN = ("Abgleich", "abgeglichen", "GitHub", "gleich", "sofort", "Sekunde", "Minute",
             "garantiert", "verloren", "nichts", "fertig", "kurz")


def _display_available():
    try:
        import tkinter
        root = tkinter.Tk()
        root.destroy()
        return True
    except Exception:
        return False


def _flet_ok():
    try:
        import flet
        return bool(flet)
    except Exception:  # noqa: BLE001
        return False


def _fill_db(path):
    """Kleiner, aber gemischter Lernstand ueber die letzten 20 Tage (Karten,
    Quiz, AP1, AP2, Trainer, Test-Session) in einem Schreibvorgang - oder eine
    Kopie von N7_GROSS_DB. Spalten wie DBManager (uid, utc_offset)."""
    import sqlite3
    import uuid
    big = os.environ.get("N7_GROSS_DB")
    if big:
        shutil.copyfile(big, path)
        return fc.DBManager(path)
    db = fc.DBManager(path)
    rng = random.Random(7)
    now = datetime.datetime.now().replace(microsecond=0)

    def stamp(i):
        return (now - datetime.timedelta(hours=5 * i)).strftime("%Y-%m-%d %H:%M:%S")
    uid = lambda: uuid.uuid4().hex   # noqa: E731
    cards = [(stamp(i), 60, card["cat"], card["q"], "freitext", int(rng.random() < 0.6),
              uid()) for i, card in enumerate(fc.KARTEIKARTEN[:60])]
    quiz = [(stamp(i % 90), 60, q["cat"], q["q"], int(rng.random() < 0.7), uid())
            for i, q in enumerate(fc.QUIZ_QUESTIONS[i % 90] for i in range(200))]
    ap1 = [(stamp(i), 60, i, s["title"], s["theme"], int(i % 2 == 0), uid())
           for i, s in enumerate(fc.AP1_SZENARIEN[:4])]
    ap2 = [(stamp(i), 60, i, s["title"], s["theme"], 1, uid())
           for i, s in enumerate(fc.SZENARIEN[:4])]
    conn = sqlite3.connect(path)
    with conn:
        conn.executemany("INSERT INTO card_events (timestamp, utc_offset, category, question,"
                         " mode, correct, uid) VALUES (?, ?, ?, ?, ?, ?, ?)", cards)
        conn.executemany("INSERT INTO quiz_answers (timestamp, utc_offset, category, question,"
                         " correct, uid) VALUES (?, ?, ?, ?, ?, ?)", quiz)
        for table, rows in (("ap1_events", ap1), ("scenario_events", ap2)):
            conn.executemany("INSERT INTO %s (timestamp, utc_offset, scenario_index, title,"
                             " theme, correct, uid) VALUES (?, ?, ?, ?, ?, ?, ?)" % table, rows)
        conn.execute("INSERT INTO trainer_aufgaben (timestamp, utc_offset, art, stufe,"
                     " correct, uid) VALUES (?, 60, 'subnetz', 1, 1, ?)", (stamp(1), uid()))
        conn.execute("INSERT INTO test_results (timestamp, utc_offset, score, total,"
                     " percentage, note, duration_seconds, uid) VALUES (?, 60, 8, 10, 80.0,"
                     " '2', 120, ?)", (stamp(2), uid()))
    conn.close()
    return db


# ---------------------------------------------------------------------------
#  Uhr-Attrappe: "morgen" fuer alle Module, die datetime.date.today() lesen
# ---------------------------------------------------------------------------

class _Clock:
    shift = 0


class _FakeDate(datetime.date):
    @classmethod
    def today(cls):
        real = datetime.date.today()
        return real + datetime.timedelta(days=_Clock.shift)


def _fake_datetime():
    shim = types.ModuleType("datetime")
    for name in dir(datetime):
        if not name.startswith("__"):
            setattr(shim, name, getattr(datetime, name))
    shim.date = _FakeDate
    return shim


def _own_texts(widget, found):
    """Sichtbare Texte (ein CTkLabel einmal, nicht auch sein inneres Label)."""
    import customtkinter as ctk
    if not isinstance(getattr(widget, "master", None), ctk.CTkLabel):
        try:
            text = widget.cget("text")
            if isinstance(text, str) and text:
                found.append(text)
        except Exception:  # noqa: BLE001
            pass
    for child in widget.winfo_children():
        _own_texts(child, found)
    return found


def _widget_state(widget, found):
    """Alles, was eine Ansicht zeigt: Texte, Daten der Zeichenflaechen."""
    try:
        found.append(("text", widget.winfo_class(), str(widget.cget("text"))))
    except Exception:  # noqa: BLE001
        pass
    for attr in ("_data", "_pct", "_color", "_note", "_labels", "_series", "_items",
                 "_rows", "_texts", "_active_days", "year", "month"):
        if attr in getattr(widget, "__dict__", {}):
            found.append((attr, type(widget).__name__, repr(widget.__dict__[attr])))
    try:
        if widget.winfo_class() == "Canvas":
            for item in widget.find_all():
                if widget.type(item) == "text":
                    found.append(("canvas", widget.itemcget(item, "text")))
    except Exception:  # noqa: BLE001
        pass
    try:
        if widget.winfo_manager() == "" and widget.winfo_class() != "Toplevel":
            found.append(("versteckt", str(widget)[-30:]))
    except Exception:  # noqa: BLE001
        pass
    for child in widget.winfo_children():
        _widget_state(child, found)
    return found


@unittest.skipUnless(_display_available(), "keine Anzeige (z.B. mit xvfb-run starten)")
class PcTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        import app_gui
        app_gui.UpdateController.auto_check = lambda self: None
        app_gui.SyncController.auto_start = lambda self: None
        app_gui.show_badge_toast = lambda *a, **k: None
        cls.gui = app_gui
        cls.db_path = os.environ["FISI_DB_PATH"]
        _fill_db(cls.db_path)
        fl.save_learning_settings(serie_an=True, ziel_an=True, ziel_anzahl=20)
        cls.errors = []
        cls.root = app_gui.ctk.CTk()
        cls.root.report_callback_exception = lambda *exc: cls.errors.append(exc)
        cls.root.geometry("1360x900+0+0")
        cls.app = app_gui.FISIApp(cls.root)
        cls.root.update()
        cls.opened = []
        cls.app.open_search_hit = lambda kind, title: cls.opened.append((kind, title))

    @classmethod
    def tearDownClass(cls):
        try:
            tk_ = cls.root.tk
            for job in tk_.splitlist(tk_.call("after", "info")):
                tk_.call("after", "cancel", job)
            cls.root.destroy()
        except Exception:  # noqa: BLE001
            pass

    def tearDown(self):
        self.assertEqual(self.errors, [])

    # -- Hilfen ------------------------------------------------------------

    def pump(self, seconds=0.05):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            self.root.update()
            time.sleep(0.002)

    def finish_search(self, limit=30.0):
        view = self.app.views["search"]
        end = time.monotonic() + limit
        while time.monotonic() < end and getattr(view, "_pending", None) is not None:
            self.root.update()
            time.sleep(0.002)
        self.root.update()
        self.assertIsNone(getattr(view, "_pending", None), "Suche nicht fertig")

    def expected_hits(self, query):
        """Treffer wie SearchView.search bis 0.63.1: Hilfe, Optionen, dann
        fisi_core.search_content (unveraendert seit 14b3bd4, AST-Beleg N7)."""
        hits = [(fh.SEARCH_KIND, None, title, text)
                for _id, title, text in fh.search_help(query)]
        hits += [(fo.SEARCH_KIND, None, title, text)
                 for _id, title, text, _t in fo.search_options(query, pc=True)]
        return hits + fc.search_content(query)

    def assert_more_hint(self, extra, count):
        """Genau ein Hinweis auf weitere Treffer. Der Anfang "..." wird in
        N8 (N-c) zu "\u2026"; beide Schreibweisen gelten, die Zahl muss stimmen."""
        self.assertEqual(len(extra), 1, extra)
        self.assertIn(extra[0], ["%s weitere %d Treffer nicht angezeigt." % (start, count)
                                 for start in ("...", "\u2026")])

    def row_texts(self, hit):
        kind, category, title, detail = hit
        head = "%s · %s" % (kind, self.gui.CATEGORY_SHORT.get(category, "")) \
            if category else kind
        snippet = detail if len(detail) <= 140 else detail[:138] + "…"
        return [head, title, snippet]

    def row_frames(self):
        view = self.app.views["search"]
        return [child for child in view.results_box.winfo_children()
                if isinstance(child, self.gui.ctk.CTkFrame)]

    def shown_rows(self):
        """[(Kopf, Titel, Ausschnitt)] und Zusatzzeilen der Trefferliste."""
        view = self.app.views["search"]
        rows, extra = [], []
        for child in view.results_box.winfo_children():
            if not isinstance(child, self.gui.ctk.CTkFrame):
                extra.append(_own_texts(child, []))
                continue
            rows.append(_own_texts(child, []))
        return rows, [text for texts in extra for text in texts]

    # -- B-I-02: Suche oben ---------------------------------------------------

    def test_k1_gleich_wie_fisi_core(self):
        """K1: vorbereiteter Suchtext liefert fuer jeden Begriff dieselben
        Treffer in derselben Reihenfolge wie fisi_core.search_content."""
        for query in TERMS + [card["q"][:12] for card in fc.KARTEIKARTEN[::97]] + \
                [scen["title"][-9:] for scen in fc.SZENARIEN[::40]]:
            self.assertEqual(self.gui.search_content_prepared(query),
                             fc.search_content(query), query)
        self.assertGreater(len(fc.search_content("a")), 60)
        # Spannt ein Treffer ueber zwei Felder eines Szenarios (Titel+Text),
        # muss er wie bisher gefunden werden
        scen = fc.SZENARIEN[0]
        seam = scen["title"][-3:] + scen["text"][:3]
        self.assertEqual(self.gui.search_content_prepared(seam), fc.search_content(seam))

    def test_k1_k2_anzeige_wie_bisher(self):
        """K1/K2: Trefferzahl, alle Zeilen (hoechstens 60) mit Kopf, Titel und
        Ausschnitt in derselben Reihenfolge, Hinweis bzw. "Keine Treffer"."""
        view = self.app.views["search"]
        # Anzeige fuer die Faelle: > 60, 0, wenige, Umlaut, Sonderzeichen,
        # Leerzeichen, Optionen-Treffer (K1 prueft die ganze Liste ohne Anzeige)
        for query in ("a", "zz-nichts", "Subnetz", "ä", "(", " raid", "Farbe", "z. B."):
            self.app.do_search(query)
            self.finish_search()
            hits = self.expected_hits(query)
            self.assertEqual(view.lbl_info.cget("text"),
                             '%d Treffer für „%s“' % (len(hits), query))
            rows, extra = self.shown_rows()
            self.assertEqual(rows, [self.row_texts(hit) for hit in hits[:60]], query)
            if not hits:
                self.assertEqual(extra, ["Keine Treffer. Versuche einen anderen Suchbegriff."])
            elif len(hits) > 60:
                self.assert_more_hint(extra, len(hits) - 60)
                # der Hinweis steht unter der letzten Zeile
                self.assertEqual(view.results_box.winfo_children()[-1].cget("text"), extra[0])
            else:
                self.assertEqual(extra, [], query)
            self.assertEqual(self.app.current, "search")

    def test_k3_erste_zeilen_sofort_rest_in_schritten(self):
        """K3: direkt nach do_search stehen die ersten Zeilen, weitere folgen
        ueber Zeitgeber in Schritten; am Ende 60 Zeilen und der Hinweis."""
        view = self.app.views["search"]
        steps = []
        original = type(view)._add_rows

        def counted():
            before = len(self.row_frames())
            started = time.perf_counter()
            original(view)
            steps.append((len(self.row_frames()) - before,
                          (time.perf_counter() - started) * 1000))
        view._add_rows = counted
        try:
            self.app.do_search("a")
            self.root.update_idletasks()
            rows, extra = self.shown_rows()
            first = self.gui.SEARCH_FIRST_ROWS
            self.assertTrue(0 < first < 60)
            self.assertEqual(len(rows), first)
            self.assertEqual(extra, [])
            self.assertIsNotNone(view._pending)
            self.finish_search()
        finally:
            del view._add_rows
        self.assertGreaterEqual(len(steps), 2, steps)
        self.assertTrue(all(0 < count <= self.gui.SEARCH_STEP_ROWS for count, _ms in steps),
                        steps)
        self.assertEqual(first + sum(count for count, _ms in steps), 60)
        print("\n  K3 Schritte (Zeilen, ms):", [(c, round(ms)) for c, ms in steps])
        rows, extra = self.shown_rows()
        self.assertEqual(len(rows), 60)
        self.assertEqual(len(extra), 1)

    def test_k4_neue_suche_bricht_alte_ab(self):
        """K4: Zweite Suche, waehrend die erste noch Zeilen nachreicht."""
        view = self.app.views["search"]
        self.app.do_search("a")
        self.root.update_idletasks()
        self.assertIsNotNone(view._pending)
        self.app.do_search("RAID")
        self.finish_search()
        self.pump(0.3)          # auch spaete Zeitgeber der ersten Suche
        hits = self.expected_hits("RAID")
        rows, _extra = self.shown_rows()
        self.assertEqual(rows, [self.row_texts(hit) for hit in hits[:60]])
        # Zweite Suche ohne Treffer: keine Zeile der ersten Suche darf
        # nachtraeglich im neuen Bereich erscheinen
        self.app.do_search("a")
        self.root.update_idletasks()
        self.assertIsNotNone(view._pending)
        self.app.do_search("zz-nichts-n7")
        self.pump(0.6)
        rows, extra = self.shown_rows()
        self.assertEqual(rows, [])
        self.assertEqual(extra, ["Keine Treffer. Versuche einen anderen Suchbegriff."])
        # Zweite Suche mit mehr als 60 Treffern: genau eine Liste, genau ein
        # Hinweis auf weitere Treffer (keine zweite, parallele Kette)
        self.app.do_search("a")
        self.root.update_idletasks()
        self.app.do_search("e")
        self.finish_search()
        self.pump(0.6)
        hits = self.expected_hits("e")
        self.assertGreater(len(hits), 60)
        rows, extra = self.shown_rows()
        self.assertEqual(rows, [self.row_texts(hit) for hit in hits[:60]])
        self.assert_more_hint(extra, len(hits) - 60)

    def test_k5_klick_und_tastatur_auch_nachgereicht(self):
        """K5: Zeile 1 und eine nachgereichte Zeile (40) per Klick, Eingabe
        und Tab erreichbar; Ziel wie open_search_hit(Art, Titel)."""
        import fisi_widgets as fw
        view = self.app.views["search"]
        self.app.do_search("a")
        self.finish_search()
        hits = self.expected_hits("a")
        frames = self.row_frames()
        self.assertEqual(len(frames), 60)
        for index in (0, 39, 59):
            del self.opened[:]
            row = frames[index]
            self.assertIn(str(self.gui.tk.Misc.cget(row, "takefocus")), ("1", "True"), index)
            row.focus_force()
            self.root.update()
            self.gui.tk.Misc.event_generate(row, "<Return>")
            self.root.update()
            self.assertEqual(self.opened, [(hits[index][0], hits[index][2])], index)
            del self.opened[:]
            row._canvas.event_generate("<Button-1>")   # CTkFrame bindet am Canvas
            self.root.update()
            self.assertEqual(self.opened, [(hits[index][0], hits[index][2])], index)
        # Tab von Zeile 39 fuehrt zu Zeile 40 (beide nachgereicht)
        self.assertEqual(fw.next_focus(frames[38]), str(frames[39]))

    def test_k6_suchtext_einmal_je_lauf(self):
        """K6: der Suchtext der Inhalte wird einmal gebildet, nicht je Suche;
        fisi_core.search_content wird nicht mehr je Suche aufgerufen."""
        calls = []
        original = self.gui.search_content

        def counted(query):
            calls.append(query)
            return original(query)
        self.gui.search_content = counted
        try:
            for query in ("Subnetz", "RAID", "zz-nichts", "IPv6", "a"):
                self.app.do_search(query)
                self.finish_search()
        finally:
            self.gui.search_content = original
        self.assertEqual(calls, [])
        self.assertEqual(self.gui.CONTENT_INDEX_BUILDS[0], 1)
        # Inhalte sind dieselben Listen wie in fisi_core (fest zur Laufzeit)
        self.assertIs(self.gui.KARTEIKARTEN, fc.KARTEIKARTEN)
        self.assertIs(self.gui.QUIZ_QUESTIONS, fc.QUIZ_QUESTIONS)
        self.assertEqual(len(self.gui.content_search_index()),
                         len(fc.KARTEIKARTEN) + len(fc.QUIZ_QUESTIONS) +
                         len(fc.SZENARIEN) + len(fc.AP1_SZENARIEN))

    def test_k6_hilfe_name_zur_laufzeit(self):
        """Testplan 2.6: Die Hilfe-Suche (nicht vorbereitet) zeigt einen zur
        Laufzeit gespeicherten Namen nicht falsch an - Hilfe-Texte enthalten
        keinen Namen; Treffer gleich fh.search_help."""
        before = self.expected_hits("Hilfe")
        fh.save_name("Ada")
        try:
            self.app.do_search("Hilfe")
            self.finish_search()
            self.assertEqual(self.expected_hits("Hilfe"), before)
            rows, _extra = self.shown_rows()
            self.assertEqual(rows, [self.row_texts(hit) for hit in before[:60]])
        finally:
            fh.save_name("")

    def test_k6_nach_farbwechsel_gleich(self):
        """A-N7-06: Suche, Farbwechsel (Neuaufbau), dieselbe Suche - gleiche
        Anzeige, keine verwaisten Zeitgeber."""
        self.app.do_search("Subnetz")
        self.finish_search()
        before = self.shown_rows()
        self.app.do_search("a")      # Zeilen werden noch nachgereicht ...
        self.root.update_idletasks()
        self.app.change_color(mode="hell")    # ... waehrend neu aufgebaut wird
        try:
            self.app.do_search("Subnetz")
            self.finish_search()
            self.assertEqual(self.shown_rows(), before)
            self.assertEqual(self.gui._orphaned_timers(self.root), [])
        finally:
            self.app.change_color(mode="dunkel")
            self.root.update()

    # -- B-I-03 Weg 1: Dashboard ---------------------------------------------

    def dashboard(self):
        self.app.show_view("dashboard")
        self.root.update()
        return self.app.views["dashboard"]

    def snapshot(self, view):
        self.root.update_idletasks()
        return _widget_state(view.content, [])

    def uncached_snapshot(self, view):
        """Referenz: dieselbe Ansicht, Zwischenspeicher geleert, neu gerechnet
        (wie eine frisch gebaute Ansicht ohne Zwischenspeicher)."""
        view._dash_cache.clear()
        view._painted.clear()
        view.refresh()
        return self.snapshot(view)

    def count_refresh(self, view):
        calls = []
        original = type(view).refresh

        def counted():
            calls.append(1)
            return original(view)
        view.refresh = counted
        return calls

    def test_k10_gebuendelt(self):
        """K10: fuenf Aenderungsmeldungen in einer Ereignisrunde -> eine
        Neuberechnung; Dashboard nicht sichtbar -> keine, beim Zeigen eine."""
        view = self.dashboard()
        calls = self.count_refresh(view)
        try:
            question = fc.QUIZ_QUESTIONS[300]
            self.app.db.log_quiz_answer(question["cat"], question["q"], True)
            for _ in range(5):
                self.app.notify_progress()
            self.root.update()
            self.assertEqual(len(calls), 1)
            del calls[:]
            self.app.show_view("notebook")
            self.root.update()
            for index in range(10):
                question = fc.QUIZ_QUESTIONS[310 + index]
                self.app.db.log_quiz_answer(question["cat"], question["q"], False)
                self.app.notify_progress()
                self.root.update()
            self.assertEqual(len(calls), 0)
            self.app.show_view("dashboard")
            self.root.update()
            self.assertEqual(len(calls), 1)
        finally:
            del view.refresh
        self.assertEqual(self.snapshot(view), self.uncached_snapshot(view))

    # Zuordnung Aenderungsart -> erneut ausgefuehrte DBManager-Methoden (K11,
    # Tabelle im Bericht). activity_days zaehlt zweimal (Tagesziel + Serie).
    DAY = {"activity_days": 2, "question_results": 1, "daily_counts": 1,
           "month_activity": 1, "recent_activities": 1}
    K11 = {
        "karte": dict(DAY, distinct_cards_learned=1, category_coverage=1,
                      category_stats=1),
        "quiz": dict(DAY, distinct_quiz_questions=1, quiz_success_rate=1,
                     category_coverage=1, category_stats=1),
        "ap1": dict(DAY, distinct_ap1=1, theme_progress=1),
        "ap2": dict(DAY, distinct_scenarios=1, theme_progress=1),
        "projekt": dict(DAY),
        "trainer": {"activity_days": 2, "daily_counts": 1},
        "test_session": {"recent_activities": 1, "month_activity": 1},
        "pruefung_gespeichert": {},
        "tagesziel": {"activity_days": 1},
        "name": {},
        "nichts": {},
        "mitternacht": {"activity_days": 2, "question_results": 1, "daily_counts": 1},
    }
    METHODS = ("distinct_cards_learned", "distinct_quiz_questions", "distinct_ap1",
               "distinct_scenarios", "quiz_success_rate", "activity_days",
               "question_results", "daily_counts", "category_coverage", "category_stats",
               "recent_activities", "month_activity", "theme_progress", "topic_daily",
               "topic_stats", "topic_answers")

    def change(self, kind):
        db = self.app.db
        if kind == "karte":
            card = fc.KARTEIKARTEN[500]
            db.log_card(card["cat"], card["q"], "freitext", False)
        elif kind == "quiz":
            question = fc.QUIZ_QUESTIONS[777]
            db.log_quiz_answer(question["cat"], question["q"], True)
        elif kind == "quiz_falsch":
            question = fc.QUIZ_QUESTIONS[777]
            db.log_quiz_answer(question["cat"], question["q"], False)
        elif kind == "ap1":
            scen = fc.AP1_SZENARIEN[7]
            db.log_ap1(7, scen["title"], scen["theme"], True)
        elif kind == "ap2":
            scen = fc.SZENARIEN[7]
            db.log_scenario(7, scen["title"], scen["theme"], False)
        elif kind == "projekt":
            project = fc.PROJEKTARBEITEN[0]
            db.log_project(0, project.get("title", "P"), project.get("cat", ""), True)
        elif kind == "trainer":
            db.log_trainer("raid", 1, True)
        elif kind == "test_session":
            db.save_test_result(3, 4, 75.0, "2", 30)
        elif kind == "pruefung_gespeichert":
            import sqlite3
            conn = sqlite3.connect(db.db_path)
            conn.execute("INSERT INTO pruefungen (timestamp, art, punkte, note, dauer,"
                         " daten, uid) VALUES (datetime('now'), 'wiso', 50, '3', 60,"
                         " '{}', lower(hex(randomblob(16))))")
            conn.commit()
            conn.close()
        elif kind == "tagesziel":
            current = fl.learning_settings()["ziel_anzahl"]
            fl.save_learning_settings(ziel_anzahl=current + 5)
        elif kind == "name":
            fh.save_name("Ben" if fh.greeting() != "Hallo Ben" else "Cleo")
        elif kind == "mitternacht":
            _Clock.shift += 1

    def install_clock(self):
        import fisi_widgets
        shim = _fake_datetime()
        modules = [self.gui, fc, fl, fisi_widgets]
        saved = [(module, module.datetime) for module in modules]
        for module in modules:
            module.datetime = shim
        return saved

    def test_k11_nur_betroffene_abfragen(self):
        """K11: je Aenderungsart werden nur die Abfragen erneut ausgefuehrt,
        deren Tabellen (oder Datum/Tagesziel) sich geaendert haben."""
        view = self.dashboard()
        if view.zoom_category:
            view._toggle_zoom(view.zoom_category)
        saved = self.install_clock()
        counts = {}
        db = self.app.db
        originals = {}
        for name in self.METHODS:
            method = getattr(db, name)
            originals[name] = method

            def counted(*args, _name=name, _method=method, **kwargs):
                counts[_name] = counts.get(_name, 0) + 1
                return _method(*args, **kwargs)
            setattr(db, name, counted)
        try:
            view.refresh()
            for kind, expected in self.K11.items():
                self.change(kind)
                counts.clear()
                view.refresh()
                self.assertEqual(counts, expected, kind)
                self.assertEqual(self.snapshot(view), self.uncached_snapshot(view), kind)
        finally:
            for name in self.METHODS:
                delattr(db, name)
            for module, value in saved:
                module.datetime = value
            _Clock.shift = 0
            fh.save_name("")
            fl.save_learning_settings(ziel_anzahl=20)
            view.refresh()

    def test_a_n7_25_abgleich_bringt_fremde_eintraege(self):
        """A-N7-25: ein Abgleich (merge_into_local) bringt Eintraege eines
        anderen Geraets; refresh_after_sync zeigt danach dieselben Zahlen wie
        eine Neuberechnung ohne Zwischenspeicher (ohne eigenes refresh)."""
        import fisi_sync
        view = self.dashboard()
        view.refresh()
        self.root.update()
        before = self.snapshot(view)
        other = fc.DBManager(os.path.join(_TMP, "anderes_geraet.db"))
        for index in range(5):
            question = fc.QUIZ_QUESTIONS[900 + index]
            other.log_quiz_answer(question["cat"], question["q"], index % 2 == 0)
            card = fc.KARTEIKARTEN[900 + index]
            other.log_card(card["cat"], card["q"], "freitext", True)
        scen = fc.AP1_SZENARIEN[3]
        other.log_ap1(3, scen["title"], scen["theme"], True)
        try:
            fisi_sync.merge_into_local(self.app.db, fisi_sync.export_local(other))
            self.app.refresh_after_sync()
            self.root.update()
            after = self.snapshot(view)
            self.assertNotEqual(after, before)          # der Abgleich aendert etwas
            self.assertEqual(after, self.uncached_snapshot(view))
        finally:
            self.app.db.reset_all()
            _fill_db(self.app.db.db_path)
            view.refresh()

    def test_k12_differenz_nach_jedem_schritt(self):
        """K12: feste Folge von 37 gemischten Aenderungen (alle Arten, auch
        Mitternacht, Tagesziel, Name, Reinzoomen, "Alles ersetzen", Loeschen
        aller Lerndaten); nach jedem Schritt zeigt das Dashboard dasselbe wie
        eine Neuberechnung ohne Zwischenspeicher."""
        import fisi_sicherung as fsi
        view = self.dashboard()
        saved = self.install_clock()
        backup = fsi.read_backup(fsi.create_backup(self.app.db, "0.63.1", "PC"))
        steps = ["karte", "quiz", "quiz", "ap1", "ap2", "projekt", "trainer",
                 "test_session", "pruefung_gespeichert", "tagesziel", "name",
                 "zoom:" + fc.CATEGORIES[0], "quiz", "karte", "mitternacht", "karte",
                 "zoom:" + fc.CATEGORIES[1], "quiz", "zoom:" + fc.CATEGORIES[1],
                 "ap1", "mitternacht", "ap2", "ersetzen", "quiz", "karte",
                 "monat_zurueck", "quiz", "monat_heute", "trainer", "loeschen",
                 "karte", "quiz", "tagesziel", "ersetzen", "mitternacht",
                 "ersetzen_gleiche_anzahl", "nichts"]
        self.assertGreaterEqual(len(steps), 30)
        try:
            for number, step in enumerate(steps):
                if step.startswith("zoom:"):
                    view._toggle_zoom(step[5:])
                elif step == "ersetzen":
                    fsi.replace_all(self.app.db, backup, os.path.join(_TMP, "sicher"),
                                    "0.63.2", "PC")
                    self.app.refresh_after_sync()
                elif step == "ersetzen_gleiche_anzahl":
                    # Ersetzen durch eine Sicherung mit derselben Zeilenzahl,
                    # aber anderem Inhalt (eine Quizantwort falsch statt richtig)
                    folder = os.path.join(_TMP, "sicher")
                    start = fsi.read_backup(fsi.create_backup(self.app.db, "0.63.2", "PC"))
                    self.change("quiz_falsch")
                    other = fsi.read_backup(fsi.create_backup(self.app.db, "0.63.2", "PC"))
                    fsi.replace_all(self.app.db, start, folder, "0.63.2", "PC")
                    self.app.refresh_after_sync()
                    self.change("quiz")
                    self.app.notify_progress()
                    self.root.update()
                    view.refresh()
                    self.assertEqual(self.snapshot(view), self.uncached_snapshot(view),
                                     "Schritt %d: %s (richtig)" % (number, step))
                    fsi.replace_all(self.app.db, other, folder, "0.63.2", "PC")
                    self.app.refresh_after_sync()
                elif step == "loeschen":
                    self.app.db.reset_all()
                    self.app.notify_progress()
                elif step == "monat_zurueck":
                    view.calendar._prev_month()
                elif step == "monat_heute":
                    view.calendar.to_current_month()
                else:
                    self.change(step)
                    self.app.notify_progress()
                self.root.update()
                view.refresh()
                self.assertEqual(self.snapshot(view), self.uncached_snapshot(view),
                                 "Schritt %d: %s" % (number, step))
        finally:
            for module, value in saved:
                module.datetime = value
            _Clock.shift = 0
            fh.save_name("")
            fl.save_learning_settings(ziel_anzahl=20)
            if view.zoom_category:
                view._toggle_zoom(view.zoom_category)
            # Lernstand fuer die folgenden Tests wiederherstellen
            _fill_db(self.app.db.db_path)
            view.refresh()

    # -- B-I-03 Weg 1: Notizblock --------------------------------------------

    def notebook(self):
        self.app.show_view("notebook")
        self.root.update()
        return self.app.views["notebook"]

    def test_k13_notizblock_gleich_notebook_search(self):
        """K13: fuer die Begriffsliste und 12+ Filterkombinationen dieselben
        Eintraege in derselben Reihenfolge wie fisi_core.notebook_search."""
        view = self.notebook()
        combos = 0
        for status in (fc.Q_PRACTICE, fc.Q_DONE, fc.Q_OPEN):
            for source in (fc.FILTER_ALL, fc.SRC_CARD, fc.SRC_QUIZ, fc.SRC_AP1):
                for category in (fc.FILTER_ALL, fc.CATEGORIES[0]):
                    view.status_pills.select_value(status, notify=False)
                    view.source_pills.select_value(source, notify=False)
                    view.cat_pills.select_value(category, notify=False)
                    view.topic_menu.set_category(category)
                    view.refresh()
                    combos += 1
                    for query in TERMS + ["", "  ", "PORT", "Thema"]:
                        self.assertEqual(
                            [id(e) for e in view._search_prepared(query)],
                            [id(e) for e in fc.notebook_search(view.all_entries, query)],
                            (status, source, category, query))
        self.assertGreaterEqual(combos, 12)
        view.status_pills.select_value(fc.Q_PRACTICE, notify=False)
        view.source_pills.select_value(fc.FILTER_ALL, notify=False)
        view.cat_pills.select_value(fc.FILTER_ALL, notify=False)
        view.topic_menu.set_category(fc.FILTER_ALL)
        view.refresh()

    def type_keys(self, view, text, pause):
        view.search._entry.focus_force()
        self.root.update()
        for char in text:
            view.search.insert("end", char)
            view.search._entry.event_generate("<KeyRelease>")
            self.root.update()
            time.sleep(pause)

    def test_k14_tipp_pause(self):
        """K14 (Schutztest): 5 Tasten kurz hintereinander -> eine Suche; nach
        einer Pause ueber 180 ms eine weitere."""
        view = self.notebook()
        view.search.delete(0, "end")
        view._apply_search()
        calls = []
        original = type(view)._apply_search

        def counted():
            calls.append(view.search.get())
            return original(view)
        view._apply_search = counted
        try:
            self.type_keys(view, "porta", 0.01)
            self.pump(0.4)
            self.assertEqual(calls, ["porta"])
            self.type_keys(view, "l", 0.0)
            self.pump(0.4)
            self.assertEqual(calls, ["porta", "portal"])
        finally:
            del view._apply_search
            view.search.delete(0, "end")
            view._apply_search()

    def test_k15_suchtext_je_refresh_nicht_je_taste(self):
        """K15: waehrend der Eingabe wird der Suchtext nicht neu gebildet
        (kein Aufruf von _entry_search_text je Taste); nach einer neuen
        Antwort und refresh ist der neue Stand suchbar."""
        view = self.notebook()
        calls = []
        original = fc._entry_search_text

        def counted(entry):
            calls.append(entry["key"])
            return original(entry)
        fc._entry_search_text = counted
        try:
            for query in ("p", "po", "por", "port", "netz"):
                view.search.delete(0, "end")
                view.search.insert(0, query)
                view._apply_search()
            self.assertEqual(calls, [])
            # neue falsche Antwort: Frage kommt in "Zu ueben" und ist suchbar
            question = fc.QUIZ_QUESTIONS[1500]
            self.app.db.log_quiz_answer(question["cat"], question["q"], False)
            view.refresh()
            self.assertTrue(calls)
            del calls[:]
            view.search.delete(0, "end")
            view.search.insert(0, question["q"][:40])
            view._apply_search()
            self.assertEqual(calls, [])
            self.assertIn(question["q"], [e["key"] for e in view.entries])
            self.assertEqual([id(e) for e in view.entries],
                             [id(e) for e in fc.notebook_search(view.all_entries,
                                                                question["q"][:40])])
        finally:
            fc._entry_search_text = original
            view.search.delete(0, "end")
            view.query = ""
            view.refresh()

    def test_k15_lernstand_nur_bei_aenderung_neu(self):
        """StatusBook wird bei Filterwechsel ohne neue Antwort nicht neu
        berechnet, nach einer neuen Antwort genau einmal."""
        view = self.notebook()
        view.refresh()
        builds = view.book_builds
        for source in (fc.SRC_CARD, fc.SRC_QUIZ, fc.FILTER_ALL):
            view.source_pills.select_value(source)
            self.root.update()
        self.assertEqual(view.book_builds, builds)
        card = fc.KARTEIKARTEN[1200]
        self.app.db.log_card(card["cat"], card["q"], "freitext", False)
        view.refresh()
        self.assertEqual(view.book_builds, builds + 1)
        self.assertIn(card["q"], [e["key"] for e in view.all_entries])
        fresh = fc.notebook_entries(fc.StatusBook(self.app.db))
        self.assertEqual([(e["source"], e["key"], e["status"], e["level"], e["time"])
                          for e in view.all_entries],
                         [(e["source"], e["key"], e["status"], e["level"], e["time"])
                          for e in fresh])

    # -- K25: Hinweis "Bitte warten" -----------------------------------------

    def wait_labels(self):
        """Texte der Abdeckung (_show_busy legt sie als tk.Frame direkt in
        das Hauptfenster); die Ansichten selbst liegen in CTk-Rahmen."""
        found = []
        for child in self.root.winfo_children():
            if type(child) is self.gui.tk.Frame:
                found += [text for text in _own_texts(child, [])
                          if text in (WAIT_BACKUP, WAIT_REPLACE)]
        return found

    def test_k25_abdeckung_wird_gefunden(self):
        """Gegenprobe zu wait_labels: eine Abdeckung mit dem Text wird gefunden."""
        overlay = self.app._show_busy(WAIT_REPLACE, single=True)
        try:
            self.assertEqual(self.wait_labels(), [WAIT_REPLACE])
        finally:
            self.app._hide_busy(overlay)
        self.assertEqual(self.wait_labels(), [])

    def test_k25_wortlaut(self):
        self.assertEqual(self.gui.WAIT_BACKUP_TEXT.encode("utf-8"),
                         b"Bitte warten \xe2\x80\x93 die Sicherung wird erstellt.")
        self.assertEqual(self.gui.WAIT_REPLACE_TEXT.encode("utf-8"),
                         b"Bitte warten \xe2\x80\x93 die Daten werden ersetzt.")
        import re
        for text in (self.gui.WAIT_BACKUP_TEXT, self.gui.WAIT_REPLACE_TEXT):
            for word in FORBIDDEN:
                self.assertIsNone(re.search(r"\b%s" % word, text, re.I), word)

    def test_k25_hinweis_beim_erstellen(self):
        import fisi_sicherung as fsi
        settings = self.app.views["settings"] if self.app.views.built("settings") else None
        if settings is None:
            self.app.show_view("settings")
            self.root.update()
            settings = self.app.views["settings"]
        seen, errors = [], []
        target = os.path.join(_TMP, "n7_test.fisisicherung")
        original = fsi.create_backup
        from tkinter import filedialog, messagebox
        saved = (filedialog.asksaveasfilename, messagebox.showerror)

        def fake_create(*args, **kwargs):
            seen.append(self.wait_labels())
            return original(*args, **kwargs)
        fsi.create_backup = fake_create
        filedialog.asksaveasfilename = lambda **kwargs: target
        messagebox.showerror = lambda title, text: errors.append((title, text,
                                                                  self.wait_labels()))
        try:
            settings.create_backup()
            self.assertEqual(seen, [[WAIT_BACKUP]])
            self.assertEqual(self.wait_labels(), [])
            self.assertTrue(os.path.exists(target))
            # Fehler beim Speichern: Hinweis weg, Meldung wie bisher
            original_save = fsi.save_file

            def broken(path, data):
                raise OSError("Platte voll")
            fsi.save_file = broken
            try:
                settings.create_backup()
            finally:
                fsi.save_file = original_save
            self.assertEqual(errors, [(fsi.SAVE_ERROR_TITLE, "Platte voll", [])])
            self.assertEqual(self.wait_labels(), [])
        finally:
            fsi.create_backup = original
            filedialog.asksaveasfilename, messagebox.showerror = saved
        self.root.update()

    def test_k25_hinweis_beim_ersetzen(self):
        import fisi_sicherung as fsi
        from tkinter import messagebox
        self.app.show_view("settings")
        self.root.update()
        settings = self.app.views["settings"]
        backup = fsi.read_backup(fsi.create_backup(self.app.db, "0.63.1", "PC"))
        seen, shown = [], []
        original = fsi.replace_all
        saved = (messagebox.askyesno, messagebox.showerror, messagebox.showinfo)

        def fake_replace(*args, **kwargs):
            seen.append(self.wait_labels())
            return original(*args, **kwargs)
        fsi.replace_all = fake_replace
        messagebox.askyesno = lambda *a, **k: True
        messagebox.showinfo = lambda title, text: shown.append(("info", self.wait_labels()))
        messagebox.showerror = lambda title, text: shown.append(("fehler", text,
                                                                 self.wait_labels()))
        try:
            settings._replace_backup(backup)
            self.assertEqual(seen, [[WAIT_REPLACE]])
            self.assertEqual(shown, [("info", [])])
            self.assertEqual(self.wait_labels(), [])
            # A-N7-33: Fehler mitten im Ersetzen - Hinweis weg, Meldung unveraendert
            del shown[:]

            def broken(*args, **kwargs):
                seen.append(self.wait_labels())
                raise fsi.BackupError("Die Sicherung ließ sich nicht einspielen: Test")
            fsi.replace_all = broken
            settings._replace_backup(backup)
            self.assertEqual(shown, [("fehler", fsi.restore_error_text(
                fsi.BackupError("Die Sicherung ließ sich nicht einspielen: Test")), [])])
            self.assertEqual(self.wait_labels(), [])
            # unerwarteter Fehler: Hinweis (und Sperre der Bedienung) ebenfalls weg
            fsi.replace_all = lambda *a, **k: 1 / 0
            with self.assertRaises(ZeroDivisionError):
                settings._replace_backup(backup)
            self.assertEqual(self.wait_labels(), [])
            self.assertEqual(self.root.grab_current(), None)
        finally:
            fsi.replace_all = original
            messagebox.askyesno, messagebox.showerror, messagebox.showinfo = saved
            _fill_db(self.app.db.db_path)
        self.root.update()

    # -- zuletzt: Fenster/Ansicht abgebaut, waehrend Zeilen nachgereicht werden

    def test_zz_abbau_waehrend_nachreichen(self):
        """A-N7-08: Ansicht wird abgebaut, waehrend noch Zeilen geplant sind:
        kein Fehler (report_callback_exception bleibt leer)."""
        view = self.app.views["search"]
        self.app.do_search("a")
        self.root.update_idletasks()
        self.assertIsNotNone(view._pending)
        view.destroy()
        self.pump(0.5)
        self.assertEqual(self.errors, [])


@unittest.skipUnless(_flet_ok(), "flet nicht installiert")
class HandyTest(unittest.TestCase):
    """K25 am Handy: gleicher Wortlaut, Hinweis nur waehrend des Vorgangs."""

    @classmethod
    def setUpClass(cls):
        import flet as ft
        sys.path.insert(1, os.path.join(HERE, "mobile", "src"))
        import main
        cls.ft, cls.main = ft, main

        class FakePage:
            views = []

            def __init__(self):
                self.overlay = []
                self.updates = 0

            def update(self, *args):
                self.updates += 1

            def __getattr__(self, _name):
                return lambda *args, **kwargs: None

        class FakeApp(main.FISIMobileApp):
            def __init__(self):
                self.page = FakePage()
                self.body = ft.Container()
                self.db = main.DBManager()
                self.sync = main.SyncController(self)
                self.perf = main.MobilePerf(self)
                self.screens = {}
                self._recoloring = False
                self.infos = []

            def info(self, title, message):
                self.infos.append((title, message, self.wait_texts()))

            def confirm(self, title, message, on_yes):
                on_yes()

            def wait_texts(self):
                texts = []
                for layer in self.page.overlay:
                    for control in layer.content.content.controls:
                        if isinstance(control, ft.Text):
                            texts.append(control.value)
                return texts

        cls.FakeApp = FakeApp

    def screen(self):
        app = self.FakeApp()
        screen = self.main.SCREEN_CLASSES["settings"](app)
        screen._flush_inputs = lambda: None
        screen._after_restore = lambda: None
        return app, screen

    def test_wortlaut_gleich_pc(self):
        self.assertEqual(self.main.WAIT_BACKUP_TEXT, WAIT_BACKUP)
        self.assertEqual(self.main.WAIT_REPLACE_TEXT, WAIT_REPLACE)
        self.assertIn('WAIT_BACKUP_TEXT = "Bitte warten \\u2013 die Sicherung wird erstellt."',
                      MOBILE_SOURCE)

    def test_hinweis_beim_erstellen(self):
        app, screen = self.screen()
        seen = []
        fsi = self.main.fsi
        original = fsi.create_backup

        def fake_create(*args, **kwargs):
            seen.append(app.wait_texts())
            return original(*args, **kwargs)
        fsi.create_backup = fake_create
        try:
            screen.create_backup()
        finally:
            fsi.create_backup = original
        self.assertEqual(seen, [[WAIT_BACKUP]])
        self.assertEqual(app.page.overlay, [])

    def test_hinweis_beim_ersetzen_und_fehler(self):
        app, screen = self.screen()
        fsi = self.main.fsi
        backup = fsi.read_backup(fsi.create_backup(app.db, "0.63.1", "Handy"))
        seen = []
        original = fsi.replace_all

        def fake_replace(*args, **kwargs):
            seen.append(app.wait_texts())
            return original(*args, **kwargs)
        fsi.replace_all = fake_replace
        try:
            screen._replace_backup(backup)
            self.assertEqual(seen, [[WAIT_REPLACE]])
            self.assertEqual(len(app.infos), 1)
            self.assertEqual(app.infos[0][2], [])
            self.assertEqual(app.page.overlay, [])

            def broken(*args, **kwargs):
                raise fsi.BackupError("Test")
            fsi.replace_all = broken
            screen._replace_backup(backup)
            self.assertEqual(app.infos[-1], (fsi.ERROR_TITLE,
                                             fsi.restore_error_text(fsi.BackupError("Test")),
                                             []))
            self.assertEqual(app.page.overlay, [])
        finally:
            fsi.replace_all = original

    def test_farbwechsel_hinweis_unveraendert(self):
        """Der bisherige Hinweis (Farbwechsel) hat weiter Titel und Text."""
        import fisi_theme
        overlay = self.main.FISIMobileApp._busy_overlay()
        texts = [c.value for c in overlay.content.content.controls
                 if isinstance(c, self.ft.Text)]
        self.assertEqual(texts, [fisi_theme.BUSY_TITLE, fisi_theme.BUSY_TEXT])


if __name__ == "__main__":
    unittest.main(verbosity=2)
