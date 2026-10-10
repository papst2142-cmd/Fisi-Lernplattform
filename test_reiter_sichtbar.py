#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test ab 0.62.3: Nach dem Vorladen ist jeder Reiter von Reise und Firma nach
dem Klick SICHTBAR - nicht nur gepackt und gemappt.

Hintergrund (Plan 0.62.3 Erfolge): Das Vorladen (TabCache.prepare_tab) legt
einen vorgebauten Reiter mit lower() nach unten, unter die Hintergrundflaeche
(CTkFrame._canvas) seines Elternrahmens. Bis 0.62.2 hob _tab_switch ihn beim
Klick nicht wieder an: Tk meldete "gemappt", der Rahmen war ueber 2000 px
hoch - und doch sah man nichts (Erfolge und 8 von 9 Firma-Reitern leer).

Ablauf wie am Bildschirm: Programm mit Vorladen starten, Spielstand waehlen,
warten bis das Vorladen fertig ist. Dann je Reiter von Reise und Firma der
echte Klickweg (Reise _choose_tab, Firma _choose), und fuer JEDEN Reiter:
  1. Stapel: der angezeigte Rahmen liegt ueber der Hintergrundflaeche
  2. Bild: unter der Reiterzeile ist Inhalt zu sehen (mehr als 2 %)

Der Spielstand wird hier selbst gebaut (Figur, alle Auftraege erledigt, Firma
gegruendet), damit es alle 9 Firma-Reiter gibt.

Der Test wird NIE uebersprungen: Fehlt die Anzeige, ist er rot.
Laeuft in der CI unter Linux (Xvfb) und Windows (pruefung/ci_tests.sh).

Start:  python test_reiter_sichtbar.py   (unter Linux z.B. mit xvfb-run)
"""

import json
import os
import shutil
import sys
import tempfile
import traceback
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from test_vorladen import AppCase, HAS_DISPLAY   # noqa: E402  vorhandene Testhilfe

MIN_INHALT = 2.0    # Prozent Bildpunkte, die sich vom Hintergrund abheben


def _firma_spielstand(path):
    """Spielfigur mit erledigten Auftraegen, Geld, Ansehen und Firma."""
    import fisi_core
    import fisi_game as fg
    db = fisi_core.DBManager(path)
    game = fg.Game(db, "PC")
    game.set_profile("Test", {})
    goal = game.content["balancing"]["gruendung"]
    # Ein Auftrag je Arbeitstag, mit Feierabend - wie im echten Spiel
    for number, task in enumerate(game.content["aufgaben"]):
        data = {"aufgabe": task["id"], "tag": number + 1, "richtig": True, "geld": 0,
                "reputation": {}}
        if number == 0:
            data["geld"] = goal["startkapital"] + 10000
            data["reputation"] = {key: 90 for key in fg.AXIS_KEYS}
        db.log_game_event(fg.EV_SOLVED, json.dumps(data), "PC")
        db.log_game_event(fg.EV_DAY_END, json.dumps({"tag": number + 1, "gehalt": 0}), "PC")
    game.reload()
    game.found_firm("Test IT-Service")
    if not game.state.firm:
        raise AssertionError("Firma nicht gegruendet")
    # Eine Bewerbung annehmen, damit "Mitarbeiter" etwas zu zeigen hat
    first = fg.applicants(game.state, game.content)[0]
    game.hire(first["id"])
    if not game.state.staff:
        raise AssertionError("niemand eingestellt")


class ReiterSichtbarTest(AppCase):
    def setUp(self):
        if not HAS_DISPLAY:
            self.fail("keine Anzeige - dieser Test darf nicht uebersprungen werden "
                      "(unter Linux mit xvfb-run starten)")
        # Wie AppCase.setUp, aber mit gegruendeter Firma statt leerer Datenbank
        self.folder = tempfile.mkdtemp(prefix="fisi reiter ")
        os.environ["FISI_DB_PATH"] = os.path.join(self.folder, "test.db")
        os.environ["FISI_SELFTEST"] = os.path.join(self.folder, "log.txt")  # kein Netz
        os.environ["HOME"] = self.folder
        os.environ.pop("FISI_VORLADEN", None)   # Vorladen muss an sein
        import customtkinter as ctk
        import app_gui
        import fisi_widgets
        self.app_gui = app_gui
        fisi_widgets.FoldCard._open_state.clear()
        fisi_widgets._PHOTO_CACHE.clear()
        fisi_widgets._IMAGE_CACHE.clear()
        _firma_spielstand(os.environ["FISI_DB_PATH"])
        app_gui.apply_appearance()
        self.errors = []
        self.root = ctk.CTk()
        self.root.report_callback_exception = lambda *exc: self.errors.append(
            "".join(traceback.format_exception(*exc)))
        self.app = app_gui.FISIApp(self.root)
        self.root.geometry("1360x900+0+0")
        self.pump(0.2)

    def tearDown(self):
        if hasattr(self, "root"):
            super().tearDown()
        else:
            shutil.rmtree(getattr(self, "folder", ""), ignore_errors=True)

    def _oben(self, view):
        """Liegt der angezeigte Reiter-Rahmen ueber der Hintergrundflaeche?"""
        tk_ = self.root.tk
        order = list(tk_.splitlist(tk_.call("winfo", "children", str(view.content))))
        body = str(view._tab_body)
        canvas = str(view.content._canvas)
        return order.index(body) > order.index(canvas)

    def _inhalt(self, view):
        """Anteil der Bildpunkte unter der Reiterzeile, die nicht Hintergrund sind."""
        from PIL import ImageGrab
        self.pump(0.3)
        row = view._tab_row
        x = view.winfo_rootx() + 10
        y = row.winfo_rooty() + row.winfo_height() + 8
        img = ImageGrab.grab(bbox=(x, y, x + 1000, y + 500)).convert("RGB")
        data = list(img.get_flattened_data()) if hasattr(img, "get_flattened_data") \
            else list(img.getdata())
        probe = data[::97]
        bg = max(set(probe), key=probe.count)
        other = sum(1 for p in data if sum(abs(a - b) for a, b in zip(p, bg)) > 30)
        return 100.0 * other / len(data)

    def test_reiter_nach_vorladen_sichtbar(self):
        app, pre = self.app, self.app.preloader
        game_view = app.views["game"]
        app.show_view("game")
        self.root.update()
        game_view._choose(game_view.game.run)
        self.root.update()
        pre.last_input = 0
        self.assertTrue(self.pump_until(lambda: pre.done), "Vorladen nicht fertig")
        geprueft, fehler = [], []
        for key in ("reise", "firma"):
            app.show_view(key)
            self.pump(0.3)
            view = app.views[key]
            click = getattr(view, "_choose_tab", None) or view._choose
            tabs = [tab for tab, _name in view._tab_list()]
            for tab in [view.tab] + [t for t in tabs if t != view.tab]:
                if tab != view.tab:
                    click(tab)
                    self.pump(0.3)
                oben = self._oben(view)
                anteil = self._inhalt(view)
                geprueft.append("%s/%s" % (key, tab))
                print("  %s/%s: oben=%s, Inhalt %.1f %%" % (key, tab, oben, anteil))
                if not oben or anteil < MIN_INHALT:
                    fehler.append("%s/%s: oben=%s, Inhalt %.1f %%" % (key, tab, oben, anteil))
        print("geprueft: %d Reiter (%s)" % (len(geprueft), ", ".join(geprueft)))
        # Reise 2 Reiter (Rueckblick, Erfolge), Firma alle 9 nach der Gruendung
        self.assertEqual(len(geprueft), 11, geprueft)
        self.assertEqual(fehler, [], "Reiter nach dem Vorladen nicht sichtbar")
        self.assertEqual(self.errors, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
