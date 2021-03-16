#!/usr/bin/env bash
### every exit != 0 fails the script
set -e
set -u

echo "Install noVNC - HTML5 based VNC viewer"
mkdir -p $NO_VNC_HOME/utils/websockify
wget -qO- https://github.com/novnc/noVNC/archive/v1.0.0.tar.gz | tar xz --strip 1 -C $NO_VNC_HOME
# use older version of websockify to prevent hanging connections on offline containers, see https://github.com/ConSol/docker-headless-vnc-container/issues/50
wget -qO- https://github.com/novnc/websockify/archive/v0.6.1.tar.gz | tar xz --strip 1 -C $NO_VNC_HOME/utils/websockify
chmod +x -v $NO_VNC_HOME/utils/*.sh

cp $NO_VNC_HOME/vnc_lite.html $NO_VNC_HOME/vnc_rapyuta.html
# a bunch of seds to fix title, favicon, etc
# TODO: will need our custom page later

# add rapyuta favicon to icons
cp $INST_SCRIPTS/favicon.ico $NO_VNC_HOME/app/images/icons/
# append our icon after <head> tag
sed -i '/<head>/a <link rel="shortcut icon" href="app/images/icons/favicon.ico">' $NO_VNC_HOME/vnc_rapyuta.html
# fix title
sed -i "s/getConfigVar('title', 'noVNC')/getConfigVar('title', 'Gazebo Simulation | rapyuta.io')/" $NO_VNC_HOME/vnc_rapyuta.html
# delete noVNC favicons
sed -i '/<link rel="icon"/d' $NO_VNC_HOME/vnc_rapyuta.html
sed -i '/<link rel="apple-touch-icon"/d' $NO_VNC_HOME/vnc_rapyuta.html
# hide CtrlAltDel button
sed -i -e 's/id="sendCtrlAltDelButton" class="noVNC_shown"/id="sendCtrlAltDelButton" class="noVNC_hidden"/' $NO_VNC_HOME/vnc_rapyuta.html

ln -s $NO_VNC_HOME/vnc_rapyuta.html $NO_VNC_HOME/index.html
