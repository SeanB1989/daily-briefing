#!/bin/bash

# Kill any process holding port 5000 (find via inode in /proc/net/tcp)
inode=$(awk 'NR>1 && $2 ~ /00000000:1388/ {print $10}' /proc/net/tcp 2>/dev/null | head -1)
if [ -n "$inode" ]; then
    for pid in $(ls /proc | grep -E '^[0-9]+$'); do
        if ls -la /proc/$pid/fd 2>/dev/null | grep -q "socket:\[$inode\]"; then
            echo "Killing PID $pid holding port 5000"
            kill -9 "$pid" 2>/dev/null
        fi
    done
    sleep 1
fi

pip install -r requirements.txt
python3 main.py
