# Gegenprüfung 2 zu Meldung 45 (Fassung 1), Sicht des Lesers Chat

Prüfer: unabhängiger Gegenprüfer 2, 14.10.2026, nach 16:15 UTC. Geprüft wurde `bau_0.63.2/meldungen/Meldung_45_Stand_und_Fragen.md` (524 Zeilen). An der Meldung wurde nichts geändert, nichts committet, keine Tests gestartet.
Schwerpunkt: ob die Fragen entscheidbar und regelkonform sind, ob „belegt“ und „berichtet“ richtig getrennt sind, ob Nicos Entscheidungen richtig wiedergegeben werden, ob Merge-Reihenfolge und Merge-Stand stimmen, und was kürzer gehen kann. Die Zahlenprüfung macht Prüfer 1.

**Selbst nachgesehen (belegt):**
- `git ls-remote origin`: `version-0632` = `a82fd34`. S6a `6ffda17`, S6b `cb60f8b`, fg113 `93bc9ce`, fg109 `cbbbad1`, fg114 `5c6087d`, n7-fg `a551440`, n9 `5185e78`, n14 `6330eb4` und s1c2 `3411ce9` stimmen mit Z. 59 überein. **`meldungen` = `83b9320`, nicht `8aaadec`.**
- `git log origin/meldungen`: `83b9320` „N9xN3 Aufloesung (3 Diffs), sha256 FG-114-Antrag nachgetragen“ liegt nach `8aaadec`.
- `SHA256SUMS.txt` auf `83b9320` hat 14 Zeilen, darunter die drei N9×N3-Diffs und der FG-114-Antrag.
- `git merge-base --is-ancestor`: N12 `180789b` ist **nicht** in `a82fd34`; N3 `b0e75bc` und S6c `829bc45` sind darin.
- Gelesen: Weisung 44 mit Nachtrag, REGELN_BAU, die vier Nico-Abschriften und die Ergebnisse `fg113`, `fg114`, `fg109`, `n14`, `n7/fg107_fg110`, `n7/gp_fg107_fg110`, `s1c2/nachbesserung`, `integration/n9_konflikt/optionen_5185e78.md` sowie die betreffenden Zeilen in `OFFEN_FUER_BERICHT.md`.

---

## Befunde

### Hoch

**H1: Regel-A-Stand veraltet. B.1 und die Selbstkontrolle nennen den falschen `meldungen`-Kopf und eine unvollständige Anlagenliste (Z. 27, 60, 94, 274–289, 129)**
- Beleg: `origin/meldungen` = `83b9320`. Darin stehen die drei N9×N3-Diffs, und `SHA256SUMS.txt` enthält jetzt auch `FG-114_Antrag…md` (`a6e007b6…`).
- Die Meldung sagt dagegen:
  - Z. 274: „Kopf `8aaadec`“.
  - Z. 288: der Antrag sei „nicht in `SHA256SUMS.txt`“. Das ist jetzt falsch.
  - Z. 60: „zehn Anlagen und der FG-114-Antrag“. Richtig sind 13 Diffs und der Antrag.
  - In der Tabelle B.1 fehlen die drei N9×N3-Diffs. Sie stehen nur in einem rohen, eingeschobenen Satz in Frage 2 (Z. 129).
- Warum hoch: Chat liest nach Regel A nur `meldungen` und prüft mit `sha256sum -c`. Ein falscher Kopf oder eine Lücke in der Liste macht die Merge-Freigabe für N9 (Frage 2) formal unvollständig.
- Korrektur:
  - B.1-Kopf auf `83b9320` setzen (vor dem Versand noch einmal per `ls-remote` prüfen).
  - Die drei N9×N3-Diffs als Zeilen in die B.1-Tabelle aufnehmen (Commit `83b9320`, „Frage 2“).
  - Den Vermerk „nicht in SHA256SUMS.txt“ streichen.
  - Z. 27 und 60 auf „13 Diffs und 1 Antrag, alle in `SHA256SUMS.txt` (`83b9320`)“ ändern.
  - Z. 129 durch einen Verweis auf B.1 ersetzen.

**H2: Frage 2 verschweigt, dass Option (A) eine nicht freigegebene Fassung der geschützten Datei `mobile/src/spiel.py` bedeutet und die Optik-Abnahme von Nico berührt (Z. 103–133)**
- Beleg:
  - REGELN Z. 18: `spiel.py` ist geschützt, Änderungen nur an freigegebenen Stellen.
  - Nachtrag W44, Abschnitt 1: „Weicht der gebaute Diff ab (andere sha), kommt der neue Diff wieder auf meldungen/anlagen/, und der Merge wartet.“
  - Die Auflösung ändert `spiel.py` um +66/−35 gegen `a82fd34`. Weder FG-106 noch FG-111 deckt diese Fassung byte-gleich ab.
  - Nicos Abnahme von 14:59 UTC galt den Fotos auf `5185e78`, also ohne N3. Mit (A) sehen Mitarbeiter- und Kreditzeile bis „Sehr groß“ anders aus als auf diesen Fotos (N3-Reihe in Textbreite statt N9-Reihe gleich breit mit `expand`).
- Die Meldung sagt nur „nicht mehr byte-gleich“ (Z. 117) und „prüft andere Eigenschaften, aber nicht weniger“ (Z. 131). Sie sagt nicht:
  - dass die Datei geschützt ist und Chat mit (A) die FG-111-Stelle neu freigibt (neue Stoppgrenze);
  - dass (A) unter 160 % das N9-Verhalten „gleich breit/`expand`“ an zwei Stellen aufgibt, also auch einen Teil von FG-106.
- Korrektur: Im Problem oder bei (A) ergänzen:
  - „`spiel.py` ist geschützt. Mit (A) gibst du die Auflösung als neue Fassung der FG-111-Kreditstelle frei (Stoppgrenze: die drei Diffs mit numstat).“
  - „Unter 160 % gilt an Mitarbeiter und Kredit dann die N3-Reihe statt der N9-Reihe.“
  - Bei den Auflagen ergänzen, an wen die Fotos gehen. Vorschlag: zur Kenntnis an Nico, weil sich das abgenommene Bild unter 160 % ändert.
  - Die Bewertung „nicht weniger“ als Einschätzung kennzeichnen.

### Mittel

**M1: Zu viele Platzhalter, und Pflichtpunkte aus Weisung 44, Abschnitt 7 sind offen (Z. 4, 6, 10, 34, 47, 322, 431, 437, 507, 523)**
- Z. 6 spricht von „drei Platzhaltern“. Es gibt aber vier verschiedene, an acht Stellen:
  - MERGE-STAND FG-113, dreimal (Z. 10, 322, 431);
  - DIAGNOSE LoadingHintTest, zweimal (Z. 34, 507);
  - TOR N6, zweimal (Z. 47, 437);
  - COMMIT, einmal (Z. 523).
- Die Diagnose (W44, 2.2) und das Tor N6 sind ausdrücklich verlangt. Bleiben sie leer, fehlt Chat ein Pflichtteil.
- Z. 4 trägt noch „Fassung 1 (Entwurf, noch nicht gegengeprüft)“.
- Korrektur:
  - Z. 6 auf „vier Platzhalter an acht Stellen“ ändern.
  - Vor dem Versand per `grep '\['` prüfen, dass keiner übrig ist.
  - Fehlt ein Ergebnis noch, ausdrücklich schreiben: „fehlt, kommt in Meldung 46, Grund …“.
  - Den Titel anpassen.

**M2: FG-113: Zeitpunkt des Merges gegenüber Regel A ist nicht ausgesprochen (Z. 10, 286, 322, 431)**
- Beleg: W44, 2.1 erlaubt den Merge ohne weitere Weisung, „wenn … der Diff nach Regel A **in Meldung 45** liegt“. REGELN Z. 219: „ausser FG-113: Merge nach Auflagen, Lesung nachträglich“. Der Diff liegt seit `bae72e5` auf `meldungen`, Meldung 45 ist aber noch nicht versandt.
- Wird vor dem Versand gemergt, sollte die Meldung das ausdrücklich sagen und begründen. Sonst wirkt es wie eine Abweichung, die erst beim Lesen auffällt.
- Korrektur: Beim Eintragen des Merge-Stands einen Satz ergänzen: „Gemergt um … UTC als `<sha>`. Der Diff lag seit `bae72e5` auf `meldungen`, deine Lesung kommt nachträglich (W44, 2.1).“ Dazu das Ergebnis des Tor-Kontrollfehlers `d13dcdd` und das Tor-Ergebnis.

**M3: Frage 5: Die Einordnung stützt sich auf eine Vermutung, obwohl ein stärkerer Beleg da ist, und eine Prüflücke fehlt (Z. 201–204)**
- „Keiner prüft Code, den N14 ändert (vermutet)“ ist gerade bei 1–4 schwach:
  - Die T-c-Tests (BG08 Ersetzen, Mischbetrieb) betreffen Abgleich und Gerät-Ersetzen.
  - N14 ändert `_marker_now` und `_stamp`, also Aufhebungsmarken.
- Stärker ist der Beleg aus `n14/ergebnis.md`, Abschnitt 3: Dieselben 4 T-c-Tests waren schon auf der N14-Basis `69e62ae` rot, im Container belegt auf `053931d`.
- Es fehlt der Hinweis, dass die Anpassung „15/15 grün auf `8888af9`“ **ohne N14** lief. Ob die angepasste T-c-Fassung mit N14 grün bleibt, ist nicht geprüft.
- Korrektur:
  - Bei 1–4 ergänzen: „schon auf der N14-Basis `69e62ae` rot (berichtet, N16/N14)“.
  - Den „vermutet“-Satz streichen oder als schwächstes Argument nachstellen.
  - Ergänzen: „Die T-c-Anpassung ist mit N14 nicht geprüft. Das zeigt erst das Tor in Schritt 8.“

**M4: Frage 4 stellt die Nutzerfolge als belegt dar. Die Quelle sagt „vermutet“ (Z. 157, 172, 180)**
- Beleg: `n14/ergebnis.md`, Nachtrag W44, Abschnitt 2: Der Mechanismus ist belegt, aber „Folge für Nutzer (vermutet): kein Verlust, aber bei jedem Abgleich ein überflüssiger Commit“.
- Die Meldung schreibt im Titel „endloses Hochladen“, in Z. 172 „Folge: … also ein überflüssiger Commit“ und in Z. 180 „dauerhaft und für Nico sichtbar“, alles ohne Stufe.
- Beobachtet wurde „Ruhe 4“ in einer begrenzten Nachstellung, nicht ein endloses Hochladen.
- Korrektur: In Z. 172 „(vermutet; beobachtet: 4 statt 0 Hochladungen in der Nachstellung)“ ergänzen. Im Titel „endloses“ durch „wiederholtes“ ersetzen oder mit „vermutet“ kennzeichnen. In Z. 180 „dauerhaft“ durch „solange keine neue Marke kommt (vermutet)“ ersetzen.

**M5: Die Selbstkontrolle meldet „erledigt“, wo B.3 und die Quellen offene Auflagen nennen (Z. 31, 37, 38, 86)**
- Z. 37, W44 2.3 Nr. 3: „Nach dem Merge laufen sie nicht noch einmal (nicht geplant …)“.
  - Die Weisung verlangt die Kontrollfehler „auf dem Endstand“. Ob `a551440` als Endstand gilt, ist offen.
  - „nicht geplant“ lädt zum Widerspruch ein.
  - Vorschlag: „KF auf `a551440` (Zweig-Endstand) 5/5 und 6/6 rot. Auf dem Integrationsstand nach dem Merge ist eine Wiederholung vorgesehen, oder du sagst, dass `a551440` reicht.“ Oder es kommt als kurze Teilfrage.
- Z. 38, W44 2.3 Nr. 4: „Messung … erledigt“. B.3 (Z. 345, 354) sagt dagegen, gemessen wurde auf dem Zweigstand, die Endstand-Messung kommt nach dem Merge. Korrektur: „auf dem Zweigstand erledigt; Endstand nach Merge offen“.
- Z. 31, 2.1 (4)–(6): „erledigt“. Laut `fg113/ergebnis.md` ist der Container-Beleg für `ibus` nach dem Merge Sache des Integrators. Korrektur: „(4) ibus-Beleg im Tor nach dem Merge“.
- Z. 86, Frage 1: „Die erteilten Auflagen sind erfüllt.“ Zu W44 2.10 gehören aber auch der ganze grüne Lauf und die Fotos an Nico. Korrektur: „Die bisher prüfbaren Auflagen sind erfüllt (Pixel, K1, PruefungstrainerBreiteTest). Ganzer Lauf und Fotos stehen aus.“

**M6: Nicos „Schreibfehler mit beheben“ (FG-103) hängt am N12-Merge, und N12 steht nicht in der Reihenfolge 3.1 (Z. 439, 502)**
- Beleg:
  - Nico, 11:54 UTC: „F1: b und den schreibfehler mit beheben“. Um 16:00 UTC hat er Lesart b bestätigt, also FG-103.
  - FG-103 ist laut 3.1 Nr. 9 „nach dem N12-Merge“ vorgesehen.
  - N12 (`180789b`) ist nicht in `a82fd34` (belegt), und N12 kommt in 3.1 nicht vor.
  - Damit hat ein ausdrücklicher Wunsch von Nico (höchste Instanz) keinen festgelegten Weg in 0.63.2.
- Ähnliches gilt für FG-102: Seine Vorbedingungen S5b, N10 und N11 stehen ebenfalls nicht in 3.1. Das nennt die Meldung nur als „(Bedingungen)“.
- Korrektur: In B.10 Schritt 9 oder B.14 einen Satz ergänzen: „N12 ist nicht in `a82fd34` und nicht in 3.1. FG-103 (Nicos ‚Schreibfehler‘) hat damit keinen festgelegten Merge-Platz. Ebenso fehlen S5b/N10/N11 für FG-102.“ Daraus entweder eine kurze Frage 9 an Chat machen (Platz von N12, S5b, N10, N11 in der Reihenfolge) oder den Plan nennen, falls es einen gibt.
- B.14 Z. 499 kürzt Nicos Wortlaut auf „F1: b …“. Den Teil „und den schreibfehler mit beheben“ vollständig zitieren, weil sich die Zeile 16:00 darauf bezieht.

### Niedrig

- **N1 (Z. 10):** „Basis-Tor … grün (B.12)“. Die Einzelheiten stehen in B.11 (Z. 461–467). Verweis auf „B.11, B.12“ ändern.
- **N2 (Z. 99–101), Frage 1:**
  - Mit (a) gibt Chat eine neue Stoppgrenze frei. Das ausdrücklich so schreiben: „Stoppgrenze neu: `app_gui.py` +12/−9, Test +38/−5“.
  - Ergänzen, dass mit dem neuen Diff erst 24 der 83 Tests gelaufen sind. Die Folge-Zeile nennt das nur indirekt.
- **N3 (Z. 233), Frage 6:** Es fehlt, ob der Merge von FG-107+110 (Schritt 9) bei (a) auf die neue FG wartet oder nicht. Ein Halbsatz genügt: „FG-107+110 wird unabhängig davon gemergt“ oder „wartet“.
- **N4 (Z. 258–261), Frage 8.1:** (a) erweitert FG-113 um eine vierte Datei (`test_workflow_0632.py`). Die Zeilenzahl fehlt. Chat braucht sie als Stoppgrenze, etwa „+1/−1 (vermutet)“.
- **N5 (Z. 135–155), Frage 3:**
  - Klarstellen, dass Nico das „Ob“ entschieden hat und Chat nur über das „Wie“ entscheidet (Abschrift `Antwort_Nico_Handy_Schalter.md`). So ist klar, warum es keine Option „nicht erteilen“ gibt.
  - Für (a) fehlt eine Zeile „Blockiert: nichts außer FG-114“.
- **N6 (Z. 119), Frage 2 (C):** Die Quelle nennt zusätzlich „Aussehen bei Maximal nicht gemessen“. Für einen fairen Vergleich mit aufnehmen.
- **N7 (Z. 158), Frage 4:** Die Belegstufe nennt „Nachtrag Weisung 44, Abschnitt 2“. Das lässt sich mit dem Dokument „Nachtrag Anlagen“, Abschnitt 2, verwechseln. Korrektur: „`n14/ergebnis.md`, Abschnitt ‚Nachtrag Weisung 44, 2.5‘, Teil 2“.
- **N8 (Z. 22 und B.11):** Gut, dass die Stufen sauber getrennt sind. Die s1c2-Quelle sagt allerdings, `test_normal_1360` „steht in bekannt_rot_github.txt“. Die Meldung sagt richtig, die Liste ist leer. Den Widerspruch zur Quelle in einem Halbsatz nennen, weil Chat sonst beim Lesen der Quelle stolpert.

---

## Merge-Reihenfolge und Merge-Stand (Prüfauftrag 4)
- `version-0632` = `a82fd34` (belegt, `ls-remote`). S6a und S6b sind nicht gemergt, die Aussage stimmt. Die verworfenen lokalen Merges `8ffcf7d`, `8888af9` und `7776627` stehen nicht als Zweigkopf auf GitHub (belegt über `ls-remote`, nur Köpfe geprüft).
- B.10 entspricht W44 3.1, Schritte 1–9. FG-114 ist als Vorschlag gekennzeichnet (Frage 3). Das ist korrekt, weil eine Abweichung von 3.1 eine Frage ist.
- Lücke: N12, S5b, N10 und N11 fehlen in 3.1, aber FG-102 und FG-103 hängen daran (M6).
- FG-113: Merge-Stand ist noch Platzhalter (M1, M2).

## Nicos Entscheidungen (Prüfauftrag 3)
- 13:33 „Foto Nachtrag: Ja sollen sie.“ sowie 14:59 „Ja für beide.“ und 16:00 „Frage 1: Ja / Frage 2: b“ sind richtig wiedergegeben, die Bedeutungen stimmen mit den Abschriften überein.
- 11:54: gekürzt; der „Schreibfehler“-Teil fehlt im Zitat (M6).
- Die Folge von Frage 2 (A) für Nicos FG-111-Abnahme ist nicht genannt (H2).

## Regeln (Prüfauftrag 1)
- Keine Empfehlung lockert einen Test. Frage 1 (c) und Frage 2 (C) sind korrekt als Lockerung gekennzeichnet und nicht empfohlen.
- Frage 4 (a) ist nur ein Antrag. Das ist richtig, weil `fisi_sync.py` geschützt ist und ein Eingriff in den Abgleich nie E1 ist.
- Frage 1 hält die Stoppgrenze ein (angehalten, nichts committet).
- Problematisch ist nur Frage 2 (H2: geschützte Datei nicht benannt) sowie der Zeitpunkt nach Regel A bei FG-113 (M2).

## Kürzungsvorschläge (Prüfauftrag 5), ohne Informationsverlust
1. **FG-113 wird fünfmal beschrieben** (Kopfblock, Auflagen-Tabelle Z. 28–33, B.2, B.10 Z. 431, B.11). In B.10 und B.11 nur „siehe B.2“ und die Laufnummer stehen lassen. Etwa 6 Zeilen weniger.
2. **Fingerabdruck „code“ und 94/92 stehen doppelt:** Z. 63–64 in „Zahlen gegen Beleg“ und B.4 und B.9 sagen dasselbe. Z. 63–64 auf einen Verweis „B.4 / B.9, belegt“ kürzen.
3. **B.13 Absturz:** Die Liste „Verloren“ und die Speicherregel lassen sich auf 5 Zeilen zusammenfassen. Wichtig für Chat sind nur: N15-Probe-Tor verloren, Basis-Tor wiederholt, und kein Stand auf GitHub ging verloren. Die Zeitangaben-Widersprüche stehen schon in „Eigene Fehler“ Nr. 6.
4. **Frage 5** ist im Kern nur zur Kenntnis, weil (a) ohnehin die geltende Regel ist. Sie kann auf Problem in 2 Zeilen, Liste der 8 Tests als eine Zeile je Gruppe (1–4 T-c, 5–7 die drei, 8 B-G-17) und Empfehlung gekürzt werden. Die Einzelnamen stehen schon in B.11 bzw. `n14/ergebnis.md`. Etwa 8 Zeilen weniger.
5. **Selbstkontrolle, Auflagen-Tabelle:** Zeilen, die nur „B.x“ verweisen (2.6, 2.7 Satz, 7), kann man zusammenfassen. Die Tabelle bleibt als Checkliste aber nützlich, deshalb nur leicht kürzen.
6. **Z. 129** streichen (siehe H1), die Diffs stehen dann in B.1.

---

## Kurzurteil
Die Fragen sind überwiegend selbsttragend und entscheidbar. Die Empfehlungen sind regelkonform, und die Stufen sind sorgfältig getrennt. Vor dem Versand nötig:
1. Den Regel-A-Stand auf `83b9320` bringen (H1).
2. In Frage 2 die geschützte Datei und die Folge für FG-106/FG-111 sowie Nicos Abnahme ausdrücklich nennen (H2).
3. Alle Platzhalter füllen oder ausdrücklich als fehlend erklären (M1), den FG-113-Merge-Zeitpunkt begründen (M2).
4. Die Stufen in Frage 4 und 5 schärfen (M3, M4), die „erledigt“-Einträge in der Selbstkontrolle berichtigen (M5).
5. Die Lücke N12/FG-103 gegenüber Nicos Wunsch nennen (M6).
