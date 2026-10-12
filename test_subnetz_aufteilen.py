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

ZU_VIELE = [
    ("192.168.10.0/24", 257, "Zu viele Subnetze: /24 + 9 Bit = /33, mehr als /32 geht nicht."),
    ("192.168.10.0/30", 5, "Zu viele Subnetze: /30 + 3 Bit = /33, mehr als /32 geht nicht."),
    ("192.168.10.0/31", 3, "Zu viele Subnetze: /31 + 2 Bit = /33, mehr als /32 geht nicht."),
    ("192.168.10.7/32", 2, "Zu viele Subnetze: /32 + 1 Bit = /33, mehr als /32 geht nicht."),
    ("2001:db8::/127", 3, "Zu viele Subnetze: /127 + 2 Bit = /129, mehr als /128 geht nicht."),
    ("2001:db8::1/128", 2, "Zu viele Subnetze: /128 + 1 Bit = /129, mehr als /128 geht nicht."),
    ("::/0", 2 ** 128 + 1, "Zu viele Subnetze: /0 + 129 Bit = /129, mehr als /128 geht nicht."),
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
            ("A 50\nB 2,5", "Zeile 2: Bitte die Anzahl Hosts als ganze Zahl angeben "
                            "(z. B. A 50)."),
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
                         "Es fehlen 64 Adressen. Das Ausgangsnetz müsste mindestens /23 sein.")
        r = fc.subnet_by_hosts("192.168.10.0/24", "A 127\nB 62\nC 30\nD 14\nE 6\nF 2")
        self.assertEqual(r["meldung"],
                         "Es fehlen 124 Adressen. Das Ausgangsnetz müsste mindestens /23 sein.")
        r = fc.subnet_by_hosts("192.168.10.0/30", "A 3")
        self.assertEqual(r["meldung"],
                         "Es fehlen 4 Adressen. Das Ausgangsnetz müsste mindestens /29 sein.")
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
            self.assertEqual(r["meldung"], "Es fehlen %s Adressen. Das Ausgangsnetz müsste "
                                           "mindestens /%d sein." % (
                                               "{:,}".format(eigen[1]).replace(",", "."),
                                               eigen[2]))
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
                       "\n".join("Vertrieb Nord %d" % i for i in range(1, 13))):
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
#  T-RW-3  die vier Beispiele aus Anhang A woertlich (dazu nur die Zeilen
#          aus Plan 0.63 Abschnitt 2.2 Punkt 3 und 9 und E-63-4, einzeln
#          benannt in ZUSAETZE)
#  T-K-8   Nibble-Zeile im Rechenweg genau dann, wenn noetig
# ===========================================================================

# Anhang A / belege/b2_rechenweg_beispiele.txt (Plan 0.63), Zeile fuer Zeile
ANHANG_A = {
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
        '  Nr Netzadresse        Erste Host      Letzte Host     Broadcast',
        '  1  10.20.0.0/18       10.20.0.1       10.20.63.254    10.20.63.255',
        '  2  10.20.64.0/18      10.20.64.1      10.20.127.254   10.20.127.255',
        '  3  10.20.128.0/18     10.20.128.1     10.20.191.254   10.20.191.255',
        '  4  10.20.192.0/18     10.20.192.1     10.20.255.254   10.20.255.255',
        '',
        'SCHRITT 5: Kontrolle',
        '   4 x 16.384 = 65.536 Adressen = Größe von /16 (2^16 = 65.536)',
        '   Alle 4 Subnetze werden verwendet.',
    ),
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
        '  Nr Netzadresse        Erste Host      Letzte Host     Broadcast',
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
        '',
        'SCHRITT 3: Wo liegt die Grenze? Schrittweite und Größe',
        '   /51 endet im 4. Hextett (Bits 49 bis 64). Davon gehören',
        '   51 - 48 = 3 Bits zum Netzanteil.',
        '   Schrittweite im 4. Hextett = 2^(64 - 51) = 2^13 = 8.192 = hex 2000',
        '   Adressen je Subnetz = 2^(128 - 51) = 2^77',
        '      = 151.115.727.451.828.646.838.272',
        '   Kein Abzug von 2: IPv6 hat keine Broadcast-Adresse.',
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
    'D_PC': (
        'RECHENWEG NACH HOSTBEDARF (VLSM, IPv4)',
        'Ausgangsnetz 192.168.10.0/24',
        'Bedarf: A 50 Hosts, B 20 Hosts, C 10 Hosts, D 2 Hosts',
        '',
        'SCHRITT 1: Nach Hostbedarf sortieren, größter Bedarf zuerst',
        '   A 50, B 20, C 10, D 2',
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
        '  Nr Name Netzadresse        Erste Host      Letzte Host     Broadcast',
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
        ' A 50, B 20, C 10, D 2',
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
}

ALTE_BUECHER = ["Ältere Bücher ziehen 2 Subnetze ab. Das ist veraltet (RFC 1878)."]
ALTE_BUECHER_HANDY = ["Ältere Bücher ziehen 2", "Subnetze ab. Das ist", "veraltet (RFC 1878)."]
NIBBLE_PC = ["An der nächsten 4-Bit-Grenze (Nibble): /52 = 16 Subnetze. In der Praxis",
             "üblich, weil dann jede Hex-Ziffer ein Teil der Subnetz-Nummer ist.",
             "Gerechnet wird hier weiter mit /51."]
NIBBLE_HANDY = ["An der nächsten", "4-Bit-Grenze (Nibble): /52", "= 16 Subnetze. In der",
                "Praxis üblich, weil dann", "jede Hex-Ziffer ein Teil",
                "der Subnetz-Nummer ist.", "Gerechnet wird hier weiter", "mit /51."]
ANYCAST_PC = ["Einzelne Adressen sind reserviert, z. B. die",
              "Subnet-Router-Anycast-Adresse (alle Bits der Schnittstellenkennung 0,",
              "RFC 4291 2.6.1)."]
ANYCAST_HANDY = ["Einzelne Adressen sind", "reserviert, z. B. die", "Subnet-Router-Anycast-",
                 "Adresse (alle Bits der", "Schnittstellenkennung 0,", "RFC 4291 2.6.1)."]


def _einzug(zeilen, einzug):
    return [einzug + zeile for zeile in zeilen]


# Zusaetzliche Zeilen gegenueber Anhang A: (nach Zeile Nr. im Anhang, Zeilen)
ZUSAETZE = {
    "A_PC": [(30, _einzug(ALTE_BUECHER, "   "))],                     # E-63-4
    "A_HANDY": [(65, _einzug(ALTE_BUECHER_HANDY, " "))],
    "B_PC": [(36, _einzug(ALTE_BUECHER, "   "))],
    "B_HANDY": [(90, _einzug(ALTE_BUECHER_HANDY, " "))],
    "C_PC": [(10, _einzug(NIBBLE_PC, "   ")),                           # 2.2 Punkt 9
             (18, _einzug(ANYCAST_PC, "   "))],                         # 2.2 Punkt 3
    "C_HANDY": [(17, _einzug(NIBBLE_HANDY, " ")), (34, _einzug(ANYCAST_HANDY, " "))],
    "D_PC": [], "D_HANDY": [],
}

BEISPIELE = {"A": ("teilen", "10.20.0.0/16", 4), "B": ("teilen", "192.168.10.0/24", 6),
             "C": ("teilen", "2001:db8:abcd::/48", 6),
             "D": ("bedarf", "192.168.10.0/24", "A 50\nB 20\nC 10\nD 2")}


def rechenweg(art, netz, wert, schmal=False):
    if art == "teilen":
        return fc.split_explain(fc.split_network(netz, wert), schmal)
    return fc.hosts_explain(fc.subnet_by_hosts(netz, wert), schmal)


def erwartet(schluessel):
    zeilen = list(ANHANG_A[schluessel])
    for nach, neu in sorted(ZUSAETZE[schluessel], reverse=True):
        zeilen[nach:nach] = neu
    return zeilen


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
    zeilen = []
    for _ in range(rng.randint(1, 12)):
        name = rng.choice(namen)
        bedarf = rng.randint(1, max(1, min(platz, 2 ** 32 - 2) // rng.choice([1, 2, 4, 12])))
        zeilen.append(("%s %d" % (name, bedarf)).strip())
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
            ("bedarf", "255.255.255.0/24", "\n".join("Lager Nord %d" % i for i in range(1, 13))),
            ("bedarf", "10.0.0.0/8", "\n".join("Geschäftsleitung %d" % (10 ** 6 + i)
                                                for i in range(12))),
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
    """T-RW-3: Anhang A woertlich, dazu nur die benannten Zeilen."""

    def test_beispiele(self):
        for schluessel in sorted(ANHANG_A):
            art, netz, wert = BEISPIELE[schluessel[0]]
            with self.subTest(beispiel=schluessel):
                text = rechenweg(art, netz, wert, schluessel.endswith("HANDY"))
                self.assertEqual(text.split("\n"), erwartet(schluessel))

    def test_zusaetze_nur_benannte_zeilen(self):
        for schluessel, liste in ZUSAETZE.items():
            for _nach, zeilen in liste:
                inhalt = " ".join(" ".join(zeilen).split())
                self.assertTrue(inhalt.startswith(("Ältere Bücher", "An der nächsten",
                                                   "Einzelne Adressen")), schluessel)

    def test_anhang_vollstaendig(self):
        self.assertEqual(sorted(ANHANG_A), ["A_HANDY", "A_PC", "B_HANDY", "B_PC",
                                            "C_HANDY", "C_PC", "D_HANDY", "D_PC"])
        self.assertEqual([len(ANHANG_A[k]) for k in sorted(ANHANG_A)],
                         [65, 30, 90, 36, 111, 39, 91, 41])   # Zeilenzahlen laut b2


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
            self.assertIn("Es fehlen 124 Adressen. Das Ausgangsnetz müsste mindestens /23 sein.",
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
            self.assertIn("B 60, C 25, A 10, D 2", self.flach(weg))
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
            self.assertIn("Es fehlen 124 Adressen. Das Ausgangsnetz müsste mindestens "
                          "/23 sein.", weg)
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



if __name__ == "__main__":
    unittest.main(verbosity=1)
