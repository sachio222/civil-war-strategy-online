"""convert_vga_to_png.py -- Convert QB64 BSAVE .VGA sprites to PNG files.

Reads planar 4-bit BSAVE sprites and writes PNG images using Pillow.
Output goes to reference/web-client/client/assets/sprites/.

Usage:
    python convert_vga_to_png.py
"""

import struct
import os
from PIL import Image

# VGA 16-color palette (canonical copy in src/cws_screen_pygame.py VGA)
VGA_RGB = [
    (0x00, 0x00, 0x00), (0x00, 0x00, 0xAA), (0x00, 0xAA, 0x00), (0x00, 0xAA, 0xAA),
    (0xAA, 0x00, 0x00), (0xAA, 0x00, 0xAA), (0xAA, 0x55, 0x00), (0xAA, 0xAA, 0xAA),
    (0x55, 0x55, 0x55), (0x55, 0x55, 0xFF), (0x55, 0xFF, 0x55), (0x55, 0xFF, 0xFF),
    (0xFF, 0x55, 0x55), (0xFF, 0x55, 0xFF), (0xFF, 0xFF, 0x55), (0xFF, 0xFF, 0xFF),
]

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
OUT_DIR = os.path.join(PROJECT_ROOT, "reference", "web-client", "client", "assets", "sprites")


def decode_vga_sprite(path):
    """Decode a QB64 BSAVE planar sprite file into a PIL Image.

    BSAVE format:
      Byte 0: 0xFD marker
      Bytes 1-2: segment (LE, ignored)
      Bytes 3-4: offset (LE, ignored)
      Bytes 5-6: data length (LE)
      Then payload:
        Word 0 (2 bytes LE): width in bits (= pixel width)
        Word 1 (2 bytes LE): height in pixels
        Then for each scanline: 4 planes x ceil(width/8) bytes
        Color index = plane0_bit + plane1_bit*2 + plane2_bit*4 + plane3_bit*8
    """
    with open(path, "rb") as f:
        raw = f.read()

    if raw[0] != 0xFD:
        raise ValueError(f"Not a BSAVE file: {path}")

    bsave_len = struct.unpack_from('<H', raw, 5)[0]
    payload = raw[7:7 + bsave_len]

    width = struct.unpack_from('<H', payload, 0)[0]
    height = struct.unpack_from('<H', payload, 2)[0]
    bytes_per_plane = (width + 7) // 8

    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    pixels = img.load()

    offset = 4
    for y in range(height):
        p0 = payload[offset:offset + bytes_per_plane]
        p1 = payload[offset + bytes_per_plane:offset + 2 * bytes_per_plane]
        p2 = payload[offset + 2 * bytes_per_plane:offset + 3 * bytes_per_plane]
        p3 = payload[offset + 3 * bytes_per_plane:offset + 4 * bytes_per_plane]
        offset += bytes_per_plane * 4

        for x in range(width):
            bi = x >> 3
            mask = 0x80 >> (x & 7)

            color_idx = 0
            if p0[bi] & mask:
                color_idx |= 1
            if p1[bi] & mask:
                color_idx |= 2
            if p2[bi] & mask:
                color_idx |= 4
            if p3[bi] & mask:
                color_idx |= 8

            r, g, b = VGA_RGB[color_idx]
            # Color 0 (black) = transparent for sprites
            a = 0 if color_idx == 0 else 255
            pixels[x, y] = (r, g, b, a)

    return img


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    sprites = ["MTN", "FORT0", "FORT1", "FORT2", "CWSICON"]

    for name in sprites:
        vga_path = os.path.join(DATA_DIR, f"{name}.VGA")
        if not os.path.exists(vga_path):
            print(f"SKIP: {vga_path} not found")
            continue

        img = decode_vga_sprite(vga_path)
        out_name = name.lower() + ".png"
        out_path = os.path.join(OUT_DIR, out_name)
        img.save(out_path, "PNG")
        print(f"OK: {name}.VGA ({img.width}x{img.height}) -> {out_name}")

    # Also convert FACE sprites if present (used by desktop, may be useful later)
    for i in range(1, 6):
        vga_path = os.path.join(DATA_DIR, f"FACE{i}.VGA")
        if os.path.exists(vga_path):
            img = decode_vga_sprite(vga_path)
            out_name = f"face{i}.png"
            out_path = os.path.join(OUT_DIR, out_name)
            img.save(out_path, "PNG")
            print(f"OK: FACE{i}.VGA ({img.width}x{img.height}) -> {out_name}")


if __name__ == "__main__":
    main()
