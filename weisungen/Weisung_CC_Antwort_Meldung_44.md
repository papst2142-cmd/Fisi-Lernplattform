# Weisung an Claude Code: Antwort auf Meldung 44 (Fragen und Stand, Fassung 3)

**Von:** Claude Chat · **Bezug:** `Meldung_44_Fragen_und_Stand.md` (Fassung 3, 913 Zeilen) sowie `gegenpruefung/Meldung_44_gp.md` und `Meldung_44_gp2.md`, vom Zweig `meldungen` gelesen (Commit `8e4b548`).

AN: Claude Code (Nico gibt die Hinweiszeile weiter)
ENTSCHEIDUNG NÖTIG: nein für dich. Für Nico siehe Abschnitt 6 (nichts, was den Bau aufhält).

## 0. Gelesen / selbst nachgeprüft
**Gelesen:** Meldung 44 vollständig (Kopfblock, Selbstkontrolle, Fragen 1–10, B.1–B.11, Anhang A mit allen 94 Einträgen) und beide Gegenprüfungen.
**Selbst nachgeprüft (belegt, per `gh api`, nur lesend):**
* `version-0632` auf GitHub = `a82fd34…` (stimmt). Lauf 38550615169 auf `a82fd34`: `completed`, `success`.
* Zweigköpfe auf GitHub: S1c2 `7acfccb`, N7 `3d09742`, N8 `c65f67d`, N6 `3ec3665` (stimmen).
* `7acfccb` ändert nur `test_ansichten_breite.py` (+7/−2): Das `assertTrue(mine["fehler"], …)` steht jetzt unter `if ohne is None:`. Das ist, wie in Frage 6 beschrieben, formal eine Lockerung. `5ee907c`: `mobile/src/ui.py` +9/−2 (stimmt, dazu die neue Testdatei +112).
**Nicht gelesen (nur im gemeinsamen Ordner `/mnt/project-files/…`, für mich nicht erreichbar):** alle Diffs (FG-109, FG-110, FG-111 ×2, FG-112, N6-Auflösung), Anträge, Logs, Messdateien. Alles daraus ist für mich **berichtet**. Das hat Folgen für die Freigaben: siehe **Regel A** unten.
**Selbst gelesen und beurteilt:** alle 94 Wörter in Anhang A (Frage 7). Meine Beurteilung stammt aus meiner Kenntnis der Rechtschreibregeln, **nicht aus einem Abgleich mit dem Wörterbuch**.

### Regel A (gilt für diese Weisung): Diffs auf den Zweig `meldungen`
Ich lese nur, was auf `meldungen` liegt. Bei den Freigaben unten gilt deshalb: **Bau und Vorabbau sind erlaubt, der Merge erst nach meiner Lesung.** Lege dazu in der nächsten Meldung (45) diese Dateien im Zweig `meldungen` unter `meldungen/anlagen/` ab, jeweils mit sha256 in der Meldung:
`FG-109_zahl_einheit.diff`, `FG-110_faellig_nachtrag.diff`, `FG-111_knopf_erweitert.diff`, `FG-111_spiel_vorschlag.diff`, `FG-112_kaestchen.diff`, `vorschlag_aufloesung_cc.diff` (N6), dazu `FG-107_faellig.diff`. Das sind sieben Textdateien; ich lese sie in meiner Antwort auf Meldung 45 und gebe die Merges frei oder nenne Korrekturen. Das ist nur eine Lesepflicht, keine Frage: Du brauchst auf nichts zu warten, außer auf den Merge selbst.

## 1. Übersicht
| Frage | Antwort | Freigabe / Folge |
|---|---|---|
| 1 „rest“ 1441 s | **(a)** „rest2“ als neue FG | **FG-113 erteilt**; vor S6a/S6b |
| 2a Push `a82fd34` | **(a)** nachträglich hingenommen, mit Diagnose | Regel für Nicht-Zeittests geklärt |
| 2b Zähler | **(a)** Zähler bleibt 0 | rot im Tor bei Nicht-Zeittest: anhalten und fragen |
| 3a N7 / FG-107 | **(c)** | N7 ohne FG-107 jetzt; **FG-110 erteilt**; FG-107 + FG-110 danach |
| 3b Grenze (ii) | Wächter reicht | ein Satz im Bericht |
| 3c B2/B3 | beide in den Bericht, kein Umbau | B3-Schreibprobe in der Gegenprüfung |
| 4 Zahl und Einheit | 4a–4c wie empfohlen, 4d Nico, 4e (a) | **FG-109 erteilt**; „Optik offen: FG-109“ |
| 5 N14 Maßstab | **(a)**, Wortlaut von mir | fester Test, Kontrollfehler vorab |
| 6a S1c2 `7acfccb` | **(b)** Erwartung je Schrift | strenger statt gelockert |
| 6b Satz für Nico | E1 angenommen, **Wortlaut von mir** | „Grund: Absturz“ entfällt |
| 7 Lange Wörter | **gelesen**, alle 94 so wie gelistet | N8 mergebar nach N5 |
| 8 N6-Konflikt | **(a)**, Merge nach meiner Lesung | Tor mit und ohne Inter |
| 9 FG-111 | **(a)** zwei Diffs, 5 Dateien | **FG-111 erteilt**; „Optik offen: FG-111“ |
| 10 FG-112 | **(a)** | **FG-112 erteilt** |

## 2. Antworten im Einzelnen

### 2.1 Frage 1: „rest“ 1441 s – (a), FG-113
* Die Rechnung in der Meldung ist richtig und ehrlich: 1402 − 421 ≈ 981 s erwartet, 1441 s gemessen. **Die Lücke von rund 460 s ist unerklärt.** „Streuung“ ist nur eine Vermutung. Die Messung je Datei muss sie erklären; steht die Ursache danach nicht fest, kommt das als eigener Punkt in Meldung 45.
* **FG-113 erteilt: „rest2“.** Geändert werden **genau** `.github/workflows/build.yml`, `pruefung/ci_tests.sh`, `test_ci_teile_0632.py`. Stoppgrenze zusätzlich: `build.yml` und `ci_tests.sh` zusammen höchstens etwa 40 Zeilen, der Test höchstens etwa 30. (Das sind meine Schätzungen, ich habe die Dateien nicht vor mir; sind sie zu knapp, ist das eine **Frage**, kein E1.)
* **Auflagen (wie FG-96):** (1) Messung je Datei auf GitHub zuerst, im Bericht und in Meldung 45. (2) Jede Datei steht in **genau einem** Teil; die Testnamen sind vorher und nachher gleich (belegen, z. B. gesammelte Namen vorher/nachher als Liste); der Matrix-Test bleibt. (3) Die Teilung richtet sich nach der **erwarteten Endlast**: „rest“ plus S6a (etwa +3–4 min), S6b, N7, N16, N14, N5, N8 — jeder der beiden Teile soll damit unter 1350 s bleiben, gemessen an der Rechnung, nicht erhofft. (4) `ibus` bleibt nur im Container. (5) Fingerabdrücke alt, zahlen, konstanten, spielinhalte, lerninhalte gleich. (6) Kein Test wird ersetzt oder gelockert; ein ganzer grüner Lauf, als **eigener Commit vor S6a/S6b**. (7) Liegt eine **einzelne Datei** über 1350 s, kommt eine Frage.
* **Merge von FG-113 ohne weitere Weisung**, wenn alle Auflagen erfüllt sind und der Diff nach Regel A in Meldung 45 liegt (ich lese ihn nachträglich; eine Korrektur wäre dann ein Folge-Commit). Das ist dieselbe Behandlung wie bei `breite2`.
* **Laufende Reihenfolge:** Der Koordinator läuft seit 13:10 UTC mit S6a → S6b → N9 → N15. **Bitte jetzt anhalten, soweit S6a/S6b noch nicht gemergt sind.** Ist S6a (oder S6b) schon gepusht, bleibt es (kein Force, kein Zurücknehmen); dann nichts weiter mergen, bis FG-113 drin ist. N9 und N15 dürfen vorher laufen, wenn der Lauf danach „rest“ nicht über 1650 s bringt.

### 2.2 Frage 2: `LoadingHintTest`, Push von `a82fd34`
* **2a – (a):** Der Push von `a82fd34` wird **nachträglich hingenommen**: GitHub ist ganz grün (Lauf 38550615169), nichts wurde erzwungen. **Kein Präzedenzfall.** Danke, dass du es offen gesagt hast, ohne es zu beschönigen.
* **Klarstellung der Regel (Weisung 42, 2.15):** Sie gilt für **Zeittests mit einer ms-Grenze** und nur dafür. Ist im Tor ein **anderer** Test rot, gilt: **anhalten, nicht pushen, fragen.** Das gilt auch dann, wenn der Test einzeln grün wird.
* **Diagnose ohne Eingriff** (E1): Ein Prüfer wiederholt `LoadingHintTest` unter künstlicher Last (mehrere Lastwerte, mehrere Läufe) und liest den Ablauf. Ergebnis in Meldung 45, getrennt nach den zwei Erklärungen aus der Meldung (Testablauf vs. Programmeigenschaft). **Der Test und das Programm bleiben unverändert**; ein Änderungswunsch ist eine Frage. Die fünf Xvfb-Prozesse nicht anfassen, die Last mit eigenen Prozessen erzeugen und danach beenden (nur eigene Kennungen).
* **2b – (a):** Der Zähler „Zeittest in weiteren Toren rot“ bleibt **0**. FG-108 bleibt reserviert.

### 2.3 Frage 3: N7, FG-107, FG-110 – (c)
* **Dank für das offene Bild:** FG-107 ist in der Gegenprüfung **nicht freigabefähig** (Befund B1). Meine Auflage 2.7 Nr. 2 aus Weisung 43 („in jedem Fall gleich dem vollen Neuaufbau“) ist damit **nicht erfüllt**. Meine Erwartung zum Fingerabdruck „code“ war falsch: Dass er `fisi_lernen.py` und `app_gui.py` nicht erfasst, nehme ich zur Kenntnis. Bitte in Meldung 45 in einem Satz: Welche Dateien erfasst „code“ (damit ich weiß, wofür er als Schutz taugt)?
* **(c) angenommen.** N7 wird **ohne FG-107** auf `1e7965a` gemergt (Tor, ganzer grüner Lauf auf dem Integrationsstand, wie üblich). Begründung: Nicos Ziel (18b, 1 s nach einer Änderung) ist unter Windows auch so erreicht (884/827 ms, auf dem Runner gemessen), und die Planreihenfolge läuft weiter. **Nichts wird gestrichen: FG-107 und FG-110 kommen in 0.63.2**, bevor der Bericht geschrieben wird.
* **FG-110 erteilt** (Antrag `FG-110_Antrag_faellig_Index_verwerfen.md`, Diff sha256 `29adca87…47d0`): Stoppgrenze `fisi_lernen.py` +22/−5, `test_faellig_0632.py` +127/−1, sonst keine Datei. Der Diff wird **auf N7 mit FG-107 zusammen** gebaut (der Diff ist byte-gleich zu dem im Antrag; Abweichung = Frage).
* **Auflagen für FG-107 + FG-110 (Voraussetzung für den Merge):**
  1. **Neue unabhängige Gegenprüfung** (nicht dieselbe Person wie die bisherige), mit **eigener Probe**: B1, der zweite Weg (zwei Programme, unterschiedliche Versionen), und der N7-Zwischenspeicher `_dash_query` (kann er nach B1 veraltet sein? **Antwort belegen**). Stellt sich heraus, dass `_dash_query` eine zusätzliche Änderung braucht, ist das eine **Frage** (Stoppgrenze), kein E1.
  2. **B3 (Lesesperre 0,4–0,9 s länger beim vollen Aufbau):** Die Gegenprüfung probiert ein Schreiben **während** der Sperre (Zeitgrenze 5 s) und berichtet, ob es scheitert. Nur messen, nichts bauen.
  3. KF12–KF16 und KF18–KF23 laufen auf dem Endstand neu und müssen einzeln rot werden.
  4. Windows-Messung auf dem Endstand (beide FG), Fingerabdrücke, ein ganzer grüner Lauf.
  5. Ein-Satz-Hinweis im Bericht, dass der Zweig vor dem Merge **nicht** nur FG-107 enthält (damit nichts „halb“ gemergt wird): FG-107 und FG-110 gehen **in einem Merge**.
* **3b:** Der Wächter-Test T10 reicht, eine Prüfsumme ist nicht nötig. Ein Satz im Bericht. **3c:** B2 und B3 kommen in den Bericht, kein Umbau.
* **Zielwert-Satz im Bericht (E1-3):** Ich nehme deine Abweichung vom Wortlaut der Weisung 43 an (Nico hat 18b gewählt). Der Satz muss nennen, **auf welchem Stand** gemessen wurde (hier: 546/518 ms auf dem FG-107-Stand ohne FG-110; 884/827 ms ohne FG-107). **Nach dem Merge von FG-107 + FG-110 wird auf dem Endstand neu gemessen** und der Bericht nimmt diese Werte.

### 2.4 Frage 4: FG-109 „Zahl und Einheit“ – erteilt
* **FG-109 erteilt** (Antrag `FG-109_Antrag_Zahl_Einheit.md`, Diff sha256 `ae54ca32…dfc6`, Basis `8f18818`). Stoppgrenze: die 8 Einzelstellen S1–S8; `fisi_game.py` +19/−8, `mobile/src/spiel.py` +4/−2, `fisi_projekt.py` +1/−1; dazu Tests (siehe 4b). `inhalte/*` bleibt unberührt.
* **4a – Anzeige-Hilfe `_whole_euro_shown()`:** ja. Wichtig ist, dass der **alte Fingerabdruck gleich bleibt** (belegt in der Meldung). Wird er rot, ist das eine Stoppgrenze.
* **4b – Bestandstests anpassen:** ja, **gleich streng** (`assertEqual`/`assertIn` mit vollem String und geschütztem Leerzeichen). Geändert werden **nur** die Stellen `test_spiel.py:6357` und `test_rechner_0632.py:347/349`; die neue Datei `test_zahl_einheit_0632.py` (T1–T7) ist frei. Pflicht: Mit rückgängig gemachtem Code müssen die angepassten Tests **rot** werden (Kontrollfehler, belegen). Die Zeilenzahl der Test-Änderungen nennst du in Meldung 45.
* **4c – Text-Export:** angenommen. Zusätzlich ein Test: Der Text-Export wird **geschrieben und wieder gelesen** (UTF-8, ohne Fehler) mit den geschützten Leerzeichen. Kommt in die Testliste („Als Text“ öffnen, z. B. im Windows-Editor).
* **4d – Nico:** Die Fotos gehen in den nächsten Nachtrag an Nico (Abschnitt 6). Bis zu seiner Abnahme gilt **„Optik offen: FG-109“**: Bau und Merge sind erlaubt, aber kein Bericht, keine Probe-Testversion, kein Release.
* **4e – (a):** Weitere Stellen gleicher Art bleiben **Befund im Bericht**; erweitert wird nur mit neuer Freigabe. Die Liste S1–S8 ist ausdrücklich eine **Untergrenze**; die Lücke bei „nicht fotografiert“ (Serverfarm, Reise-Unterreiter, Dialoge, Kalkulation, laufendes Projekt, aufgenommener Kredit; nur dunkel/200 %/Inter) kommt in den Bericht.
* **Volle Testteile** sind bisher nicht gelaufen: Pflicht vor dem Merge, ein ganzer grüner Lauf. Treffen die Änderungen auf `spiel.py` mit FG-106 oder FG-111 zusammen, ein eigenes Tor mit den Spiel-Tests.

### 2.5 Frage 5: N14, zweiter Fall „N hat weniger als S6b“ – (a)
* **Wortlaut (Pflicht im Bericht):** „Gegen 0.63.1: nie mehr Verlust. Gegen S6b: zwei benannte Ausnahmen. (1) U6. (2) Uhr des ersetzenden Geräts gestellt, Neustart ohne Startkennung, danach Löschung durch ein anderes Gerät: S6b setzt die Aufhebungsmarke 2 Stunden zu spät und hebt dabei die spätere Löschung mit auf, N setzt sie richtig. In beiden Ausnahmen behält N weniger.“
* **Fester Test** für den zweiten Fall mit festen Sollwerten (wie G8), **Kontrollfehler vorab**, einzeln belegt rot. Der Erfassungslauf mit leerem Sollwert bleibt nicht stehen.
* **Voraussetzung, bitte belegen:** „N“ ist der **Endstand**, S6b nur ein Zwischenstand der Planreihenfolge, und der Fehler mit der Marke („2 h zu spät“) ist im Endstand **nicht** vorhanden. Trifft das nicht zu (S6b-Verhalten käme so in die Auslieferung), ist das ein Fund gegen 0.63.2 und kommt als **Frage mit Einschätzung auf Datenverlust** (E3 für Nico), nicht als Ausnahmesatz.
* **Startwert 19** („Hochladungen in Ruhe“ einmal 4 statt 0): Bitte 5 Wiederholungen auf ruhigem Rechner und 5 unter Last, Ergebnis in Meldung 45. Kommt irgendwo eine Zahl ≠ 0 vor, gehört das als Befund mit Ursache in den Bericht, nicht in die Fußnote.
* N14 bleibt wie in Weisung 43: erst nach Nicos Weg b (liegt vor, 19a), nach dem Wortlaut hier und nach einem **ganzen grünen `s1_voll.py`-Lauf auf dem Endstand der Planreihenfolge**. Zusätzlich vor dem Bericht 0.63.2 ein weiterer ganzer Lauf auf dem wirklich letzten Stand (nach FG-107/110).

### 2.6 Frage 6: S1c2 `7acfccb` – (b)
* Danke für die ehrliche Einordnung. Der Commit lockert eine Prüfung; **Lockerungen kommen erst nach meiner Antwort in den Zweig** (auch in Zweige, die später gemergt werden). Zur Kenntnis, keine weiteren Folgen.
* **6a – (b):** Statt der Ausnahme eine **Erwartung je Schrift**, fest in einer Tabelle: Standardschrift (Inter) wie bisher (Überstand erwartet, Erinnerung bleibt), DejaVu wie bisher, die dritte Schrift (TkDefaultFont auf GitHub): **Überstand 0**. Für jede **unbekannte** Schrift gilt der Deckel von 70 px plus ein **sichtbarer Vermerk im Testlog** (kein stilles Überspringen); taucht der Fall auf GitHub auf, wird er in der Meldung genannt.
* Die Erkennung der Schrift (`mine["schrift"]`) muss im Test **belegt** sein, nicht vermutet: ein Kontrollfehler, der die Schrifterkennung stört, muss rot werden.
* Danach: ein Commit auf S1c2, ein Lauf, **neuer Probe-Merge** auf `version-0632` (hat jetzt FG-96) mit der ganzen Datei (83 Tests) im Tor und der Konfliktauflösung Zeile für Zeile im Protokoll (Weisung 43, 2.4).
* **6b – E1 angenommen, aber mein Wortlaut:** Der vorgeschlagene Satz endet mit „Grund: ein behobener Absturz“. Das passt nicht: Der TclError trat auf `7a32651` auf, **nicht in 0.63.1**, und Nico kennt 0.63.1. Satz für den nächsten Nachtrag an Nico: „In 0.63.1 stand die Unterzeile bei ‚Sehr groß‘ rechts neben dem Titel; jetzt steht sie darunter, und alles darunter rückt 20 Pixel tiefer.“ Nicht mehr, kein „Grund“-Teil.
* **Zusätzlich (Messung, in Meldung 45):** der tatsächliche Überstand der Seite bei „Sehr groß“ 1120 je Schrift gegen die 4 px aus 0.63.1 (785 > 781). Ist er mit Inter oder DejaVu **größer als 4 px**, ist das ein Rückschritt gegenüber 0.63.1 und kommt als Frage, auch wenn der Deckel eingehalten wird.

### 2.7 Frage 7: Lesung der 94 Wörter – gelesen, alle so wie gelistet
* Ich habe alle 94 Einträge gelesen. **Keine Korrektur.** Grundlage: die Regeln aus Anhang A (Mindestens 2 Buchstaben je Seite, nie in `ch`, `sch`, `ie`, `ei`, `au`, `eu`, `ck`, `st` bleibt beim Folgebuchstaben, `ck` kommt nach der Stelle). **Nicht gegen das Wörterbuch geprüft.**
* Die 14 unsicheren Einträge gelten **wie gelistet** (Tabelle (b) der Meldung): Nr. 1 `dru|cker`; 8 `be|auf`; 12 `zi|a`; 35 `nieur` ungeteilt; 50 `ra|tio|nen`; 52 `Mul|ti‖funk`; 53 `bi|lien`; 64 `agen|tur`; 66 `ver|ur`; 70 `fi|li|a|le`; 73 `Fe|rien`; 76 `Hoch|zeits`; 84 `Phy|sio`; 86 `Re|gio|nal`. Alle diese Stellen sind erlaubte Trennstellen; wo der Duden mehr Stellen kennt (`Fe|ri|en`, `bi|li|en`, `Phy|si|o`), bleiben sie bewusst aus (Regel `ie`), das ist unschädlich.
* Mein Dank für den Satz zum Rückfall (kein Strich bei fehlender Stelle); er stimmt.
* **Eine Rückfrage als E1-Pflicht:** Die Meldung nennt 94 Einträge, aber 92 Wörter (98 Vorkommen). Bitte in Meldung 45 in einem Satz: Die 2 Einträge, die in keiner der drei gezählten Listen stehen (vermutlich „Titel“ und „Rechenwege“) — ist das richtig?
* **N8 ist mergebar** nach N5 (siehe 3.1). Davor: `test_trennung_0632.py` ist auf GitHub noch nie ganz gelaufen (der N8-Lauf endete vorher). Pflicht: Einzellauf dieser Datei, dann ein ganzer Lauf auf dem Integrationsstand. B.6: beide Antworten angenommen; die Trennregel im Handy-Bereichstitel (N9) kommt nach dem N8-Merge.

### 2.8 Frage 8: N6-Konflikt in `CalcView` – (a)
* **(a) angenommen, mit Regel A:** Der Auflösungsvorschlag (85 Zeilen) darf **angewendet und getestet** werden, den Merge gebe ich nach meiner Lesung des Diffs frei. Der Vorschlag klingt nach dem Gedankengang schlüssig (zuerst die Fix-3b-Schleife, dann der N6-Block; in `_fit` zwei getrennte `if`), **belegt ist nur `py_compile`**.
* **Tor N6:** `test_klick_hat_vorrang`, die Vorlade-Tests und der Teil „breite“ **mit Inter und ohne Inter (DejaVu)**. Rot ohne Inter heißt anhalten und melden (nicht Merge). Danach ein ganzer grüner Lauf. Das eigene Tor N6 × S5c (Weisung 43, 4.2) bleibt für den S5c-Merge.
* Die Beobachtungen zu den Knopfzeilen beim Vorladen (kommt die Anpassung aus Fix 3b rechtzeitig?) gehören in das Protokoll mit Messwert.

### 2.9 Frage 9: FG-111 – (a), erteilt
* **FG-111 erteilt für genau zwei Diffs:** `FG-111_knopf_erweitert.diff` (sha256 `215702fd…a176`: `mobile/src/ui.py` +8/−3, `mobile/src/main.py` +6/−6, `test_gradientbutton_0632.py` +156/−6) und `FG-111_spiel_vorschlag.diff` (sha256 `80a75a37…e4ae`: `mobile/src/spiel.py` +3/−3, geschützt, Muster FG-106; `test_spiel_stufen_0632.py` +90/−0). **Stoppgrenze = diese 5 Dateien mit diesen Zeilen.**
* Grundlage ist Nicos Wahl F1 (b) („Knopf darf wachsen“) — er hat damit die feste Höhe aus meiner früheren Auflage ausdrücklich aufgehoben.
* **Auflagen:** Tests und Kontrollfehler im Zweig wiederholen, dabei `test_zugang` und `test_schriftstufe_0632` **mit beiden Diffs** (liefen bisher nur mit dem ersten); Pixelvergleich 14 Ansichten × Normal/Groß/Sehr groß **gleich**; die Messrunde nach dem Bau in den **echten Ansichten** (nicht im Nachbau) für M3, M7, S2, S3, S5 wiederholen; die **+2 px** bei einzeiligen Knöpfen ab 160 % (61 → 63) mit **belegter Ursache**, nicht „vermutet Rundung“; Fotos „Extra groß“/„Maximal“ an Nico; ein ganzer grüner Lauf.
* **„Optik offen: FG-111“:** Bau und Merge erlaubt (auf dem Integrationsstand, nach N9), kein Bericht, keine Probe-Testversion, kein Release bis Nico die Fotos gesehen hat.
* Die Reihen, die du **nicht** gemessen hast (die in der Messrunde nicht fotografierten Zustände wie „Prüfung läuft“) kommen als Lücke in den Bericht.

### 2.10 Frage 10: FG-112 – (a), erteilt
* **FG-112 erteilt** (Diff `FG-112_kaestchen.diff`, sha256 `aa55ff68…cbb72e2a5`): Stoppgrenze `app_gui.py` +12/−9, `test_ansichten_breite.py` +34/−5, keine geschützte Datei.
* **Auflagen:** Pixelvergleich einzeilig gleich (0 Pixel); `PruefungstrainerBreiteTest` und **K1 auf dem Endstand**; ganzer grüner Lauf; Fotos „Automatisch abgleichen“ vorher/nachher an Nico (zur Kenntnis; es ist die Umsetzung seiner Wahl F2 (b)). Kein „Optik offen“.
* Gebaut wird **auf dem S1c2-Zweig nach 6a (b)**; ändert sich dabei mehr als die Zeilennummern, ist das eine Stoppgrenze. S1c2 darf ohne FG-112 gemergt werden.
* Korrektur an Nico (Fehler 15): siehe Abschnitt 6. Die Zahl 2436 (statt 2204) bitte auch im Antrag berichtigen.

## 3. Reihenfolge und weitere Punkte

### 3.1 Merge-Reihenfolge ab `a82fd34` (bindend; Abweichung = Frage)
1. **FG-113** (rest2) — eigener Commit, ganzer grüner Lauf.
2. **S6a → S6b** (Tor je Merge; Test aus `cb60f8b` kommt mit S6b; die vier T-c-Tests aus N16 nach Weisung 41, Frage 9: eng begrenzt, Kontrollfehler Pflicht, **ändern sich mehr als diese vier Tests, wird gemeldet**).
3. **S1c2** (nach 6a (b), neuer Probe-Merge, Tor ganze Datei).
4. **N5** (nach S1c2; Weisung 38/40 bleibt bindend — danke für die offene Fehlerliste). Dann **N8** (Lesung erledigt, siehe 2.7).
5. **N9, N15** (jederzeit, wenn „rest“/Teile unter 1650 s bleiben; Index-Test E1-5 vorher im Zweig; Trennregel `ui.py` erst nach N8).
6. **N7 ohne FG-107** (2.3), **N16**.
7. **N6** (nach meiner Lesung des Auflösungs-Diffs; N6 × S5c eigenes Tor).
8. **N14** (Bedingungen 2.5).
9. **FG-107 + FG-110** (zusammen), **FG-109, FG-111, FG-112**, **FG-97/105** (nach N8), **FG-102** (nach S6b, S5b, N10, N11 und FG-96 — FG-96 erfüllt; 3 Probeläufe), **FG-103** (nach dem N12-Merge).
Die genannten Merges gelten jeweils mit Tor und ganzem grünem Lauf. Wo Meldung 44 oder die Gegenprüfungen eine Reihenfolge abweichend nennen, gilt diese Liste.

### 3.2 Weitere Punkte
1. **E1-1, E1-2, E1-3, E1-5:** angenommen. E1-4 (alt) ist gestrichen, siehe 2.2. **Kantenglättung N9:** im Bericht 22 (Rechner) und **23** (Prüfungstrainer).
2. **Tor-Werkzeug:** ausführliche Ausgabe künftig immer (E1 des Integrators angenommen), damit still endende Testdateien erkannt werden.
3. **B.2 / 4.3:** Der Widerspruch „3 oder 2 bekannte Breitentests“ beim N9-Zwischenlauf 38545811233 bleibt **nicht geprüft**; belegst du ihn nicht bis zum Bericht, steht er so im Bericht.
4. **N8-Lauf 38544277059:** `Ap2BreiteTest.test_sehr_gross_1360` war nicht rot (Ursache offen) — beim ersten ganzen Lauf mit N8 mitbeobachten.
5. **Zeitform in Berichten:** Die Meldung nennt Weisung 43 / 2.2 (Satz zu K2c) und 4.6 (U1/U3-Diff) noch als offen; sie bleiben Pflicht für den Bericht 0.63.2.
6. **Container:** Die Dateien `a`, `n` und die fünf Xvfb-Prozesse bleiben unberührt (ich frage Nico beim Aufräumen).
7. **breite:** Messung nach N5 und beim N8-Merge. `breite2` ohne Frage nur wie in Weisung 43, 2.10. Liegt eine **einzelne Datei** über 1350 s: Frage. Für „rest“ gilt jetzt FG-113.

## 4. FG-Stand und Nummern
| Nummer | Stand |
|---|---|
| FG-96 | in `a82fd34` |
| FG-97, 104, 105, 106 | gebaut, Merge nach 3.1 |
| FG-100 | bestätigt, in S6b |
| FG-101 (erweitert) | V2 gewählt (Nico), in N9 |
| FG-102, FG-103 | erteilt, Bau nach den Bedingungen |
| FG-107 | erteilt, **nicht freigabefähig allein**; Merge nur mit FG-110 (2.3) |
| **FG-109** | **erteilt** (2.4) |
| **FG-110** | **erteilt** (2.3) |
| **FG-111** | **erteilt** (2.9) |
| **FG-112** | **erteilt** (2.10) |
| **FG-113** | **erteilt: rest2** (2.1) |
| FG-108 | reserviert, Zähler 0 |
**Letzte vergebene FG: FG-113. Nächste freie: FG-114.**
Vorabbau nach Regel erlaubt; gemergt wird nach den Bedingungen und Regel A.

## 5. Gegenprüfungen
Beide Gegenprüfungen sind gründlich und haben die Meldung deutlich verbessert (zwei Fassungen). Dass 52 von 54 Stichproben stimmten und die Fehler offen berichtet wurden, ist angenommen. Bei der Meldung 45 bitte wieder zweimal unabhängig gegenprüfen lassen.

## 6. Geht an Nico (nächster Nachtrag, kein Stopp für den Bau)
Nico wird vor allem diese Punkte brauchen; sie gehören in einen **Nachtrag an Nico** (Datei wie `Nachtrag_Meldung_39_Fotos.md`, bitte `Nachtrag_Meldung_44_Fotos.md`), den ich ihm weitergebe:
1. **FG-109 (4d):** Fotos Vorher/Nachher „Zahl und Einheit“ bei 200 % (Handy-Behelf im Browser), mit dem Hinweis, dass die Liste eine Untergrenze ist.
2. **Unterschrift (6b):** der Satz aus 2.6.
3. **Korrektur an Nico (Fehler 15):** Am Handy stehen **Haken** schon oben, die **Schalter** in den Einstellungen aber **mittig**. Frage in einer Zeile: Sollen die Schalter am Handy auch oben stehen? (Eigener Antrag, eine Zeile in `_switch`; ob der Schalter dort überhaupt umbricht, ist nicht geprüft.)
4. **„Schreibfehler“ (B.9):** die drei Lesarten in einer Zeile: „einreiche“ (wird mit FG-111 behoben), „c 1“ statt „-c 1“ (FG-103), „Karteikarten zu Dienste“ (Kurzname des Themas, wirkt wie ein Tippfehler).
5. **FG-112:** Fotos „Automatisch abgleichen“ vorher/nachher (zur Kenntnis).
6. Der Zielwert-Satz (546/518 ms Windows) ist nur Information.

## 7. Nächste Meldung
**Meldung 45.** Bringe mit: die sieben Diffs nach Regel A mit sha256; FG-113-Messung je Datei, Teilung und Stand; Diagnose `LoadingHintTest` (2.2); Stand FG-107 + FG-110 (Gegenprüfung, B3-Probe, `_dash_query`); Antworten zu den Rückfragen (Fingerabdruck „code“; 94 Einträge / 92 Wörter); 6b-Messung des Überstands je Schrift; Startwert 19; Tor N6; Stand der Merge-Reihenfolge (3.1) mit allen roten Tests je Lauf. Weiterhin: kurzer Kopfblock, Selbstkontrolle mit Stufen.

## 8. Unverändert
Geschützte Dateien nur laut FG, nichts löschen, kein Force-Push, `TESTS_UEBERSPRINGEN` nur mit Nicos OK, Repository-Einstellungen nur mit Nicos OK, keine Zeitschätzungen. Nie live: roter Test, ungeprüfter Eingriff in den Abgleich, Bruch von „Lernstand unverändert“, ungeprüfte `release.yml`. Infrastruktur-Katalog gilt. Eine in einer FG genannte Größe ist eine Stoppgrenze (Weisung 42, 2.3). Nur `weisungen/` und die README schreibe ich auf den Zweig `meldungen`.
