#!/usr/bin/env python3
"""F6: Zweiter Start, waehrend das laufende Programm kurz blockiert ist.
Prozess A: Sperre (fisi_einzelstart.claim) + Tk-Fenster + listen() wie in
main(); BLOCK Sekunden nach dem Start blockiert ein Zeitgeber den
Hauptfaden fuer DAUER Sekunden (wie ein langer Vorlade-Schritt oder
Darstellungswechsel auf der VM). Prozess B startet waehrenddessen und ruft
claim() mit den echten Werten (3 s Antwort, 25 s Sperre) auf.
Aufruf: python f6_spaete_antwort.py ORDNER DAUER   (DAUER 0 = Gegenprobe)"""
import os
import subprocess
import sys
import tempfile
import time

SRC = os.path.abspath(sys.argv[1])
BLOCK_SECONDS = float(sys.argv[2])
if len(sys.argv) > 3 and sys.argv[3] == "A":
    os.environ["FISI_DB_PATH"] = sys.argv[4]
    sys.path.insert(0, SRC)
    import tkinter as tk
    import fisi_einzelstart as fe
    assert fe.claim()
    root = tk.Tk()
    fe.listen(root, closing=lambda: False, bring_to_front=lambda: print("A: nach vorn geholt", flush=True))
    if BLOCK_SECONDS:
        root.after(1000, lambda: (print("A: blockiert %.0f s" % BLOCK_SECONDS, flush=True),
                                  time.sleep(BLOCK_SECONDS), print("A: wieder frei", flush=True)))
    root.after(45000, root.destroy)
    root.mainloop()
    sys.exit(0)
if len(sys.argv) > 3 and sys.argv[3] == "B":
    os.environ["FISI_DB_PATH"] = sys.argv[4]
    sys.path.insert(0, SRC)
    import fisi_einzelstart as fe
    started = time.monotonic()
    result = fe.claim()
    print("B: claim() -> %s nach %.1f s (True = startet selbst, False = endet still)"
          % (result, time.monotonic() - started), flush=True)
    sys.exit(0)

folder = tempfile.mkdtemp(prefix="f6b-")
db = os.path.join(folder, "test.db")
a = subprocess.Popen([sys.executable, __file__, SRC, str(BLOCK_SECONDS), "A", db])
time.sleep(1.5)   # A ist gestartet und blockiert gleich bzw. schon
b = subprocess.run([sys.executable, __file__, SRC, str(BLOCK_SECONDS), "B", db])
a.terminate()
a.wait()
log = os.path.join(folder, "fehler.log")
print("fehler.log:", open(log, encoding="utf-8").read() if os.path.exists(log) else "(keine)")
