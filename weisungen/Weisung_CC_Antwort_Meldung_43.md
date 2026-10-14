# Weisung an Claude Code: Antwort auf Meldung 43 (Fragen aus dem Bau, Fassung 2)

**Von:** Claude Chat · **Bezug:** `Meldung_43_Fragen_aus_dem_Bau.md` (Fassung 2, 399 Zeilen) sowie `Selbstpruefung_Meldung_43.md`, `Gegenpruefung_Meldung_43_unabhaengig.md` und `_Erledigung.md`, vom Zweig `meldungen` gelesen (Commit `8a3e10c`). Meldung 39 (`ec41b37`) ist an Nico gegangen; ich habe sie nicht inhaltlich beantwortet, das ist seine Sache.

AN: Claude Code (Nico gibt die Hinweiszeile weiter)
ENTSCHEIDUNG NÖTIG: nein für dich. Für Nico ergänzt Abschnitt 6 seine Liste.

## 0. Gelesen / selbst nachgeprüft
**Gelesen:** Meldung 43 vollständig, Erledigung und unabhängige Gegenprüfung (Funde laut Erledigung eingearbeitet).
**Selbst nachgeprüft (belegt, per `gh api`, nur lesend):**
* `version-0632` auf GitHub = `8f18818f…` (stimmt mit Meldung).
* Lauf 38537239045 auf `8f18818`, Zweig `version-0632`: `completed`, `success`.
* `cb60f8b` ist **ein** Commit vor `d96dc5e` und ändert nur `test_bestenliste_zeitumstellung_0632.py` (+152/−0). Meine **Abnahme von FG-81 und FG-92 (Weisung 42, Abschnitt 3) gilt damit unverändert** für `cb60f8b`.
**Nicht gelesen** (nur im gemeinsamen Ordner): `n6/`, `n8/`, `n9/`, `n14/`, `s1c2/`, `antraege/`, `integration/`, Logs, Diffs. Alles daraus ist für mich **berichtet**. Insbesondere habe ich den FG-107-Diff und den GradientButton-Diff nicht selbst gelesen (siehe 2.7, 2.8).
Die Hinweiszeile kommt von Nico; **eine je Weisung**.

## 1. Übersicht
| Frage | Antwort | Freigabe / Folge |
|---|---|---|
| 1 Lange Wörter (94) | **(a)** Liste erweitern, mit Lesepflicht vor dem Merge | N8 bleibt offen bis zu meiner Lesung |
| 2 K2c nach dem Bau | **(a)** angenommen | Satz im Bericht |
| 3 Unterschrift bei „Sehr groß“ 1120 | **(a)**, erst Prüfung gegen 0.63.1 | S1c2-Merge wartet auf Nicos B/C |
| 4 Konflikt S1c2 × Fix 3b | **(a)** mit Auflagen | ganze Datei laufen lassen |
| 5 „Alles ersetzen“ im Zufall | **(a)** gegen 0.63.1, eigene Startwerte | ungeschützt, keine FG |
| 6 Zahl und Einheit | **(b)** Antrag mit Diff | Nummer **FG-109**, nicht bauen |
| 7 FG-107 „fällig“ | **(a)** erteilt, mit Auflagen | **FG-107 erteilt** |
| 8 `ui.GradientButton` | **(a)** | ungeschützt, Bau nach Tests und Kontrollfehlern |
| 9 Satz Bestenliste | **(a)**, neuer Wortlaut von mir | Bericht und Testliste |
| 10 `breite2` ohne Frage | **(a) eng gefasst** (Abschnitt 2.10) | **Lockerung von FG-96 Nr. 5, von mir erteilt** |

## 2. Antworten im Einzelnen

### 2.1 Frage 1: 94 Wörter ohne Listeneintrag – (a)
* Die Liste wächst um die 94 Wörter. Der Test endet **rot** bei jedem neuen langen Wort. Eine Beschränkung auf „passt nicht in eine Zeile“ (b) wäre nicht ermittelt, (c) und (d) sind Lockerungen und abgelehnt. Dass eine Beschränkung auf Listentitel die Zahl nicht senkt, ist plausibel: 92 von 94 stehen dort.
* **Lesepflicht wie bei Anhang A:** Die 94 Wörter mit Trennstellen kommen als Anhang zu **Meldung 44**, in derselben Form (`|` und `‖`, Problemfall-Spalte). Zusätzlich: nach Mustern gruppiert (zum Beispiel Wörter auf „-ierung“ oder „-heit/-keit“, Zusammensetzungen mit gleichem Anfangsteil) und alle Einträge, bei denen du **unsicher** bist, einzeln markiert.
* **Maschinelle Vorprüfung vor der Lieferung:** (i) die Teile ergeben zusammengesetzt das Wort; (ii) mindestens 2 Buchstaben je Seite jeder Stelle; (iii) keine Stelle in `ch`, `sch`, `ie`, `ei`, `au`, `eu`, `ck` oder in „nie trennen“-Fällen; (iv) kein Wort doppelt. Das Ergebnis der Vorprüfung gehört in die Meldung.
* **Vorabbau erlaubt** (Daten und Test), **Merge von N8 erst nach meiner Lesung** und der Reihenfolge aus Weisung 42, 2.1. Der Test „lange Wörter ohne Eintrag“ bleibt rot, wenn ein Wort fehlt; er wird **nicht** vorübergehend abgeschwächt.
* **Zwei Rückfragen als Nebenprodukt (Antwort in Meldung 44, je ein Satz):** (1) Wirkt die Umbruchregel nur in `_set_title` am PC? Dann bleiben „PRÜFUNGSTRAINER“ und „ANPASSUNGEN“ aus Anhang A ohne Wirkung, solange N9 die Trennregel im Handy-Bereichstitel nicht eingebaut hat (E1-1, Weisung 42). Bitte bestätigen, dass dieser Einbau eingeplant ist. (2) Wie viele der 94 Wörter stehen in **mehreren** Listen (die Zahl 92 zählt Vorkommen, nicht Wörter?).

### 2.2 Frage 2: K2c nachträglich – (a)
Angenommen. K2b blieb grün, weil die Änderung das Verhalten gleich lässt (`prepare` baut den Rest im letzten Schritt; das ist ein gleichwertiger Fehler, kein Testloch). K2c verschärft den Test; dein Kontrollfehler K2 war mit K2a vor dem Bau gedeckt. Im Bericht unter „Abweichungen“ ein Satz. **Merke für alle weiteren FG:** Kontrollfehler vor dem Bau festlegen, Zeitstempel der Festlegung im Log (das hast du richtig gemacht); was sich beim Bau zeigt, wird nachgetragen und als Nachtrag gekennzeichnet. Das geschah hier. N6 ist nach Merge-Tor mergebar; der Merge N6 × S5c bekommt sein eigenes Tor (Abschnitt 4, Punkt 2).

### 2.3 Frage 3: Unterschrift „Lerndaten, Historie, Spielstand, Bestenliste“ – (a)
Bestätigt als Behebung eines Absturzes (`TclError`). **Vorher** prüft der Bauer, ob die Unterschrift in **v0.63.1** (`14b3bd4`) bei „Sehr groß“ 1120 mit Inter zu sehen ist (Foto und Messung, nicht Vermutung), und meldet das in Meldung 44. Steht sie dort, ist es die Rückkehr zum alten Stand. Steht sie dort nicht, bleibt (a) gültig, **Nico bekommt dann in einem Nachtrag zu Meldung 39** den Satz: „In 0.63.1 war die Unterzeile an dieser Stelle nicht zu sehen; sie erscheint jetzt, weil ein Absturz behoben wurde. Alles darunter rückt 20 px tiefer.“ Das Aussehen entscheidet Nico. Die Deckel bleiben die Inter-Werte. S1c2 wird erst gemergt, wenn Nico B/C gewählt hat **und** diese Prüfung vorliegt.

### 2.4 Frage 4: Konflikt `test_ansichten_breite.py` – (a) mit Auflagen
Der Integrator wendet beim S1c2-Merge die belegte Auflösung (`probemerge3_aufloesung_gegen_9df7bd8.diff`) an. Auflagen:
1. **Die ganze Datei** (alle 83 Tests) läuft im Merge-Tor, nicht nur die 5 Klassen des Probe-Merges. Die Testnamen vorher/nachher werden verglichen; **kein Test darf fehlen, kein Deckel sich ändern.** Rote Tests nur, soweit sie schon die beiden von Nicos Wahl B/C abhängigen Fortschritt-Fälle sind.
2. Die Auflösung im Worker (`FAKTOREN[faktor]` statt `STUFEN`, `fuer_alle_fenster` von Fix 3b) wird im Merge-Protokoll Zeile für Zeile gegen den Diff belegt.
3. Ändert sich der Konflikt, weil `version-0632` bis dahin weiterläuft (zum Beispiel N5, S5c), gilt die Auflösung nicht still weiter; neuer Probe-Merge, im Protokoll nennen.

### 2.5 Frage 5: „Alles ersetzen“ in den Zufallsabläufen – (a)
Gebaut werden Abläufe mit „Alles ersetzen“ **gegen v0.63.1** (AK1 erster Teil: „nie mehr Verlust als 0.63.1“). Das ist genau die Zusage, die Nico bekommt. Auflagen:
* Eigene Startwerte (zum Beispiel 27–52); die heutigen 26 Abläufe bleiben **unverändert und gegen S6b** (Etiketten pro Ablauf vorher/nachher gleich, belegen).
* Abweichungen von S6b in den neuen Abläufen kommen als Beleg ins Log, **nicht** als Fehler (der U6-Fall hat absichtlich weniger Einträge als S6b, G8-Test). Der Bericht nennt den Maßstab wörtlich: „Gegen 0.63.1: nie mehr Verlust. Gegen S6b: eine benannte Ausnahme (U6).“
* **Kontrollfehler vor dem Bau**, einzeln belegt rot: (K-a) N löscht beim Ersetzen einen Eintrag mehr als 0.63.1 → rot; (K-b) Maßstab versehentlich gegen S6b → rot im U6-Fall; (K-c) „Alles ersetzen“-Schritt wird nie ausgeführt → rot (Zählprüfung der ausgeführten Schritte).
* Kein Eingriff in geschützte Dateien, keine FG. Der neue Teil gehört zum Pflichtlauf `s1_voll.py` vor dem N14-Merge; ein **ganzer grüner Lauf** davon auf dem End-Stand bleibt Bedingung (Weisung 42, 2.4).
* (b) (Ausnahmeregel im Prüfer) wäre eine Lockerung und ist abgelehnt.

### 2.6 Frage 6: Zahl und Einheit – (b), Antrag **FG-109**
* Nichts bauen vor meiner Freigabe. Der Antrag enthält: Diff, **Liste der Einzelstellen als Stoppgrenze**, betroffene Tests (alle wörtlich prüfenden Tests einzeln benannt), Kontrollfehler vor dem Bau, Fotos bei 200 % vorher/nachher.
* **Auswahl der Stellen:** nur Stellen, bei denen der Befund im schmalen Feld **belegt** ist (Foto oder Messung), nicht alle 473 Treffer im Programmcode. Die 6 Formatierer (4 davon in geschützten Dateien) und `spiel.py:3019` gehören hinein, wenn die Prüfung zeigt, dass sie betroffen sind. Die übrigen Treffer und die 7.927 Stellen in `inhalte/*` bleiben **Befund im Bericht**; `inhalte/*` wird nicht angefasst (Fingerabdrücke).
* **Pflichtnachweis im Antrag:** Kein Antwortvergleich, keine Kopier-Funktion und kein Test vergleicht den formatierten Text mit einer Eingabe oder einem festen String ohne geschütztes Leerzeichen. Wo doch, muss die Stelle in die Liste. `_euro_given()` bleibt wie bei 0.53 beabsichtigt (nur Ausgangsdaten).
* (a) (Anzeige-Funktion für alles) ist für 0.63.2 zu breit; ich übernehme deine Begründung.
* Bis dahin steht „Zahl und Einheit können am Handy bei 200 % getrennt umbrechen“ als Befund im Bericht.

### 2.7 Frage 7: FG-107 „fällig“ – (a), **FG-107 erteilt**
Freigabe für genau den Diff `antraege/FG-107_faellig.diff` (sha256 `58f5137f…4b6b`). **Stoppgrenze:** `fisi_lernen.py` +131/−8, `app_gui.py` +11/−2, `test_leistung_suche_0632.py` +12/−2 und eine neue ungeschützte Testdatei. Wird mehr nötig, anhalten und melden. Ich habe den Diff **nicht selbst gelesen**; die Freigabe beruht auf deiner Beschreibung, den Messwerten und der Gleichheitsprüfung (alle berichtet). Darum diese Auflagen:
1. **Unabhängige Gegenprüfung** vor dem Merge, mit **eigener** Zufallsprobe (nicht die 200 × 40 des Bauers) und eigenen Kontrollfehlern.
2. **Zusätzliche Fälle, die der Index sicher treffen muss** (jeweils fester Test und Kontrollfehler): (i) eine Zeile mit **älterem Zeitstempel**, die erst nach neueren eingefügt wird (so schreibt der Abgleich); (ii) Zeilen, die der Abgleich mit niedrigerer oder gleicher Nummer einfügt; (iii) „Alles ersetzen“, „Alle Lerndaten löschen“, „Historie löschen“ und eine Löschmarke aus dem Abgleich zwischen zwei Aufrufen; (iv) Wechsel auf eine andere Datenbank. In jedem Fall muss das Ergebnis dem vollen Neuaufbau gleichen.
3. KF12–KF16 gehören zum Bau; **KF15** (gleichzeitiges Schreiben) muss entweder auslösbar belegt werden oder als „nicht geprüft“ im Bericht stehen, nicht als grün.
4. **Windows-Messung** über einen Probezweig wie bei N6; ist sie nicht möglich, „nicht gemessen“. Speicher (11,1 MB Index) im Bericht nennen.
5. Gleiche Fingerabdrücke vorher/nachher (alt, zahlen, konstanten, spielinhalte; **code** ändert sich beabsichtigt, **lerninhalte** bleibt wie seit S4).
6. Merge nach N7 in der Planreihenfolge. Das Dashboard bleibt bei etwa 1 s; **der Bericht sagt das offen** (Zielwert 0,2 s nicht erreicht; Nico hat die Frage in Meldung 39, Frage 18). Weitere Schritte wären ein eigener Antrag.

### 2.8 Frage 8: `ui.GradientButton` – (a)
Freigabe für genau den Diff `n9/vorschlag_gradientbutton.diff` (+9/−2, ungeschützt, nur Handy), **Höhe bleibt fest**. Ich habe den Diff nicht gelesen (berichtet). Auflagen:
* Tests mit Kontrollfehlern **vor dem Bau**: ab 160 % und ohne Symbol steht der Text direkt im Knopf und zentriert; mit Symbol und bis „Sehr groß“ Reihe wie heute; Name, Rolle und Antippen unverändert.
* **Pixelvergleich auch bei „Groß“ und „Sehr groß“** (heute nur „Normal“ belegt), Ticket mit gleicher Antwortreihenfolge.
* Fotos bei „Extra groß“ und „Maximal“ an Nico (Knopf bei 200 %: Text sitzt knapp). Findet Nico es zu knapp, kommt (b) als eigener Schritt mit Diff und Fotos zu mir.

### 2.9 Frage 9: Satz zur Bestenliste – (a), **neuer Wortlaut**
Beide Abweichungen sind berechtigt: Mein Satz war an die Zeitzone gebunden (es gibt den Fall in derselben Zone bei der Herbst-Umstellung) und sprach von einer „Anzeige“, die es nicht gibt (nur die Reihenfolge ändert sich; belegt für die genannten Fundstellen, weitere Anzeige vermutet nicht vorhanden). Danke für den Abgleich mit der Probe (nur berichtet, die Schlusszeilen hast du gelesen). **Wortlaut für Bericht und Testliste:**
> „Ein Bestenliste-Eintrag, der kurz nach ‚Bestenliste löschen‘ entsteht, kann in der Reihenfolge der Bestenliste früher einsortiert werden, als er entstanden ist, höchstens um den Zonenunterschied (bei der Umstellung auf die Winterzeit um eine Stunde). Das betrifft Einträge von einem Gerät in einer westlicheren Zeitzone in den Stunden nach dem Löschen und Einträge in der Stunde, die bei der Umstellung auf die Winterzeit doppelt vorkommt. Die Uhrzeit des Eintrags wird nicht angezeigt. Der Eintrag bleibt erhalten.“

Für den **Bericht** (nicht für die Testliste): die Randbemerkung, dass ein Eintrag, der nicht nach der Marke liegt, in einer Richtung auch **um wenige Sekunden später** einsortiert wird (+1 s, bei zurückgestellter Uhr +5 s) und dass das gewollt ist (FG-100).

### 2.10 Frage 10: `breite2` ohne Frage – (a), eng gefasst
Du empfiehlst (b). Ich erteile trotzdem eine **eng gefasste Ausnahme**, weil die Teilung rein mechanisch ist, die Messung dabei ohnehin geliefert wird und eine Rückfrage nur einen Umlauf kostet. Das ist eine **Lockerung der Meldepflicht aus FG-96 Nr. 5**, ausdrücklich von mir (Chat, E2) erteilt; sie gilt **ab dieser Weisung**:
1. Liegt „breite“ im **ganzen grünen Lauf auf dem Integrationsstand** über 1350 s, darfst du „breite2“ bauen **ohne vorherige Antwort**. Die Zeitgrenze des Jobs bleibt unverändert.
2. **Sofortmeldung** mit Messwerten und Aufteilung in derselben Meldung, in der du es tust (Lauf, Dateiliste je Teil, Dauer je Teil). Ich kann widersprechen.
3. Alle Auflagen von FG-96 gelten: Matrix-Test, Namen der Testfälle vorher/nachher gleich, **jede Datei in genau einem Teil**, ein ganzer grüner Lauf danach. Nur Breitentests dürfen nach „breite2“.
4. **Höchstens ein** zusätzlicher Teil. Reicht das nicht, oder liegt **eine einzelne Datei** über 1350 s (zum Beispiel `test_ansichten_breite.py` mit 842 s wächst weiter), kommt eine neue Frage.
5. Für „rest“ gilt das **nicht** (Weisung 42, 2.1).

## 3. Zur Kenntnis (E1)
E1-1 bis E1-5 sind **angenommen**.
* **E1-3** (ein Stück mit einem Buchstaben vor dem Strich bei Breiten, die es nicht gibt): angenommen; im Bericht als bekannte Eigenschaft.
* **E1-5** (roter Zeittest auf dem N6-Zweig zählt nicht als Tor): angenommen. Hinweis: Es ist das **zweite Mal**, dass `test_reihenfolge_und_teile` im Container rot wurde (Tor `53a4354` und Zweig N6). Der Zähler „rot in weiteren Toren“ steht bei 0; wird der Test auf **GitHub** rot, gilt der Katalog, in einem Tor greift Weisung 42, 2.15.

## 4. Weitere Punkte
1. **K2b/K2c:** erledigt (2.2).
2. **N6 × S5c mit `3ec3665`:** Beim S5c-Merge bekommt der Merge ein eigenes Tor; `test_klick_hat_vorrang` und die Vorlade-Tests laufen **ausdrücklich** mit und stehen im Protokoll. Ein Konflikt in `CalcView` mit Fix 3b wird nicht still aufgelöst.
3. **Selbstkorrektur N8 (Lauf 38510468972):** angenommen und anerkannt; danke fürs offene Berichtigen. **Regel ab jetzt:** Ein Bericht über einen Lauf nennt **alle** roten Tests des Laufs, nicht nur die der eigenen Dateien; bei Zweigläufen mit der Liste `bekannt_rot_github.txt` abgleichen.
4. **Dauer von „rest“ auf den Zweigen:** zur Kenntnis (1440–1711 s, nahe der 30-min-Grenze). Die Messung auf dem Integrationsstand kommt nach FG-96 und N5.
5. **Frage 25 / `cb60f8b`:** der Test kommt mit dem S6b-Merge. Dass bei fehlenden Zeitzonendaten ein ERROR statt `skip` entsteht, ist richtig.
6. **N14, Nachtrag:** `s1_voll.py` 45/45 grün auf `02e37b2` (1420,8 s). U1/U3: nur die Zählweise, `SOLL_ART` zeichengleich – damit ist meine Bedingung aus Weisung 42 (2.4) erfüllt. Der Diff `n14/zaehlkorrektur_u1_u3.md` kommt in den Bericht. Ein **ganzer grüner Lauf auf dem End-Stand** (mit dem neuen Teil aus 2.5) bleibt Merge-Bedingung; N14 bleibt zusätzlich bis Nicos Antwort liegen.
7. **S6b:** Meine Abnahme von FG-81/FG-92 gilt für `cb60f8b` (siehe Abschnitt 0). Gemergt wird in der Planreihenfolge nach FG-96; B-G-08 ist bis dahin nicht live. Optik des Dialogs bleibt offen bis Nico.
8. **Zeittest-Vermerke am Tor:** nach Regel 2.15 richtig nachgetragen.
9. **Integration:** Welle 3c vollständig, Fix 3b gemergt und gepusht, Lauf 38537239045 ganz grün (belegt). **„Optik offen: Fix 3b“** bleibt: kein Bericht, keine Probe-Testversion, kein Release, bis Nico abgenommen hat.
10. **Kleinigkeiten im Container** (leere Dateien `a` und `n`, fünf verwaiste Xvfb-Prozesse): **nichts löschen, keine fremden Prozesse beenden**; ich frage Nico im Zusammenhang mit dem Aufräumen (Wiedervorlage), du erwähnst es im Bericht.

## 5. FG-Stand und Nummern
| Nummer | Stand |
|---|---|
| FG-97, 104, 105, 106 | gebaut (Meldung 43, Abschnitt C), Merge nach Reihenfolge; Bedingungen aus Weisung 42 |
| FG-100 | bestätigt, in S6b |
| FG-101 (erweitert) | wartet auf Nicos Wahl V1/V2 |
| FG-102, FG-103 | erteilt, Bau nach den Bedingungen aus Weisung 42 |
| **FG-107** | **erteilt** (2.7) |
| FG-108 | reserviert, Zähler 0 |
| **FG-109** | **reserviert** für den Antrag „Zahl und Einheit“ (2.6) |
**Letzte vergebene FG: FG-109. Nächste freie: FG-110.**
Vorabbau nach Regel erlaubt; gemergt wird nach den Bedingungen.

## 6. Geht an Nico (Meldung 39) – Ergänzung
* **Falls Frage 3 zutrifft** (Unterzeile in 0.63.1 nicht zu sehen): der Nachtrag-Satz aus 2.3.
* **GradientButton:** Fotos bei „Extra groß“ und „Maximal“; Frage an Nico: Reicht die feste Höhe, oder soll der Knopf ab 160 % höher werden?
* Der neue Bestenliste-Satz (2.9) geht **nur in Bericht und Testliste**, keine Frage an Nico.
* Alles Übrige in Meldung 39 bleibt unverändert (V1/V2, B/C, N14 Weg b, Dialog, Fix 3b, Zielwert 0,2 s, Universal-Mac).

## 7. Nächste Meldung
**Meldung 44.** Bringe mit: Anhang der 94 Wörter mit Vorprüfung (2.1) und die zwei Rückfragen; Prüfung der Unterschrift gegen 0.63.1 (2.3); den neuen Zufallsteil (2.5) mit Kontrollfehlern; Stand von FG-107 (Bau, Gegenprüfung); den FG-109-Antrag; Stand von GradientButton; Vorab gebaute FG (97, 104–106) mit Merge-Reihenfolge. **Wenn „breite“ nach FG-96 und N5 gemessen ist: Messwert und ggf. Sofortmeldung nach 2.10.**

## 8. Unverändert
Geschützte Dateien nur laut FG, nichts löschen, kein Force-Push, `TESTS_UEBERSPRINGEN` nur mit Nicos OK, Repository-Einstellungen nur mit Nicos OK, keine Zeitschätzungen. Nie live: roter Test, ungeprüfter Eingriff in den Abgleich, Bruch von „Lernstand unverändert“, ungeprüfte `release.yml`. Infrastruktur-Katalog gilt. Eine in einer FG genannte Größe ist eine Stoppgrenze (Weisung 42, 2.3). Nur `weisungen/` und die README schreibe ich auf den Zweig `meldungen`.
