#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests fuer den Update-Ablauf am PC (ab 0.55.1) - ohne Oberflaeche:
  * Befehlszeile fuer den Installer (/WAITPID, /UPDATELOG, /FISIEXE, /LOG),
    auch mit Leerzeichen und Umlauten im Pfad
  * update.log: Schritte, Kuerzen, kein Zugangsschluessel im Problembericht
  * Pruefung beim naechsten Start (finish_pending_update): Erfolg und
    Fehlschlag werden genau einmal gemeldet
  * Ganzer Ablauf mit einem Platzhalter-Installer: Erfolg, Fehler und
    "Datei in Benutzung". Der Platzhalter haelt sich an dieselben Regeln wie
    der echte Installer (FISI-Lernplattform.iss, [Code]): erst warten, bis
    das Programm beendet ist, dann ersetzen oder zurueckrollen, Schritte nach
    update.log, bei Fehlschlag die alte Version wieder starten.
    Der echte Inno-Setup-Installer wird am Windows-Rechner geprueft (siehe
    Bericht 0.55.1).

Datenbank, einstellungen.json und Protokolle liegen in einem Temp-Ordner
mit Leerzeichen und Umlauten (FISI_DB_PATH).

Start:  python test_update.py
"""

import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import fisi_diagnose as fd  # noqa: E402
import fisi_update as fu  # noqa: E402
from fisi_core import DBManager  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
FAKE_TOKEN = "github_pat_11GEHEIM1234567890abcdefXYZ"

# Platzhalter-Installer: verhaelt sich wie [Code] in FISI-Lernplattform.iss.
# Modus steht in modus.txt neben dem Skript (erfolg, fehler, in_benutzung).
FAKE_INSTALLER = r'''
import datetime, os, signal, sys, time
args = dict(a[1:].split("=", 1) for a in sys.argv[1:] if "=" in a)
folder = os.path.dirname(os.path.abspath(__file__))
mode = open(os.path.join(folder, "modus.txt"), encoding="utf-8").read().strip()

def log(text):
    stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(args["UPDATELOG"], "a", encoding="utf-8") as handle:
        handle.write("%s | Installer 0.56 | %s\n" % (stamp, text))

def alive(pid):
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False

pid = int(args["WAITPID"])
log("gestartet, wartet auf das Ende des Programms (Prozess %d)" % pid)
end = time.time() + 10
while alive(pid) and time.time() < end:
    time.sleep(0.05)
if alive(pid):
    log("Programm läuft nach 10 s noch und wird beendet")
    os.kill(pid, signal.SIGKILL)
else:
    log("Programm hat sich beendet")
app_dir = os.path.dirname(args["FISIEXE"])
lock = os.path.join(app_dir, "gesperrt.lock")
if mode == "in_benutzung" and os.path.exists(lock):
    holder = int(open(lock).read())
    mode = "fehler" if alive(holder) else "erfolg"
with open(args["LOG"], "w", encoding="utf-8") as inno:
    if mode == "erfolg":
        with open(os.path.join(app_dir, "version.txt"), "w") as handle:
            handle.write("0.56")
        inno.write("Installation process succeeded.\n")
        log("Installation erfolgreich, Version 0.56 ist installiert")
        code = 0
    else:
        inno.write("DeleteFile failed; code 32. Der Prozess kann nicht auf die Datei "
                   "zugreifen, da sie von einem anderen Prozess verwendet wird.\n"
                   "Rolling back changes.\n")
        log("Installation NICHT abgeschlossen, die bisherige Version bleibt unverändert.")
        log("startet die bisherige Version wieder")
        os.spawnv(os.P_NOWAIT, sys.executable, [sys.executable, args["FISIEXE"]])
        code = 1
with open(os.path.join(folder, "fertig.txt"), "w") as handle:
    handle.write(str(code))
sys.exit(code)
'''

# Stellt das laufende Programm dar: startet den Installer wie UpdateDialog
# und endet nach "hold" Sekunden (so lange braucht das Schliessen).
FAKE_PROGRAM = r'''
import os, sys, time
sys.path.insert(0, sys.argv[1])
import fisi_update
installer, exe, hold = sys.argv[2], sys.argv[3], float(sys.argv[4])
sys.executable = exe       # Pfad der "installierten" FISI-Lernplattform.exe
must_quit, text = fisi_update.install(installer, kind="windows", version="0.56")
fisi_update.write_update_log("Programm sauber beendet.")
time.sleep(hold)
'''

# Die "alte Version", die der Installer nach einem Fehlschlag neu startet
FAKE_OLD_EXE = r'''
import os
open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "neu_gestartet.txt"), "w").close()
'''


def _hash(path):
    with open(path, "rb") as handle:
        return hashlib.sha256(handle.read()).hexdigest()


class TempDataMixin:
    def setUp(self):
        self.folder = tempfile.mkdtemp(prefix="fisi update ")
        self.data = os.path.join(self.folder, "Daten Ä Ö")
        os.makedirs(self.data)
        self._env = os.environ.get("FISI_DB_PATH")
        os.environ["FISI_DB_PATH"] = os.path.join(self.data, "fisi.db")

    def tearDown(self):
        if self._env is None:
            os.environ.pop("FISI_DB_PATH", None)
        else:
            os.environ["FISI_DB_PATH"] = self._env
        shutil.rmtree(self.folder, ignore_errors=True)

    def log_text(self):
        with open(fu.update_log_path(), encoding="utf-8") as handle:
            return handle.read()


class InstallerArgsTest(TempDataMixin, unittest.TestCase):
    def test_parameter_fuer_den_installer(self):
        setup = os.path.join(self.folder, "Fisi Lernplattform Test Ü", "Setup 0.56.exe")
        exe = os.path.join(self.folder, "Programme Ä", "FISI-Lernplattform.exe")
        args = fu.windows_installer_args(setup, pid=4242, exe=exe)
        self.assertEqual(args[0], setup)
        self.assertEqual(args[1:4], ["/SILENT", "/SUPPRESSMSGBOXES", "/NORESTART"])
        self.assertIn("/WAITPID=4242", args)
        self.assertIn("/UPDATELOG=%s" % fu.update_log_path(), args)
        self.assertIn("/FISIEXE=%s" % exe, args)
        self.assertIn("/LOG=%s" % fu.installer_log_path(), args)
        # Jedes Argument mit Leerzeichen steht als Ganzes in Anfuehrungszeichen
        line = subprocess.list2cmdline(args)
        for arg in args:
            if " " in arg:
                self.assertIn('"%s"' % arg, line)
        self.assertIn("Ü", line)

    def test_standard_ist_dieser_prozess(self):
        args = fu.windows_installer_args("setup.exe")
        self.assertIn("/WAITPID=%d" % os.getpid(), args)
        self.assertIn("/FISIEXE=%s" % sys.executable, args)

    def test_iss_kennt_die_parameter(self):
        with open(os.path.join(HERE, "FISI-Lernplattform.iss"), encoding="utf-8") as handle:
            iss = handle.read()
        for name in ("WAITPID", "UPDATELOG", "FISIEXE"):
            self.assertIn("{param:%s|" % name, iss)
        self.assertIn("WaitForSingleObject", iss)
        self.assertIn("Installation NICHT abgeschlossen", iss)
        # Inno Setup liest das Skript ohne BOM als ANSI - nur ASCII erlaubt
        self.assertTrue(all(ord(char) < 128 for char in iss), "Umlaut im .iss")


class UpdateLogTest(TempDataMixin, unittest.TestCase):
    def test_zeilen_mit_zeit(self):
        fu.write_update_log("Download startet: Version 0.56")
        fu.write_update_log("Programm sauber beendet.")
        lines = self.log_text().splitlines()
        self.assertEqual(len(lines), 2)
        self.assertRegex(lines[0], r"^\d{4}-\d\d-\d\d \d\d:\d\d:\d\d \| Programm \| Download")

    def test_kuerzen(self):
        for number in range(3000):
            fu.write_update_log("Zeile %d %s" % (number, "x" * 40))
        self.assertLess(os.path.getsize(fu.update_log_path()), fu.UPDATE_LOG_MAX + 200)
        self.assertIn("Zeile 2999", self.log_text())
        self.assertTrue(self.log_text().split("\n", 1)[0][:4].isdigit())

    def test_im_problembericht_ohne_token(self):
        self.assertNotIn("update.log", fd.build_report(settings={}))
        fu.write_update_log("Installer wird gestartet")
        fu.write_update_log("Fehler mit %s" % FAKE_TOKEN)
        report = fd.build_report(settings={})
        self.assertIn("--- update.log ---", report)
        self.assertIn("Installer wird gestartet", report)
        self.assertNotIn(FAKE_TOKEN, report)
        # fehler.log-Abschnitt bleibt davor
        self.assertLess(report.index("--- fehler.log ---"), report.index("--- update.log ---"))


class PendingUpdateTest(TempDataMixin, unittest.TestCase):
    def test_ohne_update_nichts(self):
        self.assertIsNone(fu.finish_pending_update("0.55.1"))
        self.assertFalse(os.path.exists(fu.update_log_path()))

    def test_erfolg(self):
        fu.remember_pending_update("0.56")
        self.assertEqual(fu.finish_pending_update("0.56"), ("ok", "0.56"))
        self.assertIsNone(fu.finish_pending_update("0.56"))   # nur einmal
        self.assertIn("Update auf 0.56 abgeschlossen", self.log_text())

    def test_fehlschlag_wird_einmal_gemeldet(self):
        fu.remember_pending_update("0.56")
        kind, text = fu.finish_pending_update("0.55.1")
        self.assertEqual(kind, "fehler")
        self.assertIn("Version 0.56 wurde nicht installiert", text)
        self.assertIn("weiterhin Version 0.55.1", text)
        self.assertIn("Lernstand ist davon nicht betroffen", text)
        self.assertIn(fu.update_log_path(), text)
        self.assertIn(fu.REASON_UNKNOWN, text)
        self.assertIsNone(fu.finish_pending_update("0.55.1"))
        self.assertIn("NICHT abgeschlossen", self.log_text())

    def test_fehlschlag_mit_rollback(self):
        fu.remember_pending_update("0.56")
        with open(fu.installer_log_path(), "w", encoding="utf-8") as handle:
            handle.write("Rolling back changes.\n")
        self.assertIn(fu.REASON_ROLLBACK, fu.finish_pending_update("0.55.1")[1])

    def test_installer_startet_nicht(self):
        missing = os.path.join(self.folder, "gibt es nicht.exe")
        with self.assertRaises(fu.UpdateError):
            fu.install(missing, kind="windows", version="0.56")
        self.assertIsNone(fu.finish_pending_update("0.55.1"))   # keine falsche Meldung
        self.assertIn("ließ sich nicht starten", self.log_text())

    def test_andere_einstellungen_bleiben(self):
        settings = fu.load_settings()
        settings["auto_check"] = False
        fu.save_settings(settings)
        fu.remember_pending_update("0.56")
        fu.finish_pending_update("0.55.1")
        self.assertFalse(fu.load_settings()["auto_check"])


@unittest.skipIf(sys.platform == "win32",
                 "Platzhalter laeuft als Python-Skript; unter Windows wird der echte "
                 "Installer geprueft")
class PlaceholderInstallerTest(TempDataMixin, unittest.TestCase):
    """Ganzer Ablauf: Programm startet den Installer und beendet sich, der
    Installer wartet, ersetzt oder rollt zurueck, das Programm startet neu
    und meldet das Ergebnis."""

    def setUp(self):
        super().setUp()
        self.setup_dir = os.path.join(self.folder, "Fisi Lernplattform Test Ü", "Download")
        self.app_dir = os.path.join(self.folder, "Fisi Lernplattform Test Ü", "Programm")
        os.makedirs(self.setup_dir)
        os.makedirs(self.app_dir)
        self.installer = os.path.join(self.setup_dir, "FISI-Lernplattform-Setup 0.56.exe")
        with open(self.installer, "w", encoding="utf-8") as handle:
            handle.write("#!%s\n%s" % (sys.executable, FAKE_INSTALLER))
        os.chmod(self.installer, 0o755)
        self.exe = os.path.join(self.app_dir, "FISI-Lernplattform.exe")
        with open(self.exe, "w", encoding="utf-8") as handle:
            handle.write(FAKE_OLD_EXE)
        self.program = os.path.join(self.folder, "programm.py")
        with open(self.program, "w", encoding="utf-8") as handle:
            handle.write(FAKE_PROGRAM)
        # Lernstand mit einem Eintrag
        db = DBManager(os.environ["FISI_DB_PATH"])
        db.log_quiz_answer("Netzwerk", "Was ist DNS?", True)
        self.db_hash = _hash(os.environ["FISI_DB_PATH"])

    def run_update(self, mode, hold=0.3):
        with open(os.path.join(self.setup_dir, "modus.txt"), "w") as handle:
            handle.write(mode)
        started = time.time()
        program = subprocess.Popen([sys.executable, self.program, HERE, self.installer,
                                    self.exe, str(hold)])
        program.wait(timeout=30)
        done = os.path.join(self.setup_dir, "fertig.txt")
        while not os.path.exists(done) and time.time() - started < 30:
            time.sleep(0.05)
        self.assertTrue(os.path.exists(done), "Installer nicht fertig geworden")
        with open(done) as handle:
            return int(handle.read())

    def assert_order(self, *parts):
        text = self.log_text()
        positions = [text.index(part) for part in parts]
        self.assertEqual(positions, sorted(positions), text)

    def test_erfolg(self):
        self.assertEqual(self.run_update("erfolg"), 0)
        self.assert_order("Installer wird gestartet", "/WAITPID=",
                          "Installer läuft", "Programm sauber beendet",
                          "Installer 0.56 | gestartet, wartet", "Programm hat sich beendet",
                          "Installation erfolgreich")
        with open(os.path.join(self.app_dir, "version.txt")) as handle:
            self.assertEqual(handle.read(), "0.56")
        self.assertEqual(fu.finish_pending_update("0.56"), ("ok", "0.56"))
        self.assertEqual(_hash(os.environ["FISI_DB_PATH"]), self.db_hash)

    def test_installer_wartet_auf_langsames_beenden(self):
        # Programm braucht 2 s zum Schliessen - der Installer ersetzt erst danach
        self.assertEqual(self.run_update("erfolg", hold=2), 0)
        self.assert_order("Programm sauber beendet", "Programm hat sich beendet",
                          "Installation erfolgreich")
        self.assertNotIn("wird beendet", self.log_text())

    def test_fehler(self):
        self.assertEqual(self.run_update("fehler"), 1)
        self.assert_order("Installer wird gestartet", "Programm hat sich beendet",
                          "NICHT abgeschlossen", "startet die bisherige Version wieder")
        self.assertFalse(os.path.exists(os.path.join(self.app_dir, "version.txt")))
        kind, text = fu.finish_pending_update("0.55.1")
        self.assertEqual(kind, "fehler")
        self.assertIn(fu.REASON_ROLLBACK, text)
        self._wait_for(os.path.join(self.app_dir, "neu_gestartet.txt"))
        self.assertEqual(_hash(os.environ["FISI_DB_PATH"]), self.db_hash)

    def test_datei_in_benutzung(self):
        # Ein anderer Prozess haelt eine Programmdatei offen
        holder = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
        try:
            with open(os.path.join(self.app_dir, "gesperrt.lock"), "w") as handle:
                handle.write(str(holder.pid))
            self.assertEqual(self.run_update("in_benutzung"), 1)
        finally:
            holder.kill()
            holder.wait()
        self.assertIn("NICHT abgeschlossen", self.log_text())
        with open(fu.installer_log_path(), encoding="utf-8") as handle:
            self.assertIn("von einem anderen Prozess verwendet", handle.read())
        kind, text = fu.finish_pending_update("0.55.1")
        self.assertEqual(kind, "fehler")
        self.assertIn("Protokoll liegt hier", text)
        self.assertEqual(_hash(os.environ["FISI_DB_PATH"]), self.db_hash)

    def test_datei_wieder_frei(self):
        # Sperrender Prozess ist schon beendet -> Update klappt
        holder = subprocess.Popen([sys.executable, "-c", "pass"])
        holder.wait()
        with open(os.path.join(self.app_dir, "gesperrt.lock"), "w") as handle:
            handle.write(str(holder.pid))
        self.assertEqual(self.run_update("in_benutzung"), 0)

    def _wait_for(self, path, seconds=10):
        end = time.time() + seconds
        while not os.path.exists(path) and time.time() < end:
            time.sleep(0.05)
        self.assertTrue(os.path.exists(path), path)


if __name__ == "__main__":
    unittest.main(verbosity=2)
