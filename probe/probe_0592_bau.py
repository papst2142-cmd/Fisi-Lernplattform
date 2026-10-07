# -*- coding: utf-8 -*-
"""Probe 0.59.2 Bau (nur Zweig probe-0592-bau, nicht mergen): Windows-Pruefungen
aus Plan Abschnitt 6, Punkt 9.

A2  Speicherspalte gefuellt, Vergleich mit psutil
A3  verfuegbarer Speicher und Vorgang in der Messdatei
E1  laeuft.info neben der Sperre, Eintrag eines blockierten Zweitstarts
F   Waechter: Blockade in Python und in Tcl, Stapel nach 30 s, "wieder frei"
P   Problembericht mit haenger.log und laeuft.info
Aufruf: python probe/probe_0592_bau.py [teil]
"""
import os
import subprocess
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def show(title, path):
    print("--- %s:" % title)
    try:
        with open(path, encoding="utf-8") as handle:
            print(handle.read().rstrip() or "(leer)")
    except OSError as error:
        print("(nicht lesbar: %r)" % (error,))


def part_a2():
    import psutil
    import fisi_leistung as fle
    print("=== A2 Speicherspalte")
    proc = psutil.Process()
    for _ in range(3):
        mem, private = fle.memory_mb()
        info = proc.memory_full_info()
        print("  memory_mb: Arbeitssatz %s MB, privat %s MB | psutil rss %.1f MB, private %.1f MB"
              % (mem, private, info.rss / 1048576.0, info.private / 1048576.0))
        print("  available_mb: %s MB | psutil available %.0f MB"
              % (fle.available_mb(), psutil.virtual_memory().available / 1048576.0))
        _ballast = bytearray(50 * 1048576)   # noqa: F841 - Arbeitssatz waechst
        time.sleep(0.2)
    print("=== A3 Messdatei")
    folder = tempfile.mkdtemp()
    path = os.path.join(folder, "leistung.csv")
    rec = fle.Recorder("0.59.2", "PC", path=path, toolkit="probe")
    rec.task_source = lambda: "darstellung"
    rec.set_active(True)
    rec.record(fle.EVENT_BLOCKED, nach="settings", dauer_ms=6200, vorgang="seite:settings")
    rec.record("seite", von="start", nach="settings", dauer_ms=120)
    rec.flush()
    show("leistung.csv", path)


def holder(folder, mode):
    import fisi_einzelstart as fe
    if mode == "antwortet":
        fe.claim(folder, version="0.59.2")
    else:
        fe._try_lock(folder)
        fe.write_info(folder, "0.59.2")
    print("HALTER bereit", os.getpid(), flush=True)
    time.sleep(20)


def part_e():
    import fisi_einzelstart as fe
    print("=== E1/E2 Sperre und laeuft.info")
    for mode in ("antwortet", "stumm"):
        folder = tempfile.mkdtemp()
        env = dict(os.environ, FISI_DB_PATH=os.path.join(folder, "fisi.db"))
        child = subprocess.Popen([sys.executable, __file__, "halter", folder, mode],
                                 stdout=subprocess.PIPE, text=True, env=env)
        print("  Halter (%s):" % mode, child.stdout.readline().strip())
        print("  read_info:", fe.read_info(folder))
        print("  holder_text:", fe.holder_text(folder))
        for name in ("laeuft.lock", "laeuft.info"):
            try:
                with open(os.path.join(folder, name), encoding="utf-8") as handle:
                    print("  %s lesen: OK (%d Zeichen)" % (name, len(handle.read())))
            except OSError as error:
                print("  %s lesen: FEHLER %r" % (name, error))
        started = time.monotonic()
        result = subprocess.run(
            [sys.executable, "-c",
             "import sys; sys.path.insert(0, %r); import fisi_einzelstart as fe; "
             "print(fe.claim(%r, answer_seconds=2, lock_seconds=3, version='0.59.2'))"
             % (ROOT, folder)], capture_output=True, text=True, env=env)
        print("  Zweitstart: claim -> %s nach %.1f s %s" % (
            result.stdout.strip(), time.monotonic() - started, result.stderr.strip()[-300:]))
        show("fehler.log (%s)" % mode, os.path.join(folder, "fehler.log"))
        child.kill()
        child.wait()


def blocker(folder):
    """Tk-Programm mit Herzschlag wie app_gui; blockiert den Hauptfaden
    7 s in Python, 7 s in Tcl und 34 s in Python."""
    import tkinter
    import fisi_core
    import fisi_haenger as fhg
    fisi_core.install_error_log("0.59.2")
    print("setup:", fhg.setup("0.59.2"), flush=True)
    root = tkinter.Tk()

    def heartbeat():
        fhg.beat()
        root.after(fhg.BEAT_MS, heartbeat)

    def step(nr):
        if nr == 0:
            fhg.vorgang("probe:python7")
            time.sleep(7)
        elif nr == 1:
            fhg.vorgang("probe:tcl7")
            root.tk.call("after", 7000)
        elif nr == 2:
            fhg.vorgang("probe:python34")
            time.sleep(34)
        else:
            root.destroy()
            return
        fhg.vorgang(fhg.IDLE)
        root.after(4000, step, nr + 1)

    root.after(fhg.BEAT_MS, heartbeat)
    root.after(3000, step, 0)
    root.mainloop()


def part_f():
    print("=== F Waechter (Windows)")
    folder = tempfile.mkdtemp()
    env = dict(os.environ, FISI_DB_PATH=os.path.join(folder, "fisi.db"))
    started = time.monotonic()
    result = subprocess.run([sys.executable, __file__, "blocker", folder], env=env,
                            capture_output=True, text=True, timeout=180)
    print("  Laufzeit %.1f s, Rueckgabe %d, Ausgabe %r" % (
        time.monotonic() - started, result.returncode, (result.stdout + result.stderr)[-500:]))
    show("haenger.log", os.path.join(folder, "haenger.log"))
    show("fehler.log", os.path.join(folder, "fehler.log"))
    print("=== P Problembericht")
    import fisi_diagnose as fdg
    import fisi_einzelstart as fe
    fe.write_info(folder, "0.59.2")
    report = fdg.build_report(None, version="0.59.2", geraet="PC", settings={},
                              log_path=os.path.join(folder, "fehler.log"))
    for marker in ("--- fehler.log ---", "--- haenger.log ---", "--- laeuft.info ---"):
        print("  %s: %s" % (marker, "ja" if marker in report else "FEHLT"))
    print("  Benutzername im Bericht: %s" % (
        "JA (Fehler)" if os.environ.get("USERNAME", "#") in report else "nein"))
    print("  Laenge %d Zeichen" % len(report))


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "halter":
        holder(sys.argv[2], sys.argv[3])
    elif len(sys.argv) > 1 and sys.argv[1] == "blocker":
        blocker(sys.argv[2])
    else:
        for part in (part_a2, part_e, part_f):
            try:
                part()
            except Exception as error:   # noqa: BLE001
                import traceback
                print("FEHLER in %s: %r" % (part.__name__, error))
                traceback.print_exc()
