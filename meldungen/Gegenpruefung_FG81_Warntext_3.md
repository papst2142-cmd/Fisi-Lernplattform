# Dritte Gegenprüfung FG-81 (Weisung zu Meldung 37, Abschnitt 5.3)

**Stand:** 13.10.2026
**Geprüft:** Zweig `version-0632-s6b`, `d54397f` (Commits `7acca07` Tests, `4cdfd39` Text, `d54397f` Kommentar; Basis `dd0c2a0`). lokaler Arbeitsbaum nur gelesen (`git status` leer, HEAD `d54397f`).
**Prüfer:** dritter, unabhängiger Gegenprüfer (nicht der Bauer, nicht die Prüfer von gp_meldung_37 / gp_s6b_*).
**Arbeitsweise:** eigene Kopien per `git archive` (d54397f, dd0c2a0, v0.63.1, 5 Kontrollfehler-Kopien) im Scratchpad `gp3_fg81/`. Nichts geändert, committet, gepusht oder gelöscht.
**Stufen:** belegt (eigener Lauf, Log gelesen) / Code (aus dem Code abgeleitet) / berichtet / vermutet / nicht geprüft.

## Urteil

**Abnahmereif: nein.**
- Der **Wortlaut** ist korrekt eingebaut: byte-gleich mit Weisung 37 Abschnitt 3. Die Tests sind nicht lockerer, die Kontrollfehler stimmen, der AST-Beleg stimmt (alles belegt).
- **Satz 6 und Satz 7 (die neuen Sätze)** stimmen in allen Fällen, die ich gelaufen bin, für alle fünf Löscharten (belegt).
- Zwei Befunde halten die Abnahme auf:
  - **S1 (Anzeige):** Am **Linux-PC** wird der Text im Dialog abgeschnitten, auch bei 1920×1080. Es gibt keine Rolle; man kann den Text nicht verschieben. Bei 1920×1080 fehlen das Ende von Satz 6 sowie die Sätze 7 und 8, bei 1366×768 und 1280×720 schon die Sätze 5 bis 8. Am Handy wird nach meiner Rechnung ebenfalls nur etwa die Hälfte gezeigt (vermutet). Das gab es mit `dd0c2a0` schon. Der längere Text macht es schlimmer, und gerade die beiden neuen Sätze sind betroffen.
  - **M1 (Satz 5, unveränderter Satz):** „Was nach dem Erstellen der Sicherung schon abgeglichen war, bleibt gelöscht“ ist in 4 eigenen Abläufen **falsch**. Was nach der Sicherung gelernt und abgeglichen war, kommt dort zurück. Die Richtung ist ungefährlich (mehr kommt zurück, nichts geht verloren), aber die Aussage ist falsch. Nach Weisung 37, 5.3 melde ich das; ich formuliere nicht um.

## Satz für Satz

Löscharten: AL = „Alle Lerndaten löschen“, HI = „Historie löschen“, BL = „Bestenliste löschen“, SP = Spielstand zurücksetzen/löschen (`Game.reset` → `delete_run`), PR = Projekt löschen. Fälle „g…“ sind Bauer-Tests, die in meinem Lauf auf `d54397f` mitliefen (43 von 43 grün, `logs/gp3_lauf.txt`). Fälle „h…“ sind meine eigenen Abläufe (`skripte/gp3_ablaeufe.py`, Rohdaten `logs/gp3.jsonl`).

| # | Satz (gekürzt) | Löscharten | Beleg | Ergebnis | Stufe |
|---|---|---|---|---|---|
| 1 | „Ist der Abgleich eingerichtet, kommen beim nächsten Abgleich die Daten aus dem Repository wieder dazu.“ | alle | g: f7, f2b/f2c; h8 (Repository-Einträge kommen zurück); h12 (A direkt nach dem Ersetzen mit lx/p1, nach dem Abgleich ohne) | wahr; die Einschränkungen folgen in den Sätzen 2–7 | belegt |
| 2 | „Löschungen, die dieses Gerät schon kennt …, löschen das Eingespielte nicht noch einmal; das gilt auch für deine anderen Geräte, wenn …“ | AL (g: Fall 7, zwei_neue_geraete), **HI (h5, neu)**, **BL von anderem Gerät gekannt (h6, neu)**; SP/PR: nicht (dafür Satz 7) | h5: Verlauf aus der Sicherung bleibt auf A und B, Feld `aufgehoben` = `history_cleared_at`. h6: Bestenliste `a-vorher`, `b-vorher` bleibt auf A und B | wahr für AL, HI, BL; für SP/PR durch Satz 7 eingegrenzt (g: S1b, S2b) | belegt |
| 3 | „Solange ein Gerät noch eine ältere Version hat, kann … zeitweise wieder fehlen, und ein Gerät mit einer älteren Version, das die Löschung kennt, löscht es bei sich weiterhin …“ | AL (g: f4b, f4c mit v0.63.1), **HI (h13, neu, B mit v0.63.1)** | h13: A (0.63.2) behält den Verlauf in 3 Runden, B (alt, kennt die Löschung) bleibt leer | wahr | belegt |
| 4 | „Was ein anderes Gerät ohne Verbindung gelernt hat, bleibt in der Regel erhalten, wenn …“ | AL (g: f4 günstig, f5, f6, f4f), **AL+HI+BL zusammen (h11, neu)** | h11: Cs Offline-Karte, -Verlauf, -Bestenliste, -Spielstand und -Projekt bleiben auf A und C, ebenso das Eingespielte | wahr | belegt |
| 5 | „Was nach dem Erstellen der Sicherung schon abgeglichen war, bleibt gelöscht.“ | AL (g: f7 wahr; **h7, h8, h9 falsch**), **HI (h7h falsch)**, SP (h10 wahr) | siehe **M1** | **falsch** in h7, h7h, h8, h9 | belegt |
| 6 | „Löschungen eines anderen Geräts, die dieses Gerät noch nicht kennt, gelten weiter – außer sie kamen vor der letzten Löschung derselben Art, die dieses Gerät kennt (beide AL, beide HI oder beide BL); solche werden aufgehoben.“ | AL: g f2b, f2c, f2g vor/nach/ohne C, S4, S5. HI gemischt: g f2e, f2f. **HI gleiche Art: h1 (aufgehoben), h2 (später → gilt)**. BL: g S3; **h3 (später → gilt), h4 (A kennt nur AL → gilt)**. SP/PR: nicht genannt, Satz 7 | h1: Verlauf aus der Sicherung bleibt auf A und B, Feld `history_cleared_at`. h2: Verlauf weg, Karten bleiben. h3/h4: Bestenliste leer, alles andere bleibt | wahr in allen Fällen | belegt |
| 7 | „Bei Spielständen und Projekten ist das anders: … bleiben gelöscht, wenn die Löschung von einem anderen Gerät kam oder schon abgeglichen war.“ | SP, PR: g S1, S2, S1b, S2b, neuer Fall (B offline, gleicht nach dem Ersetzen ab); **h12 (drittes Gerät C offline, spielt in lx weiter)**; **h10 (Spielstand nach der Sicherung angelegt, Löschung abgeglichen)** | h12: lx und p1 auf A, B, C gelöscht; A direkt nach dem Ersetzen mit lx/p1, nach dem Abgleich ohne. h10: lz bleibt gelöscht | wahr. Gegenstück „eigene Löschung, nicht abgeglichen → kommt zurück“ in g S1 (ly) und S2 (p2) | belegt; Code: `purge_deleted_runs` (`fisi_core.py:444`), `projects` (`fisi_projekt.py:161`), `replace_lifts` nur `MARKERS` (`fisi_sync.py:654`) |
| 8 | „Bewahre die Sicherungsdatei deshalb auf.“ | – | Ratschlag | richtig | – |

Zu Satz 6 aus dem Code:
- Die Aufhebung gilt je Marke nur für den Bereich (Marke der Sicherung, letzte Marke dieses Geräts vor dem Ersetzen] (`replace_lifts`, `_lifted`, `fisi_sync.py:633-670`).
- „Spielstand zurücksetzen“ setzt keine Marke. PC (`app_gui.py:6310`) und Handy (`mobile/src/main.py:4369`) rufen `Game.reset` → `delete_run` auf. `db.reset_game` (setzt `spiel_reset_at`) nutzt keine Oberfläche, nur ein Test. Deshalb ist es richtig, dass „Spielstand“ in der Klammer von Satz 6 fehlt (Code).

## Befunde

### S1 – Am Linux-PC ist der Warntext abgeschnitten, ohne Rolle; am Handy vermutlich auch

**Ablauf (belegt):**
- Echtes Hauptfenster `FISIApp` in Xvfb mit openbox, kleinstes Fenster 1120×720.
- Dialog genau wie in `_replace_backup`: `messagebox.askyesno(REPLACE_TITLE, replace_question(backup), icon="warning")` (`app_gui.py:6391`).
- Skript `skripte/dialog_pc.py` mit `matrix_pc.sh`; Messwerte in `bilder/*.json`, Übersicht in `logs/dialog_pc_matrix_kurz.txt`.

**Messung:** Der Dialog braucht 1280 px Höhe (`dd0c2a0`: 1126 px). Tk begrenzt ihn auf die Bildschirmhöhe und staucht dafür das Textfeld.

| Bildschirm | Schrift | sichtbar bis | Knöpfe |
|---|---|---|---|
| 1366×768 | Normal / Sehr groß (gleich) | Satz 4 „… bleibt in der Regel“; Sätze 5–8 fehlen | Unterkante bei 780 px, also 12 px unter dem Bildschirmrand; anklickbar |
| 1280×720 | Normal / Sehr groß | wie oben | Unterkante bei 732 px, also 12 px darunter |
| 1920×1080 | Normal / Sehr groß | Satz 6 bis „… oder beide „Bestenliste löschen“);“; „solche werden aufgehoben“, Satz 7 und Satz 8 fehlen | Unterkante bei 1092 px |
| 1920×1080, Text `dd0c2a0` | Normal | bis „… wird dagegen“; „Bewahre …“ fehlte schon | wie oben |

Bilder:
- `bilder/pc_1366x768_normal_d54397f_openbox.png`
- `bilder/pc_1920x1080_normal_d54397f_openbox.png`
- `bilder/pc_1366x768_normal.png` (ohne Fenstermanager: gleich abgeschnitten, Knöpfe ganz sichtbar)
- `bilder/ausschnitt_dd0c2a0_1080.png` (Vorfassung)

**Weitere Beobachtungen:**
- „Sehr groß“ ändert nichts: Der Tk-Dialog nutzt `TkCaptionFont` mit `wraplength 3i`, die Skalierung von customtkinter wirkt dort nicht (belegt, JSON).
- Die Knöpfe heißen im Container „Yes/No“, weil die Sprache dort C ist. Ob sie mit deutschem System „Ja/Nein“ heißen, habe ich nicht geprüft.

**Handy (vermutet, Rechnung `skripte/handy_rechnung.py`, `logs/handy_rechnung.txt`):**
- Aufbau laut Code (`mobile/src/main.py:5411`): `confirm` zeigt `ft.AlertDialog(content=ft.Text(message, size=14))`, ohne `scrollable` und ohne Rolle.
- In Flutter bleiben dabei Titel und Knöpfe sichtbar, der Text wird unten abgeschnitten.
- Rechnung (Inter statt Roboto, 20 dp Zeilenhöhe): Bei 393×852 dp sind etwa 56 % des Texts sichtbar (`dd0c2a0`: 65 %), bei 360×800 etwa 47 %, mit Systemschrift ×1,3 etwa 25–39 %.
- Die Schriftgröße der App ist bei 14 fest, weil `ft.Text` statt `ui.text` verwendet wird; die Systemschrift wirkt.
- Ein echtes Bild vom Handy konnte ich hier nicht machen (kein Flet-Client).

**Windows/macOS:** nicht geprüft. Unter Windows ist es ein natives Meldungsfenster, das bei langem Text breiter wird. Dort passt der Text vermutlich.

**Warum schwer:**
- Der Wortlaut ist abgenommen, aber genau die neuen Sätze 6 und 7 und der Rat „Bewahre die Sicherungsdatei deshalb auf“ sieht der Nutzer am Linux-PC nicht.
- Bei 1366×768 sieht er alles ab Satz 5 nicht. Am Handy (Rechnung) sieht er vermutlich ebenfalls nur etwa die erste Hälfte.
- Er kann trotzdem „Ja“ drücken.
- Das gab es schon vorher, aber die Weisung fragt ausdrücklich danach. Nach Abschnitt 5.3 entscheidet Chat, ob gekürzt oder anders angezeigt wird.

### M1 – Satz 5 ist in vier Abläufen falsch (unveränderter Satz)

Rohdaten: `logs/gp3.jsonl`, Fälle h7, h7h, h8, h9. Tests h7–h9 sind FAIL in `logs/gp3_lauf.txt`. Alle Geräte auf 0.63.2, keine Uhrverstellung.

| Fall | Ablauf | Satz 5 sagt | Ergebnis |
|---|---|---|---|
| h7 (AL) | A erstellt die Sicherung. B lernt `b-zwischen` und gleicht ab, A gleicht ab. B ist danach **ohne Verbindung**. A „Alle Lerndaten löschen“, Abgleich, „Alles ersetzen“, Abgleich. B gleicht erst danach ab | `b-zwischen` bleibt gelöscht | A direkt vor Bs Abgleich `{a-vorher}`; danach haben **A und B `b-zwischen`** (Karten, Verlauf, Bestenliste) |
| h7h (HI) | wie h7 mit „Historie löschen“ | Verlauf `b-zwischen` bleibt gelöscht | Verlauf `b-zwischen` wieder auf A und B |
| h9 (AL, drittes Gerät) | wie h7, aber B gleicht nach der Löschung ab (B leer). C hatte `b-zwischen` vor der Löschung abgeglichen und war dann ohne Verbindung | bleibt gelöscht | Vor Cs Abgleich haben A und B `{a-vorher}`, danach haben **A, B, C `b-zwischen`** |
| h8 (AL, eigene Löschung nicht abgeglichen) | B lernt `b-zwischen` und gleicht ab, A hat es. A löscht **ohne Abgleich** und ersetzt | bleibt gelöscht | `b-zwischen` kommt aus dem Repository zurück (wie in v0.63.1; Satz 1 beschreibt das) |

- **Grund (Code):** Die Aufhebung setzt die bekannte Marke auf die Marke der Sicherung zurück (`_lifted`, `fisi_sync.py:633`). Danach liegt `b-zwischen` (nach der Sicherung, vor der Löschung) unter keiner Marke mehr. Ein Gerät, das es noch hat, lädt es wieder hoch.
- **f7** (Bauer) ist nur der Fall, in dem alle Geräte die Löschung schon übernommen haben, bevor ersetzt wird. Nur dort stimmt Satz 5.
- **Richtung:** Es kommt mehr zurück, als der Text sagt; verloren geht nichts.
- **Wie oft das vorkommt:** h7 ist bei Nico realistisch: Das Handy war beim Löschen am PC offline und kommt nach dem Ersetzen wieder online.
- **Betroffen:** Satz 5. Die Weisung hat ihn nicht geändert; er ist aber Teil des Absatzes, der Satz für Satz zu prüfen war.
- **h8:** wörtlich falsch. Der Satz lässt sich aber auch so lesen, dass die Löschung abgeglichen war; ich führe h8 deshalb nur als Lesart-Hinweis.
- Nicht umformuliert, nur gemeldet.

### L1 – „beide ‚Historie löschen‘“ ist in den Bauer-Tests nur nebenbei abgedeckt

- **Eigener Kontrollfehler `KY_hist`** (`replace_lifts` übergeht `history_cleared_at`, Kopie `mut/KY_hist`): In 47 Tests (fg81, b_g_08, BG08) wird **nur** `f2g nach` rot (`logs/kf_KY_hist.txt`).
- Meine Abläufe h1 (Satz 6, beide HI) und h5 (Satz 2, HI bekannt) werden damit beide rot (`logs/gp3_h1_h5_gegen_KY_hist.txt`).
- Die Teilaussage „beide ‚Historie löschen‘ … werden aufgehoben“ hat also keinen eigenen Test, sie wird nur indirekt über f2g „nach“ geprüft.
- Vorschlag: h1 als Test aufnehmen. Das ist eine Testergänzung, keine Textänderung.

### L2 – Teilläufe der Kontrollfehler ohne v0.63.1

- In meinen Kontrollfehler-Läufen (Kopien ohne `.git`) wurden 3 bzw. 12 Mischbetrieb-Tests übersprungen („Code aus v0.63.1 nicht verfügbar“).
- Für die Aussagen über die Kontrollfehler spielt das keine Rolle.
- Im Hauptlauf auf `d54397f` mit v0.63.1 lief alles: 57 Tests, davon 43 Bauer-Tests der Klasse BG08Ersetzen, alle grün; rot waren nur meine 4 Satz-5-Abläufe.

## Prüfpunkte (a)–(c)

**(a) Wortlaut** (belegt, `skripte/wortlaut_gp3.py`, `logs/wortlaut_ast.txt`):
- Das Skript liest die Zeile „Ist der Abgleich eingerichtet …“ unter „## 3.“ selbst aus der Weisungsdatei.
- Weisung und Code (`replace_question`, d54397f): je 1486 Byte, sha256 `89ff3412…b56b`. **byte-gleich: True**. Die sha256 stimmt mit dem Bauer-Bericht überein.
- Zeichen: 4× „, 4× “, 1× –, 1× ß in beiden.
- 2 Absätze, 8 Sätze.
- Sätze 1–5 und 8 sind wörtlich in `dd0c2a0` enthalten. Satz 6 ist neu, Satz 7 ist neu, der alte Satz 6 ist weg.
- Erster Absatz gleich `dd0c2a0`: True. `PREVIEW_HINT` gleich: True (`d126edce…`).
- `git diff dd0c2a0 d54397f`: nur `fisi_sicherung.py` (nur in `replace_question`), `pruefung/abgleich_geraet_voll.py`, `test_abgleich_0632.py`, `test_sicherung_fehler.py`.

**(b) Tests nicht lockerer** (belegt, Diff gelesen):
- `test_abgleich_0632.py`: +362 Zeilen. Entfernt wurde nur eine Docstring-Zeile (Kopf, „31 und 35“ → „31, 35 und 37“).
- `test_sicherung_fehler.py`: Der Bestandstest bleibt `assertEqual` für beide Absätze. Alle bisherigen `assertNotIn` bleiben.
- Neu in `test_sicherung_fehler.py`: 5 `assertNotIn` für den alten Satz 6, `count(". ") == 7` und `count("beide „") == 3`.
- Entfernt wurde dort nur der alte Sollwortlaut von Satz 6 (wird durch den neuen ersetzt).

Kontrollfehler selbst nachgestellt (5, davon 4 wie beim Bauer und 1 eigener):

| KF | Änderung (Kopie) | Erwartet laut Bauer | Ergebnis (eigener Lauf) |
|---|---|---|---|
| KT7 | Satz 7 ohne Vorsatz | genau 1 von 21 rot (Bestandstest) | genau 1 von 21 rot: `KernTest.test_b_g_08_warntext_nennt_eigene_loeschungen`. Gegenprobe unverändert: 21 OK. Beides unter xvfb, ohne xvfb ist zusätzlich `PCTest.test_b_g_05` rot (Anzeige fehlt) – bitte immer mit xvfb |
| KY3 | `replace_lifts` liefert `{}` | f2b, f2g vor, f2g nach, S3, S5 rot | genau diese 5, dazu f4b/f4f günstig, f5, f6, f7 (außerhalb der 16 Tests des Bauers); rot bleibt auch f2g nach |
| KS1 | `purge_deleted_runs` ohne Wirkung | S1, S1b, neuer Fall Spielstand | genau diese 3, keine Projekt-Tests |
| KP2 | `projects` beachtet „geloescht“ nicht | S2, S2b, neuer Fall Projekt | genau diese 3, keine Spielstand-Tests |
| KY_hist (eigener) | keine Aufhebung für `history_cleared_at` | – | nur f2g nach (siehe L1) |

Die Angaben des Bauers stimmen in den Stichproben.

**(c) AST Kommentar-Commit** (belegt): `ast.dump` von `fisi_sicherung.py` in `4cdfd39` und `d54397f` ist gleich (True). Von 53 Kommentaren ist genau einer geändert (Zeile 589; nur ASCII). Sonst unterscheidet sich keine Zeile. Fingerabdrücke habe ich nicht selbst gemessen; die Werte im Bauer-Bericht sind für mich berichtet.

## Nicht geprüft

- Windows- und macOS-Dialog; ein echtes Bild vom Handy (dort nur Rechnung, siehe S1).
- Uhr-Fälle (B.5), Zufallsabläufe.
- Zweites „Alles ersetzen“ mit früherer Aufhebung.
- Mischbetrieb für Spielstände/Projekte und für BL.
- Fingerabdrücke (berichtet).

## Belege

`bau_0.63.2/gegenpruefung/gp3_fg81_m37_belege/`:

**skripte/**
- `gp3_ablaeufe.py`: h1–h13; erbt BG08Ersetzen, deshalb liefen die 43 Bauer-Tests mit.
- `wortlaut_gp3.py`
- `dialog_pc.py`, `matrix_pc.sh`, `mit_openbox.sh`
- `handy_rechnung.py`

**logs/**
- `gp3_lauf.txt`, `gp3.jsonl`
- `wortlaut_ast.txt`
- `kf_KT7.txt`, `kf_KT7_gegenprobe_unveraendert.txt`, `kf_KY3.txt`, `kf_KS1.txt`, `kf_KP2.txt`, `kf_KY_hist.txt`
- `gp3_h1_h5_gegen_KY_hist.txt`
- `dialog_pc_matrix*.txt`
- `handy_rechnung.txt`

**bilder/**
- PNG und JSON je Bildschirm, Schrift und Textstand.

Arbeitskopien unter `scratchpad/gp3_fg81/` (`code`, `base`, `alt`, `mut/*`) habe ich stehen gelassen.
