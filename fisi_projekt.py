#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fachinformatiker Lernplattform - Arbeitsbereich Abschlussprojekt (ab 0.51, ohne Oberflaeche)
=================================================================================

Nicos eigenes IHK-Abschlussprojekt: Texte, Zeitplan, Kosten, Dokumentation,
Fachgespraech und Checklisten. Jedes Feld wird einzeln in der Tabelle
abschlussprojekt gespeichert (neueste Fassung gilt) und mit dem Handy
abgeglichen. Mehrere Projekte sind moeglich, eines ist je Geraet aktiv.

Vorgaben (Konzept_0.51.md, Quellen dort): Projekt hoechstens 40 Stunden
inkl. Dokumentation (§ 20 FIAusbV), Antrag mit Ausgangssituation,
Projektziel und Zeitplanung, Praesentation hoechstens 15 Minuten plus
Fachgespraech (zusammen hoechstens 30). Seitenzahl und Fristen legt die
eigene IHK fest - deshalb einstellbar.
"""

import json
import os
import re
import uuid

from fisi_core import CATEGORY_KEYS, CONTENT_DIR, PROJEKTARBEITEN

MAX_HOURS = 40
DOC_SHARE_MAX = 20          # Prozent der Stunden fuer die Dokumentation (DIHK ca. 20)
CHARS_PER_PAGE = 2800       # grobe Schaetzung fuer 11 pt, 1,5-zeilig mit Ueberschriften
DEFAULT_PAGES = 15

TABS = [("uebersicht", "Übersicht"), ("antrag", "Antrag"), ("zeitplan", "Zeitplan"),
        ("kosten", "Kosten"), ("doku", "Dokumentation"), ("fachgespraech", "Fachgespräch")]

# Felder der Uebersicht
OVERVIEW_FIELDS = [
    ("titel", "Projekttitel", False),
    ("betrieb", "Ausbildungsbetrieb / Auftraggeber", False),
    ("zeitraum", "Durchführungszeitraum", False),
    ("frist_antrag", "Abgabe Projektantrag bis", False),
    ("frist_doku", "Abgabe Dokumentation bis", False),
]

# Projektantrag (IHK Berlin/Koblenz, Konzept Abschnitt 4)
PROPOSAL_FIELDS = [
    ("bezeichnung", "Projektbezeichnung",
     "Kurzer, aussagekräftiger Titel: Was wird für wen gemacht?"),
    ("ausgangssituation", "Ausgangssituation",
     "Ist-Zustand und Problem beim Auftraggeber, warum das Projekt nötig ist."),
    ("ziel", "Projektziel",
     "Sachziel, Kostenziel, Zeitziel und Qualitätsziel - möglichst messbar."),
    ("umfeld", "Auftraggeber und Projektumfeld",
     "Wer beauftragt, wer ist beteiligt, Schnittstellen, Rahmenbedingungen."),
    ("alternativen", "Lösungsalternativen",
     "Mindestens zwei Möglichkeiten und nach welchen Kriterien entschieden wird."),
    ("systeme", "Technische Systeme und Ressourcen",
     "Hard- und Software, Netz, Werkzeuge, Personal."),
    ("einfuehrung", "Einführung und Pflege",
     "Übergabe, Einweisung, Betrieb und Wartung nach dem Projekt."),
    ("sicherheit", "IT-Sicherheit und Datenschutz",
     "Schutzbedarf, Schwachstellen, geplante Maßnahmen."),
    ("praesentationsmittel", "Dokumentation und Präsentationsmittel",
     "Welche Unterlagen entstehen, womit wird präsentiert."),
]

# Zeitplan: feste Phasen plus zwei freie
PHASES = [
    ("analyse", "Analyse (Ist-Aufnahme, Anforderungen)", 5),
    ("planung", "Planung und Entwurf (Soll-Konzept, Wirtschaftlichkeit)", 7),
    ("durchfuehrung", "Durchführung / Umsetzung", 14),
    ("test", "Test und Qualitätssicherung", 4),
    ("uebergabe", "Übergabe, Einweisung, Abnahme", 2),
    ("dokumentation", "Dokumentation", 8),
    ("frei1", "", 0),
    ("frei2", "", 0),
]

# Kostenrechnung
COST_FIELDS = [
    ("satz_azubi", "Stundensatz Auszubildende/r (EUR)", "25"),
    ("satz_ma", "Stundensatz Mitarbeiter/in (EUR)", "60"),
    ("stunden_ma", "Stunden Mitarbeiter/in (Abnahme, Einweisung)", "4"),
    ("einsparung", "Einsparung pro Monat (EUR)", "0"),
    ("laufend", "Laufende Kosten pro Monat (EUR)", "0"),
]
MATERIAL_ROWS = 5

# Dokumentation: Kapitelgeruest
CHAPTERS = [
    ("einleitung", "1. Einleitung",
     "Projektumfeld, Projektziel, Projektbegründung, Projektschnittstellen, Abgrenzung."),
    ("ist", "2. Ist-Analyse",
     "Bestandsaufnahme und Schwachstellen."),
    ("soll", "3. Soll-Konzept und Lösungsauswahl",
     "Anforderungen, Alternativen, Entscheidung (z.B. Nutzwertanalyse)."),
    ("wirtschaft", "4. Wirtschaftlichkeit",
     "Projektkosten, Make-or-Buy, Amortisation."),
    ("durchfuehrung", "5. Durchführung",
     "Umsetzung Schritt für Schritt, Abweichungen vom Plan."),
    ("test", "6. Test und Qualitätssicherung",
     "Testfälle, Testergebnisse, Abnahme."),
    ("uebergabe", "7. Übergabe und Einführung",
     "Einweisung, Dokumentation für Anwender und Administration."),
    ("fazit", "8. Fazit und Ausblick",
     "Soll-Ist-Vergleich, Lessons Learned, Ausblick."),
]

CHECKLIST_OVERVIEW = [
    ("antrag_entwurf", "Projektantrag geschrieben"),
    ("antrag_betrieb", "Antrag vom Ausbildungsbetrieb geprüft"),
    ("antrag_eingereicht", "Antrag bei der IHK eingereicht"),
    ("antrag_genehmigt", "Antrag genehmigt"),
    ("durchgefuehrt", "Projekt durchgeführt"),
    ("doku_fertig", "Dokumentation fertig und korrekturgelesen"),
    ("doku_abgegeben", "Dokumentation abgegeben"),
    ("praesentation", "Präsentation erstellt (höchstens 15 Minuten)"),
    ("geprobt", "Präsentation mit Zeitmessung geprobt"),
    ("fachgespraech", "Fachgespräch geübt"),
]
CHECKLIST_PROPOSAL = [
    ("phasen", "Zeitplan in Phasen mit Stunden"),
    ("max40", "Summe höchstens 40 Stunden inklusive Dokumentation"),
    ("eigenleistung", "Eigene Leistung klar erkennbar"),
    ("messbar", "Projektziel messbar beschrieben"),
    ("ki", "Einsatz von KI-Hilfsmitteln gekennzeichnet (falls die IHK das verlangt)"),
]
CHECKLIST_PRESENTATION = [
    ("p_dauer", "Dauer 12 bis 15 Minuten"),
    ("p_gliederung", "Gliederung: Ausgangslage, Ziel, Vorgehen, Ergebnis, Fazit"),
    ("p_wirtschaft", "Wirtschaftlichkeit kurz dargestellt"),
    ("p_folien", "Folien gut lesbar, wenig Text"),
    ("p_technik", "Technik und Ersatz (USB-Stick, PDF) vorbereitet"),
]

ESTIMATE_FIELD = "schaetzung"    # geschaetzte Punkte (0-100) fuers Gesamtergebnis
PAGES_FIELD = "seitenziel"
TITLE_FIELD = "titel"
DELETED_FIELD = "_geloescht"
ACTIVE_KEY = "aktives_projekt"   # in einstellungen.json, je Geraet


def _load_questions():
    path = os.path.join(CONTENT_DIR, "fachgespraech.json")
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    for item in data["fragen"]:
        item["cat"] = CATEGORY_KEYS.get(item["cat"]) if item["cat"] else None
    return data["fragen"]


QUESTIONS = _load_questions()


# ============================================================================
#  PROJEKTE
# ============================================================================

def new_project_id():
    return uuid.uuid4().hex[:12]


def projects(db):
    """{projekt_id: felder} ohne geloeschte Projekte."""
    return {key: fields for key, fields in db.project_fields().items()
            if fields.get(DELETED_FIELD) != "1"}


def project_title(fields):
    return (fields.get(TITLE_FIELD) or "").strip() or "Projekt ohne Titel"


def create_project(db, title=""):
    project = new_project_id()
    db.save_project_field(project, TITLE_FIELD, title)
    return project


def delete_project(db, project):
    return db.save_project_field(project, DELETED_FIELD, "1")


def active_project(db, settings):
    """Aktives Projekt dieses Geraets; sonst das erste vorhandene. Gibt es
    noch keins, eine neue Kennung - gespeichert wird das Projekt erst mit
    der ersten Eingabe (sonst laege nach jedem Start ein leeres Projekt im
    Abgleich)."""
    existing = projects(db)
    active = settings.get(ACTIVE_KEY)
    if active in existing:
        return active
    if existing:
        return sorted(existing)[0]
    return new_project_id()


def apply_template(db, project, position):
    """Uebernimmt ein Testprojekt als Anregung in den Antrag (nur leere
    Felder werden gefuellt). Liefert die Anzahl gefuellter Felder."""
    template = PROJEKTARBEITEN[position]
    fields = projects(db).get(project, {})
    values = {
        TITLE_FIELD: template["title"],
        "bezeichnung": template["title"],
        "betrieb": template.get("branche", ""),
        "ausgangssituation": template.get("ausgangssituation", ""),
        "ziel": template.get("auftrag", ""),
        "umfeld": "\n".join("- " + rule for rule in template.get("rahmenbedingungen", [])),
        "fachbereich": template.get("cat", ""),
    }
    count = 0
    for field, value in values.items():
        if value and not (fields.get(field) or "").strip():
            db.save_project_field(project, field, value)
            count += 1
    return count


# ============================================================================
#  BERECHNUNGEN
# ============================================================================

def to_number(text, default=0.0):
    """Zahl aus einer Eingabe wie "25", "25,5" oder "1.234,56"."""
    value = str(text if text is not None else "").strip().replace("€", "").replace(" ", "")
    if "," in value:
        value = value.replace(".", "").replace(",", ".")
    try:
        return float(value) if value else default
    except ValueError:
        return default


def euro(value):
    text = "{:,.2f}".format(value).replace(",", "X").replace(".", ",").replace("X", ".")
    return text + " €"


def hours_text(value):
    return ("%.1f" % value).replace(".", ",").replace(",0", "") + " Std."


def schedule(fields):
    """[(schluessel, name, stunden)] und Summe; Standardwerte, solange leer."""
    rows = []
    for key, name, default in PHASES:
        label = fields.get("phase_name_" + key, name) if key.startswith("frei") else name
        raw = fields.get("phase_" + key)
        hours = to_number(raw, default if raw is None else 0.0)
        rows.append((key, label, hours))
    total = sum(hours for _key, label, hours in rows if label or hours)
    return rows, total


def schedule_warnings(fields):
    rows, total = schedule(fields)
    notes = []
    if total > MAX_HOURS:
        notes.append("Die Summe von %s liegt über den erlaubten %d Stunden."
                     % (hours_text(total), MAX_HOURS))
    doc = dict((key, hours) for key, _n, hours in rows).get("dokumentation", 0)
    if total and doc / total * 100 > DOC_SHARE_MAX:
        notes.append("Die Dokumentation nimmt %d %% der Zeit ein (üblich höchstens "
                     "15 bis 20 %%)." % round(doc / total * 100))
    return notes


def costs(fields):
    """Kostenrechnung als dict (alle Werte in EUR bzw. Monaten)."""
    def value(key):
        default = dict((k, d) for k, _l, d in COST_FIELDS)[key]
        raw = fields.get("kosten_" + key)
        return to_number(default if raw is None else raw)
    _rows, hours = schedule(fields)
    staff = hours * value("satz_azubi") + value("stunden_ma") * value("satz_ma")
    material = []
    for number in range(MATERIAL_ROWS):
        name = (fields.get("material_name_%d" % number) or "").strip()
        amount = to_number(fields.get("material_betrag_%d" % number))
        if name or amount:
            material.append((name or "Position %d" % (number + 1), amount))
    material_sum = sum(amount for _name, amount in material)
    total = staff + material_sum
    net = value("einsparung") - value("laufend")
    months = total / net if net > 0 else None
    return {"stunden": hours, "personal": staff, "material": material,
            "material_summe": material_sum, "gesamt": total, "netto_monat": net,
            "amortisation": months}


def cost_lines(fields):
    data = costs(fields)
    lines = ["Projektstunden laut Zeitplan: %s" % hours_text(data["stunden"]),
             "Personalkosten: %s" % euro(data["personal"]),
             "Sachkosten: %s" % euro(data["material_summe"]),
             "Projektkosten gesamt: %s" % euro(data["gesamt"])]
    if data["amortisation"] is None:
        lines.append("Amortisation: keine Einsparung eingetragen")
    else:
        lines.append("Amortisation nach %s Monaten (%s Einsparung netto pro Monat)"
                     % (("%.1f" % data["amortisation"]).replace(".", ","),
                        euro(data["netto_monat"])))
    return lines


def page_estimate(fields):
    """(geschaetzte Seiten, Seitenziel) der Dokumentation."""
    chars = sum(len(fields.get("kapitel_" + key, "") or "") for key, _t, _h in CHAPTERS)
    target = int(to_number(fields.get(PAGES_FIELD), DEFAULT_PAGES)) or DEFAULT_PAGES
    return chars / float(CHARS_PER_PAGE), target


def checked(fields, key):
    return fields.get("check_" + key) == "1"


def overview_progress(fields):
    done = sum(1 for key, _text in CHECKLIST_OVERVIEW if checked(fields, key))
    return done, len(CHECKLIST_OVERVIEW)


def proposal_missing(fields):
    """Namen der noch leeren Antragsfelder."""
    return [name for key, name, _hint in PROPOSAL_FIELDS if not (fields.get(key) or "").strip()]


def estimate(fields):
    """Geschaetzte Projektpunkte (0-100) oder None."""
    raw = (fields.get(ESTIMATE_FIELD) or "").strip()
    if not raw:
        return None
    return max(0.0, min(100.0, to_number(raw)))


def questions_for(fields):
    """Fragen fuers Fachgespraech: allgemeine plus die des Fachbereichs."""
    category = fields.get("fachbereich") or None
    return [q for q in QUESTIONS if q["cat"] is None or q["cat"] == category]


def question_rating(fields, question_id):
    """True (gewusst), False (nicht gewusst) oder None."""
    value = fields.get("fg_" + question_id)
    return None if value in (None, "") else value == "1"


# ============================================================================
#  EXPORT
# ============================================================================

def export_blocks(fields):
    """Inhalt fuer Text- und PDF-Export: [(art, text)]."""
    blocks = [("h1", project_title(fields))]
    info = [(label, fields.get(key, "")) for key, label, _m in OVERVIEW_FIELDS[1:]]
    for label, value in info:
        if (value or "").strip():
            blocks.append(("p", "%s: %s" % (label, value.strip())))
    blocks.append(("h2", "Projektantrag"))
    for key, name, _hint in PROPOSAL_FIELDS:
        blocks.append(("h3", name))
        blocks.append(("p", (fields.get(key) or "").strip() or "(noch offen)"))
    blocks.append(("h2", "Zeitplanung"))
    rows, total = schedule(fields)
    for _key, name, hours in rows:
        if name or hours:
            blocks.append(("li", "%s: %s" % (name or "Weitere Phase", hours_text(hours))))
    blocks.append(("p", "Summe: %s (höchstens %d Stunden)" % (hours_text(total), MAX_HOURS)))
    blocks.append(("h2", "Kostenrechnung"))
    data = costs(fields)
    for name, amount in data["material"]:
        blocks.append(("li", "%s: %s" % (name, euro(amount))))
    for line in cost_lines(fields):
        blocks.append(("p", line))
    blocks.append(("h2", "Dokumentation"))
    for key, title, _hint in CHAPTERS:
        blocks.append(("h3", title))
        blocks.append(("p", (fields.get("kapitel_" + key) or "").strip() or "(noch offen)"))
    blocks.append(("h2", "Checkliste"))
    for key, text in CHECKLIST_OVERVIEW + CHECKLIST_PROPOSAL + CHECKLIST_PRESENTATION:
        blocks.append(("li", "[%s] %s" % ("x" if checked(fields, key) else " ", text)))
    return blocks


def export_text(fields):
    lines = []
    for kind, text in export_blocks(fields):
        if kind == "h1":
            lines += [text, "=" * len(text), ""]
        elif kind == "h2":
            lines += ["", text, "-" * len(text)]
        elif kind == "h3":
            lines += ["", text]
        elif kind == "li":
            lines.append("  - " + text)
        else:
            lines.append(text)
    return "\n".join(lines).strip() + "\n"


def export_pdf(fields):
    from fisi_pdf import build_pdf
    return build_pdf(export_blocks(fields), title=project_title(fields))


def export_name(fields, extension):
    base = re.sub(r"[^A-Za-z0-9ÄÖÜäöüß_-]+", "_", project_title(fields)).strip("_")
    return "Abschlussprojekt_%s.%s" % (base[:40] or "Projekt", extension)
