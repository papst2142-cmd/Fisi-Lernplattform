"""Probe 0.59.1 (nur Zweig probe-0591-einzelstart-windows): echtes Programm
unter Windows zweimal starten. Misst: endet der zweite Start mit 0, laeuft
das erste weiter, gibt es nur ein Hauptfenster, ist das minimierte Fenster
danach wiederhergestellt und im Vordergrund?"""
import ctypes, os, subprocess, sys, tempfile, time
from ctypes import wintypes

user32 = ctypes.windll.user32
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
env = dict(os.environ, FISI_DB_PATH=os.path.join(tempfile.mkdtemp(), "probe.db"))
env.pop("FISI_SELFTEST", None)


def windows_of(pid):
    found = []
    proc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    def cb(hwnd, _):
        owner = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
        if owner.value == pid and user32.IsWindowVisible(hwnd):
            buf = ctypes.create_unicode_buffer(256)
            user32.GetWindowTextW(hwnd, buf, 256)
            if buf.value:
                found.append((hwnd, buf.value))
        return True
    user32.EnumWindows(proc(cb), 0)
    return found


def row(name, value):
    print("| %s | %s |" % (name, value), flush=True)


first = subprocess.Popen([sys.executable, os.path.join(HERE, "app_gui.py")], env=env)
end = time.time() + 90
while time.time() < end and not windows_of(first.pid):
    time.sleep(0.5)
time.sleep(4)
wins = windows_of(first.pid)
print("| Pruefung | Ergebnis |\n|---|---|")
row("Fenster erster Start", wins)
hwnd = wins[0][0]
user32.ShowWindow(hwnd, 6)            # SW_MINIMIZE
time.sleep(1)
row("minimiert (IsIconic)", bool(user32.IsIconic(hwnd)))
start = time.time()
second = subprocess.run([sys.executable, os.path.join(HERE, "app_gui.py")], env=env,
                        capture_output=True, text=True, timeout=120)
row("zweiter Start: Rueckgabewert", second.returncode)
row("zweiter Start: Dauer s", round(time.time() - start, 1))
time.sleep(1.5)
row("erstes Programm laeuft noch", first.poll() is None)
row("Fenster des ersten Programms", windows_of(first.pid))
row("danach minimiert (IsIconic)", bool(user32.IsIconic(hwnd)))
row("im Vordergrund (GetForegroundWindow)", user32.GetForegroundWindow() == hwnd)
folder = os.path.dirname(env["FISI_DB_PATH"])
row("Dateien im Datenordner", sorted(os.listdir(folder)))
log = os.path.join(folder, "fehler.log")
row("fehler.log", open(log, encoding="utf-8").read() if os.path.exists(log) else "-")
first.kill()
first.wait()
third = subprocess.Popen([sys.executable, os.path.join(HERE, "app_gui.py")], env=env)
end = time.time() + 90
while time.time() < end and not windows_of(third.pid):
    time.sleep(0.5)
row("nach Beenden per TerminateProcess: neuer Start zeigt Fenster", bool(windows_of(third.pid)))
third.kill()
ok = second.returncode == 0
sys.exit(0 if ok else 1)
