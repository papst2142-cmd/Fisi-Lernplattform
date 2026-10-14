#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests fuer 0.63.2, Strang N11 (Bau-Haertung und Paketbau; FG-52, FG-53).

  * B-M-05  Lock-Dateien mit Pruefsummen: jede pip-Zeile nur mit
            --require-hashes aus einer Lock-Datei, Fassungen wie im
            Referenzlauf 38443624150, Inno Setup fest, certifi im Handy fest
  * B-M-06  Linux-Bau im Container Ubuntu 22.04 (Bild per Digest),
            glibc-Bedarf hoechstens wie v0.63.1 (pruefung/glibc_pruefen.py);
            Mac: beide dmg-Namen, die fisi_update.py sucht (B7)
  * B-N-12  pip-audit (pruefung/pip_audit_lauf.py) mit Attrappe: Warnung im
            normalen Lauf und bei Testversionen, rot im Release-Lauf, auch
            wenn nicht pruefbar; keine Ausnahmeliste
  * B-H-08  Unterversion oder Fix >= 100 wird vor jedem Schreiben abgelehnt
  * B-H-12  X-AppImage-Version nur im AppImage, Hinweisdatei des .deb ohne
            AppImage-Laufzeit, keine .DS_Store im Programm

Der Code-Ordner ist waehlbar (fuer die Rot-Probe gegen einen alten Stand):
    N11_CODE=<ordner mit dem Code> python test_bau_0632_n11.py

Start:  python test_bau_0632_n11.py
"""

import contextlib
import hashlib
import importlib
import io
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import textwrap
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
CODE = os.path.abspath(os.environ.get("N11_CODE") or HERE)
BUILD_YML = os.path.join(CODE, ".github", "workflows", "build.yml")
RELEASE_YML = os.path.join(CODE, ".github", "workflows", "release.yml")
LOCKS = ("requirements-lock-bau.txt", "requirements-lock-certifi.txt",
         "requirements-lock-flet.txt", "requirements-lock-pip-audit.txt",
         "requirements-lock-tests.txt")

# Fassungen, die der Referenzlauf 38443624150 (vor N11) installiert hat,
# aus dessen pip-Logs ("Successfully installed ...") je Job (N11-F2)
REFERENZ_BAU = {
    "altgraph": "0.17.5", "certifi": "2026.7.22", "customtkinter": "6.0.0",
    "darkdetect": "0.8.0", "macholib": "1.16.4", "packaging": "26.3",
    "pefile": "2024.8.26", "pillow": "12.3.0", "pyinstaller": "6.22.3",
    "pyinstaller-hooks-contrib": "2026.8", "pywin32-ctypes": "0.2.3",
    "setuptools": "84.0.0"}
REFERENZ_BAU_MARKEN = {"macholib": 'sys_platform == "darwin"',
                       "pefile": 'sys_platform == "win32"',
                       "pywin32-ctypes": 'sys_platform == "win32"'}
REFERENZ_TESTS = {"certifi": "2026.7.22", "customtkinter": "6.0.0", "darkdetect": "0.8.0",
                  "packaging": "26.3", "pillow": "12.3.0", "psutil": "7.2.2"}
# N10: Android-Laufzeit gehoert zu flet 1.0.1
REFERENZ_FLET = {"flet": "1.0.1", "flet-cli": "1.0.1", "flet-desktop": "1.0.1",
                 "flet-platform-assets": "1.0.1", "flet-web": "1.0.1"}
CERTIFI = "2026.7.22"
INNO = "6.7.1"
UBUNTU_2204 = ("ubuntu:22.04@sha256:"
               "5ec03bb3441e8b0bf3b4f9cd4629a1ae763010dc3035bb8da3ae6cf026486401")
GLIBC_GRUNDWERT_V0631 = (2, 35)

# Erwartete pip-Zeilen in build.yml: (Job, Lock-Datei), je genau einmal
PIP_ZEILEN = sorted([
    ("build", "requirements-lock-bau.txt"),
    ("build", "requirements-lock-pip-audit.txt"),
    ("android", "requirements-lock-flet.txt"),
    ("tests", "requirements-lock-tests.txt"),
    ("tests", "requirements-lock-flet.txt"),
    ("tests-windows", "requirements-lock-tests.txt"),
    ("tests-windows", "requirements-lock-flet.txt"),
    ("update-test", "requirements-lock-certifi.txt"),
    ("vorab", "requirements-lock-certifi.txt"),
])


def _lesen(pfad):
    with open(pfad, encoding="utf-8") as fh:
        return fh.read()


def _bytes(pfad):
    with open(pfad, "rb") as fh:
        return fh.read()


def _jobs(text):
    zeilen = text.splitlines()
    start = zeilen.index("jobs:")
    jobs, name = {}, None
    for zeile in zeilen[start + 1:]:
        m = re.match(r"^  ([A-Za-z0-9_-]+):\s*$", zeile)
        if m:
            name = m.group(1)
            jobs[name] = []
        elif re.match(r"^\S", zeile):
            break
        elif name:
            jobs[name].append(zeile)
    return jobs


def _schritt(text, name):
    zeilen = text.splitlines()
    for i, zeile in enumerate(zeilen):
        m = re.match(r"^(\s*)- name: (.*)$", zeile)
        if m and m.group(2).strip() == name:
            einzug = len(m.group(1))
            teil = [zeile]
            for folge in zeilen[i + 1:]:
                if folge.strip() and len(folge) - len(folge.lstrip()) <= einzug:
                    break
                teil.append(folge)
            return teil
    raise AssertionError("Schritt nicht gefunden: %s" % name)


def _lock(name):
    """{Paket: (Fassung, Marke, [Pruefsummen])}; jede Zeile muss passen."""
    pfad = os.path.join(CODE, name)
    eintraege, aktuell = {}, None
    for nr, zeile in enumerate(_lesen(pfad).splitlines(), 1):
        if not zeile.strip() or zeile.startswith("#"):
            continue
        m = re.match(r"^([a-z0-9][a-z0-9.-]*)==([0-9][^\s;]*)(?: ; (.+))? \\$", zeile)
        if m:
            if m.group(1) in eintraege:
                raise AssertionError("%s:%d doppelt: %s" % (name, nr, m.group(1)))
            aktuell = m.group(1)
            eintraege[aktuell] = (m.group(2), m.group(3), [])
            continue
        m = re.match(r"^    --hash=sha256:([0-9a-f]{64})( \\)?$", zeile)
        if m and aktuell:
            eintraege[aktuell][2].append(m.group(1))
            if not m.group(2):
                aktuell = None
            continue
        raise AssertionError("%s:%d unbekannte Zeile: %r" % (name, nr, zeile))
    return eintraege


def _modul(name, unterordner=""):
    """Laedt ein Modul aus CODE (frisch, damit Kopien geprueft werden koennen)."""
    pfad = os.path.join(CODE, unterordner)
    sys.path.insert(0, pfad)
    try:
        sys.modules.pop(name, None)
        return importlib.import_module(name)
    finally:
        sys.path.remove(pfad)


def _bau():
    return _modul("build")


# ============================================================================
#  B-M-05  Lock-Dateien
# ============================================================================

class LockTest(unittest.TestCase):

    def test_l1_jede_pip_zeile_aus_lock_mit_pruefsummen(self):
        jobs = _jobs(_lesen(BUILD_YML))
        gefunden = []
        for job, zeilen in jobs.items():
            for zeile in zeilen:
                if re.search(r"\bpip install\b", zeile) and not zeile.lstrip().startswith("#"):
                    m = re.match(r'^ +(?:run: )?(?:python3?|"\$RUNNER_TEMP/audit/bin/python") '
                                 r"-m pip install --retries 10 --timeout 60 (?:--quiet )?"
                                 r"--require-hashes -r (requirements-lock-[a-z-]+\.txt)$", zeile)
                    self.assertTrue(m, "%s: %s" % (job, zeile.strip()))
                    gefunden.append((job, m.group(1)))
        self.assertEqual(sorted(gefunden), PIP_ZEILEN)
        # release.yml installiert nichts
        self.assertNotRegex(_lesen(RELEASE_YML), r"\bpip install\b")

    def test_l2_lock_dateien_vollstaendig_mit_pruefsummen(self):
        vorhanden = sorted(name for name in os.listdir(CODE)
                           if name.startswith("requirements-lock-"))
        self.assertEqual(vorhanden, sorted(LOCKS))
        for name in LOCKS:
            eintraege = _lock(name)
            self.assertTrue(eintraege, name)
            for paket, (fassung, _marke, summen) in eintraege.items():
                self.assertTrue(summen, "%s: %s ohne Pruefsumme" % (name, paket))
                self.assertEqual(len(summen), len(set(summen)), paket)
            kopf = _lesen(os.path.join(CODE, name))
            self.assertIn("pip install --require-hashes -r %s" % name, kopf)

    def test_l5_fassungen_wie_referenzlauf(self):
        bau = _lock("requirements-lock-bau.txt")
        self.assertEqual({k: v[0] for k, v in bau.items()}, REFERENZ_BAU)
        self.assertEqual({k: v[1] for k, v in bau.items() if v[1]}, REFERENZ_BAU_MARKEN)
        tests = _lock("requirements-lock-tests.txt")
        self.assertEqual({k: v[0] for k, v in tests.items()}, REFERENZ_TESTS)
        self.assertFalse([k for k, v in tests.items() if v[1]])
        # Die festen Pins aus requirements*.txt stehen gleich in den Locks
        for datei, lock in (("requirements.txt", bau), ("requirements-build.txt", bau),
                            ("requirements.txt", tests)):
            for name, fassung in re.findall(r"^([a-z0-9-]+)==(\S+)$",
                                            _lesen(os.path.join(CODE, datei)), re.MULTILINE):
                self.assertEqual(lock[name][0], fassung, "%s %s" % (datei, name))

    def test_l6_flet_wie_n10(self):
        flet = _lock("requirements-lock-flet.txt")
        self.assertEqual({k: v[0] for k, v in flet.items() if k.startswith("flet")},
                         REFERENZ_FLET)
        self.assertEqual(len(flet), 54)
        # die Android-Laufzeit (N10) ist an genau diese flet-Fassung gebunden
        self.assertIn("releases/download/v1.0.1", _lesen(BUILD_YML))
        self.assertNotIn('"flet[all]==', _lesen(BUILD_YML))

    def test_l8_certifi_ueberall_gleich(self):
        for name in LOCKS:
            self.assertEqual(_lock(name)["certifi"][0], CERTIFI, name)
        self.assertEqual(_lock("requirements-lock-certifi.txt").keys(), {"certifi"})
        pyproject = _lesen(os.path.join(CODE, "mobile", "pyproject.toml"))
        self.assertIn('    "certifi==%s",\n' % CERTIFI, pyproject)
        self.assertNotIn('    "certifi",\n', pyproject)

    def test_l7_inno_setup_fest(self):
        schritt = "\n".join(_schritt(_lesen(BUILD_YML), "Inno Setup bereitstellen"))
        self.assertIn('$soll = "%s"' % INNO, schritt)
        self.assertIn("choco install innosetup --version $soll -y", schritt)
        # Fassung aus dem Uninstall-Eintrag (ISCC.exe meldet 0.0.0.0,
        # R3-Lauf 38504069175), vor und nach choco
        self.assertIn("Uninstall\\Inno Setup 6_is1", schritt)
        self.assertIn("(Get-ItemProperty $s).DisplayVersion", schritt)
        self.assertEqual(schritt.count("$ist = Fassung"), 2)
        self.assertIn('if ($ist -ne $soll) { Write-Host "Inno Setup $ist statt $soll"; exit 1 }',
                      schritt)
        self.assertEqual(len(re.findall(r"choco install", _lesen(BUILD_YML))), 1)

    def test_l9_cache_schluessel_aus_lock_dateien(self):
        text = _lesen(BUILD_YML)
        pfade = re.findall(r"cache-dependency-path: (\S+)", text)
        self.assertEqual(sorted(pfade), sorted(["requirements-lock-bau.txt", "|",
                                                "requirements-lock-flet.txt", "|",
                                                "requirements-lock-certifi.txt"]))
        for job in ("tests", "tests-windows"):
            zeilen = "\n".join(_jobs(text)[job])
            self.assertIn("cache-dependency-path: |\n            requirements-lock-tests.txt\n"
                          "            requirements-lock-flet.txt\n", zeilen)


# ============================================================================
#  B-M-06  Container und glibc
# ============================================================================

def _elf(versionen, klasse=2):
    """Kleinste ELF-Datei mit .dynstr und .gnu.version_r (libc.so.6)."""
    namen = ["GLIBC_%s" % v for v in versionen]
    strtab = b"\0libc.so.6\0" + b"".join(n.encode() + b"\0" for n in namen)
    offsets = []
    pos = len(b"\0libc.so.6\0")
    for n in namen:
        offsets.append(pos)
        pos += len(n) + 1
    verneed = struct.pack("<HHIII", 1, len(namen), 1, 16, 0)
    for i, off in enumerate(offsets):
        verneed += struct.pack("<IHHII", 0, 0, i + 2, off, 16 if i + 1 < len(namen) else 0)
    if klasse == 2:
        kopf_laenge, sh_laenge = 64, 64
    else:
        kopf_laenge, sh_laenge = 52, 40
    str_off = kopf_laenge
    vn_off = str_off + len(strtab)
    sh_off = vn_off + len(verneed)
    ident = b"\x7fELF" + bytes([klasse, 1, 1]) + b"\0" * 9
    if klasse == 2:
        kopf = ident + struct.pack("<HHIQQQIHHHHHH", 3, 62, 1, 0, 0, sh_off, 0,
                                   64, 0, 0, sh_laenge, 3, 0)
        sh = lambda *f: struct.pack("<IIQQQQIIQQ", *f)
    else:
        kopf = ident + struct.pack("<HHIIIIIHHHHHH", 3, 3, 1, 0, 0, sh_off, 0,
                                   52, 0, 0, sh_laenge, 3, 0)
        sh = lambda *f: struct.pack("<IIIIIIIIII", *f)
    tabelle = (sh(0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
               + sh(0, 3, 0, 0, str_off, len(strtab), 0, 0, 1, 0)
               + sh(0, 0x6FFFFFFE, 0, 0, vn_off, len(verneed), 1, 1, 4, 0))
    return kopf + strtab + verneed + tabelle


class GlibcTest(unittest.TestCase):

    def setUp(self):
        self.g = _modul("glibc_pruefen", "pruefung")
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def _datei(self, rel, inhalt):
        pfad = os.path.join(self.tmp, rel)
        os.makedirs(os.path.dirname(pfad), exist_ok=True)
        with open(pfad, "wb") as fh:
            fh.write(inhalt)
        return pfad

    def _main(self, *args):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rc = self.g.main(list(args))
        return rc, out.getvalue()

    def test_l10_grundwert_von_v0631(self):
        self.assertEqual(self.g.GRUNDWERT, GLIBC_GRUNDWERT_V0631)

    def test_elf_lesen(self):
        self.assertEqual(self.g.elf_glibc(_elf(["2.2.5", "2.34"])), {(2, 2, 5), (2, 34)})
        self.assertEqual(self.g.elf_glibc(_elf(["2.0", "2.17"], klasse=1)), {(2, 0), (2, 17)})
        with self.assertRaises(self.g.KeinElf):
            self.g.elf_glibc(b"#!/bin/sh\n")

    def test_l11_hoeher_als_grundwert_rot_auch_tief_in_so(self):
        self._datei("app/FISI-Lernplattform", _elf(["2.2.5", "2.34"]))
        self._datei("app/_internal/a/b/libneu.so.1", _elf(["2.17", "2.39"]))
        self._datei("app/_internal/text.txt", b"kein ELF")
        rc, text = self._main(os.path.join(self.tmp, "app"))
        self.assertEqual(rc, 1, text)
        self.assertIn("app: _internal/a/b/libneu.so.1 verlangt GLIBC_2.39", text)
        self.assertNotIn("FISI-Lernplattform verlangt", text)

    def test_hoechstens_grundwert_gruen(self):
        self._datei("app/FISI-Lernplattform", _elf(["2.2.5", "2.35"]))
        self._datei("app/_internal/libalt.so", _elf(["2.17"]))
        rc, text = self._main(os.path.join(self.tmp, "app"))
        self.assertEqual(rc, 0, text)
        self.assertIn("2 ELF-Dateien, hoechstens GLIBC_2.35", text)

    def test_l12_nichts_pruefbar_ist_rot(self):
        leer = os.path.join(self.tmp, "leer")
        os.makedirs(leer)
        self._datei("ohne_elf/a.txt", b"text")
        for pfad in (leer, os.path.join(self.tmp, "ohne_elf"), os.path.join(self.tmp, "fehlt")):
            rc, text = self._main(pfad)
            self.assertEqual(rc, 2, text)
            self.assertIn("FEHLER glibc-Pruefung", text)
        rc, _text = self._main()
        self.assertEqual(rc, 2)

    def test_deb_wird_entpackt(self):
        if not shutil.which("dpkg-deb"):
            self.skipTest("dpkg-deb fehlt")
        stage = os.path.join(self.tmp, "stage")
        self._datei("stage/opt/x/lib/libneu.so", _elf(["2.39"]))
        self._datei("stage/DEBIAN/control", b"Package: x\nVersion: 1\nArchitecture: amd64\n"
                    b"Maintainer: x\nDescription: x\n")
        deb = os.path.join(self.tmp, "x_1_amd64.deb")
        subprocess.run(["dpkg-deb", "--build", "--root-owner-group", stage, deb],
                       check=True, capture_output=True)
        rc, text = self._main(deb)
        self.assertEqual(rc, 1, text)
        self.assertIn("x_1_amd64.deb: opt/x/lib/libneu.so verlangt GLIBC_2.39", text)

    def test_l13_container_per_digest_im_build_yml(self):
        text = _lesen(BUILD_YML)
        jobs = _jobs(text)
        build = "\n".join(jobs["build"])
        self.assertIn("    container: ${{ matrix.container }}\n", build)
        self.assertIn("          - os: ubuntu-24.04\n            label: linux\n"
                      "            container: %s\n" % UBUNTU_2204, build)
        self.assertEqual(re.findall(r"container: (\S+)", text), ["${{", UBUNTU_2204])
        schritt = "\n".join(_schritt(text, "glibc-Bedarf pruefen (Linux)"))
        self.assertIn("if: runner.os == 'Linux'", schritt)
        self.assertIn("run: python pruefung/glibc_pruefen.py dist/FISI-Lernplattform "
                      "installer_output/*.deb installer_output/*.AppImage", schritt)
        # im Container das Python fuer Ubuntu 22.04, nicht das eingehaengte
        # des Runners (Ubuntu 24.04, R3-Lauf 38504069175: pip fehlte)
        setup = build[build.index("      - uses: actions/setup-python@v7\n"):]
        setup = setup[:setup.index("\n\n")]
        self.assertIn("        env:\n          AGENT_TOOLSDIRECTORY: ${{ runner.os == 'Linux' && "
                      "'/opt/werkzeuge-jammy' || '' }}", setup)
        self.assertEqual(text.count("AGENT_TOOLSDIRECTORY"), 1)
        werkzeuge = "\n".join(_schritt(text, "Linux-Werkzeuge installieren"))
        self.assertIn('echo "PIP_CACHE_DIR=/root/.cache/pip" >> "$GITHUB_ENV"', werkzeuge)
        self.assertEqual(text.count("PIP_CACHE_DIR"), 1)
        # der Container-Schritt laeuft vor checkout (dort fehlt sonst git)
        self.assertLess(build.index("- name: Linux-Werkzeuge installieren"),
                        build.index("- uses: actions/checkout@"))


# ============================================================================
#  B7 / B-M-06  Mac: genau die Dateinamen, die installierte Programme suchen
# ============================================================================

class MacNamenTest(unittest.TestCase):

    def _namen_aus_fisi_update(self):
        zeilen = _lesen(os.path.join(CODE, "fisi_update.py")).splitlines()[130:132]
        namen = re.findall(r'"(-macOS-[a-z0-9]+\.dmg)"', "\n".join(zeilen))
        self.assertEqual(len(namen), 2, zeilen)
        return namen

    def test_l16_package_dmg_erzeugt_genau_die_gesuchten_namen(self):
        bau = _bau()
        update = _modul("fisi_update")
        namen = self._namen_aus_fisi_update()
        erzeugt = []
        with tempfile.TemporaryDirectory() as tmp:
            app = os.path.join(tmp, "dist", "FISI-Lernplattform.app")
            os.makedirs(os.path.join(app, "Contents", "Resources"))
            for name in bau.LEGAL_FILES:
                with open(os.path.join(app, "Contents", "Resources", name), "w") as fh:
                    fh.write(name)
            for maschine in ("arm64", "x86_64"):
                befehle = []
                with mock.patch.object(bau, "ROOT", tmp), \
                        mock.patch.object(bau, "OUTPUT", os.path.join(tmp, "out")), \
                        mock.patch.object(bau, "legal_folder",
                                          lambda p: os.path.join(p, "Contents", "Resources")), \
                        mock.patch.object(bau, "run", befehle.append), \
                        mock.patch.object(bau.platform, "machine", return_value=maschine), \
                        contextlib.redirect_stdout(io.StringIO()):
                    bau.package_dmg("0.63.2", app)
                self.assertEqual(len(befehle), 1)
                erzeugt.append(os.path.basename(befehle[0][-1]))
        self.assertEqual(erzeugt, ["FISI-Lernplattform-0.63.2" + n for n in namen])
        # und fisi_update findet je Rechner genau seine Datei
        assets = [{"name": n} for n in erzeugt]
        for maschine, name in (("arm64", erzeugt[0]), ("x86_64", erzeugt[1])):
            self.assertEqual(update.pick_asset(assets, kind="macos", machine=maschine),
                             {"name": name})


# ============================================================================
#  B-N-12  pip-audit (Attrappe)
# ============================================================================

STUB = r'''#!{python}
import json, os, sys
modus = os.environ["STUB_MODUS"]
with open(os.environ["STUB_ZAEHLER"], "a") as fh:
    fh.write("x")
args = sys.argv[1:]
anf = open(args[args.index("--requirement") + 1]).read().split()
namen = [z.split("==")[0] for z in anf]
if len(namen) != len(set(namen)):
    sys.stderr.write("ERROR:pip_audit._cli:package has duplicate requirements\n")
    sys.exit(1)
ausgabe = args[args.index("--output") + 1]
if modus == "netz":
    sys.stderr.write("requests.exceptions.ConnectionError: pypi.org\n")
    sys.exit(1)
deps = []
for zeile in anf:
    name, fassung = zeile.split("==")
    vulns = []
    if modus == "fund" and name == "urllib3" or modus == "alt" and fassung == "1.26.4":
        vulns = [{{"id": "GHSA-test-0001", "fix_versions": ["9.9.9"], "aliases": []}}]
    deps.append({{"name": name, "version": fassung, "vulns": vulns}})
if modus == "uebersprungen":
    deps[0] = {{"name": deps[0]["name"], "skip_reason": "Dependency not found on PyPI"}}
json.dump({{"dependencies": deps, "fixes": []}}, open(ausgabe, "w"))
sys.exit(1 if modus == "fund" else 0)
'''


class PipAuditTest(unittest.TestCase):

    def setUp(self):
        self.lauf = _modul("pip_audit_lauf", "pruefung")
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.stub = os.path.join(self.tmp, "pip-audit")
        with open(self.stub, "w") as fh:
            fh.write(STUB.format(python=sys.executable))
        os.chmod(self.stub, 0o755)
        self.zaehler = os.path.join(self.tmp, "zaehler")

    def _lauf(self, modus, release, locks=LOCKS):
        env = {"STUB_MODUS": modus, "STUB_ZAEHLER": self.zaehler, "PIP_AUDIT_PAUSE": "0",
               "IS_RELEASE": release}
        out = io.StringIO()
        with mock.patch.dict(os.environ, env), contextlib.redirect_stdout(out):
            rc = self.lauf.main(["--pip-audit", self.stub]
                                + [os.path.join(CODE, n) for n in locks])
        versuche = len(_bytes(self.zaehler)) if os.path.exists(self.zaehler) else 0
        return rc, out.getvalue(), versuche

    def test_l19_keine_funde(self):
        for release in ("false", "true"):
            rc, text, versuche = self._lauf("leer", release)
            self.assertEqual(rc, 0, text)
            self.assertNotIn("::warning", text)
            self.assertNotIn("::error", text)
            self.assertIn("0 Funde", text)
            os.remove(self.zaehler)
        self.assertEqual(versuche, 1)

    def test_l20_fund_normaler_lauf_warnt(self):
        rc, text, _v = self._lauf("fund", "false")
        self.assertEqual(rc, 0, text)
        self.assertIn("::warning title=pip-audit::urllib3 2.8.0: GHSA-test-0001 "
                      "(behoben in: 9.9.9; Lock-Datei: requirements-lock-flet.txt, "
                      "requirements-lock-pip-audit.txt)", text)
        self.assertNotIn("::error", text)

    def test_zwei_fassungen_eines_pakets(self):
        # zwei Lock-Dateien mit verschiedenen Fassungen (Probe-Lauf 38505308938)
        alt = os.path.join(self.tmp, "requirements-lock-alt.txt")
        with open(alt, "w") as fh:
            fh.write("urllib3==1.26.4 \\\n    --hash=sha256:" + "0" * 64 + "\n")
        rc, text, versuche = self._lauf("alt", "false", locks=LOCKS + (alt,))
        self.assertEqual(rc, 0, text)
        self.assertEqual(versuche, 2)
        self.assertIn("::warning title=pip-audit::urllib3 1.26.4: GHSA-test-0001 "
                      "(behoben in: 9.9.9; Lock-Datei: requirements-lock-alt.txt)", text)
        self.assertEqual(text.count("::warning"), 1)
        self.assertIn("geprueft, 1 Funde", text)
        self.assertNotIn("nicht pruefbar", text)

    def test_l21_fund_release_rot(self):
        rc, text, _v = self._lauf("fund", "true")
        self.assertEqual(rc, 1, text)
        self.assertIn("::error title=pip-audit::urllib3 2.8.0: GHSA-test-0001", text)
        self.assertIn("Release wird nicht veroeffentlicht", text)

    def test_l22_nicht_erreichbar_normal_warnung_nach_wiederholung(self):
        rc, text, versuche = self._lauf("netz", "false")
        self.assertEqual(rc, 0, text)
        self.assertEqual(versuche, 3)
        self.assertEqual(text.count("Wiederholung wegen Netzfehler (pip-audit"), 2)
        self.assertIn("::warning title=pip-audit nicht pruefbar::", text)

    def test_l23_nicht_erreichbar_release_rot(self):
        rc, text, versuche = self._lauf("netz", "true")
        self.assertEqual(rc, 1, text)
        self.assertEqual(versuche, 3)
        self.assertIn("::error title=pip-audit nicht pruefbar::", text)
        self.assertIn("Release wird nicht veroeffentlicht", text)

    def test_uebersprungenes_paket_gilt_als_nicht_pruefbar(self):
        rc, text, _v = self._lauf("uebersprungen", "true")
        self.assertEqual(rc, 1, text)
        self.assertIn("nicht geprueft:", text)

    def test_l24_keine_ausnahmeliste(self):
        quelle = _lesen(os.path.join(CODE, "pruefung", "pip_audit_lauf.py"))
        self.assertNotIn("--ignore-vuln", quelle)
        self.assertNotRegex(quelle.lower(), r"ausnahme\w*\s*=")
        self.assertIn("keine Ausnahmeliste", quelle)

    def test_l27_vorab_nur_warnung(self):
        # Testversionen (vorab) setzen IS_RELEASE nicht auf "true"
        text = _lesen(BUILD_YML)
        self.assertIn("  IS_RELEASE: ${{ inputs.tag != '' || "
                      "startsWith(github.ref, 'refs/tags/v') }}\n", text)
        # nur diese eine Stelle setzt IS_RELEASE (der Vorab-Lauf hat kein Tag)
        self.assertEqual(len(re.findall(r"IS_RELEASE:", text)), 1)
        for release in ("", "false"):
            rc, text_, _v = self._lauf("fund", release)
            self.assertEqual(rc, 0)
            self.assertIn("::warning title=pip-audit::", text_)

    def test_l25_l26_schritt_im_workflow(self):
        text = _lesen(BUILD_YML)
        schritt = "\n".join(_schritt(text, "Sicherheitsluecken pruefen (pip-audit)"))
        self.assertIn("if: runner.os == 'Linux'", schritt)
        self.assertNotIn("continue-on-error", text)
        self.assertIn("--require-hashes -r requirements-lock-pip-audit.txt", schritt)
        aufruf = re.search(r"python pruefung/pip_audit_lauf.py --pip-audit "
                           r'"\$RUNNER_TEMP/audit/bin/pip-audit" \\\n((?:.*\\\n)*.*)', schritt)
        self.assertTrue(aufruf, schritt)
        self.assertEqual(sorted(re.findall(r"requirements-lock-[a-z-]+\.txt", aufruf.group(1))),
                         sorted(LOCKS))
        self.assertEqual(_lock("requirements-lock-pip-audit.txt")["pip-audit"][0], "2.10.1")


# ============================================================================
#  B-H-08  Version >= 100
# ============================================================================

class VersionTest(unittest.TestCase):

    def setUp(self):
        self.bau = _bau()

    def test_l28_l31_formel_unveraendert(self):
        for version, nummer in (("0.63.2", "6302"), ("0.99.99", "9999"), ("1.0", "10000"),
                                ("0.64", "6400")):
            self.assertEqual(self.bau.android_build_number(version), nummer)

    def _kopie(self, tmp):
        dateien = sorted({n for n, _p in self.bau.VERSION_SPOTS}
                         | {self.bau.ANDROID_BUILD_SPOT[0]})
        for name in dateien:
            ziel = os.path.join(tmp, name)
            os.makedirs(os.path.dirname(ziel), exist_ok=True)
            shutil.copy(os.path.join(CODE, name), ziel)
        return dateien

    @staticmethod
    def _summen(tmp, dateien):
        return {n: hashlib.sha256(_bytes(os.path.join(tmp, n))).hexdigest()
                for n in dateien}

    def test_l32_l37_setze_version_ab_100_abgelehnt_ohne_schreiben(self):
        with tempfile.TemporaryDirectory() as tmp:
            dateien = self._kopie(tmp)
            vorher = self._summen(tmp, dateien)
            for version in ("0.100", "0.62.100", "0.100.1", "1.0.100"):
                err = io.StringIO()
                with mock.patch.object(self.bau, "ROOT", tmp), \
                        contextlib.redirect_stderr(err), \
                        contextlib.redirect_stdout(io.StringIO()):
                    with self.assertRaises(SystemExit) as ende:
                        self.bau.set_version(version)
                self.assertEqual(ende.exception.code, 1)
                self.assertIn("Ungueltige Version %s" % version, err.getvalue())
                self.assertIn("100", err.getvalue())
                self.assertIn("Android", err.getvalue())
                self.assertEqual(self._summen(tmp, dateien), vorher, version)
            # 0.99.99 geht weiter (Grenze genau bei 100)
            with mock.patch.object(self.bau, "ROOT", tmp), \
                    contextlib.redirect_stdout(io.StringIO()):
                self.bau.set_version("0.99.99")
            self.assertIn("build_number = 9999\n",
                          _lesen(os.path.join(tmp, "mobile", "pyproject.toml")))

    def test_l35_check_versions_vor_dem_lesen(self):
        for version in ("0.100", "0.62.100"):
            err = io.StringIO()
            with mock.patch.object(self.bau, "_read",
                                   side_effect=AssertionError("gelesen")), \
                    contextlib.redirect_stderr(err):
                with self.assertRaises(SystemExit):
                    self.bau.check_versions(version)
            self.assertIn("Android", err.getvalue())

    def test_setze_version_ueber_kommandozeile(self):
        with tempfile.TemporaryDirectory() as tmp:
            dateien = self._kopie(tmp)
            vorher = self._summen(tmp, dateien)
            ergebnis = subprocess.run(
                [sys.executable, "-c", "import sys, build; build.ROOT = sys.argv[1]; "
                 "sys.argv = ['build.py', '--setze-version', '0.100']; build.main()", tmp],
                cwd=CODE, capture_output=True, text=True)
            self.assertEqual(ergebnis.returncode, 1, ergebnis.stderr)
            self.assertIn("kleiner als 100", ergebnis.stderr)
            self.assertEqual(self._summen(tmp, dateien), vorher)


# ============================================================================
#  B-H-12  Paketinhalt je Paketart
# ============================================================================

class PaketTest(unittest.TestCase):

    def setUp(self):
        # build.py laedt lizenzen.py selbst ("import lizenzen"): die aus CODE
        _modul("lizenzen")
        self.bau = _bau()
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.dist = os.path.join(self.tmp, "dist")
        programm = os.path.join(self.dist, self.bau.APP_NAME)
        os.makedirs(programm)
        for name in self.bau.LEGAL_FILES:
            with open(os.path.join(programm, name), "w") as fh:
                fh.write("#### AppImage-Laufzeit (aus dem Programmordner)\n")
        shutil.copy(os.path.join(CODE, "icon.png"), os.path.join(self.tmp, "icon.png"))

    def _patches(self, befehle):
        return [mock.patch.object(self.bau, "ROOT", self.tmp),
                mock.patch.object(self.bau, "DIST", self.dist),
                mock.patch.object(self.bau, "OUTPUT", os.path.join(self.tmp, "out")),
                mock.patch.object(self.bau, "run",
                                  lambda befehl, **_kw: befehle.append(befehl))]

    def _mit(self, patches, funktion, *args):
        with contextlib.ExitStack() as stack:
            for p in patches:
                stack.enter_context(p)
            stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
            funktion(*args)

    def test_l38_startdatei_je_paketart(self):
        befehle = []
        with mock.patch.dict(os.environ, {"APPIMAGETOOL": "/attrappe/appimagetool"}):
            self._mit(self._patches(befehle), self.bau.package_appimage, "0.63.2")
        appimage = _lesen(os.path.join(self.tmp, "build", "AppDir",
                                       self.bau.PACKAGE_NAME + ".desktop"))
        self._mit(self._patches(befehle) + [mock.patch.object(self.bau, "write_deb_icons")],
                  self.bau.package_deb, "0.63.2")
        deb = _lesen(os.path.join(self.tmp, "build", "deb", "usr", "share", "applications",
                                  self.bau.PACKAGE_NAME + ".desktop"))
        self.assertEqual(appimage.count("X-AppImage-Version"), 1)
        self.assertTrue(appimage.endswith("\nX-AppImage-Version=0.63.2\n"))
        self.assertNotIn("X-AppImage-Version", deb)
        # sonst gleich (bis auf den Startbefehl)
        self.assertEqual(appimage.replace("X-AppImage-Version=0.63.2\n", "")
                         .replace("Exec=" + self.bau.APP_NAME, "Exec=" + self.bau.PACKAGE_NAME),
                         deb)
        self.assertEqual(deb, self.bau.DESKTOP_ENTRY.format(exec=self.bau.PACKAGE_NAME,
                                                            wm_class=self.bau.WM_CLASS))
        # im Job tests (Linux, GitHub) ist desktop-file-utils installiert: dort Pflicht
        if os.environ.get("GITHUB_ACTIONS") == "true" and sys.platform.startswith("linux"):
            self.assertTrue(shutil.which("desktop-file-validate"), "desktop-file-validate fehlt")
        if shutil.which("desktop-file-validate"):
            for pfad in (os.path.join(self.tmp, "build", "AppDir",
                                      self.bau.PACKAGE_NAME + ".desktop"),
                         os.path.join(self.tmp, "build", "deb", "usr", "share", "applications",
                                      self.bau.PACKAGE_NAME + ".desktop")):
                ergebnis = subprocess.run(["desktop-file-validate", pfad],
                                          capture_output=True, text=True)
                self.assertEqual(ergebnis.returncode, 0, ergebnis.stdout + ergebnis.stderr)
                self.assertNotIn("error", ergebnis.stdout.lower())

    def test_l40_hinweisdatei_deb_ohne_appimage_laufzeit(self):
        befehle = []
        self._mit(self._patches(befehle) + [mock.patch.object(self.bau, "write_deb_icons")],
                  self.bau.package_deb, "0.63.2")
        stage = os.path.join(self.tmp, "build", "deb")
        for rel in (("opt", self.bau.PACKAGE_NAME), ("usr", "share", "doc",
                                                    self.bau.PACKAGE_NAME)):
            text = _lesen(os.path.join(stage, *rel, "THIRD_PARTY_NOTICES.txt"))
            self.assertNotIn("AppImage-Laufzeit", text, rel)
            self.assertIn("#### PyInstaller", text, rel)
            self.assertIn("Version 0.63.2,", text, rel)
        self.assertEqual(befehle[-1][:3], ["dpkg-deb", "--build", "--root-owner-group"])

    def test_l40_l42_komponenten_je_system(self):
        lizenzen = _modul("lizenzen")
        leer = os.path.join(self.tmp, "leer")
        os.makedirs(leer)
        schluessel = {}
        for system in ("linux", "linux-deb", "win32", "darwin"):
            gen = lizenzen.Generator(leer, system=system)
            gen.run()
            schluessel[system] = set(gen.components)
        self.assertIn("appimage", schluessel["linux"])                       # L41
        self.assertEqual(schluessel["linux-deb"], schluessel["linux"] - {"appimage"})  # L40
        for system in ("win32", "darwin"):                                   # L42
            self.assertNotIn("appimage", schluessel[system])
            self.assertEqual(schluessel[system], schluessel["linux-deb"])

    def test_l43_ds_store_wird_entfernt(self):
        ziel = os.path.join(self.tmp, "app")
        for rel in (".DS_Store", "_internal/customtkinter/assets/.DS_Store",
                    "_internal/customtkinter/assets/themes/blue.json"):
            pfad = os.path.join(ziel, rel)
            os.makedirs(os.path.dirname(pfad), exist_ok=True)
            with open(pfad, "w"):
                pass
        os.symlink("../.DS_Store", os.path.join(ziel, "_internal", ".DS_Store"))
        with contextlib.redirect_stdout(io.StringIO()):
            self.bau.remove_ds_store(ziel)
        rest = [os.path.join(b, n) for b, d, f in os.walk(ziel) for n in d + f]
        self.assertFalse([p for p in rest if os.path.basename(p) == ".DS_Store"], rest)
        self.assertTrue(os.path.isfile(os.path.join(
            ziel, "_internal/customtkinter/assets/themes/blue.json")))

    def test_l43_ds_store_im_bau_und_workflow(self):
        quelle = _lesen(os.path.join(CODE, "build.py"))
        bau_app = quelle[quelle.index("def build_app("):quelle.index("def check_no_readline(")]
        self.assertLess(bau_app.index("    remove_ds_store(target)\n"),
                        bau_app.index("    write_legal_files(target, version)\n"))
        schritt = "\n".join(_schritt(_lesen(BUILD_YML), "Paketinhalt pruefen (Linux)"))
        self.assertIn('find dist "$RUNNER_TEMP/deb" "$RUNNER_TEMP/appimage" -name .DS_Store',
                      schritt)
        # desktop-file-validate von Ubuntu 22.04 kennt SingleMainWindow nicht:
        # die Pruefung laeuft in test_l38 (Job tests, Ubuntu 24.04)
        self.assertNotIn("desktop-file-validate \"", schritt)
        self.assertIn('grep -qx "X-AppImage-Version=$VERSION" "$APP_DESKTOP"', schritt)
        self.assertIn('if grep -q "X-AppImage-Version" "$DEB_DESKTOP"; then', schritt)
        self.assertIn('exit "$FEHLER"', schritt)


if __name__ == "__main__":
    unittest.main(verbosity=2)
