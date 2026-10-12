#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T7 0.63: Messung Rechner vorher/nachher (nur Messung, kein Teil des Programms).

Erweiterung von plan_0.63/werkzeuge/mess_rechner_063.py (Plan 0.63 Abschnitt
8.1 bis 8.3). Startet eine Programmfassung (Ordner als Argument) mit leerer
Wegwerf-Datenbank und eigenem HOME und misst:

  beide Fassungen
    oeffnen_ms         Rechner oeffnen (erstes Mal), FISI_VORLADEN wie gesetzt
    wieder_ms          Rechner erneut oeffnen (von der Startseite aus)
    reiter_einzeln_ms  6 Wechsel Rechner <-> Trainer, reiter_ms = Mittel
    rechnen_ms         "Berechnen" IPv4 192.168.1.50/24 (Netzdaten)
    rechnen6_ms        "Berechnen" IPv6 2001:db8:abcd::/48 (Netzdaten)
    rechenweg_ms       Rechenweg Subnetting (IPv4) einblenden
  nur nachher (Subnetting-Karte SubnetCalc mit Schalter IPv4/IPv6)
    ipv6_vorgebaut     IPv6-Teil vor dem ersten Wechsel schon gebaut?
    erster_wechsel_ms  erster Wechsel IPv4 -> IPv6 (ohne Vorladen: baut)
    modus_einzeln_ms   6 Moduswechsel IPv6 <-> IPv4 ueber den Schalter,
                       modus_ms = Mittel
    rechenweg6_ms      Rechenweg IPv6 Netzdaten einblenden
    blaettern          "Netz aufteilen" mit grossen Netzen (T-K-6): Berechnen
                       und je Seite letzte/zurueck/erste/weiter (mit Oberflaeche)
    kern               dieselben Faelle ohne Oberflaeche (Plan 8.2: jede Seite
                       unter 50 ms): split_network, split_report je Seite

Bricht mit Rueckgabe 3 ab (und schreibt KEINE Ergebnisdatei), wenn ein
erwarteter Schalter oder ein erwartetes Element fehlt, eine Fehlermeldung
kaeme oder ein Wechsel nicht wirkt - es misst nie still nichts.

Aufruf: MESS_FASSUNG=vor|nach FISI_VORLADEN=0|normal \\
        python mess_rechner_063.py ORDNER AUSGABE.json
Ausgabe zusaetzlich eine Zeile "ERG ..."."""
import json
import os
import sys
import tempfile
import time
import traceback

SRC = os.path.abspath(sys.argv[1])
OUT = os.path.abspath(sys.argv[2])
FASSUNG = os.environ.get("MESS_FASSUNG", "")
if FASSUNG not in ("vor", "nach"):
    print("ABBRUCH: MESS_FASSUNG=vor|nach fehlt (%r)" % FASSUNG)
    sys.stdout.flush()
    os._exit(3)
folder = tempfile.mkdtemp(prefix="fisi mess063 ")
os.environ["FISI_DB_PATH"] = os.path.join(folder, "test.db")
os.environ["FISI_SELFTEST"] = os.path.join(folder, "log.txt")
os.environ["HOME"] = folder
os.environ["APPDATA"] = folder
os.environ["USERPROFILE"] = folder
sys.path.insert(0, SRC)
os.chdir(SRC)
import customtkinter as ctk  # noqa: E402
import app_gui  # noqa: E402


class Fehlt(Exception):
    pass


def need(cond, what):
    if not cond:
        raise Fehlt(what)


MELDUNGEN = []


def _keine_meldung(title, text, *a, **k):
    # Eine Fehlermeldung wuerde unter Xvfb/CI blockieren und hiesse: die
    # Eingabe kam nicht an -> nie still weitermessen
    MELDUNGEN.append("%s: %s" % (title, text))
    raise Fehlt("Fehlermeldung statt Ergebnis: %s: %s" % (title, text))


app_gui.messagebox.showerror = _keine_meldung
app_gui.messagebox.showwarning = _keine_meldung
app_gui.UpdateController.auto_check = lambda self: None
app_gui.SyncController.auto_start = lambda self: None
app_gui.apply_appearance()
root = ctk.CTk()
app = app_gui.FISIApp(root)
root.geometry("1360x880+0+0")


def settle():
    root.update_idletasks()
    root.update()


def timed(action):
    a = time.perf_counter()
    action()
    settle()
    return round((time.perf_counter() - a) * 1000, 1)


def text_of(widget):
    return widget.get("1.0", "end-1c")


def abbruch(grund):
    print("ABBRUCH (%s, FISI_VORLADEN=%s): %s" % (FASSUNG, os.environ.get("FISI_VORLADEN", "normal"), grund))
    sys.stdout.flush()
    os._exit(3)


end = time.monotonic() + 240
while time.monotonic() < end and not app.preloader.done:
    root.update()
    time.sleep(0.005)
end = time.monotonic() + 0.5
while time.monotonic() < end:
    root.update()
    time.sleep(0.01)

VORLADEN = os.environ.get("FISI_VORLADEN", "normal")
res = {"fassung": FASSUNG, "version": app_gui.APP_VERSION, "vorladen": VORLADEN,
       "vorladen_fertig": bool(app.preloader.done),
       "calc_vorgeladen": app.views.built("calc") is not None}


def gemeinsam(view):
    res["oeffnen_ms"] = timed(lambda: app.show_view("calc"))
    view = app.views["calc"]
    timed(lambda: app.show_view("dashboard"))
    res["wieder_ms"] = timed(lambda: app.show_view("calc"))
    need(app.current == "calc", "Rechner nicht offen")
    need(hasattr(view, "_on_tab"), "Reiter Rechner/Trainer (_on_tab)")
    wechsel = []
    for _ in range(3):
        wechsel.append(timed(lambda: view._on_tab("trainer")))
        wechsel.append(timed(lambda: view._on_tab("rechner")))
    need(view.calc_layout.winfo_manager() == "pack", "Rechner nach Reiterwechsel nicht sichtbar")
    res["reiter_einzeln_ms"] = wechsel
    res["reiter_ms"] = round(sum(wechsel) / len(wechsel), 1)
    return view


def messe_vor():
    view = app.views["calc"] if app.views.built("calc") is not None else None
    view = gemeinsam(view)
    need(not hasattr(view, "subnet"), "Fassung vor hat schon SubnetCalc (falscher Stand?)")
    for name in ("calc_subnet", "entry_ip", "txt_subnet", "toggle_info"):
        need(hasattr(view, name), "Element %s fehlt (vorher)" % name)
    need("subnet" in view.info_frames, "Rechenweg 'subnet' fehlt (vorher)")
    view.entry_ip.set("192.168.1.50/24")
    res["rechnen_ms"] = timed(view.calc_subnet)
    need("192.168.1." in text_of(view.txt_subnet), "IPv4-Ergebnis fehlt")
    view.entry_ip.set("2001:db8:abcd::/48")
    need(view.entry_ip.get() == "2001:db8:abcd::/48", "IPv6-Eingabe nicht gesetzt")
    res["rechnen6_ms"] = timed(view.calc_subnet)
    need("2001:db8:abcd" in text_of(view.txt_subnet), "IPv6-Ergebnis fehlt")
    res["ipv6_eingabe_geprueft"] = True
    need(not view.info_visible["subnet"], "Rechenweg schon offen")
    res["rechenweg_ms"] = timed(lambda: view.toggle_info("subnet"))
    need(view.info_visible["subnet"], "Rechenweg nicht aufgeklappt")


def blaettern(sub, mode, netz, anzahl):
    """Netz aufteilen mit grossem Netz, dann letzte/zurueck/erste/weiter."""
    if sub.mode != mode:
        sub.mode_pills.select_value(mode)
        settle()
    need(sub.mode == mode, "Moduswechsel nach %s fuer Blaettern" % mode)
    need("aufteilen" in sub.view_pills[mode].values, "Ansicht 'Netz aufteilen' fehlt (%s)" % mode)
    sub.view_pills[mode].select_value("aufteilen")
    settle()
    view = sub.views[(mode, "aufteilen")]
    need(sub.view_of[mode] == "aufteilen" and view["frame"].winfo_manager() == "pack",
         "Ansicht 'Netz aufteilen' nicht sichtbar (%s)" % mode)
    view["net"].set(netz)
    view["count"].set(str(anzahl))
    out = {"netz": netz, "anzahl": anzahl}
    out["berechnen_ms"] = timed(lambda: sub.calc(mode, "aufteilen"))
    need(view["result"] is not None, "kein Ergebnis Netz aufteilen %s" % netz)
    seiten = view["result"]["seiten"]
    need(seiten > 1 and view["pager"].winfo_manager() == "pack", "Blaettern nicht sichtbar (%s)" % netz)
    out["seiten"] = seiten
    schritte = {}
    for name, soll in (("letzte", seiten), ("zurueck", seiten - 1), ("erste", 1), ("weiter", 2)):
        knopf = {"letzte": "last", "zurueck": "back", "erste": "first", "weiter": "next"}[name]
        need(knopf in view["pager_buttons"], "Knopf %s fehlt" % knopf)
        schritte[name] = timed(lambda k=knopf: sub.turn(view, k))
        need(view["page"] == soll, "Seite nach %s: %s statt %s" % (name, view["page"], soll))
    out["seite_ms"] = schritte
    return out


def kern():
    """T-K-6-Faelle ohne Oberflaeche: je Seite eigene Zeit."""
    fc = app_gui.fisi_core
    for name in ("split_network", "split_page", "split_report", "subnet_by_hosts", "hosts_report"):
        need(hasattr(fc, name), "Kernfunktion %s fehlt" % name)
    faelle = []
    for netz, anzahl in (("::/0", 2 ** 64), ("10.0.0.0/8", 2 ** 24), ("::/0", 2 ** 127),
                         ("2001:db8::/32", 2 ** 32), ("0.0.0.0/0", 2 ** 32), ("::/0", 2 ** 128)):
        f = {"netz": netz, "anzahl": "2^%d" % (anzahl.bit_length() - 1)}
        a = time.perf_counter()
        r = fc.split_network(netz, anzahl)
        f["rechnen_ms"] = round((time.perf_counter() - a) * 1000, 2)
        for name, seite in (("seite1", 1), ("letzte", r["seiten"]), ("mitte", r["seiten"] // 2)):
            a = time.perf_counter()
            fc.split_report(r, seite)
            f[name + "_ms"] = round((time.perf_counter() - a) * 1000, 2)
            a = time.perf_counter()
            fc.split_report(r, seite, schmal=True)
            f[name + "_schmal_ms"] = round((time.perf_counter() - a) * 1000, 2)
        faelle.append(f)
    a = time.perf_counter()
    r = fc.subnet_by_hosts("0.0.0.0/0", "\n".join(str(2 ** (31 - i)) for i in range(12)))
    fc.hosts_report(r)
    faelle.append({"netz": "0.0.0.0/0", "anzahl": "Hostbedarf 12",
                   "rechnen_ms": round((time.perf_counter() - a) * 1000, 2)})
    return faelle


def messe_nach():
    view = gemeinsam(None)
    need(hasattr(view, "subnet"), "Subnetting-Karte (CalcView.subnet) fehlt (nachher)")
    sub = view.subnet
    for name in ("mode_pills", "mode_frames", "views", "view_pills", "calc", "toggle_info",
                 "set_mode", "turn", "built"):
        need(hasattr(sub, name), "SubnetCalc.%s fehlt" % name)
    need(list(sub.mode_pills.values) == ["ipv4", "ipv6"], "Schalter IPv4/IPv6 fehlt: %r"
         % (sub.mode_pills.values,))
    need(sub.mode == "ipv4", "Startmodus nicht IPv4")
    res["ipv6_vorgebaut"] = sub.built("ipv6")
    if VORLADEN == "0":
        need(not res["ipv6_vorgebaut"], "ohne Vorladen ist IPv6 schon gebaut - erster Wechsel nicht messbar")
    v4 = sub.views[("ipv4", "netzdaten")]
    v4["net"].set("192.168.1.50/24")
    res["rechnen_ms"] = timed(lambda: sub.calc("ipv4", "netzdaten"))
    need(v4["result"] and "192.168.1." in text_of(v4["box"]), "IPv4-Ergebnis fehlt")
    need(not v4["info_open"], "Rechenweg IPv4 schon offen")
    res["rechenweg_ms"] = timed(lambda: sub.toggle_info("ipv4", "netzdaten"))
    need(v4["info_open"] and v4["info"].winfo_manager() == "pack", "Rechenweg IPv4 nicht aufgeklappt")
    sub.toggle_info("ipv4", "netzdaten")   # zu, damit der Wechsel nur wechselt
    settle()
    # erster Wechsel IPv4 -> IPv6 ueber den Schalter (wie ein Klick)
    res["erster_wechsel_ms"] = timed(lambda: sub.mode_pills.select_value("ipv6"))
    need(sub.mode == "ipv6" and sub.mode_frames["ipv6"].winfo_manager() == "pack"
         and not sub.mode_frames["ipv4"].winfo_manager(), "erster Wechsel nach IPv6 wirkt nicht")
    v6 = sub.views[("ipv6", "netzdaten")]
    v6["net"].set("2001:db8:abcd::/48")
    need(v6["net"].get() == "2001:db8:abcd::/48", "IPv6-Eingabe nicht gesetzt")
    res["rechnen6_ms"] = timed(lambda: sub.calc("ipv6", "netzdaten"))
    need(v6["result"] and "2001:db8:abcd" in text_of(v6["box"]), "IPv6-Ergebnis fehlt")
    res["ipv6_eingabe_geprueft"] = True
    res["rechenweg6_ms"] = timed(lambda: sub.toggle_info("ipv6", "netzdaten"))
    need(v6["info_open"], "Rechenweg IPv6 nicht aufgeklappt")
    sub.toggle_info("ipv6", "netzdaten")
    settle()
    wechsel = []
    for ziel in ("ipv4", "ipv6", "ipv4", "ipv6", "ipv4", "ipv6"):
        wechsel.append(timed(lambda z=ziel: sub.mode_pills.select_value(z)))
        andere = "ipv6" if ziel == "ipv4" else "ipv4"
        need(sub.mode == ziel and sub.mode_frames[ziel].winfo_manager() == "pack"
             and not sub.mode_frames[andere].winfo_manager(), "Moduswechsel nach %s wirkt nicht" % ziel)
        need(sub.views[(ziel, "netzdaten")]["result"] is not None, "Ergebnis %s nach Wechsel weg" % ziel)
    res["modus_einzeln_ms"] = wechsel
    res["modus_ms"] = round(sum(wechsel) / len(wechsel), 1)
    res["blaettern"] = [blaettern(sub, "ipv6", "::/0", 2 ** 64),
                        blaettern(sub, "ipv4", "10.0.0.0/8", 2 ** 24)]
    res["kern"] = kern()


try:
    if FASSUNG == "vor":
        messe_vor()
    else:
        messe_nach()
except Fehlt as error:
    abbruch(str(error))
except Exception:   # noqa: BLE001
    abbruch("Ausnahme:\n" + traceback.format_exc())
if MELDUNGEN:
    abbruch("Meldungen: %r" % MELDUNGEN)

with open(OUT, "w", encoding="utf-8") as h:
    json.dump(res, h, indent=1)
zeile = ("ERG %s %s vorladen=%s calc_vorgeladen=%s | oeffnen %.1f | wieder %.1f | reiter %.1f"
         " | rechnen %.1f / %.1f | rechenweg %.1f"
         % (FASSUNG, res["version"], VORLADEN, res["calc_vorgeladen"], res["oeffnen_ms"],
            res["wieder_ms"], res["reiter_ms"], res["rechnen_ms"], res["rechnen6_ms"],
            res["rechenweg_ms"]))
if FASSUNG == "nach":
    zeile += (" | ipv6_vorgebaut=%s erster %.1f | modus %.1f (max %.1f) | blaettern max %.1f | kern max %.2f"
              % (res["ipv6_vorgebaut"], res["erster_wechsel_ms"], res["modus_ms"],
                 max(res["modus_einzeln_ms"]),
                 max(v for b in res["blaettern"] for v in b["seite_ms"].values()),
                 max(v for f in res["kern"] for k, v in f.items() if k.endswith("_ms"))))
print(zeile)
sys.stdout.flush()
os._exit(0)
