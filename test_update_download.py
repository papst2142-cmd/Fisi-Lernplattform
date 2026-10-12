#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests fuer den Download und das AppImage-Update (ab 0.62.5) - ohne echtes
GitHub: Ein lokaler HTTP-Server auf 127.0.0.1 spielt die GitHub-Antwort und
die Release-Dateien (Attrappen). Nichts wird aus dem Internet geladen.

  * Download: Erfolg, falsche Groesse, Abbruch (mit Laengenangabe und
    chunked), HTTP 404, Zeitueberschreitung, keine Verbindung - immer ein
    deutscher Text und keine liegengebliebene .part-Datei; alte Installer
    werden beim naechsten Download aufgeraeumt (B-A-03, B-H-03, B-H-04, B-H-05)
  * Pruefsumme (SHA-256, Feld "digest" der GitHub-Antwort): falsche wird
    abgelehnt; fehlt sie, steht das in update.log (B-B-01)
  * Ungewohnte Antwortform (Liste, assets: null): deutscher Text (B-H-07)
  * AppImage: Download in den Ordner der AppImage, auch wenn der Temp-Ordner
    ein anderes Laufwerk ist (B-H-01); startet die neue Fassung nicht, kommt
    die alte zurueck und startet (B-H-02)
  * einstellungen.json nur fuer das eigene Konto lesbar (0600, Linux) - nur
    mit Platzhalterwert (B-B-04/B-L-05); kaputte Datei: einmal eine Meldung
    am PC und am Handy mit demselben Text (B-G-13)
  * Fenster "Update verfuegbar": installiert, aber keine Datei im Release
    -> eigener Satz (B-H-06)

Code-Ordner: UPDATE_CODE=<ordner> (Vorgabe: dieser Ordner), damit derselbe
Test gegen einen aelteren Stand laufen kann (Rot-Probe).

Start:  python test_update_download.py
"""

import hashlib
import http.server
import json
import os
import shutil
import socket
import stat
import sys
import tempfile
import threading
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
CODE = os.path.abspath(os.environ.get("UPDATE_CODE") or HERE)
sys.path.insert(0, CODE)

# Nur der lokale Server - nie ueber einen Proxy ins Netz
for _var in ("http_proxy", "HTTP_PROXY", "https_proxy", "HTTPS_PROXY",
             "all_proxy", "ALL_PROXY"):
    os.environ.pop(_var, None)
os.environ["no_proxy"] = "127.0.0.1,localhost"
os.environ["NO_PROXY"] = "127.0.0.1,localhost"

_TMP = tempfile.mkdtemp(prefix="fisi_update_download_")
os.environ["FISI_DB_PATH"] = os.path.join(_TMP, "start.db")
os.environ.setdefault("FISI_SELFTEST", os.path.join(_TMP, "selbsttest.log"))

import fisi_update as fu  # noqa: E402

PLACEHOLDER_TOKEN = "PLATZHALTER-KEIN-ECHTER-TOKEN"
PAYLOAD = bytes(range(256)) * 4096          # 1 MiB "Installer"
NAME = "FISI-Lernplattform-Setup-0.63.exe"
ENGLISH = ("Error", "Not Found", "timed out", "refused", "Errno", "urlopen",
           "IncompleteRead", "object", "Unerwarteter")


def _sha(data):
    return "sha256:" + hashlib.sha256(data).hexdigest()


# ---------------------------------------------------------------------------
#  Lokaler Server (Attrappe fuer GitHub und die Release-Dateien)
# ---------------------------------------------------------------------------

STATE = {"release": {}, "app": b""}


class Handler(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *args):
        pass

    def _send(self, code, body):
        self.send_response(code)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _abort(self, headers, data):
        self.send_response(200)
        for key, value in headers.items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(data)
        self.wfile.flush()
        self.connection.shutdown(socket.SHUT_RDWR)
        self.close_connection = True

    def do_GET(self):
        path = self.path
        if path == "/latest":
            return self._send(200, json.dumps(STATE["release"]).encode())
        if path == "/latest/list":
            return self._send(200, b"[]")
        if path == "/asset/ok":
            return self._send(200, PAYLOAD)
        if path == "/asset/app":
            return self._send(200, STATE["app"])
        if path == "/asset/bigger":
            return self._send(200, PAYLOAD + b"x" * 10)
        if path == "/asset/404":
            return self._send(404, b'{"message":"Not Found"}')
        if path == "/asset/short":       # Laenge angekuendigt, halbe Datei
            return self._abort({"Content-Length": str(len(PAYLOAD))},
                               PAYLOAD[:len(PAYLOAD) // 2])
        if path == "/asset/chunkabort":  # chunked, bricht mitten im Block ab
            return self._abort({"Transfer-Encoding": "chunked"},
                               b"100000\r\n" + PAYLOAD[:300000])
        if path == "/asset/stall":       # Anfang, dann Stille (> timeout)
            self.send_response(200)
            self.send_header("Content-Length", str(len(PAYLOAD)))
            self.end_headers()
            self.wfile.write(PAYLOAD[:1000])
            self.wfile.flush()
            time.sleep(3)
            self.close_connection = True
            return
        self._send(404, b"?")


SERVER = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
SERVER.daemon_threads = True
threading.Thread(target=SERVER.serve_forever, daemon=True).start()
BASE = "http://127.0.0.1:%d" % SERVER.server_address[1]


def _closed_port():
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


class TempMixin:
    """Eigener Datenordner und eigener Temp-Ordner je Test."""

    def setUp(self):
        self.folder = tempfile.mkdtemp(prefix="fisi update Ä ", dir=_TMP)
        self.data = os.path.join(self.folder, "Daten")
        os.makedirs(self.data)
        os.environ["FISI_DB_PATH"] = os.path.join(self.data, "fisi.db")
        self._tempdir = tempfile.tempdir
        tempfile.tempdir = os.path.join(self.folder, "tmp")
        os.makedirs(tempfile.tempdir)
        self._kind = fu.install_kind

    def tearDown(self):
        fu.install_kind = self._kind
        tempfile.tempdir = self._tempdir
        shutil.rmtree(self.folder, ignore_errors=True)

    def update_folder(self):
        return os.path.join(tempfile.gettempdir(), "FISI-Lernplattform-Update")

    def leftovers(self, folder=None):
        folder = folder or self.update_folder()
        if not os.path.isdir(folder):
            return []
        return sorted(os.listdir(folder))

    def log_text(self):
        return fu.read_update_log()

    def info(self, path, size=len(PAYLOAD), name=NAME):
        return fu.UpdateInfo("0.63", "", "p", asset_name=name,
                             asset_url=BASE + path, asset_size=size)

    def assert_german_error(self, info, *expected, timeout=30):
        with self.assertRaises(fu.UpdateError) as caught:
            fu.download(info, timeout=timeout)
        text = str(caught.exception)
        for part in expected:
            self.assertIn(part, text)
        for word in ENGLISH:
            self.assertNotIn(word, text)
        return text


# ---------------------------------------------------------------------------
#  Download (B-A-03, B-H-03, B-H-04, B-H-05)
# ---------------------------------------------------------------------------

class DownloadTest(TempMixin, unittest.TestCase):
    def test_erfolg(self):
        # Schutz-Test: auf v0.62.3 schon gruen
        calls = []
        path = fu.download(self.info("/asset/ok"), lambda a, b: calls.append((a, b)))
        with open(path, "rb") as handle:
            self.assertEqual(handle.read(), PAYLOAD)
        self.assertEqual(calls[-1], (len(PAYLOAD), len(PAYLOAD)))
        self.assertEqual(self.leftovers(), [NAME])
        self.assertIn("Download fertig", self.log_text())

    def test_falsche_groesse_abgelehnt(self):
        # Schutz-Test (Gegenprobe "Groesse nicht pruefen"): auf v0.62.3 gruen
        self.assert_german_error(self.info("/asset/bigger"), "unvollständig")
        self.assertEqual(self.leftovers(), [])

    def test_abbruch_halbe_datei(self):
        self.assert_german_error(self.info("/asset/short"), "unvollständig")
        self.assertEqual(self.leftovers(), [])

    def test_abbruch_chunked(self):
        # B-H-03: ohne Laengenangabe (Proxy, Virenscanner) bricht die Verbindung ab
        self.assert_german_error(self.info("/asset/chunkabort", size=0), "unvollständig")
        self.assertEqual(self.leftovers(), [])

    def test_http_404(self):
        self.assert_german_error(self.info("/asset/404"), "HTTP 404")
        self.assertEqual(self.leftovers(), [])
        self.assertIn("404", self.log_text())   # Technik nur im Protokoll

    def test_zeitueberschreitung(self):
        # B-H-04/B-H-05: keine .part-Datei, deutscher Text
        self.assert_german_error(self.info("/asset/stall"), "zu lange", timeout=1)
        self.assertEqual(self.leftovers(), [])

    def test_keine_verbindung(self):
        info = fu.UpdateInfo("0.63", "", "p", asset_name=NAME,
                             asset_url="http://127.0.0.1:%d/x" % _closed_port(),
                             asset_size=5)
        self.assert_german_error(info, "Keine Verbindung")
        self.assertEqual(self.leftovers(), [])

    def test_alte_installer_werden_aufgeraeumt(self):
        os.makedirs(self.update_folder())
        for name in ("FISI-Lernplattform-Setup-0.61.exe",
                     "FISI-Lernplattform-Setup-0.62.exe.part"):
            with open(os.path.join(self.update_folder(), name), "wb") as handle:
                handle.write(b"alt" * 1000)
        fu.download(self.info("/asset/ok"))
        self.assertEqual(self.leftovers(), [NAME])


# ---------------------------------------------------------------------------
#  Pruefsumme (B-B-01) und Antwortform (B-H-07)
# ---------------------------------------------------------------------------

def _release(assets):
    return {"tag_name": "v0.63", "body": "Neu", "html_url": "http://x/page",
            "prerelease": False, "draft": False, "assets": assets}


class PruefsummeTest(TempMixin, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self._url = fu.LATEST_URL
        fu.LATEST_URL = BASE + "/latest"

    def tearDown(self):
        fu.LATEST_URL = self._url
        super().tearDown()

    def _info(self, digest):
        asset = {"name": NAME, "browser_download_url": BASE + "/asset/ok",
                 "size": len(PAYLOAD)}
        if digest is not None:
            asset["digest"] = digest
        STATE["release"] = _release([asset])
        return fu.check_for_update("0.62.5", kind="windows")

    def test_digest_aus_der_github_antwort(self):
        info = self._info(_sha(PAYLOAD))
        self.assertEqual(getattr(info, "asset_digest", None), _sha(PAYLOAD))

    def test_falsche_pruefsumme_abgelehnt(self):
        info = self._info(_sha(b"etwas anderes"))
        info.asset_digest = _sha(b"etwas anderes")   # auch fuer alte Staende
        text = self.assert_german_error(info, "Prüfsumme")
        self.assertIn("beschädigt", text)
        self.assertEqual(self.leftovers(), [])
        self.assertIn("Prüfsumme", self.log_text())

    def test_richtige_pruefsumme(self):
        info = self._info(_sha(PAYLOAD))
        path = fu.download(info)
        self.assertTrue(os.path.exists(path))
        self.assertIn("Prüfsumme geprüft", self.log_text())

    def test_ohne_pruefsumme_nur_groesse_und_protokoll(self):
        info = self._info(None)
        fu.download(info)
        self.assertIn("keine Prüfsumme", self.log_text())


class AntwortformTest(TempMixin, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self._url = fu.LATEST_URL

    def tearDown(self):
        fu.LATEST_URL = self._url
        super().tearDown()

    def _check(self):
        with self.assertRaises(fu.UpdateError) as caught:
            fu.check_for_update("0.62.5", kind="windows")
        self.assertIn("Die Antwort von GitHub ist unerwartet", str(caught.exception))

    def test_liste_statt_objekt(self):
        fu.LATEST_URL = BASE + "/latest/list"
        self._check()

    def test_assets_null(self):
        fu.LATEST_URL = BASE + "/latest"
        STATE["release"] = _release(None)
        self._check()

    def test_assets_fehlt_wie_bisher(self):
        # Schutz-Test: fehlt das Feld ganz, gibt es eben keine Datei
        fu.LATEST_URL = BASE + "/latest"
        release = _release([])
        release.pop("assets")
        STATE["release"] = release
        info = fu.check_for_update("0.62.5", kind="windows")
        self.assertEqual(info.version, "0.63")
        self.assertIsNone(info.asset_url)


# ---------------------------------------------------------------------------
#  AppImage (B-H-01, B-H-02)
# ---------------------------------------------------------------------------

OLD_APPIMAGE = b'#!/bin/sh\necho alt >> "$FISI_TEST_MARK/alt_gestartet"\n'
GOOD_NEW = ('#!%s\n'
            'import os, sys\n'
            'sys.path.insert(0, os.environ["FISI_TEST_CODE"])\n'
            'import fisi_update\n'
            'fisi_update.finish_pending_update("0.63")\n'
            'open(os.path.join(os.environ["FISI_TEST_MARK"], "neu_gestartet"), "a").close()\n'
            % sys.executable).encode()
CRASHING_NEW = b"#!/bin/sh\nexit 1\n"
BROKEN_NEW = b"\x7fELF\x00kaputt" + bytes(range(256)) * 64


def _other_device_tmp(than):
    """Ordner auf einem anderen Laufwerk (tmpfs /dev/shm), sonst None."""
    shm = "/dev/shm"
    try:
        if os.stat(shm).st_dev == os.stat(than).st_dev or not os.access(shm, os.W_OK):
            return None
    except OSError:
        return None
    return tempfile.mkdtemp(prefix="fisi_update_tmpfs_", dir=shm)


@unittest.skipIf(sys.platform == "win32", "AppImage nur unter Linux")
class AppImageTest(TempMixin, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.appdir = os.path.join(self.folder, "Anwendungen")
        self.marks = os.path.join(self.folder, "marken")
        os.makedirs(self.appdir)
        os.makedirs(self.marks)
        self.current = os.path.join(self.appdir, "FISI-Lernplattform.AppImage")
        with open(self.current, "wb") as handle:
            handle.write(OLD_APPIMAGE)
        os.chmod(self.current, 0o755)
        self._env = {key: os.environ.get(key)
                     for key in ("APPIMAGE", "FISI_TEST_MARK", "FISI_TEST_CODE")}
        os.environ["APPIMAGE"] = self.current
        os.environ["FISI_TEST_MARK"] = self.marks
        os.environ["FISI_TEST_CODE"] = CODE
        fu.install_kind = lambda: "appimage"
        self.shm = None

    def tearDown(self):
        for key, value in self._env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        if self.shm:
            shutil.rmtree(self.shm, ignore_errors=True)
        super().tearDown()

    def _update(self, payload):
        """Download + Installation wie im Update-Fenster. Liefert (pfad, fehler)."""
        STATE["app"] = payload
        info = fu.UpdateInfo("0.63", "", "p",
                             asset_name="FISI-Lernplattform-0.63-x86_64.AppImage",
                             asset_url=BASE + "/asset/app", asset_size=len(payload))
        path = fu.download(info)
        try:
            quit_now, _text = fu.install(path, kind="appimage", version="0.63")
        except fu.UpdateError as error:
            return path, str(error)
        self.assertTrue(quit_now)
        return path, None

    def _wait_for(self, check, seconds=20):
        end = time.time() + seconds
        while time.time() < end:
            if check():
                return True
            time.sleep(0.05)
        return check()

    def _content(self):
        with open(self.current, "rb") as handle:
            return handle.read()

    def test_download_in_den_ordner_der_appimage(self):
        # B-H-01: Temp-Ordner auf einem anderen Laufwerk (tmpfs), falls vorhanden
        self.shm = _other_device_tmp(self.appdir)
        if self.shm:
            tempfile.tempdir = self.shm
        path, error = self._update(GOOD_NEW)
        self.assertEqual(os.path.dirname(path), self.appdir)
        self.assertIsNone(error)
        self.assertTrue(self._wait_for(
            lambda: os.path.exists(os.path.join(self.marks, "neu_gestartet"))))
        self.assertEqual(self._content(), GOOD_NEW)
        # Die neue Fassung lief: die alte (.alt) ist aufgeraeumt, kein Rueckfall
        self.assertEqual(sorted(os.listdir(self.appdir)), ["FISI-Lernplattform.AppImage"])
        self.assertFalse(os.path.exists(os.path.join(self.marks, "alt_gestartet")))

    def test_tmp_auf_anderem_laufwerk(self):
        self.shm = _other_device_tmp(self.appdir)
        if not self.shm:
            self.skipTest("kein zweites Laufwerk (/dev/shm) verfuegbar")
        tempfile.tempdir = self.shm
        _path, error = self._update(GOOD_NEW)
        self.assertIsNone(error)   # rot auf v0.62.3: "Invalid cross-device link"

    def _assert_old_back(self, error):
        started = self._wait_for(
            lambda: os.path.exists(os.path.join(self.marks, "alt_gestartet")))
        self.assertEqual(self._content(), OLD_APPIMAGE, error)
        self.assertTrue(started, "alte Version wurde nicht wieder gestartet")
        self.assertTrue(os.access(self.current, os.X_OK))
        self.assertEqual(sorted(os.listdir(self.appdir)), ["FISI-Lernplattform.AppImage"])
        self.assertIn("bisherige Version wurde wiederhergestellt", self.log_text())
        # Die alte Version meldet beim Start den Fehlschlag (genau einmal)
        result = fu.finish_pending_update("0.62.5")
        self.assertEqual(result[0], "fehler")
        self.assertIn("ließ sich auf diesem System nicht starten", result[1])
        self.assertIsNone(fu.finish_pending_update("0.62.5"))

    def test_kaputte_appimage_alte_bleibt(self):
        # B-H-02: gleiche Groesse, falscher Inhalt (startet gar nicht)
        _path, error = self._update(BROKEN_NEW)
        self._assert_old_back(error)

    def test_neue_stuerzt_sofort_ab_alte_kommt_zurueck(self):
        # B-H-02: startbar, beendet sich aber sofort mit Fehler
        _path, error = self._update(CRASHING_NEW)
        self._assert_old_back(error)


# ---------------------------------------------------------------------------
#  Einstellungen (B-B-04/B-L-05, B-G-13)
# ---------------------------------------------------------------------------

class EinstellungenTest(TempMixin, unittest.TestCase):
    def path(self):
        return os.path.join(self.data, "einstellungen.json")

    @unittest.skipIf(sys.platform == "win32", "Dateirechte nur unter Linux/macOS")
    def test_nur_fuer_das_eigene_konto(self):
        old = os.umask(0o022)
        try:
            settings = fu.load_settings()
            settings["abgleich"] = {"token": PLACEHOLDER_TOKEN}
            self.assertTrue(fu.save_settings(settings))
            self.assertEqual(stat.S_IMODE(os.stat(self.path()).st_mode), 0o600)
            # Eine schon vorhandene Datei mit 0644 wird beim Speichern 0600
            os.chmod(self.path(), 0o644)
            self.assertTrue(fu.save_settings(settings))
            self.assertEqual(stat.S_IMODE(os.stat(self.path()).st_mode), 0o600)
            self.assertEqual(fu.load_settings()["abgleich"]["token"], PLACEHOLDER_TOKEN)
        finally:
            os.umask(old)

    def _break(self):
        with open(self.path(), "w", encoding="utf-8") as handle:
            handle.write('{"abgleich": {"token": "%s"' % PLACEHOLDER_TOKEN)

    def test_kaputte_datei_eine_meldung(self):
        self._break()
        self.assertTrue(fu.load_settings()["auto_check"])
        notice = fu.broken_settings_notice()
        self.assertIsNotNone(notice)
        title, text = notice
        self.assertEqual(title, "Einstellungen ersetzt")
        self.assertIn("einstellungen.defekt.json", text)
        self.assertIn("ersetzt", text)
        self.assertIsNone(fu.broken_settings_notice())   # nur einmal
        with open(os.path.join(self.data, "einstellungen.defekt.json"),
                  encoding="utf-8") as handle:
            self.assertIn(PLACEHOLDER_TOKEN, handle.read())
        # Die Datei ist jetzt wieder lesbar: beim naechsten Start keine Meldung
        with open(self.path(), encoding="utf-8") as handle:
            self.assertIsInstance(json.load(handle), dict)

    def test_heile_datei_keine_meldung(self):
        fu.save_settings({"auto_check": False})
        fu.load_settings()
        self.assertIsNone(fu.broken_settings_notice())

    def test_pc_zeigt_die_meldung(self):
        import app_gui
        self._break()
        shown = []
        original = app_gui.messagebox.showwarning
        app_gui.messagebox.showwarning = lambda title, text, **kw: shown.append((title, text))
        try:
            fake = type("App", (), {"root": None})()
            app_gui.FISIApp.check_finished_update(fake)
        finally:
            app_gui.messagebox.showwarning = original
        self.assertEqual(len(shown), 1)
        self.assertEqual(shown[0][0], "Einstellungen ersetzt")
        self.assertIn("einstellungen.defekt.json", shown[0][1])

    def test_handy_zeigt_dieselbe_meldung(self):
        import importlib.util
        if importlib.util.find_spec("flet") is None:
            self.skipTest("flet fehlt")
        sys.path.insert(1, os.path.join(CODE, "mobile", "src"))
        import main as handy

        class FakeApp(handy.FISIMobileApp):
            def __init__(self):
                self.shown = []
                self.page = type("Page", (), {"update": lambda _self: None})()

            def info(self, title, message):
                self.shown.append((title, message))

        self._break()
        app = FakeApp()
        app.check_broken_settings()
        self.assertEqual(len(app.shown), 1)
        # PC und Handy: wortgleich (beide aus fisi_update)
        self._break()
        import app_gui
        shown = []
        original = app_gui.messagebox.showwarning
        app_gui.messagebox.showwarning = lambda title, text, **kw: shown.append((title, text))
        try:
            app_gui.FISIApp.check_finished_update(type("App", (), {"root": None})())
        finally:
            app_gui.messagebox.showwarning = original
        self.assertEqual(app.shown, shown)


# ---------------------------------------------------------------------------
#  Fenster "Update verfuegbar" (B-H-06)
# ---------------------------------------------------------------------------

def _tk_ok():
    try:
        import tkinter
        root = tkinter.Tk()
        root.destroy()
        return True
    except Exception:  # noqa: BLE001
        return False


@unittest.skipUnless(_tk_ok(), "kein Display")
class FensterOhneDateiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import customtkinter as ctk
        cls.root = ctk.CTk()
        cls.root.geometry("300x200+0+0")

    @classmethod
    def tearDownClass(cls):
        cls.root.destroy()

    def _status(self, kind):
        import app_gui
        import fisi_widgets
        fisi_widgets.setup_fonts(self.root)
        app = type("App", (), {"root": self.root})()
        info = fu.UpdateInfo("0.63", "Neu", fu.RELEASES_PAGE)
        original = fu.install_kind
        fu.install_kind = lambda: kind
        try:
            dialog = app_gui.UpdateDialog(app, info)
            self.root.update()
            text = dialog.lbl_status.cget("text")
            button = dialog.btn_main
            dialog.destroy()
        finally:
            fu.install_kind = original
        return text, button

    def test_installiert_aber_keine_datei(self):
        text, _button = self._status("deb")
        self.assertIn("Für dein System liegt diesmal keine Datei bei.", text)
        self.assertNotIn("nur in der installierten Anwendung", text)

    def test_aus_dem_quellcode_wie_bisher(self):
        # Schutz-Test: Start aus dem Quellcode behaelt den alten Satz
        text, _button = self._status(None)
        self.assertIn("nur in der installierten Anwendung", text)


if __name__ == "__main__":
    try:
        unittest.main(verbosity=2)
    finally:
        SERVER.shutdown()
        shutil.rmtree(_TMP, ignore_errors=True)
