# Unabhängige Gegenprüfung Meldung 44 (Fassung 1)

Geprüft: `bau_0.63.2/meldungen/Meldung_44_Fragen_und_Stand.md`, Fassung 1 (699 Zeilen, 62.823 Bytes), am 14.10.2026 gegen 12:05 UTC.
Prüfer: unabhängig, hat die Meldung nicht geschrieben. An der Meldung nichts geändert, nichts committet, nichts gepusht, nichts gelöscht.
Maßstab: Weisung 42 und 43 (Abschriften in `plan_0.63.2/freigabe/`), `REGELN_BAU_0.63.2.md` (Zusätze W42/W43, Meldeformat), dazu Weisung 38/40 und 41, wo sie eine Regel setzen, auf die sich die Meldung stützt.
Nicht bewertet: der Inhalt von Frage 9 und 10 (Platzhalter für FG-111/FG-112).

Zeilenangaben beziehen sich auf die Meldung, Fassung 1.

**Gesamturteil:** Die Zahlen und SHAs stimmen fast ohne Ausnahme. 52 von 54 Stichproben sind richtig, eine ist überzogen und eine falsch (Liste unten). Format, Kopfblock und Selbstkontrolle passen. Vor dem Versand sollten 4 hohe und 8 mittlere Befunde korrigiert werden. Zwei Regeln werden in der Meldung nicht offen benannt: Weisung 42, 2.15 wird auf einen Test angewendet, der kein Zeittest ist, und die N5-Bedingung „erst nach S1c2“ aus Weisung 38/40 wird nicht erwähnt. Zu Frage 3 fehlt eine Information, die die Entscheidung beeinflusst. Frage 7 (b) ist nicht selbsttragend.

---

## 1. Befunde

### Hoch

**H1 – Zeittest-Regel auf einen Test angewendet, der kein Zeittest ist; Push trotz Tor ROT (Z. 82, 117–139, 363, 413)**
Weisung 42, 2.15 gilt laut Text für einen „roten **Zeittest** (Meldung nennt die Grenze, z. B. ‚429 > 400 ms‘)“. `LoadingHintTest.test_anzeige_bei_langsamer_ansicht` prüft nach `stop_preloader()`, ob der Ladehinweis erscheint (`hint["shown"] == 1`, belegt: `test_vorladen.py` auf `a82fd34`, Z. 280–288). Eine ms-Grenze prüft er nicht. Das sagt die Meldung selbst in Z. 128. Trotzdem gilt Folgendes:
- Der Integrator hat ihn nach 2.15 als „lastabhängig“ eingestuft. Die Meldung führt das als **E1-4** (Z. 413).
- `a82fd34` wurde gepusht, obwohl das Tor-Werkzeug **ROT** meldete (`tor_a82fd34.md`, Z. 3–5). Weisung 42, 4.9 verlangt den Push erst „nach den vollen Suiten und dem Merge-Tor“.
- Option (a) in Frage 2 („Regel bleibt wie sie ist, Zähler 1“) setzt stillschweigend voraus, dass dieser Test unter 2.15 fällt und mitzählt.

Damit wird eine Chat-Regel per E1 ausgeweitet, ohne dass das als Ausweitung benannt ist. Weisung 42, 2.15 Nr. 3 sagt dazu: „Nichts wird gelockert.“
**Korrektur:**
- E1-4 aus B.5 streichen und in Frage 2 als eigenen Unterpunkt **2a (nachträgliche Bestätigung)** stellen: „2.15 ist für Zeittests geschrieben. Ich habe es auf einen Test ohne ms-Grenze angewendet und `a82fd34` trotz Tor ROT gepusht (GitHub-Lauf 38550615169 ganz grün; nach 2.15 Nr. 3 ist GitHub maßgeblich). Bestätigst du das nachträglich, oder gilt der Fall als echt rot?“
- Für die Zählung eine Option nennen: „zählt nicht nach 2.15 (kein Zeittest)“ gegen „zählt mit“.
- In „Eigene Fehler“ einen Punkt aufnehmen: Push auf einer Regel, die den Fall nicht deckt.

**H2 – N5 vor S1c2 gemergt, Bedingung aus Weisung 38/40 nicht erwähnt (Z. 10, 365, 432)**
Weisung 38/40, Frage 5 sagt: „N5 erst nach Fix 3b, **S1c2** und FG-96“. So steht es auch in den REGELN, Zusatz Weisung 38/40. N5 ist lokal gemergt (`e90b78e`, Eltern `a82fd34` + `98f63ff`, belegt), S1c2 dagegen nicht. Die Meldung beruft sich nur auf die Reihenfolge aus Weisung 42, 2.1 („Fix 3b → FG-96 → N5“). Das Protokoll hatte den Zweifel selbst notiert (PROTOKOLL Z. 205: „N5 (nach S1c2? → …)“). Weisung 43, 2.4 Nr. 3 („zum Beispiel N5, S5c“) lässt sich als stillschweigende Zulassung lesen. Gesagt wird das in der Meldung aber nicht.
**Korrektur:** In B.1 (Z. 365) und B.8 einen Satz ergänzen: „Weisung 38/40, Frage 5 verlangte N5 erst nach S1c2. Ich lese Weisung 42, 2.1 und Weisung 43, 2.4 Nr. 3 als Ablösung dieser Bedingung (vermutet). N5 bleibt bis zu deiner Antwort ungepusht; ein Widerspruch genügt.“ Das kostet keine Verzögerung, weil N5 ohnehin lokal ist und das Tor noch läuft.

**H3 – Frage 3: Für die Wahl zwischen den Optionen fehlt eine Information (Z. 177, 194–198)**
Nicos Ziel nach 18b ist „1 s nach einer Änderung“. Unter Windows liegt das Dashboard nach einer Änderung schon **ohne** FG-107 unter 1 s: 884 ms nach einer Quizantwort, 827 ms nach einer Karteikarte (`n7/fg107/logs/messung_windows.md`, Spalte „vorher 1e7965a“; berichtet). Option 3a (c) nennt als Folge nur „fällig bleibt bei etwa 0,7 s bzw. 0,33 s“. Dass Nicos Ziel unter Windows auch mit (c) erreicht ist, steht dort nicht. (c) würde N7 sofort freigeben und damit auch N16 und N14 in der Planreihenfolge. Nico will möglichst keine Verzögerung.
**Korrektur:** Bei 3a (c) ergänzen: „Unter Windows liegt das Dashboard nach einer Änderung schon ohne FG-107 bei 884/827 ms, also unter Nicos Ziel von 1 s (berichtet). Im Container sind es etwa 2,0/1,5 s unter Last etwa 9.“ Die Empfehlung (a) kann bleiben, aber die Abwägung muss sichtbar sein: mit (a) sicher unter 1 s, dafür eine Gegenprüfung mehr; mit (c) N7 sofort mergebar. In der Information Z. 196 entsprechend ergänzen: „auch ohne FG-107 unter Windows unter 1 s“.

**H4 – Frage 7 (b) ist nicht selbsttragend, die Begründung stimmt nicht (Z. 313–315)**
1. Die Begründung „Eine fehlende Stelle führt nie zu einer falschen Trennung, höchstens zu einem früheren Umbruch“ ist falsch. `fisi_trennung` auf `c65f67d` (Modulkopf) sagt: „ein Wort ohne passende Stelle wird wie bisher an der letzten passenden Stelle **ohne Trennstrich** geteilt“. Mit weniger Stellen kommt dieser Rückfall häufiger vor, also eine Teilung mitten im Wort ohne Strich.
2. Bei 5 der 14 unsicheren Einträge gibt es keine Fassung „mit weniger Trennstellen“, weil die Frage `‖` gegen `|` ist oder eine Stelle mehr betrifft:
   - Nr. 8 `be|auf`
   - Nr. 52 `Mul|ti‖`
   - Nr. 66 `ver|ur`
   - Nr. 76 `Hoch|zeits`
   - Nr. 35 `nieur`

   Bei Nr. 73 und Nr. 53 ist die gelistete Fassung schon die mit weniger Stellen. Chat kann aus (b) also nicht ablesen, was ohne Antwort gilt.

**Korrektur:**
- Den Satz ersetzen durch: „Eine fehlende Stelle trennt nie falsch mit Strich. Passt keine Stelle, teilt der Rückfall wie heute ohne Strich.“
- Option (b) als Tabelle mit 14 Zeilen fassen: „Nr. / gilt ohne deine Antwort“. Zum Beispiel „Nr. 8: wie gelistet (`be|auf`)“, „Nr. 64: wie gelistet (`agen` ungeteilt)“.

### Mittel

**M1 – Kopfblock und B.2 behaupten „in keinem Lauf durch die eigene Änderung rot“ (Z. 13, 389)**
Lauf 38549977359 auf `bd14178` (S1c2) war rot durch `FortschrittDatenBreiteTest.test_sehr_gross_1120_andere_schrift`. Die Ursache war die eigene Variante B: Die Seite passt, die Erinnerung verlangte einen Überstand. Belege: `s1c2/nachbesserung/ergebnis.md` Z. 124 und Frage 6, Z. 276–277. Das widerspricht dem Kopfblock.
**Korrektur:** „In keinem der **letzten** Zweigläufe … (Ausnahme: S1c2-Vorlauf 38549977359, eigene Änderung, Frage 6)“.

**M2 – Frage 1: „Blockiert: nichts sofort“ untertreibt die Wirkung (Z. 109, 115)**
Mit (a) soll FG-113 „vor dem nächsten Merge, der rest wachsen lässt (S6b)“ kommen. Ohne (a) kann S6b „rest“ über die 1800 s treiben. Dann gilt der Lauf als weder grün noch rot (Katalog), und es gibt keinen grünen Lauf. In beiden Fällen hängt die Planreihenfolge S6a → S6b → N7 → N16 → N14 an Frage 1.
**Korrektur:** „Blockiert: S6b-Merge und damit die Planreihenfolge, bis (a) gebaut ist oder du (b) wählst.“

**M3 – Frage 1: Die Zahlen sprechen stärker gegen „Streuung“, als die Meldung schreibt (Z. 99–100)**
Auf `8f18818` lag „rest“ bei 1402 s, mit den Breitendateien. FG-96 hat „breite“ herausgenommen, das sind auf `a82fd34` 421 s. Zu erwarten wären also etwa 1402 − 421 ≈ 981 s. Gemessen wurden 1441 s, rund 460 s mehr als erwartet. Die Meldung schreibt nur, „rest“ sei „nicht kürzer“ geworden. Das ist für die Größe der Teilung (rest2) wichtig.
**Korrektur:** Die Rechnung offen nennen. Als „Ursache nicht geprüft“ kennzeichnen, „Streuung“ nur als eine von mehreren Vermutungen. Vorschlagen, dass die Messung je Datei (Teil der Option (a)) diese Lücke erklärt.

**M4 – Frage 4: „In 11 weiteren Ansichten kein Unterschied“ verschweigt die Grenzen der Prüfung (Z. 208)**
Laut FG-109-Antrag (Abschnitt 2, „Grenzen“) war die Prüfung an mehreren Stellen nicht vollständig:
- Bei 2 der 11 Ansichten gab es Pixelunterschiede ohne Textunterschied (Fortschritt, Ticket).
- „kalk“ ist **nicht geprüft**.
- Bei 8 Ansichten ist der untere Teil abgeschnitten, dort ist ebenfalls **nicht geprüft**.
- Serverfarm, Dialoge, Kalkulation und laufende Kredite wurden nicht fotografiert.

Die Liste S1–S8, die als Stoppgrenze gilt, ist darum eine Untergrenze. Werden später weitere Stellen gefunden, braucht es wieder eine FG-Runde.
**Korrektur:**
- Z. 208 so fassen: „in 8 Ansichten kein Unterschied (dort teils nur der obere Teil geprüft), 2 nur Pixel, 1 nicht geprüft; nicht fotografiert: …“
- Gegen eine spätere Verzögerung eine Unterfrage **4e** stellen: Wie wird mit weiteren belegten Stellen gleicher Art umgegangen? Zum Beispiel: Aufrufer von `_whole_euro_shown` oder `spiel.euro`, nur mit Foto-Beleg, gemeldet in der nächsten Meldung, sonst Befund im Bericht. Empfehlung: Befund im Bericht, keine Erweiterung ohne Freigabe.

**M5 – Ziel 1 s: Die Wortvorgabe aus Weisung 43, 2.7 Nr. 6 wird per E1 geändert, „an der Grenze“ beschönigt (Z. 79, 194–198, 412)**
Weisung 43, 2.7 Nr. 6 gibt den Satz für den Bericht vor: „Zielwert 0,2 s nicht erreicht“. Die Meldung ersetzt ihn per E1-3 und Information („Widerspruch genügt“). Die Begründung über Nico ist sachlich gut. Zwei Punkte stimmen aber nicht:
- 1054 ms im Container sind **über** 1 s und nicht „an der Grenze“.
- Die Windows-Messung lief auf `5592023` (FG-107 ohne FG-110).

**Korrektur:**
- Satz: „Ziel 1 s (Nico, 18b): unter Windows erreicht (546/518 ms, gemessen auf dem FG-107-Stand), im Container unter Last etwa 9 knapp verfehlt (1054/949 ms, nur Richtung).“
- E1-3 ausdrücklich als „Abweichung vom Wortlaut der Weisung 43, 2.7 Nr. 6“ kennzeichnen.

**M6 – Weisung 43, 4.7 und Planreihenfolge: Stand von S6a/S6b fehlt (Z. 10, 200, 433)**
Nach Weisung 43, 4.7 wird S6b „in der Planreihenfolge nach FG-96“ gemergt. FG-96 ist drin. Die Meldung sagt nirgends, warum S6a und S6b noch nicht laufen bzw. als Nächstes dran sind. In der Auflagen-Tabelle gibt es keine Zeile 4.7. Gerade daran hängt die Verzögerung von N7, N16 und N14.
**Korrektur:**
- Im Kopfblock unter „Läuft weiter“ den nächsten Schritt nennen, zum Beispiel „nach dem N5-Tor: S6a, dann S6b (mit Auflösung der 4 T-c-Tests nach Weisung 41, Frage 9)“, oder den Grund, warum nicht.
- In der Tabelle Zeilen 4.5 und 4.7 ergänzen.

**M7 – 4.3 „alle roten Tests“: Ein Lauf fehlt, Stufe zu hoch (Z. 51, 64, 375–389)**
- Der N9-Lauf 38545811233 auf `e6fe458` fehlt. Das ist der Lauf zum V2-Commit, den Frage 8 behandelt. Er war rot (belegt per `gh run list`).
- Die Quellen widersprechen sich: `n9/ergebnis.md` Z. 28 nennt „die drei bekannten Breitentests“, `OFFEN_FUER_BERICHT.md` Z. 114 „2 bekannte“.
- Ebenso fehlt der N15-Lauf 38543848476 auf `58d6d66`. Die Quelle `n15/ergebnis.md` Z. 317 nennt dort alle drei namentlich.
- Z. 51 stuft die Tabellenzeile 4.3 als „belegt“ ein. Der N8-Beleg ist aber nur ein Auszug von 61 Zeilen, der N9-Beleg ein Auszug von 16 Zeilen.

**Korrektur:**
- Beide Zwischenläufe mit ihren roten Tests in B.2 aufnehmen. Den Widerspruch 2/3 klären, mit dem Log oder als „Quellen widersprechen sich, nicht geprüft“.
- Z. 51 auf „Auszüge belegt, Vollständigkeit berichtet“ ändern, wie schon in Z. 64.

**M8 – 7acfccb: Eine Lockerung wurde ohne Rückfrage gepusht, steht aber nicht unter „Eigene Fehler“ (Z. 76–87, 280)**
Frage 6 ordnet den Fall ehrlich ein. In der Selbstkontrolle unter „Eigene Fehler“ fehlt er aber. REGELN, Abschnitt „Tests“: „bewusst geänderte Tests NICHT abschwächen“. Die Testdatei ist ein eigener 0.63.2-Test (es gibt `test_ansichten_breite.py` nicht in `14b3bd4`, belegt). Das mildert den Fall, ändert ihn aber nicht.
**Korrektur:** Als Punkt 12 aufnehmen: „S1c2 hat mit `7acfccb` eine Prüfung gelockert und vor einer Rückfrage gepusht (Frage 6). Nicht gemergt.“

### Gering

**G1 – Uhrzeit im Kopf (Z. 6 gegen Z. 12, 449):** „Stand etwa 11:50 UTC“, aber Nicos Antwort von 11:54 UTC ist eingearbeitet. **Korrektur:** Uhrzeit auf den tatsächlichen Stand setzen (nach 11:54).

**G2 – Kopfblock „N14-Merge nur am Wortlaut“ (Z. 9):** N14 braucht zusätzlich einen ganzen grünen `s1_voll.py`-Lauf auf dem End-Stand (Weisung 43, 2.5; B.8 sagt das richtig) und steht in der Planreihenfolge hinter N7 und N16. **Korrektur:** „N14: Wortlaut (Frage 5); dazu End-Stand-Lauf und Planreihenfolge“.

**G3 – Tabelle Z. 37 „2.5 … voller Lauf: erfüllt“:** Erfüllt ist der Lauf auf `8cef3b4`. Die Merge-Bedingung „ganzer grüner Lauf auf dem End-Stand“ ist offen. **Korrektur:** „Lauf auf `8cef3b4` 46/46; End-Stand-Lauf offen (Merge-Bedingung)“.

**G4 – Tabelle Z. 50 und Kopfblock Z. 11 „darum kein breite2“:** Gemessen ist ohne N5-Datei und ohne die vier N8-Breitendateien. Die N8-Dateien lagen lokal bei etwa 1600 s bzw. 1217 s (`n8/ergebnis.md` Z. 60/62). Ob nach dem N8-Merge „breite2“ nötig wird, ist offen. Liegt eine Datei über 1350 s, kommt nach Weisung 43, 2.10 Nr. 4 eine neue Frage. **Korrektur:** „bisher nicht nötig; Messung nach N5 und beim N8-Merge, dann ggf. breite2 ohne Frage (2.10)“.

**G5 – Frage 7, Z. 308: „(i)–(iv) für alle 127 Einträge bestanden“:** Laut `vorpruefung_94.txt` gilt (i) „steht so in einer Quelle“ nur für die 94 neuen Einträge, (ii)–(iv) für alle 127. **Korrektur:** genau so trennen. Außerdem: (iii) prüft maschinell `ch/sch/ie/ei/au/eu/ck` und Abkürzungen mit Ziffer. Weitere „nie trennen“-Fälle aus Anhang A (Versalien, englische Wörter) prüft es nicht. Das in einem Halbsatz sagen.

**G6 – B.6: „je ein Satz“ (Weisung 43, 2.1):** Beide Antworten haben je drei Sätze. **Korrektur:** auf je einen Satz kürzen, Einzelheiten in eine Klammer.

**G7 – Belegstufen: „belegt“ steht dort, wo es der Bauer oder Prüfer belegt hat (Z. 155, 182, 208, 218–219):** Gemeint ist „belegt im Code“, „belegt per Suche“ oder „belegt“ beim Fingerabdruck, jeweils durch Bauer oder Prüfer. Für den Schreiber der Meldung ist das **berichtet**. **Korrektur:** „(laut Bauer/Prüfer belegt)“ schreiben.

**G8 – Zeile 2 und Kopfblock Punkt 4: Nico-Punkte nicht vollständig:** Zeile 2 nennt nur Chat. Wählt Chat in Frage 3a (b), kommt ein weiterer E3-Punkt dazu. **Korrektur:** Zeile 2 „ja (Chat 10 Fragen; Nico über Chat: 4d, 6b, ggf. 3a b)“.

**G9 – Frage 3: macOS-Satz nicht selbsttragend (Z. 155):** Dass es unter macOS keinen Einzelstart gibt, **erhöht** die Möglichkeit des zweiten Wegs, statt sie auszuschließen. Wie Linux/Windows sie mit Einzelstart verhindern oder nicht, steht nicht da. **Korrektur:** „Unter Linux/Windows verhindert der Einzelstart ein zweites Programm (gleiche Version); unter macOS gibt es ihn nicht, dort ist der Weg möglich.“ Den Zusammenhang mit älteren Versionen prüfen bzw. als „nicht geprüft“ kennzeichnen.

**G10 – 3b, 3c, 4c ohne Gegenoption:** Dort gibt es nur eine Empfehlung. Formal fehlen die Optionen. **Korrektur:** je eine Gegenoption mit Folge in einer Zeile (3b: „Prüfsumme als FG“; 3c: „B3 Sperre vor `_recompute` beenden als FG“; 4c: „Text-Export ausnehmen“).

**G11 – B.7: S6b × S6c, „wird beim S6b-Merge aufgelöst“ (Z. 426):** Der Satz klingt nach einer stillen Anpassung von Tests. Die Grundlage ist Weisung 41, Frage 9 (eng begrenzt, Kontrollfehler Pflicht, „mehr als diese vier Tests → melden“). **Korrektur:** diese Fundstelle und Bedingung nennen.

**G12 – Dokumente am Ende unvollständig:** Es fehlen:
- `integration/tor/tor_53a4354.md` (Frage 2)
- `s1c2/nachbesserung/logs/ci_rest_38549977359.log` (Frage 6)
- `antraege/FG-107_Antrag.md` (Container-Werte 1054/949, Frage 3)
- `plan_0.63.2/freigabe/Weisung_CC_Antwort_Meldung_38_und_40.md` (H2)
- `Weisung_CC_Antwort_Meldung_41.md` (G11)

### Vermeidbare Fragen (Nico will möglichst keine Verzögerung)

- **Frage 8:** Ein zusätzlicher Test in einer **neuen, ungeschützten** Testdatei braucht nach den Vorbildern Weisung 42, 2.20 und Weisung 43, 2.5 („ungeschützt, keine FG“) keine Freigabe. Er überschreitet auch nicht die Stoppgrenze von FG-101, weil `test_anzeige_handy.py` und `ui.py` unberührt bleiben. **Vorschlag:** als E1 mit Ankündigung bauen („Kontrollfehler vorab; Widerspruch genügt“) und Frage 8 streichen.
- **Frage 6b:** Nach Weisung 43, 2.3 ist bei „in 0.63.1 sichtbar“ kein Satz an Nico nötig („Rückkehr zum alten Stand“). Neu ist nur die Lage (darunter statt daneben, +20 px). Die S1c2-Fotos gehen ohnehin an Nico (Weisung 41, 4). **Vorschlag:** E1 („Satz und Foto gehen mit dem nächsten Nachtrag; Widerspruch genügt“). Klarstellen, dass 6b den S1c2-Merge nicht blockiert, denn die Bedingungen aus 2.3 sind erfüllt (Z. 301 sagt das nur indirekt).
- **N6-Konflikt (B.3):** Nach dem jetzigen Vorgehen wartet N6 eine ganze Runde (Diff in Meldung 45, dann Weisung). **Vorschlag:** schon jetzt eine kleine E2-Unterfrage stellen: „Darf N6 nach Auflösung im Zweig, grünem Tor N6 (mit `test_klick_hat_vorrang`, Vorlade- und Rechner-Breitentests) und ganzem grünem Lauf gemergt werden, wenn der Auflösungs-Diff mit Begründung in Meldung 45 nachgereicht wird?“ Empfehlung nach eigenem Ermessen. Das ist nicht „still“, weil die Auflösung gemeldet wird.
- **„Schreibfehler mit beheben“ (B.9, Z. 453–454):** Die Lesart ist vermutet, und die Folge „darüber hinaus ist nichts zu tun“ würde im Zweifel etwas still fallen lassen (Regel „nichts gekürzt“). Es gibt drei mögliche Lesarten:
  - „einreiche“ (wird mit F1 b behoben)
  - „c 1“ (FG-103)
  - „Karteikarten zu **Dienste**“ (wirkt wie ein Tippfehler für „zu Diensten“, ist aber `"Karteikarten zu %s" % TOPIC_SHORT`, belegt `mobile/src/spiel.py:2388`, `fisi_game_gui.py:3171`)

  **Vorschlag:** eine Zeile im ohnehin nötigen Nachtrag an Nico mit diesen drei Lesarten. Das kostet keine Verzögerung.

### Auflagen aus Weisung 43: in der Tabelle unerwähnt oder ohne Beleg
| Abschnitt | Auflage | Befund |
|---|---|---|
| 2.3 | „Die Deckel bleiben die Inter-Werte“ | unerwähnt (gering; in `s1c2/nachbesserung/ergebnis.md` erfüllt) |
| 2.4 Nr. 2 | Auflösung Zeile für Zeile im Merge-Protokoll | unerwähnt; mit „offen“ in der Zeile 2.4 sinngemäß gedeckt |
| 2.5 | Abweichungen von S6b als Beleg ins Log, nicht als Fehler | unerwähnt (erfüllt laut `n14/ergebnis.md` Z. 96) |
| 4.5 | Test `cb60f8b` kommt mit dem S6b-Merge | unerwähnt |
| 4.7 | S6b in der Planreihenfolge nach FG-96 | unerwähnt, siehe M6 |
| 4.9 | „Optik offen: Fix 3b“ | erledigt laut B.1 (Nico 6a), aber keine Zeile in der Tabelle |
| 2.7 Nr. 4 | Windows-Messung | erfüllt, aber auf `5592023` statt auf dem Endstand `3d09742` (App-Code gleich, berichtet); kurz sagen |

---

## 2. Stichproben (54, davon 52 richtig, 1 überzogen, 1 falsch)

„Selbst geprüft“ heißt: in dieser Gegenprüfung mit `git`, `gh`, `sha256sum` oder durch Lesen der Datei nachgesehen.

| # | Stelle (Zeile) | Angabe in der Meldung | Quelle / Prüfweg | Ergebnis |
|---|---|---|---|---|
| 1 | 10, 59 | `version-0632` = `a82fd34` | `git ls-remote` | richtig |
| 2 | 59 | N7 `3d09742`, N8 `c65f67d`, N9 `5ee907c` | `git ls-remote` | richtig |
| 3 | 59 | N14 `8cef3b4`, N15 `e8c8442`, S1c2 `7acfccb` | `git ls-remote` | richtig |
| 4 | 59 | N6 `3ec3665`, S6b `cb60f8b` | `git ls-remote` | richtig |
| 5 | 60 | keiner der Zweigköpfe (auch N5 `98f63ff`) in `a82fd34` | `git merge-base --is-ancestor` (10×) | richtig |
| 6 | 378 | Fix 3b `9df7bd8` bei keinem Zweig Vorfahr | `merge-base` (7×) | richtig |
| 7 | 10, 365 | N5 lokal `e90b78e` | `git log`: Eltern `a82fd34` `98f63ff` | richtig |
| 8 | 361 | Welle 3c `7c470bd`, `53a4354`, `0329bc9`, `ebfaf7b`, `7e25060` | `git log --first-parent` | richtig |
| 9 | 61, 87 | Lauf 38550615169 success, 11 Jobs success, Release skipped | `gh run view` | richtig |
| 10 | 62, 96 | Job „rest“ 10:37:15–11:01:56 UTC | `gh run view` | richtig |
| 11 | 11, 62 | „rest“ 1441 s, „breite“ 421 s | `zeiten_belegt.txt` | richtig (berichtet) |
| 12 | 99 | 1402 s auf `8f18818`, 1182 s auf `4d77439` | PROTOKOLL Z. 200, 170 | richtig |
| 13 | 63, 382 | 38549211060 (N15): nur rest failure; 1407 s; 3 rote Tests | `gh`, `ci_rest_115802761348.log` | richtig |
| 14 | 63, 383 | 38549419907 (N9): 1260 s; 3 rote | `gh`, `lauf_38549419907_rot.txt` | richtig |
| 15 | 63, 384 | 38554173440 (S1c2): 1572 s; nur `test_normal_1360` | `gh`, `ci_rest_38554173440.log` | richtig |
| 16 | 63, 386 | 38550497158 (N7): 1486 s; 3 rote | `gh`, `ci_38550497158_rest_joblog.txt` | richtig |
| 17 | 63, 387 | 38544277059 (N8): rest cancelled, 2 rote | `gh`, Auszug, `n8/ergebnis.md` Z. 151 | richtig |
| 18 | 384 | Vorlauf 38549977359 auf `bd14178` | `gh`, `s1c2/…/ergebnis.md` Z. 124 | richtig |
| 19 | 102 | Zweige heute 1260–1572 s | Logs (1260/1407/1486/1572) | richtig |
| 20 | 65 | FG-107 +131/−8, +11/−2, +12/−2, sha `58f5137f…4b6b` | `git apply --numstat`, `sha256sum` | richtig |
| 21 | 66, 160 | FG-110 +22/−5, +127/−1, sha `29adca87…47d0` | dto. | richtig |
| 22 | 67, 209 | FG-109 +19/−8, +4/−2, +1/−1, sha `ae54ca32…dfc6` | dto. | richtig |
| 23 | 68, 323 | `e6fe458`: `ui.py` +9/−5, Test +8/−2 | `git show --numstat` | richtig |
| 24 | 46 | `5ee907c`: `ui.py` 9/2 | `git show --numstat` | richtig (dazu neue Testdatei +112, nicht erwähnt, unschädlich) |
| 25 | 37 | `8cef3b4` nur `pruefung/s1_voll.py` +179/−0 | `git show --numstat` | richtig |
| 26 | 278 | `7acfccb` +7/−2, `if ohne is None:` um `assertTrue` | `git show 7acfccb` | richtig |
| 27 | 43, 71 | Windows 884→546, 827→518, „fällig“ 334→21 ms | `messung_windows.md` | richtig |
| 28 | 43 | Speicher 11,1 MB | `n7/fg107/ergebnis.md` Z. 98 | richtig |
| 29 | 152, 72 | Probe 620000–620149, 874 + 882 | `gegenpruefung.md` Z. 83 | richtig |
| 30 | 72, 85 | 30.000 + 15.000 Vergleiche; Text „60.000“ | `gegenpruefung.md` Z. 81–86 | richtig |
| 31 | 42 | KF12, KF14, KF15 vom Prüfer rot, KF13/16 berichtet | `gegenpruefung.md` Z. 125–133 | richtig |
| 32 | 162 | KF18–KF23 11:30:20 UTC, 6/6 rot | FG-110-Antrag Z. 102 | richtig |
| 33 | 163 | 5 neue Tests rot auf `3d09742`, mit Fix 24 OK | FG-110-Antrag Z. 120–124 | richtig |
| 34 | 177 | „fällig“ etwa 0,7 s Container / 0,33 s Windows | FG-107-Antrag (757/700), Windows 334 | richtig |
| 35 | 197 | Container unter Last etwa 9: 1054/949 ms | FG-107-Antrag Z. 26, 82–83 | richtig |
| 36 | 74, 294 | 0.63.1: x = 325, 290 × 18 px, 785 > 781; `452141b` 769 | `*_messung.txt` | richtig |
| 37 | 70, 80 | Kantenglättung 22 (Rechner) / 23 (Prüfungstrainer) | `pixelvergleich_bj04_v2.txt` Z. 10/12 | richtig |
| 38 | 47 | GradientButton-Test 09:41:47, KF 10/10, 42 Fotos | `n9/ergebnis.md` Z. 30–32 | richtig |
| 39 | 324 | V2-Kontrollfehler 11/11 | `n9/ergebnis.md` Z. 25 | richtig |
| 40 | 382 | N15 KF 12/12 (10:03:23), 72 Fälle ≥ 29 | `n15/ergebnis.md` Z. 329–331 | richtig |
| 41 | 384 | S1c2 Container 83/83, k6/k7/k8 je 2/2 | `s1c2/…/ergebnis.md` Z. 116–118 | richtig |
| 42 | 73, 307 | 94 Wörter, 503 Stellen, 14 unsicher, 12 Gruppen | selbst gezählt: Anhang = `LANGE_WOERTER` auf `c65f67d`, Menge gleich, 503 Stellen | richtig |
| 43 | 459–645 | Anhang A gleich Datei des Bauers | `diff` der 94 Tabellenzeilen gegen `n8/Anhang_94_Woerter.md` | richtig (identisch) |
| 44 | 417 | 6 Wörter in zwei Listen; 32 + 55 + 11 = 98 | `vorpruefung_94.txt` | richtig |
| 45 | 309 | 103 lange Wörter, 0 ohne Eintrag | `vorpruefung_94.txt` | richtig |
| 46 | 308 | (i)–(iv) „für alle 127 Einträge“ | `vorpruefung_94.txt`: (i) nur für die 94 neuen | **überzogen** (G5) |
| 47 | 248–255 | N14: 46/46, 59/59, Startwerte 34/35/41, 15:22 statt 13:22, KF 09:27:46 | `n14/ergebnis.md` Z. 98–107 | richtig |
| 48 | 213, 218 | FG-109 KF 10:08:52; `spiel.py:3010`; `f2b59ce8`→`47b8a65a` | FG-109-Antrag Z. 20–23, 155 | richtig |
| 49 | 224 | `test_spiel.py:6357`, `test_rechner_0632.py:347/349` | FG-109-Antrag Z. 122–123 | richtig |
| 50 | 208 | „In 11 weiteren Ansichten zeigt sich kein Unterschied“ | FG-109-Antrag Abschnitt 2 | **ungenau** (M4) |
| 51 | 121–122 | Tor `53a4354` 429 ms/400, 25 ms; Tor `a82fd34` Last 17,05, Wiederholung bei Last etwa 5,2, 27 OK | PROTOKOLL Z. 196, `tor_a82fd34.md` Z. 12, 71 | richtig |
| 52 | 53 | `a`, `n` 0 Byte 05:26; Xvfb 24668, 25923, 3449, 26294, 17620 (02:56–03:52) | `ls --full-time`, `ps` (12:06 UTC: alle 5 laufen noch) | richtig |
| 53 | 12, 449 | Nico 11:54 UTC wörtlich; Meldung 39 Antworten | `Antwort_Nachtrag_39_Nico.md`, `Antwort_Meldung_39_Nico.md`; Empfehlungen in `Meldung_39_Fotos_und_Fragen_Nico.md` (Frage 12 ohne, 18 = b) | richtig |
| 54 | 13, 389 | „In keinem Lauf ist ein Test durch die eigene Änderung rot“ | 38549977359 (`bd14178`) rot durch eigene Variante B | **falsch** (M1) |

---

## 3. Formalien (Meldeformat)
- Zeile 1 „AN: Claude Chat“ und Zeile 2 „ENTSCHEIDUNG NÖTIG: ja …“: vorhanden (Ergänzung siehe G8).
- Kopfblock: 6 Punkte, unter der Grenze von 10 Zeilen.
- Selbstkontrolle am Anfang mit Stufen und Tabellen: vorhanden.
- Stufen belegt/berichtet/vermutet/nicht geprüft: durchgehend verwendet (Ausnahmen G7, M7).
- Jede Frage mit Entscheidungsstufe: ja. Optionen und Empfehlung: ja, außer 3b, 3c und 4c (G10). Frage 7 (b) ist nicht selbsttragend (H4).
- Keine Zeitprognosen: Suche nach Minuten, Stunden, „bald“ usw. ohne Treffer.
- Dokumente am Ende: vorhanden, unvollständig (G12).
- Gelockerte Regeln: nicht offen benannt in H1 (2.15 auf einen Test angewendet, der kein Zeittest ist, Push trotz Tor ROT) und H2 (N5-Bedingung aus Weisung 38/40). Offen benannt und zur Entscheidung gestellt: 7acfccb (Frage 6) und der Wortlaut zum Ziel (M5, nur als Information).
