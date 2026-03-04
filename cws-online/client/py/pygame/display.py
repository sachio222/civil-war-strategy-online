"""pygame.display replacement — stubs for web."""

from pygame.surface import Surface

_surface = None
_caption = ""


def init():
    pass


def quit():
    pass


def set_mode(size, flags=0):
    global _surface
    _surface = Surface(size)
    return _surface


def get_surface():
    return _surface


def set_caption(title):
    global _caption
    _caption = title


def flip():
    pass


def update(rects=None):
    pass


class _Info:
    def __init__(self):
        self.current_w = 1920
        self.current_h = 1080


def Info():
    return _Info()


def set_icon(surface):
    pass
