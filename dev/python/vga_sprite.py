"""vga_sprite.py - Load QB64 BSAVE sprites (SCREEN 12 planar format).

QB64 SCREEN 12 = 640x480, 16 colors, 4 bit planes.
BSAVE files have a 7-byte header, then raw INTEGER array data.

The GET/PUT array format for SCREEN 12 (DEFINT A-Z):
  Word 0 (2 bytes LE): width in bits (= pixel width; 1 bit/pixel/plane)
  Word 1 (2 bytes LE): height in pixels
  Then for each scan line:
    4 planes x ceil(width/8) bytes each
    Bits are MSB-first (bit 7 of each byte = leftmost pixel)
  Color index = plane0 + plane1*2 + plane2*4 + plane3*8
"""

import os
import struct
import pygame
from cws_screen_pygame import VGA

# Data files live in the QB64 game directory (two levels up from dev/python/)
_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..")


def _data_path(filename: str) -> str:
    """Resolve path to a data file, case-insensitive."""
    path = os.path.join(_DATA_DIR, filename)
    if os.path.exists(path):
        return path
    target = filename.upper()
    for f in os.listdir(_DATA_DIR):
        if f.upper() == target:
            return os.path.join(_DATA_DIR, f)
    return path


def load_vga_sprite(filename: str) -> pygame.Surface:
    """Load a QB64 BSAVE sprite file and return a pygame Surface.

    Args:
        filename: Name of the .VGA file (e.g. 'mtn.vga')

    Returns:
        pygame.Surface with the decoded sprite, pixel-exact VGA colors.
    """
    path = _data_path(filename)
    with open(path, "rb") as f:
        raw = f.read()

    # ── BSAVE header: 0xFD, segment(2), offset(2), length(2) ──
    if raw[0] != 0xFD:
        raise ValueError(f"{filename}: not a BSAVE file (missing 0xFD)")

    bsave_len = struct.unpack_from('<H', raw, 5)[0]
    payload = raw[7 : 7 + bsave_len]

    # ── Image header ──
    width_bits = struct.unpack_from('<H', payload, 0)[0]
    height     = struct.unpack_from('<H', payload, 2)[0]

    width = width_bits  # SCREEN 12: 1 bit per pixel per plane
    bytes_per_plane = (width + 7) // 8
    row_stride = bytes_per_plane * 4          # 4 planes per scan line

    # ── Decode into pixel array ──
    surf = pygame.Surface((width, height))
    pix = pygame.PixelArray(surf)             # fast pixel access

    offset = 4                                # past header
    for y in range(height):
        # Grab the 4 plane slices for this row
        p0 = payload[offset                         : offset + bytes_per_plane]
        p1 = payload[offset + bytes_per_plane       : offset + 2 * bytes_per_plane]
        p2 = payload[offset + 2 * bytes_per_plane   : offset + 3 * bytes_per_plane]
        p3 = payload[offset + 3 * bytes_per_plane   : offset + 4 * bytes_per_plane]
        offset += row_stride

        for x in range(width):
            bi = x >> 3                       # byte index
            mask = 0x80 >> (x & 7)            # MSB = leftmost pixel

            color_idx = 0
            if p0[bi] & mask: color_idx |= 1
            if p1[bi] & mask: color_idx |= 2
            if p2[bi] & mask: color_idx |= 4
            if p3[bi] & mask: color_idx |= 8

            pix[x, y] = surf.map_rgb(VGA[color_idx])

    del pix                                   # unlock surface
    return surf


def load_all_sprites(g) -> None:
    """Preload all VGA sprites and store as pygame Surfaces on GameState.

    Called once at startup after pygame.init() and SCREEN 12 are ready.
    Sets the following attributes on g:
        g.mtn_surface       - mountain sprite (mtn.vga)
        g.ncap_surface      - 13x13 capital city icon (from cwsicon.vga)
        g.face_surfaces     - dict {1..5: Surface} (face1..5.vga)
        g.fort_surfaces     - dict {0..2: Surface} (fort0..2.vga)
    """
    # ── MTN.VGA ──
    try:
        g.mtn_surface = load_vga_sprite("mtn.vga")
    except Exception as e:
        print(f"WARNING: mtn.vga: {e}")
        g.mtn_surface = None

    # ── CWSICON.VGA → Ncap (capital city marker) ──
    # Original: PUT (100,100), graphic, PSET
    #           GET (101,101)-(113,113), Ncap
    # Ncap = 13x13 sub-image starting at offset (1,1) within the sprite
    try:
        cwsicon = load_vga_sprite("cwsicon.vga")
        g.ncap_surface = cwsicon.subsurface((1, 1, 13, 13)).copy()
    except Exception as e:
        print(f"WARNING: cwsicon.vga: {e}")
        g.ncap_surface = None

    # ── FACE1-5.VGA (commander face sprites) ──
    g.face_surfaces = {}
    for i in range(1, 6):
        try:
            g.face_surfaces[i] = load_vga_sprite(f"face{i}.vga")
        except Exception as e:
            print(f"WARNING: face{i}.vga: {e}")

    # ── FORT0-2.VGA (fortification sprites in battle) ──
    g.fort_surfaces = {}
    for i in range(0, 3):
        try:
            g.fort_surfaces[i] = load_vga_sprite(f"fort{i}.vga")
        except Exception as e:
            print(f"WARNING: fort{i}.vga: {e}")
