"""Tests 0.63.2 (B-J-04 V2, Nachtrag E1-5): Beim Antippen einer Auswahl-Pille
(ui.PillGroup) kommt der richtige Index an. Seit B-J-04 V2 nimmt nur die
unsichtbare Tippflaeche (Inhalt des Semantics-Knotens) das Tippen an; der
bisherige Test rief nur select() direkt auf und haette eine falsche Zuordnung
(z. B. jede Flaeche waehlt die letzte Pille) nicht bemerkt.

Geprueft fuer beide Formen (seitlich rollend und umbrechend) und an allen
fuenf Schriftstufen: Antippen der Flaeche i liefert values[i] an on_change,
get() und current sind i, genau Knoten i ist selected. Ist die Pille schon
gewaehlt, kommt sie trotzdem an (wie bisher).
"""
import os
import sys
import unittest

HERE = os.environ.get("STUFEN_CODE") or os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(1, os.path.join(HERE, "mobile", "src"))

import ui  # noqa: E402

OPTIONEN = [("a", "Alpha"), ("b", "Beta"), ("c", "Gamma"), ("d", "Delta"), ("e", "Epsilon")]
STUFEN = (1.0, 1.15, 1.3, 1.6, 2.0)


class PillIndexTest(unittest.TestCase):

    def setUp(self):
        self._alt = ui.FONT_FACTOR[0]

    def tearDown(self):
        ui.set_font_factor(self._alt)

    def tippen(self, pills, index):
        flaeche = pills.semantics[index].content
        self.assertIsNotNone(flaeche.on_click, index)
        flaeche.on_click(None)

    def pruefen(self, umbrechen):
        for faktor in STUFEN:
            ui.set_font_factor(faktor)
            seen = []
            pills = ui.PillGroup(OPTIONEN, on_change=seen.append, initial=0,
                                 umbrechen=umbrechen)
            reihenfolge = [3, 1, 4, 0, 2, 2]
            for index in reihenfolge:
                with self.subTest(faktor=faktor, umbrechen=umbrechen, index=index):
                    self.tippen(pills, index)
                    self.assertEqual(seen[-1], OPTIONEN[index][0])
                    self.assertEqual(pills.get(), OPTIONEN[index][0])
                    self.assertEqual(pills.current, index)
                    self.assertEqual([item.selected for item in pills.semantics],
                                     [i == index for i in range(len(OPTIONEN))])
            self.assertEqual(seen, [OPTIONEN[i][0] for i in reihenfolge])

    def test_rollend(self):
        self.pruefen(False)

    def test_umbrechend(self):
        self.pruefen(True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
