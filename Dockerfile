FROM alpine:3.20

RUN apk add --no-cache ca-certificates wget unzip tzdata python3 py3-pip

# Xray core (latest release)
RUN wget -q -O /tmp/xray.zip https://github.com/XTLS/Xray-core/releases/latest/download/Xray-linux-64.zip && \
    unzip /tmp/xray.zip -d /usr/local/bin && \
    rm /tmp/xray.zip && \
    chmod +x /usr/local/bin/xray

# Caddy reverse proxy (routes /ws to xray, rest to dashboard)
RUN wget -q -O /tmp/caddy.tar.gz https://github.com/caddyserver/caddy/releases/download/v2.9.1/caddy_2.9.1_linux_amd64.tar.gz && \
    tar -xzf /tmp/caddy.tar.gz -C /usr/local/bin caddy && \
    chmod +x /usr/local/bin/caddy

# Dashboard deps
RUN pip install --break-system-packages --no-cache-dir flask qrcode Pillow

WORKDIR /app
COPY . /app

RUN chmod +x /app/entrypoint.sh

CMD ["/app/entrypoint.sh"]
