# -*- coding: utf-8 -*-
"""Kontrast der Weltkarte in der hellen Darstellung (ab 0.56).

Prueft mit der WCAG-Kontrastformel (fisi_theme.contrast, relative Luminanz)
fuer alle sechs Hintergruende und alle Grundfarben:
- Schrift der Karte (Gebietsnamen, Beschriftungen, Hinweise, Ortsschilder)
  mindestens 4,5:1 gegen den tatsaechlichen Grund,
- Strassen, Fluss, Bahn (Gleis und Schwellen), Gruenflaechen-Rand, Baeume
  und Gebaeudekonturen mindestens 3:1 gegen den Kartengrund,
- die tatsaechlich gezeichneten Formen (fisi_game.world_shapes) benutzen
  genau diese Farben,
- die dunkle Darstellung ist unveraendert (Werte wie vor 0.56).

Aufruf: python -m unittest test_karte_kontrast
"""
import os
import sys
import tempfile
import unittest

HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HIER)
# Keine echten Einstellungen lesen (Darstellung/Hintergrund kommen aus dem Test)
os.environ.setdefault("FISI_DB_PATH", os.path.join(tempfile.mkdtemp(), "fisi.db"))

import fisi_theme as th  # noqa: E402
import fisi_game as fg  # noqa: E402

TEXT_MIN = 4.5
FLAECHE_MIN = 3.0

# Kartenfarben der dunklen Darstellung (Hintergrund Violett) aus 0.55/520abf6 -
# muessen unveraendert bleiben.
DUNKEL_VIOLETT = {
    "boden": "#170D2B", "park": "#1A2136", "wasser": "#272E59", "wasser_hell": "#344A7E",
    "strasse": "#2B1949", "strasse_mitte": "#3D2465", "gleis": "#7A5ABC",
    "schwelle": "#39215F", "baum": "#1E3D45", "baum_hell": "#236059",
    "schatten": "#0F081C", "licht": "#FDDC87", "fenster": "#351F5A",
    "schrift": "#786895", "schild": "#0C0619",
}

TONE = ["#8B93A1"] + [fg.map_role_color(role) for role in fg.MAP_ROLES]


def _modes():
    """(Hintergrund, Grundfarbe) fuer alle Kombinationen."""
    for back in th.BACKGROUND_IDS:
        for preset in th.PRESET_IDS:
            yield back, preset


class KarteKontrastTest(unittest.TestCase):

    def tearDown(self):
        th.apply_mode(th.MODE_DARK)
        th.apply_preset(th.DEFAULT_PRESET)
        th.apply_background(th.DEFAULT_BACKGROUND)

    def _light(self, back, preset):
        th.apply_mode(th.MODE_LIGHT)
        th.apply_background(back)
        th.apply_preset(preset)
        self.assertTrue(th.light)

    def test_hell_schrift_mindestens_4_5(self):
        for back, preset in _modes():
            self._light(back, preset)
            p = fg.map_palette()
            ground = p["boden"]
            where = (back, preset)
            self.assertGreaterEqual(th.contrast(p["schrift"], ground), TEXT_MIN, where)
            self.assertGreaterEqual(th.contrast(p["hinweis"], ground), TEXT_MIN, where)
            self.assertGreaterEqual(th.contrast(th.C["text"], p["schild"]), TEXT_MIN, where)
            self.assertGreaterEqual(th.contrast(th.C["on_accent"], th.C["pink"]), TEXT_MIN,
                                    where)
            self.assertGreaterEqual(th.contrast(th.C["card"], th.C["green"]), TEXT_MIN, where)

    def test_hell_gebietsnamen_auf_eigenem_grund(self):
        """Gebietsnamen haben im Hellen den Kartengrund hinter sich, damit
        kreuzende Strassen den Kontrast nicht senken."""
        self._light(th.DEFAULT_BACKGROUND, th.DEFAULT_PRESET)
        p = fg.map_palette()
        names = [shape for shape in fg.landscape_labels() if shape["role"] == "ortsname"]
        self.assertTrue(names)
        for shape in names:
            self.assertEqual(shape["bg"], p["boden"])
            self.assertEqual(shape["color"], p["schrift"])
            self.assertGreaterEqual(th.contrast(shape["color"], shape["bg"]), TEXT_MIN)

    def test_hell_flaechen_und_linien_mindestens_3(self):
        for back, preset in _modes():
            self._light(back, preset)
            p = fg.map_palette()
            ground = p["boden"]
            for key in ("strasse", "wasser", "gleis", "schwelle", "park_rand", "baum"):
                self.assertGreaterEqual(th.contrast(p[key], ground), FLAECHE_MIN,
                                        (back, preset, key))
            self.assertGreaterEqual(th.contrast(p["baum"], p["park"]), FLAECHE_MIN,
                                    (back, preset, "baum/park"))
            self.assertGreaterEqual(th.contrast(p["park_rand"], p["park"]), FLAECHE_MIN,
                                    (back, preset, "park_rand/park"))
            for tone in TONE:
                wall, roof, edge = fg.map_block_colors(tone)
                for surface in (ground, wall, roof):
                    self.assertGreaterEqual(th.contrast(edge, surface), FLAECHE_MIN,
                                            (back, preset, tone, surface))

    def test_hell_gezeichnete_formen_nutzen_die_palette(self):
        """Die Weltkarte zeichnet im Hellen wirklich mit den gepruefen Farben."""
        self._light(th.DEFAULT_BACKGROUND, th.DEFAULT_PRESET)
        p = fg.map_palette()
        shapes = fg.world_shapes(None)
        self.assertEqual(shapes[0]["fill"], p["boden"])
        fills = {shape.get("fill") for shape in shapes}
        lines = {shape.get("color") for shape in shapes} | \
            {shape.get("line") for shape in shapes}
        self.assertIn(p["park"], fills)
        self.assertIn(p["baum"], fills)
        for key in ("strasse", "wasser", "gleis", "schwelle", "park_rand"):
            self.assertIn(p[key], lines, key)
        parks = [shape for shape in shapes if shape.get("fill") == p["park"]]
        self.assertTrue(all(shape["line"] == p["park_rand"] for shape in parks))
        # Alle Gebaeudekonturen erreichen 3:1 gegen den Grund
        edges = {shape["line"] for shape in shapes
                 if shape["k"] in ("rect", "poly") and shape.get("line")
                 and shape["line"] != p["park_rand"]}
        self.assertTrue(edges)
        for edge in edges:
            self.assertGreaterEqual(th.contrast(edge, p["boden"]), FLAECHE_MIN, edge)

    def test_dunkel_unveraendert(self):
        th.apply_mode(th.MODE_DARK)
        th.apply_background("violett")
        th.apply_preset(th.DEFAULT_PRESET)
        self.assertFalse(th.light)
        self.assertEqual(fg.map_palette(), DUNKEL_VIOLETT)
        for back in th.BACKGROUND_IDS:
            th.apply_background(back)
            p = fg.map_palette()
            self.assertEqual(set(p), set(DUNKEL_VIOLETT), back)
            ground = th.mix(th.C["bg"], th.C["card"], 0.55)
            self.assertEqual(p["boden"], ground, back)
            self.assertEqual(p["strasse"], th.mix(ground, th.C["border_hi"], 0.32), back)
            self.assertEqual(p["schrift"], th.mix(th.C["muted"], ground, 0.25), back)
            for tone in TONE:
                wall = th.mix(th.C["card_alt"], tone, 0.12)
                self.assertEqual(fg.map_block_colors(tone),
                                 (wall, th.mix(th.C["card"], tone, 0.30),
                                  th.mix(wall, "#000000", 0.35)), (back, tone))
            shapes = fg.world_shapes(None)
            for shape in shapes:
                if shape["k"] == "text" and shape["role"] == "ortsname":
                    self.assertNotIn("bg", shape)
                if shape.get("fill") == p["park"] and shape["k"] == "rect":
                    self.assertEqual((shape["line"], shape["lw"]), ("", 0.0))


if __name__ == "__main__":
    unittest.main()
