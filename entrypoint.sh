#!/bin/sh
set -e

echo "[entrypoint] starting with PORT=${PORT:-unset} UUID=${UUID:+set} WS_PATH=${WS_PATH:-/ws}"

if [ -z "$UUID" ]; then
  echo "ERROR: UUID environment variable is not set (generate with: uuidgen)" >&2
  exit 1
fi

PORT="${PORT:-443}"
WS_PATH="${WS_PATH:-/ws}"
ADMIN_TOKEN="${ADMIN_TOKEN:-}"
PUBLIC_DOMAIN="${PUBLIC_DOMAIN:-$RAILWAY_PUBLIC_DOMAIN}"

if [ -z "$ADMIN_TOKEN" ]; then
  echo "WARNING: ADMIN_TOKEN not set - dashboard API is unauthenticated!" >&2
fi

export PORT WS_PATH ADMIN_TOKEN PUBLIC_DOMAIN UUID

# Generate config from template
python3 /app/app.py --gen-config
echo "[entrypoint] config generated"

# Start Xray (WS inbound on 8080, stats API on 10085)
/usr/local/bin/xray run -c /app/config.json &
XRAY_PID=$!
echo $XRAY_PID > /tmp/xray.pid
echo "[entrypoint] xray started (pid=$XRAY_PID)"

# Wait for Xray API to be ready (up to 15s)
echo "[entrypoint] waiting for xray API on :10085..."
TRIES=0
while [ $TRIES -lt 30 ]; do
  if curl -sf http://127.0.0.1:10085 >/dev/null 2>&1; then
    echo "[entrypoint] xray API ready"
    break
  fi
  # Also check if xray is still alive
  if ! kill -0 $XRAY_PID 2>/dev/null; then
    echo "ERROR: xray process died during startup" >&2
    exit 1
  fi
  TRIES=$((TRIES + 1))
  sleep 0.5
done
if [ $TRIES -ge 30 ]; then
  echo "WARNING: xray API not ready after 15s, continuing anyway" >&2
fi

# Start dashboard
cd /app && python3 app.py &
DASH_PID=$!
echo "[entrypoint] dashboard started (pid=$DASH_PID)"

# Wait for Flask to be ready (up to 10s)
echo "[entrypoint] waiting for dashboard on :8081..."
TRIES=0
while [ $TRIES -lt 20 ]; do
  if curl -sf http://127.0.0.1:8081/api/healthz >/dev/null 2>&1; then
    echo "[entrypoint] dashboard ready"
    break
  fi
  if ! kill -0 $DASH_PID 2>/dev/null; then
    echo "ERROR: dashboard process died during startup" >&2
    exit 1
  fi
  TRIES=$((TRIES + 1))
  sleep 0.5
done
if [ $TRIES -ge 20 ]; then
  echo "WARNING: dashboard not ready after 10s, continuing anyway" >&2
fi

# Start Caddy reverse proxy on $PORT
/usr/local/bin/caddy run --config /app/Caddyfile &
CADDY_PID=$!
echo "[entrypoint] caddy started (pid=$CADDY_PID) on :$PORT"

# Clean shutdown on SIGTERM/SIGINT
cleanup() {
  echo "[entrypoint] shutting down..."
  kill $CADDY_PID $DASH_PID $XRAY_PID 2>/dev/null
  wait 2>/dev/null
  echo "[entrypoint] stopped"
}
trap cleanup TERM INT

wait $DASH_PID
EXIT_CODE=$?
echo "[entrypoint] dashboard exited (code=$EXIT_CODE)"
exit $EXIT_CODE
