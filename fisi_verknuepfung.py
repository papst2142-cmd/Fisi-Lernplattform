#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FISI Lernplattform - Desktop-Verknuepfung unter Linux (ab 0.59)
================================================================

Die .deb legt einen Eintrag im Anwendungsmenue an, das AppImage gar nichts.
Eine Verknuepfung auf dem Desktop ("Schreibtisch") legt deshalb fuer beide
Formate das Programm selbst an:

- beim ersten Start unter Linux mit Rueckfrage (Ja / Nein / Nicht mehr fragen)
- jederzeit ueber den Knopf "Desktop-Verknuepfung anlegen" in den Optionen
  (nur unter Linux sichtbar). Der Knopf erneuert eine vorhandene Verknuepfung
  (z.B. nachdem das AppImage verschoben wurde) - es entsteht nie eine zweite.

Der Desktop-Ordner kommt aus "xdg-user-dir DESKTOP" (je nach Sprache
~/Schreibtisch oder ~/Desktop). Gibt es keinen, wird nichts angelegt.
GNOME startet Verknuepfungen auf dem Desktop erst, wenn sie als
vertrauenswuerdig markiert sind (gio set ... metadata::trusted true); KDE
reicht das Ausfuehrrecht. Es wird nichts ausserhalb des Benutzerordners
geschrieben. Windows, macOS und Android sind nicht betroffen.
"""

import os
import shutil
import subprocess
import sys

import fisi_update

FILE_NAME = "fisi-lernplattform.desktop"
ICON_NAME = "fisi-lernplattform"
DEB_COMMAND = "/usr/bin/fisi-lernplattform"
MARKER = "X-FISI-Verknuepfung=true"
# Merker in einstellungen.json: "fragen" (Standard), "nie", "erledigt"
SETTING = "desktop_verknuepfung"

BTN_CREATE = "Desktop-Verknüpfung anlegen"
ASK_TITLE = "Desktop-Verknüpfung"
ASK_TEXT = ("Soll eine Verknüpfung zur FISI Lernplattform auf dem Desktop angelegt "
            "werden? Du kannst sie später auch in den Optionen unter „Updates“ anlegen.")
BTN_YES = "Ja"
BTN_NO = "Nein"
BTN_NEVER = "Nicht mehr fragen"
MSG_CREATED = "Verknüpfung angelegt: %s"
MSG_RENEWED = "Verknüpfung erneuert: %s"
MSG_NO_DESKTOP = ("Es wurde kein Desktop-Ordner gefunden. Die Verknüpfung wurde nicht "
                  "angelegt.")
MSG_FAILED = "Die Verknüpfung konnte nicht angelegt werden: %s"
MSG_UNSURE = ("\nFalls sie sich nicht per Doppelklick starten lässt: Rechtsklick und "
              "„Start erlauben“ wählen.")
MSG_EXISTS = "Auf dem Desktop liegt eine Verknüpfung."
MSG_NONE = "Noch keine Verknüpfung auf dem Desktop."

ENTRY = """[Desktop Entry]
Type=Application
Name=FISI Lernplattform
Comment=Lernprogramm fuer die Umschulung zum Fachinformatiker Systemintegration
Exec={exec}
Icon={icon}
Terminal=false
Categories=Education;
Keywords=FISI;IHK;Lernen;Netzwerk;Subnetting;RAID;
{marker}
"""


def kind():
    """'deb', 'appimage' oder None (Quellcode, andere Systeme)."""
    if not sys.platform.startswith("linux"):
        return None
    current = fisi_update.install_kind()
    return current if current in ("deb", "appimage") else None


def supported(current=None):
    """Knopf und Rueckfrage nur unter Linux in der installierten Fassung."""
    return (current or kind()) in ("deb", "appimage")


def _home():
    return os.path.expanduser("~")


def desktop_dir():
    """Desktop-Ordner des Benutzers oder None, wenn es keinen gibt.
    xdg-user-dir liefert den Ordner in der Sprache des Systems; ist keiner
    eingerichtet, gibt es den Benutzerordner selbst zurueck - der zaehlt
    nicht als Desktop."""
    home = _home()
    path = None
    try:
        result = subprocess.run(["xdg-user-dir", "DESKTOP"], capture_output=True,
                                text=True, timeout=5)
        if result.returncode == 0:
            path = result.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        path = None
    if not path:
        path = _from_user_dirs(home)
    if not path:
        path = os.path.join(home, "Desktop")
    path = os.path.abspath(os.path.expanduser(path))
    if os.path.normpath(path) == os.path.normpath(home) or not os.path.isdir(path):
        return None
    return path


def _from_user_dirs(home):
    """Ersatzweg ohne xdg-user-dir: ~/.config/user-dirs.dirs lesen."""
    config = os.environ.get("XDG_CONFIG_HOME") or os.path.join(home, ".config")
    try:
        with open(os.path.join(config, "user-dirs.dirs"), encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if line.startswith("XDG_DESKTOP_DIR="):
                    value = line.split("=", 1)[1].strip().strip('"')
                    return value.replace("$HOME", home)
    except OSError:
        return None
    return None


def quote_exec(path):
    """Pfad fuer die Zeile Exec= (Desktop-Entry-Spezifikation): bei Leer- oder
    Sonderzeichen in Anfuehrungszeichen, mit Schraegstrich vor " ` $ \\."""
    special = set(' \t\n"\'\\><~|&;$*?#()`')
    if not any(char in special for char in path):
        return path
    escaped = "".join("\\" + char if char in '"`$\\' else char for char in path)
    return '"%s"' % escaped


def target(current=None):
    """Was die Verknuepfung startet: bei der .deb der Befehl, beim AppImage
    die Datei an ihrem aktuellen Ort."""
    current = current or kind()
    if current == "appimage":
        return os.environ.get("APPIMAGE", "")
    if current == "deb":
        return DEB_COMMAND
    return ""


def icon_path(current=None, source=None):
    """Symbol: bei der .deb das installierte Symbol (Name), beim AppImage
    eine Kopie im Benutzerordner (fester Pfad, auch wenn das AppImage
    wandert)."""
    current = current or kind()
    if current == "deb":
        return ICON_NAME
    source = source or os.path.join(getattr(sys, "_MEIPASS", os.path.dirname(
        os.path.abspath(__file__))), "icon.png")
    data = os.environ.get("XDG_DATA_HOME") or os.path.join(_home(), ".local", "share")
    folder = os.path.join(data, "icons", "hicolor", "512x512", "apps")
    copy = os.path.join(folder, ICON_NAME + ".png")
    try:
        os.makedirs(folder, exist_ok=True)
        shutil.copyfile(source, copy)
    except OSError:
        return ICON_NAME
    return copy


def entry_text(exec_path, icon):
    return ENTRY.format(exec=quote_exec(exec_path), icon=icon, marker=MARKER)


def shortcut_path(folder=None):
    folder = folder or desktop_dir()
    return os.path.join(folder, FILE_NAME) if folder else None


def exists():
    path = shortcut_path()
    return bool(path) and os.path.isfile(path)


def desktop_session():
    """Erkannter Desktop: 'gnome', 'kde' oder 'andere' (XDG_CURRENT_DESKTOP)."""
    names = os.environ.get("XDG_CURRENT_DESKTOP", "").lower()
    if "gnome" in names or "unity" in names or "ubuntu" in names:
        return "gnome"
    if "kde" in names or "plasma" in names:
        return "kde"
    return "andere"


def _trust(path, session):
    """GNOME: als vertrauenswuerdig markieren. True, wenn sicher erledigt."""
    if session != "gnome":
        return session == "kde"   # KDE: Ausfuehrrecht genuegt
    try:
        result = subprocess.run(["gio", "set", path, "metadata::trusted", "true"],
                                capture_output=True, timeout=5)
        return result.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def create(current=None, folder=None, icon_source=None):
    """Legt die Verknuepfung an oder erneuert sie (gleicher Dateiname, also
    nie doppelt). Ergebnis: (status, pfad, sicher) mit status 'neu',
    'erneuert', 'kein_desktop' oder 'fehler' (pfad = Fehlertext)."""
    current = current or kind()
    folder = folder or desktop_dir()
    if not folder:
        return "kein_desktop", None, False
    exec_path = target(current)
    if not exec_path:
        return "fehler", "Programmdatei unbekannt", False
    path = os.path.join(folder, FILE_NAME)
    renewed = os.path.isfile(path)
    temp = path + ".tmp"
    try:
        with open(temp, "w", encoding="utf-8") as handle:
            handle.write(entry_text(exec_path, icon_path(current, icon_source)))
        os.chmod(temp, 0o755)   # Ausfuehrrecht: GNOME und KDE verlangen es
        os.replace(temp, path)
    except OSError as error:
        try:
            os.remove(temp)
        except OSError:
            pass
        return "fehler", str(error), False
    sure = _trust(path, desktop_session())
    return ("erneuert" if renewed else "neu"), path, sure


def message(result):
    status, path, sure = result
    if status == "kein_desktop":
        return MSG_NO_DESKTOP
    if status == "fehler":
        return MSG_FAILED % path
    text = (MSG_RENEWED if status == "erneuert" else MSG_CREATED) % path
    return text if sure else text + MSG_UNSURE


def create_and_report(current=None):
    result = create(current)
    if result[0] in ("neu", "erneuert"):
        set_answer("erledigt")
    return message(result)


def status_text():
    return MSG_EXISTS if exists() else MSG_NONE


# -- Rueckfrage beim ersten Start --------------------------------------------

def answer():
    value = fisi_update.load_settings().get(SETTING, "fragen")
    return value if value in ("fragen", "nie", "erledigt") else "fragen"


def set_answer(value):
    settings = fisi_update.load_settings()
    settings[SETTING] = value
    fisi_update.save_settings(settings)


def should_ask(current=None):
    """Fragen, solange weder "Ja" noch "Nicht mehr fragen" gewaehlt wurde und
    keine Verknuepfung auf dem Desktop liegt ("Nein" fragt beim naechsten
    Start wieder)."""
    if not supported(current) or answer() != "fragen":
        return False
    folder = desktop_dir()
    return bool(folder) and not os.path.isfile(os.path.join(folder, FILE_NAME))
