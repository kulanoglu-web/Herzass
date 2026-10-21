"""Rendert die 32 Spielkarten (7 bis As) aus SVG-Vorlagen zu PNG.
Vorlagen: Byron Knoll, "vector-playing-cards" (gemeinfrei), gesammelt in
github.com/notpeter/vector-playing-cards (Public Domain / WTFPL).
Aufruf: python tools/make_cards.py <Ordner mit SVGs> [Breite in px]"""
import os
import re
import sys

import resvg_py

src = sys.argv[1]
width = int(sys.argv[2]) if len(sys.argv) > 2 else 240
os.makedirs("cards", exist_ok=True)
for rank in ["7", "8", "9", "10", "J", "Q", "K", "A"]:
    for suit in "HDSC":
        name = rank + suit
        svg = open(os.path.join(src, name + ".svg"), encoding="utf-8").read()
        svg = re.sub(r'(width|height)="([0-9.]+)pt"', r'\1="\2"', svg)
        png = resvg_py.svg_to_bytes(svg_string=svg, width=width)
        with open(os.path.join("cards", name + ".png"), "wb") as f:
            f.write(bytes(png))
print("fertig", len(os.listdir("cards")))
