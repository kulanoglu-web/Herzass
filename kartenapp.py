"""Kartenwalzen - Walzen-Kartenspiel mit Halten, Ziehung und Risikoleiter.

Eigenes Spiel mit eigener Grafik und eigenen, selbst erzeugten Klaengen.
Nur Spielgeld, kein Echtgeld.  Oberflaeche: Kivy (Desktop und Android-APK).
"""
import json
import os
import random

from kivy.animation import Animation
from kivy.app import App
from kivy.clock import Clock
from kivy.core.audio import SoundLoader
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

from logic import (LADDER, PAYTABLE, RANK_LABEL, RANKS, SUITS, Game, is_red)

BG = (0.02, 0.03, 0.09, 1)
GOLD = (0.95, 0.78, 0.25, 1)
RED = (0.82, 0.10, 0.14, 1)
INK = (0.08, 0.08, 0.10, 1)
CARD_BG = (0.98, 0.97, 0.92, 1)

Window.clearcolor = BG


# ---------------------------------------------------------------- Helfer ----
def text_texture(text, size, color, bold=True):
    lab = CoreLabel(text=text, font_size=size, bold=bold, color=color)
    lab.refresh()
    return lab.texture


def draw_suit(suit, cx, cy, s):
    """Zeichnet ein Farbsymbol (0 Herz, 1 Karo, 2 Pik, 3 Kreuz) um (cx, cy), Groesse s."""
    if suit == 0:      # Herz
        Ellipse(pos=(cx - s * 0.52, cy - s * 0.02), size=(s * 0.55, s * 0.55))
        Ellipse(pos=(cx - s * 0.03, cy - s * 0.02), size=(s * 0.55, s * 0.55))
        Triangle(points=[cx - s * 0.50, cy + s * 0.18, cx + s * 0.50, cy + s * 0.18,
                         cx, cy - s * 0.55])
    elif suit == 1:    # Karo
        Quad(points=[cx, cy + s * 0.58, cx + s * 0.40, cy, cx, cy - s * 0.58,
                     cx - s * 0.40, cy])
    elif suit == 2:    # Pik
        Ellipse(pos=(cx - s * 0.52, cy - s * 0.30), size=(s * 0.55, s * 0.55))
        Ellipse(pos=(cx - s * 0.03, cy - s * 0.30), size=(s * 0.55, s * 0.55))
        Triangle(points=[cx - s * 0.50, cy - s * 0.04, cx + s * 0.50, cy - s * 0.04,
                         cx, cy + s * 0.60])
        Triangle(points=[cx, cy - s * 0.1, cx - s * 0.18, cy - s * 0.58,
                         cx + s * 0.18, cy - s * 0.58])
    else:              # Kreuz
        r = s * 0.30
        Ellipse(pos=(cx - r, cy + s * 0.04), size=(2 * r, 2 * r))
        Ellipse(pos=(cx - r * 1.55, cy - s * 0.32), size=(2 * r, 2 * r))
        Ellipse(pos=(cx + r * 0.55, cy - s * 0.32), size=(2 * r, 2 * r))
        Triangle(points=[cx, cy - s * 0.05, cx - s * 0.16, cy - s * 0.58,
                         cx + s * 0.16, cy - s * 0.58])


class Sfx:
    """Spielt die mitgelieferten WAV-Effekte; faellt still aus, wenn kein Ton geht."""

    def __init__(self):
        self.base = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sounds")
        self.sounds = {}
        self.on = True

    def play(self, name, volume=1.0):
        if not self.on:
            return
        try:
            snd = self.sounds.get(name)
            if snd is None:
                snd = SoundLoader.load(os.path.join(self.base, name + ".wav"))
                self.sounds[name] = snd
            if snd:
                snd.volume = volume
                snd.stop()
                snd.play()
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
        m = cw * 0.2
        th = max(dp(2), cw * 0.10)
        g = th * 0.9
        y0, y1 = y + h * 0.16, y + h * 0.84
        ym = (y0 + y1) / 2
        with self.canvas:
            Color(0.02, 0.0, 0.0, 1)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(4)])
            Color(0.55, 0.42, 0.10, 1)
            Line(rounded_rectangle=(x, y, w, h, dp(4)), width=dp(1))
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
                        Color(1, 0.28, 0.16, 1)
                    else:
                        Color(0.24, 0.02, 0.02, 1)
                    Line(points=pts, width=th, cap="round")


# ---------------------------------------------------------------- Karten ----
class CardWidget(Widget):
    """Eine Walze: zeigt eine Karte oder die Rueckseite."""

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
        x, y = self.pos
        w, h = self.size
        card = self.blur if self.spinning else self.card
        with self.canvas:
            if self.held:
                Color(1, 0.85, 0.25, 0.35)
                RoundedRectangle(pos=(x - dp(5), y - dp(5)),
                                 size=(w + dp(10), h + dp(10)), radius=[dp(12)])
            Color(*(GOLD if self.held else (0.0, 0.0, 0.0, 0.6)))
            RoundedRectangle(pos=(x - dp(2.5), y - dp(2.5)),
                             size=(w + dp(5), h + dp(5)), radius=[dp(10)])
            if card is None:
                Color(0.45, 0.08, 0.12, 1)
                RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(8)])
                Color(*GOLD)
                Line(rounded_rectangle=(x + dp(6), y + dp(6), w - dp(12), h - dp(12),
                                        dp(6)), width=dp(1.2))
                draw_suit(0, x + w / 2, y + h / 2, w * 0.45)
                return
            Color(*CARD_BG)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(8)])
            # leichter Glanz oben
            Color(1, 1, 1, 0.25)
            RoundedRectangle(pos=(x + dp(2), y + h * 0.55), size=(w - dp(4), h * 0.43),
                             radius=[dp(7)])
            rank, suit = card
            Color(*(RED if is_red(card) else INK))
            draw_suit(suit, x + w / 2, y + h * 0.40, w * 0.62)
            tex = text_texture(RANK_LABEL[rank], sp(30), RED if is_red(card) else INK)
            Color(1, 1, 1, 1)
            Rectangle(texture=tex, size=tex.size,
                      pos=(x + dp(6), y + h - tex.height - dp(4)))


class RiskCard(Widget):
    """Grosse Risikokarte: Rueckseite, rot/schwarz-Wechsel waehrend der Spannung, dann Aufdeckung."""

    def __init__(self, **kw):
        super().__init__(**kw)
        self.mode = "back"
        self.card = None
        self.bind(pos=self.redraw, size=self.redraw)

    def set_mode(self, mode, card=None):
        self.mode, self.card = mode, card
        self.redraw()

    def redraw(self, *_):
        self.canvas.clear()
        cw = min(self.width, self.height * 0.70)
        ch = cw / 0.70
        x = self.x + (self.width - cw) / 2
        y = self.y + (self.height - ch) / 2
        cx, cy = x + cw / 2, y + ch / 2
        with self.canvas:
            Color(0, 0, 0, 0.55)
            RoundedRectangle(pos=(x - dp(3), y - dp(3)), size=(cw + dp(6), ch + dp(6)),
                             radius=[dp(12)])
            if self.mode == "red":
                Color(*RED)
                RoundedRectangle(pos=(x, y), size=(cw, ch), radius=[dp(10)])
                Color(1, 1, 1, 1)
                draw_suit(0, cx, cy, cw * 0.62)
            elif self.mode == "black":
                Color(0.05, 0.05, 0.07, 1)
                RoundedRectangle(pos=(x, y), size=(cw, ch), radius=[dp(10)])
                Color(1, 1, 1, 1)
                draw_suit(2, cx, cy, cw * 0.62)
            elif self.mode == "face" and self.card:
                Color(*CARD_BG)
                RoundedRectangle(pos=(x, y), size=(cw, ch), radius=[dp(10)])
                col = RED if is_red(self.card) else INK
                Color(*col)
                draw_suit(self.card[1], cx, cy - ch * 0.04, cw * 0.62)
                tex = text_texture(RANK_LABEL[self.card[0]], sp(26), col)
                Color(1, 1, 1, 1)
                Rectangle(texture=tex, size=tex.size,
                          pos=(x + dp(6), y + ch - tex.height - dp(4)))
            else:  # back
                Color(0.45, 0.08, 0.12, 1)
                RoundedRectangle(pos=(x, y), size=(cw, ch), radius=[dp(10)])
                Color(*GOLD)
                Line(rounded_rectangle=(x + dp(6), y + dp(6), cw - dp(12), ch - dp(12),
                                        dp(7)), width=dp(1.4))
                draw_suit(0, cx, cy, cw * 0.5)
                tex = text_texture("?", sp(30), GOLD)
                Color(1, 1, 1, 1)
                Rectangle(texture=tex, size=tex.size,
                          pos=(cx - tex.width / 2, y + ch * 0.12))


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
                Color(0.30, 0.05, 0.10, 1)
                tcol = (0.85, 0.65, 0.65, 1)
            draw_suit(0, cx, cy, s)
            tex = text_texture(self.label, sp(10.5), tcol)
            Color(1, 1, 1, 1)
            Rectangle(texture=tex, size=tex.size,
                      pos=(cx - tex.width / 2, cy - tex.height / 2 - h * 0.05))


class LadderBar(BoxLayout):
    """Risikoleiter x1 bis x64 aus Herzen; die aktuelle Stufe blinkt."""

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
        r = min(w * 0.40, h * 0.34)
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
            Rectangle(texture=tex, size=tex.size, pos=(cx - tex.width / 2, y + h * 0.04))


# --------------------------------------------------------- Bausteine ----
class TitleBar(BoxLayout):
    def __init__(self, text, **kw):
        super().__init__(**kw)
        self.add_widget(Label(text=text, font_size=sp(24), bold=True, color=GOLD,
                              outline_width=2, outline_color=(0.25, 0.05, 0.05, 1)))
        self.bind(pos=self.redraw, size=self.redraw)

    def redraw(self, *_):
        self.canvas.before.clear()
        x, y = self.pos
        w, h = self.size
        with self.canvas.before:
            Color(0.35, 0.05, 0.10, 1)
            RoundedRectangle(pos=(x, y + h * 0.08), size=(w, h * 0.84), radius=[dp(8)])
            Color(*GOLD)
            Line(rounded_rectangle=(x, y + h * 0.08, w, h * 0.84, dp(8)), width=dp(1.3))
            for cx, suit in ((x + h * 0.55, 0), (x + w - h * 0.55, 0),
                             (x + h * 1.2, 1), (x + w - h * 1.2, 3)):
                Color(*(RED if suit < 2 else (0.1, 0.1, 0.12, 1)))
                draw_suit(suit, cx, y + h / 2, h * 0.5)


class PayTable(GridLayout):
    def __init__(self, **kw):
        super().__init__(cols=2, **kw)
        self.labels = {}
        for name, mult in PAYTABLE:
            lab = Label(text="%s  x%d" % (name, mult), font_size=sp(12.5),
                        color=(0.85, 0.9, 0.85, 1))
            self.labels[name] = lab
            self.add_widget(lab)

    def highlight(self, name):
        for n, lab in self.labels.items():
            lab.color = GOLD if n == name else (0.85, 0.9, 0.85, 1)
            lab.bold = n == name


def styled_button(text, color, font=17, **kw):
    return Button(text=text, bold=True, font_size=sp(font), background_normal="",
                  background_down="", background_color=color,
                  color=(1, 1, 1, 1) if sum(color[:3]) < 1.6 else INK, **kw)


class Machine(BoxLayout):
    def __init__(self, store_path, **kw):
        super().__init__(orientation="vertical", padding=dp(14), spacing=dp(6), **kw)
        self.store_path = store_path
        self.game = Game()
        self._load()
        self.sfx = Sfx()
        self._busy = False
        self.frozen = None
        self._mode = None

        with self.canvas.before:
            Color(*BG)
            self._bg = Rectangle(pos=self.pos, size=self.size)
            Color(*GOLD)
            self._frame = Line(rounded_rectangle=(0, 0, 10, 10, 10), width=dp(3))
            Color(0.55, 0.40, 0.08, 1)
            self._frame2 = Line(rounded_rectangle=(0, 0, 10, 10, 8), width=dp(1))
        with self.canvas.after:
            self._flash_color = Color(1, 1, 1, 0)
            self._flash_rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._layout_bg, size=self._layout_bg)

        # Anzeigen
        top = BoxLayout(size_hint_y=None, height=dp(62), spacing=dp(8))
        self.credit_led = LedDisplay(digits=6)
        self.stake_led = LedDisplay(digits=3)
        self.win_led = LedDisplay(digits=6)
        for cap, led, hint in (("PUNKTE", self.credit_led, 1.6), ("EINSATZ", self.stake_led, 0.8),
                               ("GEWINN", self.win_led, 1.6)):
            col = BoxLayout(orientation="vertical", size_hint_x=hint)
            col.add_widget(Label(text=cap, font_size=sp(11), bold=True, color=GOLD,
                                 size_hint_y=None, height=dp(16)))
            col.add_widget(led)
            top.add_widget(col)
        self.add_widget(top)

        self.add_widget(TitleBar("KARTENWALZEN", size_hint_y=None, height=dp(44)))

        self.ladder = LadderBar(size_hint_y=None, height=dp(42))
        self.add_widget(self.ladder)

        self.msg = Label(text="", font_size=sp(15), color=(0.95, 0.95, 0.85, 1),
                         size_hint_y=None, height=dp(26))
        self.add_widget(self.msg)

        # Walzenfenster
        window = BoxLayout(spacing=dp(6), padding=[dp(8), dp(8)], size_hint_y=None,
                           height=dp(138))
        with window.canvas.before:
            Color(0.0, 0.0, 0.0, 1)
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
        self.risk_panel = BoxLayout(orientation="vertical", spacing=dp(4))
        self.risk_info = Label(text="", font_size=sp(15), bold=True, color=GOLD,
                               size_hint_y=None, height=dp(26))
        row = BoxLayout(spacing=dp(10))
        self.btn_red = styled_button("ROT", RED, 20)
        self.btn_black = styled_button("SCHWARZ", (0.10, 0.10, 0.13, 1), 18)
        self.btn_red.bind(on_release=lambda *_: self.on_guess(True))
        self.btn_black.bind(on_release=lambda *_: self.on_guess(False))
        self.risk_card = RiskCard()
        row.add_widget(self.btn_red)
        row.add_widget(self.risk_card)
        row.add_widget(self.btn_black)
        self.risk_panel.add_widget(self.risk_info)
        self.risk_panel.add_widget(row)
        self.add_widget(self.middle)

        # Steuerung
        row1 = BoxLayout(spacing=dp(8), size_hint_y=None, height=dp(44))
        self.btn_minus = styled_button("Einsatz -", (0.22, 0.26, 0.34, 1), 15)
        self.btn_plus = styled_button("Einsatz +", (0.22, 0.26, 0.34, 1), 15)
        self.btn_sound = styled_button("Ton an", (0.22, 0.26, 0.34, 1), 15)
        self.btn_minus.bind(on_release=lambda *_: self.on_stake(-1))
        self.btn_plus.bind(on_release=lambda *_: self.on_stake(1))
        self.btn_sound.bind(on_release=lambda *_: self.on_sound())
        for b in (self.btn_minus, self.btn_plus, self.btn_sound):
            row1.add_widget(b)
        self.add_widget(row1)

        row2 = BoxLayout(spacing=dp(8), size_hint_y=None, height=dp(60))
        self.btn_main = styled_button("START", (0.10, 0.58, 0.26, 1), 18)
        self.btn_risk = styled_button("RISIKO", (0.88, 0.50, 0.08, 1), 18)
        self.btn_take = styled_button("NEHMEN", GOLD, 18)
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

    def on_risk(self):
        if not self._busy and self.game.risk_start():
            self.risk_card.set_mode("back")
            self.sfx.play("risk_start")
            self.refresh()

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
                elif g.state == "idle" and g.win == 0 and g.win_name is None and g.cards[0]:
                    self.sfx.play("lose", 0.5)
                self.refresh()
                return False
            return True

        Clock.schedule_interval(step, 0.06)

    # --- Risiko mit Spannung ----------------------------------------------
    def on_guess(self, red):
        g = self.game
        if self._busy or g.state != "risk":
            return
        snap = {"win": g.win, "rung": g.rung, "credit": g.credit}
        won = g.risk_guess(red)
        card = g.last_card
        final_red = is_red(card)
        self._busy = True
        self.frozen = snap
        self.refresh()
        self.msg.text = "Rot oder Schwarz ...?"
        self.risk_info.text = "Es wird gezogen ..."

        delays = [0.07] * 8 + [0.10] * 4 + [0.15] * 3 + [0.22] * 2 + [0.32, 0.46, 0.70]
        n = len(delays)
        start_red = final_red if (n - 1) % 2 == 0 else not final_red

        def flip(i):
            if i >= n:
                reveal()
                return
            face_red = start_red if i % 2 == 0 else not start_red
            self.risk_card.set_mode("red" if face_red else "black")
            self.sfx.play("risk_tick", 0.5 + 0.5 * i / n)
            Clock.schedule_once(lambda dt: flip(i + 1), delays[i])

        def reveal():
            self.risk_card.set_mode("face", card)
            self.msg.text = g.message
            self.risk_info.text = "Treffer!" if won else "Daneben!"
            if won:
                self.sfx.play("risk_win")
                self.flash((1.0, 0.85, 0.3))
            else:
                self.sfx.play("risk_lose")
                self.flash((0.9, 0.1, 0.1))
            Clock.schedule_once(finish, 1.5)

        def finish(dt):
            self.frozen = None
            self._busy = False
            self._save()
            self.refresh()

        flip(0)

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
        self.ladder.show(view["rung"], g.state in ("risk", "result") and view["win"] > 0
                         or self.frozen is not None)

        in_risk = g.state == "risk" or self.frozen is not None
        mode = "risk" if in_risk else "pay"
        if mode != self._mode:
            self._mode = mode
            self.middle.clear_widgets()
            self.middle.add_widget(self.risk_panel if in_risk else self.paytable)
        if in_risk and not self.frozen:
            self.risk_info.text = "Gewinn %d  ->  bei Treffer %d" % (g.win, g.win * 2)
        for b in (self.btn_red, self.btn_black):
            b.disabled = bool(self.frozen)

        self.btn_risk.disabled = g.state != "result"
        self.btn_take.disabled = g.state not in ("result", "risk")
        self.btn_main.disabled = g.state in ("result", "risk")
        self.btn_main.text = "ZIEHUNG" if g.state == "held" else (
            "NEU STARTEN" if g.credit < g.stake else "START")
        self.btn_minus.disabled = self.btn_plus.disabled = g.state != "idle"


class KartenwalzenApp(App):
    title = "Kartenwalzen"

    def build(self):
        if os.environ.get("KARTEN_TEST_FEHLER"):
            raise RuntimeError("Testfehler fuer die Fehleranzeige")
        path = os.path.join(self.user_data_dir, "stand.json")
        return Machine(store_path=path)


def run():
    KartenwalzenApp().run()
