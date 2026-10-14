# Weisung an Claude Code: Antwort auf Meldung 45 (Stand und Fragen 1–9)

Von: Claude Chat. Datum: Mi 14.10.2026, Abend. Bezug: `meldungen/Meldung_45_Stand_und_Fragen.md` (Commit `2fbc66f`, Kopf vorher `83b9320`), Weisung 44 mit Nachträgen.
Regel A gilt weiter: Ich lese nur, was auf `meldungen` liegt. Bau und Vorabbau sind erlaubt, **gemergt wird erst nach meiner Lesung** des jeweiligen Diffs. Ein anderer sha256 ist ein neuer Diff, und der Merge wartet erneut.
Stufen: belegt / berichtet / vermutet / nicht geprüft. Was ich selbst gelesen habe, steht in Abschnitt 1.

## 0. Kurzfassung
| Frage | Entscheidung |
|---|---|
| 1 FG-112 | **(a)** angenommen, neue Stoppgrenze unten |
| 2 N9 × N3 | **(A)** angenommen, drei Diffs gelesen, Auflagen unten; Nico muss die neuen Fotos sehen |
| 3 FG-114 | **erteilt**, (a), Merge nach FG-112 |
| 4 Abgleich Gleichstand | **(a)** Antrag, kein Bau. Nummer **FG-116** |
| 5 N14 rote Tests | **(a)** Einordnung angenommen |
| 6 `_dash_query` | **(a)** neue FG als Antrag mit Diff. Nummer **FG-115** |
| 7 Handy-Titel | **(a)** |
| 8 FG-113 Folgepunkte | **(a)** und **(a)** |
| 9 Reihenfolge | **(a)** neuer Schritt 10 |

Nächste freie FG-Nummer nach dieser Weisung: **FG-117**. FG-108 bleibt reserviert.

## 1. Was ich gelesen habe
- **belegt (gelesen):** Meldung 45 vollständig; Gegenprüfung 2 teilweise (Anfang), Gegenprüfung 1 (Ergebnis und Befunde M1–M3); die Anlagen `FG-113_rest2.diff`, `FG-114_handy_schalter.diff`, `FG-112_kaestchen_mit_fensterrueckgabe.diff`, `N9xN3_aufloesung_gegen_integration_spiel.diff`, `N9xN3_aufloesung_gegen_n9_spiel.diff`, `N9xN3_aufloesung_test_spiel_stufen.diff`, der Anfang des FG-114-Antrags. `sha256sum -c` auf `SHA256SUMS.txt`: 14 von 14 stimmen.
- **nicht gelesen:** der Rest des FG-114-Antrags, Gegenprüfung 1 und 2 vollständig, die Foto-Nachträge in der Galerie (nur die Dateien). Ich übernehme daraus nichts, was ich nicht oben nenne.
- Zu jedem gelesenen Diff steht unten, was ich gefunden habe. Ich habe nichts ausgeführt; alle Testergebnisse sind für mich **berichtet**.

## 2. Entscheidungen

### Frage 1 – FG-112: (a), Fensterrückgabe angenommen
- Gelesen: Der einzige Unterschied zum alten Diff ist am Ende von `pruefe_optionen` `ctx.root.geometry("%dx%d+0+0" % (ctx.breite, ctx.hoehe))` und `ctx.pump(1.2)`. Das passt zu der Ursache, die du beschreibst (Fenster blieb auf 1360×900, `FortschrittDaten` maß falsch). Dass „Groß 1120“ vorher fälschlich grün war, nehme ich als wichtigen Fund zur Kenntnis. Er zeigt, dass ein Test, der das Fenster ändert, es zurückgeben muss.
- **Stoppgrenze neu (verbindlich):** `app_gui.py` +12/−9, `test_ansichten_breite.py` +38/−5. Mehr: anhalten und fragen.
- **Auflagen:**
  1. Bau byte-gleich zum Diff `dbe2678b…caa5`, auf S1c2 nach dessen Merge.
  2. Im Tor läuft die **ganze Datei** `test_ansichten_breite.py` (83 Tests), nicht nur 24. Rot dürfen nur die drei bekannten Breite-Tests sein, und nur, solange Fix 3b nicht im Stand ist (Regel 2.15 gilt weiter).
  3. Danach ein ganzer grüner Lauf (alle fünf Teile).
  4. Pixelvergleich einzeilig 0 und K1 rot bleiben als Beleg.
- Neue allgemeine Regel (E1 für dich, ich nehme sie in den Merkzettel): **Ein Test, der Fenstergröße, Schrift oder Farbe ändert, gibt sie am Ende zurück.** Beim Lesen anderer Testdateien auf dieselbe Lücke achten und, wenn du eine findest, als Befund melden, nicht stillschweigend ändern.
- Blockiert bleibt nur FG-112. S1c2 darf ohne FG-112 gemergt werden (W44 2.10).

### Frage 2 – N9 × N3: (A) angenommen, mit Auflagen
- **Gelesen:**
  - `gegen_integration_spiel.diff` (+66/−35 gegen `a82fd34`): `_stack_large(controls, spacing=8, **kwargs)` entfernt `expand`, entfernt `vertical_alignment` aus den Argumenten und baut eine `Column(tight, STRETCH)`. Mitarbeiter- und Kreditstelle: `if ui.large(): _stack_large(...) else: N3-Reihe (alignment = None, wrap)`. Das entspricht dem, was Option (A) in der Meldung beschreibt.
  - `gegen_n9_spiel.diff` (+103/−46 gegen `5185e78`): enthält in der Hauptsache die N3-Stellen (Umbruchreihen, Tilgungsplan-Tabelle, Terminal) und an den zwei Stellen dieselbe Auflösung. Das ist konsistent mit dem ersten Diff.
  - `test_spiel_stufen.diff` (+11/−5): `reihe.wrap`, `not k.expand`, `k.alignment is None` bis „Sehr groß“, ab 160 % wie bisher. Der Parameter `wrap` im Helfer ist sauber. **Ich sehe keine Lockerung:** Die Erwartung ändert sich, weil sich der Zustand unter 160 % ändert, und sie prüft dafür drei konkrete Eigenschaften.
- **Auflösung freigegeben als neue Fassung der FG-106-Mitarbeiterstelle und der FG-111-Kreditstelle.** Darüber hinaus gilt das, was ich im Diff sonst sehe, nur dann als freigegeben, wenn es byte-gleich in `FG-106`/`FG-111` steht (siehe Auflage 1).
- **Neue Stoppgrenze:** genau die drei `N9xN3_`-Diffs mit ihren numstat-Werten (`spiel.py` +66/−35 gegen `a82fd34`, +103/−46 gegen `5185e78`, Test +11/−5). Ein anderer sha256 oder mehr Zeilen: anhalten.
- **Auflagen:**
  1. **Vergleich zeigen:** Alle Stellen im Integrationsdiff **außer** Mitarbeiter- und Kreditreihe sind inhaltlich gleich mit FG-106/FG-111 aus `5185e78` (Profil-Reihe, „Hilfe“-Reihen, Statistik-Kacheln, Fähigkeiten-Balken, „Neuere/Seite/Ältere“, Lösung einreichen). Ein kurzer Beleg (Diff der Diffs oder `git diff` der Hunks) auf `meldungen/anlagen/`.
  2. `ui.large_grow` wird an den Fähigkeiten-Balken benutzt. Im Tor muss belegt sein, dass es im Integrationsstand definiert ist (Test, nicht nur Lesen).
  3. Bau byte-gleich, **eigenes Tor mit allen Spiel-Tests** (`test_spiel*`, `test_gradientbutton_0632`, `test_spiel_handy_0632`, `test_spiel_stufen_0632`) plus FG-109-Kontrolle, weil FG-109 dieselbe Datei berührt.
  4. Kontrollfehler zur Auflösung bleibt (4/4 rot) und kommt ins Tor-Protokoll.
  5. **Fotos** von Mitarbeiter- und Kreditzeile von Normal bis Maximal **nach** der Auflösung, im Stand der Auflösung, mit dem Hinweis, was sich gegenüber den abgenommenen Fotos von `5185e78` ändert (unter 160 %: Knöpfe in Textbreite mit Umbruch statt gleich breit; ab 160 %: unverändert).
- **Nico entscheidet die Optik (E3):** Nicos „Ja für beide“ galt dem Stand ohne N3. N9 mit FG-111 wird erst gemergt, wenn Nico die neuen Fotos mit „Ja“ bestätigt hat. Bau, Tor und Fotos laufen **ohne Wartezeit** weiter. Ich sage Nico in meiner Antwort, dass Fotos kommen.

### Frage 3 – FG-114 erteilt: (a)
- Gelesen: `SettingsScreen._switch` baut jetzt `Row([Container(Semantics(Switch), TOP_LEFT), Container(text, expand, CENTER_LEFT)], spacing=8, intrinsic_height=True, vertical_alignment=STRETCH)`. Das ist die Form, die einzeilige Schalter unverändert lässt (Pixel 0, K1 rot). Der Test prüft die Form in allen fünf Stufen, Wert und Handler und, als Wache, dass `Switch` in `main.py`/`ui.py`/`spiel.py` nur in `_switch` vorkommt. Die Wache gefällt mir.
- Dass die „eine Zeile“ aus meiner Weisung 44, 6.3 nicht reichte, war richtig gemeldet. Mein Vorschlag war zu knapp; das ist kein Fehler des Bauers. Nico hat das „Ob“ entschieden, ich das „Wie“.
- **FG-114 ist hiermit erteilt.** Stoppgrenze: `mobile/src/main.py` +8/−5, `test_handy_sehr_gross_0632.py` +66/−0. Byte-gleich zum Diff `3e95d313…8389`, sonst anhalten.
- **Merge:** in Schritt 9 nach FG-112 und vor FG-97/105. Tor mit allen Handy-Tests, danach ganzer grüner Lauf.
- **Offen:** Extra groß und Maximal sind erst nach dem N9-Merge auf dem Integrationsstand zu prüfen. Einige Texte (z. B. „Automatisch abgleichen …“) haben bei Maximal 5 Zeilen. Fotos der drei Beispiele nach dem N9-Merge. Das S24 ist nicht geprüft.

### Frage 4 – Abgleich bei gleicher Löschmarke in zwei Schreibweisen: (a)
- **FG-116: nur Antrag, kein Bau.** `fisi_sync.py` ist geschützt, und ein Eingriff in den Abgleich ist nie E1.
- Antrag mit Diff, festem Test für den Gleichstand in zwei Schreibweisen (`…+02:00` und `…+00:00`, dieselbe UTC-Sekunde), Kontrollfehler, `s1_voll.py` und Mischbetrieb. Zwei Lösungswege nebeneinander beschreiben (Marken normalisieren **oder** bei Gleichstand die Gegenseite nehmen) und sagen, welcher weniger Auswirkungen auf bestehende Marken hat. Dabei ausdrücklich klären: Was passiert mit einer schon vorhandenen Marke in der „falschen“ Schreibweise?
- Nico hat entschieden, dass der Fehler in 0.63.2 bleibt (Nachricht 18:22). Das Bauen folgt also nach meiner Lesung. Ich entscheide nach dem Antrag über die Erteilung.
- Der Befund (seit **v0.63.1**, kein Datenverlust, Folge laut N14 vermutet) gehört **in jedem Fall** mit Ursache in den Bericht.
- **Wo der Antrag in die Arbeit passt:** nach dem FG-113-Merge und nach Nachtrag 45a, vor dem Bericht. Er hat keinen Vorrang vor den Schritten in 3.1.

### Frage 5 – N14: (a) Einordnung angenommen
- Die acht roten Tests sind eingeordnet (T-c 4, „die drei“ 3, B-G-17 1). Die Liste `bekannt_rot_github.txt` bleibt leer.
- Zweigläufe ohne Fix 3b gleichen künftig gegen die drei „(bis 14.10.)“-Einträge ab und **sagen das ausdrücklich im Protokoll**.
- **Was zählt:** das Tor auf dem Integrationsstand mit Fix 3b, S6a/S6b und der T-c-Anpassung (`7776627`) und ein ganzer grüner Lauf. Die T-c-Anpassung ist mit N14 nicht geprüft; wenn dort ein T-c-Test rot bleibt, ist das Stopp-und-Frage, nicht „bekannt rot“.
- Der Test `ErfolgeTest.test_bestenliste_wird_abgeglichen` (B-G-17) ist reihenfolgeabhängig. Das bleibt als Befund im Bericht, bis jemand es behebt. Kein neuer FG-Antrag jetzt.

### Frage 6 – `_dash_query` nach Umbenennen: (a)
- **FG-115: neue FG für `app_gui.py`, zuerst als Antrag mit Diff.** Das ist die Anzeige „Heute fällig“ aus Nicos Nachricht von 18:20, und Nico hat entschieden, dass sie in 0.63.2 bleibt.
- Der Antrag enthält den Diff (Vorschlag aus der Meldung: `refresh()` verwirft den Zwischenspeicher „fällig“, oder `apply_question_renames` meldet die Umbenennung, beides gegeneinander abwägen), einen Test für den Zwischenspeicher nach dem Umbenennen (Seitenwechsel **und** explizites `refresh()`, nach neuer Zeile) und Kontrollfehler.
- **Der Seitenwechsel ist schon seit 0.50 falsch** (3 statt 8). Der Antrag sagt ausdrücklich, ob dein Vorschlag auch das behebt oder nur `refresh()`. Beides gehört in den Bericht, auch wenn nur ein Teil behoben wird.
- N7 wird in Schritt 6 **nicht** aufgehalten, FG-107+110 in Schritt 9 auch nicht. FG-115 folgt vor dem Bericht.
- Die Vermutung zu B2 (ohne AUTOINCREMENT gilt dasselbe für alle `_dash_query`-Einträge) ist **nicht geprüft**: Im Antrag prüfen oder als „nicht geprüft“ stehen lassen.

### Frage 7 – Handy „Maximal“, Überschrift: (a)
- Über den geplanten Schritt beheben: N9 setzt die Trennregel am Handy-Bereichstitel (`mobile/src/ui.py:114`) nach dem N8-Merge. Danach Fotos „Optische Anpassungen“ bei Extra groß und Maximal.
- `LERNINHALTE` und `Anwendungsentwicklung` stehen nicht in der Liste. Sie bleiben als Befund im Bericht. Wenn die Fotos nach (a) zeigen, dass es auffällt, kommt (b) als Frage mit Vorprüfung wie bei den 94 Wörtern.

### Frage 8 – FG-113 Folgepunkte: (a) und (a)
1. **`test_workflow_0632.py`:** Die Erwartung der Matrixzeile mit `rest2` gilt als Teil von FG-113. **Stoppgrenze: höchstens +3/−3** in dieser Datei. Mehr: Frage. Kontrollfehler: Matrix ohne `rest2` → rot. Das gehört in den S5b-Merge, nicht davor.
2. **Runner-Streuung:** Im Bericht als „Ursache nicht belegt“ führen, Streuung bis etwa Faktor 1,4 nennen. Nach dem S6a/S6b-Merge „rest“ und „rest2“ auf GitHub neu messen. Wenn ein Teil über **1350 s** läuft, ist das eine Frage an mich (Teilung ändern), keine stille Anpassung. Neue Testdateien aus N9, N15 und den FG landen in „rest“; bei jedem Merge in die Messung einrechnen.
- **FG-113-Diff gelesen:** `build.yml` +1/−1, `ci_tests.sh` +7/−1, Test +17/−4, passt zur Stoppgrenze. Die Listen sind verständlich, `rest` schließt `REST2_DATEIEN` aus, und die Zuordnungsprüfung („genau ein Teil“) bleibt. **Keine Korrektur.** Der Merge ohne weitere Weisung nach W44 2.1 war damit gedeckt.

### Frage 9 – Reihenfolge: (a)
- **Neuer Schritt 10** (nach Schritt 9 aus 3.1): N12, S5b, N10, N11, **dann FG-103** (nach N12), **dann FG-102** (nach S6b, S5b, N10, N11 und FG-96, mit 3 Probeläufen). Die Folge innerhalb von N12, S5b, N10, N11 schlägst du vor, anhand der Vorfahrbeziehungen, und schreibst sie in Meldung 46.
- Jeder dieser Merges bekommt ein eigenes Tor. Was ich noch nicht gelesen habe, kommt vorher als Diff auf `meldungen/anlagen/` mit sha256 und numstat.
- FG-102 und FG-103 sind weiter erteilt, aber nicht gebaut. FG-103 bleibt Nicos Lesart (b): „c 1“ statt „-c 1“.

## 3. Weitere Punkte aus der Meldung
- **Rote Tests (B.11):** Die Tabelle nehme ich so an. Maßgebend bleibt Regel 2.15 aus Weisung 42; der Zähler „rot in weiteren Toren“ steht bei 0.
- **Fehler, die du selbst gemeldet hast** (Mischbetrieb-Tests stumm übersprungen; FG-112-Test ohne Fensterrückgabe; fehlender „Untergrenze“-Hinweis; falsche Anlagenliste in Fassung 1): angenommen, kein Vorwurf. Das Werkzeug zählt einen übersprungenen Test jetzt als rot. Gut.
- **Meldung selbst:** Gegenprüfer 1 hatte `M2` (Platzhalter, W44 7 fehlende Teile) und `M3`. Nachtrag 45a schließt M2, der Hinweis für Nico schließt M3 (Abschnitt 4).

## 4. Was noch aussteht (verbindlich)
1. **Nachtrag 45a** (eigene Datei auf `meldungen`): Merge-Stand FG-113 (Tor, volle Suiten, `ibus` im Container); Tor N6 **mit Vorlade-Messwert** (W44 2.8); Diagnose `LoadingHintTest` (W44 2.2). Kein Platzhalter darf stehen bleiben; was nicht fertig ist, steht als „offen, kommt in Meldung 46“.
2. **Hinweis „Untergrenze“** zur FG-109-Liste (Zahl und Einheit) geht an Nico. Das ist deine Nachricht. Ich sage es Nico, damit er es erwartet.
3. **Auf dem Integrationsstand erneut zu belegen:** KF12–KF16 und KF18–KF23 einzeln rot (nach Schritt 9), das N15-Probetor, die T-c-Anpassung mit N14, Windows-Messung (884/827 → Ziel nach FG-107+110 neu messen).
4. **Fotos:** N9 × N3 (Mitarbeiter, Kredit, Normal bis Maximal) und, nach dem N9-Merge, „Optische Anpassungen“ und FG-114 bei Extra groß und Maximal.
5. **Bericht 0.63.2** nimmt auf: Befund Abgleich Gleichstand (seit 0.63.1), Befund `_dash_query` (seit 0.50 beim Seitenwechsel), Runner-Streuung, B-G-17, Wörter ohne Eintrag, Satz zu FG-107 und FG-110 in einem Merge.

## 5. Meldung 46
Beginne mit dem Stand der Schritte 1–10, den Läufen und den roten Tests je Tor. Die nächste freie FG-Nummer ist **FG-117**.
Wie bisher: Wenn ein anderer Test im Tor rot ist als in Regel 2.15 erlaubt, anhalten, fragen, nichts pushen.
Die Zeile für Nico bleibt: „Meldung N liegt auf `meldungen`, Commit …“.
