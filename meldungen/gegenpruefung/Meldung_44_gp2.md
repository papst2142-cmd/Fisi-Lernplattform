# Zweite unabhängige Gegenprüfung Meldung 44 (Fassung 2)

Geprüft: `bau_0.63.2/meldungen/Meldung_44_Fragen_und_Stand.md`, Fassung 2 (898 Zeilen, 83.389 Bytes), am 14.10.2026 nach 12:59 UTC.
Prüfer: unabhängig, hat die Meldung nicht geschrieben. An der Meldung nichts geändert, nichts committet, nichts gepusht, nichts gelöscht (zwei eigene Wegwerf-Worktrees für `git apply --check` angelegt und wieder entfernt).
Zeilenangaben beziehen sich auf Fassung 2.

**Gesamturteil:** Die Befunde H1–H4 und M1–M8 der ersten Gegenprüfung sind eingearbeitet. Alle SHA-256-Werte und Zeilenzahlen zu Frage 8, 9 und 10 stimmen (selbst geprüft). Vor dem Versand sind noch zu korrigieren: **1 hoher Befund** (Frage 9: Stoppgrenze widersprüchlich), **6 mittlere** (veralteter Hinweisblock mit „Platzhalter“/„entsteht“, N5-Stand veraltet, Frage 8 Tor-Auflage unvollständig, Frage 9 Bestand/Blockiert, Frage 10 Handy-Prämisse an Nico, Frage 10 Verhältnis zu S1c2/6a) und mehrere geringe.

---

## 1. Befunde der ersten Gegenprüfung: eingearbeitet?

| Befund | eingearbeitet | Zeile(n) in Fassung 2 | Anmerkung |
|---|---|---|---|
| H1 | ja | 16, 92–95, 153–185, 581–583 | 2a/2b mit Optionen; altes E1-4 gestrichen. Die Nummer E1-4 ist jetzt neu belegt (N9-Index-Test); Z. 583 erklärt das, siehe G7 unten. |
| H2 | ja (stärker als vorgeschlagen) | 16, 89–91, 414, 540, 607 | Als eigener Fehler, N5 zurückgestellt. **Stand aber veraltet**, siehe M2. |
| H3 | ja | 218, 226–232 | Abwägung sichtbar; Empfehlung jetzt (c). Lauf 38506811682 auf `1e7965a`: nur „rest“ `failure` (selbst per `gh` geprüft). |
| H4 | ja | 390, 394–413 | Satz zum Rückfall richtig; 14 Zeilen gegen Anhang A abgeglichen, alle gleich. |
| M1 | ja | 19, 566 | – |
| M2 | ja | 15, 151 | Z. 15 „S6b-Merge“, Z. 151 „S6a/S6b-Merge“, siehe G2. |
| M3 | ja | 127–132 | „Zwischen `8f18818` und `a82fd34` liegt nur FG-96“ selbst geprüft (`git log --first-parent`): richtig. |
| M4 | ja | 267–272, 305–309 | „Reise-Unterreiter“ fehlt in der Liste „nicht fotografiert“ (FG-109-Antrag Z. 70), siehe G8. |
| M5 | ja | 251–257, 580 | – |
| M6 | ja | 16, 61–63, 608 | `6ffda17` kein Vorfahr von `a82fd34`: selbst geprüft, richtig. |
| M7 | ja | 60, 558–559 | `n15/logs/frage14b/ci_rest_115784933856.log`: 1098 s und genau die 3 Listentests (selbst gelesen), richtig. |
| M8 | ja | 96 | – |
| G1 | teilweise | 6 | „etwa 12:25 UTC“, aber Frage 9/10 enthalten Werte von 12:28–12:59 UTC, siehe G1 unten. |
| G2–G6, G9–G12 | ja | 14, 45, 17/59, 35/386–389, 586–587, 201, 239/247/297, 596–601, 845–853 | – |
| G7 | ja | 28 | – |
| G8 | ja | 2 | 6b ist E1 geworden, daher fehlt es zu Recht. |
| Vermeidbare Fragen | ja | 581, 364–374, 416–440, 628–634 | – |
| Tabelle unerwähnte Auflagen | ja | 41, 44, 46, 52, 61–63 | – |

---

## 2. Neue Fragen 8, 9, 10 gegen die Quellen

### Selbst geprüft (Zahlen, SHA)
| Angabe in der Meldung | Prüfweg | Ergebnis |
|---|---|---|
| Z. 428 `vorschlag_aufloesung_cc.diff` 85 Zeilen | `wc -l` | richtig |
| Z. 423, 429 `_build_end` läuft nach `_build_ups_rest` | `git show 3ec3665:app_gui.py`, Z. 5124–5126: Reihenfolge subnet, raid, screen, ups, ups_rest, end | richtig |
| Z. 423 AttributeError-Annahme zurückgenommen | PROTOKOLL Z. 211 (12:25 UTC) | richtig |
| Z. 450 `FG-111_knopf.diff` sha `06e99377…b302`; +8/−3, +2/−2, +78/−6 | `sha256sum`, +/- gezählt | richtig |
| Z. 486 `FG-111_knopf_erweitert.diff` sha `215702fd…a176`, 270 Zeilen, ui +8/−3, main +6/−6, Test +156/−6 | dto. | richtig |
| Z. 487 `FG-111_spiel_vorschlag.diff` sha `80a75a37…e4ae`, 138 Zeilen, spiel +3/−3, Test +90/−0 | dto. | richtig |
| Z. 486 `git apply` sauber auf `5ee907c` (einzeln und zusammen) | eigener Worktree, `git apply --check` | richtig |
| Z. 511 `FG-112_kaestchen.diff` sha `aa55ff68…cbb72e2a5`, 117 Zeilen, `git apply --check` auf `7acfccb` | `sha256sum`, `wc -l`, eigener Worktree | richtig |
| Z. 519 `app_gui.py` +12/−9, Test +34/−5 | +/- gezählt | richtig |
| Z. 470 9 Stellen `main.py`, 5 `spiel.py` | Antrag Z. 26–36 | richtig (Antrag selbst schreibt „8 Reihen“ und listet 9) |
| Z. 478–483 Messrunde | Antrag Z. 81–98 | richtig |
| Z. 513 „2204 Messungen“ | `belege_fg112/inventar.jsonl`: **2436** Zeilen (gültiges JSON, keine Dubletten) | **falsch**, schon im Antrag Z. 24 (G4). Ergebnis (nur 1 Umbruch außerhalb Prüfungstrainer) bleibt. |
| Z. 521 K1–K4, 12:12:33Z / 12:29:50Z, Optionen 12 OK | Antrag Z. 62–83 | richtig; K1 nur mit erstem Test-Stand geprüft (G5) |

### Hoch

**H1 – Frage 9: Stoppgrenze widersprüchlich, Option (a) nennt die zu erteilende Grenze nicht vollständig (Z. 449–458, 489–497)**
Der Abschnitt „Antrag“ zeigt den ursprünglichen Diff (`FG-111_knopf.diff`, sha `06e99377…`) und sagt Z. 458: „**Stoppgrenze:** genau diese 3 Dateien. Keine geschützte Datei; `mobile/src/spiel.py` bleibt unverändert.“ Empfohlen wird aber (a): erweiterter Diff **plus** `spiel.py` (geschützt) und `test_spiel_stufen_0632.py`, also 5 Dateien. Option (a) nennt nur `ui.py`/`main.py`/Test mit Zahlen; `spiel.py` +3/−3, `test_spiel_stufen_0632.py` +90/−0 und die beiden SHA stehen nur in Z. 487. Dazu verlangt der Antrag selbst (Z. 144) „Genau `FG-111_knopf.diff` … Mehr ist eine Stoppgrenze“ und Z. 39 „als eigene FG“; die Meldung gibt das als „aus dem Antrag“ wieder, aber umformuliert. Chat kann nicht eindeutig ablesen, was mit „FG-111 erteilt“ freigegeben ist.
**Ersatz Z. 458:** „- **Stoppgrenze dieses ersten Diffs:** genau diese 3 Dateien, `spiel.py` unverändert. Die Erweiterung unten ändert die Stoppgrenze; maßgeblich ist die Option, die du wählst.“
**Ersatz Z. 497:** „- **(a)** FG-111 für genau zwei Diffs erteilen: `FG-111_knopf_erweitert.diff` (sha256 `215702fd…a176`: `ui.py` +8/−3, `main.py` +6/−6, `test_gradientbutton_0632.py` +156/−6) und `FG-111_spiel_vorschlag.diff` (sha256 `80a75a37…e4ae`: `mobile/src/spiel.py` +3/−3, geschützt, Muster FG-106; `test_spiel_stufen_0632.py` +90/−0). Stoppgrenze = diese 5 Dateien mit diesen Zeilen. Folge: alle 5 gefundenen Stellen behoben; Messrunde nach dem Bau wiederholen.“
**Ersatz Z. 498:** „- (b) FG-111 nur für `FG-111_knopf_erweitert.diff` (3 Dateien, ohne `spiel.py`). Folge: …“ (Rest wie bisher)
**Ersatz Z. 499:** „- (c) FG-111 nur für `FG-111_knopf.diff` (sha256 `06e99377…b302`, `main.py:966`). Folge: …“
**Ersatz Z. 490:** „- genau die in der gewählten Option genannten Diff-Dateien (der Antrag nennt in seinen Auflagen noch nur `FG-111_knopf.diff`; das ist durch die Erweiterung überholt), mehr ist eine Stoppgrenze“

### Mittel

**M1 – Hinweisblock und Dokumentenliste veraltet: „Platzhalter“, „entsteht“, „nicht erneut geprüft“ (Z. 839, 849, 895, 896)**
Z. 839: „Fassung 2 ist nicht erneut geprüft. Vor dem Versand werden drei Platzhalter eingesetzt: der Diff zu Frage 8, die Messrunde zu Frage 9 und der Antrag zu Frage 10.“ Alle drei sind eingesetzt; diese Gegenprüfung liegt vor. Für Chat liest sich das wie eine unfertige Meldung.
**Ersatz Z. 839 (zweiter Teil):** „Die erste Gegenprüfung hat Fassung 1 geprüft (`meldungen/gegenpruefung/Meldung_44_gp.md`), eine zweite Fassung 2 (`meldungen/gegenpruefung/Meldung_44_gp2.md`); deren Befunde sind eingearbeitet.“
**Ersatz Z. 849:** „- /mnt/project-files/bau_0.63.2/integration/n6_konflikt/ (LIESMICH.txt, vorschlag_aufloesung_cc.diff, vorschlag_gegen_n6_3ec3665.diff, vorschlag_gegen_integration_a82fd34.diff)“
**Ersatz Z. 895:** „- /mnt/project-files/bau_0.63.2/antraege/FG-111_Antrag_Knopf_waechst.md“
**Ersatz Z. 896:** „- /mnt/project-files/bau_0.63.2/antraege/FG-112_Antrag_Kaestchen_erste_Zeile.md“
**Ergänzen nach Z. 852:**
„- /mnt/project-files/bau_0.63.2/antraege/FG-111_knopf_erweitert.diff
- /mnt/project-files/bau_0.63.2/antraege/FG-111_spiel_vorschlag.diff
- /mnt/project-files/bau_0.63.2/antraege/FG-112_kaestchen.diff
- /mnt/project-files/bau_0.63.2/antraege/belege_fg112/
- /mnt/project-files/bau_0.63.2/meldungen/gegenpruefung/Meldung_44_gp2.md“

**M2 – N5-Stand veraltet: Der lokale Merge ist zurückgesetzt (Z. 16, 43, 91, 540, 607)**
`version-0632` steht lokal wieder auf `a82fd34` (belegt: `git reflog version-0632`: „reset: moving to a82fd34“ nach `e90b78e`; `wt_0632` = `a82fd34`; Remote = `a82fd34`). `e90b78e` gibt es nur noch im Reflog. Die Meldung sagt dagegen „lokal `e90b78e`“ und Z. 43 „`version-0632` hat seitdem FG-96 (und lokal N5)“.
**Ersatz Z. 16 (N5-Teil):** „**N5:** Der lokale Merge `e90b78e` ist zurückgesetzt, `version-0632` steht lokal und auf GitHub auf `a82fd34`; nie gepusht. Das war mein Fehler, N5 kommt nach S1c2 (Selbstkontrolle, Fehler 1).“
**Ersatz Z. 43 (Teil):** „`version-0632` hat seitdem FG-96, und S1c2 steht jetzt auf `7acfccb`“
**Ersatz Z. 91:** „- Der Merge `e90b78e` war nur lokal, ist nicht gepusht und inzwischen lokal zurückgesetzt (`version-0632` = `a82fd34`, belegt per Reflog). N5 kommt nach S1c2.“
**Ersatz Z. 540 Spalte 2 (Anfang):** „konfliktfrei, **nicht gepusht, lokal zurückgesetzt** (`version-0632` = `a82fd34`).“
**Ersatz Z. 607 Spalte 2:** „`98f63ff`; Probe-Merge `e90b78e` zurückgesetzt, nie gepusht“

**M3 – Frage 8: Option (a) nennt nicht das Tor, das den offenen Punkt klären kann (Z. 432, 435)**
Z. 432 und LIESMICH Z. 20–22: Ob die Knopfzeilen beim Vorladen in Teilen die Fix-3b-Anpassung rechtzeitig bekommen, ist „nur per Tor mit ohne_inter (DejaVu) und Teil breite belegbar“. Option (a) nennt `test_klick_hat_vorrang`, Vorlade-Tests und „Rechner-Breitentests“, aber nicht ausdrücklich den Lauf ohne Inter. Mit Inter passen die Knopfzeilen immer (Kommentar im Diff), der kritische Fall wäre dann nicht geprüft.
**Ersatz Z. 435 (zweiter Satz):** „Danach Auflösung im N6-Zweig (Zusammenführen ohne Force) und Tor N6 mit `test_klick_hat_vorrang`, den Vorlade-Tests und dem Teil „breite“ **sowohl mit Inter als auch ohne Inter (DejaVu)**; nur so ist der offene Punkt oben belegbar. Rot im Teil ohne Inter heißt anhalten und melden.“

**M4 – Frage 9: Bestand nach der Erweiterung schmaler als angegeben; „Blockiert“ widerspricht B.8 (Z. 487, 502, 611)**
1. Z. 487 „beide Diffs zusammen: 7 Bestandsdateien grün“. Laut Antrag Z. 140 sind 2 der 7 die geänderten Testdateien selbst (`test_gradientbutton_0632`, `test_spiel_stufen_0632`). `test_zugang` (17) und `test_schriftstufe_0632` (19), die beim ersten Diff liefen (Z. 462), sind mit der Erweiterung **nicht** erneut gelaufen.
   **Ersatz in Z. 487:** „beide Diffs zusammen: 5 Bestandsdateien grün (`test_anzeige_handy` 23, `test_handy_0632` 35, `test_handy_anzeige_0632` 16, `test_handy_sehr_gross_0632` 20, `test_spiel_abgabe` 2) plus die beiden geänderten Testdateien; `test_zugang` und `test_schriftstufe_0632` liefen nur mit dem ersten Diff (berichtet)“. In den Auflagen (Z. 491) ergänzen: „dabei `test_zugang` und `test_schriftstufe_0632` mit beiden Diffs“.
2. Z. 502 „Blockiert: N9-Merge nicht; FG-111 kommt als Nachtrag auf den N9-Zweig.“ B.8 Z. 611 sagt für N9: „Index-Test (E1-4) und gegebenenfalls FG-111 **vorher** auf dem Zweig“. Das ist ein Widerspruch.
   **Ersatz Z. 502:** „**Blockiert:** nichts. N9 kann vor FG-111 gemergt werden; FG-111 kommt dann als eigener Nachtrag auf den Integrationsstand.“ (oder umgekehrt Z. 611 anpassen; eine der beiden Stellen muss weichen)

**M5 – Frage 10: Nico hat F2 (b) auf einer teilweise falschen Angabe gewählt; das steht nicht offen da (Z. 515, Selbstkontrolle)**
Der Foto-Nachtrag sagte Nico bei F2: „Es sieht überall gleich aus, auch wie am Handy“ und „am Handy ist es schon so“ (`Nachtrag_Meldung_39_Fotos.md` Z. 104, 106). Laut FG-112-Antrag Z. 31–33 (belegt per `inspect`) stimmt das nur für Haken; Schalter am Handy stehen mittig. Z. 515 nennt den Sachverhalt, aber nicht, dass die eigene Angabe an Nico falsch war, und auch nicht die Folge für ihn.
**Ersatz Z. 515:** „**Handy (berichtet, laut Bauer belegt):** Haken stehen schon oben (`ui.check_row`, START). Schalter in den Einstellungen stehen mittig (Flet-Standard, `main.py:4167`). **Mein Foto-Nachtrag hat Nico gesagt, am Handy sei es schon so; das stimmt nur für Haken.** Der Antrag ändert das Handy nicht. Ein Satz dazu geht mit dem nächsten Nachtrag an Nico; will er auch die Schalter am Handy oben, ist das eine Zeile in `_switch` als eigener Antrag (ob der Schalter dort umbricht, ist nicht geprüft).“
**Ergänzen als Fehler 15 (nach Z. 114):** „15. **Foto-Nachtrag F2:** Ich habe Nico geschrieben, am Handy stehe das Kästchen schon oben. Das gilt nur für Haken, nicht für Schalter (FG-112-Antrag, Abschnitt 2). Korrektur geht mit dem nächsten Nachtrag an Nico (Frage 10).“

**M6 – Frage 10: Merge-Ort und Verhältnis zu S1c2/Frage 6a fehlen (Z. 504–527, 619)**
FG-112 hat die Basis `7acfccb` (S1c2) und ändert `test_ansichten_breite.py`, dieselbe Datei wie `7acfccb` und wie Option 6a (b). Die Hunks überschneiden sich heute nicht (`7acfccb`: Z. 1003; FG-112: Z. 577, 600, 812; selbst geprüft), aber bei 6a (b) entsteht ein neuer S1c2-Stand. Frage 10 hat keine „Blockiert“-Zeile, B.8 sagt nur „nach deiner Freigabe“.
**Ergänzen nach Z. 527:** „**Blockiert:** nichts. FG-112 wird auf dem S1c2-Zweig gebaut, **nach** der Umsetzung deiner Wahl in 6a (bei 6a (b) wird der Diff auf den neuen Stand gesetzt; ändert sich dabei mehr als die Zeilennummern, ist das eine Stoppgrenze). S1c2 kann ohne FG-112 gemergt werden; dann kommt FG-112 als eigener Schritt.“
**Ersatz Z. 619 Spalte 3:** „nach deiner Freigabe; FG-111 auf N9 (siehe Frage 9), FG-112 auf S1c2 nach 6a“

### Gering

**G1 – Uhrzeit (Z. 6):** „etwa 12:25 UTC“, aber Frage 9/10 enthalten Werte bis 12:32Z und Antrag FG-112 von 12:59 UTC. **Ersatz:** „Stand 14.10.2026, etwa 13:00 UTC.“ (tatsächliche Uhrzeit beim Versand)

**G2 – Kopfblock zu lang und S6a/S6b uneinheitlich (Z. 9–20, 15, 151):** REGELN Z. 162: „Kopfblock max 10 Zeilen“. Der Kopfblock hat 12 Zeilen (Z. 9–20). Z. 15 nennt „S6b-Merge“, Z. 151 „S6a/S6b-Merge“. **Ersatz Z. 9–15 (eine Zeile):** „1. **Blockiert:** N7 (Frage 3), S1c2 (6a), N8 (7), N6 (8), N14-Wortlaut (5; dazu End-Stand-Lauf, Planreihenfolge), S6a/S6b und damit die Planreihenfolge (1).“

**G3 – Kopfblock 5 (Z. 19):** „Anträge FG-109, FG-110, FG-111“, ohne FG-112. **Ersatz:** „Anträge FG-109, FG-110, FG-111, FG-112.“

**G4 – Frage 10, Messanzahl (Z. 513):** „2204 Messungen“; `inventar.jsonl` hat 2436 (Prüfungstrainer 1441 einzeilig + 611 mehrzeilig, Abschlussprojekt 240, Optionen 143 + 1). Der Fehler steht schon im Antrag (Z. 24). **Ersatz:** „**Bestand (laut Bauer belegt, 2436 Messungen in `inventar.jsonl`; der Antrag nennt 2204, nachgezählt 2436 …):**“

**G5 – Frage 10, Belegstufe und Lücken (Z. 505, 511, 521):** SHA, Zeilen und `git apply --check` sind in dieser Gegenprüfung selbst nachgeprüft, in der Meldung aber ohne Stufe. K1 wurde nur mit dem ersten Test-Stand geprüft (Antrag Z. 83). Schalterhöhe 42 → 43 px im zweizeiligen Fall fehlt. **Ersatz Z. 505:** „**Belegstufe:** Nicos Antwort belegt (Abschrift gelesen); sha256, Zeilen und `git apply --check` belegt (Gegenprüfung 2); Messungen, Tests, Kontrollfehler berichtet (laut Bauer belegt), Belege `antraege/belege_fg112/`.“ **Ergänzen in Z. 521:** „K1 nur mit dem ersten Test-Stand (der Nachtrag ändert den Pfad laut Bauer nicht). Im zweizeiligen Fall wird der Schalter 1 px höher (42 → 43 px).“ In den Auflagen (a) ergänzen: „K1 auf dem Endstand wiederholen“.

**G6 – Frage 10, Anlass widerspricht dem Bestand (Z. 507 gegen 513):** Z. 507 nennt „Haken-Listen im Abschlussprojekt“ als Beispiel für mittig stehende Kästchen; laut Z. 513 und Antrag (FitWidthMixin ohne Haken-Umbruch) brechen sie nie um. **Ersatz Z. 507 (zweiter Satz):** „Andere Haken und Schalter am PC stehen weiter mittig, wenn ihr Text umbricht; gemessen kommt das nur beim Optionen-Schalter „Automatisch abgleichen“ vor (siehe Bestand).“

**G7 – E1-4 neu belegt (Z. 581, 583, 611):** Die erste Gegenprüfung und deren Leser kennen „E1-4“ als LoadingHint-Einstufung. **Ersatz:** neue Nummer „E1-5“ in Z. 581 und Z. 611; Z. 583 dann: „E1-4 (Einstufung von `LoadingHintTest`) ist gestrichen und steht zur Bestätigung in Frage 2.“

**G8 – Frage 4, Liste „nicht fotografiert“ (Z. 271):** Laut FG-109-Antrag Z. 70–71 auch „Reise-Unterreiter“, und alles nur dunkel, nur 200 %, nur Inter. **Ersatz:** „**Nicht fotografiert:** Serverfarm, Reise-Unterreiter, Dialoge, Kalkulation, laufendes Projekt, aufgenommener Kredit; nur dunkel, 200 % und Inter.“

**G9 – Frage 8, Zeitform (Z. 426):** „Der Auflösungsvorschlag kommt als Diff nach …“, er liegt aber schon dort (Z. 428). **Ersatz:** „Der Auflösungsvorschlag liegt als Diff in `/mnt/project-files/bau_0.63.2/integration/n6_konflikt/`.“

**G10 – B.7, Zeitform (Z. 594, 595):** „Der Umbau kommt als Antrag FG-111 (bzw. FG-112) zu dir“. **Ersatz:** „Der Antrag FG-111 liegt vor (Frage 9).“ bzw. „Der Antrag FG-112 liegt vor (Frage 10).“

**G11 – Frage 9, Quelle mit Zählfehler (Z. 470):** Die Meldung zählt richtig 9 Stellen in `main.py`; der Antrag schreibt „8 Reihen“ und listet 9 (Antrag Z. 26). **Ergänzen:** „(der Antrag schreibt „8 Reihen“, listet aber 9)“.

**G12 – Anhang A, Vorprüfungssatz (Z. 663):** Der übernommene Satz des Bauers lässt offen, dass (i) nur für die 94 neuen Einträge gilt (G5 der ersten Gegenprüfung). **Ergänzen am Satzende:** „((i) für die 94 neuen Einträge, (ii)–(iv) für alle 127; siehe Frage 7.)“

---

## 3. Format und Widersprüche
- Zeile 1 „AN: Claude Chat“: richtig.
- Zeile 2 „ENTSCHEIDUNG NÖTIG: ja (Chat, 10 Fragen; …)“: richtig; die Überschriften Frage 1–10 sind vorhanden, Kopfblock 4 nennt „Fragen 1–10“.
- Selbsttragend: Frage 8 und 10 ja (mit M3, M6). Frage 9 nein, solange H1 offen ist.
- Optionen und Empfehlung: Frage 8 (a/b/c, Empfehlung a), Frage 9 (a/b/c, Empfehlung a), Frage 10 (a/b, Empfehlung a) vorhanden. „Blockiert“-Zeile fehlt bei Frage 10 (M6).
- Veraltete Stellen: Z. 839 („Platzhalter“, „nicht erneut geprüft“), Z. 849/895/896 („entsteht“), Z. 426/594/595 (Zukunftsform), Z. 16/43/91/540/607 (N5 lokal), Z. 6 (Uhrzeit), Z. 19 (FG-112 fehlt). Alte Zahlen aus Fassung 1 (Frage 8 alt, E1-4 alt, „keinem Lauf rot“) kommen sonst nicht mehr vor (gesucht).
- Keine Zeitprognosen gefunden.
