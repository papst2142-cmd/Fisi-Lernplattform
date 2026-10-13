#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests ab 0.62.3 (Plan 0.62.3, Teil E): Rechenwege am Handy und Pruefung aller
Rechenwege und Rechner-Anzeigen.

  Test 1   Handy-Fassungen: hoechstens 28 Zeichen je Zeile
  Test 2   Handy-Fassungen: dieselben Zahlen wie am PC (Zusatzzahlen nur aus
           einer ausdruecklichen Liste: Oktett-Nummern, Dezimalwert je Oktett)
  Test 2b  Ergebnisse in derselben Reihenfolge wie am PC
  Test 3   dieselben Schritt-Ueberschriften
  Test 4   alle angezeigten Zahlen gleich der Ausgangsbasis v0.62.2
           (pruefung/rechenweg_basis_0622.json), ausser den freigegebenen
           Aenderungen Z1-Z12, Z14-Z27 - jede einzeln mit vorher/nachher;
           dazu deutsche Schreibweise der Anzeigen (Z4, Z7) und fps 30 (Z8)
  Test 5   Spalten gerade ("=", Punkte, Bitreihen)
  Test 6   Handy: Box ohne Umbruch, seitlich wischbar; USV-Hinweis ausserhalb
  Test 7   grosse Netze schnell, erste/letzte Host-Adresse wie bisher
  Test 9   PC-Trainer unveraendert bis auf freigegebenen Wortlaut; Handy-Form
           von Schritt 3 mit denselben Werten
  Z12      RAID 10 mit 4, 6, 8 Festplatten (2, 3, 4), ungerade: ungueltig
  PC       Ergebnis-Kaesten RAID und Bildschirm hoch genug (kein Scrollen)

Test 8 (Fingerabdruck der Spielwerte) ist das vorhandene Werkzeug aus dem
Bericht 0.54; Ergebnis steht im Bericht 0.62.3.

Start:  python test_rechenweg.py
"""

import json
import os
import re
import sys
import tempfile
import time
import unittest
from collections import Counter
from difflib import SequenceMatcher

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(1, os.path.join(HERE, "pruefung"))

import fisi_core as fc            # noqa: E402
import fisi_lernen as fl          # noqa: E402
import rechenweg_texte as rt      # noqa: E402

GRENZE = 28    # Freigabe 0.62.3 (F-P2): Anheben nur mit Freigabe

PAARE = [("SUBNET", fc.CALC_EXPLAIN_SUBNET, fc.CALC_EXPLAIN_SUBNET_HANDY),
         ("RAID", fc.CALC_EXPLAIN_RAID, fc.CALC_EXPLAIN_RAID_HANDY),
         ("SCREEN", fc.CALC_EXPLAIN_SCREEN, fc.CALC_EXPLAIN_SCREEN_HANDY),
         ("UPS", fc.CALC_EXPLAIN_UPS, fc.CALC_EXPLAIN_UPS_HANDY)]

# Test 2: Zahlen, die nur die Handy-Fassung hat (Bitreihen Oktett fuer Oktett)
ZUSATZ = {
    "SUBNET": Counter(
        # Schritt 1: "1. Oktett 11111111 = 255" ... (255/0 stehen auch am PC)
        ["n:1", "n:2", "n:3", "n:4"]
        # Schritt 2: Oktett-Nummer, Dezimalwert der Adresse und der Maske
        + ["n:1", "n:192", "n:255", "n:2", "n:168", "n:255", "n:3", "n:1", "n:255",
           "n:4", "n:50", "n:0"]),
    "RAID": Counter(), "SCREEN": Counter(), "UPS": Counter(),
}
# Test 2b: beim Subnetting die Ergebniswerte (die Bitreihen stehen am Handy
# anders); bei den anderen Rechenwegen muss die ganze Zahlenfolge gleich sein
ERGEBNISSE = {"SUBNET": {"ip:255.255.255.0", "ip:192.168.1.0", "ip:0.0.0.255",
                         "ip:192.168.1.255", "n:256", "n:254", "ip:192.168.1.1",
                         "ip:192.168.1.254"}}

# Test 4: freigegebene Aenderungen angezeigter Zahlen (Freigabe Plan 0.62.3,
# Abschnitt 4.2), je Quelle als Liste (Art, Stelle, vorher, nachher, Nummer).
# Stelle = Index in der Zahlenfolge der Ausgangsbasis.
FREIGEGEBEN = {
    "upsaufgabe:5": [("replace", 13, ["n:390.62"], ["n:390.63"], "Z1"),
                     ("replace", 18, ["n:390.62"], ["n:390.63"], "Z1")],
    "subnet:192.168.10.1/31": [("replace", 3, ["ip:192.168.10.1"], ["n:31", "n:3021"], "Z2")],
    "raid:RAID 5|4|1,5": [("replace", 2, ["n:2"], ["n:1.5"], "Z3")],
    "raid:RAID 5|3|0,5": [("replace", 2, ["n:0"], ["n:0.5"], "Z3")],
    "text:CALC_EXPLAIN_SCREEN": [("replace", 11, ["n:16.7"], ["n:16.8"], "Z5"),
                                 # ab 0.63.2 (B-N-07 5.13, FG-23): Binaerpraefix
                                 ("insert", 21, [], ["n:1024", "n:2", "n:10", "n:1",
                                                     "n:1000"], "Z24")],
    "upsaufgabe:4": [("insert", 9, [], ["n:1", "n:6"], "Z6"),
                     ("replace", 11, ["n:0.1667"], ["n:1", "n:6"], "Z6")],
    "raid:RAID 10|4|1000": [("insert", 8, [], ["n:2"], "Z12")],
    "raid:RAID 10|6|2000": [("insert", 8, [], ["n:3"], "Z12")],
    "raid:RAID 10|8|1000": [("insert", 8, [], ["n:4"], "Z12")],
    "text:CALC_EXPLAIN_RAID": [("insert", 13, [], ["n:2"], "Z15"),
                               ("insert", 45, [], ["n:2"], "Z12")],
    "text:CALC_EXPLAIN_SUBNET": [
        # ab 0.63.2 (B-N-07, FG-23): Z19 = 5.1 Beispiel /28 (Grenze im Oktett),
        # Z20 = 5.2 ODER mit Bitreihen, Z21 = 5.3 Ausnahmen /31 und /32
        ("insert", 25, [], ["ip:192.168.1.50", "n:28", "n:4", "n:50", "s:00110010",
                            "n:240", "n:11110000", "s:00110000", "n:48", "n:28",
                            "ip:192.168.1.48"], "Z19"),
        ("insert", 29, [], ["n:4", "n:0", "s:00000000", "n:11111111", "n:11111111",
                            "n:255"], "Z20"),
        ("insert", 51, [], ["n:31", "n:3021", "n:32"], "Z21"),
        ("insert", 54, [], ["n:2", "n:128"], "Z14")],
    # Ab 0.63.2 (Plan 0.63.2, FG-23), je Zahl nachgerechnet:
    # Z16 (A8): /32 zeigt "keine (/32, einzelne Adresse)" statt der Adresse
    "subnet:192.168.10.7/32": [("replace", 3, ["ip:192.168.10.7"], ["n:32"], "Z16")],
    # Z17 (B-K-N3): Bildrate 29,97 statt gerundet 30
    "screen:1920|1080|24|29,97": [("replace", 8, ["n:30"], ["n:29.97"], "Z17")],
    # Z18 (B-N-06): Teilungsweg vollstaendig statt "..." nach 12 Zeilen; die
    # Zahlen sind die fehlenden Zeilen "q : 2 = q//2 Rest q%2" (siehe
    # test_4_z18_nachgerechnet, rechnet sie aus der Basis selbst nach)
    "trainer:zahlen|3|2": [("insert", 52, [], ["n:8", "n:2", "n:4", "n:0", "n:4", "n:2", "n:2", "n:0", "n:2", "n:2", "n:1", "n:0", "n:1", "n:2", "n:0", "n:1"], "Z18")],
    "trainer:zahlen|3|6": [("insert", 53, [], ["n:2", "n:2", "n:1", "n:0", "n:1", "n:2", "n:0", "n:1"], "Z18")],
    "trainer:zahlen|3|10": [("insert", 52, [], ["n:15", "n:2", "n:7", "n:1", "n:7", "n:2", "n:3", "n:1", "n:3", "n:2", "n:1", "n:1", "n:1", "n:2", "n:0", "n:1"], "Z18")],
    "trainer:zahlen|3|11": [("insert", 52, [], ["n:7", "n:2", "n:3", "n:1", "n:3", "n:2", "n:1", "n:1", "n:1", "n:2", "n:0", "n:1"], "Z18")],
    "trainer:zahlen|3|13": [("insert", 53, [], ["n:9", "n:2", "n:4", "n:1", "n:4", "n:2", "n:2", "n:0", "n:2", "n:2", "n:1", "n:0", "n:1", "n:2", "n:0", "n:1"], "Z18")],
    "trainer:zahlen|3|19": [("insert", 52, [], ["n:13", "n:2", "n:6", "n:1", "n:6", "n:2", "n:3", "n:0", "n:3", "n:2", "n:1", "n:1", "n:1", "n:2", "n:0", "n:1"], "Z18")],
    "trainer:zahlen|3|20": [("insert", 53, [], ["n:3", "n:2", "n:1", "n:1", "n:1", "n:2", "n:0", "n:1"], "Z18")],
    "trainer:zahlen|3|21": [("insert", 52, [], ["n:14", "n:2", "n:7", "n:0", "n:7", "n:2", "n:3", "n:1", "n:3", "n:2", "n:1", "n:1", "n:1", "n:2", "n:0", "n:1"], "Z18")],
    "trainer:zahlen|3|25": [("insert", 53, [], ["n:7", "n:2", "n:3", "n:1", "n:3", "n:2", "n:1", "n:1", "n:1", "n:2", "n:0", "n:1"], "Z18")],
    "trainer:zahlen|3|30": [("insert", 52, [], ["n:11", "n:2", "n:5", "n:1", "n:5", "n:2", "n:2", "n:1", "n:2", "n:2", "n:1", "n:0", "n:1", "n:2", "n:0", "n:1"], "Z18")],
    "trainer:zahlen|3|32": [("insert", 53, [], ["n:6", "n:2", "n:3", "n:0", "n:3", "n:2", "n:1", "n:1", "n:1", "n:2", "n:0", "n:1"], "Z18")],
    "trainer:zahlen|3|36": [("insert", 53, [], ["n:13", "n:2", "n:6", "n:1", "n:6", "n:2", "n:3", "n:0", "n:3", "n:2", "n:1", "n:1", "n:1", "n:2", "n:0", "n:1"], "Z18")],
    # ab 0.63.2 (B-N-07, FG-23), nachgerechnet in test_4_bn07_nachgerechnet:
    # Z22 = 5.5 (80 % / 0,8 benannt, Laufzeitformel), Z23 = 5.7 (Beispielkopf),
    # Z25 = 4.9 (Stellenzahl wie die Anzeige: 666,67 VA, 23,0 / 18,4 min,
    # 44,4 % / 66,7 %). insert 39: 23 = "gerundet 23,0" (Z25), 80 und 4 (Z22)
    "text:CALC_EXPLAIN_UPS": [("insert", 1, [], ["n:0.9"], "Z23"),
                              ("insert", 6, [], ["n:12"], "Z23"),
                              ("insert", 7, [], ["n:1500", "n:900"], "Z23"),
                              ("insert", 10, [], ["n:666.67"], "Z25"),
                              ("insert", 34, [], ["n:60"], "Z22"),
                              ("insert", 39, [], ["n:23", "n:80", "n:4"], "Z22"),
                              ("insert", 42, [], ["n:18.4"], "Z25"),
                              ("replace", 45, ["n:667"], ["n:666.67"], "Z25"),
                              ("replace", 47, ["n:44"], ["n:44.4"], "Z25"),
                              ("replace", 50, ["n:67", "n:18.43"], ["n:66.7", "n:18.4"],
                               "Z25"),
                              ("insert", 53, [], ["n:80", "n:0.8", "n:3", "n:4"], "Z22")],
    # Z26 = 5.11 Trainer IPv4: "Die Oktette danach sind in der Netzadresse 0 und
    # in der Broadcast-Adresse 255." (Praefixgrenze im 1. bis 3. Oktett);
    # Z27 = 5.9 Trainer Zahlen: "Hex-Ziffern: E = 14, F = 15" (Hex gegeben).
    # Je Quelle nachgerechnet in test_4_z26_z27_nachgerechnet.
    'trainer:ipv4|2|3': [('insert', 26, [], ['n:0', 'n:255'], 'Z26')],
    'trainer:ipv4|2|4': [('insert', 26, [], ['n:0', 'n:255'], 'Z26')],
    'trainer:ipv4|2|5': [('insert', 26, [], ['n:0', 'n:255'], 'Z26')],
    'trainer:ipv4|2|8': [('insert', 26, [], ['n:0', 'n:255'], 'Z26')],
    'trainer:ipv4|2|13': [('insert', 26, [], ['n:0', 'n:255'], 'Z26')],
    'trainer:ipv4|2|15': [('insert', 26, [], ['n:0', 'n:255'], 'Z26')],
    'trainer:ipv4|2|18': [('insert', 26, [], ['n:0', 'n:255'], 'Z26')],
    'trainer:ipv4|2|20': [('insert', 26, [], ['n:0', 'n:255'], 'Z26')],
    'trainer:ipv4|2|27': [('insert', 26, [], ['n:0', 'n:255'], 'Z26')],
    'trainer:ipv4|2|30': [('insert', 26, [], ['n:0', 'n:255'], 'Z26')],
    'trainer:ipv4|2|31': [('insert', 26, [], ['n:0', 'n:255'], 'Z26')],
    'trainer:ipv4|2|32': [('insert', 26, [], ['n:0', 'n:255'], 'Z26')],
    'trainer:ipv4|2|33': [('insert', 26, [], ['n:0', 'n:255'], 'Z26')],
    'trainer:ipv4|2|34': [('insert', 26, [], ['n:0', 'n:255'], 'Z26')],
    'trainer:ipv4|2|35': [('insert', 26, [], ['n:0', 'n:255'], 'Z26')],
    'trainer:ipv4|2|39': [('insert', 26, [], ['n:0', 'n:255'], 'Z26')],
    'trainer:ipv4|3|0': [('insert', 26, [], ['n:0', 'n:255'], 'Z26')],
    'trainer:ipv4|3|4': [('insert', 26, [], ['n:0', 'n:255'], 'Z26')],
    'trainer:ipv4|3|6': [('insert', 26, [], ['n:0', 'n:255'], 'Z26')],
    'trainer:ipv4|3|7': [('insert', 26, [], ['n:0', 'n:255'], 'Z26')],
    'trainer:ipv4|3|8': [('insert', 26, [], ['n:0', 'n:255'], 'Z26')],
    'trainer:ipv4|3|9': [('insert', 26, [], ['n:0', 'n:255'], 'Z26')],
    'trainer:ipv4|3|12': [('insert', 26, [], ['n:0', 'n:255'], 'Z26')],
    'trainer:ipv4|3|13': [('insert', 26, [], ['n:0', 'n:255'], 'Z26')],
    'trainer:ipv4|3|14': [('insert', 26, [], ['n:0', 'n:255'], 'Z26')],
    'trainer:ipv4|3|18': [('insert', 26, [], ['n:0', 'n:255'], 'Z26')],
    'trainer:ipv4|3|19': [('insert', 26, [], ['n:0', 'n:255'], 'Z26')],
    'trainer:ipv4|3|20': [('insert', 26, [], ['n:0', 'n:255'], 'Z26')],
    'trainer:ipv4|3|21': [('insert', 26, [], ['n:0', 'n:255'], 'Z26')],
    'trainer:ipv4|3|23': [('insert', 26, [], ['n:0', 'n:255'], 'Z26')],
    'trainer:ipv4|3|25': [('insert', 26, [], ['n:0', 'n:255'], 'Z26')],
    'trainer:ipv4|3|26': [('insert', 26, [], ['n:0', 'n:255'], 'Z26')],
    'trainer:ipv4|3|28': [('insert', 26, [], ['n:0', 'n:255'], 'Z26')],
    'trainer:ipv4|3|29': [('insert', 26, [], ['n:0', 'n:255'], 'Z26')],
    'trainer:ipv4|3|33': [('insert', 26, [], ['n:0', 'n:255'], 'Z26')],
    'trainer:ipv4|3|35': [('insert', 26, [], ['n:0', 'n:255'], 'Z26')],
    'trainer:ipv4|3|37': [('insert', 26, [], ['n:0', 'n:255'], 'Z26')],
    'trainer:ipv4|3|38': [('insert', 26, [], ['n:0', 'n:255'], 'Z26')],
    'trainer:zahlen|1|3': [('insert', 9, [], ['n:13'], 'Z27')],
    'trainer:zahlen|1|14': [('insert', 9, [], ['n:11'], 'Z27')],
    'trainer:zahlen|1|19': [('insert', 9, [], ['n:12'], 'Z27')],
    'trainer:zahlen|1|21': [('insert', 9, [], ['n:14'], 'Z27')],
    'trainer:zahlen|1|24': [('insert', 9, [], ['n:10'], 'Z27')],
    'trainer:zahlen|1|27': [('insert', 9, [], ['n:14'], 'Z27')],
    'trainer:zahlen|1|28': [('insert', 7, [], ['n:10', 'n:11'], 'Z27')],
    'trainer:zahlen|1|32': [('insert', 7, [], ['n:13'], 'Z27')],
    'trainer:zahlen|1|36': [('insert', 9, [], ['n:13'], 'Z27')],
    'trainer:zahlen|2|0': [('insert', 11, [], ['n:14', 'n:15'], 'Z27')],
    'trainer:zahlen|2|5': [('insert', 11, [], ['n:10', 'n:11'], 'Z27')],
    'trainer:zahlen|2|6': [('insert', 11, [], ['n:13', 'n:15'], 'Z27')],
    'trainer:zahlen|2|11': [('insert', 12, [], ['n:12'], 'Z27')],
    'trainer:zahlen|2|14': [('insert', 9, [], ['n:14'], 'Z27')],
    'trainer:zahlen|2|15': [('insert', 12, [], ['n:13'], 'Z27')],
    'trainer:zahlen|2|18': [('insert', 11, [], ['n:11', 'n:12'], 'Z27')],
    'trainer:zahlen|2|20': [('insert', 11, [], ['n:10', 'n:15'], 'Z27')],
    'trainer:zahlen|2|28': [('insert', 11, [], ['n:12', 'n:13'], 'Z27')],
    'trainer:zahlen|2|29': [('insert', 9, [], ['n:11'], 'Z27')],
    'trainer:zahlen|2|32': [('insert', 13, [], ['n:12'], 'Z27')],
    'trainer:zahlen|2|34': [('insert', 12, [], ['n:13'], 'Z27')],
    'trainer:zahlen|2|36': [('insert', 11, [], ['n:12'], 'Z27')],
    'trainer:zahlen|2|37': [('insert', 12, [], ['n:13'], 'Z27')],
    'trainer:zahlen|3|14': [('insert', 16, [], ['n:12'], 'Z27')],
    'trainer:zahlen|3|18': [('insert', 16, [], ['n:15'], 'Z27')],
    'trainer:zahlen|3|22': [('insert', 15, [], ['n:11', 'n:15'], 'Z27')],
    'trainer:zahlen|3|23': [('insert', 15, [], ['n:15'], 'Z27')],
    'trainer:zahlen|3|24': [('insert', 14, [], ['n:12', 'n:15'], 'Z27')],
    'trainer:zahlen|3|26': [('insert', 15, [], ['n:14'], 'Z27')],
    'trainer:zahlen|3|31': [('insert', 15, [], ['n:15'], 'Z27')],
    'trainer:zahlen|3|37': [('insert', 15, [], ['n:11'], 'Z27')],
    'trainer:zahlen|3|38': [('insert', 14, [], ['n:11', 'n:15'], 'Z27')],
    'trainer:zahlen|3|39': [('insert', 15, [], ['n:11', 'n:12'], 'Z27')],
}


def _teilung_fortsetzen(text):
    """B-N-06 (ab 0.63.2), unabhaengig von fisi_lernen nachgerechnet: ersetzt
    "   ..." nach der letzten Zeile "x : 2 = q Rest r" durch die fehlenden
    Zeilen bis "1 : 2 = 0 Rest 1"."""
    lines = text.split("\n")
    if "   ..." not in lines:
        return text
    pos = lines.index("   ...")
    rest = int(re.fullmatch(r"   \d+ : 2 = (\d+) Rest [01]", lines[pos - 1]).group(1))
    fehlend = []
    while rest:
        fehlend.append("   %d : 2 = %d Rest %d" % (rest, rest // 2, rest % 2))
        rest //= 2
    return "\n".join(lines[:pos] + fehlend + lines[pos + 1:])


def _bn07_trainer(text):
    """B-N-07 (ab 0.63.2), unabhaengig von fisi_lernen aus dem alten Text
    abgeleitet: 5.11 Zeile zu den Folge-Oktetten nach dem Kurzweg (Grenze im
    1. bis 3. Oktett), 5.9 Werte der Hex-Buchstaben und Richtung "Hex -> Binaer"
    bei Hex-Vorgabe, 5.12 Hinweis, wenn es keine Folge von Nullbloecken gibt."""
    out = []
    lines = text.split("\n")
    ergebnis = next((line[10:] for line in lines if line.startswith("Ergebnis: ")), "")
    hex_gegeben = any(line.startswith("Hex -> Dezimal: ") for line in lines)
    for line in lines:
        if hex_gegeben and line.startswith("Binär -> Hex: in Vierergruppen (Nibbles) von "
                                           "rechts teilen: "):
            line = ("Hex -> Binär: jede Hex-Ziffer als Vierergruppe (Nibble) schreiben: "
                    + line.split("teilen: ", 1)[1])
        out.append(line)
        okt = re.match(r"   Kurzweg: Blockgröße im (\d)\. Oktett", line)
        if okt and int(okt.group(1)) < 4:
            out.append("   Die Oktette danach sind in der Netzadresse 0 und in der "
                       "Broadcast-Adresse 255.")
        if line.startswith("Hex -> Dezimal: "):
            buchstaben = sorted(set(re.findall(r"([A-F]) x 16\^", line)))
            if buchstaben:
                out.append("   Hex-Ziffern: " + ", ".join(
                    "%s = %d" % (b, "ABCDEF".index(b) + 10) for b in buchstaben))
        if line.startswith("2. Die längste Folge von Nullblöcken") and "::" not in ergebnis:
            out.append("   Hier gibt es keine solche Folge, dieser Schritt entfällt.")
    return "\n".join(out)


# Aenderungen nur der Schreibweise (Wert gleich, Test 4 vergleicht Werte):
# Z4 deutsche Zahlen in den Anzeigen, Z7 IPv6 gegliedert, Z9 KiB/MiB/GiB/MiB/s,
# Z10 "Abzug von 2 Adressen" (Wert 2 bleibt), Z11 "1.200 VA"/"1.000 W".
SCHREIBWEISE = {
    "Z4": ("screen:1920|1080|24|30", ["2.073.600", "6.220.800 Byte", "6.075,00 KiB",
                                       "49.766.400 Bit"]),
    "Z4 RAID": ("raid:RAID 5|4|1000", ["4.000,00 GB", "75,0 %", "4 x 1.000 GB"]),
    "Z4 Subnetz": ("subnet:10.20.30.40/8", ["16.777.214", "16.777.216"]),
    "Z7": ("subnet:2001:db8::1/64", ["18.446.744.073.709.551.616"]),
    "Z9": ("screen:1920|1080|24|30", ["177,98 MiB/s", "1.492,99 Mbit/s", "10,43 GiB/Minute",
                                       "5,93 MiB"]),
    "Z10": ("text:CALC_EXPLAIN_SUBNET", ["Abzug von 2 Adressen"]),
    "Z11": ("upsaufgabe:3", ["1.200 VA", "1.500 VA und 1.000 W"]),
    # ab 0.63.2 (B-N-07 4.9, FG-23): 666,67 VA und 44,4 % wie in der Anzeige
    "Z11 Rechenweg": ("text:CALC_EXPLAIN_UPS", ["USV 1.500 VA / 900 W",
                                                "666,67 / 1.500 = 44,4 %"]),
}


def _oktette(tokens):
    """Bitreihen in einzelne Oktette zerlegen (PC: eine Reihe, Handy: je Oktett)."""
    out = []
    for token in tokens:
        if token.startswith("bits:"):
            out += ["okt:" + part for part in token[5:].split(".")]
        elif re.fullmatch(r"[sn]:[01]{8}", token):
            out.append("okt:" + token[2:].zfill(8))
        else:
            out.append(token)
    return out


def _zahlen(text):
    return _oktette(rt.zahlen(text, "de"))


def _ueberschriften(text):
    """Nicht eingerueckte Zeilen, Absatz fuer Absatz zusammengesetzt."""
    heads, current = [], []
    for line in text.split("\n"):
        if line and not line.startswith(" "):
            current.append(line)
        elif current:
            heads.append(" ".join(current))
            current = []
    if current:
        heads.append(" ".join(current))
    return heads


class HandyFassungTest(unittest.TestCase):
    def test_1_zeilenlaenge(self):
        self.assertEqual(fc.CALC_EXPLAIN_HANDY_WIDTH, GRENZE)
        for name, _pc, handy in PAARE:
            for number, line in enumerate(handy.split("\n"), 1):
                self.assertLessEqual(len(line), GRENZE, "%s Zeile %d hat %d Zeichen: %r"
                                     % (name, number, len(line), line))

    def test_2_gleiche_zahlen(self):
        for name, pc, handy in PAARE:
            pc_z, handy_z = Counter(_zahlen(pc)), Counter(_zahlen(handy))
            self.assertEqual(pc_z - handy_z, Counter(), "%s: Zahlen fehlen am Handy" % name)
            self.assertEqual(handy_z - pc_z, ZUSATZ[name],
                             "%s: Zusatzzahlen am Handy nicht wie erlaubt" % name)

    def test_2b_reihenfolge_der_ergebnisse(self):
        for name, pc, handy in PAARE:
            keep = ERGEBNISSE.get(name)
            pc_z = [z for z in _zahlen(pc) if keep is None or z in keep]
            handy_z = [z for z in _zahlen(handy) if keep is None or z in keep]
            self.assertEqual(pc_z, handy_z, "%s: Reihenfolge der Ergebnisse" % name)

    def test_3_gleiche_schritte(self):
        for name, pc, handy in PAARE:
            pc_h, handy_h = _ueberschriften(pc), _ueberschriften(handy)
            self.assertGreaterEqual(len(pc_h), 4, name)
            self.assertEqual(pc_h, handy_h, "%s: Schritte" % name)

    def test_handy_waehlt_handy_fassung(self):
        with open(os.path.join(HERE, "mobile", "src", "main.py"), encoding="utf-8") as handle:
            source = handle.read()
        for name in ("SUBNET", "RAID", "SCREEN", "UPS"):
            self.assertIn("self._explain(CALC_EXPLAIN_%s_HANDY)" % name, source)
            self.assertNotIn("self._explain(CALC_EXPLAIN_%s)" % name, source)
        with open(os.path.join(HERE, "app_gui.py"), encoding="utf-8") as handle:
            pc = handle.read()
        self.assertNotIn("_HANDY", pc)


class ZahlenUnveraendertTest(unittest.TestCase):
    """Test 4: alle Zahlen gleich der Ausgangsbasis, ausser Z1-Z12, Z14-Z27."""

    @classmethod
    def setUpClass(cls):
        path = os.path.join(HERE, "pruefung", "rechenweg_basis_0622.json")
        with open(path, encoding="utf-8") as handle:
            cls.basis = json.load(handle)["texte"]
        cls.neu = rt.erzeuge(fc, fl)

    def test_4_alle_quellen(self):
        self.assertEqual(set(self.basis), set(self.neu))
        self.assertGreaterEqual(len(self.basis), 500)
        gefunden, zahlen = {}, 0
        for quelle in sorted(self.basis):
            alt = rt.zahlen(self.basis[quelle], rt.schreibweise_alt(quelle))
            neu = rt.zahlen(self.neu[quelle], "de")
            zahlen += len(alt)
            ops = [(art, i1, alt[i1:i2], neu[j1:j2])
                   for art, i1, i2, j1, j2 in SequenceMatcher(a=alt, b=neu, autojunk=False)
                   .get_opcodes() if art != "equal"]
            if ops:
                gefunden[quelle] = ops
        erwartet = {quelle: [eintrag[:4] for eintrag in liste]
                    for quelle, liste in FREIGEGEBEN.items()}
        self.assertEqual(gefunden, erwartet)
        self.assertGreater(zahlen, 10000)

    def test_4_jede_freigabe_einzeln(self):
        nummern = sorted({e[4] for liste in FREIGEGEBEN.values() for e in liste})
        self.assertEqual(nummern, ["Z1", "Z12", "Z14", "Z15", "Z16", "Z17", "Z18", "Z19",
                                   "Z2", "Z20", "Z21", "Z22", "Z23", "Z24", "Z25", "Z26",
                                   "Z27", "Z3", "Z5", "Z6"])

    def test_4_z18_nachgerechnet(self):
        # ab 0.63.2: jede Z18-Zahl aus der Basis selbst nachgerechnet
        quellen = sorted(q for q, liste in FREIGEGEBEN.items() if liste[0][4] == "Z18")
        self.assertEqual(len(quellen), 12)
        for quelle in quellen:
            alt = rt.zahlen(self.basis[quelle], rt.schreibweise_alt(quelle))
            neu = rt.zahlen(_teilung_fortsetzen(self.basis[quelle]), "de")
            ops = [(art, i1, alt[i1:i2], neu[j1:j2])
                   for art, i1, i2, j1, j2 in SequenceMatcher(a=alt, b=neu, autojunk=False)
                   .get_opcodes() if art != "equal"]
            self.assertEqual(ops, [e[:4] for e in FREIGEGEBEN[quelle]], quelle)

    def test_4_z26_z27_nachgerechnet(self):
        # ab 0.63.2 (B-N-07 5.11, 5.9): jede Z26-/Z27-Zahl aus der Basis selbst
        # abgeleitet (_bn07_trainer), und keine Quelle fehlt in der Liste
        erwartet = {}
        for quelle in sorted(self.basis):
            if not quelle.startswith("trainer:"):
                continue
            text = self.basis[quelle]
            for before, after, _nr in TrainerTest.ERSETZEN:
                text = text.replace(before, after)
            alt = rt.zahlen(self.basis[quelle], "de")
            neu = rt.zahlen(_bn07_trainer(text), "de")
            ops = [(art, i1, alt[i1:i2], neu[j1:j2])
                   for art, i1, i2, j1, j2 in SequenceMatcher(a=alt, b=neu, autojunk=False)
                   .get_opcodes() if art != "equal"]
            if ops:
                erwartet[quelle] = ops
        liste = {q: [e[:4] for e in l] for q, l in FREIGEGEBEN.items()
                 if l[0][4] in ("Z26", "Z27")}
        self.assertEqual(liste, erwartet)
        self.assertEqual(len(liste), 71)
        for quelle, ops in liste.items():
            nummer = FREIGEGEBEN[quelle][0][4]
            self.assertEqual(nummer, "Z26" if quelle.startswith("trainer:ipv4") else "Z27")
            if nummer == "Z26":
                self.assertEqual([op[3] for op in ops], [["n:0", "n:255"]])
            else:   # Werte der Buchstaben: A = 10 ... F = 15
                for wert in ops[0][3]:
                    self.assertIn(int(wert[2:]), range(10, 16))

    def test_4_bn07_nachgerechnet(self):
        # ab 0.63.2 (B-N-07): neue Zahlen der Rechenwege selbst nachgerechnet
        import ipaddress
        # Z19 (5.1): 192.168.1.50/28 -> Netz 192.168.1.48, Maske 240 im 4. Oktett
        netz = ipaddress.ip_network("192.168.1.50/28", strict=False)
        self.assertEqual((str(netz.network_address), netz.netmask.packed[3]),
                         ("192.168.1.48", 240))
        self.assertEqual((format(50, "08b"), format(240, "08b"), format(50 & 240, "08b")),
                         ("00110010", "11110000", "00110000"))
        # Z20 (5.2): 4. Oktett Netzadresse 0 ODER Wildcard 255 = 255
        self.assertEqual(0 | 255, 255)
        # Z21 (5.3): gleiche Aussagen wie die Anzeige (/31 RFC 3021, /32)
        self.assertIn("/31, RFC 3021", fc.subnet_report("192.168.10.1/31"))
        self.assertIn("/32, einzelne Adresse", fc.subnet_report("192.168.10.7/32"))
        # Z23 (5.7): Beispielkopf = Vorgaben des Rechners
        d = fc.UPS_FIELD_DEFAULTS
        self.assertEqual((d["pf"], d["block_ah"], d["nenn_va"], d["nenn_w"]),
                         ("0,9", "12", "1500", "900"))
        # Z25 (4.9): Werte wie die Anzeige des Rechners (eine Nachkommastelle)
        self.assertEqual(fc.de_number(600 / 0.9), "666,67")
        anzeige = fc.ups_calculate("empfehlung", dict(d), "W")["text"]
        for wert in ("44,4 %", "66,7 %", "23,0 min", "18,4 min"):
            self.assertIn(wert, anzeige)
        self.assertEqual(fc.de_number(600 / 0.9 / 1500 * 100, 1), "44,4")
        self.assertEqual(fc.de_number(288 * 0.8 / 600 * 60), "23,04")
        self.assertEqual(fc.de_number(288 * 0.8 / 600 * 60 * 0.8), "18,43")
        # Z22 (5.5): 80 % = Wirkungsgrad, Restkapazitaet und Auslastungsgrenze
        self.assertEqual((fc.UPS_ETA_DEFAULT, fc.ups_end_share(fc.UPS_AGING_DEFAULT),
                          fc.UPS_LOAD_LIMIT), (80, 80, 80))
        for schritt in ("SCHRITT 3: Verluste", "SCHRITT 4: Alterungszuschlag"):
            self.assertIn(schritt, fc.CALC_EXPLAIN_UPS)
        # Z24 (5.13): 1024 = 2^10, Dezimalpraefix 1000
        self.assertEqual(2 ** 10, 1024)

    def test_4_schreibweise(self):
        for nummer, (quelle, teile) in SCHREIBWEISE.items():
            for teil in teile:
                self.assertIn(teil, self.neu[quelle], "%s: %s" % (nummer, quelle))

    def test_4_anzeigen_deutsch(self):
        for quelle, text in self.neu.items():
            art = quelle.split(":", 1)[0]
            if art in ("raid", "screen"):
                self.assertIsNone(re.search(r"\d,\d{3}(?!\d)|\b\d+\.\d{1,2}\b", text),
                                  "%s englisch: %s" % (quelle, text))
            if art == "subnet":
                for line in text.split("\n"):
                    if "Hosts" in line or "Adressen gesamt" in line:
                        self.assertIsNone(re.search(r"\d{4}", line), line)

    def test_4_z2_31_und_z16_32(self):
        # ab 0.63.2 (A8, FG-23): /32 hat wie /31 keine Broadcast-Adresse
        self.assertIn("Broadcast-Adresse     : keine (/31, RFC 3021)",
                      fc.subnet_report("192.168.10.1/31"))
        self.assertIn("Broadcast-Adresse     : keine (/32, einzelne Adresse)",
                      fc.subnet_report("192.168.10.7/32"))
        self.assertIn("Broadcast-Adresse     : 192.168.10.3",
                      fc.subnet_report("192.168.10.1/30"))
        self.assertNotIn("keine", fc.subnet_report("192.168.10.1/30"))

    def test_4_z8_fps_vorgabe_30(self):
        for path, pattern in (("app_gui.py", r'self\.entry_fps = EntryBox\([^)]*value="30"\)'),
                              (os.path.join("mobile", "src", "main.py"),
                               r'self\.entry_fps = ui\.entry\("30"')):
            with open(os.path.join(HERE, path), encoding="utf-8") as handle:
                self.assertRegex(handle.read(), pattern, path)
        anzeige = fc.screen_report("1920", "1080", "24", "30")
        for wert in ("177,98", "1.492,99", "10,43"):
            self.assertIn(wert, anzeige)
            self.assertIn(wert, fc.CALC_EXPLAIN_SCREEN)


class SpaltenTest(unittest.TestCase):
    """Test 5: '=', Punkte und Bitreihen stehen untereinander."""

    def test_5_subnetting_pc(self):
        lines = fc.CALC_EXPLAIN_SUBNET.split("\n")
        bits = next(line for line in lines if line.startswith("   /24 = "))
        dec = lines[lines.index(bits) + 1]
        punkte = [i for i, c in enumerate(bits) if c == "."]
        self.assertEqual([i for i, c in enumerate(dec) if c == "."], punkte)
        self.assertEqual(dec.index("="), bits.index("="))
        rows = [line for line in lines if re.search(r"= [01]{8}\.", line) and line != bits]
        self.assertEqual(len(rows), 3)
        self.assertEqual(len({row.index("=") for row in rows}), 1)
        self.assertEqual(len({len(row) for row in rows}), 1)
        dash = next(line for line in lines if line.strip().startswith("-----"))
        self.assertEqual(len(dash), len(rows[0]))

    def test_5_subnetting_handy(self):
        lines = fc.CALC_EXPLAIN_SUBNET_HANDY.split("\n")
        rows = [line for line in lines if re.search(r"= [01]{8}$", line)]
        self.assertEqual(len(rows), 12)
        self.assertEqual(len({row.index("=") for row in rows}), 1)
        okt = [line for line in lines if re.match(r" \d\. Oktett [01]{8} = ", line)]
        self.assertEqual(len(okt), 4)
        self.assertEqual(len({row.index("=") for row in okt}), 1)

    def test_5_trainer(self):
        for level in (1, 2, 3):
            for seed in range(40):
                task = fl.trainer_task("ipv4", level, "e3-%d" % seed)
                rows = [s for s in task.steps if re.search(r"[01]{8}\.[01]{8}", s)]
                self.assertEqual(len(rows), 3)
                self.assertEqual(len({re.search(r"[01]{8}\.", s).start() for s in rows}), 1,
                                 rows)
                narrow = fl.trainer_task("ipv4", level, "e3-%d" % seed, schmal=True)
                rows = [s for s in narrow.steps if re.search(r" [01]{8}( = \d+)?$", s)]
                self.assertEqual(len(rows), 12)
                self.assertEqual(len({re.search(r"[01]{8}", s).start() for s in rows}), 1)

    def test_5_anzeigen(self):
        for text in (fc.screen_report("1920", "1080", "24", "30"),
                     fc.raid_report("RAID 10", "6", "2000"), fc.subnet_report("10.0.0.1/8")):
            spalten = {line.index(":") for line in text.split("\n") if ":" in line[:24]}
            self.assertEqual(spalten, {22}, text)


class BoxTest(unittest.TestCase):
    """Test 6: Box ohne Umbruch (A) am Handy, USV-Hinweis ausserhalb."""

    @classmethod
    def setUpClass(cls):
        sys.path.insert(1, os.path.join(HERE, "mobile", "src"))
        import flet as ft
        import main as handy
        import ui
        cls.ft, cls.handy, cls.ui = ft, handy, ui

    def _wischbar(self, box):
        return (isinstance(box.content, self.ft.Row) and box.content.scroll is not None
                and box.data is box.content.controls[0] and box.data.no_wrap)

    def test_6_read_box(self):
        box = self.ui.read_box("x", mono=True, scroll=True)
        self.assertTrue(self._wischbar(box))
        self.ui.set_box(box, "neu")
        self.assertEqual(box.data.value, "neu")
        plain = self.ui.read_box("x")
        self.assertIs(plain.content, plain.data)
        self.assertFalse(plain.data.no_wrap)

    def test_6_rechner(self):
        screen = self.handy.CalcScreen.__new__(self.handy.CalcScreen)
        screen.toast = lambda *args: None
        db = fc.DBManager(os.path.join(tempfile.mkdtemp(prefix="fisi rechenweg "), "t.db"))
        screen.app = type("App", (), {"db": db, "sync": None})()
        screen.build()
        for box in (screen.out_subnet, screen.out_raid, screen.out_screen, screen.out_ups):
            self.assertTrue(self._wischbar(box))
        erklaert = []

        def walk(control):
            if isinstance(control, self.ft.Container) and isinstance(
                    getattr(control, "data", None), self.ft.Text):
                erklaert.append(control)
            for name in ("content", "controls"):
                child = getattr(control, name, None)
                for item in child if isinstance(child, list) else [child]:
                    if item is not None and hasattr(item, "__dict__"):
                        walk(item)
        walk(screen.calc_box)
        texte = {box.data.value: box for box in erklaert}
        for name, _pc, handy in PAARE:
            self.assertIn(handy, texte, name)
            self.assertTrue(self._wischbar(texte[handy]), name)
        # USV: Tabelle wischt, Hinweis bricht als normaler Text um
        screen.calc_ups("empfehlung")
        self.assertIn("USV passend", screen.out_ups.data.value)
        self.assertNotIn(fc.UPS_SIMPLE_TEXT, screen.out_ups.data.value)
        self.assertEqual(screen.out_ups_hint.value, fc.UPS_SIMPLE_TEXT)
        self.assertNotIsInstance(screen.out_ups_hint, self.ft.Container)
        # Rechner-Anzeigen ueber set_box
        screen.calc_raid()
        self.assertIn("Nutzkapazität", screen.out_raid.data.value)


class GrosseNetzeTest(unittest.TestCase):
    """Test 7: /8 schnell, /0 laeuft durch, erste/letzte Host-Adresse wie bisher."""

    def test_7_zeit(self):
        start = time.perf_counter()
        fc.subnet_report("10.0.0.1/8")
        self.assertLess(time.perf_counter() - start, 0.5)
        start = time.perf_counter()
        text = fc.subnet_report("0.0.0.0/0")
        self.assertLess(time.perf_counter() - start, 0.5)
        self.assertIn("Letzte Host-Adresse   : 255.255.255.254", text)

    def test_7_wie_der_alte_weg(self):
        import ipaddress
        for prefix in range(0, 33):
            network = ipaddress.ip_network("172.20.200.17/%d" % prefix, strict=False)
            values = fc.ipv4_values(network)
            if prefix >= 12:
                hosts = list(network.hosts())          # alter Weg (bis 0.62.2)
                first = hosts[0] if hosts else network.network_address
                last = hosts[-1] if hosts else network.broadcast_address
            else:
                # alter Weg ohne Liste nachgebaut: hosts() = alle ausser Netz/Broadcast
                first, last = network[1], network[-2]
            self.assertEqual((values["erste"], values["letzte"]), (first, last), prefix)


class TrainerTest(unittest.TestCase):
    """Test 9: PC-Trainer unveraendert bis auf den freigegebenen Wortlaut."""

    ERSETZEN = [   # (vorher, nachher, Befund)
        ("Feld: Broadcast\n", "Feld: Broadcast-Adresse\n", "1.2"),
        ("Feld: Erster Host\n", "Feld: Erste Host-Adresse\n", "1.3"),
        ("Feld: Letzter Host\n", "Feld: Letzte Host-Adresse\n", "1.3"),
        ("3. Adresse binär:  ", "3. Adresse binär:   ", "1.23"),
        ("   Maske binär:    ", "   Maske binär:     ", "1.23"),
        ("4. Broadcast: alle", "4. Broadcast-Adresse: alle", "1.2"),
        ("bis Broadcast - 1)", "bis Broadcast-Adresse - 1)", "1.2"),
        (", Broadcast ", ", Broadcast-Adresse ", "1.2"),
        ("·16^", " x 16^", "1.20"),
        # ab 0.63.2 (B-N-07, FG-10/FG-23): Wortlaut 3.16 und 1.19
        (" die Netzdaten.\n", " die Netzdaten (die Adresse kann auch selbst die Netz- oder "
         "Broadcast-Adresse sein).\n", "3.16"),
        ("2. Den längsten Block aufeinanderfolgender Nullblöcke (mindestens zwei) durch "
         "'::' ersetzen, bei Gleichstand den ersten.",
         "2. Die längste Folge von Nullblöcken (mindestens zwei) durch '::' ersetzen, "
         "bei Gleichstand die erste.", "1.19"),
    ]

    @classmethod
    def setUpClass(cls):
        path = os.path.join(HERE, "pruefung", "rechenweg_basis_0622.json")
        with open(path, encoding="utf-8") as handle:
            cls.basis = json.load(handle)["texte"]

    def test_9_pc_text(self):
        count = 0
        for kind in rt.ALTE_ARTEN:
            for level, _label in fl.TRAINER_LEVELS:
                for seed in range(rt.TRAINER_SEEDS):
                    alt = self.basis["trainer:%s|%d|%d" % (kind, level, seed)]
                    for before, after, _nr in self.ERSETZEN:
                        alt = alt.replace(before, after)
                    if kind == "zahlen":        # ab 0.63.2 (B-N-06, FG-23)
                        alt = _teilung_fortsetzen(alt)
                    alt = _bn07_trainer(alt)    # ab 0.63.2 (B-N-07 5.9, 5.11, 5.12)
                    neu = rt.trainer_text(fl.trainer_task(kind, level, "e3-%d" % seed))
                    self.assertEqual(neu, alt, (kind, level, seed))
                    count += 1
        self.assertEqual(count, 480)

    def test_9_handy_form(self):
        for level in (1, 2, 3):
            for seed in range(40):
                pc = fl.trainer_task("ipv4", level, "e3-%d" % seed)
                handy = fl.trainer_task("ipv4", level, "e3-%d" % seed, schmal=True)
                self.assertEqual((handy.text, handy.fields, handy.solution),
                                 (pc.text, pc.fields, pc.solution))
                start = pc.steps.index(next(s for s in pc.steps if s.startswith("3. ")))
                block = handy.steps[start:start + 18]
                self.assertEqual(handy.steps[:start] + handy.steps[start + 18:],
                                 pc.steps[:start] + pc.steps[start + 3:])
                self.assertTrue(all(len(line) <= GRENZE for line in block), block)
                pc_z = Counter(_zahlen("\n".join(pc.steps[start:start + 3])))
                handy_z = Counter(_zahlen("\n".join(block)))
                self.assertEqual(pc_z - handy_z, Counter())
                netz = [int(o) for o in pc.solution["netz"].split(".")]
                self.assertEqual(handy_z - pc_z, Counter(["n:%d" % n for n in (1, 2, 3, 4)]
                                                         + ["n:%d" % n for n in netz]))

    def test_9_handy_nutzt_schalter(self):
        with open(os.path.join(HERE, "mobile", "src", "main.py"), encoding="utf-8") as handle:
            self.assertIn("random.randrange(1 << 30), schmal=True)", handle.read())
        with open(os.path.join(HERE, "app_gui.py"), encoding="utf-8") as handle:
            self.assertNotRegex(handle.read(), r"trainer_(round|task)\([^)]*schmal")


class PcKaestenTest(unittest.TestCase):
    """Ab 0.62.3: Die Ergebnis-Kaesten am PC zeigen alle Zeilen ohne Scrollen
    (Tk-Textfeld: sichtbar sind height - 1 Zeilen, an den Fotos gemessen).
    RAID 10 hat seit Z12 9 Zeilen, der Bildschirm mit Bildrate 30 (Z8) 12."""

    def _hoehe(self, name):
        with open(os.path.join(HERE, "app_gui.py"), encoding="utf-8") as handle:
            source = handle.read()
        return int(re.search(r"self\.txt_%s = make_text\([^)]*height=(\d+)" % name,
                             source).group(1))

    def test_raid(self):
        zeilen = max(fc.raid_report(*eingabe).count("\n") + 1 for eingabe in rt.RAID_INPUTS)
        self.assertEqual(zeilen, 9)
        self.assertGreaterEqual(self._hoehe("raid") - 1, zeilen)

    def test_bildschirm(self):
        zeilen = max(fc.screen_report(*eingabe).count("\n") + 1
                     for eingabe in rt.SCREEN_INPUTS)
        self.assertEqual(zeilen, 12)
        self.assertGreaterEqual(self._hoehe("screen") - 1, zeilen)


class Raid10Test(unittest.TestCase):
    """Z12 (Auflage): 4, 6, 8 Festplatten -> bis zu 2, 3, 4; ungerade -> ungueltig."""

    def test_z12_gerade(self):
        for disks, upto in ((4, 2), (6, 3), (8, 4)):
            text = fc.raid_report("RAID 10", str(disks), "1000")
            joined = " ".join(part.strip() for part in text.split("\n"))
            self.assertIn("Ausfalltoleranz : 1 Festplatte sicher (bis zu %d, wenn je "
                          "Spiegelpaar nur eine ausfällt)" % upto,
                          re.sub(r" +:", " :", joined))

    def test_z12_ungerade(self):
        for disks in (3, 5, 7, 9):
            text = fc.raid_report("RAID 10", str(disks), "1000")
            self.assertTrue(text.startswith("Ungültige Konfiguration für RAID 10."), text)
            self.assertNotIn("bis zu", text)
            self.assertIsNone(fc.raid_values("RAID 10", disks, 1000))

    def test_z12_andere_level_ohne_zusatz(self):
        for level in ("RAID 0", "RAID 1", "RAID 5", "RAID 6"):
            self.assertNotIn("bis zu", fc.raid_report(level, "6", "1000"))


class RundungGrenzwerteTest(unittest.TestCase):
    """Nachforderung N1: Die kaufmaennische Rundung (Decimal) darf bei
    Eingaben wie "inf", "1e27" oder "1e300" nicht abstuerzen. Unendlich und
    nan zeigen wie bis 0.62.2 "inf" und "nan". Ab 0.62.4 lehnen die Rechner
    diese Eingaben mit einer Meldung ab (gemeinsame Leseregel)."""

    def test_de_number_grenzwerte(self):
        self.assertEqual(fc.de_number(float("inf")), "inf")
        self.assertEqual(fc.de_number(float("nan"), 1), "nan")
        self.assertEqual(fc.de_number(1e27, 0), "1.000.000.000.000.000.000.000.000.000")
        self.assertTrue(fc.de_number(1e300).endswith(",00"))
        self.assertEqual(fc.de_number(390.625), "390,63")

    def test_rechner_stuerzen_nicht_ab(self):
        # Ab 0.62.4 (Plan 0.62.4 Abschnitt 3.5, bewusst umgestellt): Die
        # gemeinsame Leseregel lehnt inf, nan und die e-Schreibweise ab. Statt
        # eines Ergebnisses kommt eine Meldung (InputError), kein Absturz.
        for size in ("inf", "1e27", "nan"):
            with self.assertRaises(fc.InputError):
                fc.raid_report("RAID 0", "2", size)
        for fps in ("inf", "1e300"):
            with self.assertRaises(fc.InputError):
                fc.screen_report("1920", "1080", "24", fps)


if __name__ == "__main__":
    unittest.main(verbosity=2)
