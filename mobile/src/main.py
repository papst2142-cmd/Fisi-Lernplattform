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

import fisi_sicherung as fsi  # noqa: E402
import fisi_sync  # noqa: E402
import fisi_update  # noqa: E402
from fisi_core import (  # noqa: E402
    AP1_SZENARIEN, AP1_THEMES, AP2_THEMES, CALC_EXPLAIN_RAID, CALC_EXPLAIN_SCREEN,
    CALC_EXPLAIN_SUBNET, CATEGORIES, CATEGORY_SHORT, COLOR_DEPTHS, DBManager,
    count_word,
    FILTER_ALL, InputError, KARTEIKARTEN, PROJEKTARBEITEN, QUIZ_QUESTIONS,
    RAID_LEVELS, STATUS_FILTERS, SZENARIEN, TOPIC_NAME, TOPIC_SHORT, TOPICS,
    LEVEL_RED, LEVEL_YELLOW, Q_DONE, Q_OPEN, Q_PRACTICE, Q_STATUS_NAME, Q_STATUS_TABS,
    SOURCE_NAME, SOURCE_PLURAL, SOURCES, SRC_AP1, SRC_AP2, SRC_CARD, SRC_PROJECT,
    SRC_QUIZ, StatusBook, model_answer, notebook_entries, notebook_summary,
    position_statuses, status_label,
    ap1_theme_totals, content_totals,
    filter_positions, group_values, ihk_note, page_slice, raid_report,
    screen_report, search_content, subnet_report, theme_totals, validate_content,
)
import fisi_theme  # noqa: E402
from fisi_theme import C, CATEGORY_COLOR, THEME_COLOR, mix  # noqa: E402
import fisi_game  # noqa: E402
from fisi_lernen import (  # noqa: E402
    GOAL_MAX, GOAL_MIN, GOAL_STEP, TRAINER_KIND_NAME, TRAINER_KINDS, TRAINER_LEVEL_NAME,
    TRAINER_LEVELS, TRAINER_ROUND, DailyGoal, ReviewPlan, due_text, learning_settings,
    parse_time, reminder_due, reminder_text, save_learning_settings, trainer_round,
    trainer_summary,
)
import fisi_projekt as fpj  # noqa: E402
import fisi_pruefung as fp  # noqa: E402
import spiel  # noqa: E402
import ui  # noqa: E402

APP_TITLE = "FISI Lernplattform"
# Gleiche Version wie die PC-Version - gesetzt mit
# "python build.py --setze-version <Version>" im Hauptordner.
APP_VERSION = "0.52"

def kind_color(kind):
    """Farbe je Aktivitaetsart (Karteikarte und AP2 folgen der Grundfarbe)."""
    return {"Karteikarte": C["accent"], "Quizfrage": C["purple"],
            "AP1-Szenario": C["blue"], "AP2-Szenario": C["accent2"],
            "Testprojekt": C["orange"], "Test-Session": C["green"]}.get(kind, C["muted"])


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


def status_color(key):
    """Farbe zum Lernstand einer Frage (Schluessel aus status_label, ab 0.39)."""
    return {LEVEL_RED: C["red"], LEVEL_YELLOW: C["yellow"], "fertig": C["green"],
            Q_DONE: C["green"]}.get(key, C["muted"])


def count_text(counts):
    return "Offen %d · Zu üben %d · Abgeschlossen %d" % (
        counts[Q_OPEN], counts[Q_PRACTICE], counts[Q_DONE])


class TopicPills:
    """Themen-Pillen passend zum gewaehlten Fachbereich (seitlich scrollbar)."""

    def __init__(self, on_change):
        self.on_change = on_change
        self.pills = None
        self.root = ft.Container()
        self.set_category(FILTER_ALL)

    def set_category(self, category, topic=None):
        topics = [t for cat in CATEGORIES for t in TOPICS[cat]] \
            if category in (None, FILTER_ALL) else TOPICS.get(category, [])
        options = [(FILTER_ALL, "Alle Themen")] + [(t, TOPIC_SHORT[t]) for t in topics]
        keys = [key for key, _name in options]
        self.pills = ui.PillGroup(options, initial=keys.index(topic) if topic in keys else 0,
                                  on_change=lambda _v: self.on_change())
        self.root.content = self.pills

    def get(self):
        return self.pills.get()


def rate_row(command):
    """Zeile "Gewusst" / "Nicht gewusst" nach dem Aufdecken (ab 0.39)."""
    row = ft.Column([
        ui.text("Wusstest du es?", size=13, color=C["text_dim"]),
        ft.Row([ui.GradientButton("Gewusst", lambda _e: command(True), expand=True),
                ui.GradientButton("Nicht gewusst", lambda _e: command(False), kind="ghost",
                                  expand=True)], spacing=10),
    ], spacing=6, tight=True)
    row.visible = False
    return row


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

    # -- Reinzoom in die Themen eines Fachbereichs --------------------------

    def _toggle_zoom(self, category):
        """Antippen eines Fachbereichs zeigt dessen Themen, erneutes
        Antippen (oder Schliessen) blendet sie wieder aus."""
        self.zoom_category = None if category == self.zoom_category else category
        self.zoom_holder.controls = []
        self.zoom_bars = {}
        if self.zoom_category:
            self._build_zoom(self.zoom_category)
        self.zoom_holder.visible = bool(self.zoom_category)
        self.refresh()
        self.app.page.update()

    def _build_zoom(self, category):
        color = CATEGORY_COLOR[category]
        bars = []
        for index, topic in enumerate(TOPICS[category]):
            shade = mix(color, C["card"], 0.12 * (index % 3))
            bar = ui.GradientBar(TOPIC_NAME[topic], mix(shade, C["card"], 0.4), shade)
            self.zoom_bars[topic] = bar
            bars.append(bar)
        self.zoom_holder.controls = [ui.Card("Themen · %s" % category, [
            ui.text("Aktivität je Thema (letzte %d Tage)" % self.DAYS, size=12,
                    color=C["muted"]),
            self.zoom_heatmap,
            ui.text("Wissensstand je Thema (zählt für die Aufträge im Spiel)", size=12,
                    color=C["muted"]),
            *bars,
            ft.Row([ui.GradientButton("Schließen", lambda _e: self._toggle_zoom(category),
                                      kind="ghost", height=38)]),
        ], accent=color, subtitle="Aktivität und Wissen", spacing=12)]

    def _refresh_zoom(self):
        category = self.zoom_category
        if not category:
            return
        color = CATEGORY_COLOR[category]
        matrix = self.db.topic_daily(category, self.DAYS)
        self.zoom_heatmap.set_data([(TOPIC_SHORT[topic], color, matrix[topic])
                                    for topic in TOPICS[category]], self.DAYS,
                                   label_width=100)
        levels = fisi_game.topic_knowledge(self.db)
        stats = self.db.topic_stats()
        for topic, bar in self.zoom_bars.items():
            answered = stats[topic]["answered"]
            bar.set(levels[topic], "Wissen %d %%  ·  %d Antworten" % (levels[topic], answered)
                    if answered else "noch nicht bearbeitet")

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

        self.lbl_quote = ui.text("0 %", size=34, color=C["accent"], weight=ft.FontWeight.BOLD)
        self.lbl_quote_sub = ui.text("", size=13, color=C["muted"])

        self.chart = ui.LineChart(height=200)
        self.bar_cards = ui.GradientBar("Karteikarten", C["accent"], C["purple"])
        self.bar_quiz = ui.GradientBar("Quizfragen", C["purple"], C["accent2"])
        self.bar_ap1 = ui.GradientBar("AP1-Szenarien", C["blue"], C["accent"])
        self.bar_scen = ui.GradientBar("AP2-Szenarien", C["accent2"], C["orange"])
        self.heatmap = ui.Heatmap()

        self.fach = {}
        fach_cells = []
        for category in CATEGORIES:
            ring = ui.Ring(size=74, thickness=7, big_size=14, small_size=1)
            ring.small.visible = False
            detail = ui.text("", size=11, color=C["muted"], text_align=ft.TextAlign.CENTER)
            name = ui.text(CATEGORY_SHORT[category], size=13, weight=ft.FontWeight.BOLD)
            self.fach[category] = (ring, detail, name)
            fach_cells.append(ft.Container(
                content=ft.Column([ring, name, detail], spacing=4, tight=True,
                                  horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                expand=True, border_radius=12,
                on_click=lambda _e, cat=category: self._toggle_zoom(cat)))

        # Reinzoom: Themen eines Fachbereichs (ab 0.37), erscheint nach
        # Antippen eines Fachbereichs unter "Fortschritt je Fachbereich"
        self.zoom_category = None
        self.zoom_holder = ft.Column([], tight=True, visible=False)
        self.zoom_heatmap = ui.Heatmap()
        self.zoom_bars = {}

        # Ab 0.51: Kachel "Heute" mit Tagesziel, Lernserie und Wiederholungen
        self.goal_ring = ui.Ring(size=74, thickness=7, big_size=14, small_size=1)
        self.goal_ring.small.visible = False
        self.lbl_goal = ui.text("", size=14, weight=ft.FontWeight.BOLD)
        self.lbl_streak = ui.text("", size=13, color=C["text_soft"])
        self.goal_row = ft.Row([self.goal_ring, ft.Column(
            [self.lbl_goal, self.lbl_streak], spacing=4, tight=True, expand=True)],
            spacing=14, vertical_alignment=ft.CrossAxisAlignment.CENTER)
        self.lbl_due = ui.text("", size=14, weight=ft.FontWeight.BOLD)
        self.btn_review = ui.GradientButton("Jetzt wiederholen",
                                            lambda _e: self.app.start_review())
        self.today_card = ui.Card("Heute", [self.goal_row, self.lbl_due,
                                            ft.Row([self.btn_review])],
                                  accent=C["green"], subtitle="Tagesziel und Wiederholung")

        self.activity_box = ft.Column(spacing=6, tight=True)
        self.calendar = ui.CalendarPanel(self.db.month_activity)
        self.timeline_ap1 = ui.ThemeProgress()
        self.timeline = ui.ThemeProgress()

        return screen_list([
            self.hero,
            self.today_card,
            ft.Row([ring_card("Karteikarten", self.ring_cards),
                    ring_card("Quizfragen", self.ring_quiz)], spacing=12),
            ft.Row([ring_card("AP1 Szenarien", self.ring_ap1),
                    ring_card("AP2 Szenarien", self.ring_scen)], spacing=12),
            ui.Card("Erfolgsquote", [self.lbl_quote, self.lbl_quote_sub],
                    accent=C["accent2"], subtitle="Quiz gesamt"),
            ui.Card("Lernverlauf", [self.chart], subtitle="letzte %d Tage" % self.DAYS),
            ui.Card("Abdeckung", [self.bar_cards, self.bar_quiz, self.bar_ap1,
                                  self.bar_scen], accent=C["purple"], subtitle="Material",
                    spacing=14),
            ui.Card("Aktivität je Fachbereich", [self.heatmap], accent=C["accent2"],
                    subtitle="Auswahl zeigt die Themen"),
            ui.Card("Fortschritt je Fachbereich",
                    [ft.Row(fach_cells[:3]), ft.Row(fach_cells[3:])],
                    accent=C["green"], subtitle="Auswahl zeigt die Themen", spacing=16),
            self.zoom_holder,
            ui.Card("Aktivitäten", [self.activity_box], subtitle="zuletzt"),
            ui.Card("Lerntage", [self.calendar], accent=C["purple"],
                    subtitle="Monatsübersicht"),
            ui.Card("AP1 Prüfungsthemen", [self.timeline_ap1], accent=C["blue"],
                    subtitle="bearbeitete Grundlagenaufgaben"),
            ui.Card("AP2 Prüfungsthemen", [self.timeline], accent=C["accent2"],
                    subtitle="bearbeitete Szenarien"),
        ])

    def on_show(self):
        self.calendar.to_current_month()
        self.refresh()

    def _refresh_today(self):
        settings = learning_settings()
        goal = DailyGoal.from_db(self.db, settings["ziel_anzahl"])
        self.goal_row.visible = settings["ziel_an"] or settings["serie_an"]
        self.goal_ring.visible = self.lbl_goal.visible = settings["ziel_an"]
        self.lbl_streak.visible = settings["serie_an"]
        self.goal_ring.set(goal.fraction, C["green"] if goal.reached else C["accent"],
                           big="%d%%" % round(goal.fraction * 100))
        self.lbl_goal.value = goal.text()
        self.lbl_streak.value = goal.streak_text()
        plan = ReviewPlan.from_db(self.db)
        self.lbl_due.value = due_text(plan)
        self.btn_review.visible = plan.count() > 0

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

        self._refresh_today()
        streak = ("Lernserie: %d Tag(e)  ·  " % db.streak()
                  if learning_settings()["serie_an"] else "")
        self.hero.set_data(
            "Dein Lernstand",
            "%s%d von %d Inhalten  ·  Quiz %d %%"
            % (streak, learned, self.total_content, round(rate)),
            "%d %%" % round(learned / max(1, self.total_content) * 100),
            "Gesamt")
        self.ring_cards.set(learned_cards / max(1, total_cards), C["accent"], C["purple"],
                            str(learned_cards), "von %d Karten" % total_cards)
        self.ring_quiz.set(quiz_distinct / max(1, total_quiz), C["purple"], C["accent2"],
                           str(quiz_answered), "%d / %d Fragen" % (quiz_distinct, total_quiz))
        self.ring_ap1.set(ap1_done / max(1, total_ap1), C["blue"], C["accent"],
                          str(ap1_done), "von %d" % total_ap1)
        self.ring_scen.set(scen_done / max(1, total_scen), C["accent2"], C["orange"],
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
                            [count for _day, count in daily], C["accent"])
        matrix = db.category_daily(self.DAYS)
        self.heatmap.set_data([(CATEGORY_SHORT[cat], CATEGORY_COLOR[cat], matrix[cat])
                               for cat in CATEGORIES], self.DAYS,
                              on_click=lambda index: self._toggle_zoom(CATEGORIES[index]),
                              selected=CATEGORIES.index(self.zoom_category)
                              if self.zoom_category else None)
        self._refresh_zoom()

        coverage = db.category_coverage(self.totals)
        stats = db.category_stats()
        for category in CATEGORIES:
            ring, detail, name = self.fach[category]
            name.color = (CATEGORY_COLOR[category] if category == self.zoom_category
                          else C["text"])
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
                    ui.dot(kind_color(kind)),
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
         "%d Karten in %s Fachbereichen" % (len(KARTEIKARTEN), count_word(len(CATEGORIES))),
         "accent"),
        ("quiz", ft.Icons.TRACK_CHANGES_ROUNDED, "Prüfungstrainer",
         "%d Aufgaben, mit IHK-Note" % len(QUIZ_QUESTIONS), "primary"),
        ("ap1scenarios", ft.Icons.LAYERS_ROUNDED, "AP1 Szenarien",
         "%d Aufgaben der Grundlagenprüfung" % len(AP1_SZENARIEN), ("#2563EB", "#22D3EE")),
        ("scenarios", ft.Icons.DIAMOND_ROUNDED, "AP2 Szenarien",
         "%d Aufgaben der Abschlussprüfung" % len(SZENARIEN), ("#DB2777", "#FB923C")),
        ("testproject", ft.Icons.FLAG_ROUNDED, "Test Projekt",
         "%d Kundenaufträge zum Üben" % len(PROJEKTARBEITEN), "success"),
        ("abschluss", ft.Icons.WORKSPACE_PREMIUM_ROUNDED, "Abschlussprojekt",
         "Dein IHK-Projekt vom Antrag bis zum Fachgespräch", ("#7C3AED", "#22D3EE")),
        ("notebook", ft.Icons.EDIT_NOTE_ROUNDED, "Notizblock",
         "Was du noch üben musst, aus allen Bereichen", ("#DC2626", "#FBBF24")),
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
                    accent=C["accent"]),
        ], spacing=12)


# ============================================================================
#  KARTEIKARTEN
# ============================================================================

class CardsScreen(Screen):
    crumbs = ("LERNEN", "KARTEIKARTEN")
    MODES = [("freitext", "Freitext"), ("mc", "Multiple Choice"), ("reveal", "Aufdecken")]

    def build(self):
        self.cards = list(KARTEIKARTEN)
        self.by_question = {card["q"]: card for card in self.cards}
        self.filtered = list(self.cards)
        self.index = 0
        self.mode = "freitext"
        self.book = StatusBook(self.db)
        self.count_keys = []
        # Je Anzeige einer Karte hoechstens einmal speichern; im Modus
        # "Aufdecken" erst mit der Selbsteinschaetzung (ab 0.39)
        self.logged = False
        self.pending = None

        options = [("Alle", "Alle")] + [(c, CATEGORY_SHORT[c]) for c in CATEGORIES]
        self.cat_pills = ui.PillGroup(options, on_change=self._on_category)
        self.status_pills = ui.PillGroup(Q_STATUS_TABS, on_change=lambda _v: self.apply_filter())
        self.topic_pills = TopicPills(self.apply_filter)
        self.lbl_counts = ui.text("", size=11, color=C["muted"])
        self.mode_pills = ui.PillGroup(self.MODES, on_change=self._on_mode)

        self.lbl_status = ui.text("", size=13, weight=ft.FontWeight.BOLD, color=C["muted"])
        self.lbl_question = ui.text("", size=18, weight=ft.FontWeight.BOLD)
        self.question_card = ui.Card("Frage", [self.lbl_status, self.lbl_question],
                                     accent=C["accent"])

        self.free_hint = ui.text("Formuliere deine Antwort in eigenen Worten:", size=13,
                                 color=C["text_dim"])
        self.txt_answer = ui.entry(multiline=True, min_lines=4, max_lines=10)
        self.options = ui.OptionList()
        self.reveal_hint = ui.text("Überlege dir die Antwort und decke sie "
                                   "anschließend auf.", size=13, color=C["text_dim"])
        self.lbl_feedback = ui.text("", size=15, weight=ft.FontWeight.BOLD)
        self.lbl_solution = ui.text("", size=14, color=C["text_dim"], selectable=True)
        self.rate_box = rate_row(self.rate)
        self.answer_card = ui.Card("Deine Antwort", [
            self.free_hint, self.txt_answer, self.options, self.reveal_hint,
            self.lbl_feedback, self.lbl_solution, self.rate_box], accent=C["purple"])

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
                           ui.label("Status"), self.status_pills,
                           ui.label("Thema"), self.topic_pills.root, self.lbl_counts,
                           ui.label("Lernmodus"), self.mode_pills]),
            self.question_card, self.answer_card, controls,
        ])
        self.apply_filter()
        return root

    def on_show(self):
        # Neue Antworten (z.B. nach einem Abgleich) im Status beruecksichtigen
        self.book = StatusBook(self.db)
        self._show_status()

    def set_category(self, category, topic=None):
        """Fachbereich waehlen; mit topic nur die Karten dieses Themas (aus
        dem Spiel: "Karteikarten zu ...")."""
        self.cat_pills.select_value(category, notify=False)
        self.topic_pills.set_category(category, topic)
        self.apply_filter()

    def practice(self, questions):
        """Gezielte Uebungsrunde aus dem Notizblock: nur diese Karten."""
        self.cat_pills.select_value("Alle", notify=False)
        self.status_pills.select_value(FILTER_ALL, notify=False)
        self.topic_pills.set_category(FILTER_ALL)
        self._flush()
        self.book = StatusBook(self.db)
        self.filtered = [self.by_question[q] for q in questions if q in self.by_question]
        self.index = 0
        self._counts([card["q"] for card in self.filtered])
        self.update_ui()

    def _on_category(self, category):
        self.topic_pills.set_category(category)
        self.apply_filter()

    def apply_filter(self):
        """Fachbereich, Thema und Status anwenden. Ohne Status-Filter kommen
        unbearbeitete Karten zuerst (mit gelegentlicher Wiederholung)."""
        self._flush()
        self.book = StatusBook(self.db)
        category = self.cat_pills.get()
        topic = self.topic_pills.get()
        status = self.status_pills.get()
        base = [card for card in self.cards
                if (category == "Alle" or card["cat"] == category)
                and (topic == FILTER_ALL or card.get("thema") == topic)]
        keys = [card["q"] for card in base]
        if status == FILTER_ALL:
            keys = self.book.preferred_order(SRC_CARD, keys)
        else:
            keys = [key for key in keys if self.book.status(SRC_CARD, key)[0] == status]
        self.filtered = [self.by_question[key] for key in keys]
        self.index = 0
        self._counts([card["q"] for card in base])
        self.update_ui()

    def _counts(self, keys):
        self.count_keys = keys
        self.lbl_counts.value = count_text(self.book.counts(SRC_CARD, keys))

    def _on_mode(self, mode):
        self._flush()
        self.mode = mode
        self.update_ui()

    def jump_to_question(self, question_text):
        if not any(card["q"] == question_text for card in self.filtered):
            self.cat_pills.select_value("Alle", notify=False)
            self.status_pills.select_value(FILTER_ALL, notify=False)
            self.topic_pills.set_category(FILTER_ALL)
            self.apply_filter()
        self._flush()
        for position, card in enumerate(self.filtered):
            if card["q"] == question_text:
                self.index = position
        self.update_ui()

    def _flush(self):
        """Aufgedeckt, aber nicht bewertet: als angesehen speichern."""
        if self.pending is not None:
            card, self.pending = self.pending, None
            self.db.log_card(card["cat"], card["q"], "reveal", None)
            self.app.notify_progress()

    def _show_status(self):
        if not self.filtered:
            self.lbl_status.value = ""
            return
        text, key = status_label(self.book, SRC_CARD, self.filtered[self.index]["q"])
        self.lbl_status.value = text
        self.lbl_status.color = status_color(key)

    def update_ui(self):
        self._flush()
        self.logged = False
        self.lbl_feedback.value = ""
        self.lbl_solution.value = ""
        self.lbl_feedback.visible = self.lbl_solution.visible = False
        self.rate_box.visible = False
        self.options.clear()
        for control in (self.free_hint, self.txt_answer, self.options, self.reveal_hint):
            control.visible = False
        if not self.filtered:
            self.lbl_question.value = "Für diese Auswahl gibt es keine Karteikarten."
            self.lbl_status.value = ""
            self.lbl_counter.value = "0 / 0"
            self.btn_check.set_enabled(False)
            return
        self.btn_check.set_enabled(True)
        card = self.filtered[self.index]
        self.lbl_question.value = card["q"]
        self._show_status()
        self.lbl_counter.value = "Karte %d / %d" % (self.index + 1, len(self.filtered))
        self.question_card.set_subtitle("%s · %s" % (CATEGORY_SHORT[card["cat"]],
                                                     TOPIC_SHORT[card["thema"]]),
                                        CATEGORY_COLOR[card["cat"]])
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
            self.lbl_feedback.color = C["accent"]
            self.lbl_solution.value = card["a_full"]
            self.lbl_feedback.visible = self.lbl_solution.visible = True
            if not self.logged:
                self.pending = card
                self.rate_box.visible = True
            return

        self.lbl_feedback.visible = self.lbl_solution.visible = True
        if not self.logged:
            self.logged = True
            self._save(card, correct)

    def rate(self, correct):
        """Selbsteinschaetzung nach dem Aufdecken."""
        card, self.pending = self.pending, None
        if card is None:
            return
        self.rate_box.visible = False
        self.logged = True
        self._save(card, correct)

    def _save(self, card, correct):
        self.db.log_card(card["cat"], card["q"], self.mode, correct)
        self.book = StatusBook(self.db)
        self._show_status()
        self._counts(self.count_keys)
        self.app.notify_progress()

    def step(self, delta):
        if self.filtered:
            self._flush()
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
        self.status_pills = ui.PillGroup(Q_STATUS_TABS, on_change=lambda _v: self._update_pool())
        self.topic_pills = TopicPills(self._update_pool)
        self.stepper = ui.Stepper(value=10, minimum=5, maximum=len(self.questions), step=5)
        self.lbl_pool = ui.text("", size=12, color=C["muted"])
        self.btn_start = ui.GradientButton("Session starten", self.start_quiz, expand=True)
        self.setup_card = ui.Card("Test-Session", [
            ui.label("Fachbereich"), self.cat_pills,
            ui.label("Status"), self.status_pills,
            ui.label("Thema"), self.topic_pills.root,
            ft.Row([ui.text("Fragenanzahl", size=13, color=C["text_dim"], expand=True),
                    self.stepper]),
            self.lbl_pool, ft.Row([self.btn_start]),
        ], subtitle="%d Aufgaben im Katalog" % len(self.questions))

        self.lbl_progress = ui.text("Frage 0 / 0", size=14, color=C["text_dim"],
                                    weight=ft.FontWeight.BOLD)
        self.lbl_score = ui.text("", size=12, color=C["muted"])
        self.lbl_timer = ui.text("00:00", size=14, color=C["accent"], weight=ft.FontWeight.BOLD)
        status = ui.Card(None, [ft.Row([self.lbl_progress, ft.Container(expand=True),
                                        self.lbl_score, self.lbl_timer], spacing=12)],
                         padding=12)

        self.lbl_question = ui.text("Wähle Fachbereich und Fragenanzahl und starte die "
                                    "Session.", size=17, weight=ft.FontWeight.BOLD)
        self.options = ui.OptionList()
        self.lbl_explain = ui.text("", size=14, color=C["text_dim"], selectable=True)
        self.lbl_explain.visible = False
        question = ui.Card("Prüfungsaufgabe", [self.lbl_question, self.options,
                                               self.lbl_explain], accent=C["accent"])

        self.btn_submit = ui.GradientButton("Antwort einreichen", self.submit_answer,
                                            expand=True)
        self.btn_cancel = ui.GradientButton("Abbrechen", self.cancel_quiz, kind="ghost")
        self.btn_submit.set_enabled(False)
        self.btn_cancel.set_enabled(False)

        self._on_category("Alle")
        # Ab 0.51: Umschalter Uebung / Pruefung (Klausursimulation)
        self.practice_box = ft.Column([self.setup_card, status, question,
                                       ft.Row([self.btn_submit, self.btn_cancel],
                                              spacing=10)], spacing=14, tight=True)
        self.exam = ExamPanel(self.app)
        self.exam.visible = False
        self.mode_pills = ui.PillGroup(QUIZ_MODES, on_change=self._on_mode)
        return screen_list([self.mode_pills, self.practice_box, self.exam])

    def _on_mode(self, mode):
        if mode == "pruefung":
            if self.running:
                self._reset_controls()
            self.exam.show()
        else:
            self.exam.hide()
        self.exam.visible = mode == "pruefung"
        self.practice_box.visible = not self.exam.visible

    def _on_category(self, category):
        self.topic_pills.set_category(category)
        self._update_pool()

    def on_show(self):
        # Ab 0.51: eine laufende Pruefung geht vor
        if fp.load_running() is not None and self.mode_pills.get() != "pruefung":
            self.mode_pills.select_value("pruefung")
            return
        if self.mode_pills.get() == "pruefung":
            self.exam.show()
        elif not self.running:
            self._update_pool()

    def _update_pool(self):
        """Fachbereich, Thema und Status (ab 0.39) anwenden."""
        category = self.cat_pills.get()
        topic = self.topic_pills.get()
        status = self.status_pills.get()
        self.book = StatusBook(self.db)
        base = [q for q in self.questions
                if (category == "Alle" or q["cat"] == category)
                and (topic == FILTER_ALL or q.get("thema") == topic)]
        self.pool = [q for q in base if self.book.matches(SRC_QUIZ, q["q"], status)]
        self.stepper.set_maximum(max(5, len(self.pool)))
        counts = self.book.counts(SRC_QUIZ, [q["q"] for q in base])
        self.lbl_pool.value = "%d Fragen verfügbar\n%s" % (len(self.pool), count_text(counts))

    def practice(self, questions, keep_order=False):
        """Gezielte Uebungsrunde aus dem Notizblock: nur diese Fragen
        (hoechstens 50). keep_order: die erste Frage kommt zuerst."""
        if self.mode_pills.get() != "uebung":
            if fp.load_running() is not None:
                self.toast("Es läuft gerade eine Prüfung. Gib sie zuerst ab oder brich "
                           "sie ab.", C["yellow"])
                return
            self.mode_pills.select_value("uebung")
        if self.running:
            self._reset_controls()
        by_question = {q["q"]: q for q in self.questions}
        session = [by_question[key] for key in questions if key in by_question]
        if not session:
            return
        if not keep_order:
            random.shuffle(session)
        self.session = session[:50]
        self.pool = list(self.session)
        self._begin()

    def start_quiz(self, _event=None):
        if not self.pool:
            self.toast("Für diese Auswahl gibt es keine Fragen.")
            return
        count = min(self.stepper.get(), len(self.pool))
        if self.status_pills.get() == FILTER_ALL:
            # Unbearbeitete Fragen zuerst, dazwischen Wiederholungen
            keys = self.book.preferred_order(SRC_QUIZ, [q["q"] for q in self.pool],
                                             rng=random.Random())
            by_question = {q["q"]: q for q in self.pool}
            self.session = [by_question[key] for key in keys[:count]]
            random.shuffle(self.session)
        else:
            self.session = random.sample(self.pool, count)
        self._begin()

    def _begin(self):
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
        self._update_pool()

    def jump_to_question(self, question_text):
        if self.mode_pills.get() != "uebung" and fp.load_running() is None:
            self.mode_pills.select_value("uebung")
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
#  KLAUSURSIMULATION (ab 0.51, wie am PC)
# ============================================================================

QUIZ_MODES = [("uebung", "Übung"), ("pruefung", "Prüfung")]
WISO_PAGE = 5


def points_text(value):
    return ("%.1f" % value).replace(".", ",").replace(",0", "")


def note_color(points):
    return C["green"] if points >= 67 else C["yellow"] if points >= 50 else C["red"]


def overall_controls(db):
    """Inhalt der Kachel "Gesamtergebnis" (wie overall_card am PC)."""
    scores = fp.latest_results(db.exams())
    projects = fpj.projects(db)
    active = fpj.active_project(db, fisi_update.load_settings()) if projects else None
    estimate = fpj.estimate(projects.get(active, {})) if active else None
    if estimate is not None:
        scores["projekt"] = estimate
    lines = ["%s (%d %%): %s" % (fp.AREA_NAME[area], fp.WEIGHTS[area],
                                 "%s Punkte" % points_text(scores[area]) if area in scores
                                 else "noch offen") for area in fp.WEIGHTS]
    controls = [ui.text("\n".join(lines), size=13, color=C["text_soft"])]
    result = fp.overall(scores)
    if not result["complete"]:
        hint = "Für das Gesamtergebnis fehlt noch: %s." % ", ".join(result["fehlend"])
        if "Projekt" in result["fehlend"]:
            hint += " Die Projektnote schätzt du im Abschlussprojekt unter „Übersicht“."
        controls.append(ui.text(hint, size=12, color=C["muted"]))
        return controls
    controls.append(ui.text("Gesamt %s Punkte · Note %s · %s" % (
        points_text(result["gesamt"]), result["note"],
        "bestanden" if result["bestanden"] else "nicht bestanden"), size=15,
        weight=ft.FontWeight.BOLD, color=C["green"] if result["bestanden"] else C["red"]))
    for text, ok in result["regeln"]:
        controls.append(ui.text(("erfüllt:  " if ok else "offen:  ") + text, size=12,
                                color=C["green"] if ok else C["red"]))
    if result["ergaenzung"]:
        controls.append(ui.text(result["ergaenzung"], size=12, color=C["yellow"]))
    return controls


class ExamPanel(ft.Column):
    """Pruefungsmodus im Pruefungstrainer: Auswahl, laufende Pruefung mit
    Countdown (ohne Pause), Selbstbewertung mit Kriterien, Ergebnis."""

    def __init__(self, app):
        super().__init__(spacing=14, tight=True)
        self.app = app
        self.db = app.db
        self.state = None
        self.task_no = 0
        self.wiso_page = 0
        self.result = None
        self.timer_token = 0
        self.dirty = False

    # -- Allgemein ----------------------------------------------------------

    def _stop_timer(self):
        self.timer_token += 1

    def show(self):
        """Beim Anzeigen: laufende Pruefung fortsetzen oder Auswahl zeigen."""
        self.state = fp.load_running()
        if self.state is None:
            self.show_choice()
        elif self.state["phase"] == "laeuft":
            if fp.seconds_left(self.state) <= 0:
                self._submit_now(auto=True)
            else:
                self.show_running()
        else:
            self.show_grading()

    def hide(self):
        self.save_answers()
        self._stop_timer()

    def save_answers(self):
        if self.dirty and self.state and self.state.get("phase") == "laeuft":
            fp.save_running(self.state)
        self.dirty = False

    # -- Auswahl ------------------------------------------------------------

    def show_choice(self):
        self._stop_timer()
        rows = []
        for exam in fp.EXAMS:
            detail = ("%d Minuten · %d Auswahlfragen · 100 Punkte" % (exam["minuten"],
                                                                      fp.WISO_COUNT)
                      if exam["art"] == fp.WISO else
                      "%d Minuten · 4 Aufgaben zu je 25 Punkten" % exam["minuten"])
            rows.append(ft.Container(
                content=ft.Column([
                    ui.text(exam["name"], size=15, weight=ft.FontWeight.BOLD),
                    ui.text(detail, size=12, color=C["muted"]),
                    ft.Row([ui.GradientButton("Starten",
                                              lambda _e, a=exam["art"]: self.start(a),
                                              height=40)]),
                ], spacing=6, tight=True),
                bgcolor=C["card_alt"], border_radius=12, border=ft.Border.all(1, C["border"]),
                padding=12))
        history = self.db.exams()
        past = []
        for entry in history[:8]:
            exam = fp.EXAM.get(entry["art"])
            past.append(ft.Row([
                ft.Column([ui.text(exam["kurz"] if exam else entry["art"], size=13,
                                   weight=ft.FontWeight.BOLD),
                           ui.text(german_time(entry["timestamp"]), size=11,
                                   color=C["muted"])], spacing=2, tight=True, expand=True),
                ft.Column([ui.text("%s Punkte" % points_text(entry["punkte"]), size=14,
                                   weight=ft.FontWeight.BOLD,
                                   color=note_color(entry["punkte"])),
                           ui.text(entry["note"], size=11, color=C["text_dim"])],
                          spacing=2, tight=True,
                          horizontal_alignment=ft.CrossAxisAlignment.END)]))
        if not past:
            past = [ui.text("Noch keine Prüfung abgelegt.", size=13, color=C["muted"])]
        self.controls = [
            ui.Card("Prüfung nach IHK-Vorbild", [
                ui.text("Wie in der echten Prüfung: feste Zeit ohne Pause, alle Aufgaben "
                        "sind Pflicht, keine Musterlösung während der Prüfung. Offene "
                        "Aufgaben bewertest du nach der Abgabe selbst anhand der "
                        "Musterlösung, WiSo wird automatisch ausgewertet. Notenschlüssel "
                        "der IHK: ab 92 Punkten sehr gut, ab 81 gut, ab 67 befriedigend, "
                        "ab 50 ausreichend, ab 30 mangelhaft.", size=13,
                        color=C["text_soft"]),
                *rows], accent=C["accent"], subtitle="Verordnung 2020"),
            ui.Card("Letzte Prüfungen", past, accent=C["purple"],
                    subtitle="%d insgesamt" % len(history)),
            ui.Card("Gesamtergebnis", overall_controls(self.db), accent=C["green"],
                    subtitle="Gewichtung 20 / 50 / 10 / 10 / 10 %"),
        ]

    def start(self, art):
        exam = fp.EXAM[art]

        def go():
            self.state = fp.new_exam(art, self.db.exams(), seed=random.randrange(1 << 30))
            fp.save_running(self.state)
            self.task_no = 0
            self.wiso_page = 0
            self.show_running()

        self.app.confirm("Prüfung starten",
                         "%s\n\nDie Zeit (%d Minuten) läuft sofort und lässt sich nicht "
                         "anhalten - auch nicht, wenn du die App schließt. Jetzt starten?"
                         % (exam["name"], exam["minuten"]), go)

    # -- Laufende Pruefung --------------------------------------------------

    def show_running(self):
        state = self.state
        exam = fp.EXAM[state["art"]]
        self.lbl_clock = ui.text("", size=34, weight=ft.FontWeight.BOLD, color=C["accent"])
        self.lbl_progress = ui.text("", size=12, color=C["muted"])
        head = ui.Card(exam["kurz"], [
            ft.Row([self.lbl_clock, ui.text("verbleibend", size=12, color=C["muted"])],
                   vertical_alignment=ft.CrossAxisAlignment.END),
            self.lbl_progress,
            ui.text(exam["name"], size=12, color=C["muted"]),
            ft.Row([ui.GradientButton("Abgeben", lambda _e: self._submit(), expand=True),
                    ui.GradientButton("Abbrechen", lambda _e: self.cancel(), kind="ghost",
                                      expand=True)], spacing=10),
        ], accent=C["accent"])
        self.task_box = ft.Column(spacing=14, tight=True)
        controls = [head]
        if state["art"] != fp.WISO:
            options = [(number, "Aufgabe %d" % (number + 1))
                       for number in range(len(state["aufgaben"]))]
            controls.append(ui.PillGroup(options, on_change=self._switch_task,
                                         initial=self.task_no))
        controls.append(self.task_box)
        self.controls = controls
        if state["art"] == fp.WISO:
            self._paint_wiso()
        else:
            self._paint_task()
        self._show_clock()
        self.timer_token += 1
        self.app.page.run_task(self._tick, self.timer_token)

    def _show_clock(self):
        left = fp.seconds_left(self.state)
        self.lbl_clock.value = fp.time_text(left)
        self.lbl_clock.color = C["red"] if left < 300 else C["accent"]
        return left

    async def _tick(self, token):
        while token == self.timer_token and self.state and \
                self.state.get("phase") == "laeuft":
            left = self._show_clock()
            if left <= 0:
                self._submit_now(auto=True)
                self.app.page.update()
                return
            self.save_answers()
            try:
                self.lbl_clock.update()
            except RuntimeError:
                pass   # Seite gerade nicht sichtbar - die Zeit laeuft weiter
            await asyncio.sleep(1)

    def _progress(self):
        answers = self.state["antworten"]
        if self.state["art"] == fp.WISO:
            done = sum(1 for q in self.state["fragen"] if answers.get(q))
            return "%d von %d Fragen beantwortet" % (done, len(self.state["fragen"]))
        total = sum(len(fp.task_details(self.state, n)["teile"])
                    for n in range(len(self.state["aufgaben"])))
        done = sum(1 for value in answers.values() if value.strip())
        return "%d von %d Teilaufgaben bearbeitet" % (done, total)

    def _switch_task(self, number):
        self.save_answers()
        self.task_no = number
        self._paint_task()

    def _paint_task(self):
        details = fp.task_details(self.state, self.task_no)
        controls = []
        if details["einleitung"]:
            controls.append(ui.text(details["einleitung"], size=14, color=C["text_soft"]))
        for part_no, part in enumerate(details["teile"]):
            key = fp.answer_key(self.task_no, part_no)
            controls.append(ui.text("%s) %s  (%d Punkte)" % (chr(97 + part_no), part["text"],
                                                             part["punkte"]),
                                    size=14, weight=ft.FontWeight.BOLD))
            controls.append(ui.entry(self.state["antworten"].get(key, ""),
                                     hint="Deine Antwort", multiline=True, min_lines=3,
                                     on_change=lambda e, k=key: self._answer(k, e)))
        # Lange Titel stehen im Inhalt - als Untertitel wuerden sie die
        # Ueberschrift der Karte zusammendruecken
        controls.insert(0, ui.text("%s · 25 Punkte" % details["titel"], size=12,
                                   color=C["muted"]))
        self.task_box.controls = [ui.Card("Aufgabe %d" % (self.task_no + 1), controls,
                                          accent=C["purple"])]
        self.lbl_progress.value = self._progress()

    def _answer(self, key, event):
        self.state["antworten"][key] = event.control.value or ""
        self.dirty = True   # gespeichert wird im Sekundentakt (siehe _tick)

    def _paint_wiso(self):
        questions = self.state["fragen"]
        pages = (len(questions) + WISO_PAGE - 1) // WISO_PAGE
        by_question = {q["q"]: q for q in QUIZ_QUESTIONS}
        start = self.wiso_page * WISO_PAGE
        controls = []
        for number, question in enumerate(questions[start:start + WISO_PAGE], start=start):
            controls.append(ui.text("%d. %s" % (number + 1, question), size=14,
                                    weight=ft.FontWeight.BOLD))
            options = ui.OptionList()
            options.set_options(self.state["optionen"].get(question) or
                                by_question[question]["options"])
            chosen = self.state["antworten"].get(question)
            if chosen:
                options.select(chosen)
            original = options.select

            def choose(value, q=question, select=original):
                select(value)
                self.state["antworten"][q] = value
                fp.save_running(self.state)
                self.lbl_progress.value = self._progress()
            options.select = choose
            controls.append(options)
        back = ui.GradientButton("Zurück", lambda _e: self._wiso_turn(-1), kind="ghost",
                                 expand=True)
        back.set_enabled(self.wiso_page > 0)
        forward = ui.GradientButton("Weiter", lambda _e: self._wiso_turn(1), kind="ghost",
                                    expand=True)
        forward.set_enabled(self.wiso_page < pages - 1)
        self.task_box.controls = [
            ui.Card("Wirtschafts- und Sozialkunde", controls, accent=C["purple"],
                    subtitle="Seite %d von %d" % (self.wiso_page + 1, pages)),
            ft.Row([back, forward], spacing=10)]
        self.lbl_progress.value = self._progress()

    def _wiso_turn(self, delta):
        self.wiso_page += delta
        self._paint_wiso()
        self.app.scroll_top()

    def cancel(self):
        def confirmed():
            self._stop_timer()
            fp.clear_running()
            self.state = None
            self.show_choice()

        self.app.confirm("Prüfung abbrechen", "Die Prüfung wirklich abbrechen? Deine "
                                              "Antworten werden verworfen und es gibt kein "
                                              "Ergebnis.", confirmed)

    def _submit(self):
        self.app.confirm("Abgeben", "Prüfung jetzt abgeben? Danach kannst du nichts mehr "
                                    "ändern.", self._submit_now)

    def _submit_now(self, auto=False):
        self._stop_timer()
        self.dirty = False
        fp.submit(self.state)
        if self.state["art"] == fp.WISO:
            self._finish_now()
            return
        fp.save_running(self.state)
        if auto:
            self.app.toast("Die Zeit ist um, die Prüfung wurde abgegeben. Jetzt folgt die "
                           "Bewertung.")
        self.task_no = 0
        self.show_grading()

    # -- Bewertung ----------------------------------------------------------

    def show_grading(self):
        state = self.state
        exam = fp.EXAM[state["art"]]
        self.lbl_sum = ui.text("", size=15, weight=ft.FontWeight.BOLD)
        options = [(number, "Aufgabe %d" % (number + 1))
                   for number in range(len(state["aufgaben"]))]
        self.task_box = ft.Column(spacing=14, tight=True)
        self.controls = [
            ui.Card("Bewertung", [
                ui.text(exam["name"], size=12, color=C["muted"]),
                ui.text("Vergleiche deine Antwort mit der Musterlösung und hake ab, was du "
                        "hattest. Die Punkte werden vorgeschlagen, du kannst sie wie ein "
                        "Prüfer anpassen.", size=13, color=C["text_soft"]),
                self.lbl_sum,
                ft.Row([ui.GradientButton("Bewertung abschließen", lambda _e: self._finish(),
                                          expand=True)]),
            ], accent=C["green"]),
            ui.PillGroup(options, on_change=self._grade_task, initial=self.task_no),
            self.task_box,
        ]
        self._paint_grading()

    def _grade_task(self, number):
        self.task_no = number
        self._paint_grading()

    def _sum_text(self):
        total = 0
        for number in range(len(self.state["aufgaben"])):
            for part_no, _part in enumerate(fp.task_details(self.state, number)["teile"]):
                total += int(self.state["punkte"].get(fp.answer_key(number, part_no), 0))
        return "Zwischenstand: %d von 100 Punkten" % total

    def _paint_grading(self):
        details = fp.task_details(self.state, self.task_no)
        controls = []
        for part_no, part in enumerate(details["teile"]):
            key = fp.answer_key(self.task_no, part_no)
            controls.append(ui.text("%s) %s  (%d Punkte)" % (chr(97 + part_no), part["text"],
                                                             part["punkte"]),
                                    size=14, weight=ft.FontWeight.BOLD))
            controls.append(ui.label("Deine Antwort"))
            controls.append(ui.read_box(self.state["antworten"].get(key, "") or
                                        "(keine Antwort)"))
            controls.append(ui.label("Musterlösung · Kriterien"))
            marks = self.state["kriterien"].setdefault(key, [False] * len(part["kriterien"]))
            stepper = ui.Stepper(int(self.state["punkte"].get(key, 0)), 0, part["punkte"], 1)
            original = stepper.change

            def stepped(delta, key=key, change=original, stepper=stepper):
                change(delta)
                self.state["punkte"][key] = stepper.get()
                fp.save_running(self.state)
                self.lbl_sum.value = self._sum_text()
            stepper.change = stepped

            def toggled(value, index, key=key, part=part, marks=marks, stepper=stepper):
                marks[index] = value
                points = fp.suggested_points(part["punkte"], marks)
                self.state["punkte"][key] = points
                stepper.value = points
                stepper.label.content.value = str(points)
                fp.save_running(self.state)
                self.lbl_sum.value = self._sum_text()

            for index, criterion in enumerate(part["kriterien"]):
                controls.append(ui.check_row(
                    criterion, marks[index] if index < len(marks) else False,
                    lambda value, i=index, t=toggled: t(value, i)))
            controls.append(ft.Row([ui.text("Punkte", size=13, color=C["text_dim"]), stepper,
                                    ui.text("von %d" % part["punkte"], size=13,
                                            color=C["muted"])], spacing=10,
                                   vertical_alignment=ft.CrossAxisAlignment.CENTER))
        controls.insert(0, ui.text("%s · %s" % (details["titel"], details["thema"]),
                                   size=12, color=C["muted"]))
        self.task_box.controls = [ui.Card("Aufgabe %d" % (self.task_no + 1), controls,
                                          accent=C["purple"])]
        self.lbl_sum.value = self._sum_text()

    def _finish(self):
        self.app.confirm("Bewertung abschließen", "Bewertung abschließen und das Ergebnis "
                                                  "speichern?", self._finish_now)

    def _finish_now(self):
        self.result = fp.finish(self.db, self.state)
        art = self.state["art"]
        self.state = None
        self.app.notify_progress()
        self.show_result(art)

    # -- Ergebnis -----------------------------------------------------------

    def show_result(self, art):
        result = self.result
        exam = fp.EXAM[art]
        details = result["daten"]
        lines = [ft.Row([ui.text("%s Punkte" % points_text(result["punkte"]), size=30,
                                 weight=ft.FontWeight.BOLD,
                                 color=note_color(result["punkte"]))]),
                 ui.text("IHK-Note %s  ·  Dauer %s" % (result["note"],
                                                      fp.time_text(result["dauer"])),
                         size=14, weight=ft.FontWeight.BOLD)]
        if art == fp.WISO:
            lines.append(ui.text("%d von %d Fragen richtig" % (
                details["richtig"], len(details["fragen"])), size=14, color=C["text_soft"]))
        else:
            for number, task in enumerate(details["aufgaben"], start=1):
                lines.append(ui.text("Aufgabe %d · %s: %d von %d Punkten" % (
                    number, task["titel"], task["punkte"], task["max"]), size=13,
                    color=C["text_soft"]))
        bars = []
        for name, (reached, maximum) in sorted(details["themen"].items()):
            share = reached / maximum * 100 if maximum else 0
            bar = ui.GradientBar(name, C["red"] if share < 50 else C["green"],
                                 C["orange"] if share < 50 else C["accent"])
            bar.set(share, "%s von %s" % (points_text(reached), points_text(maximum)))
            bars.append(bar)
        weak = fp.weak_topics(result)
        if weak:
            bars.append(ui.text("Üben: " + ", ".join(weak), size=13, color=C["red"],
                                weight=ft.FontWeight.BOLD))
        self.controls = [
            ui.Card("Ergebnis", [ui.text(exam["name"], size=12, color=C["muted"])] + lines,
                    accent=C["green"]),
            ui.Card("Nach Themen", bars, accent=C["purple"], subtitle="Schwachstellen rot"),
            ft.Row([ui.GradientButton("Zur Prüfungsauswahl", lambda _e: self.show_choice(),
                                      kind="ghost", expand=True)]),
        ]


# ============================================================================
#  SZENARIEN UND TESTPROJEKTE (Liste -> Detailseite)
# ============================================================================

class PagedListBox:
    """Liste mit Suchfeld, Filter-Pillen und Seiten (gleiche Logik wie am PC,
    siehe fisi_core.filter_positions). Es werden nie mehr als LIST_PAGE_SIZE
    Zeilen gleichzeitig angezeigt, egal wie viele Eintraege es gibt.
    on_select erhaelt die Position in der Gesamtliste."""

    def __init__(self, items, on_select, subtitle, status_source,
                 category_filter=False, group_field=None):
        self.items = items
        self.on_select = on_select
        self.subtitle = subtitle
        self.status_source = status_source
        self.group_field = group_field
        self.statuses = {}
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
            ft.IconButton(ft.Icons.CHEVRON_LEFT_ROUNDED, icon_color=C["accent"],
                          on_click=lambda _e: self.turn(-1)),
            self.lbl_page,
            ft.IconButton(ft.Icons.CHEVRON_RIGHT_ROUNDED, icon_color=C["accent"],
                          on_click=lambda _e: self.turn(1)),
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
        self.root = ft.Column(controls + [self.lbl_count, self.rows, pager],
                              spacing=10, tight=True)

    def _search(self, event):
        self.query = event.control.value or ""
        self.refresh()

    def refresh(self, keep_page=False):
        self.statuses = self.status_source()
        pills = self.pills
        self.filtered = filter_positions(
            self.items, query=self.query,
            category=pills["category"].get() if "category" in pills else FILTER_ALL,
            group_field=self.group_field,
            group=pills["group"].get() if "group" in pills else FILTER_ALL,
            status=pills["status"].get(), statuses=self.statuses)
        if not keep_page:
            self.page = 0
        self._paint()

    def _paint(self):
        visible, self.page, pages = page_slice(self.filtered, self.page)
        rows = []
        for pos in visible:
            status, level = self.statuses.get(pos, (Q_OPEN, ""))
            sub = self.subtitle(self.items[pos])
            if status != Q_OPEN:
                sub += "  ·  " + Q_STATUS_NAME[status]
            rows.append(ui.list_row(
                "%d. %s%s" % (pos + 1, self.items[pos]["title"],
                              " ✓" if status == Q_DONE else ""),
                sub, CATEGORY_COLOR[self.items[pos]["cat"]],
                lambda _e, p=pos: self.on_select(p),
                sub_color=status_color(level or status) if status != Q_OPEN else None))
        self.rows.controls = rows or [ui.text("Keine Treffer für diese Auswahl.",
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
        order = [p for p in self.filtered if p > position] + \
            [p for p in self.filtered if p <= position]
        # Ohne Status-Filter geht es bevorzugt mit Nicht-Abgeschlossenem weiter
        if self.pills["status"].get() == FILTER_ALL:
            for candidate in order:
                if candidate != position and \
                        self.statuses.get(candidate, (Q_OPEN, ""))[0] != Q_DONE:
                    return candidate
        return order[0]


class ScenarioScreen(Screen):
    """AP2-Szenarien: Liste, ein Tipp oeffnet die Aufgabe als eigene Seite."""

    crumbs = ("LERNEN", "AP2 SZENARIEN")
    DATA = SZENARIEN
    LIST_TITLE = "AP2-Szenarien"

    TABLE = "scenario_events"
    SOURCE = SRC_AP2

    def build(self):
        self.index = 0
        self.own_answers = {}
        self.pending = None      # aufgedeckt, noch nicht bewertet (ab 0.39)
        self.paged = PagedListBox(
            self.DATA, self.open_detail, subtitle=lambda item: item["theme"],
            status_source=lambda: position_statuses(StatusBook(self.db), self.SOURCE),
            group_field="theme")
        self.paged.refresh()
        return screen_list([ui.Card(self.LIST_TITLE, [self.paged.root],
                                    subtitle="%d Aufgaben" % len(self.DATA))])

    def on_show(self):
        self.paged.refresh(keep_page=True)

    def open_detail(self, position):
        self._flush()
        self.index = position
        self.solution_visible = False
        self.lbl_title = ui.text("", size=18, weight=ft.FontWeight.BOLD)
        self.lbl_theme = ui.text("", size=12, color=C["muted"])
        self.lbl_status = ui.text("", size=13, weight=ft.FontWeight.BOLD)
        self.rate_box = rate_row(self.rate)
        self.task_box = ui.read_box()
        self.txt_own = ui.entry(multiline=True, min_lines=4, max_lines=18,
                                hint="Deine Lösung ...", on_change=self._own_changed)
        self.solution_box = ui.read_box()
        self.btn_toggle = ui.GradientButton("Musterlösung anzeigen", self.toggle_solution,
                                            expand=True)
        content = screen_list([
            ft.Column([self.lbl_title, self.lbl_theme, self.lbl_status], spacing=2,
                      tight=True),
            ui.Card("Aufgabenstellung", [self.task_box], accent=C["accent"]),
            ui.Card("Deine Lösung", [
                ui.text("Löse die Aufgabe hier schriftlich, bevor du die Musterlösung "
                        "aufdeckst.", size=13, color=C["text_dim"]), self.txt_own],
                accent=C["purple"]),
            ui.Card("Musterlösung", [self.solution_box, self.rate_box], accent=C["green"]),
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
        self.rate_box.visible = False
        self._show_status()

    def _show_status(self):
        text, key = status_label(StatusBook(self.db), self.SOURCE, self.index)
        self.lbl_status.value = text
        self.lbl_status.color = status_color(key)

    def _flush(self):
        """Aufgedeckt, aber nicht bewertet: als angesehen speichern."""
        if self.pending is not None:
            position, self.pending = self.pending, None
            self._log(self.DATA[position], position, None)
            self.app.notify_progress()

    def rate(self, correct):
        """Selbsteinschaetzung "Gewusst" / "Nicht gewusst"."""
        position, self.pending = self.pending, None
        if position is None:
            return
        self.rate_box.visible = False
        self._log(self.DATA[position], position, correct)
        self.app.notify_progress()
        self.paged.refresh(keep_page=True)
        self._show_status()

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
            if self.pending is None:
                self.pending = self.index
                self.rate_box.visible = True

    def _log(self, item, position, correct):
        self.db.log_scenario(position, item["title"], item["theme"], correct)

    def next_item(self, _event=None):
        self._flush()
        self.index = self.paged.next_after(self.index)
        self._load()
        self.app.scroll_top()


class Ap1ScenarioScreen(ScenarioScreen):
    crumbs = ("LERNEN", "AP1 SZENARIEN")
    DATA = AP1_SZENARIEN
    LIST_TITLE = "AP1-Szenarien"
    TABLE = "ap1_events"
    SOURCE = SRC_AP1

    def _log(self, item, position, correct):
        self.db.log_ap1(position, item["title"], item["theme"], correct)


class ProjectScreen(Screen):
    crumbs = ("LERNEN", "TEST PROJEKT")

    def build(self):
        self.index = 0
        self.pending = None      # aufgedeckt, noch nicht bewertet (ab 0.39)
        self.paged = PagedListBox(
            PROJEKTARBEITEN, self.open_detail,
            subtitle=lambda item: "%s · %s" % (item["schwierigkeit"],
                                               CATEGORY_SHORT[item["cat"]]),
            status_source=lambda: position_statuses(StatusBook(self.db), SRC_PROJECT),
            category_filter=True, group_field="schwierigkeit")
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
        self._flush()
        self.index = position
        self.lbl_title = ui.text("", size=18, weight=ft.FontWeight.BOLD)
        self.lbl_meta = ui.text("", size=12, color=C["muted"])
        self.lbl_status = ui.text("", size=13, weight=ft.FontWeight.BOLD)
        self.rate_box = rate_row(self.rate)
        self.task_box = ui.read_box()
        self.hint_box = ui.read_box()
        self.btn_toggle = ui.GradientButton("Lösungsansätze anzeigen", self.toggle_hints,
                                            expand=True)
        content = screen_list([
            ft.Column([self.lbl_title, self.lbl_meta, self.lbl_status], spacing=2,
                      tight=True),
            ui.Card("Kundenauftrag", [self.task_box], accent=C["accent"]),
            ui.Card("Lösungsansätze", [self.hint_box, self.rate_box], accent=C["green"]),
            ft.Row([self.btn_toggle]),
            ft.Row([ui.GradientButton("Nächstes Projekt", self.next_item, kind="ghost",
                                      icon=ft.Icons.ARROW_FORWARD_ROUNDED, expand=True)]),
            # Ab 0.51: als Vorlage fuers eigene Abschlussprojekt
            ft.Row([ui.GradientButton("Als Vorlage fürs Abschlussprojekt",
                                      self.use_as_template, kind="ghost", expand=True)]),
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
        self.rate_box.visible = False
        self._show_status()

    def _show_status(self):
        text, key = status_label(StatusBook(self.db), SRC_PROJECT, self.index)
        self.lbl_status.value = text
        self.lbl_status.color = status_color(key)

    def _flush(self):
        """Aufgedeckt, aber nicht bewertet: als angesehen speichern."""
        if self.pending is not None:
            position, self.pending = self.pending, None
            project = PROJEKTARBEITEN[position]
            self.db.log_project(position, project["title"], project["cat"], None)
            self.app.notify_progress()

    def rate(self, correct):
        """Selbsteinschaetzung "Gewusst" / "Nicht gewusst"."""
        position, self.pending = self.pending, None
        if position is None:
            return
        self.rate_box.visible = False
        project = PROJEKTARBEITEN[position]
        self.db.log_project(position, project["title"], project["cat"], correct)
        self.app.notify_progress()
        self.on_show()
        self._show_status()

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
            if self.pending is None:
                self.pending = self.index
                self.rate_box.visible = True

    def next_item(self, _event=None):
        self._flush()
        self.index = self.paged.next_after(self.index)
        self._load()
        self.app.scroll_top()

    def use_as_template(self, _event=None):
        self.app.screens["abschluss"].use_template(self.index)
        self.app.open("abschluss")


# ============================================================================
#  ABSCHLUSSPROJEKT (AB 0.51, wie am PC)
# ============================================================================

PROJECT_SAVE_DELAY = 0.8      # Sekunden nach dem letzten Tippen
NO_CATEGORY = "Kein Fachbereich"


class FinalProjectScreen(Screen):
    """Arbeitsbereich fuers eigene IHK-Abschlussprojekt mit denselben Reitern
    wie am PC. Eingaben werden kurz nach dem Tippen gespeichert und mit dem
    PC abgeglichen. Die Reiter werden beim ersten Oeffnen aufgebaut und
    danach wiederverwendet."""

    crumbs = ("LERNEN", "ABSCHLUSSPROJEKT")

    def build(self):
        self.project = None
        self.fields = {}
        self.inputs = {}
        self.pending = set()
        self.save_round = 0
        self.derived = {}
        self.tab_boxes = {}
        self.tab = fpj.TABS[0][0]
        self.fg_index = 0
        self.fg_hint = False
        self.stamp = None
        self.project_ids = []
        self.menu_project = ft.Dropdown(
            options=[], expand=True, on_select=self._choose_project,
            bgcolor=C["card_alt"], filled=True, fill_color=C["card_alt"],
            border_color=C["border"], focused_border_color=C["purple"], border_radius=12,
            color=C["text"], text_style=ft.TextStyle(size=14, color=C["text"]))
        self.tab_pills = ui.PillGroup(fpj.TABS, on_change=self._on_tab)
        self.tab_area = ft.Column(spacing=14, tight=True)
        self._load_project()
        return screen_list([
            ui.Card("Projekt", [
                self.menu_project,
                ft.Row([ui.GradientButton("Neues Projekt", lambda _e: self._new_project(),
                                          kind="ghost", expand=True, height=40),
                        ui.GradientButton("Löschen", lambda _e: self._delete_project(),
                                          kind="ghost", expand=True, height=40)],
                       spacing=10),
                ft.Row([ui.GradientButton("Als PDF", lambda _e: self._export("pdf"),
                                          expand=True, height=40),
                        ui.GradientButton("Als Text", lambda _e: self._export("txt"),
                                          kind="ghost", expand=True, height=40)],
                       spacing=10),
            ], accent=C["accent"], subtitle="Dein IHK-Projekt vom Antrag bis zum "
                                            "Fachgespräch"),
            self.tab_pills, self.tab_area])

    # -- Projekte -----------------------------------------------------------

    def _load_project(self, project=None):
        self.flush()
        settings = fisi_update.load_settings()
        self.project = project or fpj.active_project(self.db, settings)
        if settings.get(fpj.ACTIVE_KEY) != self.project:
            settings[fpj.ACTIVE_KEY] = self.project
            fisi_update.save_settings(settings)
        self.fields = dict(fpj.projects(self.db).get(self.project, {}))
        self.stamp = self.db.change_stamp()
        self.fg_index = 0
        self._fill_project_menu()
        self.tab_boxes, self.inputs, self.derived = {}, {}, {}
        self._on_tab(self.tab)

    def _fill_project_menu(self):
        existing = fpj.projects(self.db)
        existing[self.project] = self.fields
        self.project_ids = sorted(existing, key=lambda key: fpj.project_title(
            existing[key]).lower())
        self.menu_project.options = [ft.dropdown.Option(key=key,
                                                        text=fpj.project_title(existing[key]))
                                     for key in self.project_ids]
        self.menu_project.value = self.project

    def _choose_project(self, event):
        key = event.control.value
        if key and key != self.project:
            self._load_project(key)

    def _new_project(self):
        self.flush()
        self._load_project(fpj.create_project(self.db))
        self.app.sync.schedule()

    def _delete_project(self):
        def confirmed():
            self.pending.clear()
            fpj.delete_project(self.db, self.project)
            settings = fisi_update.load_settings()
            settings.pop(fpj.ACTIVE_KEY, None)
            fisi_update.save_settings(settings)
            self.project = None
            self._load_project()
            self.app.sync.schedule()

        self.app.confirm("Projekt löschen",
                         "„%s“ mit allen Eingaben löschen? Das lässt sich nicht rückgängig "
                         "machen und gilt nach dem Abgleich auch am PC."
                         % fpj.project_title(self.fields), confirmed)

    def _export(self, extension):
        self.flush()
        if extension == "pdf":
            data, mime = fpj.export_pdf(self.fields), "application/pdf"
        else:
            data, mime = fpj.export_text(self.fields).encode("utf-8"), "text/plain"
        self.app.page.run_task(self.app.save_file, fpj.export_name(self.fields, extension),
                               data, mime)

    def use_template(self, position):
        self.flush()
        count = fpj.apply_template(self.db, self.project, position)
        self._load_project(self.project)
        self.toast("%d Felder aus dem Testprojekt übernommen" % count if count
                   else "Alle passenden Felder waren schon ausgefüllt")

    # -- Speichern ----------------------------------------------------------

    def _changed(self, field):
        self.pending.add(field)
        self.save_round += 1
        self.app.page.run_task(self._save_later, self.save_round)

    async def _save_later(self, round_no):
        await asyncio.sleep(PROJECT_SAVE_DELAY)
        if round_no == self.save_round:
            self.flush()
            try:
                self.app.page.update()
            except RuntimeError:
                pass

    def flush(self):
        """Geaenderte Felder speichern (auch beim Verlassen der App)."""
        if not self.pending or self.project is None:
            self.pending.clear()
            return
        fields, self.pending = self.pending, set()
        changed = title = False
        for field in fields:
            getter = self.inputs.get(field)
            if getter is None:
                continue
            value = getter()
            if value != self.fields.get(field, ""):
                self.db.save_project_field(self.project, field, value)
                self.fields[field] = value
                changed = True
                title = title or field == fpj.TITLE_FIELD
        if changed:
            self.stamp = self.db.change_stamp()
            if title:
                self._fill_project_menu()
            self._refresh_derived()
            self.app.sync.schedule()

    def _set(self, field, value):
        if self.fields.get(field, "") != value:
            self.db.save_project_field(self.project, field, value)
            self.fields[field] = value
            self.stamp = self.db.change_stamp()
            self._refresh_derived()
            self.app.sync.schedule()

    def _refresh_derived(self):
        for refresh in self.derived.values():
            refresh()

    def on_show(self):
        if self.pending:
            return
        if self.db.change_stamp() != self.stamp:
            fields = fpj.projects(self.db)
            if self.project not in fields or fields[self.project] != self.fields:
                self._load_project(self.project if self.project in fields else None)
            else:
                self.stamp = self.db.change_stamp()

    # -- Bausteine ----------------------------------------------------------

    def _entry(self, field, default="", hint=None, multiline=False, keyboard=None):
        box = ui.entry(self.fields.get(field, default), hint=hint, multiline=multiline,
                       min_lines=3 if multiline else 1, keyboard=keyboard,
                       on_change=lambda _e: self._changed(field))
        box.on_blur = lambda _e: self.flush()
        self.inputs[field] = lambda: (box.value or "").strip() if not multiline \
            else (box.value or "").rstrip()
        return box

    def _checklist(self, items):
        return [ui.check_row(text, fpj.checked(self.fields, key),
                             lambda value, k=key: self._set("check_" + k,
                                                            "1" if value else "0"))
                for key, text in items]

    @staticmethod
    def _field(caption, control):
        return ft.Column([ui.text(caption, size=13, color=C["text_dim"]), control],
                         spacing=4, tight=True,
                         horizontal_alignment=ft.CrossAxisAlignment.STRETCH)

    # -- Reiter -------------------------------------------------------------

    def _on_tab(self, tab):
        self.flush()
        self.tab = tab
        box = self.tab_boxes.get(tab)
        if box is None:
            box = self.tab_boxes[tab] = ft.Column(getattr(self, "_build_" + tab)(),
                                                  spacing=14, tight=True)
        self.tab_area.controls = [box]
        self.tab_pills.select_value(tab, notify=False)
        self._refresh_derived()

    def _build_uebersicht(self):
        rows = [self._field(label, self._entry(field)) for field, label, _m in
                fpj.OVERVIEW_FIELDS]
        category = ft.Dropdown(
            options=[ft.dropdown.Option(key=NO_CATEGORY, text=NO_CATEGORY)] +
            [ft.dropdown.Option(key=c, text=CATEGORY_SHORT[c]) for c in CATEGORIES],
            value=self.fields.get("fachbereich") or NO_CATEGORY, expand=True,
            on_select=lambda e: self._set_category(e.control.value),
            bgcolor=C["card_alt"], filled=True, fill_color=C["card_alt"],
            border_color=C["border"], border_radius=12, color=C["text"],
            text_style=ft.TextStyle(size=14, color=C["text"]))
        rows.append(self._field("Fachbereich (für das Fachgespräch)", ft.Row([category])))
        lbl_progress = ui.text("", size=15, weight=ft.FontWeight.BOLD)
        lbl_missing = ui.text("", size=12, color=C["muted"])

        template_cat = ui.PillGroup([(c, CATEGORY_SHORT[c]) for c in CATEGORIES],
                                    on_change=lambda c: fill(c))
        template_list = ft.Column(spacing=8, tight=True)

        def fill(category):
            template_list.controls = [
                ui.list_row(p["title"], "%s · %s" % (p["schwierigkeit"],
                                                     CATEGORY_SHORT[p["cat"]]),
                            CATEGORY_COLOR[p["cat"]],
                            lambda _e, pos=pos: self.use_template(pos))
                for pos, p in enumerate(PROJEKTARBEITEN) if p["cat"] == category]
        fill(CATEGORIES[0])

        def refresh():
            done, total = fpj.overview_progress(self.fields)
            lbl_progress.value = "%d von %d Schritten erledigt" % (done, total)
            missing = fpj.proposal_missing(self.fields)
            lbl_missing.value = ("Im Antrag noch offen: %s" % ", ".join(missing) if missing
                                 else "Alle Felder des Antrags sind ausgefüllt.")
        self.derived["uebersicht"] = refresh
        return [
            ui.Card("Eckdaten", rows, accent=C["accent"],
                    subtitle="Fristen und Seitenzahl legt deine IHK fest"),
            ui.Card("Stand", [lbl_progress, *self._checklist(fpj.CHECKLIST_OVERVIEW),
                              lbl_missing], accent=C["green"]),
            ui.Card("Geschätzte Projektnote", [
                ui.text("Die Projektarbeit zählt 50 % der Abschlussprüfung. Trage hier "
                        "ein, wie viele Punkte (0 bis 100) du für Dokumentation, "
                        "Präsentation und Fachgespräch zusammen erwartest.", size=12,
                        color=C["muted"]),
                self._field("Erwartete Punkte (0-100)",
                            self._entry(fpj.ESTIMATE_FIELD,
                                        keyboard=ft.KeyboardType.NUMBER)),
            ], accent=C["purple"], subtitle="Fließt ins Gesamtergebnis ein"),
            ui.Card("Testprojekt als Vorlage", [
                ui.text("Tippe ein Testprojekt an: Titel, Ausgangssituation, Auftrag und "
                        "Rahmenbedingungen werden übernommen. Ausgefüllte Felder bleiben "
                        "unverändert.", size=12, color=C["muted"]),
                template_cat, template_list,
            ], accent=C["orange"], subtitle="Füllt nur leere Felder"),
        ]

    def _set_category(self, value):
        self._set("fachbereich", "" if value == NO_CATEGORY else value)
        self.fg_index = 0
        self.tab_boxes.pop("fachgespraech", None)
        self.derived.pop("fachgespraech", None)

    def _build_antrag(self):
        controls = []
        for field, name, hint in fpj.PROPOSAL_FIELDS:
            controls += [ui.text(name, size=15, weight=ft.FontWeight.BOLD),
                         ui.text(hint, size=12, color=C["muted"]),
                         self._entry(field, multiline=True)]
        return [ui.Card("Projektantrag", controls, accent=C["accent"],
                        subtitle="Gliederung wie bei den IHK-Vorlagen"),
                ui.Card("Prüfe vor dem Einreichen", self._checklist(fpj.CHECKLIST_PROPOSAL),
                        accent=C["green"])]

    def _build_zeitplan(self):
        rows = []
        for key, name, default in fpj.PHASES:
            hours = self._entry("phase_" + key, str(default) if default else "",
                                keyboard=ft.KeyboardType.NUMBER)
            hours.width = 90
            if key.startswith("frei"):
                caption = self._entry("phase_name_" + key, hint="Weitere Phase")
                caption.expand = True
            else:
                caption = ui.text(name, size=13, color=C["text_dim"], expand=True)
            rows.append(ft.Row([caption, hours], spacing=10,
                               vertical_alignment=ft.CrossAxisAlignment.CENTER))
        lbl_sum = ui.text("", size=15, weight=ft.FontWeight.BOLD)
        lbl_warn = ui.text("", size=12, color=C["yellow"])

        def refresh():
            _rows, total = fpj.schedule(self.fields)
            lbl_sum.value = "Summe: %s von %d Stunden" % (fpj.hours_text(total),
                                                        fpj.MAX_HOURS)
            lbl_sum.color = C["red"] if total > fpj.MAX_HOURS else C["text"]
            lbl_warn.value = "\n".join(fpj.schedule_warnings(self.fields))
            lbl_warn.visible = bool(lbl_warn.value)
        self.derived["zeitplan"] = refresh
        return [ui.Card("Zeitplanung", rows + [lbl_sum, lbl_warn], accent=C["accent"],
                        subtitle="Höchstens %d Stunden inkl. Dokumentation" % fpj.MAX_HOURS)]

    def _build_kosten(self):
        rates = [self._field(label, self._entry("kosten_" + key, default,
                                                keyboard=ft.KeyboardType.NUMBER))
                 for key, label, default in fpj.COST_FIELDS]
        material = []
        for number in range(fpj.MATERIAL_ROWS):
            name = self._entry("material_name_%d" % number, hint="Bezeichnung")
            name.expand = True
            amount = self._entry("material_betrag_%d" % number, hint="€",
                                 keyboard=ft.KeyboardType.NUMBER)
            amount.width = 100
            material.append(ft.Row([name, amount], spacing=10))
        result = ui.read_box("")

        def refresh():
            result.content.value = "\n".join(fpj.cost_lines(self.fields))
        self.derived["kosten"] = refresh
        return [ui.Card("Kostenrechnung", rates, accent=C["accent"],
                        subtitle="Stunden kommen aus der Zeitplanung"),
                ui.Card("Sachkosten", material, accent=C["orange"],
                        subtitle="Hardware, Lizenzen, Material"),
                ui.Card("Ergebnis", [result], accent=C["green"])]

    def _build_doku(self):
        lbl_pages = ui.text("", size=15, weight=ft.FontWeight.BOLD)
        controls = [self._field("Seitenvorgabe deiner IHK",
                                self._entry(fpj.PAGES_FIELD, str(fpj.DEFAULT_PAGES),
                                            keyboard=ft.KeyboardType.NUMBER)),
                    lbl_pages,
                    ui.text("Grobe Schätzung: etwa %d Zeichen pro Seite (11 pt, "
                            "1,5-zeilig). Deckblatt, Verzeichnisse und Anhang zählen meist "
                            "nicht mit." % fpj.CHARS_PER_PAGE, size=12, color=C["muted"])]
        for key, title, hint in fpj.CHAPTERS:
            controls += [ui.text(title, size=15, weight=ft.FontWeight.BOLD),
                         ui.text(hint, size=12, color=C["muted"]),
                         self._entry("kapitel_" + key, multiline=True)]

        def refresh():
            pages, target = fpj.page_estimate(self.fields)
            lbl_pages.value = "Etwa %s von %d Seiten" % (("%.1f" % pages).replace(".", ","),
                                                         target)
            lbl_pages.color = C["red"] if pages > target else C["text"]
        self.derived["doku"] = refresh
        return [ui.Card("Dokumentation", controls, accent=C["accent"],
                        subtitle="Kapitelgerüst nach üblicher IHK-Gliederung")]

    def _build_fachgespraech(self):
        questions = fpj.questions_for(self.fields)
        lbl_stats = ui.text("", size=12, color=C["text_dim"])
        lbl_question = ui.text("", size=17, weight=ft.FontWeight.BOLD)
        lbl_status = ui.text("", size=13, weight=ft.FontWeight.BOLD)
        lbl_hint = ui.text("", size=14, color=C["text_soft"])
        btn_hint = ui.GradientButton("Hinweis zeigen", lambda _e: toggle(), expand=True)
        rating = rate_row(lambda known: rate(known))

        def paint():
            if not questions:
                return
            question = questions[self.fg_index % len(questions)]
            lbl_question.value = question["q"]
            value = fpj.question_rating(self.fields, question["id"])
            lbl_status.value = {True: "Gewusst", False: "Nicht gewusst"}.get(
                value, "Noch nicht bewertet")
            lbl_status.color = {True: C["green"], False: C["red"]}.get(value, C["muted"])
            lbl_hint.value = question["hinweis"] if self.fg_hint else ""
            lbl_hint.visible = self.fg_hint
            btn_hint.set_text("Hinweis ausblenden" if self.fg_hint else "Hinweis zeigen")
            rating.visible = self.fg_hint
            ratings = [fpj.question_rating(self.fields, q["id"]) for q in questions]
            lbl_stats.value = ("Frage %d von %d · %d gewusst · %d nicht gewusst · %d offen"
                               % (self.fg_index % len(questions) + 1, len(questions),
                                  ratings.count(True), ratings.count(False),
                                  ratings.count(None)))

        def toggle():
            self.fg_hint = not self.fg_hint
            paint()

        def turn(delta):
            self.fg_index = (self.fg_index + delta) % max(1, len(questions))
            self.fg_hint = False
            paint()

        def rate(known):
            question = questions[self.fg_index % len(questions)]
            self._set("fg_" + question["id"], "1" if known else "0")
            turn(1)

        self.derived["fachgespraech"] = paint
        return [
            ui.Card("Präsentation", self._checklist(fpj.CHECKLIST_PRESENTATION),
                    accent=C["accent"], subtitle="höchstens 15 Minuten"),
            ui.Card("Fachgespräch üben", [
                lbl_stats, lbl_question, lbl_status, lbl_hint,
                ft.Row([btn_hint]),
                ft.Row([ui.GradientButton("Nächste Frage", lambda _e: turn(1), kind="ghost",
                                          icon=ft.Icons.ARROW_FORWARD_ROUNDED,
                                          expand=True)]),
                rating,
            ], accent=C["purple"], subtitle="%d Fragen" % len(questions)),
        ]


# ============================================================================
#  NOTIZBLOCK (AB 0.39)
# ============================================================================

SOURCE_COLOR_KEY = {SRC_CARD: "accent", SRC_QUIZ: "purple", SRC_AP1: "blue",
                    SRC_AP2: "accent2", SRC_PROJECT: "orange"}
NOTEBOOK_PAGE = 10


class NotebookScreen(Screen):
    """Zentrale Uebersicht aller Fragen, die noch geuebt werden muessen -
    ueber Karteikarten, Pruefungstrainer, AP1, AP2 und Testprojekte hinweg."""

    crumbs = ("LERNEN", "NOTIZBLOCK")

    def build(self):
        self.page = 0
        self.entries = []
        self.opened = set()
        self.book = StatusBook(self.db)
        self.summary = ft.Column(spacing=8, tight=True)
        options = [(FILTER_ALL, "Alle")] + [(c, CATEGORY_SHORT[c]) for c in CATEGORIES]
        self.cat_pills = ui.PillGroup(options, on_change=self._on_category)
        self.source_pills = ui.PillGroup([(FILTER_ALL, "Alle")] +
                                         [(src, SOURCE_PLURAL[src]) for src in SOURCES],
                                         on_change=lambda _v: self.refresh())
        self.topic_pills = TopicPills(self.refresh)
        self.status_pills = ui.PillGroup([(Q_PRACTICE, "Zu üben"), (Q_DONE, "Abgeschlossen"),
                                          (Q_OPEN, "Offen")],
                                         on_change=lambda _v: self.refresh())
        self.answer_pills = ui.PillGroup([("aus", "Ausblenden"), ("an", "Einblenden")],
                                         on_change=self._toggle_all)
        self.practice_row = ft.Column(spacing=8, tight=True)
        self.rows = ft.Column(spacing=8, tight=True)
        self.list_card = ui.Card("Zu üben", [self.rows], accent=C["red"])
        self.lbl_page = ui.text("", size=13, color=C["text_dim"])
        pager = ft.Row([
            ft.IconButton(ft.Icons.CHEVRON_LEFT_ROUNDED, icon_color=C["accent"],
                          on_click=lambda _e: self.turn(-1)),
            self.lbl_page,
            ft.IconButton(ft.Icons.CHEVRON_RIGHT_ROUNDED, icon_color=C["accent"],
                          on_click=lambda _e: self.turn(1)),
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
        root = screen_list([
            ui.Card("Lernstand je Bereich", [self.summary], accent=C["accent"],
                    subtitle="Abgeschlossen = 2x hintereinander richtig"),
            ui.Card(None, [ui.label("Fachbereich"), self.cat_pills,
                           ui.label("Bereich"), self.source_pills,
                           ui.label("Thema"), self.topic_pills.root,
                           ui.label("Status"), self.status_pills,
                           ui.label("Musterantworten"), self.answer_pills]),
            self.practice_row, self.list_card, pager,
        ])
        self.refresh()
        return root

    def on_show(self):
        self.refresh(keep_page=True)

    def _on_category(self, category):
        self.topic_pills.set_category(category)
        self.refresh()

    def _toggle_all(self, value):
        self.opened = {(e["source"], e["key"]) for e in self.entries} if value == "an" \
            else set()
        self._paint()

    def refresh(self, keep_page=False):
        self.book = StatusBook(self.db)
        category = self.cat_pills.get()
        topic = self.topic_pills.get()
        source = self.source_pills.get()
        self.entries = notebook_entries(
            self.book, status=self.status_pills.get(), category=category, topic=topic,
            sources=None if source == FILTER_ALL else [source])
        if self.answer_pills.get() == "an":
            self.opened = {(e["source"], e["key"]) for e in self.entries}
        if not keep_page:
            self.page = 0
        summary = notebook_summary(self.book, category, topic)
        bars = []
        for src in SOURCES:
            counts = summary[src]
            total = sum(counts.values()) or 1
            bar = ui.GradientBar("%s · %d zu üben" % (SOURCE_PLURAL[src], counts[Q_PRACTICE]),
                                 C["green"], C["accent"])
            bar.set(100.0 * counts[Q_DONE] / total, "%d / %d" % (counts[Q_DONE], total))
            bars.append(bar)
        self.summary.controls = bars
        cards = self._practice_keys(SRC_CARD)
        quiz = self._practice_keys(SRC_QUIZ)
        label = {Q_PRACTICE: "üben", Q_DONE: "wiederholen", Q_OPEN: "lernen"}[
            self.status_pills.get()]
        self.practice_row.controls = [
            ft.Row([ui.GradientButton("%d Karteikarten %s" % (len(cards), label),
                                      lambda _e: self.practice(SRC_CARD, cards), expand=True)]),
            ft.Row([ui.GradientButton("%d Quizfragen %s" % (len(quiz), label),
                                      lambda _e: self.practice(SRC_QUIZ, quiz), kind="accent",
                                      expand=True)]),
            ui.text("Startet eine Übungsrunde nur mit den Fragen der Liste (Quiz: höchstens "
                    "50).", size=12, color=C["muted"]),
        ]
        self._paint()

    def _practice_keys(self, source):
        return [e["key"] for e in self.entries if e["source"] == source]

    def practice(self, source, keys, first=None):
        if not keys:
            self.toast("In dieser Auswahl gibt es dazu keine Fragen.")
            return
        if first is not None:
            keys = [first] + [key for key in keys if key != first]
        if source == SRC_CARD:
            self.app.screens["cards"].practice(keys)
            self.app.open("cards")
        elif source == SRC_QUIZ:
            self.app.screens["quiz"].practice(keys, keep_order=first is not None)
            self.app.open("quiz")
        elif source == SRC_PROJECT:
            self.app.screens["testproject"].open_detail(keys[0])
        else:
            key = "ap1scenarios" if source == SRC_AP1 else "scenarios"
            self.app.screens[key].open_detail(keys[0])

    def _paint(self):
        status = self.status_pills.get()
        self.list_card.set_title(Q_STATUS_NAME[status],
                                 status_color(LEVEL_RED if status == Q_PRACTICE else status))
        self.list_card.set_subtitle("%d Fragen" % len(self.entries))
        visible, self.page, pages = page_slice(self.entries, self.page, NOTEBOOK_PAGE)
        rows = [self._row(entry) for entry in visible]
        if not rows:
            rows = [ui.text("Nichts zu üben - sehr gut! Falsch beantwortete Fragen landen "
                            "automatisch hier." if status == Q_PRACTICE else
                            "Keine Fragen in dieser Auswahl.", size=14,
                            color=C["text_soft"])]
        self.rows.controls = rows
        self.lbl_page.value = "Seite %d / %d" % (self.page + 1, pages)

    def _row(self, entry):
        source, item = entry["source"], entry["item"]
        color = status_color(entry["level"] or entry["status"])
        text, _key = status_label(self.book, source, entry["key"])
        topic = TOPIC_SHORT.get(item.get("thema"), "")
        title = entry["title"]
        if source in (SRC_AP1, SRC_AP2, SRC_PROJECT):
            title = "%d. %s" % (entry["key"] + 1, title)
        key = (source, entry["key"])
        controls = [
            ui.text("%s · %s%s" % (SOURCE_NAME[source], CATEGORY_SHORT[item["cat"]],
                                   " · " + topic if topic else ""), size=11,
                    color=C["muted"]),
            ui.text(title, size=14, weight=ft.FontWeight.BOLD),
            ui.text(text, size=12, color=color, weight=ft.FontWeight.BOLD),
        ]
        if key in self.opened:
            answer = model_answer(source, item)
            if len(answer) > 900:
                answer = answer[:900].rsplit(" ", 1)[0] + " …"
            controls.append(ui.text(answer, size=13, color=C["text_dim"], selectable=True))
        controls.append(ft.Row([
            ui.GradientButton("Antwort ausblenden" if key in self.opened else "Antwort zeigen",
                              lambda _e, k=key: self._toggle(k), kind="ghost", height=36,
                              expand=True),
            ui.GradientButton("Jetzt üben", lambda _e, e=entry: self.practice(
                e["source"], self._practice_keys(e["source"]), first=e["key"]),
                kind="accent", height=36, expand=True),
        ], spacing=8))
        return ft.Container(
            content=ft.Row([
                ft.Container(width=4, height=60, border_radius=2, bgcolor=color),
                ft.Column(controls, spacing=4, tight=True, expand=True),
            ], spacing=12, vertical_alignment=ft.CrossAxisAlignment.START),
            bgcolor=C["card_alt"], border=ft.Border.all(1, C["border"]), border_radius=12,
            padding=ft.Padding.symmetric(horizontal=12, vertical=10))

    def _toggle(self, key):
        if key in self.opened:
            self.opened.discard(key)
        else:
            self.opened.add(key)
        self._paint()

    def turn(self, delta):
        self.page += delta
        self._paint()
        self.app.scroll_top()


# ============================================================================
#  PRAXIS-RECHNER
# ============================================================================

class TrainerPanel(ft.Column):
    """Subnetting-Trainer im Rechner (ab 0.51), wie am PC."""

    def __init__(self, app):
        self.app = app
        self.db = app.db
        self.tasks, self.index, self.results, self.checked = [], 0, [], False
        self.kind_pills = ui.PillGroup(TRAINER_KINDS)
        self.level_pills = ui.PillGroup(TRAINER_LEVELS)
        self.lbl_stats = ui.text("", size=12, color=C["muted"])
        self.lbl_head = ui.text("", size=12, color=C["muted"])
        self.lbl_task = ui.text("Wähle Aufgabenart und Schwierigkeit und starte eine Runde "
                                "mit %d Aufgaben." % TRAINER_ROUND, size=16,
                                color=C["text_soft"], weight=ft.FontWeight.BOLD)
        self.fields_box = ft.Column(spacing=10, tight=True)
        self.lbl_feedback = ui.text("", size=14, weight=ft.FontWeight.BOLD)
        self.steps = ui.read_box("", mono=True)
        self.steps.visible = False
        self.btn_check = ui.GradientButton("Prüfen", lambda _e: self.check())
        self.btn_check.visible = False
        self.lbl_counter = ui.text("", size=12, color=C["muted"])
        self.entries, self.marks = {}, {}
        super().__init__([
            ui.Card("Subnetting-Trainer", [
                ui.label("Aufgabenart"), self.kind_pills,
                ui.label("Schwierigkeit"), self.level_pills,
                ft.Row([ui.GradientButton("Runde starten", lambda _e: self.start_round())]),
                self.lbl_stats,
            ], accent=C["accent"], subtitle="Zufallsaufgaben mit Selbstkontrolle"),
            ui.Card("Aufgabe", [self.lbl_head, self.lbl_task, self.fields_box,
                                self.lbl_feedback, self.steps,
                                ft.Row([self.btn_check, self.lbl_counter],
                                       vertical_alignment=ft.CrossAxisAlignment.CENTER)],
                    accent=C["purple"], spacing=12),
        ], spacing=14, tight=True)
        self.show_stats()

    def show_stats(self):
        stats = self.db.trainer_stats()
        count = sum(total for total, _right in stats.values())
        right = sum(right for _total, right in stats.values())
        self.lbl_stats.value = ("bisher %d Aufgaben, %d richtig" % (count, right)
                                if count else "")

    def start_round(self):
        self.tasks = trainer_round(self.kind_pills.get(), self.level_pills.get(),
                                   random.randrange(1 << 30))
        self.index, self.results = 0, []
        self.load_task()

    def load_task(self):
        task = self.tasks[self.index]
        self.checked = False
        self.lbl_head.value = "%s · %s" % (TRAINER_KIND_NAME[task.kind],
                                           TRAINER_LEVEL_NAME[task.level])
        self.lbl_task.value = task.text
        self.entries, self.marks, rows = {}, {}, []
        for key, label in task.fields:
            field = ui.entry("", hint=label,
                             keyboard=ft.KeyboardType.TEXT if task.kind in ("ipv6", "zahlen")
                             else ft.KeyboardType.NUMBER if key == "hosts"
                             else ft.KeyboardType.TEXT)
            mark = ui.text("", size=12)
            mark.visible = False
            self.entries[key], self.marks[key] = field, mark
            rows.append(ft.Column([ui.text(label, size=13, color=C["text_dim"]), field, mark],
                                  spacing=4, tight=True))
        self.fields_box.controls = rows
        self.lbl_feedback.value = ""
        self.steps.visible = False
        self.btn_check.set_text("Prüfen")
        self.btn_check.visible = True
        self.lbl_counter.value = "Aufgabe %d / %d" % (self.index + 1, len(self.tasks))

    def check(self):
        if not self.tasks:
            return
        if self.checked:
            self.advance()
            return
        task = self.tasks[self.index]
        result = task.check({key: field.value or "" for key, field in self.entries.items()})
        for key, ok in result.items():
            mark = self.marks[key]
            mark.value = "richtig" if ok else "richtig wäre: %s" % task.solution[key]
            mark.color = C["green"] if ok else C["red"]
            mark.visible = True
        correct = all(result.values())
        self.results.append(correct)
        self.db.log_trainer(task.kind, task.level, correct)
        self.app.sync.schedule()
        self.lbl_feedback.value = ("Alles richtig." if correct else
                                   "Noch nicht ganz - hier der Rechenweg:")
        self.lbl_feedback.color = C["green"] if correct else C["yellow"]
        self.steps.content.value = "\n".join(task.steps)
        self.steps.visible = True
        self.checked = True
        last = self.index >= len(self.tasks) - 1
        self.btn_check.set_text("Auswertung" if last else "Nächste Aufgabe")

    def advance(self):
        if self.index < len(self.tasks) - 1:
            self.index += 1
            self.load_task()
            return
        self.lbl_task.value = "Runde beendet: %s." % trainer_summary(self.results)
        self.tasks = []
        self.fields_box.controls = []
        self.steps.visible = False
        self.lbl_feedback.value = ""
        self.btn_check.visible = False
        self.lbl_counter.value = ""
        self.show_stats()


CALC_TABS = [("rechner", "Rechner"), ("trainer", "Trainer")]


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
        ], accent=C["accent"], subtitle="IPv4 und IPv6")

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
        # Ab 0.51: Umschalter Rechner / Trainer
        self.calc_box = ft.Column([subnet, raid, screen], spacing=14, tight=True)
        self.trainer = TrainerPanel(self.app)
        self.trainer.visible = False
        return screen_list([ui.PillGroup(CALC_TABS, on_change=self._on_tab),
                            self.calc_box, self.trainer])

    def _on_tab(self, value):
        self.trainer.visible = value == "trainer"
        self.calc_box.visible = not self.trainer.visible

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
        self.exam_list = ft.Column(spacing=8, tight=True)
        return screen_list([
            ft.Row([stat("tests", "Sessions", C["accent"]),
                    stat("avg", "Durchschnitt", C["purple"])], spacing=12),
            ft.Row([stat("best", "Bestes", C["accent2"]),
                    stat("streak", "Lernserie", C["green"])], spacing=12),
            ui.Card("Ergebnisse im Zeitverlauf", [self.chart],
                    subtitle="Erfolgsquote je Session"),
            ui.Card("Historie der Prüfungssessions", [self.history], accent=C["purple"]),
            ui.Card("Prüfungen (Klausursimulation)", [self.exam_list], accent=C["green"]),
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
        self.chart.set_data(labels, values, C["accent2"], y_max=100)

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
                        ui.text("%.1f %%" % percentage, size=15, color=C["accent"],
                                weight=ft.FontWeight.BOLD),
                        ui.text(note, size=11, color=C["text_dim"]),
                    ], spacing=2, tight=True,
                        horizontal_alignment=ft.CrossAxisAlignment.END),
                ]),
                bgcolor=C["card_alt"], border_radius=10,
                padding=ft.Padding.symmetric(horizontal=12, vertical=10)))

        # Ab 0.51: Pruefungen aus dem Pruefungsmodus
        exams = self.db.exams()
        self.exam_list.controls = [ft.Container(
            content=ft.Row([
                ft.Column([
                    ui.text(fp.EXAM[entry["art"]]["kurz"] if entry["art"] in fp.EXAM
                            else entry["art"], size=13, weight=ft.FontWeight.BOLD),
                    ui.text("%s  ·  %s min" % (german_time(entry["timestamp"]),
                                               entry["dauer"] // 60),
                            size=12, color=C["muted"]),
                ], spacing=2, tight=True, expand=True),
                ft.Column([
                    ui.text("%s Punkte" % points_text(entry["punkte"]), size=15,
                            color=note_color(entry["punkte"]), weight=ft.FontWeight.BOLD),
                    ui.text(entry["note"], size=11, color=C["text_dim"]),
                ], spacing=2, tight=True, horizontal_alignment=ft.CrossAxisAlignment.END),
            ]),
            bgcolor=C["card_alt"], border_radius=10,
            padding=ft.Padding.symmetric(horizontal=12, vertical=10))
            for entry in exams[:50]] or [ui.text("Noch keine Prüfung abgelegt. Den "
                                                 "Prüfungsmodus findest du im "
                                                 "Prüfungstrainer.", size=13,
                                                 color=C["muted"])]

    def _stat(self, key, value, sub):
        self.stats[key][0].value = value
        self.stats[key][1].value = sub

    def clear_history(self, _event=None):
        def confirmed():
            if self.db.clear_history():
                self.on_show()
                self.app.notify_progress()

        self.app.confirm("Historie löschen",
                         "Wirklich alle gespeicherten Testergebnisse und Prüfungen "
                         "löschen? Die Lern-Ereignisse für das Dashboard bleiben erhalten.", confirmed)


# ============================================================================
#  EINSTELLUNGEN
# ============================================================================

class SettingsScreen(Screen):
    crumbs = ("SYSTEM", "OPTIONEN")

    def build(self):
        # Ab 0.47: Schwierigkeitsgrad des laufenden Spielstands (nur Anzeige)
        self.lbl_difficulty = ui.text("", size=14, color=C["text_soft"],
                                      weight=ft.FontWeight.BOLD)
        self.lbl_reset = ui.text("", size=13, color=C["text_dim"])
        self.btn_update = ui.GradientButton("Nach Updates suchen", self.check_updates)
        self.lbl_update = ui.text("", size=13, color=C["text_dim"])
        self.lbl_update.visible = False
        auto = fisi_update.load_settings()["auto_check"]
        updates = ui.Card("Updates", [
            ft.Row([self.btn_update]), self.lbl_update,
            self._switch("Beim Start automatisch nach Updates suchen", auto,
                         self._toggle_auto),
        ], accent=C["accent2"], subtitle="installierte Version %s" % APP_VERSION)

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
        ], accent=C["accent"], subtitle="privates GitHub-Repository")
        self.show_sync_status(None, None)

        # Sicherung als Datei (fisi_sicherung.py), Texte wie am PC
        backup = ui.Card(fsi.TITLE, [
            ui.text(fsi.HELP, size=13, color=C["text_dim"]),
            ft.Row([ui.GradientButton(fsi.BTN_CREATE, self.create_backup)]),
            ft.Row([ui.GradientButton(fsi.BTN_RESTORE, self.restore_backup, kind="ghost")]),
        ], accent=C["accent2"], subtitle=fsi.SUBTITLE)

        totals = content_totals()
        lines = ["Karteikarten gesamt: %d" % len(KARTEIKARTEN),
                 "Quizfragen gesamt: %d" % len(QUIZ_QUESTIONS),
                 "AP1-Szenarien gesamt: %d" % len(AP1_SZENARIEN),
                 "AP2-Szenarien gesamt: %d" % len(SZENARIEN),
                 "Testprojekte gesamt: %d" % len(PROJEKTARBEITEN), ""]
        lines += ["%s: %d Inhalte" % (CATEGORY_SHORT[c], totals.get(c, 0)) for c in CATEGORIES]

        colors = ui.Card("Farben", [
            ui.label("Darstellung"),
            ui.PillGroup(fisi_theme.MODES, initial=fisi_theme.MODE_IDS.index(
                fisi_theme.current_mode), on_change=self._change_mode),
            ui.label("Grundfarbe"),
            ft.Row([self._color_tile(item) for item in fisi_theme.PRESETS],
                   wrap=True, spacing=10, run_spacing=10),
            ui.label("Hintergrund"),
            ft.Row([self._background_tile(item) for item in fisi_theme.BACKGROUNDS],
                   wrap=True, spacing=10, run_spacing=10),
            ui.text("Die Grundfarbe ändert Buttons, Ringe, Balken und Banner, der Hintergrund "
                    "die Flächen und Karten. Die Farben der Fachbereiche und von Erfolg, "
                    "Fehler und Warnung bleiben gleich (in der hellen Darstellung etwas "
                    "dunkler, damit sie gut lesbar sind).",
                    size=11, color=C["muted"]),
        ], accent=C["accent"], subtitle="nur für dieses Gerät")

        # Ab 0.51: Tagesziel, Lernserie, Erinnerung (je Geraet)
        values = learning_settings()
        self.goal_stepper = ui.Stepper(values["ziel_anzahl"], GOAL_MIN, GOAL_MAX, GOAL_STEP)
        original_change = self.goal_stepper.change

        def stepped(delta):
            original_change(delta)
            save_learning_settings(ziel_anzahl=self.goal_stepper.get())
        self.goal_stepper.change = stepped
        self.entry_reminder = ui.entry(values["erinnerung_zeit"], hint="18:00",
                                       keyboard=ft.KeyboardType.DATETIME,
                                       on_change=self._reminder_changed)
        self.goal_rows = {
            "ziel_an": self._switch("Tagesziel anzeigen", values["ziel_an"],
                                    lambda e: save_learning_settings(
                                        ziel_an=bool(e.control.value))),
            "serie_an": self._switch("Lernserie anzeigen", values["serie_an"],
                                     lambda e: save_learning_settings(
                                         serie_an=bool(e.control.value))),
            "erinnerung_an": self._switch("An das Tagesziel erinnern",
                                          values["erinnerung_an"],
                                          lambda e: save_learning_settings(
                                              erinnerung_an=bool(e.control.value))),
        }
        goal = ui.Card("Tagesziel", [
            self.goal_rows["ziel_an"], self.goal_rows["serie_an"],
            self.goal_rows["erinnerung_an"],
            ft.Row([ui.text("Aufgaben pro Tag", size=13, color=C["text_dim"], expand=True),
                    self.goal_stepper]),
            ft.Row([ui.text("Erinnerung um", size=13, color=C["text_dim"], expand=True),
                    ft.Container(content=self.entry_reminder, width=110)]),
            ui.text("Gezählt werden bewertete Karteikarten, Prüfungstrainer-Fragen, "
                    "Szenarien, Testprojekte und Trainer-Aufgaben. Die Erinnerung erscheint "
                    "als Hinweis, wenn du die App öffnest oder zurückholst.",
                    size=11, color=C["muted"]),
        ], accent=C["green"], subtitle="nur für dieses Gerät")

        return screen_list([
            updates, colors, goal, sync, backup,
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
                self.lbl_difficulty,
                ui.label("Wohnungen"),
                ui.PillGroup(fisi_game.RENT_CHOICES, initial=1 if fisi_game.rent_mode() else 0,
                             on_change=lambda key: fisi_game.set_rent_mode(key == "miete")),
                ui.text(fisi_game.RENT_HELP
                        % round(fisi_game.GAME["balancing"]["miete"]["kaution_anteil"] * 100),
                        size=11, color=C["muted"]),
                ft.Container(height=6),
                self.lbl_reset,
                ft.Row([ui.GradientButton("Spielstand zurücksetzen", self.reset_game,
                                          kind="danger")]),
                ft.Container(height=6),
                ui.text(fisi_game.RECORDS_HELP, size=13, color=C["text_dim"]),
                ft.Row([ui.GradientButton("Bestenliste löschen", self.reset_records,
                                          kind="danger")]),
            ], accent=C["accent2"]),
            ui.Card("Über das Programm", [ui.text(
                "%s Version %s\n\nLernprogramm für die Umschulung zum Fachinformatiker "
                "Systemintegration mit Karteikarten, Prüfungstrainer, AP1-/AP2-Szenarien, "
                "Testprojekten und Praxis-Rechnern.\n\nDie Handy-App nutzt dieselben "
                "Lerninhalte wie die PC-Version und ist mit Python und Flet umgesetzt."
                % (APP_TITLE, APP_VERSION), size=14, color=C["text_dim"])],
                accent=C["green"]),
        ])

    def _color_tile(self, item):
        """Kachel einer Grundfarbe (wie am PC): Verlauf, Akzentpunkte, Name."""
        active = item["id"] == fisi_theme.current_preset
        return ft.Container(
            content=ft.Column([
                ft.Container(height=12, width=84, border_radius=6,
                             gradient=ui.gradient(item["primary"])),
                ft.Row([ui.dot(item["accent"], 10), ui.dot(item["accent2"], 10)],
                       spacing=6, alignment=ft.MainAxisAlignment.CENTER),
                ui.text(item["name"], size=12, weight=ft.FontWeight.BOLD,
                        color=C["text"] if active else C["text_dim"]),
            ], spacing=8, tight=True, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            width=104, padding=10, border_radius=12, ink=True,
            bgcolor=C["card_hi"] if active else C["card_alt"],
            border=ft.Border.all(2, item["accent"] if active else C["border"]),
            on_click=lambda _e, key=item["id"]: self._change_color(key))

    def _background_tile(self, item):
        """Kachel eines Hintergrunds (wie am PC): Flaeche mit kleiner Karte."""
        active = item["id"] == fisi_theme.current_background
        if fisi_theme.light:
            item = fisi_theme.light_background(item["id"])   # ab 0.49
        return ft.Container(
            content=ft.Column([
                ft.Container(content=ui.dot(C["accent"], 10), width=84, height=28,
                             bgcolor=item["card"], border_radius=8,
                             border=ft.Border.all(1, item["border"]),
                             padding=ft.Padding.only(left=10),
                             alignment=ft.Alignment.CENTER_LEFT),
                ft.Text(item["name"], size=12, weight=ft.FontWeight.BOLD,
                        color=C["text"] if active else item["text_dim"]),
            ], spacing=8, tight=True, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            width=104, padding=10, border_radius=12, ink=True, bgcolor=item["bg"],
            border=ft.Border.all(2, C["accent"] if active else item["border_hi"]),
            on_click=lambda _e, key=item["id"]: self._change_background(key))

    def _change_color(self, preset_id):
        if preset_id != fisi_theme.current_preset:
            self.app.change_color(preset_id=preset_id)

    def _change_background(self, background_id):
        if background_id != fisi_theme.current_background:
            self.app.change_color(background_id=background_id)

    def _change_mode(self, mode):
        if mode != fisi_theme.current_mode:
            self.app.change_color(mode=mode)

    @staticmethod
    def _switch(caption, value, handler):
        # Ab 0.48 mit Beschriftung fuer Screenreader (sonst nur "Schalter")
        return ft.Row([
            ft.Semantics(label=caption, content=ft.Switch(
                value=value, on_change=handler, active_color=C["knob"],
                active_track_color=C["violet"], inactive_track_color=C["card_alt"],
                inactive_thumb_color=C["muted"])),
            ui.text(caption, size=13, color=C["text_dim"], expand=True),
        ], spacing=8)

    @staticmethod
    def _reminder_changed(event):
        value = parse_time(event.control.value or "")
        if value is not None:
            save_learning_settings(erinnerung_zeit=value)

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
            self.lbl_update.color = C["accent"]

    def on_show(self):
        self._show_difficulty()

    def _show_difficulty(self):
        try:
            game = self.app.screens["game"].game
            game.reload()
        except (KeyError, AttributeError):
            return
        self.lbl_difficulty.value = fisi_game.slot_options_text(game)
        self.lbl_reset.value = fisi_game.reset_help(game)

    def reset_game(self, _event=None):
        game = self.app.screens["game"].game
        game.reload()

        def confirmed():
            if game.reset():
                self.toast("Der Spielstand wurde zurückgesetzt.", C["green"])
                self.app.screens["game"].room = None
                self.app.notify_progress()
                self._show_difficulty()

        self.app.confirm("Spielstand zurücksetzen", fisi_game.reset_question(game),
                         confirmed)

    def reset_records(self, _event=None):
        def confirmed():
            if self.app.screens["game"].game.reset_records():
                self.toast("Die Bestenliste wurde gelöscht.", C["green"])
                self.app.notify_progress()

        self.app.confirm("Bestenliste löschen", fisi_game.RECORDS_ASK, confirmed)

    # -- Sicherung ------------------------------------------------------------

    def _flush_inputs(self):
        """Offene Eingaben (Pruefung, Abschlussprojekt) vorher speichern."""
        self.app.screens["quiz"].exam.save_answers()
        self.app.screens["abschluss"].flush()

    def create_backup(self, _event=None):
        self._flush_inputs()
        data = fsi.create_backup(self.db, APP_VERSION, "Handy")
        self.app.page.run_task(self.app.save_file, fsi.default_name(), data,
                               "application/octet-stream")

    def restore_backup(self, _event=None):
        self.app.page.run_task(self._pick_backup)

    async def _pick_backup(self):
        try:
            files = await ft.FilePicker().pick_files(dialog_title=fsi.BTN_RESTORE,
                                                     with_data=True)
        except Exception as error:
            self.toast("Öffnen nicht möglich: %s" % error, C["red"])
            return
        if not files:
            return
        item = files[0]
        try:
            raw = item.bytes
            if raw is None and item.path:
                # Am PC (Testlauf) kommen die Daten nicht mit
                with open(item.path, "rb") as handle:
                    raw = handle.read()
            backup = fsi.read_backup(raw or b"")
        except (OSError, fsi.BackupError) as error:
            self.app.info(fsi.ERROR_TITLE, str(error))
            self.app.page.update()
            return
        self._flush_inputs()
        self._show_backup(backup)
        self.app.page.update()

    def _show_backup(self, backup):
        """Vorschau mit der Wahl Zusammenfuehren / Alles ersetzen (wie am PC)."""
        def choose(action):
            self.app.page.pop_dialog()
            if action:
                action(backup)
            self.app.page.update()

        self.app.page.show_dialog(ft.AlertDialog(
            modal=True, bgcolor=C["card"],
            title=ft.Text(fsi.ERROR_TITLE, color=C["text"], size=18,
                          weight=ft.FontWeight.BOLD),
            content=ft.Column([
                ft.Text("\n".join(fsi.backup_summary(backup)["zeilen"]),
                        color=C["text_soft"], size=14),
                ft.Text(fsi.PREVIEW_HINT, color=C["text_dim"], size=13),
            ], tight=True, spacing=12),
            actions=[ft.TextButton(fsi.BTN_CANCEL, on_click=lambda _e: choose(None)),
                     ft.TextButton(content=ft.Text(fsi.BTN_REPLACE, color=C["red"]),
                                   on_click=lambda _e: choose(self._replace_backup)),
                     ft.TextButton(fsi.BTN_MERGE,
                                   on_click=lambda _e: choose(self._merge_backup))]))

    def _ask(self, title, message, on_answer):
        """Frage mit Ja und Nein - beide Antworten gehen weiter."""
        def answer(yes):
            self.app.page.pop_dialog()
            on_answer(yes)
            self.app.page.update()

        self.app.page.show_dialog(ft.AlertDialog(
            modal=True, bgcolor=C["card"],
            title=ft.Text(title, color=C["text"], size=18, weight=ft.FontWeight.BOLD),
            content=ft.Text(message, color=C["text_dim"], size=14),
            actions=[ft.TextButton("Nein", on_click=lambda _e: answer(False)),
                     ft.TextButton("Ja", on_click=lambda _e: answer(True))]))

    def _merge_backup(self, backup):
        runs = fsi.deleted_runs(self.db, backup)

        def merge(restore):
            chosen = runs if restore else []
            try:
                count = fsi.merge_backup(self.db, backup, [item["lauf"] for item in chosen],
                                         "Handy")
            except fsi.BackupError as error:
                self.app.info(fsi.ERROR_TITLE, str(error))
                return
            self._after_restore()
            self.app.info(fsi.ERROR_TITLE,
                          fsi.merge_message(count, [item["name"] for item in chosen]))

        if runs:
            self._ask(fsi.DELETED_TITLE, fsi.deleted_question(runs), merge)
        else:
            merge(False)

    def _replace_backup(self, backup):
        def replace():
            try:
                path = fsi.replace_all(self.db, backup, os.path.dirname(self.db.db_path),
                                       APP_VERSION, "Handy")
            except fsi.BackupError as error:
                self.app.info(fsi.ERROR_TITLE, str(error))
                return
            self._after_restore()
            self.app.info(fsi.ERROR_TITLE, fsi.replace_message(backup, path))

        self.app.confirm(fsi.REPLACE_TITLE, fsi.replace_question(backup),
                         lambda: self.app.confirm(fsi.REPLACE_CONFIRM_TITLE,
                                                  fsi.REPLACE_CONFIRM, replace))

    def _after_restore(self):
        """Nach dem Einspielen alles neu anzeigen (wie nach dem Zuruecksetzen)."""
        game = self.app.screens["game"].game
        game.invalidate()
        game._summaries.clear()   # Kurzinfos der Plaetze neu rechnen
        game.reload()
        self.app.screens["game"].room = None
        values = learning_settings()
        for key, row in self.goal_rows.items():
            row.controls[0].content.value = values[key]
        self.goal_stepper.value = values["ziel_anzahl"]
        self.goal_stepper.set_maximum(self.goal_stepper.maximum)
        self.entry_reminder.value = values["erinnerung_zeit"]
        self.app.notify_progress()
        self.app.refresh_after_sync()

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
    "testproject": ProjectScreen, "abschluss": FinalProjectScreen,
    "notebook": NotebookScreen, "calc": CalcScreen,
    "progress": ProgressScreen,
    "settings": SettingsScreen, "search": SearchScreen,
}


class FISIMobileApp:
    def __init__(self, page):
        self.page = page
        page.title = "%s %s" % (APP_TITLE, APP_VERSION)
        page.padding = 0
        self.db = DBManager(error_handler=lambda message: self.toast(message, C["red"]))
        self.sync = SyncController(self)
        self.update_dialog_open = False
        self.last_auto_check = 0
        self.dismissed_version = None
        self.slot_chosen = False   # Spielstand nach dem Start schon gewaehlt? (ab 0.48)
        self._build_ui()
        page.on_view_pop = self._view_popped
        page.on_app_lifecycle_state_change = self._lifecycle
        self.show_tab("dashboard")

    def _build_ui(self):
        """Design, Seiten und Navigation (auch zum Neuaufbau nach einem
        Wechsel der Grundfarbe)."""
        page = self.page
        page.theme_mode = ft.ThemeMode.LIGHT if fisi_theme.light else ft.ThemeMode.DARK
        page.bgcolor = C["bg"]
        page.theme = page.dark_theme = ft.Theme(
            color_scheme=ft.ColorScheme(
                primary=C["purple"], secondary=C["accent"], surface=C["bg"],
                on_surface=C["text"], error=C["red"]),
            navigation_bar_theme=ft.NavigationBarTheme(
                bgcolor=C["sidebar"], indicator_color=C["card_hi"],
                label_text_style=ft.TextStyle(size=11, color=C["text_dim"])))

        self.screens = {key: cls(self) for key, cls in SCREEN_CLASSES.items()}
        self.tab = "dashboard"

        self.crumb_main = ft.Text("", size=12, weight=ft.FontWeight.BOLD, color=C["text"])
        self.crumb_sub = ft.Text("", size=12, weight=ft.FontWeight.BOLD, color=C["accent"])
        self.body = ft.Container(expand=True)
        self.nav = ft.NavigationBar(
            destinations=[ft.NavigationBarDestination(
                icon=ft.Icon(icon, color=C["muted"]),
                selected_icon=ft.Icon(selected, color=C["accent"]), label=caption)
                for _key, icon, selected, caption in NAV],
            selected_index=0, on_change=self._nav_changed,
            bgcolor=C["sidebar"], indicator_color=C["card_hi"])

        page.views.clear()
        page.views.append(ft.View(
            route="/", controls=[self.body], appbar=self._appbar(root=True),
            navigation_bar=self.nav, bgcolor=C["bg"], padding=0))

    def change_color(self, preset_id=None, background_id=None, mode=None):
        """Neue Grundfarbe bzw. neuen Hintergrund speichern und alle Seiten
        neu aufbauen. Ab 0.48 deckt solange eine Meldung "Farben werden
        angewendet" alles ab und faengt jedes Tippen ab - so gibt es keine
        doppelten Wechsel und keine halb umgefaerbten Seiten."""
        if getattr(self, "_recoloring", False):
            return  # Ein Tippen waehrend des Umbaus wird ignoriert
        self._recoloring = True
        overlay = self._busy_overlay()
        self.page.overlay.append(overlay)
        self._lock_bars(True)
        self.page.update()
        self.page.run_task(self._recolor, preset_id, background_id, overlay, mode)

    async def _recolor(self, preset_id, background_id, overlay, mode=None):
        started = time.monotonic()
        try:
            # Kurz warten, damit die Meldung sicher gezeichnet ist
            await asyncio.sleep(0.05)
            if preset_id:
                fisi_theme.save_preset(preset_id)
            if background_id:
                fisi_theme.save_background(background_id)
            if mode:
                fisi_theme.save_mode(mode)
            spiel.refresh_theme_tables()
            # Eine laufende Pruefungssession endet mit dem Neuaufbau - ihr
            # Zeitgeber soll nicht im Hintergrund weiterlaufen
            quiz = self.screens.get("quiz")
            if quiz is not None:
                quiz.running = False
                quiz.exam.hide()   # Pruefung (ab 0.51): Antworten sichern, Uhr anhalten
            self._build_ui()
            self.show_tab("settings")
            rest = fisi_theme.BUSY_MIN_SECONDS - (time.monotonic() - started)
            if rest > 0:
                await asyncio.sleep(rest)
        finally:
            if overlay in self.page.overlay:
                self.page.overlay.remove(overlay)
            self._lock_bars(False)
            self._recoloring = False
            self.page.update()

    def _lock_bars(self, locked):
        """Kopfzeile und Navigationsleiste liegen nicht unter der Abdeckung -
        sie werden waehrend des Farbwechsels deshalb eigens gesperrt."""
        for view in self.page.views:
            for bar in (view.appbar, view.navigation_bar):
                if bar is not None:
                    bar.disabled = locked

    @staticmethod
    def _busy_overlay():
        """Abdeckung mit der Meldung waehrend des Farbwechsels (wie am PC)."""
        card = ft.Container(
            content=ft.Column([
                ft.ProgressRing(width=44, height=44, stroke_width=5, color=C["accent"],
                                bgcolor=C["ring_bg"]),
                ft.Text(fisi_theme.BUSY_TITLE, size=18, weight=ft.FontWeight.BOLD,
                        color=C["text"], text_align=ft.TextAlign.CENTER),
                ft.Text(fisi_theme.BUSY_TEXT, size=13, color=C["text_dim"],
                        text_align=ft.TextAlign.CENTER),
            ], spacing=12, tight=True, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            width=300, padding=ft.Padding.symmetric(horizontal=24, vertical=26),
            bgcolor=C["card"], border_radius=18, border=ft.Border.all(1, C["border_hi"]))
        return ft.Container(content=card, left=0, top=0, right=0, bottom=0,
                            alignment=ft.Alignment.CENTER, bgcolor=C["bg"],
                            on_click=lambda _e: None)

    # -- Kopfzeile und Navigation ------------------------------------------

    def _appbar(self, root, crumbs=None):
        if crumbs:
            title = ft.Row([ft.Text(crumbs[0], size=12, weight=ft.FontWeight.BOLD,
                                    color=C["text"]),
                            ft.Text("/", size=12, color=C["muted"]),
                            ft.Text(crumbs[1], size=12, weight=ft.FontWeight.BOLD,
                                    color=C["accent"])], spacing=7)
        else:
            title = ft.Row([self.crumb_main, ft.Text("/", size=12, color=C["muted"]),
                            self.crumb_sub], spacing=7)
        leading = None
        if root:
            logo = ui.Ring(size=30, thickness=4, big_size=1, small_size=1)
            logo.set(1.0, C["accent"], C["accent2"])
            logo.controls[1] = ft.Container(content=ui.dot(C["accent2"], 10), width=30,
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
            # scroll_to ist in flet 1.0 eine Coroutine
            async def scroll():
                try:
                    await content.scroll_to(offset=0, duration=200)
                except RuntimeError:
                    pass
            self.page.run_task(scroll)

    def open_cards(self, category, topic=None):
        self.screens["cards"].set_category(category, topic)
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

    def info(self, title, message):
        """Hinweis mit nur einem Knopf (z.B. Mitbewerber auf der Weltkarte)."""
        def close(_event):
            self.page.pop_dialog()
            self.page.update()

        self.page.show_dialog(ft.AlertDialog(
            modal=False, bgcolor=C["card"],
            title=ft.Text(title, color=C["text"], size=18, weight=ft.FontWeight.BOLD),
            content=ft.Text(message, color=C["text_dim"], size=14),
            actions=[ft.TextButton("OK", on_click=close)]))

    async def save_file(self, name, data, mime):
        """Speichern ueber den Dateidialog des Handys; klappt das nicht,
        bietet "Teilen" die Datei an (z.B. fuer Drive oder E-Mail)."""
        try:
            path = await ft.FilePicker().save_file(file_name=name, src_bytes=data)
            if path and not os.path.exists(path):
                # Am PC (Testlauf) schreibt der Dialog die Datei nicht selbst
                with open(path, "wb") as handle:
                    handle.write(data)
            if path:
                self.toast("Gespeichert: %s" % name)
            return
        except Exception:
            pass
        try:
            await ft.Share().share_files([ft.ShareFile.from_bytes(data, mime_type=mime,
                                                                  name=name)])
        except Exception as error:
            self.toast("Speichern nicht möglich: %s" % error, C["red"])

    def notify_progress(self):
        """Nach jeder Lernaktivitaet: Abgleich vormerken und neu erreichte
        Abzeichen zeigen (ab 0.46)."""
        self.sync.schedule()
        game = self.screens["game"].game
        if game.unlocked:
            # Kurz warten, damit erst die neue Ansicht (z.B. der Feierabend) steht
            self.page.run_task(self._delayed_unlocks)

    async def _delayed_unlocks(self):
        await asyncio.sleep(0.4)
        self.show_unlocks()

    def show_unlocks(self):
        """Neu erreichte Abzeichen (ab 0.46): grosse als Meilenstein-Moment,
        kleinere als kurzer Hinweis unten - wie am PC."""
        game = self.screens["game"].game
        if not game.unlocked:
            return
        items = game.take_unlocks()
        moments = [item for item in items if item["moment"]]
        others = [item for item in items if not item["moment"]]
        if others:
            self.toast("  ·  ".join(item["hinweis"] for item in others[:3]) +
                       ("  ·  +%d" % (len(others) - 3) if len(others) > 3 else ""),
                       C["yellow"])
        if moments:
            dialog = getattr(self, "moment_dialog", None)
            if dialog is not None and dialog.open:
                self.moments += moments       # Dialog ist schon offen
            else:
                self.moments = moments
                self._show_moment(0)
        self.page.update()

    def _show_moment(self, position):
        state = self.screens["game"].game.state

        def close(_event=None):
            dialog.open = False
            self.page.update()

        def next_one(_event):
            close()
            if position + 1 < len(self.moments):
                self._show_moment(position + 1)
                self.page.update()

        def open_list(_event):
            close()
            self.open_achievements()

        info = self.moments[position]
        dialog = ft.AlertDialog(
            modal=False, bgcolor=C["card"], scrollable=True,
            shape=ft.RoundedRectangleBorder(
                radius=22, side=ft.BorderSide(width=2, color=spiel.tier_color(info["tier"]))),
            inset_padding=ft.Padding.symmetric(horizontal=14, vertical=24),
            content_padding=ft.Padding.symmetric(horizontal=20, vertical=22),
            content=ft.Container(
                content=spiel.moment_card(info, state, position, len(self.moments),
                                          next_one, open_list), width=330))
        self.moment_dialog = dialog
        self.page.show_dialog(dialog)

    def open_achievements(self):
        """Spiel > Reise > Erfolge oeffnen (aus dem Meilenstein-Moment)."""
        if not self.slot_chosen:
            self.show_tab("game")   # erst einen Platz waehlen
            return
        if self.tab != "game":
            self.show_tab("game")
        else:
            while len(self.page.views) > 1:
                self.page.views.pop()
        self.screens["game"].open_journey(tab="erfolge")

    def refresh_after_sync(self):
        if len(self.page.views) == 1:
            self.screens[self.tab].on_show()

    def _lifecycle(self, event):
        if event.state in (ft.AppLifecycleState.PAUSE, ft.AppLifecycleState.HIDE,
                           ft.AppLifecycleState.INACTIVE):
            # Ab 0.51: Eingaben in Pruefung und Abschlussprojekt sichern
            self.screens["quiz"].exam.save_answers()
            self.screens["abschluss"].flush()
            self.sync.on_leave()
        elif event.state in (ft.AppLifecycleState.RESUME, ft.AppLifecycleState.SHOW):
            # Android beendet die App im Hintergrund oft nicht: Beim Zurueckholen
            # laeuft main() nicht erneut, daher hier ebenfalls nachsehen.
            self.auto_check()
            self.check_reminder()

    def start_review(self):
        """"Jetzt wiederholen" (ab 0.51): erst faellige Karteikarten, dann
        faellige Pruefungstrainer-Fragen."""
        plan = ReviewPlan.from_db(self.db)
        source = plan.first_source()
        if source is None:
            self.toast("Heute ist nichts mehr fällig.")
            return
        key = "cards" if source == SRC_CARD else "quiz"
        self.screens[key].practice(plan.session(source))
        self.open(key)

    def check_reminder(self):
        """Erinnerung ans Tagesziel (ab 0.51) als Hinweis beim Oeffnen bzw.
        Zurueckholen der App - eine Benachrichtigung bei geschlossener App
        bietet Flet 1.0.1 nicht."""
        try:
            settings = fisi_update.load_settings()
            values = learning_settings()
            goal = DailyGoal.from_db(self.db, values["ziel_anzahl"])
            if reminder_due(settings, goal, shown_on=settings.get("erinnerung_gezeigt", "")):
                import datetime
                save_learning_settings(erinnerung_gezeigt=datetime.date.today().isoformat())
                self.toast(reminder_text(goal), C["green"])
                self.page.update()
        except Exception:
            traceback.print_exc()

    # -- Updates -------------------------------------------------------------

    # Automatische Suche: kurz nach dem Start (wie am PC nach 3 Sekunden),
    # beim Zurueckholen aus dem Hintergrund hoechstens alle 30 Minuten und
    # nach einem Netzfehler (z.B. Netz beim Start noch nicht da) ein zweiter
    # Versuch nach 30 Sekunden.
    AUTO_DELAY = 3
    AUTO_INTERVAL = 30 * 60
    AUTO_RETRY = 30

    def check_updates(self, manual=False):
        self.page.run_task(self._check_updates, manual)

    async def _check_updates(self, manual=False, delay=0, retry=False):
        if delay:
            await asyncio.sleep(delay)
        info, error = None, None
        try:
            # Netzwerk im Hintergrund, Anzeige danach in der Ereignisschleife -
            # so kommt sich die Suche nicht mit dem Abgleich beim Start in die Quere.
            info = await asyncio.to_thread(
                fisi_update.check_for_update, APP_VERSION, kind="android")
        except fisi_update.UpdateError as exc:
            error = str(exc)
        except Exception as exc:
            error = "Unerwarteter Fehler: %s" % exc
        if manual:
            self.screens["settings"].show_update_status(info, error)
        elif error:
            # erfolglos: beim naechsten Zurueckholen erneut versuchen
            self.last_auto_check = 0
            if retry:
                self.page.run_task(self._check_updates, False, self.AUTO_RETRY, False)
        else:
            self.last_auto_check = time.monotonic()
        # "Spaeter" gilt bis zum naechsten App-Start - nur die Suche von Hand
        # zeigt dieselbe Version sofort wieder an.
        if info is not None and (manual or info.version != self.dismissed_version):
            self.show_update_dialog(info)
        self.page.update()

    def auto_check(self, delay=0):
        if not fisi_update.load_settings().get("auto_check", True):
            return
        now = time.monotonic()
        if self.last_auto_check and now - self.last_auto_check < self.AUTO_INTERVAL:
            return
        self.last_auto_check = now
        self.page.run_task(self._check_updates, False, delay, True)

    def show_update_dialog(self, info):
        if self.update_dialog_open:
            return
        self.update_dialog_open = True

        def close(_event=None):
            self.update_dialog_open = False
            self.dismissed_version = info.version
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
                ft.Text(hint, size=12, color=C["accent"]),
            ], tight=True, spacing=8, scroll=ft.ScrollMode.AUTO, height=320),
            actions=[ft.TextButton("Später", on_click=close),
                     ft.TextButton("Herunterladen", on_click=download)]))


def main(page: ft.Page):
    app = FISIMobileApp(page)
    page.data = app
    if os.environ.get("FISI_SELFTEST"):
        return
    app.sync.auto_start()
    app.auto_check(delay=app.AUTO_DELAY)

    async def remind_later():
        # Erinnerung ans Tagesziel (ab 0.51), nach dem ersten Abgleich
        await asyncio.sleep(8)
        app.check_reminder()
    page.run_task(remind_later)


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
        # Reinzoom in die Themen eines Fachbereichs (ab 0.37)
        dashboard = app.screens["dashboard"]
        for category in CATEGORIES + [CATEGORIES[-1]]:
            dashboard._toggle_zoom(category)
    except Exception:
        failures.append("Themen-Reinzoom: %s" % traceback.format_exc())
    try:
        # Ab 0.51: Trainer einmal durchspielen (ohne zu speichern), Wiederholung
        calc = app.screens["calc"]
        calc._on_tab("trainer")
        trainer = calc.trainer
        trainer.db = type("NoDB", (), {"log_trainer": lambda *a: True,
                                       "trainer_stats": lambda *a: {}})()
        for kind, _name in TRAINER_KINDS:
            trainer.kind_pills.select_value(kind, notify=False)
            trainer.start_round()
            for _step in range(len(trainer.tasks)):
                task = trainer.tasks[trainer.index]
                for key, field in trainer.entries.items():
                    field.value = task.solution[key]
                trainer.check()
                if not trainer.results[-1]:
                    failures.append("Trainer: Musterloesung abgelehnt (%s)" % task.text)
                trainer.check()
        calc._on_tab("rechner")
        app.start_review()
        app.check_reminder()
    except Exception:
        failures.append("Trainer/Wiederholung: %s" % traceback.format_exc())
    try:
        # Ab 0.51: jede Pruefungsart einmal aufbauen, bewerten und auswerten
        # (ohne Ergebnis zu speichern), alle Reiter des Abschlussprojekts
        quiz = app.screens["quiz"]
        quiz.mode_pills.select_value("pruefung")
        exam = quiz.exam
        for kind in fp.EXAMS:
            exam.state = fp.new_exam(kind["art"], [], seed=1)
            exam.task_no = exam.wiso_page = 0
            exam.show_running()
            fp.submit(exam.state)
            if kind["art"] != fp.WISO:
                exam.show_grading()
                for number in range(len(exam.state["aufgaben"])):
                    exam._grade_task(number)
            exam.result = fp.evaluate(exam.state)
            exam.show_result(kind["art"])
        exam.state = None
        quiz.mode_pills.select_value("uebung")
        project = app.screens["abschluss"]
        for tab, _caption in fpj.TABS:
            project._on_tab(tab)
        if not fpj.export_pdf(project.fields).startswith(b"%PDF") or \
                not fpj.export_text(project.fields):
            failures.append("Abschlussprojekt: Export leer")
    except Exception:
        failures.append("Pruefung/Abschlussprojekt: %s" % traceback.format_exc())
    try:
        # Lernspiel: Uebersicht und ein Ticket aufbauen, ohne etwas zu speichern
        game = app.screens["game"]
        game.game.state.profile = {"name": "Test",
                                   "aussehen": dict(fisi_game.DEFAULT_APPEARANCE)}
        game.render()
        wrong = [fisi_game.task_by_id(fisi_game.WRONG_DELIVERY + "ssd-automaten")]
        for task in fisi_game.GAME["aufgaben"] + fisi_game.GAME["zwischenfaelle"] + wrong:
            game.open_ticket(task["id"])
            game._show_help()
            task = game.task
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
            elif task["typ"] == "rack" and solution:
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
            elif task["typ"] == "terminal":
                game.options.run(len(task["schritte"][0]["befehle"]) - 1)
                for step in task["schritte"]:
                    game.options.run(fisi_game.terminal_right_index(step))
                game.options.reveal(game.options.complete())
            elif task["typ"] == "diagnose":
                for check_id in solution["pruefungen"]:
                    game.options.check(check_id)
                game.options.cause.select(task["ursache"])
                game.options.measure.select(task["massnahme"])
                if game.options.exchange:
                    game.options.exchange.pick(solution["teil"])
                    for text in solution["reihenfolge"]:
                        game.options.exchange.step(text)
                    game.options.exchange.reset()
                    game.options.answer
                game.options.reveal(True)
            elif task["typ"] == "wartung":
                for point_id, rating in solution["bewertung"].items():
                    game.options.check(point_id)
                    game.options.rate(point_id, rating)
                game.options.closing.select(solution["abschluss"])
                if not game.options.complete():
                    failures.append("Wartung %s: nicht vollstaendig" % task["id"])
                game.options.reveal(True)
        game._select_room("serverraum")
        game._select_room("lager")
        # Grossansichten (ohne reload, der Test-Spielstand steht nur im Speicher)
        game.office = ft.Column()
        for key in ("buero", "kunde", "zuhause"):
            game.site_key = key
            game._fill_site()
            content = game.office_plan.site_data
            for person in content["kollegen"]:
                game._office_text(tuple(person["platz"]), person)
        game.place = "talheim_nord"
        game._fill_site()
        game.site_key = "zuhause"
        game.editing = True
        game.selected = "start-matratze"
        game._fill_site()
        game._home_tap(3.0, 3.0)
        game._office_text(fisi_game.start_position(game.office_plan.site_data), None)
        # Firma (ab 0.33): vor und nach der Gruendung, mit Mitarbeitern
        game.firm_box = ft.Column()
        game._fill_firm()
        state = game.game.state
        state.firm = {"name": "Test IT", "tag": state.day, "stufe": 1}
        for item in fisi_game.applicants(state)[:2]:
            state.staff[item["id"]] = dict(item)
            state.ever_hired.add(item["id"])
        game.training_for = next(iter(state.staff))
        for key, _name in fisi_game.firm_tabs(state):
            game.firm_tab = key
            game._fill_firm()
        # Auftraege (ab 0.34): Kalkulation offen, Ticket-Auswahl offen
        game.firm_tab = "auftraege"
        game.offer_for = state.inquiries()[0]["id"]
        game.markup = 10
        game.offer_help = True
        game.assign_for = state.customer_tickets()[0]["id"]
        game._fill_firm()
        game._fill_firm()
        # Projekte (ab 0.35): Kalkulation, laufendes Projekt mit Team und Details
        game.firm_tab = "projekte"
        tender = state.tenders()[0]
        game.offer_for = tender["id"]
        game.markup = 10
        game._fill_firm()
        won = dict(tender, projekt=tender["id"], tag=state.day, netto=1000.0, anzahlung=300,
                   frist_tag=state.day + 4, stand=5.0, team=[fisi_game.SELF], fertig=None,
                   tage=[])
        state.projects[tender["id"]] = won
        state.project_offers[tender["id"]] = dict(won, gewonnen=True, geld=0, marktpreis=1100.0,
                                                  markt_zuschlag=12, zuschlag=10)
        game.team_for = tender["id"]
        game.details_for = {tender["id"]}
        game._fill_firm()
        game.firm_tab = "finanzen"
        game._fill_firm()
        # Gebaeude (ab 0.36): Stufe 3 mit Leerstand, Stufe 5 mit Sonderraeumen
        game.firm_tab = "gebaeude"
        for number, rooms in ((3, []), (5, ["lager", "serverraum"])):
            state.firm["stufe"] = number
            state.rooms = {room_id: {"raum": room_id} for room_id in rooms}
            game._fill_firm()
            game.site_key = "buero"
            game._fill_site()
        # Weltkarte und Filiale (ab 0.45): Karte, Liste, Vorschauen, zweiter Standort
        state.firm["stufe"] = 4
        state.branch = {"name": "Test Filiale", "tag": state.day, "stufe": 1}
        state.staff_site[next(iter(state.staff))] = fisi_game.SITE_BRANCH
        for key in ("gebaeude", "mitarbeiter"):
            game.firm_tab = key
            game._fill_firm()
        original = fisi_game.map_list_mode
        try:
            for flag in (False, True):
                fisi_game.map_list_mode = lambda flag=flag: flag
                game.render()
        finally:
            fisi_game.map_list_mode = original
        world = spiel.WorldMap(state, lambda _item: None)
        for item in fisi_game.map_places(state):
            spiel.model_preview(item["id"], state)
            x1, y1, x2, y2 = item["box"]
            world.place_under((x1 + x2) / 2 * world._scale(), (y1 + y2) / 2 * world._scale())
        game.open_place(fisi_game.place_by_id("bitweiche", state))
        for key in ("filiale", "buero", "zuhause", "kunde"):
            game.site_key = key
            game._fill_site()
        game.render()
        game.site_key = "buero"
        game._fill_site()
        for person in game.office_plan.site_data["kollegen"]:
            game._office_text(tuple(person["platz"]), person)
        # Reise mit Erfolgen (ab 0.46): Bestwerte, Abzeichen, jeder Meilenstein-Moment
        game.journey_box = ft.Column()
        for tab in ("rueckblick", "erfolge"):
            game.journey_tab = tab
            game._fill_journey()
        for group, _name in fisi_game.achievement_groups():
            game._badge_choose(group)
        for rule in fisi_game.achievement_rules()["erfolge"]:
            for level, stage in enumerate(rule["stufen"], 1):
                spiel.badge_image(rule["bild"], rule.get("farbe"), stage["stufe"])
                info = fisi_game.unlock_info(state, rule, level, [])
                spiel.moment_card(info, state, 0, 2, None, None)
        spiel.badge_image("stern", None, None)
        # Serverfarm (ab 0.52): Seite in allen Zustaenden, jede Aufgabe einmal
        game.farm_box = ft.Column()
        state.farm_unlocked, state.farm = None, None
        game._fill_farm()
        state.farm_unlocked = state.day
        game._fill_farm()
        state.farm = fisi_game.new_farm(state.day)
        game._fill_farm()
        game._farm_toggle_edit()
        game._farm_toggle_edit()
        for task in fisi_game.farm_tasks():
            game.open_farm_task(task["id"])
            game._show_help()
            if task["typ"] == "bestueckung":
                game.options.answer = fisi_game.fit_solution(task)
                game.options._build_middle()
                game.options._paint()
                game.options.reveal(True)
        state.farm["abnahme"] = fisi_game.farm_acceptance(state, state.day)
        state.farm["fertig"] = state.day
        game._fill_farm()
        state.farm_unlocked, state.farm = None, None
        # Spielstand-Plaetze (ab 0.48): Auswahl mit belegten und leeren Plaetzen
        game.picking = True
        game.render()
        for item in game.game.slots() + [dict(game.game.slots()[0], extra=True)]:
            game._slot_card(item)
        game.picking = False
        game.slot_bar()
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
