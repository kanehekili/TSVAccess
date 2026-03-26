#!/bin/bash
LOGFILE="/var/log/wlan-monitor.log"
while true; do
    state=$(iw wlan0 link | head -1)
    if [ "$state" = "Not connected." ]; then
        echo "$(date '+%Y-%m-%d %H:%M:%S') NOT CONNECTED" >> "$LOGFILE"
    fi
    sleep 5
done
