# FG-114 – Antrag: Schalter in den Handy-Optionen an der ersten Zeile (Vorabbau, NICHT gemergt)

Von Bauer FG-114, 14.10.2026. Bezug: Nicos Antwort „Foto Nachtrag: Ja sollen sie.“ (`plan_0.63.2/freigabe/Antwort_Nico_Handy_Schalter.md`, 13:33 UTC) auf Weisung 44, Abschnitt 6 Nr. 3.
Basis `a82fd34` (origin/version-0632). Zweig `version-0632-fg114`, ein Commit **`5c6087d`** (gepusht, kein Force).
Diff: `FG-114_handy_schalter.diff` (sha256 `3e95d3137ef69d624e4fa11905e1b0e61ac7808c39ad3f4bc6f23007cfcf8389`, 110 Zeilen; gleich `git diff a82fd34 5c6087d`).
Regel A: Vorabbau erlaubt, **Merge erst nach Chats Lesung des Diffs**. Kein Merge, kein PR, kein Tag.
Belege: `bau_0.63.2/fg114/` (`ergebnis.md`, `BEFEHLE.md`, `logs/`, `messung/`, `fotos/`, `ci/`, `werkzeug/`).
Stufen: **belegt** / berichtet / vermutet / nicht geprüft.

## 1. Bestand: alle Schalter am Handy (belegt)
Alle Schalter der Handy-App entstehen in **einem** Baustein: `mobile/src/main.py` `SettingsScreen._switch` (Zeile 4368 auf a82fd34). `ft.Switch` kommt sonst nirgends in `main.py`, `ui.py`, `spiel.py` vor (AST-Suche, jetzt als Wache im Test).

| Aufruf (main.py @ a82fd34) | Ort | Text |
|---|---|---|
| 3961 | Optionen › Updates | „Beim Start automatisch nach Updates suchen“ |
| 3980 | Optionen › Abgleich PC und Handy | „Automatisch abgleichen (beim Start, nach dem Lernen und beim Verlassen der App)“ |
| 4028 | Optionen › Diagnose und Werkzeuge | „Messung aufzeichnen“ (`fle.SWITCH`) |
| 4088/4091/4094 | Optionen › Tagesziel | „Tagesziel anzeigen“, „Lernserie anzeigen“, „An das Tagesziel erinnern“ |
| 4115/4120 | Optionen › Lerninhalte › Rahmenplan | „Abschnitt B anzeigen (Anwendungsentwicklung)“, „Abschnitt D anzeigen (Daten- und Prozessanalyse)“, „Abschnitt E anzeigen (Digitale Vernetzung)“, „Übungsauswahl nach Rahmenplan gewichten“ |
| 4946 (TourDialog._setup_controls) | Rundgang, letzte Seite „Jetzt einrichten“ (Dialog) | Abschnitt B/D/E wie oben |

**Messung** (Handy-Behelf: Flet-App im Browser, 384 px breit, wie die bisherigen Handy-Fotos; Werkzeug `fg114/werkzeug/`, Server nach `e1_server.py`): Jeder Schaltertext bekommt nur für die Messung einen eigenen Semantik-Knoten (SONDE), dessen Höhe die Zeilenzahl ergibt. Normal/Groß/Sehr groß auf a82fd34; Extra groß/Maximal auf dem N9-Zweig (`origin/version-0632-n9`, dort gibt es die Stufen; `_switch` ist dort gleich). Tabelle: `fg114/messung/bestand_tabelle.md`.

Zeilen je Schaltertext (Optionen; Rundgang-Dialog gleich wie die Optionen):

| Text | Normal | Groß | Sehr groß | Extra groß | Maximal |
|---|---|---|---|---|---|
| Beim Start automatisch nach Updates suchen | 2 | 2 | 2 | 2 | 3 |
| Automatisch abgleichen (…) | 3 | 3 | 3 | 4 | 5 |
| Messung aufzeichnen | 1 | 1 | 1 | 1 | 2 |
| Tagesziel anzeigen | 1 | 1 | 1 | 1 | 1 |
| Lernserie anzeigen | 1 | 1 | 1 | 1 | 1 |
| An das Tagesziel erinnern | 1 | 1 | 1 | 1 | 2 |
| Abschnitt B anzeigen (…) | 2 | 2 | 2 | 3 | 3 |
| Abschnitt D anzeigen (…) | 2 | 2 | 2 | 3 | 3 |
| Abschnitt E anzeigen (…) | 2 | 2 | 2 | 2 | 2 |
| Übungsauswahl nach Rahmenplan gewichten | 2 | 2 | 2 | 2 | 3 |

**Ergebnis: Ja, am Handy brechen Schalter tatsächlich um, schon bei Normal** (6 von 10 in den Optionen, alle 3 im Rundgang). Sichtbar wird „mittig“ aber erst, wenn der Text **höher als der Schalter (40 px)** ist: bei Normal nur „Automatisch abgleichen“ (57 px); zweizeilige Texte sind bei Normal 38 px hoch und stehen schon bündig. Ab Groß ist jeder mehrzeilige Text höher als der Schalter. Vorher stand jeder Schalter mittig (alle 65 Messpunkte „mittig“).

## 2. Lösung (kleinste, die einzeilige Schalter unverändert lässt)
Die „eine Zeile“ aus Weisung 44 (`vertical_alignment=START`) reicht **nicht**: dann rutscht der Text einzeiliger Schalter nach oben (belegt: Kontrollfehler K1, Pixelvergleich rot). Gebaut ist darum:

```python
return ft.Row([
    ft.Container(content=ft.Semantics(label=caption, content=ft.Switch(...)), alignment=ft.Alignment.TOP_LEFT),
    ft.Container(content=ui.text(caption, size=13, color=C["text_dim"]),
                 expand=True, alignment=ft.Alignment.CENTER_LEFT),
], spacing=8, intrinsic_height=True, vertical_alignment=ft.CrossAxisAlignment.STRETCH)
```
Die Zeile ist so hoch wie das Höhere von Schalter und Text; der Schalter steht oben, der Text in seiner Spalte mittig. Einzeilig (Text niedriger als der Schalter) ist das genau das alte Bild; mehrzeilig beginnen Schalter und Text oben – wie `ui.check_row` (START). Geprüfte, verworfene Wege: `BASELINE` (Flet-Web zeichnet dann gar nichts, belegt im Probeaufbau), Abstand oben nach geschätzter Zeilenhöhe (am Handy schriftabhängig; im Probeaufbau 1–2,5 px daneben).
Hinweis: Wie bei den Haken steht der Schalter **oben**, nicht mit seiner Mitte auf der Mitte der ersten Zeile (das wäre die PC-Lösung FG-112). Bei Normal liegt die Schalter-Mitte 20 px unter der Textoberkante, die erste Zeile 19 px hoch.

## 3. Stoppgrenze
* `mobile/src/main.py`: **+8/−5** (nur `SettingsScreen._switch`), Grenze ≤ 15 Zeilen geändert.
* `test_handy_sehr_gross_0632.py`: **+66/−0** (Kopf 2 Zeilen + Klasse `SchalterErsteZeileTest`), Grenze ≤ 80.
* Weitere Datei nötig oder Grenze reicht nicht → Stopp und Frage.
* **Geschützte Dateien: nicht betroffen** (`mobile/src/spiel.py` unberührt, keine Workflows, kein `fisi_theme.py`). Neue Testdatei: keine (Test in bestehender Datei, Teil „rest“, keine CI-Änderung).

## 4. Auflage: einzeilige Schalter unverändert (Pixelvergleich, belegt)
70 Fotos (5 Ansichten × Normal/Groß/Sehr groß/Extra groß/Maximal dunkel + Normal/Maximal hell, je vorher/nachher), 384 px, DPR 2. Werkzeug `fg114_pixel.py`: Unterschied nur im Rechteck eines Schalters erlaubt, der sich bewegt hat; jede Zeile eines nicht bewegten Schalters muss 0 Pixel Unterschied haben. Ergebnis `fg114/messung/pixelvergleich.txt`:
* **42 Zeilen nicht bewegter Schalter: alle 0 Pixel** Unterschied.
* 52 bewegte Schalter (nur mehrzeilige, Text höher als Schalter); sonst 0 Pixel in 25 von 35 Paaren.
* 10 Paare mit Unterschied außerhalb, beide Ursachen belegt und ohne Bezug zur Änderung: (a) Diagnose (7×): Uhrzeit „Erstellt: 14:27“ ↔ „14:34“ im Problembericht (Fotos zu verschiedenen Minuten); (b) Rundgang Groß/Sehr groß/Extra groß (3×): der Updates-Schalter **hinter** dem Dialog (zweizeilig, also gewollt bewegt) steht nicht in der Semantik und darum nicht in der Liste der erlaubten Rechtecke (Unterschied genau bei x 37–89).
* Zeilenzahl und Texthöhe aller 65 Messpunkte vorher = nachher (`zeilen_vorher_nachher.txt`).

## 5. Tests und Kontrollfehler (vorab festgelegt, Zeitstempel `2026-10-14T14:03:35Z`)
Festlegung: `fg114/logs/tests_und_kontrollfehler_vorab.md`.
* **Test vor dem Code rot (belegt):** a82fd34 + nur Test → `FAILED (failures=5, errors=1)`; Wache grün (`logs/test_vor_code_a82fd34.log`).
* **Nach dem Code grün:** ganze Datei `test_handy_sehr_gross_0632.py` 23 Tests OK (`logs/test_nach_code.log`).
* Anzeige-Prüfung (`fg114_zeilen.py --pruefen`): vorher **ROT 58**, nachher **GRÜN 0** (alle 65 Messpunkte, 5 Stufen).
* Kontrollfehler (Unit, `logs/kf_k1..k5.log`; Anzeige bei Groß, `logs/kf_anzeige.log`):

| Nr | Fehler | Unit | Anzeige |
|---|---|---|---|
| K1 | nur `START` (Weisung-Zeile) | rot (5 F, 1 E) | Prüfung rot 4; Pixel einzeilig „Tagesziel anzeigen“ 4551 Pixel → **rot** |
| K2 | ohne `intrinsic_height` | rot (5) | – |
| K3 | Schalter `CENTER_LEFT` | rot (5) | Prüfung rot 6 (mehrzeilig mittig); Pixel einzeilig grün (wie erwartet) |
| K4 | Text `TOP_LEFT` | rot (5) | Prüfung rot 4; Pixel einzeilig 4551 → **rot** |
| K5 | zusätzlicher `ft.Switch` in ui.py | Wache rot (1) | – |

**Nachtrag (beim Bau, nicht vorab):** Die vorab genannte Toleranz „Oberkanten ±1 px“ war zu weit: bei Groß ist ein zweizeiliger Text nur 2 px höher als der Schalter, mittig und oben liegen dann 1 px auseinander. Die Prüfung nutzt jetzt ±0,5 px (strenger); vorher bleibt rot, nachher grün.

## 6. Lauf
`build.yml` ganzer Lauf **38578347292** auf `5c6087d`, 1. Versuch: **success**, alle 11 Jobs grün (inkl. beider Macs, Android, Windows, Update-Test). Rote Tests: **keine**; `bekannt_rot_github.txt` ist leer → keine Abweichung. „rest“ 1469 s (unter 1650 s). Volle Job-Logs nicht abgelegt (Download am Proxy gesperrt), Schlusszeilen per GitHub-MCP belegt → Einzeltests „berichtet“.

## 7. Fotos für Nico
`bau_0.63.2/fg114/fotos/` (70 Fotos) und **7 Vergleichsblätter** `fotos/blaetter/blatt_<modus>_<stufe>.png` (links vorher, rechts nachher; je Ansicht Oben/Updates+Tagesziel, Abgleich, Lerninhalte, Diagnose, Rundgang). Alle 7 Blätter geöffnet und angesehen; sie enthalten Ausschnitte aller 70 Fotos.
Beobachtung ohne Bezug zu FG-114 (nicht geändert): bei Extra groß/Maximal trennt Flutter lange Wörter mitten im Wort („Anwendungsentwic|klung“, „ANPASSUNG|EN“).
