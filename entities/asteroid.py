import hashlib
import random
import settings as cfg


class Asteroid:
    """A mineable asteroid placed deterministically in space.
    Reward is either flat credits or a commodity drop, decided by seed."""

    def __init__(self, x, y):
        # Grid coords give a stable identity; jitter within the cell hides the grid
        self.aid = hashlib.md5(f"ast:{x},{y}".encode()).hexdigest()[:10]
        rng = random.Random(f"ast:{x}:{y}")

        jitter = cfg.ASTEROID_SPACING * 0.40
        self.x = float(x) + rng.uniform(-jitter, jitter)
        self.y = float(y) + rng.uniform(-jitter, jitter)

        self.radius = rng.uniform(10, 22)

        # Asteroids are supplemental income — trade is the main profit source.
        # 40% credits drop, 60% commodity drop (weighted by base price so cheap commodities more common)
        if rng.random() < 0.40:
            self.reward_kind = "credits"
            self.reward_credits = rng.randint(40, 120)
            self.reward_commodity = None
            self.reward_qty = 0
        else:
            self.reward_kind = "commodity"
            comms = list(cfg.COMMODITIES.keys())
            # Weight inversely by base_price so cheaper commodities drop more often
            weights = [1.0 / cfg.COMMODITIES[c]["base_price"] for c in comms]
            total = sum(weights)
            r = rng.random() * total
            cum = 0
            chosen = comms[0]
            for c, w in zip(comms, weights):
                cum += w
                if r <= cum:
                    chosen = c
                    break
            self.reward_commodity = chosen
            self.reward_qty = rng.randint(1, 2)
            self.reward_credits = 0
