import json, sys, statistics
rows = [json.loads(l) for f in sys.argv[1:] for l in open(f, encoding="utf-8")]
def med(v): v = sorted(v); return v[len(v)//2] if len(v) % 2 else (v[len(v)//2-1] + v[len(v)//2]) / 2
print("| Art | Seite | n | gesamt ms Median (min-max) | davon \"faellig\" ms Median (min-max) |")
print("|---|---|---|---|---|")
for art in ("nach_quiz", "nach_karte", "ohne_aenderung"):
    for seite in ("base", "neu"):
        r = [x for x in rows if x["art"] == art and x["seite"] == seite]
        g = [x["gesamt"] for x in r]; f = [x["faellig"] for x in r]
        print("| %s | %s | %d | %.0f (%.0f-%.0f) | %.0f (%.0f-%.0f) |" % (
            art, "vorher 1e7965a" if seite == "base" else "mit Diff", len(r), med(g), min(g), max(g), med(f), min(f), max(f)))
# gleiche Anzeige "Heute faellig" je Runde und Schritt
by = {}
for x in rows:
    by.setdefault((x["runde"], x["art"], rows.index(x) - min(i for i, y in enumerate(rows) if y["runde"] == x["runde"] and y["seite"] == x["seite"])), {})[x["seite"]] = x["due"]
gleich = sum(1 for v in by.values() if len(v) == 2 and v["base"] == v["neu"])
print("\nAnzeige \"Heute faellig\" je Runde/Schritt gleich: %d von %d" % (gleich, sum(1 for v in by.values() if len(v) == 2)))
print("Last (1 min) Spanne: %s - %s" % (min(float(x["last"]) for x in rows), max(float(x["last"]) for x in rows)))
