"""Startet den Installer genau so wie das Programm ab 0.55.1 (Ersatz fuer den
Klick auf "Jetzt aktualisieren"): gleiche Parameter aus
fisi_update.windows_installer_args, gleiche update.log-Zeilen. Wartet dann
auf den Installer und gibt seinen Rueckgabewert aus."""
import os, subprocess, sys
here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(here, "..", "fix"))
import fisi_update as fu
setup, pid, exe, target = sys.argv[1], int(sys.argv[2]), sys.argv[3], sys.argv[4]
args = fu.windows_installer_args(setup, pid=pid, exe=exe)
fu.write_update_log("Installer wird gestartet: %s" % subprocess.list2cmdline(args))
fu.remember_pending_update(target)
process = subprocess.Popen(args, close_fds=True)
fu.write_update_log("Installer läuft (Prozess %d). Das Programm wird jetzt beendet, "
                    "der Installer wartet darauf." % process.pid)
print("BEFEHLSZEILE", subprocess.list2cmdline(args), flush=True)
print("RUECKGABEWERT", process.wait(), flush=True)
