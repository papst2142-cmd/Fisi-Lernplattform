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
                               (app_gui.py, LIESMICH.txt, Inno-Setup-Skript,
                               mobile/src/main.py, mobile/pyproject.toml)
  python build.py --versionshinweise
                               Abschnitt der aktuellen Version aus
                               AENDERUNGEN.md ausgeben (Release-Text)

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

# Menueeintrag fuer .deb und AppImage. Ab 0.59.1 mit Umlauten (UTF-8 ohne BOM,
# in Ubuntu 26.04 mit desktop-file-validate und lintian geprueft) und
# SingleMainWindow=true: GNOME bietet im Dock kein "Neues Fenster" mehr an
# (zweite Instanz verhindert fisi_einzelstart.py).
DESKTOP_ENTRY = """[Desktop Entry]
Type=Application
Name=FISI Lernplattform
Comment=Lernprogramm für die Umschulung zum Fachinformatiker Systemintegration
Exec={exec}
Icon=fisi-lernplattform
Terminal=false
Categories=Education;
Keywords=FISI;IHK;Lernen;Netzwerk;Subnetting;RAID;
StartupWMClass={wm_class}
SingleMainWindow=true
"""

# Ab 0.59.1: Fensterklasse unter Linux. app_gui erzeugt das Hauptfenster mit
# className=PACKAGE_NAME, Tk schreibt den ersten Buchstaben der Klasse gross
# (gemessen mit xprop: "fisi-lernplattform", "Fisi-lernplattform"). GNOME
# verbindet ueber StartupWMClass Fenster und Menueeintrag (Dock-Symbol,
# "An Dash anheften"). Der Klassenname bleibt auch bei einer zweiten
# Instanz gleich, der Instanzname wird dann zu "fisi-lernplattform #2".
WM_CLASS = PACKAGE_NAME[:1].upper() + PACKAGE_NAME[1:]

# Ab 0.59.1: Symbol im .deb in mehreren Groessen (Icon Theme Specification:
# mindestens 48x48), alle aus icon.png (512x512) verkleinert
DEB_ICON_SIZES = (48, 64, 128, 256, 512)

# Ab 0.59.1: Bibliotheken, die im schlanken Ubuntu fehlen koennen (im
# Container fehlten libXft.so.2 und libXss.so.1; Paketnamen auf Ubuntu
# 22.04 und 26.04 gleich)
DEB_DEPENDS = "libxft2, libxss1"


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
    ("mobile/src/main.py", r'^(APP_VERSION = ")([^"]+)(")'),
    ("mobile/pyproject.toml", r'^(version = ")([^"]+)(")'),
]
# Interne Versionsnummer der Android-App (muss bei jedem Update steigen):
# 0.24 -> 2400, 0.24.1 -> 2401, 1.0 -> 10000
ANDROID_BUILD_SPOT = ("mobile/pyproject.toml", r'^(build_number = )(\d+)()')


def android_build_number(version):
    major, minor, fix = _version_numbers(version)[:3]
    return str(major * 10000 + minor * 100 + fix)
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
    name, pattern = ANDROID_BUILD_SPOT
    match = re.search(pattern, _read(name), re.MULTILINE)
    if not match or match.group(2) != android_build_number(version):
        wrong.append("  %s: build_number %s (erwartet %s)"
                     % (name, match.group(2) if match else "nicht gefunden",
                        android_build_number(version)))
    if wrong:
        fail("Die Version ist nicht ueberall gleich (erwartet %s):\n%s\n"
             "Beheben mit:  python build.py --setze-version %s"
             % (version, "\n".join(wrong), version))


def set_version(version):
    """Traegt eine neue Version an allen Stellen gleichzeitig ein."""
    if not re.match(VERSION_FORMAT, version):
        fail("Ungueltige Version %s - erlaubt sind z.B. 0.22 (Update) und 0.22.1 (Fix)."
             % version)
    spots = [(name, pattern, version) for name, pattern in VERSION_SPOTS]
    spots.append(ANDROID_BUILD_SPOT + (android_build_number(version),))
    for name, pattern, value in spots:
        text, count = re.subn(pattern, lambda m: m.group(1) + value + m.group(3),
                              _read(name), count=1, flags=re.MULTILINE)
        if not count:
            fail("Versionsangabe in %s nicht gefunden." % name)
        with open(os.path.join(ROOT, name), "w", encoding="utf-8", newline="") as handle:
            handle.write(text)
        info("%s -> %s" % (name, value))


def release_notes(version):
    """Abschnitt '## <version>' aus AENDERUNGEN.md - wird Text des
    GitHub-Releases und im Update-Fenster des Programms angezeigt."""
    text = _read("AENDERUNGEN.md").replace("\r\n", "\n")
    match = re.search(r"^## %s\s*\n(.*?)(?=^## |\Z)" % re.escape(version), text,
                      re.MULTILINE | re.DOTALL)
    if not match or not match.group(1).strip():
        fail("In AENDERUNGEN.md fehlt der Abschnitt '## %s'." % version)
    return match.group(1).strip()


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
        "--add-data", "inhalte%sinhalte" % separator,
        "--add-data", "fisi_symbole.otf%s." % separator,
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


def check_content():
    """Prueft die Lerninhalte in inhalte/ (Pflichtfelder, 4 Antworten, keine
    Doppelten, gueltige Themen) - bei Fehlern wird nicht gebaut."""
    sys.path.insert(0, ROOT)
    import fisi_core
    problems = fisi_core.validate_content()
    if problems:
        fail("Die Lerninhalte enthalten Fehler:\n  " + "\n  ".join(problems))
    info("Lerninhalte geprueft: %d Karteikarten, %d Quizfragen, %d AP1- und %d "
         "AP2-Szenarien, %d Testprojekte" % (
             len(fisi_core.KARTEIKARTEN), len(fisi_core.QUIZ_QUESTIONS),
             len(fisi_core.AP1_SZENARIEN), len(fisi_core.SZENARIEN),
             len(fisi_core.PROJEKTARBEITEN)))


# Zeitgrenze des Starttests in Sekunden. Ab 0.58 auf macOS Intel 240 s: Im
# ersten Release-Lauf von 0.57 brauchte der Starttest auf dem GitHub-Runner
# "macos-15-intel" ueber 120 s (lokal 41 s, ein Neustart des Jobs war gruen).
# Die Intel-Runner sind die langsamsten; die doppelte Grenze laesst Luft fuer
# solche Ausreisser, ein wirklich haengendes Programm faellt weiter auf.
SELFTEST_TIMEOUT = 120
SELFTEST_TIMEOUT_MACOS_INTEL = 240


def selftest_timeout(system=None, machine=None):
    system = sys.platform if system is None else system
    machine = platform.machine() if machine is None else machine
    if system == "darwin" and machine.lower() in ("x86_64", "amd64", "i386"):
        return SELFTEST_TIMEOUT_MACOS_INTEL
    return SELFTEST_TIMEOUT


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

    limit = selftest_timeout()
    info("Starttest der gebauten Anwendung (Zeitgrenze %d s) ..." % limit)
    try:
        result = subprocess.run(command, env=env, timeout=limit)
    except subprocess.TimeoutExpired:
        fail("Starttest: Die Anwendung hat sich nicht innerhalb von %d Sekunden beendet."
             % limit)
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


def write_deb_icons(hicolor):
    """Legt das Programmsymbol in allen Groessen aus DEB_ICON_SIZES unter
    hicolor/<n>x<n>/apps/ ab (ab 0.59.1, vorher nur 512x512)."""
    from PIL import Image
    source = os.path.join(ROOT, "icon.png")
    with Image.open(source) as image:
        image = image.convert("RGBA")
        for size in DEB_ICON_SIZES:
            folder = os.path.join(hicolor, "%dx%d" % (size, size), "apps")
            os.makedirs(folder)
            target = os.path.join(folder, PACKAGE_NAME + ".png")
            if image.size == (size, size):
                shutil.copy(source, target)
            else:
                image.resize((size, size), Image.LANCZOS).save(target)


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
        handle.write(DESKTOP_ENTRY.format(exec=PACKAGE_NAME, wm_class=WM_CLASS))
    write_deb_icons(os.path.join(stage, "usr", "share", "icons", "hicolor"))

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
            "Depends: %s\n"
            "Maintainer: FISI Lernplattform Projekt <333448595+papst2142-cmd@users.noreply.github.com>\n"
            "Description: Lernprogramm für Fachinformatiker Systemintegration\n"
            " Karteikarten, Prüfungstrainer, AP1-/AP2-Szenarien, Testprojekte und\n"
            " Praxis-Rechner mit Lernfortschritt. Bringt alle Bibliotheken mit.\n"
            % (PACKAGE_NAME, version, architecture, size_kb, DEB_DEPENDS))

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
        handle.write(DESKTOP_ENTRY.format(exec=APP_NAME, wm_class=WM_CLASS))
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
    if "--versionshinweise" in sys.argv:
        sys.stdout.reconfigure(encoding="utf-8")
        print(release_notes(app_version()))
        return

    version = app_version()
    check_versions(version)
    check_content()
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
