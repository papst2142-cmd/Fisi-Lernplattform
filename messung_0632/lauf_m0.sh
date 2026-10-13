#!/bin/bash
# 0.63.2 A13 M0 (Container, Linux, Xvfb): 5 Runden abwechselnd 0625/0631,
# profil_oeffnen.py MESS_ART=teile ohne Vorladen, dazu je Stand 2 cProfile-Laeufe.
# Aufruf: bash lauf_m0.sh ST_0625 ST_0631 ZIELORDNER   (nur Messzweig messung-0632)
set -u
HIER=$(cd "$(dirname "$0")" && pwd)
PY=/home/claude/venv/bin/python
A=$1; B=$2; Z=$3
mkdir -p "$Z"
lauf() {  # STAND ORDNER ART RUNDE
  f="$Z/p_$1_$3_0_$4"
  MESS_STAND=$1 MESS_ART=$3 FISI_VORLADEN=0 PATH=/home/claude/venv/bin:$PATH timeout 400 \
    xvfb-run -a -s '-screen 0 1920x1080x24' $PY "$HIER/profil_oeffnen.py" "$2" "$f.json" > "$f.txt" 2>&1 \
    || echo "Lauf $4 $1 $3 Rueckgabe $?"
  echo "$(date -u +%H:%M:%S) last $(cut -d' ' -f1 /proc/loadavg) $(grep -m1 '| oeffnen' "$f.txt")"
}
for r in 1 2 3 4 5; do
  lauf 0625 "$A" teile $r
  lauf 0631 "$B" teile $r
done
for r in 1 2; do
  lauf 0625 "$A" cprofile $r
  lauf 0631 "$B" cprofile $r
done
$PY "$HIER/teile_tabelle.py" "$Z" > "$Z/tabelle_teile.txt"
echo FERTIG
