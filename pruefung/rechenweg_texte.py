#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ab 0.62.3 (Teil E): erzeugt alle Texte der Rechner, Rechenwege, USV-Aufgaben
und Trainer-Aufgaben und zieht daraus die angezeigten Zahlen.

Gebraucht von test_rechenweg.py (Test 4 und 9) und einmalig fuer die
Ausgangsbasis auf v0.62.2 (pruefung/rechenweg_basis_0622.json):

    python pruefung/rechenweg_texte.py QUELLORDNER AUSGABE.json

QUELLORDNER ist ein Stand des Repos (z.B. aus "git archive ff1000c").
Die Eingaben sind dieselben wie in der Pruefung e3 (Plan 0.62.2 Teil E).
"""

import json
import os
import re
import sys
from decimal import Decimal

# Eingaben wie in e3_nachrechnung.py (Abschnitte 6 bis 10)
SUBNET_INPUTS = ["192.168.1.50/24", "10.0.0.0/255.255.255.0", "172.16.5.130/26",
                 "192.168.10.1/30", "192.168.10.1/31", "192.168.10.7/32", "10.20.30.40/8",
                 "172.20.200.17/12", "2001:db8::1/64", "2001:db8:abcd:12::/48",
                 "fe80::1/10", "2001:db8::1/127", "2001:db8::1/128"]
RAID_INPUTS = [("RAID 5", "4", "1000"), ("RAID 0", "4", "1000"), ("RAID 1", "4", "1000"),
               ("RAID 6", "4", "1000"), ("RAID 10", "4", "1000"), ("RAID 1", "2", "1000"),
               ("RAID 10", "5", "1000"), ("RAID 10", "6", "2000"), ("RAID 0", "1", "1000"),
               ("RAID 5", "2", "1000"), ("RAID 5", "4", "1,5"), ("RAID 5", "3", "0,5"),
               ("RAID 6", "5", "4000"), ("RAID 10", "8", "1000")]
SCREEN_INPUTS = [("1920", "1080", "24", "0"), ("1920", "1080", "24", "30"),
                 ("1920", "1080", "24", ""), ("1920", "1080", "24", "29,97"),
                 ("1280", "720", "8", "25"), ("3840", "2160", "32", "60"),
                 ("800", "600", "16", "0")]
TRAINER_SEEDS = 40


def erzeuge(fc, fl):
    """Alle Texte als {Quelle: Text}. fc = fisi_core, fl = fisi_lernen."""
    out = {}
    for name in ("CALC_EXPLAIN_SUBNET", "CALC_EXPLAIN_RAID", "CALC_EXPLAIN_SCREEN",
                 "CALC_EXPLAIN_UPS", "UPS_RULE_TEXT", "UPS_SIMPLE_TEXT"):
        out["text:" + name] = getattr(fc, name)
    for value in SUBNET_INPUTS:
        out["subnet:" + value] = fc.subnet_report(value)
    for level, disks, size in RAID_INPUTS:
        out["raid:%s|%s|%s" % (level, disks, size)] = fc.raid_report(level, disks, size)
    for width, height, depth, fps in SCREEN_INPUTS:
        out["screen:%s|%s|%s|%s" % (width, height, depth, fps)] = fc.screen_report(
            width, height, depth, fps)
    defaults = dict(fc.UPS_FIELD_DEFAULTS)
    for mode, _caption in fc.UPS_MODES:
        out["ups:%s" % mode] = fc.ups_calculate(mode, defaults, "W")["text"]
    out["ups:empfehlung|last=1200|VA"] = fc.ups_calculate(
        "empfehlung", dict(defaults, last="1200"), "VA")["text"]
    out["ups:empfehlung|nenn_w leer"] = fc.ups_calculate(
        "empfehlung", dict(defaults, nenn_w=""), "W")["text"]
    for index in range(len(fc.UPS_TASKS)):
        out["upsaufgabe:%d" % index] = fc.ups_task_text(index, True)
    for kind, _name in fl.TRAINER_KINDS:
        for level, _label in fl.TRAINER_LEVELS:
            for seed in range(TRAINER_SEEDS):
                out["trainer:%s|%d|%d" % (kind, level, seed)] = trainer_text(
                    fl.trainer_task(kind, level, "e3-%d" % seed))
    return out


def trainer_text(task):
    """Alles, was eine Trainer-Aufgabe anzeigt, als ein Text."""
    lines = ["Aufgabe: " + task.text]
    lines += ["Feld: %s" % label for _key, label in task.fields]
    lines += ["Lösung %s: %s" % (key, task.solution[key]) for key, _label in task.fields]
    lines += task.steps
    return "\n".join(lines)


# ---------------------------------------------------------------------------
#  Zahlen aus einem Text ziehen
# ---------------------------------------------------------------------------
# Feste Bausteine zuerst, damit "192.168.1.0" nicht als Zahl 192.168,1 gilt.
# Eine IPv4-Adresse hat genau vier Oktette 0-255 ohne fuehrende Null - so
# bleibt "18.446.744.073.709.551.616" eine Zahl.
_OKTETT = r"(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)"
_TOKEN = re.compile(
    r"(?P<bits>[01]{8}(?:\.[01]{8}){3})"
    r"|(?P<ip4>(?<![\d.])" + _OKTETT + r"(?:\." + _OKTETT + r"){3}(?!\d|\.\d))"
    r"|(?P<ip6>(?<![0-9A-Za-z:])[0-9a-fA-F]{0,4}(?::[0-9a-fA-F]{0,4}){2,7}(?![0-9A-Za-z:]))"
    r"|(?P<zahl>\d[\d.,]*\d|\d)")


def _wert(raw, schreibweise):
    """'2,073,600' (en) oder '2.073.600' (de) -> Decimal. Einzelner Trenner
    mit genau drei Ziffern danach ist nur in der passenden Schreibweise ein
    Tausendertrenner."""
    if schreibweise == "en":
        text = raw.replace(",", "")
    else:
        text = raw.replace(".", "").replace(",", ".")
    try:
        return Decimal(text)
    except Exception:  # pragma: no cover - meldet der Test
        raise ValueError("unlesbare Zahl %r (%s)" % (raw, schreibweise))


def zahlen(text, schreibweise="de"):
    """Liste der Zahlen eines Textes in Reihenfolge, als Text-Schluessel:
    'ip:192.168.1.0', 'bits:1100...', 'ip6:2001:db8::', 'n:2073600'."""
    out = []
    for match in _TOKEN.finditer(text):
        kind = match.lastgroup
        raw = match.group(kind)
        if kind == "zahl":
            # Satzzeichen am Ende ("254." oder "5,93,") gehoeren nicht dazu
            raw = raw.rstrip(".,")
            if len(raw) > 1 and raw[0] == "0" and raw.isdigit():
                out.append("s:" + raw)      # Bitfolge oder Nibble: Ziffern zaehlen
            else:
                out.append("n:%s" % _wert(raw, schreibweise))
        elif kind == "ip6":
            if raw.count(":") < 2 or not re.search(r"[0-9a-fA-F]", raw):
                continue
            out.append("ip6:%s" % raw.lower())
        else:
            out.append("%s:%s" % ("ip" if kind == "ip4" else "bits", raw))
    return [_ganz(item) for item in out]


def _ganz(item):
    """n:2073600 statt n:2.0736E+6 (Decimal.normalize schreibt Exponenten)."""
    if item.startswith("n:"):
        value = Decimal(item[2:])
        if value == value.to_integral():
            return "n:%d" % value
        return "n:%s" % format(value, "f")
    return item


def schreibweise_alt(quelle):
    """Schreibweise der Ausgangsbasis v0.62.2: Anzeigen Subnetz/RAID/Bildschirm
    englisch, alles andere deutsch (Plan 0.62.3, Test 4)."""
    return "en" if quelle.split(":", 1)[0] in ("subnet", "raid", "screen") else "de"


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        return 2
    root, target = os.path.abspath(sys.argv[1]), sys.argv[2]
    sys.path.insert(0, root)
    import fisi_core as fc
    import fisi_lernen as fl
    if os.path.dirname(os.path.abspath(fc.__file__)) != root:
        print("fisi_core nicht aus %s geladen" % root)
        return 1
    texte = erzeuge(fc, fl)
    data = {"stand": os.path.basename(root), "texte": texte}
    with open(target, "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=0, sort_keys=True)
        handle.write("\n")
    count = sum(len(zahlen(t, schreibweise_alt(q))) for q, t in texte.items())
    print("%d Quellen, %d Zahlen, gespeichert in %s" % (len(texte), count, target))
    return 0


if __name__ == "__main__":
    sys.exit(main())
