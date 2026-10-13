#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fachinformatiker Lernplattform - Updater
========================================

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
import hashlib
import http.client
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
                 asset_url=None, asset_size=0, asset_digest=None):
        self.version = version
        self.notes = notes
        self.page_url = page_url
        self.asset_name = asset_name
        self.asset_url = asset_url
        self.asset_size = asset_size
        # Ab 0.62.5: Pruefsumme aus der GitHub-Antwort ("sha256:...") oder None
        self.asset_digest = asset_digest

    @property
    def installable(self):
        """True, wenn es fuer dieses System einen Installer gibt und das
        Programm als installierte Anwendung laeuft (nicht aus dem Quellcode)."""
        return bool(self.asset_url) and install_kind() is not None

    @property
    def asset_missing(self):
        """Ab 0.62.5: installierte Anwendung, aber im Release liegt keine
        Datei fuer dieses System (vorher hiess es faelschlich, das Programm
        sei nicht installiert)."""
        return not self.asset_url and install_kind() is not None


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
        # Ab 0.62.5: Eintraege ungewohnter Form ueberspringen
        if isinstance(asset, dict) and wanted(str(asset.get("name") or "")):
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


UNEXPECTED_ANSWER = "Die Antwort von GitHub ist unerwartet. Bitte später erneut versuchen."
NO_ASSET_TEXT = ("Für dein System liegt diesmal keine Datei bei. Auf der "
                 "Download-Seite stehen alle Dateien dieses Releases.")


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

    # Ab 0.62.5: ungewohnte Antwortform (Liste, assets: null, ...) ergibt
    # einen deutschen Satz statt "Unerwarteter Fehler: 'list' object ..."
    if not isinstance(release, dict):
        raise UpdateError(UNEXPECTED_ANSWER)
    # GitHub liefert unter /releases/latest nie Vorab-Releases (Testversionen,
    # ab 0.56). Sicherheitshalber wird ein solches Release trotzdem nie
    # angeboten.
    if release.get("prerelease") or release.get("draft"):
        return None
    tag = release.get("tag_name", "")
    assets = release.get("assets", [])
    if not isinstance(tag, str) or not isinstance(assets, list):
        raise UpdateError(UNEXPECTED_ANSWER)
    if not is_newer(tag, current_version):
        return None
    asset = pick_asset(assets, kind)
    body = release.get("body")
    size = asset.get("size", 0) if asset else 0
    digest = asset.get("digest") if asset else None
    return UpdateInfo(
        version=tag.lstrip("v"),
        notes=body.strip() if isinstance(body, str) else "",
        page_url=release.get("html_url") or RELEASES_PAGE,
        asset_name=asset.get("name") if asset else None,
        asset_url=asset.get("browser_download_url") if asset else None,
        asset_size=size if isinstance(size, int) else 0,
        asset_digest=digest if isinstance(digest, str) else None,
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


UPDATE_FOLDER = "FISI-Lernplattform-Update"
NEW_SUFFIX = ".neu"      # AppImage: Download neben der laufenden Datei (ab 0.62.5)
ALT_SUFFIX = ".alt"      # AppImage: bisherige Fassung bis zum ersten Start der neuen

DOWNLOAD_HTTP = "Der Download ist fehlgeschlagen (HTTP %d). Bitte später erneut versuchen."
DOWNLOAD_TIMEOUT = ("Der Download hat zu lange gedauert. Bitte die Internetverbindung "
                    "prüfen und erneut versuchen.")
DOWNLOAD_OFFLINE = "Keine Verbindung zum Download. Bitte die Internetverbindung prüfen."
DOWNLOAD_INCOMPLETE = "Der Download ist unvollständig. Bitte erneut versuchen."
DOWNLOAD_SAVE = ("Die Datei konnte nicht gespeichert werden. Bitte freien "
                 "Speicherplatz prüfen und erneut versuchen.")
DOWNLOAD_CHECKSUM = ("Die heruntergeladene Datei ist beschädigt (Prüfsumme stimmt "
                     "nicht). Bitte erneut versuchen.")


def _remove_quietly(path):
    try:
        os.remove(path)
    except OSError:
        pass


def _download_target(info):
    """Zieldatei des Downloads. Ab 0.62.5: fuer die AppImage neben der
    laufenden Datei (sonst scheitert das Ersetzen, wenn /tmp ein anderes
    Laufwerk ist). Sonst im Temp-Ordner; alte Installer und Teil-Dateien
    frueherer Updates werden dabei aufgeraeumt."""
    current = os.environ.get("APPIMAGE")
    if install_kind() == "appimage" and current:
        return current + NEW_SUFFIX
    folder = os.path.join(tempfile.gettempdir(), UPDATE_FOLDER)
    os.makedirs(folder, exist_ok=True)
    for name in os.listdir(folder):
        _remove_quietly(os.path.join(folder, name))
    return os.path.join(folder, info.asset_name)


def _expected_sha256(info):
    """Hex-Pruefsumme aus der GitHub-Antwort ("sha256:<hex>") oder None."""
    digest = getattr(info, "asset_digest", None)
    if isinstance(digest, str) and digest.lower().startswith("sha256:"):
        value = digest.split(":", 1)[1].strip().lower()
        if re.match(r"^[0-9a-f]{64}$", value):
            return value
    return None


def _download_failed(error, text):
    write_update_log("Download fehlgeschlagen: %s" % (error,))
    raise UpdateError(text)


def download(info, progress=None, timeout=30):
    """Laedt den Installer herunter. progress(geladen, gesamt) wird
    waehrenddessen aufgerufen. Liefert den Pfad der Datei.

    Ab 0.62.5: deutsche Fehlertexte je Fall (die Technik steht in
    update.log), keine liegengebliebene .part-Datei, Pruefsumme (SHA-256)
    aus der GitHub-Antwort, wenn sie dort steht - sonst nur die Groesse und
    eine Zeile in update.log."""
    if not info.asset_url:
        raise UpdateError("Für dieses System gibt es keinen passenden Installer.")
    write_update_log("Download startet: Version %s, %s" % (info.version, info.asset_name))
    try:
        target = _download_target(info)
    except OSError as error:
        _download_failed(error, DOWNLOAD_SAVE)
    partial = target + ".part"
    sha = hashlib.sha256()
    finished = False
    try:
        try:
            with _open(info.asset_url, timeout) as response, open(partial, "wb") as handle:
                total = int(response.headers.get("Content-Length") or info.asset_size or 0)
                loaded = 0
                while True:
                    chunk = response.read(256 * 1024)
                    if not chunk:
                        break
                    handle.write(chunk)
                    sha.update(chunk)
                    loaded += len(chunk)
                    if progress:
                        progress(loaded, total)
        except urllib.error.HTTPError as error:
            _download_failed(error, DOWNLOAD_HTTP % error.code)
        except urllib.error.URLError as error:
            timed_out = isinstance(error.reason, TimeoutError)
            _download_failed(error, DOWNLOAD_TIMEOUT if timed_out else DOWNLOAD_OFFLINE)
        except TimeoutError as error:
            _download_failed(error, DOWNLOAD_TIMEOUT)
        except (http.client.HTTPException, ConnectionError) as error:
            _download_failed(repr(error), DOWNLOAD_INCOMPLETE)
        except OSError as error:
            _download_failed(error, DOWNLOAD_SAVE)
        if info.asset_size and os.path.getsize(partial) != info.asset_size:
            write_update_log("Download unvollständig: %d von %d Bytes"
                             % (os.path.getsize(partial), info.asset_size))
            raise UpdateError(DOWNLOAD_INCOMPLETE)
        expected = _expected_sha256(info)
        if expected and sha.hexdigest() != expected:
            write_update_log("Prüfsumme falsch: erwartet %s, erhalten %s"
                             % (expected, sha.hexdigest()))
            raise UpdateError(DOWNLOAD_CHECKSUM)
        if not expected:
            write_update_log("GitHub nennt keine Prüfsumme für %s, nur die Größe "
                             "wird geprüft." % info.asset_name)
        os.replace(partial, target)
        finished = True
    finally:
        if not finished:
            _remove_quietly(partial)
    write_update_log("Download fertig: %s (%d Bytes, %s)"
                     % (info.asset_name, os.path.getsize(target),
                        "Größe und Prüfsumme geprüft" if expected else "Größe geprüft"))
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


# Ab 0.62.5: Neustart nach dem AppImage-Update mit Rueckfall. Laeuft als
# eigenes sh, weil sich das Programm gleich beendet (und mit ihm die
# eingehaengte AppImage). Ein eigener Probestart vorab ist nicht sicher:
# Das Programm kennt keinen reinen Versions-Aufruf, und ein zweiter Start
# trifft auf die Sperre gegen Mehrfachstart (fisi_einzelstart). Deshalb ist
# der echte Neustart die Probe: Endet die neue Fassung mit einem Fehler
# (Code ungleich 0, auch "Exec format error") und liegt die alte noch als
# .alt daneben, kommt die alte zurueck und startet; sie meldet den
# Fehlschlag (finish_pending_update). Die neue Fassung entfernt die
# .alt-Datei bei ihrem ersten erfolgreichen Start - danach greift der
# Rueckfall nicht mehr.
APPIMAGE_RESTART = r'''
neu="$1"; alt="$2"; log="$3"
"$neu"
code=$?
if [ "$code" -ne 0 ] && [ -e "$alt" ]; then
  jetzt=$(date '+%Y-%m-%d %H:%M:%S')
  if mv -f "$alt" "$neu"; then
    printf '%s | Updater | Die neue Version startete nicht (Code %s). Die bisherige Version wurde wiederhergestellt und wird gestartet.\n' "$jetzt" "$code" >> "$log"
    exec "$neu"
  fi
  printf '%s | Updater | Die neue Version startete nicht (Code %s). Die bisherige Version ließ sich nicht zurückholen.\n' "$jetzt" "$code" >> "$log"
fi
'''


def _install_appimage(path, version):
    """Ab 0.62.5: Die bisherige AppImage bleibt als .alt daneben liegen,
    die neue kommt an ihren Platz und startet ueber APPIMAGE_RESTART.
    Liefert den Hinweistext."""
    current = os.environ["APPIMAGE"]
    backup = current + ALT_SUFFIX
    os.chmod(path, 0o755)
    _remove_quietly(backup)
    os.replace(current, backup)
    try:
        os.replace(path, current)
    except OSError:
        os.replace(backup, current)
        raise
    remember_pending_update(version, backup=backup)
    write_update_log("AppImage ersetzt. Die bisherige Version liegt bis zum ersten "
                     "Start der neuen als .alt daneben.")
    try:
        subprocess.Popen(["/bin/sh", "-c", APPIMAGE_RESTART, "fisi-update",
                          current, backup, update_log_path()], start_new_session=True)
    except OSError:
        os.replace(backup, current)
        forget_pending_update()
        raise
    return "Das Update ist installiert. Das Programm startet neu."


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
            return True, _install_appimage(path, version)

        if kind == "deb":
            # pkexec zeigt eine grafische Passwortabfrage fuer die Installation
            result = subprocess.run(["pkexec", "apt-get", "install", "-y", path])
            if result.returncode != 0:
                subprocess.Popen(["xdg-open", path])
                return False, deb_cancel_message(path)
            # Ab 0.63.2 (B-N-10): Neustart wie beim AppImage. Ein abgeloester
            # Hilfsprozess wartet, bis dieses Programm beendet ist (hoechstens
            # 30 s, danach uebernimmt die Sperre gegen Mehrfachstart das
            # Warten), und startet dann die neu installierte Fassung.
            # PYINSTALLER_RESET_ENVIRONMENT=1: Die neue Fassung richtet ihre
            # Umgebung selbst ein, statt die des beendeten Programms zu erben.
            # Laesst sich der Hilfsprozess nicht starten, bleibt es beim
            # bisherigen Hinweis (das Paket ist ja installiert).
            restart = ('i=0; while kill -0 "$1" 2>/dev/null && [ "$i" -lt 150 ]; '
                       'do sleep 0.2; i=$((i+1)); done; exec "$2"')
            try:
                subprocess.Popen(["/bin/sh", "-c", restart, "fisi-update",
                                  str(os.getpid() if pid is None else pid), sys.executable],
                                 start_new_session=True,
                                 env=dict(os.environ, PYINSTALLER_RESET_ENVIRONMENT="1"))
            except OSError as error:
                write_update_log("Paket installiert, Neustart ließ sich nicht "
                                 "vorbereiten: %s" % error)
                return False, ("Das Update ist installiert. Bitte das Programm "
                               "schließen und neu starten.")
            write_update_log("Paket installiert. Das Programm startet nach dem "
                             "Beenden neu.")
            return True, "Das Update ist installiert. Das Programm startet neu."

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
# Datei erscheint unter Optionen > Diagnose und Werkzeuge > Problem melden.

UPDATE_LOG_NAME = "update.log"
INSTALLER_LOG_NAME = "update_installer.log"
UPDATE_LOG_MAX = 64 * 1024
PENDING_KEY = "update_ausstehend"

FAILED_TITLE = "Update nicht abgeschlossen"
FAILED_TEXT = ("Das Update auf Version %(neu)s wurde nicht installiert. Installiert "
               "ist weiterhin Version %(alt)s. Dein Lernstand ist davon nicht "
               "betroffen.\n\n%(grund)s\n\nDas Protokoll liegt hier:\n%(pfad)s\n"
               "Es steht auch unter Optionen › Diagnose und Werkzeuge › Problem melden.\n\n"
               "Tipp: PC neu starten und das Update erneut versuchen. Klappt es "
               "dann nicht, den Installer von der Download-Seite von Hand starten.")
REASON_ROLLBACK = ("Der Installer konnte nicht alle Dateien ersetzen und hat alle "
                   "Änderungen rückgängig gemacht.")
REASON_UNKNOWN = "Der Installer hat die Installation nicht abgeschlossen."
REASON_APPIMAGE = ("Die neue Version ließ sich auf diesem System nicht starten. "
                   "Die bisherige Version wurde wiederhergestellt.")


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


def remember_pending_update(version, backup=None):
    """Merkt sich vor dem Start des Installers, welche Version kommen soll.
    backup (ab 0.62.5, AppImage): Pfad der bisherigen Fassung (.alt)."""
    settings = load_settings()
    settings[PENDING_KEY] = {"version": version,
                             "zeit": datetime.datetime.now().isoformat(timespec="seconds")}
    if backup:
        settings[PENDING_KEY]["alt"] = backup
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
    backup = pending.get("alt")
    backup = backup if isinstance(backup, str) and backup.endswith(ALT_SUFFIX) else None
    forget_pending_update()
    if not target or not is_newer(target, current_version):
        write_update_log("Update auf %s abgeschlossen, Programm läuft als %s."
                         % (target or "?", current_version))
        if backup and os.path.exists(backup):
            # Ab 0.62.5 (AppImage): die neue Fassung laeuft, die alte wird
            # nicht mehr gebraucht
            _remove_quietly(backup)
            write_update_log("Die bisherige Version (.alt) wurde entfernt.")
        return "ok", current_version
    write_update_log("Update auf %s NICHT abgeschlossen, installiert ist weiterhin %s."
                     % (target, current_version))
    if backup:
        reason = REASON_APPIMAGE
    else:
        reason = REASON_ROLLBACK if _installer_rolled_back() else REASON_UNKNOWN
    return "fehler", FAILED_TEXT % {
        "neu": target, "alt": current_version, "grund": reason,
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
            _BROKEN_SEEN[0] = True     # ab 0.62.5: einmal melden
        except OSError:
            pass
    return settings


# Ab 0.62.5: Meldung beim Start, wenn die Einstellungsdatei kaputt war
# (vorher war ein eingerichteter Abgleich still weg). PC und Handy zeigen
# denselben Text.
_BROKEN_SEEN = [False]
BROKEN_TITLE = "Einstellungen ersetzt"
BROKEN_TEXT = ("Die Einstellungsdatei war beschädigt und wurde durch die "
               "Grundeinstellungen ersetzt. Die alte Datei ist als "
               "einstellungen.defekt.json im Datenordner aufgehoben. Falls du "
               "den Abgleich eingerichtet hattest, richte ihn bitte neu ein.")


def broken_settings_notice():
    """Beim Start: (Titel, Text), wenn einstellungen.json kaputt war, sonst
    None. Die Datei wird dann durch die Grundeinstellungen ersetzt (das
    Original liegt schon als einstellungen.defekt.json daneben), die Meldung
    kommt also genau einmal."""
    load_settings()
    if not _BROKEN_SEEN[0]:
        return None
    _BROKEN_SEEN[0] = False
    save_settings(load_settings())
    _BROKEN_SEEN[0] = False
    return BROKEN_TITLE, BROKEN_TEXT


def save_settings(settings):
    """Ab 0.53 atomar: erst in eine Hilfsdatei schreiben, dann ersetzen - ein
    Absturz mitten im Schreiben hinterlaesst keine halbe Datei mehr.
    Ab 0.62.5 nur fuer das eigene Konto lesbar (0600; die Datei enthaelt den
    Zugangsschluessel des Abgleichs). Unter Windows ohne Wirkung."""
    path = _settings_path()
    temp = path + ".tmp"
    try:
        descriptor = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            if hasattr(os, "fchmod") and os.name != "nt":
                os.fchmod(handle.fileno(), 0o600)   # falls .tmp schon da war
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
