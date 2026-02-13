"""cws_recruit.py - Recruitment and commander assignment.
Direct port of cws_recruit.bm (128 lines).

Contains:
    recruit(g, who)             L1-106   - recruit new armies / reinforce
    commander(g, who)           L108-127 - find/create commander for new army
"""

import random
from typing import TYPE_CHECKING

from cws_globals import UNION, CONFEDERATE

if TYPE_CHECKING:
    from cws_globals import GameState


def _strong(g: 'GameState', index: int) -> str:
    """Army strength string: armysize * 100."""
    return f"{g.armysize[index]}00"


def _playb(g: 'GameState', empty: int) -> None:
    """GOSUB playb (L101-104): difficulty bonus to army size."""
    if g.side == UNION and g.difficult < 3:                  # L102
        g.armysize[empty] += 15 - 5 * g.difficult
    if g.side == CONFEDERATE and g.difficult > 3:           # L103
        g.armysize[empty] += 5 * g.difficult - 15


def _randsel(g: 'GameState', who: int, size: int) -> int:
    """GOSUB randsel (L73-100): AI city selection. Returns choose."""
    from cws_army import cutoff

    choose = 0                                              # L74
    for i in range(1, size + 1):                            # L75
        target = g.array[i]                                 # L76
        x = g.occupied[target]                              # L78
        # L79: XOR on booleans: choose if exactly one is true
        if (x == 0) != (g.armysize[x] < 155):              # L79
            choose = i

    if choose == 0:                                         # L82
        choose = 1 + int(random.random() * size)

    if g.realism > 0:                                       # L83
        x_best = 0                                          # L84
        for i in range(1, size + 1):                        # L85
            target = g.array[i]                             # L86
            if g.occupied[target] == 0:                     # L87
                y = 3 * g.cityv[target] + 33                # L88
                a = cutoff(g, who, target)                  # L89
                if a < 1:                                   # L90
                    y = y // 3
            else:                                           # L91
                y = 2 * g.cityv[target] + 20                # L92
                a = cutoff(g, who, target)                  # L93
                if a < 1:                                   # L94
                    y = y // 3
            if y > x_best and random.random() > 0.5:       # L96
                x_best = y
                choose = i

    if g.cash[who] < 100:                                   # L99
        choose = size

    return choose


# ═══════════════════════════════════════════════════════════════════════════
#  SUB recruit (who)                                           Lines 1-106
# ═══════════════════════════════════════════════════════════════════════════

def recruit(g: 'GameState', who: int) -> None:
    """Recruit new armies or reinforce existing ones."""
    from cws_util import starfin, tick, bubble
    from cws_ui import menu, clrbot, clrrite
    from cws_data import occupy
    from cws_map import icon
    from cws_army import newarmy, placearmy, cutoff

    s = g.screen

    if g.cash[who] < 100:                                   # L2: menu1
        return

    g.size = 0                                              # L3
    s.color(12)
    g.mtx[0] = "Recruit"                                   # L4

    # Check for cached recruitment cities                    L5
    if who == g.side and g.rflag > 0:
        for i in range(1, g.rflag + 1):
            x = g.rcity[i]
            g.mtx[i] = g.city[x]
            g.array[i] = x
        g.size = g.rflag
    else:
        # Build list of eligible cities                      L6-23
        max_cities = 4                                      # L6
        if random.random() > 0.8:
            max_cities -= 1
        if g.difficult < 3:                                 # L7
            max_cities += 1

        for i in range(1, 41):                              # L9
            if g.control[who] > 0:                          # L10
                pct = 0.6 * max_cities / g.control[who]
            else:
                pct = 0.3
            if g.size == 0 and i > 20:                      # L11
                pct = 0.3
            if g.size < 2 and i > 30:                       # L12
                pct = 0.3
            g.array[i] = 0                                  # L13
            if g.occupied[i] > 0 and g.cityp[i] == who:    # L14
                pct = 0.4
            if random.random() < pct and g.cityp[i] == who:  # L15
                if g.realism > 0 and g.cityo[i] == g.enemy_of(who):  # L16: foe
                    continue
                g.size += 1                                 # L17
                g.mtx[g.size] = g.city[i]                   # L18
                g.array[g.size] = i                         # L19
                if g.size > max_cities - 1:                 # L20
                    break  # alldone

    # alldone:                                              L24
    if g.size == 0:                                         # L25: menu1
        return

    # Cache for player                                      L26
    if who == g.side and g.rflag == 0:
        for i in range(1, g.size + 1):
            g.rcity[i] = g.array[i]
        g.rflag = g.size

    bubble(g, g.size)                                       # L27

    # ── levy loop ──                                       L29-72
    while True:
        if g.cash[who] < 100:                               # L30: menu1
            return

        if who == g.side or g.player == 2:                  # L31
            clrbot(g)
            s.print_text(f"{g.force[who]} funds available {g.cash[who]}")

        g.tlx = 67                                          # L32
        g.tly = 12
        g.colour = 3

        if who != g.side:                                   # L33: AI
            g.choose = _randsel(g, who, g.size)
        else:
            # Player menu                                   L35-37
            if g.choose > 0:                                # L35
                g.choose = 21 + g.choose
            menu(g, 2)                                      # L36
            clrrite(g)
            if g.choose < 1:                                # L37: menu1
                return

        # auto1:                                            L38
        empty = 0                                           # L39
        index = g.array[g.choose]                           # L40
        occupy(g, index)                                    # L41

        if g.occupied[index] > 0:                           # L42: add2
            i = g.occupied[index]
            # ── add2: reinforce existing army ──           L52-72
            target = g.array[g.choose]                      # L53
            x_add = 45                                      # L54
            a_str = ""
            if g.realism > 0:                               # L55
                x_add = 2 * g.cityv[g.armyloc[i]] + 20     # L56
                a = cutoff(g, who, target)                  # L57
                if a < 1:                                   # L58
                    x_add = x_add // 3
                    a_str = " ISOLATED !"
            g.armysize[i] += x_add                          # L60

            _playb(g, i)                                    # L62: GOSUB playb (uses i as empty)
            g.cash[who] -= 100                              # L63

            from_ = g.armyloc[i]                            # L64
            ix = g.cityx[from_] - 12
            iy = g.cityy[from_] - 11
            saved = s.get_image(ix - 9, iy - 7, ix + 9, iy + 6)  # L65
            icon(g, g.armyloc[i], 0, 2)                     # L66
            if g.noise > 0:                                 # L67
                from cws_sound import qb_sound
                qb_sound(2222, 1)

            s.color(11)                                     # L68
            clrbot(g)
            s.print_text(
                f"Army {i} {g.armyname[i]} in {g.city[g.armyloc[i]]} "
                f"strength increased to {_strong(g, i)}"
            )
            if a_str:                                       # L69
                s.print_text(a_str)

            if saved is not None:                           # L70
                s.put_image(ix - 9, iy - 7, saved)
            tick(g, max(0, g.turbo - 0.5))                  # L71
            continue  # GOTO levy (L72)

        else:
            # ── New army ──                                L43-50
            empty = commander(g, who)                       # L43

            if who != g.side and empty == 0:                # L45: menu1
                return
            if empty == 0:                                  # L46: levy
                continue

            g.armyloc[empty] = index                        # L47
            _playb(g, empty)                                # L48: GOSUB playb
            newarmy(g, who, empty, index)                   # L49
            continue  # GOTO levy (L50)


# ═══════════════════════════════════════════════════════════════════════════
#  SUB commander (who, empty)                                  Lines 108-127
# ═══════════════════════════════════════════════════════════════════════════

def commander(g: 'GameState', who: int) -> int:
    """Find or create a commander. Returns empty army slot index (0 if none)."""
    from cws_util import starfin, tick
    from cws_ui import clrbot, roman

    star, fin = starfin(g, who)                             # L110

    # Search for existing named leader                      L111-113
    for i in range(star, fin + 1):
        if g.armyloc[i] == 0 and g.lname[i] != "":         # L112
            return i

    # Generate generic leader with roman numeral name       L116-124
    for i in range(star, fin + 1):                          # L116
        if g.armyloc[i] == 0:                               # L117
            a_name = roman(i)                               # L119
            g.lname[i] = a_name                             # L121
            g.rating[i] = 1 + int(8 * random.random())     # L122
            return i                                        # L123

    # No slots available                                    L126
    clrbot(g)
    g.screen.print_text(f"No more {g.force[who]} commanders available")
    tick(g, g.turbo)
    return 0
