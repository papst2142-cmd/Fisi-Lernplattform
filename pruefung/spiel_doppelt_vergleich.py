#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Vorher/Nachher-Pruefung fuer B-G-26 (Gruppe 5.5, 0.62.5): rechnet alle
Spielstaende aus Teil 4 der Pruefung 0.62.4 mit dem ALTEN und dem NEUEN
Code und vergleicht die Spielzahlen. Nach der Aenderung muss dieses Werkzeug
nur noch laufen.

Was verglichen wird (Auflage P-14):
  1. Gespeicherte Staende (Datenbank-Abzuege als JSON) aus Teil 4, z.B.
     belege/g1/vorher_v0.30.json ... vorher_v0.62.json: jeder Durchgang
     (lauf) wird mit beiden Codes als GameState berechnet. Dabei wird
     gezaehlt: Feierabende gesamt, Feierabende OHNE Tagesangabe (werden nie
     geraten oder uebersprungen), eindeutige Doppel (gleiche Art + Tag).
  2. Fall D5 (Teil 4, g4_geraet spieltag) als Ereignisliste: hier ist ein
     Unterschied ERWARTET (alt 3 Tage/450, neu 2 Tage/300).
  3. Laeufe F1 (f1_simulation.py) je einmal mit altem und neuem Code. Die
     Laeufe sind NICHT wiederholbar (gemessen: gleicher Code zweimal ->
     anderes Geld). Deshalb: jeder Lauf muss in sich sauber sein (keine
     Ausnahme, Neuaufbau gleich, Handy-Abgleich gleich), und die gesicherten
     Datenbanken BEIDER Laeufe werden mit beiden Codes nachgerechnet - dort
     muss jede Spielzahl gleich sein.
  4. 30-Tage-Lauf: f1_simulation.py --tage 30 je Variante (einfach, normal,
     alt), wie 3.
  5. Lauf F2 (f2_durchlauf.py) mit beiden Codes: jeder Lauf 0 Fehler und
     jeder Vergleich "gleich" (Lauf gegen Lauf nur zur Info, wie 3).
  6. Alter Fingerabdruck (spiel/bericht_0.54/werkzeuge/fingerabdruck.py) mit
     beiden Codes, Soll f2b59ce8...6656.
Ab 0.63.2 (E-5) wird je Stand auch der Rueckblick verglichen (journey,
journey_stats, run_metrics): ohne Doppel muss er gleich sein, in D5 ist der
Unterschied erwartet.
Jeder Unterschied ausser in 2. ist ein Befund ("ABWEICHUNG").

Aufruf (Python 3.12):
  /home/claude/venv/bin/python -I pruefung/spiel_doppelt_vergleich.py \\
      --alt <Basis OHNE Aenderung> --neu <dieselbe Basis MIT Aenderung> \\
      --arbeit <leerer Wegwerf-Ordner> [--stufe schnell|voll] [--nur 1,2,3,4,5,6]
  schnell: F1 je Variante Startwert 0, 120 Tage, --sparsam 2; F2 mit 40
           Firmentagen (zusammen grob 10-20 min fuer beide Codes)
  voll:    F1 wie in Teil 4 (einfach 0-7, normal 0-7, alt 0-5, 400 Tage,
           --sparsam 2, gesichert an Tag 120/250/400) und F2 vollstaendig
           (mehrere Stunden; vorher Zeitfenster klaeren)
Ausgabe: <arbeit>/vergleich.txt und <arbeit>/vergleich.json; Rueckgabe 0 nur,
wenn alles gleich ist (ausser den erwarteten D5-Unterschieden).

Nur Wegwerf-Daten: jede Rechnung in eigenem Prozess mit eigenem HOME und
FISI_DB_PATH unter <arbeit>. Die Code-Ordner und Teil-4-Dateien werden nur
gelesen. Echte Nutzerdaten werden nie gelesen (A-8).
"""

import argparse
import glob
import json
import os
import re
import sqlite3
import subprocess
import sys
import tempfile

PY = "/home/claude/venv/bin/python"
TEIL4 = "/mnt/project-files/pruefung_0.62.4/teil4_F_G"
FP_ORDNER = "/mnt/project-files/spiel/bericht_0.54/werkzeuge"
FP_SOLL = "f2b59ce8f78a533cc3ec565ab983d418959e788d8ff16d35a907de328a626656"
EV_DAY_END = "tag_beendet"
EV_SOLVED = "ticket_erledigt"
# Hilfsattribut der Aenderung (Merker fuer schon gezaehlte Ereignisse) -
# gehoert nicht zu den Spielzahlen
IGNORIERT = ("content", "history", "_counted_once")


# ----------------------------------------------------------------------------
#  Rechen-Prozess: GameState mit einem Code-Ordner berechnen
# ----------------------------------------------------------------------------

def _plain(value):
    if isinstance(value, dict):
        return {str(key): _plain(item) for key, item in sorted(
            value.items(), key=lambda pair: repr(pair[0]))}
    if isinstance(value, (set, frozenset)):
        return sorted((_plain(item) for item in value), key=repr)
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    if isinstance(value, float):
        return round(value, 9)
    if value is None or isinstance(value, (int, str, bool)):
        return value
    return repr(value)


def _rueckblick(fg, state):
    """Ab 0.63.2 (E-5): Rueckblick (Meine Reise) - Tagebuch, Statistik und
    Kennzahlen. Mit Weg A rechnen sie ohne Doppel; bei Staenden ohne Doppel
    muessen sie alt und neu gleich sein."""
    out = {}
    for name in ("journey", "journey_stats", "run_metrics"):
        try:
            out[name] = _plain(getattr(fg, name)(state))
        except Exception as exc:  # noqa: BLE001 - wird verglichen und gemeldet
            out[name] = "%s: %s" % (type(exc).__name__, exc)
    return out


def rechne(code, eingabe, ausgabe):
    """Kindprozess: Ereignislisten aus eingabe (JSON: {name: [[ts, typ,
    daten], ...]}) mit dem Code in code berechnen, Ergebnis nach ausgabe."""
    sys.path.insert(0, code)
    import fisi_game as fg
    assert os.path.dirname(os.path.abspath(fg.__file__)) == os.path.abspath(code)
    with open(eingabe, encoding="utf-8") as handle:
        staende = json.load(handle)
    result = {}
    for name, events in staende.items():
        try:
            state = fg.GameState([tuple(item) for item in events])
            werte = {key: value for key, value in vars(state).items()
                     if key not in IGNORIERT}
            result[name] = {"kern": {"tage": state.days_done, "tag": state.day,
                                     "geld": state.money, "tickets": state.tickets_done,
                                     "firma": bool(state.firm)},
                            "alle": _plain(werte),
                            "rueckblick": _rueckblick(fg, state)}
        except Exception as exc:  # noqa: BLE001 - wird verglichen und gemeldet
            result[name] = {"fehler": "%s: %s" % (type(exc).__name__, exc)}
    with open(ausgabe, "w", encoding="utf-8") as handle:
        json.dump(result, handle, ensure_ascii=False, sort_keys=True)


# ----------------------------------------------------------------------------
#  Hilfen fuer den Hauptprozess
# ----------------------------------------------------------------------------

def _umgebung(arbeit, name):
    home = tempfile.mkdtemp(prefix="home_%s_" % name, dir=arbeit)
    env = dict(os.environ)
    env.update({"HOME": home, "FISI_DB_PATH": os.path.join(home, "nie_benutzt.db"),
                "FISI_SELFTEST": os.path.join(home, "selftest.txt"),
                "PYTHONDONTWRITEBYTECODE": "1", "TMPDIR": home})
    return env


def _rechne_mit(code, staende, arbeit, name):
    eingabe = os.path.join(arbeit, "staende_%s.json" % name)
    ausgabe = os.path.join(arbeit, "ergebnis_%s.json" % name)
    with open(eingabe, "w", encoding="utf-8") as handle:
        json.dump(staende, handle, ensure_ascii=False)
    subprocess.run([PY, "-I", "-B", os.path.abspath(__file__), "--rechne", code, eingabe,
                    ausgabe], check=True, env=_umgebung(arbeit, name), timeout=3600)
    with open(ausgabe, encoding="utf-8") as handle:
        return json.load(handle)


def _tag_gueltig(value):
    return type(value) is int and value > 0


def zaehle(events):
    """Feierabende/Tickets mit und ohne Tagesangabe, eindeutige Doppel."""
    out = {"feierabende": 0, "feierabende_ohne_tag": 0, "feierabend_doppel": 0,
           "tickets": 0, "tickets_ohne_tag": 0, "ticket_doppel": 0}
    seen = set()
    for _ts, kind, data in events:
        if kind == EV_DAY_END:
            out["feierabende"] += 1
            if not _tag_gueltig(data.get("tag")):
                out["feierabende_ohne_tag"] += 1
            elif (kind, data["tag"]) in seen:
                out["feierabend_doppel"] += 1
            else:
                seen.add((kind, data["tag"]))
        elif kind == EV_SOLVED:
            out["tickets"] += 1
            key = (kind, data.get("aufgabe"), data.get("tag"))
            if not _tag_gueltig(data.get("tag")):
                out["tickets_ohne_tag"] += 1
            elif isinstance(key[1], str) and key[1]:
                if key in seen:
                    out["ticket_doppel"] += 1
                else:
                    seen.add(key)
    return out


def _zeilen_zu_staenden(name, spalten, zeilen):
    """Tabelle spiel_ereignisse -> {name#lauf: [(ts, typ, daten)]}, sortiert
    wie DBManager.game_events (timestamp, id)."""
    index = {col: pos for pos, col in enumerate(spalten)}
    gruppen = {}
    for row in zeilen:
        lauf = row[index["lauf"]] if "lauf" in index else None
        gruppen.setdefault(lauf or "", []).append(row)
    staende = {}
    for lauf, rows in sorted(gruppen.items()):
        rows.sort(key=lambda r: (str(r[index["timestamp"]]), r[index["id"]]))
        events = []
        for row in rows:
            try:
                data = json.loads(row[index["daten"]]) if row[index["daten"]] else {}
            except ValueError:
                continue
            if isinstance(data, dict):
                events.append([row[index["timestamp"]], row[index["typ"]], data])
        staende["%s#%s" % (name, lauf or "ohne_lauf")] = events
    return staende


def staende_aus_abzuegen(teil4):
    """Alle JSON-Abzuege unter teil4/belege mit einer Tabelle spiel_ereignisse."""
    staende = {}
    for path in sorted(glob.glob(os.path.join(teil4, "belege", "**", "*"), recursive=True)):
        if not os.path.isfile(path) or os.path.getsize(path) > 50 * 1024 * 1024:
            continue
        try:
            with open(path, encoding="utf-8") as handle:
                data = json.load(handle)
        except (ValueError, UnicodeDecodeError):
            continue
        tabelle = data.get("tabellen", {}).get("spiel_ereignisse") \
            if isinstance(data, dict) and isinstance(data.get("tabellen"), dict) else None
        if not tabelle or not tabelle.get("zeilen"):
            continue
        name = os.path.relpath(path, teil4)
        staende.update(_zeilen_zu_staenden(name, tabelle["spalten"], tabelle["zeilen"]))
    return staende


def staende_aus_db(path, name):
    conn = sqlite3.connect("file:%s?mode=ro" % path, uri=True)
    try:
        spalten = [row[1] for row in conn.execute("PRAGMA table_info(spiel_ereignisse)")]
        zeilen = conn.execute("SELECT %s FROM spiel_ereignisse" % ", ".join(spalten)).fetchall()
    finally:
        conn.close()
    return _zeilen_zu_staenden(name, spalten, zeilen)


def d5_staende():
    """Fall D5 wie g4_geraet.py (spieltag:l2:1, dann Tag 2 auf PC und Handy)."""
    def tag(day):
        return [[EV_SOLVED, {"aufgabe": "g4-ticket-%d" % day, "geld": 50, "richtig": True,
                             "tag": day}],
                [EV_DAY_END, {"tag": day, "gehalt": 100, "miete": 0}]]
    block = tag(1) + tag(2) + tag(2)
    verzahnt = tag(1) + [tag(2)[0], tag(2)[0], tag(2)[1], tag(2)[1]]
    out = {}
    for name, items in (("D5_block", block), ("D5_verzahnt", verzahnt)):
        out[name] = [["2026-10-01 08:00:%02d" % i] + item for i, item in enumerate(items)]
    return out


def vergleiche(staende, alt, neu, erwartet=None):
    """Liefert je Stand: Zaehlung, Kernwerte alt/neu, gleich ja/nein."""
    erwartet = erwartet or {}
    zeilen = []
    for name in sorted(staende):
        a, n = alt.get(name, {}), neu.get(name, {})
        gleich = a == n
        eintrag = {"stand": name, "ereignisse": len(staende[name]),
                   "zaehlung": zaehle(staende[name]),
                   "alt": a.get("kern", a.get("fehler")), "neu": n.get("kern", n.get("fehler")),
                   "gleich": gleich}
        if not gleich and "alle" in a and "alle" in n:
            eintrag["unterschiede"] = sorted(key for key in set(a["alle"]) | set(n["alle"])
                                             if a["alle"].get(key) != n["alle"].get(key))[:40]
            # ab 0.63.2 (E-5): auch Unterschiede im Rueckblick nennen
            eintrag["unterschiede"] += sorted(
                "rueckblick." + key for key in set(a.get("rueckblick", {})) |
                set(n.get("rueckblick", {}))
                if a.get("rueckblick", {}).get(key) != n.get("rueckblick", {}).get(key))
        if name in erwartet:
            eintrag["erwartet"] = erwartet[name]
            eintrag["ok"] = (eintrag["alt"] and eintrag["neu"] and
                             [eintrag["alt"]["tage"], eintrag["alt"]["geld"]] ==
                             erwartet[name]["alt"] and
                             [eintrag["neu"]["tage"], eintrag["neu"]["geld"]] ==
                             erwartet[name]["neu"])
        else:
            eintrag["ok"] = gleich
        zeilen.append(eintrag)
    return zeilen


ZEIT_MUSTER = [(re.compile(r"\b\d+(\.\d+)? ?(s|ms)\b"), "<zeit>"),
               (re.compile(r"\bl[0-9a-f]{16}\b"), "<lauf>"),
               (re.compile(r"Laufzeit .*"), "Laufzeit <zeit>")]


def _maskiert(text):
    for muster, ersatz in ZEIT_MUSTER:
        text = muster.sub(ersatz, text)
    return text


def f1_laeufe(code, name, arbeit, laeufe, tage, sparsam, sichern_tage):
    """f1_simulation.py mit einem Code; liefert (ergebnisse ohne Zeiten, dbs)."""
    out_dir = os.path.join(arbeit, "f1_%s" % name)
    os.makedirs(out_dir, exist_ok=True)
    dbs = os.path.join(out_dir, "db")
    for variante, startwert in laeufe:
        cmd = ["timeout", "5400", "nice", "-n", "15", PY, "-I", "-B",
               os.path.join(TEIL4, "werkzeuge", "f1_simulation.py"), code,
               os.path.join(out_dir, "f1_%s.jsonl" % variante), "--variante", variante,
               "--startwerte", str(startwert), "--tage", str(tage)]
        if sparsam:
            cmd += ["--sparsam", str(sparsam)]
        if sichern_tage:
            cmd += ["--sichern", dbs, "--sichern-tage", sichern_tage]
        with open(os.path.join(out_dir, "f1.log"), "a", encoding="utf-8") as log:
            log.write("$ %s\n" % " ".join(cmd))
            log.flush()
            rc = subprocess.run(cmd, env=_umgebung(arbeit, "f1_" + name), stdout=log,
                                stderr=subprocess.STDOUT).returncode
            log.write("exit %d\n" % rc)
    ergebnisse = {}
    for path in sorted(glob.glob(os.path.join(out_dir, "f1_*.jsonl"))):
        with open(path, encoding="utf-8") as handle:
            for line in handle:
                item = json.loads(line)
                for key in ("zeiten", "rss", "laufzeit_s"):
                    item.pop(key, None)
                ergebnisse["%s_%s" % (item.get("variante"), item.get("startwert"))] = item
    return ergebnisse, sorted(glob.glob(os.path.join(dbs, "*.db")))


def f2_lauf(code, name, arbeit, firmentage):
    cmd = ["timeout", "7200", "nice", "-n", "15", PY, "-I", "-B",
           os.path.join(TEIL4, "werkzeuge", "f2_durchlauf.py"), code]
    if firmentage:
        cmd.append(str(firmentage))
    res = subprocess.run(cmd, env=_umgebung(arbeit, "f2_" + name), capture_output=True,
                         text=True)
    with open(os.path.join(arbeit, "f2_%s.txt" % name), "w", encoding="utf-8") as handle:
        handle.write(res.stdout + "\n--- stderr ---\n" + res.stderr + "\nexit %d\n"
                     % res.returncode)
    return res.returncode, _maskiert(res.stdout)


def fingerabdruck(code, arbeit, name):
    env = _umgebung(arbeit, "fp_" + name)
    res = subprocess.run(["python3", "mit_home.py", "fingerabdruck.py", code], cwd=FP_ORDNER,
                         env=env, capture_output=True, text=True, timeout=3600)
    werte = re.findall(r"\b[0-9a-f]{64}\b", res.stdout)
    with open(os.path.join(arbeit, "fingerabdruck_%s.txt" % name), "w",
              encoding="utf-8") as handle:
        handle.write(res.stdout + "\n--- stderr ---\n" + res.stderr)
    return werte[-1] if werte else None


# ----------------------------------------------------------------------------
#  Hauptablauf
# ----------------------------------------------------------------------------

def main():
    if len(sys.argv) == 5 and sys.argv[1] == "--rechne":
        rechne(*sys.argv[2:])
        return 0
    ap = argparse.ArgumentParser()
    ap.add_argument("--alt", required=True)
    ap.add_argument("--neu", required=True)
    ap.add_argument("--arbeit", required=True)
    ap.add_argument("--stufe", choices=("schnell", "voll"), default="schnell")
    ap.add_argument("--nur", default="1,2,3,4,5,6")
    ap.add_argument("--teil4", default=TEIL4)
    # Ab 0.63.2 (E-5): Mit alt = 0.63.1 (B-G-26 schon drin) sind die
    # Kopfzahlen von D5 alt und neu gleich (2 Tage, 300); verschieden ist dann
    # nur der Rueckblick (erwartet). Aufruf dafuer mit --d5-alt 2,300.
    ap.add_argument("--d5-alt", default="3,450")
    args = ap.parse_args()
    alt, neu = os.path.abspath(args.alt), os.path.abspath(args.neu)
    arbeit = os.path.abspath(args.arbeit)
    os.makedirs(arbeit, exist_ok=True)
    teile = set(args.nur.split(","))
    bericht = {"alt": alt, "neu": neu, "stufe": args.stufe, "teile": {}}
    zeilen_txt = ["Vorher/Nachher B-G-26  alt=%s  neu=%s  stufe=%s" % (alt, neu, args.stufe)]
    # alt und neu duerfen sich NUR in fisi_game.py unterscheiden (sonst wirken
    # z.B. 0.62.4-Aenderungen in fisi_core.py mit - erster Lauf gegen v0.62.3)
    basis_diff = []
    for path in sorted(glob.glob(os.path.join(alt, "**", "*.py"), recursive=True) +
                       glob.glob(os.path.join(alt, "inhalte", "**", "*.json"), recursive=True)):
        rel = os.path.relpath(path, alt)
        other = os.path.join(neu, rel)
        if rel == "fisi_game.py":
            continue
        with open(path, "rb") as h_a:
            mine = h_a.read()
        same = False
        if os.path.exists(other):
            with open(other, "rb") as h_n:
                same = h_n.read() == mine
        if not same:
            basis_diff.append(rel)
    bericht["basis_unterschiede"] = basis_diff
    zeilen_txt.append("Dateien ausser fisi_game.py verschieden: %s" % (
        basis_diff[:20] or "keine (gleiche Basis)"))
    if basis_diff:
        zeilen_txt.append("WARNUNG: alt und neu haben verschiedene Basis - das ist keine "
                          "Pruefung nur von B-G-26")
    alles_ok = not basis_diff

    def melde(teil, eintraege):
        nonlocal alles_ok
        bericht["teile"][teil] = eintraege
        zeilen_txt.append("")
        zeilen_txt.append("== %s" % teil)
        for item in eintraege:
            alles_ok = alles_ok and item.get("ok", False)
            zeilen_txt.append("%-12s %s  alt=%s  neu=%s  %s" % (
                "ok" if item.get("ok") else "ABWEICHUNG", item.get("stand"),
                item.get("alt"), item.get("neu"),
                json.dumps(item.get("zaehlung", item.get("info", "")), sort_keys=True)))
            if item.get("unterschiede"):
                zeilen_txt.append("             unterschiedlich: %s" % item["unterschiede"])

    if "1" in teile:
        staende = staende_aus_abzuegen(args.teil4)
        melde("1 gespeicherte Staende (Abzuege Teil 4)", vergleiche(
            staende, _rechne_mit(alt, staende, arbeit, "abzug_alt"),
            _rechne_mit(neu, staende, arbeit, "abzug_neu")))
    if "2" in teile:
        staende = d5_staende()
        d5_alt = [int(part) for part in args.d5_alt.split(",")]
        erwartet = {name: {"alt": d5_alt, "neu": [2, 300]} for name in staende}
        melde("2 Fall D5 (Unterschied erwartet)", vergleiche(
            staende, _rechne_mit(alt, staende, arbeit, "d5_alt"),
            _rechne_mit(neu, staende, arbeit, "d5_neu"), erwartet))
    simulationen = []
    if "3" in teile:
        if args.stufe == "voll":
            laeufe = [("einfach", s) for s in range(8)] + [("normal", s) for s in range(8)] + \
                [("alt", s) for s in range(6)]
            simulationen.append(("3 Laeufe F1", laeufe, 400, 2, "120,250,400"))
        else:
            simulationen.append(("3 Laeufe F1", [("einfach", 0), ("normal", 0), ("alt", 0)],
                                 120, 2, "60,120"))
    if "4" in teile:
        simulationen.append(("4 30-Tage-Lauf", [("einfach", 1), ("normal", 1), ("alt", 1)],
                             30, 0, "30"))
    for teil, laeufe, tage, sparsam, sichern in simulationen:
        kurz = teil.split()[0]
        erg_alt, dbs_alt = f1_laeufe(alt, "alt_" + kurz, arbeit, laeufe, tage, sparsam, sichern)
        erg_neu, dbs_neu = f1_laeufe(neu, "neu_" + kurz, arbeit, laeufe, tage, sparsam, sichern)
        eintraege = []
        # Die F1-Laeufe sind NICHT wiederholbar (gemessen: gleicher Code, zwei
        # Laeufe, anderes Geld). Deshalb: jeder Lauf muss in sich fehlerfrei
        # sein (Ausnahmen, Neuaufbau, Handy-Abgleich), und die gesicherten
        # Datenbanken BEIDER Laeufe werden mit beiden Codes nachgerechnet -
        # dort muss alles gleich sein. Lauf alt gegen Lauf neu nur zur Info.
        for herkunft, ergebnisse in (("alt", erg_alt), ("neu", erg_neu)):
            for key in sorted(ergebnisse):
                item = ergebnisse[key]
                sauber = not item.get("fehler") and not item.get("abweichungen") and \
                    not item.get("stau") and item.get("handy_abgleich") == "gleich" and \
                    item.get("tage_gespielt") == tage
                eintraege.append({"stand": "Lauf %s mit Code %s" % (key, herkunft),
                                  "alt": item.get("tage_gespielt"), "neu": item.get("ende"),
                                  "ok": sauber,
                                  "info": {"fehler": len(item.get("fehler", [])),
                                           "abweichungen": len(item.get("abweichungen", [])),
                                           "verstoesse": len(item.get("verstoesse", [])),
                                           "handy_abgleich": item.get("handy_abgleich")}})
        staende = {}
        for herkunft, dbs in (("alt", dbs_alt), ("neu", dbs_neu)):
            for path in dbs:
                staende.update(staende_aus_db(path, "%s/%s" % (herkunft,
                                                              os.path.basename(path))))
        eintraege += vergleiche(staende, _rechne_mit(alt, staende, arbeit, kurz + "_db_alt"),
                                _rechne_mit(neu, staende, arbeit, kurz + "_db_neu"))
        erwartet_dbs = len(laeufe) * len(sichern.split(","))
        eintraege.append({"stand": "gesicherte DBs (soll je %d)" % erwartet_dbs,
                          "ok": len(dbs_alt) == len(dbs_neu) == erwartet_dbs,
                          "alt": len(dbs_alt), "neu": len(dbs_neu)})
        melde(teil, eintraege)
    if "5" in teile:
        firmentage = 0 if args.stufe == "voll" else 40
        rc_a, out_a = f2_lauf(alt, "alt", arbeit, firmentage)
        rc_n, out_n = f2_lauf(neu, "neu", arbeit, firmentage)
        # F2 ist wie F1 nicht wiederholbar: jeder Lauf muss in sich sauber sein
        # (0 Fehler, jeder Vergleich "gleich"); Unterschied der Laeufe nur Info
        eintraege = []
        for herkunft, rc, out in (("alt", rc_a, out_a), ("neu", rc_n, out_n)):
            checks = [line for line in out.splitlines() if "neu aufgebaut:" in line]
            sauber = rc == 0 and "FEHLER (Ausnahmen/Abweichungen): 0" in out and \
                bool(checks) and all(line.count(": gleich") == 3 for line in checks)
            eintraege.append({"stand": "f2_durchlauf (Firmentage %s) mit Code %s" % (
                firmentage or "alle", herkunft), "alt": "exit %d" % rc,
                "neu": "%d Vergleiche" % len(checks), "ok": sauber})
        eintraege.append({"stand": "F2 alt gegen neu (nur Info)", "ok": True,
                          "info": {"zeilen_verschieden": len(set(out_a.splitlines()) ^
                                                             set(out_n.splitlines()))}})
        melde("5 Lauf F2", eintraege)
    if "6" in teile:
        fp_a, fp_n = fingerabdruck(alt, arbeit, "alt"), fingerabdruck(neu, arbeit, "neu")
        melde("6 alter Fingerabdruck", [{"stand": "fingerabdruck.py", "alt": fp_a, "neu": fp_n,
                                         "ok": fp_a == fp_n == FP_SOLL,
                                         "info": {"soll": FP_SOLL}}])

    gesamt = {}
    for eintraege in bericht["teile"].values():
        for item in eintraege:
            for key, value in (item.get("zaehlung") or {}).items():
                gesamt[key] = gesamt.get(key, 0) + value
    bericht["summe_zaehlung"] = gesamt
    bericht["alles_ok"] = alles_ok
    zeilen_txt += ["", "Summe Zaehlung: %s" % json.dumps(gesamt, sort_keys=True),
                   "ERGEBNIS: %s" % ("alles gleich (D5 wie erwartet)" if alles_ok else
                                     "ABWEICHUNG - anhalten und melden")]
    with open(os.path.join(arbeit, "vergleich.json"), "w", encoding="utf-8") as handle:
        json.dump(bericht, handle, ensure_ascii=False, indent=1, sort_keys=True)
    with open(os.path.join(arbeit, "vergleich.txt"), "w", encoding="utf-8") as handle:
        handle.write("\n".join(zeilen_txt) + "\n")
    print("\n".join(zeilen_txt))
    return 0 if alles_ok else 1


if __name__ == "__main__":
    sys.exit(main())
