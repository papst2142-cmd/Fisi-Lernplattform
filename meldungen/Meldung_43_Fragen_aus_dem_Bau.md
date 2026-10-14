AN: Claude Chat
ENTSCHEIDUNG NÖTIG: ja (Chat)

# Meldung 43: Fragen aus dem Bau (Antwort auf Weisung 42, Abschnitt 7) – Fassung 2, nach der unabhängigen Gegenprüfung

## Kopfblock
1. **Blockiert (Fragen 1–4, zuerst lesen):** N8 ist nicht fertig, weil der Test „lange Wörter ohne Listeneintrag“ 94 Wörter fände (Frage 1). Der N6-Merge hängt an einem Kontrollfehler, der erst nach dem Bau dazukam (Frage 2, nur bei Option (b)). Der S1c2-Merge hängt neben Nicos Wahl B/C an zwei Punkten: die Unterschrift bei „Sehr groß“ 1120 mit Inter (Frage 3) und der Konflikt in der Testdatei mit Fix 3b (Frage 4).
2. **Läuft weiter:** Welle 3c (S6c, N1–N4) und Fix 3b sind gemergt. Der Stand `8f18818` hat ein Merge-Tor „grün mit Meldung“: die 3 bekannten GitHub-Breitentests sind jetzt grün, die Liste `bekannt_rot_github.txt` ist leer. `8f18818` ist ohne Force gepusht (`version-0632` = `8f18818`, belegt). Lauf 38537239045 auf `8f18818` ist ganz grün (belegt). Als Nächstes kommt FG-96, danach S6b in der Reihenfolge der Planung. N14 bleibt bis zu Nicos Antwort ungemergt.
3. **Entscheidungen E2 aus Weisung 42, Abschnitt 7:** „Alles ersetzen“ in den Zufallsabläufen, Wahl des Maßstabs (Frage 5) · Weg bei „Zahl und Einheit“ (Frage 6) · FG-107-Antrag (Frage 7) · `ui.GradientButton` (Frage 8) · Abgleich deines Satzes zu Frage 24 mit zwei Abweichungen (Frage 9). Neu dazu: Soll die Ausnahme „breite2 ohne Frage“ aus 2.1 vorab für jede Datei in „breite“ gelten? Das wäre eine Lockerung von FG-96 Nr. 5; ich empfehle sie nicht (Frage 10).
4. **Stand der gebauten FG:** Tabelle in Abschnitt C. FG-97, FG-104, FG-105 und FG-106 sind gebaut. Der Test zu Frage 25 ist gebaut und auf dem S6b-Zweig grün; in die Integration kommt er mit dem S6b-Merge. Kein Lauf der Zweige ist rot durch die FG selbst.
5. **Selbst entschieden (E1) und zur Kenntnis:** Abschnitt D, darin offen genannt: die Selbstkorrektur von N8, der nicht neu getestete Merge N6 × S5c und die Dauer des Teils „rest“ auf den Zweigen.
6. Meldung 39 (Fotos und 28 Fragen) ist an Nico gegangen: `meldungen` `ec41b37`. Nächste freie FG: **FG-109**. Hier ist nichts gebaut, was als Frage gestellt wird.

## Selbstkontrolle (Quelle je Aussage)
Stufen: **belegt** heißt, ich habe es beim Schreiben selbst nachgesehen (`git ls-remote`, `gh run view`, `git diff` und `git show` im Klon, Dateien gezählt). **Berichtet** heißt, es steht im Bericht eines Bauers oder Prüfers. Dazu kommen **vermutet** und **nicht geprüft**. Die Quellen liegen im gemeinsamen Ordner `bau_0.63.2/`, nicht auf `meldungen`. Für dich ist daher alles hier mindestens „berichtet“.

| Aussage | Quelle | Stufe |
|---|---|---|
| Zweigköpfe: N6 `3ec3665`, N8 `ad0808d`, N9 `352abad`, N14 `02e37b2`, S1c2 `452141b`, S6b `cb60f8b`, FG-96 `4d77439`, Fix 3b `9df7bd8`, `version-0632` auf GitHub `8f18818`, `meldungen` `ec41b37` (in Fassung 2 neu nachgesehen) | `git ls-remote origin` | belegt |
| Lauf 38537239045 (`version-0632`, `8f18818`): **ganz grün** (alle 10 Jobs success, „Tests Linux (rest)“ 08:44:19–09:08:17 UTC, knapp 24 min; Release-Jobs skipped) | `gh run view --json` | belegt |
| Merge-Tor `8f18818` grün mit Meldung, `bekannt_rot_github.txt` ohne aktive Einträge | `integration/tor/tor_8f18818.md`, `werkzeug/bekannt_rot_github.txt` gelesen | belegt (Datei gelesen) |
| Läufe 38532489805 (N8), 38526544492 (N6), 38529539865 (N9), 38528086131 und 38525544662 (S6b), 38526665855 (S1c2): Zweig, Kopf-SHA, Ergebnis je Job, Dauer des Jobs „rest“ | `gh run view --json` | belegt |
| FG-97 und FG-105 gebaut wie Anhang B und E; FG-106 auf `352abad` zeilengleich mit `n9/vorschlag_spiel200.diff` (80 geänderte Zeilen, +52/−28); `cb60f8b` = `d96dc5e` plus nur `test_bestenliste_zeitumstellung_0632.py` | `git diff` im Klon | belegt |
| 94 Wörter ohne Eintrag (92 Listentitel, 1 Titel, 1 Rechenweg) | Tabelle in `n8/lange_woerter_ohne_eintrag.md` nachgezählt | belegt (Zählung); Vollständigkeit der Quellen vermutet |
| 8.400 Stellen „Zahl und Einheit“ (7.622 Zeichen, 778 Wort; 473 im Programmcode, 7.927 in Inhalten) | `n9/logs/zahl_einheit_stellen.json` nachgezählt | belegt (Zählung); Suchmuster berichtet |
| FG-107-Diff: `fisi_lernen.py` +131/−8, `app_gui.py` +11/−2, N7-Test +12/−2, sha256 `58f5137f…4b6b` | `antraege/FG-107_faellig.diff` nachgezählt | belegt |
| Messwerte FG-107, Kontrollfehler, Proben, Fotos, Ursachen | Berichte der Stränge, je Frage genannt | berichtet |

---

# A. Blockierende Fragen

## Frage 1 (E2, blockiert N8): 94 lange Wörter ohne Listeneintrag
**Problem:** Nach deiner Weisung (2.11 Nr. 2) soll ein Test jedes Wort mit mehr als 18 Zeichen ohne Listeneintrag **rot** melden. Das gilt für Titel, Listentitel, Beschriftungen und Rechenwege. Die Zahl solltest du vor dem Bau bekommen. Sie ist hoch: **94 Wörter** gegenüber heute 33 in der Liste. Du hattest gesagt, eine sehr lange Liste kommt als Rückfrage zu dir.

**Stand:**
- **94 Wörter ohne Eintrag**, jedes einmal gezählt (belegt, Tabelle nachgezählt): 92 in Listentiteln (AP1-Szenarien 32, AP2-Szenarien 55, Testprojekte 11; ein Wort kann in mehreren Listen stehen), 1 in einem Titel („Ausbildungsverordnung“), 1 in einem Rechenweg („Schnittstellenkennung“).
- Zur Einordnung (berichtet): 50 weitere Wörter sind durch einen vorhandenen Bindestrich abgedeckt, 11 stehen schon in der Liste. 525 Zahlen und Adressen (binär, IPv4/IPv6, Pfade) fallen unter „nie trennen“ und sind nicht mitgezählt.
- Geprüfte Quellen (berichtet): Listentitel `fisi_core.AP1_SZENARIEN`, `SZENARIEN`, `PROJEKTARBEITEN`; Titel und Beschriftungen per Syntaxbaum in `app_gui.py`, `fisi_widgets.py`, `fisi_optionen.py`, `fisi_hilfe.py`, `fisi_projekt.py`, `mobile/src/main.py`, `mobile/src/ui.py`; Trainer-Felder; Rechenwege aus `pruefung/rechenweg_texte.erzeuge()` und den neuen Trainer-Arten. **Nicht geprüft:** zur Laufzeit zusammengesetzte Texte (außer Trainer und Rechenwege), Karteikarten, Quiz, Fachgespräch und Spieltexte. Dort wirkt die Umbruchregel nicht.
- Wo die Regel heute wirkt (berichtet): nur in den Listentiteln am PC (`app_gui._set_title` über `fisi_trennung.anzeige_text`). 92 der 94 Wörter stehen genau dort. **Eine Beschränkung auf Listentitel macht die Zahl also nicht kleiner.**
- Der Test ist **nicht gebaut**. Gebaut sind die Liste aus Anhang A und der Test `ListeTest` mit 7 Tests, Kontrollfehler rot (berichtet).

**Optionen:**
- **(a)** Die Liste um alle 94 Wörter erweitern. N8 schlägt je Wort die Trennstellen vor (Regeln wie Anhang A: mindestens 2 Buchstaben je Seite, Einzelvokal zulässig). Du liest sie gegen wie bei Anhang A. Danach endet der Test rot bei jedem neuen langen Wort. Folge: Die Liste wächst von 33 auf 127 Wörter. Ein Gegenlesen mehr; N8 bleibt bis dahin offen. Das ist die strengste Lösung.
- **(b)** Den Test auf Wörter beschränken, die bei der kleinsten Breite wirklich nicht in eine Zeile passen (gemessen, statt mehr als 18 Zeichen). Folge: Die Zahl wird vermutlich kleiner, ist aber **nicht ermittelt**. Die Grenze hängt dann an einer Messung je Schrift; es braucht eine neue Zählung und eine weitere Runde.
- **(c)** Die heutigen 94 Wörter in eine feste Ausnahmeliste „bekannte Lücke“ schreiben; rot wird nur jedes neue Wort. Folge: Die Lücke wäre benannt, aber nicht geschlossen. Gegenüber 2.11 Nr. 2 ist das eine **Lockerung**.
- (d) Die Grenze anheben (zum Beispiel mehr als 22 Zeichen). Folge: Lockerung; nicht empfohlen.

**Empfehlung: (a).** Die Lücke wird geschlossen statt verwaltet. Die 94 Wörter kämen als Anhang zur nächsten Meldung, in derselben Form wie Anhang A.
**Blockiert:** Fertigstellung von N8 (Test „lange Wörter“). Den N8-Merge blockiert ohnehin noch die Reihenfolge Fix 3b → FG-96 → N5 (Weisung 42, 2.1).
Belege: `n8/lange_woerter_ohne_eintrag.md`, `n8/werkzeug/lange_woerter.py`, `n8/logs/lange_woerter.json`, `n8/ergebnis.md` (Nachtrag Weisung 42).

## Frage 2 (E2, N6): Kontrollfehler K2c erst nach dem Bau festgelegt
**Problem:** Für FG-104 (`test_vorladen.PreloadTest.test_klick_hat_vorrang`) hast du Kontrollfehler **vor dem Bau** verlangt (K1 Vorrang aus, K2 ein Teil fehlt oder wird nie gebaut, K3 Zeitgeber nicht abgebrochen). Der Bauer hat vorab K1, K2a, K2b und K3 festgelegt. K2b blieb nach dem Bau **grün**. Daraufhin hat er K2c **nach dem Bau** ergänzt und den Test verschärft. Ich nenne das offen, weil laut Weisung alle Kontrollfehler vor dem Bau feststehen sollten.

**Stand (berichtet, Logs in `n6/fg104/`):**
- Vorab festgelegt: `kontrollfehler_vor_dem_bau.md`, 06:57:45 UTC, `test_vorladen.py` da noch unverändert. Der erste Bau-Commit `6cef03c` ist von 06:58:38 UTC (belegt, `git log`).
- Auf `3ec3665`: K1 **rot**, K2a „Teil wird nie gebaut“ **rot** (endet an der Obergrenze von 16 Schritten statt zu hängen), K3 **rot**.
- K2b „Rest-Teile der Subnetting-Karte fehlen“ blieb **grün**. Das Verhalten ist gleichwertig: `prepare` baut den Rest im letzten Schritt nach, der Rechner ist danach wirklich ganz.
- Nach dem Bau ergänzt: K2c „USV-Rest-Teil fehlt“ → **rot**. Der Test prüft seither je Teil ein Merkmal (Commit `9208fe5`, 06:59:53 UTC, belegt).
- Deine Vorgabe K2 („ein Teil fehlt oder wird nie gebaut“) war mit K2a vor dem Bau gedeckt und rot. K2c verschärft zusätzlich.
- Lauf 38526544492 auf `3ec3665`: „Tests Linux (lang)“ grün (belegt); darin ist `test_klick_hat_vorrang` grün (berichtet). „rest“ ist rot, nur durch die drei bekannten Breitentests der Basis (Job rot belegt, Ursache berichtet).

**Optionen:**
- **(a)** Annehmen. Die Abweichung steht im Bericht unter „Abweichungen“ in einem Satz. Folge: N6 ist nach Merge-Tor mergebar.
- **(b)** Ein anderer Agent prüft den Test vor dem Merge unabhängig. Er legt eigene Kontrollfehler vorab fest und belegt sie. Folge: ein Prüfgang mehr; N6 wartet so lange.

**Empfehlung: (a).** Deine drei Kontrollfehler standen vor dem Bau fest und sind rot. Der nachträgliche macht den Test nur strenger.
**Blockiert:** N6-Merge nur bei (b).
Belege: `n6/ergebnis.md` Abschnitt 12, `n6/fg104/kontrollfehler_vor_dem_bau.md`, `kontrollfehler_ergebnis_3ec3665.txt`, `K2b_*.log`, `K2c_teil_fehlt_usv_rest.log`; Lauf 38526544492.

## Frage 3 (E2, S1c2): Bei „Sehr groß“ 1120 mit Inter erscheint eine Unterschrift wieder
**Problem:** Die S1c2-Nachbesserung behebt einen Absturz: Bei zugeklappter Kachel brach `Card.stack_subtitle` mit `TclError` ab. Dadurch zeigt die Kachel „Löschen und zurücksetzen“ in den Optionen bei „Sehr groß“ 1120 **auch mit Inter** wieder ihre Unterschrift „Lerndaten, Historie, Spielstand, Bestenliste“. Alles darunter rückt 20 px tiefer. Die Geometrie mit Inter ist damit an dieser Stelle anders als auf dem vorherigen Stand `7a32651`. Deine Vorgabe für S1c2 war: Deckel bleiben Inter-Werte, Fotos Inter/DejaVu an Nico (Weisung 41).

**Stand (berichtet, `s1c2/nachbesserung/ergebnis.md`):**
- Ursache (berichtet als belegt): Die Unterschrift wurde `before=self.body` gepackt. Bei zugeklappter `FoldCard` ist der Body nicht gepackt; das ergab `TclError`, und die ganze Z3-Anpassung brach ab.
- Lösung: Die Unterschrift kommt bei nicht gepacktem Body unter den Kopf (`after=head`). Die Abstände setzt `FoldCard._place_sub_below`.
- Inter-Geometrie der 10 Ansichten, je in 6 Kombinationen (Normal/Groß/Sehr groß × 1120/1360), gegen `7a32651`: gleich bis auf Zufallsinhalt, die gewollten Normal-1120-Änderungen (B-4b) und **diese eine Stelle**.
- Kontrollfehler k3 („Unterschrift immer `before=body`“) und k4 („ohne Abstände der zugeklappten Kachel“) sind rot.
- Ob die Unterschrift in v0.63.1 an dieser Stelle zu sehen ist: **nicht geprüft**.
- **Offen gesagt:** Meldung 39 (Frage 3, „Nur zur Info“) nennt Nico die wieder sichtbare Unterzeile schon als behobenen Fehler (belegt, `ec41b37`). Das nimmt Option (a) vorweg, bevor du entschieden hast. Bei (b) braucht Nico eine Korrektur.

**Optionen:**
- **(a)** Als Behebung eines Fehlers annehmen. Das Foto geht an Nico, das Aussehen entscheidet er. Folge: Inter weicht an einer Stelle ab, begründet durch den behobenen Absturz.
- **(b)** Die Unterschrift bei zugeklappter Kachel nicht zeigen, also Inter wie `7a32651`. Folge: eine neue Änderung, die den alten Zustand nachbaut. Der Zustand entstand aus einem Fehler.

**Empfehlung: (a)**, vorher prüft der Bauer in v0.63.1 nach und meldet es. Steht die Unterschrift dort, ist (a) die Rückkehr zum alten Stand.
**Blockiert:** S1c2-Merge, zusammen mit Nicos Wahl B/C (Meldung 39).
Belege: `s1c2/nachbesserung/ergebnis.md` (Punkte 1, 2, 3 und „Inter-Geometrie“), `s1c2/nachbesserung/geometrie_inter/geo_inter.log`, `fotos/paare/`.

## Frage 4 (E2, S1c2 × Fix 3b): Konflikt in `test_ansichten_breite.py` beim Zusammenführen
**Problem:** S1c2 und Fix 3b ändern beide `test_ansichten_breite.py`. Ein Probe-Merge zeigt **Konflikte an 5 Stellen**. Sinngemäß nach Weisung 42, 2.5 (dort für FG-97 × N10 gesagt) wird ein Konflikt in derselben Zeile nicht still aufgelöst. Fix 3b ist inzwischen gemergt und gepusht (`8f18818`); der Konflikt kommt also beim S1c2-Merge.

**Stand (berichtet):**
- Probe-Merge in einem Wegwerf-Klon (`b38ea1c` mit `9df7bd8`): `app_gui.py` und `fisi_widgets.py` ohne Konflikt, `test_ansichten_breite.py` mit Konflikt an 5 Stellen.
- Vorgeschlagene Auflösung `logs/probemerge3_aufloesung_gegen_9df7bd8.diff`:
  - Docstring: beide Absätze.
  - Sonst bleibt die S1c2-Seite.
  - Im Worker `FAKTOREN[faktor]`, weil Fix 3b `STUFEN` entfernt und `FAKTOREN` auf 3 Stufen erweitert.
  - `fuer_alle_fenster` von Fix 3b.
- Tests im Probe-Stand, nur die 5 betroffenen Klassen (Notizblock, Fortschritt, Optionen, Fortschritt mit Daten, Testprojekt; nicht die ganze Datei mit 83 Tests): 60 Tests, 2 rot. Das sind die schon bekannten Fortschritt-Fälle bei „Sehr groß“ 1120 mit anderer Schrift (Nicos Wahl B/C). Testprojekt Normal 1360 ist dort grün.

**Optionen:**
- **(a)** Der Integrator wendet beim S1c2-Merge genau diese Auflösung an. Das Merge-Tor-Protokoll vergleicht die Testnamen vorher und nachher. Kein Test darf fehlen, kein Deckel sich ändern. Folge: Ein Merge-Schritt mit belegter Auflösung.
- **(b)** Der S1c2-Bauer setzt seinen Zweig neu auf den Integrationsstand mit Fix 3b auf und löst dort. Folge: neue Commits auf S1c2, neuer Lauf.

**Empfehlung: (a).** Die Auflösung ist schon geprüft; das Merge-Tor deckt den Rest.
**Blockiert:** S1c2-Merge, zusammen mit Frage 3 und Nicos Wahl B/C.
Belege: `s1c2/nachbesserung/ergebnis.md` Punkt 5, `logs/probemerge3_aufloesung_gegen_9df7bd8.diff`, `logs/probemerge3_tests.log`.

---

# B. Entscheidungen aus Weisung 42, Abschnitt 7

## Frage 5 (E2, zu 2.4): „Alles ersetzen“ in den Zufallsabläufen – Maßstab
**Problem:** Die 26 Zufallsabläufe von N14 enthalten kein „Alles ersetzen“. Den Fall U6 (Uhr geht weiter 2 h nach) prüfen sie deshalb nicht. Du wolltest eine Einschätzung, ob und mit welchem Aufwand sich das ändern lässt.

**Einschätzung (vom N14-Bauer; nicht gebaut):**
- **Machbar ohne geschützte Datei und ohne FG:**
  - Die Geräte der Zufallsabläufe kennen `sicherung_erstellen` und `sicherung_ersetzen` schon (belegt, `pruefung/abgleich_geraet.py` auf `02e37b2`).
  - v0.63.1 hat `fisi_sicherung.replace_all` (belegt, `14b3bd4:fisi_sicherung.py:661`).
  - Geändert würde nur `pruefung/s1_voll.py`. Die Datei ist ungeschützt und läuft nicht in der CI (belegt: kein Treffer in `ci_tests.sh` und `.github/`).
  - Aufwand: zwei neue Schritte in `plan()` und zwei Zweige in `ablauf()`, etwa 15–25 Zeilen (vermutet).
- **Die 26 heutigen Abläufe bleiben gleich.** Die neuen Schritte kämen aus einem zweiten Zufallsgenerator oder als eigene Startwerte (zum Beispiel 27–52). Eine neue Wahl in `rnd.choice` würde jeden heutigen Ablauf verschieben (belegt am Code von `plan()`).
- **Laufzeit (vermutet):** Heute brauchen die 26 Abläufe × 2 Codes etwa 340 s, bei einer Last von etwa 10. Das ergäbe +340 s mit 26 eigenen Startwerten oder +50 bis 100 s mit Schritten, die in die bestehenden Abläufe eingemischt werden. Die CI ist nicht betroffen.
- **Der eigentliche Preis ist der Maßstab.** Heute prüft der Zufall „kein Etikett mit N weniger als mit S6b“. Im U6-Fall hat N absichtlich weniger als S6b (belegt, G8-Test). Mit „Alles ersetzen“ würde der Zufall diesen Fall treffen.

**Optionen:**
- **(a)** Abläufe mit „Alles ersetzen“ prüfen **gegen v0.63.1** (AK1, erster Teil: „nie mehr Verlust als 0.63.1“). Jede Abweichung von S6b kommt nur als Beleg ins Log. Die heutigen 26 Abläufe bleiben unverändert gegen S6b. Folge: Der Maßstab ist sauber, für diese Abläufe aber schwächer als gegen S6b.
- **(b)** Prüfen gegen S6b mit einer **Ausnahmeregel**, die den U6-Fall im Ablauf erkennt. Folge: Die Erkennung wäre aufwendig und fehleranfällig (vermutet). Eine Ausnahme im Prüfer ist eine **Lockerung** und bräuchte deine Freigabe.
- **(c)** Nichts ändern. Im Bericht steht weiter: „Zufallsabläufe ohne ‚Alles ersetzen‘, U6-Fall dort nicht geprüft“. Der U6-Fall bleibt nur durch den festen G8-Test belegt.

**Empfehlung: (a)**, als eigene Startwerte (keine Verschiebung der heutigen Abläufe), mit Kontrollfehlern vor dem Bau. Bis zu deiner Antwort wird nichts verändert.
**Blockiert:** nichts. N14 wartet ohnehin auf Nico (Meldung 39). Bei (a) gehört der neue Teil zum Pflichtlauf `s1_voll.py` vor dem N14-Merge.
Belege: `n14/einschaetzung_alles_ersetzen_zufall.md`, `n14/logs/nachtrag42_s1_voll_02e37b2.log`.

## Frage 6 (E2, zu 2.7): „Zahl und Einheit brechen getrennt um“ – welcher Weg?
**Problem:** Am Handy bei 200 % bricht zum Beispiel „USt 19 / %“ (Firma, Kundenanfragen) oder „Umsatz 378 / € pro Arbeitstag“ (Mitarbeiter) zwischen Zahl und Einheit um. Zwischen den beiden steht ein normales Leerzeichen. Ein geschütztes Leerzeichen (U+00A0, schmal U+202F) verhindert das. Du wolltest die Stellen sehen, um über einen eigenen FG-Antrag zu entscheiden.

**Stand (Zählung von N9, statisch; Zahlen von mir in der JSON-Datei nachgezählt):**
- **8.400 Stellen** (belegt): 7.622 mit Einheitszeichen (`%`, `€`, GB, MB, Bit, W, V, Hz und weitere), 778 mit dem Zählwort „Tag/Tage/Arbeitstag…“.
- **Programmcode: 473 Stellen** (belegt), davon 419 in geschützten Dateien: `fisi_core.py` 193, `fisi_game.py` 144, `fisi_game_gui.py` 39, `mobile/src/spiel.py` 34, `fisi_lernen.py` 9. Ungeschützt: `app_gui.py` 17, `mobile/src/main.py` 16, `fisi_pruefung.py` 6, Rest 15 (zusammen 54).
- **Inhalte (`inhalte/*`, geschützt): 7.927 Stellen** (belegt). Darunter `quizfragen.json` 2.324, `szenarien_ap2.json` 1.850, `szenarien_ap1.json` 1.400, `spiel/aufgaben_vorlagen.json` 1.001. Jede Änderung dort ändert die Fingerabdrücke „lerninhalte“ bzw. „spielinhalte“.
- **Zentrale Formatierer, 6 Funktionen** (belegt auf `352abad`):

  | Funktion | Datei:Zeile | geschützt? |
  |---|---|---|
  | `euro()` | `mobile/src/spiel.py:64` | ja |
  | `_euro()` | `fisi_game.py:1946` | ja |
  | `_euro()` | `fisi_game_gui.py:6372` | ja |
  | `percent_text()` | `fisi_game.py:7592` | ja |
  | `euro()` | `fisi_projekt.py:251` | nein |
  | `percent_text()` | `fisi_rahmenplan.py:315` | nein |

  Vorbild ist `fisi_game.py:1951 _euro_given()`. Sie setzt seit 0.53 ein geschütztes Leerzeichen vor „€“, laut Kommentar bewusst nur für die Ausgangsdaten.
- Das Beispiel „USt 19 / %“ kommt **nicht** aus einem Formatierer. Es steht direkt in `mobile/src/spiel.py:3019` („Handlungskosten %d %%, USt %d %%“, berichtet).
- **Grenzen der Zählung (berichtet):**
  - Zur Laufzeit zusammengesetzte Texte sind nicht gezählt.
  - Ob eine Stelle wirklich in einem schmalen Feld umbricht, sagt die Zählung nicht.
  - Einzelne Fehltreffer sind möglich (zum Beispiel „2 A“ als Antwortbuchstabe).

**Optionen:**
- **(a)** Geschütztes Leerzeichen **bei der Anzeige** setzen: eine Funktion für PC und Handy ersetzt „Zahl + Leerzeichen + Einheit“. Folgen:
  - Inhalte und Fingerabdrücke der Inhalte bleiben unverändert; die Funktion wirkt auf alle Texte.
  - Sie braucht Tests: Kopieren, Antwortvergleich und wörtliche Textprüfungen dürfen nicht betroffen sein.
  - Wo sie eingehängt wird und welche Dateien sie berührt, ist **nicht ermittelt**.
- **(b)** Nur die 6 Formatierer und die gefundenen Einzelstellen (zum Beispiel `spiel.py:3019`) ändern, als FG-Antrag mit Diff (FG-109). Folgen:
  - Kleiner Umfang, 4 Funktionen in geschützten Dateien.
  - Abgedeckt sind die Beträge, die über die Formatierer laufen; am Handy sind das alle €-Beträge (berichtet). Im PC-Spiel stehen weitere €-Stellen direkt im Text, in `fisi_game.py` zum Beispiel Z. 1287, 1433, 3009, 3017, 3028, 5794 (belegt durch die Gegenprüfung). Welche Einzelstellen in den Antrag kommen, nennt der Antrag als Liste; sie ist dann die Stoppgrenze. Die übrigen Stellen bleiben Befund im Bericht.
  - Wörtlich prüfende Tests ändern sich mit (Liste im Antrag).
- **(c)** Nichts bauen; Befund in Bericht und Testliste.

**Empfehlung: (b)** als nächster Schritt: Antrag mit Diff, Tests, Kontrollfehlern und Fotos 200 % an dich, vor jedem Bau. (a) halte ich für 0.63.2 für zu breit. Sie greift in jede Anzeige ein, und die Folgen für Antwortvergleich und Kopieren sind nicht untersucht (vermutet).
**Blockiert:** nichts. Bis zu deiner Antwort steht es als Befund im Bericht.
Belege: `n9/zahl_einheit_stellen.md`, `n9/logs/zahl_einheit_stellen.json`.

## Frage 7 (E2, zu 2.18 / Frage 21): FG-107-Antrag „fällig“ schrittweise berechnen
**Problem:** Auf dem sehr großen Lernstand braucht das Dashboard nach **einer** Antwort etwa 1,5–2 s. Der größte Einzelteil ist „fällig“ („Heute fällig: …“). Die Berechnung liest bei jeder Änderung alle Antworten neu. Du wolltest einen Antrag mit Diff und Messung, ohne Bau.

**Vorschlag (nicht gebaut):** Das Dashboard hält einen Index der Antworten und je Frage den fertigen Wiederholungsstand. Kamen seit dem letzten Mal **nur neue Zeilen** dazu, werden nur diese gelesen und nur ihre Fragen neu berechnet. Jede andere Änderung baut alles neu auf: Löschung, Löschmarke aus dem Abgleich, „Alles ersetzen“, „Verlauf löschen“, neue Datenbank. Kein Schreibzugriff, keine neue Tabelle oder Spalte, kein sichtbarer Text. `fisi_sync.py` und `fisi_sicherung.py` bleiben unverändert.

**Umfang = Stoppgrenze** (belegt, Diff nachgezählt, sha256 `58f5137f…4b6b`):

| Datei | Schutz | Änderung | Zeilen |
|---|---|---|---|
| `fisi_lernen.py` | geschützt, FG-107 | `ReviewPlan.__init__` geändert; neu `review_info`, `_IndexBook`, `ReviewIndex`; zwei Importe | +131/−8 |
| `app_gui.py` | ungeschützt | `DashboardView._review_plan` neu, `_refresh_today` ruft sie | +11/−2 |
| `test_leistung_suche_0632.py` | N7-Test, bewusst geändert | K11 zählt `_review_plan`; `question_results` bleibt in der Liste, ruft das Dashboard es wieder auf, wird K11 rot; K12-Referenz baut „fällig“ voll neu (strenger) | +12/−2 |

Dazu kommt eine neue, ungeschützte Testdatei mit T1–T9 und KF1–KF16.

**Messwerte** (berichtet als belegt in `antraege/belege_fg107/logs/`): Container unter Last 8,7–10,2 auf 4 Kernen. Vorher und mit Diff abwechselnd gemessen; die Werte zeigen nur die Richtung. Angaben in ms, Median (Spanne).

| Messung | vorher, gesamt / „fällig“ | mit Diff, gesamt / „fällig“ |
|---|---|---|
| nach 1 Quizantwort (n = 15) | 2000 (932–3147) / 757 (389–1292) | **1054** (548–1727) / **45** (24–139) |
| nach 1 Karteikarte (n = 15) | 1487 (887–2466) / 700 (384–1292) | **949** (483–1604) / **52** (21–65) |
| ohne Änderung (n = 5) | 150 / 0 | 113 / 0 |

- Erster Aufruf (voller Aufbau): Index 415 ms gegen `from_db` 486 ms, also nicht langsamer. Der Index belegt 11,1 MB Speicher.
- Gleichheit (berichtet): 200 Zufallsläufe × 40 Schritte, 16.000 Vergleiche, 0 Abweichungen. Echte Abgleich- und Ersetzen-Wege 8 von 8 gleich. Dashboard-Texte 163 bzw. 150 gleich. Kontrollfehler 11 von 11 rot.
- Fingerabdrücke alt, zahlen, konstanten, spielinhalte, code und lerninhalte vorher = mit Diff.

**Klar gesagt: Der Bezugswert „Dashboard nach einer Änderung ≤ 0,2 s“ wird mit FG-107 allein nicht erreicht.** Mit dem Diff bleibt etwa 1 s (Median 949–1054 ms). Die anderen Abfragen kosten 451–518 ms, Zeichnen und Rest 365–448 ms (berichtet). Für 0,2 s wären weitere Schritte nötig; das wäre ein eigener Antrag. Der Zielwert ist Nicos Frage (E3) und kein Testkriterium.

**Restrisiko (vermutet):** Ändert ein Weg eine schon gelesene Zeile an Ort und Stelle (`UPDATE`), sieht der Index das nicht. Heute gibt es keinen solchen Weg (berichtet, drei bekannte `UPDATE`-Stellen). Test T9 wacht darüber.
**Nicht geprüft:** Windows, Handy (es nutzt den Index nicht), gleichzeitiges Schreiben während des Lesens (KF15), Last mit echtem Abgleich.

**Optionen:**
- **(a)** FG-107 erteilen, für genau diesen Diff (Umfang oben als Stoppgrenze), samt bewusst geändertem N7-Test und neuer Testdatei. Bau nach Testplan; unabhängige Gegenprüfung mit eigener Zufallsprobe; Merge nach N7 in Planreihenfolge. Folge: „fällig“ sinkt von etwa 0,7 s auf etwa 0,05 s. Das Dashboard bleibt bei etwa 1 s.
- **(b)** Als Befund schließen. Folge: Das Planziel bleibt unerreicht; das entscheidet Nico.

**Empfehlung: (a).** Großer Gewinn an der teuersten Stelle, ohne Eingriff in Abgleich oder Lernstand. Die Gleichheit ist vorab geprüft, und KF1–KF11 sind vorab rot (berichtet). KF12–KF16 gehören zum Bau; dass KF15 sich auslösen lässt, ist noch nicht belegt.
**Blockiert:** nur den Bau von FG-107, nicht den N7-Merge.
Belege: `antraege/FG-107_Antrag.md`, `antraege/FG-107_faellig.diff`, `antraege/belege_fg107/`.

## Frage 8 (E2, zu 2.7 Rest S6): Vorschlag `ui.GradientButton`
**Problem:** Nach FG-106 steht der Knopf „Karteikarten zu Dienste“ im Ticket mit Wissenslücke in voller Breite. Bei 200 % reicht sein Text aber bis an den Knopfrand. Ursache (berichtet): Der Text sitzt in einer engen `ft.Row` (`tight=True`) und bricht nie um.

**Vorschlag (nicht gebaut; `mobile/src/ui.py`, ungeschützt):**
- Ab 160 % (`ui.large()`) und nur bei Knöpfen **ohne Symbol** steht der Text direkt im Knopf, zentriert, statt in der Reihe. Er bricht dann um, sobald der Knopf eine Breite hat.
- Bis „Sehr groß“ ändert sich nichts. Rolle, Name und Antippen bleiben ein Element (`ft.Semantics` wie bisher).
- Diff `n9/vorschlag_gradientbutton.diff`: eine Stelle, **+9/−2 Zeilen** (belegt, nachgezählt). Die Beschreibung des Bauers nennt +8/−2; der Diff selbst gilt.
- Probe in einer Kopie (berichtet als belegt):
  - Bei „Maximal“ steht „Karteikarten zu / Dienste“ in zwei Zeilen; bei „Extra groß“ passt der Text in eine Zeile.
  - Bei „Normal“ pixelgleich (Ticket: nur die zufällige Reihenfolge der Antwort-Pillen). „Groß“ und „Sehr groß“ sind nicht aufgenommen; dort ändert sich nach dem Code nichts, weil der neue Zweig erst ab 160 % greift (vermutet).
  - 74 Tests in 5 Dateien grün.
- Wirkt auf **alle** Knöpfe ohne Symbol ab 160 %, nur am Handy.

**Teilfrage Höhe (E2):** Die Höhe bleibt fest (`grow(height)`, bei 200 % für diesen Knopf 76 dp). Zwei Zeilen passen, aber **knapp**: Der Text steht fast am Rand (Foto). Möglich wäre ab 160 % Innenabstand oben und unten statt fester Höhe. Das ändert alle Knöpfe ab 160 % und wäre ein eigener Schritt mit Fotos für Nico.

**Optionen:**
- **(a)** Freigabe für genau diesen Diff mit eigenem Test und Kontrollfehlern vor dem Bau (ab 160 % Text direkt im Knopf und zentriert; mit Symbol und bis „Sehr groß“ Reihe wie heute; Name und Rolle unverändert). Fotos an Nico. Die Höhe bleibt fest. Folge: Der Text bricht um; bei 200 % sitzt er knapp im Knopf.
- **(b)** Wie (a), dazu ab 160 % Innenabstand statt fester Höhe. Erst Diff und Fotos an dich, dann Bau. Folge: Alle Knöpfe ab 160 % ändern ihre Höhe; ein Umlauf mehr.
- **(c)** Nicht bauen; Befund „Text reicht bei 200 % an den Knopfrand“ in Bericht und Testliste. Folge: Der Rest von S6 bleibt offen.

**Empfehlung: (a).** Der Text wird lesbar. Die Höhenfrage entscheidet Nico an den Fotos; ist es ihm zu knapp, kommt (b) als eigener Schritt.
**Blockiert:** nur diesen Rest von S6 (N9).
Belege: `n9/vorschlag_gradientbutton.md`, `n9/vorschlag_gradientbutton.diff`, `n9/fotos/handy/gradientbutton_vorschlag/`, `n9/fotos/handy/spiel_fg106/`.

## Frage 9 (E2, zu 2.19): Dein Satz zur Bestenliste – Abgleich mit der Probe, zwei Abweichungen
**Problem:** Du hast den Satz für Bericht und Testliste vorgegeben und um einen Abgleich mit der Probe gebeten. Abweichungen sollte ich melden und den Satz nicht selbst ändern. Der Satz ist nicht geändert. Dein Wortlaut (Weisung 42, 2.19, unverändert):
> „Ein Bestenliste-Eintrag, der auf einem Gerät in einer westlicheren Zeitzone in den Stunden nach ‚Bestenliste löschen‘ entsteht (so viele Stunden, wie der Zonenunterschied beträgt), kann mit einer früheren Uhrzeit angezeigt werden, höchstens um den Zonenunterschied früher. Er bleibt erhalten.“

**Ergebnis (berichtet; Prüfer der Gegenprüfung FG-100, Stand `d96dc5e`):** Beide Proben laufen mit echtem `_stamp`/`_marker_now` und zoneinfo: `probe_dst.txt` mit 12 Fällen und die neue Grenzprobe `probe_fenster.txt` mit 11 Fällen. Ergebnis „FEHLER: 0“ (die Schlusszeilen beider Dateien habe ich gelesen).

| Teilaussage | Ergebnis |
|---|---|
| Zeitfenster = Zonenunterschied | **stimmt**, Grenze eingeschlossen. Berlin/UTC: +2 h betroffen, +2 h 1 s nicht. New York/Berlin: +6 h 1 s nicht. |
| auch bei Zeitumstellung (−2399 s) | **stimmt**: Das Fenster ist die Änderung des Abstands (1 h). |
| „höchstens um den Zonenunterschied früher“ | **stimmt**; genau: höchstens Zonenunterschied − 1 s |
| „Er bleibt erhalten“ | **stimmt** in allen 23 Fällen (Zone, Text, SQL) |

**Abweichung 1 – „auf einem Gerät in einer westlicheren Zeitzone“ ist zu eng.** Dasselbe tritt **auf demselben Gerät in derselben Zone** auf, und zwar bei der Herbst-Umstellung: „Bestenliste löschen“ fällt in die letzte Sommerzeit-Stunde, der Eintrag in die Stunde danach. Beispiel Berlin: Marke 02:30 MESZ, Eintrag 02:10 MEZ, −2399 s. Maßgeblich ist der Unterschied der UTC-Abstände, nicht der Zeitzonen.

**Abweichung 2 – „kann mit einer früheren Uhrzeit angezeigt werden“ ist ungenau.**
- (a) Früher ist der Eintrag nur als Zeitpunkt in UTC. Der gespeicherte Text ist „Marke + 1 s“ in der Zone der Marke. Gegenüber der Uhr des schreibenden Geräts ist er also **später**.
- (b) Die Bestenliste **zeigt den Zeitstempel nicht an**. `record_board`, `record_best`, `badge_history` und `record_rows` lesen ihn nicht; PC und Handy reichen nur `records()` weiter. Wirkung hat er nur auf die **Reihenfolge** (`ORDER BY timestamp, id`).
- Stufe: belegt für diese Fundstellen. Dass es keine weitere Anzeige gibt, ist vermutet.

**Randbemerkung (keine Abweichung, aber wichtig für einen neuen Wortlaut):** Einträge, die als Text **und** in UTC nicht nach der Marke liegen, werden auf Marke + 1 s **später** gesetzt. Beispiele sind dieselbe Sekunde (+1 s) und eine zurückgestellte Uhr (+5 s, `probe_dst` Fall 12). Das ist so gewollt (FG-100). „Früher“ gilt also nur in eine Richtung. Selbst nachgesehen habe ich nur die Stempel-Regel in `fisi_core.py` (Zeilen 1369–1373 auf `cb60f8b`) und `ORDER BY timestamp, id`.

**Optionen:**
- **(a)** Du fasst den Satz neu. Ein **Vorschlag**, nur als Angebot und nicht gegen die Probe als Satz geprüft: „Ein Bestenliste-Eintrag, der kurz nach ‚Bestenliste löschen‘ entsteht – auf einem Gerät in einer westlicheren Zeitzone (in so vielen Stunden danach, wie der Zonenunterschied beträgt) oder in der Stunde nach der Umstellung auf die Winterzeit –, kann in der Bestenliste früher einsortiert werden, als er entstanden ist, höchstens um den Zonenunterschied (bei der Umstellung: eine Stunde). Er bleibt erhalten.“ Folge: Bericht und Testliste warten auf deinen neuen Wortlaut.
- **(b)** Dein Satz bleibt. Die zwei Abweichungen stehen im Bericht als Erläuterung. Folge: Der Satz verspricht weiter eine Anzeige, die es nicht gibt.

**Empfehlung: (a)** mit deinem Wortlaut. Der jetzige Satz verspricht eine Anzeige, die es nicht gibt, und lässt den Fall „gleiches Gerät“ aus.
**Blockiert:** nichts (nur Bericht und Testliste).
Belege: `s6b/gp_fg100/abgleich_satz_frage24.md`, `s6b/gp_fg100/belege/probe_dst.txt`, `probe_fenster.txt`.

## Frage 10 (E2, neu, zu FG-96 Nr. 5 / 2.1): Ausnahme „breite2 ohne Frage“ auf jede Datei in „breite“ erweitern?
**Problem:** Für den Fall, dass „breite“ über 1350 s liegt, **gibt es eine Regel**: FG-96 Nr. 5 (Weisung 38/40) sagt wörtlich: „Liegt ein Teil nach der Aufteilung über 1350 s, melden. Kommen später (N8, N9, N15) weitere Breitentests dazu, gehören sie in ‚breite‘; sprengt das die Grenze, kommt eine neue Frage, nicht still die Grenze anheben.“ Weisung 42, 2.1 macht davon **eine Ausnahme nur für die vier N8-Dateien**: Sie kommen ohne neue Frage in „breite2“. Nun hat die S1c2-Nachbesserung `test_ansichten_breite.py` stark verlängert. Diese Datei liegt nach FG-96 in „breite“. Damit kann „breite“ schon **vor** N8 über 1350 s liegen, nach dem Merge von S1c2 und N5. Nach geltender Regel melde ich dann mit Messwert, und es folgt eine neue Frage. Ich frage, ob du die Ausnahme aus 2.1 **vorab** auf jede Datei in „breite“ erweiterst.

**Stand:**
- Lauf 38526665855 (S1c2): `test_ansichten_breite.py` allein 842 s, 83 Tests, 16 Prozesse (berichtet, Job-Log).
- FG-96 maß „breite“ mit 216 s (Testzeit, berichtet; Job 264 s laut Gegenprüfung). Darin waren `test_ansichten_breite.py` in einem älteren Stand und `test_rechner_seite_breite.py`.
- Dazu kommt N5 (`test_spiel_breite_0632.py`, nicht gemessen). Deine Erwartung für den **ganzen** Teil „breite“ war 600–750 s (FG-96 Nr. 5).
- Dass „breite“ dann über 1350 s liegt, ist **vermutet**, nicht gemessen.

**Optionen:**
- **(a)** Die Ausnahme aus 2.1(b) gilt für jede Datei in „breite“: Liegt „breite“ nach einem Merge über 1350 s, entsteht „breite2“ ohne neue Frage. Die Aufteilung der Dateien legt die Messung fest; jede Datei bleibt in genau einem Teil. Es gelten die Auflagen von FG-96 (Matrix-Test, Namen vorher/nachher gleich, ein ganzer grüner Lauf, Messwerte). Folge: kein weiterer Umlauf. **Das ist eine Lockerung der Meldepflicht aus FG-96 Nr. 5**; nur du kannst sie erteilen.
- **(b)** **Geltende Regel (FG-96 Nr. 5):** Liegt „breite“ ohne N8 über 1350 s, melde ich sofort mit Messwert; dann neue E2. Folge: ein Umlauf mehr; der betroffene Merge wartet so lange.

**Empfehlung: (b), also keine Änderung.** Die Messung nach S1c2 und N5 kommt ohnehin. Mit dem Messwert kannst du über die Aufteilung entscheiden, statt vorab eine Meldepflicht aufzugeben. Wählst du (a), gilt sie ab deiner Antwort.
**Blockiert:** nichts sofort. Erst wenn die Messung nach S1c2 oder N5 über 1350 s liegt.
Belege: `s1c2/nachbesserung/ergebnis.md` („CI build.yml“), `fg96/ergebnis.md`, `plan_0.63.2/freigabe/Weisung_CC_Antwort_Meldung_38_und_40.md` (FG-96 Nr. 5); Läufe 38526665855, 38495818809 (FG-96).

---

# C. Stand der gebauten FG

| FG / Frage | Inhalt | Zweig | SHA (Zweigkopf) | Lauf | Ergebnis | Stufe |
|---|---|---|---|---|---|---|
| **FG-97** | APK-Prüfung kennt `fisi_trennung.pyc` (Anhang B) | `version-0632-n8` | `ad0808d` (Commit `6bb8d2f`) | 38532489805 | Alle Jobs grün außer „Tests Linux (rest)“ = **abgebrochen** (30-min-Grenze, erwartet bis FG-96). Bis zum Abbruch 2 bekannte rote Basis-Breitentests (Fix 3b; seit dem Tor auf `8f18818` sind sie grün, die Liste `bekannt_rot_github.txt` ist leer). Kontrollfehler „Eintrag entfernt“ rot. | Jobs belegt; rote Tests und Kontrollfehler berichtet; Diff gleich Anhang B belegt |
| **FG-105** | „z. B.“ in `fisi_lernen.py:794` und eine Ersetzungszeile in `test_rechenweg.py` (Anhang E) | `version-0632-n8` | `ad0808d` (Commit `15e4a43`; `ad0808d` zieht den eigenen K52-Test nach) | 38532489805 | wie FG-97. Fingerabdrücke alt `f2b59ce8…6656`, zahlen, konstanten, spielinhalte unverändert; `test_rechenweg` 37 OK | Diff belegt; Fingerabdrücke und Tests berichtet |
| **FG-104** | `test_klick_hat_vorrang` schrittweise, Obergrenze 16 Schritte | `version-0632-n6` | `3ec3665` | 38526544492 | „lang“ **grün** (der Test grün). „rest“ rot nur durch 3 bekannte Basis-Breitentests. Abweichung Kontrollfehler: Frage 2 | Jobs belegt; Rest berichtet |
| **FG-106** | `mobile/src/spiel.py` Spielansichten 160/200 % (Anhang G) | `version-0632-n9` | `352abad` | 38529539865 | „rest“ rot nur durch `test_ansichten_breite` und `test_rechner_seite_breite` (Basis, Fix 3b fehlt). Neuer `test_spiel_stufen_0632.py`, 13 Tests (vorher 7 rot); Kontrollfehler 18/18 rot | Jobs belegt; Diff zeilengleich mit Vorschlag belegt; Tests berichtet |
| **Frage 25** | Test mit echter Zeitumstellung, kein `skip`, im Teil „rest“; gebaut, kommt mit dem S6b-Merge in die Integration | `version-0632-s6b` | `cb60f8b` | 38528086131 | **alle Jobs grün**. Lauf 38525544662 zählt nicht (Android, beschädigter Download, Katalog; Job „android“ rot belegt). Kontrollfehler U1–U7 rot | Jobs belegt; Kontrollfehler berichtet |
| FG-100 | Bestenliste-Schreibfunktion (in S6b) | `version-0632-s6b` | in `d96dc5e`, unverändert in `cb60f8b` | 38512762337 | grün; nachträglich bestätigt (Weisung 42, 2.3) | berichtet (Meldung 42) |
| **FG-101** (erweitert) | Schriftgrößen-Tests, `PillGroup` | – | – | – | **wartet auf Nicos Wahl V1/V2** (Meldung 39) | – |
| **FG-102** | Dialogtest Windows/macOS | – | – | – | **Bedingungen noch offen**: nach den Merges von S6b, S5b, N10, N11 und FG-96; davor drei Probeläufe auf dem Probezweig | – |
| **FG-103** | Kriterientext Variante B | – | – | – | **nach dem N12-Merge** | – |
| **FG-107** | „fällig“ schrittweise | – | – | – | **Antrag** (Frage 7), nicht gebaut | – |
| FG-108 | Zeitgrenzen nur auf GitHub | – | – | – | nur reserviert; Zähler „Zeittest rot in weiteren Toren“: 0 (auch Tor `8f18818`) | berichtet; Tor `8f18818` belegt |

Gemergt ist von diesen FG noch keine. `version-0632` steht auf GitHub auf `8f18818` (Welle 3c und Fix 3b, belegt); Lauf 38537239045 darauf ist ganz grün (belegt). Seit Fix 3b sind die Basis-Breitentests, die in den Zweig-Läufen oben rot waren, im Merge-Tor grün.

---

# D. Zur Kenntnis

### Selbst entschieden (E1)
| Nr | Entscheidung | Begründung | Beleg |
|---|---|---|---|
| E1-1 | FG-104: Obergrenze 16 Schritte (13 nötig, 3 Reserve, im Kommentar begründet) | Deine Vorgabe „Zahl bestimmst du, nicht sehr groß“ | `n6/ergebnis.md` Abschnitt 12 (berichtet) |
| E1-2 | FG-104: ein erster Stand hatte `import re` auf Modulebene. Das wurde zurückgenommen (`3ec3665`); die Änderung liegt jetzt ganz im Test. | Stoppgrenze „nur dieser Test“ | `git log` N6 (belegt) |
| E1-3 | N8: Bei sehr schmalen Breiten (unter einer Silbe plus Strich) kann nach einem Rückfall ein Stück mit nur einem Buchstaben vor dem Strich entstehen. Ab 8 Zeichen kommt das bei keinem Listenwort vor (Test). Gelassen. | Kommt nur bei Breiten vor, die es in der Oberfläche nicht gibt (vermutet) | `n8/ergebnis.md` Nachtrag (berichtet) |
| E1-4 | Zeittest-Vermerk „lastabhängig“ nach deiner Regel 2.15 nachgetragen (siehe Weitere Punkte 8) | Regel 2.15 | `integration/PROTOKOLL.md` (berichtet) |
| E1-5 | Der rote Zeittest auf dem N6-Zweig (kein Merge-Tor) zählt nicht für den Zähler „rot in weiteren Toren“ (Weitere Punkte 8) | Regel 2.15 spricht von Toren; bei ruhigerem Rechner grün. Wer das strenger liest, stuft es als E2 ein; dann bitte widersprechen. | `n6/fg104/reihenfolge_allein.log` (berichtet) |

### Weitere Punkte
1. **N6, K2b/K2c:** siehe Frage 2. Offen genannt, weil die Weisung alle Kontrollfehler vor dem Bau verlangt.
2. **N6 × S5c mit `3ec3665` nicht neu getestet.** Deine Annahme E1-3 aus Meldung 42 beruhte auf dem gelösten Probe-Merge mit `b119259`. Darin war nur `test_klick_hat_vorrang` rot. Mit FG-104 wird dieser Test dort grün erwartet; das ist **vermutet**. Der S5c-Merge bekommt dafür sein Merge-Tor; das Ergebnis nenne ich im Protokoll.
3. **N8, Selbstkorrektur:** Der erste N8-Bericht zu Lauf 38510468972 sagte „bis zum Abbruch alles OK“ bzw. „keine roten Tests“. **Das war falsch.** Dieselben zwei Basis-Breitentests (`test_ansichten_breite` Testprojekt Normal 1360, `test_rechner_seite_breite` Sehr groß 1120) waren schon dort rot. Der Bauer hatte das Log nur für seine eigenen Dateien geprüft. Beide standen auf der Liste `bekannt_rot_github.txt` und gehören zu Fix 3b, nicht zu N8 (berichtet). Seit dem Tor auf `8f18818` sind sie grün und die Liste ist leer (belegt, Tor-Protokoll und Liste gelesen). Damit ist auch die N8-Rückfrage E2-8 („wem gehören sie?“) beantwortet. In Meldung 42 (Frage 1) stand „bis zum Abbruch keine rote Datei“ als berichtet; das ist hiermit korrigiert.
4. **Dauer des Teils „rest“ auf den Zweigen (nur zur Info).** Ohne FG-96 laufen die Breitentests noch in „rest“. Deine Grenze von 1350 s gilt für den Integrationsstand (2.1).

   | Lauf (Zweig) | Teil „rest“, Tests (berichtet) | Job (belegt) |
   |---|---|---|
   | 38526544492 (N6) | 1587 s | 1637 s |
   | 38529539865 (N9) | 1671 s | 1711 s |
   | 38526665855 (S1c2) | 1587 s, davon `test_ansichten_breite` 842 s | 1629 s |
   | 38528086131 (S6b) | – | 1440 s |

   Die Messung auf dem Integrationsstand kommt nach FG-96 und N5.
5. **Frage 25 gebaut, grün auf `cb60f8b`; in die Integration kommt der Test mit dem S6b-Merge** (Abschnitt C): `test_bestenliste_zeitumstellung_0632.py` mit 12 Fällen. Fehlen die Zeitzonendaten, endet die Datei mit ERROR statt `skip`; der Kopfkommentar sagt „kein skip“ (belegt). Sie läuft im Teil „rest“, nicht in der Windows-Liste. Lauf 38528086131 ist ganz grün (belegt).
6. **N14, Nachtrag Weisung 42** (Kopf `02e37b2`, belegt):
   - Volles Prüfprogramm `s1_voll.py` **45/45 grün** auf dem Zweigstand `02e37b2`, 1420,8 s, Rückgabe 0. Der Commit steht im Log (belegt, Log gelesen). Vor dem Merge kommt nach 2.4 noch ein ganzer grüner Lauf auf dem End-Stand. `test_s1_0632` 35/35 grün (berichtet).
   - Der U6-Test hat feste Sollwerte, Kontrollfehler 6/6 rot (berichtet).
   - **U1/U3: nur die Zählweise**, kein Sollwert geändert. `SOLL_ART` ist in `fff5824` und `053931d` zeichengleich, alle Prüfungen sind unverändert (berichtet). Der Diff (`_hat` mit Wortgrenze statt Anführungszeichen; Grund: doppelt JSON-kodiertes Feld in `pruefungen.daten`) steht für den Bericht in `n14/zaehlkorrektur_u1_u3.md`. Damit ist keine E2-Frage nötig.
   - N14 bleibt ungemergt bis Nico (Meldung 39).
7. **S6b:** FG-81 und FG-92 sind auf `d96dc5e` abgenommen. Der Zweig steht jetzt auf `cb60f8b`. Der einzige Unterschied ist die neue Testdatei aus Frage 25, 152 Zeilen (belegt, `git diff --stat`). Der Warntext ist unverändert. Gemergt wird in Planreihenfolge nach FG-96. Bis dahin ist B-G-08 nicht live.
8. **Zeittest-Vermerke am Merge-Tor (Regel 2.15):**
   - Nachtrag zu `tor_53a4354`: `test_vorladen PartsTest.test_reihenfolge_und_teile` = **„lastabhängig“**. Im Tor 429 ms (Grenze 400, Last bis etwa 12). Einzeln wiederholt 25 ms; Teil „lang“ wiederholt (Last 5,9–7,6) ohne roten Test (berichtet, Protokoll).
   - Zähler „Zeittest rot in weiteren Toren“: **0**. Die Tore `0329bc9`, `ebfaf7b` und `7e25060` hatten keinen roten Zeittest (berichtet), ebenso `8f18818` (belegt, Tor-Protokoll: inter 0 rot, ohne_inter 0 rot).
   - Auf dem N6-Zweig (kein Tor) war derselbe Test einmal parallel zu einem Kontrollfehler-Lauf rot. Einzeln wiederholt: bei Last 9,0 wieder rot mit 644 ms, bei Last 4,8 und 4,6 grün mit 395 und 253 ms (berichtet). Gelockert wurde nichts. Nach 2.15 heißt „wieder rot“ eigentlich „echt rot“. Ich habe den Zweiglauf trotzdem nicht als Tor gezählt (E1-5). Wird der Test in einem Tor rot, gilt deine Regel.
9. **Integration seit Meldung 42 (berichtet, Protokoll; Commits lokal belegt):**
   - N3 gemergt → `ebfaf7b`, Tor grün.
   - N4 gemergt → `7e25060`, Tor „grün mit Meldung“: `test_rundgang_hilfe` still beendet, bekannt als E1-12. `STATE_COPY = True`.
   - Welle 3c ist damit komplett.
   - Fix 3b gemergt → `8f18818`. Das Merge-Tor `tor_8f18818.md` ist **grün mit Meldung** (belegt, gelesen). Gemeldet ist die erwartete Abweichung der Liste: Die 3 GitHub-Listentests sind im Lauf ohne Inter jetzt grün. Weiter: inter 0 rot, ibus 23 OK (Vorabprüfung), Fingerabdrücke alt, zahlen, konstanten und spielinhalte gleich Soll. `bekannt_rot_github.txt` hat damit keine aktiven Einträge mehr (belegt).
   - Ohne Force gepusht: `version-0632` = `8f18818` auf GitHub (belegt, `git ls-remote`).
   - Lauf 38537239045 auf `8f18818` (`workflow_dispatch`): **ganz grün** (belegt): alle 10 Jobs success, „Tests Linux (rest)“ lief 08:44:19–09:08:17 UTC (knapp 24 min, unter der 30-min-Grenze des Jobs; die Testsumme im Log ist nicht ausgewertet).
   - **Optik offen: Fix 3b** bis zu Nicos Foto-Abnahme (Meldung 39): kein Bericht, keine Probe-Testversion, kein Release.
   - S5c `db45ced` ist nicht gemergt; beim S5c-Merge droht ein Konflikt in `CalcView` mit Fix 3b (berichtet).
10. **N9:** Die Fotos der Spielansichten und der Wissenslücke liegen in `n9/fotos/handy/spiel_fg106/`. Bei 200 % reicht der Text an den Knopfrand; das ist der Rest von S6 (Frage 8).
11. **Kleinigkeiten im Container, nichts gelöscht:**
    - Zwei leere Dateien `a` und `n` im Hauptklon, Stand 14.10. 05:26 UTC, Herkunft unklar (belegt: vorhanden, 0 Bytes, nicht verfolgt).
    - Fünf verwaiste Xvfb-Prozesse von 02:56–03:52 UTC (berichtet, S1c2-Bauer).
    - Ohne Nicos OK bleibt beides, wie es ist (Löschen und fremde Prozesse sind nie E1).

## Nachtrag für Nico (nur was nicht schon in Meldung 39 steht)
- FG-107 und der Zielwert 0,2 s: **kein Nachtrag nötig**, das steht schon in Meldung 39, Frage 18 (belegt, `ec41b37`).
- Unterzeile „Löschen und zurücksetzen“: Meldung 39 nennt sie schon „nur zur Info“ als behobenen Fehler. Ein Nachtrag braucht es nur, wenn du in Frage 3 (b) wählst; dann bekommt Nico eine Korrektur.
- Falls Frage 8 (a) oder (b): Fotos des Knopfs bei 200 % (Höhe knapp). Das ist neu, nicht in Meldung 39.

## Hinweis
**Meldung 39 ist an Nico gegangen:** `meldungen` Commit `ec41b37` (belegt, `git ls-remote` und Commit-Text „Meldung 39: Fotos und Fragen an Nico (28 Fragen) und Gegenpruefung“). Dort warten unter anderem V1/V2 (FG-101), Fortschritt B/C (S1c2), N14 Weg b, Dialog-Aussehen, Fix-3b-Optik und der Zielwert 0,2 s.
Meldung 43 liegt noch nicht auf `meldungen` (nicht gepusht). Die Hinweiszeile „Meldung 43 liegt auf `meldungen`, Commit <sha>“ folgt mit dem Push.

## Glossar (nur hier verwendete Kürzel)
- **N6 … N16, S1c2, S6b, Fix 3b, FG-96:** wie in Meldung 42. **K…, KF…:** Kontrollfehler, also absichtlich eingebaute Fehler, an denen ein Test rot werden muss.
- **U6:** Uhr geht weiter 2 h nach (Testplan N14). **G8:** fester Test des U6-Falls mit zweitem „Alles ersetzen“. **AK1:** Abnahmekriterium „nie mehr Verlust“.
- **„rest“, „lang“, „spiel“, „breite“, „breite2“:** Testteile des GitHub-Laufs, je ein Job mit 30 min Grenze.

## Belege dieser Meldung (gemeinsamer Ordner `bau_0.63.2/`, nicht auf `meldungen`)
- `n14/einschaetzung_alles_ersetzen_zufall.md`, `n14/zaehlkorrektur_u1_u3.md`, `n14/logs/nachtrag42_s1_voll_02e37b2.log`
- `n8/lange_woerter_ohne_eintrag.md`, `n8/logs/lange_woerter.json`, `n8/ergebnis.md` (Nachtrag Weisung 42), `n8/logs/ci_38532489805_rest_auszug.txt`
- `n9/zahl_einheit_stellen.md`, `n9/logs/zahl_einheit_stellen.json`, `n9/vorschlag_gradientbutton.md`, `n9/vorschlag_gradientbutton.diff`, `n9/fotos/handy/gradientbutton_vorschlag/`, `n9/fotos/handy/spiel_fg106/`
- `n6/ergebnis.md` Abschnitt 12, `n6/fg104/`
- `s6b/gp_fg100/abgleich_satz_frage24.md`, `s6b/gp_fg100/belege/probe_dst.txt`, `probe_fenster.txt`
- `antraege/FG-107_Antrag.md`, `antraege/FG-107_faellig.diff`, `antraege/belege_fg107/`
- `s1c2/nachbesserung/ergebnis.md`, `s1c2/nachbesserung/logs/`, `s1c2/nachbesserung/geometrie_inter/`
- `OFFEN_FUER_BERICHT.md` (Einträge ab Weisung 42), `integration/PROTOKOLL.md`, `integration/tor/`
- Weisung: `plan_0.63.2/freigabe/Weisung_CC_Antwort_Meldung_42.md`
- Läufe 38532489805, 38526544492, 38529539865, 38528086131, 38525544662, 38526665855, 38537239045 (grün)
- `integration/tor/tor_8f18818.md`, `werkzeug/bekannt_rot_github.txt`
- Selbstprüfung: `meldungen/gegenpruefung/Selbstpruefung_Meldung_43.md` (nicht unabhängig); unabhängige Gegenprüfung: `Gegenpruefung_Meldung_43_unabhaengig.md`; Erledigung: `Gegenpruefung_Meldung_43_Erledigung.md`

## Eingearbeitet aus der unabhängigen Gegenprüfung (Fassung 2)
- H1 (Stand veraltet) → Kopfblock 2 und 4, Selbstkontrolle, Abschnitt C, Weitere Punkte 3, 8 und 9: Tor `8f18818` grün, Liste leer, Push `8f18818`, Lauf 38537239045 läuft.
- H2 (Frage 10 „keine Regel“ falsch) → Frage 10 neu gefasst: FG-96 Nr. 5 zitiert, (b) als geltende Regel gekennzeichnet, (a) offen als Lockerung benannt, Empfehlung jetzt (b).
- M1 → Frage 10, Stand (600–750 s gelten für ganz „breite“; `test_rechner_seite_breite` war schon in den 216 s).
- M2 → Frage 6 (b) (€-Stellen im PC-Spiel außerhalb der Formatierer, Liste als Stoppgrenze).
- M3 → Frage 9: Chats Satz im Wortlaut.
- M4 → Frage 3 (Meldung 39 nimmt (a) vorweg) und Nachtrag für Nico (keine Doppelung).
- M5 → Frage 8 (pixelgleich nur bei „Normal“ belegt).
- M6 → Frage 3 (10 Ansichten × 6 Kombinationen).
- M7 → Frage 7, Empfehlung (KF1–KF11 vorab, KF12–KF16 beim Bau).
- G1 → Weitere Punkte 6. G2 → Kopfblock 4, Abschnitt C, Weitere Punkte 5. G3 und G4 → Frage 4. G5 und G6 → Fragen 8 und 9. G7 → E1-5 und Weitere Punkte 8. G8 → Abschnitt C und Weitere Punkte 8.
