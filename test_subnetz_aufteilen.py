#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests ab 0.63 (Plan 0.63, T1 Rechenkern): Netz in N gleich grosse Subnetze
aufteilen (IPv4 und IPv6) und Netz nach Hostbedarf (VLSM, IPv4).

Nachgerechnet wird unabhaengig vom Programmcode: eigene Ganzzahl-Rechnung in
dieser Datei (eigener Leser, eigene Schreibweise, eigene Vergabe). Das Modul
ipaddress dient nur als zweite Quelle fuer WERTE (Adressen als Zahl, Groessen,
Ausrichtung), nie fuer Schreibweisen: ipaddress schreibt ::ffff-Adressen je
nach Python-Patchstand anders (Plan 0.63 M-3, E-63-6).

  T-K-1   Aufteilen gegen eigene Rechnung und ipaddress, 3.000 IPv4 + 3.000
          IPv6 Zufallsfaelle (Startwert 63)
  T-K-2   Randfaelle aus Plan 0.63 Tabelle 6.1 einzeln mit erwarteter Zahl
  T-K-3   Fehlertexte deutsch und woertlich
  T-K-4   Host-Adresse wird Netz (mit Hinweis), Schreibweisen als feste Texte
  T-K-5   Hostbedarf: 5.000 Zufallsfaelle gegen ein anderes Verfahren
          (Freiliste), keine Ueberlappung, im Netz, ausgerichtet, groesstes
          zuerst, h minimal, Fehlbetrag und noetiger Praefix
  T-K-6   Laufzeit ohne Aufzaehlen (/0 IPv6 in 2^64, /8 IPv4 in 2^24) und
          keine Listen/hosts() im neuen Code
  T-K-7   Seitenrechnung
  T-K-8   Nibble-Kennwert genau dann, wenn der neue Praefix nicht durch 4
          teilbar ist (nur IPv6)
  T-K-9   /31 und /32 mit Hinweis
  T-K-10  Leseregel der Anzahl ("1.000" = 1000, "1,5" abgelehnt), genau auch
          ueber 2^53
  T-K-12  IPv4 /0 und IPv6 /0 getrennt (Versionsklasse)
  T-UI-3  Beschriftungen als Konstanten (eine Quelle fuer PC und Handy)
  T-K-13  Eingabeform "Nach Hostbedarf" (Plan 2.3.1, Fassung 4): die 43
          Faelle aus belege/b12 mit Liste oder Meldung woertlich, dazu
          M-3 (Komma, Semikolon, Schraegstrich), M-8, M-12, M-13a/b, Strich
          am Namensende, typografisches Minus, Tabulator (N-1 bis N-4)
  T-RW-3  (Fassung 4) Beispiele A bis J aus Anhang A und A2 woertlich,
          PC und Handy (20 Texte)
  T-RW-4  (Fassung 4) Grenz-Hextett und Schrittweite gegen eigene Rechnung,
          Lage der Subnetz-Bits und Uebertrag, /64-Hinweis (N-5a, N-5e)
  Fassung-4-Wortlaute: Erster/Letzter Host, Einzahl, Fehlbetrag (M-9),
          Hoechstzahl (A-M-5), Doppelpunkt, "Groesse" (N-4c/e, N-5b-g)
  T-TR-1  (0.63.1) neue Trainer-Arten "Netz aufteilen" und "Nach
          Hostbedarf": 3 Stufen x 200 Startwerte je Art gegen eigene
          Rechnung, immer loesbar, Rest 0 in mehr als 20 %, jede Teilantwort
          einzeln, Rechenweg PC (75) und Handy (28, steps_schmal)
  T-TR-3  (0.63.1) rt.ALTE_ARTEN = Anfang von TRAINER_KINDS, dazu G-63-1
          (trainer_task unveraendert) und F-63-18 = S1

T-K-11 (Mutation macht T-K-5 rot) laeuft als Gegenprobe ausserhalb des
Arbeitsbaums (Beleg im Bericht).

Der Code-Ordner ist waehlbar (fuer die Rot-Probe gegen einen alten Stand):

    SUBNETZ_CODE=<ordner mit dem Code> python test_subnetz_aufteilen.py

Start:  python test_subnetz_aufteilen.py
"""

import inspect
import ipaddress
import itertools
import os
import random
import re
import sys
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
CODE = os.path.abspath(os.environ.get("SUBNETZ_CODE") or HERE)
sys.path.insert(0, CODE)

import fisi_core as fc            # noqa: E402

GRENZE = 28    # Handy-Zeilen (Freigabe 0.62.3, F-P2)
PC_BREITE = 75    # PC-Zeilen (Plan 0.63 Abschnitt 0)
NETZKLASSE = {4: ipaddress.IPv4Network, 6: ipaddress.IPv6Network}


# ---------------------------------------------------------------------------
#  Eigene Rechnung (unabhaengig vom Programmcode, ohne ipaddress)
# ---------------------------------------------------------------------------

def eigen_v4(text):
    teile = text.split(".")
    assert len(teile) == 4
    wert = 0
    for teil in teile:
        assert teil.isdigit() and int(teil) <= 255
        wert = wert * 256 + int(teil)
    return wert


def eigen_v6(text):
    text = text.lower()
    if "." in text.rsplit(":", 1)[-1]:                    # ::ffff:1.2.3.4
        kopf, v4 = text.rsplit(":", 1)
        zahl = eigen_v4(v4)
        text = kopf + ":%x:%x" % (zahl >> 16, zahl & 0xFFFF)
    if "::" in text:
        links, rechts = text.split("::")
        lg = links.split(":") if links else []
        rg = rechts.split(":") if rechts else []
        gruppen = lg + ["0"] * (8 - len(lg) - len(rg)) + rg
    else:
        gruppen = text.split(":")
    assert len(gruppen) == 8
    wert = 0
    for gruppe in gruppen:
        wert = wert * 65536 + int(gruppe, 16)
    return wert


def eigen_v4_text(wert):
    return "%d.%d.%d.%d" % (wert >> 24, (wert >> 16) & 255, (wert >> 8) & 255, wert & 255)


def eigen_v6_text(wert):
    """RFC 5952 nach eigener Lesart: Nullfolgen suchen, die laengste (ab 2)
    wird '::', bei Gleichstand die erste."""
    gruppen = ["%x" % ((wert >> (112 - 16 * i)) & 0xFFFF) for i in range(8)]
    folgen = []
    i = 0
    while i < 8:
        if gruppen[i] == "0":
            j = i
            while j < 8 and gruppen[j] == "0":
                j += 1
            folgen.append((j - i, -i))
            i = j
        else:
            i += 1
    if not folgen or max(folgen)[0] < 2:
        return ":".join(gruppen)
    laenge, minus_start = max(folgen)
    start = -minus_start
    return ":".join(gruppen[:start]) + "::" + ":".join(gruppen[start + laenge:])


def eigen_text(version, wert):
    return eigen_v4_text(wert) if version == 4 else eigen_v6_text(wert)


def eigen_bits(anzahl):
    k = 0
    while 2 ** k < anzahl:
        k += 1
    return k


def eigen_hostbits(bedarf):
    h = 2
    while 2 ** h - 2 < bedarf:
        h += 1
    return h


def eigen_aufteilen(breite, netz, praefix, anzahl):
    k = eigen_bits(anzahl)
    if praefix + k > breite:
        return None
    groesse = 2 ** (breite - praefix - k)
    return {"k": k, "neu": praefix + k, "groesse": groesse, "anzahl": 2 ** k,
            "netz": lambda i: netz + i * groesse}


def eigen_vergabe(netz, praefix, bedarfe):
    """Groesster Bedarf zuerst (bei Gleichstand Eingabe), nacheinander."""
    groessen = [2 ** eigen_hostbits(b) for b in bedarfe]
    platz = 2 ** (32 - praefix)
    summe = sum(groessen)
    if summe > platz:
        noetig = 32
        while 2 ** (32 - noetig) < summe:
            noetig -= 1
        return ("passt nicht", summe - platz, noetig)
    reihenfolge = sorted(range(len(bedarfe)), key=lambda i: (-bedarfe[i], i))
    zeiger, aus = netz, {}
    for i in reihenfolge:
        aus[i] = (zeiger, 32 - eigen_hostbits(bedarfe[i]))
        zeiger += groessen[i]
    return aus


def freiliste(netz, bedarfe):
    """Zweites Verfahren mit ipaddress: je Bedarf (groesster zuerst) den
    kleinsten freien Block, bei Gleichstand die niedrigste Adresse, so lange
    halbieren, bis er passt."""
    frei = [netz]
    reihenfolge = sorted(range(len(bedarfe)), key=lambda i: (-bedarfe[i], i))
    aus = {}
    for i in reihenfolge:
        ziel = 30
        while ziel > 0 and 2 ** (32 - ziel) - 2 < bedarfe[i]:
            ziel -= 1
        kandidaten = [b for b in frei if b.prefixlen <= ziel]
        if not kandidaten or 2 ** (32 - ziel) - 2 < bedarfe[i]:
            return None
        block = min(kandidaten, key=lambda b: (-b.prefixlen, int(b.network_address)))
        frei.remove(block)
        while block.prefixlen < ziel:
            unten, oben = block.subnets(prefixlen_diff=1)
            frei.append(oben)
            block = unten
        aus[i] = (int(block.network_address), block.prefixlen)
    return aus


def meldung(aufruf):
    try:
        aufruf()
    except fc.InputError as fehler:
        return str(fehler)
    return None


# ---------------------------------------------------------------------------
#  T-K-1 Aufteilen gegen eigene Rechnung und ipaddress
# ---------------------------------------------------------------------------

class AufteilenZufallTest(unittest.TestCase):
    """T-K-1: 3.000 IPv4- und 3.000 IPv6-Zufallsfaelle."""

    def pruefe_fall(self, version, netz, praefix, anzahl, rng):
        breite = 32 if version == 4 else 128
        text = "%s/%d" % (eigen_text(version, netz), praefix)
        eigen = eigen_aufteilen(breite, netz, praefix, anzahl)
        if eigen is None:
            self.assertIsNotNone(meldung(lambda: fc.split_network(text, anzahl)), text)
            return
        ergebnis = fc.split_network(text, anzahl, version)
        for schluessel in ("k", "neu", "groesse", "anzahl"):
            self.assertEqual(ergebnis[schluessel], eigen[schluessel], (text, anzahl, schluessel))
        self.assertEqual(ergebnis["gewuenscht"], anzahl)
        self.assertEqual(ergebnis["netz"], netz)
        basis = NETZKLASSE[version]((netz, praefix))
        letzte = eigen["anzahl"] - 1
        stellen = {0, 1, eigen["anzahl"] // 2, letzte, rng.randrange(eigen["anzahl"])}
        for i in sorted(s for s in stellen if s <= letzte):
            eintrag = fc.split_entry(ergebnis, i)
            self.assertEqual(eintrag["netz"], eigen["netz"](i), (text, anzahl, i))
            self.assertEqual(eintrag["ende"], eigen["netz"](i) + eigen["groesse"] - 1)
            self.assertEqual(eintrag["status"], "verwendet" if i < anzahl else "frei, Reserve")
            # zweite Quelle: ipaddress (Werte)
            if eigen["anzahl"] <= 4096:
                ref = next(itertools.islice(basis.subnets(new_prefix=eigen["neu"]), i, None))
            else:
                ref = NETZKLASSE[version]((eintrag["netz"], eigen["neu"]))   # strict
                self.assertTrue(ref.subnet_of(basis))
                self.assertEqual(ref.supernet(new_prefix=praefix), basis)
            self.assertEqual(int(ref.network_address), eintrag["netz"])
            self.assertEqual(int(ref.broadcast_address), eintrag["ende"])
            self.assertEqual(ref.num_addresses, ergebnis["groesse"])
            if version == 4 and eigen["neu"] <= 30:
                self.assertEqual(eintrag["erste"], int(ref.network_address) + 1)
                self.assertEqual(eintrag["letzte"], int(ref.broadcast_address) - 1)
                self.assertEqual(eintrag["broadcast"], int(ref.broadcast_address))
                self.assertEqual(ergebnis["hosts"], ref.num_addresses - 2)
                self.assertEqual(ergebnis["maske"], int(ref.netmask))
        # letztes Subnetz endet am Netzende
        self.assertEqual(fc.split_entry(ergebnis, letzte)["ende"],
                         int(basis.broadcast_address))
        with self.assertRaises(IndexError):
            fc.split_entry(ergebnis, eigen["anzahl"])

    def test_ipv4_zufall(self):
        rng = random.Random(63)
        for _ in range(3000):
            praefix = rng.randint(0, 32)
            netz = rng.getrandbits(32) >> (32 - praefix) << (32 - praefix) if praefix else 0
            anzahl = rng.randint(1, min(4096, 2 ** (32 - praefix) * 2))
            self.pruefe_fall(4, netz, praefix, anzahl, rng)

    def test_ipv6_zufall(self):
        rng = random.Random(64)
        for _ in range(3000):
            praefix = rng.randint(0, 128)
            netz = rng.getrandbits(128) >> (128 - praefix) << (128 - praefix) if praefix else 0
            anzahl = rng.choice([1, 2, 3, 6, 12, 16, 17, 255, 256, 1000, 65536, 2 ** 20 + 1,
                                 rng.randint(1, 2 ** 40)])
            self.pruefe_fall(6, netz, praefix, anzahl, rng)


# ---------------------------------------------------------------------------
#  T-K-2 Randfaelle (Plan 0.63 Tabelle 6.1)
# ---------------------------------------------------------------------------

# (Netz, N, k, neuer Praefix, Anzahl Subnetze, Netz des letzten Subnetzes)
RANDFAELLE = [
    ("192.168.10.0/24", 1, 0, 24, 1, "192.168.10.0/24"),
    ("192.168.10.0/24", 2, 1, 25, 2, "192.168.10.128/25"),
    ("192.168.10.0/24", 4, 2, 26, 4, "192.168.10.192/26"),
    ("192.168.10.0/24", 5, 3, 27, 8, "192.168.10.224/27"),
    ("192.168.10.0/24", 64, 6, 30, 64, "192.168.10.252/30"),
    ("192.168.10.0/24", 65, 7, 31, 128, "192.168.10.254/31"),
    ("192.168.10.0/24", 128, 7, 31, 128, "192.168.10.254/31"),
    ("192.168.10.0/24", 256, 8, 32, 256, "192.168.10.255/32"),
    ("192.168.10.0/30", 2, 1, 31, 2, "192.168.10.2/31"),
    ("192.168.10.0/30", 4, 2, 32, 4, "192.168.10.3/32"),
    ("192.168.10.0/31", 2, 1, 32, 2, "192.168.10.1/32"),
    ("192.168.10.7/32", 1, 0, 32, 1, "192.168.10.7/32"),
    ("0.0.0.0/0", 1, 0, 0, 1, "0.0.0.0/0"),
    ("0.0.0.0/0", 256, 8, 8, 256, "255.0.0.0/8"),
    ("10.0.0.0/8", 300, 9, 17, 512, "10.255.128.0/17"),
    ("10.20.0.0/16", 4, 2, 18, 4, "10.20.192.0/18"),
    ("10.0.0.0/16", 8, 3, 19, 8, "10.0.224.0/19"),
    ("::/0", 1, 0, 0, 1, "::/0"),
    ("::/0", 2, 1, 1, 2, "8000::/1"),
    ("::/0", 65536, 16, 16, 65536, "ffff::/16"),
    ("2001:db8::/32", 65536, 16, 48, 65536, "2001:db8:ffff::/48"),
    ("2001:db8:abcd::/48", 6, 3, 51, 8, "2001:db8:abcd:e000::/51"),
    ("2001:db8:abcd::/48", 12, 4, 52, 16, "2001:db8:abcd:f000::/52"),
    ("2001:db8:abcd::/48", 65536, 16, 64, 65536, "2001:db8:abcd:ffff::/64"),
    ("2001:db8:abcd::/48", 65537, 17, 65, 131072, "2001:db8:abcd:ffff:8000::/65"),
    ("2001:db8::/127", 2, 1, 128, 2, "2001:db8::1/128"),
    ("2001:db8::1/128", 1, 0, 128, 1, "2001:db8::1/128"),
    ("fe80::/10", 1000, 10, 20, 1024, "febf:f000::/20"),
]

ZU_VIELE = [     # Fassung 4 (Z-10 Fund 10, N-4e): mit Hoechstzahl dahinter
    ("192.168.10.0/24", 257, "Zu viele Subnetze: /24 + 9 Bit = /33, mehr als /32 geht nicht. "
                             "Höchstens 256 Subnetze."),
    ("192.168.10.0/24", 512, "Zu viele Subnetze: /24 + 9 Bit = /33, mehr als /32 geht nicht. "
                             "Höchstens 256 Subnetze."),
    ("192.168.10.0/30", 5, "Zu viele Subnetze: /30 + 3 Bit = /33, mehr als /32 geht nicht. "
                           "Höchstens 4 Subnetze."),
    ("192.168.10.0/31", 3, "Zu viele Subnetze: /31 + 2 Bit = /33, mehr als /32 geht nicht. "
                           "Höchstens 2 Subnetze."),
    ("192.168.10.7/32", 2, "Zu viele Subnetze: /32 + 1 Bit = /33, mehr als /32 geht nicht. "
                           "Höchstens 1 Subnetz."),
    ("10.0.0.0/8", 2 ** 24 + 1, "Zu viele Subnetze: /8 + 25 Bit = /33, mehr als /32 geht "
                                "nicht. Höchstens 16.777.216 Subnetze."),
    ("2001:db8::/127", 3, "Zu viele Subnetze: /127 + 2 Bit = /129, mehr als /128 geht nicht. "
                          "Höchstens 2 Subnetze."),
    ("2001:db8::1/128", 2, "Zu viele Subnetze: /128 + 1 Bit = /129, mehr als /128 geht nicht. "
                           "Höchstens 1 Subnetz."),
    ("2001:db8::/96", 2 ** 32 + 1, "Zu viele Subnetze: /96 + 33 Bit = /129, mehr als /128 "
                                   "geht nicht. Höchstens 4.294.967.296 Subnetze."),
    ("2001:db8::/95", 2 ** 33 + 1, "Zu viele Subnetze: /95 + 34 Bit = /129, mehr als /128 "
                                   "geht nicht. Höchstens 2^33 Subnetze."),
    ("::/0", 2 ** 128 + 1, "Zu viele Subnetze: /0 + 129 Bit = /129, mehr als /128 geht nicht. "
                           "Höchstens 2^128 Subnetze."),
]


class RandfallTest(unittest.TestCase):
    """T-K-2: Randfaelle einzeln mit erwarteter Zahl."""

    def test_randfaelle(self):
        for netz, anzahl, k, neu, gesamt, letztes in RANDFAELLE:
            with self.subTest(netz=netz, anzahl=anzahl):
                r = fc.split_network(netz, anzahl)
                self.assertEqual((r["k"], r["neu"], r["anzahl"]), (k, neu, gesamt))
                eintrag = fc.split_entry(r, gesamt - 1)
                self.assertEqual(fc.subnet_net_text(r["version"], eintrag["netz"], neu), letztes)
                basis = ipaddress.ip_network(netz, strict=False)
                self.assertEqual(eintrag["ende"], int(basis.broadcast_address))
                self.assertEqual(r["groesse"] * r["anzahl"], basis.num_addresses)

    def test_zu_viele(self):
        for netz, anzahl, text in ZU_VIELE:
            with self.subTest(netz=netz, anzahl=anzahl):
                self.assertEqual(meldung(lambda: fc.split_network(netz, anzahl)), text)

    def test_grenze_genau(self):
        """/32 bzw. /128 als neuer Praefix ist erlaubt, eins mehr nicht."""
        self.assertEqual(fc.split_network("10.0.0.0/8", 2 ** 24)["neu"], 32)
        self.assertIsNotNone(meldung(lambda: fc.split_network("10.0.0.0/8", 2 ** 24 + 1)))
        self.assertEqual(fc.split_network("::/0", 2 ** 128)["neu"], 128)


# ---------------------------------------------------------------------------
#  T-K-3 Fehlertexte
# ---------------------------------------------------------------------------

NETZ_FEHLER = ("Bitte ein gültiges Netz mit Präfix angeben.\n\n"
               "Beispiele:\n  192.168.10.0/24\n  2001:db8:abcd::/48")


class FehlertextTest(unittest.TestCase):
    """T-K-3: deutsche Meldungen, woertlich."""

    def test_anzahl(self):
        for anzahl in (0, -3, "0", "-3", "-0"):
            with self.subTest(anzahl=anzahl):
                self.assertEqual(meldung(lambda: fc.split_network("10.0.0.0/8", anzahl)),
                                 "Die Anzahl muss mindestens 1 sein.")
        self.assertEqual(meldung(lambda: fc.split_network("10.0.0.0/8", "")),
                         "Bitte einen Wert eingeben: Anzahl Subnetze.")
        self.assertEqual(meldung(lambda: fc.split_network("10.0.0.0/8", "vier")),
                         "Bitte eine Zahl eingeben: Anzahl Subnetze. Zum Beispiel 1.000.")

    def test_ungueltiges_netz(self):
        for text in ("", "   ", "abc", "192.168.10.0", "192.168.300.0/24", "192.168.10.0/33",
                     "2001:db8::/129", "fe80::1%eth0/64", "192.168.10.0 /24", None,
                     "2001:db8:::/48", "1.2.3.4/-1"):
            with self.subTest(text=text):
                self.assertEqual(meldung(lambda: fc.split_network(text, 2)), NETZ_FEHLER)
                self.assertEqual(meldung(lambda: fc.subnet_by_hosts(text, "A 5")), NETZ_FEHLER)

    def test_falscher_modus(self):
        self.assertEqual(meldung(lambda: fc.split_network("2001:db8::/32", 2, 4)),
                         "Im Modus IPv4 bitte ein IPv4-Netz angeben (z. B. 192.168.10.0/24).")
        self.assertEqual(meldung(lambda: fc.split_network("10.0.0.0/8", 2, 6)),
                         "Im Modus IPv6 bitte ein IPv6-Netz angeben (z. B. 2001:db8:abcd::/48).")
        self.assertEqual(meldung(lambda: fc.subnet_by_hosts("2001:db8::/32", "A 5")),
                         "„Nach Hostbedarf“ rechnet nur mit IPv4. "
                         "Für IPv6 bitte „Netz aufteilen“ nutzen.")

    def test_bedarfszeilen(self):
        faelle = [
            ("", "Bitte mindestens ein Subnetz eingeben, je Zeile Name und Hosts (z. B. A 50)."),
            ("\n  \n", "Bitte mindestens ein Subnetz eingeben, je Zeile Name und Hosts "
                       "(z. B. A 50)."),
            ("A 50\nB 0", "Zeile 2: Der Hostbedarf muss mindestens 1 sein."),
            ("A 50\n\nB -5", "Zeile 3: Der Hostbedarf muss mindestens 1 sein."),
            ("A fünfzig", "Zeile 1: Bitte die Anzahl Hosts als ganze Zahl angeben (z. B. A 50)."),
            ("A 50\nB 2,5", "Zeile 2: Bitte je Zeile genau ein Subnetz angeben, ohne Komma, "
                            "Semikolon oder Schrägstrich (z. B. A 50)."),   # M-3 (N-3a, N-4a)
            ("A", "Zeile 1: Bitte die Anzahl Hosts als ganze Zahl angeben (z. B. A 50)."),
            ("\n".join("N%d 5" % i for i in range(13)), "Höchstens 12 Subnetze, eingegeben sind 13."),
            ("Geschaeftsfuehrung 5", "Zeile 1: Der Name ist zu lang (höchstens 16 Zeichen)."),
            ("A 4294967295", "Zeile 1: Mehr als 4.294.967.294 Hosts passen in kein IPv4-Netz."),
        ]
        for text, erwartet in faelle:
            with self.subTest(text=text):
                self.assertEqual(meldung(lambda: fc.read_host_lines(text)), erwartet)
                self.assertEqual(meldung(lambda: fc.subnet_by_hosts("10.0.0.0/8", text)), erwartet)

    def test_passt_nicht(self):
        r = fc.subnet_by_hosts("192.168.10.0/24", "A 200\nB 60")
        self.assertFalse(r["passt"])
        self.assertEqual(r["meldung"],
                         "Es fehlen 64 Adressen. Nötig wäre mindestens ein /23 (512 Adressen).")
        r = fc.subnet_by_hosts("192.168.10.0/24", "A 127\nB 62\nC 30\nD 14\nE 6\nF 2")
        self.assertEqual(r["meldung"],
                         "Es fehlen 124 Adressen. Nötig wäre mindestens ein /23 (512 Adressen).")
        r = fc.subnet_by_hosts("192.168.10.0/30", "A 3")
        self.assertEqual(r["meldung"],
                         "Es fehlen 4 Adressen. Nötig wäre mindestens ein /29 (8 Adressen).")
        r = fc.subnet_by_hosts("10.0.0.0/8", "\n".join(["4294967294"] * 2))
        self.assertEqual(r["meldung"], "Es fehlen 8.573.157.376 Adressen. Das passt in kein "
                                       "IPv4-Netz (höchstens 2^32 Adressen).")
        self.assertIn("Es fehlen 64 Adressen.", fc.hosts_report(
            fc.subnet_by_hosts("192.168.10.0/24", "A 200\nB 60")))


# ---------------------------------------------------------------------------
#  T-K-4 Normalisieren und Schreibweisen (feste Texte, nie ipaddress.compressed)
# ---------------------------------------------------------------------------

class SchreibweiseTest(unittest.TestCase):
    """T-K-4"""

    def test_host_adresse_wird_netz(self):
        r = fc.split_network("192.168.10.5/24", 4)
        self.assertEqual(r["netz"], eigen_v4("192.168.10.0"))
        self.assertEqual(r["hinweis"], "Hinweis: 192.168.10.5/24 ist eine Host-Adresse. "
                                       "Gerechnet wird mit dem Netz 192.168.10.0/24.")
        self.assertIn(r["hinweis"], r["hinweise"])
        self.assertIn(r["hinweis"], " ".join(fc.split_report(r).split()))
        self.assertTrue(fc.split_report(r).startswith("Hinweis: 192.168.10.5/24"))
        r = fc.split_network("2001:DB8:ABCD::1/48", 6)
        self.assertEqual(r["hinweis"], "Hinweis: 2001:db8:abcd::1/48 ist eine Host-Adresse. "
                                       "Gerechnet wird mit dem Netz 2001:db8:abcd::/48.")
        r = fc.subnet_by_hosts("10.20.30.40/16", "A 5")
        self.assertEqual(r["hinweis"], "Hinweis: 10.20.30.40/16 ist eine Host-Adresse. "
                                       "Gerechnet wird mit dem Netz 10.20.0.0/16.")
        for text in ("192.168.10.0/24", "2001:db8::/32", " 10.0.0.0/8 ", "::/0"):
            self.assertIsNone(fc.split_network(text, 2)["hinweis"], text)

    def test_eingaben(self):
        faelle = [
            ("2001:0DB8:0000:0000::/64", "2001:db8::/64", None),
            ("2001:db8:abcd:0012::/64", "2001:db8:abcd:12::/64", None),
            ("::/0", "::/0", None),
            ("::1/128", "::1/128", None),
            ("::/128", "::/128", None),
            ("::ffff:1.2.3.4/128", "::ffff:102:304/128", None),
            ("::ffff:1.2.3.4/96", "::ffff:0:0/96",
             "Hinweis: ::ffff:102:304/96 ist eine Host-Adresse. "
             "Gerechnet wird mit dem Netz ::ffff:0:0/96."),
            ("FE80::/10", "fe80::/10", None),
            ("10.0.0.0/255.255.0.0", "10.0.0.0/16", None),
            ("10.1.2.3/0.0.255.255", "10.1.0.0/16",
             "Hinweis: 10.1.2.3/16 ist eine Host-Adresse. Gerechnet wird mit dem Netz 10.1.0.0/16."),
        ]
        for eingabe, netz, hinweis in faelle:
            with self.subTest(eingabe=eingabe):
                r = fc.subnet_parse(eingabe)
                self.assertEqual(fc.subnet_net_text(r["version"], r["netz"], r["praefix"]), netz)
                self.assertEqual(r["hinweis"], hinweis)

    def test_kurzschreibweise_feste_texte(self):
        faelle = [
            ("0:0:0:0:0:0:0:0", "::"), ("0:0:0:0:0:0:0:1", "::1"), ("1:0:0:0:0:0:0:0", "1::"),
            ("2001:db8:0:0:1:0:0:1", "2001:db8::1:0:0:1"),
            ("2001:0:0:1:0:0:0:1", "2001:0:0:1::1"), ("0:0:1:0:0:0:0:0", "0:0:1::"),
            ("2001:db8:0:1:1:1:1:1", "2001:db8:0:1:1:1:1:1"),
            ("1:2:3:4:5:6:7:8", "1:2:3:4:5:6:7:8"), ("1:0:2:0:3:0:4:0", "1:0:2:0:3:0:4:0"),
            ("0:1:0:0:2:0:0:3", "0:1::2:0:0:3"), ("FE80:0:0:0:0:0:0:0001", "fe80::1"),
            ("2001:0DB8:0000:0000:0000:ff00:0042:8329", "2001:db8::ff00:42:8329"),
            ("0:0:0:0:0:ffff:102:304", "::ffff:102:304"),
            ("ffff:ffff:ffff:ffff:ffff:ffff:ffff:ffff", "ffff:ffff:ffff:ffff:ffff:ffff:ffff:ffff"),
        ]
        for lang, kurz in faelle:
            with self.subTest(lang=lang):
                self.assertEqual(fc.ipv6_text(eigen_v6(lang)), kurz)
                self.assertEqual(eigen_v6_text(eigen_v6(lang)), kurz)

    def test_kurzschreibweise_zufall(self):
        """20.000 Zufallsadressen: Programm = eigene Schreibweise; der Wert
        des Textes (zweite Quelle ipaddress) ist wieder die Zahl."""
        rng = random.Random(5952)
        for _ in range(20000):
            wert = 0
            for _gruppe in range(8):
                wert = wert * 65536 + rng.choice([0, 0, 0, rng.randint(1, 0xFFFF)])
            text = fc.ipv6_text(wert)
            self.assertEqual(text, eigen_v6_text(wert))
            self.assertEqual(int(ipaddress.IPv6Address(text)), wert)
            self.assertEqual(eigen_v6(text), wert)
        for _ in range(2000):
            wert = rng.getrandbits(32)
            self.assertEqual(fc.ipv4_text(wert), eigen_v4_text(wert))


# ---------------------------------------------------------------------------
#  T-K-5 Hostbedarf
# ---------------------------------------------------------------------------

class HostbedarfTest(unittest.TestCase):
    """T-K-5 (Gegenprobe T-K-11 ausserhalb des Arbeitsbaums)."""

    def pruefe(self, netztext, bedarfe):
        basis = ipaddress.IPv4Network(netztext, strict=False)
        netz, praefix = int(basis.network_address), basis.prefixlen
        r = fc.subnet_by_hosts(netztext, [("N%d" % i, b) for i, b in enumerate(bedarfe)])
        eigen = eigen_vergabe(netz, praefix, bedarfe)
        anders = freiliste(basis, bedarfe)
        groessen = [2 ** eigen_hostbits(b) for b in bedarfe]
        self.assertEqual(r["summe"], sum(groessen))
        self.assertEqual(r["kapazitaet"], basis.num_addresses)
        for item, b in zip(r["subnetze"], bedarfe):
            self.assertEqual(item["h"], eigen_hostbits(b))
            self.assertEqual(item["groesse"], 2 ** eigen_hostbits(b))
            self.assertEqual(item["maske"], int(ipaddress.IPv4Network(
                (0, item["praefix"])).netmask))
        if isinstance(eigen, tuple):
            self.assertFalse(r["passt"])
            self.assertIsNone(anders)
            self.assertEqual(r["fehlt"], eigen[1])
            self.assertEqual(r["noetig"], eigen[2])
            self.assertEqual(r["meldung"], "Es fehlen %s Adressen. Nötig wäre mindestens "
                                           "ein /%d (%s Adressen)." % (   # M-9 (N-4c)
                                               "{:,}".format(eigen[1]).replace(",", "."),
                                               eigen[2], "{:,}".format(
                                                   2 ** (32 - eigen[2])).replace(",", ".")))
            return "passt nicht"
        self.assertTrue(r["passt"])
        self.assertEqual(anders, eigen)
        self.assertEqual(r["reihenfolge"], sorted(range(len(bedarfe)),
                                                  key=lambda i: (-bedarfe[i], i)))
        netze = []
        for i, item in enumerate(r["subnetze"]):
            self.assertEqual((item["netz"], item["praefix"]), eigen[i])
            ref = ipaddress.IPv4Network((item["netz"], item["praefix"]))   # strict: ausgerichtet
            self.assertTrue(ref.subnet_of(basis))
            self.assertGreaterEqual(ref.num_addresses - 2, bedarfe[i])
            self.assertTrue(ref.prefixlen == 30 or ref.num_addresses // 2 - 2 < bedarfe[i])
            self.assertEqual(item["erste"], int(ref.network_address) + 1)
            self.assertEqual(item["letzte"], int(ref.broadcast_address) - 1)
            self.assertEqual(item["broadcast"], int(ref.broadcast_address))
            netze.append(ref)
        geordnet = [netze[i] for i in r["reihenfolge"]]
        self.assertEqual(int(geordnet[0].network_address), netz)
        for a, b in zip(geordnet, geordnet[1:]):
            self.assertFalse(a.overlaps(b))
            self.assertGreaterEqual(a.num_addresses, b.num_addresses)   # groesstes zuerst
            self.assertEqual(int(a.broadcast_address) + 1, int(b.network_address))  # keine Luecke
        rest = [ipaddress.IPv4Network(block) for block in r["bloecke"]]   # strict
        self.assertEqual(sum(n.num_addresses for n in netze + rest), basis.num_addresses)
        self.assertEqual(list(ipaddress.collapse_addresses(netze + rest)), [basis])
        self.assertEqual(r["rest"], basis.num_addresses - sum(groessen))
        if r["rest"]:
            self.assertEqual(r["rest_von"], netz + sum(groessen))
            self.assertEqual(r["rest_bis"], int(basis.broadcast_address))
        return "rest 0" if r["rest"] == 0 else "passt"

    def test_zufall(self):
        rng = random.Random(6363)
        zaehler = {"passt": 0, "passt nicht": 0, "rest 0": 0}
        for _ in range(5000):
            praefix = rng.randint(16, 30)
            netz = rng.getrandbits(32) >> (32 - praefix) << (32 - praefix)
            platz = 2 ** (32 - praefix)
            anzahl = rng.randint(1, 12)
            teiler = anzahl * rng.choice([1, 1, 1, 2, 4]) // rng.choice([1, 1, 1, 2])
            bedarfe = [rng.randint(1, max(1, platz // max(1, teiler))) for _ in range(anzahl)]
            zaehler[self.pruefe("%s/%d" % (eigen_v4_text(netz), praefix), bedarfe)] += 1
        # beide Zweige und Rest 0 kommen wirklich vor
        self.assertGreater(zaehler["passt"], 1000, zaehler)
        self.assertGreater(zaehler["passt nicht"], 500, zaehler)
        self.assertGreater(zaehler["rest 0"], 50, zaehler)

    def test_randfaelle(self):
        faelle = [
            ("192.168.10.0/24", [126, 62, 30, 14, 6, 2, 2], "rest 0"),
            ("192.168.10.0/24", [127, 62, 30, 14, 6, 2], "passt nicht"),
            ("192.168.10.0/28", [1, 2, 3], "rest 0"),
            ("192.168.10.0/24", [200], "rest 0"),
            ("192.168.10.0/24", [100], "passt"),
            ("192.168.10.0/24", [20, 20, 20, 20], "passt"),
            ("192.168.10.0/24", [50, 20, 10, 2], "passt"),
            ("192.168.10.0/30", [2], "rest 0"),
            ("192.168.10.0/30", [3], "passt nicht"),
            ("192.168.10.0/24", [10] * 12, "passt"),
            ("192.168.10.0/26", [14] * 4, "rest 0"),
            ("0.0.0.0/0", [4294967294], "rest 0"),
            ("10.0.0.0/8", [1], "passt"),
        ]
        for netz, bedarfe, erwartet in faelle:
            with self.subTest(netz=netz, bedarfe=bedarfe):
                self.assertEqual(self.pruefe(netz, bedarfe), erwartet)

    def test_beispiel_d(self):
        r = fc.subnet_by_hosts("192.168.10.0/24", "A 50\nB 20\nC 10\nD 2")
        texte = ["%s/%d" % (fc.ipv4_text(i["netz"]), i["praefix"]) for i in r["subnetze"]]
        self.assertEqual(texte, ["192.168.10.0/26", "192.168.10.64/27", "192.168.10.96/28",
                                 "192.168.10.112/30"])
        self.assertEqual(r["summe"], 116)
        self.assertEqual(r["rest"], 140)
        self.assertEqual([fc.subnet_net_text(4, n, p) for n, p in r["bloecke"]],
                         ["192.168.10.116/30", "192.168.10.120/29", "192.168.10.128/25"])
        self.assertEqual(r["hinweise"][-1], fc.SUBNET_HINT_P2P)

    def test_reihenfolge_und_namen(self):
        r = fc.subnet_by_hosts("10.0.0.0/23", "Klein 2\nGross: 100\n30 Hosts\nGleich 100")
        self.assertEqual([i["name"] for i in r["subnetze"]], ["Klein", "Gross", "Netz 3", "Gleich"])
        self.assertEqual(r["reihenfolge"], [1, 3, 2, 0])      # bei Gleichstand Eingabe
        self.assertEqual(fc.read_host_lines("A:50\nVertrieb Nord 20 Hosts\n7"),
                         [("A", 50), ("Vertrieb Nord", 20), ("Netz 3", 7)])
        self.assertEqual(fc.read_host_lines("A 1.000"), [("A", 1000)])
        bericht = fc.hosts_report(r)
        self.assertLess(bericht.index("Klein ("), bericht.index("Gross ("))

    def test_bedarf_1_2_3(self):
        r = fc.subnet_by_hosts("10.0.0.0/24", [("a", 1), ("b", 2), ("c", 3)])
        self.assertEqual([i["praefix"] for i in r["subnetze"]], [30, 30, 29])


# ---------------------------------------------------------------------------
#  T-K-6 Laufzeit ohne Aufzaehlen
# ---------------------------------------------------------------------------

NEUE_FUNKTIONEN = ["subnet_parse", "subnet_count", "split_network", "split_entry",
                   "split_page", "split_report", "read_host_lines", "subnet_by_hosts",
                   "subnet_blocks", "hosts_report", "ipv6_text", "ipv4_text"]


class LaufzeitTest(unittest.TestCase):
    """T-K-6: grosse Netze sofort, erste und letzte Seite unter 50 ms."""

    def messe(self, netz, anzahl):
        start = time.perf_counter()
        r = fc.split_network(netz, anzahl)
        erste = fc.split_page(r, 1)
        letzte = fc.split_page(r, r["seiten"])
        fc.split_report(r, r["seiten"])
        fc.split_report(r, r["seiten"], schmal=True)
        dauer = (time.perf_counter() - start) * 1000
        return r, erste, letzte, dauer

    def test_grosse_netze(self):
        for netz, anzahl, neu in [("::/0", 2 ** 64, 64), ("10.0.0.0/8", 2 ** 24, 32),
                                  ("::/0", 2 ** 127, 127), ("2001:db8::/32", 2 ** 32, 64),
                                  ("0.0.0.0/0", 2 ** 32, 32), ("::/0", 2 ** 128, 128)]:
            with self.subTest(netz=netz, anzahl=anzahl):
                r, erste, letzte, dauer = self.messe(netz, anzahl)
                self.assertEqual(r["neu"], neu)
                self.assertLess(dauer, 50, "%.1f ms" % dauer)
                self.assertEqual(len(erste["eintraege"]), 8)
                self.assertEqual(letzte["eintraege"][-1]["nr"], anzahl)
                self.assertEqual(letzte["eintraege"][-1]["ende"],
                                 int(ipaddress.ip_network(netz).broadcast_address))
                self.assertEqual(r["seiten"], anzahl // 8)

    def test_hostbedarf_gross(self):
        start = time.perf_counter()
        r = fc.subnet_by_hosts("0.0.0.0/0", "\n".join(str(2 ** (31 - i)) for i in range(12)))
        fc.hosts_report(r)
        self.assertLess((time.perf_counter() - start) * 1000, 50)

    def test_kein_aufzaehlen_im_code(self):
        for name in NEUE_FUNKTIONEN:
            quelle = inspect.getsource(getattr(fc, name))
            for verboten in (".subnets(", ".hosts(", "ip_network((", "IPv4Network((",
                             "IPv6Network((", "num_addresses", "list(range"):
                self.assertNotIn(verboten, quelle, name)


# ---------------------------------------------------------------------------
#  T-K-7 Seiten, T-K-8 Nibble, T-K-9 /31 /32, T-K-10 Leseregel, T-K-12 Version
# ---------------------------------------------------------------------------

class SeitenTest(unittest.TestCase):
    """T-K-7"""

    def test_seitenzahl(self):
        for k in range(0, 21):
            r = fc.split_network("::/0", 2 ** k)
            seiten = -(-2 ** k // 8)                       # aufgerundet
            self.assertEqual(r["seiten"], seiten)
            letzte = fc.split_page(r, seiten)
            self.assertEqual(len(letzte["eintraege"]), 2 ** k - (seiten - 1) * 8)
            self.assertEqual(letzte["eintraege"][-1]["nr"], 2 ** k)

    def test_kurze_letzte_seite_und_grenzen(self):
        r = fc.split_network("192.168.10.0/24", 3)
        self.assertEqual(r["seiten"], 1)
        self.assertEqual([e["nr"] for e in fc.split_page(r, 1)["eintraege"]], [1, 2, 3, 4])
        r = fc.split_network("192.168.10.0/24", 20)            # 32 Subnetze, 4 Seiten
        self.assertEqual(fc.split_page(r, 0)["seite"], 1)
        self.assertEqual(fc.split_page(r, -5)["seite"], 1)
        self.assertEqual(fc.split_page(r, 99)["seite"], 4)
        self.assertEqual([e["nr"] for e in fc.split_page(r, 3)["eintraege"]],
                         list(range(17, 25)))
        self.assertEqual(fc.split_page(r, 4)["eintraege"][0]["status"], "frei, Reserve")
        self.assertEqual(fc.split_page(r, 3)["eintraege"][3]["status"], "verwendet")
        self.assertEqual(fc.split_page(r, 3)["eintraege"][4]["status"], "frei, Reserve")

    def test_seitentext(self):
        r = fc.split_network("2001:db8:abcd::/48", 65536)
        self.assertEqual(fc.split_page(r, 1)["text"], "Seite 1 von 8.192")
        self.assertTrue(fc.split_report(r, 2).endswith("Seite 2 von 8.192"))


class NibbleTest(unittest.TestCase):
    """T-K-8"""

    def test_nibble_genau_dann(self):
        for praefix in range(0, 129, 3):
            for anzahl in (1, 2, 3, 5, 6, 12, 17, 100):
                if praefix + eigen_bits(anzahl) > 128:
                    continue
                r = fc.split_network("::/%d" % praefix, anzahl)
                neu = praefix + eigen_bits(anzahl)
                if neu % 4:
                    naechste = neu + (4 - neu % 4)
                    self.assertEqual(r["nibble"], naechste)
                    self.assertEqual(r["nibble_anzahl"], 2 ** (naechste - praefix))
                else:
                    self.assertIsNone(r["nibble"])
        self.assertEqual(fc.split_network("2001:db8:abcd::/48", 12)["nibble"], None)
        self.assertEqual(fc.split_network("2001:db8:abcd::/48", 6)["nibble"], 52)
        self.assertIsNone(fc.split_network("10.0.0.0/8", 6)["nibble"])        # IPv4: nie


class SonderpraefixTest(unittest.TestCase):
    """T-K-9"""

    def test_31_und_32(self):
        r = fc.split_network("192.168.10.0/24", 128)
        self.assertEqual(r["neu"], 31)
        self.assertIn("/31: 2 Adressen, nur für Punkt-zu-Punkt-Verbindungen (RFC 3021)",
                      r["hinweise"])
        e = fc.split_entry(r, 1)
        self.assertEqual((e["erste"], e["letzte"], e["broadcast"]),
                         (eigen_v4("192.168.10.2"), eigen_v4("192.168.10.3"), None))
        self.assertIn("keine", fc.split_report(r))
        r = fc.split_network("192.168.10.0/24", 256)
        self.assertIn("/32: eine einzelne Adresse", r["hinweise"])
        e = fc.split_entry(r, 5)
        self.assertEqual((e["erste"], e["letzte"], e["broadcast"]),
                         (eigen_v4("192.168.10.5"),) * 2 + (None,))
        r = fc.split_network("192.168.10.0/24", 64)
        self.assertFalse([h for h in r["hinweise"] if h.startswith("/3")])

    def test_ipv6_ohne_broadcast(self):
        e = fc.split_entry(fc.split_network("2001:db8::/126", 2), 1)
        self.assertIsNone(e["broadcast"])
        self.assertEqual((e["erste"], e["letzte"]), (e["netz"], e["netz"] + 1))


class LeseregelTest(unittest.TestCase):
    """T-K-10: Anzahl ueber read_number (gleiche Leseregel wie die anderen
    Rechner), dazu genau ueber 2^53."""

    def test_leseregel(self):
        self.assertEqual(fc.split_network("::/0", "1.000")["gewuenscht"], 1000)
        self.assertEqual(fc.split_network("::/0", "1.000")["k"], 10)
        self.assertEqual(fc.split_network("::/0", "1 000")["gewuenscht"], 1000)
        self.assertEqual(fc.split_network("::/0", " 6 ")["gewuenscht"], 6)
        for text in ("1,5", "1.5", "2,25"):
            self.assertEqual(meldung(lambda: fc.split_network("::/0", text)),
                             "Bitte eine ganze Zahl eingeben: Anzahl Subnetze.")
        self.assertEqual(fc.split_network("::/0", "4,0")["gewuenscht"], 4)

    def test_genau_ueber_2_hoch_53(self):
        r = fc.split_network("::/0", "9007199254740993")       # 2^53 + 1
        self.assertEqual(r["gewuenscht"], 2 ** 53 + 1)
        self.assertEqual(r["k"], 54)
        self.assertEqual(meldung(lambda: fc.split_network("::/0", "9.007.199.254.740.993")),
                         "Bitte eine Zahl eingeben: Anzahl Subnetze. Zum Beispiel 1.000.")
        self.assertEqual(fc.split_network("::/0", "900.719.925.474.099")["gewuenscht"],
                         900719925474099)
        r = fc.split_network("::/0", "18446744073709551617")  # 2^64 + 1, 20 Zeichen
        self.assertEqual(r["k"], 65)
        self.assertEqual(fc.split_network("::/0", "18446744073709551616")["k"], 64)
        self.assertEqual(meldung(lambda: fc.split_network("::/0", "9007199254740993,5")),
                         "Bitte eine ganze Zahl eingeben: Anzahl Subnetze.")


class VersionTest(unittest.TestCase):
    """T-K-12: /0 bei IPv4 und IPv6 getrennt (Lehre Plan 0.63 S.6 Nr. 3)."""

    def test_null_netze(self):
        v4 = fc.split_network("0.0.0.0/0", 2)
        v6 = fc.split_network("::/0", 2)
        self.assertEqual((v4["version"], v4["breite"], v4["groesse"]), (4, 32, 2 ** 31))
        self.assertEqual((v6["version"], v6["breite"], v6["groesse"]), (6, 128, 2 ** 127))
        self.assertEqual(fc.subnet_net_text(4, fc.split_entry(v4, 1)["netz"], 1), "128.0.0.0/1")
        self.assertEqual(fc.subnet_net_text(6, fc.split_entry(v6, 1)["netz"], 1), "8000::/1")
        self.assertIn("128.0.0.0/1", fc.split_report(v4))
        self.assertIn("8000::/1", fc.split_report(v6))
        self.assertEqual(fc.subnet_parse("::/0")["version"], 6)
        self.assertEqual(fc.subnet_parse("0.0.0.0/0")["version"], 4)


class BeschriftungTest(unittest.TestCase):
    """T-UI-3 (Teil Rechenkern): Beschriftungen kommen aus fisi_core."""

    def test_konstanten(self):
        self.assertEqual(fc.SUBNET_TITLE, "Subnetting")
        self.assertEqual(fc.SUBNET_MODES, [("ipv4", "IPv4"), ("ipv6", "IPv6")])
        self.assertEqual([t for _k, t in fc.SUBNET_VIEWS["ipv4"]],
                         ["Netzdaten", "Netz aufteilen", "Nach Hostbedarf"])
        self.assertEqual([t for _k, t in fc.SUBNET_VIEWS["ipv6"]],
                         ["Netzdaten", "Netz aufteilen"])
        self.assertEqual(fc.SUBNET_FIELD_NET["ipv4"], "Netz mit Präfix (z. B. 192.168.10.0/24)")
        self.assertEqual(fc.SUBNET_FIELD_NET["ipv6"],
                         "Netz mit Präfix (z. B. 2001:db8:abcd::/48)")
        self.assertEqual(fc.SUBNET_FIELD_COUNT, "Anzahl Subnetze")
        self.assertEqual(fc.SUBNET_FIELD_NEEDS, "Subnetze, je Zeile Name und Hosts (z. B. A 50)")
        self.assertEqual((fc.SUBNET_PAGE_FIRST, fc.SUBNET_PAGE_BACK, fc.SUBNET_PAGE_NEXT,
                          fc.SUBNET_PAGE_LAST), ("Erste Seite", "Zurück", "Weiter",
                                                 "Letzte Seite"))
        self.assertEqual(fc.SUBNET_PAGE_SIZE, 8)
        self.assertEqual(fc.SUBNET_HOSTS_MAX, 12)
        # die Vorgaben rechnen ohne Fehler
        netz, anzahl = fc.SUBNET_DEFAULTS[("ipv4", "aufteilen")]
        self.assertEqual(fc.split_network(netz, anzahl, 4)["neu"], 27)
        netz, anzahl = fc.SUBNET_DEFAULTS[("ipv6", "aufteilen")]
        self.assertEqual(fc.split_network(netz, anzahl, 6)["neu"], 51)
        netz, bedarf = fc.SUBNET_DEFAULTS[("ipv4", "bedarf")]
        self.assertTrue(fc.subnet_by_hosts(netz, bedarf, 4)["passt"])


class ErgebnisTextTest(unittest.TestCase):
    """Ergebnistexte: Handy hoechstens 28 Zeichen, PC hoechstens 75."""

    def test_breiten(self):
        rng = random.Random(28)
        faelle = [("192.168.10.0/24", n) for n in (1, 3, 6, 64, 128, 256)] + [
            ("0.0.0.0/0", 2 ** 32), ("::/0", 2 ** 64), ("2001:db8:abcd::/48", 6),
            ("ffff:ffff:ffff:ffff:ffff:ffff:ffff:ff00/120", 200)]
        for _ in range(300):
            v6 = rng.random() < 0.5
            breite = 128 if v6 else 32
            p = rng.randint(0, breite)
            netz = rng.getrandbits(breite)
            text = (fc.ipv6_text(netz) if v6 else fc.ipv4_text(netz)) + "/%d" % p
            faelle.append((text, rng.randint(1, 2 ** (breite - p))))
        for netz, anzahl in faelle:
            r = fc.split_network(netz, anzahl)
            for seite in (1, r["seiten"]):
                for zeile in fc.split_report(r, seite, schmal=True).split("\n"):
                    self.assertLessEqual(len(zeile), GRENZE, (netz, anzahl, zeile))
                for zeile in fc.split_report(r, seite).split("\n"):
                    self.assertLessEqual(len(zeile), PC_BREITE, (netz, anzahl, zeile))
        for bedarf in ("A 50\nB 20\nC 10\nD 2", "Geschaeftsleitun 4294967\nB 2",
                       "\n".join("Vertrieb Nord %d: %d" % (i, i) for i in range(1, 13))):
            for netz in ("0.0.0.0/0", "192.168.10.0/24", "10.0.0.0/8"):
                r = fc.subnet_by_hosts(netz, bedarf)
                for zeile in fc.hosts_report(r, schmal=True).split("\n"):
                    self.assertLessEqual(len(zeile), GRENZE, (bedarf, zeile))
                for zeile in fc.hosts_report(r).split("\n"):
                    self.assertLessEqual(len(zeile), PC_BREITE, (bedarf, zeile))



# ===========================================================================
#  Ab hier T2 (Plan 0.63): Rechenwege "Netz aufteilen" und "Nach Hostbedarf"
#
#  T-RW-1  Handy hoechstens 28 Zeichen, PC hoechstens 75 Zeichen je Zeile,
#          500 Zufallseingaben je Art und Randfaelle
#  T-RW-2  gleiche Werte PC = Handy in gleicher Reihenfolge, gleiche Schritte
#  T-RW-3  die zehn Beispiele A bis J aus Anhang A und A2 woertlich,
#          PC und Handy (Plan 0.63 Fassung 4, b2)
#  T-K-8   Nibble-Zeile im Rechenweg genau dann, wenn noetig
# ===========================================================================

# Anhang A und A2 / belege/b2_rechenweg_beispiele.txt (Plan 0.63 Fassung 4),
# Beispiele A bis J, PC und Handy, Zeile fuer Zeile
ANHANG_A = {
    'A_HANDY': (
        'RECHENWEG NETZ AUFTEILEN',
        '(IPv4)',
        'Ausgangsnetz',
        ' 10.20.0.0/16',
        'gesucht: 4 gleich große',
        'Subnetze',
        '',
        'SCHRITT 1: Bits für die',
        'Subnetze',
        ' Gesucht: kleinstes k mit',
        ' 2^k >= 4',
        ' 2^1 = 2 < 4 (zu wenig)',
        ' 2^2 = 4 >= 4 -> k = 2',
        '',
        'SCHRITT 2: Neue Präfixlänge',
        ' alte Präfixlänge + k',
        ' = 16 + 2 = 18 -> /18',
        '',
        'SCHRITT 3: Maske, Hostbits,',
        'Schrittweite',
        ' /18, Oktett für Oktett:',
        ' 1. Oktett 11111111 = 255',
        ' 2. Oktett 11111111 = 255',
        ' 3. Oktett 11000000 = 192',
        ' 4. Oktett 00000000 =   0',
        ' -> Subnetzmaske:',
        '    255.255.192.0',
        ' Hostbits = 32 - 18 = 14',
        ' Adressen je Subnetz',
        ' = 2^14 = 16.384',
        ' Schrittweite im 3. Oktett',
        ' = 256 - 192 = 64',
        ' Nutzbare Hosts je Subnetz',
        ' = 2^14 - 2 = 16.382',
        '',
        'SCHRITT 4: Subnetze',
        'auflisten',
        ' Netzadresse + Schrittweite',
        ' ergibt das nächste Subnetz.',
        'Subnetz 1: verwendet',
        ' Netz: 10.20.0.0/18',
        ' Erste: 10.20.0.1',
        ' Letzte: 10.20.63.254',
        ' Broadcast: 10.20.63.255',
        'Subnetz 2: verwendet',
        ' Netz: 10.20.64.0/18',
        ' Erste: 10.20.64.1',
        ' Letzte: 10.20.127.254',
        ' Broadcast: 10.20.127.255',
        'Subnetz 3: verwendet',
        ' Netz: 10.20.128.0/18',
        ' Erste: 10.20.128.1',
        ' Letzte: 10.20.191.254',
        ' Broadcast: 10.20.191.255',
        'Subnetz 4: verwendet',
        ' Netz: 10.20.192.0/18',
        ' Erste: 10.20.192.1',
        ' Letzte: 10.20.255.254',
        ' Broadcast: 10.20.255.255',
        '',
        'SCHRITT 5: Kontrolle',
        ' 4 x 16.384',
        ' = 65.536 Adressen',
        ' = Größe von /16',
        ' (2^16 = 65.536)',
        ' Ältere Bücher ziehen 2',
        ' Subnetze ab. Das ist',
        ' veraltet (RFC 1878).',
    ),
    'A_PC': (
        'RECHENWEG NETZ AUFTEILEN (IPv4)',
        'Ausgangsnetz 10.20.0.0/16, gesucht: 4 gleich große Subnetze',
        '',
        'SCHRITT 1: Benötigte Bits für die Subnetze',
        '   Gesucht ist das kleinste k mit 2^k >= 4.',
        '   2^1 = 2 < 4 (zu wenig)',
        '   2^2 = 4 >= 4 -> k = 2',
        '',
        'SCHRITT 2: Neue Präfixlänge',
        '   neue Präfixlänge = alte Präfixlänge + k = 16 + 2 = 18 -> /18',
        '',
        'SCHRITT 3: Subnetzmaske, Hostbits und Schrittweite',
        '   /18 = 11111111.11111111.11000000.00000000',
        '   -> Subnetzmaske: 255.255.192.0',
        '   Hostbits = 32 - 18 = 14',
        '   Adressen je Subnetz = 2^14 = 16.384',
        '   Schrittweite im 3. Oktett = 256 - 192 = 64',
        '   Nutzbare Hosts je Subnetz = 2^14 - 2 = 16.382',
        '',
        'SCHRITT 4: Subnetze auflisten',
        '   (Netzadresse + Schrittweite = nächstes Subnetz)',
        '  Nr Netzadresse        Erster Host     Letzter Host    Broadcast',
        '  1  10.20.0.0/18       10.20.0.1       10.20.63.254    10.20.63.255',
        '  2  10.20.64.0/18      10.20.64.1      10.20.127.254   10.20.127.255',
        '  3  10.20.128.0/18     10.20.128.1     10.20.191.254   10.20.191.255',
        '  4  10.20.192.0/18     10.20.192.1     10.20.255.254   10.20.255.255',
        '',
        'SCHRITT 5: Kontrolle',
        '   4 x 16.384 = 65.536 Adressen = Größe von /16 (2^16 = 65.536)',
        '   Alle 4 Subnetze werden verwendet.',
        '   Ältere Bücher ziehen 2 Subnetze ab. Das ist veraltet (RFC 1878).',
    ),
    'B_HANDY': (
        'RECHENWEG NETZ AUFTEILEN',
        '(IPv4)',
        'Ausgangsnetz',
        ' 192.168.10.0/24',
        'gesucht: 6 gleich große',
        'Subnetze',
        '',
        'SCHRITT 1: Bits für die',
        'Subnetze',
        ' Gesucht: kleinstes k mit',
        ' 2^k >= 6',
        ' 2^2 = 4 < 6 (zu wenig)',
        ' 2^3 = 8 >= 6 -> k = 3',
        '',
        'SCHRITT 2: Neue Präfixlänge',
        ' alte Präfixlänge + k',
        ' = 24 + 3 = 27 -> /27',
        '',
        'SCHRITT 3: Maske, Hostbits,',
        'Schrittweite',
        ' /27, Oktett für Oktett:',
        ' 1. Oktett 11111111 = 255',
        ' 2. Oktett 11111111 = 255',
        ' 3. Oktett 11111111 = 255',
        ' 4. Oktett 11100000 = 224',
        ' -> Subnetzmaske:',
        '    255.255.255.224',
        ' Hostbits = 32 - 27 = 5',
        ' Adressen je Subnetz',
        ' = 2^5 = 32',
        ' Schrittweite im 4. Oktett',
        ' = 256 - 224 = 32',
        ' Nutzbare Hosts je Subnetz',
        ' = 2^5 - 2 = 30',
        '',
        'SCHRITT 4: Subnetze',
        'auflisten',
        ' Netzadresse + Schrittweite',
        ' ergibt das nächste Subnetz.',
        'Subnetz 1: verwendet',
        ' Netz: 192.168.10.0/27',
        ' Erste: 192.168.10.1',
        ' Letzte: 192.168.10.30',
        ' Broadcast: 192.168.10.31',
        'Subnetz 2: verwendet',
        ' Netz: 192.168.10.32/27',
        ' Erste: 192.168.10.33',
        ' Letzte: 192.168.10.62',
        ' Broadcast: 192.168.10.63',
        'Subnetz 3: verwendet',
        ' Netz: 192.168.10.64/27',
        ' Erste: 192.168.10.65',
        ' Letzte: 192.168.10.94',
        ' Broadcast: 192.168.10.95',
        'Subnetz 4: verwendet',
        ' Netz: 192.168.10.96/27',
        ' Erste: 192.168.10.97',
        ' Letzte: 192.168.10.126',
        ' Broadcast: 192.168.10.127',
        'Subnetz 5: verwendet',
        ' Netz: 192.168.10.128/27',
        ' Erste: 192.168.10.129',
        ' Letzte: 192.168.10.158',
        ' Broadcast: 192.168.10.159',
        'Subnetz 6: verwendet',
        ' Netz: 192.168.10.160/27',
        ' Erste: 192.168.10.161',
        ' Letzte: 192.168.10.190',
        ' Broadcast: 192.168.10.191',
        'Subnetz 7: frei, Reserve',
        ' Netz: 192.168.10.192/27',
        ' Erste: 192.168.10.193',
        ' Letzte: 192.168.10.222',
        ' Broadcast: 192.168.10.223',
        'Subnetz 8: frei, Reserve',
        ' Netz: 192.168.10.224/27',
        ' Erste: 192.168.10.225',
        ' Letzte: 192.168.10.254',
        ' Broadcast: 192.168.10.255',
        '',
        'SCHRITT 5: Kontrolle',
        ' 8 x 32',
        ' = 256 Adressen',
        ' = Größe von /24',
        ' (2^8 = 256)',
        ' 6 ist keine Zweierpotenz:',
        ' Es entstehen 2^3 = 8',
        ' Subnetze. Die ersten 6',
        ' werden verwendet, der Rest',
        ' bleibt frei (Reserve).',
        ' Ältere Bücher ziehen 2',
        ' Subnetze ab. Das ist',
        ' veraltet (RFC 1878).',
    ),
    'B_PC': (
        'RECHENWEG NETZ AUFTEILEN (IPv4)',
        'Ausgangsnetz 192.168.10.0/24, gesucht: 6 gleich große Subnetze',
        '',
        'SCHRITT 1: Benötigte Bits für die Subnetze',
        '   Gesucht ist das kleinste k mit 2^k >= 6.',
        '   2^2 = 4 < 6 (zu wenig)',
        '   2^3 = 8 >= 6 -> k = 3',
        '',
        'SCHRITT 2: Neue Präfixlänge',
        '   neue Präfixlänge = alte Präfixlänge + k = 24 + 3 = 27 -> /27',
        '',
        'SCHRITT 3: Subnetzmaske, Hostbits und Schrittweite',
        '   /27 = 11111111.11111111.11111111.11100000',
        '   -> Subnetzmaske: 255.255.255.224',
        '   Hostbits = 32 - 27 = 5',
        '   Adressen je Subnetz = 2^5 = 32',
        '   Schrittweite im 4. Oktett = 256 - 224 = 32',
        '   Nutzbare Hosts je Subnetz = 2^5 - 2 = 30',
        '',
        'SCHRITT 4: Subnetze auflisten',
        '   (Netzadresse + Schrittweite = nächstes Subnetz)',
        '  Nr Netzadresse        Erster Host     Letzter Host    Broadcast',
        '  1  192.168.10.0/27    192.168.10.1    192.168.10.30   192.168.10.31',
        '  2  192.168.10.32/27   192.168.10.33   192.168.10.62   192.168.10.63',
        '  3  192.168.10.64/27   192.168.10.65   192.168.10.94   192.168.10.95',
        '  4  192.168.10.96/27   192.168.10.97   192.168.10.126  192.168.10.127',
        '  5  192.168.10.128/27  192.168.10.129  192.168.10.158  192.168.10.159',
        '  6  192.168.10.160/27  192.168.10.161  192.168.10.190  192.168.10.191',
        '  7  192.168.10.192/27  192.168.10.193  192.168.10.222  192.168.10.223',
        '  8  192.168.10.224/27  192.168.10.225  192.168.10.254  192.168.10.255',
        '',
        'SCHRITT 5: Kontrolle',
        '   8 x 32 = 256 Adressen = Größe von /24 (2^8 = 256)',
        '   6 ist keine Zweierpotenz: Es entstehen 2^3 = 8 Subnetze.',
        '   Die ersten 6 werden verwendet (Nr. 1 bis 6), Nr. 7 und 8',
        '   bleiben frei (Reserve).',
        '   Ältere Bücher ziehen 2 Subnetze ab. Das ist veraltet (RFC 1878).',
    ),
    'C_HANDY': (
        'RECHENWEG NETZ AUFTEILEN',
        '(IPv6)',
        'Ausgangsnetz',
        ' 2001:db8:abcd::/48',
        'gesucht: 6 gleich große',
        'Subnetze',
        '',
        'SCHRITT 1: Bits für die',
        'Subnetze',
        ' Gesucht: kleinstes k mit',
        ' 2^k >= 6',
        ' 2^2 = 4 < 6 (zu wenig)',
        ' 2^3 = 8 >= 6 -> k = 3',
        '',
        'SCHRITT 2: Neue Präfixlänge',
        ' alte Präfixlänge + k',
        ' = 48 + 3 = 51 -> /51',
        ' An der nächsten',
        ' 4-Bit-Grenze (Nibble): /52',
        ' = 16 Subnetze. In der',
        ' Praxis üblich, weil dann',
        ' jede Hex-Ziffer ein Teil',
        ' der Subnetz-Nummer ist.',
        ' Gerechnet wird hier weiter',
        ' mit /51.',
        '',
        'SCHRITT 3: Wo liegt die',
        'Grenze?',
        ' /51 endet im 4. Hextett',
        ' (Bits 49 bis 64).',
        ' Davon Netzanteil:',
        ' 51 - 48 = 3 Bits',
        ' Schrittweite im 4. Hextett',
        ' = 2^(64 - 51) = 2^13',
        ' = 8.192 = hex 2000',
        ' Adressen je Subnetz:',
        ' 2^(128 - 51) = 2^77',
        ' = 151.115.727.451.828.646',
        '  .838.272',
        ' Kein Abzug von 2: IPv6',
        ' hat keine Broadcast-',
        ' Adresse.',
        ' Einzelne Adressen sind',
        ' reserviert, z. B. die',
        ' Subnet-Router-Anycast-',
        ' Adresse (alle Bits der',
        ' Schnittstellenkennung 0,',
        ' RFC 4291 2.6.1).',
        '',
        'SCHRITT 4: Subnetze',
        'auflisten',
        ' 4. Hextett um die',
        ' Schrittweite erhöhen:',
        'Subnetz 1: verwendet',
        ' Bits 000 im 4. Hextett:',
        '  0000 0000 0000 0000 = 0000',
        ' Netz: 2001:db8:abcd::/51',
        ' bis:',
        '  2001:db8:abcd:1fff:',
        '  ffff:ffff:ffff:ffff',
        'Subnetz 2: verwendet',
        ' Bits 001 im 4. Hextett:',
        '  0010 0000 0000 0000 = 2000',
        ' Netz:',
        '  2001:db8:abcd:2000::/51',
        ' bis:',
        '  2001:db8:abcd:3fff:',
        '  ffff:ffff:ffff:ffff',
        'Subnetz 3: verwendet',
        ' Bits 010 im 4. Hextett:',
        '  0100 0000 0000 0000 = 4000',
        ' Netz:',
        '  2001:db8:abcd:4000::/51',
        ' bis:',
        '  2001:db8:abcd:5fff:',
        '  ffff:ffff:ffff:ffff',
        'Subnetz 4: verwendet',
        ' Bits 011 im 4. Hextett:',
        '  0110 0000 0000 0000 = 6000',
        ' Netz:',
        '  2001:db8:abcd:6000::/51',
        ' bis:',
        '  2001:db8:abcd:7fff:',
        '  ffff:ffff:ffff:ffff',
        'Subnetz 5: verwendet',
        ' Bits 100 im 4. Hextett:',
        '  1000 0000 0000 0000 = 8000',
        ' Netz:',
        '  2001:db8:abcd:8000::/51',
        ' bis:',
        '  2001:db8:abcd:9fff:',
        '  ffff:ffff:ffff:ffff',
        'Subnetz 6: verwendet',
        ' Bits 101 im 4. Hextett:',
        '  1010 0000 0000 0000 = a000',
        ' Netz:',
        '  2001:db8:abcd:a000::/51',
        ' bis:',
        '  2001:db8:abcd:bfff:',
        '  ffff:ffff:ffff:ffff',
        'Subnetz 7: frei, Reserve',
        ' Bits 110 im 4. Hextett:',
        '  1100 0000 0000 0000 = c000',
        ' Netz:',
        '  2001:db8:abcd:c000::/51',
        ' bis:',
        '  2001:db8:abcd:dfff:',
        '  ffff:ffff:ffff:ffff',
        'Subnetz 8: frei, Reserve',
        ' Bits 111 im 4. Hextett:',
        '  1110 0000 0000 0000 = e000',
        ' Netz:',
        '  2001:db8:abcd:e000::/51',
        ' bis:',
        '  2001:db8:abcd:ffff:',
        '  ffff:ffff:ffff:ffff',
        '',
        'SCHRITT 5: Kontrolle',
        ' 8 x 2^77 = 2^80',
        ' = Größe von /48',
        ' 6 ist keine Zweierpotenz:',
        ' Es entstehen 2^3 = 8',
        ' Subnetze. Die ersten 6',
        ' werden verwendet, der Rest',
        ' bleibt frei (Reserve).',
    ),
    'C_PC': (
        'RECHENWEG NETZ AUFTEILEN (IPv6)',
        'Ausgangsnetz 2001:db8:abcd::/48, gesucht: 6 gleich große Subnetze',
        '',
        'SCHRITT 1: Benötigte Bits für die Subnetze',
        '   Gesucht ist das kleinste k mit 2^k >= 6.',
        '   2^2 = 4 < 6 (zu wenig)',
        '   2^3 = 8 >= 6 -> k = 3',
        '',
        'SCHRITT 2: Neue Präfixlänge',
        '   neue Präfixlänge = alte Präfixlänge + k = 48 + 3 = 51 -> /51',
        '   An der nächsten 4-Bit-Grenze (Nibble): /52 = 16 Subnetze. In der Praxis',
        '   üblich, weil dann jede Hex-Ziffer ein Teil der Subnetz-Nummer ist.',
        '   Gerechnet wird hier weiter mit /51.',
        '',
        'SCHRITT 3: Wo liegt die Grenze? Schrittweite und Größe',
        '   /51 endet im 4. Hextett (Bits 49 bis 64). Davon gehören',
        '   51 - 48 = 3 Bits zum Netzanteil.',
        '   Schrittweite im 4. Hextett = 2^(64 - 51) = 2^13 = 8.192 = hex 2000',
        '   Adressen je Subnetz = 2^(128 - 51) = 2^77',
        '      = 151.115.727.451.828.646.838.272',
        '   Kein Abzug von 2: IPv6 hat keine Broadcast-Adresse.',
        '   Einzelne Adressen sind reserviert, z. B. die',
        '   Subnet-Router-Anycast-Adresse (alle Bits der Schnittstellenkennung 0,',
        '   RFC 4291 2.6.1).',
        '',
        'SCHRITT 4: Subnetze auflisten (4. Hextett um die Schrittweite erhöhen)',
        '  Nr Bits 4. Hextett binär        hex   Subnetz',
        '  1  000  0000 0000 0000 0000 = 0000  2001:db8:abcd::/51',
        '  2  001  0010 0000 0000 0000 = 2000  2001:db8:abcd:2000::/51',
        '  3  010  0100 0000 0000 0000 = 4000  2001:db8:abcd:4000::/51',
        '  4  011  0110 0000 0000 0000 = 6000  2001:db8:abcd:6000::/51',
        '  5  100  1000 0000 0000 0000 = 8000  2001:db8:abcd:8000::/51',
        '  6  101  1010 0000 0000 0000 = a000  2001:db8:abcd:a000::/51',
        '  7  110  1100 0000 0000 0000 = c000  2001:db8:abcd:c000::/51',
        '  8  111  1110 0000 0000 0000 = e000  2001:db8:abcd:e000::/51',
        '',
        '   Bereich je Subnetz: von der Netzadresse bis zur letzten Adresse,',
        '   z. B. Subnetz 1: 2001:db8:abcd:: bis',
        '                    2001:db8:abcd:1fff:ffff:ffff:ffff:ffff',
        '',
        'SCHRITT 5: Kontrolle',
        '   8 x 2^77 = 2^80 Adressen = Größe von /48',
        '   6 ist keine Zweierpotenz: Es entstehen 2^3 = 8 Subnetze.',
        '   Die ersten 6 werden verwendet (Nr. 1 bis 6), Nr. 7 und 8',
        '   bleiben frei (Reserve).',
    ),
    'D_HANDY': (
        'RECHENWEG NACH HOSTBEDARF',
        '(VLSM, IPv4)',
        'Ausgangsnetz',
        ' 192.168.10.0/24',
        'Bedarf:',
        ' A: 50 Hosts',
        ' B: 20 Hosts',
        ' C: 10 Hosts',
        ' D: 2 Hosts',
        '',
        'SCHRITT 1: Sortieren,',
        'größter Bedarf zuerst',
        ' A: 50, B: 20, C: 10, D: 2',
        ' So liegt jedes Subnetz an',
        ' seiner Größe ausgerichtet,',
        ' es entstehen keine Lücken.',
        '',
        'SCHRITT 2: Größe je Subnetz',
        ' kleinstes h mit',
        ' 2^h - 2 >= Bedarf',
        ' A: 50 Hosts',
        '  2^5 - 2 = 30 < 50',
        '  2^6 - 2 = 62 >= 50',
        '  h = 6 -> /26 (32 - 6)',
        '  Größe 64 Adressen',
        ' B: 20 Hosts',
        '  2^4 - 2 = 14 < 20',
        '  2^5 - 2 = 30 >= 20',
        '  h = 5 -> /27 (32 - 5)',
        '  Größe 32 Adressen',
        ' C: 10 Hosts',
        '  2^3 - 2 = 6 < 10',
        '  2^4 - 2 = 14 >= 10',
        '  h = 4 -> /28 (32 - 4)',
        '  Größe 16 Adressen',
        ' D: 2 Hosts',
        '  2^2 - 2 = 2 >= 2',
        '  h = 2 -> /30 (32 - 2)',
        '  Größe 4 Adressen',
        '',
        'SCHRITT 3: Passt es?',
        ' Summe: 64 + 32 + 16 + 4',
        ' = 116 Adressen',
        ' Ausgangsnetz /24: 2^8',
        ' = 256 Adressen',
        ' 116 <= 256 -> passt',
        '',
        'SCHRITT 4: Vergabe',
        'nacheinander',
        ' Jedes Subnetz beginnt',
        ' direkt hinter dem vorigen.',
        '1. A (50 Hosts)',
        ' Netz: 192.168.10.0/26',
        ' Maske: 255.255.255.192',
        ' Erste: 192.168.10.1',
        ' Letzte: 192.168.10.62',
        ' Broadcast: 192.168.10.63',
        '2. B (20 Hosts)',
        ' Netz: 192.168.10.64/27',
        ' Maske: 255.255.255.224',
        ' Erste: 192.168.10.65',
        ' Letzte: 192.168.10.94',
        ' Broadcast: 192.168.10.95',
        '3. C (10 Hosts)',
        ' Netz: 192.168.10.96/28',
        ' Maske: 255.255.255.240',
        ' Erste: 192.168.10.97',
        ' Letzte: 192.168.10.110',
        ' Broadcast: 192.168.10.111',
        '4. D (2 Hosts)',
        ' Netz: 192.168.10.112/30',
        ' Maske: 255.255.255.252',
        ' Erste: 192.168.10.113',
        ' Letzte: 192.168.10.114',
        ' Broadcast: 192.168.10.115',
        '',
        'SCHRITT 5: Rest',
        ' frei: 192.168.10.116',
        ' bis 192.168.10.255',
        ' = 140 Adressen',
        '',
        ' als Blöcke:',
        '  192.168.10.116/30',
        '  192.168.10.120/29',
        '  192.168.10.128/25',
        '',
        'Reihenfolge der Eingabe:',
        ' A: 192.168.10.0/26',
        ' B: 192.168.10.64/27',
        ' C: 192.168.10.96/28',
        ' D: 192.168.10.112/30',
    ),
    'D_PC': (
        'RECHENWEG NACH HOSTBEDARF (VLSM, IPv4)',
        'Ausgangsnetz 192.168.10.0/24',
        'Bedarf: A: 50 Hosts, B: 20 Hosts, C: 10 Hosts, D: 2 Hosts',
        '',
        'SCHRITT 1: Nach Hostbedarf sortieren, größter Bedarf zuerst',
        '   A: 50, B: 20, C: 10, D: 2',
        '   Begründung: So beginnt jedes Subnetz an einer Grenze, die zu',
        '   seiner Größe passt, und es entstehen keine Lücken.',
        '',
        'SCHRITT 2: Größe je Subnetz (kleinstes h mit 2^h - 2 >= Bedarf)',
        '   A (50 Hosts): 2^5 - 2 = 30 < 50, 2^6 - 2 = 62 >= 50',
        '      -> h = 6, /26 (32 - 6), Maske 255.255.255.192, Größe 64',
        '   B (20 Hosts): 2^4 - 2 = 14 < 20, 2^5 - 2 = 30 >= 20',
        '      -> h = 5, /27 (32 - 5), Maske 255.255.255.224, Größe 32',
        '   C (10 Hosts): 2^3 - 2 = 6 < 10, 2^4 - 2 = 14 >= 10',
        '      -> h = 4, /28 (32 - 4), Maske 255.255.255.240, Größe 16',
        '   D (2 Hosts): 2^2 - 2 = 2 >= 2',
        '      -> h = 2, /30 (32 - 2), Maske 255.255.255.252, Größe 4',
        '',
        'SCHRITT 3: Passt es?',
        '   Summe der Größen: 64 + 32 + 16 + 4 = 116 Adressen',
        '   Ausgangsnetz /24: 2^8 = 256 Adressen -> passt',
        '',
        'SCHRITT 4: Vergabe nacheinander ab der ersten Adresse',
        '  Nr Name Netzadresse        Erster Host     Letzter Host    Broadcast',
        '  1  A    192.168.10.0/26    192.168.10.1    192.168.10.62   192.168.10.63',
        '  2  B    192.168.10.64/27   192.168.10.65   192.168.10.94   192.168.10.95',
        '  3  C    192.168.10.96/28   192.168.10.97   192.168.10.110  192.168.10.111',
        '  4  D    192.168.10.112/30  192.168.10.113  192.168.10.114  192.168.10.115',
        '',
        'SCHRITT 5: Freier Rest',
        '   192.168.10.116 bis 192.168.10.255 = 140 Adressen',
        '',
        '   als ausgerichtete Blöcke: 192.168.10.116/30, 192.168.10.120/29,',
        '   192.168.10.128/25',
        '',
        'Ergebnis in der Reihenfolge der Eingabe:',
        '   A: 192.168.10.0/26',
        '   B: 192.168.10.64/27',
        '   C: 192.168.10.96/28',
        '   D: 192.168.10.112/30',
    ),
    'E_HANDY': (
        'RECHENWEG NACH HOSTBEDARF',
        '(VLSM, IPv4)',
        'Ausgangsnetz',
        ' 192.168.10.0/24',
        'Bedarf:',
        ' A: 120 Hosts',
        ' B: 60 Hosts',
        ' C: 50 Hosts',
        ' D: 20 Hosts',
        '',
        'SCHRITT 1: Sortieren,',
        'größter Bedarf zuerst',
        ' A: 120, B: 60, C: 50, D: 20',
        ' So liegt jedes Subnetz an',
        ' seiner Größe ausgerichtet,',
        ' es entstehen keine Lücken.',
        '',
        'SCHRITT 2: Größe je Subnetz',
        ' kleinstes h mit',
        ' 2^h - 2 >= Bedarf',
        ' A: 120 Hosts',
        '  2^6 - 2 = 62 < 120',
        '  2^7 - 2 = 126 >= 120',
        '  h = 7 -> /25 (32 - 7)',
        '  Größe 128 Adressen',
        ' B: 60 Hosts',
        '  2^5 - 2 = 30 < 60',
        '  2^6 - 2 = 62 >= 60',
        '  h = 6 -> /26 (32 - 6)',
        '  Größe 64 Adressen',
        ' C: 50 Hosts',
        '  2^5 - 2 = 30 < 50',
        '  2^6 - 2 = 62 >= 50',
        '  h = 6 -> /26 (32 - 6)',
        '  Größe 64 Adressen',
        ' D: 20 Hosts',
        '  2^4 - 2 = 14 < 20',
        '  2^5 - 2 = 30 >= 20',
        '  h = 5 -> /27 (32 - 5)',
        '  Größe 32 Adressen',
        '',
        'SCHRITT 3: Passt es?',
        ' Summe: 128 + 64 + 64 + 32',
        ' = 288 Adressen',
        ' Ausgangsnetz /24: 2^8',
        ' = 256 Adressen',
        ' 288 > 256 -> passt nicht',
        ' Es fehlen 32 Adressen.',
        ' Nötig wäre mindestens ein',
        ' /23 (512 Adressen).',
        ' Nötige Größe: die nächste',
        ' Zweierpotenz ab 288 ist 2^9',
        ' = 512 Adressen, also /23',
        ' (32 - 9).',
    ),
    'E_PC': (
        'RECHENWEG NACH HOSTBEDARF (VLSM, IPv4)',
        'Ausgangsnetz 192.168.10.0/24',
        'Bedarf: A: 120 Hosts, B: 60 Hosts, C: 50 Hosts, D: 20 Hosts',
        '',
        'SCHRITT 1: Nach Hostbedarf sortieren, größter Bedarf zuerst',
        '   A: 120, B: 60, C: 50, D: 20',
        '   Begründung: So beginnt jedes Subnetz an einer Grenze, die zu',
        '   seiner Größe passt, und es entstehen keine Lücken.',
        '',
        'SCHRITT 2: Größe je Subnetz (kleinstes h mit 2^h - 2 >= Bedarf)',
        '   A (120 Hosts): 2^6 - 2 = 62 < 120, 2^7 - 2 = 126 >= 120',
        '      -> h = 7, /25 (32 - 7), Maske 255.255.255.128, Größe 128',
        '   B (60 Hosts): 2^5 - 2 = 30 < 60, 2^6 - 2 = 62 >= 60',
        '      -> h = 6, /26 (32 - 6), Maske 255.255.255.192, Größe 64',
        '   C (50 Hosts): 2^5 - 2 = 30 < 50, 2^6 - 2 = 62 >= 50',
        '      -> h = 6, /26 (32 - 6), Maske 255.255.255.192, Größe 64',
        '   D (20 Hosts): 2^4 - 2 = 14 < 20, 2^5 - 2 = 30 >= 20',
        '      -> h = 5, /27 (32 - 5), Maske 255.255.255.224, Größe 32',
        '',
        'SCHRITT 3: Passt es?',
        '   Summe der Größen: 128 + 64 + 64 + 32 = 288 Adressen',
        '   Ausgangsnetz /24: 2^8 = 256 Adressen -> passt nicht',
        '   Es fehlen 32 Adressen. Nötig wäre mindestens ein /23 (512 Adressen).',
        '   Nötige Größe: die nächste Zweierpotenz ab 288 ist 2^9 = 512 Adressen,',
        '   also /23 (32 - 9).',
    ),
    'F_HANDY': (
        'RECHENWEG NACH HOSTBEDARF',
        '(VLSM, IPv4)',
        'Ausgangsnetz',
        ' 10.0.0.0/24',
        'Bedarf:',
        ' Lager: 10 Hosts',
        ' Verwaltung: 100 Hosts',
        ' Gäste: 25 Hosts',
        ' Server: 5 Hosts',
        ' Transfer: 2 Hosts',
        '',
        'SCHRITT 1: Sortieren,',
        'größter Bedarf zuerst',
        ' Verwaltung: 100, Gäste: 25,',
        ' Lager: 10, Server: 5,',
        ' Transfer: 2',
        ' So liegt jedes Subnetz an',
        ' seiner Größe ausgerichtet,',
        ' es entstehen keine Lücken.',
        '',
        'SCHRITT 2: Größe je Subnetz',
        ' kleinstes h mit',
        ' 2^h - 2 >= Bedarf',
        ' Verwaltung: 100 Hosts',
        '  2^6 - 2 = 62 < 100',
        '  2^7 - 2 = 126 >= 100',
        '  h = 7 -> /25 (32 - 7)',
        '  Größe 128 Adressen',
        ' Gäste: 25 Hosts',
        '  2^4 - 2 = 14 < 25',
        '  2^5 - 2 = 30 >= 25',
        '  h = 5 -> /27 (32 - 5)',
        '  Größe 32 Adressen',
        ' Lager: 10 Hosts',
        '  2^3 - 2 = 6 < 10',
        '  2^4 - 2 = 14 >= 10',
        '  h = 4 -> /28 (32 - 4)',
        '  Größe 16 Adressen',
        ' Server: 5 Hosts',
        '  2^2 - 2 = 2 < 5',
        '  2^3 - 2 = 6 >= 5',
        '  h = 3 -> /29 (32 - 3)',
        '  Größe 8 Adressen',
        ' Transfer: 2 Hosts',
        '  2^2 - 2 = 2 >= 2',
        '  h = 2 -> /30 (32 - 2)',
        '  Größe 4 Adressen',
        '',
        'SCHRITT 3: Passt es?',
        ' Summe: 128 + 32 + 16 + 8',
        '  + 4',
        ' = 188 Adressen',
        ' Ausgangsnetz /24: 2^8',
        ' = 256 Adressen',
        ' 188 <= 256 -> passt',
        '',
        'SCHRITT 4: Vergabe',
        'nacheinander',
        ' Jedes Subnetz beginnt',
        ' direkt hinter dem vorigen.',
        '1. Verwaltung (100 Hosts)',
        ' Netz: 10.0.0.0/25',
        ' Maske: 255.255.255.128',
        ' Erste: 10.0.0.1',
        ' Letzte: 10.0.0.126',
        ' Broadcast: 10.0.0.127',
        '2. Gäste (25 Hosts)',
        ' Netz: 10.0.0.128/27',
        ' Maske: 255.255.255.224',
        ' Erste: 10.0.0.129',
        ' Letzte: 10.0.0.158',
        ' Broadcast: 10.0.0.159',
        '3. Lager (10 Hosts)',
        ' Netz: 10.0.0.160/28',
        ' Maske: 255.255.255.240',
        ' Erste: 10.0.0.161',
        ' Letzte: 10.0.0.174',
        ' Broadcast: 10.0.0.175',
        '4. Server (5 Hosts)',
        ' Netz: 10.0.0.176/29',
        ' Maske: 255.255.255.248',
        ' Erste: 10.0.0.177',
        ' Letzte: 10.0.0.182',
        ' Broadcast: 10.0.0.183',
        '5. Transfer (2 Hosts)',
        ' Netz: 10.0.0.184/30',
        ' Maske: 255.255.255.252',
        ' Erste: 10.0.0.185',
        ' Letzte: 10.0.0.186',
        ' Broadcast: 10.0.0.187',
        '',
        'SCHRITT 5: Rest',
        ' frei: 10.0.0.188',
        ' bis 10.0.0.255',
        ' = 68 Adressen',
        '',
        ' als Blöcke:',
        '  10.0.0.188/30',
        '  10.0.0.192/26',
        '',
        'Reihenfolge der Eingabe:',
        ' Lager: 10.0.0.160/28',
        ' Verwaltung: 10.0.0.0/25',
        ' Gäste: 10.0.0.128/27',
        ' Server: 10.0.0.176/29',
        ' Transfer: 10.0.0.184/30',
    ),
    'F_PC': (
        'RECHENWEG NACH HOSTBEDARF (VLSM, IPv4)',
        'Ausgangsnetz 10.0.0.0/24',
        'Bedarf: Lager: 10 Hosts, Verwaltung: 100 Hosts, Gäste: 25 Hosts,',
        '        Server: 5 Hosts, Transfer: 2 Hosts',
        '',
        'SCHRITT 1: Nach Hostbedarf sortieren, größter Bedarf zuerst',
        '   Verwaltung: 100, Gäste: 25, Lager: 10, Server: 5, Transfer: 2',
        '   Begründung: So beginnt jedes Subnetz an einer Grenze, die zu',
        '   seiner Größe passt, und es entstehen keine Lücken.',
        '',
        'SCHRITT 2: Größe je Subnetz (kleinstes h mit 2^h - 2 >= Bedarf)',
        '   Verwaltung (100 Hosts): 2^6 - 2 = 62 < 100, 2^7 - 2 = 126 >= 100',
        '      -> h = 7, /25 (32 - 7), Maske 255.255.255.128, Größe 128',
        '   Gäste (25 Hosts): 2^4 - 2 = 14 < 25, 2^5 - 2 = 30 >= 25',
        '      -> h = 5, /27 (32 - 5), Maske 255.255.255.224, Größe 32',
        '   Lager (10 Hosts): 2^3 - 2 = 6 < 10, 2^4 - 2 = 14 >= 10',
        '      -> h = 4, /28 (32 - 4), Maske 255.255.255.240, Größe 16',
        '   Server (5 Hosts): 2^2 - 2 = 2 < 5, 2^3 - 2 = 6 >= 5',
        '      -> h = 3, /29 (32 - 3), Maske 255.255.255.248, Größe 8',
        '   Transfer (2 Hosts): 2^2 - 2 = 2 >= 2',
        '      -> h = 2, /30 (32 - 2), Maske 255.255.255.252, Größe 4',
        '',
        'SCHRITT 3: Passt es?',
        '   Summe der Größen: 128 + 32 + 16 + 8 + 4 = 188 Adressen',
        '   Ausgangsnetz /24: 2^8 = 256 Adressen -> passt',
        '',
        'SCHRITT 4: Vergabe nacheinander ab der ersten Adresse',
        '  Nr Name       Netzadresse   Erster Host Letzter Host Broadcast',
        '  1  Verwaltung 10.0.0.0/25   10.0.0.1    10.0.0.126   10.0.0.127',
        '  2  Gäste      10.0.0.128/27 10.0.0.129  10.0.0.158   10.0.0.159',
        '  3  Lager      10.0.0.160/28 10.0.0.161  10.0.0.174   10.0.0.175',
        '  4  Server     10.0.0.176/29 10.0.0.177  10.0.0.182   10.0.0.183',
        '  5  Transfer   10.0.0.184/30 10.0.0.185  10.0.0.186   10.0.0.187',
        '',
        'SCHRITT 5: Freier Rest',
        '   10.0.0.188 bis 10.0.0.255 = 68 Adressen',
        '',
        '   als ausgerichtete Blöcke: 10.0.0.188/30, 10.0.0.192/26',
        '',
        'Ergebnis in der Reihenfolge der Eingabe:',
        '   Lager: 10.0.0.160/28',
        '   Verwaltung: 10.0.0.0/25',
        '   Gäste: 10.0.0.128/27',
        '   Server: 10.0.0.176/29',
        '   Transfer: 10.0.0.184/30',
    ),
    'G_HANDY': (
        'RECHENWEG NETZ AUFTEILEN',
        '(IPv4)',
        'Ausgangsnetz',
        ' 192.168.10.0/30',
        'gesucht: 2 gleich große',
        'Subnetze',
        '',
        'SCHRITT 1: Bits für die',
        'Subnetze',
        ' Gesucht: kleinstes k mit',
        ' 2^k >= 2',
        ' 2^0 = 1 < 2 (zu wenig)',
        ' 2^1 = 2 >= 2 -> k = 1',
        '',
        'SCHRITT 2: Neue Präfixlänge',
        ' alte Präfixlänge + k',
        ' = 30 + 1 = 31 -> /31',
        '',
        'SCHRITT 3: Maske, Hostbits,',
        'Schrittweite',
        ' /31, Oktett für Oktett:',
        ' 1. Oktett 11111111 = 255',
        ' 2. Oktett 11111111 = 255',
        ' 3. Oktett 11111111 = 255',
        ' 4. Oktett 11111110 = 254',
        ' -> Subnetzmaske:',
        '    255.255.255.254',
        ' Hostbits = 32 - 31 = 1',
        ' Adressen je Subnetz',
        ' = 2^1 = 2',
        ' Schrittweite im 4. Oktett',
        ' = 256 - 254 = 2',
        ' /31: 2 Adressen, nur für',
        ' Punkt-zu-Punkt-Verbindungen',
        ' (RFC 3021)',
        '',
        'SCHRITT 4: Subnetze',
        'auflisten',
        ' Netzadresse + Schrittweite',
        ' ergibt das nächste Subnetz.',
        'Subnetz 1: verwendet',
        ' Netz: 192.168.10.0/31',
        ' Erste: 192.168.10.0',
        ' Letzte: 192.168.10.1',
        ' Broadcast: keine',
        'Subnetz 2: verwendet',
        ' Netz: 192.168.10.2/31',
        ' Erste: 192.168.10.2',
        ' Letzte: 192.168.10.3',
        ' Broadcast: keine',
        '',
        'SCHRITT 5: Kontrolle',
        ' 2 x 2',
        ' = 4 Adressen',
        ' = Größe von /30',
        ' (2^2 = 4)',
        ' Ältere Bücher ziehen 2',
        ' Subnetze ab. Das ist',
        ' veraltet (RFC 1878).',
    ),
    'G_PC': (
        'RECHENWEG NETZ AUFTEILEN (IPv4)',
        'Ausgangsnetz 192.168.10.0/30, gesucht: 2 gleich große Subnetze',
        '',
        'SCHRITT 1: Benötigte Bits für die Subnetze',
        '   Gesucht ist das kleinste k mit 2^k >= 2.',
        '   2^0 = 1 < 2 (zu wenig)',
        '   2^1 = 2 >= 2 -> k = 1',
        '',
        'SCHRITT 2: Neue Präfixlänge',
        '   neue Präfixlänge = alte Präfixlänge + k = 30 + 1 = 31 -> /31',
        '',
        'SCHRITT 3: Subnetzmaske, Hostbits und Schrittweite',
        '   /31 = 11111111.11111111.11111111.11111110',
        '   -> Subnetzmaske: 255.255.255.254',
        '   Hostbits = 32 - 31 = 1',
        '   Adressen je Subnetz = 2^1 = 2',
        '   Schrittweite im 4. Oktett = 256 - 254 = 2',
        '   /31: 2 Adressen, nur für Punkt-zu-Punkt-Verbindungen (RFC 3021)',
        '',
        'SCHRITT 4: Subnetze auflisten',
        '   (Netzadresse + Schrittweite = nächstes Subnetz)',
        '  Nr Netzadresse        Erster Host     Letzter Host    Broadcast',
        '  1  192.168.10.0/31    192.168.10.0    192.168.10.1    keine',
        '  2  192.168.10.2/31    192.168.10.2    192.168.10.3    keine',
        '',
        'SCHRITT 5: Kontrolle',
        '   2 x 2 = 4 Adressen = Größe von /30 (2^2 = 4)',
        '   Alle 2 Subnetze werden verwendet.',
        '   Ältere Bücher ziehen 2 Subnetze ab. Das ist veraltet (RFC 1878).',
    ),
    'H_HANDY': (
        'RECHENWEG NETZ AUFTEILEN',
        '(IPv4)',
        'Ausgangsnetz',
        ' 192.168.10.0/30',
        'gesucht: 4 gleich große',
        'Subnetze',
        '',
        'SCHRITT 1: Bits für die',
        'Subnetze',
        ' Gesucht: kleinstes k mit',
        ' 2^k >= 4',
        ' 2^1 = 2 < 4 (zu wenig)',
        ' 2^2 = 4 >= 4 -> k = 2',
        '',
        'SCHRITT 2: Neue Präfixlänge',
        ' alte Präfixlänge + k',
        ' = 30 + 2 = 32 -> /32',
        '',
        'SCHRITT 3: Maske, Hostbits,',
        'Schrittweite',
        ' /32, Oktett für Oktett:',
        ' 1. Oktett 11111111 = 255',
        ' 2. Oktett 11111111 = 255',
        ' 3. Oktett 11111111 = 255',
        ' 4. Oktett 11111111 = 255',
        ' -> Subnetzmaske:',
        '    255.255.255.255',
        ' Hostbits = 32 - 32 = 0',
        ' Adressen je Subnetz',
        ' = 2^0 = 1',
        ' Schrittweite im 4. Oktett',
        ' = 256 - 255 = 1',
        ' /32: eine einzelne Adresse',
        '',
        'SCHRITT 4: Subnetze',
        'auflisten',
        ' Netzadresse + Schrittweite',
        ' ergibt das nächste Subnetz.',
        'Subnetz 1: verwendet',
        ' Netz: 192.168.10.0/32',
        ' Erste: 192.168.10.0',
        ' Letzte: 192.168.10.0',
        ' Broadcast: keine',
        'Subnetz 2: verwendet',
        ' Netz: 192.168.10.1/32',
        ' Erste: 192.168.10.1',
        ' Letzte: 192.168.10.1',
        ' Broadcast: keine',
        'Subnetz 3: verwendet',
        ' Netz: 192.168.10.2/32',
        ' Erste: 192.168.10.2',
        ' Letzte: 192.168.10.2',
        ' Broadcast: keine',
        'Subnetz 4: verwendet',
        ' Netz: 192.168.10.3/32',
        ' Erste: 192.168.10.3',
        ' Letzte: 192.168.10.3',
        ' Broadcast: keine',
        '',
        'SCHRITT 5: Kontrolle',
        ' 4 x 1',
        ' = 4 Adressen',
        ' = Größe von /30',
        ' (2^2 = 4)',
        ' Ältere Bücher ziehen 2',
        ' Subnetze ab. Das ist',
        ' veraltet (RFC 1878).',
    ),
    'H_PC': (
        'RECHENWEG NETZ AUFTEILEN (IPv4)',
        'Ausgangsnetz 192.168.10.0/30, gesucht: 4 gleich große Subnetze',
        '',
        'SCHRITT 1: Benötigte Bits für die Subnetze',
        '   Gesucht ist das kleinste k mit 2^k >= 4.',
        '   2^1 = 2 < 4 (zu wenig)',
        '   2^2 = 4 >= 4 -> k = 2',
        '',
        'SCHRITT 2: Neue Präfixlänge',
        '   neue Präfixlänge = alte Präfixlänge + k = 30 + 2 = 32 -> /32',
        '',
        'SCHRITT 3: Subnetzmaske, Hostbits und Schrittweite',
        '   /32 = 11111111.11111111.11111111.11111111',
        '   -> Subnetzmaske: 255.255.255.255',
        '   Hostbits = 32 - 32 = 0',
        '   Adressen je Subnetz = 2^0 = 1',
        '   Schrittweite im 4. Oktett = 256 - 255 = 1',
        '   /32: eine einzelne Adresse',
        '',
        'SCHRITT 4: Subnetze auflisten',
        '   (Netzadresse + Schrittweite = nächstes Subnetz)',
        '  Nr Netzadresse        Erster Host     Letzter Host    Broadcast',
        '  1  192.168.10.0/32    192.168.10.0    192.168.10.0    keine',
        '  2  192.168.10.1/32    192.168.10.1    192.168.10.1    keine',
        '  3  192.168.10.2/32    192.168.10.2    192.168.10.2    keine',
        '  4  192.168.10.3/32    192.168.10.3    192.168.10.3    keine',
        '',
        'SCHRITT 5: Kontrolle',
        '   4 x 1 = 4 Adressen = Größe von /30 (2^2 = 4)',
        '   Alle 4 Subnetze werden verwendet.',
        '   Ältere Bücher ziehen 2 Subnetze ab. Das ist veraltet (RFC 1878).',
    ),
    'I_HANDY': (
        'RECHENWEG NETZ AUFTEILEN',
        '(IPv6)',
        'Ausgangsnetz',
        ' 2001:db8::/46',
        'gesucht: 8 gleich große',
        'Subnetze',
        '',
        'SCHRITT 1: Bits für die',
        'Subnetze',
        ' Gesucht: kleinstes k mit',
        ' 2^k >= 8',
        ' 2^2 = 4 < 8 (zu wenig)',
        ' 2^3 = 8 >= 8 -> k = 3',
        '',
        'SCHRITT 2: Neue Präfixlänge',
        ' alte Präfixlänge + k',
        ' = 46 + 3 = 49 -> /49',
        ' An der nächsten',
        ' 4-Bit-Grenze (Nibble): /52',
        ' = 64 Subnetze. In der',
        ' Praxis üblich, weil dann',
        ' jede Hex-Ziffer ein Teil',
        ' der Subnetz-Nummer ist.',
        ' Gerechnet wird hier weiter',
        ' mit /49.',
        '',
        'SCHRITT 3: Wo liegt die',
        'Grenze?',
        ' /49 endet im 4. Hextett',
        ' (Bits 49 bis 64).',
        ' Davon Netzanteil:',
        ' 49 - 48 = 1 Bit',
        ' Die 3 Subnetz-Bits (Bit 47',
        ' bis 49): 2 im 3. und 1 im',
        ' 4. Hextett.',
        ' Schrittweite im 4. Hextett',
        ' = 2^(64 - 49) = 2^15',
        ' = 32.768 = hex 8000',
        ' Adressen je Subnetz:',
        ' 2^(128 - 49) = 2^79',
        ' = 604.462.909.807.314.587',
        '  .353.088',
        ' Kein Abzug von 2: IPv6',
        ' hat keine Broadcast-',
        ' Adresse.',
        ' Einzelne Adressen sind',
        ' reserviert, z. B. die',
        ' Subnet-Router-Anycast-',
        ' Adresse (alle Bits der',
        ' Schnittstellenkennung 0,',
        ' RFC 4291 2.6.1).',
        '',
        'SCHRITT 4: Subnetze',
        'auflisten',
        ' 4. Hextett um die',
        ' Schrittweite erhöhen:',
        ' Übertrag: Wird das 4.',
        ' Hextett hex 10000, steht',
        ' dort 0 und das 3. Hextett',
        ' zählt um 1 weiter.',
        ' Beispiel:',
        ' Nr. 2: 2001:db8:0:8000::',
        ' + hex 8000',
        ' = Nr. 3: 2001:db8:1::',
        'Subnetz 1: verwendet',
        ' Subnetz-Bits: 000',
        ' 4. Hextett:',
        '  0000 0000 0000 0000 = 0000',
        ' Netz: 2001:db8::/49',
        ' bis:',
        '  2001:db8:0:7fff:',
        '  ffff:ffff:ffff:ffff',
        'Subnetz 2: verwendet',
        ' Subnetz-Bits: 001',
        ' 4. Hextett:',
        '  1000 0000 0000 0000 = 8000',
        ' Netz: 2001:db8:0:8000::/49',
        ' bis:',
        '  2001:db8:0:ffff:',
        '  ffff:ffff:ffff:ffff',
        'Subnetz 3: verwendet',
        ' Subnetz-Bits: 010',
        ' 4. Hextett:',
        '  0000 0000 0000 0000 = 0000',
        ' Netz: 2001:db8:1::/49',
        ' bis:',
        '  2001:db8:1:7fff:',
        '  ffff:ffff:ffff:ffff',
        'Subnetz 4: verwendet',
        ' Subnetz-Bits: 011',
        ' 4. Hextett:',
        '  1000 0000 0000 0000 = 8000',
        ' Netz: 2001:db8:1:8000::/49',
        ' bis:',
        '  2001:db8:1:ffff:',
        '  ffff:ffff:ffff:ffff',
        'Subnetz 5: verwendet',
        ' Subnetz-Bits: 100',
        ' 4. Hextett:',
        '  0000 0000 0000 0000 = 0000',
        ' Netz: 2001:db8:2::/49',
        ' bis:',
        '  2001:db8:2:7fff:',
        '  ffff:ffff:ffff:ffff',
        'Subnetz 6: verwendet',
        ' Subnetz-Bits: 101',
        ' 4. Hextett:',
        '  1000 0000 0000 0000 = 8000',
        ' Netz: 2001:db8:2:8000::/49',
        ' bis:',
        '  2001:db8:2:ffff:',
        '  ffff:ffff:ffff:ffff',
        'Subnetz 7: verwendet',
        ' Subnetz-Bits: 110',
        ' 4. Hextett:',
        '  0000 0000 0000 0000 = 0000',
        ' Netz: 2001:db8:3::/49',
        ' bis:',
        '  2001:db8:3:7fff:',
        '  ffff:ffff:ffff:ffff',
        'Subnetz 8: verwendet',
        ' Subnetz-Bits: 111',
        ' 4. Hextett:',
        '  1000 0000 0000 0000 = 8000',
        ' Netz: 2001:db8:3:8000::/49',
        ' bis:',
        '  2001:db8:3:ffff:',
        '  ffff:ffff:ffff:ffff',
        '',
        'SCHRITT 5: Kontrolle',
        ' 8 x 2^79 = 2^82',
        ' = Größe von /46',
    ),
    'I_PC': (
        'RECHENWEG NETZ AUFTEILEN (IPv6)',
        'Ausgangsnetz 2001:db8::/46, gesucht: 8 gleich große Subnetze',
        '',
        'SCHRITT 1: Benötigte Bits für die Subnetze',
        '   Gesucht ist das kleinste k mit 2^k >= 8.',
        '   2^2 = 4 < 8 (zu wenig)',
        '   2^3 = 8 >= 8 -> k = 3',
        '',
        'SCHRITT 2: Neue Präfixlänge',
        '   neue Präfixlänge = alte Präfixlänge + k = 46 + 3 = 49 -> /49',
        '   An der nächsten 4-Bit-Grenze (Nibble): /52 = 64 Subnetze. In der Praxis',
        '   üblich, weil dann jede Hex-Ziffer ein Teil der Subnetz-Nummer ist.',
        '   Gerechnet wird hier weiter mit /49.',
        '',
        'SCHRITT 3: Wo liegt die Grenze? Schrittweite und Größe',
        '   /49 endet im 4. Hextett (Bits 49 bis 64). Davon gehören',
        '   49 - 48 = 1 Bit zum Netzanteil.',
        '   Die 3 Subnetz-Bits (Bit 47 bis 49): 2 im 3. und 1 im 4. Hextett.',
        '   Schrittweite im 4. Hextett = 2^(64 - 49) = 2^15 = 32.768 = hex 8000',
        '   Adressen je Subnetz = 2^(128 - 49) = 2^79',
        '      = 604.462.909.807.314.587.353.088',
        '   Kein Abzug von 2: IPv6 hat keine Broadcast-Adresse.',
        '   Einzelne Adressen sind reserviert, z. B. die',
        '   Subnet-Router-Anycast-Adresse (alle Bits der Schnittstellenkennung 0,',
        '   RFC 4291 2.6.1).',
        '',
        'SCHRITT 4: Subnetze auflisten (4. Hextett um die Schrittweite erhöhen)',
        '   Übertrag: Wird das 4. Hextett hex 10000, steht dort 0 und das 3. Hextett',
        '   zählt um 1 weiter.',
        '   Beispiel: Nr. 2 2001:db8:0:8000:: + hex 8000 = Nr. 3 2001:db8:1::',
        '  Nr Bits 4. Hextett binär        hex   Subnetz',
        '  1  000  0000 0000 0000 0000 = 0000  2001:db8::/49',
        '  2  001  1000 0000 0000 0000 = 8000  2001:db8:0:8000::/49',
        '  3  010  0000 0000 0000 0000 = 0000  2001:db8:1::/49',
        '  4  011  1000 0000 0000 0000 = 8000  2001:db8:1:8000::/49',
        '  5  100  0000 0000 0000 0000 = 0000  2001:db8:2::/49',
        '  6  101  1000 0000 0000 0000 = 8000  2001:db8:2:8000::/49',
        '  7  110  0000 0000 0000 0000 = 0000  2001:db8:3::/49',
        '  8  111  1000 0000 0000 0000 = 8000  2001:db8:3:8000::/49',
        '',
        '   Bereich je Subnetz: von der Netzadresse bis zur letzten Adresse,',
        '   z. B. Subnetz 1: 2001:db8:: bis',
        '                    2001:db8:0:7fff:ffff:ffff:ffff:ffff',
        '',
        'SCHRITT 5: Kontrolle',
        '   8 x 2^79 = 2^82 Adressen = Größe von /46',
    ),
    'J_HANDY': (
        'RECHENWEG NETZ AUFTEILEN',
        '(IPv4)',
        'Ausgangsnetz',
        ' 192.168.0.0/23',
        'gesucht: 4 gleich große',
        'Subnetze',
        '',
        'SCHRITT 1: Bits für die',
        'Subnetze',
        ' Gesucht: kleinstes k mit',
        ' 2^k >= 4',
        ' 2^1 = 2 < 4 (zu wenig)',
        ' 2^2 = 4 >= 4 -> k = 2',
        '',
        'SCHRITT 2: Neue Präfixlänge',
        ' alte Präfixlänge + k',
        ' = 23 + 2 = 25 -> /25',
        '',
        'SCHRITT 3: Maske, Hostbits,',
        'Schrittweite',
        ' /25, Oktett für Oktett:',
        ' 1. Oktett 11111111 = 255',
        ' 2. Oktett 11111111 = 255',
        ' 3. Oktett 11111111 = 255',
        ' 4. Oktett 10000000 = 128',
        ' -> Subnetzmaske:',
        '    255.255.255.128',
        ' Hostbits = 32 - 25 = 7',
        ' Adressen je Subnetz',
        ' = 2^7 = 128',
        ' Schrittweite im 4. Oktett',
        ' = 256 - 128 = 128',
        ' Die 2 Subnetz-Bits (Bit 24',
        ' bis 25): 1 im 3. und 1 im',
        ' 4. Oktett.',
        ' Nutzbare Hosts je Subnetz',
        ' = 2^7 - 2 = 126',
        '',
        'SCHRITT 4: Subnetze',
        'auflisten',
        ' Netzadresse + Schrittweite',
        ' ergibt das nächste Subnetz.',
        ' Übertrag: Wird das 4.',
        ' Oktett 256, steht dort 0',
        ' und das 3. Oktett zählt um',
        ' 1 weiter.',
        ' Beispiel:',
        ' Nr. 2: 192.168.0.128',
        ' + 128',
        ' = Nr. 3: 192.168.1.0',
        'Subnetz 1: verwendet',
        ' Netz: 192.168.0.0/25',
        ' Erste: 192.168.0.1',
        ' Letzte: 192.168.0.126',
        ' Broadcast: 192.168.0.127',
        'Subnetz 2: verwendet',
        ' Netz: 192.168.0.128/25',
        ' Erste: 192.168.0.129',
        ' Letzte: 192.168.0.254',
        ' Broadcast: 192.168.0.255',
        'Subnetz 3: verwendet',
        ' Netz: 192.168.1.0/25',
        ' Erste: 192.168.1.1',
        ' Letzte: 192.168.1.126',
        ' Broadcast: 192.168.1.127',
        'Subnetz 4: verwendet',
        ' Netz: 192.168.1.128/25',
        ' Erste: 192.168.1.129',
        ' Letzte: 192.168.1.254',
        ' Broadcast: 192.168.1.255',
        '',
        'SCHRITT 5: Kontrolle',
        ' 4 x 128',
        ' = 512 Adressen',
        ' = Größe von /23',
        ' (2^9 = 512)',
        ' Ältere Bücher ziehen 2',
        ' Subnetze ab. Das ist',
        ' veraltet (RFC 1878).',
    ),
    'J_PC': (
        'RECHENWEG NETZ AUFTEILEN (IPv4)',
        'Ausgangsnetz 192.168.0.0/23, gesucht: 4 gleich große Subnetze',
        '',
        'SCHRITT 1: Benötigte Bits für die Subnetze',
        '   Gesucht ist das kleinste k mit 2^k >= 4.',
        '   2^1 = 2 < 4 (zu wenig)',
        '   2^2 = 4 >= 4 -> k = 2',
        '',
        'SCHRITT 2: Neue Präfixlänge',
        '   neue Präfixlänge = alte Präfixlänge + k = 23 + 2 = 25 -> /25',
        '',
        'SCHRITT 3: Subnetzmaske, Hostbits und Schrittweite',
        '   /25 = 11111111.11111111.11111111.10000000',
        '   -> Subnetzmaske: 255.255.255.128',
        '   Hostbits = 32 - 25 = 7',
        '   Adressen je Subnetz = 2^7 = 128',
        '   Schrittweite im 4. Oktett = 256 - 128 = 128',
        '   Die 2 Subnetz-Bits (Bit 24 bis 25): 1 im 3. und 1 im 4. Oktett.',
        '   Nutzbare Hosts je Subnetz = 2^7 - 2 = 126',
        '',
        'SCHRITT 4: Subnetze auflisten',
        '   (Netzadresse + Schrittweite = nächstes Subnetz)',
        '   Übertrag: Wird das 4. Oktett 256, steht dort 0 und das 3. Oktett zählt',
        '   um 1 weiter.',
        '   Beispiel: Nr. 2 192.168.0.128 + 128 = Nr. 3 192.168.1.0',
        '  Nr Netzadresse        Erster Host     Letzter Host    Broadcast',
        '  1  192.168.0.0/25     192.168.0.1     192.168.0.126   192.168.0.127',
        '  2  192.168.0.128/25   192.168.0.129   192.168.0.254   192.168.0.255',
        '  3  192.168.1.0/25     192.168.1.1     192.168.1.126   192.168.1.127',
        '  4  192.168.1.128/25   192.168.1.129   192.168.1.254   192.168.1.255',
        '',
        'SCHRITT 5: Kontrolle',
        '   4 x 128 = 512 Adressen = Größe von /23 (2^9 = 512)',
        '   Alle 4 Subnetze werden verwendet.',
        '   Ältere Bücher ziehen 2 Subnetze ab. Das ist veraltet (RFC 1878).',
    ),
}


BEISPIELE = {"A": ("teilen", "10.20.0.0/16", 4), "B": ("teilen", "192.168.10.0/24", 6),
             "C": ("teilen", "2001:db8:abcd::/48", 6),
             "D": ("bedarf", "192.168.10.0/24", "A 50\nB 20\nC 10\nD 2"),
             "E": ("bedarf", "192.168.10.0/24", "A 120\nB 60\nC 50\nD 20"),
             "F": ("bedarf", "10.0.0.0/24",
                   "Lager 10\nVerwaltung 100\nGäste 25\nServer 5\nTransfer 2"),
             "G": ("teilen", "192.168.10.0/30", 2), "H": ("teilen", "192.168.10.0/30", 4),
             "I": ("teilen", "2001:db8::/46", 8), "J": ("teilen", "192.168.0.0/23", 4)}


def rechenweg(art, netz, wert, schmal=False):
    if art == "teilen":
        return fc.split_explain(fc.split_network(netz, wert), schmal)
    return fc.hosts_explain(fc.subnet_by_hosts(netz, wert), schmal)


def erwartet(schluessel):
    return list(ANHANG_A[schluessel])


def verbinde(text):
    """Am Handy umbrochene Werte wieder zusammensetzen: Tausenderpunkt am
    Zeilenanfang, IPv6-Adresse nach einem Doppelpunkt am Zeilenende."""
    aus = []
    for zeile in text.split("\n"):
        rest = zeile.strip()
        if aus and re.match(r"\.[0-9]{3}", rest) and re.search(r"[0-9]$", aus[-1]):
            aus[-1] += rest
        elif aus and re.search(r"(^|\s)[0-9a-f]{0,4}(:[0-9a-f]{0,4})+:$", aus[-1]) \
                and re.match(r"[0-9a-f:]+(/[0-9]+)?(?![0-9a-zA-Z])", rest):
            aus[-1] += rest
        else:
            aus.append(zeile)
    return "\n".join(aus)


V4 = re.compile(r"(?<![0-9.])([0-9]{1,3}(?:\.[0-9]{1,3}){3})(/[0-9]{1,2})?(?![0-9]|\.[0-9])")
V6 = re.compile(r"(?<![0-9a-zA-Z:])([0-9a-f]{0,4}(?::[0-9a-f]{0,4}){2,7})(/[0-9]{1,3})?")


def adressen(text, version, nur_netze=False):
    aus = []
    for treffer in (V4 if version == 4 else V6).finditer(verbinde(text)):
        adresse, praefix = treffer.group(1), treffer.group(2) or ""
        if version == 4 and any(len(t) > 1 and t[0] == "0" or int(t) > 255
                                for t in adresse.split(".")):
            continue
        if version == 6 and adresse.count(":") < 2:
            continue
        if nur_netze and not praefix:
            continue
        aus.append(adresse + praefix)
    return aus


def schritte(text):
    return re.findall(r"^SCHRITT ([0-9]+):", text, re.M)


def zufall_teilen(rng, version):
    breite = 32 if version == 4 else 128
    praefix = rng.randint(0, breite)
    netz = rng.getrandbits(breite)
    text = (eigen_v4_text(netz) if version == 4 else eigen_v6_text(netz)) + "/%d" % praefix
    grenze = 2 ** (breite - praefix)
    anzahl = rng.choice([1, min(2, grenze), min(3, grenze), rng.randint(1, min(grenze, 300)),
                         rng.randint(1, grenze), grenze])
    return text, anzahl


def zufall_bedarf(rng):
    praefix = rng.randint(0, 30)
    netz = rng.getrandbits(32)
    platz = 2 ** (32 - praefix)
    namen = ["A", "B", "Vertrieb", "Geschäftsleitung", "Lager Nord", ""]
    zeilen, belegt = [], set()
    for nummer in range(1, rng.randint(1, 12) + 1):
        name = rng.choice(namen)
        if name and name in belegt:              # Namen eindeutig (Plan 2.3.1, N-2)
            name = "%s %d" % (name[:16 - len(" %d" % nummer)], nummer)
        belegt.add(name)
        bedarf = rng.randint(1, max(1, min(platz, 2 ** 32 - 2) // rng.choice([1, 2, 4, 12])))
        # Fassung 4 (M-12): steht im Namen eine Zahl, mit Doppelpunkt trennen
        zeilen.append("%s: %d" % (name, bedarf) if name else "%d" % bedarf)
    return "%s/%d" % (eigen_v4_text(netz), praefix), "\n".join(zeilen)


class RechenwegBreiteTest(unittest.TestCase):
    """T-RW-1"""

    def pruefe(self, art, netz, wert):
        for schmal, grenze in ((True, GRENZE), (False, PC_BREITE)):
            text = rechenweg(art, netz, wert, schmal)
            for zeile in text.split("\n"):
                self.assertLessEqual(len(zeile), grenze, (art, netz, wert, schmal, zeile))
                self.assertEqual(zeile, zeile.rstrip(), (art, netz, wert, zeile))

    def test_zufall(self):
        rng = random.Random(2828)
        for _ in range(500):
            self.pruefe("teilen", *zufall_teilen(rng, 4))
            self.pruefe("teilen", *zufall_teilen(rng, 6))
            self.pruefe("bedarf", *zufall_bedarf(rng))

    def test_randfaelle(self):
        faelle = [("teilen", n, a) for n, a, *_rest in RANDFAELLE] + [
            ("teilen", "192.168.10.5/24", 3), ("teilen", "0.0.0.0/0", 2 ** 32),
            ("teilen", "::/0", 2 ** 128), ("teilen", "::/0", 2 ** 64 + 1),
            ("teilen", "ffff:ffff:ffff:ffff:ffff:ffff:ffff:ff00/120", 200),
            ("teilen", "1234:5678:9abc:def0:1234:5678:9abc:def0/64", 3),
            ("teilen", "1234:5678:9abc:def0:1234:5678:9abc:def1/127", 2),
            ("teilen", "255.255.255.255/32", 1),
            ("bedarf", "0.0.0.0/0", "Geschäftsleitung 4294967294"),
            ("bedarf", "255.255.255.0/24", "\n".join("Lager Nord %d: %d" % (i, i)
                                                      for i in range(1, 13))),
            ("bedarf", "10.0.0.0/8", "\n".join("Geschäftsleit %02d: %d" % (i, 10 ** 6 + i)
                                                for i in range(12))),     # Namen 16 Zeichen
            ("bedarf", "192.168.10.0/24", "A 200\nB 60"),
            ("bedarf", "192.168.10.0/24", "A 126\nB 62\nC 30\nD 14\nE 6\nF 2\nG 2"),
            ("bedarf", "10.0.0.0/8", "\n".join(["4294967294"] * 12)),
        ]
        for art, netz, wert in faelle:
            with self.subTest(netz=netz, wert=wert):
                self.pruefe(art, netz, wert)


class RechenwegWerteTest(unittest.TestCase):
    """T-RW-2: PC und Handy zeigen dieselben Werte in derselben Reihenfolge."""

    def pruefe(self, art, netz, wert):
        pc = rechenweg(art, netz, wert)
        handy = rechenweg(art, netz, wert, True)
        self.assertEqual(schritte(pc), schritte(handy))
        version = 6 if ":" in netz else 4
        if art == "teilen":
            r = fc.split_network(netz, wert)
            if version == 4:
                self.assertEqual(adressen(pc, 4), adressen(handy, 4))
                # die genannte Schrittweite passt zum Abstand der Subnetze
                for text in (pc, " ".join(handy.split())):
                    treffer = re.search(r"Schrittweite im ([1-4])\. Oktett\s*= 256 - "
                                        r"([0-9]+) = ([0-9]+)", text)
                    oktett, schritt = int(treffer.group(1)), int(treffer.group(3))
                    self.assertEqual(schritt * 256 ** (4 - oktett),
                                     r["groesse"] if r["neu"] else 2 ** 32, (netz, wert))
            else:
                self.assertEqual(adressen(pc, 6, True), adressen(handy, 6, True))
                ohne = {a.split("/")[0] for a in adressen(handy, 6)}
                self.assertLessEqual({a.split("/")[0] for a in adressen(pc, 6)}, ohne)
            kennwerte = ["k = %d" % r["k"], "-> /%d" % r["neu"], fc.de_int(r["groesse"]),
                         fc.de_int(r["anzahl"])]
            self.assertEqual(schritte(pc), ["1", "2", "3", "4", "5"])
        else:
            r = fc.subnet_by_hosts(netz, wert)
            self.assertEqual(adressen(pc, 4, True), adressen(handy, 4, True))
            if r["passt"]:          # passt nicht: Masken nur am PC (Schritt 2)
                self.assertEqual(sorted(adressen(pc, 4)), sorted(adressen(handy, 4)))
            kennwerte = [fc.de_int(r["summe"]), fc.de_int(r["kapazitaet"])]
            kennwerte += ["/%d" % s["praefix"] for s in r["subnetze"]]
            self.assertEqual(schritte(pc), ["1", "2", "3", "4", "5"] if r["passt"]
                             else ["1", "2", "3"])
        pc_flach, handy_flach = " ".join(verbinde(pc).split()), " ".join(verbinde(handy).split())
        for kennwert in kennwerte:
            self.assertIn(kennwert, pc_flach, (netz, wert))
            self.assertIn(kennwert, handy_flach, (netz, wert))

    def test_zufall(self):
        rng = random.Random(2929)
        for _ in range(300):
            self.pruefe("teilen", *zufall_teilen(rng, 4))
            self.pruefe("teilen", *zufall_teilen(rng, 6))
            self.pruefe("bedarf", *zufall_bedarf(rng))

    def test_beispiele(self):
        for art, netz, wert in BEISPIELE.values():
            self.pruefe(art, netz, wert)
        # die Pruefung findet die Werte wirklich (nicht leer)
        pc = rechenweg(*BEISPIELE["C"])
        self.assertEqual(len(adressen(pc, 6, True)), 9)
        handy = rechenweg(*BEISPIELE["C"], schmal=True)
        self.assertIn("2001:db8:abcd:1fff:ffff:ffff:ffff:ffff", adressen(handy, 6))
        self.assertIn("151.115.727.451.828.646.838.272", verbinde(handy))
        self.assertEqual(len(adressen(rechenweg(*BEISPIELE["B"]), 4)), 34)


class RechenwegBeispielTest(unittest.TestCase):
    """T-RW-3 (Fassung 4): Anhang A und A2, Beispiele A bis J, PC und Handy
    woertlich (20 Texte, belege/b2_rechenweg_beispiele.txt)."""

    def test_beispiele(self):
        for schluessel in sorted(ANHANG_A):
            art, netz, wert = BEISPIELE[schluessel[0]]
            with self.subTest(beispiel=schluessel):
                text = rechenweg(art, netz, wert, schluessel.endswith("HANDY"))
                self.assertEqual(text.split("\n"), erwartet(schluessel))

    def test_anhang_vollstaendig(self):
        self.assertEqual(sorted(ANHANG_A), sorted("%s_%s" % (b, f) for b in "ABCDEFGHIJ"
                                                  for f in ("PC", "HANDY")))
        self.assertEqual({k: len(v) for k, v in ANHANG_A.items()}, {   # Zeilen laut b2
            "A_PC": 31, "A_HANDY": 68, "B_PC": 37, "B_HANDY": 93, "C_PC": 45,
            "C_HANDY": 125, "D_PC": 41, "D_HANDY": 91, "E_PC": 25, "E_HANDY": 54,
            "F_PC": 45, "F_HANDY": 106, "G_PC": 29, "G_HANDY": 59, "H_PC": 31,
            "H_HANDY": 67, "I_PC": 46, "I_HANDY": 132, "J_PC": 35, "J_HANDY": 79})
        for schluessel, zeilen in ANHANG_A.items():
            grenze = GRENZE if schluessel.endswith("HANDY") else PC_BREITE
            self.assertLessEqual(max(len(z) for z in zeilen), grenze, schluessel)


class RechenwegInhaltTest(unittest.TestCase):
    """Sonderfaelle im Rechenweg."""

    def flach(self, text):
        return " ".join(verbinde(text).split())

    def test_nibble_genau_dann(self):                                   # T-K-8
        for praefix in range(0, 128, 5):
            for anzahl in (1, 2, 3, 6, 12, 17):
                if praefix + eigen_bits(anzahl) > 128:
                    continue
                neu = praefix + eigen_bits(anzahl)
                for schmal in (False, True):
                    text = self.flach(rechenweg("teilen", "::/%d" % praefix, anzahl, schmal))
                    self.assertEqual("(Nibble)" in text, neu % 4 != 0, (praefix, anzahl))
        for schmal in (False, True):
            self.assertNotIn("Nibble", rechenweg("teilen", "10.0.0.0/8", 6, schmal))

    def test_ipv4_saetze(self):
        satz = "Ältere Bücher ziehen 2 Subnetze ab. Das ist veraltet (RFC 1878)."
        for schmal in (False, True):
            self.assertIn(satz, self.flach(rechenweg("teilen", "10.0.0.0/8", 6, schmal)))
            self.assertNotIn("Ältere", rechenweg("teilen", "10.0.0.0/8", 1, schmal))
            self.assertNotIn("Ältere", rechenweg("teilen", "2001:db8::/32", 6, schmal))
            self.assertNotIn("Anycast", rechenweg("teilen", "10.0.0.0/8", 6, schmal))
            self.assertIn("Subnet-Router-Anycast-Adresse",
                          self.flach(rechenweg("teilen", "2001:db8::/32", 6, schmal))
                          .replace("Anycast- Adresse", "Anycast-Adresse"))
            self.assertNotIn("Anycast", rechenweg("teilen", "2001:db8::/126", 4, schmal))

    def test_ein_subnetz(self):
        for netz in ("10.0.0.0/8", "2001:db8::/32"):
            for schmal in (False, True):
                text = self.flach(rechenweg("teilen", netz, 1, schmal))
                self.assertIn("Keine Teilung nötig: Bei 1 Subnetz bleibt das Netz, wie es ist.",
                              text)
                self.assertIn("-> k = 0", text)
        self.assertIn("Das eine Subnetz wird verwendet.", rechenweg("teilen", "10.0.0.0/8", 1))

    def test_schrittweite_an_oktettgrenze(self):
        """Neuer Praefix genau an einer Oktettgrenze: die Grenze liegt im
        Oktett davor (/24 -> 3. Oktett, 256 - 255 = 1)."""
        faelle = [("10.0.0.0/16", 256, "Schrittweite im 3. Oktett = 256 - 255 = 1"),
                  ("10.0.0.0/8", 256, "Schrittweite im 2. Oktett = 256 - 255 = 1"),
                  ("0.0.0.0/0", 256, "Schrittweite im 1. Oktett = 256 - 255 = 1"),
                  ("192.168.10.0/24", 256, "Schrittweite im 4. Oktett = 256 - 255 = 1"),
                  ("0.0.0.0/0", 1, "Schrittweite im 1. Oktett = 256 - 0 = 256")]
        for netz, anzahl, zeile in faelle:
            for schmal in (False, True):
                self.assertIn(zeile, self.flach(rechenweg("teilen", netz, anzahl, schmal)))

    def test_31_32(self):
        for anzahl, satz in ((128, fc.SUBNET_HINT_31), (256, fc.SUBNET_HINT_32)):
            for schmal in (False, True):
                text = rechenweg("teilen", "192.168.10.0/24", anzahl, schmal)
                self.assertIn(satz, self.flach(text))
                self.assertNotIn("2^1 - 2", text)
                self.assertNotIn("2^0 - 2", text)
                self.assertIn("keine", text)

    def test_reserve_saetze(self):
        self.assertIn("Nr. 8\n   bleibt frei (Reserve).", rechenweg("teilen", "10.0.0.0/8", 7))
        self.assertIn("Nr. 6 bis 8\n   bleiben frei (Reserve).",
                      rechenweg("teilen", "10.0.0.0/8", 5))
        self.assertIn("Alle 8 Subnetze werden verwendet.", rechenweg("teilen", "10.0.0.0/8", 8))

    def test_lange_liste_gekuerzt(self):
        for netz in ("10.0.0.0/8", "2001:db8::/32"):
            for schmal in (False, True):
                text = rechenweg("teilen", netz, 17, schmal)
                self.assertIn("5 bis 30: je + Schrittweite (alle im Ergebnis)", self.flach(text))
                muster = r"^Subnetz ([0-9.]+):" if schmal else r"^  ([0-9][0-9.]*) "
                gezeigt = re.findall(muster, text, re.M)
                self.assertEqual(gezeigt, ["1", "2", "3", "4", "31", "32"], (netz, schmal))
        self.assertEqual(len(rechenweg("teilen", "10.0.0.0/8", 16, True).split(
            "Subnetz ")), 17)                                            # 16 Bloecke

    def test_hinweis_host_adresse(self):
        for schmal in (False, True):
            text = self.flach(rechenweg("teilen", "192.168.10.5/24", 6, schmal))
            self.assertIn("Hinweis: 192.168.10.5/24 ist eine Host-Adresse. Gerechnet wird "
                          "mit dem Netz 192.168.10.0/24.", text)
            text = self.flach(rechenweg("bedarf", "192.168.10.5/24", "A 5", schmal))
            self.assertIn("Gerechnet wird mit dem Netz 192.168.10.0/24.", text)

    def test_passt_nicht_und_rest_0(self):
        for schmal in (False, True):
            text = rechenweg("bedarf", "192.168.10.0/24", "A 127\nB 62\nC 30\nD 14\nE 6\nF 2",
                             schmal)
            flach = self.flach(text)
            self.assertIn("Es fehlen 124 Adressen. Nötig wäre mindestens ein /23 "
                          "(512 Adressen).",
                          flach)
            self.assertIn("passt nicht", flach)
            self.assertIn("2^9 = 512", flach)
            self.assertNotIn("SCHRITT 4", text)
            text = rechenweg("bedarf", "192.168.10.0/24",
                             "A 126\nB 62\nC 30\nD 14\nE 6\nF 2\nG 2", schmal)
            self.assertIn("Kein Rest: Das Ausgangsnetz ist genau voll.", self.flach(text))
            self.assertNotIn("Blöcke", text)
            self.assertNotIn("/31", rechenweg(*BEISPIELE["D"], schmal=schmal))   # E-63-5

    def test_laufzeit(self):
        for netz, anzahl in (("::/0", 2 ** 64), ("10.0.0.0/8", 2 ** 24), ("::/0", 2 ** 128)):
            start = time.perf_counter()
            r = fc.split_network(netz, anzahl)
            fc.split_explain(r)
            fc.split_explain(r, True)
            self.assertLess((time.perf_counter() - start) * 1000, 50, netz)
        for name in ("split_explain", "hosts_explain", "_split_explain_v4",
                     "_split_explain_v6", "_explain_head"):
            quelle = inspect.getsource(getattr(fc, name))
            for verboten in (".subnets(", ".hosts(", "ipaddress", "list(range"):
                self.assertNotIn(verboten, quelle, name)


class Z4BeispielTest(unittest.TestCase):
    """Auflage Z-4 (Freigabe Zwischenplan 0.63): Fehlerfall "passt nicht",
    VLSM mit unsortierter Eingabe, /31 bzw. /32. Werte hier unabhaengig
    nachgerechnet (eigene Ganzzahl-Rechnung); die Texte kommen als Literal
    erst mit Plan-Fassung 3."""

    def flach(self, text):
        return " ".join(verbinde(text).split())

    def test_vlsm_unsortiert(self):
        netz, bedarf = "192.168.20.0/24", [("A", 10), ("B", 60), ("C", 25), ("D", 2)]
        zeilen = "\n".join("%s %d" % e for e in bedarf)
        eigen = eigen_vergabe(eigen_v4("192.168.20.0"), 24, [b for _n, b in bedarf])
        r = fc.subnet_by_hosts(netz, zeilen)
        self.assertEqual(r["reihenfolge"], [1, 2, 0, 3])          # B, C, A, D
        for i, item in enumerate(r["subnetze"]):
            self.assertEqual((item["netz"], item["praefix"]), eigen[i])
        erwartet = {"A": "192.168.20.96/28", "B": "192.168.20.0/26",
                    "C": "192.168.20.64/27", "D": "192.168.20.112/30"}
        for i, name in enumerate("ABCD"):
            self.assertEqual("%s/%d" % (eigen_v4_text(eigen[i][0]), eigen[i][1]),
                             erwartet[name])
        for schmal in (False, True):
            weg = rechenweg("bedarf", netz, zeilen, schmal)
            netze = adressen(weg, 4, True)[1:]           # ohne Ausgangsnetz
            self.assertEqual(netze[:4], [erwartet[n] for n in "BCAD"])   # Vergabe
            self.assertEqual(netze[-4:], [erwartet[n] for n in "ABCD"])  # Eingabe
            self.assertIn("B: 60, C: 25, A: 10, D: 2", self.flach(weg))   # N-5f
            self.assertIn("140 Adressen", self.flach(weg))
        bericht = fc.hosts_report(r)
        self.assertLess(bericht.index("A (10 Hosts)"), bericht.index("B (60 Hosts)"))

    def test_passt_nicht(self):
        netz, bedarfe = "192.168.10.0/24", [127, 62, 30, 14, 6, 2]
        eigen = eigen_vergabe(eigen_v4("192.168.10.0"), 24, bedarfe)
        self.assertEqual(eigen, ("passt nicht", 124, 23))
        text = "\n".join("N%d %d" % (i, b) for i, b in enumerate(bedarfe))
        for schmal in (False, True):
            weg = self.flach(rechenweg("bedarf", netz, text, schmal))
            self.assertIn("Es fehlen 124 Adressen. Nötig wäre mindestens ein /23 "
                          "(512 Adressen).", weg)
            self.assertIn("380", weg)                    # 256+64+32+16+8+4
            self.assertIn("2^9 = 512", weg)

    def test_31_und_32(self):
        for netz, anzahl, neu, erste_zwei in (
                ("192.168.10.0/30", 2, 31, ["192.168.10.0/31", "192.168.10.2/31"]),
                ("192.168.10.0/30", 4, 32, ["192.168.10.0/32", "192.168.10.1/32"])):
            eigen = eigen_aufteilen(32, eigen_v4("192.168.10.0"), 30, anzahl)
            self.assertEqual(eigen["neu"], neu)
            self.assertEqual(["%s/%d" % (eigen_v4_text(eigen["netz"](i)), neu)
                              for i in (0, 1)], erste_zwei)
            for schmal in (False, True):
                weg = rechenweg("teilen", netz, anzahl, schmal)
                self.assertEqual(adressen(weg, 4, True)[1:3], erste_zwei)
                self.assertIn(fc.SUBNET_HINT_31 if neu == 31 else fc.SUBNET_HINT_32,
                              self.flach(weg))


class NetzdatenIPv6Test(unittest.TestCase):
    """Fester Rechenweg "Netzdaten" IPv6 (PC und Handy)."""

    def test_breite_und_werte(self):
        pc, handy = fc.CALC_EXPLAIN_SUBNET_V6, fc.CALC_EXPLAIN_SUBNET_V6_HANDY
        self.assertTrue(all(len(z) <= GRENZE for z in handy.split("\n")))
        self.assertTrue(all(len(z) <= PC_BREITE for z in pc.split("\n")))
        self.assertEqual(adressen(pc, 6), adressen(handy, 6))
        zahlen_pc = re.findall(r"[0-9][0-9.]*", verbinde(pc))
        zahlen_handy = re.findall(r"[0-9][0-9.]*", verbinde(handy))
        self.assertEqual(zahlen_pc, zahlen_handy)
        flach = " ".join(verbinde(handy).split())
        for teil in ("18.446.744.073.709.551.616", "/64", "keine Broadcast-", "RFC 5952",
                     "RFC 4291 2.5.1", "2001:db8:abcd:12::/64"):
            self.assertIn(teil, flach)
        # die Werte im Text stimmen (zweite Quelle ipaddress)
        netz = ipaddress.IPv6Network("2001:db8:abcd:12::1/64", strict=False)
        self.assertEqual("{:,}".format(netz.num_addresses).replace(",", "."),
                         "18.446.744.073.709.551.616")
        self.assertEqual(fc.ipv6_text(int(netz.network_address)), "2001:db8:abcd:12::")
        self.assertEqual(fc.ipv6_text(int(netz.broadcast_address)),
                         "2001:db8:abcd:12:ffff:ffff:ffff:ffff")
        self.assertEqual(fc.ipv6_text(eigen_v6("2001:0db8:abcd:0012:0000:0000:0000:0001")),
                         "2001:db8:abcd:12::1")
        self.assertEqual(len(re.findall(r"^ +[1-5]\. ", pc, re.M)), 5)


# ---------------------------------------------------------------------------
#  T-K-13 Eingabeform "Nach Hostbedarf" (Plan 0.63 Fassung 4, 2.3.1, Z-3)
#  Die 43 Faelle aus belege/b12_bedarf_eingabe.txt (werkzeuge/bedarf_eingabe.py)
#  mit erwarteter Liste oder Meldung woertlich: M-3 (Komma, Semikolon,
#  Schraegstrich), M-8 (doppelte Namen), M-12 (mehrere Zahlen), M-13a/b
#  (automatischer Name), Strich am Namensende, typografisches Minus, Tabulator.
# ---------------------------------------------------------------------------

M_KOMMA = ("Zeile %d: Bitte je Zeile genau ein Subnetz angeben, ohne Komma, "
           "Semikolon oder Schrägstrich (z. B. A 50).")                         # M-3
M_ZAHLEN = ("Zeile %d: Mehrere Zahlen in der Zeile. Je Zeile ein Subnetz; steht "
            "im Namen eine Zahl, bitte mit Doppelpunkt trennen (z. B. VLAN 10: 20).")  # M-12
M_DOPPELT = ("Zeile %d: Der Name „%s“ kommt schon in Zeile %d vor. "
             "Bitte jeden Namen nur einmal verwenden.")                         # M-8
M_AUTO_A = ("Zeile %d: Den Namen „%s“ hat schon Zeile %d automatisch bekommen "
            "(sie hat keinen Namen). Bitte einen anderen Namen wählen.")        # M-13a
M_AUTO_B = ("Zeile %d: Ohne Namen heißt das Subnetz automatisch „%s“, diesen Namen "
            "hat schon Zeile %d. Bitte einen Namen angeben.")                   # M-13b
M_ZAHL = "Zeile %d: Bitte die Anzahl Hosts als ganze Zahl angeben (z. B. A 50)."   # M-4
M_MIN = "Zeile %d: Der Hostbedarf muss mindestens 1 sein."                       # M-5
M_MAX = "Zeile %d: Mehr als 4.294.967.294 Hosts passen in kein IPv4-Netz."      # M-6
M_NAME = "Zeile %d: Der Name ist zu lang (höchstens 16 Zeichen)."                # M-7
M_LEER = "Bitte mindestens ein Subnetz eingeben, je Zeile Name und Hosts (z. B. A 50)."
M_ANZAHL = "Höchstens 12 Subnetze, eingegeben sind %d."                         # M-2
M_FEHLT = "Es fehlen %s Adressen. Nötig wäre mindestens ein /%d (%s Adressen)."  # M-9
M_FEHLT_ALLES = ("Es fehlen %s Adressen. Das passt in kein IPv4-Netz "
                 "(höchstens 2^32 Adressen).")                                  # M-10

B12_FAELLE = [
    ("A 50\nB 20\nC 10\nD 2", 24, [("A", 50), ("B", 20), ("C", 10), ("D", 2)]),
    ("A: 50\nB: 20\nC: 10\nD: 2", 24, [("A", 50), ("B", 20), ("C", 10), ("D", 2)]),
    ("A 50\nB 20\nC 10\n\nD 2\n", 24, [("A", 50), ("B", 20), ("C", 10), ("D", 2)]),
    ("A 50\n\nB zwanzig", 24, M_ZAHL % 3),
    ("50\n20\n10", 24, [("Netz 1", 50), ("Netz 2", 20), ("Netz 3", 10)]),
    ("Verwaltung: 100\nGäste 25 Hosts", 24, [("Verwaltung", 100), ("Gäste", 25)]),
    ("VLAN 10: 20\nVLAN 20: 30", 24, [("VLAN 10", 20), ("VLAN 20", 30)]),
    # Fassung 4 (b17 Fund 3 und 13, N-3):
    ("VLAN 10 20", 24, M_ZAHLEN % 1),
    ("A 50; B 20", 24, M_KOMMA % 1),
    ("A 50 B 20", 24, M_ZAHLEN % 1),
    ("A 1 000", 20, M_ZAHLEN % 1),
    ("A: 1 000", 20, [("A", 1000)]),
    ("1 000", 20, [("Netz 1", 1000)]),
    ("A 50.0", 24, [("A", 50)]),
    ("A 50.5", 24, M_ZAHL % 1),
    ("A 4,0", 24, M_KOMMA % 1),
    ("A: 50: 20", 24, M_ZAHLEN % 1),
    ("50\nNetz 1: 20", 24, M_AUTO_A % (2, "Netz 1", 1)),
    ("50\nNetz 1 20", 24, M_ZAHLEN % 2),
    ("Netz 2: 50\n20", 24, M_AUTO_B % (2, "Netz 2", 1)),
    ("  A :  1.000  ", 20, [("A", 1000)]),
    (": 50", 24, [("Netz 1", 50)]),
    ("", 24, M_LEER),
    (" \n  \n", 24, M_LEER),
    ("\n".join("%d" % (i + 1) for i in range(13)), 24, M_ANZAHL % 13),
    ("A 50, B 20", 24, M_KOMMA % 1),
    ("A: 1,5", 24, M_KOMMA % 1),
    ("A 50\nB 20\nC zehn", 24, M_ZAHL % 3),
    ("A 50\nB -5", 24, M_MIN % 2),
    ("A 50\nB 0", 24, M_MIN % 2),
    ("A 5.000.000.000", 8, M_MAX % 1),
    ("Buchhaltung-Nord-2 30", 24, M_NAME % 1),
    ("A 50\nB 20\na 10", 24, M_DOPPELT % (3, "a", 1)),
    ("A 120\nB 60\nC 50\nD 20", 24, M_FEHLT % ("32", 23, "512")),
    ("A 3.000.000.000\nB 3.000.000.000", 8, M_FEHLT_ALLES % "8.573.157.376"),
    # Fassung 4, Lehrbuch-Gegenpruefung Z-10 (Fund 1, 8, 9; N-4):
    ("A 50\tB 20", 24, M_ZAHLEN % 1),
    ("A 50 / B 20", 24, M_KOMMA % 1),
    ("A 50/B 20", 24, M_KOMMA % 1),
    ("A - 50", 24, [("A", 50)]),
    ("A – 50", 24, [("A", 50)]),
    ("A 50\nB −5", 24, M_MIN % 2),
    ("Filiale1 500\nWAN1 2", 22, [("Filiale1", 500), ("WAN1", 2)]),
    ("A\t50", 24, [("A", 50)]),
]


def bedarf_ergebnis(eingabe, praefix):
    """Wie werkzeuge/bedarf_eingabe.py: Liste oder die (erste) Meldung."""
    try:
        r = fc.subnet_by_hosts("10.0.0.0/%d" % praefix, eingabe)
    except fc.InputError as fehler:
        return str(fehler)
    return r["meldung"] or r["bedarfe"]


class EingabeformTest(unittest.TestCase):
    """T-K-13: Eingabeform "Nach Hostbedarf" nach Plan 0.63 Abschnitt 2.3.1."""

    def beide(self, text, erwartet):
        self.assertEqual(meldung(lambda: fc.read_host_lines(text)), erwartet)
        self.assertEqual(meldung(lambda: fc.subnet_by_hosts("10.0.0.0/8", text)), erwartet)

    def test_b12_faelle(self):
        self.assertEqual(len(B12_FAELLE), 43)
        for eingabe, praefix, erwartet in B12_FAELLE:
            with self.subTest(eingabe=eingabe):
                self.assertEqual(bedarf_ergebnis(eingabe, praefix), erwartet)

    def test_komma_semikolon_schraegstrich(self):                    # M-3 (N-3a, N-4a)
        for text, zeile in (("A 50, B 20", 1), ("A 50,B 20", 1), ("A: 1,5", 1),
                            ("A 50\nB 20, C 10", 2), ("A 50\n\nB,C 10", 3), ("A 4,0", 1),
                            ("A, 50", 1), ("50,", 1), (",", 1), ("A 50\nB 20 Hosts,", 2),
                            ("A 50; B 20", 1), ("A 50;", 1), ("A 50\nB: 20;", 2),
                            ("A 50 / B 20", 1), ("A 50/B 20", 1), ("A/B 50", 1),
                            ("A 50\nB 20 /", 2), ("192.168.1.0/26 50", 1)):
            with self.subTest(text=text):
                self.beide(text, M_KOMMA % zeile)

    def test_mehrere_zahlen(self):                                   # M-12 (N-3b/c, N-4a)
        for text, zeile in (("VLAN 10 20", 1), ("A 50 B 20", 1), ("A 1 000", 1),
                            ("A: 50: 20", 1), ("A 50\tB 20", 1), ("A\t50\tB\t20", 1),
                            ("50\nNetz 1 20", 2), ("Netz 2 50", 1), ("A 50\n10 20", 2),
                            ("A 50\nB 2 Hosts 3", 2), ("A::50", 1), ("A 1.000 B 20", 1)):
            with self.subTest(text=text):
                self.beide(text, M_ZAHLEN % zeile)

    def test_reihenfolge(self):
        # erste Meldung von oben; Anzahl und "leer" kommen vorher; in der
        # Zeile zuerst M-3, dann M-12, dann die Zahl (Plan 2.3.1)
        self.beide("A zehn\nB 1,5", M_ZAHL % 1)
        self.beide("A 1,5\nB zehn", M_KOMMA % 1)
        self.beide("Buchhaltung-Nord-2, 30", M_KOMMA % 1)
        self.beide("A: 1: 2,5", M_KOMMA % 1)
        self.beide("A 1 zehn", M_ZAHLEN % 1)
        self.beide("VLAN 10 0", M_ZAHLEN % 1)
        self.beide("\n".join("N%d 1,5" % i for i in range(13)), M_ANZAHL % 13)

    def test_doppelte_namen(self):                                   # M-8 (N-2)
        for text, erwartet in (
                ("A 50\nB 20\na 10", M_DOPPELT % (3, "a", 1)),
                ("A 50\nA 20", M_DOPPELT % (2, "A", 1)),
                ("A 50\n\nB 20\nb: 5 Hosts", M_DOPPELT % (4, "b", 3)),
                ("VLAN 10: 20\nvlan 10: 30", M_DOPPELT % (2, "vlan 10", 1)),
                ("Gäste 5\nGÄSTE 6", M_DOPPELT % (2, "GÄSTE", 1)),
                ("A 50\nA - 20", M_DOPPELT % (2, "A", 1)),
                ("A 50\nB 20\nA 0", M_MIN % 3)):
            with self.subTest(text=text):
                self.beide(text, erwartet)

    def test_automatische_namen(self):                               # M-13a/b (N-4b)
        for text, erwartet in (
                ("50\nNetz 1: 20", M_AUTO_A % (2, "Netz 1", 1)),
                ("50\n\nnetz 1: 20", M_AUTO_A % (3, "netz 1", 1)),
                ("A 5\n50\nNetz 2: 20", M_AUTO_A % (3, "Netz 2", 2)),
                ("Netz 2: 50\n20", M_AUTO_B % (2, "Netz 2", 1)),
                ("NETZ 3: 5\n6\n7", M_AUTO_B % (3, "Netz 3", 1)),
                ("Netz 1: 50\nNetz 1: 20", M_DOPPELT % (2, "Netz 1", 1))):
            with self.subTest(text=text):
                self.beide(text, erwartet)
        self.assertEqual(fc.read_host_lines("Netz 1: 50\n20"), [("Netz 1", 50), ("Netz 2", 20)])
        self.assertEqual(fc.read_host_lines("50\nNetz 3: 20"), [("Netz 1", 50), ("Netz 3", 20)])

    def test_strich_minus_tabulator(self):                           # N-4d, Tab
        self.assertEqual(fc.read_host_lines("A - 50\nB – 20\nC: 10\nD -  2"),
                         [("A", 50), ("B", 20), ("C", 10), ("D", 2)])
        self.assertEqual(fc.read_host_lines("Lager-Nord - 30\nA-B 5"),
                         [("Lager-Nord", 30), ("A-B", 5)])
        self.assertEqual(fc.read_host_lines("A\t50\nB\t20 Hosts\nC:\t10"),
                         [("A", 50), ("B", 20), ("C", 10)])
        for text, zeile in (("A 50\nB −5", 2), ("B −5", 1), ("−5", 1),
                            ("B: −5", 1), ("B -5", 1), ("B: -5", 1), ("-0", 1)):
            with self.subTest(text=text):
                self.beide(text, M_MIN % zeile)

    def test_erlaubt_bleibt(self):
        self.assertEqual(fc.read_host_lines("A 50\nAB 20\nA B 10\nB A 5\n7\n8"),
                         [("A", 50), ("AB", 20), ("A B", 10), ("B A", 5),
                          ("Netz 5", 7), ("Netz 6", 8)])
        self.assertEqual(fc.read_host_lines("VLAN 10: 20\nVLAN 20: 30"),
                         [("VLAN 10", 20), ("VLAN 20", 30)])
        self.assertEqual(fc.read_host_lines("A 1.000\nB 2.000.000\nC: 1 000\n2 000"),
                         [("A", 1000), ("B", 2000000), ("C", 1000), ("Netz 4", 2000)])
        self.assertEqual(fc.read_host_lines("Filiale1 500\nWAN1 2\nA 50.0\nB: 7 Hosts"),
                         [("Filiale1", 500), ("WAN1", 2), ("A", 50), ("B", 7)])

    def test_laengste_meldung(self):
        laengste = max(len(e) for _e, _p, e in B12_FAELLE if isinstance(e, str))
        self.assertEqual(laengste, 136)                         # Plan 2.3.1, b12


# ---------------------------------------------------------------------------
#  T-RW-4 (Plan 0.63 Fassung 4, Z-10 Fund 2, 3 und 7): Grenz-Hextett und
#  Schrittweite gegen eigene Ganzzahl-Rechnung (nicht gegen r), Lage der
#  Subnetz-Bits und Uebertrag genau dann, wenn die Bits ueber eine Oktett-
#  bzw. Hextett-Grenze reichen, /64-Hinweis genau dann, wenn p > 64.
# ---------------------------------------------------------------------------

def eigen_de(zahl):
    """Tausenderpunkte, eigene Rechnung."""
    ziffern, gruppen = str(zahl), []
    while len(ziffern) > 3:
        gruppen.insert(0, ziffern[-3:])
        ziffern = ziffern[:-3]
    return ".".join([ziffern] + gruppen)


def eigen_einheit(praefix, einheit):
    """Nr. des Oktetts (einheit 8) bzw. Hextetts (16), in dem die Grenze des
    Praefixes liegt (Bit Nr. praefix; bei /0 die erste Einheit)."""
    nr = 1
    while nr * einheit < praefix:
        nr += 1
    return nr


def eigen_lage(alt, neu, einheit):
    """Subnetz-Bits alt+1 bis neu, Bit fuer Bit gezaehlt:
    [(Anzahl Bits, Nr. der Einheit)]."""
    teile = []
    for bit in range(alt + 1, neu + 1):
        nr = eigen_einheit(bit, einheit)
        if teile and teile[-1][1] == nr:
            teile[-1][0] += 1
        else:
            teile.append([1, nr])
    return [tuple(teil) for teil in teile]


def eigen_grenzsaetze(version, netz, alt, neu):
    """Erwartete Saetze (flach) zu Lage und Uebertrag, oder None."""
    einheit, wort = (8, "Oktett") if version == 4 else (16, "Hextett")
    teile = eigen_lage(alt, neu, einheit)
    if len(teile) < 2:
        return None
    breite = 32 if version == 4 else 128
    groesse = 2 ** (breite - neu)
    nr_grenze = teile[-1][1]
    schritt = 2 ** (einheit * nr_grenze - neu)
    schritt_text = "%d" % schritt if version == 4 else "hex %x" % schritt
    liste = ["%d im %d." % teil for teil in teile]
    lage = "Die %d Subnetz-Bits (Bit %d bis %d): %s und %s %s." % (
        neu - alt, alt + 1, neu, ", ".join(liste[:-1]), liste[-1], wort)
    ueber = "Übertrag: Wird das %d. %s %s, steht dort 0 und das %d. %s zählt um 1 weiter." % (
        nr_grenze, wort, "256" if version == 4 else "hex 10000", nr_grenze - 1, wort)
    nr = 2 ** teile[-1][0]
    text = eigen_v4_text if version == 4 else eigen_v6_text
    vorher, nachher = text(netz + (nr - 1) * groesse), text(netz + nr * groesse)
    pc = "Beispiel: Nr. %s %s + %s = Nr. %s %s" % (eigen_de(nr), vorher, schritt_text,
                                                  eigen_de(nr + 1), nachher)
    handy = "Beispiel: Nr. %s: %s + %s = Nr. %s: %s" % (eigen_de(nr), vorher, schritt_text,
                                                      eigen_de(nr + 1), nachher)
    return lage, ueber, pc, handy


HINWEIS_64_PC = ["   Hinweis: /66 ist länger als /64. Ein LAN bekommt in der Regel ein /64,",
                 "   sonst geht die automatische Adressvergabe (SLAAC) nicht."]
HINWEIS_64_HANDY = [" Hinweis: /66 ist länger als", " /64. Ein LAN bekommt in der",
                    " Regel ein /64, sonst geht", " die automatische",
                    " Adressvergabe (SLAAC)", " nicht."]


class RechenwegGrenzeTest(unittest.TestCase):
    """T-RW-4"""

    def flach(self, text):
        return " ".join(verbinde(text).split())

    def test_grenz_hextett_alle_praefixe(self):
        for neu in range(1, 129):
            hextett = eigen_einheit(neu, 16)
            schritt = 2 ** (16 * hextett - neu)
            for alt in sorted({neu - 1, max(0, neu - 5), max(0, neu - 17)}):
                with self.subTest(neu=neu, alt=alt):
                    r = fc.split_network("::/%d" % alt, 2 ** (neu - alt))
                    pc = rechenweg("teilen", "::/%d" % alt, 2 ** (neu - alt))
                    handy = self.flach(rechenweg("teilen", "::/%d" % alt, 2 ** (neu - alt),
                                                 True))
                    lage = "/%d endet im %d. Hextett (Bits %d bis %d)" % (
                        neu, hextett, 16 * hextett - 15, 16 * hextett)
                    weite = "Schrittweite im %d. Hextett = 2^(%d - %d) = 2^%d = %s = hex %x" % (
                        hextett, 16 * hextett, neu, 16 * hextett - neu, eigen_de(schritt),
                        schritt)
                    for text in (self.flach(pc), handy):
                        self.assertIn(lage, text)
                        self.assertIn(weite, text)
                        self.assertIn("SCHRITT 4: Subnetze auflisten (%d. Hextett" % hextett
                                      if text is not handy else
                                      "%d. Hextett um die Schrittweite erhöhen" % hextett, text)
                    # Schrittweite passt zum Abstand der Subnetze (eigene Rechnung)
                    self.assertEqual(schritt * 2 ** (128 - 16 * hextett), 2 ** (128 - neu))
                    self.assertEqual(r["groesse"], 2 ** (128 - neu))

    def test_48_auf_64(self):
        for schmal in (False, True):
            text = self.flach(rechenweg("teilen", "2001:db8:abcd::/48", 65536, schmal))
            self.assertIn("/64 endet im 4. Hextett (Bits 49 bis 64)", text)
            self.assertIn("= 2^0 = 1 = hex 1", text)
            self.assertIn("64 - 48 = 16 Bits", text)
            self.assertNotIn("Übertrag", text)
            self.assertNotIn("Subnetz-Bits (Bit", text)
            self.assertNotIn("länger als /64", text)
            self.assertNotIn("5. Hextett", text)
            self.assertNotIn("10000", text)

    def test_lage_und_uebertrag_genau_dann(self):
        rng = random.Random(4646)
        faelle = []
        for alt in range(0, 32):
            for neu in range(alt + 1, min(32, alt + 12) + 1):
                faelle.append((4, rng.getrandbits(32), alt, neu))
        for alt in range(0, 128):
            for neu in range(alt + 1, min(128, alt + 20) + 1):
                faelle.append((6, rng.getrandbits(128), alt, neu))
        gesehen = 0
        for version, zufall, alt, neu in faelle:
            breite = 32 if version == 4 else 128
            netz = zufall >> (breite - alt) << (breite - alt) if alt else 0
            netztext = (eigen_v4_text(netz) if version == 4 else eigen_v6_text(netz)) + \
                "/%d" % alt
            anzahl = 2 ** (neu - alt)
            erwartet_saetze = eigen_grenzsaetze(version, netz, alt, neu)
            pc = self.flach(rechenweg("teilen", netztext, anzahl))
            handy = self.flach(rechenweg("teilen", netztext, anzahl, True))
            for text, schmal in ((pc, False), (handy, True)):
                with self.subTest(netz=netztext, neu=neu, schmal=schmal):
                    self.assertEqual("Übertrag:" in text, erwartet_saetze is not None)
                    self.assertEqual("Subnetz-Bits (Bit" in text, erwartet_saetze is not None)
                    if erwartet_saetze:
                        lage, ueber, bsp_pc, bsp_handy = erwartet_saetze
                        self.assertEqual(text.count(lage), 1)
                        self.assertEqual(text.count(ueber), 1)
                        self.assertEqual(text.count(bsp_handy if schmal else bsp_pc), 1)
                        # Lage in Schritt 3, Uebertrag in Schritt 4
                        self.assertLess(text.index("SCHRITT 3"), text.index(lage))
                        self.assertLess(text.index(lage), text.index("SCHRITT 4"))
                        self.assertLess(text.index("SCHRITT 4"), text.index(ueber))
                        self.assertLess(text.index(ueber), text.index("SCHRITT 5"))
                        gesehen += 1
        self.assertGreater(gesehen, 2000)

    def test_saetze_woertlich_b21(self):
        """Wortlaut PC und Handy aus belege/b21_z10_zeilen.txt (Plan S.10)."""
        pc = rechenweg("teilen", "2001:db8::/40", 4096).split("\n")
        for zeile in ("   Die 12 Subnetz-Bits (Bit 41 bis 52): 8 im 3. und 4 im 4. Hextett.",
                      "   Übertrag: Wird das 4. Hextett hex 10000, steht dort 0 und das 3. "
                      "Hextett",
                      "   zählt um 1 weiter.",
                      "   Beispiel: Nr. 16 2001:db8:0:f000:: + hex 1000 = Nr. 17 "
                      "2001:db8:1::"):
            self.assertIn(zeile, pc)
        handy = rechenweg("teilen", "192.168.0.0/16", 1000, True)
        self.assertIn("\n".join([" Die 10 Subnetz-Bits (Bit 17", " bis 26): 8 im 3. und 2 im",
                                 " 4. Oktett."]), handy)
        self.assertIn("\n".join([" Übertrag: Wird das 4.", " Oktett 256, steht dort 0",
                                 " und das 3. Oktett zählt um", " 1 weiter.", " Beispiel:",
                                 " Nr. 4: 192.168.0.192", " + 64",
                                 " = Nr. 5: 192.168.1.0"]), handy)
        pc = rechenweg("teilen", "10.0.0.0/8", 1000)
        self.assertIn("   Beispiel: Nr. 4 10.0.192.0 + 64 = Nr. 5 10.1.0.0", pc.split("\n"))

    def test_hinweis_64_genau_dann(self):
        for neu in range(1, 129):
            alt = max(0, neu - 3)
            for schmal in (False, True):
                text = self.flach(rechenweg("teilen", "::/%d" % alt, 2 ** (neu - alt), schmal))
                satz = ("Hinweis: /%d ist länger als /64. Ein LAN bekommt in der Regel ein "
                        "/64, sonst geht die automatische Adressvergabe (SLAAC) nicht." % neu)
                self.assertEqual(satz in text, neu > 64, (neu, schmal))
                self.assertEqual("länger als /64" in text, neu > 64, (neu, schmal))
                if neu > 64:     # am Ende von Schritt 2
                    self.assertLess(text.index("SCHRITT 2"), text.index(satz))
                    self.assertLess(text.index(satz), text.index("SCHRITT 3"))
        for schmal in (False, True):
            self.assertNotIn("/64", rechenweg("teilen", "10.0.0.0/8", 2 ** 24, schmal))
        for schmal, zeilen in ((False, HINWEIS_64_PC), (True, HINWEIS_64_HANDY)):
            text = rechenweg("teilen", "2001:db8:abcd:12::/64", 4, schmal).split("\n")
            start = text.index(zeilen[0])
            self.assertEqual(text[start:start + len(zeilen)], zeilen)
            self.assertEqual(text[start + len(zeilen)], "")
            self.assertTrue(text[start + len(zeilen) + 1].startswith("SCHRITT 3"))

    def test_kennwerte_zufall(self):
        """Kennwerte der Rechenwege (k, Praefix, Oktett bzw. Hextett,
        Schrittweite, Maske) gegen die eigen_*-Rechnung dieser Datei."""
        rng = random.Random(6464)
        for _ in range(400):
            for version in (4, 6):
                netz, anzahl = zufall_teilen(rng, version)
                alt = int(netz.split("/")[1])
                k = eigen_bits(anzahl)
                neu = alt + k
                for schmal in (False, True):
                    text = self.flach(rechenweg("teilen", netz, anzahl, schmal))
                    with self.subTest(netz=netz, anzahl=anzahl, schmal=schmal):
                        self.assertIn("-> k = %d" % k, text)
                        self.assertIn("= %d + %d = %d -> /%d" % (alt, k, neu, neu), text)
                        if version == 4:
                            oktett = eigen_einheit(neu, 8)
                            schritt = 2 ** (8 * oktett - neu)
                            maske = (2 ** 32 - 1) ^ (2 ** (32 - neu) - 1)
                            self.assertIn("Schrittweite im %d. Oktett = 256 - %d = %d" % (
                                oktett, 256 - schritt, schritt), text)
                            self.assertIn("-> Subnetzmaske: %s" % eigen_v4_text(maske), text)
                        else:
                            hextett = eigen_einheit(neu, 16)
                            schritt = 2 ** (16 * hextett - neu)
                            self.assertIn("/%d endet im %d. Hextett" % (neu, hextett), text)
                            self.assertIn("= %s = hex %x" % (eigen_de(schritt), schritt), text)


# ---------------------------------------------------------------------------
#  Fassung 4 (Z-10 Fund 4, 5, 6, 8, 10): Spaltenkoepfe, Einzahl, Fehlbetrag,
#  Name und Zahl mit Doppelpunkt, "Groesse" bei einem Subnetz
# ---------------------------------------------------------------------------

class Fassung4WortlautTest(unittest.TestCase):

    def test_erster_letzter_host(self):                              # N-5b
        for text in (fc.split_report(fc.split_network("192.168.10.0/24", 4)),
                     rechenweg("teilen", "192.168.10.0/24", 4),
                     rechenweg("bedarf", "192.168.10.0/24", "A 50")):
            self.assertRegex(text, r"Erster Host +Letzter Host +Broadcast")
            self.assertNotIn("Erste Host", text)
            self.assertNotIn("Letzte Host", text)
        for text in (fc.split_report(fc.split_network("192.168.10.0/24", 4), schmal=True),
                     rechenweg("teilen", "192.168.10.0/24", 4, True)):
            self.assertIn(" Erste: 192.168.10.1", text.split("\n"))
            self.assertIn(" Letzte: 192.168.10.62", text.split("\n"))

    def test_einzahl(self):                                          # N-5c
        for netz in ("10.0.0.0/8", "2001:db8::/32"):
            pc = rechenweg("teilen", netz, 1).split("\n")
            self.assertEqual(pc[1], "Ausgangsnetz %s, gesucht: 1 Subnetz" % netz)
            handy = rechenweg("teilen", netz, 1, True).split("\n")
            stelle = handy.index("gesucht: 1 Subnetz")
            self.assertEqual(handy[stelle + 1], "")
            self.assertIn("Gesucht               : 1 Subnetz",
                          fc.split_report(fc.split_network(netz, 1)).split("\n"))
        self.assertIn("Ausgangsnetz 10.0.0.0/8, gesucht: 2 gleich große Subnetze",
                      rechenweg("teilen", "10.0.0.0/8", 2))
        pc = rechenweg("bedarf", "192.168.10.0/24", "A 1\nB 2").split("\n")
        self.assertIn("Bedarf: A: 1 Host, B: 2 Hosts", pc)
        self.assertIn("   A (1 Host): 2^2 - 2 = 2 >= 1", pc)
        self.assertIn("   B (2 Hosts): 2^2 - 2 = 2 >= 2", pc)
        handy = rechenweg("bedarf", "192.168.10.0/24", "A 1\nB 2", True).split("\n")
        self.assertIn(" A: 1 Host", handy)
        self.assertIn("2. A (1 Host)", handy)
        self.assertIn("1. B (2 Hosts)", handy)
        for schmal in (False, True):
            r = fc.subnet_by_hosts("192.168.10.0/24", "A 1\nB 2")
            for text in (rechenweg("bedarf", "192.168.10.0/24", "A 1\nB 2", schmal),
                         fc.hosts_report(r, schmal)):
                self.assertNotIn("1 Hosts", text)
                self.assertIn("A (1 Host)" if text.count("(") else "A: 1 Host", text)
        self.assertIn("1 Bit zum Netzanteil", " ".join(rechenweg("teilen", "::/48", 2).split()))

    def test_groesse_bei_einem_subnetz(self):                        # N-5g
        pc = rechenweg("bedarf", "192.168.10.0/24", "A 2").split("\n")
        self.assertIn("   Größe: 4 Adressen", pc)
        self.assertFalse(any("Summe" in zeile for zeile in pc))
        handy = rechenweg("bedarf", "192.168.10.0/24", "A 2", True).split("\n")
        stelle = handy.index(" Größe:")
        self.assertEqual(handy[stelle + 1], " = 4 Adressen")
        self.assertFalse(any("Summe" in zeile for zeile in handy))
        self.assertIn("   Summe der Größen: 4 + 4 = 8 Adressen",
                      rechenweg("bedarf", "192.168.10.0/24", "A 2\nB 2").split("\n"))

    def test_bedarf_mit_doppelpunkt(self):                           # N-5f
        pc = rechenweg("bedarf", "192.168.10.0/24", "50\n20").split("\n")
        self.assertIn("Bedarf: Netz 1: 50 Hosts, Netz 2: 20 Hosts", pc)
        self.assertIn("   Netz 1: 50, Netz 2: 20", pc)
        handy = rechenweg("bedarf", "192.168.10.0/24", "50\n20", True).split("\n")
        self.assertIn(" Netz 1: 50, Netz 2: 20", handy)

    def test_fehlbetrag(self):                                       # N-4c, N-5d
        r = fc.subnet_by_hosts(*BEISPIELE["E"][1:])
        self.assertEqual(r["meldung"],
                         "Es fehlen 32 Adressen. Nötig wäre mindestens ein /23 (512 Adressen).")
        self.assertEqual(fc.hosts_report(r).split("\n"), [
            "Ausgangsnetz: 192.168.10.0/24", "Benötigt: 288 Adressen, vorhanden: 256", "",
            "Es fehlen 32 Adressen. Nötig wäre mindestens ein /23 (512 Adressen)."])
        r = fc.subnet_by_hosts("0.0.0.0/1", "A 4294967294")
        self.assertEqual(r["meldung"], "Es fehlen 2.147.483.648 Adressen. Nötig wäre "
                                       "mindestens ein /0 (4.294.967.296 Adressen).")


# ---------------------------------------------------------------------------
#  T-TR-1 bis T-TR-3 (0.63.1, Plan 0.63 Abschnitt 4.5, Auflage Z-9): die zwei
#  neuen Trainer-Arten "Netz aufteilen" und "Nach Hostbedarf". Je Art und
#  Stufe 200 Startwerte; die Loesung wird aus dem Aufgabentext mit der
#  eigenen Rechnung dieser Datei nachgerechnet (dazu ipaddress bzw. die
#  Freiliste als zweite Quelle).
# ---------------------------------------------------------------------------

import fisi_lernen as fl          # noqa: E402

sys.path.insert(1, os.path.join(CODE, "pruefung"))
import rechenweg_texte as rt      # noqa: E402

TR_STARTWERTE = 200
TR_TEILEN = re.compile(r"Das Netz (\S+)/(\d+) soll in ([0-9.]+) gleich große Subnetze "
                       r"(an Nibble-Grenzen \(4-Bit-Grenzen\) )?aufgeteilt werden\. "
                       r"Geben Sie an: (.*)\.$")
TR_BEDARF = re.compile(r"Das Netz (\S+)/(\d+) soll nach Hostbedarf aufgeteilt werden: "
                       r"(.*)\. Vergeben wird lückenlos ab der ersten Adresse, das größte "
                       r"Subnetz zuerst\. Geben Sie je Subnetz Netzadresse/Präfix und "
                       r"Subnetzmaske an, dazu die Broadcast-Adresse des (\d+)\. vergebenen "
                       r"Subnetzes und den freien Rest in Adressen\.$")


def tr_aufgaben(art):
    for stufe in (1, 2, 3):
        for wert in range(TR_STARTWERTE):
            yield stufe, fl.trainer_task(art, stufe, "tr-%d" % wert)


def tr_privat(wert, praefix):
    """Netz liegt in 10/8, 172.16/12 oder 192.168/16."""
    for netz, laenge in ((10 << 24, 8), ((172 << 24) | (16 << 16), 12),
                         ((192 << 24) | (168 << 16), 16)):
        if praefix >= laenge and wert >> (32 - laenge) == netz >> (32 - laenge):
            return True
    return False


def tr_ohne_leer(zeilen):
    return "".join("".join(zeilen).split())


def tr_einzeln(test, task, falsch):
    """Jede Teilantwort einzeln: Musterloesung passt; nur dieses Feld falsch
    -> nur dieses Feld wird abgelehnt."""
    test.assertTrue(task.all_correct(task.solution), task.text)
    for key, _label in task.fields:
        antworten = dict(task.solution)
        antworten[key] = falsch[key]
        ergebnis = task.check(antworten)
        test.assertFalse(ergebnis[key], (task.text, key, falsch[key]))
        test.assertTrue(all(ok for k, ok in ergebnis.items() if k != key), (task.text, key))


def tr_teilen_lesen(task):
    treffer = TR_TEILEN.match(task.text)
    assert treffer, task.text
    adresse, praefix, anzahl, nibble, _gefragt = treffer.groups()
    version = 6 if ":" in adresse else 4
    breite = 32 if version == 4 else 128
    netz = eigen_v4(adresse) if version == 4 else eigen_v6(adresse)
    praefix, anzahl = int(praefix), int(anzahl.replace(".", ""))
    nr = int(re.search(r"des (\d+)\. Subnetzes\.$", task.text).group(1))
    k = eigen_bits(anzahl)
    neu = praefix + k
    if nibble:
        while neu % 4:
            neu += 1
    groesse = 2 ** (breite - neu)
    start = netz + (nr - 1) * groesse
    return {"version": version, "breite": breite, "netz": netz, "praefix": praefix,
            "anzahl": anzahl, "nibble": bool(nibble), "nr": nr, "k": k, "neu": neu,
            "groesse": groesse, "start": start, "ende": start + groesse - 1}


class TrainerTeilenTest(unittest.TestCase):
    """T-TR-1 "Netz aufteilen": 3 Stufen x 200 Startwerte."""

    def test_tr1_stufen_und_loesung_gegen_eigene_rechnung(self):
        zaehler = {"v6": 0, "nibble": 0, "stufe3": 0}
        for stufe, task in tr_aufgaben("teilen"):
            e = tr_teilen_lesen(task)
            self.assertEqual(task.kind, "teilen")
            self.assertEqual(task.level, stufe)
            self.assertTrue(2 <= e["nr"] <= e["anzahl"], task.text)
            self.assertEqual(e["netz"] % 2 ** (e["breite"] - e["praefix"]), 0, task.text)
            if stufe == 1:
                self.assertEqual((e["version"], e["praefix"]), (4, 24), task.text)
                self.assertTrue(2 <= e["anzahl"] <= 8, task.text)
            elif stufe == 2:
                self.assertEqual(e["version"], 4, task.text)
                self.assertTrue(16 <= e["praefix"] <= 23 and 2 <= e["anzahl"] <= 32, task.text)
            else:
                zaehler["stufe3"] += 1
                self.assertTrue(2 <= e["anzahl"] <= 300, task.text)
                if e["version"] == 4:
                    self.assertTrue(8 <= e["praefix"] <= 22, task.text)
                else:
                    zaehler["v6"] += 1
                    self.assertTrue(32 <= e["praefix"] <= 56, task.text)
                    self.assertEqual(e["netz"] >> 96, 0x20010DB8, task.text)
            if e["version"] == 4:
                self.assertTrue(tr_privat(e["netz"], e["praefix"]), task.text)
                self.assertLessEqual(e["neu"], 30, task.text)
                self.assertFalse(e["nibble"], task.text)
            else:
                self.assertLessEqual(e["neu"], 64, task.text)
            if e["nibble"]:
                zaehler["nibble"] += 1
                self.assertNotEqual((e["praefix"] + e["k"]) % 4, 0, task.text)
            # Musterloesung = eigene Rechnung
            erwartet = {"praefix": "/%d" % e["neu"], "netz": eigen_text(e["version"], e["start"])}
            if e["version"] == 4:
                maske = (2 ** 32 - 1) ^ (e["groesse"] - 1)
                erwartet.update(maske=eigen_v4_text(maske), adressen=eigen_de(e["groesse"]),
                                hosts=eigen_de(e["groesse"] - 2),
                                broadcast=eigen_v4_text(e["ende"]))
                schluessel = ["praefix", "maske", "adressen", "hosts", "netz", "broadcast"]
            else:
                erwartet.update(adressen="2^%d" % (128 - e["neu"]),
                                letzte=eigen_v6_text(e["ende"]))
                schluessel = ["praefix", "adressen", "netz", "letzte"]
            self.assertEqual([key for key, _l in task.fields], schluessel, task.text)
            self.assertEqual(task.solution, erwartet, task.text)
            # zweite Quelle ipaddress: Subnetz im Ausgangsnetz, ausgerichtet
            klasse = NETZKLASSE[e["version"]]
            basis = klasse((e["netz"], e["praefix"]))
            teil = klasse((e["start"], e["neu"]))          # strict: ausgerichtet
            self.assertTrue(teil.subnet_of(basis), task.text)
            self.assertEqual(int(teil.broadcast_address), e["ende"], task.text)
            self.assertEqual(teil.num_addresses, e["groesse"], task.text)
        # Stufe 3: etwa zur Haelfte IPv6, davon etwa zur Haelfte an Nibble-Grenzen
        self.assertTrue(0.3 * zaehler["stufe3"] <= zaehler["v6"] <= 0.7 * zaehler["stufe3"],
                        zaehler)
        self.assertTrue(0.3 * zaehler["v6"] <= zaehler["nibble"] <= 0.7 * zaehler["v6"],
                        zaehler)

    def test_tr1_jede_teilantwort_einzeln(self):
        for _stufe, task in tr_aufgaben("teilen"):
            e = tr_teilen_lesen(task)
            text = lambda wert: eigen_text(e["version"], wert)   # noqa: E731
            falsch = {"praefix": "/%d" % (e["neu"] - 1), "netz": text(e["start"] + e["groesse"]),
                      "adressen": eigen_de(e["groesse"] * 2)}
            if e["version"] == 4:
                falsch.update(maske=eigen_v4_text((2 ** 32 - 1) ^ (2 * e["groesse"] - 1)),
                              hosts=eigen_de(e["groesse"] - 1),
                              broadcast=text(e["ende"] - 1))
            else:
                falsch.update(letzte=text(e["ende"] + 1))
            tr_einzeln(self, task, falsch)
            # andere Schreibweisen derselben Antwort
            self.assertTrue(task.check({"praefix": str(e["neu"])})["praefix"])
            self.assertTrue(task.check({"adressen": str(e["groesse"])})["adressen"])
            self.assertTrue(task.check({"adressen": "2^%d" % (e["breite"] - e["neu"])})
                            ["adressen"])
            self.assertFalse(task.check({"adressen": "2^%d" % (e["breite"] - e["neu"] + 1)})
                             ["adressen"])
            if e["version"] == 6:
                self.assertTrue(task.check({"netz": task.solution["netz"].upper()})["netz"])
            for unsinn in ("", "/", "2^", "²", "/²7", "1.2.3.4/33", "abc", "3.2", "1.2.3.4"):
                self.assertFalse(any(task.check({k: unsinn for k, _l in task.fields}).values()),
                                 (task.text, unsinn))

    def test_tr1_rechenweg_pc_und_handy(self):
        for _stufe, task in tr_aufgaben("teilen"):
            e = tr_teilen_lesen(task)
            self.assertTrue(all(len(z) <= PC_BREITE for z in task.steps), task.text)
            self.assertTrue(all(len(z) <= GRENZE for z in task.steps_schmal), task.text)
            netz = "%s/%d" % (eigen_text(e["version"], e["netz"]), e["praefix"])
            anzahl = 2 ** (e["neu"] - e["praefix"]) if e["nibble"] else e["anzahl"]
            kern = fc.split_network(netz, anzahl, e["version"])
            for schmal, zeilen in ((False, task.steps), (True, task.steps_schmal)):
                pc = fc.split_explain(kern, schmal).split("\n")
                vorne = zeilen.index(pc[0])
                self.assertEqual(zeilen[vorne:vorne + len(pc)], pc, task.text)
                self.assertEqual(vorne > 0, e["nibble"], task.text)
                schluss = zeilen[vorne + len(pc):]
                self.assertEqual(schluss[0], "", task.text)
                self.assertTrue(schluss[1].startswith("SCHRITT 6: Gefragt ist"), task.text)
                kurz = tr_ohne_leer(schluss)
                self.assertIn("Nr.%d" % e["nr"], kurz)
                self.assertIn("(%d-1)x" % e["nr"], kurz)
                self.assertIn("=" + eigen_text(e["version"], e["start"]), kurz)
                self.assertIn("=" + eigen_text(e["version"], e["ende"]), kurz)
                if e["version"] == 6:
                    self.assertIn("=binär" + format(e["nr"] - 1, "0%db" % kern["k"]), kurz)
                if e["nibble"]:
                    vor = tr_ohne_leer(zeilen[:vorne])
                    self.assertIn("/%d+%d=/%d" % (e["praefix"], e["k"], e["praefix"] + e["k"]),
                                  vor)
                    self.assertIn("ist/%d." % e["neu"], vor)
                    self.assertIn("2^%d" % (e["neu"] - e["praefix"]), vor)

    def test_tr1_feste_beispiele(self):
        """Zwei Aufgaben woertlich (Startwert fest), damit Text und
        Teilantworten nicht unbemerkt wandern."""
        task = fl.trainer_task("teilen", 1, 7)
        self.assertEqual(task.text, "Das Netz 192.168.39.0/24 soll in 6 gleich große Subnetze "
                         "aufgeteilt werden. Geben Sie an: neue Präfixlänge, Subnetzmaske, "
                         "Adressen und nutzbare Hosts je Subnetz sowie Netzadresse und "
                         "Broadcast-Adresse des 6. Subnetzes.")
        self.assertEqual(task.fields, [
            ("praefix", "Neue Präfixlänge"), ("maske", "Subnetzmaske"),
            ("adressen", "Adressen je Subnetz"), ("hosts", "Nutzbare Hosts je Subnetz"),
            ("netz", "Netzadresse des 6. Subnetzes"),
            ("broadcast", "Broadcast-Adresse des 6. Subnetzes")])
        self.assertEqual(task.solution, {
            "praefix": "/27", "maske": "255.255.255.224", "adressen": "32", "hosts": "30",
            "netz": "192.168.39.160", "broadcast": "192.168.39.191"})
        self.assertEqual(task.steps[-4:], [
            "SCHRITT 6: Gefragt ist Subnetz Nr. 6",
            "   Netzadresse = Nr. 1 + (6 - 1) x 32 Adressen",
            "   = 192.168.39.0 + 160 = 192.168.39.160",
            "   Broadcast-Adresse = nächste Netzadresse - 1 = 192.168.39.191"])
        self.assertEqual(task.steps_schmal[-11:], [
            "", "SCHRITT 6: Gefragt ist", "Subnetz Nr. 6", " Netzadresse = Nr. 1",
            " + (6 - 1) x 32", " = 192.168.39.0", " + 160", " = 192.168.39.160",
            " Broadcast-Adresse", " = nächste Netzadresse - 1", " = 192.168.39.191"])


def tr_bedarf_lesen(task):
    treffer = TR_BEDARF.match(task.text)
    assert treffer, task.text
    adresse, praefix, liste, nr = treffer.groups()
    namen, bedarfe = [], []
    for teil in liste.split(", "):
        name, zahl = teil.rsplit(": ", 1)
        menge, einheit = zahl.split(" ")
        assert einheit == ("Host" if menge == "1" else "Hosts"), teil
        namen.append(name)
        bedarfe.append(int(menge.replace(".", "")))
    netz, praefix = eigen_v4(adresse), int(praefix)
    vergabe = eigen_vergabe(netz, praefix, bedarfe)
    return {"netz": netz, "praefix": praefix, "namen": namen, "bedarfe": bedarfe,
            "nr": int(nr), "vergabe": vergabe}


class TrainerBedarfTest(unittest.TestCase):
    """T-TR-1 "Nach Hostbedarf": 3 Stufen x 200 Startwerte, immer loesbar,
    Rest 0 in mehr als 20 % je Stufe."""

    def test_tr1_stufen_loesbar_und_loesung_gegen_eigene_rechnung(self):
        rest_null = {1: 0, 2: 0, 3: 0}
        rest_da = {1: 0, 2: 0, 3: 0}
        for stufe, task in tr_aufgaben("bedarf"):
            e = tr_bedarf_lesen(task)
            self.assertEqual((task.kind, task.level), ("bedarf", stufe))
            anzahl = len(e["bedarfe"])
            erlaubt = {1: ((2, 3), (24,)), 2: ((3, 4), (23, 24)), 3: ((4, 6), (22, 23))}[stufe]
            self.assertTrue(erlaubt[0][0] <= anzahl <= erlaubt[0][1], task.text)
            self.assertIn(e["praefix"], erlaubt[1], task.text)
            self.assertTrue(tr_privat(e["netz"], e["praefix"]), task.text)
            self.assertEqual(e["netz"] % 2 ** (32 - e["praefix"]), 0, task.text)
            self.assertEqual(len(set(n.lower() for n in e["namen"])), anzahl, task.text)
            self.assertTrue(all(len(n) <= fc.SUBNET_NAME_MAX for n in e["namen"]))
            # immer loesbar, zweites Verfahren (Freiliste) kommt aufs Gleiche
            self.assertIsInstance(e["vergabe"], dict, task.text)
            netz = ipaddress.IPv4Network((e["netz"], e["praefix"]))
            self.assertEqual(freiliste(netz, e["bedarfe"]), e["vergabe"], task.text)
            belegt = sum(2 ** (32 - p) for _s, p in e["vergabe"].values())
            rest = 2 ** (32 - e["praefix"]) - belegt
            (rest_null if rest == 0 else rest_da)[stufe] += 1
            reihenfolge = sorted(range(anzahl), key=lambda i: (-e["bedarfe"][i], i))
            self.assertTrue(1 <= e["nr"] <= anzahl, task.text)
            start, p = e["vergabe"][reihenfolge[e["nr"] - 1]]
            erwartet = {"broadcast": eigen_v4_text(start + 2 ** (32 - p) - 1),
                        "rest": eigen_de(rest)}
            schluessel = []
            for i in range(anzahl):
                start_i, p_i = e["vergabe"][i]
                erwartet["netz%d" % i] = "%s/%d" % (eigen_v4_text(start_i), p_i)
                erwartet["maske%d" % i] = eigen_v4_text((2 ** 32 - 1) ^ (2 ** (32 - p_i) - 1))
                schluessel += ["netz%d" % i, "maske%d" % i]
            self.assertEqual([k for k, _l in task.fields], schluessel + ["broadcast", "rest"])
            self.assertEqual(task.solution, erwartet, task.text)
            for i, (key, label) in enumerate(task.fields[:2 * anzahl]):
                name = e["namen"][i // 2]
                menge = fc.subnet_hosts_text(e["bedarfe"][i // 2])
                self.assertEqual(label, "%s (%s): Netzadresse/Präfix" % (name, menge)
                                 if key.startswith("netz") else "%s: Subnetzmaske" % name)
        for stufe in (1, 2, 3):
            self.assertGreater(rest_null[stufe], 0.2 * TR_STARTWERTE, rest_null)
            self.assertGreater(rest_da[stufe], 0.2 * TR_STARTWERTE, rest_da)

    def test_tr1_jede_teilantwort_einzeln(self):
        for _stufe, task in tr_aufgaben("bedarf"):
            e = tr_bedarf_lesen(task)
            falsch = {}
            for i, (start, p) in e["vergabe"].items():
                falsch["netz%d" % i] = "%s/%d" % (eigen_v4_text(start), p - 1 if start % 2 ** (33 - p)
                                                  == 0 else p + 1)
                falsch["maske%d" % i] = eigen_v4_text((2 ** 32 - 1) ^ (2 ** (33 - p) - 1))
            sol = task.solution
            falsch["broadcast"] = eigen_v4_text(eigen_v4(sol["broadcast"]) - 1)
            falsch["rest"] = str(int(sol["rest"].replace(".", "")) + 1)
            tr_einzeln(self, task, falsch)
            self.assertTrue(task.check({"rest": sol["rest"].replace(".", "")})["rest"])
            for unsinn in ("", "/", "1.2.3.4/33", "abc", "²", "6.4", "2^6"):
                self.assertFalse(any(task.check({k: unsinn for k, _l in task.fields}).values()),
                                 (task.text, unsinn))

    def test_tr1_rechenweg_pc_und_handy(self):
        for _stufe, task in tr_aufgaben("bedarf"):
            e = tr_bedarf_lesen(task)
            kern = fc.subnet_by_hosts("%s/%d" % (eigen_v4_text(e["netz"]), e["praefix"]),
                                      list(zip(e["namen"], e["bedarfe"])), 4)
            self.assertEqual(task.steps, fc.hosts_explain(kern).split("\n"))
            self.assertEqual(task.steps_schmal, fc.hosts_explain(kern, True).split("\n"))
            self.assertTrue(all(len(z) <= PC_BREITE for z in task.steps), task.text)
            self.assertTrue(all(len(z) <= GRENZE for z in task.steps_schmal), task.text)
            # die Antworten stehen im Rechenweg (PC und Handy)
            for zeilen in (task.steps, task.steps_schmal):
                kurz = tr_ohne_leer(zeilen)
                for key, wert in task.solution.items():
                    if key != "rest" or wert != "0":
                        self.assertIn(wert, kurz, (task.text, key))

    def test_tr1_festes_beispiel(self):
        task = fl.trainer_task("bedarf", 1, 7)
        self.assertEqual(task.text, (
            "Das Netz 172.16.49.0/24 soll nach Hostbedarf aufgeteilt werden: Produktion: "
            "67 Hosts, Lager: 27 Hosts, Server: 23 Hosts. Vergeben wird lückenlos ab der "
            "ersten Adresse, das größte Subnetz zuerst. Geben Sie je Subnetz "
            "Netzadresse/Präfix und Subnetzmaske an, dazu die Broadcast-Adresse des 2. "
            "vergebenen Subnetzes und den freien Rest in Adressen."))
        self.assertEqual(task.fields, [
            ("netz0", "Produktion (67 Hosts): Netzadresse/Präfix"),
            ("maske0", "Produktion: Subnetzmaske"),
            ("netz1", "Lager (27 Hosts): Netzadresse/Präfix"), ("maske1", "Lager: Subnetzmaske"),
            ("netz2", "Server (23 Hosts): Netzadresse/Präfix"), ("maske2", "Server: Subnetzmaske"),
            ("broadcast", "Broadcast-Adresse des 2. vergebenen Subnetzes"),
            ("rest", "Freier Rest (Anzahl Adressen)")])
        self.assertEqual(task.solution, {
            "netz0": "172.16.49.0/25", "maske0": "255.255.255.128",
            "netz1": "172.16.49.128/27", "maske1": "255.255.255.224",
            "netz2": "172.16.49.160/27", "maske2": "255.255.255.224",
            "broadcast": "172.16.49.159", "rest": "64"})


class TrainerSchutzTest(unittest.TestCase):
    """T-TR-2/T-TR-3 und G-63-1: alte Arten unveraendert, neue angehaengt,
    trainer_task unveraendert, Handy nimmt steps_schmal (F-63-18 = S1)."""

    def test_tr3_alte_arten_sind_der_anfang(self):
        arten = [k for k, _n in fl.TRAINER_KINDS]
        self.assertEqual(tuple(arten[:4]), rt.ALTE_ARTEN)
        self.assertEqual(rt.ALTE_ARTEN, ("ipv4", "vlsm", "zahlen", "ipv6"))
        self.assertEqual(fl.TRAINER_KINDS[4:], [("teilen", "Netz aufteilen"),
                                                ("bedarf", "Nach Hostbedarf")])
        self.assertEqual(sorted(fl.TRAINER_BUILDERS), sorted(arten))

    def test_g631_trainer_task_unveraendert(self):
        self.assertEqual(inspect.getsource(fl.trainer_task), (
            'def trainer_task(kind, level, seed, schmal=False):\n'
            '    """Eine Aufgabe, durch kind, level und seed eindeutig festgelegt.\n'
            '    schmal=True (ab 0.62.3, nur das Handy): Schritt 3 der IPv4-Aufgaben\n'
            '    Oktett fuer Oktett; Aufgabe, Loesung und alle anderen Schritte gleich."""\n'
            '    rng = random.Random("%s-%d-%s" % (kind, level, seed))\n'
            '    if kind == "ipv4":\n'
            '        return _ipv4_task(rng, level, schmal)\n'
            '    return TRAINER_BUILDERS[kind](rng, level)\n'))

    def test_s1_steps_schmal_nur_an_neuen_arten(self):
        for kind in rt.ALTE_ARTEN:
            for schmal in (False, True):
                self.assertFalse(hasattr(fl.trainer_task(kind, 2, 5, schmal), "steps_schmal"))
        for kind in ("teilen", "bedarf"):
            for stufe in (1, 2, 3):
                pc = fl.trainer_task(kind, stufe, 11)
                handy = fl.trainer_task(kind, stufe, 11, schmal=True)
                self.assertEqual((handy.text, handy.fields, handy.solution, handy.steps,
                                  handy.steps_schmal),
                                 (pc.text, pc.fields, pc.solution, pc.steps, pc.steps_schmal))
                self.assertTrue(pc.steps_schmal)

    def test_handy_anzeige_und_tastatur(self):
        with open(os.path.join(CODE, "mobile", "src", "main.py"), encoding="utf-8") as datei:
            quelle = datei.read()
        self.assertIn('"\\n".join(getattr(task, "steps_schmal", None) or task.steps)', quelle)
        self.assertIn('if task.kind in ("ipv6", "zahlen", "teilen", "bedarf")', quelle)


if __name__ == "__main__":
    unittest.main(verbosity=1)
