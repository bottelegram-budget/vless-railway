FROM alpine:3.20

RUN apk add --no-cache ca-certificates wget unzip tzdata

RUN wget -q -O /tmp/xray.zip https://github.com/XTLS/Xray-core/releases/latest/download/Xray-linux-64.zip && \
    unzip /tmp/xray.zip -d /usr/local/bin && \
    rm /tmp/xray.zip && \
    chmod +x /usr/local/bin/xray

ENV UUID="" PORT="443" WS_PATH="/"

COPY config.template.json /etc/xray/config.template.json
COPY entrypoint.sh /entrypoint.sh

RUN chmod +x /entrypoint.sh

EXPOSE 443

CMD ["/entrypoint.sh"]
