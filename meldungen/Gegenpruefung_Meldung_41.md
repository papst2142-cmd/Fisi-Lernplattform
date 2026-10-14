# Gegenprüfung Meldung 41 (Fragen aus dem Bau, Fassung 1)

Prüfer: unabhängiger Gegenprüfer (Claude Code, Unteragent, nicht Autor). Meldung nicht geändert, am Repo nichts geändert, nichts committet, nichts gepusht.
Maßstab: `REGELN_BAU_0.63.2.md` (inkl. Zusatz 14.10.), `Weisung_CC_Antwort_Meldung_38_und_40.md` (Abschnitte 0–9, Stand 03:35 UTC), `Weisung_CC_Ablauf_Grossauftraege.md`, `Weisung_CC_Meldungszweig.md`, Vorbilder Meldung 38/40 mit `gp_meldung_38.md` / `gp_meldung_40.md`.
Selbst geprüft: alle 8 genannten Läufe per `gh run view` (SHA, Zweig, Versuch, Jobs); Job-Log „Tests Linux (rest)“ des N16-Laufs per GitHub-MCP; N14-Logs unter `n14/logs/` vollständig gelesen (Test-Lauf, Basis-Lauf, Mutationsübersicht, Bestand, AST); Code `3b6a886` (`fisi_hilfe.py:430-432`, `fisi_optionen.py:105`); `git log` für `69e62ae`, `aed082e`, `7a32651`, Arbeitsbaum N14; Quellen `integration/ci_rest_3b/ergebnis.md`, `gegenpruefung/gp_s1c2_b4b.md`, `audit_testzahl/{ergebnis,tabelle,FG-97_Antrag}.md`, `n10/abschluss/b9_diagnose/diagnose.md`, `n9/ergebnis.md`, `n16/ergebnis.md`, `s6b/m38/ergebnis.md`, `s5c/ergebnis_a13_fix.md`, `n15/aufrufer_push_open.md`, `n8/FG-97_Antrag_apk_pruefen.md`, `testplaene/Testplan_N14.md`, Plan-Nachtrag (FG-50, FG-60, FG-70), `OFFEN_FUER_BERICHT.md` ab Zeile 66.

## Urteil

**Lieferbar nach Einarbeitung** von S-1 und M-1 bis M-9. Die L-Funde sind empfohlen, aber nicht Bedingung.

Zahlen, SHAs und Laufnummern stimmen ohne Ausnahme mit den Quellen überein. Die Stufen sind fast überall richtig oder vorsichtiger als nötig. Frage 1 beschreibt den Verlust richtig und ohne Beschönigung, und die Empfehlung ist als Vorschlag gekennzeichnet. Es fehlen dort aber ein Pflichtablauf aus dem Testplan (f2g) und die Einordnung gegenüber Nicos Entscheidung F20. Frage 6 beruht auf einer falschen Freigabe-Annahme und widerspricht einer stehenden Chat-Entscheidung.

## 1. Tatsachen (eigener Abruf)

| Aussage | Ergebnis | Stufe |
|---|---|---|
| Lauf 38475825951 (`9df7bd8`, fix3b) | Versuch 1, 10 Jobs success, Vorab/Release skipped | belegt |
| Lauf 38495894431 (`5c8039c`, n10) | Versuch 1, 10 Jobs success | belegt |
| Lauf 38496133527 (`30f5d8c`, n10-probe) | nur android failure, 9 success, Vorab/Release skipped | belegt |
| Lauf 38499632310 (`a567b33`, n16) | spiel + rest failure. Rest-Log: „Rote Testdateien: test_abgleich_0632.py test_ansichten_breite.py test_rechner_seite_breite.py“ | belegt (Job 115643255308) |
| Lauf 38472532424 (`5e29dd5`, messung-0632-a13) | nur Job windows, success | belegt |
| Lauf 38495818809 (`4d77439`, fg96) | nur breite failure, sonst success | belegt |
| Lauf 38502657436 (`8cded82`, n15) | nur rest failure | belegt |
| Lauf 38461199297 (`e0f9c7e`) | nur rest failure | belegt |
| Frage 1: U6 `{'A': {}, 'B': {}}` FAIL; Basis `{a-vorher 2, b-vorher 2}`; U3 ok | wie zitiert. Zeitstempel U6: t1 06:30:15 UTC, t2 06:54:16+02:00 = 04:54 UTC, also t2 rund 1 h 36 min **vor** t1; in U3 liegt t2 24 min nach t1. Das passt zu „Marke 2 h zu früh“. | belegt |
| Frage 2: Hinweis U5 7200,1/7200,3, U8 7200,2/7200,5, U7 3600,2, U1 7200,6 | wie zitiert | belegt |
| Fragen 3, 4, 5, 6, 7, 8, 9, 11, 12, 16, 17, 18 | Zahlen deckungsgleich mit den Quellen (36 Fälle, 10/12, 24 Fälle; +70/+126/+144/+314/+74/+8, 537 Aufgaben; 71 Dateien, 1387+68+384 = 1839, +23 ibus, 16,4 s, K1–K8; 223 Läufe/1512 Jobs/104 Windows-Jobs; 28 Tests, 17 Wörter; 1661,2/1703,4/1622,1/1870,0/86,2 ms, Abstand 39,1; S1–S6, M3–M9 = 7) | berichtet, gegen Quelle geprüft |
| Anhang A | Alle 86 Zeilen maschinell gegen `audit_testzahl/tabelle.md` verglichen (Datei, Teil, gesammelt, ausgeführt, GitHub): gleich, nur Kürzungen im Wortlaut | belegt |
| Frage 10 Hilfetext/Suchwörter auf `3b6a886` | wörtlich wie zitiert | belegt |
| Öffentlich publizierbar | Suche nach `@`, `/home`, `/root`, `/tmp`, `/mnt`, token, passw, secret, `ghp_`, noreply: 0 Treffer. Keine Zeitprognosen. | belegt |

## 2. Funde

### S – schwer

**S-1 · Frage 6 (Fensterziehen): falsche Freigabe-Grundlage, und die Frage widerspricht einer stehenden Entscheidung**
- *Stelle:* Frage 6, Optionen und Empfehlung; Titel „vorläufig FG-98“; E1-5.
- *Beleg:*
  - Weisung B9: „`test_leistung.py:488` (Fensterziehen): **(a)**. Auf Zustand warten statt fester Pausen, Prüfinhalt bleibt. Der Nachweis per Schleife braucht eine **FG vor dem Bau** (Antrag mit Diff).“ Die Diagnose war nur für die drei anderen Tests verlangt.
  - Plan-Nachtrag FG-60 (Tabelle Z. 605): „zeitabhängige Bestandstests (B-M-02) … S6b, N10–N14“. Die Änderung an der Testdatei ist damit **schon freigegeben**. Eine neue FG braucht nur der Schleifen-Nachweis (`build.yml`/`ci_tests.sh`, so auch `b9_diagnose/diagnose.md`).
  - Option (a) der Meldung verlangt „FG-98 für die Testdatei“ und macht den Schleifen-Nachweis optional („nur mit weiterer FG“). Das ist das Gegenteil der Weisung.
  - Option (b) „B-M-02 Teil (b) im Bericht als ‚geprüft … nichts geändert‘ führen“ widerspricht der Weisung: „B-M-02 Teil (b) bleibt **offen**, zählt nicht als erledigt“.
  - Empfehlung (b) heißt: Eine beschlossene Arbeit fällt weg (Nico: „nichts gekürzt“).
- *Korrekturvorschlag:*
  - Frage 6 neu fassen: „Du hast (a) entschieden. Der Testteil ist durch FG-60 gedeckt; vor dem Bau fehlt nur der FG-Antrag für den Schleifen-Nachweis (Diff liegt **nicht** vor).“
  - Zwei Optionen: (a) wie entschieden, Schleifen-Antrag folgt mit Diff; (b) nur der Testumbau unter FG-60, ohne Schleifen-Nachweis, Nachweis in einem normalen Lauf. Folge von (b): weniger als verlangt, deshalb E2.
  - Keine Option „B-M-02 (b) erledigt“. Die Nummer FG-98 hier streichen (siehe M-9).

### M – mittel

**M-1 · Frage 1: Pflichtablauf f2g fehlt, Zufallsabläufe nicht genannt**
- *Stelle:* Frage 1, „Ablauf“, Selbstkontrolle.
- *Beleg:*
  - `Testplan_N14.md` N14-A-G8 verlangt die „Abläufe f2b **und f2g** mit A unter U3/U6 und Neustart“.
  - `n14_test_s1_lauf1.log` enthält nur `test_g8_f2b_u3…` und `test_g8_f2b_u6…`. Keine N14-Log-Datei nennt f2g (grep: 0 Treffer).
  - AK1 wird nach Testplan auch über die 26 Zufallsabläufe nachgewiesen. Dazu steht kein Log in `n14/logs/`.
- *Korrekturvorschlag:*
  - In Frage 1 einen Satz ergänzen: „f2g unter U3/U6 und die 26 Zufallsabläufe (AK1): **nicht geprüft**. Fällt f2g ebenfalls ab, ändert das die Gewichtung der Optionen.“
  - Besser noch vor der Lieferung laufen lassen und das Ergebnis eintragen.

**M-2 · Frage 1: Nicos Entscheidung F20 nicht genannt, Stufe E2/E3 unklar**
- *Stelle:* Frage 1, Kopf und Optionen; Kopfblock Punkt 5.
- *Beleg:*
  - Weg b ist Nicos Entscheidung F20 („F20: Nein. S-1 wird mit Weg (b) gebaut“, `Weisung_CC_Nachtrag_Freigabe_Plan_Nachtrag.md`).
  - Option (b) ändert die Umsetzung von F20 teilweise. Option (a) nimmt einen neuen Verlustfall gegenüber S6b hin, auf dem Chats Annahme B10 („kein Verlust“) nicht mehr steht.
  - Testplan N14-F1 nennt dafür selbst „E2 mit Hinweis an Nico (E3, weil F20 auf der Plan-Beschreibung beruht)“.
- *Korrekturvorschlag:*
  - Ein Satz im Problem: „Weg b ist Nicos Entscheidung F20. Ob er bei einem Verlustfall gegenüber S6b selbst entscheidet (E3), legst du fest.“
  - Option ergänzen: „(e) N14 nicht in 0.63.2 (Verschieben; entscheidet Nico, E3)“. Damit ist die Liste vollständig. Die Option darf als nicht empfohlen gekennzeichnet sein.

**M-3 · Frage 1/Kopfblock: Abhängigkeit von S6b verschwiegen; N14 hat keinen Commit**
- *Stelle:* Kopfblock Punkt 1 („N14 wird bis zu deiner Antwort nicht gemergt“); E1-6 (N16).
- *Beleg:*
  - Der N14-Arbeitsbaum steht auf `69e62ae`. Das ist laut `git log` „N14 Basis: S6b (origin cad90c0, B-G-08 + R-d)“ auf S6c `e64b640`. Die Änderungen sind **nicht committet** (`git status`: `fisi_core.py`, `pruefung/abgleich_geraet.py`, `test_restrisiko_3_18.py` geändert, `test_s1_0632.py` neu). Es gibt keinen Remote-Zweig.
  - N16 (`a567b33`) liegt ebenfalls auf S6b.
  - Weisung Frage 3: „B-G-08 bleibt … außerhalb des Integrationsstands, bis ich FG-81 und FG-92 gemeinsam abgenommen habe“. Beide Stränge können also auch nach Chats Antwort erst nach dieser Abnahme gemergt werden.
  - Zusätzlich hat der N14-Stand die 4 roten T-c-Tests aus Frage 9 (`bestand_n14_test_abgleich_0632.py.log`: FAILED (failures=4), genau die vier T-c). Die Meldung sagt das nicht.
- *Korrekturvorschlag:*
  - Kopfblock Punkt 1: „N14 (nicht committet, auf S6b `cad90c0` + S6c) wird bis zu deiner Antwort nicht gemergt; Merge ohnehin erst nach Abnahme FG-81/FG-92.“
  - E1-6 um denselben Satz ergänzen.
  - In Frage 9 ergänzen: „ebenso auf dem N14-Stand“.

**M-4 · Frage 3 (Fix 3b): Option (a) übergeht die Foto-Regel**
- *Stelle:* Frage 3, „Einordnung“ und Option (a).
- *Beleg:*
  - Die Meldung beruft sich auf Chats Antwort zu N5 („andere Schriften umbrechen“). Dieselbe Antwort sagt aber: „Der Teil, der das Aussehen ändert, kommt erst **nach Nicos Foto-Abnahme** (F30).“
  - F11 (c) verlangt Design-Fotos vor dem Merge.
  - Option (a) („Merge jetzt, lehnt Nico ab, Rücknahme“) ist damit eine Ausnahme von beiden Regeln. Die Meldung nennt das nicht.
  - Kleiner Fehler: Die Änderung betrifft auch „Normal“ 1360 (Testprojekt), nicht nur „Sehr groß“.
- *Korrekturvorschlag:*
  - Bei (a) ergänzen: „Ausnahme von F11 (c) und deiner Auflage zu N5 (Aussehen erst nach Nicos Foto), begründet damit, dass sich mit Inter nichts ändert.“
  - „Layoutänderung bei Sehr groß und bei Normal 1360 (nur ohne Inter)“.
  - Bei (a) „N5 kann folgen“ ergänzen um „nach S1c2 (Frage 4) und FG-96“.

**M-5 · Frage 4: „Stand vor S1c2“ ist falsch**
- *Stelle:* Frage 4, „Alle 5 sind auf dem Stand vor S1c2 gleich (Bestand, nicht durch die zwei neuen Commits)“.
- *Beleg:*
  - Der Vergleichsstand der Gegenprüfung ist `aed082e` („S1c2 Z3 Nacharbeit L2“). Er liegt **innerhalb** von S1c2, `git log aed082e..7a32651` = nur die zwei B-4b-Commits.
  - Die Gegenprüfung sagt ausdrücklich: „5 davon sind S1c2-Z3-Zustände/Deckel“. Es sind also Fälle von S1c2 selbst, die nicht im Integrationsstand liegen. Bestand im Sinne von 0.63.1 sind sie nicht.
  - Beim Fall „Fortschritt mit Daten“ lag der Deckel auf `aed082e` bei 55; erst `5092328` hob ihn auf 70.
- *Korrekturvorschlag:* „Alle 5 sind schon vor den zwei B-4b-Commits gleich (`aed082e`); sie stammen aus S1c2 Z3, nicht aus 0.63.1.“

**M-6 · Frage 13 (Tippflächen): FG-50 deckt die Spielstellen schon**
- *Stelle:* Frage 13, „Für die 64 Stellen im Spiel (geschützte Datei) … braucht es zusätzlich Freigaben über FG-50 hinaus“.
- *Beleg:*
  - FG-50 (Plan-Nachtrag Z. 595): „Tippflächen in `main.py` und **`spiel.py`**“, Punkt B-J-04.
  - `n9/ergebnis.md` sagt „über FG-50 hinaus“ nur für die **Spielansichten bei 200 %**, nicht für die Tippflächen.
  - Neu zu genehmigen ist nur der Bestandstest `test_anzeige_handy.py` PillGroupTest.
- *Korrekturvorschlag:*
  - „Die Spielstellen deckt FG-50. Eine neue FG braucht nur der Bestandstest PillGroup; die Spielansichten bei 200 % brauchen eine eigene Freigabe (B-J-06).“
  - Fragen 12 und 13 können eine gemeinsame FG bekommen; der N9-Bauer schlägt das selbst vor.

**M-7 · E1-4: Stufe gegen den Bauer herabgesetzt**
- *Stelle:* E1-4 (Kontrollfehler D8c → D8c2).
- *Beleg:* `s6b/m38/ergebnis.md` Z. 70 führt das ausdrücklich als „**E2** Kontrollfehler D8c aus dem Testplan ist wirkungslos …; ersetzt durch D8c2“. Der Kontrollfehler stammt aus dem Testplan des Prüfers (Prüfer vor Bauer). Regel: „Im Zweifel E2.“
- *Korrekturvorschlag:* Den D8c-Teil als E2-Zeile führen (kurz: „ersetzt, strenger, bestätigst du?“) oder in E1-4 begründen, warum die Stufe gegen den Bauer herabgesetzt wird. Takefocus/fehler.log/1,25 bleiben E1 (der Bauer hat sie selbst so eingestuft).

**M-8 · Frage 16 (G1): Stufe vermutlich E3**
- *Stelle:* Frage 16, Option (a) „Für 0.63.2 gilt A13; G1 als Befund“.
- *Beleg:*
  - Option (a) gibt eine bestehende Grenze für 0.63.2 auf.
  - Weisung B9: „das Anheben einer Grenze … entscheidet Nico (E3)“.
  - Weisung zu Meldung 24: „A13-Grenze wird nicht verschoben; wird sie nicht erreicht: … Nico entscheidet“.
  - Woher G1 kommt (wer die milde Lesart festgelegt hat), sagt die Meldung nicht.
- *Korrekturvorschlag:* Die Herkunft von G1 in einem Satz nennen. Hat Nico G1 festgelegt, ist das ganze Thema E3 (Chat legt es mit Empfehlung vor). Sonst bleibt es E2 mit dem Hinweis „Grenze entfällt“.

**M-9 · FG-Nummern: Vergabe widersprüchlich (Prüfpunkt 4)**
- *Stelle:* Frage 5 (FG-97), Frage 6 (FG-98), E1-5 (N8 → FG-99).
- *Beleg:*
  - Weisung Abschnitt 8: „Nächste freie FG: FG-97 (nur falls Antrag, siehe Abschnitt 1 **und B3**)“. Chat hat FG-97 also für **zwei bedingte** Anträge genannt.
  - Die Bedingung der Zählprüfung ist **nicht** erfüllt (die Meldung sagt das selbst: „als Option“).
  - Die Bedingung bei B3 **ist** erfüllt: `n8/FG-97_Antrag_apk_pruefen.md` belegt, dass `apk_pruefen.py:31` das neue Modul nicht erfasst.
  - E1-5 gibt die Nummer aber der Option und schiebt den Pflicht-Antrag auf FG-99. Nummern vergibt Chat; das ist keine E1-Entscheidung.
  - Frage 6 braucht nach S-1 für den Testteil keine eigene Nummer.
- *Korrekturvorschlag (eindeutige Vergabe, vorläufig, Chat bestätigt):*

| Nummer | Antrag | Status |
|---|---|---|
| **FG-97** | N8: `pruefung/apk_pruefen.py` erfasst `fisi_trennung` (B3, Bedingung erfüllt) | Antrag liegt vor (`n8/FG-97_Antrag_apk_pruefen.md`), kommt mit der N8-Meldung |
| **FG-98** | Zählprüfung in `pruefung/ci_tests.sh` (Frage 5, nur bei (a)) | Option. Im Antrags-Diff dann Kommentar „FG-97“ → „FG-98“ ändern; die Rückgabe 97 darf bleiben (oder auf 98, Chat entscheidet), sonst stimmt die Nummer im Text nicht |
| – | Fensterziehen, Testteil | keine neue Nummer, FG-60 |
| **FG-99** | Fensterziehen, Schleifen-Nachweis (`build.yml`/`ci_tests.sh`) | erst wenn der Antrag mit Diff vorliegt |
| ohne Nummer | Fragen 8 (`log_record`), 12/13 (Tests Schriftstufen/PillGroup), 14 (Dialog in CI), 19 (Kriterium) | „neue FG, Nummer vergibst du“ |

  E1-5 streichen und die Vergabe als kurze E2-Zeile führen („Nummernvorschlag, bitte bestätigen“).

### L – leicht

- **L-1 · Kopfblock 1:** „Gegen 0.63.1 kein Verlust“ ohne Stufe; im Text steht „berichtet“. Im Kopfblock „(berichtet)“ ergänzen.
- **L-2 · Frage 1, Problem:** „liegt … vor einer Löschung, die ein anderes Gerät … vorher gemacht hat“ klingt allgemein. Die Bedingung fehlt: Die fremde Löschung liegt höchstens etwa die gemessene Abweichung (2 h) vor der eigenen. Ein Halbsatz genügt.
- **L-3 · Frage 1, Vergleichslauf:** Die Kopfzeile von `basis_69e62ae_test_s1.log` nennt denselben Arbeitsbaum wie der N14-Lauf („Code der Geraete: /home/claude/wt_0632_n14“). Dass er den Stand `69e62ae` ohne die N14-Änderungen zeigt, ist nur über den Dateinamen und die Ergebnisse (22 rot, Hinweis −7200) erschließbar. „S6b-Stand“ genauer als „S6b `cad90c0` (vor Streichung Satz 5)“ bezeichnen. Die Sofortmeldung des Bauers als Datei unter `n14/` ablegen; heute ist die Ursache nur aus einem Auftragstext „berichtet“.
- **L-4 · Frage 3, Option (a):** „N5, N6, N8 können folgen“: N5 braucht zusätzlich S1c2 (Frage 4) und FG-96 (Weisung Frage 5).
- **L-5 · Frage 9:** „ebenso im N16-Lauf (Teil rest rot, belegt)“. Laut Job-Log sind dort zusätzlich die zwei bekannten Breitendateien rot. „rot: `test_abgleich_0632.py` (T-c) und die zwei bekannten Breitendateien“ schreiben.
- **L-6 · Frage 18:** „(belegt im Code, nicht am Gerät gesehen)“ steht wie eine eigene Prüfung da. Laut Selbstkontrolle ist nur der Hinweistext selbst gesehen; das Schließen ist **berichtet** (N15). So kennzeichnen.
- **L-7 · Kopfblock 5 / OFFEN Z. 75:** N9-F2 (Navigationsleiste, Foto für Nico) fehlt in der Liste „Für Nico (E3)“.
- **L-8 · OFFEN Z. 80:** Der N15-Befund „IPv4-Umbruch Sehr groß auf `e0f9c7e`“ fehlt in „Zur Kenntnis 4“.
- **L-9 · Frage 14/15:** Laut `s6b/m38/ergebnis.md` Z. 70 ist auch der Handy-Dialog nur über einen Chromium-Behelf geprüft; die Abweichung zum echten Handy ist „nicht geprüft“. In Frage 14 oder in der Testliste nennen.
- **L-10 · Kürzel:** „S1–S6“ (Aufrufer im Spiel) kollidiert mit den Strangnamen S1a…S6c. „N14-F2“ (Frage 2, Problem) steht nicht im Glossar. Vorschlag: Aufrufer „SP1–SP6“ / „HA3–HA9“; im Problem von Frage 2 „deine Antwort zum Uhr-Hinweis (Meldung 40)“.
- **L-11 · Länge (Prüfpunkt 6)**, wo Chat nichts entscheiden muss:
  - Frage 5, Absatz „Rundgang-Fix“, doppelt mit E1-1: einen davon streichen.
  - „Zur Kenntnis N10“ steht mitten in Frage 6: nach „Zur Kenntnis“ verschieben.
  - Frage 15: Die Weisung (Frage 2, Auflage 4: „wo die CI es kann, sonst nicht geprüft“) entscheidet das schon, und für ein Paket gilt ohnehin „Frage E2“. Frage 15 als Zeile in „Zur Kenntnis“ führen, damit sind es 18 Fragen.
  - Frage 3: Die drei Bullets „Art des Fixes“ lassen sich auf zwei kürzen.
  - Anhang A bleibt, weil Chat die Tabelle ausdrücklich verlangt hat (Weisung 1.2).
- **L-12 · Frage 1 als Sofortmeldung:** Chat hat „Ergebnis sofort melden“ verlangt (N14-F5). Sie steht vorn, ist aber an 18 weitere Fragen gebunden. Erwägen, Frage 1 (mit M-1 bis M-3) als eigene kurze Meldung vorab zu schicken, mit eigener Hinweiszeile an Nico (Weisung Abschnitt 0/8).

## 3. Prüfpunkte im Einzelnen

1. **Zahlen/SHAs/Läufe/Stufen:**
   - Alles stimmt (Abschnitt 1).
   - Die Stufen sind korrekt oder vorsichtiger; Ausnahmen L-3 und L-6.
   - „Alle Jobs grün“ heißt jeweils: 10 Jobs success, Vorab/Release übersprungen.
2. **Frage 1 streng:**
   - Der Verlust ist richtig beschrieben. Belegt sind das Ergebnis `{}` gegen `{2,2}`, die Lage von t2 vor t1 und U3 wie S6b.
   - Ehrlich gesagt wird, dass AK1 gegenüber S6b nicht gilt und Chats Grundlage zu B10 damit wegfällt.
   - Die Empfehlung ist als „Vorschlag“ und „vermutet“ gekennzeichnet. Option (a) wird offen „Lockerung“ genannt. Der Verbleib in der Sicherungsdatei ist als vermutet und das zweite Ersetzen als nicht geprüft gekennzeichnet.
   - Keine Beschönigung gefunden.
   - Es fehlen: f2g und die Zufallsabläufe (M-1), der F20/E3-Bezug und die Option „Verschieben“ (M-2), die S6b-Abhängigkeit und der fehlende Commit (M-3).
   - Die Folgen von (b) („P4 bleibt offen“) sind nicht gemessen. Die Mutationsübersicht stützt sie nur indirekt (K3: P4 rot, f2b-U6 nicht rot). Dort „(vermutet)“ ergänzen.
3. **Format:**
   - Zeile 1/2 ist vorhanden.
   - Der Kopfblock hat 7 Zeilen (höchstens 10) und alle Pflichtteile.
   - Die Probleme sind weitgehend selbsttragend (Ausnahme L-10). Die Fragen sind einzeln beantwortbar.
   - Glossar und Belegliste sind vorhanden. Keine Zeitschätzungen, keine E-Mail-Adressen und kein Token.
4. **FG-Nummern:** siehe M-9 (FG-97 N8, FG-98 Zählprüfung, Fensterziehen-Test unter FG-60, FG-99 nur für die Schleife).
5. **OFFEN ab 13.10. 22:30 und Stufen:**
   - Es fehlt keine Chat-Entscheidung, die dort steht. Fehlende Nico-Punkte und Befunde: L-7, L-8, L-9.
   - Falsch eingestuft:
     - E1-4 (D8c) als E1 statt E2: M-7.
     - E1-5 (Nummernvergabe) als E1: M-9.
     - Frage 16 möglicherweise E3: M-8.
     - Frage 6 ist durch die Weisung schon entschieden; ihr Umbau unter FG-60 wäre ohne Frage möglich: S-1.
     - Frage 15 ist durch die Weisung schon geregelt: L-11.
6. **Länge:** L-11.
