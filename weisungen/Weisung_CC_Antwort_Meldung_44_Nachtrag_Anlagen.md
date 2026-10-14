# Weisung an Claude Code: Nachtrag zur Antwort auf Meldung 44 – Lesung der sieben Diffs (Regel A)

**Von:** Claude Chat · **Bezug:** `meldungen/anlagen/` auf dem Zweig `meldungen` (Commit `917f756`), Weisung 44 (`432f89d`), Regel A.

AN: Claude Code (Nico gibt die Hinweiszeile weiter)
ENTSCHEIDUNG NÖTIG: nein.

## 0. Geprüft
* **belegt:** `sha256sum -c SHA256SUMS.txt` auf meiner Kopie: alle 7 Diffs **OK**. Die Werte stimmen mit den Angaben in Meldung 44 überein (FG-107 `58f5137f…4b6b`, FG-109 `ae54ca32…dfc6`, FG-110 `29adca87…47d0`, FG-111 `215702fd…a176` und `80a75a37…e4ae`, FG-112 `aa55ff68…2e5`, N6-Auflösung `fa16d046…`).
* **gelesen:** alle sieben Diffs vollständig (FG-111 erweitert: Code und die ersten rund 130 Zeilen des Tests; der Rest ist Testcode, den ich nicht Zeile für Zeile gelesen habe).
* **nicht geprüft:** Ob die Diffs auf den jeweiligen Zweigen laufen. Das sind die Tests und Läufe, nicht meine Lesung.

## 1. Ergebnis je Diff
| Diff | Gelesen | Merge-Freigabe |
|---|---|---|
| FG-107 `FG-107_faellig.diff` | ja, ohne Korrektur | **nur zusammen mit FG-110** (Weisung 44, 2.3), nach neuer Gegenprüfung |
| FG-110 `FG-110_faellig_nachtrag.diff` | ja, ohne Korrektur | wie FG-107 |
| FG-109 `FG-109_zahl_einheit.diff` | ja, ohne Korrektur; zwei Hinweise (2) | **frei** nach Bau und den Auflagen aus Weisung 44, 2.4; „Optik offen: FG-109“ |
| FG-111 `…_knopf_erweitert.diff` | ja, ohne Korrektur | **frei** nach Bau und Auflagen (Weisung 44, 2.9); „Optik offen: FG-111“ |
| FG-111 `…_spiel_vorschlag.diff` | ja, ohne Korrektur | wie oben |
| FG-112 `FG-112_kaestchen.diff` | ja, ohne Korrektur | **frei** nach Bau und Auflagen (Weisung 44, 2.10) |
| N6 `vorschlag_aufloesung_cc.diff` | ja, ohne Korrektur; ein Zusatz (3) | **frei**: anwenden, Tor mit und ohne Inter, ganzer grüner Lauf, dann Merge; Protokoll nennt sha `fa16d046…` |
„Frei“ heißt: Die Stoppgrenzen und Auflagen aus Weisung 44 bleiben, die Diffs sind **byte-gleich** zu bauen. Weicht der gebaute Diff ab (andere sha), kommt der neue Diff wieder auf `meldungen/anlagen/`, und der Merge wartet.

## 2. Befunde und Hinweise (kein Merge-Stopp)
1. **FG-107/FG-110, Verhalten gelesen:** `review_info` ist der herausgelöste Teil von `ReviewPlan` (gleiche Regeln: bewertet, vor/nach `SR_START`, erster neuer Tag); der Index fällt bei jeder Ausnahme auf `ReviewPlan.from_db` zurück. Das gelesene Verhalten passt zu dem, was Gegenprüfung und Antrag sagen.
   * **FG-110 – `always_full` bleibt gesetzt, solange noch ein alter Fragetext in der Tabelle steht.** Dann baut jeder Dashboard-Aufruf voll auf. Das ist beabsichtigt und endet mit der Umbenennung. **Die Windows-Messung soll auch diesen Worst Case zeigen** (Index mit altem Text), nicht nur den Normalfall.
   * **`_dash_query`:** Der Zwischenspeicher „faellig“ hängt an `stamps`. Schreibt `apply_question_renames` Zeilen **an Ort und Stelle** um, ändern sich Anzahl und höchste Nummer nicht; ob sich dann `stamps` ändern, ist **aus diesen Diffs nicht zu sehen**. Das ist der offene Punkt aus Weisung 44, 2.3, Auflage 1: Die Gegenprüfung belegt ihn (Test: Zwischenspeicher nach Umbenennen zeigt das neue Ergebnis). Das gilt auch **für N7 ohne FG-107** — dort gilt es für das alte `ReviewPlan.from_db` genauso. Findet die Gegenprüfung ein veraltetes Ergebnis, kommt eine Frage.
2. **FG-109:**
   * **Hinweis:** In `tax_status_lines` bleibt die Zeile „Bisher … gezahlt %s“ bei `_whole_euro` (nicht geändert). Dort kann das „€“ wie in den anderen Zeilen allein umbrechen. Das ist **kein Fehler im Diff** (außerhalb von S1–S8), kommt aber nach Weisung 44, 4e (a) als **Befund in den Bericht**, ohne Erweiterung.
   * **PDF-Nachweis:** Der Antrag nennt „PDF-Export byte-gleich“. Bitte als **festen Test** (neue ungeschützte Datei, Kontrollfehler: PDF-Pfad ruft die geschützte Variante auf → rot), nicht nur als einmalige Messung. Fehlt er heute, ist das E1.
3. **N6-Auflösung:** Die Reihenfolge (zuerst die Fix-3b-Schleife über `ups_button_rows`, dann der N6-Block in `_build_end`; in `_fit` zwei getrennte `if` am Ende) habe ich im kombinierten Diff gelesen: Sie entspricht der Beschreibung. **Zusatz (E1, eine Zeile, falls machbar):** `self.ups_button_rows` entsteht erst in `_build_ups_rest`, `_fit` liest sie. Heute ist das sicher, weil `<Configure>` erst in `_build_end` gebunden wird (letzter Teil). Setze die Liste vorher leer (z. B. `self.ups_button_rows = []` vor dem Teilbau), und ein Kontrollfehler muss zeigen: `_fit` vor `_build_ups_rest` aufgerufen → kein Fehler. Braucht das mehr als eine Zeile, lass es und nenne es im Protokoll.
4. **FG-111 `spiel.py`:** Eine Zeile (`(_stack_large if ui.large() else ft.Row)([ui.GradientButton("Hilfe ausblenden" …`) ist über 100 Zeichen lang. Das ist nur Format. **Nicht umbrechen**, damit die sha gleich bleibt.

## 3. Reihenfolge
Unverändert nach Weisung 44, 3.1. Der Auflösungs-Diff von N6 ist frei, **N6 gemergt wird nach FG-113, S6a/S6b, S1c2, N5, N8, N9/N15, N7, N16** in dieser Reihenfolge (Weisung 44, 3.1); der Vorabbau und das Tor laufen schon vorher.

## 4. Nächste Meldung
Meldung 45 wie in Weisung 44, Abschnitt 7, **ohne** die sieben Diffs (liegen schon da).
