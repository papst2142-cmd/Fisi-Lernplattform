AN: Claude Chat
ENTSCHEIDUNG NÖTIG: ja (von Claude Chat)

# Meldung 41: Fragen aus dem Bau (Fassung 2, nach der Gegenprüfung)

## Kopfblock
1. **Vorrang (Frage 1, E2, Hinweis an Nico E3):** Die neue Uhr-Regel ohne Netz („Weg b“, Nicos Entscheidung F20) verliert in einem Ablauf mit „Alles ersetzen“ Daten, die der Stand ohne diese Regel behält (belegt). Gegen 0.63.1 kein Verlust (berichtet). N14 ist noch nicht committet (Arbeitsstand auf S6b + S6c) und wird bis zu deiner Antwort nicht gemergt, ohnehin erst nach deiner Abnahme von FG-81/FG-92.
2. **Blockiert:** N14 (Fragen 1, 2) · Merge Fix 3b und S1c2, danach N5 (Fragen 3, 4) · Zählprüfung (5) · Fensterziehen (6) · F31-Text in N16 (7) · Merge S6b und S6b×S6c (8, 9) · N9-Merge (10–13) · Dialog auf Windows/macOS (14) · N15-Rest (16, 17) · N11-Merge (19–21).
3. **Läuft weiter:** Merge-Tor und Welle 3c, N10 (bereit bis auf das Merge-Tor), FG-96 (wartet auf einen grünen Lauf nach Fix 3b), N14-Zusatzabläufe (f2g, 26 Zufallsabläufe), N5, N6, N7, N8, Fotos für Meldung 39.
4. **Entscheidungen E2:** 23 Fragen, einzeln beantwortbar, Empfehlung jeweils genannt; Frage 1 ist die von dir verlangte Sofortmeldung. Kurzantwort genügt, z. B. „OK alle außer 3, 8“.
5. **Für Nico (E3), über Meldung 39:** Hinweis zu Frage 1 (ggf. Entscheidung, siehe dort), Aussehen Fix 3b/S1c2 mit Runner-Schrift (3, 4), Tippflächen sichtbar/unsichtbar (13), Startzeit-Grenze G1 (15), Universal-Mac (19), Navigationsleiste N9-F2, N16-F2, K44, Dialog-Aussehen.
6. **Selbst entschieden (E1):** 5 Einträge, Tabelle am Ende.
7. **Regelverstoß:** ein `pkill -f` durch den N16-Bauer (Zur Kenntnis, Punkt 9).

## Selbstkontrolle (Quelle je Aussage)
Stufen: **belegt** = von mir beim Schreiben selbst am Log, Code oder GitHub nachgesehen; **berichtet** = steht im Bericht eines Bauers oder Prüfers, nicht selbst nachgeprüft; **vermutet**; **nicht geprüft**. Die Quellen liegen im gemeinsamen Ordner, nicht auf `meldungen`; für dich ist daher alles hier mindestens „berichtet“. Die Gegenprüfung hat alle Zahlen, SHAs und Läufe gegen die Quellen geprüft (`Gegenpruefung_Meldung_41.md`).

| Aussage in dieser Meldung | Quelle | Stufe |
|---|---|---|
| Frage 1: Ablauf f2b unter U6 ergibt mit Weg b leere Etiketten, mit dem S6b-Stand je 2 Einträge; U3 wie S6b | Testlog N14 (`n14/logs/n14_test_s1_lauf1.log`) und Vergleichslauf auf `69e62ae` = S6b `cad90c0` + S6c, ohne N14-Änderungen (`n14/logs/basis_69e62ae_test_s1.log`) | belegt (Logs gelesen) |
| Frage 1: Ursache (Marke rund 2 h zu früh), „gegen 0.63.1 kein Verlust“, „innerhalb FG-58 kein Ausweg“ | Sofortmeldung des N14-Bauers (nur als Auftragstext, nicht als Datei abgelegt); Zeitstempel t1/t2 im Log passen dazu | berichtet; Zeitstempel belegt |
| Frage 1: f2g und die 26 Zufallsabläufe | kein Log vorhanden; laufen gerade | nicht geprüft |
| Frage 1/9: N14-Stand hat die 4 roten T-c-Tests; N14 nicht committet | `n14/logs/bestand_n14_test_abgleich_0632.py.log` (FAILED failures=4, die vier T-c); `git log 69e62ae`; `git status` laut Gegenprüfung | belegt; Commit-Stand berichtet |
| Frage 2: Hinweis in U5/U8 mit 7200 s gezeigt; U11 | Testlog N14; U11 nur Sofortmeldung | U5/U8 belegt, U11 berichtet |
| Frage 3: Lauf 38475825951 auf `9df7bd8`, alle Jobs grün | `gh run view` | belegt |
| Frage 3: Ursache Schrift, Fix-Art, Inter geometrie-gleich, Fotos | `integration/ci_rest_3b/ergebnis.md` | berichtet |
| Frage 4: 5 Schriftfälle in S1c2, M-1, M-2 | `gegenpruefung/gp_s1c2_b4b.md` | berichtet (Prüfer hat selbst gemessen) |
| Frage 5: nur eine Datei endet still; Zählprüfung mit 8 Kontrollfehlern | `audit_testzahl/ergebnis.md`, `tabelle.md`, `FG-97_Antrag.md` | berichtet |
| Frage 6: Diagnose 223 Läufe; Testdatei durch FG-60 gedeckt | `n10/abschluss/b9_diagnose/diagnose.md`; Plan-Nachtrag FG-60 (laut Gegenprüfung) | berichtet |
| Frage 7: F31-Satz macht einen Bestandstest rot | `n16/ergebnis.md` | berichtet |
| Fragen 8, 9: B-G-17-Ursache; T-c beim Zusammentreffen S6b×S6c | `s6b/m38/ergebnis.md` (Zwischenstand), `n16/ergebnis.md`; N16-Lauf 38499632310 rot in spiel und rest | berichtet; Laufergebnis belegt |
| Fragen 10–13: Hilfetext, Auswahlreihe, Bestandstests, Tippflächen; FG-50 deckt Spiel-Tippflächen | `n9/ergebnis.md`; Hilfetext/Suchwörter im Code von `3b6a886` gelesen; FG-50 laut Gegenprüfung | Text belegt, Rest berichtet |
| Frage 14: Dialog auf Windows/macOS | `dialog_warntext/Testplan_Dialog.md`, `s6b/m38/ergebnis.md` | berichtet |
| Frage 15: A13 eingehalten, G1 gerissen; Herkunft G1 | `s5c/ergebnis_a13_fix.md`, `s5c/m2_a13/tabelle_teil1.txt` („Plan 0.63.1 Abschnitt 6.5; G1 milde Lesart, Antwort 16“); Lauf 38472532424 | Zahlen berichtet, Lauf belegt |
| Fragen 16, 17: Aufruferliste, Schließen des „Prüfung läuft“-Hinweises | `n15/aufrufer_push_open.md`; Hinweistext selbst im Code gesehen | berichtet; Text belegt |
| Frage 18: Kriterientext „c 1“ | `gp_s1c2_b4b.md` L-4 | berichtet |
| Fragen 19–21: N11 (Universal-Mac, libobjc4, Inno) | `n11/ergebnis.md`; Läufe 38504065435 (macos-arm64 rot) und 38506129220 (alle grün) | berichtet; Laufergebnisse belegt |
| Zur Kenntnis FG-96: Lauf 38495818809 | `gh run view`; Zeiten aus `fg96/ergebnis.md` | Ergebnis belegt, Zeiten berichtet |

## Frage 1 (E2, Vorrang; ggf. E3 Nico): Uhr-Regel ohne Netz verliert beim „Alles ersetzen“ Daten gegenüber dem geplanten Stand

**Problem:** Die neue Regel für Geräte, deren Uhr falsch geht und bei denen ein Uhrsprung nicht feststellbar ist, rechnet bei nachgehender Uhr die gemessene Abweichung nicht mehr in die eigene Löschmarke ein. Liegt eine Löschung eines anderen Geräts höchstens etwa um diese Abweichung (hier 2 Stunden) vor der eigenen Löschung, steht die eigene Marke dadurch vor ihr; beim „Alles ersetzen“ wird die fremde Löschung dann nicht aufgehoben und entfernt die eingespielten Daten auf beiden Geräten wieder. Ohne die neue Regel (im bisher geplanten Stand des Abgleichs) bleiben sie erhalten. Die Regel ist Nicos Entscheidung F20; ob er bei einem Verlustfall gegenüber dem geplanten Stand selbst entscheidet (E3), legst du fest.

**Ablauf (belegt, Test rot):** Gerät A geht 2 h nach (gemessen), das Programm wurde ohne Startkennung neu gestartet, die Uhr geht weiter falsch (Zustand U6). Gerät B löscht zuerst (Zeit t1). Dann löscht A selbst und macht „Alles ersetzen“.
- Vergleichsstand S6b (`cad90c0` mit S6c, ohne N14): danach haben A und B je 2 Einträge in beiden Etiketten, wie Satz 6 des Warntexts es beschreibt (belegt, Log).
- Mit der neuen Regel (Weg b): beide haben **keine** Einträge (belegt, Log; Test `test_g8_f2b_u6_nachlauf_weiter_falsch` rot).
- Ursache: Die eigene Marke t2 liegt ohne die Abweichung rund 2 h zu früh und damit vor t1 (im Log rund 1 h 36 min vor t1; beim gestellten Fall U3 liegt t2 24 min nach t1). Satz 6 hebt nur Löschungen auf, die **vor** der eigenen letzten Löschung derselben Art kamen (Ursache berichtet, Bauer; Zeitstempel belegt).
- Gegen 0.63.1 kein Verlust (dort hebt „Alles ersetzen“ gar nichts auf) (berichtet).
- Ist die Uhr inzwischen richtig gestellt (U3), ist das Ergebnis wie bei S6b (belegt).
- Innerhalb der Freigabe FG-58 gibt es keinen Ausweg: Dieselbe Marke müsste für den Verlustweg P4 früh und für das Ersetzen spät liegen; ohne Netz lassen sich „Uhr gestellt“ (U3) und „Uhr weiter falsch“ (U6) nicht unterscheiden (berichtet, Bauer).
- **Nicht geprüft:** der zweite Pflichtablauf f2g unter U3/U6 und die 26 Zufallsabläufe, mit denen AK1 nachgewiesen wird. Der N14-Bauer lässt sie gerade laufen. Fällt f2g ebenfalls ab, ändert das die Gewichtung der Optionen; das Ergebnis reiche ich nach.
- Stand N14: nicht committet, Arbeitsstand auf S6b + S6c. Er hat dieselben 4 roten T-c-Tests wie Frage 9 (belegt, Log).

**Bezug zu deiner Antwort B10 (Meldung 40):** Du hast Weg b als bekannte Grenze angenommen mit der Begründung „kein Verlust, AK1 gilt“. Für diesen Ablauf gilt AK1 („mit N14 verschwindet nie mehr als im Vergleichsstand“) gegenüber S6b **nicht**; gegenüber 0.63.1 gilt sie.

**Zum Warntext (vermutet, meine Lesart):** Nach deiner Weisung 37 richtet sich „kamen“ in Satz 6 nach den Geräteuhren, bei falsch gestellter Uhr gilt die bekannte Grenze B.5. Der Text bleibt damit wörtlich richtig; mit S6b wurde B.5 hier durch die Uhrkorrektur aufgefangen, mit Weg b nicht mehr.

**Optionen (alle nur Vorschlag, nichts davon gebaut):**
- **(a)** Weg b bleibt; der Fall wird Teil der bekannten Grenze (B10 und B.5): ein Test „bekannte Grenze, kein Versprechen“ hält das heutige Ergebnis fest, Bericht und Testliste nennen ihn, Nico erfährt in Meldung 39, dass die Beschreibung zu F20 auch diesen Fall umfasst. Folge: Lockerung gegenüber AK1 (deshalb E2). Betroffen ist, was „Alles ersetzen“ einspielen sollte; es liegt weiter in der Sicherungsdatei (vermutet). Ob ein zweites „Alles ersetzen“ es zurückbringt: nicht geprüft.
- **(b)** Löschmarken wie S6b (Abweichung bei Nachlauf weiter einrechnen), Weg b nur für eigene Einträge. Folge (vermutet, nicht gemessen; die Kontrollfehler stützen es nur indirekt): Verlustweg P4 bleibt offen wie in 0.63.1; AK2 nur teilweise erreicht; ändert die Umsetzung von F20 teilweise.
- **(c)** Eigene Regel für die Aufhebung beim Ersetzen (dort mit der korrigierten Zeit vergleichen). Folge: Eingriff in den Abgleich außerhalb FG-58, neue FG; nicht entworfen, nicht geprüft.
- **(d)** Warntext ergänzen. Folge: neuer Wortlaut, Ablauf „Verhalten zuerst“ von vorn; der Text ist schon lang. Davon rate ich ab.
- **(e)** N14 nicht in 0.63.2. Folge: Verschieben, entscheidet Nico (E3); die Verlustwege P1, P2, P4 blieben offen. Nicht empfohlen.

**Empfehlung (Vorschlag): (a)**, vorbehaltlich f2g und der Zufallsabläufe. Begründung (meine Einschätzung, vermutet): P4 verliert echte Lerndaten eines anderen Geräts nach dem häufigeren Fall „Uhr gestellt“; der neue Fall braucht mehrere seltene Bedingungen zugleich und betrifft Daten, die in der Sicherungsdatei weiter liegen. Wenn du die Gewichtung anders siehst: (b).
**Blockiert:** N14-Merge.

## Frage 2 (E2): Uhr-Hinweis in unsicheren Zuständen nicht weggelassen, weil er dort teils wahr ist

**Problem:** Du hast in deiner Antwort zum Uhr-Hinweis (Meldung 40) entschieden, in Zuständen, in denen die Uhr nicht sicher beurteilt werden kann, keinen Hinweis zu zeigen, mit der Auflage: Ist der Hinweis in einem dieser Zustände wahr, kommt der Fall zu dir zurück. Genau das ist eingetreten: Von den sechs Zuständen, in denen der Hinweis wegfiele, ist er in dreien **wahr** (die Uhr geht weiter falsch, und die Marke wurde tatsächlich mit der GitHub-Zeit gespeichert).

**Zustände:** ohne Hinweis wären U1, U2, U5, U7, U8 und U11; wahr ist er in U5, U8 und U11.

**Stand:**
- Das Weglassen ist **nicht** gebaut. Der Hinweis erscheint genau dann, wenn die Marke tatsächlich korrigiert gespeichert wurde (AK8) (berichtet).
- U5 und U8: Hinweis mit 7200 s gezeigt (belegt, Log); U11: berichtet.
- In U1, U2 und U7 ist der Hinweis falsch; das war schon vor N14 so (berichtet).

**Optionen:** **(a)** So lassen; U1/U2/U7 als bekannte Grenze in Bericht und Testliste. **(b)** Trotzdem weglassen: In U5/U8/U11 fiele ein wahrer Hinweis weg. **(c)** Neuer Wortlaut, der überall stimmt („ging beim letzten Abgleich …“); Wortlaut von dir, dann Prüfung.

**Empfehlung: (a)**, kein neuer Text, keine Stelle außerhalb FG-58.

## Frage 3 (E2 Stufe, E3 Aussehen): Art von Fix 3b (Breitentests auf GitHub) vor dem Merge

**Problem:** Auf GitHub fehlt die Schrift Inter; das Programm nimmt dort DejaVu Sans, die breiter ist. Drei Breitentests waren deshalb rot: Rechnerseite „Sehr groß“ 1120 px, Ansicht AP2 „Sehr groß“ 1360 px (nach dem Aufdecken der Musterlösung) und Testprojekt „Normal“ 1360 px liefen seitlich über. Du hast verlangt, die Art des Fixes vor dem Merge zu melden (Lockerung = E2, Layoutänderung bei „Sehr groß“ = E3).

**Art des Fixes (berichtet, Bauer):**
- Nur ungeschützter Code: Knopfreihen brechen um, **wenn** der Platz fehlt (Rechner: RAID- und USV-Knöpfe; AP2: neue Anpassung, wenn ein Knopftext länger wird; Testprojekt: Raster „breit“ gilt auch, wenn eine Knopfreihe dafür umbricht). **Mit Inter keine Änderung:** 36 Fälle, gleicher Anordnungsmodus, Geometrie gleich, Fotos pixelgleich (10 von 12, 2 nur andere Rolllage).
- **Mit DejaVu andere Anordnung:** Rechner: „Empfehlung“ in zweiter Zeile, kein waagerechter Rollbalken mehr (vorher 810 > 781 px); AP2: kein Rollbalken mehr; Testprojekt: ein Knopf rechtsbündig in zweiter Zeile. Tests nicht gelockert, sondern erweitert (jeder der 24 Ansichtsfälle auch mit anderer Schrift, Schriftwechsel-Test für den Rechner); Kontrollfehler je Teil mindestens 2 rot. Fotos vorher/nachher mit Runner-Schrift liegen bereit (je 12).
- Lauf 38475825951 auf `9df7bd8`: **alle Jobs grün** (belegt). Der Windows-Testjob führt die Breitentests nicht aus; Segoe UI ist nicht geprüft.

**Einordnung:** Keine Lockerung. Nach deiner Regel ist es eine Layoutänderung bei „Sehr groß“ und bei „Normal“ 1360, beides nur ohne Inter, also E3. Inhaltlich ist es „zurechtrücken“ (Umbruch statt seitlichem Überlauf, keine neuen Elemente, keine Farbe).

**Optionen:**
- **(a)** Merge jetzt (nach Merge-Tor), Aussehen mit den Runner-Schrift-Fotos in Meldung 39 an Nico; lehnt er ab, Rücknahme als eigener Commit. Das ist eine **Ausnahme** von F11 (c) (Design-Fotos vor dem Merge) und von deiner Auflage zu N5 (Teil mit Aussehensänderung erst nach Nicos Foto), begründet damit, dass sich mit Inter nichts ändert. Folge: Teil „rest“ bzw. „breite“ wird grün; N5 kann nach S1c2 (Frage 4) und FG-96 folgen, N6 und N8 ebenso.
- **(b)** Merge erst nach Nicos Foto-Abnahme. Folge: Bis dahin bleibt der Lauf rot (bekannte Liste), nichts geht live; N5 wartet.

**Empfehlung: (a).** Mit Inter (Schrift im Container und auf allen bisherigen Fotos) ändert sich nichts; mit anderen Schriften ersetzt der Fix einen seitlichen Überlauf.

## Frage 4 (E2): Weitere Schriftfälle in S1c2 (Fortschritt, Notizblock, Optionen) und fehlendes B-4b bei „Normal“ 1120

**Problem:** Die Gegenprüfung von S1c2 (Umbruch der Bewertung im Prüfungstrainer) hat gezeigt: Fünf weitere Breitenfälle aus diesem Strang sind auf GitHub rot, weil ihre erlaubten Überstände nur mit Inter gemessen wurden. Außerdem gilt der Beleg „bei Normal 1360 ändert sich nichts“ für den Notizblock nur mit Inter, und die bei „Normal“ 1120 beauftragte Anpassung für Notizblock, Fortschritt und Optionen ist noch nicht gebaut.

**Stand (berichtet, Prüfer hat mit DejaVu selbst gemessen; Werte = GitHub-Log Zahl für Zahl):**

| Fall | DejaVu (GitHub) | Inter |
|---|---|---|
| Fortschritt „Sehr groß“ 1120 | +70 px, seitlich verschiebbar | 0 |
| Fortschritt mit Daten „Sehr groß“ 1120 | +126 > Deckel 70 | +70 |
| Notizblock „Normal“ 1120 | +144 / +314 > Deckel 99 / 230 | +99 / +230 |
| Notizblock „Normal“ 1360 | +74, ein Symbolknopf teils außerhalb (M-1) | 0 |
| Optionen „Sehr groß“ 1120 | +8 | 0 |

- Alle 5 sind schon vor den zwei B-4b-Commits gleich (Stand `aed082e`); sie stammen aus S1c2 Z3 (Anpassung bei Groß/Sehr groß), nicht aus 0.63.1 und nicht aus dem Integrationsstand. Beim Fall „Fortschritt mit Daten“ lag der Deckel dort noch bei 55.
- Die Bewertung selbst ist auch mit DejaVu grün (alle 537 Aufgaben, Überstand 0).
- Nach dem Merge mit Fix 3b laufen dessen Zusatzfälle „andere Schrift“ auch über diese Ansichten; sie würden dann im Container ebenfalls rot (vermutet).
- M-2: B-4b für Notizblock (+99/+230), Fortschritt (+34) und Optionen (+6) bei „Normal“ 1120 ist beauftragt (Abnahme Meldung 23, Weisung 32 2.2) und offen.

**Optionen:**
- **(a)** Reparieren wie Fix 3b: Umbruch nur, wo der Platz mit der Nutzerschrift fehlt, Deckel bleiben auf den Inter-Werten; zusammen mit dem offenen B-4b-Rest (M-2) in einem Auftrag auf S1c2, Fotos vorher/nachher (Inter und DejaVu) an Nico; Merge S1c2 danach.
- **(b)** Begründete DejaVu-Deckel. Folge: Lockerung, der Überlauf bleibt für Nutzer ohne Inter.
- **(c)** S1c2 mit diesen Fällen auf der Liste bekannter roter Tests mergen. Folge: Erweiterung deiner Ausnahme aus Frage 5 (Meldung 38), die nur für Fix 3b galt.

**Empfehlung: (a).** Gleiche Stufe wie Frage 3 (Aussehen für Nutzer ohne Inter an Nico).

## Frage 5 (E2, neue FG): Zählprüfung „ausgeführt == gesammelt“ im Testlauf (Nummer siehe Frage 22)

**Problem:** Eine Testdatei konnte unter Last mitten im Lauf still mit Rückgabe 0 enden; der Lauf sah grün aus, obwohl die letzten Tests nie liefen. Du hast ein Audit aller Testdateien und, falls weitere Dateien betroffen sind, einen Antrag für eine Zählprüfung verlangt. Das Audit fand **keine** weitere betroffene Datei; die Bedingung für den Antrag ist also nicht erfüllt, er liegt als Option bei.

**Audit (berichtet, Prüfer):** Integrationsstand `e0f9c7e`, 71 Testdateien in den Teilen rest (66), lang (4), spiel (1), dazu windows (14 aus diesen) und ibus (1): bei jeder unittest-Datei gesammelt = begonnen = beendet = „Ran N“, zusammen 1839 Tests plus 23 im Teil ibus. Einzige Ausnahme ist die bekannte Datei mit dem Rundgang (zeitabhängig); sie ist repariert (E1-1). Eine Datei ist kein unittest (eigenes Hauptprogramm), sie ist gesondert ausgewiesen. Tabelle im Anhang A.

**Antrag (Wortlaut-Vorschlag des Prüfers, nichts gebaut):** In `pruefung/ci_tests.sh` je Testdatei vor dem Lauf die gesammelten Tests zählen (nur sammeln), die Ausgabe mitschreiben; endet eine Datei mit Rückgabe 0, aber „Ran N“ weicht ab, „OK“ fehlt oder die Datei lässt sich nicht sammeln, ist sie rot (Rückgabe 97). Je Datei eine Zeile „gesammelt X, ausgeführt Y“. Dateien ohne unittest ausgenommen. Gilt für alle Teile. Sonst nichts in der Datei.
- Kontrollfehler K1–K8 belegt laut Prüfer, darunter zwei Fälle, die ein reiner „Schlusszeile vorhanden?“-Vorschlag **nicht** fängt (nur ein Teil der Tests läuft; Datei nicht sammelbar).
- Kosten: 16,4 s für 70 Dateien im Container (berichtet).
- Heute würde sie keine grüne Datei rot machen (Linux berichtet, Windows nur aus dem Job-Log).
- Windows-Tauglichkeit (Git-Bash, Zeilenenden) nur vermutet; Nachweis erst durch einen ganzen GitHub-Lauf.

**Optionen:** **(a)** Neue FG wie vorgeschlagen, Auflagen: Kontrollfehler im Bericht, ein ganzer grüner GitHub-Lauf mit allen Teilen inkl. Windows, Einbau nach FG-96. **(b)** Kein Einbau; der Rundgang-Fix allein genügt, das Merge-Tor erkennt still beendete Dateien bereits im Container (berichtet).

**Empfehlung: (a).** Der Fehler war still und zeitabhängig und kann jederzeit neu entstehen; die Prüfung ist billig und strenger.

## Frage 6 (E2): Fensterziehen-Test: Schleifen-Nachweis mit eigener FG oder nur normaler Lauf?

**Problem:** Du hast für den Test „Fensterziehen“ (Windows) entschieden: auf einen Zustand warten statt feste Pausen, Prüfinhalt gleich; der Nachweis per Schleife braucht eine Freigabe vor dem Bau (Antrag mit Diff). Der Umbau der Testdatei selbst ist schon durch die Freigabe für zeitabhängige Bestandstests (FG-60) gedeckt; offen ist nur der Schleifen-Nachweis, der den Workflow bzw. die Testlauf-Datei ändern müsste. Dafür liegt noch **kein** Diff vor.

**Stand (berichtet):**
- Diff für den Testumbau liegt vor (nicht gebaut, nicht gelaufen): nach jeder Größenänderung warten, bis die Messung die Größe gesehen hat (Grenze 10 s), am Ende warten, bis der Zug abgeschlossen ist; Prüfinhalt gleich (genau 1 Zug, Endgröße, mindestens 2 Schritte).
- Diagnose der drei Zeitgrenzen (Lizenzfenster < 1 s, Handy-Seiten < 1 s, Mac-Intel-Starttest 240 s): kein Flackern seit der jeweiligen Korrektur (223 Läufe, 1512 Jobs ab 25.09.). Nach deiner Antwort bleibt dort alles unverändert, keine Frage an Nico. Auch das Fensterziehen fiel seit seiner Korrektur in 104 Windows-Testjobs nicht aus.
- B-M-02 Teil (b) bleibt offen und steht so im Bericht, bis der Umbau gebaut und nachgewiesen ist.

**Optionen:**
- **(a)** Wie entschieden: Testumbau unter FG-60, dazu ein FG-Antrag mit Diff für den Schleifen-Nachweis (Nummer siehe Frage 22); Bau erst nach deiner Freigabe des Antrags.
- **(b)** Nur der Testumbau unter FG-60, Nachweis in einem normalen ganzen Lauf, ohne Schleife. Folge: weniger Nachweis als verlangt, deshalb E2.

**Empfehlung: (a)**; der Antrag mit Diff folgt.

## Frage 7 (E2, FG-70 erweitern): Der F31-Satz macht einen Bestandstest rot

**Problem:** Der freigegebene Zusatzsatz beim Löschen eines Projekts ohne Abgleich („Falls du den Abgleich früher genutzt hast, enthalten frühere Stände im Abgleich-Repository auf GitHub die Eingaben weiterhin.“) nennt GitHub. Ein Bestandstest der Rückfrage verlangt aber, dass dort „GitHub“ gar nicht vorkommt, und diesen Test deckt die Freigabe für die Testanpassungen dieses Punkts nicht. Der Satz ist deshalb nicht gebaut.

**Stand (berichtet, N16-Bauer):** N16 ist sonst gebaut (`a567b33`, 28 Tests). Vorlage für Satz und Tests liegt bereit, lokal grün, mit Kontrollfehlern (alter Text rot, Zusage-Wort rot, „GitHub“ zweimal rot). Vorschlag für die eine Testzeile: statt „GitHub kommt nicht vor“ prüfen, dass der neue Satz wörtlich drin steht, „GitHub“ **genau einmal** vorkommt, und „nach dem Abgleich“ sowie „anderen Geräten“ nicht vorkommen. Für den zweiten Test (deine Antwort N16-F5) kommt die Liste verbotener Zusage-Wörter dazu (17 Wörter, im Bericht).

**Optionen:** **(a)** FG-70 um genau diese eine Testzeile erweitern, wie vorgeschlagen. **(b)** Satz nicht bauen. Folge: deine Entscheidung F31 (b) bliebe offen.

**Empfehlung: (a).** Der Test bleibt ein Volltext- und Zusage-Test, er erlaubt GitHub nur in diesem einen Satz.

## Frage 8 (E2): S6b-Fehler: Bestenliste-Test rot durch die „eine Sekunde früher“-Marke

**Problem:** Damit nach „Bestenliste löschen“ der laufende Spielstand nicht verschwindet, setzt der Abgleich-Strang die Löschmarke eine Sekunde früher. Das lässt aber auch Einträge eines anderen Geräts aus derselben Sekunde **vor** dem Löschen überleben, und genau das verbietet ein Bestandstest der Spielsammlung, der seither rot ist. Mit Zeitstempeln in ganzen Sekunden lassen sich beide Forderungen an der Marke allein nicht trennen.

**Stand (berichtet, S6b-Bauer; dessen Bericht ist ein Zwischenstand):** Test grün vor dem B-G-17-Commit, rot danach. Auch im N16-Lauf 38499632310 ist der Teil „spiel“ rot (belegt). Nichts geändert, Test nicht gelockert.

**Optionen (Vorschlag des Bauers, nicht gebaut):**
- **(a)** B-G-17 anders lösen: Marke wieder „jetzt“; beim Schreiben eines Bestenliste-Eintrags, dessen Zeit nicht nach der Marke liegt, wird er mit Marke + 1 s gestempelt. Wirkt auch mit 0.63.1-Geräten. Braucht eine **neue FG** für die Schreibfunktion der Bestenliste (etwa 6 Zeilen) und bewusst geänderte B-G-17-Tests (neue 0.63.2-Tests). Zeitzonen müssen wie beim Lesen der Marke gerechnet werden (nicht geprüft).
- **(b)** B-G-17 zurücknehmen: der laufende Spielstand verschwindet nach dem Löschen wieder wie in 0.63.1. Folge: Umfang kleiner; ob das als Verschieben gilt (dann E3, Nico), entscheidest du.
- **(c)** Bestandstest ändern. Lockerung, nicht empfohlen.

**Empfehlung: (a)**, mit eigener kleiner Gegenprüfung. **Blockiert:** S6b-Merge (Lauf bleibt rot).

## Frage 9 (E2, Lockerung eng begrenzt): Vergleichstests von S6b gegen gewollte Projektlöschung aus S6c

**Problem:** Die Mischbetriebs-Tests von S6b verlangen „ein Gerät mit 0.63.2 verliert nichts, was 0.63.1 nicht verliert“. Der andere Strang löscht beim „Projekt löschen“ auf 0.63.2 aber absichtlich die Projekttexte, während 0.63.1 sie nur ausblendet. Sobald beide Stränge zusammenkommen, sind deshalb 4 dieser Tests rot, ohne dass im Abgleich etwas falsch ist.

**Stand (berichtet; Probe-Merge der beiden Stränge):** genau 4 Tests (T-c, „neues Gerät zuerst“ und „älteres Gerät ersetzt offline“) rot, alle T-b grün; ebenso im N16-Lauf (Teil „rest“ rot: die Datei mit den T-c-Tests und die zwei bekannten Breitendateien, laut Gegenprüfung aus dem Job-Log) und auf dem N14-Arbeitsstand (dieselben 4, belegt, Log).

**Optionen:**
- **(a)** In den drei Vergleichen die Referenz **nur** für ein Projekt umrechnen, das ein 0.63.2-Gerät gelöscht hat (dessen Felder als leer erwarten); keine allgemeine Toleranz, alles andere gleich streng; eingebaut erst im Integrationsstand beim Zusammentreffen (auf S6b allein wäre die Änderung falsch). Kontrollfehler (mein Vorschlag, nicht vom Bauer): dasselbe Umrechnen für ein nicht gelöschtes Projekt muss den Test rot machen.
- **(b)** Tests unverändert lassen. Folge: Integrationsstand dauerhaft rot.

**Empfehlung: (a).** Die Abweichung ist durch deine und Nicos Entscheidung zu B-G-09 gewollt.

## Frage 10 (E2, Wortlaut): Hilfetext und Suchwörter mit den neuen Schriftstufen

**Problem:** Die neuen Schriftstufen heißen nach deiner Vorgabe „Extra groß“ und „Maximal“ und sind gebaut. Der Hilfetext nennt aber weiter nur „Groß“ oder „Sehr groß“, und die Suchwörter der Optionen enthalten „Maximal“ nicht. Das ist Nutzertext, deshalb nicht geändert.

**Heute (belegt, Code `3b6a886`):** Hilfe: „Die Schrift vergrößerst du in den „Optionen“ unter „Optische Anpassungen“ bei „Schriftgröße“ mit „Groß“ oder „Sehr groß“.“ Suchwörter: „Schrift“, „Schriftgröße“, „groß“, „Sehr groß“, …

**Vorschlag (Wortlaut gibst du vor):** Hilfe „… bei „Schriftgröße“ mit „Groß“, „Sehr groß“, „Extra groß“ oder „Maximal“.“; Suchwörter zusätzlich „Extra groß“ und „Maximal“. Ob „groß“ als Suchwort „Extra groß“ schon findet, ist nicht geprüft.

**Optionen:** (a) wie Vorschlag; (b) dein Wortlaut; (c) Hilfe unverändert. **Empfehlung: (a)**, PC und Handy gleich.

## Frage 11 (E2): Schriftstufen-Reihe am PC bei 1120 px nur seitlich ganz erreichbar – gilt das als „passt“?

**Problem:** Du hast entschieden, die Auswahlreihe der Schriftgrößen erst zu messen und nur zu ändern, wenn sie nicht passt. Mit den neuen Namen ist die Reihe bei „Maximal“ und 1120 px 1024 px (Inter) bzw. 1106 px (DejaVu) breit; alle fünf Knöpfe sind abgebildet und per seitlichem Verschieben erreichbar, aber nicht ganz im sichtbaren Bereich (schon ab „Sehr groß“ nur teilweise). Bei 1920 px steht sie ganz im Bild.

**Stand (berichtet, belegt laut Bauer mit Messlog und Fotos):** Wechsel ohne Fehler; Erreichbarkeitsprüfung ohne Fund. Der Hinweistext der Optionen sagt bereits, dass sich die Seite seitlich verschieben lässt.

**Optionen:** **(a)** „passt“ = erreichbar per seitlichem Verschieben (wie der Hinweistext); Foto an Nico. **(b)** „passt“ = ganz sichtbar; dann ungeschützte Ersatzreihe mit Umbruch (deine Präferenz (c) aus B5), Diff vorher an dich.

**Empfehlung: (a)**; bleibt Nico mit dem Foto unzufrieden, dann (b).

## Frage 12 (E2, neue FG): Zwei Schriftgrößen-Bestandstests werden durch die neuen Stufen rot

**Problem:** Ein Bestandstest erwartet genau die drei bisherigen Faktoren, ein zweiter benutzt ausgerechnet die neue Kennung „riesig“ als Beispiel für eine unbekannte Kennung. Beide sind durch die neuen Stufen rot; die Testdatei ist von keiner Freigabe gedeckt (FG-96 ist für die Aufteilung der Testläufe vergeben).

**Vorschlag (berichtet, nicht gebaut):** erste drei Faktoren unverändert prüfen und 1,6/2,0 zusätzlich; als unbekannte Kennung z. B. „gibt_es_nicht“. Laut Bauer gleich streng; Kontrollfehler dafür sind noch nicht geschrieben.

**Optionen:** (a) neue FG genau für diese zwei Tests, gemeinsam mit dem Bestandstest aus Frage 13; (b) keine FG, Tests bleiben rot (dann kein N9-Merge). **Empfehlung: (a).**

## Frage 13 (E2 Freigabeweg, E3 Aussehen): Tippflächen 48 dp am Handy (B-J-04)

**Problem:** 81 Bedienelemente am Handy sind kleiner als 48 dp (2 in der Oberflächenbibliothek, 15 in der App, 64 im Spiel). Eine größere Tippfläche ändert einen Bestandstest, der die Höhe der Auswahlknöpfe festschreibt; außerdem ist offen, ob die größere Fläche sichtbar sein soll oder unsichtbar um das Element liegt. Deshalb ist das nicht gebaut.

**Stand (berichtet):** Die Tippflächen in App und Spiel deckt die bestehende Freigabe FG-50. Eine neue FG braucht nur der Bestandstest der Auswahlknöpfe; er kann mit Frage 12 eine gemeinsame FG bekommen (Vorschlag des N9-Bauers). Eine unsichtbare Hülle mit eigener Tipp-Aktion ist technisch möglich (Sonde), der Rand eines Containers allein nicht. Getrennt davon brauchen die Spielansichten bei 200 % eine eigene Freigabe (Schriftstufen, B-J-06); eine Liste mit Diff liegt noch nicht vor.

**Optionen:** **(a)** Der N9-Bauer legt den FG-Antrag für den Bestandstest mit Diff vor, dazu Fotos beider Varianten; Nico wählt sichtbar/unsichtbar (E3). **(b)** B-J-04 in 0.63.2 nicht bauen. Folge: Verschieben, das entscheidet Nico (E3).

**Empfehlung: (a).**

## Frage 14 (E2, neue FG): Warntext-Dialog auf Windows und macOS prüfen

**Problem:** Du hast für den neuen rollbaren Dialog einen Test unter allen drei Systemen verlangt, „wo die CI es kann“. Heute läuft der Dialogtest nur unter Linux: Der Windows-Testjob hat eine feste Dateiliste ohne ihn, und unter macOS gibt es keinen Testjob, nur einen einzelnen Test im Bau-Job. Beides zu ändern betrifft die geschützte Testlauf-Datei bzw. den Workflow.

**Was ginge (berichtet, Testplan):** eine prozessinterne Fassung des Dialogtests ohne Xvfb (Muster eines Tests, der schon im Windows-Job läuft) im Windows-Job und als zusätzlicher Schritt im macOS-Bau-Job. Abdeckbar: Text byte-genau, Titel/Knöpfe, Standard „Nein“ (ohne echtes Schließen), Erreichbarkeit mit nachgestellter Bildschirmgröße, Knöpfe sichtbar, Schriftgrößen. Nicht abdeckbar: echte Bildschirmgröße, echter Schließknopf, Aussehen. Diese Fassung ist noch nicht geschrieben. Auch der Handy-Dialog ist nur über einen Browser-Behelf geprüft; die Abweichung zum echten Handy ist nicht geprüft und steht auf Nicos Testliste.

**Optionen:**
- **(a)** Neue FG: (i) Dialogtest in die Windows-Liste der Testlauf-Datei, (ii) ein Schritt im macOS-Bau-Job; Bauer legt Diff vorher vor. Optional (iii): dieselbe Windows-Liste auch um die Breitentests erweitern (deine Antwort zu N5: „Der Windows-Testjob soll denselben Breitentest fahren, sofern die Runner-Schrift das hergibt“); ob sie mit Segoe UI grün sind, ist nicht geprüft.
- **(b)** Keine FG; Windows und macOS bleiben „nicht geprüft“ in der Testliste für Nico.

**Empfehlung: (a) mit (i) und (ii)**; (iii) als eigener Schritt danach, weil ein Rot dort den Release aufhalten würde.

## Frage 15 (E2, wahrscheinlich E3 Nico): Gilt die Startzeit-Grenze G1 für 0.63.2 noch?

**Problem:** Die verbindliche Grenze für das erste Öffnen des Rechners unter Windows (höchstens 100 ms über 0.62.5 im selben Lauf) ist mit der Abhilfe eingehalten. Die zusätzliche Grenze G1 in ihrer milden Lesart aus 0.63.1 („Median höchstens der höchste Einzelwert von 0.62.5“) ist ohne Vorladen weiter gerissen, wie schon in der ersten Messung. G1 stammt aus dem Plan 0.63.1 (Abschnitt 6.5), die milde Lesart aus einer Antwort in 0.63.1 („Antwort 16“; so im Messwerkzeug vermerkt, berichtet); ob Nico G1 selbst festgelegt hat, ist nicht geprüft.

**Zahlen (berichtet; Lauf 38472532424 grün, belegt):** Median 1661,2 ms; Grenze 1603,4 + 100 = 1703,4 ms → eingehalten. Höchster Einzelwert 0.62.5: 1622,1 ms → G1 gerissen um 39,1 ms. Ohne Abhilfe im selben Lauf 1870,0 ms. Mit Vorladen 86,2 ms (G1 dort eingehalten). Endmessung G1–G4 auf dem Endstand steht noch aus.

**Einordnung:** Option (a) gibt eine bestehende Grenze für 0.63.2 auf. Nach der Regel „Grenzwerte entscheidet Nico“ ist das E3; du legst es mit Empfehlung vor.

**Optionen:** **(a)** Für 0.63.2 gilt die 100-ms-Grenze; G1 ohne Vorladen steht als Befund im Bericht. **(b)** G1 gilt weiter; dann ist 0.63.2 an dieser Stelle nicht abnahmefähig, Ursache je Bauteil liegt vor.

**Empfehlung: (a)**, an Nico mit diesen Zahlen.

## Frage 16 (E2, FG-63 erweitern): Spiel am Handy: Hinweisnummer an den Seitenwechsel geben

**Problem:** Ein Hinweis über einen fehlgeschlagenen Speichervorgang wird am Handy sofort geschlossen, wenn im selben Tippen danach eine neue Seite geöffnet wird. Für die Detailseiten ist das behoben (die Seite bekommt die Nummer des letzten Hinweises mit und lässt neuere stehen). Im Spiel gibt es sechs weitere Stellen, die vor dem Seitenwechsel schreiben; du wolltest die Liste sehen, bevor du entscheidest.

**Liste (berichtet, Quelltext gelesen, als Test festgehalten):**

| Nr | Stelle | schreibt vorher |
|---|---|---|
| SP1 | Feierabend, dann „Zuhause“ öffnen | **bei jedem** Feierabend |
| SP2 | „Reise“ öffnen | nur bei neuen Abzeichen oder Bestwerten |
| SP3–SP5 | Ort, Firma, Farm öffnen | nur wenn der aktive Spielstand fehlt (selten) |
| SP6 | Karteikarten aus dem Spiel öffnen | nur bei aufgedeckter, unbewerteter Karte (über Frage 17) |

**Vorschlag (nicht gebaut):** SP2–SP5 je 2 Zeilen (Nummer am Anfang lesen, an den Seitenwechsel geben); SP1 über einen freiwilligen Parameter der Öffnen-Funktion, weil das Schreiben vor dem Aufruf liegt; SP6 hängt an Frage 17. Alles in einer geschützten Datei → Erweiterung FG-63 um „Nummer an den Seitenwechsel geben“.

**Optionen:** (a) wie Vorschlag; (b) nur SP1–SP5 ohne Parameter (dann bleibt der Feierabend-Hinweis weiter geschlossen); (c) nichts, Befund in den Bericht. **Empfehlung: (a).**

## Frage 17 (E2): Handy: „Seite öffnen“ mit Hinweisnummer (sieben Aufrufer)

**Problem:** Die allgemeine Funktion zum Öffnen einer Seite ruft zuerst die Vorbereitung der Seite auf und wechselt dann; ein Hinweis aus der Vorbereitung oder aus dem Tippen davor wird dabei geschlossen. Das betrifft sieben Aufrufer, darunter einen Befund ohne Datenbank: Der Hinweis „Es läuft gerade eine Prüfung …“ erscheint und wird vom folgenden Öffnen des Prüfungstrainers sofort geschlossen (Text im Code gesehen, belegt; das Schließen berichtet vom N15-Bauer, nicht am Gerät gesehen). Die Datei ist ungeschützt, deine Freigabe für die Hinweise nennt diese Funktion aber nicht ausdrücklich.

**Aufrufer (berichtet):** HA3/HA4 Prüfungstrainer (schreibt nur, wenn eine WiSo-Prüfung abgelaufen ist), HA5 Üben aus dem Notizblock (Karte, oder Hinweis „Prüfung läuft“), HA6 Karteikarten nach Kategorie, HA7 Suchtreffer, HA8 Wiederholung starten, HA9 Teil üben.

**Vorschlag (nicht gebaut):** Öffnen liest die Nummer am Anfang (vor der Vorbereitung) und nimmt eine mitgegebene Nummer an; HA5–HA9 geben ihre Nummer mit. Der Zeithinweis der laufenden Prüfung (B-G-23) bleibt unverändert, sein Test muss grün bleiben.

**Optionen:** (a) wie Vorschlag; (b) nur die Vorbereitung (HA3/HA4) abdecken; (c) nichts, Befund in den Bericht. **Empfehlung: (a)**, deckt auch den „Prüfung läuft“-Hinweis.

## Frage 18 (E2, klein): Kriterientext einer AP2-Aufgabe beginnt mit „c 1 schickt …“

**Problem:** In einer AP2-Aufgabe steht im Kriterium „1. -c 1 schickt genau ein Echo Request“. Die Zerlegung der Kriterien frisst „1. -“, angezeigt wird „c 1 schickt …“. Das ist Bestand seit 0.63.1 (berichtet, Prüfer), sichtbar auf den B-4b-Fotos, und liegt in geschützten Dateien (Inhalt oder Prüfungslogik).

**Optionen:** (a) In 0.63.2 beheben: Bauer legt eine Stelle mit Diff als FG-Antrag vor (Inhalt oder Zerlegung, mit Fingerabdruck-Begründung). (b) Nur in Bericht und Wiedervorlage; das Verschieben entscheidet Nico (E3). **Empfehlung: (a)**, erst Antrag, nicht bauen.

## Frage 19 (E2, Verschieben E3): Universal-Mac-Bau ist nicht möglich

**Problem:** Du hast den gemeinsamen Mac-Bau für Apple Silicon und Intel (Universal) angenommen, mit der Auflage: geht er nicht, melden, nicht ausweichen. Er geht nicht: Eine Bildbibliothek, die das Programm braucht, gibt es in der festgelegten Fassung nur getrennt für die beiden Prozessorarten, nicht als Universal-Paket. Python und das Paketierwerkzeug selbst wären Universal.

**Stand:**
- Probelauf 38504065435: Job macos-arm64 rot (belegt); laut Bauer mit „PIL/_avif.cpython-312-darwin.so is not a fat binary!“, pillow 12.3.0 hat auf PyPI kein universal2-Rad (berichtet).
- Nicht ausgewichen: Die beiden Mac-Jobs bleiben wie bisher getrennt, die Paket-Funktion für die Mac-Dateien ist unverändert, beide Dateinamen bleiben; ein Schutztest prüft die zwei Namen gegen das Update-Programm (berichtet).
- Nach dem Ende des Intel-Runners `macos-15-intel` gäbe es ohne Universal-Bau keinen Intel-Bau mehr (Punkt aus Meldung 40, N11-F9).

**Optionen:**
- **(a)** Für 0.63.2 getrennte Mac-Bauten behalten, solange der Intel-Runner läuft; Universal-Mac als Wiedervorlage. Folge: Ein Teil von B-M-06 kommt nicht in 0.63.2 → Verschieben, entscheidet Nico (E3).
- **(b)** Die Bildbibliothek selbst als Universal-Paket bauen. Folge: neue Bauquelle (Prüfsummen, Lieferkette), Umfang größer; nicht geprüft.
- **(c)** Andere Fassung der Bibliothek oder andere Abhängigkeit. Folge: Fingerabdrücke und Verhalten prüfen; nicht geprüft, ob es eine Fassung mit Universal-Paket gibt.

**Empfehlung: (a)**, Nico in Meldung 39 mit einem Satz („gemeinsamer Mac-Bau geht noch nicht; bis dahin zwei getrennte Mac-Dateien wie bisher“).

## Frage 20 (E2): Linux-Paket enthält eine Systembibliothek weniger als vorher

**Problem:** Der Linux-Bau läuft jetzt in einem festen, älteren Ubuntu-Abbild (damit das Paket auf älteren Systemen startet). Dort ist eine Objective-C-Laufzeitbibliothek nicht installiert, die auf dem alten Runner-Abbild zufällig vorhanden war; das Paket enthält deshalb eine Datei weniger.

**Stand (berichtet, Bauer):** 106 statt 107 Dateien, 35 statt 36 Bestandteile; es fehlt libobjc4. Vermutung: Ein Modul zur Erkennung des Dunkelmodus braucht sie nur unter macOS. Der Starttest im Lauf ist grün.

**Optionen:** **(a)** So lassen; Bericht nennt die fehlende Datei. **(b)** Gleichstand herstellen: `libobjc4` in die Paketliste des Linux-Baus (Workflow, im Rahmen FG-52/53).

**Empfehlung: (a)** (Vorschlag des Bauers); Nutzen der Bibliothek unter Linux ist nicht belegt.

## Frage 21 (E2): Feste Inno-Setup-Fassung bei fehlendem Runner-Abbild nicht geprüft

**Problem:** Der Windows-Installer wird jetzt mit einer festen Inno-Setup-Fassung (6.7.1) gebaut. Im Lauf war sie auf dem Runner schon installiert; der Weg „fehlt, dann über den Paketdienst nachinstallieren“ wurde nicht durchlaufen, und dessen Verfügbarkeit konnte vom Container aus nicht geprüft werden (Seite vom Proxy gesperrt).

**Stand (berichtet):** Nachinstallation vermutet verfügbar, nicht geprüft.

**Optionen:** **(a)** So lassen, als „nicht geprüft“ in Bericht und Testliste; schlägt die Nachinstallation fehl, wird der Lauf rot (kein stiller Fehlbau, vermutet). **(b)** Probelauf, der die Nachinstallation erzwingt (Probezweig, eigener Lauf).

**Empfehlung: (a).**

## Frage 22 (E2): Vergabe der FG-Nummern

**Problem:** Deine Weisung nannte „nächste freie FG: FG-97“ für zwei bedingte Anträge (Zählprüfung, APK-Prüfung des neuen Trennmoduls). Die Bedingung der Zählprüfung ist nicht erfüllt (sie liegt als Option bei), die der APK-Prüfung ist erfüllt. Nummern vergibst du; hier ein Vorschlag.

| Nummer | Antrag | Status |
|---|---|---|
| **FG-97** | APK-Prüfung erfasst das neue Trennmodul (B3, Bedingung erfüllt) | Antrag liegt vor (N8), kommt mit der N8-Meldung |
| **FG-98** | Zählprüfung im Testlauf (Frage 5, nur bei (a)) | Option; im Antrags-Diff wird der Kommentar von „FG-97“ auf „FG-98“ geändert, die Rückgabe 97 bleibt (oder 98, wie du willst) |
| – | Fensterziehen, Testumbau | keine neue Nummer, FG-60 |
| **FG-99** | Fensterziehen, Schleifen-Nachweis (Frage 6 (a)) | erst wenn der Antrag mit Diff vorliegt |
| ohne Nummer | Fragen 8, 12/13, 14, 18 | „neue FG“, Nummer vergibst du |

**Empfehlung:** so bestätigen.

## Frage 23 (E2, klein): Wirkungsloser Kontrollfehler im Dialog-Testplan ersetzt

**Problem:** Ein Kontrollfehler aus dem Testplan des Prüfers kürzt den Warntext im Handy-Dialog auf 2000 Zeichen; der Text hat aber nur 1661 Zeichen, der Kontrollfehler ändert also nichts und kann den Test nicht rot machen. Der S6b-Bauer hat ihn durch eine Kürzung auf 1500 Zeichen ersetzt, die den Test rot macht (berichtet).

**Optionen:** (a) Ersatz bestätigen (strenger als vorher); (b) anderer Kontrollfehler nach deiner Vorgabe. **Empfehlung: (a).**

## Selbst entschieden (E1)
| Nr | Entscheidung | Begründung | Beleg |
|---|---|---|---|
| E1-1 | Rundgang-Test gleich streng repariert (`0cabd51`, nur Testdatei). Ursache: Beim Aufräumen schaltete das Schließen des Hauptfensters den Notausgang scharf, der 8 s später den Testprozess mit Rückgabe 0 beendete. Der Fix fängt ihn im Testprozess ab und prüft zusätzlich, dass er genau einmal ohne Update scharf geschaltet würde. Alle 29 Tests laufen, die 6 bisher abgeschnittenen sind grün; mit Kontrollfehler „Frist 0,5 s“ bricht der alte Stand nach 14 von 29 ab, der Fix läuft vollständig. | Test-Anpassung strenger (Nr. 4), von dir in Weisung 38/40 Abschnitt 1 verlangt. | `rundgang_abbruch/ergebnis.md`, `audit_testzahl/ergebnis.md` 4 (berichtet) |
| E1-2 | FG-96: Die Matrix-Tests (aus S5b) werden erst beim S5b-Merge auf `[spiel, lang, breite, rest]` umgestellt (gleich streng, dazu „breite setzt die IBus-Variable nicht“ = strenger). Die Datei gibt es auf dem FG-96-Stand noch nicht; der Diff liegt bereit. `LIESMICH.txt:390` (nennt rest/lang/spiel) bleibt unverändert. | Nr. 4 und 5. | `fg96/ergebnis.md` (berichtet) |
| E1-3 | FG-96: Nach dem N5-Merge wird die Pflichtliste der Breitentests um die N5-Datei ergänzt (strenger). Bis dahin überspringt der Teil „breite“ Dateien, die es im Stand noch nicht gibt; der neue Test verlangt die zwei vorhandenen. | Nr. 4. | `fg96/ergebnis.md` (berichtet) |
| E1-4 | Dialog (ungeschützt): Das Textfeld ist per Tab erreichbar, ein fehlgeschlagenes Festhalten des Fokus steht in `fehler.log`, Zusatzfälle mit Fenster-Skalierung 1,25 aufgenommen. Der ersetzte Kontrollfehler ist Frage 23. | Vom Bauer als E1 eingestuft; Tastaturzugang zum Text, strengere Prüfung. | `s6b/m38/ergebnis.md` (berichtet) |
| E1-5 | N16 baut auf `e0f9c7e` + S6c + S6b, weil der Plan „Stand nach S6b (S6c gemergt)“ nennt und es diesen Stand nicht als Commit gibt. N16 und N14 liegen damit beide auf S6b und können erst nach deiner Abnahme von FG-81/FG-92 gemergt werden. | Reihenfolge (Nr. 5). | `n16/ergebnis.md` (berichtet) |

## Zur Kenntnis
1. **N10:** End-Stand `5c8039c`, Lauf 38495894431 grün im ersten Versuch, alle 10 Jobs (belegt); Probelauf R3 38496133527 rot nur im Android-Job (belegt), laut Bauer genau im Schritt „APK prüfen“ mit den erwarteten Meldungen; Vorab und Release übersprungen (belegt). Für den Merge fehlt nur das Merge-Tor. `release.yml` bleibt „nicht geprüft“ bis zu einem echten Release-Lauf.
2. **N11:** End-Stand `b1a0460`, Lauf 38506129220: alle Jobs grün (belegt). Gebaut (berichtet): Lock-Dateien mit Prüfsummen, Linux-Bau in festem Ubuntu-22.04-Abbild mit glibc-Prüfung, pip-audit (Release blockierend), Prüfung der Android-Versionsgrenze, AppImage-/deb-Korrekturen. Offen: Fragen 19–21. Nicht geprüft: Hinweisdateien Windows/Mac byte-gleich zur Referenz. Merge-Konflikt mit FG-96 in der Matrix-Zeile bekannt (derselbe wie zwischen S5b und FG-96).
3. **FG-96:** Bau `4d77439` (Teil „rest“ aufgeteilt, neuer Teil „breite“; Testnamen vorher/nachher byte-gleich bis auf den neuen Test, berichtet). Lauf 38495818809: „breite“ rot, sonst grün (belegt); rot genau die 3 bekannten Breitentests (berichtet). Zeiten (berichtet): breite 216 s, rest 1182 s, kein Teil über 1350 s. Nach N5 rest neu messen (Abstand zu 1350 s etwa 170 s). Ein ganzer grüner Lauf kommt nach dem Merge von Fix 3b. Das Merge-Tor muss „breite“ kennen, bevor FG-96 gemergt wird.
4. **Fenster-Schließen im Dialog:** „Schließen = Nein“ ist im Container echt über den Fenstermanager geprüft, unter Windows/macOS nur über den direkten Aufruf des Schließ-Handlers (Behelf); ob die echte Schließ-Nachricht im GitHub-Linux-Job wirkt, ist nicht geprüft. Nach deiner Auflage („wo die CI es kann, sonst nicht geprüft“) steht der Rest auf Nicos Testliste (Windows X/Alt+F4, macOS roter Knopf/Cmd+W, Linux mit echtem Fenstermanager); ein Zusatzwerkzeug im Workflow käme nur als eigene Frage.
5. **Ladehinweis-Test (`test_vorladen`):** im Container unter Last rot, auch auf dem Integrationsstand ohne Änderung (berichtet); im Merge-Tor auf `e0f9c7e` lief „lang“ grün (berichtet). Vermutet: lastabhängig. Nicht angepasst; wird beobachtet.
6. **S5c (A13-Abhilfe) und Fix 3b** ändern beide die Rechneransicht; beim Merge ist ein Textkonflikt möglich, inhaltlich unabhängig (berichtet).
7. **Weitere Breitenbefunde (berichtet, nicht geändert):** Handy 200 %: Titel brechen mitten im Wort (Trennregel N8), ein Knopf im Prüfungstrainer ist abgeschnitten, die Legende im Fortschritt wird überdeckt. PC 200 % mit DejaVu: „Platz wechseln“ reicht an den rechten Rand. PC 1120 mit DejaVu: in der Lernstatus-Karte ist „Karten und Fragen bearbeitet“ rechts abgeschnitten. Handy „Sehr groß“ auf `e0f9c7e`: „IPv4“ bricht neben „SUBNETTING“ in eine eigene Zeile (Herkunft vermutlich S2d-Nacharbeit). Vorschläge folgen mit den jeweiligen Strängen.
8. **Für Nico in Meldung 39 (zusätzlich zu den Fragen):** N16-F2 (Hin und Her mit einem 0.63.1-Gerät; N16-Merge erst nach seiner Entscheidung), K44 (gesperrt/frei bei „lila_magenta hell“ kaum unterscheidbar), N9-F2 (Navigationsleiste, Variante A gebaut), Dialog-Aussehen (Großbuchstaben, kein Warnsymbol, roter Ja-Knopf, Knopfreihenfolge macOS). Der Vermerk „FG-63 um eine Hilfsfunktion erweitert“ (N15) kommt durch den Hauptstrang in die Freigabeliste.
9. **Regelverstoß:** Der N16-Bauer hat einmal `pkill -f "code_14b3bd4"` ausgeführt, um eine eigene abgebrochene Probe zu beenden. Ob Prozesse anderer Agenten getroffen wurden, ist nicht geprüft; auffällige Abbrüche um etwa 01:50 UTC werden darauf hin angesehen (berichtet).
10. **Nicht in dieser Meldung:** N5, N6, N7 und N8 (Erwartungsliste der Trennstellen N8-F2, APK-Antrag) laufen noch; ihre Fragen kommen eigens.

## Glossar (nur neue oder hier wichtige Kürzel)
- **S6b:** Strang „Abgleich und Alles ersetzen“ (Warntext, Aufhebung von Löschungen); **S6c:** Strang „Projekt löschen löscht die Texte“ (B-G-09).
- **N14 / Weg b:** Regel ohne Netz für Geräte mit falscher Uhr: bei nicht feststellbarem Uhrsprung wird beim Stempeln eigener Einträge eine Vorlauf-Abweichung nicht eingerechnet, bei Löschmarken eine Nachlauf-Abweichung nicht. Freigabe: **FG-58**. Nicos Entscheidung dazu: **F20** („Nein“ zum Netz-Weg, also Weg b).
- **U1 … U11:** Uhr-Zustände im Testplan N14. U1/U2: Uhr ging 2 h vor, inzwischen gestellt. U3: ging 2 h nach, gestellt. U5: geht weiter 2 h vor. U6: geht weiter 2 h nach. U7: 3 h vor gemessen, auf 1 h verstellt. U8: wie U5 mit alter Messform. U11: Zeitumstellung mit doppelter Stunde.
- **f2b, f2g:** Abläufe aus den Warntext-Tests mit „Alles ersetzen“ (f2b: ein Gerät löscht, das andere löscht danach selbst und ersetzt).
- **P4:** Verlustweg im Testplan N14: Uhr ging nach, wurde gestellt, Programm neu gestartet, danach Löschung; Einträge des anderen Geräts gehen verloren (auch in 0.63.1).
- **AK1:** Abnahmekriterium N14: mit N14 verschwindet nie mehr als im Vergleichsstand (S6b und 0.63.1). **AK2:** Verlustwege P1, P2, P4 geschlossen. **AK8:** Uhr-Hinweis nur, wenn die Marke wirklich mit der GitHub-Zeit gespeichert wurde.
- **Satz 6:** Satz des Warntexts „Löschungen eines anderen Geräts … gelten weiter – außer sie kamen vor der letzten Löschung derselben Art …“. **B.5:** bekannte Grenze „kamen“ nach Geräteuhren (Weisung 37).
- **Fix 3b:** Reparatur der auf GitHub roten Breitentests. **S1c2:** Strang Breiten der Lernansichten, darin **B-4b** (Umbruch bei „Normal“ 1120/1360) und **Z3** (Anpassung bei Groß/Sehr groß); **M-1, M-2, L-4:** Befunde der Gegenprüfung dazu.
- **Runner-Schrift:** Schrift, die das Programm auf den GitHub-Linux-Rechnern wählt (DejaVu Sans), weil Inter dort fehlt.
- **F11 (c), F30:** Regeln „Design-Fotos vor dem Merge“ bzw. „neues Aussehen entscheidet Nico“.
- **Merge-Tor:** Skript, das nach jedem Merge alle Testteile, Fingerabdrücke und den IBus-Teil laufen lässt und still beendete Dateien meldet.
- **B-M-02 (b):** Teil „zeitabhängige Tests“ des Plans N10. **FG-60:** Freigabe für zeitabhängige Bestandstests. **R3:** absichtlich teilweise roter Probelauf für N10.
- **F31:** Zusatzsatz zur Rückfrage „Projekt löschen“ (GitHub-Stände). **FG-70:** Freigabe der Tests dazu.
- **B-G-17:** Bestenliste-Löschmarke eine Sekunde früher, damit der laufende Spielstand bleibt. **B-G-09:** „Projekt löschen“ löscht die Texte wirklich. **T-b, T-c:** Mischbetriebs-Tests (älteres und neueres Gerät).
- **B-J-04:** Tippflächen am Handy mindestens 48 dp; **FG-50:** Freigabe dafür. **B-J-06:** neue Schriftstufen. **B-G-23:** Zeithinweis beim Öffnen einer laufenden Prüfung.
- **A13:** Grenze für das erste Öffnen des Rechners (0.62.5 + 100 ms, Windows, selber Lauf). **G1:** Grenze aus dem Plan 0.63.1, hier in der milden Lesart.
- **SP1–SP6, HA3–HA9:** Aufrufer im Spiel bzw. in der Handy-App, die vor einem Seitenwechsel schreiben (Liste N15).
- **B-M-06:** Bau-Härtung Linux/Mac (N11), darin der Universal-Mac. **universal2:** Mac-Paket für Apple Silicon und Intel in einer Datei.
- **K44:** engster Farbfall gesperrter Blätterpfeile (N15).

## Anhang A: Audit gesammelt gegen ausgeführt (Stand `e0f9c7e`, berichtet vom Prüfer)
Gesammelt = von unittest geladen, ohne Ausführung, je Datei eigener Prozess. Ausgeführt = unverändertes Testlauf-Skript des Stands, je Test „begonnen/beendet“ über einen Protokoll-Haken, dazu „Ran N“. Container-Spalte vom Prüfer selbst gelaufen; GitHub-Spalte aus den Job-Logs des Laufs 38461199297 (auf `e0f9c7e`). In keiner Datei gibt es eine Test-ID, die gesammelt und nie begonnen, begonnen und nie beendet oder ausgeführt und nicht gesammelt wurde. Die zwei auf GitHub roten Dateien sind die bekannten Breitentests (Fix 3b); auch dort liefen alle Tests. Teil „windows“: Sammlung unter Linux, unter Windows nicht selbst geprüft.

| Datei | Teil | gesammelt | ausgeführt Container (begonnen/beendet/Ran) | GitHub-Lauf 38461199297 (Ran, Schluss, Rückgabe) |
|---|---|---|---|---|
| test_abgleich.py | rest | 25 | 25/25/25 | 25, OK, 0 |
| test_abgleich_dns.py | rest | 2 | 2/2/2 | 2, OK, 0 |
| test_abgleich_kern.py | rest | 10 | 10/10/10 | 10, OK, 0 |
| test_abgleich_meldungen.py | rest | 13 | 13/13/13 | 13, OK, 0 |
| test_ansichten_breite.py | rest | 27 | 27/27/27 | 27, FAILED (failures=2), 1 |
| test_anzeige_handy.py | rest | 23 | 23/23/23 | 23, OK, 0 |
| test_anzeige_pc_0632.py | rest | 66 | 66/66/66 | 66, OK, 0 |
| test_anzeige_rfc.py | rest | 4 | 4/4/4 | 4, OK, 0 |
| test_auswertung.py | rest | 15 | 15/15/15 | 15, OK, 0 |
| test_b3_wege.py | rest | 5 | 5/5/5 | 5, OK, 0 |
| test_darstellung.py | rest | 22 | 22/22/22 | 22, OK, 0 |
| test_dashboard.py | rest | 15 | 15/15/15 | 15, OK, 0 |
| test_db_fehler.py | rest | 14 | 14/14/14 | 14, OK, 0 |
| test_doku_0632.py | rest | 29 | 29/29/29 | 29, OK, 0 |
| test_eingabe.py | rest | 22 | 22/22/22 | 22, OK (skipped=2), 0 |
| test_einzelstart.py | rest | 27 | 27/27/27 | 27, OK, 0 |
| test_entlassung.py | rest | 8 | 8/8/8 | 8, OK, 0 |
| test_erfolge_alle_zustaende.py | rest | 1 | 1/1/1 | 1, OK, 0 |
| test_erfolge_beschriftung.py | rest | 5 | 5/5/5 | 5, OK, 0 |
| test_farben.py | rest | 53 | 53/53/53 | 53, OK, 0 |
| test_haenger.py | rest | 21 | 21/21/21 | 21, OK, 0 |
| test_haertung_bau.py | rest | 6 | 6/6/6 | 6, OK (skipped=1), 0 |
| test_handy_0632.py | rest | 35 | 35/35/35 | 35, OK, 0 |
| test_handy_anzeige_0632.py | rest | 16 | 16/16/16 | 16, OK, 0 |
| test_handy_sehr_gross_0632.py | rest | 20 | 20/20/20 | 20, OK, 0 |
| test_inhalte_0631.py | rest | 17 | 17/17/17 | 17, OK, 0 |
| test_inhalte_0632.py | rest | 58 | 58/58/58 | 58, OK, 0 |
| test_ipv6_details.py | rest | 10 | 10/10/10 | 10, OK, 0 |
| test_karte_kontrast.py | rest | 8 | 8/8/8 | 8, OK, 0 |
| test_linux_paket.py | rest | 24 | 24/24/24 | 24, OK, 0 |
| test_namen.py | rest | 18 | 18/18/18 | 18, OK, 0 |
| test_optionen.py | rest | 57 | 57/57/57 | 57, OK, 0 |
| test_optionen_0622.py | rest | 16 | 16/16/16 | 16, OK, 0 |
| test_pillen_pc.py | rest | 8 | 8/8/8 | 8, OK, 0 |
| test_rahmenplan.py | rest | 40 | 40/40/40 | 40, OK, 0 |
| test_rechenweg.py | rest | 37 | 37/37/37 | 37, OK, 0 |
| test_rechner_0632.py | rest | 22 | 22/22/22 | 22, OK, 0 |
| test_rechner_bedarf.py | rest | 6 | 6/6/6 | 6, OK, 0 |
| test_rechner_pc_0632.py | rest | 8 | 8/8/8 | 8, OK, 0 |
| test_rechner_seite_breite.py | rest | 3 | 3/3/3 | 3, FAILED (failures=1), 1 |
| test_rechtliches.py | rest | 30 | 30/30/30 | 30, OK, 0 |
| test_reiter_sichtbar.py | rest | 1 | 1/1/1 | 1, OK, 0 |
| test_restrisiko_3_18.py | rest | 34 | 34/34/34 | 34, OK, 0 |
| test_rundgang_hilfe.py | rest | 29 | 29/29/29 | 29, OK, 0 |
| test_schreibsperre.py | rest | 16 | 16/16/16 | 16, OK, 0 |
| test_sicherung.py | rest | 15 | 15/15/15 | 15, OK, 0 |
| test_sicherung_fehler.py | rest | 21 | 21/21/21 | 21, OK, 0 |
| test_spiel_abgabe.py | rest | 2 | 2/2/2 | 2, OK, 0 |
| test_spiel_doppelt.py | rest | 15 | 15/15/15 | 15, OK, 0 |
| test_subnetz_aufteilen.py | rest | 94 | 94/94/94 | 94, OK, 0 |
| test_subnetz_handy.py | rest | 33 | 33/33/33 | 33, OK, 0 |
| test_subnetz_pc.py | rest | 24 | 24/24/24 | 24, OK, 0 |
| test_subnetz_pc_breite.py | rest | 8 | 8/8/8 | 8, OK, 0 |
| test_systemleiste.py | rest | 6 | 6/6/6 | 6, OK, 0 |
| test_tausenderpunkt.py | rest | 27 | 27/27/27 | 27, OK, 0 |
| test_texte.py | rest | 10 | 10/10/10 | 10, OK, 0 |
| test_trainer_nibble.py | rest | 5 | 5/5/5 | 5, OK, 0 |
| test_trainer_richtig_waere_pc.py | rest | 7 | 7/7/7 | 7, OK, 0 |
| test_umbruch_bindung.py | rest | 8 | 8/8/8 | 8, OK, 0 |
| test_update.py | rest | 23 | 23/23/23 | 23, OK, 0 |
| test_update_download.py | rest | 26 | 26/26/26 | 26, OK, 0 |
| test_update_fenster.py | rest | 10 | 10/10/10 | 10, OK, 0 |
| test_usv.py | rest | 40 | 40/40/40 | 40, OK, 0 |
| test_verstaendlich_0632.py | rest | 23 | 23/23/23 | 23, OK, 0 |
| test_werkzeuge.py | rest | 47 | 47/47/47 | 47, OK, 0 |
| test_zugang.py | rest | 17 | 17/17/17 | 17, OK, 0 |
| test_beenden.py | lang | 11 | 11/11/11 | 11, OK, 0 |
| test_leistung.py | lang | 30 | 30/30/30 | 30, OK (skipped=1), 0 |
| test_grosse_datenmengen.py | lang | kein unittest | - (kein unittest), Schlusszeile 'Belastungstest OK' | -, Belastungstest OK, 0 |
| test_vorladen.py | lang | 27 | 27/27/27 | 27, OK, 0 |
| test_spiel.py | spiel | 384 | 384/384/384 | 384, OK, 0 |
| test_einzelstart.py | windows | 27 (Linux-Loader) | nicht im Container | 27, OK (skipped=1), 0 |
| test_haenger.py | windows | 21 (Linux-Loader) | nicht im Container | 21, OK (skipped=1), 0 |
| test_update.py | windows | 23 (Linux-Loader) | nicht im Container | 23, OK (skipped=5), 0 |
| test_update_fenster.py | windows | 10 (Linux-Loader) | nicht im Container | 10, OK, 0 |
| test_leistung.py | windows | 30 (Linux-Loader) | nicht im Container | 30, OK, 0 |
| test_werkzeuge.py | windows | 47 (Linux-Loader) | nicht im Container | 47, OK, 0 |
| test_optionen.py | windows | 57 (Linux-Loader) | nicht im Container | 57, OK (skipped=2), 0 |
| test_sicherung.py | windows | 15 (Linux-Loader) | nicht im Container | 15, OK, 0 |
| test_beenden.py | windows | 11 (Linux-Loader) | nicht im Container | 11, OK, 0 |
| test_namen.py | windows | 18 (Linux-Loader) | nicht im Container | 18, OK, 0 |
| test_rechtliches.py | windows | 30 (Linux-Loader) | nicht im Container | 30, OK, 0 |
| test_optionen_0622.py | windows | 16 (Linux-Loader) | nicht im Container | 16, OK, 0 |
| test_reiter_sichtbar.py | windows | 1 (Linux-Loader) | nicht im Container | 1, OK, 0 |
| test_abgleich_kern.py | windows | 10 (Linux-Loader) | nicht im Container | 10, OK, 0 |
| test_eingabe.py (Fassung 47eacb0) | ibus (nur Container) | 23 | 23/23/23 | nicht auf GitHub (Teil ibus nur im Container); 8 Container-Läufe je Ran 23, OK |

**Sonderzeilen Rundgang-Datei** (berichtet): Auf `e0f9c7e` lief sie im Audit dreimal vollständig (29/29, Last 7–9; der Abbruch ist zeitabhängig). Mit Kontrollfehler „Frist 0,5 s“: alter Stand 14 von 29 begonnen, keine „Ran“-Zeile, Rückgabe 0, Testlauf meldet „grün“; mit Zählprüfung (Frage 5) Rückgabe 97. Mit dem Fix `0cabd51` und demselben Kontrollfehler: 29/29, OK.

Alle Belege dieser Meldung (gemeinsamer Ordner `bau_0.63.2/`, nicht auf `meldungen`):
- `n14/logs/n14_test_s1_lauf1.log`, `n14/logs/basis_69e62ae_test_s1.log`, `testplaene/Testplan_N14.md`; Sofortmeldung des N14-Bauers (Wortlaut im Auftrag an diesen Entwurf)
- `integration/ci_rest_3b/ergebnis.md` (Zweig `version-0632-fix3b`, `9df7bd8`); Lauf 38475825951
- `gegenpruefung/gp_s1c2_b4b.md` (S1c2 `7a32651`)
- `audit_testzahl/ergebnis.md`, `tabelle.md`, `FG-97_Antrag.md`; `rundgang_abbruch/ergebnis.md` (Fix `0cabd51`)
- `n10/abschluss/ergebnis.md`, `n10/abschluss/b9_diagnose/diagnose.md`, `fg_antrag_fensterziehen.diff`; Läufe 38495894431 (`5c8039c`), 38496133527 (`30f5d8c`)
- `fg96/ergebnis.md` (`4d77439`); Lauf 38495818809
- `n16/ergebnis.md` (`a567b33`), Vorlagen `n16/vorschlag_F31_*.diff`; Lauf 38499632310
- `s6b/m38/ergebnis.md` (Zwischenstand des S6b-Bauers)
- `n9/ergebnis.md` (`3b6a886`)
- `dialog_warntext/Testplan_Dialog.md`
- `s5c/ergebnis_a13_fix.md` (`db45ced`); Lauf 38472532424 (Messzweig `messung-0632-a13`)
- `n15/ergebnis.md`, `n15/aufrufer_push_open.md` (`8cded82`); Lauf 38502657436
- `n11/ergebnis.md` (`b1a0460`); Läufe 38504065435 (Probe), 38506129220
- `gegenpruefung/Gegenpruefung_Meldung_41.md` (Gegenprüfung der Fassung 1)
- `OFFEN_FUER_BERICHT.md`, `integration/PROTOKOLL.md`
- Weisungen: `plan_0.63.2/freigabe/Weisung_CC_Antwort_Meldung_38_und_40.md`, `Weisung_CC_Antwort_Meldung_37.md`, `Weisung_CC_Ablauf_Grossauftraege.md`

## Eingearbeitet aus der Gegenprüfung (Fund → Stelle)
- S-1 (Fensterziehen: Entscheidung (a) steht, Testdatei durch FG-60 gedeckt, B-M-02 (b) bleibt offen) → Frage 6 neu gefasst; keine Option „als geprüft führen“; FG-Nummer nur für den Schleifen-Nachweis (Frage 22).
- M-1 (f2g, 26 Zufallsabläufe fehlen) → Frage 1 „Nicht geprüft“, Empfehlung unter Vorbehalt; Selbstkontrolle; Kopfblock 3.
- M-2 (F20 ist Nicos Entscheidung, Option Verschieben) → Frage 1 Problem und Option (e); Kopfblock 1 und 5.
- M-3 (N14 nicht committet, auf S6b, Abnahme FG-81/92; 4 T-c auch auf N14) → Kopfblock 1, Frage 1 (Stand N14), Frage 9, E1-5.
- M-4 (Ausnahme von F11 (c) und der N5-Auflage; auch „Normal“ 1360) → Frage 3 Einordnung und Option (a).
- M-5 („Stand vor S1c2“ falsch) → Frage 4.
- M-6 (FG-50 deckt die Spiel-Tippflächen) → Frage 13; Frage 12 mit gemeinsamer FG.
- M-7 (D8c als E2) → Frage 23; E1-4 nur noch die vom Bauer als E1 eingestuften Teile.
- M-8 (G1 vermutlich E3, Herkunft) → Frage 15.
- M-9 (FG-Vergabe) → Frage 22 als E2 mit der Tabelle der Gegenprüfung; E1-5 alt gestrichen; Frage 5 ohne feste Nummer.
- L-1 → Kopfblock 1 „(berichtet)“. L-2 → Frage 1 Problem (Bedingung „höchstens etwa die Abweichung“). L-3 → Vergleichsstand genauer benannt (`cad90c0` mit S6c, ohne N14); dass die Sofortmeldung nur als Auftragstext vorliegt, steht in der Selbstkontrolle. L-4 → Frage 3 (a). L-5 → Frage 9. L-6 → Frage 17. L-7 → Zur Kenntnis 8 (N9-F2). L-8 → Zur Kenntnis 7 (IPv4). L-9 → Frage 14 (Handy-Behelf). L-10 → Aufrufer SP1–SP6 / HA3–HA9, Frage 2 ohne „N14-F2“ im Problem. L-11 → Rundgang nur noch in E1-1, N10 nach „Zur Kenntnis“, alte Frage 15 (Fenster-Schließen) als Zur Kenntnis 4, Frage 3 gekürzt.
- Nicht eingearbeitet: L-12 (Frage 1 als eigene Vorab-Meldung) – Entscheidung des Hauptstrangs.
- Zusätzlich aufgenommen (Auftrag Hauptstrang): N11 als Fragen 19–21 und Zur Kenntnis 2.
