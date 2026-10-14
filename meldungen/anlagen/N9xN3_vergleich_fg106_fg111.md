# Auflage 1 (Weisung 45, Frage 2): Vergleichsbeleg FG-106/FG-111 gegen Integrationsdiff

Stand: Vorabbau `version-0632-n9-n3` = `9e72864` (Merge a82fd34 + 5185e78 mit Aufloesung A). Erzeugt 14.10.2026 ~16:55 UTC.
Stufe: **belegt** (maschineller Hunk-Vergleich, Skript `vergleich.py` im selben Ordner).

## Methode
* N9-Seite: `git diff -U0 e0f9c7e 5185e78 -- mobile/src/spiel.py` (e0f9c7e = merge-base von a82fd34 und 5185e78; auf N9 beruehren nur die Commits 352abad FG-106 und 5185e78 FG-111 die Datei) = FG-106 + FG-111 zusammen, 13 Hunks.
* Integrationsseite: `git diff -U0 a82fd34 9e72864 -- mobile/src/spiel.py`, 14 Hunks (die Kreditstelle ist dort zwei Hunks: Kommentar + Code).
* Jeder Hunk bekommt den Namen der Stelle, die `@@`-Zeilennummern werden durch den Namen ersetzt (sie verschieben sich, weil N3 vorher Zeilen einfuegt), die `+`/`-`-Zeilen bleiben **byte-genau**. Daraus zwei Textdateien (`n9_5185e78_hunks.txt`, `integration_9e72864_hunks.txt`) und deren Diff = **Diff der Diffs** `vergleich_fg106_fg111.diff`.

## Ergebnis
Alle Stellen ausser Mitarbeiter- und Kreditreihe sind nicht nur inhaltlich, sondern **byte-gleich** (gleiche `-`- und `+`-Zeilen). Der Diff der Diffs enthaelt nur die zwei Konfliktstellen.

| Stelle | Hunk N9 (gg e0f9c7e) | Hunk Integration (gg a82fd34) | Vergleich |
|---|---|---|---|
| Helfer _stack_large | `@@ -1757,0 +1758,11 @@ def market_box(lines):` | `@@ -1763,0 +1764,11 @@ def market_box(lines):` | gleich |
| Profil-Reihe (Spielfigur) | `@@ -2091 +2102 @@ class GameScreen:` | `@@ -2097 +2108 @@ class GameScreen:` | gleich |
| Karteikarten-Knopf (Lueckenhinweis) | `@@ -2384 +2395 @@ class GameScreen:` | `@@ -2390 +2401 @@ class GameScreen:` | gleich |
| Hilfe-Reihe Ticket (Abgeben/Hilfe) | `@@ -2425 +2436,2 @@ class GameScreen:` | `@@ -2431 +2442,2 @@ class GameScreen:` | gleich |
| Statistik-Kacheln | `@@ -2770,2 +2782,5 @@ class GameScreen:` | `@@ -2776,2 +2788,5 @@ class GameScreen:` | gleich |
| Neuere/Seite/Aeltere | `@@ -2826 +2841 @@ class GameScreen:` | `@@ -2832 +2847 @@ class GameScreen:` | gleich |
| Hilfe-Reihe Angebot (Hilfe ausblenden/Abbrechen) | `@@ -3067 +3082 @@ class GameScreen:` | `@@ -3073 +3088 @@ class GameScreen:` | gleich |
| Faehigkeiten-Balken (Kategorie, Teil 1) | `@@ -3424,0 +3440,15 @@ class GameScreen:` | `@@ -3440,0 +3456,15 @@ class GameScreen:` | gleich |
| Faehigkeiten-Balken (Kategorie, Teil 2) | `@@ -3426,10 +3456 @@ class GameScreen:` | `@@ -3442,10 +3472 @@ class GameScreen:` | gleich |
| Faehigkeiten-Balken (Themen) | `@@ -3441,11 +3462,14 @@ class GameScreen:` | `@@ -3457,11 +3478,14 @@ class GameScreen:` | gleich |
| KONFLIKT Mitarbeiter (Weiterbilden/Themen/Entlassen) | `@@ -3488 +3512 @@ class GameScreen:` | `@@ -3516,3 +3540,7 @@ class GameScreen:` | VERSCHIEDEN |
| KONFLIKT Kredit (Tilgungsplan/Abloesen) | `@@ -4172 +4196 @@ class GameScreen:` | `@@ -4201 +4229 @@ class GameScreen: + @@ -4205,2 +4233,5 @@ class GameScreen:` | VERSCHIEDEN |
| Loesung einreichen (Farm) | `@@ -4753 +4777 @@ class GameScreen:` | `@@ -4803 +4834 @@ class GameScreen:` | gleich |

Hinweise:
* Die Weisung nennt "Profil-Reihe, Hilfe-Reihen, Statistik-Kacheln, Faehigkeiten-Balken, Neuere/Seite/Aeltere, Loesung einreichen". Zusaetzlich im Diff und ebenfalls gleich: der Helfer `_stack_large` und der Karteikarten-Knopf im Lueckenhinweis (`expand=ui.large() or None`, FG-106).
* Mitarbeiter/Kredit: auf der Minus-Seite steht im Integrationsdiff die N3-Reihe (`alignment = None`, `wrap=True`), auf der N9-Seite die alte `ft.Row([... expand=True ...])`. Die Plus-Seite ist die freigegebene Aufloesung A (`if ui.large(): _stack_large(...) else: N3-Reihe`).
* Byte-Gleichheit der ganzen Aufloesung mit den gelesenen Diffs: `byte_gleich.log` (87a565ad / 0aa67be1 / 19becdd8, alle drei gleich).

Dateien: `vergleich_fg106_fg111.diff`, `n9_5185e78_hunks.txt`, `integration_9e72864_hunks.txt`, `vergleich.py`.
