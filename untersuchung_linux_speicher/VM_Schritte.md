# Schritte auf der VM (Untersuchung Linux-Einfrieren, 07.10.2026)

Nur lesen und beobachten. `sudo` nur, wo es dabei steht – das machst du selbst. Ergebnisse (Text oder Foto) einfach in den Chat.



**Vorbereitung (einmal)**
1. Terminal öffnen und festhalten: `echo $XDG_SESSION_TYPE; gnome-shell --version; dpkg -l fisi-lernplattform | tail -1; nproc; free -m`
2. Werkzeuge für später installieren (einmal, mit sudo): `sudo apt install x11-utils elfutils`

**Test 1: ohne RDP (Proxmox-Konsole)**
3. In der Proxmox-Konsole (nicht über RDP) anmelden und FISI aus dem Terminal starten: `fisi-lernplattform` (das Terminal offen lassen).
4. Leistungsmessung an, dann wie gewohnt 6–8 Darstellungswechsel mit Seitenbesuchen dazwischen. Ruhig auch während eines Wechsels klicken (Klicks lösen dabei kurze X-Grabs aus, siehe F2).
5. Notieren: Hing es? Erschien „FISI reagiert nicht“ von GNOME?

**Wenn es hängt (egal ob mit oder ohne RDP)**
6. **Mindestens 2 Minuten warten**, ohne zu klicken. Kommt es zurück? (Das klärt „dauerhaft“ oder „lange blockiert“.)
7. In einem zweiten Terminal: `PID=$(pgrep -x FISI-Lernplattf | head -1); echo $PID`
8. Wartepunkte: `for t in /proc/$PID/task/*; do echo "$(cat $t/comm) $(awk '{print $3}' $t/stat) $(cat $t/wchan)"; done`
9. Prozessorzeit in 10 s: `a=$(awk '{print $14+$15}' /proc/$PID/stat); sleep 10; b=$(awk '{print $14+$15}' /proc/$PID/stat); echo $((b-a))` (0 = schläft wirklich)
10. Antwortet XWayland anderen Programmen? `timeout 5 xdpyinfo -display :0 | head -3`. Kommen 3 Zeilen, lebt XWayland. Kommt nichts, hängt XWayland selbst.
11. **Stapel (mit sudo):** `sudo eu-stack -p $PID | head -60`. Interessant ist, ob im ersten Thread `XSync`, `_XReply` oder `xcb_wait_for_reply` steht. Ein Foto oder Text davon genügt.
12. Danach wie bisher über den Ressourcenmanager beenden.

**Schließen und Sperre**
13. `grep -n -A1 "Notausgang\|Mehrfachstart" ~/.local/share/fisi-lernplattform/fehler.log`. Interessant: Welche **Versionen** stehen im Kopf darüber (gab es das schon mit 0.58.1)? Und bei „Mehrfachstart“: steht dort **„Antwort: keine“** oder **„Antwort: endet“**?
14. Einmal FISI aus dem Terminal starten, nichts tun, nach 30 s am X schließen und im Terminal beobachten, wann die Eingabeaufforderung zurückkommt (sofort oder nach ca. 8 s). Einmal über RDP, einmal über die Proxmox-Konsole.
15. Ist der Abgleich (Optionen → Abgleich) eingerichtet? (Ja/Nein genügt, er läuft vor dem Notausgang.)

**Dateien schicken**
16. `~/.local/share/fisi-lernplattform/leistungsmessung.csv` und `fehler.log` von der VM. Für den PC-Vergleich zusätzlich `leistungsmessung.csv` vom Windows-PC.
17. Optional: `journalctl --user -b --since "-30 min" | grep -i -E "xwayland|mutter|remote" | tail -50`

---

