"""Misst, ob im Fenster 'Update verfuegbar' die Knoepfe sichtbar sind
(Schriftgroesse Normal/Gross/Sehr gross). Nur lesen, nichts aendern."""
import sys, os, json
sys.path.insert(0, sys.argv[1])
size_id = sys.argv[2]; installable = sys.argv[3] == "1"; shot = sys.argv[4]
import customtkinter as ctk
import fisi_theme, fisi_widgets, fisi_update
fisi_theme.apply_font_size(size_id)
fisi_widgets.apply_ui_scale(fisi_theme.font_factor())
import app_gui
app_gui.apply_appearance()
root = ctk.CTk(); root.geometry("1200x800")
_ex=[x for x in os.environ.get('FONT_EXCLUDE','').split(',') if x]
_orig=fisi_widgets.tkfont.families
fisi_widgets.tkfont.families=lambda r=None: tuple(f for f in _orig(r) if f not in _ex)
fisi_widgets.setup_fonts(root)
print('Schrift:', fisi_widgets.F['family'])
class FakeApp: pass
app = FakeApp(); app.root = root
notes = open(sys.argv[5], encoding="utf-8").read()
info = fisi_update.UpdateInfo("0.59", notes, fisi_update.RELEASES_PAGE,
                              asset_name="x.deb" if installable else None,
                              asset_url="https://x/x.deb" if installable else None)
if installable:
    fisi_update.install_kind = lambda: "deb"
d = app_gui.UpdateDialog(app, info)
for _ in range(30):
    root.update(); root.after(50); 
import time; time.sleep(1); root.update()
def bottom(w):
    return w.winfo_rooty() + w.winfo_height()
res = {"size": size_id, "installable": installable,
       "fenster": [d.winfo_width(), d.winfo_height()],
       "fenster_unten": bottom(d),
       "knopf_haupt": [d.btn_main.winfo_ismapped(), d.btn_main.winfo_height(), bottom(d.btn_main)],
       "knopf_spaeter": [d.btn_later.winfo_ismapped(), d.btn_later.winfo_height(), bottom(d.btn_later)],
       "widget_scaling": ctk.ScalingTracker.widget_scaling,
       "window_scaling": ctk.ScalingTracker.window_scaling}
res["knoepfe_ganz_sichtbar"] = bool(d.btn_main.winfo_ismapped() and d.btn_main.winfo_height() > 5 and bottom(d.btn_main) <= bottom(d))
print(json.dumps(res))
try:
    from PIL import ImageGrab
    x, y = d.winfo_rootx(), d.winfo_rooty()
    ImageGrab.grab(bbox=(x, y, x + d.winfo_width(), y + d.winfo_height())).save(shot)
except Exception as e:
    print("kein Bild:", e)
root.destroy()
