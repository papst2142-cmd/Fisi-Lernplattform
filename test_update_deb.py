#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests fuer 0.63.2 (B-N-10): Neustart nach dem Update ueber das .deb-Paket.
  * Erfolg: pkexec apt-get install wie bisher, danach startet ein
    abgeloester Hilfsprozess (/bin/sh, eigene Sitzung) das Programm neu,
    sobald dieses beendet ist; install() liefert "beenden" (True) und
    denselben Hinweis wie beim AppImage.
  * Misserfolg (pkexec abgebrochen): wie bisher xdg-open und
    deb_cancel_message, kein Neustart.
  * Hilfsprozess laesst sich nicht starten: bisheriger Hinweis "Bitte das
    Programm schliessen und neu starten", nicht beenden.
  * Der echte Hilfsbefehl wartet, bis der Prozess beendet ist, und startet
    erst dann das Programm (nur unter Linux/macOS mit /bin/sh).

Start:  python test_update_deb.py
"""

import os
import subprocess
import sys
import tempfile
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

_TMP = tempfile.mkdtemp(prefix="fisi_update_deb_")
os.environ["FISI_DB_PATH"] = os.path.join(_TMP, "update_deb.db")

import fisi_update as fu  # noqa: E402

PATH = "/tmp/FISI-Lernplattform-Update/fisi-lernplattform_0.63.2_amd64.deb"
RESTARTS = "Das Update ist installiert. Das Programm startet neu."
OLD_TEXT = "Das Update ist installiert. Bitte das Programm schließen und neu starten."


class _Result:
    def __init__(self, code):
        self.returncode = code


class _FakeSubprocess:
    """Nachgebildetes subprocess: merkt sich run- und Popen-Aufrufe."""

    def __init__(self, code=0, popen_error=None):
        self.code = code
        self.popen_error = popen_error
        self.runs = []
        self.popens = []

    def run(self, args, **kwargs):
        self.runs.append((list(args), kwargs))
        return _Result(self.code)

    def Popen(self, args, **kwargs):  # noqa: N802 (wie subprocess)
        self.popens.append((list(args), kwargs))
        if self.popen_error is not None:
            raise self.popen_error
        return object()


class DebNeustartTest(unittest.TestCase):
    def setUp(self):
        self._orig = fu.subprocess

    def tearDown(self):
        fu.subprocess = self._orig

    def _install(self, fake, pid=4321):
        fu.subprocess = fake
        return fu.install(PATH, kind="deb", version="0.63.2", pid=pid)

    def test_erfolg_startet_hilfsprozess(self):
        fake = _FakeSubprocess(code=0)
        result = self._install(fake)
        self.assertEqual(result, (True, RESTARTS))
        # Installation selbst unveraendert
        self.assertEqual([args for args, _kw in fake.runs],
                         [["pkexec", "apt-get", "install", "-y", PATH]])
        self.assertEqual(len(fake.popens), 1)
        args, kwargs = fake.popens[0]
        self.assertEqual(args[:2], ["/bin/sh", "-c"])
        self.assertEqual(args[3:], ["fisi-update", "4321", sys.executable])
        self.assertIn('kill -0 "$1"', args[2])
        self.assertTrue(args[2].rstrip().endswith('exec "$2"'))
        self.assertIs(kwargs.get("start_new_session"), True)
        self.assertEqual(kwargs["env"].get("PYINSTALLER_RESET_ENVIRONMENT"), "1")
        # die uebrige Umgebung wird weitergegeben
        self.assertEqual(kwargs["env"].get("PATH"), os.environ.get("PATH"))

    def test_ohne_pid_eigene_prozessnummer(self):
        fake = _FakeSubprocess(code=0)
        self._install(fake, pid=None)
        self.assertEqual(fake.popens[0][0][4], str(os.getpid()))

    def test_misserfolg_wie_bisher(self):
        fake = _FakeSubprocess(code=126)
        result = self._install(fake)
        self.assertEqual(result, (False, fu.deb_cancel_message(PATH)))
        self.assertEqual([args for args, _kw in fake.popens], [["xdg-open", PATH]])

    def test_hilfsprozess_nicht_startbar(self):
        fake = _FakeSubprocess(code=0, popen_error=OSError("kein /bin/sh"))
        result = self._install(fake)
        self.assertEqual(result, (False, OLD_TEXT))

    @unittest.skipUnless(os.path.exists("/bin/sh") and os.name == "posix", "nur mit /bin/sh")
    def test_hilfsbefehl_wartet_auf_das_ende(self):
        fake = _FakeSubprocess(code=0)
        self._install(fake)
        args, _kwargs = fake.popens[0]
        folder = tempfile.mkdtemp(prefix="neustart_", dir=_TMP)
        marker = os.path.join(folder, "gestartet")
        program = os.path.join(folder, "programm.sh")
        with open(program, "w", encoding="utf-8") as handle:
            handle.write("#!/bin/sh\necho \"$PYINSTALLER_RESET_ENVIRONMENT\" > '%s'\n" % marker)
        os.chmod(program, 0o755)
        # Stellvertreter fuer das laufende Programm
        running = subprocess.Popen(["sleep", "1.5"])
        helper = subprocess.Popen(args[:4] + [str(running.pid), program],
                                  env=dict(os.environ, PYINSTALLER_RESET_ENVIRONMENT="1"))
        try:
            time.sleep(0.8)
            self.assertFalse(os.path.exists(marker),
                             "Programm startete, bevor das alte beendet war")
            running.wait()
            self.assertEqual(helper.wait(timeout=10), 0)
            with open(marker, encoding="utf-8") as handle:
                self.assertEqual(handle.read().strip(), "1")
        finally:
            for process in (running, helper):
                if process.poll() is None:
                    process.kill()
                    process.wait()


if __name__ == "__main__":
    unittest.main(verbosity=2)
