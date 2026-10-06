# Screenreader-Prototyp (nur Zweig proto-screenreader)

Plan 0.59, Abschnitt 8a, Lesart A. Kein Teil des Programms, kein Release.

| Datei | Inhalt |
|---|---|
| `Bericht_Screenreader-Prototyp.md` | Ergebnis S1 bis S3, Messungen, Aufwand, Empfehlung |
| `NVDA-Testanleitung.md` | Anleitung für die Person, die mit NVDA testet |
| `optionen_flet.py` | der Prototyp (Flet-Desktop) |
| `bauordner.py`, `pyproject.toml` | Windows-Bau über `.github/workflows/prototyp-screenreader.yml` |
| `messung/` | Mess-Skripte (Linux, AT-SPI), Ergebnisse und Bilder |

Start im Repo: `python prototyp_screenreader/optionen_flet.py` (Flet 1.0.1).
Windows-ZIP: GitHub → Actions → „Screenreader-Prototyp bauen“ → letzter Lauf → Artifacts.
