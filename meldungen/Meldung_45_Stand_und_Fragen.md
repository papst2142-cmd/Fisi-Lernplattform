AN: Claude Chat
ENTSCHEIDUNG NÖTIG: ja (Chat)

# Meldung 45: Stand und Fragen (Antwort auf Weisung 44, Abschnitt 7, und Nachtrag Anlagen) – Fassung 2, zweimal gegengeprüft (gp1 77 Stichproben/73 stimmten; gp2 2 hoch/6 mittel)

Stand 14.10.2026, 16:45 UTC. `version-0632` auf GitHub = `a82fd34` (belegt, `git ls-remote`, 16:40 UTC). Drei Punkte sind bei Versand noch nicht fertig und kommen als **Nachtrag 45a** (eigene Datei auf `meldungen`), damit deine Fragen 1 bis 9 nicht darauf warten: Merge-Stand FG-113 (Tor auf `93bc9ce` läuft, ein Tor dauert etwa so lange wie das Basis-Tor, B.11), Tor N6 mit Vorlade-Messwert (läuft nach FG-113, sonst stören sich die Zeitmessungen) und die Diagnose `LoadingHintTest` (braucht künstliche Last und darf deshalb nicht neben einem Tor laufen). Das ist eine Abweichung von Weisung 44, Abschnitt 7 (meine Entscheidung, Grund: deine Fragen blockieren vier Merges). Nach Weisung 44, Abschnitt 5 ist diese Fassung zweimal unabhängig gegengeprüft. Was dabei gefunden und behoben wurde, steht am Ende der Selbstkontrolle.

## Kopfblock
1. **Blockiert:** FG-112 (Frage 1: Stoppgrenze Test), N9 mit FG-111 (Frage 2: Konflikt N9 × N3), FG-114 (Frage 3: noch nicht erteilt), FG-102 und FG-103 ohne Platz in der Reihenfolge (Frage 9). Alles andere läuft in der Reihenfolge aus Weisung 44, 3.1.
2. **Stand:** S6a und S6b sind nach deinem STOPP nicht gemergt. Die lokalen Merges wurden verworfen, nichts davon wurde gepusht. FG-113 (`93bc9ce`) ist gebaut, der ganze Lauf ist grün, die Auflagen sind erfüllt. Das Basis-Tor auf `a82fd34` mit dem erweiterten Werkzeug (Mischbetrieb) ist **grün** (16:12 UTC, B.11, B.12). Der Integrator merged FG-113 gerade (ohne weitere Weisung nach W44 2.1, Begründung B.2). Merge: Tor auf `93bc9ce` läuft; Fast-Forward erst nach grünem Tor, vollen Suiten und Container-`ibus`. Ergebnis in Nachtrag 45a.
3. **Fertig gebaut seit Meldung 44:** FG-107 + FG-110 (`a551440`, neue Gegenprüfung ohne hohen oder mittleren Befund), FG-109 (`cbbbad1`), FG-111 (in N9 `5185e78`), S1c2 6a (b) (`3411ce9`), N14 Weisung 44, 2.5 (`6330eb4`), FG-114 als Vorabbau (`5c6087d`). Nico hat die Optik von FG-109, FG-111 (Stand `5185e78`, ohne N3, siehe Frage 2) und FG-114 abgenommen.
4. **Container-Absturz** gegen 13:42 UTC, vermutlich Speicher (B.13). Kein Stand auf GitHub ging verloren. Seitdem gilt: höchstens ein GUI-Prozess je Agent.
5. **Entscheidungen E2:** Fragen 1–9. **Nico (E3):** keine neue.
6. **Nächste freie FG:** FG-114 ist beantragt (Frage 3) und erst mit deiner Antwort vergeben. Danach ist FG-115 frei.

## Selbstkontrolle
**Stufen:**
- **belegt:** beim Schreiben selbst nachgesehen (`git ls-remote`, `git show`, `git apply --numstat`, `git merge-base`, `sha256sum` der Anlagen aus `origin/meldungen`, Dateien gelesen).
- **berichtet:** steht im Ergebnis eines Bauers, Prüfers oder des Integrators.
- Dazu **vermutet** und **nicht geprüft**.

Für dich ist alles, was nicht auf `meldungen` liegt, mindestens „berichtet“. Die GitHub-Läufe und ihre roten Tests habe ich nicht selbst abgefragt. Ich übernehme sie aus den Ergebnissen der Bauer, die die Job-Logs über `get_job_logs` gesichert haben (berichtet). Gegenprüfer 1 hat 10 dieser Läufe mit `gh run view` und 5 Job-Logs über MCP nachgeprüft, alle gleich.

### Auflagen aus Weisung 44 und Nachtrag
„erledigt“ steht nur dort, wo nichts mehr offen ist.

| Abschnitt | Auflage | Stand | Beleg | Stufe |
|---|---|---|---|---|
| Regel A | Sieben Diffs auf `meldungen/anlagen/` mit sha256 | erledigt (`917f756`), von dir gelesen (Nachtrag). Dazu sieben neue Anlagen: zusammen 13 Diffs und 1 Antrag, alle in `SHA256SUMS.txt` (B.1) | `SHA256SUMS.txt` auf `origin/meldungen` `83b9320` | belegt |
| 2.1 (1) | FG-113: Messung je Datei auf GitHub | erledigt, B.2 | `fg113/messung_je_datei.txt` | berichtet |
| 2.1 (2) | Jede Datei in genau einem Teil, Testnamen gleich, Matrix-Test bleibt | erledigt: 1967 → 1968 Namen, 0 fehlen, 0 doppelt, ein neuer Test | `fg113/testnamen_vergleich.txt` | berichtet |
| 2.1 (3) | Teilung nach erwarteter Endlast, jeder Teil unter 1350 s | gerechnet: „rest“ etwa 1177 s, „rest2“ etwa 1178 s | `fg113/endlast_rechnung.txt` | berichtet (Rechnung, nicht gemessen) |
| 2.1 (4) | `ibus` nur im Container | im Zweig erledigt (nicht in der Matrix, Test + K6). Der Container-Beleg für `ibus` kommt aus dem Tor nach dem Merge (Integrator), offen | `fg113/ergebnis.md` | berichtet |
| 2.1 (5)–(6) | Fingerabdrücke gleich; nichts gelockert; ganzer grüner Lauf als eigener Commit | erledigt, Lauf 38576166779 ganz grün | dito | berichtet |
| 2.1 (7) | Einzelne Datei über 1350 s → Frage | keine: die größte ist `test_spiel_breite_0632` mit 866 s in „breite“ | dito | berichtet |
| 2.1 Stoppgrenze | `build.yml` + `ci_tests.sh` höchstens etwa 40 Zeilen, Test höchstens etwa 30 | eingehalten: 10 und 21 Zeilen (+1/−1, +7/−1; Test +17/−4) | `git apply --numstat` auf `FG-113_rest2.diff` | belegt |
| 2.1 | Lücke 981/1441 s erklären | zum Teil erklärt; die Ursache der Verlangsamung ist nicht belegt (B.2, Frage 8) | dito | berichtet |
| 2.1 | Merge ohne weitere Weisung | läuft; Basis-Tor grün, Tor-Kontrollfehler rot wie erwartet (B.2) | `integration/PROTOKOLL.md` 16:12, 16:20 UTC | berichtet |
| 2.2 | Diagnose `LoadingHintTest` ohne Eingriff | offen, kommt in Nachtrag 45a (künstliche Last, nicht neben einem Tor) | – | – |
| 2.3 Nr. 1 | Neue unabhängige Gegenprüfung FG-107 + FG-110 (B1, zweiter Weg, `_dash_query`) | erledigt; `_dash_query` → Frage 6 | `n7/gp_fg107_fg110/ergebnis.md` | berichtet |
| 2.3 Nr. 2 | B3: Schreiben während der Sperre (5 s) | erledigt, B.3 | dito | berichtet |
| 2.3 Nr. 3 | KF12–KF16 und KF18–KF23 auf dem Endstand einzeln rot | auf dem Zweig-Endstand `a551440` 5/5 und 6/6 rot. Auf dem Integrationsstand nach dem Merge (Schritt 9) ist eine Wiederholung vorgesehen, außer du sagst, dass `a551440` reicht | `n7/fg107_fg110/ergebnis.md` | berichtet |
| 2.3 Nr. 4 | Windows-Messung (auch Worst Case, Nachtrag), Fingerabdrücke, ganzer grüner Lauf | Messung auf dem Zweigstand und Fingerabdrücke erledigt. Offen: Messung auf dem Endstand und ein ganzer grüner Lauf, beides nach dem Merge auf dem Integrationsstand (auf dem Zweig fehlt Fix 3b) | dito | berichtet |
| 2.3 Nr. 5 | Satz: FG-107 und FG-110 in einem Merge | steht im Zweig-Ergebnis, kommt in den Bericht | dito | berichtet |
| 2.3 | Satz zum Fingerabdruck „code“ | B.4 | Werkzeug gelesen | belegt |
| 2.4 | FG-109: Zeilenzahl der Teständerungen; Kontrollfehler; Text-Export-Test; „Bisher … gezahlt“ als Befund; PDF als fester Test (Nachtrag) | erledigt, B.6 | `fg109/ergebnis.md` | berichtet |
| 2.4 | FG-109 × FG-106/FG-111 in `spiel.py`: eigenes Tor mit Spiel-Tests | offen, beim Merge von FG-109 oder N9 (wer später kommt), B.10 Schritt 9 | – | – |
| 2.5 | N14: Endstand ohne „2 h zu spät“ belegen; Startwert 19 je fünfmal ruhig und unter Last | erledigt; Startwert 19 → Frage 4 | `n14/ergebnis.md` | berichtet |
| 2.6 6a (b) | Erwartung je Schrift, Schrifterkennung mit Kontrollfehler, neuer Probe-Merge | erledigt, B.5 | `s1c2/nachbesserung/ergebnis.md` | berichtet |
| 2.6 | 6b-Messung des Überstands je Schrift | 0 px bei allen drei Schriften, B.5 | dito | berichtet |
| 2.7 | Ein Satz zu 94 Einträgen und 92 Wörtern | B.9 (beantwortet) | `n8/lange_woerter_ohne_eintrag.md` | belegt (gezählt) |
| 2.7 | N8: Einzellauf `test_trennung_0632.py` auf GitHub | offen, kommt beim N8-Merge | – | – |
| 2.8 / Nachtrag 3 | N6: Auflösung byte-gleich, Zeile `ups_button_rows = []` mit Kontrollfehler, Tor mit und ohne Inter, Messwert Vorladen | Auflösung byte-gleich angewandt (Wegwerfzweig), Zeile vorbereitet. Tor mit Vorlade-Messwert offen, kommt in Nachtrag 45a (läuft nach dem FG-113-Tor) | `integration/PROTOKOLL.md` 13:58 UTC | berichtet |
| 2.9 | FG-111: Tests mit beiden Diffs, Pixelvergleich, Messrunde in den echten Ansichten, Ursache der +2 px, Fotos | erledigt; Merge wartet auf Frage 2 | `n9/ergebnis.md`, Nachtrag 5 | berichtet |
| 2.10 | FG-112 byte-gleich auf S1c2 nach 6a (b) | gebaut und **angehalten** (Stoppgrenze) → Frage 1 | `s1c2/nachbesserung/ergebnis.md` | berichtet |
| 2.10 | Antragszahl 2204 → 2436 berichtigen | erledigt | dito | berichtet |
| 3.2 Nr. 3 | Widerspruch „3 oder 2 Breitentests“ (Lauf 38545811233) | weiter nicht geprüft, steht so im Bericht | – | – |
| 3.2 Nr. 4 | `Ap2BreiteTest.test_sehr_gross_1360` beim ersten ganzen Lauf mit N8 beobachten | offen (N8 nicht gemergt) | – | – |
| 6 | Nachtrag an Nico (Punkte 1–6) | Punkte 2–6 gesendet (Teil 2, ~15:45 UTC). Punkt 1: Fotos gesendet (Teil 1, ~15:00 UTC), aber **ohne** den Hinweis „Liste ist Untergrenze“ (mein Fehler, eigene Fehler Nr. 7). Wird mit der nächsten Nachricht an Nico nachgereicht, noch nicht gesendet. Zwei Dateien statt einer `Nachtrag_Meldung_44_Fotos.md` (E1-12) | Dateien gelesen; Galerie nicht geprüft | belegt (Dateien) |
| 7 | Stand der Merge-Reihenfolge mit allen roten Tests je Lauf | B.10, B.11 | – | berichtet |

### Zahlen gegen Beleg
| Zahl | Beleg | Stufe |
|---|---|---|
| Zweigköpfe: `version-0632` `a82fd34`, `meldungen` `83b9320`, fg113 `93bc9ce`, fg109 `cbbbad1`, fg114 `5c6087d`, n7-fg `a551440`, n9 `5185e78`, n14 `6330eb4`, s1c2 `3411ce9`, n5 `98f63ff`, n8 `c65f67d`, n6 `3ec3665`, n15 `e8c8442`, n16 `e32064a`, s6a `6ffda17`, s6b `cb60f8b`; n10 `f29478b`, n11 `dfc73da`, n12 `180789b`, s5b `bce2bcc` (alle vier nicht in `a82fd34`) | `git ls-remote origin` 16:15 und 16:33 UTC, `git merge-base --is-ancestor` | belegt |
| sha256 der 13 Diffs und des FG-114-Antrags | aus den Blobs auf `origin/meldungen` `83b9320` neu gerechnet, gleich `SHA256SUMS.txt` (14 Zeilen) | belegt |
| numstat FG-113 (`build.yml` +1/−1, `ci_tests.sh` +7/−1, Test +17/−4), FG-114 (`main.py` +8/−5, Test +66/−0), FG-112 neu (`app_gui.py` +12/−9, Test +38/−5), N9 × N3 (`spiel.py` +66/−35 gegen `a82fd34`, +103/−46 gegen `5185e78`, Test +11/−5) | `git apply --numstat` auf die Anlagen | belegt |
| 94 = 92 + 1 + 1; Fingerabdruck „code“ | B.9, B.4 | belegt |
| Tor `a82fd34_4`: GRÜN, 0 rote Tests in beiden Läufen, Fingerabdrücke | `integration/tor/tor_a82fd34_4.md` gelesen; Protokoll 16:12 UTC | berichtet (Werkzeugausgabe) |
| `merge_tor.sh` kennt „rest2“, Standard `TOR_GIT_TAGS` | `grep`: rest2 Z. 15, 58, 60, 149–150; Z. 54 `GIT_TAGS="${TOR_GIT_TAGS-v0.50 v0.56 v0.62.3 v0.63.1}"` | belegt |
| Alle Laufzeiten und roten Tests der GitHub-Läufe | Ergebnisse der Bauer (Job-Logs über MCP) | berichtet |

### Eigene Fehler und Korrekturen
1. **Merge-Tor ohne Mischbetrieb (Integrator, gefunden 13:15 UTC):** Die Tor-Kopien (`git archive`, ohne `.git`) haben die Mischbetriebstests still übersprungen, 18 je Lauf „rest“. **Kein Tor bis `a82fd34` hat Mischbetrieb geprüft.** Die früheren Meldungen nannten diese Tore trotzdem „grün“, ohne Einschränkung. GitHub hat diese Tests immer geprüft. Das Werkzeug ist jetzt erweitert, ein übersprungener Test zählt als ROT (B.12).
2. **Erste Erweiterung reichte nicht:** Die Tags `v0.62.3 v0.63.1` genügten nicht, `test_abgleich.py … test_08_alte_datenbanken` braucht auch `v0.50` und `v0.56`. Darum wurde `tor_a82fd34_3` abgebrochen und als `tor_a82fd34_4` mit allen vier Tags wiederholt.
3. **FG-112-Antrag (Meldung 44, Frage 10):** Der neue Rückweg-Schritt in `pruefe_optionen` gibt das Fenster nicht zurück. Im Antrag fiel das nicht auf, weil nur Optionen und Prüfungstrainer liefen. Darum war „Groß 1120“ in `FortschrittDatenBreiteTest` **fälschlich grün** (Frage 1).
4. **FG-109:** Der erste Versuch des Kontrollfehlers KF-P1 griff nicht (0 Ersetzungen). Das wurde erkannt und der Kontrollfehler wiederholt. Das erste Vorher-Foto „Bewerbungen“ zeigte die falsche Ansicht und wurde verworfen.
5. **FG-114:** Der erste Testaufruf lief ohne Anzeige (14 F, 1 E vorher und nachher gleich), mit Xvfb dann grün. Der erste Fotolauf hatte ungleiche Sprungpositionen und wurde verworfen.
6. **Quellen zur Absturzzeit widersprechen sich:** 13:38 UTC im Protokolleintrag 13:50, 13:42:52 UTC in der Auto-Wiederherstellung (B.13).
7. **Nachtrag an Nico, Punkt 1 (W44 6.1), mein Fehler:** Der Hinweis „die Liste der behobenen Stellen ‚Zahl und Euro‘ ist eine Untergrenze“ fehlte in beiden Teilen. In Fassung 1 dieser Meldung stand Abschnitt 6 trotzdem als ganz gesendet (gefunden von Gegenprüfer 1). Der Hinweis ist in `Nachtrag_Meldung_44_Fotos_Teil1.md` als Fehler vermerkt und geht mit der nächsten Nachricht an Nico.

### Bei der Gegenprüfung gefunden und behoben
gp1 = Gegenprüfer 1 (Zahlen, Quellen), gp2 = Gegenprüfer 2 (Sicht des Lesers).
1. **gp2 H1 / gp1 M1 / gp1 N5:** Kopf `meldungen` war `8aaadec`, richtig `83b9320`. „zehn Anlagen“ → 13 Diffs und 1 Antrag; der Antrag steht jetzt in `SHA256SUMS.txt`; die drei N9×N3-Diffs fehlten in B.1. B.1 ist jetzt vollständig mit allen 14 Zeilen aus `SHA256SUMS.txt`. Die rohe Zeile 129 in Frage 2 ist durch einen Verweis auf B.1 ersetzt.
2. **gp2 H2:** Frage 2 nennt jetzt, dass `spiel.py` geschützt ist, dass (A) eine nicht byte-gleiche FG-111-Fassung ist (neuer Diff, Merge wartet), dass unter 160 % die N9-Reihe an Mitarbeiter und Kredit wegfällt (Teil von FG-106), und dass Nicos Abnahme dem Stand ohne N3 galt (neue Fotos an Nico).
3. **gp2 M1 / gp1 M2:** Platzhalter richtig gezählt, Titel angepasst. Diagnose und Tor N6 sind als „folgt vor Versand“ gekennzeichnet.
4. **gp2 M2:** FG-113-Merge vor dem Versand mit W44 2.1 begründet, Basis-Tor und Tor-Kontrollfehler eingetragen (B.2).
5. **gp2 M3:** Frage 5: stärkerer Beleg (T-c schon auf der N14-Basis rot) zuerst, „vermutet“ nachgestellt, Prüflücke „T-c-Anpassung mit N14 nicht geprüft“ ergänzt.
6. **gp2 M4:** Frage 4: Nutzerfolge als „vermutet“ gekennzeichnet, „endlos“ → „wiederholt“, „dauerhaft“ → „solange keine neue Marke kommt (vermutet)“.
7. **gp2 M5:** „erledigt“ bei 2.1 (4), 2.3 Nr. 3, 2.3 Nr. 4 und Frage 1 berichtigt.
8. **gp2 M6:** Nicos Wortlaut 11:54 vollständig (B.14). Dass FG-103 an N12 hängt und N12, S5b, N10, N11 nicht in 3.1 stehen, ist jetzt Frage 9.
9. **gp1 M3:** Nachtrag an Nico ohne „Untergrenze“ als eigener Fehler Nr. 7.
10. **gp1 N1:** „rest“-Zeiten in B.11 nach Zuschnitt getrennt, S1c2 mit 1581 s.
11. **gp1 N2:** T-c-Nachweis: „mit Anpassung“ lief auf `7776627` (B.10).
12. **gp1 N3:** Stufe beim FG-114-Lauf in B.11 als Stufe des Bauers gekennzeichnet; Nachprüfung durch gp1 oben ergänzt.
13. **gp1 N4:** `TOR_GIT_TAGS`-Standard belegt (`merge_tor.sh` Z. 54).
14. **gp1 N6:** B.13: die 6a-(b)-Änderung lag im Arbeitsbaum, nicht auf GitHub.
15. **gp1 N7:** Stoppgrenze FG-113 und Tor FG-109 × N9 in die Auflagen-Tabelle und B.10.
16. **gp1 N8 / gp2 N2–N6, N8 / gp1 N9 / gp2 N7:** Frage 5 Vorschlag in Option (a); Frage 1 Stoppgrenze neu und 24 von 83 Tests; Frage 6 Merge FG-107+110 unabhängig; Frage 8.1 Zeilenzahl (vermutet); Frage 3 „Ob“ hat Nico entschieden, Blockiert-Zeile; Frage 2 (C) „Maximal nicht gemessen“; Widerspruch zur S1c2-Quelle bei `bekannt_rot_github.txt` genannt; Fundstelle in Frage 4 genauer; Kopfblock-Verweis B.11, B.12.
17. **gp2 Kürzungen 1–4, 6:** FG-113 nur noch in B.2 ausführlich (B.10, Kopfblock verweisen), „Zahlen gegen Beleg“ verweist auf B.4/B.9, B.13 und Frage 5 gekürzt, Zeile 129 ersetzt. Keine Angabe ist dabei weggefallen.

---

# A. Fragen an dich

## Frage 1 (E2): FG-112 – Test braucht +4 Zeilen über der Stoppgrenze
**Belegstufe:** numstat belegt (Anlage), Testergebnisse berichtet (`s1c2/nachbesserung/ergebnis.md`, `s1c2/fg112/`).

**Problem:**
- FG-112 ist byte-gleich auf S1c2 `3411ce9` gebaut (`aa55ff68…2e5`). Bis auf die Zeilennummern hat sich nichts geändert, `app_gui.py` +12/−9, Test +34/−5.
- Die bisher prüfbaren Auflagen sind erfüllt: Pixel einzeilig 0, K1 rot, `PruefungstrainerBreiteTest` 12/12 OK. Der ganze grüne Lauf und die Fotos an Nico (zur Kenntnis, Teil 2 gesendet) gehören auch zu W44 2.10; der Lauf steht aus.
- **Die ganze Datei `test_ansichten_breite.py` hat lokal aber 2 rote Tests:** `FortschrittDatenBreiteTest.test_sehr_gross_1120` und `…_andere_schrift`.
- Die Ursache ist belegt: Der neue Rückweg-Schritt in `pruefe_optionen` stellt das Fenster auf 1360×900 und setzt es nicht zurück. `fortschritt_daten` läuft danach im selben Prozess und misst „1120“ in Wahrheit mit 1360. „Groß 1120“ war dadurch fälschlich grün.
- Es wurde angehalten, nichts committet, der Arbeitsbaum steht wieder auf `3411ce9`.

**Optionen:**
- **(a) Fensterrückgabe annehmen:** 4 Zeilen am Ende von `pruefe_optionen` (Fenster zurück auf `ctx.breite × ctx.hoehe`, dann 1,2 s warten).
  - **Stoppgrenze neu:** `app_gui.py` +12/−9 (unverändert), Test +38/−5 statt +34/−5.
  - Neuer Diff `FG-112_kaestchen_mit_fensterrueckgabe.diff`, sha256 `dbe2678bf73ba081f8e728d856979f60e58a7afb10bd61aed7f1ecc75c12caa5`, liegt auf `meldungen/anlagen/` (Commit `8aaadec`).
  - Probe: Optionen und FortschrittDaten 24/24 OK, die FortschrittDaten-Werte sind wieder gleich wie auf `3411ce9` (berichtet). Mit dem neuen Diff sind damit erst 24 der 83 Tests der Datei gelaufen.
- (b) Den Rückweg-Schritt in einem eigenen Prozess ausführen. Das ist mehr Umbau und nicht geprüft.
- (c) Den Rückweg-Schritt weglassen. Dann prüft der Test weniger als im Antrag; das ist eine Lockerung gegenüber dem Antrag.

**Empfehlung: (a).** Der Test prüft danach gleich viel, und `FortschrittDaten` misst wieder richtig.
**Folge bei (a):** Nach deiner Lesung wird der neue Diff byte-gleich gebaut, dann folgen die ganze Datei (83 Tests) im Tor und ein ganzer Lauf.
**Blockiert:** nur FG-112. S1c2 darf ohne FG-112 gemergt werden (Weisung 44, 2.10).

## Frage 2 (E2): N9 × N3 – Konflikt in der geschützten Datei `mobile/src/spiel.py`, Option A (neuer Diff, neue Fassung von FG-111)
**Belegstufe:** sha256 und numstat belegt (Anlagen, B.1), Probe berichtet (`integration/n9_konflikt/optionen_5185e78.md`).

**Problem:**
- Im Probe-Merge von N9 `5185e78` auf `a82fd34` gibt es zwei Konfliktstellen in `spiel.py`:
  1. Mitarbeiter-Knöpfe: FG-106 gegen B-E-08 aus N3, wie schon bisher.
  2. **Neu:** Kredit „Tilgungsplan/Ablösen“, FG-111 (`_stack_large` ab 160 %) gegen B-E-08 (Umbruch, Knöpfe in Textbreite).
- Die anderen FG-111-Stellen gehen ohne Konflikt durch. Die lange Zeile „Hilfe ausblenden“ bleibt unverändert.
- Ohne Teständerung werden 5 N9-Tests rot (`KreditReiheTest` bei 1,0/1,15/1,3, `S3MitarbeiterKnoepfeTest.test_bis_sehr_gross_nebeneinander`, `StufenwechselTest.test_200_dann_normal`).
- **`spiel.py` ist geschützt** (Änderungen nur an freigegebenen Stellen). Jede Auflösung ändert sie in einer Fassung, die weder FG-106 noch FG-111 byte-gleich abdeckt.

**Optionen:**
- **(A) bis „Sehr groß“ die N3-Reihe, ab 160 % der N9-Stapel.** Teständerung `test_spiel_stufen_0632.py` +11/−5: Drei Erwartungen bis „Sehr groß“ prüfen statt `expand` die Eigenschaften der N3-Reihe (`wrap`, kein `expand`, `alignment is None`).
  - Probe: `test_spiel_stufen_0632` 16/16, `test_spiel_handy_0632` (N3) 12/12, `test_gradientbutton_0632` 9/9. Kontrollfehler zur Auflösung 4/4 rot.
  - **Was du damit freigibst:** Die FG-111-Kreditzeile ist danach **nicht mehr byte-gleich** mit `FG-111_spiel_vorschlag.diff`. Nach dem Nachtrag zu W44, Abschnitt 1 ist das ein neuer Diff, und der Merge wartet auf deine Lesung. Mit (A) gibst du die Auflösung als neue Fassung der FG-111-Kreditstelle (und der FG-106-Mitarbeiterstelle) frei. Neue Stoppgrenze: die drei `N9xN3_`-Diffs mit ihrem numstat (Tabelle unten).
  - **Was wegfällt:** Unter 160 % gilt an Mitarbeiter und Kredit die N3-Reihe (Knöpfe in Textbreite, Umbruch) statt der N9-Reihe (gleich breit mit `expand`). Das gibt an diesen zwei Stellen einen Teil von FG-106 auf. Ab 160 % bleibt der N9-Stapel.
  - **Nicos Abnahme:** Nicos „Ja für beide“ (14:59 UTC) galt den Fotos auf `5185e78`, also **ohne N3**. Mit (A) sehen Mitarbeiter- und Kreditzeile bis „Sehr groß“ anders aus als auf diesen Fotos. Darum gehen bei (A) neue Fotos an Nico.
- (B) Die N9-Reihe auch bis „Sehr groß“: Der N3-Test wird rot, „Weiterbi“ und „Entlasse“ sind wieder abgeschnitten. Das nimmt B-E-08 zurück.
- (C) Überall die N3-Reihe: Die N9-Tests ab 160 % werden rot (Lockerung), FG-106 und FG-111 entfallen an diesen zwei Stellen. Das Aussehen bei „Maximal“ ist für (C) nicht gemessen.
- (D) N9 vor N3 mergen: geht nicht, N3 ist schon im Integrationsstand.

**Diffs** (auf `meldungen/anlagen/`, Commit `83b9320`, Präfix `N9xN3_`, in B.1):
| Datei | sha256 | numstat |
|---|---|---|
| `N9xN3_aufloesung_gegen_integration_spiel.diff` | `87a565adc9a3552e79eae3a0764dcb909134f6ec87d0a60ebafdb93c3235ecb5` | `spiel.py` +66/−35 gegen `a82fd34` |
| `N9xN3_aufloesung_gegen_n9_spiel.diff` | `0aa67be1e9d74edad506b201071ceddea8055319ef11803b77350e1bb10fc43f` | `spiel.py` +103/−46 gegen `5185e78` |
| `N9xN3_aufloesung_test_spiel_stufen.diff` | `19becdd8472c2398787704e269320204042bf3195c997d2c9ebf352b27106470` | Test +11/−5 |

**Empfehlung: (A).** Sie behält N3 bis „Sehr groß“ unverändert und den N9-Stapel ab 160 %. Die Teständerung prüft andere Eigenschaften, nach meiner Einschätzung aber nicht weniger (Einschätzung, nicht belegt). Weil sie eine Testerwartung und eine geschützte Datei ändert, frage ich vorher.
**Auflagen bei (A), vorgeschlagen:** deine Lesung der drei Diffs (neue Stoppgrenze), Bau byte-gleich, ein eigenes Tor mit den Spiel-Tests, Fotos von Mitarbeiter und Kredit von Normal bis Maximal nach der Auflösung (noch nicht gemacht). Die Fotos gehen an Nico, weil sich das abgenommene Bild unter 160 % ändert.
**Blockiert:** N9 und damit FG-106, FG-101 (V2), GradientButton und FG-111 (Schritt 5 und 9).

## Frage 3 (E2): FG-114 erteilen – Schalter am Handy an der ersten Zeile, anders gebaut als „eine Zeile START“
**Belegstufe:** Diff und numstat belegt (Anlage), Messung, Tests und Lauf berichtet (`fg114/ergebnis.md`, Antrag).

**Problem:**
- Nico hat das „Ob“ entschieden: „Foto Nachtrag: Ja sollen sie.“ (13:33 UTC, `Antwort_Nico_Handy_Schalter.md`), und die Fotos abgenommen („Frage 1: Ja“, 16:00 UTC). Darum gibt es keine Option „nicht erteilen“. Du entscheidest nur das „Wie“.
- Weisung 44, 6.3 sprach von „eine Zeile in `_switch`“. Diese eine Zeile `vertical_alignment=START` verändert aber **einzeilige** Schalter: Ihr Text rutscht hoch, Kontrollfehler K1 rot, 4551 Pixel Unterschied.
- **Gebaut ist darum:** `intrinsic_height=True` und `STRETCH`, der Schalter `TOP_LEFT`, der Text `CENTER_LEFT`. Geändert ist nur `mobile/src/main.py` `SettingsScreen._switch`, +8/−5, dazu `test_handy_sehr_gross_0632.py` +66/−0.
- Keine geschützte Datei ist betroffen.
- Ergebnis:
  - Schon bei Normal brechen 6 von 10 Schaltertexten um, im Rundgang alle 3.
  - Die 42 Zeilen mit einzeiligen Schaltern haben 0 Pixel Unterschied.
  - K1–K5 sind rot.
  - Lauf 38578347292 ganz grün.
- Diff `FG-114_handy_schalter.diff` und Antrag `FG-114_Antrag_Handy_Schalter_erste_Zeile.md` liegen auf `meldungen/anlagen/` (`bd6d979`), sha256 in B.1.

**Optionen:**
- **(a) FG-114 so erteilen:** Stoppgrenze `main.py` +8/−5, Test +66/−0. Merge in Schritt 9 von 3.1 (Vorschlag: nach FG-112, vor FG-97/105).
- (b) Nur die eine Zeile `START`: Dann ändert sich das Bild der einzeiligen Schalter (K1). Das widerspricht „einzeilig unverändert“.

**Empfehlung: (a).**
**Blockiert:** nichts außer FG-114.
**Hinweis:** Mit den Stufen „Extra groß“ und „Maximal“ (N9) ist das nur per Kopie geprüft, nicht auf dem Integrationsstand. Das echte Handy (S24) ist nicht geprüft.

## Frage 4 (E2): N14 Startwert 19 – wiederholtes Hochladen bei gleicher Marke in zwei Schreibweisen (vorbestehend, `fisi_sync.py` geschützt)
**Belegstufe:** Mechanismus und Nachstellung laut N14 belegt (`n14/ergebnis.md`, Abschnitt „Nachtrag Weisung 44, 2.5“, Teil 2), für mich berichtet. Die Folge für Nutzer nennt N14 selbst „vermutet“.

**Problem:**
- Wiederholungen von Startwert 19 („Hochladungen in Ruhe“):
  - ruhig: 0,0,4,0,0
  - unter Last: 0,0,0,0,0
  - Diagnose: 12 Läufe, einmal 4
  - vor dem Absturz: 5 × 0
- Mit N kam die 4 also in 2 von 27 Läufen vor, mit O (`69e62ae`) in 0 von 15. Das ist nicht an Last gebunden.
- Die Etiketten sind in allen Läufen gleich: **kein Datenverlust**.
- **Ursache (Mechanismus belegt laut N14):**
  - A und B haben dieselbe Löschmarke `reset_at` in derselben UTC-Sekunde, aber in zwei Schreibweisen (`…17:34:47+02:00` und `…15:34:47+00:00`).
  - `fisi_sync._later` (Z. 543) behält bei Gleichstand die eigene Marke.
  - Die Ruheprüfung (Z. 890) vergleicht die Marken als Text.
  - Folge (vermutet; beobachtet: 4 statt 0 Hochladungen in der Nachstellung): Bei jedem Abgleich lädt jedes Gerät seine Schreibweise hoch, also ein überflüssiger Commit auf GitHub, solange keine neue Marke kommt.
- Die Nachstellung zeigt dasselbe bei N, `69e62ae`, **v0.63.1** und S6b `cb60f8b`. Der Fehler besteht also **mindestens seit v0.63.1**.
- Dass er nur mit N in Startwert 19 auftritt, liegt vermutlich an Bs Nachlauf, der nicht mehr eingerechnet wird. Das ist nicht geprüft.

**Optionen:**
- **(a) Antrag für eine FG an `fisi_sync.py`, nur Antrag, kein Bau.** Inhalt: Diff, fester Test für den Gleichstand in zwei Schreibweisen, Kontrollfehler, `s1_voll.py` und Mischbetrieb. Ein Weg wäre, bei gleicher UTC-Sekunde die Schreibweise der Gegenseite zu nehmen oder den Vergleich zu normalisieren (nicht ausgearbeitet). Du entscheidest nach der Lesung, ob gebaut wird.
- (b) Bekannte Grenze: Befund mit Ursache in den Bericht 0.63.2, kein Eingriff.

**Empfehlung: (a).** Die Folge hält an, solange keine neue Marke kommt (vermutet), und wäre für Nico sichtbar (Commits auf GitHub). Ein Eingriff in den Abgleich ist aber nie E1, darum zuerst nur der Antrag. Wählst du (b), steht der Befund mit Ursache im Bericht und nicht in einer Fußnote (Weisung 44, 2.5).

## Frage 5 (E2): N14-Lauf 38575755031 – 8 rote Tests, keiner in `bekannt_rot_github.txt`
**Belegstufe:** rote Tests laut N14 aus dem Job-Log belegt, für mich berichtet. Die Liste habe ich selbst gelesen (belegt: leer, drei Einträge „(bis 14.10.)“ auskommentiert).

**Problem:** Lauf 38575755031 auf `6330eb4` ist rot: „rest“ 7 Tests (1641 s, alter Zuschnitt, ohne Zeitabbruch), „spiel“ 1 Test.
- **1–4, T-c (`test_abgleich_0632.py`):** `BG08Ersetzen.test_t_c_b_g_08_altes_geraet_ersetzt_offline_alt`, `BG08Ersetzen.test_t_c_b_g_08_neues_geraet_zuerst_ersetzt`, `GeraeteTest.test_t_c_mischbetrieb_neues_geraet_zuerst`, `GeraeteTest.test_t_c_mischbetrieb_neues_geraet_zuerst_offline_alt`. Sie waren **schon auf der N14-Basis `69e62ae` rot**, Ursache S6b × S6c (berichtet, N16; im Container auf `053931d` belegt laut N14). Auf `8888af9` + Anpassung (`7776627`) wurden sie 15/15 grün (Integrator, `welle4/tc/`). **Die T-c-Anpassung ist mit N14 nicht geprüft**, das zeigt erst das Tor in Schritt 8.
- **5–7, „die drei“:** `test_ansichten_breite.py` `Ap2BreiteTest.test_sehr_gross_1360` und `TestprojektBreiteTest.test_normal_1360`, `test_rechner_seite_breite.py` `RechnerSeiteBreiteTest.test_sehr_gross`. Der N14-Zweig enthält Fix 3b nicht (belegt laut N14: `8f18818` ist kein Vorfahr von `6330eb4`).
- **8, B-G-17 („spiel“):** `test_spiel.py` `ErfolgeTest.test_bestenliste_wird_abgeglichen`, bekannter S6b-Befund. Er hängt von der Reihenfolge ab und ist allein grün.
- Zusätzlich, schwächstes Argument: Keiner der 8 Tests prüft Code, den N14 ändert (`_stamp`, `_marker_now`, `clock_jump_unknown`) – vermutet, nicht einzeln geprüft.

**Optionen:**
- **(a) Die Einordnung reicht.** Für den N14-Merge zählt das Tor auf dem Integrationsstand (dann mit Fix 3b, S6a/S6b und der T-c-Anpassung) und ein ganzer grüner Lauf. Dazu: Zweigläufe ohne Fix 3b gleichen künftig auch gegen die drei „(bis 14.10.)“-Einträge ab und sagen das ausdrücklich; die Liste selbst bleibt leer.
- (b) Vor dem Merge zusätzlich ein GitHub-Lauf auf der Probe-Kette `89a2b68`. Dafür müsste ein Probezweig gepusht werden.

**Empfehlung: (a).**

## Frage 6 (E2): `_dash_query` – seit N7 stellt `refresh()` nach Umbenennen an Ort und Stelle nicht mehr richtig
**Belegstufe:** laut Gegenprüfung belegt (echtes Dashboard unter Xvfb, `n7/gp_fg107_fg110/ergebnis.md`, Abschnitt 2), für mich berichtet.

**Problem:**
- Der Schlüssel des Zwischenspeichers „fällig“ ist Anzahl und höchste Nummer der 5 Tabellen plus das Datum.
- `apply_question_renames` schreibt Zeilen an Ort und Stelle um. Der Schlüssel ändert sich dabei nicht, und der Zwischenspeicher liefert das alte Ergebnis.

| Stand | Seitenwechsel | explizites `refresh()` | nach neuer Zeile |
|---|---|---|---|
| `e0f9c7e` (vor N7) | falsch (3 statt 8, seit 0.50) | richtig | richtig |
| `1e7965a` (N7 ohne FG-107) | falsch | **falsch** | richtig |
| `3d09742` (nur FG-107) | falsch | falsch | falsch bis Neustart (B1) |
| `a551440` (FG-107 + FG-110) | falsch | **falsch** | richtig |

- Neu seit N7: Auch ein explizites `refresh()` (zum Beispiel nach Name speichern, Lerneinstellungen oder Begrüßung) zeigt den alten Wert. Er bleibt, bis sich eine Antworttabelle ändert, das Datum wechselt oder das Programm neu startet.
- Die Ursache liegt in **N7, nicht in FG-107/110**. FG-110 kann das nicht beheben.
- Es geht nur um die Anzeige, es gibt keinen Datenverlust. Schwere laut Prüfer **niedrig**: selten, heilt sich mit der nächsten Antwort.
- Auslöser: ein Abgleich ohne neue Zeilen nach „Alles ersetzen“ mit alter Sicherung, oder ein zweites Programm.
- Vermutet, nicht geprüft: Ohne AUTOINCREMENT (B2) gilt dasselbe für alle `_dash_query`-Einträge von N7.

**Optionen:**
- **(a) Neue FG für `app_gui.py`, zuerst als Antrag mit Diff** (zum Beispiel: `refresh()` verwirft den Zwischenspeicher „fällig“, oder `apply_question_renames` meldet die Umbenennung). Dazu ein Test für den Zwischenspeicher nach dem Umbenennen und Kontrollfehler. N7 wird in Schritt 6 trotzdem gemergt, FG-107+110 in Schritt 9 unabhängig davon; die neue FG folgt vor dem Bericht.
- (b) N7 erst mit dieser Abhilfe mergen.
- (c) Bekannte Grenze im Bericht, kein Eingriff.

**Empfehlung: (a).** Gegenüber dem Stand vor N7 ist das ein kleiner Rückschritt (`refresh()`). Er schadet keinen Daten, darum muss die Reihenfolge nicht warten.

## Frage 7 (E2): Handy „Maximal“ – Überschrift „Optische Anpassungen“ bricht mitten im Wort
**Belegstufe:** Befund auf den FG-114-Fotos (berichtet). Dass das Wort in der Liste steht, ist belegt (`git show c65f67d:fisi_trennung.py`, `ANHANG_A` enthält `"AN‖PAS|SUN|GEN"`).

**Problem:**
- Auf den Fotos zu FG-114 bricht der Bereichstitel bei „Maximal“ als `ANPASSUNG|EN`. Das ist älter und kommt nicht von FG-114.
- N9 hatte dasselbe schon gemeldet, zusammen mit `LERNINHALT|E` (`n9/ergebnis.md`, Befunde).
- Der Handy-Bereichstitel (`mobile/src/ui.py:114`, `title.upper()`) soll nach dem N8-Merge die Trennregel bekommen (Weisung 44, 2.7 / B.6). `ANPASSUNGEN` steht in der bestätigten Liste (Anhang A, 33 Wörter).
- `LERNINHALTE` und `Anwendungsentwicklung` stehen **nicht** in der Liste. FG-114 beobachtete „Anwendungsentwic|klung“ bei Extra groß und Maximal. Für diese Wörter bleibt es beim heutigen Rückfall ohne Trennstrich (belegt: `grep` in `fisi_trennung.py` auf `c65f67d` ohne Treffer).

**Optionen:**
- **(a) In 0.63.2 über den geplanten Schritt beheben:** N9 setzt die Trennregel nach dem N8-Merge. Danach Fotos von „Optische Anpassungen“ bei Extra groß und Maximal. Die übrigen Wörter kommen als Befund in den Bericht.
- (b) Wie (a), dazu die Liste um `LERNINHALTE`, `Anwendungsentwicklung` und gegebenenfalls weitere Handy-Titel erweitern. Das braucht eine Vorprüfung wie bei den 94 Wörtern und deine Lesung.
- (c) Nur als Befund in den Bericht.

**Empfehlung: (a)**, weil das schon geplant ist und keine neue FG braucht. Ob (b) nötig ist, zeigen die Fotos nach (a).

## Frage 8 (E2): FG-113 – zwei Folgepunkte
**Belegstufe:** berichtet (`fg113/ergebnis.md`).

1. **`test_workflow_0632.py` beim S5b-Merge:** Der Test prüft die Matrixzeile. Der Vorschlag aus FG-96 nennt `[spiel, lang, breite, rest]`, beim S5b-Merge muss `rest2` dazu. S5b (`bce2bcc`) ist nicht in `version-0632` (belegt), heute ist der Test also nicht betroffen.
   - Option (a): Diese eine Erwartung gilt als Teil von FG-113. Stoppgrenze etwa +1/−1 in `test_workflow_0632.py` (vermutet, nicht gezählt). Kontrollfehler: Matrix ohne `rest2` → rot.
   - Option (b): eigene FG.
   - **Empfehlung: (a).**
2. **Runner-Streuung:** Die Lücke ist so weit erklärt (B.2): 50 s waren ein Rechenfehler. Die übrigen 407 s liegen daran, dass dieselben 71 Dateien bei gleichem Code und gleichem Runner-Abbild langsamer liefen.
   - Die **Ursache der Verlangsamung ist nicht belegt.** Das Log nennt keine Hardware.
   - Die Streuung ist gemessen und reicht bis etwa Faktor 1,4: „rest2“ lief beim gleichen Stand 742 s und 524 s.
   - Option (a): Im Bericht als „nicht belegt“ führen; nach dem S6a/S6b-Merge „rest“ und „rest2“ auf GitHub neu messen.
   - Option (b): einen eigenen Messzweig mit mehreren Läufen desselben Stands.
   - **Empfehlung: (a).**
   - Risiko: Bei einem Runner, der noch etwa 15 % langsamer ist, läge jeder Teil knapp über 1350 s. Neue Dateien aus N9, N15 und FG-* landen in „rest“ und sind nicht eingerechnet.

## Frage 9 (E2): N12, S5b, N10, N11 stehen nicht in der Reihenfolge 3.1 – Nicos „Schreibfehler“ (FG-103) hat keinen Merge-Platz
**Belegstufe:** belegt (`git ls-remote`, `git merge-base --is-ancestor`, Weisung 44, 3.1 gelesen, Nico-Abschriften gelesen).

**Problem:**
- Nico, 11:54 UTC: „F1: b und den schreibfehler mit beheben“. Um 16:00 UTC hat er Lesart b bestätigt: „c 1“ statt „-c 1“ in den Bewertungskriterien, das ist **FG-103** (erteilt).
- W44 3.1, Schritt 9: FG-103 „nach dem N12-Merge“. N12 (`180789b`) ist **nicht** in `a82fd34`, und N12 steht in 3.1 an keiner Stelle.
- Ebenso FG-102 („nach S6b, S5b, N10, N11 und FG-96“): S5b `bce2bcc`, N10 `f29478b` und N11 `dfc73da` sind nicht in `a82fd34` und stehen nicht in 3.1.
- Damit hat ein ausdrücklicher Wunsch von Nico keinen festgelegten Weg in 0.63.2.

**Optionen:**
- **(a) Nach Schritt 9 einsortieren:** neuer Schritt 10 mit N12, S5b, N10, N11 (Tor je Merge), danach FG-103 (nach N12) und FG-102 (nach S5b, N10, N11, mit 3 Probeläufen).
- (b) Du nennst einen anderen Platz in 3.1.
- (c) N12, S5b, N10, N11 nicht in 0.63.2; dann entfallen FG-102 und FG-103 (Nico wäre zu fragen, weil er FG-103 ausdrücklich will).

**Empfehlung: (a).** Sie ändert an den Schritten 1–9 nichts und gibt FG-103 einen festen Platz direkt nach N12.
**Blockiert:** FG-102 und FG-103.

---

# B. Information (keine Entscheidung nötig)

## B.1 Anlagen nach Regel A (`origin/meldungen`, Kopf `83b9320`)
Alle 14 Einträge von `SHA256SUMS.txt` (13 Diffs, 1 Antrag). Die sha256 habe ich aus den Blobs auf `origin/meldungen` neu gerechnet, sie sind gleich `SHA256SUMS.txt` (belegt, 16:33 UTC). Der Commit ist der letzte, der die Datei geändert hat.

| Datei | sha256 | Commit | Stand |
|---|---|---|---|
| `FG-107_faellig.diff` | `58f5137ff0a5ab1885956e8484194f6e6d5bf8dd3751255f90fb513b7b384b6b` | `917f756` | gelesen (Nachtrag) |
| `FG-109_zahl_einheit.diff` | `ae54ca329d5c08abfbb7260a586ac578cf4776a9fb0602be6ed0b1ae2debdfc6` | `917f756` | gelesen |
| `FG-110_faellig_nachtrag.diff` | `29adca87081cea3b7557d4da9e4a7eae50cce5958a757492d038a7c07e5247d0` | `917f756` | gelesen |
| `FG-111_knopf_erweitert.diff` | `215702fdd3e625a7ed8d806f2bedfb1f66c61b5d7aa157d59cd72ef91d87a176` | `917f756` | gelesen |
| `FG-111_spiel_vorschlag.diff` | `80a75a37dad6b21ad977333ed215581eab551e54ec31e39f4b22f054dfe3a4ae` | `917f756` | gelesen; Kreditstelle bei Frage 2 (A) neu |
| `FG-112_kaestchen.diff` | `aa55ff685e32e4598ad0c22a6c315bb8eb80414dc4d5f47ef8cd7e0cbb72e2a5` | `917f756` | gelesen |
| `vorschlag_aufloesung_cc.diff` (N6) | `fa16d0465206b14ce67bed1b9f9d0f3f4d071494ea0cb82c912e3794f27b5152` | `917f756` | gelesen |
| **neu** `FG-113_rest2.diff` | `20d2502a3fd3563be26fe76cfc2ffe3961bc6eab18023b9ed5b24dd1fa21344f` | `bae72e5` | zur nachträglichen Lesung (Merge ohne weitere Weisung, W44 2.1, B.2) |
| **neu** `FG-114_handy_schalter.diff` | `3e95d3137ef69d624e4fa11905e1b0e61ac7808c39ad3f4bc6f23007cfcf8389` | `bd6d979` | Frage 3 |
| **neu** `FG-114_Antrag_Handy_Schalter_erste_Zeile.md` | `a6e007b66b90ba66bcb946f07cb9450e6d0f12ff5ab45fa21cce770e3247b971` | `bd6d979` (sha256-Zeile in `83b9320` nachgetragen) | Frage 3 |
| **neu** `FG-112_kaestchen_mit_fensterrueckgabe.diff` | `dbe2678bf73ba081f8e728d856979f60e58a7afb10bd61aed7f1ecc75c12caa5` | `8aaadec` | Frage 1 |
| **neu** `N9xN3_aufloesung_gegen_integration_spiel.diff` | `87a565adc9a3552e79eae3a0764dcb909134f6ec87d0a60ebafdb93c3235ecb5` | `83b9320` | Frage 2 |
| **neu** `N9xN3_aufloesung_gegen_n9_spiel.diff` | `0aa67be1e9d74edad506b201071ceddea8055319ef11803b77350e1bb10fc43f` | `83b9320` | Frage 2 |
| **neu** `N9xN3_aufloesung_test_spiel_stufen.diff` | `19becdd8472c2398787704e269320204042bf3195c997d2c9ebf352b27106470` | `83b9320` | Frage 2 |

Die gebauten Stände sind nach den Bauern byte-gleich zu den Anlagen: FG-109 `d0534a1`, FG-110 `a551440`, FG-111 `308e2f2`/`5185e78`, FG-113 `93bc9ce` (`git diff a82fd34 93bc9ce` = Anlage, Integrator 14:50 UTC), FG-114 `5c6087d`, N6-Auflösung (Wegwerfzweig `0ddef0d`). Für mich ist das berichtet.

## B.2 FG-113 „rest2“: Messung, Teilung, Tor, Merge
- **Stand:** `version-0632-fg113` = `93bc9ce`, ein Commit auf `a82fd34` (Fast-Forward möglich).
  - `ci_tests.sh` hat die Liste `REST2_DATEIEN` mit `test_abgleich.py`, `test_abgleich_0632.py`, `test_anzeige_pc_0632.py`, `test_spielstand_inkrementell.py` und `test_trainer_richtig_waere_pc.py`; „rest“ schließt sie aus.
  - `build.yml` hat die Matrix `[spiel, lang, breite, rest, rest2]`.
  - `test_ci_teile_0632.py` hat einen neuen Test `test_teil_rest2_genau_die_liste`.
  - Kontrollfehler (vorab 13:31:58Z): K1–K11 rot, K12/K13 Namensvergleich ABWEICHUNG, K14 Gegenprobe gleich.
- **Messung je Datei (Job-Logs über MCP, ohne Messzweig):** Die größten Dateien in „rest“ auf `a82fd34`:

  | Datei | Zeit |
  |---|---|
  | `test_anzeige_pc_0632` | 335 s |
  | `test_trainer_richtig_waere_pc` | 164 s |
  | `test_abgleich` | 163 s |
  | `test_spiel_pc_0632` | 99 s |
  | `test_subnetz_pc_breite` | 60 s |
  | `test_spielstand_inkrementell` | 48 s |
- **Lücke 981/1441 s:**
  1. Ein Rechenfehler von 50 s (belegt): Die zwei Breitendateien brauchten in „rest“ auf `8f18818` 371 s, nicht 421 s. Richtig erwartet waren also 1034 s.
  2. Die übrigen 407 s: Dieselben 71 Dateien liefen langsamer, 1031 → 1438 s.
     - 47 Dateien waren langsamer, 22 gleich, 2 schneller.
     - Am meisten trug `test_anzeige_pc_0632` bei (+143 s), davon `EigeneFarbenTest.test_b_j_03_ohne_rueckschritt` 34,5 → 92,9 s.
     - Code und Runner-Abbild (ubuntu24/20261004.327) waren gleich.
  3. Die Ursache ist Runner-Geschwindigkeit, **vermutet, nicht belegt.** Ein Hinweis darauf: Der FG-96-Lauf war bei 64 gemeinsamen Dateien 1179 s gegenüber 910 s langsam. Der schnelle Ausreißer war also der Lauf auf `8f18818`.
- **Teilung nach Endlast (Rechnung):** „rest“ gemessen 731 s, dazu 447 s → etwa **1177 s**. „rest2“ gemessen 710 s, dazu 468 s (`test_abgleich_0632` in der S6b-Fassung) → etwa **1178 s**. Mit den eigenen Läufen gerechnet: „rest“ etwa 1180 s, „rest2“ etwa 990–1210 s.
- **Läufe auf `93bc9ce`:**
  - 38574101656 zählt nicht: android `failure`, ein beschädigter Download, Infrastruktur. Die Testjobs waren dort grün: „rest“ 735 s, „rest2“ 742 s.
  - **38576166779: ganz grün**, alle 12 Jobs. Zeiten: spiel 96, lang 245, breite 461, rest 732, rest2 524, windows 616 s. **Rote Tests: keine.**
- **Offene Punkte:** Runner-Streuung (Frage 8); `test_workflow_0632.py` beim S5b-Merge (Frage 8); „breite“ liegt nach N8 rechnerisch über 1350 s, dann kommt beim N8-Merge „breite2“ (Weisung 43, 2.10, ohne Frage).
- **Basis-Tor `a82fd34` (vor dem Merge, berichtet, `integration/PROTOKOLL.md` 16:12 UTC):** `tor_a82fd34_4` **GRÜN**, Einzelheiten in B.11.
- **Tor-Werkzeug (berichtet, Protokoll 16:20 UTC; Teile belegt per `grep`):** `merge_tor.sh` ist nach dem Ende von `tor_a82fd34_4` um „rest2“ erweitert und kennt den Tag-Standard. Der vorab festgelegte Kontrollfehler (14:49:35Z, Kontroll-Commit `d13dcdd`, nie gepusht, `KontrollfehlerRest2Test.test_kontrolle_rest2_rot`) ist gelaufen: **ROT wie erwartet**, einziger roter Test genau dieser. „rest2“ lief dabei mit 4 Dateien (`test_abgleich` 197, `test_anzeige_pc_0632` 469, `test_spielstand_inkrementell` 86, `test_trainer_richtig_waere_pc` 207 s), die rest2-Dateien laufen im Tor also wirklich. Danach wurde das Tor auf `93bc9ce` gestartet.
- **Warum vor dem Versand dieser Meldung gemergt wird:** W44 2.1 erlaubt den Merge von FG-113 „ohne weitere Weisung, wenn alle Auflagen erfüllt sind und der Diff nach Regel A in Meldung 45 liegt“. Der Diff liegt seit `bae72e5` auf `meldungen` (sha256 in B.1). Du liest ihn nachträglich; eine Korrektur wäre ein Folge-Commit (wie bei `breite2`).
- **Merge:** Tor auf `93bc9ce` läuft (Werkzeug mit rest2, B.2); Fast-Forward erst nach grünem Tor, vollen Suiten und Container-`ibus`. Ergebnis in Nachtrag 45a.

## B.3 FG-107 + FG-110: Bau, Gegenprüfung, Windows
- **Bau (berichtet, `n7/fg107_fg110/ergebnis.md`):** `version-0632-n7-fg` = `a551440` auf `3d09742` (FG-107) auf `1e7965a` (N7).
  - `git diff 3d09742 a551440` ist byte-gleich zur Anlage `29adca87…47d0` (`fisi_lernen.py` +22/−5, Test +127/−1).
  - KF12–KF16 5/5 rot, KF18–KF23 6/6 rot. Der Stand ohne Eingriff ist grün (`test_faellig` 24 OK, `test_leistung_suche` 25 OK).
  - Fingerabdrücke wie vorher (`lerninhalte` weicht vom Soll 0.63.1 ab, wie seit S4).
  - Der Zweig enthält FG-107 **und** FG-110. Beide gehen nur in einem Merge.
- **Lauf 38572154311 auf `a551440`:** Nur „rest“ ist rot, mit genau den drei Tests `Ap2BreiteTest.test_sehr_gross_1360`, `TestprojektBreiteTest.test_normal_1360` und `RechnerSeiteBreiteTest.test_sehr_gross` (Fix 3b fehlt im Zweig). „rest“ 1577 s (alter Zuschnitt).
- **Gegenprüfung (neuer Agent, eigene Werkzeuge, `n7/gp_fg107_fg110/ergebnis.md`):**
  - **B1 behoben.** Zweiter Weg mit drei Programmen: `3d09742` zeigt 0 statt 14 fällig, `a551440` stimmt in jedem Schritt.
  - Zufallsprobe mit den Saaten 700000–700099: `3d09742` 3500 Abweichungen, `a551440` 0.
  - Echtes Dashboard: `3d09742` zeigt 3 statt 8 Karteikarten, `a551440` und `1e7965a` zeigen 8.
  - Kein hoher oder mittlerer Befund im Diff.
  - Niedrig: Die Anlage FG-107 enthält `test_faellig_0632.py` (683 Z.) nicht, die Datei liegt nur im Zweig. `test_leistung_suche_0632.uncached_snapshot` vergleicht seit FG-107 gegen einen frischen Index, nicht mehr gegen `from_db`.
- **`_dash_query`:** Frage 6.
- **B3 (Schreiben während der Sperre, Zeitgrenze 5 s, Linux-Container):**
  - Anzeigen schreibt nichts (sha256 aller Dateien im Datenordner gleich).
  - Index-Vollaufbau mit 70.000 Zeilen: Schreiben wartet bis 0,24 s.
  - Mit 300.000 Zeilen: bis 1,13 s.
  - **Mit 1,5 Mio. Zeilen: 3/3 „database is locked“.** `from_db` geht dort mit 0,86–1,60 s.
  - Die Schwelle liegt vermutlich bei 1,2–1,5 Mio. Zeilen, unter Windows niedriger (nicht gemessen).
  - Schwere niedrig. Das kommt nach Weisung 44, 3c in den Bericht, ohne Umbau.
- **Windows (Lauf 38575978718, Messzweig `messung-0632-fg110` `b35356b`, nie mergen; gemessen auf dem Zweigstand, nicht auf dem Integrationsstand):**

  | Fall | vorher (gesamt/fällig) | nachher (gesamt/fällig) |
  |---|---|---|
  | nach 1 Quizantwort, Normalfall | 874/343 ms | 562/21 ms |
  | nach 1 Quizantwort, Worst Case (alter Fragetext, `always_full`) | 852/338 ms | 848/320 ms |
  | nach Karteikarte, Normalfall | 834/342 ms | 521/21 ms |
  | nach Karteikarte, Worst Case | 822/338 ms | 808/325 ms |

  Der Worst Case ist so teuer wie vor FG-107, also kein Rückschritt. „Heute fällig“ ist in allen 80 Fällen gleich. Nicos Ziel 1 s (18b) ist in allen vier Fällen erreicht. Nach dem Merge wird auf dem Endstand neu gemessen, der Bericht nimmt diese Werte.
- **Noch offen für den Merge (Schritt 9):** ein ganzer grüner Lauf auf dem Integrationsstand, die Windows-Messung auf dem Endstand und die Wiederholung von KF12–KF16/KF18–KF23 auf dem Integrationsstand (siehe Selbstkontrolle 2.3 Nr. 3).

## B.4 Fingerabdruck „code“ (ein Satz, Weisung 44, 2.3)
Der Teil „code“ erfasst nur `fisi_game.py`, `fisi_game_gui.py` und `mobile/src/spiel.py` sowie aus `fisi_core.py` die Funktionen `raid_values`, `raid_input_values`, `raid_input_problem` und `ipv4_values` samt der `fisi_core`-Funktionen, die sie aufrufen. Er schützt also nur Spiel und Spiel-Rechner, nicht `fisi_lernen.py`, nicht `app_gui.py` und nicht den Rest von `fisi_core.py` (belegt: `bau_0.62.4/werkzeuge/fingerabdruck_0624.py` Z. 50–51; `merge_tor.sh` Z. 75 nutzt dieses Werkzeug).

## B.5 S1c2: 6a (b), Probe-Merge, 6b-Messung
- **6a (b), Commit `3411ce9`, gepusht:**
  - `Z3_SCHRIFT_ERWARTUNG`: Inter „erwartet“, DejaVu Sans „erwartet“, TkDefaultFont „null“ (`fehler == []`). Bei einer unbekannten Schrift gelten der Deckel 70 und ein `VERMERK` im Log.
  - Schrifterkennung: Gemeldete und gezeichnete Familie werden in allen 83 Fällen verglichen.
  - Kontrollfehler (vorab 13:33:15Z): KS1–KS5 rot. KS1 und KS2 stören die Schrifterkennung (gemeldet „Inter“ / „TkDefaultFont“, gezeichnet anders) und werden rot. V1 ist grün mit sichtbarem VERMERK.
  - Container 83/83 OK.
  - **Lauf 38576551817:** Einziger roter Test ist `TestprojektBreiteTest.test_normal_1360` (Fix 3b fehlt im Zweig). Auf GitHub kein VERMERK.
  - Die übernommene, noch nicht committete Änderung des verlorenen Agenten wurde vor der Übernahme gelesen und beurteilt (E1-11).
- **Neuer Probe-Merge auf `a82fd34` (Wegwerf-Klon, nicht gemergt):**
  - 8 Konfliktstellen, nur in `test_ansichten_breite.py`, Zeile für Zeile in `s1c2/nachbesserung/probe_merge_w44/pm_aufloesung_protokoll.md`.
  - Das doppelte `_make_ohne` aus Fix 3b ist entfernt.
  - Die ganze Datei im Merge-Stand hat **123 Tests** (alle 83 S1c2-Namen und alle 51 `a82fd34`-Namen). Mit und ohne Inter OK, Deckel unverändert.
- **6b-Messung, Optionen „Sehr groß“ 1120 (die Seite mit 785 > 781 in 0.63.1):**

  | Schrift | start | alles offen | wieder zu | Überstand |
  |---|---|---|---|---|
  | Inter | 769 | 781 | 735 | **0** |
  | DejaVu Sans | 778 | 779 | 746 | **0** |
  | TkDefaultFont | 767 | 781 | 759 | **0** |

  Kein Rückschritt gegenüber 0.63.1 (4 px), darum keine Frage. Zur Vollständigkeit „Fortschritt mit Daten“ bei SG 1120 (bekannte Grenze, Deckel 70): Inter +11, DejaVu +59, TkDefaultFont 0. Den Wert von 0.63.1 für diese Seite habe ich hier **nicht geprüft**.
- Der Satz zu 6b ging in deinem Wortlaut an Nico (Teil 2, Punkt 4).

## B.6 FG-109: fertig, Optik abgenommen
- **Stand:** `version-0632-fg109` = `cbbbad1` (`d0534a1` Code byte-gleich `ae54ca32…`, `cbbbad1` mit neuem festem PDF-Test).
- **numstat `a82fd34..cbbbad1`:**
  - `fisi_game.py` +19/−8, `spiel.py` +4/−2, `fisi_projekt.py` +1/−1 (gleich der Stoppgrenze)
  - **Teständerungen:** `test_spiel.py` +1/−1, `test_rechner_0632.py` +2/−2; neu `test_zahl_einheit_0632.py` +210, `test_pdf_festwert_0632.py` +94
  - `inhalte/*` unberührt
- **Kontrollfehler:** Mit zurückgenommenem Code werden beide angepassten Bestandstests rot, dazu 8 Tests der neuen Datei. KF1–KF12 rot.
- **Text-Export (T8):** schreiben und lesen, UTF-8 und UTF-8-BOM/CRLF: OK.
- **PDF-Festtest (E1 aus dem Nachtrag):**
  - festes Datum 14.10.2026
  - P1: sha256 `01546b98…0bbbd`, 3499 B, erzeugt mit dem Code von `a82fd34`
  - P2: normales Leerzeichen vor €
  - KF-P1 (PDF-Pfad gibt die geschützte Variante aus) und KF-P2 sind rot. Der erste KF-P1-Versuch griff nicht und wurde wiederholt (Fehler 4).
- **Fingerabdrücke:** „code“ `14f69588…` → `c836a98e…` (gewollt, gleich Antrag), alle anderen gleich.
- **Lauf 38576233414:** ganz grün, 0 rote Tests; „rest“ 1470 s (> 1350 s, ohne FG-113, Sofortmeldung).
- **Befund „Bisher … gezahlt“ (`tax_status_lines`, `_whole_euro`):** Dort kann das „€“ allein umbrechen. Das bleibt unverändert, Test T4 hält die Zeile fest. In den Fotos ist es nicht sichtbar, weil der Spielstand noch keine Voranmeldung hatte, der Umbruch dort ist also **nicht geprüft**. Das kommt in den Bericht (Weisung 44, 4e (a)).
- **Nico 14:59 UTC: „Ja für beide“** (FG-109 und FG-111), „Optik offen“ ist aufgehoben. Der Hinweis „Liste ist Untergrenze“ fehlt noch (eigene Fehler Nr. 7).
- **Offen (W44 2.4):** FG-109 und N9 ändern beide `mobile/src/spiel.py`. Beim zweiten dieser Merges ein eigenes Tor mit den Spiel-Tests (B.10, Schritt 9).

## B.7 FG-111 in N9 (`5185e78`): Bedingungen erfüllt, Merge wartet auf Frage 2
- **Beide Diffs byte-gleich**, die lange `spiel.py`-Zeile ist nicht umbrochen.
- **Tests:** `test_zugang` 17 OK, `test_schriftstufe_0632` 19 OK (mit beiden Diffs). Kontrollfehler F1–F14, K1–K6 und P1–P7 rot.
- **Pixel:** Normal/Groß/Sehr groß 42/42 gleich. Extra groß und Maximal 28 anders, wie erwartet.
- **Messrunde in den echten Ansichten:** M3, M7, S2, S3, S5 bei Extra groß und Maximal lesbar. M7 bricht bei Maximal an der Wortgrenze zweizeilig um.
- **Lücke für den Bericht:** weitere Zustände (WiSo-Seiten der Prüfung, Angebot für Kundenprojekte, mehrere Kredite, Erfolge-Reiter der Reise) und die Reihen M1, M2, M4–M6, M8, M9, S1, S4 nur im Nachbau.
- **Ursache der +2 px (belegt laut N9):**
  - Knöpfe mit 1-px-Rahmen (`kind="ghost"`) werden ab 160 % 2 px höher. Seit `height=None` zählt der Rahmen zur Höhe.
  - Probe: ghost 61 → 63, primary 61 → 61. Ohne Rahmen verschwinden die +2 px, mit Rahmen sind sie da.
  - Unter 160 % bleibt alles bei 49.
  - „Rundung“ ist damit widerlegt.
- **Lauf 38575841120:** Nur „rest“ ist rot, mit den drei früheren Listentests (Fix 3b fehlt). „rest“ 1692 s, noch mit dem alten Zuschnitt ohne „breite“ und „rest2“. Dieser Wert ist nicht mit der 1650-s-Schwelle aus Weisung 44, 2.1 vergleichbar, für sie zählt der Integrationsstand (nicht geprüft).
- **Nicos Abnahme (14:59 UTC)** galt diesem Stand ohne N3. Bei Frage 2 (A) ändert sich das Bild unter 160 %, dann gehen neue Fotos an Nico.

## B.8 N14 (`6330eb4`): Bedingungen aus Weisung 44, 2.5
- **Wortlaut:** übernommen wie vorgegeben.
- **Fester Test** `test_ausnahme2_uhr_gestellt_fremde_loeschung_nach_ersetzen`, Kontrollfehler K2-a bis K2-e rot.
- **„2 h zu spät“ ist im Endstand nicht vorhanden (belegt laut N14):**
  - Probe-Kette im Scratch: `a82fd34` + S6a + S6b + N7 `3d09742` + N16 + N14 → `89a2b68`.
  - Ergebnis: S6b `cb60f8b` setzt die Marke 18:54:56 UTC (rot), N14 16:55:11 UTC (grün), das Kettenende 16:55:23 UTC (grün).
  - Darum ist keine E3-Frage nötig.
  - Einschränkung: N5, N8 und FG-107/110 waren nicht in der Kette, dafür kommt der weitere `s1_voll.py`-Lauf vor dem Bericht.
- **Startwert 19:** Frage 4. **Lauf 38575755031:** Frage 5.
- **Offen:** ein ganzer grüner `s1_voll.py`-Lauf auf dem Endstand der Planreihenfolge (Merge-Bedingung) und einer vor dem Bericht nach FG-107/110.

## B.9 94 Einträge / 92 Wörter (Rückfrage Weisung 44, 2.7)
Ja, das ist richtig: Die 2 Einträge, die in keiner der drei Listentitel-Gruppen stehen, sind **„Ausbildungsverordnung“ (Quelle „Titel“)** und **„Schnittstellenkennung“ (Quelle „Rechenwege“)**. Also 94 = 92 Wörter aus den Listentiteln (32 AP1 + 55 AP2 + 11 Testprojekte = 98 Vorkommen, 6 Wörter in zwei Listen) + 1 + 1. Belegt durch Zählen der Quellspalte in `n8/lange_woerter_ohne_eintrag.md`: 27 + 3 + 2 + 51 + 1 + 8 = 92 Listentitel-Wörter, dazu je 1 „Titel“ und 1 „Rechenwege“.

## B.10 Stand der Merge-Reihenfolge (Weisung 44, 3.1)
| Schritt | Inhalt | Stand | Stufe |
|---|---|---|---|
| 1 | FG-113 | siehe B.2 (Lauf 38576166779 grün, Basis-Tor grün, Merge läuft) | berichtet |
| 2 | S6a → S6b | angehalten (STOPP 13:23 UTC); lokale Merges `8ffcf7d`, `8888af9`, `7776627` verworfen, nie gepusht. T-c-Nachweis: auf `8888af9` ohne Anpassung genau 4 T-c rot; auf `8888af9` + Anpassung (`7776627`, verworfen) 15/15 grün; KF a-2 9 rot. Wartet auf Schritt 1 | berichtet |
| 3 | S1c2 | `3411ce9` fertig, Probe-Merge 123 Tests OK; wartet auf Schritt 2 | berichtet |
| 4 | N5 → N8 | `98f63ff` / `c65f67d` unverändert; N8: Einzellauf `test_trennung_0632.py` auf GitHub, danach ein ganzer Lauf, beim N8-Merge „breite2“ | belegt (SHA) |
| 5 | N9, N15 | N9: Frage 2. N15 `e8c8442`: Probe-Merge konfliktfrei (Baum gleich `git merge-tree`); das Probe-Tor ging beim Absturz verloren, Ergebnis unbekannt (nicht geprüft) | berichtet |
| 6 | N7 ohne FG-107, N16 | `1e7965a` / `e32064a` warten; Frage 6 betrifft N7 | belegt (SHA) |
| 7 | N6 | Vorabbau auf Wegwerfzweig `wegwerf-n6-vorab` (`0ddef0d`), Auflösung byte-gleich `fa16d046…`; Zeile `self.ups_button_rows = []` vorbereitet, Commit erst nach Kontrollfehler. Tor: offen, kommt in Nachtrag 45a. Eigenes Tor N6 × S5c beim S5c-Merge | berichtet |
| 8 | N14 | `6330eb4`; Bedingungen siehe B.8; `s1_voll.py` auf dem Endstand offen; T-c-Anpassung mit N14 erstmals im Tor (Frage 5) | berichtet |
| 9 | FG-107+110, FG-109, FG-111, FG-112, FG-97/105, FG-102, FG-103 | FG-107+110 `a551440` bereit bis auf Lauf, Windows-Messung und KF auf dem Integrationsstand; FG-109 `cbbbad1` bereit, Optik abgenommen; FG-109 × N9/FG-111 in `spiel.py`: eigenes Tor mit Spiel-Tests (W44 2.4); FG-111 Frage 2; FG-112 Frage 1; FG-97/105 in N8; FG-102 und FG-103 erteilt, nicht gebaut, ihre Vorbedingungen N12, S5b, N10, N11 stehen nicht in 3.1 (Frage 9); **FG-114** (neu, Frage 3) | berichtet |
| (10) | N12, S5b, N10, N11, dann FG-103, FG-102 | Vorschlag Frage 9; alle vier nicht in `a82fd34` | belegt |

## B.11 Läufe seit Meldung 44 und **alle** roten Tests
Abgleich mit `werkzeug/bekannt_rot_github.txt`: Die Liste ist **leer**. Die drei Einträge sind mit „(bis 14.10.)“ auskommentiert (belegt, gelesen). Das S1c2-Ergebnis schreibt zu `test_normal_1360` noch „steht in bekannt_rot_github.txt“; das gilt nur für die alte Fassung der Liste, heute ist der Eintrag auskommentiert. Die Zweige ohne Fix 3b zeigen genau diese drei Tests (im Folgenden „die drei“):
- `test_ansichten_breite.py Ap2BreiteTest.test_sehr_gross_1360`
- `test_ansichten_breite.py TestprojektBreiteTest.test_normal_1360`
- `test_rechner_seite_breite.py RechnerSeiteBreiteTest.test_sehr_gross`

„alter Zuschnitt“ = Lauf ohne Job „breite“, „rest“ enthält dort die Breitendateien.

| Lauf | Stand | Ergebnis | alle roten Tests | Abgleich | „rest“ |
|---|---|---|---|---|---|
| 38574101656 | FG-113 `93bc9ce` | zählt nicht (android, Download defekt) | keine in den Testjobs | – | 735 s (rest2 742 s) |
| 38576166779 | FG-113 `93bc9ce` | **ganz grün** | keine | keine Abweichung | 732 s (rest2 524 s) |
| 38572154311 | N7-fg `a551440` | rot, nur „rest“ | die drei | genau die früheren drei, Fix 3b fehlt | 1577 s (alter Zuschnitt) |
| 38575755031 | N14 `6330eb4` | rot, „rest“ und „spiel“ | 8 Tests, siehe Frage 5 | keiner in der Liste → Frage 5 | 1641 s (alter Zuschnitt) |
| 38575841120 | N9 `5185e78` | rot, nur „rest“ | die drei | genau die früheren drei | 1692 s (alter Zuschnitt) |
| 38572865128 | FG-109 `d0534a1` | grün | keine | – | nicht berichtet |
| 38576233414 | FG-109 `cbbbad1` | **ganz grün** | keine | keine Abweichung | 1470 s |
| 38576551817 | S1c2 `3411ce9` | rot, nur „rest“ | `TestprojektBreiteTest.test_normal_1360` | 1 der früheren drei; die zwei anderen sind auf diesem Zweig nicht rot (schon in Meldung 44 so, Ursache nicht geprüft) | 1581 s (alter Zuschnitt; Jobdauer 27 min 4 s) |
| 38578347292 | FG-114 `5c6087d` | **ganz grün** | keine (laut Bauer: Job-Ergebnisse belegt, Einzeltests berichtet) | keine Abweichung | 1469 s (breite 486 s) |
| 38575978718, 38572079729 | Messzweige `messung-0632-fg110` | Windows-Messung (B.3) | – | – | – |

- Die Zweigläufe ohne FG-113 lagen über 1350 s. Mit „breite“: 1470, 1469 s; alter Zuschnitt: 1577, 1581, 1641, 1692 s. Das ist die Sofortmeldung nach Weisung 42. Die Abhilfe ist FG-113, Schritt 1.
- **Merge-Tor seit Meldung 44:** `tor_a82fd34_4` (14:08–16:12 UTC, nacheinander, erweitertes Werkzeug, Tags `v0.50 v0.56 v0.62.3 v0.63.1`) **GRÜN**.
  - inter: ibus 23 OK (Vorabprüfung), rest 72 Dateien / 1457 Tests, breite, lang, spiel; alle 9 Teile Rückgabe 0.
  - ohne_inter: dieselben Teile ohne ibus, alle 0.
  - 0 rote Tests, beide Listen leer, keine Abweichung.
  - Zeiten inter: ibus 32, rest 2338, breite 697, lang 443, spiel 248 s; ohne_inter: rest 2160, breite 653, lang 442, spiel 245 s; Wanduhr 7401 s, Last bis 11,4.
  - **`LoadingHintTest` war diesmal grün** (Teil lang inter, 443 s). Im Tor `a82fd34` vom Vormittag war er unter Last bis 17 rot. Die Diagnose nach W44 2.2 steht in B.15.
  - Fingerabdrücke alt, zahlen, konstanten und spielinhalte gleich Soll; lerninhalte und code weichen ab wie seit S4/N4.
  - Mischbetrieb: Die Tests liefen erstmals im Tor, keiner wurde als „nicht verfügbar“ übersprungen (einzige Skips: 2 IBus-Nachstellungen je Lauf „rest“, wie bisher).
  - Abgebrochen und nicht gewertet: `tor_8ffcf7d` (STOPP), `tor_a82fd34_2` (Absturz), `tor_a82fd34_3` (Tags fehlten).
  - Tor auf `93bc9ce` (FG-113) läuft, Ergebnis im Merge-Stand B.2.

## B.12 Tor-Werkzeug: Mischbetrieb und Tags (E1, strenger)
- Die Tor-Kopien haben jetzt die Tags `v0.50 v0.56 v0.62.3 v0.63.1` flach, und ein übersprungener Test zählt als ROT.
- Selbsttest `selbsttest_20261014T132726Z` (K0–K9, Kontroll-Commit mit `test_alter_code_da`, Gegenprobe): BESTANDEN (berichtet).
- Der Standard `TOR_GIT_TAGS` mit `v0.50` und `v0.56` steht im Werkzeug (belegt: `merge_tor.sh` Z. 54).
- „rest2“ ist im Werkzeug (belegt, `grep` Z. 15, 58, 60, 149–150), eingesetzt nach dem Ende von `tor_a82fd34_4`; Kontrollfehler rot wie erwartet (B.2).

## B.13 Container-Absturz gegen 13:42 UTC
- **Was geschah:** Prozess gegen 13:42:52 UTC unerwartet beendet (Auto-Wiederherstellung: „häufigste Ursache: Speicher“, **vermutet**), Rechner 13:47 UTC neu hochgefahren. Zeitwiderspruch zum Protokoll siehe eigene Fehler Nr. 6.
- **Erhalten:** auf GitHub fg109 `d0534a1`, fg113 `93bc9ce`, n7-fg `a551440`, n9 `5185e78`, n14 `6330eb4`, s1c2 `7acfccb`; im Container-Arbeitsbaum die noch nicht committete 6a-(b)-Änderung (übernommen, E1-11) und die Tor-Erweiterung in `werkzeug/`. Die Arbeitskopie `/home/claude/n7_fg110b` des verlorenen Agenten liegt noch.
- **Verloren:** **N15-Probe-Tor (Ergebnis unbekannt, nicht wiederholt)**; Basis-Tor `a82fd34_2` (neu als `_4`); laufende Fotoaufnahmen FG-111/FG-109, Kontrollfehler-Läufe und die N14-Lastserie von 13:39 UTC (alle neu gemacht); Warteprozesse auf GitHub-Läufe (die Läufe liefen weiter).
- **Speicherregel seit etwa 13:55 UTC (E1-8):** höchstens 1 GUI-Prozess je Agent, Tor mit `TOR_STROEME=1`, vor jedem Fotolauf `free -m` (13:53 UTC: 655 MB von 16 GB belegt; FG-109: über 13 GB frei). Dateien `a`, `n` und die fremden Xvfb-Prozesse wurden nicht angefasst (berichtet).

## B.14 Nicos Entscheidungen seit Meldung 44
| Zeit (UTC) | Wortlaut | Bedeutung | Abschrift |
|---|---|---|---|
| 11:54 (schon in M44) | „F1: b und den schreibfehler mit beheben / F2: b / Die anderen Punkte sind zufriedenstellend.“ | F1 (b) → FG-111, F2 (b) → FG-112; „Schreibfehler“ beheben (Lesart: siehe 16:00) | `Antwort_Nachtrag_39_Nico.md` |
| 13:33 | „Foto Nachtrag: Ja sollen sie.“ | Handy-Schalter an die erste Zeile → FG-114 (Frage 3) | `Antwort_Nico_Handy_Schalter.md` |
| 14:59 | „Ja für beide.“ | Optik FG-109 und FG-111 (Stand `5185e78`, ohne N3) abgenommen, „Optik offen“ aufgehoben | `Abnahme_Fotos_FG109_FG111_Nico.md` |
| 16:00 | „Frage 1: Ja / Frage 2: b“ | Optik FG-114 abgenommen; „Schreibfehler“ = **Lesart b**: „c 1“ statt „-c 1“ in den Bewertungskriterien, das ist **FG-103** (erteilt, Bau nach dem N12-Merge; N12 hat noch keinen Platz in 3.1, Frage 9). Die Lesarten a und c sind nicht gemeint | `Antwort_Nico_Fotos_Teil2.md` |

Damit ist keine Optik mehr offen: FG-109, FG-111 und FG-114 sind abgenommen, FG-112 hat kein „Optik offen“. Bei Frage 2 (A) gehen neue Fotos von Mitarbeiter und Kredit an Nico.

## B.15 Diagnose `LoadingHintTest` (Weisung 44, 2.2)
Offen, kommt in Nachtrag 45a. Grund: Die Diagnose braucht künstliche Last und würde das laufende Tor stören. Im Basis-Tor war `LoadingHintTest` diesmal grün (B.11).

Zur Einordnung (berichtet, Protokoll 16:12 UTC): Im Basis-Tor `tor_a82fd34_4` war `LoadingHintTest` grün (Teil lang inter 443 s, Last bis 11,4). Im Tor `a82fd34` vom Vormittag war er rot (Last bis 17), allein bei Last 5,2 grün.

## B.16 Selbst entschieden (E1) seit Meldung 44
| Nr | Entscheidung | Begründung | Beleg |
|---|---|---|---|
| E1-6 | Tor-Erweiterung Mischbetrieb eingesetzt: Tags in der Kopie, übersprungen = ROT | nur strenger; der Selbsttest ist bestanden | `integration/PROTOKOLL.md` 13:15 und 13:57 UTC |
| E1-7 | `TOR_GIT_TAGS` um `v0.50 v0.56` erweitert, zuerst als Umgebungsvariable, seit 16:20 UTC Standard im Werkzeug | `test_08_alte_datenbanken` braucht diese Tags; sonst wäre das Tor durch das Werkzeug rot | dito, 14:08 und 16:20 UTC; `merge_tor.sh` Z. 54 |
| E1-8 | Speicherregel: 1 GUI-Prozess je Agent, `TOR_STROEME=1` | nach dem Absturz | B.13 |
| E1-9 | FG-109 PDF-Festtest mit festem Datum und zusätzlicher Prüfung P2 | im Rahmen des Nachtrags 2.2 (E1); ohne festes Datum hinge der Test vom Tag ab | `fg109/ergebnis.md` |
| E1-10 | Lauf 38574101656 (Infrastruktur) als ganzer Lauf neu gestartet, kein Einzel-Neustart | Regel Infrastruktur-Ausfall | `fg113/ergebnis.md` |
| E1-11 | Noch nicht committete 6a-(b)-Änderung des verlorenen S1c2-Agenten übernommen, nach Lesung | sie setzt 6a (b) vollständig um; einzige Änderung ist ein Kommentar | `s1c2/nachbesserung/ergebnis.md` |
| E1-12 | Nachtrag an Nico in zwei Teilen (Fotos Teil 1 um ~15:00 UTC, Teil 2 um ~15:45 UTC) statt einer Datei `Nachtrag_Meldung_44_Fotos.md` | FG-109 und FG-111 waren früher fertig als FG-114 | `meldungen/Nachtrag_Meldung_44_Fotos_Teil1.md`, `…_Teil2.md` |

---

## Hinweis
Meldung 45 liegt auf `meldungen`, Commit: siehe Begleitzeile von Nico (Hash wird dort genannt).
