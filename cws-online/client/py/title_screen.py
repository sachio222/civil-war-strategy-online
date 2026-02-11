"""title_screen.py -- Title screen with flags and music.

Port of QBasic lines 174-202 (CWSTRAT.BAS). Exact layout:
- Game icon at (100, 100)
- "VGA CIVIL WAR STRATEGY GAME" / "Registered Edition"
- Bordered box with BOTH flags (Union and Confederate)
- Copyright and version
- Music: Battle Hymn (Union) or Shenandoah (Rebel) based on player side
"""

import asyncio
from constants import VGA
import font
import sprites
import sound


async def show_title_screen(ctx, side: int = 1):
    """Display the title screen.

    Args:
        ctx: Canvas 2D context
        side: 1=Union (plays Battle Hymn), 2=Rebel (plays Shenandoah)
    """
    # Clear to black
    ctx.fillStyle = VGA[0]
    ctx.fillRect(0, 0, 640, 480)

    # Game icon at (100, 100) - CWSTRAT.BAS line 174-175
    icon = sprites.get_sprite("cwsicon")
    if icon and getattr(icon, "complete", True) and getattr(icon, "naturalWidth", 0) > 0:
        ctx.imageSmoothingEnabled = False
        ctx.drawImage(icon, 100, 100)

    # Title text - lines 177-180
    font.print_text(ctx, 14, 27, "VGA CIVIL WAR STRATEGY GAME", 11)
    font.print_text(ctx, 15, 32, "Registered Edition", 4)
    font.print_text(
        ctx, 28, 8, "(c) 1998, 2017, 2018, 2024 by W. R. Hutsell and Dave Mackey", 14)
    font.print_text(ctx, 28, 60, "v1.61", 15)

    # Bordered box - lines 181-182
    ctx.strokeStyle = VGA[1]
    ctx.lineWidth = 1
    ctx.strokeRect(190, 170, 251, 91)
    ctx.strokeStyle = VGA[7]
    ctx.strokeRect(180, 180, 271, 71)

    # Both flags - lines 183, SUB flags
    _draw_flags(ctx, 1, -440, 0)
    _draw_flags(ctx, 2, -100, 0)

    # Instruction
    font.print_text(ctx, 26, 22, "Press any key to continue...", 15)

    if side == 1:
        asyncio.ensure_future(sound.play_battle_hymn())
    else:
        asyncio.ensure_future(sound.play_shenandoah())


def _draw_flags(ctx, who: int, w: int, a: int):
    """Port of QBasic SUB flags(who, w, a). Lines 3269-3302."""
    x = 585 + w
    y = 180 if w == 0 else 200
    if a != 0:
        y = a

    if who == 1:
        # Union flag
        ctx.fillStyle = VGA[4]
        ctx.fillRect(x - 17, y - 15, 35, 23)
        # White stripe borders (LINE draws rectangle, creates white bands)
        for i in (-13, -8, -3, 2, 7):
            ctx.fillStyle = VGA[7]
            ctx.fillRect(x - 17, y + i, 35, 1)
        ctx.fillStyle = VGA[1]
        ctx.fillRect(x - 17, y - 15, 17, 15)
        for i in range(-16, 0, 3):
            for j in range(-14, 0, 4):
                ctx.fillStyle = VGA[7]
                ctx.fillRect(x + i, y + j, 1, 1)
    elif who == 2:
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
        ctx.strokeStyle = VGA[1]
        ctx.strokeRect(x - 17, y - 15, 35, 23)
        ctx.strokeStyle = VGA[4]
        ctx.strokeRect(x - 17, y - 15, 35, 23)
