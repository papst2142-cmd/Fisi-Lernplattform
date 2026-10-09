# -*- coding: utf-8 -*-
"""Tests ab 0.60 (Abnahme, Auflage A2): Wege in die Optionen, seit die
Bereiche erst beim Aufklappen gebaut werden (B3).

  * jeder Suchtreffer (Strg+F) oeffnet seinen noch nie geoeffneten Bereich,
    baut ihn und holt ihn in den sichtbaren Teil
  * Treffer fuer "Vorlagen" klappt auch die Vorlagen im Bereich
    "Optische Anpassungen" auf (bis 0.62.1: Bereich "Farben")
  * Darstellungswechsel mit offenem Bereich "Optische Anpassungen", danach
    ein zweiter Bereich
  * Einrichtung im Rundgang, waehrend "Lerninhalte" (mit dem Rahmenplan,
    ab 0.62.2) noch nicht gebaut ist:
    der Bereich zeigt danach die neuen Werte
  * Tab-Taste durch die Optionen: Reihenfolge der Bereiche, nichts doppelt,
    nichts aus zugeklappten Bereichen

Aufruf:  python test_b3_wege.py   (braucht eine Anzeige, z.B. xvfb-run)
"""
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.chdir(HERE)
_TMP = tempfile.mkdtemp(prefix="fisi_b3wege_")
os.environ["FISI_DB_PATH"] = os.path.join(_TMP, "wege.db")
os.environ.setdefault("FISI_SELFTEST", os.path.join(_TMP, "selbsttest.log"))
os.environ["HOME"] = _TMP
os.environ["APPDATA"] = _TMP

import fisi_optionen as fo  # noqa: E402


class WegeTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        import customtkinter as ctk
        import app_gui
        import fisi_widgets as fw
        import fisi_theme
        cls.app_gui, cls.fw, cls.theme = app_gui, fw, fisi_theme
        app_gui.UpdateController.auto_check = lambda self: None
        app_gui.SyncController.auto_start = lambda self: None
        for name in ("showinfo", "showwarning", "showerror"):
            setattr(app_gui.messagebox, name, lambda *a, **k: None)
        cls.root = ctk.CTk()
        # Fehler in Tk-Rueckrufen (after_idle usw.) sammeln: im Programm landen
        # sie in fehler.log, hier lassen sie den Test scheitern
        cls.errors = []
        cls.root.report_callback_exception = lambda *exc: cls.errors.append(exc)
        cls.root.geometry("1360x880+0+0")
        cls.app = app_gui.FISIApp(cls.root)
        cls.root.maxsize(4000, 3000)
        cls.root.geometry("1360x880+0+0")
        cls.settle()

    @classmethod
    def tearDownClass(cls):
        try:
            for job in cls.root.tk.splitlist(cls.root.tk.call("after", "info")):
                cls.root.tk.call("after", "cancel", job)
            cls.root.destroy()
        except Exception:  # noqa: BLE001
            pass
        shutil.rmtree(_TMP, ignore_errors=True)

    @classmethod
    def settle(cls, times=6):
        for _ in range(times):
            cls.root.update_idletasks()
            cls.root.update()

    def tearDown(self):
        import traceback
        errors, self.errors[:] = list(self.errors), []
        self.assertFalse(errors, "".join(
            "".join(traceback.format_exception(*exc)) for exc in errors))

    def view(self):
        return self.app.views["settings"]

    def visible(self, view, widget):
        """Liegt der Kopf des Bereichs im sichtbaren Teil der Optionsseite?"""
        top = widget.winfo_rooty()
        return (view.canvas.winfo_rooty() - 2 <= top
                < view.canvas.winfo_rooty() + view.canvas.winfo_height())

    def walk(self, widget):
        yield widget
        for child in widget.winfo_children():
            yield from self.walk(child)

    # -- Suche ---------------------------------------------------------------

    def test_a_jeder_suchtreffer_baut_seinen_bereich(self):
        self.app.show_view("dashboard")
        self.settle()
        self.app.show_view("settings")
        self.settle()
        view = self.view()
        view.reset_folds()
        self.settle()
        checked = 0
        for area in fo.areas(True):
            area_id = area["id"]
            fold = view.folds.get(area_id)
            if fold is None:
                continue   # immer offen ("Updates"), schon gebaut
            if not view.built(area_id):
                self.assertFalse(fold.built, area_id)
            self.app.show_view("dashboard")   # Treffer kommt von einer anderen Seite
            self.settle()
            self.app.last_query = area["titel"]
            self.app.open_search_hit(fo.SEARCH_KIND, area["titel"])
            self.settle()
            view = self.view()
            self.assertEqual(self.app.current, "settings")
            self.assertTrue(view.built(area_id), area_id)
            self.assertTrue(view.folds[area_id].opened, area_id)
            self.assertTrue(view.folds[area_id].body.winfo_children(), area_id)
            self.assertTrue(self.visible(view, view.areas[area_id]), area_id)
            if area_id == fo.DIAGNOSE_ID:   # Werte nach dem Bauen eingetragen
                self.assertTrue(view.lbl_hang.cget("text"))
                self.assertTrue(view.lbl_perf.cget("text"))
            checked += 1
        self.assertGreaterEqual(checked, 10)

    def test_b_vorlagen_treffer_klappt_vorlagen_auf(self):
        view = self.view()
        view.reset_folds()
        self.settle()
        self.app.show_view("dashboard")
        self.settle()
        word = fo.TEMPLATES_TITLE
        hits = fo.search_options(word, True)
        self.assertTrue([hit for hit in hits if hit[0] == "optik" and hit[3]])
        self.app.last_query = word
        self.app.open_search_hit(fo.SEARCH_KIND, fo.AREA_BY_ID["optik"]["titel"])
        self.settle()
        view = self.view()
        self.assertTrue(view.folds["optik"].opened)
        self.assertTrue(view.folds[fo.TEMPLATES_ID].opened)
        self.assertTrue(self.visible(view, view.folds[fo.TEMPLATES_ID]))

    # -- Darstellungswechsel ---------------------------------------------------

    def test_c_wechsel_mit_offener_optik_dann_zweiter_bereich(self):
        self.app.show_view("settings")
        self.settle()
        self.view().open_area("optik")
        self.settle()
        was_light = self.theme.light
        target = self.theme.MODE_DARK if was_light else self.theme.MODE_LIGHT
        try:
            self.app.change_color(mode=target)
            self.settle(10)
            view = self.view()
            self.assertEqual(self.app.current, "settings")
            self.assertNotEqual(self.theme.light, was_light)
            for area_id in ("tagesziel", "sicherung"):
                view.open_area(area_id)
                self.settle()
                self.assertTrue(view.built(area_id), area_id)
                self.assertTrue(view.folds[area_id].body.winfo_children(), area_id)
            view.open_area("optik")
            self.settle()
            self.assertTrue(view.built("optik"))
        finally:
            back = self.theme.MODE_LIGHT if was_light else self.theme.MODE_DARK
            self.app.change_color(mode=back)
            self.settle(10)

    # -- Rundgang ----------------------------------------------------------------

    def test_d_einrichtung_vor_dem_bau_des_rahmenplans(self):
        import fisi_hilfe as fh
        import fisi_rahmenplan as frp
        self.app.show_view("dashboard")
        self.settle()
        # Zweimal umfaerben: danach sind die Optionen frisch, "Lerninhalte" ungebaut
        mode = self.theme.current_mode
        other = self.theme.MODE_LIGHT if mode == self.theme.MODE_DARK else self.theme.MODE_DARK
        for target in (other, mode):
            self.app.change_color(mode=target)
            self.settle(10)
        view = self.app.views.built("settings")
        if view is not None:
            self.assertFalse(view.built("lerninhalte"))
        before = frp.load_rp_settings()
        sections = {section: not before[key] for section, key in frp.SECTION_SETTING.items()}
        self.assertFalse(fh.save_setup("Test", sections, "", ""))
        if view is not None:
            view.refresh_plan()   # wie TourOverlay.finish, ungebaut ohne Fehler
        self.app.show_view("settings")
        self.settle()
        view = self.view()
        view.open_area("lerninhalte")
        self.settle()
        for section, key in frp.SECTION_SETTING.items():
            if key in view.rp_vars:
                self.assertEqual(bool(view.rp_vars[key].get()), sections[section], key)

    # -- Tastatur ----------------------------------------------------------------

    def tab(self):
        focus = self.root.tk.call("focus") or "."
        self.root.nametowidget(str(focus)).event_generate("<Tab>")
        self.settle(2)
        return self.root.nametowidget(str(self.root.tk.call("focus")))

    def test_e_tab_durch_die_optionen(self):
        self.app.show_view("settings")
        self.settle()
        view = self.view()
        view.reset_folds()
        view.open_area("optik")
        view.open_area("tagesziel")
        self.settle()
        heads = {view.folds[area_id].head: area_id for area_id in view.folds}
        self.fw.focus_widget(view.folds["rundgang"].head)
        self.settle(2)
        start = self.root.nametowidget(str(self.root.tk.call("focus")))
        seen = [start]
        for _step in range(600):
            widget = self.tab()
            if widget is start:
                break
            seen.append(widget)
        else:
            self.fail("Tab kommt nicht zum Anfang zurueck")
        inside = [w for w in seen if str(w).startswith(str(view) + ".")]
        self.assertEqual(len(inside), len(set(map(str, inside))), "doppelt erreicht")
        order = [heads[w] for w in inside if w in heads]
        expected = [area["id"] for area in fo.areas(True) if area["id"] in view.folds]
        # "Vorlagen" ist ein eigener Klappkopf innerhalb von "Optische Anpassungen"
        expected.insert(expected.index("optik") + 1, fo.TEMPLATES_ID)
        self.assertEqual(order, expected)
        closed = [view.folds[a].body for a in view.folds
                  if not view.folds[a].opened]
        for widget in inside:
            for body in closed:
                self.assertFalse(str(widget).startswith(str(body) + "."), str(widget))
        # Inhalt eines offenen Bereichs liegt zwischen seinem Kopf und dem naechsten
        optik = view.folds["optik"]
        positions = [i for i, w in enumerate(inside) if str(w).startswith(str(optik.body) + ".")]
        self.assertTrue(positions)
        head_at = inside.index(optik.head)
        next_head = inside.index(view.folds["tagesziel"].head)
        self.assertTrue(all(head_at < i < next_head for i in positions))


if __name__ == "__main__":
    unittest.main(verbosity=2)
