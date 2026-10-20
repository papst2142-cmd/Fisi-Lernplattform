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
#    breite   ab 0.63.2 (FG-96): die Breitentests (Ansichten, Rechner-Seite,
#             Spiel); vorher Teil von "rest"
#    rest     alle uebrigen test_*.py (neue Testdateien landen automatisch hier)
#    rest2    ab 0.63.2 (FG-113): lange Dateien (Abgleich, Anzeige-Seiten);
#             vorher Teil von "rest"
#    breite2  ab 0.63.2 (FG-122): Breitentest des Spiels; vorher Teil von "breite"
#    rest3    ab 0.63.2 (FG-122): Anzeige-/Breitentests aus N8; vorher Teil von "rest"
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
# Ab 0.63.2 (FG-96): Fehlt eine dieser Dateien im Stand, laeuft sie nirgends
# (sie gehoert nie zu "rest"); test_ci_teile_0632.py prueft die Zuordnung.
BREITE_DATEIEN="test_ansichten_breite.py test_rechner_seite_breite.py"
# Ab 0.63.2 (FG-122): "breite" und "rest" lagen auf GitHub ueber der Zeitgrenze
# von 30 min (Lauf 38938085051 abgebrochen); diese Dateien laufen in eigenen Teilen
BREITE2_DATEIEN="test_spiel_breite_0632.py"
REST3_DATEIEN="test_anzeige_tastatur_0632.py test_listentitel_breite_0632.py test_startzeilen_breite_0632.py test_suchfeld_rahmen_0632.py test_trainer_breite_0632.py"
# Ab 0.63.2 (FG-113): "rest" war zu lang (1441 s); diese Dateien laufen in "rest2"
# (test_abgleich_0632.py kommt mit S6a; fehlt eine im Stand, laeuft sie nirgends).
REST2_DATEIEN="test_abgleich.py test_abgleich_0632.py test_anzeige_pc_0632.py test_spielstand_inkrementell.py test_trainer_richtig_waere_pc.py"

case "$TEIL" in
  spiel)   DATEIEN="test_spiel.py" ;;
  lang)    DATEIEN="$LANG_DATEIEN" ;;
  breite)  DATEIEN=$(for d in $BREITE_DATEIEN; do [ -e "$d" ] && echo "$d"; done) ;;
  rest2)   DATEIEN=$(for d in $REST2_DATEIEN; do [ -e "$d" ] && echo "$d"; done) ;;
  breite2) DATEIEN=$(for d in $BREITE2_DATEIEN; do [ -e "$d" ] && echo "$d"; done) ;;
  rest3)   DATEIEN=$(for d in $REST3_DATEIEN; do [ -e "$d" ] && echo "$d"; done) ;;
  rest)    DATEIEN=$(ls test_*.py | grep -v -x -e test_spiel.py \
                     $(for d in $LANG_DATEIEN $BREITE_DATEIEN $BREITE2_DATEIEN $REST2_DATEIEN $REST3_DATEIEN; do echo "-e $d"; done)) ;;
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

echo "Teil $TEIL: zusammen ${ZUSAMMEN} s"
if [ -n "$ROT" ]; then
  echo "Rote Testdateien:$ROT"
  exit 1
fi
echo "Alle Testdateien gruen."
