# -*- coding: utf-8 -*-
"""Probe 0.59.2 (Plan, nicht mergen): Windows-Fragen Q2/Q6.

1) laeuft.info neben msvcrt.locking: Kann ein zweiter Prozess laeuft.lock
   bzw. laeuft.info lesen, waehrend Byte 0 von laeuft.lock gesperrt ist?
2) os.replace auf laeuft.info, waehrend ein anderer Prozess sie offen hat.
3) faulthandler unter Windows: dump_traceback_later bei blockiertem
   Hauptfaden (auch in Tcl), register vorhanden?, Neusetzen-Kosten.
4) Herzschlag-Kosten (after 500 ms) im Leerlauf.
"""
import faulthandler
import os
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HERE = os.environ.get("FISI_PROBE_DIR") or tempfile.mkdtemp()
LOCK = os.path.join(HERE, "laeuft.lock")
INFO = os.path.join(HERE, "laeuft.info")


def holder():
    import fisi_einzelstart as fe
    handle = fe._try_lock(HERE)
    tmp = INFO + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write("pid=%d\nstart=2026-10-07 08:00:00\nversion=0.59.2\n" % os.getpid())
    os.replace(tmp, INFO)
    print("HALTER bereit pid", os.getpid(), flush=True)
    time.sleep(12)
    handle.close()


def reader():
    import fisi_einzelstart as fe
    try:
        fe._try_lock(HERE)
        print("  Sperre: FREI (unerwartet)")
    except fe._Busy:
        print("  Sperre: belegt (_Busy) - wie erwartet")
    try:
        with open(LOCK, encoding="utf-8") as f:
            print("  laeuft.lock lesen: OK, Inhalt %r" % f.read())
    except OSError as e:
        print("  laeuft.lock lesen: FEHLER %r" % (e,))
    try:
        with open(INFO, encoding="utf-8") as f:
            print("  laeuft.info lesen: OK ->", f.read().replace("\n", " | "))
    except OSError as e:
        print("  laeuft.info lesen: FEHLER %r" % (e,))


def replace_while_open():
    with open(INFO, encoding="utf-8") as reading:
        reading.read(3)
        tmp = INFO + ".tmp2"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write("neu")
        try:
            os.replace(tmp, INFO)
            print("  os.replace bei offener Datei: OK")
        except OSError as e:
            print("  os.replace bei offener Datei: FEHLER %r (wird geschluckt)" % (e,))
            os.remove(tmp)
        try:
            with open(INFO, "w", encoding="utf-8") as f:
                f.write("direkt")
            print("  direkt ueberschreiben bei offener Datei: OK")
        except OSError as e:
            print("  direkt ueberschreiben bei offener Datei: FEHLER %r" % (e,))


def faulthandler_probe():
    log_path = os.path.join(HERE, "haenger.log")
    log = open(log_path, "a")
    faulthandler.enable(file=log)
    print("  register vorhanden:", hasattr(faulthandler, "register"))
    n = 1000
    t = time.perf_counter()
    for _ in range(n):
        faulthandler.dump_traceback_later(30, file=log)
    print("  Neusetzen: %.1f us je Aufruf" % ((time.perf_counter() - t) / n * 1e6))
    faulthandler.dump_traceback_later(1, file=log)
    time.sleep(1.5)
    import tkinter as tk
    root = tk.Tk()
    faulthandler.dump_traceback_later(1, file=log)
    root.tk.call("after", "2000")      # Hauptfaden blockiert in Tcl
    root.destroy()
    faulthandler.cancel_dump_traceback_later()
    log.flush()
    text = open(log_path, encoding="utf-8", errors="replace").read()
    print("  haenger.log: %d Bytes, %d x 'Timeout'" % (len(text), text.count("Timeout")))
    print("  " + text.replace("\n", "\n  ")[:1200])
    fd = log.fileno()
    import msvcrt
    import ctypes
    flags = ctypes.c_ulong()
    handle = msvcrt.get_osfhandle(fd)
    ctypes.windll.kernel32.GetHandleInformation(ctypes.c_void_p(handle), ctypes.byref(flags))
    print("  haenger.log vererbbar:", os.get_inheritable(fd), "HANDLE_FLAG_INHERIT:",
          bool(flags.value & 1))


def heartbeat_cost(mode, secs=20):
    import tkinter as tk
    root = tk.Tk()
    st = {"armed": 0.0}
    log = open(os.path.join(HERE, "h2.log"), "a")
    faulthandler.enable(file=log)

    def hb():
        now = time.monotonic()
        if now - st["armed"] >= 5:
            faulthandler.dump_traceback_later(30, file=log)
            st["armed"] = now
        root.after(500, hb)
    if mode == "an":
        root.after(500, hb)
    root.after(1000, lambda: st.update(c0=time.process_time()))

    def done():
        print("  Herzschlag %s: CPU-Zeit in %d s: %.1f ms"
              % (mode, secs, (time.process_time() - st["c0"]) * 1000))
        root.destroy()
    root.after(1000 + secs * 1000, done)
    root.mainloop()
    faulthandler.cancel_dump_traceback_later()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "holder":
            holder()
        elif sys.argv[1] == "reader":
            reader()
        elif sys.argv[1] == "hb":
            heartbeat_cost(sys.argv[2])
        sys.exit(0)
    print(sys.version, sys.platform)
    env = dict(os.environ, FISI_PROBE_DIR=HERE)
    me = os.path.abspath(__file__)
    p = subprocess.Popen([sys.executable, me, "holder"], stdout=subprocess.PIPE,
                         text=True, env=env)
    print(p.stdout.readline().strip())
    print("1) zweiter Prozess liest, waehrend die Sperre gehalten wird:", flush=True)
    subprocess.run([sys.executable, me, "reader"], env=env)
    print("2) laeuft.info ersetzen, waehrend sie offen ist:", flush=True)
    replace_while_open()
    p.wait()
    print("3) faulthandler unter Windows:", flush=True)
    faulthandler_probe()
    print("4) Herzschlag-Kosten im Leerlauf:", flush=True)
    for mode in ("aus", "an", "aus", "an"):
        subprocess.run([sys.executable, me, "hb", mode], env=env)
