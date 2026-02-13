"""cws_online.py - Online multiplayer client: serialization, HTTP, session.

Handles:
    - state_to_json(g) / state_from_json(g, data): serialize/deserialize game state
    - OnlineClient: HTTP client for communicating with the CWS server
    - Session persistence: save/load/clear ~/.cws/online_session.json
"""

import json
import os
import urllib.request
import urllib.error
from typing import TYPE_CHECKING

from cws_globals import UNION, CONFEDERATE

if TYPE_CHECKING:
    from cws_globals import GameState


# ═══════════════════════════════════════════════════════════════════════════
#  State Serialization — matches the fields saved by _filer_case3()
# ═══════════════════════════════════════════════════════════════════════════

def state_to_json(g: 'GameState') -> dict:
    """Serialize the full game state to a JSON-compatible dict.

    Mirrors the data written by _filer_case3() in cws_data.py.
    """
    armies = [None]  # index 0 unused
    for i in range(1, 41):
        armies.append({
            "name": g.armyname[i],
            "size": g.armysize[i],
            "lead": g.armylead[i],
            "loc": g.armyloc[i],
            "exper": g.armyexper[i],
            "supply": g.supply[i],
            "move": g.armymove[i],
        })

    cities = [None]  # index 0 unused
    for i in range(1, 41):
        cities.append({
            "occupied": g.occupied[i],
            "owner": g.cityp[i],
            "fort": g.fort[i],
        })

    sides = [None]  # index 0 unused
    for i in range(1, 3):
        sides.append({
            "cash": g.cash[i],
            "control": g.control[i],
            "income": g.income[i],
            "victory": g.victory[i],
            "capital": g.capcity[i],
            "fleet": g.fleet[i],
            "navyloc": g.navyloc[i],
            "navymove": g.navymove[i],
            "rr": g.rr[i],
            "tracks": g.tracks[i],
        })

    return {
        "version": 1,
        "month": g.month,
        "year": g.year,
        "usadv": g.usadv,
        "side": g.side,
        "armies": armies,
        "cities": cities,
        "sides": sides,
        "extra": {
            "emancipate": g.emancipate,
            "commerce": g.commerce,
            "raider": g.raider,
            "grudge": g.grudge,
            "pcode": g.pcode,
            "batwon": [0, g.batwon[1], g.batwon[2]],
            "casualty": [0, g.casualty[1], g.casualty[2]],
            "vicflag": [0] + [g.vicflag[i] for i in range(1, 7)],
        },
        "event_log": g.event_log,
    }


def state_from_json(g: 'GameState', data: dict) -> None:
    """Deserialize game state from a JSON dict into the GameState object.

    Mirrors the data read by _filer_case2() in cws_data.py.
    """
    from cws_util import starfin
    from cws_map import usa
    from cws_railroad import tinytrain
    from cws_ui import clrbot

    g.month = data["month"]
    g.year = data["year"]
    g.usadv = data["usadv"]
    saved_side = data["side"]

    # Load armies
    for i in range(1, 41):
        a = data["armies"][i]
        g.armyname[i] = a["name"]
        g.armysize[i] = a["size"]
        g.armylead[i] = a["lead"]
        g.armyloc[i] = a["loc"]
        g.armyexper[i] = a["exper"]
        g.supply[i] = a["supply"]
        g.armymove[i] = a["move"]

        if g.armyloc[i] > 0:
            if g.armyname[i] == g.lname[i]:
                g.lname[i] = ""
            else:
                who = UNION if i <= 20 else CONFEDERATE
                star, fin = starfin(g, who)
                for k in range(star, fin + 1):
                    if g.armyname[i] == g.lname[k]:
                        g.lname[k] = ""
                        break

    # Load cities
    for i in range(1, 41):
        c = data["cities"][i]
        g.occupied[i] = c["occupied"]
        g.cityp[i] = c["owner"]
        g.fort[i] = c["fort"]

    # Load sides
    for i in range(1, 3):
        sd = data["sides"][i]
        g.cash[i] = sd["cash"]
        g.control[i] = sd["control"]
        g.income[i] = sd["income"]
        g.victory[i] = sd["victory"]
        g.capcity[i] = sd["capital"]
        g.fleet[i] = sd["fleet"]
        g.navyloc[i] = sd["navyloc"]
        g.navymove[i] = sd["navymove"]
        g.rr[i] = sd["rr"]
        g.tracks[i] = sd["tracks"]
        g.navysize[i] = len(g.fleet[i])

    # Load extras
    extra = data.get("extra", {})
    g.emancipate = extra.get("emancipate", 0)
    g.commerce = extra.get("commerce", 0)
    g.raider = extra.get("raider", 0)
    g.grudge = extra.get("grudge", 0)
    g.pcode = extra.get("pcode", 0)
    batwon = extra.get("batwon", [0, 0, 0])
    g.batwon[1] = batwon[1]
    g.batwon[2] = batwon[2]
    casualty = extra.get("casualty", [0, 0, 0])
    g.casualty[1] = casualty[1]
    g.casualty[2] = casualty[2]
    vicflag = extra.get("vicflag", [0, 1, 1865, 30, 0, 1, 3])
    for i in range(1, min(7, len(vicflag))):
        g.vicflag[i] = vicflag[i]

    # Load event log (store only, display happens in caller)
    g.event_log = data.get("event_log", [])

    # Redraw
    g.screen.cls()
    usa(g)
    clrbot(g)
    for k in range(1, 3):
        if g.rr[k] > 0:
            tinytrain(g, k, 1)

    g.side = saved_side


# ═══════════════════════════════════════════════════════════════════════════
#  HTTP Client
# ═══════════════════════════════════════════════════════════════════════════

class OnlineClient:
    """HTTP client for the CWS online server."""

    def __init__(self, server_url: str, token: str = "", game_code: str = ""):
        self.server_url = server_url.rstrip("/")
        self.token = token
        self.game_code = game_code

    def _request(self, method: str, path: str, body: dict = None,
                 auth: bool = False) -> dict:
        """Make an HTTP request and return parsed JSON response."""
        url = f"{self.server_url}{path}"
        data = json.dumps(body).encode("utf-8") if body is not None else None
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("User-Agent", "CWS-Online/1.7")
        req.add_header("Content-Type", "application/json")
        if auth and self.token:
            req.add_header("Authorization", f"Bearer {self.token}")
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body_text = e.read().decode("utf-8", errors="replace")
            raise ConnectionError(f"HTTP {e.code}: {body_text}") from e
        except urllib.error.URLError as e:
            raise ConnectionError(f"Connection failed: {e.reason}") from e

    def create_game(self, side: int = 1) -> dict:
        """POST /api/games -> {game_code, token, side}"""
        result = self._request("POST", "/api/games", body={"side": side})
        self.token = result["token"]
        self.game_code = result["game_code"]
        return result

    def join_game(self, game_code: str) -> dict:
        """POST /api/games/{code}/join -> {token, side}"""
        result = self._request("POST", f"/api/games/{game_code}/join")
        self.token = result["token"]
        self.game_code = game_code
        return result

    def game_status(self) -> dict:
        """GET /api/games/{code} -> {status, current_side, turn_number}"""
        return self._request("GET", f"/api/games/{self.game_code}")

    def submit_turn(self, turn_number: int, state: dict) -> dict:
        """POST /api/games/{code}/turn"""
        return self._request("POST", f"/api/games/{self.game_code}/turn",
                             body={"turn_number": turn_number, "state": state},
                             auth=True)

    def poll_turn(self) -> dict:
        """GET /api/games/{code}/turn -> {ready, state, turn_number, phase, phase_label}"""
        return self._request("GET", f"/api/games/{self.game_code}/turn",
                             auth=True)

    def signal_phase(self, phase: str, label: str = "") -> dict:
        """POST /api/games/{code}/phase"""
        return self._request("POST", f"/api/games/{self.game_code}/phase",
                             body={"phase": phase, "label": label},
                             auth=True)


# ═══════════════════════════════════════════════════════════════════════════
#  Session Persistence (~/.cws/online_<code>_<side>.json)
#
#  Each game+side gets its own session file, so two players on the same
#  machine don't collide.
# ═══════════════════════════════════════════════════════════════════════════

def _session_dir() -> str:
    """Return (and create) the session directory."""
    d = os.path.join(os.path.expanduser("~"), ".cws")
    os.makedirs(d, exist_ok=True)
    return d


def _session_path_for(game_code: str, side: int) -> str:
    """Return the session file path for a specific game code and side."""
    return os.path.join(_session_dir(), f"online_{game_code}_{side}.json")


def _is_session_file(name: str) -> bool:
    """Check if a filename matches online_XXXXXX_N.json or legacy online_XXXXXX.json."""
    if not name.startswith("online_") or not name.endswith(".json"):
        return False
    middle = name[7:-5]  # strip "online_" and ".json"
    # New format: XXXXXX_N (6 alphanum + _ + side digit)
    if len(middle) == 8 and middle[6] == '_' and middle[7] in '12':
        return middle[:6].isalnum()
    # Legacy format: XXXXXX (6 alphanum, no side)
    if len(middle) == 6 and middle.isalnum():
        return True
    return False


def session_exists() -> bool:
    """Check if any online session file exists."""
    d = _session_dir()
    return any(_is_session_file(f) for f in os.listdir(d))


def list_sessions() -> list[dict]:
    """Return a list of all saved sessions (for the resume menu)."""
    d = _session_dir()
    sessions = []
    for f in sorted(os.listdir(d)):
        if _is_session_file(f):
            try:
                with open(os.path.join(d, f), "r") as fh:
                    data = json.load(fh)
                    sessions.append(data)
            except (json.JSONDecodeError, OSError):
                pass
    return sessions


def save_session(server_url: str, game_code: str, token: str, my_side: int) -> None:
    """Save the current online session to disk."""
    data = {
        "server_url": server_url,
        "game_code": game_code,
        "token": token,
        "my_side": my_side,
    }
    with open(_session_path_for(game_code, my_side), "w") as f:
        json.dump(data, f, indent=2)


def load_session(game_code: str = "") -> dict | None:
    """Load an online session from disk.

    If game_code is given, load the first session matching that code.
    Otherwise load the first session found.
    """
    sessions = list_sessions()
    if game_code:
        for s in sessions:
            if s.get("game_code") == game_code:
                return s
        return None
    return sessions[0] if sessions else None


def clear_session(game_code: str = "") -> None:
    """Remove online session file(s).

    If game_code given, remove all sessions for that game (both sides).
    Otherwise remove the first one found.
    """
    d = _session_dir()
    if game_code:
        # Remove all files matching this game code (both sides + legacy)
        for f in os.listdir(d):
            if _is_session_file(f) and game_code in f:
                os.remove(os.path.join(d, f))
        return

    # Remove first found
    for f in os.listdir(d):
        if _is_session_file(f):
            os.remove(os.path.join(d, f))
            return
