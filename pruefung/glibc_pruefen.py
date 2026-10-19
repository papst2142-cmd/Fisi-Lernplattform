#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ab 0.63.2 (B-M-06, FG-52): glibc-Bedarf der Linux-Pakete pruefen.

Liest aus jeder ELF-Datei (Programm, .so) die benoetigten Symbol-Fassungen
(Abschnitt .gnu.version_r) und sucht die hoechste "GLIBC_x.y". Sie darf nicht
ueber dem Grundwert liegen: dem hoechsten Bedarf der Linux-Pakete von v0.63.1
(gemessen mit diesem Skript, siehe GRUNDWERT). So laeuft ein neues Paket
weiter auf jedem System, auf dem 0.63.1 lief (aelteres Ubuntu = aeltere glibc).

Geprueft werden Ordner (rekursiv, ohne symbolischen Verknuepfungen zu folgen),
.deb-Pakete (mit dpkg-deb entpackt) und AppImages (die Laufzeit vorn und das
squashfs-Abbild dahinter, mit unsquashfs entpackt; es wird nichts gestartet).

Aufruf:
  python pruefung/glibc_pruefen.py <Ordner|.deb|.AppImage> ...
  python pruefung/glibc_pruefen.py --messen <...>    nur messen, kein Vergleich
Rueckgabe: 0 = hoechstens Grundwert, 1 = darueber, 2 = nichts Pruefbares
(keine ELF-Datei gefunden, Pfad fehlt, Entpacken gescheitert).
"""

import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile

# Hoechster glibc-Bedarf von v0.63.1 (Release-Dateien
# fisi-lernplattform_0.63.1_amd64.deb und FISI-Lernplattform-0.63.1-x86_64.AppImage,
# gemessen am 14.10.2026 mit diesem Skript; Beleg im Bericht N11)
GRUNDWERT = (2, 35)

SHT_GNU_VERNEED = 0x6FFFFFFE
GLIBC = re.compile(r"^GLIBC_(\d+(?:\.\d+)+)$")


class KeinElf(Exception):
    pass


def _version(text):
    return tuple(int(part) for part in text.split("."))


def _text(version):
    return "GLIBC_" + ".".join(str(part) for part in version)


def elf_glibc(data):
    """Menge der GLIBC_x.y-Fassungen, die eine ELF-Datei verlangt (bytes)."""
    if data[:4] != b"\x7fELF":
        raise KeinElf()
    klasse, ordnung = data[4], data[5]
    end = "<" if ordnung == 1 else ">"
    if klasse == 2:
        shoff, = struct.unpack_from(end + "Q", data, 0x28)
        shentsize, shnum = struct.unpack_from(end + "HH", data, 0x3A)
        shdr = end + "IIQQQQIIQQ"
    elif klasse == 1:
        shoff, = struct.unpack_from(end + "I", data, 0x20)
        shentsize, shnum = struct.unpack_from(end + "HH", data, 0x2E)
        shdr = end + "IIIIIIIIII"
    else:
        raise KeinElf()
    sections = []
    for index in range(shnum):
        start = shoff + index * shentsize
        if start + struct.calcsize(shdr) > len(data):
            break
        (_name, typ, _flags, _addr, offset, size, link, info,
         _align, _entsize) = struct.unpack_from(shdr, data, start)
        sections.append((typ, offset, size, link, info))
    found = set()
    for typ, offset, size, link, info in sections:
        if typ != SHT_GNU_VERNEED or link >= len(sections):
            continue
        str_off = sections[link][1]
        pos = offset
        for _ in range(info):                       # Verneed-Eintraege
            (_vn_version, vn_cnt, _vn_file, vn_aux,
             vn_next) = struct.unpack_from(end + "HHIII", data, pos)
            aux = pos + vn_aux
            for _ in range(vn_cnt):                 # Vernaux-Eintraege
                (_hash, _flags, _other, vna_name,
                 vna_next) = struct.unpack_from(end + "IHHII", data, aux)
                name_start = str_off + vna_name
                name_end = data.index(b"\0", name_start)
                name = data[name_start:name_end].decode("ascii", "replace")
                match = GLIBC.match(name)
                if match:
                    found.add(_version(match.group(1)))
                if not vna_next:
                    break
                aux += vna_next
            if not vn_next:
                break
            pos += vn_next
    return found


def _elf_end(data):
    """Ende der ELF-Datei vorn im AppImage (Laufzeit): Abschnittstabelle."""
    klasse = data[4]
    end = "<" if data[5] == 1 else ">"
    if klasse == 2:
        shoff, = struct.unpack_from(end + "Q", data, 0x28)
        shentsize, shnum = struct.unpack_from(end + "HH", data, 0x3A)
    else:
        shoff, = struct.unpack_from(end + "I", data, 0x20)
        shentsize, shnum = struct.unpack_from(end + "HH", data, 0x2E)
    return shoff + shentsize * shnum


def _entpacken(path, work):
    """Gibt den Ordner zurueck, der geprueft wird (Pakete entpackt)."""
    target = tempfile.mkdtemp(dir=work)
    if path.endswith(".deb"):
        subprocess.run(["dpkg-deb", "-x", path, target], check=True)
        return target
    with open(path, "rb") as handle:
        data = handle.read()
    offset = _elf_end(data)
    tool = shutil.which("unsquashfs")
    if not tool:
        raise RuntimeError("unsquashfs fehlt (Paket squashfs-tools)")
    inhalt = os.path.join(target, "inhalt")
    subprocess.run([tool, "-q", "-no-progress", "-o", str(offset), "-d", inhalt, path],
                   check=True, stdout=subprocess.DEVNULL)
    # Die Laufzeit vorn im AppImage ist selbst eine ELF-Datei
    with open(os.path.join(target, "appimage-laufzeit"), "wb") as handle:
        handle.write(data[:offset])
    return target


def messen(paths):
    """{Datei: hoechste GLIBC-Fassung} fuer alle ELF-Dateien; Zahl der ELF-Dateien."""
    ergebnis = {}
    anzahl = 0
    with tempfile.TemporaryDirectory() as work:
        for path in paths:
            if not os.path.exists(path):
                raise FileNotFoundError(path)
            anzeige = os.path.basename(os.path.normpath(path))
            if os.path.isfile(path) and (path.endswith(".deb") or path.endswith(".AppImage")):
                folder = _entpacken(path, work)
            elif os.path.isdir(path):
                folder = path
            else:
                raise RuntimeError("weder Ordner noch .deb noch .AppImage: %s" % path)
            for root, _dirs, names in os.walk(folder):
                for name in sorted(names):
                    full = os.path.join(root, name)
                    if os.path.islink(full) or not os.path.isfile(full):
                        continue
                    with open(full, "rb") as handle:
                        if handle.read(4) != b"\x7fELF":
                            continue
                        handle.seek(0)
                        data = handle.read()
                    try:
                        versions = elf_glibc(data)
                    except (KeinElf, struct.error, ValueError):
                        continue
                    anzahl += 1
                    if versions:
                        ergebnis["%s: %s" % (anzeige, os.path.relpath(full, folder))] = max(versions)
    return ergebnis, anzahl


def main(argv):
    nur_messen = "--messen" in argv
    paths = [arg for arg in argv if arg != "--messen"]
    if not paths:
        print(__doc__)
        return 2
    try:
        ergebnis, anzahl = messen(paths)
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        print("FEHLER glibc-Pruefung: %s" % error)
        return 2
    if not anzahl:
        print("FEHLER glibc-Pruefung: keine ELF-Datei gefunden in %s" % ", ".join(paths))
        return 2
    hoechst = max(ergebnis.values()) if ergebnis else (0,)
    dateien = sorted(name for name, value in ergebnis.items() if value == hoechst)
    print("glibc-Bedarf: %d ELF-Dateien, hoechstens %s (%s)"
          % (anzahl, _text(hoechst), "; ".join(dateien[:5])))
    if nur_messen:
        return 0
    zu_hoch = sorted((name, value) for name, value in ergebnis.items() if value > GRUNDWERT)
    if zu_hoch:
        print("FEHLER glibc-Bedarf ueber dem Grundwert %s (v0.63.1):" % _text(GRUNDWERT))
        for name, value in zu_hoch:
            print("  %s verlangt %s" % (name, _text(value)))
        return 1
    print("glibc-Pruefung bestanden: hoechstens %s, Grundwert %s (v0.63.1)"
          % (_text(hoechst), _text(GRUNDWERT)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
