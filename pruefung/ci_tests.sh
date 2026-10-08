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
#    windows  Auswahl fuer den Windows-Runner (Windows-eigene Wege)
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
                    test_beenden.py" ;;
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
