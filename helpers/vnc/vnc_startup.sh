#!/bin/bash
### every exit != 0 fails the script
set -e

# source "$CATKIN_WS_SRC/.s2i/bin/preamble"
# if [[ $@ == *"$CATKIN_WS_SRC/.s2i/bin/assemble"* ]]
# then
#     echo "---> Performing S2I build... Skipping server startup"
#     exec "$@"
#     exit $?
# fi

export HOME=$VNC_HOME

## resolve_vnc_connection
VNC_IP=$(hostname -i)

## change vnc password
# first entry is control, second is view (if only one is valid for both)
mkdir -p "$VNC_HOME/.vnc"
PASSWD_PATH="$VNC_HOME/.vnc/passwd"

echo "$VNC_PASSWORD" | vncpasswd -f >> $PASSWD_PATH
chmod 600 $PASSWD_PATH


## start vncserver and noVNC webclient
echo -e "\n------------------ start noVNC  ----------------------------"
if [[ $DEBUG == true ]]; then echo "$NO_VNC_HOME/utils/launch.sh --vnc localhost:$VNC_PORT --listen $NO_VNC_PORT"; fi
$NO_VNC_HOME/utils/launch.sh --vnc localhost:$VNC_PORT --listen $NO_VNC_PORT &> $VNC_HOME/no_vnc_startup.log &
PID_SUB=$!

echo -e "\n------------------ start VNC server ------------------------"
echo "remove old vnc locks to be a reattachable container"
HOME=$VNC_HOME vncserver -kill $DISPLAY &> $VNC_HOME/vnc_startup.log \
    || rm -rfv /tmp/.X*-lock /tmp/.X11-unix &> $VNC_HOME/vnc_startup.log \
    || echo "no locks present"

echo -e "start vncserver with param: VNC_COL_DEPTH=$VNC_COL_DEPTH, VNC_RESOLUTION=$VNC_RESOLUTION\n..."
if [[ $DEBUG == true ]]; then echo "vncserver $DISPLAY -depth $VNC_COL_DEPTH -geometry $VNC_RESOLUTION"; fi
HOME=$VNC_HOME vncserver $DISPLAY -depth $VNC_COL_DEPTH -geometry $VNC_RESOLUTION &> $VNC_HOME/no_vnc_startup.log
echo -e "start window manager\n..."
# $VNC_HOME/wm_startup.sh &> $STARTUPDIR/wm_startup.log

## log connect options
echo -e "\n\n------------------ VNC environment started ------------------"
echo -e "\nVNCSERVER started on DISPLAY= $DISPLAY \n\t=> connect via VNC viewer with $VNC_IP:$VNC_PORT"
echo -e "\nnoVNC HTML client started:\n\t=> connect via http://$VNC_IP:$NO_VNC_PORT/?password=...\n"
HOME=$VNC_HOME metacity --replace --no-composite &
mkdir -p $VNC_HOME/.devilspie
echo "(if (and
(is (window_property \"_NET_WM_WINDOW_TYPE\") \"_NET_WM_WINDOW_TYPE_NORMAL\")
(not (contains (window_property \"_NET_WM_STATE\") \"_NET_WM_STATE_MODAL\")))

(begin
(undecorate)
(geometry \"2000x2000\")
(maximize)
)
)" >> $VNC_HOME/.devilspie/maximize.ds
HOME=$VNC_HOME devilspie&

echo -e "\n\n------------------ EXECUTE ROS ENTRYPOINT ------------------"
# setup ros environment
source "/opt/ros/$ROS_DISTRO/setup.bash"
if [ -e "$CATKIN_WS/install/setup.bash" ]
then
     source "$CATKIN_WS/install/setup.bash"
fi
echo "Executing command: '$@'"
exec $@
