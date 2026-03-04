"""cws_screen_pygame.py — Web canvas screen backend.

Named to match the desktop import path. The desktop code does:
    from cws_screen_pygame import PygameScreen, flip
This file provides the same interface backed by a shadow framebuffer
(640x480 RGBA bytearray) + message-passing to the main thread.
"""

import math
from vga_font import get_glyph, CHAR_W as _VGA_CW, CHAR_H as _VGA_CH
from pygame.surface import Surface, _unpack_rgb

# ── VGA 16-color palette ─────────────────────────────────────────────────────
VGA = [
    (0x00, 0x00, 0x00),  # 0  black
    (0x00, 0x00, 0xAA),  # 1  blue
    (0x00, 0xAA, 0x00),  # 2  green
    (0x00, 0xAA, 0xAA),  # 3  cyan
    (0xAA, 0x00, 0x00),  # 4  red
    (0xAA, 0x00, 0xAA),  # 5  magenta
    (0xAA, 0x55, 0x00),  # 6  brown
    (0xAA, 0xAA, 0xAA),  # 7  light gray
    (0x55, 0x55, 0x55),  # 8  dark gray
    (0x55, 0x55, 0xFF),  # 9  light blue
    (0x55, 0xFF, 0x55),  # 10 light green
    (0x55, 0xFF, 0xFF),  # 11 light cyan
    (0xFF, 0x55, 0x55),  # 12 light red
    (0xFF, 0x55, 0xFF),  # 13 light magenta
    (0xFF, 0xFF, 0x55),  # 14 yellow
    (0xFF, 0xFF, 0xFF),  # 15 white
]

# Character cell size (SCREEN 12: 80 cols x 30 rows)
CHAR_W = 8
CHAR_H = 16

# Module-level reference for flip()
_active_screen = None

# Frame posting function — set up by _init_js()
_js_post_frame = None


def _init_js():
    """Set up JS interop for posting frames. Called once on first update()."""
    global _js_post_frame
    if _js_post_frame is not None:
        return

    try:
        try:
            from pyodide.code import run_js
        except ImportError:
            from pyodide import run_js
        # Create a JS function that accepts a Pyodide buffer proxy.
        # PyBuffer.getBuffer() gives access to the underlying data;
        # we copy it into a fresh Uint8ClampedArray for the main thread.
        _js_post_frame = run_js("""
        (function(pyBuf) {
            try {
                var data = pyBuf.getBuffer();
                var src = new Uint8Array(data.data.buffer,
                                         data.data.byteOffset,
                                         data.data.byteLength);
                var copy = new Uint8ClampedArray(src);
                data.release();
                self.postMessage({type: "frame", buffer: copy.buffer},
                                 [copy.buffer]);
            } catch(e) {
                // Fallback: treat pyBuf as a TypedArray-like
                try {
                    var len = pyBuf.length;
                    var copy2 = new Uint8ClampedArray(len);
                    for (var i = 0; i < len; i++) copy2[i] = pyBuf[i];
                    self.postMessage({type: "frame", buffer: copy2.buffer},
                                     [copy2.buffer]);
                } catch(e2) {
                    console.error("postFrame error:", e2);
                }
            }
        })
        """)
    except Exception as e:
        print(f"_init_js error: {e}")
        _js_post_frame = lambda buf: None


def _post_frame(data):
    """Post framebuffer bytes to the main thread."""
    global _js_post_frame
    if _js_post_frame is None:
        _init_js()
    try:
        _js_post_frame(bytes(data))
    except Exception as e:
        print(f"_post_frame error: {e}")


def flip():
    """Scale+flip replacement — calls _active_screen.update()."""
    if _active_screen is not None:
        _active_screen.update()


class PygameScreen:
    """Web implementation of the Screen protocol.

    All drawing goes to a shadow Surface (640x480).
    update() posts the raw RGBA bytes to the main thread for canvas rendering.
    """

    def __init__(self, surface=None, display=None):
        global _active_screen
        # Internal 640x480 render target
        if surface is None:
            self.surface = Surface((640, 480))
        else:
            self.surface = surface
        _active_screen = self
        self._fg_color = 15
        self._row = 1
        self._col = 1
        self._clip = None
        self._last_x = 0
        self._last_y = 0
        self._draw_color = None
        self._draw_scale = 4

    # ── Color ─────────────────────────────────────────────────────────────

    def color(self, c):
        self._fg_color = c % 16
        self._draw_color = None

    def _rgb(self, c=-1):
        if c < 0:
            c = self._fg_color
        return VGA[c % 16]

    # ── Text ──────────────────────────────────────────────────────────────

    def locate(self, row, col):
        self._row = max(1, min(30, row))
        self._col = max(1, min(80, col))

    def print_text(self, text):
        x = (self._col - 1) * CHAR_W
        y = (self._row - 1) * CHAR_H
        # Clear background
        tw = len(text) * CHAR_W
        self._fill_rect_raw(x, y, tw, CHAR_H, 0, 0, 0, 255)
        # Blit each character
        rgb = self._rgb()
        for ch in text:
            code = ord(ch)
            if 32 <= code <= 126:
                glyph = get_glyph(code, rgb)
                self.surface.blit(glyph, (x, y))
            x += CHAR_W
        self._col += len(text)

    # ── Drawing primitives ────────────────────────────────────────────────

    def line(self, x1, y1, x2, y2, c, style="", pattern=0xFFFF):
        rgb = self._rgb(c)
        r, g, b = rgb
        data = self.surface._data
        w = self.surface._w
        h = self.surface._h

        if "BF" in style.upper():
            # Filled rectangle
            rx = min(x1, x2)
            ry = min(y1, y2)
            rw = abs(x2 - x1) + 1
            rh = abs(y2 - y1) + 1
            self._fill_rect_raw(rx, ry, rw, rh, r, g, b, 255)
        elif "B" in style.upper():
            # Rectangle outline
            rx = min(x1, x2)
            ry = min(y1, y2)
            rw = abs(x2 - x1) + 1
            rh = abs(y2 - y1) + 1
            # Top and bottom
            for x in range(max(0, rx), min(w, rx + rw)):
                if 0 <= ry < h:
                    off = (ry * w + x) * 4
                    data[off] = r; data[off+1] = g; data[off+2] = b; data[off+3] = 255
                by = ry + rh - 1
                if 0 <= by < h:
                    off = (by * w + x) * 4
                    data[off] = r; data[off+1] = g; data[off+2] = b; data[off+3] = 255
            # Left and right
            for y in range(max(0, ry), min(h, ry + rh)):
                if 0 <= rx < w:
                    off = (y * w + rx) * 4
                    data[off] = r; data[off+1] = g; data[off+2] = b; data[off+3] = 255
                bx = rx + rw - 1
                if 0 <= bx < w:
                    off = (y * w + bx) * 4
                    data[off] = r; data[off+1] = g; data[off+2] = b; data[off+3] = 255
        else:
            # Line
            if pattern != 0xFFFF:
                self._dashed_line(x1, y1, x2, y2, r, g, b, pattern)
            else:
                self._line_raw(x1, y1, x2, y2, r, g, b)

        self._last_x = x2
        self._last_y = y2

    def _line_raw(self, x0, y0, x1, y1, r, g, b):
        """Bresenham line directly on shadow buffer."""
        data = self.surface._data
        w = self.surface._w
        h = self.surface._h
        x0, y0, x1, y1 = int(x0), int(y0), int(x1), int(y1)

        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy

        while True:
            if 0 <= x0 < w and 0 <= y0 < h:
                off = (y0 * w + x0) * 4
                data[off] = r; data[off+1] = g; data[off+2] = b; data[off+3] = 255
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x0 += sx
            if e2 < dx:
                err += dx
                y0 += sy

    def _dashed_line(self, x1, y1, x2, y2, r, g, b, pattern):
        dx = x2 - x1
        dy = y2 - y1
        dist = max(1, int(math.sqrt(dx * dx + dy * dy)))
        sx = dx / dist
        sy = dy / dist
        data = self.surface._data
        w = self.surface._w
        h = self.surface._h

        for i in range(dist + 1):
            bit = (pattern >> (15 - (i % 16))) & 1
            if bit:
                px = int(x1 + i * sx)
                py = int(y1 + i * sy)
                if 0 <= px < w and 0 <= py < h:
                    off = (py * w + px) * 4
                    data[off] = r; data[off+1] = g; data[off+2] = b; data[off+3] = 255

    def circle(self, x, y, radius, c, fill=False, aspect=1.0,
               start=None, end=None):
        rgb = self._rgb(c)
        r_c, g_c, b_c = rgb

        if aspect == 1.0:
            rx = radius
            ry = radius
        elif aspect < 1.0:
            rx = radius
            ry = max(1, int(radius * aspect))
        else:
            rx = max(1, int(radius / aspect))
            ry = radius

        data = self.surface._data
        w = self.surface._w
        h = self.surface._h

        if start is not None and end is not None:
            # Arc
            steps = max(60, (rx + ry) * 2)
            angle_range = end - start
            if angle_range < 0:
                angle_range += 2 * math.pi
            for i in range(steps + 1):
                angle = start + angle_range * i / steps
                px = int(x + rx * math.cos(angle))
                py = int(y - ry * math.sin(angle))
                if 0 <= px < w and 0 <= py < h:
                    off = (py * w + px) * 4
                    data[off] = r_c; data[off+1] = g_c; data[off+2] = b_c; data[off+3] = 255
        elif fill:
            # Filled ellipse
            for dy in range(-ry, ry + 1):
                py = y + dy
                if py < 0 or py >= h:
                    continue
                if ry > 0:
                    half = int(rx * math.sqrt(1.0 - (dy * dy) / (ry * ry)))
                else:
                    half = rx
                x1 = max(0, x - half)
                x2 = min(w - 1, x + half)
                for px in range(x1, x2 + 1):
                    off = (py * w + px) * 4
                    data[off] = r_c; data[off+1] = g_c; data[off+2] = b_c; data[off+3] = 255
        else:
            # Outline ellipse
            steps = max(60, (rx + ry) * 2)
            for i in range(steps):
                angle = 2.0 * math.pi * i / steps
                px = int(x + rx * math.cos(angle))
                py = int(y + ry * math.sin(angle))
                if 0 <= px < w and 0 <= py < h:
                    off = (py * w + px) * 4
                    data[off] = r_c; data[off+1] = g_c; data[off+2] = b_c; data[off+3] = 255

        self._last_x = x
        self._last_y = y

    def polygon(self, points, c, fill=False):
        rgb = self._rgb(c)
        r_c, g_c, b_c = rgb
        pts = [(int(p[0]), int(p[1])) for p in points]

        data = self.surface._data
        w = self.surface._w
        h = self.surface._h

        if fill:
            # Scanline fill
            if not pts:
                return
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
                        xn = int(xi + (y - yi) / (yj - yi) * (xj - xi))
                        nodes.append(xn)
                    j = i
                nodes.sort()
                for i in range(0, len(nodes) - 1, 2):
                    x1 = max(0, nodes[i])
                    x2 = min(w - 1, nodes[i + 1])
                    for px in range(x1, x2 + 1):
                        off = (y * w + px) * 4
                        data[off] = r_c; data[off+1] = g_c; data[off+2] = b_c; data[off+3] = 255
        else:
            for i in range(len(pts)):
                x0, y0 = pts[i]
                x1, y1 = pts[(i + 1) % len(pts)]
                self._line_raw(x0, y0, x1, y1, r_c, g_c, b_c)

    def pset(self, x, y, c):
        if 0 <= x < 640 and 0 <= y < 480:
            rgb = self._rgb(c)
            off = (y * 640 + x) * 4
            self.surface._data[off] = rgb[0]
            self.surface._data[off + 1] = rgb[1]
            self.surface._data[off + 2] = rgb[2]
            self.surface._data[off + 3] = 255
        self._last_x = x
        self._last_y = y

    def line_to(self, x, y, c=-1, style="", pattern=0xFFFF):
        if c < 0:
            c = self._fg_color
        self.line(self._last_x, self._last_y, x, y, c, style, pattern)

    # ── DRAW command interpreter ──────────────────────────────────────────

    _DRAW_DIR = {
        'U': (0, -1), 'D': (0, 1), 'L': (-1, 0), 'R': (1, 0),
        'E': (1, -1), 'F': (1, 1), 'G': (-1, 1), 'H': (-1, -1),
    }

    def draw(self, draw_str):
        cx = self._last_x
        cy = self._last_y
        color_idx = self._draw_color if self._draw_color is not None else self._fg_color
        scale = self._draw_scale
        i = 0
        s = draw_str.upper()
        data = self.surface._data
        w = self.surface._w
        h = self.surface._h

        while i < len(s):
            ch = s[i]
            i += 1

            blind = False
            no_update = False
            while ch in ('B', 'N'):
                if ch == 'B':
                    blind = True
                elif ch == 'N':
                    no_update = True
                if i < len(s):
                    ch = s[i]
                    i += 1
                else:
                    break

            if ch == 'C':
                num = ''
                while i < len(s) and s[i].isdigit():
                    num += s[i]
                    i += 1
                color_idx = int(num) % 16 if num else 0
                continue

            if ch == 'S':
                num = ''
                while i < len(s) and s[i].isdigit():
                    num += s[i]
                    i += 1
                scale = int(num) if num else 4
                continue

            if ch in self._DRAW_DIR:
                num = ''
                while i < len(s) and s[i].isdigit():
                    num += s[i]
                    i += 1
                dist = int(num) if num else 1

                dx, dy = self._DRAW_DIR[ch]
                nx = cx + int(dx * dist * scale / 4)
                ny = cy + int(dy * dist * scale / 4)

                if not blind:
                    rgb = VGA[color_idx]
                    self._line_raw(cx, cy, nx, ny, rgb[0], rgb[1], rgb[2])

                if not no_update:
                    cx, cy = nx, ny

        self._last_x = cx
        self._last_y = cy
        self._draw_color = color_idx
        self._draw_scale = scale
        return (cx, cy)

    # ── Image operations ──────────────────────────────────────────────────

    def put_image(self, x, y, sprite):
        if isinstance(sprite, Surface):
            self.surface.blit(sprite, (x, y))

    def get_image(self, x1, y1, x2, y2):
        rx = min(x1, x2)
        ry = min(y1, y2)
        rw = abs(x2 - x1) + 1
        rh = abs(y2 - y1) + 1
        rx = max(0, rx)
        ry = max(0, ry)
        if rx + rw > 640:
            rw = 640 - rx
        if ry + rh > 480:
            rh = 480 - ry
        img = Surface((rw, rh), self.surface._flags)
        img.blit(self.surface, (0, 0), (rx, ry, rw, rh))
        return img

    # ── View/Clipping ─────────────────────────────────────────────────────

    def view(self, x1=-1, y1=-1, x2=-1, y2=-1):
        if x1 < 0:
            self._clip = None
            self.surface.set_clip(None)
        else:
            self._clip = (x1, y1, x2 - x1 + 1, y2 - y1 + 1)
            self.surface.set_clip(self._clip)

    def cls(self, mode=0):
        if mode == 1 and self._clip:
            rx, ry, rw, rh = self._clip
            self._fill_rect_raw(rx, ry, rw, rh, 0, 0, 0, 255)
        else:
            self.surface._data = bytearray(640 * 480 * 4)
            self._clip = None
            self.surface.set_clip(None)
        self._row = 1
        self._col = 1

    # ── Paint (flood fill) ────────────────────────────────────────────────

    def paint(self, x, y, fill_c, border_c=-1):
        fill_rgb = self._rgb(fill_c)
        border_rgb = self._rgb(border_c) if border_c >= 0 else fill_rgb

        w, h = 640, 480
        if x < 0 or x >= w or y < 0 or y >= h:
            return

        data = self.surface._data
        off = (y * w + x) * 4
        start_r, start_g, start_b = data[off], data[off+1], data[off+2]
        fr, fg, fb = fill_rgb
        br, bg, bb = border_rgb

        if (start_r == fr and start_g == fg and start_b == fb):
            return
        if (start_r == br and start_g == bg and start_b == bb):
            return

        def _blocked(px, py):
            if px < 0 or px >= w or py < 0 or py >= h:
                return True
            o = (py * w + px) * 4
            cr, cg, cb = data[o], data[o+1], data[o+2]
            if cr == br and cg == bg and cb == bb:
                return True
            if cr == fr and cg == fg and cb == fb:
                return True
            return False

        stack = [(x, y)]
        while stack:
            sx, sy = stack.pop()
            if _blocked(sx, sy):
                continue

            # Scan left
            lx = sx
            while lx > 0 and not _blocked(lx - 1, sy):
                lx -= 1
            # Scan right
            rx = sx
            while rx < w - 1 and not _blocked(rx + 1, sy):
                rx += 1

            # Fill horizontal span
            for px in range(lx, rx + 1):
                o = (sy * w + px) * 4
                data[o] = fr; data[o+1] = fg; data[o+2] = fb; data[o+3] = 255

            # Seed rows above and below
            for ny in (sy - 1, sy + 1):
                if ny < 0 or ny >= h:
                    continue
                in_span = False
                for nx in range(lx, rx + 1):
                    if _blocked(nx, ny):
                        in_span = False
                    elif not in_span:
                        stack.append((nx, ny))
                        in_span = True

    # ── Convenience ───────────────────────────────────────────────────────

    def update(self):
        """Post framebuffer to main thread for canvas rendering."""
        _post_frame(self.surface._data)

    def fill_rect(self, x, y, w, h, c):
        rgb = self._rgb(c)
        self._fill_rect_raw(x, y, w, h, rgb[0], rgb[1], rgb[2], 255)

    def _fill_rect_raw(self, x, y, w, h, r, g, b, a):
        """Fill a rectangle directly in the shadow buffer."""
        data = self.surface._data
        sw = self.surface._w
        sh = self.surface._h

        x1 = max(0, int(x))
        y1 = max(0, int(y))
        x2 = min(sw, int(x + w))
        y2 = min(sh, int(y + h))
        if x2 <= x1 or y2 <= y1:
            return

        row_w = x2 - x1
        row_bytes = bytearray(row_w * 4)
        for i in range(row_w):
            off = i * 4
            row_bytes[off] = r
            row_bytes[off + 1] = g
            row_bytes[off + 2] = b
            row_bytes[off + 3] = a

        for yy in range(y1, y2):
            start = (yy * sw + x1) * 4
            data[start:start + row_w * 4] = row_bytes
