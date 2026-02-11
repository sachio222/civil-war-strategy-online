"""cws_report.py - Reports and information displays.
Direct port of cws_report.bm (209 lines).

Contains:
    report(g, who)   L1-208 - main report dispatch + all sub-reports
"""

import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cws_globals import GameState


def _strong(g: 'GameState', index: int) -> str:
    """Army strength string: armysize * 100."""
    return f"{g.armysize[index]}00"


def _wait_key(g: 'GameState') -> None:
    """Wait for any key press."""
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


def _data_path(filename: str) -> str:
    """Resolve data file path with case-insensitive lookup."""
    # Check current directory first
    if os.path.exists(filename):
        return filename
    # Check parent directory (data files often at project root)
    parent = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
    candidate = os.path.join(parent, filename)
    if os.path.exists(candidate):
        return candidate
    # Case-insensitive search
    for d in ['.', parent]:
        if os.path.isdir(d):
            for f in os.listdir(d):
                if f.lower() == filename.lower():
                    return os.path.join(d, f)
    return filename


# ═══════════════════════════════════════════════════════════════════════════
#  Army Report                                                 Lines 28-76
# ═══════════════════════════════════════════════════════════════════════════

def _army_report(g: 'GameState', who: int) -> None:
    """Display army report for one side."""
    from cws_util import starfin
    from cws_army import armyxy

    s = g.screen
    star, fin = starfin(g, who)                             # L32

    s.cls()                                                 # L33
    s.locate(1, 1)
    c = 9                                                   # L33
    if who == 2:
        c = 15
    s.color(c)

    # Header line                                           L35
    s.print_text(
        f" Report for {g.force[who]} Forces    "
        f"{g.month_names[g.month]}, {g.year}    "
    )
    s.color(14)
    s.print_text(f" Victory Points {g.victory[who]}")

    if c == 15:                                             # L36
        c = 7

    # VP percentage                                         L37-43
    x_total = g.victory[who] + g.victory[3 - who]          # L37
    if x_total == 0:                                        # L38
        pass
    else:
        y_pct = int((g.victory[who] / x_total) * 100)      # L41
        s.print_text(f"({y_pct} %)")

    armyxy(g, 215, 8, who)                                  # L44

    # Control/cities line                                   L45
    s.color(c)
    x_pct = int(g.control[who] * 2.5 + 0.5)
    s.locate(4, 1)
    s.print_text(f"{g.control[who]}/ 40   CITIES CONTROLLED    ({x_pct}%)")
    s.color(12)                                             # L46
    s.print_text(f"     Capital: {g.city[g.capcity[who]]}")

    # Income line                                           L47-49
    y_vp = g.vptotal                                        # L47
    if g.capcity[1] > 0:
        y_vp += 100
    if g.capcity[2] > 0:                                    # L48
        y_vp += 100
    x_inc = 0
    if g.vptotal > 0:
        x_inc = int((g.income[who] / g.vptotal) * 100)     # L49
    s.color(c)
    s.print_text(f"{g.income[who]}/{y_vp}   INCOME    ({x_inc}%)   ")
    s.color(14)
    s.print_text(f"Cash:{g.cash[who]}")

    # Column headers                                        L50
    s.color(11)
    s.locate(6, 1)
    s.print_text(" #    Name             Size  Location   Ldr Exp Suply Move To")

    # Army list                                             L51-62
    x_total_size = 0
    row = 7
    for i in range(star, fin + 1):                          # L51
        s.color(c)                                          # L52
        if g.armyloc[i] < 1:                                # L53: deadeye
            continue
        x_total_size += g.armysize[i]                       # L54

        s.locate(row, 1)                                    # L55
        s.print_text(f"{i:2}  {g.armyname[i]:18s} {_strong(g, i):>5s}  {g.city[g.armyloc[i]]:12s}")

        if who != g.side:                                   # L57
            row += 1
            continue

        # Detailed info for own side                        L58-60
        move_str = ""
        if g.armymove[i] > -1:                              # L59
            move_str = g.city[g.armymove[i]] if g.armymove[i] > 0 else ""
        else:
            move_str = "Resting"
        s.print_text(f"  {g.armylead[i]:2}  {g.armyexper[i]:2}   {g.supply[i]:2}   {move_str}")

        if g.fort[g.armyloc[i]] > 0:                        # L60
            s.locate(row, 68)
            s.print_text(f"FORT +{g.fort[g.armyloc[i]]}")
        row += 1

    # Summary                                               L63-76
    s.locate(row, 1)
    s.print_text(" " + "-" * 70)                            # L63
    row += 1
    s.locate(row, 1)
    enemy_est = int(g.aggress * x_total_size)
    s.print_text(
        f" Total Forces    {x_total_size}00"                # L64
        f"          [ Enemy Forces {enemy_est}00 ]"
    )
    row += 1
    s.locate(row, 1)
    s.print_text(" " + "-" * 70)                            # L65

    row += 1
    s.locate(row, 1)
    # Navy info                                             L66-72
    s.print_text(f" {g.force[who]} NAVY has {g.navysize[who]} ship(s) ")
    ironclad_count = 0                                      # L67-70
    for k in range(len(g.fleet[who])):
        if k < len(g.fleet[who]) and g.fleet[who][k] == "I":
            ironclad_count += 1
    if ironclad_count > 0:                                  # L71
        s.print_text(f"({ironclad_count} Ironclads) ")
    if 0 < g.navyloc[who] < 99:                            # L72
        s.print_text(f"in {g.city[g.navyloc[who]]}")

    # Train info                                            L73
    if g.rr[who] > 0:
        row += 1
        s.locate(row, 1)
        s.color(14)
        ri = g.rr[who]
        dest = g.city[g.armymove[ri]] if g.armymove[ri] > 0 else "?"
        s.print_text(f" Army #{ri} {g.armyname[ri]} on train to {dest}")

    # Border                                                L74-75
    s.line(0, 0, 639, 449, 15, "B")
    s.line(0, 62, 639, 62, 15)
    s.update()


# ═══════════════════════════════════════════════════════════════════════════
#  City Report                                                 Lines 80-100
# ═══════════════════════════════════════════════════════════════════════════

def _city_report(g: 'GameState') -> None:
    """Display city report."""
    s = g.screen
    s.cls()                                                 # L81
    s.locate(1, 1)
    s.color(14)
    s.print_text(f"City Report        {g.month_names[g.month]}, {g.year}")

    s.color(15)                                             # L82-83
    s.locate(2, 1)
    s.print_text(" #    City       Control   Value")
    s.locate(2, 41)
    s.print_text(" #    City       Control   Value")
    s.line(1, 30, 630, 30, 15)                              # L84

    # Left column: cities 1-20                              L85-88
    for i in range(1, 21):
        a_ctrl = "neutral"
        c = 4
        if g.cityp[i] == 1:
            c = 9
            a_ctrl = "UNION"
        elif g.cityp[i] == 2:
            c = 7
            a_ctrl = "REBEL"
        s.color(c)
        s.locate(2 + i, 1)                                 # L87
        s.print_text(f"{i:2}   {g.city[i]:12s} {a_ctrl:8s} {g.cityv[i]}")

    # Right column: cities 21-40                            L90-93
    for i in range(21, 41):
        a_ctrl = "neutral"
        c = 4
        if g.cityp[i] == 1:
            c = 9
            a_ctrl = "UNION"
        elif g.cityp[i] == 2:
            c = 7
            a_ctrl = "REBEL"
        s.color(c)
        s.locate(i - 18, 41)                                # L92
        s.print_text(f"{i:2}   {g.city[i]:12s} {a_ctrl:8s} {g.cityv[i]}")

    # Summary                                               L94-99
    s.line(1, 360, 630, 360, 15)                            # L94
    s.color(9)                                              # L95
    s.locate(24, 1)
    s.print_text("Side    No. Cities   Income    Cash")
    s.color(9)                                              # L96
    s.print_text(
        f"{g.force[1]:10s} {g.control[1]:4}       {g.income[1]:5}   {g.cash[1]:6}"
    )
    s.color(7)                                              # L97
    s.print_text(
        f"{g.force[2]:10s} {g.control[2]:4}       {g.income[2]:5}   {g.cash[2]:6}"
    )
    s.color(4)                                              # L98
    s.print_text(
        f"{g.force[0]:10s} {40 - g.control[1] - g.control[2]:4}"
    )
    s.line(1, 382, 630, 382, 15)                            # L99
    s.update()


# ═══════════════════════════════════════════════════════════════════════════
#  Intelligence Report                                         Lines 104-127
# ═══════════════════════════════════════════════════════════════════════════

def _intel_report(g: 'GameState') -> None:
    """Display intelligence report on map."""
    from cws_util import starfin, tick
    from cws_map import usa

    s = g.screen
    c = 9                                                   # L105
    if g.side == 2:
        c = 7
    usa(g)                                                  # L106
    star, fin = starfin(g, g.side)                          # L107

    for k in range(star, fin + 1):                          # L108
        if g.armysize[k] > 0:                               # L109
            s.color(c)                                      # L110
            ax = g.cityx[g.armyloc[k]]                      # L111
            ay = g.cityy[g.armyloc[k]]                      # L112
            z = 10                                          # L113
            if g.armysize[k] < 1000:
                z = 9
            col = int(ax / 8) - 2                           # L114
            row = int(ay / 16)
            if row > 26:                                    # L115
                row = 26

            # Clear area                                    L116-118
            for j in range(0, 4):
                s.locate(row + j, col)
                s.print_text(" " * z)

            # Print stats                                   L119-122
            s.locate(row, col)
            s.print_text(f"Siz:{_strong(g, k)}")
            s.locate(row + 1, col)
            s.print_text(f"Ldr:{g.armylead[k]}")
            s.locate(row + 2, col)
            s.print_text(f"Xpr:{g.armyexper[k]}")
            s.locate(row + 3, col)
            s.print_text(f"Sup:{g.supply[k]}")

            # Border box                                    L123
            bx1 = 8 * (col - 1) - 1
            by1 = 16 * (row - 1) - 1
            bx2 = 8 * (col + z - 1) + 1
            by2 = 16 * (row + 3) + 1
            s.line(bx1, by1, bx2, by2, 15, "B")
            s.update()
            tick(g, 1)                                      # L124


# ═══════════════════════════════════════════════════════════════════════════
#  Force Summary                                               Lines 131-149
# ═══════════════════════════════════════════════════════════════════════════

def _force_summary(g: 'GameState') -> None:
    """Display force summary on map."""
    from cws_map import usa

    s = g.screen
    summ = [0] * 41                                         # L132 (DIM summ(40))

    for k in range(1, 41):                                  # L132
        if g.occupied[k] > 0:                               # L133
            for j in range(1, 41):                          # L134
                if g.armyloc[j] == k:                       # L135
                    summ[k] += g.armysize[j]

    s.cls()                                                 # L140
    usa(g)

    for k in range(1, 41):                                  # L141
        if summ[k] > 0:                                     # L142
            c = 9                                           # L143
            if g.cityp[k] == 2:
                c = 7
            s.color(c)                                      # L144
            row = int(g.cityy[k] / 16 + 1)                 # L145
            col = int(g.cityx[k] / 8)
            s.locate(row, col)
            s.print_text(str(summ[k]))

    s.color(14)                                             # L148
    s.locate(1, 20)
    s.print_text("Total Forces in Cities (100's)")
    s.update()


# ═══════════════════════════════════════════════════════════════════════════
#  Battle Report                                               Lines 153-182
# ═══════════════════════════════════════════════════════════════════════════

def _battle_report(g: 'GameState', who: int) -> None:
    """Display battle summary."""
    from cws_army import armyxy

    s = g.screen

    # Draw in center of map                                 L154-157
    s.view(200, 123, 400, 284)                              # L154
    s.cls()                                                 # L155 (CLS 1)
    s.view()                                                # L156
    s.line(200, 123, 400, 284, 15, "B")                     # L157

    s.color(14)                                             # L158
    s.locate(9, 32)                                         # L159
    s.print_text("BATTLE SUMMARY")
    armyxy(g, 320, 160, 1)                                  # L160
    armyxy(g, 370, 160, 2)                                  # L161

    s.line(200, 176, 400, 230, 15, "B")                     # L162
    s.line(200, 230, 400, 284, 15, "B")                     # L163
    s.line(290, 176, 345, 284, 15, "B")                     # L164

    s.locate(13, 27)                                        # L165
    s.print_text("BATTLES")
    s.locate(14, 27)                                        # L166
    s.print_text("WON")
    s.locate(16, 27)                                        # L167
    s.print_text("MEN LOST")
    s.locate(17, 27)                                        # L168
    s.print_text("(1000's)")

    s.locate(14, 38)                                        # L169
    s.print_text(str(g.batwon[1]))
    s.locate(14, 45)                                        # L170
    s.print_text(str(g.batwon[2]))
    s.locate(17, 38)                                        # L171
    s.print_text(str(int(0.1 * g.casualty[1])))
    s.locate(17, 45)                                        # L172
    s.print_text(str(int(0.1 * g.casualty[2])))

    # Write battle summary file if history enabled          L173-181
    s.update()

    if g.history > 0 and who > 2:
        try:
            path = _data_path("battsumm")
            with open(path, 'w') as f:                      # L174
                f.write(" SIDE      BATTLES WON       LOSSES\n")
                for k in range(1, 3):                       # L176
                    marker = " "                            # L177
                    if g.thrill == k:
                        marker = "*"
                    f.write(
                        f"{marker}{g.force[k]:15s} {g.batwon[k]:10d} "
                        f"{100 * g.casualty[k]:10d}\n"
                    )
        except OSError:
            pass


# ═══════════════════════════════════════════════════════════════════════════
#  History Recap                                               Lines 186-200
# ═══════════════════════════════════════════════════════════════════════════

def _recap(g: 'GameState') -> None:
    """Display game history log."""
    from cws_util import tick

    s = g.screen
    s.cls()                                                 # L187
    x = 0

    path = _data_path("cws.his")
    try:
        with open(path, 'r') as f:                          # L188
            for a_line in f:                                # L189-198
                a_line = a_line.rstrip('\n')                # L190
                c = 7                                       # L191
                if '[' in a_line:
                    c = 15
                if '>' in a_line:                           # L192
                    c = 14
                if '..' in a_line:                          # L193
                    c = 11
                if '!' in a_line:                           # L194
                    c = 12
                s.color(c)
                s.locate(29, 1)                             # L195
                s.print_text(a_line)
                s.update()
                x += 1                                      # L196
                if x > 27:                                  # L197
                    tick(g, 0.4)
    except FileNotFoundError:
        s.color(12)
        s.locate(10, 20)
        s.print_text("No history file found")


# ═══════════════════════════════════════════════════════════════════════════
#  SUB report (who)                                            Lines 1-208
# ═══════════════════════════════════════════════════════════════════════════

def report(g: 'GameState', who: int = 0) -> None:
    """Main report dispatch."""
    from cws_ui import menu
    from cws_map import usa

    s = g.screen

    if who == -1:                                           # L3: frep
        _force_summary(g)
        _endrep(g, who)
        return

    if who > 100:                                           # L4: batrep
        _battle_report(g, who)
        _endrep(g, who)
        return

    # Menu                                                  L5-12
    g.mtx[0] = "Information"                                # L5
    g.mtx[1] = f"{g.force[g.side]} Armies"                  # L6
    g.mtx[2] = f"{g.force[3 - g.side]} Armies"             # L7
    g.mtx[3] = "Cities"                                     # L8
    g.mtx[4] = "Force Summary"                              # L9
    g.mtx[5] = "Intelligence"                               # L10
    g.mtx[6] = "Battles"                                    # L11
    g.size = 6

    his_path = _data_path("cws.his")                        # L12
    if os.path.exists(his_path):
        g.mtx[7] = "Recap"
        g.size = 7

    menu(g, 0)                                              # L13

    if g.choose < 0:                                        # L15: < 0 → redraw
        s.cls()                                             # L16
        usa(g)                                              # L17
        return

    report_who = who
    if g.choose == 1:                                       # default: own side
        report_who = g.side
    elif g.choose == 2:                                     # L19: enemy side
        report_who = 3 - g.side

    if g.choose == 3:                                       # L20: cityrep
        _city_report(g)
        _endrep(g, report_who)
        return
    elif g.choose == 4:                                     # L21: frep
        _force_summary(g)
        _endrep(g, report_who)
        return
    elif g.choose == 5:                                     # L22: srep
        _intel_report(g)
        _endrep(g, report_who)
        return
    elif g.choose == 6:                                     # L23: batrep
        _battle_report(g, report_who)
        _endrep(g, report_who)
        return
    elif g.choose == 7:                                     # L24: recap
        _recap(g)
        _endrep(g, report_who)
        return

    # Army report (default: choose 1 or 2)                  L30-76
    if g.choose < 0:                                        # L30: endrep
        _endrep(g, report_who)
        return
    if g.choose == 4:                                       # L31: frep
        _force_summary(g)
        _endrep(g, report_who)
        return

    _army_report(g, report_who)
    _endrep(g, report_who)


def _endrep(g: 'GameState', who: int) -> None:
    """endrep: cleanup (L201-208)."""
    from cws_map import usa

    s = g.screen
    s.color(14)                                             # L202
    s.locate(29, 29)
    s.print_text("press a key")
    s.update()
    _wait_key(g)                                            # L203

    if who < 3:                                             # L204
        s.cls()                                             # L205
        usa(g)                                              # L206
