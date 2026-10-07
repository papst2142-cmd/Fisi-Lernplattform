#!/bin/bash
# F11: Darstellungswechsel unter mutter (headless, Wayland) + Xwayland mit
# gleichzeitigen Mausklicks und Tasten ins Fenster (xdotool), um ein Haengen
# wie bei Nico auszuloesen. Haengt die Messung laenger als GRENZE s ohne neue
# Zeile, werden Wartepunkte und Stapel aller Threads gesichert.
# Aufruf: DISPLAY=:0 XAUTHORITY=... f11_xwayland_last.sh FASSUNG ERGEBNIS.json WECHSEL [CPU%]
SRC="$1"; OUT="$(realpath -m "$2")"; N="${3:-8}"; CPU="${4:-0}"; GRENZE=${GRENZE:-120}
S=$(dirname "$0")
LOG="${OUT%.json}.log"
export MESS_STAPEL="${OUT%.json}_stapel.txt"
if [ "$CPU" != 0 ]; then
  MESS_WECHSEL=$N $S/mit_grenze.sh 0 $CPU python3.12 $S/messung_wechsel.py "$SRC" "$OUT" > "$LOG" 2>&1 &
else
  MESS_WECHSEL=$N python3.12 $S/messung_wechsel.py "$SRC" "$OUT" > "$LOG" 2>&1 &
fi
RUNNER=$!
sleep 4
PID=$(pgrep -n -f "messung_wechsel.py $SRC")
echo "Messprozess $PID"
(
  while kill -0 $PID 2>/dev/null; do
    WIN=$(xdotool search --classname fisi-lernplattform 2>/dev/null | head -1)
    if [ -n "$WIN" ]; then
      xdotool mousemove --window $WIN $((200 + RANDOM % 900)) $((150 + RANDOM % 600)) click 1 2>/dev/null
      xdotool key --window $WIN Tab 2>/dev/null
    fi
    sleep 0.3
  done
) &
CLICKER=$!
last=$(stat -c %Y "$LOG"); still=0
while kill -0 $PID 2>/dev/null; do
  sleep 2
  now=$(stat -c %Y "$LOG")
  if [ "$now" = "$last" ]; then still=$((still+2)); else still=0; last=$now; fi
  if [ $still -ge $GRENZE ]; then
    echo "=== KEINE neue Zeile seit $GRENZE s - Zustand:"
    c1=$(awk '{print $14+$15}' /proc/$PID/stat); sleep 10; c2=$(awk '{print $14+$15}' /proc/$PID/stat)
    echo "  Prozessorzeit in 10 s: $(( (c2-c1) )) Ticks (100 Ticks = 1 s)"
    for k in 1 2 3; do grep -h "" /proc/$PID/task/*/wchan | tr '\0' ' '; echo; sleep 1; done
    for t in /proc/$PID/task/*; do echo "  $(cat $t/comm) $(awk '{print $3}' $t/stat) wchan=$(cat $t/wchan)"; done
    eu-stack -p $PID 2>/dev/null | grep -E "^TID|#[0-9]+ " | awk '/^TID/{n=0} {if (n<16) print; n++}'
    kill -USR1 $PID; sleep 1; echo "--- Python-Stapel (SIGUSR1, faulthandler):"; cat "$MESS_STAPEL"
    timeout 10 xdpyinfo >/dev/null 2>&1 && echo "Xwayland antwortet anderen Programmen" || echo "Xwayland antwortet NICHT"
    kill -9 $PID
    break
  fi
done
kill $CLICKER 2>/dev/null
wait $RUNNER 2>/dev/null
grep -v "^ " "$LOG" | tail -12
