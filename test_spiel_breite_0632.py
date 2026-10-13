#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests ab 0.63.2 fuer die Spiel-Ansichten (Bauauftrag N5):

  B-D-01 / B-D-02  Firma (alle Reiter) und Reise (Rueckblick, Erfolge) passen
          in die sichtbare Breite: bei Normal, Gross und Sehr gross (Faktor
          1,00 / 1,15 / 1,30) und den Fenstern 1120 x 720 (Mindestgroesse),
          1280 x 720, 1366 x 768 und 1360 x 900 gilt in jedem geprueften
          Zustand:
            * kein seitlicher Schieberegler (xview == (0.0, 1.0)), der Inhalt
              ist nicht breiter als der sichtbare Bereich,
            * jeder Knopf und jedes Bedienelement liegt ganz im sichtbaren
              Bereich und ist nicht schmaler als verlangt (nicht
              abgeschnitten).
          Bei Normal und mindestens 1360 px Breite bleibt alles genau wie
          gebaut (FitWidth aendert nichts: _fit_changed == 0).
  B-D-10 Teil b  Weltkarte und Grossansicht (Grundriss) wachsen im breiten
          Fenster mit: bei 1366 x 768 genau wie bisher (Massstab nach der
          alten Formel), bei 1920 x 1080 groesser, und die Zeichnung passt
          in den sichtbaren Bereich.

Jede Schriftgroesse und jedes Fenster laeuft in einem eigenen Prozess
(Schriftgroesse und Skalierung gelten ab dem Start); das Ergebnis wird je
Prozess zwischengespeichert.

Gegen 14b3bd4 (0.63.1) rot: Firma und Reise seitlich verschiebbar (Messung
N5: +7 bis +603 px), Karte und Grundriss bei 1920 so hoch wie bei 1366.

Der Test wird NIE uebersprungen: Fehlt die Anzeige, ist er rot.
Start:  xvfb-run -a python test_spiel_breite_0632.py
"""

import json
import os
import subprocess
import sys
import tempfile
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

STUFEN = {1.0: "normal", 1.15: "gross", 1.3: "sehr_gross"}
FENSTER = ((1120, 720), (1280, 720), (1366, 768), (1360, 900))
BEDIEN = ("NeoButton", "IconButton", "CTkOptionMenu", "CTkEntry", "EntryBox",
          "CTkCheckBox", "CTkSwitch", "CTkTextbox")


# ---------------------------------------------------------------------------
#  Im Prozess
# ---------------------------------------------------------------------------

def _spielstand(path):
    """Figur mit erledigten Auftraegen, Firma gegruendet, eine Person
    eingestellt (wie test_reiter_sichtbar.py)."""
    import fisi_core
    import fisi_game as fg
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


class Ctx:
    def __init__(self, app, root):
        self.app = app
        self.root = root
        self.ergebnis = {}

    def pump(self, seconds=0.5):
        end = time.time() + seconds
        while time.time() < end:
            self.root.update()
            time.sleep(0.01)

    def pruefe(self, view, name):
        self.pump(0.4)
        fehler = []
        sicht = view.canvas.winfo_width()
        inhalt = view.inner.winfo_reqwidth()
        xview = tuple(round(x, 4) for x in view.canvas.xview())
        if xview != (0.0, 1.0):
            fehler.append("seitlich verschiebbar, xview %s" % (xview,))
        if inhalt > sicht + 1:
            fehler.append("Inhalt %d px breiter als sichtbar (%d)" % (inhalt - sicht, sicht))
        links = view.canvas.winfo_rootx()
        rechts = links + sicht
        knoepfe = 0
        stack = [view.inner]
        while stack:
            widget = stack.pop()
            for child in widget.winfo_children():
                try:
                    if not child.winfo_ismapped():
                        continue
                except Exception:  # noqa: BLE001
                    continue
                if type(child).__name__ in BEDIEN:
                    knoepfe += 1
                    x, w = child.winfo_rootx(), child.winfo_width()
                    if x < links - 1 or x + w > rechts + 1:
                        fehler.append("%s %r ausserhalb (x %d..%d, sichtbar %d..%d)" % (
                            type(child).__name__, _text(child), x - links, x + w - links, 0,
                            sicht))
                    if w < child.winfo_reqwidth() - 2 and type(child).__name__ not in (
                            "CTkTextbox", "EntryBox", "CTkEntry"):
                        fehler.append("%s %r schmaler als verlangt (%d < %d)" % (
                            type(child).__name__, _text(child), w, child.winfo_reqwidth()))
                    continue
                stack.append(child)
        self.ergebnis[name] = {"sicht": sicht, "inhalt": inhalt, "knoepfe": knoepfe,
                               "geaendert": getattr(view, "_fit_changed", None),
                               "fehler": fehler}


def _text(widget):
    try:
        return str(widget.cget("text"))[:30]
    except Exception:  # noqa: BLE001
        return ""


def _firma(ctx):
    import fisi_game as fg
    app = ctx.app
    firm = app.views["firma"]
    app.show_view("firma")
    ctx.pump(0.8)
    tabs = [tab for tab, _name in firm._tab_list()]
    if len(tabs) != len(fg.FIRM_TABS):
        ctx.ergebnis["firma/reiter"] = {"fehler": ["nur %d Reiter" % len(tabs)]}
    for tab in tabs:
        firm._choose(tab)
        ctx.pump(0.5)
        ctx.pruefe(firm, "firma/" + tab)
        state = firm.game.state
        if tab == "auftraege":
            inquiries = [item for item in state.inquiries() if not item.get("ergebnis")]
            if inquiries:
                firm._calc(inquiries[0]["id"])
                ctx.pump(0.4)
                ctx.pruefe(firm, "firma/auftraege_zuschlag")
                firm._pick_markup(fg.offer_rules()["zuschlaege"][0])
                ctx.pump(0.4)
                firm._toggle_help()
                ctx.pump(0.4)
                ctx.pruefe(firm, "firma/auftraege_kalkulation")
                firm._cancel_calc()
            tickets = [item for item in state.customer_tickets() if not item.get("an")]
            if tickets:
                firm._pick_ticket(tickets[0]["id"])
                ctx.pump(0.4)
                ctx.pruefe(firm, "firma/auftraege_zuweisen")
                firm._pick_ticket(None)
        if tab == "projekte":
            tenders = state.tenders()
            if tenders:
                firm._toggle_details(tenders[0].get("projekt") or tenders[0]["id"])
                ctx.pump(0.4)
                ctx.pruefe(firm, "firma/projekte_details")
                firm._toggle_details(tenders[0].get("projekt") or tenders[0]["id"])
        if tab == "mitarbeiter":
            staff = state.staff_list()
            firm._toggle_topics(staff[0]["id"])
            ctx.pump(0.4)
            ctx.pruefe(firm, "firma/mitarbeiter_themen")
            firm._toggle_topics(staff[0]["id"])
            firm._pick_training(staff[0]["id"])
            firm._pick_training_cat(fg.CAT_ORDER[0])
            ctx.pump(0.4)
            ctx.pruefe(firm, "firma/mitarbeiter_weiterbildung")
            firm._pick_training(staff[0]["id"])
    firm._choose(tabs[0])
    ctx.pump(0.3)


def _reise(ctx):
    app = ctx.app
    view = app.views["reise"]
    app.show_view("reise")
    ctx.pump(0.8)
    for tab, _name in view._tab_list():
        view._choose_tab(tab)
        ctx.pump(0.6)
        ctx.pruefe(view, "reise/" + tab)


def _plaene(ctx):
    """Massstab der Weltkarte und der Grossansicht Zuhause."""
    import fisi_game as fg
    import fisi_game_gui as gg
    from fisi_widgets import px
    app = ctx.app
    gv = app.views["game"]
    fg.set_map_list_mode(False)
    app.show_view("game")
    gv.render()
    ctx.pump(0.8)
    world = gv.world
    map_w, map_h = fg.map_size()
    ctx.ergebnis["plan/karte"] = {
        "breite": world.winfo_width(), "hoehe": world.winfo_height(), "scale": world.scale,
        "alt": min(world.winfo_width() / map_w, px(world.MAX_HEIGHT) / map_h),
        "zeichnung": world.scale * map_w, "sicht_hoehe": gv.canvas.winfo_height()}
    app.show_view("zuhause")
    ctx.pump(0.8)
    view = app.views["zuhause"]
    plan = view.plan
    building = plan.content()["gebaeude"]
    margin = fg.PLAN_MARGIN
    ctx.ergebnis["plan/zuhause"] = {
        "breite": plan.winfo_width(), "hoehe": plan.winfo_height(), "scale": plan.scale,
        "alt": min(plan.winfo_width() / (building["breite"] + 2 * margin),
                   px(plan.max_height) / (building["hoehe"] + 2 * margin)),
        "zeichnung": plan.scale * building["breite"], "sicht_hoehe": view.canvas.winfo_height()}
    del gg


def worker(faktor, breite, hoehe, teile):
    home = tempfile.mkdtemp(prefix="fisi_spielbreite_")
    os.environ.update(HOME=home, APPDATA=home, FISI_DB_PATH=os.path.join(home, "t.db"),
                      FISI_SELFTEST=os.path.join(home, "log.txt"), FISI_VORLADEN="0")
    _spielstand(os.environ["FISI_DB_PATH"])
    import customtkinter as ctk
    import app_gui
    import fisi_theme
    import fisi_widgets
    fisi_theme.apply_font_size(STUFEN[faktor])
    fisi_widgets.apply_ui_scale(faktor)
    app_gui.UpdateController.auto_check = lambda self: None
    app_gui.SyncController.auto_start = lambda self: None
    meldungen = []
    app_gui.messagebox.showerror = lambda *a, **k: meldungen.append(a)
    app_gui.messagebox.showinfo = lambda *a, **k: meldungen.append(a)
    root = ctk.CTk()
    root.geometry("%dx%d+0+0" % (breite, hoehe))
    app = app_gui.FISIApp(root)
    ctx = Ctx(app, root)
    ctx.pump(0.8)
    root.geometry("%dx%d+0+0" % (breite, hoehe))
    ctx.pump(0.6)
    gv = app.views["game"]
    run = [item for item in gv.game.slots() if not item["extra"] and item.get("lauf")][0]
    gv._choose(run["lauf"])
    ctx.pump(0.8)
    for teil in teile:
        try:
            {"firma": _firma, "reise": _reise, "plaene": _plaene}[teil](ctx)
        except Exception as error:  # noqa: BLE001
            import traceback
            ctx.ergebnis["%s/ausnahme" % teil] = {"fehler": ["%r\n%s" % (
                error, traceback.format_exc())]}
    if meldungen:
        ctx.ergebnis["meldungen"] = {"fehler": ["Meldungen: %r" % meldungen]}
    print("ERG " + json.dumps(ctx.ergebnis, ensure_ascii=False))
    sys.stdout.flush()
    os._exit(0)


# ---------------------------------------------------------------------------
#  Testfaelle
# ---------------------------------------------------------------------------

def _tk_ok():
    try:
        import tkinter
        root = tkinter.Tk()
        root.destroy()
        return True
    except Exception:  # noqa: BLE001
        return False


HAS_DISPLAY = False if "--fall" in sys.argv else _tk_ok()
_ERGEBNISSE = {}


def ergebnis(faktor, breite, hoehe, teile=("firma", "reise", "plaene")):
    key = (faktor, breite, hoehe, tuple(teile))
    if key not in _ERGEBNISSE:
        done = subprocess.run([sys.executable, os.path.abspath(__file__), "--fall",
                               str(faktor), str(breite), str(hoehe)] + list(teile),
                              capture_output=True, text=True, timeout=1800, cwd=HERE)
        lines = [line for line in done.stdout.splitlines() if line.startswith("ERG ")]
        _ERGEBNISSE[key] = (json.loads(lines[-1][4:]) if lines else
                            "kein Ergebnis:\n%s\n%s" % (done.stdout[-2000:],
                                                       done.stderr[-4000:]))
    return _ERGEBNISSE[key]


class BreiteBasis(unittest.TestCase):

    def setUp(self):
        if not HAS_DISPLAY:
            self.fail("keine Anzeige - dieser Test darf nicht uebersprungen werden "
                      "(unter Linux mit xvfb-run starten)")

    def run_case(self, faktor, breite, hoehe):
        result = ergebnis(faktor, breite, hoehe)
        self.assertIsInstance(result, dict, result)
        name = "%s %dx%d" % (STUFEN[faktor], breite, hoehe)
        print("\n  %s: %s" % (name, {k: (v.get("inhalt"), v.get("sicht"), v.get("geaendert"))
                                     for k, v in sorted(result.items())
                                     if k.startswith(("firma", "reise"))}))
        fehler = {k: v["fehler"] for k, v in result.items() if v.get("fehler")}
        self.assertEqual(fehler, {}, name)
        firma = [k for k in result if k.startswith("firma/")]
        reise = [k for k in result if k.startswith("reise/")]
        # 9 Reiter plus Zustaende (Kalkulation, Zuweisen, Details, Themen,
        # Weiterbildung), 2 Reiter der Reise
        self.assertGreaterEqual(len(firma), 9 + 5, sorted(firma))
        self.assertEqual(len(reise), 2, sorted(reise))
        self.assertTrue(all(result[k]["knoepfe"] for k in firma), "keine Knoepfe gefunden")
        if faktor == 1.0 and breite >= 1360:
            # Normal und breit: genau wie gebaut (abgenommenes Aussehen)
            geaendert = {k: result[k]["geaendert"] for k in firma + reise
                         if result[k]["geaendert"]}
            self.assertEqual(geaendert, {}, "%s: bei Normal zurechtgerueckt" % name)


def _make(faktor, breite, hoehe):
    def test(self):
        self.run_case(faktor, breite, hoehe)
    return test


class FirmaReiseBreiteTest(BreiteBasis):
    """B-D-01 / B-D-02"""


for _faktor, _stufe in STUFEN.items():
    for _breite, _hoehe in FENSTER:
        setattr(FirmaReiseBreiteTest, "test_%s_%dx%d" % (_stufe, _breite, _hoehe),
                _make(_faktor, _breite, _hoehe))


class PlanWaechstTest(unittest.TestCase):
    """B-D-10 Teil b: Karte und Grundriss wachsen bei 1920 mit."""

    def setUp(self):
        if not HAS_DISPLAY:
            self.fail("keine Anzeige - dieser Test darf nicht uebersprungen werden "
                      "(unter Linux mit xvfb-run starten)")

    def _plaene(self, breite, hoehe, faktor=1.0):
        result = ergebnis(faktor, breite, hoehe, ("plaene",))
        self.assertIsInstance(result, dict, result)
        self.assertEqual({k: v["fehler"] for k, v in result.items() if v.get("fehler")}, {})
        return result

    def test_bis_1366_wie_bisher(self):
        for faktor in (1.0, 1.3):
            result = self._plaene(1366, 768, faktor)
            for key in ("plan/karte", "plan/zuhause"):
                item = result[key]
                print("\n  %s %s 1366: %s" % (key, STUFEN[faktor], item))
                self.assertAlmostEqual(item["scale"], item["alt"], places=6, msg=key)

    def test_1920_groesser_und_sichtbar(self):
        klein = self._plaene(1366, 768)
        gross = self._plaene(1920, 1080)
        for key in ("plan/karte", "plan/zuhause"):
            alt, neu = klein[key], gross[key]
            print("\n  %s: 1366 Zeichnung %.0f px (Hoehe %d), 1920 Zeichnung %.0f px "
                  "(Hoehe %d, sichtbar %d)" % (key, alt["zeichnung"], alt["hoehe"],
                                               neu["zeichnung"], neu["hoehe"],
                                               neu["sicht_hoehe"]))
            # waechst mit: mindestens ein Viertel groesser als nach der alten
            # Formel und als bei 1366
            self.assertGreater(neu["scale"], 1.25 * neu["alt"], key)
            self.assertGreater(neu["zeichnung"], 1.25 * alt["zeichnung"], key)
            # und passt in den sichtbaren Bereich
            self.assertLessEqual(neu["hoehe"], neu["sicht_hoehe"], key)


if __name__ == "__main__":
    if "--fall" in sys.argv:
        pos = sys.argv.index("--fall")
        worker(float(sys.argv[pos + 1]), int(sys.argv[pos + 2]), int(sys.argv[pos + 3]),
               sys.argv[pos + 4:])
    else:
        unittest.main(verbosity=2)
