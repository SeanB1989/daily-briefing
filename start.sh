#!/bin/bash

# Kill any process already using port 5000
port_pid=$(awk '$2 ~ /00000000:1388/ {print $7}' /proc/net/tcp 2>/dev/null | head -1)
if [ -n "$port_pid" ] && [ "$port_pid" != "0" ]; then
    kill -9 "$port_pid" 2>/dev/null
    sleep 1
fi

pip install -r requirements.txt
python3 main.py
