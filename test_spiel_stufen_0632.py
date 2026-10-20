#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests 0.63.2 N9 (B-J-06, FG-106): Handy-Spielansichten bei 160/200 %.

Weisung zu Meldung 42, 2.7: je Stelle S1-S6 ein Test - ab 160 % ("Extra
groß", "Maximal") stehen die Teile untereinander bzw. eine Kachel je Zeile,
bis "Sehr groß" (1,3) bleibt der Aufbau wie bisher. Dazu ein Test, dass nach
einem Wechsel 200 % -> Normal die alte Anordnung zurueckkommt (die Bausteine
entstehen neu; _stack_large setzt expand nur an den uebergebenen Bausteinen
auf None).

  S1 Reise/Rueckblick: Kacheln je Zeile 2 -> 1
  S2 Mitarbeiter: Faehigkeit (und Thema) Name ueber Balken und Wert
  S3 Mitarbeiter: "Weiterbilden", "Themen", "Entlassen" untereinander
  S4 Ticket und Serverfarm: "Lösung einreichen" und "Hilfe" untereinander
  S5 Uebersicht: Bild der Spielfigur ueber dem Text
  S6 Wissensluecke: Knopf "Karteikarten zu ..." in voller Breite
  FG-111 (Vorschlag): Angebot "Hilfe"/"Abbrechen", Kredit "Tilgungsplan"/
  "Abloesen", Reise "Neuere"/Seite/"Aeltere" ab 160 % untereinander

Die echten Methoden von mobile/src/spiel.GameScreen laufen gegen ein echtes
Spiel (Wegwerf-Datenbank, Spielstand mit Firma und einem Mitarbeiter, wie
test_reiter_sichtbar._firma_spielstand); statt der App steht ein kleiner
Ersatz mit push/page. Geprueft wird der gebaute Baum der Flet-Bausteine.

Start: python test_spiel_stufen_0632.py   (vorher python mobile/vorbereiten.py)
Gegenprobe gegen anderen Code: STUFEN_CODE=<ordner> python test_spiel_stufen_0632.py
"""

import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
CODE = os.path.abspath(os.environ.get("STUFEN_CODE") or HERE)
SRC = os.path.join(CODE, "mobile", "src")
sys.path.insert(0, SRC)
sys.path.insert(1, CODE)
_TMP = tempfile.mkdtemp(prefix="fisi_spiel_stufen_")
os.environ["HOME"] = os.environ["APPDATA"] = _TMP
os.environ["FISI_DB_PATH"] = os.path.join(_TMP, "h.db")

import flet as ft          # noqa: E402
import fisi_core           # noqa: E402
import fisi_game as fg     # noqa: E402
import ui                  # noqa: E402
import spiel               # noqa: E402

KLEIN = (1.0, 1.15, 1.3)   # Normal, Groß, Sehr groß: wie bisher
GROSS = (1.6, 2.0)         # Extra groß, Maximal: untereinander


def _spielstand(db):
    game = fg.Game(db, "Handy")
    game.set_profile("Test", {})
    goal = game.content["balancing"]["gruendung"]
    for number, task in enumerate(game.content["aufgaben"]):
        data = {"aufgabe": task["id"], "tag": number + 1, "richtig": True, "geld": 0,
                "reputation": {}}
        if number == 0:
            data["geld"] = goal["startkapital"] + 10000
            data["reputation"] = {key: 90 for key in fg.AXIS_KEYS}
        db.log_game_event(fg.EV_SOLVED, json.dumps(data), "Handy")
        db.log_game_event(fg.EV_DAY_END, json.dumps({"tag": number + 1, "gehalt": 0}), "Handy")
    game.reload()
    game.found_firm("Test IT-Service")
    game.hire(fg.applicants(game.state, game.content)[0]["id"])
    if not game.state.staff:
        raise AssertionError("niemand eingestellt")


class _Seite:
    def __init__(self):
        self.views = [object()]

    def update(self, *_args):
        pass


class _App:
    """Ersatz fuer main.FISIMobileApp: nur was GameScreen hier braucht."""

    def __init__(self, db):
        self.db = db
        self.page = _Seite()
        self.slot_chosen = True
        self.pushed = []

    def push(self, crumbs, content, toast_bis=None):     # toast_bis ab N15 (N-a)
        self.pushed.append((crumbs, content))

    def __getattr__(self, name):        # toast, info, confirm, show_unlocks ...
        return lambda *args, **kwargs: None


DB = fisi_core.DBManager(os.environ["FISI_DB_PATH"])
_spielstand(DB)


def kinder(control):
    out = []
    for attr in ("controls", "content"):
        value = getattr(control, attr, None)
        if isinstance(value, list):
            out.extend(value)
        elif isinstance(value, ft.Control):
            out.append(value)
    return out


def finde(root, treffer, eltern=None):
    """(Baustein, Eltern) aller Bausteine, auf die treffer zutrifft."""
    funde = []
    if treffer(root):
        funde.append((root, eltern))
    for kind in kinder(root):
        funde.extend(finde(kind, treffer, root))
    return funde


def pfad(root, ziel):
    """Liste der Bausteine von root bis ziel (beide eingeschlossen)."""
    if root is ziel:
        return [root]
    for kind in kinder(root):
        rest = pfad(kind, ziel)
        if rest:
            return [root] + rest
    return []


def knopf(caption):
    return lambda c: isinstance(c, ui.GradientButton) and c.caption.value == caption


def text(value):
    return lambda c: isinstance(c, ft.Text) and c.value == value


def baum(controls):
    return ft.Column(list(controls))


class _Basis(unittest.TestCase):

    def setUp(self):
        self.vorher = ui.FONT_FACTOR[0]

    def tearDown(self):
        ui.set_font_factor(self.vorher)

    def screen(self, faktor):
        ui.set_font_factor(faktor)
        app = _App(DB)
        gs = spiel.GameScreen(app)
        gs.game.reload()
        return gs, app


class S1ReiseTest(_Basis):
    """Rueckblick: zwei Kacheln je Zeile, ab 160 % eine."""

    def kacheln(self, faktor):
        gs, app = self.screen(faktor)
        gs.open_journey()
        root = app.pushed[-1][1]
        kachel_zeilen = []
        for titel in ("DIENSTTAGE", "TICKETS GELÖST", "ZWISCHENFÄLLE", "KUNDENPROJEKTE",
                      "ANGEBOTE", "VERDIENT"):
            (tx, _spalte), = finde(root, text(titel))
            weg = pfad(root, tx)               # ... Zeile, Kachel, Spalte, Text
            kachel_zeilen.append(weg[-4])
        return kachel_zeilen

    def test_bis_sehr_gross_zwei_je_zeile(self):
        for faktor in KLEIN:
            zeilen = self.kacheln(faktor)
            self.assertTrue(all(isinstance(z, ft.Row) for z in zeilen), faktor)
            self.assertEqual([len(z.controls) for z in zeilen], [2] * 6, faktor)
            self.assertEqual(len({id(z) for z in zeilen}), 3, faktor)

    def test_ab_160_eine_je_zeile(self):
        for faktor in GROSS:
            zeilen = self.kacheln(faktor)
            self.assertEqual([len(z.controls) for z in zeilen], [1] * 6, faktor)
            self.assertEqual(len({id(z) for z in zeilen}), 6, faktor)


class S2FaehigkeitenTest(_Basis):
    """Mitarbeiter: Faehigkeiten - Name neben (bis 1,3) bzw. ueber (ab 1,6)
    Balken und Wert; ebenso die aufgeklappten Themen."""

    def zeilen(self, faktor):
        """(Linie der Faehigkeit, Huelle um den Namen oder None,
        Linie des Themas, Huelle um den Themennamen oder None)"""
        gs, _app = self.screen(faktor)
        item = gs.game.state.staff_list()[0]
        gs.topics_for = {item["id"]}           # Themen aufgeklappt
        rows = gs._skill_bars(item)
        bar = fg.skill_bars(item)[0]
        (name, _r), = finde(rows, text(bar["name"]))
        weg = pfad(rows, name)                 # ... Linie, [Huelle 110,] Row(Name), Text
        huelle = weg[-3] if isinstance(weg[-3], ft.Container) else None
        linie = weg[-4] if huelle is not None else weg[-3]
        (thema, _r), = finde(rows, text(bar["themen"][0]["name"]))
        weg = pfad(rows, thema)                # ... Linie, [Huelle 92,] Text
        t_huelle = weg[-2] if isinstance(weg[-2], ft.Container) else None
        t_linie = weg[-3] if t_huelle is not None else weg[-2]
        return linie, huelle, t_linie, t_huelle

    def test_bis_sehr_gross_nebeneinander(self):
        for faktor in KLEIN:
            linie, huelle, t_linie, t_huelle = self.zeilen(faktor)
            self.assertIsInstance(linie, ft.Row, faktor)
            self.assertIs(linie.controls[0], huelle)
            self.assertEqual(huelle.width, 110, faktor)
            self.assertEqual(linie.controls[-1].width, 30, faktor)
            self.assertEqual(len(linie.controls), 3, faktor)
            self.assertIsInstance(t_linie, ft.Row, faktor)
            self.assertIs(t_linie.controls[0], t_huelle)
            self.assertEqual(t_huelle.width, 92, faktor)
            self.assertEqual(t_linie.controls[-1].width, 30, faktor)

    def test_ab_160_name_ueber_balken(self):
        for faktor in GROSS:
            linie, huelle, t_linie, t_huelle = self.zeilen(faktor)
            self.assertIsNone(huelle, faktor)
            self.assertIsInstance(linie, ft.Column, faktor)
            self.assertEqual(len(linie.controls), 2, faktor)
            self.assertIsInstance(linie.controls[1], ft.Row, faktor)
            self.assertEqual(linie.controls[1].controls[-1].width, ui.grow(30), faktor)
            self.assertIsNone(t_huelle, faktor)
            self.assertIsInstance(t_linie, ft.Column, faktor)
            self.assertIsInstance(t_linie.controls[1], ft.Row, faktor)
            self.assertEqual(t_linie.controls[1].controls[-1].width, ui.grow(30), faktor)


class S3MitarbeiterKnoepfeTest(_Basis):
    """Mitarbeiter: bis Sehr gross die Reihe von B-E-08 (Umbruch, Knoepfe in
    Textbreite), ab 160 % untereinander in voller Breite."""

    def reihe(self, faktor):
        gs, _app = self.screen(faktor)
        root = baum(gs._firm_mitarbeiter(gs.game.state))
        (_k, reihe), = finde(root, knopf("Weiterbilden"))
        return reihe

    def test_bis_sehr_gross_nebeneinander(self):
        for faktor in KLEIN:
            reihe = self.reihe(faktor)
            self.assertIsInstance(reihe, ft.Row, faktor)
            self.assertEqual([k.caption.value for k in reihe.controls],
                             ["Weiterbilden", "Themen", "Entlassen"])
            self.assertTrue(reihe.wrap, faktor)
            self.assertTrue(all(not k.expand for k in reihe.controls), faktor)
            self.assertTrue(all(k.alignment is None for k in reihe.controls), faktor)

    def test_ab_160_untereinander(self):
        for faktor in GROSS:
            reihe = self.reihe(faktor)
            self.assertIsInstance(reihe, ft.Column, faktor)
            self.assertEqual([k.caption.value for k in reihe.controls],
                             ["Weiterbilden", "Themen", "Entlassen"])
            self.assertTrue(all(not k.expand for k in reihe.controls), faktor)
            self.assertEqual(reihe.horizontal_alignment, ft.CrossAxisAlignment.STRETCH)


class S4EinreichenTest(_Basis):
    """Ticket und Serverfarm: "Lösung einreichen" neben/unter "Hilfe"."""

    def reihen(self, faktor):
        gs, app = self.screen(faktor)
        gs.open_ticket(gs.game.content["aufgaben"][0]["id"])
        ticket = app.pushed[-1][1]
        (_k, r1), = finde(ticket, knopf("Lösung einreichen"))
        gs.open_farm_task(fg.farm_tasks()[0]["id"])
        farm = app.pushed[-1][1]
        (_k, r2), = finde(farm, knopf("Lösung einreichen"))
        return r1, r2

    def test_bis_sehr_gross_nebeneinander(self):
        for faktor in KLEIN:
            for reihe in self.reihen(faktor):
                self.assertIsInstance(reihe, ft.Row, faktor)
                self.assertEqual([k.caption.value for k in reihe.controls],
                                 ["Lösung einreichen", "Hilfe"])
                self.assertTrue(reihe.controls[0].expand, faktor)

    def test_ab_160_untereinander(self):
        for faktor in GROSS:
            for reihe in self.reihen(faktor):
                self.assertIsInstance(reihe, ft.Column, faktor)
                self.assertEqual([k.caption.value for k in reihe.controls],
                                 ["Lösung einreichen", "Hilfe"])
                self.assertFalse(reihe.controls[0].expand, faktor)


class S5SpielfigurTest(_Basis):
    """Uebersicht: Bild der Spielfigur neben, ab 160 % ueber dem Text."""

    def reihe(self, faktor):
        gs, _app = self.screen(faktor)
        root = baum(gs._overview(gs.game.state))
        (tx, _s), = finde(root, lambda c: isinstance(c, ft.Text)
                          and str(c.value).startswith("Geschäftsführung · "))
        weg = pfad(root, tx)                   # ... Reihe, Spalte, Text
        return weg[-3], weg[-2]

    def test_bis_sehr_gross_nebeneinander(self):
        for faktor in KLEIN:
            reihe, spalte = self.reihe(faktor)
            self.assertIsInstance(reihe, ft.Row, faktor)
            self.assertEqual(len(reihe.controls), 2)
            self.assertIs(reihe.controls[1], spalte)
            self.assertTrue(spalte.expand, faktor)

    def test_ab_160_untereinander(self):
        for faktor in GROSS:
            reihe, spalte = self.reihe(faktor)
            self.assertIsInstance(reihe, ft.Column, faktor)
            self.assertIs(reihe.controls[1], spalte)
            self.assertFalse(spalte.expand, faktor)


class S6WissensknopfTest(_Basis):
    """Wissensluecke im Ticket: Knopf "Karteikarten zu ..." ab 160 % volle
    Breite (bis 1,3 so breit wie sein Text)."""

    def knopf(self, faktor):
        gs, app = self.screen(faktor)
        task = None
        for item in gs.game.content["aufgaben"]:
            if fg.requirement_gaps(item, gs.game.topic_knowledge()):
                task = item
                break
        self.assertIsNotNone(task, "kein Ticket mit Wissensluecke")
        gs.open_ticket(task["id"])
        (k, _r), = finde(app.pushed[-1][1], lambda c: isinstance(c, ui.GradientButton)
                        and c.caption.value.startswith("Karteikarten zu "))
        return k

    def test_bis_sehr_gross_textbreit(self):
        for faktor in KLEIN:
            self.assertFalse(self.knopf(faktor).expand, faktor)

    def test_ab_160_volle_breite(self):
        for faktor in GROSS:
            self.assertTrue(self.knopf(faktor).expand, faktor)


class StufenwechselTest(_Basis):
    """200 % -> Normal: nach dem Neuaufbau wieder die alte Anordnung (neue
    Bausteine, expand wieder gesetzt) - fuer S1, S3, S4, S5 und S6."""

    def test_200_dann_normal(self):
        gs, app = self.screen(2.0)
        gs.open_journey()
        alt_mitarbeiter = baum(gs._firm_mitarbeiter(gs.game.state))
        (alt_knopf, alt_reihe), = finde(alt_mitarbeiter, knopf("Weiterbilden"))
        self.assertIsInstance(alt_reihe, ft.Column)
        self.assertFalse(alt_knopf.expand)
        gs.open_ticket(gs.game.content["aufgaben"][0]["id"])
        alt_submit = gs.btn_submit
        self.assertFalse(alt_submit.expand)
        # Stufe zurueck auf Normal, derselbe Bildschirm baut neu auf
        ui.set_font_factor(1.0)
        neu_mitarbeiter = baum(gs._firm_mitarbeiter(gs.game.state))
        (neu_knopf, neu_reihe), = finde(neu_mitarbeiter, knopf("Weiterbilden"))
        self.assertIsNot(neu_knopf, alt_knopf)
        self.assertIsInstance(neu_reihe, ft.Row)
        self.assertTrue(neu_reihe.wrap)
        self.assertTrue(all(k.alignment is None for k in neu_reihe.controls))
        gs.open_ticket(gs.game.content["aufgaben"][0]["id"])
        self.assertIsNot(gs.btn_submit, alt_submit)
        self.assertTrue(gs.btn_submit.expand)
        (_k, reihe), = finde(app.pushed[-1][1], knopf("Lösung einreichen"))
        self.assertIsInstance(reihe, ft.Row)
        gs.open_journey()
        (tx, _s), = finde(app.pushed[-1][1], text("DIENSTTAGE"))
        weg = pfad(app.pushed[-1][1], tx)
        kachel, zeile = weg[-3], weg[-4]
        self.assertEqual(len(zeile.controls), 2)
        self.assertTrue(kachel.expand)
        overview = baum(gs._overview(gs.game.state))
        (tx, _s), = finde(overview, lambda c: isinstance(c, ft.Text)
                          and str(c.value).startswith("Geschäftsführung · "))
        weg = pfad(overview, tx)
        reihe, sp = weg[-3], weg[-2]
        self.assertIsInstance(reihe, ft.Row)
        self.assertTrue(sp.expand)



class _Reihe(_Basis):
    """FG-111 (Vorschlag): Reihe bis Sehr gross wie bisher, ab 160 %
    untereinander in voller Breite (_stack_large)."""

    def reihe(self, wurzel, caption):
        funde = finde(wurzel, knopf(caption))
        self.assertEqual(len(funde), 1, caption)
        return funde[0][1]

    def pruefen(self, reihe, faktor, anzahl, spacing, expand, wrap=False):
        if faktor in KLEIN:
            self.assertIsInstance(reihe, ft.Row, faktor)
            self.assertEqual(bool(reihe.wrap), wrap, faktor)
            self.assertEqual(len(reihe.controls), anzahl)
            if spacing is not None:
                self.assertEqual(reihe.spacing, spacing)
            knoepfe = [k for k in reihe.controls if isinstance(k, ui.GradientButton)]
            self.assertEqual([bool(k.expand) for k in knoepfe], [expand] * len(knoepfe))
        else:
            self.assertIsInstance(reihe, ft.Column, faktor)
            self.assertEqual(len(reihe.controls), anzahl)
            self.assertEqual(reihe.horizontal_alignment, ft.CrossAxisAlignment.STRETCH)
            self.assertFalse(any(getattr(k, "expand", None) for k in reihe.controls))


class AngebotReiheTest(_Reihe):
    """spiel.py _offer_calc: "Hilfe"/"Abbrechen" (Maximal: "Abbrech/en")."""

    def test_alle_stufen(self):
        for faktor in KLEIN + GROSS:
            with self.subTest(faktor=faktor):
                gs, _app = self.screen(faktor)
                gs.markup = fg.offer_rules()["zuschlaege"][0]
                gs.offer_help, gs.offer_board = False, None
                anfrage = gs.game.state.inquiries()[0]
                reihe = self.reihe(baum(gs._offer_calc(anfrage)), "Hilfe")
                self.assertIs(finde(reihe, knopf("Abbrechen"))[0][1], reihe)
                self.pruefen(reihe, faktor, 2, 8, True)


class KreditReiheTest(_Reihe):
    """spiel.py _running_loans: "Tilgungsplan"/"Abloesen" (Maximal: "Ablöse/n")."""

    @classmethod
    def setUpClass(cls):
        # eigener Spielstand mit einem laufenden Kredit (direkt als Ereignis;
        # take_loan prueft die Kreditwuerdigkeit)
        cls.db = fisi_core.DBManager(os.path.join(tempfile.mkdtemp(dir=_TMP), "k.db"))
        _spielstand(cls.db)
        game = spiel.GameScreen(_App(cls.db)).game
        game.reload()
        paket = fg.loan_rules(game.content)["pakete"][0]
        angebot = fg.loan_offer(game.state, paket["summe"], paket["laufzeit"], paket,
                                game.content)
        game._log(fg.EV_LOAN, {
            "kredit": "%s%d:1" % (fg.LOAN_PREFIX, game.state.day), "tag": game.state.day,
            "name": angebot["name"], "paket": angebot["paket"], "summe": angebot["summe"],
            "laufzeit": angebot["laufzeit"], "zins": angebot["zins"], "rate": angebot["rate"]})

    def test_alle_stufen(self):
        for faktor in KLEIN + GROSS:
            with self.subTest(faktor=faktor):
                ui.set_font_factor(faktor)
                gs = spiel.GameScreen(_App(self.db))
                gs.game.reload()
                karte = gs._running_loans(gs.game.state)
                reihe = self.reihe(karte, "Tilgungsplan")
                self.assertIs(finde(reihe, knopf("Ablösen"))[0][1], reihe)
                # B-E-08: bis Sehr gross Umbruch und Textbreite
                self.pruefen(reihe, faktor, 2, 8, False, wrap=True)


class ReiseSeitenTest(_Reihe):
    """spiel.py _fill_journey: "Neuere"/Seite/"Aeltere" (Maximal: "Älte…"
    rechts angeschnitten)."""

    def test_alle_stufen(self):
        for faktor in KLEIN + GROSS:
            with self.subTest(faktor=faktor):
                gs, _app = self.screen(faktor)
                gs.journey_tab, gs.journey_page = "rueckblick", 0
                gs.open_journey()
                reihe = self.reihe(baum(gs.journey_box.controls), "Neuere")
                self.assertIs(finde(reihe, knopf("Ältere"))[0][1], reihe)
                self.pruefen(reihe, faktor, 3, None, False)
                if faktor in KLEIN:
                    self.assertEqual(reihe.alignment, ft.MainAxisAlignment.SPACE_BETWEEN)


if __name__ == "__main__":
    unittest.main()
