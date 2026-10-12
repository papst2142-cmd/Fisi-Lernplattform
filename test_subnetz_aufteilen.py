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



if __name__ == "__main__":
    unittest.main(verbosity=1)
