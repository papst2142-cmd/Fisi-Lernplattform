# Unabhängige Gegenprüfung Meldung 42 (Fassung 2)

Prüfer: eigener Unteragent, nicht der Verfasser der Meldung. Nichts an der Meldung geändert, nichts committet oder gepusht.
Geprüfte Datei: `bau_0.63.2/meldungen/Meldung_42_Fragen_aus_dem_Bau.md` (Stand 14.10. 06:00:02 UTC, 989 Zeilen). Zeilennummern unten beziehen sich auf diese Fassung.
Grundlagen: REGELN_BAU_0.63.2.md, BRIEF_GEMEINSAM_1410.md, Weisungen 38/40 und 41, Meldung 41, OFFEN_FUER_BERICHT.md, `ergebnis.md` von n6, n7, n8, n9, n10/abschluss, n11, n14, s6b/m38, s6b/gp_fg100, fg96, antraege/FG-102 und FG-103, integration/PROTOKOLL.md, Logs (n8, n14).
Eigene Nachprüfung (nur lesend): `git ls-remote origin`, `gh run view` für alle 13 genannten Läufe, `git show` und `git diff` im Repo `papst2142-cmd/Fisi-Lernplattform`.

## 1. Ergebnis der Prüfgänge

| Prüfpunkt | Vorgehen | Ergebnis |
|---|---|---|
| Zweigköpfe (Z. 21) | `git ls-remote`: N6 b119259, N7 1e7965a, N8 927ef5f, N9 72afbe1, N10 f29478b, N11 dfc73da, N14 053931d, N15 5e639c2, N16 e32064a, S6b d96dc5e, version-0632 e0f9c7e | alle stimmen (belegt) |
| Läufe (Z. 20, 434–438) | alle 13 Läufe mit `gh run view`: Kopf-SHA, Zweig, Ergebnis je Job | Kopf-SHA und Ergebnis stimmen bei allen 13; N8 „rest“ 04:15:42–04:46:00 cancelled stimmt; zur Ursache bei 38509635406 siehe G-1 |
| N14-Commits (Z. 25, 430) | `git log` auf 053931d | fff5824 und 37d0ab6: Autor- und Commit-Zeit 03:44:53 UTC, also vor der Weisung 41 (03:55:06 UTC) (belegt) |
| N14-Zahlen | `s1_voll.log` (45 Tests, 993,3 s, 2 FAIL Löscharten U1/U3), `s1_voll_loescharten_lauf2.log` (8 OK), `n14_test_s1_lauf3_end.log` (35 OK, 194,9 s), „15 Etiketten … Fehler []“ (Z. 923), zweites Ersetzen 2/2 im Erfassungslauf | stimmen |
| N8-Zahlen | `ci_rest_927ef5f.txt`: 239/301/455/222 s, 4279 s, EXIT 0; `n8/ergebnis.md`: 380/342/589/289 s, 163 s | stimmen; 4279 − 1217 − 80 ≈ 2980 s (Herleitung Z. 41 schlüssig) |
| FG-96-Zahlen | `fg96/ergebnis.md`: breite 216 s, rest 1182 s; 1279 s auf e0f9c7e; Erwartung 600–750 s (Weisung 38/40 Z. 56) | stimmen |
| N6 | `git show b119259:test_vorladen.py` Z. 211–215: Schlange `[("view","calc")]`, ein `_step()`, `assertIsNotNone(…built("calc"))`, `assertTrue(pre.done)`; Messwerte 1178→385, 1176→382, 8548→10082, 248/241/250/203/204/217 ms; Kontrollfehler 25/25 | stimmen |
| N8 Code-Stellen | `apk_pruefen.py:31`, `fisi_lernen.py:794`, `fisi_core.py:4837` (Handy-Zeile 26 Zeichen), `app_gui.py:159` `"%s starten"` auf 927ef5f | stimmen |
| N7, N9, N10, FG-102, FG-103, S6b m38 | Stichproben aus den `ergebnis.md`/Anträgen (z. B. 2456→205, 3744/5186, 90/90, „30 von 30“, 75 OK, 595 Aufgaben, 4 Fundstellen, 1408 Bytes/6 Satzgrenzen) | stimmen |
| FG-100-Zeilenzahl (Z. 78) | eigene Zählung im Diff | **stimmt nicht**, siehe M-1 |
| Offenes nicht als erledigt dargestellt | B-M-02 (b) (Frage 10), FG-81/FG-92 (Z. 7, 85, 432), N14 (Z. 7, 94, 102–103, 431), Silbenregel, Weg 2 | richtig als offen dargestellt; zwei Stellen sind seit dem Schreiben überholt (G-2, G-3) |
| Doppelt zu Weisung 41/38-40 | jede Frage gegen beide Weisungen | keine verdeckte Wiederholung; drei Stellen sollten den Bezug deutlicher nennen (G-4, G-5, G-6) |
| Format | Z. 1–2 Kopfzeilen, Kopfblock 7 Punkte (≤ 10), 26 Fragen mit Problem/Stand/Optionen/Empfehlung/Belegen, Belegstufen, keine Zeitprognosen | erfüllt; kleine Lücke zur Selbsttragfähigkeit siehe G-7 |
| FG-Nummern (Frage 26) | ab FG-104 (Weisung 41 Abschn. 19: „Nächste freie FG: FG-104“) | widerspruchsfrei: FG-104 (Frage 2), FG-105 (14), FG-106 (7), FG-107 nur bei 4 (b); dieselben Nummern in Z. 69, 162, 266, 403–411; kleine Lücke siehe G-8 |

## 2. Befunde

### hoch
keine.

### mittel

**M-1 (Z. 78, auch Z. 24): Die Zahl der FG-100-Zeilen ist falsch, obwohl sie als „belegt (gezählt)“ steht.**
Eigene Zählung: `git diff 31b0c48 d96dc5e -- fisi_core.py` ist byteweise gleich mit `s6b/m38/fg100_fisi_core.diff` und ergibt **13 Einfügungen und 9 Löschungen**.
- In `log_record` kommen 13 Zeilen hinzu: **9 Codezeilen und 4 Kommentarzeilen**. Die 9 Codezeilen sind `stamp = self._stamp()`, `import fisi_sync`, `mark = …`, `local = …`, die Bedingung über 2 Zeilen, die neue Stempel-Zuweisung über 2 Zeilen und die geänderte INSERT-Parameterzeile `(*stamp, …)`. Dazu kommt 1 Löschzeile (`(*self._stamp(), …)`).
- In `reset_records` werden 8 Zeilen entfernt (5 Kommentar- und 3 Codezeilen). Diese Zahl stimmt.
- In der Meldung steht „10 hinzugefügte Codezeilen, davon ersetzt eine die bisherige Einfüge-Zeile, dazu 4 Kommentarzeilen“, also zusammen 14. Richtig sind **9** Codezeilen, die ersetzte INSERT-Zeile schon eingerechnet. Das stimmt mit dem Bauer überein (`s6b/m38/ergebnis.md` Z. 50: „9 Code- und 4 Kommentarzeilen“) und mit der Gegenprüfung (`s6b/gp_fg100/ergebnis.md` Z. 41: „Zeilenzahl 9“).
- Der Fehler übertreibt nur und schadet in der Sache nicht. Er steht aber in genau der Frage, in der es um die Zeilenzahl geht, und ist dort ausdrücklich als „belegt (gezählt)“ ausgewiesen. Die Selbstprüfung hat ihn übersehen.
- **Korrektur Z. 78:** „Diff (belegt, gezählt; `git diff 31b0c48 d96dc5e -- fisi_core.py` = 13 Einfügungen, 9 Löschungen): in `fisi_core.DBManager.log_record` 9 Codezeilen (davon ersetzt eine die bisherige Parameterzeile des INSERT) und 4 Kommentarzeilen; in `reset_records` 8 Zeilen der alten Lösung entfernt (5 Kommentar, 3 Code).“ Z. 24 bleibt dann richtig.

### gering

**G-1 (Z. 434): Die Begründung, warum Lauf 38509635406 rot ist, ist unvollständig.**
Laut `gh run view` sind zwei Jobs rot: `windows` (Schritt „Inno Setup bereitstellen“, die gewollte Probe) **und** „Tests Linux (rest)“. In der Meldung steht nur „weil … die Inno-Fehlschlag-Probe gewollt rot war“.
Korrektur: „… rot durch die gewollt rote Inno-Probe (Job windows) und ‚Tests Linux (rest)‘ (Ursache nicht geprüft, vermutlich die bekannten Breitentests)“.

**G-2 (Z. 85, 432): Die unabhängige Prüfung der Satz-5-Streichung ist angelaufen.**
Der Ordner `bau_0.63.2/s6b/gp_satz5/` wurde um 06:01:50 UTC angelegt, also nach der Meldung. Darin schreibt ein Log (`logs/tests_d96dc5e_sicherung_bg08.txt`), ein Ergebnis gibt es noch nicht. Die Aussage „liegt noch nicht vor“ ist deshalb weiter richtig.
Vorschlag: Vor dem Versand nachsehen. Liegt dann `gp_satz5/ergebnis.md` vor, Z. 432 und den Kopfblock (Z. 7) anpassen. Sonst so ergänzen: „läuft seit 06:01 UTC (`s6b/gp_satz5/`), Ergebnis steht aus“.

**G-3 (Z. 440): Der Stand der Integration ist überholt.**
Laut `integration/PROTOKOLL.md` Z. 192 ist Welle 3c bei 3/5: N2 085b72d ist gemergt (→ 0329bc9), das Merge-Tor `tor_0329bc9.md` ist grün. Der Hinweis „für N2 lief ein Merge-Tor, vermutet, nicht abgeschlossen gesehen“ ist damit überholt.
Außerdem fehlt der Hinweis, dass die Merges nur lokal sind (version-0632 auf GitHub steht weiter auf e0f9c7e, belegt).
Korrektur: „S6c, N1, N2 lokal gemergt (Tor N1 rot nur durch einen lastabhängigen Zeittest, siehe E1-4; Tor N2 grün), noch nicht gepusht …“.

**G-4 (Z. 313, 426): Frage 18 und E1-4 stellen die Regel aus Weisung 41 (Zur Kenntnis 5) weiter dar, als sie geht.**
Weisung 41 sagt zu `test_vorladen` nur „Beobachten. Tritt er auf GitHub rot auf, gilt der Katalog (kein Einzelneustart, ganzer neuer Lauf); wird er häufiger rot, kommt er als eigenes Thema (‚flaky‘) zu mir“. Eine Regel für das Merge-Tor im Container („einzeln wiederholen, dann weiter“) enthält sie nicht.
Korrektur in Z. 313 und Z. 426: „angelehnt an deine Regel … (dort nur für GitHub: Katalog; für das Merge-Tor gibt es noch keine Regel, deshalb diese Frage)“. In Frage 18 außerdem offen sagen: Weil inzwischen zwei Zeittests betroffen sind, liegt der Fall „wird er häufiger rot“ aus Weisung 41 nahe.

**G-5 (Z. 132): Option (c) in Frage 6 bietet ein Verschieben an, das der Chat schon ausgeschlossen hat.**
Weisung 41 Abschn. 13: „B-J-04 wird nicht verschoben.“
Korrektur: „(c) Keine Erweiterung. Folge: B-J-04 bleibt für diese Knöpfe offen; ein Verschieben hast du in Weisung 41 (Abschn. 13) ausgeschlossen, es bliebe nur Nico.“

**G-6 (Z. 333–339): Frage 20 hat der Chat zum Teil schon beantwortet.**
Weisung 38/40 Tabelle N6-F5 sagt: „Windows über 150 ms als Befund“. Option (a) „als Befund in den Bericht“ ist damit schon entschieden. Offen ist nur noch „jetzt weiter teilen oder nach S5c neu messen“.
Korrektur: Im Problem-Absatz so sagen („Befund ist nach N6-F5 schon gesetzt; offen ist nur, ob jetzt weiter geteilt wird“) und die Optionen darauf zuschneiden.

**G-7 (Z. 98): „Wie bei N9-F8“ ist nicht selbsttragend.**
Der Begriff steht nicht im Glossar. Er stammt aus Weisung 38/40 Z. 124, und dort gilt als Bedingung „zuerst durch Messung zeigen, dass der volle Satz das Zeitbudget sprengt“. N9 hat diesen Weg am Ende gar nicht genutzt (`n9/ergebnis.md` Z. 76: „nicht gebaut, keine Überschreitung“).
Korrektur: „Wie in Weisung 38/40 für N9-F8 bedingt erlaubt (Kern in der CI, voller Satz im Container mit Log; Bedingung: Messung zeigt, dass der volle Satz das Zeitbudget sprengt; hier belegt: rund 1000 s gegen ‚rest‘ an der 30-min-Grenze)“.

**G-8 (Z. 310, 401–411): Frage 18 (b) braucht eine neue FG, Frage 26 nennt dafür aber keine Nummer.**
Bei Frage 4 (b) ist das mit FG-107 gelöst.
Korrektur: In der Tabelle eine Zeile „FG-108 | nur falls Frage 18 (b) (Zeitgrenzen nur auf GitHub)“ ergänzen oder in Frage 18 (b) „Nummer nach deiner Vergabe“ schreiben. Am Grundsatz „nächste freie FG-104“ ändert das nichts.

**G-9 (Z. 423): Die Begründung von E1-1 deckt den Fall nur sinngemäß.**
Weisung 22 Frage 6 (a) betrifft die Trennregel in der **Unterschrift** von `ui.Card` (REGELN Z. 82). E1-1 betrifft dagegen den **Bereichstitel** (`title.upper()`, `ui.py:114`).
Korrektur: „sinngemäß nach Weisung 22, Frage 6 (a) (dort für die ui.Card-Unterschrift)“. Wer strenger liest, stuft es als E2 ein.

## 3. Hinweise ohne Befund
- Die beiden N14-Commits aus der Zeit vor der Weisung sind auf GitHub Vorfahren von 053931d, also gepusht. In OFFEN_FUER_BERICHT steht noch „nicht gepusht“. Die Meldung (Z. 430) ist richtig, die Notiz ist veraltet.
- Die Schätzung „breite“ 1100–1650 s (Z. 41) ist mit der 1217-s-Summe nachrechenbar: 216 + 400…550 (N5) + 0,4…0,7 × 1217. Sie ist richtig als „vermutet“ gekennzeichnet. N8 selbst schreibt „deutlich über 1350 s“. Die Meldung ist hier vorsichtiger, und das ist begründet.
- Kopfblock Z. 13: Gebaut sind außerdem der Umbau in Frage 10 und die Bindestrich-Trennung in Frage 11. Gefragt wird dort aber nach dem Schließen bzw. nach der Silbenregel. Kein Widerspruch.
- Keine Zeit- oder Terminprognosen gefunden. Dauern wie „rund 1000 s“ sind Messwerte.

## 4. Fazit
Versandfähig nach Korrektur von **M-1**. G-2 und G-3 vor dem Versand auf den aktuellen Stand bringen. Die übrigen geringen Befunde verbessern die Klarheit, sind aber nicht zwingend.
