#!/bin/bash
# F5 mit dem echten Linux-Paket: Programm starten, WARTE s warten, ueber
# WM_DELETE_WINDOW schliessen (wie das X am Fenster), dann messen, wie lange
# der Prozess noch lebt. Nach 3 s: Wartepunkte und Stapel aller Threads.
# Aufruf: f5_echt.sh PROGRAMMORDNER WARTE [ERGEBNISDATEI]
PROG="$1"; WAIT="${2:-20}"; OUT="${3:-/dev/stdout}"
DATA=$(mktemp -d /tmp/f5echt_XXXX)
S=$(dirname "$0")
FISI_DB_PATH="$DATA/test.db" "$PROG/FISI-Lernplattform" > "$DATA/ausgabe.txt" 2>&1 &
PID=$!
sleep "$WAIT"
{
echo "=== Anzeige $DISPLAY, PID $PID, Threads vor dem Schliessen:"
for t in /proc/$PID/task/*; do echo "  $(cat $t/comm) $(awk '{print $3}' $t/stat) wchan=$(cat $t/wchan)"; done
T0=$(date +%s.%N)
python3.12 "$S/wm_delete.py" fisi-lernplattform
for i in $(seq 30); do kill -0 $PID 2>/dev/null || break; sleep 0.1; done
if kill -0 $PID 2>/dev/null; then
  echo "=== 3 s nach dem Schliessen laeuft der Prozess noch. Threads:"
  for t in /proc/$PID/task/*; do echo "  $(cat $t/comm) $(awk '{print $3}' $t/stat) wchan=$(cat $t/wchan)"; done
  eu-stack -p $PID 2>/dev/null | grep -E "^TID|#[0-9]+ " | awk '/^TID/{n=0} {if (n<14) print; n++}'
fi
while kill -0 $PID 2>/dev/null; do sleep 0.1; done
T1=$(date +%s.%N)
echo "=== Prozess endete $(python3 -c "print(round($T1-$T0,2))") s nach dem Schliessen"
echo "--- fehler.log:"; cat "$DATA/fehler.log" 2>/dev/null || echo "(keine)"
} >> "$OUT"
