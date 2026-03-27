#!/bin/bash
# Cron-safe launcher for the Foodpanda server.
# Starts the server only if it's not already running.
# Logs to .tmp/server.log

PROJECT_DIR="/home/sarah/Desktop/Sarah/DOE-Foodpanda"
PIDFILE="$PROJECT_DIR/.tmp/server.pid"
LOGFILE="$PROJECT_DIR/.tmp/server.log"

cd "$PROJECT_DIR"
mkdir -p .tmp

# Load .env
if [ -f .env ]; then
    set -a
    source .env
    set +a
fi

# Check if already running
if [ -f "$PIDFILE" ]; then
    PID=$(cat "$PIDFILE")
    if kill -0 "$PID" 2>/dev/null; then
        echo "$(date): Server already running (PID $PID)" >> "$LOGFILE"
        exit 0
    fi
    rm -f "$PIDFILE"
fi

# Export DISPLAY for desktop notifications from cron
export DISPLAY=:0
export DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/$(id -u)/bus"

# Start server in background
cd execution
nohup python3 foodpanda_server.py >> "$LOGFILE" 2>&1 &
echo $! > "$PIDFILE"
echo "$(date): Server started (PID $!)" >> "$LOGFILE"
