#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests fuer 0.58.1: Leistungsmessung (fisi_leistung.py) und die Reparaturen
aus der Messung (plan_0.58.1, Entscheidungen E1 bis E3).

Messfunktion:
  * aus (Vorgabe): keine Datei, keine Bindung, kein Zeitgeber
  * an: Zeilen im festen Format (Kopfzeile COLUMNS, Trennzeichen ;)
  * Obergrenze 1 MB, die aeltesten Zeilen fallen weg; Loeschen
  * ungueltige Werte in einstellungen.json gelten als aus
  * der Schalter steht nicht im Abgleich (fisi_sync.export_local)
  * PC und Handy: Seitenwechsel, Darstellung, Fenstergroesse landen in der
    Datei; Handy-Schalter mit TalkBack-Beschriftung

Reparaturen:
  * customtkinter-Version ist geprueft (CTK_IMAGE_FIX_VERSIONS) und
    CTkLabel/CTkButton tragen sich beim Zerstoeren aus ihrem CTkImage aus
  * Darstellungswechsel: Python-Objekte, Tk-Schriften, Tk-Befehle und
    Tk-Bilder wachsen nicht mehr mit jedem Wechsel
  * 20 Seitenwechsel: Bedienelemente und Zeitgeber bleiben gleich
  * Mausrad: Hineinfahren legt keine neuen Tk-Befehle mehr an
  * verdeckte Ansichten behalten ihre Groesse, die sichtbare fuellt den
    Bereich (auch nach einer Groessenaenderung)
  * Bild-Zwischenspeicher mit Obergrenze in Byte

Braucht fuer die Teile mit Oberflaeche ein Display (unter Linux xvfb-run).
Start:  python test_leistung.py
"""

import gc
import json
import os
import shutil
import sys
import tempfile
import time
import traceback
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

_TMP = tempfile.mkdtemp(prefix="fisi_leistung_")
os.environ["FISI_DB_PATH"] = os.path.join(_TMP, "leistung.db")
os.environ["FISI_SELFTEST"] = os.path.join(_TMP, "selbsttest.log")   # kein Netz

import fisi_leistung as fle  # noqa: E402
import fisi_update  # noqa: E402


def _tk_ok():
    try:
        import tkinter
        root = tkinter.Tk()
        root.destroy()
        return True
    except Exception:
        return False


HAS_DISPLAY = _tk_ok()


def _settings_file():
    return os.path.join(_TMP, "einstellungen.json")


def _reset():
    for name in ("einstellungen.json", fle.FILE_NAME):
        try:
            os.remove(os.path.join(_TMP, name))
        except FileNotFoundError:
            pass


def _rows(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read().splitlines()


class RecorderTest(unittest.TestCase):
    """Ohne Oberflaeche: Einstellung, Dateiformat, Groesse, Loeschen."""

    def setUp(self):
        _reset()

    def test_standard_aus_keine_datei(self):
        self.assertFalse(fle.enabled())
        rec = fle.Recorder("0.58.1", "PC")
        self.assertFalse(rec.active)
        for _ in range(100):
            rec.record(fle.EVENT_PAGE, von="a", nach="b", dauer_ms=1.0)
        self.assertEqual(rec.buffer, [])
        rec.flush()
        self.assertFalse(os.path.exists(fle.file_path()))
        self.assertEqual(rec.state_text(), fle.STATE_NONE)

    def test_ungueltige_werte_gelten_als_aus(self):
        for value in ("true", "ja", 1, 1.0, [True], {"an": True}, None):
            with open(_settings_file(), "w", encoding="utf-8") as handle:
                json.dump({fle.SETTING_KEY: value}, handle)
            self.assertFalse(fle.enabled(), repr(value))
        with open(_settings_file(), "w", encoding="utf-8") as handle:
            handle.write("{kaputt")
        self.assertFalse(fle.enabled())
        fle.set_enabled(True)
        self.assertTrue(fle.enabled())

    def test_einschalten_schreibt_zeilen_im_format(self):
        rec = fle.Recorder("0.58.1", "PC")
        rec.set_active(True)
        self.assertTrue(fle.enabled())                  # gespeichert
        rec.record(fle.EVENT_PAGE, von="dashboard", nach="settings", dauer_ms=42.25,
                   elemente=3300, aufgaben=25)
        rec.record(fle.EVENT_RESIZE, von="1360x880", nach="1500x900", dauer_ms=12.0,
                   max_ms=30.5, anzahl=14, ereignisse=1200, elemente=3300, aufgaben=25)
        rec.record(fle.EVENT_THEME, von="dunkel; x\ny", nach="hell", dauer_ms=900.0)
        rec.flush()
        rows = _rows(fle.file_path())
        self.assertEqual(rows[0], ";".join(fle.COLUMNS))
        self.assertEqual(len(rows), 5)                  # Kopf, start, 3 Ereignisse
        for row in rows[1:]:
            self.assertEqual(len(row.split(";")), len(fle.COLUMNS), row)
        fields = dict(zip(fle.COLUMNS, rows[2].split(";")))
        self.assertEqual(fields["version"], "0.58.1")
        self.assertEqual(fields["geraet"], "PC")
        self.assertEqual(fields["ereignis"], fle.EVENT_PAGE)
        self.assertEqual((fields["von"], fields["nach"]), ("dashboard", "settings"))
        self.assertEqual(fields["dauer_ms"], "42,2")    # Komma (Excel deutsch)
        self.assertEqual((fields["elemente"], fields["aufgaben"]), ("3300", "25"))
        self.assertTrue(fields["zeit"].startswith(time.strftime("%Y-")))
        self.assertTrue(fields["system"])
        if os.path.exists("/proc/self/statm") or sys.platform == "win32":
            self.assertTrue(fields["speicher_mb"])
        self.assertEqual(fields["customtkinter"], "")          # nur in "start"
        resize = dict(zip(fle.COLUMNS, rows[3].split(";")))
        self.assertEqual((resize["anzahl"], resize["ereignisse"], resize["max_ms"]),
                         ("14", "1200", "30,5"))
        theme = dict(zip(fle.COLUMNS, rows[4].split(";")))
        self.assertEqual(theme["von"], "dunkel, x y")   # Trennzeichen entschaerft
        self.assertIn("4 Einträge", rec.state_text())
        # Ausschalten: Zeile "ende", danach nichts mehr
        rec.set_active(False)
        self.assertFalse(fle.enabled())
        rec.record(fle.EVENT_PAGE, von="a", nach="b")
        rec.flush()
        rows = _rows(fle.file_path())
        self.assertEqual(rows[-1].split(";")[4], fle.EVENT_STOP)
        self.assertEqual(len(rows), 6)

    def test_customtkinter_version_in_der_startzeile(self):
        rec = fle.Recorder("0.58.1", "PC", toolkit="6.0.0")
        rec.set_active(True)
        rec.record(fle.EVENT_PAGE, von="a", nach="b")
        rec.set_active(False)
        rows = [dict(zip(fle.COLUMNS, row.split(";"))) for row in _rows(fle.file_path())[1:]]
        self.assertEqual([(r["ereignis"], r["customtkinter"]) for r in rows],
                         [(fle.EVENT_START, "6.0.0"), (fle.EVENT_PAGE, ""),
                          (fle.EVENT_STOP, "")])

    def test_zeilen_werden_gebuendelt(self):
        rec = fle.Recorder("0.58.1", "PC")
        rec.set_active(True)
        self.assertFalse(os.path.exists(fle.file_path()))   # erst beim flush
        for _ in range(fle.FLUSH_LINES - 1):      # mit der Zeile "start"
            rec.record(fle.EVENT_PAGE, von="a", nach="b", speicher=False)
        self.assertTrue(os.path.exists(fle.file_path()))
        self.assertEqual(rec.buffer, [])

    def test_obergrenze_1_mb(self):
        rec = fle.Recorder("0.58.1", "PC")
        rec.set_active(True)
        for index in range(12000):
            rec.record(fle.EVENT_PAGE, von="dashboard", nach="seite%05d" % index,
                       dauer_ms=1.0, speicher=False)
        rec.flush()
        size = os.path.getsize(fle.file_path())
        self.assertLessEqual(size, fle.MAX_BYTES)
        rows = _rows(fle.file_path())
        self.assertEqual(rows[0], ";".join(fle.COLUMNS))     # Kopf bleibt
        self.assertTrue(rows[-1].split(";")[6].endswith("11999"))   # neueste bleibt
        self.assertNotIn("seite00000", "\n".join(rows))       # aelteste faellt weg
        for row in rows[1:]:
            self.assertEqual(len(row.split(";")), len(fle.COLUMNS))

    def test_loeschen(self):
        rec = fle.Recorder("0.58.1", "PC")
        rec.set_active(True)
        rec.record(fle.EVENT_PAGE, von="a", nach="b")
        rec.flush()
        rec.record(fle.EVENT_PAGE, von="b", nach="c")      # noch im Puffer
        self.assertTrue(rec.delete())
        self.assertFalse(os.path.exists(fle.file_path()))
        rec.flush()
        self.assertFalse(os.path.exists(fle.file_path()))   # Puffer verworfen
        self.assertTrue(rec.delete())                       # zweimal: kein Fehler
        self.assertEqual(rec.state_text(), fle.STATE_NONE)

    def test_nicht_schreibbar_stoert_nicht(self):
        rec = fle.Recorder("0.58.1", "PC", path=os.path.join(_TMP, "fehlt", "x.csv"))
        rec.set_active(True)
        rec.record(fle.EVENT_PAGE, von="a", nach="b")
        self.assertFalse(rec.flush())
        self.assertIsNone(rec.info())

    def test_nicht_im_abgleich(self):
        import fisi_core
        import fisi_sync
        fle.set_enabled(True)
        db = fisi_core.DBManager(os.environ["FISI_DB_PATH"])
        exported = json.dumps(fisi_sync.export_local(db), ensure_ascii=False)
        self.assertNotIn(fle.SETTING_KEY, exported)
        self.assertNotIn(fle.FILE_NAME, exported)
        # Die Messdatei liegt neben der Datenbank, nicht darin
        self.assertEqual(os.path.dirname(fle.file_path()), _TMP)

    def test_gleiche_texte_pc_und_handy(self):
        with open(os.path.join(HERE, "app_gui.py"), encoding="utf-8") as handle:
            pc = handle.read()
        with open(os.path.join(HERE, "mobile", "src", "main.py"), encoding="utf-8") as handle:
            mobile = handle.read()
        # Ab 0.59 kommen die Bereichstitel fuer beide aus fisi_optionen.py
        with open(os.path.join(HERE, "fisi_optionen.py"), encoding="utf-8") as handle:
            shared = handle.read()
        self.assertIn("fle.TITLE", shared)
        self.assertIn("fo.AREA_BY_ID", pc)
        self.assertIn("fo.AREA_BY_ID", mobile)
        for name in ("SUBTITLE", "HELP", "SWITCH", "BTN_SHOW", "BTN_DELETE"):
            self.assertIn("fle." + name, pc, name)
            self.assertIn("fle." + name, mobile, name)
        import fisi_hilfe as fh
        section = [s for s in fh.HELP_SECTIONS if s["id"] == "leistung"]
        self.assertEqual(len(section), 1)
        for term in (fle.TITLE, fle.SWITCH, fle.BTN_SHOW, fle.BTN_DELETE, fle.FILE_NAME):
            self.assertIn(term, section[0]["text"])
        sys.path.insert(1, os.path.join(HERE, "mobile"))
        import vorbereiten
        self.assertIn("fisi_leistung.py", vorbereiten.SHARED_FILES)
        with open(os.path.join(HERE, ".gitignore"), encoding="utf-8") as handle:
            self.assertIn("mobile/src/fisi_leistung.py", handle.read())


class CacheTest(unittest.TestCase):

    def test_obergrenze_in_byte(self):
        from PIL import Image
        import fisi_widgets as fw
        cache = fw.BoundedCache(10 * 100 * 100 * 4)        # Platz fuer 10 Bilder
        for index in range(25):
            cache[index] = Image.new("RGBA", (100, 100))
            if index == 5:
                cache.get(0)                                # 0 wird gebraucht
        self.assertEqual(len(cache), 10)
        self.assertLessEqual(cache.bytes, cache.limit)
        self.assertNotIn(1, cache)                          # aelteste fielen weg
        self.assertIn(24, cache)
        del cache[24]
        self.assertEqual(cache.bytes, 9 * 100 * 100 * 4)
        cache.clear()
        self.assertEqual((len(cache), cache.bytes), (0, 0))
        self.assertIsInstance(fw._IMAGE_CACHE, fw.BoundedCache)
        self.assertIsInstance(fw._PHOTO_CACHE, fw.BoundedCache)


class CtkVersionTest(unittest.TestCase):
    """Die Reparatur in fisi_widgets.py (_release_image) ist fuer bestimmte
    customtkinter-Versionen geprueft. requirements.txt legt ab 0.58.1 genau
    6.0.0 fest (Entscheidung F1). Eine andere Version muss erst nachgeprueft
    werden - dann in requirements.txt und CTK_IMAGE_FIX_VERSIONS eintragen."""

    def test_requirements_legen_die_version_fest(self):
        import fisi_widgets as fw
        with open(os.path.join(HERE, "requirements.txt"), encoding="utf-8") as handle:
            pins = [line.strip() for line in handle if line.startswith("customtkinter")]
        self.assertEqual(len(pins), 1)
        self.assertTrue(pins[0].startswith("customtkinter=="), pins[0])
        self.assertIn(pins[0].split("==")[1], fw.CTK_IMAGE_FIX_VERSIONS)

    def test_version_ist_geprueft(self):
        import customtkinter as ctk
        import fisi_widgets as fw
        self.assertIn(ctk.__version__, fw.CTK_IMAGE_FIX_VERSIONS,
                      "customtkinter %s ist fuer die Bild-Reparatur (0.58.1) nicht "
                      "geprueft - test_leistung.py mit dieser Version laufen lassen "
                      "und CTK_IMAGE_FIX_VERSIONS ergaenzen" % ctk.__version__)

    @unittest.skipUnless(HAS_DISPLAY, "kein Display fuer Tk")
    def test_label_und_knopf_tragen_sich_aus(self):
        import customtkinter as ctk
        from PIL import Image
        import fisi_widgets  # noqa: F401 - bringt die Reparatur mit
        root = ctk.CTk()
        try:
            image = ctk.CTkImage(Image.new("RGBA", (20, 20)), size=(20, 20))
            widgets = [ctk.CTkLabel(root, text="", image=image),
                       ctk.CTkButton(root, text="", image=image)]
            self.assertEqual(len(image._configure_callback_list), 2)
            for widget in widgets:
                widget.destroy()
            self.assertEqual(image._configure_callback_list, [])
        finally:
            for job in root.tk.splitlist(root.tk.call("after", "info")):
                root.after_cancel(job)
            root.destroy()


@unittest.skipUnless(HAS_DISPLAY, "kein Display fuer Tk")
class PcTest(unittest.TestCase):
    """Hauptfenster einmal aufbauen; Messfunktion, Speicher und Ansichten."""

    @classmethod
    def setUpClass(cls):
        _reset()
        import customtkinter as ctk
        import app_gui
        import fisi_widgets
        cls.app_gui, cls.fw, cls.ctk = app_gui, fisi_widgets, ctk
        app_gui.UpdateController.auto_check = lambda self: None
        app_gui.SyncController.auto_start = lambda self: None
        cls.toasts = []
        app_gui.show_badge_toast = lambda _root, text, *a, **k: cls.toasts.append(text)
        app_gui.apply_appearance()
        cls.errors = []
        cls.root = ctk.CTk()
        cls.root.report_callback_exception = lambda *exc: cls.errors.append(
            "".join(traceback.format_exception(*exc)))
        cls.root.geometry("1360x880+0+0")
        cls.app = app_gui.FISIApp(cls.root)
        cls.pump(0.3)
        cls.wait_preload()

    @classmethod
    def tearDownClass(cls):
        try:
            tk_ = cls.root.tk
            for job in tk_.splitlist(tk_.call("after", "info")):
                tk_.call("after", "cancel", job)
            cls.root.destroy()
        except Exception:
            pass

    def tearDown(self):
        self.assertEqual(self.errors, [])

    @classmethod
    def pump(cls, seconds):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            cls.root.update()
            time.sleep(0.005)

    @classmethod
    def wait_preload(cls, timeout=120):
        pre = cls.app.preloader
        end = time.monotonic() + timeout
        while time.monotonic() < end and not pre.done:
            cls.root.update()
            time.sleep(0.005)

    def configure_script(self, tag):
        return str(self.root.tk.call("bind", tag, "<Configure>"))

    def after_jobs(self):
        tk_ = self.root.tk
        return len(tk_.splitlist(tk_.call("after", "info")))

    def show(self, key):
        self.app.show_view(key)
        self.pump(0.05)

    # -- Messfunktion ---------------------------------------------------------

    def test_1_aus_ohne_spuren(self):
        perf = self.app.perf
        self.assertFalse(perf.active)
        self.assertNotIn("_any_configure", self.configure_script("all"))
        self.assertNotIn("_root_configure", self.configure_script(str(self.root)))
        self.assertIsNone(perf._flush_job)
        for key in ("progress", "settings", "dashboard"):
            self.show(key)
        self.root.geometry("1400x900")
        self.pump(0.3)
        perf.rec.flush()
        self.assertFalse(os.path.exists(fle.file_path()))
        self.root.geometry("1360x880")
        self.pump(0.3)

    def test_2_schalter_in_den_optionen(self):
        self.show("settings")
        settings = self.app.views["settings"]
        self.assertEqual(settings.lbl_perf.cget("text"), fle.STATE_NONE)
        settings.var_perf.set(True)
        settings._toggle_perf()
        self.assertTrue(self.app.perf.active)
        self.assertTrue(fle.enabled())
        self.assertIn("_any_configure", self.configure_script("all"))
        self.assertIsNotNone(self.app.perf._flush_job)
        for key in ("progress", "dashboard", "settings"):
            self.show(key)
        self.pump(0.1)
        # Fenstergroesse in Schritten aendern (wie Ziehen mit der Maus)
        for width in range(1360, 1480, 20):
            self.root.geometry("%dx900" % width)
            self.pump(0.03)
        self.pump(self.app_gui.PerfMonitor.RESIZE_END_MS / 1000 + 0.3)
        self.app.change_color(mode="hell")
        self.pump(0.3)
        self.app.perf.rec.flush()
        rows = [dict(zip(fle.COLUMNS, row.split(";")))
                for row in _rows(fle.file_path())[1:]]
        events = [row["ereignis"] for row in rows]
        self.assertEqual(events[0], fle.EVENT_START)
        self.assertEqual(rows[0]["customtkinter"], self.ctk.__version__)
        pages = [(row["von"], row["nach"]) for row in rows
                 if row["ereignis"] == fle.EVENT_PAGE]
        self.assertIn(("settings", "progress"), pages)
        self.assertIn(("dashboard", "settings"), pages)
        for row in rows:
            if row["ereignis"] == fle.EVENT_PAGE:
                self.assertTrue(row["dauer_ms"] and row["elemente"] and row["aufgaben"])
        resize = [row for row in rows if row["ereignis"] == fle.EVENT_RESIZE]
        self.assertEqual(len(resize), 1)
        self.assertEqual(resize[0]["nach"], "1460x900")
        self.assertGreaterEqual(int(resize[0]["anzahl"]), 2)
        self.assertGreater(int(resize[0]["ereignisse"]), 0)
        theme = [row for row in rows if row["ereignis"] == fle.EVENT_THEME]
        self.assertEqual(len(theme), 1)
        self.assertTrue(theme[0]["von"].startswith("dunkel"))
        self.assertTrue(theme[0]["nach"].startswith("hell"))
        self.assertGreater(float(theme[0]["dauer_ms"].replace(",", ".")), 0)
        # Nach dem Neuaufbau zeigt die neue Optionen-Seite den Stand an
        self.wait_preload()
        self.show("settings")
        self.pump(0.1)
        settings = self.app.views["settings"]
        self.assertTrue(settings.var_perf.get())
        self.assertIn("Einträge", settings.lbl_perf.cget("text"))
        # Loeschen und Ausschalten
        settings.delete_perf_file()
        self.assertFalse(os.path.exists(fle.file_path()))
        self.assertIn(fle.MSG_DELETED, self.toasts)
        self.assertEqual(settings.lbl_perf.cget("text"), fle.STATE_NONE)
        commands = len(self.root._tclCommands or [])
        settings.var_perf.set(False)
        settings._toggle_perf()
        self.assertFalse(fle.enabled())
        self.assertNotIn("_any_configure", self.configure_script("all"))
        self.assertNotIn("_root_configure", self.configure_script(str(self.root)))
        self.assertIsNone(self.app.perf._flush_job)
        self.assertLess(len(self.root._tclCommands or []), commands)
        self.app.change_color(mode="dunkel")
        self.wait_preload()
        self.root.geometry("1360x880")
        self.pump(0.3)

    # -- Speicher und Ansichten -------------------------------------------------

    def test_3_bilder_halten_keine_alten_knoepfe(self):
        self.app.change_color(mode="hell")
        self.wait_preload()
        self.app.change_color(mode="dunkel")
        self.wait_preload()
        dead = 0
        for value in list(self.fw._IMAGE_CACHE.values()):
            for callback in getattr(value, "_configure_callback_list", []):
                widget = getattr(callback, "__self__", None)
                if widget is not None and not widget.winfo_exists():
                    dead += 1
        self.assertEqual(dead, 0)

    def test_4_darstellungswechsel_waechst_nicht(self):
        tk_ = self.root.tk

        def snapshot():
            self.wait_preload()
            self.pump(0.2)
            gc.collect()
            return {"objekte": len(gc.get_objects()),
                    "schriften": len(tk_.splitlist(tk_.call("font", "names"))),
                    "befehle": len(tk_.splitlist(tk_.call("info", "commands"))),
                    "bilder": len(tk_.splitlist(tk_.call("image", "names")))}

        self.show("settings")
        for mode in ("hell", "dunkel"):     # einmal beide Darstellungen aufbauen
            self.app.change_color(mode=mode)
        first = snapshot()
        for mode in ("hell", "dunkel", "hell", "dunkel"):
            self.app.change_color(mode=mode)
        last = snapshot()
        # Vor 0.58.1: je Wechsel rund 5 % mehr Objekte, +225 Schriften
        self.assertLess(last["objekte"], first["objekte"] * 1.02, (first, last))
        self.assertLessEqual(last["schriften"], first["schriften"] + 5, (first, last))
        self.assertLessEqual(last["befehle"], first["befehle"] + 50, (first, last))
        # Vor 0.58.1: je Wechsel 3 Flaechenbilder der Liniendiagramme mehr
        self.assertLessEqual(last["bilder"], first["bilder"] + 2, (first, last))

    def test_5_seitenwechsel_bleiben_gleich(self):
        keys = ("dashboard", "quiz", "flashcards", "progress", "settings", "help")

        def round_trip():
            for key in keys:
                self.show(key)

        round_trip()
        self.pump(0.3)
        widgets, jobs = self.app_gui.count_widgets(self.root), self.after_jobs()
        for _ in range(4):           # 4 x 5 Wechsel = 20 Seitenwechsel
            round_trip()
        self.pump(0.3)
        self.assertEqual(self.app_gui.count_widgets(self.root), widgets)
        self.assertLessEqual(self.after_jobs(), jobs + 2)

    def test_6_mausrad_legt_keine_befehle_an(self):
        areas = []

        def collect(widget):
            if isinstance(widget, self.fw.ScrollArea):
                areas.append(widget)
            for child in widget.winfo_children():
                collect(child)

        collect(self.root)
        self.assertGreater(len(areas), 3)
        for area in areas[:3]:
            area._bind_wheel(True)
            area._bind_wheel(False)
        before = len(self.root.tk.splitlist(self.root.tk.call("info", "commands")))
        for _ in range(20):
            for area in areas:
                area._bind_wheel(True)
                self.assertIs(self.root._fisi_wheel_area, area)
                area._bind_wheel(False)
        after = len(self.root.tk.splitlist(self.root.tk.call("info", "commands")))
        self.assertEqual(after, before)
        self.assertIsNone(self.root._fisi_wheel_area)

    def test_7_verdeckte_ansichten_behalten_groesse(self):
        self.show("dashboard")
        self.pump(0.2)
        area = self.app.view_area
        old = (area.winfo_width(), area.winfo_height())
        self.root.geometry("1500x960")
        self.pump(0.4)
        new = (area.winfo_width(), area.winfo_height())
        self.assertNotEqual(old, new)
        dashboard = self.app.views.built("dashboard")
        self.assertEqual((dashboard.winfo_width(), dashboard.winfo_height()), new)
        hidden = [self.app.views.built(k) for k in self.app.views.keys()
                  if k != "dashboard" and self.app.views.built(k) is not None]
        self.assertTrue(hidden)
        for view in hidden:
            self.assertEqual(view.place_info().get("relwidth"), "0")
            self.assertEqual(int(view.place_info()["width"]), old[0])
        # Beim Anzeigen passt sich die Ansicht an
        self.show("settings")
        self.pump(0.2)
        settings = self.app.views.built("settings")
        self.assertEqual((settings.winfo_width(), settings.winfo_height()), new)
        self.assertEqual(self.app.current, "settings")
        self.root.geometry("1360x880")
        self.pump(0.3)


class HandyTest(unittest.TestCase):
    """Handy: Messung (MobilePerf) und Schalter in den Optionen."""

    @classmethod
    def setUpClass(cls):
        sys.path.insert(1, os.path.join(HERE, "mobile", "src"))
        import main
        cls.main = main

    def setUp(self):
        _reset()

    def fake_app(self):
        tasks = []

        class Page:
            views = []
            on_resize = None

            def run_task(self, func, *args):
                tasks.append((func, args))

            def update(self):
                pass

        app = type("App", (), {})()
        app.page = Page()
        return app, tasks

    def test_aus_ohne_spuren(self):
        app, tasks = self.fake_app()
        perf = self.main.MobilePerf(app)
        self.assertFalse(perf.active)
        self.assertIsNone(app.page.on_resize)
        self.assertEqual(tasks, [])
        perf.page("dashboard", "learn", time.perf_counter())
        perf.theme("dunkel", "hell", time.perf_counter())
        perf.rec.flush()
        self.assertFalse(os.path.exists(fle.file_path()))

    def test_an_schreibt_zeilen(self):
        app, tasks = self.fake_app()
        perf = self.main.MobilePerf(app)
        perf.set_active(True)
        self.assertEqual(app.page.on_resize, perf._resized)
        self.assertEqual(len(tasks), 1)                 # Schreib-Schleife
        perf.page("dashboard", "learn", time.perf_counter())
        perf.theme("dunkel", "hell", time.perf_counter())
        for width in (400, 600, 800):
            perf._resized(type("E", (), {"width": width, "height": 900})())
        perf._finish_resize()
        perf.set_active(False)
        self.assertIsNone(app.page.on_resize)
        rows = [dict(zip(fle.COLUMNS, row.split(";")))
                for row in _rows(fle.file_path())[1:]]
        self.assertEqual([row["ereignis"] for row in rows],
                         [fle.EVENT_START, fle.EVENT_PAGE, fle.EVENT_THEME,
                          fle.EVENT_RESIZE, fle.EVENT_STOP])
        self.assertEqual(rows[0]["geraet"], "Handy")
        self.assertEqual(rows[0]["customtkinter"], "")          # am Handy leer
        self.assertEqual((rows[3]["von"], rows[3]["nach"], rows[3]["anzahl"]),
                         ("400x900", "800x900", "3"))

    def test_schalter_mit_talkback(self):
        import flet as ft
        main = self.main

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

        app = FakeApp()
        screen = main.SCREEN_CLASSES["settings"](app)
        screen.on_show()
        found = []

        def walk(control):
            if isinstance(control, ft.Semantics) and control.label == fle.SWITCH:
                found.append(control)
            for name in ("content", "controls"):
                value = getattr(control, name, None)
                if isinstance(value, ft.Control):
                    walk(value)
                elif isinstance(value, list):
                    for item in value:
                        if isinstance(item, ft.Control):
                            walk(item)
        walk(screen.root)
        self.assertEqual(len(found), 1)
        switch = found[0].content
        self.assertFalse(switch.value)
        self.assertEqual(screen.lbl_perf.value, fle.STATE_NONE)
        switch.value = True
        screen._toggle_perf(type("E", (), {"control": switch})())
        self.assertTrue(fle.enabled())
        app.perf.page("dashboard", "settings", time.perf_counter())
        app.perf.rec.flush()
        screen._show_perf_state()
        self.assertIn("Einträge", screen.lbl_perf.value)
        screen.delete_perf_file()
        self.assertFalse(os.path.exists(fle.file_path()))
        switch.value = False
        screen._toggle_perf(type("E", (), {"control": switch})())
        self.assertFalse(fle.enabled())


def tearDownModule():
    shutil.rmtree(_TMP, ignore_errors=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
