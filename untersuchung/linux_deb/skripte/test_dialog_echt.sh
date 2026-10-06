#!/bin/bash
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq >/dev/null 2>&1
apt-get install -y -qq xvfb imagemagick fonts-ubuntu fonts-noto-core fonts-dejavu-core libxft2 libxss1 ca-certificates x11-utils xdotool >/dev/null 2>&1
apt-get install -y -qq /debs/fisi-lernplattform_$1_amd64.deb >/dev/null 2>&1
export HOME=/root DISPLAY=:9
Xvfb :9 -screen 0 1920x1080x24 >/dev/null 2>&1 &
sleep 2
/usr/bin/fisi-lernplattform > /t/start_$1.log 2>&1 &
sleep 30
xdotool key Escape; sleep 2; xdotool key Escape; sleep 40
xdotool search --name '.' 2>/dev/null | while read w; do n=$(xdotool getwindowname $w); [ -n "$n" ] && echo "alle: $n"; done | sort -u
xdotool search --name "Update verf" 2>/dev/null | while read w; do echo "Fenster: $(xdotool getwindowname $w)"; xwininfo -id $w | grep -E "Width|Height"; done
import -window root /t/echt_$1_vollbild.png
W=$(xdotool search --name "Update verf" | head -1); [ -n "$W" ] && import -window $W /t/echt_$1_update.png
fc-match sans-serif
