#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests fuer 0.63.2, FG-96: Aufteilung der Linux-Testteile in der CI.

  * Jede Testdatei test_*.py liegt in GENAU EINEM der Linux-Teile
    spiel, lang, breite, rest (keine doppelt, keine in keinem Teil).
  * Teil "breite" enthaelt genau die drei Breitentests (soweit im Stand),
    keiner davon laeuft zusaetzlich in "rest".
  * Eine neue Testdatei landet weiter automatisch in "rest"; kommt
    test_spiel_breite_0632.py dazu (N5), landet sie in "breite".
  * build.yml: Matrix der Linux-Tests ist [spiel, lang, breite, rest], ohne
    Teil ibus (FG-94, Weg c: ibus nur im Container).

Die Zuordnung wird nicht nachgebaut, sondern durch einen echten Aufruf von
pruefung/ci_tests.sh ermittelt, mit einem Ersatz-Python (PYTHON=true), das
nichts ausfuehrt. ci_tests.sh selbst bleibt unveraendert.

Start:  python test_ci_teile_0632.py
"""

import glob
import os
import re
import shutil
import subprocess
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
CI_TESTS = os.path.join(HERE, "pruefung", "ci_tests.sh")
BUILD = os.path.join(HERE, ".github", "workflows", "build.yml")

TEILE = ("spiel", "lang", "breite", "rest")
BREITE = {"test_spiel_breite_0632.py", "test_ansichten_breite.py",
          "test_rechner_seite_breite.py"}
# im Stand e0f9c7e vorhanden; test_spiel_breite_0632.py kommt mit N5
BREITE_PFLICHT = {"test_ansichten_breite.py", "test_rechner_seite_breite.py"}


def _bash():
    return shutil.which("bash") or "/bin/bash"


def _teil_dateien(ordner, teil):
    """Dateien, die ci_tests.sh TEIL im Ordner ausfuehren wuerde (Reihenfolge)."""
    env = dict(os.environ)
    env["PYTHON"] = "true"               # fuehrt nichts aus, Rueckgabe 0
    env["DISPLAY"] = ":fg96-keine-anzeige"  # keine eigene Xvfb starten
    env.pop("GITHUB_STEP_SUMMARY", None)
    lauf = subprocess.run([_bash(), os.path.join(ordner, "pruefung", "ci_tests.sh"), teil],
                          cwd=ordner, env=env, capture_output=True, text=True,
                          timeout=120)
    if lauf.returncode != 0:
        raise AssertionError("ci_tests.sh %s: Rueckgabe %s\n%s%s"
                             % (teil, lauf.returncode, lauf.stdout, lauf.stderr))
    return re.findall(r"^OK   (\S+) \(", lauf.stdout, re.M)


def _zuordnung(ordner):
    return {teil: _teil_dateien(ordner, teil) for teil in TEILE}


def _kopie(namen):
    """Ordner mit ci_tests.sh und leeren Testdateien der angegebenen Namen."""
    ordner = tempfile.mkdtemp(prefix="fg96_")
    os.makedirs(os.path.join(ordner, "pruefung"))
    shutil.copy(CI_TESTS, os.path.join(ordner, "pruefung", "ci_tests.sh"))
    for name in namen:
        open(os.path.join(ordner, name), "w").close()
    return ordner


def _genau_ein_teil(test, zuordnung, alle):
    gesehen = {}
    for teil, dateien in zuordnung.items():
        test.assertEqual(len(dateien), len(set(dateien)), "doppelt in %s" % teil)
        for datei in dateien:
            gesehen.setdefault(datei, []).append(teil)
    doppelt = {d: t for d, t in gesehen.items() if len(t) != 1}
    test.assertEqual(doppelt, {}, "Datei in mehr als einem Teil")
    test.assertEqual(sorted(set(alle) - set(gesehen)), [], "Datei in keinem Teil")
    test.assertEqual(sorted(set(gesehen) - set(alle)), [], "Teil nennt fremde Datei")


class GenauEinTeilTest(unittest.TestCase):

    def test_jede_testdatei_in_genau_einem_teil(self):
        alle = sorted(os.path.basename(p) for p in glob.glob(os.path.join(HERE, "test_*.py")))
        self.assertIn("test_ci_teile_0632.py", alle)
        _genau_ein_teil(self, _zuordnung(HERE), alle)

    def test_teil_breite_genau_die_breitentests(self):
        zuordnung = _zuordnung(HERE)
        vorhanden = {d for d in BREITE if os.path.exists(os.path.join(HERE, d))}
        self.assertTrue(BREITE_PFLICHT <= vorhanden, "Breitentest fehlt im Stand")
        self.assertEqual(set(zuordnung["breite"]), vorhanden)
        for datei in BREITE:
            self.assertNotIn(datei, zuordnung["rest"])
        # andere Teile unveraendert
        self.assertEqual(zuordnung["spiel"], ["test_spiel.py"])
        self.assertEqual(zuordnung["lang"], ["test_beenden.py", "test_leistung.py",
                                             "test_grosse_datenmengen.py", "test_vorladen.py"])

    def test_n5_datei_landet_in_breite_neue_datei_in_rest(self):
        # Nachstellung des Stands nach dem N5-Merge plus einer ganz neuen Datei
        alle = sorted({os.path.basename(p) for p in glob.glob(os.path.join(HERE, "test_*.py"))}
                      | BREITE | {"test_fg96_neu_nachgestellt.py"})
        ordner = _kopie(alle)
        try:
            zuordnung = _zuordnung(ordner)
        finally:
            shutil.rmtree(ordner, ignore_errors=True)
        _genau_ein_teil(self, zuordnung, alle)
        self.assertEqual(set(zuordnung["breite"]), BREITE)
        self.assertIn("test_fg96_neu_nachgestellt.py", zuordnung["rest"])
        self.assertNotIn("test_spiel_breite_0632.py", zuordnung["rest"])


class MatrixTest(unittest.TestCase):

    def _tests_job(self):
        with open(BUILD, encoding="utf-8") as fh:
            zeilen = fh.read().splitlines()
        start = zeilen.index("  tests:")
        job = []
        for zeile in zeilen[start + 1:]:
            if re.match(r"^  \S", zeile) or re.match(r"^\S", zeile):
                break
            job.append(zeile)
        return job

    def test_matrix_spiel_lang_breite_rest(self):
        job = self._tests_job()
        matrix = [z for z in job if z.strip().startswith("teil:")]
        self.assertEqual(matrix, ["        teil: [spiel, lang, breite, rest]"])

    def test_matrix_ohne_teil_ibus(self):
        # FG-94, Weg c: Teil ibus laeuft nur im Container, nicht auf GitHub
        self.assertNotIn("ibus", "\n".join(z for z in self._tests_job()
                                            if not z.lstrip().startswith("#")))

    def test_jeder_matrix_teil_in_ci_tests(self):
        with open(CI_TESTS, encoding="utf-8") as fh:
            text = fh.read()
        for teil in TEILE:
            self.assertRegex(text, r"\n  %s\)" % teil, teil)


if __name__ == "__main__":
    unittest.main()
