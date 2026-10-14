# Erledigung der unabhängigen Gegenprüfung zu Meldung 42 (Fassung 3)

Grundlage: `Gegenpruefung_Meldung_42_unabhaengig.md`. Fassung 2 bleibt als `meldungen/Meldung_42_Fragen_aus_dem_Bau_Fassung2.md` erhalten; Fassung 3 steht in `meldungen/Meldung_42_Fragen_aus_dem_Bau.md`.

| Befund | Erledigt durch | Stelle in Fassung 3 |
|---|---|---|
| M-1 (FG-100: 10 statt 9 Codezeilen) | Korrigiert auf 9 Code- und 4 Kommentarzeilen in `log_record`, 8 Zeilen weg in `reset_records`; Diff gesamt 13 Einfügungen, 9 Löschungen. Ursache: `grep -c "^+"` hatte die Kopfzeile `+++` mitgezählt. Frage 3 bleibt vorn, weil die Auflage nicht eingehalten wurde; sie blockiert jetzt nur zusammen mit FG-81/FG-92, und der Umfang ist unstrittig (alle zählen 9). | Kopfblock 1, Selbstkontrolle, Frage 3 (Überschrift, Stand, Blockiert) |
| Überholt: N2 gemergt, Tor grün (PROTOKOLL Z. 192) | S6c, N1 und N2 lokal gemergt, N2 `0329bc9` Tor grün, nicht gepusht, `version-0632` weiter `e0f9c7e` | Zur Kenntnis 11; GP-3-Vermerk als überholt |
| G-1 (Lauf 38509635406 auch „rest“ rot) | Per `gh run view` nachgeprüft: „windows“ und „Tests Linux (rest)“ rot; Ursache „rest“ nicht geprüft, als vermutet angegeben | Selbstkontrolle, Zur Kenntnis 5 |
| G-2 (Satz-5-Prüfung läuft) | „läuft (`s6b/gp_satz5/`, seit etwa 06:01 UTC)“ plus Platzhalter ⟦ERGEBNIS gp_satz5 …⟧ zum Einsetzen; beim Schreiben noch kein `ergebnis.md` | Zur Kenntnis 3 |
| G-3 (= Überholt-Befund) | siehe oben | Zur Kenntnis 11 |
| G-4 (Weisung 41 ZK 5 gilt nur für GitHub) | Frage 18: Regel nur für GitHub, Merge-Tor ungeregelt; offen gesagt: zwei Zeittests betroffen, sonst (b). E1-4: „sinngemäß angewandt“. | Frage 18, E1-4, Vermerk GP-5 |
| G-5 (Frage 6 (c) durch Weisung 41 Abschn. 13 ausgeschlossen) | Option (c) gestrichen; Hinweis mit Zitat-Bezug (Wortlaut „B-J-04 wird nicht verschoben.“ geprüft) | Frage 6 Optionen |
| G-6 (Frage 20 schon entschieden, N6-F5) | Nummer behalten (keine Verweisverschiebung), als „schon entschieden, nur Rückfrage zum Zeitpunkt“ markiert; ohne Antwort gilt (a). Kopfblock: 25 offene Fragen | Frage 20, Kopfblock 3 |
| G-7 („N9-F8“ unerklärt) | Erklärt: bedingte Erlaubnis aus Weisung 38/40, Bedingung und hier belegte Messung genannt | Frage 4 (a) |
| G-8 (Frage 18 (b) ohne FG) | FG-108 vergeben, Zeile in der Tabelle von Frage 26 ergänzt | Frage 18 (b), Frage 26, Kopfblock 4 |
| G-9 (E1-1 Begründung zu weit) | Präzisiert: Weisung 22 F6 (a) betraf `ui.Card`-Unterschrift, hier Bereichstitel `ui.py:114`; sinngemäß, bei strenger Lesart E2 | E1-1 |

Prüfung nach dem Edit: Zeilen 1–2 unverändert, Codezäune 20 (gerade), alle Ersetzungen mit Eindeutigkeits-Assertion. Nichts committet, nichts gepusht.
