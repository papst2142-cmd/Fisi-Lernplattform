# Gegenprüfung Meldung 42 (Fassung 1 → Fassung 2)

**Wichtig:** Diese Prüfung ist **nicht unabhängig**. Verlangt war ein eigener Unteragent; in der Sitzung des Verfassers stand dafür kein Werkzeug zur Verfügung. Sie ist ein getrennter, systematischer Prüfgang des Verfassers gegen die Quellen. Eine unabhängige Gegenprüfung durch einen anderen Agenten sollte der Hauptstrang vor dem Versand nachholen.

Geprüfte Datei: `bau_0.63.2/meldungen/Meldung_42_Fragen_aus_dem_Bau.md` (Fassung 1, danach Fassung 2).
Quellen: `OFFEN_FUER_BERICHT.md`; `n6`, `n7`, `n8`, `n9`, `n10/abschluss`, `n11`, `n14`, `n15`, `n16`, `s6b/m38`, `s6b/gp_fg100`, `fg96` jeweils `ergebnis.md`; `antraege/FG-102_Antrag.md`, `FG-103_Antrag.md`; `integration/PROTOKOLL.md`; Weisungen 38/40 und 41; Meldung 41; GitHub-API; Arbeitsbäume N6, N8, N9, N14.

## 1. Prüfgänge und Ergebnis
| Prüfpunkt | Vorgehen | Ergebnis |
|---|---|---|
| Laufnummern | jede Laufnummer im Fließtext gegen die Quelldateien gesucht; neun Läufe zusätzlich per `gh run view` (Zweig, Kopf-SHA, Ergebnis je Job) | alle in den Quellen vorhanden; Kopf-SHA und Ergebnis der neun Läufe stimmen (belegt) |
| SHAs | jede SHA im Fließtext gegen die Quellen; Zweigköpfe per `git ls-remote` | alle vorhanden; Zweigköpfe stimmen (belegt) |
| Zahlen | 47 Zahlen und Kennungen stichprobenartig gegen die Quellen (Messwerte N6/N7, Laufzeiten N8/N14/N9, FG-100, FG-103-Fundstellen, G1-Werte) | alle in den Quellen; „993 s“ und „45 Tests“ aus `n14/logs/s1_voll.log`, FG-100-Zeilenzahl aus dem Diff selbst gezählt |
| Nichts als erledigt, was offen ist | B-M-02 (b), FG-81/FG-92-Abnahme, N14-Merge, Silbenregel, Weg 2, unabhängige Prüfung Satz 5 | überall als offen bzw. „nicht als erledigt“ dargestellt; „gebaut“ nur bei F31, FG-101, Frage 10, N15, FG-100 (alle von Chat freigegeben) |
| Nichts doppelt zu Meldung 41 | jede Frage gegen die Fragen 1–23 von Meldung 41 und Weisung 41 | Fragen 6, 8, 9, 10 sind die in Weisung 41 verlangten Folgeanträge bzw. -fragen, keine Wiederholung; Universal-Mac und `pkill` stehen als verlangte Ergebnisse unter „Zur Kenntnis“ |
| Vollständigkeit gegen `OFFEN_FUER_BERICHT.md` (M42/E2) | Einträge N6, N7, N8, N9, N10, N14, S6b, FG-100, Anträge FG-102/103, FG-97 | alle enthalten; N6 E2-6 als E1-3, N8 E3-1 als E1-1 (begründet) |
| Format | Zeilen 1–2, Kopfblock ≤ 10 Zeilen, Fragen nummeriert mit Problem/Optionen/Empfehlung/Folgen, Belegpfade am Ende, „Zur Kenntnis“, Nico-Liste ohne Fragen, keine Zeitprognosen | erfüllt bis auf GP-4 |
| Öffentlicher Zweig | Suche nach `@`-Adressen, Token, persönlichen Pfaden | nur `@@`-Diffzeilen und ein `@unittest` im zitierten Antrag; kein Fund |
| Anhänge | per Skript wörtlich aus den Quelldateien übernommen | Codeblöcke geschlossen (20 Zäune) |

## 2. Befunde
**hoch:** keine. **mittel:** keine.
**gering:**
- **GP-1** Frage 2: „keine Freigabe deckt eine Änderung“ stand ohne Stufe; FG-60 (zeitabhängige Bestandstests) wurde nicht geprüft. → als „laut Bauer“ gekennzeichnet.
- **GP-2** Frage 1: die Schätzfaktoren 0,4/0,7 waren nicht hergeleitet. → Herleitung ergänzt (GitHub-„rest“ 1279 s gegen lokal etwa 2980 s; Startzeilen 163 gegen 222 s).
- **GP-3** Zur Kenntnis 11: „N2 im Merge-Tor“ war nur aus dem Vorhandensein des Tor-Ordners geschlossen. → als vermutet gekennzeichnet.
- **GP-4** Frage 26 ohne Belegzeile. → ergänzt.
- **GP-5** Frage 18 bestätigt im Kern eine bestehende Regel aus Weisung 41 (Zur Kenntnis 5). → nicht geändert: der Bauer hat sie als E2 gestellt, sie betrifft das Merge-Tor.

## 3. Hinweise ohne Änderung
- Der Log `n14/logs/n14_g8_zweites_ersetzen.log` ist ein Erfassungslauf mit noch leerem Sollwert (Ende „FAILED“); die Werte stehen in der Ausgabe. In der Meldung so offen genannt.
- Das volle N14-Prüfprogramm hat noch keinen ganzen grünen Lauf (2 rot im letzten ganzen Lauf, Teil-Nachlauf grün). In Frage 4 offen genannt.
- Die unabhängige Prüfung (i)–(iii) der Satz-5-Streichung (Weisung 38/40) wurde im gemeinsamen Ordner nicht gefunden. In „Zur Kenntnis“ 3 genannt.

## 4. Fazit
Fassung 2 ist nach diesem Prüfgang versandfähig. Einschränkung: nicht unabhängig (siehe oben).
