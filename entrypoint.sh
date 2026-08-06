#!/bin/sh
set -e

UUID="${UUID:-}"
PORT="${PORT:-443}"
WS_PATH="${WS_PATH:-/}"
HOST_HEADER="${HOST_HEADER:-}"

if [ -z "$UUID" ]; then
  echo "ERROR: UUID environment variable is not set" >&2
  exit 1
fi

sed -e "s/\${UUID}/${UUID}/g" \
    -e "s/\${PORT}/${PORT}/g" \
    -e "s|\${WS_PATH}|${WS_PATH}|g" \
    -e "s/\${HOST_HEADER}/${HOST_HEADER}/g" \
    /etc/xray/config.template.json > /etc/xray/config.json

exec /usr/local/bin/xray run -c /etc/xray/config.json