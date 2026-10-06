import pyatspi
def find(acc):
    try:
        st = acc.getState()
        if st.contains(pyatspi.STATE_FOCUSED) and acc.getRoleName() != "panel" or (st.contains(pyatspi.STATE_FOCUSED) and acc.name):
            states = [pyatspi.stateToString(s) for s in st.getStates()]
            return "[%s] %r %s" % (acc.getRoleName(), acc.name, [s for s in states if s in ("expanded","expandable","collapsed","checked","pressed")])
        for i in range(acc.childCount):
            r = find(acc.getChildAtIndex(i))
            if r: return r
    except Exception: return None
d = pyatspi.Registry.getDesktop(0)
print(next((r for r in (find(d.getChildAtIndex(i)) for i in range(d.childCount)) if r), "(kein Fokus gefunden)"))
