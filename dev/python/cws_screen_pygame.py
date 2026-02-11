"""cws_screen_pygame.py - Pygame rendering backend.

Implements the Screen protocol from cws_globals.py using Pygame.
Targets SCREEN 12: 640x480, 16-color VGA, 80x30 text grid (8x16 chars).

Monochrome low-effort mode: uses simple shapes, no sprites.
"""

import pygame
from vga_font import get_glyph, CHAR_W as _VGA_CW, CHAR_H as _VGA_CH

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

# Module-level reference so standalone helpers (_wait_key etc.)
# can scale+flip without access to the GameState.
_active_screen: 'PygameScreen | None' = None


def flip() -> None:
    """Scale the internal surface to the display and flip.

    Drop-in replacement for ``pygame.display.flip()`` anywhere in the
    codebase.  If no PygameScreen has been created yet, falls back to a
    plain flip.
    """
    if _active_screen is not None:
        _active_screen.update()
    else:
        pygame.display.flip()


class PygameScreen:
    """Pygame implementation of the Screen protocol.

    All QB64 drawing commands map to pygame calls.
    Coordinates are in pixels (0-639 x 0-479) just like SCREEN 12.
    Text positions use 1-based (row, col) like QB64's LOCATE.

    Rendering pipeline:
        All drawing goes to an internal 640x480 surface.
        update() nearest-neighbor-scales it to the display surface,
        giving the classic pixel-sharp retro look.
    """

    def __init__(self, surface: pygame.Surface, display: pygame.Surface | None = None):
        global _active_screen
        # Internal 640x480 render target (all drawing happens here)
        self.surface = surface
        # The actual OS window surface (may be larger); if None, same as surface
        self._display = display if display is not None else surface
        _active_screen = self
        self._fg_color = 15   # current foreground color index
        self._row = 1         # current text row (1-based)
        self._col = 1         # current text col (1-based)
        self._clip = None     # VIEW clipping rect (None = full screen)
        self._last_x = 0      # last LINE/PSET endpoint for continuation
        self._last_y = 0

        # No system font needed — we use the VGA bitmap font from vga_font.py

    # ── Color ─────────────────────────────────────────────────────────────

    def color(self, c: int) -> None:
        """Set foreground color (0-15)."""
        self._fg_color = c % 16

    def _rgb(self, c: int = -1):
        """Get RGB tuple for color index."""
        if c < 0:
            c = self._fg_color
        return VGA[c % 16]

    # ── Text ──────────────────────────────────────────────────────────────

    def locate(self, row: int, col: int) -> None:
        """Set text cursor position (1-based row, col)."""
        self._row = max(1, min(30, row))
        self._col = max(1, min(80, col))

    def print_text(self, text: str) -> None:
        """Print text at current cursor position using VGA bitmap font."""
        x = (self._col - 1) * CHAR_W
        y = (self._row - 1) * CHAR_H
        # Clear background behind text
        tw = len(text) * CHAR_W
        pygame.draw.rect(self.surface, VGA[0], (x, y, tw, CHAR_H))
        # Blit each character from the VGA bitmap font
        rgb = self._rgb()
        for ch in text:
            code = ord(ch)
            if 32 <= code <= 126:
                glyph = get_glyph(code, rgb)
                self.surface.blit(glyph, (x, y))
            x += CHAR_W
        self._col += len(text)

    # ── Drawing primitives ────────────────────────────────────────────────

    def line(self, x1: int, y1: int, x2: int, y2: int, c: int,
             style: str = "", pattern: int = 0xFFFF) -> None:
        """Draw line or box. style='B' for box, 'BF' for filled box."""
        rgb = self._rgb(c)
        if "BF" in style.upper():
            # Filled rectangle
            rx = min(x1, x2)
            ry = min(y1, y2)
            rw = abs(x2 - x1) + 1
            rh = abs(y2 - y1) + 1
            pygame.draw.rect(self.surface, rgb, (rx, ry, rw, rh))
        elif "B" in style.upper():
            # Rectangle outline
            rx = min(x1, x2)
            ry = min(y1, y2)
            rw = abs(x2 - x1) + 1
            rh = abs(y2 - y1) + 1
            pygame.draw.rect(self.surface, rgb, (rx, ry, rw, rh), 1)
        else:
            # Line
            if pattern != 0xFFFF:
                # Dashed line (simplified)
                self._dashed_line(x1, y1, x2, y2, rgb, pattern)
            else:
                pygame.draw.line(self.surface, rgb, (x1, y1), (x2, y2))
        # Track last endpoint for LINE -(x,y) continuation
        self._last_x = x2
        self._last_y = y2

    def _dashed_line(self, x1, y1, x2, y2, rgb, pattern):
        """Draw a styled line with a 16-bit pattern, pixel by pixel.

        Exact port of QBASIC LINE style: each bit in the 16-bit pattern
        controls one pixel along the line (bit 15 = first pixel, bit 0 =
        16th pixel, then repeats).  Consecutive 'on' pixels are batched
        into pygame.draw.line calls for performance.
        """
        import math
        dx = x2 - x1
        dy = y2 - y1
        dist = max(1, int(math.sqrt(dx * dx + dy * dy)))
        sx = dx / dist
        sy = dy / dist
        seg_start = None
        for i in range(dist + 1):
            bit = (pattern >> (15 - (i % 16))) & 1
            if bit:
                if seg_start is None:
                    seg_start = i
            else:
                if seg_start is not None:
                    px = int(x1 + seg_start * sx)
                    py = int(y1 + seg_start * sy)
                    ex = int(x1 + (i - 1) * sx)
                    ey = int(y1 + (i - 1) * sy)
                    pygame.draw.line(self.surface, rgb, (px, py), (ex, ey))
                    seg_start = None
        # flush last segment
        if seg_start is not None:
            px = int(x1 + seg_start * sx)
            py = int(y1 + seg_start * sy)
            ex = int(x1 + dist * sx)
            ey = int(y1 + dist * sy)
            pygame.draw.line(self.surface, rgb, (px, py), (ex, ey))

    def circle(self, x: int, y: int, r: int, c: int,
               fill: bool = False, aspect: float = 1.0) -> None:
        """Draw circle or ellipse. aspect < 1 squashes vertically (QBasic style).

        QBasic CIRCLE: aspect < 1 → rx = r, ry = r * aspect
                       aspect > 1 → rx = r / aspect, ry = r
        """
        rgb = self._rgb(c)
        if aspect == 1.0:
            if fill:
                pygame.draw.circle(self.surface, rgb, (x, y), r)
            else:
                pygame.draw.circle(self.surface, rgb, (x, y), r, 1)
        else:
            # Ellipse via bounding rect
            if aspect < 1.0:
                rx = r
                ry = max(1, int(r * aspect))
            else:
                rx = max(1, int(r / aspect))
                ry = r
            rect = (x - rx, y - ry, 2 * rx + 1, 2 * ry + 1)
            if fill:
                pygame.draw.ellipse(self.surface, rgb, rect)
            else:
                pygame.draw.ellipse(self.surface, rgb, rect, 1)
        # QBasic CIRCLE moves the graphics cursor to the center
        self._last_x = x
        self._last_y = y

    def polygon(self, points, c: int, fill: bool = False) -> None:
        """Draw a polygon. fill=True fills the interior (like PAINT)."""
        rgb = self._rgb(c)
        if fill:
            pygame.draw.polygon(self.surface, rgb, points)
        else:
            pygame.draw.polygon(self.surface, rgb, points, 1)

    def pset(self, x: int, y: int, c: int) -> None:
        """Set a single pixel."""
        if 0 <= x < 640 and 0 <= y < 480:
            self.surface.set_at((x, y), self._rgb(c))
        self._last_x = x
        self._last_y = y

    def line_to(self, x: int, y: int, c: int = -1,
                style: str = "", pattern: int = 0xFFFF) -> None:
        """LINE -(x, y) continuation: draw from last endpoint to (x,y)."""
        if c < 0:
            c = self._fg_color
        self.line(self._last_x, self._last_y, x, y, c, style, pattern)

    # ── DRAW command interpreter ──────────────────────────────────────────

    # Direction vectors: U D L R E F G H
    _DRAW_DIR = {
        'U': (0, -1), 'D': (0, 1), 'L': (-1, 0), 'R': (1, 0),
        'E': (1, -1), 'F': (1, 1), 'G': (-1, 1), 'H': (-1, -1),
    }

    def draw(self, draw_str: str) -> tuple[int, int]:
        """Execute a QBasic DRAW command string from the current cursor.

        Supports: C<n> (color), S<n> (scale), B (blind), N (no-update),
                  U/D/L/R/E/F/G/H <n> (direction with optional distance).

        Returns (x, y) — the final cursor position (for POINT(0), POINT(1)).
        """
        cx = self._last_x
        cy = self._last_y
        color_idx = self._fg_color
        scale = 4                     # default S4 = 1:1
        i = 0
        s = draw_str.upper()

        while i < len(s):
            ch = s[i]
            i += 1

            # ── Prefixes ──
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

            # ── Color ──
            if ch == 'C':
                num = ''
                while i < len(s) and s[i].isdigit():
                    num += s[i]
                    i += 1
                color_idx = int(num) % 16 if num else 0
                continue

            # ── Scale ──
            if ch == 'S':
                num = ''
                while i < len(s) and s[i].isdigit():
                    num += s[i]
                    i += 1
                scale = int(num) if num else 4
                continue

            # ── Direction ──
            if ch in self._DRAW_DIR:
                num = ''
                while i < len(s) and s[i].isdigit():
                    num += s[i]
                    i += 1
                dist = int(num) if num else 1

                dx, dy = self._DRAW_DIR[ch]
                # scale / 4 is the step multiplier
                nx = cx + int(dx * dist * scale / 4)
                ny = cy + int(dy * dist * scale / 4)

                if not blind:
                    pygame.draw.line(self.surface, VGA[color_idx],
                                     (cx, cy), (nx, ny))

                if not no_update:
                    cx, cy = nx, ny

            # Anything else (spaces, etc.) is silently skipped

        self._last_x = cx
        self._last_y = cy
        return (cx, cy)

    # ── Image operations (store/restore pixel rectangles) ──────────────

    def put_image(self, x: int, y: int, sprite) -> None:
        """Blit a stored surface at position."""
        if isinstance(sprite, pygame.Surface):
            self.surface.blit(sprite, (x, y))

    def get_image(self, x1: int, y1: int, x2: int, y2: int):
        """Capture a rectangle of pixels and return as a Surface."""
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
        return self.surface.subsurface((rx, ry, rw, rh)).copy()

    # ── View/Clipping ─────────────────────────────────────────────────────

    def view(self, x1: int = -1, y1: int = -1, x2: int = -1, y2: int = -1) -> None:
        """Set clipping rectangle (VIEW). No args = reset."""
        if x1 < 0:
            self._clip = None
            self.surface.set_clip(None)
        else:
            self._clip = (x1, y1, x2 - x1 + 1, y2 - y1 + 1)
            self.surface.set_clip(self._clip)

    def cls(self, mode: int = 0) -> None:
        """Clear screen. mode=0: all, mode=1: within current VIEW."""
        if mode == 1 and self._clip:
            self.surface.fill(VGA[0], self._clip)
        else:
            self.surface.fill(VGA[0])
            self._clip = None
            self.surface.set_clip(None)

    # ── Paint (flood fill) ─────────────────────────────────────────────────

    def paint(self, x: int, y: int, fill_c: int, border_c: int = -1) -> None:
        """PAINT (x,y), fill_c, border_c — scanline flood fill.

        Fills from seed point (x,y) with fill_c, stopping at any pixel
        whose color matches border_c.  If border_c is -1, uses fill_c
        as the border color (standard QB64 behavior).
        """
        fill_rgb = self._rgb(fill_c)
        border_rgb = self._rgb(border_c) if border_c >= 0 else fill_rgb

        w, h = self.surface.get_size()
        if x < 0 or x >= w or y < 0 or y >= h:
            return

        start_rgb = tuple(self.surface.get_at((x, y))[:3])
        if start_rgb == tuple(fill_rgb) or start_rgb == tuple(border_rgb):
            return

        # Scanline flood fill using a stack of (x, y) seed points
        def _blocked(px, py):
            if px < 0 or px >= w or py < 0 or py >= h:
                return True
            c = self.surface.get_at((px, py))[:3]
            return c == border_rgb or c == fill_rgb

        stack = [(x, y)]
        while stack:
            sx, sy = stack.pop()
            if _blocked(sx, sy):
                continue

            # Scan left to find span start
            lx = sx
            while lx > 0 and not _blocked(lx - 1, sy):
                lx -= 1
            # Scan right to find span end
            rx = sx
            while rx < w - 1 and not _blocked(rx + 1, sy):
                rx += 1

            # Fill the entire horizontal span
            pygame.draw.line(self.surface, fill_rgb, (lx, sy), (rx, sy))

            # Seed the rows above and below for any new spans
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

    def update(self) -> None:
        """Push frame to display.

        Nearest-neighbor-scales the internal 640x480 surface up to the
        display window, preserving every pixel edge (no bilinear blur).
        """
        if self._display is not self.surface:
            # pygame.transform.scale uses nearest-neighbor (no smoothing)
            pygame.transform.scale(self.surface, self._display.get_size(),
                                   self._display)
        pygame.display.flip()

    def fill_rect(self, x: int, y: int, w: int, h: int, c: int) -> None:
        """Fill a rectangle (convenience wrapper)."""
        pygame.draw.rect(self.surface, self._rgb(c), (x, y, w, h))
