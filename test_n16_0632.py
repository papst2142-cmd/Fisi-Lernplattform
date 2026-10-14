#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
N16 (ab 0.63.2, N-f, FG-70; F32 umgesetzt als Variante (ii'), Weisung zu
Meldung 40 B1): Projektfelder nach "Projekt loeschen".

Bis zum Stand S6c (B-G-09) blieb der Text eines Feldes stehen, dessen Zeit
SPAETER lag als das Loeschen (vorgehende Uhr, andere Zeitzone, Offline-
Bearbeitung eines anderen Geraets). Ab 0.63.2 loescht
fisi_core.purge_superseded_project_rows in einem geloeschten Projekt
(Feld "_geloescht" = "1") jede NICHT LEERE Fassung, die spaeter liegt als
die frueheste Loeschung - beim Speichern und nach dem Import (Abgleich,
Sicherung "Zusammenfuehren"). Nur DELETE, nie UPDATE; "_geloescht" und die
leeren Fassungen von B-G-09 bleiben (B-G-09 auch auf Geraeten mit 0.63.1);
lebende Projekte bleiben unberuehrt.

Ablaeufe nach Testplan_N16 (Pruefer vor Bauer):
  Kern       Einzelgeraet E1-E14 und "lebende Projekte nie" (Teilmenge),
             im Testprozess mit Wegwerf-Datenbanken
  Geraete    Matrix 5.1 (20), Loescher mit 0.63.1 5.2 (10), Mischbetrieb
             M1-M6, drei Geraete (4), Feldarten F-a/F-b/F-c - als eigene
             Prozesse gegen die Attrappe (pruefung/abgleich_geraet_voll.py),
             0.63.1 aus dem Tag v0.63.1 (git archive)

"Ruhe" (AK6) = nach zwei Runden in zwei weiteren Runden kein Hochladen.
Bekannte Grenze (Testplan N16-F2, E3 Nico): Haelt ein Geraet mit 0.63.1
einen SPAETER datierten Text eines geloeschten Projekts, gibt es ein Hin
und Her (je Abgleich ein Hochladen), bis es aktualisiert ist. Diese Zellen
werden gemessen und als [Beleg] ausgegeben, nicht als Ruhe gefordert;
dass das Hin und Her mit dem Update endet, prueft M5 hart.
Bekannte Grenze N16-F-c: ein beim Loeschen unbekanntes Feld, FRUEHER
geschrieben, bleibt verborgen gespeichert (keine leere Fassung, nicht
spaeter als die Loeschung).

Gegenprobe gegen einen anderen Stand (14b3bd4 oder S6b+S6c ohne N16):
    ABGLEICH_CODE=<ordner mit dem Code> python test_n16_0632.py
Nur unter Linux/macOS (Zeitzone je Prozess ueber TZ).
"""

import gzip
import hashlib
import json
import os
import random
import shutil
import sqlite3
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
WORK_KERN = tempfile.mkdtemp(prefix="fisi_n16_")
HOME = os.path.join(WORK_KERN, "home")
os.makedirs(HOME)
for _name in ("HOME", "USERPROFILE", "APPDATA", "LOCALAPPDATA", "XDG_DATA_HOME",
              "XDG_CONFIG_HOME"):
    os.environ[_name] = HOME
os.environ["FISI_DB_PATH"] = os.path.join(HOME, "start.db")
os.environ.setdefault("FISI_SELFTEST", os.path.join(WORK_KERN, "selbsttest.log"))
os.environ["FISI_VORLADEN"] = "0"

import test_abgleich as ta  # noqa: E402  (Attrappe, Geraete, git archive)
import test_abgleich_0632 as tv  # noqa: E402  (GeraetVoll)

CODE = ta.CODE
sys.path.insert(0, CODE)
import fisi_core  # noqa: E402
import fisi_projekt as fpj  # noqa: E402
import fisi_sicherung as fsi  # noqa: E402
import fisi_sync  # noqa: E402

ALT = "v0.63.1"
HOUR = 3600.0
SECRET = "PRIVATER TEXT N16"
GELOESCHT = "_geloescht"
COLUMNS = list(fisi_sync.SYNC_TABLES["abschlussprojekt"])   # timestamp, projekt, feld, wert
_ZAEHLER = [0]

# Regel bis S6c (nur "neueste Fassung je Feld gilt"), als Vergleich fuer
# "lebende Projekte nie": wortgleich zu purge_superseded_project_rows bis S6c
REGEL_BIS_S6C = (
    "DELETE FROM abschlussprojekt WHERE EXISTS ("
    " SELECT 1 FROM abschlussprojekt AS neu"
    " WHERE neu.projekt = abschlussprojekt.projekt"
    " AND neu.feld = abschlussprojekt.feld"
    " AND (neu.timestamp > abschlussprojekt.timestamp"
    "  OR (neu.timestamp = abschlussprojekt.timestamp"
    "      AND neu.uid > abschlussprojekt.uid)))")


def bericht(text):
    ta.bericht(text)


def neue_db(name="db"):
    _ZAEHLER[0] += 1
    folder = os.path.join(WORK_KERN, "%s_%d" % (name, _ZAEHLER[0]))
    os.makedirs(folder)
    return fisi_core.DBManager(os.path.join(folder, "lern.db"),
                               error_handler=lambda message: None)


def rohzeilen(db, projekt=None):
    """[(uid, timestamp, projekt, feld, wert)], sortiert."""
    conn = sqlite3.connect(db.db_path)
    try:
        rows = conn.execute("SELECT uid, timestamp, projekt, feld, wert FROM abschlussprojekt"
                            ).fetchall()
    finally:
        conn.close()
    return sorted(r for r in rows if projekt is None or r[2] == projekt)


def werte(rows, projekt):
    return sorted(r[4] for r in rows if r[2] == projekt)


def datei(zeilen):
    """Abgleich-Datei eines anderen Geraets nur mit Projektzeilen
    [(uid, timestamp, projekt, feld, wert)]."""
    return {"format": fisi_sync.FORMAT, "markers": {},
            "columns": {"abschlussprojekt": COLUMNS},
            "tables": {"abschlussprojekt": [
                [uid] + [dict(zip(("timestamp", "projekt", "feld", "wert"), rest))[c]
                         for c in COLUMNS] for uid, *rest in zeilen]}}


def verschoben(stempel, sekunden):
    """Zeitstempel (Ortszeit ohne Zone, wie _now_fine) um sekunden verschoben."""
    import datetime
    base = datetime.datetime.strptime(stempel[:26].ljust(26, "0") if "." in stempel
                                      else stempel + ".000000", "%Y-%m-%d %H:%M:%S.%f")
    return (base + datetime.timedelta(seconds=sekunden)).strftime("%Y-%m-%d %H:%M:%S.%f")


def loeschzeit(db, projekt):
    return min(r[1] for r in rohzeilen(db, projekt) if r[3] == GELOESCHT)


def ohne_text(rows, projekt):
    """AK1: im geloeschten Projekt nur noch "1" (_geloescht) und leere Fassungen."""
    return all(r[4] in ("", "1") and (r[4] == "" or r[3] == GELOESCHT)
               for r in rows if r[2] == projekt)


def tearDownModule():
    shutil.rmtree(WORK_KERN, ignore_errors=True)
    tv.tearDownModule()


# ============================================================================
#  Kern: Einzelgeraet (Testplan 4, E1-E14) und "lebende Projekte nie"
# ============================================================================

class N16Kern(unittest.TestCase):

    def setUp(self):
        self.db = neue_db(self.id().rsplit(".", 1)[-1])

    def projekt(self, db=None, titel=SECRET + " Titel"):
        db = db or self.db
        project = fpj.create_project(db, titel)
        db.save_project_field(project, "ausgangslage", SECRET + " Ausgangslage")
        db.save_project_field(project, "ziel", SECRET + " Ziel")
        db.save_project_field(project, fpj.PAGES_FIELD, "15")
        return project

    def spaetere_fassung(self, project, sekunden, feld="ausgangslage", wert=None,
                         uid="fremd-n16"):
        stempel = verschoben(loeschzeit(self.db, project), sekunden)
        fisi_sync.merge_into_local(self.db, datei([(uid, stempel, project, feld,
                                                    wert if wert is not None
                                                    else SECRET + " spaeter")]))
        return stempel

    def test_e1_wie_s6c(self):
        project = self.projekt()
        fpj.delete_project(self.db, project)
        rows = rohzeilen(self.db, project)
        self.assertEqual(werte(rows, project), ["", "", "", "", "1"])
        self.assertNotIn(project, fpj.projects(self.db))

    def test_e2_spaetere_fassung_zwei_stunden(self):
        project = self.projekt()
        fpj.delete_project(self.db, project)
        self.spaetere_fassung(project, 2 * HOUR)
        rows = rohzeilen(self.db, project)
        self.assertTrue(ohne_text(rows, project), rows)
        self.assertEqual([r[4] for r in rows if r[3] == GELOESCHT], ["1"])
        self.assertNotIn(project, fpj.projects(self.db))

    def test_e3_gleiche_zeit_bleibt_grenzfall(self):
        """Gleiche Zeit wie _geloescht ist nicht spaeter: die Fassung bleibt
        (beide uid-Richtungen). Festgelegtes Verhalten von (ii')."""
        for uid in ("0000-kleiner", "zzzz-groesser"):
            with self.subTest(uid=uid):
                self.db = neue_db("e3_" + uid)
                project = self.projekt()
                fpj.delete_project(self.db, project)
                stempel = loeschzeit(self.db, project)
                fisi_sync.merge_into_local(self.db, datei([(uid, stempel, project, "zusatz",
                                                            SECRET + " gleich")]))
                self.assertIn(SECRET + " gleich", werte(rohzeilen(self.db, project), project))

    def test_e4_eine_mikrosekunde_spaeter(self):
        project = self.projekt()
        fpj.delete_project(self.db, project)
        self.spaetere_fassung(project, 0.000001, feld="zusatz")
        self.assertTrue(ohne_text(rohzeilen(self.db, project), project))

    def test_e5_lebendes_projekt_byte_gleich(self):
        lebt = fpj.create_project(self.db, "Lebt")
        self.db.save_project_field(lebt, "ziel", "bleibt")
        geloescht = self.projekt()
        fpj.delete_project(self.db, geloescht)
        vorher = rohzeilen(self.db, lebt)
        stempel = verschoben(loeschzeit(self.db, geloescht), 2 * HOUR)
        fisi_sync.merge_into_local(self.db, datei([
            ("fremd-lebt", stempel, lebt, "ausgangslage", "spaeter, lebt"),
            ("fremd-tot", stempel, geloescht, "ziel", SECRET + " spaeter")]))
        nachher = rohzeilen(self.db, lebt)
        self.assertEqual(nachher, sorted(vorher + [("fremd-lebt", stempel, lebt,
                                                    "ausgangslage", "spaeter, lebt")]))
        self.assertEqual(fpj.projects(self.db)[lebt],
                         {fpj.TITLE_FIELD: "Lebt", "ziel": "bleibt",
                          "ausgangslage": "spaeter, lebt"})

    def test_e6_geloeschtes_ohne_spaetere_fassung_byte_gleich(self):
        p1, p3 = self.projekt(), self.projekt()
        fpj.delete_project(self.db, p3)
        vorher = rohzeilen(self.db, p3)
        fpj.delete_project(self.db, p1)
        self.spaetere_fassung(p1, 2 * HOUR)
        self.assertEqual(rohzeilen(self.db, p3), vorher)

    def test_e7_geloescht_null_ohne_wirkung(self):
        project = fpj.create_project(self.db, "Titel")
        self.db.save_project_field(project, GELOESCHT, "0")
        stempel = verschoben(loeschzeit(self.db, project), 2 * HOUR)
        fisi_sync.merge_into_local(self.db, datei([("fremd-e7", stempel, project, "ziel",
                                                    "spaeter")]))
        self.assertIn("spaeter", werte(rohzeilen(self.db, project), project))
        self.assertIn("Titel", werte(rohzeilen(self.db, project), project))

    def test_e8_frueheste_loeschung_zaehlt(self):
        """Zwei _geloescht-Zeilen (zwei Geraete haben geloescht): massgeblich
        ist die frueheste - auch wenn beide im selben Import kommen."""
        project = fpj.create_project(self.db, "Titel")
        t0 = rohzeilen(self.db, project)[0][1]
        t1, t_text, t2 = (verschoben(t0, s) for s in (60, 120, 180))
        fisi_sync.merge_into_local(self.db, datei([
            ("loesch-1", t1, project, GELOESCHT, "1"),
            ("text-1", t_text, project, "ziel", SECRET + " dazwischen"),
            ("loesch-2", t2, project, GELOESCHT, "1")]))
        rows = rohzeilen(self.db, project)
        self.assertNotIn(SECRET + " dazwischen", werte(rows, project))
        # direkt in der Regel (ohne Import): beide Zeilen liegen gleichzeitig vor
        conn = sqlite3.connect(self.db.db_path)
        try:
            cur = conn.cursor()
            for uid, ts, feld, wert in (("l1", t1, GELOESCHT, "1"),
                                        ("tx", t_text, "zusatz", SECRET + " direkt"),
                                        ("l2", t2, GELOESCHT, "1")):
                cur.execute("INSERT INTO abschlussprojekt (uid, timestamp, projekt, feld, wert)"
                            " VALUES (?, ?, ?, ?, ?)", (uid, ts, "p-e8", feld, wert))
            fisi_core.purge_superseded_project_rows(cur)
            conn.commit()
            rest = conn.execute("SELECT feld, wert FROM abschlussprojekt WHERE projekt = 'p-e8'"
                                ).fetchall()
        finally:
            conn.close()
        self.assertEqual(rest, [(GELOESCHT, "1")])

    def test_e9_spaetere_leere_fassung_bleibt(self):
        project = self.projekt()
        fpj.delete_project(self.db, project)
        stempel = self.spaetere_fassung(project, 2 * HOUR, wert="")
        self.assertIn(("fremd-n16", stempel, project, "ausgangslage", ""),
                      rohzeilen(self.db, project))

    def test_e10_sicherung_zusammenfuehren(self):
        project = self.projekt()
        fpj.delete_project(self.db, project)
        quelle = neue_db("e10_quelle")
        stempel = verschoben(loeschzeit(self.db, project), 2 * HOUR)
        fisi_sync.merge_into_local(quelle, datei([("fremd-e10", stempel, project, "ziel",
                                                   SECRET + " aus Sicherung")]))
        backup = fsi.read_backup(fsi.create_backup(quelle, "0.63.2"))
        fsi.merge_backup(self.db, backup)
        self.assertTrue(ohne_text(rohzeilen(self.db, project), project))
        self.assertNotIn(project, fpj.projects(self.db))

    def test_e11_alles_ersetzen_aeltere_sicherung_vorbestehend(self):
        """Nur dokumentiert (N16-F6, vorbestehend seit S6c): "Alles ersetzen"
        mit einer Sicherung von VOR dem Loeschen bringt das Projekt zurueck."""
        project = self.projekt()
        alt = fsi.read_backup(fsi.create_backup(self.db, "0.63.2"))
        fpj.delete_project(self.db, project)
        fsi.replace_all(self.db, alt, os.path.join(WORK_KERN, "e11_kopie"))
        sichtbar = project in fpj.projects(self.db)
        bericht("N16-E11 (N16-F6, vorbestehend): Projekt nach 'Alles ersetzen' mit "
                "aelterer Sicherung wieder sichtbar: %s" % sichtbar)
        self.assertTrue(sichtbar)

    def test_e12_export_und_sicherung_ohne_text(self):
        project = self.projekt()
        fpj.delete_project(self.db, project)
        self.spaetere_fassung(project, 2 * HOUR)
        self.assertNotIn(SECRET, json.dumps(fisi_sync.export_local(self.db), ensure_ascii=False))
        sicherung = gzip.decompress(fsi.create_backup(self.db, "0.63.2")).decode("utf-8")
        self.assertNotIn(SECRET, sicherung)

    def test_nur_delete_nie_update(self):
        """AK5: jede verbleibende Zeile ist in uid, Zeit und Wert unveraendert
        (Menge nachher Teilmenge von vorher + neu Importiertem)."""
        project = self.projekt()
        fpj.delete_project(self.db, project)
        vorher = set(rohzeilen(self.db))
        stempel = verschoben(loeschzeit(self.db, project), 2 * HOUR)
        neu = {("fremd-a", stempel, project, "ziel", SECRET + " a"),
               ("fremd-b", stempel, project, "titel", ""),
               ("fremd-c", stempel, project, "zusatz", SECRET + " c")}
        fisi_sync.merge_into_local(self.db, datei(sorted(neu)))
        nachher = set(rohzeilen(self.db))
        self.assertLessEqual(nachher, vorher | neu)
        self.assertIn(("fremd-b", stempel, project, "titel", ""), nachher)

    def test_lebende_projekte_nie_eine_zeile_geloescht(self):
        """Auflage B1: Bei lebenden Projekten loescht die neue Regel nie eine
        Zeile mehr als die Regel bis S6c (Teilmenge). Zufallsdaten mit festem
        Startwert: 60 Projekte, davon ein Teil geloescht (auch "_geloescht" =
        "0"), Fassungen frueher/gleich/spaeter, leer und nicht leer."""
        rnd = random.Random(1632)
        zeilen = []
        base = "2026-10-14 10:00:00.000000"
        for p in range(60):
            projekt = "p%02d" % p
            art = p % 4      # 0 lebt, 1 geloescht, 2 _geloescht = "0", 3 geloescht, 2x
            loesch = rnd.randint(-5, 5) * 60
            if art in (1, 3):
                zeilen.append(("g%02d" % p, verschoben(base, loesch), projekt, GELOESCHT, "1"))
            if art == 3:
                zeilen.append(("h%02d" % p, verschoben(base, loesch + 90), projekt, GELOESCHT,
                               "1"))
            if art == 2:
                zeilen.append(("g%02d" % p, verschoben(base, loesch), projekt, GELOESCHT, "0"))
            for i in range(rnd.randint(1, 9)):
                feld = rnd.choice(("titel", "ziel", "zusatz", "seitenziel"))
                sek = loesch + rnd.choice((-120, -1, 0, 0.000001, 1, 120, 7200))
                wert = rnd.choice(("", "Text %d-%d" % (p, i), "15"))
                zeilen.append(("u%02d-%d" % (p, i), verschoben(base, sek), projekt, feld, wert))

        def lauf(regel):
            conn = sqlite3.connect(":memory:")
            conn.execute("CREATE TABLE abschlussprojekt (id INTEGER PRIMARY KEY, uid TEXT,"
                         " timestamp TEXT, projekt TEXT, feld TEXT, wert TEXT)")
            conn.executemany("INSERT INTO abschlussprojekt (uid, timestamp, projekt, feld, wert)"
                             " VALUES (?, ?, ?, ?, ?)", zeilen)
            cur = conn.cursor()
            regel(cur)
            rest = set(conn.execute("SELECT uid, timestamp, projekt, feld, wert"
                                    " FROM abschlussprojekt"))
            conn.close()
            return rest

        neu = lauf(fisi_core.purge_superseded_project_rows)
        alt = lauf(lambda cur: cur.execute(REGEL_BIS_S6C))
        tot = {z[2] for z in zeilen if z[3] == GELOESCHT and z[4] == "1"}
        lebend = {z[2] for z in zeilen} - tot
        self.assertTrue(lebend and tot)
        # nur geloescht, nie geaendert oder dazu
        self.assertLessEqual(neu, set(zeilen))
        # lebende Projekte: genau dieselben Zeilen wie mit der Regel bis S6c
        self.assertEqual({z for z in neu if z[2] in lebend}, {z for z in alt if z[2] in lebend})
        # was die neue Regel zusaetzlich loescht: nur nicht leere Fassungen
        # geloeschter Projekte, spaeter als die frueheste Loeschung
        frueh = {}
        for z in zeilen:
            if z[3] == GELOESCHT and z[4] == "1":
                frueh[z[2]] = min(frueh.get(z[2], z[1]), z[1])
        weg = {z for z in zeilen if z[2] in tot} - {z for z in neu if z[2] in tot}
        for z in weg - (set(zeilen) - alt):
            self.assertTrue(z[3] != GELOESCHT and z[4] != "" and z[1] > frueh[z[2]], z)
        # und keine solche Fassung bleibt stehen
        for z in neu:
            if z[2] in tot and z[3] != GELOESCHT:
                self.assertFalse(z[4] != "" and z[1] > frueh[z[2]], z)
        bericht("lebende Projekte: %d, geloeschte: %d, Zeilen %d -> bis S6c %d, neu %d"
                % (len(lebend), len(tot), len(zeilen), len(alt), len(neu)))


# ============================================================================
#  Geraete: Abgleich mit Attrappe, 0.63.1 aus dem Tag (Testplan 5)
# ============================================================================

class N16Geraete(unittest.TestCase):
    """Geraete-Prozesse gegen die Attrappe. Werkzeuge aus test_abgleich und
    test_abgleich_0632 einzeln uebernommen (nicht geerbt, sonst liefen deren
    Tests hier ein zweites Mal)."""
    setUp = ta.AbgleichTest.setUp
    tearDown = ta.AbgleichTest.tearDown
    alle_sync = ta.AbgleichTest.alle_sync
    alter_code = ta.AbgleichTest.alter_code
    voll = tv.GeraeteTest.voll
    neu_starten = tv.GeraeteTest.neu_starten

    def zeit(self, stunden, **uhren):
        """Attrappe und alle Geraeteuhren auf echte Zeit + stunden (+ eigener
        Versatz je Geraet in Sekunden)."""
        ta.att.STATE.ctl["datum_versatz"] = stunden * HOUR
        for device in self.geraete:
            device("uhr", stunden * HOUR + uhren.get(device.name, 0.0))

    def code(self, version):
        return CODE if version == "neu" else self.alter_code(ALT)

    @staticmethod
    def zeilen(device, projekt="p1"):
        return [tuple(z) for z in device("projekt_zeilen")["zeilen"] if z[2] == projekt]

    def texte(self, device, projekt="p1"):
        return sorted(z[4] for z in self.zeilen(device, projekt))

    def spaete_texte(self, device, projekt="p1"):
        """Nicht leere Fassungen (ohne _geloescht), spaeter als die frueheste Loeschung."""
        rows = self.zeilen(device, projekt)
        loesch = [z[1] for z in rows if z[3] == GELOESCHT and z[4] == "1"]
        if not loesch:
            return []
        return sorted(z[4] for z in rows if z[3] != GELOESCHT and z[4] != ""
                      and z[1] > min(loesch))

    def ruhe(self, geraete):
        """Zwei Runden einschwingen, dann Hochladungen in zwei weiteren Runden."""
        self.alle_sync(geraete, 2)
        vorher = ta.commits()
        meldungen = []
        for _ in range(2):
            for device in geraete:
                meldungen.append("%s: %s" % (device.name, device.sync().get("meldung", "")))
        return ta.commits() - vorher, meldungen

    def pruefe_ende(self, name, neue, alte, alle):
        """AK1 auf allen neuen Geraeten, AK3 auf allen; Ruhe gefordert, wenn
        kein 0.63.1-Geraet einen spaeteren Text haelt (sonst bekannte Grenze,
        nur gemessen). Gibt die Messwerte zurueck."""
        messung = {}
        for device in alle:
            rows = self.zeilen(device)
            messung[device.name] = self.texte(device)
            self.assertIn(("1"), [z[4] for z in rows if z[3] == GELOESCHT],
                          "%s %s: _geloescht fehlt" % (name, device.name))
            self.assertEqual(device("projekte")["projekte"], [], "%s %s" % (name, device.name))
        for device in neue:
            self.assertTrue(ohne_text(self.zeilen(device), "p1"),
                            "%s %s: %s" % (name, device.name, self.zeilen(device)))
        grenze = [d.name for d in alte if self.spaete_texte(d)]
        uploads, meldungen = self.ruhe(alle)
        bericht("%s: Texte %s; Ruhe %d Hochladungen%s" % (
            name, json.dumps(messung, ensure_ascii=False), uploads,
            " (bekannte Grenze N16-F2: 0.63.1 haelt spaeteren Text auf %s)" % grenze
            if grenze else ""))
        if not grenze:
            self.assertEqual(uploads, 0, "%s: Hin und Her %s" % (name, meldungen))
        return {"texte": messung, "ruhe": uploads, "grenze": grenze}

    # ------------------------------------------------- 5.1 Matrix (20)
    URSACHEN = ("U1", "U2", "U3", "U4", "U5")

    def matrix_zelle(self, ursache, b_version, reihenfolge):
        ordner = "m51_%s_%s_%s" % (ursache, b_version, reihenfolge)
        tz_a, tz_b = ("UTC", "Etc/GMT-2") if ursache == "U3" else ("Europe/Berlin",) * 2
        a = self.voll("A", ordner=ordner, tz=tz_a)
        b = self.voll("B", code=self.code(b_version), ordner=ordner, tz=tz_b)
        self.zeit(0)
        a("projekt_feld", "p1", "titel", "Titel alt")
        a("projekt_feld", "p1", "ziel", "Ziel alt")
        a.sync()
        b.sync()
        versatz = {"U1": 2 * HOUR, "U2": 25 * HOUR, "U3": 0.0, "U4": 0.0, "U5": -2 * HOUR}
        if ursache != "U4":
            self.zeit(0.5, B=versatz[ursache])
            b("projekt_feld", "p1", "ziel", SECRET + " B")
        self.zeit(1)
        a("projekt_loeschen", "p1")
        if ursache == "U4":
            self.zeit(1.5)
            b("projekt_feld", "p1", "ziel", SECRET + " B offline")
        self.zeit(2)
        folge = (b, a) if reihenfolge == "B" else (a, b)
        for _ in range(2):
            for device in folge:
                device.sync()
        neue = [d for d in (a, b) if d.code == CODE]
        alte = [d for d in (a, b) if d.code != CODE]
        ergebnis = self.pruefe_ende(ordner, neue, alte, [a, b])
        if b_version == "alt" and ursache == "U5":
            # B-G-09 auch auf 0.63.1: frueherer Text weg
            self.assertTrue(ohne_text(self.zeilen(b), "p1"), self.zeilen(b))
        for device in (a, b):
            device.close()
            self.geraete.remove(device)
        return ergebnis

    def test_5_1_matrix(self):
        for ursache in self.URSACHEN:
            for b_version in ("neu", "alt"):
                for reihenfolge in ("B", "A"):
                    with self.subTest(ursache=ursache, b=b_version, zuerst=reihenfolge):
                        ta.server_reset()
                        self.matrix_zelle(ursache, b_version, reihenfolge)

    # ------------------------------------- 5.2 Loescher mit 0.63.1 (10)
    def loescher_alt(self, ursache, reihenfolge):
        ordner = "m52_%s_%s" % (ursache, reihenfolge)
        tz_a, tz_b = ("UTC", "Etc/GMT-2") if ursache == "U3" else ("Europe/Berlin",) * 2
        a = self.voll("A", code=self.code("alt"), ordner=ordner, tz=tz_a)
        b = self.voll("B", ordner=ordner, tz=tz_b)
        self.zeit(0)
        a("projekt_feld", "p1", "titel", "Titel alt")
        a("projekt_feld", "p1", "ziel", "Ziel alt")
        a.sync()
        b.sync()
        versatz = {"U1": 2 * HOUR, "U2": 25 * HOUR, "U3": 0.0, "U5": -2 * HOUR}
        if ursache != "U4":
            self.zeit(0.5, B=versatz[ursache])
            b("projekt_feld", "p1", "zusatz", SECRET + " B")
        self.zeit(1)
        a("projekt_loeschen", "p1")
        if ursache == "U4":
            self.zeit(1.5)
            b("projekt_feld", "p1", "zusatz", SECRET + " B offline")
        self.zeit(2)
        folge = (b, a) if reihenfolge == "B" else (a, b)
        for _ in range(2):
            for device in folge:
                device.sync()
        # auf B (0.63.2) kein spaeter geschriebener Text; aeltere Texte
        # bleiben bei (ii') stehen (das alte Geraet hat nur ausgeblendet)
        self.assertEqual(self.spaete_texte(b), [], self.zeilen(b))
        if ursache != "U5":
            self.assertNotIn(SECRET + " B", " ".join(self.texte(b)))
        self.assertIn("Titel alt", self.texte(b))
        messung = {d.name: self.texte(d) for d in (a, b)}
        grenze = [a.name] if self.spaete_texte(a) else []
        uploads, meldungen = self.ruhe([a, b])
        bericht("%s: Texte %s; Ruhe %d Hochladungen%s" % (
            ordner, json.dumps(messung, ensure_ascii=False), uploads,
            " (bekannte Grenze N16-F2)" if grenze else ""))
        if not grenze:
            self.assertEqual(uploads, 0, "%s: Hin und Her %s" % (ordner, meldungen))
        self.assertEqual(b("projekte")["projekte"], [])
        self.assertEqual(a("projekte")["projekte"], [])
        for device in (a, b):
            device.close()
            self.geraete.remove(device)

    def test_5_2_loescher_alt(self):
        for ursache in self.URSACHEN:
            for reihenfolge in ("B", "A"):
                with self.subTest(ursache=ursache, zuerst=reihenfolge):
                    ta.server_reset()
                    self.loescher_alt(ursache, reihenfolge)

    # ----------------------------------------------- 5.3 Mischbetrieb
    def test_m1_alt_geloescht_neu_gleicht_ab_still(self):
        o, n = self.voll("O", code=self.code("alt")), self.voll("N")
        self.zeit(0)
        o("projekt_feld", "p1", "titel", "Titel p1")
        o("projekt_loeschen", "p1")
        o.sync()
        n.sync()
        texte = {d.name: self.texte(d) for d in (o, n)}
        uploads, meldungen = self.ruhe([n, o])
        bericht("N16-M1: Texte %s; Ruhe %d; %s" % (json.dumps(texte, ensure_ascii=False),
                                                   uploads, meldungen[:2]))
        self.assertEqual(texte["N"], ["1", "Titel p1"])     # (ii'): nichts spaeter
        self.assertEqual(uploads, 0, meldungen)

    def test_m2_update_unter_0631_geloeschtes_bleibt_kein_schreiben_beim_start(self):
        """M2/E14: unter 0.63.1 geloeschtes Projekt (nur ausgeblendet); das
        Geraet wird auf 0.63.2 aktualisiert (gleiche Datenbank): Start ohne
        Schreiben, die alten Texte bleiben auch nach dem naechsten Speichern
        (nichts liegt spaeter als die Loeschung) und nach dem Abgleich."""
        o = self.voll("O", code=self.code("alt"))
        self.zeit(0)
        o("projekt_feld", "p1", "titel", "Titel p1")
        o("projekt_feld", "p1", "ziel", "Ziel p1")
        o("projekt_loeschen", "p1")
        o.sync()
        vorher = o("db_sha")
        o = self.neu_starten(o, CODE)
        nach_start = o("db_sha")
        self.assertEqual(nach_start["sha"], vorher["sha"])
        self.assertEqual(nach_start["nebendateien"], [])
        o("projekt_feld", "p2", "titel", "Titel p2")
        nach_speichern = self.texte(o)
        o.sync()
        x = self.voll("X", code=self.code("alt"))
        x.sync()
        uploads, _ = self.ruhe([o, x])
        bericht("N16-M2: p1 nach Start/Speichern %s, nach Abgleich %s; Ruhe %d"
                % (nach_speichern, self.texte(o), uploads))
        self.assertEqual(nach_speichern, ["1", "Titel p1", "Ziel p1"])
        self.assertEqual(self.texte(o), ["1", "Titel p1", "Ziel p1"])
        self.assertEqual(uploads, 0)

    def test_e13_t_a_oeffnen_ohne_schreiben(self):
        """E13/T-a: Datenbank aus 0.63.1 mit 0.63.2 oeffnen - einmal ohne
        geloeschtes Projekt, einmal mit einem geloeschten Projekt, dessen
        Text SPAETER liegt (unter 0.63.1 mit vorgehender Uhr geschrieben):
        Datei byte-gleich, Abgleich-Fingerabdruck alt = neu. Erst das naechste
        Speichern raeumt den spaeteren Text weg."""
        for mit_geloeschtem in (False, True):
            with self.subTest(mit_geloeschtem=mit_geloeschtem):
                o = self.voll("O", code=self.code("alt"), ordner="e13_%s" % mit_geloeschtem)
                self.zeit(0)
                o("projekt_feld", "lebt", "titel", "Lebt")
                if mit_geloeschtem:
                    self.zeit(0, O=2 * HOUR)
                    o("projekt_feld", "p1", "ziel", SECRET + " Uhr vor")
                    self.zeit(0)
                    o("projekt_loeschen", "p1")
                vorher, fp_alt = o("db_sha"), o("export_sha")
                o = self.neu_starten(o, CODE)
                nachher, fp_neu = o("db_sha"), o("export_sha")
                bericht("N16-E13 (mit geloeschtem Projekt: %s): db %s -> %s, Fingerabdruck "
                        "%s -> %s" % (mit_geloeschtem, vorher["sha"][:16], nachher["sha"][:16],
                                      fp_alt["sha"][:16], fp_neu["sha"][:16]))
                self.assertEqual(nachher["sha"], vorher["sha"])
                self.assertEqual(nachher["groesse"], vorher["groesse"])
                self.assertEqual(nachher["nebendateien"], [])
                self.assertEqual(fp_neu, fp_alt)
                if mit_geloeschtem:
                    self.assertIn(SECRET + " Uhr vor", self.texte(o))
                    o("projekt_feld", "lebt", "ziel", "irgendein Speichern")
                    self.assertTrue(ohne_text(self.zeilen(o), "p1"), self.zeilen(o))
                self.assertEqual(o("projekte")["projekte"], ["lebt"])
                o.close()
                self.geraete.remove(o)

    def m3(self):
        o, n = self.voll("O", code=self.code("alt")), self.voll("N")
        self.zeit(0)
        o("projekt_feld", "p1", "titel", "Titel p1")
        for device in (o, n):
            device.sync()
        self.zeit(1)
        n("projekt_loeschen", "p1")
        n.sync()
        self.zeit(1.5)
        o("projekt_feld", "p1", "titel", SECRET + " offline")    # offline, nach dem Loeschen
        return o, n

    def test_m3_alt_bearbeitet_offline_nach_loeschen(self):
        o, n = self.m3()
        runden = []
        for _ in range(3):
            for device in (o, n):
                v = ta.commits()
                r = device.sync()
                runden.append((device.name, ta.commits() - v, r.get("received")))
        bericht("N16-M3: Runden %s; O %s; N %s" % (runden, self.texte(o), self.texte(n)))
        self.assertTrue(ohne_text(self.zeilen(n), "p1"), self.zeilen(n))
        self.assertEqual(n("projekte")["projekte"], [])
        self.assertEqual(o("projekte")["projekte"], [])

    def test_m4_alt_uhr_vor_neu_loescht(self):
        o, n = self.voll("O", code=self.code("alt")), self.voll("N")
        self.zeit(0)
        n("projekt_feld", "p1", "titel", "Titel p1")
        for device in (n, o):
            device.sync()
        self.zeit(0.5, O=2 * HOUR)
        o("projekt_feld", "p1", "titel", SECRET + " Uhr vor")
        o.sync()
        self.zeit(1)
        n.sync()
        n("projekt_loeschen", "p1")
        runden = []
        for _ in range(3):
            for device in (n, o):
                v = ta.commits()
                r = device.sync()
                runden.append((device.name, ta.commits() - v, r.get("received")))
        bericht("N16-M4: Runden %s; O %s; N %s" % (runden, self.texte(o), self.texte(n)))
        self.assertTrue(ohne_text(self.zeilen(n), "p1"), self.zeilen(n))

    def test_m5_hin_und_her_endet_mit_dem_update(self):
        o, n = self.m3()
        self.alle_sync([o, n], 2)
        o = self.neu_starten(o, CODE)
        o.sync()
        n.sync()
        uploads, meldungen = self.ruhe([o, n])
        bericht("N16-M5: nach Update O %s, N %s; Ruhe %d"
                % (self.texte(o), self.texte(n), uploads))
        for device in (o, n):
            self.assertTrue(ohne_text(self.zeilen(device), "p1"), self.zeilen(device))
        self.assertEqual(uploads, 0, meldungen)

    def test_m6_f3_pflichtfall_nicos_geraet_neues_geraet_offline_geraet(self):
        """F3: O = Nicos Geraet v0.63.1, N = neues Geraet 0.63.2, danach
        Offline-Geraet P (0.63.2) mit Uhr +2 h schreibt p1, N loescht p1."""
        o, n = self.voll("O", code=self.code("alt")), self.voll("N")
        p = self.voll("P")
        self.zeit(0)
        o("projekt_feld", "p1", "titel", "Titel p1")
        for device in (o, n, p):
            device.sync()
        self.zeit(0.5, P=2 * HOUR)
        p("projekt_feld", "p1", "ziel", SECRET + " P")
        self.zeit(1)
        n("projekt_loeschen", "p1")
        self.zeit(2)
        for _ in range(2):
            for device in (n, o, p):
                device.sync()
        self.pruefe_ende("N16-M6", [n, p], [o], [o, n, p])

    # ------------------------------------------- 5.4 drei Geraete (4)
    def drei(self, folge_namen):
        ordner = "m54_" + folge_namen
        a = self.voll("A", ordner=ordner)
        b = self.voll("B", ordner=ordner)
        c = self.voll("C", code=self.code("alt"), ordner=ordner)
        self.zeit(0)
        a("projekt_feld", "p1", "titel", "Titel p1")
        for device in (a, b, c):
            device.sync()
        self.zeit(0.5, B=2 * HOUR)
        b("projekt_feld", "p1", "ziel", SECRET + " B")
        self.zeit(1)
        a("projekt_loeschen", "p1")
        self.zeit(1.5)
        c("projekt_feld", "p1", "zusatz", SECRET + " C offline")
        self.zeit(2)
        geraete = {"A": a, "B": b, "C": c}
        folge = [geraete[x] for x in folge_namen]
        for _ in range(2):
            for device in folge:
                device.sync()
        self.pruefe_ende(ordner, [a, b], [c], folge)
        for device in (a, b, c):
            device.close()
            self.geraete.remove(device)

    def test_5_4_drei_geraete(self):
        for folge in ("ABC", "ACB", "CAB", "BCA"):
            with self.subTest(folge=folge):
                ta.server_reset()
                self.drei(folge)

    # ------------------------------------------------ 5.5 Feldarten (3)
    def feldart(self, ordner, feld, wert, versatz_b, b_kennt_feld_vorher):
        a, b = self.voll("A", ordner=ordner), self.voll("B", ordner=ordner)
        self.zeit(0)
        a("projekt_feld", "p1", "titel", "Titel p1")
        a.sync()
        b.sync()
        self.zeit(0.5, B=versatz_b)
        b("projekt_feld", "p1", feld, wert)      # offline: A kennt das Feld beim Loeschen nicht
        if b_kennt_feld_vorher:
            b.sync()
            a.sync()
        self.zeit(1)
        a("projekt_loeschen", "p1")
        self.zeit(2)
        for _ in range(2):
            for device in (a, b):
                device.sync()
        return a, b

    def test_f_a_seitenziel_spaeter(self):
        a, b = self.feldart("f_a", fpj.PAGES_FIELD, "15", 2 * HOUR, False)
        self.pruefe_ende("N16-F-a", [a, b], [], [a, b])

    def test_f_b_unbekanntes_feld_spaeter(self):
        a, b = self.feldart("f_b", "zusatz", SECRET + " zusatz", 2 * HOUR, False)
        self.pruefe_ende("N16-F-b", [a, b], [], [a, b])

    def test_f_c_unbekanntes_feld_frueher_bekannte_grenze(self):
        """Bekannte Grenze von (ii') (Weisung zu Meldung 40, B1): ein beim
        Loeschen unbekanntes Feld, FRUEHER geschrieben (Uhr -2 h, offline),
        bleibt verborgen gespeichert - keine leere Fassung (delete_project
        kannte es nicht), nicht spaeter als die Loeschung. Kein Versprechen:
        haelt das heutige Verhalten fest; das Projekt bleibt ausgeblendet."""
        a, b = self.feldart("f_c", "zusatz", SECRET + " frueher", -2 * HOUR, False)
        stand = {d.name: self.texte(d) for d in (a, b)}
        uploads, _ = self.ruhe([a, b])
        bericht("N16-F-c (bekannte Grenze): Texte %s; Ruhe %d"
                % (json.dumps(stand, ensure_ascii=False), uploads))
        for device in (a, b):
            self.assertIn(SECRET + " frueher", self.texte(device))
            self.assertEqual(device("projekte")["projekte"], [])
        self.assertEqual(uploads, 0)


# ============================================================================
#  Rueckfrage (Testplan 5.6, R4; R1-R3 in test_projekt_loeschen.py)
# ============================================================================

class N16Rueckfrage(unittest.TestCase):

    def test_r4_einstellung_nicht_lesbar_fassung_mit_abgleich(self):
        from unittest import mock
        with mock.patch.object(fisi_sync, "is_configured", side_effect=OSError("kaputt")):
            text = fpj.delete_question({"titel": "Netzplan"})
        self.assertEqual(text, fpj.DELETE_QUESTION_SYNC % "Netzplan")


if __name__ == "__main__":
    if os.name == "nt":
        print("test_n16_0632.py braucht Zeitzonen je Prozess (TZ) - nur Linux/macOS.")
        sys.exit(0)
    print("Code: %s" % CODE)
    try:
        unittest.main(verbosity=2)
    finally:
        ta.SERVER.shutdown()
        shutil.rmtree(ta.WORK, ignore_errors=True)
