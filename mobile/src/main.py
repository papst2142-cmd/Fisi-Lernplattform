# -*- coding: utf-8 -*-
"""
FISI Lernplattform - Handy-App (Android)
========================================

Dieselben Lerninhalte, dieselbe Datenbank-Logik und derselbe Abgleich wie die
PC-Version - nur die Oberflaeche ist neu, gebaut mit Flet fuer Touch-Bedienung.
Die gemeinsamen Module (fisi_core, fisi_theme, fisi_update, fisi_sync) und der
Ordner inhalte/ werden beim Bauen aus dem Hauptordner hierher kopiert
(mobile/vorbereiten.py); beim Start aus dem Quellcode werden sie direkt aus
dem Hauptordner geladen.

Start zum Testen am PC:  python mobile/src/main.py
"""

import asyncio
import os
import random
import sys
import time
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
if not os.path.exists(os.path.join(HERE, "fisi_core.py")):
    sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))

# Auf dem Handy liegt die Datenbank im privaten Datenordner der App
if os.environ.get("FLET_APP_STORAGE_DATA") and not os.environ.get("FISI_DB_PATH"):
    os.environ["FISI_DB_PATH"] = os.path.join(os.environ["FLET_APP_STORAGE_DATA"],
                                              "fisi_lernplattform.db")

import flet as ft  # noqa: E402

import fisi_sync  # noqa: E402
import fisi_update  # noqa: E402
from fisi_core import (  # noqa: E402
    AP1_SZENARIEN, AP1_THEMES, AP2_THEMES, CALC_EXPLAIN_RAID, CALC_EXPLAIN_SCREEN,
    CALC_EXPLAIN_SUBNET, CATEGORIES, CATEGORY_SHORT, COLOR_DEPTHS, DBManager,
    FILTER_ALL, InputError, KARTEIKARTEN, PROJEKTARBEITEN, QUIZ_QUESTIONS,
    RAID_LEVELS, STATUS_FILTERS, SZENARIEN, ap1_theme_totals, content_totals,
    filter_positions, group_values, ihk_note, page_slice, raid_report,
    screen_report, search_content, subnet_report, theme_totals, validate_content,
)
from fisi_theme import C, CATEGORY_COLOR, THEME_COLOR  # noqa: E402
import fisi_game  # noqa: E402
import spiel  # noqa: E402
import ui  # noqa: E402

APP_TITLE = "FISI Lernplattform"
# Gleiche Version wie die PC-Version - gesetzt mit
# "python build.py --setze-version <Version>" im Hauptordner.
APP_VERSION = "0.27"

KIND_COLOR = {"Karteikarte": C["cyan"], "Quizfrage": C["purple"],
              "AP1-Szenario": C["blue"], "AP2-Szenario": C["pink"],
              "Testprojekt": C["orange"], "Test-Session": C["green"]}


def german_time(timestamp):
    """'2026-09-27 21:40:05' -> '27.09.2026 21:40'"""
    value = str(timestamp or "")
    if len(value) < 16:
        return value
    return "%s.%s.%s %s" % (value[8:10], value[5:7], value[:4], value[11:16])


def screen_list(controls, spacing=14):
    """Scrollbarer Inhalt einer Seite mit Rand zum Bildschirm."""
    return ft.ListView(controls, spacing=spacing, expand=True,
                       padding=ft.Padding.only(left=16, right=16, top=4, bottom=24))


# ============================================================================
#  BASIS
# ============================================================================

class Screen:
    """Eine Seite der App. build() liefert den Inhalt, on_show() frischt ihn
    beim Anzeigen auf."""

    crumbs = ("FISI", "")

    def __init__(self, app):
        self.app = app
        self.db = app.db
        self.root = self.build()

    def build(self):
        raise NotImplementedError

    def on_show(self):
        pass

    def toast(self, message, color=None):
        self.app.toast(message, color)


# ============================================================================
#  DASHBOARD
# ============================================================================

class DashboardScreen(Screen):
    crumbs = ("DASHBOARD", "HOME")
    DAYS = 14

    def build(self):
        self.totals = content_totals()
        self.total_content = sum(self.totals.values())
        self.hero = ui.HeroPanel()

        self.ring_cards = ui.Ring(size=112)
        self.ring_quiz = ui.Ring(size=112)
        self.ring_ap1 = ui.Ring(size=112)
        self.ring_scen = ui.Ring(size=112)

        def ring_card(title, ring):
            return ui.Card(title, [ft.Row([ring], alignment=ft.MainAxisAlignment.CENTER)],
                           expand=True, padding=14)

        self.lbl_quote = ui.text("0 %", size=34, color=C["cyan"], weight=ft.FontWeight.BOLD)
        self.lbl_quote_sub = ui.text("", size=13, color=C["muted"])

        self.chart = ui.LineChart(height=200)
        self.bar_cards = ui.GradientBar("Karteikarten", C["cyan"], C["purple"])
        self.bar_quiz = ui.GradientBar("Quizfragen", C["purple"], C["pink"])
        self.bar_ap1 = ui.GradientBar("AP1-Szenarien", C["blue"], C["cyan"])
        self.bar_scen = ui.GradientBar("AP2-Szenarien", C["pink"], C["orange"])
        self.heatmap = ui.Heatmap()

        self.fach = {}
        fach_cells = []
        for category in CATEGORIES:
            ring = ui.Ring(size=74, thickness=7, big_size=14, small_size=1)
            ring.small.visible = False
            detail = ui.text("", size=11, color=C["muted"], text_align=ft.TextAlign.CENTER)
            self.fach[category] = (ring, detail)
            fach_cells.append(ft.Column(
                [ring, ui.text(CATEGORY_SHORT[category], size=13, weight=ft.FontWeight.BOLD),
                 detail], spacing=4, expand=True, tight=True,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER))

        self.activity_box = ft.Column(spacing=6, tight=True)
        self.calendar = ui.CalendarPanel(self.db.month_activity)
        self.timeline_ap1 = ui.ThemeProgress()
        self.timeline = ui.ThemeProgress()

        return screen_list([
            self.hero,
            ft.Row([ring_card("Karteikarten", self.ring_cards),
                    ring_card("Quizfragen", self.ring_quiz)], spacing=12),
            ft.Row([ring_card("AP1 Szenarien", self.ring_ap1),
                    ring_card("AP2 Szenarien", self.ring_scen)], spacing=12),
            ui.Card("Erfolgsquote", [self.lbl_quote, self.lbl_quote_sub],
                    accent=C["pink"], subtitle="Quiz gesamt"),
            ui.Card("Lernverlauf", [self.chart], subtitle="letzte %d Tage" % self.DAYS),
            ui.Card("Abdeckung", [self.bar_cards, self.bar_quiz, self.bar_ap1,
                                  self.bar_scen], accent=C["purple"], subtitle="Material",
                    spacing=14),
            ui.Card("Aktivität je Fachbereich", [self.heatmap], accent=C["pink"],
                    subtitle="Intensität pro Tag"),
            ui.Card("Fortschritt je Fachbereich",
                    [ft.Row(fach_cells[:3]), ft.Row(fach_cells[3:])],
                    accent=C["green"], subtitle="Abdeckung und Erfolgsquote", spacing=16),
            ui.Card("Aktivitäten", [self.activity_box], subtitle="zuletzt"),
            ui.Card("Lerntage", [self.calendar], accent=C["purple"],
                    subtitle="Monatsübersicht"),
            ui.Card("AP1 Prüfungsthemen", [self.timeline_ap1], accent=C["blue"],
                    subtitle="bearbeitete Grundlagenaufgaben"),
            ui.Card("AP2 Prüfungsthemen", [self.timeline], accent=C["pink"],
                    subtitle="bearbeitete Szenarien"),
        ])

    def on_show(self):
        self.calendar.to_current_month()
        self.refresh()

    def refresh(self):
        db = self.db
        total_cards, total_quiz = len(KARTEIKARTEN), len(QUIZ_QUESTIONS)
        total_ap1, total_scen = len(AP1_SZENARIEN), len(SZENARIEN)
        learned_cards = db.distinct_cards_learned()
        quiz_answered = db.count_quiz_answers()
        quiz_distinct = db.distinct_quiz_questions()
        ap1_done, scen_done = db.distinct_ap1(), db.distinct_scenarios()
        rate, correct, answered = db.quiz_success_rate()
        learned = learned_cards + quiz_distinct

        self.hero.set_data(
            "Dein Lernstand",
            "Lernserie: %d Tag(e)  ·  %d von %d Inhalten  ·  Quiz %d %%"
            % (db.streak(), learned, self.total_content, round(rate)),
            "%d %%" % round(learned / max(1, self.total_content) * 100),
            "Gesamt")
        self.ring_cards.set(learned_cards / max(1, total_cards), C["cyan"], C["purple"],
                            str(learned_cards), "von %d Karten" % total_cards)
        self.ring_quiz.set(quiz_distinct / max(1, total_quiz), C["purple"], C["pink"],
                           str(quiz_answered), "%d / %d Fragen" % (quiz_distinct, total_quiz))
        self.ring_ap1.set(ap1_done / max(1, total_ap1), C["blue"], C["cyan"],
                          str(ap1_done), "von %d" % total_ap1)
        self.ring_scen.set(scen_done / max(1, total_scen), C["pink"], C["orange"],
                           str(scen_done), "von %d" % total_scen)

        self.lbl_quote.value = "%d %%" % round(rate)
        self.lbl_quote_sub.value = ("%d von %d Fragen richtig beantwortet" % (correct, answered)
                                    if answered else "noch keine Antworten erfasst")

        self.bar_cards.set(learned_cards / max(1, total_cards) * 100,
                           "%d / %d" % (learned_cards, total_cards))
        self.bar_quiz.set(quiz_distinct / max(1, total_quiz) * 100,
                          "%d / %d" % (quiz_distinct, total_quiz))
        self.bar_ap1.set(ap1_done / max(1, total_ap1) * 100, "%d / %d" % (ap1_done, total_ap1))
        self.bar_scen.set(scen_done / max(1, total_scen) * 100,
                          "%d / %d" % (scen_done, total_scen))

        daily = db.daily_counts(self.DAYS)
        self.chart.set_data([day.strftime("%d.%m") for day, _n in daily],
                            [count for _day, count in daily], C["cyan"])
        matrix = db.category_daily(self.DAYS)
        self.heatmap.set_data([(CATEGORY_SHORT[cat], CATEGORY_COLOR[cat], matrix[cat])
                               for cat in CATEGORIES], self.DAYS)

        coverage = db.category_coverage(self.totals)
        stats = db.category_stats()
        for category in CATEGORIES:
            ring, detail = self.fach[category]
            share = coverage.get(category, 0.0)
            ring.set(share / 100.0, CATEGORY_COLOR[category], None, "%d%%" % round(share))
            data = stats.get(category, {"answered": 0, "correct": 0})
            if data["answered"]:
                detail.value = "%d Antworten\n%d%% richtig" % (
                    data["answered"], round(data["correct"] / data["answered"] * 100))
            else:
                detail.value = "noch nicht\nbearbeitet"

        self.activity_box.controls = []
        activities = db.recent_activities(7)
        if not activities:
            self.activity_box.controls.append(ui.text(
                "Noch keine Aktivitäten. Starte mit den Karteikarten oder dem "
                "Prüfungstrainer.", size=13, color=C["muted"]))
        for timestamp, kind, detail, extra in activities:
            self.activity_box.controls.append(ft.Container(
                content=ft.Row([
                    ui.dot(KIND_COLOR.get(kind, C["muted"])),
                    ft.Column([
                        ui.text("%s · %s" % (kind, detail), size=13, color=C["text_dim"],
                                max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                        ui.text("%s  ·  %s" % (german_time(timestamp), extra), size=11,
                                color=C["muted"]),
                    ], spacing=1, tight=True, expand=True),
                ], spacing=10),
                bgcolor=C["card_alt"], border_radius=10,
                padding=ft.Padding.symmetric(horizontal=12, vertical=8)))

        self.calendar.refresh()
        progress = db.theme_progress(theme_totals())
        self.timeline.set_data([(name, progress.get(name, 0.0), THEME_COLOR[name])
                                for name in AP2_THEMES])
        progress_ap1 = db.theme_progress(ap1_theme_totals(), themes=AP1_THEMES,
                                         table="ap1_events")
        self.timeline_ap1.set_data([(name, progress_ap1.get(name, 0.0), THEME_COLOR[name])
                                    for name in AP1_THEMES])


# ============================================================================
#  LERNEN (Uebersicht)
# ============================================================================

class LearnScreen(Screen):
    crumbs = ("LERNEN", "ÜBERSICHT")

    ENTRIES = [
        ("cards", ft.Icons.STYLE_ROUNDED, "Karteikarten",
         "%d Karten in vier Fachbereichen" % len(KARTEIKARTEN), "accent"),
        ("quiz", ft.Icons.TRACK_CHANGES_ROUNDED, "Prüfungstrainer",
         "%d Aufgaben, mit IHK-Note" % len(QUIZ_QUESTIONS), "primary"),
        ("ap1scenarios", ft.Icons.LAYERS_ROUNDED, "AP1 Szenarien",
         "%d Aufgaben der Grundlagenprüfung" % len(AP1_SZENARIEN), ("#2563EB", "#22D3EE")),
        ("scenarios", ft.Icons.DIAMOND_ROUNDED, "AP2 Szenarien",
         "%d Aufgaben der Abschlussprüfung" % len(SZENARIEN), ("#DB2777", "#FB923C")),
        ("testproject", ft.Icons.FLAG_ROUNDED, "Test Projekt",
         "%d Kundenaufträge zum Üben" % len(PROJEKTARBEITEN), "success"),
    ]

    def build(self):
        tiles = []
        for key, icon, title, detail, colors in self.ENTRIES:
            tiles.append(ft.Container(
                content=ft.Row([
                    ft.Container(content=ft.Icon(icon, color=C["on_accent"], size=26),
                                 width=52, height=52, border_radius=16,
                                 gradient=ui.gradient(colors, ft.Alignment.TOP_LEFT,
                                                      ft.Alignment.BOTTOM_RIGHT),
                                 alignment=ft.Alignment.CENTER),
                    ft.Column([ui.text(title, size=16, weight=ft.FontWeight.BOLD),
                               ui.text(detail, size=12, color=C["muted"])],
                              spacing=2, tight=True, expand=True),
                    ft.Icon(ft.Icons.CHEVRON_RIGHT, color=C["muted"]),
                ], spacing=14),
                bgcolor=C["card"], border=ft.Border.all(1, C["border"]), border_radius=16,
                padding=14, ink=True, on_click=lambda _e, k=key: self.app.open(k)))

        chips = []
        for category in CATEGORIES:
            chips.append(ft.Container(
                content=ft.Row([ui.dot(CATEGORY_COLOR[category], 10),
                                ui.text(CATEGORY_SHORT[category], size=13,
                                        weight=ft.FontWeight.BOLD)], spacing=8, tight=True),
                bgcolor=C["card_alt"], border=ft.Border.all(1, C["border"]),
                border_radius=18, padding=ft.Padding.symmetric(horizontal=14, vertical=9),
                ink=True, on_click=lambda _e, c=category: self.app.open_cards(c)))

        return screen_list([
            *tiles,
            ui.Card("Karteikarten nach Fachbereich",
                    [ft.Row(chips, wrap=True, spacing=8, run_spacing=8)],
                    accent=C["cyan"]),
        ], spacing=12)


# ============================================================================
#  KARTEIKARTEN
# ============================================================================

class CardsScreen(Screen):
    crumbs = ("LERNEN", "KARTEIKARTEN")
    MODES = [("freitext", "Freitext"), ("mc", "Multiple Choice"), ("reveal", "Aufdecken")]

    def build(self):
        self.cards = list(KARTEIKARTEN)
        self.filtered = list(self.cards)
        self.index = 0
        self.mode = "freitext"
        self.logged = set()

        options = [("Alle", "Alle")] + [(c, CATEGORY_SHORT[c]) for c in CATEGORIES]
        self.cat_pills = ui.PillGroup(options, on_change=self._on_category)
        self.mode_pills = ui.PillGroup(self.MODES, on_change=self._on_mode)

        self.lbl_question = ui.text("", size=18, weight=ft.FontWeight.BOLD)
        self.question_card = ui.Card("Frage", [self.lbl_question], accent=C["cyan"])

        self.free_hint = ui.text("Formuliere deine Antwort in eigenen Worten:", size=13,
                                 color=C["text_dim"])
        self.txt_answer = ui.entry(multiline=True, min_lines=4, max_lines=10)
        self.options = ui.OptionList()
        self.reveal_hint = ui.text("Überlege dir die Antwort und decke sie "
                                   "anschließend auf.", size=13, color=C["text_dim"])
        self.lbl_feedback = ui.text("", size=15, weight=ft.FontWeight.BOLD)
        self.lbl_solution = ui.text("", size=14, color=C["text_dim"], selectable=True)
        self.answer_card = ui.Card("Deine Antwort", [
            self.free_hint, self.txt_answer, self.options, self.reveal_hint,
            self.lbl_feedback, self.lbl_solution], accent=C["purple"])

        self.btn_check = ui.GradientButton("Antwort prüfen", self.check_answer, expand=True)
        self.lbl_counter = ui.text("", size=13, color=C["text_dim"], weight=ft.FontWeight.BOLD)
        controls = ft.Column([
            ft.Row([self.btn_check]),
            ft.Row([
                ui.GradientButton("Zurück", lambda _e: self.step(-1), kind="ghost",
                                  icon=ft.Icons.ARROW_BACK_ROUNDED, expand=True),
                ui.GradientButton("Nächste", lambda _e: self.step(1), kind="accent",
                                  icon=ft.Icons.ARROW_FORWARD_ROUNDED, expand=True),
            ], spacing=10),
            ft.Row([self.lbl_counter], alignment=ft.MainAxisAlignment.CENTER),
        ], spacing=10, tight=True)

        root = screen_list([
            ui.Card(None, [ui.label("Fachbereich"), self.cat_pills,
                           ui.label("Lernmodus"), self.mode_pills]),
            self.question_card, self.answer_card, controls,
        ])
        self.update_ui()
        return root

    def set_category(self, category):
        self.cat_pills.select_value(category, notify=False)
        self._on_category(category)

    def _on_category(self, category):
        self.filtered = (list(self.cards) if category == "Alle"
                         else [c for c in self.cards if c["cat"] == category])
        self.index = 0
        self.update_ui()

    def _on_mode(self, mode):
        self.mode = mode
        self.update_ui()

    def jump_to_question(self, question_text):
        if not any(card["q"] == question_text for card in self.filtered):
            self.cat_pills.select_value("Alle", notify=False)
            self.filtered = list(self.cards)
        for position, card in enumerate(self.filtered):
            if card["q"] == question_text:
                self.index = position
        self.update_ui()

    def update_ui(self):
        self.lbl_feedback.value = ""
        self.lbl_solution.value = ""
        self.lbl_feedback.visible = self.lbl_solution.visible = False
        self.options.clear()
        for control in (self.free_hint, self.txt_answer, self.options, self.reveal_hint):
            control.visible = False
        if not self.filtered:
            self.lbl_question.value = "Für diesen Fachbereich sind keine Karteikarten hinterlegt."
            self.lbl_counter.value = "0 / 0"
            self.btn_check.set_enabled(False)
            return
        self.btn_check.set_enabled(True)
        card = self.filtered[self.index]
        self.lbl_question.value = card["q"]
        self.lbl_counter.value = "Karte %d / %d" % (self.index + 1, len(self.filtered))
        self.question_card.set_subtitle(CATEGORY_SHORT[card["cat"]], CATEGORY_COLOR[card["cat"]])
        if self.mode == "freitext":
            self.free_hint.visible = self.txt_answer.visible = True
            self.txt_answer.value = ""
            self.btn_check.set_text("Antwort prüfen")
        elif self.mode == "mc":
            self.options.visible = True
            shuffled = list(card["options"])
            random.Random(hash(card["q"]) & 0xFFFF).shuffle(shuffled)
            self.options.set_options(shuffled)
            self.btn_check.set_text("Antwort prüfen")
        else:
            self.reveal_hint.visible = True
            self.btn_check.set_text("Lösung aufdecken")

    def check_answer(self, _event=None):
        if not self.filtered:
            return
        card = self.filtered[self.index]
        correct = None
        if self.mode == "freitext":
            user_input = (self.txt_answer.value or "").strip()
            if not user_input:
                self.toast("Bitte gib zuerst deine Antwort ein.", C["yellow"])
                return
            correct = card["a"].lower() in user_input.lower()
            self.lbl_feedback.value = ("Sehr gut - deine Antwort enthält die Kernlösung."
                                       if correct else
                                       "Vergleiche deine Eingabe mit der Musterlösung:")
            self.lbl_feedback.color = C["green"] if correct else C["yellow"]
            self.lbl_solution.value = "Musterlösung: " + card["a_full"]
        elif self.mode == "mc":
            choice = self.options.get()
            if not choice:
                self.toast("Bitte wähle eine Antwort aus.", C["yellow"])
                return
            correct = choice == card["a"]
            self.options.reveal(card["a"])
            self.lbl_feedback.value = ("Richtig beantwortet." if correct
                                       else "Leider falsch. Richtig wäre: " + card["a"])
            self.lbl_feedback.color = C["green"] if correct else C["red"]
            self.lbl_solution.value = card["a_full"]
        else:
            self.lbl_feedback.value = "Musterlösung"
            self.lbl_feedback.color = C["cyan"]
            self.lbl_solution.value = card["a_full"]

        self.lbl_feedback.visible = self.lbl_solution.visible = True
        key = (card["q"], self.mode)
        if key not in self.logged:
            self.logged.add(key)
            self.db.log_card(card["cat"], card["q"], self.mode, correct)
            self.app.notify_progress()

    def step(self, delta):
        if self.filtered:
            self.index = (self.index + delta) % len(self.filtered)
            self.update_ui()


# ============================================================================
#  PRUEFUNGSTRAINER
# ============================================================================

class QuizScreen(Screen):
    crumbs = ("LERNEN", "PRÜFUNGSTRAINER")

    def build(self):
        self.questions = list(QUIZ_QUESTIONS)
        self.pool = list(self.questions)
        self.session = []
        self.index = 0
        self.score = 0
        self.running = False
        self.answered = False
        self.start_time = 0

        options = [("Alle", "Alle")] + [(c, CATEGORY_SHORT[c]) for c in CATEGORIES]
        self.cat_pills = ui.PillGroup(options, on_change=self._on_category)
        self.stepper = ui.Stepper(value=10, minimum=5, maximum=len(self.questions), step=5)
        self.lbl_pool = ui.text("", size=12, color=C["muted"])
        self.btn_start = ui.GradientButton("Session starten", self.start_quiz, expand=True)
        self.setup_card = ui.Card("Test-Session", [
            ui.label("Fachbereich"), self.cat_pills,
            ft.Row([ui.text("Fragenanzahl", size=13, color=C["text_dim"], expand=True),
                    self.stepper]),
            self.lbl_pool, ft.Row([self.btn_start]),
        ], subtitle="%d Aufgaben im Katalog" % len(self.questions))

        self.lbl_progress = ui.text("Frage 0 / 0", size=14, color=C["text_dim"],
                                    weight=ft.FontWeight.BOLD)
        self.lbl_score = ui.text("", size=12, color=C["muted"])
        self.lbl_timer = ui.text("00:00", size=14, color=C["cyan"], weight=ft.FontWeight.BOLD)
        status = ui.Card(None, [ft.Row([self.lbl_progress, ft.Container(expand=True),
                                        self.lbl_score, self.lbl_timer], spacing=12)],
                         padding=12)

        self.lbl_question = ui.text("Wähle Fachbereich und Fragenanzahl und starte die "
                                    "Session.", size=17, weight=ft.FontWeight.BOLD)
        self.options = ui.OptionList()
        self.lbl_explain = ui.text("", size=14, color=C["text_dim"], selectable=True)
        self.lbl_explain.visible = False
        question = ui.Card("Prüfungsaufgabe", [self.lbl_question, self.options,
                                               self.lbl_explain], accent=C["cyan"])

        self.btn_submit = ui.GradientButton("Antwort einreichen", self.submit_answer,
                                            expand=True)
        self.btn_cancel = ui.GradientButton("Abbrechen", self.cancel_quiz, kind="ghost")
        self.btn_submit.set_enabled(False)
        self.btn_cancel.set_enabled(False)

        self._on_category("Alle")
        return screen_list([self.setup_card, status, question,
                            ft.Row([self.btn_submit, self.btn_cancel], spacing=10)])

    def _on_category(self, category):
        self.pool = (list(self.questions) if category == "Alle"
                     else [q for q in self.questions if q["cat"] == category])
        self.stepper.set_maximum(max(5, len(self.pool)))
        self.lbl_pool.value = "%d Fragen verfügbar" % len(self.pool)

    def start_quiz(self, _event=None):
        if not self.pool:
            self.toast("Für diesen Fachbereich sind keine Fragen hinterlegt.")
            return
        count = min(self.stepper.get(), len(self.pool))
        self.session = random.sample(self.pool, count)
        self.index = 0
        self.score = 0
        self.running = True
        self.start_time = time.time()
        self.btn_start.set_enabled(False)
        self.btn_cancel.set_enabled(True)
        self.load_question()
        self.app.page.run_task(self._tick)

    async def _tick(self):
        while self.running:
            elapsed = int(time.time() - self.start_time)
            self.lbl_timer.value = "%02d:%02d" % (elapsed // 60, elapsed % 60)
            try:
                self.lbl_timer.update()
            except RuntimeError:
                pass  # Seite gerade nicht sichtbar - die Zeit laeuft trotzdem weiter
            await asyncio.sleep(1)

    def load_question(self):
        self.answered = False
        question = self.session[self.index]
        self.lbl_question.value = "%d. %s" % (self.index + 1, question["q"])
        self.lbl_explain.value = ""
        self.lbl_explain.visible = False
        shuffled = list(question["options"])
        random.shuffle(shuffled)
        self.options.set_options(shuffled)
        self.lbl_progress.value = "Frage %d / %d" % (self.index + 1, len(self.session))
        self.lbl_score.value = "%d richtig" % self.score
        self.btn_submit.set_text("Antwort einreichen")
        self.btn_submit.set_enabled(True)

    def submit_answer(self, _event=None):
        if not self.running:
            return
        if self.answered:
            if self.index >= len(self.session) - 1:
                self.finish_quiz()
            else:
                self.index += 1
                self.load_question()
            return
        choice = self.options.get()
        if not choice:
            self.toast("Bitte wähle eine Antwort aus.", C["yellow"])
            return
        question = self.session[self.index]
        correct = choice == question["a"]
        if correct:
            self.score += 1
        self.options.reveal(question["a"])
        self.answered = True
        prefix = "Richtig. " if correct else "Falsch. Richtig wäre: %s. " % question["a"]
        self.lbl_explain.value = prefix + question["exp"]
        self.lbl_explain.visible = True
        self.lbl_explain.color = C["green"] if correct else C["text_dim"]
        self.lbl_score.value = "%d richtig" % self.score
        self.db.log_quiz_answer(question["cat"], question["q"], correct)
        self.app.notify_progress()
        last = self.index >= len(self.session) - 1
        self.btn_submit.set_text("Auswertung anzeigen" if last else "Nächste Frage")

    def cancel_quiz(self, _event=None):
        if not self.running:
            return

        def confirmed():
            self._reset_controls()
            self.lbl_question.value = ("Session abgebrochen. Du kannst jederzeit eine "
                                       "neue starten.")
            self.options.clear()
            self.lbl_explain.value = ""
            self.lbl_explain.visible = False

        self.app.confirm("Session abbrechen",
                         "Die laufende Session wirklich abbrechen? Bereits beantwortete "
                         "Fragen bleiben in der Statistik erhalten.", confirmed)

    def finish_quiz(self):
        total = len(self.session)
        percentage = (self.score / total) * 100 if total else 0.0
        elapsed = int(time.time() - self.start_time)
        note = ihk_note(percentage)
        saved = self.db.save_test_result(self.score, total, percentage, note, elapsed)
        self.options.clear()
        self.lbl_explain.value = ""
        self.lbl_explain.visible = False
        self._reset_controls()
        hint = ("Das Ergebnis wurde gespeichert." if saved
                else "Achtung: Das Ergebnis konnte nicht gespeichert werden.")
        self.lbl_question.value = (
            "Session beendet\n\nErgebnis: %d von %d richtig (%.1f %%)\nIHK-Note: %s\n"
            "Dauer: %02d:%02d Minuten\n\n%s"
            % (self.score, total, percentage, note, elapsed // 60, elapsed % 60, hint))
        self.app.notify_progress()

    def _reset_controls(self):
        self.running = False
        self.btn_start.set_enabled(True)
        self.btn_cancel.set_enabled(False)
        self.btn_submit.set_enabled(False)
        self.btn_submit.set_text("Antwort einreichen")
        self.lbl_progress.value = "Frage 0 / 0"
        self.lbl_timer.value = "00:00"

    def jump_to_question(self, question_text):
        for question in self.questions:
            if question["q"] == question_text:
                self._reset_controls()
                self.lbl_question.value = question["q"]
                self.options.set_options(list(question["options"]))
                self.options.reveal(question["a"])
                self.lbl_explain.value = question["exp"]
                self.lbl_explain.visible = True
                self.lbl_explain.color = C["text_dim"]
                return


# ============================================================================
#  SZENARIEN UND TESTPROJEKTE (Liste -> Detailseite)
# ============================================================================

class PagedListBox:
    """Liste mit Suchfeld, Filter-Pillen und Seiten (gleiche Logik wie am PC,
    siehe fisi_core.filter_positions). Es werden nie mehr als LIST_PAGE_SIZE
    Zeilen gleichzeitig angezeigt, egal wie viele Eintraege es gibt.
    on_select erhaelt die Position in der Gesamtliste."""

    def __init__(self, items, on_select, subtitle, done_source,
                 category_filter=False, group_field=None):
        self.items = items
        self.on_select = on_select
        self.subtitle = subtitle
        self.done_source = done_source
        self.group_field = group_field
        self.done = set()
        self.filtered = list(range(len(items)))
        self.page = 0
        self.query = ""
        self.pills = {}

        search = ui.entry(hint="Titel oder Nummer suchen", on_change=self._search)
        controls = [search]
        if category_filter:
            self.pills["category"] = ui.PillGroup(
                [(FILTER_ALL, FILTER_ALL)] + [(c, CATEGORY_SHORT[c]) for c in CATEGORIES],
                on_change=lambda _v: self.refresh())
        if group_field:
            self.pills["group"] = ui.PillGroup(
                [(v, v) for v in [FILTER_ALL] + group_values(items, group_field)],
                on_change=lambda _v: self.refresh())
        self.pills["status"] = ui.PillGroup([(v, v) for v in STATUS_FILTERS],
                                            on_change=lambda _v: self.refresh())
        controls += list(self.pills.values())
        self.lbl_count = ui.text("", size=12, color=C["muted"])
        self.rows = ft.Column(spacing=8, tight=True)
        self.lbl_page = ui.text("", size=13, color=C["text_dim"])
        pager = ft.Row([
            ft.IconButton(ft.Icons.CHEVRON_LEFT_ROUNDED, icon_color=C["cyan"],
                          on_click=lambda _e: self.turn(-1)),
            self.lbl_page,
            ft.IconButton(ft.Icons.CHEVRON_RIGHT_ROUNDED, icon_color=C["cyan"],
                          on_click=lambda _e: self.turn(1)),
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
        self.root = ft.Column(controls + [self.lbl_count, self.rows, pager],
                              spacing=10, tight=True)

    def _search(self, event):
        self.query = event.control.value or ""
        self.refresh()

    def refresh(self, keep_page=False):
        self.done = self.done_source()
        pills = self.pills
        self.filtered = filter_positions(
            self.items, query=self.query,
            category=pills["category"].get() if "category" in pills else FILTER_ALL,
            group_field=self.group_field,
            group=pills["group"].get() if "group" in pills else FILTER_ALL,
            status=pills["status"].get(), done=self.done)
        if not keep_page:
            self.page = 0
        self._paint()

    def _paint(self):
        visible, self.page, pages = page_slice(self.filtered, self.page)
        self.rows.controls = [
            ui.list_row("%d. %s%s" % (pos + 1, self.items[pos]["title"],
                                      " ✓" if pos in self.done else ""),
                        self.subtitle(self.items[pos]),
                        CATEGORY_COLOR[self.items[pos]["cat"]],
                        lambda _e, p=pos: self.on_select(p))
            for pos in visible] or [ui.text("Keine Treffer für diese Auswahl.",
                                            size=13, color=C["muted"])]
        self.lbl_count.value = "%d von %d Aufgaben" % (len(self.filtered), len(self.items))
        self.lbl_page.value = "Seite %d / %d" % (self.page + 1, pages)

    def turn(self, delta):
        self.page += delta
        self._paint()

    def next_after(self, position):
        """Naechste Position innerhalb der aktuellen Auswahl."""
        if not self.filtered:
            return (position + 1) % len(self.items)
        for candidate in self.filtered:
            if candidate > position:
                return candidate
        return self.filtered[0]


class ScenarioScreen(Screen):
    """AP2-Szenarien: Liste, ein Tipp oeffnet die Aufgabe als eigene Seite."""

    crumbs = ("LERNEN", "AP2 SZENARIEN")
    DATA = SZENARIEN
    LIST_TITLE = "AP2-Szenarien"

    TABLE = "scenario_events"

    def build(self):
        self.index = 0
        self.own_answers = {}
        self.paged = PagedListBox(self.DATA, self.open_detail,
                                  subtitle=lambda item: item["theme"],
                                  done_source=lambda: self.db.completed_indices(self.TABLE),
                                  group_field="theme")
        self.paged.refresh()
        return screen_list([ui.Card(self.LIST_TITLE, [self.paged.root],
                                    subtitle="%d Aufgaben" % len(self.DATA))])

    def on_show(self):
        self.paged.refresh(keep_page=True)

    def open_detail(self, position):
        self.index = position
        self.solution_visible = False
        self.lbl_title = ui.text("", size=18, weight=ft.FontWeight.BOLD)
        self.lbl_theme = ui.text("", size=12, color=C["muted"])
        self.task_box = ui.read_box()
        self.txt_own = ui.entry(multiline=True, min_lines=4, max_lines=18,
                                hint="Deine Lösung ...", on_change=self._own_changed)
        self.solution_box = ui.read_box()
        self.btn_toggle = ui.GradientButton("Musterlösung anzeigen", self.toggle_solution,
                                            expand=True)
        content = screen_list([
            ft.Column([self.lbl_title, self.lbl_theme], spacing=2, tight=True),
            ui.Card("Aufgabenstellung", [self.task_box], accent=C["cyan"]),
            ui.Card("Deine Lösung", [
                ui.text("Löse die Aufgabe hier schriftlich, bevor du die Musterlösung "
                        "aufdeckst.", size=13, color=C["text_dim"]), self.txt_own],
                accent=C["purple"]),
            ui.Card("Musterlösung", [self.solution_box], accent=C["green"]),
            ft.Row([self.btn_toggle]),
            ft.Row([ui.GradientButton("Nächstes Szenario", self.next_item, kind="ghost",
                                      icon=ft.Icons.ARROW_FORWARD_ROUNDED, expand=True)]),
        ])
        self._load()
        self.app.push(self.crumbs, content)

    def _load(self):
        item = self.DATA[self.index]
        self.lbl_title.value = "%d. %s" % (self.index + 1, item["title"])
        self.lbl_theme.value = "%s  ·  %s" % (item["theme"], CATEGORY_SHORT[item["cat"]])
        self.task_box.content.value = item["text"]
        self.txt_own.value = self.own_answers.get(self.index, "")
        self.solution_visible = False
        self.solution_box.content.value = ("Die Musterlösung ist noch ausgeblendet.\n\n"
                                           "Bearbeite die Aufgabe zuerst selbst und decke "
                                           "die Lösung anschließend auf.")
        self.btn_toggle.set_text("Musterlösung anzeigen")

    def _own_changed(self, event):
        self.own_answers[self.index] = event.control.value

    def toggle_solution(self, _event=None):
        item = self.DATA[self.index]
        if self.solution_visible:
            self.solution_box.content.value = "Die Musterlösung ist ausgeblendet."
            self.btn_toggle.set_text("Musterlösung anzeigen")
            self.solution_visible = False
        else:
            self.solution_box.content.value = item["solution"]
            self.btn_toggle.set_text("Musterlösung ausblenden")
            self.solution_visible = True
            self._log(item)
            self.app.notify_progress()
            self.paged.refresh(keep_page=True)

    def _log(self, item):
        self.db.log_scenario(self.index, item["title"], item["theme"])

    def next_item(self, _event=None):
        self.index = self.paged.next_after(self.index)
        self._load()
        self.app.scroll_top()


class Ap1ScenarioScreen(ScenarioScreen):
    crumbs = ("LERNEN", "AP1 SZENARIEN")
    DATA = AP1_SZENARIEN
    LIST_TITLE = "AP1-Szenarien"
    TABLE = "ap1_events"

    def _log(self, item):
        self.db.log_ap1(self.index, item["title"], item["theme"])


class ProjectScreen(Screen):
    crumbs = ("LERNEN", "TEST PROJEKT")

    def build(self):
        self.index = 0
        self.paged = PagedListBox(
            PROJEKTARBEITEN, self.open_detail,
            subtitle=lambda item: "%s · %s" % (item["schwierigkeit"],
                                               CATEGORY_SHORT[item["cat"]]),
            done_source=self.db.completed_projects, category_filter=True,
            group_field="schwierigkeit")
        self.paged.refresh()
        return screen_list([ui.Card("Testprojekte", [self.paged.root],
                                    subtitle="%d Kundenaufträge" % len(PROJEKTARBEITEN))])

    def on_show(self):
        self.paged.refresh(keep_page=True)

    @staticmethod
    def task_text(project):
        lines = ["AUSGANGSSITUATION", project["ausgangssituation"], "",
                 "AUFTRAG", project["auftrag"], "", "RAHMENBEDINGUNGEN"]
        lines += ["  - " + item for item in project["rahmenbedingungen"]]
        lines += ["", "IHRE AUFGABEN (Projektantrag)"]
        lines += ["  %d. %s" % (pos, task) for pos, task in
                  enumerate(project["aufgaben"], start=1)]
        return "\n".join(lines)

    @staticmethod
    def hint_text(project):
        lines = ["Diese Hinweise ersetzen keine eigene Bearbeitung - nutze sie zum "
                 "Vergleich, nachdem du deinen eigenen Projektantrag geschrieben hast.", ""]
        for pos, (task, hint) in enumerate(zip(project["aufgaben"], project["hinweise"]),
                                           start=1):
            lines += ["%d. %s" % (pos, task), "   Lösungsansatz: %s" % hint, ""]
        return "\n".join(lines).rstrip()

    def open_detail(self, position):
        self.index = position
        self.lbl_title = ui.text("", size=18, weight=ft.FontWeight.BOLD)
        self.lbl_meta = ui.text("", size=12, color=C["muted"])
        self.task_box = ui.read_box()
        self.hint_box = ui.read_box()
        self.btn_toggle = ui.GradientButton("Lösungsansätze anzeigen", self.toggle_hints,
                                            expand=True)
        content = screen_list([
            ft.Column([self.lbl_title, self.lbl_meta], spacing=2, tight=True),
            ui.Card("Kundenauftrag", [self.task_box], accent=C["cyan"]),
            ui.Card("Lösungsansätze", [self.hint_box], accent=C["green"]),
            ft.Row([self.btn_toggle]),
            ft.Row([ui.GradientButton("Nächstes Projekt", self.next_item, kind="ghost",
                                      icon=ft.Icons.ARROW_FORWARD_ROUNDED, expand=True)]),
        ])
        self._load()
        self.app.push(self.crumbs, content)

    def _load(self):
        project = PROJEKTARBEITEN[self.index]
        self.lbl_title.value = project["title"]
        self.lbl_meta.value = "%s  ·  Schwierigkeit: %s  ·  %s" % (
            project["branche"], project["schwierigkeit"], CATEGORY_SHORT[project["cat"]])
        self.task_box.content.value = self.task_text(project)
        self.hints_visible = False
        self.hint_box.content.value = (
            "Die Lösungsansätze sind noch ausgeblendet.\n\nBearbeite den Projektantrag "
            "zuerst selbst - Ist-Analyse, Konzept, Zeit- und Kostenplanung, Risiken - "
            "und decke die Lösungsansätze anschließend zum Vergleich auf.")
        self.btn_toggle.set_text("Lösungsansätze anzeigen")

    def toggle_hints(self, _event=None):
        project = PROJEKTARBEITEN[self.index]
        if self.hints_visible:
            self.hint_box.content.value = "Die Lösungsansätze sind ausgeblendet."
            self.btn_toggle.set_text("Lösungsansätze anzeigen")
            self.hints_visible = False
        else:
            self.hint_box.content.value = self.hint_text(project)
            self.btn_toggle.set_text("Lösungsansätze ausblenden")
            self.hints_visible = True
            self.db.log_project(self.index, project["title"], project["cat"])
            self.app.notify_progress()
            self.on_show()

    def next_item(self, _event=None):
        self.index = self.paged.next_after(self.index)
        self._load()
        self.app.scroll_top()


# ============================================================================
#  PRAXIS-RECHNER
# ============================================================================

class CalcScreen(Screen):
    crumbs = ("WERKZEUGE", "RECHNER")

    def build(self):
        self.entry_ip = ui.entry("192.168.1.50/24", on_change=None)
        self.out_subnet = ui.read_box("Noch keine Berechnung durchgeführt.", mono=True)
        subnet = ui.Card("Subnetting / VLSM", [
            ui.text("IP-Adresse mit Präfix (z.B. 192.168.1.50/24)", size=13,
                    color=C["text_dim"]),
            self.entry_ip,
            ft.Row([ui.GradientButton("Berechnen", self.calc_subnet, kind="accent")]),
            self.out_subnet, *self._explain(CALC_EXPLAIN_SUBNET),
        ], accent=C["cyan"], subtitle="IPv4 und IPv6")

        self.raid_pills = ui.PillGroup([(level, level) for level in RAID_LEVELS], initial=2)
        self.entry_disks = ui.entry("4", keyboard=ft.KeyboardType.NUMBER, expand=True)
        self.entry_size = ui.entry("1000", keyboard=ft.KeyboardType.NUMBER, expand=True)
        self.out_raid = ui.read_box("Noch keine Berechnung durchgeführt.", mono=True)
        raid = ui.Card("RAID-Kapazität", [
            ui.text("RAID-Level", size=13, color=C["text_dim"]), self.raid_pills,
            self._field("Anzahl Festplatten", self.entry_disks),
            self._field("Kapazität je Platte (GB)", self.entry_size),
            ft.Row([ui.GradientButton("Berechnen", self.calc_raid)]),
            self.out_raid, *self._explain(CALC_EXPLAIN_RAID),
        ], accent=C["purple"], subtitle="Netto, Parität, Effizienz")

        self.entry_width = ui.entry("1920", keyboard=ft.KeyboardType.NUMBER, expand=True)
        self.entry_height = ui.entry("1080", keyboard=ft.KeyboardType.NUMBER, expand=True)
        self.entry_fps = ui.entry("0", keyboard=ft.KeyboardType.NUMBER, expand=True)
        self.depth_pills = ui.PillGroup(COLOR_DEPTHS, initial=2)
        self.out_screen = ui.read_box("Noch keine Berechnung durchgeführt.", mono=True)
        screen = ui.Card("Bildschirm-Datenvolumen", [
            self._field("Breite (Pixel)", self.entry_width),
            self._field("Höhe (Pixel)", self.entry_height),
            self._field("Bildwiederholrate (fps, optional)", self.entry_fps),
            ui.text("Farbtiefe", size=13, color=C["text_dim"]), self.depth_pills,
            ft.Row([ui.GradientButton("Berechnen", self.calc_screen, kind="accent")]),
            self.out_screen, *self._explain(CALC_EXPLAIN_SCREEN),
        ], accent=C["green"], subtitle="Pixel, Farbtiefe, Datenrate")
        return screen_list([subnet, raid, screen])

    @staticmethod
    def _field(caption, field):
        return ft.Row([ui.text(caption, size=13, color=C["text_dim"], expand=2),
                       ft.Container(content=field, expand=1)],
                      vertical_alignment=ft.CrossAxisAlignment.CENTER)

    @staticmethod
    def _explain(explanation):
        box = ui.read_box(explanation, mono=True)
        box.visible = False
        button = ui.GradientButton("Rechenweg anzeigen", None, kind="ghost", height=40)

        def toggle(_event):
            box.visible = not box.visible
            button.set_text("Rechenweg ausblenden" if box.visible else "Rechenweg anzeigen")

        button._handler = toggle
        return [ft.Row([button]), box]

    def _run(self, output, calculation):
        try:
            output.content.value = calculation()
        except InputError as error:
            self.toast(str(error), C["red"])

    def calc_subnet(self, _event=None):
        self._run(self.out_subnet, lambda: subnet_report(self.entry_ip.value or ""))

    def calc_raid(self, _event=None):
        self._run(self.out_raid, lambda: raid_report(
            self.raid_pills.get(), self.entry_disks.value or "", self.entry_size.value or ""))

    def calc_screen(self, _event=None):
        self._run(self.out_screen, lambda: screen_report(
            self.entry_width.value or "", self.entry_height.value or "",
            self.depth_pills.get(), self.entry_fps.value or ""))


# ============================================================================
#  LERNFORTSCHRITT
# ============================================================================

class ProgressScreen(Screen):
    crumbs = ("AUSWERTUNG", "FORTSCHRITT")

    def build(self):
        self.stats = {}

        def stat(key, title, color):
            value = ui.text("-", size=26, weight=ft.FontWeight.BOLD)
            sub = ui.text("", size=11, color=C["muted"])
            self.stats[key] = (value, sub)
            return ui.Card(title, [value, sub], accent=color, expand=True, spacing=4,
                           padding=14)

        self.chart = ui.LineChart(height=200)
        self.history = ft.Column(spacing=8, tight=True)
        return screen_list([
            ft.Row([stat("tests", "Sessions", C["cyan"]),
                    stat("avg", "Durchschnitt", C["purple"])], spacing=12),
            ft.Row([stat("best", "Bestes", C["pink"]),
                    stat("streak", "Lernserie", C["green"])], spacing=12),
            ui.Card("Ergebnisse im Zeitverlauf", [self.chart],
                    subtitle="Erfolgsquote je Session"),
            ui.Card("Historie der Prüfungssessions", [self.history], accent=C["purple"]),
            ft.Row([ui.GradientButton("Aktualisieren", lambda _e: self.on_show(),
                                      kind="ghost", expand=True),
                    ui.GradientButton("Historie löschen", self.clear_history,
                                      kind="danger", expand=True)], spacing=10),
        ])

    def on_show(self):
        results = self.db.get_all_results()
        count, average = self.db.get_stats()
        self._stat("tests", str(count), "abgeschlossene Sessions")
        self._stat("avg", "%.1f %%" % average, "über alle Sessions")
        if results:
            best = max(row[3] for row in results)
            self._stat("best", "%.1f %%" % best, ihk_note(best))
        else:
            self._stat("best", "-", "noch keine Session")
        self._stat("streak", str(self.db.streak()), "Tage in Folge")

        ordered = list(reversed(results))[-20:]
        labels = [row[0][8:10] + "." + row[0][5:7] for row in ordered] or ["heute"]
        values = [row[3] for row in ordered] or [0]
        self.chart.set_data(labels, values, C["pink"], y_max=100)

        self.history.controls = []
        if not results:
            self.history.controls.append(ui.text("Noch keine Prüfungssessions.", size=13,
                                                 color=C["muted"]))
        for timestamp, score, total, percentage, note, duration in results[:50]:
            self.history.controls.append(ft.Container(
                content=ft.Row([
                    ft.Column([
                        ui.text(german_time(timestamp), size=13, weight=ft.FontWeight.BOLD),
                        ui.text("%d / %d  ·  %02d:%02d min" % (score, total, duration // 60,
                                                              duration % 60),
                                size=12, color=C["muted"]),
                    ], spacing=2, tight=True, expand=True),
                    ft.Column([
                        ui.text("%.1f %%" % percentage, size=15, color=C["cyan"],
                                weight=ft.FontWeight.BOLD),
                        ui.text(note, size=11, color=C["text_dim"]),
                    ], spacing=2, tight=True,
                        horizontal_alignment=ft.CrossAxisAlignment.END),
                ]),
                bgcolor=C["card_alt"], border_radius=10,
                padding=ft.Padding.symmetric(horizontal=12, vertical=10)))

    def _stat(self, key, value, sub):
        self.stats[key][0].value = value
        self.stats[key][1].value = sub

    def clear_history(self, _event=None):
        def confirmed():
            if self.db.clear_history():
                self.on_show()
                self.app.notify_progress()

        self.app.confirm("Historie löschen",
                         "Wirklich alle gespeicherten Testergebnisse löschen? Die "
                         "Lern-Ereignisse für das Dashboard bleiben erhalten.", confirmed)


# ============================================================================
#  EINSTELLUNGEN
# ============================================================================

class SettingsScreen(Screen):
    crumbs = ("SYSTEM", "OPTIONEN")

    def build(self):
        self.btn_update = ui.GradientButton("Nach Updates suchen", self.check_updates)
        self.lbl_update = ui.text("", size=13, color=C["text_dim"])
        self.lbl_update.visible = False
        auto = fisi_update.load_settings()["auto_check"]
        updates = ui.Card("Updates", [
            ft.Row([self.btn_update]), self.lbl_update,
            self._switch("Beim Start automatisch nach Updates suchen", auto,
                         self._toggle_auto),
        ], accent=C["pink"], subtitle="installierte Version %s" % APP_VERSION)

        settings = fisi_sync.sync_settings()
        self.entry_repo = ui.entry(settings["sync_repo"], hint="Benutzer/fisi-lernstand")
        self.entry_token = ui.entry(settings["sync_token"], hint="github_pat_...",
                                    password=True)
        self.btn_sync = ui.GradientButton("Speichern und abgleichen", self.sync_now,
                                          kind="accent")
        self.lbl_sync = ui.text("", size=13, color=C["text_dim"])
        sync = ui.Card("Abgleich PC und Handy", [
            ui.text("Repository (Benutzer/Name)", size=13, color=C["text_dim"]),
            self.entry_repo,
            ui.text("Zugangsschlüssel (Token)", size=13, color=C["text_dim"]),
            self.entry_token,
            ft.Row([self.btn_sync]), self.lbl_sync,
            self._switch("Automatisch abgleichen (beim Start, nach dem Lernen und beim "
                         "Verlassen der App)", settings["sync_auto"], self._toggle_sync_auto),
            ui.text("Auf PC und Handy dasselbe Repository und denselben Zugangsschlüssel "
                    "eintragen. Die Anleitung steht in LIESMICH.txt unter „Abgleich PC "
                    "und Handy“.", size=11, color=C["muted"]),
        ], accent=C["cyan"], subtitle="privates GitHub-Repository")
        self.show_sync_status(None, None)

        totals = content_totals()
        lines = ["Karteikarten gesamt: %d" % len(KARTEIKARTEN),
                 "Quizfragen gesamt: %d" % len(QUIZ_QUESTIONS),
                 "AP1-Szenarien gesamt: %d" % len(AP1_SZENARIEN),
                 "AP2-Szenarien gesamt: %d" % len(SZENARIEN),
                 "Testprojekte gesamt: %d" % len(PROJEKTARBEITEN), ""]
        lines += ["%s: %d Inhalte" % (CATEGORY_SHORT[c], totals.get(c, 0)) for c in CATEGORIES]

        return screen_list([
            updates, sync,
            ui.Card("Lerninhalte", [ui.text("\n".join(lines), size=14, color=C["text_dim"])],
                    accent=C["purple"]),
            ui.Card("Daten zurücksetzen", [
                ui.text("Setzt sämtliche Lernfortschritte zurück: Testergebnisse, "
                        "Karteikarten-Verlauf, Quiz-Antworten und bearbeitete Szenarien. "
                        "Der Spielstand des Lernspiels bleibt erhalten. Mit eingerichtetem "
                        "Abgleich auch auf dem PC. Dieser Schritt lässt sich nicht "
                        "rückgängig machen.", size=13, color=C["text_dim"]),
                ft.Row([ui.GradientButton("Alle Lerndaten löschen", self.reset_all,
                                          kind="danger")]),
            ], accent=C["red"]),
            ui.Card("Spiel", [
                ui.text("Setzt nur den Spielstand zurück: Spielfigur, Spielgeld, "
                        "Reputation, Arbeitstage und erledigte Tickets. Der Lernfortschritt "
                        "bleibt erhalten. Mit eingerichtetem Abgleich auch auf dem PC.",
                        size=13, color=C["text_dim"]),
                ft.Row([ui.GradientButton("Spielstand zurücksetzen", self.reset_game,
                                          kind="danger")]),
            ], accent=C["pink"]),
            ui.Card("Über das Programm", [ui.text(
                "%s Version %s\n\nLernprogramm für die Umschulung zum Fachinformatiker "
                "Systemintegration mit Karteikarten, Prüfungstrainer, AP1-/AP2-Szenarien, "
                "Testprojekten und Praxis-Rechnern.\n\nDie Handy-App nutzt dieselben "
                "Lerninhalte wie die PC-Version und ist mit Python und Flet umgesetzt."
                % (APP_TITLE, APP_VERSION), size=14, color=C["text_dim"])],
                accent=C["green"]),
        ])

    @staticmethod
    def _switch(caption, value, handler):
        return ft.Row([
            ft.Switch(value=value, on_change=handler, active_color=C["text"],
                      active_track_color=C["violet"], inactive_track_color=C["card_alt"],
                      inactive_thumb_color=C["muted"]),
            ui.text(caption, size=13, color=C["text_dim"], expand=True),
        ], spacing=8)

    def _toggle_auto(self, event):
        settings = fisi_update.load_settings()
        settings["auto_check"] = bool(event.control.value)
        fisi_update.save_settings(settings)

    def _toggle_sync_auto(self, event):
        fisi_sync.save_sync_settings(sync_auto=bool(event.control.value))

    def sync_now(self, _event=None):
        fisi_sync.save_sync_settings(sync_repo=(self.entry_repo.value or "").strip(),
                                     sync_token=(self.entry_token.value or "").strip())
        if not fisi_sync.is_configured():
            self.lbl_sync.value = "Bitte Repository und Zugangsschlüssel eintragen."
            self.lbl_sync.color = C["yellow"]
            return
        self.btn_sync.set_enabled(False)
        self.lbl_sync.value = "Gleiche ab ..."
        self.lbl_sync.color = C["text_dim"]
        self.app.sync.run()

    def show_sync_status(self, result, error):
        self.btn_sync.set_enabled(True)
        if error:
            self.lbl_sync.value, self.lbl_sync.color = error, C["red"]
            return
        last = fisi_sync.sync_settings()["sync_last"]
        if not fisi_sync.is_configured():
            self.lbl_sync.value, self.lbl_sync.color = "Noch nicht eingerichtet.", C["muted"]
        elif result is not None:
            self.lbl_sync.value, self.lbl_sync.color = result.message, C["green"]
        elif last:
            self.lbl_sync.value = "Zuletzt abgeglichen: %s" % german_time(last)
            self.lbl_sync.color = C["text_dim"]
        else:
            self.lbl_sync.value, self.lbl_sync.color = "Noch nicht abgeglichen.", C["muted"]

    def check_updates(self, _event=None):
        self.btn_update.set_enabled(False)
        self.lbl_update.value = "Suche nach Updates ..."
        self.lbl_update.visible = True
        self.lbl_update.color = C["text_dim"]
        self.app.check_updates(manual=True)

    def show_update_status(self, info, error):
        self.btn_update.set_enabled(True)
        if error:
            self.lbl_update.value, self.lbl_update.color = error, C["red"]
        elif info is None:
            self.lbl_update.value = "Du hast die neueste Version (%s)." % APP_VERSION
            self.lbl_update.color = C["green"]
        else:
            self.lbl_update.value = "Version %s ist verfügbar." % info.version
            self.lbl_update.color = C["cyan"]

    def reset_game(self, _event=None):
        def confirmed():
            if fisi_game.Game(self.db).reset():
                self.toast("Der Spielstand wurde zurückgesetzt.", C["green"])
                self.app.screens["game"].room = None
                self.app.notify_progress()

        self.app.confirm("Spielstand zurücksetzen",
                         "Wirklich den gesamten Spielstand des Lernspiels löschen? Der "
                         "Lernfortschritt bleibt erhalten.", confirmed)

    def reset_all(self, _event=None):
        def confirmed():
            if self.db.reset_all():
                self.toast("Alle Lerndaten wurden gelöscht.", C["green"])
                self.app.notify_progress()

        self.app.confirm("Alles zurücksetzen",
                         "Wirklich ALLE Lerndaten unwiderruflich löschen?", confirmed)


# ============================================================================
#  SUCHE
# ============================================================================

class SearchScreen(Screen):
    crumbs = ("SUCHE", "ERGEBNISSE")

    def build(self):
        self.field = ui.entry(hint="Suchen ... (z.B. RAID, DNS, DSGVO)", expand=True)
        self.field.on_submit = lambda _e: self.search(self.field.value or "")
        self.field.autofocus = True
        self.lbl_info = ui.text("", size=13, color=C["text_dim"])
        self.results = ft.Column(spacing=8, tight=True)
        return screen_list([
            ft.Row([self.field, ft.Container(
                content=ft.Icon(ft.Icons.SEARCH_ROUNDED, color=C["on_accent"]),
                width=48, height=48, border_radius=24, gradient=ui.gradient("primary"),
                alignment=ft.Alignment.CENTER, ink=True,
                on_click=lambda _e: self.search(self.field.value or ""))], spacing=10),
            self.lbl_info, self.results,
        ])

    def search(self, query):
        query = query.strip()
        if not query:
            return
        hits = search_content(query)
        self.lbl_info.value = '%d Treffer für "%s"' % (len(hits), query)
        self.results.controls = []
        if not hits:
            self.results.controls.append(ui.text(
                "Keine Treffer. Versuche einen anderen Suchbegriff.", color=C["muted"]))
        for kind, category, title, detail in hits[:60]:
            snippet = detail if len(detail) <= 140 else detail[:138] + "…"
            self.results.controls.append(ft.Container(
                content=ft.Row([
                    ft.Container(width=4, height=48, border_radius=2,
                                 bgcolor=CATEGORY_COLOR.get(category, C["purple"])),
                    ft.Column([
                        ui.text("%s · %s" % (kind, CATEGORY_SHORT.get(category, "")),
                                size=11, color=C["muted"]),
                        ui.text(title, size=14, weight=ft.FontWeight.BOLD),
                        ui.text(snippet, size=12, color=C["text_dim"]),
                    ], spacing=2, tight=True, expand=True),
                ], spacing=12),
                bgcolor=C["card"], border=ft.Border.all(1, C["border"]), border_radius=12,
                padding=12, ink=True,
                on_click=lambda _e, k=kind, t=title: self.app.open_search_hit(k, t)))
        if len(hits) > 60:
            self.results.controls.append(ui.text(
                "... weitere %d Treffer nicht angezeigt." % (len(hits) - 60), size=12,
                color=C["muted"]))
        self.app.page.update()


# ============================================================================
#  ABGLEICH UND UPDATES
# ============================================================================

class SyncController:
    """Wie am PC: beim Start, kurz nach dem Lernen und beim Verlassen der App
    abgleichen - sofern eingerichtet und nicht abgeschaltet."""

    DELAY = 30

    def __init__(self, app):
        self.app = app
        self.busy = False
        self.again = False
        self.dirty = False
        self.waiting = False

    @staticmethod
    def auto_enabled():
        settings = fisi_sync.sync_settings()
        return fisi_sync.is_configured(settings) and settings["sync_auto"]

    def run(self):
        if self.busy:
            self.again = True
            return
        self.busy = True
        self.dirty = False
        self.app.page.run_thread(self._work)

    def _work(self):
        result, error = None, None
        try:
            result = fisi_sync.sync(self.app.db, device="Handy")
        except fisi_sync.SyncError as exc:
            error = str(exc)
        except Exception as exc:  # nie die App wegen des Abgleichs abstuerzen lassen
            error = "Unerwarteter Fehler beim Abgleich: %s" % exc
        self.busy = False
        if result is not None and result.received:
            self.app.refresh_after_sync()
        self.app.screens["settings"].show_sync_status(result, error)
        self.app.page.update()
        if self.again:
            self.again = False
            self.run()

    def auto_start(self):
        if self.auto_enabled():
            self.run()

    def schedule(self):
        self.dirty = True
        if not self.waiting and self.auto_enabled():
            self.waiting = True
            self.app.page.run_task(self._delayed)

    async def _delayed(self):
        await asyncio.sleep(self.DELAY)
        self.waiting = False
        self.run()

    def on_leave(self):
        """App geht in den Hintergrund: noch offene Eintraege hochladen."""
        if self.dirty and self.auto_enabled():
            self.run()


# ============================================================================
#  APP
# ============================================================================

NAV = [
    ("dashboard", ft.Icons.DASHBOARD_OUTLINED, ft.Icons.DASHBOARD_ROUNDED, "Start"),
    ("learn", ft.Icons.SCHOOL_OUTLINED, ft.Icons.SCHOOL_ROUNDED, "Lernen"),
    ("calc", ft.Icons.CALCULATE_OUTLINED, ft.Icons.CALCULATE_ROUNDED, "Rechner"),
    ("game", ft.Icons.SPORTS_ESPORTS_OUTLINED, ft.Icons.SPORTS_ESPORTS_ROUNDED, "Spiel"),
    ("progress", ft.Icons.INSIGHTS_OUTLINED, ft.Icons.INSIGHTS_ROUNDED, "Fortschritt"),
    ("settings", ft.Icons.SETTINGS_OUTLINED, ft.Icons.SETTINGS_ROUNDED, "Optionen"),
]

SCREEN_CLASSES = {
    "dashboard": DashboardScreen, "learn": LearnScreen, "cards": CardsScreen,
    "game": spiel.GameScreen,
    "quiz": QuizScreen, "ap1scenarios": Ap1ScenarioScreen, "scenarios": ScenarioScreen,
    "testproject": ProjectScreen, "calc": CalcScreen, "progress": ProgressScreen,
    "settings": SettingsScreen, "search": SearchScreen,
}


class FISIMobileApp:
    def __init__(self, page):
        self.page = page
        page.title = "%s %s" % (APP_TITLE, APP_VERSION)
        page.bgcolor = C["bg"]
        page.theme_mode = ft.ThemeMode.DARK
        page.padding = 0
        page.theme = page.dark_theme = ft.Theme(
            color_scheme=ft.ColorScheme(
                primary=C["purple"], secondary=C["cyan"], surface=C["bg"],
                on_surface=C["text"], error=C["red"]),
            navigation_bar_theme=ft.NavigationBarTheme(
                bgcolor=C["sidebar"], indicator_color=C["card_hi"],
                label_text_style=ft.TextStyle(size=11, color=C["text_dim"])))

        self.db = DBManager(error_handler=lambda message: self.toast(message, C["red"]))
        self.sync = SyncController(self)
        self.screens = {key: cls(self) for key, cls in SCREEN_CLASSES.items()}
        self.tab = "dashboard"
        self.update_dialog_open = False

        self.crumb_main = ft.Text("", size=12, weight=ft.FontWeight.BOLD, color=C["text"])
        self.crumb_sub = ft.Text("", size=12, weight=ft.FontWeight.BOLD, color=C["cyan"])
        self.body = ft.Container(expand=True)
        self.nav = ft.NavigationBar(
            destinations=[ft.NavigationBarDestination(
                icon=ft.Icon(icon, color=C["muted"]),
                selected_icon=ft.Icon(selected, color=C["cyan"]), label=caption)
                for _key, icon, selected, caption in NAV],
            selected_index=0, on_change=self._nav_changed,
            bgcolor=C["sidebar"], indicator_color=C["card_hi"])

        page.views.clear()
        page.views.append(ft.View(
            route="/", controls=[self.body], appbar=self._appbar(root=True),
            navigation_bar=self.nav, bgcolor=C["bg"], padding=0))
        page.on_view_pop = self._view_popped
        page.on_app_lifecycle_state_change = self._lifecycle
        self.show_tab("dashboard")

    # -- Kopfzeile und Navigation ------------------------------------------

    def _appbar(self, root, crumbs=None):
        if crumbs:
            title = ft.Row([ft.Text(crumbs[0], size=12, weight=ft.FontWeight.BOLD,
                                    color=C["text"]),
                            ft.Text("/", size=12, color=C["muted"]),
                            ft.Text(crumbs[1], size=12, weight=ft.FontWeight.BOLD,
                                    color=C["cyan"])], spacing=7)
        else:
            title = ft.Row([self.crumb_main, ft.Text("/", size=12, color=C["muted"]),
                            self.crumb_sub], spacing=7)
        leading = None
        if root:
            logo = ui.Ring(size=30, thickness=4, big_size=1, small_size=1)
            logo.set(1.0, C["cyan"], C["pink"])
            logo.controls[1] = ft.Container(content=ui.dot(C["pink"], 10), width=30,
                                            height=30, alignment=ft.Alignment.CENTER)
            leading = ft.Container(content=logo, padding=ft.Padding.only(left=16),
                                   alignment=ft.Alignment.CENTER_LEFT)
        return ft.AppBar(
            leading=leading, leading_width=52 if root else None, title=title,
            bgcolor=C["bg"], elevation=0, color=C["text"],
            actions=[ft.IconButton(ft.Icons.SEARCH_ROUNDED, icon_color=C["text_dim"],
                                   on_click=lambda _e: self.open("search")),
                     ft.Container(width=6)])

    def _nav_changed(self, event):
        self.show_tab(NAV[event.control.selected_index][0])

    def show_tab(self, key):
        while len(self.page.views) > 1:
            self.page.views.pop()
        self.tab = key
        self.nav.selected_index = [item[0] for item in NAV].index(key)
        screen = self.screens[key]
        self.crumb_main.value, self.crumb_sub.value = screen.crumbs
        screen.on_show()
        self.body.content = screen.root
        self.page.update()

    def open(self, key):
        """Unterseite (z.B. Karteikarten, Suche) ueber der aktuellen Seite
        oeffnen - der Zurueck-Pfeil bzw. die Zurueck-Geste fuehrt zurueck."""
        screen = self.screens[key]
        screen.on_show()
        self.push(screen.crumbs, screen.root)

    def push(self, crumbs, content):
        self.page.views.append(ft.View(
            route="/%d" % len(self.page.views), controls=[content],
            appbar=self._appbar(root=False, crumbs=crumbs), bgcolor=C["bg"], padding=0))
        self.page.update()

    def _view_popped(self, event):
        if len(self.page.views) > 1:
            self.page.views.pop()
        top = self.page.views[-1]
        if len(self.page.views) == 1:
            self.screens[self.tab].on_show()
        del top
        self.page.update()

    def scroll_top(self):
        view = self.page.views[-1]
        content = view.controls[0] if view.controls else None
        if isinstance(content, ft.ListView):
            content.scroll_to(offset=0, duration=200)

    def open_cards(self, category):
        self.screens["cards"].set_category(category)
        self.open("cards")

    def open_search_hit(self, kind, title):
        if kind == "Karteikarte":
            self.screens["cards"].jump_to_question(title)
            self.open("cards")
        elif kind == "Quizfrage":
            self.screens["quiz"].jump_to_question(title)
            self.open("quiz")
        else:
            key = "ap1scenarios" if kind == "AP1-Szenario" else "scenarios"
            screen = self.screens[key]
            for position, item in enumerate(screen.DATA):
                if item["title"] == title:
                    screen.open_detail(position)
                    return

    # -- Rueckmeldungen ------------------------------------------------------

    def toast(self, message, color=None):
        self.page.show_dialog(ft.SnackBar(
            ft.Text(message, color=C["text"]), bgcolor=C["card_hi"],
            behavior=ft.SnackBarBehavior.FLOATING,
            shape=ft.RoundedRectangleBorder(radius=12),
            show_close_icon=True, close_icon_color=color or C["text_dim"]))

    def confirm(self, title, message, on_yes):
        def answer(yes):
            self.page.pop_dialog()
            if yes:
                on_yes()
            self.page.update()

        self.page.show_dialog(ft.AlertDialog(
            modal=True, bgcolor=C["card"],
            title=ft.Text(title, color=C["text"], size=18, weight=ft.FontWeight.BOLD),
            content=ft.Text(message, color=C["text_dim"], size=14),
            actions=[ft.TextButton("Abbrechen", on_click=lambda _e: answer(False)),
                     ft.TextButton("Ja", on_click=lambda _e: answer(True))]))

    def notify_progress(self):
        """Nach jeder Lernaktivitaet: Abgleich vormerken."""
        self.sync.schedule()

    def refresh_after_sync(self):
        if len(self.page.views) == 1:
            self.screens[self.tab].on_show()

    def _lifecycle(self, event):
        if event.state in (ft.AppLifecycleState.PAUSE, ft.AppLifecycleState.HIDE,
                           ft.AppLifecycleState.INACTIVE):
            self.sync.on_leave()

    # -- Updates -------------------------------------------------------------

    def check_updates(self, manual=False):
        def work():
            info, error = None, None
            try:
                info = fisi_update.check_for_update(APP_VERSION, kind="android")
            except fisi_update.UpdateError as exc:
                error = str(exc)
            except Exception as exc:
                error = "Unerwarteter Fehler: %s" % exc
            if manual:
                self.screens["settings"].show_update_status(info, error)
            if info is not None:
                self.show_update_dialog(info)
            self.page.update()

        self.page.run_thread(work)

    def auto_check(self):
        if fisi_update.load_settings().get("auto_check", True):
            self.check_updates()

    def show_update_dialog(self, info):
        if self.update_dialog_open:
            return
        self.update_dialog_open = True

        def close(_event=None):
            self.update_dialog_open = False
            self.page.pop_dialog()

        async def download(_event):
            close()
            await ft.UrlLauncher().launch_url(info.asset_url or info.page_url,
                                              mode=ft.LaunchMode.EXTERNAL_APPLICATION)

        notes = fisi_update.plain_notes(info.notes) or "Keine Beschreibung vorhanden."
        hint = ("Die neue Version wird im Browser heruntergeladen. Danach die Datei "
                "öffnen und „Installieren“ tippen - dein Lernstand bleibt erhalten."
                if info.asset_url else
                "Für Android ist in diesem Release keine App-Datei dabei.")
        self.page.show_dialog(ft.AlertDialog(
            modal=True, bgcolor=C["card"],
            title=ft.Text("FISI Lernplattform %s ist verfügbar" % info.version,
                          color=C["text"], size=18, weight=ft.FontWeight.BOLD),
            content=ft.Column([
                ft.Text("installiert: %s" % APP_VERSION, size=12, color=C["muted"]),
                ft.Text("NEUERUNGEN", size=11, weight=ft.FontWeight.BOLD, color=C["muted"]),
                ft.Text(notes, size=13, color=C["text_dim"]),
                ft.Text(hint, size=12, color=C["cyan"]),
            ], tight=True, spacing=8, scroll=ft.ScrollMode.AUTO, height=320),
            actions=[ft.TextButton("Später", on_click=close),
                     ft.TextButton("Herunterladen", on_click=download)]))


def main(page: ft.Page):
    app = FISIMobileApp(page)
    page.data = app
    if os.environ.get("FISI_SELFTEST"):
        return
    app.sync.auto_start()
    app.auto_check()


def selftest():
    """Baut alle Seiten ohne Bildschirm auf und prueft die Inhalte - fuer den
    automatischen Test nach dem Build (GitHub Actions). Rueckgabe: Fehlerliste."""
    failures = list(validate_content())

    class FakePage:
        views = []

        def __getattr__(self, _name):
            return lambda *args, **kwargs: None

    class FakeApp(FISIMobileApp):
        def __init__(self):
            self.page = FakePage()
            self.db = DBManager()
            self.sync = SyncController(self)
            self.screens = {}
            for key, cls in SCREEN_CLASSES.items():
                try:
                    self.screens[key] = cls(self)
                except Exception:
                    failures.append("%s: %s" % (key, traceback.format_exc()))

    app = FakeApp()
    for key, screen in app.screens.items():
        try:
            screen.on_show()
            if hasattr(screen, "refresh"):
                screen.refresh()
        except Exception:
            failures.append("%s: %s" % (key, traceback.format_exc()))
    try:
        # Lernspiel: Uebersicht und ein Ticket aufbauen, ohne etwas zu speichern
        game = app.screens["game"]
        game.game.state.profile = {"name": "Test",
                                   "aussehen": dict(fisi_game.DEFAULT_APPEARANCE)}
        game.render()
        for task in fisi_game.GAME["aufgaben"]:
            game.open_ticket(task["id"])
            game._show_help()
            # PC zusammenbauen und Warenkorb einmal bedienen
            solution = fisi_game.find_solution(task, game.available)
            if task["typ"] == "bauteile" and solution:
                for slot in task["slots"]:
                    game.options.pick_slot(slot)
                    if solution.get(slot):
                        game.options.pick_part(solution[slot])
                game.options.reveal(True)
            elif task["typ"] == "bestellung":
                for offer_id, count in solution.items():
                    for _step in range(count):
                        game.options.change(offer_id, 1)
                game.options.reveal(True)
            elif task["typ"] == "rack":
                for key, bottom in solution.items():
                    game.options.pick_device(int(key))
                    game.options.tap_unit(bottom)
                game.options.pick_device(0)
                game.options.remove()
                game.options.reveal(True)
            elif task["typ"] == "formular":
                for field_id, value in solution.items():
                    if field_id in game.options.inputs:
                        game.options.inputs[field_id].value = value
                    else:
                        game.options._choose(field_id, value)
                game.options.reveal(True)
        game._select_room("serverraum")
        game._select_room("lager")
        # Bueroansicht (ohne reload, der Test-Spielstand steht nur im Speicher)
        game.office = ft.Column()
        game._fill_office()
        for person in fisi_game.GAME["kollegen"]:
            game._office_text(tuple(person["platz"]), person)
        app.screens["search"].search("raid")
        app.screens["calc"].calc_subnet()
        app.screens["calc"].calc_raid()
        app.screens["calc"].calc_screen()
    except Exception:
        failures.append(traceback.format_exc())
    return failures


if __name__ == "__main__":
    if "--selbsttest" in sys.argv:
        problems = selftest()
        print("\n".join(problems) if problems else "Selbsttest OK")
        sys.exit(1 if problems else 0)
    if "--web" in sys.argv:
        # Zum Testen am PC im Browser (Handy-Ansicht ueber die Entwicklertools)
        ft.run(main, view=ft.AppView.WEB_BROWSER, port=8550)
    else:
        ft.run(main)
