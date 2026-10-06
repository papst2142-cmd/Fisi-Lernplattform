"""AT-SPI-Baum aller Anwendungen ausgeben (Rolle, Name, Zustaende)."""
import sys, pyatspi
WANT = {"focusable", "focused", "expanded", "expandable", "collapsed", "checked", "showing", "sensitive"}
def walk(acc, depth, out, maxd=40):
    try:
        role = acc.getRoleName(); name = acc.name or ""; desc = acc.description or ""
        states = [pyatspi.stateToString(s) for s in acc.getState().getStates()]
        st = ",".join(s for s in states if s in WANT)
    except Exception as exc:
        out.append("  " * depth + "?? %s" % exc); return
    out.append("%s[%s] %r%s {%s}" % ("  " * depth, role, name, (" desc=%r" % desc) if desc else "", st))
    if depth >= maxd: return
    for i in range(acc.childCount):
        try: walk(acc.getChildAtIndex(i), depth + 1, out)
        except Exception as exc: out.append("  " * (depth+1) + "?? %s" % exc)
desk = pyatspi.Registry.getDesktop(0)
out = []
for i in range(desk.childCount):
    app = desk.getChildAtIndex(i)
    if app is None: continue
    if len(sys.argv) > 1 and sys.argv[1].lower() not in (app.name or "").lower(): 
        out.append("(App %r uebersprungen)" % app.name); continue
    walk(app, 0, out)
print("\n".join(out) if out else "(keine Anwendung im AT-SPI-Baum)")
