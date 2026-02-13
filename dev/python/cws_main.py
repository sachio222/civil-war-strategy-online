"""cws_main.py - Main game loop.
Direct port of CWSTRAT.BAS (742 lines).

This is the master control file that ties all modules together.
Contains the title screen, main menu, commands/utility/files submenus,
monthly turn processing, and game initialization.

Labels ported:
    newgame:   L8    → _newgame_init()
    iron:      L42   → inline in _newgame_init() (dead label)
    notitle:   L89   → inline in _title_screen()
    newmonth:  L136  → _newmonth()
    menu0:     L171  → _main_menu() while loop
    endrnd:    L234  → _end_round()
    optmen:    L246  → _commands_menu() while loop
    utile:     L391  → _utility_menu() while loop
    filex:     L656  → _files_menu() while loop
    loader:    L668  → _loader()

GOSUB helpers:
    unionplus  L707  → _unionplus()
    blanken    L711  → _blanken()
    rusure     L698  → _rusure()
"""

import os
import random
from datetime import date
from typing import TYPE_CHECKING

from cws_paths import save_dir, save_path_write
from cws_globals import UNION, CONFEDERATE

if TYPE_CHECKING:
    from cws_globals import GameState


# ═══════════════════════════════════════════════════════════════════════════
#  GOSUB helpers
# ═══════════════════════════════════════════════════════════════════════════

def _unionplus(g: 'GameState') -> None:
    """GOSUB unionplus (L707-709): calculate Union advantage."""
    g.usadv = 120 * g.difficult                             # L707
    if g.player >= 2:                                       # 2=local 2P, 3=online
        g.usadv = 50 * g.difficult
    if g.realism > 0:                                       # L708
        g.usadv = int(g.usadv * 0.7)


def _blanken(g: 'GameState') -> None:
    """GOSUB blanken (L711-717): 2-player turn transition screen."""
    s = g.screen
    c = g.side_color(g.side)                                 # L711
    s.cls()                                                 # L712
    s.line(100, 200, 500, 300, c, "BF")
    s.line(100, 200, 500, 300, 8 - c, "B")                 # L713
    s.color(7)                                              # L714
    s.locate(14, 31)
    s.print_text(f" {g.month_names[g.month]} {g.year}")
    s.color(11)                                             # L715
    s.locate(17, 30)
    s.print_text(f"{g.force[g.side]} PLAYER TURN")
    s.update()
    _wait_key(g)                                            # L716


def _month_transition(g: 'GameState') -> None:
    """Full-screen neutral transition before monthly events in 2-player mode."""
    s = g.screen
    s.cls()
    s.line(100, 160, 500, 320, 5, "BF")   # magenta box (neutral color)
    s.line(100, 160, 500, 320, 13, "B")    # bright magenta border
    s.color(15)
    s.locate(13, 22)
    s.print_text(f"EVENTS FOR {g.month_names[g.month]} {g.year}")
    s.color(14)
    s.locate(16, 21)
    s.print_text("both players watch — press any key")
    s.update()
    _wait_key(g)


def _wait_key(g: 'GameState') -> None:
    """DO WHILE INKEY$="": LOOP"""
    import pygame
    g.screen.update()
    while True:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                return
            if ev.type == pygame.VIDEORESIZE:
                g.screen.update()
            if ev.type == pygame.KEYDOWN:
                return
        pygame.time.wait(30)


def _rusure(g: 'GameState') -> bool:
    """GOTO rusure (L698-705): quit confirmation. Returns True to quit."""
    from cws_ui import menu, clrrite

    g.choose = 23                                           # L699
    g.mtx[0] = "Quit"                                      # L700
    g.mtx[1] = "Yes"                                       # L701
    g.mtx[2] = "No"                                        # L702
    g.size = 2                                              # L703
    g.colour = 5
    g.tlx = 67                                              # L704
    g.tly = 15
    menu(g, 0)                                              # L705
    clrrite(g)
    return g.choose == 1


# ═══════════════════════════════════════════════════════════════════════════
#  Font DATA (L719-725)
# ═══════════════════════════════════════════════════════════════════════════

def _load_font(g: 'GameState') -> None:
    """Load QB64 DRAW font definitions (L33-34, L719-725)."""
    data = [
        "",  # index 0 unused
        "U2E2F2D2BU1L3", "U4R3F1G1L2BR2BF1G1L2", "H1U2E1R2F1BD2G1L1",
        "U4R3F1D1D1G1L2", "U4R3BD2BL1L2D2R3", "U4R3BD2BL1L2",
        "H1U2E1R3BD2L2BD2R2U1", "U4BD2BR1R3U2BD3D1", "R1U4L1R2BL1BD4R1",
        "R1E1U3BG3F1", "U4BR3G2F2", "U4BD4BR1R1", "U4F2E2D4",
        "U4F4U4", "H1U2E1R2F1D2G1L1", "U4R3F1G1L2",
        "H1U2E1R2F1D2G1L1BE1F1R1", "U4R3F1G1L2BR1F2", "R3E1H1L2H1E1R3",
        "U4L2BR3R1", "H1U3BR4D3G1L1", "H2U2BR4D2G2",
        "H2U2BF3BU1D1F1E2U2", "E4BD4H4", "U2H2BR4G2", "E4L4BD4R4",
    ]
    for k in range(1, 27):
        if k < len(data):
            g.font[k] = data[k]


# ═══════════════════════════════════════════════════════════════════════════
#  newgame: (L8-53) + iron: (L42-53)
# ═══════════════════════════════════════════════════════════════════════════

def _newgame_init(g: 'GameState', replay: int) -> None:
    """Full game reset and data load."""
    from cws_data import filer, occupy, load_cities
    from cws_ui import clrbot, flags
    from cws_util import tick

    s = g.screen

    # Reset state                                           L9
    g.pcode = 0
    g.rflag = 0
    for k in range(1, 41):                                  # L10-16
        g.armysize[k] = 0
        g.armyloc[k] = 0
        g.armymove[k] = 0
        g.armylead[k] = 0
        g.armyname[k] = ""

    g.usadv = 0                                             # L17
    g.emancipate = 0
    for k in range(1, 3):                                   # L18-21
        g.navysize[k] = 0
        g.navyloc[k] = 0
        g.navymove[k] = 0
        g.rr[k] = 0
        g.victory[k] = 0
        g.tracks[k] = 0

    g.filel = 1                                             # L23
    g.vicflag[1] = 1
    filer(g, 1)                                             # L24

    # L25-31: load all VGA sprites (mtn, cwsicon, faces, forts)
    from vga_sprite import load_all_sprites
    load_all_sprites(g)

    _load_font(g)                                           # L33-34

    # Realism: force all ships to wooden pre-1862           L36-41
    if g.realism > 0 and g.year < 1862:
        for i in range(1, 3):
            g.fleet[i] = "W" * len(g.fleet[i])

    # iron: (L42-53) — post-load setup
    if g.player < 1 or g.player > 3:                        # L43
        g.player = 1
    if g.player >= 2 or g.side == 0:                        # L44
        g.side = 1
    if g.side == UNION:                                      # L45
        g.randbal = 7
    if g.side == CONFEDERATE:                               # L46
        g.randbal = 3
    if g.turbo < 1:                                         # L47
        g.turbo = 2.0
    if g.side == UNION and g.difficult < 3:                  # L48
        g.cash[CONFEDERATE] += 600 - 100 * g.difficult
    if g.side == CONFEDERATE and g.difficult > 3:           # L49
        g.cash[UNION] += 100 * g.difficult

    for i in range(1, 3):                                   # L52
        g.income[i] = g.cash[i]
        g.cash[i] = int(g.cash[i] + 50 * random.random())
    g.choose = 0                                            # L53

    # L57-62: cwsicon.vga / Ncap — loaded by load_all_sprites() above

    # Title screen                                          L63-88
    s.cls()                                                 # L63
    s.color(11)                                             # L64
    s.locate(14, 26)
    s.print_text("VGA CIVIL WAR STRATEGY ONLINE")
    s.color(4)                                              # L65
    s.locate(15, 32)
    s.print_text("Registered Edition")
    s.color(14)                                             # L66
    s.locate(27, 10)
    s.print_text("(c) 1998, 2017, 2018, 2024, 2026 by W. R. Hutsell,")
    s.locate(28, 17)
    s.print_text("Dave Mackey, and J. Krajewski")
    s.locate(27, 72)                                        # L67
    s.print_text("v1.7")
    s.line(190, 170, 440, 260, 1, "B")                     # L68
    s.line(180, 180, 450, 250, 7, "B")                     # L69
    flags(g, 1, -440, 0)                                    # L70
    flags(g, 2, -100, 0)

    # L71-88: title music
    s.update()
    if replay == 0 and g.noise == 2 and g.choose == 0:     # L71
        from cws_sound import qb_play_interruptible, shen
        if g.side == UNION:                                  # L72: Union
            skip = False
            if not skip:
                skip = qb_play_interruptible("MST170o1e8o0b8o1e8")           # L74
            if not skip:
                skip = qb_play_interruptible("e8e4f#8g4f#8")                 # L76
            if not skip:
                skip = qb_play_interruptible("g4e8d2o0b8o1d2 ")              # L78
            if not skip:
                skip = qb_play_interruptible(
                    "o1e8o0b8o1e8e8e4f#8g4f#8g4a8b2g8b2MLg16a16")           # L80
            if not skip:
                skip = qb_play_interruptible(
                    "MSb4b8b8a8g8a4a8a4f#8g4g8MLg8f#8")                     # L82
            if not skip:
                skip = qb_play_interruptible(
                    "MSe8f#4f#8f#8g8a8b4.a4.g4.f#4.o0b8o1e8e8e4d8e2.")      # L84
        else:                                               # L85: Rebel
            shen(g)                                         # L86
    # notitle: (L89)

    _unionplus(g)                                           # L90

    # Load cities (L92-102 handled entirely by load_cities)
    load_cities(g)                                          # L93-102
    clrbot(g)                                               # L103

    # L105-109
    g.wtype = 2                                             # L107
    g.hilite = 15                                           # L108

    s.update()


# ═══════════════════════════════════════════════════════════════════════════
#  Title menu (L110-134)
# ═══════════════════════════════════════════════════════════════════════════

def _title_menu(g: 'GameState') -> str:
    """Show title menu. Returns 'resume', 'new', 'online', 'online_resume', or 'quit'."""
    from cws_ui import menu
    from cws_online import session_exists

    if g.player >= 2:                                       # L110
        _blanken(g)

    has_online = session_exists()

    g.mtx[0] = "CIVIL WAR STRATEGY ONLINE"                  # L111
    g.mtx[1] = "Resume Saved Game"                          # L112
    idx = 1
    if has_online:
        idx += 1
        g.mtx[idx] = "Resume Online Game"
    idx += 1
    g.mtx[idx] = "NEW Game"                                 # L113
    new_idx = idx
    idx += 1
    g.mtx[idx] = "Quit"                                    # L114
    quit_idx = idx
    g.tlx = 33                                              # L115
    g.tly = 20
    g.colour = 5
    g.size = idx
    g.choose = 23                                           # L116
    menu(g, 0)                                              # L117

    if g.choose == 1:                                       # Resume Saved
        return "resume"
    if has_online and g.choose == 2:                        # Resume Online
        return "online_resume"
    if g.choose == new_idx:                                 # Start NEW Game
        return "new"
    if g.choose == quit_idx:                                # Quit
        return "quit"
    return "new"


def _start_new_game(g: 'GameState') -> None:
    """Start new game: init history if enabled, draw map (L124-133)."""
    from cws_map import usa

    s = g.screen
    if g.history == 1:                                      # L124
        s.cls()                                             # L125
        try:
            his_path = save_path_write("cws.his")
            # L126: backup old history — skip shell command
            with open(his_path, 'w') as f:                  # L127-129
                f.write(f"                    [ HISTORY OF GAME BEGUN {date.today()} ]\n")
        except OSError:
            pass
    else:
        s.cls()                                             # L131

    usa(g)                                                  # L133


# ═══════════════════════════════════════════════════════════════════════════
#  loader: (L668-672)
# ═══════════════════════════════════════════════════════════════════════════

def _loader(g: 'GameState') -> None:
    """Load a saved game."""
    from cws_data import filer

    g.screen.cls()                                          # L119/668
    filer(g, g.choose + 1)                                  # L670
    if g.choose == 1:                                       # L671
        g.rflag = 0
        g.mflag = 0
        g.nflag = 0


# ═══════════════════════════════════════════════════════════════════════════
#  newmonth: (L136-168)
# ═══════════════════════════════════════════════════════════════════════════

def _newmonth(g: 'GameState') -> bool:
    """Monthly turn processing. Returns True if game restarted (pcode)."""
    from cws_ui import scribe
    from cws_map import tupdate, usa
    from cws_flow import victor

    s = g.screen

    if g.side > 2:                                          # L137
        g.side = 1

    if g.player == 2:
        _month_transition(g)
        usa(g)  # redraw map so tupdate has fresh canvas

    if g.player == 3:
        g.event_log = []
        g.event_log.append(f"__month__:{g.month_names[g.month]} {g.year}")
        # Save pre-turn state snapshot for animated replay
        g.event_log.append({
            "type": "__snapshot__",
            "armyloc": list(g.armyloc),
            "armymove": list(g.armymove),
            "armysize": list(g.armysize),
            "armyname": list(g.armyname),
            "armylead": list(g.armylead),
            "armyexper": list(g.armyexper),
            "supply": list(g.supply),
            "occupied": list(g.occupied),
            "fort": list(g.fort),
            "cityp": list(g.cityp),
            "navyloc": list(g.navyloc),
            "navysize": list(g.navysize),
            "fleet": list(g.fleet),
            "victory": list(g.victory),
            "capcity": list(g.capcity),
            "commerce": g.commerce,
            "raider": g.raider,
        })

    a_str = (f"--------> EVENTS FOR {g.month_names[g.month]}"
             f" {g.year} --------")
    scribe(g, a_str, 0)                                     # L139
    tupdate(g)                                              # L140

    g.control[1] = 0                                        # L141
    g.control[2] = 0

    for i in range(1, 3):                                   # L143-147
        g.income[i] = 0                                     # L144
        if g.cash[i] > 19999:                               # L145
            g.cash[i] = 19999
        if g.cash[i] < 0:                                   # L146
            g.cash[i] = 0

    if g.player == 1 and g.side == CONFEDERATE:              # L148
        g.income[UNION] += g.usadv

    for i in range(1, 41):                                  # L150-153
        if g.cityp[i] > 0:                                 # L151
            x = g.cityp[i]
            g.control[x] += 1
            g.income[x] += g.cityv[i]
        g.armymove[i] = 0                                   # L152

    for i in range(1, 3):                                   # L155-158
        g.navymove[i] = 0
        if g.capcity[i] > 0:
            g.income[i] += 100
        g.cash[i] += g.income[i]                            # L156
        if g.commerce > 0 and i != g.commerce:              # L157
            g.cash[i] -= g.raider

    g.vptotal = g.income[1] + g.income[2]                   # L159

    chosit = 22                                             # L161 (local)
    if g.player >= 2:                                       # L162
        _blanken(g)
        usa(g)

    victor(g)                                               # L163
    # L164: ON ERROR GOTO 0 — no-op in Python

    if g.pcode > 0:                                         # L165
        for k in range(1, 41):                              # L166
            g.armyloc[k] = 0
        return True  # signal: restart game                 L167

    return False


# ═══════════════════════════════════════════════════════════════════════════
#  endrnd: (L234-237)
# ═══════════════════════════════════════════════════════════════════════════

def _end_round(g: 'GameState') -> str:
    """End round: reset flags. Returns 'newmonth', 'menu0', or 'online_wait'."""
    from cws_map import usa

    g.rflag = 0                                             # L235
    g.mflag = 0
    g.nflag = 0

    if g.player == 3:                                       # Online mode
        return "online_wait"

    if g.player == 2:                                       # L236
        g.side += 1
        if g.side == CONFEDERATE:
            _blanken(g)
            usa(g)
            return "menu0"
    return "newmonth"                                       # L237


# ═══════════════════════════════════════════════════════════════════════════
#  Commands submenu — optmen: (L246-386)
# ═══════════════════════════════════════════════════════════════════════════

def _commands_menu(g: 'GameState') -> None:
    """Commands submenu loop (CASE 7)."""
    from cws_ui import menu, clrbot, clrrite, scribe
    from cws_util import starfin, tick, stax
    from cws_army import cancel, combine, movefrom, placearmy, resupply
    from cws_army import cutoff
    from cws_combat import fortify
    from cws_misc import newcity
    from cws_map import showcity, icon
    from cws_recruit import commander
    from cws_army import relieve

    s = g.screen

    while True:                                             # optmen:
        g.tlx = 67                                          # L247
        g.tly = 13
        s.color(11)                                         # L248
        s.locate(g.tly - 2, g.tlx)
        s.print_text("esc=Main Menu")
        g.hilite = 15                                       # L249
        g.colour = 3
        chosit = 24

        g.mtx[0] = "Commands"                              # L250
        g.mtx[1] = "Cancel"                                # L251
        g.mtx[2] = "Fortify"                               # L252
        if g.cash[g.side] < 200:
            g.mtx[2] = "-"
        g.mtx[3] = "Join"                                  # L253
        g.mtx[4] = "Supply"                                # L254
        g.mtx[5] = "Capital"                               # L255
        if g.capcity[g.side] == 0 or g.cash[g.side] < 500:
            g.mtx[5] = "-"
        g.mtx[6] = "Detach"                                # L256
        if g.side == UNION:
            g.mtx[6] = "-"
        g.mtx[7] = "Army Drill"                            # L257
        g.mtx[8] = "Relieve"                               # L258
        g.mtx[9] = "MAIN MENU"                             # L259
        g.size = 9                                          # L260
        menu(g, 0)                                          # L261
        clrrite(g)
        chosit = 28                                         # L262

        # ── inner SELECT CASE ──                           L263
        if g.choose == 1:                                   # Cancel (L267)
            cancel(g, g.side)                               # L268
            g.mflag = 0
            g.choose = 22                                   # L269

        elif g.choose == 2:                                 # Fortify (L273)
            if g.cash[g.side] < 200:                        # L274
                s.color(11)
                clrbot(g)
                s.print_text("Not enough money for fort")
                return  # GOTO menu0
            fortify(g)                                      # L275
            if g.cash[g.side] < 200:                        # L276
                return  # GOTO menu0
            g.choose = 23                                   # L277
            continue                                        # GOTO optmen

        elif g.choose == 3:                                 # Combine (L282)
            x = combine(g, g.side)                          # L283-284
            if x < 0:                                       # L285
                clrbot(g)                                   # L286
                s.color(11)                                 # L287
                s.print_text("No eligible armies in same city to combine")
                stax(g, g.side)                             # L289
                return  # GOTO menu0
            g.choose = 24                                   # L292
            continue                                        # GOTO optmen

        elif g.choose == 4:                                 # Supply (L297)
            star, fin = starfin(g, g.side)                  # L298
            g.mtx[0] = "Supply"                             # L299
            g.tlx = 67                                      # L300
            g.tly = 5
            g.colour = 5
            g.size = 0                                      # L301
            for i in range(star, fin + 1):                  # L302
                if g.armyloc[i] == 0 or g.supply[i] > 1:   # L303
                    continue  # alone
                if g.realism > 0:                           # L304
                    a = cutoff(g, g.side, g.armyloc[i])     # L305
                    if a < 1:                               # L306
                        clrbot(g)
                        s.color(15)
                        s.print_text(
                            f"{g.force[g.side]} army in "
                            f"{g.city[g.armyloc[i]]} is CUT OFF !"
                        )
                        tick(g, g.turbo)
                        continue  # alone
                g.size += 1                                 # L308
                mx = min(11, len(g.armyname[i]))            # L309
                g.mtx[g.size] = g.armyname[i][:mx]         # L310
                g.array[g.size] = i                         # L311

            if g.size == 0:                                 # L314
                s.color(11)
                clrbot(g)
                s.print_text(
                    f"All eligible {g.force[g.side]} armies have supplies"
                )
                return  # GOTO menu0

            menu(g, 6)                                      # L315
            clrrite(g)
            if g.choose < 0:                                # L316
                return  # GOTO menu0
            index = g.array[g.choose]                       # L317
            if g.supply[index] < 2:                         # L318
                resupply(g, index)                           # L319
                placearmy(g, index)                          # L320
            g.choose = 25                                   # L322
            continue                                        # GOTO optmen

        elif g.choose == 5:                                 # Move Capital (L327)
            if g.capcity[g.side] == 0 or g.cash[g.side] < 500:  # L328
                clrbot(g)
                s.color(11)
                s.print_text("Cannot move capital")
                return  # GOTO menu0
            g.cash[g.side] -= 500                           # L329
            g.victory[g.enemy_of()] += 50                    # L330
            clrrite(g)                                      # L331
            g.mtx[0] = "Capital"                            # L332
            a_old = g.city[g.capcity[g.side]]               # L333
            index = newcity(g, g.capcity[g.side])           # L334
            if index == 0:                                  # L335
                return  # GOTO menu0
            g.capcity[g.side] = index                       # L336
            clrbot(g)                                       # L337
            s.print_text(
                f"{g.force[g.side]} capital moved from {a_old} "
                f"to {g.city[g.capcity[g.side]]}"
            )
            clrrite(g)                                      # L338
            showcity(g)                                     # L339
            tick(g, 9)                                      # L340
            clrbot(g)
            # Falls through to L386 → GOTO optmen

        elif g.choose == 6:                                 # Detach (L344)
            if g.side == UNION:                              # L345
                clrbot(g)
                s.color(11)
                s.print_text("Option not available to Union")
                return  # GOTO menu0
            s.color(14)                                     # L346
            s.locate(4, 68)
            s.print_text("DETACH UNIT")
            index, target = movefrom(g)                     # L347
            if target < 1 or index < 1:
                return  # GOTO menu0
            if g.armysize[index] < 65:                      # L348
                clrbot(g)
                s.print_text("Too small to detach")
                tick(g, g.turbo)
                return  # GOTO menu0
            empty = commander(g, 2)                         # L349
            if empty == 0:
                return  # GOTO menu0
            # Split forces                                  L350-355
            g.supply[empty] = int(0.3 * g.supply[index])
            g.supply[index] -= g.supply[empty]
            if g.supply[index] < 0:
                g.supply[index] = 0
            g.armysize[empty] = int(0.3 * g.armysize[index])  # L351
            g.armysize[index] -= g.armysize[empty]
            g.armyloc[empty] = target                       # L352
            g.armyexper[empty] = g.armyexper[index]
            g.armymove[empty] = 0
            g.armylead[empty] = g.rating[empty]             # L353
            g.armyname[empty] = g.lname[empty]              # L354
            g.lname[empty] = ""
            g.armyexper[empty] = g.armyexper[index]         # L355

            s.color(11)                                     # L356
            clrbot(g)
            s.print_text(
                f"Unit #{empty} with {g.armysize[empty]}00 men "
                f"detached under {g.armyname[empty]}"
            )
            tick(g, g.turbo)
            if g.noise > 0:                                 # L356
                from cws_sound import qb_sound
                qb_sound(2222, 1)
            stax(g, g.side)                                 # L357
            g.choose = 27                                   # L358
            continue                                        # GOTO optmen

        elif g.choose == 7:                                 # Drill (L363)
            s.color(14)                                     # L364
            s.locate(4, 68)
            s.print_text("DRILL ARMY")
            index, target = movefrom(g)                     # L365
            if target < 1 or index < 1:                     # L366
                s.color(11)
                clrbot(g)
                s.print_text(
                    f"No armies remain eligible for drills in "
                    f"{g.month_names[g.month]}"
                )
                return  # GOTO menu0
            if (g.armyexper[index] > 5 or
                    g.armyexper[index] >= g.armylead[index]):  # L367
                s.color(12)
                clrbot(g)
                s.print_text(
                    f"{g.armyname[index]}: Army has reached "
                    f"maximum improvement through drilling"
                )
                continue  # GOTO optmen
            g.armyexper[index] += 1                         # L368
            clrbot(g)                                       # L369
            s.print_text(
                f"{g.armyname[index]} has drilled to reach "
                f"experience level {g.armyexper[index]}"
            )
            if g.noise > 0:                                 # L369
                from cws_sound import qb_sound
                qb_sound(2222, 1)
            tick(g, g.turbo)                                # L370
            clrbot(g)
            g.armymove[index] = -1                          # L371
            g.choose = 28                                   # L372
            continue                                        # GOTO optmen

        elif g.choose == 8:                                 # Relieve (L377)
            relieve(g, g.side)                              # L378
            g.choose = 29                                   # L379
            continue                                        # GOTO optmen

        else:                                               # CASE ELSE (L382)
            return  # GOTO menu0

        # L386: fallthrough → GOTO optmen
        g.choose = 21 + g.choose
        continue


# ═══════════════════════════════════════════════════════════════════════════
#  Utility submenu — utile: (L391-650)
# ═══════════════════════════════════════════════════════════════════════════

def _utility_menu(g: 'GameState') -> None:
    """Utility submenu loop (CASE 8)."""
    from cws_ui import menu, clrbot, clrrite, topbar
    from cws_util import tick
    from cws_map import usa
    from cws_data import filer, occupy
    from cws_flow import endit
    from cws_navy import integrity

    s = g.screen

    while True:                                             # utile:
        chosit = 29                                         # L392
        g.mtx[0] = "Utility"                               # L393
        if g.player == 3:                                    # Online: show but disable
            g.mtx[1] = "-"
            g.mtx[2] = "Online"
        elif g.player == 2:
            g.mtx[1] = "Side"                              # L394
            g.mtx[2] = "2 Player"                           # L395
        else:
            g.mtx[1] = "Side"                              # L394
            g.mtx[2] = "1 Player"
        g.mtx[3] = f"Graphics {g.graf}"                    # L396
        g.mtx[4] = "Noise"                                 # L397
        if g.noise > 0:
            g.mtx[4] += "*" * g.noise
        g.mtx[5] = f"Display {g.turbo}"                    # L398
        bal = g.difficult                                   # L399
        if g.side == UNION:
            bal = 6 - g.difficult
        g.mtx[6] = f"Balance {bal}"                        # L400
        g.mtx[7] = "End Cond"                              # L401
        evt_mark = "+"                                      # L402
        if g.randbal == 0:
            evt_mark = ""
        g.mtx[8] = f"Rndom Evt {evt_mark}"                 # L403
        g.mtx[9] = "Vary Start"                            # L404
        jan_mark = "+"  if g.jancam == 1 else ""            # L405
        g.mtx[10] = f"Jan Campgn{jan_mark}"                # L406
        real_mark = "+" if g.realism == 1 else ""           # L407
        g.mtx[11] = f"Realism {real_mark}"                 # L408
        g.mtx[12] = "Chk Links"                            # L409
        his_mark = "+" if g.history == 1 else ""            # L410
        g.mtx[13] = f"History{his_mark}"                   # L411
        g.size = 13                                         # L412
        g.tlx = 67
        g.tly = 11
        s.color(11)                                         # L413
        s.locate(g.tly - 2, g.tlx)
        s.print_text("esc=Main Menu")
        if g.player == 1:                                   # L414
            g.size = 14
            g.mtx[14] = f"Aggress {g.bold}"
        menu(g, -1)                                         # L415
        clrrite(g)

        # ── inner SELECT CASE ──                           L416

        if g.choose == 1:                                   # Swap Sides (L420)
            if g.player >= 2:                               # L421
                return  # GOTO menu0
            g.side = g.enemy_of()                            # L422
            s.color(g.side_color(g.side))
            clrbot(g)                                       # L423
            s.print_text(f"Now playing {g.force[g.side]} side")
            if g.noise > 0:
                from cws_sound import qb_sound
                qb_sound(999, 1)
            if g.side == UNION:                              # L424
                g.randbal = 7
            if g.side == CONFEDERATE:                        # L425
                g.randbal = 3
            topbar(g)                                       # L426
            return  # GOTO menu0

        elif g.choose == 2:                                 # Solo/2Player (L431)
            if g.player == 3:                               # Online: can't toggle
                return  # GOTO menu0
            g.player = 3 - g.player                         # L432
            clrbot(g)
            s.color(12)
            a_mode = "Solo"                                 # L434
            if g.player == 2:
                a_mode = "2 Player"
            s.print_text(f"{a_mode} Game")                  # L435
            if g.noise > 0:                                 # L433
                from cws_sound import qb_sound
                qb_sound(999, 1)
            g.choose = 23                                   # L436
            continue  # GOTO utile

        elif g.choose == 3:                                 # Graphics (L440)
            g.graf += 1                                     # L441
            if g.graf > 3:                                  # L442
                g.graf = 0
            labels = {0: "DISABLED", 1: "ROADS", 2: "CITY NAMES", 3: "FULL"}
            a_gfx = labels.get(g.graf, "ROADS")             # L443-446
            s.cls()                                         # L447
            usa(g)                                          # L448
            clrbot(g)                                       # L449
            s.color(11)
            s.print_text(f"Graphics : {a_gfx}")
            if g.noise > 0:                                 # L449
                from cws_sound import qb_sound
                qb_sound(2700, 1)
            g.choose = 24                                   # L450
            continue  # GOTO utile

        elif g.choose == 4:                                 # Sounds (L454)
            clrrite(g)                                      # L455
            g.choose = g.noise + 22
            g.mtx[0] = "SOUNDS"                             # L456
            g.mtx[1] = "Quiet"                              # L457
            g.mtx[2] = "Sound"                              # L458
            g.mtx[3] = " & Sound"                           # L459
            g.size = 3                                      # L460
            g.tlx = 67
            g.tly = 12
            menu(g, 0)                                      # L461
            clrrite(g)
            if g.choose < 1:                                # L462
                return  # GOTO menu0
            s.color(11)                                     # L463
            clrbot(g)
            s.print_text(f"Sound Option : {g.mtx[g.choose]}")
            g.noise = g.choose - 1                          # L464
            if g.noise > 0:                                 # L465
                from cws_sound import qb_sound
                qb_sound(999, 1)
            g.choose = 25                                   # L466
            continue  # GOTO utile

        elif g.choose == 5:                                 # Display Speed (L470)
            g.choose = int(g.turbo) + 21                    # L471
            g.mtx[0] = "Display"                            # L472
            g.mtx[1] = "Fast"                               # L473
            g.mtx[2] = "Normal"                             # L474
            g.mtx[3] = "Slow"                               # L475
            g.mtx[4] = "Very Slow"                          # L476
            g.mtx[5] = "Reg Color"                          # L477
            if g.bw > 0:
                g.mtx[5] = "Alt Color"
            g.tlx = 67                                      # L478
            g.tly = 15
            g.size = 5
            menu(g, 0)                                      # L479
            clrrite(g)
            if g.choose < 1:                                # L481
                pass
            elif g.choose < 5:                              # L482
                g.turbo = float(g.choose)                   # L483
                if g.turbo == 4:                             # L484
                    g.turbo = 8.0
                clrbot(g)                                   # L485
                s.color(11)
                s.print_text(f"Display Speed : {g.mtx[g.choose]}")
            elif g.choose == 5:                             # L487
                g.bw = 1 - g.bw                             # L488
                s.cls()                                     # L489
                usa(g)                                      # L490
                topbar(g)                                   # L491
            g.choose = 26                                   # L493
            continue  # GOTO utile

        elif g.choose == 6:                                 # Play Balance (L497)
            g.choose = g.difficult + 21                     # L498
            g.mtx[0] = "Balance"                            # L499
            g.mtx[1] = "Rebel ++"                           # L500
            g.mtx[2] = "Rebel +"                            # L501
            g.mtx[3] = "Balanced"                           # L502
            g.mtx[4] = "Union +"                            # L503
            g.mtx[5] = "Union ++"                           # L504
            g.tlx = 67                                      # L505
            g.tly = 15
            g.size = 5
            menu(g, 8)                                      # L506
            clrrite(g)
            if g.choose < 1:                                # L507
                return  # GOTO menu0
            clrbot(g)                                       # L508
            s.color(11)                                     # L509
            clrbot(g)
            s.print_text(f"Play Balance : {g.mtx[g.choose]}")
            g.difficult = g.choose                          # L510
            _unionplus(g)                                   # L511
            g.choose = 27                                   # L512
            continue  # GOTO utile

        elif g.choose == 7:                                 # End Cond (L516)
            endit(g)                                        # L517
            g.choose = 28                                   # L518
            continue  # GOTO utile

        elif g.choose == 8:                                 # Random Events (L522)
            g.mtx[0] = "Random Events"                     # L523
            g.size = 4                                      # L524
            g.tlx = 30
            g.tly = 8
            g.mtx[1] = "OFF"                               # L525
            g.mtx[2] = "Favor Union "                      # L526
            if g.randbal == 3:
                g.mtx[2] += " "
            g.mtx[3] = "Neutral     "                      # L527
            if g.randbal == 5:
                g.mtx[3] += " "
            g.mtx[4] = "Favor Rebels"                      # L528
            if g.randbal == 7:
                g.mtx[4] += " "
            g.colour = 5                                    # L529
            menu(g, 0)                                      # L530
            g.colour = 4                                    # L531

            t_str = ""
            if g.choose == 1:                               # L534
                g.randbal = 0
            elif g.choose == 2:                             # L536
                g.randbal = 3
            elif g.choose == 3:                             # L538
                g.randbal = 5
            elif g.choose == 4:                             # L540
                g.randbal = 7

            if 1 < g.choose < 5:                            # L544
                t_str = g.mtx[g.choose]

            clrbot(g)                                       # L545
            a_lbl = ""                                      # L546
            if g.randbal == 0:
                a_lbl = "OFF"
            s.color(11)                                     # L547
            s.print_text(f"Random Events : {a_lbl} {t_str}")
            s.color(14)                                     # L548
            s.print_text("            press a key")
            _wait_key(g)                                    # L549
            s.cls()                                         # L550
            usa(g)                                          # L551
            g.choose = 29                                   # L552
            continue  # GOTO utile

        elif g.choose == 9:                                 # Vary Start (L557)
            filer(g, 1)                                     # L558
            g.cash[1] = int(g.cash[1] - 100 + 200 * random.random())  # L559
            g.cash[2] = int(g.cash[2] + 100 + 200 * random.random())  # L560
            g.bold = int(5 * random.random())               # L561
            for k in range(1, 7):                           # L562
                if random.random() > 0.6:                   # L563
                    g.armyloc[k] = 0
                    g.armysize[k] = 0
                    g.armylead[k] = 0
                    g.armyexper[k] = 0
                    g.armymove[k] = 0
                    g.supply[k] = 0
            # L568: FOR k = 21 TO 6 — bug: never executes (STEP 1, 21>6)
            for k in range(1, 41):                          # L574
                occupy(g, k)
            g.navysize[1] = int(10 * random.random())      # L575
            if g.navysize[1] == 0:
                g.navyloc[1] = 0
            g.navysize[2] = int(10 * random.random())      # L576
            if g.navysize[2] > 0:
                g.navyloc[2] = 27
            for i in range(1, 3):                           # L577
                g.fleet[i] = ""                             # L578
                for j in range(1, g.navysize[i] + 1):      # L579
                    a_ch = "W"                              # L580
                    if random.random() > 0.45 * g.side:
                        a_ch = "I"
                    g.fleet[i] += a_ch                      # L581
            if random.random() > 0.7:                       # L584
                g.capcity[2] = 25
            for k in range(1, 41):                          # L586
                if random.random() > 0.8:                   # L587
                    g.rating[k] = int(g.rating[k] - 3 + 6 * random.random())
                    if g.rating[k] > 9:
                        g.rating[k] = 9
                if g.rating[k] < 1:                         # L588
                    g.rating[k] = 1
            s.cls()                                         # L590
            usa(g)                                          # L591
            g.choose = 30                                   # L592
            continue  # GOTO utile

        elif g.choose == 10:                                # Jan Campaigns (L596)
            g.jancam = 1 - g.jancam                         # L597
            a_lbl = "PROHIBITED"                            # L598
            if g.jancam == 1:
                a_lbl = "ALLOWED"
            s.color(11)                                     # L599
            clrbot(g)                                       # L600
            s.print_text(f"January Campaigns : {a_lbl}")    # L601
            g.choose = 31                                   # L602
            continue  # GOTO utile

        elif g.choose == 11:                                # Realism (L606)
            g.realism = 1 - g.realism                       # L607
            clrbot(g)                                       # L608
            s.color(11)
            if g.realism == 0:                              # L609
                s.print_text("Recruiting FIXED: 7000 for NEW Armies  4500 for Additions")
            else:                                           # L611
                s.print_text("REALISM ON: Recruiting based on CITY SIZE")
                if g.side == CONFEDERATE and g.randbal == 1 and g.randbal < 5:  # L613
                    g.randbal += 2
                _unionplus(g)                               # L614
            g.choose = 32                                   # L616
            continue  # GOTO utile

        elif g.choose == 12:                                # Chk Links (L620)
            integrity(g)                                    # L621
            tick(g, 99)                                     # L622
            usa(g)                                          # L623
            # falls through to CASE ELSE → return

        elif g.choose == 13:                                # History (L627)
            g.history = 1 - g.history                       # L628
            a_lbl = "OFF"                                   # L629
            if g.history == 1:
                a_lbl = "ON"
            clrbot(g)                                       # L630
            s.print_text(f"History is now {a_lbl}")
            g.choose = 34                                   # L631
            continue  # GOTO utile

        elif g.choose == 14:                                # Aggression (L635)
            g.bold += 1                                     # L636
            if g.bold > 5:
                g.bold = 0
            labels = {0: "PASSIVE", 1: "TIMID", 2: "CAUTIOUS",
                      3: "NORMAL", 4: "BOLD", 5: "RECKLESS"}
            a_lbl = labels.get(g.bold, "NORMAL")            # L637-644
            clrbot(g)                                       # L645
            s.color(11)                                     # L646
            s.print_text(f"Enemy Aggression : {a_lbl} ({g.bold})")
            g.choose = 35                                   # L648
            continue  # GOTO utile

        else:                                               # CASE ELSE (L649)
            return  # GOTO menu0


# ═══════════════════════════════════════════════════════════════════════════
#  Files submenu — filex: (L654-680)
# ═══════════════════════════════════════════════════════════════════════════

def _files_menu(g: 'GameState') -> str:
    """Files submenu. Returns 'menu0', 'newgame', or 'quit'."""
    from cws_ui import menu, clrrite
    from cws_data import filer

    s = g.screen

    # L655: IF NOT _FILEEXISTS("*.sav") THEN filel = 0
    # Check for saved game files in save directory
    try:
        has_sav = any(
            f.lower().endswith('.sav')
            for f in os.listdir(save_dir())
        )
        if not has_sav:
            g.filel = 0
    except OSError:
        g.filel = 0

    while True:                                             # filex:
        g.choose = 23                                       # L657
        chosit = 30
        if g.year == 1861:
            g.choose = 22
        g.mtx[0] = "Options"                               # L658
        g.mtx[1] = "Load"                                  # L659
        if g.filel == 0:
            g.mtx[1] = "-"
            g.choose = 23
        g.mtx[2] = "Save"                                  # L660
        g.mtx[3] = "New Game"                               # L661
        g.mtx[4] = "Quit"                                  # L662
        g.size = 4                                          # L663
        g.tlx = 67
        g.tly = 15
        menu(g, 0)                                          # L664
        clrrite(g)

        if g.choose < 1:                                    # L666
            return "menu0"

        elif g.choose in (1, 2):                            # L667: Load/Save
            if g.choose == 1 and g.filel == 0:              # L669
                continue  # GOTO filex
            filer(g, g.choose + 1)                          # L670
            if g.choose == 1:                               # L671
                g.rflag = 0
                g.mflag = 0
                g.nflag = 0
            return "menu0"                                  # L672

        elif g.choose == 3:                                 # New Game (L673)
            # Save config via WRITE #1                      L674-676
            try:
                from cws_data import _save_cfg
                _save_cfg(g, g.side)
            except OSError:
                pass
            s.cls()                                         # L677
            return "newgame"                                # L678

        elif g.choose == 4:                                 # Quit (L679)
            return "quit"

        else:
            return "menu0"


# ═══════════════════════════════════════════════════════════════════════════
#  Main menu — menu0: (L171-688)
# ═══════════════════════════════════════════════════════════════════════════

def _main_menu(g: 'GameState') -> str:
    """Main menu loop. Returns 'newmonth', 'newgame', or 'quit'."""
    from cws_ui import menu, clrbot, clrrite, topbar
    from cws_util import starfin, tick
    from cws_map import usa, icon
    from cws_recruit import recruit
    from cws_army import armies
    from cws_navy import navy
    from cws_railroad import railroad, traincapacity
    from cws_report import report

    s = g.screen
    chosit = 22

    while True:                                             # menu0:
        topbar(g)                                           # L172
        if g.player >= 2 and g.side == 0:                   # L173
            g.side = 1
        if g.cash[g.side] < 100 and g.navyloc[g.side] == 0:  # L174
            g.nflag = 1

        g.hilite = 11                                       # L176
        g.colour = 4                                        # L177
        g.tlx = 67                                          # L178
        g.tly = 13

        g.mtx[0] = "Main"                                  # L179
        g.mtx[1] = "Troops"                                # L180
        if g.rflag < 0 or g.cash[g.side] < 100:
            g.mtx[1] = "-"
            chosit = 23
        g.mtx[2] = "Moves"                                 # L181
        if g.mflag > 0:
            g.mtx[2] = "-"
            if chosit == 23:
                chosit = 24
        g.mtx[3] = "Ships"                                 # L182
        if g.nflag > 0:
            g.mtx[3] = "-"
            if chosit == 24:
                chosit = 25
        g.mtx[4] = "Railroad"                              # L183
        if g.rr[g.side] > 0:
            g.mtx[4] = "-"
            if chosit == 25:
                chosit = 26
        g.mtx[5] = "END TURN"                              # L184
        g.mtx[6] = "Inform"                                # L185
        g.mtx[7] = "COMMANDS"                               # L186
        g.mtx[8] = "UTILITY"                                # L187
        g.mtx[9] = "Files"                                  # L188

        g.size = 9                                          # L190
        g.choose = chosit                                   # L191
        menu(g, 0)                                          # L192
        clrrite(g)

        # ── SELECT CASE choose ──                          L196

        if g.choose == 1:                                   # Recruit (L197)
            if g.cash[g.side] < 100 or g.rflag < 0:        # L198
                g.rflag = -1
                continue  # GOTO menu0
            recruit(g, g.side)                              # L199
            chosit = 23                                     # L200
            continue  # GOTO menu0

        elif g.choose == 2:                                 # Armies (L203)
            armies(g)                                       # L204
            chosit = 23                                     # L205
            continue  # GOTO menu0

        elif g.choose == 3:                                 # Ships (L208)
            if g.nflag == 0:                                # L209
                navy(g, g.side, 0)
            chosit = 25                                     # L210
            # Falls through to GOTO menu0 (L688)

        elif g.choose == 4:                                 # Railroad (L211)
            if g.rr[g.side] == 0:                           # L212
                s.color(15)                                 # L213
                s.locate(4, 68)
                s.print_text("RAILROAD MOVE")
                # L214-218: simplified train icon
                z = g.side_color(g.side)                     # L216
                s.line(550, 17, 600, 30, z, "BF")
                s.line(550, 17, 600, 30, 0, "B")
                s.color(15 if g.side == CONFEDERATE else 11)  # L219
                limit = traincapacity(g, g.side)            # L220
                clrbot(g)                                   # L221
                s.print_text(f"Railroad capacity ={limit}00")
                railroad(g, g.side)                         # L222
            else:                                           # L223
                clrbot(g)                                   # L224
                s.color(11)
                ri = g.rr[g.side]
                dest = g.city[g.armymove[ri]] if g.armymove[ri] > 0 else "?"
                s.print_text(
                    f"Railroad is already carrying "
                    f"{g.armyname[ri]} to {dest}"
                )
                continue  # GOTO menu0

        elif g.choose == 5:                                 # End Turn (L227)
            g.tlx = 67                                      # L228
            g.tly = 15
            g.hilite = 15                                   # L229
            g.colour = 3
            g.choose = 23
            g.mtx[0] = "End Turn"                           # L230
            g.mtx[1] = "Yes"                                # L231
            g.mtx[2] = "NOT YET"                            # L232
            g.size = 2                                      # L233
            menu(g, 0)
            clrrite(g)
            if g.choose != 1:
                chosit = 24
                continue  # GOTO menu0

            # endrnd:                                       L234
            result = _end_round(g)
            if result == "menu0":
                continue
            if result == "online_wait":
                return "online_wait"
            return "newmonth"                               # L237

        elif g.choose == 6:                                 # Inform (L239)
            report(g, g.side)                               # L240
            chosit = 27
            star, fin = starfin(g, g.side)                  # L241
            for i in range(star, fin + 1):                  # L242
                if g.armymove[i] > 0:                       # L243
                    icon(g, g.armyloc[i], g.armymove[i], 1)

        elif g.choose == 7:                                 # Commands (L245)
            _commands_menu(g)

        elif g.choose == 8:                                 # Utility (L390)
            _utility_menu(g)

        elif g.choose == 9:                                 # Files (L654)
            result = _files_menu(g)
            if result == "newgame":
                return "newgame"
            elif result == "quit":
                if _rusure(g):
                    return "quit"
                continue  # menu0

        elif g.choose == 99:                                # L682: hidden F7
            result = _end_round(g)
            if result == "menu0":
                continue
            if result == "online_wait":
                return "online_wait"
            return "newmonth"

        else:                                               # CASE ELSE (L684)
            chosit = 22                                     # L685

        # L688: GOTO menu0 — loop continues


# ═══════════════════════════════════════════════════════════════════════════
#  Online event replay
# ═══════════════════════════════════════════════════════════════════════════

def _show_event_replay(g: 'GameState') -> None:
    """Replay captured events from opponent's turn with full map animations.

    Restores pre-turn state from snapshot, redraws the map, then processes
    each event with the same graphics functions (animate, cannon, flags,
    surrender, shipicon, flashcity, image2) that the live player sees.
    Plain string events scroll on the bottom bar.
    """
    import pygame
    from cws_map import image2, flashcity, showcity, icon, _upbox, usa
    from cws_ui import clrbot, clrrite, flags
    from cws_combat import cannon, surrender as surrender_gfx
    from cws_navy import shipicon
    from cws_util import animate, tick
    from cws_army import placearmy
    from cws_data import occupy

    if not g.event_log:
        return

    s = g.screen
    raw_events = list(g.event_log)
    g.event_log = []

    # ── Parse event log: extract month header, snapshot, and events ──
    month_label = ""
    snapshot = None
    events = []
    for evt in raw_events:
        if isinstance(evt, str) and evt.startswith("__month__:"):
            month_label = evt[len("__month__:"):]
        elif isinstance(evt, dict) and evt.get("type") == "__snapshot__":
            snapshot = evt
        else:
            events.append(evt)

    if not events:
        return

    # ── Save post-turn state and restore pre-turn state from snapshot ──
    _SNAP_KEYS = [
        "armyloc", "armymove", "armysize", "armyname", "armylead",
        "armyexper", "supply", "occupied", "fort", "cityp",
        "navyloc", "navysize", "fleet", "victory", "capcity",
    ]
    post_state = {}
    if snapshot:
        # Save post-turn state (downloaded from server)
        for key in _SNAP_KEYS:
            post_state[key] = list(getattr(g, key))
        post_state["commerce"] = g.commerce
        post_state["raider"] = g.raider

        # Restore pre-turn state from snapshot
        for key in _SNAP_KEYS:
            src = snapshot[key]
            dest = getattr(g, key)
            for i in range(min(len(dest), len(src))):
                dest[i] = src[i]
        g.commerce = snapshot["commerce"]
        g.raider = snapshot["raider"]

        # Redraw map with pre-turn positions
        s.cls()
        usa(g)

    # ── Phase 1: "Update for Month, Year" header ──
    s.color(14)
    s.locate(1, 1)
    s.print_text(" " * 80)
    s.locate(1, 20)
    if month_label:
        s.print_text(f"Update for {month_label}")
    else:
        s.print_text("Monthly Events")
    clrbot(g)
    s.print_text(f"press any key for {month_label} events" if month_label
                 else "press any key for events")
    s.update()
    _wait_key(g)

    # Draw movement lines for all pending moves (like tupdate L122-125)
    if snapshot:
        for i in range(1, 41):
            if g.armyloc[i] > 0 and g.armymove[i] > 0:
                icon(g, g.armyloc[i], g.armymove[i], 1)

    _upbox(g)
    s.update()

    # ── Phase 2: replay each event with full animation ──
    for evt in events:

        # ── Plain string events (misc messages) ──
        if isinstance(evt, str):
            clrbot(g)
            s.color(11)
            s.print_text(evt[:79])
            s.update()
            _timed_pause(640)
            continue

        etype = evt.get("type", "")

        # ──────────── Army Movement ────────────
        if etype == "move":
            army_id = evt["army_id"]
            from_city = evt["from"]
            to_city = evt["to"]
            clrbot(g)
            s.color(11)
            s.print_text(evt["msg"][:79])
            # Set state for animation
            g.armyloc[army_id] = from_city
            g.armymove[army_id] = to_city
            if g.supply[army_id] > 0:
                g.supply[army_id] -= 1
            # Animate: draw army, erase movement line, smooth movement
            placearmy(g, army_id)
            icon(g, from_city, to_city, 5)    # erase movement line
            animate(g, army_id, 0)            # smooth forward animation
            s.update()

        # ──────────── Out of Supply ────────────
        elif etype == "no_supply":
            clrbot(g)
            s.color(11)
            s.print_text(evt["msg"][:79])
            s.update()
            tick(g, g.turbo)

        # ──────────── Friendly Meeting ────────────
        elif etype == "meeting":
            target = evt["city"]
            clrbot(g)
            s.color(11)
            s.print_text(evt["msg"][:79])
            tick(g, g.turbo)
            icon(g, target, 0, 6)    # meeting flash
            clrbot(g)
            s.update()

        # ──────────── Attack (explosion at city) ────────────
        elif etype == "attack":
            target = evt["city"]
            icon(g, target, 0, 3)    # battle explosion
            clrbot(g)
            s.color(11)
            s.print_text(evt["msg"][:79])
            s.update()
            _timed_pause(max(0, int(250 * (g.turbo - 1))))

        # ──────────── Battle ────────────
        elif etype == "battle":
            y = 68
            clrrite(g)
            # Attacker stats
            s.color(11)
            s.locate(1, y)
            s.print_text("Attacker")
            c = 9 if evt["atk_id"] <= 20 else 7
            s.color(c)
            s.locate(2, y)
            s.print_text(evt["atk_name"])
            s.locate(3, y)
            s.print_text(f"{evt['atk_size']}00")
            s.color(11)
            s.locate(11, y)
            s.print_text(f"Attack  {evt['atk_power']}")
            s.line(530, 155, 635, 175, 11, "B")

            # Defender stats
            s.locate(13, y)
            s.print_text("Defender")
            s.color(16 - c)
            s.locate(14, y)
            s.print_text(evt["def_name"])
            s.locate(15, y)
            s.print_text(f"{evt['def_size']}00")
            s.color(11)
            s.locate(25, y)
            s.print_text(f"Defend  {evt['def_power']}")
            s.line(530, 380, 635, 400, 11, "B")

            # Odds
            s.color(14)
            s.locate(27, y)
            s.print_text(f"Odds:  {evt['odds']}%")
            s.line(530, 412, 635, 435, 14, "B")
            s.line(528, 410, 637, 437, 14, "B")
            s.update()
            _wait_key(g)

            # Cannon explosion animation
            if g.graf > 2:
                cannon(g)
                k = evt.get("fort", 0)
                fort_surfs = getattr(g, 'fort_surfaces', {})
                if k in fort_surfs:
                    s.put_image(550, 270, fort_surfs[k])

            # Victory flag
            ws = evt["winner_side"]
            flags(g, ws, 0, 0)
            side_str = "UNION" if ws == 1 else "REBEL"
            s.color(14)
            s.locate(3, 68)
            s.print_text(f"{side_str} VICTORY")
            s.locate(4, 71)
            s.print_text("in")
            s.locate(5, 69)
            s.print_text(evt["city"])

            clrbot(g)
            s.color(11)
            s.print_text(evt["msg"])
            s.update()
            _timed_pause(1500)

            # Casualty line
            s.color(c)
            s.locate(1, 1)
            s.print_text(
                f"Attack Loss: {evt['atk_loss']}00/{evt['atk_size']}00 ({evt['atk_pct']}%) |"
            )
            s.color(16 - c)
            s.print_text(
                f"| Defend Loss: {evt['def_loss']}00/{evt['def_size']}00 ({evt['def_pct']}%)"
            )
            s.update()
            _wait_key(g)
            clrrite(g)

            # Apply casualties to replay state
            atk_id = evt["atk_id"]
            def_id = evt["def_id"]
            g.armysize[atk_id] = max(1, g.armysize[atk_id] - evt["atk_loss"])
            g.armysize[def_id] = max(1, g.armysize[def_id] - evt["def_loss"])
            if evt["winner"] == "attacker":
                if g.armyexper[atk_id] < 10:
                    g.armyexper[atk_id] += 1
            else:
                if g.armyexper[def_id] < 10:
                    g.armyexper[def_id] += 1
            if g.graf > 0:
                _upbox(g)

        # ──────────── Attacker Withdraw ────────────
        elif etype == "withdraw":
            army_id = evt["army_id"]
            from_city = evt["from"]     # battle city
            to_city = evt["to"]         # retreat destination
            clrbot(g)
            s.color(11)
            s.print_text(evt["msg"][:79])
            # Animate backward from battle city to retreat destination
            g.armyloc[army_id] = from_city
            g.armymove[army_id] = to_city
            placearmy(g, army_id)
            animate(g, army_id, 1)      # backward animation
            g.armyloc[army_id] = to_city
            g.armymove[army_id] = -2
            g.occupied[to_city] = army_id
            placearmy(g, army_id)
            s.update()
            _timed_pause(800)

        # ──────────── Defender Retreat ────────────
        elif etype == "retreat":
            army_id = evt["army_id"]
            from_city = evt["from"]     # battle city
            to_city = evt["to"]         # retreat destination
            clrbot(g)
            s.color(11)
            s.print_text(evt["msg"][:79])
            g.armyloc[army_id] = from_city
            g.armymove[army_id] = to_city
            placearmy(g, army_id)
            animate(g, army_id, 0)      # forward to retreat city
            g.armyloc[army_id] = to_city
            g.occupied[to_city] = army_id
            placearmy(g, army_id)
            icon(g, from_city, 0, 6)    # flash at battle city
            g.armymove[army_id] = -2
            s.update()

        # ──────────── Arrive (move into city) ────────────
        elif etype == "arrive":
            army_id = evt["army_id"]
            target = evt["city"]
            g.armyloc[army_id] = target
            g.armymove[army_id] = -2
            occupy(g, target)
            placearmy(g, army_id)
            s.update()

        # ──────────── Surrender / Crushed ────────────
        elif etype == "surrender":
            aid = evt.get("army_id", 0)
            if g.graf > 2 and aid > 0:
                surrender_gfx(g, aid)
                s.color(14)
                s.locate(3, 68)
                s.print_text(evt.get("army_name", ""))
                s.locate(4, 68)
                s.print_text("surrenders !")
            clrbot(g)
            s.color(11)
            s.print_text(evt["msg"][:79])
            s.update()
            _wait_key(g)
            clrrite(g)
            # Clear army from replay state
            if aid > 0:
                if g.armymove[aid] > 0:
                    icon(g, g.armyloc[aid], g.armymove[aid], 4)
                g.armyloc[aid] = 0
                g.armysize[aid] = 0
                g.armyname[aid] = ""
                g.armylead[aid] = 0
                g.armyexper[aid] = 0
                g.armymove[aid] = 0
                g.supply[aid] = 0

        # ──────────── City Capture ────────────
        elif etype == "capture":
            cid = evt.get("city_id", 0)
            side = evt.get("side", 1)
            if cid > 0:
                g.cityp[cid] = side
                showcity(g)
                flashcity(g, cid)
            clrbot(g)
            s.color(11)
            s.print_text(evt["msg"][:79])
            s.update()
            _timed_pause(1200)

        # ──────────── Commerce Raid ────────────
        elif etype == "raid":
            clrbot(g)
            s.color(15)
            s.print_text(evt["msg"][:79])
            if evt.get("success"):
                s.pset(500, 465, 0)
                shipicon(g, evt.get("side", 1), evt.get("ship_type", 1))
                s.update()
                _wait_key(g)
            else:
                s.update()
                _timed_pause(1200)

        # ──────────── Fleet Destroyed ────────────
        elif etype == "fleet_destroyed":
            clrbot(g)
            s.color(15)
            s.print_text(evt["msg"][:79])
            s.line(447, 291, 525, 335, 1, "BF")
            for k in range(1, 6):
                s.circle(480, 315, 4 * k, 11)
            s.update()
            _timed_pause(1500)
            s.line(447, 291, 525, 335, 1, "BF")

        # ──────────── Popup ────────────
        elif etype == "popup":
            image2(g, evt["msg"], evt.get("color", 4))

        # ──────────── Naval ────────────
        elif etype == "naval":
            image2(g, evt["msg"], 4)

        # ──────────── Unknown dict ────────────
        else:
            msg = evt.get("msg", str(evt))
            clrbot(g)
            s.color(11)
            s.print_text(msg[:79])
            s.update()
            _timed_pause(640)

    # ── Restore post-turn state and redraw final map ──
    if post_state:
        for key in _SNAP_KEYS:
            src = post_state[key]
            dest = getattr(g, key)
            for i in range(min(len(dest), len(src))):
                dest[i] = src[i]
        g.commerce = post_state["commerce"]
        g.raider = post_state["raider"]

    s.cls()
    usa(g)
    clrbot(g)
    s.update()


def _timed_pause(ms: int) -> None:
    """Pause for *ms* milliseconds; any keypress ends the pause early."""
    import pygame
    elapsed = 0
    while elapsed < ms:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                raise SystemExit
            if ev.type == pygame.KEYDOWN:
                return
        pygame.time.wait(16)
        elapsed += 16


# ═══════════════════════════════════════════════════════════════════════════
#  Online multiplayer helpers
# ═══════════════════════════════════════════════════════════════════════════

def _newgame_submenu(g: 'GameState') -> str:
    """NEW GAME sub-menu: Solo / Local 2P / Online.
    Returns 'solo', 'local2p', or 'online'."""
    from cws_ui import menu

    g.mtx[0] = "NEW GAME"
    g.mtx[1] = "Solo (vs AI)"
    g.mtx[2] = "Local 2-Player"
    g.mtx[3] = "Online"
    g.tlx = 33
    g.tly = 20
    g.colour = 5
    g.size = 3
    g.choose = 22
    menu(g, 0)

    if g.choose == 2:
        return "local2p"
    if g.choose == 3:
        return "online"
    return "solo"


def _text_input(g: 'GameState', prompt: str, default: str = "") -> str:
    """Simple text input overlay. Returns typed text or default."""
    import pygame
    s = g.screen
    text = ""

    # Draw prompt
    s.line(100, 200, 540, 270, 1, "BF")
    s.line(100, 200, 540, 270, 15, "B")
    s.color(14)
    s.locate(14, 16)
    s.print_text(prompt)
    s.color(15)
    s.locate(15, 16)
    if default:
        s.print_text(f"[{default}] _")
    else:
        s.print_text("_")
    s.update()

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                raise SystemExit
            if event.type == pygame.VIDEORESIZE:
                s.update()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    return text if text else default
                elif event.key == pygame.K_ESCAPE:
                    return ""
                elif event.key == pygame.K_BACKSPACE:
                    if text:
                        text = text[:-1]
                        s.locate(15, 16)
                        s.print_text(text + "_" + "  ")
                        s.update()
                elif event.unicode and len(event.unicode) == 1:
                    if len(text) < 40:
                        text += event.unicode
                        s.locate(15, 16)
                        s.print_text(text + "_")
                        s.update()
        pygame.time.wait(16)


def _online_setup(g: 'GameState') -> str:
    """Online setup flow: Create or Join.
    Returns 'create_ok', 'join_ok', or 'cancel'."""
    from cws_ui import menu
    from cws_online import OnlineClient, save_session

    s = g.screen

    # Create / Join menu
    g.mtx[0] = "ONLINE"
    g.mtx[1] = "Create Game"
    g.mtx[2] = "Join Game"
    g.tlx = 33
    g.tly = 20
    g.colour = 5
    g.size = 2
    g.choose = 22
    menu(g, 0)

    if g.choose < 1:
        return "cancel"

    if g.choose == 1:
        # ── Create Game ──
        server = _text_input(g, "Server address?", "localhost:1861")
        if not server:
            return "cancel"
        if not server.startswith("http"):
            if "localhost" in server or "127.0.0.1" in server:
                server = "http://" + server
            else:
                server = "https://" + server

        # Side selection
        g.mtx[0] = "Play as"
        g.mtx[1] = "Union"
        g.mtx[2] = "Rebel"
        g.tlx = 33
        g.tly = 20
        g.colour = 5
        g.size = 2
        g.choose = 22
        menu(g, 0)
        if g.choose < 1:
            return "cancel"
        chosen_side = g.choose  # Menu: 1=Union, 2=Rebel — matches convention directly

        client = OnlineClient(server)
        try:
            result = client.create_game(side=chosen_side)
        except ConnectionError as e:
            s.color(12)
            s.locate(29, 1)
            s.print_text(f"Connection failed: {e}"[:79])
            s.update()
            _wait_key(g)
            return "cancel"

        code = result["game_code"]
        g.online_client = client
        g.my_side = chosen_side
        assert g.my_side in (UNION, CONFEDERATE), f"Invalid my_side: {g.my_side}"
        g.player = 3
        g.side = 1  # Union (side 1) always plays first

        save_session(server, code, client.token, chosen_side)

        # Show waiting screen with game code
        s.cls()
        s.line(150, 150, 490, 310, 1, "BF")
        s.line(150, 150, 490, 310, 15, "B")
        s.color(14)
        s.locate(11, 27)
        s.print_text(f"Game Code: {code}")
        s.color(11)
        s.locate(13, 25)
        s.print_text("Share this code with")
        s.locate(14, 25)
        s.print_text("your opponent!")
        s.color(7)
        s.locate(16, 25)
        s.print_text("Waiting for player 2")
        s.locate(17, 25)
        s.print_text("to join ...")
        s.color(8)
        s.locate(19, 25)
        s.print_text("ESC = cancel")
        s.update()

        # Poll until opponent joins
        import pygame
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    raise SystemExit
                if event.type == pygame.VIDEORESIZE:
                    s.update()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        return "cancel"
            try:
                status = client.game_status()
                if status["status"] == "active":
                    return "create_ok"
            except ConnectionError:
                pass
            pygame.time.wait(4000)

    else:
        # ── Join Game ──
        server = _text_input(g, "Server address?", "localhost:1861")
        if not server:
            return "cancel"
        if not server.startswith("http"):
            if "localhost" in server or "127.0.0.1" in server:
                server = "http://" + server
            else:
                server = "https://" + server

        code = _text_input(g, "Game code?")
        if not code:
            return "cancel"
        code = code.upper().strip()

        client = OnlineClient(server)
        try:
            result = client.join_game(code)
        except ConnectionError as e:
            s.color(12)
            s.locate(29, 1)
            s.print_text(f"Failed to join: {e}"[:79])
            s.update()
            _wait_key(g)
            return "cancel"

        g.online_client = client
        g.my_side = result["side"]
        assert g.my_side in (UNION, CONFEDERATE), f"Invalid my_side: {g.my_side}"
        g.player = 3
        g.side = 1  # Union (side 1) always plays first

        save_session(server, code, client.token, result["side"])
        return "join_ok"


def _online_upload(g: 'GameState') -> bool:
    """Serialize game state and upload to server. Returns True on success."""
    from cws_online import state_to_json

    client = g.online_client
    if not client:
        return False

    try:
        status = client.game_status()
        turn_number = status["turn_number"]
    except ConnectionError:
        g.screen.color(12)
        g.screen.locate(29, 1)
        g.screen.print_text("Connection error getting turn number")
        g.screen.update()
        _wait_key(g)
        return False

    state = state_to_json(g)
    try:
        client.submit_turn(turn_number, state)
        return True
    except ConnectionError as e:
        g.screen.color(12)
        g.screen.locate(29, 1)
        g.screen.print_text(f"Upload failed: {e}"[:79])
        g.screen.update()
        _wait_key(g)
        return False


def _online_wait(g: 'GameState') -> str:
    """Polling loop: wait for opponent's turn.
    Returns 'ready' when opponent has played, 'disconnect' on ESC,
    or 'finished' if game ended."""
    import pygame
    import time
    from cws_online import state_from_json, save_session
    from cws_map import usa

    s = g.screen
    client = g.online_client
    if not client:
        return "disconnect"

    # Draw waiting screen
    other_side = 3 - g.my_side
    start_time = time.time()
    events_shown = False  # True once we've shown the events transition

    while True:
        if not events_shown:
            box_c = 1 if other_side == 1 else 7
            s.line(150, 150, 490, 310, box_c, "BF")
            s.line(150, 150, 490, 310, 15, "B")
            c = 9 if other_side == 1 else 7
            s.color(c)
            s.locate(11, 23)
            s.print_text(f"{g.force[other_side]} Player Turn")
            s.color(14)
            s.locate(13, 27)
            s.print_text("- Waiting -")
            s.color(7)
            s.locate(16, 23)
            s.print_text("View map while waiting")
            s.color(8)
            s.locate(18, 23)
            s.print_text("ESC = disconnect")
        else:
            # Events in progress overlay
            s.line(150, 150, 490, 310, 5, "BF")
            s.line(150, 150, 490, 310, 13, "B")
            s.color(15)
            s.locate(12, 23)
            s.print_text("Events in progress...")
            s.color(8)
            s.locate(16, 23)
            s.print_text("ESC = disconnect")
        s.update()

        # Poll loop with event handling
        wait_ticks = 0
        last_elapsed = -1
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    raise SystemExit
                if event.type == pygame.VIDEORESIZE:
                    s.update()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        return "disconnect"
                    if event.key == pygame.K_F3:
                        # Let player redraw map
                        s.cls()
                        usa(g)
                        break  # redraw waiting overlay
                    if event.key == pygame.K_F8:
                        from cws_report import report
                        report(g, -1)
                        break  # redraw waiting overlay

            # Update elapsed timer display
            if not events_shown:
                elapsed = int(time.time() - start_time)
                if elapsed != last_elapsed:
                    last_elapsed = elapsed
                    mins, secs = divmod(elapsed, 60)
                    s.locate(14, 27)
                    s.color(8)
                    s.print_text(f"  {mins}m {secs:02d}s  ")
                    s.update()

            wait_ticks += 16
            if wait_ticks >= 4000:
                # Poll server
                try:
                    result = client.poll_turn()
                    if result["ready"]:
                        state_data = result["state"]
                        if state_data:
                            state_from_json(g, state_data)
                        if g.event_log:
                            _show_event_replay(g)
                        return "ready"

                    # Not ready yet — check if events phase started
                    if not events_shown and result.get("phase") == "events":
                        events_shown = True
                        phase_label = result.get("phase_label", "")
                        # Show transition screen (magenta box, like local 2P)
                        s.cls()
                        usa(g)
                        s.line(100, 160, 500, 320, 5, "BF")
                        s.line(100, 160, 500, 320, 13, "B")
                        s.color(15)
                        s.locate(13, 22)
                        if phase_label:
                            s.print_text(f"EVENTS FOR {phase_label}")
                        else:
                            s.print_text("MONTHLY EVENTS")
                        s.color(14)
                        s.locate(16, 23)
                        s.print_text("press any key when ready")
                        s.update()
                        _wait_key(g)
                        break  # redraw overlay (now shows "Events in progress...")
                except ConnectionError:
                    pass  # retry next cycle
                wait_ticks = 0

            pygame.time.wait(16)


def _online_resume(g: 'GameState') -> str:
    """Reconnect from saved session file.
    Returns 'ready', 'waiting', 'finished', or 'error'."""
    from cws_online import (load_session, clear_session, OnlineClient,
                            state_from_json, list_sessions)
    from cws_ui import menu

    sessions = list_sessions()
    if not sessions:
        return "error"

    if len(sessions) == 1:
        session = sessions[0]
    else:
        # Let the player pick which game to resume
        g.mtx[0] = "Resume Online"
        for i, sess in enumerate(sessions[:9], 1):
            side_name = g.force[sess["my_side"]] if 1 <= sess["my_side"] <= 2 else "?"
            g.mtx[i] = f"{sess['game_code']} ({side_name})"
        g.size = min(len(sessions), 9)
        g.tlx = 33
        g.tly = 18
        g.colour = 5
        g.choose = 22
        menu(g, 0)
        if g.choose < 1:
            return "error"
        session = sessions[g.choose - 1]

    client = OnlineClient(
        session["server_url"],
        token=session["token"],
        game_code=session["game_code"],
    )
    g.online_client = client
    g.my_side = session["my_side"]
    g.player = 3

    try:
        status = client.game_status()
    except ConnectionError as e:
        g.screen.color(12)
        g.screen.locate(29, 1)
        g.screen.print_text(f"Cannot reach server: {e}"[:79])
        g.screen.update()
        _wait_key(g)
        return "error"

    if status["status"] == "finished":
        clear_session(client.game_code)
        return "finished"

    if status["status"] == "waiting":
        # Game still waiting for second player
        g.screen.color(14)
        g.screen.locate(29, 1)
        g.screen.print_text("Waiting for opponent to join...")
        g.screen.update()
        return "waiting"

    # Active game — check if it's our turn
    if status["current_side"] == g.my_side:
        # Our turn — download latest state
        try:
            result = client.poll_turn()
            if result["ready"] and result["state"]:
                state_from_json(g, result["state"])
            if g.event_log:
                _show_event_replay(g)
            return "ready"
        except ConnectionError:
            return "error"
    else:
        return "waiting"


# ═══════════════════════════════════════════════════════════════════════════
#  Top-level game loop
# ═══════════════════════════════════════════════════════════════════════════

def game_loop(g: 'GameState') -> None:
    """Main entry point: runs the full game."""
    from cws_map import usa
    from cws_online import save_session, clear_session

    replay = 0

    while True:
        # ── newgame: ──
        _newgame_init(g, replay)
        replay = 1                                          # L109

        # ── Title menu ──
        choice = _title_menu(g)
        if choice == "quit":
            return

        if choice == "online_resume":
            # Resume an existing online game
            resume_result = _online_resume(g)
            if resume_result == "error" or resume_result == "finished":
                continue  # restart outer loop (back to title)
            if resume_result == "waiting":
                # Enter waiting loop
                _start_new_game(g)
                wait_result = _online_wait(g)
                if wait_result == "disconnect":
                    continue
                # ready: state loaded, fall through to main game loop
            # resume_result == "ready": state already loaded

        elif choice == "resume":
            g.choose = 1
            if g.filel == 0:                                # L669: no save files
                pass  # skip load, fall through to main menu
            else:
                _loader(g)
                if g.player == 2:
                    from cws_ui import menu as _menu
                    from cws_map import usa as _usa
                    g.mtx[0] = "Your Side"
                    g.mtx[1] = "Union"
                    g.mtx[2] = "Confederate"
                    g.tlx = 33
                    g.tly = 20
                    g.colour = 5
                    g.size = 2
                    g.choose = 22
                    _menu(g, 0)
                    g.side = 2 if g.choose == 2 else 1
                    _blanken(g)
                    _usa(g)

        elif choice == "new":
            # Sub-menu: Solo / Local 2P / Online
            sub = _newgame_submenu(g)
            if sub == "solo":
                g.player = 1
                _start_new_game(g)
            elif sub == "local2p":
                g.player = 2
                g.side = 1
                _start_new_game(g)
            elif sub == "online":
                online_result = _online_setup(g)
                if online_result == "cancel":
                    continue  # restart outer loop (back to title)
                elif online_result in ("create_ok", "join_ok"):
                    _start_new_game(g)
                    # Union (side 1) always goes first; if we're Rebel, wait
                    if g.my_side != 1:
                        wait_result = _online_wait(g)
                        if wait_result == "disconnect":
                            continue
                        # State downloaded, proceed to main game loop

        # ── Main game loop: menu0 ↔ newmonth ↔ online_wait ──
        while True:
            result = _main_menu(g)
            if result == "quit":
                return
            if result == "newgame":
                break  # restart outer loop

            if result == "online_wait":
                # Online: upload turn, then wait for opponent
                _gc = g.online_client.game_code if g.online_client else ""
                if g.my_side == CONFEDERATE:
                    # Rebel (my_side=2): signal events, run monthly processing
                    month_label = f"{g.month_names[g.month]} {g.year}"
                    try:
                        g.online_client.signal_phase("events", month_label)
                    except ConnectionError:
                        pass  # non-critical, proceed anyway
                    restarted = _newmonth(g)
                    if restarted:
                        clear_session(_gc)
                        break  # restart outer loop
                    # After newmonth, it's Union's turn (side 1)
                    g.side = 1
                else:
                    # Union (my_side=1): just upload, Rebel's turn next (side 2)
                    g.side = 2

                _online_upload(g)

                wait_result = _online_wait(g)
                if wait_result == "disconnect":
                    break  # back to title
                if wait_result == "finished":
                    clear_session(_gc)
                    break
                # ready: state downloaded, loop back to _main_menu
                continue

            # result == "newmonth"
            restarted = _newmonth(g)
            if restarted:                                   # pcode > 0
                if g.player == 3 and g.online_client:
                    clear_session(g.online_client.game_code)
                break  # restart outer loop
            # else: loop back to _main_menu
