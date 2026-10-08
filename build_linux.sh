#!/usr/bin/env bash
# ===========================================================================
#  Fachinformatiker Lernplattform - Linux-Pakete lokal erstellen
# ===========================================================================
#  Ergebnis in installer_output/:
#    fisi-lernplattform_<Version>_amd64.deb        (Debian, Ubuntu, Mint ...)
#    FISI-Lernplattform-<Version>-x86_64.AppImage  (nur wenn appimagetool
#                                                   vorhanden ist)
#  Beide bringen alles mit und laufen ohne installiertes Python.
#
#  Die eigentliche Arbeit erledigt build.py. Normalerweise entstehen die
#  Pakete automatisch per GitHub Actions (siehe INSTALLER-ANLEITUNG.txt).
# ===========================================================================

set -euo pipefail
cd "$(dirname "$(readlink -f "$0")")"

GRUEN='\033[0;32m'; ROT='\033[0;31m'; GELB='\033[1;33m'; AUS='\033[0m'
ok()   { echo -e "${GRUEN}[OK]${AUS} $1"; }
info() { echo -e "${GELB}[..]${AUS} $1"; }
fehler() { echo -e "${ROT}[FEHLER]${AUS} $1" >&2; exit 1; }

echo
echo "==========================================================="
echo "  Fachinformatiker Lernplattform - Linux-Pakete werden erstellt"
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

command -v dpkg-deb >/dev/null 2>&1 || fehler "dpkg-deb fehlt (nur auf Debian-basierten Systemen vorhanden)."

# --- 3. Bibliotheken und PyInstaller bereitstellen -------------------------
info "CustomTkinter, Pillow und PyInstaller werden bereitgestellt ..."
python3 -m pip install --user --quiet -r requirements-build.txt \
    || python3 -m pip install --user --quiet --break-system-packages -r requirements-build.txt \
    || fehler "Die Bibliotheken konnten nicht installiert werden."
ok "Bibliotheken bereit"

# --- 4. Anwendung und Pakete bauen -----------------------------------------
echo
info "Das dauert ein bis zwei Minuten ..."
echo
python3 build.py

echo
echo "==========================================================="
echo "  Fertig - die Pakete liegen im Ordner installer_output"
echo "==========================================================="
echo
echo "  Installieren mit:"
echo "    sudo apt install ./installer_output/fisi-lernplattform_*.deb"
echo
echo "  Die Lernfortschritte werden gespeichert unter:"
echo "  ~/.local/share/fisi-lernplattform/fisi_lernplattform.db"
echo
