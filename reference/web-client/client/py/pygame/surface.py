"""pygame.Surface replacement backed by a bytearray (RGBA pixel data)."""


class Surface:
    """Software surface backed by an RGBA bytearray (w * h * 4 bytes).

    Implements the subset of pygame.Surface used by the CWS desktop code:
    set_at, get_at, fill, blit, copy, subsurface, get_size, get_rect,
    get_width, get_height, map_rgb, get_flags, set_clip, get_clip.
    """

    __slots__ = ('_w', '_h', '_data', '_flags', '_clip')

    def __init__(self, size, flags=0):
        if isinstance(size, (list, tuple)):
            self._w = int(size[0])
            self._h = int(size[1])
        else:
            self._w = int(size)
            self._h = 0
        self._flags = flags
        self._data = bytearray(self._w * self._h * 4)
        self._clip = None

    @classmethod
    def _from_data(cls, w, h, data, flags=0):
        """Internal: create Surface from existing bytearray."""
        s = object.__new__(cls)
        s._w = w
        s._h = h
        s._data = data
        s._flags = flags
        s._clip = None
        return s

    def get_size(self):
        return (self._w, self._h)

    def get_width(self):
        return self._w

    def get_height(self):
        return self._h

    def get_rect(self, **kwargs):
        r = _Rect(0, 0, self._w, self._h)
        for k, v in kwargs.items():
            setattr(r, k, v)
        return r

    def get_flags(self):
        return self._flags

    def set_clip(self, rect):
        if rect is None:
            self._clip = None
        elif isinstance(rect, (list, tuple)):
            self._clip = tuple(rect)
        else:
            self._clip = (rect.x, rect.y, rect.width, rect.height)

    def get_clip(self):
        if self._clip:
            return _Rect(*self._clip)
        return _Rect(0, 0, self._w, self._h)

    def fill(self, color, rect=None, special_flags=0):
        """Fill with color. Supports BLEND_RGBA_MULT (flag=2) for font tinting."""
        r, g, b = _unpack_rgb(color)
        a = color[3] if len(color) > 3 else 255

        if rect is not None:
            if isinstance(rect, _Rect):
                rx, ry, rw, rh = rect.x, rect.y, rect.width, rect.height
            else:
                rx, ry, rw, rh = rect[0], rect[1], rect[2], rect[3]
        else:
            rx, ry, rw, rh = 0, 0, self._w, self._h

        # Clamp
        if rx < 0:
            rw += rx; rx = 0
        if ry < 0:
            rh += ry; ry = 0
        if rx + rw > self._w:
            rw = self._w - rx
        if ry + rh > self._h:
            rh = self._h - ry
        if rw <= 0 or rh <= 0:
            return

        data = self._data
        w = self._w

        if special_flags == 2:  # BLEND_RGBA_MULT
            for y in range(ry, ry + rh):
                base = (y * w + rx) * 4
                for x in range(rw):
                    off = base + x * 4
                    data[off]     = (data[off]     * r) >> 8
                    data[off + 1] = (data[off + 1] * g) >> 8
                    data[off + 2] = (data[off + 2] * b) >> 8
                    data[off + 3] = (data[off + 3] * a) >> 8
        else:
            # Normal fill
            row_bytes = bytearray(rw * 4)
            for x in range(rw):
                off = x * 4
                row_bytes[off] = r
                row_bytes[off + 1] = g
                row_bytes[off + 2] = b
                row_bytes[off + 3] = a
            for y in range(ry, ry + rh):
                start = (y * w + rx) * 4
                data[start:start + rw * 4] = row_bytes

    def set_at(self, pos, color):
        x, y = int(pos[0]), int(pos[1])
        if 0 <= x < self._w and 0 <= y < self._h:
            off = (y * self._w + x) * 4
            r, g, b = _unpack_rgb(color)
            a = color[3] if len(color) > 3 else 255
            self._data[off] = r
            self._data[off + 1] = g
            self._data[off + 2] = b
            self._data[off + 3] = a

    def get_at(self, pos):
        x, y = int(pos[0]), int(pos[1])
        if 0 <= x < self._w and 0 <= y < self._h:
            off = (y * self._w + x) * 4
            return (self._data[off], self._data[off+1],
                    self._data[off+2], self._data[off+3])
        return (0, 0, 0, 0)

    def blit(self, source, dest, area=None):
        """Copy pixels from source Surface onto this Surface."""
        if isinstance(dest, (list, tuple)):
            dx, dy = int(dest[0]), int(dest[1])
        else:
            dx, dy = int(dest.x), int(dest.y)

        sw, sh = source._w, source._h
        sx, sy = 0, 0

        if area is not None:
            if isinstance(area, _Rect):
                sx, sy = area.x, area.y
                sw, sh = area.width, area.height
            else:
                sx = int(area[0])
                sy = int(area[1])
                sw = int(area[2])
                sh = int(area[3])

        # Clamp source area
        if sx < 0:
            dx -= sx; sw += sx; sx = 0
        if sy < 0:
            dy -= sy; sh += sy; sy = 0
        if sx + sw > source._w:
            sw = source._w - sx
        if sy + sh > source._h:
            sh = source._h - sy

        # Clamp dest
        if dx < 0:
            sx -= dx; sw += dx; dx = 0
        if dy < 0:
            sy -= dy; sh += dy; dy = 0
        if dx + sw > self._w:
            sw = self._w - dx
        if dy + sh > self._h:
            sh = self._h - dy

        if sw <= 0 or sh <= 0:
            return

        src_data = source._data
        dst_data = self._data
        src_w = source._w
        dst_w = self._w

        src_has_alpha = bool(source._flags & 1)  # SRCALPHA

        for row in range(sh):
            src_off = ((sy + row) * src_w + sx) * 4
            dst_off = ((dy + row) * dst_w + dx) * 4

            if src_has_alpha:
                # Alpha blending
                for col in range(sw):
                    so = src_off + col * 4
                    do = dst_off + col * 4
                    sa = src_data[so + 3]
                    if sa == 0:
                        continue
                    if sa == 255:
                        dst_data[do:do+4] = src_data[so:so+4]
                    else:
                        inv = 255 - sa
                        dst_data[do]     = (src_data[so]     * sa + dst_data[do]     * inv) >> 8
                        dst_data[do + 1] = (src_data[so + 1] * sa + dst_data[do + 1] * inv) >> 8
                        dst_data[do + 2] = (src_data[so + 2] * sa + dst_data[do + 2] * inv) >> 8
                        dst_data[do + 3] = max(dst_data[do + 3], sa)
            else:
                # Opaque copy (fast path)
                src_start = src_off
                dst_start = dst_off
                nbytes = sw * 4
                dst_data[dst_start:dst_start + nbytes] = src_data[src_start:src_start + nbytes]

    def copy(self):
        return Surface._from_data(self._w, self._h,
                                  bytearray(self._data), self._flags)

    def subsurface(self, rect):
        """Return a copy of a region (not a view, for simplicity)."""
        if isinstance(rect, _Rect):
            rx, ry, rw, rh = rect.x, rect.y, rect.width, rect.height
        else:
            rx, ry, rw, rh = int(rect[0]), int(rect[1]), int(rect[2]), int(rect[3])

        new_data = bytearray(rw * rh * 4)
        for row in range(rh):
            src_off = ((ry + row) * self._w + rx) * 4
            dst_off = row * rw * 4
            new_data[dst_off:dst_off + rw * 4] = self._data[src_off:src_off + rw * 4]
        return Surface._from_data(rw, rh, new_data, self._flags)

    def map_rgb(self, color):
        """RGB tuple → packed integer (for PixelArray compatibility)."""
        r, g, b = _unpack_rgb(color)
        return (r << 16) | (g << 8) | b


class PixelArray:
    """Wrapper for pixel[x, y] = color access pattern (used by vga_sprite.py)."""

    def __init__(self, surface):
        self._surface = surface

    def __setitem__(self, key, value):
        x, y = key
        if isinstance(value, int):
            # Packed RGB value from map_rgb
            r = (value >> 16) & 0xFF
            g = (value >> 8) & 0xFF
            b = value & 0xFF
            self._surface.set_at((x, y), (r, g, b, 255))
        else:
            self._surface.set_at((x, y), value)

    def __getitem__(self, key):
        x, y = key
        return self._surface.get_at((x, y))

    def __del__(self):
        pass  # No-op unlock


class _Rect:
    """Minimal Rect class."""

    __slots__ = ('x', 'y', 'width', 'height')

    def __init__(self, x=0, y=0, w=0, h=0):
        self.x = x
        self.y = y
        self.width = w
        self.height = h

    def __iter__(self):
        return iter((self.x, self.y, self.width, self.height))

    def __getitem__(self, i):
        return (self.x, self.y, self.width, self.height)[i]

    def __len__(self):
        return 4

    @property
    def w(self):
        return self.width

    @property
    def h(self):
        return self.height

    @property
    def topleft(self):
        return (self.x, self.y)

    @property
    def size(self):
        return (self.width, self.height)


def _unpack_rgb(color):
    """Extract (r, g, b) from a color that may be tuple, list, or have extra alpha."""
    if isinstance(color, int):
        return ((color >> 16) & 0xFF, (color >> 8) & 0xFF, color & 0xFF)
    return (int(color[0]), int(color[1]), int(color[2]))
