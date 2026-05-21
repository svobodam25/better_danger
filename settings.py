# Better Danger — Settings & Constants
# Monochrome 1-bit style: ONLY black (0,0,0) and white (255,255,255)
# Infinite universe, procedurally generated planets, short travel, modest profits

import math

# Display
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
FPS = 60

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)

# Physics — true newtonian, no max speed cap. The longer you thrust, the faster you go.
BASE_ACCELERATION = 100.0    # px/s² forward thrust
RETRO_THRUST_MULT = 0.5      # retro thrusters are half as powerful — stopping is harder
BASE_TURN_RATE = 150.0       # degrees/s
MAX_SPEED = 1_000_000.0      # effectively uncapped; physics never enforces it
SPEED_DISPLAY_REF = 10_000.0 # reference speed for HUD speed bar (full bar = this speed)

# Player defaults
START_CREDITS = 500
START_FUEL = 100.0
MAX_FUEL = 100.0
START_HP = 100.0
MAX_HP = 100.0
START_CARGO = 10
MAX_CARGO_BASE = 10
MAX_CARGO_UPGRADED = 20

# Fuel consumption per second of thrust
FUEL_CONSUMPTION = 2.0       # units/s at full thrust

# Docking
DOCK_PROXIMITY = 150.0       # px distance from planet surface to trigger docking
DOCK_TOLERANCE_POS = 30.0    # px tolerance for parking
DOCK_TOLERANCE_ANGLE = 25.0  # degrees tolerance for parking

# Collision damage
WALL_DAMAGE = 10.0
SHIP_COLLISION_DAMAGE = 15.0
WRONG_SLOT_PENALTY = 100.0

# Warp/Hyperdrive
WARP_FUEL_COST = 30.0
WARP_COOLDOWN = 3.0          # seconds
WARP_MIN_DIST = 80_000.0
WARP_MAX_DIST = 200_000.0

# Universe — procedural generation, Elite-style vast distances
PLANET_SPACING = 40_000       # px grid step (sparse density makes real distance much larger)
PLANET_DENSITY = 0.25         # fraction of grid cells that hold a planet
PLANET_CLUSTER_SIZE = 5       # planets per cluster
GENERATION_RADIUS = 160_000   # generate planets within this radius of player

# Planet types & their price modifiers
PLANET_TYPES = ["mining", "desert", "tech", "agricultural", "industrial"]

# Commodities
COMMODITIES = {
    "iron":       {"name": "Iron",        "base_price": 40,  "weight": 1},
    "water":      {"name": "Water",       "base_price": 80,  "weight": 1},
    "electronics":{"name": "Electronics", "base_price": 100, "weight": 2},
    "fuel_cell":  {"name": "Fuel Cell",   "base_price": 30,  "weight": 1},
    "meds":       {"name": "Meds",        "base_price": 70,  "weight": 1},
    "food":       {"name": "Food",        "base_price": 50,  "weight": 1},
    "machinery":  {"name": "Machinery",   "base_price": 120, "weight": 3},
}

# Price modifiers per planet type (buy price = base_price * modifier)
# Sell price = base_price * modifier * 0.85
PRICE_MODIFIERS = {
    "mining":        {"iron": 0.5, "water": 0.9, "electronics": 1.5, "fuel_cell": 0.7, "meds": 1.2, "food": 1.1, "machinery": 1.4},
    "desert":        {"iron": 1.6, "water": 2.5, "electronics": 1.3, "fuel_cell": 1.4, "meds": 0.6, "food": 1.5, "machinery": 1.3},
    "tech":          {"iron": 0.7, "water": 0.8, "electronics": 0.4, "fuel_cell": 0.5, "meds": 1.3, "food": 1.0, "machinery": 0.6},
    "agricultural":  {"iron": 1.2, "water": 0.5, "electronics": 1.4, "fuel_cell": 1.1, "meds": 0.8, "food": 0.3, "machinery": 1.5},
    "industrial":    {"iron": 0.6, "water": 1.0, "electronics": 0.9, "fuel_cell": 0.6, "meds": 1.1, "food": 0.8, "machinery": 0.4},
}

# Upgrades
UPGRADES = {
    "cargo_upgrade":   {"name": "Cargo Expansion", "cost": 500, "desc": "+10 cargo space"},
    "engine_upgrade":  {"name": "Engine Upgrade",  "cost": 800, "desc": "+50 acceleration"},
    "hyperdrive":      {"name": "Hyperdrive",      "cost": 5000, "desc": "Warp jump with J key"},
    "armor":           {"name": "Armor Plating",   "cost": 600, "desc": "+50 max HP"},
    "fuel_tank":       {"name": "Fuel Tank",       "cost": 350, "desc": "+50 max fuel"},
}

# Universe
STAR_COUNT = 200             # background stars (parallax layers)
EXHAUST_TRAIL_LENGTH = 20    # trailing dots behind ship

# Font sizes
FONT_SMALL = 16
FONT_MEDIUM = 22
FONT_LARGE = 32
FONT_HUGE = 48
