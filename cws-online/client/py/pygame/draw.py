"""pygame.draw replacement — draws into Surface bytearray."""

import math
from pygame.surface import _unpack_rgb


def line(surface, color, start_pos, end_pos, width=1):
    """Draw a line using Bresenham's algorithm."""
    r, g, b = _unpack_rgb(color)
    x0, y0 = int(start_pos[0]), int(start_pos[1])
    x1, y1 = int(end_pos[0]), int(end_pos[1])

    _bresenham(surface, x0, y0, x1, y1, r, g, b)


def _bresenham(surface, x0, y0, x1, y1, r, g, b):
    """Bresenham's line algorithm."""
    data = surface._data
    w = surface._w
    h = surface._h

    dx = abs(x1 - x0)
    dy = abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx - dy

    while True:
        if 0 <= x0 < w and 0 <= y0 < h:
            off = (y0 * w + x0) * 4
            data[off] = r
            data[off + 1] = g
            data[off + 2] = b
            data[off + 3] = 255
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            x0 += sx
        if e2 < dx:
            err += dx
            y0 += sy


def rect(surface, color, rect_arg, width=0):
    """Draw or fill a rectangle."""
    r, g, b = _unpack_rgb(color)
    if hasattr(rect_arg, 'x'):
        rx, ry, rw, rh = rect_arg.x, rect_arg.y, rect_arg.width, rect_arg.height
    else:
        rx, ry, rw, rh = int(rect_arg[0]), int(rect_arg[1]), int(rect_arg[2]), int(rect_arg[3])

    data = surface._data
    sw = surface._w
    sh = surface._h

    if width == 0:
        # Filled rectangle
        x1 = max(0, rx)
        y1 = max(0, ry)
        x2 = min(sw, rx + rw)
        y2 = min(sh, ry + rh)
        if x2 <= x1 or y2 <= y1:
            return
        row_bytes = bytearray((x2 - x1) * 4)
        for i in range(x2 - x1):
            off = i * 4
            row_bytes[off] = r
            row_bytes[off + 1] = g
            row_bytes[off + 2] = b
            row_bytes[off + 3] = 255
        for y in range(y1, y2):
            start = (y * sw + x1) * 4
            data[start:start + len(row_bytes)] = row_bytes
    else:
        # Outline rectangle
        # Top and bottom
        for x in range(rx, rx + rw):
            if 0 <= x < sw:
                if 0 <= ry < sh:
                    off = (ry * sw + x) * 4
                    data[off] = r; data[off+1] = g; data[off+2] = b; data[off+3] = 255
                y_bot = ry + rh - 1
                if 0 <= y_bot < sh:
                    off = (y_bot * sw + x) * 4
                    data[off] = r; data[off+1] = g; data[off+2] = b; data[off+3] = 255
        # Left and right
        for y in range(ry, ry + rh):
            if 0 <= y < sh:
                if 0 <= rx < sw:
                    off = (y * sw + rx) * 4
                    data[off] = r; data[off+1] = g; data[off+2] = b; data[off+3] = 255
                x_right = rx + rw - 1
                if 0 <= x_right < sw:
                    off = (y * sw + x_right) * 4
                    data[off] = r; data[off+1] = g; data[off+2] = b; data[off+3] = 255


def circle(surface, color, center, radius, width=0):
    """Draw a circle using midpoint algorithm."""
    r, g, b = _unpack_rgb(color)
    cx, cy = int(center[0]), int(center[1])
    radius = int(radius)

    if width == 0:
        # Filled circle
        _fill_circle(surface, cx, cy, radius, r, g, b)
    else:
        _outline_circle(surface, cx, cy, radius, r, g, b)


def _fill_circle(surface, cx, cy, radius, r, g, b):
    data = surface._data
    w = surface._w
    h = surface._h
    for y in range(-radius, radius + 1):
        py = cy + y
        if py < 0 or py >= h:
            continue
        half = int(math.sqrt(radius * radius - y * y))
        x1 = max(0, cx - half)
        x2 = min(w - 1, cx + half)
        for px in range(x1, x2 + 1):
            off = (py * w + px) * 4
            data[off] = r; data[off+1] = g; data[off+2] = b; data[off+3] = 255


def _outline_circle(surface, cx, cy, radius, r, g, b):
    data = surface._data
    w = surface._w
    h = surface._h

    def _plot(px, py):
        if 0 <= px < w and 0 <= py < h:
            off = (py * w + px) * 4
            data[off] = r; data[off+1] = g; data[off+2] = b; data[off+3] = 255

    x = 0
    y = radius
    d = 1 - radius
    while x <= y:
        _plot(cx + x, cy + y)
        _plot(cx - x, cy + y)
        _plot(cx + x, cy - y)
        _plot(cx - x, cy - y)
        _plot(cx + y, cy + x)
        _plot(cx - y, cy + x)
        _plot(cx + y, cy - x)
        _plot(cx - y, cy - x)
        if d < 0:
            d += 2 * x + 3
        else:
            d += 2 * (x - y) + 5
            y -= 1
        x += 1


def ellipse(surface, color, rect_arg, width=0):
    """Draw an ellipse."""
    r, g, b = _unpack_rgb(color)
    if hasattr(rect_arg, 'x'):
        rx, ry, rw, rh = rect_arg.x, rect_arg.y, rect_arg.width, rect_arg.height
    else:
        rx, ry, rw, rh = int(rect_arg[0]), int(rect_arg[1]), int(rect_arg[2]), int(rect_arg[3])

    cx = rx + rw // 2
    cy = ry + rh // 2
    a = rw // 2
    b_rad = rh // 2

    if a <= 0 or b_rad <= 0:
        return

    data = surface._data
    sw = surface._w
    sh = surface._h

    if width == 0:
        # Filled ellipse
        for dy in range(-b_rad, b_rad + 1):
            py = cy + dy
            if py < 0 or py >= sh:
                continue
            half = int(a * math.sqrt(1.0 - (dy * dy) / (b_rad * b_rad))) if b_rad > 0 else 0
            x1 = max(0, cx - half)
            x2 = min(sw - 1, cx + half)
            for px in range(x1, x2 + 1):
                off = (py * sw + px) * 4
                data[off] = r; data[off+1] = g; data[off+2] = b; data[off+3] = 255
    else:
        # Outline ellipse (sample at high resolution)
        steps = max(60, (a + b_rad) * 2)
        for i in range(steps):
            angle = 2.0 * math.pi * i / steps
            px = int(cx + a * math.cos(angle))
            py = int(cy + b_rad * math.sin(angle))
            if 0 <= px < sw and 0 <= py < sh:
                off = (py * sw + px) * 4
                data[off] = r; data[off+1] = g; data[off+2] = b; data[off+3] = 255


def polygon(surface, color, points, width=0):
    """Draw a polygon."""
    r, g, b = _unpack_rgb(color)
    pts = [(int(p[0]), int(p[1])) for p in points]

    if width == 0:
        # Filled polygon — scanline fill
        _fill_polygon(surface, pts, r, g, b)
    else:
        # Outline
        for i in range(len(pts)):
            x0, y0 = pts[i]
            x1, y1 = pts[(i + 1) % len(pts)]
            _bresenham(surface, x0, y0, x1, y1, r, g, b)


def _fill_polygon(surface, pts, r, g, b):
    """Scanline polygon fill."""
    if not pts:
        return
    data = surface._data
    w = surface._w
    h = surface._h

    min_y = max(0, min(p[1] for p in pts))
    max_y = min(h - 1, max(p[1] for p in pts))

    for y in range(min_y, max_y + 1):
        nodes = []
        n = len(pts)
        j = n - 1
        for i in range(n):
            yi = pts[i][1]
            yj = pts[j][1]
            if (yi < y <= yj) or (yj < y <= yi):
                xi = pts[i][0]
                xj = pts[j][0]
                x = int(xi + (y - yi) / (yj - yi) * (xj - xi))
                nodes.append(x)
            j = i
        nodes.sort()
        for i in range(0, len(nodes) - 1, 2):
            x1 = max(0, nodes[i])
            x2 = min(w - 1, nodes[i + 1])
            for px in range(x1, x2 + 1):
                off = (y * w + px) * 4
                data[off] = r; data[off+1] = g; data[off+2] = b; data[off+3] = 255


def arc(surface, color, rect_arg, start_angle, stop_angle, width=1):
    """Draw an arc."""
    r, g, b = _unpack_rgb(color)
    if hasattr(rect_arg, 'x'):
        rx, ry, rw, rh = rect_arg.x, rect_arg.y, rect_arg.width, rect_arg.height
    else:
        rx, ry, rw, rh = int(rect_arg[0]), int(rect_arg[1]), int(rect_arg[2]), int(rect_arg[3])

    cx = rx + rw // 2
    cy = ry + rh // 2
    a = rw // 2
    b_rad = rh // 2
    data = surface._data
    sw = surface._w
    sh = surface._h

    steps = max(60, (a + b_rad) * 2)
    angle_range = stop_angle - start_angle
    if angle_range < 0:
        angle_range += 2 * math.pi

    for i in range(steps + 1):
        angle = start_angle + angle_range * i / steps
        px = int(cx + a * math.cos(angle))
        py = int(cy - b_rad * math.sin(angle))  # pygame y-axis is inverted
        if 0 <= px < sw and 0 <= py < sh:
            off = (py * sw + px) * 4
            data[off] = r; data[off+1] = g; data[off+2] = b; data[off+3] = 255
