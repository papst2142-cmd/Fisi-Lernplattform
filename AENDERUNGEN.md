# Änderungen

Neueste Version oben. Jede Version bekommt vor dem Release einen eigenen
Abschnitt `## <Version>` – dieser Text erscheint im GitHub-Release und im
Update-Fenster des Programms.

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
