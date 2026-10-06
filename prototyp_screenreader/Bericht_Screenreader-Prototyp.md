# Bericht: Screenreader-Prototyp (Plan 0.59, Abschnitt 8a, Lesart A)

Stand: 06.10.2026. Zweig `proto-screenreader` (von `main` cb63c96). Kein Pull-Request, kein Tag, kein Release. Am Hauptprogramm, an Daten, Spielwerten, Abgleich, Installer und Update-Ablauf wurde nichts geändert; alle neuen Dateien liegen in `prototyp_screenreader/` und in einem eigenen Bau-Ablauf `.github/workflows/prototyp-screenreader.yml`, der nur bei Pushes auf diesen Zweig läuft.

## 1. Kurzfassung

| Frage | Antwort |
|---|---|
| Kann NVDA das heutige PC-Programm (CustomTkinter) lesen? | **Nein, praktisch nicht.** Gemessen unter Linux: Das Fenster taucht im Zugänglichkeitsbaum gar nicht auf, eine GTK-Gegenprobe im selben Lauf schon. Laut Quelltext bestehen CustomTkinter-Knöpfe aus einer Zeichenfläche plus Beschriftung ohne Rolle. Unter Windows wird NVDA voraussichtlich nur den Fenstertitel nennen (nicht gemessen). |
| Kann Flet-Desktop das? | **Ja, weitgehend.** Gemessen unter Linux: Knöpfe, Schalter, Optionsfelder, Überschriften und die Klappköpfe („Farben, eingeklappt“) kommen mit Name und Rolle an, Tab, Enter und Leertaste funktionieren, eingeklappte Inhalte sind nicht per Tab erreichbar. Unter Windows (UI Automation) ist das laut Flutter-Quelltext ebenso angelegt; ein echter NVDA-Lauf fehlt noch. |
| Empfehlung | Zuerst den **echten NVDA-Test** mit dem Prototyp machen lassen (Anleitung liegt bei). Den Weg über CustomTkinter **nicht** weiterverfolgen. Bei gutem Testergebnis einen **zugänglichen Lernmodus auf Flet-Desktop** (aus dem Handy-Code) als eigenes Roadmap-Thema prüfen. Die Entscheidung trifft Nico. |

## 2. Was ist belegt, was nicht

| Art | Inhalt |
|---|---|
| **Gemessen** (Cloud, Linux, virtuelle Anzeige, AT-SPI = Zugänglichkeitsschnittstelle unter Linux) | Baum von CustomTkinter (leer) gegen GTK (sichtbar); Tab-Reihenfolge in CustomTkinter; Baum und Tastaturablauf des Flet-Prototyps (Optionen und Karteikarte); Baum der unveränderten Handy-App als Desktop-Programm. Alle Ergebnisse und Skripte: `prototyp_screenreader/messung/`. |
| **Nur im Quelltext geprüft** | Flutter unter Windows meldet „erweitert/reduziert“ als Zustand (accessibility_bridge.cc), schickt beim Umschalten aber **kein eigenes Ereignis** (accessibility_bridge_windows.cc: EXPANDED/COLLAPSED werden übergangen). Ansagen über `SemanticsService` gehen unter Windows als UIA-„Alert“ raus (flutter_windows_view.cc, AnnounceAlert). Ob Flutter „Live-Regionen“ unter Windows weitergibt, ist im Quelltext nicht erkennbar. Tk 9.1 (erschienen 30.09.2026) hat erstmals eine Screenreader-Schnittstelle, die für reine Zeichenflächen ausdrücklich nicht gilt. |
| **Nicht geprüft** | Kein echter NVDA-Lauf (geht in der Cloud nicht). Kein Windows-Lauf des Prototyps durch Claude Code; der Windows-Bau läuft über GitHub Actions. Linux-Messwerte sind ein starker Hinweis, aber kein Beweis für Windows. |

## 3. S1: CustomTkinter/Tk

**Messung 1 (Baum):** CustomTkinter-Fenster und GTK-Fenster gleichzeitig offen. Ergebnis (`messung/ergebnisse/tk_gegen_gtk_baum.txt`): Nur das GTK-Fenster mit „GTK-Knopf, push button“ erscheint, das CustomTkinter-Fenster fehlt vollständig.

**Messung 2 (Tastatur):** Tab-Kette mit Label, Knopf, Schalter, Eingabefeld, Segmentknopf und einem normalen Tk-Knopf. Ergebnis (`messung/ergebnisse/tk_tab_reihenfolge.txt`): Nur das Eingabefeld und der normale Tk-Knopf sind Tab-Ziele. CustomTkinter-Knöpfe haben weder Enter noch Leertaste.

**Einordnung:**
- Das Hauptprogramm hat eigene Tastaturbedienung nachgerüstet (`fisi_widgets.py`, `test_zugang.py`). Sehende Tastaturnutzer kommen also zurecht; ein Screenreader bekommt davon aber keine Namen und Rollen.
- Unter Windows ist jedes Tk-Fenster ein echtes Windows-Fenster. NVDA wird deshalb den Fenstertitel nennen, Texte auf den Zeichenflächen aber nicht (Erwartung, nicht gemessen). Der Vergleichsschritt 5 in der Testanleitung prüft das.
- **Tk 9.1** bringt seit dem 30.09.2026 einen Befehl `tk accessible`, mit dem man Rolle und Namen setzen kann. Laut Handbuch gilt das nicht für Zeichenflächen („a purely visual widget“) und Rahmen. Das Programm baut mit Python 3.12, das unter Windows Tk 8.6 mitbringt. Ob CustomTkinter 6.0.0 mit Tk 9 läuft, ist offen.

**Ergebnis S1:** Kein brauchbarer Weg. Deshalb gibt es keinen Vergleichsfall im bestehenden PC-Programm (Plan: „Wenn S1 etwas liefert“).

## 4. S2: Flet-Desktop

**Gegenprobe Handy-App:** Die unveränderte Handy-App (`mobile/src/main.py`) läuft als Desktop-Programm. Der Rundgang wird mit allen Texten gelesen, die Knöpfe „Weiter“ und „Überspringen“ sind Tab-Ziele. Sie heißen aber nur „panel“ statt „Schaltfläche“, weil die Handy-Knöpfe (`ui.GradientButton`) Container mit Klick sind (`messung/ergebnisse/handy_app_als_desktop_baum.txt`).

**Prototyp:** siehe Abschnitt 6 und `messung/ergebnisse/flet_*`. Gemessen:
- Tab-Reihenfolge im Startzustand: Optionen, Karteikarte, Testschalter, Nach Updates suchen, Beim Start automatisch …, Rundgang und Hilfe (eingeklappt), Schriftgröße (eingeklappt), Farben (eingeklappt), Tagesziel (eingeklappt), Kopieren (Problem melden), Leistungsmessung (eingeklappt), dann von vorn.
- „Farben“ mit Enter: Name wechselt zu „Farben, ausgeklappt“, Tab führt in den Bereich (Darstellung, Vorlagen).
- „Vorlagen“ mit Leertaste: zwölf Kacheln als Schaltflächen („Grundfarbe Cyan/Pink“ …). Wieder eingeklappt: Die Kacheln werden übersprungen.
- Überschriften „Optionen“, „Updates“, „Problem melden“ haben die Rolle Überschrift.
- Karteikarte: Nach „Antwort zeigen“ steht der Fokus auf „Gewusst“, nach der Bewertung wieder auf „Antwort zeigen“.

**Grenzen unter Linux:** Den Zustand „erweitert/reduziert“ meldet Flutter unter Linux gar nicht (deshalb steht der Zustand zusätzlich im Namen). Textfelder fehlten im Linux-Baum. Beides ist unter Windows anders angelegt und wird im NVDA-Test geprüft.

## 5. S3: Testfall

Wie vorgeschlagen: **Optionen** in der Form von 0.59 (Updates oben und offen, Rundgang und Hilfe, Schriftgröße, Farben mit Unterbereich „Vorlagen“, Tagesziel eingeklappt, Problem melden offen, Leistungsmessung eingeklappt) und eine **Karteikarte**. Grundlage ist der heutige Stand (0.58.1), weil der Umbau 0.59 im eigenen Thread entsteht. Texte und Farben kommen aus denselben Modulen wie am Handy (`fisi_hilfe`, `fisi_diagnose`, `fisi_leistung`, `fisi_theme`, `inhalte/karteikarten.json`).

## 6. Der Prototyp

- Datei: `prototyp_screenreader/optionen_flet.py`. Start im Repo: `python prototyp_screenreader/optionen_flet.py` (Flet 1.0.1 wie am Handy).
- Windows-Programm für den Tester: ZIP aus dem Ablauf „Screenreader-Prototyp bauen“ (GitHub → Actions → Lauf → Artifacts). Die Testanleitung liegt im ZIP.
- Speichert nichts: Datenbank und `einstellungen.json` zeigen auf einen leeren Temp-Ordner.
- Klappköpfe nach Plan 0.59, Abschnitt 3: ganze Kopfzeile ist eine Schaltfläche, Pfeil ▸/▾ links in der Akzentfarbe, rechts „aufklappen/einklappen“, Hand-Mauszeiger, Hervorhebung bei Maus und Tastaturfokus, Name „Farben, eingeklappt“, Zustand erweitert/reduziert, eingeklappter Inhalt nicht im Baum.
- **Testschalter „zusätzliche Ansagen“:** Weil Flutter unter Windows das Umschalten nicht als Ereignis meldet, sagt der Prototyp den neuen Zustand zusätzlich an. Der Tester prüft mit und ohne, ob NVDA dann doppelt oder gar nicht spricht.
- Echte Schaltflächen statt Container (Rolle „Schaltfläche“), Optionsfelder für Schriftgröße und Darstellung, Live-Region plus Ansage für Meldungen.

## 7. Nebenbefund für 0.59 (Handy)

Die Handy-Knöpfe `ui.GradientButton` und die Kacheln melden sich unter Linux nur als „panel“. Für TalkBack ist das wahrscheinlich ähnlich („Doppeltippen zum Aktivieren“ ohne „Schaltfläche“), das ist aber nur abgeleitet. Die Klappköpfe der Handy-App (`ui.FoldCard`) haben schon heute `button=True` und ein Label mit Zustand; die Lösung im Prototyp lässt sich dorthin übertragen. Ich habe am Handy-Code nichts geändert; ob das in 0.59 mitgeht, entscheidet Nico im Thread „Version 0.59“.

## 8. Aufwand und Risiko (grobe Schätzung, nicht gemessen)

| Weg | Was | Aufwand (Schätzung) | Risiko |
|---|---|---|---|
| A | CustomTkinter behalten, Zugänglichkeit nachrüsten | sehr hoch, unklar | **sehr hoch:** eigenes Tk 9.1 statt Python-Tk 8.6, CustomTkinter-Bausteine sind Zeichenflächen ohne Zugänglichkeit, Tk 9.1 ist eine Woche alt. Nicht empfohlen. |
| B | Ganze PC-Oberfläche auf Flet-Desktop umstellen (Handy-Code als Grundlage) | sehr hoch: mehrere Versionen (PC-Oberfläche hat rund 7.700 Zeilen plus Spiel) | **hoch:** neuer Windows-Bau (flet build statt PyInstaller), Installer, Update-Ablauf, Linux-Pakete, Spielkarte (Zeichenfläche ohne Vorlesetext), Bestandsschutz der Darstellung. |
| C | Zusätzlicher **zugänglicher Lernmodus** auf Flet-Desktop (Karteikarten, Prüfungstrainer, Optionen) aus dem Handy-Code, PC-Programm bleibt | mittel: etwa ein bis zwei Versionen | **mittel:** zweite PC-Oberfläche pflegen, Verteilung als zweites Programm oder Startoption klären, gemeinsame Daten über denselben Datenordner. |
| – | Nur Handy-Bausteine mit echten Rollen versehen (Abschnitt 7) | klein | gering; hilft TalkBack und einem späteren Weg C. |

## 9. Empfehlung

1. **Jetzt:** NVDA-Test mit dem Prototyp durch eine Person, die NVDA kennt (Anleitung `NVDA-Testanleitung.md`, Windows-ZIP aus GitHub Actions).
2. **Weg A nicht weiterverfolgen.**
3. **Bei gutem Testergebnis:** Weg C als eigenes Thema in die Roadmap aufnehmen (nicht in 0.59; frühestens nach 0.62 Gesamttest, oder zusammen mit „Karten-Zugänglichkeit“ in 0.60, wenn Nico das möchte).
4. **Unabhängig davon** (klein, mit Nicos OK): Handy-Knöpfe mit echter Rolle (Abschnitt 7).

Die Entscheidung trifft Nico.

## 10. Quellen

- Tk 9.1, Befehl `tk accessible`: https://www.tcl-lang.org/man/tcl9.1/TkCmd/accessible.html
- Tk 9.1 erschienen (30.09.2026): https://linuxiac.com/?p=220267
- Flutter-Zugänglichkeit unter Windows: https://flutter.googlesource.com/mirrors/flutter/+show/3a5c2cefdfc73bd2e4e47d8ef80489c060436b37/docs/platforms/desktop/windows/Accessibility-on-Windows.md
- Flutter-Quelltext: `engine/src/flutter/shell/platform/common/accessibility_bridge.cc`, `.../windows/accessibility_bridge_windows.cc`, `.../windows/flutter_windows_view.cc`, `.../linux/fl_accessible_node.cc` (github.com/flutter/flutter, Stand master 06.10.2026)
- Flet und Screenreader: https://flet.dev/docs/cookbook/accessibility/
