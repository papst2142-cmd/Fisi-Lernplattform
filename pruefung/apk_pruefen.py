#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Android-APK pruefen (ab 0.61, Plan 0.61 T10)
=============================================

Damit die neue APK auf dem Handy als UPDATE der vorhandenen App installiert
wird (und nicht als zweite App ohne Lernstand), muessen Paketkennung und
Signaturzertifikat gleich bleiben. Dieses Skript prueft:

  1. Paketkennung io.github.papst2142cmd.fisi_lernplattform steht im Manifest
  2. Beschriftung unter dem Symbol ist die erwartete (Standard "FI Lernplattform")
  3. Zertifikat (Signatur v2/v3) ist dasselbe wie in der Vergleichs-APK
     (in der CI: die APK des letzten normalen Release)
  4. ab 0.62: LICENSE.txt, THIRD_PARTY_NOTICES.txt und fisi_rechtliches in
     der App (assets/app.zip)

Nur Python, ohne apksigner/Android-SDK. keytool kann diese APKs nicht lesen,
weil sie keine v1-Signatur haben.

Aufruf:  python pruefung/apk_pruefen.py NEU.apk [ALT.apk] [--beschriftung TEXT]
"""

import hashlib
import struct
import sys
import zipfile

PACKAGE = "io.github.papst2142cmd.fisi_lernplattform"
# Ab 0.62: Lizenz und Hinweise zu Fremdbestandteilen muessen in der App liegen
APP_FILES = ("LICENSE.txt", "THIRD_PARTY_NOTICES.txt", "fisi_rechtliches.pyc")
LABEL = "FI Lernplattform"
SIGNATURE_IDS = {0x7109871A: "v2", 0xF05368C0: "v3"}


def manifest_strings(apk_path):
    """String-Pool der binaeren AndroidManifest.xml (Paket, Beschriftung, ...)."""
    data = zipfile.ZipFile(apk_path).read("AndroidManifest.xml")
    offset = 8
    header_size = struct.unpack_from("<HHI", data, offset)[1]
    count, _styles, flags, start, _style_start = struct.unpack_from("<IIIII", data, offset + 8)
    utf8 = flags & (1 << 8)
    positions = struct.unpack_from("<%dI" % count, data, offset + header_size)
    strings = []
    for position in positions:
        p = offset + start + position
        if utf8:
            p += 2 if data[p] & 0x80 else 1          # Laenge in Zeichen (ueberspringen)
            length = data[p]
            if length & 0x80:
                length = ((length & 0x7F) << 8) | data[p + 1]
                p += 1
            p += 1
            strings.append(data[p:p + length].decode("utf-8", "replace"))
        else:
            length = struct.unpack_from("<H", data, p)[0]
            p += 2
            if length & 0x8000:
                length = ((length & 0x7FFF) << 16) | struct.unpack_from("<H", data, p)[0]
                p += 2
            strings.append(data[p:p + 2 * length].decode("utf-16le", "replace"))
    return strings


def _length_prefixed(buffer, offset):
    length = struct.unpack_from("<I", buffer, offset)[0]
    return buffer[offset + 4:offset + 4 + length], offset + 4 + length


def certificates(apk_path):
    """SHA-256 des ersten Signaturzertifikats je Schema, z.B. {"v2": "dccc..."}."""
    with open(apk_path, "rb") as handle:
        data = handle.read()
    end_record = data.rfind(b"PK\x05\x06")
    central = struct.unpack_from("<I", data, end_record + 16)[0]
    if data[central - 16:central] != b"APK Sig Block 42":
        return {}
    size = struct.unpack_from("<Q", data, central - 24)[0]
    position, end = central - size, central - 24
    found = {}
    while position < end:
        length, block_id = struct.unpack_from("<QI", data, position)
        value = data[position + 12:position + 8 + length]
        position += 8 + length
        if block_id in SIGNATURE_IDS:
            signers, _ = _length_prefixed(value, 0)
            signer, _ = _length_prefixed(signers, 0)
            signed, _ = _length_prefixed(signer, 0)
            _digests, offset = _length_prefixed(signed, 0)
            certs, _ = _length_prefixed(signed, offset)
            cert, _ = _length_prefixed(certs, 0)
            found[SIGNATURE_IDS[block_id]] = hashlib.sha256(cert).hexdigest()
    return found


def check(new_apk, old_apk=None, label=LABEL):
    """Liste der Fehler (leer = alles in Ordnung) und Zeilen fuer das Protokoll."""
    errors, lines = [], []
    strings = manifest_strings(new_apk)
    lines.append("Paketkennung %s: %s" % (PACKAGE, "ja" if PACKAGE in strings else "NEIN"))
    if PACKAGE not in strings:
        errors.append("Paketkennung %s fehlt im Manifest" % PACKAGE)
    lines.append("Beschriftung %r: %s" % (label, "ja" if label in strings else "NEIN"))
    if label not in strings:
        errors.append("Beschriftung %r fehlt im Manifest" % label)
    import io
    import zipfile
    app = zipfile.ZipFile(io.BytesIO(zipfile.ZipFile(new_apk).read("assets/app.zip")))
    for name in APP_FILES:
        present = name in app.namelist()
        lines.append("%s in app.zip: %s" % (name, "ja" if present else "NEIN"))
        if not present:
            errors.append("%s fehlt in der App (mobile/vorbereiten.py)" % name)
    new_certs = certificates(new_apk)
    lines.append("Zertifikat neu: %s" % (new_certs or "keins"))
    if not new_certs:
        errors.append("keine Signatur v2/v3 gefunden")
    if old_apk:
        old_certs = certificates(old_apk)
        lines.append("Zertifikat alt: %s" % (old_certs or "keins"))
        new_set, old_set = set(new_certs.values()), set(old_certs.values())
        if not new_set or new_set != old_set:
            errors.append("Zertifikat weicht vom letzten Release ab - die APK wuerde "
                          "nicht als Update installiert")
    return errors, lines


def main(argv):
    args = list(argv)
    label = LABEL
    if "--beschriftung" in args:
        position = args.index("--beschriftung")
        label = args[position + 1]
        del args[position:position + 2]
    if not args:
        print(__doc__)
        return 2
    errors, lines = check(args[0], args[1] if len(args) > 1 else None, label)
    for line in lines:
        print(line)
    for error in errors:
        print("FEHLER: " + error)
    print("APK-Pruefung: %s" % ("bestanden" if not errors else "FEHLGESCHLAGEN"))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
