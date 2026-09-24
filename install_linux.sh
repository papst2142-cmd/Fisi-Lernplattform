#!/usr/bin/env bash
# ===========================================================================
#  FISI Lernplattform - Installation ins Benutzerverzeichnis
# ===========================================================================
#  Traegt das Programm ins Startmenue ein. Es wird kein root benoetigt,
#  alles landet unterhalb von ~/.local.
#
#  Aufruf:   ./install_linux.sh            (installieren)
#            ./install_linux.sh --entfernen  (wieder entfernen)
# ===========================================================================

set -euo pipefail
QUELLE="$(dirname "$(readlink -f "$0")")"

ZIEL="$HOME/.local/share/fisi-lernplattform/programm"
BIN="$HOME/.local/bin"
DESKTOP="$HOME/.local/share/applications/fisi-lernplattform.desktop"
ICON_DIR="$HOME/.local/share/icons/hicolor/scalable/apps"
ICON="$ICON_DIR/fisi-lernplattform.svg"

GRUEN='\033[0;32m'; ROT='\033[0;31m'; AUS='\033[0m'
ok()     { echo -e "${GRUEN}[OK]${AUS} $1"; }
fehler() { echo -e "${ROT}[FEHLER]${AUS} $1" >&2; exit 1; }

# --- Entfernen --------------------------------------------------------------
if [ "${1:-}" = "--entfernen" ] || [ "${1:-}" = "--uninstall" ]; then
    rm -rf "$ZIEL"
    rm -f "$BIN/fisi-lernplattform" "$DESKTOP" "$ICON"
    command -v update-desktop-database >/dev/null 2>&1 \
        && update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true
    ok "Programm entfernt."
    echo
    echo "Die Lernfortschritte bleiben erhalten unter:"
    echo "  ~/.local/share/fisi-lernplattform/fisi_lernplattform.db"
    echo "Zum vollstaendigen Loeschen diesen Ordner entfernen."
    exit 0
fi

# --- Voraussetzungen --------------------------------------------------------
command -v python3 >/dev/null 2>&1 || fehler "python3 wurde nicht gefunden.
Bitte nachinstallieren: sudo apt install python3"

python3 -c "import tkinter" >/dev/null 2>&1 || fehler "Tkinter fehlt.
Bitte nachinstallieren:
  Debian/Ubuntu : sudo apt install python3-tk
  Fedora        : sudo dnf install python3-tkinter
  Arch          : sudo pacman -S tk"
ok "Python und Tkinter vorhanden"

# --- Dateien kopieren -------------------------------------------------------
mkdir -p "$ZIEL" "$BIN" "$ICON_DIR" "$(dirname "$DESKTOP")"
for datei in start.py app_gui.py fisi_core.py fisi_widgets.py; do
    [ -f "$QUELLE/$datei" ] || fehler "Datei fehlt: $datei"
    cp "$QUELLE/$datei" "$ZIEL/"
done
ok "Programmdateien kopiert nach $ZIEL"

# --- Startbefehl ------------------------------------------------------------
cat > "$BIN/fisi-lernplattform" <<EOF
#!/usr/bin/env bash
exec python3 "$ZIEL/start.py" "\$@"
EOF
chmod +x "$BIN/fisi-lernplattform"
ok "Startbefehl angelegt: fisi-lernplattform"

# --- Symbol -----------------------------------------------------------------
cat > "$ICON" <<'EOF'
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="64" height="64">
  <rect width="64" height="64" rx="14" fill="#160C2A"/>
  <circle cx="32" cy="32" r="19" fill="none" stroke="#22D3EE" stroke-width="4"/>
  <circle cx="32" cy="32" r="8" fill="#F472B6"/>
</svg>
EOF
ok "Symbol installiert"

# --- Startmenue-Eintrag -----------------------------------------------------
cat > "$DESKTOP" <<EOF
[Desktop Entry]
Type=Application
Name=FISI Lernplattform
Comment=Lernprogramm fuer die Umschulung zum Fachinformatiker Systemintegration
Exec=$BIN/fisi-lernplattform
Icon=fisi-lernplattform
Terminal=false
Categories=Education;Science;
Keywords=FISI;IHK;Lernen;Netzwerk;Subnetting;RAID;
EOF
chmod +x "$DESKTOP"
command -v update-desktop-database >/dev/null 2>&1 \
    && update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true
ok "Startmenue-Eintrag angelegt"

echo
echo "==========================================================="
echo "  Installation abgeschlossen"
echo "==========================================================="
echo
echo "  Start ueber das Startmenue (\"FISI Lernplattform\")"
echo "  oder im Terminal mit:  fisi-lernplattform"
echo
if ! echo "$PATH" | tr ':' '\n' | grep -qx "$BIN"; then
    echo "  Hinweis: $BIN liegt nicht im PATH."
    echo "  Diese Zeile in ~/.bashrc ergaenzen:"
    echo "      export PATH=\"\$HOME/.local/bin:\$PATH\""
    echo
fi
echo "  Lernfortschritte werden gespeichert unter:"
echo "  ~/.local/share/fisi-lernplattform/fisi_lernplattform.db"
echo
echo "  Entfernen mit:  ./install_linux.sh --entfernen"
echo
