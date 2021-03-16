#!/usr/bin/env bash
### every exit != 0 fails the script
set -e

echo "Install Xfce4 UI components"
apt-get install -y xfce4 xterm
cp $INST_SCRIPTS/xfce4-session.xml /etc/xdg/xfce4/xfconf/xfce-perchannel-xml/xfce4-session.xml
apt-get purge -y pm-utils xscreensaver*
