"""pygame.image replacement — minimal stubs."""

from pygame.surface import Surface


def load(filename):
    """Stub — sprite loading is handled by web_sprite.py."""
    return Surface((1, 1))


def save(surface, filename):
    """Stub — not needed in web."""
    pass
