#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FISI Lernplattform - Build und Installer
========================================

Baut das Programm mit PyInstaller zu einer eigenstaendigen Anwendung und
erzeugt daraus den Installer fuer das Betriebssystem, auf dem das Skript
laeuft. Die fertigen Dateien landen in installer_output/.

  Windows : FISI-Lernplattform-Setup-<Version>.exe   (Inno Setup)
  Linux   : fisi-lernplattform_<Version>_amd64.deb    (dpkg-deb)
            FISI-Lernplattform-<Version>-x86_64.AppImage (appimagetool)
  macOS   : FISI-Lernplattform-<Version>-macOS-<Arch>.dmg (hdiutil)

Aufruf:
  python build.py              Anwendung bauen und Installer erzeugen
  python build.py --nur-app    nur die Anwendung bauen (dist/)
  python build.py --ohne-test  ohne automatischen Starttest bauen

Nach dem Bauen startet build.py die fertige Anwendung einmal im Testmodus
(jede Ansicht wird geoeffnet) und bricht bei einem Fehler ab.

Voraussetzungen:
  pip install -r requirements-build.txt
  Windows zusaetzlich Inno Setup 6, Linux zusaetzlich appimagetool (optional).

PyInstaller kann nicht fuer fremde Betriebssysteme bauen. Die Installer fuer
alle drei Systeme entstehen deshalb per GitHub Actions
(.github/workflows/build.yml), wo je ein Windows-, Linux- und macOS-Rechner
dieses Skript ausfuehrt.
"""

import os
import platform
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
APP_NAME = "FISI-Lernplattform"
DISPLAY_NAME = "FISI Lernplattform"
PACKAGE_NAME = "fisi-lernplattform"
DIST = os.path.join(ROOT, "dist")
OUTPUT = os.path.join(ROOT, "installer_output")

DESKTOP_ENTRY = """[Desktop Entry]
Type=Application
Name=FISI Lernplattform
Comment=Lernprogramm fuer die Umschulung zum Fachinformatiker Systemintegration
Exec={exec}
Icon=fisi-lernplattform
Terminal=false
Categories=Education;
Keywords=FISI;IHK;Lernen;Netzwerk;Subnetting;RAID;
"""


def info(text):
    print("[..] " + text, flush=True)


def fail(text):
    print("[FEHLER] " + text, file=sys.stderr, flush=True)
    sys.exit(1)


def app_version():
    """Liest APP_VERSION aus app_gui.py - die Version wird nur dort gepflegt."""
    with open(os.path.join(ROOT, "app_gui.py"), encoding="utf-8") as handle:
        match = re.search(r'^APP_VERSION = "([^"]+)"', handle.read(), re.MULTILINE)
    if not match:
        fail("APP_VERSION wurde in app_gui.py nicht gefunden.")
    return match.group(1)


def run(command, **kwargs):
    print("     " + " ".join(command), flush=True)
    subprocess.run(command, check=True, **kwargs)


# ============================================================================
#  ANWENDUNG (PYINSTALLER)
# ============================================================================

def build_app():
    """Baut dist/FISI-Lernplattform/ (unter macOS zusaetzlich die .app).

    Bewusst als Ordner statt als einzelne Datei: Das Programm startet so
    deutlich schneller, weil beim Start nichts entpackt werden muss. Der
    Installer bringt den Ordner an seinen Platz.
    """
    for folder in ("build", "dist"):
        shutil.rmtree(os.path.join(ROOT, folder), ignore_errors=True)

    separator = ";" if os.name == "nt" else ":"
    command = [
        sys.executable, "-m", "PyInstaller",
        "--name", APP_NAME,
        "--onedir", "--windowed", "--noconfirm", "--clean",
        "--paths", ROOT,
        "--hidden-import", "app_gui",
        "--collect-data", "customtkinter",
        "--add-data", "icon.ico%s." % separator,
        "--add-data", "icon.png%s." % separator,
    ]
    if sys.platform == "win32":
        command += ["--icon", "icon.ico"]
    elif sys.platform == "darwin":
        command += ["--icon", "icon.png",
                    "--osx-bundle-identifier", "de.fisi.lernplattform"]
    command.append("start.py")

    info("Anwendung wird mit PyInstaller gebaut ...")
    run(command, cwd=ROOT)
    target = os.path.join(DIST, APP_NAME + (".app" if sys.platform == "darwin" else ""))
    if not os.path.exists(target):
        fail("PyInstaller hat kein Ergebnis erzeugt: %s" % target)
    return target


def smoke_test(app_path):
    """Startet die gebaute Anwendung einmal im Testmodus: Sie oeffnet jede
    Ansicht, fuehrt eine Suche aus und beendet sich wieder. So faellt ein
    unvollstaendiges Paket (z.B. fehlende Bibliothek) schon beim Bauen auf.
    Die Lern-Datenbank des Benutzers bleibt dabei unberuehrt."""
    if sys.platform == "win32":
        command = [os.path.join(app_path, APP_NAME + ".exe")]
    elif sys.platform == "darwin":
        command = [os.path.join(app_path, "Contents", "MacOS", APP_NAME)]
    else:
        command = [os.path.join(app_path, APP_NAME)]
        # Ohne Bildschirm (z.B. auf GitHub) einen virtuellen X-Server nutzen
        if not os.environ.get("DISPLAY") and shutil.which("xvfb-run"):
            command = ["xvfb-run", "-a"] + command

    work = os.path.join(ROOT, "build", "selftest")
    shutil.rmtree(work, ignore_errors=True)
    os.makedirs(work)
    log_path = os.path.join(work, "selftest.log")
    env = dict(os.environ, FISI_SELFTEST=log_path,
               FISI_DB_PATH=os.path.join(work, "selftest.db"))

    info("Starttest der gebauten Anwendung ...")
    try:
        result = subprocess.run(command, env=env, timeout=120)
    except subprocess.TimeoutExpired:
        fail("Starttest: Die Anwendung hat sich nicht innerhalb von 2 Minuten beendet.")
    report = ""
    if os.path.exists(log_path):
        with open(log_path, encoding="utf-8") as handle:
            report = handle.read()
    if result.returncode != 0 or report != "OK":
        fail("Starttest fehlgeschlagen (Exit-Code %d):\n%s"
             % (result.returncode, report or "keine Rueckmeldung der Anwendung"))
    info("Starttest bestanden: alle Ansichten wurden fehlerfrei geoeffnet.")


# ============================================================================
#  WINDOWS: INNO SETUP
# ============================================================================

def find_iscc():
    candidates = [os.environ.get("ISCC"), shutil.which("iscc"), shutil.which("ISCC")]
    for base in (os.environ.get("ProgramFiles(x86)"), os.environ.get("ProgramFiles"),
                 os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs")):
        if base:
            candidates.append(os.path.join(base, "Inno Setup 6", "ISCC.exe"))
    for candidate in candidates:
        if candidate and os.path.exists(candidate):
            return candidate
    return None


def package_windows(version):
    iscc = find_iscc()
    if not iscc:
        fail("Inno Setup 6 wurde nicht gefunden (https://jrsoftware.org/isdl.php).\n"
             "Die Anwendung liegt trotzdem fertig unter dist\\%s\\." % APP_NAME)
    info("Windows-Installer wird mit Inno Setup erzeugt ...")
    run([iscc, "/Q", "/DMyAppVersion=%s" % version, "FISI-Lernplattform.iss"], cwd=ROOT)


# ============================================================================
#  LINUX: DEB-PAKET UND APPIMAGE
# ============================================================================

def _copy_tree(source, target):
    shutil.copytree(source, target, symlinks=True)


def package_deb(version):
    """Installiert nach /opt/fisi-lernplattform, mit Startmenue-Eintrag und
    dem Befehl fisi-lernplattform."""
    architecture = subprocess.run(["dpkg", "--print-architecture"], check=True,
                                  capture_output=True, text=True).stdout.strip()
    stage = os.path.join(ROOT, "build", "deb")
    shutil.rmtree(stage, ignore_errors=True)
    _copy_tree(os.path.join(DIST, APP_NAME), os.path.join(stage, "opt", PACKAGE_NAME))

    os.makedirs(os.path.join(stage, "usr", "bin"))
    os.symlink("/opt/%s/%s" % (PACKAGE_NAME, APP_NAME),
               os.path.join(stage, "usr", "bin", PACKAGE_NAME))

    apps = os.path.join(stage, "usr", "share", "applications")
    os.makedirs(apps)
    with open(os.path.join(apps, PACKAGE_NAME + ".desktop"), "w", encoding="utf-8") as handle:
        handle.write(DESKTOP_ENTRY.format(exec=PACKAGE_NAME))
    icons = os.path.join(stage, "usr", "share", "icons", "hicolor", "512x512", "apps")
    os.makedirs(icons)
    shutil.copy(os.path.join(ROOT, "icon.png"), os.path.join(icons, PACKAGE_NAME + ".png"))

    size_kb = sum(os.path.getsize(os.path.join(folder, name))
                  for folder, _dirs, names in os.walk(stage) for name in names
                  if not os.path.islink(os.path.join(folder, name))) // 1024
    os.makedirs(os.path.join(stage, "DEBIAN"))
    with open(os.path.join(stage, "DEBIAN", "control"), "w", encoding="utf-8") as handle:
        handle.write(
            "Package: %s\n"
            "Version: %s\n"
            "Section: education\n"
            "Priority: optional\n"
            "Architecture: %s\n"
            "Installed-Size: %d\n"
            "Maintainer: FISI Lernplattform Projekt <333448595+papst2142-cmd@users.noreply.github.com>\n"
            "Description: Lernprogramm fuer Fachinformatiker Systemintegration\n"
            " Karteikarten, Pruefungstrainer, AP1-/AP2-Szenarien, Testprojekte und\n"
            " Praxis-Rechner mit Lernfortschritt. Bringt alle Bibliotheken mit.\n"
            % (PACKAGE_NAME, version, architecture, size_kb))

    target = os.path.join(OUTPUT, "%s_%s_%s.deb" % (PACKAGE_NAME, version, architecture))
    info("DEB-Paket wird erzeugt ...")
    run(["dpkg-deb", "--build", "--root-owner-group", stage, target])


def package_appimage(version):
    tool = os.environ.get("APPIMAGETOOL") or shutil.which("appimagetool")
    if not tool:
        info("appimagetool nicht gefunden - AppImage wird uebersprungen.")
        return
    appdir = os.path.join(ROOT, "build", "AppDir")
    shutil.rmtree(appdir, ignore_errors=True)
    _copy_tree(os.path.join(DIST, APP_NAME), os.path.join(appdir, "usr", "lib", PACKAGE_NAME))

    apprun = os.path.join(appdir, "AppRun")
    with open(apprun, "w", encoding="utf-8") as handle:
        handle.write('#!/bin/sh\nHERE="$(dirname "$(readlink -f "$0")")"\n'
                     'exec "$HERE/usr/lib/%s/%s" "$@"\n' % (PACKAGE_NAME, APP_NAME))
    os.chmod(apprun, 0o755)
    with open(os.path.join(appdir, PACKAGE_NAME + ".desktop"), "w", encoding="utf-8") as handle:
        handle.write(DESKTOP_ENTRY.format(exec=APP_NAME))
    shutil.copy(os.path.join(ROOT, "icon.png"), os.path.join(appdir, PACKAGE_NAME + ".png"))

    machine = platform.machine() or "x86_64"
    target = os.path.join(OUTPUT, "%s-%s-%s.AppImage" % (APP_NAME, version, machine))
    info("AppImage wird erzeugt ...")
    env = dict(os.environ, ARCH=machine, APPIMAGE_EXTRACT_AND_RUN="1")
    run([tool, appdir, target], env=env)


# ============================================================================
#  MACOS: DMG
# ============================================================================

def package_dmg(version, app_path):
    stage = os.path.join(ROOT, "build", "dmg")
    shutil.rmtree(stage, ignore_errors=True)
    os.makedirs(stage)
    _copy_tree(app_path, os.path.join(stage, os.path.basename(app_path)))
    # Verknuepfung zum Programme-Ordner, damit man die App hineinziehen kann
    os.symlink("/Applications", os.path.join(stage, "Programme"))

    arch = "arm64" if platform.machine() == "arm64" else "intel"
    target = os.path.join(OUTPUT, "%s-%s-macOS-%s.dmg" % (APP_NAME, version, arch))
    info("DMG wird erzeugt ...")
    run(["hdiutil", "create", "-volname", DISPLAY_NAME, "-srcfolder", stage,
         "-ov", "-format", "UDZO", target])


# ============================================================================
#  ABLAUF
# ============================================================================

def main():
    version = app_version()
    info("%s Version %s auf %s" % (DISPLAY_NAME, version, platform.platform()))
    app_path = build_app()
    if "--ohne-test" not in sys.argv:
        smoke_test(app_path)
    if "--nur-app" in sys.argv:
        info("Fertig: %s" % app_path)
        return

    os.makedirs(OUTPUT, exist_ok=True)
    if sys.platform == "win32":
        package_windows(version)
    elif sys.platform == "darwin":
        package_dmg(version, app_path)
    else:
        package_deb(version)
        package_appimage(version)
    info("Fertig. Die Installer liegen in %s" % OUTPUT)
    for name in sorted(os.listdir(OUTPUT)):
        if version in name:
            print("     " + name)


if __name__ == "__main__":
    main()
