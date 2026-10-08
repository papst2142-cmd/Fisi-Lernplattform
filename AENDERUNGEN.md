# Änderungen

Neueste Version oben. Jede Version bekommt vor dem Release einen eigenen
Abschnitt `## <Version>` – dieser Text erscheint im GitHub-Release und im
Update-Fenster des Programms.

## 0.61

**Neuer Name: Fachinformatiker Lernplattform.** Das Programm heißt ab
dieser Version „Fachinformatiker Lernplattform“, auf dem Handy kurz
„FI Lernplattform“. Lernstand, Einstellungen, Sicherungen und der Abgleich
bleiben, wo sie sind; Updates kommen weiter wie gewohnt.

- **Windows:** Startmenü und Desktop heißen nach dem Update
  „Fachinformatiker Lernplattform“, der alte Eintrag verschwindet.
- **Linux:** Der Menüeintrag heißt neu. Eine vom Programm angelegte
  Desktop-Verknüpfung wird beim ersten Start umbenannt.
- **Handy:** Auf dem Handy heißt die App „FI Lernplattform“.
- **Herausgeber** ist „Nico H“.
- **Dateinamen:** Sicherungen und Problemberichte bekommen neue Dateinamen
  („Lernplattform-Sicherung_…“, „Lernplattform-Problembericht_…“). Alte
  Sicherungen lassen sich weiter einspielen.
- **AppImage:** neuer Hinweis zum Hänger-Befehl (steht auf der Release-Seite).
- **macOS:** Die Mac-Versionen werden gebaut und automatisch gestartet,
  aber nicht von Menschen auf einem echten Mac getestet.

## 0.60.1

Seiten öffnen beim ersten Mal schneller, weil das Programm sie nach dem
Start früher und in einer neuen Reihenfolge im Hintergrund vorbereitet.

- **Erstes Öffnen schneller (PC):** Nach dem Start bereitet das Programm
  jetzt zuerst Karteikarten, Spiel, Optionen und Fortschritt vor und fängt
  damit früher an. Neu vorbereitet werden auch die Hilfe und der Bereich
  „Farben“ in den Optionen; beide gehen beim ersten Öffnen schneller auf.
  Das geschieht in kleinen Schritten und pausiert, solange geklickt,
  getippt oder mit dem Mausrad gescrollt wird.
- **Wechsel Hell/Dunkel:** Der Wechsel dauert dadurch etwas länger als in
  0.60, bleibt aber deutlich schneller als vor 0.60. Auf Linux kann der
  Wechsel dadurch deutlicher länger dauern.
- **Handy:** keine Änderung außer der Versionsnummer.
- **macOS:** wird weiter mitgebaut, aber von niemandem auf einem echten
  Mac getestet.

## 0.60

Schnellerer Wechsel zwischen Hell und Dunkel, klarere Startseite, Tests vor
jedem Release und die Eingabe-Umgehung jetzt auch unter Linux X11.

- **Schnellerer Wechsel Hell/Dunkel (PC):** Die Optionen bauen ihre
  Bereiche erst beim Aufklappen, und die alte Oberfläche wird beim Wechsel
  nicht mehr mit umgefärbt. Der Wechsel geht dadurch schneller. Dafür
  braucht der Bereich „Farben“ in den Optionen beim ersten Aufklappen
  etwas länger.
- **Startseite klarer:** Die Lernserie steht nur noch einmal oben im Banner
  (PC und Handy), der Schalter „Lernserie anzeigen“ wirkt dort. Ringe und
  Kacheln heißen „Prüfungstrainer“ statt „Quiz“. Der Ring „Prüfungstrainer“
  zeigt jetzt groß die Zahl der verschiedenen beantworteten Fragen
  („von 2174 Fragen beantwortet“), nicht mehr die Zahl aller Antworten.
- **Handy:** Die Startseite zeigt die Versionsnummer unter der Überschrift.
  Die Kacheln im Fortschritt heißen wie am PC („Test-Sessions“, „Bestes
  Ergebnis“), die Lernserie steht nicht mehr doppelt. Die Knöpfe „Hilfe“
  und „Suchen“ oben haben jetzt einen Namen für Bildschirmleser.
- **Hilfe:** Beim Öffnen sind alle Abschnitte eingeklappt, wie bei den
  Optionen (PC und Handy).
- **Linux mit X11 und IBus:** Die Eingabe-Umgehung aus 0.59.3 gilt jetzt
  auch in X11-Sitzungen, wenn IBus als Eingabemethode eingestellt ist. Unter
  X11 ist das bisher nur in einer Test-Umgebung geprüft. Wer IBus im
  Programm braucht, startet es mit `FISI_XIM=1 fisi-lernplattform`. Mit
  `FISI_XIM=1` kann das Programm wieder langsamer sein oder hängen. Die
  erste Zeile in haenger.log nennt jetzt die Sitzungsart („(X11)“ oder
  „(Wayland)“).
- **Tests vor jedem Release:** Die automatischen Tests laufen jetzt bei
  jedem Bau mit (Linux und Windows). Ein roter Test hält den Release auf.

## 0.59.3

Umgehung für das Einfrieren auf Linux (Wayland) mit IBus und korrigierter
Diagnose-Befehl.

- **Linux mit Wayland und IBus:** Das Programm konnte beim
  Darstellungswechsel oder beim Öffnen der Suche dauerhaft einfrieren und
  beim Schließen hängen bleiben. Es schaltet dort jetzt für sich die
  IBus-Eingabe ab; Umlaute, ß, AltGr-Zeichen und tote Tasten gehen weiter.
  Wer IBus im Programm braucht, startet es mit
  `FISI_XIM=1 fisi-lernplattform`. Windows, macOS und andere
  Linux-Sitzungen sind nicht betroffen.
- **Bessere Diagnose:** Die erste Zeile in haenger.log zeigt jetzt die
  Sitzungsart, die Eingabemethode (`XMODIFIERS`) und ob die Umgehung aktiv
  ist.
- **Korrigierter Befehl:** Der Befehl, mit dem das Programm unter Linux
  seine aktuelle Stelle in haenger.log schreibt, heißt jetzt
  `kill -USR1 $(pgrep -i -x -o fisi-lernplattf)`. Der bisherige Befehl fand
  das Programm aus dem .deb-Paket nicht und konnte beim AppImage den
  falschen Prozess treffen.
- **Vorladen benannt:** Das Vorladen der Seiten nach dem Start wird in der
  Diagnose früher als bekannter langer Vorgang benannt. Am Verhalten ändert
  sich nichts.

## 0.59.2

Aufgeräumte Optionen und bessere Hilfe, wenn das Programm hängt.

- **Optionen aufgeräumt:** „Problem melden“ und „Leistungsmessung“ stehen
  jetzt zusammen ganz unten im neuen Bereich „Diagnose und Werkzeuge“. Beim
  Öffnen der Optionen ist er eingeklappt, wie die anderen Bereiche. Die
  Suche führt direkt dorthin.
- **Hänger-Diagnose (PC):** Bleibt das Programm hängen, schreibt es nach
  30 Sekunden automatisch in die Datei haenger.log, an welcher Stelle es
  steht. Kürzere Blockaden ab 5 Sekunden stehen kurz in fehler.log. Beide
  Dateien liegen im Datenordner und stehen im Problembericht. Es wird nichts
  gesendet. Unter Linux kann man diese Angaben jederzeit mit einem Befehl
  abrufen; er steht unter „Diagnose und Werkzeuge“ und lässt sich dort
  kopieren (erst ab dieser Version, in älteren Versionen beendet der Befehl
  das Programm).
- **Kein zweites Fenster mehr nach kurzem Stocken:** War das laufende
  Programm beim zweiten Start nur kurz beschäftigt, öffnete sich bisher nach
  einiger Zeit doch ein zweites Fenster. Jetzt kommt das vorhandene Fenster
  nach vorn, sobald es wieder antwortet.
- **Windows: Speicher in der Leistungsmessung:** Die Spalte mit dem
  Arbeitsspeicher war unter Windows leer und ist jetzt gefüllt. Die
  Messdatei zeigt außerdem den freien Arbeitsspeicher beim Start und, was
  das Programm gerade tat, wenn es stockte.

## 0.59.1

Besser unter Linux, ein Programmfenster statt zwei und ein mitwachsendes
Update-Fenster.

- **Linux: richtiges Symbol und Name im Dock:** Das laufende Programm zeigt im
  Dock jetzt das Ring-Symbol und den Namen „FISI Lernplattform“ statt „Tk“
  und eines Zahnrads. Angeheftet und laufend ist es ein einziges Symbol.
- **Linux: schärfere Symbole:** Die .deb bringt das Symbol in fünf Größen
  von 48 bis 512 Pixeln mit, im Menü und in der Suche wirkt es nicht mehr
  verschwommen.
- **Linux: fehlende Bibliotheken:** Die .deb holt die zwei Bibliotheken, die
  das Programm unter Ubuntu zum Starten braucht, bei der Installation
  automatisch mit dazu.
- **Linux: Menüeintrag mit Umlauten:** Die Beschreibung im Menü heißt jetzt
  „Lernprogramm für …“. Im Dock gibt es kein „Neues Fenster“ mehr.
- **Nur noch ein Fenster:** Startest du das Programm ein zweites Mal (Linux
  und Windows), öffnet sich kein zweites Fenster. Das laufende Fenster kommt
  nach vorn, auch wenn es minimiert war. So können sich zwei Fenster nicht
  gegenseitig Einstellungen oder Spielstand überschreiben.
- **Update-Fenster wächst mit:** Bei den Schriftgrößen „Groß“ und „Sehr
  groß“ wird das Update-Fenster größer, die Knöpfe sind immer sichtbar und
  das Fenster lässt sich vergrößern. Bei „Normal“ bleibt es wie bisher.
- **Linux: Update ohne Passwort abgebrochen:** Bricht man die Passwortabfrage
  beim Update ab, nennt das Programm den genauen Befehl mit dem Dateinamen,
  mit dem man die .deb im Terminal installiert.
- **Handy mit Screenreader:** Knöpfe und Kacheln melden sich bei TalkBack als
  „Schaltfläche“ mit ihrem Namen. Das Ergebnis nach „Antwort prüfen“, die
  Update-Suche und der Abgleich werden vorgelesen.
- **Installation unter Ubuntu:** Auf der Release-Seite und in LIESMICH.txt
  steht, wie man die .deb mit einer Zeile im Terminal installiert und
  aktualisiert (`sudo apt install ./…deb`). Dort steht auch, was zu tun ist,
  wenn eine alte selbst angelegte Startdatei in
  `~/.local/share/applications/` den Menüeintrag verdeckt: verschieben, dann
  einmal ab- und wieder anmelden.

## 0.59

Die Optionen sind übersichtlicher, dazu eine Desktop-Verknüpfung unter Linux.

- **Optionen übersichtlich:** „Updates“ steht jetzt ganz oben. Beim Öffnen der
  Optionen sind alle anderen Bereiche eingeklappt, nur „Problem melden“ ist
  offen. Mehrere Bereiche können gleichzeitig offen sein.
- **Deutlichere Kopfzeile:** Ein großer Pfeil links in der Farbe des Bereichs,
  rechts „aufklappen“ bzw. „einklappen“. Die ganze Zeile ist anklickbar, am PC
  auch mit Tab, Eingabe- oder Leertaste. Am Handy liest TalkBack zum Beispiel
  „Farben, eingeklappt“ und sagt den Wechsel an.
- **Hilfe:** Die Abschnitte der Hilfe haben dieselbe neue Kopfzeile.
- **Vorlagen:** Die Farbvorlagen (Grundfarbe und Hintergrund) liegen im
  einklappbaren Unterbereich „Vorlagen“ und haben kleinere Kacheln.
- **Hintergründe in der hellen Darstellung:** Sie heißen dort so, wie sie
  aussehen: Flieder, Hellblau, Mintgrün, Rosé, Hellgrau und Weiß. Deine
  gewählte Farbe bleibt gleich, nur der Name ändert sich.
- **Suche:** Die Suche (Strg+F) findet jetzt auch Bereiche der Optionen,
  z. B. „Token“ oder „Weiß“. Ein Klick klappt den Bereich auf und springt hin.
- **Linux: Desktop-Verknüpfung:** Beim ersten Start unter Linux (.deb und
  AppImage) fragt das Programm, ob es eine Verknüpfung auf dem Desktop anlegen
  soll. In den Optionen unter „Updates“ gibt es dafür auch einen Knopf.
- **Hinweis zum AppImage:** Startet das AppImage nicht, steht in LIESMICH.txt
  und auf der Release-Seite, was fehlt (FUSE) und wie es trotzdem geht.

## 0.58.1

Das Programm bleibt schlank und reagiert flüssiger, dazu eine neue
Leistungsmessung in den Optionen.

- **Hell/Dunkel wechseln:** Nach einem Wechsel der Darstellung, der Farbwelt
  oder der Schriftgröße bleibt die alte Oberfläche nicht mehr im Speicher.
  Das Programm wächst dabei nicht mehr mit jedem Wechsel.
- **Fenstergröße ändern:** Deutlich flüssiger. Nicht sichtbare Seiten rechnen
  beim Ziehen nicht mehr mit, sie passen sich erst an, wenn du sie öffnest.
- **Bild-Zwischenspeicher:** Hat jetzt eine Obergrenze und wächst auch bei
  langem Ziehen am Fensterrand nicht mehr ohne Ende.
- **Leistungsmessung:** Neue Karte in den Optionen (PC und Handy). Mit
  „Messung aufzeichnen“ schreibt das Programm in eine Datei auf diesem Gerät,
  wie lange Seitenwechsel, Darstellungswechsel und Änderungen der
  Fenstergröße dauern und wie viel Arbeitsspeicher es braucht. Zu Beginn
  ist die Messung aus. Die Datei bleibt auf dem Gerät, enthält keine
  Lerndaten und keinen Namen und kommt nicht in den Abgleich. „Messdatei
  zeigen“ und „Messdatei löschen“ stehen daneben, dazu ein Hilfe-Abschnitt.

## 0.58

Neuer USV-Rechner, farbige Regler bei den eigenen Farben und viele kleine
Verbesserungen an Dashboard und Diagrammen.

- **USV-Kapazität:** Neuer Rechner unter „Rechner“. Er rechnet aus Last,
  Leistungsfaktor und Wirkungsgrad die nötige Akku-Kapazität, die Laufzeit
  eines vorhandenen Akkus oder eine Empfehlung für die USV-Größe (80-%-Regel).
  Ein Bild zeigt Last, Auslastung und Laufzeit, der Rechenweg lässt sich
  aufklappen. Dazu sechs Übungsaufgaben mit Lösung.
- **Farbige Reglerspuren:** Die Regler bei „Eigene Farben“ zeigen in ihrer
  Spur, was ein Schieben bewirkt (alle Farbtöne, grau bis voll, dunkel bis
  hell). Der Knopf bleibt auf jeder Stelle gut sichtbar.
- **Zustandszeile der eigenen Farben:** Über den Reglern steht jetzt immer,
  wie die Regler zum Gespeicherten stehen: „Startwerte aus der Farbwelt“,
  „Eigene Farben aktiv“ oder „Regler verändert, noch nicht gespeichert“.
- **Dashboard:** Passt jetzt auch bei 1360 Pixel Fensterbreite und großer
  Schrift, ohne dass etwas abgeschnitten wird.
- **Diagramme:** Am Handy wächst die Schrift der Diagramme mit der
  Schriftgröße. Das Liniendiagramm hat am Handy eine Legende (zum Beispiel
  „Aufgaben“). Bei vielen Tagen werden die Datumsangaben ausgedünnt, der
  heutige Tag ist immer beschriftet.
- **Namensfeld:** Das Feld für deinen Namen in den Optionen ist breiter.
- **Hilfe:** Neuer Abschnitt „Update und Schutzprogramm“. Das Update-Fenster
  weist mit einer Zeile darauf hin.
- **Technik:** Der Start-Test beim Bauen hat auf macOS mit Intel-Prozessor
  mehr Zeit (240 statt 120 Sekunden).

## 0.57

Eigene Farben mit Reglern und eine besser lesbare Spielkarte im dunklen Modus.

- **Eigene Farben:** In den Optionen unter „Farben“ gibt es den neuen
  Bereich „Eigene Farben“. Mit „Farbton“, „Sättigung“ und „Helligkeit“
  stellst du „Akzent 1“ und „Akzent 2“ (den Farbverlauf der Knöpfe) und den
  Hintergrund ein. Eine Vorschau zeigt sofort, wie es aussieht. Die Regler
  starten bei deiner Farbwelt; sobald du einen bewegst, werden alle Farben
  passend dazu neu berechnet. Hell und Dunkel haben getrennte Einstellungen,
  „Auf Farbwelt zurücksetzen“ stellt die gewählte Farbwelt wieder her.
- **Warnhinweise:** Ist etwas schlecht lesbar, nennt ein Hinweis den
  gemessenen Kontrast. Lassen sich die Farben der Fachbereiche kaum
  unterscheiden, erscheint eine eigene Warnzeile. Speichern geht trotzdem.
- **Kacheln:** Sind eigene Farben gespeichert oder die Regler bewegt, setzt
  ein Klick auf eine Grundfarbe oder einen Hintergrund nur die Regler.
  Gespeichert wird erst mit „Speichern“.
- **Hilfe:** Neuer Abschnitt „Eigene Farben“.
- **Spielkarte:** Im dunklen Modus sind Straßen, Fluss, Bahn, Bäume,
  Gebäudeumrisse und Beschriftungen besser lesbar (Kontrast wie bei der
  hellen Karte). Die Stimmung der Karte bleibt.
- **Hinweis:** Eigene Farben gelten nur auf diesem Gerät und kommen nicht
  in den Abgleich.

## 0.56

Aufgeräumt, schneller, verständlicher: Auswertung nach richtig und falsch,
Rundgang und Hilfe, größere Schrift und bessere Bedienung per Tastatur.

- **Auswertung:** Neues Diagramm „Richtig und falsch pro Tag“ im
  Fortschritt (Balken mit Prozent, falsch zusätzlich schraffiert). Das
  Diagramm „Ergebnisse im Prüfungstrainer“ zeigt nur echte, abgeschlossene
  Runden mit Datum; der leere Punkt bei 0 % ist weg, das Datum am PC steht
  richtig herum.
- **Aufgaben pro Tag:** Die Kurve schwingt nicht mehr unter 0 oder über die
  Tageswerte hinaus. „Tagesziel“ steht jetzt oben rechts über dem
  Diagramm und verdeckt nichts mehr.
- **Aufgeräumt:** „Aktivität je Fachbereich“ (Start) und „Karteikarten nach
  Fachbereich“ (Handy, Lernen) sind entfernt. In den Optionen sind „Farben“
  und der neue Bereich „Löschen und zurücksetzen“ zuklappbar. „Historie
  löschen“ steht jetzt dort statt im Fortschritt. Die Sicherheitsabfragen
  sind unverändert.
- **Rundgang und Hilfe:** Neue Nutzer bekommen beim ersten Start einen
  kurzen Rundgang mit „Jetzt einrichten“ (Name, Rahmenplan, Prüfungstermine).
  Wer schon gelernt hat, sieht ihn nicht von selbst, kann ihn aber in den
  Optionen unter „Rundgang und Hilfe“ starten. Neue „Hilfe“ (PC: Menüpunkt
  vor „Optionen“, Handy: Fragezeichen oben) mit Anleitung zum Abgleich,
  Tastaturhilfe und Hinweisen bei Warnungen vom Schutzprogramm; die Suche
  findet auch die Hilfe.
- **Name:** Wer einen Namen einträgt (Rundgang oder Optionen), wird im
  Dashboard bzw. auf Start mit „Hallo …“ begrüßt. Der Name bleibt auf dem
  Gerät und kommt nicht in den Abgleich, die Sicherung oder „Problem melden“.
- **Schriftgröße:** Normal, Groß und Sehr groß in den Optionen.
- **Tastatur am PC:** Lernbereiche und Optionen lassen sich mit Tab,
  Eingabe und Leertaste bedienen, mit gut sichtbarem Rahmen.
- **Farben:** Löschen- und Erfolg-Knöpfe sind etwas dunkler, Ränder von
  Eingabefeldern deutlicher; die Spielweltkarte ist im hellen Modus besser
  lesbar.
- **Schneller am PC:** Die großen Ansichten werden nach dem Start im
  Hintergrund vorbereitet und öffnen danach deutlich schneller.
- **Inhalte geprüft:** 71 bisher unsichere Inhalte nachgeprüft: 58 bestätigt,
  12 berichtigt (u. a. Bildungsurlaub Niedersachsen, IT-Fortbildung 2024,
  IP-Schutzart, Rügepflicht, PowerShell), einer bleibt offen. Dazu drei
  Fehler behoben: AP1 „Drei Fachinformatiker gründen eine UG“ (Bedingung
  in Aufgabe 3 ergänzt), Lernthema bei AP1 „PC-Kasse im Fahrradladen“ und
  AP2 „IPTV in einer Seniorenresidenz“.
- **Problem melden:** Der Bericht wird an die Person weitergegeben, von der
  du das Programm hast.
- **Update:** Jedes Release wird vor dem Veröffentlichen automatisch mit
  einem Update von der Vorversion geprüft. Das Update-Fenster zeigt nur noch
  die Neuerungen.
- Lernstand, Spielstände, Spielwerte und der Abgleich bleiben unverändert.

## 0.55.1

Fehlerbehebung: Das Update am PC bricht nicht mehr ab, das Programm schließt
sauber.

- **Wichtig für den PC:** Wer 0.54 oder 0.55 installiert hat, installiert
  diese Version einmal von Hand: PC neu starten, das Programm nicht öffnen,
  `FISI-Lernplattform-Setup-0.55.1.exe` von dieser Release-Seite
  doppelklicken. Danach laufen die Updates wieder von selbst. Am Handy
  ändert sich nichts.
- **Schließen:** Das Programm endet jetzt vollständig, auch wenn vorher
  Karteikarten, Optionen, Rechner oder das Update-Fenster offen waren.
  Vorher blieb es unsichtbar im Hintergrund und schrieb „can't delete Tcl
  command“ in fehler.log.
- **Update am PC:** Der Installer wartet, bis das Programm wirklich beendet
  ist, und ersetzt erst dann die Dateien. Jeder Schritt steht in
  `update.log` im Datenordner, auch unter Optionen › Problem melden.
  Scheitert ein Update trotzdem, startet die bisherige Version wieder und
  sagt, was passiert ist und wo das Protokoll liegt.
- Lerninhalte, Spielstände und der Abgleich bleiben unverändert.

## 0.55

Lernen nach dem Ausbildungsrahmenplan: Abdeckung sehen, gezielt üben und
384 neue Inhalte.

- **Rahmenplan-Abdeckung:** Neue Karte im Fortschritt direkt unter „Aufgaben
  pro Tag“, auf PC und Handy gleich. Sie zeigt alle 144 Punkte des
  Ausbildungsrahmenplans, aufklappbar nach Abschnitt, Position und Punkt, mit
  Anzahl der Inhalte und „Jetzt üben“. Filter: Alle, AP1, Konzeption,
  Netzwerke, Projekt, WiSo. Die Ampel (rot unter 50 %, orange bis 79 %, grün
  ab 80 %) ist in Hell und Dunkel gut lesbar.
- **Lernfeld-Ansicht:** Dieselbe Karte zeigt auf Wunsch Jahr, Lernfeld und
  Lernthema. Dein aktuelles Lernfeld steht oben und ist markiert.
- **Optionen „Rahmenplan“:** Abschnitte B, D und E einblenden, Übungsauswahl
  gewichten, aktuelles Lernfeld sowie die Termine für AP1 und AP2. Die
  Einstellungen gelten nur für das jeweilige Gerät.
- **Gewichtung:** Neue, noch nie bearbeitete Aufgaben kommen nach Zeitrichtwert,
  Lernfeld-Stunden und Nähe zur Prüfung an die Reihe. Wiederholungstermine
  bleiben unverändert. Ist der Schalter aus, gilt die Reihenfolge von 0.54.
- **384 neue Inhalte:** 165 Karteikarten, 174 Quizfragen, 15 AP1-Szenarien
  und 30 AP2-Szenarien, alle angehängt. Dein Lernstand bleibt erhalten.
- **Neues AP1-Thema:** „Arbeitsplatz einrichten: Bedarf, Beschaffung, Übergabe“.
- **Zwei neue AP2-Themen:** „Systemadministration“ und „Automatisierung &
  Skripte“.
- **Datenbanken:** 17 ältere SQL-Karten und -Fragen gehören jetzt zum
  Fachbereich „Datenbanken & SQL“. Deine Antworten dazu bleiben erhalten.
- **Bestandsschutz im Spiel:** Neue Inhalte zählen für den Wissensstand im
  Spiel erst, wenn du sie bearbeitet hast. So wird kein Auftrag durch das
  Update wieder gesperrt. Die Rahmenplan-Abdeckung zählt alle Inhalte.
- **Problem melden:** Benutzernamen in Ordnerpfaden werden im Bericht und im
  Fehlerprotokoll unkenntlich gemacht.
- **Spiel:** Bei „Arbeitsspeicher für die Leitstelle bestellen“ zählen
  einzelne RAM-Module jetzt zusammen. Vier 8-GB-Module für zwei PCs sind
  richtig, und beim Zusammenbau lassen sich zwei Module zusammen einsetzen.
- **Seitenleiste am PC:** „Inhalte bearbeitet“ und die Zahl überlappen nicht
  mehr. Bei großen Zahlen rutscht die Zahl in eine eigene Zeile.
- **Wichtig:** Bring PC und Handy beide auf 0.55. Geräte mit 0.54 kennen die
  neuen Inhalte noch nicht.

## 0.54

Möbel frei aufstellen, Schwächen direkt üben und vier neue Werkzeuge.

- **Möbel frei aufstellen (Zuhause):** Im Modus „Einrichten“ liegt ein
  feines Raster über dem Grundriss. Am PC ziehst du Möbel mit der Maus, R
  oder Rechtsklick dreht, Strg+Z oder „Rückgängig“ nimmt zurück. An Wand und
  Ecke docken Stücke an. Eine Vorschau zeigt vorher, ob es passt: grün passt,
  gelb versperrt einen Weg (nur Warnung), rot geht nicht (z. B. vor einer
  Tür). Am Handy tippst du ein Möbelstück an, dann das Zielfeld, und
  schiebst es mit vier Pfeilen. Deine bisherige Einrichtung bleibt, wo sie
  ist.
- **Wegprüfung:** Kommt die Figur nicht mehr an ein Möbelstück oder in einen
  Raum, erscheint „Achtung, Weg versperrt!“. Aufstellen bleibt erlaubt.
- **Jetzt üben:** In der Prüfungsauswertung und im Fortschritt steht neben
  jedem schwachen Thema „Jetzt üben“. Erst kommen die Quizfragen zum Thema,
  danach auf Wunsch die Karteikarten, das Ungewusste zuerst.
- **Suche im Notizblock:** Stichwort eingeben, gesucht wird in Frage,
  Antwort und Thema. Umlaute und Groß-/Kleinschreibung spielen keine Rolle.
- **Aufgaben pro Tag:** Neues Diagramm im Fortschritt für 7 oder 30 Tage mit
  Tagesziel-Linie.
- **Problem melden:** Neue Karte in den Optionen. Sie zeigt Version, Gerät,
  Datenordner und Fehlerprotokoll zum Kopieren oder Speichern.
  Zugangsschlüssel und Passwörter stehen nie darin.
- **RAID-Rechner und Serverfarm:** RAID 0 braucht bei der Eingabe
  mindestens 2 Platten.
- **Texte:** Firmen- und Personennamen stehen ohne Artikel im Satz („fängt
  bei Nico IT an“).
- **Schneller:** Firma, Reise und Spiel öffnen am PC ab dem zweiten Besuch
  in unter 0,1 Sekunden.
- **Kleinigkeiten:** Der Scrollbalken zeigt nach kürzer werdenden Seiten die
  richtige Länge. Beim Schließen bleiben keine Zeitgeber mehr zurück.

## 0.53

Prüfung und Fehlerbehebung: Diese Version bringt keine neuen Funktionen, sondern eine gründliche Prüfung von PC und Handy sowie aller Texte.

- **Lernstand bleibt erhalten:** 14 Fragetexte (5 Karteikarten, 9 Quizfragen)
  wurden korrigiert. Deine bisherigen Antworten zählen automatisch beim neuen
  Text, auch wenn sie per Abgleich von einem Gerät mit älterer Version kommen.
- **Texte:** Rund 200 Rechtschreib-, Grammatik- und Sachfehler in Karteikarten,
  Prüfungstrainer, Szenarien, Testprojekten und Spiel korrigiert, darunter
  POP3, Schaltjahr, Reverse-Lookup und vertauschte Zahlen in einem
  AP2-Szenario. Einzahl/Mehrzahl stimmt jetzt überall („1 Tag“, „2 Tage“).
- **Menünamen:** „Testprojekt“, „AP1-Szenarien“ und „AP2-Szenarien“ auf PC
  und Handy.
- **Hellmodus:** Spielername, Silber/Gold/Bronze und die HE-Nummern im Rack
  sind gut lesbar.
- **Handy:** Nach „Sicherung einspielen → Alles ersetzen“ oder „Alle
  Lerndaten löschen“ ist die Startseite wieder vollständig. Pillen-Leiste,
  Update-Fenster und Spielfigur-Laufwege korrigiert.
- **Prüfung:** Die Prüfungszeit stimmt auch bei der Umstellung auf
  Sommer- oder Winterzeit. Ein Farbwechsel während der Prüfung stoppt die
  alte Uhr sauber.
- **Lernserie:** Kopfzeile und Kachel „Heute“ zeigen dieselbe Zahl, nach
  Mitternacht frischt sich die Kachel auf.
- **Schneller:** Die Reiter in Firma und Reise wechseln deutlich schneller.
- **Kleinigkeiten:** Toasts liegen nicht mehr übereinander, Abzeichen-Namen
  werden nicht mehr abgeschnitten, in der kleinen Gebäude-Ansicht fehlt kein
  Name mehr, kein leerer Rollbalken, keine leere Seite im Abschlussprojekt.
- **Sicherer:** Einstellungen werden absturzsicher gespeichert, eine
  beschädigte Abgleich-Datei wird als solche gemeldet, der PDF-Export ersetzt
  Sonderzeichen sauber, der Textexport öffnet sich auch in älteren
  Windows-Editoren richtig. Unerwartete Fehler landen in „fehler.log“ im
  Datenordner.

## 0.52

Großauftrag Serverfarm und Sicherung: Diese Version bringt die zweite große Kampagne im Spiel und eine Sicherung des Lernstands als Datei.

- **Neu: Kampagne 2 „Großauftrag Serverfarm“.** Die Datenhafen Talheim GmbH
  baut im Rechenzentrum Lokschuppen eine Serverfarm.
  - Freigeschaltet wird sie mit Gebäudestufe 4, Serverraum, ISO 27001 und
    Cisco-Partner. Solange etwas fehlt, steht unter Firma → Zertifizierungen,
    was noch fehlt.
  - Der Lokschuppen erscheint mit „Neu“ auf der Karte. Die Kampagne startet
    erst, wenn du die Ausschreibung öffnest.
  - 6 Phasen, 18 Aufgaben, 25 Arbeitstage: Angebot, Planung und Bestellung,
    Lieferung, Einbau, Server bestücken und konfigurieren, Abnahme.
  - Du stellst ein eigenes Team zusammen. Es macht in dieser Zeit keine
    Kundentickets und keine Projekte. Die Routineaufträge laufen nebenbei
    zur Hälfte weiter.
  - Der Auftrag geht nie verloren. Einen Zuschlag über 20 % handelt die
    Kundin auf 20 % herunter.
  - Lieferverzug, Kabelfehler und Vertragsstrafen sind möglich. Auf „Einfach“
    sind die Folgen halbiert.
  - Bei einer fehlerfreien Abnahme gibt es 5.000 € Bonus.
  - Es gibt vier neue Abzeichen, den Bestwert „schnellste Fertigstellung“,
    einen Meilenstein-Moment und Einträge in „Meine Reise“.
- **Neu: Rack-Ansicht.** Sie ersetzt die alte Ansicht überall, auch bei den
  Rack-Tickets.
  - Am PC hat sie drei Spalten: Schrank, Geräte sowie Werte und Vorgaben.
  - Am Handy wählst du das Gerät aus einer Liste und tippst die Höheneinheit
    an. Werte und Vorgaben lassen sich aufklappen.
- **Neu: Aufgabe „Server bestücken“.** Du wählst CPU, RAM, Platten und das
  RAID-Level. Das RAID rechnet genauso wie der RAID-Rechner, und ein Knopf
  öffnet den Rechner mit deinen Werten.
- **Neu: Sicherung und Wiederherstellung** unter Optionen → „Sicherung“.
  - Der ganze Lernstand kommt in eine Datei `.fisisicherung`: Lernfortschritt,
    Prüfungen, Abschlussprojekt, Spielstände, Bestenliste und Tagesziel.
    Zugangsschlüssel und Farben kommen nicht mit.
  - Beim Einspielen wählst du „Zusammenführen“ (es kommt nur hinzu, was
    fehlt) oder „Alles ersetzen“. Vorher wird eine Sicherheitskopie
    angelegt.
  - Gelöschte Spielstände aus der Sicherung lassen sich als neuer Platz
    wiederherstellen.

## 0.51

Lern-Schwerpunkt: Diese Version bringt neue Lernwerkzeuge für die Prüfungsvorbereitung.

- **Neu: Wiederholung nach Plan.** Karteikarten und Fragen aus dem
  Prüfungstrainer kommen nach 1, 3, 7, 14 und 30 Tagen wieder. Nach einem
  Fehler beginnt die Karte wieder von vorn. Dashboard (PC) und Start
  (Handy) zeigen „Heute fällig“ und den Knopf „Jetzt wiederholen“.
  Was vor dem 01.10.2026 bearbeitet wurde, wird gestaffelt freigegeben,
  höchstens 20 Stück pro Tag. Rote Karten kommen zuerst.
- **Neu: Prüfungsmodus im Prüfungstrainer.** Die IHK-Prüfung wird nach der
  Ausbildungsverordnung von 2020 nachgestellt: AP1, Konzeption und
  Administration, Netzwerke sowie WiSo.
  - Die Zeit läuft fest und ohne Pause, wie in der echten Prüfung.
  - Offene Aufgaben bewertest du selbst anhand von Kriterien zum Abhaken.
    Daraus entsteht ein Punktevorschlag, den du anpassen kannst.
  - Es gilt der IHK-Notenschlüssel.
  - Das Gesamtergebnis wird nach § 24 berechnet. Bei „nicht bestanden“
    zeigt die App, ob eine mündliche Ergänzungsprüfung reichen würde.
- **Neu: Abschlussprojekt.** Am PC ist es ein eigener Menüpunkt, am Handy
  eine Kachel unter „Lernen“.
  - Sechs Reiter: Übersicht, Antrag, Zeitplan, Kosten, Dokumentation und
    Fachgespräch (mit 60 Übungsfragen).
  - Du kannst mehrere Projekte anlegen und Testprojekte als Vorlage nutzen.
  - Export als PDF oder als Text.
  - Alles wird zwischen den Geräten abgeglichen.
- **Neu: Subnetting-Trainer** im Rechner. Er übt IPv4-Subnetze, VLSM,
  Binär, Hex und Dezimal sowie IPv6, jeweils in drei Stufen. Jedes Feld
  wird einzeln geprüft, danach erscheint der Rechenweg.
- **Neu: Tagesziel, Lernserie und Erinnerung** unter Optionen →
  „Tagesziel“. Die Erinnerung erscheint als Hinweis beim Start oder beim
  Zurückkehren in die App. Sie ist standardmäßig um 18:00 Uhr
  eingeschaltet.
- Korrektur: Am Handy stand „vier Fachbereiche“. Anzahlen werden jetzt
  überall aus den Daten berechnet.
- Abgleich: Wiederholung, Prüfungen und Abschlussprojekt werden
  synchronisiert. Am besten bringst du PC und Handy beide auf 0.51.

## 0.50

- **Fehlerbehebung PC: Optionen bleiben nach dem Farbwechsel sichtbar.**
  Nach dem Wechsel von Grundfarbe, Hintergrund oder Darstellung (und beim
  ersten Klick auf „Optionen“ direkt nach dem Start) lag bisher die
  Spiel-Ansicht mit den Spielständen über der Optionen-Seite. Ursache war
  der Aufbau der Ansichten im Hintergrund seit 0.48; neu gebaute Ansichten
  landen jetzt unter der angezeigten.
- **PC: Reiter wechseln ohne Ruckeln.** Der Spielstand wird nur noch neu
  aus dem Ereignisprotokoll berechnet, wenn sich dort etwas geändert hat,
  Bilder werden nicht mehr bei jedem Wechsel neu skaliert, und Spiel-,
  Dashboard- und Notizblock-Ansichten bleiben beim Wechsel stehen, solange
  sich nichts geändert hat. Die Spielansichten wechseln damit in rund 30
  bis 60 ms statt 200 bis 700 ms; Aussehen und Spielwerte sind unverändert.
- Kehrt man in eine unveränderte Spielansicht zurück, bleibt die
  Scroll-Position erhalten und die Spielfigur steht an ihrem Platz.
- Handy: Die Spiel-Seite profitiert ebenfalls vom Spielstand-Cache.

## 0.49

- **Neu: Hellmodus.** Unter Optionen > Farben gibt es die Zeile
  „Darstellung“ mit **Dunkel** und **Hell**. Die Wahl gilt sofort, wird je
  Gerät gespeichert und lässt sich mit jeder Grundfarbe und jedem
  Hintergrund kombinieren. Standard bleibt Dunkel.
- Im Hellmodus hat jeder der sechs Hintergründe eine helle Fassung im
  selben Farbton (Lavendel, Blaugrau, Salbei, Rosé, Grau, Weiß). Grund- und
  Fachbereichsfarben werden als Schrift automatisch etwas dunkler, damit sie
  auf hellen Flächen gut lesbar sind.
- **Spiel:** Weltkarte und Grundrisse werden im Hellmodus ebenfalls hell.
  Figuren, Möbel und Gebäude behalten ihre Farben.
- Gleiche Version auf PC und Handy; enthält die Reparatur des Handy-Baus
  aus 0.48.1.

## 0.48.1

- **Fehlerbehebung Handy-Bau:** Ein Baustein, den die Handy-App beim Bauen
  aus dem Internet lädt, ist in der Nacht in einer fehlerhaften Fassung
  erschienen. Der Bau der Android-App ist daran gescheitert, deshalb gab es
  kein Release 0.48. Die App nutzt jetzt die letzte funktionierende Fassung.
- Inhaltlich ist alles wie in 0.48 (drei Spielstand-Plätze, Meldung beim
  Farbwechsel, scrollende Seitenleiste, Pfeile an den Pillenreihen,
  Weltkarte und Kleinigkeiten aus dem Systemtest). **Wichtig:** PC und
  Handy gleichen erst wieder ab, wenn beide mindestens auf 0.48.1 sind.

## 0.48

- **Spiel: Drei Spielstand-Plätze.** Beim ersten Öffnen von „Spiel“ nach
  dem Start wählst du einen von drei Plätzen. Jeder Platz ist ein eigener
  Durchgang mit Figur, Schwierigkeitsgrad, Firma und Reise. Ein belegter
  Platz zeigt Figur, Name, Schwierigkeit, Spieltag und Firma, ein leerer
  „Neuer Durchgang“. Plätze lassen sich umbenennen und einzeln löschen;
  vorher kommt der Endstand in die Bestenliste. Über „Platz wechseln“
  wechselst du jederzeit. Dein bisheriger Spielstand ist Platz 1.
  Lernfortschritt, Wissensstand und Bestenliste gelten für alle Plätze
  gemeinsam. „Spielstand zurücksetzen“ in den Optionen betrifft nur den
  aktiven Platz.
- **Abgleich:** PC und Handy haben dieselben Plätze, auch Anlegen und
  Löschen werden abgeglichen; ein gelöschter Platz kommt nicht zurück.
  **Wichtig:** Ein Gerät mit 0.47 gleicht erst wieder ab, wenn es auch auf
  0.48 aktualisiert ist. Der Lernstand geht dabei nicht verloren.
- **Farbwechsel:** Beim Wechsel von Grundfarbe oder Hintergrund erscheint
  „Farben werden angewendet – Bitte warten“, Eingaben sind so lange
  gesperrt. Am PC ist der Wechsel deutlich schneller (etwa 2,6 statt
  12,8 Sekunden).
- **PC: Seitenleiste scrollt,** wenn ausgeklappte Menüpunkte nicht mehr
  ins Fenster passen. Der Schieberegler erscheint nur bei Bedarf.
- **Handy: Pillenreihen** (z. B. die Firma-Reiter) laufen rechts aus und
  zeigen einen Pfeil, wenn es weitergeht. Der gewählte Reiter wird ins
  Bild gerückt.
- **Weltkarte:** Stadtteilnamen werden nicht mehr von Gebäuden verdeckt,
  „Neu“ steht unten am Gebäude statt auf dem Ortsschild.
- **Kleinere Verbesserungen aus dem Systemtest:** Diagramme mit runden
  Achsenschritten und vollständiger letzter Beschriftung, Hinweis bei
  leerer Filiale, Grund am gesperrten Coaching-Knopf, Farben im Tagebuch
  und Terminal nach einem Farbwechsel, Beschriftungen für Screenreader,
  nach oben scrollen am Handy sowie mehrere Fehler im Hintergrund behoben.

## 0.47

- **Spiel: Skill-Balken für Mitarbeiter.** Jede Person (auch bei den
  Bewerbungen) zeigt ihr Können jetzt als fünf farbige Balken, einen je
  Fachbereich. Ein Klick (am Handy ein Tipp) auf einen Balken klappt die
  Themen dieses Fachbereichs mit eigenen Balken und genauen Werten auf.
- **Schwierigkeitsgrad „Einfach“ oder „Normal“:** Beim Spielstart wählst
  du neben Name und Aussehen den Schwierigkeitsgrad. Er gilt fest für den
  ganzen Durchgang und lässt sich nur mit „Spielstand zurücksetzen“ neu
  wählen. Auf „Einfach“ fallen Umsatzsteuer, Mahnstufen, Abschwung,
  Gegenwind, Rückhol-Angebote und Kündigungen weg. Krankheit, Konflikte,
  abgelehnter Urlaub, Macken-Schwächen sowie Fehlerkosten und
  Ansehensverlust in der Bitweiche-Zeit sind halb so stark. Der Grad steht
  im Firmenkopf, im Rückblick und unter Optionen > Spiel. Ältere
  Spielstände zählen als „Normal“. Die Lernplattform bleibt unberührt.
- **Zwei neue Abzeichen:** „Story abgeschlossen: Einfach“ (Silber) und
  „Story abgeschlossen: Normal“ (Gold). Die Bestenliste bleibt ein
  gemeinsamer Topf. „Steuerehrlich“, „Zurück auf Kurs“ und „Treue Mannschaft“
  gibt es nur auf „Normal“.
- **„Meine Reise“:** Der Knopf „Reise öffnen“ heißt jetzt „Meine Reise“.
- **Karte:** Die Gleise der Talbahn fahren nicht mehr durch Bahnhöfe,
  Gebäude und Bäume, sondern sauber an den Bahnsteigen entlang.

## 0.46

- **Spiel: Erfolge in der Reise.** Unter Spiel > Reise gibt es jetzt die
  Reiter „Rückblick“ und „Erfolge“. Unter „Erfolge“ stehen 14 Bestwerte,
  die über alle deine Spielstände zählen (z. B. höchster Kontostand,
  größter Auftrag, meiste Mitarbeiter, Firma gegründet an Tag X), jeweils
  mit dem Durchgang, in dem du sie erreicht hast.
- **Abzeichen:** 32 Abzeichen mit Bronze-, Silber- und Goldstufen in den
  Gruppen Karriere, Firma, Geld, Personal und Wissen. Offene Abzeichen
  zeigen deinen Fortschritt und was du in früheren Durchgängen erreicht
  hast. Ein Abzeichen bleibt geheim, bis du es entdeckst.
- **Meilenstein-Moment:** Große Erfolge wie die Firmengründung, die
  Filiale oder 100.000 € auf dem Konto werden mit einer eigenen Karte
  gefeiert, samt „Zum ersten Mal erreicht!“ oder „Neuer Bestwert!“.
  Kleinere Abzeichen erscheinen als kurzer Hinweis.
- **Bestenliste bleibt erhalten:** Sie übersteht „Spielstand
  zurücksetzen“ und „Alle Lerndaten löschen“ und wird zwischen PC und
  Handy abgeglichen. Unter Optionen > Spiel kannst du sie mit „Bestenliste
  löschen“ gezielt leeren. Ältere Spielstände bekommen ihre Abzeichen
  beim ersten Öffnen still nachgetragen.

## 0.45

- **Spiel: Weltkarte als Startansicht.** Das Spiel beginnt jetzt mit einer
  Karte der Stadt aus der Vogelperspektive. Alle freigeschalteten Orte
  stehen darauf als Gebäude. Ein Klick (am Handy ein Tipp) auf ein Gebäude
  oder sein Schild öffnet den Ort. Neue Orte tragen ein „Neu“, offene
  Tickets stehen als Zahl am Gebäude. Am Handy kannst du mit zwei Fingern
  vergrößern.
- **„Liste“ statt Karte:** Ein Knopf schaltet auf eine kompakte Liste der
  Orte mit Vorschaubildern um. Jedes Gerät merkt sich deine Wahl.
- **Außenansichten:** Jedes Gebäude hat ein eigenes Modell, auch als
  Vorschaubild in den Ansichten. Dein Gewerbehof wächst mit jeder
  Ausbaustufe und zeigt Serverraum und Lager, deine Wohnung sieht je nach
  Wohnungstyp anders aus.
- **Zweiter Standort: Filiale in Lindenau.** Ab Gewerbehof-Stufe 4,
  6 Mitarbeitern und 40 Firmentagen kannst du unter Firma > Gebäude eine
  Filiale mit eigenem Namen eröffnen (30.000 €, 4 Plätze) und später
  ausbauen (15.000 €, 7 Plätze). Sie bringt eine Kundenanfrage mehr pro
  Tag und 3 % Preisvorteil bei der Talbahn-Verwaltung. Unter Mitarbeiter
  versetzt du Leute zwischen Gewerbehof und Filiale.
- **Bitweiche als Mitbewerber:** Nach der Gründung ist Bitweiche auf der
  Karte grau markiert. Ein Klick zeigt deine Bilanz gegen sie.

## 0.44

- **Spiel, eigene Firma: Rückhol-Angebote.** Viele Bewerber waren vorher
  bei einem Mitbewerber, das steht jetzt in der Bewerbung („bisher bei …“).
  Nach einiger Zeit versucht der frühere Arbeitgeber, sie zurückzuholen,
  bei schlechter Stimmung öfter. Du entscheidest: Gehalt erhöhen (+10 %),
  Halteprämie zahlen (10 Tagesgehälter) oder ziehen lassen.
- **Gegenwind:** Gewinnst du viele Angebote hintereinander, bieten alle
  Mitbewerber mindestens 10 Arbeitstage lang gezielt 3 Punkte günstiger.
  Solange zählt dein Preisvorteil (Ruf, Zertifizierungen, Werbung) nur
  halb. Die Stärke ist fest und schaukelt sich nicht hoch.
- **Konjunktur nach Tag 100:** Normale Lage, Aufschwung und Abschwung
  wechseln sich ab. Sie ändern die Zahl der Anfragen, die Marktpreise und
  den Umsatz deiner Mitarbeiter.
- **Technologietrends:** Cloud-Boom, KI-Nachfrage, Cybersecurity-Welle,
  Homeoffice, Glasfaser und Datenschutz bringen zeitweise zusätzliche
  Trend-Aufträge mit gelbem Hinweis. Passende Zertifizierungen helfen
  dabei, sind aber keine Pflicht.
- **Neuer Kasten „Markt“** unter Firma > Aufträge zeigt Konjunktur, Trend
  und Gegenwind. Alles steht auch im Morgentext und in der Reise des
  Spielers.

## 0.43

- **Spiel, eigene Firma: Mitarbeiter-Ereignisse.** Deine Mitarbeiter haben
  jetzt eine Stimmung (0 bis 100). Sie fragen ab und zu nach Urlaub: Du
  genehmigst (sie fehlen ein paar Tage, die Stimmung steigt) oder lehnst ab
  (die Stimmung sinkt, beim zweiten Mal in Folge deutlich). Ist die Stimmung
  lange sehr schlecht, kommt erst eine Warnung, dann die Kündigung.
- **Konflikte im Team:** Geraten zwei Mitarbeiter aneinander, entscheidest
  du: schlichten (kostet dich heute einen Ticket-Platz), Partei für einen
  der beiden ergreifen oder ignorieren (beide sind ein paar Tage verstimmt).
- **Krankheit:** Selten fällt jemand für 2 bis 4 Tage aus.
- **Offene Entscheidungen** stehen in der Übersicht unter „Heute“ und im
  Reiter „Mitarbeiter“. Feierabend geht erst, wenn sie beantwortet sind.
- **Macken mit Wirkung:** Jede Macke hat jetzt eine Stärke und eine
  Schwäche (z. B. „Langsam, aber gründlich“: bessere Ticket-Chance, aber
  weniger Umsatz). Die Ausprägung zeigen drei Balken (stark, mittel,
  leicht), auch in den Bewerbungen. Zwei neue Macken: Nachteule und
  Kundenflüsterer.
- **Macken schwächen sich ab:** alle 45 Arbeitstage eine Stufe oder sofort
  per Coaching (800 €, 3 Tage). Die Stärke bleibt immer voll.
- **Reise des Spielers:** Krankheit, Urlaub, Konflikte, Kündigungen,
  Coachings und schwächere Macken stehen mit drin.

## 0.42

- **Spiel, eigene Firma: Umsatzsteuer.** Die Einnahmen der Firma enthalten
  19 % Umsatzsteuer, die Vorsteuer aus Nebenkosten, Material, Ausbau,
  Weiterbildung, Werbung und Zertifizierungen wird abgezogen. Alles läuft
  automatisch: Die Firma legt die Steuer bei jedem Feierabend in eine
  Rücklage, alle 12 Arbeitstage kommt die Voranmeldung ans Finanzamt
  Talheim. Ist die Vorsteuer höher, gibt es eine Erstattung.
- **Steuer nicht bezahlt:** Reicht das Geld nicht, bleibt eine Steuerschuld
  offen. Dann greifen dieselben Mahnstufen wie bei den Krediten, die Schuld
  wird automatisch nachgezahlt, sobald wieder Geld da ist.
- **Neuer Reiter „Marketing“ (PC und Handy):** Zeitungsanzeige,
  Online-Werbung, Buswerbung und Fachmesse. Jede Form läuft dauerhaft
  (kündbar) oder einmalig für eine feste Zeit. Werbung bringt mehr Anfragen
  und Kundentickets, größere Bestellungen oder einen Preisvorteil.
- **Neuer Reiter „Zertifizierungen“ (PC und Handy):** ISO 9001, ISO 27001,
  Datenschutz (DSGVO), Microsoft-Partner, Linux (LPIC), Cisco-Partner und
  KI-Kompetenz. Sie kosten Geld und dauern einige Arbeitstage, geben einen
  Preisvorteil gegen Bitweiche und die anderen Mitbewerber (zusammen mit
  Ruf und Werbung höchstens 10 %) und schalten Großaufträge frei.
- **Großaufträge und öffentliche Ausschreibungen:** elf große Projekte
  (z. B. Windows 11 im Rathaus, WLAN für alle Grundschulen,
  Informationssicherheit im Kreisklinikum) mit 100 Punkten Aufwand. Hier
  bietet ein Mitbewerber mehr mit.
- **Finanzen:** neue Karte „Umsatzsteuer“ mit Rücklage, nächster
  Voranmeldung und den letzten Voranmeldungen. Feierabend und Reise zeigen
  Steuer, Werbung und Zertifizierungen. Am PC stehen die Firmenreiter jetzt
  in zwei Zeilen.

## 0.41

- **Spiel, eigene Firma: Kredite.** Neuer Reiter „Kredite“ unter Firma
  (PC und Handy). Die Hausbank leiht dir Geld, sobald deine Firma
  kreditwürdig ist: mindestens 10 Arbeitstage alt, 15.000 € Umsatz in den
  letzten 10 Arbeitstagen und mindestens 60 % Ansehen. Vorher zeigt der
  Reiter, was noch fehlt.
- **Kreditpakete und freie Summe:** Kurzkredit, Investitionskredit und
  Großkredit oder eine eigene Summe mit 20 bis 100 Arbeitstagen Laufzeit.
  Lange Laufzeit und große Summe kosten mehr Zins. Der Kreditrahmen hängt
  vom Umsatz und vom Ansehen ab, alle Raten zusammen dürfen höchstens die
  Hälfte des Gewinns sein.
- **Automatische Tilgung:** Die Rate (Zins und Tilgung) wird bei jedem
  Feierabend abgebucht. Mehrere Kredite laufen parallel, jeder hat einen
  Tilgungsplan und kann vorzeitig abgelöst werden.
- **Zahlungsschwierigkeiten:** Reicht das Konto nicht, platzt die Rate.
  Es gibt drei Mahnstufen mit Gebühren, weniger Ansehen, Zinsaufschlag und
  Kreditsperre. Ohne geplatzte Rate sinkt die Stufe nach 10 Arbeitstagen.
- **Finanzen:** Kreditzinsen, Tilgung und Gebühren stehen einzeln im
  Kassenbuch, dazu die festen Kosten pro Arbeitstag mit den Kreditraten.

## 0.40

- **Spiel, eigene Firma: Grenze fürs Lernen durch Arbeit.** Mitarbeiter
  lernen durch Kundentickets, Projekte und Routinearbeit in jedem Thema
  nur noch bis 70. Darüber (bis 90) geht es nur mit Weiterbildung.
- **Langsamerer Fortschritt:** Ein geschafftes Ticket bringt +1, ein
  fertiges Projekt +2 (pünktlich +1 extra), Routinearbeit alle 15
  Arbeitstage +1, ab 50 zählt alles nur halb. Fehlgeschlagene Tickets
  bringen weiterhin nichts.
- **Weiterbildung neu balanciert:** Thema +6 in 4 Arbeitstagen,
  ganzer Fachbereich +3 auf alle Themen in 5 Arbeitstagen (Preise gleich).
- **„Grenze erreicht“:** Die Feierabend-Meldung nennt, wer die Grenze in
  einem Thema erreicht hat. In den aufgeklappten Themen eines Mitarbeiters
  steht, wo nur noch Weiterbildung weiterhilft (PC und Handy).

## 0.39

- **Lernstand je Frage:** Jede Frage in Karteikarten, Prüfungstrainer,
  AP1, AP2 und Test Projekt hat jetzt einen Status: „Offen“ (grau), „Zu
  üben“ (rot nach einem Fehler, gelb nach einmal richtig danach) oder
  „Abgeschlossen“ (grün, zweimal hintereinander richtig). Ein Fehler
  holt eine abgeschlossene Frage wieder zurück.
- **Status-Reiter und Themenfilter** in allen Lernbereichen. Unbearbeitete
  Fragen kommen bevorzugt dran, nach je vier neuen eine Wiederholung.
- **Gewusst / Nicht gewusst:** Nach dem Aufdecken der Musterlösung (AP1,
  AP2, Test Projekt, Karteikarten im Modus „Aufdecken“) schätzt du dich
  selbst ein. Ohne Bewertung zählt es nur als angesehen.
- **Neuer Menüpunkt „Notizblock“:** Alle Fragen, die du noch üben solltest,
  mit Fortschritt je Bereich, Filtern nach Fachbereich, Bereich, Thema und
  Status, ein- und ausblendbaren Musterantworten und „Jetzt üben“ für
  eine gezielte Runde.
- **Spiel: „Reise“:** Rückblick mit Kennzahlen, Verlauf der Tickets je
  Arbeitstag und des Ansehens, gelöste Tickets je Fachbereich und ein
  Tagebuch mit allen wichtigen Momenten (Story, Beförderungen, jeder
  Zwischenfall, jedes Angebot, Projekte, Gründung, Ausbau, Mitarbeiter),
  filterbar nach Story, Karriere und Firma.
- **PC:** Die Seitenleiste zeigt jetzt dieselben Symbole wie die
  Handy-App, auch für die Unterpunkte.
- Der Abgleich zwischen PC und Handy nimmt die neuen Bewertungen mit.
  Bitte beide Geräte auf 0.39 aktualisieren.

## 0.38

- **Mitarbeiter mit Themenwissen:** Deine Mitarbeiter haben jetzt einen Wert
  in jedem der 36 Themen. Der Wert je Fachbereich ist der Durchschnitt
  seiner Themen, Gehalt und Umsatz rechnen wie bisher damit. Unter dem
  Namen steht „Stark in: …“ mit den zwei besten Themen, der Knopf
  „Themen“ klappt alle Werte auf.
- **Bewerber mit Profil:** Jede Bewerbung bringt zwei Stärken mit. Tim ist
  stark in Verkabelung und Hardware, Svenja in Routing und Windows & AD.
- **Kundentickets und Projekte je Thema:** Jedes Kundenticket hat ein Thema
  (z. B. „Netzwerk · WLAN“), die Erfolgschance hängt vom Wert in genau
  diesem Thema ab. Für dich selbst zählt dein Wissensstand im Thema.
  Projekte rechnen mit dem Thema ihrer Projektarbeit.
- **Mitarbeiter lernen durch Arbeit:** +2 im Thema für jedes geschaffte
  Kundenticket, +3 für ein fertiges Projekt (+1 extra, wenn es pünktlich
  ist) und alle 10 Arbeitstage Routinearbeit +1 im stärksten Thema. Ab
  Wert 70 geht es nur noch halb so schnell, 90 ist das Maximum. Der
  Feierabend zeigt, wer dazugelernt hat.
- **Zwei Arten Weiterbildung:** Zuerst den Fachbereich wählen, dann ein
  Thema (+10) oder den ganzen Fachbereich (+5 auf alle seine Themen,
  teurer und einen Tag länger).
- Bestehende Spielstände verlieren nichts: Die Themen starten beim
  bisherigen Fachbereichswert, frühere Weiterbildungen zählen weiter.
- **Handy:** Die App sucht wieder von selbst nach Updates, kurz nach dem
  Start und auch, wenn du sie aus dem Hintergrund zurückholst. Diese
  Version musst du dir noch einmal selbst über „Nach Updates suchen“
  holen, danach klappt es automatisch.
- Bitte PC und Handy beide auf 0.38 aktualisieren.

## 0.37

- **Themen je Fachbereich:** Die fünf Fachbereiche sind jetzt in 36 Themen
  unterteilt (Netzwerk 10, Sicherheit 8, Systeme 8, Wirtschaft 7,
  Datenbanken & SQL 3), zum Beispiel IPv4, Routing, Kryptografie, Linux
  oder SQL. Alle 4.000 Karteikarten, Quizfragen, Prüfungsszenarien und
  Projektarbeiten sind einem Thema zugeordnet.
- **Wissensstand je Thema:** Neben dem Wert je Fachbereich wird jetzt auch
  dein Wissensstand in jedem einzelnen Thema berechnet. Deine bisherigen
  Antworten zählen dabei automatisch mit.
- **Aufträge im Spiel verlangen Themen:** Alle 442 Aufträge und die
  Zwischenfälle setzen jetzt Wissen in einem bestimmten Thema voraus statt
  im ganzen Fachbereich. Fehlt Wissen, nennt das Ticket das Thema, und der
  Knopf „Karteikarten zu …“ öffnet genau die Karten dieses Themas.
- **Reinzoomen im Dashboard:** Ein Klick auf eine Zeile der Heatmap oder
  auf einen Ring bei „Fortschritt je Fachbereich“ öffnet die Karte
  „Themen · <Fachbereich>“ mit Aktivität und Wissensstand je Thema. Ein
  zweiter Klick oder „Schließen“ blendet sie wieder aus. Auf PC und Handy
  gleich.
- Die eigene Firma rechnet vorerst weiter mit den Fachbereichen; Mitarbeiter
  mit Themenwissen folgen in 0.38.
- Bitte PC und Handy beide auf 0.37 aktualisieren.

## 0.36

- **Drei neue Ausbaustufen** für deinen Gewerbehof unter Firma > Gebäude:
  Anbau Ost (20.000 €, 7 Arbeitsplätze), Halle Süd (34.000 €, 9 Plätze,
  drei Projekte gleichzeitig) und Halle Nord (48.000 €, 11 Plätze). Mehr
  Plätze bringen wie bisher mehr Kundentickets pro Tag.
- **Vier Sonderräume:** Ab Stufe 3 gibt es freie Flächen, die du in
  beliebiger Reihenfolge ausbaust. Jeder Raum kostet einmalig Geld, erhöht
  die Nebenkosten und bringt einen dauerhaften Vorteil:
  - Lager (ab Stufe 3): Material und Wareneinkauf 15 % günstiger. Die
    Mitbewerber zahlen weiter den normalen Preis.
  - Besprechungsraum (ab Stufe 3): 3 statt 2 Kundenanfragen pro Tag und
    +1 Kundenzufriedenheit je gewonnenem Auftrag.
  - Serverraum (ab Stufe 4): ein Projekt mehr gleichzeitig und nur noch
    halb so viele Rückschläge.
  - Schulungsraum (ab Stufe 5): Weiterbildungen 30 % günstiger und einen
    Tag kürzer.
- Neue Karte „Sonderräume“ im Reiter Gebäude, auf PC und Handy gleich.
- Die Büros heißen jetzt einheitlich Büro 2 bis Büro 5. In der kleinen
  Gebäudeansicht stehen die Schilder der unteren Reihe abwechselnd oben
  und unten, damit alle lesbar bleiben.
- **Android:** Die App wird nur noch für moderne 64-Bit-Handys gebaut
  (z. B. Samsung S24 und neuer). Die APK ist dadurch rund 58 MB statt
  143 MB groß.
- Bitte PC und Handy beide auf 0.36 aktualisieren, damit der Abgleich der
  Sonderräume klappt.

## 0.35.1

- **Fehlerbehebung PC:** Nach einem Wechsel von Grundfarbe oder Hintergrund
  konnten alte, abgelaufene Zeitgeber der vorherigen Oberfläche zufällig
  eine falsche Funktion aufrufen. Das hat den automatischen Starttest unter
  macOS (Apple-Chip) scheitern lassen, deshalb gab es kein Release 0.35.
  Solche Zeitgeber werden jetzt sofort entfernt, und der Starttest prüft
  das mit.
- Inhaltlich ist alles wie in 0.35 (Kundenprojekte, fünf neue Mitbewerber,
  Farbwechsel ohne Flackern).

## 0.35

- **Kundenprojekte:** Unter Firma gibt es den neuen Reiter „Projekte“. Alle
  drei Arbeitstage kommt eine Ausschreibung aus den 50 Testprojekten, sie
  gilt fünf Tage. Du kalkulierst ein Angebot (Projektarbeit plus Material,
  Gewinnzuschlag frei wählbar). Bei Zuschlag gibt es 30 % Anzahlung, den
  Rest bei Abschluss.
- **Team zusammenstellen:** Du teilst Mitarbeiter und dich selbst einem
  Projekt zu. Das Projekt läuft über mehrere Tage mit Fortschrittsbalken und
  Phasen (Erledigt, Jetzt, Danach). Es kann Rückschläge geben, und bei
  Verspätung zieht der Kunde etwas ab. Wer im Projekt arbeitet, macht keine
  Kundentickets und bringt keinen Routineumsatz.
- **Lernbonus:** Hast du ein Testprojekt im Lernbereich schon bearbeitet,
  arbeitet dein Team daran 20 % schneller.
- **Fünf neue Mitbewerber:** Neben Bitweiche bieten jetzt auch NetzWerk
  Kranich, Falkenstein IT-Security, Byteschmiede Hartmann & Söhne,
  Talheimer Systemhaus und CloudKontor Nord mit, jede Firma mit eigenem
  Preisstil. Das günstigste Angebot gewinnt. Unter Finanzen steht, gegen
  wen du verloren hast.
- Finanzen: neue Einnahmen „Projekte“ und Ausgaben „Projektmaterial“.
- **Fehlerbehebung PC:** Beim Wechsel von Grundfarbe oder Hintergrund
  flackert es nicht mehr. Die Oberfläche wird im Hintergrund neu aufgebaut
  und dann in einem Schritt getauscht.
- Bitte PC und Handy beide auf 0.35 aktualisieren, damit der Spielstand
  überall gleich gerechnet wird.

## 0.34

- **Angebote gegen Bitweiche:** Unter Firma gibt es vorne den neuen Reiter
  „Aufträge“. Jeden Arbeitstag kommen 2 Kundenanfragen (Talbahn und neue
  Kunden aus Talheim). Du wählst deinen Gewinnzuschlag (5 bis 30 %) und
  rechnest die Zuschlagskalkulation wie in der Prüfung. Stimmt die Rechnung
  und liegst du nicht über Bitweiche, gewinnst du den Auftrag und bekommst
  den Gewinn. Bitweiche ist unberechenbar: Manchmal gibt es einen
  Kampfpreis, manchmal sind sie ausgelastet und teuer. Nach jedem Angebot
  siehst du Bitweiches Preis.
- **Kundentickets verteilen:** Jeden Tag kommen Kundentickets aus fünf
  Fachbereichen. Du gibst sie an deine Mitarbeiter oder übernimmst selbst
  welche (mit deinem echten Wissensstand). Die Erfolgschance steht vorher
  in Prozent da, das Ergebnis gibt es beim Feierabend.
- Die Spielübersicht zeigt, was heute in der Firma noch offen ist.
- Nach der Gründung gibt es eigene Feierabend-Texte (kein Bitweiche-Gehalt
  mehr).
- Finanzen: neue Einnahmen „Angebote“ und „Kundentickets“.
- Bitte PC und Handy beide auf 0.34 aktualisieren, damit der Spielstand
  überall gleich gerechnet wird.

## 0.33

- **Eigenes Unternehmen (Grundgerüst):** Wer 25.000 € Spielgeld und 60
  Reputation hat und alle Aufträge bei Bitweiche erledigt hat, kann eine
  eigene IT-Firma gründen (Gründungskosten 15.000 €, Name frei wählbar).
  Danach gibt es kein Gehalt mehr, die Firma verdient selbst.
- **Neuer Unterpunkt „Firma“** im Spiel mit den Reitern Mitarbeiter,
  Bewerbungen, Gebäude und Finanzen.
- **Mitarbeiter:** Alle 5 Arbeitstage kommen 3 neue Bewerbungen, jede mit
  Werten in den fünf Fachbereichen, Schwerpunkt, Macke und Gehaltswunsch.
  Eingestellte Mitarbeiter bringen täglich Umsatz und kosten Gehalt. Tim und
  Svenja wollen nach einiger Zeit von Bitweiche wechseln. Weiterbildungen
  heben einen Fachbereich um 10 Punkte.
- **Eigenes Büro:** „Gewerbehof Am Stellwerk“ mit Großraum und Kaffeeecke,
  begehbar wie das Bitweiche-Büro. Die Mitarbeiter sitzen an ihren Plätzen.
  Für 12.000 € lässt sich ein zweites Büro mit drei weiteren Plätzen
  ausbauen.
- **Finanzen:** Umsatz, Gehälter und Nebenkosten pro Tag, dazu ein
  Kontoverlauf als Diagramm.
- Feierabend geht jetzt auch, wenn alle Aufträge erledigt sind.
- Bitte PC und Handy beide auf 0.33 aktualisieren, damit der Spielstand
  überall gleich gerechnet wird.

## 0.32

- **Viel mehr Aufträge im Lernspiel:** 442 Aufträge statt 46 und 50
  Zwischenfälle statt 10. Die Geschichte reicht jetzt bis Tag 100 und endet
  mit einem großen Finale: Jahreswartung aller Standorte, Audit und
  Rückblick.
- **Neue Ticket-Arten:** Bei der Wartung prüft man Punkte nach und hält
  fest, ob sie in Ordnung oder auffällig sind. Beim Austausch findet man die
  Ursache und baut das passende Ersatzteil ein. Fehlt das Teil im Lager,
  kann man es nachbestellen.
- **Neue Kunden:** Betriebswerkstatt (ab Tag 22), Verwaltung Lindenau (ab
  Tag 45) und Haltepunkt Birkenhain (ab Tag 66), jeweils mit eigenem
  Grundriss. Die Räume verändern sich, während man dort arbeitet.
- **Neue Kolleginnen und Kollegen:** Svenja, Lina, Aylin, Dr. Wendt, Marta
  und Paul. Horst (Tag 48) und Frank (Tag 80) gehen in Rente, beide
  bekommen eine Abschiedsfeier.
- **Ränge brauchen Arbeitstage:** Junior ab Tag 10, Fachkraft ab Tag 30,
  Senior ab Tag 60, zusätzlich zur Reputation. Pro Tag gibt es 3, 4, 4 bzw.
  5 Tickets.
- PC und Handy haben dieselben Inhalte und Beschriftungen.

## 0.31

- **Miete oder Kauf (Optionen > Spiel > Wohnungen).** Neben der bisherigen
  Einmalzahlung (weiterhin Standard) kann man Wohnungen jetzt mieten: Beim
  Umzug zahlt man nur eine Kaution (15 % des Kaufpreises), danach geht jeden
  Arbeitstag die Miete vom Spielgeld ab – Zweizimmer 60 €, Altbau 140 €,
  Loft 220 €. Die Miete erscheint beim Feierabend neben dem Gehalt, zu Hause
  und in der Spielübersicht. Die Kaution gibt es beim nächsten Umzug zurück.
  Der Schalter gilt für den nächsten Umzug; ein laufender Mietvertrag läuft
  bis dahin weiter. PC und Handy rechnen immer denselben Kontostand.
- **Farben wählbar (Optionen > Farben).** Sechs Grundfarben (Cyan/Pink,
  Lila/Magenta, Blau/Türkis, Grün/Lime, Orange/Gelb, Rot/Pink) für Buttons,
  Ringe, Balken und Banner, dazu sechs Hintergründe (Violett, Nachtblau,
  Tannengrün, Aubergine, Anthrazit, Schwarz). Beides lässt sich frei
  kombinieren, wirkt sofort und gilt nur für das jeweilige Gerät. Die
  Farben der Fachbereiche und von Erfolg, Fehler und Warnung bleiben gleich.
- **Bessere Lesbarkeit:** Alle Farbkombinationen erfüllen jetzt den
  Kontrast-Standard für gut lesbaren Text (WCAG AA). Dafür sind die kleinen
  Hinweistexte etwas heller und einige Button-Verläufe etwas dunkler.

## 0.30

- **Feierabend heißt jetzt nach Hause gehen.** Wer alle Tickets erledigt hat,
  macht an der Eingangstür des Büros (oder über „Feierabend machen“)
  Feierabend und steht dann in der eigenen Wohnung. Dort erscheinen das
  Gehalt und ein kurzer Text zum Tag. An der Wohnungstür geht es „Zur
  Arbeit“, am Schreibtisch zum Lernen, im Bett wird geschlafen.
- **Eigene Wohnung (Spiel > Zuhause, am Handy „Zuhause öffnen“).** Man
  startet im Einzimmer-Apartment mit Matratze und Umzugskartons. Unter
  „Einrichten“ kauft man im Möbelhaus 23 Möbel mit Spielgeld, stellt sie
  per Klick oder Tipp auf, dreht, verschiebt, packt sie in den Karton oder
  verkauft sie zum halben Preis. Möbel dürfen nicht über Wände ragen, sich
  nicht überlappen und keine Tür versperren, ein Teppich darf unter Möbeln
  liegen. Je Raum lassen sich Bodenbelag und Bodenfarbe wählen. Später kann
  man in eine Zweizimmer-Wohnung (2.500 €), einen Altbau (6.000 €) oder ein
  Loft mit Dachterrasse (12.000 €) umziehen. Bezahlt wird einmalig, eine
  Miete gibt es vorerst nicht.
- **Kundenaufträge vor Ort (Spiel > Kunde, am Handy „Kunde öffnen“).** Der
  Bahnhof Talheim ist begehbar, mit Bahnsteig und Zug, Service-Center,
  Leitstelle, Technikraum und dem IT-Büro der Talbahn. Petra Lindner und
  Horst Grabowski arbeiten dort, ihre Aufträge nimmt man vor Ort an, oft
  direkt am kaputten Gerät. In der Ticketliste steht dazu „beim Kunden“.
  Ab Arbeitstag 12 kommt der neue Bahnhof Talheim-Nord dazu: erst eine
  Baustelle mit Absperrband, mit jedem erledigten Auftrag fertiger, zur
  Eröffnung mit Wimpeln.
- **Zwischenfälle:** Ab Arbeitstag 2 kann morgens ein Zwischenfall
  dazukommen, zum Beispiel ein Anruf vom falschen „Microsoft-Support“, ein
  Stromausfall mit piepender USV oder eine Kaffeemaschine, die ins
  Firmennetz will. Höchstens einer pro Tag, er zählt nicht zu den normalen
  Tickets, und jeder kommt nur einmal. PC und Handy zeigen denselben.
- **Neue Gesichter:** Tim (Azubi im Helpdesk) und Karin Albers
  (Datenschutzbeauftragte) im Büro, beim Kunden Horst Grabowski aus der
  Leitstelle. Alle reagieren jetzt mit einem kurzen Satz auf gelöste
  Aufträge.
- **Geschichte um Talheim-Nord** (Arbeitstag 12 bis 16) mit einer Szene zu
  jedem Morgen und 12 neuen Aufträgen: Technik bestellen, Netzwerkschrank
  mit Geräten aus dem Lager bestücken, Kassen-PC, IP-Plan, Kamera-
  Speicherdauer, SLA, SQL-Auswertung der Fahrgastzahlen und die Abnahme.
- **Rack-Geräte aus dem Lager:** Bestellungen können jetzt auch USV, Switch
  und Patchpanel liefern. Im Serverschrank steht bei jedem Gerät, ob es
  bereitliegt oder aus dem Lager kommt.
- **Falsche Bestellungen werden trotzdem geliefert.** Die falsche Ware kommt
  ins Lager, und bei ihrer Ankunft meldet sich Rainer mit dem Zwischenfall
  „Falsche Ware“. Er muss behoben werden und kommt jeden Tag wieder, bis
  die Ware reklamiert und zurückgeschickt ist. Das kostet 40 €
  Rücksendung, und die Bestellung, die danach wiederkommt, bringt keinen
  Spar-Bonus mehr.

## 0.29

- **Neu im Spiel: Terminal.** Linux-Server und Windows-Arbeitsplätze werden
  in einem nachgebauten Terminal eingerichtet. Zu jedem Schritt wählst du
  einen Befehl und siehst eine echte Ausgabe. Ein falscher Befehl liefert
  eine Fehlermeldung, dann darfst du es noch einmal versuchen. Ein Fehlgriff
  ist erlaubt. Gefährliche Befehle wie `chmod 777` oder eine überschriebene
  fstab führt das Spiel nicht aus, sie kosten aber Sicherheitsbewusstsein.
- **Neu im Spiel: Fehlersuche.** Zu einem Symptom gibt es mehrere mögliche
  Prüfungen, die Ergebnisse landen im Notizblock. Am Ende wählst du Ursache
  und Maßnahme. Wer systematisch vorgeht und mit wenigen Prüfungen auskommt,
  bekommt zusätzlich Zuverlässigkeit. Unsichere Maßnahmen kosten
  Sicherheitsbewusstsein.
- **Ersatzteile aus dem Lager:** Zwei Fehlersuchen enden mit einem Tausch.
  Die SSDs für die Fahrkartenautomaten und das Netzteil aus der
  Nachbestellung kommen dafür aus dem Lager.
- **9 neue Aufträge** ab Arbeitstag 9: Datenplatte für den Fahrplanserver,
  Benutzer und Rechte fürs Service-Center, Windows-Arbeitsplatz für die
  Leitstelle per PowerShell, Webserver mit Firewall für die
  Fahrplanauskunft, nächtliche Sicherung der Automaten-Datenbank sowie
  Fehlersuche an Kassen-PC, Fahrkartenautomat, Verwaltungs-PC und
  Leitstellen-PC.

## 0.28

- **Neu im Spiel: Serverschrank bestücken.** Der Schrank wird in
  Höheneinheiten angezeigt, HE 1 ist unten. Gerät antippen, dann die
  Höheneinheit – fertig. Beim Einreichen prüft das Spiel Platz, Gewicht
  (schwere Geräte und die USV nach unten), Strom mit 20 % USV-Reserve,
  Kühlung, ob jedes Patchpanel direkt am Switch sitzt und was der Auftrag
  verlangt (zum Beispiel Ports oder freie HE). Jede passende Belegung zählt.
- **Neu im Spiel: Formulare.** IP-Pläne (gleich große Netze und VLSM), RAID-
  Kapazität, Angebotskalkulation bis zum Bruttopreis und Kauf gegen Leasing
  werden in Eingabefelder eingetragen. Die richtigen Werte rechnen dieselben
  Funktionen aus wie der Subnetz- und der RAID-Rechner. Die Eingabe ist
  tolerant: „/26“ und „255.255.255.192“ gelten beide, Komma oder Punkt ist
  egal. Nach dem Einreichen ist jedes Feld grün oder rot, bei Rot steht der
  richtige Wert daneben.
- **8 neue Aufträge** ab Arbeitstag 6: Netzwerkschrank für die Leitstelle,
  Serverschrank im Serverraum erweitern, Netzwerkschrank fürs
  Service-Center, zwei IP-Pläne für die Talbahn, RAID 6 für den Dateiserver,
  Angebot für die Leitstellen-Arbeitsplätze und Kauf oder Leasing für die
  neuen Server.

## 0.27

- **Neu im Spiel: PC zusammenbauen.** In der IT-Werkstatt liegen Mainboard,
  CPU, Arbeitsspeicher, SSD, Netzteil, Gehäuse und manchmal eine
  Grafikkarte bereit – darunter auch Teile, die nicht passen. Steckplatz
  antippen, Bauteil antippen, fertig. Beim Einreichen prüft das Spiel Sockel,
  DDR4/DDR5, Anzahl der RAM-Module, Formfaktor, M.2, Netzteil-Leistung und
  Bildausgabe und erklärt jedes Problem in einem Satz. Jede passende
  Zusammenstellung zählt.
- **Neu im Spiel: Bestellungen.** Angebote von drei Händlern mit Preis und
  Lieferzeit, dazu Bedarf, Budget und Frist. Du stellst den Warenkorb
  zusammen, Summe und Lieferzeit rechnet das Spiel mit. Wer sparsam richtig
  bestellt, bekommt einen Bonus.
- **Lieferzeit und Lager:** Bestellte Ware kommt erst nach ein paar
  Arbeitstagen an. Aufträge, die die Ware brauchen (zum Beispiel der
  Leitstellen-PC mit dem bestellten Arbeitsspeicher), erscheinen erst dann.
  Wartest du nur noch auf Lieferungen, kannst du den Arbeitstag trotzdem
  beenden.
- **Neuer Lagerflügel mit neuem Kollegen:** Das Bürogebäude hat rechts ein
  Lager mit Hochregalen, Paletten, Hubwagen und Rolltor zur Laderampe. Dort
  arbeitet Rainer Voss, Lagerist. Ein Tipp auf das Lager zeigt, was
  unterwegs ist, was auf Lager liegt und was ausgeliefert wurde.
- **7 neue Aufträge** rund um PC-Bau und Beschaffung: Service-Center-PC,
  Arbeitsspeicher und PC für die Leitstelle, Netzteile nach Meldebestand,
  Grafik-Arbeitsplatz für die Fahrplanung, Notebook für die Chefin und
  Ersatz-SSDs für die Fahrkartenautomaten.

## 0.26

- **Neu: das Lernspiel.** Deine Spielfigur arbeitet bei der Bitweiche
  IT-Service GmbH, die die IT der Talbahn Nordlicht AG betreut. Jeden
  Arbeitstag kommen Tickets von Kolleginnen, Kollegen und dem Kunden:
  Phishing-Verdacht, Arbeitsspeicher für neue Kassen-PCs, Subnetz fürs
  Service-Center, USV für die Leitstelle, RAID, Passwörter, Angebot, SQL und
  Backup-Beratung. Am PC über „Spiel“ in der Seitenleiste, auf dem Handy
  über „Spiel“ in der unteren Leiste.
- **Gekoppelt an deinen Lernfortschritt:** Aus deinen Antworten in
  Karteikarten und Prüfungstrainer wird je Fachbereich ein Wissensstand
  berechnet. Fehlt dir für ein Ticket noch Wissen, bekommst du einen Hinweis
  und kannst trotzdem loslegen – ein Fehler kostet dann aber doppelt.
  Nach jedem Ticket gibt es passende Karteikarten und Fragen zum Weiterlernen.
- **Spielfigur, Reputation und Spielgeld:** Name und Aussehen frei wählbar,
  Reputation in vier Bereichen (Fachkompetenz, Zuverlässigkeit,
  Kundenzufriedenheit, Sicherheitsbewusstsein), Rang von Azubi-Niveau bis
  Senior, Gehalt pro Arbeitstag und ein erstes Sparziel für das spätere
  eigene Unternehmen. Ohne Hilfe gelöste Tickets bringen einen Bonus.
- **Das Bürogebäude von oben:** Chefbüro, Kundenberatung, Verwaltung,
  Helpdesk, IT-Werkstatt und Serverraum mit Flur, Eingang, Wänden, Türen und
  Fenstern, eingerichtet mit Schreibtischen, Pflanzen, Regalen, Server-Racks,
  USV, Werkbank und mehr. Die Kolleginnen und Kollegen sitzen an ihren
  Plätzen, deine Spielfigur steht im Flur. Ein Tipp auf einen Raum zeigt, wer
  dort sitzt und was zu tun ist.
- **Abgleich PC und Handy:** Der Spielstand wird wie der Lernstand
  abgeglichen. Wichtig: Beide Geräte sollten auf 0.26 sein, bevor du auf
  beiden spielst.
- **Büro in groß, Figur steuern:** Unter „Spiel“ gibt es den Unterpunkt
  „Büro“ (am PC in der Seitenleiste, auf dem Handy über „Büro öffnen“). Dort
  läuft deine Figur per Klick oder Tipp durch Flur und Türen, am PC auch mit
  den Pfeiltasten. Wer einen Auftrag für dich hat, trägt ein grünes „!“ – bei
  der Person angekommen, nimmst du das Ticket direkt an. Die Farbe des Kreises
  um deine Figur wählst du selbst („Figur bearbeiten“ → „Kreis im Büro“).
- **Gleiche Namen auf PC und Handy:** Die Menüpunkte heißen jetzt überall
  „Rechner“, „Spiel“, „Fortschritt“ und „Optionen“ (nur „Dashboard“ am PC
  und „Start“ auf dem Handy bleiben verschieden).
- **Eigener Knopf „Spielstand zurücksetzen“** unter „Optionen“. „Alle
  Lerndaten löschen“ und „Historie löschen“ lassen den Spielstand stehen.

## 0.25

- **Viel mehr Lernstoff:** 4.000 statt 368 Aufgaben – 1.400 Karteikarten,
  2.000 Quizfragen, 250 AP1-Szenarien, 300 AP2-Szenarien und 50 Testprojekte,
  verteilt auf alle Fachbereiche und alle Themenblöcke. Darunter 583 neue
  Rechenaufgaben (Zahlensysteme, Zweierkomplement, Subnetting, VLSM,
  IPv6-Präfixe, RAID 5/6/50/60, chmod und umask, VM-Dimensionierung,
  SSD-Lebensdauer, Verfügbarkeit, Übertragungsdauer, Passwortstärke,
  Umsatzsteuer, Bezugs- und Handelskalkulation, Zuschlagskalkulation,
  Skonto-Zinssatz, Deckungsbeitrag, Kennzahlen, Earned Value, Abschreibung,
  TCO, Lizenzierung, Kostenvergleich, Barwert, Kreditzinsen, MTBF und MTTR,
  Netzplan und Puffer, Speicherbedarf von Bildern und Audio, Netzteil und
  USV, Stromkosten, IOPS, Kapitalwert, Risikowert, SQL-Abfragen, Skripte und
  cron-Zeiten) mit Rechenweg.
- **Neuer Fachbereich Datenbanken:** „Datenbanken & SQL“ ist jetzt ein eigener
  Fachbereich mit eigenem Kartenstapel, eigenem Filter, eigenem Menüpunkt und
  einem orangefarbenen Fortschrittsring am PC und auf dem Handy. Die Aufgaben
  reichen vom ER-Modell über Normalisierung, SQL-Abfragen, Rechte und
  Transaktionen bis zu Backup, Replikation und NoSQL. Die bisherigen
  SQL-Aufgaben bleiben in ihren Fachbereichen, der Lernfortschritt bleibt
  erhalten.
- **Prüfungsnahe Situationsaufgaben:** Viele Karten und Quizfragen schildern
  jetzt einen Fall aus dem Betriebsalltag (Kundengespräch, Ticket, Störung,
  Vertragsproblem) statt nur eine Definition abzufragen. Die neuen AP1- und
  AP2-Szenarien verbinden in jeder Aufgabe eine Rechnung mit Technik,
  Sicherheit, Recht oder Projektablauf – so wie in der echten Prüfung.
- **Mehr für die AP1:** Viele neue Aufgaben zum Einrichten eines
  IT-Arbeitsplatzes (Hardware, Ergonomie, Installation, Netzanbindung,
  Fehlersuche, Arbeitsplatzsicherheit, Kundenauftrag bis zur Abnahme) und
  erstmals Pseudocode, Struktogramm, Programmablaufplan und
  Tabellenkalkulation, auch mit Aufgaben zum Nachverfolgen von Programmen
  und Formeln.
- **Mehr für die AP2:** Konfigurations- und Logausschnitte zum Deuten
  (ACL, Routing, STP, VPN, Firewall, SIEM, Windows-Ereignisse), Skripte mit
  PowerShell und Bash, SQL-Abfragen, Ansible, Kubernetes und Proxmox, PKI im
  Betrieb, Incident Response sowie Beratung, Verträge und Projektmanagement
  auf Abschlussniveau.
- **Vertiefung Netzwerk und Sicherheit:** u.a. IPv6, OSPF und BGP, WLAN-Planung,
  DNS und DHCP im Detail, NAT und QoS, Kryptografie und Zertifikate,
  DSGVO-Praxisfälle, Angriffe und Abwehr im Netz und im Web.
- **Vertiefung Systeme:** u.a. Linux- und Windows-Administration,
  Active Directory, Virtualisierung und Container, Cloud, Storage und Backup,
  dazu HTTP/REST, Loadbalancer, Cloud-Sicherheit und IT-Service-Management.
- **Vertiefung Wirtschaft:** u.a. Vertragsrecht und Kaufvertragsstörungen,
  Arbeits- und Sozialrecht, Ausbildungsrecht, Rechtsformen, Kosten- und
  Leistungsrechnung, Investition und Finanzierung, Marketing und
  Kundenberatung, Projektmanagement, ISMS, NIS2 und Datenschutzpraxis.
- **Szenarien und Testprojekte mit Suche, Filter und Seiten:** Die Listen
  lassen sich nach Titel oder Nummer durchsuchen und nach Thema,
  Fachbereich, Schwierigkeit und Status (offen/bearbeitet) filtern.
  Bearbeitete Aufgaben tragen einen Haken. „Nächstes Szenario“ bleibt
  innerhalb der gewählten Auswahl. Gilt für PC und Handy.
- **Stabiler bei großen Datenmengen:** Die Listen zeigen seitenweise
  höchstens 15 Einträge. Vorher konnte das Programm bei sehr vielen
  Szenarien beim Start abstürzen. Ein neuer Belastungstest
  (`test_grosse_datenmengen.py`) prüft das Programm mit über 7.000 Aufgaben.
- **Angenehmere Schrift am PC:** Längere Texte (Fragen, Antwortmöglichkeiten,
  Rückmeldungen, Aufgabenstellungen und Eingabefelder) erscheinen jetzt in
  einem leicht gedämpften Weiß statt in grellem Hellweiß. Dadurch wirken sie
  ruhiger und schärfer. Überschriften bleiben unverändert hell.
- **Kalender:** Die Pfeile zum Blättern zwischen den Monaten sind jetzt am
  PC und in der Handy-App Cyan und leuchten beim Drücken im Grün der Kachel
  „Fortschritt je Fachbereich“ auf.
- **Neues Programm-Icon:** Desktop-Verknüpfung, Fensterleiste und das Icon
  der Handy-App zeigen jetzt das Logo aus der Seitenleiste – den Ring mit
  Farbverlauf von Cyan nach Pink und dem leuchtenden Punkt in der Mitte.

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
