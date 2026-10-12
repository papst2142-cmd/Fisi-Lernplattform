#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests fuer den Abgleich mehrerer Geraete (fisi_sync.py) - ab 0.62.4 (B-A-02,
B-B-03, B-G-24, B-G-25, Plan 0.62.4 Abschnitt 3.3.5, Tests 0 bis 12).

Jedes "Geraet" ist ein eigener Prozess (pruefung/abgleich_geraet.py) mit
eigener Wegwerf-Datenbank, eigenem HOME und eigener Zeitzone (TZ). Abgeglichen
wird gegen eine Attrappe der GitHub-API auf 127.0.0.1
(pruefung/abgleich_attrappe.py): keine echten Zugangsdaten, keine Verbindung
nach aussen, keine echten Daten.

Mischbetrieb (Tests 8, 9, 10): Der Code alter Staende kommt per "git archive"
aus den Tags (v0.62.3, v0.56, v0.50). Fehlt ein Tag (flacher Checkout in der
CI), wird er einmal nachgeholt. Geht das nicht, ist der Test in der CI rot und
lokal uebersprungen.

Gegenprobe gegen einen anderen Stand (z.B. v0.62.3, dort sollen die Tests 1
bis 7 und 10 rot sein):
    ABGLEICH_CODE=<ordner mit dem Code> python test_abgleich.py

Nur unter Linux/macOS (Zeitzone je Prozess ueber TZ).
Start:  python test_abgleich.py
"""

import datetime
import gzip
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "pruefung"))

import abgleich_attrappe as att  # noqa: E402

CODE = os.path.abspath(os.environ.get("ABGLEICH_CODE") or HERE)
GERAET = os.path.join(HERE, "pruefung", "abgleich_geraet.py")
IN_CI = bool(os.environ.get("GITHUB_ACTIONS") or os.environ.get("CI"))
DAY = 86400.0
MIXED_HOLD = 7 * DAY      # fisi_sync.MIXED_HOLD
TWO_H = 7200.0
INVALID = "ungültige Löschmarke"
FUTURE_BACKUP = "Sicherung enthält eine Löschmarke in der Zukunft"
WORK = tempfile.mkdtemp(prefix="fisi_abgleich_")
SERVER, PORT = att.start_server()
API = "http://127.0.0.1:%d" % PORT
_STAENDE = {}


def bericht(text):
    """Zahlen, die der Bericht braucht (Fenster, Hochladungen), sichtbar im Protokoll."""
    print("  [Beleg] %s" % text, flush=True)


def code_stand(tag):
    """Ordner mit dem Code aus einem Tag (git archive), oder None."""
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


class Geraet:
    """Ein Geraet als eigener Prozess; Aufruf mit einem Befehl, Antwort als dict."""

    def __init__(self, ordner, name, tz, code=CODE, uhr=0.0):
        self.name, self.code = name, code
        self.home = os.path.join(WORK, ordner, name)
        os.makedirs(os.path.join(self.home, "tmp"), exist_ok=True)
        env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": self.home,
               "TMPDIR": os.path.join(self.home, "tmp"),
               "FISI_DB_PATH": os.path.join(self.home, "lern.db"), "TZ": tz,
               "PYTHONDONTWRITEBYTECODE": "1", "LANG": "C.UTF-8",
               "PYTHONIOENCODING": "utf-8"}
        self.err = open(os.path.join(self.home, "stderr.txt"), "w")
        self.proc = subprocess.Popen(
            [sys.executable, "-I", "-B", GERAET, code, API, name], env=env,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self.err, text=True,
            encoding="utf-8", cwd=self.home)
        first = self.proc.stdout.readline()
        if not first:
            raise RuntimeError("Geraet %s startet nicht: %s" % (name, self._stderr()))
        if uhr:
            self("uhr", uhr)

    def _stderr(self):
        self.err.flush()
        with open(self.err.name, encoding="utf-8", errors="replace") as handle:
            return handle.read()[-2000:]

    def send(self, *command):
        self.proc.stdin.write(json.dumps(command) + "\n")
        self.proc.stdin.flush()

    def receive(self):
        line = self.proc.stdout.readline()
        if not line:
            raise RuntimeError("Geraet %s antwortet nicht: %s" % (self.name, self._stderr()))
        result = json.loads(line)
        if "fehler" in result:
            raise RuntimeError("Geraet %s: %s" % (self.name, result["fehler"]))
        return result

    def __call__(self, *command):
        self.send(*command)
        return self.receive()

    def sync(self):
        result = self("sync")
        if result["sync"] != "ok":
            raise AssertionError("Abgleich auf %s: %s" % (self.name, result))
        return result

    def namen(self):
        return self("namen")["namen"]

    def marke(self, key="reset_at"):
        return self("meta")["meta"].get(key)

    def close(self):
        try:
            self.send("ende")
            self.proc.wait(timeout=10)
        except (OSError, ValueError, subprocess.TimeoutExpired):
            self.proc.kill()
        for stream in (self.proc.stdin, self.proc.stdout, self.err):
            try:
                stream.close()
            except (OSError, ValueError):
                pass


def server_reset(**ctl):
    with att.STATE.lock:
        att.STATE.reset()
        att.STATE.ctl.update(ctl)


def commits():
    return att.STATE.commits


def datei():
    return att.STATE.data() or {}


def datei_aendern(**felder):
    """Aendert die Datei auf dem "Server" (wie ein fremdes Programm)."""
    with att.STATE.lock:
        data = att.STATE.data()
        data.update(felder)
        att.STATE.store(gzip.compress(json.dumps(data, ensure_ascii=False).encode("utf-8"),
                                      mtime=0))


def server_zeit(iso):
    """Uhrzeit im Date-Kopf der Attrappe = dieser Zeitpunkt (UTC)."""
    import datetime
    target = datetime.datetime.fromisoformat(iso).replace(tzinfo=datetime.timezone.utc)
    att.STATE.ctl["datum_versatz"] = (
        target - datetime.datetime.now(datetime.timezone.utc)).total_seconds()


def pause():
    time.sleep(1.1)     # Zeitstempel sind sekundengenau


def ohne(namen, endung):
    return not any(k.endswith(endung) for k in namen)


class AbgleichTest(unittest.TestCase):
    def setUp(self):
        server_reset()
        self.geraete = []

    def tearDown(self):
        for geraet in self.geraete:
            geraet.close()

    def geraet(self, name, tz="Europe/Berlin", code=CODE, uhr=0.0):
        device = Geraet(self.id().rsplit(".", 1)[-1], name, tz, code, uhr)
        self.geraete.append(device)
        return device

    def alle_sync(self, geraete, runden=2):
        for _ in range(runden):
            for device in geraete:
                device.sync()

    def stabil(self, geraete, runden=3):
        """Mehrere Runden ohne Lernen: Es darf nichts mehr hochgeladen werden."""
        vorher = commits()
        self.alle_sync(geraete, runden)
        self.assertEqual(commits() - vorher, 0, "Hin und Her: Hochladungen ohne neue Eintraege")

    def alter_code(self, tag="v0.62.3"):
        folder = code_stand(tag)
        if folder is None:
            if IN_CI:
                self.fail("Code aus %s nicht verfuegbar" % tag)
            self.skipTest("Code aus %s nicht verfuegbar (git archive)" % tag)
        return folder

    # ------------------------------------------------------------------ 0
    def test_00_abgleich_gegen_attrappe(self):
        """B-A-02: Abrufen, Hochladen, Konflikt 409, 422, Zeitueberschreitung."""
        a, b = self.geraet("A"), self.geraet("B")
        a("lerne", 3, "eins")
        self.assertEqual(a.sync()["sent"], 3)
        self.assertEqual(b.sync()["received"], 3)
        self.assertEqual(b.namen(), {"a-eins": 3})
        # Konflikt: ein anderes Geraet war schneller (409) -> neuer Versuch
        att.STATE.ctl.update(put_status=409, put_status_n=1)
        a("lerne", 1, "zwei")
        vorher = commits()
        a.sync()
        self.assertEqual(commits() - vorher, 1)
        # 422 (sha fehlt) wie 409: neuer Versuch
        att.STATE.ctl.update(put_status=422, put_status_n=1)
        a("lerne", 1, "drei")
        vorher = commits()
        a.sync()
        self.assertEqual(commits() - vorher, 1)
        # Dauerkonflikt: nach drei Versuchen eine Meldung, kein Absturz
        att.STATE.ctl.update(put_status=409, put_status_n=3)
        a("lerne", 1, "vier")
        self.assertEqual(a("sync")["sync"], "SyncError")
        a.sync()
        # Zeitueberschreitung beim Abrufen: Meldung, kein Absturz
        a("timeout", 1)
        att.STATE.ctl.update(get_delay=2)
        self.assertEqual(a("sync")["sync"], "SyncError")
        att.STATE.ctl.pop("get_delay")
        b.sync()
        self.assertEqual(b.namen(), {"a-eins": 3, "a-zwei": 1, "a-drei": 1, "a-vier": 1})

    # ------------------------------------------------------------------ 1
    def test_01_zwei_zonen(self):
        """A in Berlin loescht, B in UTC lernt danach: Bs Eintraege bleiben."""
        a, b = self.geraet("A", "Europe/Berlin"), self.geraet("B", "UTC")
        a("lerne", 2, "vorher")
        b("lerne", 2, "vorher")
        self.alle_sync([a, b, a], 1)
        pause()
        a("reset_all")
        a.sync()
        pause()
        b("lerne", 2, "nachher")
        b.sync()
        a.sync()
        for device in (a, b):
            namen = device.namen()
            self.assertTrue(ohne(namen, "-vorher"), (device.name, namen))
            self.assertEqual(namen.get("b-nachher"), 2, (device.name, namen))
        self.stabil([a, b])

    # ------------------------------------------------------------------ 2
    def test_02_zeitumstellung(self):
        """Loeschen 02:30 (+02:00), Lernen 02:10 (+01:00) am 25.10.: Der Eintrag bleibt."""
        a, b = self.geraet("A"), self.geraet("B")
        for device in (a, b):
            device("zeit", "2026-10-25T00:00:00")
        server_zeit("2026-10-25T00:00:00")
        a("lerne", 2, "vorher")
        b("lerne", 2, "vorher")
        self.alle_sync([a, b, a], 1)
        a("zeit", "2026-10-25T00:30:00")          # 02:30 Sommerzeit
        server_zeit("2026-10-25T00:30:00")
        a("reset_all")
        a.sync()
        self.assertTrue(a.marke().startswith("2026-10-25 02:30"), a.marke())
        b("zeit", "2026-10-25T01:10:00")          # 02:10 Winterzeit
        server_zeit("2026-10-25T01:10:00")
        b("lerne", 2, "nachher")
        b.sync()
        a("zeit", "2026-10-25T01:11:00")
        a.sync()
        for device in (a, b):
            namen = device.namen()
            self.assertTrue(ohne(namen, "-vorher"), (device.name, namen))
            self.assertEqual(namen.get("b-nachher"), 2, (device.name, namen))

    # ------------------------------------------------------------------ 3
    def _uhr_vor(self, variante, versatz, bekannt):
        a = self.geraet("A", uhr=versatz if bekannt else 0.0)
        b, c = self.geraet("B"), self.geraet("C", "UTC")
        for device in (a, b, c):
            device("lerne", 3, "vorher")
        self.alle_sync([a, b, c, a], 1)
        a("uhr", versatz)
        pause()
        a("reset_all")
        if variante == "a":
            a.sync()
        else:
            pause()
            b("lerne", 3, "fenster")
            c("lerne", 3, "fenster")
            b.sync()
            c.sync()
            pause()
            a.sync()
        pause()
        for device in (b, c, a):
            device("lerne", 3, "nachher")
        self.alle_sync([b, c, a], 2)
        marken = set()
        for device in (a, b, c):
            namen = device.namen()
            self.assertTrue(ohne(namen, "-vorher"), (device.name, namen))
            for n in "abc":
                self.assertEqual(namen.get("%s-nachher" % n), 3, (device.name, namen))
            if variante == "b":
                bericht("Test 3b %+gs %s: %s behaelt %d von 6 Fenster-Eintraegen" % (
                    versatz, "bekannt" if bekannt else "neu", device.name,
                    namen.get("b-fenster", 0) + namen.get("c-fenster", 0)))
            marken.add(device.marke())
        self.assertEqual(marken, {datei()["markers"]["reset_at"]})
        self.stabil([a, b, c])

    def test_03a_uhr_vor_ein_tag_sofort(self):
        self._uhr_vor("a", DAY, False)

    def test_03b_uhr_vor_zwei_stunden_offline(self):
        self._uhr_vor("b", TWO_H, False)

    def test_03c_uhr_vor_bekannt(self):
        """Die Uhr ging schon beim Lernen falsch und wurde beim Abgleich gemessen."""
        self._uhr_vor("a", TWO_H, True)

    def test_03d_messung_aelter_als_ein_tag(self):
        """Gegenpruefung A-9, F1: Die Abweichung steckt schon im Eintrag (_stamp),
        die Messung ist beim naechsten Abgleich aber aelter als 24 h. Sie darf
        nicht ein zweites Mal hinein, sonst faellt der Eintrag unter eine
        Loeschung, die vor ihm lag."""
        def zeit(stunden):
            att.STATE.ctl["datum_versatz"] = stunden * 3600.0
            a("uhr", stunden * 3600.0 + DAY)
            b("uhr", stunden * 3600.0)

        a, b = self.geraet("A"), self.geraet("B")
        zeit(0)
        a("lerne", 2, "vorher")
        b("lerne", 2, "vorher")
        self.alle_sync([a, b, a], 1)
        zeit(22)
        b("reset_all")
        b.sync()
        zeit(23)
        a("lerne", 1, "x")
        zeit(25)
        a.sync()
        b.sync()
        for device in (a, b):
            namen = device.namen()
            self.assertTrue(ohne(namen, "-vorher"), (device.name, namen))
            self.assertEqual(namen.get("a-x"), 1, (device.name, namen))

    # ------------------------------------------------------------------ 4
    def _zukunftsmarke(self, m_in_datei):
        a, b = self.geraet("A"), self.geraet("B", "UTC")
        a("lerne", 4, "vorher")
        b("lerne", 4, "vorher")
        self.alle_sync([a, b, a], 1)
        a("uhr", DAY)
        pause()
        if m_in_datei:          # A laedt ohne Date-Kopf ungekappt hoch
            att.STATE.ctl["ohne_datum"] = True
            a("reset_all")
            a.sync()
            att.STATE.ctl["ohne_datum"] = False
            pause()
            b.sync()
            pause()
            a.sync()
        else:
            a("reset_all")
            a.sync()
            pause()
            b.sync()
        marken = {a.marke(), b.marke(), datei()["markers"]["reset_at"]}
        self.assertEqual(len(marken), 1, marken)
        pause()
        for runde in range(3):
            vorher = commits()
            a("lerne", 2, "r%d" % runde)
            b("lerne", 2, "r%d" % runde)
            self.alle_sync([a, b], 2)
            self.assertLessEqual(commits() - vorher, 2, "Runde %d" % runde)
        for device in (a, b):
            namen = device.namen()
            self.assertTrue(ohne(namen, "-vorher"), (device.name, namen))
            for n in "ab":
                for r in range(3):
                    self.assertEqual(namen.get("%s-r%d" % (n, r)), 2, (device.name, namen))
        self.stabil([a, b])

    def test_04a_zukunftsmarke_a_kappt(self):
        self._zukunftsmarke(False)

    def test_04b_zukunftsmarke_aus_der_datei(self):
        self._zukunftsmarke(True)

    # ------------------------------------------------------------------ 5
    def test_05_ungueltige_marken(self):
        """B-G-25: Nichts wird geloescht, die Meldung kommt, der Abgleich laeuft."""
        for wert in ("x", "2026-13-45 10:00:00", 12345, "12345"):
            with self.subTest(marke=wert):
                server_reset()
                a, b = self.geraet("A%s" % len(self.geraete)), self.geraet(
                    "B%s" % len(self.geraete))
                a("lerne", 3, "eins")
                a.sync()
                datei_aendern(markers={"reset_at": wert})
                result = b("sync")
                self.assertEqual(result["sync"], "ok", result)
                self.assertIn(INVALID, result["meldung"])
                self.assertEqual(sum(b.namen().values()), 3)
                a("lerne", 1, "zwei")
                self.assertEqual(a("sync")["sync"], "ok")
                self.assertEqual(sum(a.namen().values()), 4)

    def test_05b_ungueltige_marke_mit_altem_geraet(self):
        """Restrisiko: "x" mit einem Geraet 0.62.3. Das alte loescht wie heute,
        es darf aber kein Hin und Her entstehen."""
        alt = self.alter_code()
        n, o = self.geraet("N"), self.geraet("O", code=alt)
        n("lerne", 3, "eins")
        o("lerne", 3, "eins")
        self.alle_sync([n, o, n], 1)
        datei_aendern(markers={"reset_at": "x"})
        self.alle_sync([o, n], 1)
        n("lerne", 2, "zwei")
        o("lerne", 2, "zwei")
        self.alle_sync([n, o], 2)
        bericht("Test 5b: neu behaelt %d, alt behaelt %d Eintraege" % (
            sum(n.namen().values()), sum(o.namen().values())))
        self.stabil([n, o])

    # ------------------------------------------------------------------ 6
    def test_06_meldung_entfernt(self):
        a, b = self.geraet("A"), self.geraet("B")
        a("lerne", 3, "eins")
        b("lerne", 2, "eins")
        self.alle_sync([a, b, a], 1)
        pause()
        a("reset_all")
        a.sync()
        result = b.sync()
        self.assertEqual(result["removed"], 5, result)
        self.assertIn("5 Einträge wegen einer Löschung entfernt", result["meldung"])

    # ------------------------------------------------------------------ 7
    def test_07_gemischte_marken(self):
        """Die vier Faelle der Tabelle in Plan 3.3.2 und die spaetere von zwei
        Marken ueber zwei Zonen."""
        faelle = [
            # Marke, erwartete Etiketten (Eintrag 03:30 UTC mit / ohne Abstand)
            ("2026-10-12 05:00:00+02:00", {"mit": 1}),        # mit Zone: UTC 03:00
            ("2026-10-12 05:00:00", {}),                       # ohne Zone: Text
        ]
        for nr, (marke, soll) in enumerate(faelle):
            with self.subTest(marke=marke):
                server_reset()
                q, x = self.geraet("Q%d" % nr), self.geraet("X%d" % nr, "UTC")
                q.sync()                                      # Datei mit "schreiber"
                x("eintrag", "mit", "2026-10-12 03:30:00", 0)
                x("eintrag", "ohne", "2026-10-12 03:30:00", None)
                datei_aendern(markers={"reset_at": marke})
                x.sync()
                self.assertEqual(x.namen(), {"x%d-%s" % (nr, k): v for k, v in soll.items()})
        with self.subTest("spaetere Marke ueber zwei Zonen"):
            server_reset()
            q, y = self.geraet("Q9"), self.geraet("Y", "UTC")
            q.sync()
            y("setmeta", "reset_at", "2026-10-12 05:00:00+02:00")     # 03:00 UTC
            y("eintrag", "mit", "2026-10-12 03:30:00", 0)
            datei_aendern(markers={"reset_at": "2026-10-12 04:00:00+00:00"})  # 04:00 UTC
            y.sync()
            self.assertEqual(y.marke(), "2026-10-12 04:00:00+00:00")
            self.assertEqual(y.namen(), {})

    # ------------------------------------------------------------------ 8
    def test_08_alte_datenbanken(self):
        """Datenbanken wie 0.50, 0.56 und 0.62.3 sie anlegen: oeffnen, Spalte
        ergaenzt, nichts verloren."""
        fuellen = ("import sys; sys.path.insert(0, sys.argv[1]); import fisi_core; "
                   "db = fisi_core.DBManager(); "
                   "[db.log_card('Kat', 'alt-karte-%d' % i, 'karte', 1) for i in range(3)]; "
                   "[db.log_quiz_answer('Kat', 'alt-frage-%d' % i, 1) for i in range(2)]; "
                   "db.save_test_result(8, 10, 80.0, 'gut', 300)")
        for tag in ("v0.50", "v0.56", "v0.62.3"):
            with self.subTest(stand=tag):
                alt = self.alter_code(tag)
                name = "D" + tag.replace(".", "_")
                home = os.path.join(WORK, "test_08_alte_datenbanken", name)
                os.makedirs(home, exist_ok=True)
                db_path = os.path.join(home, "lern.db")
                env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": home,
                       "FISI_DB_PATH": db_path, "PYTHONDONTWRITEBYTECODE": "1",
                       "LANG": "C.UTF-8"}
                proc = subprocess.run([sys.executable, "-I", "-B", "-c", fuellen, alt],
                                      env=env, capture_output=True, text=True, timeout=120)
                self.assertEqual(proc.returncode, 0, proc.stderr[-1500:])
                self.assertTrue(os.path.exists(db_path))
                neu = self.geraet(name)
                self.assertIn("utc_offset", neu("spalten")["spalten"])
                tabellen = neu("zaehle")["tabellen"]
                self.assertEqual(tabellen["card_events"]["zeilen"], 3)
                self.assertEqual(tabellen["quiz_answers"]["zeilen"], 2)
                self.assertEqual(tabellen["test_results"]["zeilen"], 1)
                self.assertEqual(neu.namen(), {"alt-karte": 3})

    # ------------------------------------------------------------------ 9
    def _misch(self, fall, codes):
        """Drei Geraete N1 -> O -> N2. Liefert behaltene Runden-Eintraege je
        Geraet und die Hochladungen der stabilen Runden."""
        server_reset()
        suffix = str(len(self.geraete) + commits() + int(time.time() * 1000) % 100000)
        n1 = self.geraet("N1" + suffix, code=codes[0])
        o = self.geraet("O" + suffix, code=codes[1])
        n2 = self.geraet("N2" + suffix, "UTC", code=codes[2])
        geraete = [n1, o, n2]
        for device in geraete:
            device("lerne", 3, "vorher")
        self.alle_sync(geraete + [n1], 1)
        pause()
        loescher = {"alt_uhr_vor": o, "neu_uhr_vor": n1, "neu_uhr_vor_ohne_datum": n1,
                    "neu_richtig_berlin": n1, "neu_richtig_utc": n2}[fall]
        if "uhr_vor" in fall:
            loescher("uhr", DAY)
        loescher("reset_all")
        # ohne Date-Kopf kommt die Zukunftsmarke ungekappt in die Datei, und
        # das alte Geraet uebernimmt sie (Gegenpruefung A-9, F2)
        att.STATE.ctl["ohne_datum"] = fall.endswith("ohne_datum")
        loescher.sync()
        att.STATE.ctl["ohne_datum"] = False
        pause()
        zuviel = 0
        for runde in range(3):
            for device in geraete:
                device("lerne", 2, "r%d" % runde)
            vorher = commits()
            for device in geraete:
                device.sync()
            zuviel += max(0, commits() - vorher - len(geraete))
            pause()
        vorher = commits()
        self.alle_sync(geraete, 3)
        behalten = [sum(v for k, v in device.namen().items() if "-r" in k)
                    for device in geraete]
        for device in geraete:
            device.close()
            self.geraete.remove(device)
        return behalten, commits() - vorher + zuviel

    def test_09_mischbetrieb(self):
        """Neu -> alt (v0.62.3) -> neu: kein Verlust ueber das heutige Mass
        hinaus, kein Hin und Her."""
        alt = self.alter_code()
        for fall in ("alt_uhr_vor", "neu_uhr_vor", "neu_uhr_vor_ohne_datum",
                     "neu_richtig_berlin", "neu_richtig_utc"):
            with self.subTest(fall=fall):
                heute, _ = self._misch(fall, (alt, alt, alt))
                misch, hochladungen = self._misch(fall, (CODE, alt, CODE))
                bericht("Test 9 %s: heute %s, Mischbetrieb %s von je 18, stabile Runden: "
                        "%d Hochladungen" % (fall, heute, misch, hochladungen))
                self.assertEqual(hochladungen, 0, "Hin und Her")
                for name, h, m in zip(("N1", "O", "N2"), heute, misch):
                    self.assertGreaterEqual(m, h, "%s verliert mehr als heute" % name)

    def test_09b_ungekappte_marke_im_mischbetrieb(self):
        """Gegenpruefung A-9, F2: Ein neues Geraet laedt ohne Date-Kopf eine
        Zukunftsmarke hoch, ein altes uebernimmt sie. Danach darf kein neues
        Geraet sie mehr kappen, sonst wechselt die Marke bei jeder Runde."""
        alt = self.alter_code()
        n1, o, n2 = self.geraet("N1"), self.geraet("O", code=alt), self.geraet("N2", "UTC")
        for device in (n1, o, n2):
            device("lerne", 2, "vorher")
        self.alle_sync([n1, o, n2, n1], 1)
        n1("uhr", DAY)
        pause()
        n1("reset_all")
        att.STATE.ctl["ohne_datum"] = True
        n1.sync()
        att.STATE.ctl["ohne_datum"] = False
        o.sync()
        zuviel = 0
        for runde in range(5):
            n1("lerne", 1, "r%d" % runde)
            vorher = commits()
            for device in (n1, o, n2):
                device.sync()
            zuviel += max(0, commits() - vorher - 1)
            pause()
        bericht("Test 9b: %d Hochladungen ohne neue Eintraege in 5 Runden" % zuviel)
        self.assertEqual(zuviel, 0, "Hin und Her")
        self.stabil([n1, o, n2])

    def test_09c_mischfrist_mit_falscher_uhr(self):
        """Gegenpruefung A-9, F4: Kurz vor Ende der 7-Tage-Frist nach einem
        alten Geraet muss ein neues Geraet mit Uhr +1 Tag gleichzeitig mit den
        anderen umschalten (Uhrzeit von GitHub), sonst vergleicht es schon in
        UTC und das andere noch als Text, und ein Eintrag wechselt hin und her."""
        n1, n2 = self.geraet("N1"), self.geraet("N2", "UTC")
        gesehen = (datetime.datetime.now(datetime.timezone.utc)
                   - datetime.timedelta(seconds=MIXED_HOLD - 6 * 3600))
        for device in (n1, n2):
            device("setmeta", "mischbetrieb", gesehen.isoformat())
            device("lerne", 1, "vorher")
        self.alle_sync([n1, n2, n1], 1)
        n1("uhr", DAY)
        n1.sync()                       # misst die Abweichung
        n1("lerne", 1, "e")
        n1.sync()
        pause()
        n2("reset_all")
        n2.sync()
        pause()
        vorher = commits()
        self.alle_sync([n1, n2], 4)
        zuviel = commits() - vorher
        e = [device.namen().get("n1-e", 0) for device in (n1, n2)]
        bericht("Test 9c: %d Hochladungen in 4 Ruherunden, Eintrag E behalten %s" % (zuviel, e))
        self.assertEqual(zuviel, 0, "Hin und Her")
        self.assertEqual(e[0], e[1], "uneinheitlicher Stand")

    # ------------------------------------------------------------------ 10
    def test_10a_sicherung_zukunftsmarke(self):
        """Zusammenfuehren einer Sicherung mit Zukunftsmarke (Uhr +1 Tag)."""
        a, b = self.geraet("A", uhr=DAY), self.geraet("B")
        b("lerne", 3, "eigen")
        a("reset_all")
        pfad = os.path.join(a.home, "zukunft.fisi")
        a("sicherung_erstellen", pfad)
        result = b("sicherung_zusammen", pfad)
        self.assertEqual(b.namen(), {"b-eigen": 3})
        self.assertIn(FUTURE_BACKUP, result["meldung"])

    def test_10b_sicherung_andere_zone(self):
        """Marke aus Berlin, Eintraege danach in UTC: Sie bleiben."""
        a, b = self.geraet("A"), self.geraet("B", "UTC")
        b("lerne", 2, "vorher")
        pause()
        a("reset_all")
        pfad = os.path.join(a.home, "berlin.fisi")
        a("sicherung_erstellen", pfad)
        pause()
        b("lerne", 2, "nachher")
        b("sicherung_zusammen", pfad)
        self.assertEqual(b.namen(), {"b-nachher": 2})

    def test_10c_sicherung_alt_und_neu(self):
        """Sicherung 0.62.4 in 0.62.3 und umgekehrt."""
        alt = self.alter_code()
        n, o = self.geraet("N"), self.geraet("O", code=alt)
        n("lerne", 2, "neu")
        o("lerne", 2, "alt")
        pfad_n = os.path.join(n.home, "neu.fisi")
        pfad_o = os.path.join(o.home, "alt.fisi")
        n("sicherung_erstellen", pfad_n)
        o("sicherung_erstellen", pfad_o)
        o("sicherung_zusammen", pfad_n)
        n("sicherung_zusammen", pfad_o)
        self.assertEqual(n.namen(), {"n-neu": 2, "o-alt": 2})
        self.assertEqual(o.namen(), {"n-neu": 2, "o-alt": 2})

    def test_10d_alles_ersetzen_mit_abgleich(self):
        """Alles ersetzen mit Zukunftsmarke, Abgleich eingerichtet: Nach dem
        naechsten Abgleich gilt S, Eintraege anderer danach bleiben."""
        a, b, c = self.geraet("A", uhr=DAY), self.geraet("B"), self.geraet("C", "UTC")
        b("lerne", 2, "vorher")
        c("lerne", 2, "vorher")
        self.alle_sync([b, c, b], 1)
        a("reset_all")
        pfad = os.path.join(a.home, "zukunft.fisi")
        a("sicherung_erstellen", pfad)
        pause()
        b("sicherung_ersetzen", pfad)
        b.sync()
        pause()
        c("lerne", 2, "nachher")
        self.alle_sync([c, b], 2)
        for device in (b, c):
            namen = device.namen()
            self.assertTrue(ohne(namen, "-vorher"), (device.name, namen))
            self.assertEqual(namen.get("c-nachher"), 2, (device.name, namen))

    # ------------------------------------------------------------------ 11
    def test_11_handy_kopien_byte_gleich(self):
        """Nach mobile/vorbereiten.py sind fisi_core.py, fisi_sync.py und
        fisi_game.py in der Handy-Kopie Byte fuer Byte gleich."""
        sys.path.insert(0, os.path.join(CODE, "mobile"))
        try:
            import vorbereiten
        finally:
            sys.path.pop(0)
        ziel = os.path.join(WORK, "handy_src")
        os.makedirs(ziel, exist_ok=True)
        vorbereiten.SRC = ziel
        vorbereiten.ROOT = CODE
        import contextlib
        import io
        with contextlib.redirect_stdout(io.StringIO()):
            vorbereiten.main()
        for name in ("fisi_core.py", "fisi_sync.py", "fisi_game.py"):
            with open(os.path.join(CODE, name), "rb") as one, \
                    open(os.path.join(ziel, name), "rb") as two:
                self.assertEqual(one.read(), two.read(), name)

    # ------------------------------------------------------------------ 12
    def test_12_gleichzeitig(self):
        """Zwei Geraete gleichen gleichzeitig ab (409): kein Verlust, keine Doppelten."""
        a, b = self.geraet("A"), self.geraet("B", "UTC")
        for runde in range(5):
            a("lerne", 2, "r%d" % runde)
            b("lerne", 2, "r%d" % runde)
            for device in (a, b):
                device.send("sync")
            for device in (a, b):
                self.assertEqual(device.receive()["sync"], "ok")
        self.alle_sync([a, b], 2)
        soll = {"%s-r%d" % (n, r): 2 for n in "ab" for r in range(5)}
        for device in (a, b):
            self.assertEqual(device.namen(), soll)
            karten = device("zaehle")["tabellen"]["card_events"]
            self.assertEqual((karten["zeilen"], karten["uids"], karten["doppelt"]), (20, 20, 0))


def tearDownModule():
    SERVER.shutdown()
    shutil.rmtree(WORK, ignore_errors=True)


if __name__ == "__main__":
    if os.name == "nt":
        print("test_abgleich.py braucht Zeitzonen je Prozess (TZ) - nur Linux/macOS.")
        sys.exit(0)
    print("Code der neuen Geraete: %s" % CODE)
    unittest.main(verbosity=2)
