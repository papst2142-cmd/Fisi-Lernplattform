#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests fuer Datenbankfehler ab 0.62.5 (Feinplan 0.62.5, Gruppe 5.1:
B-G-01, B-G-03, B-G-06, B-G-12).

  * kaputte Datenbank (Muell-Datei): genau EINE verstaendliche deutsche
    Meldung statt einer je Abfrage, die Datei bleibt unveraendert (B-G-01)
  * jeder Datenbankfehler steht mit dem technischen Text in fehler.log neben
    der Datenbank (B-G-12)
  * eine beschaedigte Datenseite (Kopf heil): PRAGMA quick_check beim Start
    findet sie, eine Meldung, danach wird nichts mehr geschrieben (B-G-06)
  * schreibgeschuetzter Datenordner bzw. schreibgeschuetzte Datei: eine
    Meldung beim Start statt einer je Antwort (B-G-03)
  * PC: die rote Zeile in der Seitenleiste und hoechstens ein Fenster vom
    Start bis zum Ende des Vorladens (B-G-01, B-G-03)
  * Schutz-Tests (auch auf v0.62.3 gruen): eine heile Datenbank meldet
    nichts und speichert normal; die Laufzeit von quick_check auf einer
    grossen Datenbank

Jeder Fall laeuft in einem eigenen Prozess mit Wegwerf-Ordner (eigenes
HOME, FISI_DB_PATH), nie mit echten Daten.

Gegenprobe gegen einen anderen Stand (auf v0.62.3 sollen alle Tests ausser
den Schutz-Tests rot sein):
    DBFEHLER_CODE=<ordner mit dem Code> python test_db_fehler.py

Schreibschutz unter Linux als root: der Kindprozess laeuft per setpriv als
Benutzer nobody (root darf sonst alles schreiben). Unter Windows uebersprungen.
Start:  python test_db_fehler.py   (GUI-Teil braucht eine Anzeige, z.B. xvfb-run)
"""

import hashlib
import json
import os
import random
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
CODE = os.path.abspath(os.environ.get("DBFEHLER_CODE") or HERE)
DB_NAME = "fisi_lernplattform.db"
NOBODY = 65534
WORK = tempfile.mkdtemp(prefix="fisi_dbfehler_")
os.chmod(WORK, 0o755)     # nobody muss hinein (Schreibschutz-Test als root)

# Grenze fuer quick_check beim Start auf der grossen Datenbank (Sekunden)
QUICK_CHECK_LIMIT = 1.0


def beleg(text):
    print("  [Beleg] %s" % text, flush=True)


def sha(path):
    with open(path, "rb") as handle:
        return hashlib.sha256(handle.read()).hexdigest()


def child_env(folder, home=None):
    env = {k: v for k, v in os.environ.items() if not k.startswith("FISI_")}
    home = home or os.path.join(folder, "home")
    os.makedirs(home, exist_ok=True)
    env.update(HOME=home, XDG_DATA_HOME=os.path.join(home, ".local", "share"),
               APPDATA=home, FISI_DB_PATH=os.path.join(folder, "data", DB_NAME),
               PYTHONDONTWRITEBYTECODE="1", FISI_SELFTEST=os.path.join(home, "selftest.log"),
               http_proxy="http://127.0.0.1:9", https_proxy="http://127.0.0.1:9",
               HTTP_PROXY="http://127.0.0.1:9", HTTPS_PROXY="http://127.0.0.1:9")
    return env


def run_child(code, env, prefix=(), timeout=300):
    """Fuehrt code mit dem Code-Stand CODE aus; die letzte Zeile ist JSON."""
    script = "import sys\nsys.dont_write_bytecode = True\nsys.path.insert(0, %r)\n%s" % (
        RUN_CODE, code)
    proc = subprocess.run(list(prefix) + [sys.executable, "-I", "-c", script], env=env,
                          capture_output=True, text=True, timeout=timeout, cwd=RUN_CODE)
    lines = proc.stdout.strip().splitlines()
    try:
        return json.loads(lines[-1])
    except (IndexError, ValueError):
        raise AssertionError("Kindprozess ohne Ergebnis (rc %s):\n%s\n%s" % (
            proc.returncode, proc.stdout[-1500:], proc.stderr[-3000:]))


def make_valid_db(folder, quiz=3000, cards=50, trainer=0):
    """Gueltige Datenbank mit dem Schema des Code-Stands, gefuellt per SQL."""
    data = os.path.join(folder, "data")
    os.makedirs(data, exist_ok=True)
    path = os.path.join(data, DB_NAME)
    run_child("import fisi_core, json\nfisi_core.DBManager(%r)\nprint(json.dumps(1))" % path,
              child_env(folder))
    conn = sqlite3.connect(path)
    conn.executemany("INSERT INTO quiz_answers (timestamp, category, question, correct, uid)"
                     " VALUES (?, ?, ?, ?, ?)",
                     [("2026-09-%02d 10:00:00" % (1 + i % 28), "Netzwerktechnik",
                       "Frage %04d %s" % (i, "x" * 60), i % 2, "q%05d" % i)
                      for i in range(quiz)])
    conn.executemany("INSERT INTO card_events (timestamp, category, question, mode, correct,"
                     " uid) VALUES (?, ?, ?, 'karte', 1, ?)",
                     [("2026-09-01 09:00:00", "Netzwerktechnik", "Karte %d" % i, "k%04d" % i)
                      for i in range(cards)])
    conn.executemany("INSERT INTO trainer_aufgaben (timestamp, art, stufe, correct, uid)"
                     " VALUES (?, 'subnetz', 1, ?, ?)",
                     [("2026-09-02 08:00:00", i % 2, "t%05d" % i) for i in range(trainer)])
    conn.commit()
    conn.close()
    return path


# Lernen und Lesen wie in der App: viele Abfragen hintereinander
WORKLOAD = r"""
import json, os, fisi_core
m = []
db = fisi_core.DBManager(error_handler=m.append)
start = len(m)
r = {"start": list(m)}
for _ in range(4):
    r["log_quiz_answer"] = db.log_quiz_answer("Netzwerktechnik", "neue Frage", True)
for _ in range(3):
    db.log_card("Netzwerktechnik", "neue Karte", "lernen", True)
    r["log_trainer"] = db.log_trainer("subnetz", 1, True)
    db.change_stamp(); db.activity_days(); db.quiz_success_rate()
    db.distinct_quiz_questions(); db.streak()
r["meldungen"] = m
r["read_only_reason"] = getattr(db, "read_only_reason", None)
print(json.dumps(r, ensure_ascii=False, default=str))
"""


def nobody_prefix():
    return ["setpriv", "--reuid=%d" % NOBODY, "--regid=%d" % NOBODY, "--clear-groups"]


def prepare_run_code():
    """Als root laeuft der Schreibschutz-Fall als nobody: der Code muss fuer
    nobody lesbar sein (sonst Kopie unter WORK)."""
    if os.name == "nt" or os.geteuid() != 0 or not shutil.which("setpriv"):
        return CODE
    probe = subprocess.run(nobody_prefix() + [sys.executable, "-I", "-c",
                           "import os,sys; sys.exit(0 if os.access(%r, os.R_OK) else 1)"
                           % os.path.join(CODE, "fisi_core.py")], capture_output=True)
    if probe.returncode == 0:
        return CODE
    copy = os.path.join(WORK, "code")
    shutil.copytree(CODE, copy, ignore=shutil.ignore_patterns(".git", "__pycache__"))
    for root, dirs, files in os.walk(copy):
        os.chmod(root, 0o755)
        for name in files:
            os.chmod(os.path.join(root, name), 0o644)
    return copy


RUN_CODE = prepare_run_code()


class KaputteDatenbank(unittest.TestCase):
    """B-G-01 und B-G-12: Muell statt Datenbank (wie g2_kaputt.py, db_muell)."""

    @classmethod
    def setUpClass(cls):
        cls.folder = os.path.join(WORK, "muell")
        os.makedirs(os.path.join(cls.folder, "data"))
        cls.db = os.path.join(cls.folder, "data", DB_NAME)
        rnd = random.Random(4242)
        with open(cls.db, "wb") as handle:
            handle.write(bytes(rnd.getrandbits(8) for _ in range(65536)))
        cls.before = sha(cls.db)
        cls.result = run_child(WORKLOAD, child_env(cls.folder))
        beleg("kaputte DB: %d Meldungen, erste: %s" % (
            len(cls.result["meldungen"]), (cls.result["meldungen"] or [""])[0][:90]))

    def test_genau_eine_meldung(self):
        self.assertEqual(len(self.result["meldungen"]), 1, self.result["meldungen"][:5])

    def test_meldung_deutsch_ohne_technik(self):
        text = self.result["meldungen"][0]
        self.assertIn("beschädigt", text)
        self.assertNotIn("not a database", text)

    def test_datei_unveraendert(self):
        """Schutz-Test (auch auf v0.62.3 gruen): die Datei bleibt, wie sie ist."""
        self.assertEqual(sha(self.db), self.before)

    def test_fehler_log(self):
        log = os.path.join(self.folder, "data", "fehler.log")
        self.assertTrue(os.path.isfile(log), "fehler.log fehlt")
        with open(log, encoding="utf-8") as handle:
            text = handle.read()
        self.assertIn("file is not a database", text)
        beleg("fehler.log: %d Eintraege" % text.count("=== "))


class Teilschaden(unittest.TestCase):
    """B-G-06: eine Blattseite von quiz_answers mit Zufall ueberschrieben
    (wie g_unabh2_4_kaputte_seite.py), Dateikopf und Schema heil."""

    TABLE = "quiz_answers"
    TRAINER = 0

    @classmethod
    def setUpClass(cls):
        cls.folder = os.path.join(WORK, "seite_" + cls.TABLE)
        cls.db = make_valid_db(cls.folder, trainer=cls.TRAINER)
        conn = sqlite3.connect(cls.db)
        page = conn.execute("PRAGMA page_size").fetchone()[0]
        leaves = [r[0] for r in conn.execute(
            "SELECT pageno FROM dbstat WHERE name=? AND pagetype='leaf'"
            " ORDER BY pageno", (cls.TABLE,))]
        conn.close()
        victim = leaves[len(leaves) // 2]
        with open(cls.db, "r+b") as handle:
            handle.seek((victim - 1) * page)
            handle.write(random.Random(42).randbytes(page))
        cls.before = sha(cls.db)
        cls.result = run_child(WORKLOAD, child_env(cls.folder))
        beleg("Teilschaden %s (Seite %d von %d Blattseiten): %d Meldungen, Schreiben -> %s" % (
            cls.TABLE, victim, len(leaves), len(cls.result["meldungen"]), cls.result["log_trainer"]))

    def test_eine_meldung_beim_start(self):
        self.assertEqual(len(self.result["start"]), 1, self.result["start"])
        self.assertIn("beschädigt", self.result["start"][0])
        self.assertEqual(len(self.result["meldungen"]), 1, self.result["meldungen"][:5])

    def test_kein_schreibzugriff(self):
        self.assertFalse(self.result["log_trainer"])
        self.assertEqual(self.result["read_only_reason"], "kaputt")
        self.assertEqual(sha(self.db), self.before, "beschaedigte Datei wurde veraendert")


class TeilschadenOhneStartzugriff(Teilschaden):
    """B-G-06: Schaden in einer Tabelle, die der Start sonst nicht liest
    (trainer_aufgaben) - nur quick_check findet ihn vor dem ersten Schreiben."""

    TABLE = "trainer_aufgaben"
    TRAINER = 6000


@unittest.skipIf(os.name == "nt", "Schreibschutz-Fall nur unter Linux/macOS")
class Schreibschutz(unittest.TestCase):
    """B-G-03: wie g2_schreibschutz.sh, R1 (Ordner und Datei) und R2 (nur Datei)."""

    def run_case(self, name, folder_ro):
        folder = os.path.join(WORK, name)
        db = make_valid_db(folder, quiz=200, cards=10)
        data = os.path.dirname(db)
        home = os.path.join(folder, "home")
        prefix = ()
        if os.geteuid() == 0:
            if not shutil.which("setpriv"):
                self.skipTest("setpriv fehlt (als root noetig)")
            prefix = nobody_prefix()
            os.chmod(folder, 0o755)
            os.chown(home, NOBODY, NOBODY)
            if not folder_ro:
                os.chown(data, NOBODY, NOBODY)
            for entry in os.listdir(data):
                os.chown(os.path.join(data, entry), NOBODY, NOBODY)
        os.chmod(db, 0o444)
        os.chmod(data, 0o555 if folder_ro else 0o755)
        before = sha(db)
        try:
            result = run_child(WORKLOAD, child_env(folder, home=home), prefix=prefix)
        finally:
            os.chmod(data, 0o755)
        beleg("Schreibschutz %s: %d Meldungen, erste: %s" % (
            name, len(result["meldungen"]), (result["meldungen"] or [""])[0][:90]))
        self.assertEqual(len(result["meldungen"]), 1, result["meldungen"][:6])
        self.assertIn("Dein Lernfortschritt wird nicht gespeichert: Der Datenordner ist "
                      "schreibgeschützt.", result["meldungen"][0])
        self.assertEqual(result["read_only_reason"], "schreibschutz")
        self.assertFalse(result["log_trainer"])
        self.assertEqual(sha(db), before)

    def test_ordner_und_datei(self):
        self.run_case("ro_ordner", folder_ro=True)

    def test_nur_datei(self):
        self.run_case("ro_datei", folder_ro=False)


class HeileDatenbank(unittest.TestCase):
    """Schutz-Test (auch auf v0.62.3 gruen): keine Meldung, Schreiben geht."""

    def test_normal(self):
        folder = os.path.join(WORK, "heil")
        db = make_valid_db(folder, quiz=100, cards=5)
        result = run_child(WORKLOAD, child_env(folder))
        self.assertEqual(result["meldungen"], [])
        self.assertTrue(result["log_trainer"])
        self.assertIsNone(result["read_only_reason"])
        conn = sqlite3.connect(db)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM quiz_answers").fetchone()[0], 104)
        conn.close()
        self.assertFalse(os.path.exists(os.path.join(folder, "data", "fehler.log")))


class Laufzeit(unittest.TestCase):
    """Schutz-Test: PRAGMA quick_check auf einer grossen Datenbank (deutlich
    mehr Eintraege als nach Jahren Lernen) bremst den Start nicht spuerbar."""

    def test_quick_check_gross(self):
        folder = os.path.join(WORK, "gross")
        db = make_valid_db(folder, quiz=200000, cards=200000)
        size = os.path.getsize(db)
        times = []
        for _ in range(3):
            conn = sqlite3.connect(db)
            started = time.perf_counter()
            rows = conn.execute("PRAGMA quick_check(1)").fetchall()
            times.append(time.perf_counter() - started)
            conn.close()
        self.assertEqual(rows, [("ok",)])
        result = run_child(r"""
import json, time, fisi_core
t = time.perf_counter(); fisi_core.DBManager(); print(json.dumps(time.perf_counter() - t))
""", child_env(folder))
        beleg("quick_check auf %.1f MB (400.000 Eintraege): %s ms; DBManager() gesamt %.0f ms"
              % (size / 1e6, " / ".join("%.0f" % (t * 1000) for t in times), result * 1000))
        self.assertLess(min(times), QUICK_CHECK_LIMIT)


GUI_CHILD = r"""
import json, os, time, traceback
from tkinter import messagebox
dialoge = []
for name in ("showerror", "showwarning", "showinfo", "askyesno", "askokcancel"):
    setattr(messagebox, name, lambda title=None, message=None, _n=name, **kw:
            dialoge.append([_n, title, str(message)[:200]]) or True)
import fisi_core
if SCHREIBSCHUTZ:
    fisi_core._folder_writable = lambda folder: False
import customtkinter as ctk
import app_gui
app_gui.apply_appearance()
root = ctk.CTk()
fehler = []
root.report_callback_exception = lambda *exc: fehler.append("".join(traceback.format_exception(*exc))[-500:])
app = app_gui.FISIApp(root)
root.geometry("1360x900+0+0")
end = time.monotonic() + 240
while time.monotonic() < end and not app.preloader.done:
    root.update(); time.sleep(0.005)
for key in ("progress", "dashboard", "quiz"):
    app.show_view(key)
    for _ in range(50):
        root.update(); time.sleep(0.005)
hint = getattr(app.sidebar, "db_hint", None)
r = {"dialoge": dialoge, "vorladen_fertig": app.preloader.done, "fehler": fehler,
     "zeile": hint.cget("text") if hint is not None else None,
     "zeile_sichtbar": bool(hint is not None and hint.winfo_ismapped())}
for job in root.tk.splitlist(root.tk.call("after", "info")):
    root.tk.call("after", "cancel", job)
root.destroy()
print(json.dumps(r, ensure_ascii=False))
"""


def _display_available():
    try:
        import tkinter
        root = tkinter.Tk()
        root.destroy()
        return True
    except Exception:
        return False


@unittest.skipUnless(_display_available(), "keine Anzeige")
class PCOberflaeche(unittest.TestCase):
    """B-G-01/B-G-03 am PC: hoechstens ein Fenster bis nach dem Vorladen und
    die bleibende rote Zeile in der Seitenleiste."""

    def run_gui(self, name, schreibschutz):
        """schreibschutz: die Schreibprobe meldet "nicht beschreibbar" (als
        root waere sonst alles beschreibbar); die echte Probe pruefen die
        Tests in Schreibschutz."""
        folder = os.path.join(WORK, name)
        if schreibschutz:
            make_valid_db(folder, quiz=50, cards=5)
        else:
            os.makedirs(os.path.join(folder, "data"))
            with open(os.path.join(folder, "data", DB_NAME), "wb") as handle:
                handle.write(bytes(random.Random(7).getrandbits(8) for _ in range(65536)))
        result = run_child("SCHREIBSCHUTZ = %r\n%s" % (schreibschutz, GUI_CHILD),
                           child_env(folder), timeout=400)
        beleg("PC %s: %d Fenster, Zeile: %s" % (name, len(result["dialoge"]), result["zeile"]))
        self.assertTrue(result["vorladen_fertig"])
        self.assertEqual(result["fehler"], [])
        self.assertEqual(len(result["dialoge"]), 1, result["dialoge"][:5])
        self.assertEqual(result["dialoge"][0][1], "Datenbankfehler")
        self.assertTrue(result["zeile_sichtbar"])
        return result

    def test_kaputt(self):
        result = self.run_gui("gui_kaputt", schreibschutz=False)
        self.assertEqual(result["zeile"], "Dein Lernfortschritt wird nicht gespeichert: "
                                          "Die Datenbank ist beschädigt.")

    def test_schreibschutz(self):
        result = self.run_gui("gui_schreibschutz", schreibschutz=True)
        self.assertEqual(result["zeile"], "Dein Lernfortschritt wird nicht gespeichert: "
                                          "Der Datenordner ist schreibgeschützt.")


def tearDownModule():
    for root, dirs, _files in os.walk(WORK):
        for name in dirs:
            try:
                os.chmod(os.path.join(root, name), 0o755)
            except OSError:
                pass
    shutil.rmtree(WORK, ignore_errors=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
