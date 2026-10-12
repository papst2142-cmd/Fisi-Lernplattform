#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests ab 0.63 (Plan 0.63, T3 und T6; Freigabe P63-3, D-1/D-4):
  * PC-Karte "Subnetting": Schalter IPv4/IPv6, Ansichten Netzdaten / Netz
    aufteilen / Nach Hostbedarf, Blaettern, Rechenweg je Modus und Ansicht
    (T-UI-1, T-UI-3 PC-Teil, T-UI-5 Moduswechsel nach Plan 4.6)
  * Beschriftungen nur aus fisi_core (eine Quelle fuer PC und Handy)
  * B-D-04 (Teil 0.63): Ergebnis bei Fehler LEEREN in den neuen Ansichten und
    bei RAID, Bildschirm und USV; USV "+0 %" bei Alterung "-0" (Schutz)
  * T6 (T-RB-1): Satz "Keine Rechtsberatung" genau einmal im Release-Text,
    unter "### Herunterladen" (nicht im Update-Fenster), Trockenlauf des
    Schritts aus build.yml

Teile, die erst mit dem Kern-Zweig version-063-kern kommen (ipv6_details,
SUBNET_PAGE_JUMP), werden uebersprungen, solange der Kern sie nicht hat.

Start:  xvfb-run -a python test_subnetz_pc.py
"""

import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

_TMP = tempfile.mkdtemp(prefix="fisi_subnetz_pc_")
os.environ["FISI_DB_PATH"] = os.path.join(_TMP, "subnetz_pc.db")
os.environ.setdefault("FISI_SELFTEST", os.path.join(_TMP, "selbsttest.log"))

import fisi_core as fc  # noqa: E402

SATZ = ("Die Lizenz- und Rechtstexte dieses Programms sind keine Rechtsberatung "
        "und nicht anwaltlich geprüft.")
KERN_DETAILS = hasattr(fc, "ipv6_details")
KERN_SPRUNG = hasattr(fc, "SUBNET_PAGE_JUMP") and hasattr(fc, "SUBNET_PAGE_JUMP_FIELD")


def _tk_ok():
    try:
        import tkinter
        root = tkinter.Tk()
        root.destroy()
        return True
    except Exception:  # noqa: BLE001
        return False


HAS_DISPLAY = _tk_ok()


def _source(name):
    with open(os.path.join(HERE, name), encoding="utf-8") as handle:
        return handle.read()


class QuelleTest(unittest.TestCase):
    """T-UI-3 (PC-Teil): keine eigenen Beschriftungen mehr im PC-Code."""

    def test_alte_texte_weg(self):
        pc = _source("app_gui.py")
        self.assertNotIn("Subnetting / VLSM", pc)
        self.assertNotIn("IP-Adresse mit Präfix", pc)
        self.assertNotIn('subtitle="IPv4 und IPv6"', pc)

    def test_beschriftungen_aus_dem_kern(self):
        pc = _source("app_gui.py")
        for name in ("SUBNET_TITLE", "SUBNET_MODES", "SUBNET_VIEWS", "SUBNET_FIELD_NET",
                     "SUBNET_FIELD_COUNT", "SUBNET_FIELD_NEEDS", "SUBNET_PAGE_FIRST",
                     "SUBNET_PAGE_BACK", "SUBNET_PAGE_NEXT", "SUBNET_PAGE_LAST",
                     "SUBNET_PAGE_OF", "SUBNET_SUBTITLE", "SUBNET_DEFAULTS"):
            self.assertRegex(pc, r"\b%s\b" % name, name)
        # die Texte selbst stehen nicht im PC-Code
        for text in ("Netz aufteilen", "Nach Hostbedarf", "Anzahl Subnetze",
                     "Erste Seite", "Letzte Seite", "Zur Seite"):
            self.assertNotIn('"%s"' % text, pc, text)

    def test_handy_fassung_nicht_am_pc(self):
        # wie test_rechenweg.py: der PC nutzt keine _HANDY-Texte
        self.assertNotIn("_HANDY", _source("app_gui.py"))


class UsvNullTest(unittest.TestCase):
    """B-D-04/D-5: Alterung "-0" zeigt "+0 %", nie "+-" (Schutz, schon so)."""

    def test_minus_null(self):
        fields = dict(fc.UPS_FIELD_DEFAULTS)
        for value in ("-0", "-0,0", "0"):
            fields["alterung"] = value
            text = fc.ups_calculate("akku", fields)["text"]
            self.assertIn("Mit Alterungszuschlag : 187,50 Wh (+0 %)", text, value)
            self.assertNotIn("+-", text, value)
            self.assertNotIn("-0 %", text, value)


def _step_script():
    """Der Schritt "Pruefsummen (SHA-256) in den Release-Text" aus build.yml
    (Zeilen des run-Blocks, ohne Einrueckung)."""
    lines = _source(os.path.join(".github", "workflows", "build.yml")).split("\n")
    start = next(i for i, line in enumerate(lines)
                 if line.strip() == "- name: Pruefsummen (SHA-256) in den Release-Text")
    assert lines[start + 1].strip() == "run: |", lines[start + 1]
    block = []
    for line in lines[start + 2:]:
        if line.strip() and not line.startswith(" " * 10):
            break
        block.append(line[10:])
    return "\n".join(block)


class RechtsberatungTest(unittest.TestCase):
    """T-RB-1 (Plan 0.63 Abschnitt 11, P63-7)."""

    def test_genau_einmal_unter_herunterladen(self):
        lines = _source(os.path.join(".github", "workflows", "build.yml")).split("\n")
        hits = [i for i, line in enumerate(lines) if SATZ in line]
        self.assertEqual(len(hits), 1)
        self.assertEqual(lines[hits[0]].strip(),
                         'echo "**Hinweis:** %s"' % SATZ)
        down = lines.index('            echo "### Herunterladen"')
        sums = lines.index('            echo "### Prüfsummen (SHA-256)"')
        self.assertLess(down, hits[0])
        self.assertLess(hits[0], sums)
        # nicht im Text der Testversion (Vorab-Release)
        self.assertEqual(sum("Rechtsberatung" in line for line in lines), 1)

    @unittest.skipUnless(shutil.which("bash") and shutil.which("sha256sum"),
                         "bash/sha256sum fehlen")
    def test_trockenlauf_release_text(self):
        """Den Schritt wie in der CI ausfuehren (ohne Release): eigener
        Ordner mit build.py-Kopie, zwei Schein-Installern und den
        Versionshinweisen aus AENDERUNGEN.md."""
        work = tempfile.mkdtemp(prefix="fisi_release_text_")
        try:
            for name in ("build.py", "AENDERUNGEN.md", "app_gui.py"):
                if os.path.exists(os.path.join(HERE, name)):
                    shutil.copy(os.path.join(HERE, name), work)
            os.makedirs(os.path.join(work, "installer"))
            for name in ("a.exe", "b.deb"):
                with open(os.path.join(work, "installer", name), "w") as handle:
                    handle.write(name)
            notes = subprocess.run([sys.executable, "build.py", "--versionshinweise"],
                                   cwd=work, capture_output=True, text=True, check=True,
                                   env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
            with open(os.path.join(work, "versionshinweise.md"), "w",
                      encoding="utf-8") as handle:
                handle.write(notes.stdout)
            env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
            bindir = os.path.join(work, "bin")
            os.makedirs(bindir)
            # python3 im Schritt = dieses Python
            os.symlink(sys.executable, os.path.join(bindir, "python3"))
            env["PATH"] = bindir + os.pathsep + env.get("PATH", "")
            subprocess.run(["bash", "-e", "-c", _step_script()], cwd=work, env=env,
                           capture_output=True, text=True, check=True)
            with open(os.path.join(work, "versionshinweise.md"), encoding="utf-8") as handle:
                text = handle.read()
        finally:
            shutil.rmtree(work, ignore_errors=True)
        self.assertEqual(text.count(SATZ), 1)
        self.assertIn("**Hinweis:** " + SATZ, text)
        head, _sep, tail = text.partition("### Herunterladen")
        self.assertNotIn(SATZ, head)          # Update-Fenster zeigt nur den Kopf
        self.assertIn(SATZ, tail.split("### Prüfsummen (SHA-256)")[0])
        import fisi_update
        self.assertNotIn("Rechtsberatung", "\n".join(
            str(item) for item in fisi_update.plain_notes(text)))


_SHARED = {}


def _shared_app():
    """Eine App fuer alle Oberflaechen-Tests dieser Datei (mehrere FISIApp in
    einem Prozess vertragen sich nicht mit den Bildern von Tk)."""
    if _SHARED:
        return _SHARED
    import customtkinter as ctk
    import app_gui
    app_gui.UpdateController.auto_check = lambda self: None
    app_gui.SyncController.auto_start = lambda self: None
    errors = []
    _SHARED["showerror"] = app_gui.messagebox.showerror
    app_gui.messagebox.showerror = lambda *args, **kwargs: errors.append(args)
    # Zaehler am Rechenkern (T-UI-5: beim Wechsel wird nicht neu gerechnet)
    calls = {"split": 0, "hosts": 0, "report": 0}
    orig = {name: getattr(app_gui, name) for name in
            ("split_network", "subnet_by_hosts", "subnet_report")}

    def counted(key, func):
        def wrapper(*args, **kwargs):
            calls[key] += 1
            return func(*args, **kwargs)
        return wrapper
    app_gui.split_network = counted("split", orig["split_network"])
    app_gui.subnet_by_hosts = counted("hosts", orig["subnet_by_hosts"])
    app_gui.subnet_report = counted("report", orig["subnet_report"])
    root = ctk.CTk()
    root.geometry("1360x880+0+0")
    app = app_gui.FISIApp(root)
    app.show_view("calc")
    _SHARED.update(app_gui=app_gui, errors=errors, calls=calls, orig=orig, root=root,
                   app=app)
    return _SHARED


def tearDownModule():
    if not _SHARED:
        return
    app_gui = _SHARED["app_gui"]
    for name, func in _SHARED["orig"].items():
        setattr(app_gui, name, func)
    app_gui.messagebox.showerror = _SHARED["showerror"]
    root = _SHARED["root"]
    try:
        for job in root.tk.splitlist(root.tk.call("after", "info")):
            root.tk.call("after", "cancel", job)
        root.destroy()
    except Exception:  # noqa: BLE001
        pass


@unittest.skipUnless(HAS_DISPLAY, "keine Anzeige (z.B. mit xvfb-run starten)")
class PcCase(unittest.TestCase):
    """Gemeinsame Hilfen der Oberflaechen-Tests."""

    @classmethod
    def setUpClass(cls):
        shared = _shared_app()
        cls.app_gui = shared["app_gui"]
        cls.errors = shared["errors"]
        cls.calls = shared["calls"]
        cls.root = shared["root"]
        cls.app = shared["app"]
        cls.view = cls.app.views["calc"]
        cls.sub = cls.view.subnet
        cls.settle()

    @classmethod
    def settle(cls, times=4):
        for _ in range(times):
            cls.root.update_idletasks()
            cls.root.update()

    def setUp(self):
        self.errors.clear()

    def box(self, mode, key):
        return self.sub.views[(mode, key)]["box"].get("1.0", "end-1c")

    def info(self, mode, key):
        return self.sub.views[(mode, key)]["info"].get("1.0", "end-1c")

    def go(self, mode, key=None):
        self.sub.mode_pills.select_value(mode)
        if key is not None:
            self.sub.view_pills[mode].select_value(key)
        self.settle(2)


class PcAufbauTest(PcCase):
    """T-UI-1: Start, Beschriftungen, Rechnen, Blaettern."""

    def test_0_start(self):
        # Start immer IPv4, "Netzdaten" (F-63-13 Nein); vor dem ersten
        # Rechnen alle Kaesten leer (Plan 4.6, Abstimmung T3/T4)
        sub = self.sub
        self.assertEqual(sub.mode, "ipv4")
        self.assertEqual(sub.view_of, {"ipv4": "netzdaten", "ipv6": "netzdaten"})
        self.assertEqual(sub.mode_pills.get(), "ipv4")
        self.assertEqual(sub.card.title_label.cget("text"), fc.SUBNET_TITLE.upper())
        self.assertEqual(sub.card.subtitle_label.cget("text"), fc.SUBNET_SUBTITLE["ipv4"])
        for key, _name in fc.SUBNET_VIEWS["ipv4"]:
            self.assertEqual(self.box("ipv4", key), "", key)
        self.assertFalse(sub.built("ipv6") and self.app.preloader.mode == "aus")
        self.assertTrue(sub.views[("ipv4", "netzdaten")]["frame"].winfo_ismapped())

    def test_1_beschriftungen(self):
        def texts(widget):
            found = []
            for child in widget.winfo_children():
                try:
                    found.append(child.cget("text"))
                except Exception:  # noqa: BLE001
                    pass
                found += texts(child)
            return found
        self.sub.build_mode("ipv6")
        for mode, name in fc.SUBNET_MODES:
            self.assertEqual(self.sub.mode_pills.buttons[
                self.sub.mode_pills.values.index(mode)].cget("text"), name)
            pills = self.sub.view_pills[mode]
            self.assertEqual([(v, b.cget("text")) for v, b in zip(pills.values, pills.buttons)],
                             fc.SUBNET_VIEWS[mode])
            for key, _name in fc.SUBNET_VIEWS[mode]:
                found = texts(self.sub.views[(mode, key)]["frame"])
                self.assertIn(fc.SUBNET_FIELD_NET[mode], found, (mode, key))
                if key == "aufteilen":
                    self.assertIn(fc.SUBNET_FIELD_COUNT, found)
                    for caption in (fc.SUBNET_PAGE_FIRST, fc.SUBNET_PAGE_BACK,
                                    fc.SUBNET_PAGE_NEXT, fc.SUBNET_PAGE_LAST):
                        self.assertIn(caption, found)
                    if KERN_SPRUNG:
                        self.assertIn(fc.SUBNET_PAGE_JUMP, found)
                if key == "bedarf":
                    self.assertIn(fc.SUBNET_FIELD_NEEDS, found)
        # Vorgaben (Beispiele B, C, D; Netzdaten wie abgestimmt)
        views = self.sub.views
        self.assertEqual(views[("ipv4", "netzdaten")]["net"].get(), "192.168.1.50/24")
        self.assertEqual(views[("ipv6", "netzdaten")]["net"].get(), "2001:db8:abcd:12::1/64")
        for (mode, key), (net, other) in fc.SUBNET_DEFAULTS.items():
            self.assertEqual(views[(mode, key)]["net"].get(), net)
            if key == "aufteilen":
                self.assertEqual(views[(mode, key)]["count"].get(), other)
            else:
                self.assertEqual(views[(mode, key)]["needs"].get("1.0", "end-1c"), other)
        self.assertNotIn(("ipv6", "bedarf"), views)

    def test_2_netzdaten(self):
        self.go("ipv4", "netzdaten")
        self.sub.calc("ipv4", "netzdaten")
        self.assertEqual(self.box("ipv4", "netzdaten"), fc.subnet_report("192.168.1.50/24"))
        self.go("ipv6", "netzdaten")
        self.sub.calc("ipv6", "netzdaten")
        text = self.box("ipv6", "netzdaten")
        # zwei Zeilen mehr und lange Adressen: Kasten waechst mit (keine
        # versteckten Zeilen), IPv4-Netzdaten bleiben wie bisher (height=9)
        self.assertTrue(hasattr(self.sub.views[("ipv6", "netzdaten")]["box"],
                                "autogrow_resize"))
        self.assertFalse(hasattr(self.sub.views[("ipv4", "netzdaten")]["box"],
                                 "autogrow_resize"))
        self.assertTrue(text.startswith(fc.subnet_report("2001:db8:abcd:12::1/64")))
        if KERN_DETAILS:
            extra = text[len(fc.subnet_report("2001:db8:abcd:12::1/64")):].split("\n")[1:]
            self.assertEqual(extra, ["%-22s: %s" % pair for pair in
                                     fc.ipv6_details("2001:db8:abcd:12::1/64")])
            self.assertEqual(len(extra), 2)
            for line in extra:
                self.assertTrue(line.startswith((fc.IPV6_LABEL_AUSGESCHRIEBEN,
                                                 fc.IPV6_LABEL_ADRESSTYP)), line)
        self.assertEqual(self.errors, [])
        self.go("ipv4")

    def test_3_aufteilen_und_blaettern(self):
        self.go("ipv4", "aufteilen")
        view = self.sub.views[("ipv4", "aufteilen")]
        self.sub.calc("ipv4", "aufteilen")       # Vorgabe: 6 Subnetze, eine Seite
        expect = fc.split_report(fc.split_network("192.168.10.0/24", "6", version=4), 1)
        self.assertEqual(self.box("ipv4", "aufteilen"), expect)
        self.settle(2)
        self.assertFalse(view["pager"].winfo_ismapped())   # Knopfzeile nur ab 2 Seiten
        view["count"].set("64")
        self.sub.calc("ipv4", "aufteilen")
        self.settle(2)
        result = fc.split_network("192.168.10.0/24", "64", version=4)
        self.assertTrue(view["pager"].winfo_ismapped())
        self.assertEqual(view["page_label"].cget("text"), fc.SUBNET_PAGE_OF % ("1", "8"))
        self.assertEqual(self.box("ipv4", "aufteilen"), fc.split_report(result, 1))
        buttons = view["pager_buttons"]
        self.assertFalse(buttons["first"]._enabled)
        self.assertFalse(buttons["back"]._enabled)
        self.assertTrue(buttons["next"]._enabled)
        for where, page in (("next", 2), ("next", 3), ("back", 2), ("last", 8),
                            ("next", 8), ("first", 1), ("back", 1)):
            self.sub.turn(view, where)
            self.assertEqual(view["page"], page, where)
            self.assertEqual(self.box("ipv4", "aufteilen"), fc.split_report(result, page))
        self.assertEqual(self.errors, [])

    @unittest.skipUnless(KERN_SPRUNG, "SUBNET_PAGE_JUMP kommt mit version-063-kern")
    def test_4_sprung(self):
        self.go("ipv4", "aufteilen")
        view = self.sub.views[("ipv4", "aufteilen")]
        view["count"].set("1.000")
        view["net"].set("10.0.0.0/8")
        self.sub.calc("ipv4", "aufteilen")
        result = fc.split_network("10.0.0.0/8", "1000", version=4)
        self.assertEqual(result["seiten"], 128)
        for typed, page in (("5", 5), ("128", 128), ("1.000", 128), ("0", 1),
                            ("-3", 1), ("64", 64)):
            view["jump"].set(typed)
            self.sub.jump(view)
            self.assertEqual(view["page"], page, typed)
            self.assertEqual(self.box("ipv4", "aufteilen"), fc.split_report(result, page))
        self.assertEqual(self.errors, [])
        for typed in ("", "zwei", "2,5"):
            view["jump"].set(typed)
            self.sub.jump(view)
            self.assertEqual(view["page"], 64, typed)    # Seite bleibt stehen
            self.assertEqual(self.box("ipv4", "aufteilen"), fc.split_report(result, 64))
        self.assertEqual([e[1] for e in self.errors], [
            "Bitte einen Wert eingeben: %s." % fc.SUBNET_PAGE_JUMP_FIELD,
            "Bitte eine Zahl eingeben: %s. Zum Beispiel 1.000." % fc.SUBNET_PAGE_JUMP_FIELD,
            "Bitte eine ganze Zahl eingeben: %s." % fc.SUBNET_PAGE_JUMP_FIELD])
        view["jump"].set("2")
        view["jump"]._entry.focus_force()        # Tasten gehen an das Feld mit Fokus
        self.settle(2)
        view["jump"]._entry.event_generate("<Return>")
        self.settle(2)
        self.assertEqual(view["page"], 2)

    def test_5_bedarf(self):
        self.go("ipv4", "bedarf")
        self.sub.calc("ipv4", "bedarf")
        result = fc.subnet_by_hosts("192.168.10.0/24", "A 50\nB 20\nC 10\nD 2", version=4)
        self.assertEqual(self.box("ipv4", "bedarf"), fc.hosts_report(result))
        # passt nicht (Beispiel E): Ergebnistext, keine Meldung (M-9)
        view = self.sub.views[("ipv4", "bedarf")]
        fc_text = "A 200\nB 60\nC 10"
        self.app_gui.set_text(view["needs"], fc_text)
        self.sub.calc("ipv4", "bedarf")
        self.assertEqual(self.errors, [])
        self.assertIn("Es fehlen", self.box("ipv4", "bedarf"))

    def test_6_rechenweg(self):
        sub = self.sub
        self.assertEqual(sub.explanation(sub.views[("ipv4", "netzdaten")]),
                         fc.CALC_EXPLAIN_SUBNET)
        sub.build_mode("ipv6")
        self.assertEqual(sub.explanation(sub.views[("ipv6", "netzdaten")]),
                         fc.CALC_EXPLAIN_SUBNET_V6)
        # Vor dem ersten Rechnen: Rechenweg zur Vorgabe (Beispiel B, C, D)
        for (mode, key), (net, other) in fc.SUBNET_DEFAULTS.items():
            view = sub.views[(mode, key)]
            saved = view["result"]
            view["result"] = None
            if key == "aufteilen":
                expect = fc.split_explain(fc.split_network(net, other,
                                                           version=int(mode[-1])))
            else:
                expect = fc.hosts_explain(fc.subnet_by_hosts(net, other, version=4))
            self.assertEqual(sub.explanation(view), expect, (mode, key))
            view["result"] = saved
        # Nach dem Rechnen: Rechenweg zur Eingabe; Knopf und Text
        self.go("ipv4", "aufteilen")
        view = sub.views[("ipv4", "aufteilen")]
        view["net"].set("10.0.0.0/16")
        view["count"].set("8")
        sub.calc("ipv4", "aufteilen")
        sub.toggle_info("ipv4", "aufteilen")
        self.settle(2)
        self.assertTrue(view["info"].winfo_ismapped())
        self.assertEqual(view["info_button"].cget("text"), "Rechenweg ausblenden")
        self.assertEqual(self.info("ipv4", "aufteilen"),
                         fc.split_explain(fc.split_network("10.0.0.0/16", "8", version=4)))
        # offen und neu gerechnet: Text folgt der neuen Eingabe
        view["count"].set("4")
        sub.calc("ipv4", "aufteilen")
        self.assertEqual(self.info("ipv4", "aufteilen"),
                         fc.split_explain(fc.split_network("10.0.0.0/16", "4", version=4)))
        sub.toggle_info("ipv4", "aufteilen")
        self.settle(2)
        self.assertFalse(view["info"].winfo_ismapped())
        self.assertEqual(view["info_button"].cget("text"), "Rechenweg anzeigen")

    def test_7_vorladen_baut_ipv6(self):
        # Plan 4.2: IPv6-Teil beim Vorladen verdeckt (CalcView.prepare)
        card = self.app_gui.Card(self.view.content, title=fc.SUBNET_TITLE)
        try:
            fresh = self.app_gui.SubnetCalc(card)
            self.assertEqual(fresh.mode, "ipv4")          # Start immer IPv4
            self.assertFalse(fresh.built("ipv6"))
            self.assertTrue(fresh.build_mode("ipv6"))
            self.assertFalse(fresh.build_mode("ipv6"))
            self.assertFalse(fresh.mode_frames["ipv6"].winfo_ismapped())
        finally:
            card.destroy()
        self.sub.build_mode("ipv6")
        self.assertFalse(self.view.prepare())             # schon gebaut: nichts zu tun


@unittest.skipUnless(HAS_DISPLAY, "keine Anzeige (z.B. mit xvfb-run starten)")
class PcFehlerTest(PcCase):
    """B-D-04 (D-4): nach einer Fehlermeldung ist der Kasten LEER."""

    FAELLE = [
        ("ipv4", "netzdaten", {"net": "300.1.1.1/24"}),
        ("ipv4", "aufteilen", {"count": "0"}),
        ("ipv4", "aufteilen", {"net": "2001:db8::/48"}),
        ("ipv4", "bedarf", {"needs": "A 50, B 20"}),
        ("ipv6", "netzdaten", {"net": "xyz"}),
        ("ipv6", "aufteilen", {"net": "192.168.10.0/24"}),
        ("ipv6", "aufteilen", {"count": "2,5"}),
    ]

    def _set(self, view, field, value):
        if field == "needs":
            self.app_gui.set_text(view["needs"], value)
        else:
            view[field].set(value)

    def test_neue_ansichten_leeren(self):
        for mode, key, bad in self.FAELLE:
            with self.subTest(mode=mode, key=key, bad=bad):
                self.errors.clear()
                self.go(mode, key)
                view = self.sub.views[(mode, key)]
                saved = {field: (view[field].get("1.0", "end-1c") if field == "needs"
                                 else view[field].get()) for field in bad}
                if key == "aufteilen":
                    view["count"].set("64")
                    saved.setdefault("count", "6")
                self.sub.calc(mode, key)
                self.settle(2)
                good = self.box(mode, key)
                self.assertTrue(good)
                self.sub.toggle_info(mode, key)
                info = self.info(mode, key)
                for field, value in bad.items():
                    self._set(view, field, value)
                self.sub.calc(mode, key)
                self.settle(2)
                self.assertEqual(len(self.errors), 1)
                self.assertEqual(self.errors[0][0], "Ungültige Eingabe")
                self.assertEqual(self.box(mode, key), "")          # LEER
                self.assertFalse(view["info_open"])                 # Rechenweg zu
                self.assertFalse(view["info"].winfo_ismapped())
                self.assertEqual(view["info_button"].cget("text"), "Rechenweg anzeigen")
                self.assertEqual(self.info(mode, key), info)        # letzte gueltige
                if key == "aufteilen":
                    self.assertFalse(view["pager"].winfo_ismapped())
                for field, value in saved.items():
                    self._set(view, field, value)
        self.go("ipv4", "netzdaten")

    def test_fehlertexte_wortlaut(self):
        self.go("ipv4", "aufteilen")
        view = self.sub.views[("ipv4", "aufteilen")]
        view["net"].set("192.168.10.0/24")
        view["count"].set("512")
        self.sub.calc("ipv4", "aufteilen")
        self.assertEqual(self.errors[-1][1], str(self._error(
            fc.split_network, "192.168.10.0/24", "512", version=4)))
        view["count"].set("6")
        view["net"].set("2001:db8::/48")
        self.sub.calc("ipv4", "aufteilen")
        self.assertEqual(self.errors[-1][1],
                         "Im Modus IPv4 bitte ein IPv4-Netz angeben (z. B. 192.168.10.0/24).")
        view["net"].set("192.168.10.0/24")

    @staticmethod
    def _error(func, *args, **kwargs):
        try:
            func(*args, **kwargs)
        except fc.InputError as error:
            return error
        raise AssertionError("keine Meldung")

    def test_raid_bildschirm_usv_leeren(self):
        view = self.view
        view.calc_raid()
        self.assertTrue(view.txt_raid.get("1.0", "end-1c"))
        view.entry_disks.set("abc")
        view.calc_raid()
        self.assertEqual(view.txt_raid.get("1.0", "end-1c"), "")
        view.entry_disks.set("4")
        view.calc_screen()
        self.assertTrue(view.txt_screen.get("1.0", "end-1c"))
        view.entry_width.set("-5")
        view.calc_screen()
        self.assertEqual(view.txt_screen.get("1.0", "end-1c"), "")
        view.entry_width.set("1920")
        view.calc_ups("empfehlung")
        self.assertTrue(view.txt_ups.get("1.0", "end-1c"))
        self.assertIsNotNone(view.ups_picture._picture)
        entry = view.ups_entries["eta"]
        entry.set("200")
        view.calc_ups("laufzeit")
        self.assertEqual(view.txt_ups.get("1.0", "end-1c"), "")
        self.assertIsNone(view.ups_picture._picture)
        self.settle(2)
        self.assertEqual(view.ups_picture.find_all(), ())
        entry.set(fc.UPS_FIELD_DEFAULTS["eta"])
        view.calc_ups("empfehlung")
        self.assertEqual(len(self.errors), 3)
        self.assertTrue(all(e[0] == "Ungültige Eingabe" for e in self.errors))


@unittest.skipUnless(HAS_DISPLAY, "keine Anzeige (z.B. mit xvfb-run starten)")
class PcWechselTest(PcCase):
    """T-UI-5 (Plan 4.6): Moduswechsel und Ansichtswechsel."""

    def test_wechsel(self):
        sub = self.sub
        self.go("ipv6", "netzdaten")
        self.go("ipv4", "aufteilen")
        view = sub.views[("ipv4", "aufteilen")]
        view["net"].set("172.16.0.0/16")
        view["count"].set("100")
        sub.calc("ipv4", "aufteilen")
        sub.turn(view, "next")
        sub.turn(view, "next")
        sub.toggle_info("ipv4", "aufteilen")
        self.settle(2)
        before = dict(self.calls)
        box = self.box("ipv4", "aufteilen")
        self.assertEqual(view["page"], 3)
        # auf IPv6: eigener Stand, Rechenweg zu, Untertitel, Fokus
        self.go("ipv6")
        self.assertEqual(sub.mode, "ipv6")
        self.assertEqual(sub.card.subtitle_label.cget("text"), fc.SUBNET_SUBTITLE["ipv6"])
        self.assertEqual(sub.view_of["ipv6"], "netzdaten")
        self.assertFalse(view["info_open"])
        self.assertEqual(view["info_button"].cget("text"), "Rechenweg anzeigen")
        self.assertFalse(sub.mode_frames["ipv4"].winfo_ismapped())
        self.assertTrue(sub.views[("ipv6", "netzdaten")]["frame"].winfo_ismapped())
        focus = self.root.focus_get()
        net6 = sub.views[("ipv6", "netzdaten")]["net"]
        self.assertIn(focus, (net6, getattr(net6, "_entry", None)))
        # zurueck: gleiche Eingaben, gleiches Ergebnis, gleiche Seite, nicht gerechnet
        self.go("ipv4")
        self.assertEqual(sub.view_of["ipv4"], "aufteilen")
        self.assertEqual(view["net"].get(), "172.16.0.0/16")
        self.assertEqual(view["count"].get(), "100")
        self.assertEqual(view["page"], 3)
        self.assertEqual(self.box("ipv4", "aufteilen"), box)
        self.assertFalse(view["info_open"])
        self.assertFalse(view["info"].winfo_ismapped())
        self.assertTrue(view["pager"].winfo_ismapped())
        self.assertEqual(self.calls, before)
        focus = self.root.focus_get()
        self.assertIn(focus, (view["net"], getattr(view["net"], "_entry", None)))
        # "Nach Hostbedarf" gewaehlt, auf IPv6: IPv6 zeigt seine eigene Ansicht
        self.go("ipv6", "aufteilen")
        self.go("ipv4", "bedarf")
        self.go("ipv6")
        self.assertEqual(sub.view_of["ipv6"], "aufteilen")
        self.assertEqual(sub.view_pills["ipv6"].get(), "aufteilen")
        self.go("ipv4")
        self.assertEqual(sub.view_of["ipv4"], "bedarf")
        self.assertTrue(sub.views[("ipv4", "bedarf")]["frame"].winfo_ismapped())
        # Ansichtswechsel klappt den Rechenweg ebenfalls zu
        sub.toggle_info("ipv4", "bedarf")
        self.go("ipv4", "netzdaten")
        self.assertFalse(sub.views[("ipv4", "bedarf")]["info_open"])
        self.assertEqual(self.calls, before)
        # Fehler gehoert zur eigenen Rechnung: anderer Modus unberuehrt
        sub.views[("ipv6", "aufteilen")]["net"].set("1.2.3.4/8")
        sub.calc("ipv6", "aufteilen")
        self.assertEqual(self.box("ipv4", "aufteilen"), box)
        sub.views[("ipv6", "aufteilen")]["net"].set("2001:db8:abcd::/48")


if __name__ == "__main__":
    unittest.main(verbosity=2)
