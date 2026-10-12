#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test fuer B-G-22 (ab 0.62.5, Gruppe 5.4): Haengt die Namensaufloesung (DNS),
meldet der Abgleich nach hoechstens ca. TIMEOUT (15 s) "Keine Verbindung"
statt erst nach dem Ende der Namensaufloesung (gemessen 25 s).

Nachstellung: socket.getaddrinfo haengt fuer einen Namen, der nie aufgeloest
wird (".invalid"), 25 s und scheitert dann - wie ein DNS ohne Antwort. Keine
Verbindung nach aussen, Wegwerf-HOME und -Datenbank. Proxy-Variablen werden
fuer diesen Prozess entfernt (mit Proxy loest der Proxy die Namen auf).

Gegenprobe gegen einen anderen Stand (v0.62.3: test_dns_haengt rot, ca. 25 s):
    ABGLEICH_CODE=<ordner mit dem Code> python test_abgleich_dns.py
Start:  python test_abgleich_dns.py   (dauert ca. 20 s)
"""

import os
import shutil
import socket
import sys
import tempfile
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
CODE = os.path.abspath(os.environ.get("ABGLEICH_CODE") or HERE)
WORK = tempfile.mkdtemp(prefix="fisi_dns_")
os.environ["HOME"] = WORK
os.environ["FISI_DB_PATH"] = os.path.join(WORK, "lern.db")
for _name in list(os.environ):
    if _name.lower() in ("http_proxy", "https_proxy", "all_proxy", "no_proxy"):
        del os.environ[_name]

sys.path.insert(0, os.path.join(HERE, "pruefung"))
import abgleich_attrappe as att  # noqa: E402

sys.path.insert(0, CODE)
import fisi_core  # noqa: E402
import fisi_sync  # noqa: E402

HANGING_HOST = "abgleich-dns-haengt.invalid"
HANG_SECONDS = 25
_real_getaddrinfo = socket.getaddrinfo


def _getaddrinfo(host, *args, **kwargs):
    if host == HANGING_HOST:
        time.sleep(HANG_SECONDS)
        raise socket.gaierror(socket.EAI_AGAIN, "Temporary failure in name resolution")
    return _real_getaddrinfo(host, *args, **kwargs)


socket.getaddrinfo = _getaddrinfo
fisi_sync.save_sync_settings(sync_repo="pruef/lernstand-attrappe",
                             sync_token="PLATZHALTER-KEIN-ECHTES-TOKEN")


def tearDownModule():
    shutil.rmtree(WORK, ignore_errors=True)


class DnsTest(unittest.TestCase):

    def test_dns_haengt(self):
        """Namensaufloesung haengt 25 s: Meldung nach hoechstens ca. 16 s."""
        self.assertEqual(fisi_sync.TIMEOUT, 15)
        fisi_sync.API = "https://%s" % HANGING_HOST
        db = fisi_core.DBManager(db_path=os.path.join(WORK, "a.db"),
                                 error_handler=lambda message: None)
        start = time.monotonic()
        with self.assertRaises(fisi_sync.SyncError) as caught:
            fisi_sync.sync(db, device="Test")
        took = time.monotonic() - start
        print("  [Beleg] nach %.1f s: %s" % (took, caught.exception), flush=True)
        self.assertIn("Keine Verbindung zu GitHub", str(caught.exception))
        self.assertLessEqual(took, 16.5)

    def test_schutz_normaler_abgleich(self):
        """Schutz (auch auf v0.62.3 gruen): ohne Haenger gleicht es wie bisher ab."""
        server, port = att.start_server()
        try:
            fisi_sync.API = "http://127.0.0.1:%d" % port
            db = fisi_core.DBManager(db_path=os.path.join(WORK, "b.db"),
                                     error_handler=lambda message: None)
            db.log_quiz_answer(fisi_core.CATEGORIES[2], "Frage", True)
            start = time.monotonic()
            result = fisi_sync.sync(db, device="Test")
            self.assertEqual(result.sent, 1)
            self.assertLess(time.monotonic() - start, 5)
        finally:
            server.shutdown()


if __name__ == "__main__":
    print("Code-Stand: %s" % CODE, flush=True)
    unittest.main(verbosity=2)
