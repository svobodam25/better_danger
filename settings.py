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

# Hull integrity speed limit — pushing past this damages the ship.
# 10 HP per second per 100 px/s of excess speed.
SAFE_SPEED = 1000.0
OVERSPEED_DAMAGE_PER_100 = 10.0

# Player defaults
START_CREDITS = 1500         # buffer for early learning trips
START_FUEL = 100.0
MAX_FUEL = 100.0
START_HP = 100.0
MAX_HP = 100.0
START_CARGO = 10
MAX_CARGO_BASE = 10
MAX_CARGO_UPGRADED = 20

# Fuel consumption per second of thrust
FUEL_CONSUMPTION = 1.2       # units/s at full thrust (reduced so trips are profitable)

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
PLANET_SPACING = 120_000       # px grid step (sparse density makes real distance much larger)
PLANET_DENSITY = 0.25         # fraction of grid cells that hold a planet
PLANET_CLUSTER_SIZE = 5       # planets per cluster
GENERATION_RADIUS = 480_000   # generate planets within this radius of player

# Asteroids — mineable for bonus credits / commodities between planets
ASTEROID_SPACING = 6_000          # px grid step (denser than planets)
ASTEROID_DENSITY = 0.18           # fraction of grid cells with an asteroid
ASTEROID_GENERATION_RADIUS = 40_000  # generate asteroids within this radius of player
ASTEROID_MINE_RANGE = 100         # extra px on top of asteroid radius to auto-mine

# Radar (HUD) — shows nearby planets and asteroids
RADAR_RANGE = 30_000              # world px shown by radar edge

# Display scale — 1 game-px represents 10 km of physical space.
# Used only for UI; engine still operates in raw px.
PX_PER_KM = 0.1                                  # 1 km = 0.1 px (10 km per pixel)
PX_PER_LS = 29_979.2458                          # 1 ls = ~29979 px
PX_PER_AU = 14_959_787.07                        # 1 AU = ~15 M px
PX_PER_LY = 946_073_047_258.08                   # 1 ly = ~946 G px

# Mining minigame — heat outpaces progress so you must release periodically
MINE_ENGAGE_RANGE = 300           # extra px on top of asteroid radius to start minigame with F
MINE_PROGRESS_RATE = 22.0         # % per second while drilling (4.5s straight = 100%)
MINE_HEAT_RATE = 28.0             # % per second while drilling (3.6s straight = overheat)
MINE_COOL_RATE = 35.0             # % per second when idle
MINE_OVERHEAT_DAMAGE = 15.0       # HP lost on overheat
MINE_DRILL_HEAT_REDUCTION = 0.7   # multiplier applied when Industrial Drill upgrade owned

# Ranks (based on total credits ever earned)
RANKS = [
    (0, "Spacer"),
    (5_000, "Trader"),
    (25_000, "Merchant"),
    (100_000, "Tycoon"),
    (500_000, "Magnate"),
    (2_000_000, "Elite"),
]

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

# Upgrade prerequisites — a Mk2 cannot be bought without owning Mk1, etc.
UPGRADE_PREREQUISITES = {
    "cargo_upgrade_2":  "cargo_upgrade",
    "cargo_upgrade_3":  "cargo_upgrade_2",
    "cargo_upgrade_4":  "cargo_upgrade_3",
    "cargo_upgrade_5":  "cargo_upgrade_4",
    "engine_upgrade_2": "engine_upgrade",
    "armor_2":          "armor",
    "fuel_tank_2":      "fuel_tank",
}

# Upgrades — tiered progression so the player has long-term goals
UPGRADES = {
    "cargo_upgrade":     {"name": "Cargo Expansion",    "cost": 500,   "desc": "+10 cargo space"},
    "cargo_upgrade_2":   {"name": "Cargo Hold Mk2",     "cost": 2000,  "desc": "+10 more cargo"},
    "cargo_upgrade_3":   {"name": "Cargo Hold Mk3",     "cost": 5000,  "desc": "+10 more cargo"},
    "cargo_upgrade_4":   {"name": "Heavy Freighter",    "cost": 12000, "desc": "+15 more cargo"},
    "cargo_upgrade_5":   {"name": "Bulk Carrier",       "cost": 28000, "desc": "+25 more cargo"},
    "engine_upgrade":    {"name": "Engine Upgrade",     "cost": 800,  "desc": "+50 acceleration"},
    "engine_upgrade_2":  {"name": "Engine Mk2",         "cost": 2500, "desc": "+100 acceleration"},
    "armor":             {"name": "Armor Plating",      "cost": 600,  "desc": "+50 max HP"},
    "armor_2":           {"name": "Heavy Armor",        "cost": 2200, "desc": "+50 more max HP"},
    "fuel_tank":         {"name": "Fuel Tank",          "cost": 350,  "desc": "+50 max fuel"},
    "fuel_tank_2":       {"name": "Large Fuel Tank",    "cost": 1500, "desc": "+100 more max fuel"},
    "scanner_range":     {"name": "Long-Range Scanner", "cost": 1200, "desc": "Radar range 2x"},
    "mining_drill":      {"name": "Industrial Drill",   "cost": 1500, "desc": "Mining heat -30%"},
    "hyperdrive":        {"name": "Hyperdrive",         "cost": 8000, "desc": "Warp jump with J key"},
}

# Universe
STAR_COUNT = 200             # background stars (parallax layers)
EXHAUST_TRAIL_LENGTH = 20    # trailing dots behind ship

# Font sizes
FONT_SMALL = 16
FONT_MEDIUM = 22
FONT_LARGE = 32
FONT_HUGE = 48
