# Selbstprüfung Meldung 43 (nicht unabhängig)

Stand 14.10.2026, nach 08:45 UTC. Geprüft wurde vom Verfasser selbst, in einem getrennten Prüfgang gegen die Quellen. **Das ist keine unabhängige Gegenprüfung.** Ein anderer Agent sollte sie vor dem Push auf `meldungen` nachholen.
Nichts committet, nichts gepusht. Alle Prüfungen nur lesend (`git ls-remote`, `git show/diff/log`, `gh run view`, Dateien gelesen und gezählt).

## 1. Pflichtinhalte aus Weisung 42, Abschnitt 7 (und Auftrag)
| Pflicht | Stelle in Meldung 43 | erfüllt |
|---|---|---|
| Einschätzung „Alles ersetzen“ in den Zufallsabläufen (2.4), Maßstab als E2 | Frage 5, Optionen (a) v0.63.1 / (b) Ausnahmeregel = Lockerung / (c) nichts | ja |
| Zahl der langen Wörter ohne Eintrag und Quellen (2.11 Nr. 2); Test endet rot | Frage 1: 94 = 92 Listentitel + 1 Titel + 1 Rechenweg; Quellen genannt; (c)/(d) als Lockerung markiert | ja |
| Stellen „Zahl und Einheit“ (2.7), Weg als Frage | Frage 6: 8.400, nach Datei, 6 Formatierer, Weg (a)/(b)/(c) | ja |
| Stand der gebauten FG mit Zweig, SHA, Lauf, Ergebnis | Abschnitt C (FG-97, 104, 105, 106, Frage 25, 100, 101, 102, 103, 107, 108) | ja |
| Ergebnis Probe Frage 24; zwei Abweichungen; Satz nicht umformuliert, nur Vorschlag | Frage 9; Vorschlag klar als „Angebot, nicht geprüft“ markiert, Entscheidung bei Chat | ja |
| FG-107-Antrag mit Messwerten; 0,2 s nicht erreicht | Frage 7, fett „wird mit FG-107 allein nicht erreicht“ | ja |
| GradientButton-Vorschlag; Höhe bei 200 % knapp als E2 | Frage 8 mit Teilfrage Höhe | ja |
| N6: K2b gleichwertig, K2c nach dem Bau | Frage 2 und Weitere Punkte 1 | ja |
| N6 × S5c mit `3ec3665` nicht neu getestet | Weitere Punkte 2 | ja |
| N8 Selbstkorrektur „keine roten Tests“ | Weitere Punkte 3 (mit Korrektur der Formulierung aus Meldung 42) | ja |
| S1c2: Optionen SG1120 Inter Unterschrift; Testdatei-Konflikt Fix 3b | Fragen 3 und 4 | ja |
| Dauer „rest“ auf Zweigen (nur Info) | Weitere Punkte 4 (Tabelle) | ja |
| Frage 25 erledigt | Abschnitt C, Weitere Punkte 5 | ja |
| N14: s1_voll 45/45, U1/U3 nur Zählweise | Weitere Punkte 6 | ja |
| Zeittest-Vermerke am Merge-Tor | Weitere Punkte 8 | ja |
| Punkte aus PROTOKOLL.md | Weitere Punkte 9 (N3/N4 gemergt, Welle 3c komplett, Fix 3b lokal `8f18818`, Tor läuft) | ja |
| Zeile 1/2, Kopfblock blockierend zuerst, max. 10 Zeilen | Zeile 1 „AN: Claude Chat“, Zeile 2 „ENTSCHEIDUNG NÖTIG: ja (Chat)“, Kopfblock 6 Punkte | ja |
| Jede Frage selbsttragend mit Optionen, Empfehlung, Folgen | Fragen 1–10 je Problem / Stand / Optionen mit Folge / Empfehlung / Blockiert / Belege | ja |
| „Zur Kenntnis“ und Hinweis Meldung 39 (`ec41b37`, 28 Fragen) | Abschnitt D und „Hinweis“ | ja |
| Keine Zeitprognosen | Suche nach Zeitwörtern ohne Treffer; nur Reihenfolgen genannt | ja |
| Nächste freie FG-109 | Kopfblock 6, Frage 6 (b) | ja |

## 2. Nachgeprüfte SHAs und Läufe (belegt)
- `git ls-remote origin`: n6 `3ec3665`, n8 `ad0808d`, n9 `352abad`, n14 `02e37b2`, s1c2 `452141b`, s6b `cb60f8b`, fg96 `4d77439`, fix3b `9df7bd8`, `version-0632` `e0f9c7e`, `meldungen` `ec41b37`. Stimmt mit der Meldung überein.
- Alle 25 in der Meldung genannten Kurz-SHAs sind im Klon als Commit vorhanden (`git cat-file -t`). `0329bc9`, `53a4354`, `ebfaf7b`, `7e25060` und `8f18818` gibt es nur lokal; die Meldung nennt sie als lokal.
- `gh run view` (Zweig, Kopf, Ergebnis):

  | Lauf | Zweig | Kopf | Ergebnis |
  |---|---|---|---|
  | 38532489805 | n8 | ad0808d | cancelled (nur „rest“ cancelled) |
  | 38526544492 | n6 | 3ec3665 | failure (nur „rest“) |
  | 38529539865 | n9 | 352abad | failure (nur „rest“) |
  | 38528086131 | s6b | cb60f8b | success (alle Jobs) |
  | 38525544662 | s6b | cb60f8b | failure (nur „android“) |
  | 38526665855 | s1c2 | 452141b | failure (nur „rest“) |
  | 38495818809 | fg96 | 4d77439 | failure |
  | 38510468972 | n8 | 927ef5f | cancelled |
  | 38512762337 | s6b | d96dc5e | success |

- Jobdauer „rest“ aus `startedAt`/`completedAt`: 1637 s, 1711 s, 1629 s, 1440 s.

## 3. Nachgezählte Zahlen (belegt)
- 94 Wörter: Tabelle in `n8/lange_woerter_ohne_eintrag.md` gezählt (94 Zeilen). 92 enthalten „Listentitel“ (AP1 32, AP2 55, Testprojekte 11; ein Wort kann in mehreren Listen stehen). Dazu 1 Titel und 1 Rechenweg.
- 8.400 Stellen: `n9/logs/zahl_einheit_stellen.json`. Wort 778, Zeichen 7.622, Code 473 (davon geschützt 419), Inhalte 7.927.
- Formatierer-Zeilen auf `352abad` per `grep`: 64, 1946, 1951, 6372, 7592, 251, 315.
- FG-107-Diff: +131/−8, +11/−2, +12/−2; sha256 beginnt mit `58f5137f`, endet mit `4b6b`.
- GradientButton-Diff: **+9/−2**. Die Quelle sagt +8/−2; in der Meldung steht der nachgezählte Wert mit Hinweis.
- FG-106: Die geänderten Zeilen in `mobile/src/spiel.py` (`72afbe1..352abad`) sind gleich `n9/vorschlag_spiel200.diff` (80 Zeilen, `diff` ohne Ausgabe), numstat 52/28.
- FG-97 und FG-105: `git diff 927ef5f ad0808d` gleich Anhang B (`apk_pruefen.py`) und Anhang E (`fisi_lernen.py:794`, eine Zeile in `ERSETZEN` plus Kommentar).
- `cb60f8b` gegenüber `d96dc5e`: nur `test_bestenliste_zeitumstellung_0632.py`, +152.
- N6: Datei der Kontrollfehler 06:57:45 UTC (im Text), erster Bau-Commit `6cef03c` 06:58:38 UTC, `9208fe5` 06:59:53 UTC (`git log`).
- `s1_voll.py`: In `ci_tests.sh` und `.github/` auf `02e37b2` kein Treffer.
- `14b3bd4:fisi_sicherung.py:661 replace_all` ist vorhanden.

## 4. Doppelt gefragt? (gegen Meldung 42 und Weisung 42)
- Frage 1 (lange Wörter): Weisung 2.11 Nr. 2 verlangt genau diese Rückfrage. Neu, nicht doppelt.
- Fragen 2–4 (N6-Kontrollfehler, S1c2-Inter, Konflikt): in Meldung 42 nicht gestellt.
- Frage 5, 6, 7, 8 und 9: Weisung 42 verlangt sie als Folgeschritt (2.4, 2.7, 2.18, 2.19). Die ursprünglichen Fragen 4, 7, 21 und 24 werden nicht wiederholt.
- Frage 10 („breite“ vor N8 über 1350 s): Weisung 42, 2.1 regelt nur die N8-Dateien. Neu, mit Begründung „Größen sind Stoppgrenzen“.
- **Bewusst nicht gefragt**, weil schon entschieden:
  - S1c2-E2 „rest 27 von 30 min“: FG-96 verschiebt `test_ansichten_breite.py` nach „breite“ (Weisung 38/40); daraus folgt nur Frage 10.
  - „rest“ auf den Zweigen: nach Weisung 42, Zur Kenntnis 8, bekannt; nur Info.
  - N8-E2-8: durch `bekannt_rot_github.txt` beantwortet.
  - Zeittests: Regel 2.15.
  - U1/U3: nur Zählweise, also keine E2 (2.4).

## 5. Befunde dieser Selbstprüfung (eingearbeitet)
- S1: In Frage 6 stand zuerst „Rest 18“ für die übrigen ungeschützten Dateien. Richtig ist 15 (54 − 39). Korrigiert.
- S2: Die Quelle nennt für GradientButton +8/−2; nachgezählt sind es +9/−2. In der Meldung steht 9 mit Hinweis.
- S3: N6 und S1c2 nennen beide „rest“ 1587 s (Tests), in verschiedenen Läufen. Die Jobdauern unterscheiden sich (1637 / 1629 s, belegt). Ein Zufall ist möglich. In der Meldung steht der Wert als berichtet, die Jobdauer daneben.
- S4: `n8/lange_woerter_ohne_eintrag.md` sagt „Der Test ist NICHT gebaut“. Der Auftragstext „Der Test endet rot“ meint die Vorgabe der Weisung. Die Meldung sagt beides.
- S5: Die Meldung-42-Aussage „bis zum Abbruch keine rote Datei“ (Frage 1) ist durch die N8-Selbstkorrektur überholt. In Weitere Punkte 3 ausdrücklich korrigiert.

## 6. Offen / nicht geprüft
- Inhalt der Berichte (Messwerte, Kontrollfehler, Fotos, Ursachen) ist nicht selbst nachgeprüft; in der Meldung steht er als „berichtet“.
- Der Vorschlagssatz in Frage 9 ist nicht gegen die Probe geprüft und so markiert.
- Nicht ermittelt: ob die Unterschrift „Löschen und zurücksetzen“ in v0.63.1 bei „Sehr groß“ 1120 sichtbar ist.
- Das Merge-Tor `8f18818` (Fix 3b) war beim Schreiben noch nicht fertig.
- Suche nach E-Mail, Zugangsdaten und persönlichen Pfaden in der Meldung: 0 Treffer.
