"""constants.py -- VGA palette, screen dimensions, months, Side enum.

Direct port of QBasic DIM SHARED arrays and the server-side constants.
All rendering code references these values.
"""

from enum import IntEnum

# --------------------------------------------------------------------------- #
#  VGA 16-color palette (hex strings for Canvas fillStyle/strokeStyle)
# --------------------------------------------------------------------------- #
VGA = [
    "#000000",  # 0  Black
    "#0000AA",  # 1  Blue
    "#00AA00",  # 2  Green
    "#00AAAA",  # 3  Cyan
    "#AA0000",  # 4  Red
    "#AA00AA",  # 5  Magenta
    "#AA5500",  # 6  Brown
    "#AAAAAA",  # 7  Light Gray
    "#555555",  # 8  Dark Gray
    "#5555FF",  # 9  Light Blue
    "#55FF55",  # 10 Light Green
    "#55FFFF",  # 11 Light Cyan
    "#FF5555",  # 12 Light Red
    "#FF55FF",  # 13 Light Magenta
    "#FFFF55",  # 14 Yellow
    "#FFFFFF",  # 15 White
]

# VGA palette as RGB tuples for pixel-level matching
VGA_RGB = [
    (0x00, 0x00, 0x00), (0x00, 0x00, 0xAA), (0x00, 0xAA, 0x00), (0x00, 0xAA, 0xAA),
    (0xAA, 0x00, 0x00), (0xAA, 0x00, 0xAA), (0xAA, 0x55, 0x00), (0xAA, 0xAA, 0xAA),
    (0x55, 0x55, 0x55), (0x55, 0x55, 0xFF), (0x55, 0xFF, 0x55), (0x55, 0xFF, 0xFF),
    (0xFF, 0x55, 0x55), (0xFF, 0x55, 0xFF), (0xFF, 0xFF, 0x55), (0xFF, 0xFF, 0xFF),
]

# --------------------------------------------------------------------------- #
#  Screen dimensions -- QBasic SCREEN 12 = 640x480, 16 colors
# --------------------------------------------------------------------------- #
SCREEN_WIDTH = 640
SCREEN_HEIGHT = 480
CHAR_WIDTH = 8    # VGA text mode character cell width
CHAR_HEIGHT = 16  # VGA text mode character cell height
TEXT_COLS = 80    # 640 / 8
TEXT_ROWS = 30    # 480 / 16

# --------------------------------------------------------------------------- #
#  Sides
# --------------------------------------------------------------------------- #


class Side(IntEnum):
    NEUTRAL = 0
    UNION = 1
    CONFEDERATE = 2


SIDE_NAMES = {
    Side.NEUTRAL: "NEUTRAL",
    Side.UNION: "Union",
    Side.CONFEDERATE: "Rebel",
}

# --------------------------------------------------------------------------- #
#  Army index ranges: Union 1-20, Confederate 21-40
# --------------------------------------------------------------------------- #
UNION_ARMY_START = 1
UNION_ARMY_END = 20
REBEL_ARMY_START = 21
REBEL_ARMY_END = 40
MAX_ARMIES = 40
MAX_CITIES = 40
MAX_ADJACENCY = 6

# --------------------------------------------------------------------------- #
#  Months
# --------------------------------------------------------------------------- #
MONTHS = [
    "", "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]

# --------------------------------------------------------------------------- #
#  Mountain sprite positions from SUB usa (PUT coordinates)
# --------------------------------------------------------------------------- #
MTN_POSITIONS = [
    (380, 30), (270, 200), (310, 160), (350, 120),
    (200, 185), (250, 130), (320, 80), (30, 150),
]

# --------------------------------------------------------------------------- #
#  City color indices by owner
# --------------------------------------------------------------------------- #
CITY_COLOR_UNION = 9      # Light Blue
CITY_COLOR_REBEL = 7      # Light Gray
CITY_COLOR_NEUTRAL = 12   # Light Red

# --------------------------------------------------------------------------- #
#  Menu option lists -- matching QBasic menu0
# --------------------------------------------------------------------------- #
MAIN_MENU = [
    "Troops", "Moves", "Ships", "Railroad", "END TURN",
    "Inform", "COMMANDS", "UTILITY", "Files",
]

COMMANDS_MENU = [
    "Cancel", "Fortify", "Join Army", "Supply",
    "Capital", "Detach", "Drill", "Relieve",
]

END_TURN_MENU = ["Yes", "NOT YET"]

# --------------------------------------------------------------------------- #
#  Game states
# --------------------------------------------------------------------------- #


class GamePhase:
    TITLE_SCREEN = "title_screen"
    MAIN_MENU = "main_menu"
    RECRUIT = "recruit"
    MOVE_FROM = "move_from"
    MOVE_TO = "move_to"
    RAILROAD = "railroad"
    RAILROAD_DEST = "railroad_dest"
    NAVAL = "naval"
    NAVAL_TARGET = "naval_target"
    COMMANDS = "commands"
    CMD_CANCEL = "cmd_cancel"
    CMD_FORTIFY = "cmd_fortify"
    CMD_COMBINE = "cmd_combine"
    CMD_SUPPLY = "cmd_supply"
    CMD_CAPITAL = "cmd_capital"
    CMD_DETACH = "cmd_detach"
    CMD_DRILL = "cmd_drill"
    CMD_RELIEVE = "cmd_relieve"
    END_TURN_CONFIRM = "end_turn_confirm"
    WAITING = "waiting"
    BATTLE_DISPLAY = "battle_display"
    REPORT = "report"
    UTILITY = "utility"
    SAVE_LOAD = "save_load"
    HOT_SEAT_BLANK = "hot_seat_blank"
    VICTORY = "victory"
    LOADING = "loading"
    FORTIFY = "fortify"
    EVENT_REPLAY = "event_replay"


# --------------------------------------------------------------------------- #
#  Special fleet positions for map rendering
# --------------------------------------------------------------------------- #
FLEET_SPECIAL_POS = {
    30: (515, 268),
    28: (517, 172),
    17: (380, 425),
    99: (495, 310),
}
