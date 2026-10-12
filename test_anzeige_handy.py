# -*- coding: utf-8 -*-
"""
Tests 0.63 "Anzeige Handy" (B-E-01, B-E-02, Leer-Zustand USV-Bild fuer B-D-04)
==============================================================================

Nur mobile/src/ui.py, ohne Seite und ohne Geraet:
  * fit_lines(text, zeichen): Zeile "Beschriftung : Wert", die nicht passt,
    wird zu "Beschriftung:" und darunter "  Wert" (F-8 b). Werte nie geteilt.
    Beispiele aus dem Beleg e_calc_ergebnisfeld.md (192.168.10.0/26,
    RAID 5 4 x 4000 GB, 7680 x 4320 / 32 Bit / 240 fps, USV 12500 W 45 min).
  * read_box(..., fit=True): Kasten bleibt seitlich wischbar (Kriterium wie
    test_rechenweg.py Test 6), misst seine Breite, setzt den Text mit
    fit_lines; ist eine Zeile laenger als der Kasten: Hinweis "→ wischen"
    unter dem Kasten (ausserhalb box.content) und Verlauf rechts.
  * PillGroup(..., umbrechen=True): Row mit wrap, ohne feste Hoehe, ohne Pfeil.
  * UpsPicture.set_picture(None): Leer-Zustand statt Fehler.

Aufruf: python test_anzeige_handy.py
"""

import os
import sys
import types
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(1, os.path.join(HERE, "mobile", "src"))

import flet as ft  # noqa: E402

import fisi_core as fc  # noqa: E402
import ui  # noqa: E402

USV_FELDER = dict(fc.UPS_FIELD_DEFAULTS, last="12500", minuten="45")


def beispiele():
    """Die Ergebnis-Texte aus dem Befund B-E-01 (wie am Handy angezeigt)."""
    usv = fc.ups_calculate("empfehlung", USV_FELDER, "W")["text"]
    usv = usv.partition("\n\n" + fc.UPS_SIMPLE_TEXT)[0]   # wie main.py calc_ups
    return {
        "subnetz": fc.subnet_report("192.168.10.0/26"),
        "ipv6": fc.subnet_report("2001:db8:85a3::8a2e:370:7334/64"),
        "raid": fc.raid_report("RAID 5", "4", "4000"),
        "bild": fc.screen_report("7680", "4320", "32", "240"),
        "usv": usv,
    }


def werte(text):
    """Alle Werte (Teil hinter ": ") eines Ergebnis-Textes."""
    found = []
    for line in text.split("\n"):
        pos = line.find(": ")
        if pos >= 0 and line[pos + 2:].strip():
            found.append(line[pos + 2:].strip())
    return found


class FitLinesTest(unittest.TestCase):

    def test_ohne_breite_unveraendert(self):
        for text in beispiele().values():
            self.assertEqual(ui.fit_lines(text, None), text)
            self.assertEqual(ui.fit_lines(text, 0), text)
            self.assertEqual(ui.fit_lines(text, 200), text)
        self.assertEqual(ui.fit_lines("", 10), "")

    def test_subnetz_192_168_10_0_26(self):
        text = beispiele()["subnetz"]
        # 36 Zeichen: so viel war im Befund bei 384 px, Schrift Normal zu sehen
        # ("192.168.10.6" mit halber 6, e_calc_ergebnisfeld.md)
        neu = ui.fit_lines(text, 36).split("\n")
        self.assertIn("Broadcast-Adresse:", neu)
        self.assertEqual(neu[neu.index("Broadcast-Adresse:") + 1], "  192.168.10.63")
        self.assertEqual(neu[neu.index("Letzte Host-Adresse:") + 1], "  192.168.10.62")
        self.assertEqual(neu[neu.index("Subnetzmaske:") + 1], "  255.255.255.192")
        # was passt, bleibt in der Spalte
        self.assertIn("Netzadresse           : 192.168.10.0", neu)
        self.assertTrue(all(len(line) <= 36 for line in neu), neu)
        # der Befund: nirgends ein angeschnittener, plausibler Wert
        for line in neu:
            self.assertFalse(line.endswith("192.168.10.6"), line)
            self.assertFalse(line.endswith("255.255.255."), line)

    def test_raid_4_x_4000(self):
        neu = ui.fit_lines(beispiele()["raid"], 20).split("\n")
        self.assertEqual(neu[neu.index("Festplatten:") + 1], "  4 x 4.000 GB")
        self.assertEqual(neu[neu.index("Nutzkapazität:") + 1], "  12.000,00 GB")
        self.assertTrue(all(len(line) <= 20 for line in neu), neu)

    def test_bild_7680_x_4320(self):
        neu = ui.fit_lines(beispiele()["bild"], 24).split("\n")
        self.assertEqual(neu[neu.index("Auflösung:") + 1], "  7680 x 4320 Pixel")
        # Folgezeilen (Byte, KiB, MiB) ruecken mit unter die Beschriftung
        start = neu.index("Datenmenge pro Bild:")
        self.assertEqual(neu[start + 1:start + 5],
                         ["  1.061.683.200 Bit", "  132.710.400 Byte",
                          "  129.600,00 KiB", "  126,56 MiB"])
        self.assertNotIn("7680 x 43", "\n".join(neu).replace("7680 x 4320", ""))
        self.assertTrue(all(len(line) <= 24 for line in neu), neu)
        # 38 Zeichen: Kopfzeile (41) passt nicht, die Folgezeile "126,56 MiB"
        # (34) passt - sie rueckt trotzdem mit, damit der Block zusammenbleibt
        neu = ui.fit_lines(beispiele()["bild"], 38).split("\n")
        start = neu.index("Datenmenge pro Bild:")
        self.assertEqual(neu[start + 4], "  126,56 MiB")
        self.assertIn("Pixel gesamt          : 33.177.600", neu)

    def test_usv_12500_w(self):
        neu = ui.fit_lines(beispiele()["usv"], 28).split("\n")
        self.assertEqual(neu[neu.index("Last:") + 1],
                         "  12.500 W / 13.889 VA (Leistungsfaktor 0,9)")
        # eingerueckte Zeilen behalten ihren Einzug
        self.assertIn("  nein  Auslastung Wirkleistung:", neu)
        self.assertIn("    12.500 W von 900 W = 1.388,9 %", neu)
        # zu lang auch allein: bleibt ganz (dann zeigt der Kasten "→ wischen")
        self.assertTrue(any(len(line) > 28 for line in neu))

    def test_kein_wert_geteilt_jede_zeile_passt_oder_hinweis(self):
        """Fuer jede Breite 6..70: jeder Wert steht ganz in einer Zeile, die
        Zeilen ohne Beschriftung bleiben gleich, und jede Zeile ist hoechstens
        so lang wie der Kasten - sonst ist sie ein einzelner Wert, der auch
        allein nicht passt (dann muss der Hinweis an sein, FitBoxTest)."""
        for name, text in beispiele().items():
            alt = text.split("\n")
            for zeichen in range(6, 71):
                neu = ui.fit_lines(text, zeichen).split("\n")
                rest = list(neu)
                for wert in werte(text):
                    treffer = [line for line in rest if line.endswith(wert)]
                    self.assertTrue(treffer, (name, zeichen, wert))
                    rest.remove(treffer[0])
                for line in neu:
                    if len(line) <= zeichen:
                        continue
                    stripped = line.strip()
                    self.assertTrue(
                        stripped in werte(text) or line in alt
                        or stripped.endswith(":"),
                        (name, zeichen, line))
                # nichts geht verloren, nichts kommt hinzu (ausser Umbruch/Einzug)
                self.assertEqual("".join("".join(neu).split()).replace(":", ""),
                                 "".join("".join(alt).split()).replace(":", ""),
                                 (name, zeichen))


class SatzTest(unittest.TestCase):
    """Festlegung Hauptsitzung: reiner Satz bricht an Leerzeichen um."""

    PLATZHALTER = "Noch keine Berechnung durchgeführt."

    def test_platzhalter_zweizeilig(self):
        # 32 Zeichen: Gross, 384 px (Platzhalter hat 35 Zeichen)
        self.assertEqual(ui.fit_lines(self.PLATZHALTER, 32),
                         "Noch keine Berechnung\ndurchgeführt.")
        self.assertEqual(ui.fit_lines(self.PLATZHALTER, 35), self.PLATZHALTER)
        self.assertEqual(ui.fit_lines(self.PLATZHALTER, None), self.PLATZHALTER)

    def test_woerter_nie_geteilt(self):
        for zeichen in range(1, 40):
            zeilen = ui.fit_lines(self.PLATZHALTER, zeichen).split("\n")
            self.assertEqual(" ".join(zeilen), self.PLATZHALTER, zeichen)
            for zeile in zeilen:
                self.assertTrue(len(zeile) <= zeichen or " " not in zeile, (zeichen, zeile))

    def test_spalten_und_werte_bleiben(self):
        tabelle = "Netz            Hosts   Maske"
        self.assertEqual(ui.fit_lines(tabelle, 10), tabelle)
        self.assertEqual(ui.fit_lines("2001:db8:85a3:0:ffff:ffff:ffff:ffff", 10),
                         "2001:db8:85a3:0:ffff:ffff:ffff:ffff")

    def test_kasten_vor_dem_ersten_rechnen_ohne_hinweis(self):
        box = ui.read_box(self.PLATZHALTER, mono=True, scroll=True, fit=True)
        box._box_sized(types.SimpleNamespace(width=294 + 30))
        box._text_sized(types.SimpleNamespace(width=9.0 * 35))   # Gross: 9 px
        self.assertEqual(box.zeichen, 32)
        self.assertEqual(box.data.value, "Noch keine Berechnung\ndurchgeführt.")
        self.assertFalse(box.hint.visible)
        self.assertIsNone(box.box.foreground_decoration)


class FitBoxTest(unittest.TestCase):

    @staticmethod
    def _wischbar(box):
        # dasselbe Kriterium wie test_rechenweg.py BoxTest._wischbar (Test 6)
        return (isinstance(box.content, ft.Row) and box.content.scroll is not None
                and box.data is box.content.controls[0] and box.data.no_wrap)

    def _box(self, text, breite=None, zeichenbreite=None):
        box = ui.read_box("Noch keine Berechnung durchgeführt.", mono=True,
                          scroll=True, fit=True)
        calls = []
        box.update = lambda: calls.append("update")
        ui.set_box(box, text)
        if breite:
            box._box_sized(types.SimpleNamespace(width=breite))
        if zeichenbreite:
            longest = max(len(line) for line in box.data.value.split("\n"))
            box._text_sized(types.SimpleNamespace(width=zeichenbreite * longest))
        self.assertEqual(calls, [], "im Ereignis kein eigenes update() (ui.py PillGroup)")
        return box

    def test_alter_aufruf_unveraendert(self):
        box = ui.read_box("x", mono=True, scroll=True)
        self.assertIsInstance(box, ft.Container)
        self.assertTrue(self._wischbar(box))
        plain = ui.read_box("x")
        self.assertIs(plain.content, plain.data)
        ui.set_box(box, "neu")
        self.assertEqual(box.data.value, "neu")

    def test_wischbar_und_hinweis_ausserhalb(self):
        box = self._box(beispiele()["usv"], breite=324)
        self.assertTrue(self._wischbar(box))
        # der sichtbare Kasten ist genau diese Row
        self.assertIs(box.box.content, box.content)
        self.assertIs(box.box.data, box.data)
        # Hinweis unter dem Kasten, nicht in box.content
        self.assertEqual(box.controls, [box.box, box.hint])
        self.assertNotIn(box.hint, box.content.controls)
        self.assertEqual(box.hint.value, "→ wischen")

    def test_ohne_breite_text_unveraendert_kein_hinweis(self):
        text = beispiele()["subnetz"]
        box = self._box(text)
        self.assertEqual(box.data.value, text)
        self.assertFalse(box.hint.visible)
        self.assertIsNone(box.box.foreground_decoration)

    def test_breite_misst_und_setzt_um(self):
        text = beispiele()["subnetz"]
        # 384 px Normal laut Befund: innen gut 36 Zeichen zu 7,83 px (DejaVu
        # Sans Mono 13 px); Kasten = innen + 2 x (14 Rand + 1 Linie)
        box = self._box(text, breite=286 + 30, zeichenbreite=7.83)
        self.assertEqual(box.zeichen, 36)
        self.assertIn("Broadcast-Adresse:\n  192.168.10.63", box.data.value)
        self.assertFalse(box.hint.visible)
        self.assertIsNone(box.box.foreground_decoration)
        # neuer Wert ueber set_box: im selben Modus
        ui.set_box(box, fc.raid_report("RAID 5", "4", "4000"))
        self.assertIn("Festplatten           : 4 x 4.000 GB", box.data.value)
        self.assertEqual(box.raw, fc.raid_report("RAID 5", "4", "4000"))
        # leer (B-D-04, Kasten nach Fehler leer): kein Hinweis
        ui.set_box(box, "")
        self.assertEqual(box.data.value, "")
        self.assertFalse(box.hint.visible)

    def test_zeile_zu_lang_hinweis_und_verlauf(self):
        alt = ui.FONT_FACTOR[0]
        ui.set_font_factor(1.3)          # Sehr gross
        try:
            box = self._box(beispiele()["ipv6"], breite=324, zeichenbreite=7.83 * 1.3)
        finally:
            ui.set_font_factor(alt)
        self.assertEqual(box.zeichen, 28)
        self.assertIn("Letzte Adresse:\n  2001:db8:85a3:0:ffff:ffff:ffff:ffff",
                      box.data.value)
        self.assertTrue(box.hint.visible)
        verlauf = box.box.foreground_decoration
        self.assertIsNotNone(verlauf)
        # Verlauf endet am Rand der Schrift (324 - 14 Rand - 1 Linie), beginnt
        # 28 px davor; die Linie des Kastens wird darueber neu gezogen
        self.assertEqual([round(stop, 3) for stop in verlauf.gradient.stops],
                         [0.0, round(281 / 324, 3), round(309 / 324, 3), 1.0])
        self.assertEqual(verlauf.border, box.box.border)

    def test_kein_wert_geteilt_jede_zeile_passt_oder_hinweis(self):
        for name, text in beispiele().items():
            for breite in range(150, 461, 7):
                box = self._box(text, breite=breite, zeichenbreite=7.83)
                zeilen = box.data.value.split("\n")
                passt = all(len(line) <= box.zeichen for line in zeilen)
                self.assertEqual(box.hint.visible, not passt, (name, breite))
                self.assertEqual(box.box.foreground_decoration is not None, not passt)
                for wert in werte(text):
                    self.assertTrue(any(line.endswith(wert) for line in zeilen),
                                    (name, breite, wert))

    def test_schaetzung_vor_messung_eher_knapp(self):
        # Vor der Textmessung: Schaetzung 0,62 je Schriftgroesse, nie mehr
        # Zeichen als mit der echten Breite (7,83 px bei 13 px)
        box = self._box(beispiele()["subnetz"], breite=324)
        self.assertLessEqual(box.zeichen, int(294 / 7.83))


class PillGroupTest(unittest.TestCase):

    OPTIONEN = [(level, level) for level in fc.RAID_LEVELS]

    def test_umbrechend(self):
        pills = ui.PillGroup(self.OPTIONEN, initial=2, umbrechen=True)
        self.assertTrue(pills.row.wrap)
        self.assertGreater(pills.row.run_spacing or 0, 0)
        self.assertIsNone(pills.row.scroll)
        self.assertIsNone(pills.height)
        self.assertEqual(pills.controls, [pills.row])
        self.assertIsNone(pills.hint)
        # jede Pille in einer eigenen engen Zeile (tight): nur so breit wie
        # ihre Beschriftung. Direkt im Umbruch fuellte sie wegen alignment
        # die ganze Zeile (im Browser gesehen: 5 Zeilen zu je 318 px bei 384 px)
        self.assertEqual([item.controls for item in pills.row.controls],
                         [[sem] for sem in pills.semantics])
        self.assertTrue(all(item.tight for item in pills.row.controls))
        for sem, pill in zip(pills.semantics, pills.pills):
            self.assertIs(sem.content, pill)
            self.assertEqual(pill.height, ui.grow(36))     # Pille selbst wie bisher
        self.assertEqual([item.selected for item in pills.semantics],
                         [False, False, True, False, False])
        self.assertTrue(all(item.button for item in pills.semantics))
        seen = []
        pills.on_select = seen.append
        pills.select(4)
        self.assertEqual(seen, ["RAID 10"])
        self.assertEqual(pills.get(), "RAID 10")
        self.assertEqual([item.selected for item in pills.semantics],
                         [False, False, False, False, True])
        pills.select_value("RAID 1", notify=False)
        self.assertEqual(pills.get(), "RAID 1")

    def test_standard_unveraendert(self):
        pills = ui.PillGroup(self.OPTIONEN, initial=2)
        self.assertFalse(pills.row.wrap)
        self.assertEqual(pills.row.scroll, ft.ScrollMode.HIDDEN)
        self.assertEqual(pills.height, ui.grow(36))
        self.assertEqual(pills.controls, [pills.mask, pills.hint])
        self.assertEqual(pills.hint.tooltip, "Weitere Einträge")


class UpsPictureTest(unittest.TestCase):

    def test_leer_zustand(self):
        bild = ui.UpsPicture()
        result = fc.ups_calculate("empfehlung", USV_FELDER, "W")
        bild.set_picture(result["bild"], "Zusammenfassung")
        self.assertTrue(bild.column.controls)
        bild.set_picture(None)
        self.assertEqual(bild.column.controls, [])
        self.assertEqual(bild.label, "")
        ui.UpsPicture().set_picture(None)


if __name__ == "__main__":
    unittest.main(verbosity=2)
