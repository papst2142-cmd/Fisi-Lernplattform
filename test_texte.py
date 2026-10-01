# -*- coding: utf-8 -*-
"""Textpruefung der FISI-Lernplattform (ab 0.53).

Prueft offline und ohne Fremdbibliothek:
- keine verbotene Schreibweise aus pruefung/wortliste.txt in den Lerninhalten
  (inhalte/*.json, inhalte/spiel/*.json) und in den sichtbaren Texten der
  Programme (Stringliterale der .py-Dateien, ueber ast gelesen),
- jede Quizfrage und jede Karteikarte hat genau eine Option, die gleich "a" ist,
- jeder Eintrag in inhalte/umbenennungen.json zeigt auf einen vorhandenen,
  eindeutigen neuen Fragetext, und der alte Text kommt nicht mehr vor,
- optional: Rechtschreibung der Lerninhalte mit hunspell (de_DE) plus
  Abschnitt [bekannt] der Wortliste (wird uebersprungen, wenn hunspell fehlt).

Aufruf: python -m unittest test_texte
"""
import ast
import glob
import json
import os
import re
import shutil
import subprocess
import unittest

HIER = os.path.dirname(os.path.abspath(__file__))
WORTLISTE = os.path.join(HIER, "pruefung", "wortliste.txt")

# Restfunde in Programmdateien, die noch nicht behoben sind (die .py-Dateien
# werden getrennt bearbeitet). Paare (Datei, verbotene Form). Behobene
# Eintraege hier einfach streichen; neue Funde ausserhalb dieser Menge lassen
# den Test fehlschlagen.
noch_offen_py = {
    ("app_gui.py", "AP1 Szenarien"),        # Menue und Fortschrittsringe
    ("app_gui.py", "AP2 Szenarien"),
    ("app_gui.py", "Test Projekt"),         # Menuepunkt
    ("app_gui.py", "AP1 SZENARIEN"),        # Brotkrumen-Titel
    ("app_gui.py", "AP2 SZENARIEN"),
    ("app_gui.py", "TEST PROJEKT"),
    ("app_gui.py", "Tag(e)"),               # "Lernserie: %d Tag(e)"
    ("fisi_core.py", "AP1 Szenarien"),      # SOURCE_PLURAL
    ("fisi_core.py", "AP2 Szenarien"),
    ("fisi_game_gui.py", "irgendwo hin"),   # Hinweis in der Spielansicht
    ("mobile/src/main.py", "AP1 Szenarien"),
    ("mobile/src/main.py", "AP2 Szenarien"),
    ("mobile/src/main.py", "Test Projekt"),
    ("mobile/src/main.py", "AP1 SZENARIEN"),
    ("mobile/src/main.py", "AP2 SZENARIEN"),
    ("mobile/src/main.py", "TEST PROJEKT"),
    ("mobile/src/main.py", "Tag(e)"),
    ("mobile/src/spiel.py", "irgendwo hin"),  # "Tippe irgendwo hin"
}

# Schluessel, deren Werte keine Lesetexte sind (IDs, Kategorien, Symbole).
ID_KEYS = {"cat", "thema", "theme", "typ", "raum", "ort", "id", "auftraggeber", "empfaenger", "haendler",
           "achsen", "slots", "modell", "icon", "farbe", "symbol", "bild", "stil", "key", "kategorie",
           "fachbereich", "themen", "sperren", "voraussetzung", "voraussetzungen", "schluessel"}
BUCHSTABE = "A-Za-zÄÖÜäöüß"
WORT = re.compile(r"[A-Za-zÄÖÜäöüß][A-Za-zÄÖÜäöüß\-]*[A-Za-zÄÖÜäöüß]|[A-Za-zÄÖÜäöüß]")


def rel(pfad):
    return os.path.relpath(pfad, HIER).replace(os.sep, "/")


def lade_wortliste():
    """Liefert (verboten, ausnahmen, bekannt).
    verboten: Liste (anzeige, regex, richtig); ausnahmen: Liste Textausschnitte."""
    verboten, ausnahmen, bekannt = [], [], set()
    abschnitt = None
    with open(WORTLISTE, encoding="utf-8") as h:
        for zeile in h:
            zeile = zeile.rstrip("\n")
            if not zeile.strip() or zeile.lstrip().startswith("#"):
                continue
            if zeile.strip() in ("[verboten]", "[ausnahmen]", "[bekannt]"):
                abschnitt = zeile.strip()
                continue
            if abschnitt == "[verboten]":
                falsch, _, richtig = zeile.partition(" -> ")
                falsch = falsch.strip()
                if falsch.startswith("re:"):
                    muster = re.compile(falsch[3:])
                else:
                    muster = re.compile("(?<![%s])%s(?![%s])" % (BUCHSTABE, re.escape(falsch), BUCHSTABE))
                verboten.append((falsch, muster, richtig.strip()))
            elif abschnitt == "[ausnahmen]":
                _, _, stelle = zeile.partition(" | ")
                if stelle.strip():
                    ausnahmen.append(stelle.strip())
            elif abschnitt == "[bekannt]":
                wort = zeile.split("#")[0].strip()
                if wort:
                    bekannt.add(wort)
    return verboten, ausnahmen, bekannt


def json_dateien():
    dateien = sorted(glob.glob(os.path.join(HIER, "inhalte", "*.json"))
                     + glob.glob(os.path.join(HIER, "inhalte", "spiel", "*.json")))
    return [d for d in dateien if not d.endswith("umbenennungen.json")]


def json_texte():
    """Alle Lesetexte der Inhalte als Liste (quelle, ort, text)."""
    texte = []

    def walk(obj, pfad, quelle):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if str(k).startswith("_"):  # interne Hinweise
                    continue
                walk(v, pfad + "." + str(k), quelle)
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                walk(v, pfad + "[%d]" % i, quelle)
        elif isinstance(obj, str):
            key = pfad.rsplit(".", 1)[-1].split("[")[0]
            if key in ID_KEYS or key.endswith("_id"):
                return
            if re.fullmatch(r"[a-z0-9_\-]+", obj):
                return
            if re.search(r"[A-Za-zÄÖÜäöüß]{3,}", obj):
                texte.append((quelle, pfad, obj))

    for datei in json_dateien():
        with open(datei, encoding="utf-8") as h:
            walk(json.load(h), "", rel(datei))
    return texte


CODEY = re.compile(r"^[a-z0-9_./:#%\-\[\]{}()=<>+*,;|\\'\"]*$")


def sichtbar(s):
    if not re.search(r"[A-Za-zÄÖÜäöüß]{3,}", s):
        return False
    if CODEY.match(s):
        return False
    if " " not in s and not re.search(r"[ÄÖÜäöüß]", s) and not s[0].isupper():
        return False
    return True


def py_dateien():
    dateien = [d for d in sorted(glob.glob(os.path.join(HIER, "*.py")))
               if not os.path.basename(d).startswith("test_")]
    dateien += sorted(glob.glob(os.path.join(HIER, "mobile", "*.py")))
    # Kopien der gemeinsamen Dateien (mobile/vorbereiten.py) nicht doppelt pruefen
    geteilt = {os.path.basename(d) for d in dateien}
    dateien += [d for d in sorted(glob.glob(os.path.join(HIER, "mobile", "src", "*.py")))
                if os.path.basename(d) not in geteilt]
    return dateien


def py_texte():
    """Sichtbare Stringliterale der Programme (ohne Docstrings und Kommentare)."""
    texte = []
    for datei in py_dateien():
        with open(datei, encoding="utf-8") as h:
            baum = ast.parse(h.read(), filename=datei)
        docs = set()
        for knoten in ast.walk(baum):
            if isinstance(knoten, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                rumpf = getattr(knoten, "body", [])
                if rumpf and isinstance(rumpf[0], ast.Expr) and isinstance(rumpf[0].value, ast.Constant) \
                        and isinstance(rumpf[0].value.value, str):
                    docs.add(id(rumpf[0].value))
        in_fstring = set()
        for knoten in ast.walk(baum):
            if isinstance(knoten, ast.JoinedStr):
                teile = []
                for v in knoten.values:
                    if isinstance(v, ast.Constant) and isinstance(v.value, str):
                        teile.append(v.value)
                        in_fstring.add(id(v))
                    else:
                        teile.append("{x}")
                s = "".join(teile)
                if sichtbar(s):
                    texte.append((rel(datei), "Z%d" % knoten.lineno, s))
        for knoten in ast.walk(baum):
            if isinstance(knoten, ast.Constant) and isinstance(knoten.value, str) \
                    and id(knoten) not in docs and id(knoten) not in in_fstring and sichtbar(knoten.value):
                texte.append((rel(datei), "Z%d" % knoten.lineno, knoten.value))
    return texte


def verbotene_funde(texte, verboten, ausnahmen):
    funde = []
    for quelle, ort, text in texte:
        for stelle in ausnahmen:
            text = text.replace(stelle, " ")
        for falsch, muster, richtig in verboten:
            if muster.search(text):
                funde.append((quelle, ort, falsch, richtig, text))
    return funde


class VerboteneFormenTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.verboten, cls.ausnahmen, cls.bekannt = lade_wortliste()

    def test_wortliste_gueltig(self):
        self.assertTrue(self.verboten, "Abschnitt [verboten] ist leer")
        self.assertTrue(self.bekannt, "Abschnitt [bekannt] ist leer")
        for falsch, muster, _ in self.verboten:
            for wort in self.bekannt:
                self.assertIsNone(muster.fullmatch(wort),
                                  "%r steht in [bekannt], ist aber verboten (%s)" % (wort, falsch))

    def test_inhalte_ohne_verbotene_formen(self):
        funde = verbotene_funde(json_texte(), self.verboten, self.ausnahmen)
        meldung = "\n".join("%s %s: %r -> %s | %s" % (q, o, f, r, t[:120]) for q, o, f, r, t in funde)
        self.assertEqual(funde, [], "Verbotene Schreibweisen in den Inhalten:\n" + meldung)

    def test_programmtexte_ohne_verbotene_formen(self):
        funde = verbotene_funde(py_texte(), self.verboten, self.ausnahmen)
        neu = [f for f in funde if (f[0], f[2]) not in noch_offen_py]
        meldung = "\n".join("%s %s: %r -> %s | %s" % (q, o, f, r, t[:120]) for q, o, f, r, t in neu)
        self.assertEqual(neu, [], "Verbotene Schreibweisen in Programmtexten:\n" + meldung)


class AntwortOptionenTest(unittest.TestCase):
    def pruefe(self, datei):
        with open(os.path.join(HIER, "inhalte", datei), encoding="utf-8") as h:
            eintraege = json.load(h)
        fehler = []
        for i, e in enumerate(eintraege):
            treffer = sum(1 for o in e.get("options", []) if o == e.get("a"))
            if treffer != 1:
                fehler.append("[%d] %d Optionen gleich a: %s" % (i, treffer, e.get("q", "")[:80]))
        self.assertEqual(fehler, [], datei + ":\n" + "\n".join(fehler))

    def test_quizfragen(self):
        self.pruefe("quizfragen.json")

    def test_karteikarten(self):
        self.pruefe("karteikarten.json")


class UmbenennungenTest(unittest.TestCase):
    DATEIEN = {"karte": "karteikarten.json", "quiz": "quizfragen.json"}

    def test_umbenennungen(self):
        with open(os.path.join(HIER, "inhalte", "umbenennungen.json"), encoding="utf-8") as h:
            umb = json.load(h)
        self.assertEqual(set(k for k in umb if not k.startswith("_")), set(self.DATEIEN))
        for art, datei in self.DATEIEN.items():
            with open(os.path.join(HIER, "inhalte", datei), encoding="utf-8") as h:
                fragen = [e.get("q") for e in json.load(h)]
            zuordnung = umb[art]
            for alt, neu in zuordnung.items():
                self.assertEqual(fragen.count(neu), 1,
                                 "%s: neuer Text nicht genau einmal vorhanden: %r" % (datei, neu[:100]))
                self.assertNotIn(alt, fragen, "%s: alter Text noch vorhanden: %r" % (datei, alt[:100]))
                self.assertNotIn(neu, zuordnung, "%s: Kette alt -> neu -> neuer: %r" % (datei, neu[:100]))
                self.assertNotEqual(alt, neu)


class LernstandUmbenennungTest(unittest.TestCase):
    """Antworten zu alten Fragetexten zaehlen nach der Korrektur beim neuen
    Text - beim Start (Datenbank-Migration) und nach dem Abgleich mit einem
    Geraet, das noch die alte Version hat."""

    def setUp(self):
        import tempfile
        import fisi_core
        self.core = fisi_core
        self.ordner = tempfile.mkdtemp()
        self.karte_alt, self.karte_neu = next(iter(fisi_core.QUESTION_RENAMES["card_events"].items()))
        self.quiz_alt, self.quiz_neu = next(iter(fisi_core.QUESTION_RENAMES["quiz_answers"].items()))

    def tearDown(self):
        shutil.rmtree(self.ordner, ignore_errors=True)

    def _db(self, name):
        return self.core.DBManager(os.path.join(self.ordner, name))

    def _fragen(self, db, tabelle):
        conn = db.get_connection()
        try:
            return sorted(r[0] for r in conn.execute("SELECT question FROM %s" % tabelle))
        finally:
            conn.close()

    def test_migration_beim_start(self):
        db = self._db("a.db")
        db.log_card("Netzwerk", self.karte_alt, "learn", 1)
        db.log_quiz_answer("Netzwerk", self.quiz_alt, 1)
        db.log_quiz_answer("Netzwerk", "unveraendert", 0)
        db = self._db("a.db")          # neuer Start = init_db
        self.assertEqual(self._fragen(db, "card_events"), [self.karte_neu])
        self.assertEqual(self._fragen(db, "quiz_answers"), sorted([self.quiz_neu, "unveraendert"]))
        status = db.question_results()
        self.assertIn(self.quiz_neu, str(status))
        self.assertNotIn(self.quiz_alt, str(status))

    def test_abgleich_mit_alter_version(self):
        import fisi_sync
        alt = self._db("alt.db")
        alt.log_quiz_answer("Netzwerk", self.quiz_alt, 1)
        conn = alt.get_connection()        # Geraet mit 0.52: alter Text bleibt
        conn.execute("UPDATE quiz_answers SET question = ?", (self.quiz_alt,))
        conn.commit()
        conn.close()
        daten = fisi_sync.export_local(alt)
        self.assertEqual(daten["tables"]["quiz_answers"][0][3], self.quiz_alt)
        neu = self._db("neu.db")
        self.assertEqual(fisi_sync.merge_into_local(neu, daten), 1)
        self.assertEqual(self._fragen(neu, "quiz_answers"), [self.quiz_neu])
        # erneuter Abgleich zaehlt nichts doppelt (gleiche uid)
        self.assertEqual(fisi_sync.merge_into_local(neu, daten), 0)
        self.assertEqual(len(self._fragen(neu, "quiz_answers")), 1)


class RechtschreibungTest(unittest.TestCase):
    def test_hunspell(self):
        if not shutil.which("hunspell"):
            self.skipTest("hunspell nicht installiert")
        probe = subprocess.run(["hunspell", "-D"], input="", capture_output=True, text=True)
        if "de_DE" not in (probe.stdout + probe.stderr):
            self.skipTest("hunspell-Woerterbuch de_DE fehlt")
        _, ausnahmen, bekannt = lade_wortliste()
        woerter = set()
        for _, _, s in json_texte():
            for stelle in ausnahmen:
                s = s.replace(stelle, " ")
            s = re.sub(r"\{[^}]*\}", " ", s)
            s = re.sub(r"%\(?[a-z_]*\)?[sdf]", " ", s)
            s = re.sub(r"https?://\S+", " ", s)
            s = re.sub(r"[\w.+-]+@[\w-]+\.\w+", " ", s)
            for w in WORT.findall(s):
                w = w.strip("-")
                if len(w) >= 2:
                    woerter.add(w)

        def unbekannt(liste):
            aus = subprocess.run(["hunspell", "-d", "de_DE", "-i", "utf-8", "-l"], input="\n".join(sorted(liste)),
                                 capture_output=True, text=True, encoding="utf-8").stdout
            return set(aus.split())

        falsch = unbekannt(woerter)
        teile = {p for w in falsch if "-" in w for p in w.split("-") if p}
        falsch_teile = unbekannt(teile) if teile else set()

        def ok(w):
            if w in bekannt:
                return True
            if "-" in w and all(p in bekannt or p not in falsch_teile for p in w.split("-") if p):
                return True
            return w.endswith("s") and w[:-1] in bekannt

        rest = sorted(w for w in falsch if not ok(w))
        self.assertEqual(rest, [], "Unbekannte Woerter (Tippfehler oder in [bekannt] eintragen): "
                         + ", ".join(rest[:50]))


if __name__ == "__main__":
    unittest.main()
