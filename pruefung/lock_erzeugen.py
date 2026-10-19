#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ab 0.63.2 (B-M-05, FG-52): Lock-Dateien mit SHA-256-Pruefsummen erzeugen.

Die Fassungen sind die, die der Referenzlauf 38443624150 (vor N11) auf den
GitHub-Rechnern installiert hat (aus den pip-Zeilen "Successfully installed"
der Job-Logs). Es wird nichts aktualisiert (N11-F2): Eine neue Fassung kommt
nur, wenn sie hier von Hand eingetragen wird.

Das Skript installiert nichts. Es laedt die Pakete nur mit
"pip download --no-deps --only-binary=:all:" je Zielsystem in einen
Arbeitsordner und bildet die Pruefsummen (wie "pip hash"). Danach steht in
jeder Lock-Datei jede Fassung mit "==" und den Pruefsummen aller Raeder
(wheels) fuer die Zielsysteme. pip nimmt bei "--require-hashes" jede der
angegebenen Pruefsummen an, also das Rad des jeweiligen Systems.

Aufruf (Arbeitsordner wird nicht geloescht, Pfad frei waehlbar):
  python pruefung/lock_erzeugen.py <arbeitsordner> [lock-datei ...]
"""

import hashlib
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

WIN = "win32"
MAC = "darwin"
LINUX = "linux"

# Zielsysteme: Kennung -> Gruppen von pip-Plattform-Angaben (Python 3.12,
# CPython). Je Gruppe ein pip-Aufruf, pip waehlt darin das passende Rad.
# pip 24 erweitert eine Plattform-Angabe nicht auf aeltere Fassungen, deshalb
# stehen alle erlaubten einzeln da. Linux hoechstens glibc 2.35 (Ubuntu 22.04,
# Bau-Container), macOS je ein Rad fuer Arm und Intel. Die neueste Angabe
# steht vorn (pip bevorzugt die erste, wie pip auf dem Zielsystem selbst).
_LINUX_TAGS = (["manylinux_2_%d_x86_64" % minor for minor in range(35, 4, -1)]
               + ["manylinux2014_x86_64", "manylinux2010_x86_64", "manylinux1_x86_64"])
_MAC_VERSIONEN = ["15_0", "14_0", "13_0", "12_0", "11_0", "10_15", "10_14", "10_13",
                  "10_12", "10_11", "10_10", "10_9"]
PLATTFORMEN = {
    WIN: [["win_amd64"]],
    MAC: [["macosx_%s_%s" % (v, arch) for v in _MAC_VERSIONEN for arch in ("arm64", "universal2")],
          ["macosx_%s_%s" % (v, arch) for v in _MAC_VERSIONEN for arch in ("x86_64", "universal2")]],
    LINUX: [_LINUX_TAGS],
}

# Marken (environment markers) fuer Pakete, die nur auf einem System
# gebraucht werden (wie in den Abhaengigkeiten der Pakete selbst)
NUR_WINDOWS = 'sys_platform == "win32"'
NUR_MAC = 'sys_platform == "darwin"'
NICHT_WINDOWS = 'sys_platform != "win32"'

# Lock-Datei -> (Zweck, Systeme, [(Paket, Fassung, Marke oder None)])
FLET = [
    ("annotated-doc", "0.0.5", None), ("annotated-types", "0.8.0", None),
    ("anyio", "4.15.1", None), ("arrow", "1.4.0", None),
    ("binaryornot", "0.4.4", None), ("certifi", "2026.7.22", None),
    ("chardet", "5.2.0", None), ("charset-normalizer", "3.5.2", None),
    ("click", "8.5.0", None), ("colorama", "0.4.6", NUR_WINDOWS),
    ("cookiecutter", "2.7.1", None), ("fastapi", "0.143.0", None),
    ("flet", "1.0.1", None), ("flet-cli", "1.0.1", None),
    ("flet-desktop", "1.0.1", None), ("flet-platform-assets", "1.0.1", None),
    ("flet-web", "1.0.1", None), ("h11", "0.16.0", None),
    ("httpcore", "1.0.9", None), ("httptools", "0.9.0", None),
    ("httpx", "0.28.1", None), ("idna", "3.20", None),
    ("jinja2", "3.1.6", None), ("markdown-it-py", "4.2.0", None),
    ("markupsafe", "3.0.4", None), ("mdurl", "0.1.2", None),
    ("msgpack", "1.2.3", None), ("oauthlib", "4.0.0", None),
    ("opentelemetry-api", "1.45.1", None), ("packaging", "26.3", None),
    ("pillow", "12.3.0", None), ("pydantic", "2.14.1", None),
    ("pydantic-core", "2.50.1", None), ("pygments", "2.21.0", None),
    ("python-dateutil", "2.9.0.post0", None), ("python-dotenv", "1.2.4", None),
    ("python-slugify", "9.1.3", None), ("pyyaml", "6.0.3", None),
    ("qrcode", "8.2", None), ("repath", "0.9.0", None),
    ("requests", "2.34.2", None), ("rich", "15.0.0", None),
    ("six", "1.17.0", None), ("starlette", "1.8.0", None),
    ("text-unidecode", "1.3", None), ("typing-extensions", "4.16.0", None),
    ("typing-inspection", "0.4.4", None), ("tzdata", "2026.5", None),
    ("urllib3", "2.8.0", None), ("uvicorn", "0.54.0", None),
    ("uvloop", "0.23.0", NICHT_WINDOWS), ("watchdog", "6.0.0", None),
    ("watchfiles", "1.3.0", None), ("websockets", "17.2", None),
]

LOCKS = {
    "requirements-lock-bau.txt": (
        "PC-Bau (requirements-build.txt samt Abhaengigkeiten), Job build",
        [WIN, MAC, LINUX],
        [("altgraph", "0.17.5", None), ("certifi", "2026.7.22", None),
         ("customtkinter", "6.0.0", None), ("darkdetect", "0.8.0", None),
         ("macholib", "1.16.4", NUR_MAC), ("packaging", "26.3", None),
         ("pefile", "2024.8.26", NUR_WINDOWS), ("pillow", "12.3.0", None),
         ("pyinstaller", "6.22.3", None),
         ("pyinstaller-hooks-contrib", "2026.8", None),
         ("pywin32-ctypes", "0.2.3", NUR_WINDOWS), ("setuptools", "84.0.0", None)]),
    "requirements-lock-tests.txt": (
        "Tests PC (requirements.txt und psutil), Jobs tests und tests-windows",
        [WIN, LINUX],
        [("certifi", "2026.7.22", None), ("customtkinter", "6.0.0", None),
         ("darkdetect", "0.8.0", None), ("packaging", "26.3", None),
         ("pillow", "12.3.0", None), ("psutil", "7.2.2", None)]),
    "requirements-lock-flet.txt": (
        "flet[all]==1.0.1 samt Abhaengigkeiten und certifi, Jobs android, tests und tests-windows",
        [WIN, LINUX], FLET),
    # pip-audit (B-N-12) gibt es im Referenzlauf nicht: Fassung 2.10.1 und
    # Abhaengigkeiten, jede mindestens zwei Wochen vor dem 14.10.2026
    # veroeffentlicht. Laeuft nur im Linux-Bau, in einer eigenen Umgebung.
    "requirements-lock-pip-audit.txt": (
        "pip-audit (B-N-12) samt Abhaengigkeiten, Job build (Linux), eigene Umgebung",
        [LINUX],
        [("boolean-py", "5.0", None), ("cachecontrol", "0.14.4", None),
         ("certifi", "2026.7.22", None), ("charset-normalizer", "3.5.2", None),
         ("cyclonedx-python-lib", "11.12.0", None), ("defusedxml", "0.7.1", None),
         ("filelock", "4.0.7", None), ("idna", "3.20", None),
         ("license-expression", "30.4.4", None), ("markdown-it-py", "4.2.0", None),
         ("mdurl", "0.1.2", None), ("msgpack", "1.2.3", None),
         ("packageurl-python", "0.17.6", None), ("packaging", "26.3", None),
         ("pip", "26.2.1", None), ("pip-api", "0.0.35", None),
         ("pip-audit", "2.10.1", None), ("pip-requirements-parser", "32.0.1", None),
         ("platformdirs", "4.12.2", None), ("py-serializable", "2.1.0", None),
         ("pygments", "2.21.0", None), ("pyparsing", "3.3.3", None),
         ("requests", "2.34.2", None), ("rich", "15.0.0", None),
         ("sortedcontainers", "2.4.0", None), ("tomli", "2.4.1", None),
         ("tomli-w", "1.2.0", None), ("typing-extensions", "4.16.0", None),
         ("urllib3", "2.8.0", None)]),
    "requirements-lock-certifi.txt": (
        "certifi, Jobs update-test und vorab",
        [WIN, LINUX], [("certifi", "2026.7.22", None)]),
}


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def download(name, version, system, work):
    """Laedt die Raeder einer Fassung fuer ein System, ohne Abhaengigkeiten.
    Gibt die Dateinamen zurueck (kein Rad = Fehler)."""
    target = os.path.join(work, system, "%s-%s" % (name, version))
    os.makedirs(target, exist_ok=True)
    found = set()
    # Zweiter Durchgang nur mit abi3/none: Gibt es neben dem cp312-Rad noch
    # ein abi3-Rad (z.B. charset-normalizer), kommt dessen Pruefsumme dazu.
    for group in PLATTFORMEN[system]:
        for abis, required in ((["cp312", "abi3", "none"], True), (["abi3", "none"], False)):
            command = [sys.executable, "-m", "pip", "download", "--no-deps",
                       "--only-binary=:all:", "--python-version", "3.12",
                       "--implementation", "cp"]
            for abi in abis:
                command += ["--abi", abi]
            for platform_tag in group:
                command += ["--platform", platform_tag]
            command += ["--retries", "10", "--timeout", "60", "--quiet",
                        "-d", target, "%s==%s" % (name, version)]
            result = subprocess.run(command, capture_output=True, text=True)
            if result.returncode != 0 and required:
                raise SystemExit("kein Rad fuer %s %s auf %s (%s):\n%s"
                                 % (name, version, system, group[0], result.stderr[-2000:]))
            found.update(os.listdir(target))
    if not found:
        raise SystemExit("kein Rad fuer %s %s auf %s" % (name, version, system))
    return sorted(os.path.join(target, name_) for name_ in found)


def write_lock(filename, purpose, systems, pins, work):
    lines = ["# Ab 0.63.2 (B-M-05, FG-52): Lock-Datei mit Pruefsummen - NICHT VON HAND",
             "# AENDERN, sondern mit pruefung/lock_erzeugen.py neu erzeugen.",
             "# Zweck: %s." % purpose,
             "# Systeme: %s (Python 3.12). Fassungen wie im Referenzlauf 38443624150." %
             ", ".join(systems),
             "# Installation nur mit: pip install --require-hashes -r %s" % filename]
    for name, version, marker in sorted(pins):
        hashes = set()
        for system in systems:
            if marker == NUR_WINDOWS and system != WIN:
                continue
            if marker == NUR_MAC and system != MAC:
                continue
            if marker == NICHT_WINDOWS and system == WIN:
                continue
            for path in download(name, version, system, work):
                hashes.add(_sha256(path))
        spec = "%s==%s" % (name, version)
        if marker:
            spec += " ; " + marker
        lines.append(spec + " \\")
        ordered = sorted(hashes)
        for index, value in enumerate(ordered):
            end = " \\" if index < len(ordered) - 1 else ""
            lines.append("    --hash=sha256:%s%s" % (value, end))
    with open(os.path.join(ROOT, filename), "w", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(lines) + "\n")
    print("%s: %d Pakete" % (filename, len(pins)))


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    work = os.path.abspath(sys.argv[1])
    only = sys.argv[2:]
    for filename, (purpose, systems, pins) in LOCKS.items():
        if only and filename not in only:
            continue
        write_lock(filename, purpose, systems, pins, work)


if __name__ == "__main__":
    main()
