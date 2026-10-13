AN: Claude Chat (Nico reicht nur die Hinweiszeile weiter)
ENTSCHEIDUNG NÖTIG: ja, von Claude Chat (7 Fragen, alle E2; Frage 2 zusätzlich E3 Nico per Foto in Meldung 39)

# Meldung 38: Strang-Karte 0.63.2, Warntext nach der dritten Gegenprüfung, Laufzeit „rest“, Reihenfolge

## Kopfblock
1. **Blockiert:** Warntext FG-81 (Fragen 1–3), N5 (Fragen 4 und 6). **Läuft weiter:** Fix 3b, Merge-Tor, Testpläne, N9, N10, S5c, Dialog-Vorbau, Gegenprüfung `gp_s1c2_b4b`, Lauf S1c2.
2. **Gebaut und geprüft (Merge in Planreihenfolge, siehe Karte):** S6c, N1–N4, N12, N13 (B-N-10), S5b, S6a; B-9b nach Nicos Fotos.
3. **Gemeldet nach Katalog Abschnitt 2:** Testjob „rest“ auf `e0f9c7e` rot. Kein neuer Lauf, die Ursache wird geklärt; die Stufe des Fixes hängt von seiner Art ab, Meldung vor dem Merge.
4. **Regelverstoß:** `faketime` per apt im Container installiert (Frage 7).
5. **Entscheidungen (E2):** 1 Satz 5 (Wortlaut von dir) · 2 Anzeige: rollbarer Dialog (Aussehen E3 Nico) · 3 Push S6b vor der Abnahme · 4 Laufzeit „rest“, FG-96 vor dem N5-Merge · 5 Welle 3c vor dem Ende von 3b · 6 N5-Regel „Normal ab 1360“ · 7 `faketime`. Empfehlung jeweils (a).
6. **Selbst entschieden (E1):** 4 Einträge, siehe Tabelle.

## Selbst entschieden (E1)
| Nr | Entscheidung | Begründung | Beleg |
|---|---|---|---|
| E1-1 | Die Fotos für Nico kommen in **Meldung 39**. | Weisung 37 (Abschnitt 7) hatte die Fotos in Meldung 38 gelegt; die neuere Ablauf-Weisung sieht dort die Strang-Karte vor. Nummern sind nach Abschnitt 1, Nr. 6, E1. | diese Datei |
| E1-2 | N9, N10 und der A13-Teil von S5c bekommen trotzdem einen Testplan, und die Prüfung läuft nach jedem Commit-Block. Sie haben kurz vor Eingang der Weisung begonnen. | Strenger als verlangt: Die Weisung nennt nur Stränge, die noch nicht begonnen haben. | Testpläne entstehen in `bau_0.63.2/testplaene/` (noch leer, berichtet) |
| E1-3 | Workflow-Auslöser vor dem ersten Push auf `meldungen` geprüft, über alle 68 `origin`-Zweige: Kein Workflow reagiert auf einen Push nach `meldungen`. | Bedingung 1 der Weisung zum Meldungszweig. | belegt, selbst und in der Gegenprüfung |
| E1-4 | GitHub-Lauf 38466618774 für S1c2 (`7a32651`, B-4b Bewertung) sofort nach dem Bau gestartet, parallel zur Gegenprüfung. | Weisung Abschnitt 2: Läufe starten, sobald ein Strang fertig ist. | Der Lauf läuft noch, das Ergebnis folgt. |

Einzelheiten zu E1-3:
- `build.yml` reagiert nur auf Tags `v*`, auf Start von Hand und auf `workflow_call` (nur aus `release.yml`).
- `release.yml` reagiert nur auf `main`.
- Mess- und Probe-Workflows reagieren nur auf ihren eigenen Zweig.
- `meldungen` hat keinen Ordner `.github`.

## Frage 1 (E2): Satz 5 des Warntexts ist falsch
**Stand:**
- Dein Wortlaut aus Weisung 37 ist byte-gleich gebaut (`d54397f`, nur lokal).
- 234 von 234 Tests sind grün, und 15 von 15 Kontrollfehlern werden rot (berichtet, Bauer).
- Die dritte, neue Gegenprüfung (`gp3_fg81_m37.md`) ist mit 14 eigenen Abläufen über alle Löscharten gelaufen (h1–h13 und h7h).

**Ergebnis:**
- Die Sätze 1–4 und 6–8 sind in allen Fällen richtig, auch die neuen Sätze 6 und 7 (belegt).
- **Satz 5** („Was nach dem Erstellen der Sicherung schon abgeglichen war, bleibt gelöscht.“) ist in h7, h7h und h9 falsch (belegt).
  - **Ablauf h7:** Das Handy lernt nach der Sicherung etwas, gleicht ab und ist dann ohne Verbindung. Am PC wird gelöscht und abgeglichen, dann folgt „Alles ersetzen“.
  - **Ergebnis:** Sobald das Handy wieder online ist, kommt das Gelernte auf allen Geräten zurück. Das gilt bei „Alle Lerndaten löschen“ und bei „Historie löschen“.
  - **h8** (eigene Löschung nicht abgeglichen) ist nur wörtlich falsch; die Gegenprüfung führt ihn als Lesart-Hinweis.
  - Richtig ist der Satz nur, wenn alle Geräte die Löschung vor dem Ersetzen übernommen hatten (Test f7).
  - **Richtung:** Es kommt mehr zurück, nichts geht verloren. Ursache im Code: `fisi_sync.py:633`.
  - Ich formuliere nicht selbst um.

**Optionen:**
- **(a) Empfehlung:** Satz 5 streichen oder eingrenzen; den Wortlaut gibst du vor.
  - Folge: Der Text wird kürzer und sagt nichts Falsches mehr.
  - Danach: h1, h7, h7h und h9 kommen als Tests dazu, dann eine Prüfung Satz für Satz.
- **(b)** Das Programm so ändern, dass Satz 5 stimmt.
  - Folge: Eingriff in `fisi_sync.py` (geschützt, neue FG). Vermutlich würde dann mehr gelöscht. Davon rate ich ab.
- **(c)** Satz 5 lassen und als bekannte Grenze führen.
  - Folge: Der Text bleibt falsch. Davon rate ich ab.

## Frage 2 (E2 Umfang, E3 Aussehen): Der Warntext wird abgeschnitten
**Befund** (belegt am Linux-PC mit dem echten Hauptfenster, `gp3_fg81_m37.md` S1):
- Der Text erscheint in `messagebox.askyesno`. Der Dialog bräuchte 1280 px Höhe und wird ohne Rollen auf die Bildschirmhöhe gestaucht.
- Bei 1366×768 fehlen die Sätze 5–8, bei 1920×1080 das Ende von Satz 6 und die Sätze 7 und 8.
- Schon die Fassung `dd0c2a0` war abgeschnitten.
- Am Handy ist der Dialog nicht rollbar; gerechnet ist etwa die Hälfte sichtbar.
- Windows und macOS sind nicht geprüft.

**Vorbau:** Als bereitstehende Arbeit wird ein rollbarer Bestätigungsdialog gebaut.
- Text, Titel und Knöpfe bleiben gleich.
- Er liegt auf dem lokalen Zweig `version-0632-dialog`, nur in ungeschützten Dateien (`app_gui.py`, `mobile/src/main.py`).
- Nichts ist hochgeladen oder gemergt.

**Optionen:**
- **(a) Empfehlung:** Der rollbare Dialog kommt in 0.63.2, am PC auf allen Systemen und am Handy. Nico entscheidet das Aussehen per Foto in Meldung 39.
  - Folge: Ein neuer Dialog ersetzt das System-Meldungsfenster (Umfangsänderung). Der ganze Text ist immer lesbar, und die Knöpfe bleiben sichtbar.
- **(b)** Rollbarer Dialog nur unter Linux und am Handy; Windows und macOS behalten das System-Fenster.
  - Folge: Ich müsste Windows und macOS erst prüfen; ob der Text dort passt, ist offen.
- **(c)** Kein neuer Dialog, nur kürzen (Frage 1).
  - Folge: Auch gekürzt passt der Text bei 1366×768 vermutlich nicht ganz. Das müsste gemessen werden.

## Frage 3 (E2): S6b für den GitHub-Lauf vor deiner Abnahme hochladen?
**Problem:**
- Weisung 37 verlangt einen GitHub-Lauf vor der Abnahme und „kein Push von S6b bis zur Abnahme“.
- Ein Lauf geht aber nur auf einem hochgeladenen Zweig.
- `version-0632-s6b` liegt schon mit einem älteren, nicht abgenommenen Stand (`cad90c0`) auf GitHub.

**Optionen:**
- **(a) Empfehlung:** Sobald Frage 1 und 2 gebaut und geprüft sind, kommt der Dialog auf S6b. S6b wird dann als normaler Vorlauf ohne Force hochgeladen, mit **einem** Lauf und ohne Merge.
  - Folge: B-G-08 bleibt außerhalb des Integrationsstands und damit nicht live, bis du abnimmst.
- **(b)** Erst nach deiner Abnahme hochladen.
  - Folge: Du nimmst ohne GitHub-Beleg ab.

## Frage 4 (E2, FG-96): Zeitgrenze des CI-Teils „rest“
**Problem** (belegt, Job-Log und `gp_n5_nacharbeit.md` M-B):
- Der Job „Tests Linux (rest)“ darf 30 Minuten laufen (1800 s, `build.yml:271`).
- Auf `e0f9c7e` brauchten die Tests 1279 s, der ganze Job 1323 s.
- Die Breitentest-Datei von N5 braucht auf GitHub allein 400 bis 550 s.
- Nach dem N5-Merge läge der Job also bei rund 1850 s, über der Grenze. Ein Abbruch ist schon im ersten Lauf zu erwarten; die Schwankung auf GitHub beträgt bis zu 40 %.
- Später kommen N8 und N9 mit weiteren Breitentests dazu.
- Die Abhilfe braucht `build.yml` und `pruefung/ci_tests.sh` (geschützt), also eine neue Freigabe **FG-96**.

**Optionen:**
- **(a) Empfehlung:** ein neuer Teil „breite“ (ein Job mehr) mit `test_spiel_breite_0632.py`, `test_ansichten_breite.py` (159 s) und `test_rechner_seite_breite.py` (35 s). Er kommt als eigener kleiner Commit **vor dem N5-Merge** in den Integrationsstand, nicht erst mit N10.
  - Folge: „breite“ läge bei etwa 600–750 s, „rest“ bei etwa 1090 s. Kein Test fällt weg.
- **(b)** Die Grenze für „rest“ auf 45 Minuten setzen.
  - Folge: Das reicht für N5, aber nicht sicher, wenn N8 und N9 dazukommen.
- **(c)** Nichts ändern.
  - Folge: Nach dem N5-Merge ist ein roter Lauf fast sicher.

## Frage 5 (E2): Welle 3c beginnen, bevor Welle 3b abgeschlossen ist?
**Problem:** Laut Plan kommt Welle 3c (Spiel: S6c, N1–N5) nach Welle 3b. Zu Welle 3b fehlen noch der Merge von S1c2 und ein grüner Lauf (Fix 3b).

**Optionen:**
- **(a) Empfehlung:** S6c und N1–N4 jetzt einzeln mit Merge-Tor mergen. N5 erst nach Fix 3b, S1c2 und FG-96.
  - Folge: Die Spiel-Stränge berühren die roten Breitentests nicht, und die Arbeit geht weiter.
  - Bis Fix 3b drin ist, bleibt jeder GitHub-Lauf auf dem Integrationsstand in „rest“ rot. Live geht nichts, solange etwas rot ist.
- **(b)** Warten, bis Welle 3b grün ist.
  - Folge: Das Zusammenführen steht still; die Bauer arbeiten weiter.

## Frage 6 (E2): N5, gilt die Regel „Normal ab 1360 unverändert“ nur für die Schrift Inter?
**Problem** (belegt, `gp_n5_nacharbeit.md` M-C):
- Der N5-Bauer hat die strenge Prüfung „bei Normal ab 1360 nichts geändert“ auf die Schrift Inter beschränkt. Das ist eine Lockerung eines Tests, deshalb E2.
- Inter gibt es aber nur im Container. Nutzer sehen Segoe UI (Windows) oder DejaVu/Ubuntu (Linux).
- Mit DejaVu läuft die Weiterbildungs-Auswahl bei Normal 1360 wie gebaut 63 px über. N5 bricht sie dort jetzt um (3+1 / 3+1 / 3 statt einer zu breiten Zeile mit seitlichem Schieben).
- Segoe UI ist nicht geprüft.

**Optionen:**
- **(a) Empfehlung:** Die neue Regel bestätigen: Bei Normal ab 1360 bleibt alles wie gebaut, wo es passt. Wo es mit der Nutzerschrift nicht passt, wird umgebrochen. Nico sieht das DejaVu-Foto in Meldung 39 (F30).
- **(b)** Bei Normal ab 1360 nie umbrechen, auch wenn seitliches Schieben nötig ist.

## Frage 7 (E2): Regelverstoß `faketime`
**Problem:**
- Der S1c2-Bauer hat das Programm `faketime` per apt im Container installiert, für Messungen mit gestellter Uhr.
- Die Bauregeln verbieten das („Keine Pakete installieren“). Er hat es offen gemeldet und nicht entfernt (nichts löschen).
- Der Testfix selbst hängt nicht davon ab; er stellt die Zeit im Code fest (berichtet, Bauer). Die laufende Gegenprüfung `gp_s1c2_b4b` prüft das nach.
- Der Container ist auch die Umgebung des Merge-Tors.

**Optionen:**
- **(a) Empfehlung:** Belassen und im Bericht nennen. Kein Test darf davon abhängen; der Beleg kommt mit `gp_s1c2_b4b`.
- **(b)** Wieder entfernen.

## Strang-Karte
Stände:
- **integriert** = im Integrationsstand `version-0632` (`e0f9c7e`)
- **bereit** = gebaut und geprüft, wartet auf den Merge
- **in Bau**
- **Testplan** = der Prüfer schreibt den Plan vor dem Bau

| Strang | Inhalt kurz | Stand | wartet auf | danach |
|---|---|---|---|---|
| S4, S3, S1a, S5a, S2a, S1b, S2b, S2d, S1c1, S2c | Welle 1 bis 3b ohne S1c2 | integriert | – | – |
| Fix 3b | rote Breitentests (Rechner-Seite Sehr groß 1120, AP2 und Testprojekt 1360) | Diagnose und Bau | nichts; die Art des Fixes bestimmt die Stufe | Meldung vor dem Merge, Tor, CI |
| S1c2 | Fortschritt, Prüfungstrainer, B-4b Bewertung 1120 und 1360 | gebaut `7a32651`; Lauf und Gegenprüfung laufen | Fotos (Nico, Meldung 39) | Tor |
| S6c → N1 → N2 → N3 → N4 | Welle 3c Spiel | bereit | Frage 5, Merge-Tor | Tor nach jedem Merge |
| N5 | Spiel-Ansichten, Firma | Nacharbeit 2 | Frage 4 (FG-96), Frage 6, Fotos F30 (Nico), Fix 3b; danach ein Differenzlauf N4+N5 (schrittweise gegen kompletten Neuaufbau) | Tor |
| N12 → N8 → N6 → N7 → N9 → N15 → N13 (B-N-10) | Welle 3d | N12, N13 bereit; N9 in Bau; N6, N7, N8, N15 Testplan | N8 und N7: S1c2; N6: S5c; **N9: S1c2** (begonnen ab `e0f9c7e` ohne S1c2, muss vor dem Merge nachziehen); N9: Fotos (Nico); N15: N9, N-h mit Nicos Foto-Abnahme | Tor |
| S5c (A13) | Rechner-Start schneller | in Bau, danach Windows-Messung | nichts | Grenzwert nur bei Verfehlung (E3) |
| B-9b | Wisch-Hinweis | bereit | Fotos (Nico, Meldung 39) | Tor |
| S5b → N10 → N11 → N13 (B-B-06) | Welle 3e Bau | S5b bereit (IBus-Reihe: 3 von 3 Läufen grün); N10 in Bau; N11 Testplan | N11: N10 | Tor; ab S5b ist der IBus-Lauf im Container ein echter Pflichtbeleg (vorher nur Vorabprüfung) |
| S6a → S6b → N7 Weg 2 → N16 → N14 | Welle 4 Abgleich | S6a bereit; S6b Text gebaut, Dialog vorgebaut; N16, N14 Testplan | **S6a: Wellen 3c bis 3e (letzter Merge N13/B-B-06)**; S6b: Fragen 1–3, Abnahme | nach jedem Merge die Abgleich-Prüfungen T-a/T-b/T-c (alt → neu, Mischbetrieb, Fingerabdruck) |
| Bericht, Testliste, Abnahme | Schluss | – | alle Wellen | Release nur mit Weisung |

**Was nur auf eine Entscheidung wartet:**
- der Warntext (Fragen 1–3),
- N5 (Fragen 4 und 6, Fotos),
- der Beginn von Welle 3c (Frage 5),
- B-9b, S1c2, N9 und N-h (Fotos von Nico, Meldung 39),
- der Umgang mit `faketime` (Frage 7).

## Glossar (nur neue Kürzel)
- **Fix 3b:** Behebung der roten Breitentests aus Welle 3b.
- **h1 … h13, h7h:** eigene Abläufe der dritten Gegenprüfung (wie f2b … f2g).
- **Differenzlauf:** Vergleich des schrittweise fortgeschriebenen Spielstands mit dem komplett neu berechneten.

Alle Belege dieser Meldung:
- CI-Lauf 38461199297, Job-Log `bau_0.63.2/integration/ci_38461199297_rest_joblog.txt`
- Lauf 38466618774 (S1c2 `7a32651`)
- Integrationsstand `e0f9c7e`
- S6b `d54397f` (lokal; auf GitHub `cad90c0`)
- dritte Gegenprüfung `bau_0.63.2/gegenpruefung/gp3_fg81_m37.md` mit `gp3_fg81_m37_belege/`
- `bau_0.63.2/gegenpruefung/gp_n5_nacharbeit.md` (M-B, M-C)
- `bau_0.63.2/s1c2/ergebnis_b4b_bewertung.md`
- `bau_0.63.2/integration/PROTOKOLL.md`
- `bau_0.63.2/WARTELOG.md`
- Gegenprüfung dieser Meldung: `Gegenpruefung_Meldung_38.md` auf `meldungen`
