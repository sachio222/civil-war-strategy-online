# CWS Online Server

Turn-based multiplayer server for Civil War Strategy Online. Players connect from the game client; the server tracks games, turns, and state.

## Quick Start

```bash
cd server
pip install -r requirements.txt
uvicorn server:app --host 0.0.0.0 --port 1861
```

The server is now running at `http://<your-ip>:1861`.

Game data is stored in `cws_online.db` (SQLite, created automatically). To use a custom path:

```bash
CWS_DB_PATH=/path/to/cws_online.db uvicorn server:app --host 0.0.0.0 --port 1861
```

## Exposing with Cloudflare Tunnel

If the server machine isn't directly reachable (no port forwarding, behind NAT, etc.), use a [cloudflared](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/get-started/) tunnel.

### 1. Install cloudflared

```bash
# macOS
brew install cloudflared

# Linux (Debian/Ubuntu)
curl -fsSL https://pkg.cloudflare.com/cloudflare-main.gpg | sudo tee /usr/share/keyrings/cloudflare-main.gpg > /dev/null
echo "deb [signed-by=/usr/share/keyrings/cloudflare-main.gpg] https://pkg.cloudflare.com/cloudflared $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/cloudflared.list
sudo apt update && sudo apt install cloudflared
```

### 2. Start the server

```bash
cd server
uvicorn server:app --host 0.0.0.0 --port 1861
```

### 3. Start the tunnel (separate terminal)

**Quick tunnel (no Cloudflare account needed):**

```bash
cloudflared tunnel --url http://localhost:1861
```

This prints a public URL like:

```
https://random-words-here.trycloudflare.com
```

**Named tunnel (requires Cloudflare account, persistent URL):**

```bash
cloudflared tunnel create cws
cloudflared tunnel route dns cws cws.yourdomain.com
cloudflared tunnel run --url http://localhost:1861 cws
```

### 4. Connect from the game

When the game asks for "Server address?", enter the tunnel URL:

```
random-words-here.trycloudflare.com
```

The game client adds `http://` automatically. If using a cloudflared tunnel, change the client to use `https://` -- or just enter the full URL:

```
https://random-words-here.trycloudflare.com
```

## API Endpoints

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| `POST` | `/api/games` | No | Create game -> `{game_code, token, side}` |
| `POST` | `/api/games/{code}/join` | No | Join game -> `{token, side}` |
| `GET` | `/api/games/{code}` | No | Game status -> `{status, current_side, turn_number}` |
| `POST` | `/api/games/{code}/turn` | Bearer | Submit completed turn |
| `GET` | `/api/games/{code}/turn` | Bearer | Poll for opponent's turn |

Interactive API docs available at `http://<server>:1861/docs`.

## How It Works

1. **Player 1** creates a game, gets a 6-character code and a token (Union side)
2. **Player 2** joins with the code, gets their own token (Confederate side)
3. Players take turns: submit state via POST, poll via GET
4. The server stores game state in SQLite and tracks whose turn it is
5. Games can be resumed -- the client saves session info to `~/.cws/`

## Files

| File | Purpose |
|------|---------|
| `server.py` | FastAPI app with all endpoints |
| `database.py` | SQLite schema and CRUD operations |
| `models.py` | Pydantic request/response models |
| `requirements.txt` | Python dependencies |
