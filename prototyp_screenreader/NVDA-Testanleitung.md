# Testanleitung: FISI Screenreader-Prototyp mit NVDA

Vielen Dank, dass du hilfst! Diese Anleitung ist für jemanden geschrieben, der NVDA kennt. Programmierwissen brauchst du nicht.

**Worum geht es?** Die „FISI Lernplattform“ ist ein Lernprogramm für die Ausbildung zum Fachinformatiker. Wir wollen wissen, ob man es mit einem Screenreader bedienen kann. Dafür gibt es ein kleines **Testprogramm (Prototyp)**. Es zeigt nur zwei Seiten: die **Optionen** und eine **Karteikarte**. Es speichert nichts und verändert nichts auf deinem PC. Die Knöpfe tun im Prototyp absichtlich nichts außer einer kurzen Meldung.

Zum Vergleich kannst du auch kurz das **richtige Programm** öffnen (Schritt 5). Dort erwarten wir, dass NVDA fast nichts vorliest. Das ist bekannt und kein Fehler von dir.

Dauer: etwa 30 bis 45 Minuten.

---

## 1. Was du brauchst

- Einen Windows-PC mit Windows 10 oder 11.
- **NVDA** (kostenlos). Falls noch nicht installiert: auf **nvaccess.org** unter „Download“ herunterladen und installieren. Jede aktuelle Version passt.
- Die Datei **FISI-Screenreader-Prototyp-Windows.zip** (bekommst du von Nico).
- Für den Vergleich (freiwillig): das richtige Programm „FISI Lernplattform“, falls Nico es dir gibt.

## 2. Prototyp starten

1. Die ZIP-Datei mit Rechtsklick → **„Alle extrahieren…“** entpacken, zum Beispiel auf den Desktop.
2. Im entpackten Ordner die Datei mit der Endung **.exe** starten (Name ähnlich „fisi-screenreader-prototyp.exe“ oder „FISI Screenreader-Prototyp.exe“).
3. Falls Windows meldet **„Der Computer wurde durch Windows geschützt“**: auf **„Weitere Informationen“** und dann **„Trotzdem ausführen“**. Das Testprogramm ist nicht signiert, deshalb kommt diese Warnung. Meldet ein Virenschutz etwas, bitte nichts freigeben, sondern es Nico sagen.
4. Es öffnet sich ein Fenster mit dem Titel **„FISI Screenreader-Prototyp“**.

**Tipp:** Falls NVDA beim Start nichts sagt, einmal mit **Alt+Tab** weg und wieder zurück ins Fenster wechseln.

## 3. Wichtige Begriffe

- **Klappbereich:** Eine Überschrift, die man auf- und zuklappen kann (wie ein Akkordeon). Darunter liegen Einstellungen, die man erst nach dem Aufklappen sieht.
- **Erwarteter Vorlesetext:** Was NVDA ungefähr sagen sollte. Die genauen Wörter hängen von der NVDA-Version ab (zum Beispiel „Schalter“ oder „Schaltfläche“). Wichtig ist, dass der **Sinn** stimmt.
- **Testschalter: zusätzliche Ansagen:** Ganz oben im Prototyp. Er steuert, ob das Programm beim Auf- und Zuklappen und bei Meldungen **zusätzlich** etwas ansagen lässt. Wir wollen wissen, ob NVDA das braucht oder ob es dann doppelt spricht (Schritt 4.4).

## 4. Test im Prototyp

Bitte in der Spalte **Ergebnis** eintragen: **passt**, **passt nicht** oder **teilweise**, und bei Bedarf eine Anmerkung (was NVDA wirklich gesagt hat).

### 4.1 Seite Optionen mit der Tab-Taste durchgehen

Nach dem Start mit **Tab** Schritt für Schritt vorwärts gehen.

| Nr. | Aktion | Erwarteter Vorlesetext (ungefähr) | Ergebnis | Anmerkung |
|---|---|---|---|---|
| 1 | Programm ist gestartet | „FISI Screenreader-Prototyp“ (Fenstertitel) | | |
| 2 | Tab | „Optionen, Schalter“ | | |
| 3 | Tab | „Karteikarte, Schalter“ | | |
| 4 | Tab | „Testschalter: zusätzliche Ansagen, Umschalter, gedrückt“ (oder „eingeschaltet“) | | |
| 5 | Tab | „Nach Updates suchen, Schalter“ | | |
| 6 | Tab | „Beim Start automatisch nach Updates suchen, Umschalter, gedrückt“ (oder „eingeschaltet“) | | |
| 7 | Tab | „Rundgang und Hilfe, eingeklappt, Schalter, reduziert“ | | |
| 8 | Tab | „Schriftgröße, eingeklappt, Schalter, reduziert“ | | |
| 9 | Tab | „Farben, eingeklappt, Schalter, reduziert“ | | |
| 10 | Tab | „Tagesziel, eingeklappt, Schalter, reduziert“ | | |
| 11 | Tab | „Kopieren, Schalter“ (gehört zu „Problem melden“) | | |
| 12 | Tab | „Leistungsmessung, eingeklappt, Schalter, reduziert“ | | |
| 13 | Tab | wieder „Optionen, Schalter“ (Runde beendet) | | |
| 14 | Umschalt+Tab | geht einen Schritt zurück: „Leistungsmessung, eingeklappt …“ | | |

**Wichtig:** Zwischen Schritt 7 und 12 dürfen **keine** Einstellungen aus den eingeklappten Bereichen kommen. Nur die Kopfzeilen der Bereiche.

### 4.2 Einen Bereich auf- und zuklappen

| Nr. | Aktion | Erwarteter Vorlesetext (ungefähr) | Ergebnis | Anmerkung |
|---|---|---|---|---|
| 15 | Mit Tab zu „Farben, eingeklappt“ gehen, dann **Enter** | „Farben ausgeklappt“ und/oder „erweitert“ | | |
| 16 | **NVDA+Tab** (aktuelles Element neu vorlesen) | „Farben, ausgeklappt, Schalter, erweitert“ | | |
| 17 | Tab | „Darstellung“ und „Dunkel, Auswahlschalter, aktiviert, 1 von 2“ (oder ähnlich) | | |
| 18 | **Pfeil nach unten** | „Hell, Auswahlschalter …“ (Auswahl wechselt, es wird nichts gespeichert) | | |
| 19 | Tab | „Vorlagen, eingeklappt, Schalter, reduziert“ | | |
| 20 | **Leertaste** | „Vorlagen ausgeklappt“ und/oder „erweitert“ | | |
| 21 | Tab (mehrmals) | „Grundfarbe Cyan/Pink, Schalter, ausgewählt“, dann „Grundfarbe Lila/Magenta, Schalter“ usw., danach „Hintergrund Violett …“ | | |
| 22 | Auf einer Kachel **Enter** | Meldung „Grundfarbe … setzt nur die Regler (Prototyp, nichts gespeichert)“ | | |
| 23 | Mit **Umschalt+Tab** zurück zu „Vorlagen, ausgeklappt“, dann **Enter** | „Vorlagen eingeklappt“ und/oder „reduziert“ | | |
| 24 | Tab | Die Kacheln werden übersprungen, als Nächstes kommt „Tagesziel, eingeklappt …“ | | |
| 25 | Zurück zu „Farben, ausgeklappt“ und **Enter** | „Farben eingeklappt“ und/oder „reduziert“ | | |
| 26 | Auf „Nach Updates suchen“ **Enter** | Meldung „Prototyp: Es wird nicht wirklich gesucht. Installierte Version 0.58.1.“ | | |

### 4.3 Lesemodus und Überschriften

Hier geht es darum, ob man die Seite auch **ohne Tab** lesen kann.

| Nr. | Aktion | Erwarteter Vorlesetext (ungefähr) | Ergebnis | Anmerkung |
|---|---|---|---|---|
| 27 | **NVDA+Leertaste** (Lese- bzw. Fokusmodus umschalten), falls nötig. Dann **H** | Springt zu Überschriften: „Optionen, Überschrift Ebene 1“, dann „Updates, Überschrift Ebene 2“, „Problem melden, Überschrift Ebene 2“ | | |
| 28 | Mit **Pfeil nach unten** durch die Seite lesen | Alle sichtbaren Texte in sinnvoller Reihenfolge, auch der lange Hilfetext bei „Problem melden“ | | |
| 29 | **NVDA+T** (Fenstertitel) | „FISI Screenreader-Prototyp“ | | |

Hinweis: Ob es bei diesem Programmtyp überhaupt einen Lesemodus gibt, wissen wir nicht sicher. Wenn H nichts tut, bitte einfach „passt nicht, kein Lesemodus“ eintragen.

### 4.4 Testschalter: mit und ohne zusätzliche Ansagen

| Nr. | Aktion | Erwartung | Ergebnis | Anmerkung |
|---|---|---|---|---|
| 30 | Testschalter ist **an** (Start). Einen Bereich mit Enter auf- und zuklappen | NVDA sagt den neuen Zustand **genau einmal**. Wird doppelt gesprochen? Bitte notieren. | | |
| 31 | Mit Tab zum Testschalter, **Leertaste** (jetzt aus). Wieder einen Bereich auf- und zuklappen | Sagt NVDA trotzdem, dass sich der Zustand geändert hat? Oder gar nichts? | | |
| 32 | Mit Testschalter **aus**: auf „Nach Updates suchen“ Enter | Wird die Meldung trotzdem vorgelesen? | | |

Danach den Testschalter bitte wieder **an**schalten.

### 4.5 Seite Karteikarte

| Nr. | Aktion | Erwarteter Vorlesetext (ungefähr) | Ergebnis | Anmerkung |
|---|---|---|---|---|
| 33 | Ganz oben „Karteikarte“ mit Enter wählen | Seite wechselt. | | |
| 34 | Tab bis „Antwort zeigen, Schalter“ | „Antwort zeigen, Schalter“ | | |
| 35 | Lesemodus oder Pfeiltasten: Frage lesen | „Karte 1 von 5“ und die Frage „Was ist der Standard-Port für HTTPS?“ (als Überschrift) | | |
| 36 | Auf „Antwort zeigen“ **Enter** | Die Antwort wird vorgelesen („Antwort: TCP Port 443 …“), danach steht der Fokus auf „Gewusst, Schalter“ | | |
| 37 | Tab | „Nicht gewusst, Schalter“ | | |
| 38 | Auf „Gewusst“ oder „Nicht gewusst“ **Enter** | Nächste Karte, Fokus wieder auf „Antwort zeigen“. „Karte 2 von 5“ ist lesbar. | | |

### 4.6 Allgemeiner Eindruck (Prototyp)

| Nr. | Frage | Antwort |
|---|---|---|
| 39 | Konntest du jederzeit hören, **wo** du bist? | |
| 40 | Gab es Stellen, an denen NVDA **nichts** gesagt hat? Welche? | |
| 41 | Gab es Stellen, an denen NVDA **zu viel** oder doppelt gesprochen hat? | |
| 42 | Ist die Wortwahl verständlich („eingeklappt/ausgeklappt“, „aufklappen/einklappen“)? Bessere Vorschläge? | |

## 5. Vergleich mit dem richtigen Programm (freiwillig, etwa 5 Minuten)

Nur wenn du das Programm „FISI Lernplattform“ hast.

| Nr. | Aktion | Was wir erwarten | Ergebnis | Anmerkung |
|---|---|---|---|---|
| 43 | Programm starten | NVDA sagt den Fenstertitel („FISI Lernplattform …“) | | |
| 44 | Mehrmals Tab | Sichtbar springt eine Markierung weiter, aber NVDA sagt **wenig oder nichts** (höchstens bei Eingabefeldern) | | |
| 45 | **NVDA+Pfeil nach unten** oder Objektnavigation | Wir erwarten: kaum lesbarer Inhalt | | |

Bitte das Programm danach normal schließen. Es verändert dabei nichts.

## 6. Rückmeldung an Nico

Bitte diese Angaben ausfüllen und zusammen mit den ausgefüllten Tabellen schicken (als Datei, Foto oder abgetippt):

```
Datum des Tests:
Windows-Version (Start → Einstellungen → System → Info, z. B. "Windows 11 24H2"):
NVDA-Version (NVDA-Menü → Hilfe → Über NVDA, z. B. "2026.2"):
Sprachausgabe/Stimme (z. B. "eSpeak NG", "OneCore Deutsch"):
Ausführliche Rollenansage an/aus (falls bekannt):
Bildschirm: Laptop / Monitor, Skalierung (z. B. 125 %):

Gesamteindruck Prototyp (1 = gar nicht bedienbar, 5 = gut bedienbar):
Gesamteindruck richtiges Programm (1-5, falls getestet):

Was hat gut funktioniert?

Was hat gestört?

Sonstige Anmerkungen:
```

Vielen Dank!
