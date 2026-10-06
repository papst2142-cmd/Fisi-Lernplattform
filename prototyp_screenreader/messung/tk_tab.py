"""Tab-Reihenfolge in CustomTkinter messen (tk_focusNext-Kette)."""
import tkinter as tk, customtkinter as ctk
root = ctk.CTk()
w = {"Label": ctk.CTkLabel(root, text="Updates"),
     "Button": ctk.CTkButton(root, text="Nach Updates suchen"),
     "Switch": ctk.CTkSwitch(root, text="Auto"),
     "Entry": ctk.CTkEntry(root),
     "SegmentedButton": ctk.CTkSegmentedButton(root, values=["Normal","Groß"]),
     "tk.Button": tk.Button(root, text="nativ")}
for x in w.values(): x.pack()
root.update()
names = {}
for k, x in w.items():
    for c in [x] + list(getattr(x, "winfo_children")()):
        names[str(c)] = "%s/%s" % (k, c.winfo_class())
seen, cur, chain = set(), root, []
for _ in range(30):
    nxt = cur.tk_focusNext()
    if nxt is None or str(nxt) in seen: break
    seen.add(str(nxt)); chain.append(names.get(str(nxt), str(nxt))); cur = nxt
print("Tab-Kette:", chain)
b = w["Button"]
print("Button Return-Bindung:", bool(b._text_label.bind("<Return>")), bool(b._canvas.bind("<Return>")), "space:", bool(b._canvas.bind("<space>")))
root.destroy()
