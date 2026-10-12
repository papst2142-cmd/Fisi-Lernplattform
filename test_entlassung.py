#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests fuer B-F-01 (ab 0.62.4, Plan 0.62.4 Abschnitt 3.4): Wer die Firma
verlaesst, verschwindet aus allen Projektteams und aus dem Serverfarm-Team.

Drei Wege aus der Firma:
  E  Entlassen (Game.fire, Ereignis mitarbeiter_gekuendigt)
  K  Selbst kuendigen (Stimmung 3 Feierabende unter "kritisch", nur "Normal")
  R  Rueckhol-Angebot eines Mitbewerbers, "Ziehen lassen"
Dazu: ein schon blockierter Spielstand (Protokoll mit dem Code aus dem Tag
v0.62.3 geschrieben) wird mit dem Code unter Test geladen, und "Team aendern"
mit einer Liste, die eine ausgeschiedene Kennung enthaelt.

Abkuerzungen (offen genannt):
  * Gruendung ueber Ereignisse "ticket_erledigt" mit mehr Startgeld (wie in
    test_spiel.py und den Pruefskripten).
  * Fall K: Die Stimmung wird mit fuenf Ereignissen "urlaub_abgelehnt"
    gesenkt. Die Kuendigung selbst kommt ueber den normalen Feierabend.
  * Fall R: In einer Kopie der Spielinhalte kommt das Rueckhol-Angebot sofort
    (Chance 100, keine Wartezeit). Der Weg durch den Spielcode ist derselbe.
  * Serverfarm: Aufbau wie test_spiel.ServerfarmTest (eine Aufgabe, keine
    Zwischenfaelle, Firma Stufe 4, Serverraum, Zertifikate als Ereignisse).

Gegenprobe gegen einen anderen Stand (z.B. v0.62.3, dort sind alle Tests rot):
    ENTLASSUNG_CODE=<ordner mit dem Code> python test_entlassung.py

Nur Wegwerf-Datenbanken in einem temporaeren Ordner.
Start:  python test_entlassung.py
"""

import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
# Aufruf als Hilfsprozess: python test_entlassung.py --protokoll <code> <db>
HELPER = len(sys.argv) == 4 and sys.argv[1] == "--protokoll"
CODE = os.path.abspath(sys.argv[2] if HELPER else
                       (os.environ.get("ENTLASSUNG_CODE") or HERE))
IN_CI = bool(os.environ.get("GITHUB_ACTIONS") or os.environ.get("CI"))
OLD_TAG = "v0.62.3"
WORK = tempfile.mkdtemp(prefix="fisi_entlassung_")
os.environ["FISI_DB_PATH"] = os.path.join(WORK, "unbenutzt.db")
sys.path.insert(0, CODE)

import fisi_core as core  # noqa: E402
import fisi_game as fg  # noqa: E402

NOT_HERE = "Diese Person arbeitet nicht bei dir."


# -- Hilfen ---------------------------------------------------------------------

def _content(recall=False):
    """Kopie der Spielinhalte; recall: Rueckhol-Angebot sofort und sicher."""
    content = json.loads(json.dumps(fg.GAME))
    if recall:
        rule = content["firma"]["rivalitaet"]["rueckhol"]
        rule.update({"chance": 100, "ab_tagen": 0, "abstand": 0, "abstand_firma": 0})
    return content


def _db(name):
    path = os.path.join(WORK, name)
    if os.path.exists(path):
        os.remove(path)
    return core.DBManager(path)


def _settle(game, keep=None):
    """Offene Entscheidungen mit der ersten erlaubten Moeglichkeit erledigen."""
    for item in list(game.state.open_decisions()):
        if keep and item["art"] == keep:
            continue
        option = next(o for o in item["optionen"] if not o.get("problem"))
        game.decide(item["id"], option["id"])


def _end_day(game):
    _settle(game)
    payload = game.end_day()
    game.reload()
    return payload


def _founded(db, content=None):
    """Gegruendete Firma mit genug Geld (Abkuerzung 1)."""
    content = content or fg.GAME
    game = fg.Game(db, "PC", content)
    game.set_profile("Pruef", {})
    goal = content["balancing"]["gruendung"]
    for index, task in enumerate(content["aufgaben"]):
        data = {"aufgabe": task["id"], "tag": 1, "richtig": True, "geld": 0, "reputation": {}}
        if index == 0:
            data["geld"] = int(goal["startkapital"]) + 500000
            data["reputation"] = {key: 70 for key in fg.AXIS_KEYS}
        db.log_game_event(fg.EV_SOLVED, json.dumps(data), "PC", game.run)
    game.reload()
    game.found_firm("Pruef IT")
    return game


def _former_applicant(game, content):
    """Eine Bewerbung mit frueherem Arbeitgeber (fuer das Rueckhol-Angebot)."""
    offers = fg.applicants(game.state, content)
    return next((item for item in offers if item.get("herkunft") == "bitweiche"), None) or \
        next(item for item in offers if item.get("vorher"))


def _win_project(game, team):
    content = game.content
    for _try in range(60):
        for tender in game.state.tenders():
            if tender.get("ergebnis") or fg.project_offer_problem(game.state, content):
                continue
            markup = min(fg.offer_rules(content)["zuschlaege"])
            answer = fg.find_solution(fg.project_task(tender, markup))
            result = game.send_project_offer(tender["id"], markup, answer)
            game.reload()
            if result["gewonnen"]:
                game.set_project_team(tender["id"], team)
                game.reload()
                return tender["id"]
        _end_day(game)
    raise AssertionError("kein Projekt gewonnen")


def _lower_mood(game, person):
    """Abkuerzung 2: Stimmung senken wie durch fuenf abgelehnte Urlaubsanfragen."""
    for number in range(5):
        game.db.log_game_event(fg.EV_VACATION_NO, json.dumps(
            {"anfrage": "pruef:%d:%s" % (number, person), "id": person,
             "name": game.state.staff[person].get("name", ""),
             "von": 0, "bis": 0, "tag": game.state.day}), "PC", game.run)
    game.reload()


def _quit(game, person):
    """Feierabende, bis die Person selbst kuendigt (hoechstens 10)."""
    _lower_mood(game, person)
    for _n in range(10):
        _end_day(game)
        if person not in game.state.staff:
            return
    raise AssertionError("%s hat nicht gekuendigt" % person)


def _let_go(game, person):
    """Feierabende bis zum Rueckhol-Angebot fuer person, dann "Ziehen lassen"
    und Feierabend: Danach ist die Person weg."""
    for _n in range(20):
        decision = next((item for item in game.state.open_decisions()
                         if item["art"] == fg.DECISION_RECALL and item["person"] == person),
                        None)
        if decision:
            break
        _settle(game)
        game.end_day()
        game.reload()
    else:
        raise AssertionError("kein Rueckhol-Angebot fuer %s" % person)
    game.decide(decision["id"], fg.RECALL_LET)
    game.reload()
    _end_day(game)
    if person in game.state.staff:
        raise AssertionError("%s ist nicht gegangen" % person)


def _new_person(game, content=None):
    person = fg.applicants(game.state, content or game.content)[0]["id"]
    game.hire(person)
    game.reload()
    return person


def _blocked_protocol(db_path):
    """Schreibt mit dem Code in CODE einen blockierten Spielstand: Person im
    Projektteam, entlassen, danach drei Feierabende. Liefert die Zahlen."""
    game = _founded(core.DBManager(db_path))
    person = _new_person(game)
    pid = _win_project(game, [person])
    for _ in range(2):
        _end_day(game)
    game.fire(person)
    game.reload()
    for _ in range(3):
        _end_day(game)
    state = game.state
    return {"projekt": pid, "person": person, "tag": state.day, "geld": state.money,
            "stand": state.projects[pid]["stand"], "team": state.projects[pid]["team"]}


_STAENDE = {}


def code_stand(tag):
    """Ordner mit dem Code aus einem Tag (git archive), oder None
    (wie in test_abgleich.py)."""
    if tag in _STAENDE:
        return _STAENDE[tag]
    target = os.path.join(WORK, "stand_" + tag)

    def archive():
        proc = subprocess.run(["git", "-C", HERE, "archive", "--format=tar", tag],
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
            except TypeError:           # Python ohne Filter
                tar.extractall(target)
        os.remove(tar_path)
        return True

    ok = archive()
    if not ok:
        subprocess.run(["git", "-C", HERE, "fetch", "--depth=1", "--no-tags", "origin",
                        "+refs/tags/%s:refs/tags/%s" % (tag, tag)], capture_output=True,
                       timeout=120)
        ok = archive()
    _STAENDE[tag] = target if ok else None
    return _STAENDE[tag]


# -- Projekte ---------------------------------------------------------------------

class ProjektTest(unittest.TestCase):
    """Fall E, K, R mit der Person im Projektteam."""

    def usable(self, game, pid, ghost):
        """Nach dem Weggang: Team leer, "Team aendern" gelingt, Projekt wird fertig."""
        state = game.state
        project = state.projects[pid]
        self.assertNotIn(ghost, state.staff)
        found = "Team-Liste %r, Anzeige %r" % (project["team"],
                                               fg.project_team_text(state, project))
        stand = project["stand"]
        # Zuerst der Klick-Weg (wie PC und Handy), damit "rot" den Fehler zeigt
        try:
            game.toggle_project_member(pid, fg.SELF)
        except ValueError as exc:
            self.fail("Team aendern (ich selbst): '%s' - %s" % (exc, found))
        self.assertEqual(project["team"], [], found)
        self.assertEqual(fg.project_team_text(state, project), "Noch kein Team")
        self.assertIn("noch kein Team", fg.project_status_text(state, project,
                                                               game.firm_levels()))
        game.reload()
        self.assertEqual(game.state.projects[pid]["team"], [fg.SELF])
        other = _new_person(game)
        game.toggle_project_member(pid, other)
        game.reload()
        self.assertEqual(game.state.projects[pid]["team"], [fg.SELF, other])
        for _n in range(30):
            if game.state.projects[pid]["fertig"]:
                break
            _end_day(game)
        project = game.state.projects[pid]
        self.assertTrue(project["fertig"])
        self.assertGreater(project["stand"], stand)

    def test_e_entlassen(self):
        game = _founded(_db("e.db"))
        person = _new_person(game)
        pid = _win_project(game, [person])
        for _ in range(2):
            _end_day(game)
        self.assertGreater(game.state.projects[pid]["stand"], 0)
        game.fire(person)
        game.reload()
        self.usable(game, pid, person)

    def test_k_kuendigung(self):
        game = _founded(_db("k.db"))
        self.assertTrue(game.state.ease("kuendigung", True))
        person = _new_person(game)
        pid = _win_project(game, [person])
        _end_day(game)
        _quit(game, person)
        self.assertIn(person, game.state.quit_staff)
        self.usable(game, pid, person)

    def test_r_ziehen_lassen(self):
        content = _content(recall=True)
        game = _founded(_db("r.db"), content)
        person = _former_applicant(game, content)["id"]
        game.hire(person)
        game.reload()
        pid = _win_project(game, [person])
        _let_go(game, person)
        self.assertIn(person, game.state.returned_staff)
        self.usable(game, pid, person)

    def test_team_liste_mit_ausgeschiedener_kennung(self):
        """"Team aendern" laesst eine entlassene Kennung still weg."""
        game = _founded(_db("liste.db"))
        person = _new_person(game)
        other = _new_person(game)
        pid = _win_project(game, [person])
        game.fire(person)
        game.reload()
        game.set_project_team(pid, [person, other])
        game.reload()
        self.assertEqual(game.state.projects[pid]["team"], [other])
        game.toggle_project_member(pid, person)
        game.reload()
        self.assertEqual(game.state.projects[pid]["team"], [other])
        # Unbekannte Kennungen bleiben ein Fehler
        with self.assertRaises(ValueError):
            game.set_project_team(pid, [other, "gibtsnicht"])

    def test_blockierter_stand_aus_alter_version(self):
        """Protokoll aus v0.62.3 (Person entlassen, Projekt blockiert) wird mit
        dem Code unter Test geladen: gleiche Zahlen, Team leer, bedienbar."""
        old = code_stand(OLD_TAG)
        if old is None:
            if IN_CI:
                self.fail("Tag %s fehlt, Code der alten Version nicht verfuegbar" % OLD_TAG)
            self.skipTest("Tag %s fehlt" % OLD_TAG)
        path = os.path.join(WORK, "blockiert.db")
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1",
                   FISI_DB_PATH=os.path.join(WORK, "alt_unbenutzt.db"))
        proc = subprocess.run([sys.executable, "-I", "-B", os.path.abspath(__file__),
                               "--protokoll", old, path], capture_output=True, text=True,
                              env=env, timeout=600)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        before = json.loads(proc.stdout.strip().splitlines()[-1])
        # Mit dem alten Code ist der Stand blockiert
        self.assertEqual(before["team"], [before["person"]])
        game = fg.Game(core.DBManager(path), "PC")
        state = game.state
        pid = before["projekt"]
        self.assertEqual((state.day, state.money, state.projects[pid]["stand"]),
                         (before["tag"], before["geld"], before["stand"]))
        self.usable(game, pid, before["person"])


# -- Serverfarm -------------------------------------------------------------------

class ServerfarmTest(unittest.TestCase):
    """Fall E, K, R mit der Person im Serverfarm-Team."""

    def ready(self, name, recall=False, former=False):
        content = _content(recall)
        task = content["aufgaben"][0]
        content["aufgaben"] = [task]
        content["zwischenfaelle"] = []
        db = _db(name)
        game = fg.Game(db, "PC", content)
        game.set_profile("Pruef", {})
        db.log_game_event(fg.EV_SOLVED, json.dumps(
            {"aufgabe": task["id"], "tag": 1, "richtig": True, "geld": 400000,
             "reputation": {key: 60 for key in fg.AXIS_KEYS}}), "PC", game.run)
        game.reload()
        game.found_firm("Pruef IT")
        while game.state.firm["stufe"] < 4:
            game.expand()
        game.build_room("serverraum")
        for cert in ("iso27001", "netzwerk"):
            db.log_game_event(fg.EV_CERT, json.dumps({"zert": cert, "tag": game.state.day,
                                                      "bis_tag": game.state.day, "geld": 0}),
                              "PC", game.run)
        game.reload()
        first = _former_applicant(game, content)["id"] if former else \
            fg.applicants(game.state, content)[0]["id"]
        game.hire(first)
        game.reload()
        staff = [first] + [_new_person(game) for _ in range(2)]
        _end_day(game)
        game.farm_start()
        game.farm_set_team(staff[:2])
        game.reload()
        self.assertEqual(game.state.farm["team"], staff[:2])
        return game, staff

    def usable(self, game, staff):
        ghost, stays, free = staff
        state = game.state
        self.assertNotIn(ghost, state.staff)
        found = "Team-Liste %r, Anzeige %r" % (state.farm["team"], fg.farm_status(state)["team"])
        # Zuerst der Klick-Weg (wie PC und Handy), damit "rot" den Fehler zeigt
        try:
            game.farm_toggle_member(free)
        except ValueError as exc:
            self.fail("Serverfarm-Team aendern: '%s' - %s" % (exc, found))
        self.assertEqual(state.farm["team"], [stays], found)
        self.assertNotIn(ghost, fg.farm_status(state)["team"])
        game.reload()
        self.assertEqual(game.state.farm["team"], [stays, free])
        game.farm_set_team([ghost, free])
        game.reload()
        self.assertEqual(game.state.farm["team"], [free])
        game.farm_toggle_member(ghost)
        game.reload()
        self.assertEqual(game.state.farm["team"], [free])
        with self.assertRaises(ValueError):
            game.farm_set_team([free, "x"])

    def test_e_entlassen(self):
        game, staff = self.ready("farm_e.db")
        game.fire(staff[0])
        game.reload()
        self.usable(game, staff)

    def test_k_kuendigung(self):
        game, staff = self.ready("farm_k.db")
        _quit(game, staff[0])
        self.usable(game, staff)

    def test_r_ziehen_lassen(self):
        game, staff = self.ready("farm_r.db", recall=True, former=True)
        _let_go(game, staff[0])
        self.usable(game, staff)


def tearDownModule():
    shutil.rmtree(WORK, ignore_errors=True)


if __name__ == "__main__":
    if HELPER:
        try:
            print(json.dumps(_blocked_protocol(sys.argv[3])))
        finally:
            shutil.rmtree(WORK, ignore_errors=True)
        sys.exit(0)
    print("Code unter Test: %s" % CODE)
    unittest.main(verbosity=2)
