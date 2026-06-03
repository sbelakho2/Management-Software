#!/usr/bin/env python3
"""Generate minimal placeholder RGBA icons for the Sensei Tauri app.

Produces:
  - 32x32.png
  - 128x128.png
  - 128x128@2x.png  (256x256)
  - icon.icns        (placeholder – actually a PNG renamed; replaced by real .icns later)
  - icon.ico         (placeholder – actually a PNG renamed; replaced by real .ico later)

Tauri requires RGBA (color type 6) PNGs.
"""

import struct
import zlib
import os

def create_rgba_png(width: int, height: int, r: int = 66, g: int = 133, b: int = 244, a: int = 255) -> bytes:
    """Create a minimal solid-colour RGBA PNG."""
    # PNG signature
    signature = b'\x89PNG\r\n\x1a\n'

    # IHDR chunk – color type 6 = RGBA
    ihdr_data = struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0)
    ihdr_crc = zlib.crc32(b'IHDR' + ihdr_data) & 0xffffffff
    ihdr = struct.pack('>I', 13) + b'IHDR' + ihdr_data + struct.pack('>I', ihdr_crc)

    # IDAT chunk – raw pixel data (RGBA, unfiltered)
    raw = b''
    for _ in range(height):
        raw += b'\x00'  # filter byte (None)
        for _ in range(width):
            raw += struct.pack('BBBB', r, g, b, a)

    compressed = zlib.compress(raw)
    idat_crc = zlib.crc32(b'IDAT' + compressed) & 0xffffffff
    idat = struct.pack('>I', len(compressed)) + b'IDAT' + compressed + struct.pack('>I', idat_crc)

    # IEND chunk
    iend_crc = zlib.crc32(b'IEND') & 0xffffffff
    iend = struct.pack('>I', 0) + b'IEND' + struct.pack('>I', iend_crc)

    return signature + ihdr + idat + iend


if __name__ == '__main__':
    out_dir = os.path.dirname(os.path.abspath(__file__))

    # Brand blue: #4285F4 -> (66, 133, 244) fully opaque
    png_32 = create_rgba_png(32, 32)
    png_128 = create_rgba_png(128, 128)
    png_256 = create_rgba_png(256, 256)

    with open(os.path.join(out_dir, '32x32.png'), 'wb') as f:
        f.write(png_32)
    print('Created  32x32.png (RGBA)')

    with open(os.path.join(out_dir, '128x128.png'), 'wb') as f:
        f.write(png_128)
    print('Created 128x128.png (RGBA)')

    with open(os.path.join(out_dir, '128x128@2x.png'), 'wb') as f:
        f.write(png_256)
    print('Created 128x128@2x.png (RGBA)')

    # Placeholder for .icns – on macOS this should be an Apple Icon Image.
    # We write a valid RGBA PNG as a stand-in.
    with open(os.path.join(out_dir, 'icon.icns'), 'wb') as f:
        f.write(png_256)
    print('Created icon.icns (placeholder – replace with real .icns)')

    # Placeholder for .ico – we write a valid RGBA PNG as a stand-in.
    with open(os.path.join(out_dir, 'icon.ico'), 'wb') as f:
        f.write(png_256)
    print('Created icon.ico (placeholder – replace with real .ico)')

    print('\nAll icons generated successfully.')
