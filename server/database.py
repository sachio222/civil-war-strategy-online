"""database.py - SQLite schema and CRUD operations for CWS online server.

Side convention: 1 = Union, 2 = Confederate (matches UNION/CONFEDERATE constants in cws_globals.py).
"""

import json
import secrets
import sqlite3
import os
import string
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone


DB_PATH = os.environ.get("CWS_DB_PATH", "cws_online.db")


@contextmanager
def _connect():
    """Yield a sqlite3 connection that is always closed on exit."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    """Create the games table if it doesn't exist."""
    with _connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS games (
                game_code TEXT PRIMARY KEY,
                status TEXT DEFAULT 'waiting',
                union_token TEXT,
                confed_token TEXT,
                current_side INTEGER DEFAULT 1,
                state_json TEXT,
                turn_number INTEGER DEFAULT 0,
                phase TEXT DEFAULT 'playing',
                phase_label TEXT DEFAULT '',
                created_at TEXT,
                updated_at TEXT
            )
        """)
        # Migrate existing databases that lack the phase columns
        try:
            conn.execute("ALTER TABLE games ADD COLUMN phase TEXT DEFAULT 'playing'")
        except sqlite3.OperationalError:
            pass  # column already exists
        try:
            conn.execute("ALTER TABLE games ADD COLUMN phase_label TEXT DEFAULT ''")
        except sqlite3.OperationalError:
            pass  # column already exists
        conn.commit()


def _gen_code(length: int = 6) -> str:
    """Generate a random alphanumeric game code."""
    chars = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(chars) for _ in range(length))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_game(creator_side: int = 1) -> dict:
    """Create a new game. Returns {game_code, token, side}.

    creator_side=1: creator plays Union (token stored as union_token)
    creator_side=2: creator plays Confederate (token stored as confed_token)
    """
    with _connect() as conn:
        game_code = _gen_code()
        # Ensure uniqueness
        while conn.execute("SELECT 1 FROM games WHERE game_code=?", (game_code,)).fetchone():
            game_code = _gen_code()
        token = str(uuid.uuid4())
        now = _now()
        if creator_side == 2:
            conn.execute(
                "INSERT INTO games (game_code, confed_token, created_at, updated_at) VALUES (?, ?, ?, ?)",
                (game_code, token, now, now)
            )
        else:
            conn.execute(
                "INSERT INTO games (game_code, union_token, created_at, updated_at) VALUES (?, ?, ?, ?)",
                (game_code, token, now, now)
            )
        conn.commit()
        return {"game_code": game_code, "token": token, "side": creator_side}


def join_game(game_code: str) -> dict | None:
    """Join an existing game. Returns {token, side} or None if not joinable.

    Assigns the joiner to whichever side the creator did NOT pick.
    """
    with _connect() as conn:
        row = conn.execute("SELECT * FROM games WHERE game_code=?", (game_code,)).fetchone()
        if not row:
            return None
        if row["status"] != "waiting":
            return None
        # Determine which side is open
        if row["union_token"] is None and row["confed_token"] is not None:
            # Creator is Confederate, joiner becomes Union
            joiner_side = 1
            token_col = "union_token"
        elif row["confed_token"] is None and row["union_token"] is not None:
            # Creator is Union, joiner becomes Confederate
            joiner_side = 2
            token_col = "confed_token"
        else:
            # Both filled or both empty — shouldn't happen
            return None
        token = str(uuid.uuid4())
        now = _now()
        conn.execute(
            f"UPDATE games SET {token_col}=?, status='active', updated_at=? WHERE game_code=?",
            (token, now, game_code)
        )
        conn.commit()
        return {"token": token, "side": joiner_side}


def get_game_status(game_code: str) -> dict | None:
    """Get game status. Returns {status, current_side, turn_number} or None."""
    with _connect() as conn:
        row = conn.execute("SELECT status, current_side, turn_number FROM games WHERE game_code=?",
                           (game_code,)).fetchone()
        if not row:
            return None
        return {"status": row["status"], "current_side": row["current_side"],
                "turn_number": row["turn_number"]}


def authenticate(game_code: str, token: str) -> int | None:
    """Verify token and return the player's side (1 or 2), or None."""
    with _connect() as conn:
        row = conn.execute("SELECT union_token, confed_token FROM games WHERE game_code=?",
                           (game_code,)).fetchone()
        if not row:
            return None
        if row["union_token"] == token:
            return 1
        if row["confed_token"] == token:
            return 2
        return None


def submit_turn(game_code: str, side: int, turn_number: int, state: dict) -> bool:
    """Submit a completed turn. Returns True on success."""
    with _connect() as conn:
        row = conn.execute("SELECT current_side, turn_number FROM games WHERE game_code=?",
                           (game_code,)).fetchone()
        if not row:
            return False
        if row["current_side"] != side:
            return False
        if row["turn_number"] != turn_number:
            return False
        new_side = 2 if side == 1 else 1
        now = _now()
        conn.execute(
            "UPDATE games SET state_json=?, current_side=?, turn_number=?, phase='playing', phase_label='', updated_at=? WHERE game_code=?",
            (json.dumps(state), new_side, turn_number + 1, now, game_code)
        )
        conn.commit()
        return True


def poll_turn(game_code: str, side: int) -> dict:
    """Poll for opponent's turn. Returns {ready, state, turn_number, phase, phase_label}."""
    with _connect() as conn:
        row = conn.execute("SELECT current_side, turn_number, state_json, status, phase, phase_label FROM games WHERE game_code=?",
                           (game_code,)).fetchone()
        if not row:
            return {"ready": False, "state": None, "turn_number": 0,
                    "phase": "playing", "phase_label": ""}
        phase = row["phase"] or "playing"
        phase_label = row["phase_label"] or ""
        if row["status"] == "finished":
            state = json.loads(row["state_json"]) if row["state_json"] else None
            return {"ready": True, "state": state, "turn_number": row["turn_number"],
                    "phase": phase, "phase_label": phase_label}
        if row["current_side"] == side and row["state_json"]:
            state = json.loads(row["state_json"])
            return {"ready": True, "state": state, "turn_number": row["turn_number"],
                    "phase": phase, "phase_label": phase_label}
        return {"ready": False, "state": None, "turn_number": row["turn_number"],
                "phase": phase, "phase_label": phase_label}


def set_phase(game_code: str, side: int, phase: str, label: str = "") -> bool:
    """Set the current phase of a game (e.g. 'events' during monthly processing)."""
    with _connect() as conn:
        row = conn.execute("SELECT current_side FROM games WHERE game_code=?", (game_code,)).fetchone()
        if not row:
            return False
        now = _now()
        conn.execute(
            "UPDATE games SET phase=?, phase_label=?, updated_at=? WHERE game_code=?",
            (phase, label, now, game_code)
        )
        conn.commit()
        return True


def finish_game(game_code: str) -> bool:
    """Mark a game as finished."""
    with _connect() as conn:
        now = _now()
        conn.execute("UPDATE games SET status='finished', updated_at=? WHERE game_code=?",
                     (now, game_code))
        conn.commit()
        return True
