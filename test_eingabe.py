#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests fuer 0.59.3 (fisi_eingabe.py und die kleinen Korrekturen).

  * X: Bedingungslogik der Eingabemethoden-Umgehung - alle Kombinationen aus
    System, Sitzungsart, XMODIFIERS und Schalter FISI_XIM; nur einmal
    wirksam; aendert die Umgebung danach nicht mehr; Fehler bleiben still;
    ein neu gestarteter Prozess (Neustart nach Update) prueft selbst neu
  * X2: Startzeile in haenger.log, Startzeile der Messdatei (Spalte vorgang)
  * K1: derselbe kill-Befehl in Optionen, Hilfe und LIESMICH
  * K3: Vorladen - Vorgang bleibt bis nach der Leerlauf-Runde stehen,
    "vorladen:start" bis zum ersten Schritt; Begrenzungen unveraendert
  * Nachstellung (nur mit IBus und Display): Tk haengt in XCreateIC, wenn
    ibus-daemon nicht antwortet - mit der Umgehung nicht

Start:  python test_eingabe.py
"""

import itertools
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import fisi_eingabe as fe  # noqa: E402
import fisi_haenger as fhg  # noqa: E402
import fisi_leistung as fle  # noqa: E402


def _display_ok():
    try:
        import tkinter
        root = tkinter.Tk()
        root.destroy()
        return True
    except Exception:  # noqa: BLE001
        return False


HAS_TK = _display_ok()


class _Frisch(unittest.TestCase):
    def setUp(self):
        fe._reset_for_tests()

    def tearDown(self):
        fe._reset_for_tests()


# ============================================================================
#  X - Bedingungen
# ============================================================================

SYSTEME = ("linux", "win32", "darwin")
SITZUNGEN = (("wayland", None), ("x11", None), ("", None), (None, "wayland-0"),
             ("x11", "wayland-0"), ("WAYLAND", None), ("tty", None))
MODIFIER = ("@im=ibus", "@im=fcitx", "@im=none", "", None, "@im=ibus @foo")
SCHALTER = ("1", "0", "", None)


def _umgebung(sitzung, display, modifier, schalter):
    env = {"HOME": "/home/x"}
    if sitzung is not None:
        env["XDG_SESSION_TYPE"] = sitzung
    if display is not None:
        env["WAYLAND_DISPLAY"] = display
    if modifier is not None:
        env["XMODIFIERS"] = modifier
    if schalter is not None:
        env[fe.SWITCH] = schalter
    return env


class BedingungTest(_Frisch):

    def test_alle_kombinationen(self):
        geprueft = aktiv = 0
        for system, (sitzung, display), modifier, schalter in itertools.product(
                SYSTEME, SITZUNGEN, MODIFIER, SCHALTER):
            fe._reset_for_tests()
            env = _umgebung(sitzung, display, modifier, schalter)
            before = dict(env)
            result = fe.apply(env, system)
            # Ab 0.60 (E3): keine Wayland-Bedingung mehr, X11 genauso
            erwartet = (system == "linux"
                        and "@im=ibus" in (modifier or "")
                        and schalter != "1")
            fall = (system, sitzung, display, modifier, schalter)
            self.assertEqual(result["aktiv"], erwartet, fall)
            self.assertEqual(result["vorher"], modifier, fall)
            wayland = (sitzung or "").lower() == "wayland" or bool(display)
            self.assertEqual(result["art"], ("" if system != "linux"
                                             else "Wayland" if wayland else "X11"), fall)
            if erwartet:
                aktiv += 1
                self.assertEqual(env["XMODIFIERS"], "@im=none", fall)
                expected = dict(before, XMODIFIERS="@im=none")
                self.assertEqual(env, expected, fall)     # nur diese eine Variable
                self.assertEqual(result["nachher"], "@im=none", fall)
            else:
                self.assertEqual(env, before, fall)       # gar nichts geaendert
                self.assertTrue(result["grund"], fall)
            geprueft += 1
        self.assertEqual(geprueft, 3 * 7 * 6 * 4)
        # linux x (alle 7 Sitzungen) x (ibus, ibus+foo) x (0, "", None)
        self.assertEqual(aktiv, 7 * 2 * 3)

    def test_windows_und_macos_unveraendert(self):
        for system in ("win32", "darwin", "cygwin", "freebsd13"):
            fe._reset_for_tests()
            env = {"XDG_SESSION_TYPE": "wayland", "WAYLAND_DISPLAY": "wayland-0",
                   "XMODIFIERS": "@im=ibus"}
            self.assertFalse(fe.apply(env, system)["aktiv"], system)
            self.assertEqual(env["XMODIFIERS"], "@im=ibus")

    def test_schalter_laesst_alles_wie_bisher(self):
        env = {"XDG_SESSION_TYPE": "wayland", "XMODIFIERS": "@im=ibus", "FISI_XIM": "1"}
        result = fe.apply(env, "linux")
        self.assertFalse(result["aktiv"])
        self.assertEqual(result["grund"], "FISI_XIM=1")
        self.assertEqual(env["XMODIFIERS"], "@im=ibus")

    def test_nur_einmal_wirksam_und_spaeter_keine_aenderung(self):
        env = {"XDG_SESSION_TYPE": "wayland", "XMODIFIERS": "@im=ibus"}
        first = fe.apply(env, "linux")
        self.assertTrue(first["aktiv"])
        # R1 (Nico): nicht zuruecksetzen - auch ein zweiter Aufruf oder
        # spaetere Abfragen aendern die Umgebung nicht mehr
        env["XMODIFIERS"] = "@im=ibus"
        second = fe.apply(env, "linux")
        self.assertIs(second, first)
        self.assertEqual(env["XMODIFIERS"], "@im=ibus")
        self.assertIs(fe.result(), first)
        fe.start_text()
        self.assertEqual(env["XMODIFIERS"], "@im=ibus")

    def test_fehler_bleiben_still(self):
        class Kaputt(dict):
            def get(self, *_args, **_kwargs):
                raise RuntimeError("kaputt")
        result = fe.apply(Kaputt(), "linux")
        self.assertFalse(result["aktiv"])

    def test_start_text(self):
        aktiv = fe.apply({"XDG_SESSION_TYPE": "wayland", "XMODIFIERS": "@im=ibus"}, "linux")
        self.assertEqual(fe.start_text(aktiv),
                         "Sitzung wayland | XMODIFIERS @im=ibus -> @im=none | "
                         "Eingabe-Umgehung aktiv (Wayland)")
        fe._reset_for_tests()
        x11 = fe.apply({"XDG_SESSION_TYPE": "x11", "XMODIFIERS": "@im=ibus"}, "linux")
        self.assertEqual(fe.start_text(x11), "Sitzung x11 | XMODIFIERS @im=ibus -> @im=none | "
                         "Eingabe-Umgehung aktiv (X11)")
        fe._reset_for_tests()
        x11_aus = fe.apply({"XDG_SESSION_TYPE": "x11", "XMODIFIERS": "@im=ibus",
                            "FISI_XIM": "1"}, "linux")
        self.assertEqual(fe.start_text(x11_aus), "Sitzung x11 | XMODIFIERS @im=ibus | "
                         "Eingabe-Umgehung nein (FISI_XIM=1)")
        fe._reset_for_tests()
        ohne_sitzung = fe.apply({"DISPLAY": ":0", "XMODIFIERS": "@im=ibus"}, "linux")
        self.assertEqual(fe.start_text(ohne_sitzung), "Sitzung ? | XMODIFIERS @im=ibus -> "
                         "@im=none | Eingabe-Umgehung aktiv (X11)")
        fe._reset_for_tests()
        ohne = fe.apply({"XDG_SESSION_TYPE": "wayland", "XMODIFIERS": "@im=fcitx"}, "linux")
        self.assertEqual(fe.start_text(ohne), "Sitzung wayland | XMODIFIERS @im=fcitx | "
                         "Eingabe-Umgehung nein (kein IBus)")
        fe._reset_for_tests()
        win = fe.apply({}, "win32")
        self.assertEqual(fe.start_text(win), "Eingabe-Umgehung nein (kein Linux)")
        fe._reset_for_tests()
        self.assertEqual(fe.start_text(), "")

    def test_neuer_prozess_prueft_selbst_neu(self):
        """Neustart nach Update: der neue Prozess erbt die Umgebung des alten
        (mit "@im=none") und entscheidet selbst - er aendert nichts mehr und
        nennt den Grund; mit FISI_XIM=1 bleibt es beim Schalter."""
        code = ("import sys, json; sys.path.insert(0, %r); import fisi_eingabe as fe;"
                "r = fe.apply(platform='linux'); print(json.dumps(r))" % HERE)
        import json
        env = dict(os.environ, XDG_SESSION_TYPE="wayland", XMODIFIERS="@im=ibus")
        env.pop("FISI_XIM", None)
        first = json.loads(subprocess.run([sys.executable, "-c", code], env=env,
                                          capture_output=True, text=True,
                                          check=True).stdout)
        self.assertTrue(first["aktiv"])
        env["XMODIFIERS"] = first["nachher"]          # so erbt es der Neustart
        second = json.loads(subprocess.run([sys.executable, "-c", code], env=env,
                                           capture_output=True, text=True,
                                           check=True).stdout)
        self.assertFalse(second["aktiv"])
        self.assertEqual(second["vorher"], "@im=none")
        self.assertEqual(second["grund"], "schon @im=none (geerbt oder von Hand)")
        self.assertEqual(fe.start_text(second),
                         "Sitzung wayland | XMODIFIERS @im=none | Eingabe-Umgehung "
                         "nein (schon @im=none (geerbt oder von Hand))")

    def test_start_py_setzt_vor_dem_ersten_fenster(self):
        """start.py ruft apply() als Erstes auf (vor tkinter und fail())."""
        with open(os.path.join(HERE, "start.py"), encoding="utf-8") as handle:
            text = handle.read()
        body = text.split("def main():", 1)[1]
        self.assertLess(body.index("fisi_eingabe.apply()"), body.index("import tkinter"))
        self.assertLess(body.index("fisi_eingabe.apply()"), body.index("\n        fail("))
        with open(os.path.join(HERE, "app_gui.py"), encoding="utf-8") as handle:
            text = handle.read()
        body = text.split("\ndef main():", 1)[1]
        self.assertLess(body.index("fisi_eingabe.apply()"), body.index("ctk.CTk("))
        self.assertLess(body.index("fisi_eingabe.apply()"), body.index("fhg.setup("))


# ============================================================================
#  X2 - Startzeilen
# ============================================================================

class StartzeileTest(_Frisch):

    def setUp(self):
        super().setUp()
        self.folder = tempfile.mkdtemp(prefix="fisi_eingabe_")

    def tearDown(self):
        shutil.rmtree(self.folder, ignore_errors=True)
        super().tearDown()

    def _haenger_start(self, env):
        code = textwrap.dedent("""
            import sys
            sys.path.insert(0, %r)
            import fisi_eingabe, fisi_haenger as fhg
            info = fisi_eingabe.apply(platform="linux")
            fhg.setup("9.9-test", folder=%r, extra=fisi_eingabe.start_text(info))
        """ % (HERE, self.folder))
        subprocess.run([sys.executable, "-c", code], env=env, check=True, timeout=60)
        with open(os.path.join(self.folder, fhg.LOG_NAME), encoding="utf-8") as handle:
            return handle.read()

    def test_haenger_log_umgehung_aktiv(self):
        env = dict(os.environ, XDG_SESSION_TYPE="wayland", XMODIFIERS="@im=ibus")
        env.pop("FISI_XIM", None)
        text = self._haenger_start(env)
        self.assertRegex(text, r"=== \d{4}-\d\d-\d\d \d\d:\d\d:\d\d \| Start \| Version "
                               r"9\.9-test \| linux \| pid \d+ \| Sitzung wayland \| "
                               r"XMODIFIERS @im=ibus -> @im=none \| Eingabe-Umgehung aktiv "
                               r"\(Wayland\) ===")

    def test_haenger_log_umgehung_aktiv_x11(self):
        env = dict(os.environ, XDG_SESSION_TYPE="x11", XMODIFIERS="@im=ibus")
        env.pop("FISI_XIM", None)
        env.pop("WAYLAND_DISPLAY", None)
        text = self._haenger_start(env)
        self.assertIn("| Sitzung x11 | XMODIFIERS @im=ibus -> @im=none | "
                      "Eingabe-Umgehung aktiv (X11) ===", text)

    def test_haenger_log_umgehung_nein(self):
        env = dict(os.environ, XDG_SESSION_TYPE="wayland", XMODIFIERS="@im=ibus",
                   FISI_XIM="1")
        text = self._haenger_start(env)
        self.assertIn("| Sitzung wayland | XMODIFIERS @im=ibus | Eingabe-Umgehung nein "
                      "(FISI_XIM=1) ===", text)

    def test_messdatei_startzeile(self):
        path = os.path.join(self.folder, "leistungsmessung.csv")
        rec = fle.Recorder("9.9", "PC", path=path, toolkit="6.0.0")
        rec.active = True
        rec.task_source = lambda: "bereit"
        rec.start_task = fe.MESS_TASK
        rec.record(fle.EVENT_START)
        rec.record("seite", von="a", nach="b", dauer_ms=5)
        rec.flush()
        with open(path, encoding="utf-8") as handle:
            lines = handle.read().splitlines()
        self.assertEqual(lines[0].split(";"), list(fle.COLUMNS))   # Format unveraendert
        start = dict(zip(fle.COLUMNS, lines[1].split(";")))
        page = dict(zip(fle.COLUMNS, lines[2].split(";")))
        self.assertEqual(start["vorgang"], "eingabe-umgehung")
        self.assertEqual(page["vorgang"], "bereit")

    def test_messdatei_ohne_umgehung_wie_bisher(self):
        path = os.path.join(self.folder, "leistungsmessung.csv")
        rec = fle.Recorder("9.9", "Handy", path=path)
        rec.active = True
        rec.record(fle.EVENT_START)
        rec.flush()
        with open(path, encoding="utf-8") as handle:
            start = dict(zip(fle.COLUMNS, handle.read().splitlines()[1].split(";")))
        self.assertEqual(start["vorgang"], "")


# ============================================================================
#  K1 - Befehl
# ============================================================================

class BefehlTest(unittest.TestCase):

    def test_ueberall_derselbe_befehl(self):
        self.assertEqual(fhg.KILL_COMMAND, "kill -USR1 $(pgrep -i -x -o fisi-lernplattf)")
        with open(os.path.join(HERE, "fisi_hilfe.py"), encoding="utf-8") as handle:
            hilfe = handle.read()
        with open(os.path.join(HERE, "LIESMICH.txt"), encoding="utf-8") as handle:
            liesmich = handle.read()
        for name, text in (("fisi_hilfe.py", hilfe), ("LIESMICH.txt", liesmich)):
            self.assertTrue(fhg.KILL_COMMAND in text, name)
            self.assertFalse("pgrep -x FISI-Lernplattf" in text, name)
            self.assertFalse("| head -1" in text, name)

    def test_kein_alter_befehl_im_programm(self):
        for name in os.listdir(HERE):
            if name.endswith(".py") and name != "test_eingabe.py":
                with open(os.path.join(HERE, name), encoding="utf-8") as handle:
                    self.assertNotIn("pgrep -x FISI-Lernplattf", handle.read(), name)

    def test_liesmich_erklaert_schalter(self):
        with open(os.path.join(HERE, "LIESMICH.txt"), encoding="utf-8") as handle:
            text = handle.read()
        self.assertIn("FISI_XIM=1 fisi-lernplattform", text)
        self.assertRegex(text, r"Programme, die das Programm\s+selbst")


# ============================================================================
#  K3 - Vorladen
# ============================================================================

@unittest.skipUnless(HAS_TK, "braucht Tk mit Display")
class VorladenTest(unittest.TestCase):

    def setUp(self):
        import tkinter
        self._saved = dict(fhg._state)
        fhg._state.update(vorgang=fhg.IDLE, zuletzt=None)
        self.root = tkinter.Tk()
        import app_gui
        self.app_gui = app_gui
        self.pre = app_gui.ViewPreloader.__new__(app_gui.ViewPreloader)
        self.pre.root = self.root

    def tearDown(self):
        self.root.destroy()
        fhg._state.clear()
        fhg._state.update(self._saved)

    def test_vorgang_bleibt_bis_nach_der_leerlauf_runde(self):
        seen = []
        # ein Leerlauf-Auftrag, der beim Bau entstand (Groessen, Zeichnen)
        self.root.after_idle(lambda: seen.append(fhg.current()[1]))
        before = fhg.vorgang("vorladen:settings")
        self.pre._release_task("vorladen:settings", before)
        self.assertEqual(fhg.current()[1], "vorladen:settings")   # noch nicht zurueck
        self.root.update_idletasks()
        self.assertEqual(seen, ["vorladen:settings"])
        self.assertEqual(fhg.current()[1], fhg.IDLE)

    def test_anderer_vorgang_bleibt_stehen(self):
        before = fhg.vorgang("vorladen:calc")
        self.pre._release_task("vorladen:calc", before)
        fhg.vorgang("darstellung")
        self.root.update_idletasks()
        self.assertEqual(fhg.current()[1], "darstellung")

    def test_vorladen_start_bis_zum_ersten_schritt(self):
        self.assertTrue(fhg._known(self.app_gui.PRELOAD_WAIT_TASK))
        pre = self.pre
        pre.app = type("App", (), {"slot_chosen": False, "_closing": True})()
        pre.job = None
        pre.start(delay=10)
        self.assertEqual(fhg.current()[1], "vorladen:start")
        pre._step()                           # _closing -> tut nichts weiter
        self.assertEqual(fhg.current()[1], fhg.IDLE)

    def test_begrenzungen_unveraendert(self):
        self.assertEqual(fhg.MAX_LINES, 10)
        self.assertEqual(fhg.MAX_AUTO_DUMPS, 3)
        self.assertEqual((fhg.BLOCK_SECONDS, fhg.KNOWN_SECONDS, fhg.DUMP_AFTER), (5, 30, 30))


# ============================================================================
#  Nachstellung mit IBus (nur wenn ibus-daemon, ibus-x11 und Display da sind)
# ============================================================================

IBUS_X11 = next((p for p in ("/usr/libexec/ibus-x11", "/usr/lib/ibus/ibus-x11")
                 if os.path.exists(p)), None)
HAS_IBUS = bool(HAS_TK and shutil.which("ibus-daemon") and IBUS_X11
                and shutil.which("dbus-launch") and os.environ.get("FISI_TEST_IBUS") == "1")

FENSTER = textwrap.dedent("""
    import os, sys, time, tkinter
    sys.path.insert(0, %(here)r)
    if %(umgehung)r:
        import fisi_eingabe
        fisi_eingabe.apply()
    root = tkinter.Tk()
    entry = tkinter.Entry(root); entry.pack(); entry.focus_force(); root.update()
    print("bereit", flush=True)
    sys.stdin.readline()
    for _ in range(3):
        top = tkinter.Toplevel(root); field = tkinter.Entry(top); field.pack()
        field.focus_force(); root.update(); top.destroy(); root.update()
    print("fertig", flush=True)
""")


@unittest.skipUnless(HAS_IBUS, "braucht IBus, dbus-launch und Display (FISI_TEST_IBUS=1)")
class NachstellungTest(unittest.TestCase):
    """ibus-daemon wird angehalten (SIGSTOP): ibus-x11 bekommt keine Antwort
    mehr auf CreateInputContext, Tk wartet in XCreateIC."""

    def _lauf(self, umgehung):
        env = dict(os.environ, XDG_SESSION_TYPE="wayland", XMODIFIERS="@im=ibus")
        env.pop("FISI_XIM", None)
        out = subprocess.run(["dbus-launch", "--sh-syntax"], capture_output=True,
                             text=True, check=True).stdout
        for key, value in re.findall(r"(DBUS_SESSION_BUS_\w+)='?([^';]+)'?;", out):
            env[key] = value
        daemon = subprocess.Popen(["ibus-daemon", "--xim", "--replace"], env=env,
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        proc = None
        try:
            time.sleep(3)
            proc = subprocess.Popen([sys.executable, "-c", FENSTER % {
                "here": HERE, "umgehung": umgehung}], env=env, stdin=subprocess.PIPE,
                stdout=subprocess.PIPE, text=True)
            self.assertEqual(proc.stdout.readline().strip(), "bereit")
            os.kill(daemon.pid, signal.SIGSTOP)
            proc.stdin.write("\n")
            proc.stdin.flush()
            try:
                proc.wait(timeout=20)
                done = True
            except subprocess.TimeoutExpired:
                done = False
            return done
        finally:
            if proc is not None and proc.poll() is None:
                proc.kill()
            os.kill(daemon.pid, signal.SIGCONT)
            daemon.terminate()
            subprocess.run(["pkill", "-f", "ibus-x11"], check=False)
            os.kill(int(env["DBUS_SESSION_BUS_PID"]), signal.SIGTERM)

    def test_ohne_umgehung_haengt_tk(self):
        self.assertFalse(self._lauf(False))

    def test_mit_umgehung_kein_haenger(self):
        self.assertTrue(self._lauf(True))


if __name__ == "__main__":
    unittest.main()
