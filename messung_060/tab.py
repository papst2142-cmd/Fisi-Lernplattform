import json,sys,statistics as st
for f in sys.argv[1:]:
    try: d=json.load(open(f))
    except Exception as e: print(f,"FEHLT",e); continue
    w=d["wechsel"]
    g=[x["gesamt_ms"] for x in w]
    def med(k): return round(st.median([x[k] for x in w]))
    upd=round(st.median([sum(x["update_ms"])+sum(x["update_idle_ms"]) for x in w]))
    print(f"{f:22} v{d['version']} start {d['start_ms']} | gesamt med {round(st.median(g))} ({min(g)}-{max(g)}) | umf {med('umfaerben_ms')} opt {med('optionen_bauen_ms')} abbau {med('abbau_alt_ms')} rahmen {med('rahmen_ms')} upd {upd} abd {med('abdeckung_ms')} schlaf {med('schlaf_ms')} | rss {[x['rss_danach'] for x in w]} | elem {w[0]['elemente_vorher']} opt_el {d['opt_elemente']} | schliessen {d.get('schliessen_on_close_ms')}")
