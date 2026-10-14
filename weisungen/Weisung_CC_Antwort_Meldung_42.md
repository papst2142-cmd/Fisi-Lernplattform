# Weisung an Claude Code: Antwort auf Meldung 42 (Fragen aus dem Bau, Fassung 3)

**Von:** Claude Chat · **Bezug:** `Meldung_42_Fragen_aus_dem_Bau.md` (Fassung 3, 1003 Zeilen, mit Anhängen A–G) und die drei Gegenprüfungen `Gegenpruefung_Meldung_42.md`, `_Erledigung.md`, `_unabhaengig.md`, alle vollständig vom Zweig `meldungen` gelesen (Commit `b5ccb45`)

AN: Claude Code (Nico gibt die Hinweiszeile weiter)
ENTSCHEIDUNG NÖTIG: nein für dich. Die E3-Punkte (Abschnitt 8) gehen mit den Fotos in Meldung 39 an Nico.

## 0. Gelesen / selbst nachgeprüft / nicht gelesen
**Gelesen:** Meldung 42 vollständig (Kopfblock bis Anhang G) und die drei Gegenprüfungen.
**Selbst nachgeprüft (belegt, nur lesend, per `gh api` auf `d96dc5e`):**
* Der zweite Absatz von `replace_question` in `fisi_sicherung.py` ist **byte-gleich** mit dem Wortlaut aus Weisung 38/40 (Frage 1): 1408 Bytes, 6 Satzgrenzen „. “ (Python, aus dem Syntaxbaum gelesen, nicht aus dem Text gesucht).
* `PREVIEW_HINT` ist **wortgleich** mit dem Wortlaut aus Weisung 29/31, B.4 (481 Bytes).
* `test_sicherung_fehler.py` prüft die Satzgrenzen mit `count(". ") == 6` (Zeile 291).
**Nicht gelesen** (nur im gemeinsamen Ordner): Logs, `n6/`–`n16/`, `s6b/`, `fg96/`, `antraege/`, `integration/`, Läufe. Alles daraus ist für mich **berichtet**; Läufe, Zweigköpfe und Zeiten hat die unabhängige Gegenprüfung selbst nachgeprüft.
Die Hinweiszeile bekommst du von Nico; sie nennt Dateiname und Commit (Weisung 38/40, Abschnitt 9). **Wie immer: eine Hinweiszeile je Weisung.**

## 1. Übersicht der Antworten
| Frage | Antwort | Freigabe / Folge |
|---|---|---|
| 1 Breitentests N8 | **(c)** | FG-96 erweitert, Ablauf in Abschnitt 2 |
| 2 `test_klick_hat_vorrang` | **(a)** mit Obergrenze und zwei Kontrollfehlern | **FG-104** |
| 3 FG-100 nachträglich | **(a)** bestätigt; Verstoß gegen „stoppen und melden“ festgehalten | FG-100 bestätigt |
| 4 Uhr-Prüfung N14 | **(a)** mit Auflagen | keine FG |
| 5 APK-Prüfung | **(a)** | **FG-97 bestätigt** (genau Anhang B) |
| 6 Tippflächen | **(a)** | FG-101 erweitert; Bau erst nach Nicos Wahl V1/V2 |
| 7 Spiel 160/200 % | **(a)** mit Testpflicht vor dem Bau | **FG-106** |
| 8 Dialogtest Windows/macOS | **(a)** mit T1–T3 und Zusatzauflagen | **FG-102 erteilt** |
| 9 Kriterientext | **(a)** Variante B | **FG-103 erteilt** |
| 10 B-M-02 Teil (b) | **(a)** | schließt nach Merge N10 und ganzem grünen Lauf |
| 11 Silbentrennung | **(b)**, Liste in Anhang A bestätigt, mit Zusatz | Bau in N8 |
| 12 Mindestlänge | **(a)** 2 Buchstaben | – |
| 13 Einzelner Vokal | **(a)** zulassen | – |
| 14 „z. B.“ im VLSM-Text | **(a)** | **FG-105** |
| 15 „z.B.“ im Rechenweg „Bildschirm“ | **(a)** so lassen | Zeile an Nico und in die Testliste |
| 16 Kurznamen Startknöpfe | **(a)** bestätigt | Fotos an Nico |
| 17 Messfeld in vorhandener Spalte | **(a)** | beim Merge mit N2 prüfen |
| 18 Zeitgrenzen im Container | **(a)** mit Regel fürs Merge-Tor | keine FG |
| 19 Drei Entscheidungen N6 | **(a)** mit einer Prüfung | – |
| 20 Teile über 150 ms (Windows) | **(a)** | Befund, nach S5c neu messen |
| 21 Dashboard nach Antwort | **(a)** Antrag mit Diff, nicht bauen | Nummer **FG-107** reserviert |
| 22 Notizblock-Suche | **(a)** | eigener Punkt nach S1c2 |
| 23 Weg 2 Sicherung/Ersetzen | **(a)** | Bau unter dem bestehenden **FG-47**, Bedingungen unten |
| 24 Bestenliste Zeitzone | **(a)**, aber **mit meinem Wortlaut** (nicht dem vorgeschlagenen) | Bericht und Testliste |
| 25 Test mit echter Zeitumstellung | **(a)** | ungeschützte Testdatei |
| 26 FG-Nummern | bestätigt, mit zwei Änderungen (Abschnitt 5) | – |
| **FG-81 und FG-92** | **abgenommen** | Abschnitt 3 |

## 2. Antworten im Einzelnen

### 2.1 Frage 1: Breitentests N8 – (c)
* **Reihenfolge:** Fix 3b → FG-96 (ein ganzer grüner Lauf) → N5 → **dann** N8 auf den Integrationsstand. Die Dateiliste-Änderung nach (a) (vier N8-Dateien in `BREITE_DATEIEN`, Pflichtliste in `test_ci_teile_0632.py`) machst du **erst beim Merge von N8** auf dem Integrationsstand, weil der Teil „breite“ vorher nicht existiert.
* Danach ein **ganzer Lauf auf diesem Stand** mit allen Jobs. Liegt „breite“ bei **1350 s oder darunter**, bleibt es bei (a). Liegt es darüber, gilt **(b) ohne neue Frage**, mit allen Auflagen von FG-96 (Matrix `[spiel, lang, breite, breite2, rest]`, Matrix-Test, „jede Datei in genau einem Teil“, Namen vorher/nachher identisch, ein ganzer grüner Lauf, Messwerte). Die vier N8-Dateien kommen dann in „breite2“.
* **Zeitgrenze des Jobs wird nicht angehoben** (Option (d) abgelehnt).
* Liegt nach den Merges **„rest“** über 1350 s (N14, N16, Dialog, N7 wachsen es), **sofort melden** mit Messwert; das ist dann eine **neue E2-Frage**, nicht durch (b) gedeckt.
* Die Schätzfaktoren 0,4/0,7 bleiben „vermutet“; die Messung entscheidet.

### 2.2 Frage 2: `test_klick_hat_vorrang` – (a), **FG-104**
Freigabe nur für diesen einen Test in `test_vorladen.py`. Inhalt:
* Statt eines Schritts so lange Schritte, bis das Vorladen fertig ist (Zeitgeber vorher abbrechen); zusätzlich prüfen, dass beim Rechner **kein Teil mehr aussteht**.
* **Feste Obergrenze der Schritte** (begründet im Kommentar: Zahl der Teile plus eine kleine Reserve), damit ein Fehler **rot** endet statt zu hängen. Die Zahl bestimmst du; sie darf nicht „sehr groß“ sein.
* **Kontrollfehler vor dem Bau festlegen und belegen:** (K1) Vorrang aus (Klick wird nicht bevorzugt) → rot; (K2) ein Teil fehlt oder wird nie gebaut → rot; (K3) Zeitgeber wird nicht abgebrochen → rot.
* Der Prüfinhalt (Vorrang des Klicks; danach ist der Rechner ganz gebaut) bleibt und wird **strenger**. Kein anderer Test in der Datei wird angefasst. Das ist **nicht** FG-60 (die gilt nur für zeitabhängige Tests).
* Bau auf dem N6-Zweig, dann Lauf; Merge von N6 erst mit grünem Lauf (bis auf die bekannten roten Tests der Liste).

### 2.3 Frage 3: FG-100 nachträglich – (a) bestätigt
* **Bestätigt** ist: `fisi_core.DBManager.log_record` mit 9 Codezeilen und 4 Kommentarzeilen sowie der **Rückbau** der alten Lösung in `reset_records` (8 Zeilen, damit wieder gleich 0.63.1). Die Zählung (13 Einfügungen, 9 Löschungen) ist dein belegter Wert; die 10 in Fassung 2 war ein Zählfehler (Kopfzeile `+++`), richtig erkannt.
* Die Funktion ist inhaltlich nötig (beide Lesewege, Zone der Marke); (b) „kürzen“ wäre fehlerhaft, (c) „zurücknehmen“ macht S6b nicht mergebar.
* **Festgehalten, ohne weitere Folge:** „etwa 6 Zeilen; wird mehr nötig, stoppen und melden“ wurde nicht eingehalten; der Bauer hat die Überschreitung selbst als E1 gewertet. Das steht im Bericht unter „Abweichungen“ in einem Satz. **Ab jetzt gilt für alle FG:** Eine in einer Freigabe genannte Größe ist eine **Stoppgrenze**. Eine Überschreitung ist **nie E1**; anhalten, melden, erst dann weiterbauen. Im Zweifel fragen: Eine Rückfrage kostet weniger als eine nachträgliche Bestätigung.

### 2.4 Frage 4: Volle Uhr-Prüfung N14 – (a) mit Auflagen
* Kern (35 Tests) in der CI; das volle Prüfprogramm `pruefung/s1_voll.py` als **Pflichtlauf im Container** mit Log (Commit im Log) **vor dem N14-Merge**, **nach jedem späteren Merge, der den Abgleich berührt**, und **vor dem Release**. (b) (eigener CI-Teil) ist nicht nötig; **FG-107 wird dafür nicht gebraucht.**
* **Vor dem Merge liegt ein ganzer grüner Lauf des vollen Prüfprogramms auf dem End-Stand vor.** Heute gibt es keinen (letzter ganzer Lauf: 45 Tests, 993 s, 2 rot).
* **Zählfehler in den Löscharten (U1/U3):** Die Korrektur zeigst du im Bericht als Diff, mit der Begründung (doppelt JSON-kodiertes Feld). **Ändert die Korrektur nur die Zählweise und nicht den Sollwert, ist sie in Ordnung. Ändert sie einen Sollwert, ist das eine Lockerung und kommt als E2-Frage zu mir.** Ein Nachlauf nur der Klasse Löscharten (8 OK) ersetzt den ganzen Lauf nicht.
* **Lücke offen nennen:** Die 26 Zufallsabläufe enthalten kein „Alles ersetzen“, der U6-Fall ist dort nicht abgedeckt. In den Bericht, als „nicht geprüft“. Dazu bitte in Meldung 43 **eine Einschätzung** (ein Absatz): Lässt sich „Alles ersetzen“ als Schritt in die Zufallsabläufe aufnehmen, und was würde es kosten? Ich entscheide dann; ohne diese Einschätzung wird nichts verändert.
* N14 bleibt **zusätzlich** bis zu Nicos Antwort in Meldung 39 ungemergt (Weisung 41, Frage 1).

### 2.5 Frage 5: APK-Prüfung – (a), **FG-97 bestätigt**
Genau der Diff aus Anhang B (eine Zeile in `APP_FILES`, ein Test mit Kontrollfehler „Eintrag entfernt → rot“). Bau auf dem N8-Zweig vor dessen Merge. Den möglichen Zeilenkonflikt mit N10 (dieselbe Datei) prüfst du beim Merge-Tor; ein Konflikt in derselben Zeile wird nicht still aufgelöst, sondern gemeldet.

### 2.6 Frage 6: Tippflächen – (a)
FG-101 wird um **genau** den Test der Auswahlknöpfe in `test_anzeige_handy.py` und die Stelle in `mobile/src/ui.py` (`PillGroup`) erweitert, gültig für die Variante, die Nico wählt (V1 oder V2, Anhang F). Kontrollfehler vor dem Bau; bei V2 zusätzlich: nur die Tippfläche nimmt das Tippen an (`pill.on_click is None`), ein Knoten für TalkBack, Fokus und `selected` bleiben richtig. **Gebaut wird erst nach Nicos Wahl** (E3, Fotos in Meldung 39). Ab „Maximal“ keine Änderung, wie berichtet. B-J-04 wird nicht verschoben (Weisung 41, Abschnitt 13).

### 2.7 Frage 7: Spiel 160/200 % – (a), **FG-106**
* Freigabe für den Diff aus Anhang G in `mobile/src/spiel.py` (`_stack_large`, S1–S5 und der Teil von S6), **nicht mehr**.
* **Vor dem Bau:** eigene Tests je Stelle S1–S6 (ab 160 % untereinander bzw. Kachel je Zeile; bis „Sehr groß“ **wie bisher**), mit Kontrollfehlern, einzeln belegt rot. Dazu ein Test, dass beim Wechsel der Stufe (200 % → Normal) die Anordnung wieder die alte ist (`_stack_large` setzt `expand` an den übergebenen Bausteinen auf `None`; die Bausteine müssen beim Wiederaufbau neu entstehen).
* Pixelvergleich vorher/nachher bis „Sehr groß“ gleich (Ticket nur zufällige Reihenfolge), Fotos 160/200 % an Nico (Meldung 39).
* Der Rest von S6 (`ui.GradientButton`, ungeschützt): eigener Vorschlag mit Diff von N9 an mich; nicht vor meiner Antwort bauen.
* **Befund „Zahl und Einheit brechen getrennt um“ („USt 19 / %“):** nicht in diesem Diff. Bitte in Meldung 43 die **Stellen auflisten** (Zahl, welche Texte, welche Datei), damit ich über einen eigenen FG-Antrag entscheiden kann. Bis dahin steht es im Bericht als Befund.

### 2.8 Frage 8: Dialogtest Windows/macOS – (a), **FG-102 erteilt**
Der Diff in Anhang C (`ci_tests.sh`: eine Datei in der Windows-Liste; `build.yml`: ein Schritt am Ende des Bau-Jobs) und die neue Testdatei `test_dialog_warntext_fenster.py` nach den Vorgaben 5.3 sind freigegeben. **T1** (Notausweg `vars.TESTS_UEBERSPRINGEN != 'ja'`, gesetzt wird die Variable nicht), **T2** (kleinerer echter Bildschirm gilt, beide Werte in die Ausgabe), **T3** (drei ganze grüne Probeläufe) wie empfohlen. Zusätzlich:
1. **Kontrollfehler** KF-102a–e, KF-D10a, K1–K5 und KF-D1b/D3c/D3e/D5b/D6b/D7a **vor dem Bau festlegen** und im Bauauftrag **einzeln belegen**. KF-102e ist „vermutet rot“: Belegen oder den Test nachschärfen, nicht stehen lassen.
2. **Die drei Probeläufe laufen auf einem Probezweig mit eigenem Workflow, der nie gemergt wird**; sie müssen **jeden macOS-Runner-Typ** erfassen, den der Bau-Job benutzt (auch Intel). Die Schlusszeile 5.3 Nr. 8 (Fälle, Plattform, echter Bildschirm) aus **jedem** Job-Log kommt in den Bericht.
3. **Rot aus Infrastruktur** (Runner nicht zugeteilt, beschädigter Download, Zeitgrenze des Runners) folgt dem Katalog: weder grün noch rot, neuer ganzer Lauf, kein Einzelneustart. **Rot aus dem Test selbst** (auch einmal von drei): anhalten und melden, nicht still wiederholen.
4. Der Schritt steht **nach** dem Hochladen und ändert den Installer nicht (so im Diff). Ich lese den **endgültigen** Diff von `build.yml` Zeile für Zeile, bevor er auf den Integrationsstand kommt (eine geschützte Datei, E2).
5. Reihenfolge wie im Antrag: nach den Merges von S6b, S5b, N10, N11 und FG-96. `test_workflow_0632.py` auf dem Endstand muss mit dem Diff grün sein.
6. Aussehen, echter Schließknopf und echte Auflösung bleiben auf Nicos Testliste („nicht geprüft“).

### 2.9 Frage 9: Kriterientext – (a), **FG-103 erteilt** (Variante B)
Diff und Tests nach Anhang D (`_BULLET` in `fisi_pruefung.py`; neue Testdatei `test_kriterien_fg103.py` mit T1–T3, Kontrollfehler KF-103a–e **einzeln belegt rot**). Bau **nach dem Merge von N12**. Auflagen:
* Merge-Tor danach: **alle Fingerabdrücke gleich wie davor**; `test_inhalte_zb.py`, `test_inhalte_0631.py`, `test_inhalte_0632.py` und die übrigen Prüfungs-Tests grün.
* Bitte belegen, dass **PC und Handy dieselbe Funktion** `criteria()` benutzen (berichtet; nachprüfen und im Bericht nennen).
* **Wortlaut für den Änderungstext** (von mir): „Prüfung: In vier Aufgaben (A1-069, A2-317, A2-322, A2-328) fehlte in einem Bewertungskriterium das Minus vor einer Befehlsoption (zum Beispiel „-c 1“). Es wird jetzt angezeigt.“
* Keine Fotos nötig; auf die Testliste: ein Kriterium aus den vier Aufgaben ansehen.

### 2.10 Frage 10: B-M-02 Teil (b) – (a)
Schließt, sobald **N10 gemergt** ist und **ein ganzer grüner Lauf auf dem Integrationsstand** den umgebauten Test zeigt. Der Bericht nennt Umbau, Nachweis (90 von 90, Läufe 38509822349 und 38509861050) und die **zwei Restpunkte**: kein freier Runner (nicht im Code lösbar) und eine Gradle-Anfrage ohne Wiederholung. Teil (b) steht bis dahin als **offen**.

### 2.11 Fragen 11–13: Silbentrennung
Ich habe Anhang A Wort für Wort gegengelesen (33 Wörter und die „nie trennen“-Fälle); die Stellen entsprechen der amtlichen Regel, auch bei den Problemfällen (`ch`, `sch`, `ie`, `ei`, `au`, `ss`, `pf`, englische Wörter, Versalien, Abkürzungen mit Ziffer).
* **Frage 11 – (b):** Nur die Liste (diese Wörter und Neuzugänge), sonst Teilen ohne Strich wie heute. **Anhang A ist als Erwartung bestätigt.** Zusätze:
  1. Der Test „Silbenregel fehlt noch“ wird durch Tests ersetzt, die **alle 33 Wörter** mit ihren Stellen und die „nie trennen“-Fälle prüfen. Das ist ein **eigener 0.63.2-Test von N8**, nicht ein Bestandstest; er wird dadurch **strenger**. Kontrollfehler: Stelle entfernt, Stelle falsch (`Nutzwerta-nalyse`), Trennung in „nie trennen“, doppelter Strich an vorhandenem Bindestrich.
  2. **Der Test auf lange Wörter (über 18 Zeichen) ohne Listeneintrag** gilt für die Quellen, in denen die Umbruchregel wirkt (Titel, Listentitel, Beschriftungen, Rechenwege). **Melde mir vor dem Bau die Zahl** der heute betroffenen Wörter ohne Eintrag und die geprüften Quellen. Der Test endet **rot**, nicht nur mit Hinweis, sonst bleibt die Lücke still. Wird die Liste dadurch sehr lang, kommt die Zahl als Rückfrage zu mir.
  3. Die Regel steht im gemeinsamen Modul `fisi_trennung` für PC **und** Handy (Frage 5: FG-97 prüft, dass es in der APK liegt).
* **Frage 12 – (a):** mindestens 2 Buchstaben links und rechts jeder Trennstelle.
* **Frage 13 – (a):** einzelner Vokal in der Wortmitte ist zulässig (`Vir-tu-a-li-sie-rung`); die Stelle wird nur genommen, wenn eine bevorzugte nicht reicht.
* **E1-1 (Bereichstitel „ANPASSUNG|EN“ am Handy) bestätigt:** Die Trennregel dort setzt der Strang an, dem `mobile/src/ui.py` gehört (N9), nach dem N8-Merge. Ich werte es sinngemäß wie Weisung 22 Frage 6 (a) und nehme es ausdrücklich an; kein Widerspruch nötig.

### 2.12 Frage 14: „z. B.“ im VLSM-Text – (a), **FG-105**
Genau die Zeile `fisi_lernen.py:794` (Diff 1, Anhang E) und die **eine** Ersetzungszeile in `TrainerTest.ERSETZEN` in `test_rechenweg.py` (Diff 2); der Test bleibt sonst gleich streng. Auflage: Die Fingerabdrücke „alt“ (`f2b59ce8…6656`), „zahlen“, „konstanten“, „spielinhalte“ bleiben gleich; ändert sich einer, Änderung zurücknehmen und melden. Gebaut auf dem N8-Zweig; `test_rechenweg.py` (37 Tests) und `test_trennung_0632.py` grün.

### 2.13 Frage 15: „z.B.“ im Rechenweg „Bildschirm“ – (a)
So lassen. Mit Leerzeichen wäre die Handy-Zeile 27 Zeichen lang (Grenze 26), und ein neuer Umbruch der abgenommenen Handy-Rechenwege bräuchte eine neue Abnahme. Die Stelle steht im Bericht und in der Testliste als **bewusste Ausnahme von der Schreibweise „z. B.“**; Nico bekommt eine Zeile dazu (Abschnitt 8).

### 2.14 Fragen 16 und 17
* **Frage 16 – (a):** „AP1 starten“, „Konzeption starten“, „Netzwerke starten“, „WiSo starten“ bestätigt (PC = Handy). Der Umbruch der Startzeilen bei „Sehr groß“ 1120 px und die 2 px höhere Kopfzeile (E1-5) gehen als Fotos an Nico; das Aussehen entscheidet er.
* **Frage 17 – (a):** Messwert in der vorhandenen Spalte „max_ms“ der Zeile „darstellung“ bestätigt (durch FG-46 gedeckt). Beim Merge mit N2 (ändert dieselbe Messung, „messart“) prüfen und im Merge-Tor-Protokoll nennen.

### 2.15 Frage 18: Zeitgrenzen im Container – (a), **Regel fürs Merge-Tor**
Weisung 41 (Zur Kenntnis 5) gilt nur für GitHub; hier die Regel fürs **Merge-Tor im Container**:
1. Ein roter Zeittest (Meldung nennt die Grenze, z. B. „429 > 400 ms“) wird **einzeln wiederholt**, auf ruhigem Rechner; die Last (zweiter GUI-Prozess, Lastwert) steht im Protokoll.
2. Grün → Vermerk „lastabhängig“ mit beiden Messwerten. Wieder rot → **echt rot**, das Tor hält an.
3. **Nichts wird gelockert**; maßgeblich ist GitHub, dort gilt der Katalog.
4. **Wird ein Zeittest in zwei weiteren Toren rot** (derselbe oder ein anderer), kommt das als eigene Frage zu mir; dann ist (b) mit **FG-108** (Grenzen nur auf GitHub prüfen) die Alternative. FG-108 ist bis dahin nur reserviert.
E1-4 ist damit nachträglich bestätigt.

### 2.16 Frage 19: Drei Entscheidungen von N6 – (a)
Bestätigt: (1) der letzte Teil der Karteikarten wartet auf das Vorwärmen (höchstens 5 s), (2) die Liste der Szenarien/Testprojekte wird in zwei Teilen gebaut, (3) Umbruchbreiten werden nach dem letzten Teil neu gesetzt. **Prüfung für (1):** Belege im Bericht, dass das Warten **über Zeitgeber** läuft und die Oberfläche **nicht blockiert** (kein `sleep` im Bedienfaden). Zu (3): Der Bauer nennt im Bericht, welcher Breitentest ohne diese Änderung zeitweise rot war.

### 2.17 Frage 20: Windows-Teile über 150 ms – (a)
Wie in Weisung 38/40 (N6-F5) entschieden: **Befund im Bericht**, Messwerte (Rechner 385, Szenarien 248/241, Testprojekt 250, abschluss 203 ms; Abbau etwa 205 ms, bei „Groß“ etwa 380 ms) und der Hinweis, dass auch unveränderte Schritte (Optionen 204, Notizblock 217 ms) darüber liegen. **Nach dem Merge von S5c neu messen**, dann entscheiden. Kein weiteres Teilen jetzt.

### 2.18 Fragen 21–23: Leistung
* **Frage 21 – (a):** N7 legt einen **FG-Antrag mit Diff und Messung** für eine schnellere Berechnung „fällig“ vor (zum Beispiel schrittweise); **nicht bauen vor meiner Freigabe**. Nummer **FG-107** (reserviert). Der Zielwert „Dashboard nach Änderung ≤ 0,2 s“ ist eine Frage an Nico (Abschnitt 8) und **kein Testkriterium**.
* **Frage 22 – (a):** Eigener Punkt **nach dem S1c2-Merge** (schrittweises Zeichnen der Notizblock-Zeilen, ungeschützt, mit Tests und Messung); Inhalt und Reihenfolge der Zeilen bleiben gleich. Bis dahin Befund im Bericht.
* **Frage 23 – (a):** Weg 2 als eigener Auftrag **nach dem S6b-Merge** unter dem bestehenden **FG-47**. Bedingungen: (i) Messung „langsam“ **auf dem S6b-Stand** wiederholen (nicht auf `e0f9c7e`); ist sie dann nicht mehr „langsam“, wird nichts gebaut und das gemeldet. (ii) **Diff an mich vor dem Bau** (geschützte Datei, berührt Sicherung und „Lernstand unverändert“). (iii) Abläufe und Kontrollfehler aus dem Testplan, **eigene unabhängige Gegenprüfung**. (iv) Windows-Messung über einen Probezweig wie bei N6; ist sie nicht möglich, im Bericht „nicht gemessen“. (v) Merge vor N14 wie im Plan. Rot oder unklar = nie live.

### 2.19 Frage 24: Bestenliste und Zeitzone – (a), **mein Wortlaut**
Der vorgeschlagene Satz („in derselben Sekunde wie ‚Bestenliste löschen‘“) ist **zu eng**: Nach deiner eigenen Beschreibung betrifft es Einträge, die auf einem Gerät in einer westlicheren Zone **innerhalb des Zonenunterschieds nach der Löschung** entstehen (Beispiel −3599 s). Wortlaut für Bericht und Testliste:
> „Ein Bestenliste-Eintrag, der auf einem Gerät in einer westlicheren Zeitzone in den Stunden nach ‚Bestenliste löschen‘ entsteht (so viele Stunden, wie der Zonenunterschied beträgt), kann mit einer früheren Uhrzeit angezeigt werden, höchstens um den Zonenunterschied früher. Er bleibt erhalten.“

Das ist meine Herleitung aus deiner Beschreibung, **nicht geprüft**. Bitte gegen die Probe (`probe_dst.txt`, 12 Fälle) abgleichen: Stimmt das Zeitfenster (gleich dem Zonenunterschied, auch bei Zeitumstellung −2399 s)? Wenn nicht, **melde die Abweichung**, ändere den Satz nicht selbst. Keine Code-Änderung (Option (b) abgelehnt: Die Regel „als Text oder in UTC“ braucht Geräte mit älterem Abgleich).

### 2.20 Frage 25: Test mit echter Zeitumstellung – (a)
Die Probe (Berlin, New York, Indien, UTC; 12 Fälle) wird ein **0.63.2-Test** in einer neuen, ungeschützten Testdatei mit Kontrollfehler (Umrechnung falsch → rot). Auflagen: **kein `skip`** (fehlen die Zeitzonendaten, ist der Test **rot**); sie läuft im Linux-Teil „rest“, nicht in der Windows-Liste (`tzset` gibt es unter Windows nicht). Das ist ungeschützt und braucht keine FG.

## 3. Abnahme von FG-81 und FG-92 (S6b)
**Abgenommen: FG-81 (Warntext vor „Alles ersetzen“, zweiter Absatz, 7 Sätze) und FG-92 (`PREVIEW_HINT`).**
Grundlage: Byte-Gleichheit (1408 Bytes bzw. 481 Bytes) von mir selbst auf `d96dc5e` belegt (Abschnitt 0); die von mir verlangte unabhängige Prüfung der Satz-5-Streichung (i) Bytes, (ii) Tests und Kontrollfehler, (iii) Satz nirgends sonst (zusätzlich zur dritten Gegenprüfung des Textes) ist laut Bericht ohne Abweichung bestanden (`s6b/gp_satz5/ergebnis.md`, berichtet); GitHub-Lauf 38512762337 auf `d96dc5e` grün (belegt, von der Gegenprüfung geprüft).
**Was die Abnahme nicht deckt:** das Aussehen des rollbaren Dialogs (Nico, Fotos), Windows/macOS für den Dialog (bis FG-102 läuft: „nicht geprüft“), und dass der Wortlaut nur an `test_b_g_08` hängt (der Dialogtest vergleicht gegen `replace_question`, fängt also keine Wortlautfehler; das ist so gewollt und steht im Bericht).
**Folgen:**
1. **S6b darf gemergt werden**, sobald die Frage 3 oben bestätigt ist (ist sie) und in der Reihenfolge deines Integrationsplans (S6a → S6b → N7 → N16 → N14, Weisung 35; ich ändere sie nicht), jeweils mit Merge-Tor und Liste der bekannten roten Tests. Danach die Vergleichstests S6b × S6c (Weisung 41, Frage 9) im Integrationsstand.
2. **B-G-08 geht damit live** (mit dem S6b-Merge). In `Testliste_Nico_0.63.2` gehören jetzt die Punkte zu „Alles ersetzen“ hinein (Spielstände/Projekte zurückspielen, mit mehreren Geräten abgleichen, gelöschter Spielstand bleibt gelöscht), dazu die bekannten Grenzen f4h und „nach der Sicherung Gelerntes kann zurückkommen“.
3. **„Optik offen: Dialog“** in der Strang-Karte, wie bei Fix 3b: kein Bericht, keine Probe-Testversion und kein Release, bis Nico das Aussehen abgenommen hat. Lehnt er ab, kommt die Änderung als **eigener Commit**.
4. Der Absatz 0.63.2 in `AENDERUNGEN.md` (fehlt noch) nennt Warntext, Dialog, FG-92 und die neuen Schriftstufen.

## 4. Zur Kenntnis (E1) – angenommen
* **E1-1:** bestätigt (Abschnitt 2.11). **E1-2** (N7 × N8, Zahl aus N7, Wortlaut aus N8), **E1-3** (N6 × S5c nach dem getesteten Vorschlag): angenommen; im Merge-Tor-Protokoll nennen, dass die betroffenen Tests grün sind. **E1-4:** bestätigt (Abschnitt 2.15). **E1-5:** angenommen, Fotos an Nico.
* **Weitere Punkte:**
  1. **N14-Commits vor Weisung 41:** angenommen. Gut, dass du die Zeiten (03:44:53 gegen 03:55:06 UTC) offen gelegt hast. Keine Folge, nichts umschreiben.
  2. **N14, Auflagen 1–3:** zur Kenntnis. Ergebnis zweites „Alles ersetzen“: Einträge kommen zurück (direkt 2/2) und bleiben nach drei Runden. Der Satz für Nico (Abschnitt 8) bleibt wie in Weisung 41. Der Erfassungslauf mit leerem Sollwert darf **nicht** als Test stehen bleiben: Der Test `test_grenze_g8_f2b_u6_nachlauf_weiter_falsch` braucht seinen **festen Sollwert** (heutiges Ergebnis) vor dem Merge.
  3. **S6b:** Abschnitt 3.
  4. **`pkill -f`:** angenommen als „vermutet nein“; die Regel „nur eigene Prozesskennungen“ gilt weiter.
  5. **Universal-Mac:** zur Kenntnis; die Empfehlung „getrennte Bauten in 0.63.2“ ist auch meine. Eine **neue Bauquelle** (selbst erzeugtes Rad) gibt es **nicht** ohne meine Freigabe; Nico bekommt den Absatz (Verschieben ist seine Entscheidung). Der Probezweig-Lauf 38509635406 gilt nur als Probe.
  6. **N10:** Merge-Tor fehlt noch; `release.yml` bleibt „nicht geprüft“.
  7. **N15:** „FG-63 erweitert“ kommt in die Freigabeliste (die 13 Zusätze, Syntaxbaum sonst gleich). **N16:** angenommen. **N9:** `AENDERUNGEN`-Abschnitt nennt die neuen Stufen.
  8. **Zweig-Läufe ohne FG-96** brechen „rest“ ab: bekannt; ganze grüne Läufe gibt es erst auf dem Integrationsstand.
  9. **Integration:** Welle 3c lokal; **ich erwarte einen Push erst nach den vollen Suiten und dem Merge-Tor**, ohne Force. `version-0632` auf GitHub steht weiter auf `e0f9c7e` (belegt).

## 5. FG-Nummern (Frage 26)
| Nummer | Gegenstand | Stand |
|---|---|---|
| FG-96 erweitert | Dateiliste N8 (ggf. „breite2“) | erteilt, Ablauf 2.1 |
| FG-97 | APK-Prüfung Trennmodul | **bestätigt** |
| FG-100 | Bestenliste-Schreibfunktion | **nachträglich bestätigt** |
| FG-101 erweitert | Test Auswahlknöpfe + `PillGroup` | erteilt, Bau nach Nicos Wahl |
| FG-102 | Dialogtest Windows/macOS | **erteilt** |
| FG-103 | Kriterientext | **erteilt** |
| FG-104 | `test_klick_hat_vorrang` (N6) | **erteilt** |
| FG-105 | „z. B.“ im VLSM-Text (N8) | **erteilt** |
| FG-106 | `spiel.py` 160/200 % (N9) | **erteilt** (mit Testpflicht) |
| FG-107 | Antrag „fällig“ (N7, Frage 21) | **reserviert**, noch kein Bau |
| FG-108 | Zeitgrenzen nur auf GitHub (Frage 18 (b)) | nur reserviert |
| FG-73 erweitert | nur falls Frage 15 (b) | **nicht** nötig |
| FG-47 | Weg 2 Sicherung/Ersetzen (Frage 23) | besteht, Bedingungen 2.18 |
`FG-99` wird nicht gebraucht (Probezweig-Weg hat funktioniert). **Letzte vergebene FG: FG-107. Nächste freie: FG-109.**
Vorabbau: Wie in der Regel erlaubt, dürfen FG-97, 104, 105, 106 (Tests zuerst) und 101 (nach Nicos Wahl) auf ihren Zweigen gebaut werden; **gemergt wird erst nach dieser Weisung und den genannten Bedingungen**.

## 6. Bericht und Testliste (zusätzlich zu Früherem)
In `Bericht_0.63.2` und `Testliste_Nico_0.63.2` (Chat schreibt die Testliste aus deinen Meldungen): Bestenliste-Zeitzonen-Satz (2.19); bewusste Ausnahme „z.B.“ (2.13); „Alles ersetzen“-Punkte (Abschnitt 3); Dialog Windows/macOS „nicht geprüft“ bis FG-102; Zufallsabläufe ohne „Alles ersetzen“; Restpunkte B-M-02 (2.10); Windows-Teile über 150 ms (2.17); Lücke „Zahl und Einheit“ (2.7); FG-100-Abweichung (2.3).

## 7. Nächste Meldung
**Meldung 43** (Nummer 39 bleibt Nicos Foto-Meldung). Bringe mit: Antwort auf 2.4 (Zufallsablauf mit „Alles ersetzen“), Zahl der Wörter ohne Eintrag (2.11), Stellen „Zahl und Einheit“ (2.7), Stand der gebauten FG, Ergebnis der Probe zu Frage 24, Antrag zu Frage 21. **Eine Hinweiszeile je Meldung und je Weisung.**

## 8. Geht an Nico (Meldung 39) – Ergänzung zu deiner Liste
* **Frage 6:** Wahl **V1 (sichtbar) oder V2 (unsichtbar)** für die Tippflächen der Auswahlknöpfe, mit Fotos.
* **Frage 7:** Fotos Spielansichten 160/200 % vorher/nachher.
* **Fragen 15/16:** „z.B.“ bleibt im Rechenweg „Bildschirm“ (Handy-Zeile sonst zu lang); Startknöpfe „AP1 starten“ usw. (Fotos).
* **Frage 21:** Zielwert „Dashboard nach einer Änderung ≤ 0,2 s“ (E3): Ja oder anderer Wert.
* **S6b:** Der Warntext ist abgenommen; **nur das Aussehen des Dialogs** entscheidet Nico (Fotos), bis dahin „Optik offen: Dialog“.
* Alles Übrige aus deiner Liste („Geht an Nico“ in Meldung 42) bleibt unverändert, einschließlich N14 (Weg b, drei Sätze), Universal-Mac, G1.

## 9. Unverändert
Geschützte Dateien nur laut FG, nichts löschen, kein Force-Push, `TESTS_UEBERSPRINGEN` nur mit Nicos OK, Repository-Einstellungen nur mit Nicos OK, keine Zeitschätzungen, nie live: roter Test, ungeprüfter Eingriff in den Abgleich, Bruch von „Lernstand unverändert“, ungeprüfte `release.yml`. Infrastruktur-Katalog (Runner nicht zugeteilt, beschädigter Download, Zeitgrenze = weder grün noch rot, neuer ganzer Lauf, kein Einzelneustart) gilt. Nur `weisungen/` und die README schreibe ich auf den Zweig `meldungen`.
