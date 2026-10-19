#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
B-G-09 (ab 0.63.2): "Projekt löschen" loescht die Eingaben wirklich.

Bis 0.63.1 wurde das Projekt nur ausgeblendet (Feld "_geloescht"), die Texte
blieben in Datenbank, Sicherung und Abgleich-Datei. Ab 0.63.2 schreibt
fisi_projekt.delete_project() nach dem Ausblenden je Feld eine neuere, leere
Fassung; die vorhandene Regel "neueste Fassung je Feld gilt" (seit 0.51)
entfernt die alten Zeilen sofort und nach dem Abgleich auf allen Geraeten,
auch auf Geraeten mit 0.63.1 (Gegenprobe mit dem Code aus dem Tag v0.63.1 in
einem eigenen Prozess). fisi_sync.py und fisi_core.py bleiben unveraendert.

Rueckfrage (Freigabe 4.4 Nr. 2): Der Satz zum Abgleich und der Hinweis auf
GitHub stehen nur bei eingerichtetem Abgleich.

PROJEKT_CODE=<ordner> prueft einen anderen Stand (Gegenprobe gegen 14b3bd4:
dort sind die Tests zum Loeschen und zur Rueckfrage rot).
Start:  python test_projekt_loeschen.py
"""

import gzip
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tarfile
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
CODE = os.path.abspath(os.environ.get("PROJEKT_CODE") or HERE)
WORK = tempfile.mkdtemp(prefix="fisi_projekt_loeschen_")
for _name in ("HOME", "USERPROFILE", "APPDATA", "LOCALAPPDATA", "XDG_DATA_HOME",
              "XDG_CONFIG_HOME"):
    os.environ[_name] = WORK
os.environ["FISI_DB_PATH"] = os.path.join(WORK, "standard.db")
sys.path.insert(0, CODE)

import fisi_core  # noqa: E402
import fisi_projekt as fpj  # noqa: E402
import fisi_sicherung as fsi  # noqa: E402
import fisi_sync  # noqa: E402

IN_CI = bool(os.environ.get("GITHUB_ACTIONS") or os.environ.get("CI"))
SECRET = "PRIVATER TEXT XYZ"
OLD_TAG = "v0.63.1"

# Geraet mit altem Code: liest die Abgleich-Datei (JSON) und fuehrt sie mit
# merge_into_local des alten Stands zusammen, gibt Felder und Rohzeilen aus
# und schreibt seine eigene Datei (export_local) zurueck.
OLD_DEVICE = r'''
import json, sys
code, db_path, remote_path, out_path = sys.argv[1:5]
sys.path.insert(0, code)
import fisi_core, fisi_sync
db = fisi_core.DBManager(db_path=db_path)
with open(remote_path, encoding="utf-8") as handle:
    fisi_sync.merge_into_local(db, json.load(handle))
import sqlite3
conn = sqlite3.connect(db_path)
rows = [r[0] for r in conn.execute("SELECT wert FROM abschlussprojekt")]
conn.close()
with open(out_path, "w", encoding="utf-8") as handle:
    json.dump(fisi_sync.export_local(db), handle, ensure_ascii=False)
print(json.dumps({"felder": db.project_fields(), "zeilen": rows,
                  "datei": fisi_sync.__file__}, ensure_ascii=False))
'''


def new_db(name):
    return fisi_core.DBManager(db_path=os.path.join(WORK, name + ".db"),
                               error_handler=lambda m: sys.stderr.write("DB: %s\n" % m))


def raw_values(db):
    conn = sqlite3.connect(db.db_path)
    try:
        return [row[0] for row in conn.execute("SELECT wert FROM abschlussprojekt")]
    finally:
        conn.close()


def make_project(db):
    project = fpj.create_project(db, SECRET + " Titel")
    db.save_project_field(project, "ausgangslage", SECRET + " Ausgangslage")
    db.save_project_field(project, "ziel", SECRET + " Ziel")
    db.save_project_field(project, fpj.PAGES_FIELD, "15")
    return project


_OLD = {}


def old_code():
    """Ordner mit dem Code aus OLD_TAG (git archive), oder None."""
    if OLD_TAG in _OLD:
        return _OLD[OLD_TAG]
    target = os.path.join(WORK, "stand_" + OLD_TAG)

    def archive():
        proc = subprocess.run(["git", "-C", HERE, "archive", "--format=tar", OLD_TAG],
                              capture_output=True)
        if proc.returncode:
            return False
        os.makedirs(target, exist_ok=True)
        tar_path = target + ".tar"
        with open(tar_path, "wb") as handle:
            handle.write(proc.stdout)
        with tarfile.open(tar_path) as tar:
            try:
                tar.extractall(target, filter="data")
            except TypeError:
                tar.extractall(target)
        os.remove(tar_path)
        return True

    ok = archive()
    if not ok:
        subprocess.run(["git", "-C", HERE, "fetch", "--depth=1", "--no-tags", "origin",
                        "+refs/tags/%s:refs/tags/%s" % (OLD_TAG, OLD_TAG)],
                       capture_output=True, timeout=120)
        ok = archive()
    _OLD[OLD_TAG] = target if ok else None
    return _OLD[OLD_TAG]


def tearDownModule():
    shutil.rmtree(WORK, ignore_errors=True)


class LoeschenTest(unittest.TestCase):

    def setUp(self):
        self.name = self.id().rsplit(".", 1)[-1]
        self.pc = new_db(self.name + "_pc")

    def test_b_g_09_projekttext_weg(self):
        project = make_project(self.pc)
        self.assertTrue(any(SECRET in value for value in raw_values(self.pc)))
        fpj.delete_project(self.pc, project)
        self.assertNotIn(project, fpj.projects(self.pc))
        # Datenbank, Abgleich-Datei und neue Sicherung ohne den Text
        self.assertFalse([v for v in raw_values(self.pc) if SECRET in v], raw_values(self.pc))
        exported = json.dumps(fisi_sync.export_local(self.pc), ensure_ascii=False)
        self.assertNotIn(SECRET, exported)
        backup = gzip.decompress(fsi.create_backup(self.pc, "0.63.2")).decode("utf-8")
        self.assertNotIn(SECRET, backup)
        # je Feld genau eine Zeile (leer), das Projekt bleibt ausgeblendet
        fields = self.pc.project_fields()[project]
        self.assertEqual(fields[fpj.DELETED_FIELD], "1")
        self.assertEqual({k: v for k, v in fields.items() if k != fpj.DELETED_FIELD},
                         {fpj.TITLE_FIELD: "", "ausgangslage": "", "ziel": "",
                          fpj.PAGES_FIELD: ""})
        self.assertEqual(len(raw_values(self.pc)), 5)

    def test_b_g_09_andere_projekte_bleiben(self):
        keep = fpj.create_project(self.pc, "Anderes Projekt")
        self.pc.save_project_field(keep, "ziel", "bleibt")
        project = make_project(self.pc)
        fpj.delete_project(self.pc, project)
        self.assertEqual(fpj.projects(self.pc)[keep],
                         {fpj.TITLE_FIELD: "Anderes Projekt", "ziel": "bleibt"})

    def test_b_g_09_abbruch_projekt_ausgeblendet(self):
        """Bricht das Loeschen nach dem ersten Schreiben ab (z.B. Datenbank
        gesperrt), ist das Projekt wenigstens ausgeblendet (wie bis 0.63.1)."""
        project = make_project(self.pc)
        real = self.pc.save_project_field
        calls = []

        def once_then_fail(*args):
            calls.append(args)
            return real(*args) if len(calls) == 1 else False

        self.pc.save_project_field = once_then_fail
        try:
            result = fpj.delete_project(self.pc, project)
        finally:
            del self.pc.save_project_field
        self.assertFalse(result)
        self.assertEqual(calls[0], (project, fpj.DELETED_FIELD, "1"))
        self.assertNotIn(project, fpj.projects(self.pc))

    def test_b_g_09_ueber_abgleich(self):
        handy = new_db(self.name + "_handy")
        project = make_project(self.pc)
        fisi_sync.merge_into_local(handy, fisi_sync.export_local(self.pc))
        self.assertTrue(any(SECRET in value for value in raw_values(handy)))
        fpj.delete_project(self.pc, project)
        fisi_sync.merge_into_local(handy, fisi_sync.export_local(self.pc))
        self.assertFalse([v for v in raw_values(handy) if SECRET in v])
        self.assertNotIn(project, fpj.projects(handy))
        # Rueckweg: die Datei des Handys bringt den Text nicht zurueck
        fisi_sync.merge_into_local(self.pc, fisi_sync.export_local(handy))
        self.assertFalse([v for v in raw_values(self.pc) if SECRET in v])

    def test_b_g_09_ueber_abgleich_altes_geraet(self):
        """Ein Geraet mit 0.63.1 (eigener Prozess, Code aus dem Tag) bekommt
        nach dem Abgleich ebenfalls keinen Text mehr und bringt ihn nicht
        zurueck."""
        folder = old_code()
        if folder is None:
            if IN_CI:
                self.fail("Code aus %s nicht verfuegbar" % OLD_TAG)
            self.skipTest("Code aus %s nicht verfuegbar (git archive)" % OLD_TAG)
        old_db = os.path.join(WORK, self.name + "_alt.db")
        remote = os.path.join(WORK, self.name + "_datei.json")
        back = os.path.join(WORK, self.name + "_zurueck.json")
        script = os.path.join(WORK, "altes_geraet.py")
        with open(script, "w", encoding="utf-8") as handle:
            handle.write(OLD_DEVICE)

        def old_device_sync():
            with open(remote, "w", encoding="utf-8") as handle:
                json.dump(fisi_sync.export_local(self.pc), handle, ensure_ascii=False)
            env = dict(os.environ, PYTHONIOENCODING="utf-8")
            proc = subprocess.run([sys.executable, "-I", "-B", script, folder, old_db,
                                   remote, back], capture_output=True, text=True,
                                  encoding="utf-8", env=env, cwd=WORK, timeout=120)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            return json.loads(proc.stdout.strip().splitlines()[-1])

        project = make_project(self.pc)
        first = old_device_sync()
        self.assertTrue(first["datei"].startswith(folder), first["datei"])
        self.assertTrue(any(SECRET in value for value in first["zeilen"]))
        fpj.delete_project(self.pc, project)
        after = old_device_sync()
        self.assertFalse([v for v in after["zeilen"] if SECRET in v], after["zeilen"])
        self.assertEqual(after["felder"][project][fpj.DELETED_FIELD], "1")
        with open(back, encoding="utf-8") as handle:
            back_data = json.load(handle)
        self.assertNotIn(SECRET, json.dumps(back_data, ensure_ascii=False))
        fisi_sync.merge_into_local(self.pc, back_data)
        self.assertFalse([v for v in raw_values(self.pc) if SECRET in v])


class RueckfrageTest(unittest.TestCase):
    """Wortlaut (zur Abnahme): mit und ohne eingerichteten Abgleich."""

    WITH_SYNC = ("„Netzplan“ löschen? Das Projekt und alle seine Eingaben werden gelöscht, "
                 "nach dem Abgleich auch auf deinen anderen Geräten. Das lässt sich in der "
                 "App nicht rückgängig machen.\n\nHinweis: Ältere Sicherungsdateien und "
                 "frühere Stände im Verlauf des Abgleich-Repositorys auf GitHub enthalten "
                 "die Eingaben weiterhin.")
    # Ab 0.63.2 (F31 (b), N16-F4): zweiter Satz im selben "Hinweis:"-Absatz
    WITHOUT_SYNC = ("„Netzplan“ löschen? Das Projekt und alle seine Eingaben werden "
                    "gelöscht. Das lässt sich in der App nicht rückgängig machen.\n\n"
                    "Hinweis: Ältere Sicherungsdateien enthalten die Eingaben weiterhin. "
                    "Falls du den Abgleich früher genutzt hast, enthalten frühere Stände "
                    "im Abgleich-Repository auf GitHub die Eingaben weiterhin.")
    # N16-F5 (Weisung zu Meldung 40): ohne eingerichteten Abgleich darf die
    # Rueckfrage nichts zusagen, was das Loeschen ueber dieses Geraet hinaus
    # (andere Geraete, Abgleich, GitHub) oder fuer immer bewirkt
    VERBOTENE_ZUSAGEN = ("nach dem abgleich", "beim abgleich", "beim nächsten abgleich",
                         "anderen geräten", "andere geräte", "allen geräten", "überall",
                         "aus dem abgleich-repository", "aus github", "auf github gelöscht",
                         "auch auf github", "endgültig", "dauerhaft", "restlos", "spurlos",
                         "vollständig", "unwiderruflich")

    def tearDown(self):
        fisi_sync.save_sync_settings(sync_repo="", sync_token="")

    def test_mit_abgleich(self):
        fisi_sync.save_sync_settings(sync_repo="a/b", sync_token="PLATZHALTER")
        self.assertEqual(fpj.delete_question({"titel": "Netzplan"}), self.WITH_SYNC)

    def test_ohne_abgleich(self):
        fisi_sync.save_sync_settings(sync_repo="", sync_token="")
        text = fpj.delete_question({"titel": "Netzplan"})
        self.assertEqual(text, self.WITHOUT_SYNC)
        # F31 (b) nennt GitHub genau einmal (frueher: assertNotIn "Abgleich"/"GitHub")
        self.assertEqual(text.count("GitHub"), 1)
        for wort in self.VERBOTENE_ZUSAGEN:
            self.assertNotIn(wort, text.lower())
        # N16-F4: der Satz ist der zweite Satz im selben "Hinweis:"-Absatz
        absaetze = text.split("\n\n")
        self.assertEqual(len(absaetze), 2)
        self.assertTrue(absaetze[1].startswith("Hinweis: Ältere Sicherungsdateien enthalten "
                                               "die Eingaben weiterhin. Falls du den Abgleich "
                                               "früher genutzt hast,"), absaetze[1])
        # nur Repository ohne Zugangsschluessel gilt nicht als eingerichtet
        fisi_sync.save_sync_settings(sync_repo="a/b", sync_token="")
        self.assertEqual(fpj.delete_question({"titel": "Netzplan"}), self.WITHOUT_SYNC)

    def test_pc_und_handy_gleich(self):
        with open(os.path.join(CODE, "app_gui.py"), encoding="utf-8") as handle:
            pc = handle.read()
        with open(os.path.join(CODE, "mobile", "src", "main.py"), encoding="utf-8") as handle:
            handy = handle.read()
        self.assertTrue("fpj.delete_question(self.fields)" in pc, "PC")
        self.assertTrue("fpj.delete_question(self.fields)" in handy, "Handy")


if __name__ == "__main__":
    unittest.main(verbosity=2)
