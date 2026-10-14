# -*- coding: utf-8 -*-
"""Tests 0.63.2, FG-107 (Weisung zu Meldung 43, 2.7): "faellig" schrittweise.

fisi_lernen.ReviewIndex haelt die Antworten zu Karteikarten und
Pruefungstrainer und rechnet nach neuen Zeilen nur die betroffenen Fragen neu.
Das Ergebnis muss in jedem Fall dasselbe sein wie die Berechnung bis 0.63.2
(Referenz: woertliche Kopie von ReviewPlan aus 1e7965a, unten REF_SRC) und
wie ein voller Neuaufbau.

  * T1 Zufallsstaende (feste Saaten), Index und from_db gegen die Referenz
  * T2 Zaehlprobe: nur neue Antworten -> schrittweise
  * T3 Randfaelle der Regeln (Altbestand, Kontingent, None, Mitternacht)
  * Zusatzfaelle (i)-(iv) der Weisung 43, 2.7
  * T5 Lernstand unveraendert, T6 Rueckfall, T9 Waechter "kein UPDATE"
  * KF15: Schreiben zwischen Stempel und Zeilen
  * T7 Dashboard (Fenster): Zaehlprobe und Wechsel der Datenbank

Kein skip: Fehlt die Anzeige, endet die Fensterklasse mit ERROR.
Aufruf:  xvfb-run -a python test_faellig_0632.py
"""
import datetime
import hashlib
import os
import random
import re
import shutil
import sqlite3
import sys
import tempfile
import unittest
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.chdir(HERE)
_TMP = tempfile.mkdtemp(prefix="fisi_fg107_")
os.environ["FISI_DB_PATH"] = os.path.join(_TMP, "fg107.db")
os.environ.setdefault("FISI_SELFTEST", os.path.join(_TMP, "selbsttest.log"))
os.environ["HOME"] = _TMP
os.environ["APPDATA"] = _TMP
os.environ["FISI_VORLADEN"] = "0"

import fisi_core as fc  # noqa: E402
import fisi_lernen as fl  # noqa: E402

# ReviewPlan aus 1e7965a (fisi_lernen.py Zeilen 91-167, ganze Klasse), woertlich. Der Hash
# sichert, dass die Referenz nicht nachgezogen wird.
REF_SRC = r'''class ReviewPlan:
    """Faellige Wiederholungen fuer einen Tag, einmal aus dem StatusBook
    berechnet. due[quelle] = Liste der faelligen Schluessel (zuerst die am
    laengsten ueberfaelligen)."""

    def __init__(self, book, today=None, valid=None):
        self.today = today or datetime.date.today()
        start = datetime.date.fromisoformat(SR_START)
        if valid is None:
            valid = {SRC_CARD: {card["q"] for card in KARTEIKARTEN},
                     SRC_QUIZ: {question["q"] for question in QUIZ_QUESTIONS}}
        self.state = {}
        regular, legacy = [], []
        migrated_today = 0
        for (source, key), entries in book.results.items():
            if source not in SR_SOURCES or key not in valid[source]:
                continue
            graded = [(t, v) for t, v in entries if v is not None]
            if not graded:
                continue
            stage, due = review_state(graded)
            self.state[(source, key)] = (stage, due)
            old = [t for t, _v in graded if _date(t) < start]
            new = [t for t, _v in graded if _date(t) >= start]
            if old and not new:
                legacy.append((source, key))
                continue
            if old and new and _date(new[0]) == self.today:
                migrated_today += 1
            if due <= self.today:
                regular.append((due, source, key))
        regular.sort(key=lambda item: (item[0], _stable_rank(item[1], item[2])))
        # Altbestand: zu Uebende (rot vor gelb) zuerst, sonst feste Reihenfolge
        if self.today >= start:
            def legacy_rank(item):
                status, level = book.status(*item)
                order = 0 if (status, level) == (Q_PRACTICE, LEVEL_RED) else \
                    1 if status == Q_PRACTICE else 3 if status == Q_DONE else 2
                return order, _stable_rank(*item)
            legacy.sort(key=legacy_rank)
            quota = max(0, SR_LEGACY_PER_DAY - migrated_today)
            released = legacy[:quota]
        else:
            released = []
        self.legacy_waiting = len(legacy) - len(released)
        self.due = {source: [] for source in SR_SOURCES}
        for _due, source, key in regular:
            self.due[source].append(key)
        for source, key in released:
            self.due[source].append(key)

    @classmethod
    def from_db(cls, db, today=None):
        return cls(StatusBook(db), today=today)

    def count(self, source=None):
        if source is not None:
            return len(self.due[source])
        return sum(len(keys) for keys in self.due.values())

    def is_due(self, source, key):
        return key in self.due.get(source, ())

    def stage(self, source, key):
        return self.state.get((source, key), (0, None))[0]

    def session(self, source, limit=SR_SESSION_MAX):
        """Schluessel fuer eine Wiederholungs-Sitzung (hoechstens limit)."""
        return list(self.due[source][:limit])

    def first_source(self):
        """Womit "Jetzt wiederholen" beginnt: zuerst Karteikarten, dann
        Pruefungstrainer. None, wenn nichts faellig ist."""
        for source in SR_SOURCES:
            if self.due[source]:
                return source
        return None
'''
REF_SHA256 = "2c9ecbafac6aa12ba87eea000eeb378462aa016cb2c799ec55ce7463252b93b5"
_ns = dict(vars(fl))
exec(compile(REF_SRC, "ReviewPlan_1e7965a", "exec"), _ns)  # noqa: S102
RefPlan = _ns["ReviewPlan"]

CARDS = [card["q"] for card in fc.KARTEIKARTEN]
QUIZ = [question["q"] for question in fc.QUIZ_QUESTIONS]
POOL = 120
TAGE = [datetime.date(2026, 9, 20) + datetime.timedelta(days=d) for d in range(40)]
HEUTE = [datetime.date(2026, 9, 30), datetime.date(2026, 10, 1), datetime.date(2026, 10, 14),
         datetime.date(2026, 10, 15), datetime.date(2026, 11, 20), None]


def snap(plan):
    return (plan.today, {k: list(v) for k, v in plan.due.items()}, plan.legacy_waiting,
            dict(plan.state), plan.count(), plan.first_source())


def outcome(func):
    try:
        return ("ok", snap(func()))
    except Exception as error:  # noqa: BLE001 - gleiche Ausnahme erwartet
        return ("err", type(error).__name__)


def stamp_text(rng):
    day = rng.choice(TAGE)
    if rng.random() < 0.15:
        return "%s 12:00:00" % day
    return "%s %02d:%02d:%02d" % (day, rng.randrange(24), rng.randrange(60), rng.randrange(60))


def insert(conn, table, timestamp, key, correct, row_id=None):
    if table == "card_events":
        conn.execute("INSERT INTO card_events (%stimestamp, category, question, mode, correct, uid)"
                     " VALUES (%s?, 'x', ?, 'lernen', ?, ?)"
                     % (("id, ", "?, ") if row_id is not None else ("", "")),
                     ((row_id,) if row_id is not None else ()) +
                     (timestamp, key, correct, uuid.uuid4().hex))
    else:
        conn.execute("INSERT INTO quiz_answers (%stimestamp, category, question, correct, uid)"
                     " VALUES (%s?, 'x', ?, ?, ?)"
                     % (("id, ", "?, ") if row_id is not None else ("", "")),
                     ((row_id,) if row_id is not None else ()) +
                     (timestamp, key, correct, uuid.uuid4().hex))


def insert_random(conn, rng, table, n):
    for _ in range(n):
        keys = CARDS if table == "card_events" else QUIZ
        key = rng.choice(keys[:POOL]) if rng.random() < 0.9 else rng.choice(keys)
        if rng.random() < 0.03:
            key = "unbekannte Frage %d" % rng.randrange(5)
        correct = rng.choice([1, 0, None, 1]) if table == "card_events" else rng.choice([1, 0, 1])
        insert(conn, table, stamp_text(rng), key, correct)


ARTEN = ["gleiche_sekunde", "gleiche_sekunde", "neu_jetzt", "neu_alt", "viele", "loeschen",
         "loeschen_und_neu", "alles_neu", "leeren", "abgleich_umbenennen", "nichts",
         "andere_tabelle"]


def random_step(db, rng, art):
    if art == "neu_jetzt":
        if rng.random() < 0.5:
            db.log_quiz_answer("x", rng.choice(QUIZ[:POOL]), rng.random() < 0.6)
        else:
            db.log_card("x", rng.choice(CARDS[:POOL]), "lernen", rng.choice([True, False, None]))
        return
    conn = sqlite3.connect(db.db_path)
    try:
        tables = ["card_events", "quiz_answers"]
        if art == "gleiche_sekunde":
            table = rng.choice(tables)
            row = conn.execute("SELECT timestamp, question, correct FROM %s ORDER BY random()"
                               " LIMIT 1" % table).fetchone()
            if row:
                insert(conn, table, row[0], row[1], 0 if row[2] else 1)
        elif art == "neu_alt":
            insert_random(conn, rng, rng.choice(tables), rng.randint(1, 4))
        elif art == "viele":
            insert_random(conn, rng, "card_events", rng.randint(5, 30))
            insert_random(conn, rng, "quiz_answers", rng.randint(5, 30))
        elif art in ("loeschen", "loeschen_und_neu"):
            table = rng.choice(tables)
            k = rng.randint(1, 3)
            conn.execute("DELETE FROM %s WHERE id IN (SELECT id FROM %s ORDER BY random() LIMIT ?)"
                         % (table, table), (k,))
            if art == "loeschen_und_neu":
                insert_random(conn, rng, table, k)
        elif art == "alles_neu":
            for table in tables:
                cols = "timestamp, question, correct"
                rows = conn.execute("SELECT %s FROM %s" % (cols, table)).fetchall()
                conn.execute("DELETE FROM " + table)
                for timestamp, key, correct in rows:
                    insert(conn, table, timestamp, key, correct)
        elif art == "leeren" and rng.random() < 0.3:
            for table in tables:
                conn.execute("DELETE FROM " + table)
        elif art == "abgleich_umbenennen":
            insert(conn, "quiz_answers", stamp_text(rng), "ALTER TEXT", 1)
            conn.execute("UPDATE quiz_answers SET question = ? WHERE question = 'ALTER TEXT'",
                         (rng.choice(QUIZ[:POOL]),))
        elif art == "andere_tabelle":
            conn.execute("INSERT INTO ap1_events (timestamp, scenario_index, title, theme, correct,"
                         " uid) VALUES (?, 0, 't', 't', 1, ?)", (stamp_text(rng), uuid.uuid4().hex))
        conn.commit()
    finally:
        conn.close()


class Base(unittest.TestCase):
    """Eigene Datenbank je Test."""

    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="db_", dir=_TMP)
        self.db = fc.DBManager(os.path.join(self.dir, "t.db"))

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def fill(self, rng, n_cards=200, n_quiz=200, db=None):
        conn = sqlite3.connect((db or self.db).db_path)
        insert_random(conn, rng, "card_events", n_cards)
        insert_random(conn, rng, "quiz_answers", n_quiz)
        conn.commit()
        conn.close()

    def assertSame(self, index, db=None, today=None, msg=None):
        """Index = Referenz (1e7965a) = voller Neuaufbau (neuer Index) = from_db."""
        db = db or self.db
        ref = outcome(lambda: RefPlan.from_db(db, today=today))
        self.assertEqual(outcome(lambda: index.plan(today=today)), ref, msg)
        self.assertEqual(outcome(lambda: fl.ReviewIndex(db).plan(today=today)), ref, msg)
        self.assertEqual(outcome(lambda: fl.ReviewPlan.from_db(db, today=today)), ref, msg)
        return ref


class IndexTest(Base):

    def test_referenz_unveraendert(self):
        self.assertEqual(hashlib.sha256(REF_SRC.encode("utf-8")).hexdigest(), REF_SHA256)

    def test_t1_zufallsstaende(self):
        """T1: feste Saaten, je Schritt zwei Tage; Index, voller Neuaufbau und
        from_db gegen die Referenz; Antworten des Index = question_results."""
        steps = 0
        for run in range(16):
            rng = random.Random(10007 * 107 + run)
            db = fc.DBManager(os.path.join(self.dir, "z%d.db" % run))
            self.fill(rng, rng.randint(0, 400), rng.randint(0, 400), db=db)
            index = fl.ReviewIndex(db)
            for number in range(25):
                art = rng.choice(ARTEN)
                random_step(db, rng, art)
                for today in rng.sample(HEUTE, 2):
                    self.assertSame(index, db, today, "lauf %d schritt %d %s" % (run, number, art))
                expected = {k: v for k, v in db.question_results().items()
                            if k[0] in fl.SR_SOURCES}
                self.assertEqual(index.results, expected)
            steps += index.steps
        self.assertGreater(steps, 100)

    def test_t2_zaehlprobe(self):
        self.fill(random.Random(2))
        index = fl.ReviewIndex(self.db)
        index.plan()
        for i in range(5):
            self.db.log_quiz_answer("x", QUIZ[i], i % 2 == 0)
            self.db.log_card("x", CARDS[i], "lernen", None if i == 3 else i % 2 == 1)
            self.assertSame(index)
        self.assertEqual((index.steps, index.full_builds), (5, 1))
        index.plan()                       # ohne Aenderung: weder Schritt noch Aufbau
        self.assertEqual((index.steps, index.full_builds), (5, 1))

    def test_t3_randfaelle(self):
        index = fl.ReviewIndex(self.db)
        self.assertSame(index)                                # leer
        conn = sqlite3.connect(self.db.db_path)
        for i in range(30):                                   # Altbestand > Kontingent
            insert(conn, "quiz_answers", "2026-09-%02d 10:00:00" % (1 + i % 28), QUIZ[i], i % 4 != 0)
        insert(conn, "card_events", "2026-09-05 10:00:00", CARDS[0], None)   # nur angesehen
        insert(conn, "card_events", "2026-09-05 10:00:00", "gibt es nicht", 1)
        conn.commit()
        conn.close()
        for today in HEUTE:
            self.assertSame(index, today=today)
        today = datetime.date.today()
        for i in range(3):                                    # migrated_today
            self.db.log_quiz_answer("x", QUIZ[i], True)
            self.assertSame(index, today=today)
            self.assertSame(index, today=today + datetime.timedelta(days=1))  # Mitternacht
        conn = sqlite3.connect(self.db.db_path)
        insert(conn, "quiz_answers", "2026-10-01 00:00:00", QUIZ[5], 1)      # genau SR_START
        insert(conn, "quiz_answers", "2026-09-30 23:59:59", QUIZ[6], 0)
        conn.commit()
        conn.close()
        for today in HEUTE:
            self.assertSame(index, today=today)

    # -- Zusatzfaelle Weisung 43, 2.7 -------------------------------------

    def test_i_aelterer_zeitstempel_nach_neueren(self):
        """(i) Zeile mit aelterem Zeitstempel kommt nach neueren dazu, auch zu
        derselben Frage, auch in derselben Sekunde."""
        conn = sqlite3.connect(self.db.db_path)
        for day in (10, 12, 14):
            insert(conn, "quiz_answers", "2026-10-%02d 09:00:00" % day, QUIZ[0], 1)
        conn.commit()
        index = fl.ReviewIndex(self.db)
        self.assertSame(index)
        for timestamp, value in (("2026-10-11 09:00:00", 0), ("2026-10-02 08:00:00", 0),
                                 ("2026-10-12 09:00:00", 0), ("2026-09-01 00:00:00", 1)):
            insert(conn, "quiz_answers", timestamp, QUIZ[0], value)
            conn.commit()
            for today in HEUTE:
                self.assertSame(index, today=today, msg=timestamp)
        conn.close()
        self.assertEqual(index.full_builds, 1)
        self.assertEqual([t for t, _v in index.results[(fc.SRC_QUIZ, QUIZ[0])]],
                         sorted(t for t, _v in index.results[(fc.SRC_QUIZ, QUIZ[0])]))

    def test_i_ueber_abgleich(self):
        import fisi_sync as fs
        other = fc.DBManager(os.path.join(self.dir, "b.db"))
        self.fill(random.Random(5))
        index = fl.ReviewIndex(self.db)
        self.assertSame(index)
        conn = sqlite3.connect(other.db_path)
        for i, key in enumerate(QUIZ[:20]):
            insert(conn, "quiz_answers", "2026-09-%02d 08:00:00" % (10 + i % 15), key, i % 3 != 0)
        conn.commit()
        conn.close()
        self.assertGreater(fs.merge_into_local(self.db, fs.export_local(other)), 0)
        self.assertSame(index)
        self.assertEqual(index.full_builds, 1)

    def test_ii_niedrigere_nummer(self):
        """(ii) Zeile mit niedrigerer Nummer (Luecke) -> voller Neuaufbau, gleich."""
        conn = sqlite3.connect(self.db.db_path)
        for i in range(10):
            insert(conn, "quiz_answers", "2026-10-%02d 09:00:00" % (2 + i), QUIZ[i % 3], i % 2)
        conn.execute("DELETE FROM quiz_answers WHERE id IN (3, 4)")
        conn.commit()
        index = fl.ReviewIndex(self.db)
        self.assertSame(index)
        insert(conn, "quiz_answers", "2026-10-13 09:00:00", QUIZ[0], 0, row_id=3)
        conn.commit()
        conn.close()
        self.assertSame(index)
        self.assertEqual(index.full_builds, 2)

    def test_ii_abgleich_vergibt_nur_hoehere_nummern(self):
        """(ii) Der Abgleich gibt nie eine Nummer vor: Auch wenn eine Loeschmarke
        die Zeile mit der hoechsten Nummer loescht, bekommen die uebernommenen
        Zeilen hoehere Nummern als je zuvor (AUTOINCREMENT)."""
        import fisi_sync as fs
        conn = sqlite3.connect(self.db.db_path)
        for i in range(5):
            insert(conn, "quiz_answers", "2026-10-%02d 09:00:00" % (2 + i), QUIZ[i], 1)
        insert(conn, "quiz_answers", "2026-09-01 09:00:00", QUIZ[9], 1)   # hoechste Nummer, alt
        conn.commit()
        top = conn.execute("SELECT MAX(id) FROM quiz_answers").fetchone()[0]
        conn.close()
        index = fl.ReviewIndex(self.db)
        self.assertSame(index)
        other = fc.DBManager(os.path.join(self.dir, "b.db"))
        conn = sqlite3.connect(other.db_path)
        for i in range(4):
            insert(conn, "quiz_answers", "2026-10-%02d 10:00:00" % (8 + i), QUIZ[20 + i], 0)
        conn.commit()
        conn.close()
        remote = fs.export_local(other)
        remote.setdefault("markers", {})["reset_at"] = "2026-09-15 00:00:00"
        fs.merge_into_local(self.db, remote, check_future=False)
        conn = sqlite3.connect(self.db.db_path)
        new_ids = [row[0] for row in conn.execute(
            "SELECT id FROM quiz_answers WHERE question IN (%s)" % ",".join("?" * 4), QUIZ[20:24])]
        conn.close()
        self.assertEqual(len(new_ids), 4)
        self.assertTrue(all(row_id > top for row_id in new_ids), (top, new_ids))
        self.assertSame(index)

    def _two_calls(self, change):
        self.fill(random.Random(9))
        self.db.log_quiz_answer("x", QUIZ[1], True)
        index = fl.ReviewIndex(self.db)
        self.assertSame(index)
        builds = index.full_builds
        change()
        self.assertSame(index)
        return index, builds

    def test_iii_alles_ersetzen(self):
        import fisi_sicherung as fsi
        other = fc.DBManager(os.path.join(self.dir, "b.db"))
        self.fill(random.Random(11), db=other)
        backup = fsi.read_backup(fsi.create_backup(other, "0.63.1", "B"))
        index, builds = self._two_calls(
            lambda: fsi.replace_all(self.db, backup, os.path.join(self.dir, "sicher")))
        self.assertEqual(index.full_builds, builds + 1)

    def test_iii_alle_lerndaten_loeschen(self):
        index, builds = self._two_calls(self.db.reset_all)
        self.assertEqual(index.full_builds, builds + 1)
        self.db.log_quiz_answer("x", QUIZ[2], False)
        self.assertSame(index)

    def test_iii_historie_loeschen(self):
        self._two_calls(self.db.clear_history)

    def test_iii_loeschmarke_abgleich(self):
        import fisi_sync as fs
        other = fc.DBManager(os.path.join(self.dir, "b.db"))
        remote = fs.export_local(other)
        remote.setdefault("markers", {})["reset_at"] = "2026-10-05 00:00:00"
        index, builds = self._two_calls(
            lambda: fs.merge_into_local(self.db, remote, check_future=False))
        self.assertEqual(index.full_builds, builds + 1)

    # -- Lernstand, Rueckfall, Waechter, KF15 ------------------------------

    def test_t5_lernstand_unveraendert(self):
        self.fill(random.Random(3))
        path = self.db.db_path
        before = hashlib.sha256(open(path, "rb").read()).hexdigest()
        mtime = os.stat(path).st_mtime_ns
        index = fl.ReviewIndex(self.db)
        for _ in range(3):
            index.plan()
        self.assertEqual(hashlib.sha256(open(path, "rb").read()).hexdigest(), before)
        self.assertEqual(os.stat(path).st_mtime_ns, mtime)
        self.assertEqual(sorted(os.listdir(self.dir)), ["t.db"])
        self.db.read_only_reason = "schreibgeschuetzt"     # query_only
        try:
            self.assertSame(fl.ReviewIndex(self.db))
        finally:
            self.db.read_only_reason = None

    def test_t6_rueckfall(self):
        """Kaputtes Datum bzw. Zeitstempel kein Text: gleiches Ergebnis oder
        dieselbe Ausnahme wie die Referenz; Lesefehler -> from_db."""
        self.fill(random.Random(4))
        index = fl.ReviewIndex(self.db)
        self.assertSame(index)
        conn = sqlite3.connect(self.db.db_path)
        insert(conn, "quiz_answers", 20261012, QUIZ[3], 1)          # Zahl statt Text
        conn.commit()
        self.assertSame(index)
        conn.execute("DELETE FROM quiz_answers WHERE typeof(timestamp) != 'text'")
        insert(conn, "quiz_answers", "kein Datum", QUIZ[3], 1)
        conn.commit()
        conn.close()
        ref = self.assertSame(index)
        self.assertEqual(ref, ("err", "ValueError"))
        # Kaputtes Datum bei einer Frage, die es nicht (mehr) gibt: die
        # Referenz ueberspringt sie, der Index faellt auf from_db zurueck
        conn = sqlite3.connect(self.db.db_path)
        conn.execute("DELETE FROM quiz_answers WHERE timestamp = 'kein Datum'")
        insert(conn, "quiz_answers", "kein Datum", "gibt es nicht", 1)
        conn.commit()
        conn.close()
        ref = self.assertSame(index)
        self.assertEqual(ref[0], "ok")
        conn = sqlite3.connect(self.db.db_path)
        conn.execute("DELETE FROM quiz_answers WHERE question = 'gibt es nicht'")
        insert(conn, "quiz_answers", "kein Datum", QUIZ[3], 1)
        conn.commit()
        conn.close()

        class Broken:
            db_path = self.db.db_path

            def get_connection(self):
                raise sqlite3.OperationalError("database is locked")

            question_results = self.db.question_results
        conn = sqlite3.connect(self.db.db_path)
        conn.execute("DELETE FROM quiz_answers WHERE timestamp = 'kein Datum'")
        conn.commit()
        conn.close()
        self.assertEqual(outcome(lambda: fl.ReviewIndex(Broken()).plan()),
                         outcome(lambda: RefPlan.from_db(self.db)))

    def test_t9_waechter_kein_update_im_lernstand(self):
        """Der Index sieht keine Aenderung an Ort und Stelle. Erlaubt sind nur
        die drei bekannten UPDATE-Stellen (keine trifft schon gelesene Zeilen)."""
        allowed = {("fisi_core.py", "UPDATE %s SET question = ? WHERE question = ?"),
                   ("fisi_core.py", "UPDATE %s SET uid = lower(hex(randomblob(16))) "),
                   ("fisi_sync.py", "UPDATE %s SET utc_offset = ? WHERE rowid = ?")}
        found = set()
        names = [n for n in os.listdir(HERE) if n.endswith(".py") and not n.startswith("test_")]
        names += [os.path.join("mobile", "src", "main.py")]
        for name in names:
            text = open(os.path.join(HERE, name), encoding="utf-8").read()
            for match in re.finditer(r"""["'](UPDATE\s[^"']*)["']""", text):
                found.add((name, match.group(1)))
        self.assertEqual(found, allowed)

    def test_kf15_schreiben_zwischen_stempel_und_zeilen(self):
        """Ein Schreiben aus einer zweiten Verbindung genau zwischen Stempel und
        Zeilen darf weder verloren gehen noch doppelt zaehlen."""
        self.fill(random.Random(6))
        index = fl.ReviewIndex(self.db)
        self.assertSame(index)
        db, path, injected = self.db, self.db.db_path, []

        class Conn:
            def __init__(self, inner):
                self.inner = inner

            def execute(self, sql, *args):
                if "WHERE rowid >" in sql and not injected:
                    injected.append(1)
                    other = sqlite3.connect(path, timeout=0.2)
                    try:
                        insert(other, "quiz_answers", "2026-10-13 10:00:00", QUIZ[7], 0)
                        other.commit()
                        injected.append("geschrieben")
                    except sqlite3.OperationalError:
                        injected.append("gesperrt")
                    finally:
                        other.close()
                return self.inner.execute(sql, *args)

            def close(self):
                self.inner.close()

        class Proxy:
            db_path = path
            read_only_reason = None

            def get_connection(self):
                return Conn(db.get_connection())

            def question_results(self):
                return db.question_results()
        proxy_index = fl.ReviewIndex(Proxy())
        proxy_index.plan()
        self.db.log_quiz_answer("x", QUIZ[8], True)
        proxy_index.plan()                 # Schritt mit Einschub
        self.assertEqual(injected[0], 1)
        self.db.log_quiz_answer("x", QUIZ[9], False)
        if injected[-1] == "gesperrt":     # Einschub wartete: jetzt nachholen
            conn = sqlite3.connect(path)
            insert(conn, "quiz_answers", "2026-10-13 10:00:00", QUIZ[7], 0)
            conn.commit()
            conn.close()
        for today in HEUTE:
            self.assertEqual(outcome(lambda: proxy_index.plan(today=today)),
                             outcome(lambda: RefPlan.from_db(self.db, today=today)))
        self.assertEqual(proxy_index.results, {k: v for k, v in self.db.question_results().items()
                                               if k[0] in fl.SR_SOURCES})
        self.assertIn(injected[-1], ("gesperrt", "geschrieben"))
        KF15_EINSCHUB.append(injected[-1])


KF15_EINSCHUB = []


class DashboardTest(Base):
    """T7 und Fall (iv) am echten Dashboard (braucht eine Anzeige)."""

    @classmethod
    def setUpClass(cls):
        import app_gui
        app_gui.UpdateController.auto_check = lambda self: None
        app_gui.SyncController.auto_start = lambda self: None
        app_gui.show_badge_toast = lambda *a, **k: None
        cls.gui = app_gui
        cls.root = app_gui.ctk.CTk()
        cls.errors = []
        cls.root.report_callback_exception = lambda *exc: cls.errors.append(exc)
        cls.root.geometry("1360x900+0+0")
        cls.app = app_gui.FISIApp(cls.root)
        cls.app.show_view("dashboard")
        cls.root.update()
        cls.view = cls.app.views["dashboard"]

    @classmethod
    def tearDownClass(cls):
        try:
            tk_ = cls.root.tk
            for job in tk_.splitlist(tk_.call("after", "info")):
                tk_.call("after", "cancel", job)
            cls.root.destroy()
        except Exception:  # noqa: BLE001
            pass

    def tearDown(self):
        super().tearDown()
        self.assertEqual(self.errors, [])

    def due_label(self):
        self.root.update_idletasks()
        return self.view.lbl_due.cget("text")

    def test_t7_dashboard_schrittweise(self):
        view, db = self.view, self.view.db
        self.fill(random.Random(7), db=db)
        view.refresh()
        index = view._review_index
        self.assertIs(index.db, db)
        start = index.steps
        for i in range(5):
            db.log_quiz_answer("x", QUIZ[30 + i], i % 2 == 0)
            view.refresh()
            self.assertEqual(self.due_label(), fl.due_text(RefPlan.from_db(db)))
        self.assertIs(view._review_index, index)
        self.assertEqual(index.steps - start, 5)

    def test_iv_andere_datenbank(self):
        """(iv) Das Dashboard bekommt eine andere Datenbank: neuer Index, Anzeige
        gleich der Referenz auf der neuen Datenbank."""
        view, old = self.view, self.view.db
        view.refresh()
        other = fc.DBManager(os.path.join(self.dir, "andere.db"))
        conn = sqlite3.connect(other.db_path)
        for i in range(40):
            insert(conn, "quiz_answers", "2026-10-%02d 09:00:00" % (2 + i % 10), QUIZ[200 + i], 0)
        conn.commit()
        conn.close()
        self.assertNotEqual(fl.due_text(RefPlan.from_db(other)), fl.due_text(RefPlan.from_db(old)))
        view.db = other
        try:
            view.refresh()
            self.assertIs(view._review_index.db, other)
            self.assertEqual(self.due_label(), fl.due_text(RefPlan.from_db(other)))
        finally:
            view.db = old
            view.refresh()
        self.assertEqual(self.due_label(), fl.due_text(RefPlan.from_db(old)))


def tearDownModule():
    shutil.rmtree(_TMP, ignore_errors=True)
    if KF15_EINSCHUB:
        print("KF15-Einschub:", KF15_EINSCHUB[-1])


if __name__ == "__main__":
    unittest.main(verbosity=2)
