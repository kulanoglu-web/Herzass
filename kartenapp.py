"""Pokerherz - Walzen-Kartenspiel mit Halten, Ziehung und Risiko "Null oder mehr".

Eigenes Spiel.  Kartenbilder: Byron Knoll (gemeinfrei).  Klaenge selbst erzeugt.
Nur Spielgeld, kein Echtgeld.  Oberflaeche: Kivy (Desktop und Android-APK).
"""
import json
import math
import os
import random

from kivy.animation import Animation
from kivy.app import App
from kivy.clock import Clock
from kivy.core.audio import SoundLoader
from kivy.core.image import Image as CoreImage
from kivy.core.text import Label as CoreLabel
from kivy.core.window import Window
from kivy.graphics.texture import Texture
from kivy.graphics import (Color, Ellipse, Line, Quad, Rectangle, RoundedRectangle,
                           Triangle)
from kivy.metrics import dp, sp
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.widget import Widget

from logic import LADDER, PAYTABLE, RANKS, SUITS, Game

HERE = os.path.dirname(os.path.abspath(__file__))
BG = (0.05, 0.05, 0.07, 1)
CREAM = (0.94, 0.83, 0.64, 1)
GOLD = (1.0, 0.80, 0.24, 1)
NEON = GOLD
RED = (0.92, 0.06, 0.13, 1)
INK = (0.08, 0.08, 0.10, 1)

Window.clearcolor = BG

RANK_FILE = {7: "7", 8: "8", 9: "9", 10: "10", 11: "J", 12: "Q", 13: "K", 14: "A"}
SUIT_FILE = {0: "H", 1: "D", 2: "S", 3: "C"}
_textures = {}


def card_texture(card):
    """Texture der Kartenbild-Datei (gecacht); None, wenn sie nicht geladen werden kann."""
    key = RANK_FILE[card[0]] + SUIT_FILE[card[1]]
    if key not in _textures:
        try:
            _textures[key] = CoreImage(os.path.join(HERE, "cards", key + ".png")).texture
        except Exception:
            _textures[key] = None
    return _textures[key]


def image_texture(name):
    key = "img:" + name
    if key not in _textures:
        try:
            _textures[key] = CoreImage(os.path.join(HERE, "img", name)).texture
        except Exception:
            _textures[key] = None
    return _textures[key]


# ---------------------------------------------------------------- Helfer ----
_metal = {}


def metal_texture(c, k=1.0):
    """Senkrechter Metall-Verlauf (heller Rand oben, dunkle Mitte, Glanzband, dunkler Boden)."""
    key = (tuple(round(v, 2) for v in c[:3]), round(k, 2))
    if key not in _metal:
        prof = [1.45, 1.30, 1.05, 0.80, 0.62, 0.52, 0.64, 0.90, 1.12, 0.88, 0.66, 0.55]
        buf = bytearray()
        for f in prof:
            for ch in c[:3]:
                buf.append(max(0, min(255, int(ch * f * k * 255))))
            buf.append(255)
        tex = Texture.create(size=(1, len(prof)), colorfmt="rgba")
        tex.blit_buffer(bytes(buf), colorfmt="rgba", bufferfmt="ubyte")
        tex.mag_filter = "linear"
        tex.min_filter = "linear"
        _metal[key] = tex
    return _metal[key]

def text_texture(text, size, color, bold=True):
    lab = CoreLabel(text=text, font_size=size, bold=bold, color=color)
    lab.refresh()
    return lab.texture


def draw_suit(suit, cx, cy, s):
    """Zeichnet ein Farbsymbol (0 Herz, 1 Karo, 2 Pik, 3 Kreuz) um (cx, cy), Groesse s."""
    if suit == 0:
        Ellipse(pos=(cx - s * 0.52, cy - s * 0.02), size=(s * 0.55, s * 0.55))
        Ellipse(pos=(cx - s * 0.03, cy - s * 0.02), size=(s * 0.55, s * 0.55))
        Triangle(points=[cx - s * 0.50, cy + s * 0.18, cx + s * 0.50, cy + s * 0.18,
                         cx, cy - s * 0.55])
    elif suit == 1:
        Quad(points=[cx, cy + s * 0.58, cx + s * 0.40, cy, cx, cy - s * 0.58,
                     cx - s * 0.40, cy])
    elif suit == 2:
        Ellipse(pos=(cx - s * 0.52, cy - s * 0.30), size=(s * 0.55, s * 0.55))
        Ellipse(pos=(cx - s * 0.03, cy - s * 0.30), size=(s * 0.55, s * 0.55))
        Triangle(points=[cx - s * 0.50, cy - s * 0.04, cx + s * 0.50, cy - s * 0.04,
                         cx, cy + s * 0.60])
        Triangle(points=[cx, cy - s * 0.1, cx - s * 0.18, cy - s * 0.58,
                         cx + s * 0.18, cy - s * 0.58])
    else:
        r = s * 0.30
        Ellipse(pos=(cx - r, cy + s * 0.04), size=(2 * r, 2 * r))
        Ellipse(pos=(cx - r * 1.55, cy - s * 0.32), size=(2 * r, 2 * r))
        Ellipse(pos=(cx + r * 0.55, cy - s * 0.32), size=(2 * r, 2 * r))
        Triangle(points=[cx, cy - s * 0.05, cx - s * 0.16, cy - s * 0.58,
                         cx + s * 0.16, cy - s * 0.58])


class Sfx:
    """Spielt die mitgelieferten WAV-Effekte; faellt still aus, wenn kein Ton geht."""

    def __init__(self):
        self.base = os.path.join(HERE, "sounds")
        self.sounds = {}
        self.on = True

    def play(self, name, volume=1.0, loop=False):
        if not self.on:
            return
        try:
            snd = self.sounds.get(name)
            if snd is None:
                snd = SoundLoader.load(os.path.join(self.base, name + ".wav"))
                self.sounds[name] = snd
            if snd:
                snd.volume = max(0.0, min(1.0, volume))
                snd.loop = loop
                snd.stop()
                snd.play()
        except Exception:
            pass

    def stop(self, name):
        try:
            if self.sounds.get(name):
                self.sounds[name].stop()
        except Exception:
            pass


# ----------------------------------------------------------- LED-Anzeige ----
SEGMENTS = {"0": "abcdef", "1": "bc", "2": "abdeg", "3": "abcdg", "4": "bcfg",
            "5": "acdfg", "6": "acdefg", "7": "abc", "8": "abcdefg", "9": "abcdfg",
            "-": "g"}


class LedDisplay(Widget):
    """Rote Leuchtanzeige mit weichem Glimmen (keine Segmentgeister)."""

    def __init__(self, digits=5, **kw):
        super().__init__(**kw)
        self.digits = digits
        self.value = ""
        self.bind(pos=self.redraw, size=self.redraw)

    def set(self, text):
        text = str(text)
        if text != self.value:
            self.value = text
            self.redraw()

    def redraw(self, *_):
        self.canvas.clear()
        x, y = self.pos
        w, h = self.size
        with self.canvas:
            Color(1, 1, 1, 1)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(7)],
                             texture=metal_texture(GOLD, 1.0))
            Color(0.05, 0.0, 0.0, 1)
            RoundedRectangle(pos=(x + dp(2.5), y + dp(2.5)), size=(w - dp(5), h - dp(5)),
                             radius=[dp(5)])
            Color(1, 1, 1, 0.07)
            RoundedRectangle(pos=(x + dp(2), y + h * 0.55), size=(w - dp(4), h * 0.42),
                             radius=[dp(5)])
            if self.value:
                size = h * 0.70
                tex = text_texture(self.value, size, (1.0, 0.22, 0.12, 1))
                k = min(1.0, (w - dp(14)) / float(tex.width))
                tw, th = tex.width * k, tex.height * k
                px, py = x + w - dp(8) - tw, y + (h - th) / 2
                for grow, alpha in ((1.18, 0.10), (1.09, 0.18)):
                    Color(1.0, 0.1, 0.05, alpha)
                    Rectangle(texture=tex, size=(tw * grow, th * grow),
                              pos=(px - tw * (grow - 1) / 2, py - th * (grow - 1) / 2))
                Color(1, 1, 1, 1)
                Rectangle(texture=tex, size=(tw, th), pos=(px, py))


# ---------------------------------------------------------------- Karten ----
class CardWidget(Widget):
    """Eine Walze: zeigt ein Kartenbild oder die Rueckseite."""

    def __init__(self, **kw):
        super().__init__(**kw)
        self.card = None
        self.held = False
        self.spinning = False
        self.blur = None
        self.on_tap = None
        self.bind(pos=self.redraw, size=self.redraw)

    def on_touch_down(self, touch):
        if self.on_tap and self.collide_point(*touch.pos):
            self.on_tap()
            return True
        return super().on_touch_down(touch)

    def set(self, card, held=False, spinning=False):
        self.card, self.held, self.spinning = card, held, spinning
        self.redraw()

    def redraw(self, *_):
        self.canvas.clear()
        card = self.blur if self.spinning else self.card
        ratio = 240.0 / 350.0
        cw = min(self.width, self.height * ratio)
        ch = cw / ratio
        x = self.x + (self.width - cw) / 2
        y = self.y + (self.height - ch) / 2
        with self.canvas:
            if self.held:
                Color(1, 0.85, 0.25, 0.30)
                RoundedRectangle(pos=(x - dp(6), y - dp(6)), size=(cw + dp(12), ch + dp(12)),
                                 radius=[dp(12)])
                Color(*GOLD)
                RoundedRectangle(pos=(x - dp(2.5), y - dp(2.5)), size=(cw + dp(5), ch + dp(5)),
                                 radius=[dp(8)])
            else:
                Color(0, 0, 0, 0.55)
                RoundedRectangle(pos=(x - dp(1.5), y - dp(2.5)), size=(cw + dp(3), ch + dp(3)),
                                 radius=[dp(7)])
            tex = card_texture(card) if card else None
            if card is None:
                Color(0.80, 0.20, 0.34, 1)
                RoundedRectangle(pos=(x, y), size=(cw, ch), radius=[dp(6)])
                Color(*GOLD)
                Line(rounded_rectangle=(x + dp(4), y + dp(4), cw - dp(8), ch - dp(8), dp(4)),
                     width=dp(1.2))
                draw_suit(0, x + cw / 2, y + ch / 2, cw * 0.45)
            elif tex is not None:
                Color(1, 1, 1, 1)
                Rectangle(texture=tex, pos=(x, y), size=(cw, ch))
            else:
                Color(0.98, 0.97, 0.92, 1)
                RoundedRectangle(pos=(x, y), size=(cw, ch), radius=[dp(6)])
                Color(*(RED if card[1] < 2 else INK))
                draw_suit(card[1], x + cw / 2, y + ch / 2, cw * 0.6)


# ---------------------------------------------------------- Herz-Leiter ----
class HeartCell(Widget):
    def __init__(self, label, **kw):
        super().__init__(**kw)
        self.label = label
        self.state = "off"
        self.glow = False
        self.bind(pos=self.redraw, size=self.redraw)

    def set(self, state, glow=False):
        if (state, glow) != (self.state, self.glow):
            self.state, self.glow = state, glow
            self.redraw()

    def redraw(self, *_):
        self.canvas.clear()
        x, y = self.pos
        w, h = self.size
        s = min(w / 1.12, h / 1.15)
        cx, cy = x + w / 2, y + h / 2 + h * 0.06
        with self.canvas:
            if self.state == "active" and self.glow:
                Color(1, 0.85, 0.2, 0.40)
                draw_suit(0, cx, cy, s * 1.4)
            Color(0.35, 0.22, 0.02, 1)
            draw_suit(0, cx, cy - dp(1.5), s * 1.05)
            Color(*GOLD)                               # Goldrand
            draw_suit(0, cx, cy, s)
            if self.state == "active":
                Color(1.0, 0.95, 0.55, 1) if self.glow else Color(1.0, 0.55, 0.12, 1)
                tcol = INK
            elif self.state == "passed":
                Color(1.0, 0.35, 0.35, 1)
                tcol = (1, 1, 1, 1)
            else:
                Color(0.92, 0.06, 0.13, 1)
                tcol = (1, 1, 1, 1)
            draw_suit(0, cx, cy, s * 0.80)
            Color(1, 1, 1, 0.30)
            Ellipse(pos=(cx - s * 0.38, cy + s * 0.12), size=(s * 0.30, s * 0.20))
            tex = text_texture(self.label, sp(10), tcol)
            Color(1, 1, 1, 1)
            Rectangle(texture=tex, size=tex.size,
                      pos=(cx - tex.width / 2, cy - tex.height / 2 - h * 0.05))


class LadderBar(Widget):
    """Gewinnleiter als Herz-Schlange von unten nach oben:
    untere Reihe links -> rechts, dann Wende, obere Reihe rechts -> links."""

    def __init__(self, **kw):
        super().__init__(**kw)
        self.cells = [HeartCell("0")] + [HeartCell("x%d" % m) for m in LADDER]
        for c in self.cells:
            self.add_widget(c)
        self.rung, self.active, self.phase = 0, False, False
        self.bind(pos=self._layout, size=self._layout)
        Clock.schedule_interval(self._blink, 0.35)

    def _slots(self):
        n = len(self.cells)
        per = (n + 1) // 2                  # untere Reihe
        x, y = self.pos
        w, h = self.size
        cw, ch = w / per, h / 2
        out = []
        for i in range(n):
            if i < per:
                out.append((x + i * cw, y, cw, ch))
            else:
                j = per - 1 - (i - per)
                out.append((x + j * cw + cw * 0.0, y + ch, cw, ch))
        return out

    def _layout(self, *_):
        for c, (cx, cy, cw, ch) in zip(self.cells, self._slots()):
            c.pos, c.size = (cx, cy), (cw, ch)
        self.canvas.before.clear()
        pts = []
        for cx, cy, cw, ch in self._slots():
            pts += [cx + cw / 2, cy + ch / 2]
        with self.canvas.before:
            Color(1.0, 0.78, 0.2, 0.30)
            Line(points=pts, width=dp(3), joint="round", cap="round")

    def _blink(self, dt):
        self.phase = not self.phase
        if self.active:
            self.show(self.rung, self.active)

    def show(self, rung, active):
        self.rung, self.active = rung, active
        self.cells[0].set("off")                       # Herz mit NULL am Anfang
        for i, c in enumerate(self.cells[1:]):
            if active and i == rung:
                c.set("active", self.phase)
            elif active and i < rung:
                c.set("passed")
            else:
                c.set("off")


# ----------------------------------------------- Risiko: Null oder mehr ----
class RiskFlip(Widget):
    """Grosses, pulsierendes Herz: 0 (dunkles Stahl-Herz) gegen die Zahl (feuriges Rot-Gold-Herz)."""

    def __init__(self, **kw):
        super().__init__(**kw)
        self.text, self.side, self.result = "", 0, None
        self.t = 0.0
        self.bind(pos=self.redraw, size=self.redraw)
        Clock.schedule_interval(self._tick, 1 / 30.0)

    def _tick(self, dt):
        self.t += dt
        if self.text and self.parent is not None:
            self.redraw()

    def reset(self):
        self.text, self.result = "", None
        self.redraw()

    def show(self, side, text):
        self.side, self.text, self.result = side, text, None
        self.redraw()

    def blank(self):
        self.text = ""
        self.redraw()

    def set_result(self, more):
        self.result = "more" if more else "zero"
        self.redraw()

    def redraw(self, *_):
        self.canvas.clear()
        x, y = self.pos
        w, h = self.size
        pulse = 1.0 + 0.06 * math.sin(self.t * 9.0)
        s = min(h * 0.60, w * 0.5) * pulse
        cx, cy = x + w / 2, y + h * 0.52
        with self.canvas:
            if not self.text:
                return
            if self.result == "more":
                glow, layers, tcol = (1.0, 0.85, 0.2), [(1.0, 0.75, 0.1), (1.0, 0.55, 0.1), (1.0, 0.85, 0.35), (1.0, 0.97, 0.7)], (0.35, 0.02, 0.05, 1)
            elif self.result == "zero":
                glow, layers, tcol = (1.0, 0.1, 0.1), [(0.5, 0.0, 0.05), (0.8, 0.05, 0.08), (1.0, 0.2, 0.2), (1.0, 0.45, 0.4)], (1, 1, 1, 1)
            elif self.side == 1:
                glow, layers, tcol = (1.0, 0.6, 0.1), [(1.0, 0.8, 0.2), (0.85, 0.0, 0.10), (1.0, 0.12, 0.18), (1.0, 0.45, 0.35)], (1, 1, 1, 1)
            else:
                glow, layers, tcol = (0.3, 0.5, 1.0), [(0.62, 0.66, 0.78), (0.10, 0.12, 0.20), (0.20, 0.24, 0.38), (0.38, 0.45, 0.65)], (0.85, 0.9, 1, 1)
            for k, a in ((1.55, 0.14), (1.35, 0.18), (1.18, 0.26)):
                Color(glow[0], glow[1], glow[2], a)
                draw_suit(0, cx, cy, s * k)
            Color(0.2, 0.12, 0.0, 1)
            draw_suit(0, cx, cy - dp(2), s * 1.05)
            for scale, col in zip((1.0, 0.86, 0.70, 0.50), layers):
                Color(col[0], col[1], col[2], 1)
                draw_suit(0, cx, cy + (1.0 - scale) * s * 0.10, s * scale)
            Color(1, 1, 1, 0.45)
            Ellipse(pos=(cx - s * 0.40, cy + s * 0.14), size=(s * 0.32, s * 0.20))
            tex = text_texture(self.text, s * (0.46 if len(self.text) < 4 else 0.32), tcol)
            Color(1, 1, 1, 1)
            Rectangle(texture=tex, size=tex.size,
                      pos=(cx - tex.width / 2, cy - tex.height / 2 + s * 0.05))


class RiskPanel(BoxLayout):
    def __init__(self, **kw):
        super().__init__(orientation="vertical", **kw)
        self.info = Label(text="", font_size=sp(1), size_hint_y=None, height=0)
        self.hint = Label(text="", font_size=sp(1), size_hint_y=None, height=0)
        self.track = RiskFlip()
        self.add_widget(self.track)


# -------------------------------------------------- Lampen-Taste Halten ----
class HoldLamp(ButtonBehavior, Widget):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.lit = False
        self.bind(pos=self.redraw, size=self.redraw, disabled=self.redraw)

    def set_lit(self, lit):
        if lit != self.lit:
            self.lit = lit
            self.redraw()

    def redraw(self, *_):
        self.canvas.clear()
        x, y = self.pos
        w, h = self.size
        r = min(w * 0.36, h * 0.34)
        cx, cy = x + w / 2, y + h * 0.66
        with self.canvas:
            Color(1, 1, 1, 1)
            Ellipse(pos=(cx - r * 1.2, cy - r * 1.2), size=(r * 2.4, r * 2.4),
                    texture=metal_texture(GOLD, 1.0))
            if self.lit:
                Color(1, 0.85, 0.2, 0.35)
                Ellipse(pos=(cx - r * 1.7, cy - r * 1.7), size=(r * 3.4, r * 3.4))
                col = GOLD
            elif self.disabled:
                col = (0.80, 0.04, 0.10, 1)
            else:
                col = (1.0, 0.07, 0.14, 1)
            Color(1, 1, 1, 1)
            Ellipse(pos=(cx - r, cy - r), size=(2 * r, 2 * r),
                    texture=metal_texture(col, 1.0))
            Color(1, 1, 1, 0.55)
            Ellipse(pos=(cx - r * 0.55, cy + r * 0.2), size=(r * 0.9, r * 0.5))
            tex = text_texture("HALTEN", sp(10), (0.9, 0.8, 0.5, 1) if not self.disabled
                               else (0.5, 0.45, 0.35, 1))
            Color(1, 1, 1, 1)
            Rectangle(texture=tex, size=tex.size, pos=(cx - tex.width / 2, y + h * 0.03))


# --------------------------------------------------------- Bausteine ----
class GlossButton(Button):
    """Glaenzende Taste mit Schatten, Verlauf und Lichtkante."""

    def __init__(self, text, color, font=17, **kw):
        super().__init__(text=text, bold=True, font_size=sp(font), background_normal="",
                         background_down="", background_color=(0, 0, 0, 0), **kw)
        self.base = color
        self.bind(pos=self.redraw, size=self.redraw, state=self.redraw, disabled=self.redraw)
        self.redraw()

    def set_label(self, text, color):
        if text != self.text or color != self.base:
            self.text, self.base = text, color
            self.redraw()

    def redraw(self, *_):
        self.canvas.before.clear()
        x, y = self.pos
        w, h = self.size
        c = self.base
        k = 0.30 if self.disabled else (0.80 if self.state == "down" else 1.0)
        dark = sum(c[:3]) < 1.6
        self.color = (1, 1, 1, 0.45 if self.disabled else 1) if dark else (
            INK[0], INK[1], INK[2], 0.5 if self.disabled else 1)
        with self.canvas.before:
            Color(0, 0, 0, 0.6)
            RoundedRectangle(pos=(x, y - dp(2.5)), size=(w, h), radius=[dp(10)])
            Color(1, 1, 1, 1)
            RoundedRectangle(pos=(x, y), size=(w, h), radius=[dp(10)],
                             texture=metal_texture(c, k))
            Color(1, 1, 1, 0.55 if not self.disabled else 0.15)
            Line(rounded_rectangle=(x + dp(0.5), y + dp(0.5), w - dp(1), h - dp(1), dp(10)),
                 width=dp(1))


def perimeter(x, y, w, h, r, n):
    """n Punkte gleichmaessig auf dem Rand eines abgerundeten Rechtecks."""
    top, bot = y + h, y
    straight_w, straight_h = w - 2 * r, h - 2 * r
    arc = math.pi * r / 2
    segs = [(straight_w, "t"), (arc, "tr"), (straight_h, "r"), (arc, "br"),
            (straight_w, "b"), (arc, "bl"), (straight_h, "l"), (arc, "tl")]
    total = sum(sg[0] for sg in segs)
    pts = []
    for i in range(n):
        d = total * i / n
        for ln, kind in segs:
            if d <= ln:
                f = d / ln if ln else 0
                if kind == "t":
                    p = (x + r + f * straight_w, top)
                elif kind == "tr":
                    a = math.pi / 2 - f * math.pi / 2
                    p = (x + w - r + r * math.cos(a), top - r + r * math.sin(a))
                elif kind == "r":
                    p = (x + w, top - r - f * straight_h)
                elif kind == "br":
                    a = -f * math.pi / 2
                    p = (x + w - r + r * math.cos(a), bot + r + r * math.sin(a))
                elif kind == "b":
                    p = (x + w - r - f * straight_w, bot)
                elif kind == "bl":
                    a = -math.pi / 2 - f * math.pi / 2
                    p = (x + r + r * math.cos(a), bot + r + r * math.sin(a))
                elif kind == "l":
                    p = (x, bot + r + f * straight_h)
                else:
                    a = math.pi - f * math.pi / 2
                    p = (x + r + r * math.cos(a), top - r + r * math.sin(a))
                pts.append(p)
                break
            d -= ln
    return pts


class TitleBar(BoxLayout):
    """Goldene Metall-Leiste mit wanderndem Lichtreflex."""

    def __init__(self, text, **kw):
        super().__init__(**kw)
        self.add_widget(Label(text=text, font_size=sp(24), bold=True, color=(0.28, 0.02, 0.06, 1)))
        self._shine = None
        self._t = 0.0
        self._dots = []
        self._phase = 0.0
        self.bind(pos=self.redraw, size=self.redraw)
        Clock.schedule_interval(self._tick, 1 / 30.0)

    def _tick(self, dt):
        self._t = (self._t + dt / 3.2) % 1.6
        self._phase = (self._phase + dt * 16.0) % max(1, len(self._dots))
        self._move()

    def _move(self):
        n = len(self._dots)
        for i, (col, el) in enumerate(self._dots):
            k = ((i - self._phase) % n) / float(n)          # 0 = Kopf des Lauflichts
            col.a = max(0.18, 1.0 - k * 2.6)
        if self._shine is None:
            return
        x, y = self.pos
        w, h = self.size
        gx = x - w * 0.2 + self._t * w * 1.4
        b = h * 0.12
        self._shine.points = [gx, y + b, gx + w * 0.10, y + b, gx + w * 0.16, y + h - b,
                              gx + w * 0.06, y + h - b]

    def redraw(self, *_):
        self.canvas.before.clear()
        self.canvas.after.clear()
        x, y = self.pos
        w, h = self.size
        with self.canvas.before:
            Color(0, 0, 0, 0.55)
            RoundedRectangle(pos=(x, y + h * 0.02), size=(w, h * 0.88), radius=[h * 0.30])
            Color(1, 1, 1, 1)
            RoundedRectangle(pos=(x, y + h * 0.08), size=(w, h * 0.84), radius=[h * 0.30],
                             texture=metal_texture(GOLD, 1.0))
            Color(1, 1, 1, 0.65)
            Line(rounded_rectangle=(x + 0.5, y + h * 0.08, w - 1, h * 0.84, h * 0.30), width=dp(1))
            for cx, suit in ((x + h * 0.75, 0), (x + h * 1.35, 1),
                             (x + w - h * 1.35, 2), (x + w - h * 0.75, 3)):
                Color(*((0.75, 0.02, 0.10, 1) if suit < 2 else (0.25, 0.02, 0.06, 1)))
                draw_suit(suit, cx, y + h / 2 + dp(1), h * 0.42)
        self._dots = []
        d = dp(5.2)
        with self.canvas.after:
            for px_, py_ in perimeter(x, y + h * 0.08, w, h * 0.84, h * 0.30, 36):
                col = Color(1.0, 0.97, 0.80, 0.2)
                el = Ellipse(pos=(px_ - d / 2, py_ - d / 2), size=(d, d))
                self._dots.append((col, el))
            Color(1, 1, 1, 0.38)
            self._shine = Quad(points=[0, 0, 0, 0, 0, 0, 0, 0])
        self._move()


class PayRow(BoxLayout):
    def __init__(self, name, mult, **kw):
        super().__init__(padding=[dp(8), 0], **kw)
        self.name = name
        self.lit = False
        self.l1 = Label(text=name, font_size=sp(13), halign="left", valign="middle",
                        color=(0.86, 0.9, 0.95, 1))
        self.l2 = Label(text="x%d" % mult, font_size=sp(13), bold=True, halign="right",
                        valign="middle", color=GOLD, size_hint_x=0.35)
        for lab in (self.l1, self.l2):
            lab.bind(size=lambda w, s: setattr(w, "text_size", s))
            self.add_widget(lab)
        self.bind(pos=self.redraw, size=self.redraw)

    def set_lit(self, lit):
        if lit != self.lit:
            self.lit = lit
            self.l1.color = INK if lit else (0.86, 0.9, 0.95, 1)
            self.l2.color = INK if lit else GOLD
            self.redraw()

    def redraw(self, *_):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*(GOLD if self.lit else (0.30, 0.04, 0.09, 0.80)))
            RoundedRectangle(pos=(self.x + dp(1), self.y + dp(1)),
                             size=(self.width - dp(2), self.height - dp(2)), radius=[dp(6)])


class PayTable(GridLayout):
    def __init__(self, **kw):
        super().__init__(cols=2, spacing=[dp(6), dp(3)], **kw)
        self.paylines = {}
        for name, mult in PAYTABLE:
            row = PayRow(name, mult)
            self.paylines[name] = row
            self.add_widget(row)

    def highlight(self, name):
        for n, row in self.paylines.items():
            row.set_lit(n == name)


class Machine(BoxLayout):
    def __init__(self, store_path, **kw):
        super().__init__(orientation="vertical", padding=dp(14), spacing=dp(7), **kw)
        self.store_path = store_path
        self.game = Game()
        self._load()
        self.sfx = Sfx()
        self._busy = False
        self.frozen = None
        self._mode = None
        self.running = False
        self.pause = False
        self.resolving = False
        self.risk_round = 0
        self._auto_ev = None
        self._ev = None
        self._pos = 0
        self._dir = 1

        with self.canvas.before:
            Color(*BG)
            self._bg = Rectangle(pos=self.pos, size=self.size)
            tex = image_texture("bg.png")
            if tex is not None:
                Color(1, 1, 1, 1)
                self._bgimg = Rectangle(texture=tex, pos=self.pos, size=self.size)
            else:
                self._bgimg = None
            Color(1.0, 0.78, 0.22, 1)
            self._frame = Line(rounded_rectangle=(0, 0, 10, 10, 10), width=dp(6))
            Color(1.0, 0.93, 0.68, 1)
            self._frame2 = Line(rounded_rectangle=(0, 0, 10, 10, 8), width=dp(1))
        with self.canvas.after:
            self._flash_color = Color(1, 1, 1, 0)
            self._flash_rect = Rectangle(pos=self.pos, size=self.size)
        self._fdots = []
        self._fphase = 0.0
        self.bind(pos=self._layout_bg, size=self._layout_bg)
        Clock.schedule_interval(self._frame_tick, 1 / 30.0)

        # Anzeigen
        top = BoxLayout(size_hint_y=None, height=dp(58), spacing=dp(8))
        self.credit_led = LedDisplay(digits=6)
        self.stake_led = LedDisplay(digits=2)
        self.win_led = LedDisplay(digits=6)
        for cap, led, hint in (("PUNKTE", self.credit_led, 1.7), ("EINSATZ", self.stake_led, 0.6),
                               ("GEWINN", self.win_led, 1.7)):
            col = BoxLayout(orientation="vertical", size_hint_x=hint)
            col.add_widget(Label(text=cap, font_size=sp(11), bold=True, color=GOLD,
                                 size_hint_y=None, height=dp(16)))
            col.add_widget(led)
            top.add_widget(col)
        self.add_widget(top)

        self.add_widget(TitleBar("POKERHERZ", size_hint_y=None, height=dp(44)))
        self.ladder = LadderBar(size_hint_y=None, height=dp(86))
        self.add_widget(self.ladder)

        self.msg = Label(text="", font_size=sp(15), color=(0.95, 0.95, 0.85, 1),
                         size_hint_y=None, height=dp(26))
        self.add_widget(self.msg)

        # Walzenfenster mit echten Kartenbildern
        window = BoxLayout(spacing=dp(6), padding=[dp(8), dp(8)], size_hint_y=None,
                           height=dp(118))
        with window.canvas.before:
            Color(1, 1, 1, 1)
            self._win_out = RoundedRectangle(pos=window.pos, size=window.size, radius=[dp(12)],
                                             texture=metal_texture(GOLD, 1.0))
            Color(0.07, 0.07, 0.10, 1)
            self._win_bg = RoundedRectangle(pos=window.pos, size=window.size, radius=[dp(9)])

        def upd(*_):
            self._win_out.pos, self._win_out.size = window.pos, window.size
            self._win_bg.pos = (window.x + dp(3.5), window.y + dp(3.5))
            self._win_bg.size = (window.width - dp(7), window.height - dp(7))
        window.bind(pos=upd, size=upd)
        self.reels = [CardWidget() for _ in range(5)]
        for i, r in enumerate(self.reels):
            r.on_tap = lambda i=i: self.on_hold(i)
            window.add_widget(r)
        self.add_widget(window)

        lamps = BoxLayout(spacing=dp(6), padding=[dp(8), 0], size_hint_y=None, height=dp(54))
        self.lamps = []
        for i in range(5):
            lamp = HoldLamp()
            lamp.bind(on_release=lambda btn, i=i: self.on_hold(i))
            self.lamps.append(lamp)
            lamps.add_widget(lamp)
        self.add_widget(lamps)

        # Mitte: Gewinntabelle oder Risiko-Bereich
        self.middle = BoxLayout()
        self.paytable = PayTable()
        self.risk_panel = RiskPanel()
        self.add_widget(self.middle)

        # Steuerung
        row1 = BoxLayout(spacing=dp(8), size_hint_y=None, height=dp(44))
        self.btn_minus = GlossButton("Einsatz -", (0.34, 0.36, 0.42, 1), 15)
        self.btn_plus = GlossButton("Einsatz +", (0.34, 0.36, 0.42, 1), 15)
        self.btn_sound = GlossButton("Ton an", (0.34, 0.36, 0.42, 1), 15)
        self.btn_minus.bind(on_release=lambda *_: self.on_stake(-1))
        self.btn_plus.bind(on_release=lambda *_: self.on_stake(1))
        self.btn_sound.bind(on_release=lambda *_: self.on_sound())
        for b in (self.btn_minus, self.btn_plus, self.btn_sound):
            row1.add_widget(b)
        self.add_widget(row1)

        row2 = BoxLayout(spacing=dp(8), size_hint_y=None, height=dp(62))
        self.btn_main = GlossButton("START", (0.92, 0.06, 0.13, 1), 18)
        self.btn_risk = GlossButton("RISIKO", (0.92, 0.06, 0.13, 1), 18)
        self.btn_take = GlossButton("NEHMEN", GOLD, 18)
        self.btn_main.bind(on_release=lambda *_: self.on_main())
        self.btn_risk.bind(on_release=lambda *_: self.on_risk())
        self.btn_take.bind(on_release=lambda *_: self.on_take())
        for b in (self.btn_main, self.btn_risk, self.btn_take):
            row2.add_widget(b)
        self.add_widget(row2)

        self.add_widget(Label(text="Nur Spielgeld - kein Echtgeld", font_size=sp(10.5),
                              color=(0.7, 0.75, 0.8, 1), size_hint_y=None, height=dp(16)))
        self.refresh()

    # --- Rahmen / Effekte -------------------------------------------------
    def _layout_bg(self, *_):
        x, y = self.pos
        w, h = self.size
        self._bg.pos, self._bg.size = self.pos, self.size
        if self._bgimg is not None:
            self._bgimg.pos, self._bgimg.size = self.pos, self.size
        self._frame.rounded_rectangle = (x + dp(3), y + dp(3), w - dp(6), h - dp(6), dp(14))
        self._frame2.rounded_rectangle = (x + dp(8), y + dp(8), w - dp(16), h - dp(16), dp(10))
        self._flash_rect.pos, self._flash_rect.size = self.pos, self.size
        for col, el in self._fdots:
            self.canvas.after.remove(col)
            self.canvas.after.remove(el)
        self._fdots = []
        d = dp(5.5)
        with self.canvas.after:
            for px_, py_ in perimeter(x + dp(3), y + dp(3), w - dp(6), h - dp(6), dp(14), 110):
                col = Color(1.0, 0.97, 0.80, 0.2)
                el = Ellipse(pos=(px_ - d / 2, py_ - d / 2), size=(d, d))
                self._fdots.append((col, el))

    def _frame_tick(self, dt):
        n = len(self._fdots)
        if not n:
            return
        self._fphase = (self._fphase + dt * 22.0) % n
        for i, (col, el) in enumerate(self._fdots):
            k = ((i - self._fphase) % n) / float(n)
            col.a = max(0.12, 1.0 - k * 3.0)

    def sparkle(self, n=26):
        parts = []
        with self.canvas.after:
            for _ in range(n):
                col = Color(1.0, random.uniform(0.7, 0.95), random.uniform(0.2, 0.5), 1)
                size = random.uniform(dp(3), dp(7))
                el = Ellipse(pos=(0, 0), size=(size, size))
                parts.append({"c": col, "e": el, "x": self.width * random.uniform(0.2, 0.8) + self.x,
                              "y": self.y + self.height * 0.55, "vx": random.uniform(-dp(160), dp(160)),
                              "vy": random.uniform(dp(120), dp(420)), "life": random.uniform(0.7, 1.3)})

        def step(dt):
            alive = False
            for p in parts:
                if p["life"] <= 0:
                    continue
                p["life"] -= dt
                p["vy"] -= dp(700) * dt
                p["x"] += p["vx"] * dt
                p["y"] += p["vy"] * dt
                p["e"].pos = (p["x"], p["y"])
                p["c"].a = max(0.0, min(1.0, p["life"] * 1.5))
                alive = alive or p["life"] > 0
            if not alive:
                for p in parts:
                    self.canvas.after.remove(p["c"])
                    self.canvas.after.remove(p["e"])
                return False
            return True

        Clock.schedule_interval(step, 1 / 40.0)

    def flash(self, rgb):
        if not (rgb[0] > 0.9 and rgb[1] < 0.3):
            self.sparkle()
        self._flash_color.rgba = (rgb[0], rgb[1], rgb[2], 0.5)
        Animation(a=0, duration=0.7).start(self._flash_color)

    # --- Speichern --------------------------------------------------------
    def _load(self):
        try:
            with open(self.store_path) as f:
                d = json.load(f)
            self.game.credit = int(d.get("credit", self.game.credit))
            self.game.stake = int(d.get("stake", self.game.stake))
            if self.game.credit < 5:
                self.game.reset()
        except Exception:
            pass

    def _save(self):
        try:
            with open(self.store_path, "w") as f:
                json.dump({"credit": self.game.credit, "stake": self.game.stake}, f)
        except Exception:
            pass

    # --- Aktionen ---------------------------------------------------------
    def on_sound(self):
        self.sfx.on = not self.sfx.on
        self.btn_sound.text = "Ton an" if self.sfx.on else "Ton aus"
        self.sfx.play("click")

    def on_stake(self, d):
        if self._busy:
            return
        self.game.change_stake(d)
        self.sfx.play("click")
        self.refresh()

    def on_hold(self, i):
        if self._busy:
            return
        self.game.toggle_hold(i)
        self.sfx.play("hold")
        self.refresh()

    def on_main(self):
        g = self.game
        if self._busy:
            return
        self.sfx.play("click")
        if g.state == "idle":
            if g.credit < g.stake:
                g.reset()
                self.refresh()
                return
            if g.start():
                self.refresh()
                self.animate(range(5))
        elif g.state == "held":
            changing = [i for i in range(5) if not g.held[i]]
            g.draw()
            self.animate(changing)

    def on_take(self):
        """NEHMEN geht jederzeit (auch waehrend das Risiko laeuft) - ausser waehrend der Aufloesung."""
        if self.resolving:
            return
        if self._auto_ev is not None:
            self._auto_ev.cancel()
            self._auto_ev = None
        self.pause = False
        if self.running:
            self.running = False
            if self._ev is not None:
                self._ev.cancel()
            self.sfx.stop("risk_loop")
            self.frozen = None
            self._busy = False
        if not self._busy and self.game.take():
            self.sfx.play("coins")
            self._save()
            self.refresh()

    # --- Walzen-Animation -------------------------------------------------
    def animate(self, indices):
        indices = list(indices)
        self._busy = True
        stop_at = {i: 7 + 4 * n for n, i in enumerate(indices)}
        tick = {"n": 0}
        final = list(self.game.cards)
        g = self.game

        def step(dt):
            tick["n"] += 1
            n = tick["n"]
            if n % 2 == 0:
                self.sfx.play("tick", 0.5)
            for i in indices:
                r = self.reels[i]
                if n < stop_at[i]:
                    r.blur = (random.choice(RANKS), random.choice(SUITS))
                    r.set(final[i], held=False, spinning=True)
                elif n == stop_at[i]:
                    r.set(final[i], held=g.held[i], spinning=False)
                    self.sfx.play("stop", 0.8)
            if n >= max(stop_at.values()):
                self._busy = False
                self._save()
                if g.state == "result":
                    mult = g.win // max(1, g.stake)
                    self.sfx.play("win_big" if mult >= 10 else "win_small")
                    self.flash((1.0, 0.85, 0.3))
                    self.risk_round = 0
                    self._auto_ev = Clock.schedule_once(lambda dt: self._next_round(), 1.6)
                elif g.state == "idle" and g.win == 0 and g.win_name is None:
                    self.sfx.play("lose", 0.35)
                self.refresh()
                return False
            return True

        Clock.schedule_interval(step, 0.06)

    # --- Risiko: Anzeige springt zwischen 0 und dem doppelten Gewinn --------
    def on_risk(self):
        g = self.game
        if self.running:
            self.on_stop()
            return
        return

    def _next_round(self):
        self._auto_ev = None
        self.pause = False
        self._begin_round()

    def _begin_round(self):
        g = self.game
        if self._busy or not g.risk_start():
            return
        self._busy = True
        self.running = True
        self.frozen = {"win": g.win, "rung": g.rung, "credit": g.credit}
        panel, track = self.risk_panel, self.risk_panel.track
        track.reset()
        self.refresh()
        self.msg.text = "STOPP druecken - bei der Zahl!"
        self.sfx.play("risk_start")
        Clock.schedule_once(lambda dt: self.running and self.sfx.play("risk_loop", 0.8, loop=True), 0.5)
        self._more_text = str(g.win * 2)
        self._pos = random.randrange(2)
        # immer schneller: Null, Zahl, Null, Zahl ... das Tempo steigt bei jedem Wechsel
        state = {"dt": 1.1 * 0.93 ** min(g.rung, 5), "min": 0.12, "n": 0}

        def run(dt):
            if not self.running:
                return
            self._pos = 1 - self._pos
            track.show(self._pos, self._more_text if self._pos else "0")
            state["n"] += 1
            if state["dt"] > 0.07 or state["n"] % 2 == 0:
                self.sfx.play("risk_tick_hi" if self._pos else "risk_tick_lo", 0.4)
            state["dt"] = max(state["min"], state["dt"] * 0.82)
            if state["n"] >= 7:                  # kein STOPP: nach 7 Wechseln stoppt es von selbst
                self._ev = Clock.schedule_once(lambda dt: self.on_stop(), state["dt"])
                return
            self._ev = Clock.schedule_once(run, state["dt"])

        track.show(self._pos, self._more_text if self._pos else "0")
        self._ev = Clock.schedule_once(run, state["dt"])

    def on_stop(self):
        if not self.running:
            return
        self.running = False
        self.resolving = True
        if self._ev is not None:
            self._ev.cancel()
        g = self.game
        panel, track = self.risk_panel, self.risk_panel.track
        self.sfx.stop("risk_loop")
        self.sfx.play("risk_stop")
        self.sfx.play("risk_hold")
        self.msg.text = "Und ...?"
        self.refresh()
        side = self._pos
        text = self._more_text if side else "0"

        def blink(k):
            if k % 2 == 0:
                track.show(side, text)
                self.sfx.play("heart", 0.8)
            else:
                track.blank()
            if k >= 6:
                reveal()
            else:
                Clock.schedule_once(lambda dt: blink(k + 1), 0.26)

        mult_box = {"m": 0}

        def reveal():
            mult = g.risk_resolve(side)
            mult_box["m"] = mult
            track.show(side, text)
            track.set_result(bool(mult))
            if mult:
                self.sfx.play("risk_win")
                self.flash((1.0, 0.85, 0.4))
                self.msg.text = "MEHR!"
            else:
                self.sfx.play("risk_lose")
                self.flash((1.0, 0.1, 0.1))
                self.msg.text = "NULL!"
            Clock.schedule_once(finish, 1.8)

        def finish(dt):
            self.frozen = None
            self._busy = False
            self.resolving = False
            if mult_box["m"] and g.state == "risk":
                # weiter: die naechste Runde laeuft sofort von selbst
                self.risk_round += 1
                self.pause = True
                self.refresh()
                self._auto_ev = Clock.schedule_once(lambda dt: self._next_round(), 0.9)
                return
            self.pause = False
            self._save()
            self.refresh()

        Clock.schedule_once(lambda dt: blink(0), 0.2)

    # --- Anzeige ----------------------------------------------------------
    def refresh(self):
        g = self.game
        view = self.frozen or {"win": g.win, "rung": g.rung, "credit": g.credit}
        self.credit_led.set(view["credit"])
        self.stake_led.set(g.stake)
        self.win_led.set(view["win"] if view["win"] else "")
        if not self.frozen:
            self.msg.text = g.message
        if not self._busy:
            for i, r in enumerate(self.reels):
                r.set(g.cards[i], held=g.held[i] and g.state == "held")
        for i, lamp in enumerate(self.lamps):
            lamp.set_lit(g.held[i] and g.state == "held")
            lamp.disabled = g.state != "held"
        self.paytable.highlight(g.win_name)
        in_risk = g.state in ("result", "risk") or self.frozen is not None
        self.ladder.show(view["rung"], in_risk and view["win"] > 0)

        mode = "risk" if in_risk else "pay"
        if mode != self._mode:
            self._mode = mode
            self.middle.clear_widgets()
            self.middle.add_widget(self.risk_panel if in_risk else self.paytable)
            if in_risk:
                self.risk_panel.track.reset()
        if self.pause:
            self.msg.text = "Weiter ..."
        elif in_risk and not self.frozen:
            self.msg.text = "Gleich geht's los - STOPP bei der Zahl!"

        self.btn_risk.disabled = not self.running
        self.btn_risk.set_label("STOPP" if self.running else "RISIKO",
                                GOLD if self.running else (0.92, 0.06, 0.13, 1))
        self.btn_take.disabled = self.resolving or g.state not in ("result", "risk")
        self.btn_main.disabled = in_risk
        self.btn_main.text = "ZIEHUNG" if g.state == "held" else (
            "NEU STARTEN" if g.credit < g.stake else "START")
        self.btn_minus.disabled = self.btn_plus.disabled = g.state != "idle" or bool(self.frozen)


class KartenwalzenApp(App):
    title = "Pokerherz"

    def build(self):
        if os.environ.get("KARTEN_TEST_FEHLER"):
            raise RuntimeError("Testfehler fuer die Fehleranzeige")
        path = os.path.join(self.user_data_dir, "stand.json")
        return Machine(store_path=path)


def run():
    KartenwalzenApp().run()
