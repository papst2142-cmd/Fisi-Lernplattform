# Untersuchung Linux-Erststart und .deb (Stand v0.59, 06.10.2026)

Nur Untersuchung. Nichts am Programm, an Daten, Spielwerten, Abgleich oder Update-Ablauf geändert. Wegwerf-Zweig `untersuchung-linux-deb` (von `main` 20ffa32), kein PR, kein Tag, kein Release.

Kennzeichnung: **belegt** = selbst gemessen oder ausprobiert (Ausgabe liegt unter `messung/`), **gelesen** = in Quelltext oder Dokumentation nachgelesen (Quelle genannt), **vermutet** = Schlussfolgerung ohne Nachweis, **nicht geprüft** = ohne echte Ubuntu-Desktop-Sitzung nicht prüfbar.

Prüfumgebung: Docker-Container `ubuntu:26.04` (26.04.1 LTS, dpkg 1.23.7ubuntu1) ohne grafischen Desktop, dazu Xvfb. Ein echtes GNOME und das echte App Center gab es hier nicht.

---

## Kurzbericht (Pflichtteil)

### 1. Ursache des fehlenden Menüeintrags: **nicht belegt**, ein starker Verdacht

- **belegt:** Das .deb von 0.59 enthält einen gültigen Menüeintrag `/usr/share/applications/fisi-lernplattform.desktop`. `desktop-file-validate` meldet keinen Fehler, `Exec=fisi-lernplattform` zeigt über `/usr/bin/fisi-lernplattform` auf die ausführbare Datei `/opt/fisi-lernplattform/FISI-Lernplattform`, das Symbol wird gefunden. GLib (dieselbe Bibliothek, mit der GNOME die Einträge liest) listet den Eintrag als sichtbar und findet ihn bei der Suche nach „fisi“. Dieser Eintrag ist seit 0.20 in **allen** Paketen Byte für Byte gleich. Der frühere Stand „das .deb hat schon einen Menüeintrag“ stimmt also.
- **belegt (Gegenprobe im Container):** Liegt im Benutzerordner eine Datei mit **demselben Namen** `~/.local/share/applications/fisi-lernplattform.desktop`, deren Programm nicht mehr existiert, verschwindet der richtige Eintrag aus der Liste der sichtbaren Programme. Grund: Die Datei im Benutzerordner hat Vorrang vor `/usr/share/applications` (freedesktop.org, Desktop Entry Specification, „Desktop File ID“, und XDG Base Directory Specification: `$XDG_DATA_HOME` geht vor `$XDG_DATA_DIRS`).
- **gelesen:** Genau so eine Datei hat das alte Skript `install_linux.sh` angelegt (im Repository vom Basisstand 24.09.2026 bis zum Aufräumen am 27.09.2026, Commit aa94cc1). Es schrieb `~/.local/share/applications/fisi-lernplattform.desktop` mit `Exec=~/.local/bin/fisi-lernplattform`. Das heutige Programm selbst schreibt dort nichts hin; die Desktop-Verknüpfung von 0.59 landet nur auf dem Schreibtisch (`fisi_verknuepfung.py`).
- **vermutet:** Auf Nicos VM liegt noch eine solche alte Benutzerdatei (etwa aus einer frühen Quellcode-Installation), deren Programm beim „Entfernen über Terminal“ gelöscht wurde. Das würde genau Nicos Bild erklären. Eine zweite, harmlosere Möglichkeit: GNOME hängt neue Programme hinten an die letzte Seite der Programmübersicht an, statt sie alphabetisch einzusortieren (vermutet, nicht geprüft).
- **nicht geprüft:** Nicos VM selbst. Die Prüfbefehle stehen unten in Punkt 5.

### 2. Ursache des Aktualisierungsproblems: **gelesen**, im echten App Center nicht geprüft

- **gelesen** (Quelltext App Center, github.com/ubuntu/app-center, Stand 05.10.2026, Datei `packages/app_center/lib/deb/local_deb_model.dart` und `local_deb_page.dart`): Beim Öffnen einer lokalen .deb fragt das App Center PackageKit nur, **ob ein Paket mit diesem Namen installiert ist**. Die Versionsnummern vergleicht es nicht. Ist `fisi-lernplattform` in irgendeiner Version installiert, zeigt der Knopf „Installiert“ und ist ausgegraut. Einen Knopf „Aktualisieren“ für lokale .deb-Dateien gibt es dort nicht. Deshalb musste Nico die alte Version erst entfernen.
- **belegt:** Am Paket liegt es nicht. `sudo apt install ./fisi-lernplattform_0.59_amd64.deb` und `sudo dpkg -i …` über 0.58.1 laufen fehlerfrei durch („Unpacking fisi-lernplattform (0.59) over (0.58.1)“, Rückgabewert 0), ohne Konflikte und ohne übrig gebliebene Dateien. Die Versionsreihenfolge ist für Debian richtig (`0.58 < 0.58.1 < 0.59 < 0.59.1 < 0.60` jeweils wahr).

### 3. Warnhinweis: **bei Doppelklick unvermeidlich** (gelesen)

- **gelesen** (gleicher Quelltext): Das App Center zeigt bei **jeder** lokal geöffneten .deb immer das Banner „Möglicherweise unsicher – Dieses Paket wird von einem Drittanbieter bereitgestellt …“ und vor der Installation zusätzlich die Rückfrage „Sind Sie sicher, dass Sie es installieren möchten?“. Es gibt keine Bedingung dafür: Signatur, AppStream-Daten oder Paketinhalt ändern daran nichts.
- **Folge:** Mildern lässt sich der Hinweis nur, indem Anwender den Doppelklick-Weg nicht nehmen: entweder die Ein-Zeilen-Installation im Terminal (kein Hinweis, aber Terminal) oder später eine eigene Paketquelle, ein Snap oder ein Flatpak (siehe 4b). Die Passwortabfrage bleibt bei jeder .deb-Installation, weil Systemdateien geschrieben werden.

### 4. Empfehlung in zwei Stufen

**(a) Klein und sicher, passt in 0.59.1**

| Nr. | Was | Nutzen | Aufwand | Risiko |
|---|---|---|---|---|
| a1 | **Release-Text** bekommt einen Linux-Absatz: Installation und Update mit einer Zeile `sudo apt install ./fisi-lernplattform_<Version>_amd64.deb`; Hinweis, dass das App Center nur die Erstinstallation kann und die Warnung dort bei jeder fremden .deb kommt. In `LIESMICH.txt` steht die Zeile schon (Zeile 102 f.), im Release-Text fehlt sie (belegt). | hoch | sehr klein (Text) | keins |
| a2 | **Symbole in mehreren Größen** (48, 64, 128, 256 und 512 px) statt nur 512 px. Die Icon Theme Specification verlangt mindestens 48×48 (gelesen). Gefunden wird das Symbol heute trotzdem (belegt), es wird nur herunterskaliert. | mittel | klein (build.py) | sehr gering |
| a3 | **Fensterklasse festlegen:** Das laufende Fenster meldet sich als `WM_CLASS = "tk", "Tk"` (belegt). Dazu passt kein Menüeintrag, GNOME kann Fenster und Eintrag deshalb vermutlich nicht verbinden (eigenes Symbol im Dock, „An Dash anheften“ unzuverlässig; vermutet, auf GNOME nicht geprüft). Abhilfe: `className="fisi-lernplattform"` beim Erzeugen des Hauptfensters plus `StartupWMClass=fisi-lernplattform` in der .desktop-Datei. | mittel | klein | gering (Programmänderung, deshalb nur nach Freigabe) |
| a4 | **Abhängigkeiten eintragen:** `Depends:` ist leer (belegt). Im schlanken Container fehlten `libXft.so.2` und `libXss.so.1` (belegt); auf einem normalen Ubuntu-Desktop sind sie vorhanden. Eintrag `Depends: libxft2, libxss1` macht das Paket sauberer, ändert für Nico nichts Sichtbares. | gering | sehr klein | gering |
| a5 | **Update-Fenster nicht mehr fest 560×500** (siehe F): Höhe aus dem Inhalt berechnen oder mit der Schriftgröße mitwachsen lassen und `resizable` erlauben. | hoch bei großer Schrift | klein | gering (Programmänderung, nur nach Freigabe) |
| a6 | Erst **nach Nicos Prüfung (Punkt 5)**: Liegt bei ihm tatsächlich eine alte Benutzerdatei, kann das Programm beim Start unter Linux eine verwaiste `~/.local/share/applications/fisi-lernplattform.desktop` erkennen und anbieten, sie zu entfernen. | mittel | klein bis mittel | gering, löscht nur nach Rückfrage |

Keine Maintainer-Skripte nötig: Desktop-Datenbank und Symbol-Zwischenspeicher werden schon heute von den dpkg-Triggern der Pakete `desktop-file-utils` und `hicolor-icon-theme` aktualisiert (belegt: „Processing triggers for …“ bei jeder Installation und Entfernung). Eine AppStream-Datei (`/usr/share/metainfo/…`) bringt für die lokale .deb im App Center nichts, weil diese Seite nur die Paketdaten über PackageKit liest (gelesen).

**(b) Größer, gehört in die Planung 0.61 (Verteilung)**

| Weg | Nutzen für Anwender | Aufwand | Laufende Pflege | Risiko |
|---|---|---|---|---|
| **Signierte apt-Paketquelle** (z. B. auf GitHub Pages) | Updates kommen über die normale Aktualisierungsverwaltung, kein Warnhinweis mehr bei Updates. Einmalig muss die Quelle eingerichtet werden (Terminal oder ein kleines Einrichtungspaket, das Schlüssel und Quelle ablegt). | mittel: Repository-Struktur (Release, Packages, InRelease), GPG-Schlüssel, Schritt im Release-Workflow | mittel: Schlüssel sicher verwahren und verlängern, jede Version veröffentlichen | Schlüssel-Verlust oder -Diebstahl wäre ernst; Fehler im Repository blockieren `apt update` bei Anwendern |
| **Snap** (Snap Store) | Im App Center ohne Warnung, Updates automatisch; auf Ubuntu der „eingebaute“ Weg | mittel bis hoch: snapcraft.yaml, Tk/Schriften im Snap, Test der Einschränkungen (strict confinement) | mittel | eigener Update-Ablauf muss im Snap abgeschaltet werden; Prüfung durch den Store (Kenntnisstand, nicht geprüft) |
| **Flatpak** (Flathub) | Läuft auf fast allen Linux-Systemen, Updates über die Softwareverwaltung | hoch: Flathub verlangt Bau aus dem Quelltext, keine fertigen Binärdateien im Antrag, AppStream-Metainfo ist Pflicht (gelesen, docs.flathub.org „Requirements“); PyInstaller-Paket fällt damit weg | mittel bis hoch (Manifest, Python-Abhängigkeiten pflegen) | eigener Update-Ablauf muss abgeschaltet werden, weil das Programm im Flatpak nicht in sein eigenes Verzeichnis schreiben kann (vermutet); Review kann dauern |
| **Installationsskript** `install.sh` | eine Zeile im Terminal lädt, prüft (SHA-256) und installiert | klein | klein | „Skript aus dem Netz mit sudo ausführen“ ist genau das Muster, vor dem man Anwender warnen sollte; bringt gegenüber der apt-Zeile kaum Vorteil. **Nicht empfohlen.** |
| **Nur Anleitung** (a1) | sofort, kein Warnhinweis bei Terminal-Weg | sehr klein | keine | keins, aber weiter Terminal nötig |

Meine Einschätzung (vermutet): Für 0.61 lohnt sich zuerst die **signierte apt-Paketquelle** (passt zum vorhandenen .deb und zum Release-Workflow). Snap ist auf Ubuntu der bequemste Weg für Anwender, kostet aber mehr Umbau. Flatpak/Flathub ist wegen „Bau aus dem Quelltext“ der aufwendigste.

### 5. Was Nico noch prüfen muss (auf der echten VM)

Im Terminal, ohne `sudo`, nur lesen:

```
ls -la ~/.local/share/applications/ | grep -i fisi
cat ~/.local/share/applications/fisi-lernplattform.desktop
ls -la /usr/share/applications/fisi-lernplattform.desktop
dpkg -l fisi-lernplattform
ls ~/.local/bin/ | grep -i fisi
```

1. Gibt der erste Befehl eine Datei aus, ist das sehr wahrscheinlich die Ursache (Punkt 1). Bitte den Inhalt (zweiter Befehl) schicken, **nichts löschen**, bis wir es besprochen haben.
2. In der Programmübersicht (Super-Taste) **„fisi“ eintippen**: Erscheint das Programm in der Suche? Und erscheint es ganz hinten auf der letzten Seite der Programmübersicht?
3. Läuft das Programm: Welches Symbol zeigt das Dock links? Das eigene oder ein allgemeines? (Prüft a3.)
4. Update-Fenster: Welche **Schriftgröße** ist in den Optionen eingestellt (Normal, Groß, Sehr groß)? Und ist in Ubuntu unter Einstellungen › Barrierefreiheit „Große Schrift“ an oder eine Bildschirmskalierung über 100 % eingestellt? Am besten ein Foto des Fensters.
5. Nur zur Bestätigung von Punkt 2: Öffnet Nico das 0.59-Paket per Doppelklick, während 0.59 schon installiert ist, sollte der Knopf „Installiert“ grau sein. Erwartet wird dasselbe bei installierter 0.58.1.

---

## Ausführlich zu den Fragen A bis F

### A. Inhalt des .deb 0.59 (aus dem veröffentlichten Release) – belegt

Datei von der Release-Seite geladen, SHA-256 `fdf779ac…5cfa` stimmt mit der Prüfsumme im Release-Text überein.

| Feld | Wert |
|---|---|
| Package | fisi-lernplattform |
| Version | 0.59 |
| Architecture | amd64 |
| Section / Priority | education / optional |
| Installed-Size | 93696 KiB |
| Maintainer | FISI Lernplattform Projekt (noreply-Adresse) |
| Depends, Recommends, Conflicts, Replaces, Provides | **keine** |
| Maintainer-Skripte (postinst, prerm …) | **keine**, das Steuerarchiv enthält nur `control` |

Dateien (516 Einträge, vollständig in `messung/paket_0.59.txt`): alles unter `/opt/fisi-lernplattform/` (Programm `FISI-Lernplattform` mit 755, Bibliotheken in `_internal/`), dazu
- `/usr/bin/fisi-lernplattform` → Verweis auf `/opt/fisi-lernplattform/FISI-Lernplattform`
- `/usr/share/applications/fisi-lernplattform.desktop` (644, 273 Byte)
- `/usr/share/icons/hicolor/512x512/apps/fisi-lernplattform.png` (644, 512×512 PNG)

Alle Dateien gehören root:root. Auffällig, aber unkritisch: Auch reine Datendateien in `_internal/` (z. B. `*.tcl`, `*.enc`) haben das Ausführrecht 755.

### B. Menüeintrag

1. **belegt:** Inhalt der .desktop-Datei:
   ```
   [Desktop Entry]
   Type=Application
   Name=FISI Lernplattform
   Comment=Lernprogramm fuer die Umschulung zum Fachinformatiker Systemintegration
   Exec=fisi-lernplattform
   Icon=fisi-lernplattform
   Terminal=false
   Categories=Education;
   Keywords=FISI;IHK;Lernen;Netzwerk;Subnetting;RAID;
   ```
   Nicht gesetzt: `StartupNotify`, `StartupWMClass`, `NoDisplay`, `OnlyShowIn`, `TryExec`. Kleinigkeit: „fuer“ statt „für“ im Kommentar.
2. **belegt:** `desktop-file-validate` ohne Meldung (Rückgabe 0). `Exec` löst auf `/usr/bin/fisi-lernplattform` → `/opt/fisi-lernplattform/FISI-Lernplattform` auf, ausführbar. `Icon=fisi-lernplattform` passt zur installierten Datei `hicolor/512x512/apps/fisi-lernplattform.png`; GTK findet das Symbol auch bei Anfrage 48 px. Es gibt nur diese eine Größe.
3. **belegt:** Ja. Ubuntu 26.04 hat dpkg-Trigger: `desktop-file-utils` beobachtet `/usr/share/applications`, `hicolor-icon-theme` beobachtet `/usr/share/icons/hicolor`. Bei jeder Installation, jedem Update und jeder Entfernung erscheint „Processing triggers for hicolor-icon-theme … / desktop-file-utils …“; der Symbol-Zwischenspeicher ist danach gültig und enthält den Eintrag. Eigene Skripte sind nicht nötig. GNOME selbst bemerkt neue Dateien in `/usr/share/applications` ohne Zwischenspeicher (vermutet; im Container nicht prüfbar).
4. **belegt:** Geprüft wurden die .deb von 0.20, 0.30, 0.40, 0.50, 0.55, 0.57, 0.58, 0.58.1 und 0.59 (`messung/vergleich_versionen.txt`). Menüeintrag in allen gleich (gleiche Prüfsumme), Symbol in allen nur 512 px (bei 0.20 eine andere, kleinere PNG-Datei). Keine Felder für Abhängigkeiten, keine Skripte. **Seit 0.20 hat sich am Paketaufbau nichts geändert.**
5. Ursache und Vorschlag: siehe Kurzbericht Punkt 1 und Empfehlungen a2, a3, a6.

### C. Neuinstallation über eine ältere Version (Container ubuntu:26.04) – belegt

1. `apt install ./…0.58.1…` und danach `apt install ./…0.59…`: „1 upgraded … Unpacking fisi-lernplattform (0.59) over (0.58.1)“, Rückgabe 0. Mit `dpkg -i` genauso. Keine Konflikte, keine Fehlermeldungen. Nach dem Update keine Dateien unter `/opt/fisi-lernplattform`, die nicht zum Paket gehören. Nach `apt remove` sind `/opt/fisi-lernplattform`, die .desktop-Datei und `/usr/bin/fisi-lernplattform` weg.
   - Gleiche Version noch einmal: apt sagt „is already the newest version“, dpkg installiert sie neu.
   - Ältere über neuere: apt bricht mit „Packages were downgraded and -y was used without --allow-downgrades“ ab (ohne `-y` würde es fragen), dpkg macht es ohne Rückfrage.
2. `dpkg --compare-versions`: 0.58.1 lt 0.59 wahr, 0.58 lt 0.58.1 wahr, 0.59 lt 0.59.1 wahr, 0.59.1 lt 0.60 wahr. Achtung für später: `0.59 lt 0.6` ist **falsch** (0.6 gilt als 0.6 < 0.59). Die zweistellige Schreibweise 0.60 ist also wichtig.
3. App Center: siehe Kurzbericht Punkt 2 (gelesen, nicht im echten App Center geprüft).

### D. Warnhinweis im App Center

Siehe Kurzbericht Punkt 3. Wortlaut (gelesen, deutsche Übersetzung im App Center): Banner „Möglicherweise unsicher – Dieses Paket wird von einem Drittanbieter bereitgestellt. Die Installation von Paketen von außerhalb des App Centers kann das Risiko für Ihr System und Ihre persönlichen Daten erhöhen. Stellen Sie sicher, dass Sie der Quelle vertrauen, bevor Sie fortfahren.“ und Rückfrage „Dieses Paket wird von einem Drittanbieter bereitgestellt und kann Ihr System und Ihre persönlichen Daten gefährden. Sind Sie sicher, dass Sie es installieren möchten?“. Der Link „Mehr erfahren“ führt zu ubuntu.com/server/docs/third-party-repository-usage. Das ist eine feste Warnung für jede lokale .deb, also für den Doppelklick-Weg **unvermeidlich**. Eine Signatur der .deb-Datei selbst hilft nicht (dpkg prüft solche Signaturen standardmäßig nicht, vermutet; das App Center fragt sie nicht ab, gelesen).

### E. Einfachere Wege

Bewertung in der Tabelle unter 4b und a1.

### F. Update unter Linux im Programm

**gelesen** (`fisi_update.py`, `app_gui.py`, Stand v0.59):

- Das Programm fragt beim Start (nach 3 s) `releases/latest` ab. Ist die Version neuer, öffnet sich „Update verfügbar“.
- Datei: Bei der .deb-Installation (erkannt daran, dass das Programm unter `/opt/fisi-lernplattform/` läuft) die erste Release-Datei, die auf `.deb` endet; beim AppImage (Umgebungsvariable `APPIMAGE`) die Datei auf `.AppImage`. Download nach `/tmp/FISI-Lernplattform-Update/<Dateiname>`, geprüft wird nur die **Dateigröße**, nicht die SHA-256-Prüfsumme.
- **.deb:** `pkexec apt-get install -y <Datei>` → grafische Passwortabfrage. Klappt das, steht im Fenster „Das Update ist installiert. Bitte das Programm schließen und neu starten.“ Der Anwender muss **von Hand schließen und neu starten**. Bricht er die Passwortabfrage ab, öffnet das Programm die .deb mit `xdg-open`, also im App Center, wo wegen Punkt 2 nur „Installiert“ (grau) erscheint (vermutet aus beidem zusammen, nicht geprüft). `pkexec` selbst wurde hier nicht geprüft; die apt-Installation darunter funktioniert (siehe C).
- **AppImage:** Die neue Datei ersetzt die alte am selben Ort und startet neu. Nichts von Hand nötig, solange der Ordner beschreibbar ist.

**Fenster „Update verfügbar“:**

- **gelesen:** Die Größe ist fest: `geometry("560x500")` und `resizable(False, False)`. 0.58 und 0.59 haben exakt denselben Aufbau (Klasse `UpdateDialog` in beiden Versionen zeichengleich, belegt per Prüfsumme). Die Knöpfe werden als letztes Element eingefügt; reicht der Platz nicht, schneidet Tk zuerst das zuletzt eingefügte Element ab, also die Knöpfe.
- **belegt (Xvfb, 0.59-Quelltext, Release-Text von 0.59 als Neuerungen):** Das Fenster bleibt immer 560×500. Die Schriftgröße der Optionen vergrößert den Inhalt (Faktor 1,15 bzw. 1,3), das Fenster wächst nicht mit. Gemessene Knopfhöhe (voll wären 38 / 44 / 49 px):

| Schrift im System | Normal | Groß | Sehr groß („Jetzt aktualisieren“) | Sehr groß („Zur Download-Seite“) |
|---|---|---|---|---|
| Inter | ganz sichtbar | ganz sichtbar | ganz sichtbar | 25 px, abgeschnitten |
| Ubuntu | ganz sichtbar | ganz sichtbar | ganz sichtbar | ganz sichtbar |
| DejaVu Sans | ganz sichtbar | ganz sichtbar | ganz sichtbar | 44 px |
| Noto Sans | ganz sichtbar | ganz sichtbar | **28 px, halb abgeschnitten** | **4 px, praktisch unsichtbar** |

  Bilder dazu in `bilder/`. Bei „Normal“ ließ sich Nicos Bild (gar keine Knöpfe) also **nicht** nachstellen. Bei „Sehr groß“ und einer Schrift mit größerer Zeilenhöhe verschwinden die Knöpfe nachweislich.
- **vermutet:** Auf Nicos VM war entweder eine größere Schriftgröße eingestellt oder die Schriftmaße unter GNOME sind größer als im Xvfb-Test. **nicht geprüft:** echtes GNOME (Fensterrahmen, Skalierung). Der Versuch, das echte 0.58-Paket im Container bis zum Update-Fenster laufen zu lassen, scheiterte daran, dass der Container GitHub aus dem Programm heraus nicht erreicht.

---

## Dateien dieser Untersuchung

- `messung/paket_0.59.txt`, `messung/paket_0.58.1.txt`: `dpkg -I`, Steuerarchiv, `dpkg -c` vollständig
- `messung/vergleich_versionen.txt`: neun Versionen im Vergleich
- `messung/fisi-lernplattform_0.59.desktop`: der Menüeintrag aus dem Paket
- `messung/ergebnis_26.04.txt`: Installation, Update, Downgrade, Entfernen mit apt und dpkg, Trigger, Versionsvergleich, Bibliotheken
- `messung/ergebnis_gio_26.04.txt`: GLib-Sicht auf den Eintrag und Gegenprobe mit alter Benutzerdatei
- `messung/ergebnis_wmclass.txt`: Fensterklasse des laufenden Programms
- `skripte/`: alle Prüfskripte (laufen im Container bzw. unter Xvfb, ändern nichts am Projekt)
- `bilder/`: Update-Fenster in vier Schriften und drei Schriftgrößen

## Quellen

- freedesktop.org, Desktop Entry Specification, Desktop File ID: https://specifications.freedesktop.org/desktop-entry-spec/latest/file-naming.html
- freedesktop.org, XDG Base Directory Specification: https://specifications.freedesktop.org/basedir-spec/latest/
- freedesktop.org, Icon Theme Specification („Minimally you should install a 48x48 icon in the hicolor theme“): https://specifications.freedesktop.org/icon-theme-spec/latest/
- Ubuntu App Center, Quelltext (Stand Commit 0924391, 05.10.2026): https://github.com/ubuntu/app-center, Dateien `packages/app_center/lib/deb/local_deb_page.dart`, `local_deb_model.dart`, `packagekit/packagekit_service.dart`, `src/l10n/app_de.arb`
- Ubuntu Discourse, „Supporting GUI deb package installs in Noble“: https://discourse.ubuntu.com/t/supporting-gui-deb-package-installs-in-noble/43156
- Ubuntu, Third-party repository usage: https://ubuntu.com/server/docs/third-party-repository-usage
- Flathub, Requirements: https://docs.flathub.org/docs/for-app-authors/requirements
- Debian-Werkzeuge im Container: `dpkg --compare-versions`, `desktop-file-validate`, `gtk-update-icon-cache` (Ubuntu 26.04.1)
