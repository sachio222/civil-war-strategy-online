"""sprites.py -- Army sprite drawing & image loading.

Port of sprites.js which is itself a port of QBasic SUBs:
  armyxy, placearmy, shipicon, engine, showcity, stax.

Also handles fort0/1/2.png and mtn.png sprite loading.
"""

import asyncio
from constants import VGA
from js_bridge import load_image_async, log

# --------------------------------------------------------------------------- #
#  Direction vectors for DRAW command executor
# --------------------------------------------------------------------------- #
_DIR = {
    "U": (0, -1), "D": (0, 1), "L": (-1, 0), "R": (1, 0),
    "E": (1, -1), "F": (1, 1), "G": (-1, 1), "H": (-1, -1),
}

# --------------------------------------------------------------------------- #
#  Sprite images (loaded async)
# --------------------------------------------------------------------------- #
_sprites = {
    "mtn": None,
    "fort0": None,
    "fort1": None,
    "fort2": None,
    "cwsicon": None,
}
_sprites_loaded = False


async def load_sprites(base_path: str = "assets/sprites/"):
    """Load all sprite images. Call once at startup."""
    global _sprites_loaded
    if _sprites_loaded:
        return

    names = ["mtn", "fort0", "fort1", "fort2", "cwsicon"]
    for name in names:
        img = await load_image_async(f"{base_path}{name}.png")
        _sprites[name] = img
        log(f"[sprites] Loaded {name}.png")

    _sprites_loaded = True


def get_sprite(name: str):
    """Get a loaded sprite image by name."""
    return _sprites.get(name)


def is_loaded() -> bool:
    return _sprites_loaded


# --------------------------------------------------------------------------- #
#  DRAW command executor
#  Port of QBasic DRAW interpreter.
#  Supports: U D L R E F G H (with distance), B (blank move), C (color), S (scale)
# --------------------------------------------------------------------------- #
def execute_draw(ctx, x: float, y: float, draw_string: str,
                 default_color: str = VGA[0], scale: float = 1.0):
    """Execute a QBasic DRAW command string on the canvas."""
    cx, cy = x, y
    current_color = default_color
    draw_scale = scale
    blank = False
    i = 0

    ctx.save()
    ctx.imageSmoothingEnabled = False
    ctx.lineWidth = 1
    ctx.lineCap = "square"

    while i < len(draw_string):
        ch = draw_string[i].upper()
        i += 1

        if ch == "B":
            blank = True
            continue

        if ch == "C":
            color_str = ""
            while i < len(draw_string) and draw_string[i].isdigit():
                color_str += draw_string[i]
                i += 1
            color_idx = int(color_str) if color_str else 0
            if 0 <= color_idx < 16:
                current_color = VGA[color_idx]
            blank = False
            continue

        if ch == "S":
            scale_str = ""
            while i < len(draw_string) and draw_string[i].isdigit():
                scale_str += draw_string[i]
                i += 1
            draw_scale = int(scale_str) / 4 if scale_str else 1
            blank = False
            continue

        if ch in _DIR:
            num_str = ""
            while i < len(draw_string) and draw_string[i].isdigit():
                num_str += draw_string[i]
                i += 1
            dist = int(num_str) if num_str else 1
            dx, dy = _DIR[ch]
            nx = cx + dx * dist * draw_scale
            ny = cy + dy * dist * draw_scale

            if not blank:
                ctx.strokeStyle = current_color
                ctx.beginPath()
                ctx.moveTo(cx, cy)
                ctx.lineTo(nx, ny)
                ctx.stroke()

            cx, cy = nx, ny
            blank = False

    ctx.restore()
    return (cx, cy)


# --------------------------------------------------------------------------- #
#  Union Army sprite -- port of QBasic armyxy for Union
# --------------------------------------------------------------------------- #
def draw_union_army(ctx, x: float, y: float):
    ctx.fillStyle = VGA[0]
    ctx.fillRect(x - 5, y - 3, 16, 12)

    ctx.fillStyle = VGA[4]
    ctx.fillRect(x - 7, y - 5, 15, 11)

    ctx.fillStyle = VGA[1]
    ctx.fillRect(x - 7, y - 5, 7, 6)

    ctx.strokeStyle = VGA[7]
    ctx.lineWidth = 1
    ctx.strokeRect(x + 0.5, y - 1.5, 7, 1)
    ctx.strokeRect(x - 6.5, y + 2.5, 14, 1)

    ctx.strokeStyle = VGA[0]
    ctx.strokeRect(x - 7.5, y - 5.5, 17, 13)


# --------------------------------------------------------------------------- #
#  Confederate Army sprite -- port of QBasic armyxy for Confed
# --------------------------------------------------------------------------- #
def draw_confed_army(ctx, x: float, y: float):
    ctx.fillStyle = VGA[0]
    ctx.fillRect(x - 5, y - 3, 16, 12)

    ctx.fillStyle = VGA[4]
    ctx.fillRect(x - 7, y - 5, 15, 11)

    ctx.strokeStyle = VGA[0]
    ctx.lineWidth = 1
    ctx.strokeRect(x - 7.5, y - 5.5, 17, 13)

    ctx.strokeStyle = VGA[9]
    ctx.lineWidth = 1
    for sx, sy, ex, ey in [
        (x - 7, y - 4, x + 6, y + 5),
        (x - 7, y + 4, x + 6, y - 5),
        (x - 7, y - 5, x + 7, y + 5),
        (x - 7, y + 5, x + 7, y - 5),
    ]:
        ctx.beginPath()
        ctx.moveTo(sx, sy)
        ctx.lineTo(ex, ey)
        ctx.stroke()


# --------------------------------------------------------------------------- #
#  Supply warning "S" -- port of QBasic stax
# --------------------------------------------------------------------------- #
def draw_supply_warning(ctx, x: float, y: float):
    from font import draw_char

    sx = x - 3
    sy = y + 4

    ctx.save()
    ctx.strokeStyle = VGA[11]
    ctx.lineWidth = 1
    ctx.lineCap = "square"
    draw_char(ctx, 18, sx, sy, 2)  # 18 = 'S' (ord('S') - 65)
    ctx.restore()


# --------------------------------------------------------------------------- #
#  Stacking indicator -- yellow circle
# --------------------------------------------------------------------------- #
def draw_stack_indicator(ctx, x: float, y: float):
    from js import Math as JSMath  # type: ignore

    ctx.strokeStyle = VGA[14]
    ctx.lineWidth = 1
    ctx.beginPath()
    ctx.arc(x, y, 3, 0, JSMath.PI * 2)
    ctx.stroke()


# --------------------------------------------------------------------------- #
#  Ship icon -- port of QBasic SUB shipicon (lines 3847-3878)
# --------------------------------------------------------------------------- #
def draw_ship_icon(ctx, x: float, y: float, side: int, has_ironclad: bool):
    from js import Math as JSMath  # type: ignore

    ctx.save()
    ctx.imageSmoothingEnabled = False

    colour = 9 if side == 1 else 7
    jack = 9 if side == 1 else 4  # Union: blue flag, Confed: red flag

    # Hull ellipse: CIRCLE (x,y), 18, colour, , , .4
    ctx.fillStyle = VGA[colour]
    ctx.strokeStyle = VGA[colour]
    ctx.lineWidth = 1
    ctx.beginPath()
    ctx.ellipse(x, y, 18, 7, 0, 0, JSMath.PI * 2)
    ctx.fill()
    ctx.stroke()

    if has_ironclad:
        # Ironclad: armored superstructure
        execute_draw(ctx, x - 12, y,
                     "C0S4U3R7U3R4D3R5D3R4U3R3D6L20U3L4", VGA[0], 1)

        # Turret (dark gray fill)
        ctx.fillStyle = VGA[8]
        ctx.fillRect(x - 4, y - 8, 8, 4)
        ctx.strokeStyle = VGA[0]
        ctx.strokeRect(x - 4.5, y - 8.5, 9, 5)

        # Smokestack
        ctx.fillStyle = VGA[0]
        ctx.fillRect(x - 1, y - 13, 2, 5)

        # Flag at stern
        ctx.fillStyle = VGA[jack]
        ctx.fillRect(x + 12, y - 5, 4, 3)

    else:
        # Wooden ship: mast, rigging, sails

        # Main mast
        ctx.strokeStyle = VGA[0]
        ctx.lineWidth = 1
        ctx.beginPath()
        ctx.moveTo(x, y - 2)
        ctx.lineTo(x, y - 14)
        ctx.stroke()

        # Rear mast
        ctx.beginPath()
        ctx.moveTo(x + 8, y - 2)
        ctx.lineTo(x + 8, y - 11)
        ctx.stroke()

        # Fore mast
        ctx.beginPath()
        ctx.moveTo(x - 8, y - 2)
        ctx.lineTo(x - 8, y - 10)
        ctx.stroke()

        # Sails -- white triangles
        ctx.strokeStyle = VGA[15]
        for sx, sy, ex, ey in [
            (x - 1, y - 13, x - 8, y - 5),
            (x + 1, y - 13, x + 7, y - 5),
            (x + 9, y - 10, x + 15, y - 4),
        ]:
            ctx.beginPath()
            ctx.moveTo(sx, sy)
            ctx.lineTo(ex, ey)
            ctx.stroke()

        # Bowsprit
        ctx.strokeStyle = VGA[0]
        ctx.beginPath()
        ctx.moveTo(x - 8, y - 10)
        ctx.lineTo(x - 16, y - 4)
        ctx.stroke()

        # Rigging line
        ctx.strokeStyle = VGA[7]
        ctx.beginPath()
        ctx.moveTo(x, y - 14)
        ctx.lineTo(x - 16, y - 4)
        ctx.stroke()

        # Flag at top of main mast
        ctx.fillStyle = VGA[jack]
        ctx.fillRect(x + 1, y - 16, 5, 3)

        # Flag stripe
        ctx.fillStyle = VGA[4]
        ctx.fillRect(x + 1, y - 15, 5, 1)

    ctx.restore()


# --------------------------------------------------------------------------- #
#  Train / railroad engine -- port of QBasic SUB engine (lines 3013-29)
# --------------------------------------------------------------------------- #
def draw_train_icon(ctx, x: float, y: float, color: str):
    from js import Math as JSMath  # type: ignore

    ctx.save()
    ctx.imageSmoothingEnabled = False

    # Engine outline using exact DRAW command
    draw_cmd = "C0S4R9D4R6U3R3D3R7U5H3U2R9D3G2D6F1D3F5L10D1G1L4H2L7G2L3H2L3U8L2U5BF4"
    execute_draw(ctx, x, y, draw_cmd, VGA[0], 1)

    # Fill body with side color
    ctx.fillStyle = color
    ctx.fillRect(x + 1, y + 1, 8, 3)       # cab
    ctx.fillRect(x + 10, y - 2, 5, 6)       # boiler front
    ctx.fillRect(x + 16, y - 4, 6, 7)       # boiler
    ctx.fillRect(x + 22, y - 2, 3, 5)       # nose

    # Wheels
    ctx.strokeStyle = VGA[0]
    ctx.lineWidth = 1
    for wx, wy, wr in [(x + 5, y + 10, 3), (x + 15, y + 10, 3), (x + 22, y + 10, 2)]:
        ctx.beginPath()
        ctx.arc(wx, wy, wr, 0, JSMath.PI * 2)
        ctx.stroke()

    # Smokestack
    ctx.fillStyle = VGA[0]
    ctx.fillRect(x + 20, y - 8, 3, 4)

    # Smokestack top (wider)
    ctx.fillRect(x + 19, y - 9, 5, 1)

    ctx.restore()


# --------------------------------------------------------------------------- #
#  City drawing -- port of QBasic showcity
# --------------------------------------------------------------------------- #
def draw_city(ctx, x: float, y: float, owner: int, fort: int, is_capital: bool):
    from js import Math as JSMath  # type: ignore

    ctx.imageSmoothingEnabled = False

    if owner == 1:
        color_idx = 9
    elif owner == 2:
        color_idx = 7
    else:
        color_idx = 12
    c = VGA[color_idx]

    if is_capital:
        fort_sprite = get_sprite(f"fort{min(fort, 2)}")
        if fort_sprite and hasattr(fort_sprite, 'complete') and fort_sprite.complete and fort_sprite.naturalWidth > 0:
            ctx.drawImage(fort_sprite, x - 6, y - 6)
        else:
            ctx.fillStyle = VGA[3]
            ctx.fillRect(x - 6, y - 6, 13, 13)
            ctx.fillStyle = c
            ctx.beginPath()
            ctx.arc(x, y, 4, 0, JSMath.PI * 2)
            ctx.fill()
            ctx.strokeStyle = VGA[0]
            ctx.lineWidth = 1
            ctx.stroke()

        ctx.fillStyle = VGA[0]
        ctx.fillRect(x + 9, y - 4, 7, 9)
        ctx.fillStyle = VGA[3]
        ctx.fillRect(x + 8, y - 5, 6, 8)

        if fort == 1:
            ctx.strokeStyle = VGA[0]
            ctx.lineWidth = 1
            ctx.beginPath()
            ctx.moveTo(x + 10, y - 3)
            ctx.lineTo(x + 11, y - 4)
            ctx.lineTo(x + 11, y + 2)
            ctx.stroke()
        elif fort == 2:
            ctx.strokeStyle = VGA[0]
            ctx.lineWidth = 1
            ctx.beginPath()
            ctx.moveTo(x + 9, y - 4)
            ctx.lineTo(x + 10, y - 5)
            ctx.lineTo(x + 11, y - 4)
            ctx.lineTo(x + 11, y - 3)
            ctx.lineTo(x + 8, y)
            ctx.lineTo(x + 11, y)
            ctx.stroke()
    else:
        if fort == 1:
            ctx.strokeStyle = VGA[0]
            ctx.lineWidth = 1
            ctx.strokeRect(x - 4.5, y - 4.5, 10, 10)
        elif fort >= 2:
            ctx.fillStyle = VGA[0]
            ctx.fillRect(x - 5, y - 5, 11, 11)

        ctx.strokeStyle = VGA[0]
        ctx.lineWidth = 1
        ctx.beginPath()
        ctx.arc(x, y, 4, 0, JSMath.PI * 2)
        ctx.stroke()

        ctx.fillStyle = c
        ctx.strokeStyle = c
        ctx.lineWidth = 1
        ctx.beginPath()
        ctx.arc(x, y, 3, 0, JSMath.PI * 2)
        ctx.fill()
        ctx.stroke()
