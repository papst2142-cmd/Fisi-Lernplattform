#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests fuer die Haenger-Diagnose (fisi_haenger.py, ab 0.59.2).

  * Waechter: Zeile in fehler.log bei blockiertem Hauptfaden (ab 5 s, bei
    bekannten langen Vorgaengen ab 30 s), "wieder frei", keine Zeile im
    Normalfall, hoechstens MAX_LINES je Sitzung, schweigt beim Schliessen
  * haenger.log: Kopfzeile, Kuerzen beim Start, Zustand und Ende fuer den
    Problembericht
  * echte Stapel (eigener Prozess, Hauptfaden in Tcl blockiert): erster
    Stapel nach DUMP_AFTER, zweiter nach weiteren DUMP_AGAIN (setzt der
    Waechter), danach keiner mehr; SIGUSR1 (Linux); dump_on_close
  * Fehler bleiben still (Datei nicht zu oeffnen, kaputte Datei, Herzschlag)
  * Leistungsmessung: Ereignis "blockiert" mit Seite und Vorgang

Start:  python test_haenger.py   (die Stapel-Tests brauchen Tk und ein Display)
"""

import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest
from types import SimpleNamespace

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import fisi_haenger as fhg  # noqa: E402


def _display_ok():
    try:
        import tkinter
        root = tkinter.Tk()
        root.destroy()
        return True
    except Exception:  # noqa: BLE001
        return False


HAS_TK = _display_ok()


class _Ordner(unittest.TestCase):
    """Eigener Datenordner (FISI_DB_PATH) und frischer Zustand je Test."""

    def setUp(self):
        self.folder = tempfile.mkdtemp(prefix="fisi_haenger_")
        self._old_env = os.environ.get("FISI_DB_PATH")
        os.environ["FISI_DB_PATH"] = os.path.join(self.folder, "test.db")
        self._saved = dict(fhg._state)
        fhg._state.update(beat=None, armed=None, armed_for=0, auto_dumps=0, seite="",
                          vorgang=fhg.IDLE, closing=None, lines=0, block=None,
                          zuletzt=None)

    def tearDown(self):
        fhg._state.clear()
        fhg._state.update(self._saved)
        if self._old_env is None:
            os.environ.pop("FISI_DB_PATH", None)
        else:
            os.environ["FISI_DB_PATH"] = self._old_env
        shutil.rmtree(self.folder, ignore_errors=True)

    def error_log(self):
        path = os.path.join(self.folder, "fehler.log")
        if not os.path.exists(path):
            return ""
        with open(path, encoding="utf-8") as handle:
            return handle.read()


# ============================================================================
#  WAECHTER (ohne echte Zeit, check(now=...))
# ============================================================================

class WaechterTest(_Ordner):

    def test_normalfall_keine_zeile(self):
        start = 1000.0
        for step in range(40):
            fhg._state["beat"] = start + step * 0.5
            self.assertIsNone(fhg.check(now=start + step * 0.5 + 0.4))
        self.assertEqual(self.error_log(), "")

    def test_vor_dem_ersten_herzschlag_still(self):
        # Programmstart (Fenster wird noch gebaut): kein Herzschlag, keine Zeile
        self.assertIsNone(fhg.check(now=99999.0))
        self.assertEqual(self.error_log(), "")

    def test_blockiert_ab_5_s_und_wieder_frei(self):
        fhg.seite("dashboard")
        fhg._state["beat"] = 1000.0
        self.assertIsNone(fhg.check(now=1004.0))
        self.assertEqual(fhg.check(now=1005.5), "blockiert")
        self.assertIsNone(fhg.check(now=1007.0))     # nur eine Zeile je Blockade
        log = self.error_log()
        self.assertEqual(log.count("Hauptfaden seit"), 1)
        self.assertIn("Hauptfaden seit 5,5 s ohne Rückruf (Seite: dashboard, Vorgang: "
                      "bereit)", log)
        if os.path.isdir("/proc/self/task"):
            self.assertIn("Wartepunkte: ", log)
        fhg._state["beat"] = 1012.0
        self.assertEqual(fhg.check(now=1012.5), "frei")
        self.assertIn("Hauptfaden wieder frei nach 12,5 s", self.error_log())

    def test_kurze_blockade_keine_zeile(self):
        fhg._state["beat"] = 1000.0
        self.assertIsNone(fhg.check(now=1003.0))
        fhg._state["beat"] = 1004.0
        self.assertIsNone(fhg.check(now=1004.2))
        self.assertEqual(self.error_log(), "")

    def test_bekannter_vorgang_erst_ab_30_s(self):
        for task in ("darstellung", "schrift", "vorladen:settings", "seite:settings",
                     "abgleich"):
            fhg._state.update(beat=1000.0, block=None, lines=0)
            fhg.vorgang(task)
            self.assertIsNone(fhg.check(now=1017.0), task)    # VM: 10-17 s normal
            self.assertEqual(fhg.check(now=1030.5), "blockiert", task)
            fhg.vorgang(fhg.IDLE)
            fhg._state["beat"] = 1031.0
            self.assertEqual(fhg.check(now=1031.1), "frei", task)
        self.assertEqual(self.error_log().count("Hauptfaden seit"), 5)
        self.assertIn("Vorgang: vorladen:settings", self.error_log())

    def test_hoechstens_10_zeilen_je_sitzung(self):
        now = 1000.0
        for _ in range(14):
            fhg._state["beat"] = now
            fhg.check(now=now + 6)
            fhg._state["beat"] = now + 7
            fhg.check(now=now + 7.1)
            now += 10
        log = self.error_log()
        self.assertEqual(log.count("Hauptfaden seit"), fhg.MAX_LINES)
        self.assertEqual(log.count("Weitere Blockaden in dieser Sitzung"), 1)
        self.assertEqual(log.count("wieder frei"), fhg.MAX_LINES)

    def test_schweigt_beim_schliessen(self):
        fhg.set_closing(lambda: True)
        fhg._state["beat"] = 1000.0
        self.assertIsNone(fhg.check(now=1060.0))
        self.assertEqual(self.error_log(), "")

    def test_letzter_vorgang_nach_dem_ende(self):
        fhg.vorgang("darstellung")
        fhg.vorgang(fhg.IDLE)
        self.assertEqual(fhg.recent(time.monotonic() - 5), "darstellung")
        self.assertEqual(fhg.recent(time.monotonic() + 5), fhg.IDLE)

    def test_verspaetung_des_herzschlags(self):
        self.assertEqual(fhg.beat(now=100.0), 0.0)
        self.assertAlmostEqual(fhg.beat(now=100.5), 0.0)
        self.assertAlmostEqual(fhg.beat(now=104.0), 3.0)


# ============================================================================
#  HAENGER.LOG
# ============================================================================

class DateiTest(_Ordner):

    def test_kuerzen_beim_start(self):
        path = fhg.log_path()
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("ANFANG\n" + ("x" * 99 + "\n") * 6000 + "ENDE\n")
        self.assertGreater(os.path.getsize(path), fhg.LOG_MAX)
        fhg._trim(path)
        self.assertLessEqual(os.path.getsize(path), fhg.LOG_KEEP)
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
        self.assertNotIn("ANFANG", text)
        self.assertTrue(text.startswith("x"))
        self.assertIn("ENDE", text)

    def test_zustand_und_ende(self):
        path = fhg.log_path()
        self.assertEqual(fhg.state_text(path), fhg.STATE_NONE)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("=== 2026-10-07 08:00:00 | Start | Version 0.59.2 ===\n")
        self.assertEqual(fhg.state_text(path), fhg.STATE_NONE)   # nur Kopfzeile
        with open(path, "a", encoding="utf-8") as handle:
            handle.write('Thread 0x1 (most recent call first):\n  File "a.py", line 1 in f\n')
        self.assertTrue(fhg.state_text(path).startswith("haenger.log: "))
        text, cut = fhg.tail(path)
        self.assertIn("line 1 in f", text)
        self.assertFalse(cut)

    def test_datei_nicht_zu_oeffnen_bleibt_still(self):
        blocker = os.path.join(self.folder, "ist_eine_datei")
        open(blocker, "w").close()
        code = textwrap.dedent("""
            import sys
            sys.path.insert(0, %r)
            import fisi_haenger as fhg
            ok = fhg.setup("0.59.2", folder=%r)
            fhg._state["beat"] = 1.0
            fhg.beat(); fhg.check(); fhg.dump_on_close(1)
            print("ok" if not ok and not fhg.enabled() else "falsch")
        """) % (HERE, os.path.join(blocker, "unter"))
        result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                                timeout=30, env=dict(os.environ))
        self.assertEqual(result.stdout.strip(), "ok", result.stderr)
        self.assertEqual(result.stderr, "")

    def test_kaputte_datei_bleibt_still(self):
        saved = fhg._log
        broken = open(os.path.join(self.folder, "x.log"), "w")
        broken.close()
        fhg._log = broken
        try:
            fhg._write("test")
            fhg.dump_on_close(1)
            fhg._arm(30)
        finally:
            fhg._log = saved
            import faulthandler
            faulthandler.cancel_dump_traceback_later()


# ============================================================================
#  ECHTE STAPEL (eigener Prozess)
# ============================================================================

BLOCKED = textwrap.dedent("""
    import os, sys, time, signal, tkinter
    sys.path.insert(0, %(here)r)
    import fisi_haenger as fhg
    fhg.DUMP_AFTER, fhg.DUMP_AGAIN, fhg.ARM_SECONDS = %(after)s, %(again)s, 0.5
    fhg.MAX_AUTO_DUMPS = %(max)d
    fhg.setup("9.9-test", folder=%(folder)r)
    root = tkinter.Tk()
    def beat():
        fhg.beat()
        root.after(fhg.BEAT_MS, beat)
    def block():
        fhg.vorgang("darstellung")
        root.tk.call("after", %(block_ms)d)      # Hauptfaden steht in Tcl (C)
        fhg.vorgang(fhg.IDLE)
        root.after(1500, root.destroy)
    root.after(fhg.BEAT_MS, beat)
    root.after(1200, block)
    root.mainloop()
""")


@unittest.skipUnless(HAS_TK, "braucht Tk mit Display")
class StapelTest(_Ordner):

    def _run(self, after, again, block_ms, maximum=3):
        code = BLOCKED % {"here": HERE, "folder": self.folder, "after": after,
                          "again": again, "block_ms": block_ms, "max": maximum}
        result = subprocess.run([sys.executable, "-c", code], capture_output=True,
                                text=True, timeout=120)
        self.assertEqual(result.returncode, 0, result.stderr)
        with open(os.path.join(self.folder, fhg.LOG_NAME), encoding="utf-8") as handle:
            return handle.read()

    def test_erster_und_zweiter_stapel_dann_keiner(self):
        # verkleinert: 3 s / weitere 4 s; Blockade 14 s -> genau 2 Stapel
        text = self._run(3, 4, 14000)
        self.assertIn("Start | Version 9.9-test", text)
        self.assertEqual(text.count("Timeout (0:00:03)!"), 1)
        self.assertEqual(text.count("Timeout (0:00:04)!"), 1)
        self.assertIn("Stapel 1 geschrieben", text)
        self.assertIn("Stapel 2 geschrieben", text)
        self.assertNotIn("Stapel 3", text)
        # der Stapel zeigt die blockierte Stelle im Hauptfaden
        self.assertIn("in block", text)
        self.assertIn("Vorgang: darstellung", text)
        self.assertIn("Hauptfaden wieder frei", text)

    def test_hoechstens_max_stapel_je_sitzung(self):
        text = self._run(2, 2, 12000, maximum=1)
        self.assertEqual(text.count("Timeout ("), 1)

    def test_normalfall_kein_stapel(self):
        text = self._run(3, 4, 500)
        self.assertNotIn("Timeout", text)
        self.assertEqual(self.error_log(), "")

    @unittest.skipUnless(hasattr(__import__("signal"), "SIGUSR1"), "kein SIGUSR1")
    def test_sigusr1_schreibt_stapel_und_beendet_nicht(self):
        code = textwrap.dedent("""
            import sys, time
            sys.path.insert(0, %r)
            import fisi_haenger as fhg
            fhg.setup("9.9-test", folder=%r)
            print("bereit", flush=True)
            time.sleep(3)
            print("lebt", flush=True)
        """) % (HERE, self.folder)
        proc = subprocess.Popen([sys.executable, "-c", code], stdout=subprocess.PIPE,
                                text=True)
        self.assertEqual(proc.stdout.readline().strip(), "bereit")
        import signal
        os.kill(proc.pid, signal.SIGUSR1)
        self.assertEqual(proc.stdout.readline().strip(), "lebt")
        proc.wait(timeout=20)
        proc.stdout.close()
        self.assertEqual(proc.returncode, 0)
        with open(os.path.join(self.folder, fhg.LOG_NAME), encoding="utf-8") as handle:
            text = handle.read()
        self.assertIn("most recent call first", text)
        self.assertIn("in <module>", text)

    def test_dump_on_close(self):
        code = textwrap.dedent("""
            import sys, time
            sys.path.insert(0, %r)
            import fisi_haenger as fhg
            fhg.setup("9.9-test", folder=%r)
            fhg.dump_on_close(1)
            time.sleep(2.5)      # Prozess lebt nach dem Schliessen weiter
        """) % (HERE, self.folder)
        subprocess.run([sys.executable, "-c", code], timeout=30, check=True)
        with open(os.path.join(self.folder, fhg.LOG_NAME), encoding="utf-8") as handle:
            text = handle.read()
        self.assertIn("| schliessen ===", text)
        self.assertIn("Timeout (0:00:01)!", text)

    def test_schliessen_schnell_kein_stapel(self):
        code = textwrap.dedent("""
            import sys
            sys.path.insert(0, %r)
            import fisi_haenger as fhg
            fhg.setup("9.9-test", folder=%r)
            fhg.dump_on_close(5)
        """) % (HERE, self.folder)
        begin = time.monotonic()
        subprocess.run([sys.executable, "-c", code], timeout=30, check=True)
        self.assertLess(time.monotonic() - begin, 4)
        with open(os.path.join(self.folder, fhg.LOG_NAME), encoding="utf-8") as handle:
            self.assertNotIn("Timeout", handle.read())


# ============================================================================
#  PROGRAMM: HERZSCHLAG UND LEISTUNGSMESSUNG
# ============================================================================

@unittest.skipUnless(HAS_TK, "braucht Tk mit Display")
class ProgrammTest(_Ordner):

    def test_herzschlag_zeigt_nie_einen_fehler(self):
        import app_gui
        planned = []
        fake = SimpleNamespace(
            _closing=False,
            root=SimpleNamespace(after=lambda ms, func: planned.append(ms)),
            perf=SimpleNamespace(blocked=lambda seconds: 1 / 0))
        fake._heartbeat = lambda: None
        saved = fhg.beat
        fhg.beat = lambda: 5.0      # Verspaetung -> perf.blocked wirft
        try:
            app_gui.FISIApp._heartbeat(fake)
            fhg.beat = lambda: 1 / 0
            app_gui.FISIApp._heartbeat(fake)
        finally:
            fhg.beat = saved
        self.assertEqual(planned, [fhg.BEAT_MS, fhg.BEAT_MS])
        fake._closing = True
        app_gui.FISIApp._heartbeat(fake)
        self.assertEqual(len(planned), 2)      # nach dem Schliessen nicht neu planen

    def test_blockiert_in_der_messdatei(self):
        import app_gui
        import fisi_leistung as fle
        rec = fle.Recorder("0.59.2", "PC", path=os.path.join(self.folder, "m.csv"))
        rec.active = True
        fhg.seite("settings")
        fhg.vorgang("darstellung")
        fhg.vorgang(fhg.IDLE)
        app_gui.PerfMonitor.blocked(SimpleNamespace(rec=rec), 3.2)
        rec.flush()
        with open(rec.path, encoding="utf-8") as handle:
            header, row = handle.read().splitlines()
        values = dict(zip(header.split(";"), row.split(";")))
        self.assertEqual(values["ereignis"], fle.EVENT_BLOCKED)
        self.assertEqual(values["nach"], "settings")
        self.assertEqual(values["dauer_ms"], "3200,0")
        self.assertEqual(values["vorgang"], "darstellung")


if __name__ == "__main__":
    unittest.main(verbosity=2)
