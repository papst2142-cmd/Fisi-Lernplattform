# Kurzbericht: NVDA automatisch prüfen (Erkundung)

Stand 06.10.2026. Auftrag von Nico (10:11 Uhr). Zweig `proto-screenreader`, kein Pull-Request, kein Tag, kein Release. Am Hauptprogramm, an Daten, Spielwerten, Abgleich, Installer und Update-Ablauf wurde nichts geändert.

## Ergebnis in einem Satz

NVDA lässt sich auf einem GitHub-Windows-Rechner ohne Installation und ohne Lautsprecher starten, und alles, was NVDA sagt, landet als Text im NVDA-Protokoll. Damit wurden die Schritte 1 bis 26 der Testanleitung (Abschnitte 4.1 und 4.2) automatisch durchgespielt. **NVDA liest den Prototyp fast vollständig wie erwartet vor.** Unterwegs fiel ein Startfehler im gebauten Windows-Prototyp auf, der behoben ist.

## Wichtig vorab: Startfehler im Prototyp-ZIP (behoben)

- **Fehler:** Das ZIP von heute Morgen (Läufe bis einschließlich 10) zeigte nach dem Start nur die Flet-Fehlerseite „Error running app“. Die Optionen erschienen nicht.
- **Ursache:** Das gebaute Programm entpackt `main.py` in einen Temp-Ordner. Der Prototyp suchte `inhalte/karteikarten.json` deshalb im falschen Ordner. Belegt ist das in der `console.log` des Programms (siehe `ergebnisse/lauf10_protokoll.txt`).
- **Behebung:** Die Datei wird jetzt wie am Handy über `fisi_core.CONTENT_DIR` geladen (Commit 4cf1f99). Ab Lauf 11 startet der Prototyp richtig.
- **Zum Testen nimm das ZIP aus Lauf 11:** [Run 37442078537](https://github.com/papst2142-cmd/Fisi-Lernplattform/actions/runs/37442078537), Artefakt „FISI-Screenreader-Prototyp-Windows“. Lauf 12 ist beim Bauen gescheitert (siehe unten) und hat kein ZIP.

## Was ist bewiesen, was nur gelesen, was nicht geprüft

| Art | Inhalt | Beleg |
|---|---|---|
| **Bewiesen (gemessen)** | NVDA 2026.2 läuft als tragbare Kopie mit der Sprachausgabe „silence“ auf dem GitHub-Rechner. NVDA meldet selbst, dass kein Audiogerät da ist, läuft aber weiter. | `ergebnisse/lauf11_protokoll.txt`, Abschnitte 1 bis 3 und Protokollauszug am Ende |
| **Bewiesen (gemessen)** | Vorlesetexte der Schritte 1 bis 26 im Prototyp | `ergebnisse/lauf11_protokoll.txt`, Abschnitt 5 |
| **Bewiesen (gemessen)** | Gegenprobe: Der Windows-Editor und ein reines Flutter-Programm (Zähler-Vorlage, Flutter 3.44.8) werden vorgelesen | `ergebnisse/lauf10_protokoll.txt` und `lauf11_protokoll.txt`, Abschnitt 6 |
| **Bewiesen (gemessen)** | Ursache des Startfehlers „Error running app“ | `ergebnisse/lauf10_protokoll.txt` |
| **Nur gelesen (Quellen)** | NVDA-Startoptionen (`--create-portable-silent`, `--portable-path`, `-m`, `-c`, `-f`, `--log-level=12`, `--lang`, `--disable-addons`, `-k`, `-q`). Protokollstufe 12 schreibt die Sprachausgabe mit („Speaking …“). Sprachausgabe „silence“. Download-Adresse und Prüfsumme über dieselbe Update-Auskunft, die NVDA selbst nutzt. | NVDA-Benutzerhandbuch, Abschnitt „Command Line Options“; Quelltext `source/speech/speech.py` (`log.io("Speaking …")`), `source/synthDrivers/silence.py`, `source/updateCheck.py`, `source/config/configSpec.py` auf github.com/nvaccess/nvda |
| **Nicht geprüft** | Abschnitte 4.3 (Lesemodus, H-Taste), 4.4 (Testschalter aus), 4.5 (Karteikarte), 5 (richtiges Programm). Lauf 12 sollte 4.4 und 4.5 zusätzlich prüfen, ist aber beim Bauen gescheitert. | – |
| **Nicht geprüft** | Echte Stimme und Tonausgabe, andere NVDA-Versionen, Windows 10 und 11 als Arbeitsplatz-PC (der GitHub-Rechner ist Windows Server 2025) | – |

## NVDA-Download (Quelle, Version, Prüfsummen)

- **Quelle:** Update-Auskunft `api.nvaccess.org/nvdaUpdateCheck` von NV Access. Das ist dieselbe Stelle, die NVDA für die eigene Update-Prüfung nutzt.
- **Datei:** `https://download.nvaccess.org/releases/2026.2/nvda_2026.2.exe`, Version 2026.2, 64 530 776 Bytes.
- **SHA1:** `a5b01592f4e2355432848d3ad82f5bd214f25947`. Das stimmt mit dem Wert überein, den NV Access selbst angibt.
- **SHA256:** `f3f8d29974a88d687b3c4809be192219ec579c5bdabcda5aaf53635288bca824`
- **Digitale Signatur:** gültig, „CN=NV Access Limited, O=NV Access Limited, L=Camp Mountain, S=Queensland, C=AU“.
- **Weitere Werkzeuge:** keine. Es kamen keine Erweiterungen und keine Pakete aus anderen Quellen dazu. Tasten und Fokus laufen über Windows-Bordmittel (PowerShell, `user32.dll`, UI Automation).
- **Zugangsdaten:** Die Protokolle enthalten keine Zugangsschlüssel, Passwörter oder Daten von Nico.

## Antworten auf die Fragen

**Frage 1: Kann NVDA auf dem GitHub-Rechner portabel starten und die Sprachausgabe als Text mitschreiben?**
**Ja (bewiesen).** So läuft es:
1. Der Starter legt mit `--create-portable-silent --portable-path=…` eine tragbare Kopie an.
2. NVDA startet mit `-m --lang=de --log-level=12 -f nvda.log -c <Konfig> --disable-addons`.
3. In der Konfiguration ist `synth = silence` eingestellt.

Jede Ansage steht danach als Zeile „Speaking [...]“ im Protokoll. Ein Audiogerät braucht man nicht: NVDA warnt nur „Couldn't open … audio device“ und läuft weiter. Das Kennzeichen „Screenreader läuft“ (SPI) setzt NVDA selbst. Zusatzwerkzeuge wie die Erweiterung „Speech Logger“ waren nicht nötig.

**Frage 2: Tasten senden und mitschreiben, Schritte 1 bis 26.**
**Ja (bewiesen).** Die Tasten werden als Windows-Tastendrücke eingespeist. NVDA wertet auch eingespeiste Tasten aus, deshalb funktioniert sogar NVDA+Tab. Den Vergleich mit der Anleitung zeigt die Tabelle unten.

**Frage 3: Erscheint der Inhalt im UIA-Baum, solange NVDA läuft?**
**Teilweise.**
- **Gleiche Messart wie ohne NVDA:** Auch mit NVDA steht unter dem Fenster weiter nur „FLUTTERVIEW“ (1 Element). Das gilt beim Prototyp und beim reinen Flutter-Programm.
- **Andere Messart:** Man fragt zuerst das fokussierte Element ab und liest dann den rohen Baum ab „FLUTTERVIEW“. Damit erscheinen beim Prototyp 35 Elemente mit richtigen Namen und Rollen, zum Beispiel „Farben, eingeklappt“ (Schaltfläche) und „Testschalter …“ (Kontrollfeld, an). Auch der UIA-Fokus nennt bei jedem Tab-Schritt das richtige Element.
- **Schluss:** Die Inhalte sind über UI Automation erreichbar. Nur der Weg vom Fenster nach unten ist bei Flutter unterbrochen. Die frühere Messung „nur FLUTTERVIEW“ lag also an der Messart, nicht an fehlenden Inhalten.
- **Nicht geprüft:** ob die neue Messart auch ohne laufendes NVDA Inhalte zeigt.

**Frage 4: Liegt es an der Umgebung?**
**Nein (bewiesen).** Die Umgebung ist geeignet:
- Der Windows-Editor wird richtig vorgelesen („Untitled - Notepad“, „Text Editor, Eingabefeld, mehrzeilig, Leer“).
- Ein reines Flutter-Programm ebenfalls („Increment, Schalter“).
- Fehlender Bildschirm, fehlender Ton oder die Art der Sitzung verhindern das Vorlesen nicht.
- Die Fehlerseite in den Läufen 8 bis 10 war ein Fehler im Prototyp (siehe oben), keiner der Umgebung.

## Vergleich gemessen gegen erwartet (Lauf 11, Schritte 1 bis 26)

| Nr. | Erwartet (Anleitung) | NVDA hat gesagt | Bewertung |
|---|---|---|---|
| 1 | „FISI Screenreader-Prototyp“ | „FISI Screenreader-Prototyp“ | passt |
| 2 | „Optionen, Schalter“ | „Optionen, Schalter“ | passt |
| 3 | „Karteikarte, Schalter“ | „Karteikarte, Schalter“ | passt |
| 4 | „Testschalter: zusätzliche Ansagen, Umschalter, gedrückt“ | „Testschalter: zusätzliche Ansagen, Kontrollfeld, **Nicht ausgewählt**, aktiviert“ | **teilweise**: Rolle heißt „Kontrollfeld“ statt „Umschalter“. „Aktiviert“ bedeutet „an“ und stimmt. Das zusätzliche „Nicht ausgewählt“ kann verwirren. |
| 5 | „Nach Updates suchen, Schalter“ | gleich | passt |
| 6 | „Beim Start automatisch …, Umschalter, gedrückt“ | „…, Kontrollfeld, Nicht ausgewählt, aktiviert“ | **teilweise** (wie Schritt 4) |
| 7–10 | „…, eingeklappt, Schalter, reduziert“ | „Rundgang und Hilfe, eingeklappt, Schalter, eingeklappt“ (ebenso Schriftgröße, Farben, Tagesziel) | passt. NVDA sagt „eingeklappt“ statt „reduziert“. Der Zustand wird zweimal genannt (im Namen und als Zustand). |
| 11 | „Kopieren, Schalter“ | gleich | passt |
| 12 | „Leistungsmessung, eingeklappt …“ | gleich | passt |
| 13 | wieder „Optionen, Schalter“ | „FISI Screenreader-Prototyp“, dann „Optionen, Schalter“ | passt (Fenstertitel zusätzlich) |
| 14 | „Leistungsmessung, eingeklappt …“ | gleich | passt |
| — | (zwischen 7 und 12 nichts aus eingeklappten Bereichen) | Keine Einstellungen aus eingeklappten Bereichen | passt |
| 15 | „Farben ausgeklappt“ und/oder „erweitert“ | „Farben ausgeklappt, Benachrichtigung“, „Farben, ausgeklappt“, „ausgeklappt“ | **teilweise**: richtig, aber der Zustand wird **dreimal** genannt (Zusatzansage, Name, Zustand) |
| 16 | „Farben, ausgeklappt, Schalter, erweitert“ | „Farben, ausgeklappt, Schalter, hervorgehoben, ausgeklappt“ | passt |
| 17 | „Darstellung“, „Dunkel, Auswahlschalter, aktiviert“ | „Darstellung, Gruppierung“, „Dunkel, Auswahlschalter, aktiviert“ | passt |
| 18 | Pfeil runter: „Hell, Auswahlschalter …“ | Fokus blieb auf „Dunkel“, NVDA sagte nur „German (nicht unterstützt) D“ | **passt nicht**: Pfeiltasten wechseln die Auswahl nicht. Die Meldung „German (nicht unterstützt)“ kommt von der stummen Testsprachausgabe und ist bei echter Stimme nicht zu erwarten (nicht geprüft). |
| 19 | „Vorlagen, eingeklappt …“ | „Vorlagen, eingeklappt, Schalter, eingeklappt“ | passt |
| 20 | „Vorlagen ausgeklappt“ | wie 15, dreifach | **teilweise** (dreifach) |
| 21 | „Grundfarbe Cyan/Pink, Schalter, ausgewählt“ … | zuerst „**Gruppierung, Hintergrund**“, dann „Grundfarbe Cyan/Pink, Schalter, ausgewählt“, „Grundfarbe Lila/Magenta, Schalter“, „Grundfarbe Blau/Türkis, Schalter“ | **teilweise**: Die Gruppe heißt „Hintergrund“, obwohl zuerst die Grundfarben kommen. Das ist irreführend. |
| 22 | Meldung „Grundfarbe … setzt nur die Regler …“ | „Grundfarbe Blau/Türkis: setzt nur die Regler (Prototyp, nichts gespeichert). Benachrichtigung“ | passt |
| 23 | „Vorlagen eingeklappt“ | dreifach wie 15 | **teilweise** (dreifach) |
| 24 | Kacheln übersprungen, dann „Tagesziel …“ | „Tagesziel, eingeklappt, Schalter, eingeklappt“ | passt |
| 25 | „Farben eingeklappt“ | dreifach | **teilweise** (dreifach) |
| 26 | Meldung „Prototyp: Es wird nicht wirklich gesucht …“ | „Prototyp: Es wird nicht wirklich gesucht. Installierte Version 0.58.1. Benachrichtigung“ | passt |

**Zusammengefasst:**
- 26 Schritte, davon **18 passend**, **7 teilweise** und **1 passt nicht**.
- Die Kopfzeilen, die Tab-Reihenfolge, das Überspringen eingeklappter Inhalte und die Meldungen funktionieren.
- **Verbesserungsstellen im Prototyp (noch nicht geändert):**
  - Klappzustand wird dreifach genannt. Wahrscheinlich reicht es, die Zusatzansage oder das Wort im Namen wegzulassen. Klären soll das Abschnitt 4.4.
  - Schalter heißen „Kontrollfeld, nicht ausgewählt“.
  - Pfeiltasten in der Gruppe „Darstellung“ wirken nicht.
  - Die Gruppe der Vorlagen-Kacheln heißt „Hintergrund“.

## Weitere Befunde

- **Bau von Lauf 12 gescheitert, nicht durch eigene Änderung:**
  - **Fehlermeldung:** `jni_flutter-1.0.4+1 … Constant evaluation error` beim Windows-Bau mit Flet 1.0.1.
  - **Ursache (Vermutung):** Zwischen Lauf 11 (09:2x Uhr) und Lauf 12 (09:4x Uhr) wurde offenbar eine neue Version einer Flutter-Abhängigkeit veröffentlicht. Geändert hatte sich nur das Mess-Skript.
  - **Mögliches Risiko für 0.59 (nicht geprüft):** Falls der Handy-Bau (`flet build apk`) dieselbe Abhängigkeit zieht, könnte er ebenfalls scheitern. Ich habe daran nichts geändert. Das wäre vor dem 0.59-Release zu prüfen.
- **UIA-Messart:** Für spätere Messungen ist „ab dem fokussierten Element“ die richtige Messart bei Flutter-Programmen (siehe Frage 3).

## Empfehlung: Was Nico selbst prüfen sollte

1. **ZIP aus Lauf 11** laden (Link oben) und starten. Die Optionen-Seite muss erscheinen, nicht „Error running app“.
2. Mit NVDA (echte Stimme) **Schritte 1 bis 26** grob nachhören. Die erwarteten Texte in der Anleitung sind jetzt die gemessenen. Besonders achten auf:
   - Schritt 15/20: Ist die dreifache Ansage störend?
   - Schritt 18: Wechselt die Auswahl mit den Pfeiltasten?
3. **Abschnitte 4.3, 4.4 und 4.5** (Lesemodus mit H, Testschalter aus, Karteikarte). Die wurden automatisch noch nicht geprüft.
4. Danach entscheiden, ob die vier Verbesserungsstellen im Prototyp angepasst werden sollen. Das wäre eine kleine Änderung auf diesem Zweig.

Eine weitere Automatik (4.4 und 4.5) wäre möglich, sobald der Windows-Bau wieder durchläuft. Ich habe sie nach dem gescheiterten Lauf 12 bewusst nicht weiterverfolgt, weil das Ziel der Erkundung (Fragen 1 bis 4, Abschnitte 4.1 und 4.2) erreicht ist.

## Dateien

- `nvda_lauf.ps1`: der Ablauf (NVDA holen und prüfen, tragbare Kopie, Start, Tasten, Mitschrift, UIA, Gegenprobe)
- `ergebnisse/lauf8_protokoll.txt`: erster Lauf, NVDA läuft, Prototyp zeigt die Fehlerseite
- `ergebnisse/lauf10_protokoll.txt`: Ursache des Startfehlers (console.log), Gegenprobe Editor und Flutter
- `ergebnisse/lauf11_protokoll.txt`: Prototyp läuft, Schritte 1 bis 26, UIA-Baum ab Fokus (35 Elemente)
- Ablauf in `.github/workflows/prototyp-screenreader.yml` (nur Zweig `proto-screenreader`). Die alten UIA-Messschritte sind abgeschaltet (`if: false`).

## Änderungen am Prototyp (mit Begründung)

- **Startfehler werden protokolliert:** Fehler beim Start landen in `%TEMP%\fisi_prototyp_fehler.txt`. Grund: Fehlersuche auf dem GitHub-Rechner.
- **Karteikarten über `fisi_core.CONTENT_DIR` laden:** Grund: Startfehler „Error running app“ im gebauten Programm.
- **Sonst nichts:** Namen, Ansagen und Aufbau sind unverändert.
