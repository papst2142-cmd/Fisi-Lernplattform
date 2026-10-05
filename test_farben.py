#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests fuer die eigenen Farben mit Reglern (ab 0.57, Plan Abschnitt 1):
  * Bestandsschutz: ohne eigene Farben sind alle 72 Farbwelten (2 Darstellungen
    x 6 Hintergruende x 6 Grundfarben) Wert fuer Wert wie in 0.56
  * Ableitung: Knopfverlauf = Akzent 1/2, zweiter Verlauf und Banner dunkler,
    Flaechen-Stufen, Schrift hell/dunkel nach Helligkeit des Hintergrunds
  * Kontrastberechnung und Warnhinweis mit Messwert
  * Rueckfall bei ungueltigen oder beschaedigten Werten, nie ein Absturz
  * Speichern und Laden je Darstellung, Zuruecksetzen, Kachel ersetzt
  * Abgleich (Format 2) und Sicherung enthalten die Farben nicht
  * Spielweltkarte folgt den eigenen Farben, hell mit Mindestkontrast
  * gleiche Beschriftungen PC und Handy, Regler per Tastatur (PC) und mit
    TalkBack-Beschriftung (Handy)

Datenbank und Einstellungen liegen in einem Temp-Ordner (FISI_DB_PATH).
Start:  python test_farben.py   (Teile mit Oberflaeche brauchen ein Display)
"""

import hashlib
import importlib
import json
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

_TMP = tempfile.mkdtemp(prefix="fisi_farben_")
os.environ["FISI_DB_PATH"] = os.path.join(_TMP, "farben.db")
os.environ.setdefault("FISI_SELFTEST", os.path.join(_TMP, "selbsttest.log"))

import fisi_theme as th  # noqa: E402
import fisi_game as fg  # noqa: E402
import fisi_update  # noqa: E402

SETTINGS = os.path.join(_TMP, "einstellungen.json")

# Pruefsumme aller 72 Farbwelten (C, Verlaeufe, Kartenfarben, hell/dunkel,
# Fachbereichsfarben), berechnet mit dem Stand 0.56 (main 4b8a59a). Ab 0.57
# (Entscheidung Nico F2) ist die dunkle Karte absichtlich nachgeregelt: von ihr
# zaehlen nur die unveraenderten Werte DUNKEL_KARTE_GLEICH mit, alles andere
# (Oberflaeche, Verlaeufe, helle Karte) muss Wert fuer Wert gleich bleiben.
STAND_056 = "852fee5c3621e0cd869a25ec3dc48c27201b5fc78d2419c946f7447712a08784"
DUNKEL_KARTE_GLEICH = ("boden", "park", "schatten", "licht", "fenster", "schild")

# Test-Farbsaetze (wie im Bericht 0.57)
SONNENUNTERGANG = {"akzent1": (20, 90, 42), "akzent2": (345, 80, 45),
                   "hintergrund": (220, 40, 12)}
MINT = {"akzent1": (160, 70, 28), "akzent2": (205, 80, 38), "hintergrund": (150, 30, 94)}
GRAPHIT = {"akzent1": (200, 25, 38), "akzent2": (0, 0, 35), "hintergrund": (0, 0, 10)}
NEON = {"akzent1": (280, 90, 40), "akzent2": (320, 90, 40), "hintergrund": (120, 100, 50)}
UNLESBAR = {"akzent1": (60, 100, 80), "akzent2": (180, 100, 85), "hintergrund": (0, 0, 50)}
LESBAR = (SONNENUNTERGANG, MINT, GRAPHIT, NEON)


def _tk_ok():
    try:
        import tkinter
        root = tkinter.Tk()
        root.destroy()
        return True
    except Exception:  # noqa: BLE001
        return False


def _flet_ok():
    try:
        import flet
        return bool(flet)
    except Exception:  # noqa: BLE001
        return False


def _reset():
    th.custom_colors.clear()
    th.apply_mode(th.MODE_DARK)
    th.apply_background(th.DEFAULT_BACKGROUND)
    th.apply_preset(th.DEFAULT_PRESET)
    try:
        os.remove(SETTINGS)
    except OSError:
        pass


def _map_of(palette):
    with th.preview_colors(palette):
        return fg.map_palette()


def _map_ohne_nachregelung():
    colors = fg.map_palette()
    if th.light:
        return colors
    return {key: colors[key] for key in DUNKEL_KARTE_GLEICH}


class BestandsschutzTest(unittest.TestCase):
    """Wer nichts einstellt, sieht keinen Unterschied."""

    def tearDown(self):
        _reset()

    def test_alle_farbwelten_wie_in_056(self):
        snapshot = {}
        for mode in th.MODE_IDS:
            for back in th.BACKGROUND_IDS:
                for preset in th.PRESET_IDS:
                    th.apply_mode(mode)
                    th.apply_background(back)
                    th.apply_preset(preset)
                    snapshot["%s/%s/%s" % (mode, back, preset)] = {
                        "C": dict(th.C),
                        "G": {k: list(v) for k, v in th.GRADIENTS.items()},
                        "map": _map_ohne_nachregelung(), "light": th.light,
                        "cat": {str(k): v for k, v in th.CATEGORY_COLOR.items()}}
        text = json.dumps(json.loads(json.dumps(snapshot, sort_keys=True)), sort_keys=True)
        self.assertEqual(hashlib.sha256(text.encode()).hexdigest(), STAND_056)

    def test_verlaeufe_nach_eigenen_farben_wieder_aus_der_grundfarbe(self):
        th.apply_custom(th.MODE_DARK, SONNENUNTERGANG)
        self.assertNotEqual(th.GRADIENTS["primary"], th.preset("cyan_pink")["primary"])
        th.apply_mode(th.MODE_LIGHT)   # hell hat keine eigenen Farben
        self.assertEqual(th.GRADIENTS["primary"], th.preset("cyan_pink")["primary"])
        self.assertEqual(th.GRADIENTS["accent"], th.preset("cyan_pink")["verlauf"])
        self.assertEqual(th.GRADIENTS["hero"], th.preset("cyan_pink")["hero"])

    def test_startwerte_ohne_warnung(self):
        """Die Regler starten bei der Farbwelt - dort darf keine Warnung stehen."""
        for mode in th.MODE_IDS:
            for back in th.BACKGROUND_IDS:
                for preset in th.PRESET_IDS:
                    th.apply_mode(mode)
                    th.apply_background(back)
                    th.apply_preset(preset)
                    palette = th.custom_palette(th.custom_start(mode))
                    self.assertEqual(palette["light"], mode == th.MODE_LIGHT)
                    self.assertEqual(th.custom_problems(palette, _map_of(palette)), [],
                                     (mode, back, preset))


class SanftTest(unittest.TestCase):
    """Entscheidung Nico (05.10.2026, "Knopfverlauf, sanft"): Solange die
    Regler auf dem Startwert stehen, bleibt alles exakt wie die Farbwelt."""

    def tearDown(self):
        _reset()

    def test_startwert_ist_exakt_die_farbwelt(self):
        for mode in th.MODE_IDS:
            for preset in ("cyan_pink", "orange_gelb"):
                th.apply_mode(mode)
                th.apply_preset(preset)
                th.apply_background("tannengruen")
                before = (dict(th.C), dict(th.GRADIENTS), th.light)
                start = th.custom_start(mode)
                palette = th.values_palette(start, mode)
                self.assertEqual((palette["colors"], palette["gradients"], palette["light"]),
                                 before)
                th.apply_custom(mode, start)
                self.assertEqual((dict(th.C), dict(th.GRADIENTS), th.light), before)
                th.apply_custom(mode, None)

    def test_nach_dem_verschieben_gilt_die_regel(self):
        start = th.custom_start(th.MODE_DARK)
        moved = dict(start, akzent1=(start["akzent1"][0] + 1,) + start["akzent1"][1:])
        palette = th.values_palette(moved, th.MODE_DARK)
        self.assertEqual(palette, th.custom_palette(moved))
        th.apply_custom(th.MODE_DARK, moved)
        self.assertEqual(th.GRADIENTS["primary"][0], th.hsl_to_hex(*moved["akzent1"]))
        self.assertNotEqual(th.C["accent"], "#22D3EE")

    def test_farbwelt_palette_veraendert_nichts(self):
        th.apply_custom(th.MODE_DARK, SONNENUNTERGANG)
        before = (dict(th.C), dict(th.GRADIENTS), th.light, dict(th.custom_colors))
        light = th.farbwelt_palette(th.MODE_LIGHT)
        self.assertTrue(light["light"])
        self.assertEqual((dict(th.C), dict(th.GRADIENTS), th.light, dict(th.custom_colors)),
                         before)


class AbleitungTest(unittest.TestCase):

    def tearDown(self):
        _reset()

    def test_hsl_umrechnung(self):
        self.assertEqual(th.hsl_to_hex(0, 100, 50), "#FF0000")
        self.assertEqual(th.hsl_to_hex(120, 100, 25), "#008000")
        self.assertEqual(th.hsl_to_hex(0, 0, 100), "#FFFFFF")
        self.assertEqual(th.hsl_to_hex(360, 100, 50), "#FF0000")
        for color in ("#7C3AED", "#120A24", "#F4F0FB", "#05875F"):
            again = th.hsl_to_hex(*th.hex_to_hsl(color))
            self.assertLess(max(abs(a - b) for a, b in zip(th.hex_to_rgb(color),
                                                            th.hex_to_rgb(again))), 4)

    def test_knopfverlauf_ist_akzent_1_und_2(self):
        palette = th.custom_palette(SONNENUNTERGANG)
        first, second = (th.hsl_to_hex(*SONNENUNTERGANG[k]) for k in ("akzent1", "akzent2"))
        self.assertEqual(palette["gradients"]["primary"], (first, second))
        self.assertEqual(palette["gradients"]["accent"],
                         (th.darken(first, 0.2), th.darken(second, 0.2)))
        self.assertEqual(palette["gradients"]["hero"],
                         (th.darken(first, 0.4), th.darken(second, 0.4)))
        # Schriftakzente im selben Farbton
        for key, part in (("accent", "akzent1"), ("accent2", "akzent2")):
            hue = th.hex_to_hsl(palette["colors"][key])[0]
            self.assertLessEqual(min(abs(hue - SONNENUNTERGANG[part][0]),
                                     360 - abs(hue - SONNENUNTERGANG[part][0])), 3)

    def test_startwert_trifft_den_knopfverlauf_der_farbwelt(self):
        for preset in th.PRESETS:
            th.apply_preset(preset["id"])
            palette = th.custom_palette(th.custom_start(th.MODE_DARK))
            for ours, theirs in zip(palette["gradients"]["primary"], preset["primary"]):
                self.assertLess(max(abs(a - b) for a, b in zip(th.hex_to_rgb(ours),
                                                                th.hex_to_rgb(theirs))), 4)

    def test_schrift_nach_helligkeit_des_hintergrunds(self):
        dark = th.custom_palette(SONNENUNTERGANG)
        light = th.custom_palette(MINT)
        self.assertFalse(dark["light"])
        self.assertEqual(dark["colors"]["text"], th._DARK_FIXED["text"])
        self.assertTrue(light["light"])
        self.assertEqual(light["colors"]["text"], th.LIGHT_TEXT["text"])
        # Knalliges Gruen: dunkle Schrift gewinnt
        self.assertTrue(th.custom_palette(NEON)["light"])

    def test_flaechen_stufen(self):
        dark = th.custom_palette(SONNENUNTERGANG)["colors"]
        order = [th.luminance(dark[key]) for key in ("sidebar", "bg", "card", "card_alt",
                                                    "card_hi")]
        self.assertEqual(order, sorted(order))
        self.assertGreater(th.luminance(dark["border_hi"]), th.luminance(dark["card_hi"]))
        light = th.custom_palette(MINT)["colors"]
        self.assertGreater(th.luminance(light["card"]), th.luminance(light["bg"]))
        self.assertLess(th.luminance(light["card_hi"]), th.luminance(light["bg"]))
        self.assertLess(th.luminance(light["border_hi"]), th.luminance(light["border"]))
        # gleicher Farbton wie der Regler
        for key in ("card", "card_alt", "border_hi"):
            self.assertLessEqual(abs(th.hex_to_hsl(dark[key])[0] - 220), 3, key)

    def test_alle_schluessel_vorhanden(self):
        palette = th.custom_palette(GRAPHIT)
        self.assertEqual(set(th.C) - set(palette["colors"]), set())
        self.assertEqual(set(("primary", "accent", "hero")), set(palette["gradients"]))

    def test_fachbereiche_bleiben_im_dunklen_fest(self):
        palette = th.custom_palette(SONNENUNTERGANG)
        for key in ("cyan", "pink", "purple", "green", "orange", "blue", "red", "yellow"):
            self.assertEqual(palette["colors"][key], th._DARK_FIXED[key])
        self.assertEqual(th.GRADIENTS["danger"], ("#DC2626", "#BF5811"))
        self.assertEqual(th.GRADIENTS["success"], ("#05875F", "#158293"))

    def test_extreme_ohne_absturz(self):
        for hue in range(0, 360, 45):
            for sat in (0, 100):
                for light in (0, 50, 100):
                    values = {"akzent1": (hue, sat, light), "akzent2": (hue, sat, 100 - light),
                              "hintergrund": (hue, sat, light)}
                    palette = th.custom_palette(values)
                    th.custom_problems(palette, _map_of(palette))
                    for color in palette["colors"].values():
                        self.assertRegex(color, r"^#[0-9A-F]{6}$")


class KontrastTest(unittest.TestCase):

    def tearDown(self):
        _reset()

    def test_lesbare_saetze_ohne_warnung(self):
        for values in LESBAR:
            palette = th.custom_palette(values)
            self.assertEqual(th.custom_problems(palette, _map_of(palette)), [], values)

    def test_unlesbarer_satz_warnt_mit_messwert(self):
        palette = th.custom_palette(UNLESBAR)
        problems = th.custom_problems(palette, _map_of(palette))
        names = [name for name, _value, _target in problems]
        self.assertIn("Knopfschrift auf Akzent 1", names)
        self.assertIn("Fließtext", names)
        # schlechteste zuerst, Messwert stimmt mit der WCAG-Formel
        self.assertEqual(problems[0][0], "Knopfschrift auf Akzent 1")
        self.assertAlmostEqual(problems[0][1], th.contrast(
            "#FFFFFF", th.hsl_to_hex(*UNLESBAR["akzent1"])))
        lines = th.warning_lines(problems)
        self.assertTrue(lines[0].startswith("Knopfschrift auf Akzent 1: 1,0:1 (nötig 4,5:1)"),
                        lines[0])
        self.assertEqual(lines[-1], th.CUSTOM_WARN_MORE % (len(problems) - 4))

    def test_ziele_wie_in_056(self):
        targets = {name: target for name, _v, target in th.custom_checks(
            th.custom_palette(MINT), _map_of(th.custom_palette(MINT)))}
        self.assertEqual(targets["Fließtext"], 4.5)
        self.assertEqual(targets["Rahmen von Eingabefeldern"], 3.0)
        self.assertEqual(targets["Fokusrahmen"], 3.0)
        self.assertEqual(targets["Karte: Straßen"], 3.0)
        self.assertEqual(targets["Karte: Beschriftung"], 4.5)

    def test_zahl_mit_komma(self):
        self.assertEqual(th.format_ratio(4.5), "4,5:1")
        self.assertEqual(th.format_ratio(4.49), "4,4:1")   # abgerundet, nie geschoent
        self.assertEqual(th.format_ratio(21.0), "21,0:1")


class RueckfallTest(unittest.TestCase):

    def tearDown(self):
        _reset()

    def test_ungueltige_werte(self):
        good = {"akzent1": [1, 2, 3], "akzent2": [359, 100, 100], "hintergrund": [0, 0, 0]}
        self.assertEqual(th.valid_custom(good)["akzent2"], (359, 100, 100))
        broken = [None, "rot", [], {}, {"akzent1": [1, 2, 3]},
                  dict(good, akzent1=[360, 0, 0]), dict(good, akzent1=[-1, 0, 0]),
                  dict(good, akzent1=[0, 101, 0]), dict(good, akzent1=[0, 0, "50"]),
                  dict(good, akzent1=[0, 0]), dict(good, akzent1=[0, 0, 0, 0]),
                  dict(good, akzent1=[True, 0, 0]), dict(good, akzent1=[float("nan"), 0, 0]),
                  dict(good, hintergrund="#FFFFFF")]
        for value in broken:
            self.assertIsNone(th.valid_custom(value), value)

    def test_beschaedigte_einstellungen_ergeben_farbwelt(self):
        th.apply_preset("gruen_lime")
        before = dict(th.C)
        for stored in ({"dunkel": {"akzent1": "x"}}, "kaputt", [1, 2], {"dunkel": None},
                       {"dunkel": dict(SONNENUNTERGANG, hintergrund=[0, 0, 500])}):
            with open(SETTINGS, "w", encoding="utf-8") as handle:
                json.dump({th.CUSTOM_KEY: stored}, handle)
            self.assertEqual(th.saved_custom(), {}, stored)
            th.custom_colors.clear()
            th.custom_colors.update(th.saved_custom())
            th.apply_mode(th.MODE_DARK)
            self.assertEqual(th.C, before, stored)

    def test_kaputte_datei_beim_start_kein_absturz(self):
        with open(SETTINGS, "w", encoding="utf-8") as handle:
            handle.write('{"eigene_farben": {"dunkel": {"akzent1": [1, 2')
        try:
            reloaded = importlib.reload(th)
            self.assertEqual(reloaded.custom_colors, {})
            self.assertEqual(reloaded.C["bg"], "#120A24")
        finally:
            os.remove(SETTINGS)
            importlib.reload(th)


class SpeichernTest(unittest.TestCase):

    def tearDown(self):
        _reset()

    def _stored(self):
        with open(SETTINGS, encoding="utf-8") as handle:
            return json.load(handle)

    def test_speichern_und_laden_je_darstellung(self):
        th.save_custom(th.MODE_DARK, SONNENUNTERGANG)
        th.save_custom(th.MODE_LIGHT, MINT)
        stored = self._stored()[th.CUSTOM_KEY]
        self.assertEqual(stored["dunkel"]["akzent1"], [20, 90, 42])
        self.assertEqual(stored["hell"]["hintergrund"], [150, 30, 94])
        self.assertEqual(th.saved_custom(), {"dunkel": SONNENUNTERGANG, "hell": MINT})
        self.assertEqual(th.C["bg"], th.hsl_to_hex(220, 40, 12))
        th.apply_mode(th.MODE_LIGHT)
        self.assertEqual(th.C["bg"], th.hsl_to_hex(150, 30, 94))
        self.assertTrue(th.light)
        # Nach einem Neustart (Import) wieder da
        reloaded = importlib.reload(th)
        try:
            self.assertEqual(reloaded.custom_colors, {"dunkel": SONNENUNTERGANG, "hell": MINT})
        finally:
            importlib.reload(th)

    def test_zuruecksetzen_nur_fuer_diese_darstellung(self):
        th.save_custom(th.MODE_DARK, SONNENUNTERGANG)
        th.save_custom(th.MODE_LIGHT, MINT)
        th.save_custom(th.MODE_DARK, None)
        self.assertEqual(th.saved_custom(), {"hell": MINT})
        self.assertEqual(th.C["bg"], "#120A24")
        th.save_custom(th.MODE_LIGHT, None)
        self.assertNotIn(th.CUSTOM_KEY, self._stored())

    def test_kachel_aendert_nichts_gespeichertes(self):
        """Ab 0.57 (Entscheidung Nico F3): Eine Grundfarbe/ein Hintergrund
        loescht keine eigenen Farben mehr."""
        th.save_custom(th.MODE_DARK, SONNENUNTERGANG)
        th.save_custom(th.MODE_LIGHT, MINT)
        th.save_preset("rot_pink")
        th.save_background("schwarz")
        self.assertEqual(th.saved_custom(), {"dunkel": SONNENUNTERGANG, "hell": MINT})
        self.assertEqual(th.C["bg"], th.hsl_to_hex(*SONNENUNTERGANG["hintergrund"]))
        th.save_preset(th.DEFAULT_PRESET)
        th.save_background(th.DEFAULT_BACKGROUND)

    def test_speichern_mit_angeklickter_farbwelt(self):
        world = ("orange_gelb", "tannengruen")
        start = th.custom_start(th.MODE_DARK, world)
        self.assertEqual(start["akzent1"], th.hex_to_hsl(th.preset("orange_gelb")["primary"][0]))
        self.assertEqual(start["hintergrund"], th.hex_to_hsl(th.background("tannengruen")["bg"]))
        # Regler genau auf der angeklickten Farbwelt: nur die Farbwelt speichern
        self.assertIsNone(th.custom_to_save(th.MODE_DARK, start, world))
        self.assertEqual(th.values_palette(start, th.MODE_DARK, world),
                         th.farbwelt_palette(th.MODE_DARK, world))
        # farbwelt_palette veraendert nichts
        self.assertEqual((th.current_preset, th.current_background),
                         (th.DEFAULT_PRESET, th.DEFAULT_BACKGROUND))
        moved = dict(start, akzent1=(10, 90, 40))
        self.assertEqual(th.custom_to_save(th.MODE_DARK, moved, world), moved)
        self.assertIsNone(th.custom_to_save(th.MODE_DARK, None, world))

    def test_wann_kachel_nur_regler_setzt(self):
        start = th.custom_start(th.MODE_DARK)
        self.assertFalse(th.tile_sets_sliders(th.MODE_DARK, start))
        self.assertTrue(th.tile_sets_sliders(th.MODE_DARK, dict(start, akzent1=(1, 2, 3))))
        self.assertTrue(th.tile_sets_sliders(th.MODE_DARK, start, ("rot_pink", "violett")))
        th.save_custom(th.MODE_DARK, GRAPHIT)
        self.assertTrue(th.tile_sets_sliders(th.MODE_DARK, GRAPHIT))
        self.assertFalse(th.tile_sets_sliders(th.MODE_LIGHT, th.custom_start(th.MODE_LIGHT)))

    def test_andere_einstellungen_bleiben(self):
        fisi_update.save_settings({"auto_check": False, "nutzer_name": "Nico",
                                   "sync_repo": "a/b"})
        th.save_custom(th.MODE_DARK, GRAPHIT)
        th.save_custom(th.MODE_DARK, None)
        stored = self._stored()
        self.assertEqual((stored["auto_check"], stored["nutzer_name"], stored["sync_repo"]),
                         (False, "Nico", "a/b"))

    def test_vorschau_veraendert_nichts(self):
        before = (dict(th.C), dict(th.GRADIENTS), th.light, dict(th.CATEGORY_COLOR))
        with th.preview_colors(th.custom_palette(NEON)):
            self.assertTrue(th.light)
            self.assertEqual(th.C["bg"], "#00FF00")
        self.assertEqual((dict(th.C), dict(th.GRADIENTS), th.light, dict(th.CATEGORY_COLOR)),
                         before)


class AbgleichTest(unittest.TestCase):
    """Eigene Farben bleiben auf dem Geraet (kein Eingriff in Abgleich-Format 2)."""

    def tearDown(self):
        _reset()

    def test_abgleich_und_sicherung_ohne_farben(self):
        import fisi_core
        import fisi_sicherung as fsi
        import fisi_sync
        th.save_custom(th.MODE_DARK, SONNENUNTERGANG)
        db = fisi_core.DBManager(os.environ["FISI_DB_PATH"])
        exported = json.dumps(fisi_sync.export_local(db))
        self.assertEqual(fisi_sync.FORMAT, 2)
        self.assertNotIn(th.CUSTOM_KEY, exported)
        self.assertNotIn(th.hsl_to_hex(220, 40, 12), exported)
        self.assertNotIn("akzent1", exported)
        raw = fsi.create_backup(db, "0.57", "PC")
        backup = json.dumps(fsi.read_backup(raw))
        self.assertIn("einstellungen", backup)
        self.assertNotIn(th.CUSTOM_KEY, backup)


class KarteTest(unittest.TestCase):
    """Die Karte folgt dem Hintergrund-Grundton (erweitert um eigene Farben)."""

    def tearDown(self):
        _reset()

    def test_karte_folgt_den_eigenen_farben(self):
        th.apply_custom(th.MODE_DARK, SONNENUNTERGANG)
        ground = fg.map_palette()["boden"]
        self.assertEqual(ground, th.mix(th.C["bg"], th.C["card"], 0.55))
        self.assertEqual(fg.map_palette(), _map_of(th.custom_palette(SONNENUNTERGANG)))

    def test_helle_karte_mit_mindestkontrast(self):
        """Raster ueber helle Hintergruende (Helligkeit ab 80 %, jeder Farbton,
        drei Saettigungen) und alle Grundfarben als Akzente."""
        count = 0
        for preset in th.PRESETS:
            first, second = (th.hex_to_hsl(color) for color in preset["primary"])
            for hue in range(0, 360, 30):
                for sat in (0, 50, 100):
                    for light in (80, 90, 100):
                        values = {"akzent1": first, "akzent2": second,
                                  "hintergrund": (hue, sat, light)}
                        palette = th.custom_palette(values)
                        self.assertTrue(palette["light"])
                        colors = _map_of(palette)
                        ground = colors["boden"]
                        where = (preset["id"], hue, sat, light)
                        self.assertGreaterEqual(th.contrast(colors["schrift"], ground), 4.5,
                                                where)
                        for key in ("strasse", "wasser", "gleis", "baum", "park_rand"):
                            self.assertGreaterEqual(th.contrast(colors[key], ground), 3.0,
                                                    (key,) + where)
                        count += 1
        self.assertEqual(count, 6 * 12 * 3 * 3)


    def test_dunkle_karte_mit_mindestkontrast(self):
        """Ab 0.57 (F2): Raster ueber dunkle Hintergruende (Helligkeit bis 30 %,
        jeder Farbton, drei Saettigungen) und alle Grundfarben als Akzente."""
        count = 0
        for preset in th.PRESETS:
            first, second = (th.hex_to_hsl(color) for color in preset["primary"])
            for hue in range(0, 360, 30):
                for sat in (0, 50, 100):
                    for light in (0, 10, 20, 30):
                        values = {"akzent1": first, "akzent2": second,
                                  "hintergrund": (hue, sat, light)}
                        palette = th.custom_palette(values)
                        if palette["light"]:
                            continue    # sehr kraeftiges Gelb/Gruen kippt auf hell
                        colors = _map_of(palette)
                        ground = colors["boden"]
                        where = (preset["id"], hue, sat, light)
                        self.assertGreaterEqual(th.contrast(colors["schrift"], ground), 4.5,
                                                where)
                        for key in ("strasse", "wasser", "gleis", "schwelle", "baum",
                                    "park_rand"):
                            self.assertGreaterEqual(th.contrast(colors[key], ground), 3.0,
                                                    (key,) + where)
                        count += 1
        self.assertGreater(count, 6 * 12 * 3 * 4 * 0.9)

    def test_dunkle_karte_wird_geprueft(self):
        """Ab 0.57 prueft die Warnung die Karte auch in der dunklen Darstellung."""
        palette = th.custom_palette(SONNENUNTERGANG)
        self.assertFalse(palette["light"])
        names = [item[0] for item in th.custom_checks(palette, _map_of(palette))]
        for name in ("Karte: Beschriftung", "Karte: Straßen", "Karte: Fluss"):
            self.assertIn(name, names)
        broken = dict(_map_of(palette), strasse=_map_of(palette)["boden"])
        names = [item[0] for item in th.custom_problems(palette, broken)]
        self.assertIn("Karte: Straßen", names)


class FachbereicheTest(unittest.TestCase):
    """Ab 0.57 (Entscheidung Nico F4): eigene Warnzeile, wenn sich die fuenf
    Fachbereichsfarben kaum unterscheiden (Farbabstand Delta E unter 20)."""

    def tearDown(self):
        _reset()

    def test_farbwelten_ohne_warnzeile(self):
        lowest = 100.0
        for mode in th.MODE_IDS:
            for back in th.BACKGROUND_IDS:
                for preset in th.PRESET_IDS:
                    th.apply_mode(mode)
                    th.apply_background(back)
                    th.apply_preset(preset)
                    palette = th.farbwelt_palette(mode)
                    self.assertIsNone(th.category_clash(palette), (mode, back, preset))
                    keys = ("cyan", "pink", "purple", "green", "orange")
                    lowest = min([lowest] + [th.color_distance(th.C[a], th.C[b])
                                             for a in keys for b in keys if a < b])
        self.assertGreaterEqual(lowest, 27.8)

    def test_lesbare_saetze_ohne_warnzeile(self):
        for values in LESBAR:
            self.assertIsNone(th.category_clash(th.custom_palette(values)), values)

    def test_unlesbar_und_grau(self):
        clash = th.category_clash(th.custom_palette(UNLESBAR))
        self.assertEqual(clash[:2], ("Sicherheit (Pink)", "Systeme (Lila)"))
        self.assertLess(clash[2], 2.0)
        grau = {"akzent1": (262, 83, 58), "akzent2": (333, 71, 51),
                "hintergrund": (0, 0, 60)}
        clash = th.category_clash(th.custom_palette(grau))
        self.assertEqual(clash[:2], ("Netzwerk (Cyan)", "Wirtschaft (Grün)"))
        self.assertLess(clash[2], th.CATEGORY_DISTANCE)
        # Dunkelgrau bleibt unterscheidbar
        dunkelgrau = dict(grau, hintergrund=(0, 0, 40))
        self.assertIsNone(th.category_clash(th.custom_palette(dunkelgrau)))

    def test_warnzeile_zusaetzlich_zum_kontrast(self):
        palette = th.custom_palette(UNLESBAR)
        lines = th.custom_warning(palette, _map_of(palette))
        self.assertEqual(lines[0], th.CUSTOM_WARN_TITLE)
        self.assertEqual(lines[-1], "Fachbereichsfarben schwer unterscheidbar: Sicherheit (Pink) "
                         "und Systeme (Lila) (Farbabstand 1,6, nötig 20,0)")
        grau = th.custom_palette({"akzent1": (262, 83, 58), "akzent2": (333, 71, 51),
                                  "hintergrund": (0, 0, 60)})
        lines = th.custom_warning(grau, _map_of(grau))
        self.assertTrue(lines[-1].startswith("Fachbereichsfarben schwer unterscheidbar"))
        self.assertEqual(th.custom_warning(th.custom_palette(MINT),
                                           _map_of(th.custom_palette(MINT))), [])


class TexteTest(unittest.TestCase):

    def test_gleiche_texte_pc_und_handy(self):
        with open(os.path.join(HERE, "app_gui.py"), encoding="utf-8") as handle:
            pc = handle.read()
        with open(os.path.join(HERE, "mobile", "src", "main.py"), encoding="utf-8") as handle:
            mobile = handle.read()
        for name in ("CUSTOM_TITLE", "CUSTOM_HINT", "CUSTOM_STATE_ON", "CUSTOM_STATE_OFF",
                     "CUSTOM_TILE_HINT", "CUSTOM_PREVIEW", "CUSTOM_SAVE", "CUSTOM_RESET",
                     "CUSTOM_OK", "CUSTOM_PARTS", "CUSTOM_CHANNELS",
                     "CUSTOM_PREVIEW_BUTTON", "CUSTOM_PREVIEW_MAP", "custom_warning",
                     "slider_text"):
            self.assertIn("fisi_theme." + name, pc, name)
            self.assertIn("fisi_theme." + name, mobile, name)

    def test_screenreader_beschriftung(self):
        hue = th.CUSTOM_CHANNELS[0]
        self.assertEqual(th.slider_label("Akzent 1", hue, 210), "Akzent 1, Farbton, 210 Grad")
        self.assertEqual(th.slider_label("Hintergrund", th.CUSTOM_CHANNELS[2], 9),
                         "Hintergrund, Helligkeit, 9 Prozent")
        self.assertEqual(th.slider_text(hue, 210), "210°")
        self.assertEqual(th.slider_text(th.CUSTOM_CHANNELS[1], 45), "45 %")


@unittest.skipUnless(_tk_ok(), "kein Display fuer Tk")
class ReglerPcTest(unittest.TestCase):
    """Regler am PC: Tastatur, Live-Vorschau, Speichern."""

    @classmethod
    def setUpClass(cls):
        import customtkinter as ctk
        import app_gui
        import fisi_widgets as fw
        cls.app_gui, cls.fw = app_gui, fw
        cls.root = ctk.CTk()
        cls.root.geometry("900x700+0+0")
        fw.setup_fonts(cls.root)
        cls.saved = []
        cls.panel = app_gui.CustomColors(cls.root, lambda mode, values, world=None:
                                         cls.saved.append((mode, values)))
        cls.panel.pack()
        cls.settle()

    @classmethod
    def tearDownClass(cls):
        try:
            for job in cls.root.tk.splitlist(cls.root.tk.call("after", "info")):
                cls.root.tk.call("after", "cancel", job)
            cls.root.destroy()
        except Exception:  # noqa: BLE001
            pass
        _reset()

    @classmethod
    def settle(cls, times=4):
        for _ in range(times):
            cls.root.update_idletasks()
            cls.root.update()

    def test_pfeiltasten_aendern_den_wert(self):
        slider = self.panel.sliders[("akzent1", "h")]
        start = self.panel.values["akzent1"][0]
        self.fw.focus_widget(slider)
        self.settle()
        slider.event_generate("<Right>")
        slider.event_generate("<Right>")
        slider.event_generate("<Shift-Left>")
        self.root.after(80, self.root.quit)
        self.root.mainloop()
        self.settle()
        expected = (start + 2 - 10) % 360
        self.assertEqual(self.panel.values["akzent1"][0], expected)
        self.assertEqual(self.panel.value_labels[("akzent1", "h")].cget("text"),
                         "%d°" % expected)
        self.assertEqual(int(round(slider.get())), expected)
        # Vorschau zeigt den neuen Knopfverlauf
        self.assertEqual(self.panel.palette()["gradients"]["primary"][0],
                         th.hsl_to_hex(*self.panel.values["akzent1"]))

    def test_regler_sind_per_tab_erreichbar(self):
        for slider in self.panel.sliders.values():
            self.assertEqual(str(slider.tk.call(slider._w, "cget", "-takefocus")), "1")

    def test_warnung_und_speichern(self):
        self.panel.values = dict(UNLESBAR)
        self.panel._redraw()
        self.assertIn("Knopfschrift auf Akzent 1: 1,0:1", self.panel.warning.cget("text"))
        self.assertIn("Fachbereichsfarben schwer unterscheidbar", self.panel.warning.cget("text"))
        self.panel._save()
        self.root.after(60, self.root.quit)
        self.root.mainloop()
        self.assertEqual(self.saved[-1], (th.current_mode, UNLESBAR))
        self.panel.values = dict(MINT)
        self.panel._redraw()
        self.assertIn(th.CUSTOM_OK, self.panel.warning.cget("text"))

    def test_kachel_setzt_nur_die_regler(self):
        """F3: Kachel-Klick bei bewegten Reglern stellt die Regler auf die
        Farbwelt, speichert nichts; Speichern gibt die Farbwelt mit."""
        _kachel_pruefen(self, self.app_gui.SettingsView, self.panel,
                        lambda key: int(round(self.panel.sliders[key].get())),
                        after=lambda _ms, job: job())


@unittest.skipUnless(_flet_ok(), "flet nicht installiert")
class ReglerHandyTest(unittest.TestCase):
    """Regler am Handy: TalkBack-Beschriftung mit Wert, Lautstaerke/Wischen."""

    @classmethod
    def setUpClass(cls):
        sys.path.insert(1, os.path.join(HERE, "mobile", "src"))
        import main as handy
        cls.handy = handy
        cls.saved = []
        cls.panel = handy.CustomColors(lambda mode, values, world=None:
                                       cls.saved.append((mode, values)))

    @classmethod
    def tearDownClass(cls):
        _reset()

    def test_talkback_liest_wert(self):
        semantics, _name = self.panel.semantics[("akzent1", "h")]
        value = self.panel.values["akzent1"][0]
        self.assertTrue(semantics.slider)
        self.assertTrue(semantics.exclude_semantics)
        self.assertEqual(semantics.label, "Akzent 1, Farbton, %d Grad" % value)
        self.assertEqual(semantics.value, "%d Grad" % value)
        self.panel._nudge("akzent1", th.CUSTOM_CHANNELS[0], 1)
        self.assertEqual(semantics.label, "Akzent 1, Farbton, %d Grad" % ((value + 1) % 360))
        self.assertEqual(self.panel.sliders[("akzent1", "h")].value, (value + 1) % 360)

    def test_grenzen(self):
        self.panel.values["hintergrund"] = (10, 20, 100)
        self.panel._nudge("hintergrund", th.CUSTOM_CHANNELS[2], 1)
        self.assertEqual(self.panel.values["hintergrund"][2], 100)
        semantics, _name = self.panel.semantics[("hintergrund", "l")]
        self.assertEqual(semantics.increased_value, "100 Prozent")

    def test_warnung_und_speichern(self):
        self.panel.values = dict(UNLESBAR)
        self.panel._redraw()
        self.assertIn("Knopfschrift auf Akzent 1: 1,0:1", self.panel.warning.value)
        self.assertIn("Fachbereichsfarben schwer unterscheidbar", self.panel.warning.value)
        self.panel._save()
        self.assertEqual(self.saved[-1], (th.current_mode, UNLESBAR))

    def test_kachel_setzt_nur_die_regler(self):
        _kachel_pruefen(self, self.handy.SettingsScreen, self.panel,
                        lambda key: self.panel.sliders[key].value)


def _kachel_pruefen(test, view_class, panel, slider_value, after=None):
    """Gemeinsamer Ablauf fuer PC und Handy (Entscheidung Nico F3)."""
    from types import SimpleNamespace
    calls = []
    fake_app = SimpleNamespace(change_color=lambda **kw: calls.append(kw))
    view = SimpleNamespace(custom_colors=panel, app=fake_app)
    if after:
        view.after = after
    panel.world = None
    panel._show_values(th.custom_start(panel.mode))
    # Regler auf dem Startwert, nichts gespeichert: Kachel waehlt wie bisher
    view_class._change_color(view, "rot_pink")
    test.assertEqual(calls, [{"preset_id": "rot_pink"}])
    calls.clear()
    # Regler bewegt: Kachel setzt nur die Regler, speichert nichts
    panel._show_values(dict(SONNENUNTERGANG))
    before = open(SETTINGS).read() if os.path.exists(SETTINGS) else ""
    view_class._change_color(view, "orange_gelb")
    view_class._change_background(view, "tannengruen")
    test.assertEqual(calls, [])
    test.assertEqual(open(SETTINGS).read() if os.path.exists(SETTINGS) else "", before)
    world = ("orange_gelb", "tannengruen")
    test.assertEqual(panel.world, world)
    start = th.custom_start(panel.mode, world)
    test.assertEqual(panel.values, start)
    test.assertEqual(slider_value(("akzent1", "h")), start["akzent1"][0])
    test.assertEqual(slider_value(("hintergrund", "l")), start["hintergrund"][2])
    test.assertEqual(panel.palette(), th.farbwelt_palette(panel.mode, world))
    # Speichern: Farbwelt wird gespeichert, keine eigenen Farben (Startwert)
    view_class._save_custom(view, panel.mode, dict(panel.values), panel.world)
    test.assertEqual(calls, [{"preset_id": "orange_gelb", "background_id": "tannengruen",
                              "custom": (panel.mode, None)}])
    calls.clear()
    # Bewegt und gespeichert: Farbwelt und Reglerwerte
    moved = dict(start, akzent1=(10, 90, 40))
    view_class._save_custom(view, panel.mode, moved, world)
    test.assertEqual(calls[0]["custom"], (panel.mode, moved))
    # Zuruecksetzen ohne Gespeichertes: Regler wieder auf die gespeicherte Farbwelt
    panel._reset()
    test.assertIsNone(panel.world)
    test.assertEqual(panel.values, th.custom_start(panel.mode))


def tearDownModule():
    shutil.rmtree(_TMP, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
