AN: Claude Chat (Nico reicht nur die Hinweiszeile weiter)
ENTSCHEIDUNG NÖTIG: ja, von Claude Chat (11 blockierende Punkte, 38 weitere Fragen und 1 Frage zum Vorabbau, alle E2; die E3-Fragen gehen über Meldung 39 an Nico)

# Meldung 40: Fragen aus den Testplänen N6–N11, N14–N16 (dazu zwei Fragen zum Warntext-Dialog)

## Kopfblock
1. **Blockiert bis zur Antwort:** N16 (B1) · N7 (B2) · N8 und der Trennregel-Teil von N9 (B3) · N9-Merge (B4; B5 nur, wenn A-N9-10 „passt nicht“ ergibt) · N15 Teil N-b (B6) · N11 Teil Universal-Mac (B7) · N10-Merge (B8, B11) · N10 Teil B-M-02 Tests (B9) · N14 (B10, dazu Tabelle N14-F2 bis F5; N14 wartet ohnehin auf S6b).
2. **Läuft weiter:** N9 (Bau und Messung A-N9-10), N15 Teile N-h und N-a, N11 ohne Universal-Mac, Merge-Tor, Vorrat (Tests nach Testplan, Fotos für Meldung 39). N6 und N8 warten ohnehin auf S5c, Fix 3b und S1c2 (E1-1, E1-3).
3. **Entscheidungen (E2):** B1–B11 einzeln unten, Empfehlung jeweils genannt; 38 weitere Fragen in der Tabelle (davon D-F1/D-F2 zum Warntext-Dialog); Vorabbau-Frage in Punkt 4. Kurzantwort genügt, z. B. „OK alle außer B3, N8-F2“.
4. **Frage (E2): Vorabbau nach Empfehlung?** Darf der jeweilige Bauer bis zu deiner Antwort nach der Empfehlung bauen, wo sie nichts lockert, keinen Nutzertext und kein sichtbares Verhalten festlegt, keine Prüfung ersetzt, den Umfang nicht ändert und keine geschützte Datei außerhalb einer bestehenden FG berührt? Ausgenommen sind ausdrücklich N6-F3, N14-F2, N16-F5, N11-F4 und N11-F5. Bis zu deinem OK baut niemand nach diesem Vorschlag; vor dem Merge gilt in jedem Fall deine Antwort.
5. **Für Nico (E3):** 12 Punkte, nur zur Kenntnis; sie gehen mit Meldung 39 an Nico.
6. **Selbst entschieden (E1):** 13 Einträge, siehe Tabelle.
7. **Zur Kenntnis:** N10 fertig (End-Stand `20800bd`), 2 grüne Läufe auf `50470a3`, Lauf 38474444381 auf `20800bd` gestartet (Ergebnis folgt), Gegenprüfung: mergebar mit Auflagen A1–A3. **Wichtig:** `test_rundgang_hilfe.py` bricht im Lauf still mit Rückgabe 0 ab (Bestand), wird untersucht.

## Blockierende Fragen (E2)

**B1 · N16-F1 (mit N16-F3): Welche Löschregel für N16?**
F32 (a) wörtlich umgesetzt bricht B-G-09 aus S6c: Die Regel löscht beim Speichern sofort alle Feldzeilen, `delete_project` schreibt danach keine leeren Fassungen, ein 0.63.1-Gerät behält den privaten Text; 3 von 5 `LoeschenTest`-Tests werden rot (belegt, Prüfer-Prototyp, N16-K9). Dazu entfernt (a) Texte von Projekten, die unter 0.63.1 gelöscht wurden (N16-M2), und erzeugt schon im Normal-Mischbetrieb ein endloses Hin und Her mit einem Commit je Abgleich (N16-M1), womit T-b nicht still ist (beides belegt).
Optionen: **(a-korr)** F32 (a) ohne leere Fassungen und `delete_project` liest vorher die Felder; Folge: Änderung an S6c-Code, N16-M1 bleibt laut, `test_b_g_09_projekttext_weg` müsste ohne Freigabe geändert werden (N16-F3). **(ii′)** nur nicht leere Zeilen löschen, die später als `_geloescht` liegen; Folge: alle 5 S6c-Tests grün, N16-M1 still, N16-N1/N2 behoben, Lücke N16-F-c bleibt (belegt, Prototyp). **(iii)** ganz anders.
**Empfehlung: (ii′)**, und N16-F3 (a): `test_b_g_09_projekttext_weg` bleibt unverändert. Der Rest-Fall N16-M3/M4 geht als N16-F2 an Nico (E3).

**B2 · N7-F1: Freigabe für die Suche in `fisi_core.py`?**
Die Suchfunktionen (`search_content`, `notebook_search`, `_entry_search_text`) liegen im geschützten `fisi_core.py`, das FG-46 nicht abdeckt. Optionen: (a) Vorbereitung nur in `app_gui.py`, mit Gleichheitstest gegen die `fisi_core`-Funktionen (K1/K13); keine neue FG. (b) neue FG für die drei Funktionen.
**Empfehlung: (a)**; reicht das nicht, kommt ein FG-Antrag mit Messung.

**B3 · N8-F3: Wo liegt die gemeinsame Trennregel (PC, Handy, N9)?**
`fisi_core.py` ist geschützt. Ein neues Modul braucht einen Eintrag in `mobile/vorbereiten.py` `SHARED_FILES` und eine Paketprüfung; die Handy-Liste `ui.list_row` liegt in `ui.py` (N9). Optionen: (a) neues kleines ungeschütztes Modul (z. B. `fisi_trennung.py`) mit `SHARED_FILES`-Eintrag und Test, dass die APK es enthält (`pruefung/apk_pruefen.py`); N8 baut Regel, PC und `main.py`, N9 nutzt sie für `ui.Card` und `list_row`. (b) Regel in `fisi_core.py` mit neuer FG.
**Empfehlung: (a).** Hinweis: `pruefung/apk_pruefen.py` steht unter FG-51 (N10); ob der APK-Test eine Erweiterung braucht, ist nicht geprüft.

**B4 · N9-F1: Namen der neuen Schriftstufen (Nutzertext)?**
Der Bauer nennt sie „Extra groß“ und „Riesig“. Vorschlag des Prüfers: kurz und ohne Wertung, z. B. „Größer (160 %)“ / „Am größten (200 %)“ oder nur „160 %“ / „200 %“; PC = Handy.
**Empfehlung:** Wortlaut gibst du vor; der Prüfer schlägt „Größer (160 %)“ / „Am größten (200 %)“ oder nur „160 %“ / „200 %“ vor.

**B5 · N9-F3: Schriftstufen-Reihe `fisi_game_gui.ChoiceRow` (geschützt)?**
Die PC-Auswahlreihe ist `ChoiceRow`, nicht in FG-44/FG-49. Passt sie mit 5 Einträgen bei 2,0/1120 nicht, braucht es eine FG oder einen Ersatz in `app_gui.py`. Optionen: (a) erst messen (A-N9-10); passt sie (seitlicher Bildlauf laut `FONT_HINT` erlaubt), nichts ändern. (b) sonst FG für den Umbruch in `ChoiceRow`. (c) ungeschützte Reihe in `app_gui.py`.
**Empfehlung: (a)**; blockiert den N9-Merge nur, wenn die Messung „passt nicht“ ergibt; dann kommt (b) oder (c) als Vorschlag mit Diff.

**B6 · N15-F2 und N15-F4: Freigaben in `spiel.py` für N-b?**
`spiel.py` kann `main._redraw` nicht importieren (zirkulär). F2: kleine Hilfsfunktion in `spiel.py`, wörtlich wie `main._redraw`, im Test austauschbar; dafür FG-63 um „eine Hilfsfunktion“ ergänzen (kein Eingriff in `ui.py`, das gehört N9). F4: Findet K6 Aufrufer in `spiel.py`, die vor `push`/`open` schreiben, deckt weder FG-62 noch FG-63 eine Änderung dort.
**Empfehlung:** F2 ja (FG-63 um eine Hilfsfunktion erweitern). F4: Bauer legt die Liste vor, dann FG-63-Erweiterung „Nummer an `push` geben“; nicht ohne Freigabe bauen. N-h und N-a laufen weiter.

**B7 · N11-F3 (E2-Teil): Universal-Mac und dmg-Namen**
Installierte Programme suchen beim Update `-macOS-arm64.dmg` bzw. `-macOS-intel.dmg` (`fisi_update.py:131-132`, belegt). Ein Universal-Bau muss beide Namen weiter veröffentlichen, sonst finden Intel-Installationen kein Update. Dafür muss `build.py package_dmg` geändert werden; das nennt FG-53 nicht. Alternative: neuer Name plus Änderung an `fisi_update.py`.
**Empfehlung:** beide Namen behalten und FG-53 um `package_dmg` erweitern (E2). Der Teil Release-Dateien/Download-Seite geht an Nico (E3).

**B8 · N10-F1: Probe-Lauf R3 fahren?**
Der Plan verlangt für „leere Datei vorlegen → erkannt, neu geladen“ (CI-a) und „Variable entfernen → APK-Prüfung rot“ (B-H-09) ausdrücklich einen Probe-Lauf; beides ist bisher nur lokal belegt. Optionen: (a) R3: ein ganzer Lauf auf dem Probezweig `version-0632-n10-probe` (nie gemergt) deckt beide ab; die Hash-Mutation bleibt lokal. (b) lokale Belege genügen; Folge: Abweichung vom Plan.
**Empfehlung: (a).**

**B9 · N10-F2 (B-M-02 Teil (b), Auflage A1): zeitabhängige Bestandstests**
B-M-02 hat zwei Teile: (a) Netz-Wiederholung ist gebaut; (b) zeitabhängige Tests und Mac-Starttest sind offen und zählen nicht als erledigt (belegt, `gp_n10.md` 5; der N10-Bericht ist korrigiert: FG-60 deckt die Tests, die frühere Begründung „Auftrag erlaubt nur drei Dateien“ war falsch). Betroffen laut Bericht (Stellen belegt im Code, Flackern berichtet aus der Gesamtliste):
- `test_rechtliches.py:468` Lizenzfenster < 1 s und `:562` Handy-Seiten < 1 s: jede Änderung (Grenze anheben oder Zeit von Funktion trennen) schwächt die 1-s-Zusage: Lockerung (E2) und Grenzwert (E3, Nico); beim Handy-Test ist Flackern nicht geprüft.
- `test_leistung.py:488` Fensterziehen: auf Zustand warten statt fester Pausen, Prüfinhalt bleibt; laut Bericht gleich streng, die Fehlerstelle muss erst aus den Flacker-Läufen belegt werden.
- `build.py:356-365` Mac-Intel-Starttest (240 s): Anheben ist Lockerung (E2) und Grenzwert (E3, Nico); `build.py:356-365` ist durch keine FG gedeckt (neue FG nötig, E2).
Dazu je geänderter Test 20 Läufe ohne Flackern auf GitHub, über dem N10-Budget. Optionen: (a) eigener kleiner Auftrag nach N10, Nachweis per Schleife in **einem** Durchgang statt 20 ganzen Läufen (braucht Workflow-Änderung oder eigenen Dispatch, also eine FG über FG-51 hinaus). (b) Teil (b) verschieben; das ist E3 (Nico).
**Empfehlung:** (a) für `test_leistung.py:488` (nicht gelockert). Die drei Zeitgrenzen sind Grenzwerte: Du entscheidest, ob du sie Nico vorlegst (E3), sonst (b) Verschieben an Nico. Für die Testschleife (Workflow-Änderung) beantragt der Bauer vorher eine FG. Hält den N10-Merge nicht auf.

**B10 · N14-F1: Weg b lässt auch Löschungen dieses Geräts Einträge übersehen**
Der Plan (3.41) nennt nur Löschungen anderer Geräte. Im Prüfer-Prototyp kommen auch nach Löschungen dieses Geräts Einträge zurück (U5: eigene, abgeglichene Einträge nach „Alle Lerndaten löschen“; U6: fremde Einträge) (belegt, Matrix 5.2). Optionen: (a) als bekannte Grenze annehmen (Bericht und Testliste); kein Verlust, AK1 gilt. (b) Weg b einschränken; eine Variante ohne neuen Verlustweg ist nicht bekannt.
**Empfehlung: (a)**, und Nico erfährt, dass die Beschreibung zu F20 um diesen Fall erweitert ist (Hinweis, E3).

**B11 · N10-F4 und Auflage A3: Zustimmung zum N10-Merge**
`release.yml`: Ein Netzfehler bei `git ls-remote` führt nach 3 Versuchen zum Abbruch (Job rot, kein Tag, kein Release) statt zu „Tag fehlt“ und Bau. Die Gegenprüfung hat jede geänderte Zeile gelesen und hält das für sicher (belegt, `gp_n10.md` 1). A3: Die S5b-Prüfung der Action-Versionen erlaubt neu `actions/cache@v6` (genau 1 Verwendung); das ist eine Erweiterung der erlaubten Menge als Folge von FG-51/F28, nicht „gleich streng“ (belegt).
**Empfehlung:** beides annehmen. Danach fehlen für den Merge noch R3 (B8; Probe-Lauf mit absichtlich rotem Android-Job, zählt nicht als grün), ein ganzer grüner Lauf auf dem End-Stand `20800bd` und das Merge-Tor.

## Weitere Fragen mit Empfehlung (E2)
| Nr | Stufe | Frage | Empfehlung |
|---|---|---|---|
| N6-F2 | E2 | Ist der Optionen-Bereich im Zwischenschritt zugeklappt oder offen mit Platzhalter sichtbar? | Offen lassen, Inhalt im nächsten Zeitgeber nachreichen; Foto der Zwischenstufe für Nico; falls störend, „ganz bauen“ |
| N6-F3 | E2 | Braucht die Messung „bis Abbau fertig“ ein neues Feld in `PerfMonitor` (außerhalb FG-40)? | Ja, als Teil von FG-46 (gleicher Bereich `app_gui.py`); bitte ausdrücklich bestätigen |
| N6-F5 | E2 | Zählt `FinalProjectView` (Abschlussprojekt) zu „Testprojekt“? | Nur die vier genannten Gruppen bauen; `abschluss` messen, über 150 ms Windows als Befund melden |
| N7-F3 | E2 | Ist eine feste Zuordnung je Änderungsart (K11) Pflicht, oder reicht Bündelung plus Zwischenspeicher? | K11 Pflicht mit Tabelle im Bericht; K12 (Differenztest) sichert ab |
| N7-F6 | E2 | Sicherung: gleiche Zeilenreihenfolge oder nur gleiche Menge (K21)? | Gleiche Reihenfolge (strenger); nur wenn technisch unmöglich, Menge plus Begründung an dich |
| N7-F7 | E2 (Wortlaut) | Hinweis „Bitte warten“ bei Sicherung/Ersetzen: vorhandenen Text oder neuer? | Neuer kurzer Text, Wortlaut von dir; sagt nur „läuft“, keine Zusage |
| N7-F8 | E2 | Bleibt die Handy-Suche (`main.py:4802`) langsam (Plan nennt nur PC)? | Nicht ändern; messen und als Befund nennen |
| N8-F2 | E2 | Welche Trennstellen gelten bei der Silbenregel B-D-06 als richtig? | Feste Erwartungsliste (mindestens 10 Wörter) von dir bestätigen; Regel darf weniger Stellen nutzen, nie andere |
| N8-F4 | E2 (Wortlaut) | Namen der Symbolknöpfe und Startknöpfe am PC | Kurzname + „starten“ („WiSo starten“); Namen wie am Handy (PC = Handy); Aussehen an Nico |
| N8-F5 | E2 | B-D-08 Banner-Ecke (`GradientPanel`): was heißt „gleich behandelt“? | Pixeltest K11; ändern nur, wenn der Test die Lücke zeigt, sonst Foto „kein Befund mehr“ |
| N8-F6 | E2 | B-D-14: Hinweis bei „Start trotz laufender Prüfung“? | Kein Hinweis (F23 (a): keine neue Funktion), nur die laufende Prüfung zeigen |
| N8-F7 | E2 | „z.B.“ → „z. B.“ in den Rechenweg-Texten (`fisi_core.py`), Handy-Breitengrenze 26/28 | Erst messen; passt jede Zeile, nur ersetzen; sonst nicht bauen, Zeilen mit Vorher/Nachher an dich |
| N8-F9 | E2 (Lockerung) | Darf K60 hell/dunkel auf eine Farbe je Schrift verkürzen? | Nein; alle Fälle in der CI-Datei, ein Prozess je Faktor; Laufzeit messen und melden |
| N9-F4 | E2 (FG) | Nicht erreichbare Spielansichten bei 2,0 außerhalb FG-44 (Büro, Kunde, Zuhause, Übersicht)? | Messen, Liste mit Vorschlags-Diff an dich; nicht ohne FG bauen |
| N9-F6 | E2 | Ausnahmen „Textlink im Fließtext“ unter 48 dp (K22)? | Keine Ausnahme ohne dich; Liste vorlegen |
| N9-F8 | E2 (Lockerung) | CI-Fassung des PC-Rundgangs auf eine Farbe kürzen, voller Satz im Container? | Nur mit deinem OK; Vorschlag: beide Schriften, ein Modus je Schrift abwechselnd, voller Satz im Container mit Log |
| N10-F3 | E2 | Vorab-Testversionen bauen mit Cache (gp_n10 L1-b); gilt F28 „ohne Cache“ auch für sie? | Ja, auch Vorab ohne Cache (Bedingung um `inputs.vorab == ''` ergänzen, FG-51-Stelle, Test und Kontrollfehler) |
| N10-F5 | E2 | Zählt ein Lauf mit Wiederholung **innerhalb** eines Netz-Schritts als grün? | Ja, wenn die Zeile „Wiederholung wegen …“ im Bericht steht (F27 (a)) |
| N11-F1 | E2 | Lock-Dateien lokal erzeugen oder in der CI (Plan: CI)? | Lokal, Nachweis in R1/R3; Erzeugungsbefehl im Bericht |
| N11-F2 | E2 | Fassungen wie Referenzlauf 38443624150 oder neueste? | Wie Referenzlauf, keine stille Aktualisierung |
| N11-F4 | E2 | certifi in `mobile/pyproject.toml` fest eintragen (macht den N10-Cache einmal kalt)? | Ja, Fassung aus `requirements.txt` (2026.7.22) |
| N11-F5 | E2 | Container-Bild per Digest festlegen? | Ja |
| N11-F6 | E2 | pip-audit „nicht prüfbar“ im Release blockierend? | Ja |
| N11-F7 | E2 | Ausnahmeliste für bekannte, nicht ausnutzbare Funde? | Keine Liste; Funde einzeln an dich |
| N11-F8 | E2 | pip-audit bei Vorab-Testversionen blockierend? | Nein, warnen wie im normalen Lauf; Text der Vorab-Seite unverändert |
| N14-F2 | E2 | `clock_fix_text` ist in unsicheren Fällen schon heute falsch; ändern? Optionen: (a) so lassen, (b) keinen Hinweis im unsicheren Zustand, (c) neuer Wortlaut | (b) im unsicheren Zustand keinen Hinweis zeigen (weniger Zusage, kein neuer Text, nur `_marker_now`, FG-58) |
| N14-F3 | E2 | `grenze_3_ohne_startkennung_neu_gestartet` ändert sich unter Weg b nicht; was tun? | Prüfung unverändert, nur Docstring; neuer Gegentest P1 |
| N14-F4 | E2 | `clock_deviation` ändern oder getrennte Lesefunktion? | `clock_deviation` AST-gleich, neue Lesefunktion; `fisi_sync._correct_own_entries` bleibt gleich (K6) |
| N14-F5 | E2 | Falls N14-A-G8 ein Etikett mit weniger Einträgen als S6b ergibt? | Ablauf vor dem Bau als Test schreiben, Ergebnis sofort melden; du entscheidest |
| N15-F1 | E2 | Ist `open` (on_show vor `push`) ein Aufrufer, der die Nummer braucht? | Bauer prüft per K6; wenn ja, `open` gibt die Nummer an `push`; B-G-23 bleibt unverändert (K8) |
| N15-F3 | E2 | Kopfkommentar `spiel.py:10` widerspricht dem Muster | Einen Satz ergänzen, mit FG-63 zusammen freigeben; sonst stehen lassen und im Bericht nennen |
| N15-F6 | E2 | Reicht Nicos JA zur Probe (nur hell/Normal) für N-h? | Fotos nachliefern; du prüfst; erneut an Nico nur bei Auffälligkeit (K44, K47) |
| N15-F8 | E2 (Lockerung) | Laufzeit der Tests in CI-rest (nahe 1800 s) | Datei unter 30 s; sonst Stichprobe in den Container-Lauf, nur mit deinem OK |
| N16-F4 | E2 (Wortlaut-Stelle) | Wo steht der F31-Satz? | Im selben „Hinweis:“-Absatz als zweiter Satz |
| N16-F5 | E2 (Prüfung geändert) | `assertNotIn("Abgleich"/"GitHub")` in `test_ohne_abgleich` ersetzen? | Ja; Volltext bleibt, dazu „keine Weitergabe-Zusage“ und „GitHub genau einmal“ |
| D-F1 | E2 | Standardknopf im Warntext-Dialog „Alles ersetzen“ (Vorbau `774b868`, Meldung 38 Frage 2): bisher war beim Tk-Dialog „Ja“ Standard (Eingabetaste), gebaut ist „Nein“. | „Nein“ (sicherer); Rückweg ist ein Wort (`default="yes"`) |
| D-F2 | E2 | Am Handy gilt `scrollable=True` für **alle** `confirm`-Rückfragen (32 Aufrufer); Flutter rollt nur, wenn der Text nicht passt; kurze Rückfragen sind nicht per Foto geprüft. | Annehmen; Fotos in Meldung 39 |
| N16-F6 | E2 | „lässt sich in der App nicht rückgängig machen“ stimmt mit „Alles ersetzen“ und älterer Sicherung nicht (E11, vorbestehend) | Nur melden, keine Änderung in N16 |

## Für Nico (E3), nur zur Kenntnis
Diese Punkte gehen über Meldung 39 an Nico. Du musst hier nichts entscheiden.
| Nr | Worum es geht | Empfehlung des Prüfers |
|---|---|---|
| N6-F1 | Zielwerte: Schrift/Farbe „bis bedienbar“ Windows ≤ 1,5 s; Klick-Wartezeit ≤ 150 ms | Ziel mit Bericht, kein Testkriterium |
| N7-F4 | Schwelle „langsam“ für Weg 2 (1,7 s / 2,3 s) | Weg 2 bauen, Schwelle nur fürs Protokoll |
| N7-F5 | Zielwerte Windows: Suche ≤ 0,3 s, Dashboard ≤ 0,2 s, Notizblock ≤ 0,15 s, Sicherung/Ersetzen ≤ 1 s | Ziel mit Bericht |
| N8-F4 | Aussehen von Tooltip und Fokus-Beschriftung | Fotos an Nico |
| N9-F2 | B-E-06: Beschriftung nur beim gewählten Eintrag oder kleinere Symbole | Fotos beider Varianten; „nur gewählt“ ab Sehr groß |
| N9-F7 | Sichtbar größere Elemente (z. B. GradientButton 46 → 48) | Fotoliste „sichtbar größer“ getrennt |
| N15-F5 | Gesperrt und frei farblich nah (lila, dunkel), auch B-E-03 | Foto des engsten Falls |
| N16-F2 | Rest-Hin-und-Her N16-M3/M4 mit 0.63.1-Gerät; F3-Bedingung „T-b grün“ betroffen | (a) annehmen, vorher N16-M3/M4/M5 mit dem echten Bau messen |
| N11-F3 | Release-Dateien/Download-Seite bei Universal-Mac | beide dmg-Namen behalten (E2-Teil: B7) |
| N11-F9 | Nach Ende von `macos-15-intel` kein Intel-Starttest mehr | heute nur melden |
| N10-F2 | Verschieben von B-M-02 Teil Tests, falls du nicht bauen lässt (B9) | erst nach deiner Entscheidung |
| N10-F2 | Zeitgrenzen 1 s / 240 s anheben (Grenzwert, B9) | erst nach deiner Entscheidung, ob du sie vorlegst |
| N14-F1 | Hinweis: Beschreibung zu F20 erweitert (B10) | nur informieren |

## Selbst entschieden (E1)
| Nr | Entscheidung | Begründung | Beleg |
|---|---|---|---|
| E1-1 | N6 zweigt erst nach S5c **und** S1c2 im Integrationsstand ab. | Reihenfolge innerhalb der Abhängigkeiten (Weisung Abschnitt 1 Nr. 5); S5c ist auf `e0f9c7e` nicht gemergt. | `Testplan_N6.md` 6 Nr. 4 |
| E1-2 | Getrennte Testdateien: `test_leistung_0632.py` (N6), `test_leistung_suche_0632.py` (N7). | Dateinamen (Nr. 6); Laufzeit je Datei bleibt sichtbar. | `Testplan_N7.md` 6 Nr. 2 |
| E1-3 | N8 zweigt erst nach Fix 3b und S1c2 ab. | Reihenfolge (Nr. 5); Fix 3b behebt die DejaVu-Rotstellen in denselben Ansichten. | `Testplan_N8.md` 10 Nr. 1 |
| E1-4 | `fisi_pruefung.py:107` `'z.B.'` bleibt; im Bericht als „nicht sichtbar“. | Abkürzungserkennung (FG-87), kein Anzeigetext (Nr. 6). | `Testplan_N8.md` 10 Nr. 8 |
| E1-5 | N9 baut weiter auf `e0f9c7e` und zieht vor dem Merge ohne Force auf den aktuellen Integrationsstand nach; alle Abläufe dort wiederholt, beide Stände im Bericht. | Reihenfolge (Nr. 5). | `Testplan_N9.md` 8 Nr. 5 |
| E1-6 | Probezweig für R3 heißt `version-0632-n10-probe` und bleibt danach bestehen. | Name (Nr. 6); kein Löschen ohne Auftrag. | `Testplan_N10.md` 10 N10-F6 |
| E1-7 | Zwei der drei angepassten S5b-Prüfungen (404-Zeile, curl) gelten als gleich streng oder strenger. Die dritte (Action-Versionen mit `actions/cache@v6`) ist **nicht** E1 und steht in B11. | Nr. 4 nur für gleich strenge oder strengere Tests; Gegenprüfung L1. | `n10/ergebnis.md` (K1–K4 rot), `gp_n10.md` 3 |
| E1-8 | Testwerkzeug: Befehl `reset_game` in `pruefung/abgleich_geraet.py`; Matrix-Tests in neuer Datei `test_s1_0632.py`. | Werkzeug und Dateiname (Nr. 6). | `Testplan_N14.md` 11 N14-F6 |
| E1-9 | N-b „mehr als ~10 Stellen“ wird nach Ereignis-Enden gezählt; beide Zahlen im Bericht. | Zählweise ist Fundstellen-Frage (Nr. 6); geändert wird an den Ereignis-Enden. | `Testplan_N15.md` 7 Nr. 7 |
| E1-10 | Neue Datei `test_n16_0632.py`; Werkzeug-Befehle `projekt_feld`, `projekt_zeilen`. | Dateinamen und Werkzeug (Nr. 6). | `Testplan_N16.md` 11 N16-F7 |
| E1-11 | Neuer Test `BytecodeTest.test_bytecode_reste_jede_regel_einzeln` (Befund L3): jede der drei Regeln in `bytecode_reste` muss allein greifen. | Strengerer Test (Nr. 4); Kontrollfehler G5 und zwei weitere werden rot, die alten Tests waren gegen G5 grün. | `n10/ergebnis.md` „Nacharbeit (L3)“, Commit `20800bd` |
| E1-12 | Ursache des vorzeitigen Endes von `test_rundgang_hilfe.py` klären und den Test gleich streng reparieren. | Test-Anpassung gleich streng (Nr. 4); eine Lockerung geht als E2 an dich. | `dialog_warntext/ergebnis.md` (Tests, offene Punkte 4) |
| E1-13 | Diese Meldung bekommt die Nummer **40**. | Nummer 39 ist für Nicos Fotos reserviert (Meldung 38, E1-1); Nummern sind E1 (Nr. 6). | Meldung 38 |

## Zur Kenntnis
- **Wichtig, `test_rundgang_hilfe.py` endet vorzeitig:** Die Datei bricht im Lauf nach 21–23 „ok“ mit Rückgabe 0 und ohne Schlusszeile ab, auch auf `d54397f` (Bestand, belegt durch den Bauer des Dialog-Vorbaus). Die letzten Tests laufen also nicht, obwohl der Lauf grün aussieht. Vermutete Ursache: `arm_emergency_exit` in `app_gui.py` (Notausgang `os._exit(0)`) wird im Testprozess beim Schließen eines PC-Fensters scharf gestellt. Wird untersucht (E1-12); eine Lockerung käme zu dir.
- **Warntext-Dialog (Vorbau zu Meldung 38 Frage 2):** `774b868` auf dem lokalen Zweig `version-0632-dialog`, nicht gepusht, kein Merge, kein GitHub-Lauf (berichtet). PC: eigener rollbarer Dialog; Handy: `confirm` rollbar. Neue Tests 8 OK, rot gegen `d54397f`, 6 Kontrollfehler rot (berichtet). Windows und macOS nicht geprüft. Fragen D-F1/D-F2 in der Tabelle, Aussehen an Nico (Meldung 39).
- **N10 fertig:** Bau `50470a3`, danach Nacharbeit L3 (nur `test_workflow_0632.py`); End-Stand `version-0632-n10` = **`20800bd`**, nicht gemergt (berichtet, `n10/ergebnis.md`). Lokal 74 Tests OK, 2 übersprungen (berichtet).
- **Zwei grüne Läufe:** 38467641835 (kalt) und 38469818481 (warm), beide auf **`50470a3`**, nicht auf dem End-Stand; seither wurde nur `test_workflow_0632.py` um einen Test erweitert (13 Zeilen), der Push löste keinen Lauf aus (berichtet). Alle 10 Jobs grün im ersten Versuch, kein Einzel-Job-Neustart, keine echte „Wiederholung wegen …“-Zeile (belegt, Gegenprüfung mit eigenem Abruf). Der ganze Lauf auf dem End-Stand `20800bd` ist gestartet: 38474444381 (berichtet, Ergebnis folgt; zählt erst nach grünem Abschluss). (R3 ist noch nicht gestartet und wartet auf B8; er ist absichtlich teilweise rot. Danach steht der Merge-Tor-Lauf noch aus.)
- **Gegenprüfung `gp_n10.md`:** mergebar mit Auflagen, keine S-Befunde (belegt).
  - **A1** (B-M-02 nur teilweise gebaut, Begründung korrigiert): im N10-Bericht korrigiert (berichtet) und hier in B9 gemeldet.
  - **A2** Restrisiko CI-a: Gradle fragt weiter 6-mal beim Server nach (bedingte Anfrage); ein Netzfehler dort wird nicht wiederholt (vermutet, Quelltext gelesen). Kommt in Bericht und Testliste.
  - **A3** Erweiterung der Action-Liste: in B11.
- **`release.yml` zeilenweise gelesen** (Auflage 4.3 erfüllt, belegt): Netzfehler → Abbruch statt „Tag fehlt“; kein neuer Weg zu doppelten Releases; Secrets und Auslöser unverändert; YAML gültig, `bash -n` ohne Fehler.
- **Nicht geprüft:** ein echter Release-Lauf ohne Cache (es gab keinen), die tatsächliche Cache-Belegung (API gesperrt), die übrigen 6 Prüfsummen (2 von 8 selbst geladen).
- **Cache (gp_n10-M3, vermutet):** 3,2 GB je Zweig; ohne Cache auf `main` startet jeder neue Zweig kalt; ab etwa 3 Zweigen verdrängt GitHub alte Einträge. Folge nur Zeit, kein Merge-Hindernis.

## Glossar (nur neue Kürzel)
- **B1 … B11:** Nummern der blockierenden Fragen in dieser Meldung.
- **N6-F1 usw.:** Frage 1 aus dem Testplan N6; **D-F1, D-F2:** Fragen zum Warntext-Dialog (Vorbau).
- **R3:** dritter GitHub-Lauf für N10, auf einem Probezweig mit absichtlich leerer Datei und ohne `PYTHONDONTWRITEBYTECODE`, nie gemergt; erwartet: Android rot genau in „APK prüfen“, alle anderen 9 Jobs grün.
- **A1–A3:** Auflagen der Gegenprüfung `gp_n10.md`; **L1-b**, **L3**, **gp_n10-M3**: Befunde dort; **G5**: deren Kontrollfehler „nur `.cpython-` erkannt“.
- **(ii′), (a-korr):** Varianten der N16-Löschregel aus dem Testplan N16.
- **N16-M1 … N16-M5:** Mischbetriebs-Abläufe im Testplan N16 (0.63.1-Gerät mit 0.63.2-Gerät); **N16-N1/N2:** die N-f-Grundfälle; **N16-F-c:** Fall „unbekanntes Feld, früher geschrieben, offline“; **N16-K9:** Kontrollfehler dort.
- **U5, U6:** Uhr-Zustände im Testplan N14 (+2 h bzw. −2 h, weiter abweichend); **U1/U2/U7:** weitere Uhr-Zustände im Testplan N14.
- **K…, AK…, A-N…, P…, E…:** Kontrollfehler, Abnahmekriterien, Abläufe und Fälle des jeweiligen Testplans; gleiche Nummern in verschiedenen Testplänen meinen Verschiedenes (z. B. K11 in N7 = feste Zuordnung je Änderungsart, in N8 = Pixeltest der Banner-Ecke).
- **AK1 (N14):** Mit N14 verschwinden durch Löschungen nie mehr Einträge als vorher (Teilmenge), es geht also nichts verloren.
- **A-N9-10:** Messung, ob die Schriftstufen-Reihe bei 2,0/1120 passt.

Alle Belege dieser Meldung:
- `bau_0.63.2/testplaene/Testplan_N6.md`, `Testplan_N7.md`, `Testplan_N8.md`, `Testplan_N9.md`, `Testplan_N10.md`, `Testplan_N11.md`, `Testplan_N14.md`, `Testplan_N15.md`, `Testplan_N16.md` (jeweils Abschnitt Fragen)
- Prüfer-Proben `bau_0.63.2/testplaene/proben_pruefer/` (nur Proben, keine Bauvorlage)
- `bau_0.63.2/gegenpruefung/gp_n10.md` mit `gp_n10_belege/`
- `bau_0.63.2/n10/ergebnis.md` (aktualisierte Fassung mit Nacharbeit L3), End-Stand `20800bd`
- Läufe 38467641835 und 38469818481 (`50470a3`); Lauf 38474444381 (`20800bd`, gestartet, Ergebnis folgt)
- `plan_0.63.2/nachtrag/Plan_Nachtrag_0.63.2.md` (Abschnitt 6 FG, Abschnitt 9 F), `plan_0.63.2/freigabe/Freigabe_Plan_Nachtrag_0.63.2.md`; Testpläne, Prüfer-Proben und `gp_n10.md` liegen nur lokal (nicht auf `meldungen`)
- Gegenprüfung dieser Meldung: `bau_0.63.2/gegenpruefung/gp_meldung_40.md`
- Meldung 38 (`bau_0.63.2/meldungen/Meldung_38_Strang_Karte.md`)
- `bau_0.63.2/dialog_warntext/ergebnis.md` (Vorbau `774b868`, lokal)
