#!/usr/bin/env python3
"""F5: Wie lange lebt der Prozess nach dem Schliessen noch?
Startet das Programm wie main() (ohne Sperre), wartet das Vorladen ab,
besucht Seiten, optional Darstellungswechsel, und schliesst dann ueber
FISIApp.on_close (wie das X am Fenster). Zeitstempel in AUSGABE (eine Zeile
je Schritt), faulthandler schreibt alle Stapel, falls der Prozess 3 s nach
Ende der Ereignisschleife noch lebt. Der Notausgang (8 s) bleibt aktiv; ob
er greift, steht danach in fehler.log im Datenordner.
Aufruf: python f5_schliessen.py ORDNER AUSGABE [WECHSEL]"""
import atexit
import faulthandler
import os
import sys
import tempfile
import threading
import time

SRC = os.path.abspath(sys.argv[1])
OUT = os.path.abspath(sys.argv[2])
SWITCHES = int(sys.argv[3]) if len(sys.argv) > 3 else 0
folder = os.environ.get("MESS_ORDNER") or tempfile.mkdtemp(prefix="fisi f5 ")
os.environ["FISI_DB_PATH"] = os.path.join(folder, "test.db")
# wie im Starttest: kein Netz (Update-Suche, Abgleich), kein Rundgang;
# on_close und mainloop laufen unveraendert
os.environ["FISI_SELFTEST"] = os.path.join(folder, "selftest_unbenutzt.txt")
sys.path.insert(0, SRC)
os.chdir(SRC)
T0 = time.perf_counter()
log = open(OUT, "w", encoding="utf-8", buffering=1)


def mark(text):
    log.write("%8.3f %s | Threads: %s\n" % (time.perf_counter() - T0, text, ", ".join(
        "%s%s" % (t.name, "(d)" if t.daemon else "") for t in threading.enumerate())))


atexit.register(lambda: mark("atexit (Interpreter beginnt Abbau)"))
import customtkinter as ctk   # noqa: E402
import app_gui                # noqa: E402
import fisi_theme             # noqa: E402

mark("import fertig, Daten: %s" % folder)
app_gui.install_error_log(app_gui.APP_VERSION)
app_gui.apply_appearance()
root = ctk.CTk(className=getattr(app_gui, "LINUX_CLASS_NAME", "Tk")) \
    if sys.platform.startswith("linux") else ctk.CTk()
app = app_gui.FISIApp(root)
mark("Fenster aufgebaut")
steps = {"n": 0}


def drive():
    pre = app.preloader
    if not pre.done:
        root.after(200, drive)
        return
    if steps["n"] == 0:
        mark("Vorladen fertig")
        for key in ("dashboard", "progress", "cards", "settings"):
            app.show_view(key)
            root.update()
        for _ in range(SWITCHES):
            mode = fisi_theme.MODE_LIGHT if fisi_theme.current_mode != fisi_theme.MODE_LIGHT \
                else fisi_theme.MODE_DARK
            app.change_color(mode=mode)
            root.update()
        steps["n"] = 1
        root.after(200, drive)   # Vorladen nach dem Wechsel abwarten
        return
    mark("Elemente %d, Schliessen beginnt (on_close)" % app_gui.count_widgets(root))
    started = time.perf_counter()
    app.on_close()
    mark("on_close fertig nach %.0f ms (Fenster abgebaut)" % ((time.perf_counter() - started) * 1000))


root.after(500, drive)
root.mainloop()
mark("mainloop beendet")
faulthandler.dump_traceback_later(3, file=log)
