# Erledigung der unabhängigen Gegenprüfung zu Meldung 43

Stand 14.10.2026, nach 09:10 UTC. Bezug: `Gegenpruefung_Meldung_43_unabhaengig.md` (2 hoch, 7 mittel, 8 gering).
Fassung 1 liegt als Kopie unter `meldungen/Meldung_43_Fragen_aus_dem_Bau_Fassung1.md`. Fassung 2 ist `meldungen/Meldung_43_Fragen_aus_dem_Bau.md`.
Nichts committet, nichts gepusht. Neu nachgesehen (belegt, nur lesend):
- `git ls-remote`: `version-0632` = `8f18818`, `meldungen` = `ec41b37`.
- `gh run view 38537239045`: `in_progress`; alle Jobs grün außer „Tests Linux (rest)“, der noch läuft.
- `integration/tor/tor_8f18818.md` gelesen; `werkzeug/bekannt_rot_github.txt` hat 0 aktive Zeilen.
- Schluss von `integration/PROTOKOLL.md` gelesen (Eintrag ~08:55 UTC zu Fix 3b).

| Befund | Erledigung | Stelle in Fassung 2 |
|---|---|---|
| H1 Stand veraltet | erledigt: Tor `8f18818` grün mit Meldung, Liste leer, Push `8f18818`, Lauf 38537239045 „läuft“ (nicht fertig beim Schreiben), Optik offen Fix 3b, S5c-Konfliktrisiko | Kopfblock 2, Selbstkontrolle (3 Zeilen), Abschnitt C (FG-97, Schlusssatz), Weitere Punkte 3, 8 und 9 |
| H2 Frage 10 „keine Regel“ | erledigt: FG-96 Nr. 5 wörtlich zitiert, (b) = geltende Regel, (a) offen als Lockerung der Meldepflicht; Empfehlung auf (b) geändert | Frage 10, Kopfblock 3 |
| M1 | erledigt: 600–750 s gelten für ganz „breite“; `test_rechner_seite_breite` war schon in den 216 s | Frage 10, Stand |
| M2 | erledigt: „alle Geldbeträge“ gestrichen; €-Stellen im PC-Spiel (Z. 1287, 1433, 3009, 3017, 3028, 5794, aus der Gegenprüfung) und Liste als Stoppgrenze genannt | Frage 6 (b) |
| M3 | erledigt: Chats Satz im Wortlaut, unverändert | Frage 9, Problem |
| M4 | erledigt: FG-107-Punkt gilt als schon in Meldung 39 (Frage 18); Vorwegnahme der Unterzeile in Meldung 39 offen genannt | Frage 3, Nachtrag für Nico |
| M5 | erledigt: pixelgleich nur bei „Normal“ belegt; Groß und Sehr groß vermutet | Frage 8 |
| M6 | erledigt: „10 Ansichten, je 6 Kombinationen“ | Frage 3 |
| M7 | erledigt: KF1–KF11 vorab, KF12–KF16 beim Bau, KF15 nicht belegt | Frage 7, Empfehlung |
| G1 | erledigt: Zweigstand; Lauf auf dem End-Stand vor dem Merge | Weitere Punkte 6 |
| G2 | erledigt: „gebaut, grün auf `cb60f8b`, mit dem S6b-Merge in der Integration“ | Kopfblock 4, Abschnitt C, Weitere Punkte 5 |
| G3 | erledigt: 60 Tests = 5 Klassen, nicht die ganze Datei | Frage 4 |
| G4 | erledigt: „sinngemäß nach 2.5“ | Frage 4 |
| G5 | erledigt: Randbemerkung „später“ ergänzt | Frage 9 |
| G6 | erledigt: „Folge:“ bei allen Optionen von Frage 8 und 9 | Fragen 8 und 9 |
| G7 | erledigt: als E1-5 gekennzeichnet; „wieder rot = echt rot“ offen genannt | E1-Tabelle, Weitere Punkte 8 |
| G8 | erledigt: Tor `8f18818` ohne roten Zeittest | Abschnitt C (FG-108), Weitere Punkte 8 |

Nicht übernommen: nichts.
Offen: das Ergebnis von Lauf 38537239045. Es wird nachgereicht, sobald er fertig ist. Vor dem Push auf `meldungen` `git ls-remote` erneut ausführen.
Die Selbstprüfung (`Selbstpruefung_Meldung_43.md`) bezieht sich auf Fassung 1; in den Punkten unter H1 ist sie überholt.
- Nachtrag Koordinator: Lauf 38537239045 nach Abschluss eingetragen (ganz gruen, rest 08:44:19-09:08:17 UTC).
