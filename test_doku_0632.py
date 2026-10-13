#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests fuer 0.63.2, Strang S5a: Doku-Befunde (Plan 5.9) und A11 (Attrappe).

  Attrappe   A11: put_status_n in pruefung/abgleich_attrappe.py nur unter
             STATE.lock herunterzaehlen (gleichzeitige PUTs)

Nur lesend gegen die Programmdateien (LIESMICH.txt, fisi_hilfe.py,
fisi_diagnose.py, ...). Tk-Teile brauchen eine Anzeige (xvfb-run), ohne
Anzeige werden sie uebersprungen. Keine echten Daten: Wegwerf-HOME und
-Datenbank in einem Temp-Ordner (FISI_DB_PATH).

Start:  xvfb-run -a python test_doku_0632.py
"""

import ast
import json
import os
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
WORK = tempfile.mkdtemp(prefix="fisi_doku0632_")
HOME = os.path.join(WORK, "home")
os.makedirs(HOME, exist_ok=True)
os.environ["HOME"] = HOME
os.environ["FISI_DB_PATH"] = os.path.join(HOME, "lern.db")

sys.path.insert(0, os.path.join(HERE, "pruefung"))
sys.path.insert(0, HERE)


def lesen(name):
    with open(os.path.join(HERE, name), encoding="utf-8") as f:
        return f.read()


# ---------------------------------------------------------------- A11 ---

def _with_lock(node):
    """True, wenn node ein 'with STATE.lock:'-Block ist."""
    if not isinstance(node, ast.With):
        return False
    for item in node.items:
        expr = item.context_expr
        if isinstance(expr, ast.Attribute) and expr.attr == "lock" \
                and isinstance(expr.value, ast.Name) and expr.value.id == "STATE":
            return True
    return False


def _walk_mit_sperre(node, in_lock=False):
    """(knoten, liegt_unter_STATE.lock) fuer alle Knoten unter node."""
    for child in ast.iter_child_nodes(node):
        lock = in_lock or _with_lock(child)
        yield child, lock
        yield from _walk_mit_sperre(child, lock)


class Attrappe(unittest.TestCase):
    """A11: put_status_n nur unter STATE.lock lesen und herunterzaehlen."""

    def _do_put(self):
        tree = ast.parse(lesen(os.path.join("pruefung", "abgleich_attrappe.py")))
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == "Handler":
                for f in node.body:
                    if isinstance(f, ast.FunctionDef) and f.name == "do_PUT":
                        return f
        self.fail("Handler.do_PUT nicht gefunden")

    def test_put_status_n_unter_sperre(self):
        """Lesen und Schreiben von put_status_n liegt in 'with STATE.lock'."""
        zugriffe = []
        for node, lock in _walk_mit_sperre(self._do_put()):
            if isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant) \
                    and node.slice.value == "put_status_n":
                zugriffe.append((node.lineno, "Schreiben", lock))
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
                    and node.func.attr == "get" and node.args \
                    and isinstance(node.args[0], ast.Constant) \
                    and node.args[0].value in ("put_status", "put_status_n"):
                zugriffe.append((node.lineno, "Lesen " + node.args[0].value, lock))
        self.assertTrue(any(z[1] == "Schreiben" for z in zugriffe), zugriffe)
        ohne = [z for z in zugriffe if not z[2]]
        self.assertEqual(ohne, [], "ohne STATE.lock: %r" % ohne)

    def test_kein_schlafen_und_keine_antwort_unter_sperre(self):
        """Schutz: put_hang (sleep 600) und die Antwort nie unter der Sperre,
        sonst blockiert ein haengender PUT alle anderen Anfragen."""
        schlecht = []
        for node, lock in _walk_mit_sperre(self._do_put()):
            if lock and isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
                    and node.func.attr in ("sleep", "_json", "_send"):
                schlecht.append((node.lineno, node.func.attr))
        self.assertEqual(schlecht, [])

    def test_gleichzeitige_puts_genau_n_mal(self):
        """Schutz/Verhalten: 40 gleichzeitige PUTs, put_status=500,
        put_status_n=10 -> genau 10 x 500 (auch auf 14b3bd4 meist gruen,
        das Rennen ist mit GIL selten; das Rot belegt der AST-Test)."""
        import abgleich_attrappe as att
        from http.server import ThreadingHTTPServer

        class Server(ThreadingHTTPServer):
            request_queue_size = 128   # 40 Verbindungen auf einmal annehmen
            daemon_threads = True

        server = Server(("127.0.0.1", 0), att.Handler)
        port = server.server_address[1]
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            base = "http://127.0.0.1:%d" % port

            def post(obj):
                req = urllib.request.Request(base + "/_ctl", data=json.dumps(obj).encode(),
                                             method="POST")
                urllib.request.urlopen(req, timeout=10).read()

            post({"reset": True})
            post({"put_status": 500, "put_status_n": 10})
            codes = []
            sperre = threading.Lock()
            start = threading.Event()

            def put():
                body = json.dumps({"message": "t", "content": "eA=="}).encode()
                req = urllib.request.Request(
                    base + "/repos/o/r/contents/lernstand.json.gz", data=body, method="PUT",
                    headers={"Authorization": "Bearer x"})
                start.wait(10)
                try:
                    code = urllib.request.urlopen(req, timeout=20).status
                except urllib.error.HTTPError as e:
                    code = e.code
                except Exception as e:  # Verbindungsfehler sichtbar machen
                    code = repr(e)
                with sperre:
                    codes.append(code)

            alt = sys.getswitchinterval()
            sys.setswitchinterval(1e-6)
            try:
                threads = [threading.Thread(target=put) for _ in range(40)]
                for t in threads:
                    t.start()
                start.set()
                for t in threads:
                    t.join(30)
            finally:
                sys.setswitchinterval(alt)
            self.assertEqual(len(codes), 40)
            self.assertTrue(all(isinstance(c, int) for c in codes), codes)
            self.assertEqual(codes.count(500), 10, codes)
            with att.STATE.lock:
                self.assertEqual(att.STATE.ctl.get("put_status_n"), 0)
        finally:
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
