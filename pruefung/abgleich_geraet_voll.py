#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ein "Geraet" mit vollem Lernstand fuer test_abgleich_0632.py (ab 0.63.2).

Baut auf pruefung/abgleich_geraet.py auf (gleicher Aufruf, gleiche Befehle,
gleiche Behelfe: Attrappe statt GitHub, verstellbare Uhr) und ergaenzt
Befehle, die alle abgeglichenen Tabellen fuellen und den Lernstand
vergleichbar machen. Damit laesst sich "altes Geraet (v0.63.1) neben neuem
Geraet (0.63.2)" mit echtem Inhalt nachstellen - auch fuer S6b (B-G-08).
Laeuft mit dem Code eines anderen Stands (z.B. v0.63.1 aus git archive);
die Befehle nutzen nur Funktionen, die es dort schon gibt.

Aufruf:  python -I -B abgleich_geraet_voll.py <code-ordner> <api-url> <name>
Zusaetzliche Befehle (je Zeile ein JSON-Befehl, wie abgleich_geraet.py):
  fuelle ETIKETT         je Tabelle ein Eintrag (Karten, Quiz, AP1/AP2,
                         Testprojekte, Trainer, Klausur, Test, Projektfeld,
                         Spielereignis, Spielplatz, Bestenliste)
  bestenliste ETIKETT    ein Bestenliste-Eintrag
  bestenliste_neu ETIKETT  "Bestenliste loeschen" und sofort danach (am
                         Anfang einer Sekunde, also in derselben Sekunde)
                         ein Eintrag - wie das Spiel nach dem Loeschen (B-G-17)
  projekt_loeschen NAME  fisi_projekt.delete_project
  projekt_feld ID FELD WERT  db.save_project_field (ab 0.63.2, N16)
  projekt_zeilen         Rohzeilen des Abschlussprojekts [uid, timestamp,
                         projekt, feld, wert], sortiert (ab 0.63.2, N16)
  projekte               sichtbare Projekte (fisi_projekt.projects), sortiert
  inhalt                 Lernstand ohne id (je Tabelle sortierte Zeilen mit
                         uid) und die Loeschmarken - zum Vergleich der Geraete
  export_sha             sha256 des kanonischen JSON von export_local
  db_sha                 sha256 und Groesse der Datenbankdatei, dazu ob
                         -wal/-journal liegen
  schluessel             Zahl der Eintraege je Tabelle
Ab 0.63.2 (S6b, Weisung zu Meldung 37: Spielstaende/Projekte beim Ersetzen,
Vorlage gp_meldung_37 skripte/geraet_m37.py):
  spiel_anlegen PLATZ LAUF N  Spielplatz PLATZ mit Durchgang LAUF und N
                         Spielereignissen
  spiel_loeschen PLATZ LAUF   db.delete_run - wie "Spielstand zuruecksetzen"
                         (Game.reset) und Platz loeschen in der Oberflaeche
  spielzahl              {lauf: Zahl der Spielereignisse}
  projekt_anlegen ID     Projekt ID mit Titel (save_project_field)
  projekte               sichtbare Projekt-IDs (fisi_projekt.projects)
  bestenzahl             Schluessel der Bestenliste-Eintraege
"""

import sys
sys.dont_write_bytecode = True

import hashlib  # noqa: E402
import json  # noqa: E402
import os  # noqa: E402
import time  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import abgleich_geraet as g  # noqa: E402  (laedt fisi_core usw. aus <code-ordner>)

import fisi_projekt  # noqa: E402

db = g.db
_basis = g.run


def _sekundenanfang():
    """Wartet, bis eine neue Sekunde gerade begonnen hat (< 0,1 s alt)."""
    while True:
        rest = time.time() % 1.0
        if rest < 0.05:
            return
        time.sleep(1.0 - rest + 0.001)


def fuelle(tag):
    name = "%s-%s" % (g.TAG, tag)
    db.log_card("Kat", name + "-karte", "karte", 1)
    db.log_quiz_answer("Kat", name + "-quiz", 0)
    db.log_scenario(1, name + "-ap2", "Netz", True)
    db.log_project(2, name + "-projekt", "Kat", None)
    db.log_ap1(3, name + "-ap1", "Wiso", False)
    db.log_trainer("subnetz-" + name, 2, 1)
    db.save_exam("ap2", 61.5, "3", 1200, json.dumps({"etikett": name}))
    db.save_test_result(8, 10, 80.0, "2", 300 + sum(map(ord, name)))
    db.save_project_field("Projekt " + name, "thema", "Thema " + name)
    db.log_game_event("ticket", json.dumps({"etikett": name}), g.NAME, "lauf-" + name)
    db.log_slot(1, "lauf-" + name, "angelegt", json.dumps({"name": name}), g.NAME)
    db.log_record("lauf-" + name, "rekord", name, 42.0, "{}")


def inhalt():
    conn = g._conn()
    try:
        tabellen = {}
        for table, columns in g.fisi_core.SYNC_TABLES.items():
            rows = conn.execute("SELECT uid, %s FROM %s" % (", ".join(columns), table)).fetchall()
            tabellen[table] = sorted(json.dumps(list(row), ensure_ascii=False) for row in rows)
        meta = dict(conn.execute("SELECT key, value FROM sync_meta"))
    finally:
        conn.close()
    marken = {k: v for k, v in meta.items() if k in g.fisi_sync.MARKERS and v}
    return {"tabellen": tabellen, "marken": marken}


def run(name, *args):
    if name == "fuelle":
        fuelle(args[0])
        return {"ok": True}
    if name == "bestenliste":
        ok = db.log_record("lauf-%s-%s" % (g.TAG, args[0]), "rekord",
                           "%s-%s" % (g.TAG, args[0]), 7.0, "{}")
        return {"ok": bool(ok)}
    if name == "bestenliste_neu":
        _sekundenanfang()
        ok = db.reset_records()
        db.log_record("lauf-%s-%s" % (g.TAG, args[0]), "rekord",
                      "%s-%s" % (g.TAG, args[0]), 9.0, "{}")
        conn = g._conn()
        try:
            marke = conn.execute("SELECT value FROM sync_meta WHERE key = "
                                 "'bestenliste_reset_at'").fetchone()[0]
            zeile = conn.execute("SELECT timestamp FROM spiel_bestenliste").fetchall()
        finally:
            conn.close()
        return {"ok": ok, "marke": marke, "eintraege": [row[0] for row in zeile]}
    if name == "spiel_anlegen":
        slot, lauf, n = int(args[0]), args[1], int(args[2])
        db.log_slot(slot, lauf, "angelegt", json.dumps({"name": lauf}), g.NAME)
        for i in range(n):
            db.log_game_event("ticket", json.dumps({"i": i}), g.NAME, lauf)
        return {"ok": True}
    if name == "spiel_loeschen":
        return {"ok": bool(db.delete_run(int(args[0]), args[1], g.NAME))}
    if name == "spielzahl":
        conn = g._conn()
        try:
            rows = conn.execute("SELECT lauf, COUNT(*) FROM spiel_ereignisse GROUP BY 1").fetchall()
        finally:
            conn.close()
        return {"spiel": {str(row[0]): row[1] for row in rows}}
    if name == "projekt_anlegen":
        db.save_project_field(args[0], "titel", "Titel " + args[0])
        return {"ok": True}
    if name == "projekte":
        return {"projekte": sorted(fisi_projekt.projects(db))}
    if name == "bestenzahl":
        conn = g._conn()
        try:
            rows = conn.execute("SELECT schluessel FROM spiel_bestenliste").fetchall()
        finally:
            conn.close()
        return {"besten": sorted(row[0] for row in rows)}
    if name == "projekt_loeschen":
        fisi_projekt.delete_project(db, args[0])
        return {"ok": True}
    if name == "projekt_feld":
        return {"ok": bool(db.save_project_field(args[0], args[1], args[2]))}
    if name == "projekt_zeilen":
        conn = g._conn()
        try:
            rows = conn.execute("SELECT uid, timestamp, projekt, feld, wert"
                                " FROM abschlussprojekt").fetchall()
        finally:
            conn.close()
        return {"zeilen": sorted([list(row) for row in rows], key=json.dumps)}
    if name == "projekte":
        return {"projekte": sorted(fisi_projekt.projects(db))}
    if name == "inhalt":
        return inhalt()
    if name == "export_sha":
        data = g.fisi_sync.export_local(db)
        canon = json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        return {"sha": hashlib.sha256(canon.encode("utf-8")).hexdigest(),
                "zeilen": sum(len(rows) for rows in data["tables"].values())}
    if name == "db_sha":
        with open(db.db_path, "rb") as handle:
            raw = handle.read()
        return {"sha": hashlib.sha256(raw).hexdigest(), "groesse": len(raw),
                "nebendateien": [s for s in ("-wal", "-journal", "-shm")
                                 if os.path.exists(db.db_path + s)]}
    if name == "schluessel":
        conn = g._conn()
        try:
            return {"anzahl": {t: conn.execute("SELECT COUNT(*) FROM %s" % t).fetchone()[0]
                               for t in g.fisi_core.SYNC_TABLES}}
        finally:
            conn.close()
    return _basis(name, *args)


g.run = run

if __name__ == "__main__":
    g.main()
