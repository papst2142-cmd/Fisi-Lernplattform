#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests fuer die Sperre gegen Mehrfachstart (fisi_einzelstart, ab 0.59.1).

Jeder Start laeuft als eigener Prozess (die Sperre gilt je Prozess), mit
einem eigenen Datenordner (FISI_DB_PATH):
  * erster Start bekommt die Sperre, zweiter Start mit Antwort "da" endet
  * Antwort "endet" (Programm schliesst/Update) -> zweiter Start wartet auf
    die Sperre und startet dann selbst
  * keine Antwort -> nach der Wartezeit Start ohne Sperre (wie 0.59) und
    Eintrag in fehler.log
  * nach kill -9 des ersten Starts startet der naechste normal
  * Fehler beim Anlegen der Sperre verhindern den Start nie
  * main(): FISI_SELFTEST nimmt die Sperre aus, ein "da" beendet main still
  * mit Display (Linux mit Fenstermanager, Windows): minimiertes Fenster
    kommt beim zweiten Start zurueck; Linux: das echte Programm oeffnet beim
    zweiten Start kein zweites Fenster

Start:  python test_einzelstart.py   (Fenster-Tests brauchen ein Display)
"""

import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import fisi_einzelstart as fe  # noqa: E402

BEENDET = 5     # Exit-Code der Hilfsprozesse, wenn claim() False liefert


def _display_ok():
    try:
        import tkinter
        root = tkinter.Tk()
        root.destroy()
        return True
    except Exception:  # noqa: BLE001
        return False


HAS_DISPLAY = sys.platform.startswith("linux") and _display_ok()
# Windows hat immer eine Anzeige (auch der CI-Rechner)
HAS_WINDOW = (HAS_DISPLAY or sys.platform == "win32") and _display_ok()

# Haelt die Sperre wie das echte Programm: claim() und dann je nach Modus
# antworten (Start-Thread = "da"), "endet" antworten oder gar nicht.
HOLDER = textwrap.dedent("""
    import os, sys, time
    sys.path.insert(0, %(here)r)
    import fisi_einzelstart as fe
    folder, mode, seconds = sys.argv[1], sys.argv[2], float(sys.argv[3])
    if mode == "still":
        handle = fe._try_lock(folder)
    else:
        assert fe.claim(folder)
    print("bereit", flush=True)
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        if mode == "endet":
            if fe._startup_answering:
                fe._startup_answering[1].set()
            fe.answer_signals(folder, closing=True)
        time.sleep(0.05)
""")

STARTER = textwrap.dedent("""
    import sys
    sys.path.insert(0, %(here)r)
    import fisi_einzelstart as fe
    ok = fe.claim(sys.argv[1], answer_seconds=float(sys.argv[2]),
                  lock_seconds=float(sys.argv[3]))
    print("sperre" if fe._lock_handle else "ohne", flush=True)
    sys.exit(0 if ok else %(beendet)d)
""")


class _Ordner(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.mkdtemp(prefix="fisi_einzel_")
        self.env = dict(os.environ, FISI_DB_PATH=os.path.join(self.folder, "test.db"))
        self.env.pop("FISI_SELFTEST", None)
        self.procs = []

    def tearDown(self):
        for proc in self.procs:
            if proc.poll() is None:
                proc.kill()
            proc.wait()
            for stream in (proc.stdout, proc.stderr):
                if stream:
                    stream.close()
        shutil.rmtree(self.folder, ignore_errors=True)

    def _holder(self, mode, seconds=20):
        proc = subprocess.Popen([sys.executable, "-c", HOLDER % {"here": HERE},
                                 self.folder, mode, str(seconds)],
                                env=self.env, stdout=subprocess.PIPE, text=True)
        self.procs.append(proc)
        self.assertEqual(proc.stdout.readline().strip(), "bereit")
        return proc

    def _start(self, answer=1.0, lock=2.0):
        begin = time.monotonic()
        result = subprocess.run([sys.executable, "-c",
                                 STARTER % {"here": HERE, "beendet": BEENDET},
                                 self.folder, str(answer), str(lock)],
                                env=self.env, capture_output=True, text=True, timeout=60)
        return result.returncode, result.stdout.strip(), time.monotonic() - begin

    def _log(self):
        path = os.path.join(self.folder, "fehler.log")
        if not os.path.exists(path):
            return ""
        with open(path, encoding="utf-8") as handle:
            return handle.read()


@unittest.skipUnless(fe.supported(), "nur Linux und Windows")
class SperreTest(_Ordner):
    def test_erster_start_bekommt_sperre(self):
        code, out, _ = self._start()
        self.assertEqual((code, out), (0, "sperre"))
        self.assertTrue(os.path.exists(os.path.join(self.folder, fe.LOCK_FILE)))

    def test_zweiter_start_endet_still_bei_da(self):
        self._holder("da")
        code, out, _ = self._start(answer=1.0)
        self.assertEqual((code, out), (BEENDET, "ohne"))
        self.assertEqual(self._log(), "")
        # keine Signal- oder Antwortdateien bleiben liegen
        self.assertEqual(sorted(os.listdir(self.folder)), [fe.LOCK_FILE])

    def test_zwei_gleichzeitige_zweitstarts(self):
        self._holder("da")
        starter = STARTER % {"here": HERE, "beendet": BEENDET}
        procs = [subprocess.Popen([sys.executable, "-c", starter, self.folder, "1", "2"],
                                  env=self.env, stdout=subprocess.DEVNULL)
                 for _ in range(2)]
        self.assertEqual([proc.wait(timeout=60) for proc in procs], [BEENDET, BEENDET])

    def test_endet_wartet_auf_sperre_und_startet(self):
        self._holder("endet", seconds=1.5)
        code, out, took = self._start(answer=1.0, lock=10.0)
        self.assertEqual((code, out), (0, "sperre"))
        self.assertLess(took, 10)

    def test_da_aber_programm_endet_gleich(self):
        # Sicherheitsnetz fuer das AppImage-Update: "da", dann wird die
        # Sperre innerhalb der Antwortzeit frei -> selbst starten
        self._holder("da", seconds=1.0)
        code, out, _ = self._start(answer=3.0)
        self.assertEqual((code, out), (0, "sperre"))

    def test_keine_antwort_startet_trotzdem(self):
        self._holder("still")
        code, out, took = self._start(answer=0.5, lock=1.0)
        self.assertEqual((code, out), (0, "ohne"))
        self.assertGreaterEqual(took, 1.5)
        self.assertIn("Mehrfachstart", self._log())

    def test_start_nach_kill_9(self):
        # kill() = SIGKILL unter Linux, TerminateProcess unter Windows
        holder = self._holder("da")
        holder.kill()
        holder.wait()
        self.assertTrue(os.path.exists(os.path.join(self.folder, fe.LOCK_FILE)))
        code, out, _ = self._start()
        self.assertEqual((code, out), (0, "sperre"))

    def test_fehler_verhindert_start_nie(self):
        missing = os.path.join(self.folder, "gibt", "es", "nicht")
        result = subprocess.run(
            [sys.executable, "-c", STARTER % {"here": HERE, "beendet": BEENDET},
             missing, "1", "1"], env=self.env, capture_output=True, text=True, timeout=30)
        self.assertEqual((result.returncode, result.stdout.strip()), (0, "ohne"))
        self.assertIn("Start ohne Sperre", self._log())


class AntwortTest(_Ordner):
    def _signal(self, token):
        open(os.path.join(self.folder, fe.PREFIX + token + fe.SIGNAL_SUFFIX), "w").close()

    def _answer(self, token):
        with open(fe._answer_path(self.folder, token), encoding="utf-8") as handle:
            return handle.read()

    def test_da_holt_nach_vorn(self):
        self._signal("1-1")
        self.assertTrue(fe.answer_signals(self.folder, closing=False))
        self.assertEqual(self._answer("1-1"), fe.ANSWER_HERE)

    def test_endet_beim_schliessen(self):
        self._signal("1-2")
        self._signal("1-3")
        self.assertFalse(fe.answer_signals(self.folder, closing=True))
        self.assertEqual(self._answer("1-2"), fe.ANSWER_ENDING)
        self.assertEqual(self._answer("1-3"), fe.ANSWER_ENDING)

    def test_ohne_signal_nichts(self):
        self.assertFalse(fe.answer_signals(self.folder, closing=False))
        self.assertEqual(os.listdir(self.folder), [])

    def test_alte_dateien_werden_aufgeraeumt(self):
        self._signal("alt")
        fe._write_answer(self.folder, "alt", "da")
        self._signal("neu")
        fe._clean_stale(self.folder, now=time.time() + fe.STALE_SECONDS / 2)
        self.assertEqual(len(os.listdir(self.folder)), 3)
        fe._clean_stale(self.folder, now=time.time() + fe.STALE_SECONDS + 5)
        self.assertEqual(os.listdir(self.folder), [])

    def test_plattformen(self):
        self.assertTrue(fe.supported("linux"))
        self.assertTrue(fe.supported("win32"))
        self.assertFalse(fe.supported("darwin"))


class MainTest(unittest.TestCase):
    """main() ohne Fenster: CTk wird durch eine Attrappe ersetzt, die main()
    an dieser Stelle abbricht."""

    class _Stop(Exception):
        pass

    def _run_main(self, selftest, claim_result):
        import app_gui
        calls = []
        saved = (fe.claim, fe.supported, app_gui.ctk.CTk, os.environ.get("FISI_SELFTEST"),
                 sys.excepthook)

        def fake_ctk(*_args, **_kwargs):
            raise self._Stop()
        fe.claim = lambda: calls.append("claim") or claim_result
        fe.supported = lambda platform=None: True
        app_gui.ctk.CTk = fake_ctk
        if selftest:
            os.environ["FISI_SELFTEST"] = "x.log"
        else:
            os.environ.pop("FISI_SELFTEST", None)
        try:
            app_gui.main()
            reached_window = False
        except self._Stop:
            reached_window = True
        finally:
            fe.claim, fe.supported, app_gui.ctk.CTk = saved[:3]
            if saved[3] is None:
                os.environ.pop("FISI_SELFTEST", None)
            else:
                os.environ["FISI_SELFTEST"] = saved[3]
            sys.excepthook = saved[4]
        return calls, reached_window

    def test_selftest_ohne_sperre(self):
        self.assertEqual(self._run_main(selftest=True, claim_result=False), ([], True))

    def test_da_beendet_main_ohne_fenster(self):
        self.assertEqual(self._run_main(selftest=False, claim_result=False), (["claim"], False))

    def test_sperre_bekommen_startet(self):
        self.assertEqual(self._run_main(selftest=False, claim_result=True), (["claim"], True))


# Fenster mit listen()/bring_to_front wie in app_gui.main
WINDOW = textwrap.dedent("""
    import sys, tkinter
    sys.path.insert(0, %(here)r)
    import fisi_einzelstart as fe
    folder = sys.argv[1]
    if not fe.claim(folder):
        sys.exit(%(beendet)d)
    root = tkinter.Tk(className="fisi-lernplattform")
    root.title("Einzelstart-Test")
    root.geometry("300x200")
    fe.listen(root, closing=lambda: False, bring_to_front=lambda: fe.bring_to_front(root))
    def report():
        print(root.wm_state(), flush=True)
        root.after(200, report)
    root.after(800, root.iconify)
    root.after(200, report)
    root.mainloop()
""")


@unittest.skipUnless(HAS_WINDOW, "braucht ein Display (Linux z.B. xvfb-run, Windows)")
class FensterTest(_Ordner):
    def _states(self, proc, until, seconds=15, required=True):
        end = time.monotonic() + seconds
        seen = []
        while time.monotonic() < end:
            line = proc.stdout.readline().strip()
            seen.append(line)
            if line == until:
                return seen
        if required:
            self.fail("Zustand %s nicht erreicht: %s" % (until, seen[-5:]))
        return None

    def test_minimiertes_fenster_kommt_nach_vorn(self):
        script = WINDOW % {"here": HERE, "beendet": BEENDET}
        first = subprocess.Popen([sys.executable, "-c", script, self.folder],
                                 env=self.env, stdout=subprocess.PIPE, text=True)
        self.procs.append(first)
        if not self._states(first, "iconic", seconds=6, required=False):
            self.skipTest("kein Fenstermanager: Minimieren wirkt nicht (z.B. openbox starten)")
        second = subprocess.run([sys.executable, "-c", script, self.folder],
                                env=self.env, capture_output=True, text=True, timeout=30)
        self.assertEqual(second.returncode, BEENDET, second.stderr)
        self._states(first, "normal", seconds=5)


def _windows_of_class(wm_class):
    """Sichtbare Fenster mit dieser WM_CLASS (xwininfo + xprop)."""
    tree = subprocess.run(["xwininfo", "-root", "-tree"], capture_output=True,
                          text=True).stdout
    found = []
    for line in tree.splitlines():
        parts = line.split()
        if not parts or not parts[0].startswith("0x"):
            continue
        props = subprocess.run(["xprop", "-id", parts[0], "WM_CLASS"], capture_output=True,
                               text=True).stdout
        if '"%s"' % wm_class in props:
            found.append(parts[0])
    return found


@unittest.skipUnless(HAS_DISPLAY and shutil.which("xwininfo") and shutil.which("xprop"),
                     "braucht Linux mit Display, xwininfo und xprop")
class ProgrammTest(_Ordner):
    """Das echte Programm: zweiter Start oeffnet kein zweites Fenster."""

    def test_zwei_starts_ein_fenster(self):
        first = subprocess.Popen([sys.executable, os.path.join(HERE, "app_gui.py")],
                                 env=self.env, stdout=subprocess.DEVNULL,
                                 stderr=subprocess.DEVNULL)
        self.procs.append(first)
        end = time.monotonic() + 60
        while time.monotonic() < end and not _windows_of_class("Fisi-lernplattform"):
            time.sleep(0.5)
        before = _windows_of_class("Fisi-lernplattform")
        self.assertTrue(before, "erstes Fenster erscheint nicht")
        second = subprocess.run([sys.executable, os.path.join(HERE, "app_gui.py")],
                                env=self.env, capture_output=True, text=True, timeout=90)
        self.assertEqual(second.returncode, 0, second.stderr[-2000:])
        self.assertEqual(_windows_of_class("Fisi-lernplattform"), before)
        self.assertIsNone(first.poll(), "erstes Programm darf weiterlaufen")
        self.assertEqual(self._log(), "")


if __name__ == "__main__":
    unittest.main(verbosity=2)
