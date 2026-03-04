"""pygame.font replacement — minimal stubs.

The CWS game uses vga_font.py (bitmap font), not pygame.font.
This just provides stubs so `pygame.font.init()` doesn't error.
"""


def init():
    pass


def quit():
    pass


def get_init():
    return True


class SysFont:
    """Stub system font — not actually used by the game."""

    def __init__(self, name=None, size=16, bold=False, italic=False):
        self._size = size

    def render(self, text, antialias, color, background=None):
        from pygame.surface import Surface
        w = len(text) * (self._size // 2)
        h = self._size
        return Surface((max(1, w), max(1, h)))

    def get_height(self):
        return self._size

    def get_linesize(self):
        return self._size


class Font(SysFont):
    pass
