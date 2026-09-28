# Änderungen

Neueste Version oben. Jede Version bekommt vor dem Release einen eigenen
Abschnitt `## <Version>` – dieser Text erscheint im GitHub-Release und im
Update-Fenster des Programms.

## 0.25

- **Viel mehr Lernstoff:** 916 statt 368 Aufgaben – 316 Karteikarten,
  521 Quizfragen, 30 AP1-Szenarien, 37 AP2-Szenarien und 12 Testprojekte,
  verteilt auf alle vier Fachbereiche und alle Themenblöcke. Darunter 64 neue
  Rechenaufgaben (Zahlensysteme, Subnetting, RAID, Verfügbarkeit,
  Übertragungsdauer, Umsatzsteuer, Kalkulation, Abschreibung) mit Rechenweg.
- **Szenarien und Testprojekte mit Suche, Filter und Seiten:** Die Listen
  lassen sich nach Titel oder Nummer durchsuchen und nach Thema,
  Fachbereich, Schwierigkeit und Status (offen/bearbeitet) filtern.
  Bearbeitete Aufgaben tragen einen Haken. „Nächstes Szenario“ bleibt
  innerhalb der gewählten Auswahl. Gilt für PC und Handy.
- **Stabiler bei großen Datenmengen:** Die Listen zeigen seitenweise
  höchstens 15 Einträge. Vorher konnte das Programm bei sehr vielen
  Szenarien beim Start abstürzen. Ein neuer Belastungstest
  (`test_grosse_datenmengen.py`) prüft das Programm mit über 7.000 Aufgaben.

## 0.24

- **Neu: Handy-App für Android** mit allen Bereichen der PC-Version –
  Dashboard, Karteikarten, Prüfungstrainer, AP1-/AP2-Szenarien,
  Testprojekte, Praxis-Rechner, Lernfortschritt, Suche und Einstellungen.
  Gleiche Inhalte, gleiches Design, für Touch-Bedienung gebaut. Die Datei
  `FISI-Lernplattform-0.24-Android.apk` liegt im Release.
- **Abgleich PC und Handy:** Der Lernstand kann automatisch über ein
  privates GitHub-Repository abgeglichen werden – beim Start, kurz nach dem
  Lernen und beim Beenden. Einrichtung unter Einstellungen → „Abgleich PC
  und Handy“ (Anleitung in LIESMICH.txt).
- Die Handy-App sucht selbst nach Updates und lädt die neue Version über
  den Browser.

## 0.23

- **Deutlich mehr Lernstoff:** 115 Karteikarten (vorher 67), 208 Quizfragen
  (vorher 148), 22 AP2-Szenarien (vorher 16), 15 AP1-Szenarien (vorher 10)
  und 8 Testprojekte (vorher 6) - verteilt auf alle vier Fachbereiche.
- Neu u.a.: IPv6, VLSM, WLAN mit 802.1X, strukturierte Verkabelung,
  Kryptografie-Grundlagen, DSGVO-Betroffenenrechte, ITIL, Linux- und
  Windows-Befehle, Cloud-Modelle sowie Rechenaufgaben zu Subnetting, RAID,
  Rabatt/Skonto, Break-Even, Amortisation und Abschreibung.
- Neue Szenarien: VLSM-Adressplan, IPv6-Adressplan, Unternehmens-WLAN,
  strukturierte Verkabelung, Nutzwertanalyse, Backupkonzept mit
  Berechnung; AP1: Speichergrößen, Netzwerkkomponenten, Schutzbedarf,
  Projektziele (SMART), Angebotsvergleich.
- Zwei doppelt vorhandene RAID-Fragen im Prüfungstrainer entfernt.

## 0.22

- **Automatische Updates:** Das Programm sucht beim Start nach einer neuen
  Version und bietet sie zur Installation an. Unter Windows wird das Update
  mit einem Klick installiert und das Programm startet danach neu.
- In den Einstellungen gibt es den Knopf „Nach Updates suchen“; die
  automatische Suche beim Start lässt sich dort abschalten.
- Aufgeräumt: Die alten Starter für den Start aus dem Quellcode wurden
  entfernt – die Installer ersetzen sie.

## 0.21

- Linux: DEB-Paket und AppImage starten wieder (in 0.20 fehlte ein Modul).
- Jeder Build wird jetzt automatisch getestet: Das fertige Programm öffnet
  einmal jede Ansicht, bevor es veröffentlicht wird.

## 0.20

- Neue, moderne Oberfläche mit CustomTkinter: abgerundete Kacheln,
  Farbverläufe, neu gestaltetes Dashboard.
- Installer für Windows, Linux (DEB und AppImage) und macOS (Apple-Chip
  und Intel).
- Dashboard: AP2-Szenarien zu Virtualisierung und Projektmanagement zählen
  jetzt zum passenden Themenblock.
