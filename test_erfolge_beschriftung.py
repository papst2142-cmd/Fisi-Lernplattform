#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ab 0.62.1 (Teil C): Beschriftung gestufter Erfolge.

Die Zeile unter dem Namen eines Abzeichens nennt die erreichte Stufe und die
naechste Stufe mit ihrem Fortschritt, z.B. "Bronze erreicht (Tag 6) · Silber:
71 / 75". PC und Handy zeigen denselben Text aus fisi_game.badge_status.
Geaendert ist nur der Text; Stufen, Schwellen und Spielwerte bleiben gleich.
"""
import os
import unittest

import fisi_game as fg

HERE = os.path.dirname(os.path.abspath(__file__))


def stage(tier, reached=None):
    return {"tier": tier, "name": fg.TIER_NAMES[tier], "ziel": "", "erreicht": reached,
            "moment": False}


def item(stages, level=0, progress="", ever=None, secret=False, easy_only=False):
    """Abzeichen wie aus achievement_overview, nur die Felder fuer den Text."""
    return {"stufen": stages, "stufe": level,
            "tier": stages[level - 1]["tier"] if level else None,
            "naechste": stages[level] if level < len(stages) else None,
            "fortschritt": progress, "geheim": secret, "nur_normal": easy_only,
            "je": level if ever is None else ever}


THREE = ("bronze", "silber", "gold")


def three(days=()):
    return [stage(tier, days[index] if index < len(days) else None)
            for index, tier in enumerate(THREE)]


class BeschriftungTest(unittest.TestCase):

    def check(self, entry, text, color):
        self.assertEqual(fg.badge_status(entry), (text, color))

    def test_gesperrt(self):
        self.check(item(three(), progress="42 / 60"), "Bronze: 42 / 60", "muted")
        self.check(item([stage("gold")], progress="37 / 100"), "Gold: 37 / 100", "muted")
        self.check(item(three(), progress="nächstes Ziel: Junior"),
                   "Bronze bei: Junior", "muted")
        self.check(item(three()), "Bronze: noch offen", "muted")
        self.check(item([stage("gold")]), "Gold: noch offen", "muted")
        self.check(item(three(), progress="Wissensstand wird geladen"),
                   "Wissensstand wird geladen", "muted")

    def test_erreicht(self):
        self.check(item(three([6]), 1, "71 / 75"),
                   "Bronze erreicht (Tag 6) · Silber: 71 / 75", "bronze")
        self.check(item(three([6, 30]), 2, "80 / 90"),
                   "Silber erreicht (Tag 30) · Gold: 80 / 90", "silber")
        self.check(item(three([12]), 1, "nächstes Ziel: Fachkraft"),
                   "Bronze erreicht (Tag 12) · Silber bei: Fachkraft", "bronze")
        self.check(item(three([6]), 1), "Bronze erreicht (Tag 6) · Silber: noch offen",
                   "bronze")
        self.check(item(three([6]), 1, "Wissensstand wird geladen"),
                   "Bronze erreicht (Tag 6) · Wissensstand wird geladen", "bronze")
        # Hoechste Stufe: kein Zusatz
        self.check(item(three([6, 30, 90]), 3), "Gold erreicht (Tag 90)", "gold")
        self.check(item([stage("gold", 4)], 1), "Gold erreicht (Tag 4)", "gold")
        # Tag 0 (vor dem ersten Diensttag) zeigt Tag 1 wie bisher
        self.check(item([stage("bronze", 0)], 1), "Bronze erreicht (Tag 1)", "bronze")

    def test_frueher_und_besondere(self):
        self.check(item(three([9]), 1, "30.000 € / 100.000 €", ever=2),
                   "Bronze erreicht (Tag 9) · Silber: 30.000 € / 100.000 € · früher: Silber",
                   "bronze")
        self.check(item(three(), progress="42 / 60", ever=3),
                   "Bronze: 42 / 60 · früher: Gold", "muted")
        self.check(item(three(), ever=1, easy_only=True), "nur auf Normal · früher: Bronze",
                   "muted")
        self.check(item(three(), easy_only=True), "nur auf Normal", "muted")
        self.check(item(three(), secret=True), "noch nicht entdeckt", "muted")

    def test_echte_abzeichen(self):
        # Jedes Abzeichen aus erfolge.json liefert in jedem Stand einen Text
        rules = fg.achievement_rules().get("erfolge") or []
        self.assertGreaterEqual(len(rules), 38)
        for rule in rules:
            stages = [stage(entry["stufe"]) for entry in rule["stufen"]]
            for level in range(len(stages) + 1):
                for index in range(level):
                    stages[index]["erreicht"] = index + 1
                text, color = fg.badge_status(item(stages, level, "1 / 2" if level < len(
                    stages) else ""))
                self.assertTrue(text, rule["id"])
                self.assertNotIn("nächstes Ziel", text, rule["id"])
                self.assertEqual(color, stages[level - 1]["tier"] if level else "muted")

    def test_pc_und_handy_nutzen_denselben_text(self):
        for name in ("fisi_game_gui.py", os.path.join("mobile", "src", "spiel.py")):
            with open(os.path.join(HERE, name), encoding="utf-8") as handle:
                self.assertIn("status, color = fg.badge_status(item)", handle.read(), name)


if __name__ == "__main__":
    unittest.main()
