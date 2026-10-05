"""Startet das echte Programm (main), oeffnet eine Ansicht, schliesst nach
einigen Sekunden ueber on_close (wie das X bzw. der Update-Zeitgeber) und
prueft: endet mainloop? Was steht in fehler.log?"""
import os, sys, threading, time
sys.path.insert(0, os.environ["REPO"]); os.chdir(os.environ["REPO"])
VIEW = sys.argv[1] if len(sys.argv) > 1 else "dashboard"
MODE = sys.argv[2] if len(sys.argv) > 2 else "x"   # x | update

import app_gui, customtkinter as ctk
app_gui.UpdateController.auto_check = lambda self: None
app_gui.SyncController.auto_start = lambda self: None
orig_init = app_gui.FISIApp.__init__
def patched(self, root):
    orig_init(self, root)
    def go():
        self.show_view(VIEW)
        if MODE == "update":
            dlg = app_gui.UpdateDialog(self, app_gui.fisi_update.UpdateInfo("9.9", "- Test", "x"))
            # genau wie _installed: nach 1,5 s on_close(final_sync=False)
            dlg.after(1500, lambda: self.on_close(final_sync=False))
        else:
            root.after(1500, self.on_close)
    root.after(1500, go)
app_gui.FISIApp.__init__ = patched
t0 = time.time()
def watchdog():
    time.sleep(25)
    print("ERGEBNIS: mainloop laeuft nach 25 s noch -> Prozess bleibt haengen", flush=True)
    os._exit(3)
threading.Thread(target=watchdog, daemon=True).start()
app_gui.main()
print("ERGEBNIS: mainloop beendet nach %.1f s" % (time.time() - t0), flush=True)
