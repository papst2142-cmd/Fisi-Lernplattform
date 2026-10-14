# Gegenprüfung 1 zu Meldung 45 (Fassung 1), 14.10.2026 ~16:30 UTC

Prüfer: unabhängiger Gegenprüfer 1. Geprüft wurde gegen die Quellen, nicht gegen den Entwurf. An der Meldung wurde nichts geändert, nichts committet, nichts gepusht, keine Tests gestartet.
Quellen: `OFFEN_FUER_BERICHT.md`, `integration/PROTOKOLL.md`, `ergebnis.md` in fg113, fg109, fg114, n14, n9, n7/fg107_fg110, n7/gp_fg107_fg110 und s1c2/nachbesserung; `integration/n9_konflikt/optionen_5185e78.md`; `integration/tor/tor_a82fd34_4.md` mit Rohordner; `integration/welle4/tc/`; `werkzeug/merge_tor.sh` und `bekannt_rot_github.txt`; `n8/lange_woerter_ohne_eintrag.md`; Weisung 44 und Nachtrag; Antworten von Nico in `plan_0.63.2/freigabe/`; `origin/meldungen` (frisch geholt, Kopf **83b9320**); `git ls-remote origin`; `gh run view` (10 Läufe); `get_job_logs` über MCP (5 Jobs).

## Ergebnis
**Kein hoher Befund. 3 mittlere und 9 niedrige Befunde.** Alle Zahlen zu den Läufen, den roten Tests, den Zweigköpfen, sha256 und numstat stimmen mit den Quellen überein. Die Fehler betreffen den Stand von `meldungen`, der inzwischen weiter ist als im Entwurf, die Platzhalter und einzelne Formulierungen.

## Stichproben: 77 geprüft, 73 stimmten
| Bereich | geprüft | stimmt | Abweichung |
|---|---|---|---|
| Zweigköpfe (Z. 6, 59; `ls-remote`) | 15 | 15 | – |
| Kopf `origin/meldungen` | 1 | 0 | Entwurf: `8aaadec`, tatsächlich `83b9320` (M1) |
| sha256 aus den Blobs neu gerechnet (13 Diffs + FG-114-Antrag) gegen Entwurf und `SHA256SUMS.txt` | 14 | 14 | – |
| Aussage „Antrag nicht in `SHA256SUMS.txt`“ (Z. 288) | 1 | 0 | steht seit `83b9320` drin (M1) |
| Aussage „zehn Anlagen“ (Z. 60) | 1 | 0 | es sind 13 Diffs + Antrag (M1) |
| numstat (`git apply --numstat` auf die Anlagen; `git diff --numstat` a82fd34..cbbbad1/93bc9ce/5c6087d, 3d09742..a551440) | 21 | 21 | – |
| GitHub-Läufe `gh run view` (Ergebnis, SHA, Zweig, Jobs): 38576166779, 38574101656, 38572154311, 38575755031, 38575841120, 38576233414, 38576551817, 38578347292, 38572865128, 38575978718 (dazu 38572079729: success, `messung-0632-fg110`) | 10 | 10 | – |
| Job-Logs über MCP: N14 rest (1641 s, rote Dateien), N14 spiel (genau `ErfolgeTest.test_bestenliste_wird_abgeglichen`, 384 Tests), FG-113 rest2 (524 s, grün), N7-fg rest (1577 s, zwei rote Dateien mit den drei Tests), S1c2 rest (nur `test_ansichten_breite.py` rot) | 5 | 5 | – |
| Weitere: `8f18818` ist kein Vorfahr von `6330eb4`; `93bc9ce` = a82fd34 + 1 Commit; 94 = 92 + 1 + 1 (Quellspalte gezählt: 27+3+2+51+1+8); ANHANG_A 33 Einträge mit `"AN‖PAS|SUN|GEN"` auf `c65f67d`; `fingerabdruck_0624.py` Z. 50–51; `merge_tor.sh` Z. 75, rest2 Z. 15/58/60/149–150; Tor `a82fd34_4` (GRÜN, 72/1457, Rückgaben 0, Tags); T-c 15 OK / 4 rot / KF 9 rot; `bekannt_rot_github.txt` leer | 9 | 8 | „drei Platzhalter“ (Z. 6) stimmt nicht (M2) |

Die 34 Quellvergleiche Entwurf ↔ `ergebnis.md`/Protokoll (Zeiten, Testzahlen, KF-Listen, Messwerte in B.2–B.8, Fragen 1–8) sind in den 77 nicht mitgezählt. Abweichungen gab es dort nur bei den unten genannten Formulierungen.

## Befunde

### M1 (mittel): Der Stand von `meldungen` ist veraltet (`8aaadec` statt `83b9320`)
- **Zeilen:** 27, 60, 94, 274–275, 288 sowie die Tabelle B.1 (Z. 277–289).
- **Beleg:** `git show origin/meldungen` → Kopf `83b9320` („Anlagen Regel A: N9xN3 Aufloesung (3 Diffs), sha256 FG-114-Antrag nachgetragen“). `SHA256SUMS.txt` enthält jetzt 14 Zeilen, darunter `a6e007b6…b971 FG-114_Antrag_…md` und die drei Diffs `N9xN3_*`. Die neu gerechneten sha256 aller 14 Dateien stimmen.
- **Folgen im Entwurf:**
  - Z. 27 nennt `8aaadec` und „drei neue Anlagen“. Seit `917f756` sind sieben Dateien dazugekommen: FG-113, FG-114-Diff, FG-114-Antrag, FG-112 neu und drei N9×N3-Diffs.
  - Z. 60: „zehn Anlagen und des FG-114-Antrags“ ist falsch, richtig sind 13 Diffs und der Antrag.
  - Z. 288: „nicht in `SHA256SUMS.txt`, ich habe es selbst gerechnet“ stimmt nicht mehr.
  - In B.1 fehlen die drei N9×N3-Diffs. Sie stehen nur in Frage 2 (Z. 129).
- **Korrektur:**
  - Überall `8aaadec` als Kopf durch `83b9320` ersetzen. Bei Frage 1 bleibt `8aaadec` als Commit des FG-112-Diffs richtig.
  - Z. 27: „dazu sieben neue Anlagen (B.1)“.
  - Z. 60: „sha256 der 13 Diffs und des FG-114-Antrags“.
  - Z. 288: die Klammer streichen.
  - In B.1 drei Zeilen `N9xN3_…` ergänzen, mit Commit `83b9320` und Stand „Frage 2“.
  - Z. 129 auf einen Satz kürzen: „Die drei Diffs liegen auf `meldungen/anlagen/` (`83b9320`), Präfix `N9xN3_`.“

### M2 (mittel): Platzhalter falsch gezählt, zwei Pflichtteile aus Weisung 44, 7 fehlen noch
- **Zeilen:** 4, 6, 10, 34, 47, 322, 431, 437, 507, 523.
- **Beleg:** Es gibt vier verschiedene Platzhalter an acht Stellen: `[MERGE-STAND FG-113 EINTRAGEN]` (Z. 10, 322, 431), `[DIAGNOSE LoadingHintTest FOLGT]` (Z. 34, 507), `[TOR N6 EINTRAGEN]` (Z. 47, 437) und `[COMMIT EINTRAGEN]` (Z. 523). Z. 6 nennt „drei“. Weisung 44, 7 verlangt ausdrücklich die „Diagnose `LoadingHintTest` (2.2)“ und das „Tor N6“. Beide fehlen noch. Zum Tor N6 gehört nach 2.8 auch der Messwert, ob die Fix-3b-Anpassung der Knopfzeilen beim Vorladen rechtzeitig kommt. Der Titel (Z. 4) lautet noch „Fassung 1 (Entwurf, noch nicht gegengeprüft)“.
- **Korrektur:**
  - Z. 6: „Die vier Platzhalter (an acht Stellen) …“.
  - Vor dem Versand alle acht Stellen füllen und den Titel anpassen.
  - Ist die Diagnose oder das Tor N6 bis dahin nicht fertig: ausdrücklich als „offen, kommt in Meldung 46“ kennzeichnen und in den Kopfblock aufnehmen. Ein Platzhalter darf nicht stehen bleiben.
  - Beim Tor N6 den Messwert zur Vorlade-Beobachtung nennen (Weisung 44, 2.8, letzter Punkt).

### M3 (mittel): Abschnitt 6, Punkt 1 steht nicht ganz in den Nachträgen, aber als „belegt“ erledigt
- **Zeile:** 53.
- **Beleg:** Weisung 44, 6.1 verlangt die FG-109-Fotos „mit dem Hinweis, dass die Liste eine Untergrenze ist“. `Nachtrag_Meldung_44_Fotos_Teil1.md` und `…_Teil2.md` enthalten diesen Hinweis nicht (`grep -i Untergrenze` ohne Treffer). Ob er in der Galerie steht, habe ich nicht geprüft. Die Punkte 2–6 sind in Teil 2 enthalten.
- **Korrektur:** Entweder den Hinweis in der Galerie nachsehen und die Fundstelle nennen. Oder in Z. 53 schreiben: „Punkte 2–6 gesendet; Punkt 1 ohne den Hinweis ‚Untergrenze‘ (geht mit dem nächsten Nachtrag an Nico)“. Die Stufe dann auf „belegt (Dateien), Galerie nicht geprüft“ setzen.

### N1 (niedrig): Die „rest“-Zeiten in B.11 vermischen zwei Zuschnitte, S1c2 fehlt
- **Zeilen:** 451–456 und 460.
- **Beleg:**
  - Laut `gh run view` haben die Läufe 38572154311 (N7-fg), 38575755031 (N14), 38575841120 (N9) und 38576551817 (S1c2) **keinen** Job „breite“. Sie liefen mit dem alten Zuschnitt, „rest“ enthält dort die Breitendateien.
  - Nur bei N9 steht „(alter Zuschnitt)“.
  - Z. 460 stellt 1470/1469 s (neuer Zuschnitt, mit „breite“) und 1577/1641/1692 s (alter Zuschnitt) nebeneinander.
  - Im Job-Log steht bei S1c2 „Teil rest: zusammen 1581 s“. Der Entwurf gibt dort nur die Jobdauer an.
- **Korrektur:**
  - Bei N7-fg, N14 und S1c2 „(alter Zuschnitt)“ ergänzen.
  - Bei S1c2 „1581 s (alter Zuschnitt)“ eintragen.
  - Z. 460 trennen: „mit ‚breite‘: 1470, 1469 s; alter Zuschnitt: 1577, 1581, 1641, 1692 s“.

### N2 (niedrig): Stand des T-c-Nachweises
- **Zeilen:** 202 und 432.
- **Beleg:** Laut Protokoll (13:10 UTC) wurde die T-c-Anpassung auf `8888af9` als `7776627` gebaut. „Ohne Anpassung“ bezieht sich auf `8888af9`, „mit Anpassung 15/15“ auf `7776627`. Die Logs `welle4/tc/tc_mit.log` (15 OK), `tc_ohne.log` (4 failures) und `tc_kf.log` (9 failures) stimmen.
- **Korrektur:** „auf `8888af9` + Anpassung (`7776627`, verworfen)“.

### N3 (niedrig): Z. 22 und B.11 stufen die Läufe unterschiedlich ein
- **Zeilen:** 22 und 457.
- **Beleg:** Z. 22 sagt, die Läufe seien nicht selbst abgefragt („berichtet“). In B.11 steht beim FG-114-Lauf „Job-Ergebnisse belegt“. Das ist die Stufe des Bauers, nicht die des Verfassers.
- **Korrektur:** Bei FG-114 „(laut Bauer: Job-Ergebnisse belegt, Einzeltests berichtet)“. Optional in Z. 22 ergänzen: „Gegenprüfung 1 hat 10 Läufe mit `gh run view` und 5 Job-Logs nachgeprüft, alle gleich.“

### N4 (niedrig): Der `TOR_GIT_TAGS`-Standard lässt sich belegen
- **Zeile:** 472.
- **Beleg:** `werkzeug/merge_tor.sh` Z. 54: `GIT_TAGS="${TOR_GIT_TAGS-v0.50 v0.56 v0.62.3 v0.63.1}"`. Die Kommentare in Z. 15–28 und die Teile mit `rest2` in Z. 58/60 stehen ebenfalls drin.
- **Korrektur:** „(belegt: `merge_tor.sh` Z. 54)“ statt „Inhalt im Werkzeug nicht selbst geprüft“.

### N5 (niedrig): Z. 129 ist nicht eingearbeitet
- **Zeile:** 129.
- **Beleg:** Der Satz ist roh angehängt („Die drei Diffs liegen jetzt auf `meldungen`: Anlagen auf `meldungen` (83b9320): meldungen/anlagen/…“) und wiederholt die Tabelle darüber.
- **Korrektur:** siehe M1.

### N6 (niedrig): B.13, „Erhalten (auf GitHub)“
- **Zeile:** 480.
- **Beleg:** Die noch nicht committete 6a-(b)-Änderung lag im Container-Arbeitsbaum, nicht auf GitHub. Das Protokoll (13:50 UTC) nennt sie getrennt.
- **Korrektur:** „s1c2 `7acfccb` (GitHub); dazu im Arbeitsbaum die noch nicht committete 6a-(b)-Änderung (übernommen, E1-11)“.

### N7 (niedrig): Zwei Auflagen aus Weisung 44 ohne Stand
- **Zeilen:** Tabelle Z. 24–54 und B.6/B.10.
- **Beleg:**
  - (a) Weisung 44, 2.4, letzter Punkt: Treffen die FG-109-Änderungen an `spiel.py` mit FG-106 oder FG-111 zusammen, braucht es ein eigenes Tor mit den Spiel-Tests. FG-109 ändert `mobile/src/spiel.py` (+4/−2), N9 ebenfalls. Im Entwurf steht dazu nichts.
  - (b) Weisung 44, 2.1, Stoppgrenze: `build.yml` und `ci_tests.sh` zusammen höchstens etwa 40 Zeilen, der Test höchstens etwa 30. Gebaut sind 10 und 21 Zeilen (fg113/ergebnis.md, numstat belegt). Die Einhaltung steht nicht in der Tabelle.
- **Korrektur:**
  - In B.10, Schritt 9, ergänzen: „FG-109 × N9/FG-111 in `spiel.py`: eigenes Tor mit Spiel-Tests (Weisung 44, 2.4)“.
  - Zeile 2.1 (Stoppgrenze) in die Auflagen-Tabelle: „10 / 21 Zeilen, eingehalten, belegt (numstat)“.

### N8 (niedrig): Frage 5 enthält einen zweiten Vorschlag ohne eigene Optionen
- **Zeile:** 210.
- **Beleg:** Nach „Empfehlung: (a)“ folgt „Dazu ein Vorschlag (E2)“, der künftige Zweigläufe gegen die drei „(bis 14.10.)“-Einträge abgleichen soll. Er hat keine eigenen Optionen und keine Folge.
- **Korrektur:** Als Teil von Option (a) formulieren, zum Beispiel „(a) … und künftig …“, oder als Unterpunkt 5.2 mit (a) annehmen und (b) nicht.

### N9 (niedrig): Kleinigkeiten
- Z. 158 nennt „Nachtrag Weisung 44, Abschnitt 2“. Im n14-Ergebnis heißt der Abschnitt „Nachtrag Weisung 44, 2.5“, Unterabschnitt 2. Besser: „`n14/ergebnis.md`, Nachtrag W44 2.5, Abschnitt 2“.
- Z. 166: Mit O kam die 4 in 0 von 15 Läufen vor. Das stimmt (5+5+5).

## Format, Vollständigkeit, Zeitprognosen
- **Zeile 1 und 2:** `AN: Claude Chat` und `ENTSCHEIDUNG NÖTIG: ja (Chat)`. In Ordnung.
- **Fragen:** Die Fragen 1–8 sind selbsttragend und haben je Problem, Optionen, Empfehlung und Belegstufe. Frage 8 hat zwei Unterpunkte mit je eigenen Optionen und Empfehlung. In Ordnung (Ausnahme: N8).
- **Stufen** belegt/berichtet/vermutet/nicht geprüft: durchgehend verwendet, zu klären ist nur N3.
- **Zeitprognosen:** keine gefunden (`grep` auf morgen, dauert, voraussichtlich, Prognose, „in N Minuten/Stunden“).
- **Weisung 44, 7:**
  - vorhanden: Diffs mit sha256, FG-113-Messung, Teilung und Stand, FG-107+110 (Gegenprüfung, B3, `_dash_query`), Satz zu „code“, 94/92, 6b-Messung, Startwert 19, Merge-Reihenfolge mit allen roten Tests je Lauf, Kopfblock, Selbstkontrolle.
  - fehlen noch: Diagnose `LoadingHintTest` und Tor N6 (M2).
- **Nachtrag zu Weisung 44:** Windows-Worst-Case gemessen (B.3), PDF als fester Test (B.6), Zusatzzeile N6 vorbereitet (Z. 47/437), `_dash_query` als Frage 6, lange Zeile nicht umbrochen (B.7). Vollständig.
- **Widersprüche in der Meldung:** M1 (Kopf `8aaadec` gegen `83b9320` in Z. 129), M2 („drei“ gegen vier Platzhalter), N3 (Z. 22 gegen Z. 457). Weitere habe ich nicht gefunden.
