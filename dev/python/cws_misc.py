"""cws_misc.py - Miscellaneous screens and utility subs.
Direct port of cws_misc.bm (QB64) to Python.

Original file: cws_misc.bm (146 lines)
Contains:
    SUB newcity(index)  ->  newcity(g, index) -> int   [city picker UI]
    SUB capitol         ->  capitol(g)                  [Union victory screen]
    SUB maxx            ->  maxx(g)                     [Hall of Fame]
    SUB void(a, y)      ->  void(g, a) -> int           [adjacent strength calc]

Dependencies:
    cws_ui:   menu(g, switch), clrrite(g), flags(g, who, w, a)
    cws_util: tick(g, seconds)
"""

import os
import pygame
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cws_globals import GameState

_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..")


def _data_path(filename: str) -> str:
    path = os.path.join(_DATA_DIR, filename)
    if os.path.exists(path):
        return path
    for f in os.listdir(_DATA_DIR):
        if f.upper() == filename.upper():
            return os.path.join(_DATA_DIR, f)
    return path


# ─────────────────────────────────────────────────────────────────────────────
# SUB newcity(index)  -- lines 1-41
#
# City picker UI. Lets the player cycle through their owned cities.
# Uses menu(3) = letter-input mode:
#   choose = 1  -> previous city (left/up)
#   choose = 2  -> accept current selection (enter)
#   choose = 3  -> next city (right/down)
#   choose = -27 -> ESC (cancel)
#   choose = -ASC(letter) -> jump to city starting with that letter
#
# Original GOTO labels:
#   morecap -> top of selection loop
#   spin2   -> inner loop scanning for city owned by side
#   minus1  -> scan backward for owned city
#   plus1   -> scan forward for owned city
#   fnew    -> exit (accept selection)
# ─────────────────────────────────────────────────────────────────────────────

def newcity(g: 'GameState', index: int) -> int:
    """City picker UI. Returns selected city index, or 0 if cancelled.

    Original: SUB newcity(index) -- lines 1-41
    """
    from cws_ui import menu, clrrite

    g.mtx[1] = "  "                                                 # L2
    g.mtx[3] = "  "                                                 # L3
    g.size = 3                                                       # L4
    a = g.city[index]                                                # L4

    # ── morecap loop ──────────────────────────────────────────────
    while True:                                                      # L5: morecap:
        g.tlx = 68                                                   # L6
        g.tly = 15
        g.colour = 3
        g.choose = 23
        g.mtx[2] = g.city[index]                                    # L7
        menu(g, 3)                                                   # L8
        clrrite(g)                                                   # L8

        # SELECT CASE choose                                         # L9
        if g.choose == -27:                                          # L10: CASE IS = -27
            index = 0                                                # L11
            return index                                             # EXIT SUB

        elif g.choose < 1:                                           # L12: CASE IS < 1
            # Letter typed: find city starting with that letter
            a = chr(abs(g.choose))                                   # L13
            x = 0                                                    # L14
            found_letter = False
            for k in range(1, 41):                                   # L15
                if g.city[k] and g.city[k][0:1].upper() == a.upper():  # L16
                    y = index                                        # L17
                    index = k
                    # spin2: scan forward for a city owned by side   # L18
                    while True:                                      # L18: spin2:
                        if g.cityp[index] == g.side:                 # L19
                            found_letter = True
                            break  # goto morecap
                        index += 1                                   # L20
                        if index > 40:                               # L21
                            index = 1
                        x += 1                                       # L22
                        if x >= 39:
                            index = y                                # L23
                            found_letter = True
                            break  # goto morecap
                    if found_letter:
                        break  # exit FOR k, goto morecap
            # L26: GOTO morecap (implicit: continue while loop)
            continue

        elif g.choose == 1:                                          # L27: CASE 1
            # minus1: scan backward for previous owned city
            while True:                                              # L28: minus1:
                index -= 1                                           # L29
                if index < 1:
                    index = 40
                if g.cityp[index] == g.side:                         # L30
                    break  # goto morecap
            continue  # goto morecap

        elif g.choose == 2:                                          # L31: CASE 2
            return index                                             # L32: GOTO fnew (exit)

        elif g.choose == 3:                                          # L33: CASE 3
            # plus1: scan forward for next owned city
            while True:                                              # L34: plus1:
                index += 1                                           # L35
                if index > 40:
                    index = 1
                if g.cityp[index] == g.side:                         # L36
                    break  # goto morecap
            continue  # goto morecap

        else:                                                        # L37: CASE ELSE
            index = 0                                                # L38
            return index

    return index  # fnew: END SUB                                    # L40-41


# ─────────────────────────────────────────────────────────────────────────────
# SUB capitol  -- lines 42-88
#
# Union victory screen. Draws the U.S. Capitol building, displays the
# Gettysburg Address excerpt, and plays "Battle Hymn of the Republic".
#
# The building is drawn with DRAW turtle commands (pixel art).
# Exact port of all DRAW commands for columns, windows, and Statue of Freedom.
# ─────────────────────────────────────────────────────────────────────────────

def capitol(g: 'GameState') -> None:
    """Union victory screen with Capitol building and Lincoln quote.

    Original: SUB capitol -- lines 42-88
    """
    from cws_ui import flags

    s = g.screen
    s.cls()                                                          # L43-44

    # Three colored bands (flag colors)
    s.line(1, 1, 639, 150, 4, "BF")                                 # L45: red top
    s.line(1, 150, 639, 300, 15, "BF")                              # L46: white middle
    s.line(1, 300, 639, 450, 1, "BF")                               # L47: blue bottom

    # Capitol building -- exact port of L48-76
    x = 0                                                            # L48
    s.line(150, 190, 500, 254, 7, "B")                              # L49
    s.line(270, 190, 370, 254, 7, "B")                              # L50
    s.line(270, 185, 370, 175, 7, "B")                              # L51
    s.line(280, 173, 360, 168, 7, "B")                              # L52
    s.line(270, 235, 370, 254, 7, "B")                              # L53
    s.circle(320, 150, 74, 7, start=0.2, end=2.95, aspect=2.1)      # L54
    s.line(285, 138, 355, 168, 7, "B")                              # L55

    # lwing: L56-64 — three wing sections
    for x in range(3):                                               # L64: x=0,1,2
        s.pset(180 + 120 * x, 200, 0)                               # L57
        s.draw("C7ER1E1R1E1R1E1R1E1R1E1R1E1R1E1R1E1R1E1R1E1R1F1R1F1R1F1")  # L59
        s.draw("R1F1R1F1R1F1R1F1R1F1R1F1R1F1R1F1R1F1L47D4R48U3D51L4U17L41D17L3U47")  # L60
        for i in range(1, 8):                                        # L61
            s.draw("BR6R2D25L2U25")
        s.draw("BD33R2")                                             # L62
        for i in range(1, 6):                                        # L63
            s.draw("L40BR40D3")

    # Center section columns L65-68
    s.pset(270, 190, 0)                                              # L65
    for i in range(1, 4):                                            # L66
        s.draw("C7BR6R2D45L2U45")
    s.pset(344, 190, 0)                                              # L67
    for i in range(1, 4):                                            # L68
        s.draw("C7BR6R2D45L2U45")

    # Dome windows L69-72
    s.pset(283, 140, 0)                                              # L69
    for i in range(1, 12):                                           # L70
        s.draw("C7BR6R2D25L2U25")
    s.pset(283, 120, 0)                                              # L71
    for i in range(1, 12):                                           # L72
        s.draw("C7BR6R2D15L2U15")

    # Spire L73-76
    s.line(315, 55, 325, 77, 7, "B")                                # L73
    s.line(318, 57, 322, 75, 7, "B")                                # L74
    s.pset(315, 53, 0)                                               # L75
    s.draw("S3C7R13U6L13D5BU5C7U2E1U2E2U3H2U3H1E3U2H1U2E2U2E2F2D2F4D3R2E2F1G4L1D7F1D2F1D1G2")  # L76

    # Yellow text area                                               # L77
    s.line(140, 270, 510, 430, 14, "BF")

    # Lincoln quote interleaved with Battle Hymn                      # L78-87
    # Music is interruptible so any key press skips remaining music.
    s.color(15)
    _skip = False
    if g.noise == 2:                                                  # L79
        from cws_sound import qb_play_interruptible
        _skip = qb_play_interruptible("T130MFMSO2f16f8.f16f8.e-16d8.f16b-8.o3c16d8.d16d8.c16o2b-4")
    s.locate(20, 20)                                                 # L80
    s.print_text('"... and that the government of the people,')
    if g.noise == 2 and not _skip:                                    # L81
        _skip = qb_play_interruptible("o2b-8.a16g8.g16g8.a16b-8.a16b-8.g16f8.g16f8.d16f4")
    s.locate(21, 20)                                                 # L82
    s.print_text("by the people, for the people,")
    if g.noise == 2 and not _skip:                                    # L83
        _skip = qb_play_interruptible("f8.f16f8.f16f8.e-16d8.f16b-8.o3c16d8.d16d8.c16o2b-4b-4MNo3c4c4o2b-4a4b-2")
    s.locate(22, 20)                                                 # L84
    s.print_text('shall not perish from the earth."')
    s.locate(25, 40)                                                 # L85
    s.print_text("- Abraham Lincoln")

    # Flags along the bottom                                         # L86
    for i in range(-565, 51, 50):
        flags(g, 1, i, 0)

    if g.noise == 2 and not _skip:                                    # L87
        _skip = qb_play_interruptible("P2f4..e-16d8.f16b-8.o3c16d2o2b-2g4..a16b-8.a16b-8.g16f2d2")
    if g.noise == 2 and not _skip:
        qb_play_interruptible("f4..e-16d8.f16b-8.o3c16d2o2b-4b-4o3c4c4o2b-4a4b-2..")
    s.update()


# ─────────────────────────────────────────────────────────────────────────────
# SUB maxx  -- lines 89-133
#
# Hall of Fame screen. Reads/writes hiscore.cws, checks if the current
# victory scores qualify for the leaderboard, gets player name input.
#
# Original uses SCREEN 0 (text mode). In pygame we stay in SCREEN 12
# but just use text rendering on a cleared screen.
#
# GOTO labels:
#   oldskor  -> skip insertion (score not high enough)
#   foun     -> done checking this side
#   who4     -> re-prompt for name if empty
#   automate -> skip name input for computer player
# ─────────────────────────────────────────────────────────────────────────────

def maxx(g: 'GameState') -> None:
    """Hall of Fame: read scores, check new entries, save, set pcode=1.

    Original: SUB maxx -- lines 89-133
    """
    s = g.screen

    # L90: "press a key" then wait
    s.color(14)
    s.locate(28, 1)
    s.print_text("press a key")
    s.update()
    _wait_key()

    # L91: SCREEN 0: COLOR 14, 5: CLS: COLOR 11, 0
    # In pygame we just clear and draw on the same surface
    s.cls()
    s.color(11)

    # L93-95: Draw border box
    s.locate(2, 7)
    s.print_text("|" * 57)                                           # L93
    s.locate(9, 7)
    s.print_text("|" * 57)                                           # L94
    for i in range(1, 7):                                            # L95
        s.locate(2 + i, 7)
        s.print_text("|" + " " * 55 + "|")

    # L97-103: Read high scores from file
    # Temporarily borrow city$ and matrix for score storage
    # (original reuses these shared arrays)
    hiscore_path = _data_path("hiscore.cws")
    scores_name = [""] * 11   # indices 1..10 (5 per side)
    scores_val = [[0] * 6 for _ in range(3)]  # scores_val[side][1..5]

    try:
        with open(hiscore_path, "r") as f:
            for side_s in range(1, 3):                               # L98
                s.color(14)
                s.locate(3, 30 * (side_s - 1) + 10)                 # L99
                s.print_text(f"{g.force[side_s]} HALL of FAME")
                s.color(15)
                for i in range(1, 6):                                # L100
                    line = f.readline().strip()
                    if line:
                        import csv
                        parts = list(csv.reader([line]))[0]
                        name = parts[0].strip() if len(parts) > 0 else ""
                        val = int(parts[1].strip()) if len(parts) > 1 else 0
                    else:
                        name = ""
                        val = 0
                    scores_name[5 * (side_s - 1) + i] = name        # L101
                    scores_val[side_s][i] = val
                    s.locate(3 + i, 30 * (side_s - 1) + 8)          # L102
                    s.print_text(f"{i}  {name:<20s} {val}")
    except FileNotFoundError:
        # No high score file yet -- fill with defaults
        for side_s in range(1, 3):
            s.color(14)
            s.locate(3, 30 * (side_s - 1) + 10)
            s.print_text(f"{g.force[side_s]} HALL of FAME")
            for i in range(1, 6):
                scores_name[5 * (side_s - 1) + i] = ""
                scores_val[side_s][i] = 0

    s.update()

    # L105-125: Check if current scores qualify for hall of fame
    for side_s in range(1, 3):                                       # L105
        inserted = False
        for i in range(1, 6):                                        # L105
            if g.victory[side_s] < scores_val[side_s][i]:            # L106: oldskor
                continue

            # New high score! Shift entries down                     # L107-110
            for j in range(5, i, -1):
                scores_val[side_s][j] = scores_val[side_s][j - 1]
                scores_name[5 * (side_s - 1) + j] = scores_name[5 * (side_s - 1) + j - 1]

            # Display congratulations                                # L112-115
            if side_s == 2:
                s.color(4)
            else:
                s.color(15)
            for k in range(12, 15):                                  # L113
                s.locate(k, 1)
                s.print_text(" " * 80)
            s.locate(12, 1)                                          # L114
            s.print_text(f"Congratulations ! Score of {g.victory[side_s]}")
            s.locate(13, 1)                                          # L115
            s.print_text(
                f"New Entry into {g.force[side_s]} HALL of FAME in place {i}"
            )

            # Get player name                                        # L116-119
            if g.player == 1 and side_s != g.side:                   # L116
                a = "COMPUTER"
                s.locate(14, 1)
                s.print_text(f"{a} was {g.force[side_s]} commander")
            else:
                # Get name from player                               # L117-118
                s.locate(14, 1)
                s.print_text(
                    f"What is name of {g.force[side_s]} commander? "
                )
                s.update()
                a = _input_text(g)
                if a == "":
                    a = "Anonymous"

            # Insert new entry                                       # L120-121
            scores_name[5 * (side_s - 1) + i] = a
            scores_val[side_s][i] = g.victory[side_s]
            inserted = True
            break  # goto foun                                       # L121

        # foun: next side_s                                          # L124-125

    # L127-132: Save high scores
    try:
        with open(hiscore_path, "w") as f:
            for side_s in range(1, 3):                               # L128
                for i in range(1, 6):                                # L129
                    name = scores_name[5 * (side_s - 1) + i]
                    val = scores_val[side_s][i]
                    f.write(f'"{name}",{val}\n')                     # L130
    except IOError:
        pass  # silently fail if can't write

    s.locate(20, 30)                                                 # L132
    s.print_text("Game Over")
    s.update()
    _wait_key()
    g.pcode = 1                                                      # L132


def _wait_key() -> None:
    """Block until any key is pressed (replaces DO WHILE INKEY$="": LOOP)."""
    from cws_screen_pygame import flip
    flip()
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                raise SystemExit
            if event.type == pygame.VIDEORESIZE:
                flip()
            if event.type == pygame.KEYDOWN:
                return
        pygame.time.wait(16)


def _input_text(g: 'GameState') -> str:
    """Simple text input. Replaces QB64's INPUT statement.

    Waits for the player to type a name and press Enter.
    Backspace to delete. ESC to cancel (returns empty).
    """
    text = ""
    s = g.screen
    col = 50  # cursor position after the prompt
    row = 14

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                raise SystemExit
            if event.type == pygame.VIDEORESIZE:
                s.update()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    return text
                elif event.key == pygame.K_ESCAPE:
                    return ""
                elif event.key == pygame.K_BACKSPACE:
                    if text:
                        text = text[:-1]
                        s.locate(row, col)
                        s.print_text(text + "  ")
                        s.update()
                elif event.unicode and len(event.unicode) == 1:
                    if len(text) < 20:
                        text += event.unicode
                        s.locate(row, col)
                        s.print_text(text + "_")
                        s.update()
        pygame.time.wait(16)


# ─────────────────────────────────────────────────────────────────────────────
# SUB void(a, y)  -- lines 134-145
#
# Calculate total friendly army strength in the vicinity of location `a`.
# Checks all neighbors of `a` (first ring) at full weight, and their
# neighbors (second ring) at 10% weight. Only counts armies belonging
# to the current player's side.
#
# This is a key AI evaluation function used by smarts() and evaluate().
# ─────────────────────────────────────────────────────────────────────────────

def void(g: 'GameState', a: int) -> int:
    """Calculate friendly strength adjacent to location `a`.

    Original: SUB void(a, y) -- lines 134-145

    Returns y: weighted sum of friendly army sizes near `a`.
    First-ring neighbors: full armysize.
    Second-ring neighbors: 10% of armysize (DEFINT truncation).
    """
    y = 0                                                            # L135
    for j in range(1, 7):                                            # L136
        x = g.matrix[a][j]                                          # L137
        if x == 0:
            break  # goto tally5 (exit outer loop)                   # L137

        # First ring: full strength                                  # L138
        if g.cityp[x] == g.side and g.occupied[x] > 0:
            y += g.armysize[g.occupied[x]]

        # Second ring: 10% strength                                  # L139-142
        for k in range(1, 7):
            m = g.matrix[x][k]                                      # L139
            if m == 0 or m == a:
                continue  # tally4                                   # L139
            if g.cityp[m] == g.side and g.occupied[m] > 0:          # L140
                y = int(y + 0.1 * g.armysize[g.occupied[m]])
        # tally4: NEXT k                                            # L141-142

    # tally5: END SUB                                                # L143-145
    return y
