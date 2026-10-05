#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FISI Lernplattform - Erststart-Rundgang und Hilfe (ab 0.56)
===========================================================

Texte und Logik ohne Oberflaeche, damit PC (app_gui.py) und Handy
(mobile/src/main.py) genau dieselben Texte zeigen.

Rundgang:
  * erscheint automatisch nur, wenn die Datenbank noch keinerlei Lern- oder
    Spieldaten hat UND der Merker "rundgang_gesehen" in einstellungen.json
    fehlt (Bestandsschutz: wer schon gelernt hat, sieht ihn nur auf Wunsch)
  * nach Abschluss oder Ueberspringen wird der Merker gesetzt
  * der letzte Schritt "Jetzt einrichten" speichert Name, Rahmenplan-
    Abschnitte und Pruefungstermine - nur in einstellungen.json (je Geraet),
    nie in der Lern-Datenbank und nie im Abgleich

Hilfe:
  * HELP_SECTIONS: kurze Texte in einfacher Sprache, PC und Handy gleich
  * search_help(): Treffer fuer die Suche in der Kopfzeile

Ablauf:
  if tour_due(db): ... Rundgang zeigen ...
  fehler = save_setup(name, {"B": False, ...}, "29.09.2027", "26.04.2028")
  mark_tour_seen()
"""

import datetime

import fisi_rahmenplan as frp
from fisi_update import REPOSITORY, load_settings, save_settings

# ============================================================================
#  EINSTELLUNGEN (JE GERAET, einstellungen.json)
# ============================================================================

TOUR_SEEN_KEY = "rundgang_gesehen"   # Datum, an dem der Rundgang beendet wurde
NAME_KEY = "nutzer_name"             # Name aus "Jetzt einrichten"
NAME_MAX = 40


def db_has_data(db):
    """True, sobald irgendeine Tabelle der Datenbank einen Eintrag hat
    (Lernstand, Pruefungen, Abschlussprojekt, Spiel, Bestenliste, Abgleich).
    Kann die Datenbank nicht gelesen werden, gilt sie als befuellt - dann
    erscheint der Rundgang lieber nicht von selbst."""
    rows = db._execute("SELECT name FROM sqlite_master WHERE type = 'table' "
                       "AND name NOT LIKE 'sqlite_%'", fetch="all", default=None)
    if rows is None:
        return True
    for (table,) in rows:
        found = db._execute('SELECT 1 FROM "%s" LIMIT 1' % table.replace('"', '""'),
                            fetch="one", default=True)
        if found:
            return True
    return False


def tour_seen(settings=None):
    settings = load_settings() if settings is None else settings
    return bool(settings.get(TOUR_SEEN_KEY))


def tour_due(db, settings=None):
    """Soll der Rundgang beim Start von selbst erscheinen?"""
    return not tour_seen(settings) and not db_has_data(db)


def mark_tour_seen(today=None):
    """Merker setzen (nach "Fertig" oder "Ueberspringen")."""
    settings = load_settings()
    settings[TOUR_SEEN_KEY] = (today or datetime.date.today()).isoformat()
    return save_settings(settings)


def load_name():
    return str(load_settings().get(NAME_KEY) or "")


def clean_name(text):
    return " ".join(str(text or "").split())[:NAME_MAX]


def save_name(text):
    """Ab 0.56 (Feld in den Optionen): Name speichern, nur in
    einstellungen.json. Rueckgabe: der bereinigte Name (leer = kein Name)."""
    name = clean_name(text)
    settings = load_settings()
    if str(settings.get(NAME_KEY) or "") != name:
        settings[NAME_KEY] = name
        save_settings(settings)
    return name


def greeting(name=None):
    """Begruessung auf dem Dashboard (am Handy: Start), "" ohne Namen."""
    name = clean_name(load_name() if name is None else name)
    return GREETING % name if name else ""


def setup_values():
    """Startwerte der Seite "Jetzt einrichten" (aus den Einstellungen)."""
    values = frp.load_rp_settings()
    return {
        "name": load_name(),
        "abschnitte": {section: values[frp.SECTION_SETTING[section]]
                       for section in frp.OPTIONAL_SECTIONS},
        "rp_termin_ap1": frp.date_text(values["rp_termin_ap1"]),
        "rp_termin_ap2": frp.date_text(values["rp_termin_ap2"]),
    }


def check_date(text):
    """(iso, fehler): leer ist erlaubt (kein Termin), sonst TT.MM.JJJJ -
    dieselbe Pruefung wie in den Optionen (frp.parse_date)."""
    text = str(text or "").strip()
    if not text:
        return "", None
    day = frp.parse_date(text)
    if day is None:
        return None, frp.DATE_INVALID
    return day.isoformat(), None


def save_setup(name, sections, ap1, ap2):
    """Speichert "Jetzt einrichten". Rueckgabe: None oder der Fehlertext
    (ungueltiges Datum) - dann wird gar nichts gespeichert."""
    dates = {}
    for key, text in (("rp_termin_ap1", ap1), ("rp_termin_ap2", ap2)):
        value, error = check_date(text)
        if error:
            return error
        dates[key] = value
    settings = load_settings()
    settings[NAME_KEY] = clean_name(name)
    save_settings(settings)
    values = {frp.SECTION_SETTING[section]: bool(sections.get(section))
              for section in frp.OPTIONAL_SECTIONS if section in sections}
    values.update(dates)
    frp.save_rp_settings(**values)
    return None


# ============================================================================
#  TEXTE RUNDGANG (PC UND HANDY GLEICH)
# ============================================================================

TOUR_TITLE = "Rundgang"
TOUR_STEP = "Schritt %d von %d"
TOUR_SKIP = "Überspringen"
TOUR_BACK = "Zurück"
TOUR_NEXT = "Weiter"
TOUR_FINISH = "Speichern und loslegen"
TOUR_KEYS = "Tab wechselt, Eingabe bestätigt, Esc überspringt"   # nur am PC

TOUR_PAGES = [
    {"id": "willkommen", "titel": "Willkommen",
     "text": ("Die FISI Lernplattform hilft dir bei der Vorbereitung auf die Prüfungen "
              "zum Fachinformatiker Systemintegration (AP1 und AP2).\n\n"
              "Lernen kannst du mit „Karteikarten“, im „Prüfungstrainer“ und mit den "
              "„AP1-Szenarien“ und „AP2-Szenarien“, die wie Prüfungsaufgaben aufgebaut "
              "sind. Am PC findest du alles links in der Seitenleiste, am Handy unter "
              "„Lernen“.")},
    {"id": "fortschritt", "titel": "Fortschritt und Rahmenplan",
     "text": ("Unter „Fortschritt“ siehst du, was du schon kannst: deine Ergebnisse, die "
              "Lernserie und die „Rahmenplan-Abdeckung“ für jeden Punkt des "
              "Ausbildungsrahmenplans.\n\n"
              "„Jetzt wiederholen“ im „Dashboard“ (am Handy: „Start“) holt fällige "
              "Karten und Fragen zurück, damit du nichts vergisst.")},
    {"id": "spiel", "titel": "Spiel",
     "text": ("Im „Spiel“ arbeitest du in einer IT-Firma und löst Tickets aus dem "
              "Berufsalltag. Dein Wissensstand im Spiel kommt aus dem, was du mit "
              "Karteikarten und im Prüfungstrainer lernst.\n\n"
              "Später kannst du eine eigene Firma gründen.")},
    {"id": "sicherung", "titel": "Sicherung und Abgleich",
     "text": ("Dein Lernstand wird auf diesem Gerät gespeichert. In den „Optionen“ "
              "sicherst du ihn mit „Sicherung erstellen“ als Datei oder hältst PC und "
              "Handy mit „Abgleich PC und Handy“ auf demselben Stand.\n\n"
              "Fragen beantwortet die „Hilfe“. Diesen Rundgang kannst du in den "
              "„Optionen“ jederzeit wieder starten.")},
    {"id": "einrichten", "titel": "Jetzt einrichten",
     "text": ("Alle Angaben sind freiwillig und gelten nur für dieses Gerät. Rahmenplan "
              "und Termine kannst du später in den „Optionen“ unter „Rahmenplan“ "
              "ändern.")},
]

SETUP_NAME = "Dein Name"
SETUP_NAME_HINT = "freiwillig"
SETUP_PLAN = "Rahmenplan"
SETUP_PLAN_HINT = ("Die Abschnitte B, D und E gehören zu anderen Fachrichtungen. Für "
                   "Systemintegration kannst du sie ausgeschaltet lassen.")
SETUP_DATES = "Prüfungstermine"
SETUP_DATES_HINT = ("Format TT.MM.JJJJ, leer lassen geht auch. Mit Termin kommen in den "
                    "sechs Monaten davor neue Aufgaben zu prüfungsrelevanten Themen etwas "
                    "früher dran, solange „Übungsauswahl nach Rahmenplan gewichten“ an ist.")

# Ab 0.56 (Nachbesserung): Name in den Optionen und Begruessung im Kopf des
# Dashboards (am Handy: Start) statt "Dein Lernstand"
GREETING = "Hallo %s"
NAME_OPTION_HINT = ("Nur auf diesem Gerät gespeichert, nicht im Abgleich und nicht in der "
                    "Sicherung. Mit Namen steht oben im „Dashboard“ (am Handy: „Start“) "
                    "„Hallo“ und dein Name.")

# Karte in den Optionen (PC und Handy)
OPTIONS_TITLE = "Rundgang und Hilfe"
OPTIONS_SUBTITLE = "Einführung in %d Schritten" % len(TOUR_PAGES)
OPTIONS_TEXT = ("Der Rundgang zeigt die wichtigsten Bereiche und hilft beim Einrichten "
                "(Name, Rahmenplan, Prüfungstermine). Die Hilfe erklärt alles in kurzen "
                "Texten.")
BTN_TOUR = "Rundgang starten"
BTN_HELP = "Hilfe öffnen"


# ============================================================================
#  TEXTE HILFE (PC UND HANDY GLEICH)
# ============================================================================

HELP_TITLE = "Hilfe"
HELP_SUBTITLE = "Kurz erklärt"
HELP_INTRO = ("Kurze Antworten zu den wichtigsten Bereichen. Wähle ein Thema, um es "
              "aufzuklappen. Begriffe in „Anführungszeichen“ stehen genau so in der App.")
SEARCH_KIND = "Hilfe"   # Art der Treffer in der Suche

RELEASE_PAGE_TEXT = "github.com/%s/releases" % REPOSITORY

# "reiter": Hauptpunkte der Navigation, die der Text nennt (PC-Name).
# Am Handy heisst "Dashboard" "Start", die Lernbereiche liegen unter "Lernen"
# (siehe test_rundgang_hilfe.py).
HELP_SECTIONS = [
    {"id": "lernen", "titel": "Lernen mit Karteikarten",
     "reiter": ["Karteikarten", "Dashboard", "Notizblock"],
     "text": ("Unter „Karteikarten“ (am Handy unter „Lernen“) übst du Fachbegriffe und "
              "Grundwissen. Oben wählst du den Fachbereich, zum Beispiel „Alle“ oder "
              "„Netzwerk“, und den Lernmodus:\n"
              "• „Freitext“: eigene Antwort schreiben, dann „Antwort prüfen“\n"
              "• „Multiple Choice“: eine Antwort auswählen\n"
              "• „Aufdecken“: erst überlegen, dann „Lösung aufdecken“ und mit „Gewusst“ "
              "oder „Nicht gewusst“ bewerten\n\n"
              "Was du schon bearbeitet hast, kommt nach einiger Zeit zur Wiederholung. "
              "„Jetzt wiederholen“ im „Dashboard“ (am Handy: „Start“) holt die fälligen "
              "Karten und Fragen. Im „Notizblock“ siehst du, was du noch üben musst.")},
    {"id": "pruefung", "titel": "Prüfung (AP1 und AP2)",
     "reiter": ["Prüfungstrainer", "AP1-Szenarien", "AP2-Szenarien", "Testprojekt",
                "Abschlussprojekt"],
     "text": ("Im „Prüfungstrainer“ übst du Prüfungsfragen mit Erklärung. Schalte oben auf "
              "„Prüfung“, um eine Prüfung nach IHK-Vorbild zu schreiben: AP1 oder einen "
              "der drei Teile der AP2 (Konzeption, Netzwerke, WiSo). Wie in der echten "
              "Prüfung läuft eine feste Zeit. Offene Aufgaben bewertest du nach der "
              "Abgabe selbst anhand der Musterlösung, WiSo wird automatisch ausgewertet. "
              "Danach siehst du Punkte und IHK-Note.\n\n"
              "„AP1-Szenarien“ und „AP2-Szenarien“ sind längere Aufgaben wie in der "
              "Prüfung, mit Musterlösung. Im „Testprojekt“ übst du Kundenaufträge, im "
              "„Abschlussprojekt“ planst du dein eigenes IHK-Projekt vom Antrag bis zum "
              "Fachgespräch. Am Handy findest du alles unter „Lernen“.")},
    {"id": "rechner", "titel": "Rechner (Subnetting, RAID)",
     "reiter": ["Rechner"],
     "text": ("Unter „Rechner“ gibt es drei Rechner: „Subnetting / VLSM“ (IPv4 und IPv6), "
              "„RAID-Kapazität“ und „Bildschirm-Datenvolumen“. Werte eintragen und "
              "„Berechnen“ wählen. „Rechenweg anzeigen“ erklärt, wie man es von Hand "
              "rechnet.\n\n"
              "Oben unter „Trainer“ rechnest du selbst: „IPv4-Subnetz“, „VLSM“, "
              "„Binär/Hex/Dezimal“ und „IPv6 kürzen“, jeweils „Leicht“, „Mittel“ oder "
              "„Schwer“. Trainer-Aufgaben zählen zum Tagesziel.")},
    {"id": "spiel", "titel": "Firma-Spiel",
     "reiter": ["Spiel"],
     "text": ("Im „Spiel“ arbeitest du bei der Bitweiche IT-Service GmbH. Jeder "
              "Arbeitstag bringt Tickets, zum Beispiel PCs zusammenbauen, Fehler suchen "
              "oder Netze planen. Dein Wissensstand im Spiel kommt aus dem, was du mit "
              "Karteikarten und im Prüfungstrainer lernst.\n\n"
              "Mit genug Erspartem und gutem Ansehen kannst du eine eigene Firma gründen, "
              "Leute einstellen und Aufträge annehmen. Es gibt drei Spielstände für "
              "getrennte Durchgänge. Der Lernfortschritt gilt für alle gemeinsam.")},
    {"id": "fortschritt", "titel": "Fortschritt und Rahmenplan",
     "reiter": ["Fortschritt", "Optionen"],
     "text": ("Unter „Fortschritt“ siehst du deine Lernserie, die Ergebnisse deiner "
              "Prüfungen und wie viel du an den letzten Tagen gelernt hast. Die "
              "„Rahmenplan-Abdeckung“ zeigt für jeden Punkt des Ausbildungsrahmenplans, "
              "wie gut du ihn schon kannst. Mit „Jetzt üben“ übst du gezielt einen "
              "Punkt.\n\n"
              "In den „Optionen“ unter „Rahmenplan“ stellst du ein, welche Abschnitte "
              "angezeigt werden, dein aktuelles Lernfeld und die Termine für AP1 und AP2. "
              "Ist „Übungsauswahl nach Rahmenplan gewichten“ an, kommen in den sechs "
              "Monaten vor einem Termin neue Aufgaben zu prüfungsrelevanten Themen etwas "
              "früher dran.")},
    {"id": "sicherung", "titel": "Sicherung und Abgleich",
     "reiter": ["Optionen"],
     "text": ("Dein Lernstand wird auf diesem Gerät gespeichert. In den „Optionen“ unter "
              "„Sicherung“ speicherst du ihn mit „Sicherung erstellen“ als Datei, zum "
              "Beispiel vor einem Gerätewechsel. Mit „Sicherung einspielen“ holst du ihn "
              "zurück, auch auf einem anderen Gerät. Dabei wählst du „Zusammenführen“ "
              "(nur Fehlendes ergänzen) oder „Alles ersetzen“.\n\n"
              "Mit „Abgleich PC und Handy“ haben PC und Handy denselben Lernstand. Wie "
              "du ihn einrichtest, steht im nächsten Thema.")},
    # Ab 0.56 (Nachbesserung): Anleitung hier statt nur in LIESMICH.txt (die
    # es am Handy nicht gibt)
    {"id": "abgleich", "titel": "Abgleich einrichten",
     "reiter": ["Optionen"],
     "text": ("Für den Abgleich brauchst du ein kostenloses Konto bei github.com:\n"
              "1. Lege dort ein neues, privates Repository an, zum Beispiel mit dem "
              "Namen fisi-lernstand.\n"
              "2. Erzeuge einen Zugangsschlüssel: Profilbild > Settings > Developer "
              "settings > Personal access tokens > Fine-grained tokens > Generate new "
              "token. Wähle nur dieses Repository und bei Contents das Recht Read and "
              "write. Kopiere den Schlüssel (beginnt mit github_pat_), GitHub zeigt ihn "
              "nur einmal.\n"
              "3. In den „Optionen“ unter „Abgleich PC und Handy“ trägst du bei "
              "„Repository (Benutzer/Name)“ zum Beispiel deinname/fisi-lernstand und "
              "bei „Zugangsschlüssel (Token)“ den Schlüssel ein und wählst „Speichern und "
              "abgleichen“. Auf dem anderen Gerät genauso.\n\n"
              "Achtung: Auch Löschen wird abgeglichen.")},
    {"id": "update", "titel": "Update",
     "reiter": ["Optionen"],
     "text": ("In den „Optionen“ unter „Updates“ prüft „Nach Updates suchen“, ob es eine "
              "neue Version gibt. Ist „Beim Start automatisch nach Updates suchen“ an, "
              "sucht die App beim Start von selbst.\n\n"
              "Am PC führt „Jetzt aktualisieren“ durch Download und Installation, danach "
              "startet das Programm neu. Am Handy wird die neue Version im Browser "
              "heruntergeladen. Danach die Datei öffnen und „Installieren“ tippen. Dein "
              "Lernstand bleibt erhalten.")},
    {"id": "problem", "titel": "Problem melden",
     "reiter": ["Optionen"],
     "text": ("Wenn etwas nicht klappt: In den „Optionen“ unter „Problem melden“ steht ein "
              "Bericht mit Programmversion, Gerät, Datenordner und Fehlerprotokoll. "
              "Zugangsschlüssel, Passwörter und dein Benutzername in Pfaden werden "
              "entfernt, deine Antworten und Projekttexte stehen nicht darin.\n\n"
              "Speichere den Bericht mit „Als Datei speichern“ (oder „Kopieren“) und gib "
              "ihn an die Person weiter, von der du das Programm hast. Schreib kurz dazu: "
              "Was hast du gemacht, was ist passiert, was hast du erwartet?")},
    # Ab 0.56 (Nachbesserung): kurze Tastaturhilfe (nur PC)
    {"id": "tastatur", "titel": "Bedienung mit der Tastatur (PC)",
     "reiter": [],
     "text": ("Am PC lassen sich die Lernbereiche und die Optionen ohne Maus "
              "bedienen. Die Spielkarte und die Grundrisse im Spiel brauchen noch die "
              "Maus.\n"
              "• Tab springt zum nächsten Element, Umschalt+Tab zurück. Das gewählte "
              "Element hat einen deutlichen Rahmen.\n"
              "• Eingabe oder Leertaste drückt Knöpfe, schaltet Schalter um und klappt "
              "Bereiche auf und zu.\n"
              "• Esc überspringt den Rundgang.\n\n"
              "Die Schrift vergrößerst du in den „Optionen“ unter „Schriftgröße“ mit "
              "„Groß“ oder „Sehr groß“.")},
    {"id": "schutzprogramm", "titel": "Warnung vom Schutzprogramm",
     "reiter": [],
     "text": ("Manche Schutzprogramme und Browser warnen beim Herunterladen oder "
              "Installieren der FISI Lernplattform. Der Grund: Das Programm ist neu, wird "
              "selten heruntergeladen und ist nicht digital signiert.\n\n"
              "Lade die App deshalb nur von der Release-Seite herunter: "
              + RELEASE_PAGE_TEXT + ". Dort steht zu jeder Datei eine Prüfsumme "
              "(SHA-256), mit der du die Datei vergleichen kannst. Schalte den Schutz "
              "nicht dauerhaft ab. Warnt dein Schutzprogramm auch bei der Datei von der "
              "Release-Seite, kannst du den Fehlalarm beim Hersteller des "
              "Schutzprogramms melden.")},
]
HELP_IDS = [section["id"] for section in HELP_SECTIONS]
HELP_BY_ID = {section["id"]: section for section in HELP_SECTIONS}
HELP_BY_TITLE = {section["titel"]: section for section in HELP_SECTIONS}


def search_help(query):
    """Hilfe-Abschnitte, deren Titel oder Text query enthaelt:
    [(id, titel, ausschnitt)]."""
    needle = str(query or "").strip().lower()
    if not needle:
        return []
    hits = []
    for section in HELP_SECTIONS:
        text = section["text"].replace("\n", " ")
        if needle in section["titel"].lower() or needle in text.lower():
            hits.append((section["id"], section["titel"], text))
    return hits
