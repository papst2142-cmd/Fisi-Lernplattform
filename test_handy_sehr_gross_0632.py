#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests fuer 0.63.2, Bauer S2d (Handy, Schrift "Sehr gross"):
  * B-E-05 (a) Ringe wachsen mit der Schrift (ui.Ring, grow), das Logo nicht;
    die Ringkarten der Startseite passen bei 384 dp nebeneinander;
    Nacharbeit M1: Ring und Rand nach der echten Breite (360 und 384 dp)
  * B-E-05 (b) Brotkrumen: Abstand rechts vor dem Hilfe-Symbol, Umbruch
  * B-E-05 (c) FoldCard: Abstand zwischen Titel und "aufklappen"
  * B-E-05 (d) Kacheln nebeneinander gleich hoch (Fortschritt, Startseite)
  * B-E-05 (e) Unterschrift unter dem Titel (Sehr gross), Platzhalter
    zweizeilig, letztes Wort im Banner nicht allein
  * B-E-05 (f) AP-Liste: Suchfeld ueber die volle Breite (STRETCH)
  * B-E-09 Schutz: Farbtiefe-Pillen brechen um (kein Selbst-Scrollen)

Die Flet-Steuerelemente werden nur aufgebaut, nicht angezeigt (kein Display
noetig). Vorher einmal: python mobile/vorbereiten.py
Start:  python test_handy_sehr_gross_0632.py
"""

import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

_TMP = tempfile.mkdtemp(prefix="fisi_sehr_gross_")
os.environ["FISI_DB_PATH"] = os.path.join(_TMP, "handy.db")
os.environ.setdefault("FISI_SELFTEST", os.path.join(_TMP, "selbsttest.log"))

import fisi_core as fc  # noqa: E402

sys.path.insert(1, os.path.join(HERE, "mobile", "src"))
import flet as ft  # noqa: E402
import main as handy  # noqa: E402
import ui  # noqa: E402

SEHR_GROSS = 1.3
# Innenbreite einer Ringkarte bei 384 dp: (384 - 2 x 16 - 12) / 2 - 2 x 1 Rahmen
RING_KARTE_INNEN = 168


def _walk(control, found=None):
    found = [] if found is None else found
    found.append(control)
    for name in ("content", "controls"):
        child = getattr(control, name, None)
        for item in child if isinstance(child, list) else [child]:
            if item is not None and hasattr(item, "__dict__"):
                _walk(item, found)
    return found


class _App:
    def __init__(self):
        self.db = fc.DBManager(os.path.join(tempfile.mkdtemp(dir=_TMP), "t.db"))
        self.sync = None

    def toast(self, *_args, **_kwargs):
        pass

    def start_review(self):
        pass


class _Faktor(unittest.TestCase):
    faktor = SEHR_GROSS

    def setUp(self):
        ui.set_font_factor(self.faktor)

    def tearDown(self):
        ui.set_font_factor(1.0)


def _seite_links(left):
    return left.left if isinstance(left, ft.Padding) else left


class RingTest(_Faktor):
    """B-E-05 (a)"""

    def test_ring_waechst_mit_der_schrift(self):
        ring = ui.Ring(size=112)
        self.assertEqual(ring.size, ui.grow(112))
        self.assertEqual(ring.size, 146)
        self.assertEqual(ring.canvas.width, 146)
        self.assertEqual(ring.width, 146)
        klein = ui.Ring(size=74, thickness=7, big_size=14, small_size=1)
        self.assertEqual(klein.size, ui.grow(74))

    def test_logo_bleibt_fest(self):
        logo = ui.Ring(size=30, thickness=4, big_size=1, small_size=1, mitwachsen=False)
        self.assertEqual(logo.size, 30)
        app = handy.FISIMobileApp.__new__(handy.FISIMobileApp)
        app.crumb_main, app.crumb_sub = ft.Text("DASHBOARD"), ft.Text("HOME")
        app.lbl_version = ft.Text("Version")
        bar = app._appbar(root=True)
        logo = bar.leading.content
        self.assertIsInstance(logo, ui.Ring)
        self.assertEqual((logo.size, logo.canvas.width, logo.width), (30, 30, 30))
        # Startseite: Krumen und Version untereinander, Krumen brechen um
        spalte = bar.title.content
        self.assertTrue(spalte.controls[0].wrap)
        self.assertIs(spalte.controls[1], app.lbl_version)

    def test_ringkarten_passen_nebeneinander(self):
        screen = handy.DashboardScreen(_App())
        for ring in (screen.ring_cards, screen.ring_quiz, screen.ring_ap1, screen.ring_scen):
            self.assertEqual(ring.size, ui.grow(112))
            karte = [c for c in _walk(screen.root) if isinstance(c, ui.Card)
                     and ring in _walk(c)][0]
            seite = karte.padding.left
            self.assertLessEqual(ring.size + 2 * seite, RING_KARTE_INNEN)
            self.assertGreaterEqual(seite, 6)


class _Seite:
    def __init__(self, width):
        self.width = width


class _Ereignis:
    def __init__(self, width, height=200):
        self.width, self.height = width, height


def _ringkarte(screen, ring):
    return [c for c in _walk(screen.root) if isinstance(c, ui.Card) and ring in _walk(c)][0]


def _innen(breite):
    """Innenbreite einer Ringkarte ohne Rahmen bei dieser Handybreite (dp)."""
    return int((breite - 2 * 16 - 12) // 2) - 2


class RingBreiteTest(unittest.TestCase):
    """Nacharbeit M1 (Gegenpruefung): Der Ring passt bei 360 und 384 dp und
    Normal/Gross/Sehr gross in die Karte; bei 384 dp bleibt alles wie gebaut."""

    GEBAUT_384 = {1.0: (112, 14), 1.15: (129, 14), 1.3: (146, 11)}

    def tearDown(self):
        ui.set_font_factor(1.0)

    def _screen(self, faktor, breite):
        ui.set_font_factor(faktor)
        app = _App()
        app.page = _Seite(breite)
        return handy.DashboardScreen(app)

    def _passt(self, screen, inner, text):
        for ring in (screen.ring_cards, screen.ring_quiz, screen.ring_ap1, screen.ring_scen):
            karte = _ringkarte(screen, ring)
            seite = karte.padding.left
            self.assertEqual(karte.padding.right, seite, text)
            self.assertLessEqual(ring.size + 2 * seite, inner, text)
            self.assertGreaterEqual(seite, 6, text)
            self.assertEqual((ring.width, ring.canvas.width, ring.canvas.height),
                             (ring.size, ring.size, ring.size), text)

    def test_360_passt(self):
        self.assertEqual(_innen(360), 156)
        for faktor in (1.0, 1.15, 1.3):
            with self.subTest(faktor=faktor):
                self._passt(self._screen(faktor, 360), _innen(360), "360 dp, %s" % faktor)

    def test_384_passt_und_unveraendert(self):
        self.assertEqual(_innen(384), 168)
        for faktor, (groesse, seite) in self.GEBAUT_384.items():
            with self.subTest(faktor=faktor):
                screen = self._screen(faktor, 384)
                self._passt(screen, _innen(384), "384 dp, %s" % faktor)
                karte = _ringkarte(screen, screen.ring_cards)
                self.assertEqual((screen.ring_cards.size, karte.padding.left), (groesse, seite))

    def test_echte_kartenbreite(self):
        """Erst nach dem Zeichnen bekannte Breite (on_size_change der Karte)."""
        screen = self._screen(1.3, 384)
        screen.ring_cards.set(0.5, "#ff0000", "#00ff00", "50 %", "x")
        karte = _ringkarte(screen, screen.ring_cards)
        karte.on_size_change(_Ereignis(_innen(360) + 2))
        ring = screen.ring_cards
        self._passt_eine(ring, karte, _innen(360))
        self.assertEqual(ring.canvas.shapes[0].x, ring.size / 2)
        self.assertEqual(ring.big.value, "50 %")
        # wieder breiter: zurueck auf die gebaute Groesse bei 384 dp
        karte.on_size_change(_Ereignis(_innen(384) + 2))
        self.assertEqual((ring.size, karte.padding.left), (146, 11))

    def _passt_eine(self, ring, karte, inner):
        self.assertLessEqual(ring.size + 2 * karte.padding.left, inner)
        self.assertEqual((ring.width, ring.canvas.width, ring.center.width),
                         (ring.size, ring.size, ring.size))


class RingNormalTest(_Faktor):
    """B-E-05 (a): bei Normal bleibt alles wie bisher."""
    faktor = 1.0

    def test_normal_unveraendert(self):
        self.assertEqual(ui.Ring(size=112).size, 112)
        screen = handy.DashboardScreen(_App())
        karte = [c for c in _walk(screen.root) if isinstance(c, ui.Card)
                 and screen.ring_cards in _walk(c)][0]
        self.assertEqual((karte.padding.left, karte.padding.right, karte.padding.top,
                          karte.padding.bottom), (14, 14, 14, 14))


class KopfzeileTest(_Faktor):
    """B-E-05 (b)"""

    def test_brotkrumen_abstand_und_umbruch(self):
        app = handy.FISIMobileApp.__new__(handy.FISIMobileApp)
        bar = app._appbar(root=False, crumbs=("LERNEN", "ABSCHLUSSPROJEKT"))
        self.assertIsInstance(bar.title, ft.Container)
        # sichtbar: Rand rechts + 12 Innenrand des Hilfe-Knopfs
        self.assertGreaterEqual(bar.title.padding.right, 12)
        reihe = bar.title.content
        self.assertIsInstance(reihe, ft.Row)
        self.assertTrue(reihe.wrap)
        self.assertEqual([t.value for t in reihe.controls], ["LERNEN", "/", "ABSCHLUSSPROJEKT"])

    def test_startseite_abstand_rechts(self):
        """Nacharbeit L2: auch die Startseite (Krumen + Version, root=True) hat
        den Abstand rechts vor dem Hilfe-Symbol."""
        app = handy.FISIMobileApp.__new__(handy.FISIMobileApp)
        app.crumb_main, app.crumb_sub = ft.Text("DASHBOARD"), ft.Text("HOME")
        app.lbl_version = ft.Text("Version")
        bar = app._appbar(root=True)
        self.assertIsInstance(bar.title, ft.Container)
        self.assertIsNotNone(bar.title.padding)
        self.assertGreaterEqual(bar.title.padding.right, 12)
        self.assertTrue(bar.title.content.controls[0].wrap)


class FoldCardTest(_Faktor):
    """B-E-05 (c)"""

    def _abstand(self, card):
        header = card.header_button.content
        aktion = header.controls[-1]
        self.assertIsInstance(header.controls[-2], ft.Column)
        return header.spacing + aktion.padding.left

    def test_abstand_vor_aufklappen(self):
        hilfe = ui.FoldCard("Rechner (Subnetting, RAID, Bildschirm, USV)", [ft.Text("x")],
                            key="t_hilfe", marker=True)
        # Nacharbeit L2: Schwelle = gebauter Wert (marker: 6 + 8, sonst 8 + 8);
        # vorher ">= 12" liess ACTION_GAP = 6 durch
        self.assertGreaterEqual(self._abstand(hilfe), 14)
        optionen = ui.FoldCard("Farben", [ft.Text("x")], key="t_farben", subtitle="Akzent")
        self.assertGreaterEqual(self._abstand(optionen), 16)
        hilfe.toggle()
        self.assertTrue(hilfe.body.visible)


class GleichHochTest(_Faktor):
    """B-E-05 (d)"""

    def _gleich(self, reihe):
        self.assertTrue(reihe.intrinsic_height)
        self.assertEqual(reihe.vertical_alignment, ft.CrossAxisAlignment.STRETCH)

    def test_fortschritt_kacheln(self):
        screen = handy.ProgressScreen(_App())
        reihe = screen.root.controls[0]
        self.assertEqual(len(reihe.controls), 2)
        self._gleich(reihe)

    def test_startseite_ringkarten(self):
        screen = handy.DashboardScreen(_App())
        reihen = [c for c in screen.root.controls if isinstance(c, ft.Row)
                  and any(screen.ring_cards in _walk(k) or screen.ring_ap1 in _walk(k)
                          for k in c.controls)]
        self.assertEqual(len(reihen), 2)
        for reihe in reihen:
            self._gleich(reihe)


class EinzelwortTest(_Faktor):
    """B-E-05 (e)"""

    def test_unterschrift_unter_dem_titel(self):
        card = ui.Card("Projekt", [ft.Text("x")],
                       subtitle="Dein IHK-Projekt vom Antrag bis zum Fachgespräch")
        header = card.content.controls[0]
        spalte = header.controls[1]
        self.assertIsInstance(spalte, ft.Column)
        self.assertEqual(spalte.controls, [card.title_text, card.subtitle_text])
        self.assertIsNone(card.subtitle_text.expand)
        self.assertEqual(card.subtitle_text.text_align, ft.TextAlign.LEFT)
        card.set_subtitle("IPv6")
        self.assertIsNone(card.subtitle_text.expand)
        self.assertTrue(card.subtitle_text.visible)
        ohne = ui.Card("Stand", [ft.Text("x")])
        self.assertFalse(ohne.subtitle_text.visible)

    def test_platzhalter_bricht_um(self):
        feld = ui.entry(hint=fc.NOTEBOOK_SEARCH_HINT)
        self.assertGreaterEqual(feld.hint_max_lines, 2)

    def test_banner_letztes_wort_nicht_allein(self):
        text = "Lernserie: 0 Tage  ·  Prüfungstrainer 0 % richtig"
        banner = ui.HeroPanel()
        banner.set_data("Dein Lernstand", text, "0 %", "Gesamtfortschritt")
        self.assertTrue(banner.sub.value.endswith("Prüfungstrainer 0 % richtig"))
        self.assertEqual(banner.sub.value.replace(" ", " "), text)


class EinzelwortNormalTest(_Faktor):
    """B-E-05 (e): bei Normal (und Gross) bleiben Titel und Unterschrift nebeneinander."""
    faktor = 1.15

    def test_nebeneinander(self):
        card = ui.Card("Projekt", [ft.Text("x")], subtitle="Kurz")
        header = card.content.controls[0]
        self.assertEqual(header.controls[1:3], [card.title_text, card.subtitle_text])
        self.assertEqual((card.title_text.expand, card.subtitle_text.expand), (3, 2))


class ApSucheTest(_Faktor):
    """B-E-05 (f)"""

    def test_suchfeld_volle_breite(self):
        box = handy.PagedListBox([], lambda _i: None, "", lambda: {})
        self.assertEqual(box.root.horizontal_alignment, ft.CrossAxisAlignment.STRETCH)
        self.assertIsInstance(box.root.controls[0], ft.TextField)


class FarbtiefeTest(_Faktor):
    """B-E-09 (Schutz): Die Farbtiefe-Pillen brechen um, ohne ShaderMask und
    Selbst-Scrollen - dort lag der Versatz des Bedienrahmens."""
    faktor = 1.15

    def test_umbrechend(self):
        screen = handy.CalcScreen.__new__(handy.CalcScreen)
        screen.toasts = []
        screen.toast = lambda text, color=None: screen.toasts.append(text)
        screen.app = _App()
        screen.app.scroll_top = lambda: None
        screen.build()
        self.assertIs(screen.depth_pills.umbrechen, True)
        self.assertIsNone(screen.depth_pills.mask)


if __name__ == "__main__":
    unittest.main(verbosity=1)
