#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests fuer 0.63.2, Strang S5a: Doku-Befunde (Plan 5.9) und A11 (Attrappe).

  Attrappe      A11: put_status_n in pruefung/abgleich_attrappe.py nur unter
                STATE.lock herunterzaehlen (gleichzeitige PUTs)
  AbgleichText  B-L-01, B-L-02: was der Abgleich uebertraegt, Rechnername
  FehlerLog     B-L-03: fehler.log ohne Zugangsschluessel, scheitert nie
  ScrubLaufzeit L1 (Nacharbeit): scrub laeuft auch bei langen Ketten ohne
                Leerzeichen linear, gleiche Wirkung wie vorher
  Bericht       B-L-04: "Problem melden" verspricht nichts Falsches
  BerichtAnzeige B-L-06 (Tk): neue Zeile in haenger.log erscheint im Bericht
  Liesmich      B-K-01, B-K-02, B-K-03, B-K-04, B-K-06
  Tastatur      B-K-07: Strg+F auch mit Feststelltaste, Kuerzel in Hilfe und
                LIESMICH gleich (Tk-Teil braucht eine Anzeige)
  Klappen       B-K-N2: ein Wort "zuklappen" / "zugeklappt" (PC und Handy)
  Installer     B-N-11: Kommentar an der AppId, AppId-Zeile unveraendert

Nur lesend gegen die Programmdateien (LIESMICH.txt, fisi_hilfe.py,
fisi_diagnose.py, ...). Tk-Teile brauchen eine Anzeige (xvfb-run), ohne
Anzeige werden sie uebersprungen. Keine echten Daten: Wegwerf-HOME und
-Datenbank in einem Temp-Ordner (FISI_DB_PATH).

Start:  xvfb-run -a python test_doku_0632.py
"""

import ast
import json
import os
import random
import re
import subprocess
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
WORK = tempfile.mkdtemp(prefix="fisi_doku0632_")
HOME = os.path.join(WORK, "home")
os.makedirs(HOME, exist_ok=True)
os.environ["HOME"] = HOME
os.environ["FISI_DB_PATH"] = os.path.join(HOME, "lern.db")

sys.path.insert(0, os.path.join(HERE, "pruefung"))
sys.path.insert(0, HERE)


def lesen(name):
    with open(os.path.join(HERE, name), encoding="utf-8") as f:
        return f.read()


# ---------------------------------------------------------------- A11 ---

def _with_lock(node):
    """True, wenn node ein 'with STATE.lock:'-Block ist."""
    if not isinstance(node, ast.With):
        return False
    for item in node.items:
        expr = item.context_expr
        if isinstance(expr, ast.Attribute) and expr.attr == "lock" \
                and isinstance(expr.value, ast.Name) and expr.value.id == "STATE":
            return True
    return False


def _walk_mit_sperre(node, in_lock=False):
    """(knoten, liegt_unter_STATE.lock) fuer alle Knoten unter node."""
    for child in ast.iter_child_nodes(node):
        lock = in_lock or _with_lock(child)
        yield child, lock
        yield from _walk_mit_sperre(child, lock)


class Attrappe(unittest.TestCase):
    """A11: put_status_n nur unter STATE.lock lesen und herunterzaehlen."""

    def _do_put(self):
        tree = ast.parse(lesen(os.path.join("pruefung", "abgleich_attrappe.py")))
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == "Handler":
                for f in node.body:
                    if isinstance(f, ast.FunctionDef) and f.name == "do_PUT":
                        return f
        self.fail("Handler.do_PUT nicht gefunden")

    def test_put_status_n_unter_sperre(self):
        """Lesen und Schreiben von put_status_n liegt in 'with STATE.lock'."""
        zugriffe = []
        for node, lock in _walk_mit_sperre(self._do_put()):
            if isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant) \
                    and node.slice.value == "put_status_n":
                zugriffe.append((node.lineno, "Schreiben", lock))
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
                    and node.func.attr == "get" and node.args \
                    and isinstance(node.args[0], ast.Constant) \
                    and node.args[0].value in ("put_status", "put_status_n"):
                zugriffe.append((node.lineno, "Lesen " + node.args[0].value, lock))
        self.assertTrue(any(z[1] == "Schreiben" for z in zugriffe), zugriffe)
        ohne = [z for z in zugriffe if not z[2]]
        self.assertEqual(ohne, [], "ohne STATE.lock: %r" % ohne)

    def test_kein_schlafen_und_keine_antwort_unter_sperre(self):
        """Schutz: put_hang (sleep 600) und die Antwort nie unter der Sperre,
        sonst blockiert ein haengender PUT alle anderen Anfragen."""
        schlecht = []
        for node, lock in _walk_mit_sperre(self._do_put()):
            if lock and isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
                    and node.func.attr in ("sleep", "_json", "_send"):
                schlecht.append((node.lineno, node.func.attr))
        self.assertEqual(schlecht, [])

    def test_gleichzeitige_puts_genau_n_mal(self):
        """Verhalten: 200 gleichzeitige PUTs, put_status=500,
        put_status_n=50 -> genau 50 x 500. Das Lesen von put_status_n ist
        kuenstlich verlangsamt (2 ms, LangsamesLesen), damit das Rennen
        zwischen Lesen und Herunterzaehlen sicher sichtbar wird: auf
        14b3bd4 (ohne Sperre) kommen deutlich mehr als 50 x 500 (Nacharbeit
        L2, Gegenpruefung Punkt 3)."""
        import time
        import abgleich_attrappe as att
        from http.server import ThreadingHTTPServer

        class Server(ThreadingHTTPServer):
            request_queue_size = 256   # 200 Verbindungen auf einmal annehmen
            daemon_threads = True

        class LangsamesLesen(dict):
            def get(self, key, default=None):
                wert = dict.get(self, key, default)
                if key == "put_status_n":
                    time.sleep(0.002)
                return wert

        server = Server(("127.0.0.1", 0), att.Handler)
        port = server.server_address[1]
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            base = "http://127.0.0.1:%d" % port

            def post(obj):
                req = urllib.request.Request(base + "/_ctl", data=json.dumps(obj).encode(),
                                             method="POST")
                urllib.request.urlopen(req, timeout=10).read()

            post({"reset": True})
            post({"put_status": 500, "put_status_n": 50})
            with att.STATE.lock:
                att.STATE.ctl = LangsamesLesen(att.STATE.ctl)
            codes = []
            sperre = threading.Lock()
            start = threading.Event()

            def put():
                body = json.dumps({"message": "t", "content": "eA=="}).encode()
                req = urllib.request.Request(
                    base + "/repos/o/r/contents/lernstand.json.gz", data=body, method="PUT",
                    headers={"Authorization": "Bearer x"})
                start.wait(10)
                try:
                    code = urllib.request.urlopen(req, timeout=20).status
                except urllib.error.HTTPError as e:
                    code = e.code
                except Exception as e:  # Verbindungsfehler sichtbar machen
                    code = repr(e)
                with sperre:
                    codes.append(code)

            alt = sys.getswitchinterval()
            sys.setswitchinterval(1e-6)
            try:
                threads = [threading.Thread(target=put) for _ in range(200)]
                for t in threads:
                    t.start()
                start.set()
                for t in threads:
                    t.join(60)
            finally:
                sys.setswitchinterval(alt)
            self.assertEqual(len(codes), 200)
            self.assertTrue(all(isinstance(c, int) for c in codes), codes)
            self.assertEqual(codes.count(500), 50, sorted(codes))
            with att.STATE.lock:
                self.assertEqual(dict.get(att.STATE.ctl, "put_status_n"), 0)
        finally:
            with att.STATE.lock:
                att.STATE.ctl = dict(att.STATE.ctl)
            server.shutdown()
            server.server_close()


# ---------------------------------------------------------- Doku 5.9 ---

UMSCHRIFT = {"ä": "ae", "ö": "oe", "ü": "ue", "Ä": "Ae", "Ö": "Oe", "Ü": "Ue", "ß": "ss",
             "„": '"', "“": '"', "–": "-", "…": "..."}


def ascii_text(text):
    """Programmtext so umgeschrieben, wie er in der ASCII-LIESMICH steht."""
    for old, new in UMSCHRIFT.items():
        text = text.replace(old, new)
    return text


def eng(text):
    """Leerraum (auch Zeilenumbrueche) zu einem Leerzeichen zusammenfassen."""
    return " ".join(text.split())


def liesmich_abschnitt(titel):
    """Abschnitt der LIESMICH unter einer Ueberschrift in GROSSBUCHSTABEN
    (bis zur naechsten solchen Ueberschrift)."""
    lines = lesen("LIESMICH.txt").split("\n")
    start = lines.index(titel)
    end = len(lines)
    for i in range(start + 2, len(lines) - 1):
        if lines[i + 1].startswith("-----") and lines[i].strip():
            end = i
            break
    return "\n".join(lines[start:end])


def liesmich_eintrag(name):
    """Eintrag der Bereichsliste oben in der LIESMICH, z.B. "Rechner"."""
    lines = lesen("LIESMICH.txt").split("\n")
    for i, line in enumerate(lines):
        if line.startswith("  %s " % name) and line[2 + len(name):].startswith("   "):
            block = [line]
            for follow in lines[i + 1:]:
                if not follow.strip():
                    break
                block.append(follow)
            return eng("\n".join(block))
    raise AssertionError("Eintrag %s fehlt" % name)


def hilfe(section_id):
    import fisi_hilfe as fh
    return next(s["text"] for s in fh.HELP_SECTIONS if s["id"] == section_id)


class AbgleichText(unittest.TestCase):
    """B-L-01, B-L-02: LIESMICH und Hilfe nennen alles, was der Abgleich
    uebertraegt (SYNC_TABLES), und den Rechnernamen."""

    # Tabelle -> (Wort in LIESMICH, Wort in der Hilfe). Eine neue Tabelle
    # ohne Eintrag macht den Test rot: dann bitte die Doku ergaenzen.
    ZUORDNUNG = {
        "card_events": ("was wann gelernt", "was du wann gelernt"),
        "quiz_answers": ("was wann gelernt", "was du wann gelernt"),
        "scenario_events": ("was wann gelernt", "was du wann gelernt"),
        "project_events": ("was wann gelernt", "was du wann gelernt"),
        "ap1_events": ("was wann gelernt", "was du wann gelernt"),
        "trainer_aufgaben": ("was wann gelernt", "was du wann gelernt"),
        "test_results": ("Ergebnisse von Tests", "Ergebnisse deiner Tests"),
        "pruefungen": ("Pruefungen (Punkte und Note, nicht deine Antworten)",
                       "Prüfungen (Punkte und Note, nicht deine Antworten)"),
        "abschlussprojekt": ("Abschlussprojekts", "Abschlussprojekts"),
        "spiel_ereignisse": ("Spielstaende", "Spielstände"),
        "spiel_plaetze": ("Spielstaende", "Spielstände"),
        "spiel_bestenliste": ("Bestenliste", "Bestenliste"),
    }

    def test_jede_tabelle_hat_eine_zuordnung(self):
        import fisi_core
        self.assertEqual(sorted(fisi_core.SYNC_TABLES), sorted(self.ZUORDNUNG))

    def test_aufzaehlung_wie_sync_tables(self):
        liesmich = eng(liesmich_abschnitt("ABGLEICH PC UND HANDY"))
        text = eng(hilfe("abgleich"))
        for table, (wort_liesmich, wort_hilfe) in self.ZUORDNUNG.items():
            self.assertIn(wort_liesmich, liesmich, table)
            self.assertIn(wort_hilfe, text, table)
        self.assertNotIn("keine anderen Daten", liesmich)
        self.assertIn("Loeschungen", liesmich)
        self.assertIn("Auch Löschen wird abgeglichen", text)

    def test_rechnername_in_abgleich_und_sicherung(self):
        """B-L-02: Geraetename (am PC mit Rechnername) in Abgleich und Sicherung."""
        self.assertIn('am PC "PC" und der Rechnername',
                      eng(liesmich_abschnitt("ABGLEICH PC UND HANDY")))
        self.assertIn('am PC "PC" und der Rechnername',
                      eng(liesmich_abschnitt("WO WERDEN DIE LERNFORTSCHRITTE GESPEICHERT?")))
        self.assertIn("am PC mit dem Rechnernamen", hilfe("abgleich"))
        self.assertIn("am PC mit dem Rechnernamen", hilfe("sicherung"))

    def test_geraetename_wie_im_programm(self):
        """Schutz: die Doku beschreibt, was das Programm tatsaechlich eintraegt."""
        quelle = lesen("app_gui.py")
        self.assertIn('return "PC %s" % (platform.node() or "").strip()', quelle)
        self.assertIn('fisi_sync.sync(self.app.db, device="Handy")',
                      lesen(os.path.join("mobile", "src", "main.py")))


class FehlerLog(unittest.TestCase):
    """B-L-03 (FG-5): write_error_log filtert Zugangsschluessel wie der
    Bericht und scheitert selbst nie."""

    # selbst erfundene Platzhalter-Schluessel (wie test_werkzeuge.py)
    GHP = "ghp_" + "A1b2C3d4E5f6G7h8I9j0" * 2
    PAT = "github_pat_" + "11AAAAAAA0" * 4
    BEARER = "abcDEF123456ghiJKL789"

    def setUp(self):
        self.ordner = tempfile.mkdtemp(prefix="fehlerlog_", dir=WORK)
        self.pfad = os.path.join(self.ordner, "fehler.log")

    def _text(self):
        return ("urllib.error.HTTPError: 401 bei https://api.github.com mit %s\n"
                "Token %s\nAuthorization: Bearer %s\n" % (self.GHP, self.PAT, self.BEARER))

    def test_token_wird_in_fehler_log_entfernt(self):
        import fisi_core
        fisi_core.write_error_log(self._text(), path=self.pfad)
        with open(self.pfad, encoding="utf-8") as f:
            inhalt = f.read()
        self.assertIn("HTTPError: 401", inhalt)
        self.assertIn("[entfernt]", inhalt)
        for geheim in (self.GHP, self.PAT, self.BEARER):
            self.assertNotIn(geheim, inhalt)

    def test_unbeschreibbarer_pfad_wirft_nicht(self):
        """Auflage FG-5: ein Ordner als Pfad (nicht beschreibbar) -> kein Fehler."""
        import fisi_core
        fisi_core.write_error_log(self._text(), path=self.ordner)
        fisi_core.write_error_log(self._text(),
                                  path=os.path.join(self.ordner, "fehlt", "x", "fehler.log"))

    def test_scheiternde_einfuhr_wirft_nicht_und_verraet_nichts(self):
        """Auflage FG-5: laesst sich fisi_diagnose nicht laden, wirft
        write_error_log trotzdem nicht und schreibt keinen Schluessel."""
        import fisi_core
        alt = sys.modules.get("fisi_diagnose")
        sys.modules["fisi_diagnose"] = None      # import -> ImportError
        try:
            fisi_core.write_error_log(self._text(), path=self.pfad)
        finally:
            if alt is None:
                sys.modules.pop("fisi_diagnose", None)
            else:
                sys.modules["fisi_diagnose"] = alt
        inhalt = open(self.pfad, encoding="utf-8").read() if os.path.exists(self.pfad) else ""
        for geheim in (self.GHP, self.PAT, self.BEARER):
            self.assertNotIn(geheim, inhalt)

    def test_scheiternder_filter_wirft_nicht(self):
        import fisi_core
        import fisi_diagnose

        def kaputt(*_a, **_k):
            raise RuntimeError("Filter kaputt")
        alt = fisi_diagnose.scrub
        fisi_diagnose.scrub = kaputt
        try:
            fisi_core.write_error_log(self._text(), path=self.pfad)
        finally:
            fisi_diagnose.scrub = alt
        inhalt = open(self.pfad, encoding="utf-8").read() if os.path.exists(self.pfad) else ""
        self.assertNotIn(self.GHP, inhalt)

    def test_nur_write_error_log_ruft_scrub(self):
        """Schutz: die spaete Einfuhr steht in write_error_log (oben in
        fisi_core gaebe es einen Kreis, fisi_diagnose liest fisi_core)."""
        tree = ast.parse(lesen("fisi_core.py"))
        oben = [n for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom))
                and "fisi_diagnose" in ast.dump(n)]
        self.assertEqual(oben, [])
        func = next(n for n in tree.body if isinstance(n, ast.FunctionDef)
                    and n.name == "write_error_log")
        body = [n for n in func.body if not (isinstance(n, ast.Expr)
                                             and isinstance(n.value, ast.Constant))]
        self.assertEqual(len(body), 1)
        self.assertIsInstance(body[0], ast.Try)                 # alles im try
        self.assertIsInstance(body[0].body[0], ast.ImportFrom)  # Einfuhr zuerst
        self.assertEqual(body[0].body[0].module, "fisi_diagnose")


# Muster fuer "Schluessel = Wert" in fisi_diagnose bis 121321b (Vergleich,
# quadratische Laufzeit bei langen Ketten ohne Leerzeichen)
SCRUB_ALT = (r"(?i)([\"']?[\w-]*(?:token|passw\w*|kennwort|secret|api[_-]?key)[\"']?"
             r"\s*[:=]\s*)(\"[^\"]*\"|'[^']*'|[^\s,;}]+)")

# laeuft in einem eigenen Prozess (mit Zeitgrenze, damit ein quadratischer
# Stand nicht minutenlang haengt) und gibt die Dauer je Kette aus
SCRUB_ZEIT = """
import sys, time
sys.path.insert(0, sys.argv[1])
import fisi_diagnose as fd
for n in (20000, 100000):
    for teil in ("A", "0123456789abcdef", "passw", "token", "a-", "ghp_", "bearer",
                 "authorization", "https:", "http://a", "x@", '"', "="):
        text = (teil * (n // len(teil) + 1))[:n]
        t = time.perf_counter()
        fd.scrub(text)
        print("%d %r %.4f" % (n, teil, time.perf_counter() - t), flush=True)
"""


class ScrubLaufzeit(unittest.TestCase):
    """L1 (Nacharbeit): scrub laeuft seit B-L-03 in jedem write_error_log.
    Lange Ketten ohne Leerzeichen (z.B. eine Hex-Folge) duerfen den
    aufrufenden Faden nicht sekundenlang blockieren; die Wirkung bleibt
    gleich (ghp_, github_pat_, Bearer, token=, Token in Adressen)."""

    GRENZE = 0.5     # Sekunden je Kette (gemessen linear: unter 0,1 s)

    def test_lange_ketten_linear(self):
        try:
            lauf = subprocess.run([sys.executable, "-c", SCRUB_ZEIT, HERE],
                                  capture_output=True, text=True, timeout=20)
        except subprocess.TimeoutExpired as e:
            self.fail("scrub zu langsam (Zeitgrenze 20 s), bis dahin: %r" % (e.stdout,))
        self.assertEqual(lauf.returncode, 0, lauf.stderr)
        zeilen = lauf.stdout.split("\n")[:-1]
        self.assertEqual(len(zeilen), 26, lauf.stdout)
        zu_lang = [z for z in zeilen if float(z.rsplit(" ", 1)[1]) > self.GRENZE]
        self.assertEqual(zu_lang, [])

    def _alt(self, text):
        import fisi_diagnose as fd
        alt = re.compile(SCRUB_ALT)
        for pattern, replacement in fd._PATTERNS:
            if "kennwort" in pattern.pattern:
                pattern = alt
            text = pattern.sub(replacement, text)
        return text

    def test_gleiche_wirkung_wie_vorher(self):
        import fisi_diagnose as fd
        self.assertEqual(sum("kennwort" in p.pattern for p, _r in fd._PATTERNS), 1)
        korpus = [
            "token=ghp_" + "a" * 36, "Authorization: Bearer abc.def-123456",
            "https://x:y@github.com/a", "https://ghp_abc@github.com/o/r",
            '{"token": "geheim123", "passwort": \'abc\', "api_key": "k"}',
            "GITHUB_TOKEN=abc; next", "my-api-key: 123", "x-passwort-neu = 1",
            "passwordHash: 7", "pw-token\t:\t'q'", '"Token" : "v"', 'abc"token=1',
            "foo=token=abc", "secret:", "token=", 'Kennwort = ""', "apikey=1 api-key=2",
            FehlerLog.GHP, FehlerLog.PAT, "Token " + FehlerLog.PAT,
            "Datenordner: /home/nico/.local/share\nTagesziel: 20 Aufgaben",
        ]
        teile = ["token", "TOKEN", "passw", "Passwort", "kennwort", "Secret", "apikey",
                 "api_key", "api-key", "api", "key", "-", "_", "a", "Z", "9", "ä", "=", ":",
                 " ", '"', "'", ",", ";", "}", "pass", "tok", "en", "\n", "\t", "ghp_",
                 "github_pat_", "A1b2C3d4E5f6G7h8", "bearer ", "https://", "@", "/"]
        zufall = random.Random(632)
        for _ in range(20000):
            korpus.append("".join(zufall.choice(teile) for _ in range(zufall.randint(0, 12))))
        anders = [(t, self._alt(t), fd.scrub(t)) for t in korpus if self._alt(t) != fd.scrub(t)]
        self.assertEqual(anders[:5], [])
        # Wirkung wie bisher: die bekannten Schluessel verschwinden
        for geheim, text in (
                (FehlerLog.GHP, "Fehler mit %s" % FehlerLog.GHP),
                (FehlerLog.PAT, "PAT %s" % FehlerLog.PAT),
                ("abcDEF123456", "Authorization: Bearer abcDEF123456"),
                ("abcDEF123456", "bearer abcDEF123456"),
                ("wert123", "token=wert123"),
                ("ghp_kurz", "https://ghp_kurz@github.com/o/r")):
            self.assertNotIn(geheim, fd.scrub(text), text)


class Bericht(unittest.TestCase):
    """B-L-04: kein falsches Versprechen, Bitte um Ansehen vor dem Weitergeben."""

    def test_kein_falsches_versprechen(self):
        import fisi_diagnose as fdg
        for name, text in (("fdg.HELP", fdg.HELP), ("Hilfe problem", hilfe("problem"))):
            self.assertNotIn("Projekttexte stehen nicht darin", text, name)
            self.assertNotIn("stehen nicht darin", text, name)
            self.assertIn("vor dem Weitergeben an", text, name)
            self.assertIn("Andere Angaben aus Fehlermeldungen", text, name)
        self.assertNotIn("stehen nie darin", lesen("fisi_diagnose.py"))


def _display_ok():
    try:
        import tkinter
        root = tkinter.Tk()
        root.destroy()
        return True
    except Exception:
        return False


HAS_DISPLAY = _display_ok()


@unittest.skipUnless(HAS_DISPLAY, "keine Anzeige (z.B. mit xvfb-run starten)")
class PcOberflaeche(unittest.TestCase):
    """B-L-06 und B-K-07 am echten FISIApp (Wegwerf-Datenbank)."""

    @classmethod
    def setUpClass(cls):
        import customtkinter as ctk
        import app_gui
        import fisi_hilfe as fh
        fh.mark_tour_seen()
        app_gui.UpdateController.auto_check = lambda self: None
        app_gui.SyncController.auto_start = lambda self: None
        cls.app_gui = app_gui
        cls.root = ctk.CTk()
        cls.root.geometry("1360x900+0+0")
        cls.app = app_gui.FISIApp(cls.root)
        cls.pump()

    @classmethod
    def tearDownClass(cls):
        for job in cls.root.tk.splitlist(cls.root.tk.call("after", "info")):
            cls.root.tk.call("after", "cancel", job)
        cls.root.destroy()

    @classmethod
    def pump(cls, times=8):
        for _ in range(times):
            cls.root.update_idletasks()
            cls.root.update()

    def test_neue_haenger_zeile_erscheint(self):
        """B-L-06: Eine neue Zeile in haenger.log (und laeuft.info) steht nach
        erneutem Anzeigen im Bericht, auch wenn fehler.log gleich blieb."""
        import fisi_diagnose as fdg
        import fisi_optionen as fo
        from fisi_core import error_log_path
        self.app.show_view("settings")
        self.pump()
        view = self.app.views["settings"]
        view.open_area(fo.DIAGNOSE_ID)
        self.pump()
        view._show_report()
        self.pump()
        ordner = os.path.dirname(error_log_path())
        for name, zeile in ((fdg.HANG_LOG_NAME, "Haenger-Testzeile 0632"),
                            (fdg.INFO_NAME, "Info-Testzeile 0632")):
            vorher = view.report_box.get("1.0", "end")
            self.assertNotIn(zeile, vorher)
            with open(os.path.join(ordner, name), "a", encoding="utf-8") as f:
                f.write(zeile + "\n")
            view._show_report()
            self.pump()
            self.assertIn(zeile, view.report_box.get("1.0", "end"), name)

    def test_strg_f_auch_mit_feststelltaste(self):
        """B-K-07: <Control-F> (Feststelltaste) ist gebunden wie <Control-f>
        und setzt den Fokus ins Suchfeld."""
        root = self.app.root
        self.assertTrue(root.bind("<Control-f>"))
        self.assertTrue(root.bind("<Control-F>"))
        self.app.show_view("dashboard")
        self.pump()
        root.focus_force()
        self.pump()
        entry = self.app.header.search_entry
        for event in ("<Control-f>", "<Control-F>"):
            root.focus_set()
            self.pump()
            self.assertNotEqual(root.focus_get(), entry._entry)
            root.event_generate(event)
            self.pump()
            self.assertEqual(root.focus_get(), entry._entry, event)


class Tastatur(unittest.TestCase):
    """B-K-07: dieselben Kuerzel in Hilfe und LIESMICH."""

    KUERZEL = ("Strg+F", "Strg+Eingabe", "Umschalt+Tab", "Tab", "Leertaste", "Esc")

    def test_kuerzel_in_hilfe_und_liesmich(self):
        text = hilfe("tastatur")
        liesmich = liesmich_abschnitt("TASTENKUERZEL").replace(" + ", "+")
        for kuerzel in self.KUERZEL:
            # als eigenes Wort: "Tab" zaehlt nicht als Teil von "Umschalt+Tab"
            # (Nacharbeit L4), "Strg+F" nicht als Teil von "Strg+Fx"
            muster = r"(?<![\w+])%s(?![\w+])" % re.escape(kuerzel)
            self.assertRegex(text, muster, kuerzel)
            self.assertRegex(liesmich, muster, kuerzel)


class Liesmich(unittest.TestCase):
    """B-K-01, B-K-02, B-K-03, B-K-04, B-K-06."""

    def test_repository_nur_platzhalter(self):
        import re
        text = lesen("LIESMICH.txt")
        namen = re.findall(r"([\w.-]+)/fisi-lernstand", text)
        self.assertTrue(namen)
        self.assertEqual(set(namen), {"deinname"})
        self.assertNotIn("ist bereits angelegt", text)

    def test_rechner_wie_hilfe(self):
        import re
        # „Rechner“ (Reiter), dann die vier Rechner
        namen = re.findall(r"„([^“]+)“", hilfe("rechner").split("\n\n")[0])[1:5]
        self.assertEqual(len(namen), 4, namen)
        self.assertIn("USV-Kapazität", namen)
        eintrag = liesmich_eintrag("Rechner")
        for name in namen:
            self.assertIn(ascii_text(name), eintrag, name)

    def test_optionen_wie_areas(self):
        import fisi_optionen as fo
        eintrag = liesmich_eintrag("Optionen")
        for area in fo.AREAS:
            self.assertIn(eng(ascii_text(area["titel"])), eintrag, area["id"])

    def test_dateiliste_vollstaendig(self):
        abschnitt = liesmich_abschnitt("DATEIEN IM PAKET")
        programme = sorted(name for name in os.listdir(HERE) if name.endswith(".py") and (
            name.startswith("fisi_") or name in ("app_gui.py", "start.py", "build.py",
                                                 "lizenzen.py")))
        self.assertGreater(len(programme), 20)
        fehlen = [name for name in programme if "\n  %s " % name not in abschnitt]
        self.assertEqual(fehlen, [])
        self.assertIn("\n  test_*.py ", abschnitt)

    def test_abgleich_meldungen_woertlich(self):
        import fisi_sync
        text = eng(lesen("LIESMICH.txt"))
        for code in (401, 404):
            meldung = eng(ascii_text(fisi_sync._http_error(code, "X")).replace(" X ", " ... "))
            self.assertIn('Abgleich meldet "%s"' % meldung, text, code)


class Klappen(unittest.TestCase):
    """B-K-N2: ein Wort - sichtbar "zuklappen", Tastatur/TalkBack "zugeklappt"."""

    ALT = ("einklapp", "eingeklapp")

    def _strings(self, name):
        tree = ast.parse(lesen(name))
        return [(n.lineno, n.value) for n in ast.walk(tree)
                if isinstance(n, ast.Constant) and isinstance(n.value, str)]

    def _fold_label_doc(self):
        tree = ast.parse(lesen("fisi_theme.py"))
        func = next(n for n in tree.body
                    if isinstance(n, ast.FunctionDef) and n.name == "fold_label")
        return func.body[0].value

    def test_ein_wort_in_widgets_und_handy(self):
        for name in ("fisi_widgets.py", os.path.join("mobile", "src", "ui.py")):
            alt = [(z, s) for z, s in self._strings(name)
                   if any(w in s.lower() for w in self.ALT)]
            self.assertEqual(alt, [], name)

    def test_ein_wort_in_theme(self):
        """fisi_theme.py mitpruefen (Nacharbeit L3), ohne Ausnahme: seit
        FG-79 sagt auch der Docstring von fold_label "zugeklappt"."""
        alt = [(z, s) for z, s in self._strings("fisi_theme.py")
               if any(w in s.lower() for w in self.ALT)]
        self.assertEqual(alt, [])

    def test_theme_fold_label_docstring(self):
        """FG-79: Docstring fisi_theme.py fold_label sagt "zugeklappt"."""
        doc = self._fold_label_doc().value.lower()
        self.assertIn('"farben, zugeklappt"', doc)
        self.assertFalse(any(w in doc for w in self.ALT), doc)

    def test_werte_und_beschriftung(self):
        import fisi_theme as th
        self.assertEqual((th.FOLD_OPEN_TEXT, th.FOLD_CLOSE_TEXT), ("aufklappen", "zuklappen"))
        self.assertEqual(th.FOLD_STATE_CLOSED, "zugeklappt")
        self.assertEqual(th.fold_label("Farben", False), "Farben, zugeklappt")
        self.assertEqual(th.fold_label("Farben", True), "Farben, aufgeklappt")

    def test_pc_und_handy_gleiches_wort(self):
        """Klappkarten ohne Marker sagen schon "zuklappen" (PC und Handy);
        die Optionen (Marker) jetzt auch."""
        import fisi_theme as th
        self.assertIn('"▾  zuklappen"', lesen("fisi_widgets.py"))
        self.assertIn('close_text="zuklappen"', lesen(os.path.join("mobile", "src", "ui.py")))
        self.assertEqual(th.FOLD_CLOSE_TEXT, "zuklappen")


class Installer(unittest.TestCase):
    """B-N-11 (FG-18): Kommentar an der AppId, die Zeile selbst unveraendert."""

    def test_appid_kommentar(self):
        iss = lesen("FISI-Lernplattform.iss")
        self.assertIn("\nAppId={{6B2E7B7B-6C1E-4E59-9C55-FISI-LERNPLATTFORM}}\n", iss)
        lines = iss.split("\n")
        i = lines.index("AppId={{6B2E7B7B-6C1E-4E59-9C55-FISI-LERNPLATTFORM}}")
        self.assertEqual(lines[i - 3], "[Setup]")
        self.assertTrue(lines[i - 2].startswith("; AppId: "), lines[i - 2])
        self.assertIn("NIE AENDERN", lines[i - 1])


if __name__ == "__main__":
    unittest.main(verbosity=2)
