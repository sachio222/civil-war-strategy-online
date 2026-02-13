"""game.py -- Canvas-only game controller / state machine.

Port of game.js. Exact QBasic SCREEN 12 port: everything rendered on a
single 640x480 canvas. Keyboard-driven menu navigation matching QBasic INKEY$.

State machine with ~25 states (vs the JS version's 11), adding all missing
QBasic command states.
"""

import asyncio
from constants import (
    VGA, GamePhase, MAIN_MENU, COMMANDS_MENU, END_TURN_MENU,
    Side, SIDE_NAMES,
)
import font
import sprites
import map_renderer
import ui
import api_client
import ws_client
import reports
import utility
import save_load
import sound
import animation
import victory_screen
import hot_seat
import title_screen
from js_bridge import log, warn, set_interval, clear_interval, get_context, get_canvas, set_timeout

# --------------------------------------------------------------------------- #
#  State
# --------------------------------------------------------------------------- #
_canvas = None
_ctx = None
_game_state = None
_player_side = 1
_game_code = ""
_pending_orders = []
_poll_timer = None
POLL_INTERVAL = 5000

# Menu / UI state
_current_state = GamePhase.LOADING
_menu_selected = 0
_menu_options = []
_menu_title = ""
_menu_tlx = 67
_menu_tly = 13
_replay_active = False
_replay_task = None
_menu_colour = 4
_menu_hilite = 11
_move_source_army = None
_battle_result = None
_report_lines = None
_status_message = ""
_status_color = 15

# Cached IDs for menus
_menu_army_ids = []
_menu_city_ids = []

# Map rendering cache -- avoids re-running expensive snapToVGA + floodFill
# on every menu navigation key press.  Uses an offscreen <canvas> instead of
# ImageData to avoid unreliable JsProxy-wrapped ImageData across Pyodide.
_offscreen_canvas = None
_offscreen_ctx = None
_map_dirty = True


# --------------------------------------------------------------------------- #
#  Canvas setup
# --------------------------------------------------------------------------- #
def _init_canvas():
    global _canvas, _ctx
    _canvas = get_canvas("gameCanvas")
    if _canvas is None:
        log("[game] Canvas element not found.")
        return
    _ctx = get_context(_canvas)


# --------------------------------------------------------------------------- #
#  Status message helper
# --------------------------------------------------------------------------- #
def _set_status(msg: str = "", color: int = 15):
    global _status_message, _status_color
    _status_message = msg
    _status_color = color


# --------------------------------------------------------------------------- #
#  Offscreen canvas for map cache
# --------------------------------------------------------------------------- #
def _ensure_offscreen_canvas():
    global _offscreen_canvas, _offscreen_ctx
    if _offscreen_canvas is not None:
        return
    from js import document  # type: ignore
    _offscreen_canvas = document.createElement("canvas")
    _offscreen_canvas.width = 640
    _offscreen_canvas.height = 480
    _offscreen_ctx = _offscreen_canvas.getContext("2d")
    _offscreen_ctx.imageSmoothingEnabled = False


# --------------------------------------------------------------------------- #
#  Rendering pipeline
# --------------------------------------------------------------------------- #
def render():
    """Main render function -- draws the entire screen based on current state."""
    if _ctx is None or _game_state is None:
        return

    _ctx.imageSmoothingEnabled = False

    # Full-screen report mode
    if _current_state == GamePhase.REPORT:
        ui.draw_report(_ctx, _report_lines)
        return

    # Event replay: managed by show_event_replay coroutine, don't redraw
    if _current_state == GamePhase.EVENT_REPLAY:
        return

    # Victory screen (drawn by victory_screen module, don't redraw)
    if _current_state == GamePhase.VICTORY:
        return

    # Hot-seat blank screen
    if _current_state == GamePhase.HOT_SEAT_BLANK:
        hot_seat.draw_blank_screen(_ctx, _player_side)
        return

    # Title screen (drawn by title_screen module)
    if _current_state == GamePhase.TITLE_SCREEN:
        return

    # 1. Clear to black
    _ctx.fillStyle = "#000000"
    _ctx.fillRect(0, 0, 640, 480)

    # 2. Draw the map (use offscreen canvas cache to avoid expensive snapToVGA + floodFill)
    global _map_dirty
    _ensure_offscreen_canvas()
    if _map_dirty:
        # Clear the offscreen canvas fully before re-rendering to prevent
        # stale pixels from a previous render affecting snapToVGA/floodFill.
        _offscreen_ctx.fillStyle = "#000000"
        _offscreen_ctx.fillRect(0, 0, 640, 480)
        try:
            map_renderer.draw_map(_offscreen_ctx, _game_state)
        except Exception as e:
            from js_bridge import warn
            warn(f"[game] draw_map error: {e}")
        _map_dirty = False
    _ctx.drawImage(_offscreen_canvas, 0, 0)

    # 3. Draw topbar
    ui.topbar(_ctx, _game_state)

    # 4. Draw army stats if relevant
    if _current_state in (GamePhase.MOVE_FROM, GamePhase.MOVE_TO,
                          GamePhase.RAILROAD, GamePhase.RAILROAD_DEST):
        army = _get_highlighted_army()
        if army:
            ui.army_stat(_ctx, army)

    # 5. Draw current menu
    _draw_current_menu()

    # 6. Waiting popup
    if _current_state == GamePhase.WAITING:
        opp_name = "REBEL" if _player_side == 1 else "UNION"
        ui.draw_waiting(_ctx, opp_name)

    # 7. Battle display
    if _current_state == GamePhase.BATTLE_DISPLAY:
        animation.draw_cannon_scene(_ctx)
        ui.draw_battle_result(_ctx, _battle_result)

    # 8. Bottom status
    if _status_message:
        ui.print_message(_ctx, _status_message, _status_color)


def _get_highlighted_army():
    if not _menu_army_ids or _menu_selected >= len(_menu_army_ids):
        return None
    army_id = _menu_army_ids[_menu_selected]
    armies = _game_state.get("armies", {}) if isinstance(
        _game_state, dict) else {}
    return armies.get(str(army_id)) or armies.get(army_id)


def _draw_current_menu():
    if not _menu_options:
        return
    if _current_state in (GamePhase.WAITING, GamePhase.BATTLE_DISPLAY,
                          GamePhase.REPORT, GamePhase.LOADING, GamePhase.VICTORY,
                          GamePhase.HOT_SEAT_BLANK, GamePhase.TITLE_SCREEN,
                          GamePhase.EVENT_REPLAY):
        return
    ui.draw_menu(_ctx, _menu_title, _menu_options, _menu_selected,
                 _menu_tlx, _menu_tly, _menu_colour, _menu_hilite)


# --------------------------------------------------------------------------- #
#  State transitions
# --------------------------------------------------------------------------- #
def _enter_state(new_state: str):
    global _current_state, _menu_selected, _menu_options
    _current_state = new_state
    _menu_selected = 0

    if new_state == GamePhase.MAIN_MENU:
        _setup_main_menu()
    elif new_state == GamePhase.RECRUIT:
        _build_recruit_menu()
    elif new_state == GamePhase.MOVE_FROM:
        _build_move_from_menu()
    elif new_state == GamePhase.MOVE_TO:
        _build_move_to_menu()
    elif new_state == GamePhase.RAILROAD:
        _build_railroad_menu()
    elif new_state == GamePhase.RAILROAD_DEST:
        _build_railroad_dest_menu()
    elif new_state == GamePhase.NAVAL:
        _setup_naval_menu()
    elif new_state == GamePhase.COMMANDS:
        _setup_commands_menu()
    elif new_state == GamePhase.END_TURN_CONFIRM:
        _setup_end_turn_menu()
    elif new_state == GamePhase.WAITING:
        _setup_waiting()
    elif new_state == GamePhase.BATTLE_DISPLAY:
        _setup_battle_display()
    elif new_state == GamePhase.FORTIFY:
        _build_fortify_menu()
        render()
        return
    elif new_state == GamePhase.CMD_COMBINE:
        _build_combine_menu()
    elif new_state == GamePhase.CMD_SUPPLY:
        _build_supply_menu()
    elif new_state == GamePhase.CMD_CAPITAL:
        _build_capital_menu()
    elif new_state == GamePhase.CMD_DETACH:
        _build_detach_menu()
    elif new_state == GamePhase.CMD_DRILL:
        _build_drill_menu()
    elif new_state == GamePhase.CMD_RELIEVE:
        _build_relieve_menu()
    elif new_state == GamePhase.UTILITY:
        _build_utility_menu()
    elif new_state == GamePhase.SAVE_LOAD:
        _build_save_load_menu()
    elif new_state == GamePhase.REPORT:
        _menu_options = []
    elif new_state == GamePhase.VICTORY:
        _menu_options = []
    elif new_state == GamePhase.HOT_SEAT_BLANK:
        _menu_options = []
    elif new_state == GamePhase.TITLE_SCREEN:
        _menu_options = []
    elif new_state == GamePhase.EVENT_REPLAY:
        _menu_options = []

    render()


def _setup_main_menu():
    global _menu_title, _menu_options, _menu_tlx, _menu_tly, _menu_colour, _menu_hilite
    global _menu_army_ids, _menu_city_ids, _move_source_army
    _menu_title = "Main"
    _menu_options = list(MAIN_MENU)
    _menu_tlx = 67
    _menu_tly = 13
    _menu_colour = 4
    _menu_hilite = 11
    _menu_army_ids = []
    _menu_city_ids = []
    _move_source_army = None
    _set_status("Select an option with arrow keys, Enter to confirm.", 7)


def _enter_main_menu_keep_status():
    """Return to main menu without overwriting the status message.

    Used after commands that set a meaningful result message (e.g. recruit)
    so the player can read what happened.
    """
    global _current_state, _menu_selected, _menu_title, _menu_options
    global _menu_tlx, _menu_tly, _menu_colour, _menu_hilite
    global _menu_army_ids, _menu_city_ids, _move_source_army
    _current_state = GamePhase.MAIN_MENU
    _menu_selected = 0
    _menu_title = "Main"
    _menu_options = list(MAIN_MENU)
    _menu_tlx = 67
    _menu_tly = 13
    _menu_colour = 4
    _menu_hilite = 11
    _menu_army_ids = []
    _menu_city_ids = []
    _move_source_army = None
    # Deliberately do NOT call _set_status — keep the previous message
    render()


def _setup_naval_menu():
    global _menu_title, _menu_options, _menu_tlx, _menu_tly, _menu_colour, _menu_hilite
    _menu_title = "Naval"
    _menu_options = ["Return"]
    _menu_tlx = 67
    _menu_tly = 13
    _menu_colour = 1
    _menu_hilite = 11
    _set_status("Naval operations not yet available.", 12)


def _setup_commands_menu():
    global _menu_title, _menu_options, _menu_tlx, _menu_tly, _menu_colour, _menu_hilite
    _menu_title = "Commands"
    _menu_options = list(COMMANDS_MENU)
    _menu_tlx = 67
    _menu_tly = 13
    _menu_colour = 4
    _menu_hilite = 14
    _set_status("Select a command.", 7)


def _setup_end_turn_menu():
    global _menu_title, _menu_options, _menu_tlx, _menu_tly, _menu_colour, _menu_hilite
    _menu_title = "End Turn?"
    _menu_options = list(END_TURN_MENU)
    _menu_tlx = 67
    _menu_tly = 15
    _menu_colour = 4
    _menu_hilite = 14
    order_count = len(_pending_orders)
    _set_status(f"{order_count} order(s) queued. End turn?", 14)


def _setup_waiting():
    global _menu_options
    _menu_options = []
    _set_status("Waiting for opponent...", 14)


def _setup_battle_display():
    global _menu_options
    _menu_options = []
    _set_status("Battle in progress! Press any key.", 12)


# --------------------------------------------------------------------------- #
#  Menu builders
# --------------------------------------------------------------------------- #
def _get_val(obj, key, default=0):
    """Helper to get a value from either a dict or a JsProxy object."""
    if isinstance(obj, dict):
        return obj.get(key, default)
    if hasattr(obj, key):
        return getattr(obj, key)
    try:
        return obj[key]
    except Exception:
        return default


def _build_recruit_menu():
    global _menu_title, _menu_options, _menu_tlx, _menu_tly, _menu_colour, _menu_hilite
    global _menu_city_ids

    cities = _game_state.get("cities", {}) if isinstance(
        _game_state, dict) else {}
    armies = _game_state.get("armies", {}) if isinstance(
        _game_state, dict) else {}
    occupied = _game_state.get("occupied", {}) if isinstance(
        _game_state, dict) else {}
    cash = _game_state.get("cash", {}) if isinstance(_game_state, dict) else {}
    my_cash = int(_get_val(cash, str(_player_side),
                  _get_val(cash, _player_side, 0)))
    opts = []
    _menu_city_ids = []

    for key in cities:
        c = cities[key]
        if _get_val(c, "owner") != _player_side:
            continue
        cid = _get_val(c, "id", 0)
        name = str(_get_val(c, "name", "?"))[:10]
        # Show what will happen: reinforce or new army
        occ_id = occupied.get(str(cid), occupied.get(cid, 0))
        occ = armies.get(str(occ_id)) or armies.get(occ_id) if occ_id else None
        if occ and int(_get_val(occ, "size", 0)) > 0:
            army_name = str(_get_val(occ, "name", "?"))[:6]
            opts.append(f"{name} +{army_name}")
        else:
            opts.append(f"{name} *NEW*")
        _menu_city_ids.append(cid)

    if not opts:
        opts = ["(No cities)"]
        _menu_city_ids = [0]

    _menu_title = "Recruit"
    _menu_options = opts
    _menu_tlx = 67
    _menu_tly = 13
    _menu_colour = 2
    _menu_hilite = 10
    cost_note = f"Cost $100. Cash: ${my_cash}" if my_cash >= 100 else f"Need $100! Cash: ${my_cash}"
    _set_status(f"Select city to recruit. {cost_note}. ESC cancel.", 7)


def _build_move_from_menu():
    global _menu_title, _menu_options, _menu_tlx, _menu_tly, _menu_colour, _menu_hilite
    global _menu_army_ids

    armies = _game_state.get("armies", {}) if isinstance(
        _game_state, dict) else {}
    cities = _game_state.get("cities", {}) if isinstance(
        _game_state, dict) else {}
    opts = []
    _menu_army_ids = []

    for key in armies:
        a = armies[key]
        aid = _get_val(a, "id", 0)
        army_side = 1 if aid <= 20 else 2
        if army_side == _player_side and _get_val(a, "size", 0) > 0 and _get_val(a, "location", 0) > 0:
            city = cities.get(str(_get_val(a, "location"))
                              ) or cities.get(_get_val(a, "location"))
            city_name = str(_get_val(city, "name", "?"))[:8] if city else "?"
            army_name = str(_get_val(a, "name", "?"))[:8]
            opts.append(f"{army_name} {city_name}")
            _menu_army_ids.append(aid)

    if not opts:
        opts = ["(No armies)"]
        _menu_army_ids = [0]

    _menu_title = "Move Army"
    _menu_options = opts
    _menu_tlx = 67
    _menu_tly = 13
    _menu_colour = 4
    _menu_hilite = 11
    _set_status("Select army to move. ESC to cancel.", 7)


def _build_move_to_menu():
    global _menu_title, _menu_options, _menu_tlx, _menu_tly, _menu_colour, _menu_hilite
    global _menu_city_ids

    if not _move_source_army:
        _enter_state(GamePhase.MAIN_MENU)
        return

    cities = _game_state.get("cities", {}) if isinstance(
        _game_state, dict) else {}
    src_loc = _get_val(_move_source_army, "location", 0)
    src_city = cities.get(str(src_loc)) or cities.get(src_loc)
    if not src_city:
        _enter_state(GamePhase.MAIN_MENU)
        return

    adj = _get_val(src_city, "adjacency", [])
    # Handle JsProxy arrays
    if not isinstance(adj, list):
        try:
            adj = list(adj)
        except Exception:
            adj = []

    opts = []
    _menu_city_ids = []

    for dest_id in adj:
        if dest_id <= 0:
            continue
        dest = cities.get(str(dest_id)) or cities.get(dest_id)
        if dest:
            opts.append(str(_get_val(dest, "name", "?"))[:12])
            _menu_city_ids.append(_get_val(dest, "id"))

    if not opts:
        opts = ["(No destinations)"]
        _menu_city_ids = [0]

    army_name = str(_get_val(_move_source_army, "name", "?"))
    _menu_title = "Move To"
    _menu_options = opts
    _menu_tlx = 67
    _menu_tly = 13
    _menu_colour = 4
    _menu_hilite = 14
    _set_status(f"{army_name}: select destination. ESC to cancel.", 11)


def _build_railroad_menu():
    global _menu_title, _menu_options, _menu_tlx, _menu_tly, _menu_colour, _menu_hilite
    global _menu_army_ids

    armies = _game_state.get("armies", {}) if isinstance(
        _game_state, dict) else {}
    cities = _game_state.get("cities", {}) if isinstance(
        _game_state, dict) else {}
    opts = []
    _menu_army_ids = []

    for key in armies:
        a = armies[key]
        aid = _get_val(a, "id", 0)
        army_side = 1 if aid <= 20 else 2
        if army_side == _player_side and _get_val(a, "size", 0) > 0 and _get_val(a, "location", 0) > 0:
            city = cities.get(str(_get_val(a, "location"))
                              ) or cities.get(_get_val(a, "location"))
            city_name = str(_get_val(city, "name", "?"))[:8] if city else "?"
            army_name = str(_get_val(a, "name", "?"))[:8]
            opts.append(f"{army_name} {city_name}")
            _menu_army_ids.append(aid)

    if not opts:
        opts = ["(No armies)"]
        _menu_army_ids = [0]

    _menu_title = "Railroad"
    _menu_options = opts
    _menu_tlx = 67
    _menu_tly = 13
    _menu_colour = 6
    _menu_hilite = 14
    _set_status("Select army for railroad. ESC to cancel.", 7)


def _build_railroad_dest_menu():
    global _menu_title, _menu_options, _menu_tlx, _menu_tly, _menu_colour, _menu_hilite
    global _menu_city_ids

    if not _move_source_army:
        _enter_state(GamePhase.MAIN_MENU)
        return

    cities = _game_state.get("cities", {}) if isinstance(
        _game_state, dict) else {}
    src_loc = _get_val(_move_source_army, "location", 0)
    src_city = cities.get(str(src_loc)) or cities.get(src_loc)
    if not src_city:
        _enter_state(GamePhase.MAIN_MENU)
        return

    adj = _get_val(src_city, "adjacency", [])
    if not isinstance(adj, list):
        try:
            adj = list(adj)
        except Exception:
            adj = []

    opts = []
    _menu_city_ids = []

    for dest_id in adj:
        if dest_id <= 0:
            continue
        dest = cities.get(str(dest_id)) or cities.get(dest_id)
        if dest:
            opts.append(str(_get_val(dest, "name", "?"))[:12])
            _menu_city_ids.append(_get_val(dest, "id"))

    if not opts:
        opts = ["(No destinations)"]
        _menu_city_ids = [0]

    army_name = str(_get_val(_move_source_army, "name", "?"))
    _menu_title = "RR Dest"
    _menu_options = opts
    _menu_tlx = 67
    _menu_tly = 13
    _menu_colour = 6
    _menu_hilite = 14
    _set_status(f"{army_name}: select RR destination. ESC cancel.", 11)


def _build_fortify_menu():
    global _menu_title, _menu_options, _menu_tlx, _menu_tly, _menu_colour, _menu_hilite
    global _menu_city_ids, _current_state, _menu_selected

    cities = _game_state.get("cities", {}) if isinstance(
        _game_state, dict) else {}
    opts = []
    _menu_city_ids = []

    for key in cities:
        c = cities[key]
        if _get_val(c, "owner") == _player_side:
            opts.append(str(_get_val(c, "name", "?"))[:12])
            _menu_city_ids.append(_get_val(c, "id"))

    if not opts:
        _set_status("No cities to fortify.", 12)
        _enter_state(GamePhase.MAIN_MENU)
        return

    _menu_title = "Fortify"
    _menu_options = opts
    _menu_selected = 0
    _menu_tlx = 67
    _menu_tly = 13
    _menu_colour = 2
    _menu_hilite = 10
    _current_state = GamePhase.FORTIFY
    _set_status("Select city to fortify. ESC to cancel.", 7)


def _build_combine_menu():
    global _menu_title, _menu_options, _menu_tlx, _menu_tly, _menu_colour, _menu_hilite
    global _menu_army_ids

    armies = _game_state.get("armies", {}) if isinstance(
        _game_state, dict) else {}
    opts = []
    _menu_army_ids = []

    for key in armies:
        a = armies[key]
        aid = _get_val(a, "id", 0)
        army_side = 1 if aid <= 20 else 2
        if army_side == _player_side and _get_val(a, "size", 0) > 0 and _get_val(a, "location", 0) > 0:
            opts.append(str(_get_val(a, "name", "?"))[:12])
            _menu_army_ids.append(aid)

    if not opts:
        _set_status("No armies to combine.", 12)
        _enter_state(GamePhase.MAIN_MENU)
        return

    _menu_title = "Combine"
    _menu_options = opts
    _menu_tlx = 67
    _menu_tly = 13
    _menu_colour = 5
    _menu_hilite = 13
    _set_status("Select army to combine into. ESC to cancel.", 7)


def _build_supply_menu():
    global _menu_title, _menu_options, _menu_tlx, _menu_tly, _menu_colour, _menu_hilite
    global _menu_army_ids

    armies = _game_state.get("armies", {}) if isinstance(
        _game_state, dict) else {}
    opts = []
    _menu_army_ids = []

    for key in armies:
        a = armies[key]
        aid = _get_val(a, "id", 0)
        army_side = 1 if aid <= 20 else 2
        if army_side == _player_side and _get_val(a, "size", 0) > 0:
            opts.append(str(_get_val(a, "name", "?"))[:12])
            _menu_army_ids.append(aid)

    if not opts:
        _set_status("No armies to supply.", 12)
        _enter_state(GamePhase.MAIN_MENU)
        return

    _menu_title = "Supply"
    _menu_options = opts
    _menu_tlx = 67
    _menu_tly = 13
    _menu_colour = 2
    _menu_hilite = 10
    _set_status("Select army to resupply. ESC to cancel.", 7)


def _build_capital_menu():
    global _menu_title, _menu_options, _menu_tlx, _menu_tly, _menu_colour, _menu_hilite
    global _menu_city_ids

    cities = _game_state.get("cities", {}) if isinstance(
        _game_state, dict) else {}
    opts = []
    _menu_city_ids = []

    for key in cities:
        c = cities[key]
        if _get_val(c, "owner") == _player_side:
            opts.append(str(_get_val(c, "name", "?"))[:12])
            _menu_city_ids.append(_get_val(c, "id"))

    if not opts:
        _set_status("No cities for capital.", 12)
        _enter_state(GamePhase.MAIN_MENU)
        return

    _menu_title = "Capital"
    _menu_options = opts
    _menu_tlx = 67
    _menu_tly = 13
    _menu_colour = 3
    _menu_hilite = 11
    _set_status("Select new capital city (cost 500). ESC cancel.", 7)


def _build_detach_menu():
    global _menu_title, _menu_options, _menu_tlx, _menu_tly, _menu_colour, _menu_hilite
    global _menu_army_ids

    armies = _game_state.get("armies", {}) if isinstance(
        _game_state, dict) else {}
    opts = []
    _menu_army_ids = []

    for key in armies:
        a = armies[key]
        aid = _get_val(a, "id", 0)
        army_side = 1 if aid <= 20 else 2
        if army_side == _player_side and _get_val(a, "size", 0) > 1:
            opts.append(str(_get_val(a, "name", "?"))[:12])
            _menu_army_ids.append(aid)

    if not opts:
        _set_status("No armies large enough to detach.", 12)
        _enter_state(GamePhase.MAIN_MENU)
        return

    _menu_title = "Detach"
    _menu_options = opts
    _menu_tlx = 67
    _menu_tly = 13
    _menu_colour = 5
    _menu_hilite = 13
    _set_status("Select army to split. ESC to cancel.", 7)


def _build_drill_menu():
    global _menu_title, _menu_options, _menu_tlx, _menu_tly, _menu_colour, _menu_hilite
    global _menu_army_ids

    armies = _game_state.get("armies", {}) if isinstance(
        _game_state, dict) else {}
    opts = []
    _menu_army_ids = []

    for key in armies:
        a = armies[key]
        aid = _get_val(a, "id", 0)
        army_side = 1 if aid <= 20 else 2
        if army_side == _player_side and _get_val(a, "size", 0) > 0 and _get_val(a, "experience", 0) < 10:
            opts.append(str(_get_val(a, "name", "?"))[:12])
            _menu_army_ids.append(aid)

    if not opts:
        _set_status("No armies to drill.", 12)
        _enter_state(GamePhase.MAIN_MENU)
        return

    _menu_title = "Drill"
    _menu_options = opts
    _menu_tlx = 67
    _menu_tly = 13
    _menu_colour = 6
    _menu_hilite = 14
    _set_status("Select army to drill. ESC to cancel.", 7)


def _build_relieve_menu():
    global _menu_title, _menu_options, _menu_tlx, _menu_tly, _menu_colour, _menu_hilite
    global _menu_army_ids

    armies = _game_state.get("armies", {}) if isinstance(
        _game_state, dict) else {}
    opts = []
    _menu_army_ids = []

    for key in armies:
        a = armies[key]
        aid = _get_val(a, "id", 0)
        army_side = 1 if aid <= 20 else 2
        if army_side == _player_side and _get_val(a, "size", 0) > 0:
            opts.append(str(_get_val(a, "name", "?"))[:12])
            _menu_army_ids.append(aid)

    if not opts:
        _set_status("No armies to relieve.", 12)
        _enter_state(GamePhase.MAIN_MENU)
        return

    _menu_title = "Relieve"
    _menu_options = opts
    _menu_tlx = 67
    _menu_tly = 13
    _menu_colour = 4
    _menu_hilite = 12
    _set_status("Select army to relieve commander. ESC cancel.", 7)


# --------------------------------------------------------------------------- #
#  Menu selection handlers
# --------------------------------------------------------------------------- #
def _on_menu_select(index: int):
    if _current_state == "reports_menu":
        _handle_reports_menu_select(index)
        return
    if _current_state == GamePhase.MAIN_MENU:
        _handle_main_menu_select(index)
    elif _current_state == GamePhase.RECRUIT:
        _handle_recruit_select(index)
    elif _current_state == GamePhase.MOVE_FROM:
        _handle_move_from_select(index)
    elif _current_state == GamePhase.MOVE_TO:
        _handle_move_to_select(index)
    elif _current_state == GamePhase.RAILROAD:
        _handle_railroad_select(index)
    elif _current_state == GamePhase.RAILROAD_DEST:
        _handle_railroad_dest_select(index)
    elif _current_state == GamePhase.NAVAL:
        _enter_state(GamePhase.MAIN_MENU)
    elif _current_state == GamePhase.COMMANDS:
        _handle_commands_select(index)
    elif _current_state == GamePhase.END_TURN_CONFIRM:
        _handle_end_turn_select(index)
    elif _current_state == GamePhase.FORTIFY:
        _handle_fortify_select(index)
    elif _current_state == GamePhase.CMD_COMBINE:
        _handle_combine_select(index)
    elif _current_state == GamePhase.CMD_SUPPLY:
        _handle_supply_select(index)
    elif _current_state == GamePhase.CMD_CAPITAL:
        _handle_capital_select(index)
    elif _current_state == GamePhase.CMD_DETACH:
        _handle_detach_select(index)
    elif _current_state == GamePhase.CMD_DRILL:
        _handle_drill_select(index)
    elif _current_state == GamePhase.CMD_RELIEVE:
        _handle_relieve_select(index)
    elif _current_state == GamePhase.UTILITY:
        _handle_utility_select(index)
    elif _current_state == GamePhase.SAVE_LOAD:
        _handle_save_load_select(index)


def _handle_main_menu_select(index: int):
    if index == 0:    # Troops
        _enter_state(GamePhase.RECRUIT)
    elif index == 1:  # Moves
        _enter_state(GamePhase.MOVE_FROM)
    elif index == 2:  # Ships
        _enter_state(GamePhase.NAVAL)
    elif index == 3:  # Railroad
        _enter_state(GamePhase.RAILROAD)
    elif index == 4:  # END TURN
        _enter_state(GamePhase.END_TURN_CONFIRM)
    elif index == 5:  # Inform (Reports)
        _build_reports_menu()
    elif index == 6:  # COMMANDS
        _enter_state(GamePhase.COMMANDS)
    elif index == 7:  # UTILITY
        _enter_state(GamePhase.UTILITY)
    elif index == 8:  # Files (Save/Load)
        _enter_state(GamePhase.SAVE_LOAD)


def _flash_city(city_id):
    """Fire-and-forget city flash animation on the main canvas."""
    cities = _game_state.get("cities", {}) if isinstance(
        _game_state, dict) else {}
    city = cities.get(str(city_id)) or cities.get(city_id)
    if city and _ctx:
        asyncio.ensure_future(animation.flash_city(_ctx, city))


# --------------------------------------------------------------------------- #
#  Event Replay — animates opponent's turn events on Canvas
# --------------------------------------------------------------------------- #

_SNAP_KEYS = [
    "armyloc", "armymove", "armysize", "armyname", "armylead",
    "armyexper", "supply", "occupied", "fort", "cityp",
    "navyloc", "navysize", "fleet", "victory", "capcity",
]


def _gs_get_list(gs, key):
    """Get a list field from game state, handling dict vs JsProxy."""
    if isinstance(gs, dict):
        return gs.get(key, [])
    try:
        return gs[key]
    except Exception:
        return []


def _gs_set_list(gs, key, vals):
    """Set a list field on game state."""
    if isinstance(gs, dict):
        gs[key] = vals
    else:
        try:
            gs[key] = vals
        except Exception:
            pass


def _replay_draw_map():
    """Redraw the full map using current _game_state onto the main canvas."""
    if _ctx is None or _game_state is None:
        return
    _ctx.fillStyle = "#000000"
    _ctx.fillRect(0, 0, 640, 480)
    try:
        map_renderer.draw_map(_ctx, _game_state)
    except Exception:
        pass
    ui.topbar(_ctx, _game_state)


def _replay_get_city_pos(city_id):
    """Get (x, y) for a city from the current game state."""
    cities = _game_state.get("cities", {}) if isinstance(_game_state, dict) else {}
    city = cities.get(str(city_id)) or cities.get(city_id)
    if city:
        cx = city.get("x", 0) if isinstance(city, dict) else getattr(city, "x", 0)
        cy = city.get("y", 0) if isinstance(city, dict) else getattr(city, "y", 0)
        return cx, cy
    return 0, 0


def _replay_update_army(army_id, location=None, move_target=None, size=None):
    """Update army fields in _game_state for replay state tracking."""
    if _game_state is None:
        return
    armies = _game_state.get("armies", {}) if isinstance(_game_state, dict) else {}
    army = armies.get(str(army_id)) or armies.get(army_id)
    if not army:
        return
    if isinstance(army, dict):
        if location is not None:
            army["location"] = location
        if move_target is not None:
            army["move_target"] = move_target
        if size is not None:
            army["size"] = size
    else:
        if location is not None:
            try:
                army.location = location
            except Exception:
                pass
        if move_target is not None:
            try:
                army.move_target = move_target
            except Exception:
                pass
        if size is not None:
            try:
                army.size = size
            except Exception:
                pass


def _replay_update_city_owner(city_id, side):
    """Update city ownership in _game_state for replay."""
    if _game_state is None:
        return
    cities = _game_state.get("cities", {}) if isinstance(_game_state, dict) else {}
    city = cities.get(str(city_id)) or cities.get(city_id)
    if city:
        if isinstance(city, dict):
            city["owner"] = side
        else:
            try:
                city.owner = side
            except Exception:
                pass


async def show_event_replay(event_log, post_state):
    """Replay captured events from opponent's turn with Canvas animations.

    Mirrors the desktop _show_event_replay() in cws_main.py.
    Processes event_log entries sequentially with delays/animations,
    then restores the final post-state and returns to main menu.

    Args:
        event_log: list of event dicts from the server
        post_state: the final game state dict (to restore after replay)
    """
    global _game_state, _map_dirty, _replay_active

    if not event_log or _ctx is None:
        return

    _replay_active = True
    _enter_state(GamePhase.EVENT_REPLAY)

    # Parse event log: extract month header, snapshot, and events
    month_label = ""
    snapshot = None
    events = []
    for evt in event_log:
        if isinstance(evt, str) and evt.startswith("__month__:"):
            month_label = evt[len("__month__:"):]
        elif isinstance(evt, dict) and evt.get("type") == "__snapshot__":
            snapshot = evt
        else:
            events.append(evt)

    if not events:
        _replay_active = False
        return

    # Save post-state, restore pre-turn state from snapshot if available
    if snapshot and _game_state:
        for key in _SNAP_KEYS:
            if key in snapshot:
                _gs_set_list(_game_state, key, list(snapshot[key]))
        if "commerce" in snapshot:
            if isinstance(_game_state, dict):
                _game_state["commerce"] = snapshot["commerce"]
        if "raider" in snapshot:
            if isinstance(_game_state, dict):
                _game_state["raider"] = snapshot["raider"]

    # Redraw map at pre-turn positions
    _map_dirty = True
    _replay_draw_map()

    # Header
    header = f"Update for {month_label}" if month_label else "Monthly Events"
    font.print_text(_ctx, 1, 20, header, 14)
    prompt = f"Events for {month_label}" if month_label else "Events replay"
    ui.print_message(_ctx, prompt, 11)
    await asyncio.sleep(1.5)

    # Process each event
    for evt in events:
        if not _replay_active:
            break

        # Plain string events (misc messages)
        if isinstance(evt, str):
            ui.print_message(_ctx, evt[:79], 11)
            await asyncio.sleep(0.6)
            continue

        etype = evt.get("type", "")

        # ──────── Army Movement ────────
        if etype == "move":
            ui.print_message(_ctx, evt.get("msg", "")[:79], 11)
            army_id = evt.get("army_id", 0)
            to_city = evt.get("to", 0)
            _replay_update_army(army_id, location=to_city, move_target=0)
            _map_dirty = True
            _replay_draw_map()
            await asyncio.sleep(0.4)

        # ──────── Out of Supply ────────
        elif etype == "no_supply":
            ui.print_message(_ctx, evt.get("msg", "")[:79], 13)
            await asyncio.sleep(0.5)

        # ──────── Friendly Meeting ────────
        elif etype == "meeting":
            ui.print_message(_ctx, evt.get("msg", "")[:79], 11)
            city_id = evt.get("city", 0)
            if city_id:
                _flash_city(city_id)
            await asyncio.sleep(0.5)

        # ──────── Attack ────────
        elif etype == "attack":
            ui.print_message(_ctx, evt.get("msg", "")[:79], 11)
            city_id = evt.get("city", 0)
            if city_id:
                cx, cy = _replay_get_city_pos(city_id)
                if cx > 0:
                    # Draw explosion circles
                    for r in range(4, 11):
                        _ctx.beginPath()
                        _ctx.arc(cx, cy, r, 0, 6.283)
                        _ctx.fillStyle = VGA[14]
                        _ctx.fill()
                    await asyncio.sleep(0.3)
            await asyncio.sleep(0.3)

        # ──────── Battle ────────
        elif etype == "battle":
            # Show battle stats in right panel
            battle_result = {
                "location_name": evt.get("city", ""),
                "attacker_name": evt.get("atk_name", ""),
                "attacker_strength": evt.get("atk_size", 0),
                "attacker_losses": evt.get("atk_loss", 0),
                "defender_name": evt.get("def_name", ""),
                "defender_strength": evt.get("def_size", 0),
                "defender_losses": evt.get("def_loss", 0),
                "winner": evt.get("winner_side", 0),
                "message": evt.get("msg", ""),
            }
            ui.draw_battle_result(_ctx, battle_result)
            await asyncio.sleep(2.0)
            ui.clr_rite(_ctx)

            # Apply casualties to replay state
            atk_id = evt.get("atk_id", 0)
            def_id = evt.get("def_id", 0)
            atk_loss = evt.get("atk_loss", 0)
            def_loss = evt.get("def_loss", 0)
            if atk_id:
                armies = _game_state.get("armies", {}) if isinstance(_game_state, dict) else {}
                atk_army = armies.get(str(atk_id)) or armies.get(atk_id)
                if atk_army:
                    old_size = atk_army.get("size", 0) if isinstance(atk_army, dict) else getattr(atk_army, "size", 0)
                    _replay_update_army(atk_id, size=max(1, old_size - atk_loss))
            if def_id:
                armies = _game_state.get("armies", {}) if isinstance(_game_state, dict) else {}
                def_army = armies.get(str(def_id)) or armies.get(def_id)
                if def_army:
                    old_size = def_army.get("size", 0) if isinstance(def_army, dict) else getattr(def_army, "size", 0)
                    _replay_update_army(def_id, size=max(1, old_size - def_loss))

        # ──────── Attacker Withdraw ────────
        elif etype == "withdraw":
            ui.print_message(_ctx, evt.get("msg", "")[:79], 11)
            army_id = evt.get("army_id", 0)
            to_city = evt.get("to", 0)
            _replay_update_army(army_id, location=to_city, move_target=0)
            _map_dirty = True
            _replay_draw_map()
            await asyncio.sleep(0.5)

        # ──────── Defender Retreat ────────
        elif etype == "retreat":
            ui.print_message(_ctx, evt.get("msg", "")[:79], 11)
            army_id = evt.get("army_id", 0)
            to_city = evt.get("to", 0)
            _replay_update_army(army_id, location=to_city, move_target=0)
            _map_dirty = True
            _replay_draw_map()
            await asyncio.sleep(0.5)

        # ──────── Arrive (move into city) ────────
        elif etype == "arrive":
            army_id = evt.get("army_id", 0)
            city_id = evt.get("city", 0)
            _replay_update_army(army_id, location=city_id, move_target=0)
            _map_dirty = True
            _replay_draw_map()

        # ──────── Surrender / Crushed ────────
        elif etype == "surrender":
            ui.print_message(_ctx, evt.get("msg", "")[:79], 12)
            aid = evt.get("army_id", 0)
            if aid:
                # Remove army from map
                _replay_update_army(aid, location=0, size=0)
                _map_dirty = True
                _replay_draw_map()
            await asyncio.sleep(1.0)

        # ──────── City Capture ────────
        elif etype == "capture":
            ui.print_message(_ctx, evt.get("msg", "")[:79], 11)
            city_id = evt.get("city_id", 0)
            side = evt.get("side", 1)
            if city_id:
                _replay_update_city_owner(city_id, side)
                _map_dirty = True
                _replay_draw_map()
                _flash_city(city_id)
            if evt.get("is_capital"):
                city_name = evt.get("city_name", "")
                ui.image2(_ctx, f"{city_name} has fallen!", 4)
                await asyncio.sleep(2.0)
            else:
                await asyncio.sleep(1.0)

        # ──────── Commerce Raid ────────
        elif etype == "raid":
            color = 15 if evt.get("success") else 12
            ui.print_message(_ctx, evt.get("msg", "")[:79], color)
            await asyncio.sleep(1.0)

        # ──────── Fleet Destroyed ────────
        elif etype == "fleet_destroyed":
            ui.print_message(_ctx, evt.get("msg", "")[:79], 15)
            await asyncio.sleep(1.0)

        # ──────── Popup ────────
        elif etype == "popup":
            ui.image2(_ctx, evt.get("msg", ""), evt.get("color", 4))
            await asyncio.sleep(1.5)

        # ──────── Naval ────────
        elif etype == "naval":
            ui.image2(_ctx, evt.get("msg", ""), 4)
            await asyncio.sleep(1.5)

        # ──────── Railroad Depart ────────
        elif etype == "railroad_depart":
            ui.print_message(_ctx, evt.get("msg", "")[:79], 11)
            army_id = evt.get("army_id", 0)
            _replay_update_army(army_id, location=0)
            _map_dirty = True
            _replay_draw_map()
            await asyncio.sleep(0.8)

        # ──────── Railroad Arrive ────────
        elif etype == "railroad_arrive":
            ui.print_message(_ctx, evt.get("msg", "")[:79], 11)
            army_id = evt.get("army_id", 0)
            city_id = evt.get("city", 0)
            _replay_update_army(army_id, location=city_id, move_target=0)
            _map_dirty = True
            _replay_draw_map()
            await asyncio.sleep(1.0)

        # ──────── Unknown ────────
        else:
            msg = evt.get("msg", str(evt))
            ui.print_message(_ctx, msg[:79], 11)
            await asyncio.sleep(0.6)

    # Restore post-state and redraw
    _game_state.update(post_state) if isinstance(_game_state, dict) else None
    _map_dirty = True
    _replay_active = False
    _enter_state(GamePhase.MAIN_MENU)


def _handle_recruit_select(index: int):
    """Recruit at a city — applies immediately to local game state.

    In QBasic, recruitment is instant: cash drops, army size updates,
    the player sees the result right away. We mirror that here by
    optimistically updating _game_state so the topbar and map refresh.
    The order is still queued for the server on turn submit.
    """
    global _map_dirty

    if index < 0 or index >= len(_menu_city_ids) or _menu_city_ids[index] == 0:
        _enter_state(GamePhase.MAIN_MENU)
        return

    city_id = _menu_city_ids[index]
    cities = _game_state.get("cities", {}) if isinstance(
        _game_state, dict) else {}
    armies = _game_state.get("armies", {}) if isinstance(
        _game_state, dict) else {}
    occupied = _game_state.get("occupied", {}) if isinstance(
        _game_state, dict) else {}
    cash = _game_state.get("cash", {}) if isinstance(_game_state, dict) else {}

    city = cities.get(str(city_id)) or cities.get(city_id)
    city_name = _get_val(city, "name", "?") if city else "?"
    city_value = int(_get_val(city, "value", 5)) if city else 5

    my_cash = float(cash.get(str(_player_side), cash.get(_player_side, 0)))
    if my_cash < 100:
        _set_status(
            f"Insufficient funds! Need $100, have ${int(my_cash)}.", 12)
        sound.snd_cancel()
        return

    # Queue the order for the server
    _pending_orders.append({
        "type": "recruit",
        "params": {"city_id": city_id},
    })

    # --- Apply locally so the display updates immediately ---
    # Deduct cash
    new_cash = my_cash - 100
    cash[str(_player_side)] = new_cash
    if _player_side in cash:
        cash[_player_side] = new_cash

    # Check if reinforcing an existing army or creating new
    occ_id = occupied.get(str(city_id), occupied.get(city_id, 0))
    occ_army = armies.get(str(occ_id)) or armies.get(
        occ_id) if occ_id else None

    if occ_army and int(_get_val(occ_army, "size", 0)) > 0:
        # Reinforce existing army
        reinforce_add = 45
        old_size = int(_get_val(occ_army, "size", 0))
        new_size = old_size + reinforce_add
        army_name = _get_val(occ_army, "name", "?")
        if isinstance(occ_army, dict):
            occ_army["size"] = new_size
        else:
            try:
                occ_army.size = new_size
            except Exception:
                pass

        _set_status(
            f"{army_name} reinforced at {city_name}: "
            f"{old_size}00 -> {new_size}00 troops.  Cash: ${int(new_cash)}",
            10,
        )
        sound.snd_recruit()
    else:
        # New army created
        new_size = 3 * city_value + 33
        _set_status(
            f"New army raised at {city_name} ({new_size}00 troops).  "
            f"Cash: ${int(new_cash)}",
            10,
        )
        sound.snd_recruit()

    _flash_city(city_id)
    # Don't set _map_dirty — recruit doesn't change map visuals (army sprites
    # only appear after server processes the order on turn resolution).
    # Go back to main menu but preserve our status message (don't let
    # _setup_main_menu overwrite it).
    _enter_main_menu_keep_status()


def _handle_move_from_select(index: int):
    global _move_source_army

    if index < 0 or index >= len(_menu_army_ids) or _menu_army_ids[index] == 0:
        _enter_state(GamePhase.MAIN_MENU)
        return

    army_id = _menu_army_ids[index]
    armies = _game_state.get("armies", {}) if isinstance(
        _game_state, dict) else {}
    _move_source_army = armies.get(str(army_id)) or armies.get(army_id)
    _enter_state(GamePhase.MOVE_TO)


def _handle_move_to_select(index: int):
    global _move_source_army

    if not _move_source_army or index < 0 or index >= len(_menu_city_ids) or _menu_city_ids[index] == 0:
        _enter_state(GamePhase.MAIN_MENU)
        return

    dest_id = _menu_city_ids[index]
    _pending_orders.append({
        "type": "move",
        "params": {"army_id": _get_val(_move_source_army, "id"), "destination": dest_id},
    })

    cities = _game_state.get("cities", {}) if isinstance(
        _game_state, dict) else {}
    dest = cities.get(str(dest_id)) or cities.get(dest_id)
    army_name = _get_val(_move_source_army, "name", "?")
    dest_name = _get_val(dest, "name", "?") if dest else "?"
    _set_status(f"{army_name} ordered to {dest_name}.", 10)
    sound.snd_move_order()  # SOUND 2200, .5: SOUND 2900, .7
    _flash_city(dest_id)
    _move_source_army = None
    _enter_state(GamePhase.MAIN_MENU)


def _handle_railroad_select(index: int):
    global _move_source_army

    if index < 0 or index >= len(_menu_army_ids) or _menu_army_ids[index] == 0:
        _enter_state(GamePhase.MAIN_MENU)
        return

    army_id = _menu_army_ids[index]
    armies = _game_state.get("armies", {}) if isinstance(
        _game_state, dict) else {}
    _move_source_army = armies.get(str(army_id)) or armies.get(army_id)
    _enter_state(GamePhase.RAILROAD_DEST)


def _handle_railroad_dest_select(index: int):
    global _move_source_army

    if not _move_source_army or index < 0 or index >= len(_menu_city_ids) or _menu_city_ids[index] == 0:
        _enter_state(GamePhase.MAIN_MENU)
        return

    dest_id = _menu_city_ids[index]
    _pending_orders.append({
        "type": "railroad",
        "params": {"army_id": _get_val(_move_source_army, "id"), "destination": dest_id},
    })

    cities = _game_state.get("cities", {}) if isinstance(
        _game_state, dict) else {}
    dest = cities.get(str(dest_id)) or cities.get(dest_id)
    army_name = _get_val(_move_source_army, "name", "?")
    dest_name = _get_val(dest, "name", "?") if dest else "?"
    _set_status(f"{army_name} taking RR to {dest_name}.", 10)
    sound.snd_railroad_depart()  # SOUND 2222, 1
    _flash_city(dest_id)
    _move_source_army = None
    _enter_state(GamePhase.MAIN_MENU)


def _handle_commands_select(index: int):
    if index == 0:    # Cancel
        _enter_state(GamePhase.MAIN_MENU)
    elif index == 1:  # Fortify
        _enter_state(GamePhase.FORTIFY)
    elif index == 2:  # Join Army (Combine)
        _enter_state(GamePhase.CMD_COMBINE)
    elif index == 3:  # Supply
        _enter_state(GamePhase.CMD_SUPPLY)
    elif index == 4:  # Capital
        _enter_state(GamePhase.CMD_CAPITAL)
    elif index == 5:  # Detach
        _enter_state(GamePhase.CMD_DETACH)
    elif index == 6:  # Drill
        _enter_state(GamePhase.CMD_DRILL)
    elif index == 7:  # Relieve
        _enter_state(GamePhase.CMD_RELIEVE)
    else:
        _set_status("Command not yet implemented.", 12)
        _enter_state(GamePhase.MAIN_MENU)


def _handle_fortify_select(index: int):
    if index < 0 or index >= len(_menu_city_ids) or _menu_city_ids[index] == 0:
        _enter_state(GamePhase.MAIN_MENU)
        return

    city_id = _menu_city_ids[index]
    _pending_orders.append({
        "type": "fortify",
        "params": {"city_id": city_id},
    })

    cities = _game_state.get("cities", {}) if isinstance(
        _game_state, dict) else {}
    city = cities.get(str(city_id)) or cities.get(city_id)
    name = _get_val(city, "name", "?") if city else "?"
    _set_status(f"Fortify ordered for {name}.", 10)
    sound.snd_fortify()  # SOUND 3999, .3
    _flash_city(city_id)
    _enter_state(GamePhase.MAIN_MENU)


def _handle_combine_select(index: int):
    if index < 0 or index >= len(_menu_army_ids) or _menu_army_ids[index] == 0:
        _enter_state(GamePhase.MAIN_MENU)
        return

    army_id = _menu_army_ids[index]
    _pending_orders.append({
        "type": "combine",
        "params": {"army_id": army_id},
    })
    _set_status(f"Combine ordered for army {army_id}.", 10)
    sound.snd_combat()  # SOUND 77, .5: SOUND 59, .5 (combine uses same sfx)
    _enter_state(GamePhase.MAIN_MENU)


def _handle_supply_select(index: int):
    if index < 0 or index >= len(_menu_army_ids) or _menu_army_ids[index] == 0:
        _enter_state(GamePhase.MAIN_MENU)
        return

    army_id = _menu_army_ids[index]
    _pending_orders.append({
        "type": "supply",
        "params": {"army_id": army_id},
    })
    _set_status(f"Resupply ordered for army {army_id}.", 10)
    sound.snd_supply()  # SOUND 4500, .5
    _enter_state(GamePhase.MAIN_MENU)


def _handle_capital_select(index: int):
    if index < 0 or index >= len(_menu_city_ids) or _menu_city_ids[index] == 0:
        _enter_state(GamePhase.MAIN_MENU)
        return

    city_id = _menu_city_ids[index]
    _pending_orders.append({
        "type": "capital",
        "params": {"city_id": city_id},
    })
    cities = _game_state.get("cities", {}) if isinstance(
        _game_state, dict) else {}
    city = cities.get(str(city_id)) or cities.get(city_id)
    name = _get_val(city, "name", "?") if city else "?"
    _set_status(f"Capital move to {name} ordered (cost 500).", 10)
    sound.snd_city_event()  # SOUND 4000, .7
    _flash_city(city_id)
    _enter_state(GamePhase.MAIN_MENU)


def _handle_detach_select(index: int):
    if index < 0 or index >= len(_menu_army_ids) or _menu_army_ids[index] == 0:
        _enter_state(GamePhase.MAIN_MENU)
        return

    army_id = _menu_army_ids[index]
    _pending_orders.append({
        "type": "detach",
        "params": {"army_id": army_id},
    })
    _set_status(f"Detach ordered for army {army_id}.", 10)
    sound.snd_detach()  # SOUND 2222, 1
    _enter_state(GamePhase.MAIN_MENU)


def _handle_drill_select(index: int):
    if index < 0 or index >= len(_menu_army_ids) or _menu_army_ids[index] == 0:
        _enter_state(GamePhase.MAIN_MENU)
        return

    army_id = _menu_army_ids[index]
    _pending_orders.append({
        "type": "drill",
        "params": {"army_id": army_id},
    })
    _set_status(f"Drill ordered for army {army_id}.", 10)
    sound.snd_drill()  # SOUND 2222, 1
    _enter_state(GamePhase.MAIN_MENU)


def _handle_relieve_select(index: int):
    if index < 0 or index >= len(_menu_army_ids) or _menu_army_ids[index] == 0:
        _enter_state(GamePhase.MAIN_MENU)
        return

    army_id = _menu_army_ids[index]
    _pending_orders.append({
        "type": "relieve",
        "params": {"army_id": army_id},
    })
    _set_status(f"Relieve ordered for army {army_id}.", 10)
    sound.snd_setting_change()  # SOUND 999, 1
    _enter_state(GamePhase.MAIN_MENU)


# --------------------------------------------------------------------------- #
#  Reports menu
# --------------------------------------------------------------------------- #
_report_menu_keys = []


def _build_reports_menu():
    global _menu_title, _menu_options, _menu_tlx, _menu_tly, _menu_colour, _menu_hilite
    global _report_menu_keys
    _menu_title = "Reports"
    _menu_options = reports.get_report_options()
    _report_menu_keys = list(range(len(_menu_options)))
    _menu_tlx = 67
    _menu_tly = 13
    _menu_colour = 1
    _menu_hilite = 9
    _set_status("Select a report. ESC to cancel.", 7)
    _enter_state.__wrapped_render = True  # flag: don't double-render
    global _current_state, _menu_selected
    _current_state = "reports_menu"
    _menu_selected = 0
    render()


def _handle_reports_menu_select(index: int):
    global _report_lines
    if index < 0 or index >= len(_report_menu_keys):
        _enter_state(GamePhase.MAIN_MENU)
        return
    _report_lines = reports.generate_report(_game_state, index, _player_side)
    _enter_state(GamePhase.REPORT)


# --------------------------------------------------------------------------- #
#  Utility menu
# --------------------------------------------------------------------------- #
def _build_utility_menu():
    global _menu_title, _menu_options, _menu_tlx, _menu_tly, _menu_colour, _menu_hilite
    if _game_state:
        utility.load_from_game_state(_game_state)
    _menu_title = "Utility"
    _menu_options = utility.get_utility_options()
    _menu_tlx = 67
    _menu_tly = 13
    _menu_colour = 3
    _menu_hilite = 11
    _set_status("Toggle settings. ESC to return.", 7)


def _handle_utility_select(index: int):
    msg = utility.toggle_setting(index)
    if msg:
        _set_status(msg, 10)
    sound.snd_setting_change()  # SOUND 999, 1
    global _menu_options
    _menu_options = utility.get_utility_options()
    render()


# --------------------------------------------------------------------------- #
#  Save/Load menu
# --------------------------------------------------------------------------- #
_save_load_phase = "menu"  # "menu", "save_slot", "load_slot"


def _build_save_load_menu():
    global _menu_title, _menu_options, _menu_tlx, _menu_tly, _menu_colour, _menu_hilite
    global _save_load_phase
    _save_load_phase = "menu"
    _menu_title = "Files"
    _menu_options = save_load.get_save_load_options()
    _menu_tlx = 67
    _menu_tly = 13
    _menu_colour = 6
    _menu_hilite = 14
    _set_status("Select save/load option. ESC to return.", 7)


def _handle_save_load_select(index: int):
    global _save_load_phase, _menu_title, _menu_options
    if _save_load_phase == "menu":
        if index == 0:  # Save Game
            _save_load_phase = "save_slot"
            _menu_title = "Save Slot"
            _menu_options = save_load.get_slot_options()
            _set_status("Select slot to save (1-9).", 7)
            render()
        elif index == 1:  # Load Game
            _save_load_phase = "load_slot"
            _menu_title = "Load Slot"
            _menu_options = save_load.get_slot_options()
            _set_status("Select slot to load (1-9).", 7)
            render()
        else:
            _enter_state(GamePhase.MAIN_MENU)
    elif _save_load_phase == "save_slot":
        slot = index + 1
        asyncio.ensure_future(_do_save(slot))
    elif _save_load_phase == "load_slot":
        slot = index + 1
        asyncio.ensure_future(_do_load(slot))


async def _do_save(slot: int):
    msg = await save_load.save_game(_ctx, slot)
    _set_status(msg, 10)
    _enter_state(GamePhase.MAIN_MENU)


async def _do_load(slot: int):
    msg = await save_load.load_game(_ctx, slot)
    _set_status(msg, 10)
    await _load_game_state()


def _handle_end_turn_select(index: int):
    if index == 0:
        # Yes -- submit orders
        asyncio.ensure_future(_submit_turn())
    else:
        _enter_state(GamePhase.MAIN_MENU)


# --------------------------------------------------------------------------- #
#  Order submission
# --------------------------------------------------------------------------- #
async def _submit_turn():
    global _pending_orders, _move_source_army, _map_dirty

    _set_status("Submitting orders...", 14)
    render()

    try:
        from pyodide.ffi import to_js  # type: ignore
        from js import window  # type: ignore

        orders_to_send = [dict(o) for o in _pending_orders]
        await api_client.submit_orders(orders_to_send)

        _pending_orders = []
        _move_source_army = None
        _map_dirty = True  # invalidate map cache
        _set_status("Turn submitted. Waiting for resolution...", 14)
        _enter_state(GamePhase.WAITING)

        # Refresh state after delay
        await asyncio.sleep(1.5)
        await _load_game_state()
    except Exception as e:
        _set_status(f"Error: {e}", 12)
        _enter_state(GamePhase.MAIN_MENU)


# --------------------------------------------------------------------------- #
#  Game state management
# --------------------------------------------------------------------------- #
async def _load_game_state():
    global _game_state, _player_side, _map_dirty, _replay_task

    try:
        gs = await api_client.get_game_state()

        # Check for event_log — trigger replay before loading final state
        event_log = _get_val(gs, "event_log", None)
        if (event_log and _current_state in (GamePhase.LOADING, GamePhase.WAITING)
                and not _replay_active):
            # Save final state, then replay will restore it when done
            _game_state = gs
            _map_dirty = True
            _player_side = _get_val(
                gs, "player_side", api_client.get_player_side())
            post_state = dict(gs) if isinstance(gs, dict) else gs
            _replay_task = asyncio.ensure_future(
                show_event_replay(event_log, post_state))
            return

        _game_state = gs
        _map_dirty = True  # invalidate map cache on state change
        _player_side = _get_val(
            gs, "player_side", api_client.get_player_side())

        phase = _get_val(gs, "phase", "orders")
        current_turn = _get_val(gs, "current_turn", 0)

        if current_turn != _player_side and current_turn > 0:
            _enter_state(GamePhase.WAITING)
        elif _current_state in (GamePhase.LOADING, GamePhase.WAITING):
            _enter_state(GamePhase.MAIN_MENU)
        else:
            render()
    except Exception as e:
        _set_status(f"Error: {e}", 12)
        render()


# --------------------------------------------------------------------------- #
#  Keyboard input handler
# --------------------------------------------------------------------------- #
def on_key(key: str, event):
    """Called by input_handler for each keydown event."""
    global _menu_selected, _battle_result, _report_lines

    # Waiting state: ignore most keys
    if _current_state == GamePhase.WAITING:
        return

    # Event replay: key presses are consumed (replay advances on its own)
    if _current_state == GamePhase.EVENT_REPLAY:
        event.preventDefault()
        return

    # Title screen: any key proceeds to loading
    if _current_state == GamePhase.TITLE_SCREEN:
        event.preventDefault()
        sound.stop_all()
        _enter_state(GamePhase.LOADING)
        asyncio.ensure_future(_load_game_state())
        return

    # Victory screen: any key returns to report
    if _current_state == GamePhase.VICTORY:
        event.preventDefault()
        sound.stop_all()
        _enter_state(GamePhase.REPORT)
        return

    # Hot-seat blank: any key loads state and proceeds
    if _current_state == GamePhase.HOT_SEAT_BLANK:
        event.preventDefault()
        asyncio.ensure_future(_load_game_state())
        return

    # Battle display: any key returns to main
    if _current_state == GamePhase.BATTLE_DISPLAY:
        event.preventDefault()
        _battle_result = None
        _enter_state(GamePhase.MAIN_MENU)
        return

    # Report: any key returns to main
    if _current_state == GamePhase.REPORT:
        event.preventDefault()
        _report_lines = None
        _enter_state(GamePhase.MAIN_MENU)
        return

    # Menu navigation
    if _menu_options:
        if key == "ArrowUp":
            event.preventDefault()
            _menu_selected = (_menu_selected - 1) % len(_menu_options)
            render()
            return

        if key == "ArrowDown":
            event.preventDefault()
            _menu_selected = (_menu_selected + 1) % len(_menu_options)
            render()
            return

        if key in ("PageUp", "Home"):
            event.preventDefault()
            _menu_selected = 0
            render()
            return

        if key in ("PageDown", "End"):
            event.preventDefault()
            _menu_selected = len(_menu_options) - 1
            render()
            return

        if key == "Enter":
            event.preventDefault()
            sound.snd_menu_confirm()
            _on_menu_select(_menu_selected)
            return

        if key == "Escape":
            event.preventDefault()
            if _current_state == GamePhase.UTILITY:
                _enter_state(GamePhase.MAIN_MENU)
            elif _current_state == GamePhase.SAVE_LOAD:
                _enter_state(GamePhase.MAIN_MENU)
            elif _current_state == "reports_menu":
                _enter_state(GamePhase.MAIN_MENU)
            elif _current_state != GamePhase.MAIN_MENU:
                _enter_state(GamePhase.MAIN_MENU)
            return

        # Letter key: jump to first matching option
        if len(key) == 1 and key.isalpha():
            upper_key = key.upper()
            for i, opt in enumerate(_menu_options):
                if opt and opt[0].upper() == upper_key:
                    _menu_selected = i
                    _on_menu_select(i)
                    return


def on_f7():
    """F7 shortcut: end turn."""
    _enter_state(GamePhase.END_TURN_CONFIRM)


def on_click(mx: int, my: int):
    """Called by input_handler for mouse clicks on the canvas."""
    # Future: city/army click selection
    pass


# --------------------------------------------------------------------------- #
#  WebSocket event handlers
# --------------------------------------------------------------------------- #
def _on_turn_notification(msg):
    _set_status("Opponent finished. Loading new state...", 10)
    # In 2-player hot-seat mode, show blank screen between turns
    player_count = _get_val(_game_state, "player_count",
                            1) if _game_state else 1
    if player_count == 2:
        _enter_state(GamePhase.HOT_SEAT_BLANK)
    else:
        asyncio.ensure_future(_load_game_state())


def _on_battle_result(msg):
    global _battle_result, _map_dirty
    _battle_result = msg
    _map_dirty = True  # invalidate map cache
    _enter_state(GamePhase.BATTLE_DISPLAY)

    # Play contextual sounds
    try:
        event_type = _get_val(msg, "type", "battle")
        if event_type == "city_capture":
            winner = _get_val(msg, "winner", 0)
            if winner == 1:
                asyncio.ensure_future(sound.play_union_capture())
            else:
                asyncio.ensure_future(sound.play_rebel_capture())
        else:
            asyncio.ensure_future(sound.play_surrender())
    except Exception:
        pass
    asyncio.ensure_future(_delayed_load())


async def _delayed_load():
    await asyncio.sleep(0.5)
    await _load_game_state()


def _on_game_over(msg):
    global _report_lines
    winner = _get_val(msg, "winner", 0)
    winner_name = "Union" if winner == 1 else "Confederate" if winner == 2 else "Unknown"
    _set_status(f"GAME OVER! Winner: {winner_name}", 14)

    # Prepare report lines for after victory screen dismissal
    _report_lines = [
        {"text": "GAME OVER", "color": 14},
        {"text": "", "color": 7},
        {"text": f"{winner_name} wins!", "color": 9 if winner == 1 else 7},
        {"text": str(_get_val(msg, "message", "")), "color": 7},
    ]

    # Show victory screen with music (VICTORY state, any key → REPORT)
    _enter_state(GamePhase.VICTORY)
    if _ctx:
        if winner == 1:
            asyncio.ensure_future(victory_screen.show_capitol_screen(_ctx))
        elif winner == 2:
            asyncio.ensure_future(victory_screen.show_rebel_mansion(_ctx))


def _on_ws_error(msg):
    detail = _get_val(msg, "detail", "Unknown")
    _set_status(f"Connection error: {detail}", 12)
    render()


def _on_ws_connected(msg):
    _set_status("Connected to game server.", 10)
    render()


def _on_ws_disconnected(msg):
    _set_status("Disconnected - reconnecting...", 12)
    render()


# --------------------------------------------------------------------------- #
#  Polling fallback
# --------------------------------------------------------------------------- #
def _start_polling():
    global _poll_timer
    if _poll_timer is not None:
        return

    def poll_tick():
        if not ws_client.connected():
            asyncio.ensure_future(_load_game_state())

    _poll_timer = set_interval(poll_tick, POLL_INTERVAL)


def _stop_polling():
    global _poll_timer
    if _poll_timer is not None:
        clear_interval(_poll_timer)
        _poll_timer = None


# --------------------------------------------------------------------------- #
#  Bootstrap
# --------------------------------------------------------------------------- #
async def start():
    """Main entry point -- called from main.py."""
    global _game_code, _player_side

    # Verify credentials
    _game_code = api_client.get_game_code()
    token = api_client.get_token()
    _player_side = api_client.get_player_side()

    if not _game_code or not token:
        from js import window  # type: ignore
        log("[game] No session -- redirecting to lobby")

        def _redirect():
            window.location.assign("index.html")

        set_timeout(_redirect, 1500)
        return

    # Initialize canvas
    _init_canvas()
    if _ctx is None:
        return

    # Loading screen
    _ctx.fillStyle = "#000000"
    _ctx.fillRect(0, 0, 640, 480)
    font.print_text(_ctx, 15, 25, "Loading game...", 14)

    # Load sprites
    await sprites.load_sprites("assets/sprites/")
    font.print_text(_ctx, 16, 25, "Sprites loaded.", 10)

    # Bind input (must be before title screen so keys work)
    import input_handler
    input_handler.init(_canvas, _get_game_module())

    # Connect WebSocket
    ws_client.on("turn_notification", _on_turn_notification)
    ws_client.on("battle_result", _on_battle_result)
    ws_client.on("game_over", _on_game_over)
    ws_client.on("error", _on_ws_error)
    ws_client.on("connected", _on_ws_connected)
    ws_client.on("disconnected", _on_ws_disconnected)
    ws_client.connect(_game_code, token)

    # Start polling
    _start_polling()

    # Show title screen (key press → LOADING → _load_game_state)
    _enter_state(GamePhase.TITLE_SCREEN)
    await title_screen.show_title_screen(_ctx, _player_side)


def _get_game_module():
    """Return a reference to this module for the input handler."""
    import game
    return game
