#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests fuer den Abgleich-Nachlauf (ab 0.62.5, Gruppe 5.4: B-B-02, B-G-18,
B-G-20, B-G-21, B-G-27, B-G-28).

Abgeglichen wird gegen die Attrappe der GitHub-API aus 0.62.4
(pruefung/abgleich_attrappe.py) auf 127.0.0.1: keine echten Zugangsdaten,
keine Verbindung nach aussen. Wegwerf-HOME und -Datenbanken in einem
Temp-Ordner (FISI_DB_PATH), nie echte Daten.

  B-G-27  abgeschnittene/fremde Antwort -> deutscher Satz statt
          "Unerwarteter Fehler: IncompleteRead ..." (PC und Handy: derselbe
          Text aus fisi_sync)
  B-G-28  PUT 422 auch nach drei Versuchen -> eigene Meldung statt
          "gleichzeitig abgeglichen" (Schutz: einmal 422 = neuer Versuch, wie
          test_abgleich.py test_00 verlangt)
  B-G-18  Eintraege eines geloeschten Spielstands zaehlen nicht als
          "uebernommen"
  B-B-02  Schliessen waehrend eines laufenden Abgleichs: kein zweiter daneben
          (PC, app_gui.SyncController)
  B-G-20  Projekt loeschen am PC plant einen Abgleich
  B-G-21  Handy: wirft die Anzeige nach dem Abgleich, wird der Knopf frei und
          der Fehler steht in fehler.log (mobile/src/main.py, ohne Oberflaeche)

Gegenprobe gegen einen anderen Stand (v0.62.3: alle Tests ausser den mit
"Schutz" gekennzeichneten rot):
    ABGLEICH_CODE=<ordner mit dem Code> xvfb-run -a python test_abgleich_meldungen.py
Start:  xvfb-run -a python test_abgleich_meldungen.py
"""

import gzip
import json
import os
import shutil
import sys
import tempfile
import threading
import time
import types
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
CODE = os.path.abspath(os.environ.get("ABGLEICH_CODE") or HERE)
WORK = tempfile.mkdtemp(prefix="fisi_meldungen_")
HOME = os.path.join(WORK, "home")
os.makedirs(HOME)
os.environ["HOME"] = HOME
os.environ["FISI_DB_PATH"] = os.path.join(HOME, "lern.db")

sys.path.insert(0, os.path.join(HERE, "pruefung"))
import abgleich_attrappe as att  # noqa: E402

sys.path.insert(0, CODE)
import fisi_core  # noqa: E402
import fisi_sync  # noqa: E402

SERVER, PORT = att.start_server()
fisi_sync.API = "http://127.0.0.1:%d" % PORT
REPO = "pruef/lernstand-attrappe"
fisi_sync.save_sync_settings(sync_repo=REPO, sync_token="PLATZHALTER-KEIN-ECHTES-TOKEN",
                             sync_auto=True)

MSG_INCOMPLETE = "Die Antwort von GitHub war unvollständig. Bitte später noch einmal."
MSG_422 = ("GitHub hat das Hochladen des Lernstands abgelehnt (HTTP 422). "
           "Der Lernstand auf diesem Gerät bleibt erhalten.")
_COUNTER = [0]


def beleg(text):
    print("  [Beleg] %s" % text, flush=True)


def new_db(name=None):
    _COUNTER[0] += 1
    path = os.path.join(WORK, "%s_%d.db" % (name or "geraet", _COUNTER[0]))
    return fisi_core.DBManager(db_path=path, error_handler=lambda message: None)


def attrappe(**ctl):
    with att.STATE.lock:
        att.STATE.reset()
        att.STATE.ctl.update(ctl)


def store_remote(db):
    """Legt den Lernstand von db als Datei in die Attrappe."""
    payload = gzip.compress(json.dumps(fisi_sync.export_local(db), ensure_ascii=False,
                                       separators=(",", ":")).encode("utf-8"), mtime=0)
    with att.STATE.lock:
        att.STATE.store(payload)


def puts():
    with att.STATE.lock:
        return [entry for entry in att.STATE.log if entry[0] == "PUT"]


def wait_for(condition, seconds):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        if condition():
            return True
        time.sleep(0.05)
    return condition()


def tearDownModule():
    SERVER.shutdown()
    shutil.rmtree(WORK, ignore_errors=True)


# ============================================================================
#  fisi_sync: Meldungen (B-G-27, B-G-28) und Zaehlung (B-G-18)
# ============================================================================

class Meldungen(unittest.TestCase):

    def sync_error(self, db):
        with self.assertRaises(fisi_sync.SyncError) as caught:
            fisi_sync.sync(db, device="Test")
        beleg("Meldung: %s" % caught.exception)
        return str(caught.exception)

    def test_b_g_27_abgeschnittene_antwort(self):
        """Verbindung bricht mitten in der Antwort ab (IncompleteRead)."""
        attrappe(get_body="abgeschnitten")
        self.assertEqual(self.sync_error(new_db()), MSG_INCOMPLETE)

    def test_b_g_27_fremde_seite(self):
        """Statt JSON kommt eine fremde Seite (Proxy, Virenscanner)."""
        for kind in ("html", "kein_json", "liste"):
            with self.subTest(kind=kind):
                attrappe(get_body=kind)
                self.assertEqual(self.sync_error(new_db()), MSG_INCOMPLETE)

    def test_b_g_28_422_eigene_meldung(self):
        """PUT 422 bei vorhandener Datei, dauerhaft: eigene Meldung. Die drei
        Versuche bleiben (test_abgleich.py test_00: einmal 422 = neuer
        Versuch)."""
        attrappe()
        db = new_db()
        db.log_quiz_answer(fisi_core.CATEGORIES[2], "erste Frage", True)
        fisi_sync.sync(db, device="Test")           # legt die Datei an
        db.log_quiz_answer(fisi_core.CATEGORIES[2], "zweite Frage", True)
        with att.STATE.lock:
            att.STATE.log.clear()
            att.STATE.ctl.update(put_status=422)
        self.assertEqual(self.sync_error(db), MSG_422)
        beleg("PUT-Versuche: %d" % len(puts()))
        self.assertEqual(len(puts()), 3)

    def test_b_g_28_schutz_422_einmal_neuer_versuch(self):
        """Schutz (auch auf v0.62.3 gruen): einmal 422 (z.B. Datei fehlte beim
        Lesen, ein anderes Geraet hat sie inzwischen angelegt) - erneut
        versuchen, kein Fehler."""
        attrappe(put_status=422, put_status_n=1)
        db = new_db()
        db.log_quiz_answer(fisi_core.CATEGORIES[2], "Frage", True)
        result = fisi_sync.sync(db, device="Test")
        beleg("Ergebnis: %s | PUTs: %s" % (result.message, puts()))
        self.assertEqual(result.sent, 1)
        self.assertEqual([entry[2] for entry in puts()], [422, 200])

    def test_b_g_18_geloeschter_spielstand_zaehlt_nicht(self):
        """20 Ereignisse eines hier geloeschten Durchgangs kommen aus der Datei:
        netto 0 uebernommen (rot: 20)."""
        attrappe()
        other = new_db("anderes")
        for index in range(20):
            other.log_game_event("tick", json.dumps({"i": index}), run="lauf-weg")
        store_remote(other)
        db = new_db()
        db.delete_run(2, "lauf-weg")
        result = fisi_sync.sync(db, device="Test")
        beleg("received=%d, Meldung: %s" % (result.received, result.message))
        self.assertEqual(result.received, 0)
        self.assertNotIn("übernommen", result.message)

    def test_b_g_18_schutz_normale_eintraege_zaehlen(self):
        """Schutz: Ereignisse eines nicht geloeschten Durchgangs zaehlen weiter."""
        attrappe()
        other = new_db("anderes")
        for index in range(5):
            other.log_game_event("tick", json.dumps({"i": index}), run="lauf-da")
        store_remote(other)
        db = new_db()
        db.delete_run(2, "lauf-weg")
        result = fisi_sync.sync(db, device="Test")
        self.assertEqual(result.received, 5)
        self.assertIn("5 Einträge von anderen Geräten übernommen", result.message)


# ============================================================================
#  PC: app_gui.SyncController (B-B-02) und Projekt loeschen (B-G-20)
# ============================================================================

def _app_gui():
    import app_gui
    return app_gui


class _Counting:
    """Zaehlt Aufrufe von fisi_sync.sync und wie viele gleichzeitig laufen."""

    def __init__(self):
        self.real = fisi_sync.sync
        self.lock = threading.Lock()
        self.calls = self.now = self.most = 0

    def __call__(self, *args, **kwargs):
        with self.lock:
            self.calls += 1
            self.now += 1
            self.most = max(self.most, self.now)
        try:
            return self.real(*args, **kwargs)
        finally:
            with self.lock:
                self.now -= 1

    def __enter__(self):
        fisi_sync.sync = self
        return self

    def __exit__(self, *exc):
        wait_for(lambda: self.now == 0, 20)
        fisi_sync.sync = self.real


class _FakeRoot:
    def after(self, *_args):
        return None


class PcAbgleich(unittest.TestCase):

    def controller(self):
        app_gui = _app_gui()
        app = types.SimpleNamespace(root=_FakeRoot(), db=new_db("pc"))
        app.updater = app_gui.UpdateController(app)
        return app_gui.SyncController(app)

    def test_b_b_02_kein_zweiter_abgleich_beim_schliessen(self):
        """Start-Abgleich haengt (Antwort 4 s verzoegert), Schliessen mit 2 s
        Frist: genau 1 Abgleich (rot: 2 nebeneinander)."""
        attrappe(get_delay=4)
        sync = self.controller()
        with _Counting() as counter:
            sync.run()
            self.assertTrue(wait_for(lambda: counter.calls == 1, 5))
            sync.dirty = True
            start = time.monotonic()
            sync.run_before_exit(timeout=2)
            took = time.monotonic() - start
            calls = counter.calls
        beleg("Abgleiche beim Schliessen: %d, gleichzeitig hoechstens %d, %.1f s"
              % (calls, counter.most, took))
        self.assertEqual(calls, 1)
        self.assertEqual(counter.most, 1)
        self.assertLess(took, 3.0)

    def test_b_b_02_danach_nacheinander(self):
        """Start-Abgleich wird in der Frist fertig: der letzte Abgleich laeuft
        danach, nie zwei gleichzeitig (rot: 2 gleichzeitig)."""
        attrappe(get_delay=1)
        sync = self.controller()
        with _Counting() as counter:
            sync.run()
            self.assertTrue(wait_for(lambda: counter.calls == 1, 5))
            sync.dirty = True
            sync.run_before_exit(timeout=8)
            calls = counter.calls
        beleg("Abgleiche: %d, gleichzeitig hoechstens %d" % (calls, counter.most))
        self.assertEqual(calls, 2)
        self.assertEqual(counter.most, 1)

    def test_b_b_02_schutz_ohne_laufenden_abgleich(self):
        """Schutz: Laeuft keiner, gleicht das Schliessen wie bisher einmal ab."""
        attrappe()
        sync = self.controller()
        with _Counting() as counter:
            sync.dirty = True
            sync.run_before_exit(timeout=8)
            calls = counter.calls
        self.assertEqual(calls, 1)

    def test_b_g_20_projekt_loeschen_plant_abgleich(self):
        app_gui = _app_gui()
        import fisi_projekt as fpj
        db = new_db("projekt")
        planned = []
        app = types.SimpleNamespace(
            notify_progress=lambda refresh_view=True: None,
            sync=types.SimpleNamespace(schedule=lambda: planned.append(True)))
        project = fpj.create_project(db, "Testprojekt")
        view = types.SimpleNamespace(app=app, db=db, project=project, pending={},
                                     fields={fpj.TITLE_FIELD: "Testprojekt"},
                                     _load_project=lambda *args: None)
        asked = app_gui.messagebox.askyesno
        app_gui.messagebox.askyesno = lambda *args, **kwargs: True
        try:
            app_gui.FinalProjectView._delete_project(view)
        finally:
            app_gui.messagebox.askyesno = asked
        beleg("geplante Abgleiche nach dem Loeschen: %d" % len(planned))
        self.assertIsNone(view.project)
        self.assertEqual(len(planned), 1)


# ============================================================================
#  Handy: mobile SyncController._work (B-G-21), ohne Oberflaeche
# ============================================================================

def _mobile():
    sys.path.insert(0, os.path.join(CODE, "mobile", "src"))
    import main
    return main


class _Button:
    def __init__(self):
        self.enabled = True

    def set_enabled(self, flag):
        self.enabled = flag


class _Label:
    value = ""
    color = None


class HandyAbgleich(unittest.TestCase):

    def app(self, fail_refresh=False, fail_update=0):
        main = _mobile()

        class Settings:
            sync_now = main.SettingsScreen.sync_now
            show_sync_status = main.SettingsScreen.show_sync_status

            def __init__(self, app):
                self.app = app
                self.lbl_sync, self.btn_sync = _Label(), _Button()
                self.entry_repo = types.SimpleNamespace(value=REPO)
                self.entry_token = types.SimpleNamespace(value="PLATZHALTER-KEIN-ECHTES-TOKEN")

        class Page:
            def __init__(self):
                self.fail = fail_update

            def run_thread(self, handler):
                try:                    # Flet verschluckt Fehler im Faden ebenso
                    handler()
                except Exception:
                    pass

            def update(self):
                if self.fail:
                    self.fail -= 1
                    raise RuntimeError("Control must be added to the page first")

        class App:
            def __init__(self):
                self.page, self.db = Page(), new_db("handy")
                self.sync = main.SyncController(self)
                self.screens = {"settings": Settings(self)}
                self.refreshed = 0

            def refresh_after_sync(self):
                self.refreshed += 1
                if fail_refresh:
                    raise RuntimeError("Anzeige wirft nach dem Abgleich (Testfall B-G-21)")

        other = new_db("anderes")
        for index in range(3):
            other.log_quiz_answer(fisi_core.CATEGORIES[2], "vom anderen Geraet %d" % index,
                                  True)
        attrappe()
        store_remote(other)
        return App()

    def log_text(self):
        path = fisi_core.error_log_path()
        if not os.path.exists(path):
            return ""
        with open(path, encoding="utf-8") as handle:
            return handle.read()

    def test_b_g_21_anzeige_wirft_knopf_frei(self):
        app = self.app(fail_refresh=True)
        settings = app.screens["settings"]
        settings.sync_now()
        beleg("Knopf frei: %s | Anzeige: %r | busy: %s" % (
            settings.btn_sync.enabled, settings.lbl_sync.value, app.sync.busy))
        self.assertEqual(app.refreshed, 1)
        self.assertTrue(settings.btn_sync.enabled)
        self.assertFalse(app.sync.busy)
        self.assertIn("3 Einträge von anderen Geräten übernommen", settings.lbl_sync.value)
        self.assertIn("Testfall B-G-21", self.log_text())

    def test_b_g_21_update_wirft_zweiter_wunsch_laeuft(self):
        """page.update wirft: Fehler in fehler.log, ein waehrenddessen
        gewuenschter zweiter Abgleich (again) laeuft trotzdem."""
        app = self.app(fail_update=1)
        settings = app.screens["settings"]
        app.sync.again = True
        before = self.log_text().count("RuntimeError: Control must be added")
        settings.sync_now()
        with att.STATE.lock:
            gets = [e for e in att.STATE.log if e[0] == "GET" and "contents" in e[1]]
        beleg("Abrufe der Datei: %d | again: %s" % (len(gets), app.sync.again))
        self.assertFalse(app.sync.again)
        self.assertEqual(len(gets), 2)
        self.assertTrue(settings.btn_sync.enabled)
        self.assertEqual(self.log_text().count("RuntimeError: Control must be added"),
                         before + 1)

    def test_b_g_21_schutz_ohne_fehler(self):
        """Schutz: ohne Fehler wie bisher (Anzeige, Knopf frei)."""
        app = self.app()
        settings = app.screens["settings"]
        settings.sync_now()
        self.assertTrue(settings.btn_sync.enabled)
        self.assertIn("übernommen", settings.lbl_sync.value)


if __name__ == "__main__":
    print("Code-Stand: %s" % CODE, flush=True)
    unittest.main(verbosity=2)
