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

Silbentrennung (trennstellen), Weisung zu Meldung 42, Fragen 11-13: nur die
von Chat bestaetigte Liste (Meldung 42 Anhang A, WOERTER unten) - kein
Silbenalgorithmus. Ein Wort der Liste (gross/klein gleich, Satzzeichen am
Rand wie ":" oder ")" bleiben am Wort) bekommt genau seine Stellen; jedes
andere Wort nur die Stellen nach einem vorhandenen Bindestrich. Links und
rechts jeder Stelle stehen mindestens 2 Buchstaben (Frage 12), ein einzelner
Vokal in der Wortmitte ist zulaessig (Frage 13). Bevorzugte Stellen
(Wortfuge, vorhandener Bindestrich) werden zuerst genommen, die uebrigen nur,
wenn keine bevorzugte passt. Zahlen, Adressen und Abkuerzungen ("nie
trennen") haben keine Stelle; ein Wort ohne passende Stelle wird wie bisher
an der letzten passenden Stelle ohne Trennstrich geteilt (dasselbe, was Tk
und Flutter heute tun) - die Nummer bleibt trotzdem beim Wort.
"""

import re

# Nummer am Titelanfang ("4.", "12.") - bleibt beim ersten Wort
NUMMER = re.compile(r"^\d+\.$")
# geschuetztes Leerzeichen (Handy: Flutter bricht dort nicht um)
GESCHUETZT = " "
TRENNSTRICH = "-"


# Ab 0.63.2 (Weisung zu Meldung 42, Frage 11 (b)): die bestaetigte Liste.
# "‖" bevorzugte Stelle (Wortfuge oder vorhandener Bindestrich), "|" weitere
# zulaessige Stelle (Silbengrenze). Neue Woerter kommen hier dazu.
WOERTER = (
    "Wirt|schaft|lich|keits‖be|trach|tung",
    "Wirt|schaft|lich|keits‖ver|gleich",
    "Mehr‖fak|tor-‖Au|then|ti|fi|zie|rung",
    "PRÜ|FUNGS‖TRAI|NER",
    "AN‖PAS|SUN|GEN",
    "Da|ten‖si|che|rungs‖kon|zep|te",
    "Hoch‖ver|füg|bar|keit",
    "Kun|den‖zu|frie|den|heit",
    "IPv6-‖Adres|se",
    "Netz‖werk‖in|fra|struk|tur",
    "Ab|schluss‖pro|jekt",
    "Schwie|rig|keits‖grad",
    "Broad|cast-‖Adres|se",
    "Prä|fix‖län|ge",
    "Wild|card-‖Mas|ke",
    "Punkt-‖zu-‖Punkt-‖Ver|bin|dun|gen",
    "Vir|tu|a|li|sie|rung",
    "Da|ten‖schutz-‖Grund‖ver|ord|nung",
    "Ver|schlüs|se|lung",
    "Nutz‖wert‖ana|ly|se",
    "AP2-‖Pro|jekt‖do|ku|men|ta|ti|on",
    "Amor|ti|sa|ti|ons‖rech|nung",
    "Über|tra|gungs‖ge|schwin|dig|keit",
    "Un|ter|bre|chungs‖freie",
    "UND-‖Ver|knüp|fung",
    "Sub‖netz‖mas|ke",
    "Not|fall‖wie|der‖her|stel|lung",
    "In|ves|ti|ti|ons‖ent|schei|dung",
    "Da|ten‖schutz‖kon|for|me",
    "Do|ku|men|ten‖ma|nage|ment‖sys|tem",
    "Schwach|stel|len‖ma|nage|ment",
    "Netz‖werk‖kom|po|nen|ten",
    "Re|mote‖desk|top‖diens|te-‖Farm",
)
BEVORZUGT, WEITERE = "‖", "|"
MINDESTENS = 2   # Buchstaben links und rechts jeder Stelle (Frage 12)


def _liste(eintraege):
    """{wort.lower(): (alle Stellen, bevorzugte Stellen)} aus der Liste."""
    liste = {}
    for eintrag in eintraege:
        wort, alle, bevorzugt = "", [], []
        for zeichen in eintrag:
            if zeichen in (BEVORZUGT, WEITERE):
                alle.append(len(wort))
                if zeichen == BEVORZUGT:
                    bevorzugt.append(len(wort))
            else:
                wort += zeichen
        liste[wort.lower()] = (tuple(alle), tuple(bevorzugt))
    return liste


_LISTE = _liste(WOERTER)


def _kern(wort):
    """(anfang, ende) des Wortes ohne Satzzeichen am Rand ("Titel:" ->
    "Titel", "(Wort)" -> "Wort")."""
    anfang, ende = 0, len(wort)
    while anfang < ende and not wort[anfang].isalnum():
        anfang += 1
    while ende > anfang and not wort[ende - 1].isalnum():
        ende -= 1
    return anfang, ende


def _genug(wort, stelle):
    """Mindestens MINDESTENS Buchstaben links und rechts der Stelle."""
    return (sum(z.isalpha() for z in wort[:stelle]) >= MINDESTENS and
            sum(z.isalpha() for z in wort[stelle:]) >= MINDESTENS)


def _stellen(wort):
    """(alle, bevorzugte) Stellen in wort, Positionen p: wort[:p] | wort[p:]."""
    anfang, ende = _kern(wort)
    eintrag = _LISTE.get(wort[anfang:ende].lower())
    if eintrag is not None:
        alle = [anfang + p for p in eintrag[0]]
        bevorzugt = [anfang + p for p in eintrag[1]]
    else:
        # nicht in der Liste: nur nach einem vorhandenen Bindestrich
        alle = [i + 1 for i in range(anfang, ende - 1) if wort[i] == TRENNSTRICH]
        bevorzugt = alle
    alle = [p for p in alle if _genug(wort, p)]
    return alle, [p for p in bevorzugt if p in alle]


def trennstellen(wort):
    """Alle zulaessigen Trennstellen in wort (sortiert)."""
    return _stellen(wort)[0]


def bevorzugte_stellen(wort):
    """Die bevorzugten Trennstellen in wort (Wortfuge, vorhandener
    Bindestrich); sie werden zuerst genommen."""
    return _stellen(wort)[1]


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


def _passend(einheit, start, stellen, breite, messen):
    """Die hinterste Stelle nach start, deren Stueck (mit Trennstrich, an
    einem vorhandenen Bindestrich ohne zweiten) in breite passt."""
    for stelle in reversed(stellen):
        if stelle <= start:
            break
        stueck = einheit[start:stelle]
        if not stueck.endswith(TRENNSTRICH):
            stueck += TRENNSTRICH
        if messen(stueck) <= breite:
            return stelle, stueck
    return None


def _teilen(einheit, praefix, breite, messen, stellen_von, bevorzugt_von):
    """Teilt eine zu lange Einheit in Stuecke, die je in breite passen.
    Bevorzugte Stellen zuerst, die uebrigen nur, wenn keine bevorzugte passt.
    Liefert (stuecke, mit_ersatz): mit_ersatz = True, wenn ein Stueck ohne
    zulaessige Stelle geteilt werden musste (Rueckfall wie bisher)."""
    wort = einheit[praefix:]
    stellen = sorted(set(p + praefix for p in stellen_von(wort)))
    bevorzugt = sorted(set(p + praefix for p in bevorzugt_von(wort)) & set(stellen))
    stuecke, start, ersatz = [], 0, False
    while messen(einheit[start:]) > breite:
        gewaehlt = (_passend(einheit, start, bevorzugt, breite, messen) or
                    _passend(einheit, start, stellen, breite, messen))
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


def zeilen(text, breite, messen, stellen_von=trennstellen,
           bevorzugt_von=bevorzugte_stellen):
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
        stuecke, _ersatz = _teilen(einheit, praefix, breite, messen, stellen_von,
                                   bevorzugt_von)
        geteilt = True
        ergebnis.extend(stuecke[:-1])
        zeile = stuecke[-1]
    if zeile or not ergebnis:
        ergebnis.append(zeile)
    return ergebnis, geteilt


def anzeige_text(text, breite, messen, stellen_von=trennstellen,
                 bevorzugt_von=bevorzugte_stellen):
    """Text fuer die Anzeige: unveraendert, wenn der gewoehnliche Umbruch an
    Leerzeichen reicht (kein Wort zu lang, keine Nummer allein); sonst die
    Zeilen der Regel, mit Zeilenumbruch verbunden."""
    stuecke, geteilt = zeilen(text, breite, messen, stellen_von, bevorzugt_von)
    if not geteilt:
        return text
    return "\n".join(stuecke)


def nummer_titel(nummer, titel, rest=""):
    """"4. Titel" mit geschuetztem Leerzeichen nach der Nummer (Handy:
    Flutter bricht dort nicht um, die Nummer bleibt beim Titel)."""
    return "%d.%s%s%s" % (nummer, GESCHUETZT, titel, rest)
