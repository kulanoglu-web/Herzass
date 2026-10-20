"""Kartenwalzen - Walzen-Kartenspiel mit Halten, Ziehung und Risikoleiter.

Eigenes Spiel mit eigener Grafik. Nur Spielgeld, kein Echtgeld.
Oberflaeche: Kivy (laeuft am Desktop und als Android-APK).
"""
import json
import os
import random

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import (Color, Ellipse, Line, Quad, Rectangle, RoundedRectangle,
                           Triangle)
from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.widget import Widget

from logic import (LADDER, PAYTABLE, RANK_LABEL, RANKS, SUITS, Game, is_red)

FELT = (0.04, 0.22, 0.16, 1)
GOLD = (0.95, 0.78, 0.25, 1)
RED = (0.82, 0.10, 0.14, 1)
INK = (0.08, 0.08, 0.10, 1)
CARD_BG = (0.98, 0.97, 0.92, 1)

Window.clearcolor = FELT


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


class CardWidget(Widget):
    """Eine Walze: zeigt eine Karte, 'HALTEN'-Rahmen, oder Kartenrueckseite."""

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
        with self.canvas:
            Color(*GOLD) if self.held else Color(0.0, 0.0, 0.0, 0.5)
            RoundedRectangle(pos=(x - dp(3), y - dp(3)),
                             size=(w + dp(6), h + dp(6)), radius=[dp(10)])
            card = self.blur if self.spinning else self.card
            if card is None:
                # Rueckseite
                Color(0.45, 0.08, 0.12, 1)
                RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(8)])
                Color(*GOLD)
                Line(rounded_rectangle=(x + dp(6), y + dp(6), w - dp(12), h - dp(12),
                                        dp(6)), width=dp(1.2))
                draw_suit(0, x + w / 2, y + h / 2, w * 0.45)
                return
            Color(*CARD_BG)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(8)])
            rank, suit = card
            Color(*(RED if is_red(card) else INK))
            draw_suit(suit, x + w / 2, y + h * 0.40, w * 0.62)
        # Rang als Label-Textur ueber Canvas
        from kivy.core.text import Label as CoreLabel
        lab = CoreLabel(text=RANK_LABEL[rank] if card else "", font_size=sp(30),
                        bold=True, color=(RED if is_red(card) else INK))
        lab.refresh()
        tex = lab.texture
        with self.canvas:
            Color(1, 1, 1, 1)
            Rectangle(texture=tex, size=tex.size,
                      pos=(x + dp(6), y + h - tex.height - dp(4)))


class PayTable(BoxLayout):
    def __init__(self, **kw):
        super().__init__(orientation="vertical", **kw)
        self.rows = {}
        for name, mult in PAYTABLE:
            lab = Label(text="%s  x%d" % (name, mult), font_size=sp(12),
                        color=(0.85, 0.9, 0.85, 1))
            self.rows[name] = lab
            self.add_widget(lab)

    def highlight(self, name):
        for n, lab in self.rows.items():
            lab.color = GOLD if n == name else (0.85, 0.9, 0.85, 1)
            lab.bold = n == name


class LadderBar(BoxLayout):
    """Risikoleiter: x1 bis x64 als Reihe von Herzen-Feldern."""

    def __init__(self, **kw):
        super().__init__(orientation="horizontal", spacing=dp(4), **kw)
        self.cells = []
        for m in LADDER:
            lab = Label(text="x%d" % m, font_size=sp(13), bold=True)
            with lab.canvas.before:
                lab._c = Color(0.1, 0.3, 0.24, 1)
                lab._r = RoundedRectangle(pos=lab.pos, size=lab.size, radius=[dp(6)])
            lab.bind(pos=self._upd, size=self._upd)
            self.cells.append(lab)
            self.add_widget(lab)

    @staticmethod
    def _upd(lab, *_):
        lab._r.pos, lab._r.size = lab.pos, lab.size

    def show(self, rung, active):
        for i, lab in enumerate(self.cells):
            if active and i == rung:
                lab._c.rgba = GOLD
                lab.color = INK
            elif active and i < rung:
                lab._c.rgba = (0.2, 0.5, 0.35, 1)
                lab.color = (1, 1, 1, 1)
            else:
                lab._c.rgba = (0.1, 0.3, 0.24, 1)
                lab.color = (0.7, 0.8, 0.75, 1)


def styled_button(text, color, **kw):
    b = Button(text=text, bold=True, font_size=sp(17), background_normal="",
               background_down="", background_color=color,
               color=(1, 1, 1, 1) if sum(color[:3]) < 1.6 else INK, **kw)
    return b


class Machine(BoxLayout):
    def __init__(self, store_path, **kw):
        super().__init__(orientation="vertical", padding=dp(10), spacing=dp(8), **kw)
        self.store_path = store_path
        self.game = Game()
        self._load()
        self._spin_event = None
        self._busy = False

        # Kopfzeile
        top = BoxLayout(size_hint_y=None, height=dp(56))
        self.credit_lbl = Label(font_size=sp(22), bold=True, color=GOLD, halign="left")
        self.stake_lbl = Label(font_size=sp(18), color=(1, 1, 1, 1))
        self.win_lbl = Label(font_size=sp(22), bold=True, color=(1, 1, 1, 1))
        top.add_widget(self.credit_lbl)
        top.add_widget(self.stake_lbl)
        top.add_widget(self.win_lbl)
        self.add_widget(top)

        self.ladder = LadderBar(size_hint_y=None, height=dp(34))
        self.add_widget(self.ladder)

        self.msg = Label(text="", font_size=sp(16), color=(0.95, 0.95, 0.85, 1),
                         size_hint_y=None, height=dp(34))
        self.add_widget(self.msg)

        # Walzen + Halten-Tasten
        reels = BoxLayout(spacing=dp(8), size_hint_y=None, height=dp(150))
        self.reels = [CardWidget() for _ in range(5)]
        for r in self.reels:
            reels.add_widget(r)
        self.add_widget(reels)

        holds = BoxLayout(spacing=dp(8), size_hint_y=None, height=dp(48))
        self.hold_btns = []
        for i in range(5):
            b = ToggleButton(text="HALTEN", font_size=sp(12), bold=True,
                             background_normal="", background_down="",
                             background_color=(0.35, 0.1, 0.12, 1))
            b.bind(on_release=lambda btn, i=i: self.on_hold(i))
            self.hold_btns.append(b)
            holds.add_widget(b)
        self.add_widget(holds)

        self.paytable = PayTable()
        self.add_widget(self.paytable)

        # Steuerung
        row1 = BoxLayout(spacing=dp(8), size_hint_y=None, height=dp(54))
        self.btn_minus = styled_button("Einsatz -", (0.25, 0.3, 0.35, 1))
        self.btn_plus = styled_button("Einsatz +", (0.25, 0.3, 0.35, 1))
        self.btn_minus.bind(on_release=lambda *_: self.on_stake(-1))
        self.btn_plus.bind(on_release=lambda *_: self.on_stake(1))
        row1.add_widget(self.btn_minus)
        row1.add_widget(self.btn_plus)
        self.add_widget(row1)

        self.risk_row = BoxLayout(spacing=dp(8), size_hint_y=None, height=dp(58))
        self.btn_red = styled_button("ROT", RED)
        self.btn_black = styled_button("SCHWARZ", (0.1, 0.1, 0.12, 1))
        self.btn_red.bind(on_release=lambda *_: self.on_guess(True))
        self.btn_black.bind(on_release=lambda *_: self.on_guess(False))
        self.risk_row.add_widget(self.btn_red)
        self.risk_row.add_widget(self.btn_black)
        self.add_widget(self.risk_row)

        row2 = BoxLayout(spacing=dp(8), size_hint_y=None, height=dp(64))
        self.btn_main = styled_button("START", (0.1, 0.55, 0.25, 1))
        self.btn_risk = styled_button("RISIKO", (0.85, 0.5, 0.1, 1))
        self.btn_take = styled_button("NEHMEN", GOLD)
        self.btn_main.bind(on_release=lambda *_: self.on_main())
        self.btn_risk.bind(on_release=lambda *_: self.on_risk())
        self.btn_take.bind(on_release=lambda *_: self.on_take())
        for b in (self.btn_main, self.btn_risk, self.btn_take):
            row2.add_widget(b)
        self.add_widget(row2)

        hint = Label(text="Nur Spielgeld - kein Echtgeld", font_size=sp(11),
                     color=(0.7, 0.8, 0.75, 1), size_hint_y=None, height=dp(18))
        self.add_widget(hint)
        self.refresh()

    # --- Speichern -------------------------------------------------------
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

    # --- Aktionen --------------------------------------------------------
    def on_stake(self, d):
        self.game.change_stake(d)
        self.refresh()

    def on_hold(self, i):
        if self._busy:
            return
        self.game.toggle_hold(i)
        self.refresh()

    def on_main(self):
        g = self.game
        if self._busy:
            return
        if g.state == "idle":
            if g.credit < g.stake:
                g.reset()
                self.refresh()
                return
            if g.start():
                self.animate(range(5))
        elif g.state == "held":
            changing = [i for i in range(5) if not g.held[i]]
            g.draw()
            self.animate(changing)

    def on_risk(self):
        if not self._busy and self.game.risk_start():
            self.refresh()

    def on_take(self):
        if not self._busy and self.game.take():
            self._save()
            self.refresh()

    def on_guess(self, red):
        if self._busy:
            return
        result = self.game.risk_guess(red)
        if result is None:
            return
        self._save()
        self.refresh()

    # --- Walzen-Animation ------------------------------------------------
    def animate(self, indices):
        indices = list(indices)
        self._busy = True
        stop_at = {i: 6 + 4 * n for n, i in enumerate(indices)}
        tick = {"n": 0}
        final = list(self.game.cards)

        def step(dt):
            tick["n"] += 1
            for i in indices:
                r = self.reels[i]
                if tick["n"] < stop_at[i]:
                    r.blur = (random.choice(RANKS), random.choice(SUITS))
                    r.set(final[i], held=False, spinning=True)
                elif tick["n"] == stop_at[i]:
                    r.set(final[i], held=self.game.held[i], spinning=False)
            if tick["n"] >= max(stop_at.values()):
                self._busy = False
                self._save()
                self.refresh()
                return False
            return True

        Clock.schedule_interval(step, 0.06)

    # --- Anzeige ---------------------------------------------------------
    def refresh(self):
        g = self.game
        self.credit_lbl.text = "Punkte: %d" % g.credit
        self.stake_lbl.text = "Einsatz: %d" % g.stake
        self.win_lbl.text = ("Gewinn: %d" % g.win) if g.win else ""
        self.msg.text = g.message
        if not self._busy:
            for i, r in enumerate(self.reels):
                r.set(g.cards[i], held=g.held[i] and g.state == "held")
        for i, b in enumerate(self.hold_btns):
            b.state = "down" if g.held[i] else "normal"
            b.background_color = (0.75, 0.55, 0.1, 1) if g.held[i] else (0.35, 0.1, 0.12, 1)
            b.disabled = g.state != "held"
        self.paytable.highlight(g.win_name)
        self.ladder.show(g.rung, g.state in ("risk", "result") and g.win > 0)

        in_risk = g.state == "risk"
        self.risk_row.opacity = 1 if in_risk else 0
        self.risk_row.disabled = not in_risk
        self.risk_row.height = dp(58) if in_risk else 0
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
