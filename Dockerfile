FROM alpine:3.20

RUN apk add --no-cache ca-certificates wget unzip tzdata python3 py3-pip curl

# Xray core (pinned)
RUN wget -q -O /tmp/xray.zip https://github.com/XTLS/Xray-core/releases/download/v26.3.27/Xray-linux-64.zip && \
    unzip /tmp/xray.zip -d /usr/local/bin && \
    rm /tmp/xray.zip && \
    chmod +x /usr/local/bin/xray

# Caddy reverse proxy (routes /ws to xray, rest to dashboard)
RUN wget -q -O /tmp/caddy.tar.gz https://github.com/caddyserver/caddy/releases/download/v2.11.4/caddy_2.11.4_linux_amd64.tar.gz && \
    tar -xzf /tmp/caddy.tar.gz -C /usr/local/bin caddy && \
    chmod +x /usr/local/bin/caddy

# Dashboard deps
RUN pip install --break-system-packages --no-cache-dir flask qrcode Pillow

WORKDIR /app
COPY . /app

RUN chmod +x /app/entrypoint.sh

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -sf http://localhost:8081/api/healthz || exit 1

CMD ["/app/entrypoint.sh"]
