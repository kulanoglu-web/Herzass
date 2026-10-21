import random
import unittest

from logic import Game, evaluate, new_deck, PAY, LADDER


def c(*pairs):
    return list(pairs)


class EvalTest(unittest.TestCase):
    def test_hands(self):
        self.assertEqual(evaluate(c((10, 0), (11, 0), (12, 0), (13, 0), (14, 0))), ("Royal Flush", 100))
        self.assertEqual(evaluate(c((7, 1), (8, 1), (9, 1), (10, 1), (11, 1))), ("Straight Flush", 50))
        self.assertEqual(evaluate(c((9, 0), (9, 1), (9, 2), (9, 3), (14, 0))), ("Vierling", 25))
        self.assertEqual(evaluate(c((9, 0), (9, 1), (9, 2), (12, 3), (12, 0))), ("Full House", 10))
        self.assertEqual(evaluate(c((7, 2), (9, 2), (11, 2), (12, 2), (14, 2))), ("Flush", 7))
        self.assertEqual(evaluate(c((8, 0), (9, 1), (10, 2), (11, 3), (12, 0))), ("Strasse", 5))
        self.assertEqual(evaluate(c((8, 0), (8, 1), (8, 2), (11, 3), (14, 0))), ("Drilling", 3))
        self.assertEqual(evaluate(c((7, 0), (7, 1), (13, 2), (13, 3), (14, 0))), ("Zwei Paare", 2))
        self.assertEqual(evaluate(c((11, 0), (11, 1), (8, 2), (9, 3), (14, 0))), ("Paar (Bube+)", 1))

    def test_low_pair_and_nothing(self):
        self.assertEqual(evaluate(c((7, 0), (7, 1), (8, 2), (10, 3), (14, 0))), (None, 0))
        self.assertEqual(evaluate(c((7, 0), (9, 1), (11, 2), (12, 3), (14, 0))), (None, 0))


class GameTest(unittest.TestCase):
    def test_deck(self):
        d = new_deck()
        self.assertEqual(len(d), 32)
        self.assertEqual(len(set(d)), 32)

    def test_round_flow(self):
        g = Game(credit=100, stake=10, rng=random.Random(1))
        self.assertTrue(g.start())
        self.assertEqual(g.credit, 90)
        self.assertEqual(g.state, "held")
        g.toggle_hold(0)
        kept = g.cards[0]
        g.draw()
        self.assertEqual(g.cards[0], kept)
        self.assertIn(g.state, ("idle", "result"))

    def test_no_start_without_credit(self):
        g = Game(credit=5, stake=10)
        self.assertFalse(g.start())

    def test_take_adds_win(self):
        g = Game(credit=100, stake=10)
        g.state, g.win = "result", 30
        self.assertTrue(g.take())
        self.assertEqual(g.credit, 130)
        self.assertEqual(g.state, "idle")

    def test_risk_null_oder_mehr(self):
        class R:
            def __init__(self, v):
                self.v = v

            def random(self):
                return self.v
        g = Game(credit=100, stake=10, rng=R(0.1))      # 0.1 -> mehr
        g.state, g.win = "result", 20
        self.assertTrue(g.risk_play())
        self.assertEqual((g.win, g.state, g.rung), (40, "risk", 1))
        g.rng = R(0.9)                                  # 0.9 -> null
        self.assertFalse(g.risk_play())
        self.assertEqual((g.win, g.state, g.credit), (0, "idle", 100))

    def test_risk_nicht_moeglich(self):
        g = Game(credit=100, stake=10)
        self.assertIsNone(g.risk_play())
        g.state, g.win = "held", 10
        self.assertIsNone(g.risk_play())

    def test_top_rung_pays_out(self):
        class Win:
            def random(self):
                return 0.0
        g = Game(credit=0, stake=10, rng=Win())
        g.state, g.win = "result", 10
        for _ in range(len(LADDER) - 1):
            g.risk_play()
        self.assertEqual(g.state, "idle")
        self.assertEqual(g.credit, 10 * 2 ** (len(LADDER) - 1))

    def test_simulation_conserves_credit_rules(self):
        rng = random.Random(42)
        g = Game(credit=1000, stake=10, rng=rng)
        for _ in range(2000):
            if g.credit < g.stake:
                break
            g.start()
            for i in range(5):
                if rng.random() < 0.4:
                    g.toggle_hold(i)
            g.draw()
            if g.state == "result":
                g.take()
            self.assertGreaterEqual(g.credit, 0)


if __name__ == "__main__":
    unittest.main()
