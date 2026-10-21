"""Spiellogik fuer "Kartenwalzen" - ein Walzen-Kartenspiel mit Halten und Risikoleiter.

Reine Python-Logik ohne Oberflaeche, damit sie sich einfach testen laesst.
Nur Spielgeld, kein Echtgeld.
"""
import random
from collections import Counter

# Karten: Rang 7..14 (14 = Ass), Farbe 0=Herz 1=Karo 2=Pik 3=Kreuz
RANKS = list(range(7, 15))
SUITS = [0, 1, 2, 3]
RANK_LABEL = {7: "7", 8: "8", 9: "9", 10: "10", 11: "B", 12: "D", 13: "K", 14: "A"}
SUIT_NAME = {0: "Herz", 1: "Karo", 2: "Pik", 3: "Kreuz"}

# (Name, Faktor auf den Einsatz) - vom hoechsten zum niedrigsten
PAYTABLE = [
    ("Royal Flush", 100),
    ("Straight Flush", 50),
    ("Vierling", 25),
    ("Full House", 10),
    ("Flush", 7),
    ("Strasse", 5),
    ("Drilling", 3),
    ("Zwei Paare", 2),
    ("Paar (Bube+)", 1),
]
PAY = dict(PAYTABLE)

# Risikoleiter: nach jedem richtigen Tipp verdoppelt sich der Gewinn
LADDER = [1, 2, 4, 8, 16, 32, 64]
# Risiko-Lauflicht: gleich grosse Felder, links NULL, rechts die andere Seite (x2).
RISK_CELLS = [0, 0, 0, 2, 2, 2]
STAKES = [5, 10, 20, 50]
START_CREDIT = 200


def new_deck(rng=random):
    deck = [(r, s) for r in RANKS for s in SUITS]
    rng.shuffle(deck)
    return deck


def is_red(card):
    return card[1] in (0, 1)


def evaluate(cards):
    """Gibt (Name, Faktor) zurueck, bei keinem Gewinn (None, 0)."""
    ranks = sorted(c[0] for c in cards)
    counts = sorted(Counter(ranks).values(), reverse=True)
    flush = len({c[1] for c in cards}) == 1
    straight = len(set(ranks)) == 5 and ranks[-1] - ranks[0] == 4

    if straight and flush:
        name = "Royal Flush" if ranks[0] == 10 else "Straight Flush"
    elif counts[0] == 4:
        name = "Vierling"
    elif counts[:2] == [3, 2]:
        name = "Full House"
    elif flush:
        name = "Flush"
    elif straight:
        name = "Strasse"
    elif counts[0] == 3:
        name = "Drilling"
    elif counts[:2] == [2, 2]:
        name = "Zwei Paare"
    elif counts[0] == 2:
        pair_rank = [r for r, n in Counter(ranks).items() if n == 2][0]
        name = "Paar (Bube+)" if pair_rank >= 11 else None
    else:
        name = None
    return (name, PAY[name]) if name else (None, 0)


class Game:
    """Zustandsautomat: idle -> held -> result -> (risk, risk, ...) -> idle"""

    def __init__(self, credit=START_CREDIT, stake=10, rng=None):
        self.rng = rng or random.Random()
        self.credit = credit
        self.stake = stake
        self.state = "idle"
        self.cards = [None] * 5
        self.held = [False] * 5
        self.deck = []
        self.win = 0          # aktueller Gewinn (kann in der Risikoleiter wachsen)
        self.win_name = None
        self.rung = 0         # Stufe auf der Risikoleiter
        self.message = "Einsatz waehlen und START druecken"

    # --- Einsatz ---------------------------------------------------------
    def change_stake(self, direction):
        if self.state != "idle":
            return
        i = STAKES.index(self.stake) + direction
        self.stake = STAKES[max(0, min(len(STAKES) - 1, i))]

    # --- Spielablauf -----------------------------------------------------
    def start(self):
        """Erste Ausgabe: fuenf Karten, danach duerfen Walzen gehalten werden."""
        if self.state != "idle":
            return False
        if self.credit < self.stake:
            self.message = "Zu wenig Punkte - bitte neu starten"
            return False
        self.credit -= self.stake
        self.deck = new_deck(self.rng)
        self.cards = [self.deck.pop() for _ in range(5)]
        self.held = [False] * 5
        self.win = 0
        self.win_name = None
        self.rung = 0
        self.state = "held"
        self.message = "Walzen halten, dann ZIEHUNG"
        return True

    def toggle_hold(self, i):
        if self.state != "held":
            return
        self.held[i] = not self.held[i]

    def draw(self):
        """Nicht gehaltene Walzen werden einmal neu gezogen und ausgewertet."""
        if self.state != "held":
            return False
        for i in range(5):
            if not self.held[i]:
                self.cards[i] = self.deck.pop()
        name, mult = evaluate(self.cards)
        self.win_name = name
        self.win = mult * self.stake
        if self.win:
            self.state = "result"
            self.message = "%s! %d Punkte - NEHMEN oder RISIKO" % (name, self.win)
        else:
            self.state = "idle"
            self.message = "Leider nichts. Naechste Runde?"
        return True

    # --- Risikoleiter ----------------------------------------------------
    def take(self):
        if self.state not in ("result", "risk") or self.win <= 0:
            return False
        self.credit += self.win
        self.message = "%d Punkte uebernommen" % self.win
        self.win = 0
        self.rung = 0
        self.state = "idle"
        return True

    def risk_start(self):
        """Prueft, ob ein Risiko moeglich ist (der Spieler stoppt danach selbst das Lauflicht)."""
        return self.state in ("result", "risk") and self.win > 0

    def risk_resolve(self, cell):
        """Das Lauflicht wurde auf Feld `cell` gestoppt. NULL = Gewinn weg, sonst wird
        der Gewinn mit dem Wert des Feldes (x2 oder x4) vervielfacht.
        Gibt den Faktor zurueck (0 = verloren) oder None (nicht moeglich)."""
        if not self.risk_start():
            return None
        mult = RISK_CELLS[cell]
        if mult == 0:
            self.message = "NULL - Gewinn verloren"
            self.win = 0
            self.rung = 0
            self.state = "idle"
            return 0
        self.win *= mult
        self.rung += 1
        if self.rung >= len(LADDER) - 1:
            self.credit += self.win
            self.message = "Hoechste Stufe! %d Punkte uebernommen" % self.win
            self.win = 0
            self.rung = 0
            self.state = "idle"
        else:
            self.state = "risk"
            self.message = "MEHR x%d! Jetzt %d Punkte" % (mult, self.win)
        return mult

    def reset(self):
        self.credit = START_CREDIT
        self.stake = 10
        self.state = "idle"
        self.win = 0
        self.rung = 0
        self.cards = [None] * 5
        self.held = [False] * 5
        self.message = "Neu gestartet"
