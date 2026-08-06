# VLESS + WebSocket + UDP with Dashboard — Railway deploy

Deployable VLESS proxy using [Xray-core](https://github.com/XTLS/Xray-core) with a built-in web dashboard, designed for Railway.

- **Protocol**: VLESS
- **Transport**: WebSocket (WS)
- **UDP**: Supported — QUIC/DNS-over-UDP traffic (YouTube, gaming, video calls) tunneled
- **Dashboard**: live server info, peer management, per-peer traffic stats, QR codes

## Deploy to Railway

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/template?template=surfrpt1/vless-railway)

Or manually:

1. Create a new project on [Railway](https://railway.app)
2. Choose **Deploy from GitHub repo** and select `surfrpt1/vless-railway`
3. Add the required variables (below)
4. Railway builds the Dockerfile and assigns a public domain (e.g. `https://yourapp.up.railway.app`)
5. Open your domain in a browser → the dashboard appears

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `UUID` | **Yes** | — | Initial client UUID (the dashboard creates more). Generate with `uuidgen` |
| `ADMIN_TOKEN` | **Recommended** | *(none — dashboard unauthenticated!)* | Password for the dashboard admin API |
| `WS_PATH` | No | `/ws` | WebSocket path (recommend a custom path, e.g. `/ws`) |
| `PUBLIC_DOMAIN` | No | auto | Override the domain shown in share links/QR (normally auto-detected from Railway) |

> Railway auto-injects `PORT` and `RAILWAY_PUBLIC_DOMAIN` — usually nothing to set beyond `UUID` and `ADMIN_TOKEN`.

## Dashboard features

Open `https://yourapp.up.railway.app/`:

- **Server info card** — domain, port, TLS, WS path
- **Peers table** — every client UUID with:
  - Live status (ACTIVE / idle) from Xray traffic stats (refreshes every 8s)
  - Download/upload traffic totals
  - Share link with copy button
- **+ New peer** — create a new UUID with an optional name (auto-applied to Xray via config reload)
- **Delete peer** — removes a client UUID
- **QR code** — scan from any VLESS-capable client app (v2rayNG, NekoBox, Streisand, Shadowrocket, etc.) to import the server

## Client configuration

### v2rayN / v2rayNG / NekoBox (share link)

```
vless://UUID@APPNAME.up.railway.app:443?encryption=none&security=tls&type=ws&host=APPNAME.up.railway.app&path=%2Fws#vless-railway
```

Or just scan the QR code from the dashboard.

### Manual settings (v2rayNG)

| Field | Value |
|---|---|
| Address | `APPNAME.up.railway.app` |
| Port | `443` |
| User ID | one of the peer UUIDs from the dashboard |
| Encryption | `none` |
| Transport | `ws` (WebSocket) |
| Host | `APPNAME.up.railway.app` |
| Path | `/ws` (must match `WS_PATH`) |
| TLS | `tls` |
| UDP | enabled (default) |

## How it works

- **Caddy** terminates the public HTTP(S) on Railway's port and routes `${WS_PATH}` → Xray, everything else → dashboard
- **Xray** listens internally on 8080 (VLESS+WS) and exposes its Stats API on `127.0.0.1:10085` for traffic metrics
- **Dashboard** (Flask) reads/writes `data/peers.json`, regenerates the Xray config, and triggers a SIGHUP reload on every peer change
- Private IPs are routed to **blackhole** to prevent open-relay abuse
- Peers persist in the container filesystem — for persistent storage across redeploys, connect a Railway volume at `/app/data`

## Security notes

- Set `ADMIN_TOKEN` — without it the dashboard is open to anyone who finds your URL
- Regenerate your UUID in production — never ship the example value
- Add a Railway volume (`/app/data`) to keep peers across deployments
