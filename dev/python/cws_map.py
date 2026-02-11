"""cws_map.py - Map display and turn resolution.
Direct port of cws_map.bm (810 lines).

Contains:
    flashcity(g, which)           L1-13    - flash a city marker
    icon(g, from_, dest, kind)    L15-88   - movement/effect icons (11 types)
    showcity(g)                   L89-113  - draw all city markers
    snapshot(g, x, y, flag)       L114-117 - save/restore small screen area
    tupdate(g)                    L118-388 - turn update (THE core game loop)
    image2(g, text, s)            L389-409 - message popup
    maptext(g)                    L410-427 - city name labels
    touchup(g)                    L428-488 - map detail lines
    usa(g)                        L489-809 - draw full game map

QB64 GOTO flow in tupdate() is restructured as:
    - Main for loop: break=allthru, continue=digin
    - Inner while loop: enemy -> holdon -> enemy cycle
    - Flags: goto_easy, goto_digin to route after enemy loop
"""

import pygame
import random
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cws_globals import GameState


# ═══════════════════════════════════════════════════════════════════════════
#  SUB flashcity (which)                                        Lines 1-13
# ═══════════════════════════════════════════════════════════════════════════

def flashcity(g: 'GameState', which: int) -> None:
    """Flash a city marker with color cycling animation."""
    from cws_util import tick
    s = g.screen
    cx, cy = g.cityx[which], g.cityy[which]
    for c in range(1, 16, 2):                              # L2
        s.circle(cx, cy, 4, 0)                             # L3
        s.circle(cx, cy, 3, c, fill=True)                  # L4-5
        tick(g, 0.1)                                       # L6
    c = 9                                                  # L8
    if g.cityp[which] == 2:
        c = 7
    if g.cityp[which] == 0:                                # L9
        c = 12
    s.circle(cx, cy, 4, 0)                                # L10
    s.circle(cx, cy, 3, c, fill=True)                      # L11-12


# ═══════════════════════════════════════════════════════════════════════════
#  SUB icon (from, dest, kind)                                  Lines 15-88
# ═══════════════════════════════════════════════════════════════════════════

def _clear_arrow(g: 'GameState') -> None:
    """Restore the background under any existing arrow cursor."""
    pos = getattr(g, '_arrow_save_pos', None)
    img = getattr(g, '_arrow_save', None)
    if pos and img is not None:
        g.screen.put_image(pos[0], pos[1], img)
    g._arrow_save = None
    g._arrow_save_pos = None


def icon(g: 'GameState', from_: int, dest: int, kind: int) -> None:
    """Draw various movement/effect icons. All 11 CASE types ported."""
    if from_ < 1 or from_ > 40:                           # L16: noshow
        return
    if dest < 0:                                           # L17
        return
    if from_ == 999:                                       # L18
        return

    s = g.screen
    x = g.cityx[from_] - 12                               # L19
    y = g.cityy[from_] - 11
    # dest may be 0 (no destination); cityx[0]=cityy[0]=0
    x1 = g.cityx[dest] if 0 <= dest <= 40 else 0          # L20
    y1 = g.cityy[dest] if 0 <= dest <= 40 else 0

    if kind == 1:                                          # L22-23
        # White dashed movement line
        s.line(x, y, x1, y1, 15, pattern=0xF0F0)

    elif kind == 2:                                        # L25-29
        # Recruitment flash (yellow boxes)
        from cws_util import tick
        for i in range(6, 9):                              # L26
            s.line(x - i, y - i + 3, x + i, y + i - 3, 14, "B")
        tick(g, 0.1)                                       # L29

    elif kind == 3:                                        # L31-42
        # Battle explosion (red circles + yellow fill)
        from cws_util import tick
        cx = g.cityx[from_]                                # L32: different offset
        cy = g.cityy[from_]
        snapshot(g, cx, cy, 0)                             # L33
        for j in range(1, 4):                              # L34
            for i in range(4, 11):                         # L35
                s.circle(cx, cy, i, 4)                     # L36
                s.circle(cx, cy, max(1, i - 1), 14, fill=True)  # L37: PAINT simplified
                if g.noise > 0:                              # L38
                    from cws_sound import qb_sound
                    qb_sound(37 + 50 * random.random(), 0.03)
            tick(g, 0.1)                                   # L40
            snapshot(g, cx, cy, 1)                         # L41

    elif kind == 4:                                        # L44-48
        # Erase movement (green overwrite)
        if g.occupied[from_] == 0:                         # L45
            s.line(x - 8, y - 6, x + 10, y + 8, 2, "BF")
        if x1 + y1 > 0:                                   # L46
            s.line(x, y, x1, y1, 2, pattern=0xF0F0)
        if from_ == 27 or from_ == 28:                    # L47
            touchup(g)

    elif kind == 5:                                        # L49-50
        # Erase line only
        if x1 + y1 > 0:
            s.line(x, y, x1, y1, 2, pattern=0xF0F0)

    elif kind == 6:                                        # L52-59
        # Meeting/fortification flash (white boxes)
        from cws_util import tick
        cx = g.cityx[from_]                                # L53: different offset
        cy = g.cityy[from_]
        snapshot(g, cx, cy, 0)                             # L54
        s.line(cx - 9, cy - 9, cx + 9, cy + 9, 15, "B")  # L55
        s.line(cx - 10, cy - 10, cx + 10, cy + 10, 15, "B")  # L56
        if g.noise > 0:                                      # L57
            from cws_sound import qb_sound
            qb_sound(3999, 0.3)
        tick(g, max(0, g.turbo - 0.5))                    # L58
        snapshot(g, cx, cy, 1)                             # L59

    elif kind == 7:                                        # L60-64
        # Save image and draw white highlight box
        _clear_arrow(g)                                    # auto-clean any arrow
        g._saved_image = s.get_image(x - 8, y - 8, x + 8, y + 8)  # L62
        g._saved_image_pos = (x - 8, y - 8)
        s.line(x - 7, y - 7, x + 7, y + 7, 15, "B")     # L63
        s.line(x - 8, y - 6, x + 8, y + 6, 15, "B")     # L64

    elif kind == 8:                                        # L65-67
        # Restore saved image
        _clear_arrow(g)                                    # auto-clean any arrow
        pos = getattr(g, '_saved_image_pos', None)
        img = getattr(g, '_saved_image', None)
        if pos and img is not None:
            s.put_image(pos[0], pos[1], img)               # L67
        g._saved_image = None
        g._saved_image_pos = None

    elif kind == 9:                                        # L69-80
        # Arrow pointer — auto-clean any existing arrow first
        _clear_arrow(g)
        g._arrow_save = s.get_image(x - 8, y - 8, x + 10, y + 7)  # L71
        g._arrow_save_pos = (x - 8, y - 8)
        x = x + 7                                         # L72
        y = y + 5
        # L80: PAINT (x-2, y-1), 15, 12 — fill interior white
        arrow_pts = [
            (x + 2, y), (x + 2, y - 8), (x, y - 6),
            (x - 5, y - 11), (x - 10, y - 6), (x - 6, y - 2),
            (x - 10, y), (x + 1, y),
        ]
        s.polygon(arrow_pts, 15, fill=True)                # L80
        # Outline in red                                   L73-79
        s.line(x + 2, y, x + 2, y - 8, 12)               # L73
        s.line_to(x, y - 6, 12)                           # L74
        s.line_to(x - 5, y - 11, 12)                      # L75
        s.line_to(x - 10, y - 6, 12)                      # L76
        s.line_to(x - 6, y - 2, 12)                       # L77
        s.line_to(x - 10, y, 12)                          # L78
        s.line_to(x + 1, y, 12)                           # L79

    elif kind == 11:                                       # L82-83
        # Dim connection line (black dashed)
        s.line(x + 12, y + 11, x1, y1, 0, pattern=0x1111)

    # CASE ELSE: nothing                                   # L85-86
    # noshow: (end)                                        # L87-88


# ═══════════════════════════════════════════════════════════════════════════
#  SUB showcity                                                 Lines 89-113
# ═══════════════════════════════════════════════════════════════════════════

def showcity(g: 'GameState') -> None:
    """Draw all city markers with owner colors, forts, and adjacency lines."""
    s = g.screen
    for i in range(1, 41):                                 # L90
        c = 9                                              # L91: Union blue
        if g.cityp[i] == 2:
            c = 7                                          # Confederate gray
        if g.cityp[i] == 0:                                # L92
            c = 12                                         # Neutral red
        cx = g.cityx[i]                                    # L93
        cy = g.cityy[i]

        if i == g.capcity[1] or i == g.capcity[2]:        # L94
            # Capital city: special marker
            if hasattr(g, 'ncap_surface') and g.ncap_surface is not None:
                s.put_image(cx - 6, cy - 6, g.ncap_surface)  # L95: PUT Ncap
            else:
                s.line(cx - 6, cy - 6, cx + 6, cy + 6, 15, "B")
            # L96-98: side box
            s.line(cx + 9, cy - 4, cx + 15, cy + 4, 0, "BF")
            s.line(cx + 8, cy - 5, cx + 13, cy + 2, 3, "BF")
            s.pset(cx + 8, cy - 4, 0)                     # L98: sets cursor
            # L99-100: fort DRAW commands
            if g.fort[i] == 1:
                s.draw("BR2C0E1D6BL1R2")
            elif g.fort[i] == 2:
                s.draw("C0E1R1F1D1G3R3")
        else:                                              # L101
            if g.fort[i] == 1:                             # L102
                s.line(cx - 5, cy - 5, cx + 5, cy + 5, 0, "B")
            if g.fort[i] > 1:                              # L103
                s.line(cx - 5, cy - 5, cx + 5, cy + 5, 0, "BF")
            s.circle(cx, cy, 4, 0)                        # L104
            s.circle(cx, cy, 3, c, fill=True)              # L105-106

        if g.graf == 0:                                    # L108: GOTO nocon
            continue
        for j in range(1, 7):                              # L109
            if g.matrix[i][j] > 0:
                icon(g, i, g.matrix[i][j], 11)
        # nocon:                                           # L111


# ═══════════════════════════════════════════════════════════════════════════
#  SUB snapshot (x, y, flag)                                    Lines 114-117
# ═══════════════════════════════════════════════════════════════════════════

def snapshot(g: 'GameState', x: int, y: int, flag: int) -> None:
    """Save (flag=0) or restore (flag=1) small screen area via snapshot buffer.

    Uses a separate buffer (g._snap_image) so it doesn't clobber the
    icon save/restore buffer (g._saved_image) used by icon kinds 7/8/9.
    """
    s = g.screen
    if flag == 0:                                          # L115
        g._snap_image = s.get_image(x - 10, y - 10, x + 10, y + 10)
    elif flag == 1:                                        # L116
        if hasattr(g, '_snap_image') and g._snap_image is not None:
            s.put_image(x - 10, y - 10, g._snap_image)


# ─── Helper: GOSUB upbox (Lines 334-340) ─────────────────────────────────

def _upbox(g: 'GameState') -> None:
    """Draw the UPDATE status box."""
    s = g.screen
    s.line(450, 318, 526, 420, 1, "BF")                   # L335
    s.line(527, 315, 527, 439, 10)                         # L336
    s.color(14)                                            # L337
    s.locate(23, 50)
    s.print_text("+-------------+")
    s.locate(24, 50)                                       # L338
    s.print_text("| U P D A T E |")
    s.locate(25, 50)                                       # L339
    s.print_text("+-------------+")


# ═══════════════════════════════════════════════════════════════════════════
#  SUB tupdate                                                  Lines 118-388
#
#  GOTO labels restructured:
#    allthru  → break from main for loop
#    digin    → continue (next j)
#    friend   → inline before goto_easy
#    enemy    → inner while True loop
#    kickbutt → if win==active branch
#    outta    → defender retreat path
#    deadmeat → no retreat → crushed
#    crushed  → clear army, fall to holdon
#    holdon   → check more defenders, loop or goto_easy
#    easy     → move into city, capture check
#    horde    → resupply while loop
#    smoke    → do_smoke flag for fort razing
# ═══════════════════════════════════════════════════════════════════════════

def tupdate(g: 'GameState') -> None:
    """Turn update phase: AI/moves, combat resolution, commerce, VP calc."""
    from cws_ai import smarts
    from cws_util import tick, bub2, animate, stax
    from cws_ui import clrbot, clrrite, scribe
    from cws_army import placearmy
    from cws_combat import battle, capture, retreat, surrender
    from cws_data import occupy
    from cws_railroad import railroad
    from cws_flow import engine
    from cws_navy import ships, barnacle, shipicon
    from cws_flow import iterate

    s = g.screen
    flag = 0                                               # L119

    # ── AI turn or show pending moves ──                    L120-126
    if g.player == 1:                                      # L120
        smarts(g)                                          # L121
    else:                                                  # L122
        for i in range(1, 41):                             # L123
            if g.armyloc[i] > 0 and g.armymove[i] > 0:    # L124
                icon(g, g.armyloc[i], g.armymove[i], 1)

    s.color(14)                                            # L127
    s.locate(1, 1)
    s.print_text(" " * 80)
    s.locate(1, 20)                                        # L128
    s.print_text(f"Update for {g.month_names[g.month]}, {g.year}")
    clrbot(g)                                              # L129
    s.print_text(f"press any key for {g.month_names[g.month]}, {g.year} events")
    s.update()
    _wait_key()                                            # L130
    _upbox(g)                                              # L131: GOSUB upbox

    # ══════════════════════════════════════════════════════════════════
    #                    Railroad Phase                       L135-136
    # ══════════════════════════════════════════════════════════════════
    for i in range(1, 3):                                  # L135
        if g.rr[i] > 0:
            railroad(g, i)
            s.line(5, 17, 100, 63, 3, "BF")
            s.line(5, 17, 100, 63, 0, "B")
            engine(g)

    # Clear railroad display if no railroads remain
    if g.rr[1] + g.rr[2] == 0:
        s.line(5, 17, 100, 63, 2, "BF")                   # repaint map green

    # ══════════════════════════════════════════════════════════════════
    #                    Assign Time of Action                L138-157
    # ══════════════════════════════════════════════════════════════════
    for i in range(1, 41):                                 # L138
        g.brray[i] = 999                                   # L139
        if g.armymove[i] < 0:                              # L140
            g.armymove[i] = 0
        if g.armyloc[i] > 0 and g.armymove[i] > 0:        # L141
            g.brray[i] = int(4 + 4 * random.random()) * 100 + i
        if g.supply[i] < 1 and g.armymove[i] > 0:         # L142
            g.brray[i] = 900 + i

        # L143-152: SELECT CASE armysize -- bigger armies move slower
        # NOTE: QB64 evaluates top-to-bottom; CASE IS > 400 matches first,
        # making >800 and >1000 branches UNREACHABLE. Bug preserved.
        if g.armysize[i] > 400:                            # CASE IS > 400
            if g.brray[i] < 900:
                g.brray[i] += 100
            x = 2
        else:                                              # CASE ELSE
            x = 1

        # Good leaders move faster                          L153-156
        if g.brray[i] != 999 and g.armylead[i] > 10 * random.random():
            g.brray[i] -= 100 * (g.armylead[i] // 2)      # L154
            if g.brray[i] < 100:                           # L155
                g.brray[i] = 100 + i

    bub2(g, 40)                                            # L159

    # ══════════════════════════════════════════════════════════════════
    #                    Begin Main Loop                      L163-331
    # ══════════════════════════════════════════════════════════════════
    for j in range(1, 41):                                 # L163
        flag = 0                                           # L164
        if g.brray[j] == 999:                              # L165: → allthru
            break

        active_raw = g.brray[j] // 100                     # L166
        active = g.brray[j] - 100 * active_raw
        s_side = 1                                         # 's' in original
        if active > 20:
            s_side = 2

        if g.armymove[active] < 1:                         # L167: → digin
            continue

        # ── Display move, consume supply ──                 L168-171
        s.color(11)                                        # L168
        clrbot(g)
        s.print_text(f"{g.armyname[active]} is moving to {g.city[g.armymove[active]]}")

        g.supply[active] -= 1                              # L170
        if g.supply[active] < 0:
            g.supply[active] = 0
            tick(g, g.turbo)
            clrbot(g)
            s.print_text(f"{g.armyname[active]} is out of supplies !")

        placearmy(g, active)                               # L172
        icon(g, g.armyloc[active], g.armymove[active], 5)  # L173
        animate(g, active, 0)                              # L175

        # ── Target and encounter type ──                    L177-179
        target = g.armymove[active]                        # L177
        goto_easy = False
        goto_digin = False

        if g.occupied[target] == 0:                        # L178: → easy
            goto_easy = True

        elif (s_side == 1 and g.occupied[target] < 21) or \
             (s_side == 2 and g.occupied[target] > 20):    # L179: → friend
            # ── friend ──                                   L183-187
            s.color(11)                                    # L184
            clrbot(g)
            s.print_text(
                f"{g.armyname[active]} and {g.armyname[g.occupied[target]]} "
                f"meet in {g.city[target]}"
            )
            tick(g, g.turbo)
            icon(g, g.armymove[active], 0, 6)              # L185
            clrbot(g)                                      # L186
            goto_easy = True                               # L187: → easy

        else:
            # ════════════════════════════════════════════════
            #  enemy engagement loop (enemy → holdon → enemy)
            # ════════════════════════════════════════════════
            while True:
                # ── enemy ──                                L191-196
                icon(g, target, 0, 3)                      # L192
                defend = g.occupied[target]                 # L193

                s.color(11)                                # L195
                clrbot(g)
                s.print_text(
                    f"{g.armyname[active]} attacks {g.armyname[defend]} "
                    f"in {g.city[g.armyloc[defend]]}"
                )
                tick(g, max(0, g.turbo - 1))

                win = 0
                lose = 0
                if g.armysize[defend] > 0:                 # L196
                    win, lose = battle(g, active, defend)
                    flag = 1
                    if g.graf > 0:
                        _upbox(g)

                if win > 0 and g.armyexper[win] < 10:      # L197
                    g.armyexper[win] += 1

                index = 0
                do_crushed = False
                do_outta = False

                # ── Check if army crushed ──                L199-204
                if lose > 0 and g.armysize[lose] < 2:
                    clrbot(g)                              # L200
                    a_str = (f"{g.armyname[lose]}'s army is crushed in "
                             f"{g.city[g.armyloc[defend]]}")
                    scribe(g, a_str, 2)                    # L202
                    index = lose                           # L203
                    do_crushed = True                      # → crushed

                else:
                    clrrite(g)                             # L206

                    if win == active:                       # L210: → kickbutt
                        # ── kickbutt ──                     L230-264
                        icon(g, g.armyloc[active], target, 4)  # L231
                        if g.armymove[defend] > 0:         # L232
                            icon(g, target, g.armymove[defend], 4)

                        flee = retreat(g, defend)          # L234
                        if flee > 0:
                            move2 = flee                   # → outta
                            do_outta = True
                        else:
                            # Manual retreat search          L236-248
                            best = 0
                            flee_idx = 0
                            for ii in range(1, 7):         # L237
                                xx = g.matrix[target][ii]
                                if xx > 0 and g.cityp[xx] == 3 - s_side and g.cityv[xx] > best:
                                    if best == 0:          # L240
                                        flee_idx = ii
                                        best = g.cityv[xx]
                                    else:
                                        if g.occupied[xx] == 0:  # L243
                                            flee_idx = ii
                                            best = g.cityv[xx]

                            if flee_idx == 0:              # L247: → deadmeat
                                # ── deadmeat ──             L266-269
                                index = defend
                                a_str = (f"{g.armyname[index]} surrenders to "
                                         f"{g.armyname[active]} in "
                                         f"{g.city[g.armyloc[index]]}")
                                scribe(g, a_str, 2)        # L269
                                do_crushed = True
                            else:
                                move2 = g.matrix[target][flee_idx]  # L248
                                do_outta = True

                    else:
                        # ── Attacker loses ──               L211-226
                        g.armymove[active] = g.armyloc[active]  # L211
                        g.armyloc[active] = target         # L212
                        s.color(11)                        # L213
                        clrbot(g)
                        s.print_text(
                            f"{g.armyname[active]} withdrew to "
                            f"{g.city[g.armymove[active]]}"
                        )
                        placearmy(g, g.armyloc[active])    # L215
                        animate(g, active, 1)              # L216

                        g.armyloc[active] = g.armymove[active]  # L218
                        placearmy(g, g.armyloc[active])    # L219
                        placearmy(g, active)               # L220
                        g.occupied[g.armyloc[active]] = active  # L221
                        g.armymove[active] = -2            # L222

                        # Chance defender cancels pursuit    L224
                        if 11 * random.random() > g.armylead[defend]:
                            icon(g, g.armyloc[defend], g.armymove[defend], 4)
                            if g.armymove[defend] > 0:
                                g.armymove[defend] = -2

                        tick(g, g.turbo)                   # L226
                        goto_digin = True
                        break  # exit enemy loop → digin

                # ── outta: defender retreats ──              L249-264
                if do_outta:
                    placearmy(g, defend)                    # L250
                    g.armymove[defend] = move2              # L252
                    animate(g, defend, 0)                   # L253
                    g.armyloc[defend] = move2               # L255
                    g.occupied[move2] = defend              # L256
                    clrbot(g)                              # L257
                    s.print_text(
                        f"{g.armyname[defend]} is withdrawing to {g.city[move2]}"
                    )
                    placearmy(g, defend)                    # L260
                    icon(g, target, 0, 6)                  # L262
                    g.armymove[defend] = -2                 # L263
                    # fall through to holdon

                # ── crushed: clear defeated army ──          L270-282
                if do_crushed and index > 0:
                    # L271: surrender visual
                    if g.graf > 2:
                        surrender(g, index)
                        s.color(14)
                        s.locate(3, 68)
                        s.print_text(g.armyname[index])
                        s.locate(4, 68)
                        s.print_text("surrenders !")
                    xx = 1                                 # L272
                    if index > 20:
                        xx = 2
                    if g.noise > 1 and xx != g.side:       # L273
                        from cws_sound import qb_play
                        qb_play("MFMST220o3e4g8g2.g8g8g8o4c2")
                    if g.armymove[index] > 0:              # L274
                        icon(g, g.armyloc[index], g.armymove[index], 4)
                    g.victory[3 - s_side] += 25            # L275
                    g.armyloc[index] = 0                   # L276
                    g.lname[index] = ""
                    g.armyname[index] = ""
                    g.armysize[index] = 0                  # L277
                    g.armylead[index] = 0
                    g.armyexper[index] = 0                 # L278
                    g.armymove[index] = 0
                    g.supply[index] = 0
                    # L279: BUG in original -- supply already 0, transfer lost
                    g.supply[active] = g.supply[active] + g.supply[index]
                    g.supply[index] = 0
                    if g.supply[active] > 10:              # L280
                        g.supply[active] = 10
                    tick(g, 9)                             # L281
                    clrrite(g)
                    if g.armyloc[active] == 0:             # L282: → digin
                        goto_digin = True
                        break  # exit enemy loop

                # ── holdon: check for more defenders ──     L286-289
                occupy(g, target)                          # L287
                if g.occupied[target] == 0:                # → easy
                    goto_easy = True
                    break  # exit enemy loop
                s.color(11)                                # L288
                clrbot(g)
                s.print_text(f"There are still defenders in {g.city[target]}")
                tick(g, 99)
                # continue enemy loop                      # L289: → enemy

            # ── After enemy loop ──
            if goto_digin:
                continue  # → digin (NEXT j)

        # ══════════════════════════════════════════════════
        #  easy: Move Into New City                 L293-327
        # ══════════════════════════════════════════════════
        if goto_easy:
            icon(g, g.armyloc[active], target, 4)          # L294
            g.armyloc[active] = target                     # L295
            g.armymove[active] = -2
            occupy(g, g.armyloc[active])                   # L296
            placearmy(g, active)                           # L297

            # ── City capture check ──                       L301-327
            if g.cityp[g.armyloc[active]] != s_side:       # L301
                c = g.armyloc[active]                      # L302
                do_smoke = False

                # Human captures fortified city: ask to raze L303-313
                if (g.player == 1 and s_side == g.side and
                        g.fort[c] > 0 and flag == 0):
                    from cws_ui import menu
                    g.tlx = 67                             # L304
                    g.tly = 15
                    g.hilite = 15                          # L305
                    g.colour = 3
                    g.mtx[0] = "Raze ?"                    # L306
                    g.mtx[1] = "No"                        # L307
                    g.mtx[2] = "Yes"                       # L308
                    g.size = 2                             # L309
                    menu(g, 0)                             # L310
                    clrrite(g)                             # L311
                    if g.choose == 2:                      # L312: → smoke
                        do_smoke = True

                # AI auto-raze if realism on                 L314-326
                if (g.player == 1 and s_side != g.side and
                        g.fort[c] > 0 and flag == 0):
                    if g.realism > 0 and g.cityy[c] > 150:  # L315
                        do_smoke = True

                if do_smoke:                               # smoke: L316-325
                    g.fort[c] = 0                          # L317
                    fx = g.cityx[c]                        # L318
                    fy = g.cityy[c]
                    s.line(fx - 5, fy - 5, fx + 5, fy + 5, 2, "BF")  # L320
                    showcity(g)                            # L321
                    clrbot(g)                              # L322
                    s.print_text(
                        f"{g.armyname[active]} has destroyed the forts at {g.city[c]}"
                    )
                    tick(g, 3)                             # L324

                capture(g, active, c, s_side, flag)        # L327

        # ── horde: resupply ──                              L328-329
        while g.supply[active] < 10:
            g.supply[active] += 1
            if random.random() <= 0.8:                     # 80% stop, 20% loop
                break

        # digin: (end of main loop body)                    L330-331
        s.update()

    # ══════════════════════════════════════════════════════════════════
    #                    allthru: Post-move phase             L342-388
    # ══════════════════════════════════════════════════════════════════

    # ── Commerce raiding ──                                  L343-372
    while True:
        if g.navysize[g.commerce] < 1:                     # L343
            g.commerce = 0
        if g.commerce <= 0:
            break

        clrbot(g)                                          # L345
        if random.random() < 0.8 + 0.02 * g.navysize[g.commerce]:  # L346
            # Successful raid
            g.raider = int(0.05 * g.navysize[g.commerce]
                           * (1 + random.random())
                           * g.income[3 - g.commerce])     # L347
            if g.raider < 1:                               # L348
                g.raider = 1
            denom = g.income[3 - g.commerce] if g.income[3 - g.commerce] > 0 else 1
            if g.raider / denom > 0.3:                     # L349
                g.raider = int(0.3 * g.income[3 - g.commerce])
            s.color(15)                                    # L350
            s.print_text(
                f"{g.force[g.commerce]} raiders have sunk ${g.raider} "
                f"of {g.force[3 - g.commerce]} commerce"
            )
            a = 1                                          # L351
            if g.fleet[g.commerce] and g.fleet[g.commerce][0] == "I":
                a = 2
            s.pset(500, 465, 0)                            # L352
            shipicon(g, g.commerce, a)
            if g.noise > 0:                                  # L353
                from cws_sound import qb_play
                qb_play("t210l8o4co3bo4l4co3ccL8gfego4co3bo4c")
            if g.commerce == g.side:                        # L354
                g.grudge = 1
            tick(g, 9)                                     # L355
            break  # done with commerce

        else:
            g.raider = 0                                   # L357
            barnacle(g, g.commerce)                        # L358
            s.color(15)                                    # L359
            s.print_text(
                f"{g.force[g.commerce]} raiders have lost a ship "
                f"({g.navysize[g.commerce]} remain)"
            )
            if g.noise > 0:                                # L360
                from cws_sound import qb_sound
                qb_sound(590, 0.5)
                qb_sound(999, 0.5)
                qb_sound(1999, 0.5)
            if g.navyloc[g.commerce] > 0:                  # L361
                tick(g, 9)                                 # L362
                continue                                   # L363: → allthru loop
            else:
                g.commerce = 0                             # L365
                s.line(447, 291, 525, 335, 1, "BF")       # L366
                for k in range(1, 6):                      # L367
                    s.circle(480, 315, 4 * k, 11)
                tick(g, 9)                                 # L368
                s.line(447, 291, 525, 335, 1, "BF")       # L369
                break

    # ── Final updates ──                                     L374
    touchup(g)
    ships(g)
    iterate(g)

    clrbot(g)                                              # L376
    s.line(390, 350, 520, 400, 1, "BF")                   # L377
    s.color(13)                                            # L378
    s.locate(24, 51)
    month_str = g.month_names[g.month][:3].upper() if g.month_names[g.month] else "???"
    s.print_text(f" {month_str}, {g.year}")

    # ── Victory point recalculation ──                       L379-388
    g.victory[1] = int(0.8 * g.victory[1] + 0.3 * (g.income[1] + g.control[1]))  # L379
    if g.control[1] > 29:                                  # L380
        g.victory[1] += 50
        if g.control[1] > 34:
            g.victory[1] += 100
    if g.side == 2 and g.control[1] < 11:                  # L381
        g.aggress += 0.7
    if g.victory[1] < 1:                                   # L383
        g.victory[1] = 0

    g.victory[2] = int(0.8 * g.victory[2] + 0.3 * (g.income[2] + g.control[2]))  # L384
    if g.control[2] > 29:                                  # L385
        g.victory[2] += 50
        if g.control[2] > 34:
            # BUG in original: uses victory(1) not victory(2)
            g.victory[2] = g.victory[1] + 100
    if g.side == 1 and g.control[2] < 11:                  # L386
        g.aggress += 0.7

    if g.player == 2:                                      # L387
        clrbot(g)
        s.color(14)
        s.print_text("press a key")
        s.update()
        _wait_key()


# ═══════════════════════════════════════════════════════════════════════════
#  SUB image2 (a$, s)                                          Lines 389-409
# ═══════════════════════════════════════════════════════════════════════════

def image2(g: 'GameState', text: str, color_s: int) -> None:
    """Message popup: save background, draw box, print text, wait, restore."""
    from cws_util import tick
    from cws_ui import mxw

    s = g.screen
    g.mtx[1] = text                                        # L391
    tlx = 32 - len(text) // 2                              # L392
    tly = 10
    g.size = 1                                             # L393
    wide = mxw(g)                                          # L394
    if wide > 59:                                          # L395
        wide = 59
        text = text[:59]

    # Save background                                       L398
    sx1 = 8 * tlx - 4
    sy1 = 16 * tly - 3
    sx2 = 8 * (tlx + wide + 1) + 15
    sy2 = 16 * (tly + 3) + 7
    saved = s.get_image(sx1, sy1, sx2, sy2)

    # Clear area                                            L399-401
    s.view(sx1, sy1, 8 * (tlx + wide + 1) + 7, 16 * (tly + 3) + 4)
    s.cls(1)
    s.view()

    # Draw popup box                                        L402-404
    s.line(8 * tlx, 16 * tly - 1, sx2, sy2, 0, "BF")     # L402
    bx2 = 8 * (tlx + wide + 1) + 7
    by2 = 16 * (tly + 3)
    s.line(sx1, sy1, bx2, by2, color_s, "BF")             # L403
    s.line(sx1, sy1, bx2, by2, 15, "B")                   # L404

    # Print text                                            L405-406
    s.color(14)
    s.locate(tly + 2, tlx + 2)
    s.print_text(text)
    s.update()

    tick(g, 9)                                             # L407

    # Restore background                                    L408
    s.put_image(sx1, sy1, saved)
    s.update()


# ═══════════════════════════════════════════════════════════════════════════
#  SUB maptext                                                 Lines 410-427
# ═══════════════════════════════════════════════════════════════════════════

def maptext(g: 'GameState') -> None:
    """Draw city name labels. Uses pygame font (simplified from DRAW font$).

    Original (L410-427): draws each character using DRAW font$() commands.
    Each char positioned at: cityx(k) + 6*(j-4) - 3, spaced 6px apart.
    IF a > 527 GOTO nextc — clips at map right edge.

    Color logic (L418-422):
        matrix(k,7) < 90:  C0 (black) in normal mode, C7 (gray) in B&W
        matrix(k,7) >= 90: C10 (green) — coastal/water cities
    """
    from cws_screen_pygame import VGA
    from vga_font import get_draw_glyph, DRAW_OX, DRAW_OY
    for k in range(1, 41):                                 # L411
        name = g.city[k]
        if not name:
            continue
        cx = g.cityx[k]
        cy = g.cityy[k]

        for j in range(len(name)):                         # L412
            a = cx + 6 * (j - 3) - 3                      # L413: 1-based j→0-based
            if a > 527:                                    # L415
                break

            ch = name[j].upper()
            code = ord(ch)

            # Color per original L418-422
            if g.matrix[k][7] >= 90:                       # L420-421
                rgb = VGA[10]                              # green (coastal)
            elif g.bw == 0:                                # L419
                rgb = VGA[0]                               # black (normal)
            else:
                rgb = VGA[7]                               # gray (B&W mode)

            glyph = get_draw_glyph(code, rgb)
            if glyph is not None:
                # Blit so the glyph origin (DRAW_OX, DRAW_OY) lands at (a, cy+12)
                g.screen.surface.blit(glyph, (a - DRAW_OX, cy + 12 - DRAW_OY))


# ═══════════════════════════════════════════════════════════════════════════
#  SUB touchup                                                 Lines 428-488
# ═══════════════════════════════════════════════════════════════════════════

def touchup(g: 'GameState') -> None:
    """Map detail lines: coastlines, rivers, borders. Exact port."""
    s = g.screen

    # Norfolk Coast                                         L430-433
    s.line(500, 170, 490, 165, 10)
    s.line_to(495, 160, 10)
    s.line_to(490, 155, 10)
    s.line_to(485, 150, 10)

    # Mobile border                                         L437
    s.line(145, 375, 145, 405, 10)

    # Virginia border                                       L439-443
    s.line(291, 111, 301, 101, 1)
    s.line_to(316, 96, 1)
    s.line_to(331, 76, 1)
    s.line_to(345, 51, 1)
    s.line_to(351, 30, 1)
    s.line_to(370, 35, 1)

    # Potomac River                                         L446-448
    s.line(381, 81, 431, 66, 1)
    s.line_to(456, 81, 1)
    s.line_to(471, 111, 1)

    # Paducah                                               L450-451
    s.line(115, 165, 105, 170, 1)
    s.line_to(105, 190, 1)
    s.line(106, 170, 91, 140, 1)                           # L452: Missouri R

    s.line(105, 190, 150, 190, 10)                         # L454
    s.line(120, 160, 130, 200, 1)                          # L455: Tenn River

    # Vicksburg                                             L457-458
    s.line(60, 295, 65, 325, 1)
    s.line_to(65, 335, 1)

    # Misc borders                                          L461-462
    s.line(195, 125, 170, 130, 1)
    s.line_to(165, 135, 1)

    s.line(50, 375, 60, 395, 1)                            # L464

    s.line(60, 395, 105, 405, 1)                           # L466
    s.line_to(110, 420, 1)                                 # L467

    # Savannah River                                        L469
    s.line(291, 265, 350, 340, 1)

    # Missouri River                                        L471-474
    s.line(1, 80, 15, 77, 1)
    s.line_to(25, 95, 1)
    s.line_to(50, 98, 1)
    s.line_to(75, 96, 1)

    s.line(71, 90, 61, 95, 1)                              # L476
    s.line_to(56, 85, 1)                                   # L477

    # Gulf coast detail                                     L479-484
    s.line(110, 398, 105, 398, 10)
    s.line_to(90, 396, 10)
    s.line_to(90, 400, 10)
    s.line_to(105, 402, 10)
    s.line_to(120, 415, 10)
    s.line_to(115, 420, 10)

    s.line(66, 375, 52, 375, 10)                           # L487


# ═══════════════════════════════════════════════════════════════════════════
#  SUB usa                                                     Lines 489-809
# ═══════════════════════════════════════════════════════════════════════════

def usa(g: 'GameState') -> None:
    """Draw the full game map. Every LINE command ported from original."""
    from cws_navy import chessie, ships
    from cws_army import placearmy
    from cws_util import stax
    from cws_flow import engine

    s = g.screen

    # SCREEN 12                                             L490
    s.line(1, 16, 527, 440, 10, "B")                      # L491: map border
    # L492: PAINT (200,200), 2, 10 — fill land interior green
    # At this point only the border exists, so BF rectangle is equivalent
    s.line(2, 17, 526, 439, 2, "BF")                      # L492 equivalent
    s.color(10)                                            # L493

    # ── Mountains (L495-505) ──
    if hasattr(g, 'mtn_surface') and g.mtn_surface is not None:
        mtn = g.mtn_surface
        s.put_image(380, 30, mtn)                              # L496
        s.put_image(270, 200, mtn)                             # L497
        s.put_image(310, 160, mtn)                             # L498
        s.put_image(350, 120, mtn)                             # L499
        s.put_image(200, 185, mtn)                             # L500
        s.put_image(250, 130, mtn)                             # L501
        s.put_image(320, 80, mtn)                              # L502
        s.put_image(30, 150, mtn)                              # L503
        s.line(30, 150, 70, 190, 2, "BF")                     # L504

    # ═══════════════════ Kentucky ══════════════════════════ L506-536
    s.line(105, 190, 150, 190, 10)                         # L507
    s.line_to(150, 185)                                    # L508
    s.line_to(290, 185)                                    # L509
    s.line(276, 185, 301, 175, 10)                         # L510
    s.line_to(305, 160)                                    # L511
    s.line_to(310, 155)                                    # L512
    s.line_to(305, 145)                                    # L513
    s.line_to(300, 125)                                    # L514
    s.line_to(290, 110)                                    # L515

    s.line_to(275, 95, 1)                                  # L517: river (blue)
    s.line_to(270, 95, 1)                                  # L518
    s.line_to(260, 100, 1)                                 # L519
    s.line_to(250, 100, 1)                                 # L520
    s.line_to(240, 90, 1)                                  # L521
    s.line_to(235, 85, 1)                                  # L522
    s.line_to(230, 85, 1)                                  # L523
    s.line_to(220, 90, 1)                                  # L524
    s.line_to(220, 100, 1)                                 # L525
    s.line_to(210, 105, 1)                                 # L526
    s.line_to(205, 115, 1)                                 # L527
    s.line_to(195, 125, 1)                                 # L528
    s.line_to(170, 130, 1)                                 # L529
    s.line_to(165, 135, 1)                                 # L530
    s.line_to(130, 140, 1)                                 # L531
    s.line_to(120, 150, 1)                                 # L532
    s.line_to(120, 160, 1)                                 # L533
    s.line_to(115, 165, 1)                                 # L534
    s.line_to(105, 170, 1)                                 # L535
    s.line_to(105, 190, 1)                                 # L536

    # ═══════════════════ Tennessee ═════════════════════════ L537-550
    s.line(290, 185, 320, 185, 10)                         # L538
    s.line_to(320, 185)                                    # L539
    s.line_to(315, 195)                                    # L540
    s.line_to(302, 210)                                    # L541
    s.line_to(290, 215)                                    # L542
    s.line_to(275, 230)                                    # L543
    s.line_to(260, 241)                                    # L544
    s.line_to(260, 241)                                    # L545
    s.line_to(70, 241)                                     # L546

    s.line(105, 190, 95, 200, 1)                           # L548
    s.line_to(80, 220, 1)                                  # L549
    s.line_to(70, 241, 1)                                  # L550

    # ═══════════════════ Mississippi ═══════════════════════ L551-567
    s.line(143, 241, 145, 405, 10)                         # L552
    s.line_to(135, 400)                                    # L553
    s.line_to(125, 400)                                    # L554
    s.line_to(115, 405)                                    # L555
    s.line_to(110, 400)                                    # L556
    s.line_to(110, 390)                                    # L557
    s.line_to(115, 380)                                    # L558
    s.line_to(115, 375)                                    # L559
    s.line_to(50, 375)                                     # L560
    s.line(115, 375, 60, 375, 10)                          # L561

    s.line(70, 241, 65, 280, 1)                            # L563: Miss. River
    s.line_to(60, 295, 1)                                  # L564
    s.line_to(65, 325, 1)                                  # L565
    s.line_to(65, 335, 1)                                  # L566
    s.line_to(50, 375, 1)                                  # L567

    # ═══════════════════ Alabama ═══════════════════════════ L568-576
    s.line(215, 241, 232, 375, 10)                         # L569
    s.line(176, 395, 181, 410, 10)                         # L570
    s.line_to(166, 415)                                    # L571
    s.line_to(161, 400)                                    # L572
    s.line_to(156, 405)                                    # L573
    s.line_to(146, 405)                                    # L574
    s.line(176, 395, 176, 385, 10)                         # L575
    s.line_to(231, 385)                                    # L576

    # ═══════════════════ Georgia & Florida ═════════════════ L577-601
    s.line(261, 241, 296, 241, 10)                         # L578
    s.line_to(291, 265)                                    # L579
    s.line_to(350, 340)                                    # L580
    s.line_to(336, 390)                                    # L581
    s.line_to(366, 440)                                    # L582
    s.line(336, 385, 325, 385, 10)                         # L583: Fla/Ga border
    s.line_to(320, 388)                                    # L584
    s.line_to(245, 388)                                    # L585
    s.line_to(230, 385)                                    # L586
    s.line(180, 410, 195, 410, 10)                         # L587
    s.line_to(215, 415)                                    # L588
    s.line_to(225, 425)                                    # L589
    s.line_to(255, 420)                                    # L590
    s.line_to(265, 420)                                    # L591
    s.line_to(270, 425)                                    # L592
    s.line_to(275, 440)                                    # L593
    s.line(347, 409, 343, 409, 10)                         # L594
    s.line_to(343, 431)                                    # L595
    s.line_to(346, 431)                                    # L596
    s.line_to(346, 412)                                    # L597
    s.line_to(349, 412)                                    # L598
    s.line(347, 411, 350, 411, 1)                          # L599
    s.line(353, 333, 358, 336, 10, "B")                    # L601

    # ═══════════════════ South Carolina ════════════════════ L602-612
    s.line(290, 241, 305, 240, 10)                         # L603
    s.line_to(345, 240)                                    # L604
    s.line_to(350, 250)                                    # L605
    s.line_to(380, 250)                                    # L606
    s.line_to(415, 280)                                    # L607
    s.line_to(385, 315)                                    # L608
    s.line_to(380, 320)                                    # L609
    s.line_to(375, 325)                                    # L610
    s.line_to(350, 330)                                    # L611
    s.line_to(350, 340)                                    # L612

    # ═══════════════════ North Carolina ════════════════════ L613-639
    s.line(320, 185, 500, 185, 10)                         # L614
    s.line_to(505, 190)                                    # L615
    s.line_to(490, 195)                                    # L616
    s.line_to(490, 205)                                    # L617
    s.line_to(505, 205)                                    # L618
    s.line_to(500, 215)                                    # L619
    s.line_to(485, 220)                                    # L620
    s.line_to(490, 225)                                    # L621
    s.line_to(500, 225)                                    # L622
    s.line_to(500, 230)                                    # L623
    s.line_to(490, 235)                                    # L624
    s.line_to(488, 240)                                    # L625
    s.line_to(480, 241)                                    # L626
    s.line_to(460, 250)                                    # L627
    s.line_to(455, 255)                                    # L628
    s.line_to(440, 265)                                    # L629
    s.line_to(439, 270)                                    # L630
    s.line_to(425, 278)                                    # L631
    s.line_to(415, 280)                                    # L632
    s.line(510, 190, 513, 200, 10, "B")                    # L633: Outer Banks box
    s.line(510, 206, 510, 226, 10)                         # L634
    s.line_to(500, 236)                                    # L635
    s.line_to(502, 241)                                    # L636
    s.line_to(512, 228)                                    # L637
    s.line_to(512, 208)                                    # L638
    s.line_to(510, 206)                                    # L639

    # ═══════════════════ Chesapeake Bay ════════════════════ L641-642
    chessie(g)

    # ═══════════════════ Ohio/PA/MD/VA ═════════════════════ L643-657
    s.line(291, 111, 301, 101, 1)                          # L644
    s.line_to(316, 96, 1)                                  # L645
    s.line_to(331, 76, 1)                                  # L646
    s.line_to(345, 51, 1)                                  # L647
    s.line_to(351, 30, 1)                                  # L648
    s.line_to(370, 35, 1)                                  # L649

    s.line(351, 16, 351, 54, 10)                           # L651
    s.line_to(527, 54)                                     # L652
    s.line(381, 54, 381, 81, 10)                           # L653
    s.line_to(431, 66)                                     # L654
    s.line_to(456, 81)                                     # L655
    s.line_to(471, 111)                                    # L656
    s.line(226, 85, 226, 16, 10)                           # L657

    # ═══════════════════ Louisiana/Arkansas/Missouri ═══════ L658-700
    s.line(50, 375, 60, 395, 1)                            # L659
    s.line_to(105, 405, 1)                                 # L660
    s.line_to(110, 420, 1)                                 # L661
    s.line_to(125, 438, 1)                                 # L662
    s.line(110, 398, 105, 398, 10)                         # L663
    s.line_to(90, 396)                                     # L665
    s.line_to(90, 400)                                     # L666
    s.line_to(105, 402)                                    # L669
    s.line_to(120, 415)                                    # L670
    s.line_to(115, 420)                                    # L671
    s.line_to(125, 435)                                    # L672
    s.line_to(120, 440)                                    # L673
    s.line_to(110, 425)                                    # L674
    s.line_to(100, 435)                                    # L675
    s.line_to(90, 440)                                     # L676
    s.line_to(50, 430)                                     # L677
    s.line_to(25, 435)                                     # L678
    s.line_to(1, 435)                                      # L679

    # L681-683: PAINT water/ocean areas blue
    s.paint(250, 430, 1, 10)                               # L681: Florida/Atlantic
    s.paint(110, 439, 1, 10)                               # L682: Gulf coast
    s.paint(50, 439, 1, 10)                                # L683: western Gulf

    s.line(1, 300, 61, 300, 10)                            # L685: Arkansas border
    s.line(91, 205, 71, 205, 10)                           # L686
    s.line_to(76, 190)                                     # L687
    s.line_to(71, 185)                                     # L688
    s.line_to(1, 185)                                      # L689

    # Missouri                                              L691-699
    s.line(106, 170, 91, 140, 1)                           # L691
    s.line_to(71, 120, 1)                                  # L692
    s.line_to(76, 110, 1)                                  # L693
    s.line_to(76, 95, 1)                                   # L694
    s.line_to(71, 90, 1)                                   # L695
    s.line_to(61, 95, 1)                                   # L696
    s.line_to(56, 85, 1)                                   # L697
    s.line_to(50, 35, 1)                                   # L698
    s.line_to(46, 20, 1)                                   # L699

    s.line_to(38, 16)                                      # L701: border (green)
    s.line(46, 20, 61, 17, 1)                              # L703: Illinois

    s.line(150, 17, 150, 110, 10)                          # L705
    s.line_to(147, 125, 1)                                 # L706
    s.line_to(140, 138, 1)                                 # L707

    # ═══════════════════ Rivers ════════════════════════════ L708-774
    s.line(1, 80, 15, 77, 1)                               # L710: Missouri River
    s.line_to(25, 95, 1)
    s.line_to(50, 98, 1)
    s.line_to(75, 96, 1)

    s.line(120, 160, 130, 200, 1)                          # L715: Tenn River
    s.line_to(135, 240, 1)
    s.line_to(130, 247, 1)
    s.line_to(160, 250, 1)
    s.line_to(200, 260, 1)
    s.line_to(240, 244, 1)
    s.line_to(245, 240, 1)
    s.line_to(270, 200, 1)

    s.line(120, 160, 140, 200, 1)                          # L724: Cumberland River
    s.line_to(160, 210, 1)
    s.line_to(200, 208, 1)
    s.line_to(240, 170, 1)

    s.line(161, 400, 155, 320, 1)                          # L729: Tombigbee River
    s.line_to(145, 300, 1)

    s.line(161, 400, 170, 370, 1)                          # L732: Alabama River
    s.line_to(200, 350, 1)

    s.line(230, 425, 231, 385, 1)                          # L735: Chattahoochee
    s.line_to(233, 350, 1)
    s.line_to(240, 330, 1)
    s.line_to(270, 290, 1)

    s.line(381, 81, 431, 66, 1)                            # L740: Potomac River
    s.line_to(456, 81, 1)
    s.line_to(471, 111, 1)

    s.line(485, 150, 455, 145, 1)                          # L744: James River
    s.line_to(400, 150, 1)

    s.line(489, 200, 415, 185, 1)                          # L747: Roanoke River
    s.line_to(400, 160, 1)

    s.line(296, 241, 291, 265, 1)                          # L750: Savannah River
    s.line_to(350, 340, 1)

    s.line(438, 271, 430, 235, 1)                          # L753: Cape Fear River
    s.line_to(420, 205, 1)

    s.line(500, 80, 498, 50, 1)                            # L756: Susquehanna
    s.line_to(470, 30, 1)

    s.line(405, 290, 360, 240, 1)                          # L759: Pee Dee River
    s.line(400, 300, 350, 280, 1)                          # L761: Santee River

    s.line(270, 423, 280, 410, 1)                          # L763: Suwanee River
    s.line_to(290, 390, 1)

    s.line(342, 370, 300, 350, 1)                          # L766: Altamaha River
    s.line(50, 370, 1, 330, 1)                             # L768: Red River
    s.line(65, 280, 1, 240, 1)                             # L770: Arkansas River

    s.line(430, 66, 400, 100, 1)                           # L772: Shenandoah
    s.line_to(380, 120, 1)

    # ═══════════════════ Cities & Labels ═══════════════════ L775-809
    showcity(g)                                            # L775
    s.pset(493, 280, 1)                                    # L776

    # Fort Monroe label                                     L777-780
    if g.navyloc[1] == 30 or g.navyloc[2] == 30:
        # L778: DRAW "FT" pixel font text
        s.draw("C11U7R4D3L3BR6BU3D7BU4R3U3D7BR3U7BD4BR4BU4D7R4")
        s.line(485, 241, 525, 270, 11, "B")               # L779

    if g.graf > 1:                                         # L782
        maptext(g)

    # Commerce raider box                                   L783-792
    if g.commerce > 0:
        s.line(447, 291, 525, 317, 4, "BF")               # L784
        s.line(447, 291, 525, 317, 10, "B")
        # L786-789: DRAW "COMMERCE" letter by letter using font$
        from vga_font import _DRAW_FONT_RAW
        y_f = 312                                           # L785
        a_str = "COMMERCE"                                  # L786
        for j_f in range(len(a_str)):                       # L787
            x_f = ord(a_str[j_f]) - 64                      # x = ASC(char) - 64
            s.pset(440 + 10 * (j_f + 1), y_f, 0)           # L788: 1-based j
            s.draw(_DRAW_FONT_RAW[x_f - 1])                # DRAW font$(x)
    else:
        s.line(447, 291, 525, 335, 1, "BF")               # L791

    # Place armies                                          L794-796
    for i in range(1, 41):
        if g.armyloc[i] > 0:
            placearmy(g, i)

    # Draw flag stars                                       L798-800
    for k in range(1, 3):
        stax(g, k)

    # Show pending move arrows (1-player only)              L802-804
    if g.player != 2:                                      # L802
        for i in range(1, 41):                             # L803
            if g.armyloc[i] > 0 and g.armymove[i] > 0:
                icon(g, g.armyloc[i], g.armymove[i], 1)

    ships(g)                                               # L806
    engine(g)                                              # L807

    # Date display                                          L808
    s.color(13)
    s.locate(24, 51)
    month_str = g.month_names[g.month][:3].upper() if g.month_names[g.month] else "???"
    s.print_text(f" {month_str}, {g.year}")


# ═══════════════════════════════════════════════════════════════════════════
#  Helper: wait for keypress
# ═══════════════════════════════════════════════════════════════════════════

def _wait_key() -> None:
    """Block until any key is pressed (replaces DO WHILE INKEY$="" LOOP)."""
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
