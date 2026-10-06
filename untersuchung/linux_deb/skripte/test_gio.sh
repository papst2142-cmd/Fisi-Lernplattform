#!/bin/bash
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq >/dev/null 2>&1
apt-get install -y -qq desktop-file-utils hicolor-icon-theme libgtk-3-bin python3-gi gir1.2-gtk-3.0 xvfb binutils >/dev/null 2>&1
apt-get install -y -qq /debs/fisi-lernplattform_0.59_amd64.deb >/dev/null 2>&1
echo "== icon-theme.cache enthaelt Eintrag?"; ls -la /usr/share/icons/hicolor/icon-theme.cache; grep -ac fisi-lernplattform /usr/share/icons/hicolor/icon-theme.cache
gtk-update-icon-cache --validate /usr/share/icons/hicolor 2>&1; echo "validate rc=$?"
grep -n "512x512" /usr/share/icons/hicolor/index.theme | head -3
cat > /tmp/g.py <<'P'
import gi, sys
gi.require_version("Gtk", "3.0")
from gi.repository import Gio, Gtk
a = Gio.DesktopAppInfo.new("fisi-lernplattform.desktop")
print("geladen:", a is not None)
if a:
    print("Datei:", a.get_filename(), "| should_show:", a.should_show(), "| NoDisplay:", a.get_nodisplay(), "| Exec:", a.get_commandline(), "| Name:", a.get_name())
print("in Gio.AppInfo.get_all + should_show:", any(x.get_id()=="fisi-lernplattform.desktop" and x.should_show() for x in Gio.AppInfo.get_all()))
print("Suche 'fisi':", Gio.DesktopAppInfo.search("fisi"))
t = Gtk.IconTheme.get_default(); info = t.lookup_icon("fisi-lernplattform", 48, 0)
print("Symbol 48px gefunden:", info.get_filename() if info else None)
P
echo "== GLib-Sicht (wie GNOME Shell die Eintraege liest)"; xvfb-run -a python3 /tmp/g.py
echo "== Gegenprobe: veraltete Benutzerdatei mit gleichem Namen und fehlendem Programm"
mkdir -p /root/.local/share/applications
printf '[Desktop Entry]\nType=Application\nName=FISI Lernplattform\nExec=/home/x/FISI-Lernplattform-0.50-x86_64.AppImage\nIcon=fisi-lernplattform\n' > /root/.local/share/applications/fisi-lernplattform.desktop
xvfb-run -a python3 /tmp/g.py
rm -rf /root/.local/share/applications
echo "== Gegenprobe: Desktop-Verknuepfung des Programms (~/Desktop) beeinflusst Menue?"
mkdir -p /root/Desktop; printf '[Desktop Entry]\nType=Application\nName=FISI Lernplattform\nExec=/usr/bin/fisi-lernplattform\nIcon=fisi-lernplattform\nX-FISI-Verknuepfung=true\n' > /root/Desktop/fisi-lernplattform.desktop
desktop-file-validate /root/Desktop/fisi-lernplattform.desktop; echo "validate Verknuepfung rc=$?"
echo "== fonts-ubuntu Dateien"; cd /tmp && apt-get download fonts-ubuntu >/dev/null 2>&1; dpkg -c fonts-ubuntu_*.deb | awk '{print $6}' | grep -E "ttf|otf" 
apt-cache show fonts-ubuntu | grep -E "^Version"
