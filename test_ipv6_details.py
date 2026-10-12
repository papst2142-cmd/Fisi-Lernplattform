#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests ab 0.63 (Plan 0.63, F-63-4 Variante A nach F-63-17): die zwei
IPv6-Ergebniszeilen "Ausgeschrieben" und "Adresstyp" aus
fisi_core.ipv6_details. subnet_report bleibt unveraendert (Test 4 in
test_rechenweg.py prueft das weiter, diese Datei aendert ihn nicht).

  D-1  Beispiele aus Plan 0.63 (6.4/b15 und 2.5) woertlich
  D-2  Adresstyp gegen eine eigene Rechnung mit ipaddress (subnet_of,
       overlaps), 20.000 Zufallsfaelle (Startwert 634)
  D-3  Gegenprobe mit den ipaddress-Eigenschaften (is_unspecified,
       is_loopback, is_multicast, is_link_local, is_site_local, is_private)
       fuer einzelne Adressen (/128), 20.000 Zufallsfaelle
  D-4  Ausgeschrieben = network_address.exploded + "/Praefix" (die
       ausgeschriebene Form haengt nicht vom Python-Patchstand ab)
  D-5  Fehler: IPv4, ungueltig, leer -> InputError mit dem Text von
       subnet_report
  D-6  Beschriftungen als Konstanten, Rueckgabe genau zwei Paare,
       Seitensprung-Konstanten (Schnittstelle Nachtrag 17:55)
  D-7  Regel "Praefix kuerzer als der Typbereich" an Grenzfaellen
  D-8  Zeilenlaengen PC ("%-22s: %s" wie subnet_report) und Handy
       (Wert eigene Zeile, 2 Leerzeichen Einzug): Hoechstwerte festgehalten

Der Code-Ordner ist waehlbar (fuer die Rot-Probe gegen einen alten Stand):

    IPV6_CODE=<ordner mit dem Code> python test_ipv6_details.py

Start:  python test_ipv6_details.py
"""

import ipaddress
import os
import random
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
CODE = os.path.abspath(os.environ.get("IPV6_CODE") or HERE)
sys.path.insert(0, CODE)

import fisi_core as fc            # noqa: E402

N = ipaddress.IPv6Network
ULA = "Unique Local (fc00::/7, RFC 4193)"
# Eigene Tabelle (unabhaengig vom Programmcode, Plan 0.63 2.1 und 2.5)
TABELLE = [
    (N("::/128"), "Unspezifiziert (::/128)"),
    (N("::1/128"), "Loopback (::1/128)"),
    (N("ff00::/8"), "Multicast (ff00::/8)"),
    (N("fe80::/10"), "Link-Local (fe80::/10)"),
    (N("fec0::/10"), "Site-Local (veraltet, RFC 3879)"),
    (N("fc00::/7"), ULA),
    (N("fd00::/8"), ULA + ", lokal vergeben, fd00::/8"),
    (N("fc00::/8"), ULA + ", L-Bit 0, bisher nicht vergeben"),
    (N("2001:db8::/32"), "Dokumentation (2001:db8::/32, RFC 3849)"),
    (N("3fff::/20"), "Dokumentation (3fff::/20, RFC 9637)"),
    (N("2000::/3"), "Global Unicast (2000::/3)"),
]
REST = "nicht zugeordnet (laut RFC 4291 als Global Unicast zu behandeln)"
GEMISCHT = "mehrere Adresstypen (Präfix kürzer als Typbereich)"
FEHLER = ("Bitte eine gültige Adresse angeben.\n\n"
          "Beispiele:\n  192.168.1.50/24\n  10.0.0.0/255.255.255.0\n"
          "  2001:db8::1/64")
PC_BREITE = 75
GRENZE = 28


def erwartet_typ(netz):
    """Genauester Bereich, der das ganze Netz enthaelt; sonst gemischt, wenn
    das Netz einen Bereich beruehrt; sonst nicht zugeordnet."""
    drin = [(b.prefixlen, t) for b, t in TABELLE if netz.subnet_of(b)]
    if drin:
        return max(drin)[1]
    if any(netz.overlaps(b) for b, _t in TABELLE):
        return GEMISCHT
    return REST


def details(value):
    return fc.ipv6_details(value)


def zufall_netz(rnd):
    """Zufallsnetz, gehaeuft um die Typbereiche herum."""
    art = rnd.random()
    if art < 0.6:
        basis, _t = rnd.choice(TABELLE)
        wert = int(basis.network_address) ^ (rnd.getrandbits(128) >> rnd.randint(0, 128))
    elif art < 0.7:
        wert = rnd.randint(0, 3)
    else:
        wert = rnd.getrandbits(128)
    praefix = rnd.choice([rnd.randint(0, 128), 128, 64, 48, 8, 7, 10, 3, 20, 32])
    return wert, praefix


class BeispielTest(unittest.TestCase):
    """D-1: Beispiele aus Plan 0.63 (SUBNET_INPUTS aus b15, 2.5)."""

    FAELLE = [
        ("2001:db8::1/64", "2001:0db8:0000:0000:0000:0000:0000:0000/64",
         "Dokumentation (2001:db8::/32, RFC 3849)"),
        ("2001:db8:abcd:12::/48", "2001:0db8:abcd:0000:0000:0000:0000:0000/48",
         "Dokumentation (2001:db8::/32, RFC 3849)"),
        ("fe80::1/10", "fe80:0000:0000:0000:0000:0000:0000:0000/10",
         "Link-Local (fe80::/10)"),
        ("2001:db8::1/127", "2001:0db8:0000:0000:0000:0000:0000:0000/127",
         "Dokumentation (2001:db8::/32, RFC 3849)"),
        ("2001:db8::1/128", "2001:0db8:0000:0000:0000:0000:0000:0001/128",
         "Dokumentation (2001:db8::/32, RFC 3849)"),
        ("fd00::/8", "fd00:0000:0000:0000:0000:0000:0000:0000/8",
         "Unique Local (fc00::/7, RFC 4193), lokal vergeben, fd00::/8"),
        ("fd12:3456:789a:1::1/64", "fd12:3456:789a:0001:0000:0000:0000:0000/64",
         "Unique Local (fc00::/7, RFC 4193), lokal vergeben, fd00::/8"),
        ("fc00::1/64", "fc00:0000:0000:0000:0000:0000:0000:0000/64",
         "Unique Local (fc00::/7, RFC 4193), L-Bit 0, bisher nicht vergeben"),
        ("fc00::/7", "fc00:0000:0000:0000:0000:0000:0000:0000/7",
         "Unique Local (fc00::/7, RFC 4193)"),
        ("::/128", "0000:0000:0000:0000:0000:0000:0000:0000/128",
         "Unspezifiziert (::/128)"),
        ("::1", "0000:0000:0000:0000:0000:0000:0000:0001/128",
         "Loopback (::1/128)"),
        ("ff02::1/128", "ff02:0000:0000:0000:0000:0000:0000:0001/128",
         "Multicast (ff00::/8)"),
        ("ff00::/8", "ff00:0000:0000:0000:0000:0000:0000:0000/8",
         "Multicast (ff00::/8)"),
        ("fec0::1/64", "fec0:0000:0000:0000:0000:0000:0000:0000/64",
         "Site-Local (veraltet, RFC 3879)"),
        ("3fff:abc::1/48", "3fff:0abc:0000:0000:0000:0000:0000:0000/48",
         "Dokumentation (3fff::/20, RFC 9637)"),
        ("2001:db8:abcd::/48", "2001:0db8:abcd:0000:0000:0000:0000:0000/48",
         "Dokumentation (2001:db8::/32, RFC 3849)"),
        ("2a00:1450:4001::1/64", "2a00:1450:4001:0000:0000:0000:0000:0000/64",
         "Global Unicast (2000::/3)"),
        ("2000::/3", "2000:0000:0000:0000:0000:0000:0000:0000/3",
         "Global Unicast (2000::/3)"),
        ("4000::1/64", "4000:0000:0000:0000:0000:0000:0000:0000/64", REST),
        ("::ffff:1.2.3.4/128", "0000:0000:0000:0000:0000:ffff:0102:0304/128", REST),
        ("  2001:DB8::1/64 ", "2001:0db8:0000:0000:0000:0000:0000:0000/64",
         "Dokumentation (2001:db8::/32, RFC 3849)"),
    ]

    def test_beispiele(self):
        for eingabe, lang, typ in self.FAELLE:
            with self.subTest(eingabe=eingabe):
                self.assertEqual(details(eingabe),
                                 [("Ausgeschrieben", lang), ("Adresstyp", typ)])


class ZufallTest(unittest.TestCase):
    """D-2 und D-4: 20.000 Zufallsnetze gegen ipaddress."""

    def test_zufall(self):
        rnd = random.Random(634)
        gesehen = set()
        for _ in range(20000):
            wert, praefix = zufall_netz(rnd)
            text = "%s/%d" % (ipaddress.IPv6Address(wert), praefix)
            netz = ipaddress.ip_network(text, strict=False)
            ergebnis = details(text)
            self.assertEqual(len(ergebnis), 2, text)
            self.assertEqual(ergebnis[0], (fc.IPV6_LABEL_AUSGESCHRIEBEN,
                                           netz.network_address.exploded + "/%d" % praefix),
                             text)
            self.assertEqual(ergebnis[1], (fc.IPV6_LABEL_ADRESSTYP, erwartet_typ(netz)), text)
            gesehen.add(ergebnis[1][1])
        # jeder Text kommt in den Zufallsfaellen vor
        self.assertEqual(gesehen, {t for _b, t in TABELLE} | {REST, GEMISCHT})


class EigenschaftTest(unittest.TestCase):
    """D-3: einzelne Adressen gegen die ipaddress-Eigenschaften."""

    def test_eigenschaften(self):
        rnd = random.Random(6340)
        for _ in range(20000):
            wert, _p = zufall_netz(rnd)
            adresse = ipaddress.IPv6Address(wert)
            typ = details("%s/128" % adresse)[1][1]
            with self.subTest(adresse=str(adresse)):
                self.assertEqual(typ == "Unspezifiziert (::/128)", adresse.is_unspecified)
                self.assertEqual(typ == "Loopback (::1/128)", adresse.is_loopback)
                self.assertEqual(typ == "Multicast (ff00::/8)", adresse.is_multicast)
                self.assertEqual(typ == "Link-Local (fe80::/10)", adresse.is_link_local)
                self.assertEqual(typ.startswith("Site-Local"), adresse.is_site_local)
                # 3fff::/20 (RFC 9637, 2024) kennt ipaddress in 3.12.3 noch
                # nicht, darum nur fc00::/7 und 2001:db8::/32
                if typ.startswith("Unique Local") or "2001:db8::/32" in typ:
                    self.assertTrue(adresse.is_private)
                if typ.startswith("Unique Local"):
                    lbit = (wert >> 120) & 1
                    self.assertEqual("lokal vergeben" in typ, lbit == 1)
                    self.assertEqual("L-Bit 0" in typ, lbit == 0)
                if typ == "Global Unicast (2000::/3)":
                    self.assertEqual(wert >> 125, 1)
                # Weder privat (::, ::1, fe80::/10, fc00::/7, 2001:db8::/32
                # u. a.) noch Multicast/Site-Local/3fff::/20 => GUA oder Rest
                if not (adresse.is_private or adresse.is_multicast
                        or adresse.is_site_local or wert >> 108 == 0x3fff0):
                    self.assertIn(typ, ("Global Unicast (2000::/3)", REST))


class FehlerTest(unittest.TestCase):
    """D-5: ungueltig oder IPv4 -> InputError mit dem Text von subnet_report."""

    def test_fehler(self):
        for eingabe in ["192.168.1.50/24", "10.0.0.0/255.255.255.0", "1.2.3.4",
                        "", "   ", "abc", "2001:db8::1/129", "2001:db8:::1/64",
                        "2001:db8::1/-1", "fe80::1/x", "gggg::/16"]:
            with self.subTest(eingabe=eingabe):
                with self.assertRaises(fc.InputError) as fall:
                    details(eingabe)
                self.assertEqual(str(fall.exception), FEHLER)

    def test_gleicher_text_wie_subnet_report(self):
        with self.assertRaises(fc.InputError) as fall:
            fc.subnet_report("abc")
        self.assertEqual(str(fall.exception), FEHLER)
        self.assertEqual(fc.IPV6_DETAILS_ERROR, FEHLER)


class KonstantenTest(unittest.TestCase):
    """D-6: eine Quelle fuer PC und Handy."""

    def test_konstanten(self):
        self.assertEqual(fc.IPV6_LABEL_AUSGESCHRIEBEN, "Ausgeschrieben")
        self.assertEqual(fc.IPV6_LABEL_ADRESSTYP, "Adresstyp")
        self.assertEqual(fc.SUBNET_PAGE_JUMP_FIELD, "Seite")
        self.assertEqual(fc.SUBNET_PAGE_JUMP, "Zur Seite")

    def test_form(self):
        ergebnis = details("2001:db8::1/64")
        self.assertIsInstance(ergebnis, list)
        self.assertEqual([type(p) for p in ergebnis], [tuple, tuple])
        self.assertEqual([p[0] for p in ergebnis],
                         [fc.IPV6_LABEL_AUSGESCHRIEBEN, fc.IPV6_LABEL_ADRESSTYP])
        self.assertTrue(all(isinstance(t, str) for p in ergebnis for t in p))

    def test_subnet_report_unveraendert(self):
        # subnet_report liefert fuer IPv6 weiter genau fuenf Zeilen
        text = fc.subnet_report("2001:db8::1/64")
        self.assertEqual(len(text.split("\n")), 5)
        self.assertNotIn("Adresstyp", text)
        self.assertNotIn("Ausgeschrieben", text)


class GrenzfallTest(unittest.TestCase):
    """D-7: Praefix kuerzer als der Typbereich."""

    def test_grenzfaelle(self):
        faelle = {
            "::/0": GEMISCHT, "::/127": GEMISCHT, "::/64": GEMISCHT,
            "fe80::/9": GEMISCHT, "fc00::/6": GEMISCHT, "ff00::/7": GEMISCHT,
            "2000::/2": GEMISCHT, "8000::/1": GEMISCHT,
            "fe80::/10": "Link-Local (fe80::/10)",
            "fe80::/11": "Link-Local (fe80::/10)",
            "fd00::/7": ULA,               # Netzadresse fc00::, ganzes /7
            "2001:db8::/31": "Global Unicast (2000::/3)",
            "2001:db8::/32": "Dokumentation (2001:db8::/32, RFC 3849)",
            "3fff::/19": "Global Unicast (2000::/3)",
            "3fff::/20": "Dokumentation (3fff::/20, RFC 9637)",
            "4000::/2": REST, "::2/127": REST, "::/8": GEMISCHT,
            "100::/8": REST,
        }
        for eingabe, typ in faelle.items():
            with self.subTest(eingabe=eingabe):
                self.assertEqual(details(eingabe)[1][1], typ)


class ZeilenlaengeTest(unittest.TestCase):
    """D-8: laengste Zeile PC und Handy, Hoechstwerte festgehalten
    (Ergebnis im Bericht, R-13/G-11)."""

    def test_laengen(self):
        texte = [t for _b, t in TABELLE] + [REST, GEMISCHT]
        typ_max = max(len(t) for t in texte)
        lang_max = len(details("ffff::/128")[0][1])
        self.assertEqual(lang_max, 43)
        self.assertEqual(typ_max, 65)
        pc = ["%-22s: %s" % (fc.IPV6_LABEL_AUSGESCHRIEBEN, "x" * lang_max),
              "%-22s: %s" % (fc.IPV6_LABEL_ADRESSTYP, "x" * typ_max)]
        self.assertEqual([len(z) for z in pc], [67, 89])
        # PC ueber 75 Zeichen: genau diese drei Texte (Bericht, R-13)
        self.assertEqual(sorted(t for t in texte if 24 + len(t) > PC_BREITE),
                         sorted([REST, ULA + ", lokal vergeben, fd00::/8",
                                 ULA + ", L-Bit 0, bisher nicht vergeben"]))
        # Handy: Wert in eigener Zeile mit 2 Leerzeichen Einzug; passt in
        # 28 Zeichen nur bei diesen Texten (alle anderen brauchen Umbruch
        # im Wert oder Wischen, Bericht)
        passt = sorted(t for t in texte if 2 + len(t) <= GRENZE)
        self.assertEqual(passt, sorted(["Loopback (::1/128)", "Multicast (ff00::/8)",
                                        "Link-Local (fe80::/10)",
                                        "Unspezifiziert (::/128)",
                                        "Global Unicast (2000::/3)"]))
        self.assertGreater(2 + lang_max, GRENZE)


if __name__ == "__main__":
    unittest.main(verbosity=1)
