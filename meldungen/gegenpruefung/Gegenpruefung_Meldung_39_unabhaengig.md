# Gegenprüfung Meldung 39 (unabhängig) – Version 0.63.2

Geprüft: `meldungen/Meldung_39_Fotos_und_Fragen_Nico.md` (407 Zeilen) und `meldungen/Meldung_39_Fotoliste.md` (762 Einträge, davon 760 Fotos und 2 Ordner).
Maßstab: REGELN_BAU_0.63.2.md sowie die Weisungen zu Meldung 38/40, 41 und 42.
Die Meldung selbst wurde nicht geändert. Zeilenangaben beziehen sich auf Meldung 39.

Ergebnis: **nicht versandreif.** 2 hohe, 10 mittlere und 12 geringe Befunde. Chats Wortlaute stimmen alle Byte für Byte.

---

## 1. Befunde HOCH

### H1 – E3-Pflichtpunkte aus Meldung 40 fehlen (Weisung 38/40 §6)
Fundstelle: Teil B (Z. 287–391) und Teil C (Z. 397–399). Diese Nico-Entscheidungen aus der E3-Liste fehlen:
- **N6-F1, zweite Hälfte:** Klick-Wartezeit höchstens 150 ms. Frage 17 (Z. 287) fragt nur nach der Zeit bis zur Nutzbarkeit.
- **N7-F5, die übrigen Zielwerte:** Suche höchstens 0,3 s, Notizblock höchstens 0,15 s, Sicherung/Ersetzen höchstens 1 s. Gefragt wird nur der Startseiten-Wert (Frage 18).
- **N7-F4:** die Schwelle „langsam“, ab der Weg 2 greift.
- **N8-F4:** das Aussehen von Hinweis-Blase (Tooltip) und Fokus-Rahmen. Die Fotos liegen vor (`n8/fotos/03…17`), die Meldung zeigt sie aber nicht.
- **N9-F7:** Elemente sichtbar größer.
- **N11-F9:** Wenn der Intel-Runner `macos-15-intel` wegfällt, gibt es ohne gemeinsames Programm keinen Intel-Build mehr.

Korrektur: Eine neue Frage 24 „Weitere Zielwerte“ mit allen Werten in einer Tabelle, jeweils Option (a) „so übernehmen“ und (b) „anderer Wert“, mit Folge und Empfehlung. N8-F4 wird eine eigene Fotofrage mit 2–4 Fotos aus `n8/fotos/03…17`. N9-F7 kommt in Frage 9, N11-F9 in Frage 23 (siehe M10).

### H2 – Punkte aus Meldung 42 „Geht an Nico“ fehlen (Weisung 42 §8)
Fundstelle: Teil C (Z. 397–399). Diese Punkte fehlen:
- die weiteren N8-Fotos: Listentitel, Suchfeld, Bannerecke, Trainerfelder, Tooltip, Kachel mit Tab-Fokus;
- der N8-Kasten „Markt“ nach N5;
- die Testlisten-Punkte zu N8 (B-D-06, Tab-Reihenfolge, Zoom, Farbwechsel, Tooltip mit Mausrad) und zu N15;
- die Schrittweite der Suche (N7) nach der Windows-Messung;
- der Bestenlisten-Satz für die Testliste.

Korrektur: Die fehlenden Punkte kommen wörtlich aus Meldung 42 in Teil C, als Info oder als Ja/Nein-Frage, wie Meldung 42 es vorsieht.

---

## 2. Befunde MITTEL

**M1 – Z. 34, Frage 1, Variante C.** Die Meldung nennt nur „+8 px leer“. Mit Daten ist C aber 677 px breit, also 42 px zu breit (Platz 635, Ersatzschrift-Messung aus `s1c2/nachbesserung/ergebnis.md`). Außerdem fehlt die Folge von C: zwei Tests bleiben rot, und S1c2 kann nicht eingespielt werden. Eine lockerere Grenze hat Chat schon abgelehnt.
Korrektur: „C ist mit Daten 42 px zu breit. Folge: Tests bleiben rot, S1c2 wartet weiter.“ Die Empfehlung B bleibt.

**M2 – Z. 37.** „dieser Teil wartet“ ist unklar. Laut OFFEN_FUER_BERICHT wartet ganz S1c2, also auch das, was Frage 3 zeigt.
Korrektur: „Bis zu deiner Antwort wartet der ganze Bauabschnitt S1c2 (auch Frage 2 und 3).“

**M3 – Z. 42 und Z. 239.** Zwei Platzhalter „⟦Foto folgt⟧“ stehen noch im Text. Das Foto für Frage 13 gibt es schon: Die Wissenslücke ist auf `n9/fotos/handy/spiel_fg106/vergleich_ticket_riesig.png` zu sehen. Der Satz in der Fotoliste, sie sei „nicht unter den 7 Ansichten“, ist falsch.
Korrektur: Bei Frage 13 den Pfad eintragen und die Fotoliste berichtigen. Bei Frage 1 `paar_dejavu_fortschritt_daten_mit_daten_1120_sehrgross_dunkel_s3.png` eintragen.

**M4 – Z. 157, Frage 8.** Die Meldung nennt 12 Fotos vorher und 12 nachher. Es gibt aber nur je 6, und hell + Sehr groß fehlt. Die Quelle `s6b/m38` sagt „16 vorher“, vorhanden sind nur 8.
Korrektur: Die Zahl auf 6/6 berichtigen und die Lücke (hell + Sehr groß) nennen.

**M5 – Z. 163/165, Frage 9.** Die bekannten Fehler bei 200 % fehlen (aus `n9/ergebnis.md` und den Fotos):
- Im Prüfungstrainer ist der Knopf „Antwort ein…“ abgeschnitten.
- Die Legende im Fortschritt wird verdeckt.
- Auch bei 1920 ist die PC-Seite breiter als das Fenster.
- Am Handy ist die Reihe der Schriftgrößen abgeschnitten („Maxim…“). Das ist auf dem Foto zu sehen, laut N9 aber „nicht geprüft“.

Korrektur: Ein Absatz „Bekannte Mängel bei Maximal“, damit Nico nicht annimmt, es sei alles fertig.

**M6 – Z. 183, Frage 10, Option (b).** Die Meldung beschreibt einen „geschützten Baustein“. Gemeint ist laut Meldung 41, Frage 11, aber eine *ungeschützte* Ersatzreihe, deren Diff vorher an Chat geht.
Korrektur: den Wortlaut aus Meldung 41 übernehmen.

**M7 – Z. 229, Frage 13.** Die Meldung tut so, als liege der GradientButton-Vorschlag schon bei Chat. Er ist aber erst für Meldung 43 geplant, und die gibt es noch nicht.
Korrektur: „wird mit Meldung 43 an Chat gehen“.

**M8 – Z. 249, Frage 14, Option (b).** Dort steht „Handy und PC“. Richtig ist „Handy-Listen und Rechner-Blättern gemeinsam“. Den PC betrifft (b) nicht, dort ist das Schloss schon sichtbar (`n15/ergebnis.md`, B-E-03, N-h).
Korrektur: den Satz entsprechend ändern.

**M9 – Z. 308, Frage 18.** „1 s wird erreicht“ ist zu stark. Mit der Änderung liegt der Median im Quiz bei 1054 ms, also knapp über 1 s. Gemessen wurde im Container unter Last, nicht unter Windows (FG-107-Antrag).
Korrektur: „liegt knapp an 1 s; die Zahlen zeigen nur die Richtung, Windows ist nicht gemessen.“

**M10 – Z. 388, Frage 23.** Der Satz mit „solange“ ist verdreht. In der Quelle steht: „…umstellen, solange es den Intel-Runner für den Starttest noch gibt.“ Außerdem fehlt das Risiko N11-F9 (H1).
Korrektur: den Satz aus der Quelle übernehmen und als Folge von (a) ergänzen: „Fällt macos-15-intel weg, gibt es keinen Intel-Build mehr.“

---

## 3. Befunde GERING

| Zeile | Befund | Korrektur |
|---|---|---|
| 13 | Die Handy-Fotos zeigen nicht „unten links“. | Den Hinweis auf den PC beschränken. |
| 40–41 | „nebeneinander“, obwohl die Fotos einzeln sind. „(Inter, hell)“ widerspricht „je hell und dunkel“. „dunkel, mit Daten“, obwohl die Liste auch die leere Tabelle enthält. | Die Beschreibung an die Fotos angleichen. |
| 48 | Bei „c 1“ fehlt das Minuszeichen (FG-103 behebt das später). | Anmerken oder „−1“ schreiben. |
| 132/134 | Der alte Dialog zeigt „Yes/No“ und ein rotes Dreieck, nicht „Ja/Nein“ und ein gelbes. | Berichtigen. |
| 243 | „In allen anderen Fällen gut sichtbar“ stützt sich nur auf Messwerte, nicht auf Fotos. | Ergänzen: „laut Messung“. |
| 259 | Auf dem PC-Foto ist das Fenster hinter dem Hinweis leer. | Erwähnen, damit es nicht wie ein Fehler aussieht. |
| 371 | „Normalfall (vorgeladen)“ ist eine Annahme. | Als Annahme kennzeichnen. |
| 377 | „ms“ wird nicht erklärt. | Ergänzen: „ms = Tausendstelsekunde“. |
| Frage 12 | Die Vergleichsbilder tragen kleine Beschriftungen mit „dp“. | Erklären oder im Text darauf hinweisen. |
| Frage 4 | Auf dem N8-Foto wirkt „Konzeption starten“ heller, vermutlich weil die Maus darüber ist. | Kurz erwähnen. |
| Fotoliste Z. 7 | „Intern: Interne Bezeichnung“ steht doppelt. | Bereinigen. |
| Fotoliste Frage 5 | Verweist auf Inter-Ordner mit rund 600 Dateien. | Auf die DejaVu-Paare beschränken. |

---

## 4. Bestätigt (ohne Befund)
- **Wortlaute (Byte für Byte gleich):** der B1-Satz (W38/40), der Hilfe-Satz (W41 §10), beide „Bitte warten“-Texte (N7-F7) und die drei N14-Sätze (Meldung 42, W42 §4.2/§8).
- **Frage 2:** +1494/+2514 bei 1120 und +1254/+2274 bei 1360, danach 0.
- **Frage 6:** Rechner 810 → 770, AP2 1046 → 982, Testprojekt „breit“, Inter bleibt unverändert.
- **Frage 17:** 1783–4422 ms, vorher 2877–5459 ms.
- **Frage 19:** Inhalt und Regel „Einspielen erst nach Antwort“.
- **Frage 22:** Die G1-Tabelle stimmt (1661,2 / 1703,4 / 1622,1 / 1870,0 / 86,2).
- **„Aussehen offen“:** Die Regeln (kein Bericht, keine Testversion, keine Freigabe vor Nicos Zustimmung) sind richtig dargestellt.
- **Nichts Offenes als entschieden dargestellt:** abgesehen von M7 und M9 ist das so. Keine Frage wiederholt etwas, das schon beantwortet ist.
- **Lesbarkeit:** Jede Frage hat Optionen, Folgen und eine Empfehlung. Ausnahmen: die Folge von C in Frage 1 fehlt (M1), „ms“ ist nicht erklärt.

## 5. Stichprobe Fotos (rund 25 geöffnet, Pflicht waren 15)
Geöffnet und mit dem Text abgeglichen wurden Fotos zu den Fragen 1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 12, 13, 14, 15 und 16. Frage 10 nutzt die Optionen-Fotos von Frage 9. Alle Fotos passen zum Text, bis auf die Befunde M3, M4, M5 und G (Z. 40–41, 132/134, 259, Frage 4).

## 6. Kernauswahl
Siehe `meldungen/Meldung_39_Kernauswahl.md`: 55 Fotos, höchstens 4 je Frage, alle Pfade geprüft. Die Fragen 17–23 haben keine Fotos. Die Handy-Fotos sind sehr hoch (z. B. 768 × 4800 Pixel), deshalb sind Ausschnitte für die Ansicht am Handy empfohlen.

---

# Nachprüfung Fassung 2

Geprüft: `Meldung_39_Fotos_und_Fragen_Nico.md` (624 Zeilen, 28 Fragen), `Meldung_39_Fotoliste.md` (Abschnitt „Kernauswahl“ und Anhang) und `gegenpruefung/Gegenpruefung_Meldung_39_Erledigung.md`. Die Meldung wurde nicht geändert. Zeilenangaben beziehen sich auf Fassung 2.

**Fazit: versandreif ja, nach einer Ein-Satz-Korrektur in Z. 616** (siehe N3). Es gibt keinen hohen oder mittleren Befund mehr. Alle 24 Befunde der ersten Prüfung sind erledigt. Die übrigen neuen Punkte sind gering und blockieren den Versand nicht.

## 1. Erledigung der 24 Befunde
Alle 24 sind sauber erledigt und am Text nachgesehen:
- **H1:**
  - N6-F1 steht in Frage 26.
  - N7-F5 steht in Frage 27, der Wert für die Startseite in Frage 18.
  - N7-F4 steht in Frage 28.
  - N8-F4 steht in Frage 24.
  - N9-F7 steht in Frage 12 (Z. 278) mit Verweis aus Frage 9 (Z. 227).
  - N11-F9 steht in Frage 23 (Z. 492 und 495).
- **H2:** Alle Punkte aus der Liste „Geht an Nico“ (Meldung 42, Z. 445–456) stehen jetzt in der Meldung: Fragen 24/25 sowie Teil C, Z. 606–616.
- **M1–M10 und G1–G12:** wie im Erledigungsvermerk.
  - Bei M1 sind meine Zahlen (Platz 635, +42) durch die neue Messung des Koordinators ersetzt. Das ist richtig so, denn die neue Messung entspricht der Prüfung (`ergebnis.md` Z. 82–83: 851 > 781, erlaubt 70).
  - Keine Platzhalter mehr, 0 Treffer für „Foto folgt“.
  - Fotoliste: 796 Pfade, alle vorhanden. In der Kernauswahl höchstens 4 Fotos je Frage.
  - Antwortzeile mit 28 Einträgen.
- Mit 0 Treffern für „Foto folgt“ und 796 vorhandenen Pfaden ist auch die Fotoliste in Ordnung.

## 2. Neue Fragen 24–28 gegen die Quellen
| Frage | Quelle | Ergebnis |
|---|---|---|
| 24 | `n8/ergebnis.md` Z. 44, 101; Fotos 15/16/17 geöffnet | stimmt: Namen, Schild „Nächste Seite“, Rahmen, Kachel „Systeme“ (Farbe siehe N5) |
| 25 | `n8/ergebnis.md` Z. 21–27, 101; Fotos 03 vorher/nachher, 08 vorher/nachher, 12 geöffnet | stimmt: „Mehrfaktor-Authentifizier/ung“ wird zu „Mehrfaktor-“ + „Authentifizierung“; „Wirtschaftlichkeitsver/gleich“ ist noch nicht gelöst; Suchfeld vorher unterbrochen, nachher geschlossen; Felder unter der Beschriftung |
| 26 | `n6/ergebnis.md` Z. 63–83; Testplan N6 Z. 20/160 (A3 150 ms aus 0.60.1); W42 §2.17 | stimmt (1176 → 382/417 ms; Rechner 385, Szenarien/Testprojekt ~250; unverändert ~200; neu messen nach S5c = Rechner-Start) |
| 27 | `n7/ergebnis.md` Z. 111–124; M40 Z. 114 | stimmt (0,16–0,96 s; Notizblock 1,16–1,30 s; 3,2 s / 5,1 s), Kleinigkeit siehe N7 |
| 28 | Testplan N7 Z. 22/104/171 (1,7/2,3 s aus befunde_HM); W42 §2.18 Frage 23 | stimmt, auch Chats Bedingung „erst messen, nicht langsam = nichts bauen“ |

## 3. Frage 1 gegen `fortschritt_bc_dejavu/messung.txt`
- Die Zahlen stimmen genau:
  - sichtbar 781;
  - heute 851/907;
  - B 781/840;
  - C 788/840.
- Daraus folgt:
  - 70, 126, 7 und 59 Bildpunkte zu breit — richtig gerechnet.
  - „C: eine Prüfung rot“ passt zu den beiden Tests in `ergebnis.md` Z. 82–83: bei C leer 788 > 781 rot, mit Daten 59 ≤ 70 grün.
- Die 4 Kernfotos sind geöffnet und passen zum Text:
  - 1.1: verschoben, links angeschnitten, Rollbalken.
  - 1.2: B passt, ohne „Erfolgsquote“.
  - 1.3: „Quote“, kurzer Rollbalken.
  - 1.4: B mit Daten, Tabelle passt, Rollbalken bleibt.
- Abweichungen siehe N1 und N2.

## 4. Frage 13 gegen die Wissenslücke-Fotos
Geöffnet: `wissensluecke_nachher_dunkel_extra_gross_384`, `…_nachher_dunkel_riesig_384`, `…_vorher_dunkel_riesig_384` und `…_vorher_dunkel_extra_gross_384`.
- Text Z. 311 und Foto 13.3: Bei „Extra groß“ ist der Knopf nachher so breit wie der Kasten, vorher war er nur so breit wie sein Text. Stimmt.
- Text Z. 312 und Foto 13.4: Bei „Maximal“ bleibt der Knopf nachher im Kasten, der Text „Karteikarten zu Dienste“ reicht bis an den rechten Knopfrand. Vorher ragte der Knopf bis an den Kastenrand bzw. darüber. Stimmt, auch mit `n9/ergebnis.md` Z. 47–50.
- Den Satz „Bei Normal gleich“ belegt `n9/ergebnis.md` („pixelgleich“). Die Normal-Fotos habe ich nicht geöffnet.

## 5. Neue Befunde (alle gering, außer N3)

| Nr. | Zeile | Befund | Korrektur |
|---|---|---|---|
| **N3 (mittel)** | 616 | Der Bestenliste-Satz ist sinngemäß falsch wiedergegeben. „kurz nach ‚Bestenliste löschen‘“ und „in einer anderen Zeitzone“ widersprechen Chats Berichtigung (W42 §2.19: „in derselben Sekunde“ ist zu eng; richtig ist: in den **Stunden** nach dem Löschen, so viele, wie der Zonenunterschied beträgt, auf einem Gerät in einer **westlicheren** Zone). „verschobene Uhrzeit“ ist laut `s6b/gp_fg100/abgleich_satz_frage24.md` ebenfalls noch strittig. | Neutral formulieren: „Für die Testliste kommt ein Satz zur Bestenliste bei Geräten in verschiedenen Zeitzonen; der Eintrag bleibt dabei erhalten. Den genauen Wortlaut klärt Chat noch, du bekommst ihn mit der Testliste.“ |
| N1 | 42 | „die Tabelle selbst ist mit und ohne Daten gleich breit“ gilt nur für B (636/636). Bei C sind es 643/670, heute 706/733 (`messung.txt`). Die Aussage „liegt nicht an dieser Tabelle“ bleibt richtig, weil die Tabelle in beiden Varianten unter 781 bleibt. | „In Variante B ist die Tabelle mit und ohne Daten gleich breit; in beiden Varianten passt die Tabelle selbst ins Fenster.“ |
| N2 | 47 | „alle Prüfungen sind grün“ für B ist aus den Messwerten geschlossen. Einen Testlauf mit B habe ich in `s1c2/nachbesserung/logs` nicht gefunden. | „nach den Messwerten sind alle Prüfungen grün“. |
| N4 | 544 | Foto 25.3 zeigt das Suchfeld nur nachher, Nico sieht die Reparatur also nicht. Das Vorher-Foto `08_suchfeld_sehrgross_dunkel_vorher.png` zeigt die Unterbrechung deutlich. | 25.3 als Vorher/Nachher zeigen und dafür 25.4 in die Fotoliste verschieben, oder „Vergleich in der Fotoliste“ vermerken. |
| N5 | 510 | Auf Foto 24.2 (hell) ist der Rahmen dunkel-petrol, nicht türkis. Türkis ist er nur auf dem dunklen Foto 24.3. | „ein farbiger Rahmen (hell dunkles Petrol, dunkel Türkis)“ oder nur „farbiger Rahmen“. |
| N6 | Fotoliste 1079 | Die Beschreibung „heute mit Daten tr, B mit Daten tl/tr, C leer tr“ passt nicht zur Kernauswahl (heute leer tr, B leer tl, C leer tr, B mit Daten tl). | An die Kernauswahl angleichen. |
| N7 | 572 | Dort steht „vorher 0,47 bis 2,9“. Der Höchstwert ist aber 2954 ms (RAID), also 3,0 s. | „0,47 bis 3,0“. |
| N8 | 278 | N9-F7 ist nur für die Auswahlknöpfe beantwortet. Eine Liste „sichtbar größer“ (Testplan N9, K23) gibt es nicht, und das Beispiel GradientButton 46 → 48 geht mit Meldung 43 an Chat. Das ist als Vorgehen vertretbar. | Nur Hinweis für den Bericht, keine Änderung an der Meldung nötig. |

## 6. Geöffnete Fotos in dieser Nachprüfung (17)
- **Frage 1:** 4 Fotos aus `fortschritt_bc_dejavu`.
- **Frage 13:** 4 Wissenslücke-Fotos.
- **N8:**
  - 15, 16, 17;
  - 03 vorher und nachher;
  - 08 vorher und nachher;
  - 12 nachher.
