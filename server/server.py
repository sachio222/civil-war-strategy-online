"""server.py - FastAPI app for CWS online multiplayer.

Run:
    cd server
    pip install fastapi uvicorn
    uvicorn server:app --host 0.0.0.0 --port 1861
"""

from pathlib import Path

from fastapi import FastAPI, HTTPException, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Optional

import database as db
from models import (
    CreateGameRequest, CreateGameResponse, JoinResponse, GameStatusResponse,
    TurnSubmitRequest, TurnPollResponse, PhaseRequest,
)

app = FastAPI(title="CWS Online Server")


# ── Cross-Origin Isolation headers (required for SharedArrayBuffer) ───────
class COIMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        response.headers["Cross-Origin-Embedder-Policy"] = "require-corp"
        return response

app.add_middleware(COIMiddleware)

# CORS -- allow browser client on any origin during development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    db.init_db()


def _auth(game_code: str, authorization: Optional[str]) -> int:
    """Extract token from Authorization header and authenticate."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    token = authorization[7:]
    side = db.authenticate(game_code, token)
    if side is None:
        raise HTTPException(status_code=403, detail="Invalid token for this game")
    return side


@app.post("/api/games", response_model=CreateGameResponse)
def create_game(body: CreateGameRequest = CreateGameRequest()):
    """Create a new game. Returns game code and token for chosen side."""
    result = db.create_game(creator_side=body.side)
    return CreateGameResponse(**result)


@app.post("/api/games/{code}/join", response_model=JoinResponse)
def join_game(code: str):
    """Join an existing game as Confederate."""
    result = db.join_game(code)
    if result is None:
        raise HTTPException(status_code=404, detail="Game not found or already full")
    return JoinResponse(**result)


@app.get("/api/games/{code}", response_model=GameStatusResponse)
def game_status(code: str):
    """Get game status (no auth required)."""
    result = db.get_game_status(code)
    if result is None:
        raise HTTPException(status_code=404, detail="Game not found")
    return GameStatusResponse(**result)


@app.post("/api/games/{code}/turn")
def submit_turn(code: str, body: TurnSubmitRequest,
                authorization: Optional[str] = Header(None)):
    """Upload a completed turn."""
    side = _auth(code, authorization)
    ok = db.submit_turn(code, side, body.turn_number, body.state)
    if not ok:
        raise HTTPException(status_code=409, detail="Not your turn or wrong turn number")
    return {"ok": True}


@app.post("/api/games/{code}/phase")
def set_game_phase(code: str, body: PhaseRequest,
                   authorization: Optional[str] = Header(None)):
    """Signal a phase change (e.g. 'events' when monthly processing starts)."""
    side = _auth(code, authorization)
    ok = db.set_phase(code, side, body.phase, body.label)
    if not ok:
        raise HTTPException(status_code=404, detail="Game not found")
    return {"ok": True}


@app.post("/api/games/{code}/finish")
def finish_game(code: str, authorization: Optional[str] = Header(None)):
    """Mark a game as finished."""
    _auth(code, authorization)
    db.finish_game(code)
    return {"ok": True}


@app.get("/api/games/{code}/turn", response_model=TurnPollResponse)
def poll_turn(code: str, authorization: Optional[str] = Header(None)):
    """Poll for opponent's completed turn."""
    side = _auth(code, authorization)
    result = db.poll_turn(code, side)
    return TurnPollResponse(**result)


# --------------------------------------------------------------------------- #
#  Static file serving -- MUST be last (catch-all mount)
# --------------------------------------------------------------------------- #
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_CLIENT_DIR = _PROJECT_ROOT / "cws-online" / "client"
_DESKTOP_PY_DIR = _PROJECT_ROOT / "dev" / "python"
_DATA_DIR = _PROJECT_ROOT

# Serve desktop Python files at /desktop_py/
if _DESKTOP_PY_DIR.is_dir():
    app.mount("/desktop_py", StaticFiles(directory=str(_DESKTOP_PY_DIR)), name="desktop_py")

# Serve data files (CWSLEAD.DAT, CITIES.GRD, etc.) at /data_files/
app.mount("/data_files", StaticFiles(directory=str(_DATA_DIR)), name="data_files")

# Client static files (catch-all, must be last)
if _CLIENT_DIR.is_dir():
    app.mount("/", StaticFiles(directory=str(_CLIENT_DIR), html=True), name="static")
