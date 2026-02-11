"""cws_army.py - Army management.
Direct port of cws_army.bm (300 lines).

Contains:
    armies(g)                  L1-26    - army movement orders
    armystat(g, index)         L27-37   - display army stats panel
    combine(g, who)            L38-119  - merge armies at a city
    cutoff(g, who, target)     L120-126 - count friendly adjacent cities
    movefrom(g)                L127-153 - select army/city to move from
    newarmy(g, who, empty, tgt) L154-169 - place newly recruited army
    placearmy(g, which)        L170-181 - draw army icon at city
    armyxy(g, x, y, z)        L182-200 - draw flag icon (Union/Confederate)
    cancel(g, side_)           L201-232 - cancel pending orders
    relieve(g, who)            L233-285 - replace army commander
    resupply(g, index)         L286-299 - resupply from treasury
"""

import random
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cws_globals import GameState


def _strong(g: 'GameState', index: int) -> str:
    """Army strength string: armysize * 100."""
    return f"{g.armysize[index]}00"


# ═══════════════════════════════════════════════════════════════════════════
#  SUB armyxy (x, y, z)                                        Lines 182-200
# ═══════════════════════════════════════════════════════════════════════════

def armyxy(g: 'GameState', x: int, y: int, z: int) -> None:
    """Draw army flag icon. z=1: Union, z=2: Confederate."""
    s = g.screen
    s.line(x - 5, y - 3, x + 10, y + 8, 0, "BF")         # L183: clear area

    if z == 1:                                              # L185: Union flag
        s.line(x - 7, y - 5, x + 7, y + 5, 4, "BF")      # L186: red bg
        s.line(x - 7, y - 5, x - 1, y, 1, "BF")           # L187: blue canton
        s.line(x, y - 2, x + 7, y - 1, 7, "B")            # L188: white stripe
        s.line(x - 7, y + 2, x + 7, y + 3, 7, "B")        # L189: white stripe
        s.line(x - 8, y - 6, x + 8, y + 6, 0, "B")        # L190: border

    elif z == 2:                                            # L191: Confederate flag
        s.line(x - 7, y - 5, x + 7, y + 5, 4, "BF")       # L192: red bg
        s.line(x - 8, y - 6, x + 8, y + 6, 0, "B")        # L193: border
        s.line(x - 7, y - 4, x + 6, y + 5, 9)             # L194: blue X
        s.line(x - 7, y + 4, x + 6, y - 5, 9)             # L195
        s.line(x - 7, y - 5, x + 7, y + 5, 9)             # L196
        s.line(x - 7, y + 5, x + 7, y - 5, 9)             # L197


# ═══════════════════════════════════════════════════════════════════════════
#  SUB placearmy (which)                                        Lines 170-181
# ═══════════════════════════════════════════════════════════════════════════

def placearmy(g: 'GameState', which: int) -> None:
    """Draw army icon at its current city position."""
    if which < 1 or which > 40:
        return
    if g.armyloc[which] < 1 or g.armyloc[which] > 40:
        return
    who = 1                                                 # L171
    if which > 20:
        who = 2
    x = g.cityx[g.armyloc[which]] - 12                     # L172
    y = g.cityy[g.armyloc[which]] - 11                     # L173
    armyxy(g, x, y, who)                                    # L174

    if g.supply[which] < 1:                                 # L175-180
        # Low supply indicator: small magenta 'S'
        sx = x - 3                                          # L176
        sy = y + 4
        g.screen.pset(sx, sy, 13)                           # L177
        # L178: DRAW font$(19) → simplified: draw small 'S'
        g.screen.line(sx + 1, sy - 2, sx + 4, sy - 2, 11)
        g.screen.line(sx, sy, sx + 3, sy, 11)
        g.screen.line(sx + 1, sy + 2, sx + 4, sy + 2, 11)


# ═══════════════════════════════════════════════════════════════════════════
#  SUB armystat (index)                                         Lines 27-37
# ═══════════════════════════════════════════════════════════════════════════

def armystat(g: 'GameState', index: int) -> None:
    """Display army statistics panel on the right side."""
    s = g.screen
    s.line(530, 60, 639, 150, 0, "BF")                     # L28
    s.color(15)                                             # L29
    s.locate(5, 68)                                         # L30
    s.print_text(g.armyname[index])
    c = 9                                                   # L31
    if index > 20:
        c = 7
    s.color(c)
    s.locate(6, 68)                                         # L32
    s.print_text(f"Size: {_strong(g, index)}")
    s.locate(7, 68)                                         # L33
    s.print_text(f"Leader:    {g.armylead[index]}")
    s.locate(8, 68)                                         # L34
    s.print_text(f"Exper:     {g.armyexper[index]}")
    if g.supply[index] < 2:                                 # L35
        s.color(12)
    s.locate(9, 68)                                         # L36
    s.print_text(f"Supply:    {g.supply[index]}")


# ═══════════════════════════════════════════════════════════════════════════
#  SUB cutoff (who, target, a)                                  Lines 120-126
# ═══════════════════════════════════════════════════════════════════════════

def cutoff(g: 'GameState', who: int, target: int) -> int:
    """Count friendly adjacent cities. Returns count (0 = cut off)."""
    a = 0                                                   # L121
    for j in range(1, 7):                                   # L122
        y = g.matrix[target][j]                             # L123
        if y > 0 and g.cityp[y] == who:                    # L124
            a += 1
    return a


# ═══════════════════════════════════════════════════════════════════════════
#  SUB movefrom (index, target)                                 Lines 127-153
# ═══════════════════════════════════════════════════════════════════════════

def movefrom(g: 'GameState') -> tuple:
    """Select army and city to move from. Returns (index, target).

    index=-1: no armies available, 0: cancelled.
    target=0: no city selected.
    """
    from cws_util import starfin, bubble
    from cws_ui import menu, clrrite

    s = g.screen
    g.colour = 3                                            # L128
    g.tlx = 67
    g.tly = 5
    index = 0
    g.size = 0
    target = 0

    who = g.side                                            # L129
    star, fin = starfin(g, who)

    for i in range(star, fin + 1):                          # L130-132
        if g.armyloc[i] > 0 and g.armymove[i] == 0:
            g.size += 1
            g.mtx[g.size] = g.city[g.armyloc[i]]
            g.array[g.size] = g.armyloc[i]

    if g.size == 0:                                         # L133
        return (-1, 0)

    g.mtx[0] = "From"                                      # L134
    bubble(g, g.size)                                       # L135

    # movopt:                                               L136-151
    g.tlx = 67                                              # L137
    g.tly = 5
    g.hilite = 15
    menu(g, 1)                                              # L138
    clrrite(g)

    if g.choose < 0:                                        # L139
        return (0, 0)

    target = g.array[g.choose]                              # L140

    # Find armies at this city                              L142-145
    g.size = 0
    for i in range(star, fin + 1):                          # L143
        if g.armyloc[i] == target and g.armymove[i] == 0:
            index = i                                       # L144
            g.size += 1
            g.mtx[g.size] = f"Army {i}"
            g.array[g.size] = i

    if g.size == 1:                                         # L146: only one army
        return (index, target)

    # Multiple armies: pick one                             L147-151
    g.mtx[0] = "Which"
    bubble(g, g.size)
    g.tlx = 67                                              # L149
    g.tly = 15
    menu(g, 4)
    clrrite(g)
    if g.choose < 0:                                        # L150
        return (0, 0)
    index = g.array[g.choose]                               # L151
    return (index, target)


# ═══════════════════════════════════════════════════════════════════════════
#  SUB armies                                                   Lines 1-26
# ═══════════════════════════════════════════════════════════════════════════

def armies(g: 'GameState') -> None:
    """Army movement orders: select army, destination, assign move."""
    from cws_util import tick, bubble
    from cws_ui import menu, clrbot, clrrite
    from cws_map import icon

    s = g.screen

    index, target = movefrom(g)                             # L2
    if target <= 0 or index <= 0:
        if index == -1:                                     # L3
            g.mflag = 1
        return                                              # dudd

    # tent:                                                 L5-24
    g.tlx = 67                                              # L6
    g.tly = 12
    armystat(g, index)                                      # L8
    s.color(11)                                             # L9
    s.locate(11, 68)
    s.print_text(g.city[target])

    g.size = 0                                              # L10
    g.mtx[0] = "To"                                         # L11
    for i in range(1, 7):                                   # L12
        if g.matrix[target][i] > 0:
            g.size += 1
            g.mtx[g.size] = g.city[g.matrix[target][i]]
            g.array[g.size] = g.matrix[target][i]
    bubble(g, g.size)                                       # L14

    g.hilite = 10                                           # L16
    g.colour = 3
    menu(g, 2)
    clrrite(g)

    if g.choose < 0:                                        # L17: dudd
        return

    # January campaign check                                L18
    if (g.month < 3 and g.jancam == 0 and
            g.cityp[g.array[g.choose]] != g.side):
        s.color(11)
        clrbot(g)
        s.print_text("No campaigns in January")
        tick(g, 9)
        clrbot(g)
        return                                              # dudd

    # Assign move                                           L20-24
    clrbot(g)
    s.print_text(
        f"Army {index} {g.armyname[index]} is moving from "
        f"{g.city[target]} to {g.city[g.array[g.choose]]}"
    )
    if g.noise > 0:                                         # L21
        from cws_sound import qb_sound
        qb_sound(2200, 0.5)
        qb_sound(2900, 0.7)
    icon(g, target, g.array[g.choose], 1)                   # L22
    g.armymove[index] = g.array[g.choose]                   # L23
    tick(g, g.turbo)
    clrbot(g)
    clrrite(g)                                              # L24


# ═══════════════════════════════════════════════════════════════════════════
#  SUB combine (who)                                            Lines 38-119
# ═══════════════════════════════════════════════════════════════════════════

def combine(g: 'GameState', who: int) -> int:
    """Combine armies at a city. Returns who (-1 if none available)."""
    from cws_util import starfin, tick, bubble, stax
    from cws_ui import menu, clrbot, clrrite
    from cws_map import icon, showcity

    s = g.screen
    g.colour = 3                                            # L39
    target = 0
    g.hilite = 3
    g.tlx = 67                                              # L40
    g.tly = 2
    star, fin = starfin(g, who)                             # L41

    g.size = 0                                              # L42
    for i in range(1, 41):                                  # L43
        if g.cityp[i] == who and g.occupied[i] > 0:        # L44
            for j in range(star, fin + 1):                  # L45
                if (g.armyloc[j] == i and
                        g.occupied[i] != j and
                        g.armymove[j] == 0):                # L46
                    g.size += 1
                    g.mtx[g.size] = g.city[i]
                    g.array[g.size] = i
                    break  # EXIT FOR

    if g.size == 0:                                         # L51
        return -1

    bubble(g, g.size)                                       # L52

    if who != g.side:                                       # L54: AI auto-pick
        g.choose = 1 + int(g.size * random.random())
    else:
        g.mtx[0] = "Join"                                  # L55
        g.choose = 31                                       # L56
        g.hilite = 11
        menu(g, 9)                                          # L57
        clrrite(g)

    # join:                                                 L58
    if g.choose < 1:                                        # L59: nocity2
        return who

    target = g.array[g.choose]                              # L60
    clrbot(g)                                               # L61
    s.print_text(f"Combining {g.force[who]} armies in {g.city[target]}")
    tick(g, g.turbo)

    # Initialize temporary army 0                           L63-64
    g.armysize[0] = 0
    g.armylead[0] = 0
    g.armyexper[0] = 0
    g.armyloc[0] = target
    g.armyname[0] = ""
    g.supply[0] = 0
    g.armymove[0] = 0

    best = 0                                                # L66
    x_lead = 0
    spin = 0

    for j in range(star, fin + 1):                          # L67
        # dork1 check                                       L68
        if g.armymove[j] != 0 or g.armyloc[j] != target or g.armysize[j] == 0:
            continue

        if g.armysize[0] + g.armysize[j] > 1250:           # L69
            clrbot(g)
            s.print_text(f"Cannot combine {g.armyname[j]}... TOO LARGE")
            tick(g, g.turbo)
            continue

        if g.armylead[j] > x_lead:                          # L71-76
            x_lead = g.armylead[j]
            g.armyname[0] = g.armyname[j]
            g.armylead[0] = g.armylead[j]
            best = j

        g.armysize[0] += g.armysize[j]                     # L78
        if g.armysize[0] < 1:                               # L79
            continue

        pct = g.armysize[j] / g.armysize[0]                # L80
        spin += 1                                           # L81
        g.armyexper[0] = int((1 - pct) * g.armyexper[0] + pct * g.armyexper[j])  # L82

        clrbot(g)                                           # L83
        s.print_text(f"{g.armyname[j]} is combining his {_strong(g, j)} forces")
        tick(g, g.turbo)

        g.supply[0] += g.supply[j]                          # L84
        if g.supply[0] > 10:                                # L85
            g.supply[0] = 10

        # Clear merged army                                 L86-88
        g.armysize[j] = 0
        g.armyloc[j] = 0
        g.armyexper[j] = 0
        g.armymove[j] = 0
        g.lname[j] = g.armyname[j]                         # L87
        g.armylead[j] = 0                                   # L88
        g.supply[j] = 0
        g.armyname[j] = ""

    # Apply merged result                                   L92-117
    clrbot(g)                                               # L92
    if who != g.side and spin == 0:                         # L93
        return who
    if spin == 0:                                           # L94
        s.print_text(f"No valid armies to combine at this time in {g.city[target]}")
        tick(g, g.turbo)
        return who

    g.armysize[best] = g.armysize[0]                        # L99
    g.armylead[best] = g.armylead[0]
    g.armyexper[best] = g.armyexper[0]                      # L100
    g.supply[best] = g.supply[0]
    g.armyloc[best] = target                                # L101
    g.armyname[best] = g.armyname[0]                        # L102
    g.lname[best] = ""                                      # L103

    if spin > 1:                                            # L104
        s.print_text(
            f"New army {best} of {_strong(g, best)} is commanded by {g.armyname[best]}"
        )
        g.armymove[best] = -1                               # L106
    else:                                                   # L107
        s.print_text("Only 1 eligible army -- cannot combine at this time")

    if who == g.side:                                       # L110
        tick(g, g.turbo)
    if g.noise > 0:                                         # L111
        from cws_sound import qb_sound
        qb_sound(4000, 0.7)

    showcity(g)                                             # L113
    placearmy(g, best)                                      # L114
    icon(g, target, 0, 6)                                   # L115
    g.occupied[target] = best                               # L116
    stax(g, who)                                            # L117
    return who


# ═══════════════════════════════════════════════════════════════════════════
#  SUB newarmy (who, empty, target)                             Lines 154-169
# ═══════════════════════════════════════════════════════════════════════════

def newarmy(g: 'GameState', who: int, empty: int, target: int) -> None:
    """Place a newly recruited army at target city."""
    from cws_util import tick

    s = g.screen

    g.supply[empty] = int(3 + 5 * random.random())         # L155
    if who == 1:
        g.supply[empty] += 2
    g.armyexper[empty] = 1                                  # L156
    if who == 2:
        g.armyexper[empty] = 2
    g.armylead[empty] = g.rating[empty]                     # L157
    g.armyname[empty] = g.lname[empty]                      # L158
    g.lname[empty] = ""

    s.color(12)                                             # L159
    from cws_ui import clrbot
    clrbot(g)
    s.print_text(f"Placing NEW army {empty} {g.armyname[empty]} in {g.city[target]}")

    x = 70                                                  # L161
    if g.realism > 0:
        x = 3 * g.cityv[target] + 33
    a = cutoff(g, who, target)                              # L162
    if a < 1:
        x = x // 3

    g.occupied[target] = empty                              # L163
    g.armysize[empty] = x
    s.print_text(f" Size = {_strong(g, empty)}")            # L164
    g.cash[who] -= 100                                      # L165
    if g.noise > 0:
        from cws_sound import qb_sound
        qb_sound(2222, 0.5)
    g.armyloc[empty] = target                               # L166
    placearmy(g, empty)
    tick(g, max(0, g.turbo - 0.5))                          # L167
    g.armymove[empty] = -1                                  # L168


# ═══════════════════════════════════════════════════════════════════════════
#  SUB cancel (side)                                            Lines 201-232
# ═══════════════════════════════════════════════════════════════════════════

def cancel(g: 'GameState', side_: int) -> None:
    """Cancel pending army orders."""
    from cws_util import starfin, tick, bubble, stax
    from cws_ui import menu, clrbot, clrrite
    from cws_map import icon

    s = g.screen
    star, fin = starfin(g, side_)                           # L202

    clrrite(g)                                              # L204
    g.size = 0                                              # L205
    for j in range(star, fin + 1):                          # L206
        a_str = g.armyname[j]                               # L207
        if len(a_str) > 10:
            sp = a_str.find(" ")
            if sp >= 0:
                a_str = a_str[sp + 1:]
        if g.armyloc[j] > 0 and g.armymove[j] > 0:         # L208
            g.size += 1
            g.mtx[g.size] = a_str
            g.array[g.size] = g.armyloc[j]

    bubble(g, g.size)                                       # L210
    g.tlx = 67                                              # L211
    g.tly = 2
    g.wtype = 2
    g.mtx[0] = "Cancel"                                    # L212

    if g.size < 1:                                          # L213
        clrbot(g)
        s.color(11)
        s.print_text("No units have orders to cancel")
        return

    menu(g, 1)                                              # L214

    if 1 <= g.choose <= g.size:                             # L216
        target = g.array[g.choose]                          # L217
        index = 0
        for i in range(star, fin + 1):                      # L219
            if g.armyloc[i] == target:                      # L220
                if g.mtx[g.choose] in g.armyname[i] and g.armymove[i] > 0:
                    index = i

        if index > 0:
            clrbot(g)                                       # L223
            s.color(11)
            s.print_text(
                f"{g.armyname[index]} has cancelled move to {g.city[g.armymove[index]]}"
            )
            tick(g, g.turbo + 1)
            icon(g, g.armyloc[index], g.armymove[index], 4)  # L224
            g.armymove[index] = 0                           # L225
            if g.noise > 0:
                from cws_sound import qb_sound
                qb_sound(2999, 0.5)
            stax(g, side_)                                  # L226

    clrrite(g)                                              # L231


# ═══════════════════════════════════════════════════════════════════════════
#  SUB relieve (who)                                            Lines 233-285
# ═══════════════════════════════════════════════════════════════════════════

def relieve(g: 'GameState', who: int) -> None:
    """Replace army commander."""
    from cws_util import starfin, tick, bubble
    from cws_ui import menu, clrbot, clrrite
    from cws_map import icon

    s = g.screen
    g.colour = 3                                            # L234
    g.hilite = 3
    g.tlx = 67                                              # L235
    g.tly = 2
    star, fin = starfin(g, who)                             # L236

    g.size = 0                                              # L237
    for i in range(star, fin + 1):                          # L238
        if g.armysize[i] > 0 and g.armyloc[i] > 0 and g.armymove[i] == 0:
            g.size += 1                                     # L240
            g.mtx[g.size] = g.armyname[i]                   # L241
            if len(g.mtx[g.size]) > 11:                     # L242
                g.mtx[g.size] = g.mtx[g.size][:11]
            g.array[g.size] = i                             # L243

    if g.size == 0:                                         # L247
        return
    bubble(g, g.size)                                       # L248
    g.mtx[0] = "Relieve"                                   # L249
    g.choose = 31                                           # L250
    g.hilite = 11
    menu(g, 6)                                              # L251
    clrrite(g)

    if g.choose < 1:                                        # L253
        return
    index = g.array[g.choose]                               # L254
    icon(g, g.armyloc[index], 0, 9)                         # L255

    t_name = g.armyname[index]                              # L257
    g.lname[index] = t_name                                 # L258

    # Build available leaders list                          L260-268
    g.size = 0
    for i in range(star, fin + 1):                          # L261
        if g.lname[i] != "":                                # L262
            g.size += 1                                     # L263
            g.mtx[g.size] = g.lname[i]                      # L264
            if len(g.mtx[g.size]) > 11:                     # L265
                g.mtx[g.size] = g.mtx[g.size][:11]
            g.array[g.size] = i                             # L266
    bubble(g, g.size)                                       # L269

    # have2: loop until valid choice                        L271-275
    while True:
        g.mtx[0] = "New Leader"                             # L272
        g.tlx = 67                                          # L273
        g.tly = 2
        menu(g, 0)                                          # L274
        clrrite(g)
        if g.choose >= 1:                                   # L275
            break

    g.armymove[index] = -1                                  # L276
    g.armylead[index] = g.rating[g.array[g.choose]]         # L277
    if g.armylead[index] > 0:                               # L278
        g.armylead[index] -= 1
    if g.armyexper[index] > 0:                              # L279
        g.armyexper[index] -= 1

    s.color(15)                                             # L280
    clrbot(g)
    s.print_text(
        f"{g.lname[g.array[g.choose]]} has replaced {t_name} "
        f"in {g.city[g.armyloc[index]]}"
    )
    tick(g, 9)

    g.armyname[index] = g.lname[g.array[g.choose]]         # L281
    g.lname[g.array[g.choose]] = ""                         # L282
    icon(g, g.armyloc[index], 0, 8)                         # L283
    clrbot(g)                                               # L284


# ═══════════════════════════════════════════════════════════════════════════
#  SUB resupply (index)                                         Lines 286-299
# ═══════════════════════════════════════════════════════════════════════════

def resupply(g: 'GameState', index: int) -> None:
    """Resupply army from treasury."""
    from cws_util import tick
    from cws_ui import clrbot

    s = g.screen
    who = 1                                                 # L287
    if index > 20:
        who = 2

    if g.realism > 0:                                       # L288
        a = cutoff(g, who, g.armyloc[index])                # L289
        if a < 1:                                           # L290
            return

    x = 0                                                   # L292
    if g.armysize[index] > 0:
        x = int(g.cash[who] / g.armysize[index] * 10)
    y = x + g.supply[index]                                 # L293
    if y > 5:
        x = 5 - g.supply[index]
    if x < 1:                                               # L294
        clrbot(g)
        s.print_text(f"Not enough funds in the Treasury to supply {g.armyname[index]}")
    else:
        g.supply[index] += x                                # L295
        g.cash[who] -= int(0.1 * x * g.armysize[index])
        clrbot(g)                                           # L296
        s.print_text(f"{g.armyname[index]} has received supplies")
        if g.noise > 0:                                    # L296
            from cws_sound import qb_sound
            qb_sound(4500, 0.5)

    tick(g, g.turbo)                                        # L298
    if g.cash[who] < 0:
        g.cash[who] = 0
