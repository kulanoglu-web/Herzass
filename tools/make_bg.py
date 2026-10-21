"""Erzeugt den Hintergrund img/bg.png (dunkles Blau mit Vignette und feinem Raster)."""
import math
import os
import random

from PIL import Image

W, H = 360, 800
rng = random.Random(3)
img = Image.new("RGB", (W, H))
px = img.load()
for y in range(H):
    for x in range(W):
        dx, dy = (x - W / 2) / (W / 2), (y - H * 0.42) / (H * 0.6)
        d = min(1.0, math.hypot(dx, dy))
        k = (1 - d) ** 1.4
        r, g, b = 4 + 22 * k, 6 + 30 * k, 18 + 62 * k
        if (x + y) % 6 == 0:
            r, g, b = r * 1.25, g * 1.25, b * 1.25
        n = rng.random() * 3
        px[x, y] = (int(r + n), int(g + n), int(b + n))
os.makedirs("img", exist_ok=True)
img.save("img/bg.png", optimize=True)
print("img/bg.png", img.size)
