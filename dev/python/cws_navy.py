"""cws_navy.py - Naval operations.
Direct port of cws_navy.bm (793 lines).

Contains:
    chessie(g)                L1-22    - draw Chesapeake Bay outline
    barnacle(g, who)          L24-31   - remove ship from fleet
    navy(g, who, chx)         L32-466  - main naval operations
    shiptype(g, who, i)       L467-470 - determine+draw ship type
    integrity(g)              L471-489 - map link checker
    shipicon(g, who, flag)    L490-521 - draw ship icon
    ships(g)                  L522-537 - draw all fleet positions
    ironclad(g)               L538-641 - ironclad illustration (simplified)
    schooner(g)               L642-792 - schooner illustration (simplified)
"""

import random
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cws_globals import GameState


# ═══════════════════════════════════════════════════════════════════════════
#  SUB chessie                                                  Lines 1-22
# ═══════════════════════════════════════════════════════════════════════════

def chessie(g: 'GameState') -> None:
    """Draw Chesapeake Bay coastline."""
    s = g.screen
    s.color(10)
    # Chain of LINE -() calls for bay outline
    s.pset(500, 185, 10)                                    # L3
    s.line_to(505, 180, 10)
    s.line_to(505, 175, 10)
    s.line_to(500, 170, 10)                                 # L4
    s.line_to(490, 165, 10)
    s.line_to(495, 160, 10)                                 # L5
    s.line_to(490, 155, 10)
    s.line_to(485, 150, 10)                                 # L6
    s.line_to(495, 155, 10)
    s.line_to(495, 145, 10)                                 # L7
    s.line_to(490, 140, 10)
    s.line_to(485, 130, 10)                                 # L8
    s.line_to(470, 120, 10)
    s.line_to(470, 110, 10)                                 # L9
    s.line_to(475, 120, 10)
    s.line_to(485, 120, 10)                                 # L10
    s.line_to(485, 115, 10)
    s.line_to(480, 100, 10)                                 # L11
    s.line_to(485, 90, 10)
    s.line_to(495, 80, 10)                                  # L12
    s.line_to(500, 80, 10)
    s.line_to(500, 85, 10)                                  # L13
    s.line_to(495, 90, 10)
    s.line_to(495, 100, 10)                                 # L14
    s.line_to(495, 115, 10)
    s.line_to(500, 120, 10)                                 # L15
    s.line_to(500, 130, 10)
    s.line_to(515, 135, 10)                                 # L16
    s.line_to(515, 140, 10)
    s.line_to(510, 160, 10)                                 # L17
    s.line_to(520, 145, 10)
    s.line_to(525, 120, 10)                                 # L18
    s.line_to(525, 115, 10)
    s.line_to(515, 85, 10)                                  # L19
    s.line_to(527, 95, 10)
    # L20-21: PAINT for water — simplified fill
    s.paint(500, 400, 1, 10)                                # L20
    s.paint(510, 110, 2)                                    # L21


# ═══════════════════════════════════════════════════════════════════════════
#  SUB barnacle (who)                                           Lines 24-31
# ═══════════════════════════════════════════════════════════════════════════

def barnacle(g: 'GameState', who: int) -> None:
    """Remove one ship from fleet."""
    g.navysize[who] -= 1                                    # L25
    if g.navysize[who] > 0:                                 # L26
        g.fleet[who] = g.fleet[who][:g.navysize[who]]      # L27
    else:                                                   # L28
        g.fleet[who] = ""                                   # L29
        g.navyloc[who] = 0
        g.navysize[who] = 0


# ═══════════════════════════════════════════════════════════════════════════
#  GOSUB helpers used by navy()
# ═══════════════════════════════════════════════════════════════════════════

def _box2(g: 'GameState') -> None:
    """GOSUB box2: clear screen and draw info box (L450-454)."""
    s = g.screen
    s.cls()                                                 # L451
    s.line(100, 110, 550, 240, 1, "B")                      # L452
    s.line(95, 115, 555, 235, 7, "B")                       # L453


def _boxes(g: 'GameState') -> None:
    """GOSUB boxes: draw combat fleet boxes (L446-449)."""
    s = g.screen
    s.line(10, 80, 530, 110, 1, "BF")                       # L447
    s.line(10, 80, 530, 110, 11, "B")                       # L448


def _showhit(g: 'GameState', hit: list) -> None:
    """GOSUB showhit: display hit counters (L418-422)."""
    s = g.screen
    s.locate(9, 6 * g.navysize[1])                          # L419
    s.print_text(f"{hit[1]}  ")
    s.locate(15, 6 * g.navysize[2])                         # L420
    s.print_text(f"{hit[2]}  ")
    if g.noise == 0:                                        # L421
        from cws_util import tick
        tick(g, 0.1 * g.turbo)


def _clr_line17(g: 'GameState') -> None:
    """GOSUB clr1: clear line 17 (L423-424)."""
    s = g.screen
    s.locate(17, 1)
    s.print_text(" " * 60)


def _xout(g: 'GameState', x: int, y: int) -> None:
    """GOSUB xout: draw X over sunk ship (L455-459). Simplified."""
    s = g.screen
    s.pset(x, y, 15)
    # Simplified DRAW → draw an X
    s.line(x - 5, y - 5, x + 5, y + 5, 12)
    s.line(x - 5, y + 5, x + 5, y - 5, 12)


def _nest(g: 'GameState', who: int) -> int:
    """GOSUB nest: AI target selection (L425-445). Returns choose."""
    best = 0                                                # L426
    x = 0
    for i in range(1, g.size + 1):                          # L427
        target = g.array[i]                                 # L428
        if g.cityp[target] == 0:                            # L429: neutral → skip
            continue

        if target == g.navyloc[3 - who]:                    # L431
            if (g.navysize[who] >= g.navysize[3 - who] and
                    random.random() > 0.1):
                return i

        if g.cityp[target] != who:                          # L432
            best = i                                        # L433
            x += 1
            if random.random() > 0.8:                       # L434
                return best

    if best == 0:                                           # L438
        choose = 1 + int(random.random() * g.size)          # L439
    else:
        choose = best                                       # L441

    # Bug preserved: choose = 30 (city index, not array index)
    if who == 2 and g.navyloc[2] == 30:                     # L444
        if random.random() > 0.5:
            return 30

    return choose


# ═══════════════════════════════════════════════════════════════════════════
#  Port selection for new fleet (ships: label, L115-135)
# ═══════════════════════════════════════════════════════════════════════════

def _select_port(g: 'GameState', who: int, chx: int, cost: int, a: int) -> str:
    """Handle the 'ships:' label logic (L115-135).
    Returns 'ahoy', 'return'."""
    from cws_util import tick
    from cws_ui import menu, clrbot, clrrite

    s = g.screen

    while True:                                             # ships: loop (L127)
        g.mtx[0] = "Port"                                  # L116
        g.size = 0
        g.tlx = 67
        g.tly = 12

        for i in range(1, 41):                              # L117
            if (g.matrix[i][7] == 99 and
                    g.cityp[i] == who and
                    g.navyloc[3 - who] != i):
                g.size += 1
                g.mtx[g.size] = g.city[i]
                g.array[g.size] = i

        if chx == 1:                                        # L119
            g.choose = 1 + int(g.size * random.random())

        if g.size < 1:                                      # L120
            g.navysize[who] = 0
            g.fleet[who] = ""
            if chx == 0:                                    # L122
                clrbot(g)
                s.print_text("NO SHIPYARDS AVAILABLE !")
                return "return"
            if chx == 1:                                    # L123
                return "return"

        if chx == 0:                                        # L125
            menu(g, 9)
            clrrite(g)

        if g.choose < 1:                                    # L127
            continue  # GOTO ships

        g.navyloc[who] = g.array[g.choose]                  # L128
        g.cash[who] -= cost                                 # L129
        g.navysize[who] = 1
        ships(g)                                            # L130: CALL ships (SUB)
        clrbot(g)                                           # L131
        s.color(11)
        s.print_text(
            f"{g.force[who]} is building NEW fleet in {g.city[g.array[g.choose]]}"
        )
        # L132: simplified ship icon display
        sx = 400
        sy = 465
        s.pset(sx, sy, 0)
        shipicon(g, who, a)
        if g.noise > 0:                                    # L133
            from cws_sound import qb_sound
            qb_sound(3000, 1)
        tick(g, g.turbo)                                    # L134
        return "ahoy"                                       # L135


# ═══════════════════════════════════════════════════════════════════════════
#  Naval combat (pirate: label, L318-465)
# ═══════════════════════════════════════════════════════════════════════════

def _pirate_combat(g: 'GameState', who: int, chx: int) -> None:
    """Handle ship-vs-ship naval combat (pirate: section)."""
    from cws_util import tick
    from cws_ui import clrbot

    s = g.screen
    hit = [0, 0, 0]

    # pirate: setup                                         L318-323
    while True:                                             # pirate loop
        s.cls()                                             # L319
        s.locate(1, 30)
        s.color(11)
        s.print_text("NAVAL COMBAT")

        for k in range(1, 3):                               # L320-323
            hit[k] = 10
            if g.fleet[k] and g.fleet[k][-1] == "I":
                hit[k] = 20

        # cannon: draw display                              L324-343
        while True:                                         # cannon loop
            s.locate(9, 1)                                  # L325
            s.print_text(" " * 79)
            s.locate(15, 1)                                 # L326
            s.print_text(" " * 79)

            x_pos = 10                                      # L327
            y_pos = 100
            s.color(9)                                      # L328
            s.locate(5, 25)
            s.print_text(f"UNION {g.navysize[1]} ship(s)")
            _boxes(g)                                       # L329 GOSUB boxes
            s.color(1)                                      # L330

            for i in range(1, g.navysize[1] + 1):           # L331-334
                x_pos += 50                                 # L332
                s.pset(x_pos, y_pos, 1)
                shiptype(g, 1, i)                           # L333

            s.color(11)                                     # L335
            s.locate(11, 22)
            s.print_text(f"CONFEDERATES {g.navysize[2]} ship(s)")
            s.line(10, 180, 530, 210, 1, "BF")             # L336
            s.line(10, 180, 530, 210, 11, "B")             # L337

            x_pos = 10                                      # L338
            y_pos = 200
            s.color(1)                                      # L339
            for i in range(1, g.navysize[2] + 1):           # L340-343
                x_pos += 50                                 # L341
                s.pset(x_pos, y_pos, 1)
                shiptype(g, 2, i)
            s.color(11)                                     # L344

            # wave: combat menu                             L345-413
            while True:                                     # wave loop
                g.mtx[0] = "Options"                        # L346
                g.mtx[1] = "Attack"                         # L347
                g.mtx[2] = "Retreat"                        # L348

                if chx > 0:                                 # L349
                    g.choose = 1
                else:
                    g.size = 2                              # L351
                    g.colour = 3
                    g.hilite = 14
                    g.tlx = 50
                    g.tly = 18
                    from cws_ui import menu
                    menu(g, 0)

                # powder: action dispatch                   L352
                if g.choose == 1:                           # CASE 1: Attack
                    # firemore loop                         L355-401
                    result = _firemore(g, who, chx, hit)
                    if result == "sail3":
                        return  # combat over
                    elif result == "cannon":
                        break  # break wave, restart cannon
                    # else shouldn't happen

                elif g.choose == 2:                         # CASE 2: Retreat
                    target = 0                              # L403
                    for i in range(1, 41):                   # L404-406
                        if g.cityp[i] == who:
                            if i != g.navyloc[who] and g.matrix[i][7] == 99:
                                target = i
                                if random.random() > 0.3:   # L405
                                    break
                    clrbot(g)                               # L408
                    s.color(11)
                    s.print_text(
                        f"{g.force[who]} is retreating to {g.city[target]}"
                    )
                    tick(g, g.turbo)
                    g.navyloc[who] = target                 # L409
                    return  # GOTO sail3

                else:                                       # CASE ELSE
                    continue  # GOTO wave (L412)

            # If we broke out of wave loop (cannon restart), continue pirate loop
            # Actually, cannon is an inner loop reset. Let me restructure.
            continue  # restart cannon display


def _firemore(g: 'GameState', who: int, chx: int, hit: list) -> str:
    """Handle the firemore loop (L355-401). Returns 'sail3' or 'cannon'."""
    from cws_util import tick
    from cws_ui import clrbot

    s = g.screen

    while True:                                             # firemore loop
        if g.noise > 0:                                    # L356
            from cws_sound import qb_sound
            qb_sound(77, 0.5)
            qb_sound(59, 0.5)
        pct = 0.0                                           # L357
        if g.fleet[who]:
            a_ch = g.fleet[who][-1]
        else:
            a_ch = "W"

        enemy = 3 - who
        if g.fleet[enemy]:
            b_ch = g.fleet[enemy][-1]
        else:
            b_ch = "W"

        if a_ch != b_ch:                                    # L358
            if a_ch == "I":                                 # L359
                pct = 0.1
            else:
                pct = -0.1

        if random.random() <= 0.5 + pct:                    # L361
            # hitem: hit enemy                              L363
            hit[enemy] -= 1                                 # L364
            _showhit(g, hit)
            if hit[enemy] <= 0:
                x_pos = 10 + 50 * g.navysize[enemy]        # L365
                y_pos = 90                                  # L366
                if who == 1:
                    y_pos = 190
                _xout(g, x_pos, y_pos)                      # L367
                s.locate(17, 5)                             # L368
                s.print_text(f"{g.force[enemy]} ship SUNK!")
                tick(g, g.turbo + 1)
                _clr_line17(g)
                barnacle(g, enemy)                          # L369

                if g.navysize[enemy] < 1:                   # L370
                    s.locate(19, 5)                         # L371
                    s.color(12)
                    s.print_text(f"{g.force[enemy]} fleet DEFEATED")
                    tick(g, g.turbo)                        # L373
                    g.navyloc[enemy] = 0                    # L374
                    g.fleet[enemy] = ""
                    g.victory[enemy] += 10                  # L375 (bug: awards VP to loser?)
                    if who == g.side:                        # L376
                        g.grudge = 1
                    else:
                        g.grudge = 0
                    return "sail3"                          # L377

                hit[enemy] = 10                             # L379
                if g.fleet[enemy] and g.fleet[enemy][-1] == "I":
                    hit[enemy] = 20                         # L380
                return "cannon"                             # L381
        else:
            # hitme1: hit self                              L382
            hit[who] -= 1                                   # L383
            _showhit(g, hit)
            if hit[who] <= 0:
                x_pos = 10 + 50 * g.navysize[who]          # L384
                y_pos = 190                                 # L385
                if who == 1:
                    y_pos = 90
                _xout(g, x_pos, y_pos)                      # L386
                s.locate(17, 5)                             # L387
                s.print_text(
                    f"One of the {g.force[who]} ships was SUNK!"
                )
                tick(g, g.turbo)
                _clr_line17(g)
                barnacle(g, who)                            # L388

                if g.navysize[who] < 1:                     # L389
                    s.locate(19, 5)                         # L390
                    s.color(12)
                    s.print_text(
                        f"Attacking {g.force[who]} fleet has been ELIMINATED !"
                    )
                    tick(g, g.turbo)                        # L392
                    g.navyloc[who] = 0                      # L393
                    g.fleet[who] = ""
                    g.victory[who] += 10                    # L394 (same VP pattern)
                    if who != g.side:                        # L395
                        g.grudge = 1
                    else:
                        g.grudge = 0
                    return "sail3"                          # L396

                hit[who] = 10                               # L398
                if g.fleet[who] and g.fleet[who][-1] == "I":
                    hit[who] = 20                           # L399
                return "cannon"                             # L400


# ═══════════════════════════════════════════════════════════════════════════
#  sail3 cleanup (L460-466)
# ═══════════════════════════════════════════════════════════════════════════

def _sail3(g: 'GameState') -> None:
    """Post-naval cleanup: update commerce, redraw map."""
    from cws_map import usa

    g.commerce = 0                                          # L461
    for k in range(1, 3):                                   # L462
        if g.navyloc[k] == 99:                              # L463
            g.commerce = k
    g.screen.cls()                                          # L465
    usa(g)


# ═══════════════════════════════════════════════════════════════════════════
#  SUB navy (who, chx)                                         Lines 32-466
# ═══════════════════════════════════════════════════════════════════════════

def navy(g: 'GameState', who: int, chx: int) -> None:
    """Main naval operations dispatch."""
    from cws_util import tick
    from cws_ui import menu, clrbot, clrrite
    from cws_map import icon, showcity
    from cws_misc import void
    from cws_army import newarmy
    from cws_recruit import commander
    from cws_combat import capture

    s = g.screen

    # AI pre-processing                                     L33-41
    if chx > 0:                                             # L34
        if g.navyloc[who] < 1:                              # L35
            chx = 1                                         # L36
        else:
            if g.commerce == 3 - who and g.raider > 0:      # L38
                chx = 4
            if g.grudge > 0:                                # L39
                chx = 3

    s.color(11)                                             # L42

    # ── ahoy loop ──────────────────────────────────────────
    while True:                                             # ahoy: (L43)
        cost = 100                                          # L44
        g.cityp[0] = who

        if chx == 0:                                        # L45
            clrbot(g)
            s.print_text(f"Funds available {g.cash[who]}")

        if chx == 1:                                        # L46
            if g.cash[who] < cost:                          # L47
                return
            if g.navysize[who] > 9:                         # L48
                return

        # Build menu options                                L50-67
        g.mtx[0] = "Ships"                                  # L50
        g.mtx[1] = "Build"                                  # L51

        if g.navyloc[who] != 99:                            # L52
            if (g.cash[who] < cost or g.navysize[who] > 9 or
                    g.cityp[g.navyloc[who]] != who):        # L53
                g.mtx[1] = "-"
                g.choose = 23

        g.mtx[2] = "Attack"                                # L55
        if g.navyloc[who] != 99:                            # L56
            if g.cityp[g.navyloc[who]] != 3 - who:         # L57
                g.mtx[2] = "-"
                g.choose = 22
        else:                                               # L58-60
            g.mtx[1] = "-"
            g.mtx[2] = "-"
            g.choose = 24

        g.mtx[3] = "Sail"                                  # L61
        if g.navyloc[who] < 1:
            g.mtx[3] = "-"
            if chx == 3:
                chx = 1

        g.mtx[4] = "Raid"                                  # L62
        if g.navysize[who] < 1 or g.commerce == who:
            g.mtx[4] = "-"

        g.tlx = 67                                          # L63
        g.tly = 12
        g.size = 4

        if g.navyloc[who] != 99:                            # L64-67
            if (who == 1 and g.navysize[who] > 1 and
                    g.cityp[g.navyloc[who]] == 0):          # L65
                g.size = 5
                g.mtx[5] = "Invasion"
                void(g, g.navyloc[1])
                defend = g.anima[0]  # void stores result in anima(0) based on convention
                # Actually void returns via the second param. Let me check.
                # void(g, a) calculates weighted defense. The result is in the second param.
                # But in Python we use g.anima[0] or we need to check the void implementation.
                # Looking at original: CALL void(navyloc(1), defend)
                # void modifies 'defend' via reference. In our Python port, void returns the value.
                defend = void(g, g.navyloc[1])
                if chx > 0 and defend < 100:
                    chx = 5

            if (g.realism == 0 and who == 2 and g.navysize[who] > 1 and
                    g.cityp[g.navyloc[who]] == 0):          # L66
                g.size = 5
                g.mtx[5] = "Invasion"
                defend = void(g, g.navyloc[1])
                if chx > 0 and defend < 100:
                    chx = 5

        # Action selection                                  L69-71
        action = g.choose  # default from menu disabling above

        if chx > 0:                                         # L69
            action = chx
        else:
            if g.nflag > 0 and g.choose != 1:              # L70
                return
            menu(g, 0)                                      # L71
            clrrite(g)
            action = g.choose

        # ── anchor: SELECT CASE dispatch ───────────────────
        # Handle re-dispatch (GOTO anchor with changed chx)
        while True:  # anchor dispatch loop

            # ──────────── CASE 1: Build Ship ──────────────
            if action == 1:                                 # L78
                if g.cash[who] < cost or g.navyloc[who] == 99:  # L79
                    break  # GOTO ahoy

                if chx == 1 and g.navysize[who] > 9:       # L80
                    return
                if chx == 0 and g.navysize[who] > 9:       # L81
                    break  # GOTO ahoy

                if chx == 0 and g.navyloc[who] > 0:        # L83
                    if g.cityp[g.navyloc[who]] != who:      # L84
                        break  # GOTO ahoy
                    if g.matrix[g.navyloc[who]][7] < 99:    # L85
                        break  # GOTO ahoy

                if chx == 1 and random.random() < 0.07 * g.navysize[who]:  # L87
                    return

                a_type = "W"                                # L88: ship type

                # noiron check                              L90
                skip_iron = False
                if g.realism > 0 and (g.year < 1862 or
                        (g.year == 1862 and g.month < 3)):
                    skip_iron = True

                if not skip_iron and g.cash[who] >= 2 * cost:  # L91
                    g.tlx = 67                              # L92
                    g.tly = 12
                    g.colour = 9
                    if who == g.side:                        # L93
                        g.mtx[0] = "Type"                   # L94
                        g.mtx[1] = "Wooden"
                        g.mtx[2] = "Ironclad"
                        g.size = 2                          # L97
                        menu(g, 0)                          # L98
                        clrrite(g)                          # L99
                        if g.choose < 1:                    # L100
                            break  # GOTO ahoy
                        if g.choose == 2:                   # L101
                            a_type = "I"
                            cost = 2 * cost
                    else:                                   # L102-104
                        a_type = "I"

                # noiron: add ship                          L107-142
                g.navysize[who] += 1                        # L108
                a_flag = 0
                if a_type == "W":                           # L109
                    g.fleet[who] = g.fleet[who] + a_type    # L110
                    a_flag = 1
                else:
                    g.fleet[who] = a_type + g.fleet[who]    # L112
                    a_flag = 2

                if g.navysize[who] > 1:                     # L114: add2ship
                    # add2ship:                             L136-142
                    g.cash[who] -= cost                     # L137
                    clrbot(g)                               # L138
                    s.print_text(
                        f"{g.force[who]} navy increased to {g.navysize[who]}"
                    )
                    sx = 400                                # L139
                    sy = 465
                    s.pset(sx, sy, 0)
                    shipicon(g, who, a_flag)
                    ships(g)                                # L140: CALL ships (SUB)
                    if g.noise > 0:                         # L141
                        from cws_sound import qb_sound
                        qb_sound(3000, 1)
                    tick(g, g.turbo)                        # L142
                    break  # falls through to GOTO ahoy (L314)
                else:
                    # ships: port selection                  L115
                    result = _select_port(g, who, chx, cost, a_flag)
                    if result == "return":
                        return
                    break  # "ahoy"

            # ──────────── CASE 2: Attack City ─────────────
            elif action == 2:                               # L146
                if g.navyloc[who] == 99:                    # L147
                    break  # GOTO ahoy
                if chx == 2 and g.cityp[g.navyloc[who]] == who:  # L148
                    return
                if chx == 2 and g.occupied[g.navyloc[who]] > 0 and random.random() > 0.5:  # L149
                    chx = 3
                    action = 3
                    continue  # GOTO anchor with CASE 3
                if chx == 2 and g.cityp[g.navyloc[who]] == 0:  # L150
                    chx = 3
                    break  # GOTO ahoy
                if g.navyloc[who] < 1:                      # L151
                    return
                if who == g.side:                            # L152
                    g.nflag = 1

                if g.cityp[g.navyloc[who]] != 3 - who:     # L153
                    break  # GOTO ahoy

                clrbot(g)                                   # L154
                s.color(12)
                s.print_text(f"{g.force[who]} fleet bombards {g.city[g.navyloc[who]]}")
                icon(g, g.navyloc[who], 0, 3)              # L155

                target = g.navyloc[who]                     # L157
                index = g.occupied[target]

                if index > 0:                               # not deserted
                    pct = 0.005 * g.navysize[who] + 0.02 * random.random()  # L158
                    killd = int(g.armysize[index] * pct)
                    if killd < 1:
                        killd = 1
                    clrbot(g)                               # L159
                    s.print_text(
                        f"{g.armyname[index]} suffered {100 * killd} casualties"
                    )
                    x_sup = int(0.5 * g.navysize[who] + 1)  # L160
                    if x_sup > g.supply[index]:
                        x_sup = g.supply[index]
                    g.supply[index] -= x_sup                # L161
                    tick(g, g.turbo)                        # L162
                    g.armysize[index] -= killd              # L163
                    if g.armysize[index] < 1:
                        g.armysize[index] = 1
                    return                                  # L164

                # deserted: (L165)
                while True:
                    if g.fort[target] == 0:                 # L166: GOTO blast
                        # blast: (L188)
                        if random.random() > 0.25 + 0.07 * g.navysize[who]:  # L189
                            clrbot(g)
                            s.print_text(
                                f"Citizens of {g.city[target]} stand firm against the attack"
                            )
                            tick(g, g.turbo)
                            return
                        if g.navyloc[who] == g.capcity[3 - who]:  # L190
                            clrbot(g)
                            s.print_text("The CAPITAL steadfastly stands loyal")
                            tick(g, g.turbo)
                            return
                        g.cityp[g.navyloc[who]] = 0         # L191
                        clrbot(g)                           # L192
                        s.print_text(f"{g.city[g.navyloc[who]]} is now  NEUTRAL")
                        showcity(g)                         # L193
                        g.victory[who] += g.cityv[g.navyloc[who]]  # L194
                        return                              # L195
                    else:
                        # Fort defense                      L167
                        if random.random() < 0.7 + 0.03 * (g.navysize[who] - g.fort[target]):
                            # hurt1: (L182)
                            clrbot(g)                       # L183
                            s.print_text(f"{g.city[target]} fortifications damaged")
                            g.fort[target] -= 1             # L184
                            x_c = g.cityx[target]
                            y_c = g.cityy[target]
                            s.line(x_c - 5, y_c - 5, x_c + 5, y_c + 5, 2, "BF")
                            showcity(g)                     # L185
                            tick(g, g.turbo)                # L186
                            return                          # L187
                        else:
                            # Shore battery sinks attacker  L168
                            barnacle(g, who)
                            clrbot(g)                       # L169-170
                            s.print_text(
                                f"{g.force[g.cityp[target]]} shore battery sunk an attacking ship! "
                                f"{g.navysize[who]} ship(s) left!"
                            )
                            if g.noise > 0:                 # L171
                                from cws_sound import qb_sound
                                qb_sound(77, 0.5)
                                qb_sound(59, 0.5)
                            tick(g, g.turbo)                # L172

                            if g.navysize[who] < 1:        # L173
                                g.navyloc[who] = 0          # L174
                                g.fleet[who] = ""
                                _box2(g)
                                s.locate(12, 27)            # L175
                                s.print_text(f"{g.force[who]} fleet eliminated")
                                tick(g, 9)                  # L176
                                g.victory[3 - who] += 5     # L177
                                if who == g.side:           # L178
                                    g.grudge = 0
                                _sail3(g)                   # L179: GOTO sail3
                                return
                            continue  # L181: GOTO deserted

                # Should not reach here
                return

            # ──────────── CASE 3: Sail ────────────────────
            elif action == 3:                               # L199
                g.navysize[who] = len(g.fleet[who])         # L200

                if g.navysize[who] < 1 and chx > 0:        # L201
                    return
                if g.navyloc[who] < 1 or g.navysize[who] < 1:  # L202
                    clrbot(g)
                    s.print_text("No ships remain")
                    tick(g, 1)
                    break  # GOTO ahoy

                g.size = 0                                  # L204
                for i in range(1, 41):                      # L205
                    if g.matrix[i][7] > 90 and g.navyloc[who] != i:
                        g.size += 1
                        g.mtx[g.size] = g.city[i]
                        g.array[g.size] = i

                if chx == 3:                                # L207
                    if g.size == 0:                         # L208
                        return
                    if g.grudge > 0:                        # L209
                        g.choose = 1
                        g.array[1] = g.navyloc[3 - who]
                    else:
                        # GOSUB nest                        L210
                        g.choose = _nest(g, who)
                        if g.choose <= 0:
                            return
                else:
                    # Player UI                             L212-221
                    s.color(11)                             # L212
                    s.locate(11, 68)
                    if g.navyloc[who] < 41:                 # L213
                        s.print_text(g.city[g.navyloc[who]])
                    else:
                        s.print_text("Raiding")             # L216
                    g.mtx[0] = "To"                         # L218
                    g.colour = 3                            # L219
                    g.tlx = 67
                    g.tly = 12
                    menu(g, 9)                              # L221
                    clrrite(g)
                    if g.choose < 1:
                        return

                # admiral:                                  L222
                if g.array[g.choose] == g.navyloc[who]:     # L223
                    return
                if g.array[g.choose] < 1:                   # L224
                    return
                if g.navysize[who] < 1:                     # L225
                    # GOTO ships: port selection
                    result = _select_port(g, who, chx, cost, 1)
                    if result == "return":
                        return
                    break  # ahoy

                if who == g.side:                           # L226
                    g.nflag = 1

                _box2(g)                                    # L227
                s.locate(10, 25)                            # L228
                s.print_text(f"{g.force[who]} fleet of {g.navysize[who]} ship(s) is sailing")
                s.locate(11, 25)                            # L229
                loc_str = ""
                if g.navyloc[who] < 41:                     # L230
                    loc_str = g.city[g.navyloc[who]]
                else:
                    loc_str = "Raiding"                     # L233
                dest_str = ""
                if g.array[g.choose] != 99:                 # L236
                    dest_str = g.city[g.array[g.choose]]
                else:
                    dest_str = "Raid Commerce"              # L239
                s.print_text(f"From {loc_str} to {dest_str}")

                # Ship display                              L242-245
                for i in range(1, g.navysize[who] + 1):
                    s.pset(120 + 41 * i, 210, 0)            # L243
                    shiptype(g, who, i)                     # L244

                # Ship illustration                         L246-257
                if g.graf > 2:                              # L246
                    if g.fleet[who]:
                        ch = g.fleet[who][0]
                        if ch == "I":                       # L249
                            ironclad(g)
                        elif ch == "W":                     # L251
                            schooner(g)
                    tick(g, 2 * g.turbo)                    # L254
                else:
                    tick(g, g.turbo)                        # L256

                g.navyloc[who] = g.array[g.choose]          # L258

                if g.navyloc[1] == g.navyloc[2]:            # L259: pirate
                    _pirate_combat(g, who, chx)
                _sail3(g)                                   # L260: sail3
                return

            # ──────────── CASE 4: Raid Commerce ───────────
            elif action == 4:                               # L264
                g.navysize[who] = len(g.fleet[who])         # L265

                if g.navysize[who] < 1 and chx > 0:        # L266
                    return
                if g.navysize[who] < 1 or g.commerce == who:  # L267
                    break  # GOTO ahoy

                if who == g.side:                           # L269
                    g.nflag = 1

                _box2(g)                                    # L270
                s.locate(10, 25)                            # L271
                s.print_text(
                    f"{g.force[who]} fleet of {g.navysize[who]} ship(s) is sailing"
                )
                s.locate(11, 25)                            # L272
                s.print_text(f"to RAID {g.force[3 - who]} COMMERCE !")

                for i in range(1, g.navysize[who] + 1):     # L274-277
                    s.pset(120 + 41 * i, 210, 0)            # L275
                    shiptype(g, who, i)                     # L276

                if g.graf > 2:                              # L278
                    if g.fleet[who]:
                        ch = g.fleet[who][0]
                        if ch == "I":                       # L281
                            ironclad(g)
                        elif ch == "W":                     # L283
                            schooner(g)
                    tick(g, 2 * g.turbo)                    # L286
                else:
                    tick(g, g.turbo)                        # L288

                g.navyloc[who] = 99                         # L290
                g.commerce = who

                if g.navyloc[1] == g.navyloc[2]:            # L291
                    _pirate_combat(g, who, chx)
                    _sail3(g)
                    return

                g.screen.cls()                              # L292
                from cws_map import usa
                usa(g)
                return                                      # L293

            # ──────────── CASE 5: Invasion ────────────────
            elif action == 5:                               # L297
                empty = commander(g, who)                   # L298
                if chx > 0 and empty == 0:                  # L299
                    chx = 3
                    action = 3
                    continue  # GOTO anchor with CASE 3

                barnacle(g, who)                            # L301
                c = g.navyloc[who]                          # L302
                newarmy(g, who, empty, c)
                g.cash[who] += 100                          # L303: compensate
                capture(g, empty, c, who, 0)                # L304
                g.armysize[empty] = 35                      # L305 (x=35 from L300)
                if who == g.side:                           # L306
                    g.nflag = 1
                return                                      # L307

            # ──────────── CASE ELSE ───────────────────────
            else:                                           # L311
                return                                      # L312

            # End of anchor dispatch
            break

        # End of ahoy loop iteration: continue loops back to ahoy


# ═══════════════════════════════════════════════════════════════════════════
#  SUB shiptype (who, i)                                       Lines 467-470
# ═══════════════════════════════════════════════════════════════════════════

def shiptype(g: 'GameState', who: int, i: int) -> None:
    """Determine ship type and draw icon."""
    a = 1                                                   # L468
    if i <= len(g.fleet[who]) and g.fleet[who][i - 1] == "I":
        a = 2
    shipicon(g, who, a)                                     # L469


# ═══════════════════════════════════════════════════════════════════════════
#  SUB integrity                                               Lines 471-489
# ═══════════════════════════════════════════════════════════════════════════

def integrity(g: 'GameState') -> None:
    """Check map link integrity."""
    s = g.screen
    s.cls()                                                 # L472
    s.color(15)
    x_err = 0                                               # L473
    y_fix = 0

    for i in range(1, 41):                                  # L474
        for j in range(1, 7):                               # L475
            if g.matrix[i][j] == 0:
                break  # done with this city
            index = g.matrix[i][j]                          # L476
            found = False
            for k in range(1, 7):                           # L477
                if g.matrix[index][k] == i:                 # L478
                    found = True
                    break
                if g.matrix[index][k] == 0:                 # L479
                    g.matrix[index][k] = i
                    s.print_text(
                        f"+ Adding return route from {g.city[index]} to {g.city[i]}"
                    )
                    y_fix += 1
                    found = True
                    break
            if not found:                                   # L481
                x_err += 1
                s.print_text(
                    f"Error in CITIES.GRD entry for city #{i} "
                    f"{g.city[index]}: no return route to {g.city[i]}"
                )
                from cws_util import tick
                tick(g, 1)

    if x_err + y_fix == 0:                                  # L486
        s.print_text("ALL MAP LINKS ARE OK")
        return
    if y_fix > 0:                                           # L487
        s.print_text(f"* {y_fix} fixes made to provide RETURN ROUTES")
    if x_err > 0:                                           # L488
        s.print_text(f"** {x_err} UNRESOLVED RETURN ROUTES")


# ═══════════════════════════════════════════════════════════════════════════
#  SUB shipicon (who, flag)                                    Lines 490-521
# ═══════════════════════════════════════════════════════════════════════════

def shipicon(g: 'GameState', who: int, flag: int) -> None:
    """Draw ship icon. flag=1: wooden, flag=2: ironclad.
    Uses screen._last_x/_last_y from preceding PSET as position."""
    s = g.screen
    x = s._last_x - 10                                     # L491
    y = s._last_y - 10

    # Oval hull (simplified from CIRCLE with aspect 0.4)     L492-494
    # Draw an ellipse approximation: width=18, height=7
    s.line(x - 9, y - 4, x + 9, y + 4, 9, "B")            # inner
    s.line(x - 9, y - 4, x + 9, y + 4, 10, "B")           # outer

    if flag == 1:                                           # L496: wooden ship
        # Simplified: draw hull shape and mast
        s.line(x - 10, y + 3, x + 10, y + 3, 4)           # hull line
        s.line(x, y - 8, x, y + 3, 0)                      # mast
        s.line(x, y - 8, x + 7, y - 3, 7)                  # sail
        # Jack (flag)
        if who == 1:                                        # L515-516
            s.line(x + 4, y - 8, x + 7, y - 8, 4)
            s.line(x + 4, y - 7, x + 7, y - 7, 1)
        else:                                               # L517-518
            s.line(x + 4, y - 8, x + 7, y - 8, 4)
            s.line(x + 4, y - 7, x + 7, y - 7, 3)

    elif flag == 2:                                         # L503: ironclad
        # Simplified: draw low hull and turret
        s.line(x - 10, y + 2, x + 10, y + 2, 8)           # hull line
        s.line(x - 8, y + 3, x + 8, y + 3, 0)             # waterline
        s.line(x - 3, y - 2, x + 3, y + 1, 8, "BF")       # turret
        s.line(x + 3, y, x + 8, y, 0)                      # gun
        # Jack
        if who == 1:
            s.line(x - 3, y - 4, x, y - 4, 4)
            s.line(x - 3, y - 3, x, y - 3, 1)
        else:
            s.line(x - 3, y - 4, x, y - 4, 4)
            s.line(x - 3, y - 3, x, y - 3, 3)


# ═══════════════════════════════════════════════════════════════════════════
#  SUB ships                                                   Lines 522-537
# ═══════════════════════════════════════════════════════════════════════════

def ships(g: 'GameState') -> None:
    """Draw all fleet positions on map."""
    s = g.screen

    for side in range(1, 3):                                # L523: FOR s = 1 TO 2
        if g.navysize[side] == 0 or g.navyloc[side] == 0:  # L524
            g.navyloc[side] = 0
            continue  # sink

        # Determine position                                L525-530
        loc = g.navyloc[side]
        if loc == 30:                                       # L525
            x = 515
            y = 268
        elif loc == 28:                                     # L526
            x = 517
            y = 172
        elif loc == 17:                                     # L527
            x = 380
            y = 425
        elif loc == 99:                                     # L528
            x = 495
            y = 310
        else:                                               # L529
            x = g.cityx[loc] + 25
            y = g.cityy[loc] + 25
            if loc == 24:                                   # L530
                y += 5
                x -= 5

        # Draw ship icon                                    L532-534
        s.pset(x, y, 1)                                    # L532
        a = 1                                               # L533
        if g.fleet[side] and g.fleet[side][0] == "I":
            a = 2
        shipicon(g, side, a)                                # L534


# ═══════════════════════════════════════════════════════════════════════════
#  SUB ironclad                                                Lines 538-641
#  Simplified for monochrome: basic ship silhouette
# ═══════════════════════════════════════════════════════════════════════════

def ironclad(g: 'GameState') -> None:
    """Ironclad illustration. Simplified for monochrome."""
    s = g.screen
    # Sky and water                                         L540-541
    s.line(1, 240, 639, 309, 3, "BF")                       # L540: cyan sky
    s.line(1, 309, 639, 479, 1, "BF")                       # L541: blue water

    # Simplified hull silhouette
    s.color(7)
    # Main hull
    s.line(86, 363, 478, 368, 7)
    s.line(78, 353, 86, 363, 7)
    s.line(78, 353, 161, 337, 7)
    s.line(161, 337, 406, 326, 7)
    s.line(406, 326, 478, 368, 7)
    s.line(86, 363, 478, 368, 8, "BF")                     # fill hull

    # Turret
    s.line(297, 310, 340, 260, 8, "BF")
    s.line(297, 310, 340, 310, 0)
    s.line(297, 260, 340, 260, 0)

    # Smokestack
    s.line(314, 255, 330, 314, 8, "BF")

    # Waterline
    s.line(70, 361, 490, 375, 11)

    # Flag
    s.line(95, 297, 115, 315, 4, "BF")


# ═══════════════════════════════════════════════════════════════════════════
#  SUB schooner                                                Lines 642-792
#  Simplified for monochrome: basic sailing ship
# ═══════════════════════════════════════════════════════════════════════════

def schooner(g: 'GameState') -> None:
    """Schooner illustration. Simplified for monochrome."""
    s = g.screen
    # Sky and water                                         L644-645
    s.line(1, 240, 639, 309, 3, "BF")                       # L644
    s.line(1, 309, 639, 479, 1, "BF")                       # L645

    # Masts                                                 L647-648
    s.color(6)
    s.line(245, 241, 245, 400, 6)                           # fore mast
    s.line(371, 241, 371, 400, 6)                           # main mast

    # Hull                                                  L649-654
    s.line(183, 395, 435, 400, 6)                           # deck
    s.line(188, 395, 107, 356, 6)                           # bow
    s.line(107, 356, 173, 392, 6)                           # bow lower
    s.line(435, 400, 447, 377, 6)                           # stern
    s.line(183, 395, 435, 400, 6, "BF")                    # fill hull area

    # Simplified sails                                      L666-695
    s.color(15)
    # Forward sail
    s.line(109, 355, 239, 256, 15)
    s.line(109, 355, 131, 361, 15)
    s.line(131, 361, 239, 259, 15)

    # Main sail
    s.line(379, 290, 433, 264, 15)
    s.line(433, 264, 435, 289, 15)
    s.line(435, 289, 406, 342, 15)
    s.line(406, 342, 379, 290, 15)

    # Portholes
    s.color(0)
    for k in range(260, 401, 25):
        s.circle(k, 405, 3, 0)

    # Water effects
    s.color(11)
    s.line(247, 437, 290, 422, 11)
    s.line(290, 422, 314, 416, 11)
    s.line(362, 428, 385, 419, 11)
    s.line(385, 419, 394, 421, 11)
