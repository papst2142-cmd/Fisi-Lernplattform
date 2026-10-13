#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests fuer 0.63.2, Strang S5b (Bau-Ablauf auf GitHub und Werkzeuge).

  * B-A-01  CI-Teil "ibus": test_eingabe.py mit FISI_TEST_IBUS=1
  * B-P-03  kein "pkill -f" in Tests und Pruefskripten
  * B-K-08  dokumentierte Mindestversion von Python passt zu requirements.txt,
            start.py ist nicht strenger als die Doku
  * B-M-03  Zeitgrenzen fuer jeden Job, den Werkzeug-Schritt und jedes curl
  * B-M-04  fremde Actions auf Commit-SHA, Dependabot nur github-actions
  * B-M-07  Token oben nur lesend, kein ${{ }} im Shell-Text, benannte Secrets
  * B-M-09  release.yml prueft "gibt es das Release?" (Nachstellung des
            Skripts mit Attrappen fuer git, gh und python), Nachhol-Weg
  * FG-31   Update-Test: Lernstand vorher/nachher byte-gleich (statisch)
  * Schutz: Rechtsberatungs-Satz, Version-Pins, kein Mac-Neustart

Liest die Workflow-Dateien als Text (PyYAML ist in der CI nicht installiert).

Der Code-Ordner ist waehlbar (fuer die Rot-Probe gegen einen alten Stand):
    WORKFLOW_CODE=<ordner mit dem Code> python test_workflow_0632.py

Start:  python test_workflow_0632.py
"""

import ast
import glob
import os
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
CODE = os.path.abspath(os.environ.get("WORKFLOW_CODE") or HERE)

BUILD = os.path.join(CODE, ".github", "workflows", "build.yml")
RELEASE = os.path.join(CODE, ".github", "workflows", "release.yml")
DEPENDABOT = os.path.join(CODE, ".github", "dependabot.yml")
UPDATE_TEST = os.path.join(CODE, ".github", "update-test", "update_test.ps1")
CI_TESTS = os.path.join(CODE, "pruefung", "ci_tests.sh")

# Commit, auf den softprops/action-gh-release "v3" am 13.10.2026 zeigte
# (= v3.0.3; zweimal ermittelt: git ls-remote und Abruf des Tag-Objekts)
SOFTPROPS_SHA = "efb35369e0ad2afab669f228072c1b0d510eae64"

# Mindestversion von Python je Paket aus requirements.txt (PyPI
# "Requires-Python", abgerufen 13.10.2026). Neuer Pin -> hier eintragen.
REQUIRES_PYTHON = {
    "customtkinter==6.0.0": (3, 7),
    "pillow==12.3.0": (3, 10),
    "certifi==2026.7.22": (3, 7),
}


def _lesen(pfad):
    with open(pfad, encoding="utf-8") as fh:
        return fh.read()


def _jobs(text):
    """{Jobname: [Zeilen des Job-Blocks]} unter "jobs:" (Einrueckung 2)."""
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


def _run_bloecke(text):
    """Alle Shell-Texte: [(Zeilennummer, Text)] fuer jedes "run:"."""
    zeilen = text.splitlines()
    bloecke = []
    for i, zeile in enumerate(zeilen):
        m = re.match(r"^(\s*)(?:- )?run:\s*(.*)$", zeile)
        if not m:
            continue
        einzug = len(m.group(1))
        rest = m.group(2)
        if rest.startswith("|") or rest.startswith(">"):
            teil = []
            for folge in zeilen[i + 1:]:
                if folge.strip() and len(folge) - len(folge.lstrip()) <= einzug:
                    break
                teil.append(folge)
            bloecke.append((i + 1, "\n".join(teil)))
        else:
            bloecke.append((i + 1, rest))
    return bloecke


def _schritt(text, name):
    """Zeilen des Schritts "- name: <name>" (bis zum naechsten Schritt)."""
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


def _run_text(schritt_zeilen):
    """Shell-Text eines Schritts (Block nach "run: |"), ohne Einrueckung."""
    for i, zeile in enumerate(schritt_zeilen):
        m = re.match(r"^(\s*)run: \|\s*$", zeile)
        if m:
            einzug = len(m.group(1))
            teil = []
            for folge in schritt_zeilen[i + 1:]:
                if folge.strip() and len(folge) - len(folge.lstrip()) <= einzug:
                    break
                teil.append(folge)
            return textwrap.dedent("\n".join(teil)) + "\n"
    raise AssertionError("kein run-Block")


# ============================================================================
#  Schutz (auch auf 14b3bd4 gruen)
# ============================================================================

class SchutzTest(unittest.TestCase):

    def test_rechtsberatung_unveraendert(self):
        satz = ('            echo "**Hinweis:** Die Lizenz- und Rechtstexte dieses Programms '
                'sind keine Rechtsberatung und nicht anwaltlich geprüft."')
        self.assertEqual(_lesen(BUILD).splitlines().count(satz), 1)

    def test_version_pins_unveraendert(self):
        text = _lesen(BUILD)
        self.assertEqual(text.count('python-version: "3.12"'), 5)
        self.assertEqual(text.count('"flet[all]==1.0.1"'), 3)
        for pin in (
                "https://github.com/AppImage/appimagetool/releases/download/1.9.1/appimagetool-x86_64.AppImage",
                "https://github.com/AppImage/type2-runtime/releases/download/20251108/runtime-x86_64",
                '"ed4ce84f0d9caff66f50bcca6ff6f35aae54ce8135408b3fa33abfc3cb384eb0  appimagetool"',
                '"2fca8b443c92510f1483a883f60061ad09b46b978b2631c807cd873a47ec260d  runtime-x86_64"'):
            self.assertEqual(text.count(pin), 1, pin)
        runner = re.findall(r"(?:runs-on|- os):\s*(\S+)", text)
        self.assertEqual(sorted(runner), sorted([
            "${{", "windows-2025", "ubuntu-22.04", "macos-15", "macos-15-intel",
            "ubuntu-24.04", "ubuntu-24.04", "windows-2025", "windows-2025",
            "ubuntu-24.04", "ubuntu-24.04"]))
        # GitHub-eigene Actions bleiben auf ihrer Hauptversion
        eigene = sorted(set(re.findall(r"uses: (actions/[\w-]+@\S+)", text)))
        # N10 (B-M-08): actions/cache dazu, genau einmal (Android-Job)
        self.assertEqual(eigene, ["actions/cache@v6", "actions/checkout@v7",
                                  "actions/download-artifact@v8",
                                  "actions/setup-python@v7", "actions/upload-artifact@v7"])
        self.assertEqual(text.count("uses: actions/cache@"), 1)
        self.assertEqual(sorted(set(re.findall(r"uses: (actions/[\w-]+@\S+)", _lesen(RELEASE)))),
                         ["actions/checkout@v7", "actions/setup-python@v7"])

    def test_kein_macos_neustart(self):
        for pfad in (BUILD, RELEASE):
            text = _lesen(pfad)
            self.assertNotIn("continue-on-error", text)
            # keine Aktion, die Jobs oder Schritte selbst neu startet
            self.assertNotRegex(text, r"uses: \S*retry")
        self.assertIn("          - os: macos-15\n            label: macos-arm64\n"
                      "          - os: macos-15-intel\n            label: macos-intel\n",
                      _lesen(BUILD))

    def test_zeitgrenzen_der_testjobs_unveraendert(self):
        # K8 (Meldung 21): Zeitgrenzen der Pruefungen nur mit Freigabe aendern
        jobs = _jobs(_lesen(BUILD))
        for name in ("tests", "tests-windows", "update-test"):
            self.assertIn("    timeout-minutes: 30", jobs[name], name)


# ============================================================================
#  B-A-01 / B-P-03
# ============================================================================

class IbusTeilTest(unittest.TestCase):

    def test_matrix_ohne_teil_ibus(self):
        # Weg (c): Teil ibus laeuft nur im Container, nicht auf GitHub
        jobs = _jobs(_lesen(BUILD))
        self.assertIn("        teil: [spiel, lang, rest]", jobs["tests"])
        self.assertNotIn("ibus", "\n".join(z for z in jobs["tests"]
                                            if not z.lstrip().startswith("#")))

    def test_keine_ibus_werkzeuge_auf_github(self):
        schritt = "\n".join(_schritt(_lesen(BUILD), "Werkzeuge fuer die Tests"))
        self.assertNotIn("ibus", schritt)
        self.assertNotIn("python3-tk", schritt)

    def test_ci_tests_kennt_teil_ibus(self):
        text = _lesen(CI_TESTS)
        m = re.search(r"\n  ibus\)(.*?);;\n", text, re.S)
        self.assertIsNotNone(m, "Fall ibus) fehlt in ci_tests.sh")
        self.assertIn('DATEIEN="test_eingabe.py"', m.group(1))
        self.assertIn("export FISI_TEST_IBUS=1", m.group(1))
        # Teil rest setzt den Schalter nicht
        rest = re.search(r"\n  rest\)(.*?);;\n", text, re.S).group(1)
        self.assertNotIn("FISI_TEST_IBUS", rest)


class KeinPkillFTest(unittest.TestCase):

    def test_kein_pkill_f(self):
        dateien = (glob.glob(os.path.join(CODE, "test_*.py"))
                   + glob.glob(os.path.join(CODE, "pruefung", "*.py")))
        self.assertTrue(dateien)
        funde = []
        for pfad in dateien:
            baum = ast.parse(_lesen(pfad))
            for knoten in ast.walk(baum):
                if isinstance(knoten, (ast.List, ast.Tuple)) and knoten.elts:
                    erstes = knoten.elts[0]
                    if isinstance(erstes, ast.Constant) and erstes.value == "pkill":
                        werte = [e.value for e in knoten.elts if isinstance(e, ast.Constant)]
                        if "-f" in werte or "-x" not in werte or not {"-P", "-g", "-s"} & set(werte):
                            funde.append("%s:%d %s" % (os.path.basename(pfad), knoten.lineno, werte))
                elif isinstance(knoten, ast.Constant) and isinstance(knoten.value, str):
                    if re.match(r"\s*pkill\b.*\s-f\b", knoten.value):
                        funde.append("%s:%d %r" % (os.path.basename(pfad), knoten.lineno, knoten.value))
        for pfad in glob.glob(os.path.join(CODE, "pruefung", "*.sh")) + [BUILD, RELEASE]:
            for nr, zeile in enumerate(_lesen(pfad).splitlines(), 1):
                if re.search(r"\bpkill\b[^#\n]*\s-f\b", zeile):
                    funde.append("%s:%d" % (os.path.basename(pfad), nr))
        self.assertEqual(funde, [])


# ============================================================================
#  B-K-08
# ============================================================================

class PythonVersionTest(unittest.TestCase):

    def _doku_min(self):
        m = re.search(r"^  \* Python (\d+)\.(\d+) oder neuer mit Tkinter",
                      _lesen(os.path.join(CODE, "LIESMICH.txt")), re.M)
        self.assertIsNotNone(m)
        return int(m.group(1)), int(m.group(2))

    def test_mindestversion_passt_zu_requirements(self):
        pins = [z.strip() for z in _lesen(os.path.join(CODE, "requirements.txt")).splitlines()
                if z.strip() and not z.startswith("#")]
        fehlt = [p for p in pins if p not in REQUIRES_PYTHON]
        self.assertEqual(fehlt, [], "neuer Pin: Requires-Python nachsehen und eintragen")
        self.assertGreaterEqual(self._doku_min(), max(REQUIRES_PYTHON[p] for p in pins))

    def test_doku_gleich_und_wie_ci(self):
        doku = self._doku_min()
        app = re.search(r"^Benoetigt:  Python (\d+)\.(\d+) oder neuer",
                        _lesen(os.path.join(CODE, "app_gui.py")), re.M)
        self.assertEqual((int(app.group(1)), int(app.group(2))), doku)
        # gebaut und getestet wird mit dieser Version (alle setup-python)
        self.assertEqual(set(re.findall(r'python-version: "(\d+\.\d+)"', _lesen(BUILD))),
                         {"%d.%d" % doku})

    def test_start_nicht_strenger_als_doku(self):
        # F10-Auflage: start.py darf nicht strenger werden als heute; es
        # lehnt hoechstens ab, was auch die Doku ausschliesst
        baum = ast.parse(_lesen(os.path.join(CODE, "start.py")))
        werte = [ast.literal_eval(k.value) for k in baum.body if isinstance(k, ast.Assign)
                 and any(getattr(t, "id", "") == "MIN_PYTHON" for t in k.targets)]
        self.assertEqual(len(werte), 1)
        self.assertLessEqual(werte[0], self._doku_min())
        self.assertLessEqual(werte[0], (3, 8))


# ============================================================================
#  B-M-03
# ============================================================================

class ZeitgrenzenTest(unittest.TestCase):

    def test_jeder_job_hat_zeitgrenze(self):
        for pfad in (BUILD, RELEASE):
            for name, zeilen in _jobs(_lesen(pfad)).items():
                if any(z.startswith("    uses: ") for z in zeilen):
                    continue        # Aufruf von build.yml: Grenzen gelten dort je Job
                self.assertTrue(any(re.match(r"^    timeout-minutes: \d+$", z) for z in zeilen),
                                "%s: Job %s ohne timeout-minutes" % (os.path.basename(pfad), name))

    def test_werte(self):
        jobs = _jobs(_lesen(BUILD))
        soll = {"build": 30, "android": 30, "vorab": 15, "release": 15,
                "tests": 30, "tests-windows": 30, "update-test": 30}
        ist = {}
        for name, zeilen in jobs.items():
            for z in zeilen:
                m = re.match(r"^    timeout-minutes: (\d+)$", z)
                if m:
                    ist[name] = int(m.group(1))
        self.assertEqual(ist, soll)
        self.assertIn("    timeout-minutes: 10", _jobs(_lesen(RELEASE))["tag"])

    def test_werkzeug_schritt_hat_zeitgrenze(self):
        schritt = _schritt(_lesen(BUILD), "Linux-Werkzeuge installieren")
        self.assertIn("        timeout-minutes: 10", schritt)

    def test_jedes_curl_hat_zeitgrenze(self):
        zeilen = [z for z in _lesen(BUILD).splitlines() if re.search(r"\bcurl\s", z)]
        # N10 (CI-a): dazu der Download im Schritt "Android-Laufzeit vorab
        # laden und pruefen"; jedes curl auch mit Wiederholung (B-M-02)
        self.assertEqual(len(zeilen), 4)
        for z in zeilen:
            self.assertRegex(z, r"--connect-timeout \d+ ")
            self.assertRegex(z, r"--max-time \d+ ")
            self.assertRegex(z, r"--retry \d+ --retry-delay \d+ --retry-all-errors ")


# ============================================================================
#  B-M-04 / F9
# ============================================================================

class ActionsTest(unittest.TestCase):

    def test_fremde_actions_auf_sha(self):
        for pfad in (BUILD, RELEASE):
            for zeile in _lesen(pfad).splitlines():
                m = re.match(r"^\s*(?:- )?uses: (\S+)", zeile)
                if not m or m.group(1).startswith(("actions/", "./")):
                    continue
                self.assertRegex(m.group(1), r"@[0-9a-f]{40}$", zeile)

    def test_softprops_auf_v3_stand(self):
        text = _lesen(BUILD)
        zeile = "      - uses: softprops/action-gh-release@%s # v3.0.3" % SOFTPROPS_SHA
        self.assertEqual(text.splitlines().count(zeile), 2)
        self.assertNotIn("softprops/action-gh-release@v", text)

    def test_dependabot_nur_actions_woechentlich(self):
        zeilen = [z for z in _lesen(DEPENDABOT).splitlines()
                  if z.strip() and not z.lstrip().startswith("#")]
        self.assertEqual(zeilen, [
            "version: 2",
            "updates:",
            '  - package-ecosystem: "github-actions"',
            '    directory: "/"',
            "    schedule:",
            '      interval: "weekly"',
        ])


# ============================================================================
#  B-M-07
# ============================================================================

class RechteTest(unittest.TestCase):

    def test_rechte_oben_nur_lesen(self):
        text = _lesen(BUILD)
        kopf = text[:text.index("\njobs:\n")]
        self.assertRegex(kopf, r"\npermissions:\n  contents: read\n")
        jobs = _jobs(text)
        for name, zeilen in jobs.items():
            hat_schreib = "      contents: write" in zeilen
            self.assertEqual(hat_schreib, name in ("vorab", "release"), name)

    def test_kein_ausdruck_im_shell_text(self):
        for pfad in (BUILD, RELEASE):
            funde = [(nr, t) for nr, t in _run_bloecke(_lesen(pfad)) if "${{" in t]
            self.assertEqual(funde, [], os.path.basename(pfad))

    def test_testversion_text_unveraendert(self):
        # Der sichtbare Text der Testversion bleibt zeichengleich
        text = _lesen(BUILD)
        satz = ('Gebaut aus dem Zweig \\`$REF_NAME\\` (Stand \\`${GITHUB_SHA::7}\\`). '
                'Intern trägt sie noch die Versionsnummer $VERSION; die neue Nummer '
                'wird erst bei der Freigabe gesetzt.')
        self.assertEqual(text.count(satz), 2)
        for name in ("Dateien und Text der Testversion (Linux und Handy)",
                     "Datei und Text der Testversion"):
            self.assertIn("          REF_NAME: ${{ github.ref_name }}", _schritt(text, name))

    def test_benannte_secrets(self):
        build, release = _lesen(BUILD), _lesen(RELEASE)
        self.assertNotRegex(release, r"(?m)^\s*secrets: inherit")
        benutzt = set(re.findall(r"secrets\.([A-Z0-9_]+)", build))
        self.assertEqual(benutzt, {"ANDROID_KEYSTORE_BASE64", "ANDROID_KEYSTORE_PASSWORD"})
        kopf = build[:build.index("\njobs:\n")]
        erklaert = set(re.findall(r"^      ([A-Z0-9_]+):\n        required: false$", kopf, re.M))
        self.assertEqual(erklaert, benutzt)
        weiter = dict(re.findall(r"^      ([A-Z0-9_]+): \$\{\{ secrets\.([A-Z0-9_]+) \}\}$",
                                 release, re.M))
        self.assertEqual(weiter, {s: s for s in benutzt})


# ============================================================================
#  B-M-09
# ============================================================================

class ReleaseNachholenTest(unittest.TestCase):
    """Das Skript des Schritts "Neue Version?" aus release.yml mit Attrappen
    fuer git, gh und python, so wie GitHub es startet (bash -eo pipefail)."""

    ATTRAPPEN = {
        "python": '#!/bin/bash\ncase "$*" in *app_version*) echo 0.63.2 ;; esac\n'
                  'echo "python $*" >> "$PROTOKOLL"\nexit 0\n',
        "git": '#!/bin/bash\necho "git $*" >> "$PROTOKOLL"\n'
               '[ "$ATTRAPPE_TAG" = da ] && exit 0\nexit 2\n',
        # gh wie auf dem Runner: ohne GH_TOKEN bricht es ab (Nacharbeit L3)
        "gh": '#!/bin/bash\necho "gh $*" >> "$PROTOKOLL"\n'
              'if [ -z "$GH_TOKEN" ]; then echo "gh: To use GitHub CLI in a GitHub '
              'Actions workflow, set the GH_TOKEN environment variable." >&2; exit 4; fi\n'
              'case "$ATTRAPPE_GH" in\n'
              '  da) echo v0.63.2; exit 0 ;;\n'
              '  404) echo \'{"message":"Not Found","status":"404"}\'; '
              'echo "gh: Not Found (HTTP 404)" >&2; exit 1 ;;\n'
              '  fehler404) echo "gh: Bad Gateway (HTTP 502), Anfrage 7404" >&2; exit 1 ;;\n'
              '  *) echo "gh: Bad Gateway (HTTP 502)" >&2; exit 1 ;;\nesac\n',
    }

    def _lauf(self, tag, gh):
        if not shutil.which("bash"):
            self.skipTest("kein bash")
        schritt = _schritt(_lesen(RELEASE), "Neue Version?")
        skript = _run_text(schritt)
        # env des Schritts wie auf dem Runner: GH_TOKEN nur, wenn der Schritt
        # ihn setzt (Nacharbeit L3)
        token = "x" if "          GH_TOKEN: ${{ github.token }}" in schritt else ""
        with tempfile.TemporaryDirectory() as tmp:
            bin_ordner = os.path.join(tmp, "bin")
            os.mkdir(bin_ordner)
            for name, inhalt in self.ATTRAPPEN.items():
                p = os.path.join(bin_ordner, name)
                with open(p, "w", encoding="utf-8", newline="\n") as fh:
                    fh.write(inhalt)
                os.chmod(p, 0o755)
            pfad = os.path.join(tmp, "schritt.sh")
            with open(pfad, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(skript)
            ausgabe = os.path.join(tmp, "output")
            protokoll = os.path.join(tmp, "protokoll")
            open(ausgabe, "w").close()
            open(protokoll, "w").close()
            env = dict(os.environ, PATH=bin_ordner + os.pathsep + os.environ.get("PATH", ""),
                       GITHUB_OUTPUT=ausgabe, GITHUB_REPOSITORY="beispiel/repo",
                       PROTOKOLL=protokoll, ATTRAPPE_TAG=tag, ATTRAPPE_GH=gh,
                       GH_TOKEN=token)
            r = subprocess.run(["bash", "--noprofile", "--norc", "-eo", "pipefail", pfad],
                               env=env, capture_output=True, text=True, timeout=60)
            werte = dict(z.split("=", 1) for z in _lesen(ausgabe).splitlines() if "=" in z)
            return r.returncode, werte, r.stdout + r.stderr, _lesen(protokoll)

    def test_neue_version_legt_tag_an(self):
        rc, werte, text, prot = self._lauf("fehlt", "404")
        self.assertEqual(rc, 0, text)
        self.assertEqual(werte, {"tag": "v0.63.2", "neu": "ja"})
        self.assertNotIn("gh ", prot)

    def test_tag_und_release_da_nichts_zu_tun(self):
        rc, werte, text, prot = self._lauf("da", "da")
        self.assertEqual(rc, 0, text)
        self.assertEqual(werte, {})
        self.assertIn("gh api repos/beispiel/repo/releases/tags/v0.63.2", prot)

    def test_tag_ohne_release_wird_nachgeholt(self):
        rc, werte, text, prot = self._lauf("da", "404")
        self.assertEqual(rc, 0, text)
        self.assertEqual(werte, {"tag": "v0.63.2", "neu": "nein"})
        self.assertIn("nachgeholt", text)

    def test_unklare_antwort_bricht_ab(self):
        rc, werte, text, prot = self._lauf("da", "fehler")
        self.assertNotEqual(rc, 0)
        self.assertEqual(werte, {})
        self.assertIn("HTTP 502", text)

    def test_unklare_antwort_mit_404_im_text_bricht_ab(self):
        # Nacharbeit L3 (R5): nur genau "HTTP 404" heisst "Release fehlt"
        rc, werte, text, prot = self._lauf("da", "fehler404")
        self.assertNotEqual(rc, 0)
        self.assertEqual(werte, {})
        schritt = "\n".join(_schritt(_lesen(RELEASE), "Neue Version?"))
        # N10 (B-M-02): im Wiederholungs-Block, "HTTP 404" beendet ihn
        self.assertIn('                *"HTTP 404"*) break ;;', schritt)
        self.assertEqual(schritt.count('"HTTP 404"'), 1)

    def test_schritt_hat_gh_token(self):
        # Nacharbeit L3 (R6): ohne GH_TOKEN scheitert gh auf dem Runner; jeder
        # Push auf main mit vorhandenem Tag waere rot, Nachholen nie moeglich
        schritt = _schritt(_lesen(RELEASE), "Neue Version?")
        self.assertIn("        env:", schritt)
        self.assertIn("          GH_TOKEN: ${{ github.token }}", schritt)
        rc, werte, text, prot = self._lauf("da", "da")
        self.assertEqual(rc, 0, text)

    def test_tag_anlegen_nur_bei_neuem_tag(self):
        schritt = _schritt(_lesen(RELEASE), "Tag anlegen")
        self.assertIn("        if: steps.check.outputs.tag != '' && steps.check.outputs.neu == 'ja'",
                      schritt)
        self.assertIn("    if: needs.tag.outputs.tag != ''", _jobs(_lesen(RELEASE))["release"])

    def test_nachholweg_bleibt(self):
        # Schutz (auch auf 14b3bd4 gruen bis auf den Kopftext): Hand-Lauf auf
        # dem Tag ist ein Release-Lauf
        text = _lesen(BUILD)
        self.assertIn("  workflow_dispatch:\n", text)
        self.assertIn("startsWith(github.ref, 'refs/tags/v')", "\n".join(_jobs(text)["release"]))
        self.assertIn('#  Nachholen, wenn ein Release-Lauf nach dem Anlegen des Tags scheitert:', text)


# ============================================================================
#  FG-31
# ============================================================================

class UpdateTestByteGleichTest(unittest.TestCase):

    def test_pruefung_byte_gleich(self):
        text = _lesen(UPDATE_TEST)
        zeilen = text.splitlines()
        vorher = zeilen.index('$dbVorherAngabe = DbProtokoll "vorher, alte Version laeuft" $DB')
        nachher = zeilen.index('$dbNachherAngabe = DbProtokoll "nachher, neue Version laeuft" $DB')
        # vorher: alte Version laeuft, vor dem Update; nachher: neue Version laeuft
        self.assertLess(zeilen.index('Liste "alte Version laeuft"'), vorher)
        self.assertLess(vorher, zeilen.index('Write-Host "=== 3. Update auf $NeuVersion wie aus dem Programm heraus"'))
        self.assertLess(zeilen.index('Liste "nach dem Update"'), nachher)
        self.assertIn('Pruefung "Lernstand byte-gleich" $gleich', text)
        self.assertIn("($dbVorherAngabe.Hash -ceq $dbNachherAngabe.Hash)", text)
        self.assertIn("($dbVorherAngabe.Laenge -eq $dbNachherAngabe.Laenge)", text)
        self.assertIn("[System.Security.Cryptography.SHA256]::Create()", text)
        self.assertIn('@("-wal", "-journal", "-shm")', text)
        # die bisherige Pruefung bleibt
        self.assertEqual(text.count('Pruefung "Lernstand im selben Ordner"'), 1)


# ============================================================================
#  N10: CI-a / B-E-07  Android-Laufzeit vorab laden und pruefen
# ============================================================================

LAUFZEIT_SCHRITT = "Android-Laufzeit vorab laden und pruefen"
LAUFZEIT_NACHHER = "Android-Laufzeit unveraendert (nichts nachgeladen)"


def _schritt_namen(job_zeilen):
    return [m.group(1).strip() for m in
            (re.match(r"^      - name: (.*)$", z) for z in job_zeilen) if m]


class AndroidLaufzeitTest(unittest.TestCase):
    """Der Schritt vor "APK bauen" mit Attrappen fuer curl und sleep, so wie
    GitHub ihn startet (bash -e). Die Liste der Dateien wird fuer den Lauf
    durch kleine Prueflinge mit eigenen Pruefsummen ersetzt; die echten
    Pruefsummen prueft test_pruefsummen_fest."""

    CURL = r'''#!/bin/bash
ziel=""; url=""
while [ $# -gt 0 ]; do
  case "$1" in
    -o) ziel="$2"; shift 2 ;;
    --retry|--retry-delay|--connect-timeout|--max-time) shift 2 ;;
    -*) shift ;;
    *) url="$1"; shift ;;
  esac
done
name=$(basename "$url")
echo "curl $name" >> "$PROTOKOLL"
zaehler="$ATTRAPPE_DIR/zaehler_$name"
n=$(( $(cat "$zaehler" 2>/dev/null || echo 0) + 1 )); echo "$n" > "$zaehler"
case "$ATTRAPPE_CURL" in
  null_einmal) if [ "$n" = 1 ]; then head -c 4096 /dev/zero > "$ziel"; exit 0; fi ;;
  null_immer) head -c 4096 /dev/zero > "$ziel"; exit 0 ;;
  leer_immer) : > "$ziel"; exit 0 ;;
  falsch) echo falsch > "$ziel"; exit 0 ;;
  netz) exit 7 ;;
esac
cp "$ATTRAPPE_DIR/server/$name" "$ziel"
'''

    def _prueflinge(self, tmp):
        """Kleine Dateien wie auf dem Server: {Name: (Summe, Inhalt)}."""
        import hashlib
        import io
        import tarfile
        import zipfile
        server = os.path.join(tmp, "server")
        os.makedirs(server)
        dateien = {}
        puffer = io.BytesIO()
        with tarfile.open(fileobj=puffer, mode="w:gz") as tar:
            info = tarfile.TarInfo("libpythonbundle.so")
            daten = b"bundle" * 100
            info.size = len(daten)
            tar.addfile(info, io.BytesIO(daten))
        dateien["python-android-dart-3.14.7-arm64-v8a.tar.gz"] = puffer.getvalue()
        dateien["libdart_bridge-android-arm64-v8a-py3.14.so"] = b"\x7fELF" + b"\x00\x01" * 50
        dateien["manifest.json"] = b'{"default_python_version": "3.14"}'
        puffer = io.BytesIO()
        with zipfile.ZipFile(puffer, "w") as z:
            z.writestr("vorlage.txt", "vorlage")
        dateien["flet-build-template.zip"] = puffer.getvalue()
        # passende Summe, aber kein Archiv (nur fuer test_kaputtes_archiv)
        dateien["kaputt.tar.gz"] = b"kein archiv" * 10
        for name, inhalt in dateien.items():
            with open(os.path.join(server, name), "wb") as fh:
                fh.write(inhalt)
        self._summen = {n: (hashlib.sha256(i).hexdigest(), i) for n, i in dateien.items()}
        return self._summen

    ZIELE = {
        "python-android-dart-3.14.7-arm64-v8a.tar.gz":
            "python-build/v3.14.7/python-android-dart-3.14.7-arm64-v8a.tar.gz",
        "libdart_bridge-android-arm64-v8a-py3.14.so":
            "dart-bridge/v1.10.0/libdart_bridge-android-arm64-v8a-py3.14.so",
        "manifest.json": "python-build/manifest-20260921.json",
        "flet-build-template.zip": "build-template/v1.0.1/flet-build-template.zip",
    }

    def _skript(self, name, liste):
        """Shell-Text des Schritts; die Liste (heredoc LISTE) ersetzt."""
        skript = _run_text(_schritt(_lesen(BUILD), name))
        if liste is None:
            return skript
        m = re.search(r"<<LISTE\n(.*?)\nLISTE\n", skript, re.S)
        self.assertIsNotNone(m, "Liste (heredoc LISTE) fehlt")
        return skript[:m.start(1)] + liste + skript[m.end(1):]

    def _lauf(self, tmp, curl="gut", vorher=None, namen=None, nur_nachher=False):
        """Fuehrt den Schritt aus. vorher: {Ziel relativ: bytes} im Cache."""
        if not shutil.which("bash"):
            self.skipTest("kein bash")
        if not os.path.isdir(os.path.join(tmp, "server")):
            self._prueflinge(tmp)
        summen = self._summen
        namen = namen or list(self.ZIELE)
        liste = "\n".join("%s %s https://beispiel.invalid/x/%s" % (
            summen[n][0], self.ZIELE.get(n, "python-build/v3.14.7/" + n), n) for n in namen)
        home = os.path.join(tmp, "home")
        cache = os.path.join(home, ".flet", "cache")
        for rel, inhalt in (vorher or {}).items():
            p = os.path.join(cache, rel)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "wb") as fh:
                fh.write(inhalt)
        bin_ordner = os.path.join(tmp, "bin")
        os.makedirs(bin_ordner, exist_ok=True)
        for name, inhalt in (("curl", self.CURL), ("sleep", "#!/bin/bash\nexit 0\n")):
            p = os.path.join(bin_ordner, name)
            with open(p, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(inhalt)
            os.chmod(p, 0o755)
        runner_temp = os.path.join(tmp, "runner_temp")
        os.makedirs(runner_temp, exist_ok=True)
        github_env = os.path.join(tmp, "github_env")
        protokoll = os.path.join(tmp, "protokoll")
        open(protokoll, "a").close()
        env = dict(os.environ, PATH=bin_ordner + os.pathsep + os.environ.get("PATH", ""),
                   HOME=home, RUNNER_TEMP=runner_temp, GITHUB_ENV=github_env,
                   PROTOKOLL=protokoll, ATTRAPPE_DIR=tmp, ATTRAPPE_CURL=curl,
                   FLET_CACHE_DIR=cache)
        schritte = [] if nur_nachher else [self._skript(LAUFZEIT_SCHRITT, liste)]
        if nur_nachher:
            schritte.append(self._skript(LAUFZEIT_NACHHER, None))
        text = ""
        rc = 0
        for i, skript in enumerate(schritte):
            pfad = os.path.join(tmp, "schritt%d.sh" % i)
            with open(pfad, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(skript)
            r = subprocess.run(["bash", "--noprofile", "--norc", "-e", pfad], env=env,
                               capture_output=True, text=True, timeout=120)
            text += r.stdout + r.stderr
            rc = r.returncode
        return rc, text, _lesen(protokoll), cache

    def _inhalt(self, cache, rel):
        with open(os.path.join(cache, rel), "rb") as fh:
            return fh.read()

    # -- statisch ------------------------------------------------------------

    def test_schritt_nur_im_android_job_vor_apk_bauen(self):
        jobs = _jobs(_lesen(BUILD))
        namen = _schritt_namen(jobs["android"])
        self.assertLess(namen.index("Flet installieren"), namen.index(LAUFZEIT_SCHRITT))
        self.assertLess(namen.index(LAUFZEIT_SCHRITT), namen.index("APK bauen"))
        self.assertEqual(namen.index(LAUFZEIT_NACHHER), namen.index("APK bauen") + 1)
        for job, zeilen in jobs.items():
            if job != "android":
                self.assertNotIn(LAUFZEIT_SCHRITT, "\n".join(zeilen), job)
                self.assertNotIn("FLET_CACHE_DIR", "\n".join(zeilen), job)

    def test_pruefsummen_fest(self):
        skript = _run_text(_schritt(_lesen(BUILD), LAUFZEIT_SCHRITT))
        liste = re.search(r"<<LISTE\n(.*?)\nLISTE\n", skript, re.S).group(1).splitlines()
        self.assertEqual(len(liste), 8)
        ziele = []
        for zeile in liste:
            summe, ziel, url = zeile.split(" ")
            self.assertRegex(summe, r"^[0-9a-f]{64}$")
            self.assertEqual(os.path.basename(ziel), os.path.basename(url)
                             if not ziel.endswith(".json") else "manifest-20260921.json")
            ziele.append(ziel)
        # alle drei ABIs: Gradle laedt alle drei, auch wenn die APK nur arm64 enthaelt
        for abi in ("arm64-v8a", "x86_64", "armeabi-v7a"):
            self.assertIn("python-build/v3.14.7/python-android-dart-3.14.7-%s.tar.gz" % abi, ziele)
            self.assertIn("dart-bridge/v1.10.0/libdart_bridge-android-%s-py3.14.so" % abi, ziele)
        self.assertIn("build-template/v1.0.1/flet-build-template.zip", ziele)
        self.assertEqual(len(set(ziele)), 8)
        self.assertIn('echo "FLET_CACHE_DIR=$CACHE" >> "$GITHUB_ENV"', skript)
        # flet-Fassung im Schritt = Fassung im Workflow
        self.assertIn("releases/download/v1.0.1", skript)
        self.assertEqual(_lesen(BUILD).count('"flet[all]==1.0.1"'), 3)

    # -- Verhalten -------------------------------------------------------------

    def test_leerer_cache_laedt_alles(self):
        with tempfile.TemporaryDirectory() as tmp:
            rc, text, prot, cache = self._lauf(tmp)
            self.assertEqual(rc, 0, text)
            for name, rel in self.ZIELE.items():
                self.assertEqual(self._inhalt(cache, rel), self._summen[name][1])
            self.assertEqual(prot.count("curl "), 4)
            self.assertIn("Android-Laufzeit: 4 Dateien vorab geladen und geprueft", text)
            self.assertIn("FLET_CACHE_DIR=%s" % cache, _lesen(os.path.join(tmp, "github_env")))

    def test_nullbyte_datei_im_cache_wird_neu_geladen(self):
        # B-E-07: eine Datei nur aus Nullbytes wird nicht verwendet
        rel = self.ZIELE["python-android-dart-3.14.7-arm64-v8a.tar.gz"]
        with tempfile.TemporaryDirectory() as tmp:
            rc, text, prot, cache = self._lauf(tmp, vorher={rel: b"\x00" * 11082})
            self.assertEqual(rc, 0, text)
            self.assertIn("Datei im Cache unbrauchbar (nur Nullbytes), wird neu geladen: " + rel, text)
            self.assertEqual(self._inhalt(cache, rel),
                             self._summen["python-android-dart-3.14.7-arm64-v8a.tar.gz"][1])

    def test_leere_datei_im_cache_wird_neu_geladen(self):
        rel = self.ZIELE["libdart_bridge-android-arm64-v8a-py3.14.so"]
        with tempfile.TemporaryDirectory() as tmp:
            rc, text, prot, cache = self._lauf(tmp, vorher={rel: b""})
            self.assertEqual(rc, 0, text)
            self.assertIn("Datei im Cache unbrauchbar (leer (0 Bytes)), wird neu geladen: " + rel, text)
            self.assertEqual(self._inhalt(cache, rel),
                             self._summen["libdart_bridge-android-arm64-v8a-py3.14.so"][1])

    def test_gueltige_datei_im_cache_wird_nicht_geladen(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._prueflinge(tmp)
            rel = self.ZIELE["flet-build-template.zip"]
            rc, text, prot, cache = self._lauf(
                tmp, vorher={rel: self._summen["flet-build-template.zip"][1]})
            self.assertEqual(rc, 0, text)
            self.assertIn("vorhanden und geprueft: " + rel, text)
            self.assertNotIn("curl flet-build-template.zip", prot)
            self.assertEqual(prot.count("curl "), 3)

    def test_alte_datei_im_cache_wird_neuer_als_server(self):
        # Gradle (onlyIfModified) laedt nur, wenn die Datei auf dem Server
        # neuer ist; nach dem Schritt ist jede Datei "jetzt" geaendert
        import time
        with tempfile.TemporaryDirectory() as tmp:
            self._prueflinge(tmp)
            rel = self.ZIELE["flet-build-template.zip"]
            p = os.path.join(tmp, "home", ".flet", "cache", rel)
            os.makedirs(os.path.dirname(p))
            with open(p, "wb") as fh:
                fh.write(self._summen["flet-build-template.zip"][1])
            os.utime(p, (946684800, 946684800))        # 01.01.2000
            vorher = time.time() - 5
            rc, text, prot, cache = self._lauf(tmp)
            self.assertEqual(rc, 0, text)
            self.assertGreater(os.path.getmtime(p), vorher)

    def test_download_nullbytes_wird_wiederholt(self):
        with tempfile.TemporaryDirectory() as tmp:
            rc, text, prot, cache = self._lauf(tmp, curl="null_einmal")
            self.assertEqual(rc, 0, text)
            self.assertEqual(text.count("Wiederholung wegen Download-Fehler (nur Nullbytes)"), 4)
            self.assertEqual(prot.count("curl "), 8)
            for name, rel in self.ZIELE.items():
                self.assertEqual(self._inhalt(cache, rel), self._summen[name][1])

    def test_download_immer_nullbytes_bricht_ab(self):
        with tempfile.TemporaryDirectory() as tmp:
            rc, text, prot, cache = self._lauf(tmp, curl="null_immer")
            self.assertNotEqual(rc, 0)
            self.assertIn("nach 3 Versuchen unbrauchbar (nur Nullbytes)", text)
            self.assertEqual(prot.count("curl "), 3)
            rel = self.ZIELE["python-android-dart-3.14.7-arm64-v8a.tar.gz"]
            self.assertFalse(os.path.exists(os.path.join(cache, rel)))
            self.assertFalse(os.path.exists(os.path.join(cache, rel + ".tmp")))

    def test_download_leer_bricht_ab(self):
        with tempfile.TemporaryDirectory() as tmp:
            rc, text, prot, cache = self._lauf(tmp, curl="leer_immer")
            self.assertNotEqual(rc, 0)
            self.assertIn("nach 3 Versuchen unbrauchbar (leer (0 Bytes))", text)

    def test_falsche_pruefsumme_bricht_ab(self):
        with tempfile.TemporaryDirectory() as tmp:
            rc, text, prot, cache = self._lauf(tmp, curl="falsch")
            self.assertNotEqual(rc, 0)
            self.assertIn("nach 3 Versuchen unbrauchbar (kein gueltiges Archiv)", text)
        with tempfile.TemporaryDirectory() as tmp:
            rc, text, prot, cache = self._lauf(
                tmp, curl="falsch", namen=["libdart_bridge-android-arm64-v8a-py3.14.so"])
            self.assertNotEqual(rc, 0)
            self.assertIn("nach 3 Versuchen unbrauchbar (Pruefsumme falsch)", text)

    def test_netzfehler_bricht_nach_3_versuchen_ab(self):
        with tempfile.TemporaryDirectory() as tmp:
            rc, text, prot, cache = self._lauf(tmp, curl="netz")
            self.assertNotEqual(rc, 0)
            self.assertEqual(prot.count("curl "), 3)
            self.assertIn("nach 3 Versuchen unbrauchbar (fehlt)", text)

    def test_kaputtes_archiv_trotz_passender_summe(self):
        with tempfile.TemporaryDirectory() as tmp:
            rc, text, prot, cache = self._lauf(tmp, namen=["kaputt.tar.gz"])
            self.assertNotEqual(rc, 0)
            self.assertIn("unbrauchbar (kein gueltiges Archiv)", text)

    def test_nachher_unveraendert_gruen(self):
        with tempfile.TemporaryDirectory() as tmp:
            rc, text, prot, cache = self._lauf(tmp)
            self.assertEqual(rc, 0, text)
            rc, text, prot, cache = self._lauf(tmp, nur_nachher=True)
            self.assertEqual(rc, 0, text)
            self.assertIn("Android-Laufzeit: alle 4 Dateien unveraendert, nichts nachgeladen", text)

    def test_nachher_ersetzte_datei_rot(self):
        # so ersetzt Gradle (tempAndMove): neue Datei, gleicher Inhalt
        with tempfile.TemporaryDirectory() as tmp:
            rc, text, prot, cache = self._lauf(tmp)
            self.assertEqual(rc, 0, text)
            rel = self.ZIELE["python-android-dart-3.14.7-arm64-v8a.tar.gz"]
            ziel = os.path.join(cache, rel)
            shutil.copy(ziel, ziel + ".neu")
            os.replace(ziel + ".neu", ziel)
            os.utime(ziel, (1790000000, 1790000000))
            rc, text, prot, cache = self._lauf(tmp, nur_nachher=True)
            self.assertNotEqual(rc, 0)
            self.assertIn("FEHLER: %s wurde waehrend des Baus neu geladen oder ersetzt" % rel, text)

    def test_nachher_fremde_laufzeit_rot(self):
        with tempfile.TemporaryDirectory() as tmp:
            rc, text, prot, cache = self._lauf(tmp)
            self.assertEqual(rc, 0, text)
            fremd = os.path.join(cache, "python-build", "v3.12.14",
                                 "python-android-dart-3.12.14-arm64-v8a.tar.gz")
            os.makedirs(os.path.dirname(fremd))
            with open(fremd, "wb") as fh:
                fh.write(b"x")
            rc, text, prot, cache = self._lauf(tmp, nur_nachher=True)
            self.assertNotEqual(rc, 0)
            self.assertIn("FEHLER: Gradle hat eine andere Laufzeit-Datei geladen: "
                          "python-build/v3.12.14/python-android-dart-3.12.14-arm64-v8a.tar.gz", text)


# ============================================================================
#  N10: B-H-09  APK ohne Bytecode-Reste
# ============================================================================

class BytecodeTest(unittest.TestCase):

    def _apk_pruefen(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "apk_pruefen_n10", os.path.join(CODE, "pruefung", "apk_pruefen.py"))
        modul = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(modul)
        return modul

    def test_selbsttest_ohne_bytecode(self):
        schritt = _schritt(_lesen(BUILD), "Gemeinsame Dateien kopieren und Selbsttest")
        self.assertIn("        env:", schritt)
        self.assertIn('          PYTHONDONTWRITEBYTECODE: "1"', schritt)
        self.assertIn("python mobile/src/main.py --selbsttest", "\n".join(schritt))

    def test_apk_pruefung_im_android_job(self):
        schritt = "\n".join(_schritt(
            _lesen(BUILD), "APK pruefen (Paket, Beschriftung, Zertifikat wie letztes Release)"))
        self.assertIn("python pruefung/apk_pruefen.py", schritt)

    def _apk(self, tmp, namen):
        import io
        import zipfile
        app = io.BytesIO()
        with zipfile.ZipFile(app, "w") as z:
            for name in namen:
                z.writestr(name, b"x")
        pfad = os.path.join(tmp, "probe.apk")
        with zipfile.ZipFile(pfad, "w") as z:
            z.writestr("assets/app.zip", app.getvalue())
        return pfad

    def _check(self, namen):
        modul = self._apk_pruefen()
        modul.manifest_strings = lambda apk: [modul.PACKAGE, modul.LABEL]
        modul.certificates = lambda apk: {"v2": "ab"}
        with tempfile.TemporaryDirectory() as tmp:
            return modul.check(self._apk(tmp, namen))

    def test_apk_mit_pycache_rot(self):
        # so sah die APK von 0.63.1 aus (18 Dateien, gut 2 MB)
        fehler, zeilen = self._check(["main.pyc", "fisi_rechtliches.pyc", "LICENSE.txt",
                                      "THIRD_PARTY_NOTICES.txt",
                                      "__pycache__/fisi_game.cpython-312.pyc",
                                      "__pycache__/spiel.cpython-312.pyc"])
        self.assertEqual(len(fehler), 1, fehler)
        self.assertIn("2 Bytecode-Reste in der App", fehler[0])
        self.assertIn("Bytecode-Reste (__pycache__) in app.zip: 2", zeilen)

    def test_apk_ohne_pycache_gruen(self):
        fehler, zeilen = self._check(["main.pyc", "fisi_rechtliches.pyc", "LICENSE.txt",
                                      "THIRD_PARTY_NOTICES.txt", "inhalte/lerninhalte.json"])
        self.assertEqual(fehler, [])
        self.assertIn("Bytecode-Reste (__pycache__) in app.zip: 0", zeilen)

    def test_bytecode_reste(self):
        modul = self._apk_pruefen()
        self.assertEqual(modul.bytecode_reste([
            "main.pyc", "a/__pycache__/b.cpython-314.pyc", "__pycache__/c.cpython-312.pyc",
            "d.cpython-312.pyc", "e.py", "fisi_rechtliches.pyc"]),
            ["a/__pycache__/b.cpython-314.pyc", "__pycache__/c.cpython-312.pyc",
             "d.cpython-312.pyc"])


# ============================================================================
#  N10: B-M-02  Wiederholung nur innerhalb von Netz-Schritten
# ============================================================================

class NetzWiederholungTest(unittest.TestCase):

    def test_pip_mit_wiederholung(self):
        for pfad in (BUILD, RELEASE):
            for nr, zeile in enumerate(_lesen(pfad).splitlines(), 1):
                if re.search(r"\bpip install\b", zeile) and not zeile.lstrip().startswith("#"):
                    self.assertRegex(zeile, r"pip install --retries \d+ --timeout \d+ ",
                                     "%s:%d" % (os.path.basename(pfad), nr))
        self.assertEqual(len(re.findall(r"pip install --retries 10 ", _lesen(BUILD))), 8)

    def test_apt_mit_wiederholung(self):
        zeilen = [z for z in _lesen(BUILD).splitlines() if "apt-get" in z
                  and not z.lstrip().startswith("#")]
        self.assertEqual(len(zeilen), 4)
        for z in zeilen:
            self.assertIn("sudo apt-get -o Acquire::Retries=5 ", z)

    def test_choco_mit_wiederholung(self):
        schritt = "\n".join(_schritt(_lesen(BUILD), "Inno Setup bereitstellen"))
        self.assertIn("foreach ($versuch in 1..3) {", schritt)
        self.assertIn("if ($LASTEXITCODE -eq 0) { break }", schritt)
        self.assertIn("if ($versuch -eq 3) { exit 1 }", schritt)

    def test_wiederholung_nur_in_netz_schritten(self):
        # keine Schleife um Bau, Tests oder Starttests (Mac nie neu starten)
        erlaubt = {"Inno Setup bereitstellen", LAUFZEIT_SCHRITT, "Neue Version?"}
        for pfad in (BUILD, RELEASE):
            text = _lesen(pfad)
            for m in re.finditer(r"(for VERSUCH in|foreach \(\$versuch)", text):
                davor = text[:m.start()]
                name = re.findall(r"\n\s*- name: (.*)\n", davor)[-1].strip()
                self.assertIn(name, erlaubt, os.path.basename(pfad))
            self.assertNotRegex(text, r"\brerun\b|run rerun|re-run")
            self.assertNotIn("continue-on-error", text)
        # Mac-Jobs: im Bau-Job kein Schritt mit Schleife ausser Inno Setup (nur Windows)
        build = "\n".join(_jobs(_lesen(BUILD))["build"])
        self.assertEqual(build.count("for VERSUCH in"), 0)
        self.assertIn("        if: runner.os == 'Windows'",
                      _schritt(_lesen(BUILD), "Inno Setup bereitstellen"))


class ReleaseWiederholungTest(ReleaseNachholenTest):
    """Wie ReleaseNachholenTest, git und gh scheitern aber zuerst am Netz."""

    ATTRAPPEN = dict(ReleaseNachholenTest.ATTRAPPEN)
    ATTRAPPEN["sleep"] = "#!/bin/bash\necho \"sleep $*\" >> \"$PROTOKOLL\"\nexit 0\n"
    ATTRAPPEN["git"] = (
        '#!/bin/bash\necho "git $*" >> "$PROTOKOLL"\n'
        'n=$(grep -c "^git " "$PROTOKOLL")\n'
        'if [ "$n" -le "${ATTRAPPE_GIT_FEHLER:-1}" ]; then '
        'echo "fatal: unable to access: Could not resolve host" >&2; exit 128; fi\n'
        '[ "$ATTRAPPE_TAG" = da ] && exit 0\nexit 2\n')
    ATTRAPPEN["gh"] = (
        '#!/bin/bash\necho "gh $*" >> "$PROTOKOLL"\n'
        'n=$(grep -c "^gh " "$PROTOKOLL")\n'
        'if [ "$n" -le "${ATTRAPPE_GH_FEHLER:-1}" ]; then '
        'echo "gh: Bad Gateway (HTTP 502)" >&2; exit 1; fi\n'
        'case "$ATTRAPPE_GH" in\n'
        '  da) echo v0.63.2; exit 0 ;;\n'
        '  *) echo "gh: Not Found (HTTP 404)" >&2; exit 1 ;;\nesac\n')

    # Die uebrigen geerbten Tests laufen hier mit einem Netzfehler am Anfang
    # (git und gh) und muessen dasselbe Ergebnis liefern. Diese zwei brauchen
    # die gh-Attrappe der Elternklasse (Antwort "fehler") und laufen nur dort.
    def test_unklare_antwort_bricht_ab(self):
        self.skipTest("nur in ReleaseNachholenTest")

    def test_unklare_antwort_mit_404_im_text_bricht_ab(self):
        self.skipTest("nur in ReleaseNachholenTest")

    def _lauf_mit(self, tag, gh, git_fehler="1", gh_fehler="1"):
        alt = dict(os.environ)
        os.environ["ATTRAPPE_GIT_FEHLER"] = git_fehler
        os.environ["ATTRAPPE_GH_FEHLER"] = gh_fehler
        try:
            return self._lauf(tag, gh)
        finally:
            os.environ.clear()
            os.environ.update(alt)

    def test_netzfehler_ls_remote_einmal(self):
        rc, werte, text, prot = self._lauf_mit("fehlt", "404", git_fehler="1")
        self.assertEqual(rc, 0, text)
        self.assertEqual(werte, {"tag": "v0.63.2", "neu": "ja"})
        self.assertIn("Wiederholung wegen Netzfehler (git ls-remote, Fehler 128)", text)
        self.assertEqual(prot.count("git ls-remote"), 2)
        self.assertIn("sleep 5", prot)

    def test_netzfehler_ls_remote_immer_bricht_ab(self):
        # vorher: Netzfehler galt als "Tag fehlt" und es wurde ein Tag angelegt
        rc, werte, text, prot = self._lauf_mit("fehlt", "404", git_fehler="9")
        self.assertNotEqual(rc, 0)
        self.assertEqual(werte, {})
        self.assertEqual(prot.count("git ls-remote"), 3)
        self.assertIn("Tag v0.63.2 laesst sich nicht pruefen (git ls-remote, Fehler 128)", text)

    def test_netzfehler_gh_einmal_dann_nachholen(self):
        rc, werte, text, prot = self._lauf_mit("da", "404", git_fehler="0", gh_fehler="1")
        self.assertEqual(rc, 0, text)
        self.assertEqual(werte, {"tag": "v0.63.2", "neu": "nein"})
        self.assertIn("Wiederholung wegen Netzfehler (gh api): gh: Bad Gateway (HTTP 502)", text)
        self.assertEqual(prot.count("gh api"), 2)

    def test_netzfehler_gh_einmal_dann_da(self):
        rc, werte, text, prot = self._lauf_mit("da", "da", git_fehler="0", gh_fehler="1")
        self.assertEqual(rc, 0, text)
        self.assertEqual(werte, {})
        self.assertIn("nichts zu tun", text)

    def test_netzfehler_gh_immer_bricht_nach_3_ab(self):
        rc, werte, text, prot = self._lauf_mit("da", "404", git_fehler="0", gh_fehler="9")
        self.assertNotEqual(rc, 0)
        self.assertEqual(werte, {})
        self.assertEqual(prot.count("gh api"), 3)
        self.assertIn("Release v0.63.2 laesst sich nicht pruefen: gh: Bad Gateway (HTTP 502)", text)

    def test_404_ohne_wiederholung(self):
        rc, werte, text, prot = self._lauf_mit("da", "404", git_fehler="0", gh_fehler="0")
        self.assertEqual(rc, 0, text)
        self.assertEqual(prot.count("gh api"), 1)
        self.assertNotIn("sleep", prot)


# ============================================================================
#  N10: B-M-08  Cache nur in normalen Laeufen
# ============================================================================

class CacheTest(unittest.TestCase):

    AUSDRUCK = "          cache: ${{ env.IS_RELEASE != 'true' && 'pip' || '' }}"

    def test_jedes_setup_python_mit_cache_ausser_release(self):
        zeilen = _lesen(BUILD).splitlines()
        stellen = [i for i, z in enumerate(zeilen) if "uses: actions/setup-python@" in z]
        self.assertEqual(len(stellen), 5)
        for i in stellen:
            block = zeilen[i:i + 8]
            self.assertIn(self.AUSDRUCK, block, i + 1)
            self.assertTrue(any(z.startswith("          cache-dependency-path: ") for z in block))
        self.assertEqual(len(re.findall(r"^\s+cache: ", _lesen(BUILD), re.M)), 5)
        self.assertNotIn("cache", _lesen(RELEASE))

    def test_ausdruck_release_ohne_cache(self):
        # GitHub-Ausdruck nachgerechnet: a && b || c
        def werte(is_release):
            a = is_release != "true"
            return ("pip" if a else False) or ""
        self.assertEqual(werte("true"), "")
        self.assertEqual(werte("false"), "pip")
        self.assertIn("  IS_RELEASE: ${{ inputs.tag != '' || startsWith(github.ref, 'refs/tags/v') }}",
                      _lesen(BUILD))

    def test_android_werkzeug_cache_nur_normal(self):
        jobs = _jobs(_lesen(BUILD))
        text = "\n".join(jobs["android"])
        m = re.search(r"      - uses: actions/cache@v6\n((?:        .*\n|          .*\n)+)", text + "\n")
        self.assertIsNotNone(m)
        block = m.group(1)
        self.assertIn("        if: env.IS_RELEASE != 'true'\n", block)
        for pfad in ("~/flutter", "~/.flet/cache", "~/.gradle/caches", "~/.gradle/wrapper"):
            self.assertIn("            %s\n" % pfad, block)
        self.assertIn("key: android-werkzeug-${{ runner.os }}-flet-1.0.1-"
                      "${{ hashFiles('mobile/pyproject.toml') }}", block)
        for job, zeilen in jobs.items():
            if job != "android":
                self.assertNotIn("actions/cache", "\n".join(zeilen), job)
        namen = _schritt_namen(jobs["android"])
        # vor dem Vorab-Laden: wiederhergestellte Dateien werden dort geprueft
        self.assertLess(text.index("actions/cache@v6"),
                        text.index("- name: " + LAUFZEIT_SCHRITT))
        self.assertIn(LAUFZEIT_SCHRITT, namen)


if __name__ == "__main__":
    unittest.main()
