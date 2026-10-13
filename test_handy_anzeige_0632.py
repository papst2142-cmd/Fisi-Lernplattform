#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests 0.63.2, Bauer S2a (Handy-Anzeige/Rechenweg)
=================================================

  * A2   Trainer: kein Hinweistext im Eingabefeld (wurde mit "…" gekuerzt),
         die Beschriftung steht genau einmal ueber dem Feld
  * A3   Trainer: Rechenweg im Kasten der Rechner-Ergebnisse (FitBox,
         fit_lines); Fortsetzungszeilen eingerueckter Zeilen stehen mit
         Einzug ("  = 8020" statt "8020" ab Spalte 0)
  * A4   Trainer: die sechs Arten brechen um (kein Pfeil)
  * A5-a fit_lines(..., einheitlich=True): Abschnitt ganz zweizeilig, sobald
         eine Zeile umbrechen muss; Standard (PC) unveraendert; FitBox ruft
         mit einheitlich=True auf
  * A5-c Feldbeschriftung "Netz mit Praefix (z. B. ...::/48)": U+2060 nach
         jedem "/", sichtbarer Wortlaut wie am PC
  * A5-d Bei "→ wischen" endet alles Teilbare vor dem Verlauf, rechts ein
         Leerraum von 28 px in der wischbaren Zeile
  * A3   (Meldung S2c) auch die Rechenweg-Kaesten der Rechner sind FitBoxen:
         keine Zeile abgeschnitten bei Normal/Gross/Sehr gross (384 px)
  * B-N-05 Problembericht in einer FitBox (Saetze mit Einzug, Unteilbares
         wischt), Kopieren/Speichern weiter mit dem Rohtext

Gegen einen anderen Code-Stand (Rot-Nachweis):
    HANDY0632_CODE=<ordner> python test_handy_anzeige_0632.py
"""

import math
import os
import sys
import tempfile
import types
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
CODE = os.path.abspath(os.environ.get("HANDY0632_CODE") or HERE)
sys.path.insert(0, CODE)

_TMP = tempfile.mkdtemp(prefix="fisi_handy0632_")
os.environ["FISI_DB_PATH"] = os.path.join(_TMP, "handy.db")
os.environ.setdefault("FISI_SELFTEST", os.path.join(_TMP, "selbsttest.log"))

import fisi_core as fc  # noqa: E402
import fisi_lernen as fl  # noqa: E402

sys.path.insert(1, os.path.join(CODE, "mobile", "src"))
import flet as ft  # noqa: E402
import main as handy  # noqa: E402
import ui  # noqa: E402

WJ = "⁠"
NORMAL = 7.83                      # px je Zeichen, 13 px Festbreite (Befund)


def _walk(control, found=None):
    found = [] if found is None else found
    found.append(control)
    for name in ("content", "controls"):
        child = getattr(control, name, None)
        for item in child if isinstance(child, list) else [child]:
            if item is not None and hasattr(item, "__dict__"):
                _walk(item, found)
    return found


def _texts(control):
    return [c.value for c in _walk(control) if isinstance(c, ft.Text)]


class _Db:
    def trainer_stats(self):
        return {}

    def log_trainer(self, *_args):
        pass


class _App:
    def __init__(self):
        self.db = _Db()
        self.sync = types.SimpleNamespace(schedule=lambda: None)

    def scroll_top(self):
        pass


def _trainer():
    return handy.TrainerPanel(_App())


def _set_width(box, zeichen, char_width=NORMAL):
    """FitBox auf `zeichen` Zeichen Breite stellen (wie gemessen)."""
    box._char_width = char_width
    box._box_sized(types.SimpleNamespace(width=zeichen * char_width + 30 + 0.5))
    assert box.zeichen == zeichen, (box.zeichen, zeichen)


def _norm(text):
    return "".join(text.split()).replace(":", "")


def _chunks(raw, shown):
    """Ausgabe-Zeilen je Rohzeile (fit_lines setzt Zeile fuer Zeile, die
    Reihenfolge bleibt). Liefert [(rohzeile, [ausgabezeilen])]."""
    out, pos = [], 0
    for line in raw.split("\n"):
        want, got, rows = _norm(line), "", []
        while pos < len(shown) and (not rows or len(got) < len(want)):
            if not want and rows:
                break
            rows.append(shown[pos])
            got += _norm(shown[pos])
            pos += 1
            if not want:
                break
        if got != want:
            raise AssertionError("Zeile nicht gefunden: %r -> %r" % (line, rows))
        out.append((line, rows))
    if pos != len(shown):
        raise AssertionError("Rest: %r" % shown[pos:])
    return out


# ---------------------------------------------------------------------------
#  A2, A4
# ---------------------------------------------------------------------------

class TrainerHinweisTest(unittest.TestCase):
    """A2: kein (gekuerzter) Hinweistext im Feld."""

    def test_feld_ohne_doppelten_hinweis(self):
        trainer = _trainer()
        for kind, _caption in fl.TRAINER_KINDS:
            trainer.kind_pills.select_value(kind)
            trainer.start_round()
            task = trainer.tasks[0]
            texts = _texts(trainer.fields_box)
            for key, label in task.fields:
                field = trainer.entries[key]
                self.assertIsNone(field.hint_text, (kind, label))
                self.assertEqual(texts.count(label), 1, (kind, label))


class TrainerPillenTest(unittest.TestCase):
    """A4: Arten brechen um, kein Pfeil."""

    def test_arten_brechen_um(self):
        trainer = _trainer()
        self.assertTrue(getattr(trainer.kind_pills, "umbrechen", False))
        self.assertIsNone(trainer.kind_pills.hint)
        self.assertTrue(trainer.kind_pills.row.wrap)
        self.assertEqual(trainer.kind_pills.values, [k for k, _c in fl.TRAINER_KINDS])


# ---------------------------------------------------------------------------
#  A3
# ---------------------------------------------------------------------------

class TrainerRechenwegTest(unittest.TestCase):
    """A3: Rechenweg in der FitBox, Fortsetzung mit Einzug."""

    def test_kasten_ist_fitbox(self):
        trainer = _trainer()
        self.assertIsInstance(trainer.steps, ui.FitBox)

    def test_beispiel_8020(self):
        # Befund: " 1000 0000 0010 0000 = 8020" brach vor "8020" um, die
        # Fortsetzung stand bei Spalte 0
        # (Trainer "Netz aufteilen", Schwer, Aufgabe 14, steps_schmal)
        task = fl.trainer_task("teilen", 3, 14, schmal=True)
        zeile = "  1000 0000 0010 0000 = 8020"
        self.assertIn(zeile, task.steps_schmal)
        self.assertEqual(fc.fit_lines(zeile, 22, einheitlich=True).split("\n"),
                         ["  1000 0000 0010 0000", "  = 8020"])
        trainer = _trainer()
        _set_width(trainer.steps, 22, NORMAL * 1.3)
        ui.set_box(trainer.steps, "\n".join(task.steps_schmal))
        zeilen = trainer.steps.data.value.split("\n")
        # Mit "→ wischen" (A5-d) kann die Bitreihe frueher umbrechen; der Wert
        # steht aber immer eingerueckt und mit "= " davor
        wert = [z for z in zeilen if z.endswith("8020") and "Netz" not in z]
        self.assertEqual(len(wert), 1, zeilen)
        self.assertTrue(wert[0].startswith("  ") and "= 8020" in wert[0], wert)

    def test_alle_arten_fortsetzung_mit_einzug(self):
        trainer = _trainer()
        box = trainer.steps
        geprueft = 0
        for kind, _c in fl.TRAINER_KINDS:
            for level, _n in fl.TRAINER_LEVELS:
                for seed in range(20):
                    task = fl.trainer_task(kind, level, seed, schmal=True)
                    raw = "\n".join(getattr(task, "steps_schmal", None) or task.steps)
                    for zeichen in (22, 28):
                        _set_width(box, zeichen, NORMAL * 1.3)
                        ui.set_box(box, raw)
                        shown = box.data.value.split("\n")
                        self.assertEqual(box.raw, raw)
                        # Text ohne Umbrueche zeichengleich
                        self.assertEqual(_norm(box.data.value), _norm(raw))
                        for line, rows in _chunks(raw, shown):
                            eingerueckt = line.startswith(" ") or (
                                rows and rows[0].endswith(":") and len(rows) > 1
                                and not line.endswith(":"))
                            if eingerueckt:
                                for row in rows[1:]:
                                    self.assertTrue(row.startswith(" "),
                                                    (kind, level, seed, zeichen, line, rows))
                            # Einzug der Fortsetzung nie kleiner als der Zeile
                            lead = len(line) - len(line.lstrip(" "))
                            for row in rows[1:]:
                                self.assertGreaterEqual(len(row) - len(row.lstrip(" ")),
                                                        min(lead, 2), (line, rows))
                        passt = all(len(row) <= zeichen for row in shown)
                        self.assertEqual(box.hint.visible, not passt)
                        geprueft += 1
        self.assertEqual(geprueft, 6 * 3 * 20 * 2)

    def test_check_setzt_kasten(self):
        trainer = _trainer()
        trainer.kind_pills.select_value("ipv6")
        trainer.start_round()
        task = trainer.tasks[0]
        trainer.check()
        self.assertTrue(trainer.steps.visible)
        self.assertEqual(trainer.steps.raw,
                         "\n".join(getattr(task, "steps_schmal", None) or task.steps))


class RechnerRechenwegTest(unittest.TestCase):
    """A3, Meldung S2c: Rechenwege der Rechner (auf 28 Zeichen gesetzt) wurden
    bei Sehr gross (27 Zeichen bei 384 px, gemessen) rechts abgeschnitten."""

    # Zeichen je Zeile bei 384 px: Sehr gross 27, Normal 35 (gemessen im
    # Behelf, fotos/nachher/log_*.txt); Gross liegt dazwischen
    BREITEN = (27, 31, 35)

    def _boxen(self):
        screen = FeldbeschriftungTest._screen(self)
        ergebnis = {id(b) for b in (screen.out_raid, screen.out_screen)}
        boxen = [c for c in _walk(screen.calc_box) if isinstance(c, ui.FitBox)
                 and id(c) not in ergebnis and c.raw.startswith("RECHENWEG")]
        return screen, boxen

    def test_alle_rechenwege_fitbox(self):
        screen, boxen = self._boxen()
        texte = {box.raw for box in boxen}
        for name in ("CALC_EXPLAIN_SUBNET_HANDY", "CALC_EXPLAIN_RAID_HANDY",
                     "CALC_EXPLAIN_SCREEN_HANDY", "CALC_EXPLAIN_UPS_HANDY",
                     "CALC_EXPLAIN_SUBNET_V6_HANDY"):
            self.assertIn(getattr(fc, name), texte, name)
        self.assertGreaterEqual(len(boxen), 8)

    def test_nichts_abgeschnitten(self):
        screen, _boxen = self._boxen()
        screen.calc_split("ipv4")
        screen.calc_split("ipv6")
        screen.calc_hosts()
        boxen = [b for b in _walk(screen.calc_box)
                 if isinstance(b, ui.FitBox) and b.raw.startswith("RECHENWEG")]
        self.assertGreaterEqual(len(boxen), 8)
        for box in boxen:
            raw = box.raw
            for zeichen in self.BREITEN:
                _set_width(box, zeichen, NORMAL * 1.3)
                zeilen = box.data.value.split("\n")
                self.assertTrue(all(len(z) <= zeichen for z in zeilen),
                                (zeichen, [z for z in zeilen if len(z) > zeichen]))
                self.assertFalse(box.hint.visible)
                self.assertEqual(_norm(box.data.value), _norm(raw))


# ---------------------------------------------------------------------------
#  A5-a
# ---------------------------------------------------------------------------

class FitEinheitlichTest(unittest.TestCase):

    def test_netzdaten_einheitlich(self):
        text = fc.subnet_report("192.168.10.0/26")
        neu = fc.fit_lines(text, 36, einheitlich=True).split("\n")
        koepfe = [line for line in neu if not line.startswith(" ")]
        self.assertTrue(koepfe)
        self.assertTrue(all(line.endswith(":") for line in koepfe), neu)
        self.assertNotIn("Netzadresse           : 192.168.10.0", neu)
        self.assertEqual(neu[:2], ["Netzadresse:", "  192.168.10.0"])
        self.assertEqual(_norm("\n".join(neu)), _norm(text))
        # alles passt einzeilig: bleibt einzeilig
        self.assertEqual(fc.fit_lines(text, 60, einheitlich=True), text)

    def test_abschnitte_getrennt(self):
        text = ("A     : 1\nB     : 2\n\nC     : ein langer Wert\nD     : 4\n"
                "Ein Satz ohne Spalte.")
        neu = fc.fit_lines(text, 16, einheitlich=True).split("\n")
        self.assertEqual(neu, ["A     : 1", "B     : 2", "", "C:", "  ein langer",
                               "  Wert", "D:", "  4", "Ein Satz ohne", "Spalte."])

    def test_standard_unveraendert(self):
        texte = [fc.subnet_report("192.168.10.0/26"),
                 fc.subnet_report("2001:db8:85a3::8a2e:370:7334/64"),
                 fc.raid_report("RAID 5", "4", "4000"),
                 fc.screen_report("7680", "4320", "32", "240")]
        for text in texte:
            for zeichen in range(10, 81):
                self.assertEqual(fc.fit_lines(text, zeichen),
                                 fc.fit_lines(text, zeichen, einheitlich=False))
        neu = fc.fit_lines(texte[0], 36).split("\n")
        self.assertIn("Netzadresse           : 192.168.10.0", neu)

    def test_fitbox_ruft_einheitlich(self):
        box = ui.read_box("", mono=True, scroll=True, fit=True)
        calls = []
        echt = ui.fit_lines

        def spy(text, zeichen, *args, **kwargs):
            calls.append(kwargs.get("einheitlich", args[0] if args else False))
            return echt(text, zeichen, *args, **kwargs)
        with mock.patch.object(ui, "fit_lines", spy):
            _set_width(box, 36)
            ui.set_box(box, fc.subnet_report("192.168.10.0/26"))
        self.assertTrue(calls)
        self.assertTrue(all(flag is True for flag in calls), calls)
        self.assertTrue(box.data.value.startswith("Netzadresse:\n  192.168.10.0"))


# ---------------------------------------------------------------------------
#  A5-c
# ---------------------------------------------------------------------------

class FeldbeschriftungTest(unittest.TestCase):

    def _screen(self):
        screen = handy.CalcScreen.__new__(handy.CalcScreen)
        screen.toasts = []
        screen.toast = lambda text, color=None: screen.toasts.append(text)
        screen.app = types.SimpleNamespace(
            db=fc.DBManager(os.path.join(tempfile.mkdtemp(dir=_TMP), "t.db")),
            sync=None, scroll_top=lambda: None)
        screen.build()
        return screen

    def test_wortverbinder_nach_schraegstrich(self):
        screen = self._screen()
        texts = _texts(screen.subnet_card)
        for mode in ("ipv4", "ipv6"):
            soll = fc.SUBNET_FIELD_NET[mode]
            gefunden = [t for t in texts if t and t.replace(WJ, "") == soll]
            self.assertTrue(gefunden, mode)
            for text in gefunden:
                self.assertIn("/" + WJ, text)
                self.assertEqual(text.count(WJ), soll.count("/"))
                self.assertEqual(text, soll.replace("/", "/" + WJ))
        # Die gemeinsame Konstante (PC) bleibt ohne U+2060
        self.assertNotIn(WJ, fc.SUBNET_FIELD_NET["ipv6"])


# ---------------------------------------------------------------------------
#  A5-d
# ---------------------------------------------------------------------------

class VerlaufTest(unittest.TestCase):
    """Kasten 324 px, Schrift Normal (7,83 px): 37 Zeichen; Verlauf 28 px =
    4 Zeichen."""

    SATZ = ("Ein Satz, der bei voller Breite eine Zeile aus genau "
            "siebenunddreissig Zeichen ergibt.")

    def _box(self, text):
        box = ui.read_box("", mono=True, scroll=True, fit=True)
        _set_width(box, 37)
        ui.set_box(box, text)
        return box

    def test_teilbares_endet_vor_dem_verlauf(self):
        unteilbar = "X" * 40
        box = self._box(unteilbar + "\n" + self.SATZ)
        self.assertEqual(box.zeichen, 37)
        self.assertTrue(box.hint.visible)
        frei = 37 - math.ceil(28 / NORMAL)
        zeilen = box.data.value.split("\n")
        self.assertEqual(zeilen[0], unteilbar)
        for zeile in zeilen[1:]:
            self.assertLessEqual(len(zeile), frei, zeilen)
        # ohne den zweiten Lauf stuende eine Zeile mit 37 Zeichen da
        self.assertTrue(any(len(z) > frei for z in fc.fit_lines(
            self.SATZ, 37, einheitlich=True).split("\n")))
        self.assertEqual(_norm(box.data.value), _norm(unteilbar + self.SATZ))

    def test_leerraum_rechts_nur_mit_hinweis(self):
        box = self._box("X" * 40)
        self.assertTrue(box.hint.visible)
        rest = [c for c in box.content.controls if c is not box.data]
        sichtbar = [c for c in rest if c.visible is not False]
        self.assertEqual(len(sichtbar), 1)
        self.assertEqual(sichtbar[0].width, 28)
        self.assertIs(box.content.controls[0], box.data)
        ui.set_box(box, self.SATZ)
        self.assertFalse(box.hint.visible)
        self.assertEqual([c for c in box.content.controls
                          if c is not box.data and c.visible is not False], [])
        # ohne Hinweis: Text wie bisher mit voller Breite
        self.assertEqual(box.data.value, fc.fit_lines(self.SATZ, 37, einheitlich=True))


# ---------------------------------------------------------------------------
#  B-N-05
# ---------------------------------------------------------------------------

class ProblemberichtTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        class FakePage:
            def __init__(self):
                self.views, self.overlay, self.tasks = [], [], []

            def run_task(self, handler, *args, **kwargs):
                self.tasks.append(handler)

            def __getattr__(self, _name):
                return lambda *args, **kwargs: None

        cls.app = handy.FISIMobileApp(FakePage())
        cls.screen = cls.app.screens["settings"]

    def test_kasten_ist_fitbox(self):
        box = getattr(self.screen, "report_box", None)
        self.assertIsInstance(box, ui.FitBox)
        self.assertIs(self.screen.report_text, box.text)
        self.assertEqual(box.text.size, 11)
        self.assertEqual(box.box.height, 240)
        self.assertIn(box, _walk(self.screen.root))

    def test_satz_mit_einzug_woerter_vollstaendig(self):
        box = self.screen.report_box
        _set_width(box, 30, 6.6)
        self.screen._report_key = None
        self.screen._show_report()
        roh = self.screen._report_text()
        self.assertEqual(box.raw, roh)
        zeilen = box.data.value.split("\n")
        # alle Zeichen in derselben Reihenfolge (nur Umbruch/Einzug neu)
        self.assertEqual(_norm(box.data.value), _norm(roh))
        for line, rows in _chunks(roh, zeilen):
            for row in rows:
                self.assertTrue(len(row) <= 30 or " " not in row.strip(), (line, rows))
        self.assertIn("Programmversion: %s" % handy.APP_VERSION,
                      self.screen.report_text.value.replace("\n  ", " ")
                      .replace(":\n", ": "))

    def test_kopieren_mit_rohtext(self):
        import fisi_diagnose as fdg
        self.assertEqual(self.screen._report_text(),
                         fdg.build_report(self.screen.db, handy.APP_VERSION, "Handy"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
