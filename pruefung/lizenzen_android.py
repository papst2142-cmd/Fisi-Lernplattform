#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hinweise zu Fremdbestandteilen der Handy-App aus der APK (ab 0.62, Plan 4.5)
===========================================================================

Weg B (Nicos Entscheidung E5): Dieses Skript liest eine fertige APK und
erzeugt mobile/lizenzen_android.txt (im Repo, erzeugt - nie von Hand
pflegen). mobile/vorbereiten.py legt die Datei als THIRD_PARTY_NOTICES.txt in
die App. In der CI liest der Schritt nach dem APK-Bau die NEUE APK aus und
vergleicht (--pruefen): Weicht etwas ab (neue Flet-, Flutter- oder
AndroidX-Fassung), wird der Lauf rot und nennt den Befehl zum Neuerzeugen.

Gelesen wird aus der APK:
  * assets/flutter_assets/NOTICES.Z   Flutters Sammlung (Engine, Dart-Pakete)
  * META-INF/*.version                AndroidX- und kotlinx-Module mit Version
  * kotlin-tooling-metadata.json      Kotlin-Fassung
  * assets/sitepackages.zip           Python-Pakete (*.dist-info)
  * assets/stdlib.zip                 LICENSE.txt von Python
  * lib/<abi>/*.so                    jede Bibliothek braucht eine Regel
  * Schriften (*.ttf, *.otf)          jede Schrift braucht eine Regel

Bleibt eine Bibliothek oder Schrift ohne Regel, bricht das Skript ab.
Die Datei enthaelt kein Datum und keine App-Version, damit sie nur bei
echten Aenderungen der Bestandteile abweicht.

Aufruf:
  python pruefung/lizenzen_android.py <APK> --schreiben   Datei neu erzeugen
  python pruefung/lizenzen_android.py <APK> --pruefen     mit der Datei vergleichen
"""

import difflib
import gzip
import io
import json
import os
import re
import struct
import sys
import zipfile
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TEXTS = os.path.join(ROOT, "lizenztexte")
TARGET = os.path.join(ROOT, "mobile", "lizenzen_android.txt")
SECTION_MARK = "#### "            # wie fisi_rechtliches.SECTION_MARK
NOTICES_SEPARATOR = "-" * 80
CHUNK = 60000                     # Flutter-Sammlung in Teilen (Anzeige am Handy)

# Bibliotheken, die Pythons Erweiterungsmodule fest eingebaut mitbringen
# (gemessen in der APK 0.61): Modul -> (Bestandteil, Text, Versions-Suchmuster)
BUILTIN = {
    "lib_bz2.so": ("bzip2", "datei:bzip2.txt", rb"(1\.0\.\d+), \d+-\w+-\d{4}"),
    "lib_lzma.so": ("XZ Utils (liblzma)", "datei:xz.txt", rb"\b(5\.\d+\.\d+)\b"),
    "lib_zstd.so": ("Zstandard (zstd)", "datei:appimage-laufzeit/zstd.txt",
                    rb"zstd-(\d+\.\d+\.\d+)"),
    "lib_ctypes.so": ("libffi", "rst:libffi", None),
    "libpyexpat.so": ("expat", "rst:expat", rb"expat_(\d+\.\d+\.\d+)"),
    "lib_decimal.so": ("libmpdec", "rst:libmpdec", None),
}


def read_text(name):
    with open(os.path.join(TEXTS, name), encoding="utf-8") as handle:
        return handle.read().replace("\r\n", "\n")


# ============================================================================
#  HILFEN: ELF, SCHRIFTEN
# ============================================================================

def elf_needed(data):
    """NEEDED-Eintraege einer 64-Bit-ELF-Datei (little endian), sonst []."""
    if data[:4] != b"\x7fELF" or data[4] != 2 or data[5] != 1:
        return []
    shoff, = struct.unpack_from("<Q", data, 0x28)
    shentsize, shnum = struct.unpack_from("<HH", data, 0x3A)
    sections = [struct.unpack_from("<IIQQQQIIQQ", data, shoff + i * shentsize)
                for i in range(shnum)]
    for sec in sections:
        if sec[1] != 6:                       # SHT_DYNAMIC
            continue
        strtab = sections[sec[6]]             # sh_link -> .dynstr
        names = []
        for pos in range(sec[4], sec[4] + sec[5], 16):
            tag, value = struct.unpack_from("<qQ", data, pos)
            if tag == 0:
                break
            if tag == 1:                      # DT_NEEDED
                start = strtab[4] + value
                names.append(data[start:data.index(b"\0", start)].decode())
        return names
    return []


def font_names(data):
    """Copyright (Name-ID 0) und Version (Name-ID 5) aus der name-Tabelle."""
    count, = struct.unpack_from(">H", data, 4)
    result = {}
    for i in range(count):
        tag, _check, offset, _length = struct.unpack_from(">4sIII", data, 12 + 16 * i)
        if tag != b"name":
            continue
        _fmt, records, string_offset = struct.unpack_from(">HHH", data, offset)
        for r in range(records):
            platform, _enc, _lang, name_id, length, pos = struct.unpack_from(
                ">HHHHHH", data, offset + 6 + 12 * r)
            if name_id not in (0, 5) or name_id in result:
                continue
            raw = data[offset + string_offset + pos:offset + string_offset + pos + length]
            result[name_id] = raw.decode("utf-16-be" if platform in (0, 3) else "latin-1")
    return result.get(0, ""), result.get(5, "")


# ============================================================================
#  ERZEUGEN
# ============================================================================

class Section:
    def __init__(self, title, license_name, files=(), note=""):
        self.title, self.license, self.files, self.note = title, license_name, list(files), note
        self.texts = []

    def heading(self):
        return "%s – %s" % (self.title, self.license)


class AndroidNotices:
    def __init__(self, apk_path):
        self.apk = zipfile.ZipFile(apk_path)
        self.names = self.apk.namelist()
        self.sections = {}
        self.unassigned = []
        self.python_minor = None

    def section(self, key, *args, **kwargs):
        if key not in self.sections:
            self.sections[key] = Section(*args, **kwargs)
        return self.sections[key]

    # -- Python ----------------------------------------------------------------

    def python(self):
        sec = self.sections.get("python")
        if sec:
            return sec
        version = self.python_minor or "3"
        sec = self.section("python", "Python %s (Interpreter und Standardbibliothek)" % version,
                           "PSF-2.0 (Python Software Foundation License)")
        stdlib = zipfile.ZipFile(io.BytesIO(self.apk.read("assets/stdlib.zip")))
        sec.texts.append(("LICENSE.txt aus stdlib.zip",
                          stdlib.read("LICENSE.txt").decode("utf-8")))
        path = os.path.join(TEXTS, "python", "license-%s.rst" % version)
        if not os.path.isfile(path):
            raise SystemExit("[FEHLER] lizenztexte/python/license-%s.rst fehlt - Doc/license.rst "
                             "der passenden Python-Fassung ablegen (siehe QUELLEN.txt)" % version)
        sec.texts.append(("Python-Dokumentation „History and License“ (license-%s.rst), mit "
                          "den Lizenzen der eingebauten Software" % version, read_text(
                              os.path.join("python", "license-%s.rst" % version))))
        return sec

    def builtin(self, lib, data):
        name, source, pattern = BUILTIN[lib]
        version = ""
        if pattern:
            match = re.search(pattern, data)
            version = " " + match.group(1).decode() if match else ""
        sec = self.section("builtin:" + name, name + version,
                           "siehe Text", note="fest eingebaut in %s (Python-Modul)" % lib)
        if source.startswith("datei:"):
            sec.texts.append((source[6:].split("/")[-1], read_text(source[6:])))
        else:
            sec.license = "siehe Abschnitt „%s“ im Lizenzdokument von Python" % source[4:]
            sec.texts.append(("Verweis", "Der Lizenztext steht im Abschnitt „%s“ des "
                              "Lizenzdokuments von Python (Abschnitt „Python“ in dieser "
                              "Datei)." % source[4:]))

    # -- Regeln für Bibliotheken ---------------------------------------------

    def assign_library(self, path, data):
        base = path.split("/")[-1]
        needed = elf_needed(data)
        if base in ("libflutter.so", "libapp.so"):
            return self.flutter()
        if base == "libdart_bridge.so":
            return self.flutter(note_package="serious_python")
        if base == "libdartjni.so":
            return self.flutter(note_package="jni")
        if base == "libdatastore_shared_counter.so":
            return self.androidx()
        if base.startswith(("libcrypto_python", "libssl_python")):
            match = re.search(rb"OpenSSL (\d+\.\d+\.\d+)", data)
            sec = self.section("openssl", "OpenSSL %s" % (match.group(1).decode() if match else ""),
                               "Apache-2.0")
            if not sec.texts:
                sec.texts.append(("Apache License 2.0", read_text("Apache-2.0.txt")))
            return sec
        if base.startswith("libsqlite3_python"):
            match = re.search(rb"\b(3\.\d+\.\d+)\b", data)
            sec = self.section("sqlite", "SQLite %s" % (match.group(1).decode() if match else ""),
                               "Public Domain")
            if not sec.texts:
                sec.texts.append(("sqlite.txt", read_text("sqlite.txt")))
            return sec
        if base.startswith("libmsgpack"):
            return self.sections.get("py:msgpack")
        match = re.match(r"^libpython(3\.\d+)\.so$", base)
        if match:
            self.python_minor = match.group(1)
            return self.python()
        if any(n.startswith("libpython3") for n in needed):
            if base in BUILTIN:
                self.builtin(base, data)
            return self.python()
        return None

    # -- Flutter ----------------------------------------------------------------

    def flutter(self, note_package=None):
        sec = self.section("flutter", "Flutter-Engine, Flutter und Dart-Pakete (Flutter-Sammlung)",
                           "je Paket, siehe Teile der Flutter-Sammlung",
                           note="libflutter.so ist die Flutter-Engine, libapp.so der übersetzte "
                                "Dart-Code (Flutter, Flet-Oberfläche und die Dart-Pakete). Die "
                                "Texte stehen in den Abschnitten „Flutter-Sammlung, Teil …“.")
        if note_package and note_package not in sec.note:
            sec.note += " %s gehört zum Dart-Paket „%s“." % (
                "libdart_bridge.so" if note_package == "serious_python" else "libdartjni.so",
                note_package)
        return sec

    def flutter_parts(self):
        raw = self.apk.read("assets/flutter_assets/NOTICES.Z")
        text = (gzip.decompress(raw) if raw[:2] == b"\x1f\x8b" else zlib.decompress(raw)).decode()
        blocks = [b.strip("\n") for b in text.split("\n" + NOTICES_SEPARATOR + "\n") if b.strip()]
        packages = set()
        for block in blocks:
            head = block.split("\n\n")[0]
            packages.update(line.strip() for line in head.splitlines() if line.strip())
        parts, current = [], []
        for block in blocks:
            if current and sum(len(b) for b in current) + len(block) > CHUNK:
                parts.append(current)
                current = []
            current.append(block)
        if current:
            parts.append(current)
        return len(blocks), sorted(packages), parts

    # -- AndroidX / Kotlin ------------------------------------------------------

    def androidx(self):
        sec = self.sections.get("androidx")
        if sec:
            return sec
        modules = []
        for name in sorted(self.names):
            match = re.match(r"^META-INF/(.+)\.version$", name)
            if match:
                modules.append("%s %s" % (match.group(1), self.apk.read(name).decode().strip()))
        sec = self.section("androidx", "AndroidX- und kotlinx-Bibliotheken (Java/Kotlin, %d Module)"
                           % len(modules), "Apache-2.0",
                           note="Module laut META-INF/*.version der APK (keine Gradle-Auswertung): "
                                + "; ".join(modules))
        lic = "META-INF/androidx/annotation/annotation/LICENSE.txt"
        if lic in self.names:
            sec.texts.append((lic, self.apk.read(lic).decode("utf-8")))
        else:
            sec.texts.append(("Apache License 2.0", read_text("Apache-2.0.txt")))
        return sec

    def kotlin(self):
        version = ""
        if "kotlin-tooling-metadata.json" in self.names:
            meta = json.loads(self.apk.read("kotlin-tooling-metadata.json"))
            version = meta.get("buildPluginVersion", "")
        sec = self.section("kotlin", "Kotlin-Standardbibliothek (JetBrains)%s"
                           % (", Kotlin %s" % version if version else ""), "Apache-2.0",
                           note="Fassung laut kotlin-tooling-metadata.json (Kotlin-Gradle-Plugin).")
        sec.texts.append(("Apache License 2.0", read_text("Apache-2.0.txt")))

    # -- Python-Pakete ----------------------------------------------------------

    def python_packages(self):
        site = zipfile.ZipFile(io.BytesIO(self.apk.read("assets/sitepackages.zip")))
        infos = sorted({n.split("/")[0] for n in site.namelist() if ".dist-info/" in n})
        for info in infos:
            meta = site.read(info + "/METADATA").decode("utf-8", "replace")
            fields = {}
            for line in meta.split("\n\n")[0].splitlines():
                key, _sep, value = line.partition(": ")
                fields.setdefault(key, value.strip())
            classifiers = [l.split("::")[-1].strip() for l in meta.splitlines()
                           if l.startswith("Classifier: License ::")]
            license_name = fields.get("License-Expression") or (classifiers[0] if classifiers
                                                                 else fields.get("License", ""))
            name = fields.get("Name", info)
            sec = self.section("py:" + name.lower(), "%s %s (Python-Paket)"
                               % (name, fields.get("Version", "")), license_name or "siehe Text")
            for item in sorted(site.namelist()):
                upper = item.upper()
                if item.startswith(info + "/") and any(w in upper for w in ("LICEN", "COPYING",
                                                                           "NOTICE")):
                    sec.texts.append((item.split("/")[-1], site.read(item).decode("utf-8", "replace")))
            if not sec.texts:
                if license_name == "Apache-2.0":
                    sec.note = ("Das Paket bringt keine Lizenzdatei mit; laut Paketangaben "
                                "(License-Expression) gilt Apache-2.0.")
                    sec.texts.append(("Apache License 2.0", read_text("Apache-2.0.txt")))
                else:
                    raise SystemExit("[FEHLER] Python-Paket %s ohne Lizenzdatei und ohne bekannte "
                                     "Lizenz (%r) - Regel ergaenzen" % (name, license_name))

    # -- Schriften ----------------------------------------------------------------

    def assign_font(self, path, data):
        base = path.split("/")[-1]
        if base.startswith("KaTeX_"):
            copyright_text, version = font_names(data)
            sec = self.section("katex", "KaTeX-Schriften (im Dart-Paket flutter_math_fork)",
                               "OFL-1.1 (SIL Open Font License)",
                               note="Angaben aus den Schriften: %s; %s"
                                    % (copyright_text.replace("\n", " "), version))
            if not sec.texts:
                sec.texts.append(("SIL Open Font License 1.1", read_text("OFL-1.1.txt")))
            return sec
        if base == "MaterialIcons-Regular.otf":
            sec = self.section("material", "Material Icons (Schrift, Teil von Flutter)",
                               "Apache-2.0")
            if not sec.texts:
                sec.texts.append(("Apache License 2.0", read_text("Apache-2.0.txt")))
            return sec
        if base == "CupertinoIcons.ttf":
            return self.flutter()       # Dart-Paket cupertino_icons, Text in der Sammlung
        return None

    # -- Ablauf -------------------------------------------------------------------

    def run(self):
        self.python_packages()
        libs = sorted(n for n in self.names if re.match(r"^lib/[^/]+/[^/]+\.so$", n))
        fonts = sorted(n for n in self.names if re.search(r"\.(ttf|otf)$", n, re.I))
        # libpython zuerst: liefert die Python-Fassung fuer den Abschnitt
        libs.sort(key=lambda n: not n.split("/")[-1].startswith("libpython"))
        for path in libs:
            sec = self.assign_library(path, self.apk.read(path))
            self._file(sec, path)
        for path in fonts:
            sec = self.assign_font(path, self.apk.read(path))
            self._file(sec, path)
        self.kotlin()
        self.androidx()
        if self.unassigned:
            raise SystemExit("[FEHLER] Ohne Lizenz-Zuordnung (Regel in pruefung/lizenzen_android.py "
                             "ergaenzen, nicht abschalten):\n  " + "\n  ".join(self.unassigned))
        return len(libs) + len(fonts)

    def _file(self, sec, path):
        if sec is None:
            self.unassigned.append(path)
        else:
            sec.files.append(path.split("/")[-1])

    def render(self):
        count_blocks, packages, parts = self.flutter_parts()
        order = sorted(self.sections.values(), key=lambda s: s.title.lower())
        lines = ["Fachinformatiker Lernplattform (Android) – Hinweise zu Fremdbestandteilen",
                 "",
                 "Erzeugt aus der Android-APK mit pruefung/lizenzen_android.py.",
                 "Die App enthält die folgenden Bestandteile Dritter. Für sie gelten "
                 "ausschließlich ihre eigenen Lizenzen; die Texte stehen unten in eigenen "
                 "Abschnitten.",
                 ""]
        for sec in order:
            lines.append("• " + sec.heading())
        lines.append("• Flutter-Sammlung: %d Lizenztexte zu %d Paketen in %d Teilen"
                     % (count_blocks, len(packages), len(parts)))
        lines.append("")
        written = {}
        for sec in order:
            lines.append(SECTION_MARK + sec.heading())
            if sec.note:
                lines.append("Hinweis: " + sec.note)
            if sec.files:
                lines.append("Dateien: " + ", ".join(sorted(set(sec.files))))
            for title, text in sec.texts:
                text = text.strip("\n")
                lines += ["", "--- %s ---" % title]
                if text in written and len(text) > 2000:
                    lines.append("(gleicher Text wie bei „%s“, dort vollständig)" % written[text])
                else:
                    written.setdefault(text, sec.heading())
                    lines.append(text)
            lines.append("")
        for number, blocks in enumerate(parts, 1):
            names = []
            for block in blocks:
                for line in block.split("\n\n")[0].splitlines():
                    if line.strip() and line.strip() not in names:
                        names.append(line.strip())
            shown = ", ".join(names[:6]) + (" …" if len(names) > 6 else "")
            lines.append("%sFlutter-Sammlung, Teil %d von %d: %s"
                         % (SECTION_MARK, number, len(parts), shown))
            lines.append("Pakete in diesem Teil: " + ", ".join(names))
            for block in blocks:
                lines += ["", NOTICES_SEPARATOR, block]
            lines.append("")
        return "\n".join(lines) + "\n"


def generate(apk_path):
    notices = AndroidNotices(apk_path)
    count = notices.run()
    # einheitliche Zeilenenden (einige Lizenztexte kommen mit CR/LF)
    text = notices.render().replace("\r\n", "\n").replace("\r", "\n")
    print("[..] Android-Lizenzliste: %d Bibliotheken und Schriften, alle zugeordnet; %d Abschnitte, "
          "%d Zeichen" % (count, text.count("\n" + SECTION_MARK), len(text)), flush=True)
    return text


def main(argv):
    if len(argv) < 3 or argv[2] not in ("--schreiben", "--pruefen"):
        raise SystemExit(__doc__)
    text = generate(argv[1])
    if argv[2] == "--schreiben":
        with open(TARGET, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
        print("[..] geschrieben: %s" % os.path.relpath(TARGET, ROOT))
        return
    with open(TARGET, encoding="utf-8", newline="") as handle:
        old = handle.read()
    if old == text:
        print("[..] mobile/lizenzen_android.txt passt zur APK.")
        return
    diff = list(difflib.unified_diff(old.splitlines(), text.splitlines(),
                                     "im Repo", "aus der APK", lineterm="", n=0))
    print("\n".join(diff[:80]))
    raise SystemExit("[FEHLER] mobile/lizenzen_android.txt passt nicht mehr zur APK (%d geaenderte "
                     "Zeilen). Neu erzeugen und committen:\n"
                     "  python pruefung/lizenzen_android.py <APK aus diesem Lauf> --schreiben"
                     % sum(1 for l in diff if l[:1] in "+-" and l[:3] not in ("+++", "---")))


if __name__ == "__main__":
    main(sys.argv)
