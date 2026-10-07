#!/bin/bash
# F10/F11: Startet das echte Linux-Paket 0.59.1 (entpackt) an einer Anzeige,
# wartet, bis es ruht, und zeigt je Thread den Wartepunkt (wchan) und die
# Stapel (eu-stack). Zeigt, wo die Threads im NORMALEN Ruhezustand warten -
# zum Vergleich mit Nicos Befund am haengenden Programm.
# Aufruf: f10_threads.sh PROGRAMM_ORDNER WARTEZEIT
PROG="$1"; WAIT="${2:-25}"
DATA=$(mktemp -d)
FISI_DB_PATH="$DATA/test.db" HOME="$DATA" "$PROG/FISI-Lernplattform" > "$DATA/out.txt" 2>&1 &
PID=$!
sleep "$WAIT"
echo "PID $PID, Anzeige $DISPLAY"
for t in /proc/$PID/task/*; do
  echo "Thread $(basename $t) $(cat $t/comm) Zustand $(awk '{print $3}' $t/stat) wchan=$(cat $t/wchan)"
done
eu-stack -p $PID 2>/dev/null | grep -E "^TID|#[0-9]+ " | awk '/^TID/{n=0} {if (n<9) print; n++}'
kill $PID; sleep 2; kill -9 $PID 2>/dev/null
cat "$DATA/out.txt" | tail -3
