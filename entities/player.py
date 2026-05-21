import math
import settings as cfg


class Player:
    """Player ship with newtonian physics, inventory, and upgrades."""

    def __init__(self, x=0, y=0):
        # Position & velocity
        self.x = float(x)
        self.y = float(y)
        self.vx = 0.0
        self.vy = 0.0
        self.angle = 0.0          # degrees, 0 = right, 90 = down

        # Ship stats
        self.fuel = cfg.START_FUEL
        self.max_fuel = cfg.MAX_FUEL
        self.hp = float(cfg.START_HP)
        self.max_hp = cfg.MAX_HP
        self.max_cargo = cfg.MAX_CARGO_BASE
        self.acceleration = cfg.BASE_ACCELERATION
        self.turn_rate = cfg.BASE_TURN_RATE

        # Economy
        self.credits = cfg.START_CREDITS
        self.inventory = {}        # {commodity_id: {"qty": N, "buy_price": P}}

        # Knowledge
        self.known_planets = {}    # {planet_id: Planet}
        self.known_planet_ids = set()

        # Upgrades
        self.upgrades = set()
        self.has_retro = True
        self.has_hyperdrive = False

        # Docking
        self.docked_at = None      # planet_id or None

        # Exhaust trail
        self.trail = []            # list of (x, y) tuples
        self.thrusting = False

        # Warp state
        self.warp_cooldown = 0.0
        self.warp_target_x = 0.0
        self.warp_target_y = 0.0

    def cargo_used(self):
        total = 0
        for item in self.inventory.values():
            comm_id = item.get("commodity", "")
            qty = item.get("qty", 0)
            weight = cfg.COMMODITIES.get(comm_id, {}).get("weight", 1)
            total += qty * weight
        return total

    def cargo_free(self):
        return self.max_cargo - self.cargo_used()

    def can_buy(self, commodity_id, amount, price_per_unit):
        total_cost = amount * price_per_unit
        total_weight = amount * cfg.COMMODITIES.get(commodity_id, {}).get("weight", 1)
        return (self.credits >= total_cost and
                self.cargo_used() + total_weight <= self.max_cargo)

    def buy(self, commodity_id, amount, price_per_unit):
        total_cost = amount * price_per_unit
        if not self.can_buy(commodity_id, amount, price_per_unit):
            return False
        self.credits -= total_cost
        if commodity_id in self.inventory:
            existing = self.inventory[commodity_id]
            avg_price = ((existing["buy_price"] * existing["qty"] + total_cost) /
                         (existing["qty"] + amount))
            existing["qty"] += amount
            existing["buy_price"] = int(avg_price)
        else:
            self.inventory[commodity_id] = {
                "commodity": commodity_id,
                "qty": amount,
                "buy_price": price_per_unit,
            }
        return True

    def can_sell(self, commodity_id, amount):
        return commodity_id in self.inventory and self.inventory[commodity_id]["qty"] >= amount

    def sell(self, commodity_id, amount, price_per_unit):
        if not self.can_sell(commodity_id, amount):
            return False
        self.credits += amount * price_per_unit
        self.inventory[commodity_id]["qty"] -= amount
        if self.inventory[commodity_id]["qty"] <= 0:
            del self.inventory[commodity_id]
        return True

    def apply_upgrade(self, upgrade_id):
        if upgrade_id in self.upgrades:
            return False
        cost = cfg.UPGRADES[upgrade_id]["cost"]
        if self.credits < cost:
            return False
        self.credits -= cost
        self.upgrades.add(upgrade_id)
        if upgrade_id == "retro_thrusters":
            self.has_retro = True
        elif upgrade_id == "cargo_upgrade":
            self.max_cargo = cfg.MAX_CARGO_UPGRADED
        elif upgrade_id == "engine_upgrade":
            self.acceleration = cfg.BASE_ACCELERATION + 50
        elif upgrade_id == "hyperdrive":
            self.has_hyperdrive = True
        elif upgrade_id == "armor":
            self.max_hp = cfg.MAX_HP + 50
            self.hp = min(self.hp + 50, self.max_hp)
        elif upgrade_id == "fuel_tank":
            self.max_fuel = cfg.MAX_FUEL + 50
            self.fuel = min(self.fuel + 50, self.max_fuel)
        return True

    def has_upgrade(self, upgrade_id):
        return upgrade_id in self.upgrades

    def damage(self, amount):
        self.hp -= amount
        return self.hp <= 0  # returns True if dead

    def repair(self, amount):
        if self.credits < amount * 2:
            return False
        self.credits -= amount * 2
        self.hp = min(self.hp + amount, self.max_hp)
        return True

    def refuel(self, amount):
        if self.credits < amount:
            return False
        self.credits -= amount
        self.fuel = min(self.fuel + amount, self.max_fuel)
        return True

    def is_dead(self):
        return self.hp <= 0

    def know_planet(self, planet):
        self.known_planets[planet.pid] = planet
        self.known_planet_ids.add(planet.pid)

    def knows_planet(self, planet_id):
        return planet_id in self.known_planet_ids
