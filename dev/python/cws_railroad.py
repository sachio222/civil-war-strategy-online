"""cws_railroad.py - Railroad movement.
Direct port of cws_railroad.bm (127 lines).

Contains:
    railroad(g, who)            L1-104   - main railroad movement
    tinytrain(g, who, flag)     L105-118 - draw/erase train icon
    traincapacity(g, who)       L119-126 - calculate rail capacity
"""

from typing import TYPE_CHECKING

from cws_globals import UNION, CONFEDERATE

if TYPE_CHECKING:
    from cws_globals import GameState


def _route(g: 'GameState', target: int, who: int) -> int:
    """GOSUB route (L87-98): count friendly rail connectivity.
    Returns x (0 = no connection, >1 = good route)."""
    x = 0                                                   # L88
    for j in range(1, 7):
        y = g.matrix[target][j]                             # L89
        if y > 0 and g.cityp[y] == who:                    # L90
            x += 1                                          # L91
            for m in range(1, 7):                            # L92
                z = g.matrix[y][m]                           # L93
                if z > 0 and z != target and g.cityp[z] == who:  # L94
                    x += 1
    return x


def _toot(g: 'GameState', who: int) -> None:
    """GOSUB-like cleanup for toot: label (L100-104)."""
    from cws_util import tick
    from cws_ui import clrrite, clrbot
    if who == g.side:                                       # L101
        tick(g, 9)
    clrrite(g)                                              # L102
    clrbot(g)                                               # L103


# ═══════════════════════════════════════════════════════════════════════════
#  SUB traincapacity (who, limit)                              Lines 119-126
# ═══════════════════════════════════════════════════════════════════════════

def traincapacity(g: 'GameState', who: int) -> int:
    """Calculate railroad capacity. Returns limit."""
    if g.realism == 0:                                      # L120
        return g.train[who]
    x = 11                                                  # L121
    if g.side == CONFEDERATE:
        x = 23
    limit = g.train[who] + 5 * (g.control[who] - x)        # L122
    x2 = 2 * g.train[who]                                   # L123
    if limit > x2:                                          # L124
        limit = x2
    if limit < x2 // 4:                                    # L125
        limit = x2 // 4
    return limit


# ═══════════════════════════════════════════════════════════════════════════
#  SUB tinytrain (who, flag)                                   Lines 105-118
# ═══════════════════════════════════════════════════════════════════════════

def tinytrain(g: 'GameState', who: int, flag: int) -> None:
    """Draw or erase train icon at tracked city."""
    s = g.screen

    if g.tracks[who] == 0:                                  # L106
        return
    from_ = g.tracks[who]                                   # L107
    x = g.cityx[from_] - 12                                # L108
    y = g.cityy[from_] - 11

    if flag > 0:                                            # L110: draw train
        s.line(x - 8, y - 6, x + 10, y + 7, 10, "BF")     # L111
        c = 9                                               # L112
        if who == 2:
            c = 15
        s.pset(x - 6, y - 2, 3)                            # L112: set cursor
        # L113: DRAW train outline in black at half scale (S2)
        s.draw("C0S2R9D4R6U3R3D3R7U5H3U2R9D3G2D6F1D3F5"
               "L10D1G1L4H2L7G2L3H2L3U8L2U5BF4S4")
        # L114: PAINT fill interior with side color, bounded by black
        fx, fy = s._last_x, s._last_y
        s.paint(fx, fy, c, 0)
    else:                                                   # L115: erase
        s.line(x - 9, y - 8, x + 10, y + 8, 2, "BF")      # L116


# ═══════════════════════════════════════════════════════════════════════════
#  SUB railroad (who)                                          Lines 1-104
# ═══════════════════════════════════════════════════════════════════════════

def railroad(g: 'GameState', who: int) -> None:
    """Main railroad movement handler."""
    from cws_util import starfin, tick, stax
    from cws_ui import clrbot, clrrite
    from cws_misc import void, newcity
    from cws_army import movefrom, placearmy
    from cws_data import occupy
    from cws_combat import capture
    from cws_flow import engine

    s = g.screen

    if g.rr[who] == 0:                                      # L2: CASE 0
        # ── No train in transit: start new move ──

        if who == g.side:                                   # L4: GOTO human
            # ── Human player ──                            L36-64
            index, a = movefrom(g)                          # L37
            if a < 1 or index < 1:
                s.color(11)
                clrbot(g)
                s.print_text("Railroad move not allowed")
                _toot(g, who)
                return

            limit = traincapacity(g, who)                   # L39
            if g.armysize[index] > limit:                   # L40
                clrbot(g)
                s.print_text("Too many troops for railroad capacity")
                _toot(g, who)
                return

            target = g.armyloc[index]                       # L42
            x = _route(g, target, who)
            if x <= 1:                                      # check fails
                clrbot(g)                                   # L43
                s.print_text(f"Track from {g.city[target]} is blocked")
                _toot(g, who)
                return

            # aboard: destination selection loop            L44-51
            from_ = target                                  # L46
            x1 = from_
            if from_ == 0:
                _toot(g, who)
                return

            while True:                                     # aboard loop
                clrbot(g)                                   # L45
                s.print_text(
                    f"Select destination for {g.armyname[index]} from {g.city[target]}"
                )
                g.mtx[0] = "To"                             # L46

                x1 = newcity(g, from_)                      # L47
                if x1 == from_ or x1 == 0:
                    _toot(g, who)
                    return

                target_dest = x1                            # L49
                rx = _route(g, target_dest, who)
                if rx > 1:                                  # connected
                    break                                   # GOTO haul
                clrbot(g)                                   # L50
                s.print_text(
                    f"{g.armyname[index]}'s train cannot go to "
                    f"{g.city[x1]} - select another city"
                )
                tick(g, 9)
                # loop back to aboard

        else:
            # ── AI railroad move ──                        L5-35
            star, fin = starfin(g, who)                     # L5
            max_val = 32767
            index = 0

            for i in range(star, fin + 1):                  # L7
                if g.armyloc[i] == 0 or g.armymove[i] != 0:  # puter
                    continue

                # Count adjacent enemy cities               L8-9
                x_adj = 0
                for j in range(1, 7):
                    from_c = g.matrix[g.armyloc[i]][j]
                    if from_c > 0 and g.cityp[from_c] != who:
                        x_adj += 1

                if g.occupied[g.capcity[who]] > 0 and x_adj > 1:  # L10
                    continue  # puter

                defend = void(g, g.armyloc[i])              # L11

                if g.vicflag[5] > 0 and g.occupied[g.capcity[who]] == 0:  # L12
                    if defend > max_val:
                        defend = max_val - 1

                if defend < max_val:                         # L13
                    target = g.armyloc[i]
                    rx = _route(g, target, who)
                    if rx > 1:
                        max_val = defend
                        index = i

            if index == 0 or max_val > int(0.3 * g.armysize[index]):  # L15
                _toot(g, who)
                return

            limit = traincapacity(g, who)                   # L16
            if g.armysize[index] > limit:                   # L17
                _toot(g, who)
                return

            from_ = g.armyloc[index]                        # L18

            # Find destination                              L19-34
            x1 = 0
            for i in range(1, 41):                          # L19
                if g.cityp[i] != who:                       # puted
                    continue
                defend = void(g, i)                         # L20
                if defend == 0 or defend > 3 * g.armysize[index]:
                    continue  # puted
                if g.occupied[i] > 0:                       # L21
                    continue  # puted
                target = i                                  # L22
                rx = _route(g, target, who)                 # L23
                if rx == 0:
                    continue  # puted

                if g.side == UNION and g.cityy[i] < g.cityy[from_]:  # L24
                    x1 = i
                if g.side == CONFEDERATE and g.cityy[i] > g.cityy[from_]:  # L25
                    x1 = i
                if g.fort[i] > 0 and g.occupied[i] == 0:   # L26
                    x1 = i
                    break  # EXIT FOR

            # Capital defense check                         L28-34
            if g.vicflag[5] > 0 and g.occupied[g.capcity[who]] == 0:
                target = g.capcity[who]                     # L29
                rx = _route(g, target, who)
                if rx > 0:                                  # L30
                    defend = void(g, g.capcity[who])        # L31
                    if defend > 0:                          # L32
                        x1 = g.capcity[who]

            if x1 <= 0:                                     # L35
                _toot(g, who)
                return

        # ── haul: execute rail move ──                     L52-64
        s.color(11)                                         # L53
        clrbot(g)
        s.print_text(
            f"{g.armyname[index]} is taking the train from "
            f"{g.city[from_]} to {g.city[x1]}"
        )
        if g.player == 3:
            g.event_log.append({
                "type": "railroad_depart",
                "army_id": index,
                "from_city": g.armyloc[index],
                "dest_city": x1,
                "army_name": g.armyname[index],
                "side": UNION if index <= 20 else CONFEDERATE,
                "msg": f"{g.armyname[index]} is taking the train from {g.city[from_]} to {g.city[x1]}"
            })

        g.tracks[who] = g.armyloc[index]                    # L54
        from_ = g.armyloc[index]                            # L55
        g.rrfrom[who] = from_                               # L56
        g.rr[who] = index                                   # L57
        g.armyloc[index] = 0
        g.armymove[index] = x1

        tinytrain(g, who, 1)                                # L58
        if g.noise > 0:                                     # L59
            from cws_sound import qb_sound
            qb_sound(2222, 1)
        engine(g)                                           # L60

        occupy(g, from_)                                    # L62
        if g.occupied[from_] > 0:                           # L63
            placearmy(g, g.occupied[from_])

        _toot(g, who)                                       # L64
        return

    elif g.rr[who] > 0:                                     # L66: CASE IS > 0
        # ── Train arriving ──
        tinytrain(g, who, 0)                                # L67
        occupy(g, g.rrfrom[who])                            # L68
        if g.occupied[g.rrfrom[who]] > 0:                   # L69
            placearmy(g, g.occupied[g.rrfrom[who]])

        index = g.rr[who]                                   # L71
        g.tracks[who] = g.armymove[index]                   # L72
        tinytrain(g, who, 1)                                # L73

        g.rr[who] = 0                                       # L75
        g.armyloc[index] = g.armymove[index]
        g.armymove[index] = -1

        s.color(11)                                         # L76
        clrbot(g)
        s.print_text(
            f"Train with {g.armyname[index]} has arrived in "
            f"{g.city[g.armyloc[index]]}"
        )
        if g.player == 3:
            g.event_log.append({
                "type": "railroad_arrive",
                "army_id": index,
                "city": g.armyloc[index],
                "city_name": g.city[g.armyloc[index]],
                "army_name": g.armyname[index],
                "side": UNION if index <= 20 else CONFEDERATE,
                "msg": f"Train with {g.armyname[index]} arrived in {g.city[g.armyloc[index]]}"
            })
        if g.noise > 0:                                     # L76
            from cws_sound import qb_sound
            qb_sound(1200, 2)
        tick(g, g.turbo)                                    # L77

        x = g.cityx[g.armyloc[index]] - 12                 # L78
        y = g.cityy[g.armyloc[index]] - 11
        s.line(x - 9, y - 8, x + 10, y + 8, 2, "BF")      # L79

        if g.cityp[g.armyloc[index]] != who:                # L80
            capture(g, index, g.armyloc[index], who, 0)

        placearmy(g, index)                                 # L81

        if g.occupied[g.armyloc[index]] > 0:                # L82
            stax(g, who)
            _toot(g, who)
            return

        occupy(g, g.armyloc[index])                         # L83
        placearmy(g, index)
        _toot(g, who)                                       # L84
        return
