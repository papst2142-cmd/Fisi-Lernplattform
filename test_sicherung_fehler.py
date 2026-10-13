#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests fuer 0.62.5 Gruppe 5.2 "Sicherung" (Feinplan 0.62.5, Abschnitt 5.2):

  B-G-02  "Sicherung erstellen" (PC) bei voller Platte: alte Sicherung bleibt
  B-G-04  Einstellung nicht speicherbar: Schalter zurueck, Meldung (PC, Handy)
  B-G-05  Einspielen bei gesperrter DB: Meldung, Daten gleich (PC, Handy);
          das Fenster der Vorschau schliesst erst nach der Aktion (PC)
  B-G-07  Zusammenfuehren nach "Alle Lerndaten loeschen": ehrlicher Text
  B-G-08  Warntext "Alles ersetzen" nennt abgeglichene eigene Loeschungen
  B-G-10  Vorschau zaehlt geloeschte Abschlussprojekte nicht
  B-G-11  "Alles ersetzen" bei voller Platte: keine leere Sicherheitskopie
  B-G-14  Sicherung mit falschen Datentypen: "Die Sicherung ist beschädigt"
  B-G-15  Absturz beim Speichern des Tagesziels: Lernstand und Tagesziel passen
  B-G-19  Rueckfrage nennt "Platz 1", Meldung zaehlt die Platz-Zeile nicht

Alle Daten liegen in Temp-Ordnern (FISI_DB_PATH, HOME), nie Nutzerdaten.
Die volle Platte und der Absturz sind Attrappen (open/os.open/os.replace
werfen), damit der Test ohne mount auch in der CI laeuft. Mit echtem
tmpfs: Beleg der Gruppe 5.2.

Gegen einen anderen Code-Stand (Rot-Probe, z.B. v0.62.3):
    SICHERUNG_CODE=<ordner mit dem Code> python test_sicherung_fehler.py
Braucht eine Anzeige (z.B. xvfb-run) und Flet fuer die Handy-Tests.

Start:  python test_sicherung_fehler.py
"""

import builtins
import contextlib
import errno
import gzip
import json
import os
import shutil
import sqlite3
import sys
import tempfile
import time
import types
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
CODE = os.path.abspath(os.environ.get("SICHERUNG_CODE") or HERE)
sys.path.insert(0, CODE)
sys.path.insert(1, os.path.join(CODE, "mobile", "src"))
os.chdir(CODE)

_TMP = tempfile.mkdtemp(prefix="fisi_sicherung_fehler_")
os.environ["FISI_DB_PATH"] = os.path.join(_TMP, "start.db")
os.environ.setdefault("FISI_SELFTEST", os.path.join(_TMP, "selbsttest.log"))
os.environ["HOME"] = _TMP
os.environ["APPDATA"] = _TMP
os.environ["FISI_VORLADEN"] = "0"

import fisi_sicherung as fs  # noqa: E402
import fisi_update  # noqa: E402
from fisi_core import SYNC_TABLES, DBManager  # noqa: E402

TOKEN = "PLATZHALTER_KEIN_ECHTER_SCHLUESSEL"


class Crash(BaseException):
    """Attrappe fuer einen Absturz (wie SIGKILL: kein except greift)."""


def _rows(db):
    conn = sqlite3.connect(db.db_path)
    try:
        return {table: conn.execute("SELECT uid, %s FROM %s ORDER BY uid"
                                    % (", ".join(columns), table)).fetchall()
                for table, columns in SYNC_TABLES.items()}
    finally:
        conn.close()


class _FullHandle:
    """Datei auf voller Platte: oeffnen geht, schreiben nicht."""

    def __init__(self, handle):
        self._handle = handle

    def write(self, _data):
        raise OSError(errno.ENOSPC, "No space left on device")

    def __getattr__(self, name):
        return getattr(self._handle, name)

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        self._handle.close()
        return False


@contextlib.contextmanager
def full_disk(folder):
    """Attrappe: im Ordner folder ist die Platte voll (open zum Schreiben
    legt die Datei an bzw. kuerzt sie wie echt, write scheitert)."""
    real = builtins.open
    folder = os.path.abspath(folder)

    def fake(file, mode="r", *args, **kwargs):
        handle = real(file, mode, *args, **kwargs)
        if isinstance(file, str) and os.path.dirname(os.path.abspath(file)) == folder \
                and any(flag in mode for flag in "wax"):
            return _FullHandle(handle)
        return handle

    builtins.open = fake
    try:
        yield
    finally:
        builtins.open = real


@contextlib.contextmanager
def settings_unsaveable():
    """Attrappe: einstellungen.json laesst sich nicht ersetzen (os.replace
    scheitert, wie bei gesperrter oder schreibgeschuetzter Datei)."""
    real = os.replace

    def fake(src, dst, *args, **kwargs):
        if str(dst).endswith("einstellungen.json"):
            raise OSError(errno.EACCES, "Permission denied")
        return real(src, dst, *args, **kwargs)

    with mock.patch.object(os, "replace", fake):
        yield


@contextlib.contextmanager
def locked(db_path):
    """Echte Sperre: ein anderes Programm haelt die Datenbank exklusiv."""
    conn = sqlite3.connect(db_path, timeout=0.1)
    conn.execute("BEGIN EXCLUSIVE")
    try:
        yield
    finally:
        conn.rollback()
        conn.close()


class Base(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.mkdtemp(dir=_TMP)
        self.old_path = os.environ["FISI_DB_PATH"]
        os.environ["FISI_DB_PATH"] = os.path.join(self.folder, "fisi.db")
        self.errors = []
        self.addCleanup(self._restore)

    def _restore(self):
        os.environ["FISI_DB_PATH"] = self.old_path
        shutil.rmtree(self.folder, ignore_errors=True)

    def db(self, name="fisi.db"):
        return DBManager(db_path=os.path.join(self.folder, name),
                         error_handler=self.errors.append)

    def learned(self, db, count=5, tag="A"):
        for number in range(count):
            db.log_card("Netzwerk", "Frage %s%d" % (tag, number), "lernen", True)
        return db

    def backup_of(self, db):
        return fs.read_backup(fs.create_backup(db, "0.62.5", "Test"))


# ============================================================================
#  Kern (fisi_sicherung)
# ============================================================================

class KernTest(Base):
    def test_b_g_10_geloeschtes_projekt_zaehlt_nicht(self):
        db = self.db()
        db.save_project_field("p1", "titel", "Sichtbar")
        db.save_project_field("p2", "titel", "Geloescht")
        db.save_project_field("p2", "_geloescht", "1")
        lines = fs.backup_summary(self.backup_of(db))["zeilen"]
        self.assertIn("Abschlussprojekte: 1", lines)

    def test_b_g_07_zusammenfuehren_nach_loeschen_ehrlich(self):
        db = self.learned(self.db())
        backup = self.backup_of(db)
        time.sleep(1.1)          # Loeschmarke sekundengenau nach den Eintraegen
        db.reset_all()
        count = fs.merge_backup(db, backup)
        message = fs.merge_message(count)
        self.assertEqual(count, 0)
        self.assertNotIn("Es fehlte nichts", message)
        self.assertIn("5 Einträge der Sicherung bleiben gelöscht", message)
        self.assertIn("„Alles ersetzen“", message)
        self.assertNotIn("nichts geht verloren", fs.PREVIEW_HINT)
        # Ab 0.63.2 (FG-92, Antwort Meldung 31 B.4): voller Wortlaut statt
        # Teilstueck; Verhaltenstests f9 und "Sicherung von vor dem Ersetzen"
        # in test_abgleich_0632.py BG08Ersetzen (test_fg92_*)
        self.assertEqual(fs.PREVIEW_HINT, (
            "Zusammenführen übernimmt, was auf diesem Gerät noch fehlt – doppelt wird nichts. "
            "Gelöschtes kommt dabei in der Regel nicht zurück: Was auf diesem Gerät gelöscht "
            "wurde (z. B. mit „Alle Lerndaten löschen“), bleibt gelöscht – außer die Sicherung "
            "wurde auf einem Gerät erstellt, nachdem es nach dieser Löschung mit „Alles "
            "ersetzen“ einen älteren Stand eingespielt hatte; dann kommt dieser Stand zurück. "
            "Alles ersetzen stellt genau den Stand der Sicherung her."))
        self.assertNotIn("Gelöschtes kommt dabei nicht zurück", fs.PREVIEW_HINT)
        self.assertIn("Gelöschtes kommt dabei in der Regel nicht zurück", fs.preview_text(backup))
        self.assertTrue(fs.preview_text(backup).endswith("\n\n" + fs.PREVIEW_HINT))

    def test_b_g_07_ohne_loeschung_bleibt_es_beim_alten_text(self):
        """Schutz-Test (auch auf v0.62.3 gruen): nichts geloescht, nichts neu."""
        db = self.learned(self.db())
        backup = self.backup_of(db)
        count = fs.merge_backup(db, backup)
        self.assertEqual(fs.merge_message(count),
                         "Sicherung eingespielt: Es fehlte nichts, alles war schon da.")

    def test_b_g_08_warntext_nennt_eigene_loeschungen(self):
        # Ab 0.63.2 (FG-81, nur zusammen mit B-G-08): volle neue Saetze statt
        # Teilstuecke. Endfassung (Weisung zu Meldung 37, Abschnitt 3: Satz 6
        # neu gefasst, Satz 7 zu Spielstaenden/Projekten neu; die anderen
        # Saetze wie Antwort Meldung 35 B.2): jeder Satz ist in
        # test_abgleich_0632.py BG08Ersetzen per Verhaltenstest belegt (Liste:
        # bau_0.63.2/s6b/texte_m37/ergebnis.md)
        backup = self.backup_of(self.learned(self.db()))
        text = fs.replace_question(backup)
        erster, zweiter = text.split("\n\n")
        self.assertTrue(erster.startswith("Der komplette Lernstand dieses Geräts"))
        self.assertEqual(erster, (
            "Der komplette Lernstand dieses Geräts – Lernfortschritt, Prüfungen, "
            "Abschlussprojekt, Spielstände und Bestenliste – wird durch die Sicherung "
            "vom %s ersetzt. Das Tagesziel kommt ebenfalls aus der Sicherung. Vorher wird "
            "der jetzige Stand als Sicherheitskopie neben der Datenbank gespeichert."
            % fs.backup_summary(backup)["erstellt"]))
        self.assertEqual(zweiter, (
            "Ist der Abgleich eingerichtet, kommen beim nächsten Abgleich die Daten aus "
            "dem Repository wieder dazu. "
            "Löschungen, die dieses Gerät schon kennt (zum Beispiel „Alle Lerndaten "
            "löschen“), löschen das Eingespielte nicht noch einmal; das gilt auch für "
            "deine anderen Geräte, wenn alle deine Geräte schon beim Ersetzen mindestens "
            "Version 0.63.2 hatten. "
            "Solange ein Gerät noch eine ältere Version hat, kann das Eingespielte auf "
            "deinen anderen Geräten zeitweise wieder fehlen, und ein Gerät mit einer "
            "älteren Version, das die Löschung kennt, löscht es bei sich weiterhin; "
            "aktualisiere deine anderen Geräte deshalb bald. "
            "Was ein anderes Gerät ohne Verbindung gelernt hat, bleibt in der Regel "
            "erhalten, wenn es sich erst nach dem Ersetzen wieder abgleicht und alle deine "
            "Geräte schon beim Ersetzen mindestens Version 0.63.2 hatten. "
            "Was nach dem Erstellen der Sicherung schon abgeglichen war, bleibt gelöscht. "
            "Löschungen eines anderen Geräts, die dieses Gerät noch nicht kennt, gelten "
            "weiter – außer sie kamen vor der letzten Löschung derselben Art, die dieses "
            "Gerät kennt (beide „Alle Lerndaten löschen“, beide „Historie löschen“ oder "
            "beide „Bestenliste löschen“); solche werden aufgehoben. "
            "Bei Spielständen und Projekten ist das anders: Ein zurückgesetzter oder "
            "gelöschter Spielstand und ein gelöschtes Projekt bleiben gelöscht, wenn die "
            "Löschung von einem anderen Gerät kam oder schon abgeglichen war. "
            "Bewahre die Sicherungsdatei deshalb auf."))
        self.assertNotIn("ist nach dem nächsten Abgleich wieder weg", text)
        # die beiden Saetze der ersten Fassung, die gp_s6b_nacharbeit (M1, M2) widerlegt hat
        self.assertNotIn("Auch was ein anderes Gerät ohne Verbindung gelernt hat", text)
        self.assertNotIn("Löschungen, die dieses Gerät noch nicht kennt, gelten weiter.", text)
        # Fassung von 31b539c (Meldung 31 B.3), Saetze 2, 3, 4 und 6, von
        # gp_s6b_texte (M1, M2, M3) widerlegt (Ablaeufe f4b, f4f, f2e, f2f)
        self.assertNotIn("sobald sie mindestens Version 0.63.2 haben und sich einmal "
                         "abgeglichen haben", text)
        self.assertNotIn("alle Geräte, die die Löschung kennen, mindestens Version 0.63.2",
                         text)
        self.assertNotIn("löscht das Eingespielte bei sich weiterhin", text)
        self.assertNotIn("eine unbekannte frühere Löschung eines anderen Geräts", text)
        # Vorschlag der Pruefung (gp_s6b_texte), Saetze 2 und 4: zeitlich zu weit
        # (Antwort Meldung 35 B.1, Ablauf f4f/f4h) - nur "schon beim Ersetzen"
        self.assertNotIn("sobald alle deine Geräte mindestens Version 0.63.2 haben", text)
        self.assertNotIn("alle deine Geräte mindestens Version 0.63.2 haben", text)
        self.assertEqual(text.count("schon beim Ersetzen mindestens Version 0.63.2 hatten"), 2)
        # Fassung von dd0c2a0 (Antwort Meldung 35 B.2), Satz 6: von f2g "nach"
        # (Bauer) und gp_meldung_37 (S1, S2, S1b, S2b: Spielstaende/Projekte)
        # widerlegt; ersetzt durch Weisung zu Meldung 37, Abschnitt 3
        self.assertNotIn("Löschungen, die erst nach der letzten Löschung auf diesem Gerät",
                         text)
        self.assertNotIn("kamen und die es noch nicht kennt, gelten weiter", text)
        self.assertNotIn("eine unbekannte frühere Löschung derselben Art", text)
        self.assertNotIn("(zum Beispiel ebenfalls „Alle Lerndaten löschen“)", text)
        self.assertNotIn("wird dagegen aufgehoben", text)
        self.assertEqual(zweiter.count(". "), 7)          # 8 Saetze
        self.assertEqual(text.count("beide „"), 3)

    def test_b_g_11_volle_platte_keine_leere_sicherheitskopie(self):
        target = self.learned(self.db(), tag="alt")
        before = _rows(target)
        backup = self.backup_of(self.learned(self.db("quelle.db"), tag="neu"))
        safety = os.path.join(self.folder, "kopien")
        os.makedirs(safety)
        with full_disk(safety), self.assertRaises(fs.BackupError) as caught:
            fs.replace_all(target, backup, safety)
        self.assertIn("Die Sicherheitskopie ließ sich nicht speichern", str(caught.exception))
        self.assertEqual(os.listdir(safety), [])
        self.assertEqual(_rows(target), before)

    def test_b_g_14_falsche_datentypen(self):
        good = json.loads(gzip.decompress(fs.create_backup(
            self.learned(self.db()), "0.62.5")).decode("utf-8"))
        uid = "u" * 32
        broken = {
            "zeile_ist_text": lambda d: d["tables"].update(card_events=["kaputt"]),
            "zelle_ist_liste": lambda d: d["tables"]["card_events"][0].__setitem__(1, [1]),
            "tabelle_ist_dict": lambda d: d["tables"].update(quiz_answers={"a": 1}),
            "marken_sind_liste": lambda d: d.update(markers=["reset_at"]),
            "platz_ist_kein_wert": lambda d: d["tables"].update(spiel_plaetze=[
                [uid, "2026-01-01 10:00:00", "x", "l1", "angelegt", "{}", "PC"]]),
        }
        for name, change in broken.items():
            with self.subTest(name):
                backup = json.loads(json.dumps(good))
                change(backup["daten"])
                backup["pruefsumme"] = fs._checksum(backup["daten"], backup["einstellungen"])
                raw = gzip.compress(json.dumps(backup).encode("utf-8"))
                with self.assertRaises(fs.BackupError) as caught:
                    fs.read_backup(raw)
                self.assertIn("Die Sicherung ist beschädigt", str(caught.exception))

    def test_b_g_15_absturz_beim_tagesziel(self):
        fisi_update.save_settings({"ziel_anzahl": 33, "sync_token": TOKEN})
        backup = self.backup_of(self.learned(self.db("quelle.db"), tag="neu"))
        fisi_update.save_settings({"ziel_anzahl": 7, "sync_token": TOKEN})
        target = self.learned(self.db(), tag="alt")
        old_rows = _rows(target)
        real_open, real_os_open = builtins.open, os.open

        def crash_if_settings(path, writing):
            if writing and os.path.basename(str(path)).startswith("einstellungen.json"):
                raise Crash()

        def fake_open(file, mode="r", *args, **kwargs):
            crash_if_settings(file, any(flag in mode for flag in "wax"))
            return real_open(file, mode, *args, **kwargs)

        def fake_os_open(path, flags, *args, **kwargs):
            crash_if_settings(path, flags & (os.O_WRONLY | os.O_RDWR))
            return real_os_open(path, flags, *args, **kwargs)

        with mock.patch.object(builtins, "open", fake_open), \
                mock.patch.object(os, "open", fake_os_open):
            with self.assertRaises(Crash):
                fs.replace_all(target, backup, os.path.join(self.folder, "kopien"))
        goal = fisi_update.load_settings().get("ziel_anzahl")
        rows = _rows(target)
        # Entweder alles alt oder alles neu - nie neuer Lernstand mit altem Ziel
        if rows == old_rows:
            self.assertEqual(goal, 7)
        else:
            self.assertEqual(goal, 33, "Lernstand ersetzt, Tagesziel noch alt")
        self.assertEqual(fisi_update.load_settings().get("sync_token"), TOKEN)

    def test_b_g_15_tagesziel_kommt_mit(self):
        """Schutz-Test (auch auf v0.62.3 gruen): ohne Absturz kommt das Ziel mit,
        der Zugangsschluessel bleibt."""
        fisi_update.save_settings({"ziel_anzahl": 33})
        backup = self.backup_of(self.learned(self.db("quelle.db")))
        fisi_update.save_settings({"ziel_anzahl": 7, "sync_token": TOKEN})
        fs.replace_all(self.db(), backup, os.path.join(self.folder, "kopien"))
        self.assertEqual(fisi_update.load_settings()["ziel_anzahl"], 33)
        self.assertEqual(fisi_update.load_settings()["sync_token"], TOKEN)
        self.assertEqual([n for n in os.listdir(self.folder) if n.endswith(".tmp")], [])

    def test_b_g_19_platzname_und_zahl(self):
        import fisi_game as fg
        db = self.db()
        game = fg.Game(db, "PC")
        run = game.new_run(1)                    # nie umbenannt
        for number in range(20):
            db.log_game_event("test_%d" % number, json.dumps({"n": number}), "PC", run)
        backup = self.backup_of(db)
        game.delete_run(run)
        runs = fs.deleted_runs(db, backup)
        self.assertEqual([item["name"] for item in runs], ["Platz 1"])
        self.assertIn("(„Platz 1“)", fs.deleted_question(runs))
        count = fs.merge_backup(db, backup, [run], "PC")
        self.assertEqual(count, 20)
        self.assertTrue(fs.merge_message(count, ["Platz 1"]).startswith(
            "Sicherung eingespielt: 20 Einträge übernommen."))
        # Der wiederhergestellte Platz traegt keinen fremden Namen
        self.assertEqual(fg.Game(db).layout()["namen"], {})

    def test_konstanten_wie_im_spiel_und_projekt(self):
        import fisi_game as fg
        import fisi_projekt as fpj
        self.assertEqual(fs.SLOT_LABEL % 2, fg.slot_default_name(2))
        self.assertEqual(fs.PROJECT_DELETED_FIELD, fpj.DELETED_FIELD)


# ============================================================================
#  PC (app_gui.SettingsView, BackupDialog)
# ============================================================================

def _pc_messages():
    """showerror/showinfo/askyesno des PCs mitschreiben."""
    import app_gui
    shown = []
    patches = [mock.patch.object(app_gui.messagebox, name, (lambda n: lambda *a, **k: (
        shown.append((n,) + tuple(a) + tuple(k.values())), True)[-1])(name))
        for name in ("showerror", "showinfo", "showwarning", "askyesno")]
    return shown, patches


class PCTest(Base):
    def setUp(self):
        super().setUp()
        import app_gui
        self.app_gui = app_gui
        self.shown, patches = _pc_messages()
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)

    def view(self, db, **extra):
        fake = types.SimpleNamespace(
            db=db, app=types.SimpleNamespace(flush_inputs=lambda **k: None, root=None),
            _after_restore=lambda: None, **extra)
        for name in ("_save_failed",):
            function = getattr(self.app_gui.SettingsView, name, None)
            if function is not None:
                setattr(fake, name, types.MethodType(function, fake))
        return fake

    def test_b_g_02_volle_platte_alte_sicherung_bleibt(self):
        old_db = self.learned(self.db("alt.db"), 3)
        old_bytes = fs.create_backup(old_db, "0.62.4", "alt")
        target_dir = os.path.join(self.folder, "stick")
        os.makedirs(target_dir)
        target = os.path.join(target_dir, "Lernplattform-Sicherung" + fs.BACKUP_EXT)
        with open(target, "wb") as handle:
            handle.write(old_bytes)
        db = self.learned(self.db(), 50, "neu")
        from tkinter import filedialog
        with mock.patch.object(filedialog, "asksaveasfilename", lambda **k: target), \
                mock.patch.object(self.app_gui, "show_badge_toast", lambda *a: None), \
                full_disk(target_dir):
            self.app_gui.SettingsView.create_backup(self.view(db))
        with open(target, "rb") as handle:
            raw = handle.read()
        self.assertEqual(raw, old_bytes)
        fs.read_backup(raw)
        self.assertEqual(os.listdir(target_dir), [os.path.basename(target)])
        self.assertEqual([item[0] for item in self.shown], ["showerror"])

    def test_b_g_02_sicherung_erstellen_schreibt(self):
        """Schutz-Test (auch auf v0.62.3 gruen): normaler Fall ueberschreibt."""
        target = os.path.join(self.folder, "s" + fs.BACKUP_EXT)
        with open(target, "wb") as handle:
            handle.write(b"alt")
        db = self.learned(self.db())
        from tkinter import filedialog
        with mock.patch.object(filedialog, "asksaveasfilename", lambda **k: target), \
                mock.patch.object(self.app_gui, "show_badge_toast", lambda *a: None):
            self.app_gui.SettingsView.create_backup(self.view(db))
        with open(target, "rb") as handle:
            self.assertEqual(len(fs.read_backup(handle.read())["daten"]["tables"]
                                 ["card_events"]), 5)
        self.assertEqual(self.shown, [])

    def _switch(self, value):
        state = {"value": value}
        return types.SimpleNamespace(get=lambda: state["value"],
                                     set=lambda v: state.__setitem__("value", bool(v)))

    def test_b_g_04_schalter_springt_zurueck(self):
        import fisi_sync
        fisi_update.save_settings({"auto_check": True, "sync_auto": True})
        for method, var_name, key in (("_toggle_auto", "var_auto", "auto_check"),
                                      ("_toggle_sync_auto", "var_sync_auto", "sync_auto")):
            with self.subTest(method):
                del self.shown[:]
                switch = self._switch(False)        # Nutzer schaltet aus
                fake = self.view(None, **{var_name: switch})
                with settings_unsaveable():
                    getattr(self.app_gui.SettingsView, method)(fake)
                self.assertTrue(switch.get(), "Schalter zeigt aus, gespeichert ist an")
                self.assertTrue(fisi_update.load_settings()[key])
                self.assertEqual(len(self.shown), 1, self.shown)
                self.assertEqual(self.shown[0][0], "showerror")
                self.assertIn("Die Einstellung ließ sich nicht speichern", self.shown[0][2])
        self.assertTrue(fisi_sync.sync_settings()["sync_auto"])

    def test_b_g_04_abgleich_nicht_mit_altem_repository(self):
        fisi_update.save_settings({"sync_repo": "alt/repo", "sync_token": TOKEN})
        runs, label = [], {}
        fake = self.view(
            None, entry_repo=types.SimpleNamespace(get=lambda: "neu/repo"),
            entry_token=types.SimpleNamespace(get=lambda: TOKEN),
            lbl_sync=types.SimpleNamespace(configure=lambda **k: label.update(k)),
            btn_sync=types.SimpleNamespace(set_enabled=lambda on: None))
        fake.app.sync = types.SimpleNamespace(run=lambda: runs.append(1))
        with settings_unsaveable():
            self.app_gui.SettingsView.sync_now(fake)
        self.assertEqual(runs, [], "Abgleich mit dem alten Repository gestartet")
        self.assertIn("Die Einstellung ließ sich nicht speichern", label.get("text", ""))

    def test_b_g_05_gesperrte_datenbank_meldet(self):
        source = self.learned(self.db("quelle.db"), 4, "neu")
        backup = self.backup_of(source)
        db = self.learned(self.db(), 2, "alt")
        before = _rows(db)
        for method in ("_merge_backup", "_replace_backup"):
            with self.subTest(method):
                del self.shown[:]
                with locked(db.db_path):
                    try:
                        getattr(self.app_gui.SettingsView, method)(self.view(db), backup)
                    except Exception as error:  # noqa: BLE001 - alte Fassung wirft
                        self.shown.append(("ausnahme", repr(error)))
                errors = [item for item in self.shown if item[0] == "showerror"]
                self.assertEqual(len(errors), 1, self.shown)
                self.assertIn("Die Sicherung ließ sich nicht einspielen", errors[0][2])
                self.assertEqual(_rows(db), before)

    def test_b_g_05_fenster_schliesst_nach_der_aktion(self):
        state = _pc_app()
        backup = self.backup_of(self.learned(self.db()))
        seen = []
        dialog = self.app_gui.BackupDialog(state["app"], backup,
                                           lambda b: seen.append(dialog.winfo_exists()),
                                           lambda b: None)
        state["root"].update()
        merge = [w for w in _walk(dialog) if getattr(w, "_caption", None) == fs.BTN_MERGE]
        self.assertEqual(len(merge), 1)
        merge[0].command()
        self.assertEqual(seen, [1], "Fenster schon vor der Aktion geschlossen")
        self.assertFalse(dialog.winfo_exists())


def _walk(widget):
    yield widget
    for child in widget.winfo_children():
        yield from _walk(child)


_PC = {}


def _pc_app():
    """Eine echte PC-App (fuer den Vorschau-Dialog), einmal je Lauf."""
    if not _PC:
        import customtkinter as ctk
        import app_gui
        import fisi_hilfe as fh
        fh.mark_tour_seen()
        app_gui.UpdateController.auto_check = lambda self: None
        app_gui.SyncController.auto_start = lambda self: None
        root = ctk.CTk()
        app = app_gui.FISIApp(root)
        for _ in range(4):
            root.update_idletasks()
            root.update()
        _PC.update(root=root, app=app)
    return _PC


# ============================================================================
#  Handy (mobile/src/main.py, SettingsScreen)
# ============================================================================

class HandyTest(Base):
    def setUp(self):
        super().setUp()
        import main
        self.main = main
        self.infos = []

    def screen(self, db, **extra):
        page = types.SimpleNamespace(update=lambda: None)
        fake = types.SimpleNamespace(
            db=db, _after_restore=lambda: None, _ask=lambda *a: None,
            app=types.SimpleNamespace(page=page, info=lambda t, m: self.infos.append((t, m))),
            **extra)
        for name in ("_save_failed",):
            function = getattr(self.main.SettingsScreen, name, None)
            if function is not None:
                setattr(fake, name, types.MethodType(function, fake))
        return fake

    def test_b_g_04_schalter_springt_zurueck(self):
        fisi_update.save_settings({"auto_check": True, "sync_auto": True})
        for method, key in (("_toggle_auto", "auto_check"), ("_toggle_sync_auto", "sync_auto")):
            with self.subTest(method):
                del self.infos[:]
                control = types.SimpleNamespace(value=False, update=lambda: None)
                with settings_unsaveable():
                    getattr(self.main.SettingsScreen, method)(
                        self.screen(None), types.SimpleNamespace(control=control))
                self.assertTrue(control.value, "Schalter zeigt aus, gespeichert ist an")
                self.assertTrue(fisi_update.load_settings()[key])
                self.assertEqual(len(self.infos), 1, self.infos)
                self.assertIn("Die Einstellung ließ sich nicht speichern", self.infos[0][1])

    def test_b_g_04_abgleich_nicht_mit_altem_repository(self):
        fisi_update.save_settings({"sync_repo": "alt/repo", "sync_token": TOKEN})
        runs = []
        label = types.SimpleNamespace(value="", color=None)
        fake = self.screen(None, entry_repo=types.SimpleNamespace(value="neu/repo"),
                           entry_token=types.SimpleNamespace(value=TOKEN), lbl_sync=label,
                           btn_sync=types.SimpleNamespace(set_enabled=lambda on: None))
        fake.app.sync = types.SimpleNamespace(run=lambda: runs.append(1))
        with settings_unsaveable():
            self.main.SettingsScreen.sync_now(fake)
        self.assertEqual(runs, [], "Abgleich mit dem alten Repository gestartet")
        self.assertIn("Die Einstellung ließ sich nicht speichern", label.value)

    def test_b_g_05_gesperrte_datenbank_meldet(self):
        backup = self.backup_of(self.learned(self.db("quelle.db"), 4, "neu"))
        db = self.learned(self.db(), 2, "alt")
        before = _rows(db)
        fake = self.screen(db)
        with locked(db.db_path):
            try:
                self.main.SettingsScreen._merge_backup(fake, backup)
            except Exception as error:  # noqa: BLE001 - alte Fassung wirft
                self.infos.append(("ausnahme", repr(error)))
        self.assertEqual(len(self.infos), 1, self.infos)
        self.assertIn("Die Sicherung ließ sich nicht einspielen", self.infos[0][1])
        self.assertEqual(_rows(db), before)
        # Alles ersetzen: zwei Rueckfragen (confirm), dann die Aktion
        del self.infos[:]
        fake.app.confirm = lambda title, message, on_yes: on_yes()
        with locked(db.db_path):
            try:
                self.main.SettingsScreen._replace_backup(fake, backup)
            except Exception as error:  # noqa: BLE001
                self.infos.append(("ausnahme", repr(error)))
        self.assertEqual(len(self.infos), 1, self.infos)
        self.assertIn("Die Sicherung ließ sich nicht einspielen", self.infos[0][1])
        self.assertEqual(_rows(db), before)


# ============================================================================
#  PC und Handy gleich
# ============================================================================

class TexteTest(unittest.TestCase):
    def test_pc_und_handy_nutzen_dieselben_texte(self):
        with open(os.path.join(CODE, "app_gui.py"), encoding="utf-8") as handle:
            pc = handle.read()
        with open(os.path.join(CODE, "mobile", "src", "main.py"), encoding="utf-8") as handle:
            handy = handle.read()
        for needle in ("fo.SAVE_FAILED_TITLE, fo.SAVE_FAILED", "fsi.restore_error_text(error)",
                       "fsi.PREVIEW_HINT", "fsi.replace_question(backup)",
                       "fsi.merge_message(count"):
            with self.subTest(needle):
                self.assertTrue(needle in pc, "PC: " + needle)
                self.assertTrue(needle in handy, "Handy: " + needle)


class ProjektLoeschenTest(unittest.TestCase):
    """B-G-09 (nur der Text): die Rueckfrage sagt, dass die Eingaben bleiben."""

    def test_b_g_09_rueckfrage_ehrlich_und_gleich(self):
        import fisi_projekt as fpj
        text = fpj.delete_question({"titel": "Netzplan"})
        self.assertTrue(text.startswith("„Netzplan“ löschen?"))
        self.assertIn("nur ausgeblendet, nicht entfernt", text)
        self.assertIn("in Sicherungen", text)
        with open(os.path.join(CODE, "app_gui.py"), encoding="utf-8") as handle:
            pc = handle.read()
        with open(os.path.join(CODE, "mobile", "src", "main.py"), encoding="utf-8") as handle:
            handy = handle.read()
        self.assertTrue("fpj.delete_question(self.fields)" in pc, "PC")
        self.assertTrue("fpj.delete_question(self.fields)" in handy, "Handy")


def tearDownModule():
    if _PC:
        try:
            root = _PC["root"]
            for job in root.tk.splitlist(root.tk.call("after", "info")):
                root.tk.call("after", "cancel", job)
            root.destroy()
        except Exception:  # noqa: BLE001
            pass
    shutil.rmtree(_TMP, ignore_errors=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
