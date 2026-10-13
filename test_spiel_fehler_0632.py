#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests fuer die Spiel-Kern-Fehler aus 0.63.2 (Bauauftrag N1, Plan-Nachtrag
0.63.2 Abschnitt 3, Punkte 1 bis 4):

  B-P-02  parse_number liest "0.125" als 125            (ZahlLesenTest)
  B-F-04  _num / percent_text zeigen "-0", "-0 %", "nan" (ZahlTextTest)
  B-F-07  Balken "Weg zum eigenen Unternehmen" 100 %, obwohl Auftraege
          bei Bitweiche offen sind                       (GruendungFortschrittTest)
  B-F-01  (Rest) Rueckfrage beim Entlassen nennt das Projekt nicht,
          PC- und Handy-Text gleich                      (EntlassenRueckfrageTest)

Erwartung: Die mit "ROT" markierten Tests sind auf 14b3bd4 (v0.63.1) rot und
nach der Aenderung gruen. Die mit "SCHUTZ" markierten sind auf beiden Staenden
gruen (sie belegen, dass sich echte Ausgaben nicht aendern).

Code-Ordner waehlbar (wie in test_spiel_doppelt.py):
    SPIEL_CODE=<ordner mit dem Code> python test_spiel_fehler_0632.py
Ohne Angabe: der Ordner dieser Datei. Nur Wegwerf-Datenbanken (eigener
Temp-Ordner, eigenes HOME und FISI_DB_PATH).
Liste der Abweichungen alt/neu beim Zahl-Lesen (fuer den Bericht):
    SPIEL_FEHLER_LISTE=<datei> python test_spiel_fehler_0632.py
Start:  python test_spiel_fehler_0632.py
"""

import json
import os
import re
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
CODE = os.path.abspath(os.environ.get("SPIEL_CODE") or HERE)
_HOME = tempfile.mkdtemp(prefix="fisi_spiel_fehler_")
os.environ["HOME"] = _HOME
os.environ["FISI_DB_PATH"] = os.path.join(_HOME, "nie_benutzt.db")
sys.path.insert(0, CODE)
sys.path.insert(1, os.path.join(CODE, "mobile", "src"))

import fisi_core as core  # noqa: E402
import fisi_game as fg  # noqa: E402

assert os.path.dirname(os.path.abspath(fg.__file__)) == CODE, fg.__file__

DASH = "–"   # Gedankenstrich


# -- Vergleichsstand: die drei Funktionen wie auf 14b3bd4 (v0.63.1) -------------

def _alt_num(value):
    if isinstance(value, float) and not value.is_integer():
        text = ("%.2f" % value).rstrip("0").rstrip(".")
    else:
        text = "%d" % int(round(value))
    whole, _sep, frac = text.partition(".")
    sign = "-" if whole.startswith("-") else ""
    whole = whole.lstrip("-")
    groups = []
    while len(whole) > 3:
        groups.insert(0, whole[-3:])
        whole = whole[:-3]
    groups.insert(0, whole)
    return sign + ".".join(groups) + ("," + frac if frac else "")


def _alt_percent_text(value):
    text = ("%.2f" % float(value)).rstrip("0").rstrip(".")
    return "%s %%" % text.replace(".", ",")


def _alt_parse_number(text):
    text = (text or "").strip().replace(" ", "").replace(" ", "")
    text = re.sub(r"(€|EUR|TB|GB|Platten?|%|Hosts?)$", "", text, flags=re.I).strip()
    if not text:
        return None
    if "," in text and "." in text:
        text = text.replace(".", "").replace(",", ".")
    elif "," in text:
        text = text.replace(",", ".")
    elif re.fullmatch(r"-?\d{1,3}(\.\d{3})+", text):
        text = text.replace(".", "")
    try:
        return float(text)
    except ValueError:
        return None


# -- Hilfen ---------------------------------------------------------------------

class TempDB:
    def __enter__(self):
        self.folder = tempfile.mkdtemp(dir=_HOME)
        return core.DBManager(os.path.join(self.folder, "spiel.db"))

    def __exit__(self, *_exc):
        shutil.rmtree(self.folder, ignore_errors=True)


def _content():
    return json.loads(json.dumps(fg.GAME))


def _walk(obj):
    if isinstance(obj, dict):
        yield obj
        for value in obj.values():
            yield from _walk(value)
    elif isinstance(obj, list):
        for value in obj:
            yield from _walk(value)


FORM_KINDS = ("ip_plan", "raid", "angebot", "leasing", "drucker")


def _number_fields():
    """Alle Zahl-Felder (zahl, geld, prozent) aller Formular-Aufgaben in den
    Spielinhalten: [(aufgabe, feld)]."""
    found, seen = [], set()
    for item in _walk(fg.GAME):
        if item.get("art") not in FORM_KINDS or "id" not in item:
            continue
        try:
            fields = fg.form_fields(item)
        except Exception:   # noqa: BLE001 - kein Formular (andere "art")
            continue
        for field in fields:
            if field["art"] in ("zahl", "geld", "prozent"):
                key = (item["id"], field["id"])
                if key not in seen:
                    seen.add(key)
                    found.append((item["id"], field))
    return found


def _settle(game):
    for item in list(game.state.open_decisions()):
        option = next(o for o in item["optionen"] if not o.get("problem"))
        game.decide(item["id"], option["id"])


def _end_day(game):
    _settle(game)
    game.end_day()
    game.reload()


def _founded(db):
    """Gegruendete Firma mit genug Geld (wie test_entlassung._founded)."""
    content = fg.GAME
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


def _win_project(game, team):
    """Wie test_entlassung._win_project."""
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


def _new_person(game):
    person = fg.applicants(game.state, game.content)[0]["id"]
    game.hire(person)
    game.reload()
    return person


# -- B-P-02 ---------------------------------------------------------------------

class ZahlLesenTest(unittest.TestCase):
    """B-P-02: Tausenderpunkt nur ohne fuehrende Null."""

    def test_null_komma_mit_punkt(self):
        """ROT: "0.125" ist 0,125 (alt: 125), "-0.125" ist -0,125."""
        self.assertEqual(fg.parse_number("0.125"), 0.125)
        self.assertEqual(fg.parse_number("-0.125"), -0.125)
        self.assertEqual(fg.parse_number("0.125 TB"), 0.125)

    def test_bisherige_lesarten_bleiben(self):
        """SCHUTZ: Tausender und Kommazahlen wie bisher."""
        for text, value in (("-0.5", -0.5), ("1.000", 1000.0), ("1.234,50 €", 1234.5),
                            ("12000", 12000.0), ("12.500", 12500.0), ("1.234", 1234.0),
                            ("-1.234", -1234.0), ("1.234.567", 1234567.0),
                            ("66,7 %", 66.7), ("16 TB", 16.0), ("0,125", 0.125),
                            ("0", 0.0), ("", None), ("abc", None)):
            self.assertEqual(fg.parse_number(text), value, text)

    def test_gleichheit_ueber_alle_zahlaufgaben(self):
        """SCHUTZ: Fuer jede Musterloesung aller Zahl-Felder (Anzeige, Rohwert,
        deutsche Zahl, Euro bzw. Prozent) liefern alter und neuer Stand dieselbe
        Zahl - ausser bei fuehrender Null (dann ist der neue Wert der richtige)."""
        fields = _number_fields()
        self.assertGreater(len(fields), 100)
        inputs, differ = 0, []
        for task_id, field in fields:
            soll = field["soll"]
            texts = {field["anzeige"], str(soll), fg._num(soll)}
            if field["art"] == "geld":
                texts.add(fg._euro(soll))
            if field["art"] == "prozent":
                texts.add(fg.percent_text(soll))
            for text in sorted(texts):
                inputs += 1
                old, new = _alt_parse_number(text), fg.parse_number(text)
                if old != new:
                    differ.append("%s/%s %r: alt %r, neu %r" % (task_id, field["id"], text,
                                                              old, new))
                    self.assertRegex(text.strip(), r"^-?0\.\d{3}")
                    self.assertTrue(fg.field_ok(field, text), text)
            self.assertTrue(fg.field_ok(field, field["anzeige"]),
                            "%s/%s %r" % (task_id, field["id"], field["anzeige"]))
        liste = os.environ.get("SPIEL_FEHLER_LISTE")
        if liste:
            with open(liste, "w", encoding="utf-8") as handle:
                handle.write("Zahl-Felder: %d, Eingaben: %d, alt != neu: %d\n" % (
                    len(fields), inputs, len(differ)))
                handle.writelines(line + "\n" for line in differ)


# -- B-F-04 ---------------------------------------------------------------------

class ZahlTextTest(unittest.TestCase):
    """B-F-04: kein "-0", "-0 %", "nan"."""

    def test_minus_null(self):
        """ROT: auf 0 gerundete Werte ohne Vorzeichen."""
        self.assertEqual(fg._num(-0.001), "0")
        self.assertEqual(fg._num(-0.004), "0")
        self.assertEqual(fg.percent_text(-0.001), "0 %")
        self.assertEqual(fg.percent_text(-0.004), "0 %")
        self.assertEqual(fg.percent_text(-0.0), "0 %")

    def test_nan_und_inf(self):
        """ROT: nan und inf als Gedankenstrich."""
        for value in (float("nan"), float("inf"), float("-inf")):
            self.assertEqual(fg._num(value), DASH, value)
            self.assertEqual(fg.percent_text(value), DASH, value)

    def test_sonst_unveraendert(self):
        """SCHUTZ: Werte und Raster wie bisher (alt = neu)."""
        for value, num, pct in ((-0.5, "-0,5", "-0,5 %"), (1234.5, "1.234,5", "1234,5 %"),
                                (-1234, "-1.234", "-1234 %"), (8.5, "8,5", "8,5 %"),
                                (10.0, "10", "10 %"), (0.0, "0", "0 %"), (-0.0, "0", None),
                                (0.004, "0", "0 %"), (-0.005, "-0,01", "-0,01 %")):
            self.assertEqual(fg._num(value), num, value)
            if pct is not None:
                self.assertEqual(fg.percent_text(value), pct, value)
        values = [i / 100.0 for i in range(-100000, 100001, 7)]
        values += [i / 1000.0 for i in range(-2000, 2001) if abs(i) >= 5]
        values += list(range(-2000, 2000, 13))
        for value in values:
            self.assertEqual(fg._num(value), _alt_num(value), value)
            self.assertEqual(fg.percent_text(value), _alt_percent_text(value), value)

    def test_echte_ausgaben_alt_gleich_neu(self):
        """SCHUTZ: Alle Ausgaben der echten Aufrufer (Muster der Gesamtpruefung
        0.62.4, f6_zahlformat.py: Aufgaben-Loesungen, Kredit-Raster,
        Serverfarm-Aufgaben, dazu ein Bot-Lauf) sind alt und neu gleich."""
        seen = []
        orig_num, orig_pct = fg._num, fg.percent_text

        def num_spy(value):
            seen.append(("_num", value))
            return orig_num(value)

        def pct_spy(value):
            seen.append(("percent_text", value))
            return orig_pct(value)

        fg._num, fg.percent_text = num_spy, pct_spy
        try:
            for task in fg.GAME["aufgaben"]:
                for func in (fg.find_solution, fg.solution_text):
                    try:
                        func(task)
                    except Exception:   # noqa: BLE001 - wie f6_zahlformat.py
                        pass
            for amount in range(5000, 100001, 1000):
                for term in (10, 20, 30, 40, 50, 75, 100):
                    try:
                        fg.percent_text(fg.loan_offer_numbers(amount, term)["zins"])
                    except Exception:   # noqa: BLE001
                        pass
            for task in fg.farm_tasks():
                for func in (fg.farm_solution_lines, fg.farm_solution):
                    try:
                        func(task)
                    except Exception:   # noqa: BLE001
                        pass
            with TempDB() as db:
                game = _founded(db)
                person = _new_person(game)
                pid = _win_project(game, [person])
                for _ in range(3):
                    _end_day(game)
                state = game.state
                fg.project_status_text(state, state.projects[pid], game.knowledge())
        finally:
            fg._num, fg.percent_text = orig_num, orig_pct
        self.assertGreater(len(seen), 800)
        for name, value in seen:
            old = _alt_num(value) if name == "_num" else _alt_percent_text(value)
            new = orig_num(value) if name == "_num" else orig_pct(value)
            self.assertEqual(new, old, "%s(%r)" % (name, value))
        liste = os.environ.get("SPIEL_FEHLER_LISTE")
        if liste:
            with open(liste, "a", encoding="utf-8") as handle:
                handle.write("Echte Ausgaben _num/percent_text: %d, alt != neu: 0\n" % len(seen))


# -- B-F-07 ---------------------------------------------------------------------

class GruendungFortschrittTest(unittest.TestCase):
    """B-F-07: 100 % genau dann, wenn founding_missing() leer ist."""

    def _rich(self, db, open_tasks):
        """Volles Kapital und Ansehen, alle Auftraege bis auf open_tasks erledigt."""
        game = fg.Game(db, "PC")
        game.set_profile("Nico", {})
        tasks = fg.GAME["aufgaben"]
        for index, task in enumerate(tasks[:len(tasks) - open_tasks]):
            data = {"aufgabe": task["id"], "tag": 1, "richtig": True, "geld": 0,
                    "reputation": {}}
            if index == 0:
                data["geld"] = 30000
                data["reputation"] = {key: 70 for key in fg.AXIS_KEYS}
            db.log_game_event(fg.EV_SOLVED, json.dumps(data), "PC", game.run)
        game.reload()
        return game

    def test_offene_auftraege(self):
        """ROT: 84 offene Auftraege, Kapital und Ansehen voll: unter 100 %."""
        with TempDB() as db:
            state = self._rich(db, 84).state
            self.assertIn("84 Aufträge bei Bitweiche offen", state.founding_missing())
            self.assertEqual(len(state.founding_missing()), 1)
            total = len(fg.GAME["aufgaben"])
            self.assertAlmostEqual(state.founding_progress(), (total - 84) / float(total))
            self.assertLess(state.founding_progress(), 1.0)

    def test_ein_offener_auftrag_nicht_100_prozent(self):
        """ROT: ein oder zwei offene Auftraege: Anzeige "%d %%" nie "100 %"."""
        for left in (1, 2):
            with TempDB() as db:
                state = self._rich(db, left).state
                self.assertTrue(state.founding_missing())
                self.assertLessEqual(state.founding_progress(), 0.99)
                self.assertNotEqual("%d %%" % round(state.founding_progress() * 100), "100 %")

    def test_alles_erledigt_100_prozent(self):
        """SCHUTZ: nichts offen: 1.0 und founding_missing() leer."""
        with TempDB() as db:
            state = self._rich(db, 0).state
            self.assertEqual(state.founding_missing(), [])
            self.assertEqual(state.founding_progress(), 1.0)

    def _bot(self, content, steps):
        """Bot-Lauf (alle Tickets loesen, Feierabend); nach jedem Schritt, ohne
        Firma: Fortschritt == 1.0 genau dann, wenn founding_missing() leer."""
        checked = []
        with TempDB() as db:
            game = fg.Game(db, "PC", content)
            game.set_profile("Ada", {})

            def check():
                state = game.state
                self.assertIsNone(state.firm)
                progress = state.founding_progress()
                self.assertGreaterEqual(progress, 0.0)
                self.assertLessEqual(progress, 1.0)
                self.assertEqual(progress == 1.0, state.founding_missing() == [],
                                 (state.day, progress, state.founding_missing()))
                self.assertEqual(round(progress * 100) == 100,
                                 state.founding_missing() == [])
                checked.append((progress, bool(state.founding_missing())))

            check()
            for _day in range(steps):
                for _ in range(60):
                    todo = game.state.open_tickets()
                    if not todo:
                        break
                    task = todo[0]
                    prepared = game.state.prepared_task(task)
                    answer = fg.find_solution(prepared, game.state.available_parts(prepared))
                    try:
                        game.solve(task["id"], answer or {}, False)
                    except ValueError:
                        game.defer(task["id"])
                    check()
                _settle(game)
                game.end_day()
                game.reload()
                check()
                if game.state.founding_ready():
                    break
        return checked

    def test_bot_auftraege_zuletzt(self):
        """ROT: Kapital und Ansehen sofort erreicht, Auftraege der Engpass."""
        content = _content()
        content["aufgaben"] = content["aufgaben"][:6]
        content["zwischenfaelle"] = []
        content["balancing"]["gruendung"].update(startkapital=1, mindest_reputation=1)
        checked = self._bot(content, 25)
        self.assertTrue(any(missing for _p, missing in checked))
        self.assertEqual(checked[-1], (1.0, False))

    def test_bot_kapital_zuletzt(self):
        """SCHUTZ: Auftraege zuerst erledigt, Kapital der Engpass."""
        content = _content()
        content["aufgaben"] = content["aufgaben"][:4]
        content["zwischenfaelle"] = []
        content["balancing"]["gruendung"].update(startkapital=2500, mindest_reputation=1)
        checked = self._bot(content, 40)
        self.assertTrue(any(missing for _p, missing in checked))
        self.assertEqual(checked[-1], (1.0, False))

    def test_mit_firma_kein_balken(self):
        """SCHUTZ: Mit Firma ist founding_missing() leer, und alle vier Anzeigen
        des Balkens sind dann aus (PC: nur ohne Firma bzw. nur bei fehlenden
        Bedingungen; Handy: unsichtbar mit Firma bzw. nur bei fehlenden)."""
        with TempDB() as db:
            state = _founded(db).state
            self.assertTrue(state.firm)
            self.assertEqual(state.founding_missing(), [])
        with open(os.path.join(CODE, "fisi_game_gui.py"), encoding="utf-8") as handle:
            pc = handle.read()
        with open(os.path.join(CODE, "mobile", "src", "spiel.py"), encoding="utf-8") as handle:
            mobile = handle.read()
        self.assertEqual(pc.count("founding_progress()"), 3)
        self.assertRegex(pc, r"if not state\.firm:\n\s+bar = GradientBar\(info, \"Weg zum "
                             r"eigenen Unternehmen\"[^\n]*\n[^\n]*\n[^\n]*\n\s+bar\.set\("
                             r"state\.founding_progress\(\)")
        self.assertRegex(pc, r"missing = state\.founding_missing\(\)\n\s+if missing:\n"
                             r"(\s+[^\n]*\n){3}\s+bar\.set\(state\.founding_progress\(\)")
        self.assertEqual(mobile.count("founding_progress()"), 3)
        self.assertRegex(mobile, r"founding\.set\(state\.founding_progress\(\)[^\n]*\n"
                                 r"\s+founding\.visible = not state\.firm\n")
        self.assertRegex(mobile, r"missing = state\.founding_missing\(\)\n\s+if missing:\n"
                                 r"\s+bar = [^\n]*\n\s+bar\.set\(state\.founding_progress\(\)")


# -- B-F-01 (Rest) --------------------------------------------------------------

class EntlassenRueckfrageTest(unittest.TestCase):
    """B-F-01 (Rest): Rueckfrage nennt das Projekt, PC und Handy gleich."""

    OHNE = "%s wirklich entlassen? Die Person bewirbt sich danach nicht erneut."

    @classmethod
    def setUpClass(cls):
        cls.tmp = TempDB()
        db = cls.tmp.__enter__()
        cls.game = _founded(db)
        cls.in_project = _new_person(cls.game)
        cls.free = _new_person(cls.game)
        cls.pid = _win_project(cls.game, [cls.in_project])
        cls.title = cls.game.state.projects[cls.pid]["titel"]

    @classmethod
    def tearDownClass(cls):
        cls.tmp.__exit__(None, None, None)

    def _item(self, person):
        return {"id": person, "name": self.game.state.staff[person]["name"]}

    def _pc_text(self, item):
        import fisi_game_gui as gg
        asked = []
        original = gg.messagebox.askyesno
        gg.messagebox.askyesno = lambda title, text, **_kw: asked.append((title, text))
        try:
            fake = type("Fake", (), {"game": self.game})()
            gg.FirmView._fire(fake, item)
        finally:
            gg.messagebox.askyesno = original
        self.assertEqual(len(asked), 1)
        return asked[0]

    def _mobile_text(self, item):
        import spiel
        asked = []
        app = type("App", (), {"confirm": lambda _s, title, text, _cb: asked.append(
            (title, text))})()
        fake = type("Fake", (), {"game": self.game, "app": app})()
        spiel.GameScreen._fire(fake, item)
        self.assertEqual(len(asked), 1)
        return asked[0]

    def test_rueckfrage_nennt_projekt(self):
        """ROT: Person im laufenden Projekt: Rueckfrage nennt den Titel."""
        item = self._item(self.in_project)
        self.assertEqual(self.game.state.project_of(self.in_project), self.pid)
        expected = (self.OHNE % item["name"] + " %s arbeitet im Projekt „%s“. Das Projekt "
                    "läuft ohne diese Person weiter; das Team änderst du unter "
                    "„Team ändern“." % (item["name"], self.title))
        self.assertEqual(self._pc_text(item), ("Entlassen", expected))

    def test_pc_und_handy_gleich(self):
        """ROT (Projektteil) bzw. SCHUTZ: PC- und Handy-Rueckfrage gleich."""
        for person in (self.in_project, self.free):
            item = self._item(person)
            self.assertEqual(self._pc_text(item), self._mobile_text(item))
        self.assertIn(self.title, self._mobile_text(self._item(self.in_project))[1])

    def test_ohne_projekt_unveraendert(self):
        """SCHUTZ: ohne Projekt Text wie bis 0.63.1."""
        item = self._item(self.free)
        self.assertIsNone(self.game.state.project_of(self.free))
        self.assertEqual(self._pc_text(item), ("Entlassen", self.OHNE % item["name"]))
        self.assertEqual(self._mobile_text(item), ("Entlassen", self.OHNE % item["name"]))

    def test_lesefunktion_schreibt_nichts(self):
        """ROT (neue Funktion): fire_projects nur lesend, kein Ereignis."""
        events = len(self.game.db.game_events(self.game.run))
        found = self.game.fire_projects(self.in_project)
        self.assertEqual([item["projekt"] for item in found], [self.pid])
        self.assertEqual(self.game.fire_projects(self.free), [])
        self.assertEqual(len(self.game.db.game_events(self.game.run)), events)


def tearDownModule():
    shutil.rmtree(_HOME, ignore_errors=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
