"""Tastatur-Ablauf im Prototyp messen (xdotool + AT-SPI)."""
import subprocess, time, sys
def key(k): subprocess.run(["xdotool", "key", k]); time.sleep(0.9)
def focus(): return subprocess.run(["python3.12", "focused.py"], capture_output=True, text=True).stdout.strip()
def tab_to(prefix, limit=40):
    for _ in range(limit):
        key("Tab"); f = focus()
        if prefix in f: return f
    return None
wid = subprocess.run(["xdotool", "search", "--name", "Screenreader-Prototyp"], capture_output=True, text=True).stdout.split()[0]
subprocess.run(["xdotool", "windowactivate", wid]); subprocess.run(["xdotool", "windowfocus", wid]); time.sleep(1)
print("== A: Tab-Reihenfolge Startzustand (alles zu ausser Updates/Problem melden)")
seen = []
for i in range(16):
    key("Tab"); f = focus(); print("Tab %2d: %s" % (i + 1, f))
    if f in seen[:1]: break
    seen.append(f)
print("== B: Farben mit Enter aufklappen")
print("Fokus:", tab_to("Farben,")); key("Return"); print("nach Enter:", focus())
print("== C: weiter mit Tab in den offenen Bereich")
for i in range(5): key("Tab"); print("Tab:", focus())
print("== D: Vorlagen mit Leertaste aufklappen")
print("Fokus:", tab_to("Vorlagen,")); key("space"); print("nach Leertaste:", focus())
subprocess.run("python3.12 dump_atspi.py > p_tree_vorlagen.txt", shell=True)
for i in range(3): key("Tab"); print("Tab:", focus())
print("== E: Shift+Tab zurueck zu Vorlagen, Enter = einklappen")
for i in range(3): key("shift+Tab")
print("Fokus:", focus()); key("Return"); print("nach Enter:", focus())
key("Tab"); print("naechstes Tab-Ziel nach Einklappen:", focus())
