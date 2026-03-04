"""web_sprite.py — PNG sprite loading for the web (replaces vga_sprite.py).

Sprites are pre-decoded by worker.js at startup using OffscreenCanvas.
Raw RGBA pixel data is stored in Pyodide's virtual filesystem at:
  /sprites/{name}.meta  — 4 bytes: width(LE16), height(LE16)
  /sprites/{name}.rgba  — raw RGBA pixel bytes

This module just reads those files and wraps them in Surface objects.
"""

import os
import struct
from pygame.surface import Surface
from cws_screen_pygame import VGA


def load_vga_sprite(filename):
    """Load a pre-decoded sprite. filename like 'mtn.vga' or 'face1.vga'."""
    # Map filename to the base name used by worker.js
    name = filename.replace('.vga', '').replace('.VGA', '')

    meta_path = f"/sprites/{name}.meta"
    rgba_path = f"/sprites/{name}.rgba"

    if not os.path.exists(meta_path):
        print(f"Sprite not found: {meta_path}")
        return None

    with open(meta_path, 'rb') as f:
        meta = f.read(4)
    w = meta[0] | (meta[1] << 8)
    h = meta[2] | (meta[3] << 8)

    with open(rgba_path, 'rb') as f:
        pixels = bytearray(f.read())

    expected = w * h * 4
    if len(pixels) != expected:
        print(f"Sprite {name}: expected {expected} bytes, got {len(pixels)}")
        return None

    surf = Surface._from_data(w, h, pixels)
    return surf


def load_all_sprites(g):
    """Load all sprites and store on GameState."""
    print("Loading sprites from pre-decoded files...")

    # MTN
    try:
        g.mtn_surface = load_vga_sprite("mtn.vga")
        if g.mtn_surface:
            print(f"  mtn: {g.mtn_surface.get_size()}")
    except Exception as e:
        print(f"  WARNING: mtn: {e}")
        g.mtn_surface = None

    # CWSICON → Ncap (capital city marker, 13x13 sub-image at offset 1,1)
    try:
        cwsicon = load_vga_sprite("cwsicon.vga")
        if cwsicon:
            g.ncap_surface = cwsicon.subsurface((1, 1, 13, 13)).copy()
            print(f"  cwsicon: {cwsicon.get_size()} -> ncap: 13x13")
        else:
            g.ncap_surface = None
    except Exception as e:
        print(f"  WARNING: cwsicon: {e}")
        g.ncap_surface = None

    # FACE1-5
    g.face_surfaces = {}
    for i in range(1, 6):
        try:
            surf = load_vga_sprite(f"face{i}.vga")
            if surf:
                g.face_surfaces[i] = surf
                print(f"  face{i}: {surf.get_size()}")
        except Exception as e:
            print(f"  WARNING: face{i}: {e}")

    # FORT0-2
    g.fort_surfaces = {}
    for i in range(0, 3):
        try:
            surf = load_vga_sprite(f"fort{i}.vga")
            if surf:
                g.fort_surfaces[i] = surf
                print(f"  fort{i}: {surf.get_size()}")
        except Exception as e:
            print(f"  WARNING: fort{i}: {e}")

    print("Sprites loaded.")
