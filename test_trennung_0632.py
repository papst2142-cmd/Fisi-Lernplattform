#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests 0.63.2 N8 (B-D-06): gemeinsame Umbruchregel fisi_trennung (PC und
Handy), ohne Anzeige.

Weisung zu Meldung 38/40 B3 (a): eigenes ungeschuetztes Modul, Eintrag in
mobile/vorbereiten.py SHARED_FILES (die Handy-App bekommt es), Kopie in
.gitignore. Die APK-Pruefung verlangt es in app.zip (pruefung/apk_pruefen.py
APP_FILES, FG-97, Weisung zu Meldung 42 Frage 5).

Regel (Testplan N8 K2, K4, K5, A-N8-05) mit fester Zeichenbreite gemessen:
  * jede Zeile passt in die Breite (Wortliste x Breiten 80..400 px)
  * ein zu langes Wort wird nach einem vorhandenen Bindestrich geteilt
  * die Nummer "4." bleibt beim ersten Wort
  * passt der Titel mit dem gewoehnlichen Umbruch, bleibt der Text gleich
  * jedes Wort ueber 18 Zeichen in Titeln, Listentiteln, Beschriftungen und
    Rechenwegen hat einen Listeneintrag (Weisung zu Meldung 43, 2.1; rot bei
    jedem fehlenden Wort), maschinelle Vorpruefung aller Eintraege (i)-(iv)
  * Silbentrennung nur nach der bestaetigten Liste (Weisung zu Meldung 42,
    Fragen 11-13, Meldung 42 Anhang A): alle 33 Woerter mit genau ihren
    Stellen, "nie trennen", mindestens 2 Buchstaben je Seite, bevorzugte
    Stellen zuerst, kein doppelter Strich an einem vorhandenen Bindestrich

Start:  python test_trennung_0632.py
"""

import ast
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import fisi_trennung as ft  # noqa: E402

WOERTER = ["Mehrfaktor-Authentifizierung", "Wirtschaftlichkeitsbetrachtung",
           "PRÜFUNGSTRAINER", "Netzwerkinfrastruktur", "Datensicherungskonzept",
           "Hochverfügbarkeit", "IPv6-Adressierung", "Kundenzufriedenheitsanalyse",
           "4. Wirtschaftlichkeitsbetrachtung", "Einführung einer Mehrfaktor-Authentifizierung",
           "12. Einfache Wirtschaftlichkeitsbetrachtung ✓", "OPTISCHE ANPASSUNGEN"]


def messen(text):
    """Feste Zeichenbreite 10 px (wie eine Schaetzung je Zeichen am Handy)."""
    return 10 * len(text)


def ohne_trennstriche(zeilen, text):
    """Setzt die Zeilen wieder zusammen: Leerzeichen an Umbruechen und
    eingefuegte Trennstriche fallen weg (ein vorhandener Bindestrich bleibt)."""
    ziel = text.replace(" ", "")
    ganz = ""
    for index, zeile in enumerate(zeilen):
        stueck = zeile.replace(" ", "")
        if index < len(zeilen) - 1 and stueck.endswith("-") and \
                not ziel[len(ganz):].startswith(stueck):
            stueck = stueck[:-1]
        ganz += stueck
    return ganz


# Erwartung: Meldung 42 Anhang A, Spalte "erwartete Stellen", Wort fuer Wort
# (von Chat bestaetigt, Weisung zu Meldung 42 Abschnitt 2.11). Unabhaengige
# Abschrift - nicht aus fisi_trennung gelesen.
ANHANG_A = """
Wirt|schaft|lich|keits‖be|trach|tung
Wirt|schaft|lich|keits‖ver|gleich
Mehr‖fak|tor-‖Au|then|ti|fi|zie|rung
PRÜ|FUNGS‖TRAI|NER
AN‖PAS|SUN|GEN
Da|ten‖si|che|rungs‖kon|zep|te
Hoch‖ver|füg|bar|keit
Kun|den‖zu|frie|den|heit
IPv6-‖Adres|se
Netz‖werk‖in|fra|struk|tur
Ab|schluss‖pro|jekt
Schwie|rig|keits‖grad
Broad|cast-‖Adres|se
Prä|fix‖län|ge
Wild|card-‖Mas|ke
Punkt-‖zu-‖Punkt-‖Ver|bin|dun|gen
Vir|tu|a|li|sie|rung
Da|ten‖schutz-‖Grund‖ver|ord|nung
Ver|schlüs|se|lung
Nutz‖wert‖ana|ly|se
AP2-‖Pro|jekt‖do|ku|men|ta|ti|on
Amor|ti|sa|ti|ons‖rech|nung
Über|tra|gungs‖ge|schwin|dig|keit
Un|ter|bre|chungs‖freie
UND-‖Ver|knüp|fung
Sub‖netz‖mas|ke
Not|fall‖wie|der‖her|stel|lung
In|ves|ti|ti|ons‖ent|schei|dung
Da|ten‖schutz‖kon|for|me
Do|ku|men|ten‖ma|nage|ment‖sys|tem
Schwach|stel|len‖ma|nage|ment
Netz‖werk‖kom|po|nen|ten
Re|mote‖desk|top‖diens|te-‖Farm
""".split()

# "Nie trennen" (Anhang A): keine Stelle, auch nicht bei Platzmangel mit Strich
NIE_TRENNEN = ("192.168.1.50/24", "255.255.255.0", "IPv6", "AP1", "AP2", "RFC", "3021",
               "2^(32", "-")


def erwartung(eintrag):
    """(wort, alle Stellen, bevorzugte Stellen) aus der Schreibweise der Liste."""
    wort, alle, bevorzugt = "", [], []
    for zeichen in eintrag:
        if zeichen in "‖|":
            alle.append(len(wort))
            if zeichen == "‖":
                bevorzugt.append(len(wort))
        else:
            wort += zeichen
    return wort, alle, bevorzugt


class RegelTest(unittest.TestCase):

    def test_jede_zeile_passt(self):
        """A-N8-05: Wortliste x Breiten 80..400 px - keine Zeile breiter als
        die Breite, kein Zeichen verloren (ausser eingefuegten Trennstrichen
        und den Leerzeichen an Umbruechen)."""
        for text in WOERTER:
            for breite in range(80, 401, 10):
                zeilen, _geteilt = ft.zeilen(text, breite, messen)
                for zeile in zeilen:
                    self.assertLessEqual(messen(zeile), breite, (text, breite, zeilen))
                self.assertEqual(ohne_trennstriche(zeilen, text),
                                 text.replace(" ", ""), (text, breite, zeilen))

    def test_bindestrich(self):
        self.assertEqual(ft.zeilen("Mehrfaktor-Authentifizierung", 200, messen),
                         (["Mehrfaktor-", "Authentifizierung"], True))
        self.assertEqual(ft.anzeige_text("Einführung einer Mehrfaktor-Authentifizierung",
                                         200, messen),
                         "Einführung einer\nMehrfaktor-\nAuthentifizierung")

    def test_nummer_bleibt_beim_titel(self):
        """K4: "4." steht nie allein - auch wenn das Wort geteilt werden muss."""
        for breite in range(60, 400, 10):
            for text in ("4. Wirtschaftlichkeitsbetrachtung", "4. Mehrfaktor-Authentifizierung",
                         "12. Einfache Wirtschaftlichkeitsbetrachtung ✓"):
                zeilen, _ = ft.zeilen(text, breite, messen)
                nummer = text.split(" ")[0]
                self.assertTrue(zeilen[0].startswith(nummer + " ") and
                                len(zeilen[0]) > len(nummer) + 1, (text, breite, zeilen))
        self.assertEqual(ft.zeilen("4. Mehrfaktor-Authentifizierung", 150, messen)[0][0],
                         "4. Mehrfaktor-")

    def test_unveraendert_wenn_es_passt(self):
        """K5: passt der Titel mit dem gewoehnlichen Umbruch, bleibt der Text
        zeichengleich (keine Trennung auf Vorrat, kein Zeilenumbruch)."""
        for text in ("3. Netzplan für eine Arztpraxis", "Einfache Wirtschaftlichkeitsbetrachtung",
                     "4. Wirtschaftlichkeitsbetrachtung"):
            self.assertEqual(ft.anzeige_text(text, 400, messen), text)
        # an Leerzeichen umbrechen reicht -> Text bleibt gleich (Tk/Flutter brechen)
        self.assertEqual(ft.anzeige_text("3. Netzplan für eine Arztpraxis", 150, messen),
                         "3. Netzplan für eine Arztpraxis")

    def test_rueckfall_ohne_stelle(self):
        """Ohne zulaessige Stelle (Wort nicht in der Liste, kein Bindestrich):
        teilen wie bisher (ohne Strich), Nummer beim Wort, jede Zeile passt."""
        zeilen, geteilt = ft.zeilen("4. Kundenzufriedenheitsanalyse", 150, messen)
        self.assertTrue(geteilt)
        self.assertEqual(zeilen[0], "4. Kundenzufrie")   # 15 Zeichen = 150 px
        self.assertFalse(any(z.endswith("-") for z in zeilen[:-1]), zeilen)


class ListeTest(unittest.TestCase):
    """Weisung zu Meldung 42, Fragen 11-13: nur die bestaetigte Liste
    (Anhang A), mindestens 2 Buchstaben je Seite, einzelner Vokal in der
    Wortmitte zulaessig, bevorzugte Stellen zuerst."""

    def test_33_woerter_genau_ihre_stellen(self):
        self.assertEqual(len(ANHANG_A), 33)
        for eintrag in ANHANG_A:
            wort, alle, bevorzugt = erwartung(eintrag)
            for form in (wort, wort.lower(), wort.upper()):
                self.assertEqual(ft.trennstellen(form), alle, (eintrag, form))
                self.assertEqual(ft.bevorzugte_stellen(form), bevorzugt, (eintrag, form))
            # Satzzeichen am Rand bleiben am Wort ("Investitionsentscheidung:")
            self.assertEqual(ft.trennstellen(wort + ":"), alle, eintrag)
            self.assertEqual(ft.trennstellen("(" + wort + ")"), [p + 1 for p in alle], eintrag)

    def test_nur_die_liste(self):
        """Frage 11 (b): ein Wort ausserhalb der Liste bekommt nur Stellen nach
        einem vorhandenen Bindestrich (keine Silbenregel)."""
        listenwoerter = {erwartung(e)[0].lower() for e in ANHANG_A}
        self.assertEqual({w.lower() for w in (erwartung(e)[0] for e in ft.ANHANG_A)},
                         listenwoerter)
        for wort in ("Kundenzufriedenheitsanalyse", "Datensicherungskonzept",
                     "Wirtschaftlichkeit", "Anpassung", "Netzwerk"):
            self.assertEqual(ft.trennstellen(wort), [], wort)
        self.assertEqual(ft.trennstellen("Mehrfaktor-Verfahren"), [11])

    def test_nie_trennen(self):
        for wort in NIE_TRENNEN:
            self.assertEqual(ft.trennstellen(wort), [], wort)
        # Formel: nur das Wort "Präfixlänge" darf getrennt werden
        self.assertEqual(ft.trennstellen("Präfixlänge)"), [3, 6, 9])
        for text in ("192.168.1.50/24", "255.255.255.0", "IPv6 AP1 AP2 RFC 3021",
                     "2^(32 - Präfixlänge)"):
            for breite in range(60, 200, 10):
                zeilen, _ = ft.zeilen(text, breite, messen)
                for zeile in zeilen[:-1]:
                    letztes = zeile.split(" ")[-1]
                    if letztes.endswith("-") and letztes != "-":
                        self.assertTrue(text.startswith("2^(32") and
                                        letztes[:-1] in "Präfixlänge",
                                        (text, breite, zeilen))

    def test_mindestens_zwei_buchstaben(self):
        """Frage 12: links und rechts jeder Stelle mindestens 2 Buchstaben -
        auch an einem vorhandenen Bindestrich."""
        for eintrag in ANHANG_A:
            wort = erwartung(eintrag)[0]
            for stelle in ft.trennstellen(wort):
                self.assertGreaterEqual(sum(z.isalpha() for z in wort[:stelle]), 2, eintrag)
                self.assertGreaterEqual(sum(z.isalpha() for z in wort[stelle:]), 2, eintrag)
        self.assertEqual(ft.trennstellen("E-Mail-Adresse"), [7])
        self.assertEqual(ft.trennstellen("IT-X"), [])
        self.assertEqual(ft.trennstellen("-ab-"), [])

    def test_einzelner_vokal_und_vorrang(self):
        """Frage 13: "Vir-tu-a-li-sie-rung" zulaessig; eine weitere Stelle wird
        nur genommen, wenn keine bevorzugte passt."""
        self.assertEqual(ft.zeilen("Virtualisierung", 60, messen)[0][0], "Virtu-")
        # 22 Zeichen Platz: "Wirtschaftlichkeitsbe-" passte, die Fuge geht vor
        self.assertEqual(ft.zeilen("Wirtschaftlichkeitsbetrachtung", 220, messen)[0],
                         ["Wirtschaftlichkeits-", "betrachtung"])
        # passt keine bevorzugte, die hinterste passende weitere Stelle
        self.assertEqual(ft.zeilen("Wirtschaftlichkeitsbetrachtung", 180, messen)[0][0],
                         "Wirtschaftlich-")
        self.assertEqual(ft.zeilen("Nutzwertanalyse", 100, messen)[0],
                         ["Nutzwert-", "analyse"])

    def test_zeilen_der_liste(self):
        """Jedes Wort der Liste in Breiten 80..400 px, mit Nummer "29. " ab
        120 px (dann passt jede Silbe mit Strich, laengste "29. Schwach-" und
        "schluss-"): jede Zeile passt, jede Zeile
        im Wort endet mit "-" (nie "--", kein Rueckfall ohne Strich), getrennt
        nur an Stellen der Liste, die Nummer bleibt beim Wort."""
        for eintrag in ANHANG_A:
            wort, alle, _ = erwartung(eintrag)
            for text, vorn in ((wort, 0), ("29. " + wort, 4)):
                for breite in range(120 if vorn else 80, 401, 10):
                    zeilen, _ = ft.zeilen(text, breite, messen)
                    self.assertEqual(ohne_trennstriche(zeilen, text), text.replace(" ", ""))
                    if vorn:
                        self.assertTrue(len(zeilen[0]) > vorn, (text, breite, zeilen))
                    position = 0
                    for zeile in zeilen[:-1]:
                        self.assertNotIn("--", zeile, (text, breite, zeilen))
                        self.assertLessEqual(messen(zeile), breite, (text, breite, zeilen))
                        stueck = zeile[:-1] if zeile.endswith("-") and \
                            text[position:position + len(zeile)] != zeile else zeile
                        position += len(stueck)
                        self.assertTrue(zeile.endswith("-"), (text, breite, zeilen))
                        self.assertIn(position - vorn, alle, (text, breite, zeilen))

    def test_kein_doppelter_strich(self):
        """An einem vorhandenen Bindestrich kein zweiter Strich."""
        self.assertEqual(ft.zeilen("Punkt-zu-Punkt-Verbindungen", 100, messen)[0][:3],
                         ["Punkt-zu-", "Punkt-", "Verbindun-"])
        self.assertEqual(ft.zeilen("Remotedesktopdienste-Farm", 210, messen)[0],
                         ["Remotedesktopdienste-", "Farm"])

    def test_nummer_titel_handy(self):
        self.assertEqual(ft.nummer_titel(4, "Wirtschaftlichkeit", " ✓"),
                         "4. Wirtschaftlichkeit ✓")


# ---------------------------------------------------------------------------
#  Lange Woerter (Weisung zu Meldung 43, 2.1)
# ---------------------------------------------------------------------------
GRENZE = 18
# Dateien, deren Zeichenketten als Titel/Beschriftung erscheinen (AST)
QUELL_DATEIEN = ("app_gui.py", "fisi_widgets.py", "fisi_optionen.py", "fisi_hilfe.py",
                 "fisi_projekt.py", "mobile/src/main.py", "mobile/src/ui.py")
TITEL_KW = {"title", "subtitle", "heading", "kicker"}
TEXT_KW = {"text", "label", "caption", "placeholder", "placeholder_text", "hint",
           "tooltip", "value"}
TEXT_AUFRUFE = {"make_label", "NeoButton", "Card", "CTkLabel", "CTkButton",
                "section_title", "Text", "label"}
# Anker: muessen gefunden werden (Grenze und alle vier Quellen wirken)
ANKER = {"Tabellenkalkulation": "Listentitel", "Ausbildungsverordnung": "Titel",
         "Schnittstellenkennung": "Rechenwege", "Netzwerkmodernisierung": "Listentitel"}


def _konstanten(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return [node.value]
    if isinstance(node, ast.JoinedStr):
        return [v.value for v in node.values if isinstance(v, ast.Constant)]
    if isinstance(node, ast.BinOp):
        return _konstanten(node.left) + _konstanten(node.right)
    return []


def quelltexte():
    """{Gruppe: [Text, ...]} fuer Titel, Listentitel, Beschriftungen,
    Rechenwege (Muster werkzeug/lange_woerter.py der Meldung 43)."""
    sys.path.insert(0, os.path.join(HERE, "pruefung"))
    import fisi_core as fc
    import fisi_lernen as fl
    import rechenweg_texte as rt
    texte = {"Listentitel": [], "Titel": [], "Beschriftungen": [], "Rechenwege": []}
    for daten in (fc.AP1_SZENARIEN, fc.SZENARIEN, fc.PROJEKTARBEITEN):
        texte["Listentitel"] += [item["title"] for item in daten]
    for datei in QUELL_DATEIEN:
        with open(os.path.join(HERE, datei), encoding="utf-8") as handle:
            tree = ast.parse(handle.read())
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                for kw in node.keywords:
                    if kw.arg in TITEL_KW:
                        texte["Titel"] += _konstanten(kw.value)
                    elif kw.arg in TEXT_KW:
                        texte["Beschriftungen"] += _konstanten(kw.value)
                name = getattr(node.func, "attr", getattr(node.func, "id", ""))
                if name in TEXT_AUFRUFE and len(node.args) > 1:
                    texte["Beschriftungen"] += _konstanten(node.args[1])
            if isinstance(node, ast.Assign) and len(node.targets) == 1 and \
                    getattr(node.targets[0], "id", "") in ("NAV_ITEMS", "VIEW_TITLES"):
                for sub in ast.walk(node.value):
                    texte["Titel"] += [t for t in _konstanten(sub)
                                       if not t.isidentifier() or t.isupper()]
    texte["Rechenwege"] += list(rt.erzeuge(fc, fl).values())
    for kind, _name in fl.TRAINER_KINDS:
        for level, _label in fl.TRAINER_LEVELS:
            for seed in range(rt.TRAINER_SEEDS):
                task = fl.trainer_task(kind, level, "e3-%d" % seed)
                if kind not in rt.ALTE_ARTEN:
                    texte["Rechenwege"].append(rt.trainer_text(task))
                if seed < 5:
                    texte["Beschriftungen"] += [label for _key, label in task.fields]
    return texte


def lange_woerter(texte):
    """{Wort: {Gruppen}} aller Woerter ueber GRENZE Zeichen (Satzzeichen am
    Rand ab), ohne Zahlen/Adressen ("nie trennen") und ohne Woerter, die ein
    vorhandener Bindestrich in Stuecke <= GRENZE teilt."""
    funde = {}
    for gruppe, liste in texte.items():
        for text in liste:
            for token in re.split(r"\s+", text):
                anfang, ende = ft._kern(token)
                kern = token[anfang:ende]
                if len(kern) <= GRENZE:
                    continue
                if re.fullmatch(r"[0-9A-Fa-f:./x^()]+", kern) or \
                        sum(z.isalpha() for z in kern) < len(kern) / 2:
                    continue
                if "-" in kern and all(len(t) <= GRENZE for t in kern.split("-")) and \
                        ft.trennstellen(kern):
                    continue
                funde.setdefault(kern, set()).add(gruppe)
    return funde


NIE_IN = ("ch", "ck", "ie", "ei", "au", "eu")


def vorpruefung(eintraege, quellwoerter=None):
    """Maschinelle Vorpruefung (Weisung zu Meldung 43, 2.1). Liefert eine
    Liste von Befunden (leer = bestanden):
      (i)   die Teile ergeben zusammen das Wort; mit quellwoerter: das Wort
            steht genau so in einer Quelle
      (ii)  mindestens 2 Buchstaben links und rechts jeder Stelle
      (iii) keine Stelle in ch, sch, ie, ei, au, eu, ck und keine in einer
            Abkuerzung mit Ziffer ("nie trennen")
      (iv)  kein Wort doppelt"""
    befunde, gesehen = [], {}
    for eintrag in eintraege:
        teile = re.split("[‖|]", eintrag)
        wort = "".join(teile)
        alle = ft._liste([eintrag])[wort.lower()][0]
        if not all(teile) or not re.fullmatch(r"[\w-]+", wort) or "_" in wort:
            befunde.append("(i) %s: leere oder fremde Teile" % eintrag)
        if quellwoerter is not None and wort not in quellwoerter:
            befunde.append("(i) %s: %r steht so in keiner Quelle" % (eintrag, wort))
        for stelle in alle:
            if sum(z.isalpha() for z in wort[:stelle]) < 2 or \
                    sum(z.isalpha() for z in wort[stelle:]) < 2:
                befunde.append("(ii) %s: Stelle %d mit weniger als 2 Buchstaben"
                               % (eintrag, stelle))
            paar = wort[stelle - 1:stelle + 1].lower()
            if paar in NIE_IN or wort[stelle - 1:stelle + 2].lower() == "sch":
                befunde.append("(iii) %s: Stelle %d in %r" % (eintrag, stelle, paar))
            links = wort[:stelle].rsplit("-", 1)[-1]
            rechts = wort[stelle:].split("-", 1)[0]
            if links and rechts and re.search(r"\d", links + rechts):
                befunde.append("(iii) %s: Stelle %d in einer Abkuerzung mit Ziffer"
                               % (eintrag, stelle))
        if wort.lower() in gesehen:
            befunde.append("(iv) %s: doppelt (auch %s)" % (eintrag, gesehen[wort.lower()]))
        gesehen[wort.lower()] = eintrag
    return befunde


class LangeWoerterTest(unittest.TestCase):
    """Weisung zu Meldung 43, 2.1: jedes Wort ueber 18 Zeichen in Titeln,
    Listentiteln, Beschriftungen und Rechenwegen hat einen Listeneintrag.
    Endet ROT bei jedem fehlenden Wort (nicht abgeschwaecht)."""

    @classmethod
    def setUpClass(cls):
        cls.funde = lange_woerter(quelltexte())

    def test_anker_gefunden(self):
        """Grenze und Quellen wirken (sonst waere der Test still leer)."""
        for wort, gruppe in ANKER.items():
            self.assertIn(gruppe, self.funde.get(wort, set()), wort)

    def test_jedes_lange_wort_hat_einen_eintrag(self):
        liste = {w.lower() for w in ft._LISTE}
        fehlen = sorted("%s (%s)" % (wort, ", ".join(sorted(gruppen)))
                        for wort, gruppen in self.funde.items()
                        if wort.lower() not in liste)
        self.assertEqual(fehlen, [], "%d lange Woerter ohne Eintrag in "
                         "fisi_trennung.WOERTER" % len(fehlen))


class VorpruefungTest(unittest.TestCase):
    """Maschinelle Vorpruefung (i)-(iv) ueber alle Eintraege der Liste."""

    def test_alle_eintraege(self):
        self.assertEqual(vorpruefung(ft.WOERTER), [])

    def test_neue_woerter_stehen_so_in_den_quellen(self):
        """(i) fuer die Woerter aus Meldung 43: Schreibweise wie in der Quelle."""
        quellwoerter = set(lange_woerter(quelltexte()))
        self.assertEqual(vorpruefung(ft.LANGE_WOERTER, quellwoerter), [])
        self.assertEqual(len(ft.LANGE_WOERTER), 94)

    def test_pruefung_greift(self):
        """Die Pruefung selbst erkennt jeden Fall (eigene Kontrollfehler)."""
        self.assertTrue(vorpruefung(["Rec|hner"]))            # (iii) ch
        self.assertTrue(vorpruefung(["Wa|sche"]) == [])       # vor sch erlaubt
        self.assertTrue(vorpruefung(["Was|che"]))             # (iii) s|ch
        self.assertTrue(vorpruefung(["Zu|cker", "Zuc|ker"])[0].startswith("(iii)"))
        self.assertTrue(vorpruefung(["U|ni|ver|si|tät"]))     # (ii)
        self.assertTrue(vorpruefung(["IPv|6-‖Adres|se"]))     # (iii) Ziffer
        self.assertTrue(vorpruefung(["Re|chen", "re|chen"]))  # (iv)
        self.assertTrue(vorpruefung(["Re||chen"]))            # (i)


class HandyPaketTest(unittest.TestCase):
    """B3 (a): Die Handy-App bekommt das Modul."""

    def test_shared_files(self):
        sys.path.insert(0, os.path.join(HERE, "mobile"))
        import vorbereiten
        self.assertIn("fisi_trennung.py", vorbereiten.SHARED_FILES)

    def test_apk_pruefung_kennt_modul(self):
        """B3 (a): Die APK-Pruefung verlangt fisi_trennung.pyc in app.zip."""
        sys.path.insert(0, os.path.join(HERE, "pruefung"))
        import apk_pruefen
        self.assertIn("fisi_trennung.pyc", apk_pruefen.APP_FILES)

    def test_gitignore(self):
        with open(os.path.join(HERE, ".gitignore"), encoding="utf-8") as handle:
            self.assertIn("mobile/src/fisi_trennung.py", handle.read().splitlines())

    def test_handy_liste_nutzt_regel(self):
        """K4 am Handy: die Listenzeile setzt "4." mit geschuetztem
        Leerzeichen vor den Titel (fisi_trennung.nummer_titel)."""
        with open(os.path.join(HERE, "mobile", "src", "main.py"), encoding="utf-8") as handle:
            tree = ast.parse(handle.read())
        imports = {alias.name for node in ast.walk(tree) if isinstance(node, ast.Import)
                   for alias in node.names}
        self.assertIn("fisi_trennung", imports)
        calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call) and
                 isinstance(node.func, ast.Attribute) and node.func.attr == "nummer_titel"]
        self.assertTrue(calls)


if __name__ == "__main__":
    unittest.main(verbosity=2)
