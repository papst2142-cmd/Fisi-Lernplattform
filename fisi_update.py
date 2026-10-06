#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FISI Lernplattform - Updater
============================

Sucht auf GitHub nach einer neueren Version, laedt den passenden Installer
herunter und startet die Installation. Bewusst ohne Oberflaeche und nur mit
der Standardbibliothek (plus certifi fuer die Zertifikate), damit sich die
Logik unabhaengig vom GUI-Framework nutzen und testen laesst.

Ablauf:
  info = check_for_update("0.21")       -> UpdateInfo oder None
  path = download(info, fortschritt)     -> Pfad der heruntergeladenen Datei
  quit, text = install(path)             -> ist quit True, muss sich das
                                            Programm danach sofort beenden

Ab 0.55.1 (Windows): Jeder Schritt steht in update.log im Datenordner. Der
Installer bekommt die Prozessnummer des Programms (/WAITPID) und wartet,
bis es wirklich beendet ist, bevor er eine Datei ersetzt (siehe [Code] in
FISI-Lernplattform.iss). Beim naechsten Start prueft finish_pending_update(),
ob die neue Version laeuft - sonst meldet das Programm den Fehlschlag.
"""

import datetime
import json
import os
import platform
import re
import shlex
import shutil
import ssl
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request

from fisi_core import anonymize_paths, resolve_db_path

REPOSITORY = "papst2142-cmd/Fisi-Lernplattform"
LATEST_URL = "https://api.github.com/repos/%s/releases/latest" % REPOSITORY
RELEASES_PAGE = "https://github.com/%s/releases/latest" % REPOSITORY
USER_AGENT = "FISI-Lernplattform-Updater"


class UpdateError(Exception):
    """Fehler beim Suchen, Laden oder Installieren - Text ist fuer die Anzeige."""


class UpdateInfo:
    """Beschreibt ein verfuegbares Update."""

    def __init__(self, version, notes, page_url, asset_name=None,
                 asset_url=None, asset_size=0):
        self.version = version
        self.notes = notes
        self.page_url = page_url
        self.asset_name = asset_name
        self.asset_url = asset_url
        self.asset_size = asset_size

    @property
    def installable(self):
        """True, wenn es fuer dieses System einen Installer gibt und das
        Programm als installierte Anwendung laeuft (nicht aus dem Quellcode)."""
        return bool(self.asset_url) and install_kind() is not None


# ============================================================================
#  VERSIONEN
# ============================================================================

def parse_version(text):
    """'v0.22.1' -> (0, 22, 1). Ungueltige Angaben ergeben None."""
    match = re.match(r"^v?(\d+(?:\.\d+)*)$", (text or "").strip())
    if not match:
        return None
    parts = [int(part) for part in match.group(1).split(".")]
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts)


def is_newer(candidate, current):
    """True, wenn candidate eine hoehere Version als current ist
    (0.22 > 0.21.3 > 0.21 - passend zum Schema Update 0.x / Fix 0.x.y)."""
    new, old = parse_version(candidate), parse_version(current)
    return bool(new and old and new > old)


# ============================================================================
#  WELCHE INSTALLATION LAEUFT?
# ============================================================================

def install_kind():
    """Art der laufenden Installation: 'windows', 'appimage', 'deb', 'macos'
    oder None beim Start aus dem Quellcode (dann nur Hinweis, kein Update)."""
    if not getattr(sys, "frozen", False):
        return None
    if sys.platform == "win32":
        return "windows"
    if sys.platform == "darwin":
        return "macos"
    if os.environ.get("APPIMAGE"):
        return "appimage"
    if sys.executable.startswith("/opt/fisi-lernplattform/"):
        return "deb"
    return None


def pick_asset(assets, kind=None, machine=None):
    """Waehlt aus den Release-Dateien den Installer fuer dieses System."""
    kind = kind or install_kind()
    machine = (machine or platform.machine()).lower()
    wanted = {
        "windows": lambda name: name.endswith(".exe") and "-Setup-" in name,
        "appimage": lambda name: name.endswith(".AppImage"),
        "deb": lambda name: name.endswith(".deb"),
        "macos": lambda name: name.endswith(
            "-macOS-arm64.dmg" if machine in ("arm64", "aarch64") else "-macOS-intel.dmg"),
        "android": lambda name: name.endswith(".apk"),
    }.get(kind)
    if wanted is None:
        return None
    for asset in assets:
        if wanted(asset.get("name", "")):
            return asset
    return None


# ============================================================================
#  NETZWERK
# ============================================================================

def _ssl_context():
    """Zertifikate des Systems UND von certifi zusammen verwenden.

    Nur das System reicht nicht: Die fertigen Programme finden unter macOS
    und manchen Linux-Systemen keine Zertifikate. Nur certifi reicht auch
    nicht: Virenscanner mit Web-Schutz (z.B. Norton) pruefen HTTPS mit einem
    eigenen Zertifikat, das nur im Zertifikatsspeicher des Systems steht.
    """
    context = ssl.create_default_context()
    try:
        import certifi
        context.load_verify_locations(cafile=certifi.where())
    except (ImportError, OSError, ssl.SSLError):
        pass
    return context


def _open(url, timeout):
    request = urllib.request.Request(url, headers={
        "User-Agent": USER_AGENT, "Accept": "application/vnd.github+json"})
    return urllib.request.urlopen(request, timeout=timeout, context=_ssl_context())


def check_for_update(current_version, timeout=10, kind=None):
    """Fragt das neueste Release ab. Liefert UpdateInfo, wenn es neuer ist
    als current_version, sonst None. Wirft UpdateError bei Netzproblemen.
    kind waehlt die Installer-Art (Vorgabe: die laufende Installation, die
    Handy-App uebergibt 'android')."""
    try:
        with _open(LATEST_URL, timeout) as response:
            release = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        raise UpdateError("GitHub hat die Anfrage abgelehnt (HTTP %d). "
                          "Bitte später erneut versuchen." % error.code)
    except (urllib.error.URLError, OSError, ValueError):
        raise UpdateError("Keine Verbindung zu GitHub. Bitte die "
                          "Internetverbindung prüfen.")

    # GitHub liefert unter /releases/latest nie Vorab-Releases (Testversionen,
    # ab 0.56). Sicherheitshalber wird ein solches Release trotzdem nie
    # angeboten.
    if release.get("prerelease") or release.get("draft"):
        return None
    tag = release.get("tag_name", "")
    if not is_newer(tag, current_version):
        return None
    asset = pick_asset(release.get("assets", []), kind)
    return UpdateInfo(
        version=tag.lstrip("v"),
        notes=(release.get("body") or "").strip(),
        page_url=release.get("html_url") or RELEASES_PAGE,
        asset_name=asset.get("name") if asset else None,
        asset_url=asset.get("browser_download_url") if asset else None,
        asset_size=asset.get("size", 0) if asset else 0,
    )


NOTES_END = "### Herunterladen"


def plain_notes(markdown):
    """Macht den Release-Text (Markdown aus AENDERUNGEN.md) lesbar fuer ein
    einfaches Textfeld: Aufzaehlungspunkte, keine Sternchen, fliessender
    Text statt harter Zeilenumbrueche. Ab 0.56 endet der Text vor
    "### Herunterladen" - darunter stehen nur der Hinweis zur Release-Seite
    und die SHA-256-Liste, die im Update-Fenster zu lang sind."""
    items = []
    for line in (markdown or "").replace("\r\n", "\n").split("\n"):
        stripped = line.strip()
        if stripped == NOTES_END:
            break
        if not stripped:
            items.append("")
        elif stripped.startswith(("- ", "* ")):
            items.append("• " + stripped[2:])
        elif items and items[-1]:
            items[-1] += " " + stripped
        else:
            items.append(stripped)
    text = "\n".join(item for item in items if item)
    for marker in ("**", "__", "`"):
        text = text.replace(marker, "")
    return text


def download(info, progress=None, timeout=30):
    """Laedt den Installer in einen Temp-Ordner. progress(geladen, gesamt)
    wird waehrenddessen aufgerufen. Liefert den Pfad der Datei."""
    if not info.asset_url:
        raise UpdateError("Für dieses System gibt es keinen passenden Installer.")
    write_update_log("Download startet: Version %s, %s" % (info.version, info.asset_name))
    folder = os.path.join(tempfile.gettempdir(), "FISI-Lernplattform-Update")
    os.makedirs(folder, exist_ok=True)
    target = os.path.join(folder, info.asset_name)
    partial = target + ".part"
    try:
        with _open(info.asset_url, timeout) as response, open(partial, "wb") as handle:
            total = int(response.headers.get("Content-Length") or info.asset_size or 0)
            loaded = 0
            while True:
                chunk = response.read(256 * 1024)
                if not chunk:
                    break
                handle.write(chunk)
                loaded += len(chunk)
                if progress:
                    progress(loaded, total)
    except (urllib.error.URLError, OSError) as error:
        write_update_log("Download fehlgeschlagen: %s" % error)
        raise UpdateError("Der Download ist fehlgeschlagen: %s" % error)
    if info.asset_size and os.path.getsize(partial) != info.asset_size:
        write_update_log("Download unvollständig: %d von %d Bytes"
                         % (os.path.getsize(partial), info.asset_size))
        os.remove(partial)
        raise UpdateError("Der Download ist unvollständig. Bitte erneut versuchen.")
    os.replace(partial, target)
    write_update_log("Download fertig: %s (%d Bytes, Größe geprüft)"
                     % (info.asset_name, os.path.getsize(target)))
    return target


# ============================================================================
#  INSTALLATION
# ============================================================================

def windows_installer_args(path, pid=None, exe=None):
    """Befehlszeile fuer den Inno-Setup-Installer (ab 0.55.1).

    /WAITPID: Der Installer wartet, bis dieses Programm beendet ist, und
    ersetzt erst dann Dateien (vorher startete er sofort und das Programm
    schloss sich 1,5 s spaeter - blieb es haengen, waren die Dateien in
    Benutzung und der Installer machte alles rueckgaengig).
    /UPDATELOG: Der Installer schreibt seine Schritte in update.log.
    /FISIEXE: Scheitert die Installation, startet der Installer die alte
    Version wieder, damit sie den Fehlschlag meldet.
    /LOG: ausfuehrliches Protokoll des Installers (update_installer.log).
    Pfade mit Leerzeichen und Umlauten sind sicher: subprocess setzt jedes
    Argument einzeln in Anfuehrungszeichen, Windows bekommt sie als Unicode."""
    pid = os.getpid() if pid is None else pid
    return [path, "/SILENT", "/SUPPRESSMSGBOXES", "/NORESTART",
            "/WAITPID=%d" % pid,
            "/UPDATELOG=%s" % update_log_path(),
            "/FISIEXE=%s" % (exe or sys.executable),
            "/LOG=%s" % installer_log_path()]


def install(path, kind=None, version="", pid=None):
    """Startet die Installation. Liefert (beenden, Hinweistext): Ist beenden
    True, muss sich das Programm sofort schliessen, damit der Installer die
    Dateien ersetzen kann und das Programm neu startet. version: die Version,
    die installiert wird (fuer update.log und die Pruefung beim naechsten
    Start)."""
    kind = kind or install_kind()
    try:
        if kind == "windows":
            # Der Installer laeuft sichtbar, aber ohne Rueckfragen, wartet auf
            # das Ende dieses Programms und startet es danach wieder (siehe
            # [Code] und [Run] im .iss).
            args = windows_installer_args(path, pid)
            write_update_log("Installer wird gestartet: %s" % subprocess.list2cmdline(args))
            remember_pending_update(version)
            try:
                process = subprocess.Popen(args, close_fds=True)
            except OSError:
                forget_pending_update()
                raise
            write_update_log("Installer läuft (Prozess %d). Das Programm wird jetzt "
                             "beendet, der Installer wartet darauf." % process.pid)
            return True, "Das Update wird installiert. Das Programm startet danach neu."

        if kind == "appimage":
            current = os.environ["APPIMAGE"]
            os.chmod(path, 0o755)
            os.replace(path, current)
            subprocess.Popen([current], start_new_session=True)
            return True, "Das Update ist installiert. Das Programm startet neu."

        if kind == "deb":
            # pkexec zeigt eine grafische Passwortabfrage fuer die Installation
            result = subprocess.run(["pkexec", "apt-get", "install", "-y", path])
            if result.returncode != 0:
                subprocess.Popen(["xdg-open", path])
                return False, deb_cancel_message(path)
            return False, ("Das Update ist installiert. Bitte das Programm "
                           "schließen und neu starten.")

        if kind == "macos":
            subprocess.Popen(["open", path])
            return False, ("Das Update wurde geöffnet. Bitte das Programm "
                           "schließen und „FISI-Lernplattform“ im geöffneten "
                           "Fenster auf „Programme“ ziehen (vorhandene Version "
                           "ersetzen).")
    except (OSError, KeyError) as error:
        write_update_log("Installer ließ sich nicht starten: %s" % error)
        raise UpdateError("Die Installation konnte nicht gestartet werden: %s" % error)
    raise UpdateError("Automatische Updates sind nur in der installierten "
                      "Anwendung möglich.")


def deb_cancel_message(path):
    """Meldung, wenn pkexec/apt beim .deb-Update nicht geklappt hat. Ab
    0.59.1 mit einer Terminal-Zeile und dem echten Dateinamen, weil das App
    Center bei installierter Version nur ein graues "Installiert" zeigt
    (nur Text, der Ablauf bleibt gleich)."""
    return ("Die automatische Installation wurde abgebrochen. "
            "Das Paket wurde zum manuellen Installieren geöffnet. "
            "Im Terminal geht es mit: sudo apt install %s" % shlex.quote(path))


# ============================================================================
#  UPDATE-PROTOKOLL (ab 0.55.1)
# ============================================================================
#
# update.log im Datenordner: jeder Schritt eines Updates mit Zeitpunkt -
# Download, Pruefung, Start des Installers, Beenden des Programms, Ergebnis
# (die Zeilen des Installers schreibt er selbst dazu). Nie Zugangsschluessel
# oder Passwoerter; Benutzerpfade werden wie in fehler.log ersetzt. Die
# Datei erscheint unter Optionen > Problem melden.

UPDATE_LOG_NAME = "update.log"
INSTALLER_LOG_NAME = "update_installer.log"
UPDATE_LOG_MAX = 64 * 1024
PENDING_KEY = "update_ausstehend"

FAILED_TITLE = "Update nicht abgeschlossen"
FAILED_TEXT = ("Das Update auf Version %(neu)s wurde nicht installiert. Installiert "
               "ist weiterhin Version %(alt)s. Dein Lernstand ist davon nicht "
               "betroffen.\n\n%(grund)s\n\nDas Protokoll liegt hier:\n%(pfad)s\n"
               "Es steht auch unter Optionen › Problem melden.\n\n"
               "Tipp: PC neu starten und das Update erneut versuchen. Klappt es "
               "dann nicht, den Installer von der Download-Seite von Hand starten.")
REASON_ROLLBACK = ("Der Installer konnte nicht alle Dateien ersetzen und hat alle "
                   "Änderungen rückgängig gemacht.")
REASON_UNKNOWN = "Der Installer hat die Installation nicht abgeschlossen."


def _data_folder():
    return os.path.dirname(resolve_db_path())


def update_log_path():
    return os.path.join(_data_folder(), UPDATE_LOG_NAME)


def installer_log_path():
    return os.path.join(_data_folder(), INSTALLER_LOG_NAME)


def write_update_log(text):
    """Haengt eine Zeile mit Zeitpunkt an update.log an. Darf nie scheitern."""
    try:
        path = update_log_path()
        if os.path.exists(path) and os.path.getsize(path) > UPDATE_LOG_MAX:
            with open(path, encoding="utf-8", errors="replace") as handle:
                rest = handle.read()[-UPDATE_LOG_MAX // 2:]
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(rest[rest.find("\n") + 1:])
        stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(path, "a", encoding="utf-8") as handle:
            handle.write("%s | Programm | %s\n" % (stamp, anonymize_paths(text)))
    except Exception:
        pass


def read_update_log(limit=16 * 1024):
    """Ende von update.log (fuer den Problembericht), "" ohne Datei."""
    try:
        with open(update_log_path(), "rb") as handle:
            handle.seek(0, os.SEEK_END)
            size = handle.tell()
            handle.seek(max(0, size - limit))
            text = handle.read().decode("utf-8", errors="replace")
    except OSError:
        return ""
    if size > limit:
        text = text[text.find("\n") + 1:]
    return text.strip()


def remember_pending_update(version):
    """Merkt sich vor dem Start des Installers, welche Version kommen soll."""
    settings = load_settings()
    settings[PENDING_KEY] = {"version": version,
                             "zeit": datetime.datetime.now().isoformat(timespec="seconds")}
    save_settings(settings)


def forget_pending_update():
    settings = load_settings()
    if settings.pop(PENDING_KEY, None) is not None:
        save_settings(settings)


def _installer_rolled_back():
    """Steht im Protokoll des Installers, dass er zurueckgerollt hat?"""
    try:
        with open(installer_log_path(), encoding="utf-8", errors="replace") as handle:
            text = handle.read()
    except OSError:
        return False
    return "Rolling back changes" in text


def finish_pending_update(current_version):
    """Beim Start: War ein Update unterwegs? Liefert None (nichts zu tun),
    ("ok", version) oder ("fehler", meldungstext). Die Markierung wird in
    beiden Faellen entfernt, die Meldung erscheint also genau einmal."""
    pending = load_settings().get(PENDING_KEY)
    if not isinstance(pending, dict):
        return None
    target = str(pending.get("version") or "")
    forget_pending_update()
    if not target or not is_newer(target, current_version):
        write_update_log("Update auf %s abgeschlossen, Programm läuft als %s."
                         % (target or "?", current_version))
        return "ok", current_version
    write_update_log("Update auf %s NICHT abgeschlossen, installiert ist weiterhin %s."
                     % (target, current_version))
    return "fehler", FAILED_TEXT % {
        "neu": target, "alt": current_version,
        "grund": REASON_ROLLBACK if _installer_rolled_back() else REASON_UNKNOWN,
        "pfad": update_log_path()}


# ============================================================================
#  EINSTELLUNGEN
# ============================================================================

def _settings_path():
    return os.path.join(os.path.dirname(resolve_db_path()), "einstellungen.json")


BROKEN_SETTINGS = "einstellungen.defekt.json"


def load_settings():
    """Liefert die gespeicherten Update-Einstellungen (mit Vorgabewerten).
    Ab 0.53 wird eine beschaedigte Datei vor dem naechsten Speichern als
    einstellungen.defekt.json aufgehoben (sonst still ueberschrieben)."""
    settings = {"auto_check": True}
    path = _settings_path()
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
        if not isinstance(data, dict):
            raise ValueError("einstellungen.json enthaelt kein Objekt")
        settings.update(data)
    except OSError:
        pass
    except ValueError:
        try:
            shutil.copyfile(path, os.path.join(os.path.dirname(path), BROKEN_SETTINGS))
        except OSError:
            pass
    return settings


def save_settings(settings):
    """Ab 0.53 atomar: erst in eine Hilfsdatei schreiben, dann ersetzen - ein
    Absturz mitten im Schreiben hinterlaesst keine halbe Datei mehr."""
    path = _settings_path()
    temp = path + ".tmp"
    try:
        with open(temp, "w", encoding="utf-8") as handle:
            json.dump(settings, handle, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
        return True
    except OSError:
        try:
            os.remove(temp)
        except OSError:
            pass
        return False
