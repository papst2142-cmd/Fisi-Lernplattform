# Untersuchung Linux-Einfrieren, Darstellungswechsel und Speicherbedarf

**Stand:** 07.10.2026 · **Zweig:** `untersuchung-linux-speicher` (nur Messskripte und dieser Bericht, kein PR, nichts gemergt, kein Release, kein Tag) · **Ausgangsstand:** Release v0.59.1 (main 8d7cad0), zum Vergleich v0.58.1 (main cb63c96)

**Beleg-Stufen:** **belegt** = selbst gemessen, nachgestellt oder im Code/Paket nachgesehen · **berichtet** = aus Nicos Angaben und Bildern · **vermutet** = Schluss aus Belegen, nicht direkt bewiesen · **nicht geprüft** = konnte ich nicht prüfen

---

## 0. Kurzfassung

1. **Keine Regression von 0.58.1 zu 0.59.1** (belegt). Linux (Xvfb): Darstellungswechsel im Median 3,58 s (0.58.1) gegen 3,60 s (0.59.1). Windows-Runner: 3,67 s gegen 3,93 s (+7 %). Die 10–17 s auf der VM entstehen durch die langsame VM, nicht durch 0.59.1. Mit einer CPU-Grenze von 25 % eines Kerns komme ich im Container auf **15–18 s** je Wechsel und **5,4–6,6 s** für die Optionsseite, also fast genau Nicos VM-Werte.
2. **Der Darstellungswechsel wird mit jeder schon gebauten Seite teurer** (belegt). Zwei Schritte arbeiten an der *alten* Oberfläche, die gleich weggeworfen wird: Das Umfärben (customtkinter färbt jedes alte Element neu ein, ca. 21 %) und der Abbau der alten Oberfläche mit allen vorgeladenen Seiten (ca. 24 %). Mit 1157 Elementen dauert der Wechsel 1,7 s, mit 3791 Elementen 3,6 s. Hochgerechnet auf Nicos 5330 Elemente und die VM-Geschwindigkeit ergeben sich ca. 17 s, genau der gemessene Wert (vermutet, Rechnung in F2).
3. **Die Optionsseite baut alle eingeklappten Bereiche sofort mit** (belegt). Die eingeklappten Bereiche machen ca. 93 % ihrer Bauzeit aus, „Farben“ allein 35 %. Die Seite selbst hat 818 Elemente. Die Zahlen 4758–5330 in Nicos Messdatei sind die Elemente des ganzen Fensters (alte und neue Oberfläche zusammen), nicht die der Optionsseite (belegt am selben Messdatei-Format).
4. **Speicher ist nicht die Ursache** (belegt durch Nicos vmstat und eigene Messung). Spitze 238–262 MB, Bild-Zwischenspeicher 132–138 MB von 192 MB. Mit 1100 MB Grenze läuft alles unverändert.
5. **Hängen: Der Hauptfaden wartet sehr wahrscheinlich auf eine Antwort des X-Servers** (vermutet, gut gestützt). Im normalen Ruhezustand wartet der Hauptfaden des echten Pakets im `futex`, nur der Tcl-Hilfsfaden in `poll` (belegt am echten .deb unter Xvfb und Xwayland). Nico sah beide Fäden in `poll`. Das passt zu einem Hauptfaden, der in Xlib (`XSync` → `_XReply` → `xcb_wait_for_reply` → `poll`) auf XWayland wartet. Diesen Aufrufweg gibt es im Programm, ich habe ihn unter Xwayland als Momentaufnahme gesehen. **Ein dauerhaftes Hängen konnte ich im Container aber nicht nachstellen** (Xvfb und mutter + Xwayland, mit Klicks, auch mit 25 % CPU; ohne RDP).
6. **Sperre: Hilfsprozesse erben sie nicht** (belegt). Nicos Eintrag „Sperre nach 25 s noch belegt“ lässt sich aber **genau nachstellen**: Ist das laufende Programm beim zweiten Klick nur 4 s blockiert (auf der VM normal bei Vorladen und Darstellungswechsel), kommt die Antwort zu spät. Der zweite Start wartet dann 25 s und öffnet ein zweites Fenster (belegt).
7. **Notausgang beim Schließen**: Im Container endet der Prozess in allen Varianten nach 0,3–1,7 s, auch mit echtem Paket, unter Xwayland und mit 25 % CPU (belegt). Was ihn auf der VM hält, ist **nicht geklärt**. Die naheliegende Erklärung ist dieselbe wartende X-Verbindung wie beim Hängen (vermutet).
8. **F8 Windows-Speicherspalte leer**: Das Programm übergibt das Prozess-Handle als 32-Bit-Zahl, Windows antwortet „ungültiges Handle“ (Fehler 6). Das war in 0.58.1 schon so (belegt auf dem Windows-Runner).
9. **Paket:** Python 3.12.14, Tcl/Tk 8.6.12, dazu libX11/libxcb aus Ubuntu 22.04 (belegt aus dem .deb 0.59.1). Ubuntu 26.04 selbst hat Tk 8.6.17.
10. **Empfehlung für 0.59.2** (Abschnitt 3): zuerst **Diagnose** (A: Stapelspur bei Hängen und beim Schließen, Blockier-Ereignis in der Messung, Halter der Sperre im Log, Windows-Speicherspalte), dann die zwei risikoarmen **Beschleuniger** im Darstellungswechsel (B1 alte Oberfläche nicht umfärben, B2 alte Oberfläche erst nach dem Aufdecken stückweise abbauen). Die Optionsseite „lazy“ zu bauen (B3) eher in 0.60.

---

## 1. Ausgangslage und Vorgehen

**Nicos Referenz-VM (berichtet):** Ubuntu 26.04, 4 vCPU, 4 GiB RAM (2,9 GiB im Leerlauf belegt), Swap 3,8 GiB, 1920×1080, Wayland-Sitzung, Programm über XWayland, Zugriff per RDP.

**Messumgebung (belegt):**
- Linux-Container: Ubuntu 24.04, 4 Kerne Xeon 2,1 GHz, 16 GiB, kein Swap. Python 3.12.3, Tk 8.6.14, customtkinter 6.0.0, Pillow 12.3.
- Anzeige: Xvfb 1920×1080. Zusätzlich **mutter 46.2 headless (Wayland) mit Xwayland 23.2.6** als Nachbau von Nicos Anzeige-Schicht, ohne RDP und ohne Grafikkarte.
- Windows: GitHub-Runner `windows-2025`, Python 3.12.10, über einen Mess-Workflow nur auf diesem Zweig (Lauf 37575755585).
- Leere Datenbank, Spielstand angelegt (Linux). Fenster 1360×880, Schrift normal, Farbwelt Standard. Die eingebaute Leistungsmessung war eingeschaltet wie bei Nico.
- Grenzen über cgroups: Speicher 1100 MB bzw. 260 MB, CPU 25 % eines Kerns (soll die langsame VM nachbilden).

**Ablauf wie bei Nico (F1):** Start, Vorladen abwarten, alle großen Seiten einmal öffnen. Dann **6 Darstellungswechsel** Hell/Dunkel aus den Optionen. Zwischen den Wechseln jeweils Übersicht, Lernfortschritt, Karteikarten öffnen und das Vorladen abwarten. Je Version 3 Durchläufe (Windows 2). Dazu Varianten ohne eingebaute Messung, ohne Abwarten und ohne Vorladen.

Skripte (alle im Zweig unter `untersuchung_linux_speicher/skripte/`, ändern nichts am Programm):

| Skript | Zweck |
|---|---|
| `messung_wechsel.py` | F1/F2/F4: Darstellungswechsel mit Teilzeiten, Speicher-Spitze (Abtastung alle 20 ms), Elemente |
| `f3_optionen_bereiche.py` | F3: Kosten und Elemente je Optionsbereich |
| `f5_schliessen.py`, `f5_echt.sh`, `wm_delete.py` | F5: Schließen mit Zeitstempeln. Mit dem echten .deb wird über `WM_DELETE_WINDOW` geschlossen, wie mit dem X am Fenster. |
| `sperre_vererbung.py`, `f6_spaete_antwort.py` | F6: Vererbung der Sperre, zweiter Start bei blockiertem Programm |
| `f8_speicher_windows.py` | F8: Speicherabfrage unter Windows |
| `f10_threads.sh` | F10: Wartepunkte der Threads im Ruhezustand |
| `f11_xwayland_last.sh` | F11: Darstellungswechsel unter mutter/Xwayland mit Klicks, Stapel bei Stillstand |
| `mit_grenze.sh` | Speicher- und CPU-Grenze per cgroup |
| `tabelle.py` | CSV-Auswertung |

---

## 2. Antworten auf F1–F11

### F1 Regression 0.58.1 → 0.59.1?

**Antwort: Nein, keine nennenswerte Regression.** (belegt)

| Umgebung | Version | Wechsel | Median | Spanne | Spitze Speicher |
|---|---|---|---|---|---|
| Linux (Xvfb) | 0.58.1 | 18 | **3579 ms** | 3334–4753 | 262 MB |
| Linux (Xvfb) | 0.59.1 | 18 | **3597 ms** | 3357–4011 | 241 MB |
| Windows-Runner | 0.58.1 | 12 | **3670 ms** | 3645–4072 | 237 MB |
| Windows-Runner | 0.59.1 | 12 | **3930 ms** | 3814–4482 | 238 MB |
| Linux, CPU 25 % | 0.58.1 | 3 | 15906 ms | 15090–18189 | 237 MB |
| Linux, CPU 25 % | 0.59.1 | 3 | 15701 ms | 15204–16809 | 240 MB |
| Linux, Speicher ≤ 1100 MB | 0.59.1 | 6 | 3417 ms | 3330–4105 | 241 MB |
| mutter + Xwayland (mit Klicks) | 0.59.1 | 10 | 3929 ms | 3563–4457 | 248 MB |
| mutter + Xwayland, CPU 25 % | 0.59.1 | 8 | 13241 ms | 12817–13818 | 247 MB |

- Unter Linux ist 0.59.1 gleich schnell (+0,5 %, im Rauschen). Unter Windows ist es ca. **4–7 % langsamer**. Das passt zu den 87 zusätzlichen Elementen der Optionsseite (818 statt 731, Klappköpfe, Vorlagen-Unterbereich) und zu insgesamt +2 % Elementen (3791 statt 3704).
- **Nicos offene PC-Frage** (berichtet: Windows 3,2 → 4,7 s): Wenn überhaupt, ist 0.59.1 unter Windows um wenige Prozent langsamer. Ein Sprung auf 4,7 s kommt nicht von der Version, sondern von **mehr gebauten Elementen** (6104 bei Nico, siehe F2).
- Mit **25 % CPU** (nachgebaute langsame VM) sind beide Versionen gleich (je ca. 15–18 s). Die Optionsseite braucht dabei 5,4–6,6 s. Das trifft Nicos VM-Werte (10–17 s, 5,0–8,8 s) gut (belegt im Container, Übertrag auf die VM vermutet).
- **Speichergrenze:** Mit 1100 MB (ungefähr Nicos freier Speicher) ändert sich nichts (belegt). Mit 260 MB wird das Programm im Container beendet (OOM). Das ist mit der VM nicht vergleichbar, denn der Container hat keinen Swap, die VM hat 3,8 GiB (belegt im Container, nicht übertragbar).
- `ulimit` habe ich nicht genutzt. Die cgroup-Grenze ist genauer, weil sie den tatsächlich belegten Speicher begrenzt.

Messdaten: `messdaten/darstellungswechsel.csv` (jede Zeile ein Wechsel), `messdaten/laeufe.csv`.

### F2 Was kostet der Darstellungswechsel?

**Aufteilung (Linux, 0.59.1, Median aus 18 Wechseln, gesamt 3597 ms)** (belegt):

| Teil | ms | Anteil | wächst mit gebauten Seiten? |
|---|---|---|---|
| **Umfärben der alten Oberfläche** (`apply_appearance` → customtkinter ruft für jedes alte Element `_set_appearance_mode` auf, jedes zeichnet neu) | 744 | 21 % | **ja** |
| Neuen Rahmen bauen (Seitenleiste, Kopf) | ~140 | 4 % | nein |
| **Optionsseite neu bauen und zeigen** (`show_view`), darin ca. 710 ms `build()`, ca. 400 ms Spielansicht für den Schwierigkeitsgrad (`_show_difficulty`), Rest Zeichnen | 1386 | 39 % | nein |
| **Abbau der alten Oberfläche** (`old.destroy()`, alle vorgeladenen Seiten) | 877 | 24 % | **ja** |
| Zeichnen (`update`), Abdeckung, Rest | ~355 | 10 % | etwas |

**Warum die Zeit mit der Zahl schon gebauter Seiten wächst** (belegt):

| Elemente vor dem Wechsel | gesamt | Umfärben | Abbau alt |
|---|---|---|---|
| 1157 (nichts vorgeladen) | 1688 ms | 149 ms | 103 ms |
| 3791 (alles vorgeladen) | 3597 ms | 744 ms | 877 ms |

- Pro zusätzlichem Element kostet der Wechsel im Container ca. **0,7 ms** (Umfärben und Abbau zusammen). Der Rest (Optionsseite, Rahmen) ist fest.
- Hochrechnung für Nico (vermutet): (1688 ms + 0,72 ms × (5330 − 1157)) ≈ 4,7 s im Container. Die VM ist nach F1 ca. 3,5-mal langsamer, also ≈ **16–17 s**. Gemessen hat Nico 17,1 s.
- Warum Nico mehr Elemente hat als meine Messung (5330 statt 3791): echte Lerndaten (Übersicht, Fortschritt, Notizblock) und vermutlich vorgeladene Reiter von Firma/Reise mit echtem Spielstand (vermutet).

**Blockierende Stellen im Hauptfaden** (belegt im Code, `app_gui.py` v0.59.1):
- Der ganze Wechsel ist **ein einziger Block** im Hauptfaden: `change_color` → `_show_busy` → `_recolor` → `_hide_busy`. Ereignisse werden nur in den eingebauten `update()`-Aufrufen verarbeitet: `_show_busy` (`update_idletasks` + `update`) und `_recolor` (`update_idletasks` vor dem Bau, `update_idletasks` + `update` nach dem Bau, `update` vor `destroy`). Dazwischen liegen Abschnitte von je mehreren Sekunden auf der VM ohne Ereignisverarbeitung. In dieser Zeit beantwortet das Programm auch die „Lebst du noch?“-Anfrage von GNOME (`_NET_WM_PING`) nicht.
- Während des ganzen Wechsels hält die Abdeckung einen **`grab_set`**. Laut Tk-Quelle (tkGrab.c) wird bei einem Mausklick während eines lokalen Grabs kurzzeitig ein **echter X-Grab** (`XGrabPointer`/`XGrabKeyboard`) gesetzt. Klickt Nico während des Wechsels, laufen also X-Anfragen mit Rückantwort (Quelle aus der Recherche, siehe F10; im Programm nicht nachgemessen).
- `time.sleep(BUSY_MIN_SECONDS = 0,6 s)` greift nur, wenn der Wechsel schneller als 0,6 s war (auf der VM nie).
- **Nach** dem Wechsel startet das Vorladen neu (`preloader.start()`): 16 Schritte zu je 50–960 ms im Container, auf der VM also bis ca. 3,5 s je Schritt. Die längsten Schritte sind Optionen (964 ms), Rechner (819 ms), AP1-Szenarien (571 ms) und Karteikarten (565 ms) (belegt im Container, VM-Werte hochgerechnet).
- Die Ladeanzeige (`_show_loading`) pumpt höchstens 100 Fensterereignisse mit `dooneevent` und setzt ebenfalls einen `grab_set`.
- Die eingebaute Leistungsmessung bindet `bind_all("<Configure>")`. Ohne Messung lag der Wechsel unter Linux bei 3365 ms statt 3597 ms (0.59.1). Bei 0.58.1 war es umgekehrt (3816 statt 3579). Der Einfluss ist also klein und nicht eindeutig (belegt).

Profil eines Wechsels (cProfile): `messdaten/profil_darstellungswechsel_0.59.1.txt`. Hinweis: Python 3.12 zeichnet dabei auch den Mess-Hilfsthread auf, `time.sleep` und `rss_mb` im Profil kommen von dort.

### F3 Optionsseite: Werden eingeklappte Bereiche trotzdem gebaut?

**Ja.** (belegt im Code und gemessen) `SettingsView.build()` baut für jeden `FoldCard` den kompletten Inhalt. Beim Einklappen wird nur der innere Rahmen nicht angezeigt (`pack_forget`), die Elemente existieren aber.

| Bereich | beim Öffnen eingeklappt | Elemente | Bauzeit (Median, Container) | Anteil an build() |
|---|---|---|---|---|
| Farben (mit Vorlagen und eigenen Farben) | ja | 306 | 248 ms | 35 % |
| Rahmenplan | ja | 63 | 88 ms | 12 % |
| Datenbank | ja | 31 | 57 ms | 8 % |
| Löschen | ja | 54 | 38 ms | 5 % |
| Tagesziel | ja | 49 | 37 ms | 5 % |
| Schrift, Abgleich, Spiel, Rundgang, Leistung, Sicherung, Über, Lerninhalte | ja | je 21–45 | je 15–32 ms | je 2–4 % |
| Updates, Problem melden | **nein** (offen) | 23 / 32 | 19 / 30 ms | 3 / 4 % |
| **Summe build()** | | **818** | **712 ms** | |

- Eingeklappte Bereiche: ca. **660 von 712 ms (93 %)**.
- Dazu baut `on_show` der Optionen die **Spielansicht** für den Schwierigkeitsgrad mit (ca. 400 ms beim Darstellungswechsel, belegt im Profil).
- **Hinweis zu Nicos Zahl 4758–5330:** In der Messdatei steht beim Ereignis `seite` von „“ nach `settings` die Elementzahl des **ganzen Fensters**, und zwar in dem Moment, in dem alte und neue Oberfläche gleichzeitig existieren. In meiner Messung waren das 5358 Elemente, die Optionsseite selbst hat 818 (belegt).

**Inhalte erst beim ersten Aufklappen bauen (nur Einschätzung):**
- **Aufwand: mittel** (ca. 1 Tag).
  - `FoldCard` bekommt eine Bau-Funktion, die beim ersten `set_opened(True)` läuft. Die 13 Bereichsblöcke in `build()` werden zu eigenen Methoden.
  - Alle Stellen, die Inhalte direkt ansprechen, müssen „noch nicht gebaut“ vertragen: `show_sync_status` (Abgleich), `refresh_plan` (Rahmenplan), `open_area` (Suche, ab 0.59), `custom_colors`, `font_choice`, `entry_name`, `rp_vars`/`rp_dates` sowie Tests (`test_optionen`, `test_rundgang_hilfe`, `test_leistung`).
  - Die Spielansicht für den Schwierigkeitsgrad erst beim Öffnen des Bereichs „Spiel“ bauen.
- **Risiko: mittel.**
  - Die Suche muss den Bereich vor dem Öffnen bauen.
  - Der Tastaturfokus beim Aufklappen muss stimmen.
  - Bereiche, die beim Neuaufbau nach Farb- oder Schriftwechsel offen bleiben, müssen sofort gebaut werden.
  - Das erste Aufklappen von „Farben“ dauert spürbar (auf der VM ca. 1 s).
- **Erwarteter Gewinn:**
  - Optionsseite 712 → ca. 50–100 ms `build()`, ohne Spielansicht weitere ca. 400 ms.
  - Darstellungswechsel: ca. 1,0 s von 3,6 s im Container (ca. 25–30 %), auf der VM ca. **3–4 s weniger je Wechsel**.
  - Beim Vorladen fällt der längste Schritt (Optionen, auf der VM ca. 3,4 s) weg. Das hilft auch F6 (siehe dort).

### F4 Speicher

| Zeitpunkt | Linux (Container) | Windows-Runner | Nico (berichtet) |
|---|---|---|---|
| Start (Übersicht steht) | 105 MB | 96 MB | – |
| nach Vorladen | 176 MB | 174 MB | – |
| nach allen Seiten | 185 MB | 179 MB | 180 MB |
| Spitze beim Darstellungswechsel | 241 MB (einmal 262) | 238 MB | 256 MB |
| nach 6 Wechseln | 241 MB | 238 MB | – |
| davon Bild-Zwischenspeicher | 131,7 MB | 138 MB | – |

(belegt bis auf die letzte Spalte)

- **Passt 192 MB auf 4 GiB?** Ja. Das ganze Programm braucht in der Spitze ca. 260 MB, das sind ca. 6 % von 4 GiB. Bei 1,1 GiB freiem Speicher bleibt reichlich Luft. Nicos `vmstat` zeigt beim Hängen keine Swap-Bewegung und `wa = 0` (berichtet). Mit 1100 MB cgroup-Grenze ändert sich im Container nichts (belegt). **Der Speicher erklärt weder Langsamkeit noch Hängen.**
- Der Zwischenspeicher füllt sich nur auf ca. 132–138 MB (beide Darstellungen). Die Obergrenze 192 MB wird im normalen Betrieb nicht erreicht, nur beim langen Ziehen der Fenstergröße (belegt in 0.58.1).
- **Obergrenze nach freiem Speicher (nur Konzept):**
  - Beim Start einmal den verfügbaren Speicher lesen: Linux `MemAvailable` aus `/proc/meminfo`, Windows `GlobalMemoryStatusEx`, macOS fester Wert.
  - Grenze = 10 % davon, mindestens 96 MB, höchstens 192 MB. Auf Nicos VM wären das ca. 110 MB.
  - Aufwand gering (ca. 30 Zeilen in `fisi_widgets`, 3 Tests), Risiko gering.
  - Aber: Unter ca. 135 MB müssen bei jedem Darstellungswechsel Bilder neu berechnet werden. Mit 96 MB waren das in 0.58.1 ca. 155 Bilder je Wechsel. Das macht den Wechsel auf schwachen Geräten **langsamer** statt schneller.
  - **Empfehlung: jetzt nicht umsetzen.** Höchstens den verfügbaren Speicher in der Startzeile der Messdatei mitschreiben (nur Information).

### F5 Schließen: Warum lebt der Prozess noch bis zu 8 s?

**Im Container nicht nachstellbar** (belegt). Gemessen habe ich die Zeit vom Schließen bis zum Prozessende, mit eingeschaltetem Notausgang (8 s):

| Variante | on_close (Fenster abbauen) | Prozessende nach Schließen | Notausgang |
|---|---|---|---|
| Linux Xvfb, 0.58.1 und 0.59.1, ohne und mit 2 Wechseln | 309–343 ms | sofort danach | nein (4×) |
| Linux Xvfb, CPU 25 %, beide Versionen | 1394–1672 ms | sofort danach | nein (4×) |
| Windows-Runner, beide Versionen | 510–608 ms | sofort danach | nein (4×) |
| **Echtes .deb 0.59.1**, Xvfb, Schließen per `WM_DELETE_WINDOW` | – | 0,61 s | nein |
| **Echtes .deb 0.59.1**, mutter + Xwayland | – | 0,62 s | nein |

**Was den Prozess halten könnte** (Code gelesen, belegt):
- **Threads:** Alle Threads des Programms sind `daemon=True` (Update-Suche, Abgleich, Rahmenplan-Vorberechnung, Einzelstart, Notausgang). Daemon-Threads halten das Beenden nicht auf. Beim Ende der Ereignisschleife lief in allen Messungen nur noch `MainThread` und `fisi-notausgang`.
- **`after`-Rückrufe:** werden in `on_close` alle abgebrochen. Nach `root.destroy()` läuft keine Ereignisschleife mehr.
- **Hilfsprozesse** (`xdg-open`, `pkexec`, `gio`) halten den Python-Prozess nicht am Leben.
- **Abgleich beim Beenden** (`run_before_exit`, bis 12 s) läuft **vor** dem Scharfschalten des Notausgangs, zählt also nicht zu den 8 s.
- Zwischen Notausgang und Prozessende liegen also nur `after cancel`, `root.destroy()` (Tk und X abbauen) und das Python-Ende.

**Vermutung:** Auf der VM hängt einer dieser Schritte an derselben Stelle wie beim Einfrieren, also an einer X-Anfrage an XWayland, die nicht beantwortet wird (z. B. `XSync` beim Abbau der Fenster oder beim Schließen der Anzeige-Verbindung). Dafür spricht: Es passiert nur unter Linux auf der VM (über RDP), dort aber jedes Mal, und weder Langsamkeit (CPU 25 %) noch Xwayland ohne RDP lösen es aus (belegt). Bestätigen lässt es sich mit der Stapelspur beim Schließen (Option A1, F9) oder mit Schritt 12 der VM-Anleitung.

**Gab es das schon in 0.58.1?** Der Notausgang existiert seit 0.55.1. Am Code von `on_close` hat sich zwischen 0.58.1 und 0.59.1 nichts geändert, was nach dem Scharfschalten läuft (belegt per `git diff`). Ob es auf der VM mit 0.58.1 schon auftrat: **nicht geprüft**. Nicos `fehler.log` enthält in jedem Kopf die Version, ein `grep` zeigt es (Schritt 11).

### F6 Sperre: Erbt ein Hilfsprozess die Sperre?

**Nein.** (belegt) Getestet mit dem Original-`fisi_einzelstart.claim()` aus 0.59.1. Der Elternprozess startet ein Kind und endet hart, danach prüft ein dritter Prozess die Sperre:

| Kind gestartet mit | Dateibeschreiber im Kind | Sperre nach Ende des Elternprozesses |
|---|---|---|
| `subprocess.Popen` (wie `xdg-open`, `pkexec`, Update) | 0, 1, 2 | **frei** |
| `Popen(close_fds=False)` (schlechtester Fall) | 0, 1, 2 | **frei** |
| `Popen(start_new_session=True)` (wie AppImage-Neustart) | 0, 1, 2 | **frei** |
| Gegenprobe: `pass_fds` (ausdrücklich vererbt) | 0, 1, 2, 3 | belegt |
| Gegenprobe: `fork` ohne `exec` (kommt im Programm nicht vor) | 0, 1, 2, 3 | belegt |

Der Grund: Python öffnet Dateien seit 3.4 mit `O_CLOEXEC` (Flags `02102002` im Test), und `exec` schließt sie. Die Gegenproben zeigen, dass der Test eine Vererbung erkennen würde.

**Stellen, die Hilfsprozesse starten** (belegt, `grep`):
- `fisi_update.install`: Windows-Installer (`Popen(close_fds=True)`), AppImage-Neustart (`Popen(start_new_session=True)`), `.deb` mit `run(["pkexec", "apt-get", …])` und bei Abbruch `Popen(["xdg-open", …])`, macOS `open`
- `app_gui.py`: Ordner öffnen mit `xdg-open`/`explorer` (2 Stellen), Release-Seite mit `webbrowser.open`
- `fisi_verknuepfung`: `xdg-user-dir`, `gio set …` (beide `run` mit Ende)

**Was Nicos Eintrag wirklich erklärt** (belegt nachgestellt mit `f6_spaete_antwort.py`):
- Das laufende Programm beantwortet zweite Starts über einen Zeitgeber (alle 0,4 s) im Hauptfaden. Ein zweiter Start wartet nur **3 s** auf die Antwort.
- Danach wartet er bis zu **25 s** auf die Sperre und **schaut nicht mehr nach einer späten Antwort**.

| Laufendes Programm | Ergebnis zweiter Start | fehler.log |
|---|---|---|
| nicht blockiert | nach 3,2 s still beendet, Fenster nach vorn | nichts |
| **4 s blockiert** (wie auf der VM beim Vorladen oder Darstellungswechsel) | **startet nach 28,1 s ohne Sperre → zweites Fenster** | „Mehrfachstart: … (Antwort: keine) … nach 25 s noch belegt. Start ohne Sperre.“ |

Auf der VM blockieren der Darstellungswechsel (10–17 s) und einzelne Vorlade-Schritte (bis ca. 3,5 s) den Hauptfaden länger als 3 s (vermutet aus F1/F2). Ein zweiter Klick in so einem Moment führt genau zu Nicos Eintrag, auch ohne einen anderen Prozess. **Rückfrage an Nico:** Stand in den beiden Einträgen „Antwort: keine“ oder „Antwort: endet“? Bei „endet“ war das Programm gerade beim Schließen, das passt dann zu F5.

**Halter der Sperre protokollieren (nur Konzept):**
- Wer die Sperre bekommt, schreibt in eine **eigene Datei** `laeuft.info` (nicht in `laeuft.lock`): Prozessnummer, Startzeit, Version.
- Eine eigene Datei ist nötig, weil unter Windows `msvcrt.locking` das Byte 0 von `laeuft.lock` sperrt. Ein anderer Prozess kann den gesperrten Bereich dann nicht lesen (vermutet nach Windows-Dokumentation, nicht geprüft).
- Der zweite Start hängt diese Angaben an den bestehenden Eintrag an. Unter Linux kommt der Zustand aus `/proc/<pid>/stat` dazu (z. B. `S` = schläft) und ob der Prozess noch existiert.
- Aufwand gering (ca. 30 Zeilen, 3 Tests), Risiko gering. Das Verhalten bleibt gleich, Fehler beim Schreiben oder Lesen werden geschluckt wie bisher.

### F7 Hängen erkennen (nur Konzept)

- **Herzschlag im Hauptfaden:** Nur bei eingeschalteter Leistungsmessung läuft alle 500 ms ein `after`-Rückruf. Er misst, wie viel später er drankommt als geplant.
- Ist die Verspätung größer als 2 s, schreibt er ein Ereignis `blockiert` mit der Dauer und der gerade gezeigten Seite in die Messdatei. Zusätzlich kann er den letzten bekannten Vorgang mitschreiben (z. B. „darstellung“, „vorladen:settings“).
- **Aufwand:** sehr gering (ca. 25 Zeilen in `PerfMonitor`, 2 Tests).
- **Risiko:** sehr gering. Ein Zeitgeber, der bei ausgeschalteter Messung gar nicht existiert, wird in `on_close` mit abgebrochen.
- **Grenze:** Ein **dauerhaftes** Hängen meldet er nicht, weil der Rückruf dann nie mehr läuft. Dafür ist F9 da (Wächter-Thread bzw. faulthandler).

### F8 Warum ist `speicher_mb` unter Windows leer?

**Ursache belegt** (Windows-Runner, `f8_speicher_windows.py`, beide Versionen):

```
1) fisi_leistung.memory_mb() unveraendert: (None, None)
2) GetCurrentProcess() ohne restype liefert: -1 0xffffffffffffffff
3) wie im Programm (Handle als int): 0 GetLastError 6 WorkingSet MB 0.0
4) mit restype/argtypes HANDLE: 1 WorkingSet MB 30.6, Private MB 22.9
5) psutil zum Vergleich: rss MB 32.1, private MB 22.1
```

- `ctypes` übergibt das Handle ohne Typangabe als 32-Bit-Zahl.
- Unter 64-Bit-Windows kommt es dadurch nicht als „aktueller Prozess“ an. `GetProcessMemoryInfo` scheitert mit **Fehler 6 (ungültiges Handle)**, und das Programm schreibt eine leere Spalte.
- Mit `restype = HANDLE` und passenden `argtypes` stimmen die Werte mit `psutil` überein.
- **Schon in 0.58.1 so:** gleiches Ergebnis mit 0.58.1. `fisi_leistung.py` ist seit 0.58.1 unverändert (`git log`).
- Am Handy und unter Linux betrifft es nichts (dort `/proc`).

### F9 Diagnose-Vorabversion (Linux) – nur Entwurf, Nico entscheidet

**Ziel:** Bei einem Hängen und beim langen Schließen automatisch festhalten, **wo** das Programm steht. Nur Diagnose, kein anderes Verhalten.

**Bausteine:**
1. **Stapelspur bei Hängen (faulthandler):** Beim Start `faulthandler.enable(file=…)` mit Datei `haenger.log` im Datenordner. Der Herzschlag (alle 0,5 s im Hauptfaden) setzt jedes Mal `faulthandler.dump_traceback_later(30, repeat=True, file=…)` neu.
   - Steht der Hauptfaden 30 s still, schreibt faulthandler aus seinem eigenen C-Thread die Python-Stapel **aller** Threads, alle 30 s erneut.
   - Das funktioniert auch, wenn der Hauptfaden in C (Xlib) festhängt, denn faulthandler braucht dafür weder GIL noch Ereignisschleife. faulthandler ist im Paket enthalten (belegt: fest eingebaut in `libpython3.12.so` des .deb).
2. **Stapel auf Abruf ohne sudo:** `faulthandler.register(signal.SIGUSR1, all_threads=True, file=…)`. Nico kann dann im Terminal `kill -USR1 $(pgrep -x FISI-Lernplattf | head -1)` eingeben. Im Container getestet: Der Stapel wird geschrieben, während der Hauptfaden mitten im Darstellungswechsel in Tk-Code steckt (belegt, Ausgabe in `messdaten/stapel_sigusr1_beispiel.txt`).
3. **Wächter-Ereignis:** Ein Daemon-Thread prüft jede Sekunde den Zeitstempel des Herzschlags. Ist er älter als 5 s, schreibt er einmalig eine Zeile in `fehler.log`: „Hauptfaden seit 5 s ohne Rückruf, letzte Seite …, Vorgang …“. Dazu kommen die Wartepunkte aller Threads aus `/proc/self/task/*/wchan` (Linux, ohne sudo).
   - Diese Wartepunkte zeigen `futex_do_wait` (normal) oder `poll_schedule_timeout` (wartet auf X).
   - Läuft der Herzschlag wieder, kommt eine zweite Zeile „wieder frei nach X s“. So ist „dauerhaft“ von „lange blockiert“ zu unterscheiden.
4. **Beim Schließen:** In `on_close` direkt nach dem Notausgang zusätzlich `faulthandler.dump_traceback_later(5)`. Lebt der Prozess 5 s nach dem Schließen noch, steht in `haenger.log`, in welcher Python-Zeile er hängt. Das beantwortet F5 auf der VM.

**Dateien (Entwurf):**
- neu `fisi_haenger.py`: ca. 90 Zeilen, ohne Oberfläche: Einrichten, Herzschlag-Ziel, Wächter-Thread, wchan lesen, Größenbegrenzung `haenger.log` auf 512 KB
- `app_gui.py`: ca. 10 Zeilen in `main()`, `on_close` und `PerfMonitor`
- neu `test_haenger.py`: ca. 6 Tests (Wächter meldet bei blockiertem Hauptfaden, kein Eintrag im Normalfall, Datei bleibt klein, Signal schreibt Stapel)
- Problembericht: `haenger.log` als zusätzlicher Abschnitt (wie `update.log`), optional

**Bau:** wie `vorab-0.59.1-test1` über den vorhandenen Vorab-Job (`build.yml`, `vorab_dateien=linux-handy`), nur `.deb`. Version bleibt 0.59.1, Name z. B. `0.59.1-diag1`. Den Tag-Push macht Nico am PC, aus der Cloud scheitert er (403).

**Aufwand:** ca. ½ Tag inklusive Tests und Vorab-Lauf.

**Risiko:** gering.
- faulthandler gehört zur Standardbibliothek und ist im Paket enthalten (belegt, siehe oben).
- Die Datei bleibt offen und wird klein gehalten.
- Der Wächter-Thread ist daemon und liest nur.
- Einziges Restrisiko: Ein Fehler im Herzschlag-Zeitgeber muss abgefangen werden, damit er nie eine Fehlermeldung zeigt.

**Nutzen:** hoch. Es ist der einzige Weg, die Ursache auf Nicos VM ohne `sudo gdb` sicher zu sehen.

### F10 Tk und Anzeige-Schicht

**Versionen im Linux-Paket 0.59.1** (belegt, aus dem Release-.deb gelesen):
- **Python 3.12.14**, **Tcl 8.6.12**, **Tk 8.6.12** (`_internal/libtcl8.6.so`, `libtk8.6.so`)
- mitgeliefert: `libX11.so.6`, `libxcb` (umbenannt), `libXft.so.2`, `libXss.so.1`
- Herkunft: Gebaut auf `ubuntu-22.04` mit `actions/setup-python`. Die Python-Builds von actions/python-versions binden das Tk des Runners ein, PyInstaller packt es mit ([actions/python-versions, ubuntu-python-builder](https://github.com/actions/python-versions/blob/main/builders/ubuntu-python-builder.psm1)). Das Programm benutzt auf Ubuntu 26.04 also **Tk 8.6.12 aus 2021 und Xlib/xcb aus Ubuntu 22.04**, nicht die Versionen des Systems (Ubuntu 26.04: libtk8.6 8.6.17, [packages.ubuntu.com](https://packages.ubuntu.com/search?keywords=libtk8.6&searchon=names&suite=all&section=all)).

**Threads im Normalzustand** (belegt mit dem echten Paket unter Xvfb und unter mutter/Xwayland, `f10_threads.sh`/`f5_echt.sh`):

```
Thread 1 (Hauptfaden)  S  wchan=futex_do_wait              <- wartet auf Tcl-Notifier
Thread 2 (Tcl-Notifier) S  wchan=poll_schedule_timeout      <- select() auf die X-Verbindung
```

- Tcl 8.6 mit Threads hat einen eigenen Notifier-Thread, der in `select()` wartet. Der Hauptfaden wartet währenddessen auf eine Bedingungsvariable (futex) ([tclUnixNotfy.c](https://fossies.org/linux/tcl/unix/tclUnixNotfy.c)). Erst Tcl 9 hat einen epoll-Notifier ohne diesen Thread ([TIP 458](https://core.tcl-lang.org/tips/doc/trunk/tip/458.md)).
- **Bei Nico standen beide Threads in `poll_schedule_timeout`** (berichtet). Der Hauptfaden war also **nicht** im normalen Warten der Ereignisschleife, sondern in einem eigenen `poll()`.
- Im Programm macht das praktisch nur Xlib/xcb, wenn es auf eine Antwort des X-Servers wartet (`_XReply` → `xcb_wait_for_reply`). Diesen Aufrufweg habe ich in F11 unter Xwayland als Momentaufnahme gesehen, dort während normaler Arbeit und nicht als Hänger (für Nicos Fall vermutet, gut gestützt).
- Dazu passt `Recv-Q 0`: Es liegt nichts zum Lesen an, der X-Server hat (noch) nicht geantwortet (berichtet und vermutet).

**Bekannte Fälle und Quellen** (Recherche; nur Titel bzw. Inhalt so weit lesbar, gitlab.gnome.org und Launchpad waren teils gesperrt):
- mutter markiert X11-Fenster, die nicht auf `_NET_WM_PING` antworten, als „nicht reagierend“. Solche Fenster bekamen in einem Fehlerfall keine Zeigerereignisse mehr ([mutter MR 3367](https://gitlab.gnome.org/GNOME/mutter/-/merge_requests/3367), [Issue 2900](https://gitlab.gnome.org/GNOME/mutter/-/issues/2900)). Die Wartezeit steht in `org.gnome.mutter check-alive-timeout`, Standard 5000 ms ([Fedora-Diskussion](https://discussion.fedoraproject.org/t/how-to-disable-app-is-not-responding-popup-on-gnome/74001/2)).
- Tk beantwortet den Ping im eigenen Protokoll-Handler (tkUnixWm.c), aber nur, wenn die Ereignisschleife läuft. Bei 10–17 s Block antwortet es also nicht.
- XWayland-Apps nahmen nach Arbeitsflächenwechsel keine Mausklicks mehr an, behoben in mutter 48.3.1 ([GNOME Discourse](https://discourse.gnome.org/t/48-2-xwayland-apps-not-registering-mouse-press-after-changing-workspace/29356)). Anderes Muster, zeigt aber, dass solche Fehler vorkommen.
- „XWayland freezes frequently“ ([Launchpad 1992155](https://bugs.launchpad.net/ubuntu/+bug/1992155), nur Titel lesbar).
- gnome-remote-desktop: „No input possible anymore (or only too slow?)“ ([g-r-d #22](https://gitlab.gnome.org/GNOME/gnome-remote-desktop/-/work_items/22), Inhalt nicht lesbar). Mausklicks gehen unter g-r-d ohne physische Maus nicht ([gnome-shell #2482](https://gitlab.gnome.org/GNOME/gnome-shell/-/work_items/2482), nur Titel). Sporadische Eingabe-Aussetzer einer XWayland-App unter GNOME 46 ([Devolutions-Forum](https://forum.devolutions.net/topics/55780/rdm-linux-intermittently-stops-accepting-keyboard-and-leftclick-input-)).
- Im Tk-Bugtracker gibt es keinen Eintrag zu XWayland-Hängern. Das Tk-Änderungsprotokoll 8.6.13–8.6.17 enthält keinen XWayland-Fix. Erwähnenswert ist [Tk eb3328](https://core.tcl-lang.org/tk/tktview/eb3328) („grid/pack with half-dead argument can cause hangup“, behoben in 8.6.16; ob es hier zutrifft: nicht geprüft). In customtkinter gibt es nur Leistungs-Issues ([#2690](https://github.com/TomSchimansky/CustomTkinter/issues/2690)), keine Hänger.
- Tk-Quelle tkGrab.c (8.6.12): Ein lokaler `grab_set` setzt bei einem Mausklick kurzzeitig einen echten X-Grab.

**Mögliche Umgehungen (nur Konzept, keine belegt wirksam):**
- **Kürzere Blöcke:** Darstellungswechsel in Schritten über `after()` statt in einem Rutsch (siehe B1/B2). Dann beantwortet das Programm Pings und Ereignisse zwischendurch.
- **Kein `grab_set`** auf Abdeckung und Ladeanzeige, Klicks stattdessen auf der Abdeckung abfangen (`bind` auf Klick und Taste). Dann entstehen bei Klicks während des Wechsels keine X-Grabs.
- **Weniger `update()`,** stattdessen `update_idletasks()`, wo nur gezeichnet werden soll. `update()` verarbeitet auch Eingaben und WM-Nachrichten mitten im Umbau.
- **Neueres Tk mitliefern:** z. B. Build auf ubuntu-24.04 (Tk 8.6.14) oder eigenes Tk 8.6.17. Belegt hilft das nichts, wäre aber ein günstiger Test (eigener Vorab-Build).
- **Test ohne RDP** (Nico, Proxmox-Konsole): Klärt, ob gnome-remote-desktop beteiligt ist.
- Eine Tk-spezifische Umgebungsvariable, die XWayland-Probleme umgeht, habe ich nicht gefunden.

### F11 Reproduktion im Container

| Anzeige | Ablauf | Ergebnis |
|---|---|---|
| Xvfb (ohne Fenstermanager) | 0.58.1/0.59.1, 6 Wechsel, je 3 Durchläufe | kein Hängen, Langsamkeit mit CPU 25 % nachgestellt (15–18 s je Wechsel) (belegt) |
| mutter 46.2 headless + Xwayland 23.2.6 | 10 Wechsel, alle 0,3 s Klick und Tab ins Fenster (xdotool), volle CPU | kein Hängen, Wechsel 3,6–4,5 s (belegt) |
| mutter + Xwayland, **CPU 25 %** | 4 Wechsel mit Klicks | **siehe unten** |

**Ergebnis mutter + Xwayland mit 25 % CPU** (belegt):
- 2 vollständige Läufe mit je 4 Wechseln (12,8–13,8 s je Wechsel) und Klicks und Tabs alle 0,3 s: **kein Hängen**. Ein weiterer Lauf brach nach 2 Wechseln ab, weil mein Hintergrundprozess für mutter nach seiner Zeitgrenze beendet wurde („X connection broken“). Das war ein Fehler meiner Umgebung, nicht des Programms.
- Im ersten Lauf meldete mein Wächter nach 60 s ohne neue Zeile einen Stillstand. Die Momentaufnahme zeigte den Hauptfaden **in Arbeit** (Zustand `R`) mit dem Stapel `XSync` → `_XReply` → `xcb_wait_for_reply` → `poll`. Bei 25 % CPU dauert der Abschnitt bis zur ersten Zeile aber über 60 s (Start, Vorladen, Seiten, Wechsel). Das war also **kein Hänger, sondern meine zu kurze Wartegrenze**. In den folgenden Läufen mit 120 s Grenze und Prüfung der Prozessorzeit gab es keinen Stillstand.
- Brauchbar ist die Momentaufnahme trotzdem: Sie zeigt, dass Tk beim Neuaufbau ständig synchron auf XWayland wartet (`XSync`). Antwortet XWayland an so einer Stelle nicht, steht der Hauptfaden genau so, wie Nico es gesehen hat: in `poll`, 0 % Prozessor (vermutet).
- Nebenbefund (belegt per Stapelabruf mitten im Wechsel): customtkinter ruft beim Zeichnen von Scrollbalken selbst `update_idletasks()` auf. Daraus entstehen **verschachtelte** Ereignis-Durchläufe, im Beispiel 8 Ebenen `_draw` → `update_idletasks` → `_set_hscroll` → `set` → `_draw` … (`messdaten/stapel_sigusr1_beispiel.txt`). Das kostet Zeit und macht den Ablauf schwer vorhersagbar. Ein Fehler ist es für sich nicht.

**Antwort F11:** Die **Langsamkeit** lässt sich nachstellen (CPU 25 % ergibt Nicos Zeiten). Das **Hängen** lässt sich mit Xvfb und mit mutter + Xwayland ohne RDP **nicht** nachstellen (belegt für die getesteten Abläufe).

**Was fehlt für einen vollständigen Nachbau:** ein echtes **gnome-remote-desktop** mit RDP-Client in derselben GNOME-Sitzung (braucht gnome-shell, PipeWire, einen RDP-Client und eine Benutzersitzung mit systemd) und eine echte Grafik. Beides ist im Container nicht vorhanden. Ob das Hängen auch ohne RDP auftritt, kann nur Nicos Test über die Proxmox-Konsole klären.

---

## 3. Konzeptpapier: Optionen

| Nr | Maßnahme | Aufwand | Risiko | Erwarteter Nutzen | Empfehlung |
|---|---|---|---|---|---|
| **A1** | Diagnose bei Hängen und Schließen (faulthandler, Wächter, SIGUSR1, siehe F9) | ½ Tag | gering | **hoch**: zeigt auf der VM, wo es hängt | **0.59.2**, vorher als Vorab-.deb |
| **A2** | Windows-Speicherspalte reparieren (F8: `restype`/`argtypes`) | 1 Std. | sehr gering | Messdatei am PC vollständig | **0.59.2** |
| **A3** | Messdatei: verfügbarer Speicher in der Startzeile, letzter Vorgang | 1 Std. | sehr gering | einordnen | 0.59.2 (optional) |
| **F** | Blockier-Ereignis in der Leistungsmessung (F7) | 2 Std. | sehr gering | zeigt, wie oft und wie lange die VM blockiert | **0.59.2** |
| **E1** | Halter der Sperre protokollieren (`laeuft.info`) | 2–3 Std. | gering | klärt künftige Mehrfachstart-Einträge | **0.59.2** |
| **E2** | Zweiter Start achtet während der 25 s weiter auf eine **späte Antwort „da“** und endet dann still (Verhaltensänderung!) | 2 Std. | gering | kein zweites Fenster mehr, wenn das Programm nur kurz blockiert war | 0.59.2, **nur mit Nicos OK** |
| **B1** | Darstellungswechsel: **alte Oberfläche nicht mehr umfärben**. Die alten Elemente vor `apply_appearance()` von der customtkinter-Farbliste abmelden, sie werden ohnehin zerstört. | ½ Tag | mittel (customtkinter-Interna, Version ist auf 6.0.0 festgelegt, Test muss bei anderer Version warnen wie in 0.58.1) | ca. **20 %** je Wechsel, wächst mit gebauten Seiten (VM ca. 2–4 s) | 0.59.2 oder 0.60 |
| **B2** | Darstellungswechsel: Abdeckung **vor** dem Abbau der alten Oberfläche wegnehmen und alte Seiten **einzeln über `after()`** abbauen | ½ Tag | gering–mittel (verwaiste Zeitgeber, siehe `_cancel_orphaned_timers`) | ca. **24 %** kürzerer Block, Programm reagiert zwischendurch (Pings, zweiter Start) | 0.59.2 oder 0.60 |
| **B3** | Optionen **lazy**: Bereiche erst beim ersten Aufklappen bauen, Spielansicht erst bei „Spiel“ (F3) | 1 Tag | mittel | ca. **25–30 %** je Wechsel, längster Vorlade-Schritt fällt weg | **0.60** |
| **B4** | Darstellungswechsel ganz in Schritten (`after`-Kette) statt in einem Block, ohne `grab_set` | 1–2 Tage | mittel–hoch (Zwischenzustände, Klicks während des Umbaus) | Fenster bleibt immer bedienbar, umgeht vermutlich das Hängen | erst nach A1-Ergebnis |
| **C** | Bild-Zwischenspeicher nach freiem Speicher (F4) | 2 Std. | gering | keiner auf Nicos VM (Speicher reicht), eher langsamer | **nicht umsetzen** |
| **D** | Schließen: erst nach A1-Befund entscheiden (z. B. `withdraw` + `os._exit` nach dem Sichern statt `destroy`, wenn `destroy` an X hängt) | offen | offen | Notausgang entfällt | nach A1 |
| **G** | Vorab-Test mit neuerem Tk (Build auf ubuntu-24.04 → Tk 8.6.14) | 2 Std. | gering (nur Vorab) | klärt, ob Tk 8.6.12 beteiligt ist | optional nach A1 |

**Reihenfolge-Vorschlag:**
1. **Vorab-.deb „0.59.1-diag1“** mit A1 + F (nur Diagnose). Nico testet auf der VM mit und ohne RDP.
2. Mit dem Befund entscheiden, ob B4 oder D nötig ist.
3. **0.59.2** = A1, A2, F, E1 (+ E2, wenn Nico will) und B1 + B2, falls die Messung zeigt, dass sie ohne Nebenwirkung laufen. Das ist sinnvoll **vor 0.60**: Die VM ist Nicos Referenz, und die Diagnose hilft auch bei den 0.60-Tests.
4. **0.60:** B3 (Optionen lazy) zusammen mit den Optionen-Arbeiten (freie Möbel, Karten-Zugänglichkeit), dann B4, falls nötig.

---

## 4. Schritte für Nico auf der VM (nur lesen und beobachten)

Siehe auch die eigene Datei `VM_Schritte.md` mit denselben Schritten zum Abhaken. `sudo` nur, wo es dabei steht. Das macht Nico selbst.

**Vorbereitung (einmal)**
1. Terminal öffnen und festhalten: `echo $XDG_SESSION_TYPE; gnome-shell --version; dpkg -l fisi-lernplattform | tail -1; nproc; free -m`
2. Werkzeuge für später installieren (einmal, mit sudo): `sudo apt install x11-utils elfutils`

**Test 1: ohne RDP (Proxmox-Konsole)**
3. In der Proxmox-Konsole (nicht über RDP) anmelden und FISI aus dem Terminal starten: `fisi-lernplattform` (das Terminal offen lassen).
4. Leistungsmessung an, dann wie gewohnt 6–8 Darstellungswechsel mit Seitenbesuchen dazwischen. Ruhig auch während eines Wechsels klicken (Klicks lösen dabei kurze X-Grabs aus, siehe F2).
5. Notieren: Hing es? Erschien „FISI reagiert nicht“ von GNOME?

**Wenn es hängt (egal ob mit oder ohne RDP)**
6. **Mindestens 2 Minuten warten**, ohne zu klicken. Kommt es zurück? (Das klärt „dauerhaft“ oder „lange blockiert“.)
7. In einem zweiten Terminal: `PID=$(pgrep -x FISI-Lernplattf | head -1); echo $PID`
8. Wartepunkte: `for t in /proc/$PID/task/*; do echo "$(cat $t/comm) $(awk '{print $3}' $t/stat) $(cat $t/wchan)"; done`
9. Prozessorzeit in 10 s: `a=$(awk '{print $14+$15}' /proc/$PID/stat); sleep 10; b=$(awk '{print $14+$15}' /proc/$PID/stat); echo $((b-a))` (0 = schläft wirklich)
10. Antwortet XWayland anderen Programmen? `timeout 5 xdpyinfo -display :0 | head -3`. Kommen 3 Zeilen, lebt XWayland. Kommt nichts, hängt XWayland selbst.
11. **Stapel (mit sudo):** `sudo eu-stack -p $PID | head -60`. Interessant ist, ob im ersten Thread `XSync`, `_XReply` oder `xcb_wait_for_reply` steht. Ein Foto oder Text davon genügt.
12. Danach wie bisher über den Ressourcenmanager beenden.

**Schließen und Sperre**
13. `grep -n -A1 "Notausgang\|Mehrfachstart" ~/.local/share/fisi-lernplattform/fehler.log`. Interessant: Welche **Versionen** stehen im Kopf darüber (gab es das schon mit 0.58.1)? Und bei „Mehrfachstart“: steht dort **„Antwort: keine“** oder **„Antwort: endet“**?
14. Einmal FISI aus dem Terminal starten, nichts tun, nach 30 s am X schließen und im Terminal beobachten, wann die Eingabeaufforderung zurückkommt (sofort oder nach ca. 8 s). Einmal über RDP, einmal über die Proxmox-Konsole.
15. Ist der Abgleich (Optionen → Abgleich) eingerichtet? (Ja/Nein genügt, er läuft vor dem Notausgang.)

**Dateien schicken**
16. `~/.local/share/fisi-lernplattform/leistungsmessung.csv` und `fehler.log` von der VM. Für den PC-Vergleich zusätzlich `leistungsmessung.csv` vom Windows-PC.
17. Optional: `journalctl --user -b --since "-30 min" | grep -i -E "xwayland|mutter|remote" | tail -50`

---

## 5. Rückfragen an Nico

1. In den Mehrfachstart-Einträgen: „Antwort: keine“ oder „Antwort: endet“? (F6)
2. Soll ich die Diagnose-Vorabversion (F9, Option A1 + F) vorbereiten? Den Tag-Push machst du am PC.
3. E2 (zweiter Start wartet auf eine späte Antwort statt nach 25 s ein zweites Fenster zu öffnen) ist eine **Verhaltensänderung**. Gewünscht für 0.59.2?
4. B1/B2 (schnellerer Darstellungswechsel) schon in 0.59.2 oder erst 0.60?

---

## 6. Anhang

**Messdaten (CSV, `messdaten/`):**
- `uebersicht_darstellungswechsel.txt`: Kurztabelle aller Gruppen (Median, Teilzeiten)
- `darstellungswechsel.csv`: jeder einzelne Wechsel mit Teilzeiten, Elementen und Speicher (Linux, Windows, Varianten)
- `laeufe.csv`: je Lauf Start, Vorladen, Speicher, Elemente, Schließdauer
- `optionen_bereiche.csv`: F3 Kosten je Bereich
- `leistungsmessung_beispiel_0.59.1.csv`: die Messdatei des Programms aus einem Container-Lauf (gleiches Format wie bei Nico)
- `profil_darstellungswechsel_0.59.1.txt`: cProfile eines Wechsels
- `f5_schliessen.txt`, `f5_echt.txt`, `f6_sperre.txt`, `windows_f5_f8.txt`, `f11_xwayland.txt`, `stapel_sigusr1_beispiel.txt`: Rohausgaben

**Windows-Messlauf:** Workflow `.github/workflows/untersuchung-linux-speicher.yml`, nur auf diesem Zweig. Er löst nur bei Pushes auf diesen Zweig aus und baut und veröffentlicht nichts. Lauf 37575755585.

**Nicht angefasst:** Abgleich-Format, Lernstand, Schließlogik, Installer, Update-Ablauf, Farbwerte und Farbwelten, Spielwerte. Der Zweig enthält nur den Ordner `untersuchung_linux_speicher/` und den Mess-Workflow.
