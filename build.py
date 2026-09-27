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
  python build.py --setze-version 0.22
                               neue Version an allen Stellen eintragen
                               (app_gui.py, LIESMICH.txt, Inno-Setup-Skript)

Vor jedem Build prueft build.py, dass die Version ueberall gleich ist.

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
import time

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


# Stellen, an denen die Versionsnummer zusaetzlich von Hand steht. Die Quelle
# ist APP_VERSION in app_gui.py; build.py sorgt dafuer, dass alle gleich sind.
VERSION_SPOTS = [
    ("app_gui.py", r'^(APP_VERSION = ")([^"]+)(")'),
    ("LIESMICH.txt", r'^(  FISI LERNPLATTFORM  -  Version )(\S+)()'),
    ("FISI-Lernplattform.iss", r'^(  #define MyAppVersion ")([^"]+)(")'),
]
VERSION_FORMAT = r"^\d+\.\d+(\.\d+)?$"


def _read(name):
    with open(os.path.join(ROOT, name), encoding="utf-8", newline="") as handle:
        return handle.read()


def check_versions(version):
    """Bricht ab, wenn die Version nicht ueberall gleich eingetragen ist."""
    if not re.match(VERSION_FORMAT, version):
        fail("Ungueltige Version %s - erlaubt sind z.B. 0.22 (Update) und 0.22.1 (Fix)."
             % version)
    wrong = []
    for name, pattern in VERSION_SPOTS:
        match = re.search(pattern, _read(name), re.MULTILINE)
        if not match or match.group(2) != version:
            wrong.append("  %s: %s" % (name, match.group(2) if match else "nicht gefunden"))
    if wrong:
        fail("Die Version ist nicht ueberall gleich (erwartet %s):\n%s\n"
             "Beheben mit:  python build.py --setze-version %s"
             % (version, "\n".join(wrong), version))


def set_version(version):
    """Traegt eine neue Version an allen Stellen gleichzeitig ein."""
    if not re.match(VERSION_FORMAT, version):
        fail("Ungueltige Version %s - erlaubt sind z.B. 0.22 (Update) und 0.22.1 (Fix)."
             % version)
    for name, pattern in VERSION_SPOTS:
        text, count = re.subn(pattern, lambda m: m.group(1) + version + m.group(3),
                              _read(name), count=1, flags=re.MULTILINE)
        if not count:
            fail("Versionsangabe in %s nicht gefunden." % name)
        with open(os.path.join(ROOT, name), "w", encoding="utf-8", newline="") as handle:
            handle.write(text)
        info("%s -> %s" % (name, version))


def _version_numbers(version):
    """0.22.1 -> (0, 22, 1, 0) fuer die Windows-Dateieigenschaften."""
    parts = [int(part) for part in version.split(".")]
    return tuple((parts + [0, 0, 0, 0])[:4])


def _windows_version_file(version):
    """Versionsangaben fuer die Dateieigenschaften der Windows-.exe."""
    numbers = _version_numbers(version)
    path = os.path.join(ROOT, "build", "version_info.txt")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    strings = [("CompanyName", "FISI Lernplattform Projekt"),
               ("FileDescription", DISPLAY_NAME),
               ("FileVersion", version),
               ("InternalName", APP_NAME),
               ("OriginalFilename", APP_NAME + ".exe"),
               ("ProductName", DISPLAY_NAME),
               ("ProductVersion", version)]
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(
            "VSVersionInfo(\n"
            "  ffi=FixedFileInfo(filevers=%r, prodvers=%r, mask=0x3f, flags=0x0,\n"
            "                    OS=0x40004, fileType=0x1, subtype=0x0, date=(0, 0)),\n"
            "  kids=[\n"
            "    StringFileInfo([StringTable('040704B0', [%s])]),\n"
            "    VarFileInfo([VarStruct('Translation', [1031, 1200])])\n"
            "  ]\n"
            ")\n" % (numbers, numbers,
                     ", ".join("StringStruct(%r, %r)" % item for item in strings)))
    return path


def _set_macos_version(app_path, version):
    """Traegt die Version in die macOS-App ein (PyInstaller setzt 0.0.0) und
    signiert die App danach neu, weil die Aenderung die Signatur ungueltig
    macht."""
    import plistlib
    plist_path = os.path.join(app_path, "Contents", "Info.plist")
    with open(plist_path, "rb") as handle:
        plist = plistlib.load(handle)
    plist["CFBundleShortVersionString"] = version
    plist["CFBundleVersion"] = version
    plist["CFBundleDisplayName"] = DISPLAY_NAME
    with open(plist_path, "wb") as handle:
        plistlib.dump(plist, handle)
    run(["codesign", "--force", "--deep", "--sign", "-", app_path])


def run(command, **kwargs):
    print("     " + " ".join(command), flush=True)
    subprocess.run(command, check=True, **kwargs)


# ============================================================================
#  ANWENDUNG (PYINSTALLER)
# ============================================================================

def build_app(version):
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
        # Von Pillow nur indirekt geladen - ohne diese Angabe fehlt das Modul
        # im Linux-Build und die Anwendung stuerzt beim Start ab.
        "--hidden-import", "PIL._tkinter_finder",
        "--collect-data", "customtkinter",
        "--add-data", "icon.ico%s." % separator,
        "--add-data", "icon.png%s." % separator,
    ]
    if sys.platform == "win32":
        command += ["--icon", "icon.ico",
                    "--version-file", _windows_version_file(version)]
    elif sys.platform == "darwin":
        command += ["--icon", "icon.png",
                    "--osx-bundle-identifier", "de.fisi.lernplattform"]
    command.append("start.py")

    info("Anwendung wird mit PyInstaller gebaut ...")
    run(command, cwd=ROOT)
    target = os.path.join(DIST, APP_NAME + (".app" if sys.platform == "darwin" else ""))
    if not os.path.exists(target):
        fail("PyInstaller hat kein Ergebnis erzeugt: %s" % target)
    if sys.platform == "darwin":
        _set_macos_version(target, version)
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
    command = ["hdiutil", "create", "-volname", DISPLAY_NAME, "-srcfolder", stage,
               "-ov", "-format", "UDZO", target]
    # hdiutil scheitert gelegentlich mit "Resource busy", solange macOS die
    # frisch gebaute App noch untersucht - dann kurz warten und erneut versuchen.
    for attempt in range(1, 6):
        try:
            run(command)
            return
        except subprocess.CalledProcessError:
            if attempt == 5:
                raise
            info("hdiutil war beschaeftigt - neuer Versuch %d von 5 ..." % (attempt + 1))
            time.sleep(10 * attempt)


# ============================================================================
#  ABLAUF
# ============================================================================

def main():
    if "--setze-version" in sys.argv:
        position = sys.argv.index("--setze-version")
        if position + 1 >= len(sys.argv):
            fail("Bitte die neue Version angeben, z.B.: python build.py --setze-version 0.22")
        set_version(sys.argv[position + 1])
        return

    version = app_version()
    check_versions(version)
    info("%s Version %s auf %s" % (DISPLAY_NAME, version, platform.platform()))
    app_path = build_app(version)
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
