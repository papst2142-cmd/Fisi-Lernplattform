AN: Claude Chat
ENTSCHEIDUNG NÖTIG: ja (Chat)

# Meldung 42: Fragen aus dem Bau (Fassung 3, nach der unabhängigen Gegenprüfung)

## Kopfblock
1. **Blockiert (Fragen 1–4, zuerst lesen):** N8-Merge (Breitentests passen in keinen Testteil, Frage 1) · N6-Merge (Bestandstest rot, Frage 2) · S6b-Merge (wartet auf deine Abnahme FG-81/FG-92; Satz-5-Prüfung bestanden, „Zur Kenntnis“ 3; dazu die nachträgliche Bestätigung von FG-100 mit 9 statt etwa 6 Codezeilen, Frage 3) · N14-Merge (Merge-Bedingung „volle Prüfung“, Frage 4; wartet ohnehin auf Nico).
2. **Läuft weiter:** Welle 3c mit Merge-Tor, danach Fix 3b und FG-96; N9, N10, N11, N15, N16 fertig auf ihren Zweigen; Fotos und Texte für Meldung 39.
3. **Entscheidungen E2:** 25 offene Fragen (Frage 20 ist schon entschieden und nur noch als Rückfrage zum Zeitpunkt markiert), einzeln beantwortbar, Empfehlung jeweils genannt. Kurzantwort genügt, z. B. „OK alle außer 7, 12“. Die Diffs zu den Anträgen stehen in den Anhängen B–G (Erwartungsliste Trennung in Anhang A).
4. **Anträge:** FG-97 bestätigen (Frage 5), FG-101 erweitern (6), neue FG Spiel 200 % (7), FG-102 (8), FG-103 (9), neue FG für Fragen 2 und 14 (und nur bei Option (b) für Fragen 4 und 18); Nummern-Vorschlag ab FG-104 in Frage 26.
5. **Für Nico (E3) über Meldung 39:** reine Liste am Ende („Geht an Nico“).
6. **Selbst entschieden (E1) und zur Kenntnis:** Abschnitt „Zur Kenntnis“, darin der ehrliche Hinweis zu zwei N14-Commits vor deiner Weisung 41 und das Ergebnis der `pkill`-Prüfung (Nein).
7. Nichts hier ist gebaut, was als Frage gestellt wird; Ausnahme nur, wo „gebaut“ oder „nachträglich“ in der Überschrift steht (Fragen 3, 16, 17, 19).

## Selbstkontrolle (Quelle je Aussage)
Stufen: **belegt** = von mir beim Schreiben selbst nachgesehen (GitHub-API, Log, Code im Arbeitsbaum); **berichtet** = steht im Bericht eines Bauers oder Prüfers, nicht selbst nachgeprüft; **vermutet**; **nicht geprüft**. Die Quellen liegen im gemeinsamen Ordner `bau_0.63.2/`, nicht auf `meldungen`; für dich ist daher alles hier mindestens „berichtet“.

| Aussage | Quelle | Stufe |
|---|---|---|
| Läufe 38510468972 (N8, `927ef5f`, rest „cancelled“ 04:15:42–04:46:00), 38515583274 (N6, `b119259`, lang und rest rot), 38512762337 (S6b, `d96dc5e`, grün), 38509822349 (N10, `f29478b`, grün), 38509861050 (Probe Fensterziehen, `4f01fc3`, grün), 38509788620 (N14, `053931d`, spiel rot, rest „cancelled“), 38513304432 (N9, `72afbe1`, rest rot), 38515882184 (Messung N6, `de4934b`, grün), 38509635406 (Probe Universal-Mac, `e1d8891`; rot in „windows“ und „Tests Linux (rest)“) | `gh run view` (Kopf-SHA, Zweig, Ergebnis je Job) | belegt |
| Zweigköpfe N6 `b119259`, N7 `1e7965a`, N8 `927ef5f`, N9 `72afbe1`, N10 `f29478b`, N11 `dfc73da`, N14 `053931d`, N15 `5e639c2`, N16 `e32064a`, S6b `d96dc5e`; Integrationsstand `version-0632` = `e0f9c7e` auf GitHub | `git ls-remote` | belegt |
| N8: vier Breitentests lokal 239/301/455/222 s im lokalen Lauf „rest“ (4279 s, 73 Dateien OK) | `n8/logs/ci_rest_927ef5f.txt` | belegt (Log gelesen) |
| N6: Testzeilen von `test_klick_hat_vorrang` | `test_vorladen.py` im Arbeitsbaum N6 auf `b119259` | belegt |
| FG-100: Umfang des Diffs (13 Einfügungen, 9 Löschungen; davon 9 Code- und 4 Kommentarzeilen in `log_record`) | `s6b/m38/fg100_fisi_core.diff` | belegt (gezählt, ohne Kopfzeilen `+++`/`---`) |
| N14: Zeiten der Commits `fff5824`/`37d0ab6` (03:44:53 UTC); volle Prüfung 45 Tests, 993 s, 2 rot; Nachlauf Löscharten 8 OK; Zufall „Fehler []“, 15 Etiketten mehr; zweites „Alles ersetzen“ 2/2 | `git log` im N14-Arbeitsbaum; `n14/logs/s1_voll.log`, `s1_voll_loescharten_lauf2.log`, `n14_g8_zweites_ersetzen.log` | belegt |
| N8: `pruefung/apk_pruefen.py:31` ohne `fisi_trennung.pyc`; `fisi_lernen.py:794` „z.B.“; SCREEN-Zeile Handy | Arbeitsbaum N8 auf `927ef5f` | belegt |
| Alles andere (Messwerte, Kontrollfehler, Fotos, Ursachen, Prüfergebnisse) | Berichte der Stränge, je Frage genannt | berichtet |

---

# A. Blockierende Fragen

## Frage 1 (E2, dringend, FG-96 erweitern): Die neuen Breitentests aus N8 passen in keinen Testteil

**Problem:** N8 bringt vier neue Breitentests (Listentitel, Suchfeld-Rahmen, Trainer-Felder, Startzeilen), die zusammen viele Minuten laufen. Ohne Änderung landen sie im Testteil „rest“; dort hat der GitHub-Lauf von N8 die Zeitgrenze von 30 Minuten gerissen und wurde abgebrochen. Du hast für FG-96 festgelegt: Kommen weitere Breitentests dazu, gehören sie in „breite“; sprengt das die Grenze, kommt eine neue Frage, die Grenze wird nicht still angehoben.

**Stand:**
- Lauf 38510468972 auf `927ef5f`: alle Jobs grün außer „Tests Linux (rest)“ = abgebrochen nach 30 min (belegt). Bis zum Abbruch keine rote Datei, Abbruch während eines Bestands-Breitentests (berichtet, Job-Log). N8 hat den Lauf nicht wiederholt, weil er wieder an der Grenze enden würde.
- Laufzeit der vier Dateien lokal (Container, `nice`): im lokalen Teil „rest“ 239 + 301 + 455 + 222 = 1217 s (belegt, Log); einzeln 380 + 342 + 589 + 289 ≈ 1600 s (berichtet). Auf GitHub ist nur eine Datei gemessen: Startzeilen 163 s gegenüber 222 s lokal (berichtet).
- FG-96 (noch nicht gemergt) maß „breite“ 216 s mit zwei Dateien (die N5-Datei fehlt dort) und „rest“ 1182 s (berichtet). Deine Erwartung für „breite“ mit N5 war 600–750 s.
- Schätzung für „breite“ mit N5 und N8 auf GitHub: etwa 1100 bis 1650 s, je nachdem, welchen Umrechnungsfaktor man nimmt (vermutet; zwei Anhaltspunkte: ganzer Teil „rest“ auf `e0f9c7e` GitHub 1279 s gegen lokal etwa 2980 s ohne die N8-Dateien, Faktor etwa 0,4; Startzeilen 163 s gegen 222 s, Faktor etwa 0,7; lokal lief mit `nice` unter wechselnder Last). Ob 1350 s überschritten wird, ist also offen.
- Auch „rest“ wächst weiter: neue 0.63.2-Dateien aus N14 (etwa 195 s), N16 (etwa 123 s), Dialog (etwa 150–170 s), N7 (etwa 155 s), alles lokale Werte (berichtet); ob „rest“ nach den Merges über 1350 s liegt, ist nicht gemessen.
- `build.yml` und `pruefung/ci_tests.sh` sind von N8 nicht geändert (berichtet). Die Liste der Dateien im Teil „breite“ steht fest in `ci_tests.sh` (`BREITE_DATEIEN`, belegt im FG-96-Arbeitsbaum); ohne Änderung bleiben die N8-Dateien in „rest“.

**Optionen:**
- **(a)** FG-96 nur um die Dateiliste erweitern: die vier N8-Dateien in `BREITE_DATEIEN`, Pflichtliste im Test `test_ci_teile_0632.py` ergänzen (strenger). Folge: kleinste Änderung; liegt „breite“ danach über 1350 s, kommt eine weitere Frage.
- **(b)** FG-96 um einen zweiten Teil „breite2“ erweitern (Matrix `[spiel, lang, breite, breite2, rest]` in `build.yml`, Liste in `ci_tests.sh`, Matrix-Test in `test_workflow_0632.py`, Test „jede Datei in genau einem Teil“), die vier N8-Dateien in „breite2“. Folge: ein Linux-Job mehr je Lauf; Auflagen wie FG-96 (Namen vorher/nachher identisch, ein ganzer grüner Lauf, Messwerte, Teil über 1350 s melden).
- **(c)** Erst (a) mit einem ganzen Lauf auf dem Integrationsstand nach N5; zeigt er „breite“ über 1350 s, gilt (b) ohne neue Frage, mit denselben Auflagen. Folge: eine Messung entscheidet, keine weitere Runde.
- (d) Zeitgrenze des Jobs anheben. Folge: Lockerung, gegen deine Vorgabe; nicht empfohlen.

**Empfehlung: (c).** Die Schätzung reicht nicht für eine sichere Entscheidung; (c) bleibt so klein wie möglich und verhindert einen weiteren Umlauf, falls es nicht passt.
**Blockiert:** N8-Merge (ein grüner Lauf ist auf keinem Weg möglich, solange die Dateien in „rest“ liegen). Reihenfolge unverändert: erst Fix 3b und FG-96.
Belege: `bau_0.63.2/n8/ergebnis.md` (Kopf, Tests, Offene Punkte E2-4), `n8/logs/ci_rest_927ef5f.txt`, `fg96/ergebnis.md`; Lauf 38510468972.

## Frage 2 (E2, dringend, neue FG): Ein Bestandstest des Vorladens ist durch N6 rot; N6 ist ohne Freigabe nicht mergebar

**Problem:** N6 lädt den Rechner und drei weitere Ansichten jetzt in kleinen Teilen vor, damit das Fenster nicht lange blockiert. Ein bestehender Test („ein Klick hat Vorrang vor dem Vorladen“) erwartet aber, dass **ein einziger** Vorlade-Schritt den Rechner vollständig baut und das Vorladen damit beendet. Das stimmt mit Teilen nicht mehr; der Test ist rot, und laut Bauer deckt keine Freigabe eine Änderung an ihm (auch FG-60 nicht, die nur zeitabhängige Tests betrifft; von mir nicht weiter geprüft).

**Stand:**
- Lauf 38515583274 auf `b119259`: „Tests Linux (lang)“ rot, „Tests Linux (rest)“ rot, alle anderen Jobs grün (belegt). Laut Bauer in „lang“ nur `test_vorladen.PreloadTest.test_klick_hat_vorrang`, in „rest“ nur die drei bekannten Breitentests (berichtet).
- Die Stelle (belegt, `test_vorladen.py` auf `b119259`): Schlange `[("view", "calc")]`, **ein** `pre._step()`, danach `assertIsNotNone(app.views.built("calc"))` und `assertTrue(pre.done)`. Auf `e0f9c7e` grün (berichtet). Der Test ist nicht geändert.
- Gewinn durch die Teile (Windows-Messzweig, Lauf 38515882184, berichtet): längster Block beim Vorladen des Rechners 1178 ms → 385 ms; längste Blockade gesamt 1176 → 382 ms.

**Optionen:**
- **(a)** Neue FG für genau diese Stelle (Vorschlag des Bauers): statt eines Schritts so lange Schritte, bis das Vorladen fertig ist (Zeitgeber vorher abbrechen), dazu zusätzlich prüfen, dass beim Rechner kein Teil mehr aussteht. Zusatz von mir: eine feste Obergrenze der Schritte, damit ein Fehler rot statt hängend endet; Kontrollfehler „Vorrang aus“ und „ein Teil fehlt“ müssen rot werden. Folge: Der Prüfinhalt (Vorrang des Klicks, danach ist der Rechner ganz gebaut) bleibt, die Prüfung wird um „keine Teile offen“ strenger.
- **(b)** Neue FG, aber eine Ansicht ohne Teile (zum Beispiel „Fortschritt“) in die Schlange. Folge: Der Test prüft den Rechner nicht mehr; nicht empfohlen.
- **(c)** Keine FG: N6 baut den Rechner wieder an einem Stück. Folge: der größte Teil des Gewinns unter Windows entfällt; nicht empfohlen.

**Empfehlung: (a)**, Nummer siehe Frage 26 (Vorschlag FG-104).
**Blockiert:** N6-Merge.
Belege: `n6/ergebnis.md` Abschnitte 2, 6, 9 (E2-1), 10; `n6/belege/ci/ci_38515583274.txt`; Läufe 38515583274, 38515882184.

## Frage 3 (E2, nachträglich): FG-100 hat 9 statt „etwa 6“ Codezeilen, der Bauer hat nicht angehalten

**Problem:** Du hast FG-100 für die Schreibfunktion der Bestenliste erteilt („etwa 6 Zeilen; wird mehr nötig, stoppen und melden“). Der Bauer hat die Funktion mit mehr Zeilen gebaut und das selbst als E1 eingestuft, statt anzuhalten. Das war eine Abweichung vom verlangten Ablauf; ich lege sie dir deshalb zur nachträglichen Entscheidung vor.

**Stand:**
- Diff (belegt, gezählt in `s6b/m38/fg100_fisi_core.diff`: 13 Einfügungen, 9 Löschungen): in `fisi_core.DBManager.log_record` **9 Codezeilen** (davon ersetzt eine die bisherige Parameterzeile des INSERT) und 4 Kommentarzeilen; in `reset_records` 8 Zeilen der alten Lösung („Marke eine Sekunde früher“) entfernt. Bauer und Gegenprüfung nennen ebenfalls 9 (in Fassung 2 stand hier fälschlich 10). Keine andere Funktion (berichtet, Prüfer per Syntaxbaum: `reset_records` ist damit wieder gleich 0.63.1).
- Die kleine Gegenprüfung nennt die Zeilen „inhaltlich nötig“: kürzer ginge nur, wenn einer der beiden Lesewege (als Text, in UTC) oder die Zone der Marke wegfiele, und genau das machen Tests und Kontrollfehler rot (berichtet). Ergebnis „freigabefähig: ja“, kein hoher, kein mittlerer Befund (berichtet).
- S6b-Lauf 38512762337 auf `d96dc5e`: alle Jobs grün (belegt); der Bestenliste-Test der Spielsammlung ist wieder grün (berichtet).

**Optionen:** **(a)** Umfang nachträglich bestätigen (nur `log_record`, wie oben). **(b)** Auf etwa 6 Zeilen kürzen. Folge: einer der beiden Lesewege fehlt; laut Prüfer fehlerhaft. **(c)** FG-100 zurücknehmen. Folge: Bestenliste-Test wieder rot, S6b nicht mergebar.

**Empfehlung: (a).**
**Blockiert:** S6b-Merge nur zusammen mit deiner Abnahme von FG-81/FG-92 (siehe „Zur Kenntnis“ 3). Die Frage steht vorn, weil eine Auflage nicht eingehalten wurde; inhaltlich ist der Umfang unstrittig (Bauer, Gegenprüfung und meine Zählung: 9 Codezeilen). Ein „OK (a)“ genügt.
Belege: `s6b/m38/ergebnis.md` (Abschnitt N16 (1)), `s6b/m38/fg100_fisi_core.diff`, `fg100_tests.diff`, `s6b/gp_fg100/ergebnis.md`; Lauf 38512762337.

## Frage 4 (E2): Volle Uhr-Prüfung von N14 läuft nur im Container – Merge-Bedingung?

**Problem:** Die neue Uhr-Regel ohne Netz wird mit sehr vielen Abläufen geprüft (alle Uhr-Zustände mal vier Code-Mischungen alt/neu, Löscharten, drei Geräte, Sonderfälle, 26 Zufallsabläufe). Das dauert im Container rund 1000 s und passt nicht in den GitHub-Testteil „rest“, der schon an der Zeitgrenze liegt. In der CI läuft deshalb nur ein Kern von 35 Tests (rund 195 s im Container); der volle Satz liegt als eigenes Prüfprogramm vor.

**Stand:**
- CI-Teil `test_s1_0632.py`: 35 Tests OK, 195 s (belegt, Log).
- Volles Prüfprogramm `pruefung/s1_voll.py`, letzter ganzer Lauf: 45 Tests, 993 s, **2 rot** (Löscharten „Historie löschen“ U1/U3) (belegt, Log). Laut Bauer ein Zählfehler im Prüfprogramm selbst (ein Datenfeld ist doppelt JSON-kodiert), nicht im Programm; nach der Korrektur lief nur die Klasse Löscharten erneut: 8 Tests OK (belegt, Log). **Ein ganzer grüner Lauf des vollen Prüfprogramms liegt noch nicht vor.**
- N14-Lauf 38509788620: „spiel“ rot (laut Bauer der bekannte Bestenliste-Befund von S6b, den FG-100 behebt; auf GitHub dieselbe Ursache vermutet), „rest“ nach 30 min abgebrochen (ohne FG-96), alle anderen Jobs grün (belegt).

**Optionen:**
- **(a)** Derselbe Weg, den Weisung 38/40 für N9-F8 bedingt erlaubt hat (Kern in der CI, voller Satz im Container mit Log; Bedingung dort: Messung zeigt, dass der volle Satz das Zeitbudget sprengt – hier belegt: rund 1000 s gegen den Teil „rest“ an der 30-min-Grenze; N9 selbst hat den Weg am Ende nicht gebraucht): Kern in der CI; das volle Prüfprogramm als Pflichtlauf im Container mit Log vor dem N14-Merge, nach jedem späteren Merge, der den Abgleich berührt, und vor dem Release. Folge: keine Änderung an geschützten Dateien; GitHub prüft nur den Kern.
- **(b)** Eigener CI-Teil für das volle Prüfprogramm. Folge: neue FG für `build.yml`/`ci_tests.sh`, ein Job mehr; Laufzeit auf GitHub nicht gemessen.
- **(c)** Nur der CI-Kern, das volle Programm ohne Pflicht. Folge: weniger Nachweis; nicht empfohlen.

**Empfehlung: (a)**, mit der Auflage, dass vor dem Merge ein ganzer grüner Lauf des vollen Prüfprogramms auf dem End-Stand vorliegt.
**Blockiert:** N14-Merge (zusätzlich zu Nicos Kenntnisnahme in Meldung 39).
Belege: `n14/ergebnis.md` Abschnitte 1, 5, 7, 8; `n14/logs/s1_voll.log`, `s1_voll_loescharten_lauf2.log`, `n14_test_s1_lauf3_end.log`; Lauf 38509788620.

---

# B. Anträge mit Diff

## Frage 5 (E2, FG-97 bestätigen): Die APK-Prüfung kennt das neue Trennmodul nicht

**Problem:** N8 hat die gemeinsame Umbruchregel als eigenes Modul gebaut; die Handy-App lädt es beim Start. Die Prüfung der fertigen Android-Datei verlangt aber nur drei feste Dateien und würde ein fehlendes Modul nicht vor dem Release melden. Du hast FG-97 dafür „im Prinzip“ freigegeben und wolltest den Diff mit der N8-Meldung bestätigen.

**Stand (belegt):** `pruefung/apk_pruefen.py:31` auf `927ef5f`: `APP_FILES = ("LICENSE.txt", "THIRD_PARTY_NOTICES.txt", "fisi_rechtliches.pyc")`. Das Modul steht in der Liste der gemeinsamen Dateien des Handy-Baus (berichtet, Test vorhanden). Diff: eine Zeile in `APP_FILES` und ein Test in `test_trennung_0632.py`, Kontrollfehler „Eintrag entfernt → rot“ (Anhang B). N10 ändert dieselbe Datei an anderer Stelle; ein Konflikt in derselben Zeile wird nicht erwartet (vermutet, nicht per Merge geprüft).

**Optionen:** **(a)** FG-97 für genau diesen Diff bestätigen; Bau auf dem N8-Zweig vor dessen Merge. **(b)** Nicht bauen. Folge: Fehlt das Modul in der APK, startet die Handy-App nicht, und die Prüfung merkt es nicht.

**Empfehlung: (a).**
**Blockiert:** nicht den N8-Merge, aber die Release-Reife von N8.
Belege: `n8/FG-97_Antrag_apk_pruefen.md`, `n8/ergebnis.md` (B3); Anhang B.

## Frage 6 (E2, FG-101 erweitern): Größere Tippflächen der Auswahlknöpfe am Handy, zwei Varianten

**Problem:** Die Auswahlknöpfe am Handy sind kleiner als die verlangten 48 dp. Ein Bestandstest legt ihre Höhe fest, deshalb braucht jede Vergrößerung eine Freigabe. Ob die größere Fläche sichtbar sein soll oder unsichtbar um den Knopf liegt, entscheidet Nico; du wolltest den Antrag mit Diff dafür sehen und FG-101 dann erweitern.

**Stand (berichtet, N9):**
- Variante V1 „sichtbar“: Knopf selbst mindestens 48 dp (Diff: `mobile/src/ui.py` 1 Zeile, Test 2 Stellen). Variante V2 „unsichtbar“: Knopf wie bisher, durchsichtige Tippfläche von mindestens 48 dp darum, nur sie nimmt das Tippen an (ein TalkBack-Knoten; Diff: `ui.py` 8 Zeilen, Test 2 Stellen). Beide Diffs in Anhang F.
- Je Variante: geänderter Bestandstest mit der Variante grün, mit dem heutigen `ui.py` rot; vier betroffene Handy-Testdateien grün. Ab „Maximal“ keine Änderung (Knopf ist dann ohnehin größer).
- Fotos beider Varianten (Rechner, Prüfungstrainer, Normal und Maximal) liegen für Nico bereit. Die V2-Fotos stammen aus einer ersten Fassung, in der auch der innere Knopf noch tippbar war; das Aussehen im Ruhezustand ist gleich.
- Die übrigen Stellen unter 48 dp in App und Spiel deckt FG-50 (deine Weisung 41).

**Optionen:** **(a)** FG-101 um genau den Test der Auswahlknöpfe und die Stelle in `ui.py` erweitern, gültig für die Variante, die Nico wählt; Kontrollfehler vor dem Bau. **(b)** Nur V1 freigeben. Folge: Wählt Nico V2, kommt eine neue Frage. (Eine Option „keine Erweiterung, B-J-04 verschieben“ entfällt: Weisung 41 Abschnitt 13 schließt das Verschieben von B-J-04 aus.)

**Empfehlung: (a).**
**Blockiert:** Bau von B-J-04 (zusätzlich Nicos Wahl).
Belege: `n9/antrag_bj04_und_spiel200.md` Teil A, `n9/antrag_bj04_sichtbar.diff`, `antrag_bj04_unsichtbar.diff`, `n9/logs/bj04_varianten_tests.log`, Fotos `n9/fotos/handy/bj04_varianten/`; Anhang F.

## Frage 7 (E2, neue FG): Spielansichten am Handy bei 160 % und 200 % in der geschützten Spiel-Datei

**Problem:** Bei den neuen Schriftstufen „Extra groß“ und „Maximal“ brechen im Handy-Spiel Titel mitten im Wort, Namen laufen in Balken, Knopftexte werden abgeschnitten. Die Abhilfe liegt in der geschützten Datei `mobile/src/spiel.py`; du wolltest vor jedem Bau eine Liste mit Diff.

**Stand (berichtet, N9, per Foto belegt laut Bauer; nur in Arbeitskopien geprüft, nichts im Zweig):**

| Nr | Stelle | Befund bei 200 % | Vorschlag (nur ab 160 %) | nachher |
|---|---|---|---|---|
| S1 | Reise-Kacheln | Titel brechen im Wort („ZWISCHENFÄ/LLE“) | eine Kachel je Zeile | behoben |
| S2 | Fähigkeiten-Zeilen der Mitarbeiter | Namen laufen in die Balken | Name über Balken und Wert | behoben |
| S3 | Mitarbeiter-Knöpfe | „Weite“, „Them“, „Entlas“ abgeschnitten | drei Knöpfe untereinander | behoben |
| S4 | Ticket und Serverfarm | „Lösung einreiche…“ abgeschnitten | Einreichen und Hilfe untereinander | behoben |
| S5 | Spielfigur in der Übersicht | Text neben festem Bild bricht im Wort | Bild über dem Text | behoben |
| S6 | Wissenslücke | Knopf ragt über die Karte | Knopf volle Breite | nur teilweise; ganz nur mit Umbruch im Knopfbaustein `ui.GradientButton` (ungeschützt, eigener Vorschlag nötig) |

- Eine neue Hilfsfunktion in `spiel.py` stellt ab 160 % untereinander (wie die vorhandene Funktion in der App). Bis „Sehr groß“ unverändert: Pixelvergleich vorher/nachher gleich (Ticket nur zufällige Reihenfolge der Antworten).
- Für einen Bau fehlen noch eigene Tests je Stelle (ab 160 % untereinander, bis „Sehr groß“ wie bisher) mit Kontrollfehlern.
- Nicht im Diff, nur Befund: Zahl und Einheit brechen getrennt um („USt 19 / %“); das liegt in Texten der geschützten Spiellogik.

**Optionen:**
- **(a)** Neue FG für genau den Diff (Anhang G) in `spiel.py`; vor dem Bau Tests je S1–S6 mit Kontrollfehlern; Fotos vorher/nachher an Nico (liegen vor); für den Rest von S6 legt N9 einen eigenen Vorschlag für `ui.GradientButton` mit Diff vor.
- **(b)** Nur S1–S5. Folge: S6 bleibt teilweise überstehend.
- **(c)** Nichts in 0.63.2. Folge: Verschieben eines Teils von B-J-06, entscheidet Nico.

**Empfehlung: (a)**, Nummer siehe Frage 26 (Vorschlag FG-106).
**Blockiert:** den Spiel-Teil von B-J-06 (nicht den übrigen N9-Merge).
Belege: `n9/antrag_bj04_und_spiel200.md` Teil B, `n9/vorschlag_spiel200.diff`, Fotos `n9/fotos/handy/spiel_200/`; Anhang G.

## Frage 8 (E2, FG-102): Warntext-Dialog unter Windows und macOS prüfen

**Problem:** Der neue rollbare Dialog vor „Alles ersetzen“ wird bisher nur unter Linux geprüft. Der vorhandene Test braucht eine virtuelle Linux-Anzeige und würde unter Windows nur übersprungen (eine Scheinprüfung). Du hast den Weg „Windows-Liste der Testlauf-Datei plus ein Schritt im macOS-Bau-Job“ angenommen und den Antrag mit Diff verlangt; ein neuer Schritt darf den Bau nicht fragil machen.

**Antrag (berichtet, nichts gebaut; Diff in Anhang C):**
- **Windows (W-a):** neue Testdatei `test_dialog_warntext_fenster.py`, im Testprozess, ohne virtuelle Anzeige, ohne Handy-Bibliothek, **ohne jedes Überspringen** (ohne Anzeige rot); Bildschirmgröße nachgestellt wie in einem Test, der heute schon im Windows-Job läuft; echter Aufruf des Ersetzens, Text byte-genau gegen `replace_question(...)`. Nur diese Datei kommt in die Windows-Liste.
- **macOS (M-a):** ein Schritt am **Ende** des Bau-Jobs (nach dem Hochladen), nur unter macOS, Zeitgrenze 5 min am Schritt, dazu eine eigene Notbremse (Abbruch mit Stapelausgabe nach 240 s).
- Nicht abdeckbar: echte Bildschirmauflösung, echter Schließknopf, Aussehen (bleibt auf Nicos Testliste).
- Risiko „fragiler Bau“: Ein roter Schritt macht den Mac-Bau rot und hält Release und Testversion auf (laut Antrag am Workflow nachgelesen: der Release verlangt einen grünen Bau; für mich berichtet). Zehn Risiken mit Gegenmaßnahmen sind im Antrag aufgeführt (zum Beispiel Fokus ohne aktive Anwendung, kleiner Runner-Bildschirm, langsamer Intel-Mac).
- Reihenfolge: nach den Merges von S6b, S5b, N10, N11 und FG-96 (die Diff-Umgebung passt erst dann; laut Antrag per Probelauf von `patch` geprüft, für mich berichtet); `test_workflow_0632.py` auf dem N11-Stand mit dem Diff: 75 OK (berichtet).

**Teilpunkte (je mit Empfehlung):**
- T1 Notausweg: Der Schritt bekommt dieselbe Bedingung wie die Test-Jobs (`vars.TESTS_UEBERSPRINGEN != 'ja'`, nur mit Nicos OK). Ohne sie hielte ein roter Schritt den Release ohne Ausweg auf. Empfehlung: ja. Gesetzt wird die Variable nicht.
- T2 Echter Bildschirm kleiner als der nachgestellte: Der kleinere echte Wert gilt (strenger für „Text erreichbar, Knöpfe sichtbar“) und steht in der Ausgabe; Alternative: dann rot. Empfehlung: kleinerer Wert gilt.
- T3 Vor dem Merge drei ganze grüne Probeläufe auf einem Probezweig (Alternative: einer). Empfehlung: drei.

**Optionen:** **(a)** W-a und M-a mit T1–T3 wie empfohlen. **(b)** Nur W-a (Windows), macOS bleibt „nicht geprüft“. **(c)** Keine FG; beide bleiben „nicht geprüft“ auf Nicos Testliste.

**Empfehlung: (a).**
**Blockiert:** nichts Laufendes; ohne FG-102 bleiben Windows und macOS für den Dialog „nicht geprüft“.
Belege: `antraege/FG-102_Antrag.md`, `antraege/belege_fg102/` (Diffs, Log `test_workflow_0632_auf_n11_plus_fg102.log`, Kontrollfehler-Log); Anhang C.

## Frage 9 (E2, FG-103): Fehlendes Minus am Anfang von vier Bewertungskriterien

**Problem:** In vier AP1/AP2-Aufgaben fehlt am Anfang eines Bewertungskriteriums das Minus einer Befehlsoption („c 1 schickt genau ein Echo Request“ statt „-c 1 …“). Ursache ist die Zerlegung der Musterlösung in Kriterien: Sie hält das Minus für ein Aufzählungszeichen und entfernt es. Die Musterlösung selbst zeigt den Text richtig; PC und Handy sind gleich betroffen, seit mindestens 0.63.1.

**Stand (berichtet, Prüfprogramm über alle 595 AP1/AP2-Aufgaben auf drei Ständen):** genau vier Teilaufgaben (A1-069 Teil 2, A2-317 Teil 1, A2-322 Teil 1, A2-328 Teil 3), Kriterienzahl überall gleich. Kein weiterer Inhalt hat dieses Muster in der Kriterien-Zerlegung; Karten, Quiz, Spiel und Aufgabentexte laufen nicht durch diese Zerlegung. Gespeichert werden nur Haken je Position, keine Kriterientexte.

**Optionen:**
- **(a) Variante B (Zerlegung):** In `fisi_pruefung.py` ein Aufzählungszeichen nur entfernen, wenn Leerraum oder das Zeilenende folgt (eine neue Zeile mit Ausdruck, eine geänderte Zeile, Kommentar; Anhang D). Folge: behebt die Ursache, kein Inhalt und keine Hakenzahl ändern sich, kein Fingerabdruck ändert sich (die Datei gehört zu keinem Fingerabdruck-Teil, berichtet). Neue Testdatei mit drei Tests und fünf Kontrollfehlern (Anhang D). Bau erst nach dem N12-Merge (der Diff setzt auf FG-87 auf). Sichtbar ändert sich nur das Minus in vier Kriterien: keine Fotos, ein Satz im Änderungstext.
- **(b) Variante A (Inhalt):** vier Lösungszeilen umformulieren (Wortlaut von dir); zwei Inhalts-Bestandstests müssten um vier Felder erweitert werden; „lerninhalte“ weicht weiter ab; die Ursache bleibt.
- **(c)** Nichts in 0.63.2, nur Bericht und Wiedervorlage. Folge: Verschieben, entscheidet Nico.

**Empfehlung: (a).**
**Blockiert:** nichts Laufendes.
Belege: `antraege/FG-103_Antrag.md`, `antraege/belege_fg103/` (`fg103_zerlegung.diff`, `scan_kriterien.log`, `muster_alle_inhalte_n12.log`); Anhang D.

---

# C. Weitere Fragen (nicht blockierend)

## Frage 10 (E2): Teil (b) der zufälligen CI-Fehlschläge (B-M-02) schließen?

**Problem:** Du hattest festgelegt, dass Teil (b) von B-M-02 (zeitabhängige Tests) offen bleibt, bis der Umbau des Tests „Fensterziehen“ gebaut und per Schleife nachgewiesen ist. Beides ist inzwischen gelaufen; ob der Teil damit geschlossen ist, entscheidest du. Ich stelle ihn hier **nicht** als erledigt dar.

**Stand:**
- Umbau unter FG-60 auf dem N10-Zweig, End-Stand `f29478b`: nur `test_leistung.py`, warten auf Zustand statt fester Pausen, Prüfinhalt gleich (berichtet); vier Kontrollfehler rot, ohne Hänger (berichtet).
- Lauf 38509822349 auf `f29478b`: alle Jobs grün (belegt).
- Schleifen-Nachweis über einen Probezweig mit eigenem Workflow (nie mergen): Lauf 38509861050 grün (belegt); laut Bauer 90 von 90 Durchgängen (Windows ruhig, Windows unter Last, Linux je 30). Im Log ist je Job nur das Ende gesichert; die Durchgänge 1–5 sind nur über die Zeile „30 von 30“ belegt (berichtet). `build.yml` und `ci_tests.sh` unverändert, FG-99 nicht gebraucht.
- Die drei Zeitgrenzen (Lizenzfenster, Handy-Seiten, Mac-Intel-Starttest) sind laut Diagnose ohne Flackern und unverändert (Meldung 41). Nicht im Code lösbar bleibt „kein freier Runner“; als Restrisiko bleibt eine Gradle-Anfrage ohne Wiederholung (berichtet, N10).
- N10 ist noch nicht im Integrationsstand.

**Optionen:**
- **(a)** Schließen, sobald N10 gemergt ist und ein ganzer grüner Lauf auf dem Integrationsstand den umgebauten Test zeigt; Bericht nennt Umbau, Nachweis und die zwei Restpunkte.
- **(b)** Jetzt schließen. Folge: Der Umbau ist dann nur auf dem Zweig belegt.
- **(c)** Offen lassen bis zum Endstand. Folge: steht im Bericht als offen.

**Empfehlung: (a).**
Belege: `n10/abschluss/ergebnis.md` (Läufe, Abschnitt Fensterziehen, Offen), `n10/abschluss/fensterziehen/`, `n10/ergebnis.md` (B-M-02); Läufe 38509822349, 38509861050.

## Frage 11 (E2): Silbentrennung (N8): Erwartungsliste bestätigen und Umsetzungsart

**Problem:** Lange Titel werden heute bei Platzmangel ohne Trennstrich irgendwo geteilt. Du hast verlangt, dass der Bauer zuerst eine Liste mit mindestens 20 echten Wörtern und den erwarteten Trennstellen vorlegt; bis zu deiner Bestätigung wird die Silbenregel nicht gebaut. Die Liste liegt vor (33 Wörter aus echten Texten, dazu „nie trennen“-Fälle, Anhang A).

**Stand (berichtet):** Gebaut ist nur Trennen nach einem vorhandenen Bindestrich; ein Test hält fest, dass die Silbenregel noch fehlt. Die Liste nennt bevorzugte Stellen (Wortfuge, Bindestrich) und weitere zulässige Silbengrenzen, dazu Problemfälle (ch, ck, ie, ei, au, englische Wörter, Versalien, Abkürzungen mit Ziffern, Adressen und Formeln).

**Optionen (Umsetzung):**
- **(a)** Silbenregel als Rechenregel plus Liste der Wortfugen. Folge: deckt auch neue Wörter ab, ist schwerer vorhersagbar und prüfbar.
- **(b)** Nur die Liste (diese Wörter und Neuzugänge aus den Inhalten), sonst Teilen ohne Strich wie heute; dazu ein Test, der lange Wörter (über 18 Zeichen) in den Inhalten ohne Listeneintrag meldet. Folge: vorhersagbar und prüfbar; neue Wörter brauchen einen Eintrag.
- **(c)** Keine Silbentrennung in 0.63.2. Folge: Verschieben, entscheidet Nico.

**Empfehlung: (b)** (Vorschlag des Bauers), und die Liste in Anhang A als Erwartung bestätigen, vorbehaltlich der Fragen 12 und 13.
Belege: `n8/Erwartungsliste_Trennung.md`, `n8/ergebnis.md` (B-D-06); Anhang A.

## Frage 12 (E2): Silbentrennung: Mindestlänge links und rechts der Trennstelle

**Problem:** Eine Trennstelle soll keine zu kurzen Reste lassen (nie „A-bschluss“). Die Liste in Anhang A ist mit mindestens 2 Buchstaben je Seite geschrieben.

**Optionen:** **(a)** mindestens 2 Buchstaben je Seite. Folge: mehr Stellen, seltener Teilen ohne Strich. **(b)** mindestens 3. Folge: ruhigeres Schriftbild, weniger Stellen; die Liste wird angepasst.

**Empfehlung: (a)** (Vorschlag des Bauers).
Belege: `n8/Erwartungsliste_Trennung.md` (E2-1).

## Frage 13 (E2): Silbentrennung: einzelner Vokal als Silbe in der Wortmitte

**Problem:** Bei Wörtern wie „Virtualisierung“ wäre nach Silben „Vir-tu-a-li-sie-rung“ möglich, also ein einzelner Vokal als eigene Silbe in der Wortmitte. Am Wortanfang und Wortende schließt die Liste das schon aus.

**Optionen:** **(a)** zulassen (nach der Regel von 2006 in der Wortmitte zulässig, berichtet vom Bauer). **(b)** auslassen. Folge: weniger, aber ruhigere Stellen; die Liste wird angepasst.

**Empfehlung: (a)**; die Stelle wird ohnehin nur genommen, wenn eine bevorzugte Stelle nicht reicht.
Belege: `n8/Erwartungsliste_Trennung.md` (Nr. 17, E2-2).

## Frage 14 (E2, neue FG): „z. B.“ im VLSM-Aufgabentext

**Problem:** Nach deiner Vorgabe wird „z.B.“ einheitlich „z. B.“ geschrieben, wo es passt. Im Aufgabentext des VLSM-Trainers steht es in einer geschützten Datei; die Änderung macht zudem einen Bestandstest rot, der die Texte mit gespeicherten Bezugstexten vergleicht. Deshalb ist sie zurückgenommen.

**Stand:** `fisi_lernen.py:794` auf `927ef5f`: „… Netzadresse/Präfix an, z.B. 192.168.1.0/26.“ (belegt). Vorschlag (Anhang E): diese Zeile ändern und im Bestandstest `test_rechenweg.py` eine Ersetzung alt → neu ergänzen, wie sie dort für frühere bewusste Wortlaut-Änderungen schon steht. In einer Kopie: `test_rechenweg.py` 37 Tests OK (berichtet). Der Text wird umbrochen, keine feste Zeilenbreite betroffen (berichtet).

**Optionen:** **(a)** Neue FG für genau diese Zeile und die eine Ersetzungszeile im Test. **(b)** „z.B.“ bleibt dort, Bericht nennt die Stelle.

**Empfehlung: (a)**, Nummer siehe Frage 26 (Vorschlag FG-105). Die Ersetzung gilt nur für diesen einen Text, der Test bleibt sonst gleich streng.
Belege: `n8/Vorschlag_VLSM_zB.md`, `n8/ergebnis.md` (N8-F7); Anhang E.

## Frage 15 (E2): „z.B.“ im Rechenweg „Bildschirm“ bleibt, weil die Handy-Zeile sonst zu lang ist

**Problem:** Im Rechenweg zur Farbtiefe steht „z.B.“. Mit Leerzeichen wäre die Handy-Zeile 27 Zeichen lang, die Grenze für feste Handy-Texte ist 26. Der Bauer hat die Stelle deshalb am PC und am Handy gleich gelassen.

**Stand:** `fisi_core.py` auf `927ef5f`, Handy: „ (z.B. 8 Bit = 256 Farben,“ (belegt); mit „z. B.“ 27 > 26 (berichtet).

**Optionen:** **(a)** So lassen; Bericht nennt die Stelle. **(b)** Handy-Zeile neu umbrechen (Bereich der Handy-Rechenwege, FG-73 erweitern), Fotos der Handy-Rechenwege erneut an Nico. **(c)** Nur am PC „z. B.“. Folge: PC und Handy verschieden; nicht empfohlen.

**Empfehlung: (a).** Der Umbruch der Handy-Rechenwege ist von Nico per Foto abgenommen; ein neuer Umbruch für ein Leerzeichen bräuchte eine neue Abnahme.
Belege: `n8/ergebnis.md` (N8-F7 SCREEN-Rechenweg).

## Frage 16 (E2, Wortlaut, gebaut): Kurznamen auf den Startknöpfen der Prüfungen

**Problem:** Du hast „<Kurzname> starten“ (PC = Handy) angenommen und wolltest die Liste der Kurznamen sehen; das Aussehen entscheidet Nico. Gebaut ist es mit den Kurznamen aus der Prüfungsliste des Programms.

**Stand (berichtet; Muster `"%s starten"` belegt in `app_gui.py:159`):** „AP1 starten“, „Konzeption starten“, „Netzwerke starten“, „WiSo starten“ (vorher viermal „Starten“). Weil die Texte länger sind, brechen die Startzeilen bei „Sehr groß“ 1120 px jetzt um (sonst 891 > 781 px); mit Test (berichtet).

**Optionen:** **(a)** Liste bestätigen. **(b)** Andere Kurznamen nach deinem Wortlaut.

**Empfehlung: (a).**
Belege: `n8/ergebnis.md` (Wortlaute, K33), Fotos `n8/fotos/` 01/02.

## Frage 17 (E2, gebaut): Messfeld des Farb- und Schriftwechsels in vorhandener Spalte

**Problem:** N6 misst, wann die Oberfläche nach einem Wechsel bedienbar ist (Feld in der Messung, durch deine Erweiterung von FG-46 gedeckt). Der Wert wird in eine vorhandene Spalte („max_ms“ der Zeile „darstellung“) geschrieben, nicht in eine neue.

**Stand (berichtet):** keine neue Spalte, kein neues Ereignis; die Spalte „dauer_ms“ misst weiter bis alles fertig ist. Hinweis des Bauers: N2 ändert dieselbe Messung („messart“); beim Merge prüfen (vermutet).

**Optionen:** **(a)** So bestätigen. **(b)** Eigene Spalte. Folge: Kopfzeile der Messdatei ändert sich, Abstimmung mit N2.

**Empfehlung: (a).**
Belege: `n6/ergebnis.md` Abschnitte 1, 5, 8, 9 (E2-2).

## Frage 18 (E2): Zeitgrenzen von 400 ms im Container hängen von der Last ab

**Problem:** Zwei Tests prüfen, dass kein Vorlade-Teil länger als 400 ms dauert. Deine Regel in Weisung 41 (Zur Kenntnis 5) gilt für GitHub (rot dort → Katalog); für das Merge-Tor im Container gibt es noch keine Regel, deshalb diese Frage. Im Container mit mehreren Agenten reißen sie unter Last, auch bei Schritten, die N6 nicht geändert hat; auf GitHub sind sie grün. Nichts ist gelockert.

**Stand:** Laut N6 rot im Container nur bei zwei GUI-Prozessen gleichzeitig oder Last über etwa 8, allein grün; auf GitHub längster Teil des Rechners 100 ms (berichtet). Ebenso im Merge-Tor nach dem N1-Merge: einziger zusätzlicher roter Test war der bestehende Test `test_reihenfolge_und_teile` mit 429 > 400 ms; einzeln wiederholt grün, Teil „lang“ ganz wiederholt ohne Rot (berichtet, Protokoll).

**Optionen:**
- **(a)** Keine Teständerung. Im Merge-Tor wird ein roter Zeittest einzeln wiederholt; ist er dann grün, steht er als „lastabhängig“ im Protokoll. Maßgeblich ist der GitHub-Lauf; dort muss er grün sein.
- **(b)** Diese Grenzen nur noch auf GitHub prüfen. Folge: Teständerung in `test_vorladen.py`, neue Freigabe **FG-108** (siehe Frage 26).
- **(c)** Merge-Tor bei jedem roten Zeittest anhalten. Folge: häufige Stopps ohne Befund.

**Empfehlung: (a)**; sie ergänzt deine Regel für GitHub (Weisung 41, Zur Kenntnis 5) um das Merge-Tor; wird ein Zeittest auf GitHub rot, gilt weiter der Katalog. Offen gesagt: Im Container sind inzwischen zwei verschiedene Zeittests betroffen (N6 und Merge-Tor N1); werden sie dort häufiger rot, wäre (b) die Alternative.
Belege: `n6/ergebnis.md` Abschnitt 2 und 9 (E2-3); `integration/PROTOKOLL.md` (Welle 3c 2/5), `integration/tor/tor_53a4354.md`, `tor_53a4354_lang_wdh.md`.

## Frage 19 (E2, gebaut): Drei eigene Entscheidungen von N6 beim Vorladen in Teilen

**Problem:** Der Bauer hat innerhalb von B-I-04 drei Dinge entschieden, die keine Planzeile nennt. Sie ändern kein sichtbares Verhalten im Ergebnis, aber das Vorgehen.

**Stand (berichtet):**
1. Der letzte Teil der Karteikarten wartet auf das Vorwärmen der Karten (höchstens 5 s).
2. Die Liste der Szenarien und Testprojekte wird in zwei Teilen gebaut.
3. Umbruchbreiten der vier Ansichten werden nach dem letzten Teil neu gesetzt; das behebt einen zeitweise roten Breitentest beim Testprojekt, den es auf `e0f9c7e` nicht gab.
Kontrollfehler: 25 von 25 rot (berichtet).

**Optionen:** **(a)** Bestätigen. **(b)** Einzelne zurücknehmen (dann sagst du, welche).

**Empfehlung: (a).**
Belege: `n6/ergebnis.md` Abschnitte 1, 3, 9 (E2-4).

## Frage 20 (schon entschieden, nur Rückfrage zum Zeitpunkt): Vorlade-Teile unter Windows über 150 ms

**Schon entschieden:** Weisung 38/40, N6-F5: Teile über 150 ms unter Windows sind ein Befund im Bericht. Das wird so umgesetzt; offen ist nur, ob jetzt weiter geteilt oder nach S5c neu gemessen wird. Ohne Antwort gilt (a).

**Problem:** Du wolltest Teile über 150 ms unter Windows als Befund sehen. Mehrere Teile liegen darüber; weiter teilen ließe sich nur in einem gemeinsamen Listen-Baustein bzw. im Aufbau des Rechners, was mehr Konflikt mit dem Strang S5c (schnelleres erstes Öffnen des Rechners) bringt.

**Stand (berichtet, Windows-Messung Lauf 38515882184, Ergebnis des Laufs belegt):** Rechner 385 ms, Szenarien AP1/AP2 248/241 ms, Testprojekt 250 ms, abschluss 203 ms; im Abbau je Schritt etwa 205 ms, bei Schrift „Groß“ etwa 380 ms. Auch unveränderte Schritte liegen darüber (Optionen 204, Notizblock 217 ms). Das Vorladen dauert insgesamt länger (8548 → 10082 ms Median), blockiert aber kürzer.

**Optionen:** **(a)** Als Befund in den Bericht; nach dem Merge von S5c neu messen (der Trainer fällt dann aus dem ersten Rechner-Schritt) und erst dann entscheiden. **(b)** Jetzt weiter teilen. Folge: gemeinsamer Baustein, Konflikt mit S5c.

**Empfehlung: (a).**
Belege: `n6/ergebnis.md` Abschnitte 6, 8, 9 (E2-5), `n6/belege/messung_windows/`; Lauf 38515882184.

## Frage 21 (E2, ggf. Antrag): Dashboard nach einer Antwort nicht schneller

**Problem:** Der Plan sagt für den sehr großen Lernstand: Dashboard, Notizblock und „Alles ersetzen“ werden schneller. Das Dashboard ist jetzt schnell, wenn sich nichts geändert hat, nach einer Quiz- oder Szenario-Antwort aber nicht. Gut die Hälfte der Abfragezeit steckt in der Berechnung „fällig“ in geschützten Dateien.

**Stand (berichtet, Container unter Last, nur Richtung):** Dashboard ohne Änderung 2456 → 205 ms; nach 1 Quizantwort 2193 → 2675 ms; nach 1 AP1-Szenario 1779 → 2096 ms (im Rauschen). Profil: Abfragen etwa 900–1020 ms, davon „fällig“ 507–612 ms; Zeichnen 270–400 ms. Windows nicht gemessen. Der Zielvorschlag „Dashboard nach Änderung ≤ 0,2 s“ ist eine E3-Frage an Nico aus dem Testplan, kein Testkriterium.

**Optionen:** **(a)** N7 erarbeitet einen FG-Antrag mit Diff für eine schnellere Berechnung „fällig“ (zum Beispiel schrittweise), mit Messung; nicht bauen vor deiner Freigabe. **(b)** Als Befund schließen. Folge: Ein Planziel ist nicht erreicht; das ist nach der Regel „nichts kürzen“ Nicos Entscheidung.

**Empfehlung: (a).**
Belege: `n7/ergebnis.md` Abschnitte 6 und 10 (Frage 1), `n7/logs/profil_dashboard_nach_quiz.log`, `n7/logs/messung_tabelle.md`.

## Frage 22 (E2): Notizblock-Suche nicht schneller

**Problem:** Die Suche im Notizblock ist nicht schneller geworden, weil die Zeit im Aufbau der Zeilen steckt und nicht im Suchtext. Ein schrittweises Zeichnen wie bei der Suche oben ist nicht im Plan und berührt den Strang S1c2 (Breiten der Lernansichten).

**Stand (berichtet):** Notizblock-Suche 1103/863/1048 → 1160/1208/1301 ms; Zeilenaufbau etwa 900 ms; Notizblock-Aktualisierung 2226 → 1432 ms.

**Optionen:** **(a)** Eigener Punkt nach dem S1c2-Merge (schrittweises Zeichnen, ungeschützt, mit Tests und Messung). **(b)** Als Befund schließen. Folge: Planziel teilweise nicht erreicht, Nicos Entscheidung.

**Empfehlung: (a).**
Belege: `n7/ergebnis.md` Abschnitte 6 und 10 (Frage 2).

## Frage 23 (E2): „Sicherung erstellen“ und „Alles ersetzen“ schneller (Weg 2) als eigener Auftrag nach S6b

**Problem:** Für Sicherung und „Alles ersetzen“ sieht der Plan einen zweiten Weg in einer geschützten Datei vor, bedingt durch eine Messung „langsam“ und erst auf dem Stand nach S6b. Die Messung zeigt „langsam“; S6b ist noch nicht im Integrationsstand, deshalb ist Weg 2 nicht gebaut.

**Stand (berichtet, gemessen auf `e0f9c7e`, Container):** Sicherung erstellen 3744 ms, Alles ersetzen 5186 ms (über den Schwellen des Plans). Windows nicht gemessen.

**Optionen:** **(a)** Eigener Auftrag nach dem S6b-Merge (Messung auf dem S6b-Stand, Abläufe und Kontrollfehler aus dem Testplan, eigene Gegenprüfung), Merge vor N14 wie im Plan. **(b)** Nicht bauen. Folge: Planziel nicht erreicht, Nicos Entscheidung.

**Empfehlung: (a).**
Belege: `n7/ergebnis.md` Abschnitte 1, 6, 10 (Frage 4); Plan-Nachtrag Nr. 19 und Freigabeliste FG-47.

## Frage 24 (E2, Satz für Bericht und Testliste): Bestenliste-Eintrag aus einer westlicheren Zeitzone erscheint früher

**Problem:** Mit der neuen Bestenliste-Regel bekommt ein Eintrag, der nicht nach der Lösch-Marke liegt, die Marke plus eine Sekunde. Kommt der Eintrag von einem Gerät westlich der Zeitzone der Marke, kann er in Weltzeit schon nach der Marke liegen, als Text aber nicht; er wird dann auf die Marke gesetzt und erscheint bis zum Zonenunterschied früher als seine echte Zeit. Es geht nichts verloren; betroffen sind nur Anzeige und Reihenfolge.

**Stand (berichtet, Gegenprüfung FG-100, Probe):** Beispiel Marke 12:00 (Berlin), Eintrag 11:00 auf einem Gerät in UTC: −3599 s; bei Zeitumstellung im Herbst −2399 s. Der Eintrag bleibt in beiden Lesewegen erhalten.

**Optionen:** **(a)** Ein Satz in Bericht und Testliste, keine Code-Änderung. Vorschlag: „Ein Bestenliste-Eintrag, der in derselben Sekunde wie ‚Bestenliste löschen‘ auf einem Gerät in einer westlicheren Zeitzone entstand, kann mit einer früheren Uhrzeit angezeigt werden; er bleibt erhalten.“ **(b)** Code ändern. Folge: FG-100 erweitern; die Regel „als Text oder in UTC“ ist nötig, damit Geräte mit älterem Abgleich den Eintrag behalten.

**Empfehlung: (a)**, Wortlaut von dir oder wie vorgeschlagen.
Belege: `s6b/gp_fg100/ergebnis.md` (G1), `s6b/m38/ergebnis.md` („Bekannte Eigenschaft“).

## Frage 25 (E2): Kein Repo-Test mit echter Zeitumstellung für FG-100

**Problem:** Die neuen Tests prüfen die Zeitumstellung mit festen Wertepaaren (nachgestellte Zeitstempel), nicht über die echte Umrechnung der Geräteuhr. Der Prüfer hat das mit einer eigenen Probe über die echte Umrechnung (Berlin, New York, Indien, UTC) nachgeholt; als Test im Repository fehlt sie. Deine Auflage („mindestens zwei Zonen und Zeitumstellung“) ist laut Prüfer erfüllt.

**Stand (berichtet):** Probe 12 Fälle, „FEHLER: 0“.

**Optionen:** **(a)** Die Probe als zusätzlichen 0.63.2-Test aufnehmen (ungeschützte Testdatei, Kontrollfehler rot). **(b)** So lassen, Hinweis im Bericht.

**Empfehlung: (a)**; kleiner Aufwand, schließt die Lücke dauerhaft.
Belege: `s6b/gp_fg100/ergebnis.md` (G2), `s6b/gp_fg100/belege/probe_dst.py`, `probe_dst.txt`.

## Frage 26 (E2): Vergabe der FG-Nummern

**Problem:** Nächste freie Nummer ist FG-104. Nummern vergibst du; hier ein Vorschlag passend zu den Fragen.

| Nummer | Gegenstand | Frage |
|---|---|---|
| FG-104 | `test_vorladen.py` `test_klick_hat_vorrang` (N6) | 2 |
| FG-105 | `fisi_lernen.py:794` „z. B.“ und eine Ersetzungszeile in `test_rechenweg.py` (N8) | 14 |
| FG-106 | `mobile/src/spiel.py` Spielansichten 160/200 % (N9) | 7 |
| FG-96 erweitert | Breitentests N8 (Dateiliste; ggf. Teil „breite2“) | 1 |
| FG-97 bestätigt | APK-Prüfung Trennmodul | 5 |
| FG-101 erweitert | Test der Auswahlknöpfe + `ui.PillGroup` | 6 |
| FG-102, FG-103 | wie reserviert | 8, 9 |
| FG-73 erweitert | nur falls Frage 15 (b) | 15 |
| FG-107 | nur falls Frage 4 (b) (CI-Teil volle Uhr-Prüfung) | 4 |
| FG-108 | nur falls Frage 18 (b) (Zeitgrenzen in `test_vorladen.py` nur auf GitHub) | 18 |

**Empfehlung:** so bestätigen.
Belege: Weisung 41 Abschnitt 19 (Tabelle FG-97 bis FG-103, nächste freie FG-104); Fragen 1–18 dieser Meldung.

---

## Zur Kenntnis

### Selbst entschieden (E1)
| Nr | Entscheidung | Begründung | Beleg |
|---|---|---|---|
| E1-1 | Die Trennregel im Handy-Bereichstitel („ANPASSUNG\|EN“, `mobile/src/ui.py`) wendet der Strang an, dem `ui.py` gehört (N9), nach dem N8-Merge; nicht N8. | Sinngemäß nach deiner Weisung 22, Frage 6 (a) („Strang, dem `ui.py` gehört“); dort ging es um die Unterschrift von `ui.Card`, hier um den Bereichstitel (`mobile/src/ui.py:114`). Wer das strenger liest, stuft es als E2 ein; dann bitte kurz widersprechen. Der Bauer hatte es als E3 gefragt; es ist keine Frage an Nico. | `n8/Erwartungsliste_Trennung.md` (E3-1), Weisung 22 |
| E1-2 | Merge-Konflikt N7 × N8 in der Suche (Hinweis „… weitere %d Treffer nicht angezeigt.“): Auflösung mit der Zahl aus N7 (`self._more`), Wortlaut aus N8. | Inhaltlich gleich; die N7-Tests prüfen die Zahl. | `n7/ergebnis.md` Abschnitt 8 (berichtet) |
| E1-3 | Konflikt N6 × S5c im Aufbau des Rechners: Lösung nach dem getesteten Vorschlag des N6-Bauers beim Integrieren. | Im gelösten Merge waren die betroffenen Tests grün bis auf den Test aus Frage 2. | `n6/s5c_konflikt/`, `n6/ergebnis.md` Abschnitt 8 (berichtet) |
| E1-4 | Merge-Tor nach dem N1-Merge: der zusätzliche rote Zeittest (429 > 400 ms) wurde einzeln wiederholt (grün), Teil „lang“ ganz wiederholt (0 rot); weiter mit Vermerk „lastabhängig“. | Deine Regel in Weisung 41 (Zur Kenntnis 5) gilt nur für GitHub; für das Merge-Tor habe ich sie sinngemäß angewandt (einzeln wiederholen, Vermerk). Die allgemeine Regel fürs Merge-Tor ist Frage 18. | `integration/PROTOKOLL.md`, `integration/tor/tor_53a4354*.md` (berichtet) |
| E1-5 | N8 hat zusätzlich die Startzeilen bei „Sehr groß“ 1120 px umbrechen lassen (nur Umbruch, keine neuen Elemente), weil die längeren Knopftexte sonst die Seite verbreitert hätten; Kopfzeile bei Groß/Sehr groß 2 px höher. | Zurechtrücken, Aussehen geht per Foto an Nico. | `n8/ergebnis.md` Abweichungen 3 und 5 (berichtet) |

### Weitere Punkte
1. **N14, ehrlicher Hinweis:** Die zwei Commits `fff5824` und `37d0ab6` sind lokal um 03:44:53 UTC entstanden (belegt, `git log`), also vor deiner Weisung 41 (03:55 UTC) und vor deren Auflage 1 („f2g und Zufallsabläufe erst zu Ende, bevor committet wird“); der Hauptstrang hatte lokales Committen vorher erlaubt. Gepusht wurde erst nach dem Ende von f2g und den Zufallsabläufen, zusammen mit `053931d` (berichtet). Inhaltlich hat sich dadurch nichts geändert.
2. **N14, Ergebnisse deiner Auflagen 1–3 (Weisung 41):** f2g „vor“/„nach“ unter U3 und U6: wie S6b, kein Etikett weniger (berichtet, Log genannt). 26 Zufallsabläufe: „Fehler []“, 15 Etiketten mit N14 mehr (belegt, Log); sie enthalten kein „Alles ersetzen“, der U6-Fall ist dort also nicht abgedeckt. **Zweites „Alles ersetzen“** mit derselben Datei im U6-Fall: die Einträge kommen zurück (direkt 2/2) und bleiben nach drei Abgleich-Runden auf beiden Geräten (belegt, Log; der Log ist ein Erfassungslauf mit noch leerem Sollwert, die Werte stehen in der Ausgabe). Der Test heißt `test_grenze_g8_f2b_u6_nachlauf_weiter_falsch` und trägt „bekannte Grenze, kein Versprechen“; Kontrollfehler K1 und K3 rot (berichtet). AK1 steht wörtlich wie verlangt (berichtet). N14 bleibt bis zu Nicos Antwort in Meldung 39 ungemergt.
3. **S6b nach Weisung 38/40:** End-Stand `d96dc5e`, ein Push, Lauf 38512762337 grün (belegt). Satz 5 gestrichen, byte-gleich (1408 Bytes, sechs Satzgrenzen), neue Tests h1/h7/h7h/h9, Dialog gemergt, Fotos (berichtet). Die von dir verlangte **unabhängige Prüfung (i) Bytes, (ii) Tests und Kontrollfehler, (iii) Satz nirgends sonst** ist fertig (`s6b/gp_satz5/ergebnis.md`, unabhängiger Prüfer, nicht der Bauer). **Ergebnis: alle drei Punkte bestanden, keine Abweichung.** (i) Byte-Gleichheit belegt: Laufzeit-Absatz aus `replace_question` (fisi_sicherung.py:590-608) gleich Weisung Zeile 27, 1408 Bytes, gleiche sha256 wie beim Bauer; Handy-Kopie per cmp gleich; PC (app_gui.py:6394) und Handy (mobile/src/main.py:4508) rufen dieselbe Funktion. (ii) Tests belegt (Linux): test_sicherung_fehler (21), test_sicherung, BG08Ersetzen h1/h7/h7h/h9, test_dialog_warntext (15) grün; eigene Kontrollfehler (Satz wieder ein, sinngleiche Fassung, Strich, Anführungszeichen, Doppel-Leerzeichen, Satzzeichen, Umbruch) alle rot, neutrale Gegenkontrolle grün. Hinweis: Der Wortlaut hängt allein an test_b_g_08; der Dialogtest fängt Wortlautfehler nicht. Kontrollfehler des Bauers zu den Verhaltenstests nur gesichtet (berichtet); Windows/macOS nicht geprüft. (iii) belegt: Der Satz steht nur noch im Ausschluss-Test (test_sicherung_fehler.py:288-290); Hilfe, LIESMICH, AENDERUNGEN.md (noch ohne 0.63.2-Abschnitt), Tooltips, Handy-Code sauber; 26 Treffer in den geteilten Ordnern sind nur Geschichte; eine Testliste für FG-81 gibt es noch nicht. **Damit erbitte ich deine Abnahme von FG-81 und FG-92 (zusammen mit Frage 3).** B-G-08 bleibt bis zu deiner Abnahme außerhalb des Integrationsstands. Der Vorschlag zu deiner Frage 9 (Vergleichstests S6b × S6c) liegt als Diff bereit und kommt erst im Integrationsstand (berichtet: im Probe-Merge 4 Tests grün, Kontrollfehler 4/4 rot).
4. **`pkill -f` vom 14.10. (Weisung 41, Zur Kenntnis 9): Nein**, kein fremder Lauf erkennbar getroffen. Geprüft: Das Merge-Tor `tor_e0f9c7e_2` lief 01:40–02:42 UTC vollständig, ohne „code_14b3bd4“ in den Befehlszeilen, Testzahlen wie GitHub; einziger Ausfall war das bekannte stille Ende des Rundgang-Tests um etwa 02:08 (E1-12). Das einzige andere Verzeichnis mit diesem Namen hatte Dateien mit letzter Änderung am 13.10.; der Ordner selbst wurde zuletzt am 14.10. um 01:12 UTC geändert, also vor 01:50. Befehlszeilen vergangener Prozesse sind nicht nachprüfbar, deshalb „vermutet nein“ (berichtet: Integrator und N16-Bauer). Künftig nur eigene Prozesskennungen.
5. **N11, Universal-Mac (deine Untersuchung zu Frage 19):** Auf einem Probezweig ließ sich aus den beiden offiziellen Rädern der Bildbibliothek ein Universal-Rad erzeugen; damit gelang der Universal-Bau, alle 80 Programmdateien universal, dieselbe Datei startete auf Intel (Lauf 38509635406; der Lauf ist insgesamt rot: „windows“ durch die gewollt rote Inno-Fehlschlag-Probe im selben Lauf, dazu „Tests Linux (rest)“ – Ursache nicht geprüft, vermutet die bekannten Breitentests ohne FG-96) (berichtet; Lauf belegt). Risiko: selbst erzeugte Datei, neues Werkzeug im Bau, Intel-Start etwa 50 s statt 25 s. Empfehlung des Bauers: in 0.63.2 getrennte Mac-Bauten. Der Absatz geht an Nico (Meldung 39); eine neue Bauquelle kommt nur mit deiner Freigabe. N11 End-Stand `dfc73da`, Lauf 38509144455 grün (berichtet); Fragen 20/21 umgesetzt (fehlende Datei im Bericht, Inno-Fehlschlag macht den Lauf rot, Probe 38508995179) (berichtet).
6. **N10:** End-Stand jetzt `f29478b`, Lauf 38509822349 grün (belegt). Für den Merge fehlt nur das Merge-Tor. `release.yml` bleibt „nicht geprüft“.
7. **N15:** End-Stand `5e639c2` mit deinen Fragen 16/17 (SP1–SP6, HA3–HA9, 58 Tests, Kontrollfehler rot; in der geschützten Spiel-Datei nur die 13 erlaubten Zusätze, Syntaxbaum sonst gleich) (berichtet). Lauf 38511623383 rot nur durch die bekannten Breitentests (berichtet). Der Vermerk „FG-63 erweitert“ kommt in die Freigabeliste.
8. **N16:** F31 gebaut (`e32064a`) mit der erweiterten Testzeile und der Liste der 17 verbotenen Zusage-Wörter, zusätzlich eine Absatz-Prüfung (strenger) (berichtet). Lauf 38509045853: „spiel“ rot (S6b-Befund, durch FG-100 behoben), „rest“ nach 30 min abgebrochen (berichtet).
9. **N9:** End-Stand `72afbe1`: Hilfetext und Suchwörter (deine Frage 10) und FG-101 gebaut, Kontrollfehler vorher geschrieben (berichtet). Lauf 38513304432: „rest“ rot nur durch die bekannten Breitentests, Teil „rest“ 1701 s (ohne FG-96) (berichtet; Ergebnis je Job belegt). Der Abschnitt 0.63.2 in `AENDERUNGEN` muss die neuen Stufen nennen (gibt es noch nicht).
10. **Allgemein:** Zweig-Läufe ohne FG-96 brechen den Teil „rest“ an der 30-min-Grenze ab (N8, N14, N16). Ganze grüne Läufe für Zweige auf S6b gibt es erst auf dem Integrationsstand nach FG-96, FG-100 und der T-c-Anpassung.
11. **Integration:** Welle 3c läuft: S6c, N1 und N2 lokal gemergt, jeweils mit Merge-Tor (N1: rot nur durch einen lastabhängigen Zeittest, E1-4; N2: `0329bc9`, Tor grün, `integration/PROTOKOLL.md` Z. 192), noch nicht gepusht – `version-0632` auf GitHub weiter `e0f9c7e` (belegt); danach Fix 3b mit einem ganzen Lauf, dann FG-96 (berichtet, Protokoll).

## Geht an Nico (Meldung 39)
- N14: Weg b mit der benannten Ausnahme; drei Sätze für Nico: (1) Uhr geht dauerhaft nach, Neustart, Löschen und „Alles ersetzen“: eine frühere Löschung eines anderen Geräts kann das Eingespielte wieder entfernen. (2) Die Einträge bleiben in der Sicherungsdatei; ein zweites „Alles ersetzen“ holt sie zurück, dann bleiben sie. (3) Gegenüber 0.63.1 geht nichts zusätzlich verloren; die neue Regel verhindert einen Verlust nach dem Richtigstellen der Uhr. N14 bleibt bis zu seiner Antwort liegen.
- N8: Startknöpfe „AP1 starten“, „Konzeption starten“, „Netzwerke starten“, „WiSo starten“ und die übrigen N8-Fotos (Listentitel, Suchfeld, Banner-Ecke, Trainer-Felder, Tooltip, Kachel mit Tab-Fokus).
- N8: Kästchen „Markt“ (B-D-08) erst nach N5.
- N8: nicht geprüft, auf die Testliste: Umbruch am Handy (B-D-06), Tab-Reihenfolge der IJK-Liste, Zoom-Tab-Reihenfolge und Farbwechsel; vermutet: Hinweisschild folgt dem Knopf nicht beim Rollen mit dem Mausrad.
- N9: Tippflächen Variante sichtbar/unsichtbar (Fotos), Navigationsleiste, Schriftstufen-Reihe bei 1120 px (Fotos), Spielansichten 200 % vorher/nachher (Fotos).
- N6: Zielwert für die Wartezeit nach einem Schrift- oder Farbwechsel (Windows bedienbar nach 1,8–4,4 s, danach Schritte von etwa 200 ms); Aussehen der Zwischenstufe (Fotos, Optik-Bereich einen Schritt lang offen und leer).
- N7: Wartehinweis „Bitte warten – …“ beim Erstellen der Sicherung und beim Ersetzen (Fotos); Schrittgröße der Suche erst nach einer Windows-Messung.
- N11: Universal-Mac, Absatz mit Ergebnis der Probe und Empfehlung „getrennt bleiben“.
- N15: Testlisten-Punkt „Hinweis ‚Es läuft gerade eine Prüfung …‘ nach ‚Üben‘ bleibt seine volle Zeit stehen“.
- S6b: Dialog-Aussehen (Großbuchstaben, kein Warnsymbol, roter Ja-Knopf, Knopfreihenfolge macOS) und kurze Rückfrage vorher/nachher am Handy.
- Falls Frage 24 (a): Satz zur Bestenliste in die Testliste.

## Glossar (nur hier verwendete Kürzel)
- **N6 … N16:** Bauaufträge aus dem Plan-Nachtrag; **S6b:** Strang „Abgleich und Alles ersetzen“; **S6c:** „Projekt löschen löscht die Texte“; **S1c2:** Breiten der Lernansichten; **S5c:** schnelleres erstes Öffnen des Rechners; **Fix 3b:** Reparatur der Breitentests mit der Runner-Schrift.
- **FG-nn:** Freigabe für geschützte Dateien oder Bestandstests; **FG-96:** Aufteilung der Testteile („breite“); **FG-100:** Schreibfunktion der Bestenliste; **FG-101:** Schriftgrößen-Bestandstests.
- **„rest“, „lang“, „spiel“, „breite“:** Testteile des GitHub-Laufs, je ein Job mit 30 min Grenze; **Merge-Tor:** Prüfskript nach jedem Merge.
- **B-M-02:** zufällige CI-Fehlschläge (N10); **B-I-03/B-I-04:** Leistung Dashboard/Vorladen; **B-J-04:** Tippflächen 48 dp; **B-J-06:** neue Schriftstufen; **B-D-06:** Umbruch langer Titel; **B-G-17:** Bestenliste-Löschmarke; **B-G-08:** „Alles ersetzen“ hebt Löschungen auf.
- **U1 … U11:** Uhr-Zustände im Testplan N14 (U3: Uhr ging 2 h nach, gestellt; U6: geht weiter 2 h nach); **f2g:** Pflichtablauf mit „Alles ersetzen“; **AK1:** Abnahmekriterium „nie mehr Verlust“.
- **G1, G2:** geringe Befunde der Gegenprüfung FG-100.

## Belege dieser Meldung (gemeinsamer Ordner `bau_0.63.2/`, nicht auf `meldungen`)
- `n8/ergebnis.md`, `n8/Erwartungsliste_Trennung.md`, `n8/FG-97_Antrag_apk_pruefen.md`, `n8/Vorschlag_VLSM_zB.md`, `n8/logs/ci_rest_927ef5f.txt`; Lauf 38510468972
- `n6/ergebnis.md`, `n6/belege/`, `n6/s5c_konflikt/`; Läufe 38515583274, 38515882184
- `s6b/m38/ergebnis.md`, `s6b/m38/fg100_fisi_core.diff`, `fg100_tests.diff`, `vorschlag_frage9_tc_s6c.diff`; `s6b/gp_fg100/ergebnis.md`, `s6b/gp_fg100/belege/`; Lauf 38512762337
- `n14/ergebnis.md`, `n14/sofortmeldung_F5_F2.md`, `n14/logs/` (`s1_voll.log`, `s1_voll_loescharten_lauf2.log`, `n14_g8_zweites_ersetzen.log`, `n14_test_s1_lauf3_end.log`); Lauf 38509788620
- `n9/ergebnis.md`, `n9/antrag_bj04_und_spiel200.md`, `n9/antrag_bj04_sichtbar.diff`, `n9/antrag_bj04_unsichtbar.diff`, `n9/vorschlag_spiel200.diff`; Lauf 38513304432
- `antraege/FG-102_Antrag.md`, `antraege/belege_fg102/`, `antraege/FG-103_Antrag.md`, `antraege/belege_fg103/`
- `n10/abschluss/ergebnis.md`, `n10/abschluss/fensterziehen/`; Läufe 38509822349, 38509861050
- `n7/ergebnis.md`, `n7/logs/`
- `n11/ergebnis.md`; Läufe 38509635406, 38509144455, 38508995179
- `n15/ergebnis.md`; Lauf 38511623383 · `n16/ergebnis.md`; Lauf 38509045853
- `fg96/ergebnis.md`, `integration/PROTOKOLL.md`, `integration/tor/`, `OFFEN_FUER_BERICHT.md`
- Weisungen: `plan_0.63.2/freigabe/Weisung_CC_Antwort_Meldung_38_und_40.md`, `Weisung_CC_Antwort_Meldung_41.md`
- Gegenprüfung dieser Meldung: `meldungen/gegenpruefung/Gegenpruefung_Meldung_42.md` (eigene) und `Gegenpruefung_Meldung_42_unabhaengig.md` (unabhängig), Erledigung in `Gegenpruefung_Meldung_42_Erledigung.md`

## Eingearbeitet aus der Gegenprüfung (Fund → Stelle)
- Die Gegenprüfung ist **nicht unabhängig**: In dieser Sitzung stand kein Werkzeug für einen eigenen Unteragenten zur Verfügung; sie ist ein getrennter, systematischer Prüfgang des Verfassers gegen die Quellen (Einzelheiten in `Gegenpruefung_Meldung_42.md`). Eine unabhängige Prüfung hat der Hauptstrang inzwischen nachgeholt (`Gegenpruefung_Meldung_42_unabhaengig.md`); ihre Befunde stehen im nächsten Abschnitt.
- GP-1 (Frage 2: „keine Freigabe deckt“ war unbelegt) → als „laut Bauer“ gekennzeichnet.
- GP-2 (Frage 1: Herleitung der Schätzfaktoren fehlte) → Herleitung ergänzt.
- GP-3 (Zur Kenntnis 11: N2-Merge-Tor nur aus dem Ordner geschlossen) → als vermutet gekennzeichnet; in Fassung 3 überholt (N2-Tor grün, siehe G-3).
- GP-4 (Frage 26 ohne Belegzeile) → Belegzeile ergänzt.
- Nicht geändert: GP-5 (Frage 18) – bleibt als Frage; nach G-4 präzisiert: Weisung 41 regelt nur GitHub, das Merge-Tor ist ungeregelt.

## Eingearbeitet aus der unabhängigen Gegenprüfung (Fassung 3)
- M-1 (Frage 3: 10 Codezeilen falsch, richtig 9) → Frage 3, Selbstkontrolle und Kopfblock korrigiert (Zählfehler: Kopfzeile `+++` mitgezählt); Frage 3 bleibt vorn, aber als „blockiert nur zusammen mit FG-81/FG-92“, Umfang unstrittig.
- G-1 (Lauf 38509635406 auch „rest“ rot) → Selbstkontrolle und Zur Kenntnis 5.
- G-2 (Satz-5-Prüfung läuft) → Zur Kenntnis 3 mit Platzhalter für das Ergebnis.
- G-3 (N2 gemergt, Tor grün) → Zur Kenntnis 11.
- G-4 (Weisung 41 regelt nur GitHub) → Frage 18 und E1-4.
- G-5 (Frage 6 (c) durch Weisung 41 Abschnitt 13 ausgeschlossen) → Option gestrichen, Hinweis statt dessen.
- G-6 (Frage 20 schon entschieden) → als „schon entschieden“ markiert, Nummer behalten; Kopfblock: 25 offene Fragen.
- G-7 („N9-F8“ unerklärt) → Frage 4 (a) erklärt.
- G-8 (Frage 18 (b) ohne FG-Nummer) → FG-108, Zeile in Frage 26.
- G-9 (E1-1 Begründung zu weit) → präzisiert (`ui.Card` dort, Bereichstitel hier; ggf. E2).

---

# Anhänge (Wortlaut aus den Quelldateien übernommen, nicht verändert)

## Anhang A: Erwartungsliste Trennung (N8, zu Fragen 11–13)
Quelle: `n8/Erwartungsliste_Trennung.md` (Abschnitte „Zeichen in der Liste“ bis „Nie trennen“; die Fragen stehen oben als 11–13).

#### Zeichen in der Liste

- `‖` bevorzugte Stelle (Wortfuge oder vorhandener Bindestrich), wird zuerst genommen
- `|` weitere zulässige Stelle (Silbengrenze nach amtlicher Regel 2006, §§ 107 ff.)
- Am Zeilenende steht ein Trennstrich; an einem vorhandenen Bindestrich kein zweiter.
- Vorschlag Mindestlänge (Frage E2-1 unten): links und rechts der Stelle je mindestens
  2 Buchstaben (also nie `A-bschluss`, nie `frei-e`).

#### Wörter aus echten Texten

Nr. 27-33 und Nr. 2 sind die Titel, bei denen der Test `test_listentitel_breite_0632` heute den
Rückfall (Teilung ohne Strich) misst (Log `logs/test_listentitel_breite_0632_neu.txt`).

| # | Wort (Fundstelle) | erwartete Stellen | Problemfall / warum in der Liste |
|---|---|---|---|
| 1 | Wirtschaftlichkeitsbetrachtung (inhalte/fachgespraech.json:323; Titel Abschlussprojekt) | Wirt\|schaft\|lich\|keits‖be\|trach\|tung | 30 Zeichen ohne Bindestrich; heute Rückfall ohne Strich; `ch` nie trennen |
| 2 | Wirtschaftlichkeitsvergleich (inhalte/projektarbeiten.json:99; Liste Abschlussprojekt) | Wirt\|schaft\|lich\|keits‖ver\|gleich | heute gemessener Rückfall am PC: Groß, 1360 (Titel mit Doppelpunkt, `:` bleibt am Wort) |
| 3 | Mehrfaktor-Authentifizierung (inhalte/fachgespraech.json:239) | Mehr‖fak\|tor-‖Au\|then\|ti\|fi\|zie\|rung | Bindestrich zuerst (heute schon gebaut); `au` und `ie` nie trennen |
| 4 | PRÜFUNGSTRAINER (app_gui.py:211, Seitentitel in Versalien) | PRÜ\|FUNGS‖TRAI\|NER | Versalien und Umlaut: Regel muss groß/klein gleich behandeln; `ai` nie trennen (englisch „Trainer“) |
| 5 | ANPASSUNGEN aus „Optische Anpassungen“ (app_gui.py:6105; Handy: Titel aus fisi_optionen.py, in mobile/src/ui.py:114 per `title.upper()` in Versalien, Befund N9 200 %) | AN‖PAS\|SUN\|GEN | Befund N9: heute `ANPASSUNG\|EN` (Tk/Flutter teilen irgendwo); `EN` allein ist keine Silbe |
| 6 | Datensicherungskonzepte (inhalte/rahmenplan.json:2166) | Da\|ten‖si\|che\|rungs‖kon\|zep\|te | `ch` bleibt zusammen (`si-che`, nie `sic-he`) |
| 7 | Hochverfügbarkeit (inhalte/fachgespraech.json:275) | Hoch‖ver\|füg\|bar\|keit | `ch` am Silbenende; Umlaut |
| 8 | Kundenzufriedenheit (inhalte/karteikarten.json:1403) | Kun\|den‖zu\|frie\|den\|heit | `ie` nie trennen |
| 9 | IPv6-Adresse (app_gui.py:4644, Trainer/Rechner) | IPv6-‖Adres\|se | Abkürzung mit Ziffer nie trennen; kein `A-` (Einzelvokal am Anfang) |
| 10 | Netzwerkinfrastruktur (inhalte/projektarbeiten.json:8) | Netz‖werk‖in\|fra\|struk\|tur | `tz` an der Fuge; `str` am Silbenanfang |
| 11 | Abschlussprojekt (app_gui.py:168, Navigation) | Ab\|schluss‖pro\|jekt | `sch` nie trennen; kein `A-` |
| 12 | Schwierigkeitsgrad (app_gui.py:6408) | Schwie\|rig\|keits‖grad | `Schw` bleibt zusammen, `ie` nie trennen |
| 13 | Broadcast-Adresse (app_gui.py:4719, Rechner) | Broad\|cast-‖Adres\|se | englisches Wort: `oa` nie trennen, nur `Broad-cast` |
| 14 | Präfixlänge (app_gui.py:4898, Rechner) | Prä\|fix‖län\|ge | Umlaut, `x` bleibt bei `fix` |
| 15 | Wildcard-Maske (fisi_core.py:2678, Rechenweg) | Wild\|card-‖Mas\|ke | englisch; `sk` wird `s-k` getrennt |
| 16 | Punkt-zu-Punkt-Verbindungen (fisi_core.py:2835, Rechenweg) | Punkt-‖zu-‖Punkt-‖Ver\|bin\|dun\|gen | drei Bindestriche; kurzes Stück `zu-` ist erlaubt (Bindestrich vorhanden) |
| 17 | Virtualisierung (fisi_core.py:267) | Vir\|tu\|a\|li\|sie\|rung | einzelner Vokal in der Mitte (`tu-a-li`) – zulässig, aber Frage E2-2 |
| 18 | Datenschutz-Grundverordnung (inhalte/karteikarten.json:214) | Da\|ten‖schutz-‖Grund‖ver\|ord\|nung | Fuge und Bindestrich; `tz` vor Bindestrich |
| 19 | Verschlüsselung (inhalte/fachgespraech.json:77) | Ver\|schlüs\|se\|lung | `sch` nie trennen; `ss` wird `s-s` |
| 20 | Nutzwertanalyse (inhalte/fachgespraech.json:17) | Nutz‖wert‖ana\|ly\|se | Falle: `Nutzwerta-nalyse` (rein nach Silbenmuster) wäre falsch; Fuge vor `ana` |
| 21 | AP2-Projektdokumentation (fisi_core.py:2003) | AP2-‖Pro\|jekt‖do\|ku\|men\|ta\|ti\|on | `AP2` nie trennen |
| 22 | Amortisationsrechnung (inhalte/karteikarten.json:811) | Amor\|ti\|sa\|ti\|ons‖rech\|nung | kein `A-`; `ch` bleibt zusammen |
| 23 | Übertragungsgeschwindigkeit (inhalte/karteikarten.json:4782) | Über\|tra\|gungs‖ge\|schwin\|dig\|keit | kein `Ü-`; 27 Zeichen |
| 24 | Unterbrechungsfreie (inhalte/karteikarten.json:473) | Un\|ter\|bre\|chungs‖freie | kein `frei-e` (Einzelvokal am Ende) |
| 25 | UND-Verknüpfung (fisi_core.py:4432, Rechenweg) | UND-‖Ver\|knüp\|fung | `pf` wird `p-f` |
| 26 | Subnetzmaske (fisi_core.py:1839) | Sub‖netz‖mas\|ke | Fugen zuerst |
| 27 | Notfallwiederherstellung (Listentitel „Szenarien“, gemessener Rückfall DejaVu Normal 1120 / Groß / Sehr groß 1360) | Not\|fall‖wie\|der‖her\|stel\|lung | `ie` nie trennen; Fugen Notfall‖wieder‖herstellung |
| 28 | Investitionsentscheidung: (Listentitel „Szenarien“, Rückfall DejaVu) | In\|ves\|ti\|ti\|ons‖ent\|schei\|dung | `ei` nie trennen; `:` bleibt am Wort |
| 29 | Datenschutzkonforme (Listentitel „Abschlussprojekt“, Rückfall DejaVu Groß 1360) | Da\|ten‖schutz‖kon\|for\|me | Fugen zuerst |
| 30 | Dokumentenmanagementsystem (Listentitel AP1, Rückfall DejaVu Normal 1360) | Do\|ku\|men\|ten‖ma\|nage\|ment‖sys\|tem | englisch „Management“: `ma-nage-ment`, nicht `man-age` |
| 31 | Schwachstellenmanagement (Listentitel „Szenarien“, Rückfall DejaVu Normal 1360) | Schwach\|stel\|len‖ma\|nage\|ment | `ch` nie trennen; englischer Teil |
| 32 | Netzwerkkomponenten (Listentitel AP1, Rückfall DejaVu Sehr groß 1360) | Netz‖werk‖kom\|po\|nen\|ten | `kk` an der Fuge: `werk-kom` |
| 33 | Remotedesktopdienste-Farm (Listentitel „Testprojekt“ Nr. 29, Seite 2; gemessen DejaVu Groß/Sehr groß 1360: „29. Remotedesktopdienste-“ passt nicht in die erste Zeile, Rückfall `Remotedesktopdienst\|e-Farm`) | Re\|mote‖desk\|top‖diens\|te-‖Farm | Nummer + Wort: erst die Silbenregel gibt eine passende Stelle (`29. Remote-`/`desktop…`); `st` darf getrennt werden (`diens-te`) |

#### Nie trennen (keine Stelle, auch nicht bei Platzmangel mit Strich)

| Beispiel (Fundstelle) | Grund |
|---|---|
| 192.168.1.50/24, 255.255.255.0 (fisi_core.py Rechenweg) | Zahlen/Adressen: Rückfall wie heute ohne Strich, nie Silbenregel |
| IPv6, AP1, AP2, RFC 3021 | Abkürzungen (Großbuchstaben + Ziffern) |
| 2^(32 - Präfixlänge) | Formel: nur das Wort `Präfixlänge` darf getrennt werden |


## Anhang B: FG-97, Diff (zu Frage 5)
Quelle: `n8/FG-97_Antrag_apk_pruefen.md`.

#### Diff 1: pruefung/apk_pruefen.py (eine Stelle)
```diff
--- a/pruefung/apk_pruefen.py
+++ b/pruefung/apk_pruefen.py
@@ -28,7 +28,9 @@
 
 PACKAGE = "io.github.papst2142cmd.fisi_lernplattform"
 # Ab 0.62: Lizenz und Hinweise zu Fremdbestandteilen muessen in der App liegen
-APP_FILES = ("LICENSE.txt", "THIRD_PARTY_NOTICES.txt", "fisi_rechtliches.pyc")
+# Ab 0.63.2 (N8, B3 a): gemeinsame Umbruchregel fisi_trennung (SHARED_FILES)
+APP_FILES = ("LICENSE.txt", "THIRD_PARTY_NOTICES.txt", "fisi_rechtliches.pyc",
+             "fisi_trennung.pyc")
 LABEL = "FI Lernplattform"
 SIGNATURE_IDS = {0x7109871A: "v2", 0xF05368C0: "v3"}
 
```

#### Diff 2: Test (in test_trennung_0632.py, Klasse HandyPaketTest)
```diff
+    def test_apk_pruefung_kennt_modul(self):
+        """B3 (a): Die APK-Pruefung verlangt fisi_trennung.pyc in app.zip."""
+        sys.path.insert(0, os.path.join(HERE, "pruefung"))
+        import apk_pruefen
+        self.assertIn("fisi_trennung.pyc", apk_pruefen.APP_FILES)
```
Kontrollfehler: Eintrag wieder entfernen -> Test rot.


## Anhang C: FG-102, Diff und Vorgaben (zu Frage 8)
Quelle: `antraege/belege_fg102/fg102_ci_tests.diff`, `fg102_build.diff`; Vorgaben und Kontrollfehler aus `antraege/FG-102_Antrag.md` Abschnitte 5.3 und 8.

```diff
--- a/pruefung/ci_tests.sh
+++ b/pruefung/ci_tests.sh
@@ -14,6 +14,8 @@
 #    rest     alle uebrigen test_*.py (neue Testdateien landen automatisch hier)
 #    windows  Auswahl fuer den Windows-Runner (Windows-eigene Wege; ab 0.62.4
 #             auch der Abgleich-Kern, test_abgleich.py laeuft dort nicht)
+#             Ab 0.63.2 (FG-102) auch der Warntext-Dialog "Alles ersetzen"
+#             prozessintern (test_dialog_warntext_fenster.py, ohne Xvfb)
 #    ibus     ab 0.63.2 (B-A-01): test_eingabe.py mit FISI_TEST_IBUS=1, also mit
 #             den Nachstellungstests mit echtem IBus (braucht ibus, dbus-x11).
 #             Fehlt ein Werkzeug, ist der Teil rot statt still "skipped".
@@ -38,7 +40,8 @@
   windows) DATEIEN="test_einzelstart.py test_haenger.py test_update.py test_update_fenster.py
                     test_leistung.py test_werkzeuge.py test_optionen.py test_sicherung.py
                     test_beenden.py test_namen.py test_rechtliches.py
-                    test_optionen_0622.py test_reiter_sichtbar.py test_abgleich_kern.py" ;;
+                    test_optionen_0622.py test_reiter_sichtbar.py test_abgleich_kern.py
+                    test_dialog_warntext_fenster.py" ;;
   ibus)    DATEIEN="test_eingabe.py"
            export FISI_TEST_IBUS=1
            # kurzer Zwischenspeicher-Pfad fuer IBus (Stolperstein aus 0.62.4)
```

```diff
--- a/.github/workflows/build.yml
+++ b/.github/workflows/build.yml
@@ -311,6 +311,18 @@
           path: installer_output/*
           if-no-files-found: error
 
+      # Ab 0.63.2 (FG-102): Warntext-Dialog "Alles ersetzen" auf echtem macOS
+      # (prozessintern, ohne Xvfb und ohne Flet; Text byte-genau, Standard
+      # "Nein", Bildlauf mit <MouseWheel>, Knoepfe sichtbar bei nachgestellter
+      # Bildschirmgroesse). Steht NACH dem Hochladen: Er kann den Installer
+      # nicht veraendern, die Datei liegt auch bei Rot zur Ansicht bereit.
+      # Rot macht den Job rot - wie jeder Test kein Release. Notausweg wie bei
+      # den Test-Jobs (TESTS_UEBERSPRINGEN, nur mit Nicos OK).
+      - name: Dialogtest Warntext (macOS)
+        if: runner.os == 'macOS' && vars.TESTS_UEBERSPRINGEN != 'ja'
+        timeout-minutes: 5
+        run: python test_dialog_warntext_fenster.py
+
   android:
     name: android
     runs-on: ubuntu-24.04
```

#### 5.3 Neue Testdatei `test_dialog_warntext_fenster.py` (nicht geschuetzt; Bau erst nach Freigabe, hier nur die Vorgaben)
1. Ein `ctk.CTk()` im Testprozess, keine Kindprozesse, kein Xvfb, keine Imports ausser Standardbibliothek, customtkinter, PIL und eigenen Modulen (kein flet, kein psutil, kein ctypes/X11).
2. **Kein `skip`** irgendwo in der Datei (auch nicht `skipUnless(_tk_ok())`): ohne Anzeige ist sie rot. Eine statische Pruefung in der Datei selbst (AST) verlangt das (fuer KF-D10a).
3. Bildschirm nachgestellt wie `test_update_fenster.py`: `LongQuestionDialog.winfo_screenwidth/height` an der Klasse ersetzen, nach dem Fall zuruecksetzen. Faelle wie Linux (1280x720 Normal hell, 1280x720 Sehr gross dunkel, 1366x768 Normal dunkel, 1366x768 Sehr gross hell) plus je einmal Faktor 1,25. **Regel fuer kleine echte Bildschirme (E2, siehe R2):** Ist der echte Bildschirm kleiner als der nachgestellte, nimmt der Fall den echten (kleineren) Wert und schreibt beide Werte in die Ausgabe.
4. Echter Weg `SettingsView._replace_backup(fake, backup)` mit `fake.app.root = root`; Sollwert `app_gui.fsi.replace_question(backup)` im selben Prozess (Testplan-Regel 0.1, keine Textkopie), Durchreich-Probe mit Marke.
5. Mausrad plattformgerecht: Linux `<Button-5>`, sonst `<MouseWheel>` mit `delta=-120`. Fokus: ausserhalb Linux `d.focus_lastfor()` statt `focus_get()` (siehe R1), Ereignisse an dieses Element.
6. Eigene Notbremse: `faulthandler.dump_traceback_later(240, exit=True)` am Anfang (ein Haenger wird rot mit Stapelausgabe, statt bis zur Zeitgrenze zu warten), dazu je Dialog ein `after(30000, ...)`-Schliessen wie im Linux-Kind.
7. Statische Wache in derselben Datei: Windows-Liste in `ci_tests.sh` enthaelt die Datei; `build.yml` enthaelt den Schritt "Dialogtest Warntext (macOS)" mit genau dieser `if`-Zeile, `timeout-minutes: 5` und diesem Aufruf.
8. Letzte Ausgabezeile: `Dialog prozessintern: <n> Faelle, Plattform <sys.platform>, Bildschirm echt <w>x<h>` (fuer den Bericht, Windows/macOS-Zaehlung).
9. Docstring von `test_dialog_warntext.py` ("Windows/macOS: nicht geprueft") nach dem Bau anpassen (E1).

#### 8. Kontrollfehler (Vorschlag; vor dem Bau festgelegt, im Bauauftrag einzeln belegen)

| Nr | Kontrollfehler (Wegwerf-Kopie) | muss rot werden |
|---|---|---|
| KF-102a | Datei aus der Windows-Liste nehmen | statische Wache 5.3 Nr. 7 |
| KF-102b | macOS-Schritt entfernen oder `if` auf `runner.os == 'Linux'` | statische Wache |
| KF-102c | `continue-on-error: true` am Schritt | `test_workflow_0632.test_kein_macos_neustart` und `test_wiederholung_nur_in_netz_schritten` - **belegt** auf N11-Kopie (`belege_fg102/kf_continue_on_error_test_workflow_0632.log`) |
| KF-102d | `timeout-minutes` am Schritt entfernen | statische Wache |
| KF-D10a | `@unittest.skipUnless(sys.platform == "linux", ...)` an der Klasse | statische Pruefung "kein skip" (5.3 Nr. 2); Zaehlpruefung allein faengt das **nicht** (Uebersprungenes zaehlt in "Ran N") |
| K1-K5 (Vorbau) | Hoehe nicht begrenzt; Knopfzeile nach dem Textfeld; `default="yes"`; Escape ohne Wirkung; nur erster Absatz | prozessinterne Datei unter Linux (Xvfb 1920x1080, nachgestellte Groesse) |
| KF-D1b, D3c, D3e, D5b, D6b, D7a (Testplan D10) | feste Textkopie; Escape nur am Knopf; Return fest auf "Ja"; Mausrad abgefangen (`<MouseWheel>` **und** `<Button-5>` -> "break"); `minsize(width, 120)`; feste Schrift Arial 12 | dito |
| KF-102e | Bildschirm-Ersatz wirkungslos (Ersatz an `UpdateDialog` statt `LongQuestionDialog`) | Pruefung "Fenster <= nachgestellter Bildschirm minus Raender" bzw. "Bildschirm im Dialog == Sollgroesse" (vermutet rot bei Sehr gross 1280x720; im Bau zu belegen, sonst Test nachschaerfen) |

Nachweis Windows/macOS: Job-Logs der drei Probelaeufe mit der Schlusszeile 5.3 Nr. 8 (n Faelle, Plattform, echter Bildschirm).


## Anhang D: FG-103, Diff Variante B und Tests (zu Frage 9)
Quelle: `antraege/belege_fg103/fg103_zerlegung.diff` (gegen `version-0632-n12` `180789b`); Tests aus `antraege/FG-103_Antrag.md` Abschnitt 7.

```diff
--- a/fisi_pruefung.py
+++ b/fisi_pruefung.py
@@ -116,12 +116,19 @@
 _CAPITAL_EXAMPLE = re.compile(r"(?<![^\W\d_])Z\.( ?)B\.")
 
 
+# Ab 0.63.2 (FG-103): Aufzaehlungszeichen ("-", "•", "*") am Zeilenanfang
+# nur, wenn Leerraum oder das Zeilenende folgt. Bis 0.63.1 fiel auch das
+# "-" einer Option weg ("1. -c 1 schickt ..." wurde "c 1 schickt ...",
+# ebenso "-mtime", "-rw-r-----", "-rw-r--r--").
+_BULLET = re.compile(r"^[-•*]+(?=\s|$)")
+
+
 def criteria(text):
     """Bewertungskriterien aus einer Musterloesung: jeder Satz bzw. jede
     Aufzaehlungszeile ein Kriterium."""
     items = []
     for line in text.split("\n"):
-        line = line.strip().lstrip("-•*").strip()
+        line = _BULLET.sub("", line.strip()).strip()
         if not line:
             continue
         protected = _CAPITAL_EXAMPLE.sub(lambda m: "Z\x02" + m.group(1) + "B\x02", line)
```

#### 7. Tests und Kontrollfehler (Vorschlag fuer B; vor dem Bau festgelegt)

Neue Datei `test_kriterien_fg103.py` (ungeschuetzt, ohne Fenster):
- T1: Fuer die 4 Teilaufgaben ist das erste Kriterium genau der erste Satz der Loesungszeile ohne Teilaufgaben-Nummer und beginnt mit `-c 1 schickt`, `-mtime zählt`, `-rw-r----- = 640`, `-rw-r--r-- ist`.
- T2: Ueber alle AP1/AP2-Aufgaben: Gegenueber der alten Regel (im Test als Hilfsfunktion `lstrip("-•*")` nachgebaut) unterscheiden sich **genau diese 4** Teilaufgaben, jeweils nur durch das fuehrende `-` eines Kriteriums; Kriterienzahl je Teilaufgabe ueberall gleich (zusaetzlich bleibt `test_inhalte_zb.KRITERIEN_HASH` gruen).
- T3: Aufzaehlungen: `"- x"`, `"• x"`, `"* x"`, `"-\tx"` werden zu `"x"`; `"-"`, `"---"` wie bisher; `"--privileged a."`, `"*/15 b."` behalten ihr Zeichen.

| Nr | Kontrollfehler (Wegwerf-Kopie) | muss rot werden |
|---|---|---|
| KF-103a | alte Zeile `lstrip("-•*")` zurueck | T1, T2 |
| KF-103b | `_BULLET = re.compile(r"^[-•*]+")` (ohne Blick auf Leerraum) | T1, T2, T3 |
| KF-103c | `_BULLET = re.compile(r"^-+(?=\s|$)")` (nur Minus) | T3 (`"• x"`, `"* x"`) und `test_inhalte_zb` falls betroffen |
| KF-103d | `_BULLET = re.compile(r"^[-•*]+(?=\S)")` (verkehrt) | T1, T2, T3 und FG-87-Test `"- Z. B. ..."` |
| KF-103e | in einer Inhaltskopie eine weitere Loesungszeile `"2. -x ..."` ergaenzen | T2 (Liste nicht mehr genau 4) |

Dazu: Merge-Tor nach dem Merge (Fingerabdruecke gleich wie davor), Bestandstests `test_inhalte_zb.py`, `test_inhalte_0631.py`, `test_inhalte_0632.py` und die uebrigen Pruefungs-Tests im Teil "rest" gruen.


## Anhang E: „z. B.“ im VLSM-Text, Diffs (zu Frage 14)
Quelle: `n8/Vorschlag_VLSM_zB.md`.

#### Diff 1: fisi_lernen.py (geschuetzt, FG noetig)
```diff
     text = ("Teile das Netz %s nach VLSM auf (größtes Netz zuerst, lückenlos ab der "
-            "ersten Adresse). Gib je Abteilung Netzadresse/Präfix an, z.B. "
+            "ersten Adresse). Gib je Abteilung Netzadresse/Präfix an, z. B. "
             "192.168.1.0/26." % base)
```

#### Diff 2: test_rechenweg.py, TrainerTest.ERSETZEN (eine Zeile, Wortlaut-Aenderung erklaert)
```diff
         ("2. Den längsten Block aufeinanderfolgender Nullblöcke (mindestens zwei) durch "
          "'::' ersetzen, bei Gleichstand den ersten.",
          "2. Die längste Folge von Nullblöcken (mindestens zwei) durch '::' ersetzen, "
          "bei Gleichstand die erste.", "1.19"),
+        # ab 0.63.2 (N8-F7): "z. B." mit Leerzeichen im VLSM-Aufgabentext
+        ("Präfix an, z.B. 192.168.1.0/26.", "Präfix an, z. B. 192.168.1.0/26.", "N8-F7"),
     ]
```
Belegt: `trainer:vlsm|...` steht in `pruefung/rechenweg_basis_0622.json` (Arten von
`rt.ALTE_ARTEN`). Belegt in einer Scratch-Kopie (e0f9c7e + N8-fisi_core/fisi_sync + Diff 1 + Diff 2): `test_rechenweg.py` 37 Tests OK.


## Anhang F: Tippflächen der Auswahlknöpfe, zwei Varianten (zu Frage 6)
Quelle: `n9/antrag_bj04_sichtbar.diff` (V1) und `n9/antrag_bj04_unsichtbar.diff` (V2).

#### V1 sichtbar
```diff
diff --git a/mobile/src/ui.py b/mobile/src/ui.py
index eb4e7aa..de96438 100644
--- a/mobile/src/ui.py
+++ b/mobile/src/ui.py
@@ -388,7 +388,7 @@ class PillGroup(ft.Stack):
         self.current = initial
         self.pills = []
         self.semantics = []
-        height = grow(36)
+        height = max(48, grow(36))   # B-J-04 Variante sichtbar
         for index, (_value, caption) in enumerate(options):
             pill = ft.Container(
                 content=ft.Text(caption, size=13, weight=ft.FontWeight.BOLD),
diff --git a/test_anzeige_handy.py b/test_anzeige_handy.py
index 7111084..4011f53 100644
--- a/test_anzeige_handy.py
+++ b/test_anzeige_handy.py
@@ -421,7 +421,8 @@ class PillGroupTest(unittest.TestCase):
         self.assertTrue(all(item.tight for item in pills.row.controls))
         for sem, pill in zip(pills.semantics, pills.pills):
             self.assertIs(sem.content, pill)
-            self.assertEqual(pill.height, ui.grow(36))     # Pille selbst wie bisher
+            # Ab 0.63.2 (B-J-04, Variante sichtbar): Pille mindestens 48 dp
+            self.assertEqual(pill.height, max(48, ui.grow(36)))
         self.assertEqual([item.selected for item in pills.semantics],
                          [False, False, True, False, False])
         self.assertTrue(all(item.button for item in pills.semantics))
@@ -439,7 +440,8 @@ class PillGroupTest(unittest.TestCase):
         pills = ui.PillGroup(self.OPTIONEN, initial=2)
         self.assertFalse(pills.row.wrap)
         self.assertEqual(pills.row.scroll, ft.ScrollMode.HIDDEN)
-        self.assertEqual(pills.height, ui.grow(36))
+        self.assertEqual(pills.height, max(48, ui.grow(36)))   # B-J-04
+        self.assertTrue(all(pill.height == pills.height for pill in pills.pills))
         self.assertEqual(pills.controls, [pills.mask, pills.hint])
         self.assertEqual(pills.hint.tooltip, "Weitere Einträge")
 
```

#### V2 unsichtbar
```diff
diff --git a/mobile/src/ui.py b/mobile/src/ui.py
index eb4e7aa..b5ab55a 100644
--- a/mobile/src/ui.py
+++ b/mobile/src/ui.py
@@ -388,16 +388,20 @@ class PillGroup(ft.Stack):
         self.current = initial
         self.pills = []
         self.semantics = []
-        height = grow(36)
+        height = max(48, grow(36))   # B-J-04 Variante unsichtbar: Tippflaeche
+        sichtbar = grow(36)          # Pille selbst wie bisher
         for index, (_value, caption) in enumerate(options):
             pill = ft.Container(
                 content=ft.Text(caption, size=13, weight=ft.FontWeight.BOLD),
-                height=height, border_radius=height // 2, alignment=ft.Alignment.CENTER,
-                padding=ft.Padding.symmetric(horizontal=16), ink=True,
-                on_click=lambda _e, i=index: self.select(i))
+                height=sichtbar, border_radius=sichtbar // 2, alignment=ft.Alignment.CENTER,
+                padding=ft.Padding.symmetric(horizontal=16))
+            # nur die Tippflaeche nimmt das Tippen an (ein Knoten fuer TalkBack)
+            tipp = ft.Container(content=pill, height=height, alignment=ft.Alignment.CENTER,
+                                border_radius=sichtbar // 2, ink=True,
+                                on_click=lambda _e, i=index: self.select(i))
             self.pills.append(pill)
             # Ab 0.56: TalkBack sagt "Schaltflaeche" und ob die Pille gewaehlt ist
-            self.semantics.append(ft.Semantics(content=pill, button=True, selected=False))
+            self.semantics.append(ft.Semantics(content=tipp, button=True, selected=False))
         # Geschaetzte Breiten (fett, 13 px: etwa 7,6 px je Zeichen)
         self._widths = [32 + 7.6 * FONT_FACTOR[0] * len(str(caption))
                         for _v, caption in options]
diff --git a/test_anzeige_handy.py b/test_anzeige_handy.py
index 7111084..f28e30f 100644
--- a/test_anzeige_handy.py
+++ b/test_anzeige_handy.py
@@ -420,7 +420,12 @@ class PillGroupTest(unittest.TestCase):
                          [[sem] for sem in pills.semantics])
         self.assertTrue(all(item.tight for item in pills.row.controls))
         for sem, pill in zip(pills.semantics, pills.pills):
-            self.assertIs(sem.content, pill)
+            # Ab 0.63.2 (B-J-04, Variante unsichtbar): Tippflaeche mindestens
+            # 48 dp um die Pille, nur sie nimmt das Tippen an
+            self.assertIs(sem.content.content, pill)
+            self.assertEqual(sem.content.height, max(48, ui.grow(36)))
+            self.assertIsNotNone(sem.content.on_click)
+            self.assertIsNone(pill.on_click)
             self.assertEqual(pill.height, ui.grow(36))     # Pille selbst wie bisher
         self.assertEqual([item.selected for item in pills.semantics],
                          [False, False, True, False, False])
@@ -439,7 +444,8 @@ class PillGroupTest(unittest.TestCase):
         pills = ui.PillGroup(self.OPTIONEN, initial=2)
         self.assertFalse(pills.row.wrap)
         self.assertEqual(pills.row.scroll, ft.ScrollMode.HIDDEN)
-        self.assertEqual(pills.height, ui.grow(36))
+        self.assertEqual(pills.height, max(48, ui.grow(36)))   # B-J-04 Tippflaeche
+        self.assertTrue(all(pill.height == ui.grow(36) for pill in pills.pills))
         self.assertEqual(pills.controls, [pills.mask, pills.hint])
         self.assertEqual(pills.hint.tooltip, "Weitere Einträge")
 
```

## Anhang G: Spielansichten 160/200 % am Handy (zu Frage 7)
Quelle: `n9/vorschlag_spiel200.diff` (gegen `72afbe1`; nutzt `ui.large()` und `ui.large_grow()` aus N9).

```diff
diff --git a/mobile/src/spiel.py b/mobile/src/spiel.py
index 847f9b2..e72059d 100644
--- a/mobile/src/spiel.py
+++ b/mobile/src/spiel.py
@@ -1755,6 +1755,17 @@ def market_box(lines):
         border=ft.Border.all(1, mix(C["accent"], C["card"], 0.45)))
 
 
+def _stack_large(controls, spacing=8, **kwargs):
+    """Ab 0.63.2 (B-J-06): was sonst nebeneinander steht, ab 160 %
+    untereinander in voller Breite (wie main.tile_row)."""
+    for control in controls:
+        if getattr(control, "expand", None):
+            control.expand = None
+    kwargs.pop("vertical_alignment", None)
+    return ft.Column(controls, spacing=spacing, tight=True,
+                     horizontal_alignment=ft.CrossAxisAlignment.STRETCH)
+
+
 class GameScreen:
     """Seite "Spiel" der Handy-App (gleiche Schnittstelle wie Screen in
     main.py: crumbs, root, on_show)."""
@@ -2088,7 +2099,7 @@ class GameScreen:
                 "Firma öffnen" if state.firm else "Firma gründen", self.open_firm,
                 kind="ghost" if state.firm else "primary", height=38))
         profile = ui.Card("Spielfigur", [
-            ft.Row([
+            (_stack_large if ui.large() else ft.Row)([
                 avatar(state.profile["aussehen"], 84),
                 ft.Column([
                     ui.text(state.profile["name"], size=22, weight=ft.FontWeight.BOLD),
@@ -2381,7 +2392,7 @@ class GameScreen:
                     ft.Row([ui.GradientButton(
                         "Karteikarten zu %s" % fg.TOPIC_SHORT[key],
                         lambda _e: self._open_cards(fg.TOPIC_CAT[key], key), kind="ghost",
-                        height=38)]),
+                        height=38, expand=ui.large() or None)]),
                 ], spacing=8, tight=True),
                 bgcolor=mix(C["card"], C["yellow"], 0.12), border_radius=14, padding=14,
                 border=ft.Border.all(1, mix(C["yellow"], C["card"], 0.35))))
@@ -2422,7 +2433,8 @@ class GameScreen:
         self.btn_defer = ui.GradientButton("Verschieben", self._defer, kind="ghost",
                                            expand=True)
         self.buttons = ft.Column([
-            ft.Row([self.btn_submit, self.btn_help], spacing=10),
+            (_stack_large if ui.large() else ft.Row)([self.btn_submit, self.btn_help],
+                                                     spacing=10),
             ft.Row([self.btn_defer]),
             ui.text("Ohne Hilfe gibt es %d %% Bonus."
                     % round(fg.GAME["balancing"]["bonus_ohne_hilfe"] * 100),
@@ -2767,8 +2779,11 @@ class GameScreen:
             ("Verdient", euro(stats["verdient"]), "alle Einnahmen"),
         ]
         grid = []
-        for index in range(0, len(tiles), 2):
-            grid.append(ft.Row([self._stat_tile(*tile) for tile in tiles[index:index + 2]],
+        # Ab 0.63.2 (B-J-06): ab 160 % eine Kachel je Zeile (sonst brachen die
+        # Titel mitten im Wort um: "ZWISCHENFÄ/LLE", "KUNDENPRO/JEKTE")
+        per_row = 1 if ui.large() else 2
+        for index in range(0, len(tiles), per_row):
+            grid.append(ft.Row([self._stat_tile(*tile) for tile in tiles[index:index + per_row]],
                                spacing=8))
         controls = [tabs, ui.Card("Rückblick", grid, accent=C["accent2"],
                             subtitle="%s · Tag %d · %s" % (
@@ -3422,33 +3437,42 @@ class GameScreen:
         for row in fg.skill_bars(item):
             color = CATEGORY_COLOR[fg.CAT_NAME[row["cat"]]]
             opened = self._cat_open(staff_id, row["cat"])
+            name = ft.Row([
+                ft.Icon(ft.Icons.EXPAND_MORE if opened else ft.Icons.CHEVRON_RIGHT,
+                        size=16, color=color),
+                ui.text(row["name"], size=12, weight=ft.FontWeight.BOLD, color=color)],
+                spacing=2, tight=True)
+            bar = [ft.Container(_skill_bar(row["anteil"], color, 10), expand=True),
+                   ft.Container(ui.text(str(row["wert"]), size=12, weight=ft.FontWeight.BOLD,
+                                        text_align=ft.TextAlign.RIGHT),
+                                width=ui.large_grow(30))]
+            # Ab 0.63.2 (B-J-06): ab 160 % Name ueber Balken und Wert
+            line = (ft.Column([name, ft.Row(bar, spacing=6,
+                                            vertical_alignment=ft.CrossAxisAlignment.CENTER)],
+                              spacing=2, tight=True) if ui.large() else
+                    ft.Row([ft.Container(name, width=110)] + bar,
+                           spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER))
             rows.append(ui.as_button(ft.Container(
-                content=ft.Row([
-                    ft.Container(ft.Row([
-                        ft.Icon(ft.Icons.EXPAND_MORE if opened else ft.Icons.CHEVRON_RIGHT,
-                                size=16, color=color),
-                        ui.text(row["name"], size=12, weight=ft.FontWeight.BOLD, color=color)],
-                        spacing=2, tight=True), width=110),
-                    ft.Container(_skill_bar(row["anteil"], color, 10), expand=True),
-                    ft.Container(ui.text(str(row["wert"]), size=12, weight=ft.FontWeight.BOLD,
-                                         text_align=ft.TextAlign.RIGHT), width=30)],
-                    spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER),
+                content=line,
                 padding=ft.Padding.symmetric(vertical=3), ink=True,
                 on_click=lambda _e, key=row["cat"]: self._toggle_cat(staff_id, key))))
             if not opened:
                 continue
             for topic in row["themen"]:
-                rows.append(ft.Container(ft.Row([
-                    ft.Container(ui.text(topic["name"], size=11, color=C["text_dim"]),
-                                 width=92),
-                    ft.Container(_skill_bar(topic["anteil"], mix(color, C["card_alt"], 0.35),
-                                            6), expand=True),
-                    ft.Container(ui.text(str(topic["wert"]), size=11,
-                                         color=C["yellow"] if topic["grenze"]
-                                         else C["text_soft"],
-                                         text_align=ft.TextAlign.RIGHT), width=30)],
-                    spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER),
-                    padding=ft.Padding.only(left=18)))
+                label = ui.text(topic["name"], size=11, color=C["text_dim"])
+                bar = [ft.Container(_skill_bar(topic["anteil"], mix(color, C["card_alt"], 0.35),
+                                               6), expand=True),
+                       ft.Container(ui.text(str(topic["wert"]), size=11,
+                                            color=C["yellow"] if topic["grenze"]
+                                            else C["text_soft"],
+                                            text_align=ft.TextAlign.RIGHT),
+                                    width=ui.large_grow(30))]
+                line = (ft.Column([label, ft.Row(bar, spacing=6,
+                                                 vertical_alignment=ft.CrossAxisAlignment.CENTER)],
+                                  spacing=2, tight=True) if ui.large() else
+                        ft.Row([ft.Container(label, width=92)] + bar,
+                               spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER))
+                rows.append(ft.Container(line, padding=ft.Padding.only(left=18)))
         return ft.Column(rows, spacing=2, tight=True)
 
     def _person_box(self, controls):
@@ -3485,7 +3509,7 @@ class GameScreen:
                     state.branch["name"] if there else fg.firm_rules()["gebaeude"]["name"]),
                     size=12, color=C["purple"] if there else C["green"]),
                     ft.Row([move])]
-            parts.append(ft.Row([
+            parts.append((_stack_large if ui.large() else ft.Row)([
                 ui.GradientButton("Weiterbilden", lambda _e, i=item["id"]: self._pick_training(i),
                                   kind="ghost", height=36, expand=True),
                 ui.GradientButton("Themen", lambda _e, i=item["id"]: self._toggle_topics(i),
@@ -4750,7 +4774,7 @@ class GameScreen:
                                 [self.farm_board, self.help_box, self.result_box],
                                 accent=C["accent"]))
         self.btn_help = ui.GradientButton("Hilfe", self._show_help, kind="ghost")
-        self.buttons = ft.Column([ft.Row([
+        self.buttons = ft.Column([(_stack_large if ui.large() else ft.Row)([
             ui.GradientButton("Lösung einreichen", self._farm_submit, expand=True),
             self.btn_help], spacing=10)], spacing=10, tight=True)
         controls.append(self.buttons)
```
