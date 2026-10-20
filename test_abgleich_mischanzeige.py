#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
C-4 (ab 0.63.2): Zeile "Mischbetrieb" unter dem Abgleich-Status, PC = Handy.

fisi_optionen.sync_mixed_text() liefert
  * "" (Zeile nicht gezeigt), wenn der Abgleich nicht eingerichtet ist oder
    noch nie lief (Freigabe 4.4 Nr. 4, S6-6),
  * "Abgleich: volle Schutzwirkung aktiv.", wenn kein Geraet vor 0.62.4
    innerhalb von fisi_sync.MIXED_HOLD mit abgeglichen hat,
  * sonst "Abgleich: volle Schutzwirkung ab TT.MM.JJJJ (ein Gerät mit
    älterer Version hat zuletzt am TT.MM. abgeglichen)."
Entschieden wird mit derselben Regel wie im Abgleich (_mixed_recent), auch
genau an der Grenze. fisi_sync wird nur gelesen: Der Quelltext der gelesenen
Teile ist Zeichen fuer Zeichen der von 0.63.1 (Pruefsumme unten).

Ohne Oberflaeche. MISCH_CODE=<ordner> prueft einen anderen Stand (Gegenprobe
gegen 14b3bd4: dort fehlt die Funktion, die Tests sind rot).
Start:  python test_abgleich_mischanzeige.py
"""

import ast
import datetime
import hashlib
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
CODE = os.path.abspath(os.environ.get("MISCH_CODE") or HERE)
WORK = tempfile.mkdtemp(prefix="fisi_mischanzeige_")
for _name in ("HOME", "USERPROFILE", "APPDATA", "LOCALAPPDATA", "XDG_DATA_HOME",
              "XDG_CONFIG_HOME"):
    os.environ[_name] = WORK
os.environ["FISI_DB_PATH"] = os.path.join(WORK, "standard.db")
sys.path.insert(0, CODE)

import fisi_core  # noqa: E402
import fisi_optionen as fo  # noqa: E402
import fisi_sync  # noqa: E402

CONFIGURED = {"sync_repo": "pruef/lernstand-attrappe",
              "sync_token": "PLATZHALTER-KEIN-ECHTES-TOKEN",
              "sync_last": "2026-10-01 12:00:00"}
DONE = "Abgleich: volle Schutzwirkung aktiv."
UTC = datetime.timezone.utc
NOW = datetime.datetime(2026, 10, 13, 10, 0, 0, tzinfo=UTC)

# Quelltext der gelesenen Teile von fisi_sync.py auf 0.63.1 (14b3bd4):
# _parse_utc, _mixed_recent, _note_mixed, is_configured, sync_settings,
# MIXED_KEY, MIXED_HOLD (Zeilenenden vereinheitlicht)
SYNC_READ_SHA256 = "94ac00276f1dbaf885df985080256facc9dce9d02bf767b52988275c50c08953"
SYNC_READ_NAMES = ("_parse_utc", "_mixed_recent", "_note_mixed", "is_configured",
                   "sync_settings")
SYNC_READ_CONSTS = ("MIXED_KEY", "MIXED_HOLD")


def read_parts_sha256(path):
    with open(path, encoding="utf-8") as handle:
        src = handle.read().replace("\r\n", "\n")
    parts = []
    for node in ast.parse(src).body:
        if isinstance(node, ast.FunctionDef) and node.name in SYNC_READ_NAMES:
            parts.append(ast.get_source_segment(src, node))
        elif isinstance(node, ast.Assign) and any(
                getattr(target, "id", "") in SYNC_READ_CONSTS for target in node.targets):
            parts.append(ast.get_source_segment(src, node))
    return len(parts), hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()


def tearDownModule():
    shutil.rmtree(WORK, ignore_errors=True)


class MischanzeigeTest(unittest.TestCase):

    def setUp(self):
        self.path = os.path.join(WORK, "%s.db" % self.id().rsplit(".", 1)[-1])
        self.db = fisi_core.DBManager(db_path=self.path,
                                      error_handler=lambda m: sys.stderr.write(m))

    def seen(self, moment):
        self.db.set_meta(fisi_sync.MIXED_KEY, moment.isoformat())

    def text(self, settings=CONFIGURED, now=NOW):
        return fo.sync_mixed_text(self.db, now=now, settings=dict(settings))

    # -- Sichtbarkeit (S6-6) ---------------------------------------------

    def test_nicht_eingerichtet_leer(self):
        self.seen(NOW - datetime.timedelta(days=2))
        for settings in ({"sync_repo": "", "sync_token": "x", "sync_last": "2026-10-01"},
                         {"sync_repo": "a/b", "sync_token": " ", "sync_last": "2026-10-01"}):
            with self.subTest(settings):
                self.assertEqual(self.text(settings), "")

    def test_nie_abgeglichen_leer(self):
        settings = dict(CONFIGURED, sync_last="")
        self.assertEqual(self.text(settings), "")
        self.seen(NOW - datetime.timedelta(days=2))
        self.assertEqual(self.text(settings), "")

    def test_einstellungen_aus_der_datei(self):
        # ohne settings liest die Funktion einstellungen.json (wie die Oberflaeche)
        self.assertEqual(fo.sync_mixed_text(self.db, now=NOW), "")
        fisi_sync.save_sync_settings(**CONFIGURED)
        try:
            self.assertEqual(fo.sync_mixed_text(self.db, now=NOW), DONE)
        finally:
            fisi_sync.save_sync_settings(sync_repo="", sync_token="", sync_last="")

    # -- Inhalt ------------------------------------------------------------

    def test_kein_mischwert_aktiv(self):
        self.assertIsNone(self.db.get_meta(fisi_sync.MIXED_KEY))
        self.assertEqual(self.text(), DONE)
        self.db.set_meta(fisi_sync.MIXED_KEY, "")    # so loescht _note_mixed
        self.assertEqual(self.text(), DONE)

    def test_mischwert_vor_zwei_tagen(self):
        seen = NOW - datetime.timedelta(days=2)
        self.seen(seen)
        until = (seen + datetime.timedelta(seconds=fisi_sync.MIXED_HOLD)).astimezone()
        expected = ("Abgleich: volle Schutzwirkung ab %s (ein Gerät mit älterer Version "
                    "hat zuletzt am %s abgeglichen)." % (until.strftime("%d.%m.%Y"),
                                                         seen.astimezone().strftime("%d.%m.")))
        self.assertEqual(self.text(), expected)
        # Datum + 7 Tage, unabhaengig von der Zeitzone des Rechners
        self.assertEqual(MIXED_HOLD_DAYS, 7)
        self.assertEqual(until.date() - seen.astimezone().date(), datetime.timedelta(days=7))

    def test_mischwert_alt_aktiv(self):
        self.seen(NOW - datetime.timedelta(days=30))
        self.assertEqual(self.text(), DONE)

    def test_grenze_wie_im_abgleich(self):
        hold = datetime.timedelta(seconds=fisi_sync.MIXED_HOLD)
        for offset, recent in ((hold, True),
                               (hold + datetime.timedelta(seconds=1), False),
                               (hold - datetime.timedelta(seconds=1), True)):
            with self.subTest(offset):
                self.seen(NOW - offset)
                self.assertEqual(fisi_sync._mixed_recent(self.db, NOW), recent)
                text = self.text()
                if recent:
                    self.assertTrue(text.startswith("Abgleich: volle Schutzwirkung ab "), text)
                else:
                    self.assertEqual(text, DONE)

    def test_liest_nur(self):
        self.seen(NOW - datetime.timedelta(days=2))
        with open(self.path, "rb") as handle:
            before = hashlib.sha256(handle.read()).hexdigest()
        self.text()
        self.text(now=NOW + datetime.timedelta(days=30))
        with open(self.path, "rb") as handle:
            self.assertEqual(hashlib.sha256(handle.read()).hexdigest(), before)

    def test_scheitert_nie(self):
        class Kaputt:
            def get_meta(self, key):
                raise RuntimeError("kaputt")
        self.assertEqual(fo.sync_mixed_text(Kaputt(), now=NOW, settings=dict(CONFIGURED)), "")

    # -- PC = Handy, fisi_sync nur gelesen -------------------------------

    def test_pc_und_handy_rufen_dieselbe_funktion(self):
        with open(os.path.join(CODE, "app_gui.py"), encoding="utf-8") as handle:
            pc = handle.read()
        with open(os.path.join(CODE, "mobile", "src", "main.py"), encoding="utf-8") as handle:
            handy = handle.read()
        self.assertTrue("fo.sync_mixed_text(self.app.db)" in pc, "PC")
        self.assertTrue("fo.sync_mixed_text(self.app.db)" in handy, "Handy")
        # in show_sync_status, damit es auch nach dem automatischen Abgleich stimmt
        for name, src in (("PC", pc), ("Handy", handy)):
            with self.subTest(name):
                start = src.index("    def show_sync_status(self, result, error):")
                body = src[start:src.index("\n    def ", start + 10)]
                self.assertTrue("sync_mixed" in body, name)

    def test_fisi_sync_gelesene_teile_unveraendert(self):
        self.assertEqual(read_parts_sha256(os.path.join(CODE, "fisi_sync.py")),
                         (7, SYNC_READ_SHA256))


MIXED_HOLD_DAYS = fisi_sync.MIXED_HOLD // 86400


if __name__ == "__main__":
    unittest.main(verbosity=2)
