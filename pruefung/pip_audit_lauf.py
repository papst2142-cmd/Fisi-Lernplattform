#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ab 0.63.2 (B-N-12, FG-52): bekannte Sicherheitsluecken in den Fremdpaketen.

Prueft mit pip-audit (feste Fassung, aus requirements-lock-pip-audit.txt mit
Pruefsummen, in eigener Umgebung) alle Pakete der angegebenen Lock-Dateien
gegen die Lueckendatenbank von PyPI. Es wird nichts installiert: pip-audit
liest nur Name und Fassung (--disable-pip --no-deps); die Lock-Dateien
enthalten schon alle Abhaengigkeiten.

Verhalten (F26 (b), N11-F6, N11-F7, N11-F8):
  * keine Funde                 -> Rueckgabe 0, keine Warnung
  * Funde, normaler Lauf        -> je Fund eine Warnung (::warning::), Rueckgabe 0
  * Funde, Release-Lauf         -> je Fund ein Fehler (::error::), Rueckgabe 1:
                                   der Release wird nicht veroeffentlicht
  * Pruefdienst nicht erreichbar -> erst 3 Versuche (wie die Netz-
                                   Wiederholungen aus N10), dann
                                   normaler Lauf: Warnung "nicht pruefbar", Rueckgabe 0
                                   Release-Lauf:  Fehler "nicht pruefbar", Rueckgabe 1
  * Testversionen (Feld "vorab") sind keine Release-Laeufe: nur Warnungen.
  * Es gibt keine Ausnahmeliste: jeder Fund wird gemeldet.
Release-Lauf heisst: Umgebungsvariable IS_RELEASE == "true" (build.yml).

Grenze: Geprueft werden nur Python-Pakete von PyPI. Die Python-Laufzeiten,
Tcl/Tk, die Android-Laufzeit und die Flutter-/Dart-Teile prueft pip-audit nicht.

Aufruf:
  python pruefung/pip_audit_lauf.py --pip-audit <Pfad zu pip-audit> <lock> ...
"""

import json
import os
import re
import subprocess
import sys
import tempfile
import time

VERSUCHE = 3
PIN = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*)==([^\s;\\]+)")


def pins(lock_path):
    """[(Name, Fassung)] einer Lock-Datei, ohne Marken und Pruefsummen."""
    found = []
    with open(lock_path, encoding="utf-8") as handle:
        for line in handle:
            match = PIN.match(line.strip())
            if match:
                found.append((match.group(1), match.group(2)))
    if not found:
        raise ValueError("keine Pakete in %s" % lock_path)
    return found


def _audit(tool, requirements, output):
    """Ein Lauf von pip-audit. Gibt das gelesene JSON zurueck oder None und
    den Grund, wenn nicht geprueft werden konnte."""
    if os.path.exists(output):
        os.remove(output)
    command = [tool, "--requirement", requirements, "--disable-pip", "--no-deps",
               "--format", "json", "--output", output, "--progress-spinner", "off",
               "--vulnerability-service", "pypi", "--timeout", "60"]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=900)
    except (OSError, subprocess.TimeoutExpired) as error:
        return None, "pip-audit nicht ausfuehrbar: %s" % error
    try:
        with open(output, encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        tail = (result.stderr or result.stdout or "").strip().splitlines()[-3:]
        return None, "Rueckgabe %d, keine Ergebnisliste (%s)" % (
            result.returncode, " | ".join(tail) or "keine Ausgabe")
    if not isinstance(data, dict) or not isinstance(data.get("dependencies"), list):
        return None, "Ergebnisliste unbekannten Formats"
    skipped = [dep for dep in data["dependencies"] if dep.get("skip_reason")]
    if skipped:
        return None, "nicht geprueft: " + "; ".join(
            "%s (%s)" % (dep.get("name"), dep.get("skip_reason")) for dep in skipped)
    if result.returncode not in (0, 1):
        return None, "Rueckgabe %d" % result.returncode
    return data, ""


def main(argv):
    if len(argv) < 3 or argv[0] != "--pip-audit":
        print(__doc__)
        return 2
    tool, locks = argv[1], argv[2:]
    release = os.environ.get("IS_RELEASE", "") == "true"
    pause = float(os.environ.get("PIP_AUDIT_PAUSE", "10"))
    art = "Release-Lauf" if release else "normaler Lauf (Warnung, blockiert nicht)"
    print("pip-audit: %s, %d Lock-Dateien" % (art, len(locks)))

    alle = {}
    for lock in locks:
        for name, version in pins(lock):
            alle.setdefault((name.lower(), version), []).append(os.path.basename(lock))
    with tempfile.TemporaryDirectory() as work:
        requirements = os.path.join(work, "pakete.txt")
        with open(requirements, "w", encoding="utf-8") as handle:
            for name, version in sorted(alle):
                handle.write("%s==%s\n" % (name, version))
        output = os.path.join(work, "ergebnis.json")
        data, grund = None, ""
        for versuch in range(1, VERSUCHE + 1):
            data, grund = _audit(tool, requirements, output)
            if data is not None:
                break
            if versuch < VERSUCHE:
                print("Wiederholung wegen Netzfehler (pip-audit, Versuch %d): %s" % (versuch, grund))
                sys.stdout.flush()
                time.sleep(pause)

    if data is None:
        text = ("pip-audit nicht pruefbar nach %d Versuchen: %s" % (VERSUCHE, grund))
        if release:
            print("::error title=pip-audit nicht pruefbar::%s" % text)
            print("Release wird nicht veroeffentlicht: Die Pakete liessen sich nicht auf "
                  "bekannte Sicherheitsluecken pruefen (Pruefdienst nicht erreichbar).")
            return 1
        print("::warning title=pip-audit nicht pruefbar::%s" % text)
        return 0

    funde = []
    for dep in data["dependencies"]:
        for vuln in dep.get("vulns") or []:
            funde.append((dep.get("name", "?"), dep.get("version", "?"), vuln))
    print("pip-audit: %d Pakete geprueft, %d Funde" % (len(data["dependencies"]), len(funde)))
    if not funde:
        return 0
    stufe = "error" if release else "warning"
    for name, version, vuln in funde:
        fix = ", ".join(vuln.get("fix_versions") or []) or "keine"
        quellen = ", ".join(alle.get((name.lower(), version), [])) or "?"
        print("::%s title=pip-audit::%s %s: %s (behoben in: %s; Lock-Datei: %s)"
              % (stufe, name, version, vuln.get("id", "?"), fix, quellen))
    if release:
        print("Release wird nicht veroeffentlicht: pip-audit meldet %d bekannte "
              "Sicherheitsluecke(n). Jeder Fund geht einzeln an Chat (keine Ausnahmeliste)."
              % len(funde))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
