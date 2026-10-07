#!/usr/bin/env python3
"""F6: Erbt ein vom Programm gestarteter Hilfsprozess die Sperre laeuft.lock?
Elternprozess holt die Sperre mit fisi_einzelstart.claim (Original-Code
0.59.1), startet ein Kind (sleep 20) auf verschiedene Arten, beendet sich
sofort hart; danach prueft ein dritter Prozess, ob die Sperre frei ist."""
import fcntl, os, subprocess, sys, tempfile, time, json
SRC = sys.argv[1]
sys.path.insert(0, SRC)
import fisi_einzelstart as fe

def child_variant(folder, variant):
    pid = os.fork()
    if pid == 0:
        # Elternprozess (simuliert FISI)
        assert fe.claim(folder=folder)
        fd = fe._lock_handle.fileno()
        flags = open("/proc/self/fdinfo/%d" % fd).read().split("\n")[1]
        info = {"fd": fd, "fdinfo_flags": flags.split()[1],
                "inheritable": os.get_inheritable(fd)}
        if variant == "popen_standard":          # wie xdg-open / pkexec / Neustart
            p = subprocess.Popen(["sleep", "20"])
        elif variant == "popen_close_fds_false":  # schlechtester Fall subprocess
            p = subprocess.Popen(["sleep", "20"], close_fds=False)
        elif variant == "popen_start_new_session":  # wie AppImage-Neustart
            p = subprocess.Popen(["sleep", "20"], start_new_session=True)
        elif variant == "run_wie_pkexec":           # subprocess.run blockiert -> hier Popen
            p = subprocess.Popen(["sleep", "20"])
        elif variant == "fork_ohne_exec":           # nur Gegenprobe: reines fork erbt
            p2 = os.fork()
            if p2 == 0:
                time.sleep(20); os._exit(0)
            class P: pid = p2
            p = P()
        elif variant == "pass_fds_gegenprobe":      # Gegenprobe: ausdruecklich vererbt
            p = subprocess.Popen(["sleep", "20"], pass_fds=(fd,))
        info["kind_pid"] = p.pid
        kid_fds = sorted(os.listdir("/proc/%d/fd" % p.pid)) if os.path.exists("/proc/%d/fd" % p.pid) else []
        time.sleep(0.3)
        kid_fds = sorted(os.listdir("/proc/%d/fd" % p.pid))
        info["kind_fds"] = kid_fds
        with open(os.path.join(folder, "info.json"), "w") as h:
            json.dump(info, h)
        os._exit(0)   # Elternprozess endet (wie Notausgang/Absturz)
    os.waitpid(pid, 0)
    time.sleep(0.3)
    info = json.load(open(os.path.join(folder, "info.json")))
    # Dritter Prozess: Sperre frei?
    check = subprocess.run([sys.executable, "-c", (
        "import fcntl,sys;h=open(sys.argv[1],'a+')\n"
        "try:\n fcntl.flock(h.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB);print('frei')\n"
        "except BlockingIOError:\n print('belegt')"), os.path.join(folder, fe.LOCK_FILE)],
        capture_output=True, text=True)
    info["sperre_nach_ende_eltern"] = check.stdout.strip()
    try:
        os.kill(info["kind_pid"], 9)
    except OSError:
        pass
    return info

results = {}
for v in ("popen_standard", "popen_close_fds_false", "popen_start_new_session",
          "fork_ohne_exec", "pass_fds_gegenprobe"):
    folder = tempfile.mkdtemp(prefix="sperre-")
    fe._lock_handle = None
    results[v] = child_variant(folder, v)
print(json.dumps(results, indent=1))
