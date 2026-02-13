"""server.py - FastAPI app for CWS online multiplayer.

Run:
    cd server
    pip install fastapi uvicorn
    uvicorn server:app --host 0.0.0.0 --port 1861
"""

from fastapi import FastAPI, HTTPException, Header
from typing import Optional

import database as db
from models import (
    CreateGameRequest, CreateGameResponse, JoinResponse, GameStatusResponse,
    TurnSubmitRequest, TurnPollResponse, PhaseRequest,
)

app = FastAPI(title="CWS Online Server")


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


@app.get("/api/games/{code}/turn", response_model=TurnPollResponse)
def poll_turn(code: str, authorization: Optional[str] = Header(None)):
    """Poll for opponent's completed turn."""
    side = _auth(code, authorization)
    result = db.poll_turn(code, side)
    return TurnPollResponse(**result)
