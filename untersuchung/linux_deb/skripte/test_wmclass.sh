#!/bin/bash
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq >/dev/null 2>&1
apt-get install -y -qq xvfb fonts-ubuntu libxft2 libxss1 x11-utils xdotool >/dev/null 2>&1
apt-get install -y -qq /debs/fisi-lernplattform_0.59_amd64.deb >/dev/null 2>&1
export DISPLAY=:9; Xvfb :9 -screen 0 1920x1080x24 >/dev/null 2>&1 & sleep 2
/usr/bin/fisi-lernplattform >/dev/null 2>&1 & sleep 25
for w in $(xdotool search --name "FISI"); do echo "Titel: $(xdotool getwindowname $w)"; xprop -id $w WM_CLASS; done
