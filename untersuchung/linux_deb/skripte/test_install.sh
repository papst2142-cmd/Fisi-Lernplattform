#!/bin/bash
# Laeuft im Container ubuntu:26.04. Nur Messung.
set +e
export DEBIAN_FRONTEND=noninteractive
D=/debs
log(){ echo; echo "########## $*"; }
apt-get update -qq >/dev/null 2>&1
log "Vorbereitung: desktop-file-utils hicolor-icon-theme libgtk-3-bin installieren"
apt-get install -y -qq desktop-file-utils hicolor-icon-theme libgtk-3-bin xvfb >/dev/null 2>&1; echo rc=$?
log "dpkg-Trigger mit Interesse an applications/icons"
grep -E "applications|icons" /var/lib/dpkg/triggers/File
for p in desktop-file-utils hicolor-icon-theme libgtk-3-bin; do echo "-- $p:"; cat /var/lib/dpkg/info/$p.triggers 2>/dev/null; done
log "Versionsvergleich"
for pair in "0.58.1 lt 0.59" "0.58 lt 0.58.1" "0.59 lt 0.59.1" "0.59.1 lt 0.60" "0.9 lt 0.10" "0.59 lt 0.6"; do dpkg --compare-versions $pair && echo "$pair : wahr" || echo "$pair : FALSCH"; done

run_case(){
  tool=$1
  log "FALL $tool: 0.58.1 installieren"
  if [ $tool = apt ]; then apt-get install -y $D/fisi-lernplattform_0.58.1_amd64.deb 2>&1 | tail -8; else dpkg -i $D/fisi-lernplattform_0.58.1_amd64.deb 2>&1; fi
  echo rc=$?
  dpkg -s fisi-lernplattform | grep -E "Status|Version"
  ls -la /usr/share/applications/fisi-lernplattform.desktop; grep -c fisi-lernplattform /usr/share/applications/mimeinfo.cache 2>/dev/null; ls -la /usr/share/icons/hicolor/icon-theme.cache
  find /opt/fisi-lernplattform -type f | wc -l > /tmp/n_alt
  log "FALL $tool: 0.59 darueber"
  if [ $tool = apt ]; then apt-get install -y $D/fisi-lernplattform_0.59_amd64.deb 2>&1 | tail -12; else dpkg -i $D/fisi-lernplattform_0.59_amd64.deb 2>&1; fi
  echo rc=$?
  dpkg -s fisi-lernplattform | grep -E "Status|Version"
  echo "Dateien im Paket: $(dpkg -L fisi-lernplattform | wc -l), Dateien unter /opt: $(find /opt/fisi-lernplattform -type f | wc -l) (vorher $(cat /tmp/n_alt))"
  echo "Nicht vom Paket erfasste Dateien unter /opt:"; comm -13 <(dpkg -L fisi-lernplattform | sort) <(find /opt/fisi-lernplattform | sort) | head
  ls -la --time-style=+%T /usr/share/icons/hicolor/icon-theme.cache
  log "FALL $tool: gleiche Version nochmal (0.59 ueber 0.59)"
  if [ $tool = apt ]; then apt-get install -y $D/fisi-lernplattform_0.59_amd64.deb 2>&1 | tail -4; else dpkg -i $D/fisi-lernplattform_0.59_amd64.deb 2>&1 | tail -4; fi
  log "FALL $tool: aeltere Version ueber neuere (0.58.1 ueber 0.59)"
  if [ $tool = apt ]; then apt-get install -y $D/fisi-lernplattform_0.58.1_amd64.deb 2>&1 | tail -6; else dpkg -i $D/fisi-lernplattform_0.58.1_amd64.deb 2>&1 | tail -6; fi
  echo rc=$?; dpkg -s fisi-lernplattform | grep -E "Version"
  log "FALL $tool: entfernen"
  apt-get remove -y fisi-lernplattform 2>&1 | tail -3
  echo "Reste: $(ls -d /opt/fisi-lernplattform /usr/share/applications/fisi-lernplattform.desktop /usr/bin/fisi-lernplattform 2>&1 | tr '\n' ' ')"
}
run_case apt
run_case dpkg

log "Menueeintrag pruefen (0.59 installiert)"
apt-get install -y -qq $D/fisi-lernplattform_0.59_amd64.deb >/dev/null 2>&1
desktop-file-validate /usr/share/applications/fisi-lernplattform.desktop; echo "validate rc=$?"
echo "Exec aufgeloest: $(command -v fisi-lernplattform) -> $(readlink -f $(command -v fisi-lernplattform))"; test -x "$(readlink -f /usr/bin/fisi-lernplattform)" && echo "ausfuehrbar: ja"
find / -path /proc -prune -o -name 'fisi-lernplattform.png' -print 2>/dev/null
gtk-update-icon-cache --validate /usr/share/icons/hicolor/icon-theme.cache 2>&1; echo "cache valid rc=$?"
strings /usr/share/icons/hicolor/icon-theme.cache | grep -c fisi-lernplattform
log "Bibliotheken: ldd fehlende (minimaler Container ohne Desktop)"
ldd /opt/fisi-lernplattform/FISI-Lernplattform | grep "not found"
for f in /opt/fisi-lernplattform/_internal/*.so* /opt/fisi-lernplattform/_internal/lib-dynload/*.so; do ldd $f 2>/dev/null | grep "not found"; done | sort -u
log "Startversuch unter Xvfb (5 s)"
timeout 8 xvfb-run -a /usr/bin/fisi-lernplattform > /tmp/start.log 2>&1; echo "rc=$? (124 = lief bis Zeitlimit)"; tail -5 /tmp/start.log
log "fonts-ubuntu in 26.04: Schriftfamilien"
cd /tmp && apt-get download fonts-ubuntu >/dev/null 2>&1; dpkg -c fonts-ubuntu_*.deb | grep -oE "[A-Za-z-]+\.(ttf|otf)" | sort -u | head -30
apt-cache depends ubuntu-desktop-minimal 2>/dev/null | grep -i font
