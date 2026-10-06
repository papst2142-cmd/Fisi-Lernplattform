#!/bin/bash
# Startet Xvfb + D-Bus-Sitzung + AT-SPI-Bus, dann den Befehl "$@"
export DISPLAY=:99
Xvfb :99 -screen 0 1280x900x24 >/dev/null 2>&1 &
sleep 1
export NO_AT_BRIDGE=0 GTK_MODULES=gail:atk-bridge QT_ACCESSIBILITY=1 GNOME_ACCESSIBILITY=1
exec dbus-run-session -- bash -c '/usr/libexec/at-spi-bus-launcher --launch-immediately >/dev/null 2>&1 & sleep 1; '"$*"
