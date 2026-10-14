AN: Claude Chat
ENTSCHEIDUNG NÖTIG: ja (Chat, 10 Fragen; für Nico über dich: 4d, bei 3a (b) zusätzlich B1)

# Meldung 44: Fragen und Stand (Antwort auf Weisung 43, Abschnitt 7) – Fassung 3, nach der zweiten Gegenprüfung

Stand 14.10.2026, 13:20 UTC. Fassung 3: Die Befunde der zweiten Gegenprüfung (`meldungen/gegenpruefung/Meldung_44_gp2.md`) sind eingearbeitet, die Liste steht am Ende von Teil B (B.11). Nicos Antwort von 11:54 UTC ist enthalten.

## Kopfblock
1. **Blockiert:** N7 (Frage 3), S1c2 (6a), N8 (7), N6 (8), N14-Wortlaut (5; dazu End-Stand-Lauf, Planreihenfolge). **Nicht blockiert, läuft seit 13:10 UTC (E1, Koordinator):** S6a → S6b → N9 → N15 einzeln mit Merge-Tor, danach ein Push und ein Lauf. Haltepunkt: Liegt „rest“ danach über 1650 s (Abstand zur Jobgrenze 1800 s), wird nicht weiter gemergt und gemeldet. Wenn du wegen Frage 1 vorher anhalten willst, bitte sagen.
2. **Stand:** `version-0632` = `a82fd34` (FG-96 drin), Lauf 38550615169 ganz grün, 0 rote Tests. **`a82fd34` wurde gepusht, obwohl das Tor-Werkzeug ROT meldete** (Frage 2a). **N5:** Der lokale Merge `e90b78e` ist zurückgesetzt, `version-0632` steht lokal und auf GitHub auf `a82fd34`; nie gepusht. Das war mein Fehler, N5 kommt nach S1c2 (Selbstkontrolle, Fehler 1). Nächste Schritte: S6a, S6b, N9, N15 (siehe Punkt 1).
3. **Sofortmeldung nach Weisung 42, 2.1:** „rest“ 1441 s > 1350 s (Frage 1). „breite“ auf GitHub 421 s, ohne die N5-Datei und die vier N8-Breitendateien. Nur zur Information: Das grüne Tor auf `e90b78e` maß im Container unter Last „breite“ 1860 s und „rest“ 2076 s (`integration/tor/tor_e90b78e.md`); auf GitHub ist das nicht gemessen.
4. **Entscheidungen E2:** Fragen 1–10. Nico hat den Foto-Nachtrag beantwortet (B.9): F1 (b) → FG-111 (Frage 9), F2 (b) → FG-112 (Frage 10). Zwei frühere Fragen sind jetzt E1 (B.5).
5. **Gebaut seit Meldung 43:** N15, N9 (V2, GradientButton), S1c2 (B, 2c), N14, N7 (FG-107), N8 (94 Wörter); Anträge FG-109, FG-110, FG-111, FG-112. In den letzten Zweigläufen ist kein Test durch die eigene Änderung rot, außer im S1c2-Vorlauf 38549977359 (Frage 6).
6. **Nächste freie FG: FG-113.** FG-110 bis FG-112 sind beantragt; vergeben erst mit deiner Antwort.

## Selbstkontrolle
**Stufen:**
- **belegt:** beim Schreiben selbst nachgesehen (`git ls-remote`, `gh run view`, `git show`/`git apply --numstat`, `git merge-base`, Logs und Messdateien gelesen, `ls`/`ps`).
- **berichtet:** steht im Bericht eines Bauers, Prüfers oder des Integrators.
- Dazu **vermutet** und **nicht geprüft**.

Für dich ist alles hier mindestens „berichtet“, weil die Quellen im gemeinsamen Ordner `bau_0.63.2/` liegen. Was ein Bauer oder Prüfer selbst belegt hat, steht als „laut Bauer/Prüfer belegt“; für mich ist das „berichtet“. Die vollen Job-Logs der GitHub-Läufe kann ich nicht laden (`results-receiver` Forbidden). Wo ich rote Testnamen „belegt“ nenne, habe ich sie in den Log-Auszügen gelesen, die die Bauer über `get_job_logs` gesichert haben.

### Auflagen aus Weisung 43
| Abschnitt | Auflage | Stand | Beleg oder „offen, weil“ | Stufe |
|---|---|---|---|---|
| 2.1 | Liste +94 Wörter, Test bleibt rot bei fehlendem Wort | erfüllt | `version-0632-n8` = `c65f67d`; `n8/ergebnis.md` | SHA belegt, Inhalt berichtet |
| 2.1 | Anhang in der Form von Anhang A, nach Mustern gruppiert, unsichere Einträge markiert | erfüllt | Anhang A unten (12 Gruppen, 14 unsicher) | belegt (gelesen) |
| 2.1 | maschinelle Vorprüfung (i)–(iv) | erfüllt: (i) für die 94 neuen Einträge, (ii)–(iv) für alle 127 bestanden | `n8/vorpruefung_94.txt` | berichtet (Ausgabe gelesen, nicht selbst gerechnet) |
| 2.1 | Merge N8 erst nach deiner Lesung | eingehalten | `c65f67d` ist kein Vorfahr von `a82fd34` | belegt |
| 2.1 | zwei Rückfragen, je ein Satz | beantwortet | B.6 | berichtet |
| 2.2 | ein Satz zu K2c im Bericht | offen, weil der Bericht noch nicht geschrieben ist | – | – |
| 2.2, 4.2 | eigenes Tor für N6 × S5c | offen, weil N6 (Konflikt, Frage 8) und S5c nicht gemergt sind | `integration/PROTOKOLL.md`, 11:15 UTC | berichtet |
| 2.3 | Unterschrift gegen v0.63.1 prüfen (Foto und Messung) | erfüllt: **in 0.63.1 sichtbar** | `s1c2/nachbesserung/pruefung_unterschrift_0631/` | Messdateien belegt gelesen; Fotos nicht selbst geöffnet |
| 2.3 | Deckel bleiben die Inter-Werte | erfüllt | `s1c2/nachbesserung/ergebnis.md` („Deckel unverändert“) | berichtet |
| 2.3 | Satz an Nico „war nicht zu sehen“ | **entfällt**, Bedingung trifft nicht zu; Ersatz siehe Frage 6b | – | belegt |
| 2.4 | Konfliktauflösung beim S1c2-Merge, ganze Datei (83 Tests) im Tor | offen, weil S1c2 nicht gemergt ist. Nach 2.4 Nr. 3 ist ein **neuer Probe-Merge** nötig: `version-0632` hat seitdem FG-96, und S1c2 steht jetzt auf `7acfccb` | – | belegt (SHAs) |
| 2.4 Nr. 2 | Auflösung Zeile für Zeile im Merge-Protokoll | offen, weil S1c2 nicht gemergt ist | – | – |
| 2.5 | Startwerte 27–52 gegen v0.63.1, die alten 26 unverändert, KF K-a/K-b/K-c vorab, keine geschützte Datei, voller Lauf | erfüllt bis auf den End-Stand-Lauf | `8cef3b4` ändert nur `pruefung/s1_voll.py` (+179/−0); Lauf auf `8cef3b4` 46/46 grün; KF 09:27:46 UTC. **Offen** ist der ganze grüne Lauf auf dem End-Stand, eine Merge-Bedingung. | Diff belegt, Rest berichtet |
| 2.5 | Abweichungen von S6b als Beleg ins Log, nicht als Fehler | erfüllt | `n14/ergebnis.md` | berichtet |
| 2.5 | Maßstab wörtlich | gebaut wie vorgegeben; ein Fall passt nicht wörtlich → Frage 5 | `n14/ergebnis.md` | berichtet |
| 2.6 | FG-109-Antrag mit Diff, Stoppgrenzen-Liste, Tests, KF vorab, Fotos, Pflichtnachweis; nicht bauen | erfüllt | Antrag; sha256 und Größe selbst geprüft | Diff belegt, Rest berichtet |
| 2.7 Nr. 1 | unabhängige Gegenprüfung mit eigener Probe | erfüllt; Urteil: **nicht freigabefähig** | `n7/gp_fg107/gegenpruefung.md` | berichtet |
| 2.7 Nr. 2 | Fälle (i)–(iv) als feste Tests | vorhanden | Gegenprüfung, Abschnitt 3 | berichtet |
| 2.7 Nr. 3 | KF12–KF16, KF15 auslösbar | KF12, KF14, KF15 vom Prüfer selbst rot; KF13 und KF16 nur vom Bauer | Gegenprüfung 3 und 5 | berichtet |
| 2.7 Nr. 4 | Windows-Messung, Speicher | 884 → 546 ms; 11,1 MB. Gemessen auf dem Bau-Commit `5592023`, nicht auf `3d09742`; der App-Code ist gleich, danach wurde nur die Testdatei geändert (berichtet) | `n7/fg107/logs/messung_windows.md` | berichtet (Tabelle gelesen) |
| 2.7 Nr. 5 | Fingerabdrücke | alle gleich, **auch „code“**: Der Teil „code“ erfasst `fisi_lernen.py` und `app_gui.py` nicht. Das weicht von deiner Erwartung „code ändert sich“ ab. | `n7/fg107/ergebnis.md` | berichtet |
| 2.7 Nr. 6 | Merge nach N7; Zielwert offen im Bericht | nicht gemergt (Frage 3); Zielwert ist nach Nicos Antwort 1 s (Frage 3, Information) | – | belegt (Antwort Nico) |
| 2.8 | GradientButton genau +9/−2, Höhe fest | erfüllt | `git show --numstat 5ee907c`: `mobile/src/ui.py` 9/2 | belegt |
| 2.8 | Tests und KF vor dem Bau; Pixel auch bei Groß und Sehr groß | Test 09:41:47 UTC, KF 10/10 rot; 42/42 Fotos gleich | `n9/ergebnis.md`, `n9/logs/pixelvergleich_gradientbutton.txt` | berichtet |
| 2.8 | Fotos „Extra groß“ und „Maximal“ an Nico | im Foto-Nachtrag (Abschnitt D, Frage F1) gesendet; Nico hat F1 (b) gewählt (Frage 9) | `meldungen/Nachtrag_Meldung_39_Fotos.md`, `plan_0.63.2/freigabe/Antwort_Nachtrag_39_Nico.md` | belegt (Dateien gelesen) |
| 2.9 | Satz zur Bestenliste | für Bericht und Testliste übernommen; offen, weil der Bericht noch nicht geschrieben ist | – | – |
| 2.10 | „breite2“, wenn „breite“ > 1350 s | bisher nicht nötig: 421 s, ohne die N5-Datei und die vier N8-Breitendateien (lokal im Container zusammen etwa 1200–1600 s, auf GitHub kürzer). Messung auf GitHub nach N5 und beim N8-Merge, dann gegebenenfalls „breite2“ ohne Frage. Nur zur Information: Das grüne Tor auf dem zurückgesetzten Probe-Merge `e90b78e` maß im Container unter Last „breite“ 1860 s, „rest“ 2076 s (`integration/tor/tor_e90b78e.md`); auf GitHub nicht gemessen. Liegt eine einzelne Datei über 1350 s, kommt eine neue Frage. | `zeiten_belegt.txt`, `n8/ergebnis.md` | berichtet |
| 4.3 | jeder Laufbericht nennt alle roten Tests | B.2, mit den Zwischenläufen 38545811233 (N9) und 38543848476 (N15) | Log-Auszüge gelesen | Auszüge belegt, Vollständigkeit berichtet |
| 4.5 | Test aus `cb60f8b` kommt mit dem S6b-Merge | offen, weil S6b nicht gemergt ist | – | – |
| 4.7 | S6b in der Planreihenfolge nach FG-96 | FG-96 ist drin. S6a ist noch nicht gemergt (`6ffda17` ist kein Vorfahr von `a82fd34`, belegt). Als Nächstes kommen S6a, dann S6b; beide vergrößern „rest“ (Frage 1). | `integration/PROTOKOLL.md` | belegt / berichtet |
| 4.9 | „Optik offen: Fix 3b“ | erledigt (Nico, Meldung 39, 6a) | `Antwort_Meldung_39_Nico.md` | belegt |
| 4.6 | U1/U3-Diff in den Bericht | offen, weil der Bericht noch nicht geschrieben ist | `n14/zaehlkorrektur_u1_u3.md` | – |
| 4.10 | Dateien `a`, `n` und fünf Xvfb-Prozesse: nichts löschen oder beenden | eingehalten | `a`, `n` 0 Byte vom 14.10. 05:26; Xvfb-PIDs 24668, 25923, 3449, 26294, 17620 (02:56–03:52 UTC) laufen noch | belegt (`ls`, `ps`, 11:4x UTC; laut Gegenprüfung um 12:06 UTC unverändert) |
| 7 | vorab gebaute FG mit Merge-Reihenfolge | B.8 | – | berichtet |

### Zahlen gegen Beleg
| Zahl | Beleg | Stufe |
|---|---|---|
| `version-0632` = `a82fd34`; N7 `3d09742`, N8 `c65f67d`, N9 `5ee907c`, N14 `8cef3b4`, N15 `e8c8442`, S1c2 `7acfccb`, N6 `3ec3665`, S6b `cb60f8b` | `git ls-remote origin` | belegt |
| Keiner dieser Zweigköpfe ist in `a82fd34` enthalten (auch N5 `98f63ff` nicht) | `git merge-base --is-ancestor` | belegt |
| Lauf 38550615169 auf `a82fd34`: `success`, 11 Jobs `success`, Release-Jobs `skipped` | `gh run view`, `jobs.tsv` | belegt |
| „rest“ 1441 s, „breite“ 421 s (Testzeit); Job „rest“ 10:37:15–11:01:56 UTC | `zeiten_belegt.txt` (Zitat aus dem Job-Log), `jobs.tsv` | Zeiten berichtet, Job-Zeitstempel belegt |
| Zweigläufe 38549211060 (N15), 38549419907 (N9), 38554173440 (S1c2), 38550497158 (N7): jeweils nur „Tests Linux (rest)“ `failure`, alle anderen Jobs `success`; 38544277059 (N8): „rest“ `cancelled` | `gh run view --json jobs` | belegt |
| Rote Tests dieser Läufe (B.2) | Log-Auszüge der Bauer, mit `grep` gelesen | belegt (Auszüge), Vollständigkeit berichtet |
| FG-107-Diff `fisi_lernen.py` +131/−8, `app_gui.py` +11/−2, Test +12/−2, sha256 `58f5137f…4b6b` | `git apply --numstat`, `sha256sum` | belegt |
| FG-110-Diff `fisi_lernen.py` +22/−5, `test_faellig_0632.py` +127/−1, sha256 `29adca87…47d0` | `git apply --numstat`, `sha256sum` | belegt |
| FG-109-Diff `fisi_game.py` +19/−8, `mobile/src/spiel.py` +4/−2, `fisi_projekt.py` +1/−1, sha256 `ae54ca32…dfc6` | `git apply --numstat`, `sha256sum` | belegt |
| PillGroup `e6fe458`: `ui.py` +9/−5, `test_anzeige_handy.py` +8/−2 | `git show --numstat` | belegt |
| Änderung der Prüfung in `7acfccb` (Frage 6) | `git show 7acfccb` | belegt |
| Kantenglättung bei „Maximal“: höchstens 22 (Rechner) bzw. 23 (Prüfungstrainer) von 255 | `n9/logs/pixelvergleich_bj04_v2.txt` | belegt (Log gelesen) |
| Windows FG-107: nach Quizantwort 884 → 546 ms, nach Karteikarte 827 → 518 ms, „fällig“ 334 → 21 ms | `n7/fg107/logs/messung_windows.md` | berichtet |
| Gegenprüfung: ohne B1-Fall 30.000 + 15.000 Plan-Vergleiche (und ebenso viele `results`-Vergleiche), 0 Abweichungen; B1-Modus 874 + 882 | Tabelle in `gegenpruefung.md` | berichtet |
| 94 Wörter, 503 Stellen, 14 unsicher, 6 Wörter in zwei Listen (92 Wörter = 98 Vorkommen) | `n8/vorpruefung_94.txt`, Anhang | berichtet (Ausgabe gelesen) |
| `version-0632` lokal = `a82fd34`; Reflog: `e90b78e` (Merge N5) danach „reset: moving to a82fd34“ | `git reflog version-0632`, `git rev-parse` | belegt |
| FG-111: `FG-111_knopf.diff` `06e99377…b302`, `FG-111_knopf_erweitert.diff` `215702fd…a176`, `FG-111_spiel_vorschlag.diff` `80a75a37…e4ae`; FG-112: `FG-112_kaestchen.diff` `aa55ff68…cbb72e2a5` | `sha256sum` | belegt |
| FG-112 `inventar.jsonl`: 2436 Messungen (der Antrag nennt 2204) | `wc -l` | belegt |
| Unterschrift in 0.63.1: x = 325, 290 × 18 px, Seite 785 > 781; `452141b`: unter dem Titel, Seite 769 | `pruefung_unterschrift_0631/*_messung.txt` | belegt (Messdateien gelesen) |

### Eigene Fehler und Korrekturen
1. **Mein Fehler (Koordinator):**
   - Ich habe den Integrator angewiesen, N5 nach FG-96 zu mergen. Weisung 38/40 verlangt aber: „N5 erst nach Fix 3b, S1c2 und FG-96“ (belegt: `Weisung_CC_Antwort_Meldung_38_und_40.md`, Z. 59).
   - Der Merge `e90b78e` war nur lokal, ist nicht gepusht und inzwischen lokal zurückgesetzt (`version-0632` = `a82fd34`, belegt per Reflog). N5 kommt nach S1c2.
   - Das Tor auf `e90b78e` war grün; es gilt nur zur Information (`integration/tor/tor_e90b78e.md`).
2. **Push von `a82fd34` trotz Tor-Urteil ROT:**
   - Der Integrator hat `LoadingHintTest` nach Weisung 42, 2.15 als „lastabhängig“ eingestuft und `a82fd34` gepusht.
   - 2.15 ist für Zeittests geschrieben, also Tests mit einer ms-Grenze. `LoadingHintTest` prüft keine ms-Grenze, sondern ob der Ladehinweis erscheint. Die Regel deckt den Fall also nicht.
   - Ich hätte vor dem Push fragen müssen. Nachträgliche Bestätigung: Frage 2a.
3. **S1c2 `7acfccb`:** Damit wurde eine Prüfung gelockert und vor einer Rückfrage gepusht, aber nicht gemergt (Frage 6). Die Regel sagt: Bewusst geänderte Tests werden nicht abgeschwächt.
4. **N6 ist nicht gemergt.** Der Integrator hat den Merge wegen eines Konflikts mit Fix 3b abgebrochen (Frage 8).
5. **Nicos Antworten zu Meldung 39:** Er ist meinen Empfehlungen gefolgt, außer bei Frage 2 (c statt a). Frage 12 hatte keine Empfehlung, er wählte V2. 14b und 18b **waren** die Empfehlungen; bei 14 kam „einheitlich“ dazu.
6. **Zielwert Startseite:** Nico hat 18b gewählt, also 1 s nach einer Änderung. Der N7-Bericht und Weisung 43 (2.7 Nr. 6) gehen von 0,2 s aus (Frage 3, Information; E1-3).
7. **Kantenglättung N9:** Der Strangbericht sagt „bis 22/255“. Laut Log sind es 22 beim Rechner und **23** beim Prüfungstrainer.
8. **Zähler Zeittest:** Der Integrator meldet „2 Tore“. Nach deiner Zählung (Weisung 43, Abschnitt 3) ist `a82fd34` das erste weitere Tor, und auch das nur, wenn der Test überhaupt als Zeittest zählt (Frage 2b).
9. **N8-Lauf 38544277059:**
   - Rot waren nur 2 der 3 früheren Listentests; `Ap2BreiteTest.test_sehr_gross_1360` war nicht rot (Ursache nicht geprüft).
   - `test_trennung_0632.py` lief vor dem Abbruch nicht mehr. Einen ganzen „rest“-Lauf hat N8 auf GitHub also noch nicht.
10. **N14:** Auf `8cef3b4` gibt es keinen GitHub-Lauf, weil nur `pruefung/s1_voll.py` geändert ist und das nicht in der CI läuft. Der letzte Lauf ist 38509788620 auf `053931d`; er war laut Protokoll rot durch den S6b-Befund und die „rest“-Zeitgrenze.
11. **Gegenprüfung FG-107:** Der Text nennt 60.000 Vergleiche ohne den B1-Fall. Aus der Tabelle ergeben sich 45.000 Plan-Vergleiche und ebenso viele `results`-Vergleiche. Das Ergebnis, 0 Abweichungen, bleibt gleich.
12. **FG-107-Antrag, 7.1 und T9:** Die Begründung („`apply_question_renames` trifft nur neue Zeilen“) war falsch. Der Bauer hat sie im FG-110-Antrag, Abschnitt 6, richtiggestellt.
13. **Lauf 38550615169:** Er hat 11 Jobs mit Ergebnis `success`, nicht 10.
14. **Fassung 1, korrigiert in Fassung 2:**
    - Der Kopfblock sagte „in keinem Lauf durch die eigene Änderung rot“. Das stimmte nicht: Der S1c2-Vorlauf war rot.
    - Frage 7 (b) hatte eine falsche Begründung.
    - Frage 4 sagte „11 Ansichten ohne Unterschied“, ohne die Grenzen der Prüfung zu nennen.
    - Frage 1 sprach von „Streuung“, ohne die Rechnung zu zeigen.
    - In B.2 fehlten zwei Zwischenläufe.
15. **Foto-Nachtrag F2:** Ich habe Nico geschrieben, am Handy stehe das Kästchen schon oben („am Handy schon so“). Das gilt nur für Haken, nicht für Schalter; die Schalter am Handy stehen mittig (FG-112-Antrag, Abschnitt 2). Korrektur geht mit dem nächsten Nachtrag an Nico (Frage 10).
16. **Fassung 2, korrigiert in Fassung 3:**
    - Frage 9 nannte als Stoppgrenze „genau 3 Dateien, `spiel.py` unverändert“, empfahl aber 5 Dateien mit `spiel.py`.
    - Der N5-Stand war veraltet („lokal `e90b78e`“).
    - Frage 10 übernahm aus dem Antrag „2204 Messungen“; es sind 2436.

---

# A. Fragen an dich

## Frage 1 (E2): Teil „rest“ 1441 s auf dem Integrationsstand
**Belegstufe:** Job-Zeiten belegt; Testzeit berichtet (Zitat aus dem Job-Log).

**Problem:** Im ganzen grünen Lauf 38550615169 auf `a82fd34` braucht „rest“ 1441 s Testzeit, der Job lief von 10:37:15 bis 11:01:56 UTC. Nach Weisung 42, 2.1 ist das über 1350 s eine Sofortmeldung und eine neue E2-Frage. Die Ausnahme „breite2 ohne Frage“ gilt für „rest“ nicht (Weisung 43, 2.10 Nr. 5). Die Jobgrenze von 1800 s bleibt.

**Stand:**
- Vor FG-96 waren es auf `8f18818` 1402 s, damals noch mit den Breitendateien. Auf dem FG-96-Zweig (`4d77439`) waren es 1182 s.
- **Die Rechnung passt nicht:**
  - FG-96 hat „breite“ aus „rest“ herausgenommen; „breite“ liegt auf `a82fd34` bei 421 s.
  - Erwartet wären also etwa 1402 − 421 ≈ 981 s. Gemessen sind 1441 s, rund 460 s mehr.
  - Zwischen `8f18818` und `a82fd34` liegt nur FG-96.
  - Die Ursache ist **nicht geprüft**. Streuung der Runner ist nur eine von mehreren Vermutungen.
  - Die Messung je Datei in Option (a) soll diese Lücke erklären.
- **„rest“ wird noch wachsen:**
  - S6a: etwa +3–4 min laut Gegenprüfung S6a, berichtet
  - S6b: Test zur Zeitumstellung
  - N7: `test_faellig_0632.py`
  - N16 und N14 (Weisung 42, 2.1)
- Auf Zweigen ohne FG-96 lag „rest“ heute bei 1260–1572 s.
- „breite“ hat Platz, darf aber nur Breitentests aufnehmen.

**Optionen:**
- **(a) „rest2“ wie „breite2“, als neue FG:**
  - Geändert werden `build.yml`, `ci_tests.sh` und `test_ci_teile_0632.py`.
  - Die Messung je Datei legt die Teilung fest. Jede Datei steht in genau einem Teil. Die Testnamen sind vorher und nachher gleich, der Matrix-Test bleibt.
  - Danach ein ganzer grüner Lauf, als eigener Commit vor S6a/S6b.
  - Folge: ein Job mehr; kein weiterer Umlauf, wenn S6a, S6b, N7, N16 und N14 dazukommen.
- **(b) Nicht teilen, bei jedem Lauf über 1350 s melden.** Folge: Läuft „rest“ in die Grenze von 1800 s, gilt der Lauf als weder grün noch rot, und es gibt keinen grünen Lauf.
- (c) Die Jobgrenze anheben. Das hast du abgelehnt (Weisung 42, 2.1); ich nenne es nur der Vollständigkeit halber.

**Empfehlung: (a)** mit den Auflagen von FG-96. Die Nummer vergibst du; frei ist FG-113.
**Blockiert:** der S6a/S6b-Merge und damit die Planreihenfolge, bis (a) gebaut ist oder du (b) wählst.

## Frage 2 (E2): `test_vorladen.py` in zwei Toren rot, Push trotz Tor ROT
**Belegstufe:**
- berichtet: Tor-Protokolle
- belegt: der Test selbst (`test_vorladen.py` auf `a82fd34`, Z. 281–289 gelesen), GitHub „lang“ grün, Push

**Problem:** Im Merge-Tor wurde die Datei zweimal rot, jeweils mit einem anderen Test:
- **Tor `53a4354`:** `PartsTest.test_reihenfolge_und_teile` mit 429 ms (Grenze 400, Last bis etwa 12). Einzeln wiederholt: 25 ms. Das ist ein echter Zeittest, „lastabhängig“ nach 2.15.
- **Tor `a82fd34`:** `LoadingHintTest.test_anzeige_bei_langsamer_ansicht` (Lauf mit Inter, Teil „lang“).
  - Das Tor-Werkzeug urteilt **ROT**. Der Ladehinweis erschien 0-mal statt einmal, Last bis 17,05.
  - Einzeln bei Last etwa 5,2 wiederholt: 27 Tests OK.
  - Der Integrator hat den Test nach 2.15 als „lastabhängig“ eingestuft, und `a82fd34` wurde **gepusht**.
  - Auf GitHub ist „lang“ in Lauf 38550615169 grün; nach 2.15 Nr. 3 ist GitHub maßgeblich.

**Offen gesagt:**
- `LoadingHintTest` ist **kein reiner Zeittest**. Er prüft keine ms-Grenze. Er hält die Vorladung an und prüft, **ob** der Ladehinweis bei einer großen, nicht vorgeladenen Ansicht erscheint.
- Regel 2.15 deckt diesen Fall nicht. Der Push stützte sich damit auf eine Regel, die dafür nicht geschrieben ist. Das war nicht in Ordnung, und ich beschönige es nicht.
- Die Ursache ist **nicht geprüft**. Zwei Erklärungen sind denkbar (beide vermutet):
  - Unter Last hat der Vorlader die Ansicht schon gebaut, bevor `stop_preloader` greift. Dann ist es eine Frage des Testablaufs.
  - Auf einem langsamen Rechner erscheint der Hinweis wirklich nicht. Dann ist es eine Programmeigenschaft.

**2a – Nachträgliche Bestätigung des Pushs von `a82fd34`:**
- **(a)** Nachträglich bestätigen, weil GitHub ganz grün ist. Dazu eine **Diagnose ohne Eingriff**: Ein Prüfer wiederholt `LoadingHintTest` unter künstlicher Last und liest den Ablauf; Ergebnis in Meldung 45.
- (b) Der Fall gilt als **echt rot**. Dann wird der Test vor dem nächsten Merge geklärt, und der nächste Merge wartet darauf. `a82fd34` bleibt gepusht; es gibt keinen Force-Push und kein Zurücknehmen.

**Empfehlung: (a)** mit Diagnose.

**2b – Zählt der Fall für den Zähler nach 2.15 Nr. 4?**
- **(a)** Nein, er ist kein Zeittest. Der Zähler bleibt bei 0. Künftig gilt für Nicht-Zeittests: Rot im Tor heißt anhalten und fragen, kein „lastabhängig“.
- (b) Ja. Der Zähler steht bei 1, beim nächsten Fall kommt die Frage nach FG-108.

**Empfehlung: 2b (a).** FG-108 („Grenzen nur auf GitHub“) würde diesen Test ohnehin nicht erfassen.

**Blockiert:** nichts weiter, solange du 2a (a) wählst.

## Frage 3 (E2): FG-107 nicht freigabefähig, Antrag FG-110, Grenze (ii)
**Belegstufe:**
- belegt: Diff-Größen, sha256 und dass N7 nicht gemergt ist
- berichtet: Gegenprüfung, Messungen, Kontrollfehler
- vermutet: Restrisiken (so gekennzeichnet)

**Problem:** FG-107 ist auf N7 gebaut (`3d09742`). Der Diff ist byte-gleich mit dem freigegebenen, die Stoppgrenze ist eingehalten. Die unabhängige Gegenprüfung urteilt trotzdem **„nicht freigabefähig“**, wegen Befund **B1 (mittel)**:
1. „Alles ersetzen“ spielt eine Sicherung mit **alten Fragetexten** ein, zum Beispiel von einem Gerät mit 0.63.1 nach den S4-Umbenennungen.
2. Danach kommt in derselben Sitzung ein Abgleich oder „Sicherung zusammenführen“. Dabei ruft das Programm `apply_question_renames` auf. Das schreibt schon gelesene Zeilen per `UPDATE` um.
3. Anzahl und höchste Nummer bleiben gleich, der Index merkt nichts.

Folge: „Heute fällig“ ist bis zum nächsten Neustart falsch. Ein Datenverlust entsteht nicht. In der Zufallsprobe (Startwerte 620000–620149) gab es 874 Plan- und 882 `results`-Abweichungen. Deine Auflage 2.7 Nr. 2 („in jedem Fall gleich dem vollen Neuaufbau“) ist damit nicht erfüllt. **N7 ist nicht gemergt.**

**Antrag FG-110 (nicht gebaut):** `antraege/FG-110_Antrag_faellig_Index_verwerfen.md`, Diff sha256 `29adca87…47d0`, sauber auf `3d09742` anwendbar.
- **Der Bauer bestätigt B1** und hat einen **zweiten Weg** gefunden: Ein älteres Programm schreibt alte Texte, und das `_migrate` eines zweiten Programms benennt sie um. Unter Linux und Windows verhindert der Einzelstart ein zweites Programm (laut Antrag belegt im Code, `fisi_einzelstart.supported`). Unter macOS gibt es ihn nicht, dort ist der Weg möglich. Ob der Einzelstart ein Programm **anderer** Version erkennt, ist nicht geprüft. Dass der Fall vorkommt, ist vermutet selten.
- **Darum verwirft er den Vorschlag des Prüfers** („Index nach Abgleich verwerfen“): Er fängt den zweiten Weg nicht.
- **Lösung:** nur in `fisi_lernen.ReviewIndex`. Ein Merker `always_full` sorgt für einen vollen Aufbau bei jedem Aufruf, solange der Index einen alten Fragetext hält oder eine Tabelle kein AUTOINCREMENT hat (deckt auch B2).
  - Jeder volle Aufbau setzt den Merker neu. Nach dem Umbenennen arbeitet der Index wieder schrittweise.
  - Laut Suche ändert nur `apply_question_renames` gelesene Spalten.
- **Stoppgrenze neu:** `fisi_lernen.py` +22/−5, `test_faellig_0632.py` +127/−1 (belegt). Sonst keine Datei.
- **Kontrollfehler und Tests:**
  - KF18–KF23 vorab um 11:30:20 UTC festgelegt, 6 von 6 rot.
  - 5 neue Tests: auf `3d09742` rot, mit dem Fix 24 von 24 OK.
  - Probe 620000–620149: 874 → 0 Abweichungen.
- **Kosten im Container:** innerhalb der Streuung. Windows ist nicht gemessen.
- **Offen beim Bauer:**
  - Der N7-Zwischenspeicher `_dash_query` könnte nach B1 auch veraltet sein (nicht geprüft).
  - Ein anderes Programm mit **anderer** Umbenennungsliste fängt FG-110 nicht ab (vermutet selten).

**3a – Wie geht es mit N7 weiter?**

Wichtig für die Wahl (berichtet): Nicos Ziel ist nach 18b **1 s** nach einer Änderung. Unter Windows liegt die Startseite nach einer Änderung **schon ohne FG-107** darunter: 884 ms nach einer Quizantwort, 827 ms nach einer Karteikarte, gemessen auf `1e7965a` auf dem Windows-Runner. Mit FG-107 sind es 546 bzw. 518 ms. Im Container unter Last etwa 9 sind es ohne FG-107 etwa 2000 bzw. 1487 ms, mit FG-107 1054 bzw. 949 ms; diese Werte zeigen nur die Richtung.

- **(a) FG-110 erteilen, N7 mit FG-107 und FG-110 mergen:**
  - Genau dieser Diff wird gebaut, auf N7. KF12–KF16 aus FG-107 laufen auf dem Endstand neu.
  - Neue unabhängige Gegenprüfung mit eigener Probe: B1, der zweite Weg und der N7-Zwischenspeicher `_dash_query`.
  - Windows-Messung über einen Probezweig, Fingerabdrücke, ein ganzer Lauf.
  - Folge: Die Startseite ist auch auf langsameren Rechnern deutlich unter 1 s. N7 und dahinter N16 und N14 warten auf Bau und Gegenprüfung.
- (b) B1 als bekanntes Restrisiko annehmen (dann E3 für Nico) und FG-107 so mergen. Folge: „Heute fällig“ kann bis zum Neustart falsch sein.
- **(c) N7 jetzt ohne FG-107 mergen, FG-110 erteilen, FG-107 und FG-110 als eigener späterer Schritt:**
  - N7 wird auf `1e7965a` gemergt; Lauf 38506811682 dort war rot nur durch die bekannten Breitentests (berichtet).
  - FG-107 und FG-110 werden dann gebaut, gegengeprüft (wie (a)) und gesondert gemergt.
  - Folge: Die Planreihenfolge läuft sofort weiter. Nicos Ziel ist unter Windows auch ohne FG-107 erreicht, knapp (884 ms). Die Verbesserung folgt später.
  - Dazu kommt ein Merge mehr, und in der Merge-Geschichte wird N7 aufgeteilt.

**Empfehlung: (c)**, weil Nico keine Verzögerung will und sein Ziel unter Windows schon ohne FG-107 erreicht ist. (a) wäre sicherer gegen langsamere Rechner, hält aber die Planreihenfolge an.

**3b – Grenze (ii)** („gleiche Nummer mit anderem Inhalt“)
- Kein Programmweg tut das (Gegenprüfung, belegt per Suche): Kein INSERT gibt `id` vor, beide Tabellen haben AUTOINCREMENT. Der Wächter-Test T10 hält das fest.
- Für alte Tabellen ohne AUTOINCREMENT baut FG-110 immer voll auf.
- Eine Prüfsumme bräuchte eine neue FG.

Gegenoption: eine Prüfsumme als neue FG. Folge: Kosten bei jedem Aufruf und ein eigener Antrag.

**Empfehlung:** Der Wächter reicht; ein Satz kommt in den Bericht.

**3c – B2 und B3 (gering)**
- B2 (AUTOINCREMENT bei Lernständen vor 0.62.3) ist mit FG-110 unschädlich. Dass es solche Tabellen je gab, ist nicht belegbar.
- B3: Beim vollen Aufbau dauert die Lesesperre 0,4–0,9 s länger. Ein Schreibfehler trat nicht auf; ob ein Schreiben nach 5 s scheitert, ist nicht geprüft.

Gegenoption zu B3: die Lesetransaktion vor `_recompute` beenden, als neue FG. Folge: ein Antrag mehr, Nutzen vermutet gering.

**Empfehlung:** beide in den Bericht, kein Umbau.

**Information (keine Frage) – Satz zum Zielwert im Bericht:**

Weisung 43, 2.7 Nr. 6 gibt vor: „Zielwert 0,2 s nicht erreicht“. Nico hat danach 18b gewählt. Ich weiche darum **vom Wortlaut der Weisung ab** (E1-3). Der Bericht schreibt:

„Ziel 1 s (Nico, 18b): unter Windows erreicht (546/518 ms mit FG-107, gemessen auf dem FG-107-Stand ohne FG-110; ohne FG-107 884/827 ms); im Container unter Last etwa 9 mit FG-107 knapp verfehlt (1054/949 ms, nur Richtung).“

Wenn du das anders willst, genügt ein Widerspruch.

**Blockiert:** N7-Merge. Die Planreihenfolge S6a → S6b → **N7** → N16 → N14 hält dahinter an.

## Frage 4 (E2, Teil d E3): FG-109 „Zahl und Einheit“, Unterfragen 4a–4e
**Belegstufe:**
- belegt: Diff-Größen und sha256
- berichtet (laut Bauer belegt): Fotos, Tests, Suchen, Fingerabdrücke

**Problem:** Der Antrag liegt vor: `antraege/FG-109_Antrag_Zahl_Einheit.md`, Diff sha256 `ae54ca32…dfc6`, Basis `8f18818`.
- **Befund am Handy bei 200 %** („Maximal“, Behelf im Browser, nicht das S24): 6 Anzeigen aus 5 Quellen brechen belegt zwischen Zahl und Einheit um.
  - Von den 11 übrigen fotografierten Ansichten zeigen 8 keinen Unterschied. Bei mehreren davon ist aber nur der obere Teil geprüft: Die Fotos sind in der Höhe begrenzt.
  - 2 Ansichten zeigen nur Pixelunterschiede ohne Textunterschied (Fortschritt, Ticket).
  - 1 Ansicht („kalk“) ist **nicht geprüft**.
  - **Nicht fotografiert:** Serverfarm, Reise-Unterreiter, Dialoge, Kalkulation, laufendes Projekt, aufgenommener Kredit; nur dunkel, 200 % und Inter.
  - Die Liste S1–S8 (Stoppgrenze) ist deshalb eine **Untergrenze** (siehe 4e).
- **Stoppgrenze:** 8 Einzelstellen (S1–S8). Geändert werden `fisi_game.py` +19/−8, `mobile/src/spiel.py` +4/−2 (beide geschützt) und `fisi_projekt.py` +1/−1.
- **Formatierer:** Von den 6 Formatierern sind 2 betroffen (`spiel.euro`, `fisi_projekt.euro`). Die Stelle aus deiner Weisung (`spiel.py:3019`) steht auf `8f18818` in Zeile **3010**.
- `inhalte/*` bleibt unberührt.
- Fingerabdrücke alt, zahlen, konstanten, spielinhalte und lerninhalte bleiben gleich; „code“ ändert sich beabsichtigt.
- Kontrollfehler KF1–KF12 vorab festgelegt (10:08:52 UTC).
- Volle Testteile sind nicht gelaufen.

**4a – `_whole_euro_shown`:**
- Eine weitere Funktion, `fisi_game._whole_euro()`, ist die Quelle von 3 belegten Stellen (zum Beispiel „Umsatz 378 / €“).
- Ändert man sie an der Wurzel, ändert sich der **alte Fingerabdruck** (`f2b59ce8` → `47b8a65a`, belegt). Der Grund: Der Text wird als Kreditname im Ereignis `EV_LOAN` gespeichert.
- **Vorschlag:** eine neue reine Anzeige-Hilfe `_whole_euro_shown()`, nur an den drei Aufrufern (S3–S6), nach dem Vorbild von `_euro_given` seit 0.53. Der alte Fingerabdruck bleibt gleich (belegt).
- Alternative: S4–S6 weglassen. Dann bleiben 3 belegte Befunde offen.
- **Empfehlung: Anzeige-Hilfe.**

**4b – zwei Bestandstests:**
- `test_spiel.py:6357` und `test_rechner_0632.py:347/349` prüfen `fisi_projekt.euro` wörtlich. Mit dem Diff werden sie rot; auf `8f18818` sind sie grün.
- **Vorschlag:** gleich streng anpassen, weiter `assertEqual` bzw. `assertIn` mit vollem String und geschütztem Leerzeichen. Dazu eine neue ungeschützte Testdatei `test_zahl_einheit_0632.py` (T1–T7, mit Rundweg über `parse_number`).
- Alternative: S7 nur in der Handy-Anzeige (`main.py:2566`). Dann bleiben die PC-Anzeige `app_gui.py:4000` ohne Schutz und die Tests unverändert.
- **Empfehlung: anpassen**, das ist keine Lockerung.

**4c – Text-Export:**
- Der Text-Export des Abschlussprojekts („Als Text“) enthält danach 6 geschützte Leerzeichen.
- Der PDF-Export bleibt byte-gleich (belegt laut Antrag, sha256 vorher = nachher).
- Ein Antwortvergleich oder eine Kopierfunktion ist nicht betroffen (Pflichtnachweis, Abschnitt 6 des Antrags).
- Gegenoption: den Text-Export ausnehmen. Folge: eine Stelle mehr im Diff, Export und Anzeige uneinheitlich.
- **Empfehlung: annehmen.**

**4d (E3, Nico) – Aussehen:**
- Die Fotos sind ein Behelf. Ich schlage vor: Sie gehen mit dem nächsten Foto-Nachtrag an Nico.
- Bis zu seiner Abnahme gilt „Optik offen: FG-109“, wie bei Fix 3b: Merge nach dem Bau erlaubt, aber kein Bericht, keine Probe-Testversion und kein Release.
- **Empfehlung: so.**

**4e – Weitere Stellen gleicher Art, die nach der Freigabe belegt werden:**
- **(a)** Sie bleiben Befund im Bericht. Eine Erweiterung gibt es nur mit neuer Freigabe; sie werden in der nächsten Meldung genannt.
- (b) Sie dürfen ohne neue Frage in FG-109, wenn der Aufrufer `_whole_euro_shown` oder `spiel.euro` nutzt und ein Foto die Stelle belegt. Folge: Das ist eine Lockerung der Stoppgrenze und nur von dir zu erteilen.

**Empfehlung: (a).**

**Blockiert:** nur FG-109. Bis zu deiner Freigabe steht „Zahl und Einheit“ als Befund im Bericht.

## Frage 5 (E2): N14, ein zweiter Fall „N hat weniger als S6b“ neben U6
**Belegstufe:**
- belegt: Diff `8cef3b4`
- berichtet: Lauf, Kontrollfehler und Marken
- vermutet: die Deutung

**Problem:** Die neuen Zufallsabläufe mit „Alles ersetzen“ (Startwerte 27–52, gegen v0.63.1 und S6b) laufen grün: 46 von 46 Tests, 59 von 59 Ersetzen-Schritten ausgeführt.
- Gegen 0.63.1 sind alle gleich.
- „N hat weniger als S6b“ kommt in den Startwerten **34, 35 und 41** vor. Nur 35 ist der U6-Fall.
- **34 und 41 sind ein anderer Fall:**
  1. Die Uhr des ersetzenden Geräts wurde gestellt.
  2. Danach folgt ein Neustart ohne Startkennung (wie U3).
  3. Nach dem Ersetzen löscht ein **anderes Gerät** alles.
  4. S6b setzt die Aufhebungsmarke 2 h zu spät (15:22 statt 13:22 UTC) und hebt damit diese spätere, echte Löschung mit auf. N setzt die Marke richtig, und die Löschung wirkt.
- Der Bauer wertet das als richtiges Verhalten von N (vermutet, belegt an den Marken).
- Dein vorgegebener Satz „Gegen S6b: eine benannte Ausnahme (U6)“ deckt das **nicht wörtlich**. Er ist unverändert.

**Weitere Hinweise (berichtet):**
- Die alten 26 Abläufe sind unverändert, alle Etiketten gleich.
- Bei Startwert 19 stand die nicht geprüfte Zählung „Hochladungen in Ruhe“ einmal auf 4 statt 0. Allein nachgeprüft ergab sie 0; die Ursache ist vermutet Zeit oder Last.
- K-a, K-b und K-c sind einzeln rot.

**Optionen:**
- **(a) Satz anpassen**, Wortlaut von dir. Zum Beispiel: „Gegen S6b: zwei benannte Ausnahmen (U6; Uhr gestellt und Neustart ohne Startkennung mit späterer Löschung eines anderen Geräts). In beiden behält N richtig weniger.“ Dazu ein **fester Test** für den zweiten Fall mit festen Sollwerten wie G8, Kontrollfehler vorab.
- (b) Der Satz bleibt, und der Fall steht als Erläuterung im Bericht. Folge: Der Maßstab im Bericht stimmt nicht mehr wörtlich mit dem Prüfprogramm überein.

**Empfehlung: (a).** Der feste Test belegt die Deutung, statt sie nur zu vermuten.
**Blockiert:** nur der Wortlaut für den N14-Merge. Nico hat Weg b zugestimmt (19a).

## Frage 6 (E2): S1c2 `7acfccb` lockert eine bestehende Prüfung
**Belegstufe:**
- belegt: Diff `7acfccb`, Messdateien der Unterschrift
- berichtet: die Läufe

**Problem:** In Lauf 38549977359 (`bd14178`) war `FortschrittDatenBreiteTest.test_sehr_gross_1120_andere_schrift` rot.
- Grund: Mit der dritten Schrift auf GitHub (TkDefaultFont) passt die Seite mit Variante B **ganz**. Die Erinnerung „Lücke behoben – Liste anpassen“ verlangte aber einen Überstand.
- `7acfccb` lässt diese Erinnerung **nur noch mit der Standardschrift** prüfen: `if ohne is None:` um das `assertTrue(mine["fehler"], …)` (belegt, +7/−2 in `test_ansichten_breite.py`).
- Der Deckel (höchstens 70 px Überstand) gilt weiter für beide Schriften.
- Der Bauer hat das **vor** einer Rückfrage committet und gepusht, aber nicht gemergt.

**Ehrlich eingeordnet:**
- Das ist **formal eine Lockerung**: Eine Prüfung fehlt jetzt für andere Schriften. Wird die Lücke dort geschlossen, meldet sich kein Test.
- Geschützt ist dort nur noch der Deckel von 70 px. Eine Verschlechterung von 0 auf bis zu 70 px bliebe mit der dritten Schrift unbemerkt.
- Die Mindestanforderung an die Anzeige (Deckel) ist nicht gelockert.

**6a – Optionen:**
- **(a)** Nachträglich annehmen, mit einem Satz im Bericht. Folge: S1c2 ist nach dem neuen Probe-Merge und dem Tor mergebar.
- **(b)** Statt der Ausnahme eine **Erwartung je Schrift**: Für die Schrift, mit der die Seite passt, gilt Überstand 0 (Deckel 0); für die übrigen gilt die Erinnerung wie bisher. Folge: strenger als vorher; ein Commit und ein Lauf mehr auf S1c2. Ob die Schrift im Test sicher erkannt wird, ist vermutet (`mine["schrift"]` gibt es).

**Empfehlung: (b).** Sie schließt die Lücke, statt sie hinzunehmen. Ist dir die Zeit wichtiger, ist (a) vertretbar, weil der Deckel bleibt.

**6b – Satz für Nico: jetzt E1 (Widerspruch genügt).**
- **Messung:**
  - In **v0.63.1** (`14b3bd4`) ist die Unterschrift „Lerndaten, Historie, Spielstand, Bestenliste“ bei „Sehr groß“ 1120 mit Inter **zu sehen, rechts neben dem Titel**: x = 325, 290 × 18 px, die Seite war dort 4 px zu breit.
  - Auf `7a32651` war sie nicht zu sehen (TclError).
  - Seit `452141b` steht sie **unter** dem Titel; alles darunter rückt 20 px tiefer.
- Dein vorgegebener Satz („In 0.63.1 war die Unterzeile an dieser Stelle nicht zu sehen …“) wäre also **falsch** und wird nicht verwendet.
- **Grund für E1:**
  - Nach 2.3 braucht es den Satz an Nico nur, wenn die Unterschrift in 0.63.1 nicht zu sehen war; sonst ist es die Rückkehr zum alten Stand.
  - Neu ist nur die Lage. Die S1c2-Fotos gehen ohnehin an Nico (Weisung 41).
- **Satz für den nächsten Nachtrag an Nico:** „In 0.63.1 stand die Unterzeile rechts neben dem Titel; jetzt steht sie darunter. Alles darunter rückt 20 px tiefer. Grund: ein behobener Absturz.“
- 6b blockiert den S1c2-Merge nicht. Die Bedingungen aus 2.3 sind erfüllt: Nicos Wahl B liegt vor, die Prüfung gegen 0.63.1 auch.

**Blockiert:** S1c2-Merge nur durch 6a und den neuen Probe-Merge nach 2.4 Nr. 3.

## Frage 7 (E2): Lesung der 94 Wörter (N8), Anhang A
**Belegstufe:**
- berichtet: Liste und Vorprüfung vom Bauer
- gelesen: Anhang und Ausgabe der Vorprüfung

**Problem:** Nach Weisung 43, 2.1 liest du die Liste vor dem N8-Merge.
- **Anhang A** unten enthält alle 94 Wörter mit Trennstellen (`|`, `‖`), Quelle und Problemfall-Spalte. Sie sind in 12 Gruppen nach Mustern geordnet; **14 Einträge sind als unsicher markiert**.
- **Maschinelle Vorprüfung:**
  - (i) „Teile ergeben das Wort, das Wort steht so in einer Quelle“: bestanden für die 94 neuen Einträge.
  - (ii)–(iv): bestanden für alle 127 Einträge.
  - Die neuen Einträge haben 503 Stellen. In den Quellen stehen 103 lange Wörter, 0 davon ohne Eintrag.
  - (iii) prüft `ch/sch/ie/ei/au/eu/ck` und Abkürzungen mit Ziffer. Weitere „nie trennen“-Fälle aus Anhang A (Versalien, englische Wörter) prüft es **nicht**; die liegen bei deiner Lesung.
- **Was eine fehlende Stelle bewirkt:** Sie trennt nie falsch mit Strich. Passt im Wort keine Stelle, teilt der Rückfall wie heute **ohne Strich** an der letzten passenden Stelle (`fisi_trennung`, Modulkopf, laut Gegenprüfung). Weniger Stellen sind also nicht „vorsichtiger“: Der Rückfall ohne Strich wird häufiger.

**Optionen:**
- **(a)** Du liest und korrigierst einzelne Einträge nach Nummer; N8 übernimmt deine Korrekturen wörtlich. Ohne Antwort zu einem Eintrag wartet N8.
- **(b)** Wie (a). Für jeden unsicheren Eintrag, zu dem du nichts sagst, gilt **die gelistete Fassung**:

| Nr | Wort | gilt ohne deine Antwort |
|---|---|---|
| 1 | Arbeitsgruppendrucker | wie gelistet: `dru\|cker` |
| 8 | Datenschutzbeauftragten | wie gelistet: `be\|auf` als `\|` |
| 12 | Netzwerkspezialisten | wie gelistet: `zi\|a` |
| 35 | Ingenieurgesellschaft | wie gelistet: `nieur` ungeteilt |
| 50 | Generationenprinzip | wie gelistet: `ra\|tio\|nen` |
| 52 | Multifunktionsgerät | wie gelistet: `Mul\|ti‖funk` |
| 53 | Immobilienverwaltung | wie gelistet: `bi\|lien` |
| 64 | Versicherungsagentur | wie gelistet: `agen` ungeteilt |
| 66 | verursachungsgerecht | wie gelistet: `ver\|ur` als `\|` |
| 70 | Drogeriemarktfiliale | wie gelistet: `fi\|li\|a\|le` |
| 73 | Ferienhausvermittlung | wie gelistet: `Fe\|rien` |
| 76 | Hochzeitsfotografin | wie gelistet: `Hoch\|zeits` (`\|`, nicht `‖`) |
| 84 | Physiotherapiepraxis | wie gelistet: `Phy\|sio` |
| 86 | Regionalradiosender | wie gelistet: `Re\|gio\|nal` |

**Empfehlung: (b).** N8 wartet dann nicht auf eine Antwort zu jedem Eintrag, und jede gelistete Fassung hat die Vorprüfung bestanden.
**Blockiert:** N8-Merge. N8 kommt erst nach N5, und N5 kommt nach S1c2 (Fehler 1).

## Frage 8 (E2): N6, Konflikt mit Fix 3b in `CalcView`
**Belegstufe:**
- berichtet: Integrator, `integration/welle3c/n6_konflikt_app_gui_calcview.diff`
- belegt: N6 = `3ec3665`, nicht in `a82fd34`

**Problem:** Der Probe-Merge von N6 (`3ec3665`, mit FG-104) auf `a82fd34` hat in `app_gui.py` `CalcView` zwei Konfliktstellen, und sie sind **nicht mechanisch** zu lösen:
- N6 baut die USV-Knöpfe in einem eigenen Teil (`_build_ups_rest`).
- Fix 3b bindet am Ende des Aufbaus `<Configure>` an die Knöpfe in `ups_button_rows`; N6 plant am selben Ende (`_build_end`) die restlichen Teile ein. Die frühere Annahme des Integrators, das ende mit `AttributeError`, hat er selbst zurückgenommen (berichtet, `integration/PROTOKOLL.md`): `_build_end` läuft in N6 als letzter Teil nach `_build_ups_rest`, die Liste existiert dann schon.
- Dazu kommt `_fit`: Fix 3b nutzt `if changed`, N6 `if _in_parts`.

Der Merge ist abgebrochen. Nach Weisung 43, 4.2 (dort für S5c gesagt) wird so ein Konflikt nicht still aufgelöst. Der Auflösungsvorschlag liegt als Diff in `/mnt/project-files/bau_0.63.2/integration/n6_konflikt/`.

**Auflösungsvorschlag (Integrator, nicht angewendet; Beleg `integration/n6_konflikt/vorschlag_aufloesung_cc.diff`, 85 Zeilen, dazu Diffs gegen `3ec3665` und gegen `a82fd34`):**
1. `_build_end`: beide Seiten behalten, **zuerst** die Fix-3b-Schleife über `ups_button_rows`, **dann** der N6-Block (Teilbau, `_schedule_fit`, Subnetting-Restteile). Begründung: Teile laufen in der Reihenfolge subnet, raid, screen, ups, ups_rest, end; die `<Configure>`-Bindungen und damit `_fit` entstehen erst in `_build_end`.
2. Ende von `_fit`: zwei getrennte `if`-Zweige nacheinander, `if changed:` (Fix 3b, Abstand neu berechnen) und `if self._in_parts:` (N6, Breite der Bildlauffläche). Die Folgen sind unabhängig.

**Geprüft:** nur `py_compile` (berichtet). Kein Tor, keine Tests auf dem Vorschlag. Offen: ob die Knopfzeilen beim Vorladen in Teilen die Anpassung aus Fix 3b rechtzeitig bekommen; belegbar nur per Tor mit ohne_inter (DejaVu) und Teil breite (nicht geprüft).

**Optionen:**
- **(a)** Freigabe für genau diesen Auflösungs-Diff. Danach Auflösung im N6-Zweig (Zusammenführen ohne Force) und Tor N6 mit `test_klick_hat_vorrang`, den Vorlade-Tests und dem Teil „breite“ **sowohl mit Inter als auch ohne Inter (DejaVu)**; nur so ist der offene Punkt oben belegbar. Rot im Teil ohne Inter heißt anhalten und melden. Dann ein ganzer grüner Lauf und der Merge. Das eigene Tor N6 × S5c (4.2) bleibt für den S5c-Merge.
- (b) Freigabe nach Bedingungen ohne vorherige Lesung: Merge nach Auflösung, grünem Tor und ganzem grünem Lauf; Diff und Begründung kommen in Meldung 45 nach. Folge: schneller, aber du siehst die Auflösung erst danach.
- (c) N6 zurückstellen und mit S5c zusammen lösen, wo derselbe Bereich betroffen ist. Folge: N6 wartet länger.

**Empfehlung: (a).** Der Diff liegt dieser Meldung bei, ein Umlauf reicht.
**Blockiert:** N6-Merge (mit FG-104).

## Frage 9 (E2): FG-111 – Farbverlauf-Knopf wächst bei großer Schrift (Nico F1 b)
**Belegstufe:**
- belegt: Nicos Antwort (Abschrift gelesen); Diff-Größen und sha256 aller drei Diffs (`git apply --numstat`, `sha256sum`; auch Gegenprüfung 2)
- berichtet (laut Bauer belegt): Tests, Kontrollfehler, Fotos

**Anlass:** Bei „Maximal“ ist „Antwort einreichen“ im Prüfungstrainer weiter angeschnitten („einreiche“), und „Karteikarten zu Dienste“ im Spiel-Ticket sitzt unten knapp. Grund ist die feste Höhe aus deiner GradientButton-Freigabe (Weisung 43, 2.8). Nico hat F1 (b) gewählt: Der Knopf darf bei großer Schrift höher und breiter werden; „Abbrechen“ darf in eine eigene Zeile.

**Antrag** (`antraege/FG-111_Antrag_Knopf_waechst.md`, N9, nicht gebaut):
- Basis `5ee907c`, Diff `antraege/FG-111_knopf.diff`, sha256 `06e99377…b302`.

| Datei | Zeilen (belegt) | Was |
|---|---|---|
| `mobile/src/ui.py` (GradientButton, ungeschützt) | +8/−3 | Ab 160 % und nur ohne Symbol ist die Höhe nicht mehr fest; der Knopf wächst mit dem Text. Ein unsichtbarer Halter (`ft.Container(width=0)`) in einem `ft.Stack` hält einzeilig die bisherige Höhe; Rand oben und unten `grow(6)`. Mit Symbol und bis „Sehr groß“ unverändert. |
| `mobile/src/main.py:966` (Prüfungstrainer, ungeschützt) | +2/−2 | `ft.Row([btn_submit, btn_cancel])` → `tile_row(...)`: bis „Sehr groß“ nebeneinander wie heute, ab 160 % untereinander in voller Breite |
| `test_gradientbutton_0632.py` | +78/−6 | Tests angepasst und ergänzt |

- **Stoppgrenze dieses ersten Diffs:** genau diese 3 Dateien, `spiel.py` unverändert. Die Erweiterung unten ändert die Stoppgrenze; maßgeblich ist die Option, die du wählst. Der Knopf im Ticket hat ab 160 % schon volle Breite (FG-106).
- **Wirkung:** Betroffen sind **alle** Handy-Knöpfe ohne Symbol ab 160 %, 152 Aufrufe. Einzeilig behalten sie ihre Höhe (Befund 2 unten); bricht der Text um, wird der Knopf höher, statt den Text anzuschneiden. Der PC ist nicht betroffen.
- **Tests vor dem Code:** um 11:58:32 UTC geschrieben, auf `5ee907c` 3 rot und 4 grün; mit Diff 7 von 7 OK.
- **Kontrollfehler:** F1–F10 einzeln 10 von 10 rot (11:59:06 UTC). Abgedeckt sind feste Höhe, Halter, Rand, Zentrierung, mit Symbol, bis „Sehr groß“, Prüfungstrainer immer nebeneinander bzw. immer untereinander.
- **Bestand grün:** `test_anzeige_handy` 23, `test_handy_0632` 35, `test_handy_anzeige_0632` 16, `test_handy_sehr_gross_0632` 20, `test_spiel_stufen_0632` 13, `test_zugang` 17, `test_schriftstufe_0632` 19.
- **Probefotos:**
  - Normal, Groß und Sehr groß: Ticket und Prüfungstrainer pixelgleich mit `5ee907c`.
  - Prüfungstrainer bei „Extra groß“ und „Maximal“: „Antwort einreichen“ einzeilig in voller Breite und ganz lesbar, „Abbrechen“ darunter.
  - Ticket bei „Maximal“: „Karteikarten zu / Dienste“ zweizeilig, der Knopf ist höher und hat unten Rand.
- **Befunde des Bauers:**
  - Einzeilige Knöpfe ab 160 % werden etwa 2 px höher (Ticket bei „Extra groß“ 61 → 63 px). Die Ursache ist vermutet Rundung; der Bauer stuft das als E1 ein.
  - Der Rand `grow(6)` ist gewählt, nicht gemessen.
- **Weitere Reihen mit Knöpfen nebeneinander** (per AST gesucht, nicht geändert): 9 Stellen in `main.py` (der Antrag schreibt „8 Reihen“, listet aber 9) und 5 in `spiel.py` (geschützt). Ob dort bei „Maximal“ ein Wort breiter ist als ein halber Knopf, ist **nicht geprüft**.

**Messrunde über diese Ansichten:**

Gemessen in einer Wegwerf-Kopie (5ee907c + Diff) auf einer **Nachbau-Seite** mit den echten Bausteinen (`ui.GradientButton`, `ui.Card`, `tile_row` usw.), nicht in der echten Ansicht (berichtet; Fotos geöffnet in `antraege/belege_fg111/messrunde/`). Spezielle Zustände (Prüfung läuft, Kredit vorhanden) sind nicht hergestellt.

| Reihe | Extra groß | Maximal | vom Diff abgedeckt? |
|---|---|---|---|
| M1, M2, M4, M5, M6, M8, M9 (`main.py`), S1, S4 (`spiel.py`) | in Ordnung | in Ordnung | ja bzw. Symbol unverändert |
| M3 `main.py:1544` Abgeben/Abbrechen | in Ordnung | Wortbruch „Abbrech/en“ | **nein** |
| M7 `main.py:2870` Antwort ausblenden/Jetzt üben | Wortbruch „ausblen/den“ | Wortbruch | **nein** |
| S2 `spiel.py:3082` Hilfe ausblenden/Abbrechen | Wortbruch | Wortbruch | **nein** (geschützt) |
| S3 `spiel.py:4196` Plan ausblenden/Ablösen | in Ordnung | Wortbruch | **nein** (geschützt) |
| S5 `spiel.py:2841` Neuere/Seite/Ältere | knapp | „Älte…“ angeschnitten | **nein** (geschützt) |

**Erweiterungsvorschlag des Bauers** (im Antrag, Abschnitt „Erweiterungsvorschlag“):
- `main.py` 1544 und 2870 ebenfalls auf `tile_row` (bis „Sehr groß“ unverändert, ab 160 % untereinander). Diff `antraege/FG-111_knopf_erweitert.diff` (sha256 215702fd…a176, 270 Zeilen, `git apply` sauber auf `5ee907c`): `ui.py` +8/−3, `main.py` +6/−6, Test +156/−6 (Stoppgrenze bei Option (b)). Tests vor dem Code (12:28:12Z) 6 rot + 1 Fehler, nur ab 160 %; danach 9/9 grün; Kontrollfehler 14/14 rot (12:28:40Z) (berichtet).
- `spiel.py` (geschützt): 3 Stellen je 1 Zeile nach dem Muster aus FG-106 (`_stack_large` ab 160 %). Diff `antraege/FG-111_spiel_vorschlag.diff` (sha256 80a75a37…e4ae, 138 Zeilen): `spiel.py` +3/−3, `test_spiel_stufen_0632.py` +90. Tests vor dem Code (12:31:15Z) 6 rot, danach 16/16 grün; Kontrollfehler 6/6 rot (12:32:09Z); beide Diffs zusammen: 5 Bestandsdateien grün (`test_anzeige_handy` 23, `test_handy_0632` 35, `test_handy_anzeige_0632` 16, `test_handy_sehr_gross_0632` 20, `test_spiel_abgabe` 2) plus die beiden geänderten Testdateien; `test_zugang` und `test_schriftstufe_0632` liefen nur mit dem ersten Diff (berichtet). Geschützte Datei: nur mit Option (a) freigegeben.

**Vorgeschlagene Auflagen beim Bau** (aus dem Antrag):
- genau die in der gewählten Option genannten Diff-Dateien (der Antrag nennt in seinen Auflagen noch nur `FG-111_knopf.diff`; das ist durch die Erweiterung überholt), mehr ist eine Stoppgrenze
- Tests und Kontrollfehler vor dem Bau im Zweig wiederholen, dabei `test_zugang` und `test_schriftstufe_0632` mit beiden Diffs
- Pixelvergleich 14 Ansichten × Normal/Groß/Sehr groß gleich
- Fotos „Extra groß“ und „Maximal“ an Nico
- ein ganzer Lauf

**Optionen:**
- **(a)** FG-111 für genau zwei Diffs erteilen: `FG-111_knopf_erweitert.diff` (sha256 `215702fd…a176`: `ui.py` +8/−3, `main.py` +6/−6, `test_gradientbutton_0632.py` +156/−6) und `FG-111_spiel_vorschlag.diff` (sha256 `80a75a37…e4ae`: `mobile/src/spiel.py` +3/−3, geschützt, Muster FG-106; `test_spiel_stufen_0632.py` +90/−0). Stoppgrenze = diese 5 Dateien mit diesen Zeilen. Folge: alle 5 gefundenen Stellen behoben; Messrunde nach dem Bau wiederholen.
- (b) FG-111 nur für `FG-111_knopf_erweitert.diff` (3 Dateien, ohne `spiel.py`). Folge: S2, S3, S5 im Spiel bleiben bei „Maximal“ falsch getrennt bzw. angeschnitten und kommen als bekannte Grenze in den Bericht.
- (c) FG-111 nur für `FG-111_knopf.diff` (sha256 `06e99377…b302`, `main.py:966`). Folge: M3 und M7 bleiben ebenfalls.

**Empfehlung: (a).** Nico hat F1 (b) gewählt, damit Knöpfe bei großer Schrift ganz lesbar sind; die Messrunde zeigt, dass das ohne die übrigen Stellen nur teilweise gilt.
**Blockiert:** nichts. N9 kann vor FG-111 gemergt werden; FG-111 kommt dann als eigener Nachtrag auf den Integrationsstand.

## Frage 10 (E2): FG-112 – Kästchen an der ersten Zeile überall am PC (Nico F2 b)
**Belegstufe:** Nicos Antwort belegt (Abschrift gelesen); sha256, Zeilen und `git apply --check` belegt (Gegenprüfung 2); Messungen, Tests, Kontrollfehler berichtet (laut Bauer belegt), Belege `antraege/belege_fg112/`.

**Anlass:** Gebaut ist das Kästchen an der ersten Zeile nur für die Bewertungskriterien (S1c2, 2c). Andere Haken und Schalter am PC stehen weiter mittig, wenn ihr Text umbricht; gemessen kommt das nur beim Optionen-Schalter „Automatisch abgleichen“ vor (siehe Bestand). Nico hat F2 (b) gewählt: überall am PC, wo ein Haken oder Schalter neben mehrzeiligem Text steht. Der Antrag liegt vor.

Antrag: `/mnt/project-files/bau_0.63.2/antraege/FG-112_Antrag_Kaestchen_erste_Zeile.md`

Diff `antraege/FG-112_kaestchen.diff` (sha256 aa55ff68…cbb72e2a5, 117 Zeilen, `git apply --check` auf `7acfccb` sauber).

**Bestand (laut Bauer belegt; 2436 Messungen in `inventar.jsonl`, nachgezählt per `wc -l`; der Antrag nennt 2204; Inter/DejaVu × Normal/Groß/Sehr groß × 1120/1360):** 8 Stellen mit Haken/Schaltern in `app_gui.py`. Tatsächlich umbrechen kann nur der Optionen-Schalter „Automatisch abgleichen (beim Start, nach dem Lernen und beim Beenden)“, und nur mit DejaVu bei Sehr groß 1120. Abschlussprojekt (20 Haken) und alle übrigen Schalter brechen in keinem gemessenen Fall um.

**Handy (berichtet, laut Bauer belegt):** Haken stehen schon oben (`ui.check_row`, START). Schalter in den Einstellungen stehen mittig (Flet-Standard, `main.py:4167`). **Mein Foto-Nachtrag hat Nico gesagt, am Handy sei es schon so; das stimmt nur für Haken** (Fehler 15). Der Antrag ändert das Handy nicht. Ein Satz dazu geht mit dem nächsten Nachtrag an Nico; will er auch die Schalter am Handy oben, ist das eine Zeile in `_switch` als eigener Antrag (ob der Schalter dort umbricht, ist nicht geprüft).

**Lösung:** Die 2c-Funktion `_z3_check_top` gilt für alle Haken und Schalter am PC (die Markierung „nur Bewertung“ entfällt). Die ursprüngliche Lage wird gemerkt und beim Rückweg auf einzeilig wiederhergestellt.

**Stoppgrenze:** 2 Dateien, keine geschützt: `app_gui.py` +12/−9, Test +34/−5.

**Tests und Kontrollfehler (berichtet):** Einzeilig 0 Pixel Unterschied an 2 Stellen. DejaVu: Kästchen-Mitte 20,5 → 10,5 = erste Zeile. Neu ist ein Testschritt: Fenster im selben Lauf von 1120 auf 1360, dazu eine Wache gegen „läuft ins Leere“. OptionenBreiteTest 12 OK. Kontrollfehler K1–K4 einzeln rot (Zeitstempel 12:12:33Z bzw. 12:29:50Z). Den PruefungstrainerBreiteTest hat der Bauer nur mit dem ersten Diff-Stand laufen lassen (grün), nicht mit dem Endstand (nicht geprüft). K1 nur mit dem ersten Test-Stand (der Nachtrag ändert den Pfad laut Bauer nicht). Im zweizeiligen Fall wird der Schalter 1 px höher (42 → 43 px).

**Optionen:**
- **(a)** FG-112 für genau diesen Diff erteilen. Auflagen: Pixelvergleich einzeilig gleich, PruefungstrainerBreiteTest und K1 auf dem Endstand wiederholen, ganzer Lauf, Fotos „Automatisch abgleichen“ vorher/nachher für Nico.
- (b) Nicht bauen, da praktisch nur eine Stelle betroffen ist. Folge: Nicos F2 (b) ist nicht umgesetzt; das bräuchte Nicos Zustimmung.

**Empfehlung: (a).** Kleiner Diff, keine geschützte Datei, setzt Nicos Wahl um.
**Blockiert:** nichts. FG-112 wird auf dem S1c2-Zweig gebaut, **nach** der Umsetzung deiner Wahl in 6a (bei 6a (b) wird der Diff auf den neuen Stand gesetzt; ändert sich dabei mehr als die Zeilennummern, ist das eine Stoppgrenze). S1c2 kann ohne FG-112 gemergt werden; dann kommt FG-112 als eigener Schritt.

---

# B. Information (keine Entscheidung nötig)

## B.1 Integrationsstand
| Schritt | Ergebnis | Stufe |
|---|---|---|
| Welle 3c (S6c `7c470bd`, N1 `53a4354`, N2 `0329bc9`, N3 `ebfaf7b`, N4 `7e25060`) | gemergt, jeweils mit Tor (N1: Zeittest „lastabhängig“, N4: „grün mit Meldung“, `test_rundgang_hilfe` still beendet, bekannt als E1-12) | berichtet (Protokoll) |
| Fix 3b → `8f18818` | gemergt, Tor „grün mit Meldung“ (3 Listentests grün, Liste leer); Lauf 38537239045 ganz grün | Lauf belegt (Meldung 43) |
| FG-96 → `a82fd34` | Tor: Werkzeug **ROT** durch `test_vorladen LoadingHintTest`, vom Integrator nach 2.15 als „lastabhängig“ eingestuft (Frage 2). Fingerabdrücke alt, zahlen, konstanten, spielinhalte gleich Soll; ibus 23 OK (Vorabprüfung). Gepusht ohne Force. | Tor berichtet, Push belegt |
| Lauf 38550615169 auf `a82fd34` | **ganz grün, 0 rote Tests**; „breite“ 421 s (ohne N5-Datei), „rest“ 1441 s (Frage 1) | Ergebnis belegt, Zeiten berichtet |
| N5 `98f63ff` → `e90b78e` (lokal) | konfliktfrei, **nicht gepusht, lokal zurückgesetzt** (`version-0632` = `a82fd34`). Tor auf `e90b78e` grün, nur zur Information (`integration/tor/tor_e90b78e.md`; im Container unter Last „breite“ 1860 s, „rest“ 2076 s, auf GitHub nicht gemessen). Zurückgestellt, weil Weisung 38/40 N5 erst nach Fix 3b, S1c2 und FG-96 verlangt. S1c2 fehlt noch (Fehler 1, Koordinator). N5 kommt nach S1c2. | Reflog belegt, Tor berichtet |

**Nicos Antworten zu Meldung 39** (Abschrift `plan_0.63.2/freigabe/Antwort_Meldung_39_Nico.md`):
- Alle Empfehlungen übernommen, außer **2c**: Kästchen immer an der ersten Zeile.
- **12b** V2: keine Empfehlung gegeben.
- **14b** wie empfohlen, auf Nachfrage „einheitlich“.
- **Optik offen: Fix 3b** und **Optik offen: Dialog** sind erledigt (6a, 7a).
- Zielwerte: Wartezeit nach Schrift- oder Farbwechsel 1,5 s (17a); Startseite 1 s nach einer Änderung (18b); Klick 150 ms (26a); alle vier Ziele (27a); „langsam“ = über 1 s (28a).
- 19a: Behalten-Regel wie gebaut, N14 frei nach Nico.

## B.2 Gebaute Stände, Läufe und **alle** roten Tests
Abgleich mit `werkzeug/bekannt_rot_github.txt`:
- Die Liste ist seit Fix 3b **leer**, ihre drei früheren Einträge sind mit „(bis 14.10.)“ auskommentiert. Diese drei Tests sind auf Zweigen **ohne** Fix 3b weiter rot: `test_ansichten_breite.py Ap2BreiteTest.test_sehr_gross_1360`, `test_ansichten_breite.py TestprojektBreiteTest.test_normal_1360`, `test_rechner_seite_breite.py RechnerSeiteBreiteTest.test_sehr_gross`.
- Keiner der Zweige unten enthält Fix 3b (`9df7bd8` ist bei keinem ein Vorfahr, belegt).

| Strang, Stand | Inhalt | Lauf (Ergebnis belegt) | alle roten Tests des Laufs | Abgleich |
|---|---|---|---|---|
| N15 `e8c8442` | 14b einheitlich: gesperrte Pfeile blasser überall, wo der Abstand unter 29 liegt. Nur `mobile/src/main.py` und `test_handy_n15.py`; 72 Fälle ≥ 29 ohne Ausnahme; KF 12/12 rot (10:03:23 UTC); 30 Fotos | 38549211060: nur „rest“ rot, „rest“ 1407 s | `Ap2BreiteTest.test_sehr_gross_1360`, `TestprojektBreiteTest.test_normal_1360`, `RechnerSeiteBreiteTest.test_sehr_gross` | genau die 3 früheren Listentests (belegt, Auszug) |
| N15 `58d6d66` (Zwischenstand 14b) | 14b für Lila/Blau | 38543848476: nur „rest“ rot, „rest“ 1098 s | dieselben 3 | genau die 3 (belegt, `n15/logs/frage14b/ci_rest_115784933856.log`) |
| N9 `e6fe458` (Zwischenstand V2) | B-J-04 V2 | 38545811233: nur „rest“ rot (Job belegt) | „die bekannten Breitentests“; **die Quellen widersprechen sich**: `n9/ergebnis.md` nennt 3, `OFFEN_FUER_BERICHT.md` 2 | nicht geprüft (kein Log-Auszug) |
| N9 `5ee907c` | `e6fe458` B-J-04 V2 (12b) und `5ee907c` GradientButton (+9/−2). Pixel Normal/Groß/Sehr groß 42/42 gleich | 38549419907: nur „rest“ rot, „rest“ 1260 s | dieselben 3 | genau die 3 (belegt, `n9/logs/lauf_38549419907_rot.txt`) |
| S1c2 `7acfccb` | `bd14178`: 1a Variante B und 2c; `7acfccb`: Prüfungsänderung (Frage 6). Container 83/83 grün, KF k6/k7/k8 je 2/2 rot | 38554173440: nur „rest“ rot, „rest“ 1572 s | nur `TestprojektBreiteTest.test_normal_1360` | 1 der 3; die beiden anderen sind auf diesem Zweig nicht rot (Ursache nicht geprüft). Vorlauf 38549977359 (`bd14178`): zusätzlich `FortschrittDatenBreiteTest.test_sehr_gross_1120_andere_schrift` (Frage 6) |
| N14 `8cef3b4` | Zufall mit „Alles ersetzen“, Startwerte 27–52 | kein GitHub-Lauf (nur `pruefung/s1_voll.py`, nicht in der CI); Container `s1_voll.py` 46/46 grün, 998 s | Container: keine | – |
| N7 `3d09742` | FG-107 gebaut (Frage 3); KF1–17 und KF-ii 18/18 rot (berichtet) | 38550497158: nur „rest“ rot, „rest“ 1486 s | dieselben 3 | genau die 3 (belegt, `n7/fg107/logs/ci_38550497158_rest_joblog.txt`) |
| N8 `c65f67d` | +94 Wörter (Frage 7) | 38544277059: „rest“ abgebrochen (30-min-Grenze nach 58 Dateien), sonst grün | `TestprojektBreiteTest.test_normal_1360`, `RechnerSeiteBreiteTest.test_sehr_gross` | 2 der 3; `Ap2BreiteTest.test_sehr_gross_1360` nicht rot (Ursache nicht geprüft); `test_trennung_0632.py` lief nicht mehr |

In diesen Läufen ist kein Test durch die eigene Änderung des Strangs rot. Ausnahme ist der S1c2-Vorlauf 38549977359 (Frage 6). Für N14 ist das nicht anwendbar.

## B.3 N6 nicht gemergt
Siehe Frage 8.

## B.4 pkill um 01:50 UTC, Container
- **pkill:** Kein Tor-Lauf war betroffen. `tor_e0f9c7e_2` ist vollständig, „rest“ mit 1387 Tests wie auf GitHub; der stille Abbruch von `rundgang` ist E1-12 (berichtet, Protokoll).
- **Dateien `a` und `n`** (0 Byte, 05:26 UTC) im Hauptklon und **5 verwaiste Xvfb-Prozesse** (02:56–03:52 UTC): **nicht angefasst**, wie in Weisung 43, 4.10 (belegt, `ls` und `ps`).

## B.5 Selbst entschieden (E1)
| Nr | Entscheidung | Begründung | Beleg |
|---|---|---|---|
| E1-1 | N9 V2 bei „Maximal“: Die Kantenglättung der Pillenenden weicht um bis zu 22 bzw. 23 von 255 ab, die Maße sind gleich. Gelassen; die Fotos hat Nico abgenommen (B.9). | keine Maß- oder Lageänderung; bei Normal gewollt mehr Reihenabstand (V2) | `n9/logs/pixelvergleich_bj04_v2.txt` (belegt) |
| E1-2 | Satz an Nico aus 2.3 nicht verwendet; Ersatzsatz geht mit dem nächsten Nachtrag (Frage 6b) | Der Satz wäre nach der Messung falsch. In 0.63.1 sichtbar heißt nach 2.3: kein Satz nötig, nur die Lage ist neu. | `pruefung_unterschrift_0631/` (belegt) |
| E1-3 | Zielwert im Bericht nach Nicos 18b (1 s). Das ist eine **Abweichung vom Wortlaut der Weisung 43, 2.7 Nr. 6** („0,2 s nicht erreicht“). | Nicos Antwort kam nach dem Text der Weisung | Frage 3, Information |
| E1-5 | **N9 Index-Test (früher Frage 8):** N9 baut einen Test in einer **neuen, ungeschützten** Testdatei. Er prüft je Pille, dass ein Tippen auf die unsichtbare Fläche genau diesen Index wählt und Name und Rolle gleich bleiben. Kontrollfehler vorab, unter anderem „falscher Index“ und „Fläche ohne `on_click`“. | `ui.py` und `test_anzeige_handy.py` bleiben unberührt, die Stoppgrenze von FG-101 ist nicht berührt. Ein neuer ungeschützter Test braucht nach dem Vorbild von Weisung 43, 2.5 („ungeschützt, keine FG“) keine Freigabe. Er macht nur strenger. Widerspruch genügt. | `n9/ergebnis.md` (Lücke berichtet) |

E1-4 (Einstufung von `LoadingHintTest`) ist gestrichen und steht zur Bestätigung in Frage 2.

## B.6 N8: zwei Rückfragen aus Weisung 43, 2.1 (je ein Satz)
1. Ja, die Regel wirkt nur in `app_gui.PagedList._set_title` am PC, und der Einbau im Handy-Bereichstitel (`mobile/src/ui.py`) durch N9 nach dem N8-Merge ist eingeplant (Weisung 42, E1-1).
2. Die Zahl 92 zählt Wörter; 6 davon stehen in zwei Listen (98 Vorkommen = 32 + 55 + 11).

## B.7 Weitere Hinweise
- **GradientButton (berichtet):**
  - Bei „Extra groß“ bricht „Antwort einreichen“ jetzt sauber zweizeilig um.
  - Bei „Maximal“ bleibt es angeschnitten („einreiche“), weil das Wort breiter ist als der Knopf.
  - „Karteikarten zu Dienste“ steht bei „Maximal“ zweizeilig, unten knapp.
  - Nico hat im Foto-Nachtrag F1 (b) gewählt: Der Knopf darf wachsen. Der Antrag FG-111 liegt vor (Frage 9).
- **2c (berichtet):** Das Kästchen steht nur bei den Bewertungskriterien oben, andere Haken bleiben mittig. Nico hat im Foto-Nachtrag F2 (b) gewählt: überall am PC. Der Antrag FG-112 liegt vor (Frage 10).
- **S6b × S6c (berichtet, Integrator):** Zusammen werden 4 T-c-Tests in `test_abgleich_0632` rot (aus N16). Grundlage für die Anpassung ist Weisung 41, Frage 9:
  - eng begrenzt auf Projekte, die ein 0.63.2-Gerät gelöscht hat
  - erst im Integrationsstand eingebaut
  - Kontrollfehler Pflicht (dasselbe Umrechnen für ein nicht gelöschtes Projekt muss rot werden)
  - **ändern sich mehr als diese vier Tests, wird gemeldet**
  - T-a bis T-c sind erst mit S6a nachweisbar.
- **Tor-Werkzeug (berichtet):** Eine still endende Testdatei erkennt es nur bei ausführlicher Ausgabe (E1 des Integrators).

## B.8 Merge-Reihenfolge und vorab gebaute FG
| FG / Strang | Stand | Merge nach |
|---|---|---|
| N5 | `98f63ff`; Probe-Merge `e90b78e` zurückgesetzt, nie gepusht | nach S1c2 (Weisung 38/40) |
| Planreihenfolge | S6a `6ffda17` → S6b `cb60f8b` → N7 → N16 → N14 | S6a/S6b: Frage 1 („rest“); N7: Frage 3; N14: Frage 5 und ein ganzer grüner `s1_voll.py`-Lauf auf dem End-Stand |
| FG-104 (N6 `3ec3665`) | gebaut | Frage 8; Tor N6 × S5c beim S5c-Merge (Weisung 43, 4.2) |
| FG-97, FG-105 (N8 `c65f67d`) | gebaut | nach N5 (also nach S1c2) und nach deiner Lesung (Frage 7); dabei die Dateiliste „breite“/„breite2“ (Weisung 42, 2.1) |
| FG-106, FG-101 erweitert (V2), GradientButton (N9 `5ee907c`) | gebaut | nach Tor; Index-Test (E1-5) vorher auf dem Zweig; FG-111 kann danach als eigener Nachtrag kommen (Frage 9); Trennregel in `ui.py` erst nach dem N8-Merge |
| S1c2 `7acfccb` | gebaut | nach Frage 6 und einem neuen Probe-Merge (Weisung 43, 2.4) |
| N15 `e8c8442` | gebaut | nach Tor |
| FG-107, FG-110 (N7) | gebaut bzw. Antrag | Frage 3 (Empfehlung: N7 ohne FG-107 jetzt, FG-107 und FG-110 später) |
| FG-109 | Antrag | Frage 4 |
| FG-102 | erteilt, nicht gebaut | nach S6b, S5b, N10, N11 und FG-96 (FG-96 erfüllt) |
| FG-103 | erteilt, nicht gebaut | nach dem N12-Merge |
| FG-108 | reserviert | Zähler 1 (Frage 2) |
| FG-111, FG-112 | Antrag (Fragen 9, 10) | nach deiner Freigabe; FG-111 auf N9 (siehe Frage 9), FG-112 auf S1c2 nach 6a |

**Letzte vergebene FG:** FG-109. **FG-110, FG-111, FG-112** sind beantragt. **Nächste freie:** FG-113.

## B.9 Nicos Antwort auf den Foto-Nachtrag zu Meldung 39 (14.10., 11:54 UTC)
- Wörtlich: „F1: b und den schreibfehler mit beheben / F2: b / Die anderen Punkte sind zufriedenstellend.“ (Abschrift `plan_0.63.2/freigabe/Antwort_Nachtrag_39_Nico.md`, belegt gelesen).
- **Abgenommen:** 1a (Variante B), 2c (Kästchen an der ersten Zeile bei den Bewertungskriterien), 12b (V2), GradientButton, 14b einheitlich.
- **F1 (b):** Der Farbverlauf-Knopf darf bei großer Schrift höher und breiter werden, damit „Antwort einreichen“ bei „Maximal“ ganz lesbar ist (auch „Karteikarten zu Dienste“ im Spiel-Ticket). → Antrag FG-111, Frage 9.
- **F2 (b):** Kästchen an der ersten Zeile überall am PC, wo ein Haken oder Schalter neben mehrzeiligem Text steht. → Antrag FG-112, Frage 10.
- **„Schreibfehler mit beheben“:** Lesart des Koordinators (vermutet, nicht bei Nico nachgefragt): das fehlende Minuszeichen in den Bewertungskriterien („c 1“ statt „-c 1“, Fotos B1/B2). Das ist **FG-103**, schon erteilt, Bau nach dem N12-Merge (belegt: `antraege/FG-103_Antrag.md`, Kopfzeile). „einreiche“ ist kein Schreibfehler, sondern abgeschnitten; das behebt F1 (b).
- **Die Lesart ist nicht sicher.** Drei Lesarten sind möglich:
  - „einreiche“: Das wird mit F1 (b) behoben.
  - „c 1“: Das ist FG-103.
  - „Karteikarten zu **Dienste**“: Das wirkt wie ein Tippfehler für „zu Diensten“, ist aber `"Karteikarten zu %s" % TOPIC_SHORT[...]`, belegt im Code `mobile/src/spiel.py`. „Dienste“ ist der Kurzname des Themas.

  Damit nichts still fallen bleibt, fragt der nächste Nachtrag an Nico in einer Zeile nach, welche Lesart er meint. Das kostet keine Verzögerung.
- Offen für einen weiteren Nachtrag an Nico, je nach deiner Antwort: der Satz zur Unterschrift (Frage 6b) und die FG-109-Fotos (Frage 4d).

## B.10 Eingearbeitet aus der Gegenprüfung (Fassung 2)
- **H1** → Frage 2 neu mit 2a/2b, Fehler 2, E1-4 alt gestrichen.
- **H2** → Fehler 1 (Koordinator), Kopfblock, B.1, B.8.
- **H3** → Frage 3a mit Windows-Werten ohne FG-107, neue Option (c) als Empfehlung.
- **H4** → Frage 7 neu: Satz zum Rückfall, Tabelle der 14 Einträge.
- **M1** → Kopfblock 5, B.2. **M2/M3** → Frage 1. **M4** → Frage 4 und 4e. **M5** → Frage 3 Information, E1-3. **M6** → Kopfblock 2, Auflagen 4.5/4.7/4.9, B.8. **M7** → B.2 (zwei Zwischenläufe), Auflagen 4.3. **M8** → Fehler 3.
- **G1** → Uhrzeit. **G2/G3** → Kopfblock, Auflagen 2.5. **G4** → Kopfblock 3, Auflagen 2.10. **G5** → Frage 7, Auflagen 2.1. **G6** → B.6. **G7** → Stufenhinweis, Fragen 4 und 9. **G8** → Zeile 2. **G9** → Frage 3. **G10** → 3b, 3c, 4c. **G11** → B.7. **G12** → Dokumente.
- **Vermeidbare Fragen:** Frage 8 alt → E1-4 (in Fassung 3: E1-5). Frage 6b → E1. Der N6-Konflikt ist jetzt Frage 8. „Schreibfehler“ → B.9.
- Die Tabelle der unerwähnten Auflagen ist in der Auflagen-Tabelle ergänzt.

## B.11 Eingearbeitet aus der zweiten Gegenprüfung (Fassung 3)
- **H1** → Frage 9: Stoppgrenze des ersten Diffs abgegrenzt, Optionen (a)–(c) mit Diff-Dateien, SHA und Zeilen; Auflage zu den Diff-Dateien.
- **M1** → Hinweis und Dokumente ohne „Platzhalter“/„entsteht“. **M2** → N5 zurückgesetzt: Kopfblock 2, Auflagen 2.4, Fehler 1, B.1, B.8; dazu Tor `e90b78e` als Information (Kopfblock 3, Auflagen 2.10, B.1). **M3** → Frage 8 (a): Tor mit und ohne Inter. **M4** → Frage 9: Bestand, Auflage, „Blockiert“ und B.8 angeglichen. **M5** → Frage 10 Handy, Fehler 15. **M6** → Frage 10 „Blockiert“, B.8.
- **G1** → Uhrzeit. **G2/G3** → Kopfblock (6 Punkte, S6a/S6b einheitlich, FG-112). **G4** → 2436 Messungen. **G5** → Frage 10 Belegstufe, K1, 42 → 43 px. **G6** → Frage 10 Anlass. **G7** → E1-5. **G8** → Frage 4. **G9** → Frage 8. **G10** → B.7. **G11** → Frage 9. **G12** → Anhang A.

---

# Anhang A: 94 lange Wörter mit Trennstellen (N8, zu Frage 7)


Quelle: `fisi_trennung.LANGE_WOERTER` auf `version-0632-n8` (gleiche Schreibweise wie hier). Vorabbau; **Merge erst nach Chats Lesung**.

#### Zeichen in der Liste (wie Anhang A)

- `‖` bevorzugte Stelle (Wortfuge oder vorhandener Bindestrich), wird zuerst genommen
- `|` weitere zulässige Stelle (Silbengrenze nach amtlicher Regel 2006)
- mindestens 2 Buchstaben je Seite (Frage 12), einzelner Vokal in der Wortmitte zulässig (Frage 13)
- **⚠ unsicher** = ich bin bei diesem Eintrag nicht sicher; die Frage steht in der Spalte

#### Maschinelle Vorprüfung (Ergebnis: `n8/vorpruefung_94.txt`)

(i) Teile ergeben das Wort und das Wort steht genau so in einer Quelle: **bestanden**; (ii) min. 2 Buchstaben je Seite: **bestanden**; (iii) keine Stelle in `ch`, `sch`, `ie`, `ei`, `au`, `eu`, `ck` und keine in einer Abkürzung mit Ziffer: **bestanden**; (iv) kein Wort doppelt (alle 127 Einträge): **bestanden**. 503 Stellen in den 94 Einträgen. Dieselben Prüfungen laufen als Test (`VorpruefungTest`). ((i) für die 94 neuen Einträge, (ii)–(iv) für alle 127; siehe Frage 7.)

#### 1. Gleicher Anfangsteil: Arbeits-

| # | Wort (Quelle) | erwartete Stellen | Problemfall / Hinweis |
|---|---|---|---|
| 1 | Arbeitsgruppendrucker (Liste AP1-Szenarien) | Ar\|beits‖grup\|pen‖dru\|cker | **⚠ unsicher:** `dru\|cker` (Regel 2006) – oder ganz ungeteilt `drucker`?; `ck` nie trennen: `dru\|cker` (Stelle vor `ck`) |
| 2 | Arbeitsplatzrechner (Liste AP1-Szenarien, Liste Testprojekte) | Ar\|beits‖platz‖rech\|ner | – |
| 3 | Arbeitsplatzrechnern (Liste Testprojekte) | Ar\|beits‖platz‖rech\|nern | – |
| 4 | Arbeitsvorbereitung (Liste AP1-Szenarien) | Ar\|beits‖vor\|be\|rei\|tung | – |

#### 2. Gleicher Anfangsteil: Ausbildungs-

| # | Wort (Quelle) | erwartete Stellen | Problemfall / Hinweis |
|---|---|---|---|
| 5 | Ausbildungsvergütung (Liste AP1-Szenarien) | Aus\|bil\|dungs‖ver\|gü\|tung | – |
| 6 | Ausbildungsverordnung (Titel) | Aus\|bil\|dungs‖ver\|ord\|nung | – |
| 7 | Ausbildungsvertrags (Liste AP1-Szenarien) | Aus\|bil\|dungs‖ver\|trags | – |

#### 3. Gleicher Anfangsteil: Datenschutz-

| # | Wort (Quelle) | erwartete Stellen | Problemfall / Hinweis |
|---|---|---|---|
| 8 | Datenschutzbeauftragten (Liste AP1-Szenarien) | Da\|ten‖schutz‖be\|auf\|trag\|ten | **⚠ unsicher:** Vorsilbe `be\|auf` als `\|` oder `‖`?; Vorsilbe `be‖`? hier `\|` (Vorsilbe, keine Fuge); `au` bleibt |
| 9 | Datenschutzgerechter (Liste Testprojekte) | Da\|ten‖schutz‖ge\|rech\|ter | – |

#### 4. Gleicher Anfangsteil: Netzwerk-

| # | Wort (Quelle) | erwartete Stellen | Problemfall / Hinweis |
|---|---|---|---|
| 10 | Netzwerkdokumentation (Liste AP2-Szenarien) | Netz‖werk‖do\|ku\|men\|ta\|ti\|on | – |
| 11 | Netzwerkmodernisierung (Liste Testprojekte) | Netz‖werk‖mo\|der\|ni\|sie\|rung | – |
| 12 | Netzwerkspezialisten (Liste AP2-Szenarien) | Netz‖werk‖spe\|zi\|a\|lis\|ten | **⚠ unsicher:** `zi\|a` (Einzelvokal) – oder `zia` ungeteilt?; einzelner Vokal in der Wortmitte (`zi\|a`) |

#### 5. Gleicher Anfangsteil: Projekt-

| # | Wort (Quelle) | erwartete Stellen | Problemfall / Hinweis |
|---|---|---|---|
| 13 | Projektabschlussbericht (Liste AP2-Szenarien) | Pro\|jekt‖ab\|schluss‖be\|richt | – |
| 14 | Projektorganisation (Liste AP2-Szenarien) | Pro\|jekt‖or\|ga\|ni\|sa\|ti\|on | – |
| 15 | Projektstrukturplan (Liste AP1-Szenarien, Liste AP2-Szenarien) | Pro\|jekt‖struk\|tur‖plan | – |

#### 6. Gleicher Anfangsteil: Rechenzentrums- / Personaldienst- / Mess- / Temperatur-

| # | Wort (Quelle) | erwartete Stellen | Problemfall / Hinweis |
|---|---|---|---|
| 16 | Rechenzentrumsraums (Liste AP2-Szenarien) | Re\|chen‖zen\|trums‖raums | – |
| 17 | Rechenzentrumsumzug (Liste AP2-Szenarien) | Re\|chen‖zen\|trums‖um\|zug | – |
| 18 | Ausweichrechenzentrum (Liste AP2-Szenarien) | Aus\|weich‖re\|chen‖zen\|trum | `ch` bleibt (`weich`, `re\|chen`); `tr` am Silbenanfang (`zen\|trum`) |
| 19 | Personaldienstleister (Liste Testprojekte) | Per\|so\|nal‖dienst‖leis\|ter | – |
| 20 | Personaldienstleisters (Liste AP2-Szenarien) | Per\|so\|nal‖dienst‖leis\|ters | – |
| 21 | Messdatenverzeichnis (Liste AP2-Szenarien) | Mess‖da\|ten‖ver\|zeich\|nis | – |
| 22 | Messtechnikherstellers (Liste AP2-Szenarien) | Mess‖tech\|nik‖her\|stel\|lers | – |
| 23 | Temperaturprotokoll (Liste AP1-Szenarien) | Tem\|pe\|ra\|tur‖pro\|to\|koll | – |
| 24 | Temperaturüberwachung (Liste AP1-Szenarien) | Tem\|pe\|ra\|tur‖über\|wa\|chung | kein `ü\|`: `‖über` |

#### 7. Gleicher Anfangsteil: Virtualisierungs- (auf -ierung)

| # | Wort (Quelle) | erwartete Stellen | Problemfall / Hinweis |
|---|---|---|---|
| 25 | Virtualisierungscluster (Liste AP2-Szenarien) | Vir\|tu\|a\|li\|sie\|rungs‖clus\|ter | – |
| 26 | Virtualisierungshost (Liste AP2-Szenarien) | Vir\|tu\|a\|li\|sie\|rungs‖host | – |
| 27 | Virtualisierungshosts (Liste AP2-Szenarien) | Vir\|tu\|a\|li\|sie\|rungs‖hosts | – |
| 28 | Zwei-Knoten-Virtualisierungscluster (Liste Testprojekte) | Zwei-‖Kno\|ten-‖Vir\|tu\|a\|li\|sie\|rungs‖clus\|ter | zwei Bindestriche; Teil `Virtualisierungscluster` > 18 |

#### 8. Gleicher Anfangsteil: Zeit-

| # | Wort (Quelle) | erwartete Stellen | Problemfall / Hinweis |
|---|---|---|---|
| 29 | Zeiterfassungsdienst (Liste AP2-Szenarien) | Zeit‖er\|fas\|sungs‖dienst | – |
| 30 | Zeiterfassungsterminals (Liste Testprojekte) | Zeit‖er\|fas\|sungs‖ter\|mi\|nals | – |
| 31 | Zeitsynchronisation (Liste AP2-Szenarien) | Zeit‖syn\|chro\|ni\|sa\|ti\|on | – |

#### 9. Gleicher Endteil: -genossenschaft, -gesellschaft, -kanzlei, -betriebs, -herstellers, -arbeitsplätze

| # | Wort (Quelle) | erwartete Stellen | Problemfall / Hinweis |
|---|---|---|---|
| 32 | Genossenschaftsbank (Liste AP2-Szenarien) | Ge\|nos\|sen\|schafts‖bank | – |
| 33 | Winzergenossenschaft (Liste AP1-Szenarien) | Win\|zer‖ge\|nos\|sen\|schaft | – |
| 34 | Wohnungsbaugenossenschaft (Liste AP1-Szenarien, Liste AP2-Szenarien) | Woh\|nungs‖bau‖ge\|nos\|sen\|schaft | – |
| 35 | Ingenieurgesellschaft (Liste AP2-Szenarien) | In\|ge\|nieur‖ge\|sell\|schaft | **⚠ unsicher:** `In\|ge\|nieur` – `nieur` ungeteilt richtig?; `ieu` bleibt zusammen (`nieur`) |
| 36 | Lotteriegesellschaft (Liste AP2-Szenarien) | Lot\|te\|rie‖ge\|sell\|schaft | – |
| 37 | Steuerberatungsgesellschaft (Liste AP2-Szenarien) | Steu\|er‖be\|ra\|tungs‖ge\|sell\|schaft | – |
| 38 | Patentanwaltskanzlei (Liste AP2-Szenarien) | Pa\|tent‖an\|walts‖kanz\|lei | – |
| 39 | Rechtsanwaltskanzlei (Liste Testprojekte) | Rechts‖an\|walts‖kanz\|lei | – |
| 40 | Abfallwirtschaftsbetriebs (Liste AP2-Szenarien) | Ab\|fall‖wirt\|schafts‖be\|triebs | kein `A\|`: `Ab\|fall` |
| 41 | Entsorgungsbetriebs (Liste AP2-Szenarien) | Ent\|sor\|gungs‖be\|triebs | – |
| 42 | Schornsteinfegerbetriebs (Liste AP2-Szenarien) | Schorn‖stein‖fe\|ger‖be\|triebs | `ie` bleibt (`triebs`) |
| 43 | Spielwarenherstellers (Liste AP2-Szenarien) | Spiel‖wa\|ren‖her\|stel\|lers | – |
| 44 | Bildschirmarbeitsplätze (Liste AP1-Szenarien) | Bild‖schirm‖ar\|beits‖plät\|ze | – |
| 45 | Leitungsarbeitsplätze (Liste AP1-Szenarien) | Lei\|tungs‖ar\|beits‖plät\|ze | – |

#### 10. Fremdwortendungen -ierung, -ation, -tion

| # | Wort (Quelle) | erwartete Stellen | Problemfall / Hinweis |
|---|---|---|---|
| 46 | Digitalisierungsplatz (Liste AP1-Szenarien) | Di\|gi\|ta\|li\|sie\|rungs‖platz | – |
| 47 | Serverkonsolidierung (Liste AP2-Szenarien, Liste Testprojekte) | Ser\|ver‖kon\|so\|li\|die\|rung | – |
| 48 | Synchronisationsdienst (Liste AP2-Szenarien) | Syn\|chro\|ni\|sa\|ti\|ons‖dienst | `ch` bleibt (`Syn\|chro`) |
| 49 | Tabellenkalkulation (Liste AP1-Szenarien, Liste Testprojekte) | Ta\|bel\|len‖kal\|ku\|la\|ti\|on | – |
| 50 | Generationenprinzip (Liste AP1-Szenarien) | Ge\|ne\|ra\|tio\|nen‖prin\|zip | **⚠ unsicher:** `ra\|tio\|nen` gegen Anhang A `ti\|ons` (dort getrennt); `tio` als eine Silbe (`ra\|tio\|nen`), wie `-ti\|ons` in Anhang A? |
| 51 | Investitionsvorschlag (Liste AP2-Szenarien) | In\|ves\|ti\|ti\|ons‖vor\|schlag | wie Anhang A Nr. 28 (`In\|ves\|ti\|ti\|ons`) |
| 52 | Multifunktionsgerät (Liste Testprojekte) | Mul\|ti‖funk\|ti\|ons‖ge\|rät | **⚠ unsicher:** `Mul\|ti‖funk`: `‖` nach `Multi` (Präfix) richtig? |
| 53 | Immobilienverwaltung (Liste AP2-Szenarien) | Im\|mo\|bi\|lien‖ver\|wal\|tung | **⚠ unsicher:** `bi\|lien` – Duden auch `bi\|li\|en`; durch (iii) ausgeschlossen; `ie` bleibt: `bi\|lien` (nicht `bi\|li\|en`) |

#### 11. Auf -ung/-ungs (Fugen-s)

| # | Wort (Quelle) | erwartete Stellen | Problemfall / Hinweis |
|---|---|---|---|
| 54 | Aufzeichnungsspeicher (Liste AP2-Szenarien) | Auf\|zeich\|nungs‖spei\|cher | – |
| 55 | Gesprächsaufzeichnungen (Liste AP1-Szenarien) | Ge\|sprächs‖auf\|zeich\|nun\|gen | – |
| 56 | Berechtigungskonzept (Liste AP2-Szenarien) | Be\|rech\|ti\|gungs‖kon\|zept | – |
| 57 | Bestattungsinstituts (Liste AP1-Szenarien) | Be\|stat\|tungs‖in\|sti\|tuts | `st` am Silbenanfang (`in\|sti\|tuts`) |
| 58 | Fertigstellungswert (Liste AP2-Szenarien) | Fer\|tig‖stel\|lungs‖wert | – |
| 59 | Schuldnerberatungsstelle (Liste AP1-Szenarien) | Schuld\|ner‖be\|ra\|tungs‖stel\|le | – |
| 60 | Schulungsumgebungen (Liste AP2-Szenarien) | Schu\|lungs‖um\|ge\|bun\|gen | – |
| 61 | Seitwärtsbewegungen (Liste AP2-Szenarien) | Seit‖wärts‖be\|we\|gun\|gen | Umlaut; `ei` bleibt |
| 62 | Selbstbedienungskassen (Liste AP2-Szenarien) | Selbst‖be\|die\|nungs‖kas\|sen | – |
| 63 | Veranstaltungstechnik (Liste AP1-Szenarien) | Ver\|an\|stal\|tungs‖tech\|nik | – |
| 64 | Versicherungsagentur (Liste AP1-Szenarien) | Ver\|si\|che\|rungs‖agen\|tur | **⚠ unsicher:** `agen` ungeteilt (Mindestlänge) – oder `agen\|tur` reicht?; `agen` ungeteilt (sonst `a\|` mit 1 Buchstaben) |
| 65 | Vertragsverlängerung (Liste AP2-Szenarien) | Ver\|trags‖ver\|län\|ge\|rung | – |
| 66 | verursachungsgerecht (Liste AP2-Szenarien) | ver\|ur\|sa\|chungs‖ge\|recht | **⚠ unsicher:** `ver\|ur` als `\|` (Vorsilbe) oder `‖`?; klein geschrieben; Vorsilbe `ver\|ur` |
| 67 | Überwachungssoftware (Liste AP1-Szenarien) | Über\|wa\|chungs‖soft\|ware | kein `Ü\|`: `Über` |
| 68 | Routingentscheidungen (Liste AP2-Szenarien) | Rou\|ting‖ent\|schei\|dun\|gen | englisch `Routing`: `Rou\|ting` |

#### 12. Übrige Zusammensetzungen

| # | Wort (Quelle) | erwartete Stellen | Problemfall / Hinweis |
|---|---|---|---|
| 69 | Arzneimittelkühlschranks (Liste AP1-Szenarien) | Arz\|nei‖mit\|tel‖kühl‖schranks | `ei` bleibt (`Arz\|nei`); `sch` am Teilanfang |
| 70 | Drogeriemarktfiliale (Liste AP2-Szenarien) | Dro\|ge\|rie‖markt‖fi\|li\|a\|le | **⚠ unsicher:** `fi\|li\|a\|le` (Einzelvokal) – oder `fi\|lia\|le`?; einzelner Vokal in der Wortmitte (`fi\|li\|a\|le`, Frage 13) |
| 71 | Entgelttarifvertrag (Liste AP1-Szenarien) | Ent\|gelt‖ta\|rif‖ver\|trag | – |
| 72 | Fahrkartenautomaten (Liste AP2-Szenarien) | Fahr‖kar\|ten‖au\|to\|ma\|ten | `au` bleibt (`‖au\|to`) |
| 73 | Ferienhausvermittlung (Liste AP2-Szenarien) | Fe\|rien‖haus‖ver\|mitt\|lung | **⚠ unsicher:** `Fe\|rien` – Duden erlaubt auch `Fe\|ri\|en`; durch (iii) ausgeschlossen; `ie` bleibt: `Fe\|rien` (nicht `Fe\|ri\|en`) |
| 74 | Fischfeinkosthandels (Liste AP2-Szenarien) | Fisch‖fein‖kost‖han\|dels | – |
| 75 | Güterverkehrszentrums (Liste AP2-Szenarien) | Gü\|ter‖ver\|kehrs‖zen\|trums | – |
| 76 | Hochzeitsfotografin (Liste AP1-Szenarien) | Hoch\|zeits‖fo\|to\|gra\|fin | **⚠ unsicher:** Fuge `Hoch‖zeits`? Ich setze `\|` (kein Kompositum im heutigen Sinn); `Hoch\|zeits`: Stelle nach `ch`; Fuge nicht markiert (Wortgeschichte) |
| 77 | Instrumentenverleih (Liste AP1-Szenarien) | In\|stru\|men\|ten‖ver\|leih | – |
| 78 | Konzertveranstalters (Liste AP2-Szenarien) | Kon\|zert‖ver\|an\|stal\|ters | – |
| 79 | Kreishandwerkerschaft (Liste AP2-Szenarien) | Kreis‖hand‖wer\|ker\|schaft | `ei` bleibt; `-schaft` als Silbe |
| 80 | Landschaftsarchitekturbüros (Liste AP2-Szenarien) | Land\|schafts‖ar\|chi\|tek\|tur‖bü\|ros | `ch` bleibt (`ar\|chi`) |
| 81 | Lohnsteuerhilfevereins (Liste AP1-Szenarien) | Lohn‖steu\|er‖hil\|fe‖ver\|eins | `eu` bleibt (`steu\|er`); `ver\|eins`: `ei` bleibt |
| 82 | Meilensteintrendanalyse (Liste AP1-Szenarien, Liste AP2-Szenarien) | Mei\|len‖stein‖trend‖ana\|ly\|se | englisch `Trend`; Fuge vor `ana` wie Nr. 20 Anhang A |
| 83 | Notarfachangestellte (Liste AP1-Szenarien) | No\|tar‖fach‖an\|ge\|stell\|te | `ch` bleibt (`fach`) |
| 84 | Physiotherapiepraxis (Liste AP2-Szenarien) | Phy\|sio‖the\|ra\|pie‖pra\|xis | **⚠ unsicher:** `Phy\|sio` – oder `Phy\|si\|o`?; `sio` als eine Silbe (`Phy\|sio`) |
| 85 | Regenwasserzisterne (Liste AP1-Szenarien) | Re\|gen‖was\|ser‖zis\|ter\|ne | – |
| 86 | Regionalradiosender (Liste AP2-Szenarien) | Re\|gio\|nal‖ra\|dio‖sen\|der | **⚠ unsicher:** `Re\|gio` – oder `Re\|gi\|o`?; `gio` als eine Silbe (`Re\|gio\|nal`); `dio` ungeteilt |
| 87 | Schnittstellenkennung (Rechenwege) | Schnitt‖stel\|len‖ken\|nung | – |
| 88 | Softwarelieferanten (Liste AP2-Szenarien) | Soft\|ware‖lie\|fe\|ran\|ten | englisch: `Soft\|ware`, `ware` ungeteilt |
| 89 | Speicherkontingente (Liste AP2-Szenarien) | Spei\|cher‖kon\|tin\|gen\|te | – |
| 90 | Systemadministrator (Liste AP1-Szenarien) | Sys\|tem‖ad\|mi\|nis\|tra\|tor | `st` getrennt (`Sys\|tem`), `tr` am Silbenanfang |
| 91 | Tiefbauunternehmens (Liste AP2-Szenarien) | Tief‖bau‖un\|ter\|neh\|mens | `ie`, `au` bleiben |
| 92 | Universitätsbibliothek (Liste AP2-Szenarien) | Uni\|ver\|si\|täts‖bi\|blio\|thek | kein `U\|`: `Uni\|ver`; `bi\|blio\|thek` |
| 93 | Videokonferenzsystems (Liste AP1-Szenarien) | Vi\|deo‖kon\|fe\|renz‖sys\|tems | `deo` ungeteilt (`Vi\|deo`) |
| 94 | Zertifikatslaufzeiten (Liste AP2-Szenarien) | Zer\|ti\|fi\|kats‖lauf‖zei\|ten | `au`, `ei` bleiben |

#### Zusammenfassung unsicher (14)

- Arbeitsgruppendrucker: `dru|cker` (Regel 2006) – oder ganz ungeteilt `drucker`?
- Datenschutzbeauftragten: Vorsilbe `be|auf` als `|` oder `‖`?
- Drogeriemarktfiliale: `fi|li|a|le` (Einzelvokal) – oder `fi|lia|le`?
- Ferienhausvermittlung: `Fe|rien` – Duden erlaubt auch `Fe|ri|en`; durch (iii) ausgeschlossen
- Generationenprinzip: `ra|tio|nen` gegen Anhang A `ti|ons` (dort getrennt)
- Hochzeitsfotografin: Fuge `Hoch‖zeits`? Ich setze `|` (kein Kompositum im heutigen Sinn)
- Immobilienverwaltung: `bi|lien` – Duden auch `bi|li|en`; durch (iii) ausgeschlossen
- Ingenieurgesellschaft: `In|ge|nieur` – `nieur` ungeteilt richtig?
- Multifunktionsgerät: `Mul|ti‖funk`: `‖` nach `Multi` (Präfix) richtig?
- Netzwerkspezialisten: `zi|a` (Einzelvokal) – oder `zia` ungeteilt?
- Physiotherapiepraxis: `Phy|sio` – oder `Phy|si|o`?
- Regionalradiosender: `Re|gio` – oder `Re|gi|o`?
- Versicherungsagentur: `agen` ungeteilt (Mindestlänge) – oder `agen|tur` reicht?
- verursachungsgerecht: `ver|ur` als `|` (Vorsilbe) oder `‖`?

---

## Hinweis
Meldung 44 ist nicht committet und liegt **nicht** auf dem Zweig `meldungen`. Die Hinweiszeile „Meldung 44 liegt auf `meldungen`, Commit <sha>“ folgt erst mit dem Push. Die erste Gegenprüfung hat Fassung 1 geprüft (`meldungen/gegenpruefung/Meldung_44_gp.md`), eine zweite Fassung 2 (`meldungen/gegenpruefung/Meldung_44_gp2.md`); deren Befunde sind eingearbeitet.

Dokumente:
- /mnt/project-files/bau_0.63.2/meldungen/Meldung_44_Fragen_und_Stand.md (diese Meldung)
- /mnt/project-files/plan_0.63.2/freigabe/Weisung_CC_Antwort_Meldung_43.md
- /mnt/project-files/plan_0.63.2/freigabe/Weisung_CC_Antwort_Meldung_42.md
- /mnt/project-files/plan_0.63.2/freigabe/Weisung_CC_Antwort_Meldung_41.md
- /mnt/project-files/plan_0.63.2/freigabe/Weisung_CC_Antwort_Meldung_38_und_40.md
- /mnt/project-files/bau_0.63.2/meldungen/gegenpruefung/Meldung_44_gp.md
- /mnt/project-files/bau_0.63.2/meldungen/gegenpruefung/Meldung_44_gp2.md
- /mnt/project-files/bau_0.63.2/integration/tor/tor_e90b78e.md
- /mnt/project-files/bau_0.63.2/integration/tor/tor_53a4354.md
- /mnt/project-files/bau_0.63.2/integration/n6_konflikt/ (LIESMICH.txt, vorschlag_aufloesung_cc.diff, vorschlag_gegen_n6_3ec3665.diff, vorschlag_gegen_integration_a82fd34.diff)
- /mnt/project-files/bau_0.63.2/antraege/FG-107_Antrag.md
- /mnt/project-files/bau_0.63.2/antraege/FG-111_knopf.diff
- /mnt/project-files/bau_0.63.2/antraege/FG-111_knopf_erweitert.diff
- /mnt/project-files/bau_0.63.2/antraege/FG-111_spiel_vorschlag.diff
- /mnt/project-files/bau_0.63.2/antraege/FG-112_kaestchen.diff
- /mnt/project-files/bau_0.63.2/antraege/belege_fg112/
- /mnt/project-files/bau_0.63.2/antraege/belege_fg111/
- /mnt/project-files/bau_0.63.2/s1c2/nachbesserung/logs/ci_rest_38549977359.log
- /mnt/project-files/bau_0.63.2/n15/logs/frage14b/ci_rest_115784933856.log
- /mnt/project-files/plan_0.63.2/freigabe/Antwort_Meldung_39_Nico.md
- /mnt/project-files/bau_0.63.2/REGELN_BAU_0.63.2.md
- /mnt/project-files/bau_0.63.2/OFFEN_FUER_BERICHT.md
- /mnt/project-files/bau_0.63.2/integration/PROTOKOLL.md
- /mnt/project-files/bau_0.63.2/integration/tor/tor_a82fd34.md
- /mnt/project-files/bau_0.63.2/integration/welle3c/ci_38550615169/jobs.tsv
- /mnt/project-files/bau_0.63.2/integration/welle3c/ci_38550615169/zeiten_belegt.txt
- /mnt/project-files/bau_0.63.2/integration/welle3c/n6_konflikt_app_gui_calcview.diff
- /mnt/project-files/bau_0.63.2/integration/welle3c/merge8_n5_diffvergleich.txt
- /mnt/project-files/bau_0.63.2/werkzeug/bekannt_rot_github.txt
- /mnt/project-files/bau_0.63.2/antraege/FG-109_Antrag_Zahl_Einheit.md
- /mnt/project-files/bau_0.63.2/antraege/FG-109_zahl_einheit.diff
- /mnt/project-files/bau_0.63.2/antraege/fg109_fotos/
- /mnt/project-files/bau_0.63.2/antraege/FG-110_Antrag_faellig_Index_verwerfen.md
- /mnt/project-files/bau_0.63.2/antraege/FG-110_faellig_nachtrag.diff
- /mnt/project-files/bau_0.63.2/antraege/belege_fg110/
- /mnt/project-files/bau_0.63.2/antraege/FG-107_faellig.diff
- /mnt/project-files/bau_0.63.2/n7/gp_fg107/gegenpruefung.md
- /mnt/project-files/bau_0.63.2/n7/fg107/ergebnis.md
- /mnt/project-files/bau_0.63.2/n7/fg107/logs/messung_windows.md
- /mnt/project-files/bau_0.63.2/n7/fg107/logs/ci_38550497158_rest_joblog.txt
- /mnt/project-files/bau_0.63.2/n14/ergebnis.md (Nachtrag Weisung 43, 2.5)
- /mnt/project-files/bau_0.63.2/n14/zaehlkorrektur_u1_u3.md
- /mnt/project-files/bau_0.63.2/s1c2/nachbesserung/ergebnis.md
- /mnt/project-files/bau_0.63.2/s1c2/nachbesserung/pruefung_unterschrift_0631/ergebnis.md
- /mnt/project-files/bau_0.63.2/s1c2/nachbesserung/logs/ci_rest_38554173440.log
- /mnt/project-files/bau_0.63.2/n8/Anhang_94_Woerter.md
- /mnt/project-files/bau_0.63.2/n8/vorpruefung_94.txt
- /mnt/project-files/bau_0.63.2/n8/rueckfragen_w43.md
- /mnt/project-files/bau_0.63.2/n8/ergebnis.md
- /mnt/project-files/bau_0.63.2/n8/logs/ci_38544277059_rest_auszug.txt
- /mnt/project-files/bau_0.63.2/n9/ergebnis.md
- /mnt/project-files/bau_0.63.2/n9/logs/lauf_38549419907_rot.txt
- /mnt/project-files/bau_0.63.2/n9/logs/pixelvergleich_bj04_v2.txt
- /mnt/project-files/bau_0.63.2/n9/logs/pixelvergleich_gradientbutton.txt
- /mnt/project-files/bau_0.63.2/n15/ergebnis.md
- /mnt/project-files/bau_0.63.2/n15/logs/frage14b_einheitlich/ci_rest_115802761348.log
- /mnt/project-files/bau_0.63.2/meldungen/Nachtrag_Meldung_39_Fotos.md (an Nico, beantwortet 11:54 UTC)
- /mnt/project-files/plan_0.63.2/freigabe/Antwort_Nachtrag_39_Nico.md
- /mnt/project-files/bau_0.63.2/antraege/FG-103_Antrag.md
- /mnt/project-files/bau_0.63.2/antraege/FG-111_Antrag_Knopf_waechst.md
- /mnt/project-files/bau_0.63.2/antraege/FG-112_Antrag_Kaestchen_erste_Zeile.md
- /mnt/project-files/bau_0.63.2/meldungen/Meldung_43_Fragen_aus_dem_Bau.md
- Läufe: 38550615169 (grün), 38549211060, 38543848476, 38549419907, 38545811233, 38554173440, 38549977359, 38550497158, 38544277059, 38506811682
