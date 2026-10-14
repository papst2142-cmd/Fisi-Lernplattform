# Unabhängige Gegenprüfung Meldung 43 (Fragen aus dem Bau)

Prüfer: anderer Agent als der Verfasser, nur lesend. Stand 14.10.2026, etwa 08:51–09:10 UTC.
Geprüft: `meldungen/Meldung_43_Fragen_aus_dem_Bau.md` (375 Zeilen, Datei 08:48:55 UTC) und `gegenpruefung/Selbstpruefung_Meldung_43.md`.
Regeln: `REGELN_BAU_0.63.2.md`, Weisung 42 (Abschnitt 7; 2.1, 2.4, 2.7, 2.11, 2.18, 2.19), dazu Weisung 38/40 (FG-96 Nr. 5), Meldung 42 zum Vergleich.
Nichts an der Meldung geändert, nichts committet, nichts gepusht.

**Urteil: nach Korrektur lieferbar.** Es gibt 2 hohe Befunde: ein veralteter Integrations- und GitHub-Stand und eine falsche Grundannahme in Frage 10. Dazu kommen 7 mittlere und 8 geringe Befunde. Die Zahlen aus den Quellen stimmen bis auf die unten genannten Stellen. Der Satz von Chat zu Frage 24 ist nicht umformuliert.

---

## 1. Selbst nachgeprüft (belegt)

| Was | Ergebnis |
|---|---|
| `git ls-remote origin` | n6 `3ec3665`, n8 `ad0808d`, n9 `352abad`, n14 `02e37b2`, s1c2 `452141b`, s6b `cb60f8b`, fg96 `4d77439`, fix3b `9df7bd8`, `meldungen` `ec41b37`: **stimmen**. **`version-0632` steht auf GitHub auf `8f18818`, nicht auf `e0f9c7e`** (siehe H1). |
| `gh run view` für 9 Läufe (38532489805, 38526544492, 38529539865, 38528086131, 38525544662, 38526665855, 38495818809, 38510468972, 38512762337) | Zweig, Kopf-SHA und Ergebnis je Job stimmen. Dauer des Jobs „rest“: 1637 / 1711 / 1629 / 1440 s, **stimmen**. FG-96 „breite“-Job 264 s (die Meldung nennt 216 s Testzeit, berichtet; stimmt mit `fg96/ergebnis.md`). |
| Neuer Lauf auf `version-0632` | **38537239045** auf `8f18818`, workflow_dispatch, gestartet 08:44:15 UTC, beim Prüfen `in_progress`. |
| Commits und Zeiten | `6cef03c` 06:58:38, `9208fe5` 06:59:53 UTC (stimmen). `6bb8d2f`, `15e4a43`, `6430e36`, `ad0808d` liegen auf `927ef5f..ad0808d` (stimmen). `d96dc5e..cb60f8b`: nur `test_bestenliste_zeitumstellung_0632.py` +152 (stimmt). `72afbe1..352abad`: `mobile/src/spiel.py` +52/−28 (stimmt). Alle lokalen SHAs (`ebfaf7b`, `7e25060`, `0329bc9`, `53a4354`, `8f18818` …) vorhanden. |
| Formatierer-Zeilen auf `352abad` | `spiel.py:64 euro`, `fisi_game.py:1946 _euro`, `:1951 _euro_given`, `:7592 percent_text`, `fisi_game_gui.py:6372 _euro`, `fisi_projekt.py:251 euro`, `fisi_rahmenplan.py:315 percent_text`, `spiel.py:3019` „Handlungskosten %d %%, USt %d %%“: **stimmen**. `14b3bd4:fisi_sicherung.py:661 replace_all`: stimmt. `02e37b2:pruefung/abgleich_geraet.py` kennt `sicherung_erstellen`/`sicherung_ersetzen`; `s1_voll` kommt weder in `ci_tests.sh` noch in `.github/` vor: stimmt. |
| 94 lange Wörter | Tabelle nachgezählt: 94 Zeilen, 92 mit „Listentitel“ (AP1 32, AP2 55, Testprojekte 11), dazu „Ausbildungsverordnung“ (Titel) und „Schnittstellenkennung“ (Rechenweg): **stimmt**. 33 + 94 = 127: stimmt. |
| 8.400 Stellen | Aus `zahl_einheit_stellen.md` nachgerechnet: Code 473 (geschützt 419: 34/144/39/193/9; ungeschützt 54 = 17 + 16 + 6 + 15), Inhalte 7.927, Zeichen 7.622, Wort 778. Bei den Inhalten: quizfragen 2.324, ap2 1.850, ap1 1.400, Vorlagen 1.001. **Stimmt.** |
| FG-107-Diff | sha256 `58f5137f…4b6b`: stimmt. numstat fisi_lernen.py +131/−8, app_gui.py +11/−2, test_leistung_suche_0632.py +12/−2: stimmt. Messwerte (2000/757 → 1054/45; 1487/700 → 949/52; 150 → 113; 415/486 ms; 11,1 MB; 16.000/0; 8 von 8; 163/150; 11/11) gleich wie im Antrag. |
| GradientButton-Diff | +9/−2 nachgezählt (die Quelle sagt +8/−2), wie in der Meldung vermerkt. Tests 23 + 16 + 20 + 13 + 2 = 74 in 5 Dateien: stimmt. |
| Frage 24 | Alle vier Zitate aus Chats Satz sind wortgleich mit Weisung 42, 2.19. Ergebnisse und Fälle (+2 h / +2 h 1 s / +6 h 1 s, −2399 s, „Zonenunterschied − 1 s“, 23 Fälle) stimmen mit `abgleich_satz_frage24.md`. |
| `meldungen` `ec41b37` | Commit-Text „Meldung 39: Fotos und Fragen an Nico (28 Fragen) und Gegenpruefung“: stimmt. |
| Leere Dateien `a`, `n` | vorhanden, 0 Bytes, 05:26:17 UTC, nicht verfolgt: stimmt. |
| FG-Nummern | Verwendet: FG-100 … FG-108, dazu FG-109 nur in Frage 6 (b). Nächste freie Nummer laut Kopfblock: FG-109. **Widerspruchsfrei.** |

---

## 2. Befunde

### Hoch

**H1 – Integrations- und GitHub-Stand veraltet; ein offener Punkt steht als „läuft“, obwohl er abgeschlossen ist** (Zeilen 8, 19, 299, 342–343, sinngemäß auch 87 und 287)
- Die Meldung sagt: Fix 3b ist lokal gemergt, „sein Merge-Tor läuft, Ergebnis offen“. Sie sagt außerdem „Noch kein Push; `version-0632` steht auf GitHub auf `e0f9c7e` (belegt)“, in der Selbstkontrolle (Z. 19) als „belegt“.
- Tatsächlich ist `integration/tor/tor_8f18818.md` seit 08:43:40 UTC fertig, mit dem Urteil **GRÜN MIT MELDUNG**: Die drei GitHub-Listentests sind dort grün, und `bekannt_rot_github.txt` ist jetzt **leer**. Das Protokoll trägt es ein.
- `version-0632` ist auf GitHub `8f18818` (`git ls-remote`, belegt). Damit liegen auch Welle 3c und Fix 3b auf GitHub. Lauf **38537239045** wurde um 08:44:15 UTC gestartet, also vor der letzten Speicherung der Meldung (08:48:55).
- Die Selbstprüfung („Merge-Tor beim Schreiben noch nicht fertig“) ist damit ebenfalls überholt.
- **Korrektur:**
  - Kopfblock 2 und Weitere Punkte 9 neu fassen: „Fix 3b gemergt → `8f18818`, Merge-Tor grün mit Meldung (die 3 Listentests sind jetzt grün, Liste leer). Gepusht ohne Force, `version-0632` = `8f18818` (belegt). Lauf 38537239045 läuft, Ergebnis offen.“
  - Zeile 19 (Selbstkontrolle) und Zeile 299 korrigieren.
  - In Abschnitt C (FG-97) und in Weitere Punkte 3 ergänzen, dass die Liste bekannter roter Tests seit `8f18818` leer ist.
  - Vor dem Push `git ls-remote` erneut ausführen.

**H2 – Frage 10: „Für diesen Fall gibt es keine Regel“ ist falsch** (Zeile 266; Optionen Zeilen 274–277)
- Weisung 42, 2.1 regelt zwar nur die N8-Dateien. Die Freigabe von FG-96 (Weisung 38/40, Nr. 5) regelt den Fall aber ausdrücklich: „Liegt ein Teil nach der Aufteilung über 1350 s, **melden**. Kommen später … weitere Breitentests dazu …; sprengt das die Grenze, kommt eine **neue Frage**, nicht still die Grenze anheben.“
- Weisung 42, 2.1 bestätigt diese Linie für „rest“ („neue E2-Frage, nicht durch (b) gedeckt“).
- Die Frage, was gilt, ist also beantwortet: melden, dann neue E2. Was bleibt, ist der Antrag, die Regel vorab durch eine Automatik zu ersetzen. Die empfohlene Option (a) läuft der bestehenden Regel entgegen, ohne das zu sagen. Option (b) „Wie bisher“ ist in Wahrheit die geltende Regel.
- **Korrektur:**
  - Problem neu fassen: „Nach FG-96 Nr. 5 (Weisung 38/40) melde ich dann mit Messwert, und es folgt eine neue Frage. 2.1 nimmt davon nur die N8-Dateien aus. Ich frage, ob du diese Ausnahme vorab auf jede Datei in ‚breite‘ erweiterst.“
  - Option (b) als „geltende Regel (FG-96 Nr. 5)“ kennzeichnen.
  - Bei (a) als Folge nennen: „Lockerung der Meldepflicht aus FG-96 Nr. 5“.

### Mittel

**M1 – Frage 10, Stand: Erwartung falsch zugeordnet und eine Datei doppelt gezählt** (Zeile 271)
- „N5 (`test_spiel_breite_0632.py`; deine Erwartung 600–750 s)“ stimmt nicht. Chats 600–750 s (Weisung 38/40, FG-96 Nr. 5) gelten für den **ganzen Teil „breite“** mit allen drei Dateien, nicht für die N5-Datei allein.
- „und `test_rechner_seite_breite.py`“ kommt nicht „dazu“. Die Datei steckt schon in den 216 s von FG-96 (`fg96/ergebnis.md`: „breite“ = `test_ansichten_breite` + `test_rechner_seite_breite`; es fehlt nur N5).
- **Korrektur:** „Dazu kommt N5 (`test_spiel_breite_0632.py`, nicht gemessen). Deine Erwartung für den ganzen Teil ‚breite‘ war 600–750 s.“

**M2 – Frage 6 (b): „Alle Geldbeträge im Spiel sind abgedeckt“ ist nicht belegt und falsch** (Zeile 166)
- Die Quelle sagt das nur für das Handy-Spiel (`spiel.py:64 euro()`: „alle € im Handy-Spiel“). In `fisi_game.py` auf `352abad` stehen 23 Zeilen mit „ €“. Viele davon laufen nicht über `_euro()`, zum Beispiel Z. 1287, 1433, 3009, 3017, 3028, 5794 („%d € bei %d € Budget“).
- Auch das Hauptbeispiel „USt 19 %“ deckt kein Formatierer ab. Die „gefundenen Einzelstellen“ sind als Umfang nicht abgegrenzt, obwohl sie später eine Stoppgrenze werden.
- **Korrektur:** „Abgedeckt sind die Beträge, die über die Formatierer laufen, am Handy alle €-Beträge (berichtet). Im PC-Spiel stehen weitere €-Stellen direkt im Text (mindestens 6, belegt). Welche Einzelstellen in den Antrag kommen, nennt der Antrag als Liste.“

**M3 – Frage 9: Chats Satz steht nicht im Wortlaut in der Meldung** (Zeilen 238–263)
- Der Satz ist nicht umformuliert (geprüft, die vier Teilzitate sind wortgleich). Er wird aber nur in Bruchstücken zitiert. Die Frage soll für sich allein verständlich sein, und Chat entscheidet über genau diesen Wortlaut.
- **Korrektur:** Unter „Problem“ den Satz aus Weisung 42, 2.19 wörtlich als Zitat einfügen, Quelle: `abgleich_satz_frage24.md` Zeile 5, gleicher Text.

**M4 – „Nachtrag für Nico“: Ein Punkt steht schon in Meldung 39, ein zweiter nimmt Frage 3 vorweg** (Zeilen 350–353; Frage 3, Zeilen 70–86)
- Erster Punkt: Die Meldung sagt, der Nachtrag sei „nicht in Meldung 39 enthalten“. Der FG-107-Punkt steht dort aber schon vollständig in Frage 18, mit 1054/949 ms und „0,2 s nicht erreicht“ (`ec41b37`, Zeilen 398–410). Die Selbstprüfung sagt dasselbe (OFFEN 07:28 „Nico-Info M39“).
- Zweiter Punkt: Meldung 39, Zeile 85 meldet Nico **schon jetzt** „Nur zur Info“, dass die Unterzeile „Löschen und zurücksetzen“ bei Sehr groß „durch einen Fehler fehlte“ und wieder steht. Das ist praktisch Option (a) von Frage 3, bevor Chat entschieden hat.
- **Korrektur:**
  - Den FG-107-Punkt aus dem Nachtrag streichen oder schreiben: „steht schon in Meldung 39, Frage 18“.
  - Bei Frage 3 offen nennen: „Meldung 39 nennt Nico die Unterzeile schon als behobenen Fehler (Zeile 85, nur zur Info). Bei (b) braucht Nico eine Korrektur.“

**M5 – Frage 8: „Bis ‚Sehr groß‘ ist alles pixelgleich“ ist nur für „Normal“ belegt** (Zeile 223)
- Fotos des Vorschlags gibt es nur für Normal, Extra groß und Maximal (`n9/fotos/handy/gradientbutton_vorschlag/`, 6 Bilder). Auch die Quelle belegt Pixelgleichheit nur bei „Normal“.
- Groß und Sehr groß sind nicht aufgenommen. Dass sich dort nichts ändert, folgt nur aus dem Code (`large()` erst ab 160 %).
- **Korrektur:** „Bei ‚Normal‘ pixelgleich (Ticket: nur Zufallsreihenfolge, berichtet). Groß und Sehr groß nicht aufgenommen; nach dem Code unverändert, weil der neue Zweig erst ab 160 % greift (vermutet).“

**M6 – Frage 3, Stand: „aller 10 Ansichten (Normal/Groß/Sehr groß × 1120/1360)“ ist missverständlich** (Zeile 76)
- 3 × 2 ergibt 6 Kombinationen. Laut Quelle wurden 10 Ansichten in je 6 Kombinationen verglichen. Chat könnte „10“ als Zahl der Kombinationen lesen.
- **Korrektur:** „10 Ansichten, je Normal/Groß/Sehr groß × 1120/1360 (6 Kombinationen)“.

**M7 – Frage 7, Empfehlung: „Gleichheit und Kontrollfehler sind schon vorab belegt“ geht zu weit** (Zeilen 198 und 210)
- Belegt sind 11 von 11 (KF1–KF11 gegen die Zufallsprobe). KF12–KF16 gehören zur neuen Testdatei und sind noch nicht gelaufen. Für KF15 sagt der Antrag selbst „nicht geprüft, ob deterministisch auslösbar“.
- **Korrektur:** „KF1–KF11 vorab rot (berichtet). KF12–KF16 gehören zum Bau; KF15 ist noch nicht als auslösbar belegt.“

### Gering

- **G1** (Zeile 329, Weitere Punkte 6): Der volle Lauf `s1_voll.py` 45/45 lief auf dem **Zweigstand** `02e37b2`. Nach 2.4 braucht es vor dem Merge einen ganzen grünen Lauf **auf dem End-Stand**. Ein Halbsatz verhindert, dass man das als erfüllt liest: „Vor dem Merge erneut auf dem End-Stand“.
- **G2** (Zeilen 10 und 327, „Frage 25 erledigt“): Der Test ist gebaut und grün, liegt aber nur auf dem S6b-Zweig und kommt erst mit dem S6b-Merge in die Integration. Besser: „gebaut, grün auf `cb60f8b`, mit dem S6b-Merge in der Integration“.
- **G3** (Zeile 98, Frage 4): „60 Tests, 2 rot“ betrifft nur die 5 geprüften Klassen (Notizblock, Fortschritt, Optionen, Fortschritt mit Daten, Testprojekt), nicht die ganze Datei mit 83 Tests. So benennen.
- **G4** (Zeile 89, Frage 4): Weisung 42, 2.5 betrifft den Konflikt FG-97 × N10 in `apk_pruefen.py`. Die Regel hier sinngemäß anzuwenden, ist richtig. Besser „sinngemäß nach 2.5“ schreiben.
- **G5** (Zeilen 250–255, Frage 9): Die Randbemerkung 3 der Quelle fehlt: Einträge in derselben Sekunde oder bei zurückgestellter Uhr werden auf Marke + 1 s **später** gesetzt (FG-100, gewollt). Für einen neuen Wortlaut kann das wichtig sein („früher“ gilt nur in eine Richtung). Einen Satz ergänzen.
- **G6** (Zeilen 257–259 und 230–232): In den Optionen von Frage 9 und Frage 8 fehlt ein ausdrückliches „Folge:“, anders als in den übrigen Fragen. Zu Frage 9 (a): „Folge: Bericht und Testliste warten auf deinen neuen Wortlaut.“ Zu Frage 9 (b): „Folge: Der Satz verspricht weiter eine Anzeige, die es nicht gibt.“
- **G7** (Zeile 337, Weitere Punkte 8): Auf dem N6-Zweig blieb der Zeittest bei Last 9,0 beim Wiederholen rot. Das als „kein Tor“ zu werten, ist vertretbar. Nach 2.15 ist „wieder rot“ aber „echt rot“, und auf ruhigem Rechner wurde erst bei Last 4,6–4,8 grün gemessen. Gut, dass es offen genannt ist. Die Bewertung „nicht gezählt“ sollte ausdrücklich als E1 gekennzeichnet sein.
- **G8** (Zeile 336): Der Zähler „Zeittest rot in weiteren Toren: 0“ kann um das Tor `tor_8f18818` ergänzt werden (kein roter Zeittest, belegt im Tor-Protokoll).

---

## 3. Pflichtinhalte Weisung 42, Abschnitt 7

| Pflicht | Stelle | erfüllt |
|---|---|---|
| Antwort auf 2.4 (Zufallsablauf mit „Alles ersetzen“), ein Absatz Einschätzung | Frage 5 | ja |
| Zahl der Wörter ohne Eintrag und geprüfte Quellen (2.11 Nr. 2) | Frage 1 | ja |
| Stellen „Zahl und Einheit“ (Zahl, Texte, Datei) (2.7) | Frage 6 | ja (M2 zur Folge in (b)) |
| Stand der gebauten FG | Abschnitt C | ja, aber Stand veraltet (H1) |
| Ergebnis der Probe zu Frage 24 | Frage 9 | ja (M3: Satz wörtlich ergänzen) |
| Antrag zu Frage 21 (FG-107) | Frage 7 | ja |
| Zusätzlich aus 2.7: GradientButton-Vorschlag | Frage 8 | ja |
| Eine Hinweiszeile je Meldung | Zeile 357 (Platzhalter bis zum Push) | ja |

## 4. Nichts als erledigt, was offen ist?
- Kein Fall, in dem Offenes als erledigt dargestellt wird.
- Umgekehrt steht Erledigtes als offen da (H1: Tor und Push).
- Grenzfälle sind G1 (s1_voll auf dem Zweig) und G2 (Frage 25 nicht integriert).
- FG-107, GradientButton, „Zahl und Einheit“ und der Test „lange Wörter“ sind richtig als „nicht gebaut“ gekennzeichnet.

## 5. Doppelt gefragt?
- Die Fragen 1–9 sind neu oder werden von Weisung 42 als Folgeschritt verlangt. Keine wiederholt eine schon beantwortete Frage.
- **Frage 10:** 2.1 beantwortet sie nicht. Die geltende Regel für diesen Fall steht aber in FG-96 Nr. 5 (Weisung 38/40): melden, dann neue Frage. Siehe H2. Die Frage ist als Antrag auf Erweiterung zulässig, darf aber nicht als „keine Regel“ gestellt werden.

## 6. Satz zu Frage 24
**Nicht umformuliert.** Die zitierten Teile sind wortgleich mit 2.19, und der Vorschlag ist klar als „Angebot, nicht gegen die Probe geprüft“ gekennzeichnet. Der Satz fehlt aber im Wortlaut (M3).

## 7. Format
- Zeile 1 und 2 sind richtig.
- Der Kopfblock hat 6 Punkte, die blockierenden Fragen stehen zuerst.
- Jede Frage enthält Problem, Stand, Optionen, Empfehlung, Blockiert und Belege. Ausnahme ist die fehlende „Folge:“ bei Frage 8 und 9 (G6).
- Die Belegstufen sind durchgängig angegeben. Zeitprognosen gibt es keine (Suche ohne Treffer; die Laufzeitangaben in Frage 5 sind als vermutete Messgrößen gekennzeichnet).
- FG-Nummern ab FG-109 sind widerspruchsfrei.

## 8. Zur Selbstprüfung
- Ihre Nachzählungen stimmen.
- Überholt ist sie in zwei Punkten: Abschnitt 2 („`version-0632` `e0f9c7e`“) und Abschnitt 6 („Merge-Tor `8f18818` nicht fertig“). Beides fällt unter H1.
- H2 übersieht sie in Abschnitt 4, weil sie Frage 10 nur gegen 2.1 prüft, nicht gegen FG-96 Nr. 5. Auch M1, M2, M4 und M5 übersieht sie.
