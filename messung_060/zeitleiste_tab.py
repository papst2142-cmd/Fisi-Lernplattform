"""Zusammenfassung der zeitleiste_0601-Ergebnisse je Fassung (Median, Spanne)."""
import glob, json, statistics as st, sys
files = sys.argv[1:] or glob.glob("z_*.json")
by = {}
for f in files:
    try:
        d = json.load(open(f, encoding="utf-8"))
    except Exception:
        continue
    by.setdefault(d.get("fassung", d["version"]), []).append(d)


def m(vals, fmt="%d"):
    vals = [v for v in vals if v is not None]
    if not vals:
        return "-"
    return (fmt + " (" + fmt + "-" + fmt + ")") % (st.median(vals), min(vals), max(vals))


for v, runs in sorted(by.items()):
    ready = lambda k: [r["bereit_s"].get(k) for r in runs]
    blocks = [max(r["block_ms"].values()) for r in runs if r["block_ms"]]
    parts = [max(r["teil_ms"].values()) for r in runs if r["teil_ms"]]
    print("%s n=%d fertig %s s | nach Wechsel %s s | Karteik %s Spiel %s Opt %s Fortschr %s | Block %s Teil %s | Hilfe %s Farben %s | Wechsel %s | RSS %s"
          % (v, len(runs), m([r["fertig_s"] for r in runs], "%.1f"),
             m([r["fertig_nach_wechsel_s"] for r in runs], "%.1f"),
             m(ready("cards"), "%.1f"), m(ready("game"), "%.1f"), m(ready("settings"), "%.1f"),
             m(ready("progress"), "%.1f"), m(blocks), m(parts),
             m([r["hilfe_ms"] for r in runs]), m([r["farben_ms"] for r in runs]),
             m([r["wechsel_ms"] for r in runs]), m([r["rss_mb"] for r in runs], "%.0f")))
