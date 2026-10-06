import subprocess, time
def key(k): subprocess.run(["xdotool", "key", k]); time.sleep(1.0)
def focus(): return subprocess.run(["python3.12", "focused.py"], capture_output=True, text=True).stdout.strip()
def dump(name): subprocess.run("python3.12 dump_atspi.py > %s" % name, shell=True)
key("Tab"); key("Tab"); print("Fokus:", focus()); key("Return"); print("nach Enter:", focus()); dump("k_tree1.txt")
key("Tab"); print("Tab:", focus()); key("Tab"); print("Tab:", focus())
key("Return"); print("nach Enter (Antwort zeigen):", focus()); dump("k_tree2.txt")
key("Return"); print("nach Enter (Gewusst):", focus())
