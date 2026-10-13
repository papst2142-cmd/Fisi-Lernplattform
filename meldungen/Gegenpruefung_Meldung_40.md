# Gegenprüfung Meldung 40 (Fragen aus den Testplänen N6–N11, N14–N16)

Prüfer: unabhängiger Gegenprüfer (Claude Code, Unteragent). Meldung nicht geändert, nichts committet, gepusht oder gelöscht.
Geprüft gegen: `Weisung_CC_Ablauf_Grossauftraege.md`, `Weisung_CC_Meldungszweig.md`, `Testplan_N6/N7/N8/N9/N10/N11/N14/N15/N16.md` (Abschnitt Fragen), `gp_n10.md`, `n10/ergebnis.md`, `Plan_Nachtrag_0.63.2.md` (FG-Tabelle, F20–F32), `Freigabe_Plan_Nachtrag_0.63.2.md`, `Weisung_CC_Nachtrag_Freigabe_Plan_Nachtrag.md` (F23), Meldung 38; GitHub per `gh run view` / `git ls-remote`.

## Urteil

**Lieferbar: nein in dieser Fassung; ja nach Einarbeitung von M1–M4.** Keine S-Befunde. Die Übernahme der 67 Fragen ist vollständig und inhaltlich treu, die Tatsachen stimmen.

## (1) Vollständigkeit und Treue der 67 Testplan-Fragen – belegt

Zählung je Testplan: N6 5, N7 8, N8 9, N9 8, N10 7, N11 9, N14 6, N15 8, N16 7 = **67**. Jede Frage ist genau einer Stelle der Meldung zugeordnet:
- B1–B11 decken 13 Fragen ab (B1 = N16-F1+F3, B6 = N15-F2+F4, die übrigen je eine).
- Die Tabelle „Weitere Fragen“ hat **36** Zeilen (nachgezählt).
- Die reinen E3-Fragen sind 8 (N6-F1, N7-F4, N7-F5, N9-F2, N9-F7, N15-F5, N16-F2, N11-F9). Dazu kommen 4 E3-Teile geteilter Fragen (N8-F4, N11-F3, N10-F2, N14-F1), zusammen **12** Zeilen.
- E1 aus den Testplänen: 10 (N6-F4, N7-F2, N8-F1, N8-F8, N9-F5, N10-F6, N10-F7, N14-F6, N15-F7, N16-F7). Dazu kommen E1-11 und E1-12, zusammen **12**.
- Summe: 13 + 36 + 8 + 10 = 67.

Stufen: Keine Frage wurde abgestuft. Drei Fragen sind sinnvoll heraufgestuft bzw. geteilt:
- N10-F7: Die Pin-Liste mit `actions/cache@v6` ist nach gp_n10 L1 nicht E1 und steht in B11. Das ist richtig nach „im Zweifel E2“.
- N11-F3: Der FG-53-Teil geht als E2 in B7, der Teil Release-Dateien als E3 an Nico.
- N14-F1: Die Frage ist E2 und geht zusätzlich als Hinweis an Nico (E3).

Empfehlungen: Keine ist verfälscht. Gekürzt wurde nur Unwesentliches (siehe L1).

## (2) Tatsachen – belegt (eigener Abruf)

- Lauf 38467641835 und Lauf 38469818481:
  - beide `headSha 50470a3b…`, Zweig `version-0632-n10`, `workflow_dispatch`
  - `attempt 1`, `success`
  - 10 Jobs `success`, Vorab und Release `skipped`
- `git ls-remote`: `version-0632-n10` = `20800bd…`. Der Probezweig existiert noch nicht.
- `git diff 50470a3 20800bd`: nur `test_workflow_0632.py`, 13 Zeilen mehr.
- `gh run list`: kein Lauf auf `20800bd`.
- Aus `n10/ergebnis.md` richtig übernommen: lokal 74 Tests OK, 2 übersprungen; kalt/warm; keine „Wiederholung wegen“-Zeile; Gradle 6 Anfragen; Cache 3,2 GB; 2 von 8 Prüfsummen.
- FG und F richtig wiedergegeben:
  - FG-53 nennt `package_dmg` nicht.
  - FG-60 enthält „zeitabhängige Bestandstests (B-M-02)“.
  - FG-62 betrifft `main.py`, das ungeschützt ist.
  - FG-63 betrifft nur die Ereignis-Enden.
  - FG-65 deckt „z.B.“ in geschützten Dateien (N8-F7).
  - F23 (a) ist Nicos Entscheidung (Weisung vom 13.10.).
  - F27 (a), F28 (a), F31 (b) und F32 (a) stimmen.

## (3) Format und Verständlichkeit

- Die Zeilen `AN:` und `ENTSCHEIDUNG NÖTIG:` sind vorhanden.
- Der Kopfblock hat 7 Zeilen (≤ 10). Die Teile Blockiert/läuft weiter, Entscheidungen und E1 sind vorhanden.
- Glossar und Belegzeile sind vorhanden.
- Die Verständlichkeit für Chat ist eingeschränkt (M4): Chat liest nur den Zweig `meldungen`, auf dem die Testpläne nicht liegen (eigener Abruf: dort liegen nur README, Meldung 38 und zwei Gegenprüfungen).

## (4) Vorschlag im Kopfblock: siehe M1

## (5) Öffentlich publizierbar

Suche nach `@`, `/home`, `/root`, `/tmp`, `/mnt`, `token`, `passw`, `secret`, `ghp_`: 0 Treffer außer `actions/cache@v6` (Z. 63 und 132) und dem Wort „Secrets“ (Z. 146, beschreibend). Unbedenklich.

## Befunde

| Nr | Schwere | Befund | Korrektursatz |
|---|---|---|---|
| M1 | M | Kopfblock Z. 4 ist als Aussage formuliert („Bis zur Antwort **baut** der jeweilige Bauer …“). Man kann ihn als vollendete Tatsache lesen. Die Zeile `ENTSCHEIDUNG NÖTIG` zählt ihn nicht mit. Die Ausnahmen sind zu weit gefasst, denn mehrere Tabellenzeilen fallen in E2-Bereiche, die nicht ausgeschlossen sind: N6-F3 (Feld in `PerfMonitor` liegt in den Zeilen von FG-40, nicht in denen von FG-46; „bitte ausdrücklich bestätigen“), N16-F5 (Prüfung wird ersetzt), N14-F2 (Hinweis wird im Verhalten unterdrückt, Texte-Regel Abschnitt 5) und Umfangsänderungen (N11-F4, N11-F5). | Z. 4 ersetzen durch: „4. **Frage (E2): Vorabbau nach Empfehlung?** Darf der jeweilige Bauer bis zu deiner Antwort nach der Empfehlung bauen, wo sie nichts lockert, keinen Nutzertext und kein sichtbares Verhalten festlegt, keine Prüfung ersetzt, den Umfang nicht ändert und keine geschützte Datei außerhalb einer bestehenden FG berührt? Ausgenommen sind ausdrücklich N6-F3, N14-F2, N16-F5, N11-F4 und N11-F5. Bis zu deinem OK baut niemand nach diesem Vorschlag; vor dem Merge gilt in jedem Fall deine Antwort.“ In Z. 2 „und 36 weitere Fragen“ ändern in „, 36 weitere Fragen und 1 Frage zum Vorabbau“. |
| M2 | M | B9 stuft das Anheben der Zeitgrenzen (Lizenzfenster < 1 s, Handy-Seiten < 1 s, Mac-Intel-Starttest 240 s in `build.py:356-365`) nur als E2 ein. Die Weisung (Abschnitt 1, E3) nennt aber ausdrücklich „Grenzwerte (zum Beispiel Startzeit)“ als Sache von Nico. Außerdem ist `build.py:356-365` weder von FG-60 (nur Tests) noch von FG-53 gedeckt. Eine Testschleife im Workflow braucht ebenfalls eine FG über FG-51 hinaus. | In B9 die drei Spiegelstriche zu Zeitgrenzen jeweils mit „Lockerung (E2) und Grenzwert (E3, Nico)“ kennzeichnen. Beim Mac-Starttest ergänzen: „`build.py:356-365` ist durch keine FG gedeckt (neue FG nötig, E2)“. Die Empfehlung ersetzen durch: „(a) für `test_leistung.py:488` (nicht gelockert). Die drei Zeitgrenzen sind Grenzwerte: Du entscheidest, ob du sie Nico vorlegst (E3), sonst (b) Verschieben an Nico. Für die Testschleife (Workflow-Änderung) beantragt der Bauer vorher eine FG.“ In der E3-Tabelle eine Zeile „N10-F2 Zeitgrenzen 1 s / 240 s anheben (Grenzwert)“ ergänzen. |
| M3 | M | B11 („Danach fehlt für den Merge nur noch R3 (B8) und das Tor“) und „Zur Kenntnis“ („R3 läuft auf einem Probezweig“) sind ungenau. (i) Laut Testplan N10 Z. 153 ist R3 ein Probe-Lauf mit **erwartet rotem** Android-Job („APK prüfen“) und zählt nicht als grüner Lauf. (ii) Laut Testplan N10 Z. 168 („Ändert sich der Zweig nach R2 noch, braucht es zusätzlich einen grünen Lauf auf dem neuen Endstand“) und Weisung Abschnitt 2 fehlt noch ein ganzer grüner Lauf auf `20800bd`. (iii) R3 ist noch nicht gestartet; der Probezweig existiert nicht (belegt per `git ls-remote`). | B11 letzter Satz: „Danach fehlen für den Merge noch R3 (B8; Probe-Lauf mit absichtlich rotem Android-Job, zählt nicht als grün), ein ganzer grüner Lauf auf dem End-Stand `20800bd` und das Merge-Tor.“ In „Zur Kenntnis“ den Klammersatz ersetzen durch: „(R3 ist noch nicht gestartet und wartet auf B8; er ist absichtlich teilweise rot. Der grüne Lauf auf `20800bd` und danach der Merge-Tor-Lauf stehen noch aus.)“ Glossar R3 ergänzen: „… erwartet: Android rot genau in ‚APK prüfen‘, alle anderen 9 Jobs grün“. |
| M4 | M | Die Meldung ist nicht ganz selbsttragend. Chat kann die Testpläne nicht lesen (sie liegen nicht auf `meldungen`). Kürzel, die nur in den Testplänen erklärt sind, bleiben offen: **AK1** in B10 (in N14: „Monotonie: mit N14 verschwindet nie mehr als vorher“), K-Nummern (K1/K13, K6, K8, K11, K12, K21, K22, K44, K47, K60), **A-N9-10**, **P1**, **E11**, **U1/U2/U7**. Dazu kommen Mehrdeutigkeiten: **K11** bedeutet in N7 die feste Zuordnung je Änderungsart, in N8 den Pixeltest; **M3** bedeutet im Glossar sowohl einen gp_n10-Befund (Cache) als auch einen N16-Ablauf. | Im Glossar ergänzen: „**K…, AK…, A-N…, P…, E…:** Kontrollfehler, Abnahmekriterien, Abläufe und Fälle des jeweiligen Testplans; gleiche Nummern in verschiedenen Testplänen meinen Verschiedenes (z. B. K11 in N7 = feste Zuordnung je Änderungsart, in N8 = Pixeltest der Banner-Ecke). **AK1 (N14):** Mit N14 verschwinden durch Löschungen nie mehr Einträge als vorher (Teilmenge), es geht also nichts verloren. **A-N9-10:** Messung, ob die Schriftstufen-Reihe bei 2,0/1120 passt. **U1/U2/U7:** weitere Uhr-Zustände im Testplan N14.“ In „Zur Kenntnis“ den Cache-Befund als „gp_n10-M3“ bezeichnen und im Glossar den Eintrag M1–M5 auf „N16-M1 … M5“ umstellen. |
| L1 | L | Kleine Kürzungen gegenüber dem Testplan. B4 „neigt zu 160 % / 200 %“: Der Testplan nennt die Klammerfassung zuerst und hat keine Vorliebe. N14-F2: Die Optionen (a)/(c) fehlen. N11-F8: Es fehlt „Text der Vorab-Seite unverändert“. | B4: „der Prüfer schlägt ‚Größer (160 %)‘ / ‚Am größten (200 %)‘ oder nur ‚160 %‘ / ‚200 %‘ vor“. N14-F2: „Optionen: (a) so lassen, (b) …, (c) neuer Wortlaut“. N11-F8: „…; Text der Vorab-Seite unverändert“. |
| L2 | L | Kopfblock Z. 1 führt den „N9-Merge (B4, B5)“ als blockiert. B5 blockiert laut eigener Empfehlung aber nur, wenn die Messung „passt nicht“ ergibt. | Z. 1: „N9-Merge (B4; B5 nur, wenn A-N9-10 ‚passt nicht‘ ergibt)“. |
| L3 | L | „Zur Kenntnis“: „seither kam nur eine Testdatei dazu“ stimmt nicht. Es wurde keine Datei hinzugefügt, sondern ein vorhandener Test erweitert. | „seither wurde nur `test_workflow_0632.py` um einen Test erweitert (13 Zeilen)“. |
| L4 | L | In der Belegzeile fehlen der Plan-Nachtrag und die Freigaben, obwohl F20, F23, F27, F28, F31, F32 und FG-40 bis FG-87 zitiert werden. Die genannten Testpläne und `gp_n10.md` sind für Chat auf `meldungen` nicht abrufbar. | Ergänzen: „`plan_0.63.2/nachtrag/Plan_Nachtrag_0.63.2.md` (Abschnitt 6 FG, Abschnitt 9 F), `plan_0.63.2/freigabe/Freigabe_Plan_Nachtrag_0.63.2.md`; Testpläne und Prüfer-Proben liegen nur lokal (nicht auf `meldungen`).“ Wahlweise `gp_n10.md` als `meldungen/Gegenpruefung_N10.md` mit veröffentlichen (Weisung Meldungszweig Nr. 3 erlaubt zugehörige Gegenprüfungen; vorher denselben Suchlauf machen). |
| L5 | L | E1-7 nennt die curl-Prüfung „strenger“. gp_n10 Abschnitt 3 sagt „gleich/strenger“. | „gelten als gleich streng oder strenger“. |

Nicht geprüft: die Inhalte der Prüfer-Proben (`proben_pruefer/`, z. B. „3 von 5 rot“). Sie sind nur aus Testplan N16 übernommen, und die Übernahme stimmt (Z. 24, 31).
