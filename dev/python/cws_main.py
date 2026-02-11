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

if TYPE_CHECKING:
    from cws_globals import GameState


# ═══════════════════════════════════════════════════════════════════════════
#  GOSUB helpers
# ═══════════════════════════════════════════════════════════════════════════

def _unionplus(g: 'GameState') -> None:
    """GOSUB unionplus (L707-709): calculate Union advantage."""
    g.usadv = 120 * g.difficult                             # L707
    if g.player == 2:
        g.usadv = 50 * g.difficult
    if g.realism > 0:                                       # L708
        g.usadv = int(g.usadv * 0.7)


def _blanken(g: 'GameState') -> None:
    """GOSUB blanken (L711-717): 2-player turn transition screen."""
    s = g.screen
    c = 1                                                   # L711
    if g.side == 2:
        c = 7
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


def _wait_key(g: 'GameState') -> None:
    """DO WHILE INKEY$="": LOOP"""
    import pygame
    g.screen.update()
    while True:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                return
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
    if g.player < 1 or g.player > 2:                        # L43
        g.player = 1
    if g.player == 2 or g.side == 0:                        # L44
        g.side = 1
    if g.side == 1:                                         # L45
        g.randbal = 7
    if g.side == 2:                                         # L46
        g.randbal = 3
    if g.turbo < 1:                                         # L47
        g.turbo = 2.0
    if g.side == 1 and g.difficult < 3:                     # L48
        g.cash[2] += 600 - 100 * g.difficult
    if g.side == 2 and g.difficult > 3:                     # L49
        g.cash[1] += 100 * g.difficult

    for i in range(1, 3):                                   # L52
        g.income[i] = g.cash[i]
        g.cash[i] = int(g.cash[i] + 50 * random.random())
    g.choose = 0                                            # L53

    # L57-62: cwsicon.vga / Ncap — loaded by load_all_sprites() above

    # Title screen                                          L63-88
    s.cls()                                                 # L63
    s.color(11)                                             # L64
    s.locate(14, 27)
    s.print_text("VGA CIVIL WAR STRATEGY GAME")
    s.color(4)                                              # L65
    s.locate(15, 32)
    s.print_text("Registered Edition")
    s.color(14)                                             # L66
    s.locate(28, 1)
    s.print_text("    (c) 1998, 2017, 2018, 2024 by W. R. Hutsell and Dave Mackey")
    s.locate(28, 60)                                        # L67
    s.print_text("v1.61")
    s.line(190, 170, 440, 260, 1, "B")                     # L68
    s.line(180, 180, 450, 250, 7, "B")                     # L69
    flags(g, 1, -440, 0)                                    # L70
    flags(g, 2, -100, 0)

    # L71-88: title music
    s.update()
    if replay == 0 and g.noise == 2 and g.choose == 0:     # L71
        from cws_sound import qb_play_interruptible, shen
        if g.side == 1:                                     # L72: Union
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
    """Show title menu. Returns 'resume', 'new', or 'quit'."""
    from cws_ui import menu

    if g.player == 2:                                       # L110
        _blanken(g)

    g.mtx[0] = "CIVIL WAR STRATEGY"                        # L111
    g.mtx[1] = "Resume Saved Game"                          # L112
    g.mtx[2] = "Start NEW Game"                             # L113
    g.mtx[3] = "Quit"                                      # L114
    g.tlx = 33                                              # L115
    g.tly = 20
    g.colour = 5
    g.size = 3
    g.choose = 23                                           # L116
    menu(g, 0)                                              # L117

    if g.choose == 1:                                       # L118
        return "resume"
    if g.choose == 3:                                       # L123
        return "quit"
    return "new"


def _start_new_game(g: 'GameState') -> None:
    """Start new game: init history if enabled, draw map (L124-133)."""
    from cws_map import usa

    s = g.screen
    if g.history == 1:                                      # L124
        s.cls()                                             # L125
        try:
            from cws_data import _data_path
            his_path = _data_path("cws.his")
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

    if g.player == 1 and g.side == 2:                       # L148
        g.income[1] += g.usadv

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
    if g.player == 2:                                       # L162
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
    """End round: reset flags. Returns 'newmonth' or 'menu0'."""
    from cws_map import usa

    g.rflag = 0                                             # L235
    g.mflag = 0
    g.nflag = 0

    if g.player == 2:                                       # L236
        g.side += 1
        if g.side == 2:
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
        if g.side == 1:
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
            g.victory[3 - g.side] += 50                     # L330
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
            if g.side == 1:                                 # L345
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
        g.mtx[1] = "Side"                                  # L394
        # L394 bug: IF player=2 THEN mtx$(2)="" — immediately overwritten
        if g.player == 2:
            g.mtx[2] = "2 Player"                           # L395
        else:
            g.mtx[2] = "1 Player"
        g.mtx[3] = f"Graphics {g.graf}"                    # L396
        g.mtx[4] = "Noise"                                 # L397
        if g.noise > 0:
            g.mtx[4] += "*" * g.noise
        g.mtx[5] = f"Display {g.turbo}"                    # L398
        bal = g.difficult                                   # L399
        if g.side == 1:
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
            if g.player == 2:                               # L421
                return  # GOTO menu0
            g.side = 3 - g.side                             # L422
            s.color(9 if g.side == 1 else 7)
            clrbot(g)                                       # L423
            s.print_text(f"Now playing {g.force[g.side]} side")
            if g.noise > 0:
                from cws_sound import qb_sound
                qb_sound(999, 1)
            if g.side == 1:                                 # L424
                g.randbal = 7
            if g.side == 2:                                 # L425
                g.randbal = 3
            topbar(g)                                       # L426
            return  # GOTO menu0

        elif g.choose == 2:                                 # Solo/2Player (L431)
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
                if g.side == 2 and g.randbal == 1 and g.randbal < 5:  # L613
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
    # Check for saved game files in data directory
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
    try:
        has_sav = any(
            f.lower().endswith('.sav')
            for f in os.listdir(data_dir)
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
        if g.player == 2 and g.side == 0:                   # L173
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
                z = 9                                       # L216
                if g.side == 2:
                    z = 7
                s.line(550, 17, 600, 30, z, "BF")
                s.line(550, 17, 600, 30, 0, "B")
                s.color(15 if g.side == 2 else 11)          # L219
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
            return "newmonth"

        else:                                               # CASE ELSE (L684)
            chosit = 22                                     # L685

        # L688: GOTO menu0 — loop continues


# ═══════════════════════════════════════════════════════════════════════════
#  Top-level game loop
# ═══════════════════════════════════════════════════════════════════════════

def game_loop(g: 'GameState') -> None:
    """Main entry point: runs the full game."""
    from cws_map import usa

    replay = 0

    while True:
        # ── newgame: ──
        _newgame_init(g, replay)
        replay = 1                                          # L109

        # ── Title menu ──
        choice = _title_menu(g)
        if choice == "quit":
            return
        if choice == "resume":
            g.choose = 1
            if g.filel == 0:                                # L669: no save files
                pass  # skip load, fall through to main menu
            else:
                _loader(g)
        else:
            _start_new_game(g)

        # ── Main game loop: menu0 ↔ newmonth ──
        while True:
            result = _main_menu(g)
            if result == "quit":
                return
            if result == "newgame":
                break  # restart outer loop

            # result == "newmonth"
            restarted = _newmonth(g)
            if restarted:                                   # pcode > 0
                break  # restart outer loop
            # else: loop back to _main_menu
