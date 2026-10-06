# -*- coding: utf-8 -*-
"""
FISI Lernplattform - Screenreader-Prototyp (Flet-Desktop)
=========================================================

Nur fuer den Test mit NVDA (Plan 0.59, Abschnitt 8a, Lesart A). Kein Teil des
Programms, kein Release. Zeigt die Seite "Optionen" so, wie sie nach 0.59
aussehen soll (Updates oben und offen, uebrige Bereiche eingeklappt, Problem
melden offen, Unterbereich "Vorlagen"), dazu eine Beispiel-Karteikarte.

Der Prototyp speichert nichts: Datenbank und einstellungen.json zeigen auf
einen leeren Ordner im Temp-Verzeichnis, Knoepfe zeigen nur eine Meldung.
Texte und Farben kommen aus denselben Modulen wie am Handy.

Start (im Hauptordner des Repos):  python prototyp_screenreader/optionen_flet.py
"""

import json
import os
import sys
import tempfile

# Eigene Daten des Nutzers nie anfassen: leerer Ordner statt Datenordner
os.environ["FISI_DB_PATH"] = os.path.join(tempfile.mkdtemp(prefix="fisi_proto_"),
                                          "fisi_lernplattform.db")
# Im Repo liegen die gemeinsamen Module eine Ebene hoeher, im gebauten
# Windows-Programm (bauordner.py) daneben
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = HERE if os.path.exists(os.path.join(HERE, "fisi_core.py")) else os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import flet as ft  # noqa: E402

import fisi_diagnose as fdg  # noqa: E402
import fisi_hilfe as fh  # noqa: E402
import fisi_leistung as fle  # noqa: E402
import fisi_theme  # noqa: E402
from fisi_theme import C  # noqa: E402

APP_VERSION = "0.58.1"
TITLE = "FISI Screenreader-Prototyp"
HINT_OPEN, HINT_CLOSE = "aufklappen", "einklappen"
STATE_OPEN, STATE_CLOSED = "ausgeklappt", "eingeklappt"
PROTO_NOTE = "Prototyp: Diese Schaltfläche tut hier nichts."

# Zusaetzliche Ansage ueber SemanticsService (unter Windows ein UIA-"Alert",
# den NVDA vorliest). Grund: Flutter meldet unter Windows das Umschalten
# "erweitert/reduziert" nicht als eigenes Ereignis (siehe Bericht). Ob NVDA
# ohne diese Ansage etwas sagt, prueft der Test mit dem Testschalter.
ANNOUNCE = {"service": None, "on": True}


async def announce(message):
    if ANNOUNCE["on"] and ANNOUNCE["service"] is not None:
        try:
            await ANNOUNCE["service"].announce_message(message)
        except Exception:   # Plattform ohne Ansagen: still weiter
            pass


CARDS = [card for card in json.load(open(os.path.join(ROOT, "inhalte", "karteikarten.json"),
                                          encoding="utf-8"))][:5]


# ============================================================================
#  BAUSTEINE
# ============================================================================

def text(value, size=14, color=None, weight=None, **kwargs):
    return ft.Text(value, size=size, color=color or C["text_soft"], weight=weight, **kwargs)


def heading(value, level=2, color=None, size=13):
    """Ueberschrift; NVDA springt mit H von Ueberschrift zu Ueberschrift."""
    return ft.Semantics(header=True, heading_level=level, label=value, container=True,
                        content=ft.Text(
        value.upper() if level > 1 else value, size=size if level > 1 else 22,
            weight=ft.FontWeight.BOLD, color=color or C["accent"]), exclude_semantics=True)


def own_nodes(controls):
    """Jedes Element als eigener Knoten: sonst haengt Flutter Texte an die
    naechste Ueberschrift an und NVDA liest alles als eine Zeile."""
    return [ft.Semantics(container=True, content=item) for item in controls]


def _focus_side(color):
    """Sichtbarer Rahmen nur bei Tastaturfokus (fuer sehende Tastaturnutzer)."""
    return {ft.ControlState.FOCUSED: ft.BorderSide(2, C["accent"]),
            ft.ControlState.DEFAULT: ft.BorderSide(1, color)}


def button(caption, on_click, kind="primary"):
    """Echte Schaltflaeche (Rolle "Schaltfläche", Tab-Ziel, Enter und Leertaste).

    Die Handy-Knoepfe (ui.GradientButton) sind Container mit Klick und werden
    unter Windows/Linux nur als "Bereich" gemeldet - deshalb hier ft.Button."""
    filled = kind == "primary"
    return ft.Button(
        content=caption, on_click=on_click,
        style=ft.ButtonStyle(
            bgcolor={ft.ControlState.DEFAULT: C["violet"] if filled else C["card_alt"],
                     ft.ControlState.HOVERED: "#6D28D9" if filled else C["card_hi"]},
            color=C["on_accent"] if filled else C["text"],
            side=_focus_side(C["violet"] if filled else C["border_hi"]),
            shape=ft.RoundedRectangleBorder(radius=23),
            padding=ft.Padding.symmetric(horizontal=20, vertical=14),
            mouse_cursor=ft.MouseCursor.CLICK, elevation=0,
            text_style=ft.TextStyle(size=14, weight=ft.FontWeight.BOLD)))


def card(title, controls, accent=None, subtitle=None):
    """Offene Karte (Updates, Problem melden): Titel als Ueberschrift."""
    accent = accent or C["accent"]
    head = [ft.Container(width=4, height=14, border_radius=2, bgcolor=accent),
            heading(title, color=accent)]
    if subtitle:
        head.append(ft.Semantics(container=True, content=ft.Text(subtitle, size=12,
                                                                 color=C["muted"])))
    return ft.Container(
        content=ft.Column([ft.Row(head, spacing=8)] + own_nodes(controls), spacing=12,
                          tight=True),
        bgcolor=C["card"], border_radius=16, border=ft.Border.all(1, C["border"]),
        padding=16)


class Fold(ft.Container):
    """Klappbereich nach Plan 0.59, Abschnitt 3.

    - die ganze Kopfzeile ist EINE Schaltflaeche (Tab, Enter, Leertaste, Maus)
    - Pfeil links in der Akzentfarbe (▸ zu, ▾ offen), rechts "aufklappen"/"einklappen"
    - Screenreader hoert "Farben, eingeklappt, Schaltfläche" und den Zustand
      erweitert/reduziert (Semantics.expanded)
    - eingeklappte Inhalte sind nicht im Baum, also auch nicht per Tab erreichbar
    - der Zustand wird nicht gespeichert (E4)
    """

    def __init__(self, title, controls, accent=None, subtitle=None, opened=False,
                 nested=False):
        self.title, self.opened = title, opened
        self.accent = accent or C["accent"]
        self.arrow = ft.Text("", size=20, color=self.accent, weight=ft.FontWeight.BOLD)
        self.hint = ft.Text("", size=13, color=C["text_dim"])
        texts = [ft.Text(title.upper() if not nested else title, size=13 if not nested else 14,
                         weight=ft.FontWeight.BOLD,
                         color=self.accent if not nested else C["text"])]
        if subtitle:
            texts.append(ft.Text(subtitle, size=12, color=C["muted"]))
        row = ft.Row([self.arrow, ft.Column(texts, spacing=2, tight=True, expand=True),
                      self.hint], spacing=10,
                     vertical_alignment=ft.CrossAxisAlignment.CENTER)
        self.head_button = ft.TextButton(
            # Inhalt fuer den Screenreader ausblenden: gelesen wird nur das Label
            content=ft.Semantics(exclude_semantics=True, content=row),
            on_click=self.toggle,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=12),
                padding=ft.Padding.symmetric(horizontal=10, vertical=12),
                overlay_color={ft.ControlState.HOVERED: C["card_hi"],
                               ft.ControlState.FOCUSED: C["card_hi"],
                               ft.ControlState.PRESSED: C["border_hi"]},
                side={ft.ControlState.FOCUSED: ft.BorderSide(2, C["accent"]),
                      ft.ControlState.HOVERED: ft.BorderSide(1, C["border_hi"]),
                      ft.ControlState.DEFAULT: ft.BorderSide(1, "#00000000")},
                mouse_cursor=ft.MouseCursor.CLICK))
        self.head = ft.Semantics(button=True, content=self.head_button)
        self.body = ft.Column(own_nodes(controls), spacing=12, tight=True)
        super().__init__(
            content=ft.Column([ft.MergeSemantics(content=self.head), self.body],
                              spacing=8, tight=True),
            bgcolor=C["card"] if not nested else C["card_alt"], border_radius=16,
            border=ft.Border.all(1, C["border"]),
            padding=ft.Padding.only(left=6, right=6, top=6, bottom=10))
        self._apply()

    def _apply(self):
        self.arrow.value = "▾" if self.opened else "▸"
        self.hint.value = HINT_CLOSE if self.opened else HINT_OPEN
        self.head.label = "%s, %s" % (self.title, STATE_OPEN if self.opened else STATE_CLOSED)
        self.head.expanded = self.opened
        self.body.visible = self.opened
        self.body.padding = ft.Padding.symmetric(horizontal=10)

    async def toggle(self, _event=None):
        self.opened = not self.opened
        self._apply()
        self.update()
        await announce("%s %s" % (self.title, STATE_OPEN if self.opened else STATE_CLOSED))


def switch(label, value=False):
    return ft.Switch(label=label, value=value, active_color=C["accent"],
                     label_text_style=ft.TextStyle(size=14, color=C["text_soft"]))


def radio_group(name, choices, selected):
    """Auswahl mit Optionsfeldern: NVDA liest "Normal, Optionsfeld, ausgewählt, 1 von 3"."""
    return ft.Semantics(label=name, container=True, content=ft.RadioGroup(
        value=selected, content=ft.Row(
            [ft.Radio(value=key, label=caption, active_color=C["accent"],
                      label_style=ft.TextStyle(size=14, color=C["text_soft"]))
             for key, caption in choices], wrap=True)))


# ============================================================================
#  SEITE OPTIONEN
# ============================================================================

class Options:
    def __init__(self, page):
        self.page = page
        # Meldungen erscheinen in einer "Live-Region": NVDA liest sie von selbst vor
        self.status = ft.Text("", size=13, color=C["text_dim"])
        self.status_region = ft.Semantics(live_region=True, content=self.status)

    async def say(self, message):
        self.status.value = message
        self.page.update()
        await announce(message)

    def saying(self, message):
        """Klick-Handler, der eine Meldung zeigt und ansagt."""
        async def handler(_event):
            await self.say(message)
        return handler

    def tile(self, prefix, item, selected):
        """Vorlagen-Kachel (verkleinert): Schaltflaeche mit Zustand ausgewaehlt."""
        return ft.MergeSemantics(content=ft.Semantics(
            button=True, selected=selected, label="%s %s" % (prefix, item["name"]),
            content=ft.TextButton(
                content=ft.Semantics(exclude_semantics=True, content=ft.Column([
                    ft.Container(height=8, width=60, border_radius=4,
                                 bgcolor=item.get("accent", item.get("card"))),
                    ft.Text(item["name"], size=12, weight=ft.FontWeight.BOLD,
                            color=C["text"] if selected else C["text_dim"])],
                    spacing=6, tight=True,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER)),
                on_click=self.saying(
                    "%s %s: setzt nur die Regler (Prototyp, nichts gespeichert)."
                    % (prefix, item["name"])),
                style=ft.ButtonStyle(
                    bgcolor=C["card_hi"] if selected else C["card"],
                    side=_focus_side(C["accent"] if selected else C["border"]),
                    shape=ft.RoundedRectangleBorder(radius=10),
                    padding=ft.Padding.symmetric(horizontal=10, vertical=8),
                    mouse_cursor=ft.MouseCursor.CLICK))))

    def build(self):
        note = self.saying(PROTO_NOTE)
        updates = card("Updates", [
            ft.Row([button("Nach Updates suchen", self.saying(
                "Prototyp: Es wird nicht wirklich gesucht. Installierte Version %s."
                % APP_VERSION))]),
            switch("Beim Start automatisch nach Updates suchen", True),
        ], accent=C["accent2"], subtitle="installierte Version %s" % APP_VERSION)

        tour = Fold(fh.OPTIONS_TITLE, [
            text(fh.OPTIONS_TEXT, size=13, color=C["text_dim"]),
            ft.Row([button(fh.BTN_TOUR, note)]),
            ft.Row([button(fh.BTN_HELP, note, kind="ghost")]),
        ], accent=C["green"], subtitle=fh.OPTIONS_SUBTITLE)

        fonts = Fold(fisi_theme.FONT_TITLE, [
            radio_group(fisi_theme.FONT_TITLE, fisi_theme.FONT_CHOICES, "normal"),
            text(fisi_theme.FONT_HINT, size=12, color=C["muted"]),
        ], subtitle=fisi_theme.FONT_SUBTITLE)

        presets = Fold("Vorlagen", [
            text("Grundfarbe", size=12, color=C["muted"]),
            ft.Row([self.tile("Grundfarbe", item, item["id"] == "cyan_pink")
                    for item in fisi_theme.PRESETS], wrap=True, spacing=8, run_spacing=8),
            text("Hintergrund", size=12, color=C["muted"]),
            ft.Row([self.tile("Hintergrund", item, item["id"] == "violett")
                    for item in fisi_theme.BACKGROUNDS], wrap=True, spacing=8, run_spacing=8),
            text("Eine Vorlage setzt nur die Regler; gespeichert wird erst mit „Speichern“.",
                 size=12, color=C["muted"]),
        ], nested=True)
        colors = Fold("Farben", [
            radio_group("Darstellung", fisi_theme.MODES, fisi_theme.MODE_DARK),
            presets,
            ft.Semantics(live_region=True, content=text(
                "Startwerte aus der Farbwelt", size=13, color=C["text_dim"])),
        ], subtitle="nur für dieses Gerät")

        goal = Fold("Tagesziel", [
            switch("Tagesziel anzeigen", True),
            switch("Lernserie anzeigen", True),
            switch("An das Tagesziel erinnern", False),
        ], accent=C["green"], subtitle="nur für dieses Gerät")

        report = card(fdg.TITLE, [
            text(fdg.HELP, size=13, color=C["text_dim"]),
            ft.Row([button(fdg.BTN_COPY, self.saying("Prototyp: Es wurde nichts kopiert."))]),
        ], accent=C["orange"], subtitle=fdg.SUBTITLE)

        measure = Fold(fle.TITLE, [
            text(fle.HELP, size=13, color=C["text_dim"]),
            switch(fle.SWITCH, False),
        ], accent=C["orange"], subtitle=fle.SUBTITLE)

        return [heading("Optionen", level=1), self.status_region,
                updates, tour, fonts, colors, goal, report, measure]


# ============================================================================
#  SEITE KARTEIKARTE
# ============================================================================

class Flashcard:
    def __init__(self, page):
        self.page, self.index = page, 0
        self.counter = ft.Text("", size=12, color=C["muted"])
        self.question = ft.Text("", size=18, color=C["text"], weight=ft.FontWeight.BOLD)
        self.answer = ft.Text("", size=15, color=C["text_soft"])
        self.answer_region = ft.Semantics(live_region=True, content=self.answer)
        self.reveal = button("Antwort zeigen", self.show_answer)
        self.known = button("Gewusst", self.next_card)
        self.rate = ft.Row([self.known, button("Nicht gewusst", self.next_card, kind="ghost")],
                           wrap=True)

    def paint(self):
        item = CARDS[self.index]
        self.counter.value = "Karte %d von %d" % (self.index + 1, len(CARDS))
        self.question.value = item["q"]
        self.answer.value = ""
        self.reveal.visible, self.rate.visible = True, False

    async def show_answer(self, _event):
        item = CARDS[self.index]
        self.answer.value = "Antwort: " + (item.get("a_full") or item["a"])
        self.reveal.visible, self.rate.visible = False, True
        self.page.update()
        await announce(self.answer.value)
        # Der gedrueckte Knopf verschwindet: Fokus bewusst weitergeben, sonst
        # steht der Screenreader im Leeren
        await self.known.focus()

    async def next_card(self, _event):
        self.index = (self.index + 1) % len(CARDS)
        self.paint()
        self.page.update()
        await self.reveal.focus()

    def build(self):
        self.paint()
        return [heading("Karteikarte", level=1), ft.Container(
            content=ft.Column([self.counter, ft.Semantics(header=True, heading_level=2,
                                                          content=self.question),
                               self.answer_region, self.reveal, self.rate],
                              spacing=14, tight=True),
            bgcolor=C["card"], border_radius=16, border=ft.Border.all(1, C["border"]),
            padding=20)]


# ============================================================================
#  START
# ============================================================================

def main(page: ft.Page):
    page.title = TITLE
    page.bgcolor = C["bg"]
    page.theme_mode = ft.ThemeMode.DARK
    page.window.width, page.window.height = 900, 860
    page.padding = 0
    content = ft.ListView(expand=True, spacing=14,
                          padding=ft.Padding.only(left=20, right=20, top=10, bottom=24))
    views = {"Optionen": Options(page), "Karteikarte": Flashcard(page)}
    tabs = {}

    def show(name):
        content.controls = views[name].build()
        for key, (sem, _btn) in tabs.items():
            sem.selected = key == name
        page.update()

    nav = []
    for name in views:
        btn = button(name, lambda _e, n=name: show(n), kind="ghost")
        sem = ft.Semantics(selected=False, content=btn)
        tabs[name] = (sem, btn)
        nav.append(sem)

    def toggle_announce(event):
        ANNOUNCE["on"] = bool(event.control.value)
    ANNOUNCE["service"] = ft.SemanticsService()
    nav.append(ft.Container(width=20))
    nav.append(switch("Testschalter: zusätzliche Ansagen", True))
    nav[-1].on_change = toggle_announce
    page.add(ft.Column([
        ft.Container(content=ft.Row(nav, spacing=10), padding=ft.Padding.only(
            left=20, right=20, top=14), bgcolor=C["bg"]),
        content], expand=True, spacing=6))
    show("Optionen")


if __name__ == "__main__":
    ft.run(main)
