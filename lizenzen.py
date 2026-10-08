#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fachinformatiker Lernplattform - Hinweise zu Fremdbestandteilen erzeugen (ab 0.62)
=================================================================================

Erzeugt THIRD_PARTY_NOTICES.txt aus dem FERTIGEN PyInstaller-Ordner (Plan 0.62,
Abschnitt 4). build.py ruft das nach PyInstaller auf, unter Windows, Linux und
macOS. Nie von Hand pflegen.

Jede mitgelieferte Programmdatei (erkannt am Dateikopf: ELF, PE, Mach-O) und
jede Schrift wird einem Bestandteil mit Lizenztext zugeordnet:
  * Pillow-Wheel (pillow.libs, PIL/.dylibs, Namen mit Pruefsummen-Endung)
  * Python selbst (libpython, python3*.dll, Standardbibliothek)
  * Linux: Ubuntu-Paket ueber "dpkg -S", Text aus /usr/share/doc/<Paket>/copyright
    des Baurechners (CI: ubuntu-22.04)
  * Windows/macOS: Bibliotheken der Python-Installation (OpenSSL, SQLite, ...)
    nach Namen; den Text sucht das Skript in der LICENSE.txt dieser
    Python-Installation. Steht er dort nicht, wird die Luecke ausdruecklich
    in die Datei geschrieben (Auflage A2) - nichts wird pauschal "erledigt".
  * PyInstaller-Startprogramm, Schriften, Python-Pakete aus *.dist-info

Bleibt eine Datei OHNE Zuordnung, bricht das Skript (und damit der Bau) ab.
So rutscht keine neue Bibliothek unbemerkt ohne Hinweis ins Paket.

Aufruf:
  python lizenzen.py <Programmordner> <Ausgabedatei> [--version 0.62]
  python lizenzen.py <Programmordner> --gegenprobe
        nimmt einer echten Datei kuenstlich die Zuordnung weg und erwartet,
        dass die Pruefung das meldet (T3, je System in der CI)
"""

import datetime
import os
import platform
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
TEXTS = os.path.join(ROOT, "lizenztexte")
APP_NAME = "FISI-Lernplattform"
SECTION_MARK = "#### "      # wie fisi_rechtliches.SECTION_MARK

FONT = re.compile(r"\.(ttf|otf)$", re.I)
PILLOW_HASH = re.compile(r"-[0-9a-f]{8}\.(so|dylib)", re.I)
MAGIC = (b"\x7fELF", b"MZ", b"\xfe\xed\xfa\xce", b"\xfe\xed\xfa\xcf",
         b"\xce\xfa\xed\xfe", b"\xcf\xfa\xed\xfe", b"\xca\xfe\xba\xbe")

# Bibliotheken der Python-Installation unter Windows und macOS: Name ->
# (Bestandteil, Quelle des Textes, Webseite). Quelle "rst:<Abschnitt>" = der
# Abschnitt im Lizenzdokument von Python (lizenztexte/python/license-3.x.rst,
# Teil "Incorporated Software"), "datei:<Name>" = fester Text in lizenztexte/.
# Zuerst wird immer die LICENSE.txt der Python-Installation durchsucht.
PYTHON_LIBS = [
    (r"^lib(crypto|ssl)[-.0-9_a-z]*\.(dll|dylib)$", "OpenSSL", "rst:OpenSSL",
     "https://www.openssl.org/source/license.html"),
    (r"^libffi[-.0-9]*\.(dll|dylib)$", "libffi", "rst:libffi",
     "https://github.com/libffi/libffi/blob/master/LICENSE"),
    (r"^(lib)?sqlite3?[-.0-9]*\.(dll|dylib)$", "SQLite", "datei:sqlite.txt",
     "https://www.sqlite.org/copyright.html"),
    (r"^(zlib1?|libz)[-.0-9]*\.(dll|dylib)$", "zlib", "rst:zlib",
     "https://zlib.net/zlib_license.html"),
    (r"^liblzma[-.0-9]*\.(dll|dylib)$", "XZ Utils (liblzma)", "datei:xz.txt",
     "https://github.com/tukaani-project/xz/blob/master/COPYING"),
    (r"^libbz2[-.0-9]*\.(dll|dylib)$", "bzip2", "datei:bzip2.txt",
     "https://sourceware.org/bzip2/"),
    (r"^libmpdec[-.0-9]*\.(dll|dylib)$", "libmpdec", "rst:libmpdec",
     "https://www.bytereef.org/mpdecimal/"),
    (r"^libexpat[-.0-9]*\.(dll|dylib)$", "expat", "rst:expat",
     "https://github.com/libexpat/libexpat/blob/master/COPYING"),
    (r"^(tcl|tk)\d+t?\.dll$|^tcl(dde|reg)\d+t?\.dll$|^lib(tcl|tk)[\d.]*\.dylib$", "Tcl/Tk",
     None, "https://www.tcl-lang.org/software/tcltk/license.html"),
    (r"^(vcruntime140(_1)?|msvcp140[_0-9a-z]*|ucrtbase|concrt140)\.dll$|^api-ms-win-.*\.dll$",
     "Microsoft Visual C++ Laufzeit und Universal C Runtime", None,
     "https://visualstudio.microsoft.com/license-terms/"),
]



# Name des eigenen Ubuntu-Pakets (wie PACKAGE_NAME in build.py). Ist es auf
# dem Baurechner installiert, meldet dpkg -S die Bibliotheken in
# /opt/fisi-lernplattform/_internal auch als "eigene" Dateien. Das eigene
# Programm ist aber kein Bestandteil Dritter (Gegenpruefung 0.62).
OWN_PACKAGE = "fisi-lernplattform"


def dpkg_owner(output):
    """Erstes fremdes Paket aus der Ausgabe von dpkg -S, oder None."""
    for line in output.splitlines():
        if line.startswith("diversion") or ": /" not in line:
            continue
        for name in line.split(": /")[0].split(","):
            name = name.strip().split(":")[0]
            if name and name != OWN_PACKAGE:
                return name
    return None

class Component:
    def __init__(self, key, name, version="", license_name="", note=""):
        self.key, self.name, self.version = key, name, version
        self.license, self.note = license_name, note
        self.texts = []          # [(Titel, Text)]
        self.files = []
        self.gap = None          # Text, wenn kein Lizenztext gefunden wurde

    def title(self):
        version = " %s" % self.version if self.version else ""
        return "%s%s – %s" % (self.name, version, self.license or "Lizenz siehe Text")


# ============================================================================
#  HILFSFUNKTIONEN
# ============================================================================

def _read(path):
    with open(path, encoding="utf-8", errors="replace") as handle:
        return handle.read().replace("\r\n", "\n")


def _text(name):
    return _read(os.path.join(TEXTS, name))


def is_binary(path):
    try:
        with open(path, "rb") as handle:
            head = handle.read(4)
    except OSError:
        return False
    return any(head.startswith(magic) for magic in MAGIC)


def collect_files(folder):
    """Alle Programmdateien und Schriften im Ordner (ohne symbolische Links)."""
    found = []
    for base, _dirs, names in os.walk(folder):
        for name in names:
            path = os.path.join(base, name)
            if os.path.islink(path):
                continue
            rel = os.path.relpath(path, folder).replace(os.sep, "/")
            if FONT.search(name) or is_binary(path):
                found.append(rel)
    return sorted(found)


def python_license_path():
    """LICENSE.txt der Python-Installation, mit der gebaut wird."""
    version = "python%d.%d" % sys.version_info[:2]
    for base in (sys.base_prefix, sys.prefix):
        for candidate in (os.path.join(base, "LICENSE.txt"),
                          os.path.join(base, "lib", version, "LICENSE.txt"),
                          os.path.join(base, "Lib", "LICENSE.txt"),
                          os.path.join("/usr/lib", version, "LICENSE.txt")):
            if os.path.isfile(candidate):
                return candidate
    return None


def python_license_mentions(text, word):
    """Steht zu word ein eigener Abschnitt in Pythons LICENSE.txt? Gesucht
    wird eine Zeile, die mit dem Wort beginnt oder es als Ueberschrift
    (allein, eingerueckt) enthaelt - eine Erwaehnung im Fliesstext reicht nicht."""
    pattern = re.compile(r"^\s*%s\b[^\n]{0,60}$|includes a copy of %s\b"
                         % (re.escape(word), re.escape(word)), re.M | re.I)
    return bool(pattern.search(text))


def python_rst(version=None):
    """Lizenzdokument von Python passend zur Hauptversion (3.12, 3.14), oder None."""
    version = version or "%d.%d" % sys.version_info[:2]
    path = os.path.join(TEXTS, "python", "license-%s.rst" % version)
    return (path, _read(path)) if os.path.isfile(path) else (None, "")


def rst_sections(text):
    """Ueberschriften des Teils "Incorporated Software" im Lizenzdokument."""
    lines = text.splitlines()
    return [lines[i] for i in range(len(lines) - 1)
            if lines[i].strip() and re.match(r"^-{3,}$", lines[i + 1])]


# ============================================================================
#  PYTHON-PAKETE
# ============================================================================

def runtime_distributions(requirements_file):
    """Pakete aus requirements.txt samt Abhaengigkeiten (ohne Extras)."""
    import importlib.metadata as md
    from packaging.requirements import Requirement
    names = []
    with open(requirements_file, encoding="utf-8") as handle:
        for line in handle:
            line = line.split("#")[0].strip()
            if line and not line.startswith("-"):
                names.append(Requirement(line).name)
    seen, result = set(), []
    while names:
        name = names.pop(0)
        key = re.sub(r"[-_.]+", "-", name).lower()
        if key in seen:
            continue
        seen.add(key)
        try:
            dist = md.distribution(name)
        except md.PackageNotFoundError:
            continue
        result.append(dist)
        for raw in dist.requires or []:
            req = Requirement(raw)
            if req.marker is None or req.marker.evaluate({"extra": ""}):
                names.append(req.name)
    return result


def distribution_component(dist):
    meta = dist.metadata
    license_name = meta.get("License-Expression") or ""
    classifiers = [c.split("::")[-1].strip() for c in meta.get_all("Classifier") or []
                   if c.startswith("License ::")]
    field = (meta.get("License") or "").strip()
    if not license_name:
        license_name = classifiers[0] if classifiers else field.splitlines()[0] if field else ""
    comp = Component("py:" + meta["Name"].lower(), meta["Name"], dist.version, license_name)
    if field and classifiers and "MIT" in " ".join(classifiers) and "Creative Commons" in field:
        comp.note = ("Das Metadatenfeld „License“ nennt „%s“, Klassifikator und "
                     "Lizenzdatei nennen MIT. Übernommen ist die Lizenzdatei." % field)
    for item in dist.files or []:
        upper = str(item).upper()
        if any(word in upper for word in ("LICEN", "COPYING", "NOTICE")) and \
                ".DIST-INFO" in upper:
            try:
                comp.texts.append((str(item).split("/")[-1], _read(dist.locate_file(item))))
            except OSError:
                pass
    if not comp.texts:
        comp.gap = "Lizenzdatei nicht im Paket gefunden"
    return comp


# ============================================================================
#  ZUORDNUNG
# ============================================================================

class Generator:
    def __init__(self, folder, system=None, without=None):
        self.folder = folder
        self.system = system or sys.platform
        self.without = without
        self.components = {}
        self.assigned = {}
        self.unassigned = []
        self.dpkg_cache = {}
        self.python_license = None
        path = python_license_path()
        if path:
            self.python_license = _read(path)

    def comp(self, key, *args, **kwargs):
        if key not in self.components:
            self.components[key] = Component(key, *args, **kwargs)
        return self.components[key]

    # -- feste Bestandteile --------------------------------------------------

    def python_component(self):
        comp = self.comp("python", "Python", platform.python_version(),
                         "PSF-2.0 (Python Software Foundation License)",
                         "Interpreter und Standardbibliothek der Python-Installation, "
                         "mit der gebaut wurde.")
        if not comp.texts:
            if self.python_license:
                comp.texts.append(("LICENSE.txt der Python-Installation", self.python_license))
            else:
                comp.gap = "LICENSE.txt der Python-Installation nicht gefunden"
            path, rst = python_rst()
            if rst:
                comp.texts.append(("Python-Dokumentation „History and License“ (%s), mit "
                                   "den Lizenzen der eingebauten Software"
                                   % os.path.basename(path), rst))
        return comp

    def pyinstaller_component(self):
        import importlib.metadata as md
        try:
            dist = md.distribution("pyinstaller")
        except md.PackageNotFoundError:
            dist = None
        comp = self.comp("pyinstaller", "PyInstaller (Startprogramm und Laufzeit-Hooks)",
                         dist.version if dist else "",
                         "GPL-2.0-or-later WITH Bootloader-exception; Laufzeit-Hooks Apache-2.0")
        if dist and not comp.texts:
            for item in dist.files or []:
                if "COPYING" in str(item).upper():
                    comp.texts.append(("COPYING.txt", _read(dist.locate_file(item))))
        if not comp.texts:
            comp.gap = "COPYING.txt von PyInstaller nicht gefunden"
        return comp

    def tcltk_component(self):
        comp = self.comp("tcltk", "Tcl/Tk", "", "TCL (Tcl/Tk License)")
        if not comp.texts:
            for sub in ("_tcl_data", "_tk_data"):
                for base, _dirs, names in os.walk(self.folder):
                    if os.path.basename(base) == sub and "license.terms" in names:
                        comp.texts.append(("%s/license.terms" % sub,
                                           _read(os.path.join(base, "license.terms"))))
                        break
            # Windows/macOS: Tcl/Tk der Python-Installation
            for base, _dirs, names in os.walk(sys.base_prefix):
                if comp.texts:
                    break
                if "license.terms" in names and re.match(r"^t(cl|k)\d", os.path.basename(base)):
                    comp.texts.append(("%s/license.terms" % os.path.basename(base),
                                       _read(os.path.join(base, "license.terms"))))
            # sonst (macOS: python.org legt license.terms nicht bei) feste Texte
            # aus lizenztexte/tcltk (Quelle siehe lizenztexte/QUELLEN.txt)
            if not comp.texts:
                for name in ("tcl-license.terms", "tk-license.terms"):
                    path = os.path.join(TEXTS, "tcltk", name)
                    if os.path.isfile(path):
                        comp.texts.append((name, _read(path)))
            if not comp.texts and self.python_license and \
                    python_license_mentions(self.python_license, "Tcl"):
                comp.texts.append(("Verweis", "Der Lizenztext steht im Abschnitt zu Tcl/Tk "
                                   "der LICENSE.txt von Python (Bestandteil „Python“ in "
                                   "dieser Datei)."))
            if not comp.texts:
                comp.gap = ("license.terms von Tcl/Tk nicht gefunden, siehe "
                            "https://www.tcl-lang.org/software/tcltk/license.html")
        return comp

    # -- Regeln --------------------------------------------------------------

    def _dpkg_package(self, rel):
        base = os.path.basename(rel)
        if base in self.dpkg_cache:
            return self.dpkg_cache[base]
        try:
            result = subprocess.run(["dpkg", "-S", "*/" + base], capture_output=True, text=True)
            package = dpkg_owner(result.stdout)
        except OSError:
            package = None
        self.dpkg_cache[base] = package
        return package

    def assign(self, rel):
        """Bestandteil fuer eine Datei, oder None."""
        if rel == self.without:
            return None
        base = os.path.basename(rel)
        lower = base.lower()
        # PyInstaller-Startprogramm (die Programmdatei selbst)
        if base in (APP_NAME, APP_NAME + ".exe") and \
                (rel in (APP_NAME, APP_NAME + ".exe") or rel.endswith("MacOS/" + APP_NAME)):
            return self.pyinstaller_component()
        # Schriften
        if FONT.search(base):
            if base.startswith("Roboto"):
                comp = self.comp("roboto", "Roboto (Schrift, in CustomTkinter)", "2.137",
                                 "Apache-2.0", "„Roboto is a trademark of Google“ "
                                 "(Angabe in der Schrift).")
                if not comp.texts:
                    comp.texts.append(("Apache License 2.0", _text("Apache-2.0.txt")))
                return comp
            if base == "CustomTkinter_shapes_font.otf":
                return self.package_component("customtkinter")
            if base == "fisi_symbole.otf":
                comp = self.comp("material", "Material Icons (Teilmenge fisi_symbole.otf)", "",
                                 "Apache-2.0")
                if not comp.texts:
                    comp.texts.append(("fisi_symbole_LIZENZ.txt",
                                       _read(os.path.join(ROOT, "fisi_symbole_LIZENZ.txt"))))
                    comp.texts.append(("Apache License 2.0", _text("Apache-2.0.txt")))
                return comp
            return None
        # Pillow-Wheel mit seinen gebuendelten Bibliotheken
        if rel.startswith(("PIL/", "pillow.libs/")) or "/PIL/" in rel or \
                "pillow.libs/" in rel or PILLOW_HASH.search(base):
            return self.package_component("pillow")
        # Python selbst
        if "lib-dynload/" in rel or lower.startswith("libpython") or \
                re.match(r"^python3\d*\.dll$", lower) or base == "Python" or \
                (lower.endswith(".pyd") and "/" not in rel.replace("_internal/", "", 1)):
            return self.python_component()
        # Linux: Ubuntu-Paket des Baurechners
        if self.system.startswith("linux"):
            package = self._dpkg_package(rel)
            if package:
                return self.ubuntu_component(package)
            if re.match(r"^lib(tcl|tk)[\d.]*\.so", lower):
                return self.tcltk_component()
            return None
        # Windows/macOS: Bibliotheken der Python-Installation
        for pattern, name, word, url in PYTHON_LIBS:
            if re.search(pattern, lower):
                return self.python_lib_component(name, word, url)
        return None

    def package_component(self, name):
        import importlib.metadata as md
        key = "py:" + name.lower()
        if key not in self.components:
            try:
                self.components[key] = distribution_component(md.distribution(name))
            except md.PackageNotFoundError:
                comp = Component(key, name)
                comp.gap = "Paket %s nicht installiert" % name
                self.components[key] = comp
        return self.components[key]

    def ubuntu_component(self, package):
        comp = self.comp("deb:" + package, "%s (Ubuntu-Paket)" % package, "",
                         "siehe copyright-Datei")
        if not comp.texts and not comp.gap:
            path = "/usr/share/doc/%s/copyright" % package
            if os.path.isfile(path):
                comp.texts.append((path, _read(path)))
            else:
                comp.gap = "%s fehlt auf dem Baurechner" % path
        return comp

    def python_lib_component(self, name, source, url):
        if name == "Tcl/Tk":
            return self.tcltk_component()
        key = "pylib:" + name
        if key in self.components:
            return self.components[key]
        comp = self.comp(key, name, "", "")
        word = name.split(" ")[0]
        _path, rst = python_rst()
        if self.python_license and python_license_mentions(self.python_license, word):
            comp.license = "siehe Abschnitt „%s“ in der Python-Lizenz" % word
            comp.texts.append(("Verweis", "Der Lizenztext steht in der LICENSE.txt von "
                               "Python (Bestandteil „Python“ in dieser Datei)."))
            self.python_component()
        elif source and source.startswith("rst:") and source[4:] in rst_sections(rst):
            comp.license = "siehe Abschnitt „%s“ im Lizenzdokument von Python" % source[4:]
            comp.texts.append(("Verweis", "Der Lizenztext steht im Abschnitt „%s“ des "
                               "Lizenzdokuments von Python (Bestandteil „Python“ in "
                               "dieser Datei)." % source[4:]))
            self.python_component()
        elif source and source.startswith("datei:"):
            comp.texts.append((source[6:], _text(source[6:])))
            comp.note = "Text aus dem Quellprojekt (lizenztexte/%s)." % source[6:]
        else:
            comp.gap = ("Lizenztext nicht im Paket enthalten, siehe Webseite des "
                        "Herstellers: %s" % url)
        return comp

    # -- Ablauf --------------------------------------------------------------

    def run(self, requirements_file=None):
        files = collect_files(self.folder)
        for rel in files:
            comp = self.assign(rel)
            if comp is None:
                self.unassigned.append(rel)
            else:
                comp.files.append(rel)
                self.assigned[rel] = comp.key
        # Python-Pakete und feste Bestandteile, auch ohne eigene Binaerdatei
        for dist in runtime_distributions(requirements_file or
                                          os.path.join(ROOT, "requirements.txt")):
            self.package_component(dist.metadata["Name"])
        self.pyinstaller_component()
        self.python_component()
        # Tcl/Tk-Skripte (_tcl_data/_tk_data); unter Linux deckt das Ubuntu-Paket
        # libtcl/libtk sie schon ab
        has_tk = any(os.path.basename(base) == "_tk_data" for base, _d, _n in os.walk(self.folder))
        has_deb = any(key.startswith(("deb:libtcl", "deb:libtk")) for key in self.components)
        if has_tk and not has_deb:
            self.tcltk_component()
        if self.system.startswith("linux"):
            self.appimage_component()
        return files

    def appimage_component(self):
        comp = self.comp("appimage", "AppImage-Laufzeit (type2-runtime, nur im AppImage)",
                         "20251108", "MIT; enthält musl (MIT), libfuse (LGPL-2.1), "
                         "squashfuse (BSD-2-Clause), zstd (BSD-3-Clause), zlib (Zlib)",
                         "Bestandteile laut Hilfetext der Laufzeit. Quellcode: "
                         "https://github.com/AppImage/type2-runtime")
        if not comp.texts:
            for name, title in (("type2-runtime.txt", "type2-runtime"), ("musl.txt", "musl"),
                                ("libfuse-LGPL2.txt", "libfuse (LGPL-2.1)"),
                                ("squashfuse.txt", "squashfuse"), ("zstd.txt", "zstd"),
                                ("zlib.txt", "zlib")):
                comp.texts.append((title, _text(os.path.join("appimage-laufzeit", name))))
        return comp

    def gaps(self):
        return [c for c in self.components.values() if c.gap]

    def summary(self, files):
        return ("Lizenz-Zuordnung: %d Dateien, %d zugeordnet, %d offen; %d Bestandteile, "
                "%d davon ohne Lizenztext im Paket"
                % (len(files), len(self.assigned), len(self.unassigned),
                   len(self.components), len(self.gaps())))

    def render(self, version):
        order = sorted(self.components.values(), key=lambda c: c.name.lower())
        lines = ["Fachinformatiker Lernplattform – Hinweise zu Fremdbestandteilen",
                 "",
                 "Version %s, erzeugt beim Bau am %s auf %s (lizenzen.py)."
                 % (version, datetime.date.today().isoformat(), platform.platform()),
                 "Das Programm enthält die folgenden Bestandteile Dritter. Für sie gelten "
                 "ausschließlich ihre eigenen Lizenzen; die Texte stehen unten in eigenen "
                 "Abschnitten.",
                 ""]
        for comp in order:
            lines.append("• %s (%s)" % (comp.title(), files_text(comp)))
        gaps = [c for c in order if c.gap]
        if gaps:
            lines += ["", "Ohne Lizenztext in dieser Datei:"]
            lines += ["• %s: %s" % (c.name, c.gap) for c in gaps]
        lines.append("")
        written = {}     # gleicher Text (z.B. Apache-2.0) nur einmal ausschreiben
        for comp in order:
            lines.append(SECTION_MARK + comp.title())
            if comp.note:
                lines.append("Hinweis: " + comp.note)
            if comp.gap:
                lines.append("Lizenztext: " + comp.gap)
            if comp.files:
                lines.append("Dateien: " + ", ".join(comp.files))
            for title, text in comp.texts:
                text = text.strip("\n")
                lines += ["", "--- %s ---" % title]
                if text in written and len(text) > 2000:
                    lines.append("(gleicher Text wie bei „%s“, dort vollständig)" % written[text])
                else:
                    written.setdefault(text, comp.title())
                    lines.append(text)
            lines.append("")
        return "\n".join(lines) + "\n"


def files_text(comp):
    if not comp.files:
        if comp.key.startswith("py:"):
            return "Python-Paket im Programmarchiv"
        return "keine eigene Datei im Programmordner"
    return "1 Datei" if len(comp.files) == 1 else "%d Dateien" % len(comp.files)


def generate(folder, output, version="", requirements_file=None):
    gen = Generator(folder)
    files = gen.run(requirements_file)
    print("[..] " + gen.summary(files), flush=True)
    for comp in gen.gaps():
        print("     ohne Text: %s - %s" % (comp.name, comp.gap), flush=True)
    if gen.unassigned:
        raise SystemExit("[FEHLER] Ohne Lizenz-Zuordnung (Regel in lizenzen.py ergaenzen, "
                         "nicht abschalten):\n  " + "\n  ".join(gen.unassigned))
    with open(output, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(gen.render(version))
    print_excerpt(output)
    return gen, files


def print_excerpt(path):
    """Ab 0.62 (Nachforderung N1): Groesse, Kopf und Uebersicht der erzeugten
    Datei ins Bauprotokoll, damit jeder CI-Lauf den Inhalt belegt."""
    with open(path, encoding="utf-8") as handle:
        text = handle.read()
    try:
        sys.stdout.reconfigure(encoding="utf-8")   # Windows-Konsole: Umlaute, Striche
    except (AttributeError, ValueError):
        pass
    head = text.split("\n#### ", 1)[0].rstrip()
    sections = text.count("\n#### ")
    print("[..] %s: %d Byte, %d Abschnitte. Anfang der Datei:" % (
        os.path.basename(path), os.path.getsize(path), sections), flush=True)
    for line in head.splitlines():
        print("     | " + line, flush=True)


def counter_check(folder):
    """T3: einer echten Datei die Zuordnung wegnehmen - die Pruefung muss sie melden."""
    files = collect_files(folder)
    # eine mitgelieferte Bibliothek (nicht die Programmdatei selbst)
    victim = next((f for f in files if not FONT.search(f) and "/" in f), None)
    if victim is None:
        raise SystemExit("[FEHLER] Gegenprobe: keine Programmdatei gefunden")
    gen = Generator(folder, without=victim)
    gen.run()
    if gen.unassigned == [victim]:
        print("[..] Gegenprobe bestanden: %s ohne Zuordnung wurde erkannt (Bau wuerde "
              "abbrechen)." % victim, flush=True)
        return True
    raise SystemExit("[FEHLER] Gegenprobe: erwartet %s, gemeldet %s" % (victim, gen.unassigned))


def main(argv):
    if len(argv) >= 2 and "--gegenprobe" in argv:
        counter_check(argv[1])
        return
    if len(argv) < 3:
        raise SystemExit(__doc__)
    version = argv[argv.index("--version") + 1] if "--version" in argv else ""
    generate(argv[1], argv[2], version)


if __name__ == "__main__":
    main(sys.argv)
