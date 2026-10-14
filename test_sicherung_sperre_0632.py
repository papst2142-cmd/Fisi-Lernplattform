#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests 0.63.2 FG-77 (Antwort Meldung 21, 2.3; K4): Schreibsperre waehrend
"Sicherung einspielen" -> "Zusammenfuehren", PC und Handy.

  * Sperre in merge_into_local (vor dessen Schreibblock, SyncError): die
    normale Sicherungs-Meldung, Datenbank unveraendert. Bis 0.63.1 kam die
    SyncError ungefangen (PC: Fehlerfenster von Tk, Handy: keine Meldung).
  * Sperre nach dem Zusammenfuehren, vor dem Wiederherstellen geloeschter
    Spielstaende (BackupError): ehrlicher Satz "Ein Teil der Sicherung kann
    schon uebernommen sein" - das Zusammengefuehrte ist da (K4).
  * Schon vorher gesperrt: unveraendert die normale Sicherungs-Meldung.

Werkzeuge aus test_sicherung_fehler.py (ohne dessen Tests zu erben).
Braucht eine Anzeige (z.B. xvfb-run) und Flet fuer die Handy-Tests.

Gegen einen anderen Code-Stand: SICHERUNG_CODE=<ordner> python test_sicherung_sperre_0632.py
"""

import types
import unittest
from unittest import mock

import test_sicherung_fehler as tf
import fisi_sicherung as fs
import fisi_sync
from fisi_core import DB_READ_ONLY_LINES

KAPUTT = DB_READ_ONLY_LINES["kaputt"]
VORHER = "Die Sicherung lässt sich nicht einspielen. " + KAPUTT
EHRLICH = ("Das Zusammenführen wurde unterbrochen. Ein Teil der Sicherung kann schon "
           "übernommen sein; es geht nichts verloren. " + KAPUTT + " Ist das behoben, "
           "spiele die Sicherung noch einmal mit „Zusammenführen“ ein.")


class Faelle:
    """Gemeinsame Ablaeufe; zeige(db, backup) ruft PC bzw. Handy auf und
    liefert die angezeigten Meldungen [(Titel, Text)]."""

    def daten(self):
        backup = self.backup_of(self.learned(self.db("quelle.db"), 4, "neu"))
        db = self.learned(self.db(), 2, "alt")
        return db, backup

    def test_fg_77_sperre_vor_dem_schreiben(self):
        """Sperre entsteht in merge_into_local (waehrend export_local, nach der
        ersten Pruefung): SyncError -> normale Sicherungs-Meldung, nichts
        geschrieben."""
        db, backup = self.daten()
        before = tf._rows(db)
        echt = fisi_sync.export_local

        def export(arg):
            db.read_only_reason = "kaputt"
            return echt(arg)

        with mock.patch.object(fisi_sync, "export_local", export):
            shown = self.zeige(db, backup)
        self.assertEqual(shown, [(fs.ERROR_TITLE, VORHER)])
        self.assertEqual(tf._rows(db), before)

    def test_fg_77_sperre_nach_dem_zusammenfuehren(self):
        """K4: Sperre nach dem Zusammenfuehren, vor dem Wiederherstellen eines
        geloeschten Spielstands -> ehrlicher Satz; das Zusammengefuehrte ist
        wirklich schon da."""
        db, backup = self.daten()
        before = tf._rows(db)
        echt = fisi_sync.merge_into_local

        def merge(*args, **kwargs):
            result = echt(*args, **kwargs)
            db.read_only_reason = "kaputt"
            return result

        lauf = [{"lauf": "l-weg", "name": "Platz 1"}]
        with mock.patch.object(fs, "deleted_runs", lambda *a: lauf), \
                mock.patch.object(fs, "_free_slots_after_merge", lambda *a: ([1], {})), \
                mock.patch.object(fs, "merge_into_local", merge):
            shown = self.zeige(db, backup)
        self.assertEqual(shown, [(fs.ERROR_TITLE, EHRLICH)])
        nachher = tf._rows(db)
        self.assertNotEqual(nachher, before, "nichts uebernommen - dann waere der Satz falsch")
        self.assertEqual(len(nachher["card_events"]), 6)

    def test_fg_77_schon_vorher_gesperrt(self):
        """Schutz: War die Datenbank schon vorher gesperrt, bleibt es bei der
        normalen Sicherungs-Meldung (nichts geschehen)."""
        db, backup = self.daten()
        before = tf._rows(db)
        db.read_only_reason = "kaputt"
        shown = self.zeige(db, backup)
        self.assertEqual(shown, [(fs.ERROR_TITLE, VORHER)])
        self.assertEqual(tf._rows(db), before)

    def test_fg_77_schutz_ohne_sperre(self):
        """Schutz: ohne Sperre wie bisher die Erfolgsmeldung."""
        db, backup = self.daten()
        shown = self.zeige(db, backup)
        self.assertEqual(shown, [(fs.ERROR_TITLE, fs.merge_message(4))])


class PCTest(Faelle, tf.Base):
    def setUp(self):
        super().setUp()
        import app_gui
        self.app_gui = app_gui
        self.shown, patches = tf._pc_messages()
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)

    def zeige(self, db, backup):
        fake = types.SimpleNamespace(
            db=db, app=types.SimpleNamespace(flush_inputs=lambda **k: None, root=None),
            _after_restore=lambda: None)
        del self.shown[:]
        self.app_gui.SettingsView._merge_backup(fake, backup)
        return [(item[1], item[2]) for item in self.shown
                if item[0] in ("showerror", "showinfo")]


class HandyTest(Faelle, tf.Base):
    def setUp(self):
        super().setUp()
        import main
        self.main = main

    def zeige(self, db, backup):
        infos = []
        page = types.SimpleNamespace(update=lambda: None)
        fake = types.SimpleNamespace(
            db=db, _after_restore=lambda: None,
            _ask=lambda title, message, on_answer: on_answer(True),
            app=types.SimpleNamespace(page=page, info=lambda t, m: infos.append((t, m))))
        self.main.SettingsScreen._merge_backup(fake, backup)
        return infos


class GleichTest(unittest.TestCase):
    def test_fg_77_pc_und_handy_gleich(self):
        """Text und Entscheidung am PC und am Handy gleich."""
        import app_gui
        import main
        self.assertEqual(app_gui.MSG_MERGE_INTERRUPTED, main.MSG_MERGE_INTERRUPTED)
        db = types.SimpleNamespace(read_only_reason="kaputt")
        for error, locked in ((fisi_sync.SyncError("x"), None),
                              (fs.BackupError("y"), None), (fs.BackupError("y"), "kaputt")):
            self.assertEqual(app_gui.merge_error_text(db, error, locked),
                             main.merge_error_text(db, error, locked))
        tf_db = types.SimpleNamespace(read_only_reason=None)
        error = fs.BackupError("anders")
        self.assertEqual(app_gui.merge_error_text(tf_db, error, None), "anders")
        self.assertEqual(main.merge_error_text(tf_db, error, None), "anders")


if __name__ == "__main__":
    unittest.main(verbosity=2)
