#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests ab 0.62.5 (Gruppe 5.10 Haertung Bau):

  B-B-07  MD5 in fisi_lernen.py und fisi_rahmenplan.py nur fuer Reihenfolge
          und Tageszufall: ab Python 3.9 mit usedforsecurity=False, fuer
          Python 3.8 (start.py MIN_PYTHON) eine Weiche ohne den Zusatz, mit
          "nosec B324". Ist bandit installiert, meldet es 0 x "hoch".
          Schutz-Test: Reihenfolge und Tageszufall sind dieselben Zahlen wie
          in v0.62.3 (auch auf v0.62.3 gruen).
  B-B-08  Sperrdatei gegen Mehrfachstart (fisi_einzelstart._try_lock) mit
          encoding="utf-8" geoeffnet.

Fuer die Rot-Probe kann der Code-Ordner umgestellt werden:
    HAERTUNG_CODE=<ordner mit dem Code> python test_haertung_bau.py

Start:  python test_haertung_bau.py
"""

import ast
import datetime
import os
import shutil
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
CODE = os.path.abspath(os.environ.get("HAERTUNG_CODE") or HERE)
sys.path.insert(0, CODE)

MD5_FILES = ("fisi_lernen.py", "fisi_rahmenplan.py")


def _tree(name):
    with open(os.path.join(CODE, name), encoding="utf-8") as handle:
        source = handle.read()
    return source, ast.parse(source)


def _is_md5(node):
    func = node.func
    return isinstance(func, ast.Attribute) and func.attr == "md5" and \
        isinstance(func.value, ast.Name) and func.value.id == "hashlib"


def _py38_branches(tree):
    """Zeilen der else-Zweige von 'if sys.version_info >= (3, 9):'."""
    lines = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.If) and node.orelse and \
                ast.unparse(node.test).replace(" ", "") == "sys.version_info>=(3,9)":
            for child in node.orelse:
                for sub in ast.walk(child):
                    if hasattr(sub, "lineno"):
                        lines.add(sub.lineno)
    return lines


class MD5Test(unittest.TestCase):
    """B-B-07"""

    def test_md5_nur_ohne_sicherheitszweck(self):
        for name in MD5_FILES:
            source, tree = _tree(name)
            lines = source.splitlines()
            old_branch = _py38_branches(tree)
            calls = [node for node in ast.walk(tree)
                     if isinstance(node, ast.Call) and _is_md5(node)]
            self.assertTrue(calls, name)
            modern = 0
            for call in calls:
                keywords = {kw.arg: kw.value for kw in call.keywords}
                where = "%s:%d" % (name, call.lineno)
                if call.lineno in old_branch:
                    # Python 3.8: ohne Zusatz, aber als Ausnahme gekennzeichnet
                    self.assertEqual(keywords, {}, where)
                    self.assertIn("nosec B324", lines[call.lineno - 1], where)
                else:
                    self.assertIn("usedforsecurity", keywords, where)
                    value = keywords["usedforsecurity"]
                    self.assertIsInstance(value, ast.Constant, where)
                    self.assertIs(value.value, False, where)
                    modern += 1
            self.assertEqual(modern, 1, name)

    def test_bandit_kein_hoch(self):
        bandit = shutil.which("bandit") or os.path.join(os.path.dirname(sys.executable),
                                                        "bandit")
        if not os.path.exists(bandit):
            self.skipTest("bandit nicht installiert (Pruefung nur lokal)")
        out = subprocess.run([bandit, "-q", "-lll", "-f", "txt"] +
                             [os.path.join(CODE, name) for name in MD5_FILES],
                             capture_output=True, text=True)
        self.assertNotIn("B324", out.stdout, out.stdout)
        self.assertNotIn("Severity: High", out.stdout, out.stdout)

    def test_weiche_python38(self):
        """Python 3.8 nachgestellt: version_info = 3.8 und ein hashlib.md5,
        das usedforsecurity nicht kennt (wie 3.8). Die Module laden, _md5
        liefert dieselben Werte und uebergibt den Zusatz nicht."""
        import hashlib
        import importlib.util
        real_info, real_md5 = sys.version_info, hashlib.md5
        seen = []

        def md5_38(data=b"", **kwargs):
            seen.append(kwargs)
            if kwargs:
                raise TypeError("md5() takes no keyword arguments (Python 3.8)")
            return real_md5(data)

        for info, expect_kwargs in (((3, 8, 20, "final", 0), {}),
                                    (real_info, {"usedforsecurity": False})):
            for name in MD5_FILES:
                seen.clear()
                try:
                    sys.version_info = info
                    spec = importlib.util.spec_from_file_location(
                        "_weiche_" + name[:-3], os.path.join(CODE, name))
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                finally:
                    sys.version_info = real_info
                try:
                    hashlib.md5 = md5_38 if not expect_kwargs else \
                        (lambda data=b"", **kw: (seen.append(kw), real_md5(data))[1])
                    digest = module._md5(b"fisi").hexdigest()
                finally:
                    hashlib.md5 = real_md5
                self.assertEqual(digest, real_md5(b"fisi").hexdigest(), name)
                self.assertEqual(seen, [expect_kwargs], (name, info[:2]))

    def test_reihenfolge_wie_v0623(self):
        """Schutz-Test (auch auf v0.62.3 gruen): gleiche Zahlen wie vorher."""
        import fisi_lernen
        import fisi_rahmenplan
        self.assertEqual(fisi_lernen._stable_rank("quiz", "Frage 1"),
                         "91accff755c07f69ad31a4c1428a7853")
        self.assertEqual(fisi_lernen._stable_rank("card", "Ä Karte ß"),
                         "1b8136967176ad82daf8309bdbf28d99")
        self.assertEqual(fisi_lernen._stable_rank("", ""),
                         "b99834bc19bbad24580b3adfa04fb947")
        self.assertEqual(fisi_lernen._stable_rank("kk", 42),
                         "eac8444f3bd25e2c892d96b465e827fb")
        self.assertEqual(fisi_rahmenplan._day_random(
            "quiz", "Frage 1", datetime.date(2026, 10, 12)), 0.9145504802461517)
        self.assertEqual(fisi_rahmenplan._day_random(
            "card", "Ä Karte ß", datetime.date(2024, 2, 29)), 0.7150015690346315)
        self.assertEqual(fisi_rahmenplan._day_random(
            "", "", datetime.date(2000, 1, 1)), 0.33662813906273986)


class SperrdateiTest(unittest.TestCase):
    """B-B-08"""

    def test_sperrdatei_mit_encoding(self):
        _source, tree = _tree("fisi_einzelstart.py")
        func = next(node for node in ast.walk(tree)
                    if isinstance(node, ast.FunctionDef) and node.name == "_try_lock")
        opens = [node for node in ast.walk(func) if isinstance(node, ast.Call)
                 and isinstance(node.func, ast.Name) and node.func.id == "open"]
        self.assertEqual(len(opens), 1)
        keywords = {kw.arg: kw.value for kw in opens[0].keywords}
        self.assertIn("encoding", keywords, "fisi_einzelstart.py:%d" % opens[0].lineno)
        self.assertEqual(keywords["encoding"].value, "utf-8")


if __name__ == "__main__":
    unittest.main(verbosity=2)
