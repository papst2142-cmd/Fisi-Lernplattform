#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fachinformatiker Lernplattform - Lizenz, Hinweistext und Erststart-Hinweis (ab 0.62)
===================================================================================

Alle Texte zu Lizenz und Rechtlichem stehen nur hier, damit PC (app_gui.py)
und Handy (mobile/src/main.py) wortgleich sind (Plan 0.62, Abschnitt 7).
test_rechtliches.py prueft jeden Wortlaut.

Dateien (liegen im Programm neben den Lerninhalten, beim Start aus dem
Quellcode im Hauptordner):
  LICENSE.txt               Lizenz des Programms (Nico H)
  THIRD_PARTY_NOTICES.txt   Hinweise zu Fremdbestandteilen, beim Bau von
                            lizenzen.py (PC) bzw. pruefung/lizenzen_android.py
                            (Handy) erzeugt - nie von Hand pflegen

Erststart-Hinweis: Merker HINWEIS_KEY nur in einstellungen.json (je Geraet),
nie in der Lern-Datenbank, nie im Abgleich, nicht in der Sicherung.
"""

import datetime
import os
import sys

from fisi_update import load_settings, save_settings

# ============================================================================
#  TEXTE (PC UND HANDY GLEICH)
# ============================================================================

PUBLISHER = "Nico H"
COPYRIGHT = "Copyright (c) 2026 Nico H – Alle Rechte vorbehalten"
# Kurzform fuer Copyright-Felder der Pakete (Exe, Installer, macOS, .deb) - ASCII
COPYRIGHT_FELD = "Copyright (c) 2026 Nico H"

# Hinweistext lang (Plan 0.62, 7.1; Satz zur Herkunft von Nico bestaetigt, E11)
HINWEIS = ("Die Fachinformatiker Lernplattform ist ein privates Lernprogramm. Sie ist "
           "kein Angebot und kein Produkt einer Industrie- und Handelskammer (IHK) oder "
           "einer anderen Prüfungsstelle und wird von diesen weder herausgegeben noch "
           "geprüft. Die Aufgaben, Szenarien und Testprojekte sind eigene "
           "Übungsaufgaben. Sie enthalten keine offiziellen Prüfungsaufgaben. "
           "Bezeichnungen wie „AP1“, „AP2“ oder „Note nach IHK-Schlüssel“ beschreiben "
           "nur, wofür geübt wird und nach welchem Notenschlüssel die Übung "
           "ausgewertet wird.")
# Kurzform fuer die Karte des Pruefungsmodus
HINWEIS_KURZ = "Übungsprüfung, keine offizielle IHK-Prüfung."
# Erststart-Leiste
ERSTSTART = ("Privates Lernprogramm: keine offiziellen IHK-Prüfungsaufgaben, kein "
             "IHK-Produkt. Mehr dazu unter Optionen › Über das Programm.")
BTN_VERSTANDEN = "Verstanden"
# Hinweis zur Entstehung: nur der Name, kein Logo, keine weitere Aussage
CLAUDE_HINWEIS = "Erstellt mit Hilfe von Claude (Anthropic)."
# Abschlussprojekt (Fassung Claude Chat, E12 - nennt keine bestimmte Kammer)
KI_HINWEIS = ("Wenn du für dein Abschlussprojekt KI-Hilfsmittel nutzt (zum Beispiel "
              "für Texte, Code oder Bilder), verlangen manche Kammern eine Angabe dazu "
              "in der Projektdokumentation. Frag bei deiner IHK nach, was für dich gilt.")

# Note des Pruefungstrainers (Nicos Entscheidung zum IHK-Wortlaut)
NOTE_LANG = "Note nach IHK-Schlüssel (Orientierung, keine amtliche Note)"
NOTE_KURZ = "Note (Orientierung)"

# Knoepfe und Fenster in "Über das Programm"
BTN_LIZENZ = "Lizenz"
BTN_FREMD = "Hinweise zu Fremdbestandteilen"
TITEL_LIZENZ = "Lizenz"
TITEL_FREMD = "Hinweise zu Fremdbestandteilen"
UEBERSICHT = "Übersicht"
ABSCHNITT = "Abschnitt"
# Handy: Kopfzeile der Unterseiten (wie die anderen Seiten in Grossbuchstaben)
CRUMB_LIZENZ = ("SYSTEM", "LIZENZ")
CRUMB_FREMD = ("SYSTEM", "FREMDBESTANDTEILE")
DATEI_FEHLT = ("Die Datei %s liegt nicht bei. Beim Start aus dem Quellcode entsteht "
               "sie erst beim Bau (lizenzen.py, Handy: mobile/vorbereiten.py).")

LICENSE_FILE = "LICENSE.txt"
NOTICES_FILE = "THIRD_PARTY_NOTICES.txt"
# Abschnitte in THIRD_PARTY_NOTICES.txt beginnen mit dieser Zeile
SECTION_MARK = "#### "


def about_text(app_title, app_version, platform_text):
    """Text der Seite "Über das Programm" (PC und Handy, nur platform_text
    unterscheidet sich: womit die jeweilige Version umgesetzt ist)."""
    return ("%s Version %s\n%s\n\n"
            "Lernprogramm für die Prüfungsvorbereitung zum Fachinformatiker "
            "(Schwerpunkt Systemintegration) mit Karteikarten, Prüfungstrainer, "
            "AP1-/AP2-Szenarien, Testprojekten und Praxis-Rechnern.\n\n%s\n\n%s\n\n%s"
            % (app_title, app_version, COPYRIGHT, platform_text, HINWEIS, CLAUDE_HINWEIS))


# ============================================================================
#  DATEIEN
# ============================================================================

def _search_dirs():
    here = os.path.dirname(os.path.abspath(__file__))
    dirs = []
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        dirs.append(meipass)
    dirs.append(here)
    dirs.append(os.path.dirname(here))       # mobile/src -> mobile (Quellcode)
    return dirs


def find_file(name):
    for folder in _search_dirs():
        path = os.path.join(folder, name)
        if os.path.isfile(path):
            return path
    return None


def read_file(name):
    """Inhalt der Datei oder ein Hinweis, dass sie fehlt (nie eine Ausnahme)."""
    path = find_file(name)
    if not path:
        return DATEI_FEHLT % name
    try:
        with open(path, encoding="utf-8") as handle:
            return handle.read()
    except (OSError, UnicodeDecodeError) as error:
        return DATEI_FEHLT % name + " (%s)" % error


def flow_text(text):
    """Absaetze zu je einer Zeile zusammenfassen (Handy: LICENSE.txt hat feste
    Zeilenumbrueche, die auf dem schmalen Bildschirm zu Flatterzeilen fuehren)."""
    paragraphs = [" ".join(line.strip() for line in block.splitlines())
                  for block in text.strip().split("\n\n")]
    return "\n\n".join(paragraphs)


def parse_notices(text):
    """THIRD_PARTY_NOTICES.txt -> (Uebersicht, [(Titel, Text), ...]). Die
    Oberflaechen zeigen zuerst nur die Uebersicht und einen Abschnitt erst auf
    Wunsch - ein Textfeld mit dem ganzen Text (bis 1,5 MB) waere zu langsam."""
    intro, sections, title, lines = [], [], None, []
    for line in text.splitlines():
        if line.startswith(SECTION_MARK):
            if title is not None:
                sections.append((title, "\n".join(lines).strip("\n")))
            title, lines = line[len(SECTION_MARK):].strip(), []
        elif title is None:
            intro.append(line)
        else:
            lines.append(line)
    if title is not None:
        sections.append((title, "\n".join(lines).strip("\n")))
    return "\n".join(intro).strip("\n"), sections


def load_notices():
    return parse_notices(read_file(NOTICES_FILE))


def section_label(title):
    """Kurzer Name eines Abschnitts fuer die Auswahl (ohne Lizenzangabe)."""
    return title.split(" – ")[0]


def notice_choices(intro, sections):
    """Eintraege der Auswahl: zuerst die Uebersicht, dann die Abschnitte.
    Liefert [(Name, Text)], Namen eindeutig."""
    choices, seen = [(UEBERSICHT, intro)], {UEBERSICHT}
    for title, body in sections:
        name = section_label(title)
        while name in seen:
            name += " "
        seen.add(name)
        choices.append((name, "%s\n\n%s" % (title, body)))
    return choices


# ============================================================================
#  ERSTSTART-HINWEIS (JE GERAET, einstellungen.json)
# ============================================================================

HINWEIS_KEY = "hinweis_rechtliches"   # Datum, an dem "Verstanden" gedrueckt wurde


def notice_due(settings=None):
    """Soll die Leiste erscheinen? Ja, bis einmal "Verstanden" gedrueckt
    wurde - auch fuer bestehende Nutzer nach dem Update (E6)."""
    settings = load_settings() if settings is None else settings
    return not settings.get(HINWEIS_KEY)


def mark_notice_seen(today=None):
    settings = load_settings()
    settings[HINWEIS_KEY] = (today or datetime.date.today()).isoformat()
    return save_settings(settings)
