#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FISI Lernplattform - einfacher PDF-Export (ab 0.51)
===================================================

Erzeugt ein schlichtes A4-PDF mit Ueberschriften, Absaetzen und Listen -
nur mit der Standardbibliothek, damit PC und Handy dasselbe nutzen und der
APK-Bau keinen Zusatzbaustein braucht. Schrift ist die eingebaute Helvetica
(WinAnsi-Zeichensatz: Umlaute, ss, Euro, Anfuehrungszeichen gehen).

    data = build_pdf([("h1", "Titel"), ("p", "Text ..."), ("li", "Punkt")],
                     title="Abschlussprojekt")
"""

import datetime
import zlib

PAGE_W, PAGE_H = 595.28, 841.89
MARGIN = 56
FOOTER = 30

# Zeichenbreiten (1/1000 em) fuer die Codes 32-255 in WinAnsi (cp1252),
# aus den Standard-Metriken der Helvetica
_WIDTHS = {
    "Helvetica": [
    278, 278, 355, 556, 556, 889, 667, 191, 333, 333, 389, 584, 278, 333, 278, 278,
    556, 556, 556, 556, 556, 556, 556, 556, 556, 556, 278, 278, 584, 584, 584, 556,
    1015, 667, 667, 722, 722, 667, 611, 778, 722, 278, 500, 667, 556, 833, 722, 778,
    667, 778, 722, 667, 611, 722, 667, 944, 667, 667, 611, 278, 278, 278, 469, 556,
    333, 556, 556, 500, 556, 556, 278, 556, 556, 222, 222, 500, 222, 833, 556, 556,
    556, 556, 333, 500, 278, 556, 500, 722, 500, 500, 500, 334, 260, 334, 584, 761,
    556, 0, 222, 556, 333, 1000, 556, 556, 333, 1000, 667, 333, 1000, 0, 611, 0,
    0, 222, 222, 333, 333, 350, 556, 1000, 333, 1000, 500, 333, 944, 0, 500, 667,
    278, 333, 556, 556, 556, 556, 260, 556, 333, 737, 370, 556, 584, 333, 737, 333,
    400, 584, 333, 333, 333, 556, 537, 278, 333, 333, 365, 556, 834, 834, 834, 611,
    667, 667, 667, 667, 667, 667, 1000, 722, 667, 667, 667, 667, 278, 278, 278, 278,
    722, 722, 778, 778, 778, 778, 778, 584, 778, 722, 722, 722, 722, 667, 667, 611,
    556, 556, 556, 556, 556, 556, 889, 500, 556, 556, 556, 556, 278, 278, 278, 278,
    556, 556, 556, 556, 556, 556, 556, 584, 611, 556, 556, 556, 556, 500, 556, 500,
    ],
    "Helvetica-Bold": [
    278, 333, 474, 556, 556, 889, 722, 238, 333, 333, 389, 584, 278, 333, 278, 278,
    556, 556, 556, 556, 556, 556, 556, 556, 556, 556, 333, 333, 584, 584, 584, 611,
    975, 722, 722, 722, 722, 667, 611, 778, 722, 278, 556, 722, 611, 833, 722, 778,
    667, 778, 722, 667, 611, 722, 667, 944, 667, 667, 611, 333, 278, 333, 584, 556,
    333, 556, 611, 556, 611, 556, 333, 611, 611, 278, 278, 556, 278, 889, 611, 611,
    611, 611, 389, 556, 333, 611, 556, 778, 556, 556, 500, 389, 280, 389, 584, 761,
    556, 0, 278, 556, 500, 1000, 556, 556, 333, 1000, 667, 333, 1000, 0, 611, 0,
    0, 278, 278, 500, 500, 350, 556, 1000, 333, 1000, 556, 333, 944, 0, 500, 667,
    278, 333, 556, 556, 556, 556, 280, 556, 333, 737, 370, 556, 584, 333, 737, 333,
    400, 584, 333, 333, 333, 611, 556, 278, 333, 333, 365, 556, 834, 834, 834, 611,
    722, 722, 722, 722, 722, 722, 1000, 722, 667, 667, 667, 667, 278, 278, 278, 278,
    722, 722, 778, 778, 778, 778, 778, 584, 778, 722, 722, 722, 722, 667, 667, 611,
    556, 556, 556, 556, 556, 556, 889, 556, 556, 556, 556, 556, 278, 278, 278, 278,
    611, 611, 611, 611, 611, 611, 611, 584, 611, 611, 611, 611, 611, 556, 611, 556,
    ],
}

STYLES = {
    # art: (Schrift, Groesse, Abstand davor, Abstand danach, Einzug)
    "h1": ("Helvetica-Bold", 18, 6, 10, 0),
    "h2": ("Helvetica-Bold", 13, 12, 6, 0),
    "h3": ("Helvetica-Bold", 11, 8, 3, 0),
    "p": ("Helvetica", 10.5, 0, 6, 0),
    "li": ("Helvetica", 10.5, 0, 3, 14),
    "small": ("Helvetica", 9, 0, 4, 0),
}

_REPLACE = {"\u2192": "->", "\u2190": "<-", "\u2264": "<=", "\u2265": ">=",
            "\u2713": "x", "\u2717": "-", "\u2022": "\u2022", "\u00a0": " ",
            "\u2011": "-", "\u202f": " ", "\u2212": "-", "\u221a": "Wurzel "}


def _encode(text):
    text = "".join(_REPLACE.get(ch, ch) for ch in str(text))
    return text.encode("cp1252", errors="replace")


def text_width(text, font, size):
    widths = _WIDTHS[font]
    total = 0
    for code in _encode(text):
        total += widths[code - 32] if 32 <= code <= 255 and widths[code - 32] else 556
    return total * size / 1000.0


def wrap(text, font, size, width):
    """Bricht einen Absatz in Zeilen um (Woerter, zu lange Woerter hart)."""
    lines = []
    for paragraph in str(text).split("\n"):
        words = paragraph.split(" ")
        line = ""
        for word in words:
            candidate = word if not line else line + " " + word
            if text_width(candidate, font, size) <= width:
                line = candidate
                continue
            if line:
                lines.append(line)
            while text_width(word, font, size) > width and len(word) > 1:
                cut = len(word)
                while cut > 1 and text_width(word[:cut], font, size) > width:
                    cut -= 1
                lines.append(word[:cut])
                word = word[cut:]
            line = word
        lines.append(line)
    return lines


def _escape(data):
    return data.replace(b"\\", b"\\\\").replace(b"(", b"\\(").replace(b")", b"\\)")


def build_pdf(blocks, title="", author=""):
    """blocks: Liste (art, text) mit art aus STYLES oder ("space", punkte).
    Liefert die PDF-Datei als bytes."""
    pages = []
    ops = []
    y = PAGE_H - MARGIN
    usable = PAGE_W - 2 * MARGIN

    def new_page():
        nonlocal ops, y
        ops = []
        pages.append(ops)
        y = PAGE_H - MARGIN

    new_page()
    for kind, value in blocks:
        if kind == "space":
            y -= float(value)
            continue
        if kind == "pagebreak":
            new_page()
            continue
        font, size, before, after, indent = STYLES[kind]
        leading = size * 1.35
        text = str(value)
        prefix = ""
        if kind == "li":
            prefix = "\u2022"
        lines = wrap(text, font, size, usable - indent) if text else [""]
        y -= before
        # Ueberschrift nicht allein unten auf der Seite
        need = leading * (2 if kind.startswith("h") else 1)
        for number, line in enumerate(lines):
            if y - need < MARGIN + FOOTER:
                new_page()
            need = leading
            y -= leading
            x = MARGIN + indent
            name = "F2" if font == "Helvetica-Bold" else "F1"
            if prefix and number == 0:
                ops.append(b"BT /F1 %.1f Tf %.2f %.2f Td (%s) Tj ET" % (
                    size, MARGIN + 3, y, _escape(_encode(prefix))))
            ops.append(b"BT /%s %.1f Tf %.2f %.2f Td (%s) Tj ET" % (
                name.encode(), size, x, y, _escape(_encode(line))))
        y -= after

    # Seitenzahlen und Fusszeile
    total = len(pages)
    stamp = datetime.date.today().strftime("%d.%m.%Y")
    for number, page_ops in enumerate(pages, start=1):
        footer = "%s  \u00b7  Seite %d von %d  \u00b7  %s" % (title, number, total, stamp)
        page_ops.append(b"0.45 g BT /F1 8 Tf %.2f %.2f Td (%s) Tj ET 0 g" % (
            MARGIN, MARGIN - 20, _escape(_encode(footer.strip(" \u00b7")))))

    objects = []

    def add(content):
        objects.append(content)
        return len(objects)

    catalog = add(None)
    pages_id = add(None)
    font1 = add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica "
                b"/Encoding /WinAnsiEncoding >>")
    font2 = add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold "
                b"/Encoding /WinAnsiEncoding >>")
    kids = []
    for page_ops in pages:
        stream = zlib.compress(b"\n".join(page_ops))
        content = add(b"<< /Length %d /Filter /FlateDecode >>\nstream\n%s\nendstream" % (
            len(stream), stream))
        kids.append(add(b"<< /Type /Page /Parent %d 0 R /MediaBox [0 0 %.2f %.2f] "
                        b"/Resources << /Font << /F1 %d 0 R /F2 %d 0 R >> >> "
                        b"/Contents %d 0 R >>" % (pages_id, PAGE_W, PAGE_H, font1,
                                                 font2, content)))
    objects[catalog - 1] = b"<< /Type /Catalog /Pages %d 0 R >>" % pages_id
    objects[pages_id - 1] = b"<< /Type /Pages /Kids [%s] /Count %d >>" % (
        b" ".join(b"%d 0 R" % kid for kid in kids), len(kids))
    info = add(b"<< /Title (%s) /Author (%s) /Producer (FISI Lernplattform) >>" % (
        _escape(_encode(title)), _escape(_encode(author))))

    out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = []
    for number, content in enumerate(objects, start=1):
        offsets.append(len(out))
        out += b"%d 0 obj\n%s\nendobj\n" % (number, content)
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1)
    for offset in offsets:
        out += b"%010d 00000 n \n" % offset
    out += (b"trailer\n<< /Size %d /Root %d 0 R /Info %d 0 R >>\nstartxref\n%d\n%%%%EOF\n"
            % (len(objects) + 1, catalog, info, xref))
    return bytes(out)
