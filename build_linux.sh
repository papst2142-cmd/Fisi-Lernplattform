#!/usr/bin/env bash
# ===========================================================================
#  FISI Lernplattform - Erstellt eine eigenstaendige Linux-Anwendung
# ===========================================================================
#  Ergebnis: dist/FISI-Lernplattform
#  Diese Datei laeuft ohne installiertes Python auf vergleichbaren Systemen.
# ===========================================================================

set -euo pipefail
cd "$(dirname "$(readlink -f "$0")")"

GRUEN='\033[0;32m'; ROT='\033[0;31m'; GELB='\033[1;33m'; AUS='\033[0m'
ok()   { echo -e "${GRUEN}[OK]${AUS} $1"; }
info() { echo -e "${GELB}[..]${AUS} $1"; }
fehler() { echo -e "${ROT}[FEHLER]${AUS} $1" >&2; exit 1; }

echo
echo "==========================================================="
echo "  FISI Lernplattform - Linux-Paket wird erstellt"
echo "==========================================================="
echo

# --- 1. Python vorhanden? --------------------------------------------------
command -v python3 >/dev/null 2>&1 || fehler "python3 wurde nicht gefunden.
Bitte nachinstallieren, z.B. mit: sudo apt install python3"
ok "$(python3 --version) gefunden"

python3 - <<'PY' || fehler "Python 3.8 oder neuer wird benoetigt."
import sys
sys.exit(0 if sys.version_info >= (3, 8) else 1)
PY

# --- 2. Tkinter vorhanden? -------------------------------------------------
if ! python3 -c "import tkinter" >/dev/null 2>&1; then
    fehler "Tkinter fehlt.
Bitte nachinstallieren:
  Debian/Ubuntu : sudo apt install python3-tk
  Fedora        : sudo dnf install python3-tkinter
  Arch          : sudo pacman -S tk"
fi
ok "Tkinter vorhanden"

# --- 3. PyInstaller bereitstellen ------------------------------------------
if ! python3 -c "import PyInstaller" >/dev/null 2>&1; then
    info "PyInstaller wird installiert ..."
    python3 -m pip install --user --upgrade pyinstaller \
        || python3 -m pip install --user --break-system-packages --upgrade pyinstaller \
        || fehler "PyInstaller konnte nicht installiert werden.
Alternativ ueber die Paketverwaltung: sudo apt install pyinstaller"
fi
ok "PyInstaller bereit"

# --- 4. Alte Ergebnisse entfernen ------------------------------------------
rm -rf build dist FISI-Lernplattform.spec

# --- 5. Anwendung bauen ----------------------------------------------------
echo
info "Anwendung wird gebaut, das dauert ein bis zwei Minuten ..."
echo

python3 -m PyInstaller \
    --name "FISI-Lernplattform" \
    --onefile \
    --windowed \
    --noconfirm \
    --clean \
    --add-data "fisi_core.py:." \
    --add-data "fisi_widgets.py:." \
    --add-data "app_gui.py:." \
    start.py

[ -f dist/FISI-Lernplattform ] || fehler "Der Build ist fehlgeschlagen."
chmod +x dist/FISI-Lernplattform

echo
echo "==========================================================="
echo "  Fertig"
echo "==========================================================="
echo
echo "  Die Anwendung liegt hier:"
echo "  $(pwd)/dist/FISI-Lernplattform"
echo
echo "  Start per Doppelklick oder im Terminal mit:"
echo "  ./dist/FISI-Lernplattform"
echo
echo "  Ins Startmenue eintragen (optional):"
echo "  ./install_linux.sh"
echo
echo "  Die Lernfortschritte werden gespeichert unter:"
echo "  ~/.local/share/fisi-lernplattform/fisi_lernplattform.db"
echo
