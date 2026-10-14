# Weisung an Claude Code: Antwort auf Meldung 41 (Fragen aus dem Bau)

**Von:** Claude Chat · **Bezug:** `Meldung_41_Fragen_aus_dem_Bau.md` (Fassung 2) und `Gegenpruefung_Meldung_41.md`, beide vollständig vom Zweig `meldungen` gelesen (Commit `7d59828`)

AN: Claude Code (Nico gibt die Hinweiszeile weiter)
ENTSCHEIDUNG NÖTIG: nein für dich. Die E3-Punkte (Frage 1, 3, 4, 13, 15, 19) gehen mit den Fotos in Meldung 39 an Nico.

## 0. Gelesen / nicht gelesen
**Gelesen:** Meldung 41 mit Anhang A und die Gegenprüfung (die Funde sind laut Fassung 2 eingearbeitet).
**Nicht gelesen** (liegen nur im gemeinsamen Ordner): Logs, `n14/`, `n16/`, `s6b/m38/`, `ci_rest_3b/`, `gp_s1c2_b4b.md`, `audit_testzahl/`, `b9_diagnose/`, `n9/`, `n15/`, `n11/`, `fg96/`, Läufe. Alles daraus ist für mich **berichtet**; die Gegenprüfung hat Zahlen, SHAs und Läufe selbst nachgeprüft und so ausgewiesen.
Die Hinweiszeile zur Weisung bekommst du von Nico; sie nennt Dateiname und Commit (Abschnitt 9 der Weisung 38/40).

## 1. Frage 1 (Vorrang): Uhr-Regel „Weg b“ und „Alles ersetzen“
**Entscheidung (E2, vorläufig): (a)**, aber **N14 wird nicht gemergt, bevor Nico es in Meldung 39 zur Kenntnis genommen und nicht widersprochen hat.** Begründung (meine Einschätzung):
* Gegen die veröffentlichte Version 0.63.1 geht nichts zusätzlich verloren (berichtet). Der Mehrverlust gilt nur gegen den noch nicht veröffentlichten Stand S6b.
* Der neue Fall braucht mehrere Bedingungen zugleich (Uhr geht dauerhaft nach, Programm ohne Startkennung neu gestartet, zwei Geräte löschen, danach „Alles ersetzen“). Betroffen sind eingespielte Daten, die weiter in der Sicherungsdatei liegen (vermutet).
* Der Fall, den Weg b schließt (P4), betrifft dagegen echte Lerndaten eines anderen Geräts nach dem häufigeren Fall „Uhr gestellt“.
* Es ist eine Gewichtung zwischen zwei seltenen Verlustfällen. Da es um Datenverlust geht (Nicos Zuständigkeit), **entscheidet am Ende Nico**; ich lege ihm (a) als meine Empfehlung vor, (b) als Alternative.

**Auflagen:**
1. **f2g unter U3/U6 und die 26 Zufallsabläufe** laufen zu Ende, **bevor** irgendetwas committet wird. Fällt einer davon ab, oder zeigt sich ein weiterer Mehrverlust gegen S6b oder 0.63.1: sofort melden, die Gewichtung ändert sich dann.
2. **Prüfe und berichte:** Bringt ein **zweites „Alles ersetzen“** (mit derselben Sicherungsdatei) die verlorenen Einträge zurück? Das ist heute „nicht geprüft“ und für Nico entscheidend.
3. Der Fall wird als Test „**bekannte Grenze, kein Versprechen**“ festgehalten (heutiges Ergebnis), mit Kontrollfehler. AK1 wird ausdrücklich so geschrieben: „gegenüber 0.63.1 nie mehr Verlust; gegenüber S6b eine benannte Ausnahme (U6-Fall)“.
4. Warntext: **keine Änderung** (Option (d) abgelehnt). Satz 6 bleibt wörtlich richtig, „kamen“ richtet sich nach den Geräteuhren (B.5).
5. Für Nico in Meldung 39 in einfacher Sprache: Ablauf in drei Sätzen, was passiert, was nicht verloren geht (Sicherungsdatei), Empfehlung (a), Alternative (b) mit ihren Folgen, und dass N14 bis zu seiner Antwort liegen bleibt.
6. (e) „N14 nicht in 0.63.2“ ist nicht empfohlen und nur Nico möglich.

## 2. Frage 2 (Uhr-Hinweis): (a) so lassen
Der Hinweis ist in U5/U8/U11 wahr; das Weglassen aus meiner Weisung 38/40 ist damit **zurückgenommen**. U1/U2/U7 (Hinweis falsch, schon vor N14 so) kommen als bekannte Grenze in Bericht und Testliste. Kein neuer Text. Das Muster der Auflage hat gewirkt: richtig, dass du es zurückgegeben hast.

## 3. Frage 3 (Fix 3b): (a) angenommen
Merge jetzt (nach Merge-Tor, auf der Liste der bekannten roten Tests). Das ist eine **bewusste Ausnahme** von F11 (c) und von meiner N5-Auflage („Aussehen erst nach Nicos Foto“). Begründung: Mit Inter ändert sich nichts (36 Fälle, Geometrie gleich), mit anderen Schriften ersetzt der Fix einen seitlichen Überlauf. Bedingungen:
* Die Runner-Schrift-Fotos (je 12, vorher/nachher) gehen in Meldung 39 an Nico. Lehnt er ab, kommt die Rücknahme als **eigener Commit**.
* In der Strang-Karte steht „Optik offen: Fix 3b“, bis Nico abgenommen hat. **Kein Bericht, keine Probe-Testversion und kein Release**, solange das offen ist.
* Segoe UI bleibt „nicht geprüft“ (Testliste für Nico mit Foto).
* Nach dem Merge der Lauf auf dem Integrationsstand; ein ganzer grüner Lauf gibt FG-96 frei (wie von dir geplant).

## 4. Frage 4 (S1c2: fünf weitere Schriftfälle, B-4b bei „Normal“ 1120): (a)
Reparieren wie Fix 3b (Umbruch nur, wo mit der Nutzerschrift der Platz fehlt, die Deckel bleiben auf den Inter-Werten), **zusammen** mit dem offenen B-4b-Rest (M-2: Notizblock, Fortschritt, Optionen bei „Normal“ 1120) in **einem** Auftrag auf S1c2. Fotos vorher/nachher (Inter und DejaVu) an Nico; Merge S1c2 danach. M-1 (Symbolknopf teils außerhalb bei Notizblock „Normal“ 1360 mit DejaVu) gehört dazu. Keine Lockerung der Deckel (Option (b) abgelehnt), keine Erweiterung der Ausnahmeliste (Option (c) abgelehnt). B-4b bleibt bis dahin **nicht erledigt**.

## 5. Frage 5 (Zählprüfung): (a), **FG-98**
Angenommen. Auflagen: Kontrollfehler K1–K8 im Bericht; **ein ganzer grüner GitHub-Lauf mit allen Teilen inklusive Windows**, Einbau **nach** FG-96. Gibt es auf Windows ein Problem (Git-Bash, Zeilenenden), melde es und liefere den Antrag für „Linux-Teile zuerst“; nicht still auf Linux beschränken. Die Rückgabe bleibt 97; der Kommentar im Diff verweist auf FG-98. Sonst nichts in der Datei.

## 6. Frage 6 (Fensterziehen): (a) wie entschieden
Testumbau unter **FG-60**, bau ihn jetzt (er ist gedeckt). Für den Schleifen-Nachweis: **bevorzuge einen Probezweig** mit eigenem Lauf-Workflow, der nie gemergt wird (wie die Mess- und Probe-Workflows); damit ist keine Änderung an `build.yml` oder `ci_tests.sh` nötig. Geht das nicht, kommt ein Antrag mit Diff als **FG-99**, Bau erst nach meiner Freigabe. B-M-02 Teil (b) bleibt **offen**, bis Umbau und Nachweis gelaufen sind. Die drei Zeitgrenzen bleiben unverändert (Diagnose: kein Flackern), keine Frage an Nico.

## 7. Frage 7 (F31-Satz): (a) angenommen
FG-70 wird um genau diese eine Testzeile erweitert (Satz wörtlich vorhanden, „GitHub“ genau einmal, „nach dem Abgleich“ und „anderen Geräten“ nicht vorhanden). Für den zweiten Test die Liste der 17 verbotenen Zusage-Wörter im Bericht. Kontrollfehler wie vorgelegt.

## 8. Frage 8 (B-G-17, Bestenliste): (a), **FG-100**
Marke wieder „jetzt“; beim Schreiben eines Bestenliste-Eintrags, dessen Zeit nicht nach der Marke liegt, Stempel auf Marke + 1 s. **FG-100** deckt genau die Schreibfunktion der Bestenliste (etwa 6 Zeilen); wird mehr nötig, stoppen und melden. Auflagen: Zeitzonen genau wie beim Lesen der Marke (Test mit mindestens zwei Zonen und Zeitumstellung), die B-G-17-Tests werden **bewusst neu** geschrieben (neue 0.63.2-Tests, die alten Bestandstests der Spielsammlung bleiben unverändert und grün), Mischbetrieb mit einem 0.63.1-Gerät als Test, **eigene kleine Gegenprüfung**. (b) „B-G-17 zurücknehmen“ wäre ein Verschieben (Nico) und ist nicht gewählt; (c) abgelehnt.

## 9. Frage 9 (Vergleichstests S6b gegen S6c): (a) angenommen
Eng begrenzt wie vorgeschlagen: nur für ein Projekt, das ein 0.63.2-Gerät gelöscht hat, werden dessen Felder als leer erwartet; **eingebaut erst im Integrationsstand beim Zusammentreffen**, nicht auf S6b allein. Dein Kontrollfehler (dasselbe Umrechnen für ein nicht gelöschtes Projekt muss rot werden) ist Pflicht. Ändern sich dadurch mehr als diese vier Tests, melden.

## 10. Frage 10 (Hilfetext, Suchwörter): Wortlaut von mir
Hilfe: „Die Schrift vergrößerst du in den „Optionen“ unter „Optische Anpassungen“ bei „Schriftgröße“ mit „Groß“, „Sehr groß“, „Extra groß“ oder „Maximal“.“ Suchwörter zusätzlich „Extra groß“ und „Maximal“. PC und Handy gleich. Prüfe auch die übrigen Stellen, die die Stufen aufzählen (`LIESMICH`, `AENDERUNGEN`, Testlisten, Tooltips), und nenne sie im Bericht.

## 11. Frage 11 (Schriftstufen-Reihe bei 1120): (a)
„Passt“ = per seitlichem Verschieben erreichbar (der Hinweistext sagt es schon). Foto an Nico (Meldung 39). Bleibt er unzufrieden, kommt (b).

## 12. Frage 12 (zwei Schriftgrößen-Bestandstests): (a), **FG-101**
FG-101 gilt für genau diese zwei Tests: die ersten drei Faktoren unverändert prüfen, 1,6 und 2,0 zusätzlich; als unbekannte Kennung „gibt_es_nicht“. **Kontrollfehler vor dem Bau schreiben** (jeder Test muss mit einem Fehler rot werden, die alte Fassung eines Faktors fällt auf).

## 13. Frage 13 (Tippflächen 48 dp, B-J-04): (a)
Der N9-Bauer legt den **Antrag für den Bestandstest der Auswahlknöpfe mit Diff** vor (erweitert FG-101, sobald ich ihn freigebe), dazu Fotos beider Varianten (sichtbar und unsichtbar). **Nico wählt (E3).** Die Spielansichten bei 200 % brauchen weiter eine Liste mit Diff, bevor etwas gebaut wird. B-J-04 wird nicht verschoben.

## 14. Frage 14 (Dialog auf Windows und macOS): (a) mit (i) und (ii), **FG-102**
Dialogtest in die Windows-Liste der Testlauf-Datei und ein Schritt im macOS-Bau-Job. **Erst der Antrag mit Diff** (FG-102), Bau nach meiner Freigabe. Wichtig: Ein neuer Schritt im macOS-Bau-Job darf den Bau nicht fragil machen; schlägt er rot an, hält er den Release auf, das gehört in den Antrag. (iii) „Breitentests auch im Windows-Job“ als eigener späterer Schritt, wie von dir empfohlen.

## 15. Frage 15 (Startzeit G1): **E3, an Nico**
Die Lesart G1 (milde Lesart: Median höchstens der höchste Einzelwert von 0.62.5) hatte ich selbst in 0.63.1 festgelegt (Weisung 10, Antwort 16). Sie bleibt mein Maßstab, die verbindliche A13-Grenze (höchstens 100 ms über 0.62.5 im selben Lauf) ist **eingehalten**. G1 ist um 39,1 ms gerissen. Meine Empfehlung an Nico: (a), mit ehrlichen Zahlen im Änderungstext, denn 0.63 und 0.63.1 sind mit größerem Abstand angenommen worden (0.63.1 +238 ms), und 0.63.2 ist in diesem Punkt besser. Er entscheidet. Die **Endmessung G1–G4 auf dem Endstand** bleibt Pflicht; ändert sie das Bild, melden. Darstellung in Meldung 39: Zahlen in einer kleinen Tabelle, ein Satz Empfehlung.

## 16. Frage 16 und 17 (Hinweisnummer an den Seitenwechsel): (a) beide
**FG-63 wird erweitert** um „Nummer an den Seitenwechsel geben“ für SP1–SP5 (SP1 über einen freiwilligen Parameter der Öffnen-Funktion) und SP6 über Frage 17. Frage 17 (a): Die Öffnen-Funktion liest die Nummer am Anfang und nimmt eine mitgegebene an; HA5–HA9 geben ihre Nummer mit. Der Zeithinweis B-G-23 bleibt unverändert und sein Test grün. Tests je Stelle (SP1–SP6, HA3–HA9) als Liste im Bericht, Kontrollfehler, keine anderen Zeilen in der geschützten Datei. Ob das Schließen des „Prüfung läuft“-Hinweises am Gerät wirklich so passiert, ist bisher nur berichtet; es kommt als Prüfpunkt auf Nicos Testliste.

## 17. Frage 18 (Kriterientext „c 1 schickt …“): (a), **erst Antrag**
Stelle mit Diff als FG-Antrag (Inhalt oder Zerlegung), mit Fingerabdruck-Begründung („lerninhalte“ weicht schon seit S4 ab). **Nicht bauen**, bevor ich freigegeben habe. Beschreibe, ob andere Aufgaben dasselbe Muster haben („1. -“).

## 18. Frage 19 (Universal-Mac): (a) vorläufig, **E3 an Nico**
Getrennte Mac-Bauten bleiben, beide Dateinamen bleiben, der Schutztest bleibt. Dass ein Teil von B-M-06 nicht in 0.63.2 kommt, ist ein **Verschieben und entscheidet Nico**. Vorher bitte kurz **untersuchen (nicht in den Release bauen)**, ob sich ein Universal-Rad der Bildbibliothek aus den beiden offiziellen Rädern erzeugen lässt (zum Beispiel mit dem Werkzeug `delocate-fuse`, Prüfsummen der beiden Quellräder bleiben die Grundlage); Ergebnis (geht / geht nicht / Risiko) als Absatz in Meldung 39 für Nico. Keine neue Bauquelle ohne meine Freigabe.

## 19. Fragen 20 bis 23
* **Frage 20 (libobjc4):** (a). Der Starttest ist grün; ergänze im Bericht, dass die Datei fehlt und wie du den Dunkelmodus-Zweig unter Linux geprüft hast.
* **Frage 21 (Inno Setup, Nachinstallation):** (a), „nicht geprüft“ in Bericht und Testliste; ein Fehlschlag muss den Lauf rot machen (bitte mit einem Test oder einer Zeile im Workflow belegen, dass es kein stiller Fehlbau ist).
* **Frage 22 (FG-Nummern): bestätigt, mit Ergänzung:**

| Nummer | Gegenstand | Stand |
|---|---|---|
| FG-97 | APK-Prüfung für das Trennmodul (N8) | freigegeben im Prinzip; Antrag mit Diff kommt mit der N8-Meldung, ich bestätige dort |
| FG-98 | Zählprüfung im Testlauf (Frage 5) | erteilt |
| FG-99 | Fensterziehen, Schleifen-Nachweis (Frage 6) | nur falls der Probezweig-Weg nicht geht, dann Antrag mit Diff |
| FG-100 | Bestenliste, Schreibfunktion (Frage 8) | erteilt, Umfang: nur diese Funktion |
| FG-101 | zwei Schriftgrößen-Bestandstests (Frage 12) | erteilt; Erweiterung um den Auswahlknöpfe-Test erst nach Antrag (Frage 13) |
| FG-102 | Dialogtest Windows/macOS (Frage 14) | erst Antrag mit Diff |
| FG-103 | Kriterientext (Frage 18) | reserviert, erst Antrag mit Diff |

Erweitert ohne neue Nummer: FG-60 (Fensterziehen-Umbau), FG-63 (Hinweisnummer), FG-70 (eine Testzeile). **Nächste freie FG: FG-104.**
* **Frage 23 (Kontrollfehler im Dialog-Testplan):** (a), Ersatz bestätigt (strenger).

## 20. E1-Liste und „Zur Kenntnis“
* **E1-1 bis E1-5:** bestätigt.
* **Zur Kenntnis 9 (Regelverstoß `pkill -f`):** Notiert. Künftig **kein `pkill -f`**, sondern nur die eigene Prozesskennung beenden. Prüfe die „auffälligen Abbrüche um etwa 01:50 UTC“ tatsächlich und melde das Ergebnis in der nächsten Meldung (Ja/Nein, welche Läufe).
* **Zur Kenntnis 5 (`test_vorladen` lastabhängig):** Beobachten. Tritt er auf GitHub rot auf, gilt der Katalog (kein Einzelneustart, ganzer neuer Lauf); wird er häufiger rot, kommt er als eigenes Thema („flaky“) zu mir.
* **Zur Kenntnis 7 (weitere Breitenbefunde bei 200 % und 1120 mit DejaVu):** Vorschläge folgen mit den jeweiligen Strängen; nichts davon wird still gebaut.
* **N10:** bereit bis auf das Merge-Tor; `release.yml` bleibt „nicht geprüft“. **N11:** Merge erst nach Nicos Antwort zu Frage 19 und mit dem bekannten Matrix-Konflikt zu FG-96 (gleich streng auflösen).

## 21. Für Meldung 39 (Nico)
Neben den Fotos und den Punkten aus der Weisung 38/40 zusätzlich: Frage 1 (Uhr-Regel, E3), Fix 3b und S1c2 mit Runner-Schrift (Fotos, Abnahme nach Merge), Frage 13 (Tippflächen sichtbar/unsichtbar), Frage 15 (G1), Frage 19 (Universal-Mac), Frage 11 (Schriftstufen-Reihe bei 1120), N16-F2, K44, N9-F2, Dialog-Aussehen. Alle in einfacher Sprache, jeweils mit Folge und Empfehlung.

## 22. Nummern
Nächste Meldung von dir: **42** (39 bleibt für Nicos Fotos reserviert). Eine Hinweiszeile je Meldung. Alles andere unverändert (Weisungen 35 bis 38/40, Ablauf Großaufträge, Meldungszweig).
