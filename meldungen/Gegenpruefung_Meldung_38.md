# Gegenpruefung Meldung 38 (Strang-Karte 0.63.2, Fassung 2 mit Frage 1 zum Warntext)

Geprueft: `bau_0.63.2/meldungen/Meldung_38_Strang_Karte.md` in der **ueberarbeiteten Fassung** (109 Zeilen; neue Frage 1/1b zum Warntext, E1-6, E1-7, neuer Kopfblock). An der Meldung habe ich nichts geaendert.
Grundlagen:
- Weisungen: Ablauf Grossauftraege (Abschn. 1-4, 7), Meldungszweig, Weisung zu Meldung 37 (Abschn. 5 und 7).
- Plan 0.63.2 (Welle 3b) und Plan-Nachtrag (Abschn. 2 und 5.2).
- Bau: `integration/PROTOKOLL.md`, `REGELN_BAU_0.63.2.md`, `gp3_fg81_m37.md`, `gp_n5_nacharbeit.md` (M-B, M-C), Job-Log `ci_38461199297_rest_joblog.txt`, `WARTELOG.md`, `werkzeug/`.
- Repository: `build.yml` und alle Workflows aller `origin/*`-Zweige, Git-Staende, `gh run view 38466618774`.

## Urteil: **lieferbar NEIN** (1 S, 8 M, 11 L)
Nach Behebung von S-1 und M-1 bis M-8 ist die Meldung lieferbar. Eine neue Runde ist nicht noetig, wenn nur die vorgeschlagenen Saetze eingesetzt werden.

**Oeffentlich publizierbar: ja.**
- Keine E-Mail-Adresse, keine Zugangsdaten, keine Pfade unter `/home`, `/root`, `/tmp` oder `/mnt`.
- Selbst gesucht nach `@`, `/home`, `/root`, `/tmp`, `/mnt`, `token`, `passw`, `secret`, `ghp_`: 0 Treffer.
- Es stehen nur relative Projektpfade darin.

**Format:**
- Zeile 1 und 2 (`AN:`, `ENTSCHEIDUNG NÖTIG:`) sind da.
- Der Kopfblock hat 9 Zeilen (erlaubt sind 10) und enthaelt Blockiert, Entscheidungen und E1.
- Die Tabelle E1 hat die Spalten Nr, Entscheidung, Begruendung und Beleg.
- Karte und Belegzeile sind da.
- In Ordnung bis auf die L-Punkte.

## Selbst nachgeprueft und richtig (belegt)
- **E1-5 Workflow-Ausloeser:**
  - Geprueft: alle 68 `origin/*`-Zweige mit 27 verschiedenen Workflow-Dateistaenden (`git ls-tree`/`cat-file`).
  - `build.yml` (10 Fassungen): `push: tags v*`, `workflow_dispatch`, `workflow_call`.
  - `release.yml` (4 Fassungen): nur `push: branches [main]`.
  - Mess-, Probe-, Untersuchungs- und Prototyp-Workflows: nur ihr eigener Zweig.
  - Zweig `meldungen` (Arbeitsbaum `wt_meldungen`): noch kein Commit, nur `README.md` und `meldungen/`, kein `.github`.
  - Die Aussage ist richtig (nur L-3).
- **E1-7 Lauf 38466618774** (`gh run view`, 13.10. ~21:00 UTC):
  - "Installer bauen", `workflow_dispatch`, Zweig `version-0632-s1c2`, headSha `7a32651120b8…`.
  - Status `in_progress`: macos-arm64, linux, windows und Tests Linux (spiel) gruen; lang, rest, android, Tests Windows und macos-intel laufen noch.
  - `7a32651` aendert nur `app_gui.py` und `test_ansichten_breite.py` (ungeschuetzt). B-4b braucht also kein FG-96, FG-96 bleibt fuer Frage 2 frei.
- **Frage 1 gegen `gp3_fg81_m37.md`:**
  - Urteil "nicht abnahmereif" stimmt.
  - Wortlaut byte-gleich, 234/234 Tests gruen, 15 Kontrollfehler rot (vom Bauer berichtet, auch im PROTOKOLL).
  - Saetze 1-4 und 6-8 sind richtig.
  - Satz 5 ist falsch (M1), Ursache `fisi_sync.py:633`.
  - f7 ist der einzige Fall, in dem Satz 5 stimmt.
  - Die Richtung stimmt: es kommt mehr zurueck, nichts geht verloren.
  - Dialog: 1280 px gebraucht (`dd0c2a0`: 1126 px). Bei 1366×768 fehlen die Saetze 5-8. Schon `dd0c2a0` war abgeschnitten.
  - Handy: nur gerechnet (etwa 56 %, 47 %, mit Systemschrift 25-39 %). Windows und macOS nicht geprueft.
  - Ausnahmen siehe L-9 und L-10.
- **Zahlen:**
  - 1279 s steht im Job-Log (Zeile 2666).
  - `timeout-minutes: 30` steht in `build.yml` Zeile 271.
  - 1430/1800 s und 21 % stehen in M-B.
  - Container 2034 s steht im PROTOKOLL.
  - 10 integrierte Straenge auf `e0f9c7e` = `origin/version-0632`.
  - CI 38461199297 ist nur bei "Tests Linux (rest)" rot.
- **Planabhaengigkeiten:**
  - `app_gui.py` und `mobile/src/main.py` sind nicht geschuetzt (REGELN Z. 18).
  - Die Karte stimmt mit Nachtrag 5.2 ueberein bei den Wellenreihenfolgen und bei N6, N7, N8, N11, N15, N16 und N14.
- **Stufen:** Frage 1 und Frage 2 sind richtig als E2 eingestuft. FG-96 ist die naechste freie Nummer.

## Befunde

### S (schwer)

**S-1 Frage 2: Die Reserve ist falsch eingeordnet. Mit N5 auf dem Integrationsstand wird die Grenze sehr wahrscheinlich ueberschritten, und (a) kaeme zu spaet.**
- Die 1430 s aus M-B wurden auf dem N5-Zweig gemessen (`68c268c`, Basis ohne Welle 3b).
- Auf `e0f9c7e` braucht "rest" schon 1279 s Testzeit. Der ganze Job brauchte 1323 s (20:14:16 bis 20:36:20, Job-Log).
- Die N5-Datei braucht auf GitHub 399 bis 550 s (M-B).
- Zusammen sind das rund 1830 s Testzeit plus rund 40 s Einrichtung, also mehr als 1800 s, schon ohne Schwankung (M-B: bis +40 %).
- "21 % Reserve" und "Risiko" bei (c) wirken beruhigend. Zu erwarten ist aber ein Abbruch schon im ersten Lauf nach dem N5-Merge.
- (a) soll "zusammen mit N10" kommen. N10 gehoert zu Welle 3e, N5 zu Welle 3c. Der neue Teil kaeme also erst nach dem N5-Merge. Das widerspricht dem Satz "betrifft den Merge von N5".
- **Korrektur:** "Auf `e0f9c7e` lief der Teil 1279 s (Job 1323 s von 1800 s). Die N5-Datei braucht auf GitHub allein 400 bis 550 s (M-B). Nach dem N5-Merge laege der Job bei rund 1850 s, ueber der Grenze. (a) muss **vor dem N5-Merge** im Integrationsstand sein, als eigener kleiner Commit mit FG-96, nicht mit N10. (c) fuehrt fast sicher zu einem roten Lauf." Zu (b) ergaenzen: "45 min reichen fuer N5, aber nicht sicher fuer N8/N9 dazu."

### M (mittel)

**M-1 E1-3 und Karte "Fix 3b: wartet auf nichts (E1)": Das faellt unter "Nie E1: roter Test".**
- E1-3 ist ausserdem keine eigene Entscheidung. Es ist die Pflichtfolge aus dem Katalog (Abschn. 2, Zeile 3).
- Die Art des Fixes ist noch offen:
  - gleich strenge Testanpassung mit Kontrollfehler: E1 Nr. 4;
  - Lockerung (z. B. Toleranz fuer die Runner-Schrift): E2;
  - Layout bei Sehr gross: E3 (Optik);
  - geschuetzte Datei: braucht eine FG.
- **Korrektur:** E1-3 aus der Tabelle nehmen. In den Kopfblock schreiben: "Gemeldet nach Katalog Abschn. 2: roter Testjob, kein neuer Lauf, Ursache wird geklaert." In der Karte bei Fix 3b: "Diagnose ohne Warten; die Art des Fixes bestimmt die Stufe; Meldung vor dem Merge."

**M-2 E1-4 (Welle 3c vor dem Abschluss von Welle 3b) liegt nicht eindeutig "innerhalb der freigegebenen Abhaengigkeiten" (E1 Nr. 5).**
- Plan und Nachtrag 5.2 setzen Welle 3c nach Welle 3b.
- Zu Welle 3b gehoeren S1c2 (noch nicht gemergt) und ein gruener CI-Lauf (rot).
- Folge: Bis Fix 3b bleibt jeder 3c-Lauf rot, mit N5 kommt der Zeitabbruch dazu (S-1).
- Weisung: "Im Zweifel E2."
- **Korrektur:** als E2-Frage stellen, Empfehlung "N1 bis N4 jetzt, N5 erst nach Fix 3b und FG-96". Oder die Planstelle nennen, die das Vorziehen deckt.

**M-3 Karte: N9 haengt an S1c2.**
- Laut Nachtrag 2 zweigt N9 nach Welle 3b ab, inklusive S1c2. Laut Abschn. 3 Nr. 25-27 baut N9 "auf D2/Z3 (S1c1, S1c2)" auf.
- N9 wurde ab `e0f9c7e` begonnen, also ohne S1c2.
- In der Karte hat N9 keine Abhaengigkeit und steht unter "Unabhaengig".
- **Korrektur:** Zeile 1 der Karte "Welle 1 bis 3b ohne S1c2". Bei N9: "Merge erst nach S1c2 (neu aufsetzen)". Den abweichenden Abzweig offen nennen.

**M-4 Karte: Welle 4 wartet auf das Ende von Welle 3e.**
- Nachtrag: "B-B-06 bleibt der letzte Merge vor S6a."
- In der Karte steht bei S6a nur "bereit". So wirkt der Merge frei.
- **Korrektur:** Bei Welle 4 in "wartet auf" eintragen: "S6a: Wellen 3c bis 3e (letzter Merge N13/B-B-06)".

**M-5 Frage 1b: `version-0632-s6b` liegt schon auf GitHub.**
- `origin/version-0632-s6b` = `cad90c0`. Das ist die FG-81-Fassung von 18:05 UTC, vor Weisung 35, nicht abgenommen.
- `d54397f` baut darauf auf (`merge-base --is-ancestor`, belegt).
- "Hochladen" klingt, als waere der Zweig neu.
- Der Dialog-Zweig heisst laut PROTOKOLL `version-0632-dialog`, nicht `version-0632-s6b`.
- **Korrektur:** "Der Zweig liegt mit einem aelteren Stand (`cad90c0`) schon auf GitHub; der Push waere ein normaler Vorlauf ohne Force. Der Dialog liegt auf `version-0632-dialog` und muesste vorher auf S6b gebracht werden."

**M-6 N5: offene Chat-Frage M-C und Fotos F30 fehlen.**
- `gp_n5_nacharbeit.md` M-C: Chat soll entscheiden, ob "Normal ab 1360 unveraendert" nur fuer Inter gilt. Dazu kommt Nicos Foto-Abnahme (F30).
- Nachtrag: Die Design-Teile von N5 kommen erst nach der Foto-Abnahme.
- Beides fehlt in der Karte, in "Was nur auf eine Entscheidung wartet" und in den Fragen.
- **Korrektur:** als Frage aufnehmen, oder in der Karte bei N5 eintragen: "M-C (Chat, Meldung NN), Fotos F30 (Nico, Meldung 39), Frage 2".

**M-7 (neu) E1-6 rollbarer Dialog: Uebernahme ist eine Umfangsaenderung (E2) und Optik (E3), nicht E1.**
- Die gp3 sagt ausdruecklich: "Chat entscheidet, ob gekuerzt oder anders angezeigt wird."
- Ein neuer Dialog ersetzt `messagebox.askyesno` und `confirm` am Handy. Das ist eine neue Funktion ausserhalb des Plans. Weisung Abschn. 1: Umfangsaenderungen sind E2.
- Ist "fuer PC" auf allen Systemen gemeint, aendert sich auch das Aussehen unter Windows und macOS. Dort ist es heute das System-Meldungsfenster, und laut gp3 passt der Text dort vermutlich.
- Frage 1b (a) setzt den Dialog als gegeben voraus ("zusammen mit dem rollbaren Dialog").
- Der Vorbau als bereitstehende Arbeit ist in Ordnung, ohne Push und ohne Merge.
- Der Beleg `bau_0.63.2/dialog_warntext/` existiert noch nicht.
- **Korrektur:**
  - E1-6 umformulieren: "Vorbereitet, nicht hochgeladen, nicht gemergt."
  - In Frage 1 eine Teilfrage ergaenzen: "Anzeige: (a) rollbarer Dialog PC/Handy (Umfang E2, Aussehen Nico E3), nur Linux oder alle Systeme?, (b) nur kuerzen."
  - Frage 1b davon abhaengig machen.

**M-8 (neu) Regelverstoss im Container wird nicht genannt.**
- PROTOKOLL 21:10 und `s1c2/ergebnis_b4b_bewertung.md` Z. 114: Der S1c2-Bauer hat `faketime` per apt installiert. REGELN Z. 39 sagt: "Keine Pakete installieren". Das Paket ist nicht entfernt.
- Der Container ist zugleich die Umgebung von Merge-Tor und Container-Laeufen.
- **Korrektur:** eine Zeile in den Kopfblock oder unter E1, z. B.: "Regelverstoss: `faketime` per apt im Container installiert (S1c2-Bauer, offen gemeldet); Wirkung auf die Tor-Laeufe: keine, weil … / wird geprueft; Entfernen oder Belassen entscheidest du." Die Entscheidung ist keine E1.

### L (leicht)
- **L-1** E1-1: "Katalog Nr. 6" ist falsch. Gemeint ist Abschn. 1, E1 Nr. 6. Dazu offen sagen, dass Weisung 37 Abschn. 7 die Fotos in Meldung 38 legte und die neuere Ablauf-Weisung dort die Karte vorsieht.
- **L-2** Die Zeitgrenze gilt fuer den ganzen Job (1323 s), nicht fuer die Testsumme (1279 s). Beide Zahlen nennen.
- **L-3** E1-5:
  - `build.yml` hat auch `workflow_call` (nur aus `release.yml`, also nur ueber `main`).
  - Die nach Meldungszweig Bedingung 3 verlangte Suchzeile vor dem Push fehlt (gesucht nach Zugangsdaten, E-Mail und Pfaden, Ergebnis in einer Zeile).
- **L-4** Der Beleg zu E1-2 (`testplaene/`) existiert noch nicht. "2 Testplan-Pruefer" ist nur berichtet.
- **L-5** Kopfblock Zeile 1:
  - "was bereitsteht" fehlt, z. B. "Bereit: N1-N4, N12, N13, S5b, B-9b (Fotos), S6a".
  - Die laufende Gegenpruefung `gp_s1c2_b4b` fehlt in der Aufzaehlung.
- **L-6** Glossar:
  - "Merge-Tor" und "E1/E2/E3" stammen aus Chats eigener Weisung und sind keine neuen Kuerzel.
  - Ungeklaert sind dagegen "Differenzlauf N4+N5", "FG-94 3/3", "Container-ibus-Beleg wird nach S5b echt" und "T-a/b/c".
- **L-7** Karte N15: N-h braucht zusaetzlich Nicos Foto-Abnahme (mit B-E-03).
- **L-8** Frage 2 (a) "deutlich unter der Grenze" mit Zahlen belegen. Laut Job-Log: `test_ansichten_breite` 159 s, `test_rechner_seite_breite` 35 s, N5-Datei 400-550 s. Damit braucht "breite" rund 600-750 s und "rest" rund 1090 s.
- **L-9 (neu)** Frage 1, Anzeige bei 1920×1080: Laut gp3 fehlt dort schon das Ende von Satz 6 ("solche werden aufgehoben") und dazu die Saetze 7 und 8. Also: "bei 1920×1080 das Ende von Satz 6 und die Saetze 7 und 8".
- **L-10 (neu)** Frage 1, Abläufe:
  - Die gp3 nennt Satz 5 falsch in **h7, h7h, h8 und h9**. h8 zaehlt sie nur als Lesart-Hinweis; das so schreiben, statt h8 wegzulassen.
  - Es sind 14 eigene Abläufe (h1-h13 und h7h), nicht 13.
  - (b) "dass mehr geloescht wird" als "vermutet" kennzeichnen.
- **L-11 (neu)** Form:
  - `ENTSCHEIDUNG NÖTIG` nennt "2 Fragen", es sind aber 3 Entscheidungen (1, 1b, 2). Frage 1b fehlt auch im Kopfblock (Zeile 2).
  - E1-5 steht nach E1-7, und E1-7 ist nur als Lauf-Nummer belegt. Ergaenzen: "laeuft, Ergebnis folgt; 4 von 9 Jobs gruen".
  - In die Belegzeile gehoeren noch Lauf 38466618774, S1c2 `7a32651` und der Dialog-Zweig.

## Verstaendlichkeit fuer Chat
Die Meldung ist gut lesbar. Frage 1 erklaert Satz 5 mit einem konkreten Ablauf (h7), das ist verstaendlich. Schwaechen:
- Frage 1 mischt zwei Entscheidungen (Wortlaut und Anzeige). Die Anzeige steckt im E1 statt in der Frage (M-7).
- In der Karte fehlen Wartegruende (M-3, M-4, M-6). Dadurch koennte Chat Merges freigeben, die laut Plan noch warten muessen.

## Nachpruefung Fassung 3

Geprueft: `Meldung_38_Strang_Karte.md`, Fassung 3 (177 Zeilen), neu eingelesen. Abgeglichen gegen `gp_n5_nacharbeit.md` (M-B, M-C), `gp3_fg81_m37.md`, Plan-Nachtrag 5.2, `s1c2/ergebnis_b4b_bewertung.md` (Abschn. 5) und `Abnahme_Fotos_Meldung_23_Nico.md`.

**Urteil: lieferbar JA, mit einer Ein-Zeilen-Korrektur (N-M1).** Eine weitere Runde ist nicht noetig.

**Oeffentlich publizierbar: ja.** Suche nach `@`, `/home`, `/root`, `/tmp`, `/mnt`, `token`, `passw`, `secret`, `ghp_` (ohne Gross-/Kleinschreibung): 0 Treffer.

**Kopfblock:** 6 Zeilen, erlaubt sind 10. Enthaelt Blockiert/laeuft weiter, Bereit, Katalog-Meldung, Regelverstoss, Entscheidungen mit Stufe und Empfehlung sowie E1. `AN:`, `ENTSCHEIDUNG NÖTIG:` und die Belegzeile sind da.

### Einarbeitung der Befunde
| Befund | Stand |
|---|---|
| S-1 | eingearbeitet (Frage 4): 1279/1323 s, N5-Datei 400-550 s, rund 1850 s; (a) vor dem N5-Merge, nicht mit N10; Zahlen fuer (b) und (c) stimmen |
| M-1 | eingearbeitet: E1-3 alt gestrichen, Katalog-Meldung in Kopfblock Zeile 3, Fix 3b "die Art bestimmt die Stufe" |
| M-2 | als Frage 5 (E2) gestellt |
| M-3 | eingearbeitet: "ohne S1c2", N9 muss S1c2 nachziehen |
| M-4 | in der Karte eingearbeitet (S6a wartet auf die Wellen 3c bis 3e), im Kopfblock nicht, siehe N-M1 |
| M-5 | eingearbeitet (Frage 3: `cad90c0`, Vorlauf ohne Force, Dialog vorher auf S6b) |
| M-6 | als Frage 6 gestellt, dazu Karte N5 mit F30 und Frage 4 |
| M-7 | als Frage 2 gestellt (E2 Umfang, E3 Aussehen); Vorbau nur lokal auf `version-0632-dialog` |
| M-8 | als Frage 7 gestellt, dazu Kopfblock Zeile 4 |
| L-1 bis L-11 | eingearbeitet. Kleine Reste: N-L1 bis N-L3 |

### Neue Aussagen geprueft (belegt)
- **Frage 2**, gegen gp3 S1: richtig. Die Werte 1280 px, 1366×768 (Saetze 5-8) und 1920×1080 (Ende von Satz 6, Saetze 7 und 8) stimmen. Die Handy-Werte sind gerechnet, Windows und macOS nicht geprueft. Bei (c) ist "vermutlich" richtig als Vermutung gekennzeichnet.
- **Frage 5**, gegen Nachtrag 5.2: richtig. 3c steht nach 3b, und zu 3b gehoeren S1c2 und ein gruener Lauf. Die Empfehlung "N5 erst nach S1c2" ist strenger als der Plan, das ist zulaessig.
- **Frage 6**, gegen M-C: richtig. Die Pruefung gilt nur noch fuer Inter. DejaVu Normal 1360 laeuft 63 px ueber, das Ergebnis ist 3+1 / 3+1 / 3. Segoe UI ist nicht geprueft. F30 geht an Nico.
- **Frage 7**, gegen `ergebnis_b4b_bewertung.md` Abschn. 5: richtig. Das Paket ist nur im Container, der Testfix haengt nicht davon ab, es ist nicht entfernt.
- **Frage 1**, gegen gp3: richtig. Es sind 14 Ablaeufe; h8 ist als Lesart-Hinweis genannt, f7 als einziger richtiger Fall. Die neuen Tests h1, h7, h7h und h9 decken auch L1 der gp3.

### Restbefunde
- **N-M1 (mittel, eine Zeile):**
  - Kopfblock Zeile 2 "Bereit zum Merge: … S5b, S6a" widerspricht der Karte. S6a wartet auf die Wellen 3c bis 3e. Laut Plan kommt auch S5b erst nach Welle 3d, N12 erst nach 3c.
  - Genau das sollte M-4 verhindern: Chat koennte S6a als frei lesen.
  - **Korrektur:** "Gebaut und geprueft (Merge in Planreihenfolge): S6c, N1-N4, N12, N13 (B-N-10), S5b, S6a; B-9b nach Nicos Fotos."
- **N-L1:** Karte "S6c → N4: bereit (N2/N3: Design-Teile nach Fotos)" ist ueberholt. Nico hat Punkt 8 (N2) und Punkt 9a (N3) in der Abnahme zu Meldung 23 mit JA abgenommen. Vorschlag: "N2/N3-Fotos abgenommen (Meldung 23)".
- **N-L2:** Frage 6: Einen Satz ergaenzen, warum das E2 ist. Fuer andere Schriften als Inter ist die Pruefung "nichts geaendert bei Normal ab 1360" eine **Lockerung** des Tests (gp_n5_nacharbeit (4)). Nach der Weisung ist jede Lockerung E2.
- **N-L3:** In "Was nur auf eine Entscheidung wartet" fehlt Frage 7 (`faketime`, betrifft die Container-Umgebung des Tors).
