#!/bin/bash
# ============================================================================
#  Testsammlung fuer die CI (ab 0.60, K-D)
# ============================================================================
#  Fuehrt die Testdateien test_*.py eines Teils nacheinander aus und meldet am
#  Ende, welche Dateien rot waren. Laeuft unter Linux auf einer eigenen
#  virtuellen Anzeige (Xvfb), unter Windows direkt (Git-Bash des Runners).
#
#  Aufruf:  bash pruefung/ci_tests.sh TEIL
#    spiel    test_spiel.py (dauert allein ca. 4-5 min)
#    lang     die langen Laeufe: Beenden, Leistung, grosse Datenmengen, Vorladen
#    rest     alle uebrigen test_*.py (neue Testdateien landen automatisch hier)
#    windows  Auswahl fuer den Windows-Runner (Windows-eigene Wege; ab 0.62.4
#             auch der Abgleich-Kern, test_abgleich.py laeuft dort nicht)
#    ibus     ab 0.63.2 (B-A-01): test_eingabe.py mit FISI_TEST_IBUS=1, also mit
#             den Nachstellungstests mit echtem IBus (braucht ibus, dbus-x11).
#             Fehlt ein Werkzeug, ist der Teil rot statt still "skipped".
#
#  Lokal genauso nutzbar, z.B.:  bash pruefung/ci_tests.sh rest
# ============================================================================
set -u
cd "$(dirname "$0")/.."
TEIL="${1:-rest}"
PY="${PYTHON:-python}"
LANG_DATEIEN="test_beenden.py test_leistung.py test_grosse_datenmengen.py test_vorladen.py"

case "$TEIL" in
  spiel)   DATEIEN="test_spiel.py" ;;
  lang)    DATEIEN="$LANG_DATEIEN" ;;
  rest)    DATEIEN=$(ls test_*.py | grep -v -x -e test_spiel.py \
                     $(for d in $LANG_DATEIEN; do echo "-e $d"; done)) ;;
  windows) DATEIEN="test_einzelstart.py test_haenger.py test_update.py test_update_fenster.py
                    test_leistung.py test_werkzeuge.py test_optionen.py test_sicherung.py
                    test_beenden.py test_namen.py test_rechtliches.py
                    test_optionen_0622.py test_reiter_sichtbar.py test_abgleich_kern.py" ;;
  ibus)    DATEIEN="test_eingabe.py"
           export FISI_TEST_IBUS=1
           # kurzer Zwischenspeicher-Pfad fuer IBus (Stolperstein aus 0.62.4)
           XDG_CACHE_HOME=$(mktemp -d /tmp/ibus.XXXXXX)
           export XDG_CACHE_HOME ;;
  *) echo "Unbekannter Teil: $TEIL"; exit 2 ;;
esac

# Linux: eine Anzeige fuer den ganzen Teil (wie am Bildschirm 1920x1080)
if [ "$(uname -s)" = "Linux" ] && [ -z "${DISPLAY:-}" ]; then
  # freie Nummer suchen (eine eben beendete Anzeige kann ihre Sperre noch halten)
  NR=99
  while [ -e /tmp/.X$NR-lock ]; do NR=$((NR + 1)); done
  Xvfb :$NR -screen 0 1920x1080x24 >/dev/null 2>&1 &
  XVFB=$!
  export DISPLAY=:$NR
  for _ in 1 2 3 4 5 6 7 8 9 10; do
    xdpyinfo >/dev/null 2>&1 && break
    sleep 1
  done
  trap 'kill $XVFB 2>/dev/null' EXIT
fi

# Ab 0.63.2 (CI-Befund ibus, nur Diagnose): Werkzeugstand fuer den Teil
# "ibus" ausgeben. Keine Zugangsdaten, kein Pfad einer virtuellen Umgebung;
# das Heimatverzeichnis erscheint als "~". Bricht nichts ab (kein -e).
# "useinputmethods" zeigt, ob Tk Eingabemethoden eingeschaltet hat (ohne IBus
# gemessen), nicht ob Tk im Test eine oeffnet. ldd zeigt, womit _tkinter
# verknuepft ist, nicht was geladen wird.
if [ "$TEIL" = "ibus" ]; then
  echo "::group::Diagnose ibus"
  echo "LANG=${LANG:-} LC_ALL=${LC_ALL:-} LC_CTYPE=${LC_CTYPE:-}"
  ibus version 2>&1 | head -1
  "$PY" - <<'DIAG' 2>&1 | sed "s#$HOME#~#g"
import os, subprocess, sys, locale, tkinter, _tkinter
print("python", sys.version.split()[0], "Basis", sys.base_prefix)
print("locale", locale.setlocale(locale.LC_CTYPE, ""), locale.getpreferredencoding(False))
print("tk", tkinter.Tcl().eval("info patchlevel"), _tkinter.__file__)
for zeile in subprocess.run(["ldd", _tkinter.__file__], capture_output=True,
                            text=True).stdout.splitlines():
    if any(n in zeile for n in ("libtk", "libtcl", "libX11")):
        print("  verknuepft:", zeile.strip())
root = tkinter.Tk()
print("tk useinputmethods (eingeschaltet, ohne IBus gemessen)",
      root.tk.call("tk", "useinputmethods"))
root.destroy()
DIAG
  # Gibt es ein System-Python mit Tk? (nur Befund, der Test laeuft mit $PY)
  if [ -x /usr/bin/python3 ]; then
    echo "System-Python: /usr/bin/python3 -> $(readlink -f /usr/bin/python3)"
    /usr/bin/python3 - <<'SYSPY' 2>&1 | sed "s#$HOME#~#g"
import sys
print("System-Python Version", sys.version.split()[0])
try:
    import tkinter
    print("System-Python import tkinter: ja, Tk", tkinter.Tcl().eval("info patchlevel"))
except Exception as fehler:
    print("System-Python import tkinter: nein,", type(fehler).__name__, fehler)
SYSPY
  else
    echo "System-Python: /usr/bin/python3 fehlt"
  fi
  echo "::endgroup::"
fi

ROT=""
ZUSAMMEN=0
for DATEI in $DATEIEN; do
  echo "::group::$DATEI"
  WM=""
  # Der Minimieren-Test in test_einzelstart braucht einen Fenstermanager
  if [ "$DATEI" = "test_einzelstart.py" ] && [ "$(uname -s)" = "Linux" ] && command -v openbox >/dev/null; then
    openbox >/dev/null 2>&1 &
    WM=$!
    sleep 1
  fi
  START=$(date +%s)
  "$PY" "$DATEI"
  RC=$?
  DAUER=$(( $(date +%s) - START ))
  ZUSAMMEN=$(( ZUSAMMEN + DAUER ))
  if [ -n "$WM" ]; then kill "$WM" 2>/dev/null; wait "$WM" 2>/dev/null; fi
  echo "::endgroup::"
  if [ $RC -eq 0 ]; then
    echo "OK   $DATEI (${DAUER} s)"
  else
    echo "ROT  $DATEI (${DAUER} s, Rueckgabe $RC)"
    ROT="$ROT $DATEI"
  fi
  if [ -n "${GITHUB_STEP_SUMMARY:-}" ]; then
    if [ $RC -eq 0 ]; then Z="gruen"; else Z="**rot**"; fi
    echo "- \`$DATEI\`: $Z (${DAUER} s)" >> "$GITHUB_STEP_SUMMARY"
  fi
done

# Ab 0.63.2 (FG-90, dritter IBus-Diagnose-Lauf): nur Diagnose, erst NACH den
# Tests. Kein -e, kein Abbruch: jeder Rueckgabewert wird nur ausgegeben, ROT
# und der Exit-Code am Ende kommen allein aus den Tests oben.
# Zeitgrenzen je Versuch (timeout): (1) Python pruefen 30 s, venv 120 s,
# Pakete 600 s, Test 180 s; (2) 30 s + 180 s; (3) 90 s; dazu je 10 s
# Nachfrist (-k 10). Das sind hoechstens rund 22 min zusaetzlich; der Teil
# selbst braucht bisher rund 1 min, die 30 min des Jobs reichen also.
# Erwartete Zusatzdauer: rund 2 min (Pakete laden, 2 x Nachstellung je rund
# 25 s, Versuch 3 rund 5 s; im Container ohne Versuch 1 gemessen: rund 30 s).
# Ausgaben gehen erst in eine Datei und werden dann mit "~" fuer das
# Heimatverzeichnis gezeigt.
if [ "$TEIL" = "ibus" ]; then
  echo "::group::Diagnose, ohne Einfluss auf das Ergebnis"
  DIAG=$(mktemp -d /tmp/fg90.XXXXXX)
  zeige() { sed "s#$HOME#~#g" "$1"; }
  echo "Heimatverzeichnis: $HOME" | sed "s#$HOME#~#g"
  echo "Bedeutung: OK = Tk haengt ohne Umgehung (wie im Container);"
  echo "           FAIL 'True is not false' = Tk haengt nicht (wie bisher auf GitHub)"

  echo "--- Versuch 1: System-Python /usr/bin/python3 mit python3-tk, eigene venv"
  timeout -k 10 30 /usr/bin/python3 -c "import sys, tkinter; print('System-Python', sys.version.split()[0], 'Tk', tkinter.Tcl().eval('info patchlevel'))" > "$DIAG/1a.log" 2>&1
  RC1=$?
  echo "Rueckgabe Python/Tk pruefen: $RC1"; zeige "$DIAG/1a.log"
  if [ "$RC1" -ne 0 ]; then
    echo "Versuch 1 endet hier: System-Python ohne tkinter (python3-tk fehlt?)"
  else
    # --without-pip: braucht kein ensurepip, also kein Paket python3.12-venv;
    # die Pakete installiert das pip des normalen Python in die venv (--python)
    timeout -k 10 120 /usr/bin/python3 -m venv --without-pip "$DIAG/venv" > "$DIAG/1b.log" 2>&1
    echo "Rueckgabe venv anlegen: $?"; zeige "$DIAG/1b.log"
    timeout -k 10 600 "$PY" -m pip --python "$DIAG/venv/bin/python" install -q \
      -r requirements.txt psutil > "$DIAG/1c.log" 2>&1
    echo "Rueckgabe Pakete: $?"; tail -n 20 "$DIAG/1c.log" | sed "s#$HOME#~#g"
    timeout -k 10 180 "$DIAG/venv/bin/python" test_eingabe.py \
      NachstellungTest.test_ohne_umgehung_haengt_tk > "$DIAG/1d.log" 2>&1
    echo "Rueckgabe Test ohne Umgehung (System-Python): $?"
    tail -n 25 "$DIAG/1d.log" | sed "s#$HOME#~#g"
  fi

  # Hinweis: Bei leerem LANG setzt Python 3.12 selbst LC_CTYPE=C.UTF-8 (PEP 538)
  # und gibt das an das Tk-Fenster weiter; die Zeile "LC_CTYPE" zeigt das.
  echo "--- Versuch 2: normales Python ohne LD_LIBRARY_PATH, LANG leer"
  timeout -k 10 30 env -u LD_LIBRARY_PATH LANG= "$PY" -c "import sys, locale; print('Python', sys.version.split()[0], 'LC_CTYPE', locale.setlocale(locale.LC_CTYPE, ''))" > "$DIAG/2a.log" 2>&1
  echo "Rueckgabe Python-Start: $?"; zeige "$DIAG/2a.log"
  timeout -k 10 180 env -u LD_LIBRARY_PATH LANG= "$PY" test_eingabe.py \
    NachstellungTest.test_ohne_umgehung_haengt_tk > "$DIAG/2b.log" 2>&1
  echo "Rueckgabe Test ohne Umgehung (ohne LD_LIBRARY_PATH, LANG leer): $?"
  tail -n 25 "$DIAG/2b.log" | sed "s#$HOME#~#g"

  echo "--- Versuch 3: IBus-Prozesse und Bus der Fensteranbindung (ibus-x11)"
  timeout -k 10 90 "$PY" - > "$DIAG/3.log" 2>&1 <<'BUS'
import glob, os, re, shutil, signal, subprocess, time

def prozesse():
    liste = []
    for d in glob.glob("/proc/[0-9]*"):
        try:
            name = open(d + "/comm").read().strip()
            argv = open(d + "/cmdline", "rb").read().split(b"\0")
            stat = open(d + "/stat").read().rsplit(")", 1)[1].split()
        except OSError:
            continue
        if "ibus" in name or "dbus" in name:
            args = [os.path.basename(a.decode(errors="replace")) if i == 0
                    else a.decode(errors="replace") for i, a in enumerate(argv) if a]
            liste.append((int(d[6:]), name, stat[0], int(stat[2]), " ".join(args) or name))
    return sorted(liste)

def zeigen(titel):
    print(titel)
    for pid, name, zustand, gruppe, args in prozesse():
        print("  pid %d Gruppe %d Zustand %s  %s" % (pid, gruppe, zustand, args))

zeigen("IBus/DBus-Prozesse vor dem Start:")
env = dict(os.environ)
aus = subprocess.run(["dbus-launch", "--sh-syntax"], capture_output=True, text=True).stdout
for key, value in re.findall(r"(DBUS_SESSION_BUS_\w+)='?([^';]+)'?;", aus):
    env[key] = value
daemon = subprocess.Popen(["ibus-daemon", "--xim", "--replace"], env=env,
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                          process_group=0)
try:
    for _ in range(150):
        if "@server=ibus" in subprocess.run(["xprop", "-root", "XIM_SERVERS"],
                                            capture_output=True, text=True).stdout:
            break
        time.sleep(0.1)
    print("ibus-daemon pid %d, XIM-Server da: %s" % (daemon.pid, "@server=ibus" in subprocess.run(
        ["xprop", "-root", "XIM_SERVERS"], capture_output=True, text=True).stdout))
    zeigen("IBus/DBus-Prozesse mit eigenem ibus-daemon:")
    x11 = [p for p in prozesse() if p[1] == "ibus-x11" and p[2] != "Z"]
    for pid, *_ in x11:
        try:
            umg = dict(z.split("=", 1) for z in open("/proc/%d/environ" % pid).read().split("\0") if "=" in z)
        except OSError as fehler:
            umg = {}
            print("ibus-x11 pid %d: Umgebung nicht lesbar (%s)" % (pid, fehler))
        for key in ("IBUS_ADDRESS", "DBUS_SESSION_BUS_ADDRESS", "DISPLAY"):
            print("ibus-x11 pid %d %s=%s" % (pid, key, umg.get(key, "(nicht gesetzt)")))
    print("Sitzungsbus dieses Versuchs:", env.get("DBUS_SESSION_BUS_ADDRESS"))
    for datei in sorted(glob.glob(os.path.expanduser("~/.config/ibus/bus/*"))):
        inhalt = [z for z in open(datei).read().splitlines() if z.startswith("IBUS_")]
        print("Bus-Datei", datei, "->", "; ".join(inhalt))
    if shutil.which("ss"):
        try:
            zeilen = subprocess.run(["ss", "-xpn"], capture_output=True,
                                    text=True).stdout.splitlines()[1:]
            knoten = {}
            for z in zeilen:
                t = z.split()
                if len(t) < 8:
                    continue
                m = re.search(r'\(\("([^"]+)",pid=(\d+)', z)
                knoten[t[5]] = (t[4], t[7], m.group(1) if m else "?",
                                int(m.group(2)) if m else 0)
            for inode, (pfad, gegen, name, pid) in sorted(knoten.items()):
                if name == "ibus-x11":
                    g = knoten.get(gegen, ("?", "?", "(unbekannt)", 0))
                    print("ibus-x11 pid %d verbunden mit %s pid %d %s" % (pid, g[2], g[3], g[0]))
        except Exception as fehler:
            print("ss nicht auswertbar:", type(fehler).__name__, fehler)
    else:
        print("ss fehlt: Verbindungen von ibus-x11 nicht ermittelt")
    os.kill(daemon.pid, signal.SIGSTOP)
    time.sleep(1)
    zeigen("Zustand nach SIGSTOP des eigenen ibus-daemon (T = angehalten):")
finally:
    os.kill(daemon.pid, signal.SIGCONT)
    subprocess.run(["pkill", "-g", str(daemon.pid), "-x", "ibus-x11"], check=False)
    daemon.terminate()
    try:
        daemon.wait(timeout=5)
    except subprocess.TimeoutExpired:
        daemon.kill()
    if env.get("DBUS_SESSION_BUS_PID"):
        os.kill(int(env["DBUS_SESSION_BUS_PID"]), signal.SIGTERM)
BUS
  echo "Rueckgabe Versuch 3: $?"; zeige "$DIAG/3.log"
  echo "::endgroup::"
fi

echo "Teil $TEIL: zusammen ${ZUSAMMEN} s"
if [ -n "$ROT" ]; then
  echo "Rote Testdateien:$ROT"
  exit 1
fi
echo "Alle Testdateien gruen."
