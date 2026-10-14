# Messung FG-107+FG-110 (nur Messung, nie mergen): grosser Lernstand wie gross.db der
# N7-Messung (20.000 Karteikarten-Ereignisse, 50.000 Quizantworten), fest gesaet.
#   python fg110_db.py STAND AUSGABE.db
import datetime, os, random, sqlite3, sys, tempfile, uuid
stand, out = sys.argv[1:3]
os.environ["HOME"] = tempfile.mkdtemp(prefix="fg107db")
os.environ["FISI_DB_PATH"] = out
sys.path.insert(0, stand)
import fisi_core as fc
fc.DBManager(out)                       # Tabellen wie im Programm
rng = random.Random(107)
start = datetime.datetime(2025, 9, 6, 20, 0, 0)
span = int((datetime.datetime(2026, 10, 11, 20, 0, 0) - start).total_seconds())
cards = fc.KARTEIKARTEN[:1565]
quiz = fc.QUIZ_QUESTIONS[:2174]
def ts():
    return (start + datetime.timedelta(seconds=rng.randrange(span))).strftime("%Y-%m-%d %H:%M:%S")
conn = sqlite3.connect(out)
conn.executemany("INSERT INTO card_events (timestamp, category, question, mode, correct, uid)"
                 " VALUES (?, ?, ?, 'lernen', ?, ?)",
                 [(ts(), c["cat"], c["q"], rng.choice([1, 1, 0, None]), uuid.uuid4().hex)
                  for c in (rng.choice(cards) for _ in range(20000))])
conn.executemany("INSERT INTO quiz_answers (timestamp, category, question, correct, uid)"
                 " VALUES (?, ?, ?, ?, ?)",
                 [(ts(), q["cat"], q["q"], rng.choice([1, 1, 0]), uuid.uuid4().hex)
                  for q in (rng.choice(quiz) for _ in range(50000))])
conn.commit()
print("DB", out, [conn.execute("SELECT COUNT(*) FROM %s" % t).fetchone()[0]
                  for t in ("card_events", "quiz_answers")])
conn.close()
