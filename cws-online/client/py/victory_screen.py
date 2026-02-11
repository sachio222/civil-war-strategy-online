"""victory_screen.py -- Victory / defeat screens.

Port of QBasic SUBs capitol() and rwin().

Union victory: Capitol building + Gettysburg Address + music
Rebel victory: Mansion + Dixie + star drawing
"""

import asyncio
from constants import VGA
import font
import sound
from js_bridge import sleep_ms


# --------------------------------------------------------------------------- #
#  Union Victory: Capitol / Gettysburg Address
#  Port of QBasic SUB capitol (lines ~2876-2940)
# --------------------------------------------------------------------------- #
async def show_capitol_screen(ctx):
    """Show the Union victory screen with Capitol building and Gettysburg Address."""
    from js import Math as JSMath  # type: ignore

    ctx.fillStyle = VGA[1]
    ctx.fillRect(0, 0, 640, 480)

    # Sky
    ctx.fillStyle = VGA[9]
    ctx.fillRect(0, 0, 640, 200)

    # Capitol dome (simplified)
    ctx.fillStyle = VGA[15]
    ctx.beginPath()
    ctx.arc(320, 180, 50, JSMath.PI, 0)
    ctx.fill()

    # Dome top
    ctx.fillRect(315, 130, 10, 50)

    # Capitol body
    ctx.fillStyle = VGA[15]
    ctx.fillRect(220, 180, 200, 80)

    # Columns
    ctx.strokeStyle = VGA[8]
    ctx.lineWidth = 3
    for col in range(8):
        x = 230 + col * 25
        ctx.beginPath()
        ctx.moveTo(x, 180)
        ctx.lineTo(x, 260)
        ctx.stroke()

    # Steps
    ctx.fillStyle = VGA[7]
    for step in range(3):
        ctx.fillRect(210 - step * 10, 260 + step * 8, 220 + step * 20, 8)

    # Ground
    ctx.fillStyle = VGA[2]
    ctx.fillRect(0, 284, 640, 20)

    # Title
    font.print_text(ctx, 1, 25, "UNION VICTORY!", 14)

    # Gettysburg Address excerpt
    lines = [
        "Four score and seven years ago",
        "our fathers brought forth on this",
        "continent, a new nation, conceived",
        "in Liberty, and dedicated to the",
        "proposition that all men are",
        "created equal.",
        "",
        "   -- Abraham Lincoln, 1863",
    ]

    for i, line in enumerate(lines):
        font.print_text(ctx, 21 + i, 5, line, 15)

    font.print_text(ctx, 30, 22, "Press any key to continue", 7)

    await sound.play_gettysburg()


# --------------------------------------------------------------------------- #
#  Rebel Victory: Mansion + Dixie
#  Port of QBasic SUB rwin (lines ~3780-3830)
# --------------------------------------------------------------------------- #
async def show_rebel_mansion(ctx):
    """Show the Rebel victory screen with a mansion and Dixie music."""
    from js import Math as JSMath  # type: ignore

    ctx.fillStyle = VGA[2]
    ctx.fillRect(0, 0, 640, 480)

    # Sky
    ctx.fillStyle = VGA[9]
    ctx.fillRect(0, 0, 640, 180)

    # Stars
    ctx.fillStyle = VGA[15]
    import random
    for _ in range(30):
        sx = random.randint(10, 630)
        sy = random.randint(10, 170)
        ctx.fillRect(sx, sy, 2, 2)

    # Mansion
    ctx.fillStyle = VGA[15]
    ctx.fillRect(240, 180, 160, 100)

    # Roof
    ctx.fillStyle = VGA[4]
    ctx.beginPath()
    ctx.moveTo(230, 180)
    ctx.lineTo(320, 140)
    ctx.lineTo(410, 180)
    ctx.fill()

    # Columns (4 tall columns)
    ctx.strokeStyle = VGA[8]
    ctx.lineWidth = 4
    for col in range(4):
        x = 260 + col * 40
        ctx.beginPath()
        ctx.moveTo(x, 180)
        ctx.lineTo(x, 280)
        ctx.stroke()

    # Door
    ctx.fillStyle = VGA[6]
    ctx.fillRect(305, 240, 30, 40)

    # Windows
    ctx.fillStyle = VGA[11]
    for wx in [260, 360]:
        ctx.fillRect(wx - 8, 200, 16, 20)

    # Ground / lawn
    ctx.fillStyle = VGA[2]
    ctx.fillRect(0, 280, 640, 20)

    # Fence
    ctx.strokeStyle = VGA[15]
    ctx.lineWidth = 1
    for fx in range(0, 640, 20):
        ctx.beginPath()
        ctx.moveTo(fx, 295)
        ctx.lineTo(fx, 280)
        ctx.stroke()
    ctx.beginPath()
    ctx.moveTo(0, 290)
    ctx.lineTo(640, 290)
    ctx.stroke()

    # Title
    font.print_text(ctx, 1, 22, "CONFEDERATE VICTORY!", 14)

    # Quote
    font.print_text(ctx, 21, 10, "The South shall rise again!", 7)
    font.print_text(ctx, 23, 10, "Dixie Land, I wish I was in Dixie,", 15)
    font.print_text(ctx, 24, 10, "Away, away, in Dixie Land...", 15)

    # Confederate star pattern
    ctx.fillStyle = VGA[14]
    center_x, center_y = 320, 360
    for angle_idx in range(11):
        import math
        angle = (angle_idx / 11.0) * 2 * math.pi - math.pi / 2
        r = 30
        sx = int(center_x + r * math.cos(angle))
        sy = int(center_y + r * math.sin(angle))
        ctx.fillRect(sx - 2, sy - 2, 5, 5)

    font.print_text(ctx, 30, 22, "Press any key to continue", 7)

    await sound.play_dixie()
