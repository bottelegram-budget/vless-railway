#!/bin/sh
set -e

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

# Start Xray (WS inbound on 8080, stats API on 10085)
/usr/local/bin/xray run -c /app/config.json &
echo $! > /tmp/xray.pid

# Start dashboard
cd /app && python3 app.py &
DASH_PID=$!

# Start Caddy reverse proxy on $PORT
/usr/local/bin/caddy run --config /app/Caddyfile &
CADDY_PID=$!

trap "kill $DASH_PID $CADDY_PID 2>/dev/null" EXIT

wait $DASH_PID
