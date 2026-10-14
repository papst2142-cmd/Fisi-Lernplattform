# -*- coding: utf-8 -*-
"""
Zeilenumbruch fuer kurze Titel (PC und Handy gleich), ab 0.63.2
=================================================================

Plan-Nachtrag 0.63.2 Nr. 20 (B-D-06), Weisung zu Meldung 38/40 B3 (a): eine
Regel fuer PC und Handy in einem eigenen, ungeschuetzten Modul (Handy:
mobile/vorbereiten.py SHARED_FILES). Die Breite misst der Aufrufer
(messen(text) -> Pixel; am PC die Tk-Schrift, am Handy eine Schaetzung je
Zeichen wie FitBox), die Regel selbst rechnet nicht mit Pixeln.

Was die Regel tut:
  * Woerter werden wie bisher an Leerzeichen umbrochen (gierig, wie Tk und
    Flutter).
  * Ein Wort, das allein nicht in eine Zeile passt, wird geteilt - zuerst
    nach einem vorhandenen Bindestrich ("Mehrfaktor-" / "Authentifizierung"),
    sonst an einer zulaessigen Trennstelle mit Trennstrich (trennstellen()).
  * Eine Nummer wie "4." bleibt beim ersten Wort des Titels (nie allein).
  * Passt der Titel ohne Wortteilung und ohne abgetrennte Nummer, bleibt der
    angezeigte Text unveraendert (anzeige_text(): keine Trennung "auf
    Vorrat").

Silbentrennung (trennstellen): Die Erwartungsliste mit den zulaessigen
Trennstellen legt der Bauer N8 Chat vor (Weisung 38/40, N8-F2); bis Chat sie
bestaetigt, ist die Silbenregel NICHT gebaut: trennstellen() liefert nur die
Stellen nach einem vorhandenen Bindestrich. Ein Wort ohne solche Stelle wird
dann wie bisher an der letzten passenden Stelle ohne Trennstrich geteilt
(dasselbe, was Tk und Flutter heute tun) - die Nummer bleibt trotzdem beim
Wort.
"""

import re

# Nummer am Titelanfang ("4.", "12.") - bleibt beim ersten Wort
NUMMER = re.compile(r"^\d+\.$")
# geschuetztes Leerzeichen (Handy: Flutter bricht dort nicht um)
GESCHUETZT = " "
TRENNSTRICH = "-"


def trennstellen(wort):
    """Zulaessige Trennstellen in wort (Positionen p: wort[:p] | wort[p:]).

    Bis zur Bestaetigung der Erwartungsliste durch Chat (N8-F2) nur die
    Stellen direkt nach einem vorhandenen Bindestrich ("Mehrfaktor-|...").
    Keine Stelle am Wortanfang oder -ende."""
    return [i + 1 for i, zeichen in enumerate(wort)
            if zeichen == TRENNSTRICH and 0 < i < len(wort) - 1]


def _einheiten(text):
    """Woerter des Titels; eine Nummer ("4.") wird mit dem folgenden Wort zu
    einer Einheit verbunden. Liefert [(einheit, laenge_des_praefixes)]."""
    woerter = text.split(" ")
    einheiten = []
    index = 0
    while index < len(woerter):
        wort = woerter[index]
        if NUMMER.match(wort) and index + 1 < len(woerter) and woerter[index + 1]:
            praefix = wort + " "
            einheiten.append((praefix + woerter[index + 1], len(praefix)))
            index += 2
            continue
        einheiten.append((wort, 0))
        index += 1
    return einheiten


def _teilen(einheit, praefix, breite, messen, stellen_von):
    """Teilt eine zu lange Einheit in Stuecke, die je in breite passen.
    Liefert (stuecke, mit_ersatz): mit_ersatz = True, wenn ein Stueck ohne
    zulaessige Stelle geteilt werden musste (Rueckfall wie bisher)."""
    wort = einheit[praefix:]
    stellen = sorted(set(p + praefix for p in stellen_von(wort)))
    stuecke, start, ersatz = [], 0, False
    while messen(einheit[start:]) > breite:
        gewaehlt = None
        for stelle in reversed(stellen):
            if stelle <= start:
                break
            stueck = einheit[start:stelle]
            if not stueck.endswith(TRENNSTRICH):
                stueck += TRENNSTRICH
            if messen(stueck) <= breite:
                gewaehlt = (stelle, stueck)
                break
        if gewaehlt is None:
            # Rueckfall: an der letzten passenden Stelle ohne Trennstrich
            # (wie Tk/Flutter bisher), mindestens ein Zeichen - die Nummer
            # bleibt dabei beim Wort
            ersatz = True
            stelle = start + 1
            while stelle < len(einheit) and messen(einheit[start:stelle + 1]) <= breite:
                stelle += 1
            if start < praefix and stelle <= praefix:
                stelle = min(len(einheit), praefix + 1)
            gewaehlt = (stelle, einheit[start:stelle])
        stelle, stueck = gewaehlt
        stuecke.append(stueck)
        start = stelle
    stuecke.append(einheit[start:])
    return stuecke, ersatz


def zeilen(text, breite, messen, stellen_von=trennstellen):
    """Teilt text in Zeilen, die je hoechstens breite breit sind (messen).
    Liefert (zeilen, geteilt): geteilt = True, wenn ein Wort geteilt oder
    eine Nummer beim Wort gehalten werden musste (der Text weicht dann vom
    gewoehnlichen Umbruch an Leerzeichen ab)."""
    ergebnis, zeile, geteilt = [], "", False
    for einheit, praefix in _einheiten(text):
        kandidat = einheit if not zeile else zeile + " " + einheit
        if messen(kandidat) <= breite:
            zeile = kandidat
            continue
        if zeile:
            ergebnis.append(zeile)
            zeile = ""
        if messen(einheit) <= breite:
            zeile = einheit
            continue
        stuecke, _ersatz = _teilen(einheit, praefix, breite, messen, stellen_von)
        geteilt = True
        ergebnis.extend(stuecke[:-1])
        zeile = stuecke[-1]
    if zeile or not ergebnis:
        ergebnis.append(zeile)
    return ergebnis, geteilt


def anzeige_text(text, breite, messen, stellen_von=trennstellen):
    """Text fuer die Anzeige: unveraendert, wenn der gewoehnliche Umbruch an
    Leerzeichen reicht (kein Wort zu lang, keine Nummer allein); sonst die
    Zeilen der Regel, mit Zeilenumbruch verbunden."""
    stuecke, geteilt = zeilen(text, breite, messen, stellen_von)
    if not geteilt:
        return text
    return "\n".join(stuecke)


def nummer_titel(nummer, titel, rest=""):
    """"4. Titel" mit geschuetztem Leerzeichen nach der Nummer (Handy:
    Flutter bricht dort nicht um, die Nummer bleibt beim Titel)."""
    return "%d.%s%s%s" % (nummer, GESCHUETZT, titel, rest)
