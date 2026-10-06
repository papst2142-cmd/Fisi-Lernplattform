# -*- coding: utf-8 -*-
"""
FISI Lernplattform (Handy) - Bausteine der Oberflaeche
======================================================

Karten, Verlaufs-Knoepfe, Ringe, Diagramme, Kalender - im selben Look wie die
PC-Version (Farben und Verlaeufe aus fisi_theme.py), aber fuer Touch und
schmale Bildschirme gebaut. Alles mit Flet-Bordmitteln, ohne Pillow.
"""

import calendar
import datetime
import math

import flet as ft
import flet.canvas as cv

import fisi_theme
from fisi_theme import C, GRADIENTS, mix

MONO = "monospace"


# ============================================================================
#  SCHRIFTGROESSE (ab 0.56)
# ============================================================================
#
# Flet 1.0.1 setzt keinen eigenen Textmassstab: Texte folgen damit der
# Schriftgroesse des Systems (Flutter-Standard MediaQuery.textScaler). Die
# Einstellung "Schriftgroesse" der App kommt hinzu: Jeder ft.Text bekommt beim
# Anlegen seine Groesse mal dem Faktor (Normal 1,0 / Gross 1,15 / Sehr gross
# 1,3). Feste Hoehen der Bausteine hier (Knoepfe, Pillen) wachsen mit.
# Zeichnungen auf der Leinwand (Spielkarte) bleiben gleich; Achsen und
# Legenden der Diagramme wachsen ab 0.58 mit (fs, grow).

FONT_FACTOR = [fisi_theme.font_factor()]


def fs(size):
    """Schriftgroesse mal Faktor der Einstellung (fuer ft.TextStyle)."""
    return round(size * FONT_FACTOR[0], 1) if size else size


def grow(value):
    """Feste Hoehe/Breite eines Bausteins mit Text, passend zur Schrift."""
    return int(round(value * FONT_FACTOR[0]))


def set_font_factor(factor):
    FONT_FACTOR[0] = float(factor)


_text_init = ft.Text.__init__


def _scaled_text_init(self, *args, **kwargs):
    _text_init(self, *args, **kwargs)
    if FONT_FACTOR[0] != 1.0:
        self.size = fs(self.size or 14)


ft.Text.__init__ = _scaled_text_init


# ============================================================================
#  TEXT
# ============================================================================

def text(value, size=14, color=None, weight=None, **kwargs):
    return ft.Text(value, size=size, color=color or C["text"], weight=weight, **kwargs)


def label(value, color=None):
    """Kleine Ueberschrift in Grossbuchstaben (wie MENUE/FACHBEREICH am PC)."""
    return ft.Text(value.upper(), size=11, weight=ft.FontWeight.BOLD,
                   color=color or C["muted"])


def gradient(kind, begin=ft.Alignment.CENTER_LEFT, end=ft.Alignment.CENTER_RIGHT):
    start, stop = GRADIENTS[kind] if isinstance(kind, str) else kind
    return ft.LinearGradient(colors=[start, stop], begin=begin, end=end)


# ============================================================================
#  KARTE
# ============================================================================

class Card(ft.Container):
    """Abgerundete Karte mit farbigem Strich und Titel in Grossbuchstaben."""

    def __init__(self, title=None, controls=None, accent=None, subtitle=None,
                 padding=16, spacing=10, expand=None, action=None):
        self.body = ft.Column(controls or [], spacing=spacing, tight=True,
                              horizontal_alignment=ft.CrossAxisAlignment.STRETCH)
        # Ab 0.56: Titel und Unterschrift teilen sich die Zeile (3:2), damit ein
        # langer Untertitel - v.a. bei grosser Schrift - den Titel nicht mitten
        # im Wort umbrechen laesst; die Unterschrift bricht dann selbst um
        self.subtitle_text = ft.Text(subtitle or "", size=11, color=C["muted"],
                                     text_align=ft.TextAlign.RIGHT,
                                     expand=2 if subtitle else None)
        self.title_text = None
        self.tick = None
        column = [self.body]
        if title:
            accent = accent or C["accent"]
            self.tick = ft.Container(width=4, height=14, border_radius=2, bgcolor=accent)
            self.title_text = ft.Text(title.upper(), size=11, weight=ft.FontWeight.BOLD,
                                      color=accent, expand=3)
            header = ft.Row([
                self.tick, self.title_text,
                self.subtitle_text,
            ] + ([action] if action is not None else []),
                spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER)
            column = [header, self.body]
        super().__init__(
            content=ft.Column(column, spacing=12, tight=True),
            bgcolor=C["card"], border_radius=16,
            border=ft.Border.all(1, C["border"]), padding=padding, expand=expand)

    def set_subtitle(self, value, color=None):
        self.subtitle_text.value = value
        self.subtitle_text.expand = 2 if value else None
        self.subtitle_text.color = color or C["muted"]

    def set_title(self, value, color=None):
        """Titel (und Farbe) zur Laufzeit aendern - nur bei Karten mit Titel."""
        if self.title_text is not None:
            self.title_text.value = value.upper()
            if color:
                self.title_text.color = self.tick.bgcolor = color


class FoldCard(Card):
    """Ab 0.56: Karte zum Auf- und Zuklappen (Optionen), Standard zu. Der
    Kopf ist eine Schaltflaeche mit Beschriftung fuer TalkBack. Der Zustand
    bleibt fuer die Laufzeit der App erhalten (key).

    Ab 0.59 (Optionen, marker=True, wie am PC): Pfeil links in der
    Akzentfarbe, rechts "aufklappen"/"einklappen", ganze Kopfzeile mindestens
    48 dp hoch, TalkBack liest "Farben, eingeklappt" und sagt Wechsel an
    (live_region). Die Optionen vergessen den Zustand beim Oeffnen
    (reset_states)."""

    _open_state = {}

    def __init__(self, title, controls=None, accent=None, subtitle=None, key=None,
                 opened=False, open_text="aufklappen", close_text="zuklappen",
                 marker=False, **kwargs):
        if marker:
            open_text, close_text = fisi_theme.FOLD_OPEN_TEXT, fisi_theme.FOLD_CLOSE_TEXT
        arrow = ft.Icon(ft.Icons.EXPAND_MORE, color=C["muted"], size=20)
        arrow_text = ft.Text("", size=11, color=C["muted"])
        if marker:
            arrow_text = ft.Text("", size=12, weight=ft.FontWeight.BOLD, color=C["text_dim"])
            action = arrow_text
        else:
            action = ft.Row([arrow_text, arrow], spacing=2, tight=True)
        super().__init__(title, controls, accent=accent, subtitle=subtitle,
                         action=action, **kwargs)
        self.arrow, self.arrow_text = arrow, arrow_text
        self.marker = marker
        self.fold_key = key or title
        self.opened = self._open_state.get(self.fold_key, opened)
        self._texts = (open_text, close_text)
        header = self.content.controls[0]
        # Titel und Unterschrift untereinander, rechts nur der Pfeil - sonst
        # brach z.B. "Loeschen und zuruecksetzen" schon bei normaler Schrift
        # mitten im Wort um
        self.title_text.expand = None
        self.subtitle_text.expand = None
        self.subtitle_text.text_align = ft.TextAlign.LEFT
        self.subtitle_text.visible = bool(subtitle)
        if marker:
            # Ab 0.59: Pfeil links, groesser, in der Akzentfarbe
            self.arrow = ft.Icon(ft.Icons.ARROW_RIGHT, color=accent or C["accent"], size=28)
            header.controls = [self.arrow, self.tick,
                               ft.Column([self.title_text, self.subtitle_text], spacing=2,
                                         tight=True, expand=True),
                               header.controls[-1]]
            header.spacing = 6
        else:
            header.controls = [self.tick,
                               ft.Column([self.title_text, self.subtitle_text], spacing=2,
                                         tight=True, expand=True),
                               header.controls[-1]]
        # Ab 0.59 (marker): Touch-Ziel mindestens 48 dp - Pfeil 28 + 2 x 10
        self.header_button = ft.Container(content=header, on_click=self.toggle, ink=True,
                                          border_radius=8, padding=ft.Padding.symmetric(
                                              vertical=10 if marker else 6))
        # TalkBack liest "Farben, Schaltfläche, aufklappen" statt der Einzelteile
        self.header_semantics = ft.Semantics(content=self.header_button, button=True,
                                             container=True, live_region=True if marker
                                             else None)
        self.content.controls[0] = self.header_semantics
        self._fold_title = title
        self._apply()

    @classmethod
    def reset_states(cls, prefix):
        """Ab 0.59 (E4): gemerkte Zustaende mit diesem Schluessel-Anfang vergessen."""
        for key in [key for key in cls._open_state if key.startswith(prefix)]:
            del cls._open_state[key]

    def accessible_name(self):
        return self.header_semantics.label

    def _apply(self):
        self.body.visible = self.opened
        state = self._texts[1] if self.opened else self._texts[0]
        self.arrow_text.value = state
        if self.marker:
            self.arrow.icon = ft.Icons.ARROW_DROP_DOWN if self.opened else ft.Icons.ARROW_RIGHT
            self.header_semantics.label = fisi_theme.fold_label(self._fold_title, self.opened)
        else:
            self.arrow.icon = ft.Icons.EXPAND_LESS if self.opened else ft.Icons.EXPAND_MORE
            self.header_semantics.label = "%s, %s" % (self._fold_title, state)
        self.header_semantics.expanded = self.opened

    def set_opened(self, flag):
        """Ab 0.59: auf- oder zuklappen (ohne Wechsel, wenn schon so)."""
        if bool(flag) != self.opened:
            self.toggle()

    def toggle(self, _event=None):
        self.opened = not self.opened
        self._open_state[self.fold_key] = self.opened
        self._apply()
        try:
            self.update()
        except RuntimeError:    # noch nicht auf der Seite (z.B. im Test)
            pass


# ============================================================================
#  KNOEPFE UND AUSWAHL
# ============================================================================

def as_button(control, selected=None):
    """Ab 0.59.1 (H1): Eine antippbare Flaeche (Container mit on_click)
    meldet sich als Schaltflaeche statt als Flaeche. Den Namen liest TalkBack
    aus den Texten der Flaeche (z.B. "Karteikarten, 1565 Karten ...").
    selected=True/False fuer Kacheln mit Auswahlzustand. container=True haelt
    Rolle, Name und Antippen in einem Element (gemessen). Aussehen und
    Verhalten bleiben gleich; die Flaeche selbst wird nicht veraendert.
    Ohne on_click (gesperrt, schon erledigt) bleibt sie ohne Rolle."""
    if getattr(control, "on_click", None) is None:
        return control
    # "expand" gilt fuer das umschliessende Element, sonst aendert sich die
    # Aufteilung in Zeilen und Spalten
    expand, control.expand = control.expand, None
    return ft.Semantics(button=True, container=True, selected=selected, expand=expand,
                        content=control)



def live(control):
    """Ab 0.59.1 (H1): Meldung, die nach einem Tippen erscheint (z.B.
    "Richtig beantwortet."). TalkBack liest sie vor, sobald sich der Text
    aendert (Live-Region, wie Statuszeile und Warnung im Spiel). Keine
    zusaetzliche Ansage, das Aussehen bleibt gleich. Ein- und ausgeblendet
    wird danach das umschliessende Element (Semantics ohne sichtbaren Inhalt
    zeigt sonst einen Fehlerhinweis)."""
    wrapper = ft.Semantics(live_region=True, container=True, content=control,
                           visible=control.visible)
    control.visible = True
    return wrapper


class GradientButton(ft.Container):
    """Knopf mit Farbverlauf (primary/accent/danger/success) oder als
    dezenter Rahmen-Knopf (kind='ghost')."""

    def __init__(self, caption, on_click=None, kind="primary", icon=None,
                 expand=None, height=46):
        self._kind = kind
        self._handler = on_click
        self.caption = ft.Text(caption, size=14, weight=ft.FontWeight.BOLD,
                               color=C["on_accent"] if kind != "ghost" else C["text"])
        row = [self.caption]
        if icon:
            row.insert(0, ft.Icon(icon, size=18,
                                  color=C["on_accent"] if kind != "ghost" else C["text"]))
        # Ab 0.59.1 (H1): Rolle "Schaltflaeche" mit dem Knopftext als Namen
        # (vorher meldete sich der Knopf nur als Flaeche). Die Rolle sitzt
        # innen, damit Rolle, Name und Antippen ein Element bleiben.
        super().__init__(
            content=ft.Semantics(button=True, content=ft.Row(
                row, spacing=8, tight=True, alignment=ft.MainAxisAlignment.CENTER)),
            height=grow(height), border_radius=grow(height) // 2,
            padding=ft.Padding.symmetric(horizontal=20),
            alignment=ft.Alignment.CENTER, expand=expand,
            on_click=self._clicked, ink=True)
        self._paint(True)

    def _paint(self, enabled):
        if self._kind == "ghost":
            self.gradient = None
            self.bgcolor = C["card_alt"]
            self.border = ft.Border.all(1, C["border_hi"])
        else:
            self.gradient = gradient(self._kind)
            self.border = None
        self.opacity = 1.0 if enabled else 0.4

    def _clicked(self, event):
        if self._handler and not self.disabled:
            self._handler(event)

    def set_enabled(self, flag):
        self.disabled = not flag
        self._paint(flag)

    def set_text(self, value):
        self.caption.value = value


class PillGroup(ft.Stack):
    """Sich gegenseitig ausschliessende Auswahl-Pillen, seitlich scrollbar.
    Ab 0.48: Passt die Reihe nicht auf den Bildschirm, laeuft sie rechts
    weich aus und ein Pfeil zeigt, dass es weitergeht (Tippen scrollt).

    Hinweis fuer alle Bausteine: In Ereignissen (Tippen) nie selbst update()
    aufrufen - sonst uebernimmt Flet danach die uebrigen Aenderungen der
    Seite nicht automatisch."""

    HINT_WIDTH = 34

    def __init__(self, options, on_change=None, initial=0):
        self.values = [value for value, _caption in options]
        self.on_select = on_change
        self.current = initial
        self.pills = []
        self.semantics = []
        height = grow(36)
        for index, (_value, caption) in enumerate(options):
            pill = ft.Container(
                content=ft.Text(caption, size=13, weight=ft.FontWeight.BOLD),
                height=height, border_radius=height // 2, alignment=ft.Alignment.CENTER,
                padding=ft.Padding.symmetric(horizontal=16), ink=True,
                on_click=lambda _e, i=index: self.select(i))
            self.pills.append(pill)
            # Ab 0.56: TalkBack sagt "Schaltflaeche" und ob die Pille gewaehlt ist
            self.semantics.append(ft.Semantics(content=pill, button=True, selected=False))
        # Geschaetzte Breiten (fett, 13 px: etwa 7,6 px je Zeichen)
        self._widths = [32 + 7.6 * FONT_FACTOR[0] * len(str(caption))
                        for _v, caption in options]
        self._captions = [caption for _v, caption in options]
        self._estimate = sum(self._widths) + 8 * max(0, len(options) - 1)
        self._placed = False
        self.row = ft.Row(self.semantics, spacing=8, scroll=ft.ScrollMode.HIDDEN,
                          on_scroll=self._scrolled, scroll_interval=50)
        self.mask = ft.ShaderMask(
            content=self.row, blend_mode=ft.BlendMode.DST_IN,
            shader=ft.LinearGradient(begin=ft.Alignment.CENTER_LEFT,
                                     end=ft.Alignment.CENTER_RIGHT,
                                     colors=[ft.Colors.WHITE, ft.Colors.WHITE,
                                             ft.Colors.TRANSPARENT],
                                     stops=[0.0, 0.86, 1.0]))
        self.hint = ft.Container(
            content=ft.Icon(ft.Icons.CHEVRON_RIGHT, size=20, color=C["text_dim"]),
            width=self.HINT_WIDTH, height=height, right=0, top=0,
            alignment=ft.Alignment.CENTER_RIGHT, on_click=self._step,
            tooltip="Weitere Einträge")
        super().__init__([self.mask, self.hint], height=height,
                         on_size_change=self._sized, size_change_interval=100)
        self._more = None
        self._overflow(False)
        self._paint()

    def _overflow(self, flag):
        """Rechten Auslauf und Pfeil zeigen, solange es rechts weitergeht."""
        self._more = flag
        self.hint.visible = flag
        self.mask.shader.colors = [ft.Colors.WHITE, ft.Colors.WHITE,
                                   ft.Colors.TRANSPARENT if flag else ft.Colors.WHITE]

    def _sized(self, event):
        # Erste Schaetzung, bevor der Nutzer scrollt
        width = getattr(event, "width", 0) or 0
        if width and self._estimate > width - 4:
            if not self._more:
                self._overflow(True)
                self.update()
            # Liegt die gewaehlte Pille ausserhalb (z.B. Firma > Zertifizierungen),
            # einmal dorthin scrollen
            start = sum(self._widths[:self.current]) + 8 * self.current
            if not self._placed and start + self._widths[self.current] > width - self.HINT_WIDTH:
                self._placed = True
                # Ab 0.53 Zielposition knapper geschaetzt (etwa 7 px je Zeichen)
                # und mit mehr Rand, damit die Pille links nicht angeschnitten ist
                left = sum(32 + 7.0 * len(str(caption))
                           for caption in self._captions[:self.current])
                self.page.run_task(self._scroll_to, max(0, left + 8 * self.current - 24))
        self._placed = True

    async def _scroll_to(self, offset):
        try:
            await self.row.scroll_to(offset=offset, duration=0)
        except Exception:
            pass

    def _scrolled(self, event):
        more = (getattr(event, "extent_after", 0) or 0) > 4
        if more != self._more:
            self._overflow(more)
            self.update()

    async def _step(self, _event):
        try:
            await self.row.scroll_to(delta=160, duration=250)
        except Exception:
            pass

    def _paint(self):
        for index, pill in enumerate(self.pills):
            active = index == self.current
            pill.gradient = gradient("primary") if active else None
            pill.bgcolor = None if active else C["card_alt"]
            pill.border = None if active else ft.Border.all(1, C["border"])
            pill.content.color = C["on_accent"] if active else C["text_dim"]
            self.semantics[index].selected = active

    def select(self, index, notify=True):
        self.current = index
        self._paint()
        if notify and self.on_select:
            self.on_select(self.values[index])

    def select_value(self, value, notify=True):
        if value in self.values:
            self.current = self.values.index(value)
            self._paint()
            if notify and self.on_select:
                self.on_select(value)

    def get(self):
        return self.values[self.current]


class OptionList(ft.Column):
    """Antwortzeilen zum Antippen, nach dem Pruefen gruen/rot markiert."""

    def __init__(self):
        super().__init__(spacing=8, tight=True)
        self._rows = []
        self.selected = None
        self.locked = False

    def set_options(self, options):
        self.controls.clear()
        self._rows = []
        self.selected = None
        self.locked = False
        for option in options:
            marker = ft.Container(width=20, height=20, border_radius=10)
            caption = ft.Text(option, size=15, expand=True)
            row = ft.Container(
                content=ft.Row([marker, caption], spacing=12,
                               vertical_alignment=ft.CrossAxisAlignment.CENTER),
                padding=ft.Padding.symmetric(horizontal=14, vertical=12),
                border_radius=12, ink=True,
                on_click=lambda _e, value=option: self.select(value))
            # Ab 0.56: TalkBack liest Antwort und Zustand (gewaehlt, richtig,
            # falsch) - die Farben allein sieht ein Screenreader nicht
            semantics = ft.Semantics(content=row, button=True, container=True,
                                     selected=False, label=option)
            entry = {"row": row, "marker": marker, "caption": caption,
                     "text": option, "state": "idle", "semantics": semantics}
            self._rows.append(entry)
            self._paint(entry)
            self.controls.append(semantics)

    def clear(self):
        self.set_options([])

    def select(self, value):
        if self.locked:
            return
        self.selected = value
        for entry in self._rows:
            entry["state"] = "selected" if entry["text"] == value else "idle"
            self._paint(entry)

    def get(self):
        return self.selected

    def reveal(self, correct_value):
        self.locked = True
        for entry in self._rows:
            if entry["text"] == correct_value:
                entry["state"] = "correct"
            elif entry["text"] == self.selected:
                entry["state"] = "wrong"
            else:
                entry["state"] = "muted"
            self._paint(entry)

    @staticmethod
    def _paint(entry):
        state = entry["state"]
        if state == "selected":
            bg, border, fg, dot = C["card_hi"], C["purple"], C["text"], C["purple"]
        elif state == "correct":
            bg, border, fg, dot = mix(C["card"], C["green"], 0.18), C["green"], C["text"], C["green"]
        elif state == "wrong":
            bg, border, fg, dot = mix(C["card"], C["red"], 0.18), C["red"], C["text"], C["red"]
        elif state == "muted":
            bg, border, fg, dot = C["card_alt"], C["border"], C["muted"], None
        else:
            bg, border, fg, dot = C["card_alt"], C["border"], C["text"], None
        strong = state in ("selected", "correct", "wrong")
        entry["row"].bgcolor = bg
        entry["row"].border = ft.Border.all(2 if strong else 1, border)
        entry["caption"].color = fg
        # Ab 0.56: Kreis der freien Antworten mit 3:1 (vorher border_hi)
        ring = border if state != "idle" else C["field_border"]
        entry["marker"].border = ft.Border.all(2, ring)
        semantics = entry.get("semantics")
        if semantics is not None:
            semantics.selected = state in ("selected", "wrong")
            semantics.label = entry["text"] + OPTION_STATE_TEXT.get(state, "")
        entry["marker"].content = ft.Container(
            width=10, height=10, border_radius=5, bgcolor=dot) if dot else None
        entry["marker"].alignment = ft.Alignment.CENTER


# Ab 0.56: Zustand einer Antwort fuer TalkBack
OPTION_STATE_TEXT = {"selected": ", ausgewählt", "correct": ", richtige Antwort",
                     "wrong": ", deine Antwort, falsch"}


class Stepper(ft.Row):
    """Zahl mit Minus- und Plus-Knopf."""

    def __init__(self, value=10, minimum=1, maximum=100, step=5):
        self.value = value
        self.minimum = minimum
        self.maximum = maximum
        self.step = step
        self.label = ft.Container(
            content=ft.Text(str(value), size=15, weight=ft.FontWeight.BOLD,
                            color=C["text"]),
            width=58, height=38, border_radius=10, bgcolor=C["card_alt"],
            alignment=ft.Alignment.CENTER)
        super().__init__([
            self._button(ft.Icons.REMOVE, -1), self.label,
            self._button(ft.Icons.ADD, 1)], spacing=6, tight=True)

    def _button(self, icon, direction):
        # Ab 0.56 mit Beschriftung fuer TalkBack (sonst nur "Schaltflaeche")
        return ft.Semantics(
            button=True, label="Weniger" if direction < 0 else "Mehr",
            content=ft.Container(
                content=ft.Icon(icon, size=18, color=C["text"]), width=38, height=38,
                border_radius=19, bgcolor=C["card_alt"], ink=True,
                border=ft.Border.all(1, C["border"]), alignment=ft.Alignment.CENTER,
                on_click=lambda _e: self.change(direction * self.step)))

    def change(self, delta):
        self.value = max(self.minimum, min(self.maximum, self.value + delta))
        self.label.content.value = str(self.value)

    def set_maximum(self, maximum):
        self.maximum = max(1, maximum)
        self.value = max(self.minimum, min(self.maximum, self.value))
        self.label.content.value = str(self.value)

    def get(self):
        return self.value


def entry(value="", hint=None, password=False, multiline=False, min_lines=1,
          max_lines=None, mono=False, keyboard=None, on_change=None, expand=None):
    """Dunkles, abgerundetes Eingabefeld. Bei password=True gibt es ab 0.48
    einen eigenen Augen-Knopf mit Beschriftung (auch fuer Screenreader)."""
    field = ft.TextField(
        value=value, hint_text=hint, password=password,
        multiline=multiline, min_lines=min_lines,
        max_lines=max_lines, keyboard_type=keyboard, on_change=on_change,
        bgcolor=C["card_alt"], filled=True, fill_color=C["card_alt"],
        border_color=C["field_border"], focused_border_color=C["purple"],
        border_radius=12, color=C["text"], cursor_color=C["accent"],
        hint_style=ft.TextStyle(color=C["muted"]),
        text_style=ft.TextStyle(font_family=MONO if mono else None, size=fs(14)),
        content_padding=ft.Padding.symmetric(horizontal=14, vertical=12),
        expand=expand)
    if password:
        def toggle(_event):
            field.password = not field.password
            eye.icon = ft.Icons.VISIBILITY_OFF if not field.password else ft.Icons.VISIBILITY
            eye.tooltip = "Verbergen" if not field.password else "Anzeigen"
        eye = ft.IconButton(icon=ft.Icons.VISIBILITY, icon_color=C["muted"],
                            tooltip="Anzeigen", on_click=toggle)
        field.suffix_icon = eye
    return field


def check_row(caption, value=False, on_change=None):
    """Haken mit mehrzeiliger Beschriftung (ab 0.51): ft.Checkbox bricht
    lange Texte nicht um. Auch das Tippen auf den Text setzt den Haken.
    on_change erhaelt den neuen Wert (True/False)."""
    box = ft.Checkbox(value=value, active_color=C["green"], check_color=C["on_accent"])

    def changed(_event=None):
        if on_change:
            on_change(bool(box.value))

    def toggle(_event):
        box.value = not box.value
        changed()

    box.on_change = changed
    return ft.Row([box, ft.Container(content=ft.Text(caption, size=13, color=C["text_soft"]),
                                     expand=True, on_click=toggle,
                                     padding=ft.Padding.symmetric(vertical=6))],
                  spacing=4, vertical_alignment=ft.CrossAxisAlignment.START)


def read_box(value="", mono=False):
    """Mehrzeiliger Text zum Lesen (Aufgaben, Loesungen, Rechenergebnisse)."""
    return ft.Container(
        content=ft.Text(value, size=13 if mono else 14, color=C["text_dim"],
                        font_family=MONO if mono else None, selectable=True),
        bgcolor=C["card_alt"], border_radius=12, padding=14,
        border=ft.Border.all(1, C["border"]))


def list_row(title, subtitle, accent, on_click, active=False, sub_color=None):
    """Antippbare Listenzeile mit farbiger Markierung links."""
    return ft.Container(
        content=ft.Row([
            ft.Container(width=4, height=34, border_radius=2, bgcolor=accent),
            ft.Column([
                ft.Text(title, size=14, weight=ft.FontWeight.BOLD,
                        color=C["text"] if active else C["text_dim"]),
                ft.Text(subtitle, size=12, color=sub_color or C["muted"]),
            ], spacing=2, tight=True, expand=True),
            ft.Icon(ft.Icons.CHEVRON_RIGHT, size=20, color=C["muted"]),
        ], spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        bgcolor=C["card_hi"] if active else C["card_alt"],
        border=ft.Border.all(1, C["purple"] if active else C["border"]),
        border_radius=12, padding=ft.Padding.symmetric(horizontal=12, vertical=10),
        ink=True, on_click=on_click)


def dot(color, size=9):
    return ft.Container(width=size, height=size, border_radius=size / 2, bgcolor=color)


# ============================================================================
#  BANNER, RINGE, BALKEN
# ============================================================================

class HeroPanel(ft.Container):
    """Farbverlaufs-Banner oben im Dashboard."""

    def __init__(self):
        self.title = ft.Text("", size=22, weight=ft.FontWeight.BOLD, color=C["on_accent"])
        self.sub = ft.Text("", size=13, color=mix(C["on_accent"], C["accent2"], 0.25))
        self.big = ft.Text("", size=30, weight=ft.FontWeight.BOLD, color=C["on_accent"])
        self.big_sub = ft.Text("", size=12, color=mix(C["on_accent"], C["accent2"], 0.25))
        super().__init__(
            content=ft.Row([
                ft.Column([self.title, self.sub], spacing=6, tight=True, expand=True),
                ft.Column([self.big, self.big_sub], spacing=0, tight=True,
                          horizontal_alignment=ft.CrossAxisAlignment.END),
            ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
            gradient=gradient("hero", ft.Alignment.TOP_LEFT, ft.Alignment.BOTTOM_RIGHT),
            border_radius=18, padding=20)

    def set_data(self, title, sub, big, big_sub):
        self.title.value = title
        self.sub.value = sub
        self.big.value = big
        self.big_sub.value = big_sub


class Ring(ft.Stack):
    """Fortschrittsring mit Farbverlauf und Text in der Mitte."""

    def __init__(self, size=120, thickness=11, big_size=22, small_size=11):
        self.size = size
        self.thickness = thickness
        self.canvas = cv.Canvas(width=size, height=size)
        self.big = ft.Text("", size=big_size, weight=ft.FontWeight.BOLD, color=C["text"],
                           text_align=ft.TextAlign.CENTER)
        self.small = ft.Text("", size=small_size, color=C["text_dim"],
                             text_align=ft.TextAlign.CENTER)
        center = ft.Container(
            content=ft.Column([self.big, self.small], spacing=0, tight=True,
                              horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            width=size, height=size, alignment=ft.Alignment.CENTER,
            padding=thickness + 6)
        # Ab 0.56: TalkBack liest den Ring als ein Element ("12 von 1565
        # Karten 1 Prozent") statt Zahl und Unterzeile einzeln
        self.semantics = ft.Semantics(content=self.canvas, container=True, label="")
        super().__init__([self.semantics, ft.Semantics(content=center,
                                                       exclude_semantics=True)],
                         width=size, height=size)

    def set(self, fraction, color_a, color_b=None, big="", small=""):
        fraction = max(0.0, min(1.0, fraction))
        color_b = color_b or color_a
        half = self.thickness / 2
        box = self.size - self.thickness
        shapes = [cv.Circle(self.size / 2, self.size / 2, box / 2, ft.Paint(
            color=C["ring_bg"], stroke_width=self.thickness,
            style=ft.PaintingStyle.STROKE))]
        # Ab 0.53 immer zwei Formen (Bogen bei 0 unsichtbar): Faellt ein Ring
        # auf 0, liess das Weglassen des Bogens den Flet-Client mit IndexError
        # abbrechen (z.B. Startseite nach "Sicherung einspielen > Alles ersetzen")
        if fraction <= 0:
            color_a = color_b = ft.Colors.TRANSPARENT
        sweep = max(0.02, fraction) * 2 * math.pi
        shapes.append(cv.Arc(
            half, half, box, box, start_angle=-math.pi / 2, sweep_angle=sweep,
            paint=ft.Paint(
                stroke_width=self.thickness, style=ft.PaintingStyle.STROKE,
                stroke_cap=ft.StrokeCap.ROUND,
                gradient=ft.PaintSweepGradient(
                    center=ft.Offset(self.size / 2, self.size / 2),
                    colors=[color_a, color_b, color_a if fraction >= 0.999 else color_b],
                    color_stops=[0.0, max(0.01, fraction), 1.0],
                    rotation=-math.pi / 2))))
        self.canvas.shapes = shapes
        self.big.value = big
        self.small.value = small
        parts = [part for part in (big, small if self.small.visible else "") if part]
        if parts and "%" not in big:
            parts.append("%d Prozent" % round(fraction * 100))
        self.semantics.label = " ".join(parts)


class GradientBar(ft.Column):
    """Beschriftung plus waagerechter Balken mit Farbverlauf."""

    def __init__(self, caption, color_a, color_b):
        self.colors = (color_a, color_b)
        self.value_text = ft.Text("", size=12, color=C["muted"])
        self.fill = ft.Container(height=8, border_radius=4,
                                 gradient=gradient((color_a, color_b)))
        self.rest = ft.Container(height=8)
        track = ft.Container(
            content=ft.Row([self.fill, self.rest], spacing=0),
            bgcolor=C["ring_bg"], border_radius=4, height=8)
        super().__init__([
            ft.Row([ft.Text(caption, size=13, color=C["text_dim"], expand=True),
                    self.value_text]),
            track,
        ], spacing=6, tight=True)

    def set(self, percent, value_text=""):
        share = int(round(max(0.0, min(100.0, percent)) * 10))
        self.fill.expand = share
        self.fill.visible = share > 0
        self.rest.expand = 1000 - share
        self.rest.visible = share < 1000
        self.value_text.value = value_text


# ============================================================================
#  DIAGRAMME
# ============================================================================

def _smooth(points, limits=None):
    """Weiche Kurve durch alle Punkte als Bezier-Segmente (wie am PC). Ab 0.56
    monoton (fisi_theme.curve_controls): kein Ueberschwingen ueber die
    Datenpunkte hinaus und nie unter die Nulllinie."""
    elements = [cv.Path.MoveTo(*points[0])]
    for p2, (c1, c2) in zip(points[1:], fisi_theme.curve_controls(points)):
        if limits:
            # Sicherheitsnetz: nie unter die Nulllinie bzw. ueber den Rand
            c1 = (c1[0], min(max(c1[1], limits[0]), limits[1]))
            c2 = (c2[0], min(max(c2[1], limits[0]), limits[1]))
        elements.append(cv.Path.CubicTo(c1[0], c1[1], c2[0], c2[1], p2[0], p2[1]))
    return elements


def _chart_number(value):
    return _fmt(round(value, 1)).replace(".", ",")


def chart_summary(labels, values, goal=None):
    """Ab 0.56: Diagramm als Text fuer TalkBack (alle Werte bis 14 Punkte,
    sonst Spanne, hoechster und letzter Wert)."""
    labels, values = list(labels), list(values)
    if not values:
        return "Diagramm ohne Werte"
    if len(values) <= 14:
        text = "Diagramm: " + ", ".join("%s %s" % (label, _chart_number(value))
                                         for label, value in zip(labels, values))
    else:
        top = max(range(len(values)), key=lambda index: values[index])
        text = ("Diagramm mit %d Werten von %s bis %s, höchster Wert %s (%s), letzter Wert %s"
                % (len(values), labels[0] if labels else "", labels[-1] if labels else "",
                   _chart_number(values[top]), labels[top] if top < len(labels) else "",
                   _chart_number(values[-1])))
    if goal:
        text += ", %s %s" % (goal[1], _chart_number(goal[0]))
    return text


class LineChart(ft.Semantics):
    """Ab 0.56: Liniendiagramm mit Beschriftung fuer TalkBack (die Zeichnung
    selbst kann ein Screenreader nicht lesen). Zeichnung: _LineCanvas."""

    def __init__(self, height=200):
        self.canvas = _LineCanvas(height)
        super().__init__(content=self.canvas, container=True, label="Diagramm ohne Werte")

    def set_data(self, labels, values, color, y_max=None, goal=None, name=None):
        self.canvas.set_data(labels, values, color, y_max, goal, name)
        self.label = chart_summary(labels, values, goal)


class _LineCanvas(cv.Canvas):
    """Liniendiagramm mit weicher Kurve und Verlaufsflaeche. Zeichnet sich bei
    jeder Groessenaenderung neu (Breite kommt vom Handy-Bildschirm)."""

    def __init__(self, height=200):
        self._labels = []
        self._series = []
        self._color = C["accent"]
        self._y_max = None
        self._goal = None
        self._name = None
        self._width = 300
        super().__init__(height=height, expand=True, on_resize=self._resized,
                         resize_interval=100)

    def _resized(self, event):
        self._width = event.width
        self._draw()
        self.update()

    def set_data(self, labels, values, color, y_max=None, goal=None, name=None):
        """goal (ab 0.54): (wert, text, farbe) zeichnet eine gestrichelte
        Ziellinie (z.B. das Tagesziel), wie am PC. name (ab 0.58): Legende
        oben links wie am PC (z.B. "Aufgaben")."""
        self._labels = list(labels)
        self._series = list(values)
        self._color = color
        self._y_max = y_max
        self._goal = goal
        self._name = name
        self._draw()

    def _draw(self):
        width, height = self._width, self.height
        # Ab 0.58 wachsen Achsenschrift, Legende und Raender mit der Schrift
        left, right, top, bottom = grow(30), 8, 10, grow(22)
        if self._goal or self._name:
            top = grow(26)   # Zeile fuer Legende und Ziellinie (ab 0.56/0.58)
        plot_w = max(10, width - left - right)
        plot_h = max(10, height - top - bottom)
        values = self._series or [0]
        peak = self._y_max or max(4, max(values), self._goal[0] * 1.1 if self._goal else 0)
        step = _nice_step(peak)
        peak = step * math.ceil(peak / step)

        shapes = []
        grid_paint = ft.Paint(color=C["border"], stroke_width=1)
        axis_style = ft.TextStyle(size=fs(10), color=C["muted"])
        legend_y = grow(9)
        tick = 0
        while tick <= peak + 0.001:
            y = top + plot_h - tick / peak * plot_h
            shapes.append(cv.Line(left, y, left + plot_w, y, grid_paint))
            shapes.append(cv.Text(left - 6, y, _fmt(tick), style=axis_style,
                                  alignment=ft.Alignment.CENTER_RIGHT))
            tick += step

        count = len(values)
        xs = [left + (plot_w * index / (count - 1) if count > 1 else plot_w / 2)
              for index in range(count)]
        points = [(x, top + plot_h - min(value, peak) / peak * plot_h)
                  for x, value in zip(xs, values)]
        if count > 1:
            curve = _smooth(points, (top, top + plot_h))
            area = curve + [cv.Path.LineTo(points[-1][0], top + plot_h),
                            cv.Path.LineTo(points[0][0], top + plot_h), cv.Path.Close()]
            shapes.append(cv.Path(area, paint=ft.Paint(
                style=ft.PaintingStyle.FILL,
                gradient=ft.PaintLinearGradient(
                    begin=ft.Offset(0, top), end=ft.Offset(0, top + plot_h),
                    colors=[ft.Colors.with_opacity(0.45, self._color),
                            ft.Colors.with_opacity(0.02, self._color)]))))
            shapes.append(cv.Path(curve, paint=ft.Paint(
                color=self._color, stroke_width=2.5, style=ft.PaintingStyle.STROKE,
                stroke_cap=ft.StrokeCap.ROUND, stroke_join=ft.StrokeJoin.ROUND)))
        for x, y in points:
            shapes.append(cv.Circle(x, y, 3, ft.Paint(color=self._color)))
        if self._goal and 0 < self._goal[0] <= peak:
            value, caption, color = self._goal
            y = top + plot_h - value / peak * plot_h
            shapes.append(cv.Line(left, y, left + plot_w, y, ft.Paint(
                color=color, stroke_width=1.5, stroke_dash_pattern=[6, 4])))
            # Ab 0.56 steht die Beschriftung mit einem Linienstueck oben rechts
            # ueber dem Diagramm, damit sie keine Kurve und keinen Punkt verdeckt
            shapes.append(cv.Text(left + plot_w, legend_y, caption,
                                  style=ft.TextStyle(size=fs(10), color=color),
                                  alignment=ft.Alignment.CENTER_RIGHT))
            sample = left + plot_w - len(caption) * 6 * FONT_FACTOR[0] - 8
            shapes.append(cv.Line(sample - 18, legend_y, sample, legend_y, ft.Paint(
                color=color, stroke_width=1.5, stroke_dash_pattern=[6, 4])))
        if self._name:
            # Ab 0.58: Legende wie am PC (Punkt in der Linienfarbe und Name)
            shapes.append(cv.Circle(left + 4, legend_y, 4, ft.Paint(color=self._color)))
            shapes.append(cv.Text(left + 13, legend_y, self._name,
                                  style=ft.TextStyle(size=fs(10), color=C["text_dim"]),
                                  alignment=ft.Alignment.CENTER_LEFT))

        # Beschriftung der x-Achse: ab 0.58 nach Textbreite ausgeduennt, vom
        # rechten Ende aus gezaehlt (fisi_theme.label_stride, wie am PC)
        widest = max([len(str(caption)) for caption in self._labels] or [1])
        stride = fisi_theme.label_stride(count, plot_w / max(1, count - 1),
                                         widest * 6 * FONT_FACTOR[0])
        shown = set(fisi_theme.shown_labels(count, stride))
        for index, (x, caption) in enumerate(zip(xs, self._labels)):
            last = index == count - 1
            if index in shown:
                # Die letzte Beschriftung endet am rechten Rand statt darueber
                shapes.append(cv.Text(x + (4 if last and count > 1 else 0),
                                      top + plot_h + grow(12),
                                      caption, style=axis_style,
                                      alignment=ft.Alignment.CENTER_RIGHT if last and count > 1
                                      else ft.Alignment.CENTER))
        self.shapes = shapes


class ShareBars(ft.Semantics):
    """Ab 0.56: Anteile richtig/falsch je Tag mit Beschriftung fuer TalkBack.
    Zeichnung: _ShareCanvas."""

    def __init__(self, height=190):
        self.canvas = _ShareCanvas(height)
        super().__init__(content=self.canvas, container=True, label="Diagramm ohne Werte")

    def set_data(self, data, names=None, empty=None):
        self.canvas.set_data(data, names, empty)
        right, wrong = self.canvas._names
        parts = []
        for label, share, rest in self.canvas._data:
            if share is None:
                parts.append("%s keine Aufgaben" % label)
            else:
                parts.append("%s %d Prozent %s, %d Prozent %s" % (label, share, right,
                                                                  rest, wrong))
        self.label = "Diagramm: " + "; ".join(parts) if parts else "Diagramm ohne Werte"


class _ShareCanvas(cv.Canvas):
    """Ab 0.56 (wie am PC): gestapelte Balken in Prozent je Tag, richtig unten
    (voll), falsch oben (schraffiert), Anteil richtig als Zahl ueber dem
    Balken, Tage ohne Aufgaben mit Strich."""

    def __init__(self, height=190):
        self._data = []
        self._names = ("richtig", "falsch")
        self._empty = "–"
        self._width = 300
        super().__init__(height=height, expand=True, on_resize=self._resized,
                         resize_interval=100)

    def _resized(self, event):
        self._width = event.width
        self._draw()
        self.update()

    def set_data(self, data, names=None, empty=None):
        self._data = list(data)
        if names:
            self._names = names
        if empty:
            self._empty = empty
        self._draw()

    def _draw(self):
        width, height = self._width, self.height
        # Ab 0.58 wachsen Achsenschrift, Legende und Raender mit der Schrift
        left, right, top, bottom = grow(38), 8, grow(34), grow(22)
        plot_w = max(10, width - left - right)
        plot_h = max(10, height - top - bottom)
        axis_style = ft.TextStyle(size=fs(10), color=C["muted"])
        shapes = []
        for line in range(5):
            y = top + plot_h - plot_h * line / 4
            shapes.append(cv.Line(left, y, left + plot_w, y,
                                  ft.Paint(color=C["border"], stroke_width=1)))
            shapes.append(cv.Text(left - 6, y, "%d %%" % (line * 25), style=axis_style,
                                  alignment=ft.Alignment.CENTER_RIGHT))
        count = max(1, len(self._data))
        slot = plot_w / count
        bar = max(3, min(26, slot * 0.62))
        widest = max([len(str(item[0])) for item in self._data] or [1])
        shown = set(fisi_theme.shown_labels(
            count, fisi_theme.label_stride(count, slot, widest * 6 * FONT_FACTOR[0])))
        right_paint = ft.Paint(color=C["green"])
        wrong_fill = ft.Paint(color=ft.Colors.with_opacity(0.35, C["red"]))
        wrong_line = ft.Paint(color=C["red"], stroke_width=1.5)
        for index, (label, share, rest) in enumerate(self._data):
            center = left + slot * (index + 0.5)
            x1 = center - bar / 2
            base = top + plot_h
            if share is None:
                shapes.append(cv.Text(center, base - 8, self._empty, style=axis_style,
                                      alignment=ft.Alignment.CENTER))
            else:
                split = base - plot_h * share / 100.0
                if share:
                    shapes.append(cv.Rect(x1, split, bar, base - split, paint=right_paint))
                if rest:
                    shapes.append(cv.Rect(x1, top, bar, split - top, paint=wrong_fill))
                    shapes.extend(_hatch(x1, top, bar, split - top, wrong_line))
                if count <= 14:
                    shapes.append(cv.Text(center, top - grow(8), "%d" % share,
                                          style=ft.TextStyle(size=fs(10), color=C["text_dim"]),
                                          alignment=ft.Alignment.CENTER))
            if index in shown:
                # Ab 0.58: nicht ueber den rechten Rand hinaus (grosse Schrift)
                half = len(str(label)) * 3 * FONT_FACTOR[0]
                shapes.append(cv.Text(min(center, width - half - 2), top + plot_h + grow(12),
                                      label, style=axis_style,
                                      alignment=ft.Alignment.CENTER))
        # Legende
        x = left
        for name, solid in ((self._names[0], True), (self._names[1], False)):
            legend_y = grow(9)
            if solid:
                shapes.append(cv.Rect(x, legend_y - 5, 12, 10, paint=right_paint))
            else:
                shapes.append(cv.Rect(x, legend_y - 5, 12, 10, paint=wrong_fill))
                shapes.extend(_hatch(x, legend_y - 5, 12, 10, wrong_line))
            shapes.append(cv.Text(x + 17, legend_y, name, style=ft.TextStyle(
                size=fs(11), color=C["text_dim"]), alignment=ft.Alignment.CENTER_LEFT))
            x += 30 + 7 * len(name) * FONT_FACTOR[0]
        self.shapes = shapes


def _hatch(x, y, w, h, paint, gap=6):
    """Schraege Linien in einem Rechteck (Schraffur fuer "falsch")."""
    lines = []
    offset = -h
    while offset < w:
        x1, y1 = x + offset, y + h
        x2, y2 = x + offset + h, y
        # auf das Rechteck zuschneiden
        if x1 < x:
            y1 -= x - x1
            x1 = x
        if x2 > x + w:
            y2 += x2 - (x + w)
            x2 = x + w
        if x2 > x1:
            lines.append(cv.Line(x1, y1, x2, y2, paint))
        offset += gap
    return lines


def _nice_step(peak):
    for step in (1, 2, 5, 10, 20, 25, 50, 100, 200, 500):
        if peak / step <= 4:
            return step
    return 1000


def _fmt(value):
    return str(int(value)) if float(value).is_integer() else "%.1f" % value


UPS_BAR_COLORS = {"ziel": "accent", "neu": "purple", "ok": "green", "knapp": "red"}


class UpsPicture(ft.Semantics):
    """Ab 0.58: Bild des USV-Rechners (wie am PC UpsDiagram): Last -> USV ->
    Akku untereinander, darunter die Laufzeit als Balken. Daten:
    fisi_core.ups_calculate()["bild"], Vorlesetext ups_picture_summary."""

    def __init__(self):
        self.column = ft.Column(spacing=6, tight=True)
        super().__init__(content=self.column, container=True, label="")

    def set_picture(self, picture, summary=""):
        self.label = summary
        boxes = (("LAST", picture["last"], picture["last_detail"], C["accent"], None),
                 ("USV", picture["usv"], picture["usv_detail"], C["purple"],
                  picture.get("auslastung")),
                 ("AKKU", picture["akku"], picture["akku_detail"], C["green"], None))
        controls = []
        for index, (title, value, detail, color, share) in enumerate(boxes):
            lines = [text(title, size=11, color=C["muted"], weight=ft.FontWeight.BOLD),
                     text(value, size=18, weight=ft.FontWeight.BOLD),
                     text(detail, size=12, color=C["text_dim"])]
            if share is not None:
                lines.append(self._load_bar(share, picture["grenze"]))
            controls.append(ft.Container(
                content=ft.Row([ft.Container(width=4, height=grow(52), bgcolor=color,
                                             border_radius=2),
                                ft.Column(lines, spacing=2, tight=True, expand=True)],
                               spacing=12),
                bgcolor=C["card_alt"], border=ft.Border.all(1, C["border"]),
                border_radius=12, padding=12))
            if index < 2:
                controls.append(ft.Row([ft.Icon(ft.Icons.ARROW_DOWNWARD, size=grow(18),
                                                color=C["muted"])],
                                       alignment=ft.MainAxisAlignment.CENTER))
        controls.append(ft.Container(height=4))
        for bar in picture["balken"]:
            color = C[UPS_BAR_COLORS[bar["art"]]]
            controls.append(ft.Row([text(bar["label"], size=12, color=C["text_dim"],
                                         expand=True),
                                    text(bar["text"], size=12)]))
            controls.append(self._bar(bar["anteil"], color))
        if picture.get("urteil"):
            good = picture["urteil"] == "passend"
            controls.append(text("Empfehlung: USV %s" % picture["urteil"], size=15,
                                 color=C["green"] if good else C["red"],
                                 weight=ft.FontWeight.BOLD))
        self.column.controls = controls

    @staticmethod
    def _bar(share, color, height=12):
        filled = max(0, min(1000, int(round(share * 1000))))
        parts = []
        if filled:
            parts.append(ft.Container(expand=filled, bgcolor=color))
        if filled < 1000:
            parts.append(ft.Container(expand=1000 - filled, bgcolor=C["ring_bg"]))
        return ft.Container(content=ft.Row(parts, spacing=0), height=height,
                            border_radius=height / 2,
                            clip_behavior=ft.ClipBehavior.ANTI_ALIAS)

    def _load_bar(self, share, limit):
        """Auslastung mit Strich bei der Grenze (80 %)."""
        good = share <= limit
        bar = self._bar(min(share, 100) / 100.0, C["green"] if good else C["red"], 6)
        mark = ft.Row([ft.Container(expand=int(limit)),
                       ft.Container(width=2, height=12, bgcolor=C["text"]),
                       ft.Container(expand=int(100 - limit))], spacing=0)
        return ft.Container(content=ft.Stack([ft.Container(content=bar, top=3, left=0,
                                                           right=0), mark], height=12),
                            margin=ft.Margin.only(top=4))


class Heatmap(ft.Column):
    """Aktivitaet je Fachbereich (oder Thema) und Tag als Kaestchen-Raster.
    on_click(index) macht die Zeilen antippbar (Reinzoom in die Themen)."""

    def set_data(self, rows, days, on_click=None, selected=None, label_width=78):
        peak = max([max(values) for _name, _color, values in rows] + [1])
        self.controls = []
        for index, (name, color, values) in enumerate(rows):
            cells = [ft.Container(
                height=18, expand=True, border_radius=4,
                bgcolor=mix(C["card_alt"], color, 0.18 + 0.82 * value / peak)
                if value else C["card_alt"])
                for value in values[-days:]]
            chosen = index == selected
            row = ft.Row([
                ft.Text(name, size=12, width=label_width,
                        color=color if chosen else C["text_dim"],
                        weight=ft.FontWeight.BOLD if chosen else None)] + cells,
                spacing=3)
            if on_click:
                row = ft.Container(content=row, border_radius=6,
                                   on_click=lambda _e, i=index: on_click(i))
            # Ab 0.56: Zeile fuer TalkBack als Text (Kaestchen sind nur Farbe)
            shown = values[-days:]
            row = ft.Semantics(content=row, container=True, button=bool(on_click),
                               selected=chosen, exclude_semantics=True,
                               label="%s: %d Aktivitäten an %d von %d Tagen" % (
                                   name, sum(shown), sum(1 for value in shown if value),
                                   len(shown)))
            self.controls.append(row)
        self.spacing = 8
        self.tight = True


class CalendarPanel(ft.Column):
    """Monatsuebersicht mit markierten Lerntagen und Blaettern."""

    MONTHS = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli",
              "August", "September", "Oktober", "November", "Dezember"]

    def __init__(self, provider):
        super().__init__(spacing=6, tight=True)
        self.provider = provider
        today = datetime.date.today()
        self.year, self.month = today.year, today.month

    def to_current_month(self):
        today = datetime.date.today()
        self.year, self.month = today.year, today.month

    def _shift(self, delta):
        month = self.month + delta
        self.year += (month - 1) // 12
        self.month = (month - 1) % 12 + 1
        self.refresh()

    def _arrow(self, icon, delta):
        # Standard Cyan, beim Druecken gruen wie die Kachel
        # "Fortschritt je Fachbereich" (wie am PC)
        return ft.IconButton(
            icon=icon, icon_size=18, width=34, height=34,
            tooltip="Vorheriger Monat" if delta < 0 else "Nächster Monat",   # ab 0.56
            style=ft.ButtonStyle(
                icon_color={ft.ControlState.PRESSED: C["green"],
                            ft.ControlState.DEFAULT: C["accent"]},
                bgcolor=C["card_alt"],
                overlay_color=mix(C["card_alt"], C["green"], 0.18),
                padding=0, shape=ft.CircleBorder()),
            on_click=lambda _e: self._shift(delta))

    def refresh(self):
        active = self.provider(self.year, self.month)
        today = datetime.date.today()
        head = ft.Row([
            self._arrow(ft.Icons.CHEVRON_LEFT, -1),
            ft.Text("%s %d" % (self.MONTHS[self.month - 1], self.year), size=15,
                    weight=ft.FontWeight.BOLD, color=C["text"], expand=True,
                    text_align=ft.TextAlign.CENTER),
            self._arrow(ft.Icons.CHEVRON_RIGHT, 1),
        ])
        names = ft.Row([ft.Text(name, size=11, expand=True, text_align=ft.TextAlign.CENTER,
                                color=C["accent2"] if index > 4 else C["muted"])
                        for index, name in enumerate("MDMDFSS")])
        rows = [head, names]
        for week in calendar.Calendar().monthdayscalendar(self.year, self.month):
            cells = []
            for index, day in enumerate(week):
                if not day:
                    cells.append(ft.Container(height=32, expand=True))
                    continue
                learned = day in active
                is_today = (self.year, self.month, day) == (today.year, today.month, today.day)
                cells.append(ft.Container(
                    content=ft.Container(
                        content=ft.Text(str(day), size=12, weight=ft.FontWeight.BOLD
                                        if learned else None,
                                        # ab 0.56: Lerntag nicht nur ueber die Farbe
                                        semantics_label="%d. %s%s%s" % (
                                            day, self.MONTHS[self.month - 1],
                                            ", gelernt" if learned else "",
                                            ", heute" if is_today else ""),
                                        color=C["sidebar"] if learned else
                                        (C["accent2"] if index > 4 else C["text_dim"])),
                        width=28, height=28, border_radius=14,
                        bgcolor=C["purple"] if learned else None,
                        border=ft.Border.all(2, C["accent"]) if is_today else None,
                        alignment=ft.Alignment.CENTER),
                    height=32, expand=True, alignment=ft.Alignment.CENTER))
            rows.append(ft.Row(cells, spacing=0))
        self.controls = rows


class ThemeProgress(ft.Column):
    """Fortschritt je Pruefungsthema (am PC eine Timeline mit Ringen)."""

    def set_data(self, items):
        self.controls = []
        for name, percent, color in items:
            ring = Ring(size=46, thickness=5, big_size=11, small_size=1)
            ring.set(percent / 100.0, color, mix(color, C["text"], 0.25),
                     "%d%%" % round(percent), "")
            ring.small.visible = False
            self.controls.append(ft.Row([
                ring, ft.Text(name, size=13, color=C["text_dim"], expand=True)],
                spacing=14, vertical_alignment=ft.CrossAxisAlignment.CENTER))
        self.spacing = 8
        self.tight = True
