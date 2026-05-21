import math
import settings as cfg
from utils.helpers import planet_id, planet_name, snap_to_grid


class Planet:
    """A procedurally generated planet at a fixed position in the infinite universe."""

    def __init__(self, x, y):
        # Snap to grid so planets are deterministic at grid positions
        gx = snap_to_grid(x, cfg.PLANET_SPACING)
        gy = snap_to_grid(y, cfg.PLANET_SPACING)
        self.x = float(gx)
        self.y = float(gy)
        self.pid = planet_id(gx, gy)
        self.name = planet_name(gx, gy)

        # Deterministic properties from seed
        import random
        rng = random.Random(self.pid)
        self.planet_type = rng.choice(cfg.PLANET_TYPES)
        self.radius = rng.uniform(80, 200)

        # Generate prices based on type
        self.prices = {}
        self.stock = {}
        modifiers = cfg.PRICE_MODIFIERS[self.planet_type]
        for comm_id, comm in cfg.COMMODITIES.items():
            mod = modifiers.get(comm_id, 1.0)
            base = comm["base_price"]
            buy_price = max(2, int(base * mod * rng.uniform(0.9, 1.1)))
            sell_price = max(1, int(buy_price * 0.90))
            self.prices[comm_id] = {"buy": buy_price, "sell": sell_price}
            self.stock[comm_id] = rng.randint(100, 999)

        # Available upgrades (2-3 random)
        all_upgrades = list(cfg.UPGRADES.keys())
        rng.shuffle(all_upgrades)
        self.upgrades_available = all_upgrades[:rng.randint(2, 3)]

        # Maps for sale
        self.maps_for_sale = ["map_basic"]
        if rng.random() < 0.5:
            self.maps_for_sale.append("map_sector")
        if rng.random() < 0.25:
            self.maps_for_sale.append("map_advanced")

    def buy_price(self, commodity_id):
        return self.prices.get(commodity_id, {}).get("buy", 999)

    def sell_price(self, commodity_id):
        return self.prices.get(commodity_id, {}).get("sell", 1)

    def has_stock(self, commodity_id, amount=1):
        return self.stock.get(commodity_id, 0) >= amount

    def remove_stock(self, commodity_id, amount):
        if self.has_stock(commodity_id, amount):
            self.stock[commodity_id] -= amount

    def add_stock(self, commodity_id, amount):
        self.stock[commodity_id] = self.stock.get(commodity_id, 0) + amount
