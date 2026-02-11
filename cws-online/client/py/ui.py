"""ui.py -- Canvas-only UI manager.

Port of ui.js which is itself a port of QBasic SUBs: topbar, flags, clrbot,
clrrite, armystat, menu/choices, image2, center, snapshot, and battle display.

All UI is drawn directly on the 640x480 canvas, faithfully porting the
QBasic SCREEN 12 layout.
"""

from constants import VGA, MONTHS
import font
from js_bridge import save_region, restore_region

# --------------------------------------------------------------------------- #
#  topbar(ctx, gs)
#  Port of QBasic SUB topbar (lines 4041-4071)
# --------------------------------------------------------------------------- #


def topbar(ctx, gs):
    if not gs:
        return

    side = gs.get("player_side", 1)
    side_name = "UNION" if side == 1 else "REBEL"
    month = gs.get("month", 3)
    year = gs.get("year", 1862)
    month_str = MONTHS[month][:3].upper() if 1 <= month <= 12 else ""
    date_str = f"{month_str},{year}"
    cash = gs.get("cash", {})
    my_cash = int(cash.get(str(side), cash.get(side, 0)))
    difficulty = gs.get("difficulty", 3)
    vp = gs.get("victory_points", {})
    my_vp = int(vp.get(str(side), vp.get(side, 0)))
    opp = 2 if side == 1 else 1
    opp_vp = int(vp.get(str(opp), vp.get(opp, 0)))
    total_vp = my_vp + opp_vp
    vp_pct = round((my_vp / total_vp) * 100) if total_vp > 0 else 50

    # Clear row 1
    font.clear_area(ctx, 0, 0, 640, 16)

    # LOCATE 1,10
    top_text = f"Input your decisions now for {side_name} side {date_str}"
    font.print_text(ctx, 1, 10, top_text, 11)

    # Draw flag
    draw_flags(ctx, side)

    # LOCATE 6,68: Difficulty
    font.print_text(ctx, 6, 68, f"Difficulty {difficulty}", 4)

    # LOCATE 7,68: Funds (QBasic: no $ sign)
    font.print_text(ctx, 7, 68, f"Funds: {my_cash}", 7)

    # VP progress bar
    ctx.strokeStyle = VGA[15]
    ctx.lineWidth = 1
    ctx.strokeRect(530.5, 20.5, 100, 10)

    side_color = 9 if side == 1 else 7
    bar_width = round(vp_pct)
    if bar_width > 0:
        ctx.fillStyle = VGA[side_color]
        ctx.fillRect(531, 21, bar_width, 9)
    if bar_width < 100:
        ctx.fillStyle = VGA[7 if side == 1 else 9]
        ctx.fillRect(531 + bar_width, 21, 100 - bar_width, 9)

    # LOCATE 4,68: VP
    font.print_text(ctx, 4, 68, f"VP : {my_vp}", side_color)

    # LOCATE 5,68: percent
    font.print_text(ctx, 5, 68, f"({vp_pct}%)", side_color)

    # LOCATE 26,68: shortcuts
    font.print_text(ctx, 26, 68, "F3 Redrw Scrn", 7)
    font.print_text(ctx, 27, 68, "F7 End Turn", 7)
    font.print_text(ctx, 28, 68, f"Turn: {side_name}", 7)


# --------------------------------------------------------------------------- #
#  flags(ctx, who) -- topbar version: flags(side, 0, 0)
#  Port of QBasic SUB flags: w=0 => x=585, y=180 (lines 3269-3302)
# --------------------------------------------------------------------------- #
def draw_flags(ctx, who):
    x, y = 585, 180  # QBasic position

    if who == 1:
        # Union flag: red/white stripes, blue canton, white stars
        ctx.fillStyle = VGA[4]
        ctx.fillRect(x - 17, y - 15, 35, 23)
        ctx.fillStyle = VGA[15]
        for s in range(7):
            ctx.fillRect(x - 17, y - 15 + s * 3, 35, 2)
        ctx.fillStyle = VGA[4]
        for s in range(7):
            ctx.fillRect(x - 17, y - 15 + s * 3 + 2, 35, 1)
        ctx.fillStyle = VGA[1]
        ctx.fillRect(x - 17, y - 15, 17, 12)
        ctx.fillStyle = VGA[15]
        for sr in range(3):
            for sc in range(4):
                ctx.fillRect(x - 15 + sc * 4, y - 13 + sr * 4, 2, 2)
        ctx.strokeStyle = VGA[0]
        ctx.lineWidth = 1
        ctx.strokeRect(x - 17 + 0.5, y - 15 + 0.5, 34, 22)

        font.print_text(ctx, 10, 70, "U N I O N", 9)
    else:
        # Confederate flag
        ctx.fillStyle = VGA[4]
        ctx.fillRect(x - 17, y - 15, 35, 23)

        ctx.strokeStyle = VGA[7]
        ctx.lineWidth = 1
        ctx.beginPath()
        ctx.moveTo(x - 17, y - 13)
        ctx.lineTo(x + 15, y + 7)
        ctx.stroke()
        ctx.beginPath()
        ctx.moveTo(x - 15, y - 15)
        ctx.lineTo(x + 17, y + 5)
        ctx.stroke()

        ctx.strokeStyle = VGA[1]
        ctx.beginPath()
        ctx.moveTo(x - 17, y + 7)
        ctx.lineTo(x + 17, y - 15)
        ctx.stroke()
        ctx.beginPath()
        ctx.moveTo(x - 17, y + 6)
        ctx.lineTo(x + 16, y - 15)
        ctx.stroke()
        ctx.beginPath()
        ctx.moveTo(x - 16, y + 7)
        ctx.lineTo(x + 17, y - 14)
        ctx.stroke()

        ctx.strokeStyle = VGA[7]
        ctx.beginPath()
        ctx.moveTo(x - 17, y + 5)
        ctx.lineTo(x + 15, y - 15)
        ctx.stroke()
        ctx.beginPath()
        ctx.moveTo(x - 15, y + 7)
        ctx.lineTo(x + 17, y - 13)
        ctx.stroke()

        ctx.strokeStyle = VGA[4]
        ctx.strokeRect(x - 17 + 0.5, y - 15 + 0.5, 34, 22)

        font.print_text(ctx, 10, 70, "R E B E L", 7)


# --------------------------------------------------------------------------- #
#  clr_bot(ctx) -- Clear bottom status bar (row 29)
# --------------------------------------------------------------------------- #
def clr_bot(ctx):
    ctx.fillStyle = VGA[0]
    ctx.fillRect(0, 448, 632, 16)


# --------------------------------------------------------------------------- #
#  print_message(ctx, text, color_idx)
# --------------------------------------------------------------------------- #
def print_message(ctx, text, color_idx=15):
    clr_bot(ctx)
    if text:
        font.print_text(ctx, 29, 1, text, color_idx)


# --------------------------------------------------------------------------- #
#  clr_rite(ctx) -- Clear right panel
# --------------------------------------------------------------------------- #
def clr_rite(ctx):
    ctx.fillStyle = VGA[0]
    ctx.fillRect(528, 1, 112, 450)


# --------------------------------------------------------------------------- #
#  army_stat(ctx, army) -- Port of QBasic SUB armystat
# --------------------------------------------------------------------------- #
def army_stat(ctx, army):
    if not army:
        return

    ctx.fillStyle = VGA[0]
    ctx.fillRect(530, 96, 110, 70)

    aid = army.get("id", 0) if isinstance(
        army, dict) else getattr(army, "id", 0)
    side = 1 if aid <= 20 else 2
    side_color = 9 if side == 1 else 7

    name = army.get("name", "?") if isinstance(
        army, dict) else getattr(army, "name", "?")
    size = army.get("size", 0) if isinstance(
        army, dict) else getattr(army, "size", 0)
    exp = army.get("experience", 0) if isinstance(
        army, dict) else getattr(army, "experience", 0)
    supply = army.get("supply", 0) if isinstance(
        army, dict) else getattr(army, "supply", 0)

    font.print_text(ctx, 8, 68, name[:12], 15)
    font.print_text(ctx, 9, 68, f"Size: {size}00", side_color)
    font.print_text(ctx, 11, 68, f"Exper: {exp}", 7)
    supply_color = 12 if supply < 1 else 7
    font.print_text(ctx, 12, 68, f"Supply: {supply}", supply_color)


# --------------------------------------------------------------------------- #
#  draw_menu(ctx, title, options, selected, tlx, tly, colour, hilite)
#  Port of QBasic SUB menu/choices (lines 4626-4915)
# --------------------------------------------------------------------------- #
def draw_menu(ctx, title, options, selected_index,
              tlx=67, tly=13, colour=4, hilite=11):
    if not options:
        return

    wide = max((len(o) for o in options), default=0)
    if title and len(title) > wide:
        wide = len(title)
    wide += 2  # padding

    size = len(options)

    # Convert LOCATE coords to pixels
    px = (tlx - 1) * 8
    py = (tly - 1) * 16
    box_w = (wide + 2) * 8
    box_h = (size + 3) * 16

    # Clear menu area
    ctx.fillStyle = VGA[0]
    ctx.fillRect(px, py, box_w, box_h)

    # Border
    ctx.strokeStyle = VGA[colour]
    ctx.lineWidth = 1
    ctx.strokeRect(px + 0.5, py + 0.5, box_w - 1, box_h - 1)

    # Title centered
    if title:
        title_col = tlx + (wide + 2 - len(title)) // 2
        font.print_text(ctx, tly, title_col, title, colour)

    # Options
    for j, opt in enumerate(options):
        opt_row = tly + 2 + j
        opt_col = tlx + 1
        opt_color = hilite if j == selected_index else colour

        font.print_text(ctx, opt_row, opt_col, opt, opt_color)

        # QBasic: LINE (8*(tlx+1), 16*(tly+row+1))-(8*(tlx+LEN(mtx$(row))+1)-1, 16*(tly+row+2)-1), hilite, B
        if j == selected_index:
            rx1 = 8 * (tlx + 1)
            ry1 = 16 * (tly + j + 1)
            rx2 = 8 * (tlx + len(opt) + 1) - 1
            ry2 = 16 * (tly + j + 2) - 1
            ctx.strokeStyle = VGA[hilite]
            ctx.lineWidth = 1
            ctx.strokeRect(rx1 + 0.5, ry1 + 0.5, rx2 - rx1, ry2 - ry1)


# --------------------------------------------------------------------------- #
#  image2(ctx, message, color_idx) -- Centered popup box
# --------------------------------------------------------------------------- #
def image2(ctx, message, color_idx=15):
    msg_len = len(message)
    box_w = (msg_len + 4) * 8
    box_h = 48
    px = (640 - box_w) // 2
    py = (480 - box_h) // 2

    ctx.fillStyle = VGA[1]
    ctx.fillRect(px, py, box_w, box_h)
    ctx.strokeStyle = VGA[15]
    ctx.lineWidth = 1
    ctx.strokeRect(px + 0.5, py + 0.5, box_w - 1, box_h - 1)

    font.print_text_px(ctx, px + 16, py + 16, message, color_idx)


# --------------------------------------------------------------------------- #
#  center_text(ctx, row, text) -- Center text on a row
# --------------------------------------------------------------------------- #
def center_text(ctx, row, text, color_idx=15):
    col = max(1, (80 - len(text)) // 2 + 1)
    font.print_text(ctx, row, col, text, color_idx)


# --------------------------------------------------------------------------- #
#  draw_waiting(ctx, side_name)
# --------------------------------------------------------------------------- #
def draw_waiting(ctx, side_name):
    msg = f"{side_name or 'Opponent'} is making decisions..."
    image2(ctx, msg, 14)


# --------------------------------------------------------------------------- #
#  draw_battle_result(ctx, result)
# --------------------------------------------------------------------------- #
def draw_battle_result(ctx, result):
    if not result:
        return

    clr_rite(ctx)

    font.print_text(ctx, 1, 68, "BATTLE!", 12)

    loc_name = result.get("location_name", "")
    if loc_name:
        font.print_text(ctx, 2, 68, f"at {loc_name[:10]}", 14)

    font.print_text(ctx, 4, 68, "ATTACKER:", 15)
    atk_name = result.get("attacker_name", "")
    if atk_name:
        font.print_text(ctx, 5, 68, atk_name[:12], 11)
    atk_str = result.get("attacker_strength")
    if atk_str is not None:
        font.print_text(ctx, 6, 68, f"Str: {atk_str}00", 7)
    atk_loss = result.get("attacker_losses")
    if atk_loss is not None:
        font.print_text(ctx, 7, 68, f"Loss: {atk_loss}00", 12)

    font.print_text(ctx, 13, 68, "DEFENDER:", 15)
    def_name = result.get("defender_name", "")
    if def_name:
        font.print_text(ctx, 14, 68, def_name[:12], 11)
    def_str = result.get("defender_strength")
    if def_str is not None:
        font.print_text(ctx, 15, 68, f"Str: {def_str}00", 7)
    def_loss = result.get("defender_losses")
    if def_loss is not None:
        font.print_text(ctx, 16, 68, f"Loss: {def_loss}00", 12)

    winner = result.get("winner")
    if winner is not None:
        winner_text = "Union wins!" if winner == 1 else "Rebel wins!" if winner == 2 else "Draw!"
        font.print_text(ctx, 20, 68, winner_text, 14)

    font.print_text(ctx, 27, 68, "Press any key", 7)

    msg = result.get("message", "")
    if msg:
        print_message(ctx, msg, 14)


# --------------------------------------------------------------------------- #
#  draw_report(ctx, report_lines)
# --------------------------------------------------------------------------- #
def draw_report(ctx, report_lines):
    ctx.fillStyle = VGA[0]
    ctx.fillRect(0, 0, 640, 480)

    font.print_text(ctx, 1, 30, "SITUATION REPORT", 14)

    if report_lines:
        for i, rl in enumerate(report_lines):
            if i >= 27:
                break
            if isinstance(rl, dict):
                text = rl.get("text", "")
                color = rl.get("color", 7)
            else:
                text = str(rl)
                color = 7
            font.print_text(ctx, i + 3, 1, text, color)

    font.print_text(ctx, 29, 25, "Press any key to continue", 15)


# --------------------------------------------------------------------------- #
#  snapshot_save / snapshot_restore -- Port of QBasic GET/PUT
# --------------------------------------------------------------------------- #
def snapshot_save(ctx, x, y, w, h):
    return save_region(ctx, x, y, w, h)


def snapshot_restore(ctx, data, x, y):
    restore_region(ctx, data, x, y)
