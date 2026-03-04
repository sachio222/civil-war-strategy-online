"""cws_ai.py - AI Decision Making Module
Direct port of cws_ai.bm (QB64) to Python.

Original file: cws_ai.bm (164 lines)
Contains:
    SUB smarts  ->  smarts(g)          [main AI routine]
    GOSUB enufarmies  ->  _enuf_armies(g, who)  [helper]

Translation notes:
    - GOTO labels become structured control flow (while/break/continue/flags)
    - GOSUB/RETURN becomes a helper function
    - CALL sub(x, output%) becomes output = sub(g, x) (return values)
    - COMMON SHARED vars become g.field (GameState reference)
    - RND becomes random.random()
    - DEFINT A-Z: int truncation preserved with int() where it matters
    - Original line numbers noted in comments for cross-reference

Dependencies (other modules that must exist):
    cws_flow:    events(g)
    cws_util:    starfin(g, who) -> (star, fin), tick(g, seconds)
    cws_misc:    void(g, location) -> int
    cws_ui:      clrbot(g), icon(g, from_, dest, kind), showcity(g)
    cws_army:    resupply(g, i), combine(g, who)
    cws_recruit: recruit(g, who)
    cws_navy:    navy(g, who, action), ships(g)
    cws_railroad:railroad(g, who)
    cws_combat:  evaluate(g, index) -> int
"""

import random
from typing import TYPE_CHECKING

from cws_globals import UNION, CONFEDERATE

if TYPE_CHECKING:
    from cws_globals import GameState


# ─────────────────────────────────────────────────────────────────────────────
# Helper: enufarmies
# Original: lines 151-161 (GOSUB enufarmies / RETURN)
#
# In QB64 this was an inline GOSUB sharing the caller's local scope.
# Variables x, y, z, star, fin were shared. In Python, we return x
# and let the caller re-derive star/fin.
# ─────────────────────────────────────────────────────────────────────────────

def _enuf_armies(g: 'GameState', who: int) -> int:
    """Count own armies vs enemy armies. Returns army-count metric.

    Original QB64:
        enufarmies:
        CALL starfin(star, fin, 3 - who)
        FOR i = star TO fin
            IF armyloc(i) > 0 THEN y = y + .1 * armysize(i)
        NEXT i
        CALL starfin(star, fin, who)
        x = 0: z = 0: FOR i = star TO fin: IF armyloc(i) > 0 THEN x = x + 1: z = z + .1 * armysize(i)
        NEXT i
        IF y > z THEN x = x - 2
        IF y > 2 * z THEN x = 0
        RETURN
    """
    from cws_util import starfin

    # Count enemy total strength                                    # L152
    e_star, e_fin = starfin(g, g.enemy_of(who))
    y = 0                                                           # L153
    for i in range(e_star, e_fin + 1):                              # L153-155
        if g.armyloc[i] > 0:
            y = int(y + 0.1 * g.armysize[i])   # DEFINT truncation

    # Count own army count (x) and strength (z)                     # L156
    star, fin = starfin(g, who)
    x = 0                                                           # L157
    z = 0
    for i in range(star, fin + 1):                                  # L157-158
        if g.armyloc[i] > 0:
            x += 1
            z = int(z + 0.1 * g.armysize[i])   # DEFINT truncation

    # Adjust count based on relative strength                       # L159-160
    if y > z:
        x -= 2
    if y > 2 * z:
        x = 0

    return x                                                        # L161


# ─────────────────────────────────────────────────────────────────────────────
# Main AI Routine
# Original: SUB smarts (lines 1-163)
#
# GOTO control flow map (original):
#     signup  -> line 47  (recruit section)
#     isok    -> line 56  (naval section)
#     dock    -> line 58  (naval deploy)
#     movenavy-> line 67  (naval movement)
#     movearmy-> line 91  (army orders)
#     deadman -> line 135 (skip this army, NEXT i)
#     city2   -> line 24  (search other cities to fortify)
#     capital -> line 33  (execute fortification)
#     nocap   -> line 117 (evaluate move)
#     move9   -> line 119 (assign move)
#     endlook -> line 30  (NEXT i in fort search)
#
# All forward GOTOs (to later sections) become early breaks/returns.
# city2/capital is a backward loop, restructured as while True.
# deadman inside FOR becomes continue.
# ─────────────────────────────────────────────────────────────────────────────

def smarts(g: 'GameState') -> None:
    """AI turn: supply check, fortify, recruit, naval orders, army moves.

    Called once per turn for the computer-controlled side.
    """
    # Lazy imports to match QB64's flat namespace (avoids circular deps)
    from cws_flow import events
    from cws_util import starfin, tick
    from cws_misc import void
    from cws_ui import clrbot
    from cws_map import icon, showcity
    from cws_army import resupply, combine
    from cws_recruit import recruit
    from cws_navy import navy, ships
    from cws_railroad import railroad
    from cws_combat import evaluate

    events(g)                                                       # L2

    slush = 0                                                       # L3
    who = g.enemy_of()                                               # L3
    c = 15 if g.side == UNION else 9                                 # L4

    # "Confederate/Union Side is making decisions"                  # L5-6
    g.screen.locate(1, 1)
    g.screen.print_text(" " * 80)
    g.screen.color(c)
    g.screen.locate(1, 10)
    g.screen.print_text(f"{g.force[who]} Side is making decisions")

    star, fin = starfin(g, who)                                     # L7

    # ══════════════════════════════════════════════════════════════════════
    #                          Check Supply
    # ══════════════════════════════════════════════════════════════════════
    for i in range(star, fin + 1):                                  # L11
        if g.armyloc[i] > 0 and g.supply[i] < 1:
            resupply(g, i)
    # L12: NEXT i

    # ══════════════════════════════════════════════════════════════════════
    #                    Fortify Capital or Other City
    # ══════════════════════════════════════════════════════════════════════
    cost = 200                                                      # L16

    if cost <= g.cash[who]:  # L17: IF cost > cash(who) GOTO signup
        # Determine initial target -- try capital first             # L19
        target = 0
        skip_city_search = False

        if g.occupied[g.capcity[who]] != 0 and g.fort[g.capcity[who]] <= 1:
            # Capital is occupied and not already fortified         # L20
            target = g.capcity[who]
            if g.cityp[target] == who:                              # L21
                skip_city_search = True     # goto capital directly
            else:
                target = 0                  # goto city2
        # else: capital unoccupied or already fortified -> city2

        # ── city2/capital loop ────────────────────────────────────
        # capital can jump back to city2 (L43), forming a loop.
        while True:

            if not skip_city_search:
                # ── city2: search for a city needing fortification ─ L24-31
                if 1 + random.random() < g.bold + g.aggress:       # L25
                    break   # goto signup

                target = 0                                          # L26
                for i in range(star, fin + 1):                      # L26
                    x = g.armyloc[i]                                # L27
                    if x == 0:
                        continue    # endlook
                    if g.armymove[g.occupied[x]] < 0:
                        continue    # endlook
                    if g.armymove[i] < 0:
                        continue    # endlook
                    if g.fort[x] > 1:                               # L28
                        continue    # endlook
                    defend = void(g, x)                             # L29
                    if defend > g.armysize[i]:
                        target = g.armyloc[i]
                        break       # goto capital
                # falls through to capital

            skip_city_search = False  # subsequent iterations always search

            # ── capital: execute fortification ───────────────── L33-43
            if target == 0:                                         # L34
                break   # goto signup
            if g.fort[target] > 1:                                  # L35
                break   # goto signup

            g.fort[target] += 1                                     # L36
            x = g.occupied[target]                                  # L37
            g.armymove[x] = -1
            g.cash[who] -= cost                                     # L38

            clrbot(g)                                               # L39
            g.screen.print_text(
                f"{g.city[target]} fortifications increased to {g.fort[target]}"
            )
            icon(g, target, 0, 6)                                   # L40
            showcity(g)                                             # L41

            # BUG NOTE: Original L42 reads "cash < 222" (no array index).
            # In QB64, bare 'cash' is a separate uninitialized int (=0),
            # so "0 < 222" is always true. Likely meant cash(who).
            # Preserving original behavior:
            if (who == UNION                                         # L42
                    and g.navysize[UNION] < 1
                    and random.random() > 0.5
                    and 0 < 222):               # cash (no index) = 0
                break   # goto signup

            if (3 * random.random() > 1 + g.aggress                # L43
                    and g.cash[who] >= cost):
                continue    # goto city2 (loop back for more forts)

            break   # fall through to signup

    # ══════════════════════════════════════════════════════════════════════
    #                    Recruit New Armies (signup:)
    # ══════════════════════════════════════════════════════════════════════
    #                                                                 L47
    goto_isok = False

    # L48: Confederate special case -- build navy if none exists
    if who == UNION and g.navysize[UNION] < 1 and g.cash[UNION] > 100:
        navy(g, UNION, 1)
        if g.cash[who] < 100:
            goto_isok = True

    if not goto_isok:
        # L49: GOSUB enufarmies -> returns x
        x = _enuf_armies(g, who)
        star, fin = starfin(g, who)     # restore after _enuf_armies

        # L50
        if x > 2 + 3 * g.side + 3 * random.random():
            goto_isok = True

    if not goto_isok:
        # L51: Divert cash to navy if affordable
        if (g.navysize[who] < 5
                and g.cash[who] > 100
                and g.navyloc[who] != 99):
            if g.cityp[g.navyloc[who]] == who:
                slush += 100
                g.cash[who] -= 100
                if g.cash[who] < 100:
                    goto_isok = True

    if not goto_isok:
        recruit(g, who)                                             # L52

    # ══════════════════════════════════════════════════════════════════════
    #                       Naval Commands (isok:)
    # ══════════════════════════════════════════════════════════════════════
    g.cash[who] += slush                                            # L57

    # ── dock: ─────────────────────────────────────────────────── L58-87
    goto_movenavy = False
    goto_movearmy = False

    # L59: Special case -- deploy Confederate navy from port 30
    if (g.side == CONFEDERATE
            and g.navyloc[UNION] == 0
            and g.navysize[UNION] < 1
            and g.cityp[30] == UNION
            and g.cash[UNION] > 100):
        g.navyloc[UNION] = 30
        navy(g, UNION, 1)
        goto_movenavy = True

    if not goto_movenavy:
        # L60-63: Navy in drydock (location 99)
        if g.navyloc[who] == 99:
            if random.random() < 0.9:                               # L61
                navy(g, who, 3)
            goto_movearmy = True                                    # L62

    if not goto_movenavy and not goto_movearmy:
        # L64: Check if we can/should build more ships
        if (g.cash[who] < 100
                or g.navysize[who] > 9
                or g.cityp[g.navyloc[who]] != who):
            goto_movenavy = True                                    # L64
        else:
            navy(g, who, 1)                                         # L65
            goto_movenavy = True

    # ── movenavy: ─────────────────────────────────────────────── L67-87
    if goto_movenavy and not goto_movearmy:
        if g.navysize[who] == 0:                                    # L68
            g.navyloc[who] = 0

        if g.navyloc[who] == 0:                                     # L69
            goto_movearmy = True

        if not goto_movearmy:
            if g.navyloc[who] != 99:                                # L73
                # At a friendly or neutral port -> move               L74-75
                if g.cityp[g.navyloc[who]] == who:
                    navy(g, who, 3)     # move
                    goto_movearmy = True
                elif g.cityp[g.navyloc[who]] == 0:
                    navy(g, who, 3)     # move
                    goto_movearmy = True
            else:
                # In drydock -> maybe move                            L77-78
                if random.random() < 0.5:
                    navy(g, who, 3)
                goto_movearmy = True

        # L81-87: At enemy port -> attack or move
        if not goto_movearmy:
            if g.cityp[g.navyloc[who]] != who:
                if g.occupied[g.navyloc[who]] == 0 or random.random() > 0.3:
                    navy(g, who, 2)     # attack                    # L83
                else:
                    navy(g, who, 3)     # move                      # L85

    # ══════════════════════════════════════════════════════════════════════
    #                  Give Move Orders to Each Army (movearmy:)
    # ══════════════════════════════════════════════════════════════════════
    ships(g)                                                        # L92

    # ── Check to Combine ──                                        # L96
    combine(g, who)
    railroad(g, who)                                                # L97

    # ── Top Priority: evaluate and assign moves ──                 # L101
    for i in range(star, fin + 1):
        target = g.armyloc[i]                                       # L102

        if g.armyloc[i] < 1 or g.armymove[i] < 0:                  # L103
            continue    # deadman

        x = g.armysize[i]                                           # L104
        if g.supply[i] < 1 and random.random() > 0.1:
            continue    # deadman

        choose = 0                                                  # L106
        defend = void(g, target)                                    # L108

        # Hold capital if under threat                              # L110
        if (defend > 0
                and target == g.capcity[who]
                and g.occupied[target] == i):
            continue    # deadman -- hold position

        # ── nocap check: is capital neighborhood threatened? ──    # L111-117
        skip_to_eval = True
        if target == g.capcity[who]:                                # L111
            if g.vicflag[5] != 0:                                   # L112
                skip_to_eval = False
                for j in range(1, 7):                               # L113
                    k = g.matrix[target][j]
                    # BUG NOTE: Original L114 says "IF j = 0 GOTO nocap"
                    # but j is always 1..6. Almost certainly meant k = 0.
                    if k == 0:                                      # L114
                        skip_to_eval = True
                        break
                    flag = void(g, k)                               # L115
                    if flag > 0:
                        # Threat near capital -> hold position
                        break
                else:
                    # Loop completed, no threats found
                    skip_to_eval = True

                if not skip_to_eval:
                    continue    # deadman -- defend capital

        # ── nocap: evaluate best move ──                           # L118
        best = evaluate(g, i)
        if best == 0:
            continue    # deadman

        # ── move9: assign movement order ──                        # L119-134
        # NOTE: L120 "IF best = 0" is dead code (we just checked above).
        # Preserving for fidelity: best is guaranteed nonzero here.
        if best == 0:                                               # L120
            j_val = 7   # j after FOR j=1 TO 6 exits
            choose = 1 + int((j_val - 1) * random.random())
        if choose == 0:                                             # L121
            choose = best
        g.armymove[i] = g.matrix[target][choose]                    # L122

        # Eliminate crossing moves (two armies swapping positions)  # L124
        if g.cityp[g.armymove[i]] == who:
            y = g.occupied[g.armymove[i]]
            if y > 0:
                if g.armymove[y] == x:
                    g.armymove[i] = 0
                    continue    # deadman

        # January campaign restriction                              # L125
        if (g.month == 1
                and g.jancam == 0
                and g.cityp[g.armymove[i]] != who):
            g.armymove[i] = 0
            continue    # deadman

        # Display move plan (if animation speed allows)             # L127-130
        if g.turbo > 1:
            g.screen.color(c)
            clrbot(g)
            g.screen.print_text(
                f"{g.armyname[i]} plans to move from "
                f"{g.city[g.armyloc[i]]} to {g.city[g.armymove[i]]}"
            )

        icon(g, g.armyloc[i], g.armymove[i], 1)                    # L131
        icon(g, g.armyloc[i], g.armymove[i], 9)                    # L132
        tick(g, g.turbo - 1)                                        # L133

        # Restore arrow then map tile under army icon               # L134
        from cws_map import _clear_arrow
        _clear_arrow(g)
        g.screen.put_image(
            g.cityx[g.armyloc[i]] - 20,
            g.cityy[g.armyloc[i]] - 19,
            g.image
        )

    # ── Drill idle armies (gain experience) ──                     # L137-148
    for i in range(star, fin + 1):
        if (g.armymove[i] == 0                                      # L138
                and g.armyexper[i] < 6
                and g.armyexper[i] < g.armylead[i]):
            g.armyexper[i] += 1                                     # L139

            if g.turbo > 1:                                         # L141
                clrbot(g)
                g.screen.print_text(
                    f"{g.armyname[i]} has drilled to reach "        # L143
                    f"experience level {g.armyexper[i]}"
                )

            g.armymove[i] = -1                                      # L145
            tick(g, g.turbo - 1)                                    # L146

    # L149: EXIT SUB / END SUB
