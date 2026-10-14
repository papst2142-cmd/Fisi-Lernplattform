AN: Nico
ENTSCHEIDUNG NÖTIG: ja (Nico)

# Meldung 39: Fotos und Fragen an dich (Version 0.63.2)

Hallo Nico,

hier sind alle Punkte, bei denen du entscheidest. Zuerst kommt das Aussehen mit Fotos, danach Entscheidungen ohne Fotos. Jede Frage kannst du für sich beantworten. Ganz unten steht eine Antwortzeile zum Ausfüllen. Wo „Empfehlung“ steht, ist das ein Vorschlag und keine Entscheidung. „Empfehlung (meine)“ heißt: Der Vorschlag kommt von mir, nicht von Chat oder vom Bauer.

Die Nummern 1 bis 23 sind dieselben wie in der ersten Fassung. Die Fragen 24 bis 28 sind neu dazugekommen.

**So sind die Fotos gemacht:**
- **PC-Fotos:** Das echte Programm läuft auf einem Testrechner unter Linux. Windows und Mac sind auf diesen Fotos **nicht** geprüft.
- **Handy-Fotos:** Die Handy-App läuft im Browser in Handy-Breite (384 Bildpunkte, so breit wie dein S24). Das ist nicht dein echtes Handy, kleine Unterschiede sind möglich. Manche Handy-Fotos sind sehr lang, weil sie die ganze Seite zeigen.
- **„vorher“ und „nachher“:** „vorher“ ist der bisherige Stand, „nachher“ der neue.
- **Versionsnummer:** Auf den PC-Fotos steht unten links noch „Version 0.63.1“. Die Nummer wird erst am Ende umgestellt.
- **Welche Fotos hier stehen:** Je Frage zeige ich höchstens vier Fotos. Alle übrigen Fotos und die genauen Dateien stehen in der Fotoliste (eigene Datei, Abschnitt „Kernauswahl“ und Anhang). Hier beschreibe ich nur, was du auf den Fotos siehst.

**Drei Wörter, die oft vorkommen:**
- **Schmales und normales Fenster:** Die PC-Fotos sind meist 1120 Bildpunkte breit (schmales Fenster) oder 1360 Bildpunkte breit (normales Fenster).
- **Ersatzschrift:** Unsere üblichen Fotos entstehen mit der Schrift „Inter“. Auf vielen Rechnern gibt es diese Schrift nicht. Dann nimmt das Programm eine andere, oft breitere Schrift: unter Linux meist „DejaVu Sans“, unter Windows „Segoe UI“. Auf den Prüfrechnern von GitHub ist es DejaVu Sans. Fotos „mit Ersatzschrift“ zeigen deshalb DejaVu Sans. Segoe UI unter Windows konnte niemand fotografieren. Das bleibt „nicht geprüft“ und steht auf deiner Testliste.
- **ms:** Tausendstelsekunde. 1000 ms sind 1 Sekunde.

**Was „Aussehen offen“ bedeutet:** Zwei Teile (Frage 6 und Frage 7) kommen schon vor deiner Antwort ins Programm, weil sie Fehler beheben. Solange du ihr Aussehen nicht abgenommen hast, gibt es **keinen Bericht, keine Testversion und keine Veröffentlichung**. Sagst du Nein, wird die Änderung als eigener Schritt wieder herausgenommen.

---

# Teil A: Aussehen (mit Fotos)

## Frage 1: Fortschritt-Seite bei „Sehr groß“ im schmalen Fenster – Tabelle „Historie der Prüfungssessions“

**Das Problem:** Bei „Sehr groß“ im schmalen Fenster ist mit der Ersatzschrift die Tabelle „Historie der Prüfungssessions“ zu breit. Die Spaltenköpfe dieser Tabelle können nicht umbrechen. Deshalb lässt sich die ganze Seite seitlich verschieben.

**Gemessen mit Ersatzschrift (Platz im Fenster: 781 Bildpunkte):**

| | leere Tabelle | mit Daten |
|---|---|---|
| heute | 851 (70 zu breit) | 907 (126 zu breit) |
| Variante B | 781 (passt) | 840 (59 zu breit) |
| Variante C | 788 (7 zu breit) | 840 (59 zu breit) |

Mit Daten ist die Seite in beiden Varianten 59 Bildpunkte zu breit. Das liegt nicht an dieser Tabelle: In Variante B ist die Tabelle mit und ohne Daten gleich breit, und in beiden Varianten passt die Tabelle selbst ins Fenster (aus den Messwerten geschlossen). Diese 59 Bildpunkte liegen innerhalb der Grenze, die die Prüfung für die Seite mit Daten schon heute erlaubt (70). Nach den Messwerten ist diese Prüfung deshalb in beiden Varianten grün.

**Was du siehst (heute):** Die Spalten heißen „Datum & Uhrzeit“, „Ergebnis“, „Erfolgsquote“, „Note (Orientierung)“ und „Dauer“. Unten ist ein seitlicher Rollbalken.

**Die Varianten:**
- **(a) Variante B:** Die Spalte „Erfolgsquote“ fällt bei dieser Größe weg. Folge: Die leere Tabelle passt. Nach den Messwerten sind dann alle Prüfungen grün (ein Testlauf mit B steht noch aus), und der Bauabschnitt kann übernommen werden. Die Quote fehlt dann in dieser einen Tabelle.
- **(b) Variante C:** Der Kopf heißt „Quote“, und die Uhrzeit steht ohne Sekunden. Folge: Die leere Seite bleibt 7 Bildpunkte zu breit und lässt sich seitlich verschieben. **Eine Prüfung bleibt rot, und der ganze Bauabschnitt „Breiten der Lernansichten“ kann nicht übernommen werden.** Eine lockerere Grenze hat Chat schon abgelehnt.
- **(c) Etwas anderes:** Du sagst, was. Folge: Es kommt ein neuer Vorschlag mit neuen Fotos.

**Empfehlung: (a) Variante B**, weil nur sie passt. **Wichtig:** Bis zu deiner Antwort wartet der ganze Bauabschnitt „Breiten der Lernansichten“. Dazu gehören auch die Fragen 2 und 3.

**Fotos (alle mit Ersatzschrift, dunkel, „Sehr groß“, schmales Fenster):**
- Foto 1.1: heute, leere Tabelle, nach rechts verschoben. Links ist die Tabelle angeschnitten, unten der Rollbalken.
- Foto 1.2: Variante B, leere Tabelle. Sie passt ganz ins Fenster, die Spalte „Erfolgsquote“ fehlt.
- Foto 1.3: Variante C, leere Tabelle, nach rechts verschoben. Kopf „Quote“, unten noch ein kurzer Rollbalken.
- Foto 1.4: Variante B mit Daten. Die Tabelle passt, unten bleibt der Rollbalken (siehe die 59 Bildpunkte oben).

## Frage 2: Prüfungstrainer, Bewertung bei „Normal“ (schmales und normales Fenster)

**Das Problem:** Beim Bewerten einer Prüfung waren lange Bewertungskriterien bei „Normal“ eine einzige, sehr lange Zeile. Die Seite war viel breiter als das Fenster, um bis zu 2514 Bildpunkte. Der Knopf „Bewertung abschließen“ lag rechts außerhalb und war nur durch seitliches Verschieben zu erreichen.

**Was du siehst (nachher):** Lange Kriterien brechen in mehrere Zeilen um, zum Beispiel „c 1 schickt genau ein Echo Request, -W 1 wartet höchstens 1 Sekunde …“. Kurze Kriterien bleiben einzeilig. Oben rechts ist „Bewertung abschließen“ im Bild. Es gibt keine neuen Knöpfe, Farben oder Texte.
Am Anfang fehlt ein Minuszeichen: Richtig wäre „-c 1“. Das ist ein eigener, älterer Fehler. Die Behebung ist freigegeben und kommt getrennt.

**Optionen:**
- **(a) Ja, übernehmen.** Folge: Beim Bewerten muss man nicht mehr seitlich verschieben.
- **(b) Nein.** Folge: Es bleibt wie bisher. Die Seite lässt sich seitlich verschieben, und der Knopf liegt außerhalb.
- **(c) Ändern:** Du sagst, was anders aussehen soll.

**Empfehlung: (a).** Es wird nur umgebrochen, sonst ändert sich nichts. Dieser Teil wartet mit Frage 1 (siehe dort).

**Fotos:**
- Foto 2.1 und 2.2: Konzeption-Prüfung, schmales Fenster, beim längsten Kriterium, vorher und nachher.
- Foto 2.3 und 2.4: AP1-Prüfung, normales Fenster, oben, vorher und nachher.

## Frage 3: Notizblock, Fortschritt und Optionen bei „Normal“ im schmalen Fenster, dazu Kurznamen in Tabellen

**Das Problem:** Diese drei Seiten waren bei „Normal“ im schmalen Fenster etwas breiter als das Fenster, mit seitlichem Rollbalken. Die Abhilfe ordnet nur dort um, wo der Platz nicht reicht. Im normalen Fenster ändert sich mit Inter nichts. Mit der Ersatzschrift waren außerdem einige Fälle zu breit. Auch diese passen jetzt.

**Was du siehst (nachher):**
- **Fortschritt:** Die Kacheln stehen in zwei Reihen (3 + 2). In der Tabelle „Prüfungen (Klausursimulation)“ steht in der Spalte „Prüfung“ ein Kurzname: „WiSo“, „Netzwerke“, „Konzeption“ oder „AP1“. Vorher standen dort abgeschnittene lange Namen wie „AP2 · Wirtschafts- und Sozialkunde“. Die Kurznamen kennt das Programm schon aus der Historie des Prüfungstrainers. Neu ist nur, dass sie hier stehen, wenn der Platz fehlt (auch bei „Groß“ und „Sehr groß“). Der Satz „Startet eine Übungsrunde …“ steht jetzt unter den Knöpfen.
- **Notizblock:** Die Kacheln „Lernstand je Bereich“ stehen 3 + 2 statt 5 nebeneinander. Die Filterzeilen und die Einträge brechen um, und die Blätterpfeile sind sichtbar. Mit Ersatzschrift im normalen Fenster ist jetzt auch der Symbolknopf am rechten Rand ganz zu sehen.
- **Optionen:** Die Vorlagen-Kacheln stehen 3 + 3 statt 6 nebeneinander.
- **Nur zur Info:** Bei „Sehr groß“ im schmalen Fenster steht unter dem zugeklappten Bereich „Löschen und zurücksetzen“ wieder die Unterzeile „Lerndaten, Historie, Spielstand, Bestenliste“. Sie fehlte durch einen Fehler. Alles darunter rückt deshalb etwas tiefer.

**Optionen:**
- **(a) Ja, übernehmen.** Folge: Auf diesen Seiten gibt es keinen seitlichen Rollbalken mehr, und wo der Platz fehlt, stehen Kurznamen in der Tabelle.
- **(b) Ja, aber ohne Kurznamen.** Folge: Die Tabelle bleibt abgeschnitten. Dafür braucht es eine andere Lösung mit neuem Vorschlag.
- **(c) Nein.** Folge: Es bleibt wie bisher.

**Empfehlung: (a).** Es wird nur zurechtgerückt, es kommen keine neuen Elemente dazu. Dieser Teil wartet mit Frage 1.

**Fotos (jedes Foto zeigt links vorher und rechts nachher):**
- Foto 3.1: Fortschritt mit Daten, „Normal“, schmales Fenster, hell. Kacheln 3 + 2 und Kurznamen.
- Foto 3.2: Notizblock geöffnet, „Normal“, schmales Fenster, hell.
- Foto 3.3: Optionen, alles aufgeklappt, „Normal“, schmales Fenster, hell.
- Foto 3.4: Notizblock geöffnet, „Normal“, normales Fenster, dunkel, mit Ersatzschrift. Der Symbolknopf rechts ist jetzt ganz zu sehen.

## Frage 4: Startknöpfe der Prüfungen mit Kurznamen

**Das Problem:** Im Prüfungstrainer hießen bisher alle vier Startknöpfe gleich: „Starten“. Jetzt steht auf jedem Knopf, was er startet. Das gilt am PC und am Handy gleich. Die Wörter hat Chat bestätigt, das Aussehen entscheidest du.

**Was du siehst (nachher):** „AP1 starten“, „Konzeption starten“, „Netzwerke starten“ und „WiSo starten“. Weil die Knöpfe länger sind, brechen die Prüfungstitel bei „Sehr groß“ im schmalen Fenster jetzt in zwei Zeilen um. Vorher war der Knopf rechts abgeschnitten, und es gab einen Rollbalken. Die Kopfzeile oben ist bei „Groß“ und „Sehr groß“ 2 Bildpunkte höher, bei „Normal“ ist sie unverändert.
Auf einem Foto wirkt „Konzeption starten“ heller als die anderen Knöpfe. Vermutlich lag dort beim Fotografieren die Maus darauf. Das ist keine neue Farbe.

**Optionen:**
- **(a) Ja, so übernehmen.**
- **(b) Andere Wörter auf den Knöpfen:** Du nennst sie. Folge: Es braucht neue Fotos.
- **(c) Zurück zu viermal „Starten“.** Folge: Der Umbruch bei „Sehr groß“ wäre dann nicht nötig.

**Empfehlung: (a).** So sieht man auf dem Knopf, welche Prüfung startet.

**Fotos:**
- Foto 4.1 und 4.2: „Normal“, normales Fenster, dunkel, vorher und nachher.
- Foto 4.3 und 4.4: „Sehr groß“, schmales Fenster, hell, mit Ersatzschrift, vorher und nachher.

## Frage 5: Spiel am PC (Firma und Reise) mit Ersatzschrift

**Das Problem:** Im Spiel am PC liefen in schmalen Fenstern oder bei großer Schrift Teile der Seiten „Firma“ und „Reise“ seitlich über. Die Abhilfe ordnet um, wo der Platz fehlt. Mit Inter ändert sich bei „Normal“ im normalen Fenster nichts, die Fotos sind pixelgleich. Mit der Ersatzschrift wird auch bei „Normal“ im normalen Fenster umgeordnet, weil dort sonst etwas überläuft. Chat hat festgelegt, dass dieser Teil erst nach deiner Abnahme der Fotos ins Programm kommt.

**Was du siehst (nachher):**
- **Reiterleiste der Firma** bei „Sehr groß“ im schmalen Fenster in drei Reihen statt zwei: „Aufträge, Projekte, Mitarbeiter, Bewerbungen“, dann „Gebäude“ allein, dann „Marketing, Zertifizierungen, Finanzen, Kredite“. Vorher war die Leiste rechts abgeschnitten.
- **Weiterbildung:** Die Angebote verteilen sich auf mehrere Zeilen, statt rechts abgeschnitten zu sein, zum Beispiel „Ganzer Fachbereich (1.400 €)“ und „Grundlagen 74 (600 €)“.
- **Rückblick:** Lange Texte brechen um, statt abgeschnitten zu werden, zum Beispiel „Tag 100. Sabine hat alle zusammengerufen …“. Der Knopf „Ältere“ ist sichtbar. Wenn es eng ist, stehen die Diagramme untereinander.
- **Erfolge** stehen bei „Normal“ im schmalen Fenster in 2 statt 3 Spalten. Beim Zuweisen stehen die Mitarbeiter-Knöpfe unter dem Text.

**Optionen:**
- **(a) Ja, übernehmen.**
- **(b) Nein.** Folge: Mit Ersatzschrift bleiben diese Stellen abgeschnitten oder seitlich verschiebbar.
- **(c) Ändern:** Du sagst, was.

**Empfehlung: (a).** Es wird nur zurechtgerückt, es kommen keine neuen Elemente dazu, und mit Inter bleibt „Normal“ unverändert.

**Fotos (mit Ersatzschrift):**
- Foto 5.1 und 5.2: Firma, Reiter „Marketing“, „Sehr groß“, schmales Fenster, dunkel, vorher und nachher.
- Foto 5.3 und 5.4: Firma, Mitarbeiter, Auswahl der Weiterbildung, „Normal“, normales Fenster, hell, vorher und nachher.

## Frage 6: Reparatur für die Ersatzschrift im Rechner, in den AP2-Szenarien und im Testprojekt („Aussehen offen“)

**Das Problem:** Auf den Prüfrechnern von GitHub, also mit Ersatzschrift, liefen drei Seiten seitlich über:
- der Rechner bei „Sehr groß“ im schmalen Fenster,
- die AP2-Szenarien bei „Sehr groß“ nach „Musterlösung anzeigen“,
- das Testprojekt bei „Normal“ im normalen Fenster.

Die Reparatur lässt Knopfreihen nur dann umbrechen, wenn der Platz fehlt. Mit Inter ändert sich nichts. Chat hat entschieden, dass die Reparatur schon vor deiner Abnahme übernommen wird (siehe „Aussehen offen“ oben).

**Was du siehst (nachher, mit Ersatzschrift):**
- **Rechner, Unterbrechungsfreie Stromversorgung:** „Akku berechnen“ und „Laufzeit berechnen“ stehen in der ersten Zeile, „Empfehlung“ in der zweiten. Es gibt keinen seitlichen Rollbalken mehr. Die RAID-Knöpfe bleiben einzeilig.
- **AP2-Szenarien:** Unten gibt es keinen seitlichen Rollbalken mehr („Musterlösung ausblenden“, „Nächstes Szenario“).
- **Testprojekt:** Das Raster ist wie bisher. Der Knopf „Als Vorlage fürs Abschlussprojekt“ steht rechtsbündig in einer zweiten Zeile.

**Optionen:**
- **(a) Ja, Aussehen abnehmen.**
- **(b) Nein.** Folge: Die Reparatur wird herausgenommen. Mit Ersatzschrift laufen die Seiten wieder seitlich über, und die Prüfungen auf GitHub sind wieder rot.
- **(c) Ändern:** Du sagst, was.

**Empfehlung: (a).** Mit Inter ändert sich nichts. Mit anderen Schriften ersetzt die Reparatur einen seitlichen Überlauf.

**Fotos (mit Ersatzschrift, hell):**
- Foto 6.1 und 6.2: Rechner, Knöpfe der Unterbrechungsfreien Stromversorgung, „Sehr groß“, schmales Fenster, vorher und nachher.
- Foto 6.3 und 6.4: Testprojekt unten, „Normal“, normales Fenster, vorher und nachher.

Die AP2-Fotos stehen in der Fotoliste. Windows mit Segoe UI ist nicht geprüft.

## Frage 7: Warnung vor „Alles ersetzen“ – Aussehen des neuen Fensters („Aussehen offen“)

**Das Problem:** Vor „Alles ersetzen“ (Sicherung einspielen) erscheint eine lange Warnung. **Am Linux-PC war sie bisher abgeschnitten.** Das alte Systemfenster zeigte den Text nicht ganz, die Knöpfe „Yes“ und „No“ (englisch) waren am unteren Bildschirmrand angeschnitten, und die Schriftgröße des Programms galt dort nicht.

**So ist es jetzt gelöst:** Ein eigenes Fenster zeigt den Text zum Rollen. Die Knöpfe sind immer sichtbar, und die Schriftgröße des Programms gilt. Der Text selbst ist von Chat abgenommen und hat sich nicht geändert. Am PC ist „Nein“ vorbelegt: Eingabetaste, Escape und das Schließen des Fensters bedeuten „Nein“. Am Handy rollt die Warnung ebenfalls, und der letzte Satz „Bewahre die Sicherungsdatei deshalb auf.“ ist erreichbar.

**Was du siehst (nachher, PC):**
- Der Fenstertitel ist „Alles ersetzen“, im Fenster steht die Überschrift in Großbuchstaben: „ALLES ERSETZEN“.
- Es gibt kein Warnsymbol mehr. Vorher war es ein rot umrandetes Dreieck.
- Der Text hat einen Rollbalken.
- Darunter steht links ein **roter** Knopf „Ja“ und rechts „Nein“.
- Auf dem Mac ist die übliche Reihenfolge umgekehrt (Nein links, Ja rechts). Dieses Fenster macht es überall gleich.

**Optionen:**
- **(a) Ja, so übernehmen.**
- **(b) Ja, aber ändern:** zum Beispiel ein Warnsymbol dazu, die Überschrift nicht in Großbuchstaben, „Ja“ nicht rot oder auf dem Mac die umgekehrte Reihenfolge. Du nennst, was.
- **(c) Nein.** Folge: Das alte Systemfenster kommt zurück und ist am Linux-PC wieder abgeschnitten.

**Empfehlung: (a).** Der Text ist ganz lesbar, und die Knöpfe sind immer erreichbar. Windows und Mac sind für dieses Fenster noch nicht geprüft. Ein Test dafür ist freigegeben, und der Punkt steht auf deiner Testliste.

**Fotos (Bildschirm 1366 × 768, „Normal“, hell):**
- Foto 7.1: PC vorher, altes Systemfenster mit „Yes“/„No“, unten angeschnitten.
- Foto 7.2: PC nachher, oben.
- Foto 7.3: PC nachher, nach dem Rollen unten.
- Foto 7.4: Handy nachher, hell, „Normal“, unten mit dem letzten Satz.

## Frage 8: Kurze Rückfragen am Handy (kurze Bestätigungsfrage)

**Das Problem:** Damit lange Warnungen am Handy rollen, gilt die Rollfunktion jetzt für **alle** Rückfragen am Handy. Kurze Rückfragen sollen dabei genau so aussehen wie vorher. Am PC bleiben die anderen Rückfragen unverändert beim Systemfenster.

**Was du siehst:** „Bestenliste löschen“ mit dem Text „Wirklich die Bestenliste löschen? Bestwerte und Abzeichen früherer Spielstände sind danach weg. Der laufende Spielstand trägt sich gleich wieder ein.“ und den Knöpfen „Abbrechen“ und „Ja“. Vorher und nachher sind die Fotos **pixelgleich** (gemessen: 0 Bildpunkte Unterschied).
Fotografiert sind drei Einstellungen in je zwei Durchläufen: hell „Normal“, dunkel „Normal“ und dunkel „Sehr groß“. Das sind 6 Fotos vorher und 6 nachher. **Hell mit „Sehr groß“ fehlt.**

**Optionen:**
- **(a) Bestätigt, so lassen.**
- **(b) Nein.** Folge: Nur die lange Warnung rollt, dafür braucht es eine andere Lösung.

**Empfehlung: (a).**

**Fotos (hell, „Normal“):**
- Foto 8.1: vorher.
- Foto 8.2: nachher.
- Foto 8.3: Unterschied-Bild. Es ist leer, weil es keinen Unterschied gibt.

## Frage 9: Neue Schriftgrößen „Extra groß“ und „Maximal“

**Das Problem:** Du hattest zwei größere Schriftstufen gewählt, 160 % und 200 %. Die Namen „Extra groß“ und „Maximal“ hat Chat festgelegt. Sie passen zu „Normal“, „Groß“ und „Sehr groß“, und „Maximal“ zeigt, dass es nichts Größeres gibt. Du entscheidest über das Aussehen.

**Was du siehst:**
- **Optionen:** Unter „Optische Anpassungen“ → „Schriftgröße“ steht die Reihe „Normal, Groß, Sehr groß, Extra groß, Maximal“.
- **PC bei den neuen Stufen:** Alles ist größer. Die Seite ist breiter als das Fenster und lässt sich seitlich verschieben. So steht es auch im Hinweistext: „passt sie nicht mehr ins Fenster, lässt sie sich seitlich verschieben“.
- **Handy:** Kacheln und Ringe stehen untereinander, die Kopfzeile ist höher, und die Diagramme sind höher und haben eine lesbare Achse.
- **Hilfe-Satz (Wortlaut von Chat):** „Die Schrift vergrößerst du in den „Optionen“ unter „Optische Anpassungen“ bei „Schriftgröße“ mit „Groß“, „Sehr groß“, „Extra groß“ oder „Maximal“.“

**Bekannte Mängel bei „Maximal“ (200 %), am Foto gesehen und noch nicht behoben:**
- **Handy, Worttrennung:** Einzelne Wörter brechen mitten im Wort um, zum Beispiel „Sättigun/g“, „ANPASSUNG/EN“ und „VORLAGE/N“. Eine Trennregel dafür ist in Arbeit und noch nicht eingebaut.
- **Handy, Prüfungstrainer:** Der Knopf „Antwort ein…“ ist abgeschnitten, weil zwei Knöpfe nebeneinander stehen.
- **Handy, Fortschritt:** In der Legende wird „Aufgaben“ vom Linien-Symbol teilweise verdeckt.
- **Handy, Optionen:** Die Reihe der Schriftgrößen ist rechts abgeschnitten („Maxim…“). Das ist auf dem Foto zu sehen, wurde aber nicht eigens geprüft.
- **PC:** Auch im breiten Fenster (1920 Bildpunkte) ist die Seite breiter als das Fenster und lässt sich seitlich verschieben. Bei „Vorlagen“ ist „aufklappen“ angeschnitten.

Ob Bedienelemente sichtbar größer werden dürfen, entscheidest du in Frage 12.

**Optionen:**
- **(a) Ja, Aussehen so übernehmen.** Die bekannten Mängel bleiben dabei als offene Punkte im Bericht. Die Worttrennung kommt mit der Trennregel.
- **(b) Ändern:** Du sagst, was.

**Empfehlung: (a).**

**Fotos:**
- Foto 9.1: PC, Optionen bei „Extra groß“, schmales Fenster, hell.
- Foto 9.2: Handy, Optionen bei „Maximal“, dunkel.
- Foto 9.3: Handy, Startseite bei „Maximal“, dunkel.
- Foto 9.4: Handy, Prüfungstrainer bei „Maximal“, dunkel, mit dem abgeschnittenen Knopf.

## Frage 10: Reihe der Schriftgrößen am PC im schmalen Fenster

**Das Problem:** Mit fünf Stufen ist die Knopfreihe „Normal … Maximal“ bei großer Schrift im schmalen Fenster breiter als der sichtbare Bereich. Alle fünf Knöpfe sind da und funktionieren. Ganz sieht man sie aber nur durch seitliches Verschieben. Im breiten Fenster (1920) steht die Reihe ganz im Bild.

**Was du siehst:** Bei „Maximal“ im schmalen Fenster sieht man „Normal“, „Groß“ und „Sehr gro…“. Rechts ist die Reihe abgeschnitten, unten ist ein Rollbalken. Im breiten Fenster sieht man die ganze Reihe bis „Maximal“.

**Optionen:**
- **(a) So lassen:** „passt“ heißt hier „per seitlichem Verschieben erreichbar“, so wie es der Hinweistext sagt.
- **(b) Ändern, die Reihe soll ganz sichtbar sein:** Dann kommt eine neue Ersatzreihe mit Umbruch. Sie ist kein geschützter Baustein. Die genaue Änderung geht vorher an Chat. Folge: neue Fotos.

**Empfehlung: (a)**, so auch Chat. Bist du mit dem Foto unzufrieden, kommt (b).

**Fotos:**
- Foto 10.1: Optionen bei „Maximal“, schmales Fenster, dunkel, mit Ersatzschrift.
- Foto 10.2: Optionen bei „Maximal“, breites Fenster (1920), hell.

## Frage 11: Leiste unten am Handy bei großer Schrift

**Das Problem:** Am Handy wächst bei großer Schrift die Leiste unten mit (Start, Lernen, Rechner, Spiel, Fortschritt, Optionen). Wächst auch die Beschriftung mit, bricht „Fortschritt“ mitten im Wort um („Fortsc/hritt“). Das passiert selbst dann, wenn nur der gewählte Eintrag beschriftet ist. Deshalb ist so gebaut: Leiste und Symbole werden größer, die Beschriftung bleibt klein und einzeilig.

**Was du siehst (gebaut):** Bei „Maximal“ große Symbole, darunter klein „Start“, „Lernen“, „Rechner“, „Spiel“, „Fortschritt“ und „Optionen“, alles einzeilig.

**Optionen:**
- **(a) So übernehmen** (große Symbole, kleine Beschriftung).
- **(b) Die Beschriftung wächst mit.** Folge: Wörter brechen mitten im Wort um („Lerne/n“, „Rechn/er“).
- **(c) Beschriftung nur beim gewählten Eintrag.** Folge: Ab „Groß“ bricht „Fortschritt“ trotzdem um, und die anderen Einträge haben keine Beschriftung.

**Empfehlung: (a).** Nur so bleibt jede Beschriftung ganz lesbar.

**Fotos:**
- Foto 11.1: gebaute Fassung in den Stufen „Normal“, „Sehr groß“, „Extra groß“ und „Maximal“.
- Foto 11.2: Probebilder für (b) und (c).

## Frage 12: Größere Tippflächen der Auswahlknöpfe am Handy – sichtbar oder unsichtbar?

**Das Problem:** Die kleinen Auswahlknöpfe am Handy sind kleiner als die empfohlene Mindestgröße zum Tippen, zum Beispiel „IPv4“/„IPv6“, „Netzdaten“ oder „RAID 0“. Empfohlen sind 48 Einheiten, heute sind es 36. Es gibt zwei Wege. Gebaut wird erst nach deiner Wahl. Ab „Maximal“ ändert sich nichts, weil die Knöpfe dann ohnehin groß genug sind.

Damit beantwortest du zugleich eine allgemeine Frage aus dem Plan. Bisher gilt: Die sichtbare Größe bleibt, wo es geht. Wo etwas sichtbar größer wird, entscheidest du per Foto. Mit (a) erlaubst du das für diese Auswahlknöpfe.

**Was du siehst:** Die Rechner-Seite und den Prüfungstrainer, jeweils in drei Spalten: heute, V1 und V2. Die kleinen Beschriftungen mit „dp“ auf den Vergleichsbildern sind technische Größenangaben für Handys („Einheiten“). Du kannst sie überlesen.

**Optionen:**
- **(a) V1 „sichtbar“:** Die Knöpfe selbst werden höher. Folge: Man sieht größere Knöpfe, und die Seite wird etwas länger.
- **(b) V2 „unsichtbar“:** Die Knöpfe sehen aus wie heute. Um jeden liegt eine unsichtbare Fläche von 48 Einheiten, die das Tippen annimmt. Folge: Das Aussehen bleibt gleich, nur der Abstand zwischen den Reihen wird etwas größer.

**Empfehlung:** keine, das ist reine Geschmackssache. Für beide Varianten sind die Tests grün (laut Bauer).
Die V2-Fotos stammen aus einer ersten Fassung, in der auch der innere Knopf noch antippbar war. Im Ruhezustand sieht das gleich aus.

**Fotos (dunkel):**
- Foto 12.1: Rechner bei „Normal“: heute, V1 und V2.
- Foto 12.2: Rechner bei „Maximal“: heute, V1 und V2.
- Foto 12.3: Prüfungstrainer bei „Normal“: heute, V1 und V2.

## Frage 13: Spiel am Handy bei „Extra groß“ und „Maximal“

**Das Problem:** Bei den neuen großen Stufen gab es im Handy-Spiel drei Fehler:
- Titel brachen mitten im Wort um („ZWISCHENFÄ/LLE“).
- Namen liefen in die Balken.
- Knopftexte waren abgeschnitten („Lösung einreiche…“).

Die Abhilfe stellt ab „Extra groß“ Dinge untereinander. Bis „Sehr groß“ bleibt alles wie bisher. Die Fotos sind gleich, nur die Antworten im Ticket stehen in zufälliger Reihenfolge. Chat hat diese Änderung freigegeben. Sie ist gebaut, aber noch nicht ins Programm übernommen. Das Aussehen entscheidest du.

**Was du siehst (nachher):**
- **Reise, Rückblick:** eine Kachel je Zeile, „ZWISCHENFÄLLE“ steht ganz da.
- **Mitarbeiter:** Der Name steht über Balken und Wert („Netzwerk“, darunter Balken und „72“). Die Knöpfe stehen untereinander.
- **Ticket:** „Lösung einreichen“ geht über die ganze Breite, „Hilfe“ steht darunter.
- **Übersicht:** Das Bild der Spielfigur steht über dem Text („Geschäftsführung · Test IT-Service“).
- **Büro, Zuhause und der Kopf der Firma:** unverändert.
- **Wissenslücke** (der gelbe Kasten „Dafür fehlt dir noch Wissen …“ mit dem Knopf „Karteikarten zu Dienste“):
  - Bei „Normal“ sind vorher und nachher gleich.
  - Bei „Extra groß“ ist der Knopf jetzt so breit wie der Kasten.
  - Bei „Maximal“ bleibt der Knopf im Kasten, aber der Text reicht bis an den Rand des Knopfes. **Das ist ein bekannter Rest.** Ganz lösen lässt er sich nur mit einem Umbruch im Knopf selbst. Ein Vorschlag dafür wird mit Meldung 43 an Chat gehen. Dazu musst du jetzt nichts entscheiden.

**Optionen:**
- **(a) Ja, übernehmen**, mit dem bekannten Rest bei der Wissenslücke.
- **(b) Ändern:** Du sagst, was.
- **(c) Nein.** Folge: Bei „Extra groß“ und „Maximal“ bleiben Wörter zerbrochen und Texte abgeschnitten.

**Empfehlung: (a).**

**Fotos (dunkel; jedes Vergleichsbild zeigt links vorher und rechts nachher):**
- Foto 13.1: Mitarbeiter bei „Maximal“, Vergleich.
- Foto 13.2: Ticket bei „Maximal“, Vergleich. Oben ist auch die Wissenslücke zu sehen.
- Foto 13.3: Wissenslücke bei „Extra groß“, nachher. Der Knopf ist so breit wie der Kasten.
- Foto 13.4: Wissenslücke bei „Maximal“, nachher. Der Text reicht bis an den Rand des Knopfes.

## Frage 14: Gesperrte Blätterpfeile in der Farbwelt „Lila/Magenta“ hell

**Das Problem:** Gesperrte Blätterpfeile, zum Beispiel „zurück“ auf Seite 1, werden blasser gezeigt. Dieses Aussehen hast du mit Meldung 23 abgenommen. In der Farbwelt „Lila/Magenta“ im hellen Modus sind gesperrte und freie Pfeile auf dem Foto **kaum zu unterscheiden**, beide sind ähnlich lila. Bei „Blau/Türkis“ hell ist der Unterschied sichtbar, aber schwach. In allen anderen Fällen ist er laut Messung gut sichtbar.

**Was du siehst:** Handy, Rechner „Netz aufteilen“, „Seite 1 von 32“ und „Seite 32 von 32“, darunter die vier Pfeile.

**Optionen:**
- **(a) So lassen.**
- **(b) Andere gedämpfte Farbe** für diese Fälle. Folge: Die Pfeilfarbe ändert sich in den Handy-Listen und beim Blättern im Rechner gemeinsam, und es braucht neue Fotos. Den PC betrifft das nicht, dort ist die Sperre schon gut sichtbar.

**Empfehlung (meine): (b).** Eine Sperre, die man nicht sieht, hilft nicht. Der Bauer hat keine Empfehlung gegeben.

**Fotos (jedes zeigt links vorher und rechts nachher):**
- Foto 14.1: „Lila/Magenta“ hell.
- Foto 14.2: „Blau/Türkis“ hell.
- Foto 14.3: „Lila/Magenta“ dunkel, dort gut sichtbar.

## Frage 15: Hinweis „Bitte warten“ beim Erstellen einer Sicherung und beim Ersetzen

**Das Problem:** Beim Erstellen einer Sicherung und bei „Alles ersetzen“ sah man bisher eine Weile nichts. Jetzt erscheint ein kleiner Kasten mit einem drehenden Kreis. Den Wortlaut hat Chat festgelegt, bewusst ohne Zusage und ohne die Wörter „Abgleich“ oder „GitHub“.

**Was du siehst (Wortlaut von Chat):** „Bitte warten – die Sicherung wird erstellt.“ bzw. „Bitte warten – die Daten werden ersetzt.“ Am PC steht der Kasten mittig im Fenster, am Handy mittig über der Seite.
Auf den PC-Fotos ist das Fenster hinter dem Kasten leer. Das liegt an der Fotoaufnahme, es ist kein Fehler im Programm.

**Optionen:**
- **(a) Ja, so übernehmen.**
- **(b) Ändern:** Du sagst, was du am Aussehen ändern willst. Den Wortlaut ändert nur Chat.

**Empfehlung: (a).**

**Fotos:**
- Foto 15.1: PC, Sicherung, „Normal“, hell.
- Foto 15.2: PC, Ersetzen, „Sehr groß“, dunkel.
- Foto 15.3: Handy, Sicherung, „Normal“, hell.
- Foto 15.4: Handy, Ersetzen, „Sehr groß“, dunkel.

## Frage 16: Kurzer Zwischenschritt nach einem Schrift- oder Farbwechsel

**Das Problem:** Ein Schrift- oder Farbwechsel baut die Oberfläche neu auf. Damit das Fenster dabei bedienbar bleibt, passiert das jetzt in kleinen Schritten. Für einen kurzen Augenblick ist dabei der Bereich „Optische Anpassungen“ schon aufgeklappt, aber noch leer. Im nächsten Schritt erscheint der Inhalt.

**Was du siehst:**
- **Erstes Foto:** „OPTISCHE ANPASSUNGEN“ mit „zuklappen“, darunter eine leere Fläche, darunter „Tagesziel“, „Abgleich PC und Handy“, „Sicherung“ und „Datenbank“. Reste der alten Oberfläche sind nicht zu sehen.
- **Zweites Foto:** der fertige Bereich, mit „Schriftgröße“, „Farben“ und so weiter.

**Optionen:**
- **(a) So lassen.**
- **(b) Den Bereich in einem Stück bauen.** Folge: Es gibt keinen leeren Augenblick. Dafür reagiert das Fenster einen etwas längeren Moment nicht.

**Empfehlung: (a).** Der leere Bereich ist nur einen kurzen Schritt lang zu sehen.

**Fotos (hell, Schrift „Normal“ → „Groß“):**
- Foto 16.1: Zwischenschritt.
- Foto 16.2: fertig.

---

# Teil B: Entscheidungen ohne Fotos

## Frage 17: Ziel für die Wartezeit nach einem Schrift- oder Farbwechsel (Windows)

**Das Problem:** Für die Zeit, bis das Programm nach einem Wechsel wieder bedienbar ist, gibt es noch keinen festen Zielwert. Vorgeschlagen war: höchstens 1,5 Sekunden unter Windows. Auf einem Windows-Prüfrechner gemessen, wird es mit der Änderung schneller. Das Ziel ist aber noch nicht erreicht. Der Zielwert ist kein Prüfkriterium, er steht im Bericht.

**Was du siehst:** Nach einem Wechsel ist das Fenster unter Windows nach etwa 1,8 Sekunden (Hell/Dunkel) bis 4,4 Sekunden (Schrift „Groß“) wieder bedienbar. Vorher waren es 2,9 bis 5,5 Sekunden. Danach baut das Programm im Hintergrund weiter. Einzelne Schritte dauern etwa 0,2 Sekunden, bei „Groß“ etwa 0,4 Sekunden. Um diese einzelnen Schritte geht es in Frage 26.

**Optionen:**
- **(a) Ziel 1,5 Sekunden.** Folge: Im Bericht steht offen, dass das Ziel noch nicht erreicht ist.
- **(b) Anderer Wert:** Du nennst ihn.
- **(c) Kein Zielwert.** Dann stehen nur die Messwerte im Bericht.

**Empfehlung (meine): (a).** So bleibt das Ziel sichtbar, und die Lücke steht offen im Bericht.

## Frage 18: Ziel für die Startseite nach einer Antwort

**Das Problem:** Bei sehr viel Lernstand ist die Startseite (am PC „Dashboard“) jetzt schnell, wenn sich nichts geändert hat: etwa 0,2 Sekunden. Nach einer einzigen Quiz- oder Karteikarten-Antwort braucht sie aber etwa 1,5 bis 2 Sekunden. Vorgeschlagen war ein Ziel von höchstens 0,2 Sekunden.
Es gibt einen Antrag an Chat, den Teil „fällig“ schneller zu rechnen. Er ist **noch nicht freigegeben**. Mit diesem Antrag allein liegt die Startseite nach einer Antwort **knapp an 1 Sekunde**: im Mittel 1054 ms nach einer Quiz-Antwort und 949 ms nach einer Karteikarte, also nicht bei 0,2 Sekunden. Gemessen wurde auf dem Testrechner unter Last. Die Zahlen zeigen deshalb nur die Richtung, unter Windows ist nicht gemessen. Für 0,2 Sekunden müssten weitere Teile umgebaut werden, nämlich andere Abfragen und das Zeichnen. Dafür gibt es noch keinen Vorschlag.

**Was du siehst:** Nach einer Antwort dauert es etwa 1,5 bis 2 Sekunden, bis die Startseite mit „Heute fällig: …“ und den Kacheln neu steht. Mit dem Antrag wäre es etwa 1 Sekunde.

**Optionen:**
- **(a) Ziel 0,2 Sekunden.** Folge: Mit dem Antrag allein ist das nicht erreicht. Es braucht weitere Arbeit und neue Vorschläge an Chat.
- **(b) Ziel 1 Sekunde nach einer Änderung.** Ohne Änderung bleibt es bei 0,2 Sekunden. Folge: Mit dem Antrag liegt das knapp an der Grenze, ob es erreicht wird, ist offen. Unter Windows ist nicht gemessen.
- **(c) Kein Zielwert.** Dann stehen nur die Messwerte im Bericht.

**Empfehlung (meine): (b).** 0,2 Sekunden nach einer Änderung bräuchte einen größeren Umbau mehrerer Teile. Über den Antrag selbst entscheidet Chat.

## Frage 19: Uhr-Regel und „Alles ersetzen“

**Das Problem, einfach gesagt:** Du hast entschieden, dass das Programm nicht ins Netz geht, wenn der automatische Abgleich aus ist. Für Geräte mit falsch gehender Uhr gilt deshalb eine „Behalten-Regel“. Sie verhindert einen Datenverlust, nachdem die Uhr richtiggestellt wurde. Dabei hat sich ein neuer, seltener Fall gezeigt. Er tritt nur auf, wenn mehrere Dinge zusammenkommen: Die Uhr geht dauerhaft nach, das Programm wurde neu gestartet, auf zwei Geräten wurde gelöscht, und danach kam „Alles ersetzen“.

**Wortlaut für dich (drei Sätze aus der Liste für dich, von Chat bestätigt, wörtlich übernommen):**
> (1) Uhr geht dauerhaft nach, Neustart, Löschen und „Alles ersetzen“: eine frühere Löschung eines anderen Geräts kann das Eingespielte wieder entfernen. (2) Die Einträge bleiben in der Sicherungsdatei; ein zweites „Alles ersetzen“ holt sie zurück, dann bleiben sie. (3) Gegenüber 0.63.1 geht nichts zusätzlich verloren; die neue Regel verhindert einen Verlust nach dem Richtigstellen der Uhr.

Dass ein zweites „Alles ersetzen“ die Einträge zurückholt und dass sie danach bleiben, ist in einem Testlauf belegt. Die Warnung vor „Alles ersetzen“ ändert sich nicht.

**Optionen:**
- **(a) Behalten-Regel wie gebaut.** Dieser Fall wird als bekannte Grenze in Bericht und Testliste aufgenommen. Folge: wie oben beschrieben.
- **(b) Für die Löschmarken die alte Berechnung.** Die Behalten-Regel gilt dann nur für eigene Einträge. Folge: Der Fall oben tritt nicht auf. Dafür bleibt der Verlust nach dem Richtigstellen der Uhr möglich, wie in 0.63.1 (vermutet, nicht gemessen).
- **(c) Die Uhr-Regel nicht in 0.63.2.** Folge: Sie wird verschoben, und drei bekannte Verlustwege bleiben offen. Nicht empfohlen.

**Empfehlung: (a)**, so empfehlen es Chat und der Bauer. Der Fall, den die Regel schließt, ist häufiger und betrifft echte Lerndaten eines anderen Geräts. Der neue Fall ist seltener, und die Daten liegen weiter in der Sicherungsdatei.
**Wichtig:** Dieser Teil wird erst übernommen, wenn du geantwortet hast.

**Dazu zur Kenntnis (ein Satz):** Die Beschreibung deiner Entscheidung „kein Netzzugriff bei ausgeschaltetem automatischem Abgleich“ ist um einen weiteren Fall erweitert: Bei einem Gerät mit falsch gehender Uhr können auch nach einer Löschung **auf diesem Gerät** gelöschte Einträge wieder auftauchen; verloren geht dabei nichts.

## Frage 20: „Projekt löschen“, wenn noch ein Gerät mit 0.63.1 im Abgleich ist

**Das Problem:** Ein Gerät mit 0.63.2 löscht ein Abschlussprojekt. Ein anderes Gerät hat noch 0.63.1 und dazu einen später gespeicherten Text dieses Projekts. Dann geht es zwischen den beiden hin und her: Bei jedem Abgleich wird einmal hochgeladen, das Gerät mit 0.63.1 behält seinen Text, und das neue Gerät hat ihn nicht. Das endet, sobald das alte Gerät auf 0.63.2 aktualisiert ist (im Test belegt).

**Was du siehst:** Auf dem Bildschirm nichts Besonderes. Im Abgleich wird bei jedem Durchgang etwas „übernommen“, solange das alte Gerät noch 0.63.1 hat.

**Optionen:**
- **(a) Als bekannte Grenze annehmen.** In Bericht und Testliste steht dann: „bald alle Geräte aktualisieren“.
- **(b) Nicht annehmen.** Folge: Es braucht eine andere Löschregel. Die ist nicht entworfen, und die bisher bekannte Alternative hätte den Schutz aus 0.63.1 gebrochen.

**Empfehlung: (a)**, so empfiehlt es die Prüfung. Das Hin und Her endet mit dem Update, und eine andere Regel ohne neue Nachteile ist nicht bekannt.
**Wichtig:** Dieser Teil wird erst übernommen, wenn du geantwortet hast.

## Frage 21: Andere Umsetzung der Regel beim „Projekt löschen“ (Widerspruch möglich)

**Das Problem:** Eine frühere Festlegung lautete: Löschen gilt unabhängig von der Zeit. Sie wird anders umgesetzt als ursprünglich geplant. Gelöscht werden nur Textstände, die nicht leer sind und nach der Löschung des Projekts gespeichert wurden. Wörtlich umgesetzt hätte die alte Fassung den Schutz aus 0.63.1 gebrochen: Ein Gerät mit 0.63.1 hätte den privaten Projekttext behalten.

**Satz von Chat für dich (wörtlich, er spricht von dir in der dritten Person):**
> „Gleicher Zweck, andere Umsetzung, weil die ursprüngliche Fassung den Schutz aus 0.63.1 gebrochen hätte; er kann widersprechen“

**Optionen:**
- **(a) Einverstanden.**
- **(b) Ich widerspreche.** Folge: Chat entscheidet neu. Die Umsetzung wird erst übernommen, wenn das geklärt ist.

**Empfehlung: (a).**

## Frage 22: Startzeit des Rechners unter Windows (Grenze „G1“)

**Das Problem:** Für das erste Öffnen des Rechners unter Windows gibt es zwei Grenzen.
- Die verbindliche Grenze ist eingehalten: höchstens 0,1 Sekunden langsamer als Version 0.62.5.
- Eine zusätzliche, strengere Grenze aus Version 0.63.1 heißt „G1“: nicht langsamer als der langsamste Einzelwert von 0.62.5. Sie ist um 39,1 ms gerissen, wenn der Rechner nicht vorgeladen ist.

| Messung (Windows, ein Lauf) | ms |
|---|---|
| 0.62.5, Bezugswert der verbindlichen Grenze | 1603,4 |
| 0.62.5, langsamster Einzelwert (Grenze G1) | 1622,1 |
| verbindliche Grenze (0.62.5 + 100) | 1703,4 |
| **0.63.2 ohne Vorladen, mittlerer Wert** | **1661,2** |
| 0.63.2 ohne die neue Abhilfe | 1870,0 |
| 0.63.2 mit Vorladen | 86,2 |

**Was du siehst:** Nichts, der Unterschied ist etwa vier Hundertstelsekunden. Ist der Rechner vorgeladen, öffnet er sofort. Dass das nach dem Start der Normalfall ist, nehme ich an. Gemessen ist es nicht.

**Optionen:**
- **(a) Für 0.63.2 gilt die verbindliche Grenze.** Die Zahlen zu G1 ohne Vorladen stehen offen im Bericht.
- **(b) G1 gilt weiter.** Folge: 0.63.2 ist an dieser Stelle nicht abnahmefähig, bis jemand es schneller macht.

**Empfehlung: (a)**, so empfehlen es Chat und der Bauer. 0.63 und 0.63.1 sind mit größerem Abstand angenommen worden: 0.63.1 lag 238 ms über 0.62.5. 0.63.2 ist hier besser. Eine Endmessung auf dem fertigen Stand kommt noch. Ändert sie das Bild, melde ich mich.

## Frage 23: Ein gemeinsames Mac-Programm für Apple- und Intel-Macs

**Das Problem:** Geplant war, statt zwei Mac-Dateien (eine für Apple-Prozessoren, eine für Intel) eine gemeinsame zu bauen. Mit den offiziellen Dateien geht das nicht, weil eine Bildbibliothek, die das Programm braucht, nur getrennt geliefert wird.

**Ergebnis der Probe:** Es geht. Aus den zwei offiziellen Dateien der Bildbibliothek lässt sich eine gemeinsame Datei für beide Mac-Arten bauen, und das Programm startet damit auf Apple- und Intel-Macs.
Die Probe hat drei Risiken:
- **Selbst hergestellte Datei:** Ihre Prüfsumme kommt nicht vom offiziellen Paketverzeichnis, sondern aus unserem Bau. Geprüft sind nur die beiden Ausgangsdateien.
- **Neues Werkzeug:** Im Bau kommt ein neues Werkzeug dazu.
- **Langsamerer Start:** Auf Intel startet die App langsamer. In der Probe waren es rund 50 Sekunden statt 25, erlaubt sind 240.

**Was du siehst:** Heute und bei (a) gibt es weiter zwei Downloads, „…-macOS-arm64.dmg“ und „…-macOS-intel.dmg“. Die Update-Funktion kennt genau diese Namen.

**Ein Risiko für später:** Der Intel-Mac-Prüfrechner von GitHub hat ein angekündigtes Ende. Fällt er weg, gibt es keinen Intel-Build mehr und auch keinen Starttest auf einem Intel-Mac. Der Text der Veröffentlichung sagt, dass das Programm auf Mac-Rechnern von GitHub einmal gestartet wurde. Das wäre für Intel dann nicht mehr richtig. Heute wird das nur gemeldet. Wie es dann weitergeht, kommt als eigene Frage, wenn es so weit ist.

**Optionen:**
- **(a) In 0.63.2 getrennte Mac-Dateien wie bisher.** Der Bauer empfiehlt dazu wörtlich: „Den Universal-Bau erst mit Freigabe als neue Bauquelle umstellen, solange es den Intel-Runner für den Starttest noch gibt.“ Folge: Der gemeinsame Mac-Bau kommt nicht in 0.63.2, sondern wird verschoben und kommt wieder auf den Tisch. Fällt der Intel-Prüfrechner weg, bevor umgestellt ist, gibt es keinen Intel-Build mehr.
- **(b) Gemeinsame Datei jetzt.** Folge: Es gibt eine neue Bauquelle mit den Risiken oben, und es braucht zusätzlich eine Freigabe von Chat.

**Empfehlung: (a)**, so empfehlen es Chat und der Bauer.

---

# Teil A2: Weitere Fotos (neu in Fassung 2)

## Frage 24: Hinweisschild und Fokusrahmen am PC

**Das Problem:** Am PC haben die Symbolknöpfe jetzt Namen, zum Beispiel „Vorherige Seite“, „Nächste Seite“, „Weniger“ und „Mehr“. Die Namen sind dieselben wie am Handy. Zeigt man mit der Maus auf so einen Knopf, erscheint ein kleines Hinweisschild mit dem Namen. Geht man mit der Tab-Taste auf einen Knopf oder eine Kachel, erscheint ein farbiger Rahmen darum. Das Schild und der Rahmen sind neues Aussehen.

**Was du siehst (nachher):**
- **Maus auf dem Pfeil rechts neben „Seite 1 / 4“:** Darunter erscheint ein kleines dunkles Schild „Nächste Seite“.
- **Derselbe Pfeil, mit der Tab-Taste angesteuert:** Ein farbiger Rahmen um den Knopf (im hellen Modus dunkles Petrol, im dunklen Modus Türkis), darunter das Schild „Nächste Seite“.
- **Kachel mit der Tab-Taste angesteuert:** Ein türkiser Rahmen um die Kachel „Systeme“.

**Optionen:**
- **(a) Ja, so übernehmen.**
- **(b) Ändern:** zum Beispiel eine andere Farbe oder Form für Schild oder Rahmen. Du nennst, was.
- **(c) Kein Schild, nur Rahmen.** Folge: Mit der Maus sieht man den Namen eines Symbolknopfs nicht mehr.

**Empfehlung (meine): (a).** Schild und Rahmen zeigen, welcher Knopf gemeint ist, und sind klein.

**Fotos:**
- Foto 24.1: Hinweisschild mit der Maus, „Normal“, dunkel.
- Foto 24.2: Hinweisschild und Rahmen mit der Tab-Taste, „Sehr groß“, hell.
- Foto 24.3: Kachel mit Rahmen nach der Tab-Taste, „Normal“, dunkel.

## Frage 25: Listentitel, Suchfeld, Banner-Ecke und Trainer-Felder am PC

**Das Problem:** Vier kleine Stellen am PC sahen bisher fehlerhaft aus. Sie sind repariert:
- **Listentitel:** Lange Titel in den Listen (Testprojekt, AP1, Szenarien) brachen mitten im Wort um. Jetzt brechen sie zwischen Wörtern oder nach einem Bindestrich um.
- **Suchfeld:** Oben im Fenster war der Rahmen bei „Groß“ und „Sehr groß“ unten unterbrochen. Jetzt ist er geschlossen.
- **Banner-Ecke:** Auf der Startseite hatte der farbige Kasten im breiten Fenster eine unsaubere Ecke. Jetzt ist sie sauber gerundet.
- **Trainer-Felder:** Im Rechner-Trainer („Netz aufteilen“, „IPv4“, Stufe „Schwer“) stehen die Eingabefelder bei „Sehr groß“ im schmalen Fenster jetzt unter ihrer Beschriftung statt daneben. So passt die Seite ins Fenster.

**Was du siehst:** Im Testprojekt wird vorher „Mehrfaktor-Authentifizier/ung“ mitten im Wort getrennt. Nachher steht „Mehrfaktor-“ am Zeilenende und „Authentifizierung“ ganz in der nächsten Zeile. **Noch nicht gelöst:** Ein sehr langes Wort ohne Bindestrich wird weiter mitten im Wort getrennt, zum Beispiel „Wirtschaftlichkeitsver/gleich“. Das bleibt so, bis die Trennregel aus Frage 9 eingebaut ist.

**Optionen:**
- **(a) Ja, übernehmen.**
- **(b) Ändern:** Du sagst, an welcher Stelle und was.
- **(c) Nein.** Folge: Diese vier Stellen bleiben wie bisher.

**Empfehlung (meine): (a).** Es sind Reparaturen ohne neue Elemente.

**Fotos (Banner-Ecke und Trainer-Felder nur in der Fotoliste):**
- Foto 25.1 und 25.2: Liste Testprojekt, „Groß“, normales Fenster, dunkel, mit Ersatzschrift, vorher und nachher.
- Foto 25.3 und 25.4: Suchfeld bei „Sehr groß“, dunkel, vorher (Rahmen unten unterbrochen) und nachher (Rahmen geschlossen).

---

# Teil B2: Weitere Zielwerte (neu in Fassung 2)

Für alle drei Fragen gilt: Ein Zielwert ist kein Prüfkriterium. Er steht im Bericht, und es steht dort offen, ob er erreicht ist.

## Frage 26: Wie lange darf ein Klick warten? (Windows)

**Das Problem:** Während das Programm im Hintergrund Seiten vorbereitet oder nach einem Wechsel umbaut, kann ein Klick kurz warten müssen. Vorgeschlagen ist ein Ziel: Ein Klick wartet höchstens 150 ms. Diesen Wert gab es schon in einer früheren Version.

**Was gemessen ist (Windows-Prüfrechner):** Die längste Wartezeit beim Vorbereiten lag früher bei etwa 1,2 Sekunden. Jetzt liegt sie bei etwa 0,4 Sekunden (382 ms im Mittel, höchstens 417 ms). Einige Teile liegen noch über 150 ms, zum Beispiel der Rechner (385 ms) und die Szenarien und das Testprojekt (etwa 250 ms). Auch Schritte, die nicht geändert wurden, liegen bei etwa 200 ms. Chat hat festgelegt: Nach einem anderen Umbau (schnelleres erstes Öffnen des Rechners) wird neu gemessen, und dann wird entschieden. Jetzt wird nichts weiter geteilt.

**Optionen:**
- **(a) Ziel 150 ms.** Folge: Im Bericht steht, dass das Ziel noch nicht erreicht ist.
- **(b) Anderer Wert:** Du nennst ihn.
- **(c) Kein Zielwert.** Dann stehen nur die Messwerte im Bericht.

**Empfehlung: (a)**, so steht es im Testplan, als Ziel mit Bericht.

## Frage 27: Ziele für Suche, Notizblock-Suche und Sicherung (Windows)

**Das Problem:** Für drei weitere Wartezeiten gibt es Vorschläge für Zielwerte. Gemessen ist bisher nur auf dem Testrechner unter Last, also keine Windows-Werte. Die Zahlen zeigen deshalb nur die Richtung.

| Was | Vorgeschlagenes Ziel | Gemessen (Testrechner, unter Last) |
|---|---|---|
| Suche oben: bis die ersten Treffer zu sehen sind | höchstens 0,3 Sekunden | 0,16 bis 0,96 Sekunden je nach Suchwort (vorher 0,47 bis 3,0) |
| Suche im Notizblock bei sehr viel Lernstand | höchstens 0,15 Sekunden | etwa 1,2 bis 1,3 Sekunden (nicht schneller geworden) |
| Sicherung erstellen | höchstens 1 Sekunde | etwa 3,2 Sekunden (unverändert) |
| „Alles ersetzen“ | höchstens 1 Sekunde | etwa 5,1 Sekunden (unverändert) |

Für die Notizblock-Suche gibt es einen eigenen Auftrag nach dem Bauabschnitt aus Frage 1. Für Sicherung und Ersetzen siehe Frage 28.

**Optionen:**
- **(a) Alle vier Ziele so übernehmen.** Folge: Im Bericht steht offen, welche Ziele noch nicht erreicht sind.
- **(b) Andere Werte:** Du nennst, für welche Zeile welchen Wert.
- **(c) Keine Zielwerte.** Dann stehen nur die Messwerte im Bericht.

**Empfehlung: (a)**, so steht es im Testplan, als Ziel mit Bericht.

## Frage 28: Ab wann gelten Sicherung und „Alles ersetzen“ als „langsam“?

**Das Problem:** Für Sicherung und „Alles ersetzen“ gibt es einen möglichen Umbau, der sie schneller machen soll. Chat hat festgelegt: Erst wird auf dem neuen Stand noch einmal gemessen. Ist es dann **nicht langsam**, wird nichts gebaut. Ab wann etwas „langsam“ ist, entscheidest du.

**Bisherige Werte:** Früher gemessen wurden 1,7 Sekunden für das Erstellen einer Sicherung und 2,3 Sekunden für „Alles ersetzen“. Jetzt sind es auf dem Testrechner unter Last etwa 3,2 und 5,1 Sekunden. Nach jeder der Schwellen unten wäre das „langsam“. Unter Windows ist nicht gemessen.

**Optionen:**
- **(a) „Langsam“ heißt: über dem Ziel aus Frage 27**, also über 1 Sekunde. Folge: Nach den heutigen Werten wird der Umbau gebaut, mit den Auflagen von Chat.
- **(b) „Langsam“ heißt: über den früheren Werten**, also über 1,7 bzw. 2,3 Sekunden. Folge: Nach den heutigen Werten wird der Umbau ebenfalls gebaut. Wird es durch andere Änderungen schneller, kann er entfallen.
- **(c) Anderer Wert:** Du nennst ihn.

**Empfehlung (meine): (a).** So passt die Schwelle zum Ziel aus Frage 27. Der Testplan hatte vorgeschlagen, den Umbau in jedem Fall zu bauen und die Schwelle nur zu notieren. Chat hat aber festgelegt, dass erst gemessen wird.

---

# Teil C: Nur zur Kenntnis (keine Antwort nötig)

- **„z.B.“ im Rechenweg „Bildschirm“:** Überall heißt es jetzt „z. B.“ mit Leerzeichen. Nur im Rechenweg zur Farbtiefe bleibt „z.B.“ ohne Leerzeichen. Sonst wäre die Handy-Zeile 27 statt höchstens 26 Zeichen lang, und die Handy-Rechenwege, die du abgenommen hast, müssten neu umbrochen werden. Die Stelle steht als bewusste Ausnahme im Bericht und auf der Testliste.
- **Zeitgrenzen der Prüfungen auf GitHub:** Die Untersuchung hat kein zufälliges Fehlschlagen gezeigt. Die Grenzen bleiben, du musst dazu nichts entscheiden.
- **Windows und Mac:** Das Warnfenster aus Frage 7 und alles mit der Schrift Segoe UI sind dort noch nicht geprüft. Das steht auf deiner Testliste.
- **Kasten „Markt“ im Spiel:** Er bekommt dieselbe Rahmen-Reparatur wie Suchfeld und Banner (Frage 25). Das geschieht aber erst, wenn der Spiel-Teil aus Frage 5 übernommen ist. Fotos dazu gibt es noch nicht.
- **Auf deine Testliste (nicht geprüft, Fragen 4, 24 und 25):**
  - der Umbruch langer Titel am Handy,
  - ob beim Durchgehen aller Seiten mit der Tab-Taste jeder Symbolknopf seinen Namen zeigt,
  - wohin die Tab-Taste springt, wenn auf der Startseite eine Kachel geöffnet ist,
  - ob die Tab-Taste auf der Startseite nach einem Farbwechsel noch alle Kacheln erreicht.

  Vermutet, nicht geprüft: Das Hinweisschild aus Frage 24 wandert nicht mit, wenn man mit dem Mausrad rollt.
- **Auf deine Testliste (Prüfungstrainer):** Der Hinweis „Es läuft gerade eine Prüfung …“ nach „Üben“ bleibt seine volle Zeit stehen.
- **Suche oben, Schrittgröße:** Die Treffer erscheinen jetzt in Schritten zu je 12 Zeilen. Auf dem Testrechner unter hoher Last dauerte ein Schritt bis zu 0,5 Sekunden, geplant waren höchstens 0,4. Ob die Schritte so bleiben oder kleiner werden, wird erst nach einer Messung unter Windows entschieden. Dann kommt die Frage, falls nötig, an dich.
- **Bestenliste und Zeitzonen:** Für die Testliste kommt ein Satz zur Bestenliste bei Geräten in verschiedenen Zeitzonen. Kein Eintrag geht dabei verloren. Den genauen Wortlaut klärt Chat noch; du bekommst ihn mit der Testliste.

---

## Antwortzeile zum Ausfüllen

Bitte je Frage den Buchstaben einsetzen. Bei „Ändern“ oder „anderer Wert“ schreibst du kurz dazu, was du willst. Meine Empfehlungen sind schon eingetragen, streiche, was du anders willst. Bei Frage 12 gibt es keine Empfehlung.

`1a 2a 3a 4a 5a 6a 7a 8a 9a 10a 11a 12_ 13a 14b 15a 16a 17a 18b 19a 20a 21a 22a 23a 24a 25a 26a 27a 28a`
