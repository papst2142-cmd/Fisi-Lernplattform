#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test ab 0.63.2 (FG-109): Zahl und Einheit brechen am Handy bei 200 % nicht
mehr getrennt um - an genau den belegten Stellen S1-S8 des Antrags
(bau_0.63.2/antraege/FG-109_Antrag_Zahl_Einheit.md).

T1  spiel.euro() mit geschuetztem Leerzeichen vor "€"
T2  Untertitel "Kundenanfragen": "20 %" und "19 %" geschuetzt
T3  staff_money_text, ad_price_text, tax_status_lines Zeile "Dieser Zeitraum"
T4  Stoppgrenze: tax_status_lines Zeile 1 und "Bisher ... gezahlt" unveraendert
T5  _whole_euro unveraendert (Kreditname im Ereignis EV_LOAN), dazu T5b:
    _euro und _euro_given wie in 0.53
T6  fisi_projekt.euro geschuetzt; T6b PDF-Export byte-gleich zum alten Format
T7  Rundweg: jede neue Anzeige wird als Eingabe als dieselbe Zahl gelesen
T8  Text-Export ("Als Text") schreiben und wieder lesen (UTF-8 und, wie am PC,
    UTF-8 mit BOM und CRLF), die geschuetzten Leerzeichen bleiben erhalten

Gegenprobe mit anderem Code-Ordner:
    ZAHL_EINHEIT_CODE=<ordner> python test_zahl_einheit_0632.py
Vorher einmal: python mobile/vorbereiten.py
"""

import json
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
CODE = os.path.abspath(os.environ.get("ZAHL_EINHEIT_CODE") or HERE)
sys.path.insert(0, CODE)
sys.path.insert(1, os.path.join(CODE, "mobile", "src"))

import fisi_core as core      # noqa: E402
import fisi_game as fg        # noqa: E402
import fisi_projekt as fpj    # noqa: E402

NB = " "


class App:
    """Ersatz fuer die Handy-App (nur was GameScreen beim Aufbau braucht)."""

    def __init__(self, db):
        self.db = db
        self.slot_chosen = True
        self.page = None

    def __getattr__(self, name):
        return lambda *args, **kwargs: None


def tax_item(anzahl=2, zahllast=300):
    return {"naechste": 12, "ruecklage": 1234, "tage": 3, "ust": 190, "umsatz": 1000,
            "vorsteuer": 40, "ausgaben": 250, "zahllast": zahllast, "anzahl": anzahl,
            "gezahlt": 5000, "erstattet": 70}


PROJEKT = {"titel": "Testprojekt", "kosten_einsparung": "500", "kosten_laufend": "40",
           "material_name_0": "Server", "material_betrag_0": "4999",
           "material_name_1": "Lizenz", "material_betrag_1": "1234,5"}


class HandyEuroTest(unittest.TestCase):
    """T1 und T2 (mobile/src/spiel.py, geschuetzte Datei, S1/S2)."""

    @classmethod
    def setUpClass(cls):
        import spiel
        cls.sp = spiel

    def test_t1_euro(self):
        self.assertEqual(self.sp.euro(0), "0" + NB + "€")
        self.assertEqual(self.sp.euro(1234), "1.234" + NB + "€")
        self.assertEqual(self.sp.euro(-15000), "-15.000" + NB + "€")
        self.assertNotIn(" €", self.sp.euro(20000))

    def test_t2_untertitel_kundenanfragen(self):
        tmp = tempfile.mkdtemp(prefix="fg109_")
        try:
            db = core.DBManager(os.path.join(tmp, "h.db"))
            screen = self.sp.GameScreen(App(db))
            game = screen.game
            game.set_profile("Pruefer", {})
            goal = game.content["balancing"]["gruendung"]
            for number, task in enumerate(game.content["aufgaben"]):
                data = {"aufgabe": task["id"], "tag": number + 1, "richtig": True,
                        "geld": 0, "reputation": {}}
                if number == 0:
                    data["geld"] = goal["startkapital"] + 10000
                    data["reputation"] = {key: 90 for key in fg.AXIS_KEYS}
                db.log_game_event(fg.EV_SOLVED, json.dumps(data), "Handy", game.run)
                db.log_game_event(fg.EV_DAY_END, json.dumps({"tag": number + 1, "gehalt": 0}),
                                  "Handy", game.run)
            game.reload()
            game.found_firm("Pruef IT")
            game.reload()
            cards = screen._firm_auftraege(game.state)
            subtitles = [card.subtitle_text.value for card in cards
                         if getattr(card, "subtitle_text", None) is not None]
            text = next(s for s in subtitles if s.startswith("Handlungskosten"))
            rules = fg.offer_rules()
            self.assertEqual(text, "Handlungskosten %d%s%%, USt %d%s%%"
                             % (rules["handlungskosten"], NB, rules["ust"], NB))
            self.assertNotIn(" %", text)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class SpielTexteTest(unittest.TestCase):
    """T3-T5 (fisi_game.py, geschuetzte Datei, S3-S6)."""

    def test_t3_staff_money_text(self):
        text = fg.staff_money_text({"gehalt": 231, "umsatz": 378, "werte": {}})
        self.assertEqual(text, "Gehalt 231" + NB + "€ · Umsatz 378" + NB + "€ pro Arbeitstag")

    def test_t3_ad_price_text(self):
        text = fg.ad_price_text({"laufend": 110, "einmalig": {"preis": 900, "tage": 10}})
        self.assertEqual(text, "Laufend 110" + NB + "€ pro Arbeitstag · einmalig 900" + NB
                         + "€ für 10 Arbeitstage (90" + NB + "€ pro Tag)")

    def test_t3_tax_dieser_zeitraum(self):
        line = fg.tax_status_lines(tax_item())[1]
        self.assertTrue(line.startswith("Dieser Zeitraum"), line)
        self.assertNotIn(" €", line)
        self.assertEqual(line.count(NB + "€"), 5, line)
        refund = fg.tax_status_lines(tax_item(zahllast=-80))[1]
        self.assertIn("Erstattung 80" + NB + "€", refund)

    def test_t4_stoppgrenze_andere_zeilen_unveraendert(self):
        lines = fg.tax_status_lines(tax_item())
        self.assertEqual(len(lines), 3)
        self.assertTrue(lines[0].startswith("Steuerrücklage 1.234 € · "), lines[0])
        self.assertIn("gezahlt 5.000 €", lines[2])
        self.assertIn("erstattet 70 €", lines[2])
        self.assertNotIn(NB, lines[0] + lines[2])

    def test_t5_whole_euro_und_kreditname_unveraendert(self):
        self.assertEqual(fg._whole_euro(15000), "15.000 €")
        tmp = tempfile.mkdtemp(prefix="fg109_")
        try:
            game = fg.Game(core.DBManager(os.path.join(tmp, "h.db")), "PC")
            offer = fg.loan_offer(game.state, 15000, 100, None, game.content)
            self.assertEqual(offer["name"], "Freier Kredit 15.000 €")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_t5b_euro_und_euro_given_wie_053(self):
        self.assertEqual(fg._euro(48000), "48.000,00 €")
        self.assertEqual(fg._euro_given(48000), "48.000,00" + NB + "€")


class ProjektTest(unittest.TestCase):
    """T6, T6b und T8 (fisi_projekt.py, S7)."""

    def test_t6_euro(self):
        self.assertEqual(fpj.euro(1234.5), "1.234,50" + NB + "€")
        lines = fpj.cost_lines(PROJEKT)
        self.assertIn("Sachkosten: 6.233,50" + NB + "€", lines)
        self.assertFalse(any(" €" in line for line in lines), lines)

    def test_t6b_pdf_bytegleich_zum_alten_format(self):
        new = fpj.export_pdf(PROJEKT)
        original = fpj.euro
        fpj.euro = lambda value: original(value).replace(NB + "€", " €")
        try:
            old = fpj.export_pdf(PROJEKT)
        finally:
            fpj.euro = original
        self.assertEqual(new, old)

    def test_t8_text_export_schreiben_und_lesen(self):
        text = fpj.export_text(PROJEKT)
        self.assertEqual(text.count(NB + "€"), 6, text)
        tmp = tempfile.mkdtemp(prefix="fg109_")
        try:
            # Handy (main.py "Als Text"): UTF-8; PC (app_gui.py): UTF-8 mit BOM, CRLF
            for name, data, encoding in (
                    ("handy.txt", text.encode("utf-8"), "utf-8"),
                    ("pc.txt", text.replace("\n", "\r\n").encode("utf-8-sig"), "utf-8-sig")):
                path = os.path.join(tmp, name)
                with open(path, "wb") as handle:
                    handle.write(data)
                with open(path, "r", encoding=encoding, errors="strict", newline="") as handle:
                    back = handle.read().replace("\r\n", "\n")
                self.assertEqual(back, text, name)
                self.assertIn("Sachkosten: 6.233,50" + NB + "€", back)
                with open(path, "rb") as handle:
                    self.assertIn(b"6.233,50\xc2\xa0\xe2\x82\xac", handle.read())
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class RundwegTest(unittest.TestCase):
    """T7: angezeigte Werte lassen sich wieder als Eingabe lesen."""

    def test_t7_rundweg(self):
        import spiel
        for value in (0, 7, 378, 1234, 20000, 1234567):
            for text in (spiel.euro(value), fg._whole_euro_shown(value), fpj.euro(value)):
                self.assertEqual(fg.parse_number(text), float(value), repr(text))
                self.assertEqual(fpj.to_number(text), float(value), repr(text))
                self.assertTrue(fg.field_ok({"art": "geld", "soll": float(value)}, text),
                                repr(text))


if __name__ == "__main__":
    unittest.main()
