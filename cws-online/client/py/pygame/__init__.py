"""pygame shim package — drop-in replacement for running CWS in Pyodide.

Exports all constants, types, and submodules that the desktop CWS code uses.
"""

# ── Submodules ───────────────────────────────────────────────────────────
from pygame import event
from pygame import time_mod as time
from pygame import mixer
from pygame import display
from pygame import draw
from pygame import transform
from pygame import font
from pygame import image

# ── Surface and PixelArray ───────────────────────────────────────────────
from pygame.surface import Surface, PixelArray

# ── Event types ──────────────────────────────────────────────────────────
QUIT = 256
VIDEORESIZE = 257
KEYDOWN = 258

# ── Key codes ────────────────────────────────────────────────────────────
K_RETURN = 13
K_ESCAPE = 27
K_UP = 273
K_DOWN = 274
K_LEFT = 275
K_RIGHT = 276
K_HOME = 278
K_END = 279
K_PAGEUP = 280
K_PAGEDOWN = 281
K_BACKSPACE = 8
K_SPACE = 32
K_F1 = 282
K_F3 = 284
K_F7 = 288
K_F8 = 289
K_t = 116

# ── Surface flags ────────────────────────────────────────────────────────
SRCALPHA = 1
BLEND_RGBA_MULT = 2
RESIZABLE = 0

# ── Module-level functions ───────────────────────────────────────────────

def init():
    """No-op — everything is initialized on demand."""
    pass

def quit():
    """No-op."""
    pass

# ── Error class ──────────────────────────────────────────────────────────

class error(Exception):
    pass
