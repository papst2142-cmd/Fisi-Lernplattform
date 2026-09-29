# Änderungen

Neueste Version oben. Jede Version bekommt vor dem Release einen eigenen
Abschnitt `## <Version>` – dieser Text erscheint im GitHub-Release und im
Update-Fenster des Programms.

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
