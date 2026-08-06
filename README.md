# VLESS + WebSocket + UDP on Railway

Deployable VLESS proxy using [Xray-core](https://github.com/XTLS/Xray-core), designed for Railway.

- **Protocol**: VLESS
- **Transport**: WebSocket (WS)
- **UDP**: Supported — enables QUIC/DNS-over-UDP traffic (e.g. YouTube, gaming, video calls work through the tunnel)

## Deploy to Railway

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/template?template=surfrpt1/vless-railway)

Or manually:

1. Create a new project on [Railway](https://railway.app)
2. Choose **Deploy from GitHub repo** and select this repo
3. Add the required variables (below)
4. Railway builds the Dockerfile and assigns a public domain (e.g. `https://yourapp.up.railway.app`)
5. Point your client at that domain, port 443, path `/ws`

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `UUID` | **Yes** | — | Client UUID. Generate with `uuidgen` or any online UUID v4 generator |
| `PORT` | No | `443` | Listening port (Railway overrides with `$PORT` if set by platform) |
| `WS_PATH` | No | `/` | WebSocket path, e.g. `/ws` (recommend a custom path) |
| `HOST_HEADER` | No | *(none)* | Optional Host header override for WS handshake |

> Railway auto-injects `PORT` — set your client's port to the Railway public port (usually 443).

## Client Configuration

### v2rayN / v2rayNG / NekoBox (share link)

```
vless://UUID@APPNAME.up.railway.app:443?encryption=none&security=tls&type=ws&host=APPNAME.up.railway.app&path=%2Fws#railway-vless
```

Replace:
- `UUID` — your generated UUID
- `APPNAME.up.railway.app` — your Railway public domain

### Manual settings (v2rayNG)

| Field | Value |
|---|---|
| Address | `APPNAME.up.railway.app` |
| Port | `443` |
| User ID | `UUID` |
| Encryption | `none` |
| Transport | `ws` (WebSocket) |
| Host | `APPNAME.up.railway.app` |
| Path | `/ws` (must match `WS_PATH`) |
| TLS | `tls` |
| UDP | enabled (default) |

## How UDP works

VLESS tunnels both TCP and UDP inside the WebSocket stream. The `freedom` outbound with `domainStrategy: UseIP` resolves domains locally and forwards UDP datagrams, so QUIC-based apps (YouTube, Cloudflare, gaming) work through the tunnel.

## Notes

- This config routes **private IPs to blackhole** to prevent the proxy being used as an open relay for internal-network scanning.
- Regenerate the UUID in production — never ship the example value.
- Local testing: `docker build -t vless-railway . && docker run -e UUID=$(uuidgen) -p 443:443 vless-railway`
