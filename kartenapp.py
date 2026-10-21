"""Kartenwalzen - Walzen-Kartenspiel mit Halten, Ziehung und Risiko "Null oder mehr".

Eigenes Spiel.  Kartenbilder: Byron Knoll (gemeinfrei).  Klaenge selbst erzeugt.
Nur Spielgeld, kein Echtgeld.  Oberflaeche: Kivy (Desktop und Android-APK).
"""
import json
import os
import random

from kivy.animation import Animation
from kivy.app import App
from kivy.clock import Clock
from kivy.core.audio import SoundLoader
from kivy.core.image import Image as CoreImage
from kivy.core.text import Label as CoreLabel
from kivy.core.window import Window
from kivy.graphics import (Color, Ellipse, Line, Quad, Rectangle, RoundedRectangle,
                           Triangle)
from kivy.metrics import dp, sp
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.widget import Widget

from logic import LADDER, PAYTABLE, RANKS, RISK_CELLS, SUITS, Game

HERE = os.path.dirname(os.path.abspath(__file__))
BG = (0.08, 0.20, 0.40, 1)
GOLD = (1.0, 0.82, 0.30, 1)
RED = (0.82, 0.10, 0.14, 1)
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
    """Rote Siebensegment-Anzeige."""

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
        text = self.value[-self.digits:].rjust(self.digits)
        cw = w / self.digits
        m = cw * 0.22
        th = max(dp(1.8), cw * 0.10)
        g = th * 0.9
        y0, y1 = y + h * 0.17, y + h * 0.83
        ym = (y0 + y1) / 2
        with self.canvas:
            Color(0.01, 0.0, 0.0, 1)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(5)])
            Color(0.55, 0.42, 0.10, 1)
            Line(rounded_rectangle=(x, y, w, h, dp(5)), width=dp(1))
            for i, ch in enumerate(text):
                x0, x1 = x + i * cw + m, x + (i + 1) * cw - m
                segs = {
                    "a": [x0 + g, y1, x1 - g, y1], "b": [x1, y1 - g, x1, ym + g],
                    "c": [x1, ym - g, x1, y0 + g], "d": [x0 + g, y0, x1 - g, y0],
                    "e": [x0, ym - g, x0, y0 + g], "f": [x0, y1 - g, x0, ym + g],
                    "g": [x0 + g, ym, x1 - g, ym]}
                lit = SEGMENTS.get(ch, "")
                for name, pts in segs.items():
                    if name in lit:
                        Color(1, 0.10, 0.05, 0.28)
                        Line(points=pts, width=th * 2.3, cap="round")
                        Color(1, 0.30, 0.18, 1)
                    else:
                        Color(0.14, 0.015, 0.015, 1)
                    Line(points=pts, width=th, cap="round")


# ---------------------------------------------------------------- Karten ----
class CardWidget(Widget):
    """Eine Walze: zeigt ein Kartenbild oder die Rueckseite."""

    def __init__(self, **kw):
        super().__init__(**kw)
        self.card = None
        self.held = False
        self.spinning = False
        self.blur = None
        self.bind(pos=self.redraw, size=self.redraw)

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
            if self.state == "active":
                Color(GOLD[0], GOLD[1], GOLD[2], 0.40 if self.glow else 0.18)
                draw_suit(0, cx, cy, s * 1.3)
                Color(*GOLD)
                tcol = INK
            elif self.state == "passed":
                Color(0.85, 0.12, 0.18, 1)
                tcol = (1, 1, 1, 1)
            else:
                Color(0.62, 0.20, 0.34, 1)
                tcol = (1, 0.88, 0.9, 1)
            draw_suit(0, cx, cy, s)
            tex = text_texture(self.label, sp(10.5), tcol)
            Color(1, 1, 1, 1)
            Rectangle(texture=tex, size=tex.size,
                      pos=(cx - tex.width / 2, cy - tex.height / 2 - h * 0.05))


class LadderBar(BoxLayout):
    """Gewinnleiter x1 bis x64 aus Herzen; die aktuelle Stufe blinkt."""

    def __init__(self, **kw):
        super().__init__(orientation="horizontal", spacing=dp(2), **kw)
        self.cells = [HeartCell("x%d" % m) for m in LADDER]
        for c in self.cells:
            self.add_widget(c)
        self.rung, self.active, self.phase = 0, False, False
        Clock.schedule_interval(self._blink, 0.35)

    def _blink(self, dt):
        self.phase = not self.phase
        if self.active:
            self.show(self.rung, self.active)

    def show(self, rung, active):
        self.rung, self.active = rung, active
        for i, c in enumerate(self.cells):
            if active and i == rung:
                c.set("active", self.phase)
            elif active and i < rung:
                c.set("passed")
            else:
                c.set("off")


# ----------------------------------------------- Risiko: Null oder mehr ----
class RiskTrack(Widget):
    """Lauflicht-Leiste: links NULL, nach rechts waechst die Vermehrung (x2, ganz rechts x4)."""
    cells = len(RISK_CELLS)

    def __init__(self, **kw):
        super().__init__(**kw)
        self.runner = -1
        self.result = None          # None, "more" oder "zero" (Endergebnis)
        self.blink = False
        self.bind(pos=self.redraw, size=self.redraw)

    def reset(self):
        self.runner, self.result = -1, None
        self.redraw()

    def set_runner(self, i, blink=False):
        self.runner, self.blink = i, blink
        self.redraw()

    def set_result(self, i, more):
        self.runner, self.result, self.blink = i, "more" if more else "zero", False
        self.redraw()

    def redraw(self, *_):
        self.canvas.clear()
        x, y = self.pos
        w, h = self.size
        gap = dp(2.5)
        cw = (w - gap * (self.cells - 1)) / self.cells
        with self.canvas:
            for i in range(self.cells):
                cx = x + i * (cw + gap)
                val = RISK_CELLS[i]
                if val == 0:
                    base, tcol, label, fs = (0.46, 0.10, 0.20, 1), (1, 0.85, 0.88, 1), "0", 15
                elif val == 2:
                    base, tcol, label, fs = (0.98, 0.74, 0.20, 1), INK, "x2", 12
                else:
                    base, tcol, label, fs = (1.0, 0.45, 0.15, 1), (1, 1, 1, 1), "x4", 13
                lit = i == self.runner
                if lit:
                    if self.result == "more":
                        glow, base = (0.3, 1.0, 0.4), (0.45, 1.0, 0.50, 1)
                    elif self.result == "zero":
                        glow, base = (1.0, 0.2, 0.2), (1.0, 0.25, 0.25, 1)
                    else:
                        glow, base = (1.0, 1.0, 0.8), (1.0, 1.0, 0.92, 1)
                        if self.blink:
                            glow, base = (1.0, 0.6, 0.2), (1.0, 0.85, 0.5, 1)
                    Color(glow[0], glow[1], glow[2], 0.35)
                    RoundedRectangle(pos=(cx - dp(3), y - dp(5)), size=(cw + dp(6), h + dp(10)),
                                     radius=[dp(9)])
                    tcol = INK
                Color(*base)
                RoundedRectangle(pos=(cx, y), size=(cw, h), radius=[dp(7)])
                Color(1, 1, 1, 0.16)
                RoundedRectangle(pos=(cx + dp(1.2), y + h * 0.52), size=(cw - dp(2.4), h * 0.42),
                                 radius=[dp(6)])
                tex = text_texture(label, sp(fs), tcol)
                Color(1, 1, 1, 1)
                Rectangle(texture=tex, size=tex.size,
                          pos=(cx + (cw - tex.width) / 2, y + (h - tex.height) / 2))


class RiskPanel(BoxLayout):
    def __init__(self, **kw):
        super().__init__(orientation="vertical", spacing=dp(6), **kw)
        self.info = Label(text="", font_size=sp(16), bold=True, color=GOLD,
                          size_hint_y=None, height=dp(30))
        self.track = RiskTrack(size_hint_y=None, height=dp(54))
        self.hint = Label(text="", font_size=sp(13), color=(0.8, 0.85, 0.9, 1),
                          size_hint_y=None, height=dp(28))
        self.add_widget(Widget())
        self.add_widget(self.info)
        self.add_widget(self.track)
        self.add_widget(self.hint)
        self.add_widget(Widget())


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
            Color(0.12, 0.10, 0.06, 1)
            Ellipse(pos=(cx - r * 1.18, cy - r * 1.18), size=(r * 2.36, r * 2.36))
            if self.lit:
                Color(1, 0.85, 0.2, 0.30)
                Ellipse(pos=(cx - r * 1.6, cy - r * 1.6), size=(r * 3.2, r * 3.2))
                Color(1, 0.88, 0.30, 1)
            elif self.disabled:
                Color(0.22, 0.06, 0.07, 1)
            else:
                Color(0.62, 0.08, 0.10, 1)
            Ellipse(pos=(cx - r, cy - r), size=(2 * r, 2 * r))
            Color(1, 1, 1, 0.30)
            Ellipse(pos=(cx - r * 0.55, cy + r * 0.1), size=(r * 0.9, r * 0.6))
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
            Color(0, 0, 0, 0.55)
            RoundedRectangle(pos=(x, y - dp(2.5)), size=(w, h), radius=[dp(11)])
            Color(c[0] * 0.5 * k, c[1] * 0.5 * k, c[2] * 0.5 * k, 1)
            RoundedRectangle(pos=(x, y), size=(w, h), radius=[dp(11)])
            Color(c[0] * k, c[1] * k, c[2] * k, 1)
            RoundedRectangle(pos=(x + dp(1.5), y + dp(3)), size=(w - dp(3), h - dp(5)),
                             radius=[dp(10)])
            if not self.disabled:
                Color(1, 1, 1, 0.20)
                RoundedRectangle(pos=(x + dp(4), y + h * 0.52), size=(w - dp(8), h * 0.40),
                                 radius=[dp(8)])


class TitleBar(BoxLayout):
    def __init__(self, text, **kw):
        super().__init__(**kw)
        self.add_widget(Label(text=text, font_size=sp(24), bold=True, color=(1, 1, 1, 1),
                              outline_width=1.5, outline_color=(0.45, 0.05, 0.2, 1)))
        self.bind(pos=self.redraw, size=self.redraw)

    def redraw(self, *_):
        self.canvas.before.clear()
        x, y = self.pos
        w, h = self.size
        with self.canvas.before:
            Color(0, 0, 0, 0.25)
            RoundedRectangle(pos=(x, y + h * 0.04), size=(w, h * 0.84), radius=[h * 0.42])
            Color(0.86, 0.22, 0.42, 1)
            RoundedRectangle(pos=(x, y + h * 0.10), size=(w, h * 0.84), radius=[h * 0.42])
            Color(1, 1, 1, 0.16)
            RoundedRectangle(pos=(x + dp(6), y + h * 0.52), size=(w - dp(12), h * 0.38),
                             radius=[h * 0.19])
            for cx, suit in ((x + h * 0.75, 0), (x + h * 1.35, 1),
                             (x + w - h * 1.35, 2), (x + w - h * 0.75, 3)):
                Color(1, 1, 1, 0.95)
                draw_suit(suit, cx, y + h / 2 + dp(1), h * 0.42)


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
            Color(*(GOLD if self.lit else (1, 1, 1, 0.13)))
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
            Color(*GOLD)
            self._frame = Line(rounded_rectangle=(0, 0, 10, 10, 10), width=dp(3))
            Color(1, 1, 1, 0.25)
            self._frame2 = Line(rounded_rectangle=(0, 0, 10, 10, 8), width=dp(1))
        with self.canvas.after:
            self._flash_color = Color(1, 1, 1, 0)
            self._flash_rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._layout_bg, size=self._layout_bg)

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

        self.add_widget(TitleBar("KARTENWALZEN", size_hint_y=None, height=dp(44)))
        self.ladder = LadderBar(size_hint_y=None, height=dp(40))
        self.add_widget(self.ladder)

        self.msg = Label(text="", font_size=sp(15), color=(0.95, 0.95, 0.85, 1),
                         size_hint_y=None, height=dp(26))
        self.add_widget(self.msg)

        # Walzenfenster mit echten Kartenbildern
        window = BoxLayout(spacing=dp(6), padding=[dp(8), dp(8)], size_hint_y=None,
                           height=dp(118))
        with window.canvas.before:
            Color(0.04, 0.34, 0.36, 0.95)
            self._win_bg = RoundedRectangle(pos=window.pos, size=window.size, radius=[dp(10)])
            Color(*GOLD)
            self._win_line = Line(rounded_rectangle=(0, 0, 10, 10, 10), width=dp(2))

        def upd(*_):
            self._win_bg.pos, self._win_bg.size = window.pos, window.size
            self._win_line.rounded_rectangle = (window.x, window.y, window.width,
                                                window.height, dp(10))
        window.bind(pos=upd, size=upd)
        self.reels = [CardWidget() for _ in range(5)]
        for r in self.reels:
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
        self.btn_minus = GlossButton("Einsatz -", (0.30, 0.52, 0.80, 1), 15)
        self.btn_plus = GlossButton("Einsatz +", (0.30, 0.52, 0.80, 1), 15)
        self.btn_sound = GlossButton("Ton an", (0.30, 0.52, 0.80, 1), 15)
        self.btn_minus.bind(on_release=lambda *_: self.on_stake(-1))
        self.btn_plus.bind(on_release=lambda *_: self.on_stake(1))
        self.btn_sound.bind(on_release=lambda *_: self.on_sound())
        for b in (self.btn_minus, self.btn_plus, self.btn_sound):
            row1.add_widget(b)
        self.add_widget(row1)

        row2 = BoxLayout(spacing=dp(8), size_hint_y=None, height=dp(62))
        self.btn_main = GlossButton("START", (0.16, 0.74, 0.40, 1), 18)
        self.btn_risk = GlossButton("RISIKO", (0.98, 0.52, 0.10, 1), 18)
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

    def flash(self, rgb):
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
                elif g.state == "idle" and g.win == 0 and g.win_name is None:
                    self.sfx.play("lose", 0.35)
                self.refresh()
                return False
            return True

        Clock.schedule_interval(step, 0.06)

    # --- Risiko: Lauflicht selbst stoppen ----------------------------------
    def on_risk(self):
        g = self.game
        if self.running:
            self.on_stop()
            return
        if self._busy or not g.risk_start():
            return
        self._busy = True
        self.running = True
        self.frozen = {"win": g.win, "rung": g.rung, "credit": g.credit}
        panel, track = self.risk_panel, self.risk_panel.track
        track.reset()
        self.msg.text = "Stoppe das Licht - je weiter rechts, desto mehr!"
        self.refresh()
        panel.info.text = "STOPP druecken!"
        panel.hint.text = "links NULL   -   rechts MEHR (ganz rechts x4)"
        self.sfx.play("risk_start")
        Clock.schedule_once(lambda dt: self.running and self.sfx.play("risk_loop", 0.8, loop=True), 0.5)
        n = RiskTrack.cells
        self._pos = random.randrange(n)
        self._dir = random.choice((-1, 1))
        speed = max(0.045, 0.085 - 0.008 * g.rung)

        def advance():
            nxt = self._pos + self._dir
            if nxt < 0 or nxt >= n:
                self._dir = -self._dir
                nxt = self._pos + self._dir
            self._pos = nxt

        def run(dt):
            if not self.running:
                return
            advance()
            track.set_runner(self._pos)
            self.sfx.play("risk_tick_hi" if RISK_CELLS[self._pos] else "risk_tick_lo", 0.45)
            self._ev = Clock.schedule_once(run, speed)

        self._advance = advance
        self._ev = Clock.schedule_once(run, speed)

    def on_stop(self):
        if not self.running:
            return
        self.running = False
        if self._ev is not None:
            self._ev.cancel()
        g = self.game
        panel, track = self.risk_panel, self.risk_panel.track
        self.sfx.stop("risk_loop")
        self.sfx.play("risk_stop")
        panel.info.text = "Das Licht laeuft aus ..."
        self.refresh()

        def coast(i):
            self._advance()
            track.set_runner(self._pos)
            self.sfx.play("risk_tick_hi" if RISK_CELLS[self._pos] else "risk_tick_lo", 0.7)
            if i + 1 < 3:
                Clock.schedule_once(lambda dt: coast(i + 1), 0.12 + 0.16 * (i + 1))
            else:
                self.sfx.play("risk_hold")
                panel.info.text = "Und ...?"
                blink(0)

        def blink(k):
            track.set_runner(self._pos, blink=(k % 2 == 0))
            if k % 2 == 0:
                self.sfx.play("heart", 0.8)
            if k >= 5:
                reveal()
            else:
                Clock.schedule_once(lambda dt: blink(k + 1), 0.28)

        def reveal():
            mult = g.risk_resolve(self._pos)
            track.set_result(self._pos, bool(mult))
            self.msg.text = g.message
            if mult:
                self.sfx.play("risk_win")
                self.flash((0.4, 1.0, 0.5))
                panel.info.text = "MEHR x%d!" % mult
            else:
                self.sfx.play("risk_lose")
                self.flash((1.0, 0.1, 0.1))
                panel.info.text = "NULL!"
            Clock.schedule_once(finish, 1.8)

        def finish(dt):
            self.frozen = None
            self._busy = False
            self._save()
            self.refresh()

        Clock.schedule_once(lambda dt: coast(0), 0.15)

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
        if in_risk and not self.frozen:
            self.risk_panel.info.text = "Gewinn %d  -  RISIKO oder NEHMEN" % g.win
            self.risk_panel.hint.text = "Du stoppst das Licht selbst: links NULL, rechts MEHR"

        self.btn_risk.disabled = (bool(self.frozen) and not self.running) or (
            not self.frozen and g.state not in ("result", "risk"))
        self.btn_risk.set_label("STOPP" if self.running else "RISIKO",
                                (0.90, 0.15, 0.20, 1) if self.running else (0.98, 0.52, 0.10, 1))
        self.btn_take.disabled = bool(self.frozen) or g.state not in ("result", "risk")
        self.btn_main.disabled = in_risk
        self.btn_main.text = "ZIEHUNG" if g.state == "held" else (
            "NEU STARTEN" if g.credit < g.stake else "START")
        self.btn_minus.disabled = self.btn_plus.disabled = g.state != "idle" or bool(self.frozen)


class KartenwalzenApp(App):
    title = "Kartenwalzen"

    def build(self):
        if os.environ.get("KARTEN_TEST_FEHLER"):
            raise RuntimeError("Testfehler fuer die Fehleranzeige")
        path = os.path.join(self.user_data_dir, "stand.json")
        return Machine(store_path=path)


def run():
    KartenwalzenApp().run()
