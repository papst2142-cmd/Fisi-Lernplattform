#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test ab 0.63.2 (B-N-09): Werden Abzeichen und Bestwerte richtig GEZEICHNET?

Die Tests test_erfolge_alle_zustaende.py und test_erfolge_beschriftung.py
pruefen die Daten (fisi_game), test_reiter_sichtbar.py nur, dass ueberhaupt
etwas zu sehen ist. Hier wird das Gezeichnete gegen die Daten geprueft:

PC (fisi_game_gui, echtes Tk):
  * badge_canvas: fuer jedes Bild aus erfolge.json, jede Farbe und jede
    Stufe (keine, Bronze, Silber, Gold) entsprechen die Zeichenbefehle auf
    dem Canvas genau fisi_game.badge_shapes(Bild, Farbe, Stufe): gleiche
    Anzahl, gleiche Form (Kreis, Rechteck, Linie, Bogen, Vieleck), gleiche
    Farben, Kreise/Linien an der richtigen Stelle (Massstab 64 px).
  * Kachel eines Abzeichens (JourneyView._badge_tile) fuer die echten
    Abzeichen eines Spielstands, dazu jedes Abzeichen in jeder Stufe:
    Zeichnung = badge_shapes(bild, farbe, tier), Rahmenfarbe = Stufenfarbe
    (offen: border), Name ("???" bei geheim), Zustandszeile und ihre Farbe
    aus badge_status/tier_text_color, Text bzw. "Noch nicht entdeckt.".
  * Bestwerte (JourneyView._build_records): Untertitel record_subtitle,
    je Bestwert in der Reihenfolge von record_board Name, Wert, Zusatz,
    Wertfarbe (text/muted) und gelber Rahmen nur bei Rekord in mehreren
    Durchgaengen.
Handy (mobile/src/spiel.py, Flet-Steuerelemente ohne Seite):
  * GameScreen._achievements: dieselben Pruefungen fuer Bestwerte und
    Abzeichen (Canvas-Formen und Farben gegen badge_shapes).

Reiner Schutztest (Plan-Nachtrag Nr. 15): gegen 14b3bd4 gruen, rot nur bei
einem Fehler im Zeichnen (Mutationsprobe im Bericht). Wird nie still
uebersprungen: ohne Anzeige oder ohne flet/spiel.py ist er rot.

Start:  xvfb-run -a python test_abzeichen_zeichnen.py
"""

import copy
import json
import os
import shutil
import sys
import tempfile
import types
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(1, os.path.join(HERE, "mobile", "src"))

import fisi_core   # noqa: E402
import fisi_game as fg   # noqa: E402

TIERS = (None, "bronze", "silber", "gold")


def _tk_ok():
    try:
        import tkinter
        root = tkinter.Tk()
        root.destroy()
        return True
    except Exception:  # noqa: BLE001
        return False


HAS_DISPLAY = _tk_ok()


def _spielstand(path):
    """Spielfigur mit erledigten Auftraegen, Firma und einer Person: so gibt
    es erreichte und offene Abzeichen und Bestwerte mit Werten."""
    db = fisi_core.DBManager(path)
    game = fg.Game(db, "PC")
    game.set_profile("Kim Talbahn", {"kreis": "pink"})
    goal = game.content["balancing"]["gruendung"]
    for number, task in enumerate(game.content["aufgaben"]):
        data = {"aufgabe": task["id"], "tag": number + 1, "richtig": True, "geld": 0,
                "reputation": {}}
        if number == 0:
            data["geld"] = goal["startkapital"] + 60000
            data["reputation"] = {key: 90 for key in fg.AXIS_KEYS}
        db.log_game_event(fg.EV_SOLVED, json.dumps(data), "PC")
        db.log_game_event(fg.EV_DAY_END, json.dumps({"tag": number + 1, "gehalt": 0}), "PC")
    game.reload()
    game.found_firm("Test IT-Service")
    game.hire(fg.applicants(game.state, game.content)[0]["id"])
    game.reload()
    game.check_achievements(force=True)
    game.reload()
    return game


def _bilder_farben():
    rules = fg.achievement_rules()["erfolge"]
    bilder = sorted({rule.get("bild") for rule in rules} | {"unbekannt"})
    farben = sorted({rule.get("farbe") for rule in rules})
    return bilder, farben


def _erwartet(shape):
    """(Form, Farben) eines Zeichenbefehls, wie sie gezeichnet sein muessen."""
    kind = shape["k"]
    if kind in ("rect", "oval", "poly"):
        return kind, (shape["fill"] or "").lower(), (shape["line"] or "").lower()
    if kind in ("line", "arc"):
        return kind, (shape["color"] or "").lower()
    return kind, (shape.get("color") or "").lower()


def _zwei_durchgaenge(records, state):
    """Bestenliste mit einem frueheren Durchgang: ein Bestwert dort hoeher
    (kein Rekord jetzt), die anderen haelt der laufende Durchgang."""
    rules = [rule for rule in fg.achievement_rules()["bestwerte"]
             if rule.get("besser") != "weniger"]
    run = "2000-01-01 00:00:00"
    extra = [(run, run, fg.REC_BEST, rules[0]["id"], 10 ** 7, {"tag": 5, "text": ""}),
             (run, run, fg.REC_BEST, "diensttage", 12, {"tag": 12, "text": ""})]
    return extra + list(records)


def _abzeichen_varianten(items):
    """Jedes Abzeichen wie im Spielstand und zusaetzlich in jeder Stufe
    (Bronze/Silber/Gold) und geheim - nur die Felder, die die Kachel liest."""
    out = []
    for item in items:
        out.append(item)
        for level, stage in enumerate(item["stufen"]):
            copy_ = copy.deepcopy(item)
            copy_["tier"] = stage["tier"]
            copy_["stufe"] = level + 1
            copy_["je"] = level + 1
            copy_["naechste"] = item["stufen"][level + 1] \
                if level + 1 < len(item["stufen"]) else None
            copy_["geheim"] = False
            out.append(copy_)
        secret = copy.deepcopy(item)
        secret["geheim"] = True
        secret["tier"] = None
        out.append(secret)
    return out


# ---------------------------------------------------------------------------
#  PC
# ---------------------------------------------------------------------------

class PcZeichnenTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # nie still ueberspringen: ohne Anzeige ist der Test rot
        if not HAS_DISPLAY:
            raise AssertionError("keine Anzeige - dieser Test darf nicht uebersprungen "
                                 "werden (unter Linux mit xvfb-run starten)")
        cls.folder = tempfile.mkdtemp(prefix="fisi_abzeichen_")
        os.environ["HOME"] = cls.folder
        cls.game = _spielstand(os.path.join(cls.folder, "t.db"))
        import customtkinter as ctk
        import fisi_game_gui as gg
        cls.gg = gg
        import fisi_widgets
        cls.root = ctk.CTk()
        fisi_widgets.setup_fonts(cls.root)
        cls.root.geometry("1360x900+0+0")
        cls.frame = ctk.CTkFrame(cls.root)
        cls.frame.pack(fill="both", expand=True)

    @classmethod
    def tearDownClass(cls):
        cls.root.destroy()
        shutil.rmtree(cls.folder, ignore_errors=True)

    def tearDown(self):
        for child in self.frame.winfo_children():
            child.destroy()

    def _pump(self):
        for _ in range(4):
            self.root.update()

    def _gezeichnet(self, canvas):
        """(Form, Farben) aller Canvas-Elemente in Zeichenreihenfolge."""
        out = []
        for item in canvas.find_all():
            kind = canvas.type(item)
            if kind == "oval":
                out.append(("oval", canvas.itemcget(item, "fill").lower(),
                            canvas.itemcget(item, "outline").lower()))
            elif kind in ("rectangle", "polygon"):
                out.append(("flaeche", canvas.itemcget(item, "fill").lower(),
                            canvas.itemcget(item, "outline").lower()))
            elif kind == "line":
                out.append(("line", canvas.itemcget(item, "fill").lower()))
            elif kind == "arc":
                out.append(("arc", canvas.itemcget(item, "outline").lower()))
            else:
                out.append((kind, canvas.itemcget(item, "fill").lower()))
        return out

    @staticmethod
    def _soll(shapes):
        out = []
        for shape in shapes:
            entry = _erwartet(shape)
            if entry[0] in ("rect", "poly"):
                entry = ("flaeche",) + entry[1:]
            out.append(entry)
        return out

    def _pruefe_canvas(self, canvas, picture, color, tier, size=64):
        from fisi_widgets import px
        shapes = fg.badge_shapes(picture, color, tier)
        label = "%s/%s/%s" % (picture, color, tier)
        self.assertEqual(self._gezeichnet(canvas), self._soll(shapes), label)
        # Lage: Kreise und Linien im Massstab size/BADGE_SIZE, ohne Versatz
        scale = px(size) / fg.BADGE_SIZE
        items = canvas.find_all()
        for item, shape in zip(items, shapes):
            if shape["k"] == "oval":
                soll = (shape["x"] * scale, shape["y"] * scale,
                        (shape["x"] + shape["w"]) * scale, (shape["y"] + shape["h"]) * scale)
            elif shape["k"] == "line":
                x1, y1, x2, y2 = shape["pts"]
                soll = (x1 * scale, y1 * scale, x2 * scale, y2 * scale)
            else:
                continue
            ist = canvas.coords(item)
            for a, b in zip(ist, soll):
                self.assertAlmostEqual(a, b, delta=0.75, msg="%s Lage %s" % (label, shape))
        # Stufe: Ring in der Stufenfarbe, offen mit Schloss
        if tier:
            self.assertEqual(canvas.itemcget(items[1], "outline").lower(),
                             fg.TIER_COLORS[tier].lower(), label)
        else:
            self.assertGreaterEqual(len(items), 4, label)

    def test_badge_canvas_jedes_bild_jede_farbe_jede_stufe(self):
        bilder, farben = _bilder_farben()
        geprueft = 0
        for picture in bilder:
            for color in farben:
                for tier in TIERS:
                    canvas = self.gg.badge_canvas(self.frame, picture, color, tier, size=64)
                    canvas.pack()
                    self._pump()
                    self._pruefe_canvas(canvas, picture, color, tier)
                    canvas.destroy()
                    geprueft += 1
        print("\n  badge_canvas: %d Kombinationen (Bild x Farbe x Stufe)" % geprueft)
        self.assertEqual(geprueft, len(bilder) * len(farben) * len(TIERS))

    def _kachel_teile(self, tile):
        """Canvas, Beschriftungen und Balken einer Kachel in Packreihenfolge
        (Kopf mit Bild, Name, Zustand, Balken; darunter Text und Ziele)."""
        canvases, labels, bars = [], [], []

        def walk(widget):
            for child in widget.pack_slaves():
                if isinstance(child, self.gg.ShapeCanvas):
                    canvases.append(child)
                elif type(child).__name__ == "CTkLabel":
                    labels.append(child)
                elif type(child).__name__ == "CTkProgressBar":
                    bars.append(child)
                else:
                    walk(child)
        walk(tile)
        return canvases, labels, bars

    def test_abzeichen_kachel_gegen_daten(self):
        from fisi_theme import C
        state = self.game.state
        items = fg.achievement_overview(state, self.game.topic_knowledge(),
                                        self.game.records())
        tiers = {item["tier"] for item in items}
        self.assertIn(None, tiers)
        self.assertTrue(tiers - {None}, "Spielstand ohne erreichtes Abzeichen")
        geprueft = 0
        for item in _abzeichen_varianten(items):
            tile = self.gg.JourneyView._badge_tile(None, self.frame, item)
            tile.pack()
            self._pump()
            canvases, labels, bars = self._kachel_teile(tile)
            self.assertEqual(len(canvases), 1, item["id"])
            self._pruefe_canvas(canvases[0], item["bild"], item["farbe"], item["tier"])
            tier = item["tier"]
            self.assertEqual(tile.cget("border_color"),
                             self.gg.tier_color(tier) if tier else C["border"], item["id"])
            texts = [label.cget("text") for label in labels]
            self.assertEqual(texts[0], "???" if item["geheim"] else item["name"])
            self.assertEqual(labels[0].cget("text_color"),
                             C["text"] if tier else C["text_dim"])
            status, color = fg.badge_status(item)
            self.assertEqual(texts[1], status, item["id"])
            self.assertEqual(labels[1].cget("text_color"), fg.tier_text_color(color))
            self.assertEqual(texts[2], "Noch nicht entdeckt." if item["geheim"]
                             else item["text"])
            goals = fg.badge_goals(item) if len(item["stufen"]) > 1 else ""
            self.assertEqual(texts[3:], [goals] if goals else [], item["id"])
            show_bar = bool(item["naechste"] and item["balken"] and not item["geheim"])
            self.assertEqual(len(bars), 1 if show_bar else 0, item["id"])
            if show_bar:
                self.assertAlmostEqual(bars[0].get(), item["anteil"], places=3)
                self.assertEqual(bars[0].cget("progress_color"),
                                 self.gg.tier_color(item["naechste"]["tier"]))
            tile.destroy()
            geprueft += 1
        print("\n  Abzeichen-Kacheln: %d (Spielstand %d, dazu je Stufe und geheim)"
              % (geprueft, len(items)))

    def test_bestwerte_gegen_daten(self):
        state = self.game.state
        records = self.game.records()
        self._bestwerte(records, state)
        # Zwei Durchgaenge: ein frueherer mit hoeherem Wert, damit Rekord-
        # und Nicht-Rekord-Kacheln vorkommen
        board = self._bestwerte(_zwei_durchgaenge(records, state), state)
        rekord = [item["rekord"] for item in board["werte"] if item["wert"] is not None]
        self.assertIn(True, rekord)
        self.assertIn(False, rekord)

    def _bestwerte(self, records, state):
        from fisi_theme import C
        for child in self.frame.winfo_children():
            child.destroy()
        board = fg.record_board(records, state)
        fake = types.SimpleNamespace(content=self.frame,
                                     game=types.SimpleNamespace(records=lambda: records))
        self.gg.JourneyView._build_records(fake, state)
        self._pump()
        card = self.frame.winfo_children()[0]
        self.assertEqual(card.subtitle_label.cget("text"), fg.record_subtitle(board))
        grids = [w for w in card.body.winfo_children() if w.grid_slaves()]
        self.assertEqual(len(grids), 1)
        tiles = sorted(grids[0].grid_slaves(),
                       key=lambda w: (int(w.grid_info()["row"]), int(w.grid_info()["column"])))
        self.assertEqual(len(tiles), len(board["werte"]))
        for tile, item in zip(tiles, board["werte"]):
            labels = [w for w in tile.winfo_children() if type(w).__name__ == "CTkLabel"]
            self.assertEqual([w.cget("text") for w in labels],
                             [item["name"].upper(), item["wert_text"],
                              fg.record_detail(item, board["durchgaenge"])], item["name"])
            self.assertEqual(labels[1].cget("text_color"),
                             C["text"] if item["wert"] is not None else C["muted"])
            mark = item["rekord"] and board["durchgaenge"] > 1
            self.assertEqual(tile.cget("border_color"), C["yellow"] if mark else C["border"])
        print("\n  Bestwerte PC: %d Kacheln, %d Durchgaenge"
              % (len(tiles), board["durchgaenge"]))
        return board


# ---------------------------------------------------------------------------
#  Handy
# ---------------------------------------------------------------------------

def _flet_ok():
    try:
        import flet  # noqa: F401
        import spiel  # noqa: F401
        return True
    except Exception:  # noqa: BLE001
        return False


class HandyZeichnenTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # nie still ueberspringen: ohne flet/spiel.py ist der Test rot
        if not _flet_ok():
            raise AssertionError("flet/spiel.py nicht ladbar - dieser Test darf nicht "
                                 "uebersprungen werden (mobile/vorbereiten.py ausfuehren)")
        cls.folder = tempfile.mkdtemp(prefix="fisi_abzeichen_handy_")
        cls.game = _spielstand(os.path.join(cls.folder, "t.db"))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.folder, ignore_errors=True)

    @staticmethod
    def _alle(control):
        """Alle Steuerelemente unter control (Tiefensuche, Reihenfolge)."""
        out = [control]
        for name in ("content", "controls"):
            value = getattr(control, name, None)
            if isinstance(value, list):
                for item in value:
                    out += HandyZeichnenTest._alle(item)
            elif value is not None and hasattr(value, "__dict__") and \
                    not isinstance(value, (str, bytes)):
                out += HandyZeichnenTest._alle(value)
        return out

    @staticmethod
    def _gezeichnet(canvas):
        out = []
        for shape in canvas.shapes:
            out.append((type(shape).__name__, str(shape.paint.color).lower()))
        return out

    @staticmethod
    def _soll(shapes):
        """Handy: je Flaeche erst die Fuellung, dann der Rand (eigene Form)."""
        names = {"rect": "Rect", "oval": "Oval", "poly": "Path"}
        out = []
        for shape in shapes:
            kind = shape["k"]
            if kind in names:
                if shape["fill"]:
                    out.append((names[kind], shape["fill"].lower()))
                if shape["line"]:
                    out.append((names[kind], shape["line"].lower()))
            elif kind == "line":
                out.append(("Line", shape["color"].lower()))
            elif kind == "arc":
                out.append(("Arc", shape["color"].lower()))
        return out

    def _screen(self):
        import spiel
        return types.SimpleNamespace(game=self.game, badge_group="alle",
                                     _badge_choose=lambda group: None,
                                     _badge_tile=spiel.GameScreen._badge_tile)

    def test_badge_image_jedes_bild_jede_farbe_jede_stufe(self):
        import spiel
        bilder, farben = _bilder_farben()
        geprueft = 0
        for picture in bilder:
            for color in farben:
                for tier in TIERS:
                    canvas = spiel.badge_image(picture, color, tier, 56)
                    self.assertEqual(self._gezeichnet(canvas),
                                     self._soll(fg.badge_shapes(picture, color, tier)),
                                     "%s/%s/%s" % (picture, color, tier))
                    if tier:
                        rings = [s for s in canvas.shapes if type(s).__name__ == "Oval"]
                        self.assertIn(fg.TIER_COLORS[tier].lower(),
                                      [str(s.paint.color).lower() for s in rings])
                    geprueft += 1
        print("\n  badge_image Handy: %d Kombinationen" % geprueft)

    def test_abzeichen_kachel_gegen_daten(self):
        import flet as ft
        import spiel
        from fisi_theme import C
        state = self.game.state
        items = fg.achievement_overview(state, self.game.topic_knowledge(),
                                        self.game.records())
        for item in _abzeichen_varianten(items):
            tile = spiel.GameScreen._badge_tile(item)
            controls = self._alle(tile)
            canvases = [c for c in controls if type(c).__name__ == "Canvas"]
            self.assertEqual(len(canvases), 1, item["id"])
            self.assertEqual(self._gezeichnet(canvases[0]),
                             self._soll(fg.badge_shapes(item["bild"], item["farbe"],
                                                        item["tier"])), item["id"])
            tier = item["tier"]
            self.assertEqual(tile.border.top.color,
                             spiel.tier_color(tier) if tier else C["border"])
            texts = [c for c in controls if isinstance(c, ft.Text)]
            self.assertEqual(texts[0].value, "???" if item["geheim"] else item["name"])
            status, color = fg.badge_status(item)
            self.assertEqual(texts[1].value, status)
            self.assertEqual(texts[1].color, fg.tier_text_color(color))
            self.assertEqual(texts[2].value, "Noch nicht entdeckt." if item["geheim"]
                             else item["text"])
            bars = [c for c in controls if isinstance(c, ft.ProgressBar)]
            show_bar = bool(item["naechste"] and item["balken"] and not item["geheim"])
            self.assertEqual(len(bars), 1 if show_bar else 0)
            if show_bar:
                self.assertAlmostEqual(bars[0].value, item["anteil"], places=3)

    def test_bestwerte_und_abzeichen_seite(self):
        records = self.game.records()
        self._seite(records)
        board = self._seite(_zwei_durchgaenge(records, self.game.state))
        self.assertEqual(board["durchgaenge"], 2)

    def _seite(self, records):
        import flet as ft
        import spiel
        from fisi_theme import C
        state = self.game.state
        board = fg.record_board(records, state)
        screen = self._screen()
        screen.game = types.SimpleNamespace(records=lambda: records,
                                            topic_knowledge=self.game.topic_knowledge)
        controls = spiel.GameScreen._achievements(screen, state)
        bestwerte = controls[0]
        texts = [c.value for c in self._alle(bestwerte) if isinstance(c, ft.Text)]
        self.assertIn(fg.record_subtitle(board), texts)
        kacheln = [c for c in self._alle(bestwerte) if isinstance(c, ft.Container)
                   and isinstance(c.content, ft.Column) and c.expand]
        self.assertEqual(len(kacheln), len(board["werte"]))
        for tile, item in zip(kacheln, board["werte"]):
            values = [c for c in tile.content.controls if isinstance(c, ft.Text)]
            self.assertEqual([c.value for c in values],
                             [item["name"].upper(), item["wert_text"],
                              fg.record_detail(item, board["durchgaenge"])])
            self.assertEqual(values[1].color,
                             C["text"] if item["wert"] is not None else C["muted"])
            mark = item["rekord"] and board["durchgaenge"] > 1
            self.assertEqual(tile.border.top.color, C["yellow"] if mark else C["border"])
        items = fg.achievement_overview(state, self.game.topic_knowledge(), records)
        canvases = [c for c in self._alle(controls[1]) if type(c).__name__ == "Canvas"]
        self.assertEqual(len(canvases), len(items))
        for canvas, item in zip(canvases, items):
            self.assertEqual(self._gezeichnet(canvas),
                             self._soll(fg.badge_shapes(item["bild"], item["farbe"],
                                                        item["tier"])), item["id"])
        print("\n  Handy: %d Bestwerte, %d Abzeichen" % (len(kacheln), len(canvases)))
        return board


if __name__ == "__main__":
    unittest.main(verbosity=2)
