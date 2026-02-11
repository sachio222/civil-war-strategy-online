"""cws_flow.py - Game flow: events, victory, turn progression.
Direct port of cws_flow.bm (438 lines).

Contains:
    iterate(g)              L1-37    - monthly iteration
    endit(g)                L38-71   - victory condition toggle
    engine(g)               L72-88   - train status display
    events(g)               L89-237  - random special events
    victor(g)               L238-365 - victory check / game end
    rwin(g)                 L366-437 - confederate win screen
"""

import random
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cws_globals import GameState


# ═══════════════════════════════════════════════════════════════════════════
#  SUB iterate                                                  Lines 1-37
# ═══════════════════════════════════════════════════════════════════════════

def iterate(g: 'GameState') -> None:
    """Monthly iteration: place armies, advance month, supply, aggression."""
    from cws_army import placearmy, cutoff
    from cws_util import tick, stax
    from cws_ui import clrbot

    s = g.screen

    # Place all active armies                               L3-4
    for i in range(1, 41):
        if g.armyloc[i] > 0:
            placearmy(g, i)

    # Advance month                                         L6-7
    g.month += 2
    if g.month > 12:
        g.month = 1
        g.year += 1

    # Supply maintenance                                    L9-31
    side_s = 1                                              # L9
    for i in range(1, 41):                                  # L10
        if g.armyloc[i] < 1:                                # rip
            continue
        if i > 20:                                          # L11
            side_s = 2

        # Auto resupply from treasury                       L12-18
        if g.cash[side_s] >= 0.2 * g.armysize[i]:          # L12
            a = 1                                           # L13
            if g.realism > 0:
                a = cutoff(g, side_s, g.armyloc[i])
            if a > 0:                                       # L14
                g.supply[i] += 1                            # L15
                g.cash[side_s] -= int(0.2 * g.armysize[i])  # L16

        # Winter supply drain                               L19
        if (g.month < 7 or g.month > 10) and g.matrix[g.armyloc[i]][7] < 99:
            g.supply[i] -= 1

        # Naval blockade supply drain                       L20
        if (g.matrix[g.armyloc[i]][7] == 99 and
                g.navyloc[3 - side_s] == g.armyloc[i]):
            g.supply[i] -= 1
            clrbot(g)
            s.print_text(f"{g.armyname[i]} is blockaded")
            tick(g, g.turbo)

        # Out of supplies                                   L21-29
        s.color(13)                                         # L21
        if g.supply[i] < 1:                                 # L22
            g.supply[i] = 0                                 # L23
            clrbot(g)                                       # L24
            s.print_text(f"{g.armyname[i]} is out of supplies")
            placearmy(g, i)                                 # L26
            tick(g, g.turbo)                                # L27
            if random.random() > 0.8 and g.armysize[i] > 50:  # L28
                g.armysize[i] = int(0.9 * g.armysize[i])

    # Update status displays                                L32
    for k in range(1, 3):
        stax(g, k)

    # Calculate aggression ratio                            L33-36
    y = 0                                                   # L33
    for i in range(1, 21):
        y += 0.1 * g.armysize[i]
    x = 0                                                   # L34
    for i in range(21, 41):
        x += 0.1 * g.armysize[i]

    if g.side == 2 and x > 0:                              # L35
        g.aggress = y / x
    else:
        g.aggress = 1.0
    if g.side == 1 and y > 0:                              # L36
        g.aggress = x / y
    elif g.side == 1:
        g.aggress = 1.0


# ═══════════════════════════════════════════════════════════════════════════
#  SUB endit                                                    Lines 38-71
# ═══════════════════════════════════════════════════════════════════════════

def endit(g: 'GameState') -> None:
    """Victory condition toggle menu."""
    from cws_ui import menu, center
    from cws_map import usa

    s = g.screen

    a_str = f"{abs(g.vicflag[3]) * 2.5}% Cities"           # L39
    t_str = f"{abs(g.vicflag[3]) * 2.5}% Total Income"     # L40
    mtx8 = f"Time: {g.month_names[g.vicflag[1]]} {abs(g.vicflag[2])}"  # L41
    mtx9 = f"{abs(g.vicflag[6])}:1 Force Ratio"            # L42

    s.color(15)                                             # L43
    s.locate(1, 1)
    s.print_text("Press ENTER to toggle ending conditions")
    s.color(14)                                             # L44
    s.print_text("                ESC when done")

    chosit = 0

    # what4: loop                                           L45-67
    while True:
        for i in range(2, 7):                               # L46
            if g.vicflag[i] > 0:
                g.mtx[i - 1] = "+ "
            else:
                g.mtx[i - 1] = "  "

        g.choose = chosit                                   # L48
        g.mtx[0] = "Victory Conditions"                    # L49
        g.mtx[1] = g.mtx[1] + mtx8                          # L50
        g.mtx[2] = g.mtx[2] + a_str                         # L51
        g.mtx[3] = g.mtx[3] + t_str                         # L52
        g.mtx[4] = g.mtx[4] + "Capital Captured"            # L53
        g.mtx[5] = g.mtx[5] + mtx9                          # L54
        g.mtx[6] = "DONE"                                   # L55

        g.wtype = 2                                         # L56
        g.colour = 3
        g.size = 6
        g.hilite = 14
        menu(g, 0)                                          # L57
        chosit = 21 + g.choose                              # L58

        if g.choose == 1:                                   # L60
            g.vicflag[2] = -g.vicflag[2]                    # L61
        elif 2 <= g.choose <= 5:                            # L62
            g.vicflag[g.choose + 1] = -g.vicflag[g.choose + 1]  # L63
        else:                                               # L64: cheer
            break

    # cheer:                                                L68-70
    s.cls()                                                 # L69
    usa(g)                                                  # L70


# ═══════════════════════════════════════════════════════════════════════════
#  SUB engine                                                   Lines 72-88
# ═══════════════════════════════════════════════════════════════════════════

def engine(g: 'GameState') -> None:
    """Display train status indicators in top-left corner."""
    s = g.screen
    if g.rr[1] + g.rr[2] == 0:                             # L73: notrain
        return
    s.line(5, 17, 100, 63, 3, "BF")                        # L74
    s.line(5, 17, 100, 47, 0, "B")                          # L75
    s.line(5, 47, 100, 63, 0, "B")                          # L76

    for i in range(1, 3):                                   # L78
        if g.rr[i] == 0:                                    # L79: notrane
            continue
        c = 9                                               # L80
        if i == 2:
            c = 15
        bx = 15 if i == 1 else 60
        s.pset(bx, 25, 3)                                   # L80: set cursor
        if i == 2:
            s.pset(60, 25, 3)
        # L81: DRAW train outline in black, scale S4 (1:1)
        s.draw("C0S4R9D4R6U3R3D3R7U5H3U2R9D3G2D6F1D3F5"
               "L10D1G1L4H2L7G2L3H2L3U8L2U5BF4")
        # L82: PAINT fill interior with side color, bounded by black
        fx, fy = s._last_x, s._last_y
        s.paint(fx, fy, c, 0)
        # Destination text                                  L83
        dest = ""
        if g.rr[i] > 0 and g.armymove[g.rr[i]] > 0:
            dest = g.city[g.armymove[g.rr[i]]][:5]
        s.locate(4, 6 * (i - 1) + 2)
        s.print_text(dest)


# ═══════════════════════════════════════════════════════════════════════════
#  GOSUB riot (L161-178)
# ═══════════════════════════════════════════════════════════════════════════

def _riot(g: 'GameState', who: int) -> bool:
    """Riot event. Returns True if riot occurred, False otherwise."""
    from cws_util import tick
    from cws_ui import clrbot, scribe
    from cws_map import showcity, image2

    s = g.screen

    if g.realism == 0:                                      # L162
        return False
    if g.control[who] == 1:                                 # L163
        return False  # EXIT SUB equivalent

    for k in range(1, 100):                                 # L164
        x = 1 + int(40 * random.random())                   # L165
        if (g.cityo[x] != who and g.cityp[x] == who and
                g.occupied[x] == 0):                        # L166
            clrbot(g)                                       # L167
            s.color(15)
            s.print_text(f" Riots have broken out in {g.city[x]}")
            g.cityp[x] = 0                                 # L169
            showcity(g)                                     # L170
            tick(g, g.turbo)                                # L171
            clrbot(g)                                       # L172
            image2(g, f"{g.city[x]} is now NEUTRAL !", 4)   # L173
            tick(g, g.turbo)                                # L174
            return True                                     # L175
    return False


# ═══════════════════════════════════════════════════════════════════════════
#  SUB events                                                   Lines 89-237
# ═══════════════════════════════════════════════════════════════════════════

def events(g: 'GameState') -> None:
    """Random special events."""
    from cws_util import tick
    from cws_ui import clrbot, scribe
    from cws_navy import ships
    from cws_map import usa

    s = g.screen

    # Ironclad announcement                                 L93-98
    if g.realism > 0 and g.year == 1862 and g.month < 3:
        s.color(14)
        clrbot(g)
        s.print_text("SPECIAL DEVELOPMENT : IRONCLAD ships now available")
        if g.noise > 0:                                     # L96
            from cws_sound import qb_sound
            for k in range(5):
                qb_sound(140, 1)
                qb_sound(37, 1)
        _wait_key(g)                                        # L97
        return

    if g.randbal == 0:                                      # L100
        return

    plus = g.difficult                                      # L101
    if g.side == 1:
        plus = 6 - g.difficult
    pct = 0.005 * (g.year - 1860) * plus * plus             # L102
    if pct > 0.9:
        pct = 0.9
    if random.random() > pct:                               # L103
        return

    clrbot(g)                                               # L105
    s.color(14)
    s.print_text("SPECIAL EVENT...")

    who = 1                                                 # L106
    if random.random() > 0.1 * g.randbal:
        who = 2

    if who == 1:
        # ── CASE 1: Confederate events ──                  L112-159
        if g.year == 1864 and g.month == 1:                 # L113
            g.victory[2] += 50
        if g.year == 1865 and g.month == 1:                 # L114
            g.victory[2] += 100

        if random.random() > 0.9:                           # L115
            if _riot(g, who):
                return

        clrbot(g)                                           # L117

        if random.random() <= 0.2 and g.navysize[2] <= 9:  # L118
            # English ships for South
            empty = 0
            if g.navysize[2] > 0 and g.navyloc[2] != 99:   # L119
                empty = g.navyloc[2]
            else:
                for i in range(1, 41):                      # L121
                    if (g.cityp[i] == 2 and
                            g.matrix[i][7] == 99 and
                            g.navyloc[1] != i):             # L122
                        empty = i
                        break

            if empty > 0:                                   # L124 → float1/dull1
                scribe(g, "England has given ships to the South", 2)  # L126
                g.navysize[2] += 2 * plus                   # L127
                if g.navysize[2] > 10:                      # L128
                    g.navysize[2] = 10
                x = g.navysize[2] - len(g.fleet[2])        # L129
                if x > 0:
                    g.fleet[2] += "W" * x                   # L130
                g.navyloc[2] = empty                        # L131
                ships(g)
                _dull1(g)
                return

        # mercen:                                           L133
        if random.random() <= 0.1 and g.control[2] >= 30:   # L134
            a_name = "French"                               # L135
            if random.random() > 0.5:
                a_name = "British"
            # Find a random Confederate army                L136
            # Bug preserved: original uses undefined 'index'
            index = 0
            for i in range(21, 41):
                if g.armysize[i] > 0 and g.armyloc[i] > 0:
                    index = i
                    break
            if index > 0:
                scribe(g, f"{a_name} mercenaries join {g.armyname[index]}'s army", 2)
                g.armysize[index] += 100 * plus             # L137
                g.armyexper[index] = 10                     # L138
                g.supply[index] = 10
                _dull1(g)
                return

        # money:                                            L140
        if random.random() <= 0.3 and g.control[2] >= 12:   # L141
            scribe(g, "The South has obtained a loan from Europe", 2)
            g.cash[2] += 100 * plus                         # L148: purse
            _dull1(g)
            return

        # cotton:                                           L144
        if random.random() <= 0.5 and g.control[2] >= 12:   # L145
            scribe(g, "Cash from cotton sales fill the Rebel Treasury", 2)
            g.cash[2] += 100 * plus                         # L148: purse
            _dull1(g)
            return

        # uprising:                                         L150
        pct_val = 0.9                                       # L151
        a_msg = "Union troops diverted to fight Western Indian uprisings"  # L152
        if random.random() > 0.5:                           # L153
            a_msg = "Union 90-day enlistees return home"
        if g.year == 1864 and g.month > 5:                  # L154
            a_msg = "20% of Union forces take furloughs to vote in 1864 elections"
            pct_val = 0.8
        scribe(g, a_msg, 2)                                 # L155
        for k in range(1, 21):                              # L156
            g.armysize[k] = int(pct_val * g.armysize[k])   # L157
        _dull1(g)
        return

    elif who == 2:
        # ── CASE 2: Union events ──                        L182-227
        if (random.random() <= 0.1 and g.navyloc[1] != 0 and
                g.navysize[1] <= 9):                        # L183
            if random.random() > 0.95:                      # L184
                if _riot(g, who):
                    return
            scribe(g, "Union shipworks have produced extra ships", 2)  # L185
            g.navysize[1] += plus                           # L186
            if g.navysize[1] > 10:                          # L187
                g.navysize[1] = 10
            x = g.navysize[1] - len(g.fleet[1])            # L188
            if x > 0:
                g.fleet[1] += "W" * x                       # L189
            _dull2(g)
            return

        # event2:                                           L191
        if random.random() >= 0.7:                          # L192
            scribe(g, "Volunteer troops swell the Union ranks", 2)  # L193
            x_count = 0                                     # L194
            for i in range(1, 21):
                x_count += 1
                if x_count > 5:
                    break
                if g.armysize[i] > 0 and random.random() > 0.5:  # L195
                    g.armysize[i] = int(g.armysize[i] * 1.1 + plus)
            _dull2(g)
            return

        # abe:                                              L197
        if g.emancipate == 0 and g.year > 1862:            # L198
            g.emancipate = 1                                # L200
            scribe(g, "Abraham Lincoln announces the Emancipation Proclamation", 2)
            g.victory[1] += 100                             # L202
            g.victory[2] -= 100
            usa(g)                                          # L203
            _dull2(g)
            return

        if g.year == 1864 and g.month == 11:               # L206
            scribe(g, "Lincoln has been reelected", 2)       # L207
            g.victory[2] = int(0.5 * g.victory[2])          # L208
            _dull2(g)
            return

        if random.random() > 0.5:                           # L211
            scribe(g, "Wealthy Unionists give generously to the Federal Cause", 2)
            g.cash[1] += 100 * plus                         # L213
            _dull2(g)
            return

        if random.random() > 0.5 and g.year > 1861:        # L216
            scribe(g, "Rebel deserters leave the battlefield to go home", 2)
            for i in range(21, 41):                         # L218
                g.armysize[i] = int(0.92 * g.armysize[i])
            _dull2(g)
            return

        if random.random() > 0.5 and g.year > 1861:        # L220
            scribe(g, "Union soldiers now have repeating rifles", 2)
            for i in range(1, 21):                          # L222
                if g.armyexper[i] < 9:                      # L223
                    g.armyexper[i] += 2

        scribe(g, "Secretary of War Stanton predicts the end of the Rebellion", 2)  # L226
        g.victory[1] += 10                                  # L227
        _dull2(g)
        return


def _dull1(g: 'GameState') -> None:
    """dull1: Confederate event cleanup (L234-236). Music + wait."""
    if g.noise == 2:                                        # L235
        from cws_sound import qb_play
        qb_play("MNMFT160o2L16geL8ccL16cdefL8ggge")
    _wait_key(g)


def _dull2(g: 'GameState') -> None:
    """dull2: Union event cleanup (L231-233). Music + wait."""
    if g.noise == 2:                                        # L232
        from cws_sound import qb_play
        qb_play("MNMFL16o2T120dd.dd.co1b.o2do3g.ab.bb.ag")
    _wait_key(g)


def _wait_key(g: 'GameState') -> None:
    """Wait for any key press (DO WHILE INKEY$="": LOOP)."""
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


# ═══════════════════════════════════════════════════════════════════════════
#  SUB victor                                                   Lines 238-365
# ═══════════════════════════════════════════════════════════════════════════

def victor(g: 'GameState') -> None:
    """Check victory conditions and potentially end the game."""
    from cws_ui import menu, clrbot, center
    from cws_map import usa, image2
    from cws_misc import capitol, maxx
    from cws_report import report

    s = g.screen

    # Count total army strengths                            L239-242
    x = 0                                                   # Union
    for j in range(1, 21):
        if g.armyloc[j] > 0:
            x += g.armysize[j]
    y = 0                                                   # Confederate
    for j in range(21, 41):
        if g.armyloc[j] > 0:
            y += g.armysize[j]

    clrbot(g)                                               # L244
    s.color(14)

    # Time warning                                          L245-248
    if (g.vicflag[2] > 0 and g.year >= g.vicflag[2] and
            g.month < g.vicflag[1]):
        a_msg = (f"Time almost expired "
                 f"({g.month_names[g.vicflag[1]]},{g.vicflag[2]})")
        image2(g, a_msg, 4)                                 # L247

    # Check each side                                       L249
    for i in range(1, 3):
        j = 0
        a_str = ""

        # Annihilation check                                L250
        if (i == 1 and y == 0) or (i == 2 and x == 0):
            j = 7
            g.victory[i] += 300

        # Time expired                                      L252
        elif (g.year >= g.vicflag[2] and g.month >= g.vicflag[1] and
              g.vicflag[2] > 0):
            j = 2

        # City control                                      L253
        elif g.control[i] >= g.vicflag[3] and g.vicflag[3] > 0:
            j = 3

        # Income percentage                                 L254
        elif (g.vicflag[4] > 0 and
              (g.income[1] + g.income[2]) > 0 and
              g.income[i] / (g.income[1] + g.income[2]) >= 0.01 * g.vicflag[4]):
            j = 4

        # Capital captured                                  L255
        elif (g.vicflag[5] > 0 and
              g.capcity[3 - i] == 0 and g.capcity[i] > 0):
            j = 5

        # Force ratio                                       L257-266
        elif g.vicflag[6] > 0:
            if i == 1:
                if y == 0:                                  # L259
                    j = 7
                elif x / y > g.vicflag[6]:                  # L260
                    j = 6
            if i == 2:
                if x == 0:                                  # L263
                    j = 7
                elif y / x > g.vicflag[6]:                  # L264
                    j = 6

        if j > 0:
            # ── finis: victory achieved ──                 L287-362
            # Determine victory description                 L288-301
            if j < 3:                                       # L289
                a_str = "TIME EXPIRED"
            elif j == 3:                                    # L291
                a_str = f"{2.5 * g.vicflag[3]}% CITIES CONTROLLED"
            elif j == 4:                                    # L293
                a_str = f"{g.vicflag[4]} % OF TOTAL INCOME"
            elif j == 5:                                    # L295
                a_str = "CAPITAL CAPTURED"
            elif j == 6:                                    # L297
                a_str = f"{g.vicflag[6]}:1 ARMY STRENGTH RATIO"
            elif j == 7:                                    # L299
                a_str = "ENEMY ANNIHILATED"

            # Display victory screen                        L302-326
            s.cls()                                         # L302 (CLS)
            c = 1                                           # L303
            if i == 2:
                c = 7
            s.line(0, 0, 639, 479, 4, "BF")                # L304
            s.line(0, 40, 550, 460, 0, "BF")               # L305
            usa(g)                                          # L306
            s.line(70, 140, 485, 265, 0, "BF")             # L307
            s.line(50, 120, 465, 250, c, "BF")             # L308
            s.line(50, 120, 465, 250, 4, "B")              # L309
            s.color(14)                                     # L310

            t_str = f"{g.force[i]} SIDE IS WINNING"         # L311
            if j == 2:                                      # L312
                center(g, 10, "Confederates will win a technical victory")
            else:
                center(g, 10, t_str)

            s.color(15)                                     # L314
            t2 = f"END GAME VICTORY CONDITION {j - 1} REACHED"  # L315
            center(g, 12, t2)                               # L316
            center(g, 14, a_str)                            # L317

            # End game menu                                 L319-347
            g.mtx[0] = "End Game"                           # L319
            g.mtx[1] = "Yes"                                # L320
            g.mtx[2] = "No-Override"                        # L321
            g.size = 2                                      # L322
            g.colour = 4
            g.tlx = 27                                      # L323
            g.tly = 18
            g.hilite = 15                                   # L324
            if j == 7:                                      # L325
                g.size = 1
            menu(g, 0)                                      # L326

            if g.choose != 1 and j < 7:                    # L328: play4ever
                g.vicflag[j] += 1                           # L330
                if j == 5:                                  # L331
                    g.vicflag[j] = 0
                s.cls()                                     # L332
                usa(g)                                      # L333
                return                                      # L334

            # Confirm end or play more                      L336-347
            g.mtx[0] = "Options"                            # L336
            g.mtx[1] = "Quit this Game"                     # L337
            g.mtx[2] = "Play More"                          # L338
            if g.player == 1:                               # L339
                g.mtx[2] = f"No - Press Onward to {g.city[g.capcity[3 - g.side]]}"
            g.size = 2                                      # L340
            g.colour = 8
            g.tlx = 27                                      # L341
            g.tly = 18

            if j != 7:                                      # L342
                menu(g, 0)                                  # L343
                if g.choose != 1:                           # L344: play4ever
                    g.vicflag[j] += 1
                    if j == 5:
                        g.vicflag[j] = 0
                    s.cls()
                    usa(g)
                    return
            else:                                           # L345
                g.victory[i] += 100                         # L346

            # Game over                                     L349-362
            g.thrill = i                                    # L349
            usa(g)                                          # L350
            report(g, 100 + g.side)

            if j == 2:                                      # L351
                for k in range(1, 3):
                    g.victory[k] = int(0.7 * g.victory[k])
                rwin(g)
                # death:
                s.color(14)                                 # L356
                s.locate(4, int(40 - 0.5 * len(a_str)))
                if g.history > 0:                           # L357
                    from cws_ui import scribe as ui_scribe
                    ui_scribe(g, t_str, 0)                  # L358
                    ui_scribe(g, a_str, 0)                  # L359
                s.print_text(a_str)                         # L361
                maxx(g)
                return

            t_str = ""
            if i == 1:                                      # L353
                capitol(g)
                s.color(15)
                s.locate(2, 27)
                t_str = f"UNION VICTORY  VP's={g.victory[1]}"
                s.print_text(t_str)
            elif i == 2:                                    # L354
                rwin(g)
                s.color(15)
                s.locate(2, 27)
                t_str = f"REBEL VICTORY  VP's={g.victory[2]}"
                s.print_text(t_str)

            # death:                                        L355-362
            s.color(14)                                     # L356
            s.locate(4, int(40 - 0.5 * len(a_str)))
            if g.history > 0:                               # L357
                from cws_ui import scribe as ui_scribe
                ui_scribe(g, t_str, 0)                      # L358
                ui_scribe(g, a_str, 0)                      # L359
            s.print_text(a_str)                             # L361
            maxx(g)
            return

        else:
            # stale: near-victory warnings                  L268-284
            clrbot(g)                                       # L268
            s.color(14)

            if (g.vicflag[3] > 0 and
                    g.control[i] >= 0.9 * g.vicflag[3]):    # L269
                a_msg = (f"{g.force[i]} side almost controls"
                         f" {g.vicflag[3]} cities")
                image2(g, a_msg, 4)                         # L271

            if (g.vicflag[4] > 0 and
                    (g.income[1] + g.income[2]) > 0 and
                    g.income[i] / (g.income[1] + g.income[2]) >= 0.009 * g.vicflag[4]):
                a_msg = (f"{g.force[i]} side close to"
                         f" {g.vicflag[4]} % of total income")
                image2(g, a_msg, 4)                         # L276

            if g.vicflag[6] > 0 and x > 0 and y > 0:      # L279
                ratio_check = False
                if i == 1 and x / y > 0.9 * g.vicflag[6]:
                    ratio_check = True
                if i == 2 and y / x > 0.9 * g.vicflag[6]:
                    ratio_check = True
                if ratio_check:                             # L280
                    a_msg = (f"{g.force[i]}side close to"
                             f" {g.vicflag[6]}:1 strength ratio")
                    image2(g, a_msg, 4)                     # L282

            # stale: NEXT i → continue loop


# ═══════════════════════════════════════════════════════════════════════════
#  SUB rwin                                                     Lines 366-437
# ═══════════════════════════════════════════════════════════════════════════

def rwin(g: 'GameState') -> None:
    """Confederate win screen. Exact port of QB64 SUB rwin (L366-437)."""
    s = g.screen

    # Background                                            L367
    s.line(2, 2, 637, 239, 4, "BF")                        # L367

    # X pattern border                                      L368-369
    s.color(15)
    s.line(2, 40, 597, 239, 15)                             # L368
    s.line_to(637, 239, 15)
    s.line_to(637, 199, 15)
    s.line_to(40, 2, 15)
    s.line_to(2, 2, 15)
    s.line_to(2, 40, 15)
    s.line(2, 199, 2, 239, 15)                              # L369
    s.line_to(40, 239, 15)
    s.line_to(637, 40, 15)
    s.line_to(637, 2, 15)
    s.line_to(597, 2, 15)
    s.line_to(2, 199, 15)

    # Blue field                                            L370-371
    s.line(242, 95, 395, 145, 4, "BF")                     # L370
    s.paint(4, 20, 1, 15)                                   # L371

    # Green ground                                          L373
    s.line(2, 239, 637, 438, 2, "BF")                      # L373

    # Stars (GOSUB stars L374, L424-435)
    for idx in range(1, 9):                                 # L425
        if idx < len(g.starx) and idx < len(g.stary):
            sx = g.starx[idx]                               # L426
            sy = g.stary[idx]
            s.pset(sx, sy, 0)                               # L427
            s.line(sx + 2, sy - 1, sx + 8, sy + 16, 15)    # L428
            s.line_to(sx - 6, sy + 2, 15)                   # L429
            s.line_to(sx - 20, sy + 16, 15)
            s.line_to(sx - 14, sy - 1, 15)                  # L430
            s.line_to(sx - 30, sy - 9, 15)
            s.line_to(sx - 12, sy - 9, 15)                  # L431
            s.line_to(sx - 6, sy - 25, 15)
            s.line_to(sx, sy - 9, 15)                       # L432
            s.line_to(sx + 16, sy - 9, 15)
            s.line_to(sx + 2, sy - 1, 15)                   # L433
            s.paint(sx, sy, 15)                              # L433

    # Landscape                                             L377-385
    s.pset(1, 240, 0)                                       # L377
    s.draw("S14BR68C0E6U1E3R2E4R10F2R7F2R5E3R12F7R4F2E3R5E3R9F4")  # L378
    s.draw("C0R6F2R5F1R3F3L44F2L42E1H1L29E2R1BH5BL3BR5")  # L379
    s.paint(300, 230, 5, 0)                                 # L380

    s.pset(2, 330, 0)                                       # L381
    s.draw("C0D18U1R32E4R26E2R27E5R20E2R1E2U1E2U2E4H4L5H2L9H1L5H3L4H2L5H1L3H2L12H4")  # L382
    s.draw("C0D1F4R5F2R3F2R4F5R5F3L13G1L8G2L24G1L30G1L18D21")  # L383
    s.draw("BE5")                                            # L384
    x_pt = s._last_x
    y_pt = s._last_y + 5
    s.paint(x_pt, y_pt, 9, 0)                               # L384

    s.draw("BU12C11R21F1R2BR2BD6C11R9E1R9E1R6BH7C11R9E1R9BF5C11R9E1R1E1R10")  # L385

    # Border                                                L386-387
    s.line(1, 1, 638, 440, 14, "B")                         # L386
    s.line(2, 2, 637, 439, 14, "B")                         # L387

    # Mansion                                               L389-409
    x = 100                                                 # L390
    y = 240
    s.circle(x + 50, y + 40, 80, 0, aspect=0.2)           # L391
    s.paint(x + 50, y + 40, 6, 0)                          # L392
    s.line(x + 95, y - 14, x + 102, y + 8, 8, "BF")       # L393
    s.line(x + 100, y - 14, x + 102, y + 8, 7, "BF")      # L394
    s.line(x, y, x + 100, y + 36, 7, "BF")                # L395
    for i in range(1, 7):                                   # L396
        s.line(x + 17 * i, y + 6, x + 17 * i + 4, y + 32, 0, "BF")
    s.line(x + 12, y + 18, x + 98, y + 22, 7, "BF")       # L397
    s.line(x + 50, y + 20, x + 57, y + 36, 8, "BF")       # L398
    s.line(x + 100, y + 36, x + 105, y + 39, 7)           # L399
    s.line_to(x + 5, y + 39, 7)                            # L400
    s.line_to(x, y + 38, 7)

    # Side porch                                            L402-407
    s.line(x, y, x - 7, y - 7, 8)                         # L402
    s.line_to(x - 14, y + 5, 8)
    s.line_to(x - 14, y + 33, 8)                           # L403
    s.line_to(x, y + 36, 8)
    s.line_to(x, y, 8)
    s.color(10)                                             # L404
    s.line(x - 5, y - 7, x + 95, y - 7, 10)
    s.line_to(x + 107, y + 7, 10)                          # L404
    s.line_to(x + 7, y + 7, 10)                            # L405
    s.line_to(x - 5, y - 7, 10)
    s.paint(x, y - 3, 10)                                   # L406
    s.paint(x - 5, y + 15, 8)                               # L407

    # Column highlights                                     L409
    for i in range(1, 7):
        s.line(x + 19 * i - 12, y + 7, x + 19 * i - 12 + 2, y + 40, 15, "BF")

    # Dixie music                                           L411-420
    s.update()
    if g.noise >= 2:
        from cws_sound import qb_play
        qb_play("MBMS T120")                                       # L412
        qb_play("O3 L16 g e L8 c c L16 c d e f L8 g g g e a a a. L16 g a8. g a b")  # L413
        qb_play("O4 L16 c d e4. c O3 g O4 c4. O3 g e g4. d e c4 P8")                # L414
        qb_play("L16 g e L8 c c L16 c d e f L8 g g g e a a a. L16 g a8. g a b")      # L415
        qb_play("O4 L16 c d e4. c O3 g O4 c4. O3 g e g4. d e c4.")                   # L416
        qb_play("L16 T150 g a b T120 O4 L8 c e d. c16 O3 a O4 c4 O3 a O4 d4.")      # L417
        qb_play("O3 a O4 d4. O3 T150 L16 g a b T120 L8 O4 c e d. c16")               # L418
        qb_play("L8 O3 a b O4 c. O3 a16 g e O4 c. O3 e16 e d4 e c4. e d4. a")       # L419
        qb_play("L8 g e O4 c. e16 d c4 O3 e c4. e d4. a g e O4 e4. c16 d c4")       # L420
