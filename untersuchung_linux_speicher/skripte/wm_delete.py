#!/usr/bin/env python3
"""Schickt allen Fenstern mit der WM_CLASS-Instanz ARG die Nachricht
WM_DELETE_WINDOW - dasselbe, was ein Klick auf das X am Fensterrahmen
ausloest. Braucht python-xlib."""
import sys
from Xlib import X, display, protocol

d = display.Display()
wm_protocols = d.intern_atom("WM_PROTOCOLS")
wm_delete = d.intern_atom("WM_DELETE_WINDOW")


def walk(window):
    try:
        children = window.query_tree().children
    except Exception:
        return
    for child in children:
        yield child
        yield from walk(child)


sent = 0
for win in walk(d.screen().root):
    try:
        cls = win.get_wm_class()
    except Exception:
        cls = None
    if cls and cls[0] == sys.argv[1]:
        event = protocol.event.ClientMessage(window=win, client_type=wm_protocols,
                                             data=(32, [wm_delete, X.CurrentTime, 0, 0, 0]))
        win.send_event(event)
        sent += 1
d.flush()
print("WM_DELETE_WINDOW an %d Fenster geschickt" % sent)
