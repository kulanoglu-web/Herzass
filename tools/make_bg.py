"""Erzeugt den Hintergrund img/bg.png: heller Blau-Tuerkis-Verlauf mit weichem Lichtfleck."""
import math
import os

from PIL import Image

W, H = 360, 800
img = Image.new("RGB", (W, H))
px = img.load()
top, bot = (34, 110, 190), (14, 40, 100)
for y in range(H):
    t = y / (H - 1.0)
    for x in range(W):
        dx, dy = (x - W * 0.5) / (W * 0.7), (y - H * 0.28) / (H * 0.5)
        glow = max(0.0, 1 - math.hypot(dx, dy)) ** 1.6
        r = top[0] + (bot[0] - top[0]) * t + 55 * glow
        g = top[1] + (bot[1] - top[1]) * t + 70 * glow
        b = top[2] + (bot[2] - top[2]) * t + 60 * glow
        px[x, y] = (min(255, int(r)), min(255, int(g)), min(255, int(b)))
os.makedirs("img", exist_ok=True)
img.save("img/bg.png", optimize=True)
print("img/bg.png", img.size)
