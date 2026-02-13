"""cws_combat.py - Combat resolution.
Direct port of cws_combat.bm (531 lines).

Contains:
    battle(g, attack, defend)     L1-193   - battle resolution → (win, lose)
    fortify(g)                    L194-228 - build fortifications → target city
    strong(g, index)              L229-232 - helper: army strength string
    cannon(g)                     L233-280 - battle visual (simplified mono)
    capture(g, active, c, s, flag) L281-299 - city capture
    evaluate(g, index)            L300-386 - AI move evaluation → best adj idx
    retreat(g, defend)            L387-407 - retreat path selection → city
    surrender(g, who)             L408-530 - surrender visual (simplified mono)

QB64 bugs preserved:
    L126-131: SELECT CASE >300 makes >800 unreachable (casualty calc)
    L137-141: Same SELECT CASE bug for attacker casualties
    L185: 'IF attack > 2' should be 'IF attack > 20' (side determination)
"""

import random
import pygame
from typing import TYPE_CHECKING
from cws_globals import UNION, CONFEDERATE

if TYPE_CHECKING:
    from cws_globals import GameState


def _strong(g: 'GameState', index: int) -> str:
    """Return army strength string: armysize * 100. (SUB strong, L229-232)"""
    return f"{g.armysize[index]}00"


# ═══════════════════════════════════════════════════════════════════════════
#  SUB battle (attack, defend, win, lose)                      Lines 1-193
# ═══════════════════════════════════════════════════════════════════════════

def battle(g: 'GameState', attack: int, defend: int) -> tuple:
    """Resolve battle. Returns (win, lose) army indices.

    Full combat calculation with all modifiers:
    base strength, leader/exp, small army penalty, outnumber ratio,
    supply, difficulty, fort bonus, grapple loop, casualty distribution.
    """
    from cws_map import icon, showcity
    from cws_ui import clrbot, clrrite, scribe, flags
    from cws_util import tick, normal

    s = g.screen

    if g.armysize[defend] < 1:                             # L2
        g.armysize[defend] = 1
    if g.armysize[attack] < 1:                             # L3
        g.armysize[attack] = 1

    icon(g, g.armyloc[defend], 0, 9)                       # L5: arrow pointer
    s.locate(1, 1)                                         # L6
    s.print_text(" " * 80)

    y = 68                                                 # L7: display column
    clrrite(g)
    s.color(11)
    s.locate(1, y)
    s.print_text("Attacker")

    c = 9                                                  # L8
    if attack > 20:
        c = 7

    # ── Attacker stats ──
    s.color(c)
    s.locate(2, y)                                         # L9
    s.print_text(g.armyname[attack])
    s.locate(3, y)                                         # L10
    s.print_text(_strong(g, attack))

    x = 0.01 * g.armysize[attack]                         # L11
    if x > g.tcr:
        x = g.tcr
    s.locate(4, y)                                         # L12
    s.print_text(f"Base    {int(x)}")

    # Leader/Experience bonus                               L13
    if g.armysize[attack] / g.armysize[defend] > 0.2:
        x = x + 0.3 * g.armylead[attack] + 0.3 * g.armyexper[attack]
        if x > g.tcr:
            x = g.tcr
    if g.armyexper[attack] > 8:                            # L14
        x = x + 1
        if x > g.tcr:
            x = g.tcr
    s.locate(5, y)                                         # L15
    s.print_text(f"Ldr/Exp {int(x)}")

    # Small army penalty                                    L16
    if g.armysize[attack] < 15:
        x = 0.5 * x
        if x > g.tcr:
            x = g.tcr
    s.locate(6, y)                                         # L17
    s.print_text(f"Small   {int(x)}")

    # Outnumber adjustments                                 L18-21
    ratio = g.armysize[attack] / g.armysize[defend] if g.armysize[defend] > 0 else 999
    if ratio <= 0.5:
        x = x - 2
        if x < 1:
            x = 1
    if ratio > 3:                                          # L19
        x = x + 2
        if x > g.tcr:
            x = g.tcr
    if ratio > 10:                                         # L20
        x = g.tcr
    if ratio <= 0.2:                                       # L21
        x = 1
    s.locate(7, y)                                         # L22
    s.print_text(f"Outman  {int(x)}")

    # Supply penalty                                        L23
    if g.supply[attack] < 1:
        x = 0.5 * x
        s.color(13)
    s.locate(8, y)                                         # L24
    s.print_text(f"Supply  {int(x)}")
    s.color(c)
    if x < 1:                                              # L25
        x = 1

    # Difficulty adjustment                                 L27-28
    if attack < 21 and g.side == CONFEDERATE and g.difficult > 3:   # L27
        x = x + 2 * g.difficult - 6
    if attack > 20 and g.side == UNION and g.difficult < 3:   # L28
        x = x + 6 - 2 * g.difficult
    s.locate(9, y)                                         # L29
    s.print_text(f"Difclt  {int(x)}")
    if x > g.tcr:                                          # L30
        x = g.tcr
    s.color(11)
    s.locate(11, y)                                        # L31
    s.print_text(f"Attack  {int(x)}")
    s.line(530, 155, 635, 175, 11, "B")                    # L32

    # ── Defender stats ──
    x1 = 0.013 * g.armysize[defend] + 1                   # L34
    if g.realism == 1:
        x1 = 0.02 * g.armysize[defend] + 2
        if x1 > 20:
            x1 = 20
    s.locate(13, y)                                        # L35
    s.print_text("Defender")
    s.color(16 - c)                                        # L36: inverted color
    s.locate(14, y)
    s.print_text(g.armyname[defend])
    s.locate(15, y)                                        # L37
    s.print_text(_strong(g, defend))
    s.locate(16, y)                                        # L38
    s.print_text(f"Base    {int(0.01 * g.armysize[defend])}")
    s.locate(17, y)                                        # L39
    s.print_text(f"Defense {int(x1)}")

    # Defender leader/exp bonus                             L40
    d_ratio = g.armysize[defend] / g.armysize[attack] if g.armysize[attack] > 0 else 999
    if d_ratio > 0.2:
        x1 = x1 + 0.3 * g.armylead[defend] + 0.3 * g.armyexper[defend]
        if x1 > g.tcr:
            x1 = g.tcr
    if g.armyexper[defend] > 8:                            # L41
        x1 = x1 + 1
        if x1 > g.tcr:
            x1 = g.tcr
    s.locate(18, y)                                        # L42
    s.print_text(f"Ldr/Exp {int(x1)}")

    if g.armysize[defend] < 15:                            # L43
        x1 = 0.5 * x1
    s.locate(19, y)                                        # L44
    s.print_text(f"Small   {int(x1)}")

    # Defender outnumber SELECT CASE                        L46-56
    r = d_ratio
    if r > 10:                                             # CASE IS > 10
        x1 = g.tcr
    elif r > 1.5:                                          # CASE IS > 1.5
        x1 = x1 + 2
    elif r < 0.5:                                          # CASE IS < .5 (catches < .2 too)
        x1 = 0.8 * x1
    # CASE IS < .2: unreachable (bug preserved)
    if x1 < 1:                                             # L57
        x1 = 1
    if x1 > g.tcr:                                         # L58
        x1 = g.tcr

    s.locate(20, y)                                        # L60
    s.print_text(f"Outman  {int(x1)}")
    if g.supply[defend] < 1:                               # L61
        x1 = 0.5 * x1
        s.color(13)
    s.locate(21, y)                                        # L62
    s.print_text(f"Supply  {int(x1)}")
    s.color(16 - c)
    if x1 < 1:                                             # L63
        x1 = 1

    # Difficulty adjustment for defender                    L65-66
    if defend < 21 and g.side == CONFEDERATE and g.difficult > 3:   # L65
        x1 = x1 + 2 * g.difficult - 6
    if defend > 20 and g.side == UNION and g.difficult < 3:   # L66
        x1 = x1 + 6 - 2 * g.difficult
    s.locate(22, y)                                        # L67
    s.print_text(f"Difclt  {int(x1)}")

    # Fort bonus                                            L69-76
    a_str = "Fort"                                         # L69
    if g.armymove[defend] == 0:
        x1 = x1 * (1 + g.fort[g.armyloc[defend]])
    if x1 > g.tcr:                                         # L70
        x1 = g.tcr
    if g.fort[g.armyloc[defend]] > 0 and g.armymove[defend] == 0:  # L71
        s.color(13)
        a_str = "Fort+"                                    # L72
        if g.fort[g.armyloc[defend]] == 2:                 # L73
            a_str = "Fort++"
    s.locate(23, y)                                        # L75
    s.print_text(f"{a_str:8s}{int(x1)}")
    if x1 > g.tcr:                                         # L76
        x1 = g.tcr
    s.color(11)
    s.locate(25, y)                                        # L77
    s.print_text(f"Defend  {int(x1)}")
    s.line(530, 380, 635, 400, 11, "B")                    # L78

    # ── Odds calculation ──                                 L80-88
    scale = x                                              # L81
    if x1 > scale:
        scale = x1
    scale = scale + 1                                      # L82

    odds = x / (x + x1) if (x + x1) > 0 else 0.5         # L84
    a_pct = int(100 * odds)
    if a_pct < 1:
        a_pct = 1
    s.color(14)                                            # L86
    s.locate(27, y)
    s.print_text(f"Odds:  {a_pct}%")
    s.line(530, 412, 635, 435, 14, "B")                    # L87
    s.line(528, 410, 637, 437, 14, "B")                    # L88
    s.update()

    # Wait for keypress                                     L89
    _wait_key()

    # Battle visual                                         L90-102
    if g.graf > 2:
        cannon(g)
        # L92-99: fort graphic
        k = g.fort[g.armyloc[defend]]                      # L92
        fort_surfs = getattr(g, 'fort_surfaces', {})
        if k in fort_surfs:
            s.put_image(550, 270, fort_surfs[k])           # L98
    else:
        clrrite(g)                                         # L101

    # Supply consumption                                    L103-104
    # BUG: consumes supply for armies 1 and 2, not attack/defend
    for i in range(1, 3):
        if g.supply[i] > 0:
            g.supply[i] -= 1

    # ── Grapple loop: determine winner ──                   L106-115
    while True:                                            # grapple:
        hit = 0                                            # L107
        hit1 = 0
        star = scale * random.random()                     # L108
        fin = scale * random.random()
        if g.noise > 0:                                    # L109
            from cws_sound import qb_sound
            qb_sound(77, 0.5)
            qb_sound(59, 0.5)
        if star <= x:                                      # L110
            hit = 1
        if fin <= x1:                                      # L111
            hit1 = 1
        if hit == 0 and hit1 == 0:                         # L113
            continue
        if hit == 1 and hit1 == 1:                         # L114
            continue
        break

    if hit == 1:                                           # L115
        win, lose = attack, defend
    else:
        win, lose = defend, attack

    # ── Display victory ──                                  L117-123
    a_str = "UNION"                                        # L117
    if win > 20:
        a_str = "REBEL"
    s.color(14)
    s.locate(3, 68)                                        # L118
    s.print_text(f"{a_str} VICTORY")
    s.locate(4, 71)                                        # L119
    s.print_text("in")
    s.locate(5, 69)                                        # L120
    s.print_text(g.city[g.armyloc[defend]])
    a_side = UNION                                          # L121
    if win > 20:
        a_side = CONFEDERATE
    flags(g, a_side, 0, 0)                                 # L122
    clrbot(g)
    s.color(11)
    s.print_text(
        f"{g.armyname[win]} defeats {g.armyname[lose]} in "
        f"{g.city[g.armyloc[defend]]}"
    )
    tick(g, 9)                                             # L123

    # ── Casualty calculation ──                             L125-155

    # Defender casualties                                   L125-134
    pct = 0.01 * g.defac - 0.03 * g.fort[g.armyloc[defend]]  # L125
    if win == attack:
        pct = 1.3 * pct
    # SELECT CASE armysize(defend): >300 catches all (bug)  L126-131
    if g.armysize[defend] > 300:
        pct = 0.9 * pct
    # >800 unreachable
    xbar = g.armysize[attack] * pct                        # L132
    vary = xbar * (1 - pct)                                # L133
    killd = normal(xbar, vary)                              # L134

    # Attacker casualties                                   L136-145
    pct = 0.01 * g.atkfac + 0.02 * g.fort[g.armyloc[defend]]  # L136
    if win == defend:
        pct = 1.5 * pct
    # Same SELECT CASE bug                                  L137-141
    if g.armysize[attack] > 300:
        pct = 0.9 * pct
    xbar = g.armysize[defend] * pct                        # L143
    vary = xbar * (1 - pct)                                # L144
    killa = normal(xbar, vary)                              # L145

    # Cross-contaminate and cap casualties                  L148-154
    killa = int(0.8 * killa + 0.2 * killd)                # L148
    if killa < 1:
        killa = 1
    killd = int(0.8 * killd + 0.2 * killa)                # L149
    if killd < 1:
        killd = 1
    if killa > 9 * killd:                                  # L150
        killa = 9 * killd
    if killd > 5 * killa:                                  # L151
        killd = 5 * killa
    if killa >= g.armysize[attack]:                        # L153
        killa = g.armysize[attack] - 1
    if killd >= g.armysize[defend]:                        # L154
        killd = g.armysize[defend] - 1

    # ── Display results ──                                  L156-175
    x_pct = int(100 * odds)                                # L156
    if x_pct < 1:
        x_pct = 1

    s.color(c)                                             # L159
    s.locate(1, 1)                                         # L160
    atk_pct = int(100 * killa / g.armysize[attack]) if g.armysize[attack] > 0 else 0
    s.print_text(f"Attack Loss: {killa}00/{_strong(g, attack)} ({atk_pct}%) |")
    s.color(16 - c)                                        # L164
    def_pct = int(100 * killd / g.armysize[defend]) if g.armysize[defend] > 0 else 0
    s.print_text(f"| Defend Loss: {killd}00/{_strong(g, defend)} ({def_pct}%)")

    # Build history string                                  L168-175
    atk_str = f" ({killa}00/{g.armysize[attack]}00) "
    def_str = f" ({killd}00/{g.armysize[defend]}00)"
    if win == defend:
        w_str, l_str = atk_str, def_str
    else:
        w_str, l_str = def_str, atk_str
    w_name = f"*{g.armyname[win]}" if win == attack else g.armyname[win]
    l_name = f"*{g.armyname[lose]}" if win == defend else g.armyname[lose]
    hist = f"{g.city[g.armyloc[defend]]}: {w_name}{w_str} defeats {l_name}{l_str}"

    # Emit structured battle event for online replay
    if g.player == 3:
        g.event_log.append({
            "type": "battle",
            "city": g.city[g.armyloc[defend]],
            "atk_name": g.armyname[attack], "atk_id": attack,
            "atk_size": g.armysize[attack],
            "def_name": g.armyname[defend], "def_id": defend,
            "def_size": g.armysize[defend],
            "atk_power": int(x), "def_power": int(x1),
            "odds": a_pct,
            "winner": "attacker" if win == attack else "defender",
            "winner_side": UNION if win <= 20 else CONFEDERATE,
            "atk_loss": killa, "atk_pct": atk_pct,
            "def_loss": killd, "def_pct": def_pct,
            "fort": g.fort[g.armyloc[defend]],
            "msg": f"{g.armyname[win]} defeats {g.armyname[lose]} in {g.city[g.armyloc[defend]]}"
        })
        g._skip_scribe_log = True

    scribe(g, hist, 0)                                     # L175

    # Wait for AI battles                                   L177-179
    if g.player == 1:
        if (g.side == UNION and attack > 20) or (g.side == CONFEDERATE and attack < 21):
            s.color(14)
            clrbot(g)
            s.print_text("hit any key to continue")
            s.update()
            _wait_key()

    # Apply casualties                                      L181-183
    g.armysize[attack] -= killa                            # L181
    g.armysize[defend] -= killd                            # L182
    if g.armysize[defend] < 1:                             # L183
        g.armysize[defend] = 1

    # Statistics                                            L185-191
    # BUG: L185 uses 'attack > 2' instead of 'attack > 20'
    ss = UNION                                              # L185
    if attack > 2:
        ss = CONFEDERATE
    g.casualty[ss] += killa                                # L186
    g.casualty[g.enemy_of(ss)] += killd                    # L187

    ss = UNION                                              # L189
    if win > 20:
        ss = CONFEDERATE
    g.batwon[ss] += 1                                      # L190
    g.victory[ss] += 1                                     # L191
    icon(g, g.armyloc[defend], 0, 8)                       # L192: restore image

    s.update()
    return (win, lose)


# ═══════════════════════════════════════════════════════════════════════════
#  SUB fortify (target)                                        Lines 194-228
# ═══════════════════════════════════════════════════════════════════════════

def fortify(g: 'GameState') -> int:
    """Build fortifications. Returns target city index, 0 if none built."""
    from cws_util import starfin, tick, bubble, stax
    from cws_ui import clrbot, clrrite, menu
    from cws_map import icon, showcity
    from cws_army import placearmy
    from cws_data import occupy

    s = g.screen
    target = 0                                             # L195
    g.hilite = 11
    g.tlx = 67                                             # L196
    g.tly = 2
    who = g.side                                           # L197
    star, fin = starfin(g, who)                            # L198

    g.size = 0                                             # L199
    for i in range(star, fin + 1):                         # L200
        if g.armyloc[i] > 0 and g.fort[g.armyloc[i]] < 2:  # L201
            g.size += 1                                    # L202
            g.mtx[g.size] = g.city[g.armyloc[i]]          # L203
            g.array[g.size] = g.armyloc[i]                 # L204

    if g.size == 0:                                        # L207
        clrbot(g)
        s.color(11)
        s.print_text("No cities eligible to fortify")
        return 0

    bubble(g, g.size)                                      # L208
    g.mtx[0] = "Fortify"                                   # L209
    g.choose = 31                                          # L210
    menu(g, 9)                                             # L211
    clrrite(g)

    if g.choose < 0:                                       # L212: nocity
        return 0

    target = g.array[g.choose]                             # L213
    occupy(g, target)
    xx = g.occupied[target]
    if xx < 0:
        return 0

    if g.fort[target] > 1:                                 # L214
        clrbot(g)
        s.print_text(f"{g.city[target]} at MAXIMUM fortification level of 2")
        tick(g, 4)
        return 0

    cost = 200                                             # L215
    if g.cash[g.side] < cost:                              # L216
        clrbot(g)
        s.print_text(
            f"Fortifications for {g.city[target]} cost {cost} "
            f"and you only have {g.cash[g.side]}"
        )
        tick(g, 4)
        return 0

    s.color(3)                                             # L217
    g.fort[target] += 1                                    # L218
    g.cash[g.side] -= cost                                 # L219
    clrbot(g)                                              # L220
    s.print_text(f"{g.city[target]} fortifications increased to {g.fort[target]}")
    icon(g, target, 0, 6)                                  # L221
    showcity(g)                                            # L222
    if g.armymove[xx] > 0:                                 # L223
        icon(g, g.armyloc[xx], g.armymove[xx], 5)
    g.armymove[xx] = -1                                    # L224
    placearmy(g, xx)                                       # L225
    stax(g, who)                                           # L226
    return target


# ═══════════════════════════════════════════════════════════════════════════
#  SUB cannon                                                  Lines 233-280
# ═══════════════════════════════════════════════════════════════════════════

def cannon(g: 'GameState') -> None:
    """Draw cannon battle scene. Exact port of QB64 SUB cannon (L233-280)."""
    from cws_ui import clrrite
    s = g.screen
    clrrite(g)                                             # L234
    # Background panels                                     L235-237
    s.line(528, 80, 639, 310, 3, "BF")                    # L235
    s.line(528, 310, 639, 435, 2, "BF")                   # L236
    s.line(528, 405, 639, 420, 0, "BF")                   # L237
    s.pset(580, 380, 0)                                    # L238

    # Cannon wheels                                         L240-243
    s.draw("BR15")                                          # L240
    x = s._last_x; y = s._last_y
    s.circle(x, y, 25, 1, aspect=1.4)                      # L241
    s.circle(x + 5, y, 27, 1, start=4.0, end=1.5, aspect=1.4)  # L242
    s.circle(x, y, 29, 1, aspect=1.4)                      # L243

    s.draw("BR20")                                          # L244
    x = s._last_x; y = s._last_y
    s.paint(x, y, 3, 1)                                    # L245

    s.draw("BR3BU7")                                        # L246
    x = s._last_x; y = s._last_y
    s.paint(x, y, 5, 1)                                    # L247

    # Cannon barrel                                         L248-259
    s.draw("BL15C7G4L50H1L12H1L7H3U1H1U4E5R6E1R13E1R52F3D2R1E1R1F2D5G3H2G2BL2")  # L248
    s.draw("BH2C6")                                         # L249
    x = s._last_x; y = s._last_y
    s.paint(x, y, 7)                                        # L250

    s.draw("BD2R4C0G4L50H1L12H1L7H3U1H1U4E5R6E1R13E1R52F3D2R1E1R1F2D5G3H2G2BR5U3")  # L251
    s.draw("C8G2H2G6L15G1L32H1L1H1L19H3E2R2F1R6")          # L252
    s.draw("E2R4F1R6E1R58F1G2BL9BH2BU5BR3C15H1L48G1L13G1L4")  # L253

    s.draw("BD3BF3BR9")                                      # L254
    x = s._last_x; y = s._last_y
    s.paint(x, y, 8)                                        # L255

    # Soldier body                                          L256-259
    s.draw("BR34BE1BR7BL5BD8C6R16F5D1F4D6F7R17D7L30H18L8H4L18H3U5R33BR17BD5")  # L256
    x = s._last_x; y = s._last_y
    s.paint(x, y, 6)                                        # L257

    s.draw("BU5C8F8D7F6R1F1R16D7E3U7G3E2BE2C8L16H6U8C8G3BE3C8H8G6BR5")  # L258
    x = s._last_x; y = s._last_y
    s.paint(x, y, 8)                                        # L259

    # Smoke rings                                           L260-268
    s.draw("BL38")                                           # L260
    x = s._last_x; y = s._last_y
    s.circle(x, y, 30, 4, aspect=1.4)                       # L261
    s.circle(x + 5, y, 35, 4, start=4.0, end=1.5, aspect=1.4)  # L262
    s.circle(x, y, 35, 4, aspect=1.4)                       # L263
    s.circle(x, y, 8, 4, aspect=1.4)                        # L264
    s.paint(x, y, 1, 4)
    s.paint(x, y, 0, 4)

    s.draw("BR23")                                           # L265
    x = s._last_x; y = s._last_y
    s.paint(x, y, 1, 4)                                     # L266
    s.paint(x, y, 4, 4)

    s.draw("BR5BU7")                                         # L267
    x = s._last_x; y = s._last_y
    s.paint(x, y, 1, 4)                                     # L268
    s.paint(x, y, 0, 4)

    # Soldier details (DRAW commands)                        L269-278
    s.draw("BU22BL28")                                       # L269
    s.draw("C4D20R1U19BD37C4D20L1U21BH2BL1BH1C4G12F1E11BU3BH2")  # L270
    s.draw("BU3BL1C4L13U1R15BR1BU3C4H12E1F11BF5BE4C4E11F1G11BD3C4R13D1L10D3BL3BD1C4")  # L271
    s.draw("F12G1H12BL33BH13BU3BH2BU1BE1BR2BU1BE1BR1")     # L272
    s.draw("BL5BU5C8E4U1")                                   # L273
    s.draw("H4E3H3U3E3H6L3G7F1H7E2U2E2H7L7G9D6F8G3L1H3L5G7D4F4R2D3F3R2G5D4L4G4D5F8D2")  # L274
    s.draw("R5F9E3F5R6E6H4E2F6R3E8F1E4H5U2H3U1H1U7E4H7BL5")  # L275

    x = s._last_x; y = s._last_y
    s.paint(x, y, 8, 8)                                     # L276

    s.draw("BR9BD6C15H8L1H2L12G1F5L8G4F4R3G3D1G2D3F2E5G1D8R4E3D6F3E12H1U1H1U6E5BH6BU4")  # L277
    s.draw("BD15")                                            # L278
    x = s._last_x; y = s._last_y
    s.paint(x, y, 14, 15)                                    # L279
    s.update()


# ═══════════════════════════════════════════════════════════════════════════
#  SUB capture (active, c, s, flag)                            Lines 281-299
# ═══════════════════════════════════════════════════════════════════════════

def capture(g: 'GameState', active: int, c: int, s_side: int, flag: int) -> None:
    """Handle city capture: flip ownership, VP, capital check, fort damage."""
    from cws_ui import clrbot, scribe
    from cws_map import flashcity, showcity, image2
    from cws_util import tick

    scr = g.screen
    g.cityp[c] = s_side                                    # L282
    a_str = f"{g.armyname[active]} has captured {g.city[c]}"

    # Emit structured capture event for online replay
    if g.player == 3:
        g.event_log.append({
            "type": "capture",
            "city_id": c,
            "city_name": g.city[c],
            "army_name": g.armyname[active],
            "side": s_side,
            "msg": a_str
        })
        g._skip_scribe_log = True

    scr.color(11)                                          # L284
    scribe(g, a_str, 1)
    scr.update()
    if active < 21 and g.noise > 1:                        # L285
        from cws_sound import qb_play
        qb_play("MNMFL16o2T120dd.dd.co1b.o2do3g.ab.bb.ag")
    if active > 20 and g.noise > 1:                        # L286
        from cws_sound import qb_play
        qb_play("MNMFT160o2L16geL8ccL16cdefL8ggge")

    if c != g.capcity[g.enemy_of(s_side)]:                  # L287
        flashcity(g, c)
        if s_side != g.side:                               # notify player
            scribe(g, a_str, 2)

    g.victory[s_side] += g.cityv[c]                        # L288

    if c == g.capcity[g.enemy_of(s_side)]:                  # L289: CAPITAL captured!
        g.victory[s_side] += 100                           # L290
        g.victory[g.enemy_of(s_side)] -= 100               # L291
        cap_str = f"{g.force[g.enemy_of(s_side)]} CAPITAL captured !"
        scribe(g, cap_str, 1)                              # L293
        image2(g, f"{g.city[g.capcity[g.enemy_of(s_side)]]} has fallen!", 4)  # L294
        g.capcity[g.enemy_of(s_side)] = 0                  # L295
        flashcity(g, c)                                    # L296

    # Fort damage from battle                               L298
    if g.fort[c] > 0 and flag > 0:
        g.fort[c] -= 1
        fx = g.cityx[c]
        fy = g.cityy[c]
        scr.line(fx - 5, fy - 5, fx + 5, fy + 5, 2, "BF")
        showcity(g)
        if s_side != g.side:                               # notify player
            fort_dmg = f"{g.city[c]} fortifications damaged in battle"
            scribe(g, fort_dmg, 2)

    scr.update()


# ═══════════════════════════════════════════════════════════════════════════
#  SUB evaluate (index, x)                                     Lines 300-386
#
#  AI move evaluation. Scores each adjacent city and returns the best.
#  GOTO labels: alleval (break), alle (continue), ourn (skip), tally3 (continue)
# ═══════════════════════════════════════════════════════════════════════════

def evaluate(g: 'GameState', index: int) -> int:
    """AI: evaluate best move for army. Returns adjacency index (1-6) or 0."""
    from cws_util import starfin
    from cws_misc import void

    from_ = g.armyloc[index]                               # L301
    x_thresh = 200                                         # L302
    if g.aggress > 1.5:
        x_thresh = 80
        if g.aggress > 2:
            x_thresh = 20
            if g.aggress > 3:
                x_thresh = 5

    defend_str = void(g, from_)                            # L303
    if defend_str == 0:
        x_thresh = 0
    if g.bold > 1:                                         # L304
        x_thresh = int(0.5 * x_thresh)

    best_str = g.armysize[index]                           # L306

    for j in range(1, 7):                                  # L308
        g.array[j] = -1
        a = g.matrix[from_][j]
        if a > 0 and g.occupied[a] > 0:                   # L309
            best_str -= g.armysize[g.occupied[a]]
    best_str = int(0.01 * best_str)                        # L310
    if g.bold > 0:                                         # L311
        best_str = best_str + 20 * g.bold

    star, fin = starfin(g, g.enemy_of())                    # L313

    max_j = 6                                              # will be set by loop
    for j in range(1, 7):                                  # L315
        y_score = -1                                       # L316
        a = g.matrix[from_][j]
        if a == 0:
            max_j = j - 1                                  # alleval
            break

        # Check if enemy is already targeting this city     L318-320
        c = g.occupied[a]
        skip_city = False
        for k in range(star, fin + 1):                     # L319
            if g.armyloc[k] > 0 and g.armymove[k] == a and c == 0:
                skip_city = True                           # alle
                break
        if skip_city:
            continue

        # Score this city                                   L322
        y_score = (best_str - x_thresh * g.fort[from_]
                   - g.cityv[from_] + int(30 * random.random()))
        if g.fort[from_] > 0:                              # L323
            if index == g.occupied[from_]:
                y_score -= 25
                if g.realism > 0:
                    y_score -= 50
        if a == g.capcity[g.side]:                         # L324
            if g.vicflag[5] > 0:
                y_score += 200
        if g.cityp[a] != g.enemy_of():                     # L325
            y_score += 5 * g.cityv[a] + 10 * g.fort[a]

        if g.cityp[a] != g.side:                           # L326: not our city
            pass  # skip to ourn (combat scoring below doesn't apply)
        else:
            # Enemy city - evaluate attack                  L327-356
            if c == 0:                                     # L327
                y_score += 10 * g.cityv[a]
            else:
                x1 = 1                                     # L328
                if g.fort[a] == 1:
                    x1 = 2
                if g.fort[a] == 3:
                    x1 = 3

                if g.armysize[c] > 0:                      # L330
                    odds = g.armysize[index] / (x1 * g.armysize[c])  # L331
                    if g.realism > 1:                      # L332
                        odds = 0.8 * odds
                else:
                    odds = 5                               # L334

                if g.armysize[index] < 15:                 # L337
                    y_score -= 300
                    odds = 0.1
                if g.bold < 3 and g.armysize[index] < 40 and odds < 0.8:  # L338
                    y_score = 0
                if g.realism > 0:                          # L339
                    y_score -= 15
                if odds < 0.5:                             # L340
                    y_score -= 200
                if g.bold == 0 and random.random() > 0.9:  # L341
                    y_score += 10 * (g.armylead[index] - g.armylead[c]
                                     + g.armyexper[index] - g.armylead[index])
                if g.supply[index] < 1:                    # L342
                    y_score -= 100

                # SELECT CASE odds + .5 * bold              L343-356
                val = odds + 0.5 * g.bold
                if val < 0.3:
                    y_score = -9999
                elif val < 0.5:
                    y_score -= 300
                elif val <= 0.8:
                    y_score -= 20
                elif val <= 1.2:
                    y_score -= 5
                elif val <= 1.5:
                    y_score += 10
                else:
                    y_score += int(0.5 * (g.armysize[index] - g.armysize[c])
                                   + 50 * random.random())

        # ourn:                                             L357-374
        if g.cityp[a] == g.enemy_of() and c > 0 and g.armymove[c] == 0:  # L358
            y_score -= g.armysize[c]
        if g.side == UNION and g.cityy[a] < g.cityy[from_]:   # L359
            y_score += 2
        if g.side == CONFEDERATE and g.cityy[a] > g.cityy[from_]:   # L360
            y_score += 2

        # Look-ahead: score adjacent cities (2 hops)       L362-372
        for k in range(1, 7):                              # L362
            m = g.matrix[a][k]
            if m == 0:                                     # tally3
                break
            if g.cityp[m] == 0:                            # L363
                y_score += 3 * g.cityv[m] + 4 * g.fort[m]
            if g.cityp[m] == g.side:                       # L364 (enemy city)
                y_score += 3 * g.cityv[m] + 4 * g.fort[m]
            if g.cityp[m] == g.side and c > 0:            # L365
                if g.armysize[c] > 0:                      # L367
                    lk_odds = g.armysize[index] / g.armysize[c]
                else:
                    lk_odds = 5
                if lk_odds < 1:                            # L368
                    y_score -= 2
            if g.cityp[m] == g.capcity[g.side]:            # L370
                y_score += 50

        g.array[j] = y_score                               # L374
    else:
        max_j = 6                                          # L376

    # Find best scoring city                                L378-385
    # alleval:
    x_best = 0                                             # L378
    best = 0
    for j in range(1, max_j + 1):                          # L379
        if g.array[j] < 0:                                 # L380: allof
            continue
        if g.array[j] > x_best:                            # L381
            x_best = g.array[j]
            best = j

    if defend_str > g.armysize[index] and best > 0 and g.array[best] < 50:  # L384
        best = 0

    return best                                            # L385


# ═══════════════════════════════════════════════════════════════════════════
#  SUB retreat (defend, x)                                     Lines 387-407
# ═══════════════════════════════════════════════════════════════════════════

def retreat(g: 'GameState', defend: int) -> int:
    """Player retreat selection. Returns city index to retreat to, or 0."""
    from cws_util import bubble
    from cws_ui import menu, clrrite

    # AI armies don't get player retreat choice             L389-391
    if g.player == 1:
        if (g.side == UNION and defend > 20) or (g.side == CONFEDERATE and defend < 21):
            return 0

    g.hilite = 13                                          # L393
    g.colour = 3
    g.tlx = 67
    g.tly = 5
    g.size = 0

    yy = g.armyloc[defend]                                 # L394
    who = UNION                                             # L395
    if defend > 20:
        who = CONFEDERATE

    for k in range(1, 7):                                  # L396-398
        mk = g.matrix[yy][k]
        if mk > 0 and g.cityp[mk] == who:
            g.size += 1
            g.mtx[g.size] = g.city[mk]
            g.array[g.size] = mk

    if g.size == 0:                                        # L399
        return 0
    if g.size == 1:                                        # L400
        return g.array[1]

    g.mtx[0] = "Retreat"                                   # L401
    bubble(g, g.size)                                      # L402
    menu(g, 9)                                             # L403
    clrrite(g)                                             # L404

    if g.choose < 0 or g.choose > g.size:                  # L405
        return 0
    return g.array[g.choose]                               # L406


# ═══════════════════════════════════════════════════════════════════════════
#  SUB surrender (who)                                         Lines 408-530
# ═══════════════════════════════════════════════════════════════════════════

def surrender(g: 'GameState', who: int) -> None:
    """Draw surrender scene. Exact port of QB64 SUB surrender (L408-530)."""
    from cws_util import tick
    from cws_ui import flags

    s = g.screen
    ss = UNION                                              # L410
    c = 1
    s.color(0)
    w = 514
    if who > 20:
        c = 7
        ss = CONFEDERATE

    # Background panels                                     L412-415
    s.line(w + 15, 440, w + 125, 16, 2, "BF")             # L413
    s.line(w + 15, 16, w + 125, 290, 3, "BF")             # L414
    s.line(w + 14, 16, w + 125, 440, c, "B")              # L415

    x = 77                                                 # L416
    y = 280

    # Ground ellipse                                        L417-418
    s.circle(w + x + 10, y + 30, 30, 4, aspect=0.1)       # L417
    s.paint(w + x + 10, y + 30, 6, 4)                     # L418

    # Body outline                                          L419-434
    s.line(w + x, y + 28, w + x + 6, y + 28, 0)           # L419
    s.line_to(w + x + 6, y + 8, 0)
    s.line_to(w + x + 8, y + 8, 0)                        # L420
    s.line_to(w + x + 8, y + 28, 0)
    s.line_to(w + x + 12, y + 28, 0)                      # L421
    s.line_to(w + x + 12, y + 12, 0)
    s.line_to(w + x + 15, y + 12, 0)                      # L422
    s.line_to(w + x + 15, y + 30, 0)
    s.line_to(w + x + 18, y + 30, 0)                      # L423
    s.line_to(w + x + 18, y + 20, 0)
    s.line_to(w + x + 21, y + 21, 0)                      # L424
    s.line_to(w + x + 21, y + 32, 0)
    s.line_to(w + x + 25, y + 32, 0)                      # L425
    s.line_to(w + x + 25, y + 17, 0)
    s.line_to(w + x + 27, y + 17, 0)                      # L426
    s.line_to(w + x + 25, y - 10, 0)
    s.line_to(w + x + 19, y - 14, 0)                      # L427
    s.line_to(w + x + 15, y - 5, 0)
    s.line_to(w + x + 12, y - 12, 0)                      # L428
    s.line_to(w + x + 8, y - 15, 0)
    s.line_to(w + x + 6, y - 15, 0)                       # L429
    s.line_to(w + x + 6, y - 11, 0)
    s.line_to(w + x + 3, y - 14, 0)                       # L430
    s.line_to(w + x + 2, y - 14, 0)
    s.line_to(w + x + 1, y - 10, 0)                       # L431
    s.line_to(w + x - 3, y - 11, 0)
    s.line_to(w + x - 3, y + 15, 0)                       # L432
    s.line_to(w + x, y + 15, 0)
    s.line_to(w + x, y - 3, 0)                            # L433
    s.line_to(w + x + 2, y - 3, 0)
    s.line_to(w + x, y + 28, 0)                           # L434
    s.paint(w + x + 10, y, 8 - c, 0)                      # L435

    # Eyes                                                  L437-438
    s.circle(w + x + 7, y - 10, 3, 0)                     # L437
    s.paint(w + x + 7, y - 10, 0, 0)
    s.circle(w + x + 20, y - 8, 3, 0)                     # L438
    s.paint(w + x + 20, y - 8, 0, 0)

    # Hair lines                                            L440-444
    s.line(w + x + 5, y - 30, w + x + 6, y - 9, 0)       # L440
    s.line(w + x + 20, y, w + x + 35, y + 30, 0)         # L441
    s.line(w + x + 20, y + 1, w + x + 35, y + 31, 0)     # L442
    s.line(w + x + 22, y - 31, w + x + 21, y - 8, 0)     # L443
    s.line(w + x - 1, y - 28, w + x, y - 8, 0)           # L444

    # Boot                                                  L446-452
    s.circle(w + 37, 425, 22, 8, aspect=0.3)              # L446
    s.paint(w + 37, 430, 8, 8)                             # L447
    s.line(w + 26, 426, w + 46, 426, 0)                   # L448
    s.line_to(w + 46, 423, 0)                              # L449
    s.line_to(w + 36, 419, 0)
    s.line_to(w + 36, 397, 0)                              # L450
    s.line_to(w + 26, 397, 0)
    s.line_to(w + 26, 426, 0)                              # L451
    s.paint(w + 27, 399, 0, 0)                             # L452

    # Arm                                                   L454-459
    s.line(w + 26, 397, w + 25, 396, 0)                   # L454
    s.line_to(w + 24, 374, 0)
    s.line_to(w + 25, 346, 0)                              # L455
    s.line(w + 25, 346, w + 22, 341, 0)
    s.line_to(w + 46, 341, 0)                              # L456
    s.line_to(w + 46, 349, 0)
    s.line_to(w + 41, 365, 0)                              # L457
    s.line_to(w + 41, 380, 0)
    s.line_to(w + 36, 398, 0)                              # L458
    s.paint(w + 30, 350, c, 0)                             # L459

    # Saber                                                 L461-476
    s.line(w + 55, 288, w + 58, 360, 14, "BF")            # L461
    s.line(w + 55, 288, w + 55, 360, 14)                   # L462
    s.line(w + 56, 361, w + 55, 360, 14)                   # L463
    s.line(w + 57, 361, w + 58, 350, 14)                   # L464
    s.line(w + 58, 350, w + 58, 288, 14)                   # L465
    s.line(w + 55, 272, w + 62, 288, 6, "B")              # L466
    s.line(w + 56, 273, w + 61, 287, 6, "B")              # L467
    s.line(w + 57, 274, w + 60, 286, 6, "B")              # L468
    s.line(w + 54, 295, w + 60, 305, 12, "BF")            # L470
    s.line(w + 53, 294, w + 61, 306, 0, "B")              # L471
    s.line(w + 57, 303, w + 61, 303, 0)                   # L472
    s.line(w + 57, 298, w + 61, 298, 0)                   # L473
    s.line(w + 34, 310, w + 46, 312, c, "BF")             # L474
    s.line(w + 25, 380, w + 35, 378, 0)                   # L475
    s.line(w + 25, 365, w + 34, 366, 0)                   # L476

    # Shoulder / torso                                      L478-498
    s.color(0)                                              # L478
    s.line(w + 53, 297, w + 31, 305, 0)                   # L479
    s.line_to(w + 25, 270, 0)
    s.line_to(w + 18, 270, 0)                              # L480
    s.line_to(w + 16, 275, 0)
    s.line_to(w + 21, 309, 0)                              # L481
    s.line_to(w + 28, 316, 0)
    s.line_to(w + 52, 306, 0)                              # L482
    s.line_to(w + 53, 298, 0)
    s.paint(w + 20, 280, c, 0)                             # L483
    s.line(w + 30, 310, w + 32, 305, 0)                   # L484
    s.line_to(w + 25, 307, 0)
    s.line(w + 46, 298, w + 47, 275, 0)                   # L485
    s.line(w + 47, 275, w + 41, 269, 0)                   # L486
    s.line(w + 41, 269, w + 25, 269, 0)                   # L487
    s.paint(w + 45, 275, c, 0)                             # L488
    s.circle(w + 40, 275, 1, 14)                           # L489
    s.circle(w + 40, 285, 1, 14)                           # L490
    s.circle(w + 40, 295, 1, 14)                           # L491

    # Lower torso                                           L493-498
    s.line(w + 21, 306, w + 18, 340, 0)                   # L493
    s.line(w + 18, 340, w + 47, 340, 0)                   # L494
    s.line(w + 46, 310, w + 48, 339, 0)                   # L495
    s.paint(w + 30, 330, c, 0)                             # L496
    s.line(w + 46, 312, w + 21, 316, 0, "BF")             # L497
    s.line(w + 25, 312, w + 35, 313, c, "BF")             # L498

    # Hat                                                   L500-514
    s.line(w + 30, 268, w + 41, 264, 12, "BF")            # L500
    s.line(w + 30, 263, w + 41, 263, 0)                   # L501
    s.line(w + 30, 264, w + 26, 260, 0)                   # L502
    s.line_to(w + 25, 248, 0)
    s.line_to(w + 28, 243, 0)                              # L503
    s.line_to(w + 46, 243, 0)
    s.line_to(w + 48, 245, 0)                              # L504
    s.line_to(w + 48, 248, 0)
    s.line_to(w + 51, 254, 0)                              # L505
    s.line_to(w + 51, 255, 0)
    s.line_to(w + 48, 256, 0)                              # L506
    s.line_to(w + 48, 261, 0)
    s.line_to(w + 46, 263, 0)                              # L507
    s.line_to(w + 39, 263, 0)
    s.paint(w + 40, 250, 12, 0)                            # L508

    # Hat brim                                              L510-514
    s.line(w + 16, 242, w + 57, 241, 0, "BF")             # L510
    s.line(w + 45, 240, w + 28, 240, 0)                   # L511
    s.line_to(w + 31, 232, 0)                              # L512
    s.line_to(w + 45, 232, 0)
    s.line_to(w + 48, 240, 0)                              # L513
    s.paint(w + 40, 235, c, 0)                             # L514

    # Flagpole                                              L516
    s.line(w + 80, 303, w + 81, 200, 6, "BF")             # L516

    # Face detail                                           L518-526
    s.line(w + 48, 251, w + 44, 250, 0, "B")              # L518
    s.line(w + 29, 263, w + 43, 266, 0)                   # L519
    s.line_to(w + 46, 266, 0)                              # L520
    s.line_to(w + 48, 263, 0)
    s.line_to(w + 48, 260, 0)                              # L521
    s.line_to(w + 37, 258, 0)
    s.line_to(w + 36, 255, 0)                              # L522
    s.line_to(w + 37, 250, 0)
    s.line_to(w + 39, 246, 0)                              # L523
    s.line_to(w + 40, 243, 0)

    c2 = 0                                                 # L524
    if ss == CONFEDERATE:
        c2 = 15
        s.line(547, 263, 558, 263, 15)
    s.paint(w + 33, 250, c2, 0)                            # L525
    s.paint(w + 42, 264, c2, 0)                            # L526

    # Flag                                                  L528
    flags(g, g.enemy_of(ss), 26, 0)
    if who < 99:                                           # L529
        tick(g, g.turbo)
    s.update()


# ═══════════════════════════════════════════════════════════════════════════
#  Helper: wait for keypress
# ═══════════════════════════════════════════════════════════════════════════

def _wait_key() -> None:
    """Block until any key pressed."""
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
