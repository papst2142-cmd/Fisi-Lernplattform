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
"""

import json
import os
import platform
import re
import ssl
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request

from fisi_core import resolve_db_path

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
                          "Bitte spaeter erneut versuchen." % error.code)
    except (urllib.error.URLError, OSError, ValueError):
        raise UpdateError("Keine Verbindung zu GitHub. Bitte die "
                          "Internetverbindung pruefen.")

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


def plain_notes(markdown):
    """Macht den Release-Text (Markdown aus AENDERUNGEN.md) lesbar fuer ein
    einfaches Textfeld: Aufzaehlungspunkte, keine Sternchen, fliessender
    Text statt harter Zeilenumbrueche."""
    items = []
    for line in (markdown or "").replace("\r\n", "\n").split("\n"):
        stripped = line.strip()
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
        raise UpdateError("Fuer dieses System gibt es keinen passenden Installer.")
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
        raise UpdateError("Der Download ist fehlgeschlagen: %s" % error)
    if info.asset_size and os.path.getsize(partial) != info.asset_size:
        os.remove(partial)
        raise UpdateError("Der Download ist unvollstaendig. Bitte erneut versuchen.")
    os.replace(partial, target)
    return target


# ============================================================================
#  INSTALLATION
# ============================================================================

def install(path, kind=None):
    """Startet die Installation. Liefert (beenden, Hinweistext): Ist beenden
    True, muss sich das Programm sofort schliessen, damit der Installer die
    Dateien ersetzen kann und das Programm neu startet."""
    kind = kind or install_kind()
    try:
        if kind == "windows":
            # Der Installer laeuft sichtbar, aber ohne Rueckfragen, und
            # startet das Programm danach wieder (siehe [Run] im .iss).
            subprocess.Popen([path, "/SILENT", "/SUPPRESSMSGBOXES", "/NORESTART"],
                             close_fds=True)
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
                return False, ("Die automatische Installation wurde abgebrochen. "
                               "Das Paket wurde zum manuellen Installieren geoeffnet.")
            return False, ("Das Update ist installiert. Bitte das Programm "
                           "schliessen und neu starten.")

        if kind == "macos":
            subprocess.Popen(["open", path])
            return False, ('Das Update wurde geoeffnet. Bitte das Programm '
                           'schliessen und "FISI-Lernplattform" im geoeffneten '
                           'Fenster auf "Programme" ziehen (vorhandene Version '
                           'ersetzen).')
    except (OSError, KeyError) as error:
        raise UpdateError("Die Installation konnte nicht gestartet werden: %s" % error)
    raise UpdateError("Automatische Updates sind nur in der installierten "
                      "Anwendung moeglich.")


# ============================================================================
#  EINSTELLUNGEN
# ============================================================================

def _settings_path():
    return os.path.join(os.path.dirname(resolve_db_path()), "einstellungen.json")


def load_settings():
    """Liefert die gespeicherten Update-Einstellungen (mit Vorgabewerten)."""
    settings = {"auto_check": True}
    try:
        with open(_settings_path(), encoding="utf-8") as handle:
            settings.update(json.load(handle))
    except (OSError, ValueError):
        pass
    return settings


def save_settings(settings):
    try:
        with open(_settings_path(), "w", encoding="utf-8") as handle:
            json.dump(settings, handle, indent=2)
        return True
    except OSError:
        return False
