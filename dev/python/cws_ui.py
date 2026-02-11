"""cws_ui.py - Menu system and UI utilities.
Direct port of cws_ui.bm (QB64) to Python.

Original file: cws_ui.bm (309 lines)
Contains:
    SUB center(y, a$)        ->  center(g, y, text)
    SUB clrbot               ->  clrbot(g)
    SUB clrrite              ->  clrrite(g)
    SUB scribe(a$, flag)     ->  scribe(g, text, flag)
    SUB topbar               ->  topbar(g)
    SUB choices(b1, wide)    ->  choices(g, b1, wide)
    SUB menu(switch%)        ->  menu(g, switch)
    SUB mxw(wide)            ->  mxw(g) -> int
    SUB flags(who, w, a)     ->  flags(g, who, w, a)
    SUB roman(target, a$)    ->  roman(target) -> str

The menu SUB is the most complex: a GOTO/GOSUB-driven interactive
menu with arrow navigation, letter shortcuts, switch-dependent icon
highlighting, and F-key shortcuts. Restructured as a while loop with
pygame event polling.

QB64 INKEY$ 2-byte scan codes for special keys (second byte):
    H(72)=Up, P(80)=Down, I(73)=PgUp, Q(81)=PgDn
    =(61)=F3, A(65)=F7, >(62)=F4, B(66)=F8

Dependencies:
    cws_map:    icon(g, from_, dest, kind), usa(g), image2(g, text, s)
    cws_army:   armystat(g, index)
    cws_report: report(g, who)
"""

import os
import pygame
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cws_globals import GameState


# ─────────────────────────────────────────────────────────────────────────────
# SUB center(y, a$)  -- lines 1-5
# ─────────────────────────────────────────────────────────────────────────────

def center(g: 'GameState', y: int, text: str) -> None:
    """Print text centered horizontally on row y.

    Original: SUB center(y, a$) -- lines 1-5
    """
    x = len(text)                                                    # L2
    x = 26 - x // 2                                                 # L3
    g.screen.locate(y, 7 + x)                                       # L4
    g.screen.print_text(text)


# ─────────────────────────────────────────────────────────────────────────────
# SUB clrbot  -- lines 6-9
# ─────────────────────────────────────────────────────────────────────────────

def clrbot(g: 'GameState') -> None:
    """Clear the bottom status line (row 29).

    Original: SUB clrbot -- lines 6-9
    """
    g.screen.locate(29, 1)                                           # L7
    g.screen.print_text(" " * 79)
    g.screen.locate(29, 1)                                           # L8


# ─────────────────────────────────────────────────────────────────────────────
# SUB clrrite  -- lines 11-15
# ─────────────────────────────────────────────────────────────────────────────

def clrrite(g: 'GameState') -> None:
    """Clear the right panel (pixels 528-639, rows 1-450).

    Original: SUB clrrite -- lines 11-15
    """
    g.screen.view(528, 1, 639, 450)                                  # L12
    g.screen.cls(1)                                                  # L13
    g.screen.view()                                                  # L14


# ─────────────────────────────────────────────────────────────────────────────
# SUB scribe(a$, flag)  -- lines 16-27
# ─────────────────────────────────────────────────────────────────────────────

def scribe(g: 'GameState', text: str, flag: int) -> None:
    """Display and optionally log a message.

    flag=1: print on bottom bar
    flag=2: show as popup (image2)

    Original: SUB scribe(a$, flag) -- lines 16-27
    """
    if flag == 1:                                                    # L18
        clrbot(g)
        g.screen.print_text(text)
    elif flag == 2:                                                  # L19
        from cws_map import image2
        image2(g, text, 4)

    if g.history > 0:                                                # L21
        try:
            his_path = os.path.join(os.path.dirname(__file__),
                                    "..", "..", "cws.his")
            with open(his_path, "a") as f:                           # L22
                f.write(text.strip() + "\n")                         # L23-24
        except IOError:
            pass


# ─────────────────────────────────────────────────────────────────────────────
# SUB topbar  -- lines 28-58
# ─────────────────────────────────────────────────────────────────────────────

def topbar(g: 'GameState') -> None:
    """Draw the top status bar with side info, VP bar, difficulty, funds.

    Original: SUB topbar -- lines 28-58
    """
    s = g.screen

    s.locate(1, 1)                                                   # L29
    s.print_text(" " * 80)
    s.color(11)                                                      # L30
    s.locate(1, 10)                                                  # L31
    s.print_text(f"Input your decisions now for {g.force[g.side]} side ")
    s.color(14)
    s.print_text(f"{g.month_names[g.month]}, {g.year}  ")

    flags(g, g.side, 0, 0)                                          # L33

    c_top = 4                                                        # L34
    if g.bw > 0:
        c_top = 7
    s.color(c_top)
    s.locate(6, 68)                                                  # L35
    s.print_text(f"Difficulty {g.difficult}")
    s.locate(7, 68)                                                  # L36
    s.print_text(f"Funds:{g.cash[g.side]}")

    for i in range(1, 3):                                            # L38
        if g.victory[i] < 0:
            g.victory[i] = 0

    x = g.victory[1] + g.victory[2]                                  # L40
    y = 0
    c = 9                                                            # L41
    if g.side == 2:
        c = 7
    s.line(580, 15, 580, 35, 15)                                     # L42
    s.line(530, 20, 630, 30, 8 - c, "BF")                           # L43
    if x > 0:                                                        # L44
        y = int(100 * (g.victory[g.side] / x))

    s.line(530, 20, 530 + y, 30, c, "BF")                           # L46
    s.color(c)                                                       # L47
    s.locate(4, 68)
    s.print_text(f"VP : {g.victory[g.side]}")

    s.locate(5, 68)                                                  # L49
    s.print_text(f"( {y} %)")

    # Status string                                                  # L51-53
    a = "  Snd"
    if g.noise < 2:
        a = "   Snd"
        if g.noise == 0:
            a = "      "
    if g.graf > 0:
        a = a + f" G{g.graf}"
    a = a + f" {g.player}"

    s.color(c)                                                       # L54
    s.locate(26, 68)                                                 # L55
    s.print_text("F3 Redrw Scrn")
    s.locate(27, 68)                                                 # L56
    s.print_text("F7 End Turn")
    s.locate(28, 68)                                                 # L57
    s.print_text(a)


# ─────────────────────────────────────────────────────────────────────────────
# SUB mxw(wide)  -- lines 243-249
# ─────────────────────────────────────────────────────────────────────────────

def mxw(g: 'GameState') -> int:
    """Calculate maximum width needed for current menu items.

    Original: SUB mxw(wide) -- lines 243-249
    """
    wide = len(g.mtx[0]) + 1                                        # L244
    for i in range(1, g.size + 1):                                   # L245
        x = len(g.mtx[i])                                           # L246
        if x > wide:                                                 # L247
            wide = x
    return wide


# ─────────────────────────────────────────────────────────────────────────────
# SUB choices(b1, wide)  -- lines 59-76
# ─────────────────────────────────────────────────────────────────────────────

def choices(g: 'GameState', b1: int, wide: int) -> None:
    """Render the menu box, title, separator, and option text.

    Original: SUB choices(b1, wide) -- lines 59-76
    """
    s = g.screen
    boxc = g.colour                                                  # L60
    if g.wtype > 10:
        boxc = int(g.wtype / 10)
        g.wtype = g.wtype - 10 * boxc

    s.color(boxc)                                                    # L61

    # Clear menu area                                                # L62-64
    x1 = 8 * g.tlx - 6
    y1 = 16 * g.tly - 11
    x2 = 8 * (g.tlx + wide + 1) + 7
    y2 = 16 * (g.tly + g.size + 2) + 8
    s.view(x1, y1, x2, y2)
    s.cls(1)
    s.view()

    # Outer box                                                      # L65
    s.line(x1, y1, x2, y2, g.colour, "B")

    # Title separator                                                # L66
    s.line(8 * g.tlx - 2, 16 * (g.tly + 1) + 3,
           8 * (g.tlx + wide + 1) + 3, 16 * (g.tly + 1) + 6,
           g.colour, "B")

    # Double border if wtype=2                                       # L67-69
    if abs(g.wtype) == 2:
        s.line(8 * g.tlx - 2, 16 * g.tly - 8,
               8 * (g.tlx + wide + 1) + 3,
               16 * (g.tly + g.size + 2) + 4,
               g.colour, "B")

    s.color(g.colour)                                                # L70

    # Title                                                          # L72
    s.locate(g.tly + 1, g.tlx + b1)
    s.print_text(g.mtx[0])

    # Options                                                        # L73-75
    for i in range(1, g.size + 1):
        s.locate(g.tly + 2 + i, g.tlx + 2)
        s.print_text(g.mtx[i])


# ─────────────────────────────────────────────────────────────────────────────
# SUB menu(switch%)  -- lines 77-242
#
# The main interactive menu. This is the most complex function in the UI.
#
# GOTO labels restructured:
#   remenu  -> top of function (re-entered via F3 redraw)
#   sel1    -> top of selection highlight + event loop
#   reglr   -> normal key handling after crsr returns
#   crsr    -> key polling subroutine (now inline in event loop)
#   arrows  -> arrow key handler
#   limits  -> wrap row within 1..size
#   called  -> cleanup and return
#   noadjust -> center tlx if 0
#
# switch modes:
#   0 = standard menu
#   1 = highlight city with white box (icon 7/8)
#   2 = highlight city with arrow + show defender (icon 9/8)
#   3 = letter-input mode (for newcity picker)
#   4 = show army stats
#   5 = show army info in bottom bar
#   6 = highlight army location (icon 9/8 on armyloc)
#   8 = show commander face
#   9 = highlight city with arrow (icon 9/8)
# ─────────────────────────────────────────────────────────────────────────────

def menu(g: 'GameState', switch: int) -> int:
    """Interactive menu. Returns selection in g.choose.

    Original: SUB menu(switch%) -- lines 77-242
    """
    from cws_map import icon

    s = g.screen

    # ── remenu: initialization ────────────────────────────────────  L78-115
    if g.colour == 0:                                                # L79
        g.colour = 7
    # L80: LOCATE 1,1,0 (hide cursor - N/A in pygame)
    if g.mtx[0] == "":                                               # L81
        g.mtx[0] = "M E N U"

    wide = mxw(g)                                                    # L83
    if g.tlx == 0:                                                   # L84
        g.tlx = int(40.5 - 0.5 * wide)

    if g.choose < 21:                                                # L85
        g.choose = 1
    if g.choose > 21:                                                # L86
        g.choose = g.choose - 21
    if g.choose > 21:                                                # L87
        g.choose = 1
    row = g.choose                                                   # L88
    if row < 1:
        row = 1
    if row > g.size:                                                 # L89
        row = 1
    g.choose = row                                                   # L90
    row1 = row                                                       # L91

    if g.tly == 0:                                                   # L93
        g.tly = int(11.5 - 0.5 * g.size)
    if g.tly + g.size > 26:                                          # L94
        g.tly = 26 - g.size

    b1 = int(0.5 * (wide - len(g.mtx[0])) + 0.5) + 1               # L113

    # Draw menu                                                      # L115
    choices(g, b1, wide)

    flag = 0  # local flag for switch=2 defender display

    # ── sel1: main selection loop ─────────────────────────────────  L116+
    while True:
        # Always clean any leftover arrow before drawing a new one
        from cws_map import _clear_arrow
        _clear_arrow(g)

        # Switch-specific highlighting at sel1                       # L117-155
        if switch == 1:                                              # L118
            icon(g, g.array[row], 0, 7)
        elif switch == 2:                                            # L119-134
            icon(g, g.array[row], 0, 9)
            target = g.occupied[g.array[row]]                        # L120
            if target > 0:                                           # L121
                flag = 1                                             # L122
                t = g.armyname[target]                               # L123
                if len(t) > wide:                                    # L124
                    t = t[:wide]
                s.color(12)                                          # L125
                s.locate(g.tly + 2 + row, g.tlx + 2)                # L126
                s.print_text(" " * wide)
                s.locate(g.tly + 2 + row, g.tlx + 2)                # L127
                s.print_text(t)
                s.locate(g.tly + 4 + g.size, g.tlx + 1)             # L128
                s.print_text(" " * 12)
                s.locate(g.tly + 4 + g.size, g.tlx + 1)             # L129
                s.print_text(f"Size {g.armysize[target]}00")         # L129-130
            else:
                flag = 0                                             # L132
                s.locate(g.tly + 4 + g.size, g.tlx + 1)             # L133
                s.print_text(" " * 12)
        elif switch == 4:                                            # L135
            from cws_army import armystat
            armystat(g, g.array[row])
        elif switch == 5:                                            # L136
            s.color(11)
            clrbot(g)
            # NOTE: 'index' here refers to the caller's context.
            # In QB64 this was a shared local. We use g.array[row] as index.
            idx = g.array[row] if hasattr(g, 'array') else row
            s.print_text(
                f"{g.armyname[idx]}  Exp={g.armyexper[idx]}"
                f" Cash={g.cash[g.side]}"
            )
        elif switch == 6:                                            # L137
            icon(g, g.armyloc[g.array[row]], 0, 9)
        elif switch == 8:                                            # L138-153
            # Commander face graphic
            if g.graf > 2 and row > 0:
                s.line(548, 148, 592, 216, 15, "B")                 # L140
                a = row                                              # L141
                if g.side == 1:
                    a = 6 - row
                face_surfs = getattr(g, 'face_surfaces', {})
                if a in face_surfs:
                    s.put_image(550, 150, face_surfs[a])             # L147
                    if g.side == 2:                                   # L148-151
                        s.paint(560, 160, 8, 0)
                        s.paint(570, 155, 7, 0)
        elif switch == 9:                                            # L154
            icon(g, g.array[row], 0, 9)

        # Highlight current row                                      # L156-161
        if flag == 0:
            s.color(g.hilite)                                        # L157
            s.locate(g.tly + 2 + row, g.tlx + 2)                    # L158
            s.print_text(g.mtx[row])                                 # L159
            if g.bw > 0:                                             # L160
                s.line(8 * (g.tlx + 1),
                       16 * (g.tly + row + 1),
                       8 * (g.tlx + len(g.mtx[row]) + 1) - 1,
                       16 * (g.tly + row + 2) - 1,
                       g.hilite, "B")

        s.update()

        # ── crsr: wait for key input ──────────────────────────────  L182+
        key_result = _wait_menu_key(g)
        action = key_result["action"]
        key_char = key_result.get("char", "")

        # ── Process key result ────────────────────────────────────

        # switch=3 special handling (letter-input mode)              # L163-166
        if switch == 3:
            if action == "up":                                       # L164
                g.choose = 1
                break  # goto called
            elif action == "enter":                                  # L165
                g.choose = 2
                break  # goto called
            elif action == "down":                                   # L166
                g.choose = 3
                break  # goto called
            elif action == "char":
                # Any letter -> choose = -ASC(UCASE$(key))          # L185
                g.choose = -ord(key_char.upper())
                break  # goto called
            elif action == "escape":
                g.choose = -ord(key_char) if key_char else -27
                break
            # Other keys: loop back to sel1
            continue

        # reglr: normal mode handling                                # L167+
        if action == "enter":                                        # L168
            g.choose = row
            break  # goto called

        if action == "escape":                                       # L186
            g.choose = -1
            break  # goto called

        if action == "letter_match":                                 # L188-191
            g.choose = key_result["match"]
            row = g.choose
            break  # goto called

        if action == "f3":                                           # L200-205
            from cws_map import usa
            s.cls()
            usa(g)
            choices(g, b1, wide)
            topbar(g)
            continue  # back to sel1

        if action == "f7":                                           # L207-209
            g.choose = 99
            break  # goto called

        if action == "f8":                                           # L212-216
            from cws_report import report
            report(g, -1)
            choices(g, b1, wide)
            topbar(g)
            continue  # back to sel1

        # Arrow navigation                                          # L193-199
        if action in ("up", "down", "home", "end"):
            # In QB64, arrows: sets row1=row BEFORE moving row,     # L195
            # then RETURNs to reglr: which unhighlights row1.
            row1 = row                                               # L195

            if action == "up":                                       # L196
                row -= 1
            elif action == "down":                                   # L198
                row += 1
            elif action == "home":                                   # L197
                row = 1
            elif action == "end":                                    # L199
                row = g.size

            # limits:                                                # L220-223
            if row > g.size:
                row = 1
            if row < 1:
                row = g.size

            # reglr: unhighlight old row                             # L169-171
            if switch == 2:                                          # L169
                s.locate(g.tly + 2 + row1, g.tlx + 2)
                s.print_text(" " * wide)
            s.color(g.colour)                                        # L170
            s.locate(g.tly + 2 + row1, g.tlx + 2)                   # L171
            s.print_text(g.mtx[row1])

            # Clean up old row's icon                                # L173-178
            from cws_map import _clear_arrow
            _clear_arrow(g)                                          # erase arrow (kinds 9)
            if switch == 1:                                          # L174 (kind 7 highlight box)
                if g.mtx[row1] != "EXIT":                            # L175
                    icon(g, g.array[row1], 0, 8)

            g.choose = row                                           # L180
            flag = 0  # reset for next iteration
            continue  # goto sel1                                    # L181

    # ── called: cleanup and return ────────────────────────────────  L231-242
    if g.noise > 0:                                                  # L232
        from cws_sound import qb_sound
        qb_sound(700, 0.5)
    s.color(g.colour)                                                # L233
    g.tlx = 0                                                        # L234
    g.tly = 0

    # Restore icon for current row                                   # L235-240
    from cws_map import _clear_arrow
    _clear_arrow(g)                                                  # erase arrow (kinds 9)
    if switch == 1:                                                  # L236 (kind 7 highlight box)
        icon(g, g.array[row], 0, 8)                                  # L237

    s.view()                                                         # L241
    return g.choose


def _wait_menu_key(g: 'GameState') -> dict:
    """Wait for a meaningful key press in the menu context.

    Replaces the GOSUB crsr / arrows block (lines 182-218).
    Returns a dict with 'action' and optional extra fields.

    Mapped from QB64 INKEY$ scan codes:
        Up=H(72), Down=P(80), PgUp=I(73), PgDn=Q(81)
        F3==(61), F7=A(65), F4=>(62), F8=B(66)
    """
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                raise SystemExit

            if event.type == pygame.KEYDOWN:
                key = event.key

                # Enter                                              # L183
                if key == pygame.K_RETURN:
                    return {"action": "enter"}

                # Escape                                             # L186
                if key == pygame.K_ESCAPE:
                    return {"action": "escape", "char": chr(27)}

                # Arrow keys                                         # L196-199
                if key == pygame.K_UP:
                    return {"action": "up"}
                if key == pygame.K_DOWN:
                    return {"action": "down"}
                if key in (pygame.K_HOME, pygame.K_PAGEUP):
                    return {"action": "home"}
                if key in (pygame.K_END, pygame.K_PAGEDOWN):
                    return {"action": "end"}

                # F-keys                                             # L200-217
                if key == pygame.K_F3:
                    return {"action": "f3"}
                if key == pygame.K_F7:
                    return {"action": "f7"}
                if key == pygame.K_F8:
                    return {"action": "f8"}

                # Printable character                                # L184-191
                if event.unicode and len(event.unicode) == 1:
                    ch = event.unicode
                    if ch.isalpha():
                        # Try to match first letter of a menu item   # L188-191
                        for k in range(1, g.size + 1):
                            item = g.mtx[k].lstrip()
                            if item:
                                c1 = item[0].upper()
                                if c1 == ch.upper():
                                    return {"action": "letter_match",
                                            "match": k, "char": ch}
                        # No match -- in switch=3, still return char
                        return {"action": "char", "char": ch}

        pygame.time.wait(16)


# ─────────────────────────────────────────────────────────────────────────────
# SUB flags(who, w, a)  -- lines 250-283
# ─────────────────────────────────────────────────────────────────────────────

def flags(g: 'GameState', who: int, w: int, a: int) -> None:
    """Draw a Union or Confederate flag.

    Original: SUB flags(who, w, a) -- lines 250-283
    """
    s = g.screen

    x = 585 + w                                                      # L251
    y = 200
    if w == 0:
        y = 180
    if a != 0:                                                       # L252
        y = a

    if who == 1:                                                     # L254: Union flag
        s.line(x - 17, y - 15, x + 17, y + 7, 4, "BF")             # L255
        for i in range(-13, 10, 5):                                  # L256-258
            s.line(x - 17, y + i, x + 17, y + i - 1, 7, "B")
        s.line(x - 17, y - 15, x, y, 1, "BF")                      # L259
        if w == 0:                                                   # L260
            s.color(9)
            s.locate(10, 70)
            s.print_text("U N I O N")
        for i in range(-16, 0, 3):                                   # L261-263
            for j in range(-14, 0, 4):
                s.pset(x + i, y + j, 7)

    elif who == 2:                                                   # L264: Confederate flag
        s.line(x - 17, y - 15, x + 17, y + 7, 4, "BF")             # L265
        # White X                                                    # L266-267
        s.line(x - 17, y - 13, x + 15, y + 7, 7)
        s.line(x - 15, y - 15, x + 17, y + 5, 7)
        # Blue X                                                    # L269-271
        s.line(x - 17, y + 7, x + 17, y - 15, 1)
        s.line(x - 17, y + 6, x + 16, y - 15, 1)
        s.line(x - 16, y + 7, x + 17, y - 14, 1)
        # More white X lines                                        # L272-273
        s.line(x - 17, y + 5, x + 15, y - 15, 7)
        s.line(x - 15, y + 7, x + 17, y - 13, 7)
        # Blue diagonal                                             # L275-277
        s.line(x - 17, y - 15, x + 17, y + 7, 1)
        s.line(x - 17, y - 14, x + 16, y + 7, 1)
        s.line(x - 16, y - 15, x + 17, y + 6, 1)
        # Border                                                    # L278
        s.line(x - 17, y - 15, x + 17, y + 7, 4, "B")

        if w == 0:                                                   # L280
            s.color(4)
            s.locate(10, 70)
            s.print_text("R E B E L")


# ─────────────────────────────────────────────────────────────────────────────
# SUB roman(target, a$)  -- lines 284-308
# ─────────────────────────────────────────────────────────────────────────────

def roman(target: int) -> str:
    """Generate roman numeral army name like 'Union III' or 'Rebel VII'.

    NOTE: In original QB64, target is modified in-place (subtracted).
    Here we work on a local copy.

    Original: SUB roman(target, a$) -- lines 284-308
    """
    n = target
    a = "Union "                                                     # L285
    if n > 20:
        a = "Rebel "
    if n > 20:                                                       # L286
        n = n - 20
    if n > 10:                                                       # L287
        a = a + "X"
        n = n - 10

    if n < 4:                                                        # L289
        # add1s: GOSUB                                               # L290, L304-306
        if n > 0:
            a = a + "I" * n
    elif n == 4:                                                     # L291-292
        a = a + "IV"
    elif 5 <= n <= 8:                                                # L293-296
        a = a + "V"
        x = n - 5
        if x > 0:
            a = a + "I" * x
    elif n == 9:                                                     # L297-298
        a = a + "IX"
    elif n == 10:                                                    # L299-300
        a = a + "X"

    return a
