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
        self.assertEqual(eigene, ["actions/checkout@v7", "actions/download-artifact@v8",
                                  "actions/setup-python@v7", "actions/upload-artifact@v7"])
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

    def test_matrix_hat_teil_ibus(self):
        jobs = _jobs(_lesen(BUILD))
        self.assertIn("        teil: [spiel, lang, rest, ibus]", jobs["tests"])

    def test_werkzeuge_fuer_ibus(self):
        schritt = "\n".join(_schritt(_lesen(BUILD), "Werkzeuge fuer die Tests"))
        # Ab FG-91: python3-tk bleibt, weil Tk auf GitHub damit einfror
        # (Lauf 38430837558), vermutet ursaechlich.
        # Ganze Zeile pruefen (vorher nur der Anfang "... ibus dbus-x11")
        self.assertIn("\n            sudo apt-get install -y ibus dbus-x11 python3-tk\n", schritt + "\n")

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
        self.assertEqual(len(zeilen), 3)
        for z in zeilen:
            self.assertRegex(z, r"--connect-timeout \d+ ")
            self.assertRegex(z, r"--max-time \d+ ")


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
        self.assertIn('              *"HTTP 404"*) ;;', schritt)

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


if __name__ == "__main__":
    unittest.main()
