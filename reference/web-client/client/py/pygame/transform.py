"""pygame.transform replacement — minimal stubs."""

from pygame.surface import Surface


def scale(surface, size, dest_surface=None):
    """Nearest-neighbor scale."""
    nw, nh = int(size[0]), int(size[1])
    ow, oh = surface._w, surface._h

    if dest_surface is not None:
        result = dest_surface
    else:
        result = Surface((nw, nh), surface._flags)

    src = surface._data
    dst = result._data

    for dy in range(nh):
        sy = dy * oh // nh
        for dx in range(nw):
            sx = dx * ow // nw
            src_off = (sy * ow + sx) * 4
            dst_off = (dy * nw + dx) * 4
            dst[dst_off:dst_off + 4] = src[src_off:src_off + 4]

    return result


def flip(surface, xbool, ybool):
    """Flip horizontally and/or vertically."""
    w, h = surface._w, surface._h
    result = Surface((w, h), surface._flags)
    src = surface._data
    dst = result._data

    for y in range(h):
        for x in range(w):
            sx = (w - 1 - x) if xbool else x
            sy = (h - 1 - y) if ybool else y
            src_off = (sy * w + sx) * 4
            dst_off = (y * w + x) * 4
            dst[dst_off:dst_off + 4] = src[src_off:src_off + 4]

    return result


def rotate(surface, angle):
    """Stub — return copy (rotation not used in CWS)."""
    return surface.copy()
