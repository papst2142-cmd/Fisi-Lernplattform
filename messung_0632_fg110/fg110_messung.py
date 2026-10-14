# Messung FG-107+FG-110 (nur Messung, nie mergen): Dashboard nach einer Aenderung (grosser Lernstand), Zeit gesamt und "faellig"
#   python fg110_messung.py CODE GROSS.db AUSGABE.jsonl SEITE RUNDE [worst]
# worst (W44 Nachtrag): nach dem Start schreibt "ein aelteres Programm" eine Quizantwort
# mit ALTEM Fragetext (QUESTION_RENAMES) direkt in den Lernstand; danach haelt der Index
# einen alten Text, always_full ist gesetzt und jeder Aufruf baut voll auf.
# Je Aufruf ein eigener Prozess auf einer frischen DB-Kopie. Wanduhr in ms,
# refresh() + update_idletasks wie N7 (messung_n7.py / profil_dash_quiz.py).
import json, os, shutil, sys, tempfile, time
code, src, out, seite, runde = sys.argv[1:6]
worst = len(sys.argv) > 6 and sys.argv[6] == "worst"
tmp = tempfile.mkdtemp(prefix="fg107d"); db = os.path.join(tmp, "g.db"); shutil.copyfile(src, db)
os.environ.update(HOME=tmp, FISI_DB_PATH=db, FISI_SELFTEST=os.path.join(tmp, "s"), FISI_VORLADEN="0")
sys.path.insert(0, code); os.chdir(code)
import app_gui, fisi_core as fc
app_gui.UpdateController.auto_check = lambda self: None
app_gui.SyncController.auto_start = lambda self: None
app_gui.show_badge_toast = lambda *a, **k: None
root = app_gui.ctk.CTk(); root.geometry("1360x900+0+0")
app = app_gui.FISIApp(root); app.show_view("dashboard")
for _ in range(3): root.update()
view = app.views["dashboard"]
if worst:   # alter Text wie von einem aelteren Programm (ohne _migrate dieses Programms)
    import sqlite3
    alt, neu_text = next(iter(fc.QUESTION_RENAMES["quiz_answers"].items()))
    q = next(x for x in fc.QUIZ_QUESTIONS if x["q"] == neu_text)
    app.db.log_quiz_answer(q["cat"], q["q"], True)     # Zeile im Format des Programms ...
    c = sqlite3.connect(db)                             # ... mit altem Text (aelteres Programm)
    c.execute("UPDATE quiz_answers SET question = ? WHERE id = (SELECT MAX(id) FROM quiz_answers)", (alt,))
    c.commit(); c.close()
times = {}
orig = view._dash_query
def timed(name, func, *args, stamps=None):
    t0 = time.perf_counter(); r = orig(name, func, *args, stamps=stamps)
    times[name] = times.get(name, 0) + (time.perf_counter() - t0) * 1000; return r
view._dash_query = timed
rows = []
def _last():
    try:
        return open("/proc/loadavg").read().split()[0]
    except OSError:
        return "0"      # Windows: keine Lastangabe
def mess(art, aktion):
    aktion()
    times.clear(); t0 = time.perf_counter(); view.refresh(); root.update_idletasks()
    total = (time.perf_counter() - t0) * 1000
    idx = getattr(view, "_review_index", None)
    rows.append(dict(seite=seite, runde=int(runde), art=("worst_" if worst else "") + art,
                     always_full=getattr(idx, "always_full", None), full_builds=getattr(idx, "full_builds", None),
                     steps=getattr(idx, "steps", None), gesamt=round(total, 1),
                     faellig=round(times.get("faellig", 0), 1),
                     abfragen=round(sum(times.values()), 1),
                     due=view.lbl_due.cget("text"),
                     last=_last()))
    for _ in range(2): root.update()
mess("erstes_refresh", lambda: None)          # Index/Zwischenspeicher fuellen
for i in range(3):
    q = fc.QUIZ_QUESTIONS[5 + i]
    mess("nach_quiz", lambda q=q: app.db.log_quiz_answer(q["cat"], q["q"], i % 2 == 0))
for i in range(3):
    c = fc.KARTEIKARTEN[7 + i]
    mess("nach_karte", lambda c=c: app.db.log_card(c["cat"], c["q"], "lernen", i % 2 == 0))
mess("ohne_aenderung", lambda: None)
with open(out, "a", encoding="utf-8") as f:
    for r in rows: f.write(json.dumps(r, ensure_ascii=False) + "\n")
shutil.rmtree(tmp, ignore_errors=True); os._exit(0)
