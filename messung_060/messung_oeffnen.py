"""Messung 0.60 (Abnahme A2): erstes und zweites Oeffnen jeder Seite und jedes
Optionsbereichs, nach frischem Start und nach einem Darstellungswechsel.

Aufruf: python messung_oeffnen.py REPO AUSGABE.json VORLADEN(0/1)
VORLADEN=1: wie im Alltag, das Vorladen im Leerlauf ist fertig, bevor gemessen
wird. VORLADEN=0: Vorladen aus, also der ungünstigste Fall (sofort klicken).
Gemessen wird show_view bzw. open_area bis die Ereignisschleife leer ist
(update_idletasks + update), in ms."""
import json, os, shutil, sys, tempfile, time

repo, out, preload = sys.argv[1], sys.argv[2], sys.argv[3] == "1"
tmp = tempfile.mkdtemp()
os.environ["HOME"] = tmp
os.environ["APPDATA"] = tmp
os.environ["FISI_DB_PATH"] = os.path.join(tmp, "fisi.db")
beispiel = os.path.join(os.path.dirname(os.path.abspath(__file__)), "beispiel.db")
if os.path.exists(beispiel):
    shutil.copy(beispiel, os.environ["FISI_DB_PATH"])
sys.path.insert(0, repo)
os.chdir(repo)
import app_gui  # noqa: E402
import fisi_hilfe as fh  # noqa: E402
import fisi_optionen as fo  # noqa: E402
import fisi_theme  # noqa: E402
from fisi_update import load_settings, save_settings  # noqa: E402

s = load_settings(); s[fh.TOUR_SEEN_KEY] = True; save_settings(s)
app_gui.UpdateController.auto_check = lambda self: None
app_gui.SyncController.auto_start = lambda self: None
if not preload:
    app_gui.ViewPreloader.start = lambda self, delay=0: setattr(self, "done", True)
    app_gui.ViewPreloader.add_game = lambda self: None

root = app_gui.ctk.CTk()
root.geometry("1360x880+0+0")
t_start = time.perf_counter()
app = app_gui.FISIApp(root)
root.maxsize(4000, 3000)
root.geometry("1360x880+0+0")


def pump(sec):
    end = time.monotonic() + sec
    while time.monotonic() < end:
        root.update()
        time.sleep(0.01)


def settle():
    root.update_idletasks()
    root.update()


def wait_preload():
    if not preload:
        pump(1.0)
        return
    end = time.monotonic() + 180
    while time.monotonic() < end and not app.preloader.done:
        root.update()
        time.sleep(0.01)
    pump(1.0)


def timed(action):
    t0 = time.perf_counter()
    action()
    settle()
    return round((time.perf_counter() - t0) * 1000)


PAGES = [key for key, _i, _t, _s in app_gui.NAV_ITEMS if key != "dashboard"]


def round_of(name):
    wait_preload()
    res = {"seiten_1": {}, "seiten_2": {}, "bereiche_1": {}, "bereiche_2": {}}
    for nr in (1, 2):
        for key in PAGES:
            res["seiten_%d" % nr][key] = timed(lambda k=key: app.show_view(k))
            res["seiten_%d" % nr]["dashboard_zurueck_" + key] = timed(
                lambda: app.show_view("dashboard"))
    app.show_view("settings")
    settle()
    view = app.views["settings"]
    for nr in (1, 2):
        view.reset_folds()
        settle()
        for area in fo.areas(True):
            if area["id"] not in view.folds:
                continue
            res["bereiche_%d" % nr][area["id"]] = timed(
                lambda a=area["id"]: view.open_area(a))
            view.folds[area["id"]].set_opened(False)
            settle()
    app.show_view("dashboard")
    settle()
    return res


result = {"vorladen": preload, "start_ms": None}
pump(0.5)
result["start_ms"] = round((time.perf_counter() - t_start) * 1000)
result["frisch"] = round_of("frisch")
other = fisi_theme.MODE_LIGHT if not fisi_theme.light else fisi_theme.MODE_DARK
result["wechsel_ms"] = timed(lambda: app.change_color(mode=other))
result["nach_wechsel"] = round_of("nach_wechsel")
json.dump(result, open(out, "w", encoding="utf-8"), indent=1)


def short(d):
    return " ".join("%s=%d" % (k[:6], v) for k, v in d.items() if not k.startswith("dash"))


for teil in ("frisch", "nach_wechsel"):
    r = result[teil]
    print("ERG %s v%d S1 %s" % (teil, preload, short(r["seiten_1"])))
    print("ERG %s v%d S2 %s" % (teil, preload, short(r["seiten_2"])))
    print("ERG %s v%d B1 %s" % (teil, preload, short(r["bereiche_1"])))
    print("ERG %s v%d B2 %s" % (teil, preload, short(r["bereiche_2"])))
sys.stdout.flush()
os._exit(0)
