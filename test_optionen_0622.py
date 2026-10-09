#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests fuer 0.62.2 (Optionen aufraeumen, Plan 0.62.2 Abschnitt 7.2):

  1. PC und Handy gleich: Reihenfolge der gebauten Bereiche, Titel und
     Zwischenueberschriften (Ausnahme nur "Datenbank", gibt es nur am PC)
  2. "Über das Programm" startet offen und gebaut, laesst sich zuklappen,
     ist nach erneutem Betreten wieder offen und bleibt nach einem
     Farbwechsel zu, wenn er zugeklappt war (PC und Handy)
  3. Inhalt der zusammengelegten Bereiche "Optische Anpassungen" und
     "Lerninhalte"; die alten Kennungen gibt es nicht mehr
  4. Suche
  5. Rundgang "Jetzt einrichten": "Lerninhalte" zeigt die neuen Werte
  6. Hilfe-Texte nennen die neuen Orte, "ganz unten" faellt weg
  7. Tastatur: Klappkoepfe in der neuen Reihenfolge, Zwischenueberschriften
     nehmen keinen Fokus
  8. reset_folds mit gebautem "Optische Anpassungen" und offenen "Vorlagen"
  9. Schriftwechsel mit offenem "Optische Anpassungen"

Kein Test wird uebersprungen: Fehlt Tk (Anzeige) oder Flet, werden die
Tests rot (Test 1 braucht beides in einem Lauf, Auflage der Freigabe).

Start:  python test_optionen_0622.py   (braucht eine Anzeige, z.B. xvfb-run)
"""

import os
import shutil
import sys
import tempfile
import traceback
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.chdir(HERE)

_TMP = tempfile.mkdtemp(prefix="fisi_optionen_0622_")
os.environ["FISI_DB_PATH"] = os.path.join(_TMP, "optionen.db")
os.environ.setdefault("FISI_SELFTEST", os.path.join(_TMP, "selbsttest.log"))
os.environ["HOME"] = _TMP
os.environ["APPDATA"] = _TMP

import fisi_hilfe as fh  # noqa: E402
import fisi_optionen as fo  # noqa: E402
import fisi_rahmenplan as frp  # noqa: E402
import fisi_theme as th  # noqa: E402

PC_IDS = ["updates", "rundgang", "optik", "tagesziel", "abgleich", "sicherung",
          "datenbank", "lerninhalte", "spiel", "loeschen", "diagnose", "ueber"]
HANDY_IDS = [key for key in PC_IDS if key != "datenbank"]
OLD_IDS = ("schrift", "farben", "rahmenplan")

# Beim Start der Module gesammelt: fehlt Tk oder Flet, scheitern die Tests
# (statt still uebersprungen zu werden)
_PROBLEMS = {}
PC = None
HANDY = None


def setUpModule():
    global PC, HANDY
    try:
        PC = _start_pc()
    except Exception:  # noqa: BLE001
        _PROBLEMS["pc"] = traceback.format_exc()
    try:
        HANDY = _start_handy()
    except Exception:  # noqa: BLE001
        _PROBLEMS["handy"] = traceback.format_exc()


def tearDownModule():
    if PC is not None:
        try:
            root = PC["root"]
            for job in root.tk.splitlist(root.tk.call("after", "info")):
                root.tk.call("after", "cancel", job)
            root.destroy()
        except Exception:  # noqa: BLE001
            pass
    th.custom_colors.clear()
    shutil.rmtree(_TMP, ignore_errors=True)


def _start_pc():
    import customtkinter as ctk
    import app_gui
    import fisi_widgets as fw
    fh.mark_tour_seen()
    app_gui.UpdateController.auto_check = lambda self: None
    app_gui.SyncController.auto_start = lambda self: None
    for name in ("showinfo", "showwarning", "showerror"):
        setattr(app_gui.messagebox, name, lambda *a, **k: None)
    root = ctk.CTk()
    errors = []
    root.report_callback_exception = lambda *exc: errors.append(exc)
    root.geometry("1360x880+0+0")
    app = app_gui.FISIApp(root)
    root.maxsize(4000, 3000)
    root.geometry("1360x880+0+0")
    state = {"root": root, "app": app, "app_gui": app_gui, "fw": fw, "ctk": ctk,
             "errors": errors}
    _settle(state)
    return state


def _settle(state, times=6):
    for _ in range(times):
        state["root"].update_idletasks()
        state["root"].update()


def _start_handy():
    import flet as ft
    sys.path.insert(1, os.path.join(HERE, "mobile", "src"))
    import main
    import ui

    class FakePage:
        views = []

        def __getattr__(self, _name):
            return lambda *args, **kwargs: None

    class FakeApp(main.FISIMobileApp):
        def __init__(self):
            self.page = FakePage()
            self.body = ft.Container()
            self.db = main.DBManager()
            self.sync = main.SyncController(self)
            self.perf = main.MobilePerf(self)
            self.screens = {}
            self._recoloring = False

    return {"ft": ft, "main": main, "ui": ui, "app": FakeApp()}


class Case(unittest.TestCase):
    """Gemeinsame Helfer. Jeder Test scheitert, wenn PC oder Handy fehlt."""

    need = ("pc", "handy")

    def setUp(self):
        for key in self.need:
            if key in _PROBLEMS:
                self.fail("%s nicht startbar (Test darf nicht uebersprungen "
                          "werden):\n%s" % (key, _PROBLEMS[key]))
        if PC is not None:
            PC["errors"][:] = []

    def tearDown(self):
        if PC is not None:
            errors, PC["errors"][:] = list(PC["errors"]), []
            self.assertFalse(errors, "".join(
                "".join(traceback.format_exception(*exc)) for exc in errors))

    # -- PC ------------------------------------------------------------------

    def settle(self, times=6):
        _settle(PC, times)

    def pc_view(self, enter=True):
        """Optionen am PC; enter=True: wie von einer anderen Seite betreten."""
        app = PC["app"]
        if enter:
            app.show_view("dashboard")
            self.settle()
            app.show_view("settings")
            self.settle()
        return app.views["settings"]

    def walk(self, widget):
        yield widget
        for child in widget.winfo_children():
            yield from self.walk(child)

    def pc_texts(self, widget):
        """Texte aller Beschriftungen in der Reihenfolge des Aufbaus."""
        ctk = PC["ctk"]
        return [w.cget("text") for w in self.walk(widget) if isinstance(w, ctk.CTkLabel)]

    def pc_section_labels(self, view, area_id):
        ctk = PC["ctk"]
        titles = [title.upper() for title in self.section_titles(area_id)]
        return [w for w in self.walk(view.folds[area_id].body)
                if isinstance(w, ctk.CTkLabel) and w.cget("text") in titles]

    # -- Handy -----------------------------------------------------------------

    def handy_screen(self, fresh=True):
        """Optionen am Handy; fresh=True vergisst gemerkte Klappzustaende."""
        if fresh:
            HANDY["ui"].FoldCard.reset_states(fo.STATE_PREFIX)
        return HANDY["main"].SCREEN_CLASSES["settings"](HANDY["app"])

    def handy_texts(self, control):
        ft = HANDY["ft"]
        texts = []

        def visit(item):
            if isinstance(item, ft.Text):
                texts.append(item.value)
            for name in ("content", "controls"):
                value = getattr(item, name, None)
                if isinstance(value, ft.Control):
                    visit(value)
                elif isinstance(value, list):
                    for child in value:
                        if isinstance(child, ft.Control):
                            visit(child)
        visit(control)
        return texts

    # -- gemeinsam ---------------------------------------------------------------

    @staticmethod
    def section_titles(area_id):
        return [item["titel"] for item in fo.sections(area_id)]

    def headings(self, texts, area_id):
        """Zwischenueberschriften (Grossbuchstaben) eines Bereichs in Reihenfolge."""
        titles = [title.upper() for title in self.section_titles(area_id)]
        return [text for text in texts if text in titles]


# ============================================================================
#  1. PC und Handy gleich
# ============================================================================

class GleichTest(Case):

    def test_1_reihenfolge_titel_und_ueberschriften(self):
        view = self.pc_view()
        screen = self.handy_screen()
        pc_order = list(view.areas)
        handy_order = list(screen.areas)
        self.assertEqual(pc_order, PC_IDS)
        self.assertEqual([key for key in pc_order if key != "datenbank"], handy_order)
        self.assertNotIn("datenbank", handy_order)
        for area_id in handy_order:
            if area_id in view.folds:
                self.assertEqual(view.folds[area_id].fold_title,
                                 screen.folds[area_id]._fold_title, area_id)
                self.assertEqual(view.folds[area_id].fold_title,
                                 fo.AREA_BY_ID[area_id]["titel"], area_id)
            else:
                self.assertNotIn(area_id, screen.folds, area_id)
        # Zwischenueberschriften je Bereich gleich (PC: Bereich bauen)
        for area_id in (fo.OPTIK_ID, fo.LEARN_ID, fo.DIAGNOSE_ID):
            view.folds[area_id].ensure_built()
            self.settle()
            pc_heads = self.headings(self.pc_texts(view.folds[area_id].body), area_id)
            handy_heads = self.headings(self.handy_texts(screen.areas[area_id]), area_id)
            expected = [item["titel"].upper() for item in fo.sections(area_id, pc=False)]
            self.assertEqual(handy_heads, expected, area_id)
            if area_id == fo.DIAGNOSE_ID:
                # am PC zusaetzlich "Hänger-Diagnose" (nur_pc, seit 0.59.2)
                self.assertEqual([h for h in pc_heads if h in expected], expected)
            else:
                self.assertEqual(pc_heads, expected, area_id)


# ============================================================================
#  2. "Über das Programm"
# ============================================================================

class UeberTest(Case):

    def test_2_pc_offen_zuklappbar_wieder_offen_farbwechsel(self):
        app, theme = PC["app"], th
        view = self.pc_view()
        about = view.folds[fo.ABOUT_ID]
        self.assertTrue(about.opened)
        self.assertTrue(about.built)
        self.assertTrue(about.body.winfo_ismapped())
        about.toggle()                       # zuklappen
        self.settle()
        self.assertFalse(about.opened)
        self.assertFalse(about.body.winfo_ismapped())
        # Farbwechsel aus den Optionen: zugeklappt bleibt zu
        was_light = theme.light
        target = theme.MODE_DARK if was_light else theme.MODE_LIGHT
        try:
            app.change_color(mode=target)
            self.settle(10)
            view = self.pc_view(enter=False)
            self.assertEqual(app.current, "settings")
            self.assertFalse(view.folds[fo.ABOUT_ID].opened)
        finally:
            back = theme.MODE_LIGHT if was_light else theme.MODE_DARK
            app.change_color(mode=back)
            self.settle(10)
        self.assertFalse(self.pc_view(enter=False).folds[fo.ABOUT_ID].opened)
        # verlassen und wieder betreten: wieder offen
        view = self.pc_view()
        self.assertTrue(view.folds[fo.ABOUT_ID].opened)
        self.assertTrue(view.folds[fo.ABOUT_ID].body.winfo_ismapped())

    def test_2_handy_offen_zuklappbar_wieder_offen_farbwechsel(self):
        screen = self.handy_screen()
        about = screen.folds[fo.ABOUT_ID]
        self.assertTrue(about.opened)
        self.assertTrue(about.body.visible)
        about.toggle()
        self.assertFalse(about.opened)
        self.assertFalse(about.body.visible)
        # Farbwechsel: die Optionen werden neu gebaut, gemerkter Zustand gilt
        rebuilt = self.handy_screen(fresh=False)
        self.assertFalse(rebuilt.folds[fo.ABOUT_ID].opened)
        # Betreten von einem anderen Reiter (reset_folds): wieder offen
        rebuilt.reset_folds()
        self.assertTrue(rebuilt.folds[fo.ABOUT_ID].opened)
        self.assertTrue(rebuilt.folds[fo.ABOUT_ID].body.visible)
        self.assertEqual([key for key, fold in rebuilt.folds.items() if fold.opened],
                         [fo.ABOUT_ID])


# ============================================================================
#  3. Inhalt der zusammengelegten Bereiche
# ============================================================================

class InhaltTest(Case):

    def test_3_alte_kennungen_gibt_es_nicht_mehr(self):
        ids = [area["id"] for area in fo.areas(True)]
        for old in OLD_IDS:
            self.assertNotIn(old, ids)
            self.assertNotIn(old, fo.AREA_BY_ID)
        view = self.pc_view()
        screen = self.handy_screen()
        for old in OLD_IDS:
            self.assertNotIn(old, view.areas)
            self.assertNotIn(old, screen.areas)

    def test_3_pc_optik_und_lerninhalte(self):
        view = self.pc_view()
        view.open_area(fo.OPTIK_ID)
        view.open_area(fo.LEARN_ID)
        self.settle()
        # SCHRIFTGRÖSSE ueber FARBEN (auch auf dem Bildschirm), dazu
        # Schriftwahl und "Vorlagen"
        heads = self.pc_section_labels(view, fo.OPTIK_ID)
        self.assertEqual([w.cget("text") for w in heads],
                         [th.FONT_TITLE.upper(), fo.COLORS_TITLE.upper()])
        self.assertLess(heads[0].winfo_rooty(), heads[1].winfo_rooty())
        self.assertTrue(view.font_choice.winfo_ismapped())
        self.assertLess(view.font_choice.winfo_rooty(), heads[1].winfo_rooty())
        self.assertIn(fo.TEMPLATES_ID, view.folds)
        self.assertGreater(view.folds[fo.TEMPLATES_ID].winfo_rooty(), heads[1].winfo_rooty())
        # Anzahl-Zeilen ueber RAHMENPLAN, darunter die Schalter
        texts = self.pc_texts(view.folds[fo.LEARN_ID].body)
        plan_at = texts.index(frp.OPTIONS_TITLE.upper())
        count_at = [i for i, text in enumerate(texts) if "Karteikarten gesamt" in text]
        self.assertTrue(count_at)
        self.assertLess(count_at[0], plan_at)
        # F4: "Testprojekte gesamt" auch am PC, gleicher Wortlaut wie am Handy
        from fisi_core import PROJEKTARBEITEN
        line = "Testprojekte gesamt: %d" % len(PROJEKTARBEITEN)
        self.assertTrue(any(line in text.split("\n") for text in texts))
        plan_head = self.pc_section_labels(view, fo.LEARN_ID)[0]
        switches = [w for w in self.walk(view.folds[fo.LEARN_ID].body)
                    if isinstance(w, PC["ctk"].CTkSwitch)]
        self.assertEqual(len(switches), len(view.rp_vars))
        self.assertTrue(all(w.winfo_rooty() > plan_head.winfo_rooty() for w in switches))

    def test_3_handy_optik_und_lerninhalte(self):
        screen = self.handy_screen()
        texts = self.handy_texts(screen.areas[fo.OPTIK_ID])
        self.assertEqual(self.headings(texts, fo.OPTIK_ID),
                         [th.FONT_TITLE.upper(), fo.COLORS_TITLE.upper()])
        self.assertLess(texts.index(th.FONT_HINT), texts.index(fo.COLORS_TITLE.upper()))
        self.assertIn(fo.TEMPLATES_ID, screen.folds)
        self.assertIn(fo.TEMPLATES_TITLE.upper(), texts)   # Kartentitel gross
        self.assertGreater(texts.index(fo.TEMPLATES_TITLE.upper()),
                           texts.index(fo.COLORS_TITLE.upper()))
        texts = self.handy_texts(screen.areas[fo.LEARN_ID])
        plan_at = texts.index(frp.OPTIONS_TITLE.upper())
        self.assertLess(texts.index(frp.OPTIONS_SUBTITLE), len(texts))
        lines = [text for text in texts if text and "gesamt" in text]
        self.assertTrue(lines)
        from fisi_core import PROJEKTARBEITEN
        self.assertTrue(any("Testprojekte gesamt: %d" % len(PROJEKTARBEITEN)
                            in text.split("\n") for text in lines))
        self.assertLess(texts.index(lines[0]), plan_at)
        self.assertGreater(texts.index(frp.WEIGHT_OPTION_HINT), plan_at)


# ============================================================================
#  4. Suche
# ============================================================================

class SucheTest(Case):

    need = ()

    def test_4_suche(self):
        def targets(word):
            return [hit[0] for hit in fo.search_options(word, True)]
        self.assertIn(fo.OPTIK_ID, targets("Schriftgröße"))
        self.assertIn(fo.LEARN_ID, targets("Rahmenplan"))
        self.assertIn(fo.LEARN_ID, targets("Prüfungstermin"))
        self.assertEqual(fo.hit_target(fo.OPTIK_TITLE, "Vorlagen"), (fo.OPTIK_ID, True))
        self.assertEqual(fo.hit_target(fo.OPTIK_TITLE, "Regler"), (fo.OPTIK_ID, False))
        # Kein Treffer zeigt die alten Titel als Bereich
        for word in ("Farbe", "Farben", "Schrift", "Schriftgröße", "Rahmenplan",
                     "Vorlagen", "Regler", "Lernfeld", "Hell", "Prüfungstermin"):
            for hit in fo.search_options(word, True) + fo.search_options(word, False):
                self.assertNotIn(hit[1], ("Farben", th.FONT_TITLE, frp.OPTIONS_TITLE),
                                 (word, hit))
                self.assertNotIn(hit[0], OLD_IDS, (word, hit))


# ============================================================================
#  5. Rundgang "Jetzt einrichten"
# ============================================================================

class RundgangTest(Case):

    def change_plan(self):
        before = frp.load_rp_settings()
        sections = {section: not before[key] for section, key in frp.SECTION_SETTING.items()}
        self.assertFalse(fh.save_setup("Test", sections, "01.10.2027", "01.05.2028"))
        return sections

    def test_5_pc_bereich_schon_gebaut(self):
        view = self.pc_view()
        view.open_area(fo.LEARN_ID)
        self.settle()
        self.assertTrue(view.built(fo.LEARN_ID))
        sections = self.change_plan()
        view.refresh_plan()          # wie TourOverlay.finish
        for section, key in frp.SECTION_SETTING.items():
            if key in view.rp_vars:
                self.assertEqual(bool(view.rp_vars[key].get()), sections[section], key)
        self.assertEqual(view.rp_dates["rp_termin_ap1"].get(), "01.10.2027")

    def test_5_pc_bereich_noch_nicht_gebaut(self):
        app = PC["app"]
        app.show_view("dashboard")
        self.settle()
        # Zweimal umfaerben: danach sind die Optionen frisch, "Lerninhalte" ungebaut
        mode = th.current_mode
        other = th.MODE_LIGHT if mode == th.MODE_DARK else th.MODE_DARK
        for target in (other, mode):
            app.change_color(mode=target)
            self.settle(10)
        view = app.views.built("settings")
        if view is not None:
            self.assertFalse(view.built(fo.LEARN_ID))
        sections = self.change_plan()
        if view is not None:
            view.refresh_plan()      # ungebaut ohne Fehler
        view = self.pc_view()
        view.open_area(fo.LEARN_ID)
        self.settle()
        for section, key in frp.SECTION_SETTING.items():
            if key in view.rp_vars:
                self.assertEqual(bool(view.rp_vars[key].get()), sections[section], key)
        self.assertEqual(view.rp_dates["rp_termin_ap1"].get(), "01.10.2027")

    def test_5_handy_neu_gebaut(self):
        self.change_plan()
        screen = self.handy_screen()
        self.assertEqual(screen.rp_dates["rp_termin_ap1"].value, "01.10.2027")
        self.assertEqual(screen.rp_dates["rp_termin_ap2"].value, "01.05.2028")


# ============================================================================
#  6. Hilfe-Texte
# ============================================================================

def _strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _strings(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _strings(item)


class HilfeTest(Case):

    need = ()

    def test_6_hilfe_nennt_die_neuen_orte(self):
        texts = []
        for name in dir(fh):
            if not name.startswith("_"):
                texts.extend(_strings(getattr(fh, name)))
        joined = "\n".join(texts)
        for old in ("unter „Farben“", "unter „Schriftgröße“", "unter „Rahmenplan“"):
            self.assertNotIn(old, joined)
        self.assertNotIn("ganz unten unter „Diagnose", joined)
        problem = [text for text in texts if "„Problem melden“" in text
                   and "„Diagnose und " in text]
        self.assertTrue(problem)
        self.assertTrue(all("ganz unten" not in text for text in problem))
        for new in ("unter „Optische Anpassungen“ bei „Farben“",
                    "Anpassungen“ bei „Schriftgröße“",
                    "unter „Lerninhalte“ bei „Rahmenplan“"):
            self.assertIn(new, joined)


# ============================================================================
#  7. Tastatur (PC)
# ============================================================================

class TastaturTest(Case):

    need = ("pc",)

    def tab(self):
        root = PC["root"]
        focus = root.tk.call("focus") or "."
        root.nametowidget(str(focus)).event_generate("<Tab>")
        self.settle(2)
        return root.nametowidget(str(root.tk.call("focus")))

    def test_7_tab_reihenfolge_und_ueberschriften_ohne_fokus(self):
        root = PC["root"]
        view = self.pc_view()
        view.open_area(fo.OPTIK_ID)
        view.open_area(fo.LEARN_ID)
        self.settle()
        heads = {view.folds[area_id].head: area_id for area_id in view.folds}
        PC["fw"].focus_widget(view.folds["rundgang"].head)
        self.settle(2)
        start = root.nametowidget(str(root.tk.call("focus")))
        seen = [start]
        for _step in range(800):
            widget = self.tab()
            if widget is start:
                break
            seen.append(widget)
        else:
            self.fail("Tab kommt nicht zum Anfang zurueck")
        inside = [w for w in seen if str(w).startswith(str(view) + ".")]
        order = [heads[w] for w in inside if w in heads]
        expected = [area["id"] for area in fo.areas(True) if area["id"] in view.folds]
        expected.insert(expected.index(fo.OPTIK_ID) + 1, fo.TEMPLATES_ID)
        self.assertEqual(order, expected)
        labels = (self.pc_section_labels(view, fo.OPTIK_ID)
                  + self.pc_section_labels(view, fo.LEARN_ID))
        self.assertEqual(len(labels), 3)
        names = {str(w) for w in inside}
        for label in labels:
            for part in self.walk(label):
                self.assertNotIn(str(part), names, label.cget("text"))


# ============================================================================
#  8. reset_folds mit gebautem "Optische Anpassungen" und offenen "Vorlagen"
# ============================================================================

class ResetTest(Case):

    def test_8_pc(self):
        view = self.pc_view()
        view.open_area(fo.OPTIK_ID, templates=True)
        self.settle()
        self.assertTrue(view.folds[fo.TEMPLATES_ID].opened)
        view.reset_folds()
        self.settle()
        self.assertFalse(view.folds[fo.TEMPLATES_ID].opened)
        self.assertFalse(view.folds[fo.OPTIK_ID].opened)
        self.assertEqual([key for key, fold in view.folds.items() if fold.opened],
                         [fo.ABOUT_ID])

    def test_8_handy(self):
        screen = self.handy_screen()
        screen.open_area(fo.OPTIK_ID, templates=True)
        self.assertTrue(screen.folds[fo.TEMPLATES_ID].opened)
        screen.reset_folds()
        self.assertFalse(screen.folds[fo.TEMPLATES_ID].opened)
        self.assertFalse(screen.folds[fo.OPTIK_ID].opened)
        self.assertEqual([key for key, fold in screen.folds.items() if fold.opened],
                         [fo.ABOUT_ID])

    def test_8_unfolded_at_start_vertraegt_vorlagen(self):
        self.assertFalse(fo.unfolded_at_start(fo.TEMPLATES_ID))
        self.assertTrue(fo.unfolded_at_start(fo.ABOUT_ID))
        self.assertEqual([area["id"] for area in fo.areas(True)
                          if fo.unfolded_at_start(area["id"])], [fo.ABOUT_ID])


# ============================================================================
#  9. Schriftwechsel mit offenem "Optische Anpassungen"
# ============================================================================

class SchriftTest(Case):

    need = ("pc",)

    def test_9_schriftwechsel_bereich_bleibt_offen(self):
        app = PC["app"]
        view = self.pc_view()
        view.open_area(fo.OPTIK_ID)
        self.settle()
        before = th.current_font_size
        target = "gross" if before != "gross" else "normal"
        try:
            app.change_font_size(target)
            self.settle(10)
            view = self.pc_view(enter=False)
            self.assertEqual(app.current, "settings")
            fold = view.folds[fo.OPTIK_ID]
            self.assertTrue(fold.opened)
            self.assertTrue(fold.built)
            self.assertEqual(view.font_choice.value, target)
            # Farben-Teile vollstaendig (auch fuer ein spaeteres Gegenmittel)
            self.assertEqual(len(view.custom_colors.sliders), 9)
        finally:
            app.change_font_size(before)
            self.settle(10)
        self.assertEqual(th.current_font_size, before)


if __name__ == "__main__":
    unittest.main(verbosity=2)
