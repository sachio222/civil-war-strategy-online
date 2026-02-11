"""map_renderer.py -- Main map renderer.

Exact port of map.js which is itself a port of QBasic SUB usa() from
CWSTRAT.BAS to HTML5 Canvas. Every LINE command is translated faithfully.
Water areas use real scanline flood fill matching QBasic PAINT.

Pixel ops (snapToVGA, floodFill) delegate to window.CWSPixelOps (JS helper)
for performance.
"""

from constants import VGA, MONTHS, MTN_POSITIONS, FLEET_SPECIAL_POS
import font
import sprites
from js_bridge import snap_to_vga, flood_fill
from pyodide.ffi import to_js  # type: ignore


# --------------------------------------------------------------------------- #
#  Helpers
# --------------------------------------------------------------------------- #
def _line(ctx, x1, y1, x2, y2):
    ctx.beginPath()
    ctx.moveTo(x1, y1)
    ctx.lineTo(x2, y2)
    ctx.stroke()


def _polyline(ctx, pts):
    if len(pts) < 2:
        return
    ctx.beginPath()
    ctx.moveTo(pts[0][0], pts[0][1])
    for i in range(1, len(pts)):
        ctx.lineTo(pts[i][0], pts[i][1])
    ctx.stroke()


def _stroke_box(ctx, x1, y1, x2, y2):
    lx = min(x1, x2)
    ly = min(y1, y2)
    w = abs(x2 - x1)
    h = abs(y2 - y1)
    ctx.strokeRect(lx + 0.5, ly + 0.5, w, h)


def _fill_box(ctx, x1, y1, x2, y2):
    lx = min(x1, x2)
    ly = min(y1, y2)
    w = abs(x2 - x1) + 1
    h = abs(y2 - y1) + 1
    ctx.fillRect(lx, ly, w, h)


def _connection_line(ctx, x1, y1, x2, y2):
    ctx.save()
    ctx.strokeStyle = VGA[0]
    ctx.lineWidth = 1
    ctx.setLineDash(to_js([1, 3]))
    ctx.beginPath()
    ctx.moveTo(x1, y1)
    ctx.lineTo(x2, y2)
    ctx.stroke()
    ctx.restore()


# --------------------------------------------------------------------------- #
#  draw_map(ctx, gs) -- Main entry point, port of SUB usa()
# --------------------------------------------------------------------------- #
def draw_map(ctx, gs):
    # Extract game state -- use .get() for Python dicts (after to_py conversion)
    if isinstance(gs, dict):
        cities = gs.get("cities", {})
        armies = gs.get("armies", {})
        fleets = gs.get("fleets", {})
        occupied = gs.get("occupied", {})
        capitals = gs.get("capitals", {})
        adjacency_matrix = gs.get("adjacency_matrix", {})
        player_side = gs.get("player_side", 1)
        railroad = gs.get("railroad", {})
        train = gs.get("train", {})
        commerce = gs.get("commerce", 0)
        month = gs.get("month")
        year = gs.get("year")
    else:
        # Fallback for JsProxy or other objects
        cities = getattr(gs, "cities", {}) or {}
        armies = getattr(gs, "armies", {}) or {}
        fleets = getattr(gs, "fleets", {}) or {}
        occupied = getattr(gs, "occupied", {}) or {}
        capitals = getattr(gs, "capitals", {}) or {}
        adjacency_matrix = getattr(gs, "adjacency_matrix", {}) or {}
        player_side = getattr(gs, "player_side", 1) or 1
        railroad = getattr(gs, "railroad", {}) or {}
        train = getattr(gs, "train", {}) or {}
        commerce = getattr(gs, "commerce", 0) or 0
        month = getattr(gs, "month", None)
        year = getattr(gs, "year", None)

    ctx.save()
    try:
        ctx.imageSmoothingEnabled = False
        ctx.lineWidth = 1
        ctx.lineCap = "square"
        ctx.lineJoin = "miter"
        ctx.setLineDash(to_js([]))
        ctx.lineDashOffset = 0
        ctx.globalAlpha = 1.0
        ctx.globalCompositeOperation = "source-over"

        # 1. Green border + fill
        ctx.strokeStyle = VGA[10]
        _stroke_box(ctx, 1, 16, 527, 440)
        ctx.fillStyle = VGA[2]
        ctx.fillRect(2, 17, 525, 423)

        # 2. Mountain sprites
        mtn_img = sprites.get_sprite("mtn")
        if mtn_img and hasattr(mtn_img, 'complete') and mtn_img.complete and mtn_img.naturalWidth > 0:
            ctx.imageSmoothingEnabled = False
            for mx, my in MTN_POSITIONS:
                ctx.drawImage(mtn_img, mx, my)
            ctx.fillStyle = VGA[2]
            _fill_box(ctx, 30, 150, 70, 190)

        # 3. State borders
        _draw_state_borders(ctx)

        # 4. Snap anti-aliased pixels to VGA, then flood fill water
        snap_to_vga(ctx)
        _draw_water_areas(ctx)

        # 5. Rivers
        _draw_rivers(ctx)

        # 6. Cities
        _draw_cities(ctx, cities, capitals)

        # 7. City connection lines
        _draw_connections(ctx, cities, adjacency_matrix)

        # 8. City name labels
        _draw_city_labels(ctx, cities, adjacency_matrix)

        # 9. Commerce raider box
        _draw_commerce_area(ctx, commerce)

        # 10. Railroad engine indicators
        _draw_railroad_engines(ctx, railroad, train, armies, cities)

        # 11. Armies
        _draw_armies(ctx, armies, cities, occupied)

        # 12. Movement lines (dashed white)
        _draw_movement_lines(ctx, armies, cities, player_side)

        # 13. Fleets
        _draw_fleets(ctx, fleets, cities)

        # 14. Naval blockade box
        _draw_naval_box(ctx, fleets, cities)

        # 15. Date display
        _draw_date(ctx, month, year)

        # 16. Snap anti-aliased text (city labels, etc.) to VGA for crisp pixels
        snap_to_vga(ctx)
    finally:
        ctx.restore()


# --------------------------------------------------------------------------- #
#  State borders -- exact port of every LINE command
# --------------------------------------------------------------------------- #
def _draw_state_borders(ctx):
    # Kentucky
    ctx.strokeStyle = VGA[10]
    ctx.lineWidth = 1

    _polyline(ctx, [(105, 190), (150, 190)])
    _polyline(ctx, [(150, 190), (150, 185), (290, 185)])
    _polyline(ctx, [(276, 185), (301, 175), (305, 160), (310, 155),
                    (305, 145), (300, 125), (290, 110)])

    ctx.strokeStyle = VGA[1]
    _polyline(ctx, [
        (290, 110), (275, 95), (270, 95), (260, 100), (250, 100),
        (240, 90), (235, 85), (230, 85), (220, 90), (220, 100),
        (210, 105), (205, 115), (195, 125), (170, 130), (165, 135),
        (130, 140), (120, 150), (120, 160), (115, 165), (105, 170), (105, 190),
    ])

    # Tennessee
    ctx.strokeStyle = VGA[10]
    _polyline(ctx, [
        (290, 185), (320, 185), (315, 195), (302, 210),
        (290, 215), (275, 230), (260, 241), (70, 241),
    ])

    ctx.strokeStyle = VGA[1]
    _polyline(ctx, [(105, 190), (95, 200), (80, 220), (70, 241)])

    # Mississippi
    ctx.strokeStyle = VGA[10]
    _polyline(ctx, [
        (143, 241), (145, 405), (135, 400), (125, 400),
        (115, 405), (110, 400), (110, 390), (115, 380), (115, 375), (50, 375),
    ])
    _line(ctx, 115, 375, 60, 375)

    ctx.strokeStyle = VGA[1]
    _polyline(ctx, [(70, 241), (65, 280), (60, 295),
              (65, 325), (65, 335), (50, 375)])

    # Alabama
    ctx.strokeStyle = VGA[10]
    _line(ctx, 215, 241, 232, 375)
    _polyline(ctx, [(176, 395), (181, 410), (166, 415),
              (161, 400), (156, 405), (146, 405)])
    _polyline(ctx, [(176, 395), (176, 385), (231, 385)])

    # Georgia & Florida
    _polyline(ctx, [
        (261, 241), (296, 241), (291, 265), (350, 340),
        (336, 390), (366, 440),
    ])
    _polyline(ctx, [(336, 385), (325, 385),
              (320, 388), (245, 388), (230, 385)])
    _polyline(ctx, [
        (180, 410), (195, 410), (215, 415), (225, 425),
        (255, 420), (265, 420), (270, 425), (275, 440),
    ])
    _polyline(ctx, [(347, 409), (343, 409), (343, 431),
              (346, 431), (346, 412), (349, 412)])

    ctx.strokeStyle = VGA[1]
    _line(ctx, 347, 411, 350, 411)

    ctx.strokeStyle = VGA[10]
    _stroke_box(ctx, 353, 333, 358, 336)

    # South Carolina
    _polyline(ctx, [
        (290, 241), (305, 240), (345, 240), (350, 250),
        (380, 250), (415, 280), (385, 315), (380, 320),
        (375, 325), (350, 330), (350, 340),
    ])

    # North Carolina
    _polyline(ctx, [
        (320, 185), (500, 185), (505, 190), (490, 195),
        (490, 205), (505, 205), (500, 215), (485, 220),
        (490, 225), (500, 225), (500, 230), (490, 235),
        (488, 240), (480, 241), (460, 250), (455, 255),
        (440, 265), (439, 270), (425, 278), (415, 280),
    ])

    _stroke_box(ctx, 510, 190, 513, 200)
    _polyline(ctx, [
        (510, 206), (510, 226), (500, 236), (502, 241),
        (512, 228), (512, 208), (510, 206),
    ])

    # Chesapeake Bay
    _draw_chessie(ctx)

    # Ohio/PA/MD/VA
    ctx.strokeStyle = VGA[1]
    _polyline(ctx, [
        (291, 111), (301, 101), (316, 96), (331, 76),
        (345, 51), (351, 30), (370, 35),
    ])

    ctx.strokeStyle = VGA[10]
    _line(ctx, 351, 16, 351, 54)
    _line(ctx, 351, 54, 527, 54)
    _polyline(ctx, [(381, 54), (381, 81), (431, 66), (456, 81), (471, 111)])
    _line(ctx, 226, 85, 226, 16)

    # Louisiana/Arkansas/Missouri
    ctx.strokeStyle = VGA[1]
    _polyline(ctx, [(50, 375), (60, 395), (105, 405), (110, 420), (125, 438)])

    ctx.strokeStyle = VGA[10]
    _polyline(ctx, [(110, 398), (105, 398), (90, 396), (90, 400)])
    _polyline(ctx, [
        (90, 400), (105, 402), (120, 415), (115, 420),
        (125, 435), (120, 440), (110, 425), (100, 435),
        (90, 440), (50, 430), (25, 435), (1, 435),
    ])

    _line(ctx, 1, 300, 61, 300)
    _polyline(ctx, [(91, 205), (71, 205), (76, 190), (71, 185), (1, 185)])

    ctx.strokeStyle = VGA[1]
    _polyline(ctx, [
        (106, 170), (91, 140), (71, 120), (76, 110),
        (76, 95), (71, 90), (61, 95), (56, 85), (50, 35), (46, 20),
    ])

    ctx.strokeStyle = VGA[10]
    _line(ctx, 46, 20, 38, 16)

    ctx.strokeStyle = VGA[1]
    _line(ctx, 46, 20, 61, 17)

    ctx.strokeStyle = VGA[10]
    _line(ctx, 150, 17, 150, 110)

    ctx.strokeStyle = VGA[1]
    _polyline(ctx, [(150, 110), (147, 125), (140, 138)])


# --------------------------------------------------------------------------- #
#  Chesapeake Bay -- exact port of SUB chessie
# --------------------------------------------------------------------------- #
def _draw_chessie(ctx):
    ctx.strokeStyle = VGA[10]
    ctx.lineWidth = 1

    _polyline(ctx, [
        (500, 185), (505, 180), (505, 175), (500, 170), (490, 165),
        (495, 160), (490, 155), (485, 150), (495, 155), (495, 145),
        (490, 140), (485, 130), (470, 120), (470, 110), (475, 120),
        (485, 120), (485, 115), (480, 100), (485, 90), (495, 80),
        (500, 80), (500, 85), (495, 90), (495, 100), (495, 115),
        (500, 120), (500, 130), (515, 135), (515, 140), (510, 160),
        (520, 145), (525, 120), (525, 115), (515, 85), (527, 95),
    ])


# --------------------------------------------------------------------------- #
#  Water areas -- real flood fill replicating QBasic PAINT
# --------------------------------------------------------------------------- #
def _draw_water_areas(ctx):
    flood_fill(ctx, 500, 400, 1, 10)  # Atlantic Ocean
    flood_fill(ctx, 510, 110, 2, 2)   # Chesapeake interior
    flood_fill(ctx, 250, 430, 1, 10)  # Gulf of Mexico
    flood_fill(ctx, 110, 439, 1, 10)  # Louisiana delta
    flood_fill(ctx, 50, 439, 1, 10)   # Far-west Gulf


# --------------------------------------------------------------------------- #
#  Rivers -- exact port of every river LINE command
# --------------------------------------------------------------------------- #
def _draw_rivers(ctx):
    ctx.strokeStyle = VGA[1]
    ctx.lineWidth = 1

    _polyline(ctx, [(1, 80), (15, 77), (25, 95), (50, 98), (75, 96)])
    _polyline(ctx, [
        (120, 160), (130, 200), (135, 240), (130, 247),
        (160, 250), (200, 260), (240, 244), (245, 240), (270, 200),
    ])
    _polyline(ctx, [(120, 160), (140, 200),
              (160, 210), (200, 208), (240, 170)])
    _polyline(ctx, [(161, 400), (155, 320), (145, 300)])
    _polyline(ctx, [(161, 400), (170, 370), (200, 350)])
    _polyline(ctx, [(230, 425), (231, 385),
              (233, 350), (240, 330), (270, 290)])
    _polyline(ctx, [(381, 81), (431, 66), (456, 81), (471, 111)])
    _polyline(ctx, [(485, 150), (455, 145), (400, 150)])
    _polyline(ctx, [(489, 200), (415, 185), (400, 160)])
    _polyline(ctx, [(296, 241), (291, 265), (350, 340)])
    _polyline(ctx, [(438, 271), (430, 235), (420, 205)])
    _polyline(ctx, [(500, 80), (498, 50), (470, 30)])
    _line(ctx, 405, 290, 360, 240)
    _line(ctx, 400, 300, 350, 280)
    _polyline(ctx, [(270, 423), (280, 410), (290, 390)])
    _line(ctx, 342, 370, 300, 350)
    _line(ctx, 50, 370, 1, 330)
    _line(ctx, 65, 280, 1, 240)
    _polyline(ctx, [(430, 66), (400, 100), (380, 120)])


# --------------------------------------------------------------------------- #
#  Cities
# --------------------------------------------------------------------------- #
def _draw_cities(ctx, cities, capitals):
    cap1 = capitals.get("1", capitals.get(1, 0))
    cap2 = capitals.get("2", capitals.get(2, 0))

    for key in cities:
        c = cities[key]
        cid = c.get("id", 0) if isinstance(c, dict) else getattr(c, "id", 0)
        cx = c.get("x", 0) if isinstance(c, dict) else getattr(c, "x", 0)
        cy = c.get("y", 0) if isinstance(c, dict) else getattr(c, "y", 0)
        owner = c.get("owner", 0) if isinstance(
            c, dict) else getattr(c, "owner", 0)
        fort_val = c.get("fort", 0) if isinstance(
            c, dict) else getattr(c, "fort", 0)
        is_capital = (cid == cap1 or cid == cap2)
        sprites.draw_city(ctx, cx, cy, owner, fort_val, is_capital)

    ctx.fillStyle = VGA[1]
    ctx.fillRect(493, 280, 1, 1)


# --------------------------------------------------------------------------- #
#  City connection lines (dotted black)
# --------------------------------------------------------------------------- #
def _draw_connections(ctx, cities, adjacency_matrix):
    drawn = set()

    for key in cities:
        c = cities[key]
        cid = c.get("id", 0) if isinstance(c, dict) else getattr(c, "id", 0)
        cx = c.get("x", 0) if isinstance(c, dict) else getattr(c, "x", 0)
        cy = c.get("y", 0) if isinstance(c, dict) else getattr(c, "y", 0)
        adj = c.get("adjacency", []) if isinstance(
            c, dict) else getattr(c, "adjacency", [])

        for dest_id in adj:
            if dest_id <= 0:
                continue
            pair_key = f"{min(cid, dest_id)}-{max(cid, dest_id)}"
            if pair_key in drawn:
                continue
            drawn.add(pair_key)

            dest = cities.get(str(dest_id)) or cities.get(dest_id)
            if not dest:
                continue

            dx = dest.get("x", 0) if isinstance(
                dest, dict) else getattr(dest, "x", 0)
            dy = dest.get("y", 0) if isinstance(
                dest, dict) else getattr(dest, "y", 0)
            _connection_line(ctx, cx, cy, dx, dy)


# --------------------------------------------------------------------------- #
#  City name labels
# --------------------------------------------------------------------------- #
def _draw_city_labels(ctx, cities, adjacency_matrix):
    for key in cities:
        c = cities[key]
        cx = c.get("x", 0) if isinstance(c, dict) else getattr(c, "x", 0)
        cy = c.get("y", 0) if isinstance(c, dict) else getattr(c, "y", 0)
        name = c.get("name", "") if isinstance(
            c, dict) else getattr(c, "name", "")
        port = c.get("port", 0) if isinstance(
            c, dict) else getattr(c, "port", 0)
        is_port = port >= 90
        start_x = cx + 6 * (1 - 4) - 3
        text_y = cy + 12
        text_color = VGA[10] if is_port else VGA[0]
        font.draw_text(ctx, name, start_x, text_y, text_color, 1)


# --------------------------------------------------------------------------- #
#  Commerce raider area
# --------------------------------------------------------------------------- #
def _draw_commerce_area(ctx, commerce):
    if commerce > 0:
        ctx.fillStyle = VGA[4]
        _fill_box(ctx, 447, 291, 525, 317)
        ctx.strokeStyle = VGA[10]
        _stroke_box(ctx, 447, 291, 525, 317)

        text = "COMMERCE"
        for j, ch in enumerate(text):
            char_x = 440 + 10 * (j + 1)
            font.draw_text(ctx, ch, char_x, 312, VGA[0], 1)
    else:
        ctx.fillStyle = VGA[1]
        _fill_box(ctx, 447, 291, 525, 335)


# --------------------------------------------------------------------------- #
#  Railroad engine indicators
# --------------------------------------------------------------------------- #
def _draw_railroad_engines(ctx, railroad, train, armies, cities):
    rr1 = railroad.get("1", railroad.get(1, 0))
    rr2 = railroad.get("2", railroad.get(2, 0))
    if rr1 + rr2 == 0:
        return

    ctx.fillStyle = VGA[3]
    _fill_box(ctx, 5, 17, 100, 63)
    ctx.strokeStyle = VGA[0]
    _stroke_box(ctx, 5, 17, 100, 47)
    _stroke_box(ctx, 5, 47, 100, 63)

    for side in [1, 2]:
        rr_army = rr1 if side == 1 else rr2
        if rr_army == 0:
            continue

        train_color = VGA[9] if side == 1 else VGA[15]
        base_x = 15 if side == 1 else 60
        sprites.draw_train_icon(ctx, base_x, 25, train_color)

        army = armies.get(str(rr_army)) or armies.get(rr_army)
        if army:
            mt = army.get("move_target", 0) if isinstance(
                army, dict) else getattr(army, "move_target", 0)
            if mt > 0:
                dest_city = cities.get(str(mt)) or cities.get(mt)
                if dest_city:
                    dname = dest_city.get("name", "") if isinstance(
                        dest_city, dict) else getattr(dest_city, "name", "")
                    label = dname[:5]
                    px_x = 8 if side == 1 else 55
                    font.print_text_px(ctx, px_x, 50, label, 0)


# --------------------------------------------------------------------------- #
#  Armies
# --------------------------------------------------------------------------- #
def _draw_armies(ctx, armies, cities, occupied):
    keys = list(armies.keys())

    # First pass: stack indicators
    for key in keys:
        a = armies[key]
        aid = a.get("id", 0) if isinstance(a, dict) else getattr(a, "id", 0)
        a_size = a.get("size", 0) if isinstance(
            a, dict) else getattr(a, "size", 0)
        a_loc = a.get("location", 0) if isinstance(
            a, dict) else getattr(a, "location", 0)
        if a_size <= 0 or a_loc <= 0:
            continue
        occ = occupied.get(str(a_loc), occupied.get(a_loc, 0))
        if occ != aid and occ > 0:
            city = cities.get(str(a_loc)) or cities.get(a_loc)
            if city:
                cx = city.get("x", 0) if isinstance(
                    city, dict) else getattr(city, "x", 0)
                cy = city.get("y", 0) if isinstance(
                    city, dict) else getattr(city, "y", 0)
                sprites.draw_stack_indicator(ctx, cx - 12, cy - 12)

    # Second pass: army sprites
    for key in keys:
        a = armies[key]
        aid = a.get("id", 0) if isinstance(a, dict) else getattr(a, "id", 0)
        a_size = a.get("size", 0) if isinstance(
            a, dict) else getattr(a, "size", 0)
        a_loc = a.get("location", 0) if isinstance(
            a, dict) else getattr(a, "location", 0)
        a_supply = a.get("supply", 0) if isinstance(
            a, dict) else getattr(a, "supply", 0)
        if a_size <= 0 or a_loc <= 0:
            continue

        city = cities.get(str(a_loc)) or cities.get(a_loc)
        if not city:
            continue

        cx = city.get("x", 0) if isinstance(
            city, dict) else getattr(city, "x", 0)
        cy = city.get("y", 0) if isinstance(
            city, dict) else getattr(city, "y", 0)
        ax = cx - 12
        ay = cy - 11
        side = 1 if aid <= 20 else 2

        if side == 1:
            sprites.draw_union_army(ctx, ax, ay)
        else:
            sprites.draw_confed_army(ctx, ax, ay)

        if a_supply < 1:
            sprites.draw_supply_warning(ctx, ax, ay)


# --------------------------------------------------------------------------- #
#  Movement lines (dashed white)
# --------------------------------------------------------------------------- #
def _draw_movement_lines(ctx, armies, cities, player_side):
    ctx.save()
    ctx.strokeStyle = VGA[15]
    ctx.lineWidth = 1
    ctx.setLineDash(to_js([4, 4]))

    for key in armies:
        a = armies[key]
        aid = a.get("id", 0) if isinstance(a, dict) else getattr(a, "id", 0)
        a_loc = a.get("location", 0) if isinstance(
            a, dict) else getattr(a, "location", 0)
        a_mt = a.get("move_target", 0) if isinstance(
            a, dict) else getattr(a, "move_target", 0)
        if a_loc <= 0 or a_mt <= 0:
            continue

        side = 1 if aid <= 20 else 2
        if side != player_side:
            continue

        from_city = cities.get(str(a_loc)) or cities.get(a_loc)
        to_city = cities.get(str(a_mt)) or cities.get(a_mt)
        if not from_city or not to_city:
            continue

        fx = (from_city.get("x", 0) if isinstance(from_city, dict)
              else getattr(from_city, "x", 0)) - 12
        fy = (from_city.get("y", 0) if isinstance(from_city, dict)
              else getattr(from_city, "y", 0)) - 11
        tx = to_city.get("x", 0) if isinstance(
            to_city, dict) else getattr(to_city, "x", 0)
        ty = to_city.get("y", 0) if isinstance(
            to_city, dict) else getattr(to_city, "y", 0)

        ctx.beginPath()
        ctx.moveTo(fx, fy)
        ctx.lineTo(tx, ty)
        ctx.stroke()

    ctx.restore()


# --------------------------------------------------------------------------- #
#  Fleets
# --------------------------------------------------------------------------- #
def _draw_fleets(ctx, fleets, cities):
    from js import Math as JSMath  # type: ignore

    for key in fleets:
        f = fleets[key]
        f_ships = f.get("ships", "") if isinstance(
            f, dict) else getattr(f, "ships", "")
        f_loc = f.get("location", 0) if isinstance(
            f, dict) else getattr(f, "location", 0)
        f_side = f.get("side", 0) if isinstance(
            f, dict) else getattr(f, "side", 0)
        if not f_ships or f_loc == 0:
            continue

        if f_loc in FLEET_SPECIAL_POS:
            sx, sy = FLEET_SPECIAL_POS[f_loc]
        else:
            city = cities.get(str(f_loc)) or cities.get(f_loc)
            if not city:
                continue
            cx = city.get("x", 0) if isinstance(
                city, dict) else getattr(city, "x", 0)
            cy = city.get("y", 0) if isinstance(
                city, dict) else getattr(city, "y", 0)
            sx = cx + 25
            sy = cy + 25
            if f_loc == 24:
                sy += 5
                sx -= 5

        has_ironclad = len(f_ships) > 0 and f_ships[0] == "I"
        sprites.draw_ship_icon(ctx, sx, sy, f_side, has_ironclad)


# --------------------------------------------------------------------------- #
#  Naval box
# --------------------------------------------------------------------------- #
def _draw_naval_box(ctx, fleets, cities):
    f1 = fleets.get("1") or fleets.get(1)
    f2 = fleets.get("2") or fleets.get(2)
    show = False
    if f1:
        loc = f1.get("location", 0) if isinstance(
            f1, dict) else getattr(f1, "location", 0)
        if loc == 30:
            show = True
    if f2:
        loc = f2.get("location", 0) if isinstance(
            f2, dict) else getattr(f2, "location", 0)
        if loc == 30:
            show = True

    if show:
        ctx.strokeStyle = VGA[11]
        ctx.lineWidth = 1
        font.draw_text(ctx, "NAVY", 490, 258, VGA[11], 1)
        _stroke_box(ctx, 485, 241, 525, 270)


# --------------------------------------------------------------------------- #
#  Date display
# --------------------------------------------------------------------------- #
def _draw_date(ctx, month, year):
    if not month or not year:
        return
    month_str = MONTHS[month][:3].upper() if 1 <= month <= 12 else ""
    date_str = f" {month_str},{year}"
    font.print_text(ctx, 24, 51, date_str, 13)


# --------------------------------------------------------------------------- #
#  Hit testing
# --------------------------------------------------------------------------- #
def hit_test_city(cities, mx, my, radius=12):
    best = None
    best_dist = radius * radius

    for key in cities:
        c = cities[key]
        cx = c.get("x", 0) if isinstance(c, dict) else getattr(c, "x", 0)
        cy = c.get("y", 0) if isinstance(c, dict) else getattr(c, "y", 0)
        dx = cx - mx
        dy = cy - my
        d2 = dx * dx + dy * dy
        if d2 < best_dist:
            best_dist = d2
            best = c

    return best


def hit_test_army(armies, cities, mx, my):
    best = None
    best_dist = 15 * 15

    for key in armies:
        a = armies[key]
        a_size = a.get("size", 0) if isinstance(
            a, dict) else getattr(a, "size", 0)
        a_loc = a.get("location", 0) if isinstance(
            a, dict) else getattr(a, "location", 0)
        if a_size <= 0 or a_loc <= 0:
            continue
        city = cities.get(str(a_loc)) or cities.get(a_loc)
        if not city:
            continue
        cx = city.get("x", 0) if isinstance(
            city, dict) else getattr(city, "x", 0)
        cy = city.get("y", 0) if isinstance(
            city, dict) else getattr(city, "y", 0)
        ax = cx - 12
        ay = cy - 11
        dx = ax - mx
        dy = ay - my
        d2 = dx * dx + dy * dy
        if d2 < best_dist:
            best_dist = d2
            best = a

    return best


def find_city(cities, city_id):
    return cities.get(str(city_id)) or cities.get(city_id)
